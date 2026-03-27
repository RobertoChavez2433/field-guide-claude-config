# Delete Flow Fix — Dependency Graph Analysis

**Generated:** 2026-03-26 Session 657
**Source:** Exploration wave (5 agents) + CodeMunch symbol tracing

## Requirements (from S09 investigation + user-approved decisions)

1. **Wire up Path C**: Replace `RemovalDialog` with `ProjectDeleteSheet` bottom sheet, showing transparent delete options (local-only / local+cloud / cloud)
2. **Confirmation**: "Are you sure? This will delete all project data" for database deletes
3. **Role gating**: Admin=any project, Engineer=own projects only, Inspector=cannot delete projects (can only remove from device)
4. **Supabase cascade trigger**: Setting `deleted_at` on project cascades to all 14 child tables
5. **RLS fix**: Inspector entry deletion requires `created_by_user_id = auth.uid()` server-side
6. **Reappearance fix**: Locally-removed project shows in "Not Downloaded" tab

## Direct Changes

### 1. UI Wiring — Replace RemovalDialog with ProjectDeleteSheet

**File:** `lib/features/projects/presentation/screens/project_list_screen.dart`
- **Method `_showRemovalDialog` (line 537-571)**: REPLACE — show `ProjectDeleteSheet` as modal bottom sheet instead of `RemovalDialog`
- **Method `_buildMyProjectsTab` (line 432)**: UPDATE — `onRemove` callback becomes role-aware
- **Method `_buildCompanyTab` (line 491-493)**: UPDATE — unify delete flow for local Company tab entries
- **Method `_handleRemoteDelete` (line 228-296)**: KEEP for remote-only entries, but add cascade via provider
- **New method `_handleCascadeDelete`**: Call `ProjectProvider.deleteProject()` for cloud delete + local cleanup

**File:** `lib/features/projects/presentation/widgets/project_delete_sheet.dart` (line 1-153)
- MODIFY — add testing keys, add confirmation step for database deletes

**File:** `lib/features/projects/presentation/widgets/widgets.dart` (barrel)
- ADD export: `project_delete_sheet.dart`

**File:** `lib/shared/testing_keys/projects_keys.dart`
- ADD keys for delete sheet: `projectDeleteSheet`, `projectDeleteSheetRemoveCheckbox`, `projectDeleteSheetDatabaseCheckbox`, `projectDeleteSheetConfirmButton`

### 2. fetchRemoteProjects Reappearance Fix

**File:** `lib/features/projects/data/services/project_lifecycle_service.dart`
- **Method `removeFromDevice` (line 75-251)**: MODIFY — preserve `projects` row during removal. Only delete children + `synced_projects`. Do NOT hard-delete the project row (Step 7, line 232).

**Root cause:** `removeFromDevice()` hard-deletes the `projects` row AND `synced_projects`. Then `fetchRemoteProjects()` reads from local `projects` table — deleted row = invisible. Incremental sync won't re-pull because `updated_at` cursor hasn't advanced.

**Fix:** Keep the project metadata row. Only delete `synced_projects` (unenroll). The project row stays in SQLite with all its metadata, allowing `fetchRemoteProjects()` to find it as "unenrolled" (available for re-download).

### 3. Supabase Cascade Trigger

**File:** NEW `supabase/migrations/YYYYMMDD_cascade_soft_delete_trigger.sql`
- CREATE FUNCTION `cascade_project_soft_delete()` — AFTER UPDATE trigger on `projects`
- Fires when `deleted_at` transitions NULL → non-NULL
- Cascades to 14 child tables:
  - Direct (9): locations, contractors, daily_entries, bid_items, personnel_types, photos, form_responses, todo_items, calculation_history
  - Indirect via contractors (1): equipment
  - Indirect via daily_entries (4): entry_contractors, entry_equipment, entry_personnel_counts, entry_quantities
- Sets `deleted_at = NEW.deleted_at`, `updated_at = NEW.updated_at` (let `stamp_deleted_by` handle `deleted_by`)
- Only updates rows WHERE `deleted_at IS NULL` (skip already-deleted)

### 4. daily_entries RLS Fix

**File:** NEW `supabase/migrations/YYYYMMDD_tighten_daily_entries_rls.sql`
- DROP POLICY `company_daily_entries_delete`
- CREATE POLICY with: company scope AND (`created_by_user_id = auth.uid()` OR `is_admin_or_engineer()`)
- Also fix `todo_items` DELETE policy (same vulnerability)

## Dependent Files (callers/consumers)

| File | Reason |
|------|--------|
| `lib/features/projects/presentation/providers/project_provider.dart` | `deleteProject()` at line 491 — already wired, just needs call site |
| `lib/features/auth/presentation/providers/auth_provider.dart` | `canDeleteProject()` at line 210 — used for UI gating |
| `lib/features/projects/data/services/project_lifecycle_service.dart` | `canDeleteFromDatabase()` at line 285 — used by sheet |
| `lib/services/soft_delete_service.dart` | `cascadeSoftDeleteProject()` at line 50 — called by provider |
| `lib/features/sync/engine/sync_engine.dart` | `_createDeletionNotification()` at line 1858 — cascade will trigger per-child notifications |
| `lib/core/driver/driver_server.dart` | `_handleRemoveFromDevice()` at line 1100 — uses lifecycle service |

## Test Files

| File | Purpose |
|------|--------|
| `test/features/projects/presentation/providers/project_provider_tabs_test.dart` | Provider tests — verify deleteProject |
| `test/features/projects/presentation/widgets/removal_dialog_test.dart` | Existing dialog tests — may need update |
| NEW `test/features/projects/presentation/widgets/project_delete_sheet_test.dart` | Sheet widget tests |
| NEW `test/services/soft_delete_service_test.dart` | Cascade behavior tests |

## Dead Code to Clean Up

- `lib/features/projects/presentation/widgets/removal_dialog.dart` — KEEP but reduce usage (still used for quick device-only removal by inspectors)
- `RemovalChoice` enum — KEEP (still used by inspector flow)

## Data Flow Diagram

```
User taps delete icon on project card
  │
  ├── Inspector? → RemovalDialog (device-only, no change)
  │
  └── Admin/Engineer? → ProjectDeleteSheet (bottom sheet)
        │
        ├── "Remove from device" only
        │     └── ProjectLifecycleService.removeFromDevice()
        │           └── Preserves projects row (FIX)
        │           └── Deletes children + synced_projects
        │           └── fetchRemoteProjects() → project reappears
        │
        └── "Delete from database" (+ auto-check remove)
              └── Confirmation dialog: "Are you sure?"
              │
              ├── Local project → ProjectProvider.deleteProject()
              │     └── SoftDeleteService.cascadeSoftDeleteProject()
              │     └── change_log entries → sync push → Supabase
              │     └── Supabase trigger fires → cascade to 14 children
              │
              └── Remote-only → ProjectLifecycleService.deleteFromSupabase()
                    └── admin_soft_delete_project RPC
                    └── Supabase trigger fires → cascade to 14 children
```

## Blast Radius Summary

| Category | Count |
|----------|-------|
| Direct changes | 7 files (3 Dart, 2 SQL, 1 barrel, 1 testing keys) |
| Dependent files | 6 files |
| Test files | 2 existing + 2 new |
| Dead code cleanup | 0 (RemovalDialog kept for inspector flow) |
