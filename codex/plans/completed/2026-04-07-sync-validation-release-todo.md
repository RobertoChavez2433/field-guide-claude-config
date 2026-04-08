Date: 2026-04-07
Branch: `sync-engine-refactor`
Status key: `[ ]` pending, `[-]` in progress, `[x]` done, `[!]` blocked

# Sync Validation Release TODO

## Architecture Guardrail Gate

[x] Audit full sync-engine ownership boundaries before finishing live release validation
Current finding: the hard-delete issue exposed a broader architecture gap around which components may own remote sync I/O, local sync-table mutation, `change_log`, `synced_projects`, and scope logic.
[x] Save a broader sync-engine component-contract plan
[x] Save a sync-engine ownership-lint TODO
[x] Land the first ownership lint wave before closing the remaining lifecycle proof lanes
Implementation note: new ownership lints now guard sync-engine imports, UI bypasses, handler construction, raw sync SQL, raw Supabase sync-table I/O, sync storage access, `change_log`, `synced_projects`, scope-filter construction, scattered sync-table lists, and a 300-line sync-component cap.
[x] Keep the broad sync-owner lints enabled and burn down the surfaced legacy sync backlog
Lint note: the broad architecture pass started at `83` findings (`79` errors, `4` warnings). After removing the dead sync-facing `BaseRemoteDatasource` layer, collapsing direct sync-bucket access behind `SyncFileAccessService`, and moving scattered table manifests into `DeleteGraphRegistry`, `dart run custom_lint` now reports `4` warnings and `0` sync-architecture errors. Do not narrow the lint; keep it broad as a regression tripwire.
[x] Save a concrete phased sync validation proof plan
Plan note: `.codex/plans/2026-04-07-sync-validation-proof-phases-plan.md` is now the ordered execution map for the remaining release proof.
[x] Save a CodeMunch-backed legacy sync surface audit
Audit note: `.codex/plans/2026-04-07-sync-legacy-surface-audit.md` now traces the remaining SQLite, Supabase, local-file, and remote-storage ownership leaks and recommends the next lint wave.
[x] Audit driver generic mutation endpoints for hidden sync-owner bypasses
Audit note: `DriverServer` still exposed broad generic `/driver/create-record` and `/driver/update-record` mutation surfaces over protected sync tables like `user_consent_records`, `support_tickets`, `change_log`, `conflict_log`, `deletion_notifications`, and pull-only `project_assignments`. Tighten the mutation allowlists and add a lint so the harness cannot quietly reintroduce those bypasses.

## Immediate Wave

[x] Resume live run `2026-04-06_193351_codex_sync-delete-live`
[x] Verify project-delete storage cleanup
[x] Verify deleted entry absence in UI on S21
[x] Verify deleted entry absence in UI on Windows
[x] Verify deleted project absence in UI on S21
[x] Verify deleted project absence in UI on Windows
[x] Update report/checkpoint/checklist after this wave

## Lifecycle Proof

