# Session State

**Last Updated**: 2026-03-27 | **Session**: 661

## Current Phase
- **Phase**: S09 PASS, S10 FAIL (BUG-S01-2). Delete cascade working end-to-end. Assignment unassignment broken.
- **Status**: 6 fixes deployed (RPC wiring, RLS policies, sync engine). Supabase migrations pushed. Not committed yet.

## HOT CONTEXT - Resume Here

### What Was Done This Session (661)

1. **S09 Delete Cascade — PASS** after 6 fixes:
   - **`is_approved_engineer()` helper** — missing Supabase function referenced by RPC
   - **`ProjectProvider.deleteProject()` calls RPC** — was only doing local cascade, never calling Supabase `admin_soft_delete_project`
   - **`company_projects_select` RLS** — inspector couldn't see soft-deleted projects (assignment also cascade-deleted → project invisible)
   - **`see_assignments` RLS** — removed `deleted_at IS NULL` so sync can pull assignment tombstones
   - **`_reconcileSyncedProjects()`** — added `AND deleted_at IS NULL` to stop re-enrolling soft-deleted assignments
   - **Orphan cleaner** — added `AND deleted_at IS NULL` to evict soft-deleted projects from `synced_projects`

2. **S10 Unassignment + Cleanup — FAIL (BUG-S01-2)**:
   - Assignment toggle in `AssignmentsStep` unchecks checkbox visually but **doesn't persist soft-delete to SQLite or create change_log entry**
   - Supabase assignment row unchanged (same `updated_at` from yesterday)
   - Pre-existing bug from original `2mthw` run — not a regression

3. **Supabase migrations pushed**:
   - `20260327200000_add_is_approved_engineer_helper.sql`
   - `20260327200001_fix_rls_deletion_propagation.sql`
   - `20260327200002_temp_restore_test_project.sql` (test data restore, can be cleaned up)

### What Needs to Happen Next

1. **Fix BUG-S01-2**: AssignmentsStep toggle doesn't persist unassignment
   - Investigate `AssignmentsStep` widget → what happens when checkbox is toggled?
   - The save button likely doesn't call soft-delete on removed assignments
   - Need to trace: toggle → save → what writes to SQLite/change_log
   - Key files: `lib/features/projects/presentation/widgets/assignments_step.dart`, assignment provider

2. **Re-run S10** after fixing BUG-S01-2

3. **Commit** all changes (massive — see uncommitted changes below)

4. **PDF extraction still freezing** at "finding table structure"

### Uncommitted Changes

From this session (S661 — delete cascade + sync fixes):
- `lib/features/projects/presentation/providers/project_provider.dart` — added Supabase RPC call before local cascade
- `lib/features/sync/engine/sync_engine.dart` — `_reconcileSyncedProjects()` filters `deleted_at IS NULL`, orphan cleaner checks `deleted_at IS NULL`
- `supabase/migrations/20260327200000_add_is_approved_engineer_helper.sql`
- `supabase/migrations/20260327200001_fix_rls_deletion_propagation.sql`
- `supabase/migrations/20260327200002_temp_restore_test_project.sql`

From S660 (permission fix + seeding):
- `lib/main.dart`, `lib/main_driver.dart` — MANAGE_EXTERNAL_STORAGE removal
- `tools/seed-springfield.mjs`, `tools/assign-springfield.mjs`

From S659 (PDF extraction fix):
- `lib/features/pdf/presentation/helpers/pdf_import_helper.dart`, `mp_import_helper.dart`

From S658 (delete flow + 0582B/IDR):
- 4 cascade migrations, lifecycle service, delete sheet, project list screen, auth provider
- 0582B calculator, HMA keys, proctor/quick test content, hub screen, IDR template
- 6 test files

From prior sessions:
- 12 ValueKey scroll fixes, start-driver.ps1, driver_server.dart

## Blockers

### BLOCKER-34: Item 38 — Superscript `th` → `"` (Tesseract limitation)
**Status**: OPEN (parked, cosmetic)

### BLOCKER-36: Item 130 — Whitewash destroys `y` descender
**Status**: OPEN (parked, cosmetic)

### BLOCKER-28: SQLite Encryption (sqlcipher)
**Status**: OPEN — production readiness blocker

### BLOCKER-23: Flutter Keys Not Propagating to Android resource-id
**Status**: OPEN — MEDIUM

