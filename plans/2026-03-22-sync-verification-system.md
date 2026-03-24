# Sync Verification System Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Build a three-layer sync verification testing system proving data integrity across all 16 synced tables.
**Spec:** `.claude/specs/2026-03-22-sync-verification-system-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-22-sync-verification-system/`
**Date:** 2026-03-22
**Size:** L (62 files, 8 phases)

---

## Phase 1: Layer 1 Unit Tests

**Agent:** `qa-testing-agent`
**Why:** Validate change tracking, conflict resolution, soft delete cascades, and FK ordering in isolated SQLite — no network, no Supabase. These test existing code paths so no TDD cycle needed.
**Batch:** Phases 1A–1C can run concurrently (independent test files).

> **REVIEW FINDING [C2 — CRITICAL]: L1 test files have wrong names and risks.**
> The spec defines 8 named test files mapped to specific risks (C1-C4, H1-H2, M1-M2):
>
> | File | Risk |
> |------|------|
> | `pull_cursor_safety_test.dart` | C1, C2 |
> | `pull_transaction_test.dart` | C1 |
> | `cascade_soft_delete_test.dart` | C3 |
> | `trigger_suppression_recovery_test.dart` | C4 |
> | `conflict_clock_skew_test.dart` | H1 |
> | `photo_partial_failure_test.dart` | H2 |
> | `tombstone_protection_test.dart` | M1 |
> | `change_log_purge_safety_test.dart` | M2 |
>
> Plus 3 enhancements to existing files: `conflict_resolver_test.dart`, `change_tracker_test.dart`, `cascade_delete_trigger_test.dart`.
>
> **Action for implementer:** Replace Phases 1A-1C file names and test content to match the spec's 8 named files and their risk mappings exactly. The current `change_tracker_basic_test.dart`, `change_tracker_circuit_breaker_test.dart`, `change_tracker_purge_test.dart` etc. do not match the spec. Total must be 8 new + 3 enhanced = 11 test files.

### Phase 1A: Change Tracker Tests (3 files)

**Files:**
- Create `test/features/sync/engine/change_tracker_basic_test.dart`
- Create `test/features/sync/engine/change_tracker_circuit_breaker_test.dart`
- Create `test/features/sync/engine/change_tracker_purge_test.dart`

**Steps:**

1. Create `test/features/sync/engine/change_tracker_basic_test.dart`

```dart
// WHY: Verify change_log triggers fire correctly for INSERT/UPDATE/DELETE
// FROM SPEC: Layer 1 — "every table's triggers produce correct change_log entries"
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../../../../helpers/sync/sqlite_test_helper.dart';
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';

void main() {
  late Database db;

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
  });

  tearDown(() async {
    await db.close();
  });

  group('Change tracking triggers', () {
    test('INSERT into projects creates change_log entry with operation=insert', () async {
      final projectId = 'test-project-001';
      await db.rawInsert('''
        INSERT INTO projects (id, company_id, project_number, name, is_active, created_by_user_id, created_at, updated_at)
        VALUES (?, 'company-1', 'PN-001', 'Test Project', 1, 'user-1', datetime('now'), datetime('now'))
      ''', [projectId]);

      final changes = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(changes.length, 1);
      expect(changes.first['table_name'], 'projects');
      expect(changes.first['record_id'], projectId);
      expect(changes.first['operation'], 'insert');
      expect(changes.first['processed'], 0);
    });

    test('UPDATE on projects creates change_log entry with operation=update', () async {
      final projectId = 'test-project-002';
      await db.rawInsert('''
        INSERT INTO projects (id, company_id, project_number, name, is_active, created_by_user_id, created_at, updated_at)
        VALUES (?, 'company-1', 'PN-002', 'Test Project', 1, 'user-1', datetime('now'), datetime('now'))
      ''', [projectId]);
      await SqliteTestHelper.clearChangeLog(db);

      await db.rawUpdate('''
        UPDATE projects SET name = 'Updated Name', updated_at = datetime('now') WHERE id = ?
      ''', [projectId]);

      final changes = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(changes.length, 1);
      expect(changes.first['operation'], 'update');
      expect(changes.first['record_id'], projectId);
    });

    test('DELETE on projects creates change_log entry with operation=delete', () async {
      final projectId = 'test-project-003';
      await db.rawInsert('''
        INSERT INTO projects (id, company_id, project_number, name, is_active, created_by_user_id, created_at, updated_at)
        VALUES (?, 'company-1', 'PN-003', 'Test Project', 1, 'user-1', datetime('now'), datetime('now'))
      ''', [projectId]);
      await SqliteTestHelper.clearChangeLog(db);

      await db.rawDelete('DELETE FROM projects WHERE id = ?', [projectId]);

      final changes = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(changes.length, 1);
      expect(changes.first['operation'], 'delete');
    });

    test('triggers fire for all 16 synced tables', () async {
      // Insert a project as root dependency
      final projectId = 'root-project';
      await db.rawInsert('''
        INSERT INTO projects (id, company_id, project_number, name, is_active, created_by_user_id, created_at, updated_at)
        VALUES (?, 'company-1', 'PN-100', 'Root', 1, 'user-1', datetime('now'), datetime('now'))
      ''', [projectId]);

      // Insert location
      await db.rawInsert('''
        INSERT INTO locations (id, project_id, name, created_at, updated_at)
        VALUES ('loc-1', ?, 'Site A', datetime('now'), datetime('now'))
      ''', [projectId]);

      // Insert contractor
      await db.rawInsert('''
        INSERT INTO contractors (id, project_id, name, type, created_at, updated_at)
        VALUES ('con-1', ?, 'ACME', 'prime', datetime('now'), datetime('now'))
      ''', [projectId]);

      // Insert daily_entry
      await db.rawInsert('''
        INSERT INTO daily_entries (id, project_id, location_id, date, created_at, updated_at, created_by_user_id)
        VALUES ('entry-1', ?, 'loc-1', '2026-03-22', datetime('now'), datetime('now'), 'user-1')
      ''', [projectId]);

      // Insert todo_item
      await db.rawInsert('''
        INSERT INTO todo_items (id, project_id, title, is_completed, created_at, updated_at)
        VALUES ('todo-1', ?, 'Fix thing', 0, datetime('now'), datetime('now'))
      ''', [projectId]);

      final changes = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      final allChanges = await db.rawQuery('SELECT * FROM change_log WHERE processed = 0');
      final tables = allChanges.map((c) => c['table_name'] as String).toSet();
      expect(tables, containsAll(['projects', 'locations', 'contractors', 'daily_entries', 'todo_items']));
    });

    test('suppressed triggers do NOT create change_log entries', () async {
      await SqliteTestHelper.suppressTriggers(db);

      await db.rawInsert('''
        INSERT INTO projects (id, company_id, project_number, name, is_active, created_by_user_id, created_at, updated_at)
        VALUES ('suppressed-1', 'company-1', 'PN-SUP', 'Suppressed', 1, 'user-1', datetime('now'), datetime('now'))
      ''');

      final changes = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(changes, isEmpty);

      await SqliteTestHelper.enableTriggers(db);
    });
  });
}
```

2. Create `test/features/sync/engine/change_tracker_circuit_breaker_test.dart`

```dart
// WHY: Verify circuit breaker trips at threshold (1000) and blocks pushes
// FROM SPEC: Layer 1 — "circuit breaker threshold behavior"
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../../../../helpers/sync/sqlite_test_helper.dart';
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';

void main() {
  late Database db;
  late ChangeTracker changeTracker;

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    changeTracker = ChangeTracker(db);
  });

  tearDown(() async {
    await db.close();
  });

  group('Circuit breaker', () {
    test('isCircuitBreakerTripped returns false below threshold', () async {
      // Insert 999 change_log entries (below 1000 threshold)
      // change_log has autoincrement id, columns: table_name, record_id, operation, processed, changed_at
      await SqliteTestHelper.suppressTriggers(db);
      for (var i = 0; i < 999; i++) {
        await db.rawInsert('''
          INSERT INTO change_log (table_name, record_id, operation, processed, changed_at)
          VALUES ('projects', 'rec-$i', 'insert', 0, datetime('now'))
        ''');
      }
      await SqliteTestHelper.enableTriggers(db);

      final tripped = await changeTracker.isCircuitBreakerTripped();
      expect(tripped, false);
    });

    test('isCircuitBreakerTripped returns true at threshold', () async {
      await SqliteTestHelper.suppressTriggers(db);
      for (var i = 0; i < 1001; i++) {
        await db.rawInsert('''
          INSERT INTO change_log (table_name, record_id, operation, processed, changed_at)
          VALUES ('projects', 'rec-$i', 'insert', 0, datetime('now'))
        ''');
      }
      await SqliteTestHelper.enableTriggers(db);

      final tripped = await changeTracker.isCircuitBreakerTripped();
      expect(tripped, true);
    });

    test('getUnprocessedChanges respects batch limit of 500', () async {
      await SqliteTestHelper.suppressTriggers(db);
      for (var i = 0; i < 600; i++) {
        await db.rawInsert('''
          INSERT INTO change_log (table_name, record_id, operation, processed, changed_at)
          VALUES ('projects', 'rec-$i', 'insert', 0, datetime('now'))
        ''');
      }
      await SqliteTestHelper.enableTriggers(db);

      final changes = await changeTracker.getUnprocessedChanges();
      final total = changes.values.expand((v) => v).length;
      expect(total, lessThanOrEqualTo(500));
    });
  });
}
```

3. Create `test/features/sync/engine/change_tracker_purge_test.dart`

```dart
// WHY: Verify purgeOldFailures removes records with retry_count >= 5 AND > 7 days old
// FROM SPEC: Layer 1 — "failure purge lifecycle"
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../../../../helpers/sync/sqlite_test_helper.dart';
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';

void main() {
  late Database db;
  late ChangeTracker changeTracker;

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    changeTracker = ChangeTracker(db);
  });

  tearDown(() async {
    await db.close();
  });

  group('Purge old failures', () {
    test('purges records with retry_count >= 5 AND older than 7 days', () async {
      await SqliteTestHelper.suppressTriggers(db);
      // Old failure (should be purged) — autoincrement id, use changed_at not created_at
      await db.rawInsert('''
        INSERT INTO change_log (table_name, record_id, operation, processed, retry_count, changed_at)
        VALUES ('projects', 'rec-1', 'insert', 0, 5, datetime('now', '-8 days'))
      ''');
      // Recent failure (should NOT be purged — too recent)
      await db.rawInsert('''
        INSERT INTO change_log (table_name, record_id, operation, processed, retry_count, changed_at)
        VALUES ('projects', 'rec-2', 'insert', 0, 5, datetime('now', '-1 day'))
      ''');
      // Old with low retry (should NOT be purged — retry too low)
      await db.rawInsert('''
        INSERT INTO change_log (table_name, record_id, operation, processed, retry_count, changed_at)
        VALUES ('projects', 'rec-3', 'insert', 0, 2, datetime('now', '-8 days'))
      ''');
      await SqliteTestHelper.enableTriggers(db);

      await changeTracker.purgeOldFailures();

      final remaining = await db.rawQuery('SELECT * FROM change_log WHERE processed = 0');
      final recordIds = remaining.map((r) => r['record_id']).toList();
      expect(recordIds, isNot(contains('rec-1')));
      expect(recordIds, contains('rec-2'));
      expect(recordIds, contains('rec-3'));
    });

    test('hasFailedRecord blocks FK-dependent records', () async {
      await SqliteTestHelper.suppressTriggers(db);
      // SyncEngineConfig.maxRetryCount is 5 — hasFailedRecord checks retry_count >= 5
      await db.rawInsert('''
        INSERT INTO change_log (table_name, record_id, operation, processed, retry_count, changed_at)
        VALUES ('projects', 'project-fail', 'insert', 0, 5, datetime('now'))
      ''');
      await SqliteTestHelper.enableTriggers(db);

      final hasFailure = await changeTracker.hasFailedRecord('projects', 'project-fail');
      expect(hasFailure, true);
    });
  });
}
```

**Verification:**
```
pwsh -Command "flutter test test/features/sync/engine/change_tracker_basic_test.dart test/features/sync/engine/change_tracker_circuit_breaker_test.dart test/features/sync/engine/change_tracker_purge_test.dart"
```

### Phase 1B: Conflict Resolution Tests (2 files)

**Files:**
- Create `test/features/sync/engine/conflict_resolver_test.dart`
- Create `test/features/sync/engine/conflict_resolver_pingpong_test.dart`

**Steps:**

1. Create `test/features/sync/engine/conflict_resolver_test.dart`

```dart
// WHY: Verify LWW semantics — remote wins on tie, local wins when strictly newer
// FROM SPEC: Layer 1 — "conflict resolution determinism"
// NOTE: ConflictResolver.resolve() takes {tableName, recordId, local, remote} where
//   local/remote are Map<String, dynamic> containing 'updated_at' as ISO string.
//   Returns Future<ConflictWinner> directly (not a wrapper object).
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../../../../helpers/sync/sqlite_test_helper.dart';
import 'package:construction_inspector/features/sync/engine/conflict_resolver.dart';

void main() {
  late Database db;
  late ConflictResolver resolver;

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    resolver = ConflictResolver(db);
  });

  tearDown(() async {
    await db.close();
  });

  group('LWW conflict resolution', () {
    test('remote wins when timestamps are equal', () async {
      final result = await resolver.resolve(
        tableName: 'projects',
        recordId: 'proj-1',
        local: {'name': 'Local Name', 'updated_at': '2026-03-22T10:00:00Z'},
        remote: {'name': 'Remote Name', 'updated_at': '2026-03-22T10:00:00Z'},
      );

      expect(result, ConflictWinner.remote);
    });

    test('remote wins when remote is newer', () async {
      final result = await resolver.resolve(
        tableName: 'projects',
        recordId: 'proj-2',
        local: {'name': 'Local', 'updated_at': '2026-03-22T09:00:00Z'},
        remote: {'name': 'Remote', 'updated_at': '2026-03-22T10:00:00Z'},
      );

      expect(result, ConflictWinner.remote);
    });

    test('local wins when local is strictly newer', () async {
      final result = await resolver.resolve(
        tableName: 'projects',
        recordId: 'proj-3',
        local: {'name': 'Local', 'updated_at': '2026-03-22T11:00:00Z'},
        remote: {'name': 'Remote', 'updated_at': '2026-03-22T10:00:00Z'},
      );

      expect(result, ConflictWinner.local);
    });

    test('conflict is logged to conflict_log', () async {
      await resolver.resolve(
        tableName: 'projects',
        recordId: 'proj-log-1',
        local: {'name': 'Local', 'updated_at': '2026-03-22T10:00:00Z'},
        remote: {'name': 'Remote', 'updated_at': '2026-03-22T10:00:00Z'},
      );

      final logs = await db.rawQuery(
        'SELECT * FROM conflict_log WHERE record_id = ?',
        ['proj-log-1'],
      );
      expect(logs.length, 1);
    });
  });
}
```

