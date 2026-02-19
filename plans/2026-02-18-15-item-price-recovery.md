# Implementation Plan: 15-Item Price Recovery (Pipe Fix + Classification Fix + Rescue Gate)

**Date**: 2026-02-18 | **Session**: 372

## Context

The pipeline scorecard shows 24 items with null `unit_price` at Stage 18 (107/131). Investigation traced the **most upstream root cause** to Stage 8 (Row Classification), where 15 priceContinuation rows are misclassified as `boilerplate`. These 15 rows contain real price data that OCR detected correctly (confirmed by Hypothesis 1 investigation — all 15 have exact-match price text in unified_elements).

**Why they're misclassified**: The `priceContinuation` gate at `row_classifier_v3.dart:244` requires `textPopulated.isEmpty`. Two contamination patterns cause this gate to reject valid price rows:

- **Pattern A (9 items: 27-32, 59, 112, 113)**: Pipe `|` OCR artifacts from gridlines land in text-zone columns. Root cause: `_scanWhitespaceInset` breaks on first white pixel, leaving gridline body in cell crops. OCR reads the gridline as `|`.
- **Pattern B (6 items: 26, 38, 121, 123, 125, 130)**: Description overflow fragments (e.g., `"vate"`, `"Reducing"`, `"Fav"`) share the same Y-band as prices, so `_groupElementsByRow` puts them on the same row. Text-zone elements make `textPopulated.isNotEmpty`.

**Three independent fixes**, each solving a distinct layer:

| Fix | Solves | File |
|-----|--------|------|
| 1. Pipe scan termination | Pattern A source (eliminates `\|` artifacts) | `text_recognizer_v2.dart` |
| 2. Relaxed priceCont gate | Pattern B (allows minor text + prices) | `row_classifier_v3.dart` |
| 3. Rescue gate (validation) | Defense-in-depth for both patterns | `row_classifier_v3.dart` |

## Pipeline Stage Order (Reference)

```
Stage 2B-iii: Text Recognition (OCR)        ← Fix 1 here
Stage 3:      Element Validation
              (Provisional classification + header consolidation)
Stage 4B:     Region Detection
Stage 4C:     Column Detection
Stage 4A:     Row Classification V3          ← Fixes 2 & 3 here
              Header Consolidation (Final)
Stage 4A.5:   Row Merging
Stage 4D:     Cell Extraction
Stage 4E:     Row Parsing
```

---

## Fix 1: `_scanWhitespaceInset` Termination Logic

