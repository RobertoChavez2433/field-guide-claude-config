# Sync Hardening & RLS Enforcement Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Fix two critical blockers (pulled projects not importable, 8 tables missing RLS) and 8 audit findings (per-record FK blocking, company_id stamping, conflict ping-pong, offline removal safety, silent drop logging, crash recovery docs, RLS 42501 notification).
**Spec:** Derived from systematic debugging session S584 research agents.
**Analysis:** `.claude/dependency_graphs/2026-03-17-sync-hardening-and-rls/analysis.md`
**Reviews:** `.claude/code-reviews/2026-03-17-sync-hardening-and-rls-plan-review.md`

**Architecture:** Sync engine push/pull hardening with per-record granularity, Supabase RLS enforcement on all core tables, conflict circuit breaker, and user-visible error surfacing for permission denials.
**Tech Stack:** Flutter, SQLite (sqflite), Supabase (PostgreSQL + RLS), ChangeNotifier providers
**Blast Radius:** 1 new migration file, 8 modified files, 4 test files updated

### Review Findings Applied
- **CR-CRIT-1**: Offline removal guard moved to service layer (Phase 4.1)
- **CR-CRIT-2**: ConflictResolver uses query-based approach, preserving `Future<ConflictWinner>` return type
- **CR-HIGH-3**: DB version bump to 36 + createConflictLogTable updated
- **CR-HIGH-4**: hasFailedRecord() exists — no new method needed
- **CR-HIGH-5**: All SyncEngineResult construction sites enumerated
- **CR-HIGH-6**: Supabase migration uses `DROP POLICY IF EXISTS` + rollback block
- **CR-HIGH-7**: Phases 2.1.1 and 3.2.1 consolidated into single final code block
- **CR-MED-8**: Phase 4 reuses existing `isOffline` variable
- **CR-MED-9**: Magic number 3 → `SyncEngineConfig.conflictPingPongThreshold`
- **SEC-CRIT-1**: Migration defensively drops all known policy name variants
- **SEC-CRIT-2**: Step 1.2.2 expanded to cover entry_equipment and entry_contractors
- **SEC-HIGH-2**: company_id comparison uses `?.toString()`
- **SEC-HIGH-3**: Conflict_log cleanup for circuit-broken records added
- **SEC-LOW-1**: EntryPersonnelCountsAdapter fkColumnMap corrected to `type_id`

---

## Phase 1: Schema Changes (Local SQLite + Supabase Migration)

---

### Sub-phase 1.1: Add conflict_count to conflict_log Table

**Files:**
- Modify: `lib/core/database/schema/sync_engine_tables.dart`
- Modify: `lib/core/database/database_service.dart`
- Test: `test/features/sync/engine/conflict_resolver_test.dart`

**Agent**: backend-data-layer-agent

#### Step 1.1.1: Add conflict_count column to conflict_log CREATE TABLE constant

In `sync_engine_tables.dart:36-47`, add `conflict_count INTEGER NOT NULL DEFAULT 0` to the `createConflictLogTable` constant so new installs get the column.

#### Step 1.1.2: Bump database version to 36

In `database_service.dart:53` (or wherever `_databaseVersion` is defined), change from `35` to `36`.

#### Step 1.1.3: Add migration block for existing databases

In `database_service.dart:_onUpgrade()`, add:
```dart
if (oldVersion < 36) {
  await _addColumnIfNotExists(db, 'conflict_log', 'conflict_count', 'INTEGER NOT NULL DEFAULT 0');
}
```

#### Step 1.1.4: Add conflictPingPongThreshold to SyncEngineConfig

In the `SyncEngineConfig` class (or `sync_config.dart`), add:
```dart
/// Maximum consecutive local-wins conflicts before circuit breaker stops re-pushing.
static const int conflictPingPongThreshold = 3;
```

#### Step 1.1.5: Write test verifying conflict_count column exists after migration

```dart
test('conflict_log has conflict_count column after migration', () async {
  final info = await db.rawQuery('PRAGMA table_info(conflict_log)');
  final columns = info.map((r) => r['name'] as String).toList();
  expect(columns, contains('conflict_count'));
});
```

---

### Sub-phase 1.2: Supabase RLS Migration

**Files:**
- Create: `supabase/migrations/20260317000000_enable_rls_core_tables.sql`

**Agent**: backend-supabase-agent

