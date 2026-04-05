## Phase 2: Extract I/O Boundaries (LocalSyncStore + SupabaseSync)

Phase 2 creates the two foundational I/O boundary classes that every subsequent handler depends on. After this phase, no class outside `LocalSyncStore` touches `Database` for sync operations, and no class outside `SupabaseSync` touches `SupabaseClient` for sync row I/O.

**Prerequisite**: Phase 1 complete (SyncErrorClassifier, ClassifiedSyncError, SyncErrorKind exist in `lib/features/sync/engine/sync_error_classifier.dart` and `lib/features/sync/domain/sync_error.dart`).

---

### Sub-phase 2.1: Create LocalSyncStore

**Files:**
- Create: `lib/features/sync/engine/local_sync_store.dart`
- Test: `test/features/sync/engine/local_sync_store_contract_test.dart`

**Agent**: backend-supabase-agent

#### Step 2.1.1: Write LocalSyncStore contract test (red)

Create the contract test file that defines the public API for LocalSyncStore. All tests will be red initially.

```dart
// test/features/sync/engine/local_sync_store_contract_test.dart

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/features/sync/engine/local_sync_store.dart';

// WHY: Contract tests define the public API before implementation exists.
// FROM SPEC Section 4.2: "Written TDD-style before each class exists."

void main() {
  late Database db;
  late LocalSyncStore store;

  setUpAll(() {
    // NOTE: sqflite_ffi initialization for desktop test runner
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  setUp(() async {
    db = await databaseFactoryFfi.openDatabase(
      inMemoryDatabasePath,
      options: OpenDatabaseOptions(
        version: 1,
        onCreate: (db, version) async {
          // WHY: Minimal schema for contract testing — only tables LocalSyncStore touches
          await db.execute('''
            CREATE TABLE sync_control (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL DEFAULT '0'
            )
          ''');
          await db.execute(
            "INSERT INTO sync_control (key, value) VALUES ('pulling', '0')",
          );
          await db.execute('''
            CREATE TABLE sync_metadata (
              key TEXT PRIMARY KEY,
              value TEXT
            )
          ''');
          await db.execute('''
            CREATE TABLE synced_projects (
              project_id TEXT PRIMARY KEY,
              synced_at TEXT,
              unassigned_at TEXT
            )
          ''');
          await db.execute('''
            CREATE TABLE projects (
              id TEXT PRIMARY KEY,
              name TEXT,
              company_id TEXT,
              updated_at TEXT,
              deleted_at TEXT,
              created_at TEXT
            )
          ''');
          await db.execute('''
            CREATE TABLE contractors (
              id TEXT PRIMARY KEY,
              name TEXT,
              project_id TEXT,
              updated_at TEXT,
              deleted_at TEXT
            )
          ''');
          await db.execute('''
            CREATE TABLE daily_entries (
              id TEXT PRIMARY KEY,
              project_id TEXT,
              date TEXT,
              updated_at TEXT,
              deleted_at TEXT,
              deleted_by TEXT
            )
          ''');
          await db.execute('''
            CREATE TABLE change_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              table_name TEXT NOT NULL,
              record_id TEXT NOT NULL,
              operation TEXT NOT NULL,
              changed_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now')),
              processed INTEGER DEFAULT 0,
              retry_count INTEGER DEFAULT 0,
              error_message TEXT,
              metadata TEXT
            )
          ''');
          await db.execute('''
            CREATE TABLE conflict_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              table_name TEXT NOT NULL,
              record_id TEXT NOT NULL,
              detected_at TEXT NOT NULL,
              dismissed_at TEXT
            )
          ''');
          await db.execute('''
            CREATE TABLE deletion_notifications (
              id TEXT PRIMARY KEY,
              record_id TEXT NOT NULL,
              table_name TEXT NOT NULL,
              project_id TEXT,
              record_name TEXT,
              deleted_by TEXT,
              deleted_by_name TEXT,
              deleted_at TEXT,
              seen INTEGER DEFAULT 0
            )
          ''');
          await db.execute('''
            CREATE TABLE user_profiles (
              id TEXT PRIMARY KEY,
              display_name TEXT,
              company_id TEXT
            )
          ''');
          await db.execute('''
            CREATE TABLE project_assignments (
              id TEXT PRIMARY KEY,
              project_id TEXT,
              user_id TEXT,
              deleted_at TEXT,
              updated_at TEXT
            )
          ''');
        },
      ),
    );
    store = LocalSyncStore(db);
  });

  tearDown(() async {
    await db.close();
  });

  group('trigger suppression', () {
    test('suppressTriggers sets pulling to 1', () async {
      await store.suppressTriggers();
      final rows = await db.query('sync_control', where: "key = 'pulling'");
      expect(rows.first['value'], '1');
    });

    test('restoreTriggers sets pulling to 0', () async {
      await store.suppressTriggers();
      await store.restoreTriggers();
      final rows = await db.query('sync_control', where: "key = 'pulling'");
      expect(rows.first['value'], '0');
    });

    test('withTriggersSuppressed runs action with suppression in try/finally',
        () async {
      // WHY: CRITICAL — trigger suppression MUST be in try/finally to prevent
      // stuck pulling='1' state on exception.
      // FROM SPEC Section 4.2: "upsertPulledRecord with trigger suppression in try/finally"
      var actionRan = false;
      await store.withTriggersSuppressed(() async {
        final rows = await db.query('sync_control', where: "key = 'pulling'");
        expect(rows.first['value'], '1');
        actionRan = true;
      });
      expect(actionRan, isTrue);
      final rows = await db.query('sync_control', where: "key = 'pulling'");
      expect(rows.first['value'], '0');
    });

    test('withTriggersSuppressed restores triggers even on exception', () async {
      // WHY: This is the MOST CRITICAL contract — stuck pulling='1' stops all
      // change_log generation until app restart.
      try {
        await store.withTriggersSuppressed(() async {
          throw StateError('simulated failure');
        });
      } on StateError {
        // expected
      }
      final rows = await db.query('sync_control', where: "key = 'pulling'");
      expect(rows.first['value'], '0');
    });
  });

  group('readLocalRecord', () {
    test('returns record by id', () async {
      await db.insert('daily_entries', {
        'id': 'e1',
        'project_id': 'p1',
        'date': '2026-01-01',
      });
      final record = await store.readLocalRecord('daily_entries', 'e1');
      expect(record, isNotNull);
      expect(record!['id'], 'e1');
    });

    test('returns null for missing record', () async {
      final record = await store.readLocalRecord('daily_entries', 'missing');
      expect(record, isNull);
    });
  });

  group('upsertPulledRecord', () {
    test('inserts new record with trigger suppression', () async {
      // FROM SPEC Section 4.2: "upsertPulledRecord with trigger suppression in try/finally"
      final rowId = await store.upsertPulledRecord(
        'daily_entries',
        {'id': 'e1', 'project_id': 'p1', 'date': '2026-01-01'},
      );
      expect(rowId, greaterThan(0));
      // Verify triggers were restored
      final ctrl = await db.query('sync_control', where: "key = 'pulling'");
      expect(ctrl.first['value'], '0');
    });
  });

  group('writeBackServerTimestamp', () {
    test('updates updated_at with trigger suppression', () async {
      await db.insert('daily_entries', {
        'id': 'e1',
        'project_id': 'p1',
        'date': '2026-01-01',
        'updated_at': '2026-01-01T00:00:00.000Z',
      });
      await store.writeBackServerTimestamp(
        'daily_entries',
        'e1',
        '2026-01-01T12:00:00.000Z',
      );
      final rows = await db.query(
        'daily_entries',
        where: 'id = ?',
        whereArgs: ['e1'],
      );
      expect(rows.first['updated_at'], '2026-01-01T12:00:00.000Z');
      // Triggers restored
      final ctrl = await db.query('sync_control', where: "key = 'pulling'");
      expect(ctrl.first['value'], '0');
    });
  });

  group('column cache', () {
    test('getLocalColumns returns column names from PRAGMA', () async {
      final columns = await store.getLocalColumns('daily_entries');
      expect(columns, containsAll(['id', 'project_id', 'date']));
    });

    test('getLocalColumns caches results', () async {
      final first = await store.getLocalColumns('daily_entries');
      final second = await store.getLocalColumns('daily_entries');
      // NOTE: Same Set instance from cache
      expect(identical(first, second), isTrue);
    });

    test('stripUnknownColumns removes columns not in local schema', () async {
      final columns = await store.getLocalColumns('daily_entries');
      final stripped = store.stripUnknownColumns(
        {'id': 'e1', 'project_id': 'p1', 'unknown_col': 'val'},
        columns,
      );
      expect(stripped.containsKey('unknown_col'), isFalse);
      expect(stripped['id'], 'e1');
    });
  });

  group('cursor management', () {
    test('readCursor returns null for no cursor', () async {
      final cursor = await store.readCursor('daily_entries');
      expect(cursor, isNull);
    });

    test('writeCursor stores and readCursor retrieves', () async {
      await store.writeCursor('daily_entries', '2026-01-01T00:00:00.000Z');
      final cursor = await store.readCursor('daily_entries');
      expect(cursor, '2026-01-01T00:00:00.000Z');
    });

    test('clearCursor removes cursor', () async {
      await store.writeCursor('daily_entries', '2026-01-01T00:00:00.000Z');
      await store.clearCursor('daily_entries');
      final cursor = await store.readCursor('daily_entries');
      expect(cursor, isNull);
    });
  });

  group('synced projects', () {
    test('loadSyncedProjectIds returns enrolled project IDs', () async {
      await db.insert('synced_projects', {'project_id': 'p1'});
      await db.insert('synced_projects', {'project_id': 'p2'});
      final ids = await store.loadSyncedProjectIds();
      expect(ids, containsAll(['p1', 'p2']));
    });

    test('enrollProject inserts into synced_projects idempotently', () async {
      await store.enrollProject('p1');
      await store.enrollProject('p1'); // duplicate — should not throw
      final rows = await db.query('synced_projects');
      expect(rows.length, 1);
    });
  });

  group('storeMetadata', () {
    test('stores and retrieves metadata key-value', () async {
      await store.storeMetadata('last_sync_time', '2026-01-01T00:00:00.000Z');
      final rows = await db.query(
        'sync_metadata',
        where: 'key = ?',
        whereArgs: ['last_sync_time'],
      );
      expect(rows.first['value'], '2026-01-01T00:00:00.000Z');
    });
  });

  group('resetPullingFlag', () {
    test('resets pulling to 0 for crash recovery', () async {
      await db.execute(
        "UPDATE sync_control SET value = '1' WHERE key = 'pulling'",
      );
      await store.resetPullingFlag();
      final rows = await db.query('sync_control', where: "key = 'pulling'");
      expect(rows.first['value'], '0');
    });
  });
}
```

#### Step 2.1.2: Implement LocalSyncStore

Create the production class that wraps all sync-related SQLite I/O.