## Recent Sessions

### Session 661 (2026-03-27)
**Work**: Re-ran S09 and S10 sync verification. Fixed 6 bugs blocking delete cascade propagation: missing `is_approved_engineer()` helper, `deleteProject()` not calling Supabase RPC, two RLS policies hiding tombstones from inspectors, `_reconcileSyncedProjects()` re-enrolling deleted assignments, orphan cleaner not checking `deleted_at`. S09 now PASS. S10 FAIL on pre-existing BUG-S01-2 (assignment toggle doesn't persist).
**Decisions**: RLS `see_assignments` policy had `deleted_at IS NULL` removed entirely — inspectors can now see their own soft-deleted assignments for sync propagation. Orphan cleaner auto-evicts soft-deleted projects within 2 sync cycles.
**Next**: Fix BUG-S01-2 → re-run S10 → commit.

### Session 660 (2026-03-27)
**Work**: Seeded Springfield project with 131 bid items + M&P from source PDFs. Fixed permission-every-launch bug (MANAGE_EXTERNAL_STORAGE + FilePicker). Created project_assignment for sync enrollment. APK v0.9.0-beta.660.
**Decisions**: Use OTP auth flow for seeding (enforce_created_by requires auth.uid()). project_assignments required for sync enrollment. Removed MANAGE_EXTERNAL_STORAGE — use app-specific dirs on mobile.
**Next**: Verify sync pulls bid items → investigate PDF freeze → commit.

### Session 659 (2026-03-27)
**Work**: Diagnosed + fixed PDF extraction wiring bug. pdfrx fails silently in background isolates. Rewired both helpers to main-thread execution with progress dialog. APK v0.9.0-beta.659 released.
**Decisions**: Bypass background isolate path entirely. Run pipeline on main thread with blocking progress dialog. Background isolate architecture can be revisited later (render on main, OCR in worker).
**Next**: User testing → commit → S09-S10 re-run.

### Session 658 (2026-03-27)
**Work**: /implement delete flow fix (5 phases) + /implement 0582B+IDR (7 phases). Post-implement review sweeps fixed 3 HIGHs. APK v0.9.0-beta.658 released.
**Decisions**: Extended admin_soft_delete_project RPC for engineers (own projects only). Added auth.uid() guard to cascade trigger. calculation_history added to device removal.
**Next**: Commit → re-run S09-S10 → S03/S04.

## Active Debug Session

None active.

## Test Results

### Flutter Unit Tests
- **Full suite**: 3141/3141 PASSING (S658 baseline, not re-run this session)
- **PDF tests**: 911/911 PASSING (verified after fix)
- **Analyze**: PASSING (0 errors, 115 info)

### Sync Verification (Current Run — tag `2mthw`)
- **S01**: PASS — 7 tables, 16 records synced
- **S02**: PASS — Entry + contractors + quantity synced. BUG-S02-1: personnel/equipment not persisted.
- **S03**: SKIP — inject-photo-direct HTTP 500 (driver bug)
- **S04**: SKIP — No inspector_forms in database
- **S05**: PASS — Todo synced clean
- **S06**: PASS — HMA calc 58 tons synced clean
- **S07**: PASS — 5/8 entities updated via UI, synced, verified on inspector
- **S08**: PASS — PDF exported (436KB), ADB pulled
- **S09**: PASS — RPC + cascade trigger + RLS fix + orphan cleaner. Inspector pulls 21 tombstones, auto-evicts in 2 cycles.
- **S10**: FAIL — BUG-S01-2: Assignment toggle doesn't persist soft-delete. Pre-existing.

## Reference
- **Delete Flow Fix Plan (IMPLEMENTED)**: `.claude/plans/2026-03-26-delete-flow-fix.md`
- **0582B+IDR Plan (IMPLEMENTED)**: `.claude/plans/2026-03-26-0582b-fixes-and-idr-template.md`
- **Schema Divergence Fix Plan (APPROVED)**: `.claude/plans/2026-03-26-schema-divergence-fix.md`
- **Claude-Driven Sync Plan (APPROVED)**: `.claude/plans/2026-03-25-sync-verification-claude-driven.md`
- **Test Registry**: `.claude/test-flows/registry.md`
- **Defects**: `.claude/defects/_defects-{feature}.md`
- **S09/S10 Test Results**: `.claude/test_results/2026-03-27_S09-S10/`
