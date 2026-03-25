# L2 Category B Conversion & One-Off Fixes Spec

**Date**: 2026-03-25
**Status**: Approved
**Scope**: 22 JS test scenario files + 1 shared constant

---

## Overview

### Purpose
Fix remaining 73 L2 sync verification failures (21 failing + 52 skipped) by converting 20 Category B verbose scenario files to the shared ctx pattern, fixing photos-S1 endpoint, and fixing project-assignments-S5 UNIQUE constraint.

### Scope
- **In scope**: 22 JS test scenario files in `tools/debug-server/scenarios/L2/`, 1 constant in `scenario-helpers.js`
- **Out of scope**: Dart production code (no changes), shared fixture changes, L3 scenarios, new tables

### Success Criteria
- [ ] Full L2 suite: 84/84 passing (or identified failures unrelated to these fixes)
- [ ] No scenario creates its own project except `projects-S4/S5`
- [ ] All scenario files use `{name, description, run({ctx})}` export shape
- [ ] Zero orphaned test records after clean run + teardown

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| `projects-S4/S5` handling | Scenario-local project with modern export shape + own cleanup | Can't soft-delete shared fixture project; skipping tests is not an option |
| photos-S1 test image | Valid 1x1 JPEG base64 constant | Truncated stub may fail `decodeImage()`; valid JPEG eliminates ambiguity |
| project-assignments-S5 fix | Scenario-local pre-cleanup hard-DELETE | UNIQUE issue is specific to this table's fixed `adminUserId`; generic pattern is over-engineering |
| calculation-history S2/S3 records | Scenario-local via `makeCalculationHistory(ctx)` | Keep shared fixture lean; scenario-local is the established pattern |
| S5 record source | Always scenario-local (never fixture records) | S4 may soft-delete fixture records; S5 must be independent |
| S4 record source | Create scenario-local records using fixture IDs as FK parents | Avoids soft-deleting fixture records that cross-table scenarios depend on; matches contractors-S4 reference pattern |
| S1 UNIQUE constraints | No additional fixes needed | Already resolved in S637; all other S1 files use `Date.now()` or have no UNIQUE constraints |

---

## Conversion Pattern

### Category B → Category A (S4 Conflict)

```js
// AFTER (Category A)
const { seedAndSync, runConflictPhase, softDeleteAndVerify, waitForSyncClean, makeXxx } = require('../../scenario-helpers');

module.exports = {
  name: 'table-S4-conflict',
  description: '...',
  async run({ verifier, device, ctx }) {
    // For tables IN fixture: use ctx.*Id directly
    // For tables NOT in fixture: create scenario-local record
    const record = makeXxx(ctx.projectId, { name: `SYNCTEST-xxx-s4-${Date.now()}` });
    await seedAndSync(verifier, device, 'table_name', record);

    // Remote wins
    await runConflictPhase(device, verifier, {
      table: 'table_name', id: record.id, field: 'field_name',
      localVal: 'local-value', remoteVal: 'remote-value', expectedWinner: 'remote'
    });

    // Local wins
    await runConflictPhase(device, verifier, {
      table: 'table_name', id: record.id, field: 'field_name',
      localVal: 'local-value-2', remoteVal: 'remote-value-2', expectedWinner: 'local'
    });

    await softDeleteAndVerify(verifier, device, 'table_name', record.id);
    await waitForSyncClean(device);
  }
};
```

### Category B → Category A (S5 Fresh-Pull)

```js
module.exports = {
  name: 'table-S5-fresh-pull',
  description: '...',
  async run({ verifier, device, ctx }) {
    // ALWAYS scenario-local (never fixture records — S4 may have soft-deleted them)
    const record = makeXxx(...);
    await seedAndSync(verifier, device, 'table_name', record);
    await verifyPulled(device, 'table_name', record.id, { field: value });

    await device.removeLocalRecord('table_name', ctx.projectId);
    await device.triggerSync();
    await waitForSyncComplete(device);
    await verifyPulled(device, 'table_name', record.id, { field: value });
  }
};
```

### projects-S4/S5 (Scenario-Local Project)

```js
module.exports = {
  name: 'projects-S4-conflict',
  description: '...',
  async run({ verifier, device, ctx }) {
    const project = makeProject({ name: `SYNCTEST-project-s4-${Date.now()}`, ... });
    const assignment = makeProjectAssignment({ project_id: project.id, user_id: ctx.inspectorUserId, ... });
    await verifier.insertRecord('projects', project);
    await verifier.insertRecord('project_assignments', assignment);
    // sync, conflict phases, cleanup...
    try {
      // ... conflict logic using runConflictPhase on project ...
    } finally {
      await verifier.deleteRecord('project_assignments', assignment.id);
      await verifier.deleteRecord('projects', project.id);
    }
  }
};
```

---

## File Manifest (22 files)

### S4 Conversions (9 files)

