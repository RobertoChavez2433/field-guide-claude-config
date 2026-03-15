# PDF Grid And OCR Hardening Wave 1 Plan

Date: 2026-03-13
Author: Codex
Status: Ready for approval
Related spec: `../specs/2026-03-13-pdf-grid-ocr-hardening-codex-spec.md`
Related review: `../adversarial_reviews/2026-03-13-pdf-grid-ocr-hardening-codex/review.md`
Dependency graph: `../dependency_graphs/2026-03-13-pdf-grid-ocr-hardening-codex/dependency-graph.md`
Blast radius: `../dependency_graphs/2026-03-13-pdf-grid-ocr-hardening-codex/blast-radius.md`

## Objective

Implement wave 1 as a strictly upstream hardening pass for:

- Stage `2B-ii.6` grid cleanup
- Stage `2B-iii` cell OCR

Wave 1 must not compensate downstream. No row-classifier, row-merger, parser, or post-processing heuristics are part of this plan unless the upstream stages become strong and new evidence proves another root cause.

## Success Gate

Approve wave 1 only if all of the following are true:

- cell-level evaluation harness exists and is runnable
- `item_number` and `description` cell accuracy materially improve on a balanced crop corpus
- control cells in the other four columns do not regress materially
- crop-level border/grid residue is reduced without visible text erosion
- Springfield end-to-end totals improve as a consequence of upstream gains, not downstream compensation

## Phase 0: Baseline And Harness Foundation

### Sub-phase 0.1: Freeze the current upstream baseline

1. Read and archive the latest Springfield artifacts before changing behavior.
   Files:
   - [report.json](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/reports/latest-windows/report.json)
   - [scorecard.md](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/reports/latest-windows/scorecard.md)
   - [debug_ocr_crops](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/debug_ocr_crops)
2. Record the confirmed wave-1 failures in plan notes:
   - multiline description crops blank under `psm 7`
   - item-number retry can degrade a valid first-pass read
   - crop-edge rails remain after grid removal
3. Do not alter downstream fixtures yet.

Verification:
```powershell
Get-ChildItem test/features/pdf/extraction/reports/latest-windows
Get-ChildItem test/features/pdf/extraction/debug_ocr_crops | Select-Object -First 20 Name
```
Expected outcome:
- latest report and crop corpus are present and readable

### Sub-phase 0.2: Build the balanced cell-evaluation corpus

1. Create a corpus metadata file under `test/features/pdf/extraction/` that lists:
   - crop path
   - page/row/column
   - expected text
   - column semantic
   - tags such as `multiline`, `item_anchor`, `numeric_control`, `border_residue_visible`
2. Seed the corpus with both failing and passing crops across all six columns.
3. Ensure the corpus includes:
   - failing multiline descriptions
   - known item-anchor risk cells
   - numeric control cells that already read correctly
   - at least a small set of clean controls per column

Files to create:
- `test/features/pdf/extraction/ocr_cell_corpus.json` or similar

Verification:
- corpus file can be loaded by Dart tests
- corpus includes all six columns and both pass/fail examples

### Sub-phase 0.3: Build the cell-level OCR evaluation harness

1. Add a dedicated harness that can run OCR policies against the saved crop corpus without requiring full document extraction.
2. The harness must execute the same OCR-prep and candidate-selection logic used by [text_recognizer_v2.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart), or explicitly share that logic.
3. Emit a report containing:
   - first-pass output
   - retry/fallback outputs
   - chosen output
   - candidate scores
   - acceptance reason
   - pass/fail vs expected
4. Save results into a stable output folder under `.claude/test-results/` or `test/features/pdf/extraction/reports/`.

Files to create or modify:
- new harness under `test/features/pdf/extraction/` or `integration_test/`
- helper utilities under `test/features/pdf/extraction/helpers/` if needed

Verification commands:
```powershell
flutter test <new_cell_harness_test>
```
Expected outcome:
- harness runs locally without the full pipeline
- per-column accuracy summary is produced

## Phase 1: Fix Diagnostics Before Tuning Behavior

### Sub-phase 1.1: Repair residue metrics

1. Audit [text_recognizer_v2.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart) crop residue measurement.
2. Audit [crop_ocr_stats.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/ocr/crop_ocr_stats.dart) aggregation and serialization.
3. Fix the saturation bug that currently reports `1.0` for average dark/edge fractions.
4. Add targeted tests proving residue metrics differ between:
   - empty/clean crops
   - crops with dark edge rails
   - crops with interior text only

