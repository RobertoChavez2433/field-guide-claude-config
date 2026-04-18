# Google Assisted OCR Fast Iteration Spec - 2026-04-13

## Status

- [x] Establish the first-pass corpus target: 12 paired bid-item PDFs and 12
  paired Measurement & Payment PDFs, not a 100-document hardening set.
- [x] Keep the immediate working path on the Google Assisted Pipeline with
  Google Cloud Vision image OCR as the current best measured backend.
- [x] Keep the Custom Pipeline separate. The Custom Pipeline must not call
  Google Cloud Vision, Document AI, or any Google-only adapter.
- [x] Keep test artifacts under a deletable run root so Windows and S10 output
  can be removed without hunting through scattered folders.
- [x] Add four more real Michigan project pairs to the acceptance corpus.
  - [x] Prioritize pay-item PDFs by table/grid stress coverage, not by whether
    the same source provides a real `01 22 00` section.
- [x] Add at least two MDOT/AASHTOWare-style bid-item stress PDFs.
  - [x] Downloaded 8 public MDOT Schedule of Items / bid-tab-by-item stress
    PDFs into `.tmp/public_mdot_pdf_corpus/bid_item_stress`.
  - [x] Added a tracked provenance manifest at
    `test/features/pdf/extraction/fixtures/mdot_public_pdf_corpus_manifest.json`.
  - [x] Added table-stress tags for schedule and bid-tab inputs so each stress
    document has an explicit extraction reason.
  - [x] Added `scripts/download_mdot_public_pdf_corpus.ps1` for repeatable
    download from MDOT public URLs.
  - [x] Added `scripts/generate_mdot_companion_mp_pdfs.py` to generate a
    similar-style `01 22 00` Measurement and Payment companion for each MDOT
    source PDF under `.tmp/public_mdot_pdf_corpus/bid_item_stress`.
  - [x] Added `mdot_public_pdf_corpus_manifest_test.dart` so the generated
    stress-pair contract cannot drift into unpaired or unlabeled fixtures.
  - [x] Promoted the four public MDOT Schedule of Items stress pairs into the
    prerelease acceptance corpus as four 25-page samples, about 100 schedule
    pages total, with stepped, zero-padded expected item-number ranges.
- [x] Build the faster OCR-cache replay runner that starts from captured
  normalized OCR data and skips device, Google, and PDF-rendering cost.
  - [x] Add a pure-Dart cache inspector for captured Google OCR JSON.
  - [x] Promote the Google OCR cache/replay adapter from test helpers into the
    production OCR seam so replay uses the real `OcrEngineV2` pipeline path.
  - [x] Add the downstream post-processing replay path that runs the extraction
    stages from cached normalized OCR data.
- [x] Add compact summary and failure-bucket output for replay runs.
- [x] Tighten acceptance gates so auto-accept cannot pass when expected counts,
  item numbers, or bid totals fail.
- [x] Add cleanup commands/hooks for `.tmp/google_ocr_research/<run_id>` and
  S10 staging directories.
- [ ] Run local cache replay across Springfield plus the expanded prerelease
  corpus.
- [ ] Run final connected S10 verification with real Google calls and no OCR
  fallback or replay cache.
- [ ] Run a final review against this checklist before closing the lane.

## Decisions

Use two company-facing extraction pipelines:

- Custom Pipeline: internal/local OCR and post-processing only.
- Google Assisted Pipeline: one public Google-backed pipeline. It may
  internally compare Google Cloud Vision, Document AI Enterprise Document OCR,
  Form Parser, or Layout Parser, but those are backend strategies, not separate
  company modes.

Use Google Cloud Vision image OCR as the immediate backend because it is the
closest measured route so far. Document AI remains available for bakeoff and
future table-structure experiments, but the next speed improvement is the replay
runner, not more slow device iteration.

Current replay status: the harness can now replay cached Google OCR through the
production `OcrEngineV2` seam, so element validation, structure detection, row
parsing, post-processing, and quality validation still run through the same
pipeline graph. That avoids Google/device calls but still pays PDF rendering and
OCR-preparation cost. The faster no-render replay seam now starts after OCR with
cached full-page normalized `OcrElement` pages, runs the downstream extraction
stages, writes summary/failure output through
`gocr_downstream_replay_test.dart`, and reports that it does not exercise
grid-line detection, crop-cell mapping, or DPI re-extraction.

