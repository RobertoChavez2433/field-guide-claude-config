# Project State UI & Assignments Spec

**Date:** 2026-03-18
**Status:** Reviewed — pending final approval
**Adversarial Review:** `.claude/adversarial_reviews/2026-03-18-project-state-ui/review.md`

---

## 1. Overview

### Purpose
Redesign the Projects tab to give users a clean, role-aware experience for managing which projects live on their device. Currently, all company projects auto-pull for every user, causing confusion and performance issues. The new design introduces a tabbed layout, project assignments managed from the project setup wizard, and clear visual states for on-device vs remote vs archived projects.

### Scope — Included
- 3-tab layout: My Projects | Company | Archived
- Fix auto-enrollment bug (fresh accounts start empty)
- Two-badge system (location + lifecycle) on project cards
- Rich preview cards with filter chips on Company tab (All / On Device / Not Downloaded)
- Multi-step unenrollment dialog with sync-first safety option
- Project assignment tab in project setup wizard — admins/engineers assign team members
- Auto-sync + notification (via pending notifications queue) when a user is assigned
- Project archival — admin/engineer marks complete; moves to Archived tab on all devices
- Per-project user assignments — organizational (not access-control); controls My Projects visibility
- Archived projects respect assignments — only assigned members can download
- Project creation restricted to Admin + Engineer roles
- Empty state for My Projects with "Browse Available" CTA
- Delete legacy `project_selection_screen.dart` + full GoRouter route audit

### Scope — Excluded
- Auto-archive based on inactivity (may add later)
- Assign-during-approval flow (assignment is project-centric)
- Stale-role retry handling for demoted engineers (extremely unlikely edge case)

### Data Access Model (MF-6)
**Assignments are organizational, not access-control boundaries.** Any approved company member can self-enroll from the Company tab and pull full project data — RLS scopes all data by `company_id`, not by assignment. Assignments control:
- What appears in "My Projects" tab (auto-enrolled on assignment)
- Who the admin/engineer has formally placed on a project
- Whether archived projects can be downloaded (assignment required)

Self-enrollment is a convenience for inspectors who need ad-hoc access to a project they weren't formally assigned to.

### Success Criteria
- Fresh inspector sees empty My Projects tab with browse CTA
- Admin/engineer can assign inspectors from the setup wizard
- Assigned projects auto-sync with snackbar notification
- Inspector can self-enroll from Company tab
- Archived projects visible but only downloadable by assigned members
- Removing a project prompts sync-first safety dialog
- No auto-enrollment of all company projects for new accounts

---

## 2. Data Model

### New Entity: `project_assignments`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| project_id | UUID | Yes | FK → projects.id |
| user_id | UUID | Yes | FK → auth.users.id |
| assigned_by | UUID | Yes | FK → auth.users.id (server-enforced via trigger) |
| company_id | UUID | Yes | FK → companies.id (denormalized for integrity RPC; populated via trigger from project) |
| assigned_at | TIMESTAMPTZ | Yes | When the assignment was made |
| updated_at | TIMESTAMPTZ | Yes | Last modification (trigger-maintained) |

**Changes from initial draft (review findings):**
- Dropped `created_at` — redundant with `assigned_at` for insert-only table (NH-15)
- Added `company_id` — enables `get_table_integrity` RPC, avoids join for audits (NH-16)
- `assigned_by` server-enforced via `enforce_created_by()` trigger pattern (MF-2)

**Unique constraint:** `(project_id, user_id)`

### Modified Entity: `synced_projects`

Add column:
```sql
ALTER TABLE synced_projects ADD COLUMN unassigned_at TEXT;
```

When the assignment adapter detects a deletion for the current user during pull, it sets `unassigned_at = now()` on the matching `synced_projects` row. This enables the "Unassigned" badge without auto-unenrolling. (MF-4)

### Supabase Schema
```sql
CREATE TABLE project_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  assigned_by UUID NOT NULL REFERENCES auth.users(id),
  company_id UUID NOT NULL REFERENCES companies(id),
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (project_id, user_id)
);

-- CRITICAL: Enable RLS (MF-1)
ALTER TABLE project_assignments ENABLE ROW LEVEL SECURITY;
```