Files to modify:
- [text_recognizer_v2.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart)
- [crop_ocr_stats.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/ocr/crop_ocr_stats.dart)
- [stage_2b_text_recognizer_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart)

Verification commands:
```powershell
flutter test test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart
```
Expected outcome:
- residue metrics are bounded and non-saturated
- tests prove metrics distinguish crop conditions

### Sub-phase 1.2: Improve per-cell decision observability

1. Extend OCR reporting so each evaluated crop can expose:
   - first-pass profile
   - fallback profiles tried
   - chosen candidate
   - reason chosen
2. Keep this instrumentation test/debug oriented.
3. Ensure report naming is generic and reusable beyond Springfield.

Files to modify:
- [text_recognizer_v2.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart)
- harness/report helper files created in Phase 0

Verification:
- harness output includes candidate-by-candidate trace
- stage report still serializes cleanly

## Phase 2: OCR Policy Redesign

### Sub-phase 2.1: Refactor OCR policy model into first-pass and candidate stacks

1. Replace row-inherited first-pass behavior with true column-owned policy behavior.
2. Keep policies explicit for all six columns.
3. Make policy definitions data-driven in one central map or configuration section.
4. Define acceptance rules before changing runtime behavior.

Files to modify:
- [text_recognizer_v2.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart)
- [stage_2b_text_recognizer_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart)

Verification:
- policy coverage test proves every column has an explicit first-pass and fallback contract

### Sub-phase 2.2: Make description first pass truly multiline-aware

1. Change `description` first pass to use a multiline-friendly OCR profile instead of inheriting `rowPsm`.
2. Add result-plus-image gating for `description` fallback.
3. Keep retries conditional:
   - blank output
   - implausibly short output for crop geometry
   - low-signal/noisy output with visible ink
4. Add candidate selection rules that prefer text completeness and coherent alpha-token coverage.

Files to modify:
- [text_recognizer_v2.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart)
- [stage_2b_text_recognizer_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart)
- new harness fixtures/tests as needed

Verification commands:
```powershell
flutter test test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart
flutter test <new_cell_harness_test>
```
Expected outcome:
- multiline description failures improve on the corpus
- single-line controls do not regress materially

### Sub-phase 2.3: Replace item-number single-fallback trust with candidate scoring

1. Keep `psm 8 + whitelist` as one candidate, not the automatic winner.
2. Score candidate outputs using:
   - exact item-token shape
   - digit preservation
   - absence of alpha contamination
   - confidence
3. Use neighboring sequence only as a weak tie-breaker.
4. Explicitly reject fallback candidates that degrade a valid first-pass item token.

Files to modify:
- [text_recognizer_v2.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart)
- [stage_2b_text_recognizer_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart)
- corpus harness files from Phase 0

Verification:
- a test reproduces the `119 -> 18` degradation risk and proves the selector rejects the degraded candidate
- corpus report shows improved item-anchor accuracy with no control regressions

### Sub-phase 2.4: Keep the remaining columns stable and observable

1. Leave `unit`, `quantity`, `unit_price`, and `bid_amount` mostly intact in wave 1.
2. Add or update control tests so grid and OCR changes cannot silently regress these columns.
3. Use these columns as regression guards rather than first-wave redesign targets.

Files to modify:
- [stage_2b_text_recognizer_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart)
- harness corpus metadata and expected results

Expected outcome:
- no material drop in control-column accuracy while item/description improve

## Phase 3: Conservative Grid Fringe Tuning

### Sub-phase 3.1: Reproduce residue against repaired diagnostics

1. Use the repaired residue metrics plus saved crop images to identify remaining border rails.
2. Confirm the issue is anti-aliased fringe around detected lines, not broad text contamination.
3. Document representative before/after cells in plan notes or test comments.

Files to read and possibly update:
- [grid_line_remover.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/grid_line_remover.dart)
- [tmp_pdf_debug_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/integration_test/tmp_pdf_debug_test.dart)

Verification:
- crop examples show reproducible residue before tuning

### Sub-phase 3.2: Apply conservative fringe expansion

1. Tune mask growth to cover line fringe, not to remove more arbitrary content.
2. Keep horizontal and vertical behavior separated.
3. Preserve the surgical coordinate model and avoid broad morphological clipping.
4. Keep inpaint conservative and text-safe.

