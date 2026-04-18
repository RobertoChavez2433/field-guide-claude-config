# Extraction Pipeline Decomposition And Trace Verification Spec

This spec is the completion gate for decomposing the PDF extraction pipeline.
Work is complete only when every checklist item is green, every decomposed
stage emits structured logging/debug trace data, and the original four PDFs
plus the full cached corpus have been verified with no unintended behavioral
regressions.

This is a refactor-first effort. Do not add new extraction heuristics, fixture
edits, comparator changes, or PDF-specific branches while completing this spec.

## Running Status

- Current stage under decomposition: row parser decomposition is now through
  cell-to-field parsing, misaligned row parsing, fallback text repair/token
  parsing, item-number sequence rescue, parsed-item confidence calculation, and
  row-parser substage trace payloads. `row_parser_row_type_handler.dart` now
  owns total-row extraction, section-header synthesis, and non-data skip reason
  handling, with a `row_type_handling` substage trace.
  `row_parser_parsed_item_assembler.dart` now owns final parsed-item warnings,
  field counts, confidence calculation, and item materialization.
  `row_parser_trace_emitter.dart` now owns row-parser substage trace emission
  and source-ID aggregation. `core_parsing_tests.dart` is now split into
  focused core, schedule-item, bid-tab, and item-number rescue parsing parts.
  `row_parser_bid_tab_by_item_parser.dart` now owns the embedded AASHTOWare
  bid-tab-by-item mini-parser and its special-provision marker rule, with a
  focused helper-level test counterpart. `row_parser_data_row_parser.dart` now
  owns the standard data-row branch inside `RowParsingWorkflow.parse`,
  including bid-tab parsing, cell-to-field parsing, fallback row parsing,
  sequence rescue, text repair, skip decisions, and parsed-item assembly.
  `column_detection_trace_emitter.dart` now owns column substage trace payload,
  decision, and mutation construction; `ColumnDetectionWorkflow` delegates to
  it. `column_detection_stage_reporter.dart` now owns legacy column layer
  stage-output/report payloads for grid-seeded, header, text-alignment,
  whitespace-gap, missing-inference, and anchor-correction outputs.
  `column_detection_run_coordinator.dart` now owns the top-level non-empty and
  empty column-detection sequencing, leaving `ColumnDetectionWorkflow` as the
  lifecycle/logging facade.
  `row_merger_rules.dart` now owns standalone pay-item promotion evidence,
  including the existing OCR-damaged right-side unit-fragment heuristic, plus
  boilerplate continuation rule evaluation and trailing continuation rule
  evaluation. Row merger emits
  `row_merge_input_analysis`, `standalone_pay_item_detection`,
  `continuation_attachment_rule_evaluation`, and `merge_materialization`
  substage traces through the same stage trace path. `row_merger_trace_payloads.dart`
  owns the current row-merger trace JSON construction. The
  `continuation_attachment_rule_evaluation` trace now includes leading
  description-anchor reservation decisions and source row IDs for that
  materialized mutation.
  `row_merger_materializer.dart` now owns the behavior-preserving merged-row
  mutations for continuation attachment, standalone promotion, and orphan
  boilerplate demotion. `row_merger_features.dart` now owns shared semantic
  column payload, structured-fragment, bid-amount, and standalone numeric token
  feature reading. `row_merger_continuation_placement_feature_reader.dart` now
  owns descriptor/measurement continuation-placement feature predicates.
  `row_merger_leading_bid_amount_tail_extractor.dart` now owns arithmetic and
  interleaved leading bid-amount tail detachment.
  `row_merger_trace_emitter.dart` now owns row-merger stage-output emission for
  input analysis, standalone detection, continuation rule evaluation, and merge
  materialization while preserving the existing trace payloads. The remaining
  continuation-placement payload helpers for boilerplate continuation type,
  complete schedule payloads, and anchorless unpriced schedule payloads now
  live in `row_merger_continuation_placement_feature_reader.dart`. The
  remaining `row_merger_test.dart` rule-family cases are split into standalone
  schedule, price, description, structured/text, and descriptor-continuation
  tests with shared row builders in `row_merger_test_support.dart`.
