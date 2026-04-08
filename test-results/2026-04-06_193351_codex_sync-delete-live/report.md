# Sync Delete Verification Report — 2026-04-06 19:33:51
Platform: dual (windows:4948 + android-s21:4949)
Run Tag: t138i

## Results
| Flow | Status | Duration | Notes |
|------|--------|----------|-------|
| Entry delete S21 -> Cloud -> Windows | Pass after fix | multi-step | Real UI delete on S21, sender queue drained, Supabase tombstones verified for `daily_entries`/`photos`/`documents`, storage prefixes empty, Windows converged after pull |
| Project delete S21 -> Cloud -> Windows | Pass after fixes | multi-step | Real UI delete on S21, remote RPC tombstoned full subtree including `project_assignments`, sender + Windows now converge on deleted project subtree |

## SQLite Verification
| Flow | Sender Row | Sender Queue | Receiver Row | Receiver Queue | Notes |
|------|------------|--------------|--------------|----------------|-------|
| Entry delete `1a31fc0c-33ef-4f99-8c07-60ebc9825c4e` | deleted entry + deleted photo/document | drained after sync | deleted entry + deleted photo/document | none | Initial live run exposed missing child cascade in `DailyEntryProvider.deleteEntry()`; fixed to use `SoftDeleteService.cascadeSoftDeleteEntry(...)` |
| Project delete `d2bb6a5d-010f-4e9b-adcb-9188ea442391` | deleted project subtree incl. assignments | no pending delete changes; sender still has storage cleanup rows to observe | deleted project subtree incl. assignment tombstone on Windows | none observed | Initial live run exposed local `project_assignments` stale rows after project delete; fixed by adding `project_assignments` to project soft-delete graph |

## Supabase Verification
| Table | Records Created | Records Verified | Cascade Deleted | Notes |
|-------|----------------|-----------------|-----------------|-------|
| `daily_entries` / `photos` / `documents` | 1 entry + 1 photo + 1 document | yes | yes | Entry delete propagated with row tombstones and storage removal |
| `projects` subtree for `VRF-Delete t138i` | 1 project + descendants | yes | yes | Verified remote tombstones for project, contractor, location, personnel types, and both project assignments |

## Cross-Device Sync
| Flow | Windows→Cloud | Cloud→S21 | Latency | Notes |
|------|----------------|-----------|---------|-------|

## Log Anomalies
| Flow | Level | Category | Message | Timestamp |
|------|-------|----------|---------|-----------|

## Bugs Found
- Sync defect fixed: real entry delete UI path only soft-deleted `daily_entries`, leaving active `photos` / `documents` on sender and receiver until code change. Fixed in `DailyEntryProvider.deleteEntry()` by routing through `SoftDeleteService.cascadeSoftDeleteEntry(...)`.
- Sync defect fixed: receiver pull scope dropped deleted parent IDs, so child tombstones for via-entry and via-contractor tables could not arrive after parent deletion. Fixed by retaining materialized deleted parent IDs for pull scope.
- Sync defect fixed: project delete local cascade missed `project_assignments`, leaving stale local assignment rows after remote RPC cascade. Fixed by adding `project_assignments` to the shared project soft-delete graph.

## Post-Run Sweep
| Table | VRF Records Found | Status |
|-------|-------------------|--------|

## Observations
- Delete orchestration needs to stay split across graph, local cascade, remote coordinator, scope-revocation cleanup, and propagation verification. The live failures this run were all graph/scope drift, not generic sync instability.
- `delete-propagation` project snapshots currently include duplicate table rows for some entry/file-backed tables. This does not invalidate the counts used here, but the verifier output should be deduplicated before final release proof.

## Pre-Resume Refactor Checkpoint — 2026-04-07
- Sync dashboard now follows the refactored UI endpoint pattern: a screen-local `SyncDashboardController` is provided via `sync_screen_providers.dart`, and the screen no longer owns inline async diagnostics state.
- `/driver/delete-propagation` is now handled by a dedicated `DriverDeletePropagationHandler` instead of extending `DriverServer` further.
- `DeletePropagationVerifier.inspectProject(...)` now collapses overlapping direct/entry/contractor scope filters into one snapshot row per table, eliminating the duplicate project snapshot output observed in the live run.
- Local proof before resuming device work: targeted sync presentation + delete-verifier tests passed, and `flutter analyze` on the touched sync/driver files passed clean.

## Resume Wave — 2026-04-07
- Windows driver bootstrap initially failed because `lib/core/app_widget.dart` had a `ThemeExtension` collection typing error that only surfaced during `flutter run -d windows`. The compile break was fixed, then both drivers were relaunched successfully (`4948` Windows, `4949` S21).
- UI absence proof is now explicit on both devices:
  - Windows `/projects`: `project_card_d2bb6a5d-010f-4e9b-adcb-9188ea442391` not found
  - S21 `/projects`: `project_card_d2bb6a5d-010f-4e9b-adcb-9188ea442391` not found
  - Windows `/entries`: `entries_list_entry_tile_1a31fc0c-33ef-4f99-8c07-60ebc9825c4e` not found
  - S21 `/entries`: `entries_list_entry_tile_1a31fc0c-33ef-4f99-8c07-60ebc9825c4e` not found
- Project-delete storage cleanup is now explicit for the deleted subtree. Using the desktop app’s persisted Supabase session, remote storage list queries returned zero matches for every surviving deleted-project `remote_path` in `entry-photos` and `entry-documents`.
- This closes the previously open `project-delete-storage-and-ui-verification` gate.

## Restore Retest Wave — 2026-04-07
- First restore retest exposed a real restore-scope defect: restoring the project from Trash only revived the local `projects` row, leaving `project_assignments` tombstoned. Windows could not pull the restored project because scope never came back.
- Fixes landed before the next live retest:
  - local `SoftDeleteService.restoreWithCascade('projects', ...)` now restores the project subtree instead of only the parent row
  - project restore from Trash now uses a remote-first `admin_restore_project` Supabase RPC and suppresses local restore sync logging
  - remote migration `20260407120000_add_project_restore_rpc.sql` restores the project subtree server-side and handles `project_assignments` restore without reopening general client-side assignment updates
- Live retest after the client + remote changes:
  - S21 delete from `/projects` tombstoned `projects` + `project_assignments` again
  - S21 restore from `/settings/trash` revived `projects`, `project_assignments`, `daily_entries`, `photos`, and `documents` locally with matching `updated_at`
  - Supabase rows for `projects`, `project_assignments`, `daily_entries`, `photos`, and `documents` all returned `deleted_at = null`
  - Windows pull reported `pulled: 13` and the restored subtree is now active in receiver SQLite, including `synced_projects`, `project_assignments`, `daily_entries`, `photos`, and `documents`
- Remaining blocker after the successful restore convergence:
  - S21 `/projects` now shows `project_card_d2bb6a5d-010f-4e9b-adcb-9188ea442391`
  - Windows `/projects` still does not show `project_card_d2bb6a5d-010f-4e9b-adcb-9188ea442391` even though the project row is active locally and `synced_projects` contains the project
  - Windows receiver UI visibility therefore remains open before the hard-delete / revocation overlap lane can continue
- Additional note:
  - a `driver/sync` call issued while S21 remained on Trash returned a widget lifecycle error (`Looking up a deactivated widget's ancestor is unsafe`). The restore itself had already converged remotely and on Windows, so this did not block the restore proof, but the screen-level sync invocation path needs follow-up.

## Restore Visibility + Idempotence Wave — 2026-04-07
- The earlier Windows `/projects` visibility blocker is closed. After route/tab interaction and a clean rebuild, both devices now surface:
  - restored project card `project_card_d2bb6a5d-010f-4e9b-adcb-9188ea442391`
  - restored entry tile `entries_list_entry_tile_1a31fc0c-33ef-4f99-8c07-60ebc9825c4e`
- A real repeat-sync blocker was then isolated on S21:
  - pull cursors only advanced when a fetched row changed locally, so already-matching rows inside the safety window could be re-fetched indefinitely
  - `support_tickets` remote schema had gained `updated_at`, but local SQLite and the model had not, causing a permanent support-ticket pull/conflict loop on Android