### Triggers (SC-8)
```sql
-- Enforce assigned_by = auth.uid() on INSERT (MF-2)
CREATE TRIGGER trg_project_assignments_created_by
  BEFORE INSERT ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION enforce_created_by();

-- Prevent timestamp spoofing on INSERT
CREATE TRIGGER trg_project_assignments_insert_ts
  BEFORE INSERT ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();

-- Auto-update updated_at
CREATE TRIGGER trg_project_assignments_updated_at
  BEFORE UPDATE ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Populate company_id from project (NH-16)
CREATE OR REPLACE FUNCTION populate_assignment_company_id()
RETURNS TRIGGER AS $$
BEGIN
  NEW.company_id := (SELECT company_id FROM projects WHERE id = NEW.project_id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_project_assignments_company_id
  BEFORE INSERT ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION populate_assignment_company_id();
```

### Audit Logging (NH-18)
```sql
-- Log assignment changes for forensic traceability
CREATE OR REPLACE FUNCTION log_assignment_change()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    RAISE LOG 'project_assignment_created: project=% user=% by=%', NEW.project_id, NEW.user_id, NEW.assigned_by;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    RAISE LOG 'project_assignment_deleted: project=% user=% by=%', OLD.project_id, OLD.user_id, auth.uid();
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_project_assignments_audit
  AFTER INSERT OR DELETE ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION log_assignment_change();
```

### RLS Policies

```sql
-- SELECT: Scoped by role (SC-7)
-- Inspectors see only their own assignments; admins/engineers see all company assignments
CREATE POLICY "see_assignments" ON project_assignments
  FOR SELECT TO authenticated
  USING (
    (user_id = auth.uid() OR is_admin_or_engineer())
    AND company_id = get_my_company_id()
  );

-- INSERT: Admin/engineer only, same company, assignee must be company member (MF-3)
CREATE POLICY "admin_engineer_assign" ON project_assignments
  FOR INSERT TO authenticated
  WITH CHECK (
    is_admin_or_engineer()
    AND company_id = get_my_company_id()
    AND assigned_by = auth.uid()
    AND user_id IN (
      SELECT id FROM user_profiles
      WHERE company_id = get_my_company_id() AND status = 'approved'
    )
  );

-- DELETE: Admin/engineer only, same company
CREATE POLICY "admin_engineer_unassign" ON project_assignments
  FOR DELETE TO authenticated
  USING (
    is_admin_or_engineer()
    AND company_id = get_my_company_id()
  );
```

### New Helper Function
```sql
CREATE OR REPLACE FUNCTION is_admin_or_engineer()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM user_profiles
    WHERE id = auth.uid()
      AND status = 'approved'
      AND role IN ('admin', 'engineer')
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public;
```

### Sync Considerations
- `project_assignments` gets its own table adapter with `ScopeType.direct`
- SELECT RLS scopes data by role — inspectors get only their rows, admins/engineers get all (SC-7)
- Auto-enrollment injection point: `adapter.onPullComplete(pulledRows, currentUserId)` callback in the engine, called after each table's pull completes (MF-5)
- On pull, new assignment for current user → INSERT into `synced_projects` + add to pending notifications queue
- On pull, assignment deleted for current user → set `unassigned_at` on `synced_projects` row (do NOT delete)
- Assignments held in-memory during wizard; only written to DB on final save (SC-12)

---

## 3. User Flow

### Entry Points
1. Bottom nav → Projects tab (primary)
2. Notification tap → opens My Projects tab
3. Dashboard card → opens My Projects tab

### Tab Navigation
```
Projects Tab
├── [My Projects]  [Company]  [Archived]
│
├── My Projects (default tab)
│   ├── Empty state → "No projects yet. Browse available projects →"
│   └── Cards: enrolled projects with two badges (On Device + Active)
│
├── Company
│   ├── Filter chips: [All] [On Device] [Not Downloaded]
│   ├── Cards: all active company projects
│   │   ├── On Device → tap opens project
│   │   └── Not Downloaded → tap shows download confirmation
│   └── Search bar
│
└── Archived
    ├── Cards: all archived projects (company-wide)
    │   ├── Assigned + On Device → viewable, read-only
    │   ├── Assigned + Not Downloaded → can download
    │   └── Not Assigned → metadata visible, download disabled
    └── Empty state → "No archived projects"
```

