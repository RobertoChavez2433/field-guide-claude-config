# Grid Line Detection + Row-Level OCR Plan

## Context

The V2 extraction pipeline uses Tesseract PSM=6 (single block) to OCR full page images. PSM 6 disables column detection and reads straight left-to-right, producing garbage on table-heavy pages 2-6 (`I hc J IAA HS AT IE:` instead of "Erosion Control, Silt Fence"). The PDF is a clean digital 6-page bid schedule with visible grid lines and 6 columns.

**Fix**: Insert a GridLineDetector stage that detects table grid lines, crops individual rows, and OCRs each with PSM 7 (singleLine). Vertical grid lines also feed directly into column detection as high-confidence boundaries.

## Architecture Overview

```
Stage 2B-ii:   ImagePreprocessorV2 → Map<int, PreprocessedPage>
Stage 2B-ii.5: GridLineDetector    → GridLines (NEW)
Stage 2B-iii:  TextRecognizerV2    → Map<int, List<OcrElement>> (MODIFIED - uses GridLines)
  ├─ Grid page:    crop rows → erase vertical lines → PSM 7 per row
  └─ Non-grid page: full-page OCR with PSM 4 (singleColumn)
...
Stage 4C:      ColumnDetectorV2    → ColumnMap (MODIFIED - uses GridLines vertical lines)
  └─ Layer 0 (new): grid_line method at 0.95 confidence, bypasses text alignment clustering
```

---

## Phase 1: GridLines Model + GridLineDetector

### New: `lib/features/pdf/services/extraction/models/grid_lines.dart`

```
GridLineResult:
  pageIndex: int
  horizontalLines: List<double>  // normalized Y positions, sorted
  verticalLines: List<double>    // normalized X positions, sorted
  hasGrid: bool                  // true if >= 3 horizontal AND >= 2 vertical
  confidence: double
  toMap() / fromMap()

GridLines:
  pages: Map<int, GridLineResult>
  detectedAt: DateTime
  gridPages / nonGridPages getters
  toMap() / fromMap()
```

### New: `lib/features/pdf/services/extraction/stages/grid_line_detector.dart`

**Algorithm per page** (image already grayscale from preprocessor):
1. Decode `enhancedImageBytes` via `img.decodeImage()`
2. **Horizontal scan**: For each pixel row, count dark pixels (`luminance < 128`). If >60% of width is dark → part of horizontal line. Cluster adjacent dark rows → single line at cluster center Y. Normalize to 0.0-1.0.
3. **Vertical scan**: Only within vertical extent of first-to-last horizontal line. For each pixel column, count dark pixels. If >40% of bounded height is dark → vertical line. Cluster + normalize.
4. Filter: skip lines in top/bottom 5% of page, enforce minimum spacing (0.5% page height)
5. `hasGrid = horizontalLines.length >= 3 && verticalLines.length >= 2`

**Constants**: `kDarkPixelThreshold=128`, `kHorizontalCoverage=0.60`, `kVerticalCoverage=0.40`, `kMinHorizontalLines=3`, `kMinVerticalLines=2`, `kMinLineSpacing=0.005`, `kPageMargin=0.05`

### Update: `stage_names.dart` — add `gridLineDetection`
### Update: `models/models.dart` — export `grid_lines.dart`
### Update: `stages/stages.dart` — export `grid_line_detector.dart`

### New test: `test/features/pdf/extraction/stages/stage_2b_grid_line_detector_test.dart`
- Programmatically generate test images with grids using `image` package
- Test correct line count/positions, `hasGrid` logic, no-grid fallback
- Test `GridLines` serialization round-trip
- Test per-page independence

---

## Phase 2: TextRecognizerV2 Row Cropping

### Modify: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`

Add `GridLines? gridLines` parameter to `recognize()`. Per-page fork:

- **Grid page** → `_recognizeWithRowCropping()`:
  1. For each consecutive pair of horizontal lines `[hLines[i], hLines[i+1]]`:
     - Compute pixel boundaries, pad inward 2px to skip the grid line
     - `img.copyCrop(image, x:0, y:topPx, width:imgWidth, height:cropHeight)`
     - Erase vertical line positions (3px wide white band at each)
     - Encode to PNG, call `engine.recognizeCrop()` with PSM 7
     - Map crop-relative coords to page space:
       ```
       page_left  = cropRegion.left + elem.left * cropRegion.width
       page_top   = cropRegion.top  + elem.top  * cropRegion.height
       page_right = cropRegion.left + elem.right * cropRegion.width
       page_bot   = cropRegion.top  + elem.bottom * cropRegion.height
       ```
  2. Aggregate all row elements into page's element list

- **Non-grid page** → `_recognizeFullPage()` with PSM 4 (singleColumn)

### Modify: `lib/features/pdf/services/extraction/ocr/tesseract_config_v2.dart`
- Add `case 4: return PageSegMode.singleColumn;` to `pageSegMode` getter (currently missing, falls to default=singleBlock)