| # | File | Record Source | Conflict Field |
|---|------|-------------|----------------|
| 1 | `bid-items-S4-conflict.js` | Scenario-local: `makeBidItem(ctx.projectId)` | `description` |
| 2 | `calculation-history-S4-conflict.js` | Scenario-local: `makeCalculationHistory(ctx)` | `notes` |
| 3 | `locations-S4-conflict.js` | Scenario-local: `makeLocation(ctx.projectId)` | `name` |
| 4 | `personnel-types-S4-conflict.js` | Scenario-local: `makePersonnelType(ctx.projectId)` | `name` |
| 5 | `todo-items-S4-conflict.js` | Scenario-local: `makeTodoItem(ctx)` | `title` |
| 6 | `photos-S4-conflict.js` | Scenario-local: `makePhoto(ctx)` | `filename` (normalized — not `file_path`) |
| 7 | `inspector-forms-S4-conflict.js` | Scenario-local: `makeInspectorForm({project_id: ctx.projectId})` | `name` |
| 8 | `entry-quantities-S4-conflict.js` | Scenario-local: `makeEntryQuantity(ctx)` | `quantity` |
| 9 | `projects-S4-conflict.js` | Scenario-local project (Option A) | `name` |

### S5 Conversions (9 files) — ALL scenario-local records

| # | File | Factory | Verify Fields |
|---|------|---------|---------------|
| 10 | `bid-items-S5-fresh-pull.js` | `makeBidItem(ctx.projectId)` | `description`, `bid_quantity` |
| 11 | `calculation-history-S5-fresh-pull.js` | `makeCalculationHistory(ctx)` | `notes`, `result_data` |
| 12 | `locations-S5-fresh-pull.js` | `makeLocation(ctx.projectId)` | `name` |
| 13 | `personnel-types-S5-fresh-pull.js` | `makePersonnelType(ctx.projectId)` | `name` |
| 14 | `todo-items-S5-fresh-pull.js` | `makeTodoItem(ctx)` | `title`, `is_completed` |
| 15 | `photos-S5-fresh-pull.js` | `makePhoto(ctx)` | `filename` |
| 16 | `inspector-forms-S5-fresh-pull.js` | `makeInspectorForm({project_id: ctx.projectId})` | `name` |
| 17 | `entry-quantities-S5-fresh-pull.js` | `makeEntryQuantity(ctx)` | `quantity` |
| 18 | `projects-S5-fresh-pull.js` | Scenario-local project (Option A) | `name`, `project_number` |

### Calculation-History S2/S3 (2 files)

| # | File | Record Source | Action |
|---|------|-------------|--------|
| 19 | `calculation-history-S2-update-push.js` | Scenario-local: `makeCalculationHistory(ctx)` | Update `notes` field |
| 20 | `calculation-history-S3-delete-push.js` | Scenario-local: `makeCalculationHistory(ctx)` | Soft-delete |

### One-Off Fixes (2 files)

| # | File | Fix |
|---|------|-----|
| 21 | `photos-S1-push.js` | Rewrite: use `/driver/inject-photo-direct` with `TEST_JPEG_BASE64` constant, use `ctx` |
| 22 | `project-assignments-S5-fresh-pull.js` | Add pre-cleanup: hard-DELETE stale `(ctx.projectId, ctx.adminUserId)` before insert |

### Shared Constant (1 addition)

| File | Addition |
|------|----------|
| `scenario-helpers.js` | `TEST_JPEG_BASE64` — valid 1x1 white JPEG, ~107 bytes base64 |

---

## Edge Cases & Special Handling

### projects-S4/S5 Cleanup
Creates only project + assignment (no children). `finally` block hard-DELETEs in FK order: assignment first, then project.

### photos-S4 Field Normalization
Current Category B uses `filename` (local-wins) and `file_path` (remote-wins) inconsistently. Normalize to `filename` for both conflict phases.

### todo-items / inspector-forms `project_id`
Current Category B seeds without `project_id`. Factory functions (`makeTodoItem(ctx)`, `makeInspectorForm({project_id})`) handle this — verify before using.

### S4/S5 Independence
S4 uses fixture records (may soft-delete them). S5 always creates scenario-local records. They are fully independent — S4's soft-delete does not affect S5.

---

## Testing Strategy

### Verification
1. **Per-table smoke test**: After each table's conversion, run `node run-tests.js --table <table>`
2. **Full L2 suite**: After all 22 files, run `node run-tests.js --layer L2` — target 84/84
3. **Teardown verification**: Query Supabase for `SYNCTEST-` prefixed records after full run — should be zero

### Risk Areas

| Risk | Mitigation |
|------|-----------|
| Factory missing `project_id` | Verify each `make*()` factory before using |
| Valid JPEG fails `decodeImage()` | Use known-good 1x1 JPEG, not truncated stub |
| `projects-S4` cleanup misses FK children | Only create project + assignment — minimal FK surface |
| S4 soft-deletes fixture record | S5 is independent (scenario-local); test runner runs S1→S5 per table sequentially |

### No Dart Changes
Zero production code changes. All fixes are JS files in `tools/debug-server/`.