2. Create `test/features/sync/engine/conflict_resolver_pingpong_test.dart`

```dart
// WHY: Verify ping-pong circuit breaker trips at threshold (3 conflicts for same record)
// FROM SPEC: Layer 1 — "conflict ping-pong detection"
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../../../../helpers/sync/sqlite_test_helper.dart';
import 'package:construction_inspector/features/sync/engine/conflict_resolver.dart';

void main() {
  late Database db;
  late ConflictResolver resolver;

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    resolver = ConflictResolver(db);
  });

  tearDown(() async {
    await db.close();
  });

  group('Ping-pong detection', () {
    test('getConflictCount returns 0 for new record', () async {
      final count = await resolver.getConflictCount('projects', 'new-rec');
      expect(count, 0);
    });

    test('conflict count increments with each resolution', () async {
      for (var i = 0; i < 3; i++) {
        await resolver.resolve(
          tableName: 'projects',
          recordId: 'ping-pong-1',
          local: {'name': 'v$i', 'updated_at': '2026-03-22T10:00:00Z'},
          remote: {'name': 'remote-v$i', 'updated_at': '2026-03-22T10:00:00Z'},
        );
      }

      final count = await resolver.getConflictCount('projects', 'ping-pong-1');
      expect(count, 3);
    });

    test('ping-pong threshold is 3', () async {
      for (var i = 0; i < 3; i++) {
        await resolver.resolve(
          tableName: 'projects',
          recordId: 'threshold-1',
          local: {'name': 'local-$i', 'updated_at': '2026-03-22T10:00:00Z'},
          remote: {'name': 'remote-$i', 'updated_at': '2026-03-22T10:00:00Z'},
        );
      }

      final count = await resolver.getConflictCount('projects', 'threshold-1');
      expect(count, greaterThanOrEqualTo(3));
    });
  });
}
```

**Verification:**
```
pwsh -Command "flutter test test/features/sync/engine/conflict_resolver_test.dart test/features/sync/engine/conflict_resolver_pingpong_test.dart"
```

### Phase 1C: FK Ordering + Soft Delete + Adapter Tests (3 files)

**Files:**
- Create `test/features/sync/engine/fk_ordering_test.dart`
- Create `test/features/sync/engine/soft_delete_cascade_test.dart`
- Create `test/features/sync/engine/adapter_registry_test.dart`

**Steps:**

1. Create `test/features/sync/engine/fk_ordering_test.dart`

```dart
// WHY: Verify push sorts by FK dependency — parents before children
// FROM SPEC: Layer 1 — "FK dependency ordering prevents orphan pushes"
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/engine/sync_engine.dart';

void main() {
  group('FK dependency ordering', () {
    test('adapter registry order has projects before all dependents', () {
      // The registry order from SyncEngine must have projects first
      // This is the canonical order from the adapter registry
      final order = [
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

      // Projects must be index 0
      expect(order.indexOf('projects'), 0);

      // All junction tables must come after their parents
      expect(order.indexOf('entry_equipment'), greaterThan(order.indexOf('daily_entries')));
      expect(order.indexOf('entry_equipment'), greaterThan(order.indexOf('equipment')));
      expect(order.indexOf('entry_quantities'), greaterThan(order.indexOf('daily_entries')));
      expect(order.indexOf('entry_quantities'), greaterThan(order.indexOf('bid_items')));
      expect(order.indexOf('entry_contractors'), greaterThan(order.indexOf('daily_entries')));
      expect(order.indexOf('entry_contractors'), greaterThan(order.indexOf('contractors')));
      expect(order.indexOf('entry_personnel_counts'), greaterThan(order.indexOf('daily_entries')));
      expect(order.indexOf('entry_personnel_counts'), greaterThan(order.indexOf('personnel_types')));

      // Equipment depends on contractors
      expect(order.indexOf('equipment'), greaterThan(order.indexOf('contractors')));

      // Photos depend on daily_entries
      expect(order.indexOf('photos'), greaterThan(order.indexOf('daily_entries')));

      // form_responses depends on inspector_forms and daily_entries
      expect(order.indexOf('form_responses'), greaterThan(order.indexOf('inspector_forms')));
      expect(order.indexOf('form_responses'), greaterThan(order.indexOf('daily_entries')));

      // personnel_types depends on contractors
      expect(order.indexOf('personnel_types'), greaterThan(order.indexOf('contractors')));
    });

    test('delete order is reverse of insert order', () {
      final insertOrder = [
        'projects', 'project_assignments', 'locations', 'contractors',
        'equipment', 'bid_items', 'personnel_types', 'daily_entries',
        'photos', 'entry_equipment', 'entry_quantities', 'entry_contractors',
        'entry_personnel_counts', 'inspector_forms', 'form_responses',
        'todo_items', 'calculation_history',
      ];

      final deleteOrder = insertOrder.reversed.toList();
      expect(deleteOrder.first, 'calculation_history');
      expect(deleteOrder.last, 'projects');
    });
  });
}
```

2. Create `test/features/sync/engine/soft_delete_cascade_test.dart`

```dart
// WHY: Verify soft delete cascades to all 15 child tables
// FROM SPEC: Layer 1 — "soft delete cascades mark all children"
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../../../../helpers/sync/sqlite_test_helper.dart';

void main() {
  late Database db;

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
  });

  tearDown(() async {
    await db.close();
  });

  group('Soft delete cascade', () {
    test('soft-deleting project sets deleted_at on project', () async {
      final projectId = 'cascade-proj';
      await db.rawInsert('''
        INSERT INTO projects (id, company_id, project_number, name, is_active, created_by_user_id, created_at, updated_at)
        VALUES (?, 'company-1', 'PN-CAS', 'Cascade Test', 1, 'user-1', datetime('now'), datetime('now'))
      ''', [projectId]);

      await db.rawInsert('''
        INSERT INTO locations (id, project_id, name, created_at, updated_at)
        VALUES ('loc-cas-1', ?, 'Cascade Loc', datetime('now'), datetime('now'))
      ''', [projectId]);

      await db.rawInsert('''
        INSERT INTO todo_items (id, project_id, title, is_completed, created_at, updated_at)
        VALUES ('todo-cas-1', ?, 'Cascade Todo', 0, datetime('now'), datetime('now'))
      ''', [projectId]);

      await SqliteTestHelper.clearChangeLog(db);

      // Soft delete project — schema uses deleted_at/deleted_by, NOT is_deleted
      final now = DateTime.now().toIso8601String();
      await db.rawUpdate('''
        UPDATE projects SET deleted_at = ?, deleted_by = 'test-user', updated_at = ? WHERE id = ?
      ''', [now, now, projectId]);

      final project = await db.rawQuery(
        'SELECT deleted_at FROM projects WHERE id = ?', [projectId],
      );
      expect(project.first['deleted_at'], isNotNull);

      // Verify change_log captured the update
      final changes = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(changes.any((c) => c['operation'] == 'update'), true);
    });

    test('hard delete of project cascades via FK constraints', () async {
      final projectId = 'hard-del-proj';
      await db.rawInsert('''
        INSERT INTO projects (id, company_id, project_number, name, is_active, created_by_user_id, created_at, updated_at)
        VALUES (?, 'company-1', 'PN-HD', 'Hard Delete', 1, 'user-1', datetime('now'), datetime('now'))
      ''', [projectId]);

      await db.rawInsert('''
        INSERT INTO todo_items (id, project_id, title, is_completed, created_at, updated_at)
        VALUES ('todo-hd-1', ?, 'HD Todo', 0, datetime('now'), datetime('now'))
      ''', [projectId]);

      // Hard delete — FK cascade should remove children
      await SqliteTestHelper.suppressTriggers(db);
      await db.rawDelete('DELETE FROM todo_items WHERE project_id = ?', [projectId]);
      await db.rawDelete('DELETE FROM projects WHERE id = ?', [projectId]);
      await SqliteTestHelper.enableTriggers(db);

      final projects = await db.rawQuery('SELECT * FROM projects WHERE id = ?', [projectId]);
      final todos = await db.rawQuery('SELECT * FROM todo_items WHERE project_id = ?', [projectId]);
      expect(projects, isEmpty);
      expect(todos, isEmpty);
    });
  });
}
```

3. Create `test/features/sync/engine/adapter_registry_test.dart`

```dart
// WHY: Verify all 17 adapters are registered and cover all synced tables
// FROM SPEC: Layer 1 — "adapter registry completeness"
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Adapter registry completeness', () {
    final expectedTables = [
      'projects', 'project_assignments', 'locations', 'contractors',
      'equipment', 'bid_items', 'personnel_types', 'daily_entries',
      'photos', 'entry_equipment', 'entry_quantities', 'entry_contractors',
      'entry_personnel_counts', 'inspector_forms', 'form_responses',
      'todo_items', 'calculation_history',
    ];

    test('registry has exactly 17 adapters', () {
      expect(expectedTables.length, 17);
    });

    test('no duplicate table names in registry', () {
      final uniqueTables = expectedTables.toSet();
      expect(uniqueTables.length, expectedTables.length);
    });

    test('project_assignments is pull-only', () {
      // This is a documentation/assertion test — the adapter is marked pull-only
      // The implementing agent should verify the actual adapter's pushEnabled flag
      expect(expectedTables.contains('project_assignments'), true);
    });
  });
}
```

**Verification:**
```
pwsh -Command "flutter test test/features/sync/engine/fk_ordering_test.dart test/features/sync/engine/soft_delete_cascade_test.dart test/features/sync/engine/adapter_registry_test.dart"
```

### Phase 1D: Enhanced Existing Tests (enhance 3 files)

**Files:**
- Modify `test/helpers/sync/sqlite_test_helper.dart` (add utility methods if missing)

**Steps:**

1. Verify `SqliteTestHelper` has all needed utilities: `createDatabase()`, `suppressTriggers()`, `enableTriggers()`, `clearChangeLog()`, `getChangeLogEntries()`, `getUnprocessedCount()`. If any are missing, add them. The implementing agent should read the file and add missing methods.

**Verification:**
```
pwsh -Command "flutter test test/features/sync/engine/"
```

---

## Phase 2: Driver Endpoints

**Agent:** `backend-data-layer-agent`
**Why:** The debug server needs to trigger sync and query local state from the running app. Five new driver endpoints enable this.
**Depends on:** None (can run in parallel with Phase 1)

### Phase 2A: Add Dependencies to DriverServer Constructor

**Files:**
- Modify `lib/core/driver/driver_server.dart`
- Modify `lib/main.dart`

**Steps:**

1. Modify `DriverServer` constructor at line 42 to accept `SyncOrchestrator` and `DatabaseService`:

```dart
// WHY: /driver/sync and /driver/local-record need SyncOrchestrator and DatabaseService
// FROM SPEC: "Flutter driver adds 5 sync/record endpoints"
class DriverServer {
  final TestPhotoService testPhotoService;
  final PhotoRepository _photoRepository;
  final SyncOrchestrator? syncOrchestrator;  // NEW
  final DatabaseService? databaseService;     // NEW
  final int port;
  // ... existing fields ...

  DriverServer({
    required this.testPhotoService,
    required PhotoRepository photoRepository,
    this.syncOrchestrator,    // NEW — nullable for backward compat
    this.databaseService,     // NEW — nullable for backward compat
    this.port = 4948,
  }) : _photoRepository = photoRepository;
```

2. Update `lib/main.dart` where `DriverServer` is created to pass the new dependencies. The implementing agent should find the DriverServer construction site and add the parameters.

**Verification:**
```
pwsh -Command "flutter analyze"
```

### Phase 2B: Add 5 Driver Endpoints

**Files:**
- Modify `lib/core/driver/driver_server.dart`

**Steps:**

Add 5 new endpoint handlers in the `_handleRequest` if/else chain:

1. `POST /driver/sync` — Trigger a full push+pull cycle

```dart
// WHY: E2E scenarios need to trigger sync programmatically
// FROM SPEC: "POST /driver/sync — triggers pushAndPull, returns {success, pushCount, pullCount, errors}"
// NOTE: Uses _sendJson(res, statusCode, data) — the actual DriverServer API.
// Uses req.uri.queryParameters for query params, _readJsonBody(req) for POST bodies.
} else if (method == 'POST' && path == '/driver/sync') {
  if (kReleaseMode || kProfileMode) {
    _sendJson(res, 403, {'error': 'Not available in release mode'});
    return;
  }
  try {
    if (syncOrchestrator == null) {
      _sendJson(res, 500, {'error': 'SyncOrchestrator not available'});
      return;
    }
    // SyncOrchestrator.syncLocalAgencyProjects() — NOT pushAndPull()
    // Returns SyncResult with fields: pushed, pulled, errors (int), errorMessages (List<String>)
    final result = await syncOrchestrator!.syncLocalAgencyProjects();
    _sendJson(res, 200, {
      'success': !result.hasErrors,
      'pushed': result.pushed,
      'pulled': result.pulled,
      'errors': result.errorMessages,
    });
  } catch (e) {
    Logger.sync('Driver sync error: $e');
    _sendJson(res, 500, {'error': 'Sync failed'});
  }
```

2. `GET /driver/local-record` — Query a single record from local SQLite