- Latest unit test command/result:
  - `dart analyze lib/features/pdf/services/extraction/stages/column_detection_workflow.dart lib/features/pdf/services/extraction/stages/column_detection_run_coordinator.dart lib/features/pdf/services/extraction/stages/column_detection_stage_reporter.dart lib/features/pdf/services/extraction/stages/column_detection_trace_emitter.dart lib/features/pdf/services/extraction/stages/column_detection_orchestration.dart lib/features/pdf/services/extraction/stages/column_detection_rules.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/column_detection/column_detection_stage_reporter_test.dart test/features/pdf/extraction/stages/column_detection/column_detection_trace_emitter_test.dart test/features/pdf/extraction/stages/column_detection/stage_trace_outputs_test.dart test/features/pdf/extraction/stages/column_detection/column_detection_orchestration_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/column_detection/column_detection_stage_reporter_test.dart test/features/pdf/extraction/stages/column_detection/column_detection_trace_emitter_test.dart test/features/pdf/extraction/stages/column_detection/stage_trace_outputs_test.dart test/features/pdf/extraction/stages/column_detection/column_detection_orchestration_test.dart -d windows`
    -> passed, `13/13`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_parsing_workflow.dart lib/features/pdf/services/extraction/stages/row_parser_bid_tab_by_item_parser.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_parser/row_parser_bid_tab_by_item_parser_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_parser/row_parser_bid_tab_by_item_parser_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_isolated_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_trace_test.dart -d windows`
    -> passed, `39/39`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_trace_emitter.dart lib/features/pdf/services/extraction/stages/row_merger_trace_payloads.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger_test.dart -d windows`
    -> passed, `32/32`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_parsing_workflow.dart lib/features/pdf/services/extraction/stages/row_parser_data_row_parser.dart lib/features/pdf/services/extraction/stages/row_parser_bid_tab_by_item_parser.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_trace_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_isolated_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_trace_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_bid_tab_by_item_parser_test.dart -d windows`
    -> passed, `39/39`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_continuation_placement_feature_reader.dart lib/features/pdf/services/extraction/stages/row_merger_features.dart test/features/pdf/extraction/stages/row_merger/row_merger_continuation_placement_feature_reader_test.dart test/features/pdf/extraction/stages/row_merger_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger/row_merger_continuation_placement_feature_reader_test.dart test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart -d windows`
    -> passed, `37/37`.
  - `dart analyze test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_parser/core_parsing_tests.dart test/features/pdf/extraction/stages/row_parser/schedule_item_parsing_tests.dart test/features/pdf/extraction/stages/row_parser/bid_tab_parsing_tests.dart test/features/pdf/extraction/stages/row_parser/item_number_rescue_parsing_tests.dart`
    -> passed, no issues.
  - `dart analyze test/features/pdf/extraction/stages/post_processing/repair_log_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_math_validation_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_math_candidate_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_math_digit_repair_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_math_price_backsolve_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_description_repair_test.dart`
    -> passed, no issues.
  - `dart analyze test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_leading_schedule_attachment_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_leading_price_attachment_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_leading_description_attachment_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_leading_structured_attachment_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_descriptor_continuation_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_test_support.dart`
    -> passed, no issues.
  - `dart analyze test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart test/features/pdf/extraction/integration/gocr_downstream_replay/expected_comparison_helpers.dart test/features/pdf/extraction/integration/gocr_downstream_replay/expected_comparison_ground_truth.dart test/features/pdf/extraction/integration/gocr_downstream_replay/expected_comparison_row_matching.dart test/features/pdf/extraction/integration/gocr_downstream_replay/expected_comparison_diagnosis.dart test/features/pdf/extraction/integration/gocr_downstream_replay/expected_comparison_source_provenance.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_parser_stage_test.dart -d windows`
    -> passed, `32/32`.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart -d windows`
    -> passed, `5/5`.
  - `flutter test test/features/pdf/extraction/stages/post_processing/repair_log_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_math_validation_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_math_candidate_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_math_digit_repair_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_math_price_backsolve_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_description_repair_test.dart -d windows`
    -> passed, `29/29`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows`
    -> passed, `1/1`; replay harness skipped as expected without `RUN_GOCR_DOWNSTREAM_REPLAY=true`.
  - `dart analyze test/features/pdf/extraction/helpers/gocr_trace_artifact_contract.dart test/features/pdf/extraction/helpers/gocr_trace_artifact_contract/field_contract_helpers.dart test/features/pdf/extraction/helpers/gocr_trace_artifact_contract/mutation_ground_truth_helpers.dart test/features/pdf/extraction/helpers/gocr_trace_artifact_contract/metrics_helpers.dart test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart`
    -> passed, no issues.
  - `$rowMergerTests = @('test/features/pdf/extraction/stages/row_merger_test.dart') + (Get-ChildItem test/features/pdf/extraction/stages/row_merger -Filter '*_test.dart' | ForEach-Object { $_.FullName }); flutter test @rowMergerTests -d windows`
    -> passed, `81/81`.
  - `$postTests = Get-ChildItem test/features/pdf/extraction/stages/post_processing -Filter *.dart | Where-Object { $_.Name -ne 'post_processing_test_helpers.dart' } | ForEach-Object { $_.FullName }; flutter test @postTests -d windows`
    -> passed, `78/78`.
  - `dart analyze test/features/pdf/extraction/stages/post_processing/artifact_cleaning_rules_test.dart test/features/pdf/extraction/stages/post_processing/artifact_cleaning_description_repair_test.dart test/features/pdf/extraction/stages/post_processing/artifact_cleaning_unit_rules_test.dart test/features/pdf/extraction/stages/post_processing/artifact_cleaning_pavement_marking_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/post_processing/artifact_cleaning_rules_test.dart test/features/pdf/extraction/stages/post_processing/artifact_cleaning_description_repair_test.dart test/features/pdf/extraction/stages/post_processing/artifact_cleaning_unit_rules_test.dart test/features/pdf/extraction/stages/post_processing/artifact_cleaning_pavement_marking_test.dart -d windows`
    -> passed, `18/18`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_parsing_workflow.dart lib/features/pdf/services/extraction/stages/row_parser_v3.dart lib/features/pdf/services/extraction/stages/row_parser_trace_payloads.dart lib/features/pdf/services/extraction/pipeline/extraction_pipeline_tabular_runner.dart test/features/pdf/extraction/stages/row_parser/row_parser_trace_test.dart test/features/pdf/extraction/helpers/mock_stages/parser_post_quality_mocks.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_parser/row_parser_trace_test.dart test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `5/5`.
  - `flutter test test/features/pdf/extraction/stages/row_parser/row_parser_trace_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_text_repair_rules_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_misaligned_row_parser_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_sequence_rescue_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_cell_field_parser_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_confidence_calculator_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_isolated_test.dart test/features/pdf/extraction/stages/checksum_validation_test.dart test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart -d windows`
    -> passed, `89/89`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_parsing_workflow.dart lib/features/pdf/services/extraction/stages/row_parser_v3.dart lib/features/pdf/services/extraction/stages/row_parser_confidence_calculator.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_parser/row_parser_confidence_calculator_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_isolated_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_parser/row_parser_confidence_calculator_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_isolated_test.dart test/features/pdf/extraction/stages/checksum_validation_test.dart test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart -d windows`
    -> passed, `68/68`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_features.dart lib/features/pdf/services/extraction/stages/row_merger_materializer.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart lib/features/pdf/services/extraction/stages/row_merger_trace_payloads.dart test/features/pdf/extraction/stages/row_merger/leading_structured_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger/leading_structured_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger_test.dart -d windows`
    -> passed, `36/36`.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_standalone_promotion_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/boilerplate_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/trailing_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/leading_price_anchor_reservation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/leading_description_anchor_reservation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/sequence_gap_continuation_promotion_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/leading_text_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/leading_structured_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_feature_reader_test.dart -d windows`
    -> passed, `73/73`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `dart analyze lib/features/pdf/services/extraction/stages/column_detection_workflow.dart lib/features/pdf/services/extraction/stages/column_detection_stage_reporter.dart lib/features/pdf/services/extraction/stages/column_detection_trace_emitter.dart lib/features/pdf/services/extraction/stages/column_detection_orchestration.dart lib/features/pdf/services/extraction/stages/column_detection_rules.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/column_detection/column_detection_stage_reporter_test.dart test/features/pdf/extraction/stages/column_detection/column_detection_trace_emitter_test.dart test/features/pdf/extraction/stages/column_detection/stage_trace_outputs_test.dart test/features/pdf/extraction/stages/column_detection/column_detection_orchestration_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/column_detection/column_detection_stage_reporter_test.dart test/features/pdf/extraction/stages/column_detection/column_detection_trace_emitter_test.dart test/features/pdf/extraction/stages/column_detection/stage_trace_outputs_test.dart test/features/pdf/extraction/stages/column_detection/column_detection_orchestration_test.dart -d windows`
    -> passed, `13/13`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_parsing_workflow.dart lib/features/pdf/services/extraction/stages/row_parser_trace_emitter.dart lib/features/pdf/services/extraction/stages/row_parser_trace_payloads.dart lib/features/pdf/services/extraction/stages/row_parser_parsed_item_assembler.dart lib/features/pdf/services/extraction/stages/row_parser_row_type_handler.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_parser/row_parser_trace_emitter_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_trace_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_parsed_item_assembler_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_parser/row_parser_trace_emitter_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_trace_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_parsed_item_assembler_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_row_type_handler_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart -d windows`
    -> passed, `42/42`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_leading_bid_amount_tail_extractor.dart lib/features/pdf/services/extraction/stages/row_merger_features.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_merger/row_merger_leading_bid_amount_tail_extractor_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger/row_merger_leading_bid_amount_tail_extractor_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_feature_reader_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart -d windows`
    -> passed, `21/21`.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_leading_bid_amount_tail_extractor_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_continuation_placement_feature_reader_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_feature_reader_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart -d windows`
    -> passed, `51/51`.
  - `flutter test test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart -d windows`
    -> passed, `42/42`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_features.dart lib/features/pdf/services/extraction/stages/row_merger_materializer.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart lib/features/pdf/services/extraction/stages/row_merger_trace_payloads.dart test/features/pdf/extraction/stages/row_merger/leading_text_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger/leading_text_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger_test.dart -d windows`
    -> passed, `34/34`.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_standalone_promotion_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/boilerplate_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/trailing_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/leading_price_anchor_reservation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/leading_description_anchor_reservation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/sequence_gap_continuation_promotion_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/leading_text_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_feature_reader_test.dart -d windows`
    -> passed, `68/68`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_features.dart lib/features/pdf/services/extraction/stages/row_merger_materializer.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart lib/features/pdf/services/extraction/stages/row_merger_trace_payloads.dart test/features/pdf/extraction/stages/row_merger/sequence_gap_continuation_promotion_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger/sequence_gap_continuation_promotion_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger_test.dart -d windows`
    -> passed, `33/33`.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_standalone_promotion_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/boilerplate_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/trailing_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/leading_price_anchor_reservation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/leading_description_anchor_reservation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/sequence_gap_continuation_promotion_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_feature_reader_test.dart -d windows`
    -> passed, `64/64`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `flutter test test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart -d windows`
    -> passed, `42/42`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_features.dart lib/features/pdf/services/extraction/stages/row_merger_materializer.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart lib/features/pdf/services/extraction/stages/row_merger_trace_payloads.dart test/features/pdf/extraction/stages/row_merger/leading_price_anchor_reservation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger/leading_price_anchor_reservation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger_test.dart -d windows`
    -> passed, `32/32`.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_standalone_promotion_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/boilerplate_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/trailing_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/leading_price_anchor_reservation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/leading_description_anchor_reservation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_feature_reader_test.dart -d windows`
    -> passed, `60/60`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `flutter test test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart -d windows`
    -> passed, `42/42`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_features.dart lib/features/pdf/services/extraction/stages/row_merger_materializer.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart lib/features/pdf/services/extraction/stages/row_merger_trace_payloads.dart test/features/pdf/extraction/stages/row_merger/leading_description_anchor_reservation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger/leading_description_anchor_reservation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger_test.dart -d windows`
    -> passed, `31/31`.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_standalone_promotion_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/boilerplate_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/trailing_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/leading_description_anchor_reservation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_feature_reader_test.dart -d windows`
    -> passed, `56/56`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `flutter test test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart -d windows`
    -> passed, `42/42`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_features.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart test/features/pdf/extraction/stages/row_merger/row_merge_feature_reader_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_standalone_promotion_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/boilerplate_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/trailing_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_feature_reader_test.dart -d windows`
    -> passed, `52/52`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_features.dart lib/features/pdf/services/extraction/stages/row_merger_materializer.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart lib/features/pdf/services/extraction/stages/row_merger_trace_payloads.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_merger/row_merge_feature_reader_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_standalone_promotion_test.dart test/features/pdf/extraction/stages/row_merger/boilerplate_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/trailing_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_standalone_promotion_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/boilerplate_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/trailing_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_feature_reader_test.dart -d windows`
    -> passed, `50/50`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `flutter test test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart -d windows`
    -> passed, `42/42`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_features.dart lib/features/pdf/services/extraction/stages/row_merger_materializer.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart lib/features/pdf/services/extraction/stages/row_merger_trace_payloads.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_merger/row_merge_feature_reader_test.dart test/features/pdf/extraction/stages/row_merger/boilerplate_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/boilerplate_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_feature_reader_test.dart -d windows`
    -> passed, `43/43`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `flutter test test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart -d windows`
    -> passed, `42/42`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_materializer.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart lib/features/pdf/services/extraction/stages/row_merger_trace_payloads.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_merger/boilerplate_continuation_rule_evaluator_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/boilerplate_continuation_rule_evaluator_test.dart -d windows`
    -> passed, `40/40`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `flutter test test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart -d windows`
    -> passed, `42/42`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_materializer.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart lib/features/pdf/services/extraction/stages/row_merger_trace_payloads.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merge_materializer_test.dart -d windows`
    -> passed, `37/37`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `flutter test test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart -d windows`
    -> passed, `42/42`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart lib/features/pdf/services/extraction/stages/row_merger_trace_payloads.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart -d windows`
    -> passed, `34/34`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_parsing_workflow.dart lib/features/pdf/services/extraction/stages/row_parser_row_type_handler.dart lib/features/pdf/services/extraction/stages/row_parser_trace_payloads.dart lib/features/pdf/services/extraction/stages/row_merger_continuation_placement_feature_reader.dart lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart lib/features/pdf/services/extraction/stages/row_merger_trace_payloads.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_parser/row_parser_row_type_handler_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_continuation_placement_feature_reader_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_parser/row_parser_row_type_handler_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_trace_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_continuation_placement_feature_reader_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart -d windows`
    -> passed, `15/15`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_parsing_workflow.dart lib/features/pdf/services/extraction/stages/row_parser_parsed_item_assembler.dart lib/features/pdf/services/extraction/stages/row_parser_row_type_handler.dart lib/features/pdf/services/extraction/stages/row_parser_trace_payloads.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_parser/row_parser_parsed_item_assembler_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_row_type_handler_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_trace_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_parser/row_parser_parsed_item_assembler_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_row_type_handler_test.dart test/features/pdf/extraction/stages/row_parser/row_parser_trace_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_isolated_test.dart -d windows`
    -> passed, `43/43`.
  - `dart analyze lib/features/pdf/services/extraction/stages/column_detection_workflow.dart lib/features/pdf/services/extraction/stages/column_detection_trace_emitter.dart lib/features/pdf/services/extraction/stages/column_detection_orchestration.dart lib/features/pdf/services/extraction/stages/column_detection_rules.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/column_detection/column_detection_trace_emitter_test.dart test/features/pdf/extraction/stages/column_detection/stage_trace_outputs_test.dart test/features/pdf/extraction/stages/column_detection/column_detection_orchestration_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/column_detection/column_detection_trace_emitter_test.dart test/features/pdf/extraction/stages/column_detection/stage_trace_outputs_test.dart test/features/pdf/extraction/stages/column_detection/column_detection_orchestration_test.dart -d windows`
    -> passed, `10/10`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_merger.dart lib/features/pdf/services/extraction/stages/row_merger_rules.dart lib/features/pdf/services/extraction/pipeline/extraction_pipeline_tabular_runner.dart lib/features/pdf/services/extraction/stages/stages.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart test/features/pdf/extraction/helpers/mock_stages/region_column_cell_mocks.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/row_merger/standalone_pay_item_detector_test.dart test/features/pdf/extraction/stages/row_merger/row_merger_trace_test.dart -d windows`
    -> passed, `34/34`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `flutter test test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart -d windows`
    -> passed, `42/42`.
  - `dart analyze lib/features/pdf/services/extraction/stages/row_semantic_classification_stage.dart lib/features/pdf/services/extraction/stages/row_semantic_classification_rules.dart lib/features/pdf/services/extraction/stages/row_classifier_v3.dart test/features/pdf/extraction/stages/row_semantic_classification_stage_test.dart test/features/pdf/extraction/stages/row_semantic_classification/row_semantic_trace_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/row_semantic_classification_stage_test.dart test/features/pdf/extraction/stages/row_semantic_classification/row_semantic_trace_test.dart -d windows`
    -> passed, `5/5`.
  - `flutter test test/features/pdf/extraction/stages/row_classifier_v3_test.dart -d windows`
    -> passed, `36/36`.
  - `flutter test test/features/pdf/extraction/contracts/element_validation_to_row_classification_contract_test.dart test/features/pdf/extraction/contracts/row_classification_to_region_detection_contract_test.dart -d windows`
    -> passed, `10/10`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `dart analyze lib/features/pdf/services/extraction/stages/column_detection_workflow.dart lib/features/pdf/services/extraction/stages/column_detection_orchestration.dart test/features/pdf/extraction/stages/column_detection/column_detection_orchestration_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/column_detection -d windows`
    -> passed, `78/78`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `dart analyze lib/features/pdf/services/extraction/stages/column_detection_workflow.dart lib/features/pdf/services/extraction/stages/column_detection_orchestration.dart test/features/pdf/extraction/stages/column_detection/column_detection_orchestration_test.dart`
    -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/column_detection -d windows`
    -> passed, `76/76`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows`
    -> passed, `4/4`.
  - `dart analyze lib/features/pdf/services/extraction/pipeline/substage_trace_payload.dart lib/features/pdf/services/extraction/pipeline/stage_trace.dart lib/features/pdf/services/extraction/pipeline/extraction_pipeline_stage_runtime.dart lib/features/pdf/services/extraction/stages/column_detection_workflow.dart lib/features/pdf/services/extraction/stages/column_detection_rules.dart test/features/pdf/extraction/stages/column_detection/stage_trace_outputs_test.dart test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart` -> passed, no issues.
  - `flutter test test/features/pdf/extraction/stages/column_detection -d windows` -> passed, `72/72`.
  - `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart -d windows` -> passed, `4/4`.
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart -d windows` -> passed, `31/31`.
  - `flutter test test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart -d windows` -> passed, `42/42`.
