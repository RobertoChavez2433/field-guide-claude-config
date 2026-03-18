# Session State

**Last Updated**: 2026-03-18 | **Session**: 588

## Current Phase
- **Phase**: Admin dashboard fixed, sync phantom-pending fixed, project state UI spec complete + reviewed.
- **Status**: 3 bugs fixed (RPC type mismatch, sync phantom pending, orphan scanner). Project State UI spec brainstormed, reviewed, and finalized. Not yet committed. Spec ready for /writing-plans.

## HOT CONTEXT - Resume Here

### What Was Done This Session (588)

1. **Admin Dashboard load failure** — surfaced real error (`varchar`/`text` mismatch in `get_pending_requests_with_profiles` RPC). Created + pushed migration `20260318100000_fix_pending_requests_rpc_types.sql` with `::TEXT` casts.
2. **Phantom pending changes after sync** — root cause: `_pushUpsert()` writes back server `updated_at` without suppressing change_log trigger. Fixed by wrapping with `pulling=1` guard (same pattern as `_pushPhotoThreePhase`).
3. **Published debug APK** to GitHub release `debug-admin-dashboard-v0.1.2` (twice — updated with sync fix).
4. **Discovered `OrphanScanner` bug** — `column photos.company_id does not exist` (code 42703). Noted for fix.
5. **Brainstormed + spec'd Project State UI** — full 11-section spec with adversarial review:
   - 3-tab layout: My Projects | Company | Archived
   - `project_assignments` table with RLS, triggers, audit logging
   - Assignment management in project setup wizard
   - Auto-enrollment on assignment + pending notifications queue
   - Scoped SELECT RLS (inspectors see own assignments only)
   - Multi-step removal dialog with sync-first safety

### Key Decisions (S588)
- Assignments are organizational, not access-control boundaries (self-enrollment still allowed)
- Scoped SELECT RLS for assignments (inspectors see own only, admins see all)
- Archived projects respect assignments (only assigned can download)
- Assignments held in-memory during wizard until save (no orphan risk)
- CompanyFilter as Dart enum, not magic strings
- Both timestamp triggers on project_assignments (match existing pattern)
- Delete legacy project_selection_screen.dart with full route audit

### What Needs to Happen Next

1. **Commit current fixes** — RPC type fix migration, sync phantom-pending fix, admin provider changes
2. **Invoke /writing-plans** for project state UI spec → phased implementation plan
3. **Fix OrphanScanner bug** — `photos.company_id` doesn't exist, needs join through daily_entries
4. **Fix `handle_new_user()` trigger** — doesn't populate display_name from auth metadata (admin dashboard shows "Unknown")

### KNOWN PROBLEMS
- **OrphanScanner crash**: `column photos.company_id does not exist` — needs join fix
- **Unknown display name**: `handle_new_user()` trigger only inserts `id`, no `display_name` from metadata
- **Repair migration needed** — remote DB has pre-review SQL; local files corrected post-review

## Blockers

### BLOCKER-22: Location Field Stuck "Loading"
**Status**: FIXED (S587)

### BLOCKER-34: Item 38 — Superscript `th` → `"` (Tesseract limitation)
**Status**: OPEN

### BLOCKER-36: Item 130 — Whitewash destroys `y` descender
**Status**: OPEN

### BLOCKER-28: SQLite Encryption (sqlcipher)
**Status**: OPEN

### BLOCKER-23: Flutter Keys Not Propagating to Android resource-id
**Status**: OPEN — MEDIUM

## Recent Sessions

### Session 588 (2026-03-18)
**Work**: Fixed admin dashboard RPC type mismatch + sync phantom-pending bug. Brainstormed + spec'd Project State UI (3-tab layout, project_assignments table, assignment wizard, auto-enrollment). Adversarial review complete (6 MUST-FIX resolved, 8 SHOULD-CONSIDER decided). Debug APK on GitHub.
**Decisions**: Assignments = organizational not access-control. Scoped SELECT RLS. Archived respects assignments. In-memory wizard state.
**Next**: Commit. /writing-plans for project state UI. Fix OrphanScanner + display_name bugs.

