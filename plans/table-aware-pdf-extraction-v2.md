# Plan V2: Table-Aware PDF Extraction (Native-First + Image Fallback)

## Goals
- Reliably extract bid schedule tables from visually clean PDFs with grid lines.
- Prefer native text extraction when usable; fall back to image-based OCR + table structure when not.
- Eliminate row/column mixing caused by OCR block text or malformed text layers.

## Evidence & Constraints (from codebase and PDF)
- The PDF renders cleanly and has consistent grid lines and repeated headers (visual ground truth).
- Current OCR-first path collapses multi-column data into single rows because row reconstruction is column-agnostic.
  - See `lib/features/pdf/services/ocr/ocr_row_reconstructor.dart`
- `ColumnLayoutParser` relies on Syncfusion `extractTextLines()` word bounds; when those bounds are flattened, header and clustering fail.
  - See `lib/features/pdf/services/parsers/column_layout_parser.dart`
- OCR pipeline already renders images and can output `TextBlock` elements with bounding boxes, but those boxes are not used for column assignment.
  - See `lib/features/pdf/services/pdf_import_service.dart`
  - See `lib/features/pdf/services/ocr/ml_kit_ocr_service.dart`

## Core Strategy (V2)
1) **Native text first** (fast, accurate for digital PDFs)
2) **Image-based table-aware OCR fallback** (robust for bad text layers)

Rationale:
- Digital PDFs often have a usable text layer; OCR only adds noise and cost.
- When the text layer is malformed, the rendered image is still clean, so OCR + table structure is reliable.

## V2 Improvements vs V1 Plan
- Add a **native text gate** before OCR to avoid unnecessary OCR on clean PDFs.
- Add **column boundary detection** and **column-aware row reconstruction** for OCR output.
- Add **table line detection** as a fallback when header OCR fails.
- Explicit **guardrails** for DPI/memory/time to avoid runtime blowups.
- Add diagnostics to explain which path was used and why.

## Phase 0: Diagnostics and Gating (PR-Size)
### Objective
Decide between native text or OCR using reliable signals; log decision rationale.

### Changes
- `lib/features/pdf/services/pdf_import_service.dart`
  - Add a gate that prefers `ColumnLayoutParser` when:
    - `extractTextLines()` yields sufficient lines/words, and
    - header row detected, and
    - at least 3 distinct X clusters exist.
  - Only fall back to OCR if any of the above fail.
- `lib/features/pdf/services/parsers/parser_diagnostics.dart`
  - Log:
    - text lines count
    - header detection result
    - cluster count
    - chosen pipeline ("native" vs "ocr")

### Reasoning
This avoids OCR when native text is strong, and prevents unnecessary noise and latency.

## Phase 1: Column Boundaries from OCR Header (PR-Size)
### Objective
Use OCR header words to define column boundaries and assign each OCR element to a column.

### New Files
- `lib/features/pdf/services/ocr/header_column_detector.dart`
  - Detect header row by keywords and Y clustering.
  - Compute boundary midpoints between header columns.
  - Confidence score based on number of headers found and alignment consistency.

### Changes
- `lib/features/pdf/services/ocr/ocr_row_reconstructor.dart`
  - Add a column-aware reconstruction method:
    - Assign each OCR element to a column based on X position.
    - Construct `OcrRow` with field-specific column text.

### Reasoning
OCR elements have bounding boxes, but the current reconstructor ignores columns. This is the main cause of mixed fields.

## Phase 2: Table Line Detection (PR-Size)
### Objective
Detect vertical grid lines from the rendered image and use them as ground-truth column boundaries.

### New Files
- `lib/features/pdf/services/ocr/table_line_detector.dart`
  - Grayscale, threshold, scan for vertical runs.
  - Cluster X positions into line candidates.
  - Convert line positions into column boundaries.

### Changes
- `lib/features/pdf/services/ocr/column_detector.dart`
  - Unified interface:
    - Try header-based detection first.
    - If low confidence or missing headers, use line detection.
    - Cross-validate and choose best.

### Reasoning
Grid lines are the most reliable signal. This path handles PDFs where header OCR is noisy or missing.

## Phase 3: OCR Pipeline Integration (PR-Size)
### Objective
Wire column detection into the OCR-first pipeline.

### Changes
- `lib/features/pdf/services/pdf_import_service.dart`
  - After OCR produces `OcrElements`, run `ColumnDetector`.
  - Pass `ColumnBoundaries` into `OcrRowReconstructor`.
  - Use `OcrRowParser` to parse per-column fields.
- `lib/features/pdf/services/ocr/ocr_row_reconstructor.dart`
  - Support both current behavior and column-aware behavior (feature flag or optional parameter).

### Reasoning
This ensures OCR output is structured before parsing, preventing description/price mixing.

## Phase 4: Guardrails for 200 DPI and Performance (PR-Size)
### Objective
Ensure OCR stays within memory/time budgets and remains stable across devices.

### Guardrails
- Limit DPI dynamically based on:
  - page dimensions
  - device memory class
  - current page count
- Default target: 200 DPI, but reduce to 150 if:
  - page render > N ms
  - memory usage exceeds threshold
  - page count > 25

### Changes
- `lib/features/pdf/services/ocr/pdf_page_renderer.dart`
  - Implement adaptive DPI with clear logging.
- `lib/features/pdf/services/pdf_import_service.dart`
  - Log chosen DPI and reason.

### Reasoning
200 DPI is often ideal for OCR, but forcing it everywhere risks latency and memory spikes.

## Phase 5: Verification & Regression Tests (PR-Size)
### Objective
Prove extraction is stable and prevent regressions.

### Tests
- Unit tests for:
  - Header detection (`header_column_detector.dart`)
  - Line detection (`table_line_detector.dart`)
  - Column assignment logic
- End-to-end fixture:
  - Use the Springfield PDF pages as a fixture for CI checks.

### Files
- `test/features/pdf/ocr/header_column_detector_test.dart`
- `test/features/pdf/ocr/table_line_detector_test.dart`
- `test/features/pdf/ocr/ocr_row_reconstructor_test.dart`

### Reasoning
Parsing issues are subtle; regression tests ensure the fix holds.

## Risk Mitigations
- If text extraction is good, OCR is skipped entirely.
- If header detection fails, line detection provides fallback.
- If line detection fails (no lines), revert to header or use conservative defaults.
- Always log which path was chosen and why.

## Acceptance Criteria
- Extract 131 items with correct columns from the Springfield PDF.
- No prices in description fields.
- No missing quantities when table shows them.
- OCR used only when native text fails.

## Implementation Order (PR Phases)
1) Diagnostics + native gate (fastest ROI)
2) Header-based column detection + column-aware row reconstruction
3) Table line detection + column detector
4) OCR pipeline wiring + guardrails
5) Tests + fixture coverage

## File References
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/pdf/services/parsers/column_layout_parser.dart`
- `lib/features/pdf/services/parsers/parser_diagnostics.dart`
- `lib/features/pdf/services/ocr/ocr_row_reconstructor.dart`
- `lib/features/pdf/services/ocr/ml_kit_ocr_service.dart`
- `lib/features/pdf/services/ocr/pdf_page_renderer.dart`
- `lib/features/pdf/services/ocr/image_preprocessor.dart`

