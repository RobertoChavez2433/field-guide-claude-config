# DPI-Target Upscaling + Pipeline Observability

**Created**: 2026-02-19 (Session 389, Brainstorming)
**Status**: DESIGNED — awaiting approval
**Blocker**: BLOCKER-8 (CropUpscaler threshold too low)

## Overview

### Problem
CropUpscaler uses a pixel-width threshold (`kMinCropWidth=300`) that lets currency columns (355-381px) escape upscaling. All 16 OCR errors are in these non-upscaled columns. The scorecard reports 55 OK / 0 LOW / 0 BUG because post-processing silently corrects the errors.

### Solution
1. Replace pixel-width threshold with DPI-target scaling (`targetDpi=600`)
2. Fix broken `sourceDpi` metric in TesseractEngineV2
3. Add 5 observability metrics to the scorecard so silent failures become visible

### Success Criteria
- [ ] All cell crops upscaled to 600 effective DPI
- [ ] `sourceDpi` reports actual effective DPI, not crop-pixels/page-points
- [ ] 855+ extraction tests green
- [ ] After fixture regen: scorecard maintains 0 LOW / 0 BUG (or improves)
- [ ] New metrics would have flagged the 16 OCR errors if they existed before the fix

---

## Part A: DPI-Target Upscaling

### A1. CropUpscaler Changes

**File**: `lib/features/pdf/services/extraction/shared/crop_upscaler.dart`

**Constants — Replace**:
```dart
// REMOVE:
static const int kMinCropWidth = 300;
static const int kMinCropHeight = 40;

// ADD:
static const double kTargetDpi = 600.0;
```

**Constants — Keep**:
```dart
static const double kMaxScaleFactor = 4.0;
static const int kPaddingPixels = 10;
static const int kMaxOutputDimension = 2000;
```

**API Change**:
```dart
// Before:
CropUpscalerResult prepareForOcr(img.Image crop)
double computeScaleFactor(int width, int height)

// After:
CropUpscalerResult prepareForOcr(img.Image crop, {required double renderDpi})
double computeScaleFactor(double renderDpi, int width, int height)
```

**New `computeScaleFactor` Logic**:
```dart
double computeScaleFactor(double renderDpi, int width, int height) {
  if (renderDpi >= kTargetDpi) return 1.0;

  final dpiScale = kTargetDpi / renderDpi;  // e.g., 600/300 = 2.0

  final outputCap = min(
    kMaxScaleFactor,
    min(kMaxOutputDimension / width, kMaxOutputDimension / height),
  );

  return min(dpiScale, outputCap).clamp(1.0, kMaxScaleFactor);
}
```

**Result Metadata** — Add `effectiveDpi` to `CropUpscalerResult`:
```dart
final double effectiveDpi;  // renderDpi * actualScaleFactor
```

### A2. TextRecognizerV2 Plumbing

