# GOCR Stage Trace And Ground Truth Spec

Created: 2026-04-14

## Direction Change

We are pausing new extraction-rule iteration until the GOCR replay harness can
account for every source value at every stage through one durable output
endpoint.

The current replay proves the risk: a comparator that normalizes punctuation,
spacing, case, or numeric tolerance can make Grand Blanc, Huron Valley, and
Springfield appear clean while exact character-for-character comparison still
finds many row/column mismatches. Exact totals are necessary but no longer
sufficient. We need a trace format that shows exactly when every cell changes,
disappears, moves columns, or gets repaired.

## Non-Negotiables

- [ ] Every baseline PDF must have a 100% visually verified ground-truth JSON
  for every pay item row and every compared column:
  - [ ] `item_number`
  - [ ] `description`
  - [ ] `unit`
  - [ ] `quantity`
  - [ ] `unit_price`
  - [ ] `bid_amount`
  - [ ] `confidence`
  - [ ] `fields_present`
- [ ] Ground truth must be corrected only from visual PDF evidence or explicit
  user confirmation.
- [ ] Ground-truth corrections must be recorded as fixture corrections, not as
  production rules.
- [ ] Production fixes must be algorithmic and corpus-stable. They may use row
  geometry, stage provenance, unit vocabulary, numeric consistency, local item
  sequence, and complete structured payloads. They must not key off PDF names,
  contractor names, fixture paths, or item numbers specific to one document.
- [ ] Every new rule must run against all four baseline PDFs in one replay.
- [ ] Checksum, row count, item number, and every field comparison must all pass
  before a PDF is considered locked down.
- [ ] The ground-truth comparator must not normalize, coerce, trim, round,
  case-fold, punctuation-fold, or tolerate deltas. It must compare raw expected
  fixture values to raw final pipeline values exactly.
- [ ] Any cleanup or canonicalization must happen in a named production stage
  and be visible in the trace as an input value, output value, rule/reason, and
  mutation. The comparator is only a measuring instrument.
- [ ] Large device logs, such as S21 console output, are not the primary debug
  artifact. The primary artifact must be a structured replay trace written once
  at the end of the run.

## Baseline PDFs

- [ ] Berrien County `berrien_127449_us12-pay-items`
  - Current latest run:
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_debug_endpoint_01`
  - State: exact comparator reports 201 row/column mismatches.
  - Current root-cause status: `201/201` mismatches are explicitly
    `unresolved_placeholder`; no mismatch is marked resolved from a placeholder
    bucket.
  - Current source-cell provenance gaps: `162` final fields
    (`27` each for item number, description, unit, quantity, unit price, and
    bid amount).
  - Primary risk: final totals are correct while descriptions/units still have
    OCR glyph, column, punctuation, spacing, and production-stage mutation
    errors.
- [ ] Grand Blanc `grand_blanc_938710_sewer-pay-items`
  - Current latest run:
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_debug_endpoint_01`
  - State: exact comparator reports 89 row/column mismatches.
  - Current root-cause status: `89/89` mismatches are explicitly
    `unresolved_placeholder`.
  - Current source-cell provenance gaps: `120` final fields
    (`20` each for item number, description, unit, quantity, unit price, and
    bid amount).
  - Corrected status: not locked down character-for-character.
- [ ] Huron Valley `huron_valley_917245_dwsrf-pay-items`
  - Current latest run:
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_debug_endpoint_01`
  - State: exact comparator reports 112 row/column mismatches.
  - Current root-cause status: `112/112` mismatches are explicitly
    `unresolved_placeholder`.
  - Current source-cell provenance gaps: `72` final fields
    (`12` each for item number, description, unit, quantity, unit price, and
    bid amount).
  - Corrected status: not locked down character-for-character.
- [ ] Springfield `springfield-864130`
  - Current latest run:
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_debug_endpoint_01`
  - State: exact comparator reports 103 row/column mismatches.
  - Current root-cause status: `103/103` mismatches are explicitly
    `unresolved_placeholder`.
  - Current source-cell provenance gaps: `12` final fields
    (`2` each for item number, description, unit, quantity, unit price, and bid
    amount).
  - Corrected status: not locked down character-for-character. Item 99 remains
    visually/user-confirmed as `HMA, 5EML`; `SEML` is incorrect.

## Single Trace Endpoint

- [x] Create one replay trace endpoint that can write a single structured file
  per replay run, separate from device/Flutter console logs.
- [x] Default target:
  `.tmp/google_ocr_research/<run_id>/traces/<document_key>-stage-trace.json`.
- [x] Add an optional compact summary target:
  `.tmp/google_ocr_research/<run_id>/summaries/<document_key>-stage-trace-summary.json`.
- [x] Keep the existing replay summary, but stop relying on a truncated failure
  message as the debugging surface.
- [ ] Make the trace endpoint usable by either:
  - [x] no-render cached GOCR replay, or
  - [x] a driver/debug diagnostics route that consumes the same trace schema.
    - `GET /diagnostics/gocr-trace` lists runs.
    - `GET /diagnostics/gocr-trace?run=<run_id>` returns the run manifest.
    - `GET /diagnostics/gocr-trace?run=<run_id>&document=<document_key>&artifact=<trace|summary|mismatches|mismatches_csv>`
      returns the selected branch artifact.
- [x] The endpoint must flush at the end of the document run so the device log
  can remain terse.

## Trace Schema TODO

- [x] Add `trace_schema_version`.
- [x] Add `document_key`, `expected_key`, source PDF/cache metadata, provider,
  and run timestamp.
- [x] Add `ground_truth_fixture` metadata:
  - [x] fixture path
  - [x] fixture item count
  - [x] expected checksum
  - [x] verification status
  - [x] last visual review note, if available
- [x] Add a canonical `cell_id` for each observed value.
  - [x] Stable across stages where possible.
  - [x] Includes document key, page index, physical row index, element index,
    and source text span/hash.
- [x] Add a canonical `logical_row_id` for each parsed/pay-item row.
- [x] Add a canonical `logical_field` enum:
  - [x] `item_number`
  - [x] `description`
  - [x] `unit`
  - [x] `quantity`
  - [x] `unit_price`
  - [x] `bid_amount`
- [x] Add `source_provenance` to every final field:
  - [ ] physical source row(s)
    - Current artifact has cell/token provenance when a final row can be
      matched, but some cell traces still emit `unknown_row` and not every
      final field has physical-row provenance.
  - [ ] base row vs continuation row
  - [x] source column assignment
  - [x] raw OCR token IDs when the final row can be matched to a source cell
  - [x] stage that last mutated the value
- [x] Add `mutation_history` to every final field:
  - [x] stage name
  - [x] input value
  - [x] output value
  - [ ] rule name or stage decision
    - Current artifact uses snapshot-diff placeholders such as
      `stage_snapshot_observation`. That proves when a value changed, but not
      yet which production rule caused it.
  - [ ] reason code
    - Current artifact uses generic observation reason codes. This must be
      tied to stage-local repair/mutation records before the intent is fully
      captured.
  - [x] confidence before/after
  - [x] whether value changed, moved, was dropped, was synthesized, or was
    copied forward unchanged
- [x] Add `stage_invariants` per stage:
  - [x] row count in/out
  - [x] cell count in/out
  - [x] item count in/out
  - [x] dropped element count
  - [x] orphan element count
  - [x] duplicated item number count
  - [x] invalid unit count
  - [x] arithmetic mismatch count

## Stage Coverage TODO

- [ ] OCR cache input:
  - [ ] every OCR element
  - [ ] text
  - [ ] confidence
  - [ ] page index
  - [ ] bounding box / normalized coordinates
- [ ] element validation:
  - [ ] input element ID
  - [ ] output element ID
  - [ ] clamping or rejection reason
- [ ] row grouping:
  - [ ] every physical row
  - [ ] ordered element IDs
  - [ ] grouping strategy
  - [ ] page index and row index
- [ ] row classification:
  - [ ] every row type
  - [ ] reason code
  - [ ] confidence
  - [ ] semantic features used
- [ ] region detection:
  - [ ] included and excluded rows
  - [ ] inclusion/exclusion reason
  - [ ] table span boundaries
- [ ] column detection:
  - [ ] column boundaries
  - [ ] selected method
  - [ ] per-page adjustments
  - [ ] rejected candidate methods
- [ ] row merging:
  - [ ] base row ID
  - [ ] continuation row IDs
  - [ ] merge reason
  - [ ] all element IDs in merged order
  - [ ] base-vs-continuation provenance for each element