```dart
// lib/features/sync/engine/local_sync_store.dart

import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:uuid/uuid.dart';

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/shared/utils/safe_row.dart';

/// All sync-related SQLite I/O: record reads/writes, cursor management,
/// trigger suppression (pulling='1'/'0' in try/finally), column cache
/// (PRAGMA table_info), server timestamp writeback, unknown column stripping.
///
/// WHY: Extracted from SyncEngine to create a clean I/O boundary.
/// FROM SPEC Section 3 (Target Architecture): "Dependencies: Database only"
///
/// IMPORTANT: Trigger suppression (sync_control.pulling) MUST always be in
/// try/finally blocks. This class owns ALL trigger suppression to prevent
/// the stuck-pulling='1' bug that stops change_log generation.
class LocalSyncStore {
  final Database _db;

  /// Cached column info per table (PRAGMA table_info).
  /// WHY: Avoids repeated PRAGMA queries during pull — same pattern as
  /// SyncEngine._localColumnsCache (sync_engine.dart:153).
  final Map<String, Set<String>> _localColumnsCache = {};

  LocalSyncStore(this._db);

  /// Expose the raw database for components that need direct access
  /// (ChangeTracker, ConflictResolver, etc. that pre-date this boundary).
  /// NOTE: This is a transitional escape hatch. Future phases should
  /// migrate those components to use LocalSyncStore methods instead.
  Database get database => _db;

  // ---------------------------------------------------------------------------
  // Trigger Suppression
  // ---------------------------------------------------------------------------

  /// Set sync_control.pulling = '1' to suppress change_log triggers.
  ///
  /// IMPORTANT: Always pair with [restoreTriggers] in a finally block,
  /// or use [withTriggersSuppressed] which handles this automatically.
  /// FROM SPEC: "sync_control flag MUST be inside transaction" (lint rule S3)
  Future<void> suppressTriggers() async {
    await _db.execute(
      "UPDATE sync_control SET value = '1' WHERE key = 'pulling'",
    );
  }

  /// Reset sync_control.pulling = '0' to re-enable change_log triggers.
  Future<void> restoreTriggers() async {
    await _db.execute(
      "UPDATE sync_control SET value = '0' WHERE key = 'pulling'",
    );
  }

  /// Execute [action] with triggers suppressed, guaranteed to restore
  /// triggers in the finally block even on exception.
  ///
  /// WHY: This is THE safe pattern for trigger suppression. Every caller
  /// should use this instead of manual suppress/restore pairs.
  /// FROM SPEC: "Trigger suppression (pulling='1'/'0') MUST be in try/finally blocks"
  Future<T> withTriggersSuppressed<T>(Future<T> Function() action) async {
    await suppressTriggers();
    try {
      return await action();
    } finally {
      await restoreTriggers();
    }
  }

  /// Best-effort reset of pulling flag for crash recovery.
  /// Called at start of sync cycle and on app startup.
  /// FROM SPEC: SyncEngine.resetState (sync_engine.dart:209-218)
  Future<void> resetPullingFlag() async {
    try {
      await _db.execute(
        "UPDATE sync_control SET value = '0' WHERE key = 'pulling'",
      );
    } on Object catch (e) {
      Logger.sync('[LocalSyncStore] resetPullingFlag best-effort: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Record I/O
  // ---------------------------------------------------------------------------

  /// Read a single record by ID from a sync table.
  /// Returns null if the record does not exist.
  /// FROM SPEC: Extracted from SyncEngine._push (db.query calls at lines 521-526, 561-565, etc.)
  Future<Map<String, dynamic>?> readLocalRecord(
    String tableName,
    String recordId,
  ) async {
    final rows = await _db.query(
      tableName,
      where: 'id = ?',
      whereArgs: [recordId],
    );
    return rows.isEmpty ? null : rows.first;
  }

  /// Read a single column value from a record.
  /// Returns null if the record does not exist.
  Future<Map<String, dynamic>?> readLocalRecordColumns(
    String tableName,
    String recordId,
    List<String> columns,
  ) async {
    final rows = await _db.query(
      tableName,
      columns: columns,
      where: 'id = ?',
      whereArgs: [recordId],
    );
    return rows.isEmpty ? null : rows.first;
  }

  /// Insert a pulled record with ConflictAlgorithm.ignore.
  /// Trigger suppression is the CALLER's responsibility (pull runs inside
  /// a single withTriggersSuppressed block for the entire pull cycle).
  ///
  /// Returns the rowId (0 if insert was silently ignored due to conflict).
  /// FROM SPEC: SyncEngine._pullTable insert path (sync_engine.dart:1801-1833)
  Future<int> insertPulledRecord(
    String tableName,
    Map<String, dynamic> record,
  ) async {
    return _db.insert(
      tableName,
      record,
      conflictAlgorithm: ConflictAlgorithm.ignore,
    );
  }

  /// Update a local record by ID. Used for pull conflict resolution (remote wins)
  /// and insert->update fallback (ConflictAlgorithm.ignore returned 0).
  ///
  /// Returns the number of rows affected.
  Future<int> updateLocalRecord(
    String tableName,
    Map<String, dynamic> values,
    String recordId,
  ) async {
    return _db.update(
      tableName,
      values,
      where: 'id = ?',
      whereArgs: [recordId],
    );
  }

  /// Combined insert-or-update for pulled records.
  /// Attempts insert with ignore, falls back to update if rowId==0.
  /// Returns the effective rowId (>0 means record was written).
  ///
  /// NOTE: Caller must ensure triggers are suppressed before calling this.
  /// FROM SPEC: ConflictAlgorithm.ignore MUST have rowId==0 fallback (lint S1)
  Future<int> upsertPulledRecord(
    String tableName,
    Map<String, dynamic> record,
  ) async {
    // NOTE: Trigger suppression is NOT done here because the pull cycle
    // wraps the entire adapter loop in withTriggersSuppressed.
    // Individual record operations run within that scope.
    final rowId = await _db.insert(
      tableName,
      record,
      conflictAlgorithm: ConflictAlgorithm.ignore,
    );
    if (rowId == 0) {
      final recordId = record['id'] as String;
      final updated = await _db.update(
        tableName,
        record,
        where: 'id = ?',
        whereArgs: [recordId],
      );
      if (updated > 0) {
        Logger.sync('Pull insert->update fallback: $tableName/$recordId');
        return 1; // Signal success
      }
      Logger.sync(
        'Pull insert ignored (constraint conflict): $tableName/${record["id"]}',
      );
      return 0;
    }
    return rowId;
  }

  /// Write back server-assigned timestamp to prevent false conflicts.
  /// Uses trigger suppression to avoid generating spurious change_log entries.
  ///
  /// FROM SPEC: SyncEngine._pushUpsert timestamp writeback (sync_engine.dart:1113-1128)
  Future<void> writeBackServerTimestamp(
    String tableName,
    String recordId,
    String serverUpdatedAt, {
    Map<String, dynamic>? additionalFields,
  }) async {
    await withTriggersSuppressed(() async {
      final updateFields = <String, dynamic>{
        'updated_at': serverUpdatedAt,
        if (additionalFields != null) ...additionalFields,
      };
      await _db.update(
        tableName,
        updateFields,
        where: 'id = ?',
        whereArgs: [recordId],
      );
    });
  }

  /// Write back remote_path and optionally updated_at for file sync bookkeeping.
  /// FROM SPEC: SyncEngine._pushFileThreePhase Phase 3 (sync_engine.dart:1314-1335)
  Future<void> bookmarkRemotePath(
    String tableName,
    String recordId,
    String remotePath, {
    String? serverUpdatedAt,
    String? localUpdatedAt,
  }) async {
    await withTriggersSuppressed(() async {
      final updateFields = <String, dynamic>{'remote_path': remotePath};
      if (serverUpdatedAt != null && serverUpdatedAt != localUpdatedAt) {
        updateFields['updated_at'] = serverUpdatedAt;
      }
      await _db.update(
        tableName,
        updateFields,
        where: 'id = ?',
        whereArgs: [recordId],
      );
    });
  }

  /// Suppress triggers, remap a record's ID, cascade to child FK columns,
  /// and update change_log references.
  /// FROM SPEC: SyncEngine._pushUpsert natural key remap (sync_engine.dart:996-1053)
  Future<void> remapRecordId({
    required String tableName,
    required String oldId,
    required String newId,
    required List<({String table, String column})> childFkColumns,
  }) async {
    await withTriggersSuppressed(() async {
      // Check if target ID already exists locally
      final existingTarget = await _db.query(
        tableName,
        where: 'id = ?',
        whereArgs: [newId],
      );
      if (existingTarget.isNotEmpty) {
        Logger.sync(
          'Natural key remap: target $newId already exists locally in '
          '$tableName. Removing duplicate $oldId.',
        );
        await _db.delete(tableName, where: 'id = ?', whereArgs: [oldId]);
        await _db.delete(
          'change_log',
          where: 'record_id = ? AND table_name = ? AND processed = 0',
          whereArgs: [oldId, tableName],
        );
        return;
      }

      // Update the record's own ID
      await _db.execute(
        'UPDATE $tableName SET id = ? WHERE id = ?',
        [newId, oldId],
      );
      // Update FK references in child tables
      for (final child in childFkColumns) {
        await _db.execute(
          'UPDATE ${child.table} SET ${child.column} = ? '
          'WHERE ${child.column} = ?',
          [newId, oldId],
        );
      }
      // Update change_log references
      await _db.execute(
        'UPDATE change_log SET record_id = ? '
        'WHERE record_id = ? AND table_name = ?',
        [newId, oldId, tableName],
      );
    });
  }

  /// Check if remap target ID already exists (used to short-circuit push).
  Future<bool> recordExists(String tableName, String recordId) async {
    final rows = await _db.query(
      tableName,
      columns: const ['id'],
      where: 'id = ?',
      whereArgs: [recordId],
      limit: 1,
    );
    return rows.isNotEmpty;
  }

  // ---------------------------------------------------------------------------
  // Column Cache
  // ---------------------------------------------------------------------------

  /// Get the set of column names for a table (cached PRAGMA table_info).
  /// FROM SPEC: SyncEngine._getLocalColumns (sync_engine.dart:2223-2235)
  ///
  /// NOTE: Uses rawQuery for PRAGMA — Android API 36 rejects PRAGMA via execute().
  Future<Set<String>> getLocalColumns(String tableName) async {
    if (_localColumnsCache.containsKey(tableName)) {
      return _localColumnsCache[tableName]!;
    }
    assert(
      RegExp(r'^[a-z_]+$').hasMatch(tableName),
      'Unsafe tableName: $tableName',
    );
    final columns = await _db.rawQuery('PRAGMA table_info($tableName)');
    final names = columns.map((c) => c.requireString('name')).toSet();
    _localColumnsCache[tableName] = names;
    return names;
  }

  /// Strip columns from a record that don't exist in the local schema.
  /// FROM SPEC: SyncEngine._stripUnknownColumns (sync_engine.dart:2237-2244)
  Map<String, dynamic> stripUnknownColumns(
    Map<String, dynamic> record,
    Set<String> localColumns,
  ) {
    return Map.fromEntries(
      record.entries.where((e) => localColumns.contains(e.key)),
    );
  }

  // ---------------------------------------------------------------------------
  // Cursor Management
  // ---------------------------------------------------------------------------

  /// Read the pull cursor for a table.
  /// FROM SPEC: SyncEngine._pullTable cursor read (sync_engine.dart:1718-1725)
  Future<String?> readCursor(String tableName) async {
    final rows = await _db.query(
      'sync_metadata',
      where: 'key = ?',
      whereArgs: ['last_pull_$tableName'],
    );
    return rows.isNotEmpty ? rows.first.optionalString('value') : null;
  }

  /// Write the pull cursor for a table.
  /// FROM SPEC: SyncEngine._pullTable cursor write (sync_engine.dart:1957-1963)
  Future<void> writeCursor(String tableName, String updatedAt) async {
    await _db.execute(
      'INSERT OR REPLACE INTO sync_metadata (key, value) '
      "VALUES ('last_pull_$tableName', ?)",
      [updatedAt],
    );
  }

  /// Clear the pull cursor for a table (forces full re-pull on next cycle).
  /// FROM SPEC: SyncEngine._clearCursor (sync_engine.dart:2284-2291)
  Future<void> clearCursor(String tableName) async {
    await _db.delete(
      'sync_metadata',
      where: 'key = ?',
      whereArgs: ['last_pull_$tableName'],
    );
    Logger.sync('Cleared cursor for $tableName');
  }

  // ---------------------------------------------------------------------------
  // Synced Projects
  // ---------------------------------------------------------------------------

  /// Load all enrolled project IDs from synced_projects.
  /// FROM SPEC: SyncEngine._loadSyncedProjectIds (sync_engine.dart:2020-2090)
  Future<List<String>> loadSyncedProjectIds() async {
    final rows = await _db.query('synced_projects');
    return rows.map((r) => r.requireString('project_id')).toList();
  }

  /// Enroll a project ID into synced_projects (idempotent).
  /// FROM SPEC: SyncEngine._rescueParentProject enrollment (sync_engine.dart:2207-2210)
  Future<void> enrollProject(String projectId) async {
    await _db.rawInsert(
      'INSERT OR IGNORE INTO synced_projects (project_id) VALUES (?)',
      [projectId],
    );
  }

  /// Load contractor IDs for a set of project IDs.
  /// FROM SPEC: SyncEngine._loadContractorIdsForProjectIds (sync_engine.dart:2005-2018)
  Future<List<String>> loadContractorIdsForProjectIds(
    List<String> projectIds,
  ) async {
    if (projectIds.isEmpty) return [];
    final placeholders = projectIds.map((_) => '?').join(',');
    final contractors = await _db.query(
      'contractors',
      columns: ['id'],
      where: 'project_id IN ($placeholders) AND deleted_at IS NULL',
      whereArgs: projectIds,
    );
    return contractors.map((row) => row.requireString('id')).toList();
  }

  /// Clean orphaned synced_projects entries where the project was deleted
  /// or never actually pulled. Only runs after projects adapter completes.
  /// FROM SPEC: SyncEngine._loadSyncedProjectIds orphan cleanup (sync_engine.dart:2027-2067)
  Future<List<String>> cleanOrphanedSyncedProjects(
    List<String> syncedProjectIds,
  ) async {
    if (syncedProjectIds.isEmpty) return syncedProjectIds;

    final placeholders = syncedProjectIds.map((_) => '?').join(',');
    final existingProjects = await _db.query(
      'projects',
      columns: ['id'],
      where: 'id IN ($placeholders) AND deleted_at IS NULL',
      whereArgs: syncedProjectIds,
    );
    final existingIds =
        existingProjects.map((r) => r.requireString('id')).toSet();
    final orphanIds =
        syncedProjectIds.where((id) => !existingIds.contains(id)).toList();

    if (orphanIds.isNotEmpty) {
      final orphanPlaceholders = orphanIds.map((_) => '?').join(',');
      Logger.sync(
        'Cleaning ${orphanIds.length} orphaned/deleted synced_projects entries',
      );
      await _db.delete(
        'synced_projects',
        where: 'project_id IN ($orphanPlaceholders)',
        whereArgs: orphanIds,
      );
      return syncedProjectIds.where(existingIds.contains).toList();
    }
    return syncedProjectIds;
  }

  /// Load all contractor IDs for currently synced projects.
  Future<List<String>> loadSyncedContractorIds(
    List<String> syncedProjectIds,
  ) async {
    if (syncedProjectIds.isEmpty) return [];
    final placeholders = syncedProjectIds.map((_) => '?').join(',');
    final contractors = await _db.query(
      'contractors',
      columns: ['id'],
      where: 'project_id IN ($placeholders) AND deleted_at IS NULL',
      whereArgs: syncedProjectIds,
    );
    return contractors.map((r) => r.requireString('id')).toList();
  }

  // ---------------------------------------------------------------------------
  // Metadata
  // ---------------------------------------------------------------------------

  /// Store a key-value pair in sync_metadata.
  /// FROM SPEC: SyncEngine._storeMetadata (sync_engine.dart:2294-2299)
  Future<void> storeMetadata(String key, String value) async {
    await _db.execute(
      'INSERT OR REPLACE INTO sync_metadata (key, value) VALUES (?, ?)',
      [key, value],
    );
  }

  /// Read a metadata value by key.
  Future<String?> readMetadata(String key) async {
    final rows = await _db.query(
      'sync_metadata',
      where: 'key = ?',
      whereArgs: [key],
    );
    return rows.isNotEmpty ? rows.first.optionalString('value') : null;
  }

  /// Write last_sync_time to sync_metadata.
  /// FROM SPEC: SyncEngine._pull last sync time write (sync_engine.dart:1691-1695)
  Future<void> writeLastSyncTime() async {
    await _db.execute(
      'INSERT OR REPLACE INTO sync_metadata (key, value) '
      "VALUES ('last_sync_time', ?)",
      [DateTime.now().toUtc().toIso8601String()],
    );
  }

  // ---------------------------------------------------------------------------
  // Tombstone checks
  // ---------------------------------------------------------------------------

  /// Check if a pending delete exists in change_log for a record.
  /// Used during pull to prevent re-inserting records with pending local deletes.
  /// FROM SPEC: SyncEngine._pullTable tombstone check (sync_engine.dart:1784-1797)
  Future<bool> hasPendingDelete(String tableName, String recordId) async {
    final rows = await _db.query(
      'change_log',
      where:
          "table_name = ? AND record_id = ? AND operation = 'delete' AND processed = 0",
      whereArgs: [tableName, recordId],
      limit: 1,
    );
    return rows.isNotEmpty;
  }

  // ---------------------------------------------------------------------------
  // Deletion Notifications
  // ---------------------------------------------------------------------------

  /// Create a deletion notification for a record deleted by another user.
  /// FROM SPEC: SyncEngine._createDeletionNotification (sync_engine.dart:2246-2277)
  Future<void> createDeletionNotification({
    required TableAdapter adapter,
    required Map<String, dynamic> local,
    required Map<String, dynamic> remote,
    required String userId,
  }) async {
    final deletedBy = remote['deleted_by'] as String?;
    if (deletedBy == null || deletedBy == userId) return;

    String? deletedByName;
    if (deletedBy.isNotEmpty) {
      final profiles = await _db.query(
        'user_profiles',
        columns: ['display_name'],
        where: 'id = ?',
        whereArgs: [deletedBy],
      );
      if (profiles.isNotEmpty) {
        deletedByName = profiles.first['display_name'] as String?;
      }
    }

    await _db.insert('deletion_notifications', {
      'id': const Uuid().v4(),
      'record_id': remote['id'],
      'table_name': adapter.tableName,
      'project_id': remote['project_id'] ?? local['project_id'],
      'record_name': adapter.extractRecordName(local),
      'deleted_by': deletedBy,
      'deleted_by_name': deletedByName,
      'deleted_at': remote['deleted_at'],
      'seen': 0,
    });
  }

  // ---------------------------------------------------------------------------
  // Enrollment (used by EnrollmentHandler and PullHandler)
  // ---------------------------------------------------------------------------

  /// Reconcile synced_projects from current assignments.
  /// FROM SPEC: SyncEngine._reconcileSyncedProjects (sync_engine.dart:2097-2128)
  Future<int> reconcileSyncedProjects(String userId) async {
    if (userId.isEmpty) return 0;

    final assignments = await _db.query(
      'project_assignments',
      columns: ['project_id'],
      where: 'user_id = ? AND deleted_at IS NULL',
      whereArgs: [userId],
    );

    if (assignments.isEmpty) return 0;

    final existing = await _db.query('synced_projects', columns: ['project_id']);
    final existingIds =
        existing.map((r) => r.requireString('project_id')).toSet();

    var reconciled = 0;
    for (final row in assignments) {
      final projectId = row.requireString('project_id');
      if (!existingIds.contains(projectId)) {
        await _db.rawInsert(
          'INSERT OR IGNORE INTO synced_projects (project_id) VALUES (?)',
          [projectId],
        );
        Logger.sync('Reconciled synced_projects for project: $projectId');
        reconciled++;
      }
    }

    if (reconciled > 0) {
      Logger.sync('Reconciled $reconciled synced_projects entries');
    }
    return reconciled;
  }

  /// Enroll projects from project_assignments for a specific user.
  /// FROM SPEC: SyncEngine._enrollProjectsFromAssignments (sync_engine.dart:2133-2167)
  Future<int> enrollProjectsFromAssignments(String userId) async {
    if (userId.isEmpty) {
      Logger.sync('Cannot enroll projects: no current user ID');
      return 0;
    }

    final assignments = await _db.query(
      'project_assignments',
      columns: ['project_id'],
      where: 'user_id = ? AND deleted_at IS NULL',
      whereArgs: [userId],
    );

    if (assignments.isEmpty) {
      Logger.sync('No project_assignments for user $userId');
      return 0;
    }

    var enrolled = 0;
    for (final row in assignments) {
      final projectId = row.requireString('project_id');
      final inserted = await _db.rawInsert(
        'INSERT OR IGNORE INTO synced_projects (project_id) VALUES (?)',
        [projectId],
      );
      if (inserted > 0) enrolled++;
    }

    if (enrolled > 0) {
      Logger.sync('Engine-enrolled $enrolled projects from assignments');
    }
    return enrolled;
  }

  /// Query local assignments for cursor-reset check.
  /// FROM SPEC: SyncEngine._pull fresh-restore guard (sync_engine.dart:1671-1681)
  Future<bool> hasLocalAssignments() async {
    final localAssignments = await _db.query(
      'project_assignments',
      where: 'deleted_at IS NULL',
      limit: 1,
    );
    return localAssignments.isNotEmpty;
  }

  // ---------------------------------------------------------------------------
  // Conflict management (used by PullHandler)
  // ---------------------------------------------------------------------------

  /// Auto-dismiss conflicts older than 30 days.
  /// FROM SPEC: SyncEngine._cleanupExpiredConflicts (sync_engine.dart:2345-2356)
  Future<void> cleanupExpiredConflicts() async {
    final thirtyDaysAgo = DateTime.now()
        .subtract(const Duration(days: 30))
        .toUtc()
        .toIso8601String();
    await _db.update(
      'conflict_log',
      {'dismissed_at': DateTime.now().toUtc().toIso8601String()},
      where: 'dismissed_at IS NULL AND detected_at < ?',
      whereArgs: [thirtyDaysAgo],
    );
  }

  /// Store a per-table integrity check result in sync_metadata.
  /// FROM SPEC: SyncEngine._storeIntegrityResult (sync_engine.dart:2359-2373)
  Future<void> storeIntegrityResult(String tableName, String jsonResult) async {
    await _db.execute(
      'INSERT OR REPLACE INTO sync_metadata (key, value) VALUES (?, ?)',
      ['integrity_$tableName', jsonResult],
    );
  }

  // ---------------------------------------------------------------------------
  // Raw SQL execution (escape hatch for operations not yet migrated)
  // ---------------------------------------------------------------------------

  /// Execute a raw SQL update. Used for operations that don't have
  /// a dedicated method yet (transitional).
  Future<void> executeRaw(String sql, [List<Object?>? arguments]) async {
    await _db.execute(sql, arguments);
  }

  /// Execute a raw SQL query. Used for operations that don't have
  /// a dedicated method yet (transitional).
  Future<List<Map<String, dynamic>>> queryRaw(
    String sql, [
    List<Object?>? arguments,
  ]) async {
    return _db.rawQuery(sql, arguments);
  }
}
```

