Date: 2026-04-06
Author: Codex
Status: Session Handoff
Branch: `codex/ocr-per-page-runtime-isolation`
Base Branch: `sync-engine-refactor`
Scope: Continue the OCR/PDF extraction runtime refactor in isolation from the rest of the team, with Springfield fidelity locked and the next work focused on page-local OCR cost.

## Executive Summary

This branch exists because the OCR runtime work has crossed the point where it should no longer share an active integration branch with unrelated sync/pay-app work.

What is already proven:
- Springfield remains green on the active OCR path:
  - `131/131`
  - exact checksum `$7,882,926.73`
  - no bogus rows
- the correct outer concurrency model is already validated:
  - persistent OCR-only workers
  - one Tesseract engine per worker
  - serial OCR inside each worker
  - `OMP_THREAD_LIMIT=1`
  - bounded worker count
- the persistent `2`-worker pool on the S25 is better than same-build serial
- worker bootstrap, queueing, and transport overhead are now measured and negligible

What is not yet solved:
- sub-`60s`
- a lower-call-count per-page recognition shape that preserves Springfield fidelity
- strict automated raw-grid visual gating at the intermediate artifact layer

Core conclusion at handoff:
- the next real runtime win must come from reducing page-local OCR work
- more worker-boundary tuning is no longer the highest-value path

## Current Branch State

Current branch for future OCR work:
- `codex/ocr-per-page-runtime-isolation`

Why this branch was created:
- isolate the OCR runtime refactor from the shared `sync-engine-refactor` branch
- allow page-local OCR experiments without interfering with the ongoing sync/pay-app work
- keep future OCR tuning and failed experiments contained

## Important Commits Already On This Line

- `7491fc02` `Fix flusseract stream capture for concurrent OCR`
- `f7f0bf08` `Refactor OCR page recognition into a worker pool`
- `fc3762b3` `Refine OCR page pool worker endpoints`

Those three commits are the current architectural baseline for the OCR runtime path.

## What Was Completed Before This Handoff

### 1. Fidelity was re-protected

The branch recovered and locked the Springfield path after earlier OCR regressions:
- item-number lane was protected
- alpha-contaminated item numbers force retry
- strict Springfield correctness gates were added
- `classify_enable_learning=0` was retained for pooled OCR stability

Protected acceptance state:
- `131/131`
- exact checksum
- no bogus rows

### 2. The original worker failure was root-caused correctly

The first concurrent worker implementation was hanging because `flusseract` used process-global stdout/stderr capture around native OCR calls.

Fix:
- Android and Windows stream capture were disabled in the native wrapper

This matters because it proved the real conclusion was:
- the worker idea was right
- that wrapper implementation was wrong

### 3. Short-lived worker batches were rejected

Short-lived `compute()`-style page workers were not the right boundary:
- too much lifecycle overhead
- too much payload transport overhead
- not competitive against the protected serial baseline

### 4. Persistent workers were implemented and validated

The runtime path now uses:
- long-lived isolates
- startup handshake
- request IDs
- response correlation
- explicit shutdown
- `TransferableTypedData`
- one private Tesseract engine per worker
- dynamic page dispatch to the next available worker

### 5. The worker endpoint shape was cleaned up

The active page-worker path was refactored so document-invariant worker state is sent once and page-local state is sent per request.

Important result:
- the “proof” path is no longer framed as a throwaway prototype
- the worker endpoint is now clean enough to stop being the main refactor target

### 6. Worker overhead was measured directly

Latest measured S25 Springfield run on the pooled path:
- `131/131`
- exact checksum
- no bogus rows
- total duration `120s`
- `text_recognition = 100715 ms`
- `image_preprocessing = 13630 ms`
- `ocr_page_worker_bootstrap_ms = 11`
- `ocr_page_worker_total_estimated_queue_ms = 38`
- `ocr_page_worker_total_round_trip_ms = 171276`
- `ocr_page_worker_total_execute_ms = 171238`

Interpretation:
- bootstrap is negligible
- queue time is negligible
- transport is negligible
- execute time inside each worker is the real bottleneck

## Current Measured OCR Shape

Springfield S25 pooled run metrics:
- `planned_cell_crops = 822`
- `prepared_crop_count = 822`
- `total_ocr_calls = 854`
- `re_ocr_attempts = 20`
- `re_ocr_successes = 2`
- `psm6_calls = 42`
- `psm7_calls = 780`
- `psm8_calls = 13`
- `psm11_calls = 7`

Per-page OCR call shape:
- page `0`: `36` planned crops, `46` OCR calls
- page `1`: `168` planned crops, `176` OCR calls
- page `2`: `168` planned crops, `168` OCR calls
- page `3`: `162` planned crops, `168` OCR calls
- page `4`: `168` planned crops, `172` OCR calls
- page `5`: `120` planned crops, `124` OCR calls

Retry concentration:
- column `0` item number: `12`
- column `1` description: `7`
- column `4` unit price: `1`

Why this matters:
- retry trimming is too small to solve the runtime gap
- preprocessing is only the secondary cost center
- the big lever is first-pass OCR call volume and/or per-call overhead

## Current Source-Backed Direction

Primary sources already used and saved into the OCR plans:
- Tesseract FAQ:
  https://github.com/tesseract-ocr/tesseract/wiki/FAQ/ec7f89630d433163f88ef98df058a02d00d9fdd3
