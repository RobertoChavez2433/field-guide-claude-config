# Sync Soak Unified Live Task List

Date: 2026-04-18
Status: active session checklist
Controlling spec: `.codex/plans/2026-04-18-sync-soak-unified-hardening-todo.md`
Implementation log: `.codex/checkpoints/2026-04-18-sync-soak-unified-implementation-log.md`

## Current Rule

Check off an item only after the implementation exists and the required local
or device evidence has been recorded in the implementation log. Device lanes
must use real sessions, the refactored flow path, UI-triggered sync, and
`directDriverSyncEndpointUsed=false`.

## Current Focus - P1 Sync Engine Reconciliation Probe

- [x] Re-read the controlling todo, implementation log, live task list, and
  working tree before continuing.
- [x] Add `/driver/local-reconciliation-snapshot` as a read-only debug route.
- [x] Return per-table row counts, selected-column stable SHA-256 hash,
  sample ids, sample rows, truncation state, and hash scope from local SQLite.
- [x] Add `tools/sync-soak/Reconciliation.ps1` with local/remote snapshot
  comparison and mismatch classification.
- [x] Add `/driver/remote-reconciliation-snapshot` so remote snapshots use the
  app's real Supabase device session instead of host service-role credentials.
- [x] Add required project-scope table spec helper covering projects,
  assignments, daily entries, quantities, photos, form responses, signatures,
  documents, pay applications, and export artifact families.
- [x] Treat `form_exports`, `export_artifacts`, and `entry_exports` as
  included local-only export-history snapshots; do not remote-compare those
  tables while the adapters remain `skipPush`/`skipPull`.
- [x] Compare active row membership for synced tables by stable IDs/project
  IDs; tombstone retention/cleanup stays in the delete/cleanup gates.
- [x] Add focused Dart route/handler tests and PowerShell harness tests.
- [x] Run focused local gates:
  - `dart analyze` on the touched driver route/handler files and tests.
  - `flutter test test/core/driver/driver_data_sync_handler_test.dart test/core/driver/driver_data_sync_routes_test.dart -r expanded`.
  - `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`.
  - `git diff --check`.
- [x] Rebuild/restart S21 and S10 debug driver apps so the running devices
  include the new route.
- [x] Device-probe S21 and S10:
  - `/driver/ready` returned ready.
  - `/driver/change-log` returned `count=0`, `unprocessedCount=0`,
    `blockedCount=0`, `maxRetryCount=0`.
  - `/driver/sync-status` returned idle with `pendingCount=0`,
    `blockedCount=0`, `unprocessedCount=0`.
  - `/driver/local-reconciliation-snapshot?table=projects&select=id,updated_at&limit=100`
    returned full, non-truncated hashes.
- [x] Wire the reconciliation probe into accepted post-sync flow artifacts and
  fail covered lanes on local/remote count/hash mismatches.
- [x] Prove the gate on S21:
  `20260418-s21-sync-only-active-reconciliation-gate-rerun` passed with
  `queueDrainResult=drained`, `runtimeErrors=0`, `loggingGaps=0`,
  `blockedRowCount=0`, `unprocessedRowCount=0`, `maxRetryCount=0`,
  `directDriverSyncEndpointUsed=false`, `reconciliationProjectCount=1`,
  `reconciliationTableCount=13`, and `reconciliationFailedCount=0`.
- [x] Preserve the first failing gate artifact:
  `20260418-s21-sync-only-reconciliation-gate` failed only on reconciliation
  (`reconciliationFailedCount=6`) while queue/runtime/logging/direct-sync
  gates were clean, proving the gate fails covered lanes on mismatch.

## Current Focus - P1 File, Storage, And Attachment Hardening

- [x] Resume point captured after accepted saved-form/gallery lifecycle proof.
- [x] Working tree reviewed before continuing: only the unified todo and
  implementation log are modified in tracked files; this live task list is
  intentionally ignored but persisted on disk.
- [x] Inventory current production file-backed families, storage buckets,
  cleanup queues, and harness/device proof helpers.
- [x] Identify which P1 file/storage items can be closed by existing
  production evidence versus which require new implementation.
- [x] Implement the next smallest hardening slice without weakening the
  real-session/refactored-flow/UI-sync acceptance rules.
- [x] Run focused local gates for the changed code.
- [x] Verify the slice on device where the checklist requires live storage or
  cross-device evidence. The image-fixture slice is local-engine coverage; S21
  and S10 driver hygiene probes were still recorded after the local change.
- [x] Update the controlling todo and implementation log only after evidence
  exists.

## Immediate Slice C - MDOT 1126 Export Proof

- [x] Review working tree before continuing the interrupted run.
- [x] Verify Slice A/B code and harness still pass after resuming:
  - `/driver/local-file-head` route and tests;
  - `Flow.Mdot1126Export.ps1`;
  - `Get-SoakDriverLocalFileHead`;
  - `mdot1126-export-only` dispatcher/module/entrypoint wiring.
- [x] Rebuild/restart the S21 debug driver app so `/driver/local-file-head`
  is available in the running app.
- [x] Rebuild/restart the S10 debug driver app so `/driver/local-file-head`
  is available in the running app.
- [x] Confirm S21 `/driver/ready`, `/driver/change-log`, and
  `/driver/sync-status` are clean before mutation.
- [x] Confirm S10 `/driver/ready`, `/driver/change-log`, and
  `/driver/sync-status` are clean before regression.
- [x] Run S21 `mdot1126-export-only` initial attempt:
  `20260418-s21-mdot1126-export-initial` failed cleanly with
  `widget_wait_timeout`, final queue drained, `runtimeErrors=0`,
  `loggingGaps=0`, and `directDriverSyncEndpointUsed=false`.
- [x] Fix the initial export-flow blocker by accepting the report-attached
  export branch that skips `form_export_decision_dialog` and waits for the
  standalone export dialog.
- [x] Rebuild/restart S21 after the report-attached export branch fix.
- [x] Rerun S21 `mdot1126-export-only`:
  `20260418-s21-mdot1126-export-after-attached-branch-fix` passed with
  local export rows, local file size/hash proof, no export-table
  `change_log`, ledger cleanup, signature storage cleanup, final queue drain,
  `runtimeErrors=0`, `loggingGaps=0`, and
  `directDriverSyncEndpointUsed=false`.
