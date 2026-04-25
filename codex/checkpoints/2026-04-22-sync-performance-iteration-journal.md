# Sync Performance Iteration Journal

Date: 2026-04-22
Owner: Codex
Scope: live Supabase sync performance tuning on real device lanes

## Purpose

This file is the running journal for sync-engine performance iterations.
Each entry should record:

- the bottleneck we targeted
- why that target was chosen
- what changed in code
- how it was verified
- what the live device measurements said afterward
- what the next bottleneck became

## Iteration 1

Target:
- write-checkpoint verification cost on live S21 medium syncs

Why:
- live S21 evidence showed checkpoint proof dominating `medium-row-quick`
  after push and pull completed

Implementation:
- batched write-checkpoint proof reads
- measurement pipeline fixes so live artifacts captured real phase timings

Outcome:
- checkpoint cost dropped sharply
- checkpoint was no longer the dominant cost on the medium path

Key live result:
- `medium-row-quick`: checkpoint `8235ms -> 367ms`

Next bottleneck:
- push cost remained dominant on 30s+ row-backed syncs
- full/no-op syncs still paid a substantial pull fan-out tax

## Iteration 2

Target:
- push-side per-row remote overhead

Why:
- live S21 medium runs still spent ~`26s-27s` in push
- code audit found two repeated remote costs in the hot path:
  - per-row LWW timestamp fetches
  - per-row sync-hint RPC emission

Implementation:
- batched LWW server timestamp prefetch
- buffered/coalesced sync hint emission by table/project scope

Verification:
- targeted sync tests and static analysis passed
- live S21 rerun completed successfully

Outcome:
- medium row-backed syncs improved substantially

Key live results:
- `medium-row-full`: `30295ms -> 15796ms`; push `26471ms -> 12179ms`
- `medium-row-quick`: `30495ms -> 14302ms`; push `26848ms -> 12130ms`

Next bottleneck:
- no-op and full syncs remain pull-bound
- `tiny-noop-full` still spends about `2.8s` in pull over `22` pull pages

## Iteration 3

Target:
- full-sync pull fan-out and no-op/full fixed overhead

Why:
- after Iteration 2, the slowest remaining common path is not checkpoint or
  push for no-op/full syncs
- live S21 evidence shows `tiny-noop-full` remains dominated by pull across
  nearly every synced table

Planned audit focus:
- determine whether full sync can safely narrow the table set for scoped data
- determine whether an exhaustive pull is only required on a slower cadence
- preserve real consistency guarantees and missed-hint recovery behavior

Status:
- implemented and measured

Implementation:
- persisted `last_exhaustive_full_pull_time` so full sync can distinguish a
  recent exhaustive sweep from a stale device
- carried trusted table/project pull seeds forward from the push path
- added a guarded scoped-full pull mode:
  - direct/root tables stay active
  - non-direct tables narrow to dirty or push-derived scopes
  - exhaustive full pull remains the fallback when the device is stale or no
    trusted scopes exist
- hardened the live matrix script so it:
  - accepts comma-joined `ScenarioIds`
  - always writes `summary.json` and `summary.md` on failure with status and
    error details

Verification:
- targeted sync tests and static analysis passed
- failure-artifact path verified with an intentionally bad scenario id
- live S21 rerun completed successfully

Key live results:
- `tiny-noop-full`: `3678ms`; pull still `2967ms` over `22` pages
- `medium-row-full`: `16412ms`; push `13683ms`, pull `1546ms`, `8` pull pages
- `medium-row-quick`: `13858ms`; push `11668ms`, pull `949ms`, `5` pull pages

Outcome:
- the guarded scoped-full path reduced full-sync pull fan-out materially on the
  medium row-backed case
- no-op full remains effectively unchanged because it still must take the
  exhaustive recovery path when no trusted scopes exist
- total medium full time did not fall enough because push is still the
  dominant phase even after the narrower pull

Next bottleneck:
- push remains the main cost on medium row-backed syncs
- no-op full still pays the exhaustive `22`-page recovery sweep
- the next audit should determine whether push can batch or pipeline more of
  the row-backed upsert path, and separately whether the no-op full contract
  can be narrowed safely without weakening missed-hint recovery

