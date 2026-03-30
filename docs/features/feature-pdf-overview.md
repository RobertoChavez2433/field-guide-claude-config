---
feature: pdf
type: overview
scope: PDF Extraction & Generation (V2 Pipeline)
updated: 2026-03-30
---

# PDF Feature Overview

## Purpose

The PDF feature enables construction inspectors to extract structured data from bid PDFs and generate customized inspection reports. It implements a V2 OCR-first extraction pipeline optimized for damaged, corrupted, and multi-column bid documents commonly found in construction.

## Key Responsibilities

- **PDF Extraction**: Render PDF pages as images, apply preprocessing, and extract bid items using Tesseract OCR through a 27-stage pipeline
- **Quality Validation**: Detect CMap corruption, validate extracted data against expected schemas, and measure extraction confidence
- **Data Post-Processing**: Infer missing fields (quantity from amount/unitPrice), split multi-item rows, and deduplicate entries
- **Template Generation**: Fill inspection report templates with project data and save as structured PDFs
- **Bid Item Parsing**: Extract tabular bid item data (item number, description, unit, quantity, unitPrice) with confidence scoring
- **Multi-Page Import**: Orchestrate multi-page extraction via `MpExtractionService` with progress reporting

## Key Files

### Services

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/pdf/services/pdf_service.dart` | `PdfService` | Core PDF generation — fills templates, saves reports |
| `lib/features/pdf/services/pdf_import_service.dart` | `PdfImportService` | Orchestrates single-file import: file picking, extraction, persistence |
| `lib/features/pdf/services/photo_pdf_service.dart` | `PhotoPdfService` | Renders PDF pages to images for preview and OCR input |
| `lib/features/pdf/services/mp/mp_extraction_service.dart` | `MpExtractionService` | Multi-page extraction coordinator with per-page progress |

### OCR Sub-System

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/pdf/services/ocr/tesseract_initializer.dart` | `TesseractInitializer` | Manages Tesseract lifecycle (init, warm-up, teardown) |
| `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart` | `TesseractEngineV2` | Concrete OCR engine; implements `OcrEngineV2` |
| `lib/features/pdf/services/extraction/ocr/ocr_engine_v2.dart` | `OcrEngineV2` | Abstract interface for V2 OCR engines |

### Extraction Pipeline

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` | `ExtractionPipeline` | Main orchestrator — runs all 27 stages in sequence |
| `lib/features/pdf/services/extraction/stages/` | (27 stage classes) | Individual stage implementations (see Stages section) |
| `lib/features/pdf/services/extraction/models/pipeline_config.dart` | `PipelineConfig` | Configuration for OCR, inference, splitting |

### Presentation

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart` | `PdfImportPreviewScreen` | Single-file import preview and confirmation UI |
| `lib/features/pdf/presentation/screens/mp_import_preview_screen.dart` | `MpImportPreviewScreen` | Multi-page import preview with per-page progress |
| `lib/features/pdf/presentation/widgets/extraction_banner.dart` | `ExtractionBanner` | In-progress extraction status banner widget |
| `lib/features/pdf/presentation/widgets/extraction_detail_sheet.dart` | `ExtractionDetailSheet` | Bottom sheet showing extraction result detail |
| `lib/features/pdf/presentation/helpers/pdf_import_helper.dart` | `PdfImportHelper` | Presentation-layer helper coordinating single-file import flow |
| `lib/features/pdf/presentation/helpers/mp_import_helper.dart` | `MpImportHelper` | Presentation-layer helper coordinating multi-page import flow |

### Data Models

| File Path | Purpose |
|-----------|---------|
| `lib/features/pdf/data/models/parsed_bid_item.dart` | `ParsedBidItem` — canonical extracted bid item with confidence |
| `lib/features/pdf/services/extraction/models/quality_report.dart` | `QualityReport` — per-page OCR quality summary |
| `lib/features/pdf/services/extraction/models/pipeline_config.dart` | `PipelineConfig` — pipeline tuning knobs |

## Extraction Pipeline Stages

The 27 stages in `lib/features/pdf/services/extraction/stages/` (in logical order):

