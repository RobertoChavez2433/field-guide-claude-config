# Sync Orchestrator Refactor Plan

Date: 2026-04-06
Owner: Codex
Worktree: `C:\Users\rseba\Projects\Field_Guide_App_payapp_sync_verification`
Branch: `codex/payapp-sync-verification`
Spec anchors:
- `.claude/specs/2026-04-04-sync-engine-refactor-spec.md`
- `.claude/specs/2026-04-05-pay-application-spec.md`
- `.claude/docs/features/feature-sync-architecture.md`
- `.claude/rules/sync/sync-patterns.md`

## Goal

Reduce sync-engine orchestration risk without broad architectural churn by
extracting record-level policy and recovery logic out of oversized handlers.
The primary success condition is unchanged sync behavior with stronger
characterization coverage and clearer failure surfaces, especially for
pay-app/export-artifact sync where data loss is unacceptable.

## Why Now

The current branch is still wiring pay-app/export sync and verification. The
largest sync files are starting to hide behavior:

- `lib/features/sync/engine/pull_handler.dart`
- `lib/features/sync/engine/push_handler.dart`
- `lib/features/sync/engine/integrity_checker.dart`

Those files now mix orchestration with per-record policy, FK rescue, cache
cleanup, and remote/local comparison rules. That raises the chance of silent
failures, weak reviewability, and accidental data-loss regressions.

## Scope

### In Scope

1. Keep `PullHandler` as a thin table/page orchestrator.
2. Extract pull record-apply logic out of `PullHandler`.
3. Extract pay-app/export-artifact dependency rescue out of `PullHandler`.
4. Extract file-cache invalidation out of `PullHandler`.
5. Keep `PushHandler` as a thin change-cycle orchestrator.
6. Extract push eligibility/blocking/scope planning out of `PushHandler`.
7. Extract push execution/routing out of `PushHandler`.
8. Expand sync verification to explicitly prove preserved behavior after
   extraction.

### Out of Scope

1. OCR pipeline changes.
2. A broad sync rewrite or engine re-architecture.
3. Replacing `LocalSyncStore` as the main SQLite facade unless a very small
   extraction becomes obviously necessary.
4. A broad `IntegrityChecker` rewrite unless a narrow extraction is clearly
   safer than leaving it in place.
5. New product features unrelated to pay-app/export sync safety.

## Current Assessment

### `pull_handler.dart`

Current responsibilities:
- pull-cycle orchestration
- per-table cursor/page iteration
- insert/update/conflict application
- `pay_applications.previous_application_id` rescue
- `pay_applications.export_artifact_id` rescue
- file-backed artifact cache invalidation

Safe extraction path:
- `PullRecordApplier`
  - apply new vs existing remote records
  - own remote/local conflict handling
  - own remote-wins update path
- `PullDependencyRescuer`
  - rescue export artifact parents
  - rescue pay-app previous chain
  - keep recursion/cycle guard local to this collaborator
- `PullFileCacheReconciler`
  - invalidate stale local file cache on remote delete or `remote_path` change

`PullHandler` should retain:
- trigger-suppressed pull-cycle wrapper
- scope-plan iteration
- page fetch loop
- cursor updates
- callbacks/progress

### `push_handler.dart`

Current responsibilities:
- push-cycle orchestration
- FK failed-parent blocking
- adapter skip filtering
- out-of-scope project skip logic
- delete/update/insert routing
- record validation, stamping, remap, LWW, and writeback

Safe extraction path:
- `PushChangePlanner`
  - batch slicing by table
  - failed-parent blocking
  - adapter skip and out-of-scope eligibility checks
- `PushRecordExecutor`
  - route delete vs upsert
  - own delete execution
  - own upsert execution
  - own company stamping, natural-key remap, LWW, file-adapter routing, and
    server timestamp writeback

`PushHandler` should retain:
- circuit-breaker gate
- read unprocessed changes
- table-order iteration
- retry/error aggregation
- progress reporting

### `integrity_checker.dart`

Current responsibilities:
- integrity schedule gate
- per-table comparison
- server ID batch fetching
- orphan purge
- checksum helpers

Safe extraction path:
- extract orphan purge first if it can move without changing semantics
- leave `run()` + `_checkTable()` together unless the comparator seam is clean
  after the handler refactors

Initial recommendation:
- treat extraction as optional, not mandatory
- only prioritize `OrphanPurger` if it materially improves reviewability
  without changing purge semantics or maintenance-handler wiring
- otherwise keep `IntegrityChecker` as the owner of integrity cadence and
  result shaping for this pass

### `local_sync_store.dart`

Current state:
- already a facade over `TriggerStateStore`, `LocalRecordStore`,
  `SyncMetadataStore`, and `SyncedScopeStore`

Recommendation:
- leave it as the approved SQLite boundary from the April 4 refactor spec
- only add narrow delegation if a handler extraction needs it

## Verification Additions Required

### Pull Characterization

1. `PullHandler` still writes the max cursor once per table after paging.
2. file-backed remote delete still clears local cache file and local path.
3. file-backed remote `remote_path` replacement still clears stale local cache.
4. pay-app previous-chain rescue still materializes parent chain before child.
5. pay-app export-artifact rescue still materializes parent artifact before
   child pay app.
6. rescue failures still surface as FK skips rather than silent success.

### Push Characterization

1. FK failed-parent blocking still prevents child push and marks the child
   failed with a reason.
2. out-of-scope project changes still skip push and mark processed.
3. adapter skip filters still mark processed without remote write.
4. file adapters still route through `FileSyncHandler`.
5. non-file upserts still preserve natural-key remap and timestamp writeback.
6. LWW skip still increments skipped-push accounting without remote write.

### Integrity / Maintenance Verification

1. integrity drift still recommends cursor reset only when threshold rules are
   exceeded.
2. orphan purge still respects synced-project scoping and non-soft-delete
   behavior.
3. extracted orphan purge still restores `sync_control.pulling = '0'` on every
   path.

### Runtime / No-Silent-Failure Checks

1. no new catch blocks without a test asserting the resulting observable
   behavior
2. no helper should swallow FK rescue or file cleanup failures silently
3. analyzer + focused sync suites rerun after each extraction step

## End State

This refactor is complete only when:

1. `PullHandler` and `PushHandler` are materially smaller and mostly
   orchestration.
2. extracted collaborators own the record-level policy they encapsulate.
3. sync tests prove pay-app/export-artifact safety and no behavior regressions.
4. `flutter analyze` and the focused sync/pay-app verification slice are green.
5. no class touched in this pass moves farther away from the April 4 sync
   refactor constraints, especially the thin coordinator / clear I/O boundary
   goals.
6. incidental generated files are restored before handoff.
