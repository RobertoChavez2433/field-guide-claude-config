# Plan: Cell Crop Upscaling for OCR Quality

**Date**: 2026-02-15
**Phase**: Pipeline Accuracy Improvement — OCR Text Quality
**Prerequisite**: Grid detection working (6/6 pages), cell cropping working (150+ data rows)

## Problem Statement

Cell crops from the 300 DPI full-page render are too small for Tesseract:

| Column | Crop Width (px) | Char Height (px) | Effective DPI |
|--------|-----------------|-------------------|---------------|
| Item No. (5.6%) | ~143 | ~10-15 | 18 |
| Description (35%) | ~895 | ~20 | 75 |
| Unit (8.6%) | ~220 | ~12-18 | 30 |
| Quantity (11.5%) | ~294 | ~15-20 | 40 |
| Unit Price (13.9%) | ~355 | ~15-20 | 47 |
| Amount (14.9%) | ~381 | ~15-20 | 50 |

Tesseract needs **25-35px cap-height** for reliable recognition. Our narrow columns are at 10-15px.

## Solution: Bicubic Upscale + White Padding Before OCR

Research consensus: render full page at 300 DPI (keep current), upscale individual cell crops to target 30px cap-height using bicubic interpolation, add 10px white border padding.

## Implementation Phases

---

### Phase 1: Core Upscaling Logic in TextRecognizerV2