- [ ] cell extraction:
  - [ ] assignment decision per element
  - [ ] assigned logical column
  - [ ] rejected/orphan elements
  - [ ] materialized cells with ordered element IDs
- [ ] numeric interpretation:
  - [ ] raw text
  - [ ] display text
  - [ ] parsed value
  - [ ] interpretation rule
  - [ ] rejected numeric candidates
- [ ] row parsing:
  - [ ] raw cells in
  - [ ] parsed item out
  - [ ] skipped row reason
  - [ ] local item sequence decision
- [ ] post-normalization:
  - [ ] normalized description/unit/number values
  - [ ] repair notes with rule names
- [ ] post-splitting:
  - [ ] input row(s)
  - [ ] split output row(s)
  - [ ] split reason
- [ ] post-validation:
  - [ ] math validation inputs
  - [ ] accepted/rejected candidate repairs
  - [ ] checksum contribution by row
- [ ] sequence correction:
  - [ ] neighbor rows consulted
  - [ ] rule preconditions
  - [ ] value changes
- [ ] deduplication:
  - [ ] duplicate groups
  - [ ] row kept/removed/rekeyed
- [ ] field confidence:
  - [ ] final per-field confidence
  - [ ] confidence source
- [ ] final comparison:
  - [ ] every expected row
  - [ ] every actual row
  - [ ] every compared field
  - [ ] raw expected comparison value
  - [ ] raw actual comparison value
  - [ ] exact comparison mode
  - [ ] mismatch reason
  - [ ] root-cause bucket

## Full Mismatch Artifact TODO

- [x] Add a complete mismatch artifact for every replay run:
  `.tmp/google_ocr_research/<run_id>/failures/<document_key>-mismatches.json`.
- [x] Include one entry per field mismatch, not a truncated joined string.
- [x] Include:
  - [x] document key
  - [x] item number
  - [x] field
  - [x] expected value
  - [x] actual value
  - [x] raw expected comparison value
  - [x] raw actual comparison value
  - [x] exact comparison mode
  - [x] raw item number
  - [x] raw description
  - [x] raw unit
  - [x] raw quantity
  - [x] raw unit price
  - [x] raw bid amount
  - [x] last mutating stage
  - [x] root-cause bucket
  - [x] source provenance IDs
- [x] Add a companion CSV for quick visual scanning:
  `.tmp/google_ocr_research/<run_id>/failures/<document_key>-mismatches.csv`.
- [x] Keep the test failure message short and point to the artifact path.

## Root-Cause Buckets

Use these buckets on every mismatch before adding production code:

- [ ] `fixture_error`
  - Ground truth is wrong or incomplete after visual PDF review.
- [ ] `ocr_source_error`
  - Vision OCR source text/glyph is wrong before downstream processing.
- [ ] `element_validation_error`
  - Source text is lost or geometry is damaged during validation.
- [ ] `row_grouping_error`
  - Tokens from one physical row are split incorrectly or unrelated rows merge.
- [ ] `row_classification_error`
  - Physical row type is wrong.
- [ ] `region_detection_error`
  - Correct row is excluded from the table span or an unrelated row is included.
- [ ] `column_detection_error`
  - Column boundaries are wrong for the page/region.
- [ ] `row_merging_error`
  - Continuation row ownership is wrong, or a complete item absorbs another
    item's text/numerics.
- [ ] `cell_assignment_error`
  - Tokens are assigned to the wrong logical column.
- [ ] `numeric_interpretation_error`
  - Raw numeric/currency text is parsed incorrectly.
- [ ] `row_parsing_error`
  - Correct cells enter row parsing but the parsed item fields are wrong.
- [ ] `post_normalization_error`
  - Description/unit cleanup changes correct data or misses a general cleanup.
- [ ] `post_split_error`
  - Split/compaction creates, drops, or misroutes an item.
- [ ] `post_validation_error`
  - Math repair chooses a wrong candidate.
- [ ] `sequence_correction_error`
  - Neighbor-based sequence repair moves or rewrites the wrong text.
- [ ] `deduplication_error`
  - Correct row is removed or rekeyed incorrectly.
- [ ] `field_confidence_error`
  - Final value is right but confidence/field evidence is misleading.
- [ ] `comparison_error`
  - Final output and fixture are semantically equal but comparison logic says
    they differ.

## Ground Truth Verification TODO

- [x] Create a per-PDF ground-truth verification ledger:
  `.tmp/google_ocr_research/ground_truth_review/<document_key>-review.md`.
- [ ] For each item, record:
  - [x] item number
  - [x] description
  - [x] unit
  - [x] quantity
  - [x] unit price
  - [x] bid amount
  - [ ] visual PDF page/source note
  - [ ] reviewer/date
  - [x] correction note column if changed
- [ ] Verify Berrien end-to-end again before continuing extraction-rule work.
- [ ] Verify Grand Blanc item 24 remains correct after the latest production
  fix.
- [ ] Verify Huron Valley items 27/28 remain correct after the latest
  production fix.
- [ ] Verify Springfield item 99 remains `HMA, 5EML`; `SEML` is incorrect.
- [ ] Add a fixture-review status field or sidecar so unreviewed fixtures are
  not silently treated as locked.

## Regression And Lint Guardrails TODO

- [x] Add a custom lint/check that production extraction code cannot branch on
  fixture/PDF/document keys.
- [x] Add a custom lint/check that post-processing rules have stable reason
  codes and rule names in repair logs.
  - Implemented `no_generic_gocr_repair_trace_codes`.
  - Post-processing repair `rule_name` and `reason_code` are now generated
    from stable stage/type/logical-field metadata; free-form repair text stays
    in `reason`.
- [x] Add a custom lint/check that new ground-truth fixture edits update the
  review ledger.
  - Added `gocr_ground_truth_review_status.json` as the fixture-review sidecar.
    Current statuses remain `needs_visual_pdf_review`, so no fixture is treated
    as locked.
- [x] Add a custom lint/check that replay failure output includes full mismatch
  artifact paths when failures exist.
- [x] Add a test that all baseline ground-truth fixtures contain the same
  required fields for every row.
- [x] Add a test that ground-truth fixture item counts match the corpus expected
  metadata.
- [x] Add a test that the replay comparator/artifacts keep exact raw comparison
  values and do not reintroduce `normalized_*` fields or tolerance-based
  equality.
- [ ] Add a test that full-stage trace schema contains all required stages.
- [ ] Add a test that every final field has source provenance and a last
  mutating stage.
- [x] Add a test that every mismatch receives a root-cause bucket before being
  marked resolved.
  - Mismatch artifacts now distinguish `unresolved_placeholder` from
    `confirmed_first_bad_stage`; placeholders cannot be confused with resolved
    root-cause evidence.
- [x] Add a test that no replay report is accepted on checksum alone.

## Visualization TODO

- [x] Design the trace file so it can be loaded by a local debug page without
  parsing Flutter logs.
- [ ] Add a row timeline view:
  - [ ] OCR element row
  - [ ] classified row
  - [ ] merged row
  - [ ] cell row
  - [ ] numeric row
  - [ ] parsed item
  - [ ] post-processed item
  - [ ] ground-truth comparison
- [x] Add field-level diff view for one item number.
- [ ] Add column heatmap/counts for mismatches by root-cause bucket.
- [ ] Add a source-provenance view for a final field showing exactly which OCR
  tokens created it.
- [x] Add a compact run dashboard:
  - [x] PDF
  - [ ] row count
  - [ ] item count
  - [ ] checksum match
  - [x] mismatch count
  - [x] root-cause bucket counts
  - [ ] artifact links

## Immediate Execution Queue

- [x] Stop adding Berrien text/unit production rules until trace coverage is
  improved.
- [x] Implement full mismatch JSON/CSV artifacts first.
- [x] Add root-cause bucket placeholders to mismatch entries.
- [x] Add Berrien focus specs for representative failures:
  - [x] item 16 unit `SFFF` vs `FT`
  - [x] item 17 missing `FT`
  - [x] item 27 missing `, LM` description suffix with raw unit `, LM CYD`
  - [x] item 30 leading item-fragment pollution `(3 ) Erosion Control`
  - [x] item 33 unit `(YƆ` vs `CYD`
  - [x] item 41 leading `< 1` item-fragment pollution and `(YƆ` unit
  - [x] item 100 leading `00` description pollution
  - [x] item 113 duplicate/leading `13 HMA` issue
  - [x] item 178/179 expected repeated `Conc Barrier` phrase mismatch
  - [x] item 197 expected repeated `Stop Bar` phrase mismatch