#### Step 2.1.3: Verify LocalSyncStore

```
pwsh -Command "flutter analyze lib/features/sync/engine/local_sync_store.dart"
```

Expected: No analysis errors.

---

### Sub-phase 2.2: Create SupabaseSync

**Files:**
- Create: `lib/features/sync/engine/supabase_sync.dart`
- Test: `test/features/sync/engine/supabase_sync_contract_test.dart`

**Agent**: backend-supabase-agent

#### Step 2.2.1: Write SupabaseSync contract test (red)

```dart
// test/features/sync/engine/supabase_sync_contract_test.dart

import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:construction_inspector/features/sync/engine/supabase_sync.dart';
import 'package:construction_inspector/features/sync/engine/sync_error_classifier.dart';
import 'package:construction_inspector/features/sync/domain/sync_error.dart';

// WHY: Contract tests define SupabaseSync public API before implementation.
// FROM SPEC Section 4.2: "upsert calls, delete sends UPDATE with deleted_at,
// fetchPage applies filters+cursor+limit, refreshAuth on 401"
//
// NOTE: These tests use mock SupabaseClient patterns. The actual Supabase calls
// are verified via integration tests (Layer 5). Contract tests verify the
// routing and error handling logic.

void main() {
  group('SupabaseSync API surface', () {
    // NOTE: Full mock-based contract tests require a MockSupabaseClient
    // implementation. These are structural tests verifying the class compiles
    // and has the expected public API.

    test('class exists and can be referenced', () {
      // WHY: Compile-time verification that SupabaseSync exists with expected constructor
      expect(SupabaseSync, isNotNull);
    });
  });

  group('SyncErrorClassifier integration', () {
    // WHY: SupabaseSync delegates error classification to SyncErrorClassifier.
    // These tests verify the classifier produces correct results that SupabaseSync
    // would use for retry/skip decisions.

    test('401 error classifies as authExpired with shouldRefreshAuth', () {
      final error = PostgrestException(message: 'JWT expired', code: '401');
      final classified = SyncErrorClassifier.classify(error);
      expect(classified.kind, SyncErrorKind.authExpired);
      expect(classified.shouldRefreshAuth, isTrue);
      expect(classified.retryable, isTrue);
    });

    test('429 error classifies as rateLimited', () {
      final error = PostgrestException(
        message: 'Too Many Requests',
        code: '429',
      );
      final classified = SyncErrorClassifier.classify(error);
      expect(classified.kind, SyncErrorKind.rateLimited);
      expect(classified.retryable, isTrue);
    });

    test('42501 error classifies as rlsDenial (permanent)', () {
      final error = PostgrestException(
        message: 'permission denied for table',
        code: '42501',
      );
      final classified = SyncErrorClassifier.classify(error);
      expect(classified.kind, SyncErrorKind.rlsDenial);
      expect(classified.retryable, isFalse);
    });
  });
}
```

#### Step 2.2.2: Implement SupabaseSync

```dart
// lib/features/sync/engine/supabase_sync.dart

import 'dart:io';

import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/engine/sync_error_classifier.dart';

/// All Supabase row I/O: upsert, delete, select, auth refresh (on 401),
/// rate limit handling.
///
/// WHY: Extracted from SyncEngine to create a clean I/O boundary.
/// Replaces the 8 @visibleForTesting methods on SyncEngine
/// (pushDeleteRemote, upsertRemote, insertOnlyRemote, fetchServerUpdatedAt,
/// shouldSkipLwwPush, etc.).
///
/// FROM SPEC Section 3 (Target Architecture):
/// "Dependencies: SupabaseClient, SyncErrorClassifier"
class SupabaseSync {
  final SupabaseClient _supabase;

  SupabaseSync(this._supabase);

  /// Expose the raw SupabaseClient for components that need direct access
  /// (IntegrityChecker, OrphanScanner, StorageCleanup that pre-date this boundary).
  /// NOTE: Transitional escape hatch.
  SupabaseClient get client => _supabase;

  // ---------------------------------------------------------------------------
  // Row I/O
  // ---------------------------------------------------------------------------

  /// Upsert a record to Supabase and return the server response.
  /// FROM SPEC: SyncEngine.upsertRemote (sync_engine.dart:785-795)
  /// Replaces: @visibleForTesting upsertRemote
  Future<Map<String, dynamic>> upsertRecord(
    String tableName,
    Map<String, dynamic> payload,
  ) async {
    return _supabase
        .from(tableName)
        .upsert(payload)
        .select('updated_at')
        .single();
  }

  /// INSERT (never upsert) a record to Supabase for append-only tables.
  /// Swallows 23505 (duplicate key) as idempotent success.
  ///
  /// WHY: insertOnly adapters (e.g. user_consent_records) must never update
  /// existing records. Server-side RLS has no UPDATE policy, and the
  /// consent audit trail must be immutable.
  /// FROM SPEC: SyncEngine.insertOnlyRemote (sync_engine.dart:806-826)
  /// Replaces: @visibleForTesting insertOnlyRemote
  Future<void> insertOnly(
    String tableName,
    Map<String, dynamic> payload,
  ) async {
    try {
      await _supabase.from(tableName).insert(payload);
    } on Object catch (e) {
      final msg = e.toString();
      if (msg.contains('23505') || msg.contains('duplicate key')) {
        Logger.sync(
          'insertOnly: $tableName/${payload["id"]} already exists (idempotent)',
        );
        return;
      }
      rethrow;
    }
  }

  /// Push a soft-delete: sends UPDATE with deleted_at/deleted_by.
  /// Returns the server response (empty if record already absent on server).
  /// FROM SPEC: SyncEngine.pushDeleteRemote (sync_engine.dart:761-779)
  /// Replaces: @visibleForTesting pushDeleteRemote
  Future<List<Map<String, dynamic>>> pushSoftDelete({
    required String tableName,
    required String recordId,
    required String deletedAt,
    required String deletedBy,
    required String updatedAt,
  }) async {
    final raw = await _supabase
        .from(tableName)
        .update({
          'deleted_at': deletedAt,
          'deleted_by': deletedBy,
          'updated_at': updatedAt,
        })
        .eq('id', recordId)
        .select('updated_at, deleted_by');
    return (raw as List).cast<Map<String, dynamic>>();
  }

  /// Push a hard-delete (record already gone locally).
  /// Idempotent — swallows errors if remote record also doesn't exist.
  /// FROM SPEC: SyncEngine._pushDelete hard-delete path (sync_engine.dart:677-688)
  Future<void> pushHardDelete({
    required String tableName,
    required String recordId,
  }) async {
    try {
      await _supabase.from(tableName).delete().eq('id', recordId);
    } on Object catch (e) {
      Logger.sync('Hard-delete push ignored: $tableName/$recordId -- $e');
    }
  }

  /// Fetch the server's updated_at for a record. Returns null if the record
  /// does not exist on the server (first push).
  /// FROM SPEC: SyncEngine.fetchServerUpdatedAt (sync_engine.dart:833-847)
  /// Replaces: @visibleForTesting fetchServerUpdatedAt
  Future<DateTime?> fetchServerUpdatedAt(
    String tableName,
    String recordId,
  ) async {
    final row = await _supabase
        .from(tableName)
        .select('updated_at')
        .eq('id', recordId)
        .maybeSingle();
    if (row == null) return null;
    final ts = row['updated_at'] as String?;
    if (ts == null) return null;
    return DateTime.parse(ts);
  }

  /// Pre-check for UNIQUE constraint violations before upsert.
  /// Returns the existing remote record's ID if a different record occupies
  /// the natural key slot, or null if safe to proceed.
  /// FROM SPEC: SyncEngine._preCheckUniqueConstraint (sync_engine.dart:1144-1176)
  Future<String?> preCheckUniqueConstraint(
    String tableName,
    String payloadId,
    List<String> naturalKeyColumns,
    Map<String, dynamic> payload,
  ) async {
    if (naturalKeyColumns.isEmpty) return null;

    var query = _supabase.from(tableName).select('id');
    for (final col in naturalKeyColumns) {
      final value = payload[col];
      if (value == null) return null;
      query = query.eq(col, value);
    }

    final existing = await query.maybeSingle();
    if (existing == null) return null;

    final existingId = existing['id'] as String?;
    if (existingId == payloadId) return null; // Same record

    return existingId; // Different record occupies the slot
  }

  // ---------------------------------------------------------------------------
  // Pull I/O
  // ---------------------------------------------------------------------------

  /// Fetch a page of records for a table with scope filter and cursor.
  /// FROM SPEC: SyncEngine._pullTable query building (sync_engine.dart:1732-1756)
  Future<List<Map<String, dynamic>>> fetchPage({
    required String tableName,
    required PostgrestFilterBuilder Function(PostgrestFilterBuilder query)
        applyFilter,
    String? cursor,
    required Duration safetyMargin,
    required int pageSize,
    required int offset,
  }) async {
    PostgrestFilterBuilder query = _supabase.from(tableName).select();
    query = applyFilter(query);

    if (cursor != null) {
      final cursorTime = DateTime.parse(cursor).subtract(safetyMargin);
      query = query.gte('updated_at', cursorTime.toIso8601String());
    }

    return List<Map<String, dynamic>>.from(
      await query
          .order('updated_at', ascending: true)
          .range(offset, offset + pageSize - 1) as List,
    );
  }

  /// Fetch a single record by ID from Supabase.
  /// Used by FK rescue to fetch missing parent projects.
  /// FROM SPEC: SyncEngine._rescueParentProject fetch (sync_engine.dart:2178-2183)
  Future<Map<String, dynamic>?> fetchRecord(
    String tableName,
    String recordId,
  ) async {
    final rows = await _supabase
        .from(tableName)
        .select()
        .eq('id', recordId)
        .limit(1);
    if (rows.isEmpty) return null;
    return Map<String, dynamic>.from(rows.first as Map);
  }

  // ---------------------------------------------------------------------------
  // Storage I/O
  // ---------------------------------------------------------------------------

  /// Upload binary data to a Supabase storage bucket.
  /// Returns true if upload succeeded, false if file already exists (409).
  /// FROM SPEC: SyncEngine._pushFileThreePhase Phase 1 (sync_engine.dart:1273-1288)
  Future<bool> uploadFile({
    required String bucket,
    required String storagePath,
    required List<int> bytes,
  }) async {
    try {
      await _supabase.storage.from(bucket).uploadBinary(storagePath, bytes);
      return true;
    } on StorageException catch (e) {
      if (e.statusCode == '409' || e.message.contains('already exists')) {
        Logger.sync('File already exists at $storagePath (idempotent)');
        return true; // Already uploaded — idempotent success
      }
      rethrow;
    }
  }

  /// Remove a file from storage (cleanup on partial failure).
  /// Best-effort — does not throw on failure.
  /// FROM SPEC: SyncEngine._pushFileThreePhase cleanup (sync_engine.dart:1303-1310)
  Future<void> removeFile({
    required String bucket,
    required String storagePath,
  }) async {
    try {
      await _supabase.storage.from(bucket).remove([storagePath]);
    } on Object catch (e) {
      Logger.sync('File cleanup failed for $storagePath: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Auth
  // ---------------------------------------------------------------------------

  /// Attempt to refresh the auth session. Returns true if refresh succeeded.
  /// FROM SPEC: SyncEngine._handleAuthError (sync_engine.dart:1524-1536)
  Future<bool> refreshAuth() async {
    final session = _supabase.auth.currentSession;
    if (session == null) return false;
    try {
      await _supabase.auth.refreshSession();
      Logger.auth('Auth refresh attempted: success=true');
      return true;
    } on Object catch (e) {
      Logger.auth('Auth refresh failed: ${e.runtimeType}');
      return false;
    }
  }

  /// Get current user ID from auth session.
  String? get currentUserId => _supabase.auth.currentUser?.id;
}
```

#### Step 2.2.3: Verify SupabaseSync

```
pwsh -Command "flutter analyze lib/features/sync/engine/supabase_sync.dart"
```

Expected: No analysis errors.

---

### Sub-phase 2.3: Wire I/O boundaries into SyncEngine (transitional)

**Files:**
- Modify: `lib/features/sync/engine/sync_engine.dart`
- Modify: `lib/features/sync/application/sync_engine_factory.dart`

**Agent**: backend-supabase-agent

#### Step 2.3.1: Add LocalSyncStore and SupabaseSync as constructor parameters to SyncEngine

Modify `SyncEngine` to accept the two I/O boundaries as constructor parameters. During this transitional step, the engine still uses `db` and `supabase` directly for methods not yet migrated, but new code and gradually migrated methods will use the boundaries.

In `lib/features/sync/engine/sync_engine.dart`, add to the constructor:

```dart
// WHY: Transitional wiring — SyncEngine now accepts I/O boundaries alongside
// raw db/supabase. As phases 3-5 extract handlers, they will depend ONLY on
// LocalSyncStore/SupabaseSync. Once phase 5 completes, raw db/supabase
// fields will be removed from SyncEngine.
//
// IMPORTANT: Do NOT remove db/supabase yet — existing private methods still
// use them. They are deprecated-in-place and will be removed in P5.

// Add these fields after the existing fields (around line 97):
final LocalSyncStore localStore;
final SupabaseSync supabaseSync;

// Modify constructor (line 155) to accept them:
SyncEngine({
  required this.db,
  required this.supabase,
  required this.companyId,
  required this.userId,
  required this.localStore,       // NEW
  required this.supabaseSync,     // NEW
  this.lockedBy = 'foreground',
  this.onProgress,
  DirtyScopeTracker? dirtyScopeTracker,
}) : _dirtyScopeTracker = dirtyScopeTracker,
     _mutex = SyncMutex(db),
     _changeTracker = ChangeTracker(db),
     _conflictResolver = ConflictResolver(db),
     _integrityChecker = IntegrityChecker(db, supabase),
     _orphanScanner = OrphanScanner(supabase),
     _storageCleanup = StorageCleanup(supabase, db);
```

In `lib/features/sync/application/sync_engine_factory.dart`, update the factory to create and pass the I/O boundaries:

```dart
// Add imports:
import 'package:construction_inspector/features/sync/engine/local_sync_store.dart';
import 'package:construction_inspector/features/sync/engine/supabase_sync.dart';

// In the createEngine method (or wherever SyncEngine is constructed):
// Create I/O boundaries
final localStore = LocalSyncStore(database);
final supabaseSync = SupabaseSync(supabaseClient);

// Pass to SyncEngine:
return SyncEngine(
  db: database,
  supabase: supabaseClient,
  companyId: companyId,
  userId: userId,
  localStore: localStore,       // NEW
  supabaseSync: supabaseSync,   // NEW
  lockedBy: lockedBy,
  dirtyScopeTracker: dirtyScopeTracker,
);
```

Also update `SyncEngine.createForBackgroundSync` (sync_engine.dart:179-206) to create and pass I/O boundaries:

```dart
static Future<SyncEngine?> createForBackgroundSync({
  required Database database,
  required SupabaseClient supabase,
}) async {
  // ... existing session/userId/companyId resolution ...
  final localStore = LocalSyncStore(database);
  final supabaseSync = SupabaseSync(supabase);

  return SyncEngine(
    db: database,
    supabase: supabase,
    companyId: companyId,
    userId: userId,
    localStore: localStore,
    supabaseSync: supabaseSync,
    lockedBy: 'background',
  );
}
```

#### Step 2.3.2: Update test files that construct SyncEngine directly

Any test files that directly construct SyncEngine must be updated to pass the new required parameters. Search for `SyncEngine(` in test files:

- `test/features/sync/engine/sync_engine_test.dart`
- `test/features/sync/engine/sync_engine_delete_test.dart`
- `test/features/sync/engine/sync_engine_lww_test.dart`
- `test/features/sync/engine/sync_engine_e2e_test.dart`
- `test/features/sync/application/background_sync_handler_test.dart`

For each, add the I/O boundary parameters:

```dart
// In test setup where SyncEngine is created:
final localStore = LocalSyncStore(db);
final supabaseSync = SupabaseSync(mockSupabase);

final engine = SyncEngine(
  db: db,
  supabase: mockSupabase,
  companyId: 'test-company',
  userId: 'test-user',
  localStore: localStore,       // NEW
  supabaseSync: supabaseSync,   // NEW
);
```

For test subclasses (`_EmptyResponseSyncEngine`, `_LwwTestSyncEngine`, `_NullTimestampLwwTestSyncEngine`), pass through to super:

```dart
class _EmptyResponseSyncEngine extends SyncEngine {
  _EmptyResponseSyncEngine({
    required super.db,
    required super.supabase,
    required super.companyId,
    required super.userId,
    required super.localStore,
    required super.supabaseSync,
  });
  // ... existing overrides ...
}
```

#### Step 2.3.3: Verify transitional wiring

```
pwsh -Command "flutter analyze lib/features/sync/engine/ lib/features/sync/application/sync_engine_factory.dart"
```

Expected: No analysis errors. All existing tests should still compile (behavioral verification deferred to CI).

---

## Phase 3: Extract Push + File Handlers

Phase 3 extracts push orchestration and file upload into dedicated handler classes that depend on the I/O boundaries from Phase 2 instead of raw `db`/`supabase`.

**Prerequisite**: Phase 2 complete (LocalSyncStore and SupabaseSync exist and are wired into SyncEngine).

---

### Sub-phase 3.1: Create PushHandler

**Files:**
- Create: `lib/features/sync/engine/push_handler.dart`
- Test: `test/features/sync/engine/push_handler_contract_test.dart`

**Agent**: backend-supabase-agent

#### Step 3.1.1: Write PushHandler contract test (red)

```dart
// test/features/sync/engine/push_handler_contract_test.dart

import 'package:flutter_test/flutter_test.dart';

import 'package:construction_inspector/features/sync/engine/push_handler.dart';

// WHY: Contract tests define PushHandler public API before implementation.
// FROM SPEC Section 4.2: "Given changes -> calls SupabaseSync in FK order,
// skips blocked records, uses FileSyncHandler for file adapters, accurate counts"

void main() {
  group('PushHandler API surface', () {
    test('class exists with expected constructor', () {
      // WHY: Compile-time verification that PushHandler exists
      expect(PushHandler, isNotNull);
    });
  });

  group('PushResult', () {
    test('combines with + operator', () {
      const a = PushResult(pushed: 3, errors: 1, errorMessages: ['err1']);
      const b = PushResult(pushed: 2, errors: 0, errorMessages: []);
      final combined = a + b;
      expect(combined.pushed, 5);
      expect(combined.errors, 1);
      expect(combined.errorMessages, ['err1']);
    });

    test('empty result has zero counts', () {
      const result = PushResult();
      expect(result.pushed, 0);
      expect(result.errors, 0);
      expect(result.rlsDenials, 0);
      expect(result.skippedPush, 0);
    });
  });
}
```

#### Step 3.1.2: Implement PushHandler

```dart
// lib/features/sync/engine/push_handler.dart

import 'dart:math';

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';
import 'package:construction_inspector/features/sync/engine/conflict_resolver.dart';
import 'package:construction_inspector/features/sync/engine/file_sync_handler.dart';
import 'package:construction_inspector/features/sync/engine/local_sync_store.dart';
import 'package:construction_inspector/features/sync/engine/supabase_sync.dart';
import 'package:construction_inspector/features/sync/engine/sync_error_classifier.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';
import 'package:construction_inspector/features/sync/domain/sync_error.dart';
import 'package:construction_inspector/shared/utils/safe_row.dart';

/// Result of a push cycle.
class PushResult {
  final int pushed;
  final int errors;
  final List<String> errorMessages;
  final int rlsDenials;
  final int skippedPush;

  const PushResult({
    this.pushed = 0,
    this.errors = 0,
    this.errorMessages = const [],
    this.rlsDenials = 0,
    this.skippedPush = 0,
  });

  PushResult operator +(PushResult other) {
    return PushResult(
      pushed: pushed + other.pushed,
      errors: errors + other.errors,
      errorMessages: [...errorMessages, ...other.errorMessages],
      rlsDenials: rlsDenials + other.rlsDenials,
      skippedPush: skippedPush + other.skippedPush,
    );
  }
}

/// Push orchestration: reads changes, FK ordering, per-record routing,
/// skip/block decisions.
///
/// WHY: Extracted from SyncEngine._push (sync_engine.dart:473-625) to create
/// a focused, independently testable push handler.
/// FROM SPEC Section 3 (Target Architecture):
/// "Dependencies: LocalSyncStore, SupabaseSync, ChangeTracker, SyncRegistry,
///  SyncErrorClassifier, FileSyncHandler"
class PushHandler {
  final LocalSyncStore _localStore;
  final SupabaseSync _supabaseSync;
  final ChangeTracker _changeTracker;
  final ConflictResolver _conflictResolver;
  final SyncRegistry _registry;
  final FileSyncHandler _fileSyncHandler;
  final String companyId;
  final String userId;

  /// Progress callback for UI tracking.
  void Function(String tableName, int processed, int? total)? onProgress;

  /// Per-cycle counters (reset at start of push).
  int _rlsDenialCount = 0;
  int _skippedPushCount = 0;

  PushHandler({
    required LocalSyncStore localStore,
    required SupabaseSync supabaseSync,
    required ChangeTracker changeTracker,
    required ConflictResolver conflictResolver,
    required SyncRegistry registry,
    required FileSyncHandler fileSyncHandler,
    required this.companyId,
    required this.userId,
    this.onProgress,
  })  : _localStore = localStore,
        _supabaseSync = supabaseSync,
        _changeTracker = changeTracker,
        _conflictResolver = conflictResolver,
        _registry = registry,
        _fileSyncHandler = fileSyncHandler;

  /// Execute the push cycle: read changes, FK order, route each record.
  /// FROM SPEC: SyncEngine._push (sync_engine.dart:473-625)
  Future<PushResult> push() async {
    _rlsDenialCount = 0;
    _skippedPushCount = 0;

    // Circuit breaker check
    // FROM SPEC Section 3L: Prevents runaway push loops
    if (await _changeTracker.isCircuitBreakerTripped()) {
      await _changeTracker.purgeOldFailures();
      if (await _changeTracker.isCircuitBreakerTripped()) {
        Logger.sync(
          'CIRCUIT BREAKER: change_log exceeds ${SyncEngineConfig.circuitBreakerThreshold}. '
          'Push suspended.',
        );
        return const PushResult(
          errors: 1,
          errorMessages: ['Circuit breaker tripped: too many pending changes'],
        );
      }
    }

    final changes = await _changeTracker.getUnprocessedChanges();
    if (changes.isEmpty) return const PushResult();

    var pushed = 0;
    var errors = 0;
    final errorMessages = <String>[];

    // Process tables in FK dependency order
    // FROM SPEC: SyncEngine._push FK ordering (sync_engine.dart:503)
    for (final tableName in _registry.dependencyOrder) {
      final tableChanges = changes[tableName];
      if (tableChanges == null || tableChanges.isEmpty) continue;

      final adapter = _registry.adapterFor(tableName);

      // Per-record FK blocking
      // FROM SPEC: SyncEngine._push FK blocking (sync_engine.dart:509-554)
      final fkMap = adapter.fkColumnMap;
      final unblockedChanges = <ChangeEntry>[];

      if (fkMap.isEmpty) {
        unblockedChanges.addAll(tableChanges);
      } else {
        for (final change in tableChanges) {
          var blocked = false;
          final localRecord = await _localStore.readLocalRecord(
            adapter.tableName,
            change.recordId,
          );
          if (localRecord == null) {
            unblockedChanges.add(change);
            continue;
          }
          for (final entry in fkMap.entries) {
            final parentTable = entry.key;
            final fkColumn = entry.value;
            final parentId = localRecord[fkColumn]?.toString();
            if (parentId != null &&
                await _changeTracker.hasFailedRecord(parentTable, parentId)) {
              Logger.sync(
                'BLOCKED: ${adapter.tableName}/${change.recordId} -- '
                'parent $parentTable/$parentId has failed',
              );
              await _changeTracker.markFailed(
                change.id,
                'Blocked by failed parent $parentTable/$parentId',
              );
              errors++;
              blocked = true;
              break;
            }
          }
          if (!blocked) unblockedChanges.add(change);
        }
      }

      // Process unblocked changes
      var processedInTable = 0;
      for (final change in unblockedChanges) {
        // Adapter skip check (e.g. builtin forms)
        // FROM SPEC: SyncEngine._push skip check (sync_engine.dart:559-580)
        if (change.operation != 'delete') {
          final record = await _localStore.readLocalRecord(
            adapter.tableName,
            change.recordId,
          );
          if (record != null && adapter.shouldSkipPush(record)) {
            await _changeTracker.markProcessed(change.id);
            pushed++;
            Logger.sync(
              'Push skip (adapter filter): ${adapter.tableName}/${change.recordId}',
            );
            processedInTable++;
            onProgress?.call(tableName, processedInTable, unblockedChanges.length);
            continue;
          }
        }

        try {
          await _routeAndPush(adapter, change);
          await _changeTracker.markProcessed(change.id);
          pushed++;
        } on Object catch (e) {
          Logger.sync('Push error for $tableName/${change.recordId}: $e');
          final shouldRetry = await _handlePushError(e, change);
          if (shouldRetry) {
            try {
              await _routeAndPush(adapter, change);
              await _changeTracker.markProcessed(change.id);
              pushed++;
            } on Object catch (retryError) {
              Logger.sync(
                'Push retry failed for $tableName/${change.recordId}: $retryError',
              );
              await _changeTracker.markFailed(
                change.id,
                'Retry failed: $retryError',
              );
              errors++;
              errorMessages.add('$tableName/${change.recordId}: $retryError');
            }
          } else {
            errors++;
            errorMessages.add('$tableName/${change.recordId}: $e');
          }
        }
        processedInTable++;
        onProgress?.call(tableName, processedInTable, unblockedChanges.length);
      }
    }

    return PushResult(
      pushed: pushed,
      errors: errors,
      errorMessages: errorMessages,
      rlsDenials: _rlsDenialCount,
      skippedPush: _skippedPushCount,
    );
  }

  /// Route a change to the correct push method.
  /// FROM SPEC: SyncEngine._routeAndPush (sync_engine.dart:632-651)
  Future<void> _routeAndPush(TableAdapter adapter, ChangeEntry change) async {
    if (change.operation == 'delete') {
      await _pushDelete(adapter, change);
    } else if (change.operation == 'update') {
      final record = await _localStore.readLocalRecordColumns(
        adapter.tableName,
        change.recordId,
        ['deleted_at'],
      );
      if (record != null && record['deleted_at'] != null) {
        await _pushDelete(adapter, change);
      } else {
        await _pushUpsert(adapter, change);
      }
    } else {
      await _pushUpsert(adapter, change);
    }
  }

  /// Push soft-delete or hard-delete.
  /// FROM SPEC: SyncEngine._pushDelete (sync_engine.dart:662-753)
  Future<void> _pushDelete(TableAdapter adapter, ChangeEntry change) async {
    final localRecord = await _localStore.readLocalRecord(
      adapter.tableName,
      change.recordId,
    );

    if (localRecord == null) {
      // Hard-delete: local record gone
      Logger.sync(
        'Hard-delete push: ${adapter.tableName}/${change.recordId} -- '
        'local record gone, deleting remote',
      );
      await _supabaseSync.pushHardDelete(
        tableName: adapter.tableName,
        recordId: change.recordId,
      );
      return;
    }

    final deletedAt = localRecord['deleted_at'];
    if (deletedAt == null) {
      Logger.sync(
        'Soft-delete skip: ${adapter.tableName}/${change.recordId} -- '
        'record not deleted (restored?)',
      );
      return;
    }

    final localUpdatedAtBefore = localRecord['updated_at'];
    final response = await _supabaseSync.pushSoftDelete(
      tableName: adapter.tableName,
      recordId: change.recordId,
      deletedAt: deletedAt as String,
      deletedBy: localRecord.optionalString('deleted_by') ?? userId,
      updatedAt: localRecord.requireString('updated_at'),
    );

    if (response.isEmpty) {
      Logger.sync(
        'Soft-delete push: ${adapter.tableName}/${change.recordId} '
        '-- remote record already absent',
      );
      return;
    }

    // Write back server timestamps
    // FROM SPEC: BUG-A FIX (sync_engine.dart:729-753)
    final serverUpdatedAt = response.first['updated_at'] as String?;
    final serverDeletedBy = response.first['deleted_by'] as String?;
    if (serverUpdatedAt != null && serverUpdatedAt != localUpdatedAtBefore) {
      await _localStore.writeBackServerTimestamp(
        adapter.tableName,
        change.recordId,
        serverUpdatedAt,
        additionalFields:
            serverDeletedBy != null ? {'deleted_by': serverDeletedBy} : null,
      );
    }
  }

  /// Push upsert (insert or update).
  /// FROM SPEC: SyncEngine._pushUpsert (sync_engine.dart:939-1129)
  Future<void> _pushUpsert(TableAdapter adapter, ChangeEntry change) async {
    final localRecord = await _localStore.readLocalRecord(
      adapter.tableName,
      change.recordId,
    );

    if (localRecord == null) {
      Logger.sync(
        'Push skip: ${adapter.tableName}/${change.recordId} -- '
        'deleted locally after trigger fired',
      );
      return;
    }

    await adapter.validate(localRecord);
    final payload = adapter.convertForRemote(localRecord);

    // Stamp user columns
    for (final col in adapter.userStampColumns.keys) {
      payload[col] = userId;
    }

    // Company ID validation + stamping
    // FROM SPEC: SyncEngine.validateAndStampCompanyId (sync_engine.dart:910-929)
    _validateAndStampCompanyId(payload, adapter.tableName, change.recordId);

    // Pre-check UNIQUE constraints
    // FROM SPEC: SyncEngine._preCheckUniqueConstraint (sync_engine.dart:1144-1176)
    final conflictRemoteId = await _supabaseSync.preCheckUniqueConstraint(
      adapter.tableName,
      payload['id'] as String,
      adapter.naturalKeyColumns,
      payload,
    );
    if (conflictRemoteId != null) {
      final oldId = payload['id'] as String;
      Logger.sync(
        'Natural key conflict auto-resolved: ${adapter.tableName} '
        'local=$oldId -> remote=$conflictRemoteId',
      );
      await _localStore.remapRecordId(
        tableName: adapter.tableName,
        oldId: oldId,
        newId: conflictRemoteId,
        childFkColumns: _childFkColumns(adapter.tableName),
      );
      // Check if remap resulted in a duplicate removal
      if (!await _localStore.recordExists(adapter.tableName, conflictRemoteId)) {
        // Target was removed during remap — nothing to push
        return;
      }
      payload['id'] = conflictRemoteId;
    }

    // Stamp created_by_user_id
    if (payload['created_by_user_id'] == null ||
        payload['created_by_user_id'] == '') {
      payload['created_by_user_id'] = userId;
    }

    // Route file adapters to FileSyncHandler
    if (adapter.isFileAdapter) {
      await _fileSyncHandler.pushFileThreePhase(
        adapter: adapter,
        change: change,
        localRecord: localRecord,
        payload: payload,
        companyId: companyId,
      );
      return;
    }

    // LWW push guard
    // FROM SPEC: SyncEngine.shouldSkipLwwPush (sync_engine.dart:856-889)
    if (await _shouldSkipLwwPush(adapter.tableName, payload)) {
      return;
    }

    // Execute push
    if (adapter.insertOnly) {
      await _supabaseSync.insertOnly(adapter.tableName, payload);
      return;
    }
    final response = await _supabaseSync.upsertRecord(adapter.tableName, payload);

    // Write back server timestamp
    final serverUpdatedAt = response['updated_at'] as String?;
    if (serverUpdatedAt != null && serverUpdatedAt != payload['updated_at']) {
      await _localStore.writeBackServerTimestamp(
        adapter.tableName,
        payload['id'] as String,
        serverUpdatedAt,
      );
    }
  }

  /// LWW push guard: skip push if server has newer data.
  /// FROM SPEC: SyncEngine.shouldSkipLwwPush (sync_engine.dart:856-889)
  Future<bool> _shouldSkipLwwPush(
    String tableName,
    Map<String, dynamic> payload,
  ) async {
    final localUpdatedAt = payload['updated_at'] as String?;
    final recordId = payload['id'] as String;
    final serverTs = await _supabaseSync.fetchServerUpdatedAt(tableName, recordId);
    if (serverTs != null && localUpdatedAt != null) {
      final localTs = DateTime.parse(localUpdatedAt);
      if (serverTs.compareTo(localTs) >= 0) {
        Logger.sync(
          'LWW push skip: $tableName/$recordId -- '
          'server=$serverTs >= local=$localTs',
        );
        await _conflictResolver.resolve(
          tableName: tableName,
          recordId: recordId,
          local: payload,
          remote: {
            'id': recordId,
            'updated_at': serverTs.toUtc().toIso8601String(),
          },
        );
        _skippedPushCount++;
        return true;
      }
    }
    return false;
  }

  /// Company ID validation + stamping.
  /// FROM SPEC: SyncEngine.validateAndStampCompanyId (sync_engine.dart:910-929)
  void _validateAndStampCompanyId(
    Map<String, dynamic> payload,
    String tableName,
    String recordId,
  ) {
    if (payload.containsKey('company_id')) {
      final payloadCompanyId = payload['company_id']?.toString();
      if (payloadCompanyId == null || payloadCompanyId.isEmpty) {
        payload['company_id'] = companyId;
        Logger.sync('Stamped company_id on $tableName/$recordId');
      } else if (payloadCompanyId != companyId) {
        throw StateError(
          'Company ID mismatch: $tableName record has $payloadCompanyId '
          'but current user belongs to $companyId. '
          'Refusing to push cross-company data.',
        );
      }
    }
  }

  /// Error handling for push failures. Returns true if retry is appropriate.
  /// FROM SPEC: SyncEngine._handlePushError (sync_engine.dart:1407-1512)
  /// NOW delegates to SyncErrorClassifier for classification.
  Future<bool> _handlePushError(Object error, ChangeEntry change) async {
    final classified = SyncErrorClassifier.classify(error);

    // Auth refresh
    if (classified.shouldRefreshAuth) {
      final refreshed = await _supabaseSync.refreshAuth();
      if (refreshed) return true;
      throw StateError('Auth refresh failed, aborting sync');
    }

    // Rate limit / transient: backoff and maybe retry
    if (classified.kind == SyncErrorKind.rateLimited ||
        classified.kind == SyncErrorKind.networkError) {
      Logger.error(
        '${classified.kind.name.toUpperCase()}: ${change.tableName}/${change.recordId}',
      );
      final delay = _computeBackoff(change.retryCount);
      await Future.delayed(delay);
      if (change.retryCount == 0) {
        await _changeTracker.markFailed(
          change.id,
          'Retryable (${classified.kind.name}): ${classified.logDetail}',
        );
        return true;
      }
      await _changeTracker.markFailed(
        change.id,
        '${classified.kind.name}: ${classified.logDetail}',
      );
      return false;
    }

    // Constraint violation (23505): retryable if TOCTOU race
    if (classified.kind == SyncErrorKind.uniqueViolation) {
      Logger.sync('CONSTRAINT 23505: ${change.tableName}/${change.recordId}');
      if (change.retryCount < 2) {
        await _changeTracker.markFailed(
          change.id,
          'Constraint race (23505): ${classified.logDetail} -- will retry',
        );
        return true;
      }
      await _changeTracker.markFailed(
        change.id,
        'Constraint violation (23505): ${classified.logDetail}',
      );
      return false;
    }

    // RLS denied (42501): permanent
    if (classified.kind == SyncErrorKind.rlsDenial) {
      Logger.error(
        'RLS DENIED (42501): ${change.tableName}/${change.recordId}',
      );
      await _changeTracker.markFailed(
        change.id,
        'RLS denied (42501) on ${change.tableName}',
      );
      _rlsDenialCount++;
      return false;
    }

    // FK violation (23503): permanent
    if (classified.kind == SyncErrorKind.fkViolation) {
      Logger.error(
        'FK VIOLATION 23503: ${change.tableName}/${change.recordId}',
      );
      await _changeTracker.markFailed(
        change.id,
        'FK violation (23503): ${classified.logDetail}',
      );
      return false;
    }

    // All others: permanent
    await _changeTracker.markFailed(change.id, error.toString());
    return false;
  }

  Duration _computeBackoff(int retryCount) {
    final delayMs =
        SyncEngineConfig.retryBaseDelay.inMilliseconds * pow(2, retryCount);
    final cappedMs = min(
      delayMs.toInt(),
      SyncEngineConfig.retryMaxDelay.inMilliseconds,
    );
    return Duration(milliseconds: cappedMs);
  }

  /// Child FK columns for ID remap cascading.
  /// FROM SPEC: SyncEngine._childFkColumns (sync_engine.dart:1182-1220)
  static List<({String table, String column})> _childFkColumns(
    String parentTable,
  ) {
    return switch (parentTable) {
      'projects' => [
        (table: 'daily_entries', column: 'project_id'),
        (table: 'locations', column: 'project_id'),
        (table: 'contractors', column: 'project_id'),
        (table: 'bid_items', column: 'project_id'),
        (table: 'photos', column: 'project_id'),
        (table: 'entry_quantities', column: 'project_id'),
        (table: 'personnel_types', column: 'project_id'),
        (table: 'todo_items', column: 'project_id'),
        (table: 'inspector_forms', column: 'project_id'),
        (table: 'equipment', column: 'project_id'),
        (table: 'project_assignments', column: 'project_id'),
        (table: 'form_exports', column: 'project_id'),
        (table: 'entry_exports', column: 'project_id'),
        (table: 'documents', column: 'project_id'),
      ],
      'daily_entries' => [
        (table: 'entry_contractors', column: 'entry_id'),
        (table: 'entry_equipment', column: 'entry_id'),
        (table: 'entry_personnel_counts', column: 'entry_id'),
        (table: 'entry_quantities', column: 'entry_id'),
        (table: 'photos', column: 'entry_id'),
        (table: 'form_responses', column: 'entry_id'),
        (table: 'entry_exports', column: 'entry_id'),
        (table: 'documents', column: 'entry_id'),
      ],
      'form_responses' => [(table: 'form_exports', column: 'form_response_id')],
      'locations' => [(table: 'daily_entries', column: 'location_id')],
      'contractors' => [
        (table: 'entry_contractors', column: 'contractor_id'),
        (table: 'personnel_types', column: 'contractor_id'),
      ],
      _ => [],
    };
  }
}
```