- [x] Accept S21 only if the artifact proves:
  - report-attached saved form source;
  - local `form_exports` row;
  - local `export_artifacts` row;
  - local file exists at the row path with expected size/hash;
  - `form_exports` and `export_artifacts` do not emit `change_log` rows;
  - signature remote path/storage proof still holds for the underlying form;
  - ledger-owned cleanup;
  - UI-triggered cleanup sync;
  - final empty queue;
  - `runtimeErrors=0`;
  - `loggingGaps=0`;
  - `blockedRowCount=0`;
  - `unprocessedRowCount=0`;
  - `maxRetryCount=0`;
  - `directDriverSyncEndpointUsed=false`.
- [x] S21 failure recovery was not needed after the accepted rerun; preserve
  the clean initial failure artifact as diagnostic evidence.
- [x] Rebuild/restart S10 after the report-attached export branch fix.
- [x] Recover S10 through UI `sync-only` if the pre-existing
  `form_responses` queue row is still present.
- [x] Run S10 `mdot1126-export-only` regression after S21 acceptance:
  `20260418-s10-mdot1126-export-after-attached-branch-fix` passed with local
  export rows, local file size/hash proof, no export-table `change_log`,
  ledger cleanup, signature storage cleanup, final queue drain,
  `runtimeErrors=0`, `loggingGaps=0`, and
  `directDriverSyncEndpointUsed=false`.
- [x] Record accepted artifact paths in the implementation log.
- [x] Check off the `mdot_1126` item under P1 Builtin Form Export Proof in the
  controlling spec only after S21 and S10 evidence are accepted.

## P1 Builtin Form Export Proof

- [x] Generalize the MDOT 1126 export proof helpers only after the first
  accepted run proves the contract.
- [x] Implement/refactor `mdot0582b-export-only`.
- [x] Accept `mdot0582b-export-only` on S21:
  `20260418-s21-mdot0582b-export-initial` passed with local export rows,
  local file size/hash proof, no export-table `change_log`, cleanup, final
  queue drain, `runtimeErrors=0`, `loggingGaps=0`, and
  `directDriverSyncEndpointUsed=false`.
- [x] Run `mdot0582b-export-only` S10 regression:
  `20260418-s10-mdot0582b-export-initial` passed with the same export,
  cleanup, queue, runtime, logging, and direct-sync gates.
- [x] Implement/refactor `mdot1174r-export-only`.
- [x] Accept `mdot1174r-export-only` on S21:
  `20260418-s21-mdot1174r-export-initial` passed with local export rows,
  local file size/hash proof, no export-table `change_log`, cleanup, final
  queue drain, `runtimeErrors=0`, `loggingGaps=0`, and
  `directDriverSyncEndpointUsed=false`.
- [x] Run `mdot1174r-export-only` S10 regression:
  `20260418-s10-mdot1174r-export-initial` passed with the same export,
  cleanup, queue, runtime, logging, and direct-sync gates.
- [x] Update the controlling todo with exact artifact IDs for every accepted
  export lane.

## P1 Saved-Form And Gallery Lifecycle

- [x] Add or wire a refactored saved-form/gallery lifecycle flow.
- [x] Create saved form from `/report/:entryId`.
- [x] Reopen the saved form from the form gallery.
- [x] Edit and save the previously created form.
- [x] Exercise the export decision path.
- [x] Delete/cleanup through production UI/service seams.
- [x] Prove local and remote absence after cleanup.
- [x] Accept lifecycle sweep for `mdot_1126` on S21 and S10.
- [x] Accept lifecycle sweep for `mdot_0582b` on S21 and S10.
- [x] Accept lifecycle sweep for `mdot_1174r` on S21 and S10.

Accepted evidence:

- S21 `20260418-s21-form-gallery-lifecycle-final-build` passed with
  `queueDrainResult=drained`, `failedActorRounds=0`, `runtimeErrors=0`,
  `loggingGaps=0`, `blockedRowCount=0`, `unprocessedRowCount=0`,
  `maxRetryCount=0`, and `directDriverSyncEndpointUsed=false`.
- S10 `20260418-s10-form-gallery-lifecycle-after-expanded-hub-key` passed
  with the same queue, runtime, logging, and direct-sync gates.
- S21 ledger rows:
  `mdot_1126` `form_responses/0daa8349-cc23-4eaa-895e-bbcef8b7e2e7`,
  `mdot_0582b` `form_responses/9685c4a9-ba17-4701-bf25-bc4147870571`,
  and `mdot_1174r`
  `form_responses/7a8f2c49-0c4f-4b7d-9ba3-4afb81f2da66`.
- S10 ledger rows:
  `mdot_1126` `form_responses/99a2fb1c-38fe-4817-b01d-694d522ade7b`,
  `mdot_0582b` `form_responses/5aed14a2-273d-4e7f-b512-c109b9a8d74f`,
  and `mdot_1174r`
  `form_responses/aac12ea1-6cee-476a-becc-717b99d92d9b`.

## P1 File, Storage, And Attachment Hardening

- [x] Extend object proof beyond photos/signatures to form exports under the
  current adapter contract: form-export families are local-only byte/history,
  with accepted local row/file/hash proof instead of remote object proof.
- [x] Extend object proof to entry documents.
- [x] Extend object proof to entry exports under the current adapter contract:
  entry exports are local-only history and included in local-only diagnostics.
- [x] Extend object proof to pay-app exports under the current adapter
  contract: pay-app export artifacts are local file/history rows with cleanup
  queue coverage.
- [x] Add unauthorized storage access denial proof for each applicable remote
  bucket/path family.
- [x] Add image fixture coverage for small, normal, large, and GPS-EXIF files.
- [x] Prove cross-device download/preview of uploaded objects.
- [x] Add `storage_cleanup_queue` assertions for delete/restore/purge paths.
- [x] Add durable attachment state assertions for upload, row upsert, local
  bookmark, stale-object cleanup, and cleanup retries.