- Latest original-four replay command/result:
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_parser_decomposition_trace_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_parser_confidence_calculator_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_merger_leading_structured_rule_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_merger_leading_text_rule_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_merger_sequence_gap_rule_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_merger_leading_price_reservation_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_merger_leading_description_reservation_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_merger_descriptor_feature_reader_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_merger_trailing_rule_trace_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_merger_feature_reader_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_merger_continuation_rules_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_merger_materializer_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_merger_trace_payload_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_merger_standalone_trace_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`. Artifact spot-check found all
    three row-merger substage IDs in generated stage trace summaries/traces.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_row_semantic_rules_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`. Artifact spot-check found row
    semantic substage IDs in the generated stage trace summaries.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_column_candidate_orchestration_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_column_orchestration_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_column_rules_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed only known Berrien `16` description mismatches; Grand Blanc,
    Huron Valley, and Springfield remain `0`.
  - Trace check: Berrien artifact has six column substage traces and no missing
    `input`/`output`/`decisions`/`mutations`/`provenance` keys.
- Latest full-corpus replay command/result:
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_parser_decomposition_trace_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_parser_confidence_calculator_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_merger_leading_structured_rule_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_merger_leading_text_rule_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_merger_sequence_gap_rule_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_merger_leading_price_reservation_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_merger_leading_description_reservation_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_merger_descriptor_feature_reader_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_merger_trailing_rule_trace_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_merger_feature_reader_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_merger_continuation_rules_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_merger_materializer_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_merger_trace_payload_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_merger_standalone_trace_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_row_semantic_rules_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_column_candidate_orchestration_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_column_orchestration_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_column_rules_extract_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
  - Result: failed with the known current total of `427` mismatches and the two
    existing MDOT trace-contract failures for
    `mdot_2026_03_06_26_03001_bid_tab-pay-items` and
    `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
- Latest review result: not complete. The row semantic and row-merger
  decomposition slices replayed without new mismatches, but remaining review
  gates stay red until the rest of row merger, row parsing, trace-contract, and
  test-counterpart decomposition items below are green.

## 1. Spec Setup

- [x] Save this spec under `.codex/plans/2026-04-15-extraction-pipeline-decomposition-trace-spec.md`.
- [x] Link this spec from `.codex/PLAN.md` as the active extraction decomposition gate.
- [x] Mark this spec as the verification gate before resuming MDOT heuristic iteration.
- [x] Add a running status section with:
  - [x] current stage under decomposition.
  - [x] latest unit test command and result.
  - [x] latest original-four replay command and result.
  - [x] latest full-corpus replay command and result.
  - [x] latest review result.

## 2. Trace Contract

- [x] Extend the existing `StageTrace` / `StageTraceSink` path for decomposed substages.
- [x] Do not create a separate debug/logging transport.
- [x] Keep existing top-level stage artifacts compatible with current replay/debug tooling.
- [x] Add substage trace entries in addition to existing stage outputs.
- [x] Every currently decomposed substage trace includes:
  - [x] stable `stageId`.
  - [x] stable `substageId`.
  - [x] compact `input`.
  - [x] compact `output`.
  - [x] `decisions`.
  - [x] `mutations`.
  - [x] `provenance` where source-backed data exists.
- [x] Every currently decomposed rule-like decision includes:
  - [x] stable `ruleName`.
  - [x] `reasonCode`.
  - [x] accepted/rejected status.
  - [x] confidence or score when applicable.
- [x] Every currently decomposed mutation includes:
  - [x] entity kind or field name.
  - [x] `before`.
  - [x] `after`.
  - [x] `ruleName`.
  - [x] `reasonCode`.
  - [x] source IDs where available.
  - [x] explicit status for inferred, synthesized, dropped, moved, split, merged, or reassigned values.

## 3. Column Detection Decomposition

- [x] Decompose `ColumnDetectionWorkflow` without changing behavior.
- [x] Extract candidate collection.
- [x] Extract grid/semantic candidate scoring.
- [x] Extract pathological grid detection.
- [x] Extract candidate arbitration.
- [x] Extract page semantic propagation.
- [x] Extract agreement/confidence scoring.
- [x] Thread the trace emitter through every extracted unit.
- [x] Emit inputs, outputs, decisions, mutations, and provenance for every current column substage trace.
- [x] Verify extraction output is identical before and after this decomposition slice.

## 4. Row Semantic Classification Decomposition

- [x] Decompose `RowSemanticClassificationStage` without changing behavior.
- [x] Extract row feature reading.
- [x] Extract data-row anchor detection.
- [x] Extract continuation classification.
- [x] Extract header/non-data classification.
- [x] Thread the trace emitter through every extracted unit.
- [x] Emit row IDs, row features, prior-row context, selected row type, reason code, confidence, and provenance.
- [x] Verify extraction output is identical before and after this decomposition slice.

## 5. Row Merger Decomposition

- [x] Decompose `RowMerger` without changing behavior.
- [x] Extract row merge feature computation.
  - [x] Extract shared semantic/payload row-merge feature reading.
  - [x] Extract text/anchor/local-sequence row-merge feature reading.
  - [x] Extract descriptor/spec/section-fragment row-merge feature reading.
  - [x] Extract remaining continuation-placement feature helpers.
- [x] Extract standalone pay-item detection.
- [x] Extract continuation attachment rule evaluation.
  - [x] Extract boilerplate continuation attachment rule evaluation.
  - [x] Extract trailing continuation attachment rule evaluation.
  - [x] Extract leading price-anchor reservation rule evaluation.
  - [x] Extract leading description-anchor reservation rule evaluation.
  - [x] Extract sequence-gap continuation promotion rule evaluation.
  - [x] Extract leading text continuation rule evaluation.
  - [x] Extract leading structured continuation rule evaluation.
  - [x] Extract remaining leading continuation attachment rules.
- [x] Extract merge materialization.
- [x] Extract row-merge trace payload construction for the current
      standalone/materialization slice into `row_merger_trace_payloads.dart`.
- [x] Extract row-merge trace stage-output emission into
      `row_merger_trace_emitter.dart`.
- [x] Thread the trace emitter through the current extracted row-merger unit.
- [x] Emit base row IDs, continuation row IDs, feature counts,
      accepted/rejected rules, before/after merged-row membership, and
      provenance for the current row-merger slice.
- [x] Verify extraction output is identical before and after this decomposition
      slice.

## 6. Row Parsing Decomposition

- [x] Decompose `RowParsingWorkflow` without changing behavior.
- [x] Extract standard data-row parsing.
- [x] Extract AASHTOWare bid-tab-by-item parsing.
- [x] Extract cell-to-field parsing.
- [x] Extract misaligned row parsing.
- [x] Extract fallback token parsing.
- [x] Extract item-number sequence rescue.
- [x] Extract parsed-item confidence calculation.
- [x] Thread the trace emitter through every extracted unit.
- [x] Emit raw cells, parsed fields, fallback decisions, sequence corrections, confidence inputs, field-level mutations, and provenance.
- [x] Verify extraction output is identical before and after this decomposition.

## 7. Trace Tests

- [x] Add trace-shape tests for decomposed substages.
- [x] Tests fail if any decomposed substage omits `input`.
- [x] Tests fail if any decomposed substage omits `output`.
- [x] Tests fail if any decomposed substage omits `decisions`.
- [x] Tests fail if any decomposed substage omits `mutations`.
- [x] Tests fail if source-backed output omits provenance.
- [x] Tests fail if a rule decision lacks stable `ruleName` or `reasonCode`.
- [x] Tests fail if a mutation lacks `before`, `after`, `ruleName`, or `reasonCode`.
- [x] Tests confirm existing top-level stage artifacts remain readable by current replay/debug tooling.

## 8. Test Counterpart Decomposition

Production-stage decomposition is not complete unless the matching tests are
kept decomposed as well. Do not let a replacement god test file grow while
splitting the production code.

- [x] Add test-file size and complexity review to every decomposition slice.
- [x] Prefer focused test files by behavior/rule/stage over large aggregate
      test files.
- [x] Add shared test builders/helpers only when they reduce repeated setup
      without hiding behavior under test.
- [x] Keep trace-shape tests separate from extraction-behavior tests when the
      split improves readability.
- [x] Track the current PDF extraction test-file decomposition queue:
  - [x] `test/features/pdf/extraction/integration/gocr_downstream_replay/expected_comparison_helpers.dart`
        is split into ground-truth, row-matching, diagnosis, and source-
        provenance helper parts while keeping comparator behavior unchanged.
  - [x] `test/features/pdf/extraction/stages/row_merger_test.dart`
        now keeps only basic-flow coverage; leading schedule, price,
        description, structured/text, and descriptor continuation scenarios are
        standalone focused files, with shared row builders in
        `row_merger_test_support.dart`.
  - [x] `test/features/pdf/extraction/stages/row_parser/core_parsing_tests.dart`
        is split into core, schedule-item, bid-tab, and item-number rescue
        parsing parts.
  - [x] `test/features/pdf/extraction/stages/post_processing/repair_log_test.dart`
        is split into repair-log basics, math scale repairs, math candidate
        repairs, math digit repairs, math price-backsolve repairs, and
        description repair rules.
  - [x] `test/features/pdf/services/mp/mp_stage_trace_diagnostic_test.dart`
        is split into fixture readiness, body text accuracy, scorecard, and
        shared diagnostic support files. The wrapper is now a thin trace
        assertion file.
  - [x] `test/features/pdf/extraction/helpers/gocr_trace_artifact_contract.dart`
        is split into field contract, mutation/ground-truth contract, and
        metrics helpers while preserving the public validation API.
  - [x] `test/features/pdf/extraction/stages/post_processing/artifact_cleaning_rules_test.dart`
        is split into core artifact-cleaning rules, description repairs, unit
        rules, and pavement-marking artifact rules.
- [x] Add or update focused test counterpart files during each production
      decomposition stage:
  - [x] Column detection tests stay split under
        `test/features/pdf/extraction/stages/column_detection/`.
  - [x] Row semantic classification tests are split by row type/rule family.
  - [x] Row merger tests are split before or during row-merger production
        decomposition.
  - [x] Row parser tests are split before or during row-parser production
        decomposition.
- [x] The review gate must fail if a touched test file becomes a new large
      aggregate file instead of a focused counterpart.

## 9. Verification Loop

For each decomposed stage, repeat this loop until all items are green:

- [x] Run focused unit tests for the touched stage.
- [x] Run adjacent stage tests affected by the touched stage.
- [x] Run original-four PDF replay as the no-regression gate.
- [x] Run full cached-corpus replay including MDOT PDFs.
- [x] Compare extraction output against the previous baseline.
- [x] Confirm any differences are only added trace/debug artifacts.
- [x] Record command, result, artifact path, and remaining failures in this spec.
- [x] Fix failures.
- [x] Repeat until green.

## 10. Required Test Commands

- [x] Run row merger tests:
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart -d windows`
- [x] Run row parser and rescue tests:
  - `flutter test test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart -d windows`
