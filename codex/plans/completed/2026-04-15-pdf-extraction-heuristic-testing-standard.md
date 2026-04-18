# PDF Extraction Heuristic Testing Standard

Created: 2026-04-15

This is the standing test and iteration standard for PDF extraction heuristic
and algorithmic rule changes after the extraction pipeline decomposition gate.
Use it to keep replay evidence comparable from run to run.

This document standardizes method. It does not declare the current corpus
accurate. The current post-decomposition benchmark still has known exact
mismatches; heuristic work is accepted only when those counts decrease without
introducing regressions and the final target remains zero asserted mismatches
and zero trace-contract failures.

## Current Baseline

Use these artifact roots as the baseline for post-decomposition heuristic work:

- Original-four no-regression run:
  `.tmp/google_ocr_research/original_four_replay_after_final_trace_lint_gate_01`
- Full cached corpus run:
  `.tmp/google_ocr_research/full_corpus_replay_after_final_trace_lint_gate_01`
- Expected manifest:
  `test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json`
- Ground-truth review status sidecar:
  `test/features/pdf/extraction/fixtures/gocr_ground_truth_review_status.json`

Post-decomposition baseline status:

- Original-four replay failed only on
  `berrien_127449_us12-pay-items` with `16` asserted
  `ground_truth_column_mismatch` entries, all currently bucketed as
  `row_parsing_error`.
- Full cached corpus replay failed with `427` asserted row/column mismatches
  plus two existing `stage_trace_schema_contract` failures.
- The two trace-contract failures are both post-deduplication mutation
  attribution gaps:
  - `mdot_2026_03_06_26_03001_bid_tab-pay-items`
  - `mdot_2026_04_03_26_04001_bid_tab-pay-items`
- Current full-corpus mismatch count by document:
  - `berrien_127449_us12-pay-items`: `16`
  - `mdot_2025_11_07_estqua-pay-items`: `5`
  - `mdot_2025_12_05_estqua-pay-items`: `80`
  - `mdot_2026_03_06_26_03001_bid_tab-pay-items`: `5`
  - `mdot_2026_03_06_26_03002_bid_tab-pay-items`: `2`
  - `mdot_2026_03_06_estqua-pay-items`: `118`
  - `mdot_2026_04_03_26_04001_bid_tab-pay-items`: `6`
  - `mdot_2026_04_03_26_04003_bid_tab-pay-items`: `1`
  - `mdot_2026_04_03_estqua-pay-items`: `194`

Do not replace this baseline with a run that changes cache contents, expected
fixtures, comparison mode, or trace-contract rules unless the change is called
out in this document or in a successor dated standard.

## Corpus Inventory

The manifest-driven corpus contains these extraction contracts. Pay-item
contracts are the primary heuristic gate; measurement-payment contracts are
included when cache artifacts exist for them and remain part of the manifest.