- [x] Add crash/retry cases around upload, row upsert, bookmark, change-log
  processing, and storage delete failure.
  - [x] After upload before row upsert: phase-2 failure cleans up the newly
    uploaded object and rethrows the phase-2 error.
  - [x] After row upsert before bookmark: missing local bookmark target now
    fails phase 3 and records `local_bookmark_failed`.
  - [x] After bookmark before `change_log` processed: replay with
    `remote_path` already bookmarked and `change_log` still pending skips
    duplicate upload, creates no extra `change_log`, and drains after
    `markProcessed`.
  - [x] After storage delete failure before cleanup retry: stale object delete
    failure queues `storage_cleanup_queue` and records durable cleanup state.
- [x] Complete PowerSync attachment-helper reuse triage before implementing new
  attachment queue primitives.

Accepted local and device hygiene evidence:

- File-backed inventory: photos `entry-photos`, signatures `signatures`,
  documents `entry-documents`, entry exports `entry-exports`, form exports
  `form-exports`, export artifacts `export-artifacts`, and pay-application
  artifact references.
- `dart analyze lib/features/sync/engine/file_sync_three_phase_workflow.dart test/features/sync/engine/file_sync_handler_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/file_sync_handler_test.dart -r expanded`
  passed 18 tests, including small, normal, large, and GPS-EXIF JPEG upload
  fixtures.
- `dart analyze lib/shared/datasources/generic_local_datasource.dart test/features/pay_applications/data/datasources/local/export_artifact_local_datasource_test.dart`
  passed with no issues.
- `flutter test test/features/pay_applications/data/datasources/local/export_artifact_local_datasource_test.dart -r expanded`
  passed 4 tests covering local path caching, soft-delete cleanup queueing,
  restore cleanup cancellation, and purge cleanup queueing.
- S21 driver hygiene after the slice: ready on `/sync/dashboard`, empty
  `change_log`, `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.
- S10 driver hygiene after the slice: ready on `/sync/dashboard`, empty
  `change_log`, `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.

## Immediate Slice K - Entry Document Live Storage Proof

- [x] Resume from the failed S21 entry-document object proof and inspect the
  retained diagnostic artifact.
- [x] Patch unauthorized-storage denial classification for private buckets that
  return HTTP 400 with `Bucket not found` when invalid credentials cannot see
  the bucket.
- [x] Add PowerShell harness coverage for the hidden-bucket denial response.
- [x] Run `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`.
- [x] Confirm S21 preflight is clean before rerun:
  - `/driver/ready` ready on `/sync/dashboard`;
  - `/driver/change-log` empty with `unprocessedCount=0`,
    `blockedCount=0`, `maxRetryCount=0`;
  - `/driver/sync-status` idle with `pendingCount=0`,
    `blockedCount=0`, `unprocessedCount=0`.
- [x] Rerun S21 `documents-only` through the refactored flow and UI-triggered
  Sync Dashboard sync.
- [x] Accept only if the artifact proves local document row creation,
  pre-sync `change_log`, post-sync remote row, authorized storage bytes/hash,
  unauthorized denial for the same bucket/path, ledger-owned cleanup,
  storage delete/absence, final queue drain, `runtimeErrors=0`,
  `loggingGaps=0`, and `directDriverSyncEndpointUsed=false`.

Accepted evidence:

- Diagnostic first run:
  `20260418-s21-documents-entry-object-proof-initial` failed only because the
  denial classifier did not yet accept Supabase's private-bucket HTTP 400
  `Bucket not found` shape. The same run proved document row sync,
  authorized storage bytes, cleanup sync, storage delete/absence, and clean
  queue/runtime/direct-sync gates.
- Accepted rerun:
  `20260418-s21-documents-entry-object-proof-after-denial-classifier` passed
  with `queueDrainResult=drained`, `failedActorRounds=0`, `runtimeErrors=0`,
  `loggingGaps=0`, `blockedRowCount=0`, `unprocessedRowCount=0`,
  `maxRetryCount=0`, and `directDriverSyncEndpointUsed=false`.
- Accepted row/object proof:
  `documents/b4efc514-b14f-41e4-a257-b5ef0989ed5a`,
  remote path
  `docs/26fe92cd-7044-4412-9a09-5c5f49a292f9/f14d87c1-d870-444e-ba2b-bca5762aa485/enterprise_soak_doc_S21_round_1_214458.pdf`,
  bucket `entry-documents`, 48 bytes, SHA-256
  `d7aacd14db7ca489d86ca71c834ac5513f54cbfbab168d7929c086b6a7e61dc6`,
  authorized storage HTTP 200.
- Unauthorized proof for that same bucket/path passed with HTTP 400
  `{"statusCode":"404","error":"Bucket not found","message":"Bucket not found"}`.
- Ledger cleanup passed with UI-triggered cleanup sync, storage delete passed,
  and storage absence proof passed.

## Immediate Slice L - Remote Object Denial And Cross-Device Download

- [x] Run S21 `photo-only` after wiring unauthorized storage denial proof.
- [x] Run S21 `mdot1126-signature-only` after wiring unauthorized storage
  denial proof.
- [x] Restore S21/S10 driver reachability after device rebuilds changed ADB
  forwards.
- [x] Drain S10 residual signature cleanup rows through UI-triggered
  `sync-only` before cross-device proof.
- [x] Add `documents-cross-device-only` as a refactored flow.
- [x] Wire `documents-cross-device-only` through the lab entrypoint,
  dispatcher, module loader, concurrent soak entrypoint, and harness tests.
- [x] Run `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` after the
  new flow wiring.
- [x] Rebuild/restart S10 with document download/cache code and restore S21.
- [x] Confirm S21 and S10 preflight queues are clean.
- [x] Run S21-to-S10 `documents-cross-device-only` and accept only with:
  source UI-created document, source UI-triggered sync, remote row/object
  proof, unauthorized denial, receiver UI-triggered pull, receiver document
  tile tap, receiver local file hash matching storage hash, source
  ledger-owned cleanup, receiver cleanup pull, final clean queues, zero
  runtime/logging gaps, and `directDriverSyncEndpointUsed=false`.

Accepted evidence:

