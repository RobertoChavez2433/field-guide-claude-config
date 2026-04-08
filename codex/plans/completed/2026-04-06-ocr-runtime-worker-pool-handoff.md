Date: 2026-04-06
Author: Codex
Status: Checkpoint / Session Handoff
Scope: OCR/PDF extraction runtime optimization for Springfield on Android, with fidelity held at `131/131`, exact checksum, and no bogus rows.

## Executive Summary

This session moved the OCR optimization work from speculative tuning into a measured, source-backed execution-model change.

What is now true:
- the Springfield Android extraction remains green at:
  - `131/131`
  - exact checksum `$7,882,926.73`
  - no bogus rows
- the previous short-lived page-worker approach was replaced with a persistent OCR worker pool
- the persistent `2`-worker pool on the S25 is the first worker shape that beats same-build serial
- `3` workers still regress on the S25
- the sub-`60s` goal remains open and will require more than just workerization

Best measured same-build results on `sm-s938u`:

| Mode | Result | Total | Text Recognition | Notes |
|------|--------|------:|-----------------:|-------|
| Persistent pool, `2` workers | `131/131` | `90s` | `70831 ms` | Best live worker result |
| Serial control | `131/131` | `98s` | `77655 ms` | Same build, same device |
| Persistent pool, `3` workers | `131/131` | `110s` | `83555 ms` | Regressed from `2` workers |

Core conclusion:
- the right endpoint shape is now validated:
  - render/preprocess on main isolate
  - OCR-only worker isolates
  - one Tesseract engine per worker
  - serial OCR inside each worker
  - `OMP_THREAD_LIMIT=1`
  - bounded worker count
  - dynamic page scheduling

Update after the endpoint instrumentation refactor:
- worker bootstrap and queue overhead were measured directly on the S25 pooled path
- they are negligible compared with worker execute time
- the next runtime phase should target page-local OCR cost rather than more worker-pool tuning

Latest measured worker metrics on `sm-s938u` with `2` workers:
- `ocr_page_worker_bootstrap_ms = 11`
- `ocr_page_worker_batch_elapsed_ms = 100639`
- `ocr_page_worker_total_round_trip_ms = 171276`
- `ocr_page_worker_total_execute_ms = 171238`
- `ocr_page_worker_total_estimated_queue_ms = 38`
- `ocr_page_worker_max_estimated_queue_ms = 17`

Interpretation:
- bootstrap is not meaningful at Springfield scale
- request transport is not the runtime bottleneck
- page-local execute time is now the bottleneck to attack

## Problem Statement

The original target was to drive Springfield runtime below `60s` without losing quality.

The non-negotiable quality constraints were:
- retain `131` extracted items
- retain exact checksum `$7,882,926.73`
- produce no bogus rows
- avoid visual regression

The local runtime data showed early that OCR was the dominant cost center:
- `text_recognition` consumed roughly `80%` of wall time on Android
- parser and retry logic were not the main bottleneck
- broad parser rewrites or retry trimming could not plausibly deliver the stretch target

That forced the work toward two tracks:
1. protect quality first
2. then attack OCR execution cost structurally

## What Was Done

### 1. Protected the Springfield baseline

Recovered and then locked the green Springfield path by:
- adding a strict Springfield gate to the integration harness
- protecting the item-number crop lane
- forcing retry for alpha-contaminated item numbers such as `62 B`
- retaining `classify_enable_learning=0` for pooled Tesseract consistency

Important regression that was diagnosed and fixed:
- item `9` could disappear
- item `62` could become `62 B`
- one bogus row could appear downstream

This work restored:
- `131/131`
- exact checksum
- no bogus rows

### 2. Rejected low-signal runtime experiments

Several experiments were run and intentionally rejected:
- wide-description fallback
- first-pass structured whitelists
- higher worker counts without a better boundary

Why they were rejected:
- they either slowed the pipeline down
- or reintroduced correctness regressions
- or both

### 3. Refactored `TextRecognizerV2` execution seams

The OCR path was separated into cleaner responsibilities:
- `TextRecognizerV2` became the orchestration layer
- per-page execution moved into `OcrPageRecognitionExecutor`
- a strategy seam was introduced above the executor
- isolate-safe worker request/result DTOs were added

This removed the need to keep concurrency logic embedded in the stage orchestrator and made worker experiments much safer.

### 4. Diagnosed the original worker hang correctly

The first page-worker attempt on device hung during `text_recognition`.

