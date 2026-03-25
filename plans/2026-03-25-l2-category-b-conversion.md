# L2 Category B Conversion Plan

**Goal**: Fix remaining 73 L2 sync verification failures (21 failing + 52 skipped) by converting 20 Category B verbose scenario files to the shared ctx pattern, fixing photos-S1 endpoint, and fixing project-assignments-S5 UNIQUE constraint.

**Files touched**: 22 JS files in `tools/debug-server/scenarios/L2/`, 1 constant addition in `tools/debug-server/scenario-helpers.js`

**Success criteria**: Full L2 suite 84/84 passing. All scenario files use `{name, description, run({ctx})}` export shape. No scenario creates its own project except `projects-S4/S5`.

---

## Phase 1: Add TEST_JPEG_BASE64 constant to scenario-helpers.js

**Agent**: qa-testing-agent

### Step 1.1: Add constant and export

**File**: `tools/debug-server/scenario-helpers.js`

Add the constant BEFORE the module.exports block (before line 590):

```js
// Minimal valid 1x1 white JPEG for photo injection tests
const TEST_JPEG_BASE64 = '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8AKwA=';
```

Then add `TEST_JPEG_BASE64` to the module.exports object. Change line ~612:

```js
  verifyPulled, waitForSyncClean,
```

to:

```js
  verifyPulled, waitForSyncClean,
  TEST_JPEG_BASE64,
```

---

## Phase 2: Fix photos-S1-push.js (one-off)

**Agent**: qa-testing-agent

### Step 2.1: Complete rewrite of photos-S1-push.js

**File**: `tools/debug-server/scenarios/L2/photos-S1-push.js`

Replace entire file with:

```js
const { makePhoto, seedAndSync, softDeleteAndVerify, waitForSyncComplete, waitForSyncClean, TEST_JPEG_BASE64 } = require('../../scenario-helpers');

module.exports = {
  name: 'photos-S1-push',
  description: 'Inject photo locally via driver, push to Supabase, verify metadata',

  async run({ verifier, device, ctx }) {
    const record = makePhoto(ctx, {
      filename: `SYNCTEST-photo-s1-${Date.now()}.jpg`,
    });

    // Inject photo directly on device (bypasses Supabase — tests push)
    await device._request('POST', '/driver/inject-photo-direct', {
      base64Data: TEST_JPEG_BASE64,
      filename: record.filename,
      entryId: ctx.dailyEntryId,
      projectId: ctx.projectId,
    });

    // Sync pushes the locally-injected photo metadata to Supabase
    await device.triggerSync();
    await waitForSyncComplete(device);

    // Verify metadata arrived on Supabase (photo file may not upload in test mode)
    const rows = await verifier.queryRecords('photos', {
      entry_id: `eq.${ctx.dailyEntryId}`,
      filename: `eq.${record.filename}`,
    });
    if (!rows || rows.length === 0) {
      throw new Error(`Photo not found on Supabase with filename=${record.filename}`);
    }

    // Clean up: soft-delete the pushed photo
    await softDeleteAndVerify(verifier, device, 'photos', rows[0].id);
    await waitForSyncClean(device);
  },
};
```

---

## Phase 3: Fix project-assignments-S5-fresh-pull.js (one-off)

**Agent**: qa-testing-agent

### Step 3.1: Add pre-cleanup for stale UNIQUE constraint violation

**File**: `tools/debug-server/scenarios/L2/project-assignments-S5-fresh-pull.js`

Replace entire file with:

```js
const { makeProjectAssignment, seedAndSync, verifyPulled, waitForSyncComplete, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'project-assignments-S5-fresh-pull',
  description: 'Seed project assignment, sync, remove from device, re-sync, verify restored',

  async run({ verifier, device, ctx }) {
    // Pre-cleanup: remove any stale (ctx.projectId, ctx.adminUserId) assignment
    // that could cause a UNIQUE constraint violation on insert
    const stale = await verifier.queryRecords('project_assignments', {
      project_id: `eq.${ctx.projectId}`,
      user_id: `eq.${ctx.adminUserId}`,
    });
    for (const row of stale) {
      await verifier.deleteRecord('project_assignments', row.id);
    }

    const record = makeProjectAssignment(ctx, { user_id: ctx.adminUserId });
    await verifier.authenticateAs('admin');
    try {
      await seedAndSync(verifier, device, 'project_assignments', record);
    } finally {
      verifier.resetAuth();
    }
    await verifyPulled(device, 'project_assignments', record.id);
    await device.removeLocalRecord('project_assignments', ctx.projectId);
    await device.triggerSync();
    await waitForSyncComplete(device);
    await verifyPulled(device, 'project_assignments', record.id);
    // Clean up via server-side hard-delete (no soft-delete on this table)
    await verifier.deleteRecord('project_assignments', record.id);
    await waitForSyncClean(device);
  },
};
```

