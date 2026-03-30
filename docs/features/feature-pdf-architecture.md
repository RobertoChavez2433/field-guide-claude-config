---
feature: pdf
type: architecture
scope: PDF Extraction & Generation (V2 Pipeline)
updated: 2026-03-30
---

# PDF Feature Architecture

## Overview

The PDF feature is **service-oriented**, not repository-pattern. It handles two concerns:

1. **PDF generation** — Produce IDR (Inspector's Daily Report) PDFs from entry data.
2. **PDF extraction** — Import pay-item bid schedules and Measurement & Payment (M&P) PDFs.

There is no sync adapter for PDF. Extracted bid items are owned by the `quantities` feature once imported.

---

## Layer Structure

```
lib/features/pdf/
├── pdf.dart                        # Feature barrel export
├── domain/
│   └── domain.dart                 # Placeholder (extraction logic lives in services)
├── data/
│   ├── models/
│   │   ├── models.dart             # Barrel export
│   │   └── parsed_bid_item.dart    # Extracted item with confidence/warnings
│   └── datasources/
│       └── local/
│           └── extraction_metrics_local_datasource.dart  # SQLite metrics persistence
├── presentation/
│   ├── presentation.dart           # Barrel export
│   ├── helpers/
│   │   ├── pdf_import_helper.dart  # File picker + progress dialog + main-thread extraction
│   │   └── mp_import_helper.dart   # Same pattern for M&P PDFs
│   ├── screens/
│   │   ├── screens.dart
│   │   ├── pdf_import_preview_screen.dart   # Review/confirm extracted bid items
│   │   └── mp_import_preview_screen.dart    # Review/confirm M&P extraction matches
│   └── widgets/
│       ├── widgets.dart
│       ├── extraction_banner.dart            # Root-level slim banner (~48dp) above nav bar
│       └── extraction_detail_sheet.dart      # Bottom sheet: stage breakdown + cancel
├── di/
│   └── pdf_providers.dart          # DI wiring (see DI section)
└── services/
    ├── services.dart               # Barrel export
    ├── pdf_service.dart            # IDR PDF generation (Syncfusion templates)
    ├── pdf_import_service.dart     # Orchestrates pipeline → PdfImportResult
    ├── photo_pdf_service.dart      # Embeds photos into IDR report pages
    ├── ocr/                        # Top-level OCR asset management
    │   ├── ocr.dart                # Barrel (TesseractConfig + TesseractInitializer)
    │   ├── tesseract_config.dart   # Tessdata path resolution (app support dir)
    │   └── tesseract_initializer.dart  # Copies bundled .traineddata assets to writable location
    ├── mp/
    │   ├── mp_models.dart          # M&P extraction domain models
    │   └── mp_extraction_service.dart  # M&P extraction (reuses V2 OCR stages)
    └── extraction/
        ├── pipeline/               # Core orchestrator + support classes
        │   ├── extraction_pipeline.dart      # Central orchestrator (stages 0–6, re-extraction loop)
        │   ├── pipeline_context.dart         # Mutable context passed between stages
        │   ├── extraction_metrics.dart       # Persists pipeline run stats to SQLite
        │   ├── result_converter.dart         # PipelineResult → PdfImportResult / BidItem[]
        │   ├── coordinate_normalizer.dart    # Normalizes OCR bounding boxes to logical coords
        │   ├── confidence_model.dart         # Shared confidence scoring formulas
        │   ├── ocr_text_extractor.dart       # Helper: render+preprocess+OCR for cell re-scan
        │   └── synthetic_region_builder.dart # Builds table regions from grid-line geometry
        ├── runner/                 # Background-isolate job management
        │   ├── extraction_job.dart           # Sealed job types: BidItemExtractionJob, MpExtractionJob
        │   ├── extraction_job_runner.dart    # ChangeNotifier: spawns worker isolate, streams progress
        │   ├── extraction_progress.dart      # Progress value object with stage labels
        │   └── extraction_result.dart        # Sealed results: BidItemJobResult, MpJobResult, JobError
        ├── ocr/                    # V2 OCR engine (pipeline-internal)
        │   ├── ocr_engine_v2.dart            # Abstract OCR engine interface
        │   ├── tesseract_engine_v2.dart      # Flusseract wrapper with HOCR output support
        │   ├── tesseract_config_v2.dart      # PSM mode, DPI, language config for V2 engine
        │   └── crop_ocr_stats.dart           # Stats for per-cell re-OCR operations
        ├── stages/                 # Individual extraction stage implementations
        │   ├── stages.dart                   # Barrel export
        │   ├── stage_names.dart              # Stage identifier string constants
        │   ├── stage_fixtures.dart           # Fixture serialization helpers for integration tests
        │   ├── document_quality_profiler.dart
        │   ├── page_renderer_v2.dart
        │   ├── image_preprocessor_v2.dart
        │   ├── grid_line_detector.dart
        │   ├── grid_line_remover.dart
        │   ├── text_recognizer_v2.dart
        │   ├── element_validator.dart
        │   ├── row_classifier_v3.dart
        │   ├── header_consolidator.dart
        │   ├── region_detector_v2.dart
        │   ├── column_detector_v2.dart
        │   ├── grid_line_column_detector.dart
        │   ├── header_detector.dart
        │   ├── text_alignment_detector.dart
        │   ├── whitespace_gap_detector.dart
        │   ├── anchor_corrector.dart
        │   ├── cell_extractor_v2.dart
        │   ├── numeric_interpreter.dart
        │   ├── row_parser_v3.dart
        │   ├── field_confidence_scorer.dart
        │   ├── post_processor_v2.dart
        │   ├── value_normalizer.dart
        │   ├── row_splitter.dart
        │   ├── consistency_checker.dart
        │   ├── item_deduplicator.dart
        │   └── quality_validator.dart
        ├── models/                 # V2 pipeline-internal models
        │   ├── models.dart
        │   ├── pipeline_config.dart
        │   ├── document_profile.dart
        │   ├── extraction_result.dart
        │   ├── ocr_element.dart
        │   ├── detected_regions.dart
        │   ├── column_map.dart
        │   ├── cell_grid.dart
        │   ├── classified_rows.dart
        │   ├── grid_lines.dart
        │   ├── parsed_items.dart
        │   ├── processed_items.dart
        │   ├── quality_report.dart
        │   ├── stage_report.dart
        │   ├── sidecar.dart
        │   ├── document_checksum.dart
        │   ├── confidence.dart
        │   ├── interpreted_value.dart
        │   └── interpretation_rule.dart
        ├── shared/                 # Cross-stage utilities and constants
        │   ├── pipeline_constants.dart
        │   ├── quality_thresholds.dart
        │   ├── unit_registry.dart
        │   ├── header_keywords.dart
        │   ├── extraction_patterns.dart
        │   ├── field_format_validator.dart
        │   ├── post_process_utils.dart
        │   ├── text_quality_analyzer.dart
        │   ├── math_utils.dart
        │   ├── crop_upscaler.dart
        │   ├── geometry_utils.dart
        │   └── keyword_matcher.dart
        └── rules/                  # Field interpretation rules
            ├── text_rules.dart
            ├── numeric_rules.dart
            ├── currency_rules.dart
            └── interpretation_patterns.dart
```

---

## Key Classes

### Top-Level Services

| Class | File | Purpose |
|-------|------|---------|
| `PdfService` | `services/pdf_service.dart` | Generates IDR PDFs using Syncfusion templates; embeds entry data, contractors, quantities |
| `PdfImportService` | `services/pdf_import_service.dart` | Orchestrates `ExtractionPipeline` on the main thread; returns `PdfImportResult` |
| `PhotoPdfService` | `services/photo_pdf_service.dart` | Renders photo pages within IDR reports |

### OCR Asset Management (Top-Level OCR)

| Class | File | Purpose |
|-------|------|---------|
| `TesseractConfig` | `services/ocr/tesseract_config.dart` | Resolves tessdata directory path in app support storage; caches result |
| `TesseractInitializer` | `services/ocr/tesseract_initializer.dart` | Copies bundled `assets/tessdata/eng.traineddata` to writable location on first run; idempotent |

### Pipeline Orchestrator

| Class | File | Purpose |
|-------|------|---------|
| `ExtractionPipeline` | `extraction/pipeline/extraction_pipeline.dart` | Central orchestrator; runs stages 0–6; re-extraction loop (max 3 attempts with DPI/PSM adjustments); returns `PipelineResult` |
| `PipelineResult` | `extraction/pipeline/extraction_pipeline.dart` | Result container: `processedItems`, `qualityReport`, `stageReports`, `sidecar`, `totalAttempts` |
| `PipelineContext` | `extraction/pipeline/pipeline_context.dart` | Mutable context shared between stages: `documentId`, `documentHash`, `config`, `sidecar`, `stageReports` |
| `ExtractionMetrics` | `extraction/pipeline/extraction_metrics.dart` | Persists run stats to `extraction_metrics` + `stage_metrics` SQLite tables (best-effort) |
| `ResultConverter` | `extraction/pipeline/result_converter.dart` | Converts `PipelineResult` → `PdfImportResult` + `List<BidItem>` |
| `SyntheticRegionBuilder` | `extraction/pipeline/synthetic_region_builder.dart` | Builds table regions from grid-line geometry; merges with `RegionDetectorV2` output |

### Background Isolate Runner

| Class | File | Purpose |
|-------|------|---------|
| `ExtractionJobRunner` | `extraction/runner/extraction_job_runner.dart` | `ChangeNotifier`; spawns one worker isolate; streams `ExtractionProgress`; supports cancel between pages |
| `BidItemExtractionJob` | `extraction/runner/extraction_job.dart` | Job type for pay-item PDF extraction |
| `MpExtractionJob` | `extraction/runner/extraction_job.dart` | Job type for M&P PDF extraction; carries serialized `existingBidItemMaps` |
| `BidItemJobResult` / `MpJobResult` | `extraction/runner/extraction_result.dart` | Sealed result types carrying `resultMap` (cross-isolate serialization) |

### V2 OCR Engine (Pipeline-Internal)

| Class | File | Purpose |
|-------|------|---------|
| `OcrEngineV2` | `extraction/ocr/ocr_engine_v2.dart` | Abstract OCR engine interface |
| `TesseractEngineV2` | `extraction/ocr/tesseract_engine_v2.dart` | Flusseract wrapper; HOCR output; native FFI |
| `TesseractConfigV2` / `OcrConfigV2` | `extraction/ocr/tesseract_config_v2.dart` | PSM mode, DPI, language for V2 engine |

### M&P Sub-System

| Class | File | Purpose |
|-------|------|---------|
| `MpExtractionService` | `services/mp/mp_extraction_service.dart` | Extracts M&P descriptions from state DOT PDFs; matches against existing bid items; reuses V2 OCR stages |

---

## Extraction Pipeline Stages (Stage 0–6)

```
ExtractionPipeline.extract()
│
├─ Stage 0:  DocumentQualityProfiler  → DocumentProfile (structure, page count)
│
├─ Stage 2B: OCR Path (all pages)
│   ├─ 2B-i:    PageRendererV2        → Map<int, RenderedPage>
│   ├─ 2B-ii:   ImagePreprocessorV2   → Map<int, PreprocessedPage>
│   ├─ 2B-ii.5: GridLineDetector      → GridLines
│   ├─ 2B-ii.6: GridLineRemover       → cleaned pages + enriched GridLines
│   └─ 2B-iii:  TextRecognizerV2      → Map<int, List<OcrElement>>  (Tesseract FFI)
│
├─ Stage 3:  ElementValidator         → ExtractionResult (coordinate normalization)
│
├─ Pre-4B:  RowClassifierV3 (provisional) + HeaderConsolidator (provisional)
│
├─ Stage 4B: SyntheticRegionBuilder + RegionDetectorV2 → DetectedRegions
│
├─ Stage 4C: ColumnDetectorV2         → ColumnMap
│
├─ Stage 4A: RowClassifierV3 (final)  → ClassifiedRows
│            HeaderConsolidator (final)
│            RowMerger                → merged rows
│
├─ Stage 4D: CellExtractorV2          → CellGrid
│            NumericInterpreter       → interpreted cell values
│
├─ Stage 4E: RowParserV3              → ParsedItems
│            FieldConfidenceScorer    → confidence-scored ParsedItems
│
├─ Stage 5:  PostProcessorV2          → ProcessedItems (inference, splitting, dedup)
│
└─ Stage 6:  QualityValidator         → QualityReport (status, overallScore)
                                         QualityStatus: autoAccept | reviewFlagged | reExtract | partialResult
```

**Re-extraction loop** (max 3 attempts):
- Attempt 0: default config (300 DPI, PSM 6)
- Attempt 1: 400 DPI, PSM 3 (auto page segmentation)
- Attempt 2: 400 DPI, PSM 6 (single block)
- Best attempt selected by `qualityReport.overallScore`

---

## Data Models

### `data/models/` (Feature-Public)

| Model | Fields | Notes |
|-------|--------|-------|
| `ParsedBidItem` | `itemNumber`, `description`, `unit`, `quantity`, `unitPrice`, `bidAmount`, `confidence`, `warnings` | Confidence 0.0–1.0; `< 0.65` needs review |
| `PdfImportResult` | `parsedItems`, `bidItems`, `metadata`, `warnings`, `repairNotes`, `parserUsed`, `usedOcr` | Returned by `PdfImportService`; consumed by preview screens |

### `extraction/models/` (Pipeline-Internal)

Key internal models (not exposed outside the feature):

| Model | Purpose |
|-------|---------|
| `PipelineConfig` | Per-run settings: `ocrDpi`, `tesseractPsmMode`, `amountTolerance`, `expectedItemCount` |
| `DocumentProfile` | Output of `DocumentQualityProfiler`: page count, extraction strategy |
| `OcrElement` | Single OCR word/line with bounding box |
| `GridLines` | Per-page detected grid line positions |
| `ColumnMap` | Column boundary definitions with semantic labels |
| `CellGrid` | 2D grid of extracted cell text values |
| `ClassifiedRows` | Rows after `RowClassifierV3` assigns `RowType` |
| `ParsedItems` | Items after row parsing (pre-post-processing) |
| `ProcessedItems` | Items after post-processing: `items`, `repairLog`, `inferenceLog`, `repairStats` |
| `QualityReport` | Overall quality: `status`, `overallScore`, `reExtractionStrategy` |
| `StageReport` | Per-stage timing, input/output counts, warnings |
| `Sidecar` | Metadata attached to an extraction run |

---

## DI Wiring

**File:** `lib/features/pdf/di/pdf_providers.dart`

```dart
List<SingleChildWidget> pdfProviders({required PdfService pdfService}) {
  return [
    Provider<PdfService>.value(value: pdfService),
    ChangeNotifierProvider(create: (_) => ExtractionJobRunner()),
  ];
}
```

- `PdfService` — singleton, injected from `main.dart` (Tier 4).
- `ExtractionJobRunner` — singleton `ChangeNotifier`; owns the worker isolate lifecycle.
- `PdfImportService` — instantiated per-import (no shared state; not DI-registered).
- `MpExtractionService` — instantiated per-import inside worker isolate; `dispose()` called after use.

---

## Two Import Paths

### Standard Bid Item Import (pay-item PDFs)

```
User taps "Import PDF"
    ↓
PdfImportHelper.importFromPdf()
    ↓ file picker + size check (100MB limit)
PdfImportService.importBidSchedule()
    ↓ main-thread ExtractionPipeline (pdfrx requires main Flutter engine)
ExtractionPipeline.extract() → PipelineResult
    ↓
ResultConverter.toPdfImportResult() → PdfImportResult
    ↓
ExtractionMetrics.recordRun() → SQLite (best-effort)
    ↓
PdfImportPreviewScreen: review ParsedBidItem[] with confidence badges
    ↓ user confirms
BidItem[] saved via quantities feature (BidItemProvider)
```

**Why main-thread (not isolate):** `pdfrx` page rendering requires `BackgroundIsolateBinaryMessenger` + full Flutter engine context. The background-isolate path (`ExtractionJobRunner`) silently returned 0 items because page renders returned null in the worker isolate. `PdfImportHelper` runs on the main thread.

### M&P Import (Measurement & Payment PDFs)

```
User taps "Import M&P"
    ↓
MpImportHelper (file picker + progress dialog, main thread)
    ↓
MpExtractionService.extract(pdfBytes, existingBidItems)
    ↓ reuses V2 OCR stages (PageRendererV2, TextRecognizerV2, etc.)
MpExtractionResult (matches: MpMatch[], unmatched entries, stats)
    ↓
MpImportPreviewScreen: review matches before saving descriptions
```

### Background Isolate Path (ExtractionJobRunner)

`ExtractionJobRunner` exists for the **future** background path and is currently wired to the UI via `ExtractionBanner` + `ExtractionDetailSheet`. It can submit `BidItemExtractionJob` or `MpExtractionJob`, stream progress, and support cancellation between pages. PDF bytes transferred zero-copy via `TransferableTypedData`. Not used by `PdfImportHelper` (see above).

---

## Presentation

### Screens

| Screen | Consumed By |
|--------|-------------|
| `PdfImportPreviewScreen` | Receives `PdfImportResult` via route `extra`; user edits/confirms bid items |
| `MpImportPreviewScreen` | Receives `MpJobResult` or `MpExtractionResult` via route `extra` |

### Widgets

| Widget | Purpose |
|--------|---------|
| `ExtractionBanner` | Slim banner (48dp) rendered above bottom nav bar; shows stage icon, label, progress bar, elapsed time; auto-dismisses 10s after completion; taps open `ExtractionDetailSheet` or navigate to preview |
| `ExtractionDetailSheet` | Bottom sheet: full stage checklist with done/current/pending icons, progress bar, elapsed time, cancel/dismiss buttons |

### Helpers

| Helper | Purpose |
|--------|---------|
| `PdfImportHelper` | Static entry point: file picker → size check → main-thread `PdfImportService` → navigate to preview |
| `MpImportHelper` | Same pattern for M&P PDFs; uses `MpExtractionService` directly |

---

## Offline Behavior

Fully offline. All extraction (OCR via Tesseract FFI, preprocessing via OpenCV `opencv_dart`, rendering via `pdfrx` / PDFium) runs locally. No network calls during import or generation.

Extracted bid items are persisted to SQLite by the `quantities` feature after user confirmation. The sync adapter for `bid_items` (in the `quantities` feature) queues them for Supabase push.

---

## Feature Relationships

| Depends On | Why |
|------------|-----|
| `quantities` | `BidItem` model lives in quantities; import saves items via `BidItemProvider` |
| `projects` | Pay-item import is triggered from project setup; `projectId` scopes all extractions |
| `entries` | `PdfService` generates IDR PDFs from `DailyEntry` data |
| `photos` | `PhotoPdfService` embeds photos into IDR report pages |
| `forms` | PDF form-filling for structured form templates |

| Required By | Why |
|-------------|-----|
| `projects` | Pay-item import flow in project setup screen |
| `entries` | IDR report generation |
| `quantities` | Bid item data sourced from extraction |

---

## Performance

| Metric | Target |
|--------|--------|
| Single-page PDF | < 15 seconds including OCR |
| Multi-page (10+) | < 3 seconds/page average |
| Re-extraction loop (3 attempts) | < 45 seconds total |
| OCR session memory | ~50–100 MB (Tesseract heap) |
| Page render buffer | ~5–10 MB per page |

Tesseract tessdata asset: `assets/tessdata/eng.traineddata` (14.7MB). Copied to app support directory on first run by `TesseractInitializer`.

---

## Testing

### Unit Tests — Stage-Level
Location: `test/features/pdf/extraction/stages/`

Each stage tested independently (happy path + error paths).

### Integration Tests — Pipeline-Level
- `integration_test/springfield_report_test.dart` — Full pipeline trace + regression gate against Springfield PDF
- `test/features/pdf/extraction/integration/full_pipeline_integration_test.dart` — Pipeline-level integration

### Pipeline Comparison System
- `test/features/pdf/extraction/golden/` — `pipeline_comparator.dart`, `report_generator.dart`
- `test/features/pdf/extraction/fixtures/` — JSON ground truth
- `test/features/pdf/extraction/reports/` — Per-run reports (gitignored)

### Coverage Target
- ≥ 90% for all extraction stages
- 100% for confidence scoring logic

---

## Import Pattern

```dart
// Trigger import from another feature (e.g., project setup)
import 'package:construction_inspector/features/pdf/presentation/helpers/pdf_import_helper.dart';

// Read extraction results
import 'package:construction_inspector/features/pdf/services/pdf_import_service.dart';

// Observe background extraction
import 'package:construction_inspector/features/pdf/services/extraction/runner/extraction_job_runner.dart';

// Pipeline (internal or test use)
import 'package:construction_inspector/features/pdf/services/extraction/pipeline/extraction_pipeline.dart';
import 'package:construction_inspector/features/pdf/data/models/parsed_bid_item.dart';
```
