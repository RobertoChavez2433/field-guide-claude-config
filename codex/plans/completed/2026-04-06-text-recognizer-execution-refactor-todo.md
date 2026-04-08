# Text Recognizer Execution Refactor TODO

Date: 2026-04-06
Status: Active

## Immediate

- Keep the S25 serial Springfield path green.
- Keep OCR page workers disabled by default.
- Keep the new page-recognition strategy seam stable.
- Use the new worker DTOs as the only payload contract for future worker attempts.

## Completed

- Per-page OCR execution has been extracted from `TextRecognizerV2`.
- The active runtime path is back on the serial executor split.
- The refactor has been validated with targeted tests and a green S25 Springfield run.
- Ordered page execution now goes through an explicit page-recognition strategy.
- Worker metrics are now sourced from the strategy result path.
- The strategy seam has been validated with targeted tests and another green S25 Springfield run.
- Worker request/result DTOs now exist and have focused round-trip tests.
- A non-default worker-proof strategy now exists with validation and serial fallback tests.

## This Refactor Slice

- Add a dedicated serial page execution component for:
  - render DPI sanitization
  - grid/full-page branching
  - page-level fallback capture
- Update `TextRecognizerV2` to orchestrate pages and aggregate outcomes only.
- Keep future worker code out of the orchestration hot path.

## After This Slice

- Add a narrow two-page worker proof before another full Springfield worker attempt.
- Keep serial as the default strategy until the narrow proof is green on the S25.
- Build the real worker runner behind the completed proof strategy.

## Verification

- `dart analyze` on the touched OCR files
- targeted `ocr_text_recognizer` tests
- if behavior risk appears, rerun Springfield on the S25
