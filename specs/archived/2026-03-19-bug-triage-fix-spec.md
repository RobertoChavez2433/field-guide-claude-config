# Bug Triage Fix Spec — 13 Bugs from S591 Device Testing

**Date**: 2026-03-19
**Session**: S592
**Source**: `bugs_report.md` (14 bugs filed, 1 dismissed as non-issue)
**Adversarial Review**: `.claude/adversarial_reviews/2026-03-19-bug-triage-fix/review.md`

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
- RLS INSERT and UPDATE policies block inspector project management server-side

### Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Inspector write scope | Entries + locations + pay items + contractors + equipment + personnel types | All field data actions — this is the inspector's job |
| Project management | Admin + engineer only (create, archive, delete, edit details) | Organizational actions, not field work |
| Engineer delete | Allowed | Engineers need full project lifecycle control |
| Sync recovery | Re-check DNS on every refresh + global offline indicator | User shouldn't feel chained to connectivity |
| Enrollment deadlock | Reload `_syncedProjectIds` after `project_assignments` pull + orphan cleaner guard | `ScopeType.direct` already set; real fix is pull ordering |
| Company tab visibility | All projects visible, download restricted to assigned for inspector | Inspector can see project cards but not import unassigned |
| RLS fix | Tighten INSERT + UPDATE policies, replace `is_viewer()` body with `SELECT FALSE` | Defense-in-depth; safe approach to dead function cleanup |
| `is_viewer()` handling | Replace body with `SELECT FALSE`, do NOT drop — 70-96 policy clauses still reference it | Dropping breaks all write policies. Batch clause cleanup deferred. |

---

## Permission Model Changes

### Core Fix: Replace `canWrite` with granular permissions

```
UserRole:
  canWrite          → REMOVE
  canManageProjects → admin, engineer only (create, archive, delete, edit project details)
  canEditFieldData  → all roles (contractors, equipment, personnel types, locations, pay items, entries, photos, todos, forms)
```

Remove `canEditProject` dead code getter first (BUG-012) before adding new getters to avoid accidental use during migration.

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

### Migration Path for ~139 `canWrite` Occurrences

**NOTE**: Grep shows ~139 auth-related occurrences across 24 files (not 102 as originally estimated). Implementer should expect more sites than estimated. Run `flutter analyze` after each pass to catch remaining compile errors.

Three categories:
1. **Project management actions** (create, archive, edit project details) → replace with `canManageProjects` — ~15 call sites
2. **Field data actions** (contractors, equipment, personnel types, locations, pay items, entries, photos, todos, forms) → replace with `canEditFieldData` (true for all roles) — ~87+ call sites
3. **`BaseListProvider.canWrite` injection sites** — 10 injection sites in `main.dart:782-895` wire `() => authProvider.canWrite` into every field-data provider (`LocationProvider`, `ContractorProvider`, `PersonnelTypeProvider`, `EquipmentProvider`, `PhotoProvider`, `TodoProvider`, `DailyEntryProvider`, `BidItemProvider`, `InspectorFormProvider`, `CalculatorProvider`). Replace all with `() => authProvider.canEditFieldData`.

### Route Guards (BUG-007)

**IMPORTANT**: Guards must be in the top-level GoRouter `redirect:` callback in `_buildRouter()`, not widget-level. Deep links bypass widget guards.

```dart
// In top-level redirect callback (app_router.dart)
if (location == '/project/new') {
  final canManage = _authProvider.userProfile?.role.canManageProjects ?? false;
  if (!canManage) return '/projects';
}
```

- `/project/new` → redirect if `!canManageProjects`
- `/project/:id/edit` → **allow all roles**. Inspector gets full access to contractors, locations, pay items tabs. Only the Details tab (project name, dates, etc.) is gated by `canManageProjects` within the screen itself.

### Project Card Edit Button (BUG-008 + MF-6)

**CRITICAL**: The edit pencil `IconButton` on project cards (`project_list_screen.dart:740`) is currently gated by `canWrite`. It must **NOT** be replaced with `canManageProjects` — that would block inspectors from reaching the contractor/location/pay-item tabs entirely. Replace with `canEditFieldData` (true for all roles). Inspectors need to tap into the edit screen to do their field work.

### Archive Button on Project Cards (BUG-009)

The archive toggle `IconButton` (`project_list_screen.dart:755-774`) must be gated by `canManageProjects`. For inspector, the button is hidden/disabled. Add `canManageProjects` check inside `toggleActive()` method as a defense-in-depth guard.

### Dashboard (BUG-011)

