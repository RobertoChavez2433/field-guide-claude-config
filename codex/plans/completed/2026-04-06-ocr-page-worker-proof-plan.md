# OCR Page Worker Proof Plan

Date: 2026-04-06
Branch: `sync-engine-refactor`
Owner: Codex
Status: Active

## Why This Exists

The OCR runtime work now has a source-backed execution target:

- OCR-only workers after rendering and preprocessing
- bounded page-level parallelism before any cell-level attempt
- `OMP_THREAD_LIMIT=1`
- isolated Tesseract instances per worker
- serial OCR inside each worker
- deterministic aggregation by page index

This matches current Tesseract guidance more closely than same-isolate async fanout or shared engine state.

## Primary Sources

- Tesseract FAQ:
  https://github.com/tesseract-ocr/tesseract/wiki/FAQ/ec7f89630d433163f88ef98df058a02d00d9fdd3
- Tesseract Release Notes:
  https://github.com/tesseract-ocr/tesseract/wiki/ReleaseNotes/7d40c6ba2d3619a5185666be9f920845d5920925
- Tesseract ImproveQuality:
  https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
- Tesseract Issue #3109:
  https://github.com/tesseract-ocr/tesseract/issues/3109

## Objective

Build a narrow, non-default two-page OCR worker proof that:

- uses the new isolate-safe DTO contract
- preserves the protected serial runtime path
- validates worker request/result shape and fallback behavior
- prepares for a later S25 worker experiment without enabling it yet

## Scope

In scope:

- worker-proof strategy abstraction above the serial page executor
- two-page batching only for the proof path
- request serialization into worker DTOs
- result validation and deterministic reordering by page index
- clean serial fallback if the worker path throws or returns invalid data

Out of scope:

- full Springfield worker activation
- any default-runtime behavior change
- crop-policy retuning
- cell-level parallelism
- model swaps

## Acceptance Criteria

- The proof path is opt-in only.
- It serializes page requests using the DTO contract already added.
- It validates response count and page identities before accepting worker output.
- It falls back to the serial strategy on worker failure or malformed output.
- Focused tests cover:
  - happy-path two-page worker proof
  - deterministic page ordering after worker return
  - serial fallback on worker failure
  - serial fallback on invalid worker output

## Next Step After This Plan

Once the proof path is stable in tests:

1. decide whether to run a very narrow device proof on S25
2. keep worker count conservative
3. keep serial as the default strategy
4. only later consider a broader Springfield worker experiment

## Iteration Result

Completed in this slice:

1. added a non-default worker-proof page-recognition strategy
2. routed proof batches through the worker DTO contract
3. validated worker output shape before accepting results
4. added serial fallback when the worker throws or returns invalid output
5. covered the strategy with focused tests

Files added:

- `lib/features/pdf/services/extraction/stages/ocr_page_worker_proof_strategy.dart`
- `test/features/pdf/extraction/stages/ocr_page_worker_proof_strategy_test.dart`

Verification:

- `dart analyze` passed on the touched OCR strategy files
- focused worker-proof strategy tests passed

Implication:

- the next iteration should build the real runner behind this proof strategy
- the protected runtime path remains unchanged because the strategy is still opt-in only
