Date: 2026-04-06
Status: Active

## Immediate

- Keep the persistent worker-client abstraction intact.
- Keep serial OCR as the protected fallback path.
- Keep long-lived OCR workers on `Isolate.spawn`, not repeated `compute()`.
- Keep one Tesseract engine per worker and serial OCR inside each worker.
- Keep `TransferableTypedData` for page bytes end-to-end.
- Keep request IDs, `Completer` correlation, and explicit shutdown intact.
- Keep `2` workers as the active S25 benchmark shape.

## Verification

- Keep existing DTO and strategy tests green.
- Run `dart analyze` on touched OCR files.
- Record repeated S25 pooled runs to quantify variance.
- Compare pooled runs against same-build serial when needed.
- If another worker-pool change is made, capture raw-grid diffs as well as final item flow.

## Guardrails

- Do not remove the strict Springfield gate.
- Do not revert the protected item-number lane.
- Do not remove `classify_enable_learning=0`.
- Do not reintroduce native stdout/stderr capture in `flusseract`.
- Do not use the S21.
