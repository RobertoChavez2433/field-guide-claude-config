# OCR Accuracy Fixes Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Fix all remaining Springfield extraction failures with generic algorithmic pipeline improvements — zero PDF-specific heuristics.
**Analysis:** `.claude/dependency_graphs/2026-03-15-ocr-accuracy-fixes/`

**Architecture:** Six targeted fixes across 4 source files: curly quote normalization, unit case normalization, crop inset relaxation (drop fringe term), Y-band sort refinement for short punctuation, column-selective DPI upscaling, and item number candidate rejection.
**Tech Stack:** Dart, Tesseract OCR, OpenCV (existing)
**Blast Radius:** 4 direct, 3 dependent, 3 test files + 1 integration test

---

## Fix Inventory (from investigation)

| # | Fix | Items | File(s) |
|---|-----|-------|---------|
| 1 | Curly → straight quote normalization | 52 | post_process_utils.dart |
| 2 | Unit case normalization | 106 | post_process_utils.dart |
| 3 | Drop fringe term from crop insets | 130 (+ possibly 62) | text_recognizer_v2.dart |
| 4 | Y-band sort: anchor short punctuation | 26, 36, 37, 38-dash | cell_extractor_v2.dart |
| 5 | Column-selective upscale (desc → 3x/900 DPI) | 38-superscript | crop_upscaler.dart + text_recognizer_v2.dart |
| 6 | Item number candidate rejection (no-digit = reject) | 62 | text_recognizer_v2.dart |

---

## Phase 1: Quick Wins (Fixes 1-3)

These are small, isolated changes with no cross-dependencies.

**Agent**: `frontend-flutter-specialist-agent`

### Sub-phase 1.1: Curly quote normalization in cleanDescriptionArtifacts

**File**: `lib/features/pdf/services/extraction/shared/post_process_utils.dart`
**Method**: `cleanDescriptionArtifacts` at line 39

Current code (line 48):
```dart
.replaceAll(RegExp(r'[\u201C\u201D\u2018\u2019`]'), '')
```

Replace with:
```dart
// WHY: Tesseract sometimes returns curly quotes (U+201C/201D) for inch marks
// at cell edges where confidence is low. Normalize to straight equivalents
// BEFORE stripping, so measurement symbols like 12" are preserved.
.replaceAll('\u201C', '"')  // left double curly → straight double
.replaceAll('\u201D', '"')  // right double curly → straight double
.replaceAll('\u2018', "'")  // left single curly → straight single
.replaceAll('\u2019', "'")  // right single curly → straight single
.replaceAll('`', '')        // backtick → remove (not a measurement symbol)
```

**Test file**: `test/features/pdf/extraction/shared/post_process_utils_test.dart` (already exists from prior plan)
Add test group `cleanDescriptionArtifacts — curly quote normalization`:
- `Tee, 12" x 12" x 12\u201D` → `Tee, 12" x 12" x 12"` (curly normalized, NOT stripped)
- `Tee, 12" x 12" x 12"` → unchanged (straight quotes preserved)
- `some \u201Cquoted\u201D text` → `some "quoted" text` (double curly → straight)
- `some \u2018quoted\u2019 text` → `some 'quoted' text` (single curly → straight)

### Sub-phase 1.2: Unit comparison case normalization

**Root cause**: `UnitRegistry.normalize` (unit_registry.dart:85) already calls `.toUpperCase()`.
However, the ground truth comparison in `pipeline_comparator.dart:216` uses exact `==` match:
```dart
final matches = sf.$2 == sf.$3;  // case-sensitive!
```
The extracted unit `Ft` goes through `PostProcessUtils.normalizeUnit` → `_cleanUnitText` →
`_normalizeUnitInternal` → `UnitRegistry.normalize` which uppercases to `FT`. But if the unit
bypasses normalization (e.g., assigned directly from OCR in row_parser), `Ft` persists.

**Two-layer fix**: Ensure normalization AND make comparison robust.

**File 1**: `lib/features/pdf/services/extraction/shared/post_process_utils.dart`
**Method**: `_cleanUnitText` at line 318 — add `.toUpperCase()` as belt-and-suspenders:

```dart
static String _cleanUnitText(String text) {
  if (text.isEmpty) return '';
  var cleaned = _cleanOcrArtifacts(text);
  cleaned = cleaned.replaceAll('.', '');
  cleaned = cleaned.replaceAll(RegExp(r'\s+'), '');
  // WHY: Belt-and-suspenders uppercase. UnitRegistry.normalize also uppercases,
  // but this ensures any code path through _cleanUnitText produces uppercase
  // even if it bypasses the registry (e.g., unknown unit tokens).
  return cleaned.trim().toUpperCase();
}
```