- Fixes landed before the next live rerun:
  - `PullHandler` now advances its cursor to the newest remote `updated_at` seen in the fetched page, even when the row already matches locally
  - local `support_tickets` schema/model now include `updated_at`, with a migration/backfill so the local row can retain the remote sync timestamp
  - regression coverage was added for pull cursor advancement on already-matching rows and for the `support_tickets` schema/model shape
- Live rerun after those fixes:
  - Android migration initially failed because SQLite rejects `ALTER TABLE ... ADD COLUMN` with a non-constant default; the migration was corrected to add `updated_at` without that default and backfill from `created_at`
  - after reinstall/relaunch, both Windows and S21 returned `{"success":true,"pushed":0,"pulled":0,"errors":[]}` on the first full sync rerun
  - both Windows and S21 returned the same `pushed: 0, pulled: 0` result on a second consecutive full sync rerun
- This closes the restore visibility + restore-state idempotence gate. The next live lane is hard-delete / revocation overlap.

## Hard Delete Wave — 2026-04-07
- Sender setup:
  - S21 re-deleted project `d2bb6a5d-010f-4e9b-adcb-9188ea442391` through the production `/projects` delete path and confirmed the project trash controls were present
  - S21 Trash `Delete Forever` removed the project trash actions immediately
  - S21 `/driver/delete-propagation` then reported `target_exists: false`, `synced_project_enrolled: false`, and zero remaining subtree rows across the registered project graph
- Immediate sender result:
  - S21 local `projects` and `daily_entries` rows for the test subtree were no longer found through `/driver/local-record`
  - sender full sync reported `{"success":true,"pushed":1,"pulled":0,"errors":[]}`