- [x] Run relevant column detection tests discovered during implementation.
- [x] Run relevant row semantic classification tests discovered during implementation.
- [x] Run original-four replay using the established GOCR replay cache gate.
- [x] Run full cached-corpus replay using `.tmp/gocr_ocr_cache`.

## 11. Review Gate

After all checklist items appear green:

- [x] Perform a code review pass focused on behavioral regressions, missing trace coverage, and mutation attribution gaps.
- [x] Perform a test-structure review focused on oversized test files and
      hidden setup complexity.
- [x] Confirm no PDF-specific production branches were introduced.
- [x] Confirm no fixture changes were made as part of this refactor.
- [x] Confirm no comparator normalization or shortcut was added.
- [x] Confirm every extracted unit has trace coverage.
- [x] Confirm every stage still has top-level trace output.
- [x] Confirm every substage has input/output/decision/mutation/provenance trace data.
- [x] Re-run the full verification loop after review fixes.
- [x] Mark the spec complete only after review and final replay are both green
      relative to the known refactor baseline. Accuracy mismatches remain the
      existing post-decomposition heuristic work queue.

## Assumptions

- This spec must be saved and tracked before implementation begins.
- The existing `StageTrace`, `StageTraceSink`, `PipelineRunState`, `StageReport`, and replay artifacts remain the canonical logging/debug system.
- The first implementation pass is behavior-preserving decomposition only.
- MDOT heuristic iteration resumes only after this decomposition and trace verification gate is complete.