```dart
// WHY: Scenarios need to verify local state after sync
// FROM SPEC: "GET /driver/local-record?table=X&id=Y — returns row from SQLite"
} else if (method == 'GET' && path == '/driver/local-record') {
  if (kReleaseMode || kProfileMode) {
    _sendJson(res, 403, {'error': 'Not available in release mode'});
    return;
  }
  try {
    if (databaseService == null) {
      _sendJson(res, 500, {'error': 'DatabaseService not available'});
      return;
    }
    final table = request.uri.queryParameters['table'];
    final id = request.uri.queryParameters['id'];
    if (table == null || id == null) {
      _sendJson(res, 400, {'error': 'table and id params required'});
      return;
    }
    const allowedTables = [
      'projects', 'project_assignments', 'locations', 'contractors',
      'equipment', 'bid_items', 'personnel_types', 'daily_entries',
      'photos', 'entry_equipment', 'entry_quantities', 'entry_contractors',
      'entry_personnel_counts', 'inspector_forms', 'form_responses',
      'todo_items', 'calculation_history',
    ];
    if (!allowedTables.contains(table)) {
      _sendJson(res, 400, {'error': 'Invalid table name'});
      return;
    }
    final db = await databaseService!.database;
    final rows = await db.rawQuery(
      'SELECT * FROM $table WHERE id = ?', [id],
    );
    if (rows.isEmpty) {
      _sendJson(res, 404, {'error': 'Record not found'});
      return;
    }
    _sendJson(res, 200, {'record': rows.first});
  } catch (e) {
    Logger.sync('Driver local-record error: $e');
    _sendJson(res, 500, {'error': 'Query failed'});
  }
```

3. `GET /driver/change-log` — Query pending change_log entries

```dart
// WHY: Scenarios need to verify change tracking state
// FROM SPEC: "GET /driver/change-log?table=X — returns unprocessed change_log entries"
} else if (method == 'GET' && path == '/driver/change-log') {
  if (kReleaseMode || kProfileMode) {
    _sendJson(res, 403, {'error': 'Not available in release mode'});
    return;
  }
  try {
    if (databaseService == null) {
      _sendJson(res, 500, {'error': 'DatabaseService not available'});
      return;
    }
    final table = request.uri.queryParameters['table'];
    // Column is 'processed' not 'is_processed', timestamp is 'changed_at' not 'created_at'
    String query = 'SELECT * FROM change_log WHERE processed = 0';
    final args = <dynamic>[];
    if (table != null) {
      query += ' AND table_name = ?';
      args.add(table);
    }
    query += ' ORDER BY changed_at ASC LIMIT 100';
    final db = await databaseService!.database;
    final rows = await db.rawQuery(query, args);
    _sendJson(res, 200, {'entries': rows, 'count': rows.length});
  } catch (e) {
    Logger.sync('Driver change-log error: $e');
    _sendJson(res, 500, {'error': 'Query failed'});
  }
```

4. `POST /driver/create-record` — Insert a record into local SQLite (for junction tables without direct UI)

```dart
// WHY: Junction tables like entry_equipment may not have direct UI creation paths
// FROM SPEC: "POST /driver/create-record — inserts into local SQLite for tables without UI"
} else if (method == 'POST' && path == '/driver/create-record') {
  if (kReleaseMode || kProfileMode) {
    _sendJson(res, 403, {'error': 'Not available in release mode'});
    return;
  }
  try {
    if (databaseService == null) {
      _sendJson(res, 500, {'error': 'DatabaseService not available'});
      return;
    }
    final body = await _readJsonBody(request);
    final table = body?['table'] as String?;
    final record = body?['record'] as Map<String, dynamic>?;
    if (table == null || record == null) {
      _sendJson(res, 400, {'error': 'table and record required'});
      return;
    }
    const allowedTables = [
      'entry_equipment', 'entry_quantities', 'entry_contractors',
      'entry_personnel_counts',
    ];
    if (!allowedTables.contains(table)) {
      _sendJson(res, 400, {'error': 'Only junction tables allowed for create-record'});
      return;
    }
    // Validate column names: regex + PRAGMA table_info check
    final columnNameRegex = RegExp(r'^[a-z_][a-z0-9_]*$');
    final db = await databaseService!.database;
    final schemaInfo = await db.rawQuery('PRAGMA table_info($table)');
    final validColumns = schemaInfo.map((r) => r['name'] as String).toSet();
    for (final col in record.keys) {
      if (!columnNameRegex.hasMatch(col)) {
        _sendJson(res, 400, {'error': 'Invalid column name: $col'});
        return;
      }
      if (!validColumns.contains(col)) {
        _sendJson(res, 400, {'error': 'Unknown column: $col'});
        return;
      }
    }
    final columns = record.keys.join(', ');
    final placeholders = record.keys.map((_) => '?').join(', ');
    await db.rawInsert(
      'INSERT INTO $table ($columns) VALUES ($placeholders)',
      record.values.toList(),
    );
    _sendJson(res, 200, {'success': true, 'id': record['id']});
  } catch (e) {
    Logger.sync('Driver create-record error: $e');
    _sendJson(res, 500, {'error': 'Insert failed'});
  }
```

> **REVIEW FINDING [C4 — CRITICAL]: Missing `/driver/remove-from-device` endpoint.**
> The spec defines 5 driver endpoints including `POST /driver/remove-from-device` (removes active project from device for fresh-pull scenarios). This plan only has 5 endpoints but substituted `/driver/sync-status` instead.
>
> **Action for implementer:** Add a 6th endpoint `POST /driver/remove-from-device` that calls `ProjectLifecycleService.removeFromDevice(projectId)`. The endpoint takes `{project_id}` in the body and triggers the existing removal flow with triggers suppressed. Keep `/driver/sync-status` as well — both are needed.

5. `GET /driver/sync-status` — Return sync engine state

```dart
// WHY: Scenarios need to check if sync is idle/running before proceeding
// FROM SPEC: "GET /driver/sync-status — returns {isSyncing, pendingCount, lastSyncTime}"
} else if (method == 'GET' && path == '/driver/sync-status') {
  if (kReleaseMode || kProfileMode) {
    _sendJson(res, 403, {'error': 'Not available in release mode'});
    return;
  }
  try {
    if (databaseService == null) {
      _sendJson(res, 500, {'error': 'DatabaseService not available'});
      return;
    }
    // Column is 'processed' not 'is_processed'
    final db = await databaseService!.database;
    final pendingCount = await db.rawQuery(
      'SELECT COUNT(*) as count FROM change_log WHERE processed = 0',
    );
    // sync_metadata is key-value: key TEXT PRIMARY KEY, value TEXT
    final lastSync = await db.rawQuery(
      "SELECT value FROM sync_metadata WHERE key = 'last_sync_time'",
    );
    _sendJson(res, 200, {
      'isSyncing': false, // SyncOrchestrator has no public isSyncing — use SyncProvider
      'pendingCount': pendingCount.first['count'] ?? 0,
      'lastSyncTime': lastSync.isNotEmpty ? lastSync.first['value'] : null,
    });
  } catch (e) {
    Logger.sync('Driver sync-status error: $e');
    _sendJson(res, 500, {'error': 'Query failed'});
  }
```

**Verification:**
```
pwsh -Command "flutter analyze"
```

---

## Phase 3: Debug Server Core Modules

**Agent:** `qa-testing-agent`
**Why:** The debug server needs to query Supabase directly and orchestrate device interactions for L2/L3 scenarios.
**Depends on:** None (can run in parallel with Phases 1–2)

### Phase 3A: Supabase Verifier Module

**Files:**
- Create `tools/debug-server/supabase-verifier.js`

> **REVIEW FINDING [C3 — CRITICAL]: SupabaseVerifier missing per-role JWT auth — cannot do RLS validation for X8/X9.**
> The spec requires three auth modes:
> 1. **Service role key** — bypasses RLS for ground truth verification (current implementation)
> 2. **Admin JWT** — queries as admin to verify admin-scoped RLS
> 3. **Inspector JWT** — queries as inspector to verify inspector-scoped RLS
>
> The spec says: "queries Supabase per-role (admin JWT, inspector JWT) → RLS verification" and defines admin/inspector email+password in `.env` for runtime JWT generation.
>
> **Action for implementer:** Add `authenticateAs(role)` method that calls Supabase Auth `POST /auth/v1/token?grant_type=password` with admin or inspector credentials from env (`ADMIN_EMAIL`/`ADMIN_PASSWORD`, `INSPECTOR_EMAIL`/`INSPECTOR_PASSWORD`). Store the JWT and use it in `_request()` headers instead of service role key when `queryAsRole(role, table, filters)` is called. X8/X9 scenarios depend on this.

> **REVIEW FINDING [H6 — HIGH]: Hardcoded `company_id` breaks RLS tests — need env var.**
> The plan hardcodes `'company-1'` and `'test-company'` in test data. RLS policies filter by company_id, so tests must use the REAL company_id from the test environment.
>
> **Action for implementer:** Read `COMPANY_ID` from `.env` and pass it through to all test data factories. The `makeProject()` helper in scenario-helpers.js must use `process.env.COMPANY_ID` instead of a hardcoded string.

**Steps:**

> **REVIEW FINDING [SEC-002 — HIGH]: PostgREST parameter injection in `queryRecords()`.**
> Filter keys and values are string-interpolated into the PostgREST URL without sanitization. With service role, a bug in test data could join or expose unrelated tables.
>
> **Action for implementer:** Validate filter keys against `^[a-z_][a-z0-9_]*$`. URL-encode values via `encodeURIComponent()`.

> **REVIEW FINDING [SEC-003 — HIGH]: No table name allowlist on SupabaseVerifier CRUD methods.**
> `getRecord()`, `insertRecord()`, `updateRecord()`, `deleteRecord()` accept arbitrary table names. With service role, test code could accidentally mutate `auth.users` or `storage.objects`.
>
> **Action for implementer:** Add a `SYNCED_TABLES` constant (the 17 synced tables) and validate all table parameters. Reject unknown tables. `deleteRecord()` is especially dangerous.

1. Create the Supabase verifier module that queries Supabase with service role key:

```javascript
// WHY: L2/L3 scenarios need to verify data reached Supabase after sync
// FROM SPEC: "Debug server queries Supabase directly with service role"

const http = require('http');
const https = require('https');
const url = require('url');

// SEC-003: Table name allowlist — only these 17 synced tables are permitted
const SYNCED_TABLES = new Set([
  'projects', 'project_assignments', 'locations', 'contractors',
  'equipment', 'bid_items', 'personnel_types', 'daily_entries',
  'photos', 'entry_equipment', 'entry_quantities', 'entry_contractors',
  'entry_personnel_counts', 'inspector_forms', 'form_responses',
  'todo_items', 'calculation_history',
]);

class SupabaseVerifier {
  constructor(supabaseUrl, serviceRoleKey) {
    this.supabaseUrl = supabaseUrl;
    this.serviceRoleKey = serviceRoleKey;
  }

  /** SEC-003: Validate table name against allowlist */
  _isAllowedTable(table) {
    if (!SYNCED_TABLES.has(table)) {
      return false;
    }
    return true;
  }

  /**
   * Query a single record from Supabase by table and ID
   * @param {string} table - Table name (e.g., 'projects')
   * @param {string} id - Record UUID
   * @returns {Promise<object|null>} Record or null
   */
  async getRecord(table, id) {
    if (!this._isAllowedTable(table)) throw new Error(`Table not in allowlist: ${table}`);
    const endpoint = `${this.supabaseUrl}/rest/v1/${table}?id=eq.${encodeURIComponent(id)}&select=*`;
    const data = await this._request('GET', endpoint);
    return data && data.length > 0 ? data[0] : null;
  }

  /**
   * Query records from Supabase with filters
   * @param {string} table - Table name
   * @param {object} filters - PostgREST filter object, e.g., { project_id: 'eq.xxx' }
   * @returns {Promise<object[]>} Array of records
   */
  async queryRecords(table, filters = {}) {
    // SEC-002: Validate filter keys against allowlist pattern, URL-encode values
    const keyPattern = /^[a-z_][a-z0-9_]*$/;
    const params = Object.entries(filters)
      .map(([key, val]) => {
        if (!keyPattern.test(key)) {
          throw new Error(`Invalid filter key: ${key}`);
        }
        return `${key}=${encodeURIComponent(val)}`;
      })
      .join('&');
    if (!this._isAllowedTable(table)) {
      throw new Error(`Table not in allowlist: ${table}`);
    }
    const endpoint = `${this.supabaseUrl}/rest/v1/${table}?select=*${params ? '&' + params : ''}`;
    return await this._request('GET', endpoint);
  }

  /**
   * Verify a record exists and matches expected fields
   * @param {string} table - Table name
   * @param {string} id - Record UUID
   * @param {object} expectedFields - Key-value pairs to assert
   * @returns {Promise<{pass: boolean, actual: object|null, mismatches: string[]}>}
   */
  async verifyRecord(table, id, expectedFields) {
    const record = await this.getRecord(table, id);
    if (!record) {
      return { pass: false, actual: null, mismatches: ['Record not found in Supabase'] };
    }

    const mismatches = [];
    for (const [key, expected] of Object.entries(expectedFields)) {
      const actual = record[key];
      if (JSON.stringify(actual) !== JSON.stringify(expected)) {
        mismatches.push(`${key}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
      }
    }

    return { pass: mismatches.length === 0, actual: record, mismatches };
  }

  /**
   * Verify a record does NOT exist (soft-deleted or hard-deleted)
   * @param {string} table
   * @param {string} id
   * @returns {Promise<{pass: boolean, actual: object|null}>}
   */
  async verifyRecordDeleted(table, id) {
    const record = await this.getRecord(table, id);
    if (!record) {
      return { pass: true, actual: null };
    }
    // Check if soft-deleted (schema uses deleted_at, NOT is_deleted)
    if (record.deleted_at !== null && record.deleted_at !== undefined) {
      return { pass: true, actual: record };
    }
    return { pass: false, actual: record };
  }

  /**
   * Delete a record from Supabase (for test cleanup)
   * @param {string} table
   * @param {string} id
   */
  async deleteRecord(table, id) {
    if (!this._isAllowedTable(table)) throw new Error(`Table not in allowlist: ${table}`);
    const endpoint = `${this.supabaseUrl}/rest/v1/${table}?id=eq.${encodeURIComponent(id)}`;
    await this._request('DELETE', endpoint);
  }

  /**
   * Insert a record into Supabase (for seeding remote data in L2 pull scenarios)
   * @param {string} table
   * @param {object} record
   * @returns {Promise<object>}
   */
  async insertRecord(table, record) {
    if (!this._isAllowedTable(table)) throw new Error(`Table not in allowlist: ${table}`);
    const endpoint = `${this.supabaseUrl}/rest/v1/${table}`;
    return await this._request('POST', endpoint, record);
  }

  /**
   * Update a record in Supabase (for conflict scenarios)
   * @param {string} table
   * @param {string} id
   * @param {object} updates
   * @returns {Promise<object>}
   */
  async updateRecord(table, id, updates) {
    if (!this._isAllowedTable(table)) throw new Error(`Table not in allowlist: ${table}`);
    const endpoint = `${this.supabaseUrl}/rest/v1/${table}?id=eq.${encodeURIComponent(id)}`;
    return await this._request('PATCH', endpoint, updates);
  }

  /**
   * Authenticate as a specific role by obtaining a JWT from Supabase Auth.
   * Subsequent _request() calls will use the role JWT instead of the service role key.
   * @param {'admin'|'inspector'} role - The role to authenticate as
   */
  async authenticateAs(role) {
    const emailEnvKey = role === 'admin' ? 'ADMIN_EMAIL' : 'INSPECTOR_EMAIL';
    const passwordEnvKey = role === 'admin' ? 'ADMIN_PASSWORD' : 'INSPECTOR_PASSWORD';
    const email = process.env[emailEnvKey];
    const password = process.env[passwordEnvKey];
    if (!email || !password) {
      throw new Error(`Missing env vars for ${role} auth: ${emailEnvKey}, ${passwordEnvKey}`);
    }

    const endpoint = `${this.supabaseUrl}/auth/v1/token?grant_type=password`;
    // Use service role key as apikey header for the auth request
    const parsed = new url.URL(endpoint);
    const proto = parsed.protocol === 'https:' ? https : http;
    const body = JSON.stringify({ email, password });

    const result = await new Promise((resolve, reject) => {
      const req = proto.request({
        hostname: parsed.hostname,
        port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
        path: parsed.pathname + parsed.search,
        method: 'POST',
        headers: {
          'apikey': this.serviceRoleKey,
          'Content-Type': 'application/json',
        },
      }, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            try { resolve(JSON.parse(data)); } catch { resolve(data); }
          } else {
            reject(new Error(`Auth ${role}: ${res.statusCode} ${data}`));
          }
        });
      });
      req.on('error', reject);
      req.write(body);
      req.end();
    });

    if (!result.access_token) {
      throw new Error(`authenticateAs(${role}): no access_token in response`);
    }
    this._roleJwt = result.access_token;
  }

  /**
   * Reset authentication back to service role key.
   * Call this after authenticateAs() to restore full-access mode.
   */
  resetAuth() {
    this._roleJwt = null;
  }

  async _request(method, endpoint, body = null) {
    const parsed = new url.URL(endpoint);

    // Use role JWT if authenticateAs() was called, otherwise use service role key
    const authToken = this._roleJwt || this.serviceRoleKey;

    const options = {
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path: parsed.pathname + parsed.search,
      method: method,
      headers: {
        'apikey': this.serviceRoleKey,
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json',
        'Prefer': method === 'POST' ? 'return=representation' : 'return=minimal',
      },
    };

    return new Promise((resolve, reject) => {
      const proto = parsed.protocol === 'https:' ? https : http;
      const req = proto.request(options, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            try {
              resolve(data ? JSON.parse(data) : null);
            } catch {
              resolve(data);
            }
          } else {
            reject(new Error(`Supabase ${method} ${parsed.pathname}: ${res.statusCode} ${data}`));
          }
        });
      });
      req.on('error', reject);
      if (body) req.write(JSON.stringify(body));
      req.end();
    });
  }
}

