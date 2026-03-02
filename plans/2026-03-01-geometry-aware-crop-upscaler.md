# Implementation Plan: Geometry-Aware Crop Upscaler

**Last Updated**: 2026-03-01
**Status**: READY (post-adversarial review)
**Adversarial Review**: PASSED with 7 corrections applied

## Overview

The PDF extraction pipeline's CropUpscaler currently applies a uniform 2.0x upscale (300 to 600 DPI) to ALL cell crops before OCR. Narrow numeric columns (unitPrice=333px, bidAmount=358px) still produce low OCR confidence despite upscaling -- item 121's unitPrice has conf=0.555 and value=null. The previous attempt to fix this with `kMinCropWidth=500` caused BLOCKER-16 (item merger regression, 131 to 130 items, 2 BUGs).

This plan implements a **column-adaptive DPI target with a continuous curve** that gives narrower columns more upscaling without the hard threshold that caused BLOCKER-16. The formula is:

```
targetDpi(cropWidth) = baseDpi + boostDpi * max(0, 1 - cropWidth / widthCeiling)
```

Constants: `baseDpi=600, boostDpi=300, widthCeiling=500`

**Expected impact**: Narrow columns get 2.28x-2.71x scale (vs uniform 2.0x), while wide columns stay at 2.0x. This should improve OCR confidence for unitPrice/bidAmount without changing crop boundaries or causing row mergers.

**Important limitation**: The adaptive boost only applies when `renderDpi < kBaseDpi` (600). At `renderDpi >= 600`, all crops return `scaleFactor=1.0` regardless of width — no upscaling occurs, so no boost is possible. This matches the existing behavior and is intentional: if the render is already high-DPI, upscaling adds no value.

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Approach | Continuous curve | Avoids hard threshold that caused BLOCKER-16 |
| Formula location | Inside `computeScaleFactor()` | No API changes needed; cropWidth already available |
| API surface change | None | `prepareForOcr` signature unchanged; width comes from `crop.width` |
| kTargetDpi constant | Replaced by formula | Was 600.0 uniform; now varies 600-900 by crop width |
| Safety caps | Preserved | kMaxScaleFactor=4.0 and kMaxOutputDimension=2000 unchanged |

## Scale Factor Reference Table

| Column | Crop Width | targetDpi | Scale (at 300 DPI render) | Old Scale |
|--------|-----------|-----------|--------------------------|-----------|
| itemNumber | 143px | 814 DPI | 2.71x | 2.0x |
| unit | 206px | 776 DPI | 2.59x | 2.0x |
| quantity | 276px | 734 DPI | 2.45x | 2.0x |
| unitPrice | 333px | 700 DPI | 2.33x | 2.0x |
| bidAmount | 358px | 685 DPI | 2.28x | 2.0x |
| 500px+ | 500px | 600 DPI | 2.00x | 2.0x |
| description | 841px | 600 DPI | 2.00x | 2.0x |

**Edge case — low renderDpi**: At `renderDpi=150`, the formula produces scale factors up to 5.99x, but `kMaxScaleFactor=4.0` caps all columns. The adaptive boost is fully absorbed by the cap. The boost progressively helps fewer columns as renderDpi drops below ~200.

---

## Phase 1: CropUpscaler Code Changes

**Agent**: `pdf-agent`
**Branch**: `feature/geometry-aware-crop-upscaler`
**Files in scope**: `lib/features/pdf/services/extraction/shared/crop_upscaler.dart`

### Task 1.1: Replace uniform DPI constant with adaptive formula

**File**: `lib/features/pdf/services/extraction/shared/crop_upscaler.dart`

#### Constants to change (lines 22-25)

Replace:
```dart
static const double kTargetDpi = 600.0;
```

With:
```dart
/// Base target DPI applied to all crops (floor).
static const double kBaseDpi = 600.0;

/// Additional DPI boost applied to narrow crops (max boost at width=0).
static const double kBoostDpi = 300.0;

/// Crop width (in pixels) at which boost reaches zero.
/// Crops wider than this get kBaseDpi only.
static const double kWidthCeiling = 500.0;
```

Keep unchanged:
```dart
static const double kMaxScaleFactor = 4.0;
static const int kPaddingPixels = 10;
static const int kMaxOutputDimension = 2000;
```

#### Method to change: `computeScaleFactor` (lines 110-128)