- [x] Rerun the four-PDF replay and inspect the new artifacts before the next
  production rule.
- [x] Update this spec after each replay with:
  - [x] run path
  - [x] mismatch deltas
  - [x] root-cause bucket deltas
  - [x] rule/fixture decisions
  - [x] rejected approaches

## Implementation Notes 2026-04-14

- Latest artifact run:
  `.tmp/google_ocr_research/codex_downstream_replay_20260414_stage_trace_artifacts_03`.
- Replay state after diagnostic implementation:
  - Berrien: `200/200`, checksum exact, 61 asserted row/column mismatches.
  - Grand Blanc: 0 asserted mismatches.
  - Huron Valley: 0 asserted mismatches.
  - Springfield: 0 asserted mismatches.
- Confidence fixture values are captured but marked `observed_not_asserted`.
  Reason: current fixture confidence values are placeholder extraction metadata,
  not visually derivable PDF ground truth. `fields_present` remains asserted.
- Berrien current root-cause placeholder counts:
  - `field_confidence_error`: 5
  - `ocr_source_error`: 11
  - `cell_assignment_error`: 5
  - `post_normalization_error`: 12
  - `row_parsing_error`: 28
- Added static local viewer:
  `tools/gocr_trace_viewer.html`.
- Added production guardrail lint:
  `no_pdf_specific_gocr_extraction_branching`.
- Rejected approach: treating placeholder `confidence: 0.95` fixture values as
  asserted PDF ground truth. It created false failures on all three already
  clean PDFs and would optimize the pipeline toward fixture metadata rather
  than visible PDF content.

## Exact Comparator Correction 2026-04-14

- Rejected approach: any ground-truth comparison normalization in the replay
  harness. Normalizing punctuation, spacing, case, or numeric deltas inside the
  comparator hides the upstream stage that mutated the data and defeats the
  purpose of the stage trace.
- Updated comparator direction:
  - [x] Text fields compare exact string output.
  - [x] Numeric fields compare exact numeric output.
  - [x] Checksum comparison uses exact numeric equality.
  - [x] Mismatch artifacts emit `expected_comparison_value`,
    `actual_comparison_value`, and `comparison_mode: exact`.
  - [x] Stage mutation history uses exact value equality when deciding whether
    a value changed between stages.
- Exact replay result after removing comparison normalization:
  - Run path:
    `.tmp/google_ocr_research/codex_downstream_replay_20260414_exact_raw_schema_01`.
  - Berrien: 201 mismatches.
  - Grand Blanc: 89 mismatches.
  - Huron Valley: 112 mismatches.
  - Springfield: 103 mismatches.
- Corrected status: Grand Blanc, Huron Valley, and Springfield are not
  character-for-character locked down yet. They were only clean under the
  rejected normalized comparator.

## Spec Re-Audit 2026-04-14

Latest verification run:
`.tmp/google_ocr_research/codex_downstream_replay_20260414_spec_audit_01`.

Verified as implemented:

- [x] Exact comparator direction is implemented and covered by
  `gocr_ground_truth_fixture_contract_test.dart`.
  - Text compares exact string output.
  - Numeric fields compare exact numeric output.
  - Checksum comparison uses exact numeric equality.
  - Mismatch artifacts use `expected_comparison_value`,
    `actual_comparison_value`, and `comparison_mode: exact`.
  - Generated mismatch artifacts do not contain `normalized_expected_value` or
    `normalized_actual_value`.
- [x] Full comparison rows are emitted for every baseline expected row and all
  eight compared fields.
  - Berrien: `1600` comparison rows.
  - Grand Blanc: `944` comparison rows.
  - Huron Valley: `1120` comparison rows.
  - Springfield: `1048` comparison rows.
- [x] Full mismatch JSON/CSV artifacts are emitted and test failures point to
  artifact paths instead of relying on truncated console output.
- [x] Pay-item trace artifacts include all current required stage IDs in
  `_requiredTraceStages`.
- [x] Every final field currently has a mutation history array and a
  `last_mutating_stage` value.
- [x] Every current mismatch has a root-cause bucket field.
- [x] `no_pdf_specific_gocr_extraction_branching` is registered and its package
  test passes when run from `fg_lint_packages/field_guide_lints`.
- [x] Stage-trace collector, live diagnostic sink, and basic pipeline trace
  contract tests pass.

Verified gaps against the original intent:

- [ ] The trace model still records stage `output` plus count metadata, not a
  first-class stage `input` snapshot. This means the endpoint does not yet show
  complete before/after payloads for every stage boundary.
- [ ] Normalized GOCR replay `text_recognition` currently emits cache counts
  only. The full OCR element list first appears at `element_validation`, so the
  earliest OCR-cache input boundary is not yet trace-complete.
- [ ] Final-field mutation history is reconstructed from stage snapshots.
  Current `rule_name`/`reason_code` values are mostly generic
  `stage_snapshot_observation` entries, so the trace shows where values changed
  but not the exact production rule that changed them.
- [ ] Stage-local post-processing snapshots expose cumulative repair counts but
  not stage-local repair/mutation records. The final `post_processing` stage
  has `repair_log`, but the mutation timeline is not yet joined to the exact
  repair entry per field.
- [ ] Repair entries themselves need stronger structured fields. Current
  entries have `type`, `before`, `after`, and free-text `reason`, but no stable
  `rule_name`, `reason_code`, `stage_id`, `field`, or mutation kind.
- [ ] Source provenance is partial. Current run has token provenance gaps:
  - Berrien: `562` final fields have partial provenance.
  - Grand Blanc: `356` final fields have partial provenance.
  - Huron Valley: `352` final fields have partial provenance.
  - Springfield: `274` final fields have partial provenance.
  Confidence and `fields_present` are derived fields and need explicit derived
  provenance. Some value fields also lose physical row identity because
  `CellGridRow` does not carry the original physical row index.
- [ ] Root-cause buckets are still initial placeholders. They are useful for
  sorting failures, but they are not confirmed evidence buckets until trace
  provenance identifies the first stage where each mismatch appears.
- [ ] Ground-truth review ledgers now contain item-by-item fixture rows, but
  they are still not visually verified against the PDFs. Each row still needs a
  page/source note, reviewer/date, and correction note when applicable.
- [ ] `confidence` is present in comparison rows but remains
  `observed_not_asserted`. If confidence is part of the 100% acceptance gate,
  the fixture must define an auditable expected-confidence source or the
  pipeline must compare it against a deterministic derived-confidence contract.
- [ ] The local trace viewer can inspect field diffs, but it does not yet show
  the full row timeline, column heatmap, or source-token provenance view called
  for by this spec.

Latest exact replay result:

- Berrien: `201` exact row/column mismatches.
- Grand Blanc: `89` exact row/column mismatches.
- Huron Valley: `112` exact row/column mismatches.
- Springfield: `103` exact row/column mismatches.

Trace mutation implementation run:
`.tmp/google_ocr_research/codex_downstream_replay_20260414_stage_boundaries_02`.

- Berrien: `3220/3220` OCR input elements emitted; `44`
  post-normalize stage mutations; `85` final-field mutation-history entries
  joined to repair IDs.
- Grand Blanc: `1778/1778` OCR input elements emitted; `9`
  post-normalize stage mutations; `11` final-field mutation-history entries
  joined to repair IDs.
- Huron Valley: `2066/2066` OCR input elements emitted; `8`
  post-normalize stage mutations; `8` final-field mutation-history entries
  joined to repair IDs.
- Springfield: `2046/2046` OCR input elements emitted; `51`
  post-normalize stage mutations; `55` final-field mutation-history entries
  joined to repair IDs.
- Exact mismatch counts did not change in this trace-only pass, as expected:
  Berrien `201`, Grand Blanc `89`, Huron Valley `112`, Springfield `103`.

Stage-boundary and physical-provenance implementation run:
`.tmp/google_ocr_research/codex_downstream_replay_20260414_stage_boundaries_02`.

- Exact mismatch counts remain unchanged:
  - Berrien: `201`.
  - Grand Blanc: `89`.
  - Huron Valley: `112`.
  - Springfield: `103`.
- Each baseline trace now has `59` `stage_boundaries` entries.
- Each baseline trace has `59/59` boundary output snapshots and `58/59`
  boundary input snapshots. The one missing input is the initial stage boundary,
  which declares `input_status: initial_boundary_no_input`.
