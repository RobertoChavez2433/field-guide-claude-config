# OCR Runtime Endpoint Refactor Plan

Date: 2026-04-06
Author: Codex
Status: Active
Scope: Refine the OCR page-worker execution boundary so the persistent worker pool is easier to extend, lower-overhead, and aligned with the proven Tesseract/Dart isolate model.

## Why This Plan Exists

The current branch already proved the right outer shape:
- persistent page workers beat same-build serial on S25
- `2` workers is the practical cap on the S25
- one Tesseract engine per worker with `OMP_THREAD_LIMIT=1` is viable

But the current worker protocol still carries too much per-document state in every page request:
- `OcrConfigV2` is repeated on every page message
- `tessdataPath` is repeated on every page message
- the strategy and class naming still imply a temporary proof rather than the chosen execution path

This plan narrows the next refactor to the worker endpoints themselves, not new OCR heuristics.

## Primary Sources Anchoring The Refactor

Tesseract:
- FAQ:
  https://github.com/tesseract-ocr/tesseract/wiki/FAQ/ec7f89630d433163f88ef98df058a02d00d9fdd3
- Release notes:
  https://github.com/tesseract-ocr/tesseract/wiki/ReleaseNotes/7d40c6ba2d3619a5185666be9f920845d5920925
- ImproveQuality:
  https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
- OpenMP oversubscription issue:
  https://github.com/tesseract-ocr/tesseract/issues/3109

Dart / Flutter:
- Dart isolates guide:
  https://dart.dev/language/isolates
- Flutter isolate performance guide:
  https://docs.flutter.dev/perf/isolates
- `TransferableTypedData`:
  https://api.dart.dev/dart-isolate/TransferableTypedData-class.html

## Current Pipeline Read

Relevant code:
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
- `lib/features/pdf/services/extraction/stages/ocr_page_recognition_executor.dart`
- `lib/features/pdf/services/extraction/stages/ocr_page_worker_proof_strategy.dart`
- `lib/features/pdf/services/extraction/stages/ocr_page_worker_runner.dart`
- `lib/features/pdf/services/extraction/stages/ocr_page_recognition_worker_payload.dart`
- `lib/features/pdf/services/extraction/stages/ocr_grid_page_recognition_stage.dart`

What the code currently does:
1. `TextRecognizerV2` chooses serial vs worker strategy.
2. The worker strategy builds a page DTO for every page.
3. Each page DTO currently includes both page data and document-invariant worker state.
4. The worker isolate owns a private `TesseractEngineV2`.
5. Inside each worker, page OCR is still serial at the cell and retry level.

What that implies:
- the outer concurrency boundary is already correct
- the next clean refactor point is the worker protocol, not intra-page cell concurrency
- the dominant remaining runtime cost is still OCR itself, but endpoint cleanup is the right prerequisite before deeper optimization

## New Measured Finding After Endpoint Instrumentation

Latest S25 Springfield debug-server run with `OCR_PAGE_WORKER_COUNT=2`:
- scorecard verdict: `PASS (0 regressions)`
- `131/131`
- exact checksum preserved
- no bogus rows
- total duration: `120s`
- `text_recognition`: `100715 ms`

New worker metrics from that run:
- `ocr_page_worker_bootstrap_ms = 11`
- `ocr_page_worker_batch_elapsed_ms = 100639`
- `ocr_page_worker_total_round_trip_ms = 171276`
- `ocr_page_worker_total_execute_ms = 171238`
- `ocr_page_worker_total_estimated_queue_ms = 38`
- `ocr_page_worker_max_estimated_queue_ms = 17`

Interpretation:
- worker bootstrap cost is negligible
- queueing / transport overhead is negligible
- round-trip time is effectively identical to worker-side execute time
- the persistent pool is no longer the bottleneck worth optimizing first

That means the next runtime phase must target page-local execution cost:
- OCR call volume per page
- page-local crop/recognition work shape
- possibly a row-banded or other lower-call-count recognition path

It should not begin with:
- more worker-count experiments
- more worker transport redesign
- more isolate bootstrap work

## Measured Constraints To Preserve

Protected gates:
- `131/131` Springfield items
- exact checksum `$7,882,926.73`
- no bogus rows
- no regression in the active S25 worker path

Known runtime context from prior checkpoint:
- persistent `2`-worker pool on S25: about `90s`
- serial control on same build/device: about `98s`
- persistent `3`-worker pool: regressed

## In Scope

- promote the page-worker path from “proof” semantics to the intended runtime path
- split worker bootstrap state from per-page work payloads
- reduce repeated transport of document-invariant worker inputs
- keep page ordering, fallback behavior, and fidelity unchanged
- add just enough observability to reason about worker endpoint costs

## Out Of Scope

- switching OCR engines
- introducing PaddleOCR or platform-specific OCR backends
- cell-level parallel OCR inside one worker
- global DPI retuning
- raw-grid visual gating expansion
- native text extraction as the primary Springfield path

## Endpoint Shape We Want

Main isolate responsibilities:
- build document-level worker initialization state once
- build page payloads with only page-specific data
- own worker-count selection and strategy fallback

Worker bootstrap responsibilities:
- receive invariant worker initialization once
- prime tessdata path once
- create one private Tesseract engine once
- reuse the same executor/engine for all assigned pages

Per-page message responsibilities:
- carry only page-specific image and grid payloads
- return only the page result snapshot needed for deterministic merge and metrics

## Completion Gates

Architecture gates:
- one explicit worker-init DTO exists
- per-page DTO no longer carries document-invariant config/tessdata fields
- the pool strategy naming reflects that this is the chosen runtime path

Correctness gates:
- payload round-trip tests still pass
- strategy fallback tests still pass
- no regression in page ordering or failure handling

Performance gates:
- no expected runtime regression from the endpoint refactor
- endpoint logs clearly separate invariant bootstrap state from page payload flow

## Expected Next Work After This Refactor

Only after this endpoint cleanup is done should the next runtime slice begin:
1. add worker-side timing visibility for queue wait vs page OCR cost
2. identify whether the next cut belongs in preprocessing or per-page OCR cost
3. pursue sub-`60s` with measured bottleneck data, not worker-boundary guesswork
