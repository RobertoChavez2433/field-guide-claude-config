# OCR Runtime Endpoint Refactor TODO

Date: 2026-04-06
Author: Codex
Status: Active
Parent: `2026-04-06-ocr-runtime-endpoint-refactor-plan.md`

## End Goals

- keep the persistent page-worker architecture as the cross-platform OCR path
- make the worker boundary clean enough to iterate without protocol churn
- preserve Springfield correctness while removing avoidable endpoint overhead
- leave a clear measured path toward the next runtime reduction phase

## Hard Stop Scope

This TODO is complete when:
- worker init state is sent once per worker lifecycle
- per-page requests contain only page-specific data
- strategy/runner naming no longer frames the pool as a temporary proof
- local OCR worker tests and analyzer are green

This TODO does not include:
- new OCR heuristics
- cell-level parallelization
- S25 runtime retuning loops
- raw-grid gating work

## Execution Queue

1. Document the live boundary.
- Confirm which request fields are invariant across a Springfield run.
- Confirm which fields must remain page-local.

2. Refactor the worker protocol.
- Add a worker-init DTO for document-invariant state.
- Remove `config` and `tessdataPath` from the per-page DTO.
- Initialize worker engine/runtime state from bootstrap data.

3. Promote the runtime naming.
- Replace “proof” naming in the active strategy path with production-oriented worker-pool naming.
- Keep the serial fallback path intact.

4. Preserve deterministic recovery behavior.
- Keep worker failures falling back to serial.
- Keep page result ordering stable by page index.

5. Re-verify locally.
- Update payload and strategy tests for the new endpoint split.
- Run targeted analyzer and worker-path tests.

## Follow-On Queue After This TODO

1. Completed: add queue-time vs execute-time worker metrics.
2. Completed: estimate transport overhead from the cleaned endpoint shape.
3. Completed conclusion: transport overhead is negligible on the S25 pooled path.
4. Next: quantify page-local cost by pairing per-page execute time with per-page OCR-call count.
5. Next: design the next safe refactor around reducing OCR call volume, not worker overhead.