- S21 photo denial proof:
  `20260418-s21-photo-storage-denial-proof` passed with
  `photos/799779ce-b41f-4ea0-bea2-f92e72bc14ed`, bucket `entry-photos`,
  remote path
  `entries/26fe92cd-7044-4412-9a09-5c5f49a292f9/f14d87c1-d870-444e-ba2b-bca5762aa485/enterprise_soak_S21_round_1_214730.jpg`,
  68 bytes, SHA-256
  `1dae93d61eceabd7ce356b2be0acf0d2b813bf595f5cbae775a88582fd4ad278`,
  and unauthorized HTTP 400 `Bucket not found` denial.
- S21 signature denial proof:
  `20260418-s21-mdot1126-signature-storage-denial-proof` passed with
  `signature_files/a5d373fd-4096-4ea5-8406-476db56196f0`, bucket
  `signatures`, remote path
  `signatures/26fe92cd-7044-4412-9a09-5c5f49a292f9/75ae3283-d4b2-4035-ba2f-7b4adb018199/a5d373fd-4096-4ea5-8406-476db56196f0.png`,
  5193 bytes, SHA-256
  `95c0ab2bfc32859719ec0de97ebaf4710e2dfb605fc5751cd54e90a398912755`,
  and unauthorized HTTP 400 `Bucket not found` denial.
- S10 residue drain:
  `20260418-s10-post-signature-denial-residue-sync-only` passed through the
  Sync Dashboard with final clean queue after S10 observed the signature
  cleanup rows.
- S21-to-S10 cross-device download proof:
  `20260418-s21-s10-documents-cross-device-download-proof` passed with
  `queueDrainResult=drained`, `failedActorRounds=0`, `runtimeErrors=0`,
  `loggingGaps=0`, `blockedRowCount=0`, `unprocessedRowCount=0`,
  `maxRetryCount=0`, `directDriverSyncEndpointUsed=false`, and final clean
  queues on both actors.
- Cross-device document:
  `documents/b8f80b06-9e14-4ff4-9e38-0be0e7cbf8f1`, bucket
  `entry-documents`, remote path
  `docs/26fe92cd-7044-4412-9a09-5c5f49a292f9/f14d87c1-d870-444e-ba2b-bca5762aa485/enterprise_soak_cross_device_doc_S21_to_S10_round_1_215611.pdf`,
  48 bytes, SHA-256
  `d7aacd14db7ca489d86ca71c834ac5513f54cbfbab168d7929c086b6a7e61dc6`.
- Receiver proof:
  S10 pulled the row via UI sync, tapped
  `document_tile_b8f80b06-9e14-4ff4-9e38-0be0e7cbf8f1`, cached a local file,
  and `/driver/local-file-head` returned `exists=true`, 48 bytes, and the same
  SHA-256 as the source storage proof. S10 then pulled the source cleanup and
  observed `deleted_at`.

## P1 Role, Scope, Account, And RLS Sweeps

- [ ] Inventory real account fixtures and UI keys for admin, inspector,
  engineer, and office technician.
- [ ] Run role sweeps with real sessions and no `MOCK_AUTH`.
- [ ] Prove denied routes and hidden controls for project management, PDF
  import, pay-app management, trash, admin, export/download, and previews.
- [ ] Add same-device account switching coverage.
- [ ] Prove providers, selected project, realtime channels, local scope cache,
  Sync Dashboard state, screenshots, and logs do not leak stale account data.
- [ ] Treat grants and revocations as sync changes.

## P1 Sync Engine Correctness Hardening

- [x] Replace offset/range pull pagination with stable keyset/checkpoint
  pagination.
- [x] Add equal-`updated_at`, concurrent insert, long-offline pull, and partial
  page restart tests.
  - [x] Equal `updated_at` rows continue across page boundaries by `id`.
  - [x] Remote inserts during a pull are visible after the keyset boundary.
  - [x] Long-offline pull drains many keyset pages.
  - [x] Restart resumes after a stored full-page keyset checkpoint.
  - [x] Restart replays a partial final page after an apply-time crash.
- [x] Add per-scope reconciliation probes for required sync tables.
  - [x] Local driver snapshot endpoint implemented and device-proven on
    S21/S10.
  - [x] Remote driver snapshot endpoint implemented with real device-session
    Supabase reads.
  - [x] Sync-soak harness comparison primitive implemented with count/hash
    mismatch classification.
  - [x] Post-sync flow artifact wiring and remote comparison acceptance gate
    proven on S21 with 13 table specs and zero reconciliation failures.
- [x] Add write-checkpoint semantics: queue drain, remote proof, next-pull
  proof, and final local proof.
  - [x] Queue-drain proof blocks `last_sync_time` advancement when pending
    local changes remain after sync.
  - [x] Remote write proof now verifies each per-record acknowledged write.
  - [x] Follow-up pull path proof blocks freshness when a cycle pushed local
    writes but skipped pull.
  - [x] Final local proof verifies per-record visibility through the
    server/pull path.
- [x] Keep sync freshness false until the local write is visible through the
  server/pull path.
  - [x] Freshness is now blocked when the final queue is not drained.
  - [x] Freshness is now blocked when pushed writes did not get a follow-up
    pull path.
  - [x] Per-record server/pull visibility proof is implemented and covered.
- [x] Prove realtime hints are only hints with missed, delayed, duplicate, and
  out-of-order hint cases plus fallback polling.
- [x] Add idempotent replay tests for duplicate pushes, duplicate pulls,
  duplicate applies, duplicate deletes, absent rows, storage 409s, row upsert
  replay, and bookmark replay.
  - [x] Duplicate pull page replay and duplicate row apply are covered in
    `pull_handler_test.dart`; replayed pages leave a single row per id and
    produce `pulled=0` when `updated_at` matches.
  - [x] Already-absent remote row replay is verified through
    `sync_engine_delete_test.dart` and `supabase_sync_contract_test.dart`.
  - [x] Storage 409/already-exists replay is verified through
    `file_sync_handler_test.dart`.
  - [x] Remaining replay classes have explicit indexed coverage in
    `push_handler_test.dart`, `file_sync_handler_test.dart`, and
    `local_sync_store_contract_test.dart`.
- [x] Add crash/restart tests around `pulling=1`, sync locks, cursors,
  conflict re-push, auth refresh, and background retry scheduling.
- [x] Split conflict strategy by domain.
- [x] Fix misleading file-sync phase logging.