Replace the body of `computeScaleFactor`:
```dart
double computeScaleFactor(double renderDpi, int width, int height) {
  if (!renderDpi.isFinite || renderDpi <= 0 || width <= 0 || height <= 0) {
    return 1.0;
  }
  if (renderDpi >= kBaseDpi) {
    // Already at or above base DPI — no upscaling needed, regardless of
    // crop width. Narrow-crop boost only applies when images need
    // upscaling in the first place.
    return 1.0;
  }

  // Continuous curve: narrow crops get higher target DPI.
  // At width=0 → targetDpi = kBaseDpi + kBoostDpi (maximum boost).
  // At width>=kWidthCeiling → targetDpi = kBaseDpi (no boost).
  final boostFraction = (1.0 - width / kWidthCeiling).clamp(0.0, 1.0);
  final targetDpi = kBaseDpi + kBoostDpi * boostFraction;

  final dpiScale = targetDpi / renderDpi;
  final outputCap = min(
    kMaxScaleFactor,
    min(kMaxOutputDimension / width, kMaxOutputDimension / height),
  );
  final maxAllowedScale = outputCap < 1.0 ? 1.0 : outputCap;
  return min(
    dpiScale,
    maxAllowedScale,
  ).clamp(1.0, kMaxScaleFactor).toDouble();
}
```

#### No changes to `prepareForOcr`

The method at line 34 already calls `computeScaleFactor(renderDpi, originalWidth, originalHeight)` where `originalWidth = crop.width`. The variable scale factor flows through to `effectiveDpi: renderDpi * scaleFactor` at line 86 — this now correctly reflects the per-crop effective DPI.

#### No changes to `CropUpscaleResult`

All fields remain the same. `effectiveDpi` and `scaleFactor` will now vary per crop, which is the intended behavior. Downstream consumers (TesseractEngineV2, CropOcrStats) already handle variable values.

### Steps
1. Open `crop_upscaler.dart`
2. Replace `kTargetDpi` constant with `kBaseDpi`, `kBoostDpi`, `kWidthCeiling`
3. Replace `computeScaleFactor` body with adaptive formula
4. Remove any references to `kTargetDpi` (check for compile errors)
5. Run `pwsh -Command "flutter analyze"` — zero issues expected
6. Run `pwsh -Command "flutter test test/features/pdf/extraction/shared/crop_upscaler_test.dart"` — tests WILL FAIL (expected, Phase 2 fixes them)

---

## Phase 2: Update All CropUpscaler-Dependent Tests

**Agent**: `pdf-agent` (same agent, sequential after Phase 1)
**Files in scope**:
- `test/features/pdf/extraction/shared/crop_upscaler_test.dart`
- `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart` (**CRITICAL — found by adversarial review**)

### Task 2.1: Update `crop_upscaler_test.dart` — `computeScaleFactor` assertions

**File**: `test/features/pdf/extraction/shared/crop_upscaler_test.dart`

#### Test: "returns 1.0 when render DPI already meets target" (line 22-25)

Change `kTargetDpi` references to `kBaseDpi`:
```dart
test('returns 1.0 when render DPI already meets target', () {
  expect(upscaler.computeScaleFactor(600, 140, 90), equals(1.0));
  expect(upscaler.computeScaleFactor(720, 140, 90), equals(1.0));
});
```
No assertion changes needed — behavior is identical (renderDpi >= kBaseDpi still returns 1.0).

#### Test: "scales by target DPI ratio for typical crops" (line 27-30)

Update expected values. With width=500 (at widthCeiling), targetDpi=600, so scale=600/300=2.0 — unchanged.
With width=500 at renderDpi=450: targetDpi=600, scale=600/450=1.333 — unchanged.
**No changes needed for this test** since width=500 is exactly at the ceiling.

Add a new test for narrow crops:
```dart
test('scales higher for narrow crops (adaptive DPI boost)', () {
  // width=143 (itemNumber column): targetDpi = 600 + 300 * (1 - 143/500) = 814.2
  // scale = 814.2 / 300 = 2.714
  expect(upscaler.computeScaleFactor(300, 143, 90), closeTo(2.714, 0.001));

  // width=333 (unitPrice column): targetDpi = 600 + 300 * (1 - 333/500) = 700.2
  // scale = 700.2 / 300 = 2.334
  expect(upscaler.computeScaleFactor(300, 333, 90), closeTo(2.334, 0.001));

  // width=500 (at ceiling): targetDpi = 600 + 300 * 0 = 600
  // scale = 600 / 300 = 2.0
  expect(upscaler.computeScaleFactor(300, 500, 90), equals(2.0));

  // width=800 (above ceiling): targetDpi = 600, scale = 2.0
  expect(upscaler.computeScaleFactor(300, 800, 90), equals(2.0));
});
```