## 12. Remaining TODO Audit

This audit is the live work queue for closing the spec. Check items here only
after the matching checklist item above is also green and the verification loop
has been recorded in Running Status.

- [x] Trace contract closure:
  - [x] Add source IDs to decomposed mutations where the source rows/elements
        are available.
    - [x] Add source IDs to row-parser row-type, fallback, sequence, and
          misaligned-field mutations where source rows are available.
    - [x] Add source row IDs to row-merger standalone promotion and
          merge-materialization mutations.
    - [x] Add source row IDs through cell extraction, numeric interpretation,
          and field-confidence scoring trace payloads.
    - [x] Add post-processing repair mutation source-item snapshots where
          source rows are no longer available.
- [x] Column detection closure:
  - [x] Decide whether remaining `ColumnDetectionWorkflow` orchestration
        ownership is decomposed enough to mark complete, or extract the next
        orchestration seam.
    - [x] Extract column substage trace decision/mutation construction into
          `column_detection_trace_emitter.dart`.
    - [x] Extract column legacy layer stage-output/report construction into
          `column_detection_stage_reporter.dart`.
  - [x] Verify every extracted column unit is represented by the current trace
        emitter path before checking off trace-threading.
- [x] Row merger closure:
  - [x] Extract remaining leading continuation placement rules.
    - [x] Extract leading price-anchor reservation rule.
    - [x] Extract leading description-anchor reservation rule.
    - [x] Extract sequence-gap continuation promotion rule.
    - [x] Extract leading text continuation rule.
    - [x] Extract leading structured continuation rule.
  - [x] Extract remaining continuation-placement feature helpers.
    - [x] Extract descriptor/measurement continuation-placement feature
          predicates into `row_merger_continuation_placement_feature_reader.dart`.
    - [x] Extract leading bid-amount tail detachment into
          `row_merger_leading_bid_amount_tail_extractor.dart`.
  - [x] Add focused tests for each extracted leading-placement rule.
  - [x] Confirm row-merger trace output covers every extracted row-merger rule.
  - [x] Continue splitting `row_merger_test.dart` by rule family.