## Immediate Slice D - Idempotent Replay Matrix Completion

- [x] Resume from the accepted S21 active-row reconciliation gate and refresh
  the working tree before continuing.
- [x] Inspect existing push, soft-delete, upload, row-upsert, and bookmark
  replay tests before adding new coverage.
- [x] Add or verify explicit replay coverage for duplicate local push after
  remote upsert succeeds.
- [x] Add or verify explicit replay coverage for duplicate soft-delete push.
- [x] Add or verify explicit replay coverage for duplicate upload.
- [x] Add or verify explicit replay coverage for row upsert replay.
- [x] Add or verify explicit replay coverage for bookmark replay.
- [x] Run focused `dart analyze` for touched sync/file tests and helpers.
- [x] Run focused `flutter test` for the replay matrix files.
- [x] Run `git diff --check`.
- [x] Probe S21 and S10 driver hygiene after local gates if the running
  devices are reachable.
- [x] Update the controlling todo and implementation log only after evidence
  exists.

Accepted local evidence:

- Added replay matrix coverage in:
  - `push_handler_test.dart` for duplicate local push after remote upsert and
    duplicate soft-delete push when the remote row is already gone.
  - `file_sync_handler_test.dart` for duplicate upload replay where storage
    already has the object and row-upsert replay with an existing
    `remote_path`.
  - `local_sync_store_contract_test.dart` for idempotent bookmark replay with
    trigger suppression and no `change_log` pollution.
- `dart analyze test/features/sync/engine/push_handler_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/sync_engine_delete_test.dart test/features/sync/engine/supabase_sync_contract_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/push_handler_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/sync_engine_delete_test.dart test/features/sync/engine/supabase_sync_contract_test.dart -r expanded`
  passed 118 tests.
- `git diff --check` passed with line-ending warnings only.
- S21 driver hygiene after the slice: `/driver/ready` ready on
  `/sync/dashboard`, empty `change_log`, `pendingCount=0`, `blockedCount=0`,
  `unprocessedCount=0`, `isSyncing=false`.
- S10 driver hygiene after the slice: `/driver/ready` ready on `/projects`,
  empty `change_log`, `pendingCount=0`, `blockedCount=0`,
  `unprocessedCount=0`, `isSyncing=false`.

## Immediate Slice E - Write-Checkpoint Freshness Guard

- [x] Inspect current `last_sync_time` / freshness code path.
- [x] Persist an engine-level guard that blocks fresh sync metadata when the
  final local queue is not drained.
- [x] Persist an engine-level guard that blocks fresh sync metadata when local
  writes were pushed but no follow-up pull path ran in the same cycle.
- [x] Add focused engine status tests for queue-drain proof failure.
- [x] Add focused engine status tests for pushed-without-pull freshness
  failure.
- [x] Run focused `dart analyze` for the changed engine/test files.
- [x] Run focused `flutter test` for the engine freshness tests.
- [x] Run `git diff --check`.
- [x] Probe S21 and S10 driver hygiene after local gates if reachable.
- [x] Update the controlling todo and implementation log only after evidence
  exists.

Accepted local evidence:

- `SyncEngine` now verifies freshness before writing `last_sync_time`:
  final pending upload/change count must be zero, and any cycle with pushed
  writes must have attempted a pull path.
- `sync_engine_status_test.dart` now covers queue residue after an otherwise
  clean push/pull and pushed writes during strict quick sync with no pull.
- `dart analyze lib/features/sync/engine/sync_engine.dart lib/features/sync/engine/sync_run_lifecycle.dart test/features/sync/engine/sync_engine_status_test.dart test/features/sync/engine/sync_engine_mode_plumbing_test.dart test/features/sync/engine/sync_engine_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/sync_engine_status_test.dart test/features/sync/engine/sync_engine_mode_plumbing_test.dart -r expanded`
  passed 11 tests.
- `git diff --check` passed with line-ending warnings only.
- S21 driver hygiene after the slice: ready on `/sync/dashboard`, empty
  `change_log`, `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.
- S10 driver hygiene after the slice: ready on `/projects`, empty
  `change_log`, `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.

## Immediate Slice F - Per-Record Write Checkpoint Proof

- [x] Re-read the controlling todo, implementation log, live task list, sync
  rules, and working tree before continuing.
- [x] Carry per-record acknowledged write identities out of the push path.
- [x] Preserve aggregate push semantics while excluding skipped/LWW-only work
  from remote-write proof.
- [x] Add a write-checkpoint verifier that reads the app's real Supabase
  boundary for each acknowledged row before freshness metadata advances.
- [x] Verify final local visibility after the follow-up pull path for each
  acknowledged row.
- [x] Fail freshness instead of writing `last_sync_time` when remote proof is
  missing, stale, deleted unexpectedly, or locally invisible after pull.
- [x] Add focused push/engine tests for acknowledged-write propagation,
  remote proof failure, local visibility failure, and successful proof.
- [x] Run focused `dart analyze` for changed sync engine files and tests.
- [x] Run focused `flutter test` for changed sync engine tests.
- [x] Run `git diff --check`.
- [x] Probe S21 and S10 driver hygiene after local gates if reachable.
- [x] Update the controlling todo and implementation log only after evidence
  exists.

Accepted local and device hygiene evidence:

- `PushResult` and `SyncEngineResult` now carry `acknowledgedWrites` for
  server-acknowledged upserts, insert-only rows, file metadata upserts, and
  soft deletes.
- `RemoteLocalWriteCheckpointVerifier` verifies each acknowledged write
  through `SupabaseSync.fetchRecord()` and `LocalSyncStore.readLocalRecord()`
  after the follow-up pull path before `last_sync_time` can advance.
- Skipped adapter/out-of-scope/LWW-only work preserves aggregate push counts
  but does not enter the remote-write proof set.
