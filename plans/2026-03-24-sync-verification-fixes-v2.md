# Sync Verification Fixes V2 — Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Fix all 6 systemic blockers preventing 94 sync verification scenarios from passing, so that test infrastructure no longer masks real sync issues.
**Spec:** N/A (research-driven — see CONTEXT section in this plan)
**Analysis:** `.claude/dependency_graphs/2026-03-24-sync-verification-fixes-v2/`

**Architecture:** All fixes are in the Node.js test infrastructure (`tools/debug-server/`). A new `seedProjectWithAssignment()` helper in `scenario-helpers.js` wraps the 4-step auth-insert-insert-reset dance needed to create project_assignments rows (needed because `enforce_assignment_assigned_by` trigger requires `auth.uid()` to be non-null). Cleanup switches from soft-delete to hard-delete to bypass the `stamp_deleted_by` trigger. Individual scenario files get mechanical edits to call the new helper and remove broken `conflict_log` Supabase queries.
**Tech Stack:** Node.js, Supabase PostgREST, HTTP driver
**Blast Radius:** ~80 files (1 infrastructure + ~67 L2 scenarios + 10 L3 scenarios + 1 verifier allowlist)

---

## Phase 1: Fix Infrastructure — scenario-helpers.js and supabase-verifier.js
### Sub-phase 1.1: Fix make*() helpers with missing fields
**Files:** `tools/debug-server/scenario-helpers.js`
**Agent:** general-purpose

#### Step 1.1.1: Fix makeContractor — add company_id, deleted_at, deleted_by

Find this code in `tools/debug-server/scenario-helpers.js`:
```js
function makeContractor(projectId, overrides = {}) {
  return {
    id: uuid(),
    project_id: projectId,
    name: `SYNCTEST-Contractor ${Date.now()}`,
    type: 'prime',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}
```

Replace with:
```js
function makeContractor(projectId, overrides = {}) {
  return {
    id: uuid(),
    project_id: projectId,
    company_id: process.env.COMPANY_ID || (() => { throw new Error('COMPANY_ID env var required'); })(),
    name: `SYNCTEST-Contractor ${Date.now()}`,
    type: 'prime',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}
```

#### Step 1.1.2: Fix makeEquipment — add deleted_at, deleted_by

Find this code in `tools/debug-server/scenario-helpers.js`:
```js
function makeEquipment(contractorId, overrides = {}) {
  return {
    id: uuid(),
    contractor_id: contractorId,
    name: `SYNCTEST-Equipment ${Date.now()}`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}
```

Replace with:
```js
function makeEquipment(contractorId, overrides = {}) {
  return {
    id: uuid(),
    contractor_id: contractorId,
    name: `SYNCTEST-Equipment ${Date.now()}`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}
```

#### Step 1.1.3: Fix makePersonnelType — add deleted_at, deleted_by

Find this code in `tools/debug-server/scenario-helpers.js`:
```js
function makePersonnelType(projectId, overrides = {}) {
  return {
    id: uuid(),
    project_id: projectId,
    name: `SYNCTEST-PersonnelType ${Date.now()}`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}
```

Replace with:
```js
function makePersonnelType(projectId, overrides = {}) {
  return {
    id: uuid(),
    project_id: projectId,
    name: `SYNCTEST-PersonnelType ${Date.now()}`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}
```

#### Step 1.1.4: Fix makeBidItem — add deleted_at, deleted_by

Find this code in `tools/debug-server/scenario-helpers.js`:
```js
function makeBidItem(projectId, overrides = {}) {
  return {
    id: uuid(),
    project_id: projectId,
    item_number: `SYNCTEST-BI-${Date.now().toString(36).toUpperCase()}`,
    description: `SYNCTEST-BidItem ${Date.now()}`,
    unit: 'EA',
    bid_quantity: 100.0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}
```

Replace with:
```js
function makeBidItem(projectId, overrides = {}) {
  return {
    id: uuid(),
    project_id: projectId,
    item_number: `SYNCTEST-BI-${Date.now().toString(36).toUpperCase()}`,
    description: `SYNCTEST-BidItem ${Date.now()}`,
    unit: 'EA',
    bid_quantity: 100.0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}
```

#### Step 1.1.5: Fix makeInspectorForm — add project_id parameter

Find this code in `tools/debug-server/scenario-helpers.js`:
```js
function makeInspectorForm(overrides = {}) {
  return {
    id: uuid(),
    name: `SYNCTEST-Form ${Date.now()}`,
    template_path: '/templates/test.json',
    is_builtin: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}
```

Replace with:
```js
function makeInspectorForm(projectId, overrides = {}) {
  return {
    id: uuid(),
    project_id: projectId,
    name: `SYNCTEST-Form ${Date.now()}`,
    template_path: '/templates/test.json',
    is_builtin: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}
```

**IMPORTANT:** This is a breaking signature change. All callers must be updated in subsequent phases. Current callers (7 total):
- `inspector-forms-S1-push.js`: `makeInspectorForm({ name: 'SYNCTEST-Original-InspectorForm' })`
- `inspector-forms-S2-update-push.js`: `makeInspectorForm()`
- `inspector-forms-S3-delete-push.js`: `makeInspectorForm()`
- `form-responses-S1-push.js`: `makeInspectorForm()`
- `form-responses-S3-delete-push.js`: `makeInspectorForm()`

