# Held-Out OCR Generalization Hardening Spec

Date: 2026-04-16

Purpose: harden the OCR PDF extraction pipeline so new PDFs can run first-try
through the app with trustworthy field-level output. Acceptance is not item
count parity. Acceptance is exact visual field accuracy, or an explicit review
flag when the system cannot prove exact fidelity.

## Non-Negotiables

- [ ] Compare against visual ground truth with exact string equality only.
- [ ] Do not normalize in the comparator. No punctuation, whitespace, case,
      glyph, numeric, class-code, or currency forgiveness.
- [ ] Do not use native text as acceptance evidence. The app path must assume
      native text can fail and must exercise the OCR pipeline.
- [ ] Do not add PDF-name, project-name, or document-key branching.
- [ ] Prefer general layout-family, geometry, OCR provenance, and confidence
      rules over one-off downstream repairs.
- [ ] Treat high semantic confidence and exact visual fidelity as different
      signals.
- [ ] Auto-accept is allowed only when exact visual provenance is preserved or
      the field is otherwise provably faithful.

## Current Locked Baseline PDFs

These three PDFs are now the held-out baseline. Do not tune directly against
them during the next iteration wave except to confirm whether general fixes
improve them after the nine-PDF hardening loop.

- [ ] `external_baraga_erfo17_bid_form_window:pay_items`
  - Layout family: municipal boxed bid form.
  - Current exact field accuracy: `83.3333%`.
  - Rows: `23/23`.
  - Visual status: fully manually visual-verified.
- [ ] `external_mdot_2025_02_07_estqua_window:pay_items`
  - Layout family: AASHTOWare schedule of items.
  - Current exact field accuracy: `82.7471%`.
  - Rows: `398/398`.
  - Visual status: scaffold generated, row-by-row visual verification pending.
- [ ] `external_mdot_2025_02_07_25_02001_bid_tab_window:pay_items`
  - Layout family: AASHTOWare bid tab.
  - Current exact field accuracy: `47.0588%`.
  - Rows: `68/68`.
  - Visual status: scaffold generated, row-by-row visual verification pending.

Baseline artifacts:

- [ ] `.tmp/external_pdf_validation_20260415/visual_ground_truth_labels/summary.csv`
- [ ] `.tmp/external_pdf_validation_20260415/visual_ground_truth_labels/field_comparison.csv`
- [ ] `.tmp/external_pdf_validation_20260415/visual_ground_truth_labels/field_deviations.csv`
- [ ] `.tmp/external_pdf_validation_20260415/visual_ground_truth_labels/deviation_summary_by_category.csv`
- [ ] `.tmp/external_pdf_validation_20260415/visual_ground_truth_labels/trace_token_audit_summary.json`
- [ ] `.tmp/external_pdf_validation_20260415/visual_ground_truth_labels/trace_token_audit.csv`

## Baseline Findings To Carry Forward

- [ ] Exact comparison currently has `651` field deviations.
- [ ] `623/651` deviations are numeric visual text mutations.
- [ ] `554/651` deviations had the exact printed token preserved in
      `row_parsing.raw_*`, then diverged when final numeric fields were emitted
      as parsed doubles.
- [ ] `66/651` deviations had the truth token in the source row text but no
      `raw_bid_amount` carried onto the final item.
- [ ] `30/651` deviations are raw token differences that need OCR, row
      assembly, or description repair investigation.
- [ ] `1/651` deviation has a missing raw item field.
- [ ] Known description repairs surfaced by the baseline:
  - `CI A`, `CIA`, `CI E`, `CIE` should repair to visual `Cl A` / `Cl E`
    when class-code policy allows alphabetic `CI` normalization.
  - `Cement - Treated` should repair to `Cement-Treated`.
  - `OPEN - CLOSED` should repair to `OPEN-CLOSED`.
  - `Handling and Disposal, LM` can be misclassified as boilerplate after an
    existing description continuation and must attach as a trailing
    continuation.