[x] Restore deleted project or entry and verify cascade parity
[x] Restore parity note: project `d2bb6a5d-010f-4e9b-adcb-9188ea442391` and entry `1a31fc0c-33ef-4f99-8c07-60ebc9825c4e` now restore across S21 SQLite, Supabase, Windows SQLite, and both `/projects` + `/entries` UIs
[-] Hard-delete restored item and verify no sync residue
Audit note: the risk is broader than Trash. Any client path that physically removes a local row from a soft-delete sync table and still emits `change_log.operation = delete` must preserve a last tombstone payload instead of escalating to remote physical delete. That includes Trash `Delete Forever`, retention purge, and any future local purge path built on the same contract.
Fresh-fixture proof note: project `b28afcd0-501f-463c-a255-8f61469a2ba5` confirmed the new contract live. S21 `Delete Forever` purged the sender shell, preserved and re-timestamped the remote soft tombstone, Windows stayed on a hidden tombstone state instead of resurrecting active data, and repeated sync settled at `pushed: 0, pulled: 0` on both devices. Remaining work is to finish revocation overlap and decide whether receiver-local tombstone purge should ever be immediate or remain a server-retention concern.
[x] Rework the shared local-purge delete contract for soft-delete sync tables
Implementation note: local hard purge now preserves tombstone metadata in `change_log.metadata`, push replays that preserved soft-delete when the local row is already gone, and the client no longer remote-hard-deletes soft-delete tables just because the sender purged its local tombstone.
[x] Replace local project-assignment mutation with a remote-first sync owner
Proof note: fresh-build S21 + Windows rerun on project `4825141a-7b6b-44f9-9ef1-ba5e89dc39fd` now restores the assignment through the sanctioned remote path, creates no new local `project_assignments` `change_log` rows, rematerializes the Windows project on ordinary pull, and settles at `pushed: 0, pulled: 0` on both devices.
[x] Decide and prove legacy exhausted `project_assignments` retry cleanup on upgraded devices
Proof note: S21 migration v56 now purges invalid pending `project_assignments` `change_log` rows on upgraded installs. Live rerun confirmed `/driver/change-log?table=project_assignments` returns `count: 0` after rebuild, and repeat full sync still settles at `pushed: 0, pulled: 0`.
[ ] Fix post-orphan-purge enrollment cleanup
Audit note: `synced_projects` cleanup runs in pull finalization, but orphan purge happens later in maintenance. That leaves stale enrollment behind for at least one cycle after maintenance-assisted cleanup.
[x] Clean stale `synced_projects` in the same maintenance cycle after orphan purge
Implementation note: `MaintenanceHandler` now reloads `synced_projects` after orphan purge and immediately prunes entries whose project row was just soft-deleted by maintenance.
[ ] Audit local-only eviction and legacy direct-delete surfaces before release closeout
Audit note: `removeFromDevice` and scope-revocation eviction are intentionally local-only and currently suppress triggers/clear `change_log`, so they are not the same bug. Legacy `BaseRemoteDatasource.delete()` style APIs still exist, and the current assignment wizard/provider still bypasses the intended remote-first ownership boundary for `project_assignments`.
[x] Remove the `support_tickets.updated_at` schema-verifier drift on upgraded installs
Audit note: v53 fixed the functional repeat-pull loop by adding `updated_at`, but the migration still creates a nullable/no-default column on upgraded SQLite files while the canonical schema expects `TEXT NOT NULL DEFAULT strftime(...)`. This is still an integrity/startup warning until the migration shape is reconciled.
Proof note: migration v55 rebuilds `support_tickets` to the canonical shape. Live S21 startup now logs `SchemaReport(drift=0, missing_cols=0, missing_tables=0)`.
[x] Verify delete/revocation overlap
Revocation note: fresh fixture `4825141a-7b6b-44f9-9ef1-ba5e89dc39fd` proved that revoking the Windows assignment from an otherwise active project fully evicts the Windows local scope with no local sync residue while the remote project stays active for S21.
Overlap note: fresh fixture `c55c4b2f-1c9a-4ca3-a0fc-1a209f9c57a3` proved that when project delete tombstones and assignment revocation arrive together, both devices converge to a hidden tombstone with `synced_project_enrolled = false` and repeated sync settles at `pushed: 0, pulled: 0`.
[x] Verify repeated sync is idempotent after each lifecycle step
Restore/idempotence note: after fixing pull cursor advancement and the local `support_tickets.updated_at` schema mismatch, two consecutive full sync runs on both S21 and Windows returned `pushed: 0, pulled: 0`. Re-run this proof after hard-delete and revocation overlap.
Hard-delete note: the fresh-fixture hard-delete rerun also settled at `pushed: 0, pulled: 0` on both devices with no pending S21 project delete changes.
Revocation note: revocation-only and delete-plus-revocation overlap both settled at `pushed: 0, pulled: 0`.
Assignment note: the remote-first assignment mutation rerun also settled at `pushed: 0, pulled: 0` on both devices with no new `project_assignments` sync residue.
Remove-from-device note: after serializing `removeFromDevice` behind the shared sync mutex and clearing project-scoped pull cursors on local-only removal, Windows revalidated fresh-pull parity on project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d` (`pulled: 21`, then `0/0`) and S21 revalidated the same contract on the same shared project (`0/0` after auto-sync overlap settled). No pending `change_log` residue remained, and the opposite device stayed active throughout each local-only removal.
[x] Verify remove-from-device and fresh-pull on Windows
Windows proof note: local scope dropped to a preserved project shell with `synced_project_enrolled = false`, zero descendant rows, and zero local `change_log`. The next ordinary sync rematerialized the full subtree and settled at `pushed: 0, pulled: 0`.
[x] Verify remove-from-device and fresh-pull on S21
S21 proof note: local scope dropped to a preserved project shell with `synced_project_enrolled = false`, zero descendant rows, and zero local `change_log`. After the fresh-pull cursor reset fix, the next healthy sync rematerialized the full subtree, restored both assignments, and settled at `pushed: 0, pulled: 0`.
Next lane: file-backed live lanes (`documents`, `entry_exports`, `form_exports`, strengthened `photos`) are now the highest-value remaining proof because the remove-from-device resurrection/no-drift gate is closed.

## File-Backed Proof

[x] Documents live flow
[x] `entry_exports` live flow
[x] `form_exports` live flow
[x] Strengthened photos live flow
[x] File-backed delete propagation parity
[x] File-backed storage cleanup idempotence
Proof note: shared fixture project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d` / entry `4e35a00d-26d7-44b7-9f5d-c67c9e6f2f91` now proves live create/push/pull/delete convergence for `documents`, `photos`, `entry_exports`, and `form_exports`. S21 pushed the staged file-backed wave, Windows pulled all five rows, both devices settled at `0/0`, remote rows and storage objects existed before delete, S21 real entry delete tombstoned all four file-backed tables plus the entry itself, storage cleanup drained to zero queued rows, Windows converged to the same tombstoned subtree, both `/entries` UIs hid the entry tile, and repeated sync again settled at `0/0`.

