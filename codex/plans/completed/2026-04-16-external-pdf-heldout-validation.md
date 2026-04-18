# External PDF Held-Out Validation

Created: 2026-04-16

Purpose: validate first-try generalization on three PDFs that were not part of
the original four-plus-eight PDF training/hardening corpus.

## Held-Out Corpus

- Municipal boxed bid form:
  `.tmp/external_pdf_validation_20260415/samples/baraga_erfo17_imperial_heights_bid_form_pages_014_023.pdf`
- AASHTOWare Schedule of Items:
  `.tmp/external_pdf_validation_20260415/samples/mdot_2025-02-07_estqua_pages_001_010.pdf`
- AASHTOWare Bid Tabulation by Item:
  `.tmp/external_pdf_validation_20260415/samples/mdot_2025-02-07_25-02001_bid_tab_pages_002_010.pdf`

Run-local manifest:
`.tmp/external_pdf_validation_20260415/external_validation_manifest_holdout_latest.json`.

Do not use the earlier `native_text_proxy_external_validation` label as
acceptance evidence. Native PDF text is not the standard for this lane. Treat
the run below as OCR-pipeline evidence only, and treat field-level truth as
unknown until every compared row/cell is checked against rendered page images.

Rendered visual review pages:
`.tmp/external_pdf_validation_20260415/visual_pages/`.

OCR candidate review ledgers:
`.tmp/external_pdf_validation_20260415/visual_ground_truth_review/`.

First-seen OCR report:
`.tmp/external_pdf_validation_20260415/ocr_first_seen_report/README.md`.

## Live Capture Result

Command shape:

```powershell
flutter test integration_test/pre_release_pdf_corpus_test.dart -d windows `
  --dart-define=PDF_CORPUS_MANIFEST=.tmp/external_pdf_validation_20260415/external_validation_manifest_holdout_latest.json `
  --dart-define=PDF_CORPUS_EXPECTED=.tmp/external_pdf_validation_20260415/external_validation_expected_03.json `
  --dart-define=PDF_CORPUS_BASELINE=.tmp/external_pdf_validation_20260415/external_validation_baseline_holdout_latest.json `
  --dart-define=PDF_CORPUS_DOCUMENT_KIND=pay_items `
  --dart-define=PDF_CORPUS_CLOUD_OCR_MODE=google_cloud_vision `
  --dart-define=PDF_CORPUS_OCR_CACHE_MODE=capture `
  --dart-define=PDF_CORPUS_WRITE_TRACE=true `
  --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/external_pdf_validation_20260415/pre_release_harness_run_03
```

Result: passed through the OCR pipeline with `failure_count: 0` for structural
count/item-number checks. This is not a field-level accuracy pass.

Artifacts:

- Summary:
  `.tmp/external_pdf_validation_20260415/pre_release_harness_run_03/summaries/corpus-summary.json`
- Failures:
  `.tmp/external_pdf_validation_20260415/pre_release_harness_run_03/failures/corpus-failures.json`
- OCR cache:
  `.tmp/external_pdf_validation_20260415/pre_release_harness_run_03/cache/`
- Baseline/golden snapshot:
  `.tmp/external_pdf_validation_20260415/external_validation_baseline_holdout_latest.json`

| Document | Expected | Extracted | Quality | Status | Expected failures |
| --- | ---: | ---: | ---: | --- | ---: |
| Baraga ERFO 17 bid form window | 23 | 23 | 0.7433 | reviewFlagged | 0 |
| MDOT 2025-02-07 ESTQ&A schedule window | 398 | 398 | 0.7253 | reviewFlagged | 0 |
| MDOT 2025-02-07 25-02001 bid tab window | 68 | 68 | 0.9549 | autoAccept | 0 |

## Cache Replay Result

Command shape:

```powershell
flutter test integration_test/pre_release_pdf_corpus_test.dart -d windows `
  --dart-define=PDF_CORPUS_MANIFEST=.tmp/external_pdf_validation_20260415/external_validation_manifest_holdout_latest.json `
  --dart-define=PDF_CORPUS_EXPECTED=.tmp/external_pdf_validation_20260415/external_validation_expected_03.json `
  --dart-define=PDF_CORPUS_BASELINE=.tmp/external_pdf_validation_20260415/external_validation_baseline_holdout_latest.json `
  --dart-define=PDF_CORPUS_DOCUMENT_KIND=pay_items `
  --dart-define=PDF_CORPUS_CLOUD_OCR_MODE=google_cloud_vision `
  --dart-define=PDF_CORPUS_OCR_CACHE_MODE=replay `
  --dart-define=PDF_CORPUS_OCR_CACHE_DIR=.tmp/external_pdf_validation_20260415/pre_release_harness_run_03/cache `
  --dart-define=PDF_CORPUS_WRITE_TRACE=true `
  --dart-define=GOOGLE_OCR_RESEARCH_RUN_DIR=.tmp/external_pdf_validation_20260415/pre_release_harness_run_03_replay
```

Result: replayed the captured OCR cache with `failure_count: 0` for structural
count/item-number checks. This is not a field-level accuracy pass.

Artifacts:

- Summary:
  `.tmp/external_pdf_validation_20260415/pre_release_harness_run_03_replay/summaries/corpus-summary.json`
- Traces:
  `.tmp/external_pdf_validation_20260415/pre_release_harness_run_03_replay/traces/`

## Interpretation

- First-try OCR generalization is strong for gross pay-item extraction across
  all three held-out layout families: count and item-number checks matched.
- The traces show `ocr_only` strategy with rendered pages and Google Vision
  OCR tokens; the run does not depend on native text extraction.
- The MDOT bid-tab held-out sample reached `autoAccept`.
- The Baraga municipal window and MDOT schedule window remain `reviewFlagged`;
  they should enter app review flow, not blind import acceptance.
- Field-level accuracy percentage is not currently honest to report because
  these held-out PDFs do not yet have independent visual per-cell ground truth.
- Mutation/deviation evidence exists in:
  `.tmp/external_pdf_validation_20260415/ocr_first_seen_report/raw_to_final_mutations.csv`
  and
  `.tmp/external_pdf_validation_20260415/ocr_first_seen_report/repair_log.csv`.

## Remaining Gates

- [ ] Promote the held-out manifest/expected/baseline out of `.tmp` if this
      becomes a permanent regression gate.
- [ ] Build visually reviewed row-by-row/per-cell ground truth for the three
      held-out PDFs before describing them as locked or reporting true field
      accuracy.
- [ ] Decide whether `reviewFlagged` is acceptable for first-try import review
      flow, or whether held-out PDFs must reach `autoAccept`.
- [ ] Add exact per-cell comparison for held-out pay-item fixtures if the goal
      is field-level accuracy rather than count/item-number generalization.
- [ ] Run a connected-device Google-assisted capture gate if the release gate
      requires tablet/S10/S21 proof instead of Windows capture plus replay.
- [x] Push the three PDFs to S21 `RFCNC0Y975L` under
      `/sdcard/Download/FieldGuide_HeldOut_OCR_20260416/` for app-side import
      testing.
