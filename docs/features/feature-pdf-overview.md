---
feature: pdf
type: overview
scope: PDF Extraction & Generation (V2 Pipeline)
updated: 2026-02-13
---

# PDF Feature Overview

## Purpose

The PDF feature enables construction inspectors to extract structured data from bid PDFs and generate customized inspection reports. It implements a V2 OCR-first extraction pipeline optimized for damaged, corrupted, and multi-column bid documents commonly found in construction.

## Key Responsibilities

- **PDF Extraction**: Render PDF pages as images, apply preprocessing, and extract bid items using Tesseract OCR (stages 0-6)
- **Quality Validation**: Detect CMap corruption, validate extracted data against expected schemas, and measure extraction confidence
- **Data Post-Processing**: Infer missing fields (quantity from amount/unitPrice), split multi-item rows, and deduplicate entries
- **Template Generation**: Fill inspection report templates with project data and save as structured PDFs
- **Bid Item Parsing**: Extract tabular bid item data (item number, description, unit, quantity, unitPrice) with confidence scoring

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/pdf/services/extraction/` | V2 extraction pipeline (stages 0-6) |
| `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` | Main orchestrator for all 7 stages |
| `lib/features/pdf/services/extraction/stages/` | Individual stage implementations |
| `lib/features/pdf/services/extraction/models/pipeline_config.dart` | Configuration for OCR, inference, splitting |
| `lib/features/pdf/data/models/` | ParsedBidItem, QualityReport models |
| `lib/features/pdf/presentation/screens/pdf_preview_screen.dart` | PDF preview and validation UI |
| `assets/templates/*.pdf` | Inspection report templates (fillable forms) |

## Data Sources

- **Input**: PDF files stored locally on device or accessed from cloud storage
- **SQLite**: Persists extracted bid items and quality reports locally
- **Tesseract OCR**: External OCR engine (via `flusseract` package) for page text extraction
- **Image Library**: Preprocessing for page rendering (contrast, denoise, adaptive binarization)

## Integration Points

**Depends on:**
- `core/database` - SQLite storage for bid items and metadata
- `entries` - Daily entry model references extracted bid items
- `photos` - Photo service for PDF page previews

**Required by:**
- `entries` - Daily entries link to extracted bid items
- `quantities` - Quantity tracking uses extracted bid items as baseline

## Offline Behavior

The PDF feature is **fully offline-capable**. Extraction, parsing, and report generation occur locally without network dependency. Cloud sync (if implemented) uploads completed reports to Supabase after extraction completes. Users can work with PDFs entirely offline; synchronization happens asynchronously during sync operations.

## Edge Cases & Limitations

- **CMap Corruption**: Damaged character encoding in PDFs bypasses native extraction; OCR is always used (see `pdf-v2-constraints.md`)
- **Multi-Page Documents**: Processes one page at a time; must aggregate results manually
- **Re-extraction Loop**: Attempts 3 different DPI/PSM configurations if initial OCR confidence is low
- **Confidence Threshold**: Items below 60% confidence require manual review; 60-80% show warnings
- **Memory Constraints**: Large multi-page PDFs may require chunked processing on resource-constrained devices

## Detailed Specifications

See `architecture-decisions/pdf-v2-constraints.md` for:
- Hard rules (no V1 imports, OCR-only routing, no legacy flags)
- Performance targets (single-page < 15 sec, multi-page < 3 sec/page)
- Test coverage requirements (≥ 90% for extraction stages)

See `rules/pdf/pdf-generation.md` for:
- Template field naming conventions and mapping patterns
- OCR preprocessing pipeline details (contrast, deskew, binarization)
- Debugging and testing patterns for PDF-related code