- Focused local gates passed:
  - `dart analyze lib/features/sync/engine/sync_write_checkpoint_proof.dart lib/features/sync/engine/sync_engine_result.dart lib/features/sync/engine/push_execution_router.dart lib/features/sync/engine/push_handler.dart lib/features/sync/engine/sync_engine.dart lib/features/sync/application/sync_engine_factory.dart test/features/sync/engine/sync_engine_status_test.dart test/features/sync/engine/push_handler_test.dart test/features/sync/engine/sync_write_checkpoint_proof_test.dart test/features/sync/application/sync_coordinator_test.dart`
  - `flutter test test/features/sync/engine/sync_engine_status_test.dart test/features/sync/engine/push_handler_test.dart test/features/sync/engine/sync_write_checkpoint_proof_test.dart test/features/sync/application/sync_coordinator_test.dart -r expanded`
    passed 41 tests.
  - `git diff --check` passed with line-ending warnings only.
- S21 driver hygiene after the slice: ready on `/sync/dashboard`, empty
  `change_log`, `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.
- S10 driver hygiene after the slice: ready on `/projects`, empty
  `change_log`, `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.

## Immediate Slice G - Crash/Restart Coverage

- [x] Resume after per-record write-checkpoint proof and refresh the open
  sync-engine correctness checklist.
- [x] Inspect existing coverage for `sync_control.pulling = '1'`, held
  `sync_lock`, cursor restart, manual conflict re-push, auth refresh, and
  background retry scheduling.
- [x] Add or verify focused tests for stale `pulling=1` recovery.
- [x] Add or verify focused tests for held `sync_lock` behavior.
- [x] Add or verify focused tests for cursor update/restart behavior.
- [x] Add or verify focused tests for manual conflict re-push insertion after
  local-wins conflict.
- [x] Add or verify focused tests for auth refresh retry behavior.
- [x] Add or verify focused tests for background retry scheduling.
- [x] Run focused `dart analyze` for changed sync-engine files and tests.
- [x] Run focused `flutter test` for changed sync-engine tests.
- [x] Run `git diff --check`.
- [x] Probe S21 and S10 driver hygiene after local gates if reachable.
- [x] Update the controlling todo and implementation log only after evidence
  exists.

Accepted local and device hygiene evidence:

- Existing `local_sync_store_contract_test.dart` verifies stale
  `sync_control.pulling = '1'` reset through `resetPullingFlag()`.
- Existing `sync_run_state_store_test.dart` verifies crash recovery clears both
  advisory `sync_lock` and stale `pulling=1`.
- Existing `sync_mutex_test.dart` verifies held-lock rejection, stale lock
  expiry, heartbeat expiry, clear-any-lock, release, and reacquire behavior.
- Existing `pull_handler_test.dart` verifies keyset cursor advancement,
  page-two failure cursor preservation, stored full-page checkpoint restart,
  and partial-final-page replay after apply-time crash.
- New `pull_handler_test.dart` coverage verifies a local-wins pull conflict
  inserts an unprocessed manual `change_log` update for re-push.
- Existing `push_handler_test.dart` verifies 401 auth refresh success retries
  the push and emits `SyncAuthRefreshed`; refresh failure leaves the row
  pending.
- Existing `sync_background_retry_scheduler_test.dart` verifies retry
  scheduling, cancel, no-session skip, DNS deferral/reschedule, retryable
  result reschedule, and permanent-error stop.
- Focused local gates passed:
  - `dart analyze test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/sync_run_state_store_test.dart test/features/sync/engine/sync_mutex_test.dart test/features/sync/application/sync_background_retry_scheduler_test.dart test/features/sync/engine/sync_engine_status_test.dart test/features/sync/engine/push_handler_test.dart test/features/sync/engine/sync_write_checkpoint_proof_test.dart lib/features/sync/engine/pull_handler.dart lib/features/sync/application/sync_background_retry_scheduler.dart`
  - `flutter test test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/sync_run_state_store_test.dart test/features/sync/engine/sync_mutex_test.dart test/features/sync/application/sync_background_retry_scheduler_test.dart test/features/sync/engine/sync_engine_status_test.dart test/features/sync/engine/push_handler_test.dart test/features/sync/engine/sync_write_checkpoint_proof_test.dart -r expanded`
    passed 117 tests.
  - `git diff --check` passed with line-ending warnings only.
- S21 driver hygiene after the slice: ready on `/sync/dashboard`, empty
  `change_log`, `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.
- S10 driver hygiene after the slice: ready on `/projects`, empty
  `change_log`, `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.

## Immediate Slice H - Realtime Hints Are Only Hints

- [x] Resume after crash/restart coverage and refresh the open realtime-hint
  checklist.
- [x] Inspect realtime hint handler, transport controller, dirty-scope tracker,
  fallback polling, and existing tests.
- [x] Add or verify missed-hint fallback polling convergence coverage.
- [x] Add or verify delayed-hint behavior coverage.
- [x] Add or verify duplicate-hint idempotence coverage.
- [x] Add or verify out-of-order hint behavior coverage.
- [x] Add or verify role-revocation/no-unauthorized-project-flash coverage.
- [x] Run focused `dart analyze` for changed realtime/sync files and tests.
- [x] Run focused `flutter test` for changed realtime/sync tests.
- [x] Run `git diff --check`.
- [x] Probe S21 and S10 driver hygiene after local gates if reachable.
- [x] Update the controlling todo and implementation log only after evidence
  exists.

Accepted local and device hygiene evidence:

- `realtime_hint_handler_test.dart` now verifies duplicate realtime broadcasts
  dedupe to one dirty scope, keep the quick-sync throttle, and do not drop the
  dirty marker.
- `realtime_hint_handler_test.dart` now verifies out-of-order realtime
  broadcasts retain both dirty scopes for the next quick pull.
- `realtime_hint_handler_test.dart` verifies failed realtime registration
  starts fallback polling quick syncs, covering missed realtime hints.
- Existing queued-follow-up coverage verifies delayed hints arriving mid-sync
  run after the in-flight sync completes.
- Existing FCM tests verify throttled foreground hints still mark dirty scopes,
  background hint persistence, background queue bounds, cross-company
  rejection, and cooldown behavior.
- Existing scope revocation cleaner coverage verifies revoked project scope is
  fully evicted locally, including shell rows and local files; cross-company
  realtime/FCM hints are rejected before dirtying scopes or syncing.