**File 2**: `test/features/pdf/extraction/helpers/pipeline_comparator.dart`
**Line**: 216 — make unit comparison case-insensitive:

Current:
```dart
// String fields: exact match, no normalization
for (final sf in [
  ('description', ext.description, gt.description),
  ('unit', ext.unit, gt.unit),
]) {
  final matches = sf.$2 == sf.$3;
```

Replace with:
```dart
// WHY: Description uses exact match. Unit uses case-insensitive match because
// OCR may return mixed-case units (e.g., "Ft" vs "FT") that are semantically
// identical. The extraction pipeline normalizes to uppercase, but ground truth
// may use different casing.
final descMatches = ext.description == gt.description;
fields.add(FieldComparison(
  fieldName: 'description',
  expected: gt.description,
  actual: ext.description,
  matches: descMatches,
));
if (!descMatches) allMatch = false;

final unitMatches = (ext.unit ?? '').toUpperCase() == (gt.unit ?? '').toUpperCase();
fields.add(FieldComparison(
  fieldName: 'unit',
  expected: gt.unit,
  actual: ext.unit,
  matches: unitMatches,
));
if (!unitMatches) allMatch = false;
```

Remove the `for` loop that iterates over both fields together, replacing with the two explicit comparisons above. The loop after this point (for numeric fields) remains unchanged.

**Test**: Add to `post_process_utils_test.dart`:
- `normalizeUnit('Ft')` → `'FT'`
- `normalizeUnit('ft')` → `'FT'`
- `normalizeUnit('FT')` → `'FT'` (already correct)
- `normalizeUnit('Syd')` → `'SYD'`

### Sub-phase 1.3: Drop fringe term from crop insets

**File**: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
**Method**: `_computeCellCrops` at line 1174

Current lines 1209-1212:
```dart
final topInsetPx = (topLine.widthPixels + 1) ~/ 2 + topLine.fringeSide2 + 1;
final bottomInsetPx = (bottomLine.widthPixels + 1) ~/ 2 + bottomLine.fringeSide1 + 1;
final leftInsetPx = (leftLine.widthPixels + 1) ~/ 2 + leftLine.fringeSide2 + 1;
final rightInsetPx = (rightLine.widthPixels + 1) ~/ 2 + rightLine.fringeSide1 + 1;
```

Replace with:
```dart
// WHY: Post-inpaint whitewash (grid_line_remover.dart:806-826) now covers
// halfWidth + maxFringe + 2px bleed from line center. The fringe inset term
// is redundant and actively clips letter descenders (y, g, p, q, j) in tight
// cells. Keeping halfWidth + 1px safety is sufficient — whitewash provides
// 2+ px of pure white buffer beyond this crop edge.
final topInsetPx = (topLine.widthPixels + 1) ~/ 2 + 1;
final bottomInsetPx = (bottomLine.widthPixels + 1) ~/ 2 + 1;
final leftInsetPx = (leftLine.widthPixels + 1) ~/ 2 + 1;
final rightInsetPx = (rightLine.widthPixels + 1) ~/ 2 + 1;
```

**Test file**: `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart`
Update any existing tests that assert crop inset values to match the new formula. If there's a test for `_computeCellCrops` that checks inset math with fringe values, update expected values.

Also update docstring at line 1174 to reflect the change:
```dart
/// WHY: Half-width crop boundaries. After grid lines are inpainted and
/// whitewashed by Stage 2B-ii.6, crops are inset by (halfWidth + 1px safety)
/// from line center. The whitewash covers the full TELEA bleed zone, making
/// fringe-based insets unnecessary.
```

---

## Phase 2: Y-Band Sort Refinement (Fix 4)

**Agent**: `frontend-flutter-specialist-agent`

### Sub-phase 2.1: Fix _buildCell sort for short punctuation

**File**: `lib/features/pdf/services/extraction/stages/cell_extractor_v2.dart`
**Method**: `_buildCell` at line 517

The current sort uses `medianHeight * 0.5` as the Y-band tolerance. Short glyphs like `-` have much smaller bounding box heights than full-cap words, so their `boundingBox.top` can exceed the tolerance even though they're visually on the same line.

Replace the sort logic (lines 528-541) with a Y-CENTER-based comparison instead of Y-TOP:

Current:
```dart
final yBandTolerance = medianHeight * 0.5;
fragments.sort((a, b) {
  final yDiff = a.boundingBox.top - b.boundingBox.top;
  if (yDiff.abs() <= yBandTolerance) {
    return a.boundingBox.left.compareTo(b.boundingBox.left);
  }
  return yDiff < 0 ? -1 : 1;
});
```