- Receiver result without maintenance:
  - Windows full sync reported `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
  - Windows still retained the active project subtree immediately after that normal pull, so hard delete did not converge through the ordinary pull path alone
- Receiver result with forced maintenance:
  - after `POST /driver/reset-integrity-check` and another full sync, Windows soft-deleted the stale project subtree as `deleted_by = system_orphan_purge`
  - Windows `/projects` and `/entries` no longer surface the project card or restored entry tile after that maintenance-assisted cleanup
- Remaining hard-delete gaps:
  - receiver cleanup currently depends on integrity/orphan purge rather than a first-class hard-delete propagation path
  - Windows `synced_projects` remained enrolled for the project even after the subtree was orphan-purged
  - S21 `/projects` still showed a stale project card immediately after local hard delete despite `/driver/local-record` proving the row was gone; that looks like a screen refresh/UI issue, not a local SQLite failure
- Audit conclusion before the next patch:
  - the current client hard-delete path (`hardDeleteWithSync` -> change_log `delete` -> `pushHardDelete`) is structurally unsafe for multi-device convergence because it physically removes the remote soft-delete tombstone before lagging receivers can pull it
  - the safer contract is to treat Trash `Delete Forever` as a local purge of an already-soft-deleted record while leaving remote tombstones for normal receiver convergence and server-side retention purge
  - `synced_projects` cleanup also lags one cycle because pull finalization runs before maintenance/orphan purge mutates the local subtree

## Shared Delete-Contract Audit — 2026-04-07
- The hard-delete bug is a shared sync-contract problem, not just a Trash-screen problem.
- Runtime paths fall into three categories:
  - Soft-delete lifecycle paths: standard deletes update local rows with tombstones and are still sync-safe.
  - Local-only eviction paths: `removeFromDevice` and scope-revocation eviction intentionally suppress triggers and clear local change tracking so they do not mutate Supabase. These are different by contract and are not the root cause of the hard-delete drift.
  - Local purge paths that still emit sync deletes: Trash `Delete Forever`, retention purge, and any future local purge built on the same pattern were unsafe because once the sender physically removed the local row, push escalated to remote physical delete for a soft-delete table.
- Shared fix landed before the next live rerun:
  - local hard purge now preserves the final tombstone payload in `change_log.metadata`
  - push now replays that preserved soft-delete when the local row is already gone instead of remote-hard-deleting the row
  - maintenance now cleans stale `synced_projects` in the same cycle after orphan purge soft-deletes a project shell
- Targeted local proof after the patch:
  - `flutter test test/features/sync/engine/push_handler_test.dart test/features/sync/engine/maintenance_handler_contract_test.dart test/features/sync/engine/cascade_soft_delete_test.dart`
  - `flutter analyze` on the touched sync/delete files
- Additional audit follow-up that remains open:
  - legacy `BaseRemoteDatasource.delete()` style APIs still exist and should be treated as footguns until their runtime usage is fully constrained
  - `support_tickets.updated_at` no longer causes repeat-pull churn, but upgraded SQLite installs still log schema drift because migration v53 does not yet match the canonical `NOT NULL DEFAULT` shape

## Fresh Fixture Hard-Delete Revalidation — 2026-04-07
- The original proof project `d2bb6a5d-010f-4e9b-adcb-9188ea442391` was no longer restorable remotely, so a fresh live fixture was created on S21 through the production project-create UI:
  - project `b28afcd0-501f-463c-a255-8f61469a2ba5`
  - name `VRF HardDelete t138i-b`
- New-fixture setup notes:
  - the project row pushed remotely under the admin account (`created_by_user_id = 88054934-9cc5-4af3-b1c6-38f262a7da23`)
  - to give the Windows device a legitimate receiver scope, a remote `project_assignments` row was inserted for the Windows account (`d1ca900e-d880-4915-9950-e29ba180b028`)
  - after that assignment landed, Windows ordinary sync pulled the project row and assignment, and local `delete-propagation` showed `target_exists: true`, `target_deleted: false`, `synced_project_enrolled: true`
- Fresh-fixture soft-delete proof:
  - S21 deleted the project through the real `/projects` delete sheet + confirm-dialog flow
  - S21 local state: project tombstoned, both project assignments tombstoned, `synced_project_enrolled: false`
  - Supabase state: project row tombstoned and both assignment rows tombstoned with matching `deleted_at` / `updated_at`
  - Windows ordinary sync pulled `2` rows and converged to the same hidden tombstone state
  - Windows UI absence was explicit again: `project_card_b28afcd0-501f-463c-a255-8f61469a2ba5` not found
- Fresh-fixture hard-delete proof:
  - S21 Trash `Delete Forever` removed the local project shell immediately: `target_exists: false`, no remaining project-assignment rows, one pending delete change, then sender sync reported `{"success":true,"pushed":1,"pulled":0,"errors":[]}`
  - the first normal Windows sync after that sender push reported `{"success":true,"pushed":0,"pulled":0,"errors":[]}` and kept the local tombstoned shell
  - after forcing the Windows integrity cadence, the next sync pulled `1` row and updated the local tombstone metadata, but the receiver still intentionally remained a hidden tombstone rather than locally purging the shell
  - remote Supabase state after the sender hard-delete push stayed on a soft tombstone, with `updated_at` advanced to `2026-04-07T13:12:15.940163-04:00`
- Idempotence after the fresh-fixture hard delete is now explicit:
  - S21 consecutive sync: `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
  - Windows consecutive sync: `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
  - S21 `change_log?table=projects` returned zero pending entries
- Architecture conclusion from the fresh fixture:
  - the shared delete-contract fix did close the data-loss/drift class where sender hard delete could physically remove the remote soft-delete tombstone before lagging receivers saw it
  - the current contract is now: sender `Delete Forever` locally purges the sender shell, preserves/replays the remote tombstone, and receivers converge to a hidden tombstone state until a later server-side retention purge removes the remote row
  - under that contract, the old expectation that Windows should immediately drop the local tombstone shell on ordinary pull is no longer the correct success condition

## Revocation + Overlap Wave — 2026-04-07
- Simple revocation cleanup proof used a fresh remote-seeded fixture:
  - project `4825141a-7b6b-44f9-9ef1-ba5e89dc39fd`
  - name `VRF Revocation t138i-d`
- Revocation-only result:
  - both devices first pulled the active project and assignment scope from Supabase
  - the Windows assignment row was then soft-deleted remotely while the project itself remained active in Supabase
  - the next ordinary Windows sync fully evicted the local project scope: `/driver/local-record` returned `Record not found`, `/driver/delete-propagation` reported `target_exists: false`, `synced_project_enrolled: false`, zero remaining `project_assignments`, and Windows `change_log` stayed empty
  - the remote project row stayed active (`deleted_at = null`), and S21 remained enrolled on the same project with one active assignment and one deleted assignment after its next pull
  - repeated sync after that revocation settled at `{"success":true,"pushed":0,"pulled":0,"errors":[]}` on Windows
- Delete-plus-revocation overlap proof used a second remote-seeded fixture:
  - project `c55c4b2f-1c9a-4ca3-a0fc-1a209f9c57a3`
  - name `VRF RevocationOverlap t138i-e`
- Overlap result:
  - both devices first pulled the active project and assignments
  - the server-side `admin_soft_delete_project` RPC was then executed remotely, which tombstoned the project row and both assignment rows together
  - the next ordinary pull on both devices converged to a hidden tombstone state: the project row remained locally with `deleted_at` populated, `synced_project_enrolled: false`, and `project_assignments` showed only deleted rows
  - both `/projects` UIs no longer surfaced the project card (`project_card_c55c4b2f-1c9a-4ca3-a0fc-1a209f9c57a3` not found on Windows or S21)
  - repeated sync after the overlap settled immediately at `{"success":true,"pushed":0,"pulled":0,"errors":[]}` on both devices
- Architecture conclusion from the revocation wave:
  - plain scope revocation of an active project now fully evicts the revoked receiver cache without mutating the still-active remote project
  - when delete tombstones and assignment revocation arrive together, delete currently wins over full local eviction: receivers keep a hidden project tombstone with `synced_project_enrolled: false` rather than dropping the row entirely
- New blocker isolated while closing this wave:
  - S21 still carries two exhausted `project_assignments` update retries in `change_log` with `RLS denied (42501)` even though the corresponding assignment IDs are no longer present locally or remotely
  - code audit points at the current assignment wizard path as the architectural footgun: `ProjectAssignmentProvider.save()` still writes `project_assignments` locally through `ProjectAssignmentRepository`, even though the sync adapter marks that table `skipPush: true` and the intended ownership model treats it as pull-only
  - release closeout now needs a remote-first assignment mutation boundary (or equivalent suppression/ownership fix) plus a clean-device re-proof that assignment flows no longer create local `project_assignments` sync residue

## Project Assignment Mutation Contract Wave — 2026-04-07
- First rerun exposed invalid live evidence: the S21 was still on a stale build. Android app logs still contained the removed string `Immediate push triggered after project creation`, so both drivers were rebuilt and relaunched before re-running the lane.
- Fresh-build UI state on S21 proved the assignment screen itself was no longer stale:
  - route `/project/4825141a-7b6b-44f9-9ef1-ba5e89dc39fd/edit?tab=4` showed the Windows inspector unchecked and only the admin selected
  - this removed the earlier suspicion that the screen was still reading stale local assignment state after revocation
- Client-side ownership fix:
  - `ProjectAssignmentMutationService` now diffs against the active remote baseline only by filtering `project_assignments.deleted_at IS NULL`
  - this closes the bug where a soft-deleted remote assignment row was incorrectly treated as already active, producing `added=0 removed=0` and skipping the restore mutation
- Server-side restore-contract fix:
  - existing trigger immutability logic still blocked reactivating a soft-deleted `project_assignments` row during the mutation flow
  - migration `20260407143000_allow_assignment_restore_rpc.sql` now lets `admin_upsert_project_assignment` set the sanctioned `app.restore_project_assignment` flag before restoring an existing assignment row
- Targeted local validation passed before the live rerun:
  - `flutter test test/features/projects/data/services/project_assignment_mutation_service_test.dart`
  - `flutter analyze lib/features/projects/data/services/project_assignment_mutation_service.dart test/features/projects/data/services/project_assignment_mutation_service_test.dart`
  - `npx supabase db push --include-all`
- Final live proof on fresh builds:
  - S21 save from `/project/4825141a-7b6b-44f9-9ef1-ba5e89dc39fd/edit?tab=4` logged `ProjectAssignmentMutationService: project=4825141a-7b6b-44f9-9ef1-ba5e89dc39fd added=1 removed=0`
  - S21 `delete-propagation` for the same project then showed `project_assignments total_count: 2`, `active_count: 2`, `deleted_count: 0`
  - S21 `change_log?table=project_assignments` stayed at the same two historical exhausted retries; no new local assignment sync rows were created by the new save path
  - Windows ordinary full sync pulled the restored assignment truth, kept `synced_project_enrolled: true`, and `/projects` rendered `project_card_4825141a-7b6b-44f9-9ef1-ba5e89dc39fd`
  - repeated full sync then settled at `{"success":true,"pushed":0,"pulled":0,"errors":[]}` on both S21 and Windows
- Architecture conclusion from the lane:
  - assignment mutation is now correctly remote-first for `project_assignments`
  - restore-capable soft-delete tables need an explicit sanctioned RPC/trigger path, not ad hoc row updates
  - executor diff logic must query the active remote baseline (`deleted_at IS NULL`) rather than raw rows that include tombstones
- Remaining blockers after this proof:
  - upgraded SQLite installs still log `support_tickets.updated_at` schema drift because migration v53 does not yet match the canonical `NOT NULL DEFAULT` shape
  - S21 still carries two old exhausted `project_assignments` retries from the pre-fix contract breach, so release closeout still needs a legacy residue decision or cleanup proof

## Upgraded-Install Repair Wave — 2026-04-07
- The next live blocker after assignment-contract proof was upgraded-device state, not fresh-install state.
- Source audit confirmed the mismatch:
  - canonical SQLite DDL already defines `support_tickets.updated_at` as `TEXT NOT NULL DEFAULT strftime(...)`
  - migration v53 only added `updated_at TEXT`, which stopped the repeat-pull loop but left permanent SchemaVerifier drift on upgraded installs
- Fixes landed before the next live rerun:
  - migration v55 rebuilds `support_tickets` to the canonical schema shape and replays existing ticket rows through the rebuilt table
  - migration v56 purges pending `change_log` residue for pull-only `project_assignments`, because any local pending row for that table is invalid by contract
  - regression coverage was added for both repairs: canonical `support_tickets` rebuild and pull-only `project_assignments` residue purge
- Targeted local validation passed:
  - `flutter test test/features/sync/schema/support_ticket_schema_test.dart test/core/database/project_assignment_changelog_repair_test.dart`
  - `flutter analyze` on the touched database/support-ticket test files
- Final live proof on rebuilt Windows + S21:
  - S21 startup log now reports `Migration v55: rebuilt support_tickets with canonical updated_at schema`
  - S21 startup log then reports `SchemaVerifier: verified 40 tables in 80ms — SchemaReport(drift=0, missing_cols=0, missing_tables=0)`
  - after v56, S21 startup log reports `Migration v56: purged 2 invalid project_assignments change_log entries`
  - S21 `/driver/change-log?table=project_assignments` now returns `count: 0`
  - ordinary full sync still settles cleanly after both repairs: Windows `{"success":true,"pushed":0,"pulled":0,"errors":[]}` and S21 `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
- Release-status conclusion after this wave:
  - the assignment mutation contract is no longer a live blocker
  - upgraded-install schema drift for `support_tickets.updated_at` is no longer a live blocker
  - legacy `project_assignments` retry residue is no longer a live blocker
  - the branch is still not fully release-proven because major proof lanes remain open: remove-from-device/fresh-pull parity, file-backed flows, support-ticket and consent live flows, restart/retry chaos lanes, and the final mixed-flow soak

## Remove-From-Device / Fresh-Pull Parity Wave — 2026-04-07
- The first remove-from-device rerun exposed two separate defects:
  - `removeFromDevice` mutated local project scope outside the shared sync mutex, so a local-only eviction could race an in-flight sync on S21
  - local-only eviction deleted project-scoped rows without resetting pull cursors, so a later "fresh pull" could miss older remote rows and rematerialize only part of the scope