- Final-field provenance now separates derived fields from OCR-backed fields:
  - Berrien: `1038` OCR-token fields, `400` derived fields, `162` partial
    final-row fields.
  - Grand Blanc: `588` OCR-token fields, `236` derived fields, `120` partial
    final-row fields.
  - Huron Valley: `768` OCR-token fields, `280` derived fields, `72` partial
    final-row fields.
  - Springfield: `774` OCR-token fields, `262` derived fields, `12` partial
    final-row fields.
- Every OCR-token final field now carries physical source-row metadata in
  `source_cells[*].physical_source_rows`.
- The four stage-trace artifacts now have `0` `unknown_row` OCR-token IDs.
- Remaining partial final-row fields are real source-provenance gaps where the
  final field could not yet be matched back to a source cell, not derived-field
  bookkeeping.

Updated priority order:

- [x] Add first-class `input`/`output` stage boundary support to the trace
  schema, starting with replay-only artifacts if production memory overhead
  needs to stay bounded.
- [x] Emit every normalized GOCR cache element at the OCR-cache input boundary,
  before element validation can clamp, reject, or reshape it.
- [x] Add stable mutation records to post-processing substages:
  - [x] `stage_id`
  - [x] `item_id`
  - [x] `field`
  - [x] `input_value`
  - [x] `output_value`
  - [x] `rule_name`
  - [x] `reason_code`
  - [x] `mutation_kind`
  - [x] source repair entry ID
- [x] Join final-field mutation history to those mutation records instead of
  relying on snapshot diff placeholders.
- [x] Preserve physical row identity through cell extraction so final field
  provenance can point to page, physical row, base/continuation status, cell,
  and OCR token IDs.
- [ ] Add trace-schema tests that fail when required stages omit required
  row/cell/value/mutation fields.
- [ ] Add lint/test guardrails for stable post-processing rule names and
  reason codes.
- [ ] Complete visual PDF review ledgers before treating any fixture as locked.

## Still-Incomplete Implementation Checklist 2026-04-14

These are the concrete gaps that are still costing iteration time. Do not mark
this section complete unless the artifact proves the input, output, mutation,
rule/reason, and provenance are present without reading Flutter/S21 console
logs.

- [ ] Stage boundary visibility
  - [x] Every stage artifact records the stage input payload or an explicit
    bounded input snapshot.
    - Latest artifact has `58/59` stage-boundary input snapshots per baseline;
      the initial boundary explicitly records `initial_boundary_no_input`.
  - [x] Every stage artifact records the stage output payload.
  - [x] Every stage artifact records row/cell/value counts for input and
    output.
  - [ ] Every stage artifact records dropped, orphaned, moved, synthesized, and
    copied-forward values where applicable.
- [ ] OCR-cache input visibility
  - [x] The normalized GOCR replay `text_recognition` trace emits every cached
    OCR element before validation.
  - [x] Each OCR input element has a stable ID, text, confidence, page index,
    element index, bounding box, and coordinate metadata.
- [ ] Mutation attribution
  - [x] Post-processing substages emit stage-local `stage_repair_log` entries.
  - [x] Post-processing substages emit field-level `stage_mutations`.
  - [x] Each mutation has `stage_id`, `item_id`, `field`, `input_value`,
    `output_value`, `rule_name`, `reason_code`, `mutation_kind`, and
    `repair_id`.
  - [x] Final-field `mutation_history` joins to exact stage-local mutation
    records instead of generic snapshot observations wherever a repair record
    exists.
- [ ] Source provenance
  - [x] Cell extraction preserves physical row identity in `CellGridRow`.
  - [x] Final field provenance includes page, physical row, base vs
    continuation status, cell index, OCR token IDs, and OCR token snapshots.
    - Remaining partial provenance entries are source-cell matching gaps, not
      missing row metadata for matched OCR-token fields.
  - [x] Derived fields such as `confidence` and `fields_present` have explicit
    derived-value provenance, not fake OCR-token provenance.
- [ ] Root-cause classification
  - [ ] Root-cause buckets are confirmed from the first stage where the mismatch
    appears.
  - [ ] Placeholder root-cause buckets are not treated as resolved evidence.
- [ ] Ground truth ledgers
  - [x] Berrien has an item-by-item visual PDF verification ledger.
    - Ledger rows created: `200`.
  - [x] Grand Blanc has an item-by-item visual PDF verification ledger.
    - Ledger rows created: `118`.
  - [x] Huron Valley has an item-by-item visual PDF verification ledger.
    - Ledger rows created: `140`.
  - [x] Springfield has an item-by-item visual PDF verification ledger.
    - Ledger rows created: `131`; item 99 remains `HMA, 5EML`.
  - [x] Each ledger row records item number, description, unit, quantity, unit
    price, bid amount, visual PDF page/source note, reviewer/date, and
    correction note.
  - [ ] Every ledger row has been visually verified against the rendered PDF.
- [ ] Guardrails
  - [ ] Trace-schema tests fail if required stage payload fields are absent.
  - [x] Repair-log tests fail if rule names or reason codes are generic/free
    text only.
  - [ ] Fixture-edit tests fail if ground-truth rows change without ledger
    updates.
- [ ] Visualization
  - [ ] Row timeline view covers OCR input, validation, grouping,
    classification, merging, cell extraction, numeric interpretation, parsing,
    post-processing, and final comparison.
  - [x] Field source view shows the exact OCR tokens and mutation records that
    produced the final value.
    - `tools/gocr_trace_viewer.html` now renders source cells, physical source
      rows, OCR tokens, and mutation history for the selected field.
  - [ ] Mismatch dashboard groups by confirmed root-cause bucket and stage.
  - [x] Viewer can start from the run manifest or the singular
    `/diagnostics/gocr-trace` endpoint and branch to document artifacts without
    needing separate debug endpoints.

## Final Four Debuggability Checklist 2026-04-14

The remaining work should reduce the number of places we need to look while
preserving the exact, non-normalized comparison contract.

- [x] Singular trace endpoint/index
  - [x] Write one run-level manifest that indexes every trace, summary, and
    mismatch artifact for the run.
    - `gocr-trace-manifest.json` is written at the run root.
  - [x] Add one driver/debug diagnostics route that can list runs and return
    a selected trace artifact using the same schema as replay files.
    - `GET /diagnostics/gocr-trace` lists runs.
    - `GET /diagnostics/gocr-trace?run=<run_id>` returns the run manifest.
    - `GET /diagnostics/gocr-trace?run=<run_id>&document=<document_key>&artifact=trace`
      returns a selected artifact. Other artifact branches: `summary`,
      `mismatches`, `mismatches_csv`.
  - [x] Keep per-document JSON/CSV files as branch artifacts, not separate
    competing endpoints.
- [x] Root-cause confirmation
  - [x] Add artifact fields that distinguish `initial_placeholder` from
    `confirmed_first_bad_stage`.
  - [x] Add a workflow/test gate so a mismatch cannot be marked resolved while
    still using a placeholder root-cause bucket.
    - Current artifacts explicitly report `root_cause_resolution_status:
      unresolved_placeholder` for placeholder buckets.
- [x] Remaining source-provenance gaps
  - [x] Make partial final-row provenance countable by document/field.
  - [x] Add a focused artifact section that lists every final field without
    source-cell provenance so those gaps can be attacked directly.
    - Trace artifacts now emit `source_provenance_gaps` and
      `source_provenance_gap_counts`.
- [x] Ground-truth visual verification gate
  - [x] Add a fixture-review sidecar/contract so edited fixture rows require
    ledger evidence.
  - [x] Keep all unreviewed ledgers visibly marked `needs_visual_pdf_review`
    until every row has a PDF page/source note and reviewer/date.

## Acceptance Gate

- [ ] All four PDFs have visually verified ground-truth fixtures.
- [ ] All four PDFs pass row count, item-number, checksum, and every field
  comparison.
- [ ] Every stage emits structured trace data for every row/cell/value.
- [ ] Every final field can be traced back to source OCR elements.
- [ ] Every value mutation has a stage, rule/reason, and before/after value.
- [x] Replay failures point to complete JSON/CSV artifacts instead of relying
  on truncated console logs.
- [ ] Guardrail tests/lints prevent PDF-specific production rules and
  unreviewed fixture drift.

## Spec Intent Audit 2026-04-14

Conclusion: the implementation has captured the core debugging direction, but
the full spec intent is not complete yet. We now have enough centralized
artifact plumbing to stop relying on S21/Flutter console logs, but we do not
yet have complete evidence for every row, cell, value, mutation, and confirmed
first-bad stage.

