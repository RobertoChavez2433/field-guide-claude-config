# L2 Category B Conversion — Dependency Graph

## Direct Changes (22 JS files + 1 constant)

All files in `tools/debug-server/scenarios/L2/`.

### S4 Conflict Conversions (9 files)

| File | Current Pattern | Record Source | Conflict Field | Lines |
|------|----------------|--------------|----------------|-------|
| `bid-items-S4-conflict.js` | Cat B: `{run}`, own project, inline step() | Fixture: `ctx.bidItemId` | `description` | 127 → ~25 |
| `calculation-history-S4-conflict.js` | Cat B: `{run}`, own project, inline step() | Scenario-local: `makeCalculationHistory(ctx)` | `notes` | ~127 → ~25 |
| `locations-S4-conflict.js` | Cat B: `{run}`, own project+location, inline step() | Fixture: `ctx.locationId` | `name` | 118 → ~25 |
| `personnel-types-S4-conflict.js` | Cat B: `{run}`, own project, inline step() | Fixture: `ctx.personnelTypeId` | `name` | 124 → ~25 |
| `todo-items-S4-conflict.js` | Cat B: `{run}`, own project, no project_id on seed | Scenario-local: `makeTodoItem(ctx)` | `title` | 126 → ~25 |
| `photos-S4-conflict.js` | Cat B: `{run}`, own project+loc+entry, inconsistent fields | Scenario-local: `makePhoto(ctx)` | `filename` (normalized) | 133 → ~25 |
| `inspector-forms-S4-conflict.js` | Cat B: `{run}`, own project, no project_id on seed | Fixture: `ctx.inspectorFormId` | `name` | 125 → ~25 |
| `entry-quantities-S4-conflict.js` | Cat B: `{run}`, own project+loc+entry+biditem | Scenario-local: `makeEntryQuantity(ctx)` | `quantity` | 141 → ~25 |
| `projects-S4-conflict.js` | Cat B: `{run}`, IS the project | Scenario-local project (Option A) | `name` | 122 → ~45 |

### S5 Fresh-Pull Conversions (9 files)

All S5 files use scenario-local records (never fixture records).

| File | Current Pattern | Factory | Verify Fields | Lines |
|------|----------------|---------|---------------|-------|
| `bid-items-S5-fresh-pull.js` | Cat B: `{run}`, own project, `device._request()` | `makeBidItem(ctx.projectId)` | `description`, `bid_quantity` | 71 → ~22 |
| `calculation-history-S5-fresh-pull.js` | Cat B: same | `makeCalculationHistory(ctx)` | `notes`, `result_data` | ~71 → ~22 |
| `locations-S5-fresh-pull.js` | Cat B: same | `makeLocation(ctx.projectId)` | `name` | ~56 → ~22 |
| `personnel-types-S5-fresh-pull.js` | Cat B: same | `makePersonnelType(ctx.projectId)` | `name` | ~56 → ~22 |
| `todo-items-S5-fresh-pull.js` | Cat B: same | `makeTodoItem(ctx)` | `title`, `is_completed` | ~56 → ~22 |
| `photos-S5-fresh-pull.js` | Cat B: same | `makePhoto(ctx)` | `filename` | ~56 → ~22 |
| `inspector-forms-S5-fresh-pull.js` | Cat B: same | `makeInspectorForm({project_id: ctx.projectId})` | `name` | ~56 → ~22 |
| `entry-quantities-S5-fresh-pull.js` | Cat B: same | `makeEntryQuantity(ctx)` | `quantity` | ~56 → ~22 |
| `projects-S5-fresh-pull.js` | Cat B: own project IS the record | Scenario-local project (Option A) | `name`, `project_number` | 56 → ~35 |

### Calculation-History S2/S3 (2 files)

| File | Current Pattern | Factory | Action |
|------|----------------|---------|--------|
| `calculation-history-S2-update-push.js` | Cat B: `{run}`, own project, inline seed | `makeCalculationHistory(ctx)` | Update `notes` field |
| `calculation-history-S3-delete-push.js` | Cat B: `{run}`, own project, inline seed | `makeCalculationHistory(ctx)` | Soft-delete |

### One-Off Fixes (2 files)

| File | Current Issue | Fix |
|------|--------------|-----|
| `photos-S1-push.js` | Wrong endpoint (`/driver/inject-photo`), no base64 data, Cat B structure | Rewrite to use `/driver/inject-photo-direct` with `TEST_JPEG_BASE64`, modern Cat A export |
| `project-assignments-S5-fresh-pull.js` | UNIQUE `(project_id, user_id)` hit on retry | Add pre-cleanup hard-DELETE before insert |