Verification evidence so far: focused unit/analyze gates pass for the replay
seam, manifest contracts, row parser rescues, and quality gate. The existing
three-project OCR cache replay is still not an extraction pass: Berrien and
Grand Blanc pay-item counts/checksums fail expectations, and Huron Valley now
has a row-parser rescue path that can recover the 57-63 shifted tee sequence in
a stable 433-row grouping replay. The engine-level replay also exposed a cache
fingerprint mismatch path for Huron page 4 that had been swallowed as an empty
OCR page, producing a misleading 369-row grouping run; replay cache mismatches
now fail fatally instead of continuing with silent page loss. The no-render
replay runner reproduces failures quickly, which proves the faster iteration
loop is usable but also confirms the table structure/row grouping stage still
needs work before the replay gate can close. The corpus harness blocks
auto-accept when expected counts, item numbers, or fixture bid totals fail and
writes explicit `auto_accept_allowed` / `auto_accept_blocked` summary fields.
The production quality gate now also downgrades large internal
contiguous-sequence gaps such as 1-56/85-140 while leaving MDOT-style stepped
item codes alone. 2026-04-13 Springfield fresh Google Vision capture is green
again on Windows with 131/131 items, checksum `$7,882,926.73`, and strict
auto-accept gate pass. The original/custom Springfield pipeline is also green
on Windows with 131/131 items and the same checksum. Springfield cache replay is
green from the refreshed cache with 131/131 items and the same checksum; the
cache now keys exact request fingerprints, tolerates a single unambiguous
same-page image-byte drift with a warning, and still fails on ambiguous replay
entries instead of silently dropping pages into a partial run. MDOT stress pairs
and the S10 connected real-Google gate still need fresh capture/replay before
this lane is complete.

Do not create PDF-specific hacks. New rules must be general geometry,
classification, numeric, dictionary, or confidence heuristics. They must not
depend on file name, county, project name, known item count, or exact document
text.

## Research Notes

Google provider notes are captured in
`.codex/plans/2026-04-13-google-assisted-ocr-provider-plan.md`.

MDOT/AASHTOWare notes checked on 2026-04-13:

Detailed AASHTOWare pay-item and OpenAPI alignment notes are saved separately
in `.codex/research/2026-04-13-aashtoware-pay-item-alignment.md`.

- AASHTOWare OpenAPI is a gateway/API management platform for routing data to
  or from AASHTOWare applications. It is intended for licensed agencies and
  approved third parties through the AASHTOWare developer portal, not anonymous
  public data scraping.
  Source: https://www.aashtoware.org/story/what-is-aashtoware-openapi/
- The AASHTOWare OpenAPI architecture doc says OpenAPI does not host API
  implementations or store AASHTOWare application data; it routes requests to
  agency-hosted endpoints. That means a future integration needs credentials and
  agency enablement before it can serve as a live source of truth.
  Source: https://developer.aashtoware.org/content/html_widgets/nzq08.html
- The AASHTOWare developer portal FAQ says developers need an active license,
  portal account, authentication credentials, and network access to API
  endpoints. Treat this as a future integration lane, not a dependency for the
  current OCR extraction gate.
  Source: https://developer.aashtoware.org/content/html_widgets/t2qya.html
- MDOT's AASHTOWare wiki describes contract items as the awarded vendor's bid
  prices for contract items and shows that unattached/new items are selected
  from item data. This supports a future known-pay-item repository as a
  validation/ranking source.
  Source: https://mdotwiki.state.mi.us/aashtoware/index.php/Contract_Administration
- MDOT's Daily Work Reports wiki describes item postings as selected contract
  line numbers with units that self-populate before quantity entry. This maps
  to our eventual Field Guide workflow: imported bid items should become known
  contract items that make later quantity entry cleaner.
  Source: https://mdotwiki.state.mi.us/aashtoware/index.php/Daily_Work_Reports
- MDOT public bid letting surfaces and Schedule of Items PDFs are useful
  bid-item stress inputs because they vary table size, page count, schedule
  layout, bid-tab layout, bidder price columns, dense numeric columns, repeated
  headers, wrapped descriptions, and text proximity to table rules. They do not
  automatically provide paired M&P/spec sections, which is acceptable for this
  stress lane because M&P parsing is not the current bottleneck. For the first
  stress set, pair those public bid-item inputs with generated Measurement and
  Payment companion PDFs. Keep those generated companions out of the official
  acceptance corpus until matching real M&P/spec documents are available.
  Source: https://www.michigan.gov/en/mdot/Business/Contractors/bid-letting
- City of Ann Arbor public project manuals look promising for real acceptance
  candidates only if their pay-item/bid-form tables add table/grid stress not
  already covered by the corpus. The presence of `SECTION 01 22 00` is a useful
  pairing convenience, not the selection criterion. These should be downloaded,
  split into pay-item and M&P fixtures, counted, and validated before they enter
  the acceptance corpus.
  Sources:
  - https://www.a2gov.org/media/zlxedok1/itb_4679_document.pdf
  - https://a2gov.legistar.com/View.ashx?GUID=F5133C05-58E9-4040-8317-212C14FFC771&ID=14221033&M=F