- Tesseract release notes:
  https://github.com/tesseract-ocr/tesseract/wiki/ReleaseNotes/7d40c6ba2d3619a5185666be9f920845d5920925
- Tesseract ImproveQuality:
  https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
- Tesseract Command-Line Usage:
  https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html
- OpenMP oversubscription discussion:
  https://github.com/tesseract-ocr/tesseract/issues/3109
- Dart isolates:
  https://dart.dev/language/isolates
- Flutter isolate guidance:
  https://docs.flutter.dev/perf/isolates
- `TransferableTypedData`:
  https://api.dart.dev/dart-isolate/TransferableTypedData-class.html

Key takeaways already reflected in code and plans:
- bounded worker concurrency is the right outer model
- one engine per worker is the safe model
- serial OCR inside each worker remains the right Tesseract shape
- future runtime work should focus on page-local recognition shape, not shared-engine tricks

## Ranked Next-Step Options

### Highest-upside option: row-banded OCR

Shape:
- OCR a full row band once
- reassign recognized words into known columns by x position
- fall back to cell OCR when structure is not trustworthy

Why it matters:
- it is the first option with real potential to collapse first-pass OCR call volume dramatically

Main risk:
- row-level text can bleed across columns and hurt numeric fidelity if the fallback rules are weak

### Second option: lane- or column-group OCR

Shape:
- combine semantically similar columns into a smaller number of OCR bands

Why it matters:
- still reduces calls materially
- lower risk than whole-row OCR

### Enabling refactor that should happen first: lower-overhead OCR result format

Shape:
- stop assuming HOCR is the only useful OCR output for crops
- add a cheaper word-box result mode so future page-local recognizers are not forced through HOCR XML generation/parsing

Why it matters:
- lower risk than changing geometry first
- useful for both the current cell path and future row/lane recognizers
- sets up the next runtime experiments cleanly

### Low-value near-term options

These are not the next main path:
- more worker-count tuning
- more worker transport redesign
- retry micro-tuning as a primary runtime strategy
- preprocessing-only optimization as the main push

## Files And Plans That Matter Most On Resume

Primary OCR handoff and planning docs:
- [2026-04-06-ocr-runtime-worker-pool-handoff.md](C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-06-ocr-runtime-worker-pool-handoff.md)
- [2026-04-06-ocr-runtime-endpoint-refactor-plan.md](C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-06-ocr-runtime-endpoint-refactor-plan.md)
- [2026-04-06-ocr-runtime-endpoint-refactor-todo.md](C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-06-ocr-runtime-endpoint-refactor-todo.md)
- [2026-04-06-ocr-per-page-optimization-plan.md](C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-06-ocr-per-page-optimization-plan.md)
- [2026-04-06-ocr-per-page-optimization-todo.md](C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-06-ocr-per-page-optimization-todo.md)

Most relevant runtime code:
- [text_recognizer_v2.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart)
- [ocr_page_recognition_executor.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/ocr_page_recognition_executor.dart)
- [ocr_page_pool_strategy.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/ocr_page_pool_strategy.dart)
- [ocr_page_worker_runner.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/ocr_page_worker_runner.dart)
- [ocr_grid_page_recognition_stage.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/ocr_grid_page_recognition_stage.dart)
- [ocr_cell_recognition_stage.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/ocr_cell_recognition_stage.dart)
- [ocr_retry_resolution_stage.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/ocr_retry_resolution_stage.dart)
- [tesseract_engine_v2.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart)

## Recommended Exact Resume Point

The next session should begin with:
1. stay on `codex/ocr-per-page-runtime-isolation`
2. read the per-page optimization plan/TODO first
3. keep the current cell-based worker path as the protected fallback
4. implement the lower-overhead OCR output seam before trying row-banded OCR

## Recommended First Implementation Slice On Resume

The next code slice should be:
- add OCR result-format selection to the engine/config contract
- support a direct word-box result mode alongside HOCR
- keep HOCR as the default until the alternate page-local recognizer is proven

Why this is the right next slice:
- low-risk enabling refactor
- keeps Springfield default behavior stable
- avoids another large orchestration rewrite
- makes the first row-banded or lane-banded recognizer experiment possible without reworking the engine again

## Acceptance Gates For Future OCR Work

Primary acceptance gate:
- Springfield on S25 via the debug server

Protected pass conditions:
- `131/131`
- exact checksum
- no bogus rows

What future OCR experiments must report:
- total runtime
- `text_recognition` runtime
- OCR call-count deltas
- fallback counts back to the protected cell path

Supporting local checks are fine, but they are not the acceptance gate for this branch.

## Risks To Keep In Mind

### 1. Final extraction can stay green while raw-grid output still has recoverable mistakes

That means:
- final-item gates are stronger than raw-grid visual gates today
- “no visual regression” still needs stricter machine enforcement if that requirement becomes hard again

### 2. Worker count is already effectively solved for the S25

The branch should assume:
- `2` workers is the practical cap for this device
- more worker-count experimentation is low priority unless new device evidence forces it

### 3. Row-banded OCR is the highest-upside change, but also the easiest way to regress numerics

So the branch should not remove:
- the current cell recognizer
- item-number protection
- deterministic fallback paths

## Device And Workflow Notes

Operational notes from the user:
- S25 is the active OCR device
- do not use the S21 for this OCR work
- use the debug server as the primary view into app/runtime behavior

Branching note:
- this OCR work should continue only on `codex/ocr-per-page-runtime-isolation` until it has a clear, stable, reviewable result