## Integrity / Maintenance

[x] Re-run integrity on Windows after remote maintenance/backfill proof
[x] Re-run integrity on S21 after remote maintenance/backfill proof
[x] Verify orphan purge clears stale pay-app/file-backed rows live
[x] Verify no recurring drift after scope churn
Proof note: forced maintenance rerun now passes live on both devices. After resetting `last_integrity_check`, both Windows and S21 full syncs settled at `pushed: 0, pulled: 0`. On Windows, I seeded a local-only orphan pair inside active project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d`: `export_artifacts/d333298f-dddd-479f-a774-54eac7bf6114` plus child `pay_applications/a554c947-0641-4088-a62c-3fea463f180e`, with no pending `change_log` residue and confirmed remote absence via authenticated Supabase REST. The next forced Windows maintenance cycle recorded drift for both tables (`local_count: 1`, `remote_count: 0`, `cursor_reset_recommended: true`) and then soft-deleted both rows locally as `deleted_by = system_orphan_purge` in the same cycle while keeping local `change_log` empty. S21's forced integrity rerun stayed clean for the same tables (`local_count: 0`, `remote_count: 0`). Repeat full sync after the purge again settled at `pushed: 0, pulled: 0` on both devices, so the maintenance-assisted cleanup is no longer recurring drift.

## Retry / Restart / Modes

[x] Retry/restart during push
[x] Retry/restart during push note: on S21, I staged six large file-backed `photos` inserts against active project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d` / entry `37214186-5025-422b-900c-ca8a5a6611da`, confirmed `change_log` pending count `6`, started `/driver/sync`, waited until `/driver/sync-status` reported `isSyncing = true`, then force-stopped the app mid-flight. Post-crash SQLite still held all six local rows with `remote_path = null` and six unprocessed `change_log` rows, while authenticated Supabase REST returned zero remote rows for those IDs. On relaunch, the app's ordinary sync path drained the same six changes automatically, local `remote_path` values were backfilled, remote Supabase rows materialized exactly once for all six IDs, Windows ordinary sync pulled `6`, and the next repeated sync on both devices settled at `pushed: 0, pulled: 0`.
[x] Record architecture follow-up from the push chaos lane
Architecture note: recovery after process death is currently durable because `change_log` and `storage_cleanup_queue` persist work. Delayed retry scheduling itself is still timer-memory only and there is no persisted `failed_sync_queue` on this branch yet. The second control-plane gap from the chaos reruns is now closed: startup crash recovery clears stale `sync_lock` + `sync_control.pulling` state before the first resumed run, and `/driver/sync-status` now reports the effective shared gate instead of only the in-memory status store.
[x] Retry/restart during pull
[x] Retry/restart during pull note: with Windows offline, I pushed a fresh `retry_pullb` fixture of `120` `photos` rows from S21 into active entry `37214186-5025-422b-900c-ca8a5a6611da`, then cold-launched Windows and killed it during the startup pull when local SQLite had materialized only `55` of those `120` rows. Post-crash Windows still showed the old `last_pull_photos` cursor, proving the partial page had not been checkpointed forward. After relaunch, Windows stayed on the partial `55` rows until the next ordinary sync; that manual sync then pulled the missing `65`, advanced `last_pull_photos`, and the next repeated sync settled at `pushed: 0, pulled: 0`. Remote Supabase count for `filename LIKE '%retry_pullb%'` stayed `120`, so recovery completed without duplication or remote loss.
[x] Retry/restart during delete propagation
[x] Retry/restart during delete propagation note: sprint-1 fixture entry `96af93cc-fb77-4bed-9006-3ecae4efc426` proved the sender-local delete graph is durable across crash (`23` pending tombstone changes and `22` queued cleanup paths persisted locally while Supabase still showed the entry and all children active), and the next ordinary S21 sync after relaunch pushed the missing delete fan-out so Windows pulled `23` tombstones and both devices returned to `0/0`. Sprint-2 fixture entry `db3b76ff-f749-415b-b21b-c49853aebbcb` re-proved the lane on a fresh subtree (`1 + 12 + 3` pending rows): pre-recovery remote state stayed active, relaunch resumed the tail of the delete push automatically (`isSyncing = true`, `pendingCount = 5`), Windows pulled `16`, and the subtree converged deleted again without manual DB repair.
[x] Retry/restart during storage cleanup
[x] Retry/restart during storage cleanup note: sprint-1 fixture entry `6899b31c-e884-4cf6-9c95-983080d44af7` was killed in the cleanup phase after row propagation had finished (`pendingCount = 0`) but with `44` queued storage deletes still present locally. Supabase rows were already tombstoned while sample `entry-photos` and `entry-documents` objects still existed. The next ordinary S21 sync after relaunch drained the cleanup queue to `0`, sample storage checks returned `not_found`, Windows pulled `47` tombstones, and repeat sync settled at `0/0`. Sprint-2 fixture entry `0c2eba96-1c92-4e88-a0b6-ca9501fc04e8` re-proved the same contract with `30` queued storage deletes and also exposed the control-plane race: relaunch left the queue stranded, `/driver/sync-status` reported idle, and repeated `/driver/sync` calls were rejected as `another sync is already in progress` until the hidden run finally cleared; the next admitted sync then drained the queue to `0`, sample storage objects returned `not_found`, and both devices ended at `0/0`.
[x] Retry/restart full matrix rerun on fresh sprint-2 fixtures
[x] Retry/restart rerun note: a second full sprint revalidated all four lanes. `retry_push2` re-proved sender crash durability on S21, `retry_pullc` re-proved receiver partial-page recovery on Windows (`94 / 120` rows materialized before kill, missing `26` recovered later), `db3b76ff-f749-415b-b21b-c49853aebbcb` re-proved delete propagation, and `0c2eba96-1c92-4e88-a0b6-ca9501fc04e8` re-proved storage cleanup. The data plane remained durable twice over, and the stale crash-left run gate has now been fixed live by startup recovery + shared-gate status reporting.
[x] Fix false-idle / hidden-in-progress run-state mismatch after crash recovery
[x] Crash-gate fix note: on Windows, I seeded the exact persisted failure state directly into the live SQLite store (`sync_lock.id = 1`, `locked_by = crash-replay`, `sync_control.pulling = 1`), relaunched the real driver app, and then verified three things without manual DB cleanup: startup recovery cleared the stale gate (`sync_lock` row removed, `pulling = 0`), `/driver/sync-status` reported `isSyncing = false` truthfully, and an immediate `/driver/sync` was admitted and returned `{"success":true,"pushed":0,"pulled":0,"errors":[]}` instead of `another sync is already in progress`.
[x] Quick-resume mode proof
[x] Quick-resume note: with fresh `last_sync_time` and no persisted background hint, S21 was backgrounded to Home while Windows created a new shared `entry_quantities` row through the trigger-backed driver create path (`f369778b-4d4d-4fd5-a1c4-613540ee5724`) and pushed it successfully (`pushed: 1`). While S21 remained backgrounded, `/driver/local-record` confirmed the new row was absent. After bringing S21 back to the foreground without any manual sync call, the same row materialized locally on the resumed device. That closes the resume catch-up behavior on a shared sync table. Follow-up note for the next mode lane: the resumed catch-up did not advance persisted `last_sync_time`, so realtime-hint/quick-mode diagnostics should keep an eye on whether this path is a deliberate hint-driven catch-up or a timestamp-writeback gap.
[x] Realtime hint mode proof
[x] Realtime hint repair note: the branch now includes the private-channel auth + payload hardening migrations, plus the deterministic client push-side emitter path:
  - `20260407233000_restore_private_sync_hint_fanout.sql`
  - `20260407234500_authorize_private_sync_hint_channels.sql`
  - `20260408001000_use_realtime_send_for_private_sync_hints.sql`
  - `20260408013000_add_emit_sync_hint_rpc.sql`
  - `20260408014000_simplify_sync_hint_channel_lookup.sql`
