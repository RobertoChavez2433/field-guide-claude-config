# Sync Bulletproof Checklist

Date: 2026-04-06
Branch: `sync-engine-refactor`
Primary devices: Windows + S21 (`RFCNC0Y975L`)
Status key: `[ ]` pending, `[-]` in progress, `[x]` done, `[!]` blocked/external

## Ground Rules

[x] Stay on `sync-engine-refactor`, not the worktree
[x] Use S21 and Windows only for live verification
[ ] Drive verification through real app flows first; use driver/test hooks only at OS boundaries
[ ] Save all live run artifacts under `.claude/test-results/`
[ ] File non-sync runtime defects to GitHub issues with repro + screenshots/logs
[ ] Keep sync defects in this checklist until fixed and re-verified

## Current Architectural Findings

[x] Record the delete-architecture research artifact in `.codex/plans/2026-04-06-sync-delete-architecture-research.md`
[x] Record the materialized-scope architecture replan in `.codex/plans/2026-04-06-sync-materialization-architecture-replan.md`
[x] Confirm active-scope pay-app delete propagation and storage cleanup works on live S21 -> Windows flow
[x] Confirm `removeFromDevice()` previously missed `export_artifacts` / `pay_applications`
[x] Fix `removeFromDevice()` so project eviction removes pay-app metadata and returns `export_artifacts.local_path`
[x] Implement first-class scope-revocation cleanup so data that leaves sync scope does not remain as stale local residue
[x] Decide and document the materialized-view contract for non-enrolled projects: manual remove keeps shell; revoked/invisible scope fully evicts shell + subtree
[x] Decide and document historical repair behavior for already-stale cached scope
[-] Introduce one shared materialized-scope model for pull, integrity, orphan purge, and revocation
[x] Move `viaEntry` scope from denormalized `project_id` fallback assumptions to authoritative `entry_id` scope for pull + integrity
[x] Exclude local-only builtin/null-project rows from integrity where they are not part of the synchronized materialized view
[x] Add Supabase maintenance triggers/backfill so remote `entry_*`.`project_id` stays aligned with parent `daily_entries.project_id`
[x] Diagnose delete-propagation stale-data risk as duplicated graph knowledge, not only large service size
[-] Introduce one shared delete-graph registry for soft delete, remove-from-device, purge, and revocation
[-] Introduce a delete propagation verifier/checkpoint layer for SQLite, change_log, Supabase, storage, and second-client convergence
[x] Expand orphan purge coverage beyond the old hard-coded table list so pay-app and file-backed rows participate in stale-row cleanup

## Regression Coverage

[x] Add regression coverage for project eviction of `export_artifacts` / `pay_applications`
[x] Add regression coverage for revoked/deleted project scope cleanup
[x] Add regression coverage for stale local rows that are no longer remotely visible through RLS
[ ] Add regression coverage for integrity after scope cleanup
[x] Add regression coverage for scope-aware integrity on `viaProject`, `viaEntry`, and `viaContractor` tables
[x] Add regression coverage for builtin/null-project rows excluded from integrity
[x] Add regression coverage so scoped integrity excludes remote tombstones on soft-delete tables
[x] Add regression coverage for `viaEntry` pull when remote child rows are keyed by `entry_id` scope rather than trustworthy `project_id`
[ ] Add regression coverage for restart/retry during delete propagation and cleanup
[x] Add regression coverage for all sync defects found during live verification
[x] Add regression coverage that the shared delete graph includes every file-backed and pay-app table needed by soft delete and eviction
[x] Add regression coverage that orphan purge includes `export_artifacts` from the registered sync graph

## Preflight Per Live Run

[x] Confirm branch and dirty worktree state before each major live pass
[x] Confirm S21 device id is `RFCNC0Y975L`
[x] Confirm Windows driver build is current
[x] Confirm Android S21 driver build is current
[x] Confirm debug server is reachable
[x] Create/refresh `.claude/test-results/<timestamp>_codex_sync-bulletproof/`
[x] Write checkpoint/report skeleton before starting the next live wave
[x] Create a fresh live-delete run directory with checkpoint/report/log placeholders
[x] Confirm both driver ports answer `GET /driver/ready`
[x] Confirm the active Windows + S21 installs are the driver builds, not stale app instances
[x] Record initial `sync-status`, `change_log`, and project roster on both devices before mutating data