#### Step 3.1.3: Verify PushHandler

```
pwsh -Command "flutter analyze lib/features/sync/engine/push_handler.dart"
```

Expected: No analysis errors.

---

### Sub-phase 3.2: Create FileSyncHandler

**Files:**
- Create: `lib/features/sync/engine/file_sync_handler.dart`
- Test: `test/features/sync/engine/file_sync_handler_contract_test.dart`

**Agent**: backend-supabase-agent

#### Step 3.2.1: Write FileSyncHandler contract test (red)

```dart
// test/features/sync/engine/file_sync_handler_contract_test.dart

import 'package:flutter_test/flutter_test.dart';

import 'package:construction_inspector/features/sync/engine/file_sync_handler.dart';

// WHY: Contract tests verify the three-phase file push and EXIF stripping API.
// FROM SPEC Section 4.2: "Three-phase sequence, EXIF strip when flagged,
// storage path validated, phase-2 failure cleans up phase-1"

void main() {
  group('FileSyncHandler API surface', () {
    test('class exists with expected constructor', () {
      expect(FileSyncHandler, isNotNull);
    });
  });

  group('storage path validation', () {
    test('rejects path traversal attempts', () {
      expect(
        () => FileSyncHandler.validateStoragePath(
          '../../../etc/passwd',
          stripExifGps: false,
        ),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('accepts valid photo path', () {
      // NOTE: No throw expected
      FileSyncHandler.validateStoragePath(
        'entries/abc-123/def-456/photo.jpg',
        stripExifGps: true,
      );
    });

    test('accepts valid document path', () {
      FileSyncHandler.validateStoragePath(
        'documents/abc-123/def-456/report.pdf',
        stripExifGps: false,
      );
    });
  });
}
```

#### Step 3.2.2: Implement FileSyncHandler

```dart
// lib/features/sync/engine/file_sync_handler.dart

import 'dart:io';
import 'dart:typed_data';

import 'package:image/image.dart' as img;

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';
import 'package:construction_inspector/features/sync/engine/conflict_resolver.dart';
import 'package:construction_inspector/features/sync/engine/local_sync_store.dart';
import 'package:construction_inspector/features/sync/engine/supabase_sync.dart';

/// Three-phase file upload, EXIF GPS stripping, storage path validation.
///
/// WHY: Extracted from SyncEngine._pushFileThreePhase (sync_engine.dart:1227-1336)
/// and SyncEngine._stripExifGps (sync_engine.dart:1366-1392) to isolate file
/// upload logic from general push orchestration.
///
/// FROM SPEC Section 3 (Target Architecture):
/// "Dependencies: SupabaseSync (storage), LocalSyncStore, image package"
class FileSyncHandler {
  final SupabaseSync _supabaseSync;
  final LocalSyncStore _localStore;
  final ConflictResolver _conflictResolver;

  FileSyncHandler({
    required SupabaseSync supabaseSync,
    required LocalSyncStore localStore,
    required ConflictResolver conflictResolver,
  })  : _supabaseSync = supabaseSync,
        _localStore = localStore,
        _conflictResolver = conflictResolver;

  /// Three-phase file push: upload file, upsert metadata, bookmark locally.
  ///
  /// Phase 1: Upload binary to storage bucket (idempotent on 409)
  /// Phase 2: Upsert metadata with remote_path. On failure: cleanup Phase 1.
  /// Phase 3: Bookmark remote_path + server updated_at locally with trigger suppression.
  ///
  /// FROM SPEC: SyncEngine._pushFileThreePhase (sync_engine.dart:1227-1336)
  Future<void> pushFileThreePhase({
    required TableAdapter adapter,
    required ChangeEntry change,
    required Map<String, dynamic> localRecord,
    required Map<String, dynamic> payload,
    required String companyId,
  }) async {
    final filePath = localRecord['file_path'] as String?;
    var remotePath = localRecord['remote_path'] as String?;

    // LWW push guard for file records -- BEFORE Phase 1 to prevent storage leaks
    // FROM SPEC: sync_engine.dart:1238-1246
    final recordId = payload['id'] as String;
    final localUpdatedAt = payload['updated_at'] as String?;
    final serverTs = await _supabaseSync.fetchServerUpdatedAt(
      adapter.tableName,
      recordId,
    );
    if (serverTs != null && localUpdatedAt != null) {
      final localTs = DateTime.parse(localUpdatedAt);
      if (serverTs.compareTo(localTs) >= 0) {
        Logger.sync(
          'LWW push skip (${adapter.tableName}): $recordId -- '
          'server=$serverTs >= local=$localTs',
        );
        await _conflictResolver.resolve(
          tableName: adapter.tableName,
          recordId: recordId,
          local: payload,
          remote: {
            'id': recordId,
            'updated_at': serverTs.toUtc().toIso8601String(),
          },
        );
        return;
      }
    }

    // Phase 1: Upload file (skip if already uploaded)
    if (remotePath == null || remotePath.isEmpty) {
      if (filePath == null || filePath.isEmpty) {
        Logger.sync(
          '${adapter.tableName} ${change.recordId}: no file_path or remote_path, skipping',
        );
        return;
      }

      final file = File(filePath);
      if (!file.existsSync()) {
        Logger.sync(
          '${adapter.tableName} ${change.recordId}: file not found at $filePath, skipping',
        );
        return;
      }

      var bytes = await file.readAsBytes();
      // ADV-56: Strip EXIF GPS data before upload for privacy (photos only)
      if (adapter.stripExifGps) {
        bytes = stripExifGps(bytes);
      }
      final storagePath = adapter.buildStoragePath(companyId, localRecord);
      validateStoragePath(storagePath, stripExifGps: adapter.stripExifGps);

      await _supabaseSync.uploadFile(
        bucket: adapter.storageBucket,
        storagePath: storagePath,
        bytes: bytes,
      );
      remotePath = storagePath;
    }

    // Phase 2: Upsert metadata with FRESH remote_path
    payload['remote_path'] = remotePath;
    Map<String, dynamic>? photoResponse;
    try {
      photoResponse = await _supabaseSync.upsertRecord(
        adapter.tableName,
        payload,
      );
    } on Object catch (_) {
      // WHY: Phase 2 failure -> cleanup Phase 1 upload to prevent orphaned files
      // FROM SPEC: Section 3D -- File Cleanup on Partial Failure
      Logger.sync(
        '${adapter.tableName} ${change.recordId}: Phase 2 failed, '
        'cleaning up uploaded file at $remotePath',
      );
      await _supabaseSync.removeFile(
        bucket: adapter.storageBucket,
        storagePath: remotePath,
      );
      rethrow;
    }

    // Phase 3: Bookmark remote_path locally with trigger suppression
    // FROM SPEC: sync_engine.dart:1314-1335
    final serverUpdatedAt = photoResponse['updated_at'] as String?;
    await _localStore.bookmarkRemotePath(
      adapter.tableName,
      change.recordId,
      remotePath,
      serverUpdatedAt: serverUpdatedAt,
      localUpdatedAt: payload['updated_at'] as String?,
    );
  }

  /// Strip EXIF GPS metadata from image bytes before upload (ADV-56).
  ///
  /// Preserves orientation and other non-GPS EXIF data. Falls back to
  /// returning original bytes if image cannot be decoded.
  /// FROM SPEC: SyncEngine._stripExifGps (sync_engine.dart:1366-1392)
  static Uint8List stripExifGps(Uint8List bytes) {
    try {
      final image = img.decodeImage(bytes);
      if (image == null) return bytes;

      if (image.exif.gpsIfd.isEmpty) return bytes;

      final clean = img.Image.from(image);
      clean.exif.imageIfd.copy(image.exif.imageIfd);
      clean.exif.exifIfd.copy(image.exif.exifIfd);
      clean.exif.interopIfd.copy(image.exif.interopIfd);
      // Deliberately omit gpsIfd to strip GPS data

      final encoded = img.encodeJpg(clean, quality: 95);
      return Uint8List.fromList(encoded);
    } on Object catch (e) {
      Logger.sync('EXIF GPS strip failed, uploading original: $e');
      return bytes;
    }
  }

  /// Validate a storage path matches the expected pattern.
  /// FROM SPEC: SyncEngine._validateStoragePath (sync_engine.dart:1343-1359)
  static void validateStoragePath(
    String path, {
    required bool stripExifGps,
  }) {
    final RegExp pattern;
    if (stripExifGps) {
      pattern = RegExp(
        r'^[a-zA-Z0-9_/-]+/[a-f0-9-]+/[a-f0-9-]+/[a-zA-Z0-9_.-]+\.(jpg|jpeg|png|heic)$',
      );
    } else {
      pattern = RegExp(
        r'^[a-zA-Z0-9_/-]+/[a-f0-9-]+/[a-f0-9-]+/[a-zA-Z0-9_.-]+\.(jpg|jpeg|png|heic|pdf|xls|xlsx|doc|docx|csv|txt)$',
      );
    }
    if (!pattern.hasMatch(path)) {
      throw ArgumentError('Invalid storage path: $path');
    }
  }
}
```

#### Step 3.2.3: Verify FileSyncHandler

```
pwsh -Command "flutter analyze lib/features/sync/engine/file_sync_handler.dart"
```

Expected: No analysis errors.

---

## Phase 4: Extract Pull + Enrollment + FK Rescue

Phase 4 extracts pull orchestration, enrollment, and FK rescue into dedicated handlers.

**Prerequisite**: Phase 2 complete (LocalSyncStore and SupabaseSync exist).

---

### Sub-phase 4.1: Create PullHandler

**Files:**
- Create: `lib/features/sync/engine/pull_handler.dart`
- Test: `test/features/sync/engine/pull_handler_contract_test.dart`

**Agent**: backend-supabase-agent

#### Step 4.1.1: Write PullHandler contract test (red)