**File**: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`

### Change 1a: Inner loop (lines 608-628)

Replace "break on first white" with "scan all depths, track furthest dark pixel":

**Current** (line 610-625):
```dart
for (final perpPos in samplePositions) {
  int inset = 0;
  for (int d = 0; d < maxScanDepth; d++) {
    // ... coordinate computation ...
    final pixel = image.getPixel(px, py);
    if (pixel.r >= whiteThreshold) {
      break;                          // ← premature exit
    }
    inset = d + 1;
  }
  if (inset > maxInset) maxInset = inset;
}
```

**After**:
```dart
for (final perpPos in samplePositions) {
  int lastDark = -1;
  for (int d = 0; d < maxScanDepth; d++) {
    // ... coordinate computation (unchanged) ...
    final pixel = image.getPixel(px, py);
    if (pixel.r < whiteThreshold) {
      lastDark = d;
    }
  }
  final inset = lastDark + 1;        // 0 if no dark pixels found
  if (inset > maxInset) maxInset = inset;
}
```

### Change 1b: Doc comment (lines 575-578)

Update to reflect new behavior: scans all depths up to `maxScanDepth` (9px), returns furthest dark pixel + 1. Remove "until reaching a white pixel" and "Max scan depth is 5px".

### Expected effect

- Pipe `|` count drops from 36 to 0 in unified_elements
- Pattern A rows lose their text-zone contamination → pass existing strict priceCont gate
- Items 58/111 pipe-prefixed values (`| $10,206.80`, `| $739.90`) become clean

---

## Fix 2: Relaxed priceContinuation Gate for Mixed Rows

**File**: `lib/features/pdf/services/extraction/stages/row_classifier_v3.dart`

### Problem

The classification waterfall has a gap — no branch handles rows with **both** text-zone and price-zone content that lack an item number:

```
Gate 5 (priceCont):  pricePopulated.isNotEmpty AND textPopulated.isEmpty    ← rejects mixed
Gate 6 (descCont):   textPopulated.isNotEmpty AND pricePopulated.isEmpty    ← rejects mixed
→ Falls through to boilerplate
```

Pattern B rows look like: `vate | Property | $1.00 | $10,000.00` — desc fragments + real prices.

### Change 2a: Add `_isMinorTextContent` helper method

Add a new private method that identifies "minor" text-zone content — fragments that don't constitute a real data row:

```dart
/// Returns true if text-zone elements are minor fragments (desc overflow,
/// not a real data row). Used to relax the priceContinuation gate.
bool _isMinorTextContent(
  List<OcrElement> textElements,
  _ZoneContext zones,
) {
  if (textElements.isEmpty) return true;

  // If any element matches item number pattern, it's not minor
  final itemElements = zones.itemNumberColumn == null
      ? const <OcrElement>[]
      : textElements.where((e) =>
          e.boundingBox.left >= zones.itemNumberColumn!.startX &&
          e.boundingBox.right <= zones.itemNumberColumn!.endX);
  if (itemElements.any((e) => _itemNumberPattern.hasMatch(e.text.trim()))) {
    return false;
  }

  // Total non-whitespace character count across all text-zone elements
  final totalChars = textElements.fold<int>(
    0, (sum, e) => sum + e.text.trim().length,
  );

  // Minor if total text is short (desc overflow fragments are typically < 20 chars)
  return totalChars <= 20;
}
```

**Threshold rationale**: The 6 Pattern B rows have text-zone char counts of 5, 9, 12, 9, 9, 3 (max=12). Real data rows have item# + description + unit + qty — typically 30+ chars. Threshold of 20 provides comfortable margin.

### Change 2b: Insert relaxed gate between lines 258 and 260

After the strict priceCont gate fails, add:

```dart
// Relaxed priceContinuation: allows minor text-zone content (desc overflow)
if (pricePopulated.isNotEmpty &&
    textPopulated.isNotEmpty &&
    !hasItemNumber &&
    _isMinorTextContent(textPopulated, zones) &&
    zones.priceColumns.isNotEmpty) {
  if (_canContinueFromPrevious(previousRow, const {
        RowType.data,
        RowType.descContinuation,
      }, pageIndex) &&
      _gapWithinThreshold(
        current: rowElements,
        previous: previousRow!,
        medianHeight: medianHeight,
      )) {
    return const _ClassifiedType(RowType.priceContinuation, 0.82);
  }
}
```

Note: confidence 0.82 (lower than strict gate's 0.88) signals this was a relaxed match.

### Expected effect

- Pattern B rows (26, 38, 121, 123, 125, 130) reclassify as `priceContinuation`
- Their prices flow through merging → cell extraction → parsing
- No false positives: real data rows have item numbers and long text (> 20 chars)

---

## Fix 3: Header-Validated Rescue Gate (Validation Layer)

**File**: `lib/features/pdf/services/extraction/stages/row_classifier_v3.dart`

### Purpose

Defense-in-depth using header-derived column knowledge. When we classified header rows (Stage 4A) and built the column map (Stage 4C), we learned the exact X positions of each column — including where `unitPrice` and `bidAmount` live on every page. Fix 3 uses those known positions as a validation pass: after the main classification loop, sweep all `boilerplate` rows and check if any have OCR elements sitting in the price-column X ranges (as defined by the `columnMap` that was derived from header analysis). If they do and follow a data row, they're misclassified priceContinuation rows that should be rescued.

### Change 3a: Add `_rescueBoilerplateRows` method

```dart
/// Post-classification sweep: reclassify boilerplate rows that contain
/// price-column elements and follow a data/continuation row.
/// Uses header-derived column positions from columnMap to identify
/// price-column content.
void _rescueBoilerplateRows(
  List<ClassifiedRow> rows,
  List<ColumnDef> pageColumnsLookup(int pageIndex),
  ColumnMap columnMap,
  double medianHeight,
) {
  for (int i = 0; i < rows.length; i++) {
    if (rows[i].type != RowType.boilerplate) continue;

    final row = rows[i];
    final pageColumns = pageColumnsLookup(row.pageIndex);
    final zones = _computeZones(pageColumns);

    // Must have price-zone elements (using header-derived column boundaries)
    final elementsByColumn = _mapElementsToColumns(row.elements, pageColumns);
    final priceElements = _zoneElements(elementsByColumn, zones.priceColumns);
    if (priceElements.isEmpty) continue;

    // Must have at least one element with a dollar sign or numeric price pattern
    final hasPriceText = priceElements.any(
      (e) => e.text.contains('\$') || RegExp(r'\d+[.,]\d{2}').hasMatch(e.text),
    );
    if (!hasPriceText) continue;

    // Must follow a data or continuation row (check previous non-blank)
    if (i == 0) continue;
    final prev = rows[i - 1];
    if (prev.pageIndex != row.pageIndex) continue;
    if (!const {
      RowType.data,
      RowType.descContinuation,
      RowType.priceContinuation,
    }.contains(prev.type)) continue;

    // Gap check
    if (!_gapWithinThreshold(
      current: row.elements,
      previous: prev,
      medianHeight: medianHeight,
    )) continue;

    // Rescue: reclassify as priceContinuation
    rows[i] = ClassifiedRow(
      pageIndex: row.pageIndex,
      rowIndex: row.rowIndex,
      type: RowType.priceContinuation,
      elements: row.elements,
      confidence: 0.75,  // lowest confidence — rescued row
    );
  }
}
```

### Change 3b: Call rescue gate at end of `classify()` method

After the main `for (final rowElements in pageRows)` loop completes (after line 94, before line 97), add:

```dart
// Fix 3: Header-validated rescue gate — uses columnMap positions to
// catch boilerplate rows that contain price-column content
_rescueBoilerplateRows(
  rows,
  (pageIndex) => _columnsForPage(pageIndex, columnMap),
  columnMap,
  medianHeight,
);
```

### Note: ClassifiedRow mutability

`ClassifiedRow` is currently created in the loop and added to `rows`. The rescue gate replaces entries in the list. Check if `ClassifiedRow` allows this — it should since `rows` is a `List<ClassifiedRow>` (mutable list with mutable entries).

### Expected effect

- Catches any remaining boilerplate rows with price content that Fixes 1+2 missed
- Confidence 0.75 distinguishes rescued rows in diagnostics
- No false positives: requires dollar sign/numeric pattern + adjacent data row + gap threshold

---

## Testing

### New unit tests in `row_classifier_v3_test.dart`

Using existing test helpers (`_rowAt`, `_cell`, `_extraction`, `_columnMap`):

1. **Fix 2 test**: "classifies mixed text+price row after data as priceContinuation"
   - Data row with item number, then row with short text fragments + price elements
   - Expect: `[data, priceContinuation]`

2. **Fix 2 negative test**: "rejects mixed row with long text content"
   - Data row, then row with many text elements (> 20 chars) + prices
   - Expect: NOT `priceContinuation` (falls to boilerplate or descContinuation)

3. **Fix 3 test**: "rescue gate reclassifies boilerplate with price content"
   - Data row, then row with pipes + prices that would fail both gates
   - Expect: rescue gate catches it → `priceContinuation`

4. **Fix 3 negative test**: "rescue gate ignores boilerplate without price text"
   - Boilerplate row with no dollar signs or numeric prices
   - Expect: stays `boilerplate`

### Integration verification

After all 3 fixes:

```powershell
# 1. Regenerate fixtures
pwsh -Command "dart run tool/generate_springfield_fixtures.dart"

