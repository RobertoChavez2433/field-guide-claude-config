# Session State

**Last Updated**: 2026-03-04 | **Session**: 492

## Current Phase
- **Phase**: App Lifecycle Safety + Soft-Delete Fixes
- **Status**: Pushed repos, deployed Supabase migrations, implemented app lifecycle plan (schema verifier, version tracking, upgrade re-auth), fixed trash count refresh, fixed Gradle lint lock. v0.76.0 released.

## HOT CONTEXT - Resume Here

### What Was Done This Session (492)

1. **Pushed both repos** — `fix/sync-dns-resilience` (app) + `master` (config)
2. **Deployed Supabase migrations** — `20260304000000_soft_delete_columns.sql` + hotfix `20260304100000_soft_delete_missing_tables.sql`
3. **Fixed missing soft-delete columns** — `entry_contractors` + `entry_personnel_counts` were missing from SQLite migration v28, Supabase migration, and purge function. Added v29 migration.
4. **Brainstormed app lifecycle design** — 4 states defined (background resume, cold start, upgrade, fresh install). Decisions: auto-repair, cold start → dashboard, upgrade → re-auth, schema verifier.
5. **Implemented app lifecycle plan via `/implement`** — All 4 phases + 6 quality gates passed:
   - Phase 0: Schema verifier (25 tables, ~14ms, self-healing)
   - Phase 1: App version tracking (package_info_plus)
   - Phase 2: Removed route restore (cold starts → dashboard)
   - Phase 3: Upgrade re-auth (signOutLocally)
6. **Fixed trash count not refreshing** — Settings screen now reloads count when returning from trash
7. **Bumped version to 0.76.0** — Triggers upgrade detection on existing installs
8. **Fixed Gradle lint lock** — Disabled `checkReleaseBuilds` in build.gradle.kts, builds now ~45s instead of 7min
9. **Released v0.76.0** — https://github.com/RobertoChavez2433/construction-inspector-tracking-app/releases/tag/v0.76.0

### What Needs to Happen Next

1. **VERIFY: Trash "Empty All" syncs deletions to Supabase** — User reported 426 items still showing after emptying trash. The `purgeExpiredRecords()` does local SQLite DELETE but may not be pushing hard-deletes to Supabase. The sync layer's `_pushPendingChanges()` was supposed to handle this (session 491 Phase 2 — sync layer skip deleted, edit-wins). VERIFY that the push path actually syncs `deleted_at` timestamps to Supabase before the purge hard-deletes them. If the purge runs before push, the records vanish locally and Supabase never learns they were deleted → next pull resurrects them.
2. **Dry run `/test --smoke`** — Connect device, validate smoke flows
3. **Fix BLOCKER-24** — add UNIQUE index to SQLite projects table
4. **Fix BLOCKER-22** — location field stuck loading

## Blockers

### BLOCKER-26: Trash Purge May Not Sync to Supabase Before Hard Delete
**Status**: OPEN — NEEDS VERIFICATION (not confirmed as bug yet)
**Symptom**: User emptied trash (426 items), count badge didn't update (fixed in session 492), but need to verify Supabase actually received the deletions.
**Theory**: `purgeExpiredRecords(retentionDays: 0)` does hard DELETE locally. If the `deleted_at` timestamps weren't pushed to Supabase BEFORE the purge, Supabase still has the records as non-deleted → next sync pull resurrects them.
**Verification needed**: Check if sync push includes `deleted_at`/`deleted_by` columns. Check the sync flow: soft-delete → push `deleted_at` to Supabase → THEN purge locally. The post-sync purge in `syncAll()` (line 461-473) runs AFTER push, which is correct for the 30-day auto-purge. But "Empty Trash" calls `purgeExpiredRecords(retentionDays: 0)` directly WITHOUT syncing first.
**Files**: `lib/services/soft_delete_service.dart:291-329`, `lib/services/sync_service.dart:440-473`, `lib/features/settings/presentation/screens/trash_screen.dart:356-368`

### BLOCKER-24: SQLite Missing UNIQUE Constraint on Project Number — Sync Race
**Status**: OPEN — HIGH PRIORITY
**Symptom**: User creates project, sees "already exists" on save, or project appears duplicated.
**Fix**: Add `CREATE UNIQUE INDEX idx_project_number_company ON projects(company_id, project_number)` to SQLite.
**Files**: `lib/core/database/schema/core_tables.dart`, `lib/core/database/database_service.dart`

### BLOCKER-22: Location Field Stuck "Loading" on New Entry Screen
**Status**: OPEN — HIGH PRIORITY
**Symptom**: Location field shows perpetual "loading" spinner when no location exists for project.
**Root cause**: NOT YET INVESTIGATED.

### BLOCKER-23: Flutter Keys Not Propagating to Android resource-id
**Status**: OPEN — MEDIUM (mitigated by content-desc/text fallback in test skill)