The root cause was not “Tesseract concurrency is wrong.”
The root cause was local native wrapper behavior in `flusseract`:
- native stdout/stderr capture used `dup2()` on process-global file descriptors
- that is unsafe when multiple OCR calls run concurrently inside one process

Fix applied:
- disabled native stdout/stderr capture on Android and Windows in `packages/flusseract/src/logfns.h`

This was a critical finding because it changed the direction from:
- “worker OCR is probably not viable”
to:
- “the high-level concurrency model is still valid, but the native wrapper had a concurrency bug”

### 5. Proved short-lived workers were the wrong boundary

After the native fix, short-lived worker batches were able to complete correctly, but they were still not good enough:
- `1x1` proved correctness only and was too slow
- `2x3` was the best short-lived worker shape, but still slower than the earlier protected serial baseline
- `3x2` regressed further

This matched the isolate research:
- repeated short-lived workers have too much setup/transport overhead for repeated OCR work

### 6. Replaced batch `compute()` workers with a persistent worker pool

Implemented a persistent worker path using:
- `Isolate.spawn`
- startup handshake
- request ids
- response correlation
- explicit shutdown
- `TransferableTypedData` for page bytes
- one Tesseract engine per worker
- dynamic page scheduling to the next available worker

This is the key architectural result of the session.

## Research Completed

### Tesseract guidance

Primary sources used:
- FAQ:
  https://github.com/tesseract-ocr/tesseract/wiki/FAQ/ec7f89630d433163f88ef98df058a02d00d9fdd3
- Release notes:
  https://github.com/tesseract-ocr/tesseract/wiki/ReleaseNotes/7d40c6ba2d3619a5185666be9f920845d5920925
- ImproveQuality:
  https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
- OpenMP oversubscription discussion:
  https://github.com/tesseract-ocr/tesseract/issues/3109

Key takeaways:
- for many images, the recommended outer-parallel shape is effectively one OCR worker per core with `OMP_THREAD_LIMIT=1`
- repeated reuse of one OCR API instance can be affected by adaptive learning, which is why `classify_enable_learning=0` was retained
- “thread-safe” does not mean “share one mutable engine across workers”
- Tesseract is weak at table recognition on its own, so custom segmentation plus page-level concurrency above that segmentation is the right direction

### Dart / Flutter isolate guidance

Primary sources used:
- Dart isolate guide:
  https://dart.dev/language/isolates
- Flutter isolate performance guide:
  https://docs.flutter.dev/perf/isolates
- `TransferableTypedData` API:
  https://api.dart.dev/dart-isolate/TransferableTypedData-class.html

Key takeaways:
- repeated short-lived isolates are not the best shape for repeated heavy work
- Flutter explicitly points toward stateful / longer-lived isolates for ongoing workloads
- Dart’s robust long-lived-worker pattern uses:
  - `Isolate.spawn`
  - ports
  - request ids
  - `Completer` correlation
  - explicit close / shutdown
- `TransferableTypedData` is appropriate for high-volume byte transport

### Community / practical OCR guidance

Source:
- https://groups.google.com/g/tesseract-ocr/c/Wdh_JJwnw94

Key takeaway:
- character pixel size matters more than just nominal DPI
- more pixels are not automatically better

This remains relevant for future post-pool OCR tuning.

## Code Changes Made

Primary OCR runtime files:
- [text_recognizer_v2.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart)
- [ocr_page_recognition_executor.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/ocr_page_recognition_executor.dart)
- [ocr_page_recognition_worker_payload.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/ocr_page_recognition_worker_payload.dart)
- [ocr_page_worker_proof_strategy.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/ocr_page_worker_proof_strategy.dart)
- [ocr_page_worker_runner.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/ocr_page_worker_runner.dart)

Native wrapper fix:
- [logfns.h](C:/Users/rseba/Projects/Field_Guide_App/packages/flusseract/src/logfns.h)

Tests added or extended:
- [ocr_page_recognition_worker_payload_test.dart](C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/ocr_page_recognition_worker_payload_test.dart)
- [ocr_page_worker_proof_strategy_test.dart](C:/Users/rseba/Projects/Field_Guide_App/test/features/pdf/extraction/stages/ocr_page_worker_proof_strategy_test.dart)

## Measured Results

### Earlier protected baseline context

Before the persistent pool:
- green serial S25 runs were generally around `94-98s`
- best short-lived worker path was still worse than serial

### Same-build comparison after the pool refactor

Persistent `2`-worker pool:
- `131/131`
- exact checksum
- no bogus rows
- `90s` total
- `70831 ms` text recognition
- `ocr_page_workers_used = true`
- `ocr_page_worker_count = 2`
- `ocr_page_worker_fallbacks = 0`

