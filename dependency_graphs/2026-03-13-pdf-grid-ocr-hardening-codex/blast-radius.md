# Blast Radius: PDF Grid And OCR Hardening Wave 1

Date: 2026-03-13
Author: Codex
Related spec: `../../specs/2026-03-13-pdf-grid-ocr-hardening-codex-spec.md`

## Expected File Edits

### High-confidence edit targets

- [text_recognizer_v2.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart)
- [crop_ocr_stats.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/ocr/crop_ocr_stats.dart)
- [grid_line_remover.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/grid_line_remover.dart)
- [stage_2b_text_recognizer_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart)
- [grid_line_remover_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/grid_line_remover_test.dart)
- [stage_2b6_to_2biii_contract_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart)
- [tmp_pdf_debug_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/integration_test/tmp_pdf_debug_test.dart)

### Likely new files

- a cell-level OCR evaluation harness
- one or more fixture metadata files for the balanced crop corpus
- possibly helper utilities under `test/features/pdf/extraction/helpers/`

### Read-only but verification-critical files

- [row_classifier_v3.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/row_classifier_v3.dart)
- [row_merger.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/row_merger.dart)
- [cell_extractor_v2.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/cell_extractor_v2.dart)
- [springfield_report_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/integration_test/springfield_report_test.dart)

## Behavioral Risks

### OCR policy risks

- `description` first-pass changes can improve multiline crops but regress short single-line descriptions if acceptance logic is weak.
- `item_number` candidate scoring can accidentally prefer shorter but cleaner-looking numeric tokens if structural scoring is underweighted.
- retry inflation can increase runtime sharply if image/result gating is too permissive.

### Grid tuning risks

- conservative fringe expansion can still nick adjacent glyph strokes if mask growth is not bounded by line geometry.
- inpaint tuning can make narrow digits softer even when line removal improves.
- page-level metrics can appear improved while crop-level OCR worsens.

### Diagnostics risks

- residue metrics are currently unreliable; changing behavior before fixing those metrics could mislead tuning.
- harness-only measurements can drift from real pipeline behavior if the harness bypasses actual OCR prep or candidate selection.

## Explicit Non-goals To Protect

These files should not be modified in wave 1 unless new evidence proves Stage 2 is no longer the blocker:

- [row_classifier_v3.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/row_classifier_v3.dart)
- [row_merger.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/row_merger.dart)
- [cell_extractor_v2.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/cell_extractor_v2.dart)
- parser/post-processing stages downstream of cell extraction

## Verification Surfaces

### Unit and contract tests

- `flutter test test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart`
- `flutter test test/features/pdf/extraction/stages/grid_line_remover_test.dart`
- `flutter test test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart`

### Cell-level harness validation

- new crop corpus evaluation command
- expected output: per-column pass rates, candidate win rates, no control regressions

### End-to-end validation

- `flutter test integration_test/tmp_pdf_debug_test.dart -d windows --dart-define=SPRINGFIELD_PDF=...`
- `flutter test integration_test/springfield_report_test.dart -d windows --dart-define=SPRINGFIELD_PDF=...`
- expected output: stronger upstream cell reads before any downstream stage changes

## Review Findings Folded Into Plan

- keep a strict boundary between OCR recovery and row inference
- define acceptance rules per column before changing retry behavior
- require crop-level diagnostics and cell-level scoring before trusting grid-tuning improvements