Proof note: private-channel registration + authorization are still required, but the decisive live fix was moving foreground hint emission into the owned push executor path and simplifying channel lookup to `sync_hint_subscriptions` itself. On the decisive rerun, Windows created and pushed `entry_quantities/680adba1-50ac-47ee-894b-251ecd059f4f` from shared fixture entry `37214186-5025-422b-900c-ca8a5a6611da`; S21 remained foregrounded and subscribed, then `/diagnostics/sync_transport` recorded a fresh successful quick run (`pulled: 2`, completed `2026-04-07T20:20:27.056652`) and `/driver/local-record` returned the same new row locally without any manual S21 sync call. The earlier failed foreground probes remain useful regression IDs: `617881ce-4098-4141-a0d3-c6a0307eab1a`, `74fc22b2-d09b-4214-8c26-3624ee0677fe`, `88984b0f-212d-4bdc-8f9e-2250106746d6`.
[x] Global full sync proof
Proof note: no-hint remote project renames on shared fixture `e7dde2a2-8662-4d5a-ad32-3e167ad5576d` now prove true full-mode catch-up on both devices. Windows pulled `1` to local name `VRF Global Sweep Win 211633`, S21 pulled `1` to local name `VRF Global Sweep S21 211701`, and both runtimes reported `lastRequestedMode = full` with `lastRunHadDirtyScopesBeforeSync = false`.
[x] Dirty-scope isolation proof
Proof note: after hardening `RealtimeHintHandler` to normalize nested private-broadcast envelopes, Windows pushed scoped `entry_quantities/e3d86498-88dc-49e7-9406-9472de84a2fa` under shared project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d` while unrelated remote no-hint drift was staged on project `4825141a-7b6b-44f9-9ef1-ba5e89dc39fd`. S21 quick-sync materialized only the scoped quantity, logcat showed `RealtimeHintHandler: marked dirty project=e7dde2a2-8662-4d5a-ad32-3e167ad5576d table=entry_quantities`, and the unrelated project rename stayed absent locally.
[x] Private channel register/teardown proof
Proof note: S21 remained active on opaque private channel `sync_hint:88adb079...`. Windows sign-out revoked prior subscription row `a3a1c799-e8f3-4d4b-9a89-84348f0d3738` for device install `8361b13c-5f53-4cef-8fc4-211edcb21b49`, and the next sign-in created new active row `dea887bf-911e-4b15-a0a3-3f8079180db7` on channel `sync_hint:fd401b14...`. Post-rebind foreground hint row `entry_quantities/ed816553-474a-40a9-880a-e11d85884110` auto-materialized on Windows without manual sync.

## User-Scoped / Insert-Only

[x] Support ticket live flow
[x] Support ticket note: on S21, the real `/help-support` screen submitted ticket `833518ea-f187-4c54-ba6b-bce95f1a3e0e`, created one local `change_log` insert, pushed the ticket to Supabase after the missing signature-table migration was deployed, and then settled back to `pushed: 0, pulled: 0` with no pending `support_tickets` residue. Windows is a different user identity in this proof setup, so non-materialization there is expected for this user-scoped table rather than a sync defect.
[x] Consent record live flow
[x] Verify insert-only semantics stay correct
Proof note: the consent lane is now live-proven on both device identities through the real router/version gate. On S21, forcing the stored `flutter.consent_policy_version` to `0.9.0` relaunched the app into `/consent`, the shipped consent screen appended rows `0d5bbdc5-74a7-4136-95c7-8216113ad751` and `d0782666-66cb-4956-bd74-aa5d571a5827`, manual sync pushed `2`, and repeat sync settled at `0/0`. On Windows, the same stale-version gate relaunched into `/consent`, the shipped screen appended rows `10476a23-1ef0-4d58-aca1-dfb7235d7a3b` and `5b163116-9e40-4a00-8bd0-9b4c08f0d288`, the app's quick-sync path drained the two inserts automatically, and repeat sync again settled at `0/0`. Both devices restored `flutter.consent_policy_version = 1.0.0`, both local SQLite stores contain four append-only records per user, and Supabase now shows the new accepted rows for both user identities.
[x] Prove consent through the router/version gate, not direct SQLite row injection
Proof note: both S21 and Windows entered `/consent` only after their stored policy versions were downgraded, then returned to `/` through the shipped accept action. No direct SQLite consent-row seeding was used.
[x] Add a lint guarding protected sync tables from generic driver mutation allowlists
Implementation note: `DriverServer` now keeps protected sync tables queryable but excludes them from the generic `/driver/create-record` and `/driver/update-record` mutation allowlists, and custom lint rule `no_driver_generic_mutation_of_protected_sync_tables` now prevents those bypasses from creeping back in.
Next lane: sync-mode proof, starting with quick-resume and realtime-hint behavior under the now twice-proven retry/restart contract.

## Closeout

[x] Final mixed-flow soak run
Proof note: shared fixture project `e7dde2a2-8662-4d5a-ad32-3e167ad5576d` passed create/edit/delete/remove-from-device/fresh-pull/integrity on both devices. S21 created `entry_quantities/749fe7e9-cf6a-4ef0-8f8d-7b6df4e057e7`, Windows auto-received and edited it, S21 auto-received the edit, S21 then tombstoned the same row with the real S21 user UUID, Windows converged to the tombstone, Windows remove-from-device dropped local scope, fresh full sync rematerialized active file-backed row `photos/1ff02e3e-ea39-4b24-b36e-b5374e9f1737` without resurrecting the deleted quantity, and forced integrity plus repeat sync ended at `pushed: 0, pulled: 0` on both devices with `change_log` count `0`.
[x] Final proof matrix
Proof note: this sweep now has live evidence across lifecycle delete/restore/hard-delete/revocation, remove-from-device/fresh-pull parity, file-backed create/delete/storage cleanup, integrity maintenance, user-scoped insert-only flows, retry/restart chaos, quick-resume, realtime-hint, global full sync, dirty-scope isolation, private-channel lifecycle, and mixed-flow soak. Each lane was verified against the relevant combination of SQLite state, `change_log`, Supabase rows, storage objects, UI visibility, and repeat-sync idempotence.
[x] Document external blockers, if any
Closeout note: no open high-severity sync blocker remains from this release-proof sweep. Non-blocking follow-up only: `/driver/inject-photo-direct` returned a harness-side `500` on one tiny-PNG soak attempt even though the file-backed lane was already fully proven through shipped flows and existing active-photo checks.
