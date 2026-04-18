# Google Assisted OCR Provider Plan - 2026-04-13

## Decision

Keep exactly two company-facing pipelines:

- Custom Pipeline: local/internal extraction only. It must not call Google
  Vision, Document AI, or any other cloud OCR provider.
- Google Assisted Pipeline: one company opt-in mode. It may internally run
  Google Cloud Vision, Document AI Enterprise Document OCR, Document AI Layout
  Parser, or a later Google backend, but those are backend strategies, not
  separate company modes.

The next implementation step is a provider bakeoff, not another row parser
rewrite. The default candidate remains Google Cloud Vision image OCR because it
is already wired and was closer on the S10 corpus. The first new candidate to
add is Document AI Enterprise Document OCR, not Form Parser. Form Parser stays
an experiment because it is substantially more expensive and intended for
form/KVP extraction rather than our bid-table-first use case.

## Research Artifacts

Official Google sources checked on 2026-04-13:

- Cloud Vision pricing:
  https://cloud.google.com/vision/pricing
  - Relevant finding: pricing is per image/page; PDF pages count as individual
    images. Document Text Detection has the first 1,000 units/month free and is
    $1.50 per 1,000 units for the next tier.
- Cloud Vision PDF/file OCR:
  https://cloud.google.com/vision/docs/file-small-batch
  - Relevant finding: `files:annotate` can synchronously OCR a PDF/TIFF/GIF
    file for up to five pages per request, while async file annotation supports
    larger PDF jobs through Cloud Storage. This should be tested because our
    current Vision path sends rendered page images, not raw PDF pages.
- Cloud Vision data usage:
  https://cloud.google.com/vision/docs/data-usage
  - Relevant finding: online image data is processed in memory and Google says
    customer content is not used to train Cloud Vision.
- Document AI pricing:
  https://cloud.google.com/document-ai/pricing
  - Relevant finding: Enterprise Document OCR is $1.50 per 1,000 pages, Layout
    Parser is $10 per 1,000 pages, and Form Parser / Custom extractor are $30
    per 1,000 pages for the first 1,000,000 pages/month.
- Document AI Enterprise Document OCR:
  https://cloud.google.com/document-ai/docs/enterprise-document-ocr
  - Relevant finding: this is the low-cost Document AI OCR processor. It
    supports PDF/image formats, page-range processing, language hints, image
    quality analysis, native PDF parsing, and processor version pinning.
- Document AI Form Parser:
  https://cloud.google.com/document-ai/docs/form-parser
  - Relevant finding: this is an extraction processor for forms and simple
    tables. It is not up-trainable and should not be the default for our
    multi-page pay-item tables unless bakeoff data proves it wins.
- Document AI Layout Parser:
  https://cloud.google.com/document-ai/docs/layout-parse-chunk
  - Relevant finding: this is table/layout oriented and may help if OCR text is
    good but table structure remains bad, but it costs more than Vision or
    Enterprise Document OCR and current Gemini-backed versions have region/data
    residency caveats that must be reviewed before production use.
- Document AI security:
  https://cloud.google.com/document-ai/docs/security
  - Relevant finding: Google says Document AI customer documents/predictions are
    not used to train Document AI models. Online processing is in-memory and not
    persisted to disk, aside from request metadata.

Current repo and test artifacts:

- `.codex/research/2026-04-12-ocr-vendor-decision.md` previously selected
  Google first and Vision first, with Document AI as an escalation path.
- `test/features/pdf/extraction/PDF_HARDENING.md` already defines the faster
  capture/replay loop and warns that device testing is the final gate.
- `integration_test/pre_release_pdf_corpus_test.dart` and
  `integration_test/springfield_report_test.dart` already support internal
  Google-assisted backend selection and cache capture/replay.
- `scripts/verify_google_cloud_ocr_readiness.ps1` verifies the two Google Edge
  Functions and the shared company opt-in guard.
- `supabase/functions/google-cloud-vision-ocr/index.ts` is the existing Vision
  image-page path.
- `supabase/functions/google-document-ai-ocr/index.ts` is currently a generic
  Document AI process call. The processor type is configured by secret, so the
  code cannot assume Form Parser behavior.
- `lib/features/pdf/services/extraction/ocr/ocr_engine_factory.dart` preserves
  one public Google Assisted mode with internal backend selection.

Measured corpus evidence from the connected S10 and Windows loop:

- S10 Document AI current processor run completed all three new pay-item PDFs
  but missed the gates:
  - Berrien: 137/200 items, checksum 3329994.15 vs 7467543.00.
  - Huron: 128/140 items, checksum 8823546.50 vs 10531942.76.
  - Grand Blanc: 101/118 items, checksum 4524608.14 vs 7918199.14.
- S10 Vision image-page run was closer but still failed:
  - Berrien: 164/200 items, checksum 1227836.25 vs 7467543.00.
  - Huron: 139/140 items, checksum 10504262.76 vs 10531942.76.
  - Grand Blanc: 113/118 items, checksum 7007444.14 vs 7918199.14.
- Windows Vision Berrien trace reproduced the S10 Vision count at 164/200. The
  trace showed item-number tokens shifted into other column roles, so the next
  parser work must be provider-profiled and trace-driven, not PDF-specific.
