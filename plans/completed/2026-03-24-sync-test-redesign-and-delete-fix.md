# Sync Test Redesign + Hard-Delete Fix — Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Redesign sync verification tests around a shared TestContext (eliminating 84 separate projects) and fix the sync engine's hard-delete orphan crash bug.
**Spec:** `.claude/specs/2026-03-24-sync-test-redesign-and-delete-fix-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-24-sync-test-redesign-and-delete-fix/`

**Architecture:** The test infrastructure moves from per-scenario project creation to a shared TestContext with 9 fixture records seeded once per run. The sync engine gets three fixes: idempotent delete handling (Fix A), orphan purge (Fix B), and safer transient-error classification (Fix C). All 84 L2 + 10 L3 scenarios are rewritten to accept `ctx` and use common helpers.
**Tech Stack:** Dart/Flutter (sync engine), Node.js/JavaScript (test infrastructure)
**Blast Radius:** 4 direct Dart files, ~97 JS files, 3 widget key files, 5 dependent, 3 test files

---

## Phase 1: Sync Engine Fixes (Dart)

### Sub-phase 1.1: Fix A — _pushDelete treats missing record as success
**Files:** `lib/features/sync/engine/sync_engine.dart`
**Agent:** `backend-supabase-agent`

#### Step 1.1.1: Replace throw with idempotent return

In `lib/features/sync/engine/sync_engine.dart` around lines 600-605, find:

```dart
// OLD (lines ~600-605):
// BUG-C: 0 rows affected — record doesn't exist on server
if (response.isEmpty) {
  throw StateError(
    'Soft-delete push failed: ${adapter.tableName}/${change.recordId} '
    '— remote record not found (0 rows affected)',
  );
}
```

Replace with:

```dart
// FIX A: Server record already gone — goal achieved (idempotent delete)
// WHY: Hard-deleted Supabase records return empty response. The intent
// (record gone from server) is already satisfied — no need to throw.
// The caller (_push loop) calls markProcessed after _routeAndPush returns.
if (response.isEmpty) {
  Logger.sync(
    'Soft-delete push: ${adapter.tableName}/${change.recordId} '
    '— remote record already absent, marking processed',
  );
  return;
}
```

<!-- NOTE: The _push() method calls `await _changeTracker.markProcessed(change.id)` after
     `_routeAndPush()` returns normally, so returning here is sufficient. -->

#### Step 1.1.2: Verify Fix A compiles

```
pwsh -Command "flutter analyze lib/features/sync/engine/sync_engine.dart"
```

Expected: No errors. Warnings OK.

---

### Sub-phase 1.2: Fix C — _isTransientError hardening
**Files:** `lib/features/sync/application/sync_orchestrator.dart`
**Agent:** `backend-supabase-agent`

#### Step 1.2.1: Add non-transient patterns and change default

In `lib/features/sync/application/sync_orchestrator.dart` around lines 414-462, find the `nonTransientPatterns` list and the `return true` default at the end of `_isTransientError`.

**Add to nonTransientPatterns array** (after the existing entries):

```dart
// FIX C: Delete-related errors are permanent, not transient
// FROM SPEC: Prevents infinite retry on hard-deleted records
'remote record not found',
'0 rows affected',
'Soft-delete push failed',
```

**Replace the final `return true`** (the default case at the end of the method) with:

```dart
// FIX C: Unknown errors default to non-transient (safer than infinite retry)
// WHY: Transient-by-default caused infinite retry loops for permanent errors.
// A false negative (treating transient as permanent) just delays one sync cycle.
// A false positive (treating permanent as transient) causes infinite retry + battery drain.
Logger.sync('WARNING: Unknown error type in _isTransientError, '
    'defaulting to non-transient: ${result.errorMessages}');
return false;
```

#### Step 1.2.2: Verify Fix C compiles

```
pwsh -Command "flutter analyze lib/features/sync/application/sync_orchestrator.dart"
```

Expected: No errors.

---

### Sub-phase 1.3: Fix B — Orphan purge in IntegrityChecker
**Files:** `lib/features/sync/engine/integrity_checker.dart`, `lib/features/sync/engine/sync_engine.dart`
**Agent:** `backend-supabase-agent`

#### Step 1.3.1: Add purgeOrphans method to IntegrityChecker

In `lib/features/sync/engine/integrity_checker.dart`, add the following method to the `IntegrityChecker` class.

<!-- NOTE: The implementing agent MUST read integrity_checker.dart first to find the exact
     class structure, field names (_db, _supabase), and import style before inserting. -->

Add this method at the end of the class, before the closing `}`:

```dart
/// FIX B: Purge local records whose server counterpart was hard-deleted.
/// WHY: When an admin hard-deletes a Supabase record, the local copy becomes
/// an orphan that the sync engine tries to push forever. This detects and
/// soft-deletes those orphans locally.
/// FROM SPEC: Called after _integrityChecker.run() and _orphanScanner.scan()
Future<int> purgeOrphans({
  required Set<String> syncedProjectIds,
  required ChangeTracker changeTracker,
}) async {
  if (syncedProjectIds.isEmpty) return 0;

  // FK order: parents first so child queries still work
  // NOTE: This order matches the sync adapter registration order
  final tablesToCheck = [
    'projects',
    'project_assignments',
    'locations',
    'contractors',
    'equipment',
    'bid_items',
    'personnel_types',
    'daily_entries',
    'photos',
    'entry_equipment',
    'entry_quantities',
    'entry_contractors',
    'entry_personnel_counts',
    'inspector_forms',
    'form_responses',
    'todo_items',
    'calculation_history',
  ];

  int totalPurged = 0;

  for (final table in tablesToCheck) {
    try {
      // 1. Get local non-deleted record IDs
      final localRows = await _db.query(
        table,
        columns: ['id', 'project_id'],
        where: 'deleted_at IS NULL',
      );

      if (localRows.isEmpty) continue;

      // 2. Filter to synced projects only
      // NOTE: Some tables (projects, project_assignments) may not have project_id
      // directly — the implementing agent must check the schema and handle accordingly.
      // For 'projects' table, filter by id IN syncedProjectIds.
      // For 'project_assignments', filter by project_id IN syncedProjectIds.
      // For all others, filter by project_id IN syncedProjectIds.
      final List<String> localIds;
      if (table == 'projects') {
        localIds = localRows
            .where((r) => syncedProjectIds.contains(r['id'] as String))
            .map((r) => r['id'] as String)
            .toList();
      } else {
        localIds = localRows
            .where((r) => syncedProjectIds.contains(r['project_id'] as String))
            .map((r) => r['id'] as String)
            .toList();
      }

      if (localIds.isEmpty) continue;

      // 3. Skip records with unprocessed change_log entries
      final pendingIds = await changeTracker.getPendingRecordIds(table);
      final idsToCheck = localIds.where((id) => !pendingIds.contains(id)).toList();

      if (idsToCheck.isEmpty) continue;

      // 4. Batch-query Supabase in pages of 100
      final serverIds = <String>{};
      for (var i = 0; i < idsToCheck.length; i += 100) {
        final batch = idsToCheck.sublist(
          i,
          i + 100 > idsToCheck.length ? idsToCheck.length : i + 100,
        );
        final response = await _supabase
            .from(table)
            .select('id')
            .inFilter('id', batch);
        for (final row in response) {
          serverIds.add(row['id'] as String);
        }
      }

      // 5. Diff: local - server = orphans
      final orphanIds = idsToCheck.where((id) => !serverIds.contains(id)).toSet();

      if (orphanIds.isEmpty) continue;

      // 6. Soft-delete each orphan locally
      // WHY: sync_control pulling=1 prevents the change_tracker from logging
      // these as local changes that need to be pushed back to the server.
      // NOTE: try/finally ensures pulling=0 is always reset (SEC-H1).
      final now = DateTime.now().toUtc().toIso8601String();
      int purgedCount = 0;
      await _db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
      try {
        for (final orphanId in orphanIds) {
          await _db.update(
            table,
            {'deleted_at': now, 'deleted_by': 'system_orphan_purge'},
            where: 'id = ?',
            whereArgs: [orphanId],
          );
          purgedCount++;
          Logger.sync('Orphan purged: $table/$orphanId — missing from server');
        }
      } finally {
        await _db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
      }

      totalPurged += purgedCount;
      Logger.sync('Orphan purge: $table — $purgedCount records soft-deleted');
    } catch (e) {
      // NOTE: Don't let one table failure stop the rest
      Logger.sync('Orphan purge: $table — error: $e');
    }
  }

  return totalPurged;
}
```