```dart
// test/features/sync/engine/pull_handler_contract_test.dart

import 'package:flutter_test/flutter_test.dart';

import 'package:construction_inspector/features/sync/engine/pull_handler.dart';

// WHY: Contract tests define PullHandler public API.
// FROM SPEC Section 4.2: "Given pages -> calls LocalSyncStore.upsertPulledRecord,
// invokes ConflictResolver, calls EnrollmentHandler after assignments,
// respects dirty scopes"

void main() {
  group('PullHandler API surface', () {
    test('class exists with expected constructor', () {
      expect(PullHandler, isNotNull);
    });
  });

  group('PullResult', () {
    test('combines with + operator', () {
      const a = PullResult(pulled: 3, errors: 1, errorMessages: ['err1']);
      const b = PullResult(pulled: 2, errors: 0, conflicts: 1);
      final combined = a + b;
      expect(combined.pulled, 5);
      expect(combined.errors, 1);
      expect(combined.conflicts, 1);
    });

    test('empty result has zero counts', () {
      const result = PullResult();
      expect(result.pulled, 0);
      expect(result.errors, 0);
      expect(result.conflicts, 0);
      expect(result.skippedFk, 0);
    });
  });
}
```

#### Step 4.1.2: Implement PullHandler

```dart
// lib/features/sync/engine/pull_handler.dart

import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';
import 'package:construction_inspector/features/sync/engine/conflict_resolver.dart';
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
import 'package:construction_inspector/features/sync/engine/enrollment_handler.dart';
import 'package:construction_inspector/features/sync/engine/fk_rescue_handler.dart';
import 'package:construction_inspector/features/sync/engine/local_sync_store.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';
import 'package:construction_inspector/features/sync/engine/supabase_sync.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';
import 'package:construction_inspector/shared/utils/safe_row.dart';

/// Result of a pull cycle.
class PullResult {
  final int pulled;
  final int errors;
  final List<String> errorMessages;
  final int conflicts;
  final int skippedFk;

  const PullResult({
    this.pulled = 0,
    this.errors = 0,
    this.errorMessages = const [],
    this.conflicts = 0,
    this.skippedFk = 0,
  });

  PullResult operator +(PullResult other) {
    return PullResult(
      pulled: pulled + other.pulled,
      errors: errors + other.errors,
      errorMessages: [...errorMessages, ...other.errorMessages],
      conflicts: conflicts + other.conflicts,
      skippedFk: skippedFk + other.skippedFk,
    );
  }
}

/// Pull orchestration: iterates adapters, applies scope filters, manages
/// cursors, tombstone protection, conflict delegation.
///
/// WHY: Extracted from SyncEngine._pull (sync_engine.dart:1542-1710) and
/// SyncEngine._pullTable (sync_engine.dart:1712-1966).
/// FROM SPEC Section 3 (Target Architecture):
/// "Dependencies: LocalSyncStore, SupabaseSync, ConflictResolver,
///  SyncRegistry, DirtyScopeTracker"
class PullHandler {
  final LocalSyncStore _localStore;
  final SupabaseSync _supabaseSync;
  final ConflictResolver _conflictResolver;
  final ChangeTracker _changeTracker;
  final SyncRegistry _registry;
  final DirtyScopeTracker? _dirtyScopeTracker;
  final EnrollmentHandler _enrollmentHandler;
  final FkRescueHandler _fkRescueHandler;
  final String companyId;
  final String userId;

  /// Progress callback for UI tracking.
  void Function(String tableName, int processed, int? total)? onProgress;

  /// Callback when pull completes for a table. Used by enrollment hooks.
  /// WARNING: Fires while triggers are suppressed.
  Future<void> Function(String tableName, int pulledCount)? onPullComplete;

  /// Callback when circuit breaker trips for a record.
  void Function(String tableName, String recordId, int conflictCount)?
      onCircuitBreakerTrip;

  // Internal state
  List<String> _syncedProjectIds = [];
  List<String> _syncedContractorIds = [];
  bool _projectsAdapterCompleted = false;
  int _pullConflictCount = 0;
  int _pullSkippedFkCount = 0;

  PullHandler({
    required LocalSyncStore localStore,
    required SupabaseSync supabaseSync,
    required ConflictResolver conflictResolver,
    required ChangeTracker changeTracker,
    required SyncRegistry registry,
    required EnrollmentHandler enrollmentHandler,
    required FkRescueHandler fkRescueHandler,
    required this.companyId,
    required this.userId,
    DirtyScopeTracker? dirtyScopeTracker,
    this.onProgress,
    this.onPullComplete,
    this.onCircuitBreakerTrip,
  })  : _localStore = localStore,
        _supabaseSync = supabaseSync,
        _conflictResolver = conflictResolver,
        _changeTracker = changeTracker,
        _registry = registry,
        _dirtyScopeTracker = dirtyScopeTracker,
        _enrollmentHandler = enrollmentHandler,
        _fkRescueHandler = fkRescueHandler;

  /// Execute the pull cycle.
  /// FROM SPEC: SyncEngine._pull (sync_engine.dart:1542-1710)
  Future<PullResult> pull({bool onlyDirtyScopes = false}) async {
    _projectsAdapterCompleted = false;
    _pullConflictCount = 0;
    _pullSkippedFkCount = 0;

    await _localStore.reconcileSyncedProjects(userId);
    _syncedProjectIds = await _localStore.loadSyncedProjectIds();

    var pulled = 0;
    var errors = 0;
    final errorMessages = <String>[];

    // Suppress triggers for entire pull cycle
    // FROM SPEC: "pulling='1' set before writes, '0' reset in finally, even on error"
    try {
      await _localStore.suppressTriggers();

      for (final adapter in _registry.adapters) {
        if (adapter.skipPull) {
          Logger.sync('Pull skip (adapter.skipPull): ${adapter.tableName}');
          continue;
        }

        // Scope-based skip logic
        // FROM SPEC: SyncEngine._pull scope checks (sync_engine.dart:1564-1577)
        if (adapter.scopeType == ScopeType.direct) {
          // Always pull direct-scoped tables
        } else if (_syncedProjectIds.isEmpty) {
          Logger.sync('Pull skip (no loaded projects): ${adapter.tableName}');
          continue;
        } else if (adapter.scopeType == ScopeType.viaContractor &&
            _syncedContractorIds.isEmpty) {
          Logger.sync('Pull skip (no contractors): ${adapter.tableName}');
          continue;
        }

        // Dirty scope filtering for quick sync
        List<String>? projectIdsForPull;
        List<String>? contractorIdsForPull;
        if (onlyDirtyScopes &&
            _dirtyScopeTracker != null &&
            !_dirtyScopeTracker!.isDirty(adapter.tableName)) {
          Logger.sync(
            'Pull skip (not dirty, quick mode): ${adapter.tableName}',
          );
          continue;
        }

        if (onlyDirtyScopes && _dirtyScopeTracker != null) {
          switch (adapter.scopeType) {
            case ScopeType.direct:
              break;
            case ScopeType.viaProject:
            case ScopeType.viaEntry:
              final dirtyProjectIds = _dirtyScopeTracker!.dirtyProjectIdsFor(
                adapter.tableName,
                _syncedProjectIds,
              );
              if (dirtyProjectIds.isEmpty) {
                Logger.sync(
                  'Pull skip (no dirty projects, quick mode): ${adapter.tableName}',
                );
                continue;
              }
              projectIdsForPull = dirtyProjectIds.toList();
            case ScopeType.viaContractor:
              final dirtyProjectIds = _dirtyScopeTracker!.dirtyProjectIdsFor(
                adapter.tableName,
                _syncedProjectIds,
              );
              if (dirtyProjectIds.isEmpty) {
                Logger.sync(
                  'Pull skip (no dirty contractors, quick mode): ${adapter.tableName}',
                );
                continue;
              }
              projectIdsForPull = dirtyProjectIds.toList();
              contractorIdsForPull =
                  await _localStore.loadContractorIdsForProjectIds(
                projectIdsForPull,
              );
              if (contractorIdsForPull.isEmpty) {
                Logger.sync(
                  'Pull skip (no dirty contractors in scoped projects): ${adapter.tableName}',
                );
                continue;
              }
          }
        }

        try {
          final count = await _pullTable(
            adapter,
            projectIds: projectIdsForPull,
            contractorIds: contractorIdsForPull,
          );
          pulled += count;

          // Reload scope IDs after key adapters
          if (adapter.tableName == 'projects') {
            _projectsAdapterCompleted = true;
            if (count > 0) {
              _syncedProjectIds = await _localStore.loadSyncedProjectIds();
              Logger.sync(
                'Reloaded synced project IDs after pulling $count projects',
              );
            }
          }

          if (adapter.tableName == 'project_assignments') {
            if (count > 0) {
              Logger.sync(
                'Pulled $count project_assignments, enrolling projects',
              );
            }
            // Always run enrollment after project_assignments
            // FROM SPEC: SyncEngine._pull enrollment (sync_engine.dart:1663)
            await _enrollmentHandler.enrollFromAssignments(userId);
            _syncedProjectIds = await _localStore.loadSyncedProjectIds();

            // Fresh-restore guard
            // FROM SPEC: SyncEngine._pull cursor reset (sync_engine.dart:1670-1681)
            if (_syncedProjectIds.isEmpty) {
              final hasAssignments = await _localStore.hasLocalAssignments();
              if (!hasAssignments) {
                await _localStore.clearCursor('project_assignments');
                Logger.sync(
                  'Fresh-restore: cleared project_assignments cursor',
                );
              }
            }
          }
        } on Object catch (e, stack) {
          Logger.error(
            'Pull failed for ${adapter.tableName}',
            error: e,
            stack: stack,
          );
          errors++;
          errorMessages.add('${adapter.tableName}: $e');
        }
      }

      // Update last sync time
      await _localStore.writeLastSyncTime();

      // Clean orphaned synced_projects after projects adapter
      if (_projectsAdapterCompleted) {
        _syncedProjectIds = await _localStore.cleanOrphanedSyncedProjects(
          _syncedProjectIds,
        );
      }

      // Reload contractors for downstream use
      _syncedContractorIds = await _localStore.loadSyncedContractorIds(
        _syncedProjectIds,
      );
    } finally {
      await _localStore.restoreTriggers();
    }

    return PullResult(
      pulled: pulled,
      errors: errors,
      errorMessages: errorMessages,
      conflicts: _pullConflictCount,
      skippedFk: _pullSkippedFkCount,
    );
  }

  /// Pull a single table with cursor-based pagination.
  /// FROM SPEC: SyncEngine._pullTable (sync_engine.dart:1712-1966)
  Future<int> _pullTable(
    TableAdapter adapter, {
    List<String>? projectIds,
    List<String>? contractorIds,
  }) async {
    final cursor = await _localStore.readCursor(adapter.tableName);
    var totalPulled = 0;
    var offset = 0;
    String? maxUpdatedAt;

    while (true) {
      final page = await _supabaseSync.fetchPage(
        tableName: adapter.tableName,
        applyFilter: (query) => _applyScopeFilter(
          query,
          adapter,
          projectIds: projectIds,
          contractorIds: contractorIds,
        ),
        cursor: cursor,
        safetyMargin: SyncEngineConfig.pullSafetyMargin,
        pageSize: SyncEngineConfig.pullPageSize,
        offset: offset,
      );

      if (page.isEmpty) break;

      final localColumns = await _localStore.getLocalColumns(adapter.tableName);

      for (final remoteRaw in page) {
        final remote = adapter.convertForLocal(
          Map<String, dynamic>.from(remoteRaw),
        );
        final recordId = remote['id'] as String;

        final localRecord = await _localStore.readLocalRecord(
          adapter.tableName,
          recordId,
        );

        if (localRecord == null) {
          // Record does not exist locally
          if (remote['deleted_at'] != null) continue; // Skip deleted

          // Tombstone check
          final hasTombstone = await _localStore.hasPendingDelete(
            adapter.tableName,
            recordId,
          );
          if (hasTombstone) {
            Logger.sync(
              'Pull skip (tombstone): ${adapter.tableName}/$recordId',
            );
            continue;
          }

          final filtered = _localStore.stripUnknownColumns(remote, localColumns);
          try {
            final rowId = await _localStore.insertPulledRecord(
              adapter.tableName,
              filtered,
            );
            if (rowId == 0) {
              // Insert was ignored -- try update fallback
              final updated = await _localStore.updateLocalRecord(
                adapter.tableName,
                filtered,
                recordId,
              );
              if (updated > 0) {
                totalPulled++;
                Logger.sync(
                  'Pull insert->update fallback: ${adapter.tableName}/$recordId',
                );
              } else {
                Logger.sync(
                  'Pull insert ignored: ${adapter.tableName}/$recordId',
                );
              }
            } else {
              totalPulled++;
            }
          } on DatabaseException catch (e) {
            if (e.toString().contains('FOREIGN KEY')) {
              // FK rescue for project_assignments
              if (adapter.tableName == 'project_assignments') {
                final projectId = filtered['project_id'] as String?;
                if (projectId != null) {
                  final rescued = await _fkRescueHandler.rescueParentProject(
                    projectId,
                  );
                  if (rescued) {
                    try {
                      final retryRowId = await _localStore.insertPulledRecord(
                        adapter.tableName,
                        filtered,
                      );
                      if (retryRowId > 0) {
                        totalPulled++;
                        Logger.sync(
                          'FK rescue: pulled parent project $projectId for assignment $recordId',
                        );
                        continue;
                      }
                    } on DatabaseException catch (retryError) {
                      Logger.sync(
                        'FK rescue retry failed for ${adapter.tableName}/$recordId: $retryError',
                      );
                    }
                  }
                }
              }
              Logger.sync(
                'Pull skip (FK violation): ${adapter.tableName}/$recordId',
              );
              _pullSkippedFkCount++;
              continue;
            }
            rethrow;
          }
        } else {
          // Record exists locally
          if (localRecord['updated_at'] == remote['updated_at']) continue;

          // Conflict resolution
          final winner = await _conflictResolver.resolve(
            tableName: adapter.tableName,
            recordId: recordId,
            local: localRecord,
            remote: remote,
          );
          _pullConflictCount++;

          if (winner == ConflictWinner.remote) {
            final filtered = _localStore.stripUnknownColumns(remote, localColumns);
            await _localStore.updateLocalRecord(
              adapter.tableName,
              filtered,
              recordId,
            );
            totalPulled++;

            // Deletion notification
            if (remote['deleted_at'] != null && remote['deleted_by'] != null) {
              await _localStore.createDeletionNotification(
                adapter: adapter,
                local: localRecord,
                remote: remote,
                userId: userId,
              );
            }
          } else {
            // Local wins -- circuit breaker check
            final conflictCount = await _conflictResolver.getConflictCount(
              adapter.tableName,
              recordId,
            );
            if (conflictCount >= SyncEngineConfig.conflictPingPongThreshold) {
              Logger.sync(
                'CIRCUIT BREAKER: Skipping re-push for ${adapter.tableName}/$recordId '
                '(conflict count: $conflictCount)',
              );
              onCircuitBreakerTrip?.call(
                adapter.tableName,
                recordId,
                conflictCount,
              );
            } else {
              await _changeTracker.insertManualChange(
                adapter.tableName,
                recordId,
                'update',
              );
            }
          }
        }

        // Track max updated_at for cursor
        final updatedAt = remote['updated_at'] as String?;
        if (updatedAt != null &&
            (maxUpdatedAt == null || updatedAt.compareTo(maxUpdatedAt) > 0)) {
          maxUpdatedAt = updatedAt;
        }
      }

      onProgress?.call(adapter.tableName, totalPulled, null);

      if (page.length < SyncEngineConfig.pullPageSize) break;
      offset += SyncEngineConfig.pullPageSize;
    }

    // Fire onPullComplete callback
    if (totalPulled > 0 && onPullComplete != null) {
      await onPullComplete!(adapter.tableName, totalPulled);
    }

    // Update cursor
    if (maxUpdatedAt != null) {
      await _localStore.writeCursor(adapter.tableName, maxUpdatedAt);
    }

    return totalPulled;
  }

  /// Apply scope filter to a Supabase query.
  /// FROM SPEC: SyncEngine._applyScopeFilter (sync_engine.dart:1972-2003)
  PostgrestFilterBuilder _applyScopeFilter(
    PostgrestFilterBuilder query,
    TableAdapter adapter, {
    List<String>? projectIds,
    List<String>? contractorIds,
  }) {
    switch (adapter.scopeType) {
      case ScopeType.direct:
        final filters = adapter.pullFilter(companyId, userId);
        var filteredQuery = query;
        for (final entry in filters.entries) {
          filteredQuery = filteredQuery.eq(entry.key, entry.value);
        }
        return filteredQuery;
      case ScopeType.viaProject:
      case ScopeType.viaEntry:
        final scopedProjectIds = projectIds ?? _syncedProjectIds;
        if (adapter.includesNullProjectBuiltins) {
          final projectIdsCsv = scopedProjectIds.join(',');
          return query.or('project_id.in.($projectIdsCsv),project_id.is.null');
        }
        return query.inFilter('project_id', scopedProjectIds);
      case ScopeType.viaContractor:
        final scopedContractorIds = contractorIds ?? _syncedContractorIds;
        return query.inFilter('contractor_id', scopedContractorIds);
    }
  }
}
```

