# Table-Aware PDF Extraction V3 - Completion Plan (PR Phases)

Location: C:\Users\rseba\Projects\Field Guide App\.claude\plans\table-aware-pdf-extraction-v3-completion.md

## Goal
Finish the V3 pipeline so it is feature-complete against the original plan and acceptance criteria. This plan focuses on the gaps that remain in the current codebase and organizes them into PR-sized phases.

## Scope Summary (Current Gaps)
- Line-based column detection produces unnamed col_# columns, but the parser expects semantic column names.
- Cell-level re-OCR is not implemented (merged blocks never reprocessed).
- Line detection uses hard-coded image size instead of actual render size.
- Progress dialog exists but is not wired into the import flows.
- Row boundary detection does not use grid lines.
- Integration tests are placeholder; no real fixtures or Springfield data used.

---

## PR 1: Column Naming + Line Detection Dimension Fix

Purpose: Make line-based detection compatible with parsing and ensure grid-line detection uses actual image dimensions.

### Changes
- Map line-based column boundaries to semantic names to avoid empty fields when line detection is selected.
  - Options (choose one implementation):
    - Header-assisted mapping: if header columns exist, snap line-based boundaries to the nearest header column centers and reuse header names.
    - Ratio-based naming fallback: when headers are missing, apply the standard ratios to assign semantic names to the line-based segments in left-to-right order.
- Pass real render dimensions into column detection rather than hard-coded defaults.

### Files
- Update lib/features/pdf/services/table_extraction/column_detector.dart
  - Logic to reconcile line-based results with semantic names.
  - Ensure cross-validation returns semantic names even when line-based chosen.
- Update lib/features/pdf/services/table_extraction/line_column_detector.dart
  - Optionally expose raw boundary positions for mapping if needed.
- Update lib/features/pdf/services/table_extraction/table_extractor.dart
  - Use real page image width/height from OCR render pipeline (not hard-coded kDefaultImageWidth/Height).
- Update lib/features/pdf/services/pdf_import_service.dart
  - Ensure _runOcrPipeline returns width/height metadata per page or on the first page used for column detection.
  - Example: return List<({Uint8List bytes, int width, int height})> or add pageImageSizes alongside pageImages.
- Tests:
  - Update test/features/pdf/table_extraction/column_detector_test.dart to cover line-based mapping into semantic names.
  - Add test for line-based detection with headers missing (ratio fallback naming).

### Reasoning
- The current pipeline will parse empty cells if line-based detection wins. This is a hard correctness bug and must be fixed before accuracy work.
- Hard-coded image size makes line detection unreliable; correctness depends on actual pixel coordinates.

---

## PR 2: Cell-Level Re-OCR (Merged Blocks)

Purpose: Implement the cell re-OCR path to split merged text spanning multiple columns.

### Changes
- Add cell-level re-OCR to CellExtractor using MlKitOcrService.recognizeRegion.
  - Detect merged blocks (isMergedBlock) and re-OCR each column cell region.
  - Cache decoded images per page to avoid repeated decode work.
  - Set usedCellReOcr true per row when any cell is reprocessed.
- Update pipeline to count and report re-OCR usage in diagnostics.

### Files
- Update lib/features/pdf/services/table_extraction/cell_extractor.dart
  - Accept page image access and optionally a MlKitOcrService instance.
  - Add per-row re-OCR logic and set usedCellReOcr.
- Update lib/features/pdf/services/table_extraction/table_extractor.dart
  - Pass page images and OCR service into CellExtractor.
  - Ensure reOcrCells progress stage is emitted when re-OCR occurs.
- Update lib/features/pdf/services/ocr/ml_kit_ocr_service.dart
  - Confirm recognizeRegion signature fits the usage and returns cleaned text.
- Tests:
  - Add or extend test/features/pdf/table_extraction/cell_extractor_test.dart to verify merged block re-OCR and usedCellReOcr true.