#### Step 1.2.1: Write migration to ENABLE ROW LEVEL SECURITY on 8 tables

```sql
-- supabase/migrations/20260317000000_enable_rls_core_tables.sql

-- WHY: These 8 tables were assumed to have RLS by multi_tenant_foundation.sql but didn't.
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE bid_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE entry_quantities ENABLE ROW LEVEL SECURITY;
ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE contractors ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipment ENABLE ROW LEVEL SECURITY;
```

#### Step 1.2.2: Replace USING(true) policies with company-scoped policies

**IMPORTANT**: Use `DROP POLICY IF EXISTS` for ALL known policy name variants before `CREATE POLICY`. The `multi_tenant_foundation.sql` migration may have already replaced these policies. The migration must be defensive — if a policy already exists with the correct name, drop it first to avoid `42710 already exists` errors.

Cover ALL 5 tables that had `USING(true)` anon policies in `catchup_v23.sql`: `personnel_types`, `entry_personnel_counts`, `entry_personnel`, `entry_equipment`, `entry_contractors`.

For each table, the pattern is:
```sql
-- Defensively drop ALL known policy name variants (old anon names + current company names)
DROP POLICY IF EXISTS "anon_select_{table}" ON {table};
DROP POLICY IF EXISTS "anon_insert_{table}" ON {table};
DROP POLICY IF EXISTS "anon_update_{table}" ON {table};
DROP POLICY IF EXISTS "anon_delete_{table}" ON {table};
DROP POLICY IF EXISTS "Authenticated users can manage {table}" ON {table};
DROP POLICY IF EXISTS "company_{table}_select" ON {table};
DROP POLICY IF EXISTS "company_{table}_insert" ON {table};
DROP POLICY IF EXISTS "company_{table}_update" ON {table};
DROP POLICY IF EXISTS "company_{table}_delete" ON {table};

-- Recreate company-scoped policies using the appropriate FK chain
CREATE POLICY "company_{table}_select" ON {table} FOR SELECT TO authenticated
  USING ({fk_chain_to_company});
CREATE POLICY "company_{table}_insert" ON {table} FOR INSERT TO authenticated
  WITH CHECK ({fk_chain_to_company} AND NOT is_viewer());
-- ... update and delete similarly
```

FK chains:
- `personnel_types`: `project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())`
- `entry_personnel_counts`: `entry_id IN (SELECT id FROM daily_entries WHERE project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id()))`
- `entry_personnel`: same two-hop as entry_personnel_counts
- `entry_equipment`: same two-hop via daily_entries
- `entry_contractors`: same two-hop via daily_entries

**NOTE**: `multi_tenant_foundation.sql` already created company-scoped policies for `entry_equipment` and `entry_contractors`. The DROP IF EXISTS / CREATE pattern ensures idempotency regardless of prior migration state.

#### Step 1.2.3: Add performance indexes

```sql
-- WHY: RLS policies filter by project_id/contractor_id — indexes prevent full scans.
CREATE INDEX IF NOT EXISTS idx_daily_entries_project ON daily_entries(project_id);
CREATE INDEX IF NOT EXISTS idx_bid_items_project ON bid_items(project_id);
CREATE INDEX IF NOT EXISTS idx_locations_project ON locations(project_id);
CREATE INDEX IF NOT EXISTS idx_contractors_project ON contractors(project_id);
CREATE INDEX IF NOT EXISTS idx_photos_project ON photos(project_id);
CREATE INDEX IF NOT EXISTS idx_equipment_contractor ON equipment(contractor_id);
```

#### Step 1.2.4: Add rollback block to migration

At the top of the migration file, add a commented rollback section:
```sql
-- ROLLBACK (run manually if needed):
-- ALTER TABLE projects DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE daily_entries DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE photos DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE bid_items DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE entry_quantities DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE locations DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE contractors DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE equipment DISABLE ROW LEVEL SECURITY;
```

#### Step 1.2.5: Verify live state before push

Run against the live Supabase instance:
```sql
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public' ORDER BY tablename;
```
Confirm the 8 tables listed in Step 1.2.1 actually have `rowsecurity = false`.

#### Step 1.2.6: Push migration to Supabase

Run: `npx supabase db push`

Verify no errors. The migration must be atomic — all ENABLE + policy changes in a single transaction.

---

## Phase 2: Sync Engine Core Fixes (BLOCKERS + Push Hardening)