<!-- IMPORTANT: The implementing agent MUST verify:
     1. The exact field names used by IntegrityChecker (_db vs db, _supabase vs supabase)
     2. The _db.query() and _db.update() method signatures match the actual DatabaseService API
     3. Whether ChangeTracker has a getPendingRecordIds(table) method — if not, it must be added
        or an alternative approach used (e.g., raw query on change_log table)
     4. Trigger suppression is done via sync_control table (key='pulling', value='1'/'0'),
        NOT via a per-table 'pulling' column. Verify the sync_control table exists and
        that the change_tracker reads it before logging changes.
     5. Whether some tables lack project_id (e.g., project_assignments uses project_id,
        but check inspector_forms, etc.)
-->

#### Step 1.3.2: Call purgeOrphans from SyncEngine.pushAndPull

In `lib/features/sync/engine/sync_engine.dart` around line 290, after the existing `_integrityChecker.run()` and `_orphanScanner.scan()` calls, add:

```dart
// FIX B: Purge local records whose server counterpart was hard-deleted
// FROM SPEC: Runs after integrity check and orphan scan
final purgedCount = await _integrityChecker.purgeOrphans(
  syncedProjectIds: _syncedProjectIds,
  changeTracker: _changeTracker,
);
if (purgedCount > 0) {
  Logger.sync('Orphan purge: $purgedCount local records soft-deleted');
}
```

<!-- NOTE: The implementing agent must read sync_engine.dart to find the exact location
     of _integrityChecker.run() and _orphanScanner.scan() calls, and verify field names
     _syncedProjectIds and _changeTracker exist on the SyncEngine class. -->

#### Step 1.3.3: Add getPendingRecordIds to ChangeTracker (if needed)

The implementing agent must check if `ChangeTracker` already has a method to get pending record IDs for a table. If not, add:

**File:** `lib/features/sync/engine/change_tracker.dart`

```dart
/// Returns the set of record IDs that have unprocessed change_log entries for [table].
Future<Set<String>> getPendingRecordIds(String table) async {
  final rows = await _db.query(
    'change_log',
    columns: ['record_id'],
    where: 'table_name = ? AND processed = 0',
    whereArgs: [table],
  );
  return rows.map((r) => r['record_id'] as String).toSet();
}
```

<!-- NOTE: Only add this if the method doesn't exist. The implementing agent must verify
     the change_log table schema (column names: table_name, record_id, processed). -->

#### Step 1.3.4: Verify all Dart changes compile

```
pwsh -Command "flutter analyze lib/features/sync/"
```

Expected: No errors.

---

### Sub-phase 1.4: Unit tests for sync engine fixes
**Files:** `test/features/sync/sync_engine_delete_test.dart` (new)
**Agent:** `qa-testing-agent`

#### Step 1.4.1: Create unit test file

<!-- NOTE: The implementing agent must read existing test files in test/features/sync/
     to match the project's test patterns (mock setup, test utilities, etc.) -->

Create `test/features/sync/sync_engine_delete_test.dart` with tests for:

1. **Fix A test:** Mock a _pushDelete scenario where Supabase returns empty response. Assert no exception thrown.
2. **Fix C test:** Assert that unknown error messages return `false` from `_isTransientError`. Assert known transient patterns still return `true`. Assert new non-transient patterns ('remote record not found', '0 rows affected', 'Soft-delete push failed') return `false`.

The implementing agent should model these tests on existing sync test patterns in the project.

#### Step 1.4.3: Add purgeOrphans unit tests (Fix B)

Add the following test cases to `test/features/sync/sync_engine_delete_test.dart` covering the `IntegrityChecker.purgeOrphans` method:

1. **Orphan detected and soft-deleted:** Given a local record whose ID is absent from the mocked Supabase response, assert that the record is soft-deleted locally (deleted_at set, deleted_by = 'system_orphan_purge').
2. **Record with pending change_log entry is skipped:** Given a local record with a pending change_log entry (processed = 0), assert that `purgeOrphans` does NOT soft-delete it even if it is absent from the server response.
3. **pulling=1/0 wrapped in try/finally:** Given a mocked _db that throws during the soft-delete loop, assert that `UPDATE sync_control SET value = '0' WHERE key = 'pulling'` is still called in the finally block.

<!-- NOTE: The implementing agent must mock _db and _supabase to write these tests.
     Check existing IntegrityChecker test patterns (if any) in test/features/sync/. -->

#### Step 1.4.4: Verify tests pass

```
pwsh -Command "flutter test test/features/sync/sync_engine_delete_test.dart"
```

Expected: All tests pass.

---

## Phase 2: Test Infrastructure (JS)

> **NOTE FOR IMPLEMENTING AGENT — DeviceOrchestrator API:** Before writing any helpers that call `device.*` methods, you MUST read `tools/debug-server/device-orchestrator.js` to verify what methods are actually available. The DeviceOrchestrator makes HTTP calls to the Flutter driver. The method names used in this plan are approximations — use the actual API found in that file. Specific mappings to verify:
> - `device.softDelete(table, id)` → may need to use `device.createRecord(table, { id, deleted_at: now, deleted_by: userId })` or the driver's `/driver/delete-record` endpoint
> - `device.updateRecord(table, id, fields)` → verify against `/driver/update-record` endpoint
> - `device.waitForSyncComplete()` → may need `device.triggerSync()` + `waitFor(() => device.getSyncStatus(), ...)` pattern
> - `device.recordExists(table, id)` → may need `device.getLocalRecord(table, id)` and check if non-null
> - `device.getPendingChangeCount()` → may need `device.getChangeLog()` and check length
> - `device.removeLocalRecord(table, id)` → verify against `/driver/remove-from-device` endpoint
>
> **The implementing agent MUST read `tools/debug-server/device-orchestrator.js` to verify all available methods before writing helpers. The method names above are approximations — use the actual API.**

### Sub-phase 2.1: TestContext class and factories
**Files:** `tools/debug-server/scenario-helpers.js`
**Agent:** `general-purpose`

#### Step 2.1.1: Read current scenario-helpers.js

The implementing agent MUST read the full file first to understand existing factory functions and exports.

#### Step 2.1.2: Add TestContext class

Add at the top of scenario-helpers.js (after existing imports/requires):