| PDF family | Pay-item key and count | Measurement-payment key and count | Review status |
| --- | ---: | ---: | --- |
| Berrien County US-12 | `berrien_127449_us12:pay_items` `200` | `berrien_127449_us12:measurement_payment` `200` | needs visual PDF review |
| Grand Blanc sewer | `grand_blanc_938710_sewer:pay_items` `118` | `grand_blanc_938710_sewer:measurement_payment` `118` | needs visual PDF review |
| Huron Valley DWSRF | `huron_valley_917245_dwsrf:pay_items` `140` | `huron_valley_917245_dwsrf:measurement_payment` `140` | needs visual PDF review |
| Springfield DWSRF | `springfield_864130_dwsrf:pay_items` `131` | `springfield_864130_dwsrf:measurement_payment` `131` | needs visual PDF review |
| MDOT 2026-04-03 ESTQ&A | `mdot_2026_04_03_estqua:pay_items` `677` | `mdot_2026_04_03_estqua:measurement_payment` `250` | needs visual review ledger |
| MDOT 2026-03-06 ESTQ&A | `mdot_2026_03_06_estqua:pay_items` `685` | `mdot_2026_03_06_estqua:measurement_payment` `250` | needs visual review ledger |
| MDOT 2025-12-05 ESTQ&A | `mdot_2025_12_05_estqua:pay_items` `904` | `mdot_2025_12_05_estqua:measurement_payment` `250` | needs visual review ledger |
| MDOT 2025-11-07 ESTQ&A | `mdot_2025_11_07_estqua:pay_items` `831` | `mdot_2025_11_07_estqua:measurement_payment` `250` | needs visual review ledger |
| MDOT 2026-04-03 26-04001 bid tab | `mdot_2026_04_03_26_04001_bid_tab:pay_items` `18` | `mdot_2026_04_03_26_04001_bid_tab:measurement_payment` `18` | needs visual review ledger |
| MDOT 2026-04-03 26-04003 bid tab | `mdot_2026_04_03_26_04003_bid_tab:pay_items` `23` | `mdot_2026_04_03_26_04003_bid_tab:measurement_payment` `23` | needs visual review ledger |
| MDOT 2026-03-06 26-03001 bid tab | `mdot_2026_03_06_26_03001_bid_tab:pay_items` `78` | `mdot_2026_03_06_26_03001_bid_tab:measurement_payment` `78` | needs visual review ledger |
| MDOT 2026-03-06 26-03002 bid tab | `mdot_2026_03_06_26_03002_bid_tab:pay_items` `112` | `mdot_2026_03_06_26_03002_bid_tab:measurement_payment` `112` | needs visual review ledger |

Ground-truth status must remain honest. A PDF is not locked until every row and
every compared cell has visual PDF evidence or explicit user confirmation.

## Non-Negotiables

- The comparator remains exact. Do not normalize, trim, case-fold,
  punctuation-fold, coerce, round, add tolerances, or compare checksums alone.
- Fixture edits are allowed only when visual PDF evidence or explicit user
  confirmation proves the fixture is wrong. Record the correction in the
  review ledger or sidecar.
- Production fixes must be broad algorithmic rules. They may use geometry,
  row structure, column labels, source-id fragments, unit vocabulary, numeric
  consistency, local sequence evidence, and trace provenance.
- Production fixes must not branch on PDF name, document key, fixture path,
  agency/contractor/county/project name, literal expected description, or a
  one-off item number.
- Every cleanup, split, repair, dedupe, or inferred value belongs in a named
  production stage with stable `rule_name`, `reason_code`, mutation kind,
  before/after values, and source provenance where available.
- A replay failure is actionable only from the structured artifacts, not from
  console text.
- A successful iteration must prove no regression on the original-four gate
  and the full cached corpus gate.

## Standard Iteration Loop

Use this sequence for every heuristic or algorithmic rule change.

1. Pick one target failure from the current artifacts.
   Start with the mismatch JSON/CSV and the matching stage trace:
   `.tmp/google_ocr_research/<run_id>/failures/<document>-mismatches.json`
   and `.tmp/google_ocr_research/<run_id>/traces/<document>-stage-trace.json`.

2. Classify the first bad stage before writing production code.
   Use the established buckets: OCR source, validation, row grouping,
   row classification, region detection, column detection, row merging,
   cell assignment, numeric interpretation, row parsing, post-normalization,
   post-splitting, post-validation, sequence correction, deduplication,
   field confidence, or comparison.

3. State the general rule.
   The rule must be explainable without naming the PDF, expected row text, or
   item number. If the evidence is only document-specific, do not implement a
   production heuristic yet.

4. Add or update focused tests first.
   Prefer pure rule/helper tests for the touched stage, then a narrow stage
   test. Do not grow a god test file. Keep trace-shape tests separate when it
   improves readability.

5. Implement through the existing stage owner.
   Use the decomposed class for the affected stage and wire trace/mutation
   data through the existing `StageTrace` and substage payload path.

6. Run focused static and unit validation.
   Analyze touched production and test files. Run the touched stage tests and
   adjacent stage tests before any corpus replay.

7. Run a focused replay when useful.
   Use the same replay harness with a cache directory containing the target
   document JSON. The only allowed difference from the full command is
   `PDF_CORPUS_OCR_CACHE_DIR` and `GOOGLE_OCR_RESEARCH_RUN_DIR`.

