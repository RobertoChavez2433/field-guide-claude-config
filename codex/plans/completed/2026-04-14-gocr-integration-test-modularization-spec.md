# GOCR Integration Test Modularization Spec - 2026-04-14

## Goal

Create a maintainable, fast iteration test layout for the Google Assisted OCR
work without mixing it into the custom/local OCR pipeline. Keep tests small
enough to reason about, with a practical target of about 500 lines per test
file when the behavior can be split cleanly.

This spec is a working checklist. Update it as refactors land.

## Non-Negotiables

- [x] Preserve the protected Springfield originals while refactoring.
- [x] Keep the Custom Pipeline free of Google Cloud Vision and Document AI
  calls.
- [x] Keep the Google Assisted Pipeline as one public pipeline. Google Cloud
  Vision and Document AI are internal Google backends, not separate public
  company modes.
- [x] Do not add PDF-specific hacks. New parsing rules must be general
  geometry, classification, numeric, dictionary, or confidence heuristics.
- [x] Keep run outputs under a deletable `.tmp` run root or the existing S10
  staging root.
- [x] Do not add test-only production hooks.

## CodeMunch / Filesystem Map

- [x] Refresh CodeMunch index for the current worktree.
  - Evidence: `index_folder` on `C:\Users\rseba\Projects\Field_Guide_App`
    indexed 130 changed files, 24 new files, and removed 39 stale files.
  - Final refresh after modularization indexed 3 changed files, 11 new files,
    and removed 11 stale files with 15,666 symbols.
- [x] Use CodeMunch to map repo-level and integration-test structure.
  - CodeMunch mapped `integration_test` and confirmed the active indexed repo
    as `local/Field_Guide_App-37debbe5`.
- [x] Cross-check with the live filesystem for
  `test/features/pdf/extraction`.
  - CodeMunch tree/outline still collapsed this subtree to
    `ocr_cell_corpus.json`, so the live tree is the authoritative source for
    the detailed PDF extraction test map.

## Test Ownership Map

Checked entries mean the file was audited for pipeline ownership and size. Some
files were split; files already below the 500-line OCR/PDF test limit were left
intact.

Google Assisted / GOCR tests:

- [x] `integration_test/pre_release_pdf_corpus_test.dart`
- [x] `integration_test/springfield_report_test.dart`
- [x] `test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart`
- [x] `test/features/pdf/extraction/helpers/gocr_ocr_cache_test.dart`
- [x] `test/features/pdf/extraction/ocr/google_cloud_vision_ocr_engine_test.dart`
- [x] `test/features/pdf/extraction/ocr/google_cloud_vision_edge_function_contract_test.dart`
- [x] `test/features/pdf/extraction/ocr/google_document_ai_ocr_engine_test.dart`
- [x] `test/features/pdf/extraction/ocr/google_document_ai_edge_function_contract_test.dart`
- [x] `test/features/pdf/extraction/integration/pre_release_pdf_corpus_manifest_test.dart`
- [x] `test/features/pdf/extraction/integration/mdot_public_pdf_corpus_manifest_test.dart`

Custom/local OCR tests:

- [x] `integration_test/ocr_cell_corpus_harness_test.dart`
- [x] `test/features/pdf/extraction/ocr/tesseract_engine_v2_test.dart`
- [x] `test/features/pdf/extraction/ocr/tesseract_engine_v2_reinit_test.dart`
- [x] `test/features/pdf/extraction/ocr/tesseract_reinit_guard_test.dart`
- [x] `test/features/pdf/extraction/stages/ocr_text_recognizer_test.dart`
- [x] `test/features/pdf/extraction/stages/ocr_row_band_page_recognition_stage_test.dart`
- [x] `test/features/pdf/extraction/stages/ocr_grid_page_recognition_stage_test.dart`
- [x] `test/features/pdf/extraction/stages/ocr_cell_recognition_stage_test.dart`
- [x] `test/features/pdf/extraction/stages/ocr_page_pool_strategy_test.dart`
- [x] `test/features/pdf/extraction/stages/ocr_page_recognition_executor_test.dart`
- [x] `test/features/pdf/extraction/stages/ocr_page_recognition_worker_payload_test.dart`
- [x] `test/features/pdf/extraction/stages/ocr_cell_crop_planner_test.dart`
- [x] `test/features/pdf/extraction/stages/ocr_crop_preparation_stage_test.dart`
- [x] `test/features/pdf/extraction/stages/ocr_full_page_recognition_strategy_test.dart`
- [x] `test/features/pdf/extraction/stages/ocr_retry_resolution_stage_test.dart`
- [x] `test/features/pdf/extraction/pipeline/ocr_preparation_stage_test.dart`
- [x] `test/features/pdf/extraction/pipeline/re_extraction_loop_test.dart`
- [x] `test/features/pdf/extraction/shared/crop_upscaler_test.dart`