- Contractors card → navigates to `project-edit?tab=2` for **all roles** (field data)
- Locations card → navigates to `project-edit?tab=1` for **all roles** (field data)

### `canEditProject` (BUG-012)

Delete dead code getter entirely before adding new getters. Currently at `auth_provider.dart:212`, never called anywhere in the codebase.

### Details Tab Read-Only for Inspector

On `ProjectSetupScreen` Details tab, when `!canManageProjects`:
- Form fields render read-only
- Save button hidden
- Show banner: "Project details are managed by admins and engineers" (not generic "View-only mode")

---

## Sync Engine Fixes

### BUG-006: Sticky `_isOnline` Recovery

**Change**: `_refresh()` in `project_list_screen.dart` calls `checkDnsReachability()` before checking `isSupabaseOnline`.

```
Current:  if (orchestrator.isSupabaseOnline) → sync
Fixed:    await orchestrator.checkDnsReachability() → if (orchestrator.isSupabaseOnline) → sync
```

**Also fix these stale-flag readers**:
- `_checkNetwork()` at `project_list_screen.dart:89-91` — must call `checkDnsReachability()` instead of just reading `isSupabaseOnline`
- `_showRemovalDialog` at `project_list_screen.dart:509` — must refresh before gating `syncAndRemove`

**Global offline indicator**: Add to existing `ScaffoldWithNavBar` banner area at `app_router.dart:657-700`. The `banners` list already uses `Consumer2<SyncProvider, AppConfigProvider>` — add a connectivity condition here. Small dot or icon, not intrusive.

### BUG-005 + BUG-002: Fresh Inspector Deadlock & synced_projects Race (Same Root Cause)

**NOTE**: `project_assignments` adapter is already `ScopeType.direct` (set in prior session at `project_assignment_adapter.dart:17`). The original BUG-005 diagnosis was incorrect.

**Real root cause**: The orphan cleaner in `_loadSyncedProjectIds()` (`sync_engine.dart:1312-1327`) runs at the top of `_pull()` and deletes `synced_projects` entries for projects not yet in the local `projects` table. On a fresh device, this purges newly enrolled entries before the `projects` adapter has run.

**Additionally**: `onPullComplete` is already awaited (`sync_engine.dart:1270`), not fire-and-forget as originally stated. The race is that `_syncedProjectIds` is loaded once at the top of `_pull()` and not reloaded after `project_assignments` enrollment.

**Two fixes**:

1. **Reload after assignment enrollment**: Add a `_syncedProjectIds` reload inside `_pull()` after `project_assignments` adapter completes, mirroring the existing `projects` reload at `sync_engine.dart:1068`:
```dart
if (adapter.tableName == 'project_assignments' && count > 0) {
  await _loadSyncedProjectIds();
  Logger.sync('Reloaded synced project IDs after pulling $count assignments');
}
```

2. **Orphan cleaner guard**: In `_loadSyncedProjectIds()`, only delete orphan `synced_projects` entries if the `projects` adapter has already run in this cycle. Track with a `bool _projectsAdapterCompleted` flag reset at the start of each `_pull()` call.

