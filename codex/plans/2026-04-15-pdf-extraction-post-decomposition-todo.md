# PDF Extraction Post-Decomposition To-Do

Created: 2026-04-15

This is the active to-do list for the post-decomposition PDF extraction
iteration loop. Completion means the original-four replay and the full cached
corpus replay both reach zero asserted mismatches and zero trace-contract
failures, with honest ground-truth review status preserved.

## Current Evidence

- [x] Viewed the post-decomposition benchmark standard:
      `docs/testing/pdf-extraction-heuristic-testing-standard.md`.
- [x] Re-ran the original-four extraction replay:
      `.tmp/google_ocr_research/original_four_audit_current_20260415_01`.
  - Result: reproduced the benchmark with only
    `berrien_127449_us12-pay-items` failing.
  - Current mismatch count: `16`.
  - Current root-cause bucket: `row_parsing_error=16`.
- [x] Re-ran the full cached-corpus extraction replay:
      `.tmp/google_ocr_research/full_corpus_audit_current_20260415_01`.
  - Result: reproduced the benchmark with `427` asserted mismatches and `2`
    trace-contract failures.
- [x] Added compact replay audit tooling:
      `scripts/audit_pdf_extraction_replay.ps1`.
  - Default output root:
    `.claude/test-results/YYYY-MM-DD/pdf-extraction-replay-audit-<time>-<run_id>/`.
  - Current original-four audit output:
    `.claude/test-results/2026-04-15/pdf-extraction-replay-audit-134851-original_four_audit_current_20260415_01/`.
  - Current full-corpus audit output:
    `.claude/test-results/2026-04-15/pdf-extraction-replay-audit-134858-full_corpus_audit_current_20260415_01/`.
- [x] Updated the PDF extraction testing workflow rules to use the compact
      audit script and avoid broad PowerShell deserialization of giant replay
      JSON artifacts.
- [x] Reviewed representative PDFs visually and saved the reviewed source PDFs
      into a durable Claude asset corpus:
      `.claude/specs/assets/pdf-corpus/ocr-layout-review/`.
  - Municipal boxed bid forms:
    `.claude/specs/assets/pdf-corpus/ocr-layout-review/municipal_bid_forms/`.
  - AASHTOWare Schedule of Items:
    `.claude/specs/assets/pdf-corpus/ocr-layout-review/mdot_schedule_of_items/`.
  - AASHTOWare Bid Tabs:
    `.claude/specs/assets/pdf-corpus/ocr-layout-review/mdot_bid_tabs/`.
  - Manifest:
    `.claude/specs/assets/pdf-corpus/ocr-layout-review/README.md`.
- [x] Confirmed the reviewed corpus contains three distinct layout families
      that the extraction system must recognize and handle; testing parameters
      do not change because these are the PDFs we are training and hardening
      against.

## Layout-Aware Extraction Spec Direction

Do not treat the next source experiment as pure "grid-aware OCR." The forward
spec is layout-aware extraction/OCR across all three reviewed layout families:

- [ ] `municipal_boxed_bid_form`.
  - Examples:
    - `municipal_bid_forms/berrien_127449_pay_items.pdf`
    - `municipal_bid_forms/springfield_864130_pay_items.pdf`
    - `municipal_bid_forms/huron_valley_917245_pay_items.pdf`
    - `municipal_bid_forms/grand_blanc_938710_pay_items.pdf`
  - Visual shape: municipal bid forms with visible boxed table rules, row
    lines, column lines, and bid-total/bid-amount columns.
  - Expected pipeline behavior: grid/cell/row-aware OCR can be appropriate
    when native text is absent or weak; checksum/math validation remains
    available because quantity, unit price, and bid amount columns exist.
- [ ] `aashtoware_schedule_of_items`.
  - Example:
    - `mdot_schedule_of_items/mdot_2026-04-03_estqua_schedule_sample_pages_001_025.pdf`
  - Visual shape: AASHTOWare Schedule of Items pages with gray/zebra row bands,
    stable columns, repeated headers, wrapped descriptions, and no full boxed
    vertical grid.
  - Expected pipeline behavior: detect row bands and column lanes without
    requiring grid-line intersections. These pages do not have the same total
    amount/bid amount column expected by municipal bid forms, so parsing must
    succeed without checksum validation as the acceptance mechanism.
