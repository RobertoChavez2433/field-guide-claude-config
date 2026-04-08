# Sync Validation Proof Phases Plan

Date: 2026-04-07
Branch: `sync-engine-refactor`
Owner: Codex

## Goal

Close the remaining sync release-proof lanes with explicit architecture gates,
live evidence, and exit criteria so the branch can be judged on drift/loss
resistance instead of intuition.

## Architecture Readout

The broad custom lint pass is doing the right job. The sync core has been
decomposed, but legacy sync-era data access still exists outside the intended
owners.

### Custom Lint Snapshot

- `60` total findings on 2026-04-07.
- `56` architecture errors.
- `4` non-blocking warnings unrelated to the proof matrix.

### Error Clusters

1. Raw Supabase sync-table row I/O outside approved owners:
   `calculation_history`, `contractors`, `entry_equipment`, `equipment`,
   `personnel_types`, `daily_entries`, `form_responses`, `inspector_forms`,
   `locations`, `photos`, `projects`, `bid_items`, `entry_quantities`,
   `todo_items`, and the shared `BaseRemoteDatasource` surface.
2. Sync contract lists still scattered outside the registry:
   `photo_adapter.dart`, `simple_adapters.dart`, `soft_delete_service.dart`.
3. Raw local deletes still exist in sync paths:
   `conflict_resolver.dart`, `sync_metadata_store.dart`.
4. One `change_log` cleanup path still lacks an explicit success guard in
   `database_service.dart`.

## Phase 0: Architecture Debt Surfaced By Lints

### Objective

Eliminate the remaining legacy sync access surfaces before relying on the proof
matrix as release evidence.

### Work

1. Replace feature remote datasource sync-table writes/reads with approved sync
   owners or formally isolate them as non-sync-only APIs.
2. Reduce or remove `BaseRemoteDatasource` usage for any registered sync table.
3. Replace scattered sync-table lists with registry or adapter contract access.
4. Remove raw local delete behavior from sync internals unless the component is
   explicitly a local-only eviction owner.
5. Guard all `change_log` cleanup with explicit sync success predicates.

### Proof

- `dart run custom_lint` returns zero sync-architecture errors.
- `flutter analyze` stays clean.
- Regression tests cover the new ownership paths.

### Exit Criteria

- No `no_raw_supabase_sync_table_io_outside_supabase_sync` violations.
- No `sync_table_contract_must_come_from_registry` violations.
- No raw-delete sync violations left without an approved exception path.

## Phase 1: Remove-From-Device And Fresh-Pull Parity

### Objective

Prove that local-only eviction never becomes remote data loss and never causes
stale resurrection after re-enrollment.

### Scenarios

1. Windows remove-from-device on an active assigned project, then fresh pull.
2. S21 remove-from-device on an active assigned project, then fresh pull.
3. Repeat both after prior delete/restore/hard-delete fixes are present.

### Evidence To Capture

- `/driver/sync-status`
- `/driver/change-log?table=<table>`
- `/driver/delete-propagation`
- `/driver/synced-projects`
- SQLite row state for `projects`, `project_assignments`, `daily_entries`,
  `photos`, `documents`
- UI absence after local removal and UI rematerialization after fresh pull

### Exit Criteria

- Removed device clears local scope only.
- Remote rows remain correct.
- Fresh pull rematerializes the same active scope with no duplicate rows.
- Two consecutive sync runs settle at `pushed: 0, pulled: 0`.

## Phase 2: File-Backed Live Lanes

### Objective

Prove that file-backed entities converge across SQLite, Supabase, storage, and
UI without orphaning or silent divergence.

### Lanes

1. Documents:
   create, sync, inspect storage path, delete, restore if supported, verify
   storage cleanup.
2. Entry exports:
   generate export, sync metadata, validate file presence/absence remotely and
   on receiver.
3. Form exports:
   same proof pattern as entry exports.
4. Strengthened photo flow:
   create, upload, receiver render, delete, verify storage cleanup idempotence.

### Evidence To Capture

- Supabase row state including `remote_path`
- Storage object existence before and after delete
- Receiver SQLite metadata
- Receiver UI presence/absence
- `storage_cleanup_queue` state where applicable

### Exit Criteria

- Each file-backed lane passes create/sync/delete convergence.
- No orphaned storage objects remain after cleanup.
- Repeat sync stays idle at `0/0`.

## Phase 3: User-Scoped And Insert-Only Lanes

### Objective

Prove that non-project, user-scoped, and insert-only tables obey their special
contracts and do not inherit wrong delete/update behavior.

### Lanes

1. Support tickets:
   create on one device, sync to remote, pull to second device if applicable,
   verify no repeat pull churn and no schema drift warnings.
2. Consent records:
   create and verify insert-only behavior, no ad hoc updates/deletes, no retry
   storms.

### Evidence To Capture

- `change_log` rows before and after sync
- Supabase row state
- SQLite row state on both devices
- Repeat sync idempotence

### Exit Criteria

- Support ticket lane settles cleanly with `updated_at` contract intact.
- Consent flow proves insert-only semantics with no false delete/update paths.

## Phase 4: Retry And Restart Chaos

### Objective

Prove idempotence and safety when the app is interrupted during active sync or
cleanup.

### Interruptions

1. Kill during push.
2. Kill during pull.
3. Kill during delete propagation.
4. Kill during storage cleanup.

### Method

- Start the target lane.
- Force-close the app or stop the driver mid-flight.
- Relaunch and run ordinary sync only.
- Verify queue recovery, row correctness, and no duplicate writes.

### Evidence To Capture

- `change_log`
- `failed_sync_queue`
- `storage_cleanup_queue`
- pull cursor / last sync timestamps
- final SQLite and Supabase row state

### Exit Criteria

- Recovery completes without manual DB surgery.
- No stranded retry residue remains after the next healthy cycle.
- Final state matches single-run behavior.

## Phase 5: Mixed-Flow Soak And Final Proof Matrix

### Objective

Run a realistic chained flow that exercises the repaired contracts together,
then record the final proof matrix by table and behavior.

### Soak Flow

1. Create project-scoped records with files.
2. Edit records on sender.
3. Sync to receiver.
4. Delete one branch, restore another, hard-delete a third if supported.
5. Revoke scope from one device.
6. Remove from device on the other.
7. Fresh-pull both devices.
8. Reopen apps and run integrity.
9. Repeat sync twice.

### Final Matrix Must Show

- table/adapter
- owner component
- create/update/delete/restore/hard-delete expectation
- remote row evidence
- local row evidence on both devices
- storage evidence if file-backed
- UI visibility evidence
- idempotence evidence
- remaining known limitations

### Exit Criteria

- Every registered sync table has explicit evidence or an explicit
  non-applicability note.
- No open high-severity drift or data-loss class remains.

## Execution Order

1. Phase 0 architecture lint backlog
2. Phase 1 remove-from-device and fresh-pull parity
3. Phase 2 file-backed lanes
4. Phase 3 support-ticket and consent lanes
5. Phase 4 retry/restart chaos
6. Phase 5 mixed-flow soak and final matrix

## Notes

- Do not narrow the new lints to make the repo look cleaner.
- If the broad lints expose additional legacy sync surfaces, keep them visible
  and track them in this plan or the release TODO.
- Live validation remains Windows + S21 only for device proof.