---

### Sub-phase 2.1: BLOCKER-38 — Pulled Projects Enrolled in synced_projects

**Files:**
- Modify: `lib/features/sync/engine/sync_engine.dart` (two locations)
- Test: `test/features/sync/engine/sync_engine_test.dart`

**Agent**: backend-supabase-agent

#### Step 2.1.1: Replace insert block with consolidated enrollment + logging

In `_pullTable()`, replace the insert block at ~line 1035-1042 with this consolidated block that handles BOTH BLOCKER-38 enrollment AND silent-drop logging (Phase 3.2). This is the FINAL form — Phase 3.2 does NOT modify this block again.

```dart
final filtered = _stripUnknownColumns(remote, localColumns);
final rowId = await db.insert(
  adapter.tableName,
  filtered,
  conflictAlgorithm: ConflictAlgorithm.ignore,
);
// WHY: ConflictAlgorithm.ignore returns 0 when insert is silently dropped.
// Log it so we know data was skipped rather than losing it invisibly.
if (rowId == 0) {
  Logger.sync('Pull insert ignored (constraint conflict): ${adapter.tableName}/$recordId');
} else {
  totalPulled++;
  // WHY: BLOCKER-38 — pulled projects must be enrolled so child adapters can sync their data.
  if (adapter.tableName == 'projects') {
    await db.insert('synced_projects', {
      'project_id': recordId,
      'synced_at': DateTime.now().toUtc().toIso8601String(),
    }, conflictAlgorithm: ConflictAlgorithm.ignore);
    Logger.sync('Auto-enrolled pulled project: $recordId');
  }
}
```

#### Step 2.1.2: Reload _syncedProjectIds after projects adapter completes

In `_pull()`, after the projects adapter finishes (inside the `for` loop over adapters), reload the synced project IDs so child adapters see new projects:

```dart
try {
  final count = await _pullTable(adapter);
  pulled += count;
  // WHY: BLOCKER-38 — child adapters need fresh project IDs from projects just pulled.
  if (adapter.tableName == 'projects' && count > 0) {
    await _loadSyncedProjectIds();
    Logger.sync('Reloaded synced project IDs after pulling $count projects');
  }
} catch (e) {
  // ... existing error handling ...
}
```

#### Step 2.1.3: Write tests for BLOCKER-38

```dart
test('pulled project is auto-enrolled in synced_projects', () async {
  // Setup: mock Supabase returns a project not in synced_projects
  // Act: run _pull()
  // Assert: synced_projects contains the new project_id
});

test('child adapters see projects pulled in same cycle', () async {
  // Setup: mock Supabase returns a project + daily_entries for that project
  // Act: run _pull()
  // Assert: daily_entries were pulled (not skipped due to missing project)
});
```

---

### Sub-phase 2.2: AUDIT FIX 1 — Per-Record FK Blocking

**Files:**
- Modify: `lib/features/sync/engine/adapters/*.dart` (add fkColumnMap to each adapter)
- Modify: `lib/features/sync/engine/sync_engine.dart` (`_push()` method)
- Test: `test/features/sync/engine/sync_engine_test.dart`

**Agent**: backend-supabase-agent

#### Step 2.2.1: Add fkColumnMap to TableAdapter base class

In the `TableAdapter` abstract class, add:

```dart
/// Maps parent table name -> local FK column name for per-record blocking.
/// Override in adapters that have FK dependencies.
// WHY: Table-level blocking is too aggressive — one bad project blocks all projects' children.
Map<String, String> get fkColumnMap => {};
```

#### Step 2.2.2: Implement fkColumnMap in each adapter with FK dependencies

For each adapter that has `fkDependencies`, add the corresponding `fkColumnMap`:

| Adapter | fkColumnMap |
|---------|-------------|
| `DailyEntryAdapter` | `{'projects': 'project_id'}` |
| `LocationAdapter` | `{'projects': 'project_id'}` |
| `ContractorAdapter` | `{'projects': 'project_id'}` |
| `BidItemAdapter` | `{'projects': 'project_id'}` |
| `PhotoAdapter` | `{'daily_entries': 'entry_id'}` |
| `EquipmentAdapter` | `{'contractors': 'contractor_id'}` |
| `EntryEquipmentAdapter` | `{'daily_entries': 'entry_id', 'equipment': 'equipment_id'}` |
| `EntryQuantitiesAdapter` | `{'daily_entries': 'entry_id', 'bid_items': 'bid_item_id'}` |
| `EntryContractorsAdapter` | `{'daily_entries': 'entry_id', 'contractors': 'contractor_id'}` |
| `EntryPersonnelCountsAdapter` | `{'daily_entries': 'entry_id', 'personnel_types': 'type_id'}` |
| `FormResponseAdapter` | `{'inspector_forms': 'form_id'}` |