- [ ] `aashtoware_bid_tab`.
  - Examples:
    - `mdot_bid_tabs/mdot_2026-03-06_26-03002_bid_tab_by_item.pdf`
    - `mdot_bid_tabs/mdot_2026-04-03_26-04001_bid_tab_by_item.pdf`
  - Visual shape: AASHTOWare Tabulation of Bids pages with gray banded rows,
    bidder price groups, partial vertical separators, and double-line item
    records where line number/item ID/quantity/prices and description/unit can
    appear on separate visual lines.
  - Expected pipeline behavior: recognize the double-line AASHTOWare record
    shape, preserve bidder-group boundaries, and parse rows without assuming a
    municipal-style total/bid amount checksum contract.

## Research Sources And Confirmed Provider Limits

- [x] Google Cloud Vision `DOCUMENT_TEXT_DETECTION` returns a
      `fullTextAnnotation` hierarchy with `Page`, `Block`, `Paragraph`,
      `Word`, and `Symbol` nodes, including bounding boxes/confidence for OCR
      text.
  - Source: `https://cloud.google.com/vision/docs/fulltext-annotations`
  - Source: `https://cloud.google.com/vision/docs/reference/rest/v1/AnnotateImageResponse`
- [x] Vision `BlockType` can include `TABLE` and `RULER`, but Vision does not
      provide a complete table-cell schema, column semantics, grid
      intersections, or a guaranteed row/column model.
  - Source: `https://cloud.google.com/vision/docs/reference/rest/v1/AnnotateImageResponse`
- [x] Vision file/PDF OCR can return normalized bounding vertices for PDF
      processing, and the small synchronous file API supports limited-page PDF
      jobs; this remains a provider experiment, not a replacement for our
      layout classifier.
  - Source: `https://cloud.google.com/vision/docs/pdf`
  - Source: `https://cloud.google.com/vision/docs/file-small-batch`
- [x] Document AI exposes structured table objects/cells through the Document
      schema and table-oriented processors, but current measured project
      evidence showed the configured Document AI processor underperformed
      Vision image OCR on the compared S10 corpus.
  - Source: `https://cloud.google.com/document-ai/docs/reference/rest/v1/Document`
  - Source: `https://cloud.google.com/document-ai/docs/form-parser`
  - Source: `https://cloud.google.com/document-ai/docs/layout-parse-chunk`
  - Local measured note:
    `.codex/plans/2026-04-13-google-assisted-ocr-provider-plan.md`.

## Layout-Aware Implementation TODO

- [ ] Add a layout classifier before source-specific OCR/table parsing.
  - Required output families:
    `municipal_boxed_bid_form`, `aashtoware_schedule_of_items`,
    `aashtoware_bid_tab`, and `unknown`.
  - Candidate signals: native text availability, visual grid-line density,
    gray/zebra band density, AASHTOWare header tokens, repeated table headers,
    stable x-column anchors, bidder-group headers, and double-line item
    records.
  - The classifier must not branch on PDF filename, project name, county,
    letting date, expected item count, or one known item number.
- [ ] Preserve all existing replay/testing parameters.
  - The original-four replay and full cached-corpus replay remain the gates.
  - The reviewed PDFs remain part of the training/hardening corpus.
  - Any new focused tests must be additive and must not weaken current exact
    comparison, trace-contract, or ground-truth rules.
- [ ] Add layout-aware source selection.
  - For native/positioned AASHTOWare PDFs, prefer native positioned PDF text
    when it is present and stable enough.
  - For scanned or image-heavy boxed municipal bid forms, keep OCR and
    grid/cell/row-band routes available.
  - For mixed/uncertain pages, compare native text and OCR evidence through
    traceable source provenance rather than silently replacing one with the
    other.
- [ ] Add AASHTOWare Schedule of Items row-band parsing.
  - Detect row bands from gray/zebra regions, text baselines, and stable item
    number/line number anchors.
  - Detect columns for line number, item description, item ID, quantity, and
    units without requiring vertical grid lines.
  - Allow wrapped descriptions and repeated headers.
  - Accept parsed item rows without requiring bid amount/checksum validation.
- [ ] Add AASHTOWare Bid Tab double-line row parsing.
  - Group line number/item ID/quantity/prices with following description/unit
    lines when they are part of the same visual item record.
  - Preserve bidder-group column boundaries and repeated unit-price/ext-amount
    pairs.
  - Parse rows without assuming a municipal-style total/bid amount checksum
    contract.
- [ ] Keep municipal boxed-form grid handling.
  - Use grid/cell/row-band OCR where it improves source text or cell
    assignment.
  - Continue math/checksum validation where quantity, unit price, and bid
    amount columns exist.
- [ ] Add trace output for layout decisions and source selection.
  - Required fields: `layout_family`, signals used, confidence, native text
    availability, OCR route, row-band/grid-band source, and fallback reason.
  - Any final field mutation still needs stable `rule_name`, `reason_code`,
    before/after values, mutation kind, and source provenance.