## Immediate Live Delete Wave

[x] Wave 1: preflight and capture baseline on Windows + S21
[x] Generate a fresh `VRF-<tag>` project if no safe active delete test project exists
[x] Verify project appears on both clients before starting delete mutation flows
[x] Capture initial SQLite rows and `change_log` counts for project, entry, pay-app, export, and file-backed descendants
[x] Capture initial Supabase rows and storage objects for the same subtree
[x] Capture initial `/driver/delete-propagation` snapshot on the sender and receiver
[x] Wave 2: entry delete propagation through real UI
[x] Delete one active entry from the sender through the production UI
[x] Verify sender local tombstones, file cleanup queue, and pending `change_log` via `/driver/delete-propagation`
[x] Sync sender through Settings UI and verify queue drain
[x] Verify Supabase tombstones and storage cleanup for every file-backed entry descendant
[x] Pull on the second client and verify receiver tombstones + cleared active descendants
[x] Verify receiver UI no longer surfaces the deleted entry
[-] Wave 3: project delete propagation through real UI
[x] Delete the active test project from the sender through the production UI
[x] Verify sender subtree tombstones / eviction state through `/driver/delete-propagation`
[x] Sync sender through Settings UI and verify queue drain plus `synced_projects` removal
[x] Verify Supabase project subtree tombstones and remote storage cleanup
[x] Pull on the second client and verify receiver subtree convergence
[x] Verify receiver UI no longer surfaces the deleted project
[x] Wave 4 restore parity cleared; continue with hard-delete / revocation overlap
[x] Restore the deleted project or entry from trash and verify child restoration parity
[x] Restore parity note: both devices now surface the restored project card and restored entry tile after pull
[-] Hard-delete the restored item from trash and verify no stale SQLite or Supabase residue remains
Audit finding: the shared problem is larger than Trash. Any client-side local purge on a soft-delete sync table that leaves behind `change_log.operation = delete` was escalating to remote physical delete once the local row was gone. That bypasses normal cursor pull for lagging receivers. Windows only converged after maintenance/orphan purge, so the shared local-purge contract was not release-grade.
[x] Rework shared local-purge delete contract so receiver convergence does not depend on integrity/orphan purge
[x] Rework `synced_projects` cleanup so maintenance-assisted orphan purge does not leave stale enrollment behind for an extra cycle
[ ] Re-run hard-delete lane end-to-end after the shared contract patch
[x] Replace local project-assignment mutation with a remote-first sync owner before release closeout
Proof note: fresh-build S21 + Windows rerun on project `4825141a-7b6b-44f9-9ef1-ba5e89dc39fd` now restores assignments through a sanctioned remote RPC path, creates no new local `project_assignments` `change_log` residue, rematerializes the Windows project on ordinary pull, and settles at `pushed: 0, pulled: 0` on both devices.
[x] Decide and prove cleanup/repair handling for legacy exhausted `project_assignments` retries on upgraded devices
Proof note: S21 migration v56 now purges invalid pending `project_assignments` `change_log` rows created by the old local-mutation breach. Live rerun confirmed `/driver/change-log?table=project_assignments` returns `count: 0`.
[ ] Audit local-only scope eviction and legacy direct-delete surfaces before release closeout
[x] Reconcile the v53 `support_tickets.updated_at` migration shape with the canonical schema so upgraded installs stop logging startup/integrity drift
Proof note: migration v55 rebuilds `support_tickets` to the canonical `updated_at TEXT NOT NULL DEFAULT ...` shape. Live S21 startup now logs `SchemaReport(drift=0, missing_cols=0, missing_tables=0)`.
[x] Remove project assignment or otherwise revoke scope, then verify revocation cleanup does not strand stale data
Revocation proof note: active project `4825141a-7b6b-44f9-9ef1-ba5e89dc39fd` was revoked remotely for Windows, and the next ordinary Windows sync fully evicted the local scope with no `change_log` residue while the remote project stayed active for S21.
[-] Verify a repeated sync run after each delete state change remains idempotent
Restore-state note: after fixing pull cursor advancement and the local `support_tickets.updated_at` schema mismatch, two consecutive full sync runs returned `pushed: 0, pulled: 0` on both Windows and S21. Re-run this after hard-delete and revocation.
Revocation-state note: both the active-project revocation proof and the delete-plus-revocation overlap proof settled at `pushed: 0, pulled: 0`.
Assignment-state note: the remote-first assignment mutation rerun also settled at `pushed: 0, pulled: 0` on both devices with no new `project_assignments` sync residue.
Overall gate note: idempotence is no longer blocked by stale S21 `project_assignments` retry residue. The next highest-value proof is remove-from-device/fresh-pull parity to ensure deleted data does not resurrect after cache rebuild.
[ ] Wave 5: cache rebuild / fresh pull confirmation
[ ] Remove the active test project from device on Windows and verify local eviction
[ ] Pull the project back down and verify deleted descendants do not resurrect
[ ] Repeat remove-from-device / fresh pull on S21 if needed for parity
[ ] Save final proof matrix and post-run cleanup notes

