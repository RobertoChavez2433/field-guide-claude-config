# Cell-Level OCR Using Grid Line Boundaries

## Context

The PDF extraction pipeline's OCR stage (Stage 2B-iii) currently crops full-width row strips (~3050px) between horizontal grid lines and runs Tesseract PSM 7 on them. PSM 7 ("single text line") on these wide strips fails because:

- Grid lines are read as `|`, `[`, `]` characters (e.g., "8" becomes "||8")
- ~65% of text is dropped (2.1 elements/row instead of ~6)
- Narrow columns (item number = 170px, unit, quantity) are missed entirely

The strip images themselves are perfectly clear and readable. The problem is purely Tesseract's interpretation of full-row strips containing grid lines.

**Previous attempt at cell cropping failed** because crops cut INTO grid lines, causing fragmented header text ("IB" instead of "Item No."). This plan fixes that with a grid line inset.

## Approach

Crop individual cells between grid lines (excluding grid line pixels via inset), then run PSM 7 on each cell. This is what PSM 7 was designed for: a single text value in a focused image.

**Scope**: Almost entirely in `TextRecognizerV2`. Downstream stages consume `List<OcrElement>` with normalized bounding boxes, so no downstream changes needed.

## Files to Modify

| File | Change |
|------|--------|
| `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart` | Add `_CellCrop`, `_computeCellCrops()`, `_recognizeWithCellCrops()`, switch dispatch |
| `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart` | Update crop count expectations, add cell-level tests |

**No changes needed**: `crop_upscaler.dart` (already handles cell-sized crops), `coordinate_normalizer.dart` (reuse `fromCropRelative()`), `cell_extractor_v2.dart` (works as-is), `extraction_pipeline.dart` (calls `textRecognizer.recognize()` unchanged).

## Implementation Steps

### Step 1: Add `_CellCrop` model and `_gridLineInset` constant

Private class alongside existing `_RowStrip`:
```dart
class _CellCrop {
  final int rowIndex;
  final int columnIndex;
  final Rect bounds; // normalized 0.0-1.0
}

// Grid lines are ~2-3px at 400 DPI (~3400px width) = ~0.001 normalized
static const double _gridLineInset = 0.001;
```

### Step 2: Add `_computeCellCrops()` method

Computes cell regions from H-lines x V-lines grid. For each consecutive pair of H-lines (row) and V-lines (column), create a `_CellCrop`. Springfield example: 7 V-lines = 6 columns per row, 28 H-lines on page 1 = 27 rows = 162 cells.

### Step 3: Implement `_recognizeWithCellCrops()`

Same signature as `_recognizeWithRowStrips()` so it's a drop-in replacement. Algorithm:

1. Decode preprocessed image once
2. Sort H-lines and V-lines, call `_computeCellCrops()`
3. Compute median row height for PSM selection
4. For each `_CellCrop`:
   - Apply `_gridLineInset` to bounds (shrink inward to exclude grid lines)
   - Convert to pixel coords via `CoordinateNormalizer.toPixels()`
   - Crop with `img.copyCrop()`
   - Emit diagnostic: `page_{p}_row_{rr}_col_{c}_raw`
   - Run `_cropUpscaler.prepareForOcr()` (handles narrow columns via upscaling)
   - Emit diagnostic: `page_{p}_row_{rr}_col_{c}_ocr`
   - Determine PSM: row 0 = PSM 6 (headers), tall rows = PSM 6, normal = PSM 7
   - Run `engine.recognizeCrop()`
   - Map coordinates: cell-crop-pixels -> page-normalized (same chain as row-strip path)
5. Sort elements by (top, left), return same record type as `_recognizeWithRowStrips()`

### Step 4: Switch dispatch in `recognize()`

Change the call from `_recognizeWithRowStrips()` to `_recognizeWithCellCrops()`. Keep the old method for rollback safety.

### Step 5: Update metrics labels

Rename `strips_upscaled` -> `cells_upscaled` etc. in `_CropOcrStats.upscalingMetrics`. Add `cells_ocrd` counter.

### Step 6: Update tests

**Existing tests to update** (expected crop counts change due to cell-level granularity):
- `'computes expected row strips from grid lines'` — 4 rows x N columns
- `'uses first/last vertical lines as row-strip margins'` — now 1 column per row
- `'skips margin columns by strip bounds'` — now 3 columns per row
- Upscaling metrics key names

**New tests to add**:
- Grid line inset verification (bounds shrink by `_gridLineInset`)
- Cell count: 4 H-lines x 3 V-lines = 3 rows x 2 cols = 6 recognizeCrop calls
- Narrow column (170px) produces OCR output after upscaling
- Empty cell (no text) doesn't error

### Step 7: Regenerate Springfield fixtures

Run fixture generator with cell-level OCR to produce new golden data. This is a separate step after code verification.

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Grid line pixels in crop (previous failure) | `_gridLineInset = 0.001` excludes grid line pixels before pixel conversion |
| Non-grid pages break | `if (gridPage?.hasGrid == true)` check unchanged; non-grid pages use `_recognizeFullPage()` |
| Performance (6x more Tesseract calls) | Each cell is ~6x smaller image; Tesseract is O(area), so total time similar |
| Rollback needed | Keep `_recognizeWithRowStrips()` in file, one-line switch back |
| CropUpscaler can't handle narrow cells | Already tested: 140x90px item# column upscales to 300x192px |

## Verification

1. `pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart"` — unit tests pass
2. `pwsh -Command "flutter test test/features/pdf/extraction/"` — all extraction tests pass
3. Regenerate Springfield fixtures and run stage trace diagnostic:
   - Expect ~6 elements per row (up from ~2.1)
   - Expect item numbers without `|` `[` artifacts
   - Expect unit/quantity/unitPrice/bidAmount columns populated
   - Expect >100 GT item matches (up from 26/131)