```js
// WHY: Shared fixture eliminates per-scenario project creation (84 → 1 project)
// FROM SPEC: TestContext Shape section
class TestContext {
  constructor({
    companyId, adminUserId, inspectorUserId,
    project, projectAssignment, location, contractor,
    equipment, bidItem, personnelType, dailyEntry, inspectorForm,
  }) {
    this.companyId = companyId;
    this.adminUserId = adminUserId;
    this.inspectorUserId = inspectorUserId;
    this.project = project;
    this.projectAssignment = projectAssignment;
    this.location = location;
    this.contractor = contractor;
    this.equipment = equipment;
    this.bidItem = bidItem;
    this.personnelType = personnelType;
    this.dailyEntry = dailyEntry;
    this.inspectorForm = inspectorForm;
  }

  // Convenience accessors
  get projectId() { return this.project.id; }
  get locationId() { return this.location.id; }
  get contractorId() { return this.contractor.id; }
  get equipmentId() { return this.equipment.id; }
  get bidItemId() { return this.bidItem.id; }
  get personnelTypeId() { return this.personnelType.id; }
  get dailyEntryId() { return this.dailyEntry.id; }
  get inspectorFormId() { return this.inspectorForm.id; }
  get projectAssignmentId() { return this.projectAssignment.id; }
}
```

#### Step 2.1.3: Add new make*() factory functions

Add these factories after the existing ones in scenario-helpers.js. Each follows the existing pattern (generates UUID, uses SYNCTEST- prefix).

<!-- NOTE: The implementing agent must read existing factories (makeProject, makeContractor, etc.)
     to match their exact pattern — UUID generation method, field naming, etc. -->

```js
// FROM SPEC: New make*() Factories section
function makeProjectAssignment(ctx, overrides = {}) {
  return {
    id: uuid(),
    project_id: ctx.projectId,
    user_id: ctx.inspectorUserId,
    role: 'inspector',
    company_id: ctx.companyId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}

function makeEntryContractor(ctx, overrides = {}) {
  return {
    id: uuid(),
    daily_entry_id: ctx.dailyEntryId,
    contractor_id: ctx.contractorId,
    worker_count: 3,
    hours_worked: 8.0,
    project_id: ctx.projectId,
    company_id: ctx.companyId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}

function makeEntryEquipment(ctx, overrides = {}) {
  return {
    id: uuid(),
    daily_entry_id: ctx.dailyEntryId,
    equipment_id: ctx.equipmentId,
    hours_used: 4.5,
    project_id: ctx.projectId,
    company_id: ctx.companyId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}

function makeEntryPersonnelCount(ctx, overrides = {}) {
  return {
    id: uuid(),
    daily_entry_id: ctx.dailyEntryId,
    personnel_type_id: ctx.personnelTypeId,
    contractor_id: ctx.contractorId,
    count: 5,
    project_id: ctx.projectId,
    company_id: ctx.companyId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}

function makeEntryQuantity(ctx, overrides = {}) {
  return {
    id: uuid(),
    daily_entry_id: ctx.dailyEntryId,
    bid_item_id: ctx.bidItemId,
    quantity: 10.0,
    project_id: ctx.projectId,
    company_id: ctx.companyId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}

function makeTodoItem(ctx, overrides = {}) {
  const namePrefix = overrides.namePrefix || 'SYNCTEST';
  delete overrides.namePrefix;
  return {
    id: uuid(),
    title: `${namePrefix}-todo-${Date.now()}`,
    completed: false,
    project_id: ctx.projectId,
    company_id: ctx.companyId,
    created_by: ctx.inspectorUserId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}

function makeCalculationHistory(ctx, overrides = {}) {
  return {
    id: uuid(),
    daily_entry_id: ctx.dailyEntryId,
    calculation_type: 'hma',
    input_data: JSON.stringify({ area: 100, thickness: 2, density: 145 }),
    result: 290.0,
    project_id: ctx.projectId,
    company_id: ctx.companyId,
    created_by: ctx.inspectorUserId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}

function makePhoto(ctx, overrides = {}) {
  return {
    id: uuid(),
    daily_entry_id: ctx.dailyEntryId,
    file_path: `synctest/photo-${Date.now()}.jpg`,
    caption: 'SYNCTEST photo',
    project_id: ctx.projectId,
    company_id: ctx.companyId,
    created_by: ctx.inspectorUserId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}
```

#### Step 2.1.4: Fix existing factories

Apply these patches to existing factories in scenario-helpers.js:

**makeContractor:** Add `deleted_at: null, deleted_by: null` if not already present.
**makeEquipment:** Add `deleted_at: null, deleted_by: null` if not already present.
**makeDailyEntry:** Ensure `status: 'draft'` and `revision_number: 0` are defaults.
**makeInspectorForm:** Add optional `project_id` param: `project_id: overrides.project_id || ctx.projectId`
**All factories:** Ensure they accept `namePrefix` override where a name/title field exists.

<!-- NOTE: The implementing agent must read the existing factories to see exactly what
     fields are already present before applying these patches. Do not duplicate fields. -->

#### Step 2.1.5: Add common helper functions

Add these helpers after the factories:

```js
// FROM SPEC: Common Helpers to Extract section

/**
 * Seed a record in Supabase and trigger sync on device.
 * WHY: Every S2/S3/S4/S5 scenario needs this exact sequence.
 */
async function seedAndSync(verifier, device, table, record) {
  await verifier.insertRecord(table, record);
  await device.triggerSync();
  await device.waitForSyncComplete();
}

/**
 * Soft-delete a test record and verify it syncs to Supabase.
 * WHY: Every scenario must clean up its own records via the app's sync flow.
 */
async function softDeleteAndVerify(verifier, device, table, id) {
  await device.softDelete(table, id);
  await device.triggerSync();
  await device.waitForSyncComplete();
  const row = await verifier.getRecord(table, id);
  if (!row || !row.deleted_at) {
    throw new Error(`Soft-delete verification failed: ${table}/${id} — deleted_at not set on server`);
  }
}

/**
 * Run a conflict scenario phase: update both sides, sync, verify winner.
 * WHY: S4 scenarios have two phases (remote-wins, local-wins) with identical structure.
 */
async function runConflictPhase(device, verifier, { table, id, field, localValue, remoteValue, expectedWinner }) {
  // 1. Update locally
  await device.updateRecord(table, id, { [field]: localValue });
  // 2. Update remotely (after local, so remote has later timestamp)
  if (expectedWinner === 'remote') {
    await verifier.updateRecord(table, id, { [field]: remoteValue });
  } else {
    // For local-wins: update remote first so local has later timestamp
    await verifier.updateRecord(table, id, { [field]: remoteValue });
    await new Promise(r => setTimeout(r, 2000)); // 2s minimum for LWW timestamp reliability
    await device.updateRecord(table, id, { [field]: localValue });
  }
  // 3. Sync
  await device.triggerSync();
  await device.waitForSyncComplete();
  // 4. Verify
  const row = await verifier.getRecord(table, id);
  const expected = expectedWinner === 'remote' ? remoteValue : localValue;
  if (row[field] !== expected) {
    throw new Error(
      `Conflict resolution failed: ${table}/${id}.${field} = ${row[field]}, ` +
      `expected ${expected} (${expectedWinner} wins)`
    );
  }
}

/**
 * Verify a record was pulled to the device.
 */
async function verifyPulled(device, table, id) {
  const exists = await device.recordExists(table, id);
  if (!exists) {
    throw new Error(`Pull verification failed: ${table}/${id} not found on device`);
  }
}

/**
 * Wait for sync to be clean (no pending changes).
 */
async function waitForSyncClean(device) {
  await device.triggerSync();
  await device.waitForSyncComplete();
  const pending = await device.getPendingChangeCount();
  if (pending > 0) {
    throw new Error(`Sync not clean: ${pending} pending changes remain`);
  }
}
```