# 2. Run full PDF test suite (858+ tests)
pwsh -Command "flutter test test/features/pdf/extraction/"

# 3. Run stage trace scorecard
pwsh -Command "flutter test test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart --plain-name 'Print stage-by-stage scorecard vs ground truth'"
```

### Expected scorecard deltas

| Metric | Before | After (expected) |
|--------|--------|-----------------|
| Pipe `\|` elements | 36 | 0 |
| Stage 8 boilerplate rows | 17 | 2 (only legitimate boilerplate) |
| Stage 8 priceCont rows | 116 | 131 |
| Stage 16 price coverage | 122/138 | 137/138 (total row still null) |
| Stage 18 w/ unit_price | 107/131 | ~122/131 (+15 from classification fix) |
| Stage 18 w/ bid_amount | 107/131 | ~122/131 |
| Null unit_price | 24 | ~9 (Cat B/C items remain) |
| Checksum delta | $567,598 | significantly reduced |

Items still affected after this fix (remaining blockers):
- BLOCKER-3 (Cat C — OCR format errors): Items 1, 4, 10, 11, 74, 87, 88, 89 — malformed price text
- Item 114: OCR reads `$3.200.00` instead of `$3,200.00`

---

## Files Modified

| File | Changes | Risk |
|------|---------|------|
| `text_recognizer_v2.dart:608-628` | Fix 1: Replace inner loop termination | Low — scan depth capped at 9 |
| `text_recognizer_v2.dart:575-578` | Fix 1: Doc comment update | None |
| `row_classifier_v3.dart:258` | Fix 2: Insert relaxed priceCont gate | Low — gated by `_isMinorTextContent` |
| `row_classifier_v3.dart` (new method) | Fix 2: Add `_isMinorTextContent` | None — new helper |
| `row_classifier_v3.dart:94` | Fix 3: Call rescue gate | Low — post-pass only touches boilerplate |
| `row_classifier_v3.dart` (new method) | Fix 3: Add `_rescueBoilerplateRows` | Low — strict criteria |
| `row_classifier_v3_test.dart` | 4 new unit tests | None — additive |
| `test/.../springfield_*.json` | Fixture regeneration | None — test data |

## Implementation Order

1. Fix 1 (pipe scan) — independent, upstream
2. Fix 2 (relaxed gate) — independent, classification layer
3. Fix 3 (rescue gate) — validation layer, runs after 1+2
4. Unit tests for Fixes 2+3
5. Regenerate fixtures
6. Run full test suite + scorecard comparison