Adapters without FK dependencies (ProjectAdapter, PersonnelTypeAdapter, InspectorFormAdapter, TodoItemAdapter, CalculationHistoryAdapter) use the default empty map.

#### Step 2.2.3: Replace table-level FK blocking with per-record blocking in _push()

Replace the existing FK blocking section at `sync_engine.dart:295-323` (the block starting with `// TODO(spec-3M)` comment through the `if (blocked) continue;` line) with per-record logic. Note: `hasFailedRecord()` already exists in `change_tracker.dart:183-190` — do NOT add it again.

After the per-record blocking block below, the existing push loop at ~line 326 (`for (final change in tableChanges)`) must be changed to iterate over `unblockedChanges` instead of `tableChanges`. The exact line to change is the `for` loop that follows the blocking section.

```dart
// WHY: Per-record FK blocking — only block a child if its SPECIFIC parent has failed,
// not all children of the same table type.
final fkMap = adapter.fkColumnMap;
final unblockedChanges = <ChangeLogEntry>[];

if (fkMap.isEmpty) {
  // No FK dependencies or no column map — process all changes
  unblockedChanges.addAll(tableChanges);
} else {
  for (final change in tableChanges) {
    bool blocked = false;
    // Look up the local record to get its FK values
    final localRows = await db.query(
      adapter.tableName,
      where: 'id = ?',
      whereArgs: [change.recordId],
    );
    if (localRows.isEmpty) {
      // Record deleted locally — let it through (it's a delete change)
      unblockedChanges.add(change);
      continue;
    }
    final localRecord = localRows.first;
    for (final entry in fkMap.entries) {
      final parentTable = entry.key;
      final fkColumn = entry.value;
      final parentId = localRecord[fkColumn]?.toString();
      if (parentId != null && await _changeTracker.hasFailedRecord(parentTable, parentId)) {
        Logger.sync('BLOCKED: ${adapter.tableName}/${change.recordId} — parent $parentTable/$parentId has failed');
        await _changeTracker.markFailed(change.id, 'Blocked by failed parent $parentTable/$parentId');
        errors++;
        blocked = true;
        break;
      }
    }
    if (!blocked) {
      unblockedChanges.add(change);
    }
  }
}
// Continue processing with unblockedChanges instead of tableChanges
```

Then update the subsequent push loop to iterate over `unblockedChanges` instead of `tableChanges`.

#### Step 2.2.4: Write tests for per-record FK blocking

```dart
test('per-record FK blocking: only blocks child of failed parent', () async {
  // Setup: project A has failed push, project B is fine
  // Both have daily_entries queued
  // Act: run _push()
  // Assert: entries for A are blocked, entries for B are pushed
});

test('per-record FK blocking: delete changes pass through even if record missing', () async {
  // Setup: record deleted locally, parent has failures
  // Act: run _push()
  // Assert: delete change is not blocked (localRows.isEmpty path)
});
```

---

### Sub-phase 2.3: AUDIT FIX 2 — Company ID Stamping for All Tables

**Files:**
- Modify: `lib/features/sync/engine/sync_engine.dart` (`_pushUpsert()` method)
- Test: `test/features/sync/engine/sync_engine_test.dart`

**Agent**: backend-supabase-agent

#### Step 2.3.1: Generalize company_id stamping

Replace the projects-only check (`sync_engine.dart:475-485`) with a table-agnostic check:

```dart
// WHY: Child records created during cold-start race may have null company_id.
// Stamp it for any table that has the column, not just projects.
// NOTE: Use ?.toString() to prevent type-mismatch false positives (SEC-HIGH-2).
if (payload.containsKey('company_id')) {
  final payloadCompanyId = payload['company_id']?.toString();
  if (payloadCompanyId == null || payloadCompanyId.isEmpty) {
    payload['company_id'] = companyId;
    Logger.sync('Stamped company_id on ${adapter.tableName}/${change.recordId}');
  } else if (payloadCompanyId != companyId) {
    throw StateError(
      'Company ID mismatch: ${adapter.tableName} record has $payloadCompanyId '
      'but current user belongs to $companyId. '
      'Refusing to push cross-company data.',
    );
  }
}
```