## Iteration 4

Target:
- per-row remote upsert overhead on hot row-backed push tables

Why:
- after Iteration 3, medium live S21 runs still spent most of their time in
  push even though pull fan-out had improved
- code audit confirmed the hottest remaining row-backed tables still issued one
  Supabase upsert per row
- the new timing split showed the hot tables were all eligible simple-table
  adapters: `entry_quantities`, `form_responses`, `entry_equipment`, and
  `entry_personnel_counts`

Status:
- implemented and measured

Implementation:
- added guarded bulk upsert support to `SupabaseSync`
- added bulk-upsert preparation/execution to `PushExecutionRouter` for eligible
  simple-table adapters only
- kept full fallback to the existing per-row path whenever the table is not a
  clean bulk candidate or the batch call fails
- added contract coverage for both the happy path and the forced-fallback path

Verification:
- `dart analyze` on the touched sync files and tests
- `flutter test test/features/sync/engine/push_handler_contract_test.dart test/features/sync/engine/supabase_sync_contract_test.dart`
- live S21 rerun completed successfully

Key live results:
- `medium-row-full`: `16412ms -> 5248ms`; push `13683ms -> 2898ms`
- `medium-row-quick`: `13858ms -> 5096ms`; push `11668ms -> 2651ms`
- hot table push times on `medium-row-full` dropped to:
  - `entry_quantities`: `555ms` for `60` rows
  - `form_responses`: `227ms` for `20` rows
  - `entry_equipment`: `202ms` for `10` rows
  - `entry_personnel_counts`: `170ms` for `10` rows
- `tiny-noop-full` immediately after driver restart remained noisy at
  `10062ms` with the same exhaustive `22`-page sweep, but a warm rerun on the
  same live lane settled to `2275ms` with `1557ms` in pull over `4` pages

Outcome:
- the guarded bulk-upsert path was the right next optimization for the slow
  medium runs and removed the dominant per-row remote cost
- medium push is no longer a double-digit-second problem on S21
- the remaining medium push gap is now mostly local overhead outside the
  per-table remote execution window
- no-op full still needs to be evaluated separately for stale-device exhaustive
  recovery versus warm repeated full-sync behavior

Next bottleneck:
- medium row-backed syncs still spend meaningful push time outside the
  per-table remote execution window, which likely points to local preparation
  and per-row queue acknowledgement overhead
- no-op full remains expensive when the device has to take the exhaustive
  recovery path

## Iteration 5

Target:
- local push overhead that remained after guarded bulk upsert

Why:
- after Iteration 4, the hot table remote execution windows were already
  sub-second, but medium push still spent roughly `1.6s-1.7s` outside those
  table windows
- code audit showed repeated local work on the same rows:
  - per-row `change_log` acknowledgement after successful bulk pushes
  - per-row `updated_at` reads during LWW priming
  - per-row planner reads for blocked/skip decisions
  - per-row local row reads again when preparing bulk-upsert payloads

Status:
- implemented and measured

Implementation:
- added batched `change_log` acknowledgement for successful bulk pushes
- changed LWW priming to batch-read `updated_at` locally by record ID
- added full-row `readLocalRecordsByIds()` and used it in `PushTablePlanner`
  so planning no longer re-reads the same row for blocked/skip decisions
- preloaded those local rows into `prepareBulkUpsert()` so bulk preparation
  stops hitting SQLite again for the same hot table rows

Verification:
- `dart analyze` on the touched sync files and tests
- `flutter test test/features/sync/engine/change_tracker_test.dart test/features/sync/engine/push_handler_contract_test.dart test/features/sync/characterization/characterization_push_skip_test.dart`
- repeated live S21 reruns completed successfully

Key live results:
- versus the first post-bulk-upsert S21 run:
  - `medium-row-full`: `5248ms -> 4663ms`; push `2898ms -> 2352ms`
  - `medium-row-quick`: `5096ms -> 4179ms`; push `2651ms -> 2259ms`
- latest warm S21 no-op/full:
  - `tiny-noop-full`: `1406ms`; pull `760ms`; `4` pages