- There is an uncommitted exploratory change in
  `lib/features/pdf/services/extraction/stages/row_parsing_workflow.dart` that
  improved one Berrien Vision run from 164 to 184 items but is not accepted
  design yet. Treat it as scratch until the provider bakeoff chooses the input
  shape we are optimizing for.

## Provider Strategy

1. Keep Vision image OCR as baseline.
   - It is already deployed and least disruptive.
   - It is low-cost and closest on the S10 gate so far.
   - Its weakness appears to be geometry/column assignment after OCR, so parser
     profiling is still necessary.

2. Add a Vision raw-PDF backend experiment.
   - Use `files:annotate` for up to five pages per request, chunking our pay
     item ranges as needed.
   - Store output in the same GOCR cache format and same `.tmp` report tree.
   - This tests whether provider-side PDF handling gives better geometry than
     our current render-to-PNG-per-page path.

3. Add a Document AI Enterprise Document OCR bakeoff before more Form Parser
   work.
   - Configure a separate Enterprise Document OCR processor in Google Cloud.
   - Use the existing `google-document-ai-ocr` function with the Enterprise OCR
     processor ID where possible.
   - Enable relevant OCR config only when it is generally applicable:
     `enableNativePdfParsing` for raw PDFs, language hint `en`, image quality
     score for diagnostics, and page ranges to avoid processing unneeded pages.

4. Keep Document AI Form Parser as an experiment, not default.
   - It may help with simple tables, but at $30/1,000 pages it needs to beat
     Vision and Enterprise OCR materially on the exact corpus gates.
   - Do not design parser rules around Form Parser-specific table output unless
     bakeoff data proves that is the winning backend.

5. Consider Document AI Layout Parser only after the cheaper OCR routes fail.
   - It is more table-aware than plain OCR and may solve column alignment.
   - It is more expensive than Vision/Enterprise OCR, and region/data-residency
     notes for newer Gemini-backed versions must be reviewed before production.

## Boilerplate And Table Extraction Policy

Do not remove boilerplate before Google OCR as the default. Give the provider
full page context, then suppress headers, footers, legends, and non-table rows
in provider-specific post-processing. Pre-OCR cropping is allowed only for
general, geometry-derived page ranges/regions after trace evidence shows that
full-page OCR hurts a backend. No rules may depend on a filename, project name,
known item count, county name, or exact PDF text.

The Google Assisted Pipeline may reuse custom pipeline post-processing when the
contract is provider-neutral. Google-specific parser profiles can be added for
coordinate normalization, row classification, table-cell flattening, and
confidence review. The Custom Pipeline must not import or depend on Google-only
adapters.

## Implementation Plan

1. Clean up docs and readiness wording.
   - Remove wording that implies the Document AI backend is Form Parser by
     default.
   - Document the recommended bakeoff order: Vision image, Vision raw PDF,
     Document AI Enterprise OCR, Form Parser, Layout Parser.

2. Add backend metadata to the Google Assisted harness.
   - Capture provider, provider route, processor type/config, request unit
     estimate, page count, and elapsed time in the OCR cache/report output.
   - Keep all outputs under `.tmp/google_ocr_research/<run-id>/` or the existing
     caller-provided `.tmp` directories.

3. Add a raw-PDF provider seam.
   - Introduce an internal backend name for Vision raw-PDF testing without
     changing the company-facing `cloud_ocr_mode`.
   - Keep the final parser input as normalized `OcrElement` values so the same
     corpus gates can compare providers.

4. Add Enterprise Document OCR configuration support.
   - Keep credentials and processor IDs server-side.
   - Add a processor/profile env value such as `DOCUMENT_AI_PROCESSOR_TYPE` for
     diagnostics and future routing, without exposing it as a company mode.
   - Add contract tests so Document AI remains behind the same Google Assisted
     authorization guard.

5. Run provider bakeoff locally first.
   - Capture real Google responses once.
   - Replay from cache for parser iteration.
   - Compare the three new pay-item PDFs and the Springfield 131 baseline.

6. Only then decide parser changes.
   - If provider output is good but row assignment is bad, create a Google
     Assisted post-processing profile.
   - If raw provider output is bad, change provider/config before adding parser
     heuristics.
   - Promote or discard the existing `row_parsing_workflow.dart` scratch patch
     based on replay evidence.

7. Final gate on connected S10.
   - Run the three new pay-item PDFs and Springfield through the real Google
     Assisted Pipeline, no OCR fallback and no replay cache.
   - Keep device test artifacts in a deletable directory and avoid permanent
     S10 bloat.

## Acceptance Criteria

- Company-facing configuration still exposes only Custom Pipeline and Google
  Assisted Pipeline.
- Custom Pipeline has no Google Vision or Document AI dependency.
- Google Assisted internal backends are traceable in reports/cache metadata.
- Three new pay-item PDFs meet expected item counts and bid-amount checksums.
- Springfield still extracts all 131 original items.
- No OCR fallback is used in the Google Assisted test path.
- The S10 final gate passes with real Google calls, not replay.
- Lint/contract tests prevent accidental cross-wiring between the custom and
  Google-assisted pipelines.