Shared downstream extraction tests:

- [x] `test/features/pdf/extraction/stages/column_detection_stage_test.dart`
- [x] `test/features/pdf/extraction/stages/post_processing_stage_test.dart`
- [x] `test/features/pdf/extraction/stages/row_parser_stage_test.dart`
- [x] `test/features/pdf/extraction/stages/row_merger_test.dart`
- [x] `test/features/pdf/extraction/stages/row_splitter_test.dart`
- [x] `test/features/pdf/extraction/stages/quality_validation_stage_test.dart`
- [x] `test/features/pdf/extraction/stages/cell_extraction_stage_test.dart`
- [x] `test/features/pdf/extraction/stages/row_classifier_v3_test.dart`
- [x] `test/features/pdf/extraction/stages/checksum_validation_test.dart`
- [x] `test/features/pdf/extraction/stages/grid_line_detection_stage_test.dart`
- [x] `test/features/pdf/extraction/stages/region_detection_stage_test.dart`
- [x] `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart`
- [x] `test/features/pdf/extraction/integration/full_pipeline_integration_test.dart`
- [x] `test/features/pdf/extraction/contracts/*_contract_test.dart`
- [x] `test/features/pdf/extraction/models/*_test.dart`
- [x] `test/features/pdf/extraction/pipeline/extraction_pipeline_test.dart`
- [x] `test/features/pdf/extraction/pipeline/extraction_metrics_test.dart`
- [x] `test/features/pdf/extraction/pipeline/*_test.dart` files that do not
  instantiate Google or Tesseract backends.
- [x] `test/features/pdf/extraction/helpers/mock_stages.dart`
- [x] `test/features/pdf/extraction/helpers/pipeline_comparator.dart`
- [x] `test/features/pdf/extraction/helpers/report_generator.dart`

## Refactor Queue

- [x] Add lint guardrails after the first test split proves the intended
  layout.
  - Existing guardrail: `max_file_length` already warns above 500 lines and
    errors above 1000 lines.
  - [x] Add a focused PDF/GOCR test-size rule if the existing global rule is
    too broad or too easy to baseline.
    - Added `max_pdf_extraction_test_file_length` as an ERROR above 500
      lines for `test/features/pdf/extraction` and the GOCR/Springfield
      integration harness surfaces.
  - [x] Add a Google Assisted/custom OCR segregation rule that prevents Google
    Vision/Document AI imports or provider calls from custom/local OCR tests
    and production custom OCR directories.
    - Added `no_google_assisted_ocr_in_custom_ocr`.
  - [x] Add unit tests for any new custom lint rule under
    `fg_lint_packages/field_guide_lints/test`.
  - [x] Run `dart test` in `fg_lint_packages/field_guide_lints`.
- [x] Split `column_detection_stage_test.dart` first.
  - Current size: about 6.7k-7.1k lines, 13 groups, 62 tests.
  - Final layout:
    - `stages/column_detection/column_detection_test_helpers.dart`
    - `stages/column_detection/header_keyword_matching_test.dart`
    - `stages/column_detection/multi_row_header_assembly_test.dart`
    - `stages/column_detection/column_boundary_calculation_test.dart`
    - `stages/column_detection/fallback_to_standard_ratios_test.dart`
    - `stages/column_detection/missing_column_inference_test.dart`
    - `stages/column_detection/text_alignment_clustering_test.dart`
    - `stages/column_detection/whitespace_gap_detection_test.dart`
    - `stages/column_detection/grid_line_integration_part_01_test.dart`
    - `stages/column_detection/grid_line_integration_part_02_test.dart`
    - `stages/column_detection/grid_line_integration_part_03_test.dart`
    - `stages/column_detection/margin_detection_semantic_inference_01_test.dart`
    - `stages/column_detection/margin_detection_semantic_inference_02_test.dart`
    - `stages/column_detection/margin_detection_semantic_inference_03_test.dart`
    - `stages/column_detection/margin_detection_semantic_inference_04_test.dart`
    - `stages/column_detection/margin_detection_semantic_inference_05_test.dart`
    - `stages/column_detection/margin_detection_semantic_inference_06_test.dart`
    - `stages/column_detection/margin_detection_semantic_inference_07_test.dart`
    - `stages/column_detection/margin_detection_semantic_inference_08_test.dart`
    - `stages/column_detection/margin_detection_semantic_inference_09_test.dart`
    - `stages/column_detection/margin_detection_semantic_inference_10_test.dart`
    - `stages/column_detection/margin_detection_semantic_inference_11_test.dart`
    - `stages/column_detection/margin_detection_semantic_inference_12_test.dart`
    - `stages/column_detection/margin_detection_semantic_inference_13_test.dart`
    - `stages/column_detection/empty_edge_cases_test.dart`
    - `stages/column_detection/anchor_correction_test.dart`
    - `stages/column_detection/stage_trace_outputs_test.dart`
    - `stages/column_detection/stage_report_validation_test.dart`
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/stages/column_detection`
- [x] Split `ocr_text_recognizer_test.dart` after the shared detector split.
  - Current size: about 2.8k-3.1k lines, 11 groups, 57 tests.
  - Keep this under the Custom/local OCR side.
  - Final layout keeps the original `_test.dart` entrypoint as the library
    owner and moves behavior groups into `part` files under
    `stages/ocr_text_recognizer/`.
  - Split areas:
    - recognizer basics and stage reports,
    - cell crop computation,
    - PSM selection and coordinate mapping,
    - grid/non-grid routing,
    - low-confidence re-OCR fallback,
    - crop upscaling and candidate scoring.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/stages/ocr_text_recognizer_test.dart`