### Flow 1: Inspector first login (empty state)
Opens Projects tab → My Projects empty → CTA → Company tab → taps project → download confirmation → syncs → appears in My Projects

### Flow 2: Admin/Engineer assigns inspector
Admin opens project → Edit → Assignments tab → checks inspector → Save → project_assignments row created → Inspector's next sync auto-enrolls + snackbar notification → project appears in My Projects

### Flow 3: Inspector removes project from device
Long-press → Dialog: [Sync & Remove] / [Delete from Device] / [Cancel]
- "Sync & Remove" → sync, verify `getUnsyncedChangeCount(projectId) == 0`, then remove
- "Delete from Device" → warning: "Local data will be deleted without syncing" → [Delete Anyway] / [Cancel]
- Removal: delete local data, remove from `synced_projects`. Project moves to Company tab.

### Flow 4: Admin archives project
Admin sets `is_active = false` → syncs → all team members see project move to Archived tab on next sync. Local data stays.

### Flow 5: Assignments in project wizard
Create/Edit Project wizard:
1. Project Details
2. Locations
3. Assignments (NEW) — searchable member list with checkboxes + role badges
4. Save (existing FAB pattern preserved)

- Assignments held in-memory until save (SC-12)
- Creator auto-assigned, can't be unchecked
- Counter: "N of M assigned"

---

## 4. UI Components

### Tab Bar
`TabBar` with 3 tabs + badge counts: My Projects (N) | Company (N) | Archived (N)

### Project Card (unified)
Same card across all tabs with contextual badges.

**Location badges (shown on Company/Archived tabs):**
| Badge | Color | When |
|-------|-------|------|
| On Device | Green pill | In `synced_projects` |
| Remote | Grey pill | Not in `synced_projects` |

**Lifecycle badges:**
| Badge | Color | When |
|-------|-------|------|
| Active | Cyan pill | `is_active = true` |
| Archived | Amber pill | `is_active = false` |
| Unassigned | Red outline pill | `synced_projects.unassigned_at` is set |

**Contextual actions per tab:**

| Tab | Tap | Long-press | Trailing |
|-----|-----|------------|----------|
| My Projects | Open | Sync/Delete dialog | Edit, Quick-entry |
| Company (on device) | Open | — | Edit (admin/eng) |
| Company (not downloaded) | Download dialog | — | — |
| Archived (assigned, on device) | Open (read-only) | Remove from device | — |
| Archived (assigned, not downloaded) | Download dialog | — | — |
| Archived (not assigned) | Disabled / metadata only | — | — |

### Filter Chips (Company tab)
```dart
enum CompanyFilter { all, onDevice, notDownloaded }  // SC-10
```
`[All (12)] [On Device (3)] [Not Downloaded (9)]` — single-select, default: All

### Empty States
- My Projects: folder icon + "No projects on your device" + [Browse Available Projects]
- Company (no projects at all): "No company projects yet. Ask your admin to create one."
- Company (filtered empty): "No projects match this filter."
- Archived: "No archived projects."

### Assignments Step (wizard)
Searchable list of company members. Checkboxes + role badges. Creator locked. Counter.

### Dialogs
- Download confirmation: simple confirm/cancel
- Removal: multi-step (Sync & Remove / Delete / Cancel → warning if delete)

### New Widgets
| Widget | Purpose |
|--------|---------|
| `ProjectTabBar` | 3-tab controller with badge counts |
| `ProjectFilterChips` | Company tab filter chips |
| `AssignmentListTile` | Checkbox + name + role badge |
| `AssignmentsStep` | Wizard step with search + list |
| `RemovalDialog` | Multi-step removal flow |
| `ProjectEmptyState` | Empty state with CTA |