- Fixes landed before the final rerun:
  - `ProjectLifecycleService.removeFromDevice(...)` now acquires the shared SQLite sync mutex before mutating local scope and refuses to run while sync already owns the lock
  - when the project metadata shell is intentionally preserved for re-download, `removeFromDevice(...)` now clears the pull cursors for the project-scoped sync tables so the next healthy cycle performs a true fresh pull instead of relying on stale table cursors
  - targeted local validation passed:
    - `flutter test test/features/projects/data/services/project_lifecycle_service_test.dart`
    - `flutter analyze lib/features/projects/data/services/project_lifecycle_service.dart test/features/projects/data/services/project_lifecycle_service_test.dart`
- Fixture note:
  - the earlier S21 rerun against `4825141a-7b6b-44f9-9ef1-ba5e89dc39fd` turned out to be contaminated, not a new enrollment bug; direct SQLite inspection showed that project was only actively assigned to the Windows inspector account after the revocation proof, so it was not a valid S21 admin fresh-pull fixture anymore
  - the clean shared fixture for final proof was project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d` (`VRF-Oakridge aun53`)
- Final live proof on the patched builds:
  - Windows remove-from-device on `e7dde2a2-8662-4d5a-ad32-3e167ad5576d` reduced local state to a preserved project shell with `synced_project_enrolled = false`, zero descendant rows, and zero local `change_log`; S21 stayed fully active on the same project throughout
  - the next ordinary Windows sync rematerialized the full subtree (`pulled: 21`), including `locations`, `contractors`, `daily_entries`, `entry_*` tables, `equipment`, `bid_items`, `personnel_types`, and the active `project_assignments` row; the second consecutive Windows sync settled at `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
  - S21 remove-from-device on the same project reduced local state to the same preserved project shell with `synced_project_enrolled = false`, zero descendant rows, and zero local `change_log`; Windows stayed fully active on the same project throughout
  - after the cursor-reset fix, the next healthy S21 sync rematerialized the full subtree and both active assignment rows; once an overlapping auto-sync finished, the next consecutive S21 sync settled at `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
- Contract conclusion from the wave:
  - remove-from-device is a local-only scope eviction, not a UI disappearance contract; the project shell can remain visible as the re-downloadable metadata card while the synced subtree and `synced_projects` enrollment are removed
  - the actual correctness gate is now proven: local-only eviction no longer mutates Supabase, the other device stays active, the evicted device recreates the same active scope on the next healthy sync, and repeat sync returns to `0/0`

## File-Backed Live Wave — 2026-04-07
- Shared file-backed fixture:
  - project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d`
  - entry `4e35a00d-26d7-44b7-9f5d-c67c9e6f2f91`
  - document `e645a8b1-7d32-4a1d-80ad-945fd93b5193`
  - photo `86e4f663-5663-471e-b939-1b252f853159`
  - entry export `7f32b8f6-cfbb-4b75-8d4d-3ec09fe8d901`
  - form export `4d31540d-9a2c-4d52-8d4e-f2b72423655e`
- Create/push/pull proof on S21 -> Cloud -> Windows:
  - S21 staged a new proof entry plus one live `documents`, `photos`, `entry_exports`, and `form_exports` row each
  - pre-push S21 `delete-propagation` for the entry showed exactly one active row in each of the four file-backed tables and `pending_change_count: 7`
  - sender full sync reported `{"success":true,"pushed":7,"pulled":0,"errors":[]}`
  - Windows full sync then reported `{"success":true,"pushed":0,"pulled":5,"errors":[]}`
  - repeated full sync immediately settled at `{"success":true,"pushed":0,"pulled":0,"errors":[]}` on both S21 and Windows
- Local materialization proof after the create wave:
  - S21 local records for all four file-backed tables now carried non-null `remote_path` values
  - Windows local records for the same four rows materialized with matching `remote_path` values and the expected receiver-side `file_path = null` cache shape
  - both S21 and Windows `change_log` endpoints returned `count: 0` for `daily_entries`, `documents`, `photos`, `entry_exports`, and `form_exports` after the create wave settled
- Remote row + storage proof after the create wave:
  - authenticated Supabase REST queries returned all five remote rows (`daily_entries`, `documents`, `photos`, `entry_exports`, `form_exports`) with `deleted_at = null`
  - authenticated storage checks returned `200` for the exact object paths in `entry-documents`, `entry-photos`, `entry-exports`, and `form-exports`
- Real entry-delete proof for the file-backed subtree:
  - S21 navigated to `/report/4e35a00d-26d7-44b7-9f5d-c67c9e6f2f91`, used the shipped report-menu delete path, and returned to `/entries`
  - pre-sync S21 `delete-propagation` for the entry showed the entry plus all four file-backed rows tombstoned locally, with `queued_cleanup_count: 1` on each file-backed table
  - sender full sync then reported `{"success":true,"pushed":6,"pulled":0,"errors":[]}`
  - Windows full sync reported `{"success":true,"pushed":0,"pulled":5,"errors":[]}`
  - repeated sync again settled immediately at `{"success":true,"pushed":0,"pulled":0,"errors":[]}` on both devices
- Delete convergence proof after the delete wave:
  - S21 and Windows `delete-propagation` for the same entry now match exactly: entry tombstoned, all four file-backed tables tombstoned, `pending_change_count: 0`, `pending_delete_change_count: 0`, and `queued_cleanup_count: 0` everywhere
  - both `/entries` UIs explicitly hide the deleted fixture entry: `entries_list_entry_tile_4e35a00d-26d7-44b7-9f5d-c67c9e6f2f91` not found on S21 or Windows
  - S21 `change_log` returned `count: 0` for `documents`, `photos`, `entry_exports`, and `form_exports` after the delete wave settled
- Remote row + storage proof after the delete wave:
  - authenticated Supabase REST queries returned all five remote rows with `deleted_at` populated and matching post-delete `updated_at`
  - authenticated storage download checks for the exact four object paths now return Supabase `not_found`, confirming remote storage cleanup for `entry-documents`, `entry-photos`, `entry-exports`, and `form-exports`
- Harness note:
  - `/driver/inject-document-direct` still advertises `csv` as an allowed extension while `DocumentRepository` correctly rejects it; that mismatch is a driver-fixture issue, not a sync-engine issue, so the live proof used a real PDF document fixture instead
- Conclusion from the wave:
  - the file-backed live lane is now closed for create, push, pull, delete, remote row convergence, remote storage cleanup, receiver convergence, and repeat-sync idempotence across `documents`, `photos`, `entry_exports`, and `form_exports`

## Integrity / Maintenance Wave — 2026-04-07
- Baseline before the forced rerun:
  - both drivers were healthy and idle: Windows `/driver/sync-status` reported `pendingCount: 0`, `lastSyncTime: 2026-04-07T20:24:03.313271Z`; S21 `/driver/sync-status` reported `pendingCount: 0`, `lastSyncTime: 2026-04-07T20:23:59.669645Z`
  - both devices already had persisted integrity metadata from earlier maintenance cycles
- Controlled orphan fixture on Windows:
  - active shared project: `e7dde2a2-8662-4d5a-ad32-3e167ad5576d`
  - seeded directly into live Windows SQLite with trigger suppression / no pending sync residue:
    - `export_artifacts/d333298f-dddd-479f-a774-54eac7bf6114`
    - `pay_applications/a554c947-0641-4088-a62c-3fea463f180e`
  - both rows were active locally (`deleted_at = null`, `deleted_by = null`)
  - Windows `change_log` had zero rows for those IDs after seeding
  - authenticated Supabase REST queries confirmed both IDs were absent remotely (`[]` for both tables)