### Session 587 (2026-03-18)
**Work**: Device testing bug fixes (P1 location, P2 weather, P4/P8 delete-sync, P6/P7 admin offline). CRITICAL: found and fixed sync permanent offline trap (_isOnline never recovers). Debug APK v0.1.2-debug-s587 on GitHub.
**Decisions**: Tombstone check via change_log not separate table. P3/P5 are network, not code.
**Next**: Device test new APK. Commit.

### Session 586 (2026-03-18)
**Work**: /implement project management E2E plan (11 phases, 6 orchestrator launches, 0 handoffs). 30 files modified, 3032 tests passing. All reviews PASS. Bug found: code.contains('503') masks 23503 FK errors.
**Decisions**: Batched final 4 phases into one orchestrator launch. Repair migration deferred as tech debt.
**Next**: Commit. Push Supabase migrations. Build + device test. Fix BLOCKER-22. Fix 503 bug.

### Session 585 (2026-03-17)
**Work**: Implemented sync hardening plan (4 orchestrator launches, 2962 tests passing). Device testing found Import broken (missing Provider). Full project lifecycle audit (13 issues). Brainstormed + spec'd + planned project management E2E fix (11 phases). Committed 7 app commits + 2 config commits.
**Decisions**: Metadata auto-sync only (no auto-enroll). Keep canWrite (add new methods alongside). SECURITY DEFINER RPC for remote delete. Remove viewer role. Available Projects from local SQLite.
**Next**: /implement project management E2E plan. Build + device test. Fix BLOCKER-22.

### Session 584 (2026-03-17)
**Work**: Systematic debugging for BLOCKER-38 + BLOCKER-39 + proactive sync audit. Launched 2 deep research agents (found 10 additional sync issues). /writing-plans produced 6-phase plan. Adversarial review (code + security) found 2+2 CRITICAL, 5+4 HIGH findings — all fixed inline. Plan ready for /implement.
**Decisions**: ConflictResolver keeps Future<ConflictWinner> (query-based conflict count). Offline removal guard at service + UI layers. Migration uses DROP POLICY IF EXISTS defensively. fkColumnMap corrected for EntryPersonnelCountsAdapter.
**Next**: Commit S583 bugfixes. /implement sync hardening plan. Test on device.

## Active Plans

### Project State UI & Assignments — SPEC COMPLETE, NEEDS PLAN
- **Spec**: `.claude/specs/2026-03-18-project-state-ui-spec.md`
- **Review**: `.claude/adversarial_reviews/2026-03-18-project-state-ui/review.md`
- **Status**: Spec reviewed and finalized. Ready for /writing-plans.

### Project Management E2E Fix — IMPLEMENTED (Session 586)
- **Spec**: `.claude/specs/2026-03-17-project-management-e2e-spec.md`
- **Plan**: `.claude/plans/2026-03-17-project-management-e2e.md`
- **Status**: All 11 phases implemented. 3032 tests passing. Not yet committed. Needs device test.

### Sync Hardening & RLS Enforcement — IMPLEMENTED + COMMITTED (Session 585)
- **Plan**: `.claude/plans/2026-03-17-sync-hardening-and-rls.md`
- **Status**: All 6 phases implemented. 2962 tests passing. Committed.

## Reference
- **Project State UI Spec**: `.claude/specs/2026-03-18-project-state-ui-spec.md`
- **Project Management E2E Spec**: `.claude/specs/2026-03-17-project-management-e2e-spec.md`
- **Project Lifecycle Spec**: `.claude/specs/2026-03-16-project-lifecycle-spec.md`
- **Pipeline UX Spec**: `.claude/specs/2026-03-15-pipeline-ux-overhaul-spec.md`
- **Defects**: `.claude/defects/_defects-pdf.md`, `_defects-sync.md`, `_defects-entries.md`
- **Debug build tag**: `debug-admin-dashboard-v0.1.2` on GitHub releases
- **Release build tag**: `v0.1.1` on GitHub releases