- latest hot-table push windows remain low:
  - `entry_quantities`: `441ms` for `60` rows on medium full
  - `form_responses`: `194ms` for `20` rows on medium full
  - `entry_personnel_counts`: `167ms` for `10` rows on medium full
  - `entry_equipment`: `163ms` for `10` rows on medium full

Outcome:
- the local batching/preload slice produced a real but smaller follow-up gain
  after the larger remote bulk-upsert win
- warm medium row-backed syncs are now roughly `4.2s-4.7s` on S21 instead of
  `13.8s-16.4s`
- warm no-op/full behavior is now much closer to the original sub-2-second
  target when the device is not forced down the exhaustive recovery path

Next bottleneck:
- the remaining medium push cost is concentrated in the preparation path that
  still validates/converts rows one by one and in the fixed full-sync pull
  cost on stale/exhaustive runs
- the next meaningful gain likely needs either:
  - a broader table-level preparation pipeline for bulk-eligible rows, or
  - further reduction of exhaustive full-pull fan-out on stale devices without
    weakening recovery guarantees

## Iteration 6

Target:
- push prelude latency outside the measured table execution windows
- summary artifact reliability when the live matrix completed but failed while
  writing markdown output

Why:
- the best stable warm S21 full run still spent about `1.1s` of push time
  outside the per-table execution timers
- code audit showed repeated per-table prelude work before execution began:
  - repeated `synced_projects` and failed-parent lookups across tables
  - serialized per-table LWW batch fetches against Supabase
- the live matrix still had a bad failure mode where a completed run could
  write `summary.json` and then die while rendering `summary.md`

Status:
- implemented and measured

Implementation:
- added `PushPlanningContext` so `PushTablePlanner` reuses synced-project IDs,
  failed-parent sets, and contractor project lookups across tables in one push
  cycle
- changed `PushHandler` to stage table plans first and start per-table LWW
  priming earlier so the remote timestamp fetches overlap with later planning
  work instead of serially blocking each table
- hardened `Write-PerfSummaryMarkdown` so it stringifies summary values before
  appending markdown lines, preventing end-of-run artifact failures

Verification:
- `dart analyze lib/features/sync/engine/push_handler.dart lib/features/sync/engine/push_table_planner.dart test/features/sync/engine/push_handler_contract_test.dart`
- `flutter test test/features/sync/engine/push_handler_contract_test.dart test/features/sync/characterization/characterization_push_skip_test.dart test/features/sync/engine/change_tracker_test.dart`
- reran the live S21 matrix successfully with summary artifacts written

Key live results:
- artifact: `tools/testing/test-results/2026-04-22/live-sync-performance-tuned-S21-20260422-100643/summary.json`
- versus the previous stable S21 checkpoint:
  - `medium-row-full`: `4027ms -> 3818ms`; push `1997ms -> 1792ms`
  - `medium-row-quick`: `3775ms -> 3166ms`; push `2088ms -> 1417ms`
- `tiny-noop-full` on the restarted lane remained exhaustive and slow:
  - `3975ms`; pull `3297ms`; `22` pages

Outcome:
- the overlapped/cached push-prelude slice produced a real warm-medium win and
  the summary writer failure path is now fixed
- the warm medium full path was now close enough that the remaining gap to a
  sub-`3000ms` combined push-plus-pull run was small

Next bottleneck:
- remove the last duplicate local row reads after planning
- trim non-critical direct-table cost on scoped full pulls without weakening
  scope freshness or missed-hint recovery

## Iteration 7

Target:
- the last duplicated local reads on the medium push path
- the non-critical direct-table pull tax on scoped full syncs

Why:
- after Iteration 6, warm medium full still hovered just above the combined
  `3000ms` push-plus-pull target
- code audit showed `PushHandler` still re-read the same local rows after
  planning:
  - once for LWW priming
  - again for bulk-upsert preparation
- scoped full still paid a direct-table poll tax even when only the project
  scope was dirty

Status:
- implemented and measured

Implementation:
- `PushTablePlan` now carries the planner’s preloaded local rows
- `PushHandler` reuses those rows for both LWW priming and bulk-upsert
  preparation instead of querying SQLite again