Verified against latest trace run:
`.tmp/google_ocr_research/codex_downstream_replay_20260414_debug_endpoint_01`.

- [x] Single endpoint/index intent is captured.
  - One run manifest is written at `gocr-trace-manifest.json`.
  - `GET /diagnostics/gocr-trace` lists runs.
  - `GET /diagnostics/gocr-trace?run=<run_id>` returns the manifest.
  - `GET /diagnostics/gocr-trace?run=<run_id>&document=<document_key>&artifact=<trace|summary|mismatches|mismatches_csv>`
    returns branch artifacts from the manifest.
- [x] Exact, non-normalizing comparator intent is captured.
  - Artifacts emit `comparison_mode: exact`.
  - Mismatch JSON/CSV carry raw expected and actual comparison values.
  - Current focused tests reject `normalized_expected_value`,
    `normalized_actual_value`, and tolerance-based equality.
- [x] Full mismatch-artifact intent is captured.
  - Four failing baseline pay-item PDFs now point to complete JSON/CSV mismatch
    artifacts rather than truncated console output.
- [x] Baseline fixture shape intent is partially captured.
  - All four fixture files contain the required row fields and expected item
    counts.
  - All four fixtures are explicitly marked `needs_visual_pdf_review`.
- [x] Stage trace plumbing is partially captured.
  - Baseline pay-item traces contain all required stage IDs.
  - Each pay-item trace has `59` stage boundaries.
  - Each boundary has an output snapshot; all non-initial boundaries have an
    input snapshot.
  - OCR cache input is visible at `text_recognition` before validation:
    Berrien `3220`, Grand Blanc `1778`, Huron Valley `2066`, Springfield
    `2046` OCR elements.
- [ ] Stage coverage intent is not fully captured.
  - Several stage outputs are still diagnostic summaries rather than every
    per-row/per-cell/per-value decision required by the Stage Coverage TODO.
  - `element_validation` still reports aggregate page metadata rather than
    every input/output element ID and clamping/rejection decision.
  - Some stage-local decision payloads are present, but there is not yet a
    schema test proving each required stage emits all required row/cell/value
    fields.
- [ ] Mutation attribution intent is not fully captured.
  - Post-processing substages emit `stage_repair_log` and `stage_mutations`.
  - Final-field histories join to exact repair IDs where repair records exist.
  - Latest artifact still has many generic timeline observations because most
    copied-forward or non-repair changes are reconstructed from snapshots:
    Berrien `11115`, Grand Blanc `6581`, Huron Valley `7832`, Springfield
    `7281` generic observation entries.
  - Remaining work: distinguish acceptable copied-forward observations from
    un-attributed actual mutations, and fail when a changed value lacks a
    stable stage-local rule/reason.
- [ ] Source provenance intent is not fully captured.
  - Matched OCR-backed fields carry page, physical row, base/continuation
    status, cell index, OCR token IDs, and OCR token snapshots.
  - Derived fields have explicit derived provenance instead of fake OCR
    provenance.
  - Remaining source-cell provenance gaps are still present:
    Berrien `162`, Grand Blanc `120`, Huron Valley `72`, Springfield `12`.
- [ ] Root-cause intent is not fully captured.
  - Mismatch artifacts distinguish `unresolved_placeholder` from
    `confirmed_first_bad_stage`.
  - All current baseline mismatches remain unresolved placeholders:
    Berrien `201/201`, Grand Blanc `89/89`, Huron Valley `112/112`,
    Springfield `103/103`.
  - Root-cause buckets are useful sorting labels only until the first bad stage
    is proven from the trace.
- [ ] Ground-truth verification intent is not fully captured.
  - Item-by-item review ledgers exist for all four PDFs.
  - Review sidecar says `reviewed_item_count: 0` for every baseline.
  - Every ledger row still needs actual visual PDF verification evidence before
    fixtures can be treated as locked.
- [ ] Guardrail intent is only partially captured.
  - `no_pdf_specific_gocr_extraction_branching` is registered and blocks
    obvious conditional branching on baseline document names, fixture keys, and
    related metadata in production extraction code.
  - `no_generic_gocr_repair_trace_codes` is registered for production stage
    code.
  - Current contract tests still rely heavily on source-string checks. We still
    need artifact-shape tests that load emitted traces and fail when required
    stage payloads, final-field provenance, mutation attribution, or fixture
    review gates are absent.
- [ ] Visualization intent is not fully captured.
  - The viewer can start from a manifest or `/diagnostics/gocr-trace` and
    branch to trace, summary, mismatch JSON, and mismatch CSV artifacts.
  - Field source view exists.
  - Full row timeline and root-cause/stage dashboard remain open.

Next required implementation queue:

- [ ] Add artifact-shape tests that load a generated trace fixture and assert
  required payload fields for every required stage, not just source-code
  substrings.
- [ ] Add a mutation-attribution gate: every changed value must have a stable
  `rule_name`, `reason_code`, mutation kind, and before/after value, while
  copied-forward unchanged values may remain explicitly marked as such.
- [ ] Close source-cell provenance gaps so every OCR-backed final field traces
  to source OCR tokens, or emits a precise stage-local explanation for why it
  cannot.
- [ ] Implement confirmed first-bad-stage classification from the stage
  timeline before treating any root-cause bucket as resolved.
- [ ] Complete row-by-row visual PDF review ledgers and update
  `reviewed_item_count` only from visual PDF evidence or explicit user
  confirmation.
- [ ] Expand the trace viewer with row timeline and root-cause/stage dashboard
  views so the single endpoint is enough for normal debugging.
- [ ] After those gates are real, resume algorithmic extraction fixes across
  all four PDFs in one replay until exact mismatches reach zero.

## Root-Cause Trace Contract Update 2026-04-14

Latest root-cause replay:
`.tmp/google_ocr_research/codex_downstream_replay_20260414_root_cause_02`.

- [x] Asserted mismatch rows can no longer pass the trace contract as
  unresolved placeholders.
  - `gocr_trace_artifact_contract_test.dart` now rejects asserted mismatch rows
    unless they carry `root_cause_bucket_status: confirmed`,
    `root_cause_resolution_status: confirmed_first_bad_stage`,
    `first_bad_stage`, `first_bad_stage_scope`, and
    `first_bad_stage_evidence`.
- [x] All four pay-item trace artifacts pass the stricter contract:
  - Berrien: `unresolved_mismatch_count: 0`.
  - Grand Blanc: `unresolved_mismatch_count: 0`.
  - Huron Valley: `unresolved_mismatch_count: 0`.
  - Springfield: `unresolved_mismatch_count: 0`.
- [x] First-bad-stage attribution now uses general evidence only:
  - final field stage timeline;
  - exact raw/final expected-vs-actual values;
  - source provenance status;
  - OCR glyph evidence such as non-ASCII source text;
  - field type and stable stage IDs.
- [x] The root-cause classifier does not branch on PDF names, contractor names,
  fixture paths, or item numbers.

Current exact mismatch/root-cause clusters:

- Berrien: `201` mismatches.
  - `post_normalization_error`: `146`.
  - `row_parsing_error`: `35`.
  - `ocr_source_error`: `12`.
  - `field_confidence_error`: `5`.
  - `cell_assignment_error`: `3`.
- Grand Blanc: `89` mismatches.
  - `post_normalization_error`: `65`.
  - `row_parsing_error`: `20`.
  - `ocr_source_error`: `4`.
- Huron Valley: `112` mismatches.
  - `post_normalization_error`: `85`.
  - `row_parsing_error`: `18`.
  - `ocr_source_error`: `9`.
- Springfield: `103` mismatches.
  - `post_normalization_error`: `77`.
  - `row_parsing_error`: `17`.
  - `ocr_source_error`: `9`.

Next algorithmic implementation queue from confirmed clusters:

- [ ] Add a general post-normalization description rule for OCR punctuation
  spacing around commas, periods, semicolons, colons, percent signs,
  parentheses, quotes, and hyphens.
- [ ] Preserve exact fixture comparison. The rule must change production output
  in a named post-normalization stage and emit stable mutation records; the
  comparator must remain exact and non-normalizing.
- [ ] Add focused tests for the punctuation-spacing normalization rule using
  representative generic OCR strings, not document-specific item numbers.
- [ ] Rerun all four baseline PDFs together after the rule.
- [ ] Then attack remaining `row_parsing_error`, `ocr_source_error`, and
  `cell_assignment_error` buckets from the new artifacts.