## Current Benchmark

- [ ] Original-four replay reaches zero asserted mismatches.
  - Current: `16`.
  - Failing document: `berrien_127449_us12-pay-items`.
- [ ] Full cached-corpus replay reaches zero asserted mismatches.
  - Current: `427`.
- [ ] Full cached-corpus replay reaches zero trace-contract failures.
  - Current: `2`.
- [ ] Ground-truth status remains explicit; no fixture changes are accepted
      without visual PDF evidence or explicit user confirmation.

## Full-Corpus Root-Cause Totals

- [ ] Close `post_normalization_error`: `198`.
- [ ] Close `row_parsing_error`: `125`.
- [ ] Close `ocr_source_error`: `48`.
- [ ] Close `numeric_interpretation_error`: `27`.
- [ ] Close `field_confidence_error`: `15`.
- [ ] Close `cell_assignment_error`: `14`.

## Most Upstream Root Cause

- [ ] Trace and repair the earliest confirmed first-bad stage:
      `text_recognition` via `ocr_source_error`.
  - Evidence source:
    `.claude/test-results/2026-04-15/pdf-extraction-replay-audit-134858-full_corpus_audit_current_20260415_01/ocr-source-examples.csv`.
  - Current count: `48`.
  - Field shape: `description=27`, `unit=21`.
  - Dominant examples:
    - `Dr` rendered as `Ɔ`, `☐`, or `○` in structure descriptions.
    - `Ton` rendered as `TCN`, `TOL`, `TOI`, or `ON`.
    - `Dlr` rendered as `DIR`.
    - `LSUM` rendered as `SJM`.
    - OCR inserted non-ASCII glyphs inside descriptions such as
      `Sɩt base, CIP` for `Subbase, CIP`.
  - Raw cache confirmation:
    - `.tmp/gocr_ocr_cache/mdot_2026_04_03_estqua-pay-items-google_cloud_vision.json`
      contains raw Google-cache element text including `Sɩt`, `D⚫`,
      `⚫ntro`, `Mɔɔilization`, `_S` + `JM`, `Tcn`, `Tol`, `Toi`, `Et`,
      `Inmi`, `Ɔ`, and `○`.
    - `.tmp/gocr_ocr_cache/mdot_2026_03_06_estqua-pay-items-google_cloud_vision.json`
      contains raw Google-cache element text including `Ɔ` and `☐`.
    - Therefore the dominant OCR-source examples are upstream cache/source OCR
      artifacts, not artifacts invented by row parsing or post-processing.

## Priority 0: OCR Source / Provider / Rendering / Layout Experiments

- [ ] Confirm the current Google Assisted MDOT cache route is full-page Vision
      image OCR, not table/cell-region OCR.
  - Current cache evidence:
    `.tmp/gocr_ocr_cache/mdot_2026_04_03_estqua-pay-items-google_cloud_vision.json`
    uses provider `google_cloud_vision`, call scope `image`, and rendered page
    images such as `2550x3300`.
  - Current replay evidence:
    `gocr_downstream_replay_test.dart` starts after cached normalized OCR and
    does not exercise grid-line detection, crop-cell mapping, or DPI
    re-extraction.
  - Current code distinction:
    grid/cell crop OCR exists in `OcrPageRecognitionExecutor` for pages with a
    detected grid, but the audited replay artifacts are full-page normalized
    Google Vision cache artifacts.
- [ ] Design a layout-aware source experiment before adding more downstream
      canonicalization rules.
  - Use geometry/layout-derived regions only: detected table span, row bands,
    gray/zebra bands, column lanes, cells from boxed grids, or AASHTOWare
    double-line item records.
  - Compare native positioned PDF text against Vision image OCR for
    AASHTOWare schedule and bid-tab pages before assuming rendered-image OCR is
    the best source.
  - Keep it as an internal Google Assisted backend/profile, not a new
    company-facing mode.
  - Capture output in the same GOCR cache/replay artifact format so exact
    comparison remains unchanged.
  - Compare against the current full-page Vision baseline with the compact
    audit script.
- [ ] Decide the first source experiment shape.
  - Candidate A: native positioned PDF text path for AASHTOWare Schedule of
    Items and Bid Tab pages, preserving word coordinates and source provenance.
  - Candidate B: row-band/gray-band extraction for AASHTOWare Schedule of Items
    pages, using line number/item number anchors and stable x-column lanes.
  - Candidate C: double-line item-record grouping for AASHTOWare Bid Tab pages.
  - Candidate D: boxed-grid row/cell/column OCR for municipal bid forms where
    native text is absent or weaker than OCR.
  - Candidate E: selective Vision crop OCR only for high-risk short
    unit/description tokens or ambiguous native-text/visual-source conflicts.
  - Acceptance: fewer `ocr_source_error` mismatches with no original-four or
    full-corpus regressions and no new trace-contract failures.