- Forced maintenance rerun:
  - `POST /driver/reset-integrity-check` returned success on both Windows and S21
  - the next ordinary full sync on both devices settled at `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
- Windows maintenance proof after the forced rerun:
  - persisted integrity metadata for the staged orphan tables recorded the expected pre-purge drift:
    - `integrity_export_artifacts`: `drift_detected: true`, `cursor_reset_recommended: true`, `local_count: 1`, `remote_count: 0`
    - `integrity_pay_applications`: `drift_detected: true`, `cursor_reset_recommended: true`, `local_count: 1`, `remote_count: 0`
  - the same maintenance cycle then soft-deleted both staged rows locally:
    - `export_artifacts/d333298f-dddd-479f-a774-54eac7bf6114` -> `deleted_by = system_orphan_purge`
    - `pay_applications/a554c947-0641-4088-a62c-3fea463f180e` -> `deleted_by = system_orphan_purge`
  - Windows `change_log` still returned zero rows for those two IDs after the purge
- S21 maintenance proof after the forced rerun:
  - persisted integrity metadata stayed clean for the same table family:
    - `integrity_export_artifacts`: `drift_detected: false`, `local_count: 0`, `remote_count: 0`
    - `integrity_pay_applications`: `drift_detected: false`, `local_count: 0`, `remote_count: 0`
- Repeat-sync / no-recurring-drift proof:
  - the next repeated full sync on Windows again settled at `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
  - the next repeated full sync on S21 again settled at `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
- Conclusion from the wave:
  - integrity reruns are now explicitly live-proven on both devices
  - maintenance-assisted orphan purge now has direct live evidence on pay-app / file-backed tables, not just project-entry tables
  - after maintenance repairs the local-only orphan state, the branch returns immediately to `0/0` repeat-sync behavior with no new `change_log` residue

## Support Ticket Wave — 2026-04-07
- User-scoped proof setup note:
  - `support_tickets` is scoped by `user_id`, not project or company
  - the S21 and Windows apps in this validation run are different user identities, so cross-device materialization is NOT expected for this table
- Real UI submission on S21:
  - navigated to `/help-support`
  - used the shipped support form with message `Support sync proof 2026-04-07T20:45:30Z from S21 live validation.`
  - local SQLite inserted ticket `833518ea-f187-4c54-ba6b-bce95f1a3e0e` with `status = open`, `log_file_path = null`
  - local `change_log` showed exactly one pending `support_tickets` insert for that ticket
- New blocker surfaced while closing the lane:
  - the first manual S21 sync after submission returned `pushed: 1` but also surfaced branch-wide remote schema errors:
    - `signature_files: Remote sync schema is missing table signature_files`
    - `signature_audit_log: Remote sync schema is missing table signature_audit_log`
  - root cause: the branch had already registered both signature tables locally, but Supabase had not yet applied `supabase/migrations/20260408000000_signature_tables.sql`
- Remote fix applied during the live run:
  - ran `npx supabase db push --include-all`
  - remote migration `20260408000000_signature_tables.sql` applied successfully
  - authenticated Supabase REST checks then returned `[]` for both `signature_files` and `signature_audit_log` instead of 404
- Final support-ticket proof after the remote fix:
  - authenticated Supabase REST returned the new support ticket row:
    - `833518ea-f187-4c54-ba6b-bce95f1a3e0e`
    - `user_id = 88054934-9cc5-4af3-b1c6-38f262a7da23`
    - `status = open`
  - after rerunning S21 sync, the support-ticket lane settled cleanly:
    - one successful sync reported `{"success":true,"pushed":1,"pulled":1,"errors":[]}`
    - the next repeated sync reported `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
  - direct SQLite inspection on S21 showed:
    - no pending `support_tickets` `change_log` entries
    - `last_sync_time = 2026-04-07T20:53:25.592578Z`
- Harness note:
  - tapping the support success-screen `Done` path through the driver triggered a framework-locked provider reset (`SupportProvider.reset`) and destabilized the Android driver process
  - that is a driver/UI stability issue, not a support-ticket sync defect; the proof was completed after relaunching the S21 driver app and re-running sync
- Conclusion from the wave:
  - the dedicated support-ticket live flow is now proven on the correct user-scoped path: real UI submit on S21, remote row creation in Supabase, and repeat-sync return to `0/0`
  - the live run also closed a broader branch-level blocker by deploying the missing remote signature-table migration required by the current sync registry

## Consent Wave — 2026-04-07
- Architecture guardrail landed before the live rerun:
  - `DriverServer` no longer exposes protected sync tables through the generic `/driver/create-record` and `/driver/update-record` allowlists
  - protected tables remain queryable for diagnostics only
  - custom lint `no_driver_generic_mutation_of_protected_sync_tables` now keeps those bypasses from silently returning
- S21 re-consent proof through the router/version gate:
  - baseline local state for user `88054934-9cc5-4af3-b1c6-38f262a7da23` showed exactly two accepted consent rows and zero pending `change_log`
  - forcing `flutter.consent_policy_version = 0.9.0` in the real persisted shared prefs relaunched S21 into `/consent`
  - the shipped consent screen was scrolled to the bottom and the real `consent_accept_button` action was tapped
  - post-accept prefs restored `flutter.consent_policy_version = 1.0.0` and updated `flutter.consent_timestamp = 2026-04-07T21:20:34.218175Z`
  - local SQLite appended two new accepted rows:
    - `0d5bbdc5-74a7-4136-95c7-8216113ad751` (`privacy_policy`)
    - `d0782666-66cb-4956-bd74-aa5d571a5827` (`terms_of_service`)
  - pre-manual-sync S21 `change_log?table=user_consent_records` returned exactly two pending inserts for those IDs
  - manual S21 sync then reported `{"success":true,"pushed":2,"pulled":0,"errors":[]}`
  - repeated S21 sync settled at `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
  - authenticated Supabase REST now shows both new accepted rows as the latest records for that user
- Windows re-consent proof through the same gate:
  - baseline local state for user `d1ca900e-d880-4915-9950-e29ba180b028` showed two accepted local consent rows, zero pending `change_log`, and an older remote accepted pair
  - forcing the Windows shared prefs `flutter.consent_policy_version = 0.9.0` relaunched the app into `/consent`
  - the same shipped consent screen was scrolled and accepted
  - post-accept prefs restored `flutter.consent_policy_version = 1.0.0` and updated `flutter.consent_timestamp = 2026-04-07T21:22:40.942703Z`
  - local SQLite appended two new accepted rows:
    - `10476a23-1ef0-4d58-aca1-dfb7235d7a3b` (`privacy_policy`)
    - `5b163116-9e40-4a00-8bd0-9b4c08f0d288` (`terms_of_service`)
  - Windows `change_log?table=user_consent_records` was already empty by the time of inspection, and `/driver/sync-status` showed the app's own sync path had advanced `lastSyncTime`
  - repeated manual Windows sync settled at `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
  - authenticated Supabase REST now shows the two new accepted rows as the latest consent records for the Windows user
- Conclusion from the wave:
  - consent is now live-proven through the real version-gate path on both device identities
  - the table stayed insert-only: every proof step appended new accepted rows, no update/delete residue was created, and repeated sync returned to `0/0`
  - remaining release work now moves to retry/restart and sync-mode proof breadth

## Retry/Restart Push Wave — 2026-04-07
- Fixture setup:
  - active shared project: `e7dde2a2-8662-4d5a-ad32-3e167ad5576d`
  - active entry: `37214186-5025-422b-900c-ca8a5a6611da`
  - staged S21 file-backed rows:
    - `8b1515a0-022c-4c52-9bcf-5a9a3d1125c3`
    - `8bb96788-654c-4cea-b233-400db565cd88`
    - `e2f0e7c0-a988-41ae-a631-efd99a6071c9`
    - `fbaf64f5-0155-45ab-9660-3121ef898b1f`
    - `7f00d03d-80cb-4d8b-8538-7f3a42a613f4`
    - `2b01c181-70da-4707-acca-2f66a6993f7f`
- Interruption method:
  - injected six large photos on S21 through `/driver/inject-photo-direct`
  - confirmed `/driver/change-log?table=photos` returned `count = 6`
  - launched `/driver/sync` on S21, polled `/driver/sync-status` until `isSyncing = true`, then force-stopped `com.fieldguideapp.inspector`
  - the sync HTTP request died with transport error after the process kill, which is expected for this lane
- Post-crash frozen state before relaunch:
  - direct SQLite copy from S21 showed all six `photos` rows still present locally with `remote_path = null`
  - the same SQLite snapshot still held six unprocessed `change_log` inserts for those photo IDs
  - authenticated Supabase REST returned `[]` for those six IDs, so the interrupted attempt had not left partial remote row materialization behind