### Shared Constant (1 addition)

| File | Addition |
|------|----------|
| `scenario-helpers.js` | `TEST_JPEG_BASE64` constant (valid 1x1 white JPEG, exported) |

---

## Key Source References (for plan-writer)

### Reference Category A — contractors-S4-conflict.js (FULL SOURCE)
```js
const { makeContractor, seedAndSync, runConflictPhase, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'contractors-S4-conflict',
  description: 'Contractor conflict resolution: remote-wins then local-wins',

  async run({ verifier, device, ctx }) {
    const record = makeContractor(ctx.projectId, {
      name: `SYNCTEST-contractor-s4-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'contractors', record);
    await runConflictPhase(device, verifier, {
      table: 'contractors', id: record.id, field: 'name',
      localValue: 'SYNCTEST-local-phase1', remoteValue: 'SYNCTEST-remote-phase1',
      expectedWinner: 'remote',
    });
    await runConflictPhase(device, verifier, {
      table: 'contractors', id: record.id, field: 'name',
      localValue: 'SYNCTEST-local-phase2', remoteValue: 'SYNCTEST-remote-phase2',
      expectedWinner: 'local',
    });
    await softDeleteAndVerify(verifier, device, 'contractors', record.id);
    await waitForSyncClean(device);
  },
};
```

### Reference Category A — contractors-S5-fresh-pull.js (FULL SOURCE)
```js
const { makeContractor, seedAndSync, verifyPulled, softDeleteAndVerify, waitForSyncComplete, waitForSyncClean } = require('../../scenario-helpers');

