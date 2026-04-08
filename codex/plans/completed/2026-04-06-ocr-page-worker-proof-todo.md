# OCR Page Worker Proof TODO

Date: 2026-04-06
Status: Active

## Immediate

- Keep the S25 serial Springfield baseline green.
- Keep OCR page workers disabled by default.
- Keep the worker shape aligned to the Tesseract-backed model:
  - OCR-only workers
  - bounded page-level parallelism
  - `OMP_THREAD_LIMIT=1`
  - isolated Tesseract instances per worker
  - serial OCR inside each worker
  - deterministic aggregation by page index

## Build Now

- Add a non-default worker-proof page-recognition strategy.
- Route pages through the new DTO contract before worker execution.
- Reorder worker results back to requested page order.
- Fallback to the serial strategy if the worker path throws.
- Fallback to the serial strategy if the worker returns malformed output.
- Cover the proof path with focused tests before any device run.

## Completed

- Added the non-default worker-proof page-recognition strategy.
- Routed proof batches through the worker DTO contract.
- Added deterministic page reordering after worker return.
- Added serial fallback on worker throw or malformed output.
- Added focused strategy tests for happy path and fallback behavior.

## Next

- Build the real runner behind the proof strategy.
- Keep the proof runner off the default runtime path.
- Decide whether the first live worker run should be a unit-level proof only or a very narrow S25 proof.

## Do Not Do Yet

- Do not enable worker execution in the default runtime.
- Do not rerun full Springfield on a worker path until the narrow proof is stable.
- Do not attempt cell-level concurrency first.
- Do not share Tesseract engine instances across workers.