#### Step 2.3.2: Write test for generalized company_id stamping

```dart
test('company_id stamped on child table when null', () async {
  // Setup: a daily_entry with company_id = null in payload
  // Act: _pushUpsert()
  // Assert: company_id is set to current user's companyId
});
```

---

## Phase 3: Conflict & Error Handling Improvements

---

### Sub-phase 3.1: AUDIT FIX 3 — Conflict Ping-Pong Circuit Breaker

**Files:**
- Modify: `lib/features/sync/engine/conflict_resolver.dart`
- Modify: `lib/features/sync/engine/sync_engine.dart` (`_pullTable()`)
- Test: `test/features/sync/engine/conflict_resolver_test.dart`

**Agent**: backend-supabase-agent

#### Step 3.1.1: Increment conflict_count in ConflictResolver.resolve()

**IMPORTANT**: Do NOT change the return type of `resolve()`. It must remain `Future<ConflictWinner>`. Use a query-based approach instead — add a `getConflictCount()` method that the caller queries separately.

In `resolve()`, before inserting into `conflict_log`, check if a row already exists for this (table_name, record_id). If so, increment its count. If not, insert with `conflict_count = 1`:

```dart
// WHY: Track how many times the same record has conflicted to detect ping-pong.
final existing = await _db.query('conflict_log',
  where: 'table_name = ? AND record_id = ?',
  whereArgs: [tableName, recordId],
  orderBy: 'detected_at DESC',
  limit: 1,
);
int conflictCount = 1;
if (existing.isNotEmpty) {
  conflictCount = ((existing.first['conflict_count'] as int?) ?? 0) + 1;
}
await _db.insert('conflict_log', {
  'table_name': tableName,
  'record_id': recordId,
  'winner': winner == ConflictWinner.local ? 'local' : 'remote',
  'lost_data': jsonEncode(lostData),
  'detected_at': detectedAt,
  'expires_at': expiresAt,
  'conflict_count': conflictCount,
});

// Return ONLY the winner — conflict_count is queried separately
return winner;
```

#### Step 3.1.2: Add getConflictCount() method to ConflictResolver

```dart
/// Query the current conflict count for a specific record.
/// Used by the circuit breaker in _pullTable() to detect ping-pong.
Future<int> getConflictCount(String tableName, String recordId) async {
  final rows = await _db.query('conflict_log',
    columns: ['conflict_count'],
    where: 'table_name = ? AND record_id = ?',
    whereArgs: [tableName, recordId],
    orderBy: 'detected_at DESC',
    limit: 1,
  );
  if (rows.isEmpty) return 0;
  return (rows.first['conflict_count'] as int?) ?? 0;
}
```

#### Step 3.1.3: Add circuit breaker in _pullTable() local-wins path

In `_pullTable()`, where local wins conflict (~line 1079-1084), query conflict count and check before inserting the re-push change. The existing call site at `sync_engine.dart:1053` (`final winner = await _conflictResolver.resolve(...)`) does NOT need to change — `resolve()` still returns `ConflictWinner`.

```dart
} else {
  // WHY: Circuit breaker — stop re-pushing after threshold consecutive conflicts.
  final conflictCount = await _conflictResolver.getConflictCount(adapter.tableName, recordId);
  if (conflictCount >= SyncEngineConfig.conflictPingPongThreshold) {
    Logger.sync('CIRCUIT BREAKER: Skipping re-push for ${adapter.tableName}/$recordId '
        '(conflict count: $conflictCount). Record stuck — check conflict viewer.');
  } else {
    await _changeTracker.insertManualChange(
      adapter.tableName,
      recordId,
      'update',
    );
  }
}
```

#### Step 3.1.4: Add cleanup for circuit-broken conflict_log rows

In `ConflictResolver.pruneExpired()` or the cleanup cycle, add cleanup for rows where `conflict_count >= conflictPingPongThreshold` and `detected_at` is older than 7 days. This prevents unbounded row growth from stuck records:

```dart
// WHY: Circuit-broken records accumulate rows indefinitely. Clean up old stuck conflicts.
await _db.delete('conflict_log',
  where: 'conflict_count >= ? AND detected_at < ?',
  whereArgs: [SyncEngineConfig.conflictPingPongThreshold, cutoffDate],
);
```

#### Step 3.1.5: Write tests for circuit breaker

```dart
test('conflict_count increments on repeated conflicts for same record', () async {
  // Resolve same record 3 times
  // Assert: getConflictCount() returns 3
});

test('circuit breaker stops re-push after threshold conflicts', () async {
  // Setup: resolve same record conflictPingPongThreshold times
  // Act: pull with local-wins conflict
  // Assert: no manual change inserted (insertManualChange not called)
});

test('circuit-broken conflict_log rows are cleaned up after 7 days', () async {
  // Setup: insert conflict_log row with conflict_count >= threshold, old detected_at
  // Act: run pruneExpired()
  // Assert: row deleted
});
```

---

### Sub-phase 3.2: AUDIT FIX 5 — Log Silent ConflictAlgorithm.ignore Drops

**NOTE**: This fix is already consolidated into the code block in **Step 2.1.1** above. The `rowId == 0` check and logging are part of the same block that handles BLOCKER-38 enrollment. **No additional code changes needed in this sub-phase** — it exists only for tracking/commit purposes.

**Agent**: backend-supabase-agent (same agent as Phase 2.1)

#### Step 3.2.1: Verify consolidated block from Step 2.1.1

Confirm the insert block in `_pullTable()` includes both:
1. `if (rowId == 0)` logging for silent drops
2. `if (adapter.tableName == 'projects')` enrollment for BLOCKER-38

Both are in the consolidated block written in Step 2.1.1. No further edits needed.

---

### Sub-phase 3.3: AUDIT FIX 7 — RLS 42501 User Notification

**Files:**
- Modify: `lib/features/sync/engine/sync_engine.dart` (`_handlePushError()`)
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart`
- Test: `test/features/sync/engine/sync_engine_test.dart`

**Agent**: backend-supabase-agent

#### Step 3.3.1: Add Logger.error and counter for 42501 errors

In `_handlePushError()` (~line 854-858), upgrade from silent failure to logged + counted:

```dart
if (code == '42501') {
  // WHY: RLS denials are permanent — user must know their data can't sync due to permissions.
  // NOTE: $message from Supabase may contain schema details — Logger.error applies release scrubbing.
  Logger.error('RLS DENIED (42501): ${change.tableName}/${change.recordId}');
  await _changeTracker.markFailed(change.id, 'RLS denied (42501): $message');
  _rlsDenialCount++;
  return false;
}
```

Add `int _rlsDenialCount = 0;` as an instance field on SyncEngine. Reset to 0 at the start of `pushAndPull()` (~line 158).

#### Step 3.3.1b: Add rlsDenials to SyncEngineResult

Add `final int rlsDenials` as an optional field with default `0` to `SyncEngineResult` (~line 32-58):

```dart
const SyncEngineResult({
  this.pushed = 0,
  this.pulled = 0,
  this.errors = 0,
  this.errorMessages = const [],
  this.lockFailed = false,
  this.rlsDenials = 0,  // NEW
});
final int rlsDenials;
```

**IMPORTANT**: Update the `operator +` at ~line 50 to sum rlsDenials:
```dart
SyncEngineResult operator +(SyncEngineResult other) => SyncEngineResult(
  pushed: pushed + other.pushed,
  pulled: pulled + other.pulled,
  errors: errors + other.errors,
  errorMessages: [...errorMessages, ...other.errorMessages],
  rlsDenials: rlsDenials + other.rlsDenials,  // NEW
);
```

**All SyncEngineResult construction sites that need updating** (add `rlsDenials: _rlsDenialCount` where the push result is returned):
- `sync_engine.dart:~167` — `const SyncEngineResult(lockFailed: true)` — OK as-is (default 0)
- `sync_engine.dart:~272` — circuit breaker return — OK as-is (default 0)
- `sync_engine.dart:~282` — empty changes return — OK as-is (default 0)
- `sync_engine.dart:~360` — `_push()` return — ADD `rlsDenials: _rlsDenialCount`
- `sync_engine.dart:~970` — `_pull()` return — OK as-is (pull doesn't generate RLS errors)
- `sync_engine.dart:~223` — `pushResult + pullResult` — handled by `operator +`

#### Step 3.3.2: Surface RLS denials in SyncProvider

In `sync_provider.dart`, after receiving a `SyncEngineResult` with `rlsDenials > 0`, trigger the existing `SyncErrorToastCallback` with a user-friendly message:

```dart
if (result.rlsDenials > 0) {
  _lastError = 'Permission denied: ${result.rlsDenials} record(s) cannot sync. '
      'Contact your administrator if this persists.';
  _errorCallback?.call(_lastError!);
  Logger.sync('RLS denials surfaced to user: ${result.rlsDenials}');
}
```

#### Step 3.3.3: Write test for RLS denial notification

```dart
test('42501 errors surface via SyncErrorToastCallback', () async {
  // Setup: mock Supabase returns 42501 on push
  // Act: pushAndPull()
  // Assert: errorCallback was invoked with permission denied message
});
```

---

## Phase 4: UI Safety — Offline Removal Guard

---

### Sub-phase 4.1: AUDIT FIX 4 — Block removeFromDevice When Offline + Unsynced

**Files:**
- Modify: `lib/features/projects/data/services/project_lifecycle_service.dart` (service-layer guard)
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart` (UI early-exit)
- Test: `test/features/projects/data/services/project_lifecycle_service_test.dart`
- Test: `test/features/projects/presentation/screens/project_list_screen_test.dart`