- [ ] Known confidence gap: the current quality system can score a field high
      because the parsed semantic number is correct while exact visual token
      fidelity is not preserved.

## Code Changes Already Started

- [x] Exact replay ground-truth comparator now compares `toString()` values
      only and does not numeric-normalize.
- [x] Description cleaner repairs compact class-code confusables `CIA` and
      `CIE`.
- [x] Description cleaner repairs `Cement - Treated` and `OPEN - CLOSED`.
- [x] Row merger treats `Handling and Disposal` as a trailing descriptor
      continuation signal.
- [x] Field confidence caps OCR-backed parsed numeric fields that lack a raw
      source token.
- [x] Quality status blocks auto-accept when parsed OCR numeric fields lack raw
      source tokens.

## Next Corpus Expansion

Goal: collect nine additional PDFs, three per layout family, and use them as
the next hardening iteration set. The original three held-out PDFs remain the
locked baseline until after the nine-PDF loop.

- [ ] Collect three additional municipal boxed bid forms.
- [ ] Collect three additional AASHTOWare schedule-of-items PDFs.
- [ ] Collect three additional AASHTOWare bid-tab PDFs.
- [ ] Store source PDFs under the existing external-validation sample flow.
- [ ] Render page windows to PNG for visual review.
- [ ] Build visual ground-truth ledgers for every row and field.
- [ ] Mark each row as one of:
  - `visual_verified`
  - `needs_full_visual_verification`
  - `ambiguous_visual_token`
- [ ] Do not promote a ledger to acceptance ground truth until every row is
      visually checked.

## Nine-PDF Iteration Workflow

For each of the nine PDFs:

- [ ] Run through the same OCR app/harness path used by the S21 import flow.
- [ ] Capture full stage traces with `PDF_CORPUS_WRITE_TRACE=true`.
- [ ] Export final extracted fields.
- [ ] Compare final extracted fields against visual ledgers using exact string
      equality only.
- [ ] Generate field-level deviation CSVs.
- [ ] Generate trace token audit:
  - [ ] Whether source OCR row text exactly contains the visual token.
  - [ ] Whether `row_parsing.raw_*` exactly equals the visual token.
  - [ ] Whether final field output exactly equals the visual token.
  - [ ] First stage where the exact visual token is lost.
- [ ] Classify every deviation as one of:
  - [ ] Source OCR glyph/token error.
  - [ ] Row grouping or row-merging error.
  - [ ] Cell assignment/materialization error.
  - [ ] Numeric interpretation preserved value but lost visual token.
  - [ ] Post-processing mutated visual text.
  - [ ] Missing raw provenance.
  - [ ] Ground-truth visual ambiguity.
- [ ] Open an implementation task only after the same failure pattern appears
      across the nine-PDF corpus or is clearly layout-family general.

## Pipeline Hardening Backlog

### Raw Visual Token Preservation

- [ ] Preserve raw visual tokens for every user-facing field:
  - [ ] `visual_item_number_text`
  - [ ] `visual_description_text`
  - [ ] `visual_unit_text`
  - [ ] `visual_quantity_text`
  - [ ] `visual_unit_price_text`
  - [ ] `visual_bid_amount_text`
- [ ] Keep parsed numeric values for math and app workflows.
- [ ] Keep visual text values for audit, comparison, user display review, and
      exact acceptance gates.
- [ ] Carry raw bid amount from bid-tab source rows instead of leaving
      `raw_bid_amount` empty when a displayed token is present.
- [ ] Add trace contract checks that fail when a final parsed field has OCR
      evidence but lacks raw visual provenance.
- [ ] Add app/import contract checks so the app can show or audit the raw token
      that produced each parsed value.

### Confidence And Auto-Accept

- [ ] Split confidence into at least two signals:
  - [ ] Semantic extraction confidence.
  - [ ] Visual token fidelity/provenance confidence.
- [ ] Penalize or block auto-accept when final values are parsed from OCR but
      raw visual token provenance is missing.
- [ ] Penalize fields where post-processing mutates text and the mutation is
      not backed by an accepted OCR repair rule.