---

## 5. State Management

### Modified: `ProjectProvider`

New state:
```dart
int _currentTabIndex = 0;
CompanyFilter _companyFilter = CompanyFilter.all;  // SC-10: proper enum
```

New getters (computed in single pass — NH-17):
```dart
List<MergedProjectEntry> get myProjects;       // enrolled + active
List<MergedProjectEntry> get companyProjects;   // all active, filtered
List<MergedProjectEntry> get archivedProjects;  // is_active = false
int get myProjectsCount;
int get companyProjectsCount;
int get archivedProjectsCount;
```

`_buildMergedView()` computes all three lists in a single pass over the data, storing them directly rather than deriving lazily in getters. (NH-17)

New methods:
```dart
void setCompanyFilter(CompanyFilter filter);
Future<void> enrollProject(String projectId);
Future<void> unenrollProject(String projectId, {bool syncFirst = false});
```

### New: `ProjectAssignmentProvider`

Separate provider for wizard step. Holds assignments in-memory until save (SC-12):
```dart
Future<void> loadForProject(String projectId, String companyId);
void toggleAssignment(String userId);
Future<void> save(String projectId, String assignedBy);
bool isAssigned(String userId);
int get assignedCount;
```

### Notification Flow (SC-9)
`SyncProvider` gets a `List<String> _pendingNotifications` queue. After sync:
1. Assignment adapter's `onPullComplete` adds messages: "You've been assigned to [Project Name]"
2. UI checks `pendingNotifications` after sync completes
3. Shows snackbars sequentially
4. Provider clears the list after display

### Error Handling
- Assignments require network → "You need to be online to manage assignments"
- Enrollment failure → snackbar error, card stays in Company tab
- Unenrollment sync failure → "Sync failed. Try again or delete without syncing."
- "Sync & Remove" completes when `getUnsyncedChangeCount(projectId) == 0`

---

## 6. Offline Behavior

### Capabilities

| Action | Offline? | Notes |
|--------|----------|-------|
| View My Projects | Yes | Local SQLite |
| Work on enrolled projects | Yes | Full offline |
| View Company tab | Partial | Cached metadata. Download requires network. |
| View Archived tab | Yes | Cached metadata + local archived |
| Download a project | No | "You're offline" message |
| Remove from device | Yes | Local-only operation |
| Sync & Remove | No | Greyed out with tooltip |
| Manage assignments | No | "You need to be online" |
| Receive assignment | Deferred | Pulled on next sync |

### Sync Strategy

**`project_assignments`:** Server-authoritative.
- Pull-only on inspector devices (they never write assignments)
- Push+pull on admin/engineer devices
- SELECT RLS scopes by role — inspectors get only their rows (SC-7)
- No change_log trigger on inspector devices

**Auto-enrollment on pull (MF-5):**
```
Engine calls adapter.onPullComplete(pulledRows, currentUserId)
→ For each row where user_id == currentUserId:
    → If project_id NOT IN synced_projects:
        → INSERT INTO synced_projects (ConflictAlgorithm.ignore)
        → Add to SyncProvider.pendingNotifications
→ For deletions where user_id == currentUserId:
    → Set synced_projects.unassigned_at = now()
    → Do NOT remove synced_projects row (data safety)
```

### Conflict Resolution

| Scenario | Resolution |
|----------|------------|
| Two admins assign same user | UNIQUE constraint, second insert no-op |
| Admin removes assignment while inspector offline | Inspector keeps data. "Unassigned" badge on next sync. |
| Self-enroll + admin assigns same | No conflict — synced_projects exists, assignment additive |
| Archive with unsynced data | Push before pull. Data syncs, then archive pulls down. |

---

## 7. Edge Cases

### Error States

| Scenario | Handling |
|----------|----------|
| Download fails mid-sync | Enrollment rolled back. Card stays in Company tab. |
| Project deleted while on device | Soft-delete pulls down. Local data cleaned up. |
| Admin demoted mid-session | Assignments tab disappears on next sync. Server blocks writes immediately. |
| Network drops during Sync & Remove | Removal aborted. "Sync failed. Project not removed." |
| All projects archived | Empty My Projects: "No active projects. Check Archived tab." |
| Company has zero projects | Company tab: "No company projects yet. Ask your admin to create one." |

