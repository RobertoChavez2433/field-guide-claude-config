# Dependency Graph: PDF Grid And OCR Hardening Wave 1

Date: 2026-03-13
Author: Codex
Related spec: `../../specs/2026-03-13-pdf-grid-ocr-hardening-codex-spec.md`

## Scope

Wave 1 is intentionally limited to upstream stages:

- Stage `2B-ii.6` grid cleanup
- Stage `2B-iii` cell OCR
- shared diagnostics and evaluation harnesses needed to judge those stages

Explicitly out of scope for implementation in this wave:

- Stage `4A` row-classification behavior changes
- Stage `4A.5` row-merging behavior changes
- Stage `4D+` parser, post-processing, and downstream repair heuristics

## Primary Runtime Path

1. [extraction_pipeline.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart)
   - orchestrates Stage `2B-ii.6` and Stage `2B-iii`
   - emits `onStageOutput` and `onDiagnosticImage`
2. [grid_line_remover.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/grid_line_remover.dart)
   - removes detected grid lines and inpaints cleaned pages
   - emits grid-removal metrics consumed by reports
3. [text_recognizer_v2.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart)
   - computes cell crops
   - prepares crops for OCR
   - selects OCR configs and retries
   - emits OCR metrics and diagnostics
4. [crop_ocr_stats.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/ocr/crop_ocr_stats.dart)
   - aggregates crop geometry, upscaling, and residue metrics for Stage `2B-iii`

## Adjacent Consumers

- [cell_extractor_v2.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/cell_extractor_v2.dart)
  - downstream consumer of OCR element geometry and row structure
  - not a wave-1 edit target, but affected by OCR element quality
- [row_classifier_v3.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/row_classifier_v3.dart)
  - downstream consumer of OCR element quality
  - remains read-only context for this wave
- [row_merger.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/row_merger.dart)
  - downstream consumer of row typing
  - remains read-only context for this wave

## Diagnostic And Evaluation Entry Points

- [integration_test/tmp_pdf_debug_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/integration_test/tmp_pdf_debug_test.dart)
  - current crop/image dump harness
  - likely expanded or paired with a cell-evaluation harness
- [integration_test/springfield_report_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/integration_test/springfield_report_test.dart)
  - end-to-end verification after cell-level acceptance
- [stage_2b_text_recognizer_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart)
  - primary unit test surface for OCR policy changes
- [grid_line_remover_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/grid_line_remover_test.dart)
  - primary unit test surface for conservative grid-tuning changes
- [stage_2b6_to_2biii_contract_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart)
  - contract coverage across grid removal and OCR stages

## New Artifacts Expected In Wave 1

- a dedicated cell-level OCR evaluation harness under `test/features/pdf/extraction/` or `integration_test/`
- fixture/corpus metadata for selected cell crops
- possibly new test helpers for candidate scoring and OCR-profile comparisons

## Change Clusters

### Cluster A: OCR Policy Core

- [text_recognizer_v2.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart)
- [crop_ocr_stats.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/ocr/crop_ocr_stats.dart)
- [stage_2b_text_recognizer_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart)

### Cluster B: Grid Cleanup Core

- [grid_line_remover.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/grid_line_remover.dart)
- [grid_line_remover_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/grid_line_remover_test.dart)
- [stage_2b6_to_2biii_contract_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart)

### Cluster C: Harness And Report Verification

- [integration_test/tmp_pdf_debug_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/integration_test/tmp_pdf_debug_test.dart)
- [integration_test/springfield_report_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/integration_test/springfield_report_test.dart)
- test report outputs under `test/features/pdf/extraction/reports/`

## Architectural Notes

- The pipeline already gives a clean upstream seam between grid removal and OCR; wave 1 should exploit that seam rather than compensating in Stage 4.
- `TextRecognizerV2` currently owns both crop generation and OCR policy. That makes it the highest-value file for first-pass and retry redesign.
- `GridLineRemover` metrics currently overstate confidence because page-level cleanliness does not guarantee crop-level cleanliness; diagnostics must stay coupled to crop evaluation.