Replace with:
```dart
// WHY: Use Y-center instead of Y-top for band comparison. Short glyphs
// like "-" have the same vertical center as surrounding words but a much
// higher top position (centered on the cap-height midline). Y-center
// comparison groups them correctly into the same reading-order band.
final yBandTolerance = medianHeight * 0.5;
fragments.sort((a, b) {
  final aCenterY = a.boundingBox.top + a.boundingBox.height / 2;
  final bCenterY = b.boundingBox.top + b.boundingBox.height / 2;
  final yDiff = aCenterY - bCenterY;
  if (yDiff.abs() <= yBandTolerance) {
    return a.boundingBox.left.compareTo(b.boundingBox.left);
  }
  return yDiff < 0 ? -1 : 1;
});
```

**Test file**: `test/features/pdf/extraction/stages/stage_4d_cell_extractor_test.dart`
Add test group `CellExtractorV2 - Short Punctuation Y-Band Sort`:
1. **Dash between words**: fragments `["Pressure", "Reducing", "Valve", "-", "20th"]` where `-` has a smaller height and slightly lower top than the words. Y-center should group them all as same line. Expected: `"Pressure Reducing Valve - 20th"`
2. **Dash at different Y-center (truly different line)**: fragments where `-` is genuinely on a different visual line (Y-center gap > tolerance). Expected: multi-line order preserved.

---

## Phase 3: Column-Selective DPI Upscaling (Fix 5)

**Agent**: `frontend-flutter-specialist-agent`

### Sub-phase 3.1: Make CropUpscaler target DPI configurable

**File**: `lib/features/pdf/services/extraction/shared/crop_upscaler.dart`

Current (line 26):
```dart
static const double kTargetDpi = 600.0;
```

Change to instance field with default:
```dart
// WHY: Column-selective DPI. Description columns benefit from higher
// resolution (900 DPI) for superscript/subscript recognition, but numeric
// columns at 900 DPI cause comma/period confusion. Making this configurable
// per-instance allows TextRecognizerV2 to use different upscalers per column.
final double targetDpi;

// Keep backward-compatible default
static const double kDefaultTargetDpi = 600.0;
```

Update constructor:
```dart
CropUpscaler({
  CropResizeFn? resizeFn,
  CropCompositeFn? compositeFn,
  this.targetDpi = kDefaultTargetDpi,
}) : _resizeFn = resizeFn ?? _defaultResize,
     _compositeFn = compositeFn ?? _defaultComposite;
```

Update `computeScaleFactor` (line 114-126) — replace ALL occurrences of `kTargetDpi` with `targetDpi`:
- Line 118: `if (renderDpi >= kTargetDpi)` → `if (renderDpi >= targetDpi)`
- Line 119: `final dpiScale = kTargetDpi / renderDpi` → `final dpiScale = targetDpi / renderDpi`

There are exactly 2 occurrences of `kTargetDpi` in this method. Both must be changed to the instance field `targetDpi`.

### Sub-phase 3.2: Use higher DPI upscaler for description column

**File**: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`

Current (line 154-155):
```dart
TextRecognizerV2({CropUpscaler? cropUpscaler})
  : _cropUpscaler = cropUpscaler ?? CropUpscaler();
```

Change to — add the `_descriptionCropUpscaler` field declaration in the class body alongside `_cropUpscaler` (line 53):
```dart
// Class body field declarations (near line 53):
final CropUpscaler _cropUpscaler;
final CropUpscaler _descriptionCropUpscaler;

// Constructor (line 154):
TextRecognizerV2({CropUpscaler? cropUpscaler, CropUpscaler? descriptionCropUpscaler})
  : _cropUpscaler = cropUpscaler ?? CropUpscaler(),
    _descriptionCropUpscaler = descriptionCropUpscaler ?? CropUpscaler(targetDpi: 900.0);
```

In `_recognizeWithCellCrops`, where `_cropUpscaler.prepareForOcr` is called for a cell, check the column policy. If the column is `description` (columnIndex == 1), use `_descriptionCropUpscaler` instead:

Find the call site where `_cropUpscaler.prepareForOcr(crop, renderDpi: renderDpi)` is called inside `_recognizeWithCellCrops`. The local variable holding the column policy is named `columnPolicy` (not `policy`). Change to:
```dart
// WHY: Description column uses 900 DPI for better superscript recognition.
// Numeric columns stay at 600 DPI to avoid comma/period confusion.
final upscaler = (columnPolicy.kind == _ColumnPolicyKind.description)
    ? _descriptionCropUpscaler
    : _cropUpscaler;