#### Step 2.1.6: Update module.exports

Add all new functions and the TestContext class to the existing `module.exports`:

```js
// Add to existing exports:
TestContext,
makeProjectAssignment,
makeEntryContractor,
makeEntryEquipment,
makeEntryPersonnelCount,
makeEntryQuantity,
makeTodoItem,
makeCalculationHistory,
makePhoto,
seedAndSync,
softDeleteAndVerify,
runConflictPhase,
verifyPulled,
waitForSyncClean,
```

#### Step 2.1.7: Verify syntax

```bash
node -c tools/debug-server/scenario-helpers.js
```

Expected: No syntax errors.

---

## Phase 3: Test Runner (JS)

### Sub-phase 3.1: Setup/teardown/sweep in supabase-verifier.js
**Files:** `tools/debug-server/supabase-verifier.js`
**Agent:** `general-purpose`

#### Step 3.1.1: Read current supabase-verifier.js

The implementing agent MUST read the full file first.

> **NOTE FOR IMPLEMENTING AGENT — SupabaseVerifier API:** SupabaseVerifier does NOT have a `this.supabase` client property. It uses raw HTTP calls via an internal `_request` method (or similar). Before implementing `sweepSynctestRecords` and `teardownFixture`, read `tools/debug-server/supabase-verifier.js` to understand the actual request API. Use the existing `verifier.deleteRecord(table, id)` for individual deletes. For bulk deletes by name prefix, add a new `hardDeleteByPrefix(table, nameField, prefix)` method that uses the raw `_request` API. The code blocks below that use `this.supabase.from(table)...` are pseudocode only — the implementing agent must translate these to the actual SupabaseVerifier request pattern.

#### Step 3.1.2: Add SYNCTEST-* sweep method

Add to the SupabaseVerifier class:

```js
// FROM SPEC: Run Lifecycle step 2 — catches prior orphans
// WHY: Any prior test run failure could leave SYNCTEST-* records in Supabase
// NOTE: PSEUDOCODE BELOW — implementing agent must translate to actual SupabaseVerifier
// request API (read supabase-verifier.js first). IDs are UUIDs; SYNCTEST- prefix is on
// name/title/description fields, NOT on id. Use the existing queryByPrefix pattern from
// run-tests.js --clean logic, and reuse verifier.deleteRecord(table, id) per record.
// SEC-H2: Log count deleted per table.
async sweepSynctestRecords() {
  // FK teardown order from spec (children first)
  const teardownOrder = [
    'entry_personnel_counts', 'entry_equipment', 'entry_quantities',
    'entry_contractors', 'photos', 'calculation_history', 'todo_items',
    'form_responses', 'daily_entries', 'equipment', 'personnel_types',
    'bid_items', 'contractors', 'locations', 'inspector_forms',
    'project_assignments', 'projects',
  ];

  let totalDeleted = 0;
  for (const table of teardownOrder) {
    try {
      // NOTE: Hard-DELETE (not soft-delete) — these are test artifacts
      // Using service role bypasses RLS
      // IMPORTANT: Query by name-like fields (NOT id), since IDs are UUIDs.
      // For most tables: query where name LIKE 'SYNCTEST-%'
      // For tables without 'name': use 'title', 'description', or other identifying field
      // Use the existing queryByPrefix / deleteRecord pattern from run-tests.js --clean

      // [Implementing agent: replace this block with actual SupabaseVerifier _request calls]
      // Example pseudocode (DO NOT use this.supabase — it doesn't exist):
      //   const records = await this.queryByPrefix(table, 'name', 'SYNCTEST-');
      //   for (const r of records) await this.deleteRecord(table, r.id);
      //   if (records.length) console.log(`  Sweep ${table}: ${records.length} records deleted`);
      //   totalDeleted += records.length;

      // Also sweep additional name-like fields where applicable
      // SEC-H2: Always log count per table
    } catch (e) {
      console.warn(`  Sweep ${table}: error — ${e.message}`);
    }
  }
  return totalDeleted;
}
```

#### Step 3.1.3: Add shared fixture setup method

```js
// FROM SPEC: Run Lifecycle step 3
async setupSharedFixture(companyId, adminUserId, inspectorUserId) {
  const { TestContext, makeProject, makeProjectAssignment, makeLocation,
    makeContractor, makeEquipment, makeBidItem, makePersonnelType,
    makeDailyEntry, makeInspectorForm,
  } = require('./scenario-helpers');

  const prefix = 'SYNCTEST-FIXTURE';

  // NOTE: All fixture records use SYNCTEST-FIXTURE- prefix for easy identification
  // IMPORTANT: Factory call signatures use positional args — makeX(projectId, overrides)
  // for most existing factories. Verify each factory signature in scenario-helpers.js.
  const project = makeProject({ name: `${prefix}-project`, company_id: companyId });
  await this.insertRecord('projects', project);

  // makeProjectAssignment is a new factory that takes (ctx, overrides) — but ctx isn't
  // available here. Call it inline or use a minimal object matching the factory signature.
  // The implementing agent must check makeProjectAssignment's signature and call accordingly.
  const projectAssignment = makeProjectAssignment(
    { projectId: project.id, inspectorUserId, companyId },
    { user_id: inspectorUserId }
  );
  await this.insertRecord('project_assignments', projectAssignment);

  // Existing factories use positional args: makeLocation(projectId, overrides)
  const location = makeLocation(project.id, { name: `${prefix}-location`, company_id: companyId });
  await this.insertRecord('locations', location);

  const contractor = makeContractor(project.id, { name: `${prefix}-contractor`, company_id: companyId });
  await this.insertRecord('contractors', contractor);

  const equipment = makeEquipment(project.id, { name: `${prefix}-equipment`, company_id: companyId });
  await this.insertRecord('equipment', equipment);

  const bidItem = makeBidItem(project.id, { name: `${prefix}-bid-item`, company_id: companyId });
  await this.insertRecord('bid_items', bidItem);

  const personnelType = makePersonnelType(project.id, { name: `${prefix}-personnel-type`, company_id: companyId });
  await this.insertRecord('personnel_types', personnelType);

  // makeDailyEntry takes (projectId, locationId, overrides)
  const dailyEntry = makeDailyEntry(project.id, location.id, { company_id: companyId });
  await this.insertRecord('daily_entries', dailyEntry);

  const inspectorForm = makeInspectorForm(project.id, {
    company_id: companyId,
    name: `${prefix}-form`,
  });
  await this.insertRecord('inspector_forms', inspectorForm);

  return new TestContext({
    companyId, adminUserId, inspectorUserId,
    project, projectAssignment, location, contractor,
    equipment, bidItem, personnelType, dailyEntry, inspectorForm,
  });
}
```

<!-- IMPORTANT: The implementing agent MUST read scenario-helpers.js to verify the exact
     call signature of each factory before implementing. The calls above use the expected
     positional-arg pattern (makeLocation(projectId, overrides), etc.) based on the review,
     but the agent must confirm each one matches the actual code. -->

#### Step 3.1.4: Add teardown method