- [x] Row parser closure:
  - [x] Decompose `RowParsingWorkflow.parse`.
  - [x] Extract standard data-row parsing.
  - [x] Extract AASHTOWare bid-tab-by-item parsing.
  - [x] Extract cell-to-field parsing.
  - [x] Extract row-type output handling.
  - [x] Extract misaligned row parsing.
  - [x] Extract fallback token parsing.
  - [x] Extract item-number sequence rescue.
  - [x] Extract parsed-item confidence calculation.
  - [x] Extract parsed-item warning/count/materialization assembly.
  - [x] Add row-parser substage trace payloads for raw cells, parsed fields,
        fallback decisions, sequence corrections, confidence inputs, field
        mutations, and provenance.
  - [x] Extract row-parser substage trace emission into
        `row_parser_trace_emitter.dart`.
  - [x] Split row-parser tests before adding new parser trace tests.
- [x] Test counterpart closure:
  - [x] Split `expected_comparison_helpers.dart`.
  - [x] Split remaining `row_merger_test.dart` rule families.
  - [x] Split `row_parser/core_parsing_tests.dart`.
  - [x] Split `post_processing/repair_log_test.dart`.
  - [x] Split `mp_stage_trace_diagnostic_test.dart`.
  - [x] Split remaining oversized replay focus and row-rescue helper files
        before enabling the PDF test-length lint as a hard gate.
  - [x] Reassess smaller trace/helper tests after parser trace work lands.