**File**: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`

**Location**: Between lines 335-342 (after `img.copyCrop`, before `img.encodePng`)

**Changes**:

1. **Add `_upscaleCropForOcr()` method** — Takes a cropped `img.Image`, returns upscaled `img.Image`:
   - Compute scale factor: `targetMinDimension / min(cropWidth, cropHeight)`
   - Clamp scale factor: minimum 1.0 (no downscale), maximum 4.0 (avoid over-enlargement)
   - Skip upscale if both dimensions already >= threshold (e.g., width >= 300 AND height >= 40)
   - Use `img.copyResize()` with `interpolation: img.Interpolation.cubic`

2. **Add `_addWhitePadding()` method** — Adds 10px white border:
   - Create new `img.Image(width: w+20, height: h+20)` filled white
   - Composite the upscaled crop at offset (10, 10)
   - This prevents Tesseract from struggling with text touching image edges

3. **Update `_recognizeWithCellCropping()` loop** (line 335-342):
   ```
   // BEFORE (current):
   final cropped = img.copyCrop(decodedImage, x, y, w, h);
   final cropBytes = Uint8List.fromList(img.encodePng(cropped));

   // AFTER:
   final cropped = img.copyCrop(decodedImage, x, y, w, h);
   final upscaled = _upscaleCropForOcr(cropped);
   final padded = _addWhitePadding(upscaled);
   final cropBytes = Uint8List.fromList(img.encodePng(padded));
   ```

4. **Update width/height passed to `engine.recognizeCrop()`** — Must use padded dimensions, not original crop dimensions. The coordinate mapping back to page-space uses `cropRegionNormalized` (unchanged), so the page-level coordinates remain correct.

5. **Track upscaling metrics** in the existing metrics map:
   - `cells_upscaled`: count of cells that needed upscaling
   - `avg_scale_factor`: average scale factor applied
   - `cells_skipped_upscale`: cells already large enough

**Configuration constants** (top of class or as static members):
```dart
static const int kMinCropWidth = 300;    // Minimum width in pixels for OCR
static const int kMinCropHeight = 40;    // Minimum height in pixels for OCR
static const double kMaxScaleFactor = 4.0;
static const int kPaddingPixels = 10;
```

**Fail parameters**:
- If upscaling produces an image > 2000x2000, log warning and cap at 4x
- If `img.copyResize` fails, fall back to un-upscaled crop (log warning, don't crash)

---

### Phase 2: Unit Tests for Upscaling Logic

**File**: `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart`

**New test group**: `'TextRecognizerV2 - Cell Crop Upscaling'`

**Tests** (using synthetic images, no mocks needed for the upscaling logic itself):

1. **Small crop gets upscaled** — 100x30 crop → verify output dimensions >= kMinCropWidth x kMinCropHeight
2. **Large crop NOT upscaled** — 500x80 crop → verify output dimensions unchanged (plus padding)
3. **Scale factor capped at 4x** — 20x10 crop → verify output <= 80x40 (before padding)
4. **Padding adds exactly 20px** — Any crop → verify width+20, height+20
5. **Very narrow column** — 50x60 crop (narrow but tall) → verify upscaled proportionally
6. **Very short row** — 300x15 crop (wide but short) → verify upscaled proportionally
7. **1x1 edge case** — Degenerate crop → verify no crash, skip or minimal output
8. **Interpolation quality** — Create a synthetic image with known text pattern, upscale, verify no artifacts destroy the pattern (visual regression)

**Test approach**: Create synthetic grayscale PNG images with `img.Image()`, run through `_upscaleCropForOcr()` and `_addWhitePadding()`, verify dimensions and pixel values.

**Note**: To test private methods, either:
- (a) Extract upscaling to a public utility class (e.g., `CropUpscaler`) in `shared/`
- (b) Test indirectly through `recognize()` with mock OCR engine that captures input dimensions

**Recommendation**: Option (a) — extract to `CropUpscaler` utility class. This keeps TextRecognizerV2 focused on orchestration and makes the upscaling testable in isolation.

---

### Phase 3: Measurement Infrastructure

**Goal**: Quantify the before/after impact on OCR quality at every level.

#### 3A: Add crop-level diagnostics to StageReport metrics

In `text_recognizer_v2.dart`, extend the existing metrics map:

```dart
'crop_dimensions': {
  'min_width': minCropWidth,
  'max_width': maxCropWidth,
  'min_height': minCropHeight,
  'max_height': maxCropHeight,
  'avg_width': avgCropWidth,
  'avg_height': avgCropHeight,
},
'upscaling': {
  'cells_upscaled': cellsUpscaled,
  'cells_skipped': cellsSkippedUpscale,
  'avg_scale_factor': avgScaleFactor,
  'max_scale_factor': maxScaleFactor,
},
```

#### 3B: Update stage_trace_diagnostic_test.dart

Add a new test in the "Stage-by-Stage Pipeline Trace" group for text recognition upscaling analysis:

- Print crop dimension distribution (histogram by column)
- Print upscaling stats (how many cells upscaled, by how much)
- Print per-column OCR confidence before/after (from unified_elements)
- Compare against previous fixture baseline

#### 3C: Extend GoldenFileMatcher reporting

The existing `GoldenFileMatcher` already tracks:
- `matchRate` — % of expected items found
- `allFieldsMatch` — per-field fuzzy matching

Add to the diagnostic output:
- **Per-field accuracy breakdown**: item_number accuracy, description accuracy, unit accuracy, quantity accuracy, unit_price accuracy, bid_amount accuracy
- **Confidence distribution**: histogram of OCR confidences (0-0.2, 0.2-0.4, ..., 0.8-1.0)

---

### Phase 4: Fixture Regeneration & Baseline Comparison

**Process** (same as Session 346):

1. Run `generate_fixtures_test.dart` integration test with real Springfield PDF
2. This regenerates all 10 fixture JSON files
3. Run `stage_trace_diagnostic_test.dart` to analyze new fixtures
4. Run `springfield_golden_test.dart` to compare against ground truth

**Before/After Scoreboard** (update in `_state.md`):

| Metric | Before (Session 346) | After | Target |
|--------|---------------------|-------|--------|
| Grid pages detected | 6/6 | 6/6 | 6 |
| Columns detected | 8 | — | 6-8 |
| Data rows classified | 150 | — | ~131 |
| Parsed items (pre-dedup) | 78 | — | 131 |
| Final items (post-dedup) | 3 | — | 131 |
| Total amount | $0 | — | $7,882,926.73 |
| Quality score | 0.570 | — | >= 0.85 |
| Median OCR confidence | 0.364 | — | >= 0.80 |
| Ground truth match rate | ~0% | — | >= 80% |

**Pass criteria for this phase**:
- Median OCR confidence improves (currently 0.364 → target >= 0.50)
- Parsed items (pre-dedup) increases (currently 78 → target >= 78, no regression)
- At least some item numbers are now recognizable (currently 0)
- At least some descriptions contain readable text (currently garbage)

**Fail criteria** (revert and investigate):
- Median OCR confidence decreases
- Fewer parsed items than before
- Pipeline crashes or timeouts
- Memory usage causes test OOM

---

### Phase 5: Dedup Investigation (Contingent)

If upscaling improves OCR text quality but dedup still removes too many items:

1. Examine post-processing dedup logic
2. Check if items now have distinct text (not all identical garbage)
3. If dedup is still over-filtering, tune thresholds in a separate follow-up

This is out of scope for this plan but noted as the next step.

---

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `lib/.../stages/text_recognizer_v2.dart` | MODIFY | Add upscaling + padding to cell crop loop |
| `lib/.../shared/crop_upscaler.dart` | NEW | Extracted upscaling utility (testable) |
| `test/.../stages/stage_2b_text_recognizer_test.dart` | MODIFY | Add upscaling unit tests |
| `test/.../golden/stage_trace_diagnostic_test.dart` | MODIFY | Add upscaling metrics analysis |
| Fixture JSON files (10 files) | REGENERATE | Via integration test |

## Agent Assignments

| Phase | Agent | Action |
|-------|-------|--------|
| 1 | frontend-flutter-specialist-agent | Implement CropUpscaler + integrate |
| 2 | qa-testing-agent | Write unit tests |
| 3A-3B | frontend-flutter-specialist-agent | Metrics + diagnostic updates |
| 3C | qa-testing-agent | GoldenFileMatcher enhancements |
| 4 | Manual (integration test) | Fixture regeneration |
| 4 | code-review-agent | Review all changes |

## Risks

1. **Upscaling may not be enough** — If pdfx renders at low quality (blurry source), upscaling blurry pixels won't help. Mitigation: check rendered image quality in diagnostic test first.
2. **Memory pressure** — Many cells × 4x upscale could increase memory. Mitigation: process cells sequentially (current pattern), discard upscaled image after OCR.
3. **Coordinate mapping** — Must ensure upscaled+padded dimensions don't corrupt the crop→page coordinate transform. Mitigation: coordinate mapping uses `cropRegionNormalized` (unchanged by upscaling), so this should be safe.
4. **Performance** — Upscaling adds time per cell. For 150 rows × 8 columns = 1200 cells, even 5ms/cell = 6 seconds. Acceptable for accuracy improvement.