### BLOCKER-25: Nested Task Tool Calls Don't Work in Subagents
**Status**: OPEN — ARCHITECTURAL LIMITATION (mitigated by top-level orchestration)

### BLOCKER-10: Fixture Generator Requires SPRINGFIELD_PDF Runtime Define
**Status**: OPEN (PDF scope only).

## Recent Sessions

### Session 492 (2026-03-04)
**Work**: Pushed repos + deployed Supabase migrations. Fixed 2 missing soft-delete tables (entry_contractors, entry_personnel_counts) — DB v29. Brainstormed + implemented app lifecycle safety (schema verifier, version tracking, upgrade re-auth, route restore removal). Fixed trash count refresh. Bumped to v0.76.0. Fixed Gradle lint lock (45s builds). Released v0.76.0.
**Decisions**: Schema verifier on every startup (self-healing). Cold start → dashboard. Upgrade → re-auth. Disable Gradle lint on release builds. Version must be bumped for upgrade detection to trigger.
**Next**: Verify trash purge syncs to Supabase (BLOCKER-26), smoke test, fix BLOCKER-24, fix BLOCKER-22.

### Session 491 (2026-03-04)
**Work**: Context-efficient test skill. Investigated + brainstormed + implemented sync-aware soft-delete system (5 phases, 24 files, all quality gates). Committed 6 logical app commits + 2 config commits.
**Decisions**: Soft-delete + 30-day purge. Edit-wins conflict resolution. Trash screen in Settings. RLS SELECT policies NOT modified. DB version 27→28.
**Next**: Push repos, deploy migration, smoke test, fix BLOCKER-24, fix BLOCKER-22.

### Session 490 (2026-03-03)
**Work**: Brainstormed + implemented testing system overhaul. 30 flows, 12 journeys, 4 tiers, flag-based CLI.
**Decisions**: Replace Patrol entirely. 4 tiers. Flag style CLI. Top-level orchestration. Haiku for wave agents.
**Next**: Dry run `/test --smoke`, fix sync defects, fix BLOCKER-24.

### Session 489 (2026-03-03)
**Work**: Validated test orchestration delegation. Confirmed BLOCKER-25 (nested Task calls fail).
**Decisions**: Top-level orchestration only. 1 flow per agent. Haiku for wave agents.
**Next**: Testing system overhaul brainstorm, fix sync defects, fix BLOCKER-24.

### Session 488 (2026-03-03)
**Work**: Full `/test --all` run (3/5 PASS, 1 FAIL). Redesigned orchestrator + wave agent. Discovered BLOCKER-24.
**Decisions**: Orchestrator gets Task tool. Wave agents get Write/Edit + mandatory logcat.
**Next**: CLI restart, retry `/test --all`, fix BLOCKER-24, fix BLOCKER-22.

## Active Plans

### App Lifecycle Safety — IMPLEMENTED (Session 492)
- **Design**: `.claude/plans/2026-03-04-app-lifecycle-design.md`
- **Status**: All 4 phases implemented, all 6 quality gates passed. Released as v0.76.0.
- **Key files**: `lib/core/database/schema_verifier.dart`, `lib/main.dart`

### Sync-Aware Deletion System — IMPLEMENTED (Session 491)
- **Design**: `.claude/plans/2026-03-04-sync-aware-deletion-system.md`
- **Status**: Implemented + deployed. BLOCKER-26 open re: trash purge sync verification.
- **Key files**: `lib/services/soft_delete_service.dart`, `lib/features/settings/presentation/screens/trash_screen.dart`

### Testing System Overhaul — IMPLEMENTED (Session 490)
- **Design**: `.claude/plans/2026-03-03-testing-system-overhaul.md`
- **Status**: Phases 0-2 + 4 implemented. Phases 3 + 5 deferred (require device).

### Review & Submit Flow + Auth — IMPLEMENTED (Session 484)
- **Plan**: `.claude/plans/2026-03-03-review-submit-flow-and-auth.md`
- **Status**: All 5 phases implemented + reviewed + fixed. Committed.

### Project-Based Multi-Tenant Architecture — DEPLOYED (Session 453)
- **PRD**: `.claude/prds/2026-02-21-project-based-architecture-prd.md`

## Reference
- **Improvements**: `.claude/improvements.md`
- **Lifecycle Plan**: `.claude/plans/2026-03-04-app-lifecycle-design.md`
- **Deletion System Plan**: `.claude/plans/2026-03-04-sync-aware-deletion-system.md`
- **Testing Overhaul Plan**: `.claude/plans/2026-03-03-testing-system-overhaul.md`
- **Archive**: `.claude/logs/state-archive.md`
- **Defects**: `.claude/defects/_defects-database.md`, `.claude/defects/_defects-toolbox.md`, `.claude/defects/_defects-pdf.md`, `.claude/defects/_defects-sync.md`, `.claude/defects/_defects-forms.md`, `.claude/defects/_defects-auth.md`, `.claude/defects/_defects-projects.md`, `.claude/defects/_defects-entries.md`
