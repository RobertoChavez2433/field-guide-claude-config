Date: 2026-04-06
Owner: Codex
Status: Active
Scope: Replace the short-lived page-worker proof with a persistent OCR worker pool aligned to Tesseract and Dart isolate guidance.

## Objective

Refactor the OCR worker path so it uses long-lived bounded workers instead of repeated `compute()` batches, while preserving the protected Springfield baseline:

- `131/131`
- exact checksum `$7,882,926.73`
- no bogus rows
- no visual regression

The first success criterion for this refactor is not sub-`60s`.
It is:
- stable worker execution on the S25
- no worker hangs
- no regression from the protected baseline
- a measurable improvement over the current short-lived worker path

## Why This Refactor

Local evidence:
- short-lived `compute()` workers now complete after the `flusseract` fix
- best short-lived worker run on S25 is still only about `106s` total / `85.8s` text recognition
- earlier protected serial S25 runs are still better at about `94-95s` total / `~75-76s` text recognition
- fixed `2x3` chunking also leaves visible skew between workers

Source-backed reasons:
- Tesseract guidance supports bounded outer parallelism with isolated engine instances and `OMP_THREAD_LIMIT=1`
- Flutter guidance recommends stateful, longer-lived isolates for repeated work instead of repeated short-lived isolates
- Dart’s robust isolate pattern recommends explicit ports, request IDs, and shutdown handling
- `TransferableTypedData` is the right transport for page PNG bytes

Primary references:
- Tesseract FAQ:
  https://github.com/tesseract-ocr/tesseract/wiki/FAQ/ec7f89630d433163f88ef98df058a02d00d9fdd3
- Tesseract release notes:
  https://github.com/tesseract-ocr/tesseract/wiki/ReleaseNotes/7d40c6ba2d3619a5185666be9f920845d5920925
- ImproveQuality:
  https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
- Oversubscription issue:
  https://github.com/tesseract-ocr/tesseract/issues/3109
- Dart isolates:
  https://dart.dev/language/isolates
- Flutter isolate performance:
  https://docs.flutter.dev/perf/isolates
- `TransferableTypedData`:
  https://api.dart.dev/dart-isolate/TransferableTypedData-class.html

## Target Endpoint Shape

Main isolate:
- render and preprocess pages
- create compact page OCR requests
- spawn and own a bounded worker pool for the recognition session
- schedule work to the next available worker
- merge results by page index
- emit stage metrics and debug logs

Worker isolate:
- own one private Tesseract engine
- process one OCR request at a time
- return one compact recognized-page snapshot per request
- shut down explicitly

Request contract:
- `request_id`
- one page OCR request
- `TransferableTypedData` for page bytes
- compact structural metadata only

Response contract:
- `request_id`
- one recognized-page snapshot or structured transport error
- no verbose per-cell diagnostics on the hot path

Pool behavior:
- bounded worker count, starting at `2` on S25
- serial OCR inside each worker
- dynamic assignment to the next available worker
- serial fallback if pool creation or worker transport fails

## Refactor Stages

### Stage 1: Worker Client Boundary

- replace the batch `workerRunner` callback with a worker-client/session abstraction
- keep `TextRecognizerV2` focused on orchestration
- keep serial strategy as the default protected path

### Stage 2: Persistent Worker Pool

- implement long-lived worker isolates with `Isolate.spawn`
- use startup handshake plus explicit shutdown
- correlate responses with request IDs
- keep one engine per worker

### Stage 3: Dynamic Scheduling

- stop sending coarse fixed chunks as the only worker unit
- schedule the next available page to the next available worker
- preserve deterministic output ordering by page index

### Stage 4: Validation

- targeted unit tests for:
  - worker-client lifecycle
  - response correlation
  - serial fallback on transport failure
  - deterministic output ordering
- `dart analyze` on touched OCR files
- Springfield rerun on the S25 with debug-server tracing

## Current Result

Completed benchmark outcomes on `sm-s938u`:
- persistent `2`-worker pool:
  - `131/131`
  - exact checksum
  - no bogus rows
  - about `90s` total
  - about `70831 ms` text recognition
- same-build serial control:
  - `131/131`
  - exact checksum
  - no bogus rows
  - about `98s` total
  - about `77655 ms` text recognition
- persistent `3`-worker pool:
  - `131/131`
  - exact checksum
  - no bogus rows
  - about `110s` total
  - about `83555 ms` text recognition

Current conclusion:
- the refactor succeeded
- the persistent `2`-worker pool is the correct endpoint shape so far
- the next phase is no longer worker viability; it is post-pool optimization and stronger visual-stability enforcement

## Risks

- worker lifecycle bugs can strand pending requests
- worker exit/error handling can hide failures if the request map is not drained correctly
- verbose diagnostics removal can accidentally drop metrics needed by the harness
- per-page dispatch can improve balance but still lose if transport overhead remains too high

## Exit Criteria

- S25 Springfield remains green
- worker pool completes without hangs
- measured worker pool runtime beats the current short-lived worker path
- if it does not beat the protected serial baseline, keep it non-default and continue tightening the worker boundary before broader rollout