- [ ] Promote confidence output to include per-field reasons:
  - [ ] Raw token present.
  - [ ] Raw token missing.
  - [ ] Raw token changed by stage.
  - [ ] Source OCR glyph uncertainty.
  - [ ] Row continuation attached or inferred.
- [ ] Add a review flag for exact visual mismatches even when math validation
      passes.

### Comparator And Ground Truth

- [ ] Keep the comparator exact-only.
- [ ] Add tests proving these are mismatches:
  - [ ] `1` vs `1.0`
  - [ ] `923,802.000` vs `923802.0`
  - [ ] `Cl A` vs `CI A`
  - [ ] `Cement-Treated` vs `Cement - Treated`
- [ ] Ensure all comparison outputs include:
  - [ ] Document key.
  - [ ] Row index.
  - [ ] Item number.
  - [ ] Field name.
  - [ ] Visual truth value.
  - [ ] Pipeline final value.
  - [ ] Raw source value.
  - [ ] First bad stage.
  - [ ] Deviation category.
  - [ ] Visual review status.

### OCR And Row Assembly

- [ ] Investigate the `30` raw-token-differs deviations from the baseline
      before adding more description repair rules.
- [ ] Confirm whether each raw-token difference is:
  - [ ] OCR glyph error.
  - [ ] Cell crop boundary loss.
  - [ ] Row continuation ordering.
  - [ ] Over-aggressive artifact cleaning.
  - [ ] Visual ground-truth ambiguity.
- [ ] Improve row-merger continuation handling using layout-general features:
  - [ ] Same page.
  - [ ] Same text band.
  - [ ] Description-column alignment.
  - [ ] No structured numeric payload.
  - [ ] Lexical trailing-fragment signals.
- [ ] Avoid rules that depend on bid item number, PDF name, or project name.

### App Verification

- [ ] Build and install the app on the S21 after hardening changes.
- [ ] Use the HTTP driver to run imports through the app, not just SQL or
      local harness output.
- [ ] Create one project per imported PDF using the bid item project name.
- [ ] Import bid items through the app workflow.
- [ ] Verify the imported values through app UI and exported app state.
- [ ] Confirm no red screens during import, project creation, navigation, or
      item review.
- [ ] Confirm auto-accept/review-flag status matches visual fidelity outcome.

## Iteration Acceptance Gates

Nine-PDF iteration set:

- [ ] Each PDF has complete visual ground truth.
- [ ] Every field mismatch has a trace diagnosis.
- [ ] No false-positive exact matches are permitted.
- [ ] Any field without raw provenance is review-flagged.
- [ ] Any known confidence blind spot becomes a regression test.
- [ ] General fixes must improve or preserve behavior across the full
      nine-PDF set.

Locked three-PDF baseline retry:

- [ ] Re-run the original three held-out PDFs only after the nine-PDF loop has
      produced general fixes.
- [ ] Exact accuracy target is `100%` for visual-verified fields.
- [ ] If `100%` is not reached, every remaining field must be review-flagged
      with a specific trace diagnosis.
- [ ] Count/item-number success alone is not accepted.
- [ ] Native-text success is not accepted as field-level proof.

Regression gates:

- [ ] Original four-plus-eight training corpus remains no-regression.
- [ ] Held-out baseline exact comparator remains no-normalization.
- [ ] Stage trace contract remains complete enough to identify first bad
      stage for every exact mismatch.
- [ ] App-level S21 import path remains red-screen free.

## Immediate Next To-Do

- [ ] Finish row-by-row visual verification for the two MDOT baseline ledgers.
- [ ] Add raw visual token preservation for bid-tab `raw_bid_amount`.
- [ ] Re-run held-out three-PDF trace replay after the current description,
      row-merger, confidence, and comparator changes.
- [ ] Generate an updated exact comparison and trace-token audit.
- [ ] Collect the nine additional PDFs.
- [ ] Start the nine-PDF hardening loop before declaring the three held-out
      baseline PDFs solved.
