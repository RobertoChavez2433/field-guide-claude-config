# Sync Verification Scenario Ground Truth Fixes

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Fix all 94 sync verification scenarios with correct routes, keys, column names, and logic from the actual codebase.
**Spec:** N/A — this is a mechanical correction task based on ground-truth verification.
**Analysis:** `.claude/dependency_graphs/2026-03-24-scenario-ground-truth-fixes/analysis.md`

**Architecture:** Fix string literals and rewrite UI-navigation steps to use driver commands for features without standalone routes. All changes in JS scenario files.
**Tech Stack:** JavaScript (Node.js test scenarios)
**Blast Radius:** 95 direct (94 scenarios + 1 helper), 0 dependent, 0 cleanup

---

## Phase 1: Fix scenario-helpers.js

**Agent**: `general-purpose`
**File**: `tools/debug-server/scenario-helpers.js`

### Change 1: Fix makeContractor() type value

The only valid `ContractorType` values in the app are `prime` and `sub`. The current value `general` will fail Supabase insertion.

**Line 188** — change `type: 'general'` to `type: 'prime'`:

```
BEFORE (line 188):
    type: 'general',

AFTER:
    type: 'prime',
```

This single fix propagates to all 24 files that use `makeContractor()` or manually seed contractors with `type: 'general'`.

### Verification

After this change, `grep -r "type: 'general'" tools/debug-server/scenarios/` should still return hits in files that inline the contractor seed (not using the helper). Those are fixed in later phases.

---

## Phase 2: Fix L2 Scenarios — Tables WITH Dedicated Routes

**Agent**: `general-purpose`

These tables have real routes and real widget keys. Fix route paths, key names, and logic.

### Sub-phase 2.1: projects (S1, S2, S3)

#### File: `tools/debug-server/scenarios/L2/projects-S1-push.js`

**Change 1 — Line 16:** Fix route path
```
BEFORE:
      await device.navigate('/projects/create');
AFTER:
      await device.navigate('/project/new');
```

**Change 2 — Line 22:** Fix save button key
```
BEFORE:
      await device.tap('save_project_button');
AFTER:
      await device.tap('project_save_button');
```

Lines 20-21 (`project_name_field`, `project_number_field`) are CORRECT — no change.

#### File: `tools/debug-server/scenarios/L2/projects-S2-update-push.js`

**Change 1 — Line 22:** Fix route path
```
BEFORE:
      await device.navigate(`/projects/${project.id}/edit`);
AFTER:
      await device.navigate(`/project/${project.id}/edit`);
```

**Change 2 — Line 24:** Fix save button key
```
BEFORE:
      await device.tap('save_project_button');
AFTER:
      await device.tap('project_save_button');
```

Line 23 (`project_name_field`) is CORRECT — no change.

#### File: `tools/debug-server/scenarios/L2/projects-S3-delete-push.js`

**FULL REWRITE** — The project delete flow requires a complex 2-step confirmation dialog that is fragile for sync tests. Convert to driver-only soft-delete.

Replace the ENTIRE file content with:

```javascript
// S3: DELETE PUSH — Soft-delete locally, push, verify deleted_at on Supabase
// TABLE: projects
// FROM SPEC: "S3 — Soft-Delete -> Push -> Verify"
// REWRITTEN: Driver-only soft-delete (no UI navigation — delete flow is complex 2-step dialog)

const { uuid, step, verify, cleanup, waitFor, makeProject } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Delete Push ${Date.now()}` });
  const cleanupRecords = [{ table: 'projects', id: project.id }];

  try {
    // Step 1: Create and sync initial record
    await step('Seed and sync initial record', async () => {
      await verifier.insertRecord('projects', project);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Soft-delete locally via driver (bypasses complex 2-step dialog)
    await step('Soft-delete project via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'projects',
        id: project.id,
        data: {
          deleted_at: new Date().toISOString(),
          deleted_by: project.created_by_user_id,
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Step 3: Verify change_log has the update (soft-delete is an UPDATE with deleted_at)
    await step('Verify change_log entry for soft-delete', async () => {
      const log = await device.getChangeLog('projects');
      verify(log.count > 0, 'Expected change_log entry for soft-delete');
    });

    // Step 4: Trigger sync to push the soft-delete
    await step('Trigger sync to push soft-delete', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Delete sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 5: Verify Supabase shows deleted_at and deleted_by
    await step('Verify deleted_at on Supabase', async () => {
      const remote = await verifier.getRecord('projects', project.id);
      verify(remote !== null, 'Record should still exist in Supabase (soft-deleted)');
      verify(remote.deleted_at !== null && remote.deleted_at !== undefined,
        'deleted_at should be set on Supabase');
      verify(remote.deleted_by !== null && remote.deleted_by !== undefined,
        'deleted_by should be set on Supabase');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### Files with NO changes needed in projects:
- `projects-S4-conflict.js` — uses driver commands only, all correct
- `projects-S5-fresh-pull.js` — uses verifier/driver only, all correct

### Sub-phase 2.2: daily-entries (S1, S2, S3)

#### File: `tools/debug-server/scenarios/L2/daily-entries-S1-push.js`

**FULL REWRITE** — The entry wizard requires a date in the route path and uses different widget keys.

Replace the ENTIRE file content with:

```javascript
// S1: PUSH — Create locally via UI, sync, verify in Supabase
// TABLE: daily_entries (location_id nullable, status defaults 'draft', revision_number defaults 0)
// FROM SPEC: "S1 — push scenario for each table"

const { step, verify, assertEqual, cleanup, waitFor, makeProject, makeLocation } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `DailyEntry Push Project ${Date.now()}` });
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

    // Step 2: Create daily entry locally via UI
    // Entry wizard route: /entry/:projectId/:date
    await step('Create daily entry via UI', async () => {
      await device.navigate(`/entry/${project.id}/${entryDate}`);
      await device.enterText('entry_wizard_activities', activityMarker);
      await device.tap('entry_wizard_save_draft');
    });

    // Step 3: Trigger sync
    await step('Trigger sync', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify record reached Supabase with our specific marker
    await step('Verify daily entry in Supabase', async () => {
      const records = await verifier.queryRecords('daily_entries', {
        project_id: `eq.${project.id}`,
        date: `eq.${entryDate}`,
      });
      verify(records.length > 0, `Daily entry not found in Supabase for date=${entryDate}`);
      assertEqual(records[0].project_id, project.id, 'project_id');
      verify(records.some(r => r.activities && r.activities.includes(activityMarker)),
        `Expected activities to contain marker '${activityMarker}'`);
    });

    // Step 5: Verify change_log is cleared
    await step('Verify change_log cleared after sync', async () => {
      await waitFor(async () => {
        const status = await device.getSyncStatus();
        return status.pendingCount === 0;
      }, 'change_log cleared', 10000);
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/daily-entries-S2-update-push.js`

**FULL REWRITE** — Fix route and widget key for entry wizard.

Replace the ENTIRE file content with:

```javascript
// S2: UPDATE PUSH — Update locally, push, verify update in Supabase
// TABLE: daily_entries
// FROM SPEC: "S2 — Update -> Push -> Verify"
// REWRITTEN: Use driver for update (entry wizard submit flow is complex)

const { step, verify, assertEqual, cleanup, makeProject, makeLocation, makeDailyEntry } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `DailyEntry Update Project ${Date.now()}` });
  const location = makeLocation(project.id, { name: `SYNCTEST-Location-DE-Update-${Date.now()}` });
  const entry = makeDailyEntry(project.id, location.id, { status: 'draft', revision_number: 0 });
  const cleanupRecords = [
    { table: 'daily_entries', id: entry.id },
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, location, entry, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      await verifier.insertRecord('daily_entries', entry);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Update daily entry locally via driver
    // (Entry wizard submit flow requires multiple wizard steps — use driver for reliability)
    await step('Update daily entry activities locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'daily_entries',
        id: entry.id,
        data: {
          activities: 'SYNCTEST updated activities',
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push update', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Update sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase has updated activities
    await step('Verify updated daily entry in Supabase', async () => {
      const remote = await verifier.getRecord('daily_entries', entry.id);
      verify(remote !== null, 'Daily entry not found in Supabase');
      assertEqual(remote.activities, 'SYNCTEST updated activities', 'activities after update');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/daily-entries-S3-delete-push.js`

**FULL REWRITE** — Convert to driver-only soft-delete.

Replace the ENTIRE file content with:

```javascript
// S3: DELETE PUSH — Soft-delete locally, push, verify deleted_at on Supabase
// TABLE: daily_entries
// FROM SPEC: "S3 — Soft-Delete -> Push -> Verify"
// REWRITTEN: Driver-only soft-delete (no standalone delete route for entries)

const { step, verify, cleanup, makeProject, makeLocation, makeDailyEntry } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `DailyEntry Delete Project ${Date.now()}` });
  const location = makeLocation(project.id, { name: `SYNCTEST-Location-DE-Delete-${Date.now()}` });
  const entry = makeDailyEntry(project.id, location.id, { status: 'draft', revision_number: 0 });
  const cleanupRecords = [
    { table: 'daily_entries', id: entry.id },
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, location, entry, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      await verifier.insertRecord('daily_entries', entry);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Soft-delete daily entry via driver
    await step('Soft-delete daily entry via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'daily_entries',
        id: entry.id,
        data: {
          deleted_at: new Date().toISOString(),
          deleted_by: entry.created_by_user_id,
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push soft-delete', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Delete sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase shows deleted_at
    await step('Verify deleted_at on Supabase', async () => {
      const remote = await verifier.getRecord('daily_entries', entry.id);
      verify(remote !== null, 'Record should still exist in Supabase (soft-deleted)');
      verify(remote.deleted_at !== null && remote.deleted_at !== undefined,
        'deleted_at should be set on Supabase');
      verify(remote.deleted_by !== null && remote.deleted_by !== undefined,
        'deleted_by should be set on Supabase');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/daily-entries-S4-conflict.js`

**Change 1 — Line 32:** Fix invalid status value. `in_review` is not a valid status for daily_entries. Use `activities` field instead.

```
BEFORE:
        data: { status: 'in_review' },
AFTER:
        data: { activities: 'Local conflict edit' },
```

No other changes needed — the rest uses driver commands and verifier which are correct.

#### File: `tools/debug-server/scenarios/L2/daily-entries-S5-fresh-pull.js`
No changes needed — uses verifier/driver only, all correct.

### Sub-phase 2.3: todo-items (S1, S2, S3)

#### File: `tools/debug-server/scenarios/L2/todo-items-S1-push.js`

**FULL REWRITE** — The todo list is at `/todos` with a FAB button, not a create route.

Replace the ENTIRE file content with:

```javascript
// S1: PUSH — Create locally via UI, sync, verify in Supabase
// TABLE: todo_items (project_id nullable)
// FROM SPEC: "S1 — push scenario for each table"

const { step, verify, assertEqual, cleanup, waitFor, makeProject } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `TodoItems Push Project ${Date.now()}` });
  const todoTitle = `SYNCTEST-Todo-Push-${Date.now()}`;
  const cleanupRecords = [
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed project and sync
    await step('Seed project and sync', async () => {
      await verifier.insertRecord('projects', project);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Create todo item locally via UI
    // Navigate to /todos, tap FAB to open create dialog
    await step('Create todo item via UI', async () => {
      await device.navigate('/todos');
      await device.tap('todos_add_button');
      await device.enterText('todos_title_field', todoTitle);
      await device.tap('todos_save_button');
    });

    // Step 3: Trigger sync
    await step('Trigger sync', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify record reached Supabase
    await step('Verify todo item in Supabase', async () => {
      const records = await verifier.queryRecords('todo_items', {
        title: `eq.${todoTitle}`,
      });
      verify(records.length > 0, `Todo item not found in Supabase with title=${todoTitle}`);
      assertEqual(records[0].is_completed, false, 'is_completed should default to false');
    });

    // Step 5: Verify change_log is cleared
    await step('Verify change_log cleared after sync', async () => {
      await waitFor(async () => {
        const status = await device.getSyncStatus();
        return status.pendingCount === 0;
      }, 'change_log cleared', 10000);
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/todo-items-S2-update-push.js`

**FULL REWRITE** — No individual todo route exists. Convert to driver-only.

Replace the ENTIRE file content with:

```javascript
// S2: UPDATE PUSH — Update locally, push, verify update in Supabase
// TABLE: todo_items (project_id nullable)
// FROM SPEC: "S2 — Update -> Push -> Verify"
// REWRITTEN: Driver-only (no individual todo route exists)

const { uuid, step, verify, assertEqual, cleanup, makeProject } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `TodoItems Update Project ${Date.now()}` });
  const todoId = uuid();
  const cleanupRecords = [
    { table: 'todo_items', id: todoId },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, todo item, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('todo_items', {
        id: todoId,
        title: `SYNCTEST-Todo-Update-${Date.now()}`,
        is_completed: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Mark todo as completed locally via driver
    await step('Mark todo as completed locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'todo_items',
        id: todoId,
        data: { is_completed: 1, updated_at: new Date().toISOString() },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push update', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Update sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase has updated is_completed
    await step('Verify updated todo item in Supabase', async () => {
      const remote = await verifier.getRecord('todo_items', todoId);
      verify(remote !== null, 'Todo item not found in Supabase');
      assertEqual(remote.is_completed, true, 'is_completed after update');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/todo-items-S3-delete-push.js`

**FULL REWRITE** — Convert to driver-only soft-delete.

Replace the ENTIRE file content with:

```javascript
// S3: DELETE PUSH — Soft-delete locally, push, verify deleted_at on Supabase
// TABLE: todo_items (project_id nullable)
// FROM SPEC: "S3 — Soft-Delete -> Push -> Verify"
// REWRITTEN: Driver-only soft-delete (no individual todo route)

const { uuid, step, verify, cleanup, makeProject } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `TodoItems Delete Project ${Date.now()}` });
  const todoId = uuid();
  const cleanupRecords = [
    { table: 'todo_items', id: todoId },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, todo item, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('todo_items', {
        id: todoId,
        title: `SYNCTEST-Todo-Delete-${Date.now()}`,
        is_completed: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Soft-delete todo item via driver
    await step('Soft-delete todo item via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'todo_items',
        id: todoId,
        data: {
          deleted_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push soft-delete', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Delete sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase shows deleted_at
    await step('Verify deleted_at on Supabase', async () => {
      const remote = await verifier.getRecord('todo_items', todoId);
      verify(remote !== null, 'Record should still exist in Supabase (soft-deleted)');
      verify(remote.deleted_at !== null && remote.deleted_at !== undefined,
        'deleted_at should be set on Supabase');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### Files with NO changes needed in todo-items:
- `todo-items-S4-conflict.js` — uses driver commands only, all correct
- `todo-items-S5-fresh-pull.js` — uses verifier/driver only, all correct

### Sub-phase 2.4: calculation-history (S1)

#### File: `tools/debug-server/scenarios/L2/calculation-history-S1-push.js`

**FULL REWRITE** — Calculator route is `/calculator` (no project prefix). Needs input fields filled before calculating.

Replace the ENTIRE file content with:

```javascript
// S1: PUSH — Create locally via UI, sync, verify in Supabase
// TABLE: calculation_history (project_id nullable, input_data/result_data JSON TEXT NOT NULL, notes nullable)
// FROM SPEC: "S1 — push scenario for each table"

const { step, verify, assertEqual, cleanup, waitFor, makeProject } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `CalcHistory Push Project ${Date.now()}` });
  const cleanupRecords = [
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed project and sync
    await step('Seed project and sync', async () => {
      await verifier.insertRecord('projects', project);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Set active project by navigating to project dashboard first (H3 fix)
    // Calculator uses the last-selected project. Must set it before navigating to /calculator.
    await step('Set active project', async () => {
      await device.navigate(`/project/${project.id}`);
    });

    // Step 3: Create calculation history locally via UI
    // Calculator route is /calculator (no project prefix)
    // Use HMA calculator as default test type
    await step('Create calculation history via UI', async () => {
      await device.navigate('/calculator');
      await device.enterText('calculator_hma_area', '100');
      await device.enterText('calculator_hma_thickness', '2');
      await device.enterText('calculator_hma_density', '145');
      await device.tap('calculator_hma_calculate_button');
      await device.tap('calculator_save_button');
    });

    // Step 4: Trigger sync
    await step('Trigger sync', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 5: Verify record reached Supabase
    await step('Verify calculation history in Supabase', async () => {
      const records = await verifier.queryRecords('calculation_history', {
        project_id: `eq.${project.id}`,
      });
      verify(records.length > 0, 'Calculation history not found in Supabase');
    });

    // Step 6: Verify change_log is cleared
    await step('Verify change_log cleared after sync', async () => {
      await waitFor(async () => {
        const status = await device.getSyncStatus();
        return status.pendingCount === 0;
      }, 'change_log cleared', 10000);
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### Files with NO changes needed in calculation-history:
- `calculation-history-S2-update-push.js` — already uses driver commands, all correct
- `calculation-history-S3-delete-push.js` — already uses driver commands, all correct
- `calculation-history-S4-conflict.js` — uses driver commands only, all correct
- `calculation-history-S5-fresh-pull.js` — uses verifier/driver only, all correct

---

## Phase 3: Fix L2 Scenarios — Tables WITHOUT Dedicated Routes (Convert to Driver-Only)

**Agent**: `general-purpose`

These features have NO standalone route. S1 (create), S2 (update), S3 (delete) must be rewritten to use driver commands instead of UI navigation.

**IMPORTANT**: `/driver/create-record` is restricted to junction tables only. For non-junction tables, S1 scenarios use a seed+sync+update pattern: seed on Supabase, sync down, update locally via driver, sync to push, verify update reached Supabase.

### Sub-phase 3.1: locations (S1, S2, S3)

#### File: `tools/debug-server/scenarios/L2/locations-S1-push.js`

**FULL REWRITE:**

```javascript
// S1: PUSH — Seed on Supabase, sync down, update locally via driver, push, verify
// TABLE: locations
// FROM SPEC: "S1 — push scenario for each table"
// REWRITTEN: Driver-only (no standalone route for locations)
// PATTERN: Seed -> pull -> local update -> push -> verify update on Supabase

const { uuid, step, verify, assertEqual, cleanup, waitFor, makeProject, makeLocation } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Location Push Project ${Date.now()}` });
  const locationId = uuid();
  const locationName = `SYNCTEST-Location-Push-${Date.now()}`;
  const cleanupRecords = [
    { table: 'locations', id: locationId },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed project in Supabase and sync
    await step('Seed project and sync', async () => {
      await verifier.insertRecord('projects', project);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Seed location on Supabase with original name
    await step('Seed location on Supabase', async () => {
      await verifier.insertRecord('locations', {
        id: locationId,
        project_id: project.id,
        name: 'SYNCTEST-Original-Name',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    });

    // Step 3: Sync to pull location to device
    await step('Sync to pull location', async () => {
      const result = await device.triggerSync();
      verify(result.success, 'Pull sync failed');
    });

    // Step 4: Update locally to create a change_log entry (tests push path)
    await step('Update location locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'locations',
        id: locationId,
        data: { name: locationName, updated_at: new Date().toISOString() },
      });
    });

    // Step 5: Verify change_log entry exists
    await step('Verify change_log entry exists', async () => {
      const log = await device.getChangeLog('locations');
      verify(log.count > 0, 'Expected at least one change_log entry for locations');
    });

    // Step 6: Trigger sync to push
    await step('Trigger sync', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 7: Verify update reached Supabase
    await step('Verify location update in Supabase', async () => {
      const remote = await verifier.getRecord('locations', locationId);
      verify(remote !== null, 'Location not found in Supabase');
      assertEqual(remote.name, locationName, 'name');
    });

    // Step 8: Verify change_log cleared
    await step('Verify change_log cleared after sync', async () => {
      await waitFor(async () => {
        const status = await device.getSyncStatus();
        return status.pendingCount === 0;
      }, 'change_log cleared', 10000);
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/locations-S2-update-push.js`

**FULL REWRITE:**

```javascript
// S2: UPDATE PUSH — Update locally, push, verify update in Supabase
// TABLE: locations
// FROM SPEC: "S2 — Update -> Push -> Verify"
// REWRITTEN: Driver-only (no standalone route for locations)

const { step, verify, assertEqual, cleanup, makeProject, makeLocation } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Location Update Project ${Date.now()}` });
  const location = makeLocation(project.id, { name: `SYNCTEST-Location-Update-${Date.now()}` });
  const updatedName = `SYNCTEST-Location-Updated-${Date.now()}`;
  const cleanupRecords = [
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, location, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Update location locally via driver
    await step('Update location name locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'locations',
        id: location.id,
        data: { name: updatedName, updated_at: new Date().toISOString() },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push update', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Update sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase has updated name
    await step('Verify updated location in Supabase', async () => {
      const remote = await verifier.getRecord('locations', location.id);
      verify(remote !== null, 'Location not found in Supabase');
      assertEqual(remote.name, updatedName, 'name after update');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/locations-S3-delete-push.js`

**FULL REWRITE:**

```javascript
// S3: DELETE PUSH — Soft-delete locally, push, verify deleted_at on Supabase
// TABLE: locations
// FROM SPEC: "S3 — Soft-Delete -> Push -> Verify"
// REWRITTEN: Driver-only soft-delete (no standalone route for locations)

const { step, verify, cleanup, makeProject, makeLocation } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Location Delete Project ${Date.now()}` });
  const location = makeLocation(project.id, { name: `SYNCTEST-Location-Delete-${Date.now()}` });
  const cleanupRecords = [
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, location, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Soft-delete location via driver
    await step('Soft-delete location via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'locations',
        id: location.id,
        data: {
          deleted_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push soft-delete', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Delete sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase shows deleted_at
    await step('Verify deleted_at on Supabase', async () => {
      const remote = await verifier.getRecord('locations', location.id);
      verify(remote !== null, 'Record should still exist in Supabase (soft-deleted)');
      verify(remote.deleted_at !== null && remote.deleted_at !== undefined,
        'deleted_at should be set on Supabase');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

### Sub-phase 3.2: contractors (S1, S2, S3)

Same pattern as locations. All three files need full rewrites.

#### File: `tools/debug-server/scenarios/L2/contractors-S1-push.js`

**FULL REWRITE:**

```javascript
// S1: PUSH — Seed on Supabase, sync down, update locally via driver, push, verify
// TABLE: contractors
// FROM SPEC: "S1 — push scenario for each table"
// REWRITTEN: Driver-only (no standalone route for contractors)

const { uuid, step, verify, assertEqual, cleanup, waitFor, makeProject, makeContractor } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Contractor Push Project ${Date.now()}` });
  const contractor = makeContractor(project.id, { name: `SYNCTEST-Contractor-Original-${Date.now()}` });
  const updatedName = `SYNCTEST-Contractor-Push-${Date.now()}`;
  const cleanupRecords = [
    { table: 'contractors', id: contractor.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed project and sync
    await step('Seed project and sync', async () => {
      await verifier.insertRecord('projects', project);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Seed contractor on Supabase
    await step('Seed contractor on Supabase', async () => {
      await verifier.insertRecord('contractors', contractor);
    });

    // Step 3: Sync to pull contractor
    await step('Sync to pull contractor', async () => {
      const result = await device.triggerSync();
      verify(result.success, 'Pull sync failed');
    });

    // Step 4: Update locally via driver (tests push path)
    await step('Update contractor locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'contractors',
        id: contractor.id,
        data: { name: updatedName, updated_at: new Date().toISOString() },
      });
    });

    // Step 5: Trigger sync
    await step('Trigger sync', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 6: Verify update reached Supabase
    await step('Verify contractor in Supabase', async () => {
      const remote = await verifier.getRecord('contractors', contractor.id);
      verify(remote !== null, 'Contractor not found in Supabase');
      assertEqual(remote.name, updatedName, 'name');
    });

    // Step 7: Verify change_log cleared
    await step('Verify change_log cleared after sync', async () => {
      await waitFor(async () => {
        const status = await device.getSyncStatus();
        return status.pendingCount === 0;
      }, 'change_log cleared', 10000);
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/contractors-S2-update-push.js`

**FULL REWRITE:**

```javascript
// S2: UPDATE PUSH — Update locally, push, verify update in Supabase
// TABLE: contractors
// FROM SPEC: "S2 — Update -> Push -> Verify"
// REWRITTEN: Driver-only (no standalone route for contractors)

const { uuid, step, verify, assertEqual, cleanup, makeProject } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Contractor Update Project ${Date.now()}` });
  const contractorId = uuid();
  const contractorName = `SYNCTEST-Contractor-Update-${Date.now()}`;
  const updatedName = `SYNCTEST-Contractor-Updated-${Date.now()}`;
  const cleanupRecords = [
    { table: 'contractors', id: contractorId },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, contractor, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('contractors', {
        id: contractorId,
        project_id: project.id,
        name: contractorName,
        type: 'prime',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Update contractor locally via driver
    await step('Update contractor name locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'contractors',
        id: contractorId,
        data: { name: updatedName, updated_at: new Date().toISOString() },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push update', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Update sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase has updated name
    await step('Verify updated contractor in Supabase', async () => {
      const remote = await verifier.getRecord('contractors', contractorId);
      verify(remote !== null, 'Contractor not found in Supabase');
      assertEqual(remote.name, updatedName, 'name after update');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/contractors-S3-delete-push.js`

**FULL REWRITE:**

```javascript
// S3: DELETE PUSH — Soft-delete locally, push, verify deleted_at on Supabase
// TABLE: contractors
// FROM SPEC: "S3 — Soft-Delete -> Push -> Verify"
// REWRITTEN: Driver-only soft-delete (no standalone route for contractors)

const { uuid, step, verify, cleanup, makeProject } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Contractor Delete Project ${Date.now()}` });
  const contractorId = uuid();
  const cleanupRecords = [
    { table: 'contractors', id: contractorId },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, contractor, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('contractors', {
        id: contractorId,
        project_id: project.id,
        name: `SYNCTEST-Contractor-Delete-${Date.now()}`,
        type: 'prime',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Soft-delete contractor via driver
    await step('Soft-delete contractor via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'contractors',
        id: contractorId,
        data: {
          deleted_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push soft-delete', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Delete sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase shows deleted_at
    await step('Verify deleted_at on Supabase', async () => {
      const remote = await verifier.getRecord('contractors', contractorId);
      verify(remote !== null, 'Record should still exist in Supabase (soft-deleted)');
      verify(remote.deleted_at !== null && remote.deleted_at !== undefined,
        'deleted_at should be set on Supabase');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

### Sub-phase 3.3: equipment (S1, S2, S3)

Same pattern as contractors. Equipment FK is `contractor_id`. Must seed project + contractor first.

#### File: `tools/debug-server/scenarios/L2/equipment-S1-push.js`

**FULL REWRITE:**

```javascript
// S1: PUSH — Seed on Supabase, sync down, update locally via driver, push, verify
// TABLE: equipment (deep FK: project -> contractor -> equipment)
// FROM SPEC: "S1 — push scenario for each table"
// REWRITTEN: Driver-only (no standalone route for equipment)

const { uuid, step, verify, assertEqual, cleanup, waitFor, makeProject, makeEquipment } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Equipment Push Project ${Date.now()}` });
  const contractorId = uuid();
  const equipmentId = uuid();
  const updatedName = `SYNCTEST-Equipment-Push-${Date.now()}`;
  const cleanupRecords = [
    { table: 'equipment', id: equipmentId },
    { table: 'contractors', id: contractorId },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed project + contractor and sync
    await step('Seed project, contractor, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('contractors', {
        id: contractorId,
        project_id: project.id,
        name: `SYNCTEST-Contractor-ForEquip-${Date.now()}`,
        type: 'prime',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Seed equipment on Supabase
    await step('Seed equipment on Supabase', async () => {
      await verifier.insertRecord('equipment', {
        id: equipmentId,
        contractor_id: contractorId,
        name: 'SYNCTEST-Equipment-Original',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    });

    // Step 3: Sync to pull equipment
    await step('Sync to pull equipment', async () => {
      const result = await device.triggerSync();
      verify(result.success, 'Pull sync failed');
    });

    // Step 4: Update locally via driver
    await step('Update equipment locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'equipment',
        id: equipmentId,
        data: { name: updatedName, updated_at: new Date().toISOString() },
      });
    });

    // Step 5: Trigger sync
    await step('Trigger sync', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 6: Verify update reached Supabase
    await step('Verify equipment in Supabase', async () => {
      const remote = await verifier.getRecord('equipment', equipmentId);
      verify(remote !== null, 'Equipment not found in Supabase');
      assertEqual(remote.name, updatedName, 'name');
      assertEqual(remote.contractor_id, contractorId, 'contractor_id');
    });

    // Step 7: Verify change_log cleared
    await step('Verify change_log cleared after sync', async () => {
      await waitFor(async () => {
        const status = await device.getSyncStatus();
        return status.pendingCount === 0;
      }, 'change_log cleared', 10000);
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/equipment-S2-update-push.js`

**FULL REWRITE:**

```javascript
// S2: UPDATE PUSH — Update locally, push, verify update in Supabase
// TABLE: equipment (deep FK: project -> contractor -> equipment)
// FROM SPEC: "S2 — Update -> Push -> Verify"
// REWRITTEN: Driver-only (no standalone route for equipment)

const { uuid, step, verify, assertEqual, cleanup, makeProject } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Equipment Update Project ${Date.now()}` });
  const contractorId = uuid();
  const equipmentId = uuid();
  const updatedName = `SYNCTEST-Equipment-Updated-${Date.now()}`;
  const cleanupRecords = [
    { table: 'equipment', id: equipmentId },
    { table: 'contractors', id: contractorId },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, contractor, equipment, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('contractors', {
        id: contractorId,
        project_id: project.id,
        name: `SYNCTEST-Contractor-ForEquip-${Date.now()}`,
        type: 'prime',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      await verifier.insertRecord('equipment', {
        id: equipmentId,
        contractor_id: contractorId,
        name: `SYNCTEST-Equipment-Update-${Date.now()}`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Update equipment locally via driver
    await step('Update equipment name locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'equipment',
        id: equipmentId,
        data: { name: updatedName, updated_at: new Date().toISOString() },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push update', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Update sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase has updated name
    await step('Verify updated equipment in Supabase', async () => {
      const remote = await verifier.getRecord('equipment', equipmentId);
      verify(remote !== null, 'Equipment not found in Supabase');
      assertEqual(remote.name, updatedName, 'name after update');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/equipment-S3-delete-push.js`

**FULL REWRITE:**

```javascript
// S3: DELETE PUSH — Soft-delete locally, push, verify deleted_at on Supabase
// TABLE: equipment (deep FK: project -> contractor -> equipment)
// FROM SPEC: "S3 — Soft-Delete -> Push -> Verify"
// REWRITTEN: Driver-only soft-delete (no standalone route for equipment)

const { uuid, step, verify, cleanup, makeProject } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Equipment Delete Project ${Date.now()}` });
  const contractorId = uuid();
  const equipmentId = uuid();
  const cleanupRecords = [
    { table: 'equipment', id: equipmentId },
    { table: 'contractors', id: contractorId },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, contractor, equipment, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('contractors', {
        id: contractorId,
        project_id: project.id,
        name: `SYNCTEST-Contractor-ForEquip-${Date.now()}`,
        type: 'prime',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      await verifier.insertRecord('equipment', {
        id: equipmentId,
        contractor_id: contractorId,
        name: `SYNCTEST-Equipment-Delete-${Date.now()}`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Soft-delete equipment via driver
    await step('Soft-delete equipment via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'equipment',
        id: equipmentId,
        data: {
          deleted_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push soft-delete', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Delete sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase shows deleted_at
    await step('Verify deleted_at on Supabase', async () => {
      const remote = await verifier.getRecord('equipment', equipmentId);
      verify(remote !== null, 'Record should still exist in Supabase (soft-deleted)');
      verify(remote.deleted_at !== null && remote.deleted_at !== undefined,
        'deleted_at should be set on Supabase');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

### Sub-phase 3.4: bid-items (S1, S2, S3)

Same pattern as locations. Apply identical rewrite pattern (seed+sync+update for S1, driver update for S2, driver soft-delete for S3).

#### File: `tools/debug-server/scenarios/L2/bid-items-S1-push.js`

**FULL REWRITE** — same pattern as locations-S1. Seed bid item on Supabase, sync down, update locally via driver, push, verify. Use `makeBidItem()` helper.

Replace all `device.navigate(...)` / `device.enterText(...)` / `device.tap(...)` blocks with the seed+sync+update pattern:
```javascript
// After seeding project:
const bidItem = makeBidItem(project.id, { item_number: `BID-PUSH-${Date.now().toString(36).toUpperCase()}` });
// Seed on Supabase, sync down, update description locally, push, verify
```

**Complete rewrite file content:**

```javascript
// S1: PUSH — Seed on Supabase, sync down, update locally via driver, push, verify
// TABLE: bid_items
// FROM SPEC: "S1 — push scenario for each table"
// REWRITTEN: Driver-only (no standalone route for bid items)

const { step, verify, assertEqual, cleanup, waitFor, makeProject, makeBidItem } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `BidItem Push Project ${Date.now()}` });
  const bidItem = makeBidItem(project.id);
  const updatedDescription = `SYNCTEST-BidItem-Push-${Date.now()}`;
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

    await step('Seed bid item on Supabase', async () => {
      await verifier.insertRecord('bid_items', bidItem);
    });

    await step('Sync to pull bid item', async () => {
      const result = await device.triggerSync();
      verify(result.success, 'Pull sync failed');
    });

    await step('Update bid item locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'bid_items',
        id: bidItem.id,
        data: { description: updatedDescription, updated_at: new Date().toISOString() },
      });
    });

    await step('Trigger sync', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Sync failed: ${JSON.stringify(result.errors)}`);
    });

    await step('Verify bid item in Supabase', async () => {
      const remote = await verifier.getRecord('bid_items', bidItem.id);
      verify(remote !== null, 'Bid item not found in Supabase');
      assertEqual(remote.description, updatedDescription, 'description');
    });

    await step('Verify change_log cleared after sync', async () => {
      await waitFor(async () => {
        const status = await device.getSyncStatus();
        return status.pendingCount === 0;
      }, 'change_log cleared', 10000);
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/bid-items-S2-update-push.js`

**FULL REWRITE** — Replace UI navigation with driver update:

```javascript
// S2: UPDATE PUSH — Update locally, push, verify update in Supabase
// TABLE: bid_items
// FROM SPEC: "S2 — Update -> Push -> Verify"
// REWRITTEN: Driver-only (no standalone route for bid items)

const { uuid, step, verify, assertEqual, cleanup, makeProject, makeBidItem } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `BidItem Update Project ${Date.now()}` });
  const bidItem = makeBidItem(project.id);
  const updatedDescription = `SYNCTEST-BidItem-Updated-${Date.now()}`;
  const cleanupRecords = [
    { table: 'bid_items', id: bidItem.id },
    { table: 'projects', id: project.id },
  ];

  try {
    await step('Seed project, bid item, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('bid_items', bidItem);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    await step('Update bid item description locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'bid_items',
        id: bidItem.id,
        data: { description: updatedDescription, updated_at: new Date().toISOString() },
      });
    });

    await step('Trigger sync to push update', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Update sync failed: ${JSON.stringify(result.errors)}`);
    });

    await step('Verify updated bid item in Supabase', async () => {
      const remote = await verifier.getRecord('bid_items', bidItem.id);
      verify(remote !== null, 'Bid item not found in Supabase');
      assertEqual(remote.description, updatedDescription, 'description after update');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/bid-items-S3-delete-push.js`

**FULL REWRITE** — Driver-only soft-delete. Same pattern as contractors-S3 but with `makeBidItem()`.

```javascript
// S3: DELETE PUSH — Soft-delete locally, push, verify deleted_at on Supabase
// TABLE: bid_items
// FROM SPEC: "S3 — Soft-Delete -> Push -> Verify"
// REWRITTEN: Driver-only soft-delete (no standalone route for bid items)

const { step, verify, cleanup, makeProject, makeBidItem } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `BidItem Delete Project ${Date.now()}` });
  const bidItem = makeBidItem(project.id);
  const cleanupRecords = [
    { table: 'bid_items', id: bidItem.id },
    { table: 'projects', id: project.id },
  ];

  try {
    await step('Seed project, bid item, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('bid_items', bidItem);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    await step('Soft-delete bid item via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'bid_items',
        id: bidItem.id,
        data: {
          deleted_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    });

    await step('Trigger sync to push soft-delete', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Delete sync failed: ${JSON.stringify(result.errors)}`);
    });

    await step('Verify deleted_at on Supabase', async () => {
      const remote = await verifier.getRecord('bid_items', bidItem.id);
      verify(remote !== null, 'Record should still exist in Supabase (soft-deleted)');
      verify(remote.deleted_at !== null && remote.deleted_at !== undefined,
        'deleted_at should be set on Supabase');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

### Sub-phase 3.5: personnel-types (S1, S2, S3)

Same pattern as locations. Apply identical rewrite pattern using `makePersonnelType()`.

#### File: `tools/debug-server/scenarios/L2/personnel-types-S1-push.js`

**FULL REWRITE:**

```javascript
// S1: PUSH — Seed on Supabase, sync down, update locally via driver, push, verify
// TABLE: personnel_types
// FROM SPEC: "S1 — push scenario for each table"
// REWRITTEN: Driver-only (no standalone route for personnel types)
// PATTERN: Seed -> pull -> local update -> push -> verify update on Supabase

const { uuid, step, verify, assertEqual, cleanup, waitFor, makeProject, makePersonnelType } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `PersonnelType Push Project ${Date.now()}` });
  const typeId = uuid();
  const typeName = `SYNCTEST-PersonnelType-Push-${Date.now()}`;
  const cleanupRecords = [
    { table: 'personnel_types', id: typeId },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed project in Supabase and sync
    await step('Seed project and sync', async () => {
      await verifier.insertRecord('projects', project);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Seed personnel type on Supabase with original name
    await step('Seed personnel type on Supabase', async () => {
      await verifier.insertRecord('personnel_types', {
        id: typeId,
        project_id: project.id,
        name: 'SYNCTEST-Original-PersonnelType',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    });

    // Step 3: Sync to pull personnel type to device
    await step('Sync to pull personnel type', async () => {
      const result = await device.triggerSync();
      verify(result.success, 'Pull sync failed');
    });

    // Step 4: Update locally to create a change_log entry (tests push path)
    await step('Update personnel type locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'personnel_types',
        id: typeId,
        data: { name: typeName, updated_at: new Date().toISOString() },
      });
    });

    // Step 5: Verify change_log entry exists
    await step('Verify change_log entry exists', async () => {
      const log = await device.getChangeLog('personnel_types');
      verify(log.count > 0, 'Expected at least one change_log entry for personnel_types');
    });

    // Step 6: Trigger sync to push
    await step('Trigger sync', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 7: Verify update reached Supabase
    await step('Verify personnel type update in Supabase', async () => {
      const remote = await verifier.getRecord('personnel_types', typeId);
      verify(remote !== null, 'Personnel type not found in Supabase');
      assertEqual(remote.name, typeName, 'name');
    });

    // Step 8: Verify change_log cleared
    await step('Verify change_log cleared after sync', async () => {
      await waitFor(async () => {
        const status = await device.getSyncStatus();
        return status.pendingCount === 0;
      }, 'change_log cleared', 10000);
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/personnel-types-S2-update-push.js`

**FULL REWRITE:**

```javascript
// S2: UPDATE PUSH — Update locally, push, verify update in Supabase
// TABLE: personnel_types
// FROM SPEC: "S2 — Update -> Push -> Verify"
// REWRITTEN: Driver-only (no standalone route for personnel types)

const { step, verify, assertEqual, cleanup, makeProject, makePersonnelType } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `PersonnelType Update Project ${Date.now()}` });
  const personnelType = makePersonnelType(project.id, { name: `SYNCTEST-PersonnelType-Update-${Date.now()}` });
  const updatedName = `SYNCTEST-PersonnelType-Updated-${Date.now()}`;
  const cleanupRecords = [
    { table: 'personnel_types', id: personnelType.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, personnel type, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('personnel_types', personnelType);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Update personnel type locally via driver
    await step('Update personnel type name locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'personnel_types',
        id: personnelType.id,
        data: { name: updatedName, updated_at: new Date().toISOString() },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push update', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Update sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase has updated name
    await step('Verify updated personnel type in Supabase', async () => {
      const remote = await verifier.getRecord('personnel_types', personnelType.id);
      verify(remote !== null, 'Personnel type not found in Supabase');
      assertEqual(remote.name, updatedName, 'name after update');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/personnel-types-S3-delete-push.js`

**FULL REWRITE:**

```javascript
// S3: DELETE PUSH — Soft-delete locally, push, verify deleted_at on Supabase
// TABLE: personnel_types
// FROM SPEC: "S3 — Soft-Delete -> Push -> Verify"
// REWRITTEN: Driver-only soft-delete (no standalone route for personnel types)

const { step, verify, cleanup, makeProject, makePersonnelType } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `PersonnelType Delete Project ${Date.now()}` });
  const personnelType = makePersonnelType(project.id, { name: `SYNCTEST-PersonnelType-Delete-${Date.now()}` });
  const cleanupRecords = [
    { table: 'personnel_types', id: personnelType.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, personnel type, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('personnel_types', personnelType);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Soft-delete personnel type via driver
    await step('Soft-delete personnel type via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'personnel_types',
        id: personnelType.id,
        data: {
          deleted_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push soft-delete', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Delete sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase shows deleted_at
    await step('Verify deleted_at on Supabase', async () => {
      const remote = await verifier.getRecord('personnel_types', personnelType.id);
      verify(remote !== null, 'Record should still exist in Supabase (soft-deleted)');
      verify(remote.deleted_at !== null && remote.deleted_at !== undefined,
        'deleted_at should be set on Supabase');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

### Sub-phase 3.6: inspector-forms (S1, S2, S3)

Same pattern. `inspector_forms` requires `template_path` and `is_builtin`. Use `makeInspectorForm()`.

**NOTE**: `makeInspectorForm(overrides = {})` takes NO positional projectId argument. Pass `project_id` via overrides: `makeInspectorForm({ project_id: project.id })`.

#### File: `tools/debug-server/scenarios/L2/inspector-forms-S1-push.js`

**FULL REWRITE:**

```javascript
// S1: PUSH — Seed on Supabase, sync down, update locally via driver, push, verify
// TABLE: inspector_forms
// FROM SPEC: "S1 — push scenario for each table"
// REWRITTEN: Driver-only (no standalone route for inspector forms)
// PATTERN: Seed -> pull -> local update -> push -> verify update on Supabase

const { uuid, step, verify, assertEqual, cleanup, waitFor, makeProject, makeInspectorForm } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `InspectorForm Push Project ${Date.now()}` });
  const formId = uuid();
  const formName = `SYNCTEST-InspectorForm-Push-${Date.now()}`;
  const cleanupRecords = [
    { table: 'inspector_forms', id: formId },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed project in Supabase and sync
    await step('Seed project and sync', async () => {
      await verifier.insertRecord('projects', project);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Seed inspector form on Supabase with original name
    await step('Seed inspector form on Supabase', async () => {
      await verifier.insertRecord('inspector_forms', {
        id: formId,
        name: 'SYNCTEST-Original-InspectorForm',
        template_path: '/templates/test.json',
        is_builtin: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    });

    // Step 3: Sync to pull inspector form to device
    await step('Sync to pull inspector form', async () => {
      const result = await device.triggerSync();
      verify(result.success, 'Pull sync failed');
    });

    // Step 4: Update locally to create a change_log entry (tests push path)
    await step('Update inspector form locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'inspector_forms',
        id: formId,
        data: { name: formName, updated_at: new Date().toISOString() },
      });
    });

    // Step 5: Verify change_log entry exists
    await step('Verify change_log entry exists', async () => {
      const log = await device.getChangeLog('inspector_forms');
      verify(log.count > 0, 'Expected at least one change_log entry for inspector_forms');
    });

    // Step 6: Trigger sync to push
    await step('Trigger sync', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 7: Verify update reached Supabase
    await step('Verify inspector form update in Supabase', async () => {
      const remote = await verifier.getRecord('inspector_forms', formId);
      verify(remote !== null, 'Inspector form not found in Supabase');
      assertEqual(remote.name, formName, 'name');
    });

    // Step 8: Verify change_log cleared
    await step('Verify change_log cleared after sync', async () => {
      await waitFor(async () => {
        const status = await device.getSyncStatus();
        return status.pendingCount === 0;
      }, 'change_log cleared', 10000);
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/inspector-forms-S2-update-push.js`

**FULL REWRITE:**

```javascript
// S2: UPDATE PUSH — Update locally, push, verify update in Supabase
// TABLE: inspector_forms
// FROM SPEC: "S2 — Update -> Push -> Verify"
// REWRITTEN: Driver-only (no standalone route for inspector forms)

const { step, verify, assertEqual, cleanup, makeProject, makeInspectorForm } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `InspectorForm Update Project ${Date.now()}` });
  const form = makeInspectorForm({ project_id: project.id });
  const updatedName = `SYNCTEST-InspectorForm-Updated-${Date.now()}`;
  const cleanupRecords = [
    { table: 'inspector_forms', id: form.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, inspector form, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('inspector_forms', form);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Update inspector form locally via driver
    await step('Update inspector form name locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'inspector_forms',
        id: form.id,
        data: { name: updatedName, updated_at: new Date().toISOString() },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push update', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Update sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase has updated name
    await step('Verify updated inspector form in Supabase', async () => {
      const remote = await verifier.getRecord('inspector_forms', form.id);
      verify(remote !== null, 'Inspector form not found in Supabase');
      assertEqual(remote.name, updatedName, 'name after update');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/inspector-forms-S3-delete-push.js`

**FULL REWRITE:**

```javascript
// S3: DELETE PUSH — Soft-delete locally, push, verify deleted_at on Supabase
// TABLE: inspector_forms
// FROM SPEC: "S3 — Soft-Delete -> Push -> Verify"
// REWRITTEN: Driver-only soft-delete (no standalone route for inspector forms)

const { step, verify, cleanup, makeProject, makeInspectorForm } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `InspectorForm Delete Project ${Date.now()}` });
  const form = makeInspectorForm({ project_id: project.id });
  const cleanupRecords = [
    { table: 'inspector_forms', id: form.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed and sync
    await step('Seed project, inspector form, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('inspector_forms', form);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Soft-delete inspector form via driver
    await step('Soft-delete inspector form via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'inspector_forms',
        id: form.id,
        data: {
          deleted_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Step 3: Trigger sync
    await step('Trigger sync to push soft-delete', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Delete sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify Supabase shows deleted_at
    await step('Verify deleted_at on Supabase', async () => {
      const remote = await verifier.getRecord('inspector_forms', form.id);
      verify(remote !== null, 'Record should still exist in Supabase (soft-deleted)');
      verify(remote.deleted_at !== null && remote.deleted_at !== undefined,
        'deleted_at should be set on Supabase');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

### Sub-phase 3.7: form-responses (S1, S3)

#### File: `tools/debug-server/scenarios/L2/form-responses-S1-push.js`

**FULL REWRITE** — Same seed+sync+update pattern. Seed all dependencies (project, location, entry, form, form_response) on Supabase, sync, update response_data locally, push, verify.

```javascript
// S1: PUSH — Seed on Supabase, sync down, update locally via driver, push, verify
// TABLE: form_responses
// FROM SPEC: "S1 — push scenario for each table"
// REWRITTEN: Driver-only (no standalone route for form responses)

const { uuid, step, verify, assertEqual, cleanup, waitFor, makeProject, makeLocation, makeDailyEntry, makeInspectorForm, makeFormResponse } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `FormResponse Push Project ${Date.now()}` });
  const location = makeLocation(project.id, { name: `SYNCTEST-Location-FR-Push-${Date.now()}` });
  const entry = makeDailyEntry(project.id, location.id, { status: 'draft', revision_number: 0 });
  const form = makeInspectorForm({ project_id: project.id });  // H2 fix: use helper
  const response = makeFormResponse(project.id, form.id, { entry_id: entry.id });
  const updatedData = '{"field1": "pushed-from-device"}';
  const cleanupRecords = [
    { table: 'form_responses', id: response.id },
    { table: 'daily_entries', id: entry.id },
    { table: 'locations', id: location.id },
    { table: 'inspector_forms', id: form.id },
    { table: 'projects', id: project.id },
  ];

  try {
    await step('Seed all dependencies and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      await verifier.insertRecord('daily_entries', entry);
      await verifier.insertRecord('inspector_forms', form);  // H2 fix: use helper object
      await verifier.insertRecord('form_responses', response);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    await step('Update response_data locally via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'form_responses',
        id: response.id,
        data: { response_data: updatedData, updated_at: new Date().toISOString() },
      });
    });

    await step('Trigger sync', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Sync failed: ${JSON.stringify(result.errors)}`);
    });

    await step('Verify form response in Supabase', async () => {
      const remote = await verifier.getRecord('form_responses', response.id);
      verify(remote !== null, 'Form response not found in Supabase');
      assertEqual(remote.response_data, updatedData, 'response_data');
    });

    await step('Verify change_log cleared after sync', async () => {
      await waitFor(async () => {
        const status = await device.getSyncStatus();
        return status.pendingCount === 0;
      }, 'change_log cleared', 10000);
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

#### File: `tools/debug-server/scenarios/L2/form-responses-S3-delete-push.js`

**Two changes needed:**

1. **Line 37:** Fix `form_type: 'inspector'` -> `form_type: 'inspection'`
2. **Lines 52-55:** Replace UI navigation with driver soft-delete

**FULL REWRITE:**

```javascript
// S3: DELETE PUSH — Soft-delete locally, push, verify deleted_at on Supabase
// TABLE: form_responses
// FROM SPEC: "S3 — Soft-Delete -> Push -> Verify"
// REWRITTEN: Driver-only soft-delete (no standalone route for form responses)

const { uuid, step, verify, cleanup, makeProject, makeLocation, makeDailyEntry, makeInspectorForm, makeFormResponse } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `FormResponse Delete Project ${Date.now()}` });
  const location = makeLocation(project.id, { name: `SYNCTEST-Location-FR-Delete-${Date.now()}` });
  const entry = makeDailyEntry(project.id, location.id, { status: 'draft', revision_number: 0 });
  const form = makeInspectorForm({ project_id: project.id });  // H2 fix: use helper
  const response = makeFormResponse(project.id, form.id, { entry_id: entry.id });
  const cleanupRecords = [
    { table: 'form_responses', id: response.id },
    { table: 'daily_entries', id: entry.id },
    { table: 'locations', id: location.id },
    { table: 'inspector_forms', id: form.id },
    { table: 'projects', id: project.id },
  ];

  try {
    await step('Seed all dependencies and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      await verifier.insertRecord('daily_entries', entry);
      await verifier.insertRecord('inspector_forms', form);  // H2 fix: use helper object
      await verifier.insertRecord('form_responses', response);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    await step('Soft-delete form response via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'form_responses',
        id: response.id,
        data: {
          deleted_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    });

    await step('Trigger sync to push soft-delete', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Delete sync failed: ${JSON.stringify(result.errors)}`);
    });

    await step('Verify deleted_at on Supabase', async () => {
      const remote = await verifier.getRecord('form_responses', response.id);
      verify(remote !== null, 'Record should still exist in Supabase (soft-deleted)');
      verify(remote.deleted_at !== null && remote.deleted_at !== undefined,
        'deleted_at should be set on Supabase');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

### Sub-phase 3.8: photos-S3

#### File: `tools/debug-server/scenarios/L2/photos-S3-delete-push.js`

**FULL REWRITE** — Convert UI navigation to driver soft-delete:

```javascript
// S3: DELETE PUSH — Soft-delete photo locally, push, verify deleted_at on Supabase
// TABLE: photos
// FROM SPEC: "S3 — Soft-Delete -> Push -> Verify"
// REWRITTEN: Driver-only soft-delete (no standalone route for photo deletion)

const { uuid, step, verify, cleanup, makeProject, makeLocation, makeDailyEntry } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Photos Delete Project ${Date.now()}` });
  const location = makeLocation(project.id, { name: `SYNCTEST-Location-Photo-Delete-${Date.now()}` });
  const entry = makeDailyEntry(project.id, location.id, { status: 'draft', revision_number: 0 });
  const photoId = uuid();
  const cleanupRecords = [
    { table: 'photos', id: photoId },
    { table: 'daily_entries', id: entry.id },
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    await step('Seed project, location, entry, photo, and sync', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      await verifier.insertRecord('daily_entries', entry);
      await verifier.insertRecord('photos', {
        id: photoId,
        entry_id: entry.id,
        project_id: project.id,
        file_path: null,  // file_path is stripped before push (H1 fix)
        filename: `SYNCTEST-photo-delete-${Date.now()}.jpg`,
        captured_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    await step('Soft-delete photo via driver', async () => {
      await device._request('POST', '/driver/update-record', {
        table: 'photos',
        id: photoId,
        data: {
          deleted_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    });

    await step('Trigger sync to push soft-delete', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Delete sync failed: ${JSON.stringify(result.errors)}`);
    });

    await step('Verify deleted_at on Supabase', async () => {
      const remote = await verifier.getRecord('photos', photoId);
      verify(remote !== null, 'Record should still exist in Supabase (soft-deleted)');
      verify(remote.deleted_at !== null && remote.deleted_at !== undefined,
        'deleted_at should be set on Supabase');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

---

## Phase 4: Fix L2 S4-Conflict and S5-Fresh-Pull Scenarios with `type: 'general'`

**Agent**: `general-purpose`

These scenarios inline contractor seeds with `type: 'general'` instead of using `makeContractor()`. Fix them all.

### Files needing `type: 'general'` -> `type: 'prime'` (inline seeds, not using makeContractor):

All 24 files identified by grep. After Phase 1 fixes `makeContractor()`, only files that manually seed contractors with `type: 'general'` need fixing. These are the files that do `verifier.insertRecord('contractors', { ... type: 'general' ... })`:

1. `contractors-S2-update-push.js` (already rewritten in Phase 3)
2. `contractors-S3-delete-push.js` (already rewritten in Phase 3)
3. `contractors-S4-conflict.js` — line 23: `type: 'general'` -> `type: 'prime'`
4. `contractors-S5-fresh-pull.js` — line 23: `type: 'general'` -> `type: 'prime'`
5. `equipment-S1-push.js` (already rewritten in Phase 3)
6. `equipment-S2-update-push.js` (already rewritten in Phase 3)
7. `equipment-S3-delete-push.js` (already rewritten in Phase 3)
8. `equipment-S4-conflict.js` — line 24: `type: 'general'` -> `type: 'prime'`
9. `equipment-S5-fresh-pull.js` — line 25: `type: 'general'` -> `type: 'prime'`
10. `entry-contractors-S1-push.js` — find `type: 'general'` and change to `type: 'prime'`
11. `entry-contractors-S2-update-push.js` — find `type: 'general'` and change to `type: 'prime'`
12. `entry-contractors-S3-delete-push.js` — find `type: 'general'` and change to `type: 'prime'`
13. `entry-contractors-S4-conflict.js` — find `type: 'general'` and change to `type: 'prime'`
14. `entry-contractors-S5-fresh-pull.js` — find `type: 'general'` and change to `type: 'prime'`
15. `entry-equipment-S1-push.js` — find `type: 'general'` and change to `type: 'prime'`
16. `entry-equipment-S2-update-push.js` — find `type: 'general'` and change to `type: 'prime'`
17. `entry-equipment-S3-delete-push.js` — find `type: 'general'` and change to `type: 'prime'`
18. `entry-equipment-S4-conflict.js` — find `type: 'general'` and change to `type: 'prime'`
19. `entry-equipment-S5-fresh-pull.js` — find `type: 'general'` and change to `type: 'prime'`
20. `entry-personnel-counts-S1-push.js` — find `type: 'general'` and change to `type: 'prime'`
21. `entry-personnel-counts-S2-update-push.js` — find `type: 'general'` and change to `type: 'prime'`
22. `entry-personnel-counts-S3-delete-push.js` — find `type: 'general'` and change to `type: 'prime'`
23. `entry-personnel-counts-S4-conflict.js` — find `type: 'general'` and change to `type: 'prime'`
24. `entry-personnel-counts-S5-fresh-pull.js` — find `type: 'general'` and change to `type: 'prime'`

**IMPLEMENTATION INSTRUCTION**: For each file listed above that was NOT already rewritten in Phase 3, use a simple find-and-replace: `type: 'general'` -> `type: 'prime'`. These are single-line changes.

### Files needing `form_type: 'inspector'` -> `form_type: 'inspection'`:

1. `form-responses-S2-update-push.js` — line 37: `form_type: 'inspector'` -> `form_type: 'inspection'`
2. `form-responses-S3-delete-push.js` (already rewritten in Phase 3 using `makeFormResponse()` which has correct value)
3. `form-responses-S4-conflict.js` — line 37: `form_type: 'inspector'` -> `form_type: 'inspection'`
4. `form-responses-S5-fresh-pull.js` — line 37: `form_type: 'inspector'` -> `form_type: 'inspection'`

---

## Phase 5: Fix Project-Assignments Scenarios (S2-S5)

**Agent**: `general-purpose`

All 4 project-assignments files call a non-existent RPC `admin_assign_project_member`. Replace with `verifier.insertRecord('project_assignments', ...)`.

### Pattern for all 4 files:

**IMPORTANT (C1 fix):** The `trg_project_assignments_assigned_by` trigger stamps `assigned_by = auth.uid()`. Service role has NULL `auth.uid()`, and `assigned_by` is NOT NULL — so `insertRecord` with service role will fail. You MUST authenticate as admin before inserting.

Replace:
```javascript
await verifier.callRpc('admin_assign_project_member', {
  p_project_id: project.id,
  p_user_id: userId,
  p_company_id: companyId,
  p_assigned_by: userId,
});
```

With:
```javascript
// Authenticate as admin so auth.uid() is non-null for the trigger
await verifier.authenticateAs('admin');
const paId = uuid();
await verifier.insertRecord('project_assignments', {
  id: paId,
  project_id: project.id,
  user_id: userId,
  company_id: companyId,
  assigned_by: userId,
  assigned_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
});
// Query back to get actual ID (triggers may modify)
const assignments = await verifier.queryRecords('project_assignments', {
  project_id: `eq.${project.id}`,
  user_id: `eq.${userId}`,
});
await verifier.resetAuth();
```

Then use `assignments[0].id` as the `assignmentId` for all subsequent operations (replacing the pre-generated `uuid()` assignmentId).

### File: `tools/debug-server/scenarios/L2/project-assignments-S2-update-push.js`

Add `uuid` to the require at line 6 (already there). Replace lines 22-27 with the pattern above. Change `assignmentId` references after the seed step to use the queried ID.

**Key structural change:** The current code generates `assignmentId = uuid()` at line 12 and uses it for `cleanupRecords` and `driver/update-record`. After the fix, `assignmentId` must be set from the query result. Move `cleanupRecords` to be set after the query.

### File: `tools/debug-server/scenarios/L2/project-assignments-S3-delete-push.js`
Same pattern. Replace lines 21-26.

### File: `tools/debug-server/scenarios/L2/project-assignments-S4-conflict.js`
Same pattern. Replace lines 21-26.

### File: `tools/debug-server/scenarios/L2/project-assignments-S5-fresh-pull.js`
Same pattern. Replace lines 20-26.

**IMPLEMENTATION NOTE FOR AGENT**: For each file:
1. Keep `const assignmentId = uuid();` as-is for initial declaration
2. **Before** the `insertRecord`, add: `await verifier.authenticateAs('admin');`
3. Replace the `callRpc` with `insertRecord` using the `assignmentId`
4. After `insertRecord`, add: `const assignments = await verifier.queryRecords('project_assignments', { project_id: \`eq.\${project.id}\`, user_id: \`eq.\${userId}\` }); const realAssignmentId = assignments[0].id;`
5. **After** the query, add: `await verifier.resetAuth();`
6. If `realAssignmentId !== assignmentId`, update `cleanupRecords` and use `realAssignmentId` for subsequent operations
7. Simplify: since we're doing `insertRecord` with our own `id`, triggers unlikely to change it. Just use `assignmentId` directly but still add the query as a safety check.

---

## Phase 6: Fix L3 Scenarios (X1-X10)

**Agent**: `general-purpose`

### File: `tools/debug-server/scenarios/L3/X1-admin-creates-inspector-pulls.js`

**Change 1 — Line 14:** Fix route
```
BEFORE:
      await adminDevice.navigate('/projects/create');
AFTER:
      await adminDevice.navigate('/project/new');
```

**Change 2 — Line 17:** Fix save button key
```
BEFORE:
      await adminDevice.tap('save_project_button');
AFTER:
      await adminDevice.tap('project_save_button');
```

Lines 15-16 (`project_name_field`, `project_number_field`) are CORRECT — no change.

### File: `tools/debug-server/scenarios/L3/X2-inspector-creates-admin-sees.js`

**Change 1 — Line 25:** Fix route (use deterministic past date to avoid collision — C3 fix)
```
BEFORE:
      await inspectorDevice.navigate(`/projects/${project.id}/entries/create`);
AFTER:
      const entryDate = '2020-02-10';
      await inspectorDevice.navigate(`/entry/${project.id}/${entryDate}`);
```

**Change 2 — Line 26:** Fix save button key, add unique marker
```
BEFORE:
      await inspectorDevice.tap('save_entry_button');
AFTER:
      await inspectorDevice.enterText('entry_wizard_activities', `SYNCTEST-X2-${Date.now()}`);
      await inspectorDevice.tap('entry_wizard_save_draft');
```

### File: `tools/debug-server/scenarios/L3/X3-simultaneous-edit-conflict.js`

**FULL REWRITE** — Both admin and inspector edit steps use invented routes and keys. Convert to driver-only for both devices.

Replace lines 27-37 (the two edit steps) with driver commands:

```javascript
    // Step 1: Both devices edit the same entry via driver
    await step('Admin: Edit entry activities via driver', async () => {
      await adminDevice._request('POST', '/driver/update-record', {
        table: 'daily_entries',
        id: entry.id,
        data: { activities: 'Admin edit', updated_at: new Date().toISOString() },
      });
    });

    await step('Inspector: Edit entry activities via driver', async () => {
      await inspectorDevice._request('POST', '/driver/update-record', {
        table: 'daily_entries',
        id: entry.id,
        data: { activities: 'Inspector edit', updated_at: new Date().toISOString() },
      });
    });
```

Rest of the file (sync and verification steps) is correct.

### File: `tools/debug-server/scenarios/L3/X4-admin-deletes-inspector-cascades.js`
**No changes needed** — uses verifier.updateRecord() directly, all column names correct.

### File: `tools/debug-server/scenarios/L3/X5-inspector-offline-reconnect.js`

**Change 1 — Lines 43-44:** Fix route and key (use deterministic past date — C3 fix)
```
BEFORE:
      await inspectorDevice.navigate(`/projects/${project.id}/entries/create`);
      await inspectorDevice.tap('save_entry_button');
AFTER:
      const entryDate = '2020-03-10';
      await inspectorDevice.navigate(`/entry/${project.id}/${entryDate}`);
      await inspectorDevice.enterText('entry_wizard_activities', `SYNCTEST-X5-${Date.now()}`);
      await inspectorDevice.tap('entry_wizard_save_draft');
```

### File: `tools/debug-server/scenarios/L3/X6-offline-conflict-cross-device.js`

**Change 1 — Lines 42-43:** Fix inspector entry route/key (use deterministic past dates — C3 fix)
```
BEFORE:
      await inspectorDevice.navigate(`/projects/${project.id}/entries/create`);
      await inspectorDevice.tap('save_entry_button');
AFTER:
      const entryDate = '2020-04-10';
      await inspectorDevice.navigate(`/entry/${project.id}/${entryDate}`);
      await inspectorDevice.enterText('entry_wizard_activities', `SYNCTEST-X6-inspector-${Date.now()}`);
      await inspectorDevice.tap('entry_wizard_save_draft');
```

**Change 2 — Lines 48-49:** Fix admin entry route/key
```
BEFORE:
      await adminDevice.navigate(`/projects/${project.id}/entries/create`);
      await adminDevice.tap('save_entry_button');
AFTER:
      const adminEntryDate = '2020-04-11';
      await adminDevice.navigate(`/entry/${project.id}/${adminEntryDate}`);
      await adminDevice.enterText('entry_wizard_activities', `SYNCTEST-X6-admin-${Date.now()}`);
      await adminDevice.tap('entry_wizard_save_draft');
```

### File: `tools/debug-server/scenarios/L3/X7-photo-offline-sync.js`
**No changes needed** — uses `/driver/inject-photo-direct` which is a real endpoint. All verifier queries are correct.

### File: `tools/debug-server/scenarios/L3/X8-rls-inspector-isolation.js`
**No changes needed** — uses `verifier.authenticateAs()` and `verifier.resetAuth()` which exist. All column/table references are correct.

### File: `tools/debug-server/scenarios/L3/X9-rls-admin-visibility.js`
**No changes needed** — same as X8, all correct.

### File: `tools/debug-server/scenarios/L3/X10-fk-ordering-under-load.js`

**FULL REWRITE** — Multiple invented routes and keys. Convert ALL UI navigation to driver or verifier seeding.

Replace the ENTIRE file content with:

```javascript
// X10: FK ordering under load — rapid multi-table create + sync
// FROM SPEC: "X10 — all records sync without 23503 FK errors"
// REWRITTEN: All data creation via verifier/driver (no UI navigation for embedded tables)

const { uuid, step, verify, cleanup, makeProject, makeLocation, makeContractor, makeEquipment, makeBidItem, makeDailyEntry } = require('../../scenario-helpers');

async function run({ verifier, adminDevice, inspectorDevice }) {
  const project = makeProject({ name: `X10-FKLoad ${Date.now()}` });
  const location = makeLocation(project.id);
  const contractor = makeContractor(project.id);
  const equipment = makeEquipment(contractor.id);
  const entry = makeDailyEntry(project.id, location.id);
  const bidItem = makeBidItem(project.id);
  const photoId = uuid();

  const cleanupRecords = [
    { table: 'photos', id: photoId },
    { table: 'bid_items', id: bidItem.id },
    { table: 'equipment', id: equipment.id },
    { table: 'daily_entries', id: entry.id },
    { table: 'contractors', id: contractor.id },
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Seed project via verifier, sync to device
    await step('Seed project and pull to inspector device', async () => {
      await verifier.insertRecord('projects', project);
      const result = await inspectorDevice.triggerSync();
      verify(result.success, `Initial sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 2: Seed all dependent records on Supabase
    await step('Seed all dependent records on Supabase', async () => {
      await verifier.insertRecord('locations', location);
      await verifier.insertRecord('contractors', contractor);
      await verifier.insertRecord('equipment', equipment);
      await verifier.insertRecord('daily_entries', entry);
      await verifier.insertRecord('bid_items', bidItem);
    });

    // Step 3: Sync to pull all records
    await step('Sync to pull all records', async () => {
      const result = await inspectorDevice.triggerSync();
      verify(result.success, `Pull sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Create multiple local changes to test FK ordering on push
    await step('Create local changes across multiple tables', async () => {
      // Update each record locally to create change_log entries
      await inspectorDevice._request('POST', '/driver/update-record', {
        table: 'locations', id: location.id,
        data: { name: 'FK Load Location Updated', updated_at: new Date().toISOString() },
      });
      await inspectorDevice._request('POST', '/driver/update-record', {
        table: 'contractors', id: contractor.id,
        data: { name: 'FK Load Contractor Updated', updated_at: new Date().toISOString() },
      });
      await inspectorDevice._request('POST', '/driver/update-record', {
        table: 'equipment', id: equipment.id,
        data: { name: 'FK Load Equipment Updated', updated_at: new Date().toISOString() },
      });
      await inspectorDevice._request('POST', '/driver/update-record', {
        table: 'bid_items', id: bidItem.id,
        data: { description: 'FK Load Bid Item Updated', updated_at: new Date().toISOString() },
      });
    });

    // Step 5: Inject a test photo (tests photo push path)
    await step('Inspector: Inject test photo', async () => {
      await inspectorDevice._request('POST', '/driver/inject-photo-direct', {
        base64Data: '/9j/4AAQSkZJRg==',
        filename: 'fk_load_test.jpg',
        entryId: entry.id,
        projectId: project.id,
      });
    });

    // Step 6: Sync all at once — this tests FK ordering in the sync engine
    await step('Inspector: Trigger sync (all in one batch)', async () => {
      const result = await inspectorDevice.triggerSync();
      verify(result.success, `Batch sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 7: Verify ALL records on Supabase
    await step('Verify all record types on Supabase', async () => {
      const proj = await verifier.getRecord('projects', project.id);
      verify(proj !== null, 'Project should exist on Supabase');

      const locs = await verifier.queryRecords('locations', { project_id: `eq.${project.id}` });
      verify(locs.length > 0, 'Location should exist on Supabase');

      const contractors = await verifier.queryRecords('contractors', { project_id: `eq.${project.id}` });
      verify(contractors.length > 0, 'Contractor should exist on Supabase');

      const entries = await verifier.queryRecords('daily_entries', { project_id: `eq.${project.id}` });
      verify(entries.length > 0, 'Daily entry should exist on Supabase');

      const photos = await verifier.queryRecords('photos', { project_id: `eq.${project.id}` });
      verify(photos.length > 0, 'Photo should exist on Supabase');

      const bidItems = await verifier.queryRecords('bid_items', { project_id: `eq.${project.id}` });
      verify(bidItems.length > 0, 'Bid item should exist on Supabase');

      if (contractors.length > 0) {
        const equip = await verifier.queryRecords('equipment', { contractor_id: `eq.${contractors[0].id}` });
        verify(equip.length > 0, 'Equipment should exist on Supabase');
      }
    });

    // Step 8: Check change_log for zero FK errors
    await step('Verify no FK errors in change_log', async () => {
      const log = await inspectorDevice.getChangeLog();
      const fkErrors = (log.entries || []).filter(
        e => e.error_message && e.error_message.includes('23503'),
      );
      verify(fkErrors.length === 0, `Should have zero 23503 FK errors, found ${fkErrors.length}`);
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

---

## Phase 7: Verification

**Agent**: `qa-testing-agent`

1. Run test runner against projects-S1-push as smoke test:
   ```
   node tools/debug-server/run-tests.js --scenario projects-S1-push
   ```
2. Run all L2 S1-push scenarios
3. Run at least one S3 (soft-delete) smoke test — projects-S3-delete-push is a good candidate since it was fully rewritten
4. Run all L2 S4-conflict scenarios (these were mostly clean)
5. Run L3 X1 and X4 as cross-cutting smoke tests

---

## Summary: Files Changed

### Full rewrites (complete file replacement): 30 files
| File | Reason |
|------|--------|
| projects-S3-delete-push.js | Complex 2-step delete dialog -> driver |
| daily-entries-S1-push.js | Wrong route/keys -> fixed entry wizard route |
| daily-entries-S2-update-push.js | Wrong route/keys -> driver update |
| daily-entries-S3-delete-push.js | Wrong route -> driver soft-delete |
| todo-items-S1-push.js | Wrong route/keys -> /todos + correct keys |
| todo-items-S2-update-push.js | No individual todo route -> driver |
| todo-items-S3-delete-push.js | No individual todo route -> driver |
| calculation-history-S1-push.js | Wrong route/keys -> /calculator + correct keys |
| locations-S1-push.js | No route -> seed+sync+update pattern |
| locations-S2-update-push.js | No route -> driver update |
| locations-S3-delete-push.js | No route -> driver soft-delete |
| contractors-S1-push.js | No route -> seed+sync+update pattern |
| contractors-S2-update-push.js | No route -> driver update + fix type |
| contractors-S3-delete-push.js | No route -> driver soft-delete + fix type |
| equipment-S1-push.js | No route -> seed+sync+update pattern + fix type |
| equipment-S2-update-push.js | No route -> driver update + fix type |
| equipment-S3-delete-push.js | No route -> driver soft-delete + fix type |
| bid-items-S1-push.js | No route -> seed+sync+update pattern |
| bid-items-S2-update-push.js | No route -> driver update |
| bid-items-S3-delete-push.js | No route -> driver soft-delete |
| personnel-types-S1-push.js | No route -> seed+sync+update pattern |
| personnel-types-S2-update-push.js | No route -> driver update |
| personnel-types-S3-delete-push.js | No route -> driver soft-delete |
| inspector-forms-S1-push.js | No route -> seed+sync+update pattern |
| inspector-forms-S2-update-push.js | No route -> driver update |
| inspector-forms-S3-delete-push.js | No route -> driver soft-delete |
| form-responses-S1-push.js | No route -> seed+sync+update pattern |
| form-responses-S3-delete-push.js | No route + fix form_type -> driver |
| photos-S3-delete-push.js | No route -> driver soft-delete |
| X10-fk-ordering-under-load.js | Multiple invented routes -> all driver/verifier |

### Line-level fixes (targeted edits): 35 files
| File | Change |
|------|--------|
| scenario-helpers.js | `type: 'general'` -> `type: 'prime'` (line 188) |
| projects-S1-push.js | Route + key (lines 16, 22) |
| projects-S2-update-push.js | Route + key (lines 22, 24) |
| daily-entries-S4-conflict.js | `status: 'in_review'` -> `activities: 'Local conflict edit'` (line 32) |
| form-responses-S2-update-push.js | `form_type: 'inspector'` -> `form_type: 'inspection'` (line 37) |
| form-responses-S4-conflict.js | `form_type: 'inspector'` -> `form_type: 'inspection'` (line 37) |
| form-responses-S5-fresh-pull.js | `form_type: 'inspector'` -> `form_type: 'inspection'` (line 37) |
| contractors-S4-conflict.js | `type: 'general'` -> `type: 'prime'` (line 23) |
| contractors-S5-fresh-pull.js | `type: 'general'` -> `type: 'prime'` (line 23) |
| equipment-S4-conflict.js | `type: 'general'` -> `type: 'prime'` (line 24) |
| equipment-S5-fresh-pull.js | `type: 'general'` -> `type: 'prime'` (line 25) |
| entry-contractors-S1-push.js | `type: 'general'` -> `type: 'prime'` |
| entry-contractors-S2-update-push.js | `type: 'general'` -> `type: 'prime'` |
| entry-contractors-S3-delete-push.js | `type: 'general'` -> `type: 'prime'` |
| entry-contractors-S4-conflict.js | `type: 'general'` -> `type: 'prime'` |
| entry-contractors-S5-fresh-pull.js | `type: 'general'` -> `type: 'prime'` |
| entry-equipment-S1-push.js | `type: 'general'` -> `type: 'prime'` |
| entry-equipment-S2-update-push.js | `type: 'general'` -> `type: 'prime'` |
| entry-equipment-S3-delete-push.js | `type: 'general'` -> `type: 'prime'` |
| entry-equipment-S4-conflict.js | `type: 'general'` -> `type: 'prime'` |
| entry-equipment-S5-fresh-pull.js | `type: 'general'` -> `type: 'prime'` |
| entry-personnel-counts-S1-push.js | `type: 'general'` -> `type: 'prime'` |
| entry-personnel-counts-S2-update-push.js | `type: 'general'` -> `type: 'prime'` |
| entry-personnel-counts-S3-delete-push.js | `type: 'general'` -> `type: 'prime'` |
| entry-personnel-counts-S4-conflict.js | `type: 'general'` -> `type: 'prime'` |
| entry-personnel-counts-S5-fresh-pull.js | `type: 'general'` -> `type: 'prime'` |
| project-assignments-S2-update-push.js | Replace `callRpc` with `insertRecord` |
| project-assignments-S3-delete-push.js | Replace `callRpc` with `insertRecord` |
| project-assignments-S4-conflict.js | Replace `callRpc` with `insertRecord` |
| project-assignments-S5-fresh-pull.js | Replace `callRpc` with `insertRecord` |
| X1-admin-creates-inspector-pulls.js | Route + key (lines 14, 17) |
| X2-inspector-creates-admin-sees.js | Route + key (lines 25-26) |
| X3-simultaneous-edit-conflict.js | Convert both edit steps to driver |
| X5-inspector-offline-reconnect.js | Route + key (lines 43-44) |
| X6-offline-conflict-cross-device.js | Route + key (lines 42-43, 48-49) |

### Files with NO changes needed: 30 files

Every file below was verified to use correct routes, widget keys, column names, and helper calls. No edits required.

**L2 — S4-conflict and S5-fresh-pull for driver/verifier-only tables (13 files):**
1. `projects-S4-conflict.js`
2. `projects-S5-fresh-pull.js`
3. `daily-entries-S5-fresh-pull.js`
4. `todo-items-S4-conflict.js`
5. `todo-items-S5-fresh-pull.js`
6. `locations-S4-conflict.js`
7. `locations-S5-fresh-pull.js`
8. `bid-items-S4-conflict.js`
9. `bid-items-S5-fresh-pull.js`
10. `personnel-types-S4-conflict.js`
11. `personnel-types-S5-fresh-pull.js`
12. `inspector-forms-S4-conflict.js`
13. `inspector-forms-S5-fresh-pull.js`

**L2 — calculation-history S2-S5 (4 files):**
14. `calculation-history-S2-update-push.js`
15. `calculation-history-S3-delete-push.js`
16. `calculation-history-S4-conflict.js`
17. `calculation-history-S5-fresh-pull.js`

**L2 — photos S1, S2, S4, S5 (4 files):**
18. `photos-S1-push.js`
19. `photos-S2-update-push.js`
20. `photos-S4-conflict.js`
21. `photos-S5-fresh-pull.js`

**L2 — entry-quantities (all 5, no `type:'general'` present) (5 files):**
22. `entry-quantities-S1-push.js`
23. `entry-quantities-S2-update-push.js`
24. `entry-quantities-S3-delete-push.js`
25. `entry-quantities-S4-conflict.js`
26. `entry-quantities-S5-fresh-pull.js`

**L3 — cross-cutting scenarios with correct verifier/driver usage (4 files):**
27. `X4-admin-deletes-inspector-cascades.js`
28. `X7-photo-offline-sync.js`
29. `X8-rls-inspector-isolation.js`
30. `X9-rls-admin-visibility.js`

**Total clean: 30 files.** The originally claimed 35 was wrong and inconsistent. The original incorrectly counted junction table scenarios (entry-contractors, entry-equipment, entry-personnel-counts -- 15 files) as clean despite them needing `type: 'general'` -> `type: 'prime'` fixes. It also miscounted by omitting photos S1/S2 and calc-history S2/S3 which ARE clean. This corrected list is exhaustive.

---

## Agent Routing

| Phase | Agent | Files |
|-------|-------|-------|
| 1 | general-purpose | 1 file |
| 2 | general-purpose | 10 files (3 projects + 3 daily-entries + 3 todo-items + 1 calc) |
| 3 | general-purpose | 21 files (3 each for 7 tables) |
| 4 | general-purpose | 24 type fixes + 3 form_type fixes |
| 5 | general-purpose | 4 project-assignments files |
| 6 | general-purpose | 6 L3 files |
| 7 | qa-testing-agent | Smoke tests |

## Risk Notes

1. **`/driver/create-record` restriction**: Only works for junction tables. Non-junction S1 scenarios use seed+sync+update pattern instead.
2. **Entry date in route**: The `/entry/:projectId/:date` route requires a date parameter. Use deterministic past dates (e.g., `'2020-01-15'`) to avoid collision with existing entries. Each scenario that creates entries should use a distinct date.
3. **Project-assignments triggers**: Supabase triggers may auto-stamp `assigned_by`, `company_id`, `updated_at`. Query after insert to verify actual values.
4. **Calculator widget keys**: `calculator_hma_area`, `calculator_hma_thickness`, `calculator_hma_density`, `calculator_hma_calculate_button`, `calculator_save_button` — these need verification against the actual calculator widget if the smoke test fails.
5. **SEC-002 false positive**: Security review flagged `todo-items-S2` for missing `company_id`, but `todo_items` has no `company_id` column — it uses `project_id`. The inline seed in todo-items-S2 is correct (it seeds `title`, `is_completed`, `created_at`, `updated_at`). `project_id` is nullable per schema. No fix needed.
6. **Inline seeds and NOT NULL fields**: All inline seeds that go through `verifier.insertRecord()` must include all NOT NULL columns for the target table. The helpers (`makeProject`, `makeContractor`, etc.) handle this correctly. When seeding inline (without helpers), verify that `id`, `created_at`, `updated_at`, and any table-specific NOT NULL columns are included.
