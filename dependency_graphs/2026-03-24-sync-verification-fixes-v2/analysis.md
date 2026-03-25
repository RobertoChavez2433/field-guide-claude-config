# Sync Verification Fixes V2 — Dependency Graph & Analysis

## Problem Summary

All 94 sync verification scenarios fail due to systemic issues in the test infrastructure:
1. No `project_assignments` seeded → sync engine pulls nothing
2. `stamp_deleted_by` trigger blocks service-role cleanup
3. Missing fields in `make*()` helpers (company_id, deleted_at/deleted_by, project_id)
4. S4 scenarios query non-existent Supabase `conflict_log` table
5. UI-based scenarios may reference unattached widget keys

## Direct Changes

### 1. `tools/debug-server/scenario-helpers.js` (MODIFY)
**Symbols affected:** makeProject, makeContractor, makeEquipment, makePersonnelType, makeBidItem, makeInspectorForm, cleanup, module.exports
**Changes:**
- Add `makeProjectAssignment(projectId, userId)` helper
- Add `seedProjectWithAssignment(verifier, project, userId)` composite helper (authenticates, inserts project + assignment, resets auth)
- Add `seedProjectWithAssignments(verifier, project, userIds)` for L3 (both admin + inspector)
- Fix `makeContractor`: add `company_id`, `deleted_at: null`, `deleted_by: null`
- Fix `makeEquipment`: add `deleted_at: null`, `deleted_by: null`
- Fix `makePersonnelType`: add `deleted_at: null`, `deleted_by: null`
- Fix `makeBidItem`: add `deleted_at: null`, `deleted_by: null`
- Fix `makeInspectorForm`: add `project_id` parameter (required NOT NULL), `deleted_at: null`, `deleted_by: null`
- Fix `cleanup()`: switch from `softDeleteRecord` to `deleteRecord` (hard DELETE bypasses triggers)
- Update module.exports

### 2. `tools/debug-server/supabase-verifier.js` (MODIFY)
**Symbols affected:** queryByPrefix
**Changes:**
- Already partially fixed (tablesWithoutName set) — verify completeness

### 3. `tools/debug-server/scenarios/L2/*-S1-push.js` (MODIFY — 16 files)
**Pattern:** Add `project_assignments` seeding before first sync
- `bid-items-S1-push.js`
- `calculation-history-S1-push.js`
- `contractors-S1-push.js`
- `daily-entries-S1-push.js`
- `entry-contractors-S1-push.js`
- `entry-equipment-S1-push.js`
- `entry-personnel-counts-S1-push.js`
- `entry-quantities-S1-push.js` (NOTE: no file in git status, may already be correct or missing)
- `equipment-S1-push.js`
- `form-responses-S1-push.js`
- `inspector-forms-S1-push.js`
- `locations-S1-push.js`
- `personnel-types-S1-push.js`
- `photos-S1-push.js` (NOTE: no S1 in git status — may need creation or is unchanged)
- `projects-S1-push.js` (UI-based — different pattern, cleanup only)
- `todo-items-S1-push.js`

### 4. `tools/debug-server/scenarios/L2/*-S2-*.js` (MODIFY — ~16 files)
Same pattern: add project_assignments seeding

### 5. `tools/debug-server/scenarios/L2/*-S3-*.js` (MODIFY — ~16 files)
Same pattern: add project_assignments seeding

### 6. `tools/debug-server/scenarios/L2/*-S4-*.js` (MODIFY — ~10 files)
- Add project_assignments seeding
- Fix conflict_log verification: query LOCAL SQLite via driver, not Supabase

### 7. `tools/debug-server/scenarios/L2/*-S5-*.js` (MODIFY — ~10 files)
- Add project_assignments seeding
- Fix TEST_USER_ID → ADMIN_USER_ID in project-assignments-S5

### 8. `tools/debug-server/scenarios/L3/*.js` (MODIFY — 10 files)
- Add project_assignments for BOTH admin and inspector users
- Fix conflict_log queries to use local driver

## Trigger Analysis (Supabase)