- Recovery after ordinary relaunch:
  - relaunching S21 through the shipped app path immediately re-entered `/` and the app's own sync path started automatically
  - once idle, S21 SQLite showed all six local rows with populated `remote_path` values and zero pending `photos` `change_log`
  - authenticated Supabase REST then showed exactly one remote `photos` row for each of the six IDs, with matching `remote_path`
  - Windows ordinary sync reported `{"success":true,"pushed":0,"pulled":6,"errors":[]}`
  - direct Windows SQLite inspection showed the same six photo IDs, matching `remote_path`, and zero pending local `photos` `change_log`
  - repeated sync then settled at:
    - S21: `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
    - Windows: `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
- Architectural note from the wave:
  - crash recovery is currently durable because `change_log` persisted the unfinished work and the next healthy sync replayed it
  - delayed retry scheduling itself is still process-memory only; this branch does not currently persist a separate `failed_sync_queue`
- Conclusion from the wave:
  - kill-during-push is now live-proven for a real file-backed path
  - the branch recovered without manual DB repair, without duplicate remote rows, and without stranded local `change_log` residue
  - the next retry/restart gate should move to kill-during-pull

## Retry/Restart Pull Wave — 2026-04-07
- Fixture setup:
  - receiver: Windows only, with the app fully stopped before sender mutation
  - sender: S21 active shared project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d`
  - target entry: `37214186-5025-422b-900c-ca8a5a6611da`
  - staged remote batch: `120` new `photos` rows whose filenames contain `retry_pullb`
- Sender preparation:
  - Windows was force-stopped first so realtime or resume sync could not consume the new rows early
  - on S21, `120` new tiny-photo rows were created against the target entry through `/driver/inject-photo-direct`
  - S21 then pushed the batch successfully with `{"success":true,"pushed":120,"pulled":0,"errors":[]}`
  - authenticated Supabase REST later confirmed remote count `120` for `filename LIKE '%retry_pullb%'`
- Interruption method:
  - Windows was cold-launched from the debug driver executable
  - during startup sync, local SQLite was polled for `filename LIKE '%retry_pullb%'`
  - the process was force-killed once the receiver had materialized a partial state:
    - poll sample: `7:38:True:0`
    - post-crash SQLite snapshot settled at `55` local rows for the new batch
- Post-crash frozen state:
  - Windows local SQLite contained only `55` of the expected `120` `retry_pullb` photo rows
  - `sync_metadata.last_pull_photos` still held the old pre-batch value `2026-04-07T21:49:31.054686+00:00`
  - that proves the partial pull had applied rows locally before the table cursor advanced
- Recovery:
  - after relaunch, Windows remained on the partial `55` rows until the next ordinary sync
  - the next ordinary manual sync then reported `{"success":true,"pushed":0,"pulled":65,"errors":[]}`
  - post-recovery SQLite showed:
    - `120` local `retry_pullb` rows
    - `last_pull_photos = 2026-04-07T21:53:40.840097+00:00`
    - `last_sync_time = 2026-04-07T21:56:09.677353Z`
  - the next repeated Windows sync settled at `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
- Conclusion from the wave:
  - kill-during-pull is now live-proven on a multi-page file-backed batch
  - the branch did not lose rows and did not advance the pull cursor past unseen rows
  - recovery depended on the next ordinary sync after relaunch, not on relaunch alone automatically finishing the interrupted pull
  - the next retry/restart gate should move to delete propagation