### Modify: `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart`
- Call `tess.setPageSegMode(cfg.pageSegMode)` before each `hocrText()` call in both `recognizeImage()` and `recognizeCrop()`, so PSM can change between calls on the same instance

### Tests:
- Coordinate mapping: element at (0.5, 0.5) in crop covering Y=[0.2, 0.3] → page Y=0.25
- PSM 4 used when no grid lines
- Vertical line erasing produces white pixels

---

## Phase 3: ColumnDetectorV2 Grid Line Integration

### Modify: `lib/features/pdf/services/extraction/stages/column_detector_v2.dart`

Add `GridLines? gridLines` parameter to `detect()`.

**New Layer 0** (before existing Layer 1 header keywords):
1. Collect vertical lines from all grid-detected pages
2. Cluster across pages (tolerance 1% page width) → median position per cluster
3. N vertical lines → N+1 columns (0.0→line1, line1→line2, ..., lineN→1.0)
4. Assign semantic headers by position order: [itemNumber, description, unit, quantity, unitPrice, bidAmount]
5. Return `method: 'grid_line'`, `confidence: 0.95`
6. When grid confidence >= 0.90, skip Layers 1-2 entirely

Also produce `perPageAdjustments` since line positions are detected per-page (user requirement).

Replace the existing `_detectFromLines()` TODO stub (lines 523-546) — superseded by this approach.

### Tests:
- Vertical lines at known X positions → correct column boundaries
- Method = 'grid_line', confidence = 0.95
- Fallback to existing layers when no grid

---

## Phase 4: Pipeline Wiring + Fixtures

### Modify: `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`
- Add `GridLineDetector gridLineDetector` to constructor with default
- Insert Stage 2B-ii.5 between preprocessing (line 402) and text recognition (line 404)
- Pass `gridLines` to `textRecognizer.recognize()` and `columnDetector.detect()`
- Emit `onStageOutput` for fixture generation

### Modify: `tool/generate_springfield_fixtures.dart`
- Add `StageNames.gridLineDetection: 'springfield_grid_lines.json'` to map

### Regenerate all fixtures by running generator against Springfield PDF

### Update: `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`
- Add grid line detection stage to trace output

### Update: `test/features/pdf/extraction/golden/springfield_golden_test.dart`
- Update item count, quality score, match rate expectations

### Update: `test/features/pdf/extraction/helpers/mock_stages.dart`
- Add `MockGridLineDetector`

### Update: pipeline + re-extraction loop tests with new constructor parameter

---

## File Inventory

### New (4 files)
| File | Purpose |
|------|---------|
| `lib/.../models/grid_lines.dart` | GridLines + GridLineResult model |
| `lib/.../stages/grid_line_detector.dart` | Grid line detection stage |
| `test/.../stages/stage_2b_grid_line_detector_test.dart` | Unit tests |
| `test/.../fixtures/springfield_grid_lines.json` | Generated fixture |

### Modified (12 files)
| File | Change |
|------|--------|
| `stages/stage_names.dart` | Add `gridLineDetection` constant |
| `models/models.dart` | Export grid_lines.dart |
| `stages/stages.dart` | Export grid_line_detector.dart |
| `stages/text_recognizer_v2.dart` | Accept GridLines, row cropping + PSM 7/4 |
| `stages/column_detector_v2.dart` | Accept GridLines, Layer 0 grid-based columns |
| `pipeline/extraction_pipeline.dart` | Wire GridLineDetector, pass GridLines downstream |
| `ocr/tesseract_config_v2.dart` | Add PSM 4 case |
| `ocr/tesseract_engine_v2.dart` | Per-call setPageSegMode before hocrText |
| `tool/generate_springfield_fixtures.dart` | Add grid lines fixture |
| `golden/stage_trace_diagnostic_test.dart` | Add grid line stage |
| `golden/springfield_golden_test.dart` | Update expectations |
| `helpers/mock_stages.dart` | Add MockGridLineDetector |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| PSM switching on same Tesseract instance | `setPageSegMode()` is supported between calls. If fails, recreate instance. |
| Row crop too small (<15px) | Set minimum crop height; merge tiny rows with adjacent |
| False positive lines (borders, shadows) | Skip top/bottom 5% of page; require minimum spacing |
| Vertical line erasing leaves artifacts | Erase 3-5px wide band per line |
| Performance (N rows × 6 pages = ~150 OCR calls) | PSM 7 is faster per-call than PSM 6. Profile in Phase 4. |

## Verification

1. `pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_2b_grid_line_detector_test.dart"`
2. `pwsh -Command "flutter test test/features/pdf/extraction/"`
3. Stage trace → 6 columns detected via grid_line method
4. Golden test → item match rate improves from 0% toward 90%+
5. Quality score → improves from 0.615 toward 0.85+
6. Total amount → converges toward $7,882,926.73