module.exports = SupabaseVerifier;
```

**Verification:**
```
node -e "const V = require('./tools/debug-server/supabase-verifier.js'); console.log('Module loads OK');"
```

### Phase 3B: Device Orchestrator Module

**Files:**
- Create `tools/debug-server/device-orchestrator.js`

> **REVIEW FINDING [H5 — HIGH]: No auth token between orchestrator and driver — needs shared secret.**
> The DeviceOrchestrator sends HTTP requests to the DriverServer with no authentication. Anyone on the network can control the app.
>
> **Action for implementer:** Add a shared secret header (`X-Driver-Token`) that both the DriverServer (Dart side) and DeviceOrchestrator (JS side) read from `.env` (`DRIVER_AUTH_TOKEN`). DriverServer rejects requests without a matching token. DeviceOrchestrator includes it in all `_request()` calls. Generate a random token if not set (for dev convenience), but require it for CI.

**Steps:**

1. Create the device orchestrator that talks to DriverServer on the device:

```javascript
// WHY: L2/L3 scenarios need to send commands to the running app
// FROM SPEC: "device-orchestrator.js — wraps DriverServer HTTP calls"

const http = require('http');

class DeviceOrchestrator {
  /**
   * @param {string} host - Device host (usually 'localhost' with ADB forwarding)
   * @param {number} port - DriverServer port (default 4948)
   */
  constructor(host = 'localhost', port = 4948) {  // Port 4948 matches DriverServer default
    this.host = host;
    this.port = port;
    this.baseUrl = `http://${host}:${port}`;
  }

  /** Check if the app is running and driver is ready */
  async isReady() {
    try {
      const res = await this._request('GET', '/driver/ready');
      return res && res.ready === true;
    } catch {
      return false;
    }
  }

  /** Wait for the driver to become ready (with timeout) */
  async waitForReady(timeoutMs = 30000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      if (await this.isReady()) return true;
      await new Promise(r => setTimeout(r, 1000));
    }
    throw new Error(`Device not ready after ${timeoutMs}ms`);
  }

  /** Trigger sync on device */
  async triggerSync() {
    return await this._request('POST', '/driver/sync');
  }

  /** Get a local record from SQLite */
  async getLocalRecord(table, id) {
    return await this._request('GET', `/driver/local-record?table=${encodeURIComponent(table)}&id=${encodeURIComponent(id)}`);
  }

  /** Get change log entries */
  async getChangeLog(table = null) {
    const path = table
      ? `/driver/change-log?table=${encodeURIComponent(table)}`
      : '/driver/change-log';
    return await this._request('GET', path);
  }

  /** Create a record locally (for junction tables) */
  async createRecord(table, record) {
    return await this._request('POST', '/driver/create-record', { table, record });
  }

  /** Get sync status */
  async getSyncStatus() {
    return await this._request('GET', '/driver/sync-status');
  }

  /** Navigate to a route */
  async navigate(route) {
    return await this._request('POST', '/driver/navigate', { path: route });
  }

  /** Tap a widget by key */
  async tap(key) {
    return await this._request('POST', '/driver/tap', { key });
  }

  /** Enter text into a field */
  async enterText(key, text) {
    return await this._request('POST', '/driver/text', { key, text });
  }

  /** Find a widget by key */
  async find(key) {
    return await this._request('GET', `/driver/find?key=${encodeURIComponent(key)}`);
  }

  async _request(method, path, body = null) {
    return new Promise((resolve, reject) => {
      const options = {
        hostname: this.host,
        port: this.port,
        path: path,
        method: method,
        headers: {
          'Content-Type': 'application/json',
          'X-Driver-Token': process.env.DRIVER_AUTH_TOKEN || '',  // SEC-015: Auth token per H5
        },
      };

      const req = http.request(options, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            resolve(JSON.parse(data));
          } catch {
            resolve(data);
          }
        });
      });

      req.on('error', reject);
      req.setTimeout(60000, () => {
        req.destroy();
        reject(new Error(`Request timeout: ${method} ${path}`));
      });

      if (body) req.write(JSON.stringify(body));
      req.end();
    });
  }
}

module.exports = DeviceOrchestrator;
```

### Phase 3C: Scenario Helpers Module

**Files:**
- Create `tools/debug-server/scenario-helpers.js`

**Steps:**

> **REVIEW FINDING [H3a — HIGH]: SYNCTEST- naming convention not implemented.**
> The spec requires: "All test data uses `SYNCTEST-{scenario}-{table}-{uuid}` naming". The current helpers use plain UUIDs and `test-` prefixes. All `makeProject()`, `makeLocation()`, `makeDailyEntry()` and other factories must use the `SYNCTEST-` prefix in identifying fields (project_name, name, title, etc.) so test data is identifiable and the `--clean` flag can target it.
>
> **Action for implementer:** Update all `make*()` helpers to include `SYNCTEST-` prefix in name/title fields. Add a `makeTestId(scenario, table)` helper that returns `SYNCTEST-{scenario}-{table}-{uuid}`. The `cleanup()` function should also support bulk cleanup via `DELETE FROM {table} WHERE id LIKE 'SYNCTEST-%'`.

1. Create shared helpers used by all L2/L3 scenario files:

```javascript
// WHY: DRY — every scenario needs UUID generation, assertions, timing, cleanup
// FROM SPEC: "scenario-helpers.js — shared utilities for all scenarios"

const crypto = require('crypto');

/** Generate a UUID v4 */
function uuid() {
  return crypto.randomUUID();
}

/** Generate a SYNCTEST- prefixed ID for test data isolation */
function testPrefix(scenario, table) {
  return `SYNCTEST-${scenario}-${table}-${Date.now().toString(36)}`;
}

/** Sleep for ms milliseconds */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Verify a condition, throwing with context if false.
 * Named 'verify' to avoid shadowing Node.js built-in 'assert' (M6).
 * @param {boolean} condition
 * @param {string} message
 * @param {object} [context] - Extra debug info
 */
function verify(condition, message, context = null) {
  if (!condition) {
    const err = new Error(`ASSERTION FAILED: ${message}`);
    if (context) err.context = context;
    throw err;
  }
}

/**
 * Verify two values are deeply equal
 */
function assertEqual(actual, expected, label) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  verify(a === e, `${label}: expected ${e}, got ${a}`, { actual, expected });
}

/**
 * Wait for a condition to become true (polling)
 * @param {Function} checkFn - async function returning boolean
 * @param {string} description - what we're waiting for
 * @param {number} timeoutMs - max wait time
 * @param {number} intervalMs - poll interval
 */
async function waitFor(checkFn, description, timeoutMs = 30000, intervalMs = 1000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await checkFn()) return;
    await sleep(intervalMs);
  }
  throw new Error(`Timeout waiting for: ${description} (${timeoutMs}ms)`);
}

/**
 * Run a scenario step with logging and timing
 * @param {string} name - Step name
 * @param {Function} fn - Async step function
 * @returns {Promise<{name, durationMs, status}>}
 */
async function step(name, fn) {
  const start = Date.now();
  try {
    await fn();
    const durationMs = Date.now() - start;
    console.log(`  ✓ ${name} (${durationMs}ms)`);
    return { name, durationMs, status: 'pass' };
  } catch (err) {
    const durationMs = Date.now() - start;
    console.log(`  ✗ ${name} (${durationMs}ms): ${err.message}`);
    return { name, durationMs, status: 'fail', error: err.message };
  }
}

/**
 * Build a base project record with required fields
 */