```js
// FROM SPEC: Run Lifecycle step 5
// NOTE: PSEUDOCODE BELOW — implementing agent must translate to actual SupabaseVerifier
// request API (read supabase-verifier.js first). Do NOT use this.supabase — it doesn't exist.
// IDs are UUIDs; SYNCTEST- prefix is on name/title fields, NOT on id fields.
// Use verifier.deleteRecord(table, id) per record, or a bulk hardDeleteByPrefix method.
// Reuse the existing --clean / queryByPrefix pattern from run-tests.js.
async teardownFixture(ctx) {
  // FK teardown order from spec (children first)
  const teardownOrder = [
    'entry_personnel_counts', 'entry_equipment', 'entry_quantities',
    'entry_contractors', 'photos', 'calculation_history', 'todo_items',
    'form_responses', 'daily_entries', 'equipment', 'personnel_types',
    'bid_items', 'contractors', 'locations', 'inspector_forms',
    'project_assignments', 'projects',
  ];

  for (const table of teardownOrder) {
    try {
      // Hard-DELETE all SYNCTEST-* records by name field (NOT by id — IDs are UUIDs)
      // [Implementing agent: use hardDeleteByPrefix(table, nameField, 'SYNCTEST-') or
      //  queryByPrefix + deleteRecord per record, matching existing patterns]
    } catch (e) {
      console.warn(`  Teardown ${table}: ${e.message}`);
    }
  }

  // Final sweep by name fields (catches any stragglers)
  await this.sweepSynctestRecords();
}
```

#### Step 3.1.5: Verify syntax

```bash
node -c tools/debug-server/supabase-verifier.js
```

Expected: No syntax errors.

---

### Sub-phase 3.0: Pre-flight security check
**Agent:** `general-purpose`

#### Step 3.0.1: Verify .env.test is gitignored

Before creating or touching any `.env.test` file:

```bash
git check-ignore -v tools/debug-server/.env.test
```

Expected: Output shows the file is matched by a gitignore rule. If not, add it to `.gitignore` before proceeding. **Never commit `.env.test` — it contains Supabase service role credentials.**

---

### Sub-phase 3.2: Test runner CLI flags
**Files:** `tools/debug-server/run-tests.js` (or equivalent main runner file)
**Agent:** `general-purpose`

#### Step 3.2.1: Read current runner

The implementing agent MUST read the runner file to understand its current structure.

<!-- NOTE: The runner file may be named differently. Check:
     - tools/debug-server/run-tests.js
     - tools/debug-server/index.js
     - tools/debug-server/server.js (already known to be the debug server)
     The implementing agent should glob for *.js in tools/debug-server/ to find it. -->

> **NOTE FOR IMPLEMENTING AGENT — TestRunner class structure:** Read `tools/debug-server/run-tests.js` (or wherever TestRunner lives) to understand the actual class structure before modifying lifecycle methods. The `ctx` object must be threaded through the existing runner's scenario execution path — do NOT bolt on a standalone `runTests()` function if one already exists. The lifecycle pseudocode in Step 3.2.3 must be integrated into whatever structure the existing runner already uses.

#### Step 3.2.2: Add CLI flag parsing

Add or update CLI argument parsing for the new flags.

> **NOTE FOR IMPLEMENTING AGENT:** The existing run-tests.js uses switch-case parsing (not `startsWith`). Follow the existing pattern in the file — do NOT introduce a new `args.find(a => a.startsWith(...))` style if the file already uses switch-case. Integrate the new flags into the existing arg-parsing block.

The flags to support (translated to the existing style):

```js
// FROM SPEC: CLI Flags section — integrate into existing switch-case pattern
// New flags to add:
// --cleanup-only  → run sweep and exit
// --keep-fixture  → skip teardown after run
// --layer=L2|L3   → filter by layer
// --table=<name>  → filter by table name
// --filter=<str>  → filter scenario names by substring
```

#### Step 3.2.3: Implement run lifecycle

Update the main run function to follow the lifecycle:

```js
async function runTests() {
  // 1. Pre-flight
  console.log('=== Pre-flight checks ===');
  // ... existing pre-flight (env, CLI, device, Supabase connectivity)

  // 2. --cleanup-only mode
  if (flags.cleanupOnly) {
    console.log('=== Cleanup-only mode ===');
    const swept = await verifier.sweepSynctestRecords();
    console.log(`Swept ${swept} SYNCTEST records`);
    return;
  }

  // 3. SYNCTEST-* sweep (always, catches prior orphans)
  console.log('=== Pre-run sweep ===');
  await verifier.sweepSynctestRecords();

  // 4. Setup shared fixture
  console.log('=== Setting up shared fixture ===');
  const ctx = await verifier.setupSharedFixture(companyId, adminUserId, inspectorUserId);

  // 5. Sync fixture to device
  await device.triggerSync();
  await device.waitForSyncComplete();

  try {
    // 6. Execute scenarios
    // ... run scenarios with ctx passed to each run() function
    // Order: S1→S2→S3→S4 per table, then S5 per table last

    // 7. Report
  } finally {
    // 8. Teardown (unless --keep-fixture)
    if (!flags.keepFixture) {
      console.log('=== Teardown ===');
      await verifier.teardownFixture(ctx);
    }
  }
}
```

<!-- NOTE: The implementing agent must integrate this with the existing runner structure.
     The exact integration depends on how scenarios are currently loaded and executed. -->

#### Step 3.2.4: Update scenario execution to pass ctx

Find where scenarios' `run()` functions are called and add `ctx`:

```js
// OLD:
await scenario.run({ verifier, device });

// NEW:
await scenario.run({ verifier, device, ctx });
```

#### Step 3.2.5: Verify syntax

```bash
node -c tools/debug-server/run-tests.js
```

Expected: No syntax errors.

---

## Phase 4: L2 Scenario Rewrites (JS)

### Sub-phase 4.1: S1 (push) scenarios
**Files:** All `*-S1-push.js` files in `tools/debug-server/scenarios/L2/`
**Agent:** `general-purpose`

#### Step 4.1.1: Canonical S1 template — contractors-S1-push.js

This is the complete template for ALL S1 scenarios:

```js
// tools/debug-server/scenarios/L2/contractors-S1-push.js
const { makeContractor, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

// FROM SPEC: S1 pattern — Create locally -> sync -> verify on Supabase -> soft-delete -> verify cleanup
module.exports = {
  name: 'contractors-S1-push',
  description: 'Create contractor locally, push to Supabase, verify, clean up',

  async run({ verifier, device, ctx }) {
    // 1. Create record locally via the app
    const record = makeContractor({
      project_id: ctx.projectId,
      company_id: ctx.companyId,
      name: `SYNCTEST-contractor-push-${Date.now()}`,
    });
    await device.createRecord('contractors', record);

    // 2. Sync to Supabase
    await device.triggerSync();
    await device.waitForSyncComplete();

    // 3. Verify on Supabase
    const serverRow = await verifier.getRecord('contractors', record.id);
    if (!serverRow) throw new Error('Contractor not found on server after push');
    if (serverRow.name !== record.name) throw new Error('Contractor name mismatch on server');

    // 4. Soft-delete and verify cleanup
    await softDeleteAndVerify(verifier, device, 'contractors', record.id);

    // 5. Ensure sync is clean
    await waitForSyncClean(device);
  },
};
```

#### Step 4.1.2: All S1 files and their table-specific differences