## Baseline Local Validation

[x] Re-run targeted pay-app + sync tests after recent fixes
[x] Re-run targeted analyze on touched pay-app + sync files
[x] Re-run lifecycle/delete-related unit tests after the next scope-cleanup change
[x] Re-run focused sync integrity/orphan tests after the next scope-cleanup change
[ ] Re-run file-backed table tests after any delete/storage cleanup change

## Live Sync Lane A: Pay App / Export Artifact

[x] Create pay app on S21 through real UI
[x] Verify sender SQLite row for `export_artifacts`
[x] Verify sender SQLite row for `pay_applications`
[x] Verify sender `change_log` entries exist before sync
[x] Sync sender through UI
[x] Verify sender queue drain
[x] Verify Supabase rows exist
[x] Verify storage object exists in `export-artifacts`
[x] Pull to Windows and verify receiver SQLite rows
[x] Verify Windows receiver UI can open pay-app detail
[x] Delete pay app on S21 through real UI
[x] Verify local tombstones on sender
[x] Verify sender queue drain after delete sync
[x] Verify Supabase tombstones after delete
[x] Verify storage object removed after delete
[x] Pull to Windows and verify receiver tombstones
[ ] Re-run the same flow after scope-cleanup work lands to ensure no regression
[ ] Verify same-range replace does not lose prior file before new metadata persists
[ ] Verify overlap-block flow does not create hidden rows or files
[ ] Verify retry/restart after pay-app create cannot produce duplicate linkage
[ ] Verify retry/restart after pay-app delete cannot strand storage cleanup

## Live Sync Lane B: Scope Revocation / Stale Data

[x] Root-cause why stale local project/data survives after project leaves active sync scope
[x] Capture fresh S21 and Windows local DB snapshots after next live scope test
[x] Verify whether stale rows are due to assignment revocation, remote deletion, or old local unenrollment
[x] Implement automatic cleanup when project leaves `synced_projects` and has no pending changes
[x] Verify cleanup policy on S21: stale project shell behavior matches documented contract
[x] Verify cleanup policy on Windows: stale project shell behavior matches documented contract
[x] Verify historical stale rows are cleaned or explicitly marked for reset
[x] Verify integrity drift disappears or is narrowed to real mismatches only
[x] Verify orphan purge no longer ignores out-of-scope stale project subtrees
[x] Follow up the remaining live integrity drift on `entry_equipment`, `entry_quantities`, `entry_contractors`, and `inspector_forms`
[x] Prove whether remaining drift is scope-contract mismatch, missing remote denormalization maintenance, or true replication loss
[x] Re-run S21 + Windows integrity after scope-aware integrity changes land
[x] Force integrity on Windows + S21 and verify the next sync returns clean with no drift logs
[ ] Re-run S21 + Windows integrity after remote `entry_*`.`project_id` maintenance/backfill lands

## Live Sync Lane C: File-Backed Tables