Note: `inspector-forms-S4-conflict.js`, `inspector-forms-S5-fresh-pull.js`, `form-responses-S4-conflict.js`, `form-responses-S5-fresh-pull.js`, and `form-responses-S2-update-push.js` create inspector_forms records inline (not via the helper) and also need `project_id` added.

### Sub-phase 1.2: Add seedProjectWithAssignment helper
**Files:** `tools/debug-server/scenario-helpers.js`
**Agent:** general-purpose

#### Step 1.2.1: Add seedProjectWithAssignment function

Add the following function BEFORE the `module.exports` block in `tools/debug-server/scenario-helpers.js`:

```js
/**
 * Seed a project AND a project_assignment row for a single user.
 * Required because the sync engine only pulls projects the user is assigned to.
 * Must authenticate as admin because the enforce_assignment_assigned_by trigger
 * requires auth.uid() to be non-null (it overwrites assigned_by with auth.uid()).
 *
 * @param {SupabaseVerifier} verifier
 * @param {object} project - Project record from makeProject()
 * @param {string} userId - User UUID to assign (e.g., ADMIN_USER_ID)
 * @returns {Promise<string>} The assignment ID (for cleanup)
 */
async function seedProjectWithAssignment(verifier, project, userId) {
  await verifier.insertRecord('projects', project);
  await verifier.authenticateAs('admin');
  const assignmentId = uuid();
  try {
    await verifier.insertRecord('project_assignments', {
      id: assignmentId,
      project_id: project.id,
      user_id: userId,
      assigned_by: userId,  // Trigger overwrites with auth.uid()
      company_id: process.env.COMPANY_ID,  // Trigger overwrites from project
      assigned_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  } finally {
    verifier.resetAuth();
  }
  return assignmentId;
}

/**
 * Seed a project AND project_assignment rows for multiple users.
 * Used by L3 multi-device scenarios where both admin and inspector need access.
 *
 * @param {SupabaseVerifier} verifier
 * @param {object} project - Project record from makeProject()
 * @param {string[]} userIds - Array of user UUIDs to assign
 * @returns {Promise<string[]>} Array of assignment IDs (for cleanup)
 */
async function seedProjectWithAssignments(verifier, project, userIds) {
  await verifier.insertRecord('projects', project);
  await verifier.authenticateAs('admin');
  const assignmentIds = [];
  try {
    for (const userId of userIds) {
      const assignmentId = uuid();
      await verifier.insertRecord('project_assignments', {
        id: assignmentId,
        project_id: project.id,
        user_id: userId,
        assigned_by: userId,  // Trigger overwrites with auth.uid()
        company_id: process.env.COMPANY_ID,  // Trigger overwrites from project
        assigned_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      assignmentIds.push(assignmentId);
    }
  } finally {
    verifier.resetAuth();
  }
  return assignmentIds;
}
```

#### Step 1.2.2: Export the new helpers

Find the `module.exports` line in `tools/debug-server/scenario-helpers.js`:
```js
module.exports = {
  uuid, testPrefix, sleep, verify, assertEqual,
  waitFor, step, cleanup,
  makeProject, makeDailyEntry, makeLocation,
  makeContractor, makeEquipment, makePersonnelType,
  makeBidItem, makeInspectorForm, makeFormResponse,
  setAirplaneMode,
};
```

Replace with:
```js
module.exports = {
  uuid, testPrefix, sleep, verify, assertEqual,
  waitFor, step, cleanup,
  makeProject, makeDailyEntry, makeLocation,
  makeContractor, makeEquipment, makePersonnelType,
  makeBidItem, makeInspectorForm, makeFormResponse,
  seedProjectWithAssignment, seedProjectWithAssignments,
  setAirplaneMode,
};
```

### Sub-phase 1.3: Fix cleanup — switch from soft-delete to hard-delete
**Files:** `tools/debug-server/scenario-helpers.js`
**Agent:** general-purpose

#### Step 1.3.1: Replace cleanup function

Find this code in `tools/debug-server/scenario-helpers.js`:
```js
async function cleanup(verifier, records) {
  // Soft-delete in children-first FK order with retry + backoff.
  // Arrays are already passed in children-first order — do NOT reverse.
  // Uses soft-delete (PATCH deleted_at) instead of hard DELETE to match production behavior.
  // Hard-delete is reserved for --clean flag only.
  const maxRetries = 3;
  for (const { table, id } of records) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        await verifier.softDeleteRecord(table, id);
        break; // Success — move to next record
      } catch (e) {
        if (attempt === maxRetries) {
          console.log(`  cleanup: failed to soft-delete ${table}/${id} after ${maxRetries} attempts: ${e.message}`);
        } else {
          await sleep(attempt * 500); // Backoff: 500ms, 1000ms
        }
      }
    }
  }

  // Post-cleanup verification — check records are now soft-deleted
  try {
    for (const { table, id } of records) {
      const remaining = await verifier.getRecord(table, id);
      if (remaining && !remaining.deleted_at) {
        console.log(`  cleanup WARNING: ${table}/${id} still not soft-deleted after cleanup`);
      }
    }
  } catch (e) {
    // Verification is best-effort — don't fail the test over it
  }
}
```