**File**: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`

**Change**: Pass `renderDpi` from `PreprocessedPage` (or pipeline config) to `_cropUpscaler.prepareForOcr()`.

- The render DPI is set in `ExtractionPipeline` (default 300, retry 400)
- `PreprocessedPage` should carry a `renderDpi` field (or it's passed as a parameter to `TextRecognizerV2.process()`)
- At the call site (line 385): `_cropUpscaler.prepareForOcr(cropped, renderDpi: renderDpi)`

**Check**: `PreprocessedPage` — does it already carry DPI info? If not, add a `double renderDpi` field. The pipeline creates `PreprocessedPage` objects and knows the render DPI.

### A3. sourceDpi Fix in TesseractEngineV2

**File**: `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart`

**Current Bug** (lines 273-285): Computes `72 * (cropPixels / pagePoints)` for crop-based OCR, yielding nonsensical 27-31 DPI. The page dimensions in points are unrelated to the crop dimensions in pixels.

**Fix Options** (choose during implementation):
1. **Pass `effectiveDpi` from CropUpscaler result** — Most accurate. The `effectiveDpi = renderDpi * scaleFactor` from CropUpscaler tells the true story.
2. **Pass `renderDpi` directly** — Simpler but doesn't reflect upscaling.

**Recommended**: Option 1. The `sourceDpi` in `CoordinateMetadata` should reflect the effective DPI after upscaling. The caller already has the `CropUpscalerResult.effectiveDpi`.

**Change**: Add `double? effectiveDpi` parameter to `recognizeCrop()`. If provided, use it instead of computing from crop/page dimensions.

### A4. Expected Impact on Springfield PDF

| Column | Current | After (renderDpi=300) |
|--------|---------|----------------------|
| itemNumber (143px) | 2.1x → 300px | 2.0x → 286px |
| description (896px) | 1.0x (no scale) | 2.0x → 1792px |
| unit (220px) | 1.4x → 300px | 2.0x → 440px |
| quantity (294px) | 1.02x → 300px | 2.0x → 588px |
| unitPrice (355px) | **1.0x (no scale)** | **2.0x → 710px** |
| bidAmount (381px) | **1.0x (no scale)** | **2.0x → 762px** |

- unitPrice and bidAmount now get 2x upscaling (currently 1.0x)
- Expected: most/all of the 16 OCR errors eliminated
- Description column upscale from 896→1792 is well within 2000 cap
- Performance: ~50-100ms additional per page (interpolation cost on larger images)

---

## Part B: Pipeline Observability (5 New Metrics)

### B1. Interpretation Pattern Alarm (Scorecard Row)

**What**: Count non-standard interpretation patterns per column. If >5% of cells in any column use a correction pattern (e.g., `european_periods`, `corrupted_symbol`), flag as LOW. If >15%, flag as BUG.

**Where**: Stage 4D.5 (Numeric Interpreter output). Data already exists in `interpreted_grid` fixture — each cell has `matched_pattern`.

**Implementation**:
- In the scorecard test, after loading `springfield_interpreted_grid.json`, iterate rows/columns
- Count cells where `matched_pattern` is a correction pattern (not `standard_us`, `no_comma_us`, `plain_numeric`, `text_pass_through`)
- Group by column semantic (unitPrice, bidAmount, etc.)
- Add scorecard row: `| 4D.5 | Correction patterns | <=5%/col | <actual> | % | OK/LOW/BUG |`

**Catches**: Springfield had 11 `european_periods` in unitPrice = 8.4% → LOW

### B2. Per-Field Confidence Checks (Scorecard Row)

**What**: Check that no field's mean confidence is significantly below others. Flag if any field is >0.10 below the median of all fields.

**Where**: Stage 4E.5 (Field Confidence). Data exists in `springfield_field_confidence.json` as `mean_field_confidence` per field.

**Implementation**:
- In the scorecard test, after loading field confidence data
- Compute median of all 6 field mean confidences
- Flag any field with mean_confidence > 0.10 below median as BUG, > 0.05 as LOW
- Add scorecard row: `| 4E.5 | Per-field conf gap | <=0.05 | bidAmount: -0.114 | n/a | BUG |`

**Catches**: bidAmount 0.846 vs median ~0.960 = 0.114 gap → BUG

### B3. Re-OCR Effectiveness (Scorecard Row)

**What**: Check re-OCR attempt/success ratio. Flag if attempts > 0 and success rate < 50%.

**Where**: Stage 2B-iii (OCR). Data exists in `springfield_ocr_metrics.json` as `re_ocr_attempts` and `re_ocr_successes`.

**Implementation**:
- In the scorecard test, read `re_ocr_attempts` and `re_ocr_successes` from OCR metrics
- If attempts > 0 and success rate < 50%, flag as LOW
- If attempts > 0 and success rate = 0%, flag as BUG (re-OCR is completely ineffective)
- Add scorecard row: `| 2B-iii | Re-OCR success | >=50% | 0/1 | 0% | BUG |`

**Catches**: Springfield had 1 attempt, 0 successes → BUG

**NOTE**: After Part A's upscaling fix, the 16 OCR errors may be eliminated, meaning re-OCR may not trigger at all. In that case `attempts=0` and we skip this check. This metric is forward-looking — it catches future PDFs where re-OCR fires but fails.

### B4. Post-Processing Recovery Count (Scorecard Row)

**What**: Count items where the final value differs from what standard_us parsing alone would produce — items that required a correction pattern to parse.

**Where**: Stage 4D.5. Derivable from `interpreted_grid.json` by counting cells with non-standard `matched_pattern` in numeric columns.

**Implementation**:
- Similar to B1 but focuses on the aggregate count, not per-column distribution
- Count total numeric cells (qty + unitPrice + bidAmount) with correction patterns
- If recovery rate > 10% of total numeric cells, flag as LOW
- Add scorecard row: `| 4D.5 | Recovery rate | <=10% | 14/393 | 3.6% | OK |`

**Catches**: Provides the "how many errors were silently fixed" number. Combined with B1 (which catches per-column spikes), this gives the aggregate view.

### B5. Upscale Coverage per Column (OCR Metrics + Scorecard)

**What**: Track upscale rate per column index. Flag if any column has dramatically lower upscale rate than others (suggests a threshold gap).

**Where**: Stage 2B-iii (TextRecognizerV2 `_CropOcrStats`).

**Implementation — Production Code**:
- Add `Map<int, int> upscaledPerColumn` and `Map<int, int> totalPerColumn` to `_CropOcrStats`
- In the cell OCR loop, after CropUpscaler runs, increment the appropriate counter
- Emit per-column upscale rates in OCR metrics output

**Implementation — Scorecard Test**:
- Read per-column upscale rates from `springfield_ocr_metrics.json`
- Flag if any column's upscale rate deviates by >50% from the median rate
- Add scorecard row: `| 2B-iii | Upscale uniformity | uniform | col4:0%, col5:0% | n/a | LOW |`

**After Part A**: With DPI-target scaling, ALL columns will be upscaled at 2.0x (since render DPI = 300 < target 600). Upscale rate per column = 100% for all. This metric becomes useful for catching future regressions or edge cases.

---

## Implementation Phases

### Phase 1: CropUpscaler DPI-Target (A1-A4)
**Agent**: `frontend-flutter-specialist-agent` (Dart code changes)
**Files**:
- `lib/features/pdf/services/extraction/shared/crop_upscaler.dart`
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
- `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart`
- `test/features/pdf/extraction/stages/crop_upscaler_test.dart`
- `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart`

**Verification**: `flutter test test/features/pdf/extraction/` — all green

### Phase 2: Observability Metrics (B1-B5)
**Agent**: `frontend-flutter-specialist-agent` (production code) + `qa-testing-agent` (scorecard additions)
**Files**:
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart` (B5 — per-column tracking)
- `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart` (B1-B5 — new scorecard rows)
- Possibly `lib/features/pdf/services/extraction/stages/quality_validator.dart` if we embed metrics there