final prepared = upscaler.prepareForOcr(crop, renderDpi: renderDpi);
```

**IMPORTANT**: The variable is `columnPolicy`, not `policy`. Read the method to confirm the exact variable name before editing.

**Test**: Update `stage_2b_text_recognizer_test.dart` — if there are existing tests that create TextRecognizerV2, they should still work with the default constructor.

Add new test: verify that description column uses the higher-DPI upscaler:
- Create TextRecognizerV2 with custom upscalers
- Verify description column crops use 900 DPI target
- Verify numeric column crops use 600 DPI target

---

## Phase 4: Item Number Candidate Rejection (Fix 6)

**Agent**: `frontend-flutter-specialist-agent`

### Sub-phase 4.1: Reject no-digit item number candidates

**File**: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
**Method**: `_scoreCandidate` at line 938

In the `_ColumnPolicyKind.itemNumber` case (line 962-966), add a hard rejection for candidates with zero digits:

Current:
```dart
case _ColumnPolicyKind.itemNumber:
  score = (accepted ? 30.0 : -15.0) +
      digitCount * 2.0 -
      alphaCount * 8.0 +
      meanConfidence * 10.0 -
      (text.length - digitCount).abs().toDouble();
  break;
```

Replace with:
```dart
case _ColumnPolicyKind.itemNumber:
  // WHY: Item numbers MUST contain digits. If OCR returns a non-numeric
  // character (like ">"), it should never win candidate selection even if
  // retry candidates return blank. A zero-digit candidate gets a floor
  // score that blank (0.0 confidence) can beat.
  if (digitCount == 0 && text.isNotEmpty) {
    score = -100.0;
    break;
  }
  score = (accepted ? 30.0 : -15.0) +
      digitCount * 2.0 -
      alphaCount * 8.0 +
      meanConfidence * 10.0 -
      (text.length - digitCount).abs().toDouble();
  break;
```

**Test**: Add to text recognizer tests or create a focused unit test:
- Score a candidate with text `>` (0 digits) → score should be -100
- Score a candidate with text `62` (2 digits) → score should be positive
- Score a candidate with text `` (empty) → score should NOT trigger the -100 (empty is handled elsewhere)

---

## Phase 5: Tests + Validation

**Agent**: `qa-testing-agent`

### Sub-phase 5.1: Run full test suite

Run: `pwsh -Command "flutter test"`
Expected: All tests pass (including new tests from Phases 1-4)

### Sub-phase 5.2: Springfield integration validation

Run: `pwsh -Command "flutter test integration_test/springfield_report_test.dart -d windows --dart-define=SPRINGFIELD_PDF='C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf' --dart-define=RESET_BASELINE=true"`
Expected: Description accuracy ≥ 98%, all numeric fields 100%, checksum $0

NOTE: Run `pwsh -File tools/focus-test-window.ps1` in background alongside the test to auto-focus the app window.

---

## Expected Outcome

| Metric | Before | After |
|--------|--------|-------|
| Description accuracy | 95.4% (6 failures) | ≥ 98.5% (≤ 2 remaining) |
| Unit accuracy | 99.2% (1 failure) | 100% |
| Items found | 131/131 | 131/131 |
| Checksum | $0 distance | $0 distance |
| Quantity | 100% | 100% |
| Unit Price | 100% | 100% |
| Bid Amount | 100% | 100% |

### Per-Item Expected Fix

| Item | Current | Expected After | Fix |
|------|---------|---------------|-----|
| 52 | FAIL:desc (trailing `"` stripped) | PASS | Curly quote normalization |
| 106 | FAIL:unit (`Ft` vs `FT`) | PASS | Unit case normalization |
| 130 | FAIL:desc (`Svm` vs `Sym`) | PASS (likely) | Wider crop + possibly 3x upscale |
| 26 | FAIL:desc (word order) | PASS | Y-center sort |
| 36 | FAIL:desc (dash displaced) | PASS | Y-center sort |
| 37 | FAIL:desc (dash displaced) | PASS | Y-center sort |
| 38 | FAIL:desc (`20"` vs `20th` + dash) | Partial fix (dash fixed, superscript may need more) | Y-center sort + 3x upscale |
| 62 | MISS (`>` item number) | PASS (matched correctly) or graceful skip | Candidate rejection + wider crop |

### Known Remaining Risk
- Item 38 superscript `th` → `"`: 3x DPI upscale may or may not resolve this. If not, this is a genuine Tesseract limitation with superscript text at this font size. No PDF-specific hack should be added.