#### Test: "caps scale factor by max output dimension" (line 37-41)

Width=800 is above ceiling, so targetDpi=600. **No change needed** — same result as before.

### Task 2.2: Update `crop_upscaler_test.dart` — `prepareForOcr` assertions

#### Test: "item number column crop (140x90) is upscaled with padding" (line 64-85)

Update assertions for variable scale:
```dart
test('item number column crop (140x90) is upscaled with padding', () {
  final crop = createTestCrop(140, 90);
  final result = upscaler.prepareForOcr(crop, renderDpi: 300);

  expect(result.wasUpscaled, isTrue);
  expect(result.usedFallback, isFalse);
  expect(result.warning, isNull);
  expect(result.originalWidth, equals(140));
  expect(result.originalHeight, equals(90));

  // width=140: targetDpi = 600 + 300*(1-140/500) = 816
  // scale = 816/300 = 2.72
  expect(result.scaleFactor, closeTo(2.72, 0.02));
  expect(result.processedWidth, closeTo(381, 2));
  expect(result.processedHeight, closeTo(245, 2));
  expect(
    result.image.width,
    equals(result.processedWidth + CropUpscaler.kPaddingPixels * 2),
  );
  expect(
    result.image.height,
    equals(result.processedHeight + CropUpscaler.kPaddingPixels * 2),
  );
  expect(result.effectiveDpi, closeTo(816.0, 6.0));
});
```

#### Test: "unit column crop (219x90) is upscaled to target DPI" (line 87-94)

Update:
```dart
test('unit column crop (219x90) gets adaptive upscaling', () {
  final crop = createTestCrop(219, 90);
  final result = upscaler.prepareForOcr(crop, renderDpi: 300);

  expect(result.wasUpscaled, isTrue);
  // width=219: targetDpi = 600 + 300*(1-219/500) = 768.6
  // scale = 768.6/300 = 2.562
  expect(result.scaleFactor, closeTo(2.562, 0.02));
  expect(result.effectiveDpi, closeTo(768.6, 6.0));
});
```

#### Test: "description column crop (895x90) is NOT upscaled at target DPI" (line 96-105)

**No changes needed** — renderDpi=600 still returns 1.0 regardless of width.

#### Test: "handles 1x1 crop without error" (line 141-149)

Update: width=1 gives targetDpi=899.4, scale=2.998:
```dart
test('handles 1x1 crop without error', () {
  final crop = img.Image(width: 1, height: 1);
  img.fill(crop, color: img.ColorRgb8(0, 0, 0));
  final result = upscaler.prepareForOcr(crop, renderDpi: 300);

  expect(result.usedFallback, isFalse);
  expect(result.wasUpscaled, isTrue);
  // width=1: targetDpi = 600+300*(1-1/500) = 899.4, scale ~ 3.0
  expect(result.processedWidth, closeTo(3, 1));
  expect(result.processedHeight, closeTo(3, 1));
});
```

### Task 2.3: Update `stage_2b_text_recognizer_test.dart` (ADVERSARIAL REVIEW FIX)

**File**: `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart`

This file has **6 hardcoded assertions** that depend on uniform 2.0x scaling. These MUST be updated or tests will fail silently in CI:

| Line | Current Assertion | New Expected Value | Reason |
|------|-------------------|--------------------|--------|
| ~1453 | `expect(result.scaleFactor, 2.0)` (width=100) | `closeTo(2.84, 0.02)` | width=100: targetDpi=840, scale=2.8 |
| ~1454 | `expect(result.effectiveDpi, 600.0)` (width=100) | `closeTo(840.0, 6.0)` | Follows from new targetDpi |
| ~1455 | `expect(result.processedWidth, 200)` (width=100) | `closeTo(284, 3)` | round(100 * 2.84) |
| ~1518 | `expect(result.image.width, 22)` (1x1 crop) | `closeTo(23, 1)` | 1×~3.0 + 20 padding |
| ~1614 | `expect(mockEngine...width, 360)` (width=170) | `closeTo(452, 5)` | width=170: targetDpi=798, scale=2.66 |
| ~1616 | `expect(mockEngine...effectiveDpi, 600.0)` (width=170) | `closeTo(798.0, 6.0)` | Follows from new targetDpi |