### Reasoning
- This is a core strategy in the original plan to resolve merged OCR blocks and prevent price/qty contamination across columns.

---

## PR 3: Row Boundary Detection via Grid Lines

Purpose: Improve row extraction accuracy on table grids by detecting horizontal lines rather than only Y-clustering.

### Changes
- Extend LineColumnDetector or create a small helper to detect horizontal grid lines and return Y positions.
- Modify CellExtractor to use detected row boundaries when available (fallback to Y-clustering when not).

### Files
- Add lib/features/pdf/services/table_extraction/row_boundary_detector.dart (new helper) or extend line_column_detector.dart.
- Update lib/features/pdf/services/table_extraction/cell_extractor.dart
  - Use row boundaries when available; continue to support Y-clustering fallback.
- Tests:
  - Add tests for row boundary detection using synthetic images similar to current line detector tests.

### Reasoning
- Y-clustering is fragile for dense tables. Horizontal line detection improves row grouping, especially for scanned PDFs.

---

## PR 4: Progress UI Wiring

Purpose: Surface the pipeline stages to users via the existing progress dialog.

### Changes
- Replace the generic Importing PDF... dialog with PdfImportProgressDialog and stream stage updates.
- Pass onProgress into PdfImportService.importBidSchedule from both import entry points.

### Files
- Update lib/features/projects/presentation/screens/project_setup_screen.dart
  - Use PdfImportProgressDialog and keep it updated as progress callbacks fire.
- Update lib/features/quantities/presentation/screens/quantities_screen.dart
  - Same as above.
- Update lib/features/pdf/services/pdf_import_service.dart
  - Ensure onProgress is passed through and invoked for all stages.
- Tests:
  - Widget test to confirm dialog updates on stage changes (optional if time constrained).

### Reasoning
- Progress reporting was part of acceptance criteria; the UI exists but is unused.

---

## PR 5: Integration Tests + Fixtures (Springfield)

Purpose: Validate the full pipeline against real data and acceptance criteria.

### Changes
- Add a Springfield fixture and at least one scanned or bad-text fixture.
- Replace placeholder integration tests with real assertions (count of items, column integrity, header skipping, etc.).

### Files
- Add fixtures under test/features/pdf/table_extraction/fixtures/ or test/fixtures/pdf/.
  - Example: springfield_ocr_elements.json, springfield_page1.png (or extracted OCR dump).
- Update test/features/pdf/table_extraction/integration_test.dart
  - Load real fixture data and assert:
    - Item count >= 131
    - No description contains price patterns
    - Quantities present where expected
    - Header rows skipped on pages 2+

### Reasoning
- Current tests are structural only and do not validate actual parsing accuracy.

---

## PR 6: Cleanup + Deprecation Finalization

Purpose: Finish the deprecation plan and reduce ambiguity.

### Changes
- Mark legacy parsers for eventual removal (if not already).
- Add clear diagnostics and log warnings when falling back from TableExtractor.

### Files
- lib/features/pdf/services/ocr/ocr_row_reconstructor.dart (already deprecated; confirm annotation and add migration comment if needed)
- lib/features/pdf/services/pdf_import_service.dart (log explicit fallback reason when TableExtractor produces 0 items)

### Reasoning
- Ensures the new pipeline is the primary path and legacy code is clearly transitional.

---

## Acceptance Criteria Alignment
- Extract all 131+ items from Springfield PDF with correct columns.
- No prices in description fields.
- No missing quantities when table shows them.
- Contract boilerplate not parsed as items.
- Repeated headers skipped.
- Progress UI shows stage-by-stage feedback.
- Diagnostics logged for debugging.

---

## Suggested Execution Order
1) PR 1 (column naming + dimensions)
2) PR 2 (re-OCR)
3) PR 3 (row boundaries)
4) PR 4 (progress UI)
5) PR 5 (fixtures + integration tests)
6) PR 6 (cleanup)