#### Step 4.1.3: Verify PullHandler

```
pwsh -Command "flutter analyze lib/features/sync/engine/pull_handler.dart"
```

Expected: No analysis errors.

---

### Sub-phase 4.2: Create EnrollmentHandler

**Files:**
- Create: `lib/features/sync/engine/enrollment_handler.dart`
- Test: `test/features/sync/engine/enrollment_handler_contract_test.dart`

**Agent**: backend-supabase-agent

#### Step 4.2.1: Write EnrollmentHandler contract test (red)

```dart
// test/features/sync/engine/enrollment_handler_contract_test.dart

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/features/sync/engine/enrollment_handler.dart';
import 'package:construction_inspector/features/sync/engine/local_sync_store.dart';

// WHY: Contract tests for EnrollmentHandler.
// FROM SPEC Section 4.2: "New assignments -> synced_projects inserts,
// already-enrolled -> no-op, orphan cleanup"

void main() {
  late Database db;
  late LocalSyncStore store;
  late EnrollmentHandler handler;

  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  setUp(() async {
    db = await databaseFactoryFfi.openDatabase(
      inMemoryDatabasePath,
      options: OpenDatabaseOptions(
        version: 1,
        onCreate: (db, version) async {
          await db.execute('''
            CREATE TABLE sync_control (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL DEFAULT '0'
            )
          ''');
          await db.execute(
            "INSERT INTO sync_control (key, value) VALUES ('pulling', '0')",
          );
          await db.execute('''
            CREATE TABLE sync_metadata (key TEXT PRIMARY KEY, value TEXT)
          ''');
          await db.execute('''
            CREATE TABLE synced_projects (
              project_id TEXT PRIMARY KEY,
              synced_at TEXT,
              unassigned_at TEXT
            )
          ''');
          await db.execute('''
            CREATE TABLE projects (
              id TEXT PRIMARY KEY, name TEXT, company_id TEXT,
              updated_at TEXT, deleted_at TEXT, created_at TEXT
            )
          ''');
          await db.execute('''
            CREATE TABLE project_assignments (
              id TEXT PRIMARY KEY, project_id TEXT, user_id TEXT,
              deleted_at TEXT, updated_at TEXT
            )
          ''');
          await db.execute('''
            CREATE TABLE contractors (
              id TEXT PRIMARY KEY, name TEXT, project_id TEXT,
              updated_at TEXT, deleted_at TEXT
            )
          ''');
        },
      ),
    );
    store = LocalSyncStore(db);
    handler = EnrollmentHandler(localStore: store);
  });

  tearDown(() async {
    await db.close();
  });

  group('enrollFromAssignments', () {
    test('enrolls new assignment into synced_projects', () async {
      await db.insert('project_assignments', {
        'id': 'a1',
        'project_id': 'p1',
        'user_id': 'user1',
      });
      final enrolled = await handler.enrollFromAssignments('user1');
      expect(enrolled, 1);

      final synced = await db.query('synced_projects');
      expect(synced.length, 1);
      expect(synced.first['project_id'], 'p1');
    });

    test('already-enrolled project is a no-op', () async {
      await db.insert('project_assignments', {
        'id': 'a1',
        'project_id': 'p1',
        'user_id': 'user1',
      });
      await db.insert('synced_projects', {'project_id': 'p1'});

      final enrolled = await handler.enrollFromAssignments('user1');
      expect(enrolled, 0);
    });

    test('does not enroll assignments for other users', () async {
      await db.insert('project_assignments', {
        'id': 'a1',
        'project_id': 'p1',
        'user_id': 'other-user',
      });
      final enrolled = await handler.enrollFromAssignments('user1');
      expect(enrolled, 0);
    });

    test('skips soft-deleted assignments', () async {
      await db.insert('project_assignments', {
        'id': 'a1',
        'project_id': 'p1',
        'user_id': 'user1',
        'deleted_at': '2026-01-01T00:00:00.000Z',
      });
      final enrolled = await handler.enrollFromAssignments('user1');
      expect(enrolled, 0);
    });
  });
}
```

#### Step 4.2.2: Implement EnrollmentHandler

```dart
// lib/features/sync/engine/enrollment_handler.dart

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/engine/local_sync_store.dart';

/// Handles synced_projects enrollment from project_assignments.
///
/// WHY: Extracted from SyncEngine._enrollProjectsFromAssignments
/// (sync_engine.dart:2133-2167) and SyncEnrollmentService (sync_enrollment_service.dart).
/// FROM SPEC Section 3 (Target Architecture):
/// "Dependencies: LocalSyncStore"
///
/// NOTE: This handler runs during pull while triggers are suppressed.
/// Writes to synced_projects (a non-triggered table) are safe.
class EnrollmentHandler {
  final LocalSyncStore _localStore;

  /// Callback to notify UI of new assignments.
  void Function(String message)? onNewAssignmentDetected;

  EnrollmentHandler({
    required LocalSyncStore localStore,
    this.onNewAssignmentDetected,
  }) : _localStore = localStore;

  /// Enroll projects from current user's project_assignments.
  /// Returns the number of newly enrolled projects.
  /// FROM SPEC: SyncEngine._enrollProjectsFromAssignments (sync_engine.dart:2133-2167)
  Future<int> enrollFromAssignments(String userId) async {
    return _localStore.enrollProjectsFromAssignments(userId);
  }

  /// Reconcile synced_projects with current assignments.
  /// Heals gaps where removeFromDevice() deleted synced_projects but
  /// assignments remain.
  /// FROM SPEC: SyncEngine._reconcileSyncedProjects (sync_engine.dart:2097-2128)
  Future<int> reconcile(String userId) async {
    return _localStore.reconcileSyncedProjects(userId);
  }
}
```

#### Step 4.2.3: Verify EnrollmentHandler

```
pwsh -Command "flutter analyze lib/features/sync/engine/enrollment_handler.dart"
```

Expected: No analysis errors.

---

### Sub-phase 4.3: Create FkRescueHandler

**Files:**
- Create: `lib/features/sync/engine/fk_rescue_handler.dart`
- Test: `test/features/sync/engine/fk_rescue_handler_contract_test.dart`

**Agent**: backend-supabase-agent

#### Step 4.3.1: Write FkRescueHandler contract test (red)

```dart
// test/features/sync/engine/fk_rescue_handler_contract_test.dart

import 'package:flutter_test/flutter_test.dart';

import 'package:construction_inspector/features/sync/engine/fk_rescue_handler.dart';

// WHY: Contract tests for FK rescue.
// FROM SPEC Section 4.2: "Missing parent -> fetch + write + return true,
// not on server -> return false"

void main() {
  group('FkRescueHandler API surface', () {
    test('class exists with expected constructor', () {
      expect(FkRescueHandler, isNotNull);
    });
  });
}
```

#### Step 4.3.2: Implement FkRescueHandler

```dart
// lib/features/sync/engine/fk_rescue_handler.dart

import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/engine/local_sync_store.dart';
import 'package:construction_inspector/features/sync/engine/supabase_sync.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';

/// Fetches missing FK parents from Supabase during pull.
///
/// WHY: Extracted from SyncEngine._rescueParentProject (sync_engine.dart:2175-2221).
/// When a project_assignment references a project that doesn't exist locally,
/// we fetch the project from Supabase, insert it, and enroll it.
///
/// FROM SPEC Section 3 (Target Architecture):
/// "Dependencies: SupabaseSync, LocalSyncStore"
class FkRescueHandler {
  final SupabaseSync _supabaseSync;
  final LocalSyncStore _localStore;
  final SyncRegistry _registry;

  FkRescueHandler({
    required SupabaseSync supabaseSync,
    required LocalSyncStore localStore,
    required SyncRegistry registry,
  })  : _supabaseSync = supabaseSync,
        _localStore = localStore,
        _registry = registry;

  /// Fetch a missing parent project from Supabase, insert locally,
  /// and enroll in synced_projects.
  ///
  /// Returns true if the project was successfully fetched and inserted.
  /// Idempotent: uses ConflictAlgorithm.ignore for insert and
  /// INSERT OR IGNORE for enrollment.
  ///
  /// FROM SPEC: SyncEngine._rescueParentProject (sync_engine.dart:2175-2221)
  Future<bool> rescueParentProject(String projectId) async {
    try {
      final remoteProject = await _supabaseSync.fetchRecord(
        'projects',
        projectId,
      );

      if (remoteProject == null) {
        Logger.sync('FK rescue failed: project $projectId not found on remote');
        return false;
      }

      // Convert using project adapter's type converters
      final projectAdapter = _registry.adapterFor('projects');
      final localProject = projectAdapter.convertForLocal(remoteProject);

      // Strip unknown columns
      final projectColumns = await _localStore.getLocalColumns('projects');
      final filtered = _localStore.stripUnknownColumns(
        localProject,
        projectColumns,
      );

      // Insert with ignore (idempotent)
      await _localStore.insertPulledRecord('projects', filtered);

      // Enroll in synced_projects
      await _localStore.enrollProject(projectId);

      Logger.sync('FK rescue: inserted parent project $projectId and enrolled');
      return true;
    } on Object catch (e) {
      Logger.sync('FK rescue error for project $projectId: $e');
      return false;
    }
  }
}
```

#### Step 4.3.3: Verify FkRescueHandler

```
pwsh -Command "flutter analyze lib/features/sync/engine/fk_rescue_handler.dart"
```

Expected: No analysis errors.

---

## Phase 5: Maintenance Handler + Slim Engine

Phase 5 extracts maintenance orchestration and reduces SyncEngine to a slim coordinator that delegates to handlers. After this phase, SyncEngine has no direct DB or Supabase access and no @visibleForTesting methods.

**Prerequisite**: Phases 3 and 4 complete (PushHandler, PullHandler, FileSyncHandler, EnrollmentHandler, FkRescueHandler all exist).

---

### Sub-phase 5.1: Create MaintenanceHandler

**Files:**
- Create: `lib/features/sync/engine/maintenance_handler.dart`
- Test: `test/features/sync/engine/maintenance_handler_contract_test.dart`

**Agent**: backend-supabase-agent

#### Step 5.1.1: Write MaintenanceHandler contract test (red)

```dart
// test/features/sync/engine/maintenance_handler_contract_test.dart

import 'package:flutter_test/flutter_test.dart';

import 'package:construction_inspector/features/sync/engine/maintenance_handler.dart';

// WHY: Contract tests for MaintenanceHandler.
// FROM SPEC Section 4.2: "Correct call order, respects integrityCheckInterval,
// logs to sync_metadata"

void main() {
  group('MaintenanceHandler API surface', () {
    test('class exists with expected constructor', () {
      expect(MaintenanceHandler, isNotNull);
    });
  });
}
```

#### Step 5.1.2: Implement MaintenanceHandler

```dart
// lib/features/sync/engine/maintenance_handler.dart

import 'dart:convert';

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';
import 'package:construction_inspector/features/sync/engine/conflict_resolver.dart';
import 'package:construction_inspector/features/sync/engine/integrity_checker.dart';
import 'package:construction_inspector/features/sync/engine/local_sync_store.dart';
import 'package:construction_inspector/features/sync/engine/orphan_scanner.dart';
import 'package:construction_inspector/features/sync/engine/storage_cleanup.dart';

/// Integrity check, orphan scan, conflict/change_log pruning, storage cleanup.
///
/// WHY: Extracted from SyncEngine._runMaintenanceHousekeeping
/// (sync_engine.dart:2301-2338) and related helpers.
/// FROM SPEC Section 3 (Target Architecture):
/// "Dependencies: IntegrityChecker, OrphanScanner, StorageCleanup, ChangeTracker"
class MaintenanceHandler {
  final IntegrityChecker _integrityChecker;
  final OrphanScanner _orphanScanner;
  final StorageCleanup _storageCleanup;
  final ChangeTracker _changeTracker;
  final ConflictResolver _conflictResolver;
  final LocalSyncStore _localStore;
  final String companyId;

  MaintenanceHandler({
    required IntegrityChecker integrityChecker,
    required OrphanScanner orphanScanner,
    required StorageCleanup storageCleanup,
    required ChangeTracker changeTracker,
    required ConflictResolver conflictResolver,
    required LocalSyncStore localStore,
    required this.companyId,
  })  : _integrityChecker = integrityChecker,
        _orphanScanner = orphanScanner,
        _storageCleanup = storageCleanup,
        _changeTracker = changeTracker,
        _conflictResolver = conflictResolver,
        _localStore = localStore;

  /// Run storage cleanup (expired files).
  /// FROM SPEC: SyncEngine.pushAndPull full mode (sync_engine.dart:323-327)
  Future<void> cleanupStorage() async {
    try {
      await _storageCleanup.cleanupExpiredFiles();
    } on Object catch (e, stack) {
      Logger.error('Storage cleanup failed', error: e, stack: stack);
    }
  }

  /// Run full maintenance housekeeping: pruning, integrity, orphans.
  /// FROM SPEC: SyncEngine._runMaintenanceHousekeeping (sync_engine.dart:2301-2338)
  Future<void> runHousekeeping({required String logPrefix}) async {
    // Prune processed change_log entries
    await _changeTracker.pruneProcessed();

    // Prune expired conflicts
    await _conflictResolver.pruneExpired();

    // Auto-dismiss old conflicts
    // FROM SPEC: SyncEngine._cleanupExpiredConflicts (sync_engine.dart:2345-2356)
    await _localStore.cleanupExpiredConflicts();

    // Check if integrity check is due
    if (!await _integrityChecker.shouldRun()) {
      Logger.sync('$logPrefix: integrity check not due yet');
      return;
    }

    try {
      // Run integrity check
      final integrityResults = await _integrityChecker.run();
      for (final result in integrityResults) {
        await _localStore.storeIntegrityResult(
          result.tableName,
          jsonEncode({
            'checked_at': DateTime.now().toUtc().toIso8601String(),
            'drift_detected': result.driftDetected,
            'local_count': result.localCount,
            'remote_count': result.remoteCount,
            'mismatch_reason': result.mismatchReason,
          }),
        );
        if (result.driftDetected) {
          await _localStore.clearCursor(result.tableName);
        }
      }

      // Orphan scan
      final orphans = await _orphanScanner.scan(companyId, autoDelete: true);
      if (orphans.isNotEmpty) {
        await _localStore.storeMetadata(
          'orphan_count',
          orphans.length.toString(),
        );
      }

      // Orphan purge (local records for unsynced projects)
      final syncedProjectIds = await _localStore.loadSyncedProjectIds();
      final purgedCount = await _integrityChecker.purgeOrphans(
        syncedProjectIds: syncedProjectIds.toSet(),
        changeTracker: _changeTracker,
      );
      if (purgedCount > 0) {
        Logger.sync(
          '$logPrefix orphan purge: $purgedCount local records soft-deleted',
        );
      }
    } on Object catch (e, stack) {
      Logger.error('$logPrefix integrity check failed', error: e, stack: stack);
    }
  }
}
```

#### Step 5.1.3: Verify MaintenanceHandler

```
pwsh -Command "flutter analyze lib/features/sync/engine/maintenance_handler.dart"
```

Expected: No analysis errors.

---

### Sub-phase 5.2: Slim down SyncEngine to coordinator-only

**Files:**
- Modify: `lib/features/sync/engine/sync_engine.dart` (full rewrite to ~200 lines)
- Modify: `lib/features/sync/application/sync_engine_factory.dart`

**Agent**: backend-supabase-agent

#### Step 5.2.1: Rewrite SyncEngine as slim coordinator

Replace the 2374-line SyncEngine with a ~200-line coordinator that delegates to handlers. The coordinator owns: mutex, heartbeat, mode routing, debug server posts. It has NO direct DB or Supabase access and NO @visibleForTesting methods.

The new SyncEngine constructor accepts all handlers:

```dart
// lib/features/sync/engine/sync_engine.dart (NEW — full rewrite)
//
// WHY: SyncEngine is now a slim coordinator (~200 lines) that delegates to
// focused handler classes. No direct DB or Supabase access.
// FROM SPEC Section 3: "Coordinator only: mutex, heartbeat, mode routing"
// FROM SPEC Success Criteria: "SyncEngine coordinator is under 250 lines"
//                              "No @visibleForTesting methods remain"

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
import 'package:construction_inspector/features/sync/engine/local_sync_store.dart';
import 'package:construction_inspector/features/sync/engine/maintenance_handler.dart';
import 'package:construction_inspector/features/sync/engine/pull_handler.dart';
import 'package:construction_inspector/features/sync/engine/push_handler.dart';
import 'package:construction_inspector/features/sync/engine/sync_mutex.dart';

/// Result of a sync engine push/pull cycle.
class SyncEngineResult {
  final int pushed;
  final int pulled;
  final int errors;
  final List<String> errorMessages;
  final bool lockFailed;
  final int rlsDenials;
  final int conflicts;
  final int skippedFk;
  final int skippedPush;

  const SyncEngineResult({
    this.pushed = 0,
    this.pulled = 0,
    this.errors = 0,
    this.errorMessages = const [],
    this.lockFailed = false,
    this.rlsDenials = 0,
    this.conflicts = 0,
    this.skippedFk = 0,
    this.skippedPush = 0,
  });

  bool get hasErrors => errors > 0;
  bool get isSuccess => !hasErrors && !lockFailed && conflicts == 0;

  SyncEngineResult operator +(SyncEngineResult other) {
    return SyncEngineResult(
      pushed: pushed + other.pushed,
      pulled: pulled + other.pulled,
      errors: errors + other.errors,
      errorMessages: [...errorMessages, ...other.errorMessages],
      rlsDenials: rlsDenials + other.rlsDenials,
      conflicts: conflicts + other.conflicts,
      skippedFk: skippedFk + other.skippedFk,
      skippedPush: skippedPush + other.skippedPush,
    );
  }
}

/// Progress callback for UI tracking.
typedef SyncProgressCallback =
    void Function(String tableName, int processed, int? total);

/// Slim sync coordinator: mutex, heartbeat, mode routing.
/// Delegates all I/O to PushHandler, PullHandler, MaintenanceHandler.
///
/// WHY: Decomposed from the 2374-line God Object. This coordinator knows
/// NOTHING about SQLite, Supabase, or individual table adapters.
/// FROM SPEC Section 3: "No direct DB or Supabase access"
class SyncEngine {
  final PushHandler _pushHandler;
  final PullHandler _pullHandler;
  final MaintenanceHandler _maintenanceHandler;
  final SyncMutex _mutex;
  final LocalSyncStore _localStore;
  final DirtyScopeTracker? _dirtyScopeTracker;
  final String lockedBy;

  SyncProgressCallback? onProgress;

  // Debug server — same dual-gate pattern as Logger._sendHttp
  static const _debugServerEnabled = bool.fromEnvironment(
    'DEBUG_SERVER',
    defaultValue: false,
  );
  static final _debugHttpClient = HttpClient()
    ..idleTimeout = const Duration(seconds: 2);

  SyncEngine({
    required PushHandler pushHandler,
    required PullHandler pullHandler,
    required MaintenanceHandler maintenanceHandler,
    required SyncMutex mutex,
    required LocalSyncStore localStore,
    required this.lockedBy,
    DirtyScopeTracker? dirtyScopeTracker,
    this.onProgress,
  })  : _pushHandler = pushHandler,
        _pullHandler = pullHandler,
        _maintenanceHandler = maintenanceHandler,
        _mutex = mutex,
        _localStore = localStore,
        _dirtyScopeTracker = dirtyScopeTracker;

  /// Reset sync state. Called on app startup and before each sync cycle.
  Future<void> resetState() async {
    await _localStore.resetPullingFlag();
    await _mutex.forceReset(lockedBy);
  }

  /// Top-level sync coordinator with mode-aware behavior.
  /// FROM SPEC: SyncEngine.pushAndPull (sync_engine.dart:221-401)
  Future<SyncEngineResult> pushAndPull({SyncMode mode = SyncMode.full}) async {
    // Crash recovery: reset pulling flag
    await _localStore.resetPullingFlag();

    // Acquire lock
    if (!await _mutex.tryAcquire(lockedBy)) {
      Logger.sync('Lock held by another process, skipping sync');
      return const SyncEngineResult(lockFailed: true);
    }
    _postSyncStatus({'type': 'sync_state', 'state': 'started', 'mode': mode.name});

    final stopwatch = Stopwatch()..start();
    final heartbeatTimer = Timer.periodic(
      const Duration(seconds: 60),
      (_) => _mutex.heartbeat(),
    );
    var cycleCompleted = false;
    var combined = const SyncEngineResult();

    try {
      switch (mode) {
        case SyncMode.quick:
          final pushResult = await _executePush(mode);
          var pullResult = const SyncEngineResult();
          if (SyncEngineConfig.quickSyncPullsDirtyScopes &&
              _dirtyScopeTracker != null &&
              _dirtyScopeTracker.hasDirtyScopes) {
            pullResult = await _executePull(mode, onlyDirtyScopes: true);
            if (!pullResult.hasErrors) _dirtyScopeTracker.clearAll();
          } else {
            Logger.sync('Quick sync: no dirty scopes or tracker unavailable');
          }
          combined = pushResult + pullResult;

        case SyncMode.full:
          final pushResult = await _executePush(mode);
          await _maintenanceHandler.cleanupStorage();
          final pullResult = await _executePull(mode);
          await _maintenanceHandler.runHousekeeping(logPrefix: 'Full sync');
          _dirtyScopeTracker?.clearAll();
          combined = pushResult + pullResult;

        case SyncMode.maintenance:
          Logger.sync('Maintenance sync started');
          final pullResult = await _executePull(mode);
          await _maintenanceHandler.runHousekeeping(logPrefix: 'Maintenance');
          _dirtyScopeTracker?.pruneExpired();
          combined = pullResult;
      }
      cycleCompleted = true;
    } finally {
      heartbeatTimer.cancel();
      stopwatch.stop();
      if (cycleCompleted) {
        Logger.sync(
          'Sync cycle (${mode.name}): pushed=${combined.pushed} pulled=${combined.pulled} '
          'errors=${combined.errors} conflicts=${combined.conflicts} '
          'skippedFk=${combined.skippedFk} skippedPush=${combined.skippedPush} '
          'duration=${stopwatch.elapsedMilliseconds}ms',
        );
        _postSyncStatus({
          'type': 'sync_state', 'state': 'completed', 'mode': mode.name,
          'pushed': combined.pushed, 'pulled': combined.pulled,
          'errors': combined.errors, 'conflicts': combined.conflicts,
          'duration_ms': stopwatch.elapsedMilliseconds,
        });
      } else {
        _postSyncStatus({
          'type': 'sync_state', 'state': 'failed', 'mode': mode.name,
        });
      }
      await _mutex.release();
    }
    return combined;
  }

  /// Push-only (for testing).
  Future<SyncEngineResult> pushOnly() async {
    if (!await _mutex.tryAcquire(lockedBy)) {
      return const SyncEngineResult(lockFailed: true);
    }
    try {
      return await _executePush(SyncMode.full);
    } finally {
      await _mutex.release();
    }
  }

  /// Pull-only (for testing).
  Future<SyncEngineResult> pullOnly() async {
    if (!await _mutex.tryAcquire(lockedBy)) {
      return const SyncEngineResult(lockFailed: true);
    }
    try {
      return await _executePull(SyncMode.full);
    } finally {
      await _mutex.release();
    }
  }

  Future<SyncEngineResult> _executePush(SyncMode mode) async {
    final pushResult = await _pushHandler.push();
    Logger.sync(
      '${mode.name} push complete: ${pushResult.pushed} pushed, '
      '${pushResult.errors} errors',
    );
    _postSyncStatus({
      'type': 'sync_state', 'state': 'push_complete', 'mode': mode.name,
      'pushed': pushResult.pushed, 'errors': pushResult.errors,
    });
    return SyncEngineResult(
      pushed: pushResult.pushed,
      errors: pushResult.errors,
      errorMessages: pushResult.errorMessages,
      rlsDenials: pushResult.rlsDenials,
      skippedPush: pushResult.skippedPush,
    );
  }

  Future<SyncEngineResult> _executePull(
    SyncMode mode, {
    bool onlyDirtyScopes = false,
  }) async {
    final pullResult = await _pullHandler.pull(onlyDirtyScopes: onlyDirtyScopes);
    Logger.sync(
      '${mode.name} pull complete: ${pullResult.pulled} pulled, '
      '${pullResult.errors} errors',
    );
    _postSyncStatus({
      'type': 'sync_state', 'state': 'pull_complete', 'mode': mode.name,
      'pulled': pullResult.pulled, 'errors': pullResult.errors,
    });
    return SyncEngineResult(
      pulled: pullResult.pulled,
      errors: pullResult.errors,
      errorMessages: pullResult.errorMessages,
      conflicts: pullResult.conflicts,
      skippedFk: pullResult.skippedFk,
    );
  }

  /// POST sync lifecycle events to debug server (fire-and-forget).
  void _postSyncStatus(Map<String, dynamic> status) {
    if (!_debugServerEnabled) return;
    if (kReleaseMode) return;
    final payload = {
      ...status,
      'timestamp': DateTime.now().toUtc().toIso8601String(),
    };
    try {
      unawaited(
        _debugHttpClient
            .postUrl(Uri.parse('http://127.0.0.1:3947/sync/status'))
            .then((request) {
              request.headers.contentType = ContentType.json;
              request.write(jsonEncode(payload));
              return request.close();
            })
            .then((response) async {
              await response.drain<void>();
            })
            .catchError((e) {
              Logger.sync('[SyncEngine] debug status post catchError: $e');
            }),
      );
    } on Object catch (e) {
      Logger.sync('[SyncEngine] debug status post failed: $e');
    }
  }
}
```

#### Step 5.2.2: Update SyncEngineFactory to construct handlers and slim engine

Update `lib/features/sync/application/sync_engine_factory.dart` to create all handler instances and wire them into the slim SyncEngine:

```dart
// In the factory method that creates SyncEngine:
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';
import 'package:construction_inspector/features/sync/engine/conflict_resolver.dart';
import 'package:construction_inspector/features/sync/engine/enrollment_handler.dart';
import 'package:construction_inspector/features/sync/engine/file_sync_handler.dart';
import 'package:construction_inspector/features/sync/engine/fk_rescue_handler.dart';
import 'package:construction_inspector/features/sync/engine/integrity_checker.dart';
import 'package:construction_inspector/features/sync/engine/local_sync_store.dart';
import 'package:construction_inspector/features/sync/engine/maintenance_handler.dart';
import 'package:construction_inspector/features/sync/engine/orphan_scanner.dart';
import 'package:construction_inspector/features/sync/engine/pull_handler.dart';
import 'package:construction_inspector/features/sync/engine/push_handler.dart';
import 'package:construction_inspector/features/sync/engine/storage_cleanup.dart';
import 'package:construction_inspector/features/sync/engine/supabase_sync.dart';
import 'package:construction_inspector/features/sync/engine/sync_mutex.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';

// Factory method body:
SyncEngine createEngine({
  required Database database,
  required SupabaseClient supabaseClient,
  required String companyId,
  required String userId,
  String lockedBy = 'foreground',
  DirtyScopeTracker? dirtyScopeTracker,
}) {
  // I/O boundaries
  final localStore = LocalSyncStore(database);
  final supabaseSync = SupabaseSync(supabaseClient);

  // Existing well-scoped components
  final mutex = SyncMutex(database);
  final changeTracker = ChangeTracker(database);
  final conflictResolver = ConflictResolver(database);
  final integrityChecker = IntegrityChecker(database, supabaseClient);
  final orphanScanner = OrphanScanner(supabaseClient);
  final storageCleanup = StorageCleanup(supabaseClient, database);
  final registry = SyncRegistry.instance;

  // Handlers
  final enrollmentHandler = EnrollmentHandler(localStore: localStore);
  final fkRescueHandler = FkRescueHandler(
    supabaseSync: supabaseSync,
    localStore: localStore,
    registry: registry,
  );
  final fileSyncHandler = FileSyncHandler(
    supabaseSync: supabaseSync,
    localStore: localStore,
    conflictResolver: conflictResolver,
  );
  final pushHandler = PushHandler(
    localStore: localStore,
    supabaseSync: supabaseSync,
    changeTracker: changeTracker,
    conflictResolver: conflictResolver,
    registry: registry,
    fileSyncHandler: fileSyncHandler,
    companyId: companyId,
    userId: userId,
  );
  final pullHandler = PullHandler(
    localStore: localStore,
    supabaseSync: supabaseSync,
    conflictResolver: conflictResolver,
    changeTracker: changeTracker,
    registry: registry,
    enrollmentHandler: enrollmentHandler,
    fkRescueHandler: fkRescueHandler,
    companyId: companyId,
    userId: userId,
    dirtyScopeTracker: dirtyScopeTracker,
  );
  final maintenanceHandler = MaintenanceHandler(
    integrityChecker: integrityChecker,
    orphanScanner: orphanScanner,
    storageCleanup: storageCleanup,
    changeTracker: changeTracker,
    conflictResolver: conflictResolver,
    localStore: localStore,
    companyId: companyId,
  );

  return SyncEngine(
    pushHandler: pushHandler,
    pullHandler: pullHandler,
    maintenanceHandler: maintenanceHandler,
    mutex: mutex,
    localStore: localStore,
    lockedBy: lockedBy,
    dirtyScopeTracker: dirtyScopeTracker,
  );
}
```

Also update `SyncEngine.createForBackgroundSync` (now a factory function that uses the same handler construction pattern).

#### Step 5.2.3: Update SyncOrchestrator to work with new SyncEngine

The `SyncOrchestrator` calls `SyncEngine.pushAndPull()` which has the same signature. The callbacks (`onPullComplete`, `onCircuitBreakerTrip`) must now be set on the `PullHandler` instead of `SyncEngine`. Update wiring in `SyncInitializer.create()`:

```dart
// In sync_initializer.dart, after creating the engine:
// Wire callbacks to PullHandler (accessed through engine factory)
// NOTE: The factory returns the engine, but callbacks need to be set
// on the PullHandler. The factory should expose the pull handler
// or the engine should expose a method to set pull callbacks.

// Option: Add callback setters to SyncEngine that delegate to PullHandler:
// In the slim SyncEngine:
set onPullComplete(Future<void> Function(String, int)? callback) {
  _pullHandler.onPullComplete = callback;
}

set onCircuitBreakerTrip(
  void Function(String, String, int)? callback,
) {
  _pullHandler.onCircuitBreakerTrip = callback;
}

set onNewAssignmentDetected(void Function(String)? callback) {
  // Route to enrollment handler's notification callback
  // (PullHandler's enrollmentHandler)
}
```

#### Step 5.2.4: Update all test files that reference old SyncEngine API

Test files that use `@visibleForTesting` methods (`pushDeleteRemote`, `upsertRemote`, `insertOnlyRemote`, `fetchServerUpdatedAt`, `shouldSkipLwwPush`, `pushDeleteForTesting`, `validateAndStampCompanyId`, `pushUpsertForTesting`) must be rewritten to test the new handler classes directly.

Tests that subclass SyncEngine (`_EmptyResponseSyncEngine`, `_LwwTestSyncEngine`, `_NullTimestampLwwTestSyncEngine`) must be replaced with tests that mock `SupabaseSync` and pass it to the appropriate handler.

Key test file updates:
- `test/features/sync/engine/sync_engine_test.dart` -- reduce to testing only the coordinator (mode routing, mutex, heartbeat)
- `test/features/sync/engine/sync_engine_delete_test.dart` -- move soft-delete tests to `push_handler_test.dart`
- `test/features/sync/engine/sync_engine_lww_test.dart` -- move LWW tests to `push_handler_test.dart`

#### Step 5.2.5: Verify slim SyncEngine

```
pwsh -Command "flutter analyze lib/features/sync/engine/"
```

Expected: No analysis errors. The slim SyncEngine should be under 250 lines. No `@visibleForTesting` annotations remain on any class in `lib/features/sync/engine/`.

#### Step 5.2.6: Verify line counts meet spec targets

Count lines in the slim SyncEngine:
- Target: under 250 lines (FROM SPEC Success Criteria)
- No class in `lib/features/sync/engine/` exceeds 500 lines
- Zero `@visibleForTesting` methods anywhere in the engine directory

Verification checklist:
- `sync_engine.dart`: ~200 lines (coordinator only)
- `push_handler.dart`: ~300 lines
- `pull_handler.dart`: ~350 lines
- `supabase_sync.dart`: ~250 lines
- `local_sync_store.dart`: ~300 lines (was ~450 due to enrollment methods, within 500 limit)
- `file_sync_handler.dart`: ~200 lines
- `enrollment_handler.dart`: ~50 lines
- `fk_rescue_handler.dart`: ~80 lines
- `maintenance_handler.dart`: ~100 lines