**Verification**: Scorecard test with new assertions (initially these may flag LOW/BUG on stale fixtures)

### Phase 3: Fixture Regeneration + Final Validation
**Agent**: Manual (fixture regen requires PDF file) + `qa-testing-agent`
**Steps**:
1. Regenerate Springfield fixtures with the new CropUpscaler logic
2. Run scorecard — expect improved OCR quality in cols 4+5
3. The new observability metrics should show improvement:
   - B1 (pattern alarm): fewer correction patterns if OCR is better
   - B2 (per-field confidence): bidAmount confidence should improve
   - B3 (re-OCR): may not trigger at all if errors are eliminated
   - B4 (recovery count): should decrease
   - B5 (upscale coverage): all columns at 100% upscale rate
4. Verify all 855+ extraction tests green
5. Update scorecard baseline in `_state.md`

---

## Verification Criteria

| Check | Expected |
|-------|----------|
| `flutter test test/features/pdf/extraction/` | All green |
| Scorecard after fixture regen | 0 BUG, <=2 LOW (new metrics may flag pre-existing issues) |
| bidAmount mean confidence | > 0.90 (currently 0.846) |
| OCR errors in cols 4+5 | Reduced from 16 (ideally 0) |
| `effectiveDpi` logged per crop | 600.0 for all crops at 300 DPI render |
| `sourceDpi` in TesseractEngineV2 | Correct effective DPI (not 27-31) |
| Per-column upscale rate | 100% for all columns at 300 DPI render |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Description column (896→1792px) may change OCR behavior | Monitor; bicubic at 2x is within optimal range. Revert if description accuracy drops. |
| Larger crops = more memory per page | Capped at 2000px. 6 columns × ~700px avg × 20 rows = ~84MB/page. Acceptable. |
| Existing tests assert on specific scale factors | Update tests to use DPI-based expectations |
| New observability metrics may flag pre-existing issues on OTHER fixtures | Expected — these are real issues being surfaced. Triage after. |