[ ] S11 documents flow: create through UI path + deterministic boundary, verify SQLite, queue, Supabase, storage, receiver
[ ] `entry_exports` flow: create, sync, verify SQLite, queue, Supabase, storage, receiver
[ ] `form_exports` flow: create, sync, verify SQLite, queue, Supabase, storage, receiver
[ ] Strengthen photos flow so real UI path is exercised before injection boundary
[ ] Re-test delete propagation for file-backed rows under project delete
[ ] Re-test delete propagation for file-backed rows under entry delete
[ ] Re-test remove-from-device for file-backed rows on second client
[ ] Re-test storage cleanup queue idempotence on repeated sync runs

## Live Sync Lane D: Core Sync Modes / Maintenance

[ ] S12 quick-resume catch-up
[ ] S13 foreground realtime hint
[ ] S15 global full sync action + role visibility
[ ] S16 dirty-scope project isolation
[ ] S18 private channel registration
[ ] S19 private channel teardown + rebind
[ ] S17 maintenance housekeeping path if reproducible in current environment
[ ] Verify no sync mode leaves stranded `change_log` work
[ ] Verify mode changes do not reintroduce stale local scope

## Live Sync Lane E: User-Scoped / Insert-Only Tables

[ ] S20 support ticket sync: create through UI, verify sender row, queue, Supabase, receiver/user scoping
[ ] S21 consent audit sync: trigger real consent action, verify insert-only semantics, queue drain, Supabase rows
[ ] Verify neither flow triggers unsupported delete/update assumptions
[x] Fix support-ticket repeat-pull conflict loop caused by local SQLite missing `updated_at` after the remote table gained that column
[ ] Verify integrity checker behavior stays correct for skipped-integrity tables
[ ] Verify upgraded-device startup no longer reports `support_tickets.updated_at` schema drift

## Live Sync Lane F: Delete / Restore / Propagation

[x] Force delete flows to use the shared delete graph instead of duplicated per-service child lists
[x] Project delete cascade through real UI on active synced project
[x] Entry delete cascade through real UI on active synced entry
[ ] Verify sender SQLite tombstones for all affected children
[ ] Verify receiver SQLite tombstones for all affected children
[ ] Verify storage cleanup for all file-backed descendants
[x] Verify delete graph parity across soft delete, remove-from-device, purge, and revocation cleanup
[x] Deduplicate `/driver/delete-propagation` project snapshot output before the next live delete wave
[ ] Verify expanded orphan purge now clears stale pay-app/file-backed rows in live Windows + S21 flows
[x] Verify delete-verification checkpoint captures local tombstone state, queue state, and enrollment state in SQLite
[ ] Extend delete-verification checkpoint to remote row state, remote storage state, and second-client convergence
[x] Verify revocation cleanup does not over-delete active tombstones still needed for replication
Overlap proof note: delete/revocation fixture `c55c4b2f-1c9a-4ca3-a0fc-1a209f9c57a3` converged to a hidden tombstone on both devices with `synced_project_enrolled = false`, so the receiver did not over-evict before delete truth settled.
[x] Verify delete + scope revocation interaction when a project leaves scope during or after tombstone propagation
[ ] Verify restore-from-trash with cascade still works after cleanup changes
[ ] Verify hard delete from trash does not create bad sync residue
[ ] Verify delete propagation under role differences does not lose remote truth

## Cross-Client Fresh-Pull / Cache-Rebuild

[ ] Windows remove-from-device fresh-pull flow for active project
[ ] S21 remove-from-device fresh-pull flow for active project
[ ] Verify fresh-pull rehydrates pay-app/export artifacts correctly
[ ] Verify fresh-pull rehydrates documents/photos/forms correctly
[ ] Verify fresh-pull does not resurrect stale deleted data
[ ] Verify post-fresh-pull integrity is clean

## Non-Sync Bugs To Log Separately

[ ] File the confirmed S21 contractor-comparison overflow/freeze issue on GitHub with screenshots/logs/repro
[ ] File any newly observed non-sync UX/runtime defects encountered during live verification
[ ] Keep GitHub issue IDs referenced back in this checklist/report

## Reporting / Closeout

[x] Update this checklist after every live wave
[x] Save run checkpoint after every meaningful flow cluster
[x] Save report summary after every meaningful flow cluster
[ ] Produce final proof matrix covering SQLite, queue, Supabase, storage, receiver UI, and log review for each verified lane
[ ] Document any residual external blockers explicitly if something cannot be proven in the current environment