8. Run the original-four no-regression replay.
   The result must not add any original-four mismatches or trace-contract
   failures. A rule that improves the target MDOT document but regresses any
   original-four PDF is rejected.

9. Run the full cached corpus replay.
   The result must reduce or preserve mismatch counts outside the intended
   target and must not add trace-contract failures.

10. Record the iteration.
    Capture command, run directory, mismatch deltas by document, root-cause
    bucket deltas, accepted rule, rejected approaches, and remaining failures
    in the active heuristic spec.

## Canonical Commands

Focused unit test examples must be adapted to the touched stage, but corpus
replay commands should stay structurally identical.

Original-four gate:

```powershell
flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache_original_four_20260415_decomp_01 --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/<run_id_original_four> --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json
```

Full cached corpus gate:

```powershell
flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows --dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/gocr_ocr_cache --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/google_ocr_research/<run_id_full_corpus> --dart-define=PDF_CORPUS_EXPECTED=test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_expected.json
```

Trace contract and transport spot checks:

```powershell
flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart test/features/pdf/extraction/pipeline/stage_trace_sink_test.dart test/features/pdf/extraction/pipeline/stage_trace_diagnostics_test.dart -d windows
```

Replay harness smoke check without replay:

```powershell
flutter test test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart -d windows
```

Use run IDs that encode the date, target, and pass number, for example:

- `original_four_after_mdot_0403_row_split_20260415_01`
- `full_corpus_after_mdot_0403_row_split_20260415_01`
- `focused_mdot_2026_04_03_estqua_row_split_20260415_01`

Never reuse a run directory for a new result.

## Required Artifacts

Every accepted iteration must leave these artifacts under the run directory:

- `gocr-trace-manifest.json`
- `summaries/downstream-replay-summary.json`
- `failures/downstream-replay-failures.json` when failures exist
- `failures/<document>-mismatches.json` for each asserted mismatch document
- `failures/<document>-mismatches.csv` for quick review
- `traces/<document>-stage-trace.json`
- `summaries/<document>-stage-trace-summary.json`

The mismatch JSON is the source of truth for field-level deltas. The trace JSON
is the source of truth for first-bad-stage analysis and mutation attribution.
The console failure message is only a pointer to these artifacts.

## Acceptance Rules

A heuristic iteration can be accepted when all are true:

- Focused unit and adjacent stage tests pass.
- Touched files analyze cleanly.
- The original-four replay has no new failures versus the current baseline.
- The full cached corpus replay has no new failures versus the current
  baseline.
- The target mismatch count decreases, or the change closes a trace-contract
  failure without increasing any mismatch count.
- Every changed final field has stable mutation attribution and source
  provenance where source rows or cells are available.
- The active spec records the command, run directory, deltas, and rule
  rationale.

The final accuracy gate for this lane is stricter:

- Original-four replay: zero asserted mismatches and zero trace-contract
  failures.
- Full cached corpus replay: zero asserted mismatches and zero trace-contract
  failures for every cached PDF.
- Ground-truth status remains explicit; PDFs with unreviewed visual ledgers are
  not described as visually locked even if the extraction replay is clean.

## Rejected Evidence

Do not use any of these as acceptance evidence:

- A passing checksum with row/field mismatches still present.
- A replay that used a different expected fixture without a recorded fixture
  review update.
- A replay that changed comparator behavior.
- A single focused PDF replay without original-four and full-corpus gates.
- A console log excerpt without the structured mismatch and trace artifacts.
- A rule that fixes one document by recognizing that document's identity.

## Update Discipline

After each accepted or rejected heuristic pass, update the active heuristic
spec with:

- target document and failure bucket;
- general rule attempted;
- focused tests added or changed;
- exact commands run;
- artifact run paths;
- mismatch delta table;
- trace-contract delta;
- accepted decision or rejection reason;
- next target failure.

If the replay harness, expected manifest, cache directories, comparator rules,
or trace-contract gate change, update this standard first so the next run is
not compared against incompatible evidence.