**Note**: Lines ~1553 and ~1556 test width=800 crops (above ceiling) and still pass unchanged.

The implementing agent MUST read the actual test file to find exact line numbers, as they may have shifted since this plan was written.

### Steps
1. Open `crop_upscaler_test.dart` — update per Tasks 2.1 and 2.2
2. Open `stage_2b_text_recognizer_test.dart` — update per Task 2.3
3. Run `pwsh -Command "flutter test test/features/pdf/extraction/shared/crop_upscaler_test.dart"` — all pass
4. Run `pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart"` — all pass
5. Run `pwsh -Command "flutter analyze"` — zero issues

---

## Phase 3: Regenerate Golden Fixtures

**Agent**: `qa-testing-agent` (requires physical PDF file on disk)
**Files in scope**: `test/features/pdf/extraction/fixtures/` (all JSON files)
**Prerequisite**: Phases 1-2 complete and passing

### Task 3.1: Count fixture files before regeneration

Record the number of `springfield_*.json` files in the fixtures directory. After regeneration, verify the count is unchanged. A count mismatch indicates something unexpected in the pipeline.

### Task 3.2: Regenerate Springfield fixtures

The fixture generator re-runs the full pipeline with the updated CropUpscaler and writes new JSON fixtures.

**Command**:
```
pwsh -Command "flutter test integration_test/generate_golden_fixtures_test.dart -d windows --dart-define='SPRINGFIELD_PDF=C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf'"
```

**Expected fixture changes in `springfield_ocr_metrics.json`**:
- `avg_scale_factor`: 2.0 → ~2.3 (varies by column width distribution)
- `max_scale_factor`: 2.0 → ~2.71 (itemNumber column at 143px)
- `avg_ocr_width`: 784 → ~900+ (wider OCR images for narrow columns)
- `min_ocr_width`: 306 → ~388 (143px * 2.71x + 20px padding)
- `cells_upscaled`: 822 (unchanged — all cells still upscaled)
- `cells_skipped_upscale`: 0 (unchanged)
- Per-column upscale rates: all still 100% (all 6 columns still upscaled)

### Task 3.3: Verify fixture file count unchanged

Compare count of `springfield_*.json` files against pre-regeneration count from Task 3.1.

### Task 3.4: Run scorecard and verify no regression

**Command**:
```
pwsh -Command "flutter test test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart"
```

**Scorecard baseline**: 68 OK / 3 LOW / 0 BUG
**Acceptable outcomes**:
- Same or better (e.g., 69 OK / 2 LOW / 0 BUG) — PASS
- Same (68 OK / 3 LOW / 0 BUG) — PASS
- Any increase in BUG count — FAIL, requires investigation

**What to watch for**:
1. `B5 upscale uniformity` metric: Checks upscale RATE (upscaled/total), NOT scale factor magnitude. All columns still upscaled → should remain OK.
2. `B6 math consistency`: Should improve or stay same (better OCR on narrow numeric columns)
3. **Items count: Must remain 131.** Any drop indicates BLOCKER-16 regression.
4. **Item 121 unitPrice**: Currently value=null, conf=0.555. Watch for improvement.
5. **BLOCKER-16 regression guard — Item 50**: Verify item 50 is intact with description containing "Valve" and correct bid amount. This was the specific item that merged in BLOCKER-16.

### Steps
1. Count fixture files before regeneration
2. Run fixture generator with Springfield PDF
3. Verify fixtures were written (check file timestamps) and count unchanged
4. Run scorecard test
5. Capture scorecard output, compare against baseline
6. If BUG count increased or item count < 131, STOP and report regression
7. If scorecard same or improved, proceed

---

## Phase 4: Update Stage Trace Tests (if needed)

**Agent**: `qa-testing-agent`
**Files in scope**: `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`

### Task 4.1: Verify B5 upscale uniformity metric still works

The B5 metric at line 3158-3195 checks deviation of upscale **rates** (upscaled_count / total_count per column), NOT scale factor values. Since all columns still get upscaled, rates remain 100% for all 6 columns, and deviation stays 0%. **No changes expected.**

### Task 4.2: Verify OCR metrics fixture format is unchanged

The fixture `springfield_ocr_metrics.json` format is produced by `CropOcrStats.cropDimensionMetrics` and `CropOcrStats.upscalingMetrics`. Neither method changes schema — only the VALUES change. **No test format changes needed.**

### Task 4.3: Update any hardcoded assertions in stage trace tests