**Agent**: backend-data-layer-agent (service layer) + frontend-flutter-specialist-agent (UI)

#### Step 4.1.1: Add service-layer guard in removeFromDevice()

**CRITICAL**: The safety check MUST be at the service boundary, not just the UI. Any caller that bypasses the sheet (automation, tests, swipe-to-delete) must hit this guard.

In `project_lifecycle_service.dart:removeFromDevice()` (~line 70), add a precondition parameter and check:

```dart
/// Removes all local data for a project. Returns photo file paths for cleanup.
///
/// Throws [StateError] if [forceOfflineRemoval] is false and there are unsynced
/// changes. Callers must explicitly opt in to data loss.
Future<List<String>> removeFromDevice(
  String projectId, {
  bool forceOfflineRemoval = false,
}) async {
  if (projectId.trim().isEmpty) {
    throw ArgumentError('projectId must not be empty');
  }

  // WHY: Defense-in-depth — prevent permanent data loss when unsynced changes exist.
  // The UI layer should check first and show a warning, but the service layer enforces.
  if (!forceOfflineRemoval) {
    final unsyncedCount = await getUnsyncedChangeCount(projectId);
    if (unsyncedCount > 0) {
      Logger.sync('BLOCKED: removeFromDevice refused — $unsyncedCount unsynced changes for $projectId');
      throw StateError(
        'Cannot remove project with $unsyncedCount unsynced changes. '
        'Sync first or pass forceOfflineRemoval: true to override.',
      );
    }
  }

  // ... rest of existing method unchanged ...
```

#### Step 4.1.2: Add UI early-exit guard in _showDeleteSheet()

In `_showDeleteSheet()` (~line 93-130), add an early-exit check using the EXISTING `isOffline` variable already computed at line 113 (`final isOffline = !orchestrator.isSupabaseOnline`). Do NOT add a new provider read:

```dart
// WHY: Early UX feedback — don't make user go through the sheet just to get blocked.
// The service layer also enforces this, but showing a dialog upfront is better UX.
if (isOffline && unsyncedCount > 0) {
  Logger.sync('UI: removeFromDevice blocked — offline with $unsyncedCount unsynced changes');
  if (!mounted) return;
  showDialog(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Cannot Remove Project'),
      content: Text(
        'Cannot remove project while offline — $unsyncedCount unsynced '
        'change${unsyncedCount == 1 ? '' : 's'} would be permanently lost. '
        'Connect to the internet and sync first.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx),
          child: const Text('OK'),
        ),
      ],
    ),
  );
  return;
}
```

#### Step 4.1.3: Update _handleRemoveFromDevice to catch StateError

In `_handleRemoveFromDevice()` (~line 130), wrap the `removeFromDevice()` call to catch the service-layer `StateError` and show a snackbar:

```dart
try {
  final photoPaths = await lifecycleService.removeFromDevice(entry.project.id);
  // ... existing cleanup ...
} on StateError catch (e) {
  if (mounted) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(e.message)),
    );
  }
}
```