module.exports = {
  name: 'contractors-S5-fresh-pull',
  description: 'Seed contractor, sync, remove from device, re-sync, verify restored',

  async run({ verifier, device, ctx }) {
    const record = makeContractor(ctx.projectId, {
      name: `SYNCTEST-contractor-s5-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'contractors', record);
    await verifyPulled(device, 'contractors', record.id);
    await device.removeLocalRecord('contractors', ctx.projectId);
    await device.triggerSync();
    await waitForSyncComplete(device);
    await verifyPulled(device, 'contractors', record.id);
    await softDeleteAndVerify(verifier, device, 'contractors', record.id);
    await waitForSyncClean(device);
  },
};
```

### Factory Functions (ALL VERIFIED SOURCE)

#### makeProject(overrides = {})
```js
function makeProject(overrides = {}) {
  const { userId, ...rest } = overrides;
  return {
    id: uuid(),
    company_id: process.env.COMPANY_ID || (() => { throw new Error('COMPANY_ID env var required'); })(),
    project_number: `PN-${Date.now().toString(36)}`,
    name: `SYNCTEST-${Date.now()}`,
    is_active: true,
    created_by_user_id: userId || uuid(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...rest,
  };
}
```

#### makeProjectAssignment(ctx, overrides = {})
```js
function makeProjectAssignment(ctx, overrides = {}) {
  return {
    id: uuid(),
    project_id: ctx.projectId,
    user_id: ctx.inspectorUserId,
    assigned_by: ctx.adminUserId || ctx.inspectorUserId,
    company_id: ctx.companyId,
    assigned_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}
```

#### makeBidItem(projectId, overrides = {})
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

#### makeCalculationHistory(ctx, overrides = {})
```js
function makeCalculationHistory(ctx, overrides = {}) {
  return {
    id: uuid(),
    entry_id: ctx.dailyEntryId,
    calc_type: 'hma',
    input_data: JSON.stringify({ area: 100, thickness: 2, density: 145 }),
    result_data: JSON.stringify({ value: 290.0 }),
    project_id: ctx.projectId,
    created_by_user_id: ctx.inspectorUserId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}
```

#### makeLocation(projectId, overrides = {})
```js
function makeLocation(projectId, overrides = {}) {
  return {
    id: uuid(),
    project_id: projectId,
    name: `SYNCTEST-Location-${Date.now().toString(36)}`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}
```

#### makePersonnelType(projectId, overrides = {})
```js
function makePersonnelType(projectId, overrides = {}) {
  const namePrefix = overrides.namePrefix || 'SYNCTEST';
  const { namePrefix: _np, ...rest } = overrides;
  return {
    id: uuid(),
    project_id: projectId,
    name: `${namePrefix}-PersonnelType ${Date.now()}`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...rest,
  };
}
```

#### makeTodoItem(ctx, overrides = {})
```js
function makeTodoItem(ctx, overrides = {}) {
  const namePrefix = overrides.namePrefix || 'SYNCTEST';
  const { namePrefix: _np, ...rest } = overrides;
  return {
    id: uuid(),
    title: `${namePrefix}-todo-${Date.now()}`,
    is_completed: false,
    project_id: ctx.projectId,
    created_by_user_id: ctx.inspectorUserId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...rest,
  };
}
```

#### makePhoto(ctx, overrides = {})
```js
function makePhoto(ctx, overrides = {}) {
  return {
    id: uuid(),
    entry_id: ctx.dailyEntryId,
    project_id: ctx.projectId,
    file_path: `synctest/photo-${Date.now()}.jpg`,
    filename: `photo-${Date.now()}.jpg`,
    caption: 'SYNCTEST photo',
    captured_at: new Date().toISOString(),
    created_by_user_id: ctx.inspectorUserId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}
```

#### makeEntryQuantity(ctx, overrides = {})
```js
function makeEntryQuantity(ctx, overrides = {}) {
  return {
    id: uuid(),
    entry_id: ctx.dailyEntryId,
    bid_item_id: ctx.bidItemId,
    quantity: 10.0,
    project_id: ctx.projectId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}
```

#### makeInspectorForm(overrides = {})
```js
function makeInspectorForm(overrides = {}) {
  return {
    id: uuid(),
    name: `SYNCTEST-Form ${Date.now()}`,
    template_path: '/templates/test.json',
    is_builtin: false,
    project_id: overrides.project_id || null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}
```

### Helper Functions (VERIFIED SIGNATURES)

```
seedAndSync(verifier, device, table, record) — inserts record into Supabase, triggers sync, waits for completion
runConflictPhase(device, verifier, { table, id, field, localValue, remoteValue, expectedWinner }) — handles both 'remote' and 'local' winner scenarios with sleep(2000) for timestamp safety
softDeleteAndVerify(verifier, device, table, id) — soft-deletes via device, syncs, verifies deleted_at on server
verifyPulled(device, table, id) — checks record exists on device via getLocalRecord()
waitForSyncComplete(device, description?, timeoutMs?) — polls isSyncing until false
waitForSyncClean(device) — triggers sync, waits complete, asserts zero pending changes
device.removeLocalRecord(table, projectId) — calls POST /driver/remove-from-device { project_id }
device.updateRecord(table, id, updates) — auto-stamps updated_at if not set; calls POST /driver/update-record { table, id, data }
verifier.deleteRecord(table, id) — hard DELETE via Supabase REST API (service role)
verifier.queryRecords(table, filters) — GET with PostgREST filters (service role)
verifier.insertRecord(table, record) — POST to Supabase REST API
verifier.authenticateAs(role) — obtains JWT for 'admin' or 'inspector' role
verifier.resetAuth() — clears role JWT, returns to service role
```

### module.exports from scenario-helpers.js (line 590-613)
All needed factories and helpers are already exported:
`uuid, testPrefix, sleep, verify, assertEqual, waitFor, step, cleanup, makeProject, makeDailyEntry, makeLocation, makeContractor, makeEquipment, makePersonnelType, makeBidItem, makeInspectorForm, makeFormResponse, setAirplaneMode, TestContext, makeProjectAssignment, makeEntryContractor, makeEntryEquipment, makeEntryPersonnelCount, makeEntryQuantity, makeTodoItem, makeCalculationHistory, makePhoto, seedAndSync, waitForSyncComplete, softDeleteAndVerify, runConflictPhase, verifyPulled, waitForSyncClean`

### inject-photo-direct endpoint (driver_server.dart:680-710)
- POST `/driver/inject-photo-direct`
- Required fields: `base64Data` (String), `filename` (String, must end in .jpg/.jpeg/.png), `entryId` (String UUID), `projectId` (String UUID)
- Returns: `{injected: true, direct: true, id: <photoId>, entryId, localPath}`
- Creates SQLite record directly via `testPhotoService.injectPhotoDirect()`

---

## Blast Radius

- **Direct**: 22 JS scenario files + 1 addition to scenario-helpers.js
- **Dependent**: 0 (these are leaf test files; no other files import them)
- **Tests**: Self-verifying (running the L2 suite IS the test)
- **Cleanup**: 0 (old code is replaced, not deleted elsewhere)
- **Dart changes**: 0