Replace with:
```js
async function cleanup(verifier, records) {
  // Hard-delete in children-first FK order with retry + backoff.
  // Arrays are already passed in children-first order — do NOT reverse.
  // Uses hard DELETE instead of soft-delete (PATCH deleted_at) because the
  // stamp_deleted_by trigger fires on UPDATE and throws when auth.uid() is NULL
  // (service role has no auth.uid()). Hard DELETE bypasses the UPDATE trigger entirely.
  const maxRetries = 3;
  for (const { table, id } of records) {
    if (!id) continue; // Skip records with null IDs (e.g., unresolved assignment IDs)
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        await verifier.deleteRecord(table, id);
        break; // Success — move to next record
      } catch (e) {
        if (attempt === maxRetries) {
          console.log(`  cleanup: failed to delete ${table}/${id} after ${maxRetries} attempts: ${e.message}`);
        } else {
          await sleep(attempt * 500); // Backoff: 500ms, 1000ms
        }
      }
    }
  }
}
```

### Sub-phase 1.4: Remove conflict_log from Supabase verifier allowlist
**Files:** `tools/debug-server/supabase-verifier.js`
**Agent:** general-purpose

#### Step 1.4.1: Remove conflict_log from SYNCED_TABLES

Find this code in `tools/debug-server/supabase-verifier.js`:
```js
const SYNCED_TABLES = new Set([
  'projects', 'project_assignments', 'locations', 'contractors',
  'equipment', 'bid_items', 'personnel_types', 'daily_entries',
  'photos', 'entry_equipment', 'entry_quantities', 'entry_contractors',
  'entry_personnel_counts', 'inspector_forms', 'form_responses',
  'todo_items', 'calculation_history',
  'conflict_log',  // Read-only audit table used by S4 conflict verification
]);
```

Replace with:
```js
const SYNCED_TABLES = new Set([
  'projects', 'project_assignments', 'locations', 'contractors',
  'equipment', 'bid_items', 'personnel_types', 'daily_entries',
  'photos', 'entry_equipment', 'entry_quantities', 'entry_contractors',
  'entry_personnel_counts', 'inspector_forms', 'form_responses',
  'todo_items', 'calculation_history',
  // conflict_log removed — it is a local SQLite table only, not in Supabase
]);
```

---

## Phase 2: Fix L2 S1-S3 Driver-Only Scenarios (Tables Without UI Routes)
### Sub-phase 2.1: Fix S1 push scenarios — add project assignment seeding
**Files:** All S1 scenario files for driver-only tables
**Agent:** general-purpose

Every S1-S3 scenario for these tables needs:
1. Import `seedProjectWithAssignment` from scenario-helpers
2. Get user ID from `process.env.ADMIN_USER_ID`
3. Replace `verifier.insertRecord('projects', project)` with `seedProjectWithAssignment(verifier, project, userId)`
4. Add `{ table: 'project_assignments', id: assignmentId }` to cleanupRecords (BEFORE the projects entry, AFTER all children)
5. For inspector_forms scenarios using the helper: update call to `makeInspectorForm(project.id, ...)` instead of `makeInspectorForm(...)`
6. For inline inspector_forms records: add `project_id: project.id` to the inline object
7. For inline contractor records: add `company_id: process.env.COMPANY_ID` and `deleted_at: null, deleted_by: null`

**Complete file list for S1 scenarios (14 files):**
- `tools/debug-server/scenarios/L2/bid-items-S1-push.js`
- `tools/debug-server/scenarios/L2/contractors-S1-push.js`
- `tools/debug-server/scenarios/L2/equipment-S1-push.js`
- `tools/debug-server/scenarios/L2/locations-S1-push.js`
- `tools/debug-server/scenarios/L2/personnel-types-S1-push.js`
- `tools/debug-server/scenarios/L2/inspector-forms-S1-push.js`
- `tools/debug-server/scenarios/L2/form-responses-S1-push.js`
- `tools/debug-server/scenarios/L2/entry-contractors-S1-push.js`
- `tools/debug-server/scenarios/L2/entry-equipment-S1-push.js`
- `tools/debug-server/scenarios/L2/entry-personnel-counts-S1-push.js`
- `tools/debug-server/scenarios/L2/todo-items-S1-push.js`
- `tools/debug-server/scenarios/L2/calculation-history-S1-push.js`
- `tools/debug-server/scenarios/L2/photos-S1-push.js` (if it exists — check; photos may only have S3)
- `tools/debug-server/scenarios/L2/entry-quantities-S1-push.js` (if it exists)

**NOTE:** `photos-S1-push.js` does NOT exist in the glob results (only S3). `entry-quantities-S1-push.js` DOES exist.

#### Template transformation for S1 scenarios

**BEFORE** (example: bid-items-S1-push.js):
```js
const { step, verify, assertEqual, cleanup, waitFor, makeProject, makeBidItem } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `BidItem Push Project ${Date.now()}` });
  const bidItem = makeBidItem(project.id);
  // ...
  const cleanupRecords = [
    { table: 'bid_items', id: bidItem.id },
    { table: 'projects', id: project.id },
  ];

  try {
    await step('Seed project and sync', async () => {
      await verifier.insertRecord('projects', project);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });
```