- [x] Split or helper-extract `quality_validation_stage_test.dart`.
  - Current size: about 1.5k-1.7k lines.
  - Keep shared/downstream and provider-neutral.
  - Final layout: `stages/quality_validation/*_test.dart` plus
    `quality_validation_test_helpers.dart`.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/stages/quality_validation`
- [x] Split or helper-extract `post_processing_stage_test.dart`.
  - Current size: about 1.1k-1.3k lines.
  - Final split:
    - basic preservation/reporting
    - repair log and GOCR-derived numeric repair cases
    - confidence/sidecar/stage report
    - edge/integration/data consistency
    - artifact cleaning rules
  - Final layout: `stages/post_processing/*_test.dart` plus
    `post_processing_test_helpers.dart`.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/stages/post_processing`
- [x] Split or helper-extract `cell_extraction_stage_test.dart`.
  - Current size: about 1.1k-1.3k lines.
  - Final layout keeps the original `_test.dart` entrypoint as the library
    owner and moves behavior groups into `stages/cell_extraction/` part files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/stages/cell_extraction_stage_test.dart`
- [x] Split or helper-extract `row_classifier_v3_test.dart`.
  - Current size: about 1.0k-1.1k lines.
  - Final layout keeps the original `_test.dart` entrypoint as the library
    owner and moves provider-neutral row-classification groups into
    `stages/row_classifier_v3/` part files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/stages/row_classifier_v3_test.dart`
- [x] Split or helper-extract `checksum_validation_test.dart`.
  - Current size: about 700-750 lines.
  - Final layout keeps the original `_test.dart` entrypoint as the library
    owner and moves model, parser-total, post-processor checksum, and
    quality-validator checksum groups into `stages/checksum_validation/` part
    files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/stages/checksum_validation_test.dart`
- [x] Split or helper-extract `row_parser_stage_test.dart`.
  - Current size: about 700 lines.
  - Final layout keeps the original `_test.dart` entrypoint as the library
    owner and moves core parsing, row-type handling, and defensive checks into
    `stages/row_parser/` part files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/stages/row_parser_stage_test.dart`
- [x] Split or helper-extract `grid_line_detection_stage_test.dart`.
  - Current size: about 650-700 lines.
  - Final layout keeps the original `_test.dart` entrypoint as the library
    owner and moves model, detector, density-filtering, and multi-page groups
    into `stages/grid_line_detection/` part files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/stages/grid_line_detection_stage_test.dart`
- [x] Split or helper-extract `region_detection_stage_test.dart`.
  - Current size: about 600 lines.
  - Final layout keeps the original `_test.dart` entrypoint as the library
    owner and moves region behavior groups into `stages/region_detection/` part
    files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/stages/region_detection_stage_test.dart`
- [x] Extract shared Google Assisted replay diagnostics from
  `gocr_downstream_replay_test.dart`.
  - Current size: about 800 lines.
  - Final layout keeps the opt-in replay harness in the original `_test.dart`
    entrypoint and moves result summary, expected comparison, output writing,
    diagnostics, compaction, sampling, and failure/path helpers into
    `integration/gocr_downstream_replay/` part files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart`
- [x] Split `gocr_ocr_cache_test.dart`.
  - Current size: about 600 lines.
  - Final layout keeps the shared temp-directory lifecycle and fake engine in
    the original `_test.dart` entrypoint and moves capture/replay, validation
    failure, fingerprint drift, and normalized replay cases into
    `helpers/gocr_ocr_cache/` part files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/helpers/gocr_ocr_cache_test.dart`
- [x] Split `cell_boundary_verification_test.dart`.
  - Final layout keeps the fixture lifecycle in the original `_test.dart`
    entrypoint and moves boundary behavior groups into
    `stages/cell_boundary_verification/` part files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/stages/cell_boundary_verification_test.dart`
- [x] Split `mock_stages.dart`.
  - Final layout keeps the helper library entrypoint and moves stage mock
    families into `helpers/mock_stages/` part files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/pipeline/re_extraction_loop_test.dart`
- [x] Split `extraction_pipeline_test.dart`.
  - Final layout keeps the pipeline test library entrypoint and moves behavior
    groups and pipeline fixtures into `pipeline/extraction_pipeline/` part
    files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/pipeline/extraction_pipeline_test.dart`
- [x] Split `extraction_metrics_test.dart`.
  - Final layout keeps the metrics entrypoint and moves metric behavior groups
    into `pipeline/extraction_metrics/` part files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/pipeline/extraction_metrics_test.dart`
- [x] Split `full_pipeline_integration_test.dart`.
  - Final layout keeps the integration entrypoint and moves fixture readiness,
    baseline quality/math, persistence/conversion, and postprocess sidecar
    groups into `integration/full_pipeline_integration/` part files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/integration/full_pipeline_integration_test.dart`
- [x] Split the downstream contract tests.
  - Final layouts keep each contract entrypoint and move behavior groups into
    `contracts/column_detection_to_cell_extraction/` and
    `contracts/post_processing_to_quality_validation/` part files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/contracts/column_detection_to_cell_extraction_contract_test.dart`
    - [x] `flutter test test/features/pdf/extraction/contracts/post_processing_to_quality_validation_contract_test.dart`
- [x] Split report/comparator helper files that had become god helpers.
  - Final layout moves comparator result types, comparator core, regression
    gate, and compatibility API into `helpers/pipeline_comparator/` part files.
  - Final layout moves report JSON trace generation, scorecard generation, and
    report I/O into `helpers/report_generator/` part files.
  - Verification:
    - [x] `dart analyze test/features/pdf/extraction/helpers/pipeline_comparator.dart test/features/pdf/extraction/helpers/report_generator.dart`
    - [x] `flutter test test/features/pdf/extraction/helpers/report_generator_test.dart test/features/pdf/extraction/integration/full_pipeline_integration_test.dart`
- [x] Split or helper-extract `ocr_row_band_page_recognition_stage_test.dart`.
  - Current size: about 1.2k lines.
  - Keep under Custom/local OCR.
  - Final layout keeps the original `_test.dart` entrypoint as the library
    owner and moves each scenario into `stages/ocr_row_band_page_recognition/`
    part files.
  - Verification:
    - [x] `flutter test test/features/pdf/extraction/stages/ocr_row_band_page_recognition_stage_test.dart`
- [x] Extract shared Google Assisted integration runtime helpers from
  `pre_release_pdf_corpus_test.dart` and `springfield_report_test.dart` only
  after the current GOCR replay gates are stable.
  - Final layout keeps each integration test's main execution flow in the root
    file and moves private runtime, output, comparison, platform/file, upload,
    and gate helpers into harness-specific part folders under
    `integration_test/pre_release_pdf_corpus/` and
    `integration_test/springfield_report/`.
  - Verification:
    - [x] `dart analyze integration_test/pre_release_pdf_corpus_test.dart integration_test/springfield_report_test.dart`

## Verification Gates

- [x] After each test split, run the moved test folder/file only.
- [x] After shared downstream refactors, run:
  - `flutter test test/features/pdf/extraction/stages/row_splitter_test.dart`
  - `flutter test test/features/pdf/extraction/stages/post_processing`
  - `flutter test test/features/pdf/extraction/stages/column_detection`
- [x] Before parser rule work resumes, run the fast GOCR downstream replay
  corpus from the cached `.tmp/google_ocr_research` run root.
  - Latest run:
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_054823`.
  - Current replay state after general parser rules:
    - Berrien: 200/200 rows; checksum `$6,645,715.50` vs `$7,467,543.00`.
    - Grand Blanc: 118/118 rows; checksum `$7,883,213.14` vs
      `$7,918,199.14`.
    - Huron Valley: 140/140 rows; checksum `$10,524,412.76` vs
      `$10,531,942.76`.
    - MDOT samples: `826/830`, `903/900`, `682/680`, `654/676`.
  - Parser-quality rule changes landed in this pass:
    - GOCR replay now uses the same Google-assisted row classifier and region
      detector profile as the production Google-assisted path.
    - Noisy unit recovery is generalized through unit-token recovery.
    - Region span keeps short currency-marked split table fragments before the
      next same-page data row without bridging schedule metadata.
    - Row rescue can recover split item starts after numeric/price continuation
      fragments.
    - Local-sequence priced row splitting handles OCR decimal item-number
      artifacts after sequence rescue.
    - Row-merger diagnostics/tests now cover anchorless data continuations,
      though the latest replay shows the Grand Blanc 24-31 window still needs
      deeper classification/materialization work.
- [ ] Before declaring the lane complete, run the connected S21 real-Google
  gate with no OCR fallback and no replay cache.
  - Not run yet in this pass because the fast cached downstream replay still
    has known parser failures. Use S21 serial `RFCNC0Y975L` when this gate is
    ready.

## 2026-04-14 Audit Addendum

- `test/features/pdf/extraction/helpers/report_generator.dart` drifted over
  the new 500-line PDF extraction lint limit at 503 lines. It was trimmed to
  494 lines without behavior changes.
- Focused diagnostics were added to the GOCR downstream replay summary:
  row-rescue decisions, region span decisions, and compact local-sequence item
  windows.
- Focused verification run:
  - `flutter test test/features/pdf/extraction/stages/region_table_span_stage_test.dart`
  - `flutter test test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart`
  - `flutter test test/features/pdf/extraction/stages/row_splitter_test.dart`
  - `flutter test test/features/pdf/extraction/stages/row_merger_test.dart`
  - `flutter test test/features/pdf/extraction/stages/post_processing/repair_log_test.dart`
  - `dart analyze lib/features/pdf/services/extraction/stages/region_table_span_stage.dart lib/features/pdf/services/extraction/stages/row_rescue_adjustment_stage.dart lib/features/pdf/services/extraction/stages/row_splitter.dart lib/features/pdf/services/extraction/stages/row_merger.dart test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart test/features/pdf/extraction/stages/region_table_span_stage_test.dart test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart test/features/pdf/extraction/stages/row_splitter_test.dart test/features/pdf/extraction/stages/row_merger_test.dart`

### Pipeline Direction From Checksum Audit

- Treat 100% item count as a weak gate until it is paired with row identity and
  arithmetic checks. The latest local bid replay shows `200/200`, `118/118`,
  and `140/140`, but the checksums remain low by `$821,827.50`, `$34,986.00`,
  and `$7,530.00`.
- The failures are not one uniform "extra rows" bug:
  - Berrien has a full six-column map and one region. Its dominant failure is
    numeric amount corruption: 18 rows where `quantity * unitPrice` differs
    from `bidAmount` account for `$813,635.50` of the `$821,827.50` checksum
    gap. The current post-consistency path can backsolve unit price to match a
    corrupted bid amount, so the next rule should prefer the stable
    quantity/unit-price pair when raw bid text has dropped or displaced digits.
  - Grand Blanc has one region but only a five-column map with no explicit
    quantity column. Around items 24-31, `HOUR 30`, `EA 12`, and `FT 4,250`
    are collapsed into the unit column, then sequence rescue shifts later rows
    while keeping the count at 118. The next rule should fix quantity-column
    inference and row-boundary association before adding more post-split rules.
  - Huron Valley has the same five-column map shape and no simple arithmetic
    mismatches. Its `$7,530.00` gap comes from sequence rescue fabricating local
    items from dimension text such as `6" x 6" x 6"` and `8"`, then renumbering
    the next real anchored rows. The next rule should make local sequence rescue
    reject dimension-only anchors unless the row has a complete structured
    payload.
  - MDOT schedule PDFs are a separate class: no checksum is available, and the
    remaining failures are row inclusion/count issues around schedule table
    spans and between-table report metadata. Do not use local bid checksum
    heuristics to tune MDOT.
- Next implementation order:
  1. Add a row-identity diagnostic gate to the replay summary: first raw leading
     item number, repaired item number, arithmetic status, and structured
     payload status for every local sequence item.
  2. Fix Berrien's numeric root cause in post consistency/math repair: support
     missing-digit/displaced-separator bid amount repair from
     `quantity * unitPrice`, and stop blindly backsolving unit price when the
     bid amount is the lone corrupted field.
  3. Fix Grand/Huron column detection: infer a quantity column between unit and
     unitPrice when the detected unit column consistently contains
     `<unit> <quantity>` and the unit/unitPrice spans overlap.
  4. Gate row parser sequence rescue on row identity: do not infer or advance a
     local item number from dimension-only text or from anchorless continuation
     rows when the previous item is incomplete.
  5. Re-run cached replay after each rule, then run the connected S21
     real-Google gate only after the cached replay stops showing known parser
     failures.

### 2026-04-14 Continued Replay Audit

- Cached replay run:
  `.tmp/google_ocr_research/codex_downstream_replay_20260414_raw_bid_digit_05`.
- Berrien is now exact in cached replay:
  - 200/200 items; checksum `$7,467,543.00` vs `$7,467,543.00`.
  - General numeric rules now cover the source-confirmed rows where raw bid
    digit artifacts hid opposing errors: item 41 (`$17.80 / $104,877.60`) and
    item 50 (`$9.10 / $13,559.00`).
  - A false-positive guard was added for exact-math rows with clean raw currency
    support, after item 52 (`$4.65 / $5,552.10`) proved that a trailing table
    border artifact alone must not trigger a unit-price digit repair.
- Grand Blanc remains low by `$34,986.00`, and the gap is now row-localized:
  - Page 2/source item 24 is present in OCR but parsed without its structured
    numeric payload; this accounts for `$18,424.00`.
  - Page 4/source item 57 is skipped/shifted at the top of the table fragment;
    this accounts for `$5,760.00`.
  - Page 5/source item 100 (`Dr Structure Cover, Adj, Case 1`) is skipped while
    the adjacent case row survives; this accounts for `$9,090.00`.
  - Page 6/source items 113 and 116 have complete quantity/unit price values
    but lose bid amounts; these account for `$704.00` and `$1,008.00`.
- Huron Valley remains low by `$7,530.00`, also row-localized:
  - Page 4/source item 57 is skipped/shifted; this accounts for `$5,460.00`.
  - Page 4/source item 77 (`Reducer, 12" x 10"`) is skipped/shifted; this
    accounts for `$2,070.00`.
- Direction change:
  - Do not continue with broad checksum or post-processing bid synthesis for
    Grand/Huron. Their remaining failures start upstream where OCR elements are
    available but row/cell materialization and row parsing associate numeric
    cells with the wrong local sequence row or omit them entirely.
  - Next implementation should add a focused row/cell association diagnostic
    for the localized source rows above, then fix the earliest stage that drops
    the row payload. The expected general rule shape is: preserve a structured
    row's own numeric cells when a local item anchor is present, and prevent
    dimension/description continuation rows from consuming the following
    structured row's numeric payload.

## Notes

The 500-line target is a maintainability target, not a blind rule. It is better
to keep a cohesive 650-line file than to split one behavior across several
files that need cross-file reading. The hard failures are files that mix
pipeline ownership or hide many unrelated stages behind one test fixture.

## Appended Continuation TODO - 2026-04-14

- [x] Re-read the latest GOCR specs and uncommitted prior-session changes before
  continuing parser work.
- [x] Create and wire full item-level ground truths for all four baseline PDFs:
  Berrien County (`200` rows), Grand Blanc (`118` rows), Huron Valley (`140`
  rows), and Springfield (`131` rows). Each fixture now carries every expected
  item number, description, unit, quantity, unit price, and bid amount.
- [x] Strengthen the cached replay gate so it compares every extracted row and
  every expected column against `ground_truth_items_path`, not only checksums or
  spot validations. The summary also now emits row/column diagnostics for every
  extracted item.
- [x] Confirm the parser prefix rule is general: item-number cells that contain
  an item number plus leading description text now promote that text into the
  description while guarding against duplicate prefixes and numeric-only
  fragments.
- [x] Back out the experimental global deskew grouping rule. It was rejected
  because it regressed the full four-PDF corpus, inflated totals, and failed the
  focused row-grouping suite. Do not reintroduce global row deskew without a
  corpus-level invariant that proves it preserves row count and payload
  ownership.
- [x] Re-run the stable cached replay after the deskew backout:
  `.tmp/google_ocr_research/codex_downstream_replay_20260414_after_deskew_revert_01`.
- [ ] Continue updating this spec after each meaningful replay run so the active
  full-row/full-column failure set stays concrete.
- [ ] Grand Blanc next target:
  - Current latest replay:
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_pending_desc_prefix_01`.
  - Item count is `118/118`; checksum is now exact at `$7,918,199.14`.
  - Full ground-truth comparison is down to `1` description mismatch:
    item 24 continuation ordering (`Non-Hazardous Contaminated Material
    Handling And` vs `Disposal Contaminated Material Handling`).
  - The page-scoped leading structured-payload row-merger rule fixed the item
    57 top-of-page shift. It is intentionally page-scoped: once the first data
    item after a page/table header proves that structured numeric fragments
    precede the item anchor, later anchored rows on that page may pull their
    immediately preceding structured fragments. A broader global leading rule
    was rejected because it shifted normal rows.
  - The row-parser pending description-prefix rule fixed items 27/28 by
    carrying skipped anchored description-only rows (`27 | Sanitary`,
    `28 | Sanitary`) into the next structured rows that resolved to the same
    item number.
  - Item 24's checksum payload is restored, but full text comparison still
    shows a continuation-order description mismatch. Keep that as a separate
    description-ordering fix; do not special-case `Disposal`.
  - A speculative leading-boilerplate attachment plus inferred local-sequence
    fanout was tried in
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_leading_boilerplate_attach_01`
    and backed out because it produced huge checksum regressions. Do not
    reintroduce inferred fanout from a single item number; the next attempt
    needs a safer row-identity/source-row association rule.
- [ ] Huron Valley next target:
  - Current latest replay:
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_pending_desc_prefix_01`.
  - Current state: `140/140`; checksum `$10,534,586.76` vs `$10,531,942.76`,
    so the remaining net error is `$2,644.00` high.
  - Full ground-truth comparison is down to `15` row/column mismatches.
  - The page-scoped leading structured-payload row-merger rule fixed the item
    57 shift. The remaining numeric failures are localized to later rows on the
    same page: item 63, item 77, and item 83/84 ownership. Item 77's correct
    `$2,070.00` row is still present in upstream classified diagnostics, but it
    is not yet associated with item 77 because the unit/description material
    between the numeric fragment and anchor needs a more precise diagnostic
    before adding another rule.
  - The row-parser exact-repeat local sequence rescue tightening recovered the
    `$2,070.00` Reducer row: raw item `76 Reducer, 16" x 12"` now remains item
    `76` instead of being rewritten to a duplicate `77` and dropped by the later
    field-confidence pass.
- [ ] Improve row/cell association diagnostics so the summary can answer where
  the row disappeared for a specified item number even when the text terms do
  not all land in one physical row.
- [ ] Springfield next target:
  - Current latest replay:
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_pending_desc_prefix_01`.
  - Current state: `129/131`; missing expected item numbers `119` and `124`.
  - Checksum is massively inflated: `$1,555,349,145,344.95` vs expected
    `$7,882,926.73`.
  - Full ground-truth comparison currently reports `23` row/column mismatches.
    The largest failures are upstream row/cell merges: item 118 absorbs timber
    wall repair material and item 123 absorbs adjacent pavement-marking text and
    quantities. Fix after the shared Grand/Huron item 57 shift, unless the same
    row-ownership rule naturally covers it.
- [ ] Berrien next target:
  - Current latest replay:
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_pending_desc_prefix_01`.
  - Current state: `200/200`; checksum exact at `$7,467,543.00`.
  - Full ground-truth comparison still reports `58` row/column mismatches,
    mostly OCR glyph/unit normalization and description text cleanup. Treat
    these as general OCR normalization rules only when they are supported by
    column context and known unit vocabulary, not by PDF-specific strings.
- [x] Add a focused row-parser unit test for preserving sequential
  description-only local item rows when the previous local item is present.
- [ ] Fix the earliest general stage that causes the localized Grand/Huron
  drops. Prefer row identity and structured-payload preservation rules over
  post-processing bid synthesis.
- [x] Re-run the cached GOCR downstream replay after the sequence-stub parser
  rule.
- [x] Run the focused row-parser stage suite after the sequence-stub parser
  rule.
- [ ] Only after cached replay stops showing known parser failures, run the
  connected S21 real-Google gate on `RFCNC0Y975L` with no OCR fallback and no
  replay cache.

## Appended Research Audit TODO - 2026-04-14

Source refresh: official Google Cloud Vision docs for OCR, PDF/TIFF OCR,
`fullTextAnnotation`, and feature selection.

- [x] Keep the rule standard algorithm explicit:
  - Every new production rule must name the upstream invariant it uses, such as
    "same-page anchored row is incomplete and immediately adjacent structured
    fragments complete unit/quantity/price/bid payload."
  - Every rule must be replayed against all four ground-truth PDFs, not just the
    row that motivated it.
  - If a rule fixes one PDF but shifts another, back it out or narrow it by a
    corpus-stable invariant.
- [x] Refresh Cloud Vision OCR guidance:
  - Use `DOCUMENT_TEXT_DETECTION` for dense document/table pages because Google
    documents it as optimized for dense text and documents, with page/block/
    paragraph/word/symbol structure in `fullTextAnnotation`.
  - Keep `languageHints` empty for this English/Latin bid-table corpus unless a
    measured failure proves a hint helps; Google warns that wrong hints can
    hurt and usually are unnecessary for Latin text.
  - Treat PDF/TIFF async output as structured OCR geometry with normalized
    vertices in `[0,1]`, not as a line-perfect table extractor.
  - Document AI remains a possible future product-level pivot for structured
    form/table parsing, but do not mix it into this GOCR cached replay lane
    until the current Vision pipeline has exhausted general row/cell rules.
- [x] Confirm current GOCR pipeline direction:
  - Continue using Vision geometry and downstream row/cell association instead
    of checksum-only synthesis. The latest exact Grand checksum still had a
    description mismatch, proving checksum alone is not enough.
  - Continue improving replay diagnostics so each mismatch can be traced from
    raw OCR elements to classification, merging, cell assignment, numeric
    interpretation, parsing, post-validation, and final ground-truth comparison.
  - Keep the four full fixtures as the gate for all row and column values:
    item number, description, unit, quantity, unit price, bid amount, checksum,
    row count, and missing/duplicate item numbers.
- [x] Record rejected 2026-04-14 rule attempts:
  - A direct same-page leading text-only description-fragment merge was tried in
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_leading_desc_same_line_prefix_01`
    and backed out. It did not fix Grand item 24 and increased the all-four
    replay failures, including Berrien `58 -> 61` row/column mismatches and
    Springfield `23 -> 32`.
  - A same-line item-number-cell prefix guard was then tested by itself in
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_same_line_prefix_only_01`
    and backed out. It also left Grand item 24 unchanged and increased Berrien
    `58 -> 61`.
  - Confirmed return-to-baseline run:
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_after_rejected_rule_backouts_01`.
    Current baseline remains Grand `1` description mismatch, Berrien `58`
    row/column mismatches with exact checksum, Huron `15` row/column mismatches
    and `$2,644.00` high checksum, and Springfield `23` row/column mismatches
    with missing `119`/`124`.
- [ ] Next general-rule candidates, in order:
  - Use the enriched replay diagnostics from
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_term_windows_01`.
    The replay now emits `assigned_term_row_windows`,
    `merged_term_row_windows`, `cell_term_row_windows`, and
    `numeric_term_row_windows` so split-term failures can be traced by nearby
    row neighborhoods even when no single row contains every focus term.
  - Inspect Grand item 24 through the cell-assignment stage before adding
    another rule. The visual PDF confirms the ground truth is
    `Non-Hazardous Contaminated Material Handling And Disposal`; the remaining
    failure is upstream OCR/cell ownership that currently drops
    `Non-Hazardous`, moves `And` into the unit cell, and promotes `Disposal` as
    an item-number-cell prefix. Do not reintroduce the rejected leading-text
    merge or same-line prefix guard without a stronger corpus-stable invariant.
  - Improve diagnostics for Huron item 63/77/83 windows to show nearby row
    ownership even when source terms are split across non-adjacent rows.
  - Fix Huron's remaining `$2,644.00` high checksum through upstream row/cell
    association, not post-processing total correction.
  - Fix Springfield's item 118/123 merge explosions by preventing complete
    structured rows from absorbing adjacent complete pay items.
  - Add context-backed OCR normalization for Berrien only when supported by
    column semantics and unit vocabulary, such as known-unit repair in the unit
    column; do not add description string substitutions.

## Appended Audit TODO - 2026-04-14 Late Pass

- [x] Reconfirmed the rule standard:
  - The retained production rules in this branch use algorithmic invariants
    such as row identity, same-page adjacency, local item sequence, structured
    numeric payload presence, unit vocabulary, and arithmetic consistency.
  - New attempts in this pass were also algorithmic, but they were rejected
    because the full four-PDF replay proved they were not corpus-stable. They
    must not be reintroduced as PDF-specific exceptions.
- [x] Corrected full ground truth where visual page evidence contradicted the
  fixture:
  - Grand Blanc item 24 is
    `Non-Hazardous Contaminated Material Handling And Disposal`.
  - Huron Valley item 28 is
    `Non-Hazardous Contaminated Material Handling And Disposal`, not just
    `Disposal`; verified against `.tmp/ground_truth_pdf_pages/huron-2.png`.
- [x] Rejected parser/cell/merger experiments from this pass:
  - Embedded item-number geometry splitting and unit-prefix splitting fixed part
    of Grand item 24 but collapsed Grand items 100/101 into a massive checksum
    regression. Backed out.
  - Same-baseline leading text-prefix merge was tried after parser backout. It
    remained general but produced no net corpus improvement and changed Grand/
    Huron failure shape by promoting item/text fragments in the wrong order.
    Backed out.
  - Continuation-line cell reassignment was tried in
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_continuation_cell_reassign_01`
    and narrowed in
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_continuation_cell_reassign_02`.
    It improved Springfield row/column mismatch count from `23` to `20`, but
    regressed Berrien from `58` to `61` and Grand from `1` to `2`, while Huron
    remained at `15`. Backed out.
- [x] Re-established the stable cached baseline after backouts:
  - Latest baseline run:
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_cell_reassign_backout_huron_gt_01`.
  - Berrien: `200/200`, checksum exact `$7,467,543.00`, `58` row/column
    mismatches.
  - Grand Blanc: `118/118`, checksum exact `$7,918,199.14`, `1` row/column
    mismatch: item 24 description ordering/ownership.
  - Huron Valley: `140/140`, checksum `$10,534,586.76` vs `$10,531,942.76`,
    `15` row/column mismatches after fixture correction.
  - Springfield: `129/131`, missing `119` and `124`, checksum
    `$1,555,349,145,344.95` vs `$7,882,926.73`, `23` row/column mismatches.
- [ ] Next safe diagnostic step:
  - Add row/cell ownership diagnostics that include source physical row type
    and base-vs-continuation provenance for every element in a merged data row.
    The current trace shows final cell values but not enough provenance to write
    a safe reassignment rule.
  - Use those diagnostics on Grand item 24 and Huron items 27/28 before another
    production change. The likely rule shape is row-ownership aware, not string
    aware: a continuation fragment should only move between item rows when its
    source physical row is more strongly aligned to the following local item
    anchor than to the previous complete structured row.
  - Keep checking every row and every column through the exhaustive fixture gate
    after each rule; checksum exactness is necessary but not sufficient.
