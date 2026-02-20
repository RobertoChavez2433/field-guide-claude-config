# PDF Extraction Enhancement Reference (V2)

Current extraction is fully OCR-based (no native text hybrid). All pages are rasterized and processed through Tesseract.

## V2 Pipeline at a Glance

| Stage | Class | Purpose |
|-------|-------|---------|
| 0 | `DocumentQualityProfiler` | Per-page quality profiling (scan vs native, char count) |
| 2B-i | `PageRendererV2` | Rasterize to PNG — adaptive DPI (≤10 pg→300, 11-25→250, >25→200) |
| 2B-ii | `ImagePreprocessorV2` | Grayscale + adaptive contrast (no binarization) |
| 2B-ii.5 | `GridLineDetector` | Detect table grid lines (normalized 0.0-1.0) |
| 2B-ii.6 | `GridLineRemover` | OpenCV inpainting to erase grid lines (grid pages only) |
| 2B-iii | `TextRecognizerV2` | Cell-level OCR (grid) or full-page PSM 4 (non-grid) |
| 3 | `ElementValidator` | Coordinate normalization + element filtering |
| 4A | `RowClassifierV3` | Row classification (two-phase: pre- and post-column) |
| 4B | `RegionDetectorV2` | Table region detection |
| 4C | `ColumnDetectorV2` | Column boundary detection |
| 4D | `CellExtractorV2` | Assign OCR elements to cells |
| 4D.5 | `NumericInterpreter` | Parse numeric/currency values |
| 4E | `RowParserV3` | Map cells → ParsedBidItem fields |
| 4E.5 | `FieldConfidenceScorer` | Per-field confidence (weighted geometric mean) |
| 5 | `PostProcessorV2` | Normalization, deduplication, math backsolve |
| 6 | `QualityValidator` | Quality gate; triggers re-extraction loop if below threshold |

Re-extraction loop: up to 2 retries at 400 DPI (PSM 3 then PSM 6). Best result by `overallScore` kept.

---

## Key Enhancement Techniques

### Adaptive DPI
`PageRendererV2` selects render DPI based on page count to balance quality vs memory:
- ≤10 pages → 300 DPI
- 11-25 pages → 250 DPI
- >25 pages → 200 DPI
- Re-extraction retries always use 400 DPI

### Grid Line Removal
`GridLineRemover` (package: `opencv_dart` v2.2.1+3) runs only on pages flagged by `GridLineDetector`. Uses morphological open to isolate horizontal/vertical lines, then `cv.INPAINT_TELEA` (radius=2) to erase them. This prevents grid pixels from corrupting OCR reads on cell edges.

### Cell-Level Cropping + CropUpscaler
On grid pages, `TextRecognizerV2` crops each cell individually before passing to Tesseract. `CropUpscaler` targets an effective 600 DPI output using cubic interpolation with 10px padding, capped at 2000px. This avoids running a huge full-page raster through PSM 7.

### Per-Cell PSM Selection (`_determineRowPsm`)
- Row 0 (header) → PSM 6 (uniform block)
- Tall rows (>1.8× median height) → PSM 6
- All other data rows → PSM 7 (single line)

### Re-OCR Fallback on Numeric Columns
For columns 3, 4, 5 (qty/price/amount), if all elements have confidence < 0.50 AND no digit characters exist, `TextRecognizerV2` re-runs the cell with PSM 8 + numeric whitelist (`$0123456789,. -`). This addresses right-aligned currency values that PSM 7 mis-segments.

---

## Python Debugging Tools (Dev Only)

These scripts are for development analysis, not runtime use:

| Tool | Purpose |
|------|---------|
| `check_fillable_fields.py` | Determine PDF type (fillable vs scanned) |
| `extract_form_field_info.py` | Get field metadata for IDR template mapping |
| `convert_pdf_to_images.py` | Visual analysis of rasterized pages |
| `check_bounding_boxes.py` | Verify OCR element positions |

Use Python tools when:
- A PDF fails extraction and you need to understand why (layout, encoding, scanned)
- Verifying ground truth for OCR confidence debugging
- Pre-analyzing a new bid schedule format before updating Dart pipeline code

---

## Integration Points

- Main entry: `lib/features/pdf/services/pdf_import_service.dart`
- Stage barrel: `lib/features/pdf/services/extraction/stages/stages.dart`
- Pipeline orchestrator: `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`
