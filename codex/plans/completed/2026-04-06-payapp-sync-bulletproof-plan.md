# Pay App + Sync Bulletproof Plan

Date: 2026-04-06
Worktree: `C:\Users\rseba\Projects\Field_Guide_App_payapp_sync_verification`
Branch: `codex/payapp-sync-verification`
Spec anchor: `.claude/specs/2026-04-05-pay-application-spec.md`

## Objective

Prove that the pay-application feature and the sync engine are safe for pre-production with sync integrity as the first priority. The main bar is no known data-loss path across local SQLite, Supabase rows, or file storage for pay-app exports and their related artifacts.

## End Goals

- No silent data-loss or corruption path remains in pay-app creation, replacement, export, sync, pull, delete, or restore flows.
- `pay_applications` and `export_artifacts` stay logically consistent across SQLite rows, `change_log`, Supabase rows, and remote storage objects.
- File-backed pay-app artifacts survive replace, retry, conflict, delete, and multi-device sync sequences without orphaning or cross-linking.
- The implemented behavior still matches the spec intent for export flow, exported history, comparison/discrepancy artifacts, and chronology rules.
- The verification story is strong enough to explain exactly what is proven, what is still unproven, and why.

## Scope

In scope:
- pay-app export / replace / delete / detail / history flows
- `export_artifacts` + `pay_applications` sync and storage handling
- pull-side rescue, cache-path behavior, purge / soft-delete / delete propagation
- test coverage and runtime verification directly relevant to the new pay-app feature and sync safety

Out of scope unless required by a discovered pay-app/sync defect:
- unrelated feature work
- OCR pipeline changes
- non-pay-app product polish

## Workstreams

1. Sync Integrity Audit
- Re-walk push, pull, delete, purge, cache-path, and storage cleanup flows for `pay_applications` and `export_artifacts`.
- Treat silent failure, partial success, stale remote reuse, and parent/child divergence as highest severity.
- Thin oversized sync orchestrators where mixed responsibilities are hiding error
  paths, starting with `pull_handler`, `push_handler`, and then
  `integrity_checker` only if the seam is behavior-neutral.

2. Test Gap Closure
- Strengthen regressions where current proof is still indirect, especially around UI-triggered export behavior and destructive sync/delete paths.
- Prefer tests that prove invariants, not implementation details.

3. Runtime Verification
- Re-run analyzer and the focused pay-app/export/sync suite from this worktree.
- Re-run Windows and S21 driver checks on isolated ports once the branch is build-stable outside concurrent OCR work.

4. Residual-Risk Reduction
- Keep iterating until remaining risk is either closed or clearly external to this slice.
- Do not claim “green” while a known build/runtime blocker outside this slice still prevents the required verification run.

## Active TODO

1. Runtime Harness
- Keep S21 on an isolated HTTP driver port with no overlap against the other active debug sessions.
- Prefer attached-debug style iteration where practical, but require cold relaunches for init-sensitive sync changes.
- Restore Windows runtime verification so the second client path is available again.

2. Sync Verification
- Re-run the shared sync verification chain against the current refactor state with proof at the UI, SQLite, `change_log`, Supabase, storage, and log layers.
- Pay special attention to silent-failure surfaces:
  - unprocessed `change_log` rows after “successful” sync
  - FK-rescue skips that never recover
  - file-backed rows whose metadata syncs but storage state does not
  - user-scoped tables that probe unsupported soft-delete columns
  - background integrity warnings that are masking real drift
- Record every confirmed anomaly with exact table, IDs, timestamps, and reproduction steps before fixing.

3. Pay App Verification
- Complete P01 exported-history visibility through the real Forms UI.
- Complete P02 same-range replace and prove logical identity/number preservation.
- Complete P03 overlap-block and prove no saved row is created.
- Complete P04 delete propagation and prove SQLite, Supabase, and storage cleanup.
- Complete P05 contractor comparison plus discrepancy PDF export, without touching the OCR pipeline.
- Complete P06 cross-client pay-app artifact sync/delete verification once the second runtime is stable.
- Replace developer-style pay-app/comparison instructions with operator-facing copy before final runtime signoff.
- Standardize on one permanent 5-item contractor CSV fixture for parser tests, widget tests, and live S21 comparison verification.

4. Test Hardening
- Add or strengthen tests for every defect found during runtime verification.
- Keep sync orchestrators thin and observable; do not add new swallowed exceptions or silent catch paths.
- Re-run focused `flutter test` and `flutter analyze` after each fix before resuming device verification.
- Add fixture-backed proof that the permanent contractor CSV still parses into five usable rows with daily detail.
- Add narrow-width comparison UI coverage so cleanup controls do not overflow on phone-sized layouts.

5. Defect Tracking
- Log any still-open confirmed defect or runtime blocker to GitHub with reproduction steps and evidence links.
- Do not file speculative issues; only file defects that survive reproduction and triage.

## Success Criteria

- `flutter analyze` passes from this worktree.
- Focused pay-app/export/sync regression suite passes from this worktree.
- No open High findings remain in pay-app/export/sync review.
- Any remaining Medium findings are either fixed or explicitly shown to be non-data-loss issues.
- Runtime verification either passes on Windows and S21 or is blocked only by a known branch-wide issue outside pay-app/sync ownership.
- Sync orchestration files are thin enough that record-level rescue, cache
  invalidation, routing, and eligibility logic are independently testable.
