---
name: Delete Flow Fix — S09 Critical Findings
description: Complete analysis of project delete flow gaps found during sync verification S09. Dead code paths, missing UI wiring, Supabase cascade gap, RLS security issue. User-approved 5-fix plan ready for /writing-plans.
type: project
---

## Context
During sync verification S09 (Delete Cascade), discovered that the "Delete from Device" UI action only removes data locally — no cloud propagation. The cascade soft-delete code path exists but is dead code with no UI call site.

**Why:** The delete flow was partially implemented across 3 separate paths but never fully connected. Path C (the cascade path) was built but the widget (`ProjectDeleteSheet`) was never wired into `project_list_screen.dart`.

**How to apply:** When working on delete-related features, this is THE reference for the current state. All 5 fixes must be implemented together. Start with `/writing-plans` using this context + a second exploration wave.

## Three Code Paths

### Path A: "Delete from Device" (WORKING)
- **Service**: `ProjectLifecycleService.removeFromDevice()`
- **UI**: `RemovalDialog` → "Delete from Device" option
- **Behavior**: Hard-deletes all local SQLite data in a transaction. Suppresses change_log triggers via `sync_control.pulling='1'`. Does NOT touch Supabase.
- **Bug**: After removal, `fetchRemoteProjects` returns `available (unenrolled)=0` — project doesn't reappear as downloadable (BUG-S09-2).

### Path B: "Admin Remote Delete" (WORKING, limited)
- **Service**: `ProjectLifecycleService.deleteFromSupabase()`
- **UI**: Company tab, remote-only projects, admin-only
- **Behavior**: Calls Supabase RPC `admin_soft_delete_project()` — sets `deleted_at` on project row ONLY. No child cascade.

### Path C: "Cascade Soft-Delete + Sync" (DEAD CODE)
- **Service**: `SoftDeleteService.cascadeSoftDeleteProject()`
- **Provider**: `ProjectProvider.deleteProject()` — **ZERO call sites**
- **Widget**: `ProjectDeleteSheet` (`project_delete_sheet.dart`) — **NEVER instantiated**
- **Behavior**: Soft-deletes project + ALL 14 child tables locally. Writes change_log entries. Sync pushes to Supabase. THIS IS THE CORRECT PATH but it's unreachable from UI.

## User-Approved Fixes (5 items)

1. **Wire up Path C** with transparent delete options:
   - Show user exactly what will be deleted (local only, local+cloud)
   - Use `ProjectDeleteSheet` or similar — connect to `ProjectProvider.deleteProject()`
   - Role gating: Admin=any project, Engineer=own only, Inspector=cannot delete from cloud

2. **Confirmation dialog**: "Are you sure? This will delete all project data"

3. **Supabase cascade trigger**: When `deleted_at` is set on `projects`, immediately cascade to all 14 child tables:
   - locations, contractors, equipment, bid_items, personnel_types, project_assignments
   - daily_entries, entry_contractors, entry_equipment, entry_personnel_counts, entry_quantities
   - photos, form_responses, inspector_forms, todo_items, calculation_history

4. **Fix daily_entries RLS**: Add `created_by_user_id = auth.uid()` to DELETE/UPDATE policy for inspectors (SECURITY-S09-1)

5. **Fix fetchRemoteProjects**: Locally-removed projects should reappear in "Not Downloaded" tab

## Key Files
- `lib/features/projects/presentation/screens/project_list_screen.dart` — UI entry point, wiring needed
- `lib/features/projects/presentation/widgets/removal_dialog.dart` — current dialog (Path A only)
- `lib/features/projects/presentation/widgets/project_delete_sheet.dart` — DEAD CODE (Path C UI)
- `lib/features/projects/data/services/project_lifecycle_service.dart` — removeFromDevice, deleteFromSupabase
- `lib/services/soft_delete_service.dart` — cascadeSoftDeleteProject (the correct cascade)
- `lib/features/projects/presentation/providers/project_provider.dart` — deleteProject (no call site)
- `supabase/migrations/20260317100001_admin_soft_delete_rpc.sql` — admin_soft_delete_project RPC
- `supabase/migrations/20260304000000_soft_delete_columns.sql` — purge_soft_deleted_records
- `supabase/migrations/20260313100000_sync_hardening_triggers.sql` — stamp_deleted_by trigger

## Role Matrix
| Action | Admin | Engineer | Inspector |
|---|---|---|---|
| Remove from device (local) | ✅ | ✅ | ✅ |
| Delete from cloud (cascade) | ✅ any project | ✅ own projects (`created_by_user_id == self`) | ❌ |
| Delete entries | ✅ any | ✅ any | ✅ own only (needs RLS fix) |

## Security Finding
`daily_entries` RLS DELETE/UPDATE policy (`multi_tenant_foundation` migration) only checks company membership via `NOT is_viewer()`. No `created_by_user_id` check. Inspector can delete ANY company entry via direct Supabase API. UI-only guard (`canEditEntry`) is insufficient.

## Test Evidence
- Test results: `.claude/test_results/2026-03-26_12-27/report.md`
- Checkpoint: `.claude/test_results/2026-03-26_12-27/checkpoint.json`
- Run tag: `2mthw`, S09=FAIL