### Permission Edge Cases

| Scenario | Behavior |
|----------|----------|
| Inspector creates project | FAB hidden. Deep-link redirects with message. |
| Inspector opens wizard | Read-only. No Assignments tab. |
| Cross-company assignment | RLS blocks — INSERT checks both project and user company. |
| Unassigned inspector downloads archived | Disabled — metadata visible, download blocked. |
| Deactivated member in list | Greyed out + "Deactivated" badge. Can't be newly assigned. |

### Race Conditions

| Scenario | Resolution |
|----------|------------|
| Two admins editing assignments | Last-write-wins per row. UNIQUE prevents duplicates. |
| Inspector syncs during admin save | Pulls committed state only. |
| Double-enrollment | `ConflictAlgorithm.ignore`. Safe. |
| Duplicate notification on crash recovery | `ConflictAlgorithm.ignore` handles re-insert. Notification may show twice — acceptable UX tradeoff. |

---

## 8. Testing Strategy

### Unit Tests (HIGH)
- ProjectAssignmentRepository CRUD + duplicate handling
- ProjectProvider tab filtering — single-pass computation
- Auto-enrollment on assignment pull
- Unenrollment flow (sync-first vs delete-only)
- CompanyFilter enum filtering logic

### Widget Tests (HIGH)
- Tab switching + badge counts update
- ProjectCard badge combos (all combinations)
- AssignmentsStep (search, toggle, counter, creator locked)
- RemovalDialog multi-step flow
- Permission gating (FAB, Assignments tab, archive download)

### Widget Tests (MED)
- Filter chip selection
- Download confirmation dialog
- Empty states (all 4 variants)
- Unassigned badge display

### Integration Tests
- Fresh inspector: empty → browse → download → My Projects
- Admin assigns → inspector syncs → auto-appears + notification
- Remove project (both Sync & Remove and Delete paths)
- Archive project → moves to Archived tab
- Unassigned member cannot download archived project
- Offline: Company tab cached, download disabled
- 50+ project catalog filter performance

---

## 9. Performance Considerations

| Area | Concern | Mitigation |
|------|---------|------------|
| 100+ projects in Company tab | Rendering | `ListView.builder` — only visible cards built |
| Project metadata pull | Size | ~1KB/project. 100 = ~100KB. Fine. |
| Assignments pull | Size | Inspector: own rows only (~10 rows). Admin: all (~1000 max). Fine. |
| Tab switching | Rebuild | Pre-computed lists in single pass (NH-17). Swap, don't recompute. |
| Filter toggle | Re-filter | In-memory O(n). Instant for <1000. |
| Auto-enrollment batch | Multiple inserts | Collect all, bulk-insert, single sync. |

---

## 10. Security Implications

### Authorization Matrix

| Operation | Required Role | Enforcement |
|-----------|--------------|-------------|
| View any tab | Any authenticated | Client + RLS |
| Download/enroll (active) | Any authenticated | Local + RLS by company |
| Download (archived) | Assigned members only | Client + RLS + assignment check |
| Create project | Admin, Engineer | Client: FAB hidden. Server: RLS INSERT. |
| Edit project | Admin, Engineer | Client: button hidden. Server: RLS UPDATE. |
| Manage assignments | Admin, Engineer | Client: tab hidden. Server: RLS + `is_admin_or_engineer()`. |
| Archive project | Admin, Engineer | Client: toggle hidden. Server: RLS UPDATE. |

### RLS Summary

| Policy | Scope |
|--------|-------|
| SELECT | `user_id = auth.uid() OR is_admin_or_engineer()` + `company_id` (SC-7) |
| INSERT | `is_admin_or_engineer()` + `company_id` + `assigned_by = auth.uid()` + `user_id` in same company (MF-2, MF-3) |
| DELETE | `is_admin_or_engineer()` + `company_id` |
| RLS enabled | `ALTER TABLE project_assignments ENABLE ROW LEVEL SECURITY` (MF-1) |