## Corpus Plan

- [x] Keep Springfield as the protected 131-item regression gate.
- [x] Keep the three current prerelease project pairs:
  - `berrien_127449_us12`
  - `huron_valley_917245_dwsrf`
  - `grand_blanc_938710_sewer`
- [x] Add Springfield to the paired acceptance manifest while keeping its
  strict 131-item/checksum gate as the protected regression check:
  - `springfield_864130_dwsrf`
- [x] Add four public MDOT bid-tab stress pairs with generated M&P companions:
  - `mdot_2026_04_03_26_04001_bid_tab`
  - `mdot_2026_04_03_26_04003_bid_tab`
  - `mdot_2026_03_06_26_03001_bid_tab`
  - `mdot_2026_03_06_26_03002_bid_tab`
- [x] Add four public MDOT Schedule of Items stress pairs with generated M&P
  companions, sampled to 25 pay-item pages each:
  - `mdot_2026_04_03_estqua`
  - `mdot_2026_03_06_estqua`
  - `mdot_2025_12_05_estqua`
  - `mdot_2025_11_07_estqua`
- [x] Add four more real Michigan project pairs with both:
  - a bid-item/pay-item PDF, and
  - a matching or generated M&P/spec section PDF or equivalent
    measurement-and-payment document.
  - Select the pay-item side for stress coverage first:
    - multiple table sizes, including small and large row counts,
    - text touching or nearly touching grid/table rules,
    - dense numeric columns and bid amount/unit price fields,
    - wrapped descriptions and repeated page headers,
    - grid-line and non-grid schedule layouts,
    - scanned/image-heavy versus text-extractable PDFs,
    - enough page count variation to exercise tablet performance and review.
- [x] For each new paired project, record:
  - project id,
  - source URL or local provenance note,
  - pay-item PDF filename,
  - M&P PDF filename,
  - pay-item table/grid stress tags,
  - expected pay-item count,
  - expected item-number set or contiguous range,
  - expected bid amount total when available.
- [x] Promote the MDOT/AASHTOWare-style bid-item stress PDFs into the 12-pair
  acceptance set with generated M&P companions.
- [x] Use generated companion M&P PDFs for stress-pair coverage when the
  pay-item table is valuable but a matching real M&P/spec section is unavailable.
  Generated M&P content must not be used to hide pay-item table failures; it is
  supporting material for the paired flow, not the acceptance signal.

## AASHTOWare Pay-Item Repository Lane

This is useful, but it should not block the immediate OCR gate.

- [ ] Research whether the AASHTOWare OpenAPI Project endpoints available to us
  expose reference items, project items, contract items, contract project items,
  and bid history.
- [ ] If access is granted, design an import seam for known pay items with:
  - item number/code,
  - description,
  - unit,
  - spec book/version,
  - active/inactive status,
  - agency/source,
  - optional aliases and historical descriptions.
- [ ] Use the repository only after OCR/table parsing as a semantic validation
  and ranking signal:
  - normalize item descriptions,
  - flag impossible item-code/unit combinations,
  - repair low-confidence descriptions when item number and unit strongly match,
  - improve confidence issue explanations,
  - help M&P matching and later AASHTOWare export mapping.
- [ ] Do not use the repository to invent missing rows or override document
  values without a confidence-review flag. The PDF remains the source of truth
  for import.

## Fast Replay Runner Plan

- [x] Add a run-root setting such as `GOOGLE_OCR_RESEARCH_RUN_DIR`.
- [x] Route cache output under `<run_dir>/cache`.
- [x] Route compact summaries under `<run_dir>/summaries`.
- [x] Route failure buckets under `<run_dir>/failures`.
- [x] Route full stage traces under `<run_dir>/traces` only when explicitly
  requested.
- [x] Keep `.tmp/google_ocr_research/<run_id>` as the default local pattern.
- [x] Preserve existing per-harness override flags for compatibility.
- [x] Keep replay behind the production OCR engine adapter instead of a
  post-processing-only harness hook.
- [x] Add replay output fields:
  - provider/backend,
  - cache mode,
  - document key,
  - document kind,
  - elapsed time,
  - item count,
  - expected item count,
  - missing item numbers,
  - duplicate item numbers,
  - checksum expected/actual/delta,
  - quality status,
  - auto-accept allowed or blocked.
- [x] Add failure buckets:
  - missing item number,
  - duplicate item number,
  - nonnumeric item number,
  - checksum mismatch,
  - region/table span miss,
  - column shift,
  - row parser miss,
  - dedupe/remap issue,
  - M&P match miss.