**AFTER**:
```js
const { step, verify, assertEqual, cleanup, waitFor, makeProject, makeBidItem, seedProjectWithAssignment } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const userId = process.env.ADMIN_USER_ID || (() => { throw new Error('ADMIN_USER_ID env var required'); })();
  const project = makeProject({ name: `BidItem Push Project ${Date.now()}` });
  const bidItem = makeBidItem(project.id);
  // ...
  let assignmentId;
  const cleanupRecords = [
    { table: 'bid_items', id: bidItem.id },
    { table: 'project_assignments', id: null },  // Updated after seed
    { table: 'projects', id: project.id },
  ];

  try {
    await step('Seed project and sync', async () => {
      assignmentId = await seedProjectWithAssignment(verifier, project, userId);
      cleanupRecords.find(r => r.table === 'project_assignments').id = assignmentId;
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });
```

Apply this pattern to ALL 13 S1 files listed above (excluding photos-S1 which doesn't exist).

**Special cases for S1:**
- `inspector-forms-S1-push.js`: Change `makeInspectorForm({ name: 'SYNCTEST-Original-InspectorForm' })` to `makeInspectorForm(project.id, { name: 'SYNCTEST-Original-InspectorForm' })`. NOTE: this scenario currently has NO project — a project must be added and seeded with assignment. The scenario currently only seeds the form. Add project creation + assignment.
- `form-responses-S1-push.js`: Change `makeInspectorForm()` to `makeInspectorForm(project.id)`. This scenario already has a project.
- `entry-contractors-S1-push.js`: The inline contractor record at line 28-33 needs `company_id: process.env.COMPANY_ID, deleted_at: null, deleted_by: null` added.
- Similarly for any other scenario that creates contractors inline.

### Sub-phase 2.2: Fix S2 update-push scenarios
**Files:** All S2 scenario files for driver-only tables (14 files)
**Agent:** general-purpose

**Complete file list for S2 scenarios:**
- `tools/debug-server/scenarios/L2/bid-items-S2-update-push.js`
- `tools/debug-server/scenarios/L2/contractors-S2-update-push.js`
- `tools/debug-server/scenarios/L2/equipment-S2-update-push.js`
- `tools/debug-server/scenarios/L2/locations-S2-update-push.js`
- `tools/debug-server/scenarios/L2/personnel-types-S2-update-push.js`
- `tools/debug-server/scenarios/L2/inspector-forms-S2-update-push.js`
- `tools/debug-server/scenarios/L2/form-responses-S2-update-push.js`
- `tools/debug-server/scenarios/L2/entry-contractors-S2-update-push.js`
- `tools/debug-server/scenarios/L2/entry-equipment-S2-update-push.js`
- `tools/debug-server/scenarios/L2/entry-personnel-counts-S2-update-push.js`
- `tools/debug-server/scenarios/L2/entry-quantities-S2-update-push.js`
- `tools/debug-server/scenarios/L2/todo-items-S2-update-push.js`
- `tools/debug-server/scenarios/L2/calculation-history-S2-update-push.js`
- `tools/debug-server/scenarios/L2/photos-S2-update-push.js`

Apply the same transformation pattern as S1:
1. Add `seedProjectWithAssignment` to require
2. Add `userId` from `ADMIN_USER_ID`
3. Replace `verifier.insertRecord('projects', project)` with `assignmentId = await seedProjectWithAssignment(verifier, project, userId)`
4. Add `{ table: 'project_assignments', id: null }` to cleanupRecords before projects entry
5. Update assignmentId in cleanupRecords after seed
6. Fix `makeInspectorForm()` calls to `makeInspectorForm(project.id)` where applicable
7. Add `company_id`, `deleted_at`, `deleted_by` to inline contractor records where applicable
8. Add `project_id` to inline inspector_forms records where applicable

**Special cases for S2:**
- `inspector-forms-S2-update-push.js`: Uses `makeInspectorForm()` — needs a project added and call changed to `makeInspectorForm(project.id)`. Currently has no project at all — add project + assignment.
- For any S2 scenario that doesn't currently create a project (inspector-forms-S2 only), add a project + assignment.

### Sub-phase 2.3: Fix S3 delete-push scenarios
**Files:** All S3 scenario files for driver-only tables (14 files)
**Agent:** general-purpose

**Complete file list for S3 scenarios:**
- `tools/debug-server/scenarios/L2/bid-items-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/contractors-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/equipment-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/locations-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/personnel-types-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/inspector-forms-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/form-responses-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/entry-contractors-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/entry-equipment-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/entry-personnel-counts-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/entry-quantities-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/todo-items-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/calculation-history-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/photos-S3-delete-push.js`

Apply the same transformation pattern as S1/S2.

**Special cases for S3:**
- `inspector-forms-S3-delete-push.js`: Uses `makeInspectorForm()` — needs project + assignment. Change to `makeInspectorForm(project.id)`.
- `form-responses-S3-delete-push.js`: Uses `makeInspectorForm()` — already has a project. Change to `makeInspectorForm(project.id)`.

---

## Phase 3: Fix L2 UI-Based Scenarios (projects-S1, daily-entries-S1)
### Sub-phase 3.1: Fix projects-S1-push.js
**Files:** `tools/debug-server/scenarios/L2/projects-S1-push.js`
**Agent:** general-purpose

This scenario creates a project via the UI, so we cannot pre-seed the project or its assignment. The project is created entirely by the app. However, for sync to PUSH the project, the sync engine needs the project to be in scope.

**Analysis:** Actually, looking at the sync engine's `_applyScopeFilter`, projects use `ScopeType.direct` which filters by `company_id`, NOT by `project_assignments`. So projects-S1 does NOT need an assignment — it pushes with company_id scoping. The project will be pushed if the device's company_id matches.

**Fix needed for projects-S1:** Only the cleanup needs fixing — switch from `softDeleteRecord` to `deleteRecord`. The scenario already has custom cleanup that calls `verifier.softDeleteRecord('projects', record.id)` inline.

Find in `tools/debug-server/scenarios/L2/projects-S1-push.js`:
```js
  } finally {
    // Clean up project created via UI (app-assigned ID may differ from pre-generated projectId)
    try {
      const records = await verifier.queryRecords('projects', { project_number: `eq.${projectNumber}` });
      for (const record of records) {
        await verifier.softDeleteRecord('projects', record.id);
      }
    } catch (_) {}
    await cleanup(verifier, cleanupRecords);
  }
```

Replace with:
```js
  } finally {
    // Clean up project created via UI (app-assigned ID may differ from pre-generated projectId)
    try {
      const records = await verifier.queryRecords('projects', { project_number: `eq.${projectNumber}` });
      for (const record of records) {
        await verifier.deleteRecord('projects', record.id);
      }
    } catch (_) {}
    await cleanup(verifier, cleanupRecords);
  }
```

**NOTE:** This scenario will still fail at the UI interaction step (widget keys not attached). That's out of scope for this plan.

### Sub-phase 3.2: Fix daily-entries-S1-push.js
**Files:** `tools/debug-server/scenarios/L2/daily-entries-S1-push.js`
**Agent:** general-purpose

This scenario seeds a project + location, then creates an entry via UI. The project needs an assignment for the sync to pull it to the device (so the UI can navigate to it).

**Fix:** Add `seedProjectWithAssignment` and assignment to cleanupRecords. Replace `verifier.insertRecord('projects', project)` with the helper.

Find in `tools/debug-server/scenarios/L2/daily-entries-S1-push.js`:
```js
const { step, verify, assertEqual, cleanup, waitFor, makeProject, makeLocation } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `SYNCTEST-DailyEntry Push Project ${Date.now()}` });
  const location = makeLocation(project.id, { name: `SYNCTEST-Location-DE-Push-${Date.now()}` });
  // Use a deterministic past date to avoid collision with existing entries (C3 fix)
  const entryDate = '2020-01-15';
  const activityMarker = `SYNCTEST-Push-${Date.now()}`;
  const cleanupRecords = [
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed project + location and sync
    await step('Seed project, location, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });
```

Replace with:
```js
const { step, verify, assertEqual, cleanup, waitFor, makeProject, makeLocation, seedProjectWithAssignment } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const userId = process.env.ADMIN_USER_ID || (() => { throw new Error('ADMIN_USER_ID env var required'); })();
  const project = makeProject({ name: `SYNCTEST-DailyEntry Push Project ${Date.now()}` });
  const location = makeLocation(project.id, { name: `SYNCTEST-Location-DE-Push-${Date.now()}` });
  // Use a deterministic past date to avoid collision with existing entries (C3 fix)
  const entryDate = '2020-01-15';
  const activityMarker = `SYNCTEST-Push-${Date.now()}`;
  let assignmentId;
  const cleanupRecords = [
    { table: 'locations', id: location.id },
    { table: 'project_assignments', id: null },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed project + location and sync
    await step('Seed project, location, and sync', async () => {
      assignmentId = await seedProjectWithAssignment(verifier, project, userId);
      cleanupRecords.find(r => r.table === 'project_assignments').id = assignmentId;
      await verifier.insertRecord('locations', location);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });
```

Also fix the custom cleanup at the end:
```js
  } finally {
    // Clean up daily_entries for this project (entry ID is app-generated, clean up by project)
    try {
      const entries = await verifier.queryRecords('daily_entries', { project_id: `eq.${project.id}` });
      for (const entry of entries) {
        await verifier.softDeleteRecord('daily_entries', entry.id);
      }
    } catch (_) {}
    await cleanup(verifier, cleanupRecords);
  }
```

Replace with:
```js
  } finally {
    // Clean up daily_entries for this project (entry ID is app-generated, clean up by project)
    try {
      const entries = await verifier.queryRecords('daily_entries', { project_id: `eq.${project.id}` });
      for (const entry of entries) {
        await verifier.deleteRecord('daily_entries', entry.id);
      }
    } catch (_) {}
    await cleanup(verifier, cleanupRecords);
  }
```

**NOTE:** This scenario will also still fail at UI interaction. Out of scope.

---

## Phase 4: Fix L2 S4 Conflict Scenarios
### Sub-phase 4.1: Add project assignments and remove conflict_log queries
**Files:** All 17 S4 scenario files
**Agent:** general-purpose

**Complete file list (17 files):**
- `tools/debug-server/scenarios/L2/bid-items-S4-conflict.js`
- `tools/debug-server/scenarios/L2/calculation-history-S4-conflict.js`
- `tools/debug-server/scenarios/L2/contractors-S4-conflict.js`
- `tools/debug-server/scenarios/L2/daily-entries-S4-conflict.js`
- `tools/debug-server/scenarios/L2/entry-contractors-S4-conflict.js`
- `tools/debug-server/scenarios/L2/entry-equipment-S4-conflict.js`
- `tools/debug-server/scenarios/L2/entry-personnel-counts-S4-conflict.js`
- `tools/debug-server/scenarios/L2/entry-quantities-S4-conflict.js`
- `tools/debug-server/scenarios/L2/equipment-S4-conflict.js`
- `tools/debug-server/scenarios/L2/form-responses-S4-conflict.js`
- `tools/debug-server/scenarios/L2/inspector-forms-S4-conflict.js`
- `tools/debug-server/scenarios/L2/locations-S4-conflict.js`
- `tools/debug-server/scenarios/L2/personnel-types-S4-conflict.js`
- `tools/debug-server/scenarios/L2/photos-S4-conflict.js`
- `tools/debug-server/scenarios/L2/project-assignments-S4-conflict.js`
- `tools/debug-server/scenarios/L2/projects-S4-conflict.js`
- `tools/debug-server/scenarios/L2/todo-items-S4-conflict.js`

#### Transformation for each S4 file:

**Change A:** Add `seedProjectWithAssignment` to require, add `userId`, replace project insert with helper, add assignment to cleanupRecords. Same pattern as Phase 2.

**Change B:** Remove ALL `conflict_log` query steps. Every S4 file has two such steps:

Step pattern 1 — "Verify conflict logged":
```js
    await step('Verify conflict logged', async () => {
      const conflicts = await verifier.queryRecords('conflict_log', {
        table_name: `eq.TABLE_NAME`,
        record_id: `eq.${RECORD_ID}`,
      });
      verify(conflicts.length > 0, 'Expected conflict_log entry');
    });
```

Step pattern 2 — "Verify reverse conflict logged":
```js
    await step('Verify reverse conflict logged', async () => {
      const conflicts = await verifier.queryRecords('conflict_log', {
        table_name: `eq.TABLE_NAME`,
        record_id: `eq.${RECORD_ID}`,
      });
      // Should now have at least 2 entries (Phase 1 + Phase 2)
      verify(conflicts.length >= 2, 'Expected at least 2 conflict_log entries (remote-wins + local-wins)');
    });
```

**DELETE both of these steps** from every S4 file. The LWW resolution is already verified by the preceding steps that check the record's final value.

**Special cases for S4:**
- `project-assignments-S4-conflict.js`: Already has correct assignment seeding via `authenticateAs('admin')`. No need to add `seedProjectWithAssignment`. BUT: replace `process.env.TEST_USER_ID` with `process.env.ADMIN_USER_ID` (and error message). Still need to remove conflict_log steps.
- `projects-S4-conflict.js`: Projects use `ScopeType.direct` (company_id), not `viaProject`. May not need assignment. But adding one is safe and consistent. Check this file to confirm — if it already works without assignment, still add for consistency.
- `inspector-forms-S4-conflict.js`: Has inline inspector_forms record — add `project_id: project.id`.
- `form-responses-S4-conflict.js`: Has inline inspector_forms record — add `project_id: project.id`.
- Any S4 with inline contractors: add `company_id: process.env.COMPANY_ID, deleted_at: null, deleted_by: null`.

---

## Phase 5: Fix L2 S5 Fresh-Pull Scenarios
### Sub-phase 5.1: Add project assignments and fix env vars
**Files:** All 17 S5 scenario files
**Agent:** general-purpose

**Complete file list (17 files):**
- `tools/debug-server/scenarios/L2/bid-items-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/calculation-history-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/contractors-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/daily-entries-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/entry-contractors-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/entry-equipment-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/entry-personnel-counts-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/entry-quantities-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/equipment-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/form-responses-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/inspector-forms-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/locations-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/personnel-types-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/photos-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/project-assignments-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/projects-S5-fresh-pull.js`
- `tools/debug-server/scenarios/L2/todo-items-S5-fresh-pull.js`

#### Transformation for each S5 file:

Same as Phase 2 — add `seedProjectWithAssignment`, replace project insert, add assignment to cleanupRecords.

**Special cases for S5:**
- `project-assignments-S5-fresh-pull.js`: Already has correct assignment seeding via `authenticateAs('admin')`. But uses `process.env.TEST_USER_ID` — replace with `process.env.ADMIN_USER_ID` and update error message from `'TEST_USER_ID env var required'` to `'ADMIN_USER_ID env var required'`.
- `inspector-forms-S5-fresh-pull.js`: Has inline inspector_forms record — add `project_id: project.id`.
- Any S5 with inline contractors: add `company_id`, `deleted_at`, `deleted_by`.

---

## Phase 6: Fix L2 Remaining Scenarios (projects-S2, projects-S3, daily-entries-S2, daily-entries-S3)
### Sub-phase 6.1: Fix projects-S2 and projects-S3
**Files:**
- `tools/debug-server/scenarios/L2/projects-S2-update-push.js`
- `tools/debug-server/scenarios/L2/projects-S3-delete-push.js`
**Agent:** general-purpose

Apply the same transformation: add `seedProjectWithAssignment`, replace project insert, add assignment to cleanupRecords.

### Sub-phase 6.2: Fix daily-entries-S2, daily-entries-S3, daily-entries-S4
**Files:**
- `tools/debug-server/scenarios/L2/daily-entries-S2-update-push.js`
- `tools/debug-server/scenarios/L2/daily-entries-S3-delete-push.js`
**Agent:** general-purpose

Apply the same transformation. These scenarios seed projects and dependencies.

**NOTE:** `daily-entries-S4-conflict.js` is already covered in Phase 4.

---

## Phase 7: Fix L3 Multi-Device Scenarios
### Sub-phase 7.1: Fix L3 scenarios that seed via verifier (X2, X3, X4, X5, X6, X7, X9, X10)
**Files:** 8 files
**Agent:** general-purpose

**Complete file list:**
- `tools/debug-server/scenarios/L3/X2-inspector-creates-admin-sees.js`
- `tools/debug-server/scenarios/L3/X3-simultaneous-edit-conflict.js`
- `tools/debug-server/scenarios/L3/X4-admin-deletes-inspector-cascades.js`
- `tools/debug-server/scenarios/L3/X5-inspector-offline-reconnect.js`
- `tools/debug-server/scenarios/L3/X6-offline-conflict-cross-device.js`
- `tools/debug-server/scenarios/L3/X7-photo-offline-sync.js`
- `tools/debug-server/scenarios/L3/X9-rls-admin-visibility.js`
- `tools/debug-server/scenarios/L3/X10-fk-ordering-under-load.js`

#### Transformation:

L3 scenarios use `{ verifier, adminDevice, inspectorDevice }` and need BOTH users assigned.

1. Import `seedProjectWithAssignments` (plural) from scenario-helpers
2. Get both user IDs:
   ```js
   const adminUserId = process.env.ADMIN_USER_ID || (() => { throw new Error('ADMIN_USER_ID env var required'); })();
   const inspectorUserId = process.env.INSPECTOR_USER_ID || (() => { throw new Error('INSPECTOR_USER_ID env var required'); })();
   ```
3. Replace `verifier.insertRecord('projects', project)` with:
   ```js
   const assignmentIds = await seedProjectWithAssignments(verifier, project, [adminUserId, inspectorUserId]);
   ```
4. Add assignment cleanup entries BEFORE projects entry:
   ```js
   { table: 'project_assignments', id: assignmentIds[0] },
   { table: 'project_assignments', id: assignmentIds[1] },
   ```
   Since cleanupRecords is defined before the assignment IDs are known, use the `null` + backfill pattern or restructure to add them after seed.

**Special cases:**
- `X6-offline-conflict-cross-device.js`: Has conflict_log query step — DELETE it (same as Phase 4).
- `X4-admin-deletes-inspector-cascades.js`: Seeds a `todo_items` record inline — add `deleted_at: null, deleted_by: null` to it.
- `X10-fk-ordering-under-load.js`: Uses `makeContractor` and `makeEquipment` — those are already fixed in Phase 1. Also uses `inspectorDevice` only (not adminDevice for data). Needs assignment for inspector user at minimum.

### Sub-phase 7.2: Fix X1 (admin creates via UI) and X8 (RLS, no project seeding)
**Files:**
- `tools/debug-server/scenarios/L3/X1-admin-creates-inspector-pulls.js`
- `tools/debug-server/scenarios/L3/X8-rls-inspector-isolation.js`
**Agent:** general-purpose

#### X1-admin-creates-inspector-pulls.js:
This creates a project via admin UI. The admin's project will be pushed to Supabase, but the inspector needs an assignment to pull it. The challenge: the project ID is unknown until after the admin syncs.

**Fix approach:** After admin creates and syncs (Step 2-3), query Supabase for the project, then seed an assignment for the inspector before the inspector syncs (Step 4).

Find in X1 after "Step 3: Verify on Supabase":
```js
    // Step 3: Verify on Supabase and capture real server-assigned ID
    await step('Verify project in Supabase', async () => {
      const records = await verifier.queryRecords('projects', {
        project_number: `eq.${project.project_number}`,
      });
      verify(records.length > 0, 'Project not found on Supabase');
      // Project was created via admin UI — server may assign a different ID than makeProject()
      cleanupRecords[0].id = records[0].id;
    });

    // Step 4: Inspector syncs on Samsung
    await step('Inspector: Trigger sync', async () => {
```

Replace with:
```js
    // Step 3: Verify on Supabase and capture real server-assigned ID
    let realProjectId;
    await step('Verify project in Supabase', async () => {
      const records = await verifier.queryRecords('projects', {
        project_number: `eq.${project.project_number}`,
      });
      verify(records.length > 0, 'Project not found on Supabase');
      realProjectId = records[0].id;
      cleanupRecords[0].id = realProjectId;
    });

    // Step 3b: Assign inspector to the project so sync pulls it
    await step('Assign inspector to project', async () => {
      const inspectorUserId = process.env.INSPECTOR_USER_ID || (() => { throw new Error('INSPECTOR_USER_ID env var required'); })();
      await verifier.authenticateAs('admin');
      const paId = uuid();
      try {
        await verifier.insertRecord('project_assignments', {
          id: paId,
          project_id: realProjectId,
          user_id: inspectorUserId,
          assigned_by: inspectorUserId,
          company_id: process.env.COMPANY_ID,
          assigned_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
        cleanupRecords.splice(1, 0, { table: 'project_assignments', id: paId });
      } finally {
        verifier.resetAuth();
      }
    });

    // Step 4: Inspector syncs on Samsung
    await step('Inspector: Trigger sync', async () => {
```

Also add `uuid` to the require imports if not already there.

Also fix the cleanup to use `deleteRecord` for the inline `softDeleteRecord` call — but actually X1 uses the standard `cleanup()` function which is already fixed in Phase 1.

#### X8-rls-inspector-isolation.js:
This scenario does NOT seed any projects — it just queries existing data as inspector. No changes needed for project assignment. No cleanup changes needed (no cleanupRecords). **Skip this file — no changes required.**

---

## Phase 8: Fix project-assignments S2, S3, S4 TEST_USER_ID
### Sub-phase 8.1: Fix TEST_USER_ID to ADMIN_USER_ID
**Files:**
- `tools/debug-server/scenarios/L2/project-assignments-S2-update-push.js`
- `tools/debug-server/scenarios/L2/project-assignments-S3-delete-push.js`
- `tools/debug-server/scenarios/L2/project-assignments-S4-conflict.js`
- `tools/debug-server/scenarios/L2/project-assignments-S5-fresh-pull.js`
**Agent:** general-purpose

In all 4 files, find:
```js
  const userId = process.env.TEST_USER_ID || (() => { throw new Error('TEST_USER_ID env var required'); })();
```

Replace with:
```js
  const userId = process.env.ADMIN_USER_ID || (() => { throw new Error('ADMIN_USER_ID env var required'); })();
```

Also in `project-assignments-S4-conflict.js`, remove the two conflict_log steps (already covered conceptually in Phase 4, but listing here since the Phase 4 description focuses on non-assignment S4 files).

---

## Phase 9: Verification
### Sub-phase 9.1: Syntax check all modified files
**Agent:** general-purpose

Run `node -c <file>` on every modified file to verify no syntax errors:

```bash
cd tools/debug-server
node -c scenario-helpers.js
node -c supabase-verifier.js
for f in scenarios/L2/*.js scenarios/L3/*.js; do node -c "$f" || echo "SYNTAX ERROR: $f"; done
```

### Sub-phase 9.2: Dry-run a single scenario
**Agent:** general-purpose

If a device is available, run a single scenario to smoke-test the fixes:

```bash
cd tools/debug-server
node run-tests.js --scenario L2/bid-items-S1-push --device localhost:4948
```

If no device is available, this step is informational only — the syntax check in 9.1 is the minimum gate.

---

## Summary of Changes by File

### Infrastructure (2 files modified):
| File | Changes |
|------|---------|
| `scenario-helpers.js` | Fix 5 make*() helpers (add missing fields), add `seedProjectWithAssignment` + `seedProjectWithAssignments`, switch `cleanup` from soft-delete to hard-delete, update exports |
| `supabase-verifier.js` | Remove `conflict_log` from SYNCED_TABLES allowlist |

### L2 Scenarios (84 files):
| Scenario Type | Count | Changes |
|---------------|-------|---------|
| S1 push | 13 | Add assignment seeding, fix makeInspectorForm callers, fix inline records |
| S2 update | 14 | Add assignment seeding, fix makeInspectorForm callers |
| S3 delete | 14 | Add assignment seeding, fix makeInspectorForm callers |
| S4 conflict | 17 | Add assignment seeding, remove conflict_log queries, fix inline records |
| S5 fresh-pull | 17 | Add assignment seeding, fix TEST_USER_ID |
| projects-S1 | 1 | Fix inline softDeleteRecord to deleteRecord |
| daily-entries-S1 | 1 | Add assignment seeding, fix inline softDeleteRecord |
| projects-S2, S3 | 2 | Add assignment seeding |
| daily-entries-S2, S3 | 2 | Add assignment seeding |
| project-assignments S2-S5 | 4 | Fix TEST_USER_ID to ADMIN_USER_ID, remove conflict_log (S4 only) |

**Note:** Some files appear in multiple categories above. The total unique L2 file count is 84.

### L3 Scenarios (9 files modified, 1 skipped):
| File | Changes |
|------|---------|
| X1 | Add inspector assignment after project creation |
| X2, X3, X4, X5, X7, X9 | Add dual assignments via seedProjectWithAssignments |
| X6 | Add dual assignments + remove conflict_log query |
| X8 | **No changes needed** (no project seeding) |
| X10 | Add assignment for inspector user |

### Files NOT Modified:
- `tools/debug-server/run-tests.js` — no changes needed
- `tools/debug-server/scenarios/L3/X8-rls-inspector-isolation.js` — no project seeding, no cleanup issues