### Triggers
- `enforce_created_by()` — stamps `assigned_by = auth.uid()` (MF-2)
- `enforce_insert_updated_at()` — prevents timestamp spoofing (SC-8)
- `update_updated_at_column()` — maintains `updated_at` (SC-8)
- `populate_assignment_company_id()` — denormalizes `company_id` from project (NH-16)
- `log_assignment_change()` — audit log for INSERT/DELETE (NH-18)

### Threat Model

| Threat | Mitigation |
|--------|------------|
| Inspector crafts assignment | RLS INSERT rejects |
| Cross-company assignee | INSERT checks user_id company membership (MF-3) |
| Spoofed assigned_by | Trigger overwrites with auth.uid() (MF-2) |
| Spoofed timestamps | `enforce_insert_updated_at` trigger (SC-8) |
| Mass self-enrollment | Local-only, no server impact |
| Deactivated user creates assignment | `is_admin_or_engineer()` checks `status = 'approved'` |

---

## 11. Migration/Cleanup

### Supabase Migrations
| Migration | Change |
|-----------|--------|
| `create_project_assignments.sql` | CREATE TABLE + RLS + triggers + `is_admin_or_engineer()` + audit logging |
| `fix_auto_enrollment.sql` | Remove v30 backfill that auto-populates synced_projects |

### SQLite Changes
- Add `project_assignments` table (schema version bump)
- Add `unassigned_at TEXT` column to `synced_projects` (MF-4)

### New Files
| File | Purpose |
|------|---------|
| `lib/features/sync/adapters/project_assignment_adapter.dart` | Table adapter with `onPullComplete` |
| `lib/features/projects/data/models/project_assignment.dart` | Model |
| `lib/features/projects/data/repositories/project_assignment_repository.dart` | CRUD |
| `lib/features/projects/presentation/providers/project_assignment_provider.dart` | Wizard state |
| `lib/features/projects/presentation/widgets/assignments_step.dart` | Wizard step |
| `lib/features/projects/presentation/widgets/project_tab_bar.dart` | Tab bar |
| `lib/features/projects/presentation/widgets/project_filter_chips.dart` | Filters |
| `lib/features/projects/presentation/widgets/removal_dialog.dart` | Multi-step dialog |
| `lib/features/projects/presentation/widgets/project_empty_state.dart` | Empty state |
| `supabase/migrations/20260318_create_project_assignments.sql` | Migration |
| `supabase/rollbacks/20260318_create_project_assignments_rollback.sql` | Rollback |

### Modified Files
| File | Change |
|------|--------|
| `project_list_screen.dart` | 3-tab layout, filter chips, updated badges |
| `project_provider.dart` | Tab getters, single-pass build, filter logic, enroll/unenroll |
| `project_setup_screen.dart` | Add Assignments step |
| `database_service.dart` | Add project_assignments table + synced_projects.unassigned_at. Version bump. |
| `sync_engine_tables.dart` | Add project_assignments DDL |
| `sync_registry.dart` | Register assignment adapter |
| `sync_engine.dart` | `onPullComplete` callback, auto-enrollment logic |
| `sync_provider.dart` | `pendingNotifications` queue |
| `main.dart` | Register ProjectAssignmentProvider |
| `app_router.dart` | Remove project-selection route (SC-14) |

### Dead Code Removal
- `project_selection_screen.dart` — deleted + full GoRouter route audit (SC-14)
- v30 migration backfill in `database_service.dart` — remove auto-populate logic

### Bug Fixes Bundled
- `OrphanScanner: column photos.company_id does not exist` — fix query join
- Phantom pending changes after sync — `_pushUpsert` pulling guard (already fixed)
- `get_pending_requests_with_profiles` varchar/text mismatch (already pushed)

### Backward Compatibility
- Existing users: `synced_projects` entries stay. Can manually unenroll.
- Existing projects without assignments: show in Company tab. Self-enrollment works.
- Standard `onUpgrade` path for new table + column.