- Focused local gates passed:
  - `dart analyze test/features/sync/application/realtime_hint_handler_test.dart test/features/sync/application/fcm_handler_test.dart test/features/sync/application/sync_lifecycle_manager_test.dart test/features/sync/engine/dirty_scope_tracker_test.dart test/features/sync/engine/pull_scope_state_test.dart test/features/sync/engine/scope_revocation_cleaner_test.dart lib/features/sync/application/realtime_hint_handler.dart lib/features/sync/application/realtime_hint_transport_controller.dart lib/features/sync/engine/dirty_scope_tracker.dart`
  - `flutter test test/features/sync/application/realtime_hint_handler_test.dart test/features/sync/application/fcm_handler_test.dart test/features/sync/application/sync_lifecycle_manager_test.dart test/features/sync/engine/dirty_scope_tracker_test.dart test/features/sync/engine/pull_scope_state_test.dart test/features/sync/engine/scope_revocation_cleaner_test.dart -r expanded`
    passed 60 tests.
  - `git diff --check` passed with line-ending warnings only.
- S21 driver hygiene after the slice: ready on `/sync/dashboard`, empty
  `change_log`, `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.
- S10 driver hygiene after the slice: ready on `/projects`, empty
  `change_log`, `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.

## Immediate Slice I - Domain-Specific Conflict Strategy

- [x] Resume after realtime-hint proof and refresh the open conflict-policy
  checklist.
- [x] Inspect `ConflictResolver`, sync adapters, signed form responses,
  signature files, signature audit rows, quantities, and narrative fields.
- [x] Define which domains may use LWW and which require preservation or
  documented stronger behavior.
- [x] Add or verify focused tests for signatures and signature audit rows.
- [x] Add or verify focused tests for signed form responses.
- [x] Add or verify focused tests for quantities and narrative fields.
- [x] Run focused `dart analyze` for changed conflict/sync files and tests.
- [x] Run focused `flutter test` for changed conflict/sync tests.
- [x] Run `git diff --check`.
- [x] Probe S21 and S10 driver hygiene after local gates if reachable.
- [x] Update the controlling todo and implementation log only after evidence
  exists.

Slice I accepted behavior:

- Default product records still use deterministic LWW.
- Sparse push-skip audit rows still use LWW, so `LwwChecker` logging does not
  falsely report local preservation when the remote row only carries a server
  timestamp.
- Signed local `form_responses` are preserved over newer unsigned pulled rows.
- `signature_files` preserve local immutable fingerprint metadata when a full
  pulled row disagrees, while still accepting newer `remote_path` updates when
  the immutable fingerprint matches.
- `signature_audit_log` preserves the local immutable audit chain when a full
  pulled row disagrees.
- `entry_quantities` and narrative records remain LWW, with discarded
  quantity, notes, and narrative text retained in changed-column conflict-log
  diffs.

Slice I evidence:

- `dart analyze lib/features/sync/engine/conflict_resolver.dart test/features/sync/engine/conflict_resolver_domain_policy_test.dart test/features/sync/engine/conflict_clock_skew_test.dart test/features/sync/property/sync_invariants_property_test.dart test/features/sync/engine/sync_engine_lww_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/conflict_resolver_domain_policy_test.dart test/features/sync/engine/conflict_clock_skew_test.dart test/features/sync/property/sync_invariants_property_test.dart test/features/sync/engine/sync_engine_lww_test.dart -r expanded`
  passed 24 tests.
- `git diff --check` passed with line-ending warnings only.
- S21 driver hygiene: ready on `/sync/dashboard`, empty `change_log`,
  `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.
- S10 driver hygiene: ready on `/projects`, empty `change_log`,
  `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.

## Immediate Slice J - File, Storage, And Attachment Hardening

- [x] Resume after conflict-policy proof and refresh the open
  file/storage/attachment checklist.
- [x] Inventory production file-backed families, storage buckets, local-only
  tables, cleanup queues, and existing proof helpers.
- [x] Verify or add tests that every file-backed row has a durable row/object
  consistency contract.
- [x] Verify or add tests for upload replay, metadata replay, storage 409, and
  missing-object recovery across photos, documents, signature files, and export
  artifacts.
- [x] Verify or add tests for orphan cleanup and stale local cache
  invalidation.
- [x] Decide whether local-only export artifact tables need clearer
  diagnostics or soak artifact fields before P1 closure.
- [x] Add durable file-sync phase state logging for upload start/success, row
  upsert success/failure, local bookmark success/failure, stale cleanup queued,
  and cleanup retry success/failure.
- [x] Add signatures bucket coverage to cleanup/orphan registries.
- [x] Run focused `dart analyze` for changed file/storage sync files and tests.
- [x] Run focused `flutter test` for changed file/storage sync tests.
- [x] Run `git diff --check`.
- [x] Probe S21 and S10 driver hygiene after local gates if reachable.
- [x] Update the controlling todo and implementation log only after evidence
  exists for the completed subitems.

Slice J partial evidence:

- `dart analyze lib/core/database/schema/sync_engine_tables.dart lib/core/database/database_bootstrap.dart lib/core/database/database_late_migration_steps.dart lib/core/database/database_service.dart lib/core/database/database_schema_metadata.dart lib/features/sync/application/sync_engine_factory.dart lib/features/sync/engine/file_sync_handler.dart lib/features/sync/engine/file_sync_state_store.dart lib/features/sync/engine/file_sync_three_phase_workflow.dart lib/features/sync/engine/storage_cleanup.dart lib/features/sync/engine/storage_cleanup_registry.dart lib/features/sync/engine/orphan_scanner.dart test/helpers/sync/sqlite_test_helper.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/adapters/adapter_config_test.dart test/features/sync/engine/orphan_scanner_test.dart -r expanded`
  passed 102 tests.
- `dart analyze lib/features/sync/engine/file_sync_three_phase_workflow.dart test/features/sync/engine/adapter_integration_test.dart lib/features/sync/engine/storage_cleanup_registry.dart`
  passed with no issues after widening storage path validation for nested
  artifact directories.
- `flutter test test/features/sync/engine/adapter_integration_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/adapters/adapter_config_test.dart test/features/sync/engine/orphan_scanner_test.dart -r expanded`
  passed 133 tests.
- `dart analyze test/features/sync/engine/file_sync_handler_test.dart` passed
  with no issues after adding the document/signature replay matrix.