- added `keepDirectTableActiveInScopedFull` to `TableAdapter`
- set `SupportTicketAdapter.keepDirectTableActiveInScopedFull = false`
- `PullScopeState` now respects that flag during scoped full pulls
- added a `pull_scope_state_test.dart` contract proving opted-out direct tables
  are skipped unless they are dirty

Verification:
- `dart analyze lib/features/sync/adapters/table_adapter.dart lib/features/sync/adapters/support_ticket_adapter.dart lib/features/sync/engine/pull_scope_state.dart lib/features/sync/engine/push_handler.dart lib/features/sync/engine/push_table_planner.dart test/features/sync/engine/pull_scope_state_test.dart`
- `flutter test test/features/sync/engine/pull_scope_state_test.dart test/features/sync/engine/push_handler_contract_test.dart test/features/sync/characterization/characterization_push_skip_test.dart test/features/sync/engine/change_tracker_test.dart`
- successful live S21 rerun with summary artifacts written:
  - `tools/testing/test-results/2026-04-22/live-sync-performance-tuned-S21-20260422-101550/summary.json`

Key live results:
- `medium-row-full`:
  - observed duration `3858ms`
  - push `1722ms`
  - pull `1259ms`
  - checkpoint `8ms`
  - maintenance `12ms`
  - combined push-plus-pull `2981ms`
- `medium-row-quick`:
  - observed duration `2964ms`
  - push `1300ms`
  - pull `903ms`

Outcome:
- the warm S21 medium full path reached the requested sub-`3000ms` combined
  engine push-plus-pull target
- the broader observed end-to-end full-sync duration is still roughly
  `3.8s-3.9s`, so UI/measurement overhead and non-engine work remain above the
  stricter whole-cycle target
- exhaustive no-op full sync is still much slower and remains its own
  bottleneck
- `support_tickets` still appeared in the touched-table list on the acceptance
  run even though the new scoped-full policy is in place, so that specific
  pull-side gain should be treated as unconfirmed until the next audit explains
  whether a real dirty scope or a secondary path kept it active

Next bottleneck:
- split remaining end-to-end overhead between engine work and host/UI polling
- explain why `support_tickets` still materialized during the scoped full run
- reduce the exhaustive `22`-page no-op full path, which is still the main
  cost outlier

## Iteration 8

Target:
- measure the real UI-driven full-sync path instead of the old lock-only proxy
- remove post-sync provider refresh from the active sync state

Why:
- the engine had already reached sub-`3000ms` combined push-plus-pull once,
  but the dashboard-driven live cycle was still above the user-facing target
- audit showed `/driver/sync-status` reported only the shared sync gate, while
  the dashboard button/spinner used `SyncStatusStore`
- `SyncProvider` also kept `isSyncing` true during the post-sync provider
  refresh callback, which inflated the visible sync window

Status:
- implemented and measured

Implementation:
- `/driver/sync-status` now exposes UI sync state from `SyncStatusStore` plus
  a separate `syncGateActive` diagnostic
- `measure-device-sync.ps1` now measures against the UI sync state and captures
  gate activity separately; polling default is now `100ms`
- `SyncProvider.fullSync()` and `quickSync()` now return once the sync cycle
  itself completes instead of waiting for the post-sync provider refresh
- post-sync provider refresh no longer reuses `isDownloading` as a fake
  extension of the sync state

Verification:
- `dart analyze lib/core/driver/driver_data_sync_handler_local_query_routes.dart lib/features/sync/presentation/providers/sync_provider.dart lib/features/sync/presentation/providers/sync_provider_listeners.dart test/features/sync/presentation/providers/sync_provider_test.dart`
- `flutter test test/features/sync/presentation/providers/sync_provider_test.dart`
- PowerShell parse check for `tools/measure-device-sync.ps1`

Key live results:
- focused live S21 UI proof:
  - `tools/testing/test-results/2026-04-22/live-sync-performance-ui-cycle-S21-20260422-iteration8/summary.json`
  - `medium-row-full` observed duration `5563ms`
  - push `2893ms`
  - pull `1751ms`
  - maintenance `66ms`
  - checkpoint `32ms`