## Exact Replay Update 2026-04-14 Punctuation 08

Latest replay:
`.tmp/google_ocr_research/codex_downstream_replay_20260414_punctuation_08`.

- [x] Berrien County is exact against the current visually corrected fixture:
  `0` row/column mismatches, `200` items, checksum `$7,467,543.00`.
- [x] Grand Blanc remains exact: `0` row/column mismatches, `118` items,
  checksum `$7,918,199.14`.
- [x] Huron Valley remains exact: `0` row/column mismatches, `140` items,
  checksum `$10,531,942.76`.
- [ ] Springfield still has `3` exact mismatches:
  - item `63` description: fixture `Bend, 45°, 12"` vs output
    `Bend, 45°, 12", N`; raw unit is `N EA`.
  - item `64` description: fixture `Bend, 22.5°, 12"` vs output
    `Bend, 22.5°, 12", N`; raw unit is `N EA`.
  - item `106` unit: fixture `Ft` vs output `FT`; raw unit is `Ft`.
- [ ] Springfield blocker: there is currently no Springfield rendered PDF page
  image or source PDF in the workspace, and web search did not find a usable
  visual source. Do not edit the Springfield fixture for these rows until the
  PDF image is available or the user explicitly confirms the exact visual
  values.

Algorithmic/generalistic production changes added in this pass:

- [x] Row merging now reserves a description continuation for the following
  numeric anchor when the previous item is complete and the next item has the
  next local sequence number but no description signal. This is based on row
  type, local sequence, structured payload, and description presence only.
- [x] Post-normalization removes OCR bullet/current-item fragments from leading
  descriptions such as `· 16 Cofferdams`.
- [x] Unit-prefix restoration appends `foot`/`feet` to numeric descriptors with
  a space instead of a comma.
- [x] Sequence description correction canonicalizes interleaved contaminated
  material disposal phrases where the current item number was absorbed into the
  description.
- [x] Sequence description correction reorders split `Barricade ... Lighted`
  descriptions from numeric-anchor row splits.
- [x] Sequence description correction reassigns a split pavement-marking drum
  continuation from the following row back to the preceding complete row.

Visual fixture corrections made from rendered Berrien PDF pages:

- [x] Page 5: items `113`, `114`, `116`, `117`.
- [x] Page 6: items `137`, `138`.
- [x] Page 7: items `156`, `157`, `171`, `172`, `173`, `174`, `175`, `178`,
  `179`.
- [x] Page 8: items `196`, `197`.
- [ ] Berrien review sidecar now records `17` visually reviewed rows. The full
  Berrien ledger is still not complete; only those rows are visually locked.

Verification run after this pass:

- [x] `flutter test test/features/pdf/extraction/stages/row_merger_test.dart test/features/pdf/extraction/stages/post_processing/artifact_cleaning_rules_test.dart test/features/pdf/extraction/stages/post_processing/repair_log_test.dart test/features/pdf/extraction/integration/gocr_ground_truth_fixture_contract_test.dart -d windows`
- [ ] Four-PDF replay still fails only because of Springfield's `3` unverified
  exact mismatches listed above.

Updated continuation queue:

- [ ] Obtain/render the Springfield source PDF pages containing items `63`,
  `64`, and `106`, then correct fixture or production behavior from visual
  evidence.
- [ ] Complete visual PDF review for every row in all four ledgers before
  marking any baseline fixture `locked`.
- [ ] Keep all future extraction rules corpus-stable: no fixture path,
  document key, contractor name, or item-number-specific branches.
- [ ] Continue reducing trace/schema gaps from the acceptance gate: required
  per-stage payload tests, complete row timeline viewer, and root-cause/stage
  dashboard.

## MDOT Ground Truth Expansion TODO 2026-04-14

Goal: bring the MDOT public PDF corpus up to the same exact-comparison,
stage-traced, visually verified standard as the four baseline pay-item PDFs.
The output of this work is not another weak row-count/checksum gate. Each MDOT
ground truth must become an item-by-item, column-by-column visual ledger that
can drive the same exact comparator and trace artifacts already used for the
baseline GOCR replay.

Current MDOT corpus inventory:

- [x] Source PDFs exist locally under
  `.tmp/public_mdot_pdf_corpus/bid_item_stress/`.
- [x] Public corpus manifest exists:
  `test/features/pdf/extraction/fixtures/mdot_public_pdf_corpus_manifest.json`.
- [x] Pre-release corpus manifest already references the MDOT documents:
  `test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_manifest.json`.
- [x] Pre-release expected metadata already has weak MDOT row-count/pattern
  gates in
  `test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`.
- [x] MDOT pay-item ground-truth item JSON drafts now exist for every MDOT
  pay-item PDF.
- [x] MDOT item-by-item visual review ledgers now exist for every MDOT
  pay-item PDF.
- [x] MDOT expected metadata now includes `ground_truth_items_path`; any MDOT
  Google OCR cache file added to the no-render replay directory will run
  through the same exact comparator and mismatch artifacts as the four
  baseline PDFs.

MDOT documents to bring up to standard:

- [x] `mdot_2026_04_03_estqua:pay_items`
  - Source: `mdot_2026-04-03_estqua_schedule_of_items_sample_pages_001_025.pdf`
    in the pre-release manifest.
  - Full source also exists as `mdot_2026-04-03_estqua_schedule_of_items.pdf`.
  - Source-derived gate: `677` rows, item numbers matching `^\d{4}$`,
    `198` unique item numbers.
- [x] `mdot_2026_03_06_estqua:pay_items`
  - Source: `mdot_2026-03-06_estqua_schedule_of_items_sample_pages_001_025.pdf`.
  - Full source also exists as `mdot_2026-03-06_estqua_schedule_of_items.pdf`.
  - Source-derived gate: `685` rows, item numbers matching `^\d{4}$`,
    `112` unique item numbers.
- [x] `mdot_2025_12_05_estqua:pay_items`
  - Source: `mdot_2025-12-05_estqua_schedule_of_items_sample_pages_001_025.pdf`.
  - Full source also exists as `mdot_2025-12-05_estqua_schedule_of_items.pdf`.
  - Source-derived gate: `904` rows, item numbers matching `^\d{4}$`,
    `270` unique item numbers.
- [x] `mdot_2025_11_07_estqua:pay_items`
  - Source: `mdot_2025-11-07_estqua_schedule_of_items_sample_pages_001_025.pdf`.
  - Full source also exists as `mdot_2025-11-07_estqua_schedule_of_items.pdf`.
  - Source-derived gate: `831` rows, item numbers matching `^\d{4}$`,
    `222` unique item numbers.
- [x] `mdot_2026_04_03_26_04001_bid_tab:pay_items`
  - Source: `mdot_2026-04-03_26-04001_bid_tab_by_item.pdf`.
  - Current weak gate: `18` rows, item numbers `0005` through `0090`.
- [x] `mdot_2026_04_03_26_04003_bid_tab:pay_items`
  - Source: `mdot_2026-04-03_26-04003_bid_tab_by_item.pdf`.
  - Current weak gate: `23` rows, item numbers `0005` through `0115`.
- [x] `mdot_2026_03_06_26_03001_bid_tab:pay_items`
  - Source: `mdot_2026-03-06_26-03001_bid_tab_by_item.pdf`.
  - Current weak gate: `78` rows, item numbers `0005` through `0390`.
- [x] `mdot_2026_03_06_26_03002_bid_tab:pay_items`
  - Source: `mdot_2026-03-06_26-03002_bid_tab_by_item.pdf`.
  - Current weak gate: `112` rows, item numbers `0005` through `0560`.
- [x] MDOT generated measurement-payment companion PDFs:
  - The corpus also has generated `*_generated_mp_companion.pdf` files for
    each MDOT document.
  - Exact draft fixtures now use `ground_truth_entries_path` with item number,
    title, body, line item number, source item ID, unit, confidence, source
    PDF/page/y, source type, and visual-review status.
  - The pre-release corpus harness now exact-compares M&P title/body when a
    `ground_truth_entries_path` is present.

Ground-truth fixture creation:

- [x] Create one exhaustive pay-item JSON fixture for every MDOT pay-item PDF:
  - `test/features/pdf/extraction/fixtures/mdot_2026_04_03_estqua_ground_truth_items.json`
  - `test/features/pdf/extraction/fixtures/mdot_2026_03_06_estqua_ground_truth_items.json`
  - `test/features/pdf/extraction/fixtures/mdot_2025_12_05_estqua_ground_truth_items.json`
  - `test/features/pdf/extraction/fixtures/mdot_2025_11_07_estqua_ground_truth_items.json`
  - `test/features/pdf/extraction/fixtures/mdot_2026_04_03_26_04001_bid_tab_ground_truth_items.json`
  - `test/features/pdf/extraction/fixtures/mdot_2026_04_03_26_04003_bid_tab_ground_truth_items.json`
  - `test/features/pdf/extraction/fixtures/mdot_2026_03_06_26_03001_bid_tab_ground_truth_items.json`
  - `test/features/pdf/extraction/fixtures/mdot_2026_03_06_26_03002_bid_tab_ground_truth_items.json`
- [x] Each MDOT fixture row must include every compared field, with no
  derived omissions:
  - item number;
  - description;
  - unit;
  - quantity;
  - unit price, when present on the PDF type;
  - bid amount, when present on the PDF type;
  - bidder/vendor price columns for bid-tab PDFs, if those columns are part of
    the extraction contract;
  - explicit blank/missing fields when the visual PDF has no value.
- [x] Current pipeline output is not used as ground truth. Draft values come
  from the source PDF native text layer and are marked
  `needs_visual_pdf_review`.
- [x] Preserve exact visible text in fixtures. Do not trim, case-fold,
  canonicalize, round, normalize punctuation, or rewrite units inside the
  comparator or the fixture-creation process.
- [x] If a value is intentionally synthesized or inferred by production code,
  fixture and trace must record that as synthesized/inferred provenance rather
  than pretending it is OCR-token-backed.

Visual PDF review ledgers:

- [x] Render every MDOT pay-item source PDF page used by the corpus into a
  deterministic review directory, for example:
  `.tmp/google_ocr_research/ground_truth_review/mdot_pages/<document-id>/page-N.png`.
- [x] Create one review ledger per MDOT pay-item PDF under
  `.tmp/google_ocr_research/ground_truth_review/`.
- [x] Every ledger row must record:
  - document key;
  - source PDF path;
  - visual page number;
  - visual row or table position;
  - item number;
  - every compared cell value;
  - review status;
  - reviewer/date;
  - correction notes when the draft fixture differed from the PDF.
- [x] Keep `reviewed_item_count` accurate. It may increase only from visual PDF
  evidence or explicit user confirmation.
- [x] Add MDOT fixture entries to
  `test/features/pdf/extraction/fixtures/gocr_ground_truth_review_status.json`
  with `needs_visual_pdf_review` until every row and every compared cell is
  visually checked.

Expected metadata and exact replay integration:

- [x] Add `ground_truth_items_path` for each MDOT pay-item expected entry in
  `pre_release_pdf_corpus_expected.json` only after the corresponding fixture
  file exists.
- [x] Add `ground_truth_verification_status:
  needs_visual_review_ledger` for each MDOT pay-item expected entry until the
  ledger is complete.
- [x] Extend the GOCR downstream replay document selection so MDOT fixtures can
  run through the same exact comparison path as Berrien, Grand Blanc, Huron
  Valley, and Springfield.
- [x] Ensure the exact comparator remains exact for MDOT:
  - no normalization;
  - no tolerance;
  - no case folding;
  - no hidden unit conversion;
  - no punctuation cleanup inside comparison.
- [x] Emit MDOT mismatch JSON and CSV artifacts with the same fields as the
  baseline replay:
  - raw expected;
  - raw actual;
  - field name;
  - row identity;
  - first bad stage;
  - root-cause bucket and status;
  - final-field source provenance;
  - stage timeline evidence.
- [x] Include every MDOT run in the `/diagnostics/gocr-trace` manifest output
  so the existing trace viewer can inspect MDOT rows without a second debug
  endpoint.

Recommended iteration order:

- [x] Start with the small bid-tab PDFs:
  - `mdot_2026_04_03_26_04001_bid_tab` (`18` rows);
  - `mdot_2026_04_03_26_04003_bid_tab` (`23` rows).
- [x] Then add the medium/large bid-tab PDFs:
  - `mdot_2026_03_06_26_03001_bid_tab` (`78` rows);
  - `mdot_2026_03_06_26_03002_bid_tab` (`112` rows).
- [x] Then add the large ESTQ&A schedule samples:
  - `mdot_2026_04_03_estqua` (`676` rows);
  - `mdot_2026_03_06_estqua` (`680` rows);
  - `mdot_2025_11_07_estqua` (`830` rows);
  - `mdot_2025_12_05_estqua` (`900` rows).
- [x] After pay items are stable, define and apply the equivalent exact
  ground-truth standard to the generated measurement-payment companion PDFs.

Algorithmic rule discipline for MDOT work:

- [x] No production rule may branch on MDOT document key, fixture filename,
  letting date, source URL, county/project name, or a specific item number.
- [x] Layout-specific logic is allowed only when driven by general evidence:
  table geometry, repeated header structure, column labels, grid lines,
  item-number pattern, row grouping, OCR token position, or cell payload shape.
- [x] Every new MDOT-motivated production rule must have focused unit coverage
  using generic sample strings/rows and must run the full baseline-plus-MDOT
  replay before being treated as accepted.
- [x] All cleanup/canonicalization belongs in named production stages with
  mutation records. The comparator must never mask MDOT failures.

Acceptance gate:

- [ ] Each MDOT pay-item PDF has a visually verified ground-truth JSON fixture.
- [ ] Each MDOT pay-item PDF has a complete visual review ledger with every
  row and every compared cell accounted for.
- [ ] Existing four baseline PDFs still replay at their current exact status
  while MDOT fixtures are added.
- [ ] Each MDOT pay-item PDF replays with:
  - exact item count;
  - exact item number sequence or exact item-number set;
  - exact description text;
  - exact unit text;
  - exact quantity text/value as represented by the extraction contract;
  - exact unit price and bid amount when present;
  - exact bidder/vendor price cells for bid-tab PDFs when included in the
    extraction contract.
- [ ] Every MDOT mismatch has a first bad stage, root-cause bucket, root-cause
  status, and field-level provenance.
- [ ] Every MDOT final field is classified as OCR-token-backed, explicitly
  blank/missing, or synthesized/inferred.
- [ ] The trace viewer can inspect MDOT mismatch rows from the single manifest
  and endpoint path already used for the baseline corpus.

### MDOT Implementation Update 2026-04-14

Generated by: `python scripts/generate_mdot_ground_truth.py`.

- [x] Added repeatable source-PDF fixture generation tooling:
  `scripts/generate_mdot_ground_truth.py`.
- [x] Rendered every MDOT pay-item source page used by the corpus into:
  `.tmp/google_ocr_research/ground_truth_review/mdot_pages/`.
- [x] Created exhaustive MDOT pay-item fixture drafts:
  - `mdot_2026_04_03_estqua`: `677` rows.
  - `mdot_2026_03_06_estqua`: `685` rows.
  - `mdot_2025_12_05_estqua`: `904` rows.
  - `mdot_2025_11_07_estqua`: `831` rows.
  - `mdot_2026_04_03_26_04001_bid_tab`: `18` rows.
  - `mdot_2026_04_03_26_04003_bid_tab`: `23` rows.
  - `mdot_2026_03_06_26_03001_bid_tab`: `78` rows.
  - `mdot_2026_03_06_26_03002_bid_tab`: `112` rows.
- [x] Corrected the old weak MDOT ESTQ&A expected counts to source-derived
  counts. The previous values were row-count metadata, not locked ground
  truth.
- [x] Created MDOT generated measurement-payment fixture drafts with
  `ground_truth_entries_path`:
  - ESTQ&A companions: `250` entries each.
  - Bid-tab companions: `18`, `23`, `78`, and `112` entries.
- [x] Updated `pre_release_pdf_corpus_expected.json` with MDOT ground-truth
  paths and `needs_visual_review_ledger` statuses.
- [x] Updated `gocr_ground_truth_review_status.json` with MDOT pay-item and
  measurement-payment sidecars. All MDOT `reviewed_item_count` values remain
  `0` because no row has been human-verified against the rendered page image
  yet.
- [x] Added fixture contract coverage proving MDOT pay-item and
  measurement-payment fixtures are exhaustive source-PDF drafts and cannot
  regress to row-count-only metadata.
- [x] Extended the pre-release measurement-payment harness to exact-compare
  title/body fields when `ground_truth_entries_path` exists.
