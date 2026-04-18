# PDF Extraction Post-100 Decomposition And Trace To-Do

Created: 2026-04-16

This is the post-100% structural hardening checklist for the PDF extraction
pipeline. Completion means the full cached corpus remains at zero asserted
mismatches and zero trace-contract failures while the new 100% heuristics are
split into focused production/test seams and every field-changing repair stays
traceable through inputs, outputs, decisions, mutations, and provenance.

## Current Baseline

- [x] Full cached corpus reached `0` asserted mismatches and `0`
      trace-contract failures in:
      `.claude/test-results/2026-04-15/pdf-extraction-replay-audit-202957-full_corpus_after_final_ocr_context_repairs_20260415_01/audit-summary.md`.
- [x] Original-four replay reached `0` asserted mismatches and `0`
      trace-contract failures in:
      `.claude/test-results/2026-04-15/pdf-extraction-replay-audit-202534-original_four_after_final_ocr_context_repairs_20260415_01/audit-summary.md`.
- [x] No ground-truth fixtures were edited for the 100% pass.

## Audit Findings

- [x] Production god-class audit completed.
  - `post_process_utils.dart` was the top new god-class risk because it mixed
    description artifact cleanup, construction OCR word repairs, unit recovery,
    numeric parsing, price parsing, currency heuristics, and rounding.
  - `row_parser_data_row_parser.dart` remains a follow-up risk because `parse`
    owns bid-tab fast path, cell parsing, schedule repair, fallback parsing,
    sequence rescue, pending-prefix handling, skip decisions, assembly, and
    trace sample construction.
  - `item_deduplication_workflow.dart` remains a provenance follow-up because
    duplicate candidates need stable source-candidate identity in addition to
    field before/after maps.
  - `value_normalizer.dart` remains a provenance follow-up because repair notes
    are keyed by item number and should carry the best available source item
    snapshot/provenance for missing or later-rewritten item numbers.
- [x] Test god-class audit completed.
  - `artifact_cleaning_rules_test.dart` is the first test split target.
  - Additional follow-up targets: `re_extraction_loop_test.dart`,
    `mp_extraction_service_test.dart`, row/element contract tests, and broad
    PDF test helper hubs.

## Production Decomposition Queue

- [x] Split `PostProcessUtils` into focused seams while preserving its public
      compatibility facade.
  - [x] `post_process_utils.dart` is now a thin facade.
  - [x] `description_artifact_cleaner.dart` owns description artifact rule
        orchestration.
  - [x] `construction_description_ocr_word_fixes.dart` owns construction OCR
        word repair chunks.
  - [x] `unit_text_normalizer.dart` owns unit token cleanup and recovery.
  - [x] `numeric_value_parser.dart` owns quantity/currency parse, validation,
        token-shape heuristics, and rounding.
- [ ] Split `RowParserDataRowParser.parse` into focused row-data parse phases.
  - [x] Bid-tab fast path must emit a row-level trace decision/sample before
        returning.
  - [x] No-item-number skip must emit a structured decision with row
        provenance.
  - [x] Section-total skip must emit a structured decision with row
        provenance.
  - [x] No-numeric-payload skip must emit decision/provenance for the skip and
        pending-prefix decision.
  - [x] Extract trace sample construction into a trace helper/emitter rather
        than keeping it in the parser.
- [x] Strengthen duplicate repair provenance.
  - [x] Carry stable duplicate candidate/source identity through
        `RepairEntry` details.
  - [x] Preserve all duplicate candidate source snapshots instead of relying
        only on maps keyed by final item number.
- [x] Strengthen value-normalizer provenance.
  - [x] Include source item snapshots/provenance in repair details when the
        item number is missing, repaired, or ambiguous.
  - [ ] Keep quantity/unit/description context repairs in separate helper
        classes if `value_normalizer.dart` grows further.
- [ ] Reassess `layout_classifier.dart` after row parser and post-processing
      splits; split signal collection, source selection, and policy selection
      only if it starts to grow beyond focused ownership.

## Test Decomposition Queue

- [x] Split `artifact_cleaning_rules_test.dart` by repair family.
  - [x] Core punctuation/spacing and measurement artifact repairs.
  - [x] Construction-description OCR recovery.
  - [ ] Pavement-marking repairs.
  - [ ] Class-code preservation/normalization policy.