**Flow after fix (fresh inspector device)**:
1. `_pull()` starts → `_loadSyncedProjectIds()` → empty, orphan cleaner skipped (projects adapter hasn't run yet)
2. `project_assignments` adapter pulls (direct scope) → `onPullComplete` enrolls assigned projects into `synced_projects`
3. `_loadSyncedProjectIds()` reloads → now has entries
4. `projects` adapter pulls → project rows arrive
5. Remaining project-scoped adapters pull normally with populated `_syncedProjectIds`

### BUG-004: No Auto-Reschedule After Retry Exhaustion

**Change**: After `_syncWithRetry()` exhausts 3 attempts, use a cancellable `Timer` (not `Future.delayed`) stored as `Timer? _backgroundRetryTimer` on `SyncOrchestrator`. Timer fires after 60 seconds, calls `checkDnsReachability()`, and re-attempts if DNS passes. Cap at 1 retry.

**Cancellation**: Cancel the timer at the start of `syncLocalAgencyProjects()` to prevent overlap with manual refresh. This avoids the UX issue of a stale background retry firing after the user has already manually recovered.

```dart
Timer? _backgroundRetryTimer;

// In _syncWithRetry() after exhaustion:
_backgroundRetryTimer?.cancel();
_backgroundRetryTimer = Timer(const Duration(seconds: 60), () async {
  await checkDnsReachability();
  if (_isOnline) await syncLocalAgencyProjects();
});

// In syncLocalAgencyProjects():
_backgroundRetryTimer?.cancel();
```

**Alternative considered**: Rely solely on `SyncLifecycleManager` app-resume path. Rejected because it doesn't cover the case where the user stays on-screen.

---

## State Management Fix

### BUG-001: Stale `_selectedProject` After removeFromDevice

**Change**: In `_handleRemoveFromDevice` (project_list_screen.dart), after calling `lifecycleService.removeFromDevice()`:

1. Guard externally before clearing: `if (projectProvider.selectedProject?.id == projectId) projectProvider.clearSelectedProject()` — `clearSelectedProject()` takes no parameters (confirmed at `project_provider.dart:365`)
2. Call `settingsProvider.clearIfMatches(projectId)` — clears persisted `last_project_<userId>` from SharedPreferences

Both calls already exist in the `deleteProject` path. The fix is adding them to the `removeFromDevice` path with the correct signatures.

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

### BUG-015: RLS Migration

**New migration** with three changes:

1. **Tighten INSERT policy**:
```sql
DROP POLICY IF EXISTS "company_projects_insert" ON projects;
CREATE POLICY "company_projects_insert" ON projects
  FOR INSERT TO authenticated
  WITH CHECK (
    company_id = get_my_company_id()
    AND is_admin_or_engineer()
  );
```
**NOTE**: Use existing `is_admin_or_engineer()` function (from `20260319100000_create_project_assignments.sql`). Do NOT use `is_admin() OR is_engineer()` — those don't exist as separate functions.

2. **Tighten UPDATE policy** (MF-3 — inspector can currently UPDATE `is_active`, `name`, `start_date`, etc.):
```sql
DROP POLICY IF EXISTS "company_projects_update" ON projects;
CREATE POLICY "company_projects_update" ON projects
  FOR UPDATE TO authenticated
  USING (
    company_id = get_my_company_id()
    AND is_admin_or_engineer()
  )
  WITH CHECK (
    company_id = get_my_company_id()
    AND is_admin_or_engineer()
  );
```
Inspectors should NOT be able to UPDATE the `projects` table at all. All inspector field work happens on child tables (locations, contractors, entries, etc.), not the `projects` row itself.

3. **Replace `is_viewer()` body** (do NOT drop the function):
```sql
CREATE OR REPLACE FUNCTION is_viewer()
RETURNS BOOLEAN AS $$
  SELECT FALSE;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION is_viewer() IS 'DEPRECATED: Viewer role removed in 20260317. Always returns FALSE. 70+ policy clauses still reference this function. Batch cleanup deferred.';
```

**Policies on other tables** (`user_certifications`, `storage.objects`, `daily_entries`, `locations`, `contractors`, etc.) all reference `is_viewer()` with `AND NOT is_viewer()`. Since the function now explicitly returns `FALSE`, these clauses evaluate to `AND TRUE` — correct behavior (all non-viewer roles can write, and no viewers exist). These can be batch-cleaned in a future migration.

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Inspector deep-links to `/project/new` | Top-level GoRouter redirect sends to `/projects` |
| Inspector on Details tab of project edit | Fields render read-only, Save hidden, banner shown |
| Inspector taps edit pencil on project card | Allowed — opens setup screen where they can edit field data tabs |
| Inspector taps archive on project card | Button not rendered (gated by `canManageProjects`) |
| Network drops mid-sync, recovers 30s later | Next pull-to-refresh re-checks DNS, sync resumes |
| Fresh inspector device, zero assignments | `project_assignments` pulls (direct scope), `onPullComplete` finds nothing to enroll, empty state shown. No deadlock. |
| Fresh inspector device, has assignments | `project_assignments` pulls → enrollment → `_syncedProjectIds` reloaded → child tables pull in same cycle |
| Inspector assigned to project mid-session | Next sync pulls assignment, auto-enrolls, data arrives on following cycle |
| `removeFromDevice` on last remaining project | `_selectedProject` cleared (if matching), dashboard shows "no project selected" |
| Inspector tries to download unassigned project | Download action disabled, tooltip explains |
| Orphan cleaner runs before projects adapter | Guard prevents deletion — `_projectsAdapterCompleted` flag is false |
| Background retry timer fires after manual refresh | Timer cancelled at start of `syncLocalAgencyProjects()` |
| Inspector tries to UPDATE projects row via sync engine | RLS UPDATE policy blocks with `is_admin_or_engineer()` check |

---

## Testing Strategy

| Area | Test Type | Priority |
|------|-----------|----------|
| `canManageProjects` returns false for inspector | Unit | HIGH |
| `canEditFieldData` returns true for all roles | Unit | HIGH |
| Router redirects inspector from `/project/new` (top-level redirect) | Widget | HIGH |
| Archive button hidden for inspector | Widget | HIGH |
| Edit button **enabled** for inspector (reaches field data tabs) | Widget | HIGH |
| `toggleActive` rejects inspector role | Unit | HIGH |
| Download disabled for unassigned projects (inspector) | Widget | HIGH |
| `_refresh()` calls `checkDnsReachability()` | Unit | HIGH |
| `_syncedProjectIds` reloaded after `project_assignments` pull | Unit | HIGH |
| `_selectedProject` cleared after removeFromDevice | Unit | MEDIUM |
| Dashboard staleness guard | Widget | MEDIUM |
| Tap target size >= 48dp | Widget | MEDIUM |
| RLS INSERT policy blocks inspector | Integration (Supabase) | MEDIUM |
| RLS UPDATE policy blocks inspector | Integration (Supabase) | MEDIUM |
| Orphan cleaner guard respects adapter ordering | Unit | MEDIUM |
| Background retry timer cancelled on manual sync | Unit | MEDIUM |
| `_checkNetwork()` calls `checkDnsReachability()` | Unit | MEDIUM |
| Offline indicator shows/hides correctly | Widget | LOW |
| Inspector can reach contractor/location tabs from edit button | Widget | LOW |
| `BaseListProvider` injection uses `canEditFieldData` | Unit | LOW |
| Zero remaining `canWrite` references in `lib/` (grep check) | CI | LOW |

---

## Security Implications

### RLS Changes

| Policy | Current | After |
|--------|---------|-------|
| `company_projects_insert` | `NOT is_viewer()` (always true) | `is_admin_or_engineer()` |
| `company_projects_update` | `NOT is_viewer()` + `deleted_at IS NULL` (inspector can update any field) | `is_admin_or_engineer()` |
| `is_viewer()` function | Returns `SELECT role = 'viewer'` (always false) | Replaced with `SELECT FALSE` + deprecation comment. NOT dropped. |

### Defense-in-Depth Layers

| Layer | What it guards |
|-------|---------------|
| **Router redirect** | Blocks inspector from project create screen |
| **UI gates** (`canManageProjects`) | Hides archive button, create FAB, project details Save |
| **Provider guards** | `toggleActive()`, `deleteProject()` reject unauthorized roles |
| **RLS INSERT policy** | Server blocks project creation by inspector |
| **RLS UPDATE policy** | Server blocks project field changes (is_active, name, dates) by inspector |

### Sync Engine Consideration (SC-5)

The sync engine `change_log` has no client-side role filter. If an inspector's local SQLite somehow contains a project UPDATE in `change_log`, the sync engine will push it to Supabase where the RLS UPDATE policy will now reject it. This is acceptable — the server-side guard is the correct enforcement point. A client-side guard in the sync engine would be a nice-to-have optimization to reduce unnecessary API calls, but is not required for security.

### Remaining `is_viewer()` References

~70-96 policy clauses across 8 migration files still reference `is_viewer()`. With the function body replaced to `SELECT FALSE`, all `AND NOT is_viewer()` clauses evaluate to `AND TRUE` — correct behavior. Batch cleanup of these clauses is deferred to a future migration to avoid blast radius risk.

---

## Migration & Cleanup

### Schema Migration

One new Supabase migration:
- Drop + recreate `company_projects_insert` policy with `is_admin_or_engineer()`
- Drop + recreate `company_projects_update` policy with `is_admin_or_engineer()`
- Replace `is_viewer()` function body with `SELECT FALSE` + deprecation comment

### Code Cleanup

| Item | Action |
|------|--------|
| `AuthProvider.canEditProject` | Remove first (dead code, BUG-012) — before adding new getters |
| `UserRole.canWrite` | Remove getter entirely |
| `UserProfile.canWrite` | Remove (delegates to role) |
| `AuthProvider.canWrite` | Remove |
| `BaseListProvider.canWrite` injection | Update 10 sites in `main.dart:782-895` to use `canEditFieldData` |
| ~139 `canWrite` occurrences | Replace with `canManageProjects` (~15) or `canEditFieldData` (~87+) |
| `ViewOnlyBanner` widget | Rewire for Details tab: "Project details are managed by admins and engineers" |
| Post-migration grep | Verify zero remaining `canWrite` references in `lib/` |

### No Backward Compatibility Needed

- `canWrite` is only used internally (not persisted, not in API responses)
- Removing it is a compile-time break — all sites must be updated before build succeeds
- No feature flags needed — this is a bug fix, not a gradual rollout
