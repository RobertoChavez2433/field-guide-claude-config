# Sync Issue Verification Tracker

Date: 2026-04-05
Branch: `sync-engine-refactor`
Author: Codex

## Goal

Verify every open sync-related GitHub issue against the current branch before
doing more fixes, then work only from issues that are still real.

## Current Verdict

### Verified Fixed, Already Closed

- [x] `#204` Inspector full sync fails integrity verification and clears cursors
  - Verified by `.claude/test-results/2026-04-05_2300_codex_sync-reverify/verification-summary.md`
  - Current evidence: tolerated drift no longer resets cursors; no new cursor poisoning observed.
  - GitHub status: closed on 2026-04-05

- [x] `#205` Realtime sync hint RPC registration fails because required Supabase functions are missing
  - Verified fixed for registration + teardown semantics by the same reverify summary.
  - Current evidence: live private-channel subscription succeeds; teardown/rebind works after sign-out ordering fix.
  - GitHub status: closed on 2026-04-05

- [x] `#224` Android resume quick sync does not catch up remote entry changes
  - Verified fixed at the sync/pull layer by the same reverify summary.
  - Important nuance: the already-open report UI still stayed stale until one route refresh, so this issue overlaps with `#212`.
  - GitHub status: closed on 2026-04-05

- [x] `#167` `verify-sync.ps1` cannot verify Supabase state because loaded API key is invalid
  - Verified fixed on 2026-04-05 by running `pwsh -File tools/verify-sync.ps1 -Table projects -CountOnly`
  - Current evidence: script now returns `projects count: 9` against real Supabase credentials.
  - Root cause `H-167-A` confirmed: PowerShell/PostgREST count path was broken by `HEAD + Range: 0-0`.
  - Root cause `H-167-B` confirmed: PowerShell's default browser-like user agent is rejected by Supabase secret keys unless overridden.
  - GitHub status: closed on 2026-04-05

## Verified Fixed, Runtime Reverified

- [x] `#212` Foreground inspector does not auto-catch-up after admin sync
  - Status: runtime reverified fixed on 2026-04-05 using S21 inspector (`4948`)
  - Investigation evidence: initial repro showed the report staying stale after foreground mutation and channel rebind.
  - Root cause `H-212-A` confirmed: the sync layer can catch up, but `EntryEditorScreen` held a stale in-memory entry snapshot and never reloaded after sync completion.
  - Hypothesis `H-212-B`: realtime quick-sync is not always being triggered after foreground remote mutations, especially after rebind, so both transport and UI refresh may be involved.
  - Fix applied: open report screens now listen for completed sync cycles and reload their entry/related providers when a new successful sync snapshot arrives and no local edits are in progress.
  - Verification so far: targeted `dart analyze` clean; `flutter test test/features/entries/presentation/screens/entry_editor_report_test.dart` passed.
  - Runtime evidence: seeded entry `65aa5299-b259-4ba2-8309-4732aba8dfd8` stayed open on `/report/...`; after a server-side activities update plus sync completion, the on-screen Activities text changed from `Codex sync baseline 214446` to `Codex sync updated 215747` without leaving the route.
  - Screenshot evidence: `.claude/test_results/2026-04-05/4948-report-baseline.png`, `.claude/test_results/2026-04-05/4948-report-after-212-sync-complete.png`
  - GitHub status: closed on 2026-04-06

- [x] `#211` Inspector does not show deletion notification banner after synced project removal
  - Status: runtime reverified fixed on 2026-04-05 using S21 inspector (`4948`)
  - Evidence: `ProjectListScreen` renders `DeletionNotificationBanner`, but unassignment only marked `synced_projects.unassigned_at` and never created a `deletion_notifications` row; banner also loaded once and stayed dismissed for the widget lifetime.
  - Root cause `H-211-A` confirmed: project unassignment/removal path did not create a deletion notification.
  - Root cause `H-211-B` confirmed: banner did not refresh after later sync completions and would stay dismissed even when new unseen notifications arrived.
  - Fix applied: `SyncEnrollmentService` now creates a project-level deletion notification on assignment removal; banner now reloads after sync completion and clears dismissal when new unseen notifications exist.
  - Verification so far: targeted `dart analyze` clean; `flutter test test/features/sync/application/sync_enrollment_service_test.dart` passed.
  - Runtime evidence: authenticated admin soft-deleted assignment `8a2590be-da18-46ca-9301-82e867356b56`; inspector sync then showed `deletion_notification_banner`, and the pulled local `project_assignments` row carried `deleted_at` / `deleted_by`.
  - GitHub status: closed on 2026-04-06