Search the stage trace test for any hardcoded assertions that reference:
- `avg_scale_factor` == 2.0
- `max_scale_factor` == 2.0
- `avg_ocr_width` == 784

If found, update to match new values from regenerated fixtures. If these values are only printed (not asserted), no changes needed.

### Steps
1. Run `pwsh -Command "flutter test test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart"` with fixtures from Phase 3
2. If all tests pass, Phase 4 is complete (no changes needed)
3. If assertions fail on hardcoded OCR metrics values, update to match new fixture values
4. Re-run tests to confirm pass

---

## Files Modified (Summary)

| File | Change | Phase |
|------|--------|-------|
| `lib/features/pdf/services/extraction/shared/crop_upscaler.dart` | Replace `kTargetDpi` with `kBaseDpi`/`kBoostDpi`/`kWidthCeiling`; update `computeScaleFactor` with continuous curve formula | 1 |
| `test/features/pdf/extraction/shared/crop_upscaler_test.dart` | Update scale factor assertions for variable upscaling; add new narrow-crop test | 2 |
| `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart` | Update 6 hardcoded scale/DPI/width assertions for variable upscaling | 2 |
| `test/features/pdf/extraction/fixtures/*.json` | Regenerated by fixture generator (~30 files) | 3 |
| `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart` | Only if hardcoded OCR metric assertions exist (likely none) | 4 |

**Files NOT modified** (explicit exclusions):
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart` — no changes needed; it already passes `crop.width` to CropUpscaler via the crop image, and coordinate mapping handles variable scale factors
- `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart` — already accepts variable `effectiveDpi`
- `lib/features/pdf/services/extraction/ocr/crop_ocr_stats.dart` — already tracks variable scale factors (accumulates `_totalScaleFactor` and `_maxScaleFactor` independently, no uniformity assumption)
- Post-processor, confidence scoring, row parser — no changes

---

## Risk Assessment

### Risk 1: BLOCKER-16 Regression (Item Merger)
**Likelihood**: LOW
**Rationale**: The continuous curve produces scale factors of 2.28x-2.71x for narrow columns (vs the 500px hard threshold that forced all narrow columns to 500px output width). The key difference: this approach changes scale uniformly across the crop without changing crop boundaries. BLOCKER-16 was caused by `kMinCropWidth=500` changing the crop REGION to be wider, capturing adjacent cell content (confirmed in `_defects-pdf.md`). Here, crop boundaries stay identical — only the upscale ratio changes.
**Mitigation**: Phase 3 scorecard check. If items < 131, STOP immediately. Check item 50 specifically (BLOCKER-16 regression guard).

### Risk 2: Memory Impact from Larger Crops
**Likelihood**: LOW
**Impact**: Cells are processed sequentially in a `for` loop (text_recognizer_v2.dart:355). Peak concurrent memory is 1-2 crops + the decoded page image, NOT all cells simultaneously. The narrowest column (143px) goes from 280px to ~388px output — each crop is ~388×244×4 = ~378KB. With only 1 crop in flight, this is trivially safe. The actual memory concern is the decoded full-page image (~4MB for Springfield), which is unchanged.
**Mitigation**: kMaxOutputDimension=2000 cap preserved. kMaxScaleFactor=4.0 cap preserved.

### Risk 3: Variable effectiveDpi Impact on Tesseract
**Likelihood**: LOW-MEDIUM
**Rationale**: The change passes variable `effectiveDpi` (685-814 DPI instead of uniform 600 DPI) to Tesseract. Tesseract uses DPI to estimate character sizes, so changing DPI can change which characters are recognized — potentially for better OR worse. The scorecard is the primary safety net. If OCR quality degrades on specific items despite higher DPI, that would indicate Tesseract is sensitive to DPI metadata in unexpected ways.
**Mitigation**: Phase 3 scorecard check validates overall quality. Per-item comparison in Phase 3 Task 3.4.

### Risk 4: Scorecard B5 "Upscale Uniformity" Metric
**Likelihood**: NONE
**Rationale**: B5 checks upscale RATE (fraction of cells upscaled per column), not scale factor magnitude. All columns still get upscaled (scale > 1.0 at renderDpi=300), so the rate remains 100% for all columns, and deviation stays 0%.

### Risk 5: Low renderDpi Nullifies Boost
**Likelihood**: LOW (edge case)
**Rationale**: At `renderDpi=150`, all columns hit the `kMaxScaleFactor=4.0` cap regardless of width. The adaptive boost is fully absorbed. Between `renderDpi=150-250`, the boost progressively helps fewer columns. This is acceptable because low-DPI renders have bigger quality problems than crop sizing. Document this limitation but don't try to solve it.

---

## Verification Criteria

1. **Unit tests pass**: `pwsh -Command "flutter test test/features/pdf/extraction/shared/crop_upscaler_test.dart"` — all pass
2. **Text recognizer tests pass**: `pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart"` — all pass
3. **Static analysis clean**: `pwsh -Command "flutter analyze"` — zero issues
4. **Scorecard no regression**: 68+ OK / 3- LOW / 0 BUG (same or better than baseline)
5. **Item count preserved**: Springfield extraction still produces 131 items
6. **BLOCKER-16 guard**: Item 50 intact with correct description and bid amount
7. **Scale factors correct**: In regenerated `springfield_ocr_metrics.json`:
   - `avg_scale_factor` > 2.0 (confirms variable upscaling is active)
   - `max_scale_factor` ~ 2.71 (confirms boost applied to narrowest column)
   - `min_ocr_width` > 306 (confirms narrow columns get more upscaling)