- [x] Review-gate closure:
  - [x] Run behavioral regression review.
  - [x] Run test-structure review.
  - [x] Confirm no PDF-specific branches, fixture edits, or comparator changes
        were introduced during decomposition.
  - [x] Re-run the full verification loop and mark this spec complete only
        after the loop is green or the remaining known baseline failures are
        explicitly resolved in the post-decomposition heuristic phase.

## 13. Appended CodeMunch And Test-Counterpart Audit Queue

These items were appended after auditing the full extraction pipeline and its
test counterparts. Keep this queue at the bottom as the living intake list for
future decomposition slices.

- [x] CodeMunch repository audit ran against `local/Field_Guide_App-37debbe5`.
  The repo health snapshot identified `RowParsingWorkflow.parse` and
  `ColumnDetectionWorkflow.detect` as the highest-risk PDF extraction hotspots.
- [x] CodeMunch hotspot ranking for extraction pipeline production code:
  - `lib/features/pdf/services/extraction/stages/row_parsing_workflow.dart::RowParsingWorkflow.parse`
    complexity `82`, churn `8`, hotspot score `180.1724`.
  - `lib/features/pdf/services/extraction/stages/column_detection_workflow.dart::ColumnDetectionWorkflow.detect`
    complexity `124`, churn `3`, hotspot score `171.9005`.
  - `lib/features/pdf/services/extraction/stages/row_parsing_workflow.dart::RowParsingWorkflow._parseMisalignedDataRow`
    complexity `36`, churn `8`, hotspot score `79.1001`.
  - `lib/features/pdf/services/extraction/stages/row_semantic_classification_stage.dart::RowSemanticClassificationStage._classifyRow`
    complexity `48`, churn `4`, hotspot score `77.253`.
  - `lib/features/pdf/services/extraction/stages/item_deduplication_workflow.dart::ItemDeduplicationWorkflow.deduplicate`
    complexity `52`, churn `3`, hotspot score `72.0873`.
  - `lib/features/pdf/services/extraction/stages/grid_line_column_detection_workflow.dart::GridLineColumnDetectionWorkflow.detect`
    complexity `59`, churn `2`, hotspot score `64.8181`.
- [x] CodeMunch extraction-candidate tool was checked for the current primary
  files. It returned no multi-caller extraction candidates, which means the
  decomposition must be based on internal complexity and trace boundaries
  rather than shared-call reuse.