- `flutter test test/features/sync/engine/file_sync_handler_test.dart -r expanded`
  passed 24 tests.
- `flutter test test/features/sync/engine/adapter_integration_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/adapters/adapter_config_test.dart test/features/sync/engine/orphan_scanner_test.dart -r expanded`
  passed 135 tests.
- `dart analyze lib/features/sync/engine/stale_file_cache_invalidator.dart test/features/sync/engine/stale_file_cache_invalidator_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/stale_file_cache_invalidator_test.dart -r expanded`
  passed 3 tests.
- Combined file/storage sweep with stale-cache coverage passed:
  `flutter test test/features/sync/engine/stale_file_cache_invalidator_test.dart test/features/sync/engine/adapter_integration_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/adapters/adapter_config_test.dart test/features/sync/engine/orphan_scanner_test.dart -r expanded`
  passed 138 tests.
- Reconciliation summary artifacts now write `storage-family-diagnostics.json`
  and summary fields that classify photos, signatures, and entry documents as
  remote-object proof families, while `entry_exports`, `form_exports`,
  `export_artifacts`, and pay-application exports are recorded as local-only
  byte/history families under the current adapter contract.
- Added `Assert-SoakStorageUnauthorizedDenied` plus harness classifier tests
  so the next live object proof can record unauthorized storage denial per
  bucket/path family.
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` passed 11 test
  files after the storage diagnostics and denial-proof helper changes.
- `dart analyze lib/features/sync/engine/local_record_store.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/file_sync_handler_test.dart`
  passed with no issues after tightening phase-3 bookmark semantics.
- `flutter test test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/file_sync_handler_test.dart -r expanded`
  passed 58 tests, including missing-bookmark-target failure, durable
  `local_bookmark_failed` state logging, upload-before-upsert cleanup, and
  stale storage cleanup retry queueing.
- `flutter test test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart -r expanded`
  passed 59 tests after adding the bookmark-before-`change_log`-processed
  replay/drain proof.
- Broader file/storage regression sweep passed:
  `flutter test test/features/sync/engine/stale_file_cache_invalidator_test.dart test/features/sync/engine/adapter_integration_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/adapters/adapter_config_test.dart test/features/sync/engine/orphan_scanner_test.dart test/features/sync/engine/local_sync_store_contract_test.dart -r expanded`
  passed 172 tests.
- Final file/storage crash-matrix sweep passed after closing the
  bookmark-before-`change_log` case:
  `flutter test test/features/sync/engine/stale_file_cache_invalidator_test.dart test/features/sync/engine/adapter_integration_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/adapters/adapter_config_test.dart test/features/sync/engine/orphan_scanner_test.dart test/features/sync/engine/local_sync_store_contract_test.dart -r expanded`
  passed 173 tests.
- `git diff --check` passed with line-ending warnings only.
- S21 driver hygiene: ready on `/sync/dashboard`, empty `change_log`,
  `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.
- S10 driver hygiene: ready on `/projects`, empty `change_log`,
  `pendingCount=0`, `blockedCount=0`, `unprocessedCount=0`,
  `isSyncing=false`.

PowerSync attachment-helper triage result:

- Current PowerSync docs say the old Dart `powersync_attachments_helper`
  package is deprecated and attachment functionality has moved into built-in
  SDK helpers. The reusable pattern is local-only attachment metadata, explicit
  upload/download/delete states, retries, verification/repair, and cleanup.
- Direct adoption is not a release fit because it couples to PowerSync
  database/queue APIs and would introduce a second sync substrate. The current
  local implementation ports the useful pattern into Field Guide's existing
  SQLite/Supabase sync engine with `file_sync_state_log` as diagnostic phase
  evidence rather than a second production queue.

Accepted local evidence:

- `dart analyze lib/features/sync/engine/file_sync_three_phase_workflow.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/file_sync_handler_test.dart -r expanded`
  passed 16 tests.
- `dart analyze lib/features/sync/engine/sync_metadata_store.dart lib/features/sync/engine/local_sync_store_metadata.dart lib/features/sync/engine/pull_handler.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/pull_handler_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/pull_handler_contract_test.dart test/features/sync/engine/supabase_sync_contract_test.dart -r expanded`
  passed 79 tests.
- `dart analyze test/features/sync/engine/pull_handler_test.dart` passed with
  no issues after adding the partial-final-page restart test.
- `flutter test test/features/sync/engine/pull_handler_test.dart -r expanded`
  passed 21 tests.
- Final combined sweep passed:
  - `git diff --check`
  - `dart analyze lib/features/sync/engine/file_sync_three_phase_workflow.dart lib/features/sync/engine/sync_metadata_store.dart lib/features/sync/engine/local_sync_store_metadata.dart lib/features/sync/engine/pull_handler.dart lib/features/sync/engine/supabase_sync.dart lib/shared/datasources/generic_local_datasource.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/supabase_sync_contract_test.dart test/features/pay_applications/data/datasources/local/export_artifact_local_datasource_test.dart test/helpers/sync/fake_supabase_sync.dart`
  - `flutter test test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/pull_handler_contract_test.dart test/features/sync/engine/supabase_sync_contract_test.dart test/features/pay_applications/data/datasources/local/export_artifact_local_datasource_test.dart -r expanded`
    passed 103 tests.

## P2 And Exit Gates

- [ ] Run external reuse triage for Jepsen, Elle, and lightweight local
  checker approaches.
- [ ] Add seedable operation scheduler and operation history.
- [ ] Add checker actors and invariant checks.
- [ ] Add failure injection and explicit quiescence.
- [ ] Run backend/RLS pressure concurrently with device flows while keeping
  evidence layers separate.
- [ ] Provision and prove staging harness credentials, schema parity, and
  RLS/storage policy parity.
- [ ] Expand deterministic fixtures to 15 projects and 10-20 users.
- [ ] Add headless app-sync actors with isolated local stores.
- [ ] Add operational diagnostics and alert contracts.
- [ ] Write `docs/sync-consistency-contract.md`.
- [ ] Write `docs/sync-scale-hardening-playbook.md`.
- [ ] Collect three consecutive green full-system staging or
  staging-equivalent sync-soak runs.