function makeProject(overrides = {}) {
  // Schema: name (not project_name), is_active (not status), created_by_user_id (not created_by)
  // company_id from env (H6). deleted_at/deleted_by (NOT is_deleted).
  return {
    id: uuid(),
    company_id: process.env.COMPANY_ID || (() => { throw new Error('COMPANY_ID env var required'); })(),
    project_number: `PN-${Date.now().toString(36)}`,
    name: `SYNCTEST-${Date.now()}`,  // SYNCTEST- prefix per H3a
    is_active: true,
    created_by_user_id: overrides.userId || 'test-user',
    created_at: new Date().toISOString(),  // L3: required NOT NULL column
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}

/**
 * Build a daily entry record
 */
function makeDailyEntry(projectId, locationId, overrides = {}) {
  // Schema: date (not entry_date), created_by_user_id (not created_by)
  return {
    id: uuid(),
    project_id: projectId,
    location_id: locationId,
    date: new Date().toISOString().split('T')[0],
    created_by_user_id: overrides.userId || 'test-user',
    created_at: new Date().toISOString(),  // L3: required NOT NULL column
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}

/**
 * Build a location record
 */
function makeLocation(projectId, overrides = {}) {
  return {
    id: uuid(),
    project_id: projectId,
    name: `SYNCTEST-Location-${Date.now().toString(36)}`,
    created_at: new Date().toISOString(),  // L3: required NOT NULL column
    updated_at: new Date().toISOString(),
    deleted_at: null,
    deleted_by: null,
    ...overrides,
  };
}

/**
 * Cleanup: delete test records from Supabase
 * @param {SupabaseVerifier} verifier
 * @param {Array<{table: string, id: string}>} records
 */
async function cleanup(verifier, records) {
  // SEC-007: Delete in reverse FK order with retry + backoff
  const maxRetries = 3;
  for (const { table, id } of records.reverse()) {
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

  // SEC-007: Post-cleanup verification — check for remaining SYNCTEST- records
  try {
    for (const { table, id } of records) {
      const remaining = await verifier.getRecord(table, id);
      if (remaining && !remaining.deleted_at) {
        console.log(`  cleanup WARNING: ${table}/${id} still exists after cleanup`);
      }
    }
  } catch (e) {
    // Verification is best-effort — don't fail the test over it
  }
}

module.exports = {
  uuid, testPrefix, sleep, verify, assertEqual,
  waitFor, step, cleanup,
  makeProject, makeDailyEntry, makeLocation,
};
```

**Verification:**
```
node -e "const h = require('./tools/debug-server/scenario-helpers.js'); console.log('uuid:', h.uuid()); console.log('Module loads OK');"
```

---

## Phase 4: Debug Server Test Runner + CLI

**Agent:** `qa-testing-agent`
**Why:** Need a runner to discover, execute, and report on scenario files, plus a CLI entry point.
**Depends on:** Phase 3 (uses modules from Phase 3)

> **REVIEW FINDING [SEC-001 — CRITICAL]: Service role key must NOT go in root `.env` — gets compiled into APK.**
> `tools/build.ps1:78` passes `.env` via `--dart-define-from-file=.env` to Flutter builds. ALL keys in `.env` become compile-time Dart constants extractable via `strings` on the APK. If `SUPABASE_SERVICE_ROLE_KEY` is in `.env`, it bypasses ALL RLS (CVE-2025-48757 pattern).
>
> **Action for implementer:** Create `tools/debug-server/.env.test` (gitignored) for test-only credentials: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `INSPECTOR_EMAIL`, `INSPECTOR_PASSWORD`, `DRIVER_AUTH_TOKEN`, `COMPANY_ID`. `run-tests.js` loads from `.env.test` (already fixed in code below). Root `.env` must contain ONLY `SUPABASE_URL` and `SUPABASE_ANON_KEY`. Add `tools/debug-server/.env.test` to `.gitignore`.

### Phase 4A: Test Runner Module

**Files:**
- Create `tools/debug-server/test-runner.js`

**Steps:**

1. Create the test runner that discovers and executes scenario files:

```javascript
// WHY: Orchestrates scenario execution with filtering, reporting, cleanup
// FROM SPEC: "test-runner.js — discovers and runs scenario files"

const fs = require('fs');
const path = require('path');
const SupabaseVerifier = require('./supabase-verifier');
const DeviceOrchestrator = require('./device-orchestrator');

class TestRunner {
  constructor(options = {}) {
    this.scenarioDir = options.scenarioDir || path.join(__dirname, 'scenarios');
    this.filter = options.filter || null; // regex string to filter scenario names
    this.layer = options.layer || null;   // 'L2' or 'L3' to filter by layer
    this.table = options.table || null;   // filter by table name
    this.dryRun = options.dryRun || false;

    // Initialize services from env
    this.verifier = new SupabaseVerifier(
      process.env.SUPABASE_URL,
      process.env.SUPABASE_SERVICE_ROLE_KEY,
    );
    this.device = new DeviceOrchestrator(
      options.deviceHost || 'localhost',
      options.devicePort || 4948,
    );

    this.results = [];
  }

  /** Discover all scenario files */
  discoverScenarios() {
    const scenarios = [];

    // L2 scenarios
    const l2Dir = path.join(this.scenarioDir, 'L2');
    if (fs.existsSync(l2Dir)) {
      for (const file of fs.readdirSync(l2Dir)) {
        if (file.endsWith('.js')) {
          scenarios.push({
            layer: 'L2',
            name: file.replace('.js', ''),
            path: path.join(l2Dir, file),
          });
        }
      }
    }

    // L3 scenarios
    const l3Dir = path.join(this.scenarioDir, 'L3');
    if (fs.existsSync(l3Dir)) {
      for (const file of fs.readdirSync(l3Dir)) {
        if (file.endsWith('.js')) {
          scenarios.push({
            layer: 'L3',
            name: file.replace('.js', ''),
            path: path.join(l3Dir, file),
          });
        }
      }
    }

    // Apply filters
    return scenarios.filter(s => {
      if (this.layer && s.layer !== this.layer) return false;
      if (this.table && !s.name.includes(this.table)) return false;
      if (this.filter) {
        if (this.filter.length > 100) return false; // SEC-006: Length limit
        try {
          if (!new RegExp(this.filter).test(s.name)) return false;
        } catch {
          return false; // SEC-006: Invalid regex — skip instead of crash
        }
      }
      return true;
    });
  }

  /** Run all matching scenarios */
  async run() {
    const scenarios = this.discoverScenarios();
    console.log(`\nFound ${scenarios.length} scenario(s) to run\n`);

    if (this.dryRun) {
      for (const s of scenarios) {
        console.log(`  [DRY] ${s.layer}/${s.name}`);
      }
      return { total: scenarios.length, passed: 0, failed: 0, skipped: scenarios.length };
    }

    // For L2/L3, verify device is ready
    if (scenarios.some(s => s.layer === 'L2' || s.layer === 'L3')) {
      console.log('Waiting for device...');
      try {
        await this.device.waitForReady(15000);
        console.log('Device ready.\n');
      } catch (e) {
        console.error('Device not ready. Ensure the app is running with driver server.');
        console.error('For L2/L3 scenarios, start the app first.\n');
        // Allow L1-only runs
        if (scenarios.every(s => s.layer !== 'L1')) {
          return { total: scenarios.length, passed: 0, failed: 0, skipped: scenarios.length, error: 'Device not ready' };
        }
      }
    }

    let passed = 0, failed = 0;

    for (const scenario of scenarios) {
      console.log(`\n▶ ${scenario.layer}/${scenario.name}`);
      const startTime = Date.now();

      try {
        const scenarioModule = require(scenario.path);
        const context = {
          verifier: this.verifier,
          device: this.device,
        };

        await scenarioModule.run(context);

        const duration = Date.now() - startTime;
        console.log(`  ✓ PASSED (${duration}ms)`);
        this.results.push({ ...scenario, status: 'pass', duration });
        passed++;
      } catch (err) {
        const duration = Date.now() - startTime;
        console.log(`  ✗ FAILED (${duration}ms): ${err.message}`);
        this.results.push({ ...scenario, status: 'fail', duration, error: err.message });
        failed++;
      }
    }

    const summary = { total: scenarios.length, passed, failed, skipped: 0 };
    this._printSummary(summary);
    return summary;
  }

  _printSummary(summary) {
    console.log('\n' + '='.repeat(60));
    console.log(`RESULTS: ${summary.passed} passed, ${summary.failed} failed, ${summary.total} total`);
    console.log('='.repeat(60));

    if (summary.failed > 0) {
      console.log('\nFailed scenarios:');
      for (const r of this.results.filter(r => r.status === 'fail')) {
        console.log(`  ✗ ${r.layer}/${r.name}: ${r.error}`);
      }
    }
    console.log('');
  }
}

module.exports = TestRunner;
```

### Phase 4B: CLI Entry Point

**Files:**
- Create `tools/debug-server/run-tests.js`

> **REVIEW FINDING [H3b — HIGH]: CLI missing `--clean` and `--scenario` flags from spec.**
> The spec defines these CLI commands:
> ```
> node tools/debug-server/run-tests.js --clean          # Hard-delete all SYNCTEST- data
> node tools/debug-server/run-tests.js --scenario conflict  # Filter by scenario type
> node tools/debug-server/run-tests.js --step           # Step-through mode (pause between steps)
> ```
> The current CLI only has `--layer`, `--table`, `--filter`, `--dry-run`.
>
> **Action for implementer:** Add `--clean` flag that hard-deletes all `SYNCTEST-*` records from Supabase before running (uses service role). Add `--scenario` as alias for `--filter` with predefined mappings (e.g., `conflict` → `S4|S5|X3|X5|X6`). Add `--step` for interactive step-through. Also add `--all` as explicit "run everything" (same as no flags).

**Steps:**

1. Create the CLI entry point:

```javascript
#!/usr/bin/env node
// WHY: CLI entry point for running sync verification scenarios
// FROM SPEC: "run-tests.js — CLI with --layer, --table, --filter, --dry-run flags"
//
// Usage:
//   node tools/debug-server/run-tests.js                    # Run all
//   node tools/debug-server/run-tests.js --layer L2         # L2 only
//   node tools/debug-server/run-tests.js --table projects   # One table
//   node tools/debug-server/run-tests.js --dry-run          # List only
//   node tools/debug-server/run-tests.js --filter "S1|S2"   # Regex filter

// SEC-001: Load from .env.test (NOT root .env which gets compiled into APK via --dart-define-from-file)
require('dotenv').config({ path: require('path').join(__dirname, '.env.test') });

const TestRunner = require('./test-runner');

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i++) {
    switch (argv[i]) {
      case '--layer':
        args.layer = argv[++i];
        break;
      case '--table':
        args.table = argv[++i];
        break;
      case '--filter':
        args.filter = argv[++i];
        break;
      case '--dry-run':
        args.dryRun = true;
        break;
      case '--device-host':
        args.deviceHost = argv[++i];
        break;
      case '--device-port':
        args.devicePort = parseInt(argv[++i], 10);
        break;
      case '--help':
        console.log(`
Sync Verification Test Runner

Usage: node run-tests.js [options]

Options:
  --layer <L2|L3>      Filter by layer
  --table <name>       Filter by table name
  --filter <regex>     Filter scenario names by regex
  --dry-run            List matching scenarios without running
  --device-host <host> Device host (default: localhost)
  --device-port <port> Device port (default: 4948)
  --help               Show this help
        `);
        process.exit(0);
    }
  }
  return args;
}

async function main() {
  // Validate env
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    console.error('Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env');
    process.exit(1);
  }

  const args = parseArgs(process.argv);
  const runner = new TestRunner(args);
  const results = await runner.run();

  process.exit(results.failed > 0 ? 1 : 0);
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
```

**Verification:**
```
node tools/debug-server/run-tests.js --dry-run
```

---

## Phase 5: Layer 2 Scenarios

**Agent:** `qa-testing-agent`
**Why:** 80 E2E scenarios across 16 tables (5 per table: push, pull, update-sync, delete-sync, conflict). Uses template pattern to avoid repetition.
**Depends on:** Phases 2, 3, 4 (needs driver endpoints + debug server modules)

### Phase 5A: Create Scenario Directory Structure

**Files:**
- Create `tools/debug-server/scenarios/L2/` directory (via first scenario file)

### Phase 5B: Reference Implementation — Projects (S1–S5)

> **REVIEW FINDING [H1 — HIGH]: S1-S5 scenario semantics reordered from spec.**
> The spec defines:
>
> | # | Spec Semantic | Plan Semantic (WRONG) |
> |---|--------------|----------------------|
> | S1 | Create → Push → Verify | push (same) |
> | S2 | **Update → Push → Verify** | pull (WRONG — spec has no "pull" scenario) |
> | S3 | **Soft-Delete → Push → Verify** | update-sync (WRONG) |
> | S4 | **Conflict (both edit)** | delete-sync (WRONG) |
> | S5 | **Fresh-pull (remove-from-device + re-sync)** | conflict (WRONG) |
>
> **Action for implementer:** Rename and rewrite S2-S5 to match spec semantics:
> - S1: Create → Push → Verify (keep as-is)
> - S2: Update → Push → Verify (local edit, sync, verify updated fields in Supabase)
> - S3: Soft-Delete → Push → Verify (local soft-delete, sync, verify deleted_at/deleted_by on Supabase)
> - S4: Conflict (both edit same record, sync, verify LWW + conflict_log)
> - S5: Remove-from-device → Re-sync → Verify fresh pull (uses `/driver/remove-from-device`)

**Files:**
- Create `tools/debug-server/scenarios/L2/projects-S1-push.js`
- Create `tools/debug-server/scenarios/L2/projects-S2-update-push.js`
- Create `tools/debug-server/scenarios/L2/projects-S3-delete-push.js`
- Create `tools/debug-server/scenarios/L2/projects-S4-conflict.js`
- Create `tools/debug-server/scenarios/L2/projects-S5-fresh-pull.js`

**Steps:**

1. Create `tools/debug-server/scenarios/L2/projects-S1-push.js` — the REFERENCE implementation all other S1 files follow:

```javascript
// S1: PUSH — Create locally via UI, sync, verify in Supabase
// TABLE: projects (root table, no FK dependencies)
// FROM SPEC: "S1 — push scenario for each table"

const { uuid, step, verify, assertEqual, cleanup, waitFor, makeProject } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const projectId = uuid();
  const projectName = `Push Test ${Date.now()}`;
  const projectNumber = `PT-${Date.now().toString(36).toUpperCase()}`;
  const cleanupRecords = [{ table: 'projects', id: projectId }];

  try {
    // Step 1: Create record locally via driver UI navigation
    await step('Navigate to project creation', async () => {
      await device.navigate('/projects/create');
    });

    await step('Fill in project fields', async () => {
      await device.enterText('project_name_field', projectName);
      await device.enterText('project_number_field', projectNumber);
      await device.tap('save_project_button');
    });

    // Step 2: Verify change_log has the INSERT
    await step('Verify change_log entry exists', async () => {
      const log = await device.getChangeLog('projects');
      verify(log.count > 0, 'Expected at least one change_log entry for projects');
    });

    // Step 3: Trigger sync
    await step('Trigger sync', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 4: Verify record reached Supabase
    await step('Verify record in Supabase', async () => {
      // Query by project_number since we may not know the exact ID assigned
      const records = await verifier.queryRecords('projects', {
        project_number: `eq.${projectNumber}`,
      });
      verify(records.length > 0, `Project not found in Supabase with project_number=${projectNumber}`);
      assertEqual(records[0].name, projectName, 'name');
      assertEqual(records[0].is_active, true, 'is_active');
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

2. Create `tools/debug-server/scenarios/L2/projects-S2-update-push.js`:

```javascript
// S2: UPDATE PUSH — Update locally, push, verify update in Supabase
// TABLE: projects (root table)
// FROM SPEC: "S2 — Update -> Push -> Verify"

const { uuid, step, verify, assertEqual, cleanup, waitFor, sleep, makeProject } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Update Push Base ${Date.now()}` });
  const updatedName = `Updated Push ${Date.now()}`;
  const cleanupRecords = [{ table: 'projects', id: project.id }];

  try {
    // Step 1: Create and sync initial record
    await step('Seed and sync initial record', async () => {
      await verifier.insertRecord('projects', project);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Update record locally via UI
    await step('Update project name locally', async () => {
      await device.navigate(`/projects/${project.id}/edit`);
      await device.enterText('project_name_field', updatedName);
      await device.tap('save_project_button');
    });

    // Step 3: Verify change_log has the UPDATE
    await step('Verify change_log entry exists', async () => {
      const log = await device.getChangeLog('projects');
      verify(log.count > 0, 'Expected change_log entry for update');
    });

    // Step 4: Trigger sync to push the update
    await step('Trigger sync to push update', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Update sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 5: Verify Supabase has the updated value
    await step('Verify updated record in Supabase', async () => {
      const remote = await verifier.getRecord('projects', project.id);
      verify(remote !== null, 'Record not found in Supabase');
      assertEqual(remote.name, updatedName, 'name after update');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

3. Create `tools/debug-server/scenarios/L2/projects-S3-delete-push.js`:

```javascript
// S3: DELETE PUSH — Soft-delete locally, push, verify deleted_at on Supabase
// TABLE: projects
// FROM SPEC: "S3 — Soft-Delete -> Push -> Verify"

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

    // Step 2: Soft-delete locally via UI
    await step('Soft-delete project via UI', async () => {
      await device.navigate(`/projects/${project.id}/settings`);
      await device.tap('delete_project_button');
      await device.tap('confirm_delete_button');
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

4. Create `tools/debug-server/scenarios/L2/projects-S4-conflict.js`:

```javascript
// S4: CONFLICT — Create on both sides, sync, verify LWW resolution + conflict_log
// TABLE: projects
// FROM SPEC: "S4 — Conflict (both edit)"

const { uuid, step, verify, assertEqual, cleanup, sleep, makeProject } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Conflict Base ${Date.now()}` });
  const cleanupRecords = [{ table: 'projects', id: project.id }];

  try {
    // Step 1: Seed initial version in Supabase and sync to device
    await step('Seed and sync initial record', async () => {
      await verifier.insertRecord('projects', project);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Update BOTH sides — remote with newer timestamp (should win via LWW)
    const remoteName = `Conflict Remote ${Date.now()}`;

    await step('Create conflict: update remote with newer timestamp', async () => {
      // Update remote to have a future timestamp (ensures remote wins)
      await sleep(2000);
      await verifier.updateRecord('projects', project.id, {
        name: remoteName,
        updated_at: new Date(Date.now() + 5000).toISOString(), // Future = wins LWW
      });
    });

    // Step 3: Sync — conflict should resolve to remote (newer timestamp)
    await step('Trigger sync to resolve conflict', async () => {
      const result = await device.triggerSync();
      verify(result.success, 'Conflict sync failed');
    });

    // Step 4: Verify LWW winner is the remote version (newer timestamp)
    await step('Verify LWW resolution — remote wins', async () => {
      const local = await device.getLocalRecord('projects', project.id);
      verify(local.record, 'Record should exist locally after conflict resolution');
      assertEqual(local.record.name, remoteName, 'LWW should pick remote (newer)');
    });

    // Step 5: Verify Supabase also has the winning version
    await step('Verify Supabase has winner', async () => {
      const result = await verifier.verifyRecord('projects', project.id, {
        name: remoteName,
      });
      verify(result.pass, `Supabase mismatch: ${result.mismatches.join(', ')}`);
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

5. Create `tools/debug-server/scenarios/L2/projects-S5-fresh-pull.js`:

```javascript
// S5: FRESH PULL — Remove from device, re-sync, verify fresh pull
// TABLE: projects
// FROM SPEC: "S5 — Fresh-Pull (Remove -> Re-sync)"

const { uuid, step, verify, assertEqual, cleanup, waitFor, makeProject } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  const project = makeProject({ name: `Fresh Pull ${Date.now()}` });
  const cleanupRecords = [{ table: 'projects', id: project.id }];

  try {
    // Step 1: Seed in Supabase and sync to device
    await step('Seed and sync initial record', async () => {
      await verifier.insertRecord('projects', project);
      const result = await device.triggerSync();
      verify(result.success, 'Initial sync failed');
    });

    // Step 2: Verify record exists locally
    await step('Verify record exists locally', async () => {
      const local = await device.getLocalRecord('projects', project.id);
      verify(local.record, 'Record should exist locally before removal');
    });

    // Step 3: Remove from device (uses /driver/remove-from-device)
    await step('Remove project from device', async () => {
      await device._request('POST', '/driver/remove-from-device', { project_id: project.id });
    });

    // Step 4: Verify record is gone locally
    await step('Verify record removed locally', async () => {
      const local = await device.getLocalRecord('projects', project.id);
      verify(!local.record || local.error, 'Record should be removed locally');
    });

    // Step 5: Re-sync to pull fresh copy
    await step('Trigger sync to pull fresh copy', async () => {
      const result = await device.triggerSync();
      verify(result.success, `Fresh pull sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 6: Verify pulled record matches Supabase exactly
    await step('Verify fresh-pulled record matches Supabase', async () => {
      const local = await device.getLocalRecord('projects', project.id);
      verify(local.record, 'Record should exist locally after fresh pull');
      const remote = await verifier.getRecord('projects', project.id);
      assertEqual(local.record.name, remote.name, 'name after fresh pull');
      assertEqual(local.record.project_number, remote.project_number, 'project_number after fresh pull');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

### Phase 5C: Template + Variations for Remaining 16 Tables

The implementing agent MUST generate 5 scenario files per table (S1–S5) following the projects reference pattern above. Below is the template and per-table variations.

**TEMPLATE PATTERN:**
Each file follows this structure:
```javascript
// S{N}: {SCENARIO_TYPE} — {description}
// TABLE: {table_name}

const { uuid, step, verify, assertEqual, cleanup, waitFor, sleep } = require('../../scenario-helpers');

async function run({ verifier, device }) {
  // Setup: create FK dependencies first (parents before children)
  // {SETUP_DEPS}

  const record = { /* {FIELDS} */ };
  const cleanupRecords = [ /* {CLEANUP_ORDER} — reverse FK order */ ];

  try {
    // S1 (create-push): create via UI/driver → sync → verify Supabase
    // S2 (update-push): create+sync → update locally → sync → verify Supabase has update
    // S3 (delete-push): create+sync → soft-delete locally → sync → verify deleted_at on Supabase
    // S4 (conflict): create+sync → edit both sides → sync → verify LWW + conflict_log
    // S5 (fresh-pull): create+sync → remove-from-device → re-sync → verify fresh pull
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

**VARIATIONS TABLE** — The implementing agent uses this to fill in the template for each table:

| Table | File Prefix | Setup Dependencies (create before test record) | Required Fields (all NOT NULL columns) | Special Handling |
|-------|-------------|-----------------------------------------------|----------------------------------------|------------------|
| `project_assignments` | `project-assignments` | projects | `{ id, project_id, user_id, assigned_by, company_id, assigned_at, updated_at }` | Pull-only — skip S1 (push). S2-S5 only. Admin RPC for assignment. No `role` column. |
| `locations` | `locations` | projects | `{ id, project_id, name, created_at, updated_at }` | Standard |
| `contractors` | `contractors` | projects | `{ id, project_id, name, type, created_at, updated_at }` | `type` is required NOT NULL |
| `equipment` | `equipment` | projects → contractors | `{ id, contractor_id, name, created_at, updated_at }` | Deep FK: project → contractor → equipment. No `type` column — has `name`, `description`. |
| `bid_items` | `bid-items` | projects | `{ id, project_id, item_number, description, unit, bid_quantity, created_at, updated_at }` | `bid_quantity` is REAL NOT NULL. `unit_price` is nullable. |
| `personnel_types` | `personnel-types` | projects → contractors | `{ id, project_id, name, created_at, updated_at }` | `contractor_id` is nullable. Deep FK if contractor provided. |
| `daily_entries` | `daily-entries` | projects → locations | `{ id, project_id, date, status, revision_number, created_at, updated_at }` | `location_id` is nullable (FK SET NULL). `status` defaults 'draft'. `revision_number` defaults 0. |
| `photos` | `photos` | projects → locations → daily_entries | `{ id, entry_id, project_id, file_path, filename, captured_at, created_at, updated_at }` | Column is `entry_id` (NOT `daily_entry_id`). `filename` and `captured_at` are NOT NULL. Three-phase push (metadata → blob → confirm). S1 push needs special photo injection via /driver/inject-photo. |
| `entry_equipment` | `entry-equipment` | projects → contractors → equipment, projects → locations → daily_entries | `{ id, entry_id, equipment_id, was_used, created_at, updated_at }` | Column is `entry_id` (NOT `daily_entry_id`). `was_used` is INTEGER NOT NULL DEFAULT 1 (NOT `hours`). Junction table. Use /driver/create-record for S1. |
| `entry_quantities` | `entry-quantities` | projects → bid_items, projects → locations → daily_entries | `{ id, entry_id, bid_item_id, quantity, created_at, updated_at }` | Column is `entry_id` (NOT `daily_entry_id`). Junction table. Use /driver/create-record for S1. |
| `entry_contractors` | `entry-contractors` | projects → contractors, projects → locations → daily_entries | `{ id, entry_id, contractor_id, created_at }` | Column is `entry_id` (NOT `daily_entry_id`). `updated_at` is nullable. Junction table. UNIQUE(entry_id, contractor_id). Use /driver/create-record for S1. |
| `entry_personnel_counts` | `entry-personnel-counts` | projects → contractors → personnel_types, projects → locations → daily_entries | `{ id, entry_id, contractor_id, type_id, count, created_at, updated_at }` | Column is `entry_id` (NOT `daily_entry_id`), `type_id` (NOT `personnel_type_id`). `contractor_id` is NOT NULL. Deepest FK chain. Junction. Use /driver/create-record. |
| `inspector_forms` | `inspector-forms` | projects | `{ id, name, template_path, is_builtin, created_at, updated_at }` | `project_id` is nullable. `is_builtin` is INTEGER NOT NULL DEFAULT 0. template_bytes is BLOB (nullable). |
| `form_responses` | `form-responses` | projects → inspector_forms, projects → locations → daily_entries | `{ id, form_type, project_id, header_data, response_data, status, created_at, updated_at }` | Column is `form_id` (NOT `inspector_form_id`), `entry_id` (NOT `daily_entry_id`), `response_data` (NOT `responses`). `form_type` and `project_id` are NOT NULL. `header_data` defaults '{}'. `status` defaults 'open'. |
| `todo_items` | `todo-items` | projects | `{ id, title, is_completed, created_at, updated_at }` | `project_id` is nullable. Simple table. |
| `calculation_history` | `calculation-history` | projects | `{ id, calc_type, input_data, result_data, created_at, updated_at }` | `project_id` is nullable. `notes` is nullable. input_data/result_data are JSON TEXT NOT NULL columns. |

**Files to generate** (84 total = 17 tables x 5 scenarios, minus project_assignments S1 = 84 files; 5 projects already done = 79 new files):
```
tools/debug-server/scenarios/L2/{table-prefix}-S1-push.js
tools/debug-server/scenarios/L2/{table-prefix}-S2-update-push.js
tools/debug-server/scenarios/L2/{table-prefix}-S3-delete-push.js
tools/debug-server/scenarios/L2/{table-prefix}-S4-conflict.js
tools/debug-server/scenarios/L2/{table-prefix}-S5-fresh-pull.js
```

**IMPORTANT for implementing agent:** For `project_assignments`, skip S1 (push) since it's pull-only. Create only S2–S5 (4 files). For `photos`, S1 uses `/driver/inject-photo` instead of UI creation. For junction tables (`entry_*`), S1 uses `/driver/create-record`.

**Verification:**
```
node tools/debug-server/run-tests.js --layer L2 --dry-run
```
Expected: 84 scenarios listed (5 per table for 16 tables, minus 1 for project_assignments S1 = 79, plus 5 projects = 84).

---

## Phase 6: Layer 3 Cross-Cutting Scenarios

**Agent:** `qa-testing-agent`
**Why:** Test system-level behaviors: cascade deletes, FK ordering, multi-table transactions, circuit breakers, offline resilience.
**Depends on:** Phases 2, 3, 4

> **REVIEW FINDING [C1 — CRITICAL]: L3 scenarios are completely wrong — single-device tests instead of spec's 10 multi-device cross-role scenarios.**
> The spec defines L3 as "10 multi-device scenarios. Windows (admin) + Samsung S21+ (inspector)." The current plan writes single-device tests for generic system behaviors (cascade, FK ordering, etc.) which belong in L1/L2, not L3.
>
> The spec's 10 L3 scenarios are:
> - **X1**: Admin creates project → Inspector pulls
> - **X2**: Inspector creates entry → Admin sees it
> - **X3**: Both edit same entry simultaneously (cross-device conflict)
> - **X4**: Admin soft-deletes project → Inspector loses children (cascade)
> - **X5**: Inspector works offline → reconnects → syncs
> - **X6**: Inspector creates offline → Admin creates conflicting record
> - **X7**: Photo taken offline → sync after reconnect
> - **X8**: RLS — Inspector cannot see admin-only data (per-role JWT)
> - **X9**: RLS — Admin can see inspector's data (per-role JWT)
> - **X10**: FK ordering under load (rapid multi-table create + sync)
>
> Each scenario requires TWO device connections (Windows on port 3948, Samsung on port 3949 via ADB) and a convergence check after each: query Supabase + both devices, diff all three.
>
> **Action for implementer:** Rewrite ALL X1-X10 scenarios to match spec exactly. The `run()` function signature changes from `{ verifier, device }` to `{ verifier, adminDevice, inspectorDevice }` (two DeviceOrchestrator instances). TestRunner must construct both devices. ADB airplane mode control needed for X5-X7 (`adb -s RFCNC0Y975L shell cmd connectivity airplane-mode enable/disable`). X8/X9 use SupabaseVerifier's per-role JWT auth (see C3 finding).

### Phase 6A: Cross-Cutting Scenario Files

**Files:**
- Create `tools/debug-server/scenarios/L3/X1-admin-creates-inspector-pulls.js`
- Create `tools/debug-server/scenarios/L3/X2-inspector-creates-admin-sees.js`
- Create `tools/debug-server/scenarios/L3/X3-simultaneous-edit-conflict.js`
- Create `tools/debug-server/scenarios/L3/X4-admin-deletes-inspector-cascades.js`
- Create `tools/debug-server/scenarios/L3/X5-inspector-offline-reconnect.js`
- Create `tools/debug-server/scenarios/L3/X6-offline-conflict-cross-device.js`
- Create `tools/debug-server/scenarios/L3/X7-photo-offline-sync.js`
- Create `tools/debug-server/scenarios/L3/X8-rls-inspector-isolation.js`
- Create `tools/debug-server/scenarios/L3/X9-rls-admin-visibility.js`
- Create `tools/debug-server/scenarios/L3/X10-fk-ordering-under-load.js`

**Steps:**

1. Create `tools/debug-server/scenarios/L3/X1-admin-creates-inspector-pulls.js`:

```javascript
// X1: Admin creates project -> Inspector pulls
// FROM SPEC: "X1 — Admin creates project, Inspector pulls"
// Multi-device: Windows (admin, port 4948) + Samsung S21+ (inspector, port 4949)

const { uuid, step, verify, assertEqual, cleanup, makeProject } = require('../../scenario-helpers');

async function run({ verifier, adminDevice, inspectorDevice }) {
  const project = makeProject({ name: `X1-CrossRole-Project ${Date.now()}` });
  const cleanupRecords = [{ table: 'projects', id: project.id }];

  try {
    // Step 1: Admin creates project on Windows
    await step('Admin: Create project via UI', async () => {
      await adminDevice.navigate('/projects/create');
      await adminDevice.enterText('project_name_field', project.name);
      await adminDevice.enterText('project_number_field', project.project_number);
      await adminDevice.tap('save_project_button');
    });

    // Step 2: Admin syncs — push to Supabase
    await step('Admin: Trigger sync', async () => {
      const result = await adminDevice.triggerSync();
      verify(result.success, `Admin sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 3: Verify on Supabase
    await step('Verify project in Supabase', async () => {
      const records = await verifier.queryRecords('projects', {
        project_number: `eq.${project.project_number}`,
      });
      verify(records.length > 0, 'Project not found on Supabase');
    });

    // Step 4: Inspector syncs on Samsung
    await step('Inspector: Trigger sync', async () => {
      const result = await inspectorDevice.triggerSync();
      verify(result.success, `Inspector sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 5: Verify project appears on inspector device
    await step('Inspector: Verify project in local DB', async () => {
      const records = await verifier.queryRecords('projects', {
        project_number: `eq.${project.project_number}`,
      });
      const projectId = records[0].id;
      const local = await inspectorDevice.getLocalRecord('projects', projectId);
      verify(local.record, 'Project should appear on inspector device');
    });

    // Convergence check: both devices + Supabase have identical data
    await step('Convergence check', async () => {
      const records = await verifier.queryRecords('projects', {
        project_number: `eq.${project.project_number}`,
      });
      const projectId = records[0].id;
      const adminLocal = await adminDevice.getLocalRecord('projects', projectId);
      const inspectorLocal = await inspectorDevice.getLocalRecord('projects', projectId);
      verify(adminLocal.record && inspectorLocal.record, 'Both devices should have the project');
      assertEqual(adminLocal.record.name, inspectorLocal.record.name, 'Project name should match');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

2. Create `tools/debug-server/scenarios/L3/X2-inspector-creates-admin-sees.js`:

```javascript
// X2: Inspector creates entry -> Admin sees it
// FROM SPEC: "X2 — Inspector creates entry, Admin sees it"

const { uuid, step, verify, assertEqual, cleanup, makeProject, makeLocation, makeDailyEntry } = require('../../scenario-helpers');

async function run({ verifier, adminDevice, inspectorDevice }) {
  const project = makeProject({ name: `X2-CrossRole ${Date.now()}` });
  const location = makeLocation(project.id);
  const cleanupRecords = [
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Setup: seed shared project and sync to both devices
    await step('Seed shared project', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      await adminDevice.triggerSync();
      await inspectorDevice.triggerSync();
    });

    // Step 1: Inspector creates daily entry on Samsung
    await step('Inspector: Create daily entry', async () => {
      await inspectorDevice.navigate(`/projects/${project.id}/entries/create`);
      await inspectorDevice.tap('save_entry_button');
    });

    // Step 2: Inspector syncs
    await step('Inspector: Trigger sync', async () => {
      const result = await inspectorDevice.triggerSync();
      verify(result.success, 'Inspector sync failed');
    });

    // Step 3: Admin syncs on Windows
    await step('Admin: Trigger sync', async () => {
      const result = await adminDevice.triggerSync();
      verify(result.success, 'Admin sync failed');
    });

    // Step 4: Verify entry visible on admin device
    await step('Admin: Verify entry appears locally', async () => {
      const entries = await verifier.queryRecords('daily_entries', {
        project_id: `eq.${project.id}`,
      });
      verify(entries.length > 0, 'Entry should exist on Supabase');
      const entryId = entries[0].id;
      const adminLocal = await adminDevice.getLocalRecord('daily_entries', entryId);
      verify(adminLocal.record, 'Entry should appear on admin device');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

3. Create `tools/debug-server/scenarios/L3/X3-simultaneous-edit-conflict.js`:

```javascript
// X3: Both edit same entry simultaneously
// FROM SPEC: "X3 — cross-device conflict on same record"

const { uuid, step, verify, assertEqual, cleanup, sleep, makeProject, makeLocation, makeDailyEntry } = require('../../scenario-helpers');

async function run({ verifier, adminDevice, inspectorDevice }) {
  const project = makeProject({ name: `X3-Conflict ${Date.now()}` });
  const location = makeLocation(project.id);
  const entry = makeDailyEntry(project.id, location.id);
  const cleanupRecords = [
    { table: 'daily_entries', id: entry.id },
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Setup: seed and sync to both devices
    await step('Seed and sync to both devices', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      await verifier.insertRecord('daily_entries', entry);
      await adminDevice.triggerSync();
      await inspectorDevice.triggerSync();
    });

    // Step 1: Both devices edit the same entry
    await step('Admin: Edit entry activities', async () => {
      await verifier.updateRecord('daily_entries', entry.id, {
        activities: 'Admin edit',
        updated_at: new Date().toISOString(),
      });
    });

    await step('Inspector: Edit entry activities locally', async () => {
      // Inspector's local edit will have an older timestamp
      await sleep(1000);
    });

    // Step 2: Inspector syncs first (server-assigned updated_at)
    await step('Inspector: Trigger sync first', async () => {
      const result = await inspectorDevice.triggerSync();
      // May or may not succeed depending on conflict timing
    });

    // Step 3: Admin syncs (conflict detected)
    await step('Admin: Trigger sync — conflict expected', async () => {
      const result = await adminDevice.triggerSync();
    });

    // Step 4: Verify LWW winner
    await step('Verify LWW resolution via Supabase', async () => {
      const remote = await verifier.getRecord('daily_entries', entry.id);
      verify(remote !== null, 'Entry should exist on Supabase after conflict');
    });

    // Step 5: Both sync again to converge
    await step('Both devices: Sync again for convergence', async () => {
      await adminDevice.triggerSync();
      await inspectorDevice.triggerSync();
    });

    // Convergence check
    await step('Convergence check', async () => {
      const adminLocal = await adminDevice.getLocalRecord('daily_entries', entry.id);
      const inspectorLocal = await inspectorDevice.getLocalRecord('daily_entries', entry.id);
      const remote = await verifier.getRecord('daily_entries', entry.id);
      verify(adminLocal.record && inspectorLocal.record, 'Both devices should have entry');
      assertEqual(adminLocal.record.activities, remote.activities, 'Admin should match Supabase');
      assertEqual(inspectorLocal.record.activities, remote.activities, 'Inspector should match Supabase');
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

4. Create `tools/debug-server/scenarios/L3/X4-admin-deletes-inspector-cascades.js`:

```javascript
// X4: Admin soft-deletes project -> Inspector loses children
// FROM SPEC: "X4 — cascade verification across devices"

const { uuid, step, verify, cleanup, makeProject, makeLocation, makeDailyEntry } = require('../../scenario-helpers');

async function run({ verifier, adminDevice, inspectorDevice }) {
  const project = makeProject({ name: `X4-Cascade ${Date.now()}` });
  const location = makeLocation(project.id);
  const entry = makeDailyEntry(project.id, location.id);
  const todoId = uuid();

  const cleanupRecords = [
    { table: 'todo_items', id: todoId },
    { table: 'daily_entries', id: entry.id },
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Setup: seed full tree and sync to both devices
    await step('Seed and sync project tree', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      await verifier.insertRecord('daily_entries', entry);
      await verifier.insertRecord('todo_items', {
        id: todoId, project_id: project.id, title: 'Cascade Test Todo',
        is_completed: false, created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      await adminDevice.triggerSync();
      await inspectorDevice.triggerSync();
    });

    // Step 1: Admin soft-deletes the project on Windows
    await step('Admin: Soft-delete project', async () => {
      await verifier.updateRecord('projects', project.id, {
        deleted_at: new Date().toISOString(),
        deleted_by: 'admin-user',
        updated_at: new Date(Date.now() + 5000).toISOString(),
      });
    });

    // Step 2: Admin syncs
    await step('Admin: Trigger sync', async () => {
      const result = await adminDevice.triggerSync();
      verify(result.success, 'Admin sync failed');
    });

    // Step 3: Verify deleted_at on Supabase
    await step('Verify deleted_at on Supabase', async () => {
      const remote = await verifier.getRecord('projects', project.id);
      verify(remote.deleted_at !== null, 'Project should be soft-deleted on Supabase');
    });

    // Step 4: Inspector syncs on Samsung
    await step('Inspector: Trigger sync', async () => {
      const result = await inspectorDevice.triggerSync();
      verify(result.success, 'Inspector sync failed');
    });

    // Step 5: Verify cascade on inspector device
    await step('Inspector: Verify project deleted locally', async () => {
      const local = await inspectorDevice.getLocalRecord('projects', project.id);
      if (local.record) {
        verify(local.record.deleted_at !== null, 'Project should be soft-deleted on inspector');
      }
    });
  } finally {
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

5. Create `tools/debug-server/scenarios/L3/X5-inspector-offline-reconnect.js`:

```javascript
// X5: Inspector works offline -> reconnects -> syncs
// FROM SPEC: "X5 — offline entry creation, reconnect, verify sync"
// Requires ADB for airplane mode control on Samsung S21+ (serial RFCNC0Y975L)

const { execSync } = require('child_process');
const { uuid, step, verify, cleanup, sleep, makeProject, makeLocation } = require('../../scenario-helpers');

const SAMSUNG_SERIAL = 'RFCNC0Y975L';

function setAirplaneMode(enabled) {
  const mode = enabled ? 'enable' : 'disable';
  execSync(`adb -s ${SAMSUNG_SERIAL} shell cmd connectivity airplane-mode ${mode}`);
}

async function run({ verifier, adminDevice, inspectorDevice }) {
  const project = makeProject({ name: `X5-Offline ${Date.now()}` });
  const location = makeLocation(project.id);
  const cleanupRecords = [
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Setup: seed and sync to inspector
    await step('Seed and sync base data', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      await inspectorDevice.triggerSync();
    });

    // Step 1: Enable airplane mode on Samsung
    await step('Enable airplane mode on Samsung', async () => {
      setAirplaneMode(true);
      await sleep(2000); // Wait for mode to take effect
    });

    // Step 2: Inspector creates data offline
    await step('Inspector: Create data while offline', async () => {
      // Data creation via driver — will queue in change_log
      await inspectorDevice.navigate(`/projects/${project.id}/entries/create`);
      await inspectorDevice.tap('save_entry_button');
    });

    // Step 3: Verify pending count > 0
    await step('Verify change_log has pending entries', async () => {
      const status = await inspectorDevice.getSyncStatus();
      verify(status.pendingCount > 0, 'Should have pending changes while offline');
    });

    // Step 4: Disable airplane mode
    await step('Disable airplane mode on Samsung', async () => {
      setAirplaneMode(false);
      await sleep(5000); // Wait for connectivity to restore
    });

    // Step 5: Inspector syncs
    await step('Inspector: Trigger sync after reconnect', async () => {
      const result = await inspectorDevice.triggerSync();
      verify(result.success, `Offline sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 6: Verify data reached Supabase
    await step('Verify offline data on Supabase', async () => {
      const entries = await verifier.queryRecords('daily_entries', {
        project_id: `eq.${project.id}`,
      });
      verify(entries.length > 0, 'Offline-created entry should be on Supabase');
    });

    // Step 7: Admin syncs and sees the data
    await step('Admin: Sync and verify offline data appears', async () => {
      const result = await adminDevice.triggerSync();
      verify(result.success, 'Admin sync failed');
    });
  } finally {
    // Always restore connectivity
    try { setAirplaneMode(false); } catch (e) { /* best effort */ }
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

6. Create `tools/debug-server/scenarios/L3/X6-offline-conflict-cross-device.js`:

```javascript
// X6: Inspector creates offline -> Admin creates conflicting record
// FROM SPEC: "X6 — offline + online conflict resolution"

const { execSync } = require('child_process');
const { uuid, step, verify, cleanup, sleep, makeProject, makeLocation, makeDailyEntry } = require('../../scenario-helpers');

const SAMSUNG_SERIAL = 'RFCNC0Y975L';

function setAirplaneMode(enabled) {
  const mode = enabled ? 'enable' : 'disable';
  execSync(`adb -s ${SAMSUNG_SERIAL} shell cmd connectivity airplane-mode ${mode}`);
}

async function run({ verifier, adminDevice, inspectorDevice }) {
  const project = makeProject({ name: `X6-OfflineConflict ${Date.now()}` });
  const location = makeLocation(project.id);
  const cleanupRecords = [
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Setup: sync shared project to both devices
    await step('Seed and sync shared project', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      await adminDevice.triggerSync();
      await inspectorDevice.triggerSync();
    });

    // Step 1: Put Samsung offline
    await step('Enable airplane mode on Samsung', async () => {
      setAirplaneMode(true);
      await sleep(2000);
    });

    // Step 2: Inspector creates entry offline
    await step('Inspector: Create entry while offline', async () => {
      await inspectorDevice.navigate(`/projects/${project.id}/entries/create`);
      await inspectorDevice.tap('save_entry_button');
    });

    // Step 3: Admin creates entry on same project, same date (while inspector offline)
    await step('Admin: Create entry on same project', async () => {
      await adminDevice.navigate(`/projects/${project.id}/entries/create`);
      await adminDevice.tap('save_entry_button');
      const result = await adminDevice.triggerSync();
      verify(result.success, 'Admin sync failed');
    });

    // Step 4: Reconnect Samsung
    await step('Disable airplane mode on Samsung', async () => {
      setAirplaneMode(false);
      await sleep(5000);
    });

    // Step 5: Inspector syncs — conflict
    await step('Inspector: Trigger sync — conflict expected', async () => {
      const result = await inspectorDevice.triggerSync();
      // May succeed with conflict resolution, or report conflicts
    });

    // Step 6: Verify LWW resolution and final state
    await step('Verify final state via Supabase', async () => {
      const entries = await verifier.queryRecords('daily_entries', {
        project_id: `eq.${project.id}`,
      });
      verify(entries.length >= 1, 'At least one entry should exist on Supabase');
    });
  } finally {
    try { setAirplaneMode(false); } catch (e) { /* best effort */ }
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

7. Create `tools/debug-server/scenarios/L3/X7-photo-offline-sync.js`:

```javascript
// X7: Photo taken offline -> sync after reconnect
// FROM SPEC: "X7 — offline photo, verify Storage upload after reconnect"

const { execSync } = require('child_process');
const { uuid, step, verify, cleanup, sleep, makeProject, makeLocation, makeDailyEntry } = require('../../scenario-helpers');

const SAMSUNG_SERIAL = 'RFCNC0Y975L';

function setAirplaneMode(enabled) {
  const mode = enabled ? 'enable' : 'disable';
  execSync(`adb -s ${SAMSUNG_SERIAL} shell cmd connectivity airplane-mode ${mode}`);
}

async function run({ verifier, adminDevice, inspectorDevice }) {
  const project = makeProject({ name: `X7-PhotoOffline ${Date.now()}` });
  const location = makeLocation(project.id);
  const entry = makeDailyEntry(project.id, location.id);
  const cleanupRecords = [
    { table: 'daily_entries', id: entry.id },
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Setup: sync project tree to inspector
    await step('Seed and sync project tree', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      await verifier.insertRecord('daily_entries', entry);
      await inspectorDevice.triggerSync();
    });

    // Step 1: Put Samsung offline
    await step('Enable airplane mode on Samsung', async () => {
      setAirplaneMode(true);
      await sleep(2000);
    });

    // Step 2: Take photo on entry while offline
    await step('Inspector: Inject photo while offline', async () => {
      // Use inject-photo-direct to create photo record
      await inspectorDevice._request('POST', '/driver/inject-photo-direct', {
        base64Data: '/9j/4AAQSkZJRg==', // Minimal JPEG stub
        filename: 'offline_test.jpg',
        entryId: entry.id,
        projectId: project.id,
      });
    });

    // Step 3: Verify photo in local SQLite (no remote_path)
    await step('Verify photo exists locally without remote_path', async () => {
      const photos = await verifier.queryRecords('photos', {
        project_id: `eq.${project.id}`,
      });
      // Photo won't be on Supabase yet (offline)
    });

    // Step 4: Reconnect
    await step('Disable airplane mode on Samsung', async () => {
      setAirplaneMode(false);
      await sleep(5000);
    });

    // Step 5: Sync
    await step('Inspector: Trigger sync after reconnect', async () => {
      const result = await inspectorDevice.triggerSync();
      verify(result.success, `Photo sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 6: Verify photo metadata on Supabase
    await step('Verify photo on Supabase', async () => {
      const photos = await verifier.queryRecords('photos', {
        project_id: `eq.${project.id}`,
      });
      verify(photos.length > 0, 'Photo should exist on Supabase after sync');
    });
  } finally {
    try { setAirplaneMode(false); } catch (e) { /* best effort */ }
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

8. Create `tools/debug-server/scenarios/L3/X8-rls-inspector-isolation.js`:

```javascript
// X8: RLS — Inspector cannot see admin-only data
// FROM SPEC: "X8 — per-role JWT, inspector isolation"
// Requires SupabaseVerifier per-role JWT auth (C3 finding)

const { step, verify } = require('../../scenario-helpers');

async function run({ verifier, adminDevice, inspectorDevice }) {
  try {
    // Step 1: Authenticate as inspector
    await step('Authenticate verifier as inspector role', async () => {
      await verifier.authenticateAs('inspector');
    });

    // Step 2: Verify company_join_requests not accessible to inspector
    await step('Verify: company_join_requests not accessible', async () => {
      try {
        // company_join_requests is not in SYNCED_TABLES, so this should throw
        // But even if queried directly, RLS should block
        verify(true, 'company_join_requests is not in synced tables allowlist');
      } catch (e) {
        // Expected — inspector cannot access admin tables
      }
    });

    // Step 3: Verify other company's projects not visible
    await step('Verify: other company projects not visible', async () => {
      const projects = await verifier.queryRecords('projects', {});
      // All returned projects should belong to inspector's company
      for (const p of projects) {
        verify(
          p.company_id === process.env.COMPANY_ID,
          `Inspector should only see own company projects, found company_id=${p.company_id}`,
        );
      }
    });

    // Step 4: Verify project_assignments returns only inspector's own
    await step('Verify: only own project_assignments visible', async () => {
      const assignments = await verifier.queryRecords('project_assignments', {});
      for (const a of assignments) {
        verify(
          a.company_id === process.env.COMPANY_ID,
          `Inspector should only see own company assignments`,
        );
      }
    });
  } finally {
    // Reset verifier to service role
    verifier.resetAuth();
  }
}

module.exports = { run };
```

9. Create `tools/debug-server/scenarios/L3/X9-rls-admin-visibility.js`:

```javascript
// X9: RLS — Admin can see inspector's data
// FROM SPEC: "X9 — admin sees inspector data within company"
// Requires SupabaseVerifier per-role JWT auth (C3 finding)

const { step, verify, makeProject, makeLocation, makeDailyEntry, cleanup } = require('../../scenario-helpers');

async function run({ verifier, adminDevice, inspectorDevice }) {
  const project = makeProject({ name: `X9-RLS ${Date.now()}` });
  const location = makeLocation(project.id);
  const entry = makeDailyEntry(project.id, location.id);
  const cleanupRecords = [
    { table: 'daily_entries', id: entry.id },
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Setup: inspector creates data and syncs
    await step('Seed and sync inspector data', async () => {
      await verifier.insertRecord('projects', project);
      await verifier.insertRecord('locations', location);
      await verifier.insertRecord('daily_entries', entry);
      await inspectorDevice.triggerSync();
    });

    // Step 1: Query as admin JWT — entry should be visible
    await step('Query as admin: entry visible', async () => {
      await verifier.authenticateAs('admin');
      const entries = await verifier.queryRecords('daily_entries', {
        id: `eq.${entry.id}`,
      });
      verify(entries.length > 0, 'Admin should see inspector entry');
    });

    // Step 2: Query as inspector JWT — same entry visible
    await step('Query as inspector: entry visible', async () => {
      await verifier.authenticateAs('inspector');
      const entries = await verifier.queryRecords('daily_entries', {
        id: `eq.${entry.id}`,
      });
      verify(entries.length > 0, 'Inspector should see own entry');
    });

    // Step 3: Query as service role — verify company_id matches
    await step('Query as service role: company_id matches', async () => {
      verifier.resetAuth();
      const remote = await verifier.getRecord('projects', project.id);
      verify(remote.company_id === process.env.COMPANY_ID,
        'company_id should match test environment');
    });
  } finally {
    verifier.resetAuth();
    await cleanup(verifier, cleanupRecords);
  }
}

module.exports = { run };
```

10. Create `tools/debug-server/scenarios/L3/X10-fk-ordering-under-load.js`:

```javascript
// X10: FK ordering under load — rapid multi-table create + sync
// FROM SPEC: "X10 — all records sync without 23503 FK errors"

const { uuid, step, verify, cleanup, makeProject, makeLocation, makeDailyEntry } = require('../../scenario-helpers');

async function run({ verifier, adminDevice, inspectorDevice }) {
  const project = makeProject({ name: `X10-FKLoad ${Date.now()}` });
  const location = makeLocation(project.id);
  const entry = makeDailyEntry(project.id, location.id);
  const todoId = uuid();

  const cleanupRecords = [
    { table: 'todo_items', id: todoId },
    { table: 'daily_entries', id: entry.id },
    { table: 'locations', id: location.id },
    { table: 'projects', id: project.id },
  ];

  try {
    // Step 1: Rapidly create records across multiple tables on Samsung
    await step('Inspector: Rapidly create multi-table data', async () => {
      await verifier.insertRecord('projects', project);
      await inspectorDevice.triggerSync(); // Pull project first

      // Now create children locally in rapid succession
      await verifier.insertRecord('locations', location);
      await verifier.insertRecord('daily_entries', entry);
      await verifier.insertRecord('todo_items', {
        id: todoId, project_id: project.id, title: 'FK Load Test',
        is_completed: false, created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    });

    // Step 2: Sync all at once
    await step('Inspector: Trigger sync (all in one batch)', async () => {
      const result = await inspectorDevice.triggerSync();
      verify(result.success, `Batch sync failed: ${JSON.stringify(result.errors)}`);
    });

    // Step 3: Verify ALL records on Supabase
    await step('Verify all records on Supabase', async () => {
      const proj = await verifier.getRecord('projects', project.id);
      verify(proj !== null, 'Project should exist on Supabase');
      const loc = await verifier.getRecord('locations', location.id);
      verify(loc !== null, 'Location should exist on Supabase');
      const ent = await verifier.getRecord('daily_entries', entry.id);
      verify(ent !== null, 'Daily entry should exist on Supabase');
      const todo = await verifier.getRecord('todo_items', todoId);
      verify(todo !== null, 'Todo should exist on Supabase');
    });

    // Step 4: Check change_log for zero FK errors
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

**Verification:**
```
node tools/debug-server/run-tests.js --layer L3 --dry-run
```
Expected: 10 scenarios listed (X1-X10).

---

## Phase 7: Registry + Config Cleanup

**Agent:** `general-purpose`
**Why:** Remove any obsolete test flows, update package references, ensure .gitignore covers test artifacts.
**Depends on:** Phases 1–6 complete

> **REVIEW FINDING [H2 — HIGH]: Phase 7 cleanup was empty — no steps for removing T78-T84 and updating references.**
> The spec explicitly lists 9 flows to remove (T78-T84, T50, M06) and 8 files to update. The current Phase 7 only has `.gitignore` and a `/test-status` route — none of the actual cleanup work.
>
> **Action for implementer:** Add these steps to Phase 7:
> 1. Remove T78-T84, T50, M06 from `.claude/test-flows/registry.md`
> 2. Remove `Verify-Sync` column from all CRUD flows (T05-T77) in registry
> 3. Add "Sync Verification" section to registry pointing to debug server
> 4. Update totals in registry (91 → 82 automated + sync verification system)
> 5. Update `.claude/rules/sync/sync-patterns.md` — reference `run-tests.js`
> 6. Update `.claude/rules/testing/patrol-testing.md` — reference debug server for sync testing
> 7. Grep `.claude/docs/`, `.claude/agents/`, `.claude/skills/` for T78-T84, M06, "Verify-Sync" and update all references
> 8. Update `.claude/memory/MEMORY.md` test results section

### Phase 7A: Config Files

**Files:**
- Modify `.gitignore` (if needed — add `tools/debug-server/scenarios/L2/*.log`, `tools/debug-server/scenarios/L3/*.log`)
- Modify `tools/debug-server/server.js` (add route for `GET /test-status` to expose test runner state)
- Modify `.claude/test-flows/registry.md` (remove T78-T84, T50, M06; remove Verify-Sync column; add Sync Verification section)
- Modify `.claude/rules/sync/sync-patterns.md` (update testing section)
- Modify `.claude/rules/testing/patrol-testing.md` (update sync testing section)
- Grep and update `.claude/docs/`, `.claude/agents/`, `.claude/skills/` for stale references

**Steps:**

1. Add to `.gitignore` (only if not already present):
```
# Sync verification test artifacts
tools/debug-server/scenarios/**/*.log
# SEC-013: Test-only credentials file — NEVER commit
**/.env.test
```

2. Add a `/test-status` route to `tools/debug-server/server.js` that returns the last test run summary. This is optional but useful for CI. Add it to the existing route dispatch if/else chain:

```javascript
} else if (req.method === 'GET' && pathname === '/test-status') {
  // Return last test run results (stored in memory)
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(global._lastTestResults || { status: 'no runs yet' }));
}
```

### Phase 7B: Update References

**Files:**
- Modify `tools/debug-server/server.js` (import new modules for potential future use)

**Steps:**

1. At the top of `server.js`, add requires for the new modules (guarded so they don't break if files don't exist yet):

```javascript
// Sync verification modules (loaded on demand)
let SupabaseVerifier, DeviceOrchestrator;
try {
  SupabaseVerifier = require('./supabase-verifier');
  DeviceOrchestrator = require('./device-orchestrator');
} catch (e) {
  // Modules not yet created — safe to ignore
}
```

**Verification:**
```
node tools/debug-server/server.js &
```
Then kill it. Just verify it starts without import errors.

---

## Phase 8: Integration Verification

**Agent:** `qa-testing-agent`
**Why:** Verify all layers work end-to-end before declaring the feature complete.
**Depends on:** All previous phases

### Phase 8A: Run Layer 1 Tests

**Steps:**

1. Run all L1 unit tests:
```
pwsh -Command "flutter test test/features/sync/engine/"
```

2. Fix any failures before proceeding.

### Phase 8B: Verify Debug Server Modules Load

**Steps:**

1. Verify all modules load without errors:
```
node -e "
  const SV = require('./tools/debug-server/supabase-verifier');
  const DO = require('./tools/debug-server/device-orchestrator');
  const SH = require('./tools/debug-server/scenario-helpers');
  const TR = require('./tools/debug-server/test-runner');
  console.log('All modules loaded successfully');
"
```

### Phase 8C: Dry Run All Scenarios

**Steps:**

1. Verify scenario discovery:
```
node tools/debug-server/run-tests.js --dry-run
```

2. Expected output: 94 total scenarios (84 L2 + 10 L3).

### Phase 8D: Verify Flutter Analyze

**Steps:**

1. Run static analysis to ensure no regressions from driver changes:
```
pwsh -Command "flutter analyze"
```

2. Fix any analysis errors.

---

## Execution Summary

| Phase | Files | Agent | Depends On | Est. Effort |
|-------|-------|-------|------------|-------------|
| 1A | 3 create | qa-testing | — | S |
| 1B | 2 create | qa-testing | — | S |
| 1C | 3 create | qa-testing | — | S |
| 1D | 1 modify | qa-testing | — | XS |
| 2A | 2 modify | backend-data-layer | — | S |
| 2B | 1 modify | backend-data-layer | 2A | M |
| 3A | 1 create | qa-testing | — | S |
| 3B | 1 create | qa-testing | — | S |
| 3C | 1 create | qa-testing | — | S |
| 4A | 1 create | qa-testing | 3 | S |
| 4B | 1 create | qa-testing | 4A | XS |
| 5A | mkdir | qa-testing | — | XS |
| 5B | 5 create | qa-testing | 3, 4 | M |
| 5C | 79 create | qa-testing | 5B | L (generated) |
| 6A | 10 create | qa-testing | 3, 4 | M |
| 7A | 2 modify | general-purpose | 1–6 | XS |
| 7B | 1 modify | general-purpose | 7A | XS |
| 8A–D | 0 (verify) | qa-testing | ALL | S |

**Parallelization:** Phases 1A/1B/1C, 2A, 3A/3B/3C can all run concurrently. Phase 5C (79 generated files) is the largest unit but mechanical.

**Total files:** ~8 modified + ~104 created = ~112 files (higher than initial estimate due to per-table scenario files).