- [x] Verified:
  - `python -m py_compile scripts/generate_mdot_ground_truth.py`
  - `flutter test test/features/pdf/extraction/integration/gocr_ground_truth_fixture_contract_test.dart -d windows`
  - `flutter test test/features/pdf/extraction/integration/pre_release_pdf_corpus_manifest_test.dart test/features/pdf/extraction/integration/mdot_public_pdf_corpus_manifest_test.dart -d windows`
  - `dart analyze integration_test/pre_release_pdf_corpus_test.dart test/features/pdf/extraction/integration/gocr_ground_truth_fixture_contract_test.dart`
- [ ] GOCR exact replay with all MDOT documents is not yet complete. A focused
  04/03 ESTQ&A cache exists and is being used for downstream replay, but the
  full `.tmp/gocr_ocr_cache/` baseline-plus-MDOT set still needs to be rerun
  after the remaining 04/03 row-collapse blockers are fixed.
- [ ] Current baseline replay after MDOT metadata wiring:
  `.tmp/google_ocr_research/codex_mdot_metadata_replay_20260414_01`.
  It included the existing seven cache files only and failed solely on the
  already-known Springfield three-row fixture/source blocker.
- [ ] Remaining hard gate before marking MDOT locked: visually inspect every
  MDOT ledger row against rendered page images and increment
  `reviewed_item_count` only from direct visual evidence or explicit user
  confirmation.

### MDOT Hardening Update 2026-04-14 Late

Current focus: `mdot_2026_04_03_estqua-pay-items`.

- Latest replay:
  `.tmp/google_ocr_research/mdot_2026_04_03_estqua_downstream_replay_after_fragmented_schedule_01`.
- Current exact status:
  - [ ] Expected `677` rows; extracted `675`.
  - [x] Item-number pattern failure from raw `19`/`a` is resolved in the
    latest replay.
  - [ ] Exact row/column mismatch artifact still reports `2068` mismatches.
- General algorithmic changes added:
  - [x] Anchorless unpriced schedule rows can be rescued from boilerplate/data
    deferral when geometry shows description text plus right-side quantity and
    unit-like tokens before the next data row.
  - [x] Row merging now treats unpriced schedule continuations with 5-8 digit
    source IDs as standalone rows instead of swallowing them into the previous
    item.
  - [x] Row parsing now treats unpriced schedule rows with damaged but present
    source-id payloads as schedule rows and can infer a new section reset to
    `0005` after a high local sequence.
- Focused tests passing:
  - [x] `flutter test test/features/pdf/extraction/stages/row_merger_test.dart -d windows`
  - [x] `flutter test test/features/pdf/extraction/stages/row_rescue_adjustment_stage_test.dart -d windows`
  - [x] `flutter test test/features/pdf/extraction/stages/row_parser_stage_test.dart -d windows`
- Remaining root-cause TODO:
  - [ ] The row containing `Traf Regulator Control` is still collapsed into
    the preceding sign row; continue upstream at row merging/cell extraction
    using the fragmented source-id evidence, not a document-specific rule.
  - [ ] The row containing `Maintenance Gravel` is still collapsed into
    `_ Project Cleanup, Modified`; continue at post-splitting/row-splitting
    for merged unpriced quantity schedule rows.
  - [ ] After those two row-count losses are fixed, rerun the single 04/03
    replay and then the full original-baseline plus MDOT replay to prove zero
    regressions.

## Next Implementation TODO 2026-04-14

Use this as the immediate continuation checklist. The spec remains the
verification gate; do not mark this complete on checksum, row count, or sampled
validation alone.

1. [ ] Extract and inspect the latest focused trace:
   `.tmp/google_ocr_research/mdot_2026_04_03_estqua_downstream_replay_after_fragmented_schedule_01`.
   - [ ] Slice `row_merging`, `cell_extraction`, `row_parsing`, and
     `post_processing` stage records into
     `.tmp/google_ocr_research/debug_extract_0403_after_fragmented_schedule_01/`.
   - [ ] Confirm the first-bad stage for the remaining `Traf Regulator Control`
     row by comparing physical row IDs, merged row IDs, cell rows, and final
     parsed items.
   - [ ] Confirm the first-bad stage for the remaining `Maintenance Gravel`
     row by comparing the input cells that produce
     `_ Project Cleanup, Modified Maintenance Gravel`.

2. [ ] Fix the `Traf Regulator Control` collapse with a general rule.
   - [ ] Rule must be based on row geometry, source-id fragments, quantity/unit
     payload, and local schedule sequence only.
   - [ ] Rule must not branch on document key, MDOT name, item number, expected
     description, or fixture path.
   - [ ] Add a focused unit test using generic fragmented schedule-source
     tokens that proves a standalone unpriced schedule continuation is promoted
     rather than absorbed into the preceding row.
   - [ ] Re-run focused stage tests before replay.

3. [ ] Fix the `Maintenance Gravel` collapse with a general row-splitting or
   post-splitting rule.
   - [ ] Rule must detect merged unpriced schedule rows from repeated
     source-id/line-number/quantity/unit structure, not from the literal
     descriptions.
   - [ ] Preserve exact comparator behavior; any cleanup or split must happen
     in a named production stage with repair/mutation history.
   - [ ] Add a focused unit test proving a merged unpriced schedule row splits
     into two schedule rows with independent item numbers, units, and
     quantities.

4. [ ] Rerun the focused 04/03 GOCR downstream replay.
   - [ ] Expected row count: `677`.
   - [ ] No item-number pattern failures.
   - [ ] No checksum shortcut; inspect the full mismatch JSON/CSV.
   - [ ] If mismatches remain, bucket each one by first bad stage before adding
     another rule.

5. [ ] Rerun the full original-baseline plus MDOT replay.
   - [ ] Use `.tmp/gocr_ocr_cache` after the focused 04/03 replay reaches the
     exact row-count and item-number gate.
   - [ ] Confirm the original four PDFs do not regress.
   - [ ] Confirm every MDOT PDF with available GOCR cache emits exact mismatch
     artifacts through the same trace endpoint.
   - [ ] Update this spec with run path, row counts, exact mismatch counts,
     root-cause bucket deltas, accepted rules, and rejected approaches.

6. [ ] Keep ground-truth status honest.
   - [ ] Do not mark any MDOT fixture locked until the visual review ledger has
     every row and compared cell checked against the rendered PDF pages.
   - [ ] Do not increment `reviewed_item_count` without visual PDF evidence or
     explicit user confirmation.
   - [ ] Continue treating MDOT fixtures as `needs_visual_review_ledger` until
     the full visual ledger is complete.

## Spec TODO Audit 2026-04-15

Leftover unchecked work from the full spec, appended here so the active
continuation list has one bottom-of-file gate. The current implementation lane
remains the focused 04/03 MDOT row-collapse repair first, then the full
baseline-plus-MDOT replay.

1. [ ] Close the focused `mdot_2026_04_03_estqua-pay-items` row-count gap:
   recover both missing rows (`Traf Regulator Control` and `Maintenance
   Gravel`) with geometry/source-id/quantity/unit/sequence-based rules only.
2. [ ] Rerun the focused 04/03 replay after each rule and require `677/677`
   rows, no item-number pattern failures, exact mismatch artifacts, and
   first-bad-stage/root-cause evidence for any remaining mismatch.
3. [ ] Rerun all available cached PDFs together after the focused replay is
   stable, using the original four baseline PDFs as the no-regression gate and
   including every MDOT cache present under `.tmp/gocr_ocr_cache`.
4. [ ] Keep the four original baseline blockers visible: Springfield still
   needs visual/source resolution for items `63`, `64`, and `106`; all four
   baseline ledgers still need full row-by-row visual verification before they
   can be marked locked.
5. [ ] Keep the MDOT ground-truth status honest: every MDOT pay-item and
   measurement-payment fixture remains `needs_visual_review_ledger` until each
   rendered-page ledger row and compared cell is visually checked.
6. [ ] Finish trace-schema coverage gates: required per-stage payload tests,
   complete final-field source provenance, stable rule/reason attribution for
   every changed value, and confirmed first-bad-stage classification instead of
   placeholder root-cause evidence.
7. [ ] Finish the trace viewer/debug surface: row timeline from OCR through
   comparison, root-cause/stage dashboard, source-provenance drilldown, and run
   dashboard row count/item count/checksum/artifact links.
8. [ ] Preserve extraction-rule discipline on every iteration: no production
   branching on document key, fixture path, contractor/agency name, literal
   expected description, or one-off item number.