8. **No API changes**: `CropUpscaler.prepareForOcr` signature unchanged
9. **No downstream breakage**: TextRecognizerV2, TesseractEngineV2, CropOcrStats all work without code changes
10. **Fixture count unchanged**: Same number of `springfield_*.json` files before and after regeneration

---

## Rollback Plan

If regression is detected after Phase 3:

1. **Immediate**: Revert `crop_upscaler.dart` to restore `kTargetDpi=600.0` and uniform `computeScaleFactor`
2. **Tests**: Revert `crop_upscaler_test.dart` and `stage_2b_text_recognizer_test.dart` to original assertions
3. **Fixtures**: Regenerate golden fixtures with the reverted code
4. **Verify**: Run scorecard, confirm 68 OK / 3 LOW / 0 BUG restored

The revert is safe because:
- Only 3 files changed (1 production, 2 test)
- Fixtures are auto-generated, not hand-edited
- No API changes means no downstream code depends on the new constants

---

## Agent Dispatch Plan

This is a **sequential** workflow (NOT parallel) because each phase depends on the previous:

| Phase | Agent | Depends On | Files |
|-------|-------|------------|-------|
| 1 | `pdf-agent` | None | `crop_upscaler.dart` |
| 2 | `pdf-agent` | Phase 1 | `crop_upscaler_test.dart`, `stage_2b_text_recognizer_test.dart` |
| 3 | `qa-testing-agent` | Phase 2 + Springfield PDF on disk | `fixtures/*.json` |
| 4 | `qa-testing-agent` | Phase 3 | `stage_trace_diagnostic_test.dart` |

**Do NOT dispatch parallel agents** — Phase 2 modifies test assertions that depend on Phase 1 code changes, and Phase 3 regenerates fixtures that depend on Phase 1+2 being correct.

---

## Adversarial Review Log

The following corrections were applied from the adversarial review:

| # | Finding | Severity | Action Taken |
|---|---------|----------|-------------|
| 1 | `stage_2b_text_recognizer_test.dart` missing from plan — 6 assertions will break | CRITICAL | Added Task 2.3, added to Files Modified table, updated rollback plan |
| 2 | Memory analysis claims "6 cells" but cells process sequentially | IMPORTANT | Rewrote Risk 2 with correct reasoning (1 crop in flight) |
| 3 | No documentation of formula inertness at `renderDpi >= 600` | IMPORTANT | Added limitation note in Overview, added Risk 5 |
| 4 | Variable effectiveDpi impact on Tesseract not assessed | IMPORTANT | Added Risk 3 (LOW-MEDIUM) |
| 5 | No fixture count verification | SUGGESTED | Added Task 3.1, Task 3.3, Verification Criteria #10 |
| 6 | No BLOCKER-16 regression guard for item 50 | SUGGESTED | Added to Phase 3 Task 3.4 watchlist, Verification Criteria #6 |
| 7 | `computeScaleFactor` comment could be clearer | MINOR | Updated comment at renderDpi >= kBaseDpi check |

---

## BLOCKER-16 Defect Update

After successful completion, update `.claude/defects/_defects-pdf.md`:
- Change BLOCKER-16 status from OPEN to RESOLVED
- Add resolution note: "Fixed with continuous curve formula (kBaseDpi=600, kBoostDpi=300, kWidthCeiling=500) instead of hard kMinCropWidth=500 threshold"
- Record new scorecard baseline