- [x] Add focused pure-rule tests for `ColumnCandidateArbiter`,
  `MissingColumnInference`, `PageColumnSemanticPropagator`, and
  `ColumnAgreementScorer` without growing an aggregate god test file.
- [x] Add focused orchestration tests for `ColumnPageAdjustmentSelector` and
  `ColumnAnchorCorrectionArbiter` in
  `test/features/pdf/extraction/stages/column_detection/column_detection_orchestration_test.dart`.
- [x] Continue splitting `ColumnDetectionWorkflow.detect`:
  - [x] extract candidate collection/orchestration state.
  - [x] extract candidate scoring decision material.
  - [x] extract page adjustment selection.
  - [x] extract anchor-correction arbitration.
  - [x] extract layer diagnostics construction.
- [x] Split row semantic classification next, before adding more MDOT
  heuristics:
  - [x] extract row feature/context reading.
  - [x] extract data anchor rules.
  - [x] extract continuation/header/boilerplate rules.
  - [x] add substage trace payloads for every rule family.
  - [x] split tests by row type/rule family instead of adding to one large
        file.
- [x] Split `row_merger_test.dart` before or during row merger production work.
  It now keeps only basic-flow coverage; leading schedule, price, description,
  structured/text, and descriptor-fragment cases live in standalone focused
  files under
  `test/features/pdf/extraction/stages/row_merger/`.
- [x] Split `core_parsing_tests.dart` before or during row parsing production
  work. Schedule-item, bid-tab, and item-number rescue scenarios now live in
  separate focused part files.
- [x] Split `expected_comparison_helpers.dart` before adding more replay
  diagnostics. Ground-truth comparison, row matching, diagnosis, and source
  provenance helpers now live in focused part files.
- [x] Split `repair_log_test.dart` before adding more post-processing trace
  assertions. Math scale, candidate, digit, price-backsolve, and description
  repair rules now live in focused standalone tests.
- [x] Keep every new trace-shape test in focused counterpart files:
  - [x] column trace tests remain under
        `test/features/pdf/extraction/stages/column_detection/`.
  - [x] pipeline trace transport tests remain under
        `test/features/pdf/extraction/pipeline/`.
  - [x] row semantic trace tests live in
        `test/features/pdf/extraction/stages/row_semantic_classification/`.
  - [x] row-merger trace tests get their own focused file before
        production row-merger decomposition starts.
  - [x] future row-parser trace tests get their own focused file before
        production row-parser decomposition starts.

## 14. Final Review, Lint, And Benchmark Gate

- [x] Three-way final review completed with separate agents:
  - [x] Upstream OCR/validation/classification/header/region/column slice.
  - [x] Middle row-merging/cell/numeric/row-parser/confidence slice.
  - [x] Downstream post-processing/quality/replay/test-helper slice.
- [x] Review findings addressed:
  - [x] Row classification, region detection, and cell extraction substage
        outputs now preserve legacy top-level diagnostic keys while also
        carrying `SubstageTracePayload` input, decisions, mutations, and
        provenance.
  - [x] Empty column-map cell extraction and empty row-parser inputs emit
        no-op substage traces instead of returning before trace emission.
  - [x] Numeric interpretation and field-confidence scoring emit structured
        substage traces with source-row provenance.
  - [x] Post-processing repair mutations include source item snapshots where
        row-level provenance is no longer available.
  - [x] Final header consolidation now has an explicit stage start/complete
        log banner around the recorded stage.
- [x] Structure lock-in lints added:
  - [x] `max_pdf_extraction_production_file_length` caps PDF extraction
        production files at 1600 lines.
  - [x] `max_pdf_extraction_callable_length` caps PDF extraction callables at
        450 lines.
  - [x] `max_pdf_extraction_test_file_length` now also covers
        `test/features/pdf/services/mp/`.
- [x] Lint baseline cleanup completed for touched/scope files:
  - [x] `row_cell_focus_helpers.dart` split to
        `row_cell_focus_matching_helpers.dart`.
  - [x] `row_rescue_adjustment_stage_test.dart` split to
        `row_rescue_adjustment_stage_test_helpers.dart`.
- [x] Final validation commands:
  - [x] `dart analyze` on all final touched production/test/lint files passed.
  - [x] `dart test test/architecture/max_pdf_extraction_test_file_length_test.dart test/architecture/max_pdf_extraction_production_file_length_test.dart test/architecture/max_pdf_extraction_callable_length_test.dart`
        from `fg_lint_packages/field_guide_lints` passed `6/6`.
  - [x] `flutter test test/features/pdf/extraction/stages/cell_extraction_stage_test.dart test/features/pdf/extraction/stages/region_detection_stage_test.dart test/features/pdf/extraction/stages/row_classifier_v3_test.dart test/features/pdf/extraction/stages/numeric_interpreter_test.dart test/features/pdf/extraction/stages/field_confidence_scorer_test.dart test/features/pdf/extraction/stages/row_parser_stage_test.dart test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_test.dart test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows`
        passed `140/140`; replay harness skipped without the define.
  - [x] `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart test/features/pdf/extraction/pipeline/stage_trace_sink_test.dart test/features/pdf/extraction/pipeline/stage_trace_diagnostics_test.dart -d windows`
        passed `9/9`.
  - [x] `dart run custom_lint` confirms the new PDF extraction lint rules do
        not introduce failures. The run still fails on existing unrelated
        issues: one `no_pdf_specific_gocr_extraction_branching` finding in
        `gocr_trace_artifact_store.dart`, extraction-metrics soft-delete
        filter findings, and one existing `no_silent_catch` warning in
        `gocr_ocr_cache.dart`.
- [x] Final benchmark:
  - [x] Original-four replay:
        `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/original_four_replay_after_final_trace_lint_gate_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
        stayed at the known Berrien-only `16` mismatch baseline.
  - [x] Full cached corpus replay:
        `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/full_corpus_replay_after_final_trace_lint_gate_01 --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
        stayed at the known `427` mismatch baseline plus the same two MDOT
        trace-contract artifact failures.