Outcome:
- the UI measurement path is now aligned with the dashboard state instead of
  the advisory lock alone
- the remaining gap is not just timing semantics; the live medium full path is
  still engine-bound, especially in push
- the run confirmed a large fixed push-prelude cost beyond the per-table push
  timings, so the next optimization needed to target create-heavy push setup

Next bottleneck:
- reduce pre-table push overhead on create-heavy batches
- keep the UI-driven proof on the real dashboard button for acceptance

## Iteration 9

Target:
- remove unnecessary LWW timestamp prefetch on true insert operations

Why:
- Iteration 8 showed push remained the dominant hotspot on the medium full UI
  path
- per-table push timings accounted for only part of total `pushMs`
- the staged medium scenario is create-heavy, so paying LWW timestamp fetches
  for new inserts was avoidable overhead

Status:
- implemented and measured

Implementation:
- `PushHandler._primeLwwChecks()` now skips LWW priming for insert changes
- `PushExecutionRouter.prepareBulkUpsert()` and `_pushUpsert()` now keep LWW
  checks for updates but skip them for inserts
- updated `push_handler_test.dart` so update-path LWW coverage uses the batched
  timestamp fetch path, and added coverage proving inserts skip LWW prefetch

Verification:
- `dart analyze lib/features/sync/engine/push_handler.dart lib/features/sync/engine/push_execution_router.dart test/features/sync/engine/push_handler_test.dart`
- `flutter test test/features/sync/engine/push_handler_test.dart`
- `flutter test test/features/sync/engine/sync_engine_lww_test.dart --plain-name "uses prefetched server timestamps when primed for a table"`

Key live results:
- focused live S21 UI proof:
  - `tools/testing/test-results/2026-04-22/live-sync-performance-ui-cycle-S21-20260422-iteration9/summary.json`
  - `medium-row-full` observed duration `4798ms`
  - transport duration `4083ms`
  - push `2550ms`
  - pull `1474ms`
  - maintenance `44ms`
  - checkpoint `13ms`

Outcome:
- the insert-only LWW optimization produced a real live improvement:
  - observed UI duration `5563ms -> 4798ms`
  - push `2893ms -> 2550ms`
  - pull `1751ms -> 1474ms`
- the medium full UI path is still above the `3000ms` target on live Supabase
- the next bottleneck is still the fixed push prelude plus the remaining
  7-page scoped full pull, not checkpoint proof or maintenance

Next bottleneck:
- break down and reduce the non-table portion of `pushMs`
- further narrow or accelerate the remaining scoped full pull fan-out on the
  medium full dashboard path

## Iteration 10

Target:
- harden the live matrix script so end-of-run summary writing cannot fail
- measure the current pull-page and push-prelude reductions on the real S21

Why:
- the matrix script had repeatedly failed after the live run completed, which
  made the artifact lane unreliable
- the current worktree already included a larger pull page size and lighter
  push queue enumeration, so the right next move was to prove those changes
  live before adding more code

Status:
- implemented and measured

Implementation:
- `tools/run-live-sync-performance-matrix.ps1` now writes `summary.json`
  first, reloads the normalized JSON shape, and generates `summary.md` from
  that normalized object
- the summary writer now falls back to a minimal markdown file instead of
  killing the run if markdown generation fails
- the live proof also carried forward the already-landed `pullPageSize=200`
  change plus the `ChangeTracker`/`PushTablePlanner` prelude reductions

Verification:
- PowerShell parse check for `tools/run-live-sync-performance-matrix.ps1`
- successful live S21 summary write:
  - `tools/testing/test-results/2026-04-22/live-sync-performance-ui-cycle-S21-20260422-iteration10c/summary.json`
  - `tools/testing/test-results/2026-04-22/live-sync-performance-ui-cycle-S21-20260422-iteration10c/summary.md`

Key live results:
- focused live S21 UI proof:
  - `tools/testing/test-results/2026-04-22/live-sync-performance-ui-cycle-S21-20260422-iteration10c/summary.json`
  - `medium-row-full` observed duration `4634ms`
  - push `2677ms`
  - pull `1188ms`
  - maintenance `62ms`
  - checkpoint `14ms`