1. `PageRendererV2` — render PDF page to bitmap at target DPI
2. `DocumentQualityProfiler` — measure OCR-readiness, detect corruption
3. `ImagePreprocessorV2` — contrast, deskew, denoise, adaptive binarization
4. `GridLineDetector` — detect horizontal/vertical ruling lines
5. `GridLineRemover` — erase grid lines before OCR to reduce noise
6. `GridLineColumnDetector` — infer column boundaries from grid geometry
7. `TextRecognizerV2` — run Tesseract OCR on preprocessed page
8. `RegionDetectorV2` — segment page into header, body, footer regions
9. `HeaderDetector` — locate and classify column header row(s)
10. `HeaderConsolidator` — merge split/wrapped header cells
11. `ColumnDetectorV2` — detect column boundaries from text alignment
12. `WhitespaceGapDetector` — identify column separating whitespace gaps
13. `TextAlignmentDetector` — classify text alignment per column (L/R/C)
14. `AnchorCorrector` — correct anchor drift across multi-column pages
15. `CellExtractorV2` — assign OCR elements to (row, column) cells
16. `RowClassifierV3` — label rows as bid-item, continuation, or noise
17. `RowMerger` — merge continuation rows into their parent bid item
18. `RowParserV3` — parse merged rows into structured `ParsedBidItem` candidates
19. `NumericInterpreter` — resolve ambiguous numeric formats (currency, counts)
20. `ElementValidator` — validate individual OCR element plausibility
21. `FieldConfidenceScorer` — compute per-field and per-item confidence scores
22. `ConsistencyChecker` — cross-validate amount = unitPrice × quantity math
23. `PostProcessorV2` — infer missing fields, normalize units
24. `ValueNormalizer` — canonical formatting for units, descriptions, numbers
25. `RowSplitter` — split compound rows containing multiple bid items
26. `ItemDeduplicator` — remove duplicate items across page boundaries
27. `QualityValidator` — final gate; assigns accept/warn/reject to each item

## Data Sources

- **Input**: PDF files stored locally on device or accessed via system file picker
- **SQLite**: Persists extracted bid items and quality reports locally
- **Tesseract OCR**: External OCR engine (via `flusseract` package) for page text extraction
- **Image Library**: OpenCV-based preprocessing for page rendering (contrast, denoise, adaptive binarization)

## Integration Points

**Required by:**
- `entries` — daily entries link to extracted bid items
- `projects` — project import flow triggers PDF extraction
- `forms` — form templates reference extracted bid item data

**Depends on:**
- `projects` — project context (id, name) stored alongside extracted items
- `quantities` — extracted bid items seed the quantity tracking baseline
- `entries` — bid item references carried into daily entry records
- `core/database` — SQLite storage for bid items and extraction metadata

## Offline Behavior

The PDF feature is **fully offline-capable**. Extraction, parsing, and report generation occur locally without network dependency. Cloud sync (if implemented) uploads completed reports to Supabase after extraction completes. Users can work with PDFs entirely offline; synchronization happens asynchronously during sync operations.

## Edge Cases & Limitations

- **CMap Corruption**: Damaged character encoding in PDFs bypasses native extraction; OCR is always used (see `pdf-v2-constraints.md`)
- **Multi-Page Documents**: Processes one page at a time via `MpExtractionService`; results are aggregated after all pages complete
- **Re-extraction Loop**: Attempts 3 different DPI/PSM configurations if initial OCR confidence is low
- **Confidence Threshold**: Items below 60% confidence require manual review; 60-80% show warnings
- **Memory Constraints**: Large multi-page PDFs may require chunked processing on resource-constrained devices
- **FFI Constraint**: Tesseract + OpenCV use native FFI and must remain on the isolate they were initialized on

## Detailed Specifications

See `architecture-decisions/pdf-v2-constraints.md` for:
- Hard rules (no V1 imports, OCR-only routing, no legacy flags)
- Performance targets (single-page < 15 sec, multi-page < 3 sec/page)
- Test coverage requirements (≥ 90% for extraction stages)

See `rules/pdf/pdf-generation.md` for:
- Template field naming conventions and mapping patterns
- OCR preprocessing pipeline details (contrast, deskew, binarization)
- Debugging and testing patterns for PDF-related code