| File | Table | Factory | Parent IDs from ctx | Name/key field | Verification field |
|------|-------|---------|--------------------|-----------------|--------------------|
| `bid-items-S1-push.js` | `bid_items` | `makeBidItem` | `project_id: ctx.projectId` | `name` | `name` |
| `calculation-history-S1-push.js` | `calculation_history` | `makeCalculationHistory` | `ctx` (full) | N/A (no name) | `calculation_type` |
| `contractors-S1-push.js` | `contractors` | `makeContractor` | `project_id: ctx.projectId` | `name` | `name` |
| `daily-entries-S1-push.js` | `daily_entries` | `makeDailyEntry` | `project_id: ctx.projectId, location_id: ctx.locationId` | N/A | `status` |
| `entry-contractors-S1-push.js` | `entry_contractors` | `makeEntryContractor` | `ctx` (full) | N/A | `worker_count` |
| `entry-equipment-S1-push.js` | `entry_equipment` | `makeEntryEquipment` | `ctx` (full) | N/A | `hours_used` |
| `entry-personnel-counts-S1-push.js` | `entry_personnel_counts` | `makeEntryPersonnelCount` | `ctx` (full) | N/A | `count` |
| `equipment-S1-push.js` | `equipment` | `makeEquipment` | `project_id: ctx.projectId` | `name` | `name` |
| `form-responses-S1-push.js` | `form_responses` | `makeFormResponse` | `inspector_form_id: ctx.inspectorFormId, project_id: ctx.projectId` | N/A | (check exists) |
| `inspector-forms-S1-push.js` | `inspector_forms` | `makeInspectorForm` | `project_id: ctx.projectId` | `name` | `name` |
| `locations-S1-push.js` | `locations` | `makeLocation` | `project_id: ctx.projectId` | `name` | `name` |
| `personnel-types-S1-push.js` | `personnel_types` | `makePersonnelType` | `project_id: ctx.projectId` | `name` | `name` |
| `photos-S3-delete-push.js` | N/A — this is S3, not S1 | — | — | — | — |
| `projects-S1-push.js` | `projects` | `makeProject` | `company_id: ctx.companyId` | `name` | `name` |
| `todo-items-S1-push.js` | `todo_items` | `makeTodoItem` | `ctx` (full) | `title` | `title` |

<!-- NOTE: For factories that take `ctx` as first arg (new factories), call as makeX(ctx, overrides).
     For existing factories that take only overrides, call as makeX(overrides). The implementing agent
     must check each factory signature. -->

---

### Sub-phase 4.2: S2 (update-push) scenarios
**Files:** All `*-S2-update-push.js` files in `tools/debug-server/scenarios/L2/`
**Agent:** `general-purpose`

#### Step 4.2.1: Canonical S2 template — contractors-S2-update-push.js

```js
const { makeContractor, seedAndSync, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

// FROM SPEC: S2 pattern — Seed in Supabase -> sync to device -> update locally -> sync -> verify -> soft-delete
module.exports = {
  name: 'contractors-S2-update-push',
  description: 'Seed contractor, sync, update locally, push update, verify',

  async run({ verifier, device, ctx }) {
    // 1. Seed record in Supabase
    const record = makeContractor({
      project_id: ctx.projectId,
      company_id: ctx.companyId,
      name: `SYNCTEST-contractor-s2-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'contractors', record);

    // 2. Update locally
    const updatedName = `SYNCTEST-contractor-s2-updated-${Date.now()}`;
    await device.updateRecord('contractors', record.id, { name: updatedName });

    // 3. Sync update to Supabase
    await device.triggerSync();
    await device.waitForSyncComplete();

    // 4. Verify update on server
    const serverRow = await verifier.getRecord('contractors', record.id);
    if (serverRow.name !== updatedName) {
      throw new Error(`Update not pushed: expected ${updatedName}, got ${serverRow.name}`);
    }

    // 5. Clean up
    await softDeleteAndVerify(verifier, device, 'contractors', record.id);
    await waitForSyncClean(device);
  },
};
```

#### Step 4.2.2: All S2 files and their table-specific differences

| File | Table | Factory | Update field | Update value |
|------|-------|---------|-------------|--------------|
| `bid-items-S2-update-push.js` | `bid_items` | `makeBidItem` | `name` | `SYNCTEST-bid-item-s2-updated-${Date.now()}` |
| `contractors-S2-update-push.js` | `contractors` | `makeContractor` | `name` | `SYNCTEST-contractor-s2-updated-${Date.now()}` |
| `daily-entries-S2-update-push.js` | `daily_entries` | `makeDailyEntry` | `notes` | `SYNCTEST-updated-notes-${Date.now()}` |
| `entry-contractors-S2-update-push.js` | `entry_contractors` | `makeEntryContractor` | `worker_count` | `7` |
| `entry-equipment-S2-update-push.js` | `entry_equipment` | `makeEntryEquipment` | `hours_used` | `9.5` |
| `entry-personnel-counts-S2-update-push.js` | `entry_personnel_counts` | `makeEntryPersonnelCount` | `count` | `12` |
| `equipment-S2-update-push.js` | `equipment` | `makeEquipment` | `name` | `SYNCTEST-equipment-s2-updated-${Date.now()}` |
| `form-responses-S2-update-push.js` | `form_responses` | `makeFormResponse` | `response_data` | `JSON.stringify({updated: true})` |
| `inspector-forms-S2-update-push.js` | `inspector_forms` | `makeInspectorForm` | `name` | `SYNCTEST-form-s2-updated-${Date.now()}` |
| `locations-S2-update-push.js` | `locations` | `makeLocation` | `name` | `SYNCTEST-location-s2-updated-${Date.now()}` |
| `personnel-types-S2-update-push.js` | `personnel_types` | `makePersonnelType` | `name` | `SYNCTEST-type-s2-updated-${Date.now()}` |
| `project-assignments-S2-update-push.js` | `project_assignments` | `makeProjectAssignment` | `role` | `'lead_inspector'` |
| `projects-S2-update-push.js` | `projects` | `makeProject` | `name` | `SYNCTEST-project-s2-updated-${Date.now()}` |
| `todo-items-S2-update-push.js` | `todo_items` | `makeTodoItem` | `title` | `SYNCTEST-todo-s2-updated-${Date.now()}` |

---

### Sub-phase 4.3: S3 (delete-push) scenarios
**Files:** All `*-S3-delete-push.js` files in `tools/debug-server/scenarios/L2/`
**Agent:** `general-purpose`

#### Step 4.3.1: Canonical S3 template — contractors-S3-delete-push.js

```js
const { makeContractor, seedAndSync, waitForSyncClean } = require('../../scenario-helpers');