- [ ] Re-check Vision raw-PDF backend as a separate experiment only if
      layout-aware native/row-band/grid-band routes do not improve source text.
  - This was already listed in the provider plan because current Vision sends
    rendered page images, not raw PDFs.
- [ ] Do not reprioritize Document AI as the next step unless there is a new
      processor/config hypothesis.
  - Existing measured note from
    `.codex/plans/2026-04-13-google-assisted-ocr-provider-plan.md`:
    current Document AI processor missed the gates and was worse than Vision
    image OCR on the S10 three-PDF comparison:
    Berrien `137/200` vs Vision `164/200`, Huron `128/140` vs Vision
    `139/140`, Grand Blanc `101/118` vs Vision `113/118`.
  - Document AI Layout Parser remains a future table-structure experiment only
    after cheaper Vision image/table-region/raw-PDF routes fail.

## Immediate Iteration Queue

- [ ] Add focused tests for OCR-glyph/unit canonicalization using broad rules,
      not document identity, after the first source/rendering experiment is
      measured.
  - Candidate rule input: known unit vocabulary, field geometry, source token
    confidence, and item-row structure.
  - Candidate stage owner must be selected before implementation:
    text cleanup, post-normalization, or a dedicated OCR-token canonicalization
    seam.
- [ ] Decide whether `Dr`/structure glyph repair belongs in a general OCR text
      canonicalizer or a description-domain normalization rule.
  - The rule must not branch on MDOT document keys or expected descriptions.
- [ ] Add trace/mutation attribution for any OCR-token repair.
  - Required fields: stable `rule_name`, `reason_code`, mutation kind,
    before/after values, and source provenance.
- [ ] Run focused unit tests for the chosen stage.
- [ ] Run adjacent stage tests affected by the chosen stage.
- [ ] Run a focused replay for the target OCR-source failure set.
- [ ] Run the original-four no-regression replay.
- [ ] Run the full cached-corpus replay.
- [ ] Run `scripts/audit_pdf_extraction_replay.ps1` after each replay and
      record the dated `.claude/test-results/` output path here.

## Trace-Contract Queue

- [ ] Fix post-deduplicate mutation attribution for
      `mdot_2026_03_06_26_03001_bid_tab-pay-items`.
  - Current errors: `10`.
  - Affected item: `0100`.
  - Missing: stable `rule_name` and `reason_code` for changed final fields.
- [ ] Fix post-deduplicate mutation attribution for
      `mdot_2026_04_03_26_04001_bid_tab-pay-items`.
  - Current errors: `8`.
  - Affected item: `0045`.
  - Missing: stable `rule_name` and `reason_code` for changed final fields.

## High-Volume Downstream Queue

- [ ] Reduce `post_normalization_error` without hiding true OCR-source errors.
  - Largest documents:
    - `mdot_2026_03_06_estqua-pay-items`: `76`.
    - `mdot_2026_04_03_estqua-pay-items`: `71`.
    - `mdot_2025_12_05_estqua-pay-items`: `44`.
- [ ] Reduce `row_parsing_error`.
  - Largest documents:
    - `mdot_2026_03_06_estqua-pay-items`: `36`.
    - `mdot_2026_04_03_estqua-pay-items`: `35`.
    - `mdot_2025_12_05_estqua-pay-items`: `33`.
    - `berrien_127449_us12-pay-items`: `16`.
- [ ] Reduce `numeric_interpretation_error`.
  - Largest document: `mdot_2026_04_03_estqua-pay-items`: `23`.
- [ ] Reduce `field_confidence_error`.
  - Largest document: `mdot_2026_04_03_estqua-pay-items`: `13`.
- [ ] Reduce `cell_assignment_error`.
  - Largest document: `mdot_2026_04_03_estqua-pay-items`: `12`.

## Acceptance Checklist For Each Rule Pass

- [ ] Rule is algorithmic and explainable without naming a PDF, document key,
      agency, expected text, or one item number.
- [ ] Focused tests added or updated before production changes.
- [ ] Touched files analyze cleanly.
- [ ] Original-four replay has no new failures.
- [ ] Full cached corpus has no new failures outside the intended target.
- [ ] Target mismatch count decreases or a trace-contract failure closes.
- [ ] Audit output is generated under `.claude/test-results/YYYY-MM-DD/`.
- [ ] This to-do list records command, run directory, audit directory, mismatch
      delta, trace-contract delta, and next target.