Outcome:
- the script-artifact lane is stable again; summary writing is no longer a
  false failure at the end of the run
- the larger pull pages materially reduced pull time and page fan-out
- push was still the dominant remaining bottleneck on the create-heavy medium
  path

Next bottleneck:
- remove remaining per-row local work after bulk upsert
- keep pressure on the fixed push tail before chasing more pull changes

## Iteration 11

Target:
- remove the sequential local timestamp write-back tail after bulk upsert

Why:
- audit of the bulk path showed that even after `upsertRecords()` succeeded,
  the client still wrote back the server `updated_at` one row at a time under
  trigger suppression
- on a `100`-row create-heavy sync, that meant repeated trigger toggles and
  local SQLite updates after the remote batch was already done

Status:
- implemented and measured

Implementation:
- `LocalRecordStore` now exposes `writeBackServerTimestamps()` for batched
  local `updated_at` write-back under a single trigger-suppressed block
- `LocalSyncStoreRecords` now forwards the new batched write-back helper
- `PushExecutionRouter.executeBulkUpsert()` now collects remote timestamp
  changes and applies them through the batched local write-back path
- `push_handler_contract_test.dart` now verifies that bulk upsert writes the
  returned server timestamps back to every pushed row

Verification:
- `dart analyze lib/features/sync/engine/local_record_store.dart lib/features/sync/engine/local_sync_store_records.dart lib/features/sync/engine/push_execution_router.dart test/features/sync/engine/push_handler_contract_test.dart`
- `flutter test test/features/sync/engine/push_handler_contract_test.dart test/features/sync/engine/push_handler_test.dart`

Key live results:
- focused live S21 UI proof:
  - `tools/testing/test-results/2026-04-22/live-sync-performance-ui-cycle-S21-20260422-iteration11/summary.json`
  - `medium-row-full` observed duration `3885ms`
  - push `1899ms`
  - pull `1268ms`
  - maintenance `53ms`
  - checkpoint `13ms`
  - combined push-plus-pull `3167ms`

Outcome:
- the batched timestamp write-back cut the remaining push tail substantially
- this left the lane only `167ms` above the combined push-plus-pull target
- the next likely win was to remove more duplicated per-row local scope lookup
  work on the same create-heavy tables

Next bottleneck:
- avoid repeated project-scope lookups when the push path already resolved the
  dirty pull scope for the row

## Iteration 12

Target:
- reuse the already-resolved project scope when emitting sync hints

Why:
- audit showed `_prepareUpsertInput()` already computed `suggestedPullScope`
  for each row, but `_emitSyncHint()` resolved the same project again
- for `viaEntry` rows without a direct `project_id`, that meant extra
  `daily_entries` lookups even though the needed project ID was already known

Status:
- implemented and measured

Implementation:
- `PushExecutionRouter._emitSyncHint()` now accepts a pre-resolved `projectId`
- bulk and single-row push paths now pass `suggestedPullScope?.projectId` into
  `_emitSyncHint()` instead of forcing another scope lookup
- delete and preserved-tombstone paths reuse the same resolved project scope
  for their sync-hint emission

Verification:
- `dart analyze lib/features/sync/engine/push_execution_router.dart`
- `flutter test test/features/sync/engine/push_handler_contract_test.dart test/features/sync/engine/push_handler_test.dart`

Key live results:
- focused live S21 UI proof:
  - `tools/testing/test-results/2026-04-22/live-sync-performance-ui-cycle-S21-20260422-iteration12/summary.json`
  - `medium-row-full` observed duration `3364ms`
  - push `1583ms`
  - pull `1098ms`
  - maintenance `27ms`
  - checkpoint `27ms`
  - combined push-plus-pull `2681ms`

Outcome:
- the live S21 medium full lane is now back under the requested
  sub-`3000ms` combined push-plus-pull target on live Supabase
- the broader observed UI-driven full-sync cycle is still above `3000ms`, so
  the remaining gap is now outside the core push-plus-pull engine budget

Next bottleneck:
- isolate the remaining non-engine whole-cycle overhead between sync
  completion, diagnostics refresh, and dashboard/UI polling if the stricter
  observed end-to-end target becomes the next lane