- [ ] Split `re_extraction_loop_test.dart` by retry policy, source selection,
      cache reuse, trace contracts, and attempt tracking.
- [ ] Split `mp_extraction_service_test.dart` into behavior-only and
      trace-only files.
- [ ] Split oversized contract tests by scenario family before adding more
      contract cases.
- [ ] Split broad helper hubs only when a touched test would otherwise grow a
      hidden setup god-helper.

## Trace And Logging Acceptance

- [x] Every extracted production unit emits or contributes to stage trace data.
- [x] Every final field mutation has stable `ruleName`, `reasonCode`, mutation
      kind/status, before value, after value, and source provenance.
- [x] Every skip/early-return path that changes output emits an explicit
      decision record.
- [x] Top-level stage traces remain readable by existing replay/debug tooling.
- [x] Full cached-corpus replay remains at `0` asserted mismatches and `0`
      trace-contract failures after the structural refactor.

## Verification Log

- [x] `dart analyze lib/features/pdf/services/extraction/shared/post_process_utils.dart lib/features/pdf/services/extraction/shared/description_artifact_cleaner.dart lib/features/pdf/services/extraction/shared/construction_description_ocr_word_fixes.dart lib/features/pdf/services/extraction/shared/unit_text_normalizer.dart lib/features/pdf/services/extraction/shared/numeric_value_parser.dart`
      passed after the post-processing facade split.
- [x] `dart analyze lib/features/pdf/services/extraction/shared/post_process_utils.dart lib/features/pdf/services/extraction/shared/description_artifact_cleaner.dart lib/features/pdf/services/extraction/shared/construction_description_ocr_word_fixes.dart lib/features/pdf/services/extraction/shared/unit_text_normalizer.dart lib/features/pdf/services/extraction/shared/numeric_value_parser.dart lib/features/pdf/services/extraction/models/processed_items.dart lib/features/pdf/services/extraction/stages/post_processing_stage_support.dart lib/features/pdf/services/extraction/stages/item_deduplication_workflow.dart lib/features/pdf/services/extraction/stages/value_normalizer.dart lib/features/pdf/services/extraction/stages/row_parser_data_row_parser.dart lib/features/pdf/services/extraction/stages/row_parser_data_row_trace_emitter.dart test/features/pdf/extraction/stages/post_processing/artifact_cleaning_rules_test.dart test/features/pdf/extraction/stages/post_processing/artifact_cleaning_construction_ocr_rules_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_test.dart`
      passed after provenance and row-data trace changes.
- [x] `flutter test test/features/pdf/extraction/stages/post_processing/artifact_cleaning_rules_test.dart test/features/pdf/extraction/stages/post_processing/artifact_cleaning_construction_ocr_rules_test.dart test/features/pdf/extraction/stages/post_processing/artifact_cleaning_unit_rules_test.dart test/features/pdf/extraction/stages/post_processing/artifact_cleaning_description_repair_test.dart test/features/pdf/extraction/shared/post_process_utils_test.dart -d windows`
      passed `28/28`.
- [x] `flutter test test/features/pdf/extraction/stages/item_deduplicator_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_trace_test.dart test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
      passed `16/16`.
- [x] `flutter test test/features/pdf/extraction/stages/post_processing/repair_log_test.dart test/features/pdf/extraction/stages/item_deduplicator_test.dart -d windows`
      passed `11/11` after adding source-provenance assertions.
- [x] Original-four replay:
      `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_after_post100_decomposition_trace_refactor_20260416_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
      passed.
  - Audit:
    `.claude/test-results/2026-04-15/pdf-extraction-replay-audit-205253-original_four_after_post100_decomposition_trace_refactor_20260416_01/audit-summary.md`.
  - Result: `0` asserted mismatches, `0` trace-contract failures.
- [x] Full cached-corpus replay:
      `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_after_post100_decomposition_trace_refactor_20260416_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
      passed.
  - Audit:
    `.claude/test-results/2026-04-15/pdf-extraction-replay-audit-205724-full_corpus_after_post100_decomposition_trace_refactor_20260416_01/audit-summary.md`.
  - Result: `0` asserted mismatches, `0` trace-contract failures.