// FROM SPEC: S3 pattern — Seed -> sync -> delete via app -> sync -> verify deleted_at on Supabase
// NOTE: This IS the test — verifying that app-initiated deletes propagate correctly
module.exports = {
  name: 'contractors-S3-delete-push',
  description: 'Seed contractor, sync, delete via app, verify deleted_at on Supabase',

  async run({ verifier, device, ctx }) {
    // 1. Seed record in Supabase
    const record = makeContractor({
      project_id: ctx.projectId,
      company_id: ctx.companyId,
      name: `SYNCTEST-contractor-s3-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'contractors', record);

    // 2. Delete via the app (soft-delete locally)
    await device.softDelete('contractors', record.id);

    // 3. Sync to Supabase
    await device.triggerSync();
    await device.waitForSyncComplete();

    // 4. Verify deleted_at is set on Supabase (THIS IS THE TEST)
    const serverRow = await verifier.getRecord('contractors', record.id);
    if (!serverRow) {
      // NOTE: Fix A handles this — if record was hard-deleted, sync shouldn't crash
      throw new Error('Record missing from server entirely (unexpected hard-delete?)');
    }
    if (!serverRow.deleted_at) {
      throw new Error('deleted_at not set on server after delete-push');
    }

    // 5. Sync should be clean (no retry loops)
    await waitForSyncClean(device);
  },
};
```

#### Step 4.3.2: All S3 files and their table-specific differences

| File | Table | Factory | Parent IDs |
|------|-------|---------|-----------|
| `bid-items-S3-delete-push.js` | `bid_items` | `makeBidItem` | `project_id: ctx.projectId` |
| `contractors-S3-delete-push.js` | `contractors` | `makeContractor` | `project_id: ctx.projectId` |
| `daily-entries-S3-delete-push.js` | `daily_entries` | `makeDailyEntry` | `project_id: ctx.projectId, location_id: ctx.locationId` |
| `entry-contractors-S3-delete-push.js` | `entry_contractors` | `makeEntryContractor` | `ctx` (full) |
| `entry-equipment-S3-delete-push.js` | `entry_equipment` | `makeEntryEquipment` | `ctx` (full) |
| `entry-personnel-counts-S3-delete-push.js` | `entry_personnel_counts` | `makeEntryPersonnelCount` | `ctx` (full) |
| `equipment-S3-delete-push.js` | `equipment` | `makeEquipment` | `project_id: ctx.projectId` |
| `form-responses-S3-delete-push.js` | `form_responses` | `makeFormResponse` | `inspector_form_id: ctx.inspectorFormId, project_id: ctx.projectId` |
| `inspector-forms-S3-delete-push.js` | `inspector_forms` | `makeInspectorForm` | `project_id: ctx.projectId` |
| `locations-S3-delete-push.js` | `locations` | `makeLocation` | `project_id: ctx.projectId` |
| `personnel-types-S3-delete-push.js` | `personnel_types` | `makePersonnelType` | `project_id: ctx.projectId` |
| `photos-S3-delete-push.js` | `photos` | `makePhoto` | `ctx` (full) |
| `project-assignments-S3-delete-push.js` | `project_assignments` | `makeProjectAssignment` | `ctx` (full) |
| `projects-S3-delete-push.js` | `projects` | `makeProject` | `company_id: ctx.companyId` |
| `todo-items-S3-delete-push.js` | `todo_items` | `makeTodoItem` | `ctx` (full) |

---

### Sub-phase 4.4: S4 (conflict) scenarios
**Files:** All `*-S4-conflict.js` files in `tools/debug-server/scenarios/L2/`
**Agent:** `general-purpose`

#### Step 4.4.1: Canonical S4 template — contractors-S4-conflict.js

```js
const { makeContractor, seedAndSync, runConflictPhase, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

// FROM SPEC: S4 pattern — Seed -> sync -> Phase 1 (remote wins) -> Phase 2 (local wins) -> soft-delete
module.exports = {
  name: 'contractors-S4-conflict',
  description: 'Contractor conflict resolution: remote-wins then local-wins',

  async run({ verifier, device, ctx }) {
    // 1. Seed record in Supabase
    const record = makeContractor({
      project_id: ctx.projectId,
      company_id: ctx.companyId,
      name: `SYNCTEST-contractor-s4-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'contractors', record);

    // 2. Phase 1: Remote wins
    await runConflictPhase(device, verifier, {
      table: 'contractors',
      id: record.id,
      field: 'name',
      localValue: 'SYNCTEST-local-phase1',
      remoteValue: 'SYNCTEST-remote-phase1',
      expectedWinner: 'remote',
    });

    // 3. Phase 2: Local wins
    await runConflictPhase(device, verifier, {
      table: 'contractors',
      id: record.id,
      field: 'name',
      localValue: 'SYNCTEST-local-phase2',
      remoteValue: 'SYNCTEST-remote-phase2',
      expectedWinner: 'local',
    });

    // 4. Clean up
    await softDeleteAndVerify(verifier, device, 'contractors', record.id);
    await waitForSyncClean(device);
  },
};
```

#### Step 4.4.2: All S4 files and their table-specific differences

| File | Table | Factory | Conflict field | Local values | Remote values |
|------|-------|---------|---------------|-------------|---------------|
| `contractors-S4-conflict.js` | `contractors` | `makeContractor` | `name` | `SYNCTEST-local-phase{N}` | `SYNCTEST-remote-phase{N}` |
| `daily-entries-S4-conflict.js` | `daily_entries` | `makeDailyEntry` | `notes` | `SYNCTEST-local-notes-{N}` | `SYNCTEST-remote-notes-{N}` |
| `entry-contractors-S4-conflict.js` | `entry_contractors` | `makeEntryContractor` | `worker_count` | `5` / `15` | `10` / `20` |
| `entry-equipment-S4-conflict.js` | `entry_equipment` | `makeEntryEquipment` | `hours_used` | `3.0` / `7.0` | `6.0` / `2.0` |
| `entry-personnel-counts-S4-conflict.js` | `entry_personnel_counts` | `makeEntryPersonnelCount` | `count` | `3` / `15` | `8` / `20` |
| `equipment-S4-conflict.js` | `equipment` | `makeEquipment` | `name` | `SYNCTEST-local-phase{N}` | `SYNCTEST-remote-phase{N}` |
| `form-responses-S4-conflict.js` | `form_responses` | `makeFormResponse` | `response_data` | `JSON.stringify({local: N})` | `JSON.stringify({remote: N})` |
| `project-assignments-S4-conflict.js` | `project_assignments` | `makeProjectAssignment` | `role` | `'inspector'` / `'lead_inspector'` | `'lead_inspector'` / `'inspector'` |

---

### Sub-phase 4.5: S5 (fresh-pull) scenarios
**Files:** All `*-S5-fresh-pull.js` files in `tools/debug-server/scenarios/L2/`
**Agent:** `general-purpose`

#### Step 4.5.1: Canonical S5 template — contractors-S5-fresh-pull.js

```js
const { makeContractor, seedAndSync, verifyPulled, softDeleteAndVerify, waitForSyncClean } = require('../../scenario-helpers');

// FROM SPEC: S5 pattern — Seed -> sync -> remove-from-device -> re-sync -> verify restored -> soft-delete
// NOTE: S5 runs LAST per table (after S1-S4) per spec
module.exports = {
  name: 'contractors-S5-fresh-pull',
  description: 'Seed contractor, sync, remove from device, re-sync, verify restored',

  async run({ verifier, device, ctx }) {
    // 1. Seed record in Supabase
    const record = makeContractor({
      project_id: ctx.projectId,
      company_id: ctx.companyId,
      name: `SYNCTEST-contractor-s5-${Date.now()}`,
    });
    await seedAndSync(verifier, device, 'contractors', record);

    // 2. Verify it's on device
    await verifyPulled(device, 'contractors', record.id);

    // 3. Remove from device (local-only delete, not synced)
    await device.removeLocalRecord('contractors', record.id);

    // 4. Re-sync — should pull it back
    await device.triggerSync();
    await device.waitForSyncComplete();

    // 5. Verify restored on device
    await verifyPulled(device, 'contractors', record.id);

    // 6. Clean up
    await softDeleteAndVerify(verifier, device, 'contractors', record.id);
    await waitForSyncClean(device);
  },
};
```

#### Step 4.5.2: All S5 files and their table-specific differences

| File | Table | Factory | Parent IDs |
|------|-------|---------|-----------|
| `contractors-S5-fresh-pull.js` | `contractors` | `makeContractor` | `project_id: ctx.projectId` |
| `entry-contractors-S5-fresh-pull.js` | `entry_contractors` | `makeEntryContractor` | `ctx` (full) |
| `entry-equipment-S5-fresh-pull.js` | `entry_equipment` | `makeEntryEquipment` | `ctx` (full) |
| `entry-personnel-counts-S5-fresh-pull.js` | `entry_personnel_counts` | `makeEntryPersonnelCount` | `ctx` (full) |
| `equipment-S5-fresh-pull.js` | `equipment` | `makeEquipment` | `project_id: ctx.projectId` |
| `form-responses-S5-fresh-pull.js` | `form_responses` | `makeFormResponse` | `inspector_form_id: ctx.inspectorFormId, project_id: ctx.projectId` |
| `project-assignments-S5-fresh-pull.js` | `project_assignments` | `makeProjectAssignment` | `ctx` (full) |

---

### Sub-phase 4.6: Verify all L2 scenarios
**Agent:** `general-purpose`

#### Step 4.6.1: Syntax check all L2 files

```bash
for f in tools/debug-server/scenarios/L2/*.js; do node -c "$f" || echo "FAIL: $f"; done
```

Expected: No syntax errors.

---

## Phase 5: L3 Scenario Rewrites (JS)

### Sub-phase 5.1: Update all L3 scenarios
**Files:** All 10 files in `tools/debug-server/scenarios/L3/`
**Agent:** `general-purpose`

#### Step 5.1.1: Read all L3 scenarios

The implementing agent must read each L3 file to understand its current structure. L3 scenarios are cross-cutting multi-device tests — they are more complex than L2 and each is unique.

#### Step 5.1.2: Update signature and use ctx

For each L3 scenario, apply these changes:

1. **Update function signature:** `async run({ verifier, device })` -> `async run({ verifier, device, ctx })`
2. **Replace inline project/fixture creation** with `ctx` references
3. **Replace cleanup logic** with `softDeleteAndVerify` / `waitForSyncClean` where appropriate
4. **Ensure SYNCTEST- prefix** on all test data names

**L3 files to update:**

| File | Description | Key changes |
|------|-------------|-------------|
| `X1-admin-creates-inspector-pulls.js` | Admin creates, inspector pulls | Use ctx.projectId, ctx fixtures |
| `X2-inspector-creates-admin-sees.js` | Inspector creates, admin sees | Use ctx.projectId |
| `X3-simultaneous-edit-conflict.js` | Two-device conflict | Use ctx fixtures for seeding |
| `X5-inspector-offline-reconnect.js` | Offline/reconnect flow | Use ctx.projectId |
| `X6-offline-conflict-cross-device.js` | Offline conflict across devices | Use ctx fixtures |
| `X7-photo-offline-sync.js` | Photo sync after offline | Use ctx.dailyEntryId |
| `X10-fk-ordering-under-load.js` | FK ordering stress test | Use ctx fixtures as parents |

<!-- NOTE: X4, X8, X9 may not exist yet. The implementing agent should check what files
     are actually present and only modify existing ones. -->

#### Step 5.1.3: Verify all L3 scenarios

```bash
for f in tools/debug-server/scenarios/L3/*.js; do node -c "$f" || echo "FAIL: $f"; done
```

Expected: No syntax errors.

---

## Phase 6: Widget Key Verification

### Sub-phase 6.1: Verify EntriesTestingKeys
**Files:** `lib/features/entries/presentation/` (exact file TBD)
**Agent:** `frontend-flutter-specialist-agent`

#### Step 6.1.1: Find and verify widget keys

The implementing agent must:

1. Search for `EntriesTestingKeys` or equivalent in `lib/features/entries/`
2. Verify these keys exist (needed by L2 daily-entries-S1-push for UI navigation):
   - Entry create button
   - Date field / date picker
   - Save button
   - Entry list item (for selection)
3. If any key is missing, add it following the pattern of `ProjectsTestingKeys`

#### Step 6.1.2: Verify existing keys are correct

Confirm these key sets exist and are used in widgets:

- `ProjectsTestingKeys`: `projectCreateButton`, `projectNameField`, `projectNumberField`, `projectSaveButton`
- `ToolboxTestingKeys`: `todosAddButton`, `todosTitleField`, `todosSaveButton`, `calculatorSaveButton`, `calculatorHmaArea`, `calculatorHmaThickness`, `calculatorHmaDensity`, `calculatorCalculateButton`

```
pwsh -Command "flutter analyze lib/features/entries/ lib/features/projects/ lib/features/toolbox/"
```

Expected: No errors.

---

## Phase 7: RLS Audit

### Sub-phase 7.1: Query Supabase RLS policies
**Agent:** `backend-supabase-agent`

#### Step 7.1.1: Pull and inspect RLS policies

```bash
npx supabase db pull --schema public
```

Then check each of the 17 synced tables for RLS policies:

**Tables to audit:**
```
projects, project_assignments, locations, contractors, equipment, bid_items,
personnel_types, daily_entries, photos, entry_equipment, entry_quantities,
entry_contractors, entry_personnel_counts, inspector_forms, form_responses,
todo_items, calculation_history
```

For each table, verify:
1. RLS is enabled (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`)
2. SELECT policy exists for authenticated users (scoped to company_id)
3. INSERT policy exists for authenticated users
4. UPDATE policy exists for authenticated users
5. DELETE policy exists (or soft-delete-only pattern enforced)

#### Step 7.1.2: Document findings

Create a verification comment in the test runner or a separate audit log:

```js
// RLS Audit 2026-03-24: All 17 synced tables verified
// - All have RLS enabled
// - All have company_id-scoped SELECT policies
// - [note any exceptions or findings]
```

<!-- NOTE: The implementing agent should report any missing or misconfigured policies
     for the user to review. Do NOT auto-fix RLS policies without explicit approval. -->

---

## Phase 8: Smoke Test

### Sub-phase 8.1: Run contractors L2 suite
**Agent:** `general-purpose`

#### Step 8.1.1: Run single-table test

```bash
cd tools/debug-server && node run-tests.js --layer=L2 --table=contractors
```

Expected:
- Pre-run sweep completes
- Shared fixture created (1 project, 9 fixture records)
- contractors-S1-push: PASS
- contractors-S2-update-push: PASS
- contractors-S3-delete-push: PASS
- contractors-S4-conflict: PASS
- contractors-S5-fresh-pull: PASS
- Teardown completes
- 0 SYNCTEST-* records remain

#### Step 8.1.2: Verify cleanup

```bash
cd tools/debug-server && node run-tests.js --cleanup-only
```

Expected: `Swept 0 SYNCTEST records` (everything was already cleaned up).

#### Step 8.1.3: Run full L2 suite (if single table passes)

```bash
cd tools/debug-server && node run-tests.js --layer=L2
```

Expected: All scenarios pass with single shared project.

---

## Summary of All Files Modified

### Dart files (Phase 1):
- `lib/features/sync/engine/sync_engine.dart` — Fix A + Fix B callsite
- `lib/features/sync/application/sync_orchestrator.dart` — Fix C
- `lib/features/sync/engine/integrity_checker.dart` — Fix B (purgeOrphans method)
- `lib/features/sync/engine/change_tracker.dart` — getPendingRecordIds (if needed)
- `test/features/sync/sync_engine_delete_test.dart` — New unit tests

### JS files (Phases 2-5):
- `tools/debug-server/scenario-helpers.js` — TestContext, 8 factories, 5 helpers
- `tools/debug-server/supabase-verifier.js` — sweep, setupSharedFixture, teardownFixture
- `tools/debug-server/run-tests.js` — CLI flags, lifecycle, ctx passing
- 84 L2 scenario files in `tools/debug-server/scenarios/L2/`
- 7-10 L3 scenario files in `tools/debug-server/scenarios/L3/`

### Widget key files (Phase 6):
- `lib/features/entries/presentation/` — verify/add testing keys
- `lib/features/projects/presentation/` — verify existing keys
- `lib/features/toolbox/presentation/` — verify existing keys
