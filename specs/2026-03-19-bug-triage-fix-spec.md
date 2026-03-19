# Bug Triage Fix Spec — 13 Bugs from S591 Device Testing

**Date**: 2026-03-19
**Session**: S592
**Source**: `bugs_report.md` (14 bugs filed, 1 dismissed as non-issue)

## Overview

### Purpose
Fix 13 bugs found during live 2-device testing (S591) spanning sync engine reliability, role-based permissions, state management, UX, and RLS enforcement.

### Scope
**Included**: All 13 bugs (BUG-001 through BUG-015, excluding dismissed BUG-013)
**Excluded**: New features, untested flows from S591, OrphanScanner crash, display_name bug

### Success Criteria
- Inspector cannot create/edit/archive projects (except locations, pay items, contractors, equipment, personnel types)
- Inspector cannot download unassigned projects
- Sync recovers automatically after transient network loss (no restart needed)
- Fresh inspector device receives assignment data on first sync (no deadlock)
- `_selectedProject` is cleared after removeFromDevice
- All existing tests pass + new tests for permission gates
- RLS INSERT policy blocks inspector project creation server-side

### Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Inspector write scope | Entries + locations + pay items + contractors + equipment + personnel types | All field data actions — this is the inspector's job |
| Project management | Admin + engineer only (create, archive, delete, edit details) | Organizational actions, not field work |
| Engineer delete | Allowed | Engineers need full project lifecycle control |
| Sync recovery | Re-check DNS on every refresh + global offline indicator | User shouldn't feel chained to connectivity |
| Enrollment deadlock | `project_assignments` → `ScopeType.direct` | Breaks chicken-and-egg with minimal change |
| Company tab visibility | All projects visible, download restricted to assigned for inspector | Inspector can see project cards but not import unassigned |
| RLS fix | Tighten INSERT policy now | Defense-in-depth, small migration |

---

## Permission Model Changes

### Core Fix: Replace `canWrite` with granular permissions

```
UserRole:
  canWrite          → REMOVE
  canManageProjects → admin, engineer only (create, archive, delete, edit project details)
  canEditFieldData  → all roles (contractors, equipment, personnel types, locations, pay items, entries, photos, todos, forms)
```

### Permission Matrix

| Action | Admin | Engineer | Inspector |
|--------|-------|----------|-----------|
| Create project | Y | Y | N |
| Edit project details | Y | Y | N |
| Archive/activate project | Y | Y | N |
| Delete project | Y | Y | N |
| Add/edit/delete contractors | Y | Y | **Y** |
| Add/edit/delete equipment | Y | Y | **Y** |
| Add/edit/delete personnel types | Y | Y | **Y** |
| Add/edit/delete locations | Y | Y | **Y** |
| Add/edit/delete pay items | Y | Y | **Y** |
| Create/edit daily entries | Y | Y | Y |
| Add/edit photos | Y | Y | Y |
| Create/edit todos | Y | Y | Y |
| Create/edit forms | Y | Y | Y |
| Download assigned projects | Y | Y | Y |
| Download unassigned projects | Y | Y | **N** |
| View all company projects | Y | Y | Y |

### Migration Path for 102 `canWrite` Call Sites

Two categories:
1. **Project management actions** (create, archive, edit project details) → replace with `canManageProjects` — ~15 call sites
2. **Field data actions** (contractors, equipment, personnel types, locations, pay items, entries, photos, todos, forms) → replace with `canEditFieldData` (true for all roles) — ~87 call sites

### Route Guards (BUG-007)

- `/project/new` → redirect if `!canManageProjects`
- `/project/:id/edit` → allow all roles. Inspector gets full access to contractors, locations, pay items tabs. Only the Details tab (project name, dates, etc.) is gated by `canManageProjects`

### Dashboard (BUG-011)

- Contractors card → navigates to `project-edit?tab=2` for **all roles** (field data)
- Locations card → navigates to `project-edit?tab=1` for **all roles** (field data)

### `canEditProject` (BUG-012)

Delete dead code getter entirely. The two new getters replace it.

### `toggleActive` (BUG-009)

Add `canManageProjects` check inside `toggleActive()` method. Archive button gated by `canManageProjects` instead of `canWrite`.

---

## Sync Engine Fixes

### BUG-006: Sticky `_isOnline` Recovery