## Retry/Restart Delete Propagation Wave — 2026-04-07
- Sprint-1 fixture:
  - project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d`
  - entry `96af93cc-fb77-4bed-9006-3ecae4efc426`
  - local subtree before interruption: `18` photos, `4` documents
- Sprint-1 interruption:
  - deleted the entry through the shipped report-menu path on S21
  - pre-sync SQLite showed the full sender-local delete graph already durable:
    - entry tombstoned
    - `18` photo tombstones
    - `4` document tombstones
    - `23` pending `change_log` rows
    - `22` queued cleanup rows
  - started `/driver/sync` and force-stopped S21 once `/driver/sync-status` reported `isSyncing = true`
- Sprint-1 frozen state after crash:
  - S21 local SQLite still held the full tombstoned subtree and all `23` pending delete changes
  - authenticated Supabase REST still showed the entry and all `22` children active (`deleted_at = null`)
- Sprint-1 recovery:
  - relaunch alone did not resume the delete push
  - the next ordinary S21 sync reported `{"success":true,"pushed":23,"pulled":0,"errors":[]}`
  - authenticated Supabase REST then showed the entry, all `18` photos, and all `4` documents tombstoned
  - Windows pull reported `{"success":true,"pushed":0,"pulled":23,"errors":[]}`
  - Windows SQLite converged to the same tombstoned subtree (`18` deleted photos, `4` deleted documents)
- Sprint-2 rerun fixture:
  - entry `db3b76ff-f749-415b-b21b-c49853aebbcb`
  - local subtree before interruption: `12` photos, `3` documents
- Sprint-2 rerun result:
  - post-crash local SQLite still held `16` pending delete changes while remote rows stayed active
  - after relaunch, S21 reported `isSyncing = true` with only the tail of the delete fan-out left (`pendingCount = 5`)
  - the coordinator rejected a manual `/driver/sync` as already in progress, but the resumed run finished the remote delete anyway
  - Windows then pulled `16` tombstones and converged to the same deleted subtree
- Cross-sprint conclusion:
  - delete propagation is now live-proven twice
  - the data plane is durable in both variants, but relaunch behavior is inconsistent: one rerun needed the next ordinary sync, while the second resumed the tail automatically

## Retry/Restart Storage Cleanup Wave — 2026-04-07
- Sprint-1 fixture:
  - entry `6899b31c-e884-4cf6-9c95-983080d44af7`
  - local subtree before interruption: `38` photos, `8` documents
- Sprint-1 interruption:
  - deleted the entry through the shipped report-menu path on S21
  - pre-sync SQLite showed `46` queued cleanup objects
  - started `/driver/sync`, waited until `pendingCount = 0` while `isSyncing = true`, then force-stopped S21
- Sprint-1 frozen state after crash:
  - local SQLite showed `0` pending row mutations but `44` queued cleanup rows still persisted
  - authenticated Supabase REST showed the entry and all child rows already tombstoned
  - authenticated storage info calls still returned `200` for sample `entry-photos` and `entry-documents` objects
- Sprint-1 recovery:
  - relaunch alone did not drain the cleanup queue
  - the next ordinary S21 sync drained `storage_cleanup_queue` for that entry to `0`
  - the same sample storage info calls then returned Supabase `not_found`
  - Windows had already pulled the row tombstones (`{"success":true,"pushed":0,"pulled":47,"errors":[]}`) and stayed converged after cleanup
- Sprint-2 rerun fixture:
  - entry `0c2eba96-1c92-4e88-a0b6-ca9501fc04e8`
  - local subtree before interruption: `24` photos, `6` documents
- Sprint-2 rerun result:
  - crash hit the cleanup phase again with `30` queued cleanup rows still present and all remote rows already tombstoned
  - relaunch left the queue stranded at `30`
  - `/driver/sync-status` repeatedly reported `isSyncing = false` while `/driver/sync` kept returning `another sync is already in progress`
  - once the hidden run-state finally cleared, the next admitted S21 sync drained the queue to `0`
  - sample storage objects then returned `not_found` for both the photo and document buckets
- Cross-sprint conclusion:
  - storage cleanup is now live-proven twice
  - the underlying cleanup queues are durable, but the resumed-run control plane is not trustworthy: a hidden in-progress lock can outlive both crash and relaunch while status still reports idle

## Retry/Restart Sprint 2 Rerun — 2026-04-07
- Push rerun (`retry_push2` on entry `37214186-5025-422b-900c-ca8a5a6611da`):
  - post-crash state again held all six local rows with `remote_path = null`, six pending local changes, and zero remote rows for the marker
  - unlike sprint 1, relaunch did not drain the backlog automatically
  - the next admitted S21 sync pushed the six photos plus two previously unsynced draft-entry fixtures, and Windows later converged the six marker rows
- Pull rerun (`retry_pullc` batch of `120` on the same entry):
  - Windows was killed after partially materializing `94` of `120` rows
  - relaunch left Windows on `94`, and `/driver/sync` was rejected for an extended period as `another sync is already in progress` while `/driver/sync-status` kept reporting idle
  - once admitted, the next ordinary sync pulled the missing `26`, advanced the cursor, and repeated sync settled at `0/0`
- Delete and cleanup reruns:
  - fresh entries `db3b76ff-f749-415b-b21b-c49853aebbcb` and `0c2eba96-1c92-4e88-a0b6-ca9501fc04e8` re-proved delete propagation and storage cleanup on independent subtrees
- Cross-sprint summary:
  - all four retry/restart lanes now pass twice with no data loss, no remote duplication, and clean final `0/0` sync on both devices
  - the remaining issue in this proof area is control-plane coherence, not row/file durability:
    - `/driver/sync-status` can report idle while `/driver/sync` is still rejected as already in progress
    - resumed runs after crash are not deterministic about whether they self-finish on relaunch or wait for the next admitted sync

## Crash-Gate Recovery Fix Wave — 2026-04-07
- Root cause analysis:
  - the false-idle defect was not a broad retry failure; it was a split-brain control-plane issue
  - `/driver/sync-status` had been reporting only the in-memory `SyncStatusStore.isSyncing` flag while the coordinator admission path still respected the shared SQLite advisory gate (`sync_lock` + `sync_control.pulling`)
  - after a killed sync, those persisted gate rows could outlive the process and block new runs even though status looked idle
- Code fix landed before the next live replay:
  - startup now runs explicit crash recovery over the shared run-state store, clearing stale `sync_lock` and resetting `sync_control.pulling`
  - `DriverServer /driver/sync-status` now reports the effective shared gate through `SyncCoordinator.isSyncGateActive()` instead of reading only the in-memory status store
- Live proof used the exact persisted failure state, not a vague approximation:
  - target: live Windows SQLite store at `.dart_tool/sqflite_common_ffi/databases/construction_inspector.db`
  - seeded rows before relaunch:
    - `sync_lock(id=1, locked_by='crash-replay', locked_at='2026-04-07T23:10:00.000Z', last_heartbeat='2026-04-07T23:10:00.000Z')`
    - `sync_control(key='pulling', value='1')`
  - after relaunch of the real Windows driver app:
    - `sync_lock` count returned `0`
    - `sync_control.pulling` returned `0`
    - `/driver/sync-status` returned `{"isSyncing":false,"pendingCount":0,"lastSyncTime":"2026-04-07T23:09:05.20636Z"}`
    - an immediate `/driver/sync` call was admitted and returned `{"success":true,"pushed":0,"pulled":0,"errors":[]}`
- Conclusion from the wave:
  - the stale crash-left gate defect is closed live
  - the remaining architecture note in retry/restart is now the lack of a persisted delayed retry queue, not hidden stale run-state

## Quick-Resume Mode Wave — 2026-04-07
- Objective:
  - prove that a device with fresh data resumes through the quick foreground catch-up path and materializes a new shared-scope change without a manual sync call
- First attempt:
  - I used `DriverServer /driver/update-record` against `projects`
  - that path updated SQLite directly but did not create a real `change_log` entry for this table, so it was rejected as a valid sync mutation proof and not counted as the lane result
- Validated live setup:
  - shared project: `e7dde2a2-8662-4d5a-ad32-3e167ad5576d`
  - shared entry: `37214186-5025-422b-900c-ca8a5a6611da`
  - trigger-backed mutation path: `entry_quantities` generic create endpoint
  - new row used for the decisive proof: `f369778b-4d4d-4fd5-a1c4-613540ee5724`
- Proof steps:
  - baseline S21 `/driver/sync-status` before backgrounding showed a fresh `lastSyncTime` (`2026-04-07T23:15:52.622802Z`)
  - S21 was backgrounded to Home with `adb shell input keyevent 3`
  - Windows created `entry_quantities/f369778b-4d4d-4fd5-a1c4-613540ee5724` locally through `/driver/create-record`
  - Windows `change_log?table=entry_quantities` showed `count = 1`
  - Windows manual sync then pushed the row successfully: `{"success":true,"pushed":1,"pulled":0,"errors":[]}`
  - while S21 was still backgrounded, `/driver/local-record?table=entry_quantities&id=f369778b-4d4d-4fd5-a1c4-613540ee5724` returned not found
  - S21 was then brought back to the foreground with `adb shell am start -n com.fieldguideapp.inspector/.MainActivity`
  - without any manual `/driver/sync` call on S21, `/driver/local-record` began returning the new row locally:
    - `quantity = 207.407`
    - `project_id = e7dde2a2-8662-4d5a-ad32-3e167ad5576d`
- Conclusion from the wave:
  - quick-resume catch-up is now live-proven on a shared trigger-backed table
  - the key negative check passed: the row was absent while S21 stayed backgrounded and only appeared after foreground resume
  - one follow-up observation remains for the next mode lane: persisted `last_sync_time` did not advance during this catch-up, so realtime-hint / quick-mode diagnostics should watch whether that is a deliberate non-sync delivery path or a metadata writeback gap

## Realtime-Hint Mode Wave — 2026-04-07
- Objective:
  - prove that a foreground, already-subscribed device receives a private `sync_hint` broadcast and triggers a quick sync without lifecycle transition or manual sync
- Driver/diagnostic hardening landed before the live reruns:
  - `/diagnostics/sync_transport` now exposes `transportHealth` and last-run summaries from the live app
  - `RealtimeHintHandler` now subscribes with `RealtimeChannelConfig(private: true)` and the unit test contract locks that in
- First live defect found:
  - after the client switched to private channels, S21 subscription failed with:
    - `Unauthorized: You do not have permissions to read from this Channel topic: sync_hint:88adb079...`
  - fix landed:
    - `20260407234500_authorize_private_sync_hint_channels.sql` adds explicit `realtime.messages` SELECT policy keyed to `sync_hint_subscriptions.channel_name = realtime.topic()`
- Second live defect path:
  - after the auth policy fix, both devices reported:
    - `transportHealth.status = active`
    - `reason = subscribed`
    - `realtime_channel_active = true`
    - `fallback_polling_active = false`
  - but foreground hint delivery still did not happen
- Trigger/fanout hardening attempts landed during the same wave:
  - `20260407233000_restore_private_sync_hint_fanout.sql`
    - restores explicit private-channel fanout alongside `invoke_daily_sync_push(...)`
  - `20260407235500_fix_private_sync_hint_broadcast_url.sql`
    - aligns the trigger-side fanout URL with the edge function’s `/realtime/v1/api/broadcast` route
  - `20260408001000_use_realtime_send_for_private_sync_hints.sql`
    - replaces trigger-side HTTP fanout with the canonical `realtime.send(...)` database path
  - `server_hint_plumbing_test.dart` now characterizes the auth policy and the canonical `realtime.send(...)` fanout contract so this path cannot silently revert
- Live probe setup:
  - shared project: `e7dde2a2-8662-4d5a-ad32-3e167ad5576d`
  - shared entry: `37214186-5025-422b-900c-ca8a5a6611da`
  - shared bid item: `671fabea-0f81-4ca8-8e35-6be674b6f550`
  - S21 remained foregrounded on `/projects`
  - Windows created and pushed three fresh `entry_quantities` rows:
    - `617881ce-4098-4141-a0d3-c6a0307eab1a`
    - `74fc22b2-d09b-4214-8c26-3624ee0677fe`
    - `88984b0f-212d-4bdc-8f9e-2250106746d6`
  - each Windows push returned `{"success":true,"pushed":1,"pulled":0,"errors":[]}`
- Negative result:
  - on all three probes, S21 stayed `active/subscribed` for the full `12s` poll window
  - S21 `/diagnostics/sync_transport.lastRun` did not change during the poll window
  - S21 `/driver/local-record?table=entry_quantities&id=<probe>` stayed `Record not found`
  - `adb logcat` showed no `RealtimeHintHandler: marked dirty ...` or `RealtimeHintHandler: triggering quick sync ...` activity tied to the probe pushes
  - Windows stdout also showed no hint-side activity after its own push, which means the delivery gap is upstream of both clients rather than receiver-only
- Manual recovery check:
  - a manual S21 `/driver/sync` after the failed probes returned `{"success":true,"pushed":0,"pulled":2,"errors":[]}`
  - that proves remote changes were still pullable through the normal path even though foreground invalidation never fired
- Conclusion from the wave:
  - private-channel registration and authorization were necessary but not sufficient
  - the live branch-level fix was architectural: sender push now emits foreground `sync_hint` through an explicit owned RPC executor instead of relying only on opaque remote trigger side effects
  - simplifying channel lookup to `sync_hint_subscriptions` itself removed another hidden dependency from the fanout path

## Realtime-Hint Repair Rerun — 2026-04-07
- Architecture changes landed after the failed probe wave:
  - `20260408013000_add_emit_sync_hint_rpc.sql`
    - adds authenticated `emit_sync_hint(...)` so the sanctioned client push executor can explicitly emit the foreground hint after a successful remote write
  - `20260408014000_simplify_sync_hint_channel_lookup.sql`
    - removes the unnecessary `user_profiles` join from private fanout and active-channel lookup, leaving `sync_hint_subscriptions` as the single source of truth for live channel routing
  - app-side push path now calls the owned emitter after successful upsert / insert-only / file push / soft-delete push
- First validation after the executor wiring still missed:
  - Windows pushes of `entry_quantities/864f2878-dfcd-458d-bc30-485988714e87` did not materialize on S21
  - that isolated the remaining problem to the company fanout lookup rather than the client subscription path
- Decisive live proof after the simplified channel lookup:
  - both devices relaunched healthy and subscribed:
    - Windows `channel_name = sync_hint:0a3bf671...`
    - S21 `channel_name = sync_hint:88adb079...`
  - Windows created and pushed fresh shared row:
    - `entry_quantities/680adba1-50ac-47ee-894b-251ecd059f4f`
    - payload lived under shared project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d`
    - Windows sync result: `{"success":true,"pushed":1,"pulled":0,"errors":[]}`
  - without any manual S21 `/driver/sync` call:
    - S21 `/diagnostics/sync_transport` recorded a new successful run
      - `pulled = 2`
      - `completedAt = 2026-04-07T20:20:27.056652`
    - S21 `/driver/local-record?table=entry_quantities&id=680adba1-50ac-47ee-894b-251ecd059f4f` returned the row locally