---

## Phase 4: Convert S4 files with simple factories (4 files)

**Agent**: qa-testing-agent

These tables have simple factories that take `(projectId, overrides)`. Each S4 creates a scenario-local record using `ctx.projectId` as FK parent.

### Step 4.1: bid-items-S4-conflict.js

**File**: `tools/debug-server/scenarios/L2/bid-items-S4-conflict.js`

Replace entire file with:

```js
const { makeBidItem, seedAndSync, runConflictPhase, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'bid-items-S4-conflict',
  description: 'Bid item conflict resolution: remote-wins then local-wins',

  async run({ verifier, device, ctx }) {
    const record = makeBidItem(ctx.projectId, {
      description: `SYNCTEST-biditem-s4-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'bid_items', record);
    await runConflictPhase(device, verifier, {
      table: 'bid_items', id: record.id, field: 'description',
      localValue: 'SYNCTEST-local-phase1', remoteValue: 'SYNCTEST-remote-phase1',
      expectedWinner: 'remote',
    });
    await runConflictPhase(device, verifier, {
      table: 'bid_items', id: record.id, field: 'description',
      localValue: 'SYNCTEST-local-phase2', remoteValue: 'SYNCTEST-remote-phase2',
      expectedWinner: 'local',
    });
    await softDeleteAndVerify(verifier, device, 'bid_items', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 4.2: locations-S4-conflict.js

**File**: `tools/debug-server/scenarios/L2/locations-S4-conflict.js`

Replace entire file with:

```js
const { makeLocation, seedAndSync, runConflictPhase, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'locations-S4-conflict',
  description: 'Location conflict resolution: remote-wins then local-wins',

  async run({ verifier, device, ctx }) {
    const record = makeLocation(ctx.projectId, {
      name: `SYNCTEST-location-s4-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'locations', record);
    await runConflictPhase(device, verifier, {
      table: 'locations', id: record.id, field: 'name',
      localValue: 'SYNCTEST-local-phase1', remoteValue: 'SYNCTEST-remote-phase1',
      expectedWinner: 'remote',
    });
    await runConflictPhase(device, verifier, {
      table: 'locations', id: record.id, field: 'name',
      localValue: 'SYNCTEST-local-phase2', remoteValue: 'SYNCTEST-remote-phase2',
      expectedWinner: 'local',
    });
    await softDeleteAndVerify(verifier, device, 'locations', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 4.3: personnel-types-S4-conflict.js

**File**: `tools/debug-server/scenarios/L2/personnel-types-S4-conflict.js`

Replace entire file with:

```js
const { makePersonnelType, seedAndSync, runConflictPhase, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'personnel-types-S4-conflict',
  description: 'Personnel type conflict resolution: remote-wins then local-wins',

  async run({ verifier, device, ctx }) {
    const record = makePersonnelType(ctx.projectId, {
      name: `SYNCTEST-personneltype-s4-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'personnel_types', record);
    await runConflictPhase(device, verifier, {
      table: 'personnel_types', id: record.id, field: 'name',
      localValue: 'SYNCTEST-local-phase1', remoteValue: 'SYNCTEST-remote-phase1',
      expectedWinner: 'remote',
    });
    await runConflictPhase(device, verifier, {
      table: 'personnel_types', id: record.id, field: 'name',
      localValue: 'SYNCTEST-local-phase2', remoteValue: 'SYNCTEST-remote-phase2',
      expectedWinner: 'local',
    });
    await softDeleteAndVerify(verifier, device, 'personnel_types', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 4.4: inspector-forms-S4-conflict.js

**File**: `tools/debug-server/scenarios/L2/inspector-forms-S4-conflict.js`

Replace entire file with:

```js
const { makeInspectorForm, seedAndSync, runConflictPhase, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'inspector-forms-S4-conflict',
  description: 'Inspector form conflict resolution: remote-wins then local-wins',

  async run({ verifier, device, ctx }) {
    const record = makeInspectorForm({
      project_id: ctx.projectId,
      name: `SYNCTEST-form-s4-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'inspector_forms', record);
    await runConflictPhase(device, verifier, {
      table: 'inspector_forms', id: record.id, field: 'name',
      localValue: 'SYNCTEST-local-phase1', remoteValue: 'SYNCTEST-remote-phase1',
      expectedWinner: 'remote',
    });
    await runConflictPhase(device, verifier, {
      table: 'inspector_forms', id: record.id, field: 'name',
      localValue: 'SYNCTEST-local-phase2', remoteValue: 'SYNCTEST-remote-phase2',
      expectedWinner: 'local',
    });
    await softDeleteAndVerify(verifier, device, 'inspector_forms', record.id);
    await waitForSyncClean(device);
  },
};
```

---

## Phase 5: Convert S4 files with ctx-based factories (5 files)

**Agent**: qa-testing-agent

These tables have factories that take `(ctx, overrides)` and require FK parents from ctx.

### Step 5.1: calculation-history-S4-conflict.js

**File**: `tools/debug-server/scenarios/L2/calculation-history-S4-conflict.js`

Replace entire file with:

```js
const { makeCalculationHistory, seedAndSync, runConflictPhase, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'calculation-history-S4-conflict',
  description: 'Calculation history conflict resolution: remote-wins then local-wins',

  async run({ verifier, device, ctx }) {
    const record = makeCalculationHistory(ctx, {
      notes: `SYNCTEST-calc-s4-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'calculation_history', record);
    await runConflictPhase(device, verifier, {
      table: 'calculation_history', id: record.id, field: 'notes',
      localValue: 'SYNCTEST-local-phase1', remoteValue: 'SYNCTEST-remote-phase1',
      expectedWinner: 'remote',
    });
    await runConflictPhase(device, verifier, {
      table: 'calculation_history', id: record.id, field: 'notes',
      localValue: 'SYNCTEST-local-phase2', remoteValue: 'SYNCTEST-remote-phase2',
      expectedWinner: 'local',
    });
    await softDeleteAndVerify(verifier, device, 'calculation_history', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 5.2: todo-items-S4-conflict.js

**File**: `tools/debug-server/scenarios/L2/todo-items-S4-conflict.js`

Replace entire file with:

```js
const { makeTodoItem, seedAndSync, runConflictPhase, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'todo-items-S4-conflict',
  description: 'Todo item conflict resolution: remote-wins then local-wins',

  async run({ verifier, device, ctx }) {
    const record = makeTodoItem(ctx, {
      title: `SYNCTEST-todo-s4-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'todo_items', record);
    await runConflictPhase(device, verifier, {
      table: 'todo_items', id: record.id, field: 'title',
      localValue: 'SYNCTEST-local-phase1', remoteValue: 'SYNCTEST-remote-phase1',
      expectedWinner: 'remote',
    });
    await runConflictPhase(device, verifier, {
      table: 'todo_items', id: record.id, field: 'title',
      localValue: 'SYNCTEST-local-phase2', remoteValue: 'SYNCTEST-remote-phase2',
      expectedWinner: 'local',
    });
    await softDeleteAndVerify(verifier, device, 'todo_items', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 5.3: photos-S4-conflict.js

**File**: `tools/debug-server/scenarios/L2/photos-S4-conflict.js`

Replace entire file with:

```js
const { makePhoto, seedAndSync, runConflictPhase, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'photos-S4-conflict',
  description: 'Photo conflict resolution: remote-wins then local-wins',

  async run({ verifier, device, ctx }) {
    const record = makePhoto(ctx, {
      filename: `SYNCTEST-photo-s4-${Date.now()}.jpg`,
    });
    await seedAndSync(verifier, device, 'photos', record);
    await runConflictPhase(device, verifier, {
      table: 'photos', id: record.id, field: 'filename',
      localValue: 'SYNCTEST-local-phase1.jpg', remoteValue: 'SYNCTEST-remote-phase1.jpg',
      expectedWinner: 'remote',
    });
    await runConflictPhase(device, verifier, {
      table: 'photos', id: record.id, field: 'filename',
      localValue: 'SYNCTEST-local-phase2.jpg', remoteValue: 'SYNCTEST-remote-phase2.jpg',
      expectedWinner: 'local',
    });
    await softDeleteAndVerify(verifier, device, 'photos', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 5.4: entry-quantities-S4-conflict.js

**File**: `tools/debug-server/scenarios/L2/entry-quantities-S4-conflict.js`

Replace entire file with:

```js
const { makeEntryQuantity, seedAndSync, runConflictPhase, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'entry-quantities-S4-conflict',
  description: 'Entry quantity conflict resolution: remote-wins then local-wins',

  async run({ verifier, device, ctx }) {
    const record = makeEntryQuantity(ctx, {
      quantity: 10.0,
    });
    await seedAndSync(verifier, device, 'entry_quantities', record);
    await runConflictPhase(device, verifier, {
      table: 'entry_quantities', id: record.id, field: 'quantity',
      localValue: 999.0, remoteValue: 99.0,
      expectedWinner: 'remote',
    });
    await runConflictPhase(device, verifier, {
      table: 'entry_quantities', id: record.id, field: 'quantity',
      localValue: 888.0, remoteValue: 1.0,
      expectedWinner: 'local',
    });
    await softDeleteAndVerify(verifier, device, 'entry_quantities', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 5.5: projects-S4-conflict.js (SPECIAL: scenario-local project)

**File**: `tools/debug-server/scenarios/L2/projects-S4-conflict.js`

Replace entire file with:

```js
const { makeProject, makeProjectAssignment, runConflictPhase, waitForSyncComplete, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'projects-S4-conflict',
  description: 'Project conflict resolution: remote-wins then local-wins',

  async run({ verifier, device, ctx }) {
    const project = makeProject({
      userId: ctx.inspectorUserId,
      name: `SYNCTEST-project-s4-${Date.now()}`,
    });
    const assignment = makeProjectAssignment(ctx, {
      project_id: project.id,
      user_id: ctx.inspectorUserId,
    });

    try {
      // Seed project + assignment so device can sync it
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('project_assignments', assignment);
      await device.triggerSync();
      await waitForSyncComplete(device);

      await runConflictPhase(device, verifier, {
        table: 'projects', id: project.id, field: 'name',
        localValue: 'SYNCTEST-local-phase1', remoteValue: 'SYNCTEST-remote-phase1',
        expectedWinner: 'remote',
      });
      await runConflictPhase(device, verifier, {
        table: 'projects', id: project.id, field: 'name',
        localValue: 'SYNCTEST-local-phase2', remoteValue: 'SYNCTEST-remote-phase2',
        expectedWinner: 'local',
      });
      await waitForSyncClean(device);
    } finally {
      // Hard-delete assignment first (FK constraint), then project
      await verifier.deleteRecord('project_assignments', assignment.id);
      await verifier.deleteRecord('projects', project.id);
    }
  },
};
```

---

## Phase 6: Convert all S5 files (9 files)

**Agent**: qa-testing-agent

ALL S5 files create scenario-local records, seed to Supabase via `seedAndSync`, then test remove-from-device + re-sync pull.

### Step 6.1: bid-items-S5-fresh-pull.js

**File**: `tools/debug-server/scenarios/L2/bid-items-S5-fresh-pull.js`

Replace entire file with:

```js
const { makeBidItem, seedAndSync, verifyPulled, softDeleteAndVerify, waitForSyncComplete, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'bid-items-S5-fresh-pull',
  description: 'Seed bid item, sync, remove from device, re-sync, verify restored',

  async run({ verifier, device, ctx }) {
    const record = makeBidItem(ctx.projectId, {
      description: `SYNCTEST-biditem-s5-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'bid_items', record);
    await verifyPulled(device, 'bid_items', record.id);
    await device.removeLocalRecord('bid_items', ctx.projectId);
    await device.triggerSync();
    await waitForSyncComplete(device);
    await verifyPulled(device, 'bid_items', record.id);
    await softDeleteAndVerify(verifier, device, 'bid_items', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 6.2: calculation-history-S5-fresh-pull.js

**File**: `tools/debug-server/scenarios/L2/calculation-history-S5-fresh-pull.js`

Replace entire file with:

```js
const { makeCalculationHistory, seedAndSync, verifyPulled, softDeleteAndVerify, waitForSyncComplete, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'calculation-history-S5-fresh-pull',
  description: 'Seed calculation history, sync, remove from device, re-sync, verify restored',

  async run({ verifier, device, ctx }) {
    const record = makeCalculationHistory(ctx, {
      notes: `SYNCTEST-calc-s5-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'calculation_history', record);
    await verifyPulled(device, 'calculation_history', record.id);
    await device.removeLocalRecord('calculation_history', ctx.projectId);
    await device.triggerSync();
    await waitForSyncComplete(device);
    await verifyPulled(device, 'calculation_history', record.id);
    await softDeleteAndVerify(verifier, device, 'calculation_history', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 6.3: locations-S5-fresh-pull.js

**File**: `tools/debug-server/scenarios/L2/locations-S5-fresh-pull.js`

Replace entire file with:

```js
const { makeLocation, seedAndSync, verifyPulled, softDeleteAndVerify, waitForSyncComplete, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'locations-S5-fresh-pull',
  description: 'Seed location, sync, remove from device, re-sync, verify restored',

  async run({ verifier, device, ctx }) {
    const record = makeLocation(ctx.projectId, {
      name: `SYNCTEST-location-s5-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'locations', record);
    await verifyPulled(device, 'locations', record.id);
    await device.removeLocalRecord('locations', ctx.projectId);
    await device.triggerSync();
    await waitForSyncComplete(device);
    await verifyPulled(device, 'locations', record.id);
    await softDeleteAndVerify(verifier, device, 'locations', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 6.4: personnel-types-S5-fresh-pull.js

**File**: `tools/debug-server/scenarios/L2/personnel-types-S5-fresh-pull.js`

Replace entire file with:

```js
const { makePersonnelType, seedAndSync, verifyPulled, softDeleteAndVerify, waitForSyncComplete, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'personnel-types-S5-fresh-pull',
  description: 'Seed personnel type, sync, remove from device, re-sync, verify restored',

  async run({ verifier, device, ctx }) {
    const record = makePersonnelType(ctx.projectId, {
      name: `SYNCTEST-personneltype-s5-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'personnel_types', record);
    await verifyPulled(device, 'personnel_types', record.id);
    await device.removeLocalRecord('personnel_types', ctx.projectId);
    await device.triggerSync();
    await waitForSyncComplete(device);
    await verifyPulled(device, 'personnel_types', record.id);
    await softDeleteAndVerify(verifier, device, 'personnel_types', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 6.5: todo-items-S5-fresh-pull.js

**File**: `tools/debug-server/scenarios/L2/todo-items-S5-fresh-pull.js`

Replace entire file with:

```js
const { makeTodoItem, seedAndSync, verifyPulled, softDeleteAndVerify, waitForSyncComplete, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'todo-items-S5-fresh-pull',
  description: 'Seed todo item, sync, remove from device, re-sync, verify restored',

  async run({ verifier, device, ctx }) {
    const record = makeTodoItem(ctx, {
      title: `SYNCTEST-todo-s5-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'todo_items', record);
    await verifyPulled(device, 'todo_items', record.id);
    await device.removeLocalRecord('todo_items', ctx.projectId);
    await device.triggerSync();
    await waitForSyncComplete(device);
    await verifyPulled(device, 'todo_items', record.id);
    await softDeleteAndVerify(verifier, device, 'todo_items', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 6.6: photos-S5-fresh-pull.js

**File**: `tools/debug-server/scenarios/L2/photos-S5-fresh-pull.js`

Replace entire file with:

```js
const { makePhoto, seedAndSync, verifyPulled, softDeleteAndVerify, waitForSyncComplete, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'photos-S5-fresh-pull',
  description: 'Seed photo, sync, remove from device, re-sync, verify restored',

  async run({ verifier, device, ctx }) {
    const record = makePhoto(ctx, {
      filename: `SYNCTEST-photo-s5-${Date.now()}.jpg`,
    });
    await seedAndSync(verifier, device, 'photos', record);
    await verifyPulled(device, 'photos', record.id);
    await device.removeLocalRecord('photos', ctx.projectId);
    await device.triggerSync();
    await waitForSyncComplete(device);
    await verifyPulled(device, 'photos', record.id);
    await softDeleteAndVerify(verifier, device, 'photos', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 6.7: inspector-forms-S5-fresh-pull.js

**File**: `tools/debug-server/scenarios/L2/inspector-forms-S5-fresh-pull.js`

Replace entire file with:

```js
const { makeInspectorForm, seedAndSync, verifyPulled, softDeleteAndVerify, waitForSyncComplete, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'inspector-forms-S5-fresh-pull',
  description: 'Seed inspector form, sync, remove from device, re-sync, verify restored',

  async run({ verifier, device, ctx }) {
    const record = makeInspectorForm({
      project_id: ctx.projectId,
      name: `SYNCTEST-form-s5-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'inspector_forms', record);
    await verifyPulled(device, 'inspector_forms', record.id);
    await device.removeLocalRecord('inspector_forms', ctx.projectId);
    await device.triggerSync();
    await waitForSyncComplete(device);
    await verifyPulled(device, 'inspector_forms', record.id);
    await softDeleteAndVerify(verifier, device, 'inspector_forms', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 6.8: entry-quantities-S5-fresh-pull.js

**File**: `tools/debug-server/scenarios/L2/entry-quantities-S5-fresh-pull.js`

Replace entire file with:

```js
const { makeEntryQuantity, seedAndSync, verifyPulled, softDeleteAndVerify, waitForSyncComplete, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'entry-quantities-S5-fresh-pull',
  description: 'Seed entry quantity, sync, remove from device, re-sync, verify restored',

  async run({ verifier, device, ctx }) {
    const record = makeEntryQuantity(ctx, {
      quantity: 42.0,
    });
    await seedAndSync(verifier, device, 'entry_quantities', record);
    await verifyPulled(device, 'entry_quantities', record.id);
    await device.removeLocalRecord('entry_quantities', ctx.projectId);
    await device.triggerSync();
    await waitForSyncComplete(device);
    await verifyPulled(device, 'entry_quantities', record.id);
    await softDeleteAndVerify(verifier, device, 'entry_quantities', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 6.9: projects-S5-fresh-pull.js (SPECIAL: scenario-local project)

**File**: `tools/debug-server/scenarios/L2/projects-S5-fresh-pull.js`

Replace entire file with:

```js
const { makeProject, makeProjectAssignment, verifyPulled, waitForSyncComplete, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'projects-S5-fresh-pull',
  description: 'Seed project, sync, remove from device, re-sync, verify restored',

  async run({ verifier, device, ctx }) {
    const project = makeProject({
      userId: ctx.inspectorUserId,
      name: `SYNCTEST-project-s5-${Date.now()}`,
    });
    const assignment = makeProjectAssignment(ctx, {
      project_id: project.id,
      user_id: ctx.inspectorUserId,
    });

    try {
      // Seed project + assignment so device can sync it
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('project_assignments', assignment);
      await device.triggerSync();
      await waitForSyncComplete(device);

      await verifyPulled(device, 'projects', project.id);

      // Remove from device, re-sync, verify restored
      await device.removeLocalRecord('projects', project.id);
      await device.triggerSync();
      await waitForSyncComplete(device);
      await verifyPulled(device, 'projects', project.id);

      await waitForSyncClean(device);
    } finally {
      // Hard-delete assignment first (FK constraint), then project
      await verifier.deleteRecord('project_assignments', assignment.id);
      await verifier.deleteRecord('projects', project.id);
    }
  },
};
```

---

## Phase 7: Convert calculation-history S2/S3 (2 files)

**Agent**: qa-testing-agent

### Step 7.1: calculation-history-S2-update-push.js

**File**: `tools/debug-server/scenarios/L2/calculation-history-S2-update-push.js`

Replace entire file with:

```js
const { makeCalculationHistory, seedAndSync, softDeleteAndVerify, waitForSyncComplete, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'calculation-history-S2-update-push',
  description: 'Update calculation history locally, push to Supabase, verify update',

  async run({ verifier, device, ctx }) {
    const record = makeCalculationHistory(ctx, {
      notes: `SYNCTEST-calc-s2-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'calculation_history', record);

    // Update notes locally via driver, then push
    const updatedNotes = `SYNCTEST-calc-s2-updated-${Date.now()}`;
    await device.updateRecord('calculation_history', record.id, { notes: updatedNotes });
    await device.triggerSync();
    await waitForSyncComplete(device);

    // Verify update reached Supabase
    const remote = await verifier.getRecord('calculation_history', record.id);
    if (!remote) throw new Error('Calculation history not found on Supabase after update push');
    if (remote.notes !== updatedNotes) {
      throw new Error(`Notes mismatch: expected "${updatedNotes}", got "${remote.notes}"`);
    }

    // Clean up
    await softDeleteAndVerify(verifier, device, 'calculation_history', record.id);
    await waitForSyncClean(device);
  },
};
```

### Step 7.2: calculation-history-S3-delete-push.js

**File**: `tools/debug-server/scenarios/L2/calculation-history-S3-delete-push.js`

Replace entire file with:

```js
const { makeCalculationHistory, seedAndSync, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'calculation-history-S3-delete-push',
  description: 'Soft-delete calculation history locally, push to Supabase, verify deleted_at',

  async run({ verifier, device, ctx }) {
    const record = makeCalculationHistory(ctx, {
      notes: `SYNCTEST-calc-s3-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'calculation_history', record);

    // softDeleteAndVerify: sets deleted_at on device, syncs, verifies deleted_at on Supabase
    await softDeleteAndVerify(verifier, device, 'calculation_history', record.id);
    await waitForSyncClean(device);
  },
};
```

---

## Verification

After all phases, run the full L2 suite:

```bash
node tools/debug-server/run-tests.js --level L2
```

Expected: **84/84 passing**, 0 failing, 0 skipped.

---

## File Summary

| Phase | File | Change |
|-------|------|--------|
| 1 | `scenario-helpers.js` | Add `TEST_JPEG_BASE64` constant + export |
| 2 | `photos-S1-push.js` | Full rewrite: inject-photo-direct + ctx pattern |
| 3 | `project-assignments-S5-fresh-pull.js` | Add pre-cleanup for UNIQUE constraint |
| 4 | `bid-items-S4-conflict.js` | Convert to ctx + runConflictPhase pattern |
| 4 | `locations-S4-conflict.js` | Convert to ctx + runConflictPhase pattern |
| 4 | `personnel-types-S4-conflict.js` | Convert to ctx + runConflictPhase pattern |
| 4 | `inspector-forms-S4-conflict.js` | Convert to ctx + runConflictPhase pattern |
| 5 | `calculation-history-S4-conflict.js` | Convert to ctx + runConflictPhase pattern |
| 5 | `todo-items-S4-conflict.js` | Convert to ctx + runConflictPhase pattern |
| 5 | `photos-S4-conflict.js` | Convert to ctx + runConflictPhase pattern |
| 5 | `entry-quantities-S4-conflict.js` | Convert to ctx + runConflictPhase pattern |
| 5 | `projects-S4-conflict.js` | Scenario-local project + try/finally cleanup |
| 6 | `bid-items-S5-fresh-pull.js` | Convert to ctx + seedAndSync/verifyPulled pattern |
| 6 | `calculation-history-S5-fresh-pull.js` | Convert to ctx + seedAndSync/verifyPulled pattern |
| 6 | `locations-S5-fresh-pull.js` | Convert to ctx + seedAndSync/verifyPulled pattern |
| 6 | `personnel-types-S5-fresh-pull.js` | Convert to ctx + seedAndSync/verifyPulled pattern |
| 6 | `todo-items-S5-fresh-pull.js` | Convert to ctx + seedAndSync/verifyPulled pattern |
| 6 | `photos-S5-fresh-pull.js` | Convert to ctx + seedAndSync/verifyPulled pattern |
| 6 | `inspector-forms-S5-fresh-pull.js` | Convert to ctx + seedAndSync/verifyPulled pattern |
| 6 | `entry-quantities-S5-fresh-pull.js` | Convert to ctx + seedAndSync/verifyPulled pattern |
| 6 | `projects-S5-fresh-pull.js` | Scenario-local project + try/finally cleanup |
| 7 | `calculation-history-S2-update-push.js` | Convert to ctx + seedAndSync pattern |
| 7 | `calculation-history-S3-delete-push.js` | Convert to ctx + seedAndSync pattern |

**Total**: 22 files modified (1 helper + 21 scenarios)