**Change**: `_refresh()` in `project_list_screen.dart` calls `checkDnsReachability()` before checking `isSupabaseOnline`.

```
Current:  if (orchestrator.isSupabaseOnline) → sync
Fixed:    await orchestrator.checkDnsReachability() → if (orchestrator.isSupabaseOnline) → sync
```

**Global offline indicator**: Add a small connectivity status widget (dot or icon) to the app's scaffold or bottom nav bar. Reads `isSupabaseOnline` from `SyncOrchestrator` via provider. Shows when offline, disappears when online. Not intrusive — just informational.

Also fix `_checkNetwork()` and `_showRemovalDialog` which read the stale flag without refreshing.

### BUG-005: Fresh Inspector Deadlock

**Change**: Set `project_assignments` adapter to `ScopeType.direct` so it always pulls regardless of `synced_projects` state.

Flow after fix:
1. Fresh inspector device — `synced_projects` empty
2. `_pull()` runs → `project_assignments` pulls (direct scope, no skip)
3. `onPullComplete` fires → auto-enrolls assigned projects into `synced_projects`
4. Next sync cycle → `_loadSyncedProjectIds()` returns non-empty → all 15 project-scoped tables pull normally

### BUG-004: No Auto-Reschedule After Retry Exhaustion

**Change**: After `_syncWithRetry()` exhausts 3 attempts, schedule a delayed retry via `Future.delayed` (e.g., 60 seconds) that calls `checkDnsReachability()` and re-attempts if DNS passes. Cap at 1 background retry to avoid infinite loops. The existing `SyncLifecycleManager` app-resume path already handles longer outages.

Changes are already safe in `change_log` (`processed=0`, `markFailed` preserves them). This just closes the gap between "retries exhausted" and "user happens to resume app."

### BUG-002: synced_projects Race Conditions

Two fixes:

1. **`onPullComplete` ordering**: Move the auto-enrollment from a fire-and-forget async callback to an awaited step within the sync cycle itself, after `project_assignments` adapter completes but before `fetchRemoteProjects` reads `synced_projects`. This eliminates the race where `fetchRemoteProjects` reads before enrollment commits.

2. **Orphan cleaner guard**: In `_loadSyncedProjectIds()`, only delete orphan `synced_projects` entries if the `projects` adapter has already run in this cycle. If projects haven't been pulled yet, a "missing" project row may simply be arriving later in the same cycle.

---

## State Management Fix

### BUG-001: Stale `_selectedProject` After removeFromDevice

**Change**: In `_handleRemoveFromDevice` (project_list_screen.dart), after calling `lifecycleService.removeFromDevice()`:

1. Call `projectProvider.clearSelectedProject(projectId)` — clears `_selectedProject` if it matches the removed ID (same pattern as `deleteProject` at provider line 512-514)
2. Call `settingsProvider.clearIfMatches(projectId)` — clears persisted `last_project_<userId>` from SharedPreferences

Both calls already exist in the `deleteProject` path. The fix is adding them to the `removeFromDevice` path.

**Dashboard guard**: Add a null/staleness check in `project_dashboard_screen.dart` — if `selectedProject` is non-null but its ID doesn't exist in `projectProvider.projects`, treat it as null and show the "no project selected" state. Belt-and-suspenders against any other path that forgets to clear.

---

## UX & RLS Fixes

### BUG-003: Tap Targets Too Small (20x20 → 48x48)

**Change**: On the edit and archive `IconButton`s in project cards, replace:
```
constraints: const BoxConstraints()
padding: EdgeInsets.zero
```
with:
```
constraints: const BoxConstraints(minWidth: 48, minHeight: 48)
```

Remove the `padding: EdgeInsets.zero`. Let Material defaults handle it.

### BUG-014: Inspector Can Download Unassigned Projects

**Change**: In the Company tab's download/import action, check `isAssigned` on `MergedProjectEntry` before allowing download. If `!isAssigned && role == inspector`, disable the download action and show a tooltip: "Contact your admin to be assigned to this project."

The project card remains visible — inspector can see name, status, etc. Just can't download.

Add a "My Projects" filter chip to the Company tab that filters to `isAssigned == true`. Defaults to showing all.

### BUG-015: RLS INSERT Policy Fix

**New migration**: Replace the `company_projects_insert` policy:

```sql
DROP POLICY "company_projects_insert" ON projects;
CREATE POLICY "company_projects_insert" ON projects
  FOR INSERT TO authenticated
  WITH CHECK (
    company_id = get_my_company_id()
    AND (is_admin() OR is_engineer())
  );
```

Also drop the dead `is_viewer()` function in the same migration.

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Inspector deep-links to `/project/new` | Router redirects to `/projects` |
| Inspector on Details tab of project edit | Fields render read-only, Save button hidden |
| Inspector taps archive on project card | Button not rendered (gated by `canManageProjects`) |
| Network drops mid-sync, recovers 30s later | Next pull-to-refresh re-checks DNS, sync resumes |
| Fresh inspector device, zero assignments | `project_assignments` pulls (direct scope), `onPullComplete` finds nothing to enroll, empty state shown. No deadlock. |
| Inspector assigned to project mid-session | Next sync pulls assignment, auto-enrolls, data arrives on following cycle |
| `removeFromDevice` on last remaining project | `_selectedProject` cleared, dashboard shows "no project selected" |
| Inspector tries to download unassigned project | Download action disabled, tooltip explains |
| Orphan cleaner runs before projects adapter | Guard prevents deletion — waits until projects adapter has completed |

---

## Testing Strategy

| Area | Test Type | Priority |
|------|-----------|----------|
| `canManageProjects` returns false for inspector | Unit | HIGH |
| `canEditFieldData` returns true for all roles | Unit | HIGH |
| Router redirects inspector from `/project/new` | Widget | HIGH |
| Archive button hidden for inspector | Widget | HIGH |
| `toggleActive` rejects inspector role | Unit | HIGH |
| Download disabled for unassigned projects | Widget | HIGH |
| `_refresh()` calls `checkDnsReachability()` | Unit | HIGH |
| `project_assignments` pulls with empty `synced_projects` | Unit | HIGH |
| `_selectedProject` cleared after removeFromDevice | Unit | MEDIUM |
| Dashboard staleness guard | Widget | MEDIUM |
| Tap target size >= 48dp | Widget | MEDIUM |
| RLS INSERT policy blocks inspector | Integration (Supabase) | MEDIUM |
| Orphan cleaner guard respects adapter ordering | Unit | MEDIUM |
| Offline indicator shows/hides correctly | Widget | LOW |

---

## Security Implications

### RLS Changes

| Policy | Current | After |
|--------|---------|-------|
| `company_projects_insert` | `NOT is_viewer()` (always true) | `is_admin() OR is_engineer()` |
| `is_viewer()` function | Exists, always returns false | Remove in same migration |

### Defense-in-Depth Layers

| Layer | What it guards |
|-------|---------------|
| **Router redirect** | Blocks inspector from project create screen |
| **UI gates** (`canManageProjects`) | Hides archive button, create FAB, project details Save |
| **Provider guards** | `toggleActive()`, `deleteProject()` reject unauthorized roles |
| **RLS policies** | Server blocks INSERT even if all client guards bypassed |

### No New Attack Surfaces

- No new tables or columns
- No new RLS policies beyond tightening the INSERT
- `canEditFieldData` is true for all roles (same as current `canWrite` behavior for field data) — no regression
- `canManageProjects` is strictly more restrictive than current state

---

## Migration & Cleanup

### Schema Migration

One new Supabase migration:
- Drop + recreate `company_projects_insert` policy with `is_admin() OR is_engineer()`
- Drop `is_viewer()` function

### Code Cleanup

| Item | Action |
|------|--------|
| `UserRole.canWrite` | Remove getter entirely |
| `UserProfile.canWrite` | Remove (delegates to role) |
| `AuthProvider.canWrite` | Remove |
| `AuthProvider.canEditProject` | Remove (dead code, BUG-012) |
| `is_viewer()` SQL function | Drop in migration |
| 102 `canWrite` call sites | Replace with `canManageProjects` (~15) or `canEditFieldData` (~87) |
| `ViewOnlyBanner` widget | Repurpose — shows when `!canManageProjects` on Details tab |

### No Backward Compatibility Needed

- `canWrite` is only used internally (not persisted, not in API responses)
- Removing it is a compile-time break — all 102 sites must be updated before build succeeds
- No feature flags needed — this is a bug fix, not a gradual rollout