- Conclusion from the rerun:
  - the realtime-hint lane is now closed live
  - the owned push-side emitter is the contract we should rely on going forward for deterministic foreground invalidation
  - remote trigger fanout can remain as a fallback path, but it is no longer the sole proof surface for foreground convergence

## Global Full Sync Wave — 2026-04-07
- Objective:
  - prove that a true full sync still catches unrelated remote drift even when no dirty-scope hint exists
- Shared fixture:
  - project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d`
- Windows proof:
  - staged remote no-hint project rename to `VRF Global Sweep Win 211633`
  - Windows `POST /driver/sync` returned `{"success":true,"pushed":0,"pulled":1,"errors":[]}`
  - Windows local project row updated to the same name
  - runtime diagnostics reported `lastRequestedMode = full` and `lastRunHadDirtyScopesBeforeSync = false`
- S21 proof:
  - staged remote no-hint project rename to `VRF Global Sweep S21 211701`
  - S21 `POST /driver/sync` returned `{"success":true,"pushed":0,"pulled":1,"errors":[]}`
  - S21 local project row updated to the same name
  - runtime diagnostics again reported `lastRequestedMode = full` and `lastRunHadDirtyScopesBeforeSync = false`
- Conclusion:
  - full sync mode remains a reliable catch-up path for unrelated remote drift on both devices

## Dirty-Scope Isolation Wave — 2026-04-07
- Objective:
  - prove that private sync hints only materialize the intended dirty scope instead of broadening to unrelated project drift
- Root cause fixed before the decisive rerun:
  - `RealtimeHintHandler` had been parsing a flat payload shape while private broadcasts arrived in an envelope
  - after normalizing nested `payload` / `data.payload`, the receiver now derives dirty scopes from the actual live private broadcast
- Fixture:
  - shared project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d`
  - unrelated remote-drift target `4825141a-7b6b-44f9-9ef1-ba5e89dc39fd`
  - scoped probe `entry_quantities/e3d86498-88dc-49e7-9406-9472de84a2fa`
- Proof steps:
  - staged a no-hint remote rename on project `4825141a-7b6b-44f9-9ef1-ba5e89dc39fd` using replicated admin SQL
  - created and pushed scoped quantity `e3d86498-88dc-49e7-9406-9472de84a2fa` from Windows under project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d`
  - kept S21 foregrounded and waited for the hint-driven quick run
- Result:
  - S21 materialized the scoped quantity locally
  - logcat recorded `RealtimeHintHandler: marked dirty project=e7dde2a2-8662-4d5a-ad32-3e167ad5576d table=entry_quantities`
  - quick pull skipped unrelated tables such as `projects` and `project_assignments`
  - S21 local project `4825141a-7b6b-44f9-9ef1-ba5e89dc39fd` retained its older name and did not absorb the unrelated no-hint rename
- Conclusion:
  - dirty-scope isolation is now live-proven rather than inferred

## Private Channel Registration + Rebind Wave — 2026-04-07
- Objective:
  - prove that `sync_hint_subscriptions` remains the authoritative lifecycle store for channel registration, teardown, and rebind
- Active subscriptions before teardown:
  - S21 active row on `sync_hint:88adb079...`
  - Windows active row `a3a1c799-e8f3-4d4b-9a89-84348f0d3738` on `sync_hint:0a3bf671...` for device install `8361b13c-5f53-4cef-8fc4-211edcb21b49`
- Teardown / rebind proof:
  - signed out on Windows through `/settings`
  - queried `sync_hint_subscriptions` and confirmed the prior Windows row was revoked with `revoked_at` populated
  - signed back in on the same Windows install
  - queried `sync_hint_subscriptions` again and confirmed a new active row `dea887bf-911e-4b15-a0a3-3f8079180db7` on `sync_hint:fd401b14...` for the same `device_install_id`
  - confirmed only one active row remained for that install
- Post-rebind foreground proof:
  - S21 created and pushed `entry_quantities/ed816553-474a-40a9-880a-e11d85884110`
  - Windows stayed foregrounded and subscribed on the new channel
  - Windows transport showed a fresh pull and local SQLite materialized the new row without a manual sync call
- Conclusion:
  - private-channel registration, teardown, and rebind are now live-proven end to end

## Final Mixed-Flow Soak Wave — 2026-04-07
- Objective:
  - prove that the hardened sync engine survives a realistic mixed user flow without drift, resurrection, or queue residue
- Shared fixtures:
  - project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d`
  - entry `37214186-5025-422b-900c-ca8a5a6611da`
  - active file-backed photo `1ff02e3e-ea39-4b24-b36e-b5374e9f1737`
  - soak quantity `749fe7e9-cf6a-4ef0-8f8d-7b6df4e057e7`
- Flow:
  - S21 created quantity `749fe7e9-cf6a-4ef0-8f8d-7b6df4e057e7` and pushed it
  - Windows auto-materialized the row and confirmed the active photo still existed locally
  - Windows edited the same quantity and pushed it
  - S21 auto-materialized the edit
  - S21 first attempted a bad synthetic tombstone payload (`deleted_by = soak_s21`) and the system failed loudly with Postgres `22P02 invalid input syntax for type uuid`
  - S21 corrected the same tombstone using the real device user UUID and pushed successfully
  - Windows converged to the tombstoned quantity
  - Windows remove-from-device dropped the local project scope, including the active photo and the deleted quantity
  - Windows fresh full sync rematerialized the active photo but did not resurrect the deleted quantity
  - forced integrity plus two repeat sync cycles ended at `{"success":true,"pushed":0,"pulled":0,"errors":[]}` on both devices, and both `entry_quantities` change logs returned `count = 0`
- Conclusion:
  - the mixed-flow soak closed cleanly with no silent drift, no resurrection of deleted state, and no residual pending sync work