Files to modify:
- [grid_line_remover.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/grid_line_remover.dart)
- [grid_line_remover_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/grid_line_remover_test.dart)
- [stage_2b6_to_2biii_contract_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart)

Verification commands:
```powershell
flutter test test/features/pdf/extraction/stages/grid_line_remover_test.dart
flutter test test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart
```
Expected outcome:
- residue decreases on affected crop examples
- no new text clipping failures appear in tests

### Sub-phase 3.3: Stop before adaptive per-line modeling unless needed

1. Re-run the cell harness after conservative tuning.
2. If residue remains but controls are safe, document whether adaptive per-line fringe estimation is needed for a later wave.
3. Do not escalate to per-line adaptation in wave 1 unless conservative tuning clearly fails and evidence is strong.

Stop condition:
- if conservative tuning regresses OCR controls, revert the tuning direction and keep OCR policy gains only

## Phase 4: Integrated Upstream Verification

### Sub-phase 4.1: Cell-harness acceptance pass

1. Run the full balanced corpus through the new OCR policy and grid-tuning stack.
2. Compare against the frozen baseline from Phase 0.
3. Summarize:
   - per-column accuracy
   - failing-to-passing recoveries
   - passing-to-failing regressions
   - candidate win rates
   - residue correlation

Verification command:
```powershell
flutter test <new_cell_harness_test>
```
Expected outcome:
- `item_number` and `description` improve materially
- no unacceptable regressions in the other columns

### Sub-phase 4.2: End-to-end Springfield reruns

1. Re-run the crop/debug harness.
2. Re-run the full Springfield report.
3. Inspect whether known merged-row artifacts decrease without changing Stage 4 logic.

Verification commands:
```powershell
$pdf = 'C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf'
flutter test integration_test/tmp_pdf_debug_test.dart -d windows "--dart-define=SPRINGFIELD_PDF=$pdf"
flutter test integration_test/springfield_report_test.dart -d windows "--dart-define=SPRINGFIELD_PDF=$pdf"
```
Expected outcome:
- improved cell-level outputs in saved crops
- improved Springfield item recovery and fewer merged logical rows
- any remaining failures are cleaner and farther downstream

## Phase 5: Review, Cleanup, And Commit Readiness

### Sub-phase 5.1: Manual review round

Perform one review pass with code-review and security lenses:

- confirm row-inference boundaries were preserved
- confirm no production-only diagnostic leakage was introduced
- confirm policy definitions remain centralized and testable
- confirm no hidden Springfield-only rules slipped in

Expected outcome:
- no CRITICAL or HIGH findings blocking implementation readiness

### Sub-phase 5.2: Cleanup

1. Remove dead experimental branches in the OCR policy code.
2. Keep the debug crop harness, but document it as intentional workflow support.
3. Ensure generated crop/report outputs remain ignored and are not accidentally staged.
4. Update plan/spec references if artifact names change.

Files to verify:
- [.gitignore](/C:/Users/rseba/Projects/Field_Guide_App/.gitignore)
- [tmp_pdf_debug_test.dart](/C:/Users/rseba/Projects/Field_Guide_App/integration_test/tmp_pdf_debug_test.dart)

## Test Matrix

Run at minimum:

```powershell
flutter test test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart
flutter test test/features/pdf/extraction/stages/grid_line_remover_test.dart
flutter test test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart
flutter test test/features/pdf/extraction/pipeline/extraction_pipeline_test.dart
flutter test <new_cell_harness_test>
dart analyze lib/features/pdf/services/extraction/ocr/crop_ocr_stats.dart lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart lib/features/pdf/services/extraction/stages/grid_line_remover.dart
```

If Windows integration remains available, also run:

```powershell
$pdf = 'C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf'
flutter test integration_test/tmp_pdf_debug_test.dart -d windows "--dart-define=SPRINGFIELD_PDF=$pdf"
flutter test integration_test/springfield_report_test.dart -d windows "--dart-define=SPRINGFIELD_PDF=$pdf"
```

## Expected Deliverables

- repaired crop residue diagnostics
- dedicated cell-level OCR evaluation harness and corpus
- column-aware multiline description policy
- scored item-number candidate selection
- conservative grid fringe tuning with tests
- updated Springfield report showing improved upstream behavior

## Review Outcome Folded Into This Plan

The prior adversarial review requirements are preserved here:

- no row-inference compensation in wave 1
- explicit per-column acceptance rules before retry redesign
- crop-level diagnostics are mandatory and part of the success gate
