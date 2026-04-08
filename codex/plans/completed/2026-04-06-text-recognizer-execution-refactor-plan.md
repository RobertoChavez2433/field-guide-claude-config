# Text Recognizer Execution Refactor Plan

Date: 2026-04-06
Branch: `sync-engine-refactor`
Owner: Codex
Status: Active

## Why This Exists

The general Springfield OCR runtime findings now show two things at the same time:

- the protected serial path is still green on the S25
- the first page-worker OCR prototype hangs on-device during `text_recognition`

That means the next iteration should not be another direct worker retry. The code needs a cleaner execution boundary first.

## Source-Aligned Target

This refactor is preparing the worker model supported by the Tesseract sources already captured in the OCR findings:

- OCR-only workers after rendering/preprocessing
- bounded page-level parallelism
- `OMP_THREAD_LIMIT=1`
- isolated Tesseract instances per worker
- serial OCR inside each worker
- deterministic aggregation by page index

## Problem Statement

`TextRecognizerV2` currently mixes four responsibilities:

1. stage orchestration and reporting
2. page ordering and page outcome collection
3. per-page OCR execution
4. experimental worker serialization and worker lifecycle logic

That coupling creates three concrete problems:

- the serial baseline is harder to reason about because dead worker-path code still lives in the same class
- worker failures are difficult to isolate because execution, serialization, and aggregation are intertwined
- future experiments cannot be validated incrementally; the first real proof currently requires the full Springfield path

## Refactor Goals

Immediate goals:

- keep the protected S25 serial baseline unchanged in behavior
- reduce `TextRecognizerV2` back to orchestration/reporting responsibility
- move per-page recognition into a dedicated execution component
- create an explicit seam where future execution strategies can plug in

Near-term goals:

- define isolate-safe request/result boundaries outside the orchestration class
- make a future worker strategy opt-in and independently testable
- add a smaller proof path before full Springfield reruns

Non-goals for this refactor slice:

- no correctness-risk crop tuning
- no Tesseract model changes
- no full worker re-enable in this slice
- no promise of immediate runtime reduction

## Proposed Shape

### Stage 1: Separate Serial Page Execution

Create a dedicated page execution component that owns:

- page-level render DPI sanitization
- grid-vs-full-page fork
- page-level fallback/error capture
- normalized page result object

`TextRecognizerV2` should keep:

- page ordering
- page outcome collection
- metrics aggregation
- final stage report construction

Expected outcome:

- serial behavior stays intact
- the baseline path becomes easier to inspect and test

### Stage 2: Introduce Execution Strategy Boundary

Once serial page execution is isolated, add a small strategy seam:

- serial page executor
- future worker page executor

The orchestration layer should not know worker payload details.

Expected outcome:

- worker attempts become a replaceable strategy, not embedded control flow

### Stage 3: Build A Smaller Worker Proof

Before another full Springfield run:

- validate a two-page OCR worker proof
- require explicit success/failure logging from the worker boundary
- prove request/result serialization independently from full extraction

Expected outcome:

- no more all-or-nothing Springfield-only worker validation

## Acceptance Criteria

For this refactor slice:

- `TextRecognizerV2` orchestration becomes materially smaller and clearer
- serial OCR behavior remains the default path
- existing protected Springfield behavior remains green
- no automatic worker activation

For the later worker slice:

- worker execution must not be enabled by default until:
  - a narrow proof passes
  - S25 Springfield passes
  - no hang is observed in `text_recognition`

## First Iteration From This Plan

Implement now:

1. extract serial page recognition into a dedicated component
2. remove worker-specific decision pressure from the main orchestration flow
3. leave future worker support explicitly disabled
4. verify analysis and targeted OCR tests

This is a refactor-for-safety iteration, not a speedup iteration.

## Iteration Result

Completed in this slice:

1. extracted serial per-page OCR execution into `ocr_page_recognition_executor.dart`
2. reduced `TextRecognizerV2` back to orchestration/reporting duties
3. kept worker execution out of the active runtime path
4. validated targeted tests and a green S25 Springfield run

Observed S25 result after the refactor:

- `131/131`
- exact checksum
- no bogus rows
- duration about `94s`
- `text_recognition` about `74590 ms`

Implication:

- the refactor is a good staging point for the next execution-strategy experiment

## Second Iteration From This Plan

Implement now:

1. move the ordered batch page loop out of `TextRecognizerV2` and behind an explicit strategy
2. keep the serial strategy as the only active runtime path
3. wire worker-related metrics through the strategy result instead of hard-coded stage constants
4. verify the seam with targeted tests and another green S25 Springfield run

This is still a refactor-for-safety iteration, not a speedup iteration.

## Iteration Result

Completed in this slice:

1. added an explicit page-recognition strategy contract above the single-page executor
2. kept the default runtime on the serial strategy
3. removed hard-coded worker metrics from `TextRecognizerV2`
4. validated the seam with recognizer tests and another green S25 Springfield run

Observed S25 result after the strategy seam:

- `131/131`
- exact checksum
- no bogus rows
- duration about `94s`
- `text_recognition` about `75821 ms`

Implication:

- the strategy seam is now ready for isolate-safe worker DTO work
- the next slice should prove serialization and worker lifecycle on a narrow two-page path before touching the full Springfield worker run

## Third Iteration From This Plan

Implement now:

1. define isolate-safe request/result DTOs for page OCR worker traffic
2. cover request and result round-trips with focused tests
3. keep runtime behavior unchanged while the payload contract is stabilized

This is still setup work for future worker proofing, not a speedup iteration.

## Iteration Result

Completed in this slice:

1. added worker request DTOs for page input, grid metadata, OCR config, and tessdata path
2. added recognized-page result snapshots for grid, full-page, and failure outcomes
3. validated round-trip behavior with focused worker payload tests

Implication:

- the next slice can focus on a narrow two-page worker proof instead of payload design
- serial remains the protected default runtime path