| Trigger | Table(s) | Fires On | Impact on Tests |
|---------|----------|----------|-----------------|
| `stamp_deleted_by` | All 16 synced | BEFORE UPDATE (deleted_at NULL→non-NULL) | BLOCKS soft-delete cleanup with service role |
| `enforce_created_by` | All 16 synced | BEFORE INSERT | Sets created_by_user_id to auth.uid() (NULL with service role) — non-blocking but contaminates |
| `enforce_assignment_assigned_by` | project_assignments | BEFORE INSERT | Sets assigned_by = auth.uid() — must authenticate before insert |
| `populate_assignment_company_id` | project_assignments | BEFORE INSERT | Auto-populates company_id from project — helpful, not blocking |
| `enforce_insert_updated_at` | All 16 | BEFORE INSERT | Overwrites updated_at with NOW() — non-blocking |
| `lock_created_by` | All 16 | BEFORE UPDATE | Preserves created_by_user_id — non-blocking |

**Solution:** Use hard DELETE for cleanup (triggers are BEFORE UPDATE only). Use authenticateAs('admin') for project_assignments inserts.

## Sync Engine Scoping

| ScopeType | Tables | Pull Filter |
|-----------|--------|-------------|
| `direct` | projects, project_assignments, inspector_forms | `company_id = ?` |
| `viaProject` | locations, contractors, bid_items, personnel_types, daily_entries, todo_items, calculation_history, form_responses | `project_id IN (synced_projects)` |
| `viaEntry` | photos, entry_equipment, entry_quantities, entry_contractors, entry_personnel_counts | `project_id IN (synced_projects)` (denormalized) |
| `viaContractor` | equipment | `contractor_id IN (contractors WHERE project_id IN synced_projects)` |

**Critical:** `synced_projects` is populated from `project_assignments` via `_enrollProjectsFromAssignments()`. Without a `project_assignments` row for the test user, ALL viaProject/viaEntry/viaContractor tables return 0 rows on pull.

## FK Chain Requirements

For each scenario type, these parent records must exist on Supabase AND be pullable:

```
projects (root) ← project_assignments (for logged-in user)
  ├── locations ← project_id
  ├── contractors ← project_id + company_id
  │   └── equipment ← contractor_id
  ├── bid_items ← project_id
  ├── personnel_types ← project_id
  ├── daily_entries ← project_id + location_id
  │   ├── entry_contractors ← daily_entry_id + contractor_id
  │   ├── entry_equipment ← daily_entry_id + equipment_id
  │   ├── entry_personnel_counts ← daily_entry_id + contractor_id + personnel_type_id
  │   ├── entry_quantities ← daily_entry_id + bid_item_id
  │   └── photos ← daily_entry_id + project_id
  ├── inspector_forms ← project_id (NOT NULL)
  │   └── form_responses ← form_id + project_id
  ├── todo_items ← project_id
  └── calculation_history ← project_id
```

## Driver Endpoint Analysis

| Endpoint | Writes change_log? | Notes |
|----------|-------------------|-------|
| `/driver/update-record` | YES (SQLite trigger) | rawUpdate fires AFTER UPDATE trigger |
| `/driver/create-record` | YES (SQLite trigger) | rawInsert fires AFTER INSERT trigger. Limited to junction tables only. |
| `/driver/sync` | N/A | Calls syncOrchestrator.syncLocalAgencyProjects() |
| `/driver/remove-from-device` | Suppresses (pulling=1) | Correct — cleanup shouldn't generate change_log |

## conflict_log Issue

- `conflict_log` exists in LOCAL SQLite only (created by sync engine schema)
- It does NOT exist in Supabase (no migration creates it)
- S4 scenarios query it via `verifier.queryRecords('conflict_log', ...)` → will get PostgREST 404
- **Fix:** S4 scenarios must verify conflicts via driver's local record query, not Supabase verifier. Add a `/driver/query-conflicts` endpoint or use existing `/driver/local-record` with conflict_log table.

## Widget Key Attachment Status

Keys are DEFINED in testing_keys but grep shows NO attachment in presentation layer for:
- `project_save_button` — NOT found in projects/presentation/
- `entry_wizard_activities` — NOT found in entries/presentation/

This means UI-based scenarios (projects-S1, daily-entries-S1, calculation-history-S1, todo-items-S1) will fail at widget interaction. However, these are pre-existing issues from the S633/S634 ground-truth fixes and are OUT OF SCOPE for this plan (they require Flutter code changes, not JS test fixes).

## Blast Radius

- **Direct:** 3 infrastructure files + ~67 scenario files = ~70 files
- **Dependent:** 0 (no app code changes needed except possibly conflict_log driver endpoint)
- **Tests:** The scenario files ARE the tests
- **Cleanup:** Remove stale SYNCTEST-* records from Supabase after first successful run