Serial control:
- `131/131`
- exact checksum
- no bogus rows
- `98s` total
- `77655 ms` text recognition
- `ocr_page_workers_used = false`

Persistent `3`-worker pool:
- `131/131`
- exact checksum
- no bogus rows
- `110s` total
- `83555 ms` text recognition

Interpretation:
- persistent workers are now a real runtime win
- `2` workers is the practical cap for the S25
- `3` workers increase contention and regress

## What This Means

### Proven

- the Tesseract-backed concurrency path is viable in this codebase
- the original worker hang was implementation-specific, not a dead-end in principle
- the persistent worker pool is better than same-build serial on device
- the source-backed architecture choice was correct

### Not yet solved

- sub-`60s`
- strict machine enforcement of raw-grid / visual stability at the intermediate artifact layer
- broader variance characterization across many repeated pooled runs

## Residual Risks

### 1. Final extraction is green, but raw-grid artifacts can still be imperfect

The final report is correct, but the intermediate OCR-grid output can still show recoverable anomalies that downstream parsing repairs.

Implication:
- the hard gate currently proves final extraction fidelity
- it does not fully prove raw-grid visual fidelity

If “no visual regression” must also cover intermediate grid artifacts, then a stronger visual comparator is still needed.

### 2. Worker count is device-sensitive

The S25 strongly prefers `2` workers.
There is no evidence that simply increasing concurrency will help further.

### 3. Workerization alone will not hit `<= 60s`

The pool refactor won the first structural runtime battle, but the remaining gap is still large.

## Intended Direction From Here

If this work resumes later, the next phase should not start by redesigning workers again.
The worker boundary is now good enough to treat as the current best execution model.

Recommended next direction:

1. Keep the persistent `2`-worker pool as the active runtime candidate on S25.
2. Add stronger comparison for raw-grid / visual stability if that requirement remains strict.
3. Measure repeated pooled runs to quantify variance under comparable thermal conditions.
4. Attack the next runtime tier below the worker boundary:
   - reduce OCR cost per page
   - reduce preprocessing cost
   - preserve the protected item-number lane
5. Avoid more worker-count experimentation unless new device evidence appears.

Potential future workstreams:

### Workstream A: Raw-grid fidelity enforcement

Goal:
- make “no visual regression” machine-enforced, not implied by final item correctness

Possible work:
- compare clean-grid / OCR-grid artifacts against protected baselines
- add targeted checks for historically risky rows and columns

### Workstream B: Post-pool OCR input tuning

Goal:
- reduce OCR cost without reopening known item-number failures

Likely direction:
- geometry-aware scaling
- selective lane protection
- avoid global DPI changes that hurt narrow numeric cells

### Workstream C: Preprocessing cost reduction

Goal:
- lower the `~13-20s` preprocessing range without quality loss

### Workstream D: Better pooled-run observability

Goal:
- make future tuning faster and less ambiguous

Possible work:
- per-worker timings
- per-page dispatch timings
- queue wait vs OCR execution time

## Verification Completed This Session

Local verification:
- `flutter test test/features/pdf/extraction/stages/ocr_page_recognition_worker_payload_test.dart`
- `flutter test test/features/pdf/extraction/stages/ocr_page_worker_proof_strategy_test.dart`
- `dart analyze` on touched OCR worker files

Device verification on S25 using debug server:
- persistent `2`-worker pool Springfield run
- same-build serial control Springfield run
- persistent `3`-worker pool Springfield run

All three preserved:
- `131/131`
- exact checksum
- no bogus rows

## Recommended Resume Point

When this work resumes, start from:
- [2026-04-06-pdf-ocr-runtime-findings.md](C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-06-pdf-ocr-runtime-findings.md)
- [2026-04-06-pdf-ocr-runtime-stabilization-plan.md](C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-06-pdf-ocr-runtime-stabilization-plan.md)
- [2026-04-06-pdf-ocr-runtime-todo.md](C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-06-pdf-ocr-runtime-todo.md)
- [2026-04-06-ocr-worker-pool-refactor-plan.md](C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-06-ocr-worker-pool-refactor-plan.md)
- [2026-04-06-ocr-worker-pool-refactor-todo.md](C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-06-ocr-worker-pool-refactor-todo.md)

Recommended first action on resume:
- decide whether the next goal is:
  - stricter raw-grid visual enforcement, or
  - pure runtime reduction below the new `~90s` pooled result

That decision should determine the next implementation slice.