## Cleanup Plan

- [x] Add a local cleanup command or script for `.tmp/google_ocr_research`.
- [x] Keep last N runs by default and remove older trace-heavy artifacts.
- [x] Add an S10 cleanup command for `/data/local/tmp/field_guide_pdf_corpus`
  and any run-root staging directory used by final tablet gates.
- [x] Document cleanup in `test/features/pdf/extraction/PDF_HARDENING.md`.

## Verification Gates

- [x] Unit tests:
  - `test/features/pdf/extraction/helpers/gocr_ocr_cache_test.dart`
  - `test/features/pdf/extraction/helpers/report_generator_test.dart`
  - `test/features/pdf/extraction/pipeline/stage_trace_diagnostics_test.dart`
  - Google Vision/Document AI OCR mapper and contract tests touched by the
    backend wiring.
  - `test/features/pdf/extraction/integration/mdot_public_pdf_corpus_manifest_test.dart`
- [ ] Local replay:
  - [x] Springfield 131-item gate.
    - 2026-04-13 fresh Google Vision capture gate passed on Windows:
      131/131 items, checksum `$7,882,926.73`, strict gate passed.
    - 2026-04-13 Custom Pipeline/original Springfield gate passed on Windows:
      131/131 items, checksum `$7,882,926.73`, strict gate passed.
    - 2026-04-13 replay against refreshed `.tmp/gocr_ocr_cache` passed on
      Windows: 131/131 items, checksum `$7,882,926.73`, strict gate passed.
    - 2026-04-13 cache replay no longer collapses same-page multi-attempt
      entries onto one key. Exact request fingerprints win; a single
      same-page/same-config image-byte drift replays with a warning; ambiguous
      drift fails with `OcrReplayException`.
  - [ ] Current three prerelease project pairs.
    - Existing cache replay currently fails extraction expectations, but fails
      closed with `reviewFlagged` instead of `autoAccept`.
    - 2026-04-13 Huron evidence: dimension/description shifted-cell parser
      rescue can recover item numbers 57-63 when the replay reaches the stable
      433-row grouping path; a separate 369-row grouping path was traced to a
      GOCR replay cache fingerprint mismatch on page 4 being swallowed as an
      OCR page failure. Replay cache mismatches now throw fatally so this cannot
      masquerade as a low-count extraction.
  - New 8-pair acceptance corpus once real documents and expectations exist.
  - MDOT bid-items-only stress set, when available.
- [ ] Connected tablet:
  - S10 real Google Assisted Pipeline run.
  - No OCR fallback.
  - No replay cache.
  - Output contained in a deletable device directory.
- [ ] Final review:
  - Confirm Custom Pipeline has no Google-only dependency.
  - Confirm Google Assisted Pipeline has one public company-facing mode.
  - Confirm all output is under deletable run roots.
  - Confirm auto-accept is blocked on corpus expectation failures.

## 2026-04-13 Testing Loop Audit

- [x] Confirmed the Windows integration replay harness is too slow for every
  rule tweak across the full stress set:
  - a single 25-page MDOT sample took about 95-101 seconds wall time including
    Windows build/startup and about 47-51 seconds inside extraction,
  - the seven-document cached pay-item batch was interrupted after about eight
    minutes while the Windows test executable was still running,
  - this is not a viable inner loop for OCR/table-rule iteration.
- [x] Confirmed the no-render downstream replay runner is much faster:
  - seven cached pay-item PDFs ran in about 31 seconds wall time,
  - the actual test body completed in about 4 seconds after Flutter test
    load/compile,
  - artifacts are contained under `.tmp/google_ocr_research/`.
- [ ] Bring the no-render replay runner into parity with the Windows replay
  before treating it as the main acceptance gate:
  - 2026-04-13 no-render replay produced different MDOT schedule results than
    the Windows replay path after the same header change,
  - likely cause: no-render replay bypasses page rendering/grid-line detection
    and page-analysis context used by the Windows pipeline,
  - next step is to compare stage summaries for Windows replay vs no-render
    replay on the same combined cache and either align the no-render seam or
    create a faster render-aware replay gate.
- [x] Reduce default trace cost:
  - avoid writing full 100MB+ traces on every run just because a run root is
    configured,
  - keep summaries/failure buckets on by default,
  - require an explicit trace flag or trace document filter for full stage
    payloads.
- [ ] Keep broad validation after every rule change:
  - fast gate: run all cached pay-item PDFs together through the no-render or
    equivalent fast replay harness,
  - parity gate: run the Windows replay harness across representative families
    until the fast replay runner is proven equivalent,
  - final gate: run connected S10 with real Google Assisted Pipeline and no
    replay cache.