#### Step 4.1.4: Write tests for offline removal guard

```dart
// Service layer test
test('removeFromDevice throws StateError when unsynced changes exist', () async {
  // Setup: insert change_log row with processed=0 for project
  // Act + Assert: expect removeFromDevice(projectId) to throw StateError
});

test('removeFromDevice succeeds with forceOfflineRemoval: true', () async {
  // Setup: insert change_log row with processed=0 for project
  // Act: removeFromDevice(projectId, forceOfflineRemoval: true)
  // Assert: no exception, project removed
});

// UI test
test('project removal blocked when offline with unsynced changes', () async {
  // Setup: orchestrator.isSupabaseOnline = false, unsyncedCount = 5
  // Act: trigger _showDeleteSheet()
  // Assert: AlertDialog shown, ProjectDeleteSheet NOT shown
});
```

---

## Phase 5: Documentation & Comment-Only Fix

---

### Sub-phase 5.1: AUDIT FIX 6 — Document pulling=1 Crash Recovery

**Files:**
- Modify: `lib/features/sync/engine/sync_engine.dart`

**Agent**: backend-supabase-agent

#### Step 5.1.1: Add crash recovery comment at pushAndPull() entry

At `sync_engine.dart:~160` (the `pulling=0` reset line), add:

```dart
// WHY: Crash recovery for pulling=1 stuck state.
// If the app crashes between setting pulling=1 (in _pull()) and the finally block
// that resets it to 0, SQLite triggers remain suppressed on next launch.
// This unconditional reset at pushAndPull() entry ensures triggers are re-enabled
// before any new sync cycle begins. resetState() also performs this reset.
await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
```

---

## Phase 6: Review & Validation

---

### Sub-phase 6.1: Run All Sync Tests

**Agent**: qa-testing-agent

#### Step 6.1.1: Run sync feature tests

```
pwsh -Command "flutter test test/features/sync/"
```

All tests must pass. Fix any failures before proceeding.

#### Step 6.1.2: Run project lifecycle tests

```
pwsh -Command "flutter test test/features/projects/"
```

#### Step 6.1.3: Run full test suite

```
pwsh -Command "flutter test"
```

### Sub-phase 6.2: Static Analysis

**Agent**: qa-testing-agent

#### Step 6.2.1: Run flutter analyze

```
pwsh -Command "flutter analyze"
```

No new warnings or errors allowed.

---

## Commit Strategy

| Phase | Commit Message |
|-------|---------------|
| Phase 1.1 | `feat(db): add conflict_count column to conflict_log` |
| Phase 1.2 | `feat(supabase): enable RLS on 8 core tables + company-scoped policies` |
| Phase 2.1 | `fix(sync): auto-enroll pulled projects in synced_projects (BLOCKER-38)` |
| Phase 2.2 | `refactor(sync): per-record FK blocking replaces table-level blocking` |
| Phase 2.3 | `fix(sync): generalize company_id stamping to all tables` |
| Phase 3.1 | `feat(sync): conflict ping-pong circuit breaker after 3 repeats` |
| Phase 3.2 | `fix(sync): log silently ignored pull inserts` |
| Phase 3.3 | `feat(sync): surface RLS 42501 denials to user via toast` |
| Phase 4.1 | `fix(projects): block removeFromDevice when offline with unsynced data` |
| Phase 5.1 | `docs(sync): document pulling=1 crash recovery path` |

---

## Risk Assessment

| Fix | Risk | Mitigation |
|-----|------|-----------|
| BLOCKER-38 (synced_projects enrollment) | LOW | ConflictAlgorithm.ignore prevents duplicates |
| BLOCKER-39 (RLS migration) | MEDIUM | Verify live state before push; rollback DDL documented; DROP IF EXISTS prevents conflicts |
| Per-record FK blocking | MEDIUM | Extra DB queries per change; bounded by change count |
| Company ID stamping | LOW | Only stamps when null; mismatch still throws |
| Conflict circuit breaker | LOW | Threshold of 3 is conservative; stuck records visible in conflict viewer |
| Offline removal guard | LOW | Service-layer + UI double guard; forceOfflineRemoval escape hatch |
| Silent drop logging | LOW | Read-only logging; no behavior change |
| RLS 42501 notification | LOW | Adds toast; existing failure handling unchanged |