- [x] `#206` Inspector report can get stuck on Loading after sync and throws a Null-to-String cast error
  - Status: runtime reverified fixed on 2026-04-05 using S21 inspector (`4948`)
  - Evidence: `Photo.fromMap()` was casting `file_path` to non-null `String`, while synced remote-only photos can legitimately have null/empty `file_path` and only a `remote_path`.
  - Root cause `H-206-A` confirmed: nullable synced photo field was still modeled as non-null and crashed the report route.
  - Fix applied: photo model now accepts nullable `filePath`; thumbnail/detail/gallery/pdf paths now fail soft when no local file exists.
  - Verification so far: targeted `dart analyze` clean; `flutter test test/data/models/photo_test.dart test/services/photo_service_test.dart` passed.
  - Runtime evidence: server photo `ed1f6b3d-f7f8-42f4-bd5a-c4a686ad7706` synced down with `file_path = null` and non-null `remote_path`; the inspector report route remained stable and reopened normally with `report_screen_title` present.
  - GitHub status: closed on 2026-04-06

- [x] `#225` Settings trash count stays stale after deleting trash and syncing
  - Status: runtime reverified fixed on 2026-04-05 using Windows admin (`4949`)
  - Evidence: `SettingsScreen` now awaits return from `/settings/trash` and calls `_loadTrashCount()` on navigation return.
  - Hypothesis `H-225-A` disproved for current source: the stale-count-on-return path appears to have already been patched.
  - Runtime evidence: Settings initially showed `15 items in trash` with badge `15`; after deleting a trash item and returning from Trash, Settings refreshed to `7 items in trash` with badge `7` instead of holding the old count.
  - Screenshot evidence: `.claude/test_results/2026-04-05/4949-settings-trash-check.png`, `.claude/test_results/2026-04-05/4949-settings-after-trash-delete.png`
  - GitHub status: closed on 2026-04-06

- [x] `#164` Startup sync pushes daily entry into Supabase RLS denial
  - Status: code-path audit + runtime reverify indicate fixed on current refactored branch
  - Evidence: issue ref points at removed `sync_orchestrator.dart`, so the issue is partly stale on its face.
  - Hypothesis `H-164-A`: already fixed by refactor plus LWW/skip logic, and only needs live repro to clear.
  - Root cause `H-164-B` confirmed in audit and fixed in code: push eligibility still allowed non-direct records for projects not present in `synced_projects`.
  - Fix applied: `PushHandler` now resolves scoped project ownership and skips non-direct pushes when the owning project is not currently synced.
  - Runtime evidence: after removing project `41088ce9-0eda-4211-b4ea-45c30c99b5a7` from device sync scope, a local dirty entry (`7d5a0dec-1ac4-4475-810a-9ca7996f1908`) under that project cleared from local `change_log` during Settings sync and did not appear in Supabase. No issue-specific RLS denial was observed on the user-path sync.
  - Follow-up note: a later S21 sync failure was traced to a leftover local test `projects` row (`75ae3283-d4b2-4035-ba2f-7b4adb018199`, description `Out-of-scope local metadata for #164 verification`) that was outside normal issue scope. After removing that artifact, device sync returned to `pendingCount: 0` and `Synced`.
  - GitHub status: closed on 2026-04-06

## Tooling / Tech-Debt Items Touching Sync

### Closed

- [x] `#226` Lint: `no_silent_catch`
  - Status: fixed and closed on 2026-04-06
  - Sync-relevant site: `lib/features/sync/engine/file_sync_handler.dart:183`

- [x] `#227` Lint: `path_traversal_guard`
  - Status: fixed and closed on 2026-04-06
  - Sync-relevant sites are in sync adapter/characterization tests.

- [x] `#228` Lint: `copywith_nullable_sentinel`
  - Status: fixed and closed on 2026-04-06
  - Sync-relevant site: `lib/features/sync/engine/integrity_checker.dart:42`

- [x] `#229` Lint: `require_soft_delete_filter`
  - Status: fixed and closed on 2026-04-06
  - Sync relevance: protects provider/controller query sites from accidentally surfacing soft-deleted synced rows.

## Deferred / Out Of Scope For This Pass

- [ ] `#129` Remote signed URL fallback for synced documents
  - Enhancement, not a current defect. Keep out of the bulletproof defect pass unless requested.

## Remaining Sync Queue

1. No remaining open sync issues from the April 5, 2026 verification pass.
2. Any further sync work should be treated as new defects or new guardrail follow-up, not unresolved backlog from this pass.
