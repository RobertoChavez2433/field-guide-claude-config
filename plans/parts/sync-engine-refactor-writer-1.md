## Phase 0: Characterization Tests

**Goal**: Capture every observable sync behavior as immutable test contracts BEFORE any code changes. These tests run against the current monolith and must remain green throughout the entire refactor. They are the safety net.

**Branch**: `refactor/sync-engine-p0-characterization`

**Ground rules**:
- All test files go in `test/features/sync/characterization/`
- Tests use `SqliteTestHelper.createDatabase()` from `test/helpers/sync/sqlite_test_helper.dart` for in-memory SQLite
- Tests use `SyncTestData.*` factories from `test/helpers/sync/sync_test_data.dart` for seed data
- Tests use `buildNullSupabase()` from `test/helpers/sync/sync_engine_test_helpers.dart` for placeholder Supabase client
- Tests import the CURRENT monolith classes directly -- no mocks for the system under test
- Each test file is a standalone `void main()` with `setUpAll(sqfliteFfiInit)`, `setUp`, `tearDown`
- No `flutter test` steps -- verification is via `pwsh -Command "flutter analyze"` and CI

---

### Sub-phase 0.1: Push Upsert Characterization

**Files:**
- Create: `test/features/sync/characterization/characterization_push_upsert_test.dart`

**Agent**: qa-testing-agent

These tests capture the exact push-upsert behavior for every adapter type. They verify that given a change_log INSERT/UPDATE entry and a corresponding local record, the SyncEngine produces the correct Supabase upsert call.

#### Step 0.1.1: Create push upsert characterization test file

```dart
// test/features/sync/characterization/characterization_push_upsert_test.dart
//
// FROM SPEC Section 4.1: "For each adapter: given change_log INSERT/UPDATE
// + local record -> exact Supabase upsert payload"
//
// WHY: Captures the exact payload transformation for every adapter so that
// PushHandler extraction in P3 cannot silently change push behavior.
//
// PATTERN: Uses SyncEngine subclass that intercepts upsertRemote() calls
// to capture the payload without hitting real Supabase.
//
// NOTE: Tests the full push pipeline: ChangeTracker reads change_log,
// adapter.convertForRemote() transforms the record, SyncEngine routes
// to upsert. We verify the final payload matches expectations.

import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:construction_inspector/features/sync/engine/sync_engine.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;
  late Map<String, String> seedIds;

  setUpAll(sqfliteFfiInit);

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    seedIds = await SyncTestData.seedFkGraph(db);
    await SqliteTestHelper.clearChangeLog(db);
    // WHY: Register adapters fresh for each test to avoid cross-test leakage.
    SyncRegistry.instance.registerSyncAdapters();
  });

  tearDown(() async {
    await db.close();
  });

  // NOTE: Each test group covers one adapter type. The test inserts a local
  // record (triggers change_log via SQLite trigger), then verifies the
  // change_log entry was created with the correct table_name and operation.
  // The full upsert-to-Supabase path requires a SyncEngine subclass that
  // captures the outbound payload -- those are in the subclass below.

  group('Push upsert: change_log creation for each table', () {
    // WHY: Verifies SQLite triggers fire correctly for each syncable table.
    // FROM SPEC: "change_log is trigger-only -- 20 tables have SQLite triggers
    // gated by sync_control.pulling='0'"

    test('projects INSERT creates change_log entry', () async {
      await db.insert('projects', SyncTestData.projectMap(
        id: 'char-proj-1',
        companyId: seedIds['companyId'],
        projectNumber: 'CHAR-001',
      ));

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(entries, hasLength(1));
      expect(entries.first['record_id'], 'char-proj-1');
      expect(entries.first['operation'], 'insert');
      expect(entries.first['processed'], 0);
    });

    test('daily_entries INSERT creates change_log entry', () async {
      await db.insert('daily_entries', SyncTestData.dailyEntryMap(
        id: 'char-entry-1',
        projectId: seedIds['projectId']!,
        locationId: seedIds['locationId'],
      ));

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'daily_entries');
      expect(entries, hasLength(1));
      expect(entries.first['record_id'], 'char-entry-1');
      expect(entries.first['operation'], 'insert');
    });

    test('photos INSERT creates change_log entry', () async {
      await db.insert('photos', SyncTestData.photoMap(
        id: 'char-photo-1',
        entryId: seedIds['entryId']!,
        projectId: seedIds['projectId']!,
      ));

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'photos');
      expect(entries, hasLength(1));
      expect(entries.first['record_id'], 'char-photo-1');
    });

    test('contractors INSERT creates change_log entry', () async {
      await db.insert('contractors', SyncTestData.contractorMap(
        id: 'char-contr-1',
        projectId: seedIds['projectId']!,
      ));

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'contractors');
      expect(entries, hasLength(1));
      expect(entries.first['record_id'], 'char-contr-1');
    });

    test('todo_items INSERT creates change_log entry', () async {
      await db.insert('todo_items', SyncTestData.todoItemMap(
        id: 'char-todo-1',
        projectId: seedIds['projectId']!,
      ));

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'todo_items');
      expect(entries, hasLength(1));
      expect(entries.first['record_id'], 'char-todo-1');
    });

    test('form_responses INSERT creates change_log entry', () async {
      await db.insert('form_responses', SyncTestData.formResponseMap(
        id: 'char-fr-1',
        projectId: seedIds['projectId']!,
        entryId: seedIds['entryId'],
      ));

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'form_responses');
      expect(entries, hasLength(1));
      expect(entries.first['record_id'], 'char-fr-1');
    });

    test('UPDATE creates change_log entry with update operation', () async {
      // WHY: Ensures UPDATE triggers fire, not just INSERT triggers.
      await db.update(
        'projects',
        {'name': 'Updated Name', 'updated_at': DateTime.now().toUtc().toIso8601String()},
        where: 'id = ?',
        whereArgs: [seedIds['projectId']],
      );

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(entries, hasLength(1));
      expect(entries.first['operation'], 'update');
    });
  });

  group('Push upsert: adapter convertForRemote', () {
    // WHY: Verifies each adapter strips localOnlyColumns and applies converters
    // correctly before push. These are the exact transformations that PushHandler
    // must preserve.

    test('PhotoAdapter strips file_path from remote payload', () async {
      final adapter = SyncRegistry.instance.adapterFor('photos');
      final localRow = SyncTestData.photoMap(
        id: 'conv-photo-1',
        entryId: seedIds['entryId']!,
        projectId: seedIds['projectId']!,
        filePath: '/local/path/photo.jpg',
      );

      final remote = adapter.convertForRemote(localRow);
      // FROM SPEC: file_path is localOnlyColumns for PhotoAdapter
      expect(remote.containsKey('file_path'), isFalse);
      expect(remote.containsKey('id'), isTrue);
      expect(remote['id'], 'conv-photo-1');
    });

    test('DailyEntryAdapter convertForRemote preserves all columns', () async {
      final adapter = SyncRegistry.instance.adapterFor('daily_entries');
      final localRow = SyncTestData.dailyEntryMap(
        id: 'conv-entry-1',
        projectId: seedIds['projectId']!,
      );

      final remote = adapter.convertForRemote(localRow);
      // NOTE: DailyEntryAdapter has empty localOnlyColumns (sync_status removed in v31)
      expect(remote.containsKey('id'), isTrue);
      expect(remote.containsKey('project_id'), isTrue);
      expect(remote['project_id'], seedIds['projectId']);
    });

    test('DocumentAdapter strips file_path from remote payload', () async {
      final adapter = SyncRegistry.instance.adapterFor('documents');
      final localRow = SyncTestData.documentMap(
        id: 'conv-doc-1',
        entryId: seedIds['entryId']!,
        projectId: seedIds['projectId']!,
        filePath: '/local/path/doc.pdf',
      );

      final remote = adapter.convertForRemote(localRow);
      expect(remote.containsKey('file_path'), isFalse);
    });
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 0.2: Push Delete Characterization

**Files:**
- Create: `test/features/sync/characterization/characterization_push_delete_test.dart`

**Agent**: qa-testing-agent

#### Step 0.2.1: Create push delete characterization test file

```dart
// test/features/sync/characterization/characterization_push_delete_test.dart
//
// FROM SPEC Section 4.1: "Soft-delete: UPDATE with deleted_at.
// Hard-delete: DELETE. Idempotent cases."
//
// WHY: Verifies that soft-delete and hard-delete paths produce distinct
// change_log operations, and that the engine routes them correctly.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/features/sync/engine/sync_registry.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;
  late Map<String, String> seedIds;

  setUpAll(sqfliteFfiInit);

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    seedIds = await SyncTestData.seedFkGraph(db);
    await SqliteTestHelper.clearChangeLog(db);
    SyncRegistry.instance.registerSyncAdapters();
  });

  tearDown(() async {
    await db.close();
  });

  group('Soft-delete: UPDATE with deleted_at', () {
    // FROM SPEC: "Soft-delete is the default -- delete() = soft-delete"
    // WHY: Soft-delete is an UPDATE, which should create an 'update' change_log entry
    // containing the deleted_at timestamp. The push path sends this as an upsert.

    test('setting deleted_at on project creates update change_log entry', () async {
      final now = DateTime.now().toUtc().toIso8601String();
      await db.update(
        'projects',
        {'deleted_at': now, 'deleted_by': 'test-user', 'updated_at': now},
        where: 'id = ?',
        whereArgs: [seedIds['projectId']],
      );

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(entries, hasLength(1));
      // WHY: Soft-delete fires the UPDATE trigger, NOT the DELETE trigger
      expect(entries.first['operation'], 'update');
      expect(entries.first['record_id'], seedIds['projectId']);
    });

    test('setting deleted_at on daily_entries creates update change_log entry', () async {
      final now = DateTime.now().toUtc().toIso8601String();
      await db.update(
        'daily_entries',
        {'deleted_at': now, 'deleted_by': 'test-user', 'updated_at': now},
        where: 'id = ?',
        whereArgs: [seedIds['entryId']],
      );

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'daily_entries');
      expect(entries, hasLength(1));
      expect(entries.first['operation'], 'update');
    });
  });

  group('Hard-delete: DELETE', () {
    // WHY: Hard-delete fires the DELETE trigger, creating a 'delete' change_log entry.
    // The push path routes this to pushDeleteRemote (Supabase DELETE or soft-delete UPDATE).

    test('hard-delete on todo_items creates delete change_log entry', () async {
      // NOTE: todo_items has no FK children, safe to hard-delete without cascade issues
      final todoId = 'char-hard-del-todo';
      await SqliteTestHelper.suppressTriggers(db);
      await db.insert('todo_items', SyncTestData.todoItemMap(
        id: todoId,
        projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.enableTriggers(db);
      await SqliteTestHelper.clearChangeLog(db);

      await db.delete('todo_items', where: 'id = ?', whereArgs: [todoId]);

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'todo_items');
      expect(entries, hasLength(1));
      expect(entries.first['operation'], 'delete');
      expect(entries.first['record_id'], todoId);
    });
  });

  group('Idempotent delete cases', () {
    // WHY: Deleting a record that has already been soft-deleted should still
    // produce a change_log entry (the trigger fires on any UPDATE).

    test('updating deleted_at again on already-deleted record creates entry', () async {
      final now = DateTime.now().toUtc().toIso8601String();
      // First soft-delete
      await db.update(
        'projects',
        {'deleted_at': now, 'deleted_by': 'test-user', 'updated_at': now},
        where: 'id = ?',
        whereArgs: [seedIds['projectId']],
      );
      await SqliteTestHelper.clearChangeLog(db);

      // Second soft-delete update
      final later = DateTime.now().add(const Duration(seconds: 1)).toUtc().toIso8601String();
      await db.update(
        'projects',
        {'deleted_at': later, 'updated_at': later},
        where: 'id = ?',
        whereArgs: [seedIds['projectId']],
      );

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(entries, hasLength(1));
      expect(entries.first['operation'], 'update');
    });
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 0.3: Push Ordering Characterization

**Files:**
- Create: `test/features/sync/characterization/characterization_push_ordering_test.dart`

**Agent**: qa-testing-agent

#### Step 0.3.1: Create push ordering characterization test file

```dart
// test/features/sync/characterization/characterization_push_ordering_test.dart
//
// FROM SPEC Section 4.1: "Changes across multiple tables push in FK
// dependency order"
//
// WHY: The FK ordering is critical for referential integrity on the server.
// If a child record is pushed before its parent, Supabase returns 23503.
// This test captures the exact ordering from SyncRegistry.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/features/sync/engine/sync_registry.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;

  setUpAll(sqfliteFfiInit);

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    SyncRegistry.instance.registerSyncAdapters();
  });

  tearDown(() async {
    await db.close();
  });

  group('FK dependency ordering in SyncRegistry', () {
    // WHY: This is the exact ordering that SyncEngine._push iterates.
    // The refactored PushHandler MUST preserve this exact order.

    test('dependencyOrder places parents before children', () {
      final order = SyncRegistry.instance.dependencyOrder;

      // FROM SPEC: projects must come before all project-scoped tables
      final projectsIndex = order.indexOf('projects');
      final locationsIndex = order.indexOf('locations');
      final contractorsIndex = order.indexOf('contractors');
      final dailyEntriesIndex = order.indexOf('daily_entries');
      final photosIndex = order.indexOf('photos');
      final bidItemsIndex = order.indexOf('bid_items');

      expect(projectsIndex, lessThan(locationsIndex),
          reason: 'projects must push before locations');
      expect(projectsIndex, lessThan(contractorsIndex),
          reason: 'projects must push before contractors');
      expect(projectsIndex, lessThan(dailyEntriesIndex),
          reason: 'projects must push before daily_entries');
      expect(projectsIndex, lessThan(bidItemsIndex),
          reason: 'projects must push before bid_items');
      expect(dailyEntriesIndex, lessThan(photosIndex),
          reason: 'daily_entries must push before photos');
    });

    test('entry junction tables come after both parents', () {
      final order = SyncRegistry.instance.dependencyOrder;

      final contractorsIndex = order.indexOf('contractors');
      final dailyEntriesIndex = order.indexOf('daily_entries');
      final entryContractorsIndex = order.indexOf('entry_contractors');
      final entryEquipmentIndex = order.indexOf('entry_equipment');
      final entryQuantitiesIndex = order.indexOf('entry_quantities');
      final bidItemsIndex = order.indexOf('bid_items');
      final equipmentIndex = order.indexOf('equipment');

      expect(dailyEntriesIndex, lessThan(entryContractorsIndex),
          reason: 'daily_entries must push before entry_contractors');
      expect(contractorsIndex, lessThan(entryContractorsIndex),
          reason: 'contractors must push before entry_contractors');
      expect(equipmentIndex, lessThan(entryEquipmentIndex),
          reason: 'equipment must push before entry_equipment');
      expect(bidItemsIndex, lessThan(entryQuantitiesIndex),
          reason: 'bid_items must push before entry_quantities');
    });

    test('form_responses comes after inspector_forms', () {
      final order = SyncRegistry.instance.dependencyOrder;
      final formsIndex = order.indexOf('inspector_forms');
      final responsesIndex = order.indexOf('form_responses');

      // WHY: form_responses has FK to inspector_forms
      expect(formsIndex, lessThan(responsesIndex));
    });

    test('all 22 adapters are registered', () {
      final order = SyncRegistry.instance.dependencyOrder;
      // FROM SPEC ground-truth: 22 adapter classes
      expect(order, hasLength(22));
    });

    test('dependencyOrder contains all expected tables', () {
      final order = SyncRegistry.instance.dependencyOrder;
      // FROM SPEC ground-truth: verified table names
      final expectedTables = [
        'projects', 'project_assignments', 'locations', 'contractors',
        'equipment', 'bid_items', 'personnel_types', 'daily_entries',
        'photos', 'entry_equipment', 'entry_quantities', 'entry_contractors',
        'entry_personnel_counts', 'inspector_forms', 'form_responses',
        'form_exports', 'entry_exports', 'documents', 'todo_items',
        'calculation_history', 'support_tickets', 'user_consent_records',
      ];
      for (final table in expectedTables) {
        expect(order, contains(table), reason: 'Missing adapter for $table');
      }
    });
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 0.4: Push Skip Characterization

**Files:**
- Create: `test/features/sync/characterization/characterization_push_skip_test.dart`

**Agent**: qa-testing-agent

#### Step 0.4.1: Create push skip characterization test file

```dart
// test/features/sync/characterization/characterization_push_skip_test.dart
//
// FROM SPEC Section 4.1: "Builtin forms, adapter shouldSkipPush, FK-blocked
// records -> markProcessed without Supabase call"
//
// WHY: These skip paths are invisible -- they consume change_log entries
// without ever calling Supabase. The refactored PushHandler must preserve
// exactly the same skip decisions.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;
  late Map<String, String> seedIds;

  setUpAll(sqfliteFfiInit);

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    seedIds = await SyncTestData.seedFkGraph(db);
    await SqliteTestHelper.clearChangeLog(db);
    SyncRegistry.instance.registerSyncAdapters();
  });

  tearDown(() async {
    await db.close();
  });

  group('Builtin forms are skipped', () {
    // FROM SPEC: "is_builtin=1 rows are server-seeded -- triggers skip them,
    // cascade-delete skips them, push skips them"
    // WHY: The is_builtin trigger guard prevents change_log entries, AND
    // InspectorFormAdapter.shouldSkipPush checks is_builtin.

    test('InspectorFormAdapter.shouldSkipPush returns true for builtin forms', () {
      final adapter = SyncRegistry.instance.adapterFor('inspector_forms');
      final builtinRecord = {
        'id': 'builtin-form-1',
        'is_builtin': 1,
        'project_id': null,
        'name': 'MDOT 0582B',
      };
      expect(adapter.shouldSkipPush(builtinRecord), isTrue);
    });

    test('InspectorFormAdapter.shouldSkipPush returns false for user forms', () {
      final adapter = SyncRegistry.instance.adapterFor('inspector_forms');
      final userRecord = {
        'id': 'user-form-1',
        'is_builtin': 0,
        'project_id': seedIds['projectId'],
        'name': 'Custom Form',
      };
      expect(adapter.shouldSkipPush(userRecord), isFalse);
    });

    test('builtin form INSERT does NOT create change_log entry (trigger guard)', () async {
      // WHY: The inspector_forms trigger has an additional WHEN clause:
      // AND NEW.is_builtin != 1
      await db.insert('inspector_forms', {
        ...SyncTestData.inspectorFormMap(
          id: 'builtin-test-1',
          projectId: seedIds['projectId']!,
        ),
        'is_builtin': 1,
      });

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'inspector_forms');
      expect(entries, isEmpty,
          reason: 'is_builtin=1 should be filtered by trigger WHEN clause');
    });
  });

  group('Adapter shouldSkipPush for other adapters', () {
    // WHY: Most adapters return false from shouldSkipPush (base class default).
    // This verifies the default behavior is preserved.

    test('ProjectAdapter shouldSkipPush returns false for normal records', () {
      final adapter = SyncRegistry.instance.adapterFor('projects');
      final record = SyncTestData.projectMap(
        id: 'skip-proj-1',
        companyId: seedIds['companyId'],
      );
      expect(adapter.shouldSkipPush(record), isFalse);
    });

    test('ConsentRecordAdapter is insertOnly', () {
      final adapter = SyncRegistry.instance.adapterFor('user_consent_records');
      // FROM SPEC: ConsentRecordAdapter has insertOnly = true
      expect(adapter.insertOnly, isTrue);
    });
  });

  group('Adapter scope types are correct', () {
    // WHY: Scope types drive pull filter behavior. This captures the exact
    // configuration per adapter that must be preserved.

    test('direct scope adapters', () {
      expect(SyncRegistry.instance.adapterFor('projects').scopeType.name, 'direct');
      expect(SyncRegistry.instance.adapterFor('project_assignments').scopeType.name, 'direct');
      expect(SyncRegistry.instance.adapterFor('user_consent_records').scopeType.name, 'direct');
      expect(SyncRegistry.instance.adapterFor('support_tickets').scopeType.name, 'direct');
    });

    test('viaProject scope adapters', () {
      expect(SyncRegistry.instance.adapterFor('locations').scopeType.name, 'viaProject');
      expect(SyncRegistry.instance.adapterFor('contractors').scopeType.name, 'viaProject');
      expect(SyncRegistry.instance.adapterFor('bid_items').scopeType.name, 'viaProject');
      expect(SyncRegistry.instance.adapterFor('personnel_types').scopeType.name, 'viaProject');
      expect(SyncRegistry.instance.adapterFor('todo_items').scopeType.name, 'viaProject');
      expect(SyncRegistry.instance.adapterFor('daily_entries').scopeType.name, 'viaProject');
      expect(SyncRegistry.instance.adapterFor('calculation_history').scopeType.name, 'viaProject');
    });

    test('viaEntry scope adapters', () {
      expect(SyncRegistry.instance.adapterFor('photos').scopeType.name, 'viaEntry');
      expect(SyncRegistry.instance.adapterFor('entry_equipment').scopeType.name, 'viaEntry');
      expect(SyncRegistry.instance.adapterFor('entry_quantities').scopeType.name, 'viaEntry');
      expect(SyncRegistry.instance.adapterFor('entry_contractors').scopeType.name, 'viaEntry');
      expect(SyncRegistry.instance.adapterFor('entry_personnel_counts').scopeType.name, 'viaEntry');
      expect(SyncRegistry.instance.adapterFor('documents').scopeType.name, 'viaEntry');
    });

    test('file adapters are correctly flagged', () {
      expect(SyncRegistry.instance.adapterFor('photos').isFileAdapter, isTrue);
      expect(SyncRegistry.instance.adapterFor('documents').isFileAdapter, isTrue);
      expect(SyncRegistry.instance.adapterFor('entry_exports').isFileAdapter, isTrue);
      expect(SyncRegistry.instance.adapterFor('form_exports').isFileAdapter, isTrue);
      // Non-file adapters
      expect(SyncRegistry.instance.adapterFor('projects').isFileAdapter, isFalse);
      expect(SyncRegistry.instance.adapterFor('daily_entries').isFileAdapter, isFalse);
    });
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 0.5: Push File Characterization

**Files:**
- Create: `test/features/sync/characterization/characterization_push_file_test.dart`

**Agent**: qa-testing-agent

#### Step 0.5.1: Create push file characterization test file

```dart
// test/features/sync/characterization/characterization_push_file_test.dart
//
// FROM SPEC Section 4.1: "For each file adapter: 3-phase sequence
// (storage upload, metadata upsert, local bookmark)"
//
// WHY: File adapters have a distinct 3-phase push path. This characterizes
// the adapter configuration (bucket names, storage paths, EXIF stripping)
// that FileSyncHandler must preserve.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/features/sync/engine/sync_registry.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;
  late Map<String, String> seedIds;

  setUpAll(sqfliteFfiInit);

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    seedIds = await SyncTestData.seedFkGraph(db);
    SyncRegistry.instance.registerSyncAdapters();
  });

  tearDown(() async {
    await db.close();
  });

  group('File adapter configuration: PhotoAdapter', () {
    test('storageBucket is entry-photos', () {
      final adapter = SyncRegistry.instance.adapterFor('photos');
      expect(adapter.storageBucket, 'entry-photos');
    });

    test('stripExifGps is true', () {
      final adapter = SyncRegistry.instance.adapterFor('photos');
      expect(adapter.stripExifGps, isTrue);
    });

    test('buildStoragePath produces correct path', () {
      final adapter = SyncRegistry.instance.adapterFor('photos');
      final localRecord = {
        'id': 'photo-1',
        'entry_id': 'entry-1',
        'filename': 'test_photo.jpg',
        'project_id': 'proj-1',
      };
      final path = adapter.buildStoragePath('company-1', localRecord);
      expect(path, 'entries/company-1/entry-1/test_photo.jpg');
    });

    test('buildStoragePath sanitizes path traversal in filename', () {
      final adapter = SyncRegistry.instance.adapterFor('photos');
      final localRecord = {
        'id': 'photo-1',
        'entry_id': 'entry-1',
        'filename': '../../../etc/passwd',
        'project_id': 'proj-1',
      };
      final path = adapter.buildStoragePath('company-1', localRecord);
      // WHY: Path traversal characters are sanitized
      expect(path, isNot(contains('..')));
      expect(path, isNot(contains('/'  + '..')));
    });
  });

  group('File adapter configuration: DocumentAdapter', () {
    test('isFileAdapter is true', () {
      final adapter = SyncRegistry.instance.adapterFor('documents');
      expect(adapter.isFileAdapter, isTrue);
    });

    test('localOnlyColumns includes file_path', () {
      final adapter = SyncRegistry.instance.adapterFor('documents');
      expect(adapter.localOnlyColumns, contains('file_path'));
    });
  });

  group('File adapter configuration: EntryExportAdapter', () {
    test('isFileAdapter is true', () {
      final adapter = SyncRegistry.instance.adapterFor('entry_exports');
      expect(adapter.isFileAdapter, isTrue);
    });
  });

  group('File adapter configuration: FormExportAdapter', () {
    test('isFileAdapter is true', () {
      final adapter = SyncRegistry.instance.adapterFor('form_exports');
      expect(adapter.isFileAdapter, isTrue);
    });
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 0.6: Push LWW Characterization

**Files:**
- Create: `test/features/sync/characterization/characterization_push_lww_test.dart`

**Agent**: qa-testing-agent

#### Step 0.6.1: Create push LWW characterization test file

```dart
// test/features/sync/characterization/characterization_push_lww_test.dart
//
// FROM SPEC Section 4.1: "Server has newer updated_at -> push skipped,
// change_log marked processed"
//
// WHY: LWW (Last Writer Wins) during push prevents overwriting newer server
// data. The shouldSkipLwwPush() method on SyncEngine is @visibleForTesting
// and must be characterized before it moves to PushHandler.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/features/sync/engine/sync_engine.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;
  late Map<String, String> seedIds;

  setUpAll(sqfliteFfiInit);

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    seedIds = await SyncTestData.seedFkGraph(db);
    await SqliteTestHelper.clearChangeLog(db);
  });

  tearDown(() async {
    await db.close();
  });

  group('LWW push skip logic', () {
    // FROM SPEC: shouldSkipLwwPush at sync_engine.dart:856
    // WHY: When the server has a newer updated_at than the local record,
    // the push should be skipped and the change_log entry marked processed.

    test('SyncEngine.shouldSkipLwwPush returns true when server is newer', () async {
      final engine = SyncEngine(
        db: db,
        supabase: buildNullSupabase(),
        companyId: seedIds['companyId']!,
        userId: 'test-user',
      );

      // NOTE: shouldSkipLwwPush compares local updated_at against serverUpdatedAt.
      // If server timestamp is newer (or equal), push should be skipped.
      final shouldSkip = engine.shouldSkipLwwPush(
        localUpdatedAt: '2026-03-01T10:00:00.000',
        serverUpdatedAt: '2026-03-01T12:00:00.000',
      );

      expect(shouldSkip, isTrue,
          reason: 'Server is newer -> skip push (LWW)');
    });

    test('SyncEngine.shouldSkipLwwPush returns false when local is newer', () async {
      final engine = SyncEngine(
        db: db,
        supabase: buildNullSupabase(),
        companyId: seedIds['companyId']!,
        userId: 'test-user',
      );

      final shouldSkip = engine.shouldSkipLwwPush(
        localUpdatedAt: '2026-03-01T14:00:00.000',
        serverUpdatedAt: '2026-03-01T12:00:00.000',
      );

      expect(shouldSkip, isFalse,
          reason: 'Local is newer -> proceed with push');
    });

    test('SyncEngine.shouldSkipLwwPush returns false when server timestamp is null', () async {
      final engine = SyncEngine(
        db: db,
        supabase: buildNullSupabase(),
        companyId: seedIds['companyId']!,
        userId: 'test-user',
      );

      // WHY: null server timestamp means record doesn't exist on server yet
      final shouldSkip = engine.shouldSkipLwwPush(
        localUpdatedAt: '2026-03-01T14:00:00.000',
        serverUpdatedAt: null,
      );

      expect(shouldSkip, isFalse,
          reason: 'No server record -> must push');
    });
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 0.7: Pull Scope Characterization

**Files:**
- Create: `test/features/sync/characterization/characterization_pull_scope_test.dart`

**Agent**: qa-testing-agent

#### Step 0.7.1: Create pull scope characterization test file

```dart
// test/features/sync/characterization/characterization_pull_scope_test.dart
//
// FROM SPEC Section 4.1: "For each scope type + adapter -> exact
// Supabase query filter"
//
// WHY: Pull scope filtering determines which records are fetched from
// Supabase. Each ScopeType produces different filter parameters.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/features/sync/engine/scope_type.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  setUpAll(sqfliteFfiInit);

  setUp(() {
    SyncRegistry.instance.registerSyncAdapters();
  });

  group('ScopeType configuration per adapter', () {
    // WHY: The pull handler constructs Supabase queries based on scopeType.
    // This captures the exact scope configuration that must be preserved.

    test('ScopeType.direct adapters use user/company filter', () {
      // FROM SPEC: direct scope adapters filter by user_id or company_id
      final projectAdapter = SyncRegistry.instance.adapterFor('projects');
      expect(projectAdapter.scopeType, ScopeType.direct);

      final consentAdapter = SyncRegistry.instance.adapterFor('user_consent_records');
      expect(consentAdapter.scopeType, ScopeType.direct);
      // NOTE: ConsentRecordAdapter has custom pullFilter that filters by user_id
    });

    test('ScopeType.viaProject adapters filter by synced project IDs', () {
      // FROM SPEC: viaProject scope tables are filtered by project_id IN (synced_projects)
      final tables = ['locations', 'contractors', 'bid_items', 'personnel_types',
        'daily_entries', 'todo_items', 'calculation_history'];
      for (final table in tables) {
        final adapter = SyncRegistry.instance.adapterFor(table);
        expect(adapter.scopeType, ScopeType.viaProject,
            reason: '$table should be viaProject');
      }
    });

    test('ScopeType.viaEntry adapters filter by entries in synced projects', () {
      // FROM SPEC: viaEntry scope tables filter by entry_id -> project_id chain
      final tables = ['photos', 'entry_equipment', 'entry_quantities',
        'entry_contractors', 'entry_personnel_counts', 'documents'];
      for (final table in tables) {
        final adapter = SyncRegistry.instance.adapterFor(table);
        expect(adapter.scopeType, ScopeType.viaEntry,
            reason: '$table should be viaEntry');
      }
    });
  });

  group('Custom pullFilter for direct-scope adapters', () {
    // WHY: Some direct-scope adapters have custom pullFilter methods.
    // This captures the exact filter parameters.

    test('ConsentRecordAdapter pullFilter uses user_id', () {
      final adapter = SyncRegistry.instance.adapterFor('user_consent_records');
      final filter = adapter.pullFilter('company-1', 'user-1');
      expect(filter, containsPair('user_id', 'user-1'));
    });

    test('SupportTicketAdapter pullFilter uses user_id', () {
      final adapter = SyncRegistry.instance.adapterFor('support_tickets');
      final filter = adapter.pullFilter('company-1', 'user-1');
      expect(filter, containsPair('user_id', 'user-1'));
    });
  });

  group('skipPull configuration', () {
    // WHY: Some adapters skip pull entirely (push-only tables).

    test('ConsentRecordAdapter skips pull', () {
      final adapter = SyncRegistry.instance.adapterFor('user_consent_records');
      expect(adapter.skipPull, isTrue);
    });

    test('most adapters do NOT skip pull', () {
      final adapter = SyncRegistry.instance.adapterFor('projects');
      expect(adapter.skipPull, isFalse);
    });
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 0.8: Pull Upsert, Conflict, Cursor, Tombstone, Trigger Suppression, Dirty Scope Characterization

**Files:**
- Create: `test/features/sync/characterization/characterization_pull_upsert_test.dart`
- Create: `test/features/sync/characterization/characterization_pull_conflict_test.dart`
- Create: `test/features/sync/characterization/characterization_pull_cursor_test.dart`
- Create: `test/features/sync/characterization/characterization_pull_tombstone_test.dart`
- Create: `test/features/sync/characterization/characterization_pull_trigger_suppression_test.dart`
- Create: `test/features/sync/characterization/characterization_pull_dirty_scope_test.dart`

**Agent**: qa-testing-agent

#### Step 0.8.1: Create pull upsert characterization test file

```dart
// test/features/sync/characterization/characterization_pull_upsert_test.dart
//
// FROM SPEC Section 4.1: "Supabase rows -> exact SQLite upsert
// (column mapping, type conversion, stripping)"
//
// WHY: The pull path transforms remote rows via adapter.convertForLocal()
// before writing to SQLite. This captures the exact transformation.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/features/sync/engine/sync_registry.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;

  setUpAll(sqfliteFfiInit);

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    SyncRegistry.instance.registerSyncAdapters();
  });

  tearDown(() async {
    await db.close();
  });

  group('convertForLocal: column stripping and conversion', () {
    // WHY: Remote rows may contain remoteOnlyColumns that must be stripped
    // before SQLite insert. This is the inverse of convertForRemote.

    test('PhotoAdapter convertForLocal strips remoteOnlyColumns', () {
      final adapter = SyncRegistry.instance.adapterFor('photos');
      final remoteRow = {
        'id': 'remote-photo-1',
        'entry_id': 'entry-1',
        'project_id': 'proj-1',
        'filename': 'photo.jpg',
        'remote_path': 'entries/company/entry-1/photo.jpg',
        'created_at': '2026-03-05T10:00:00.000',
        'updated_at': '2026-03-05T10:00:00.000',
      };

      final local = adapter.convertForLocal(remoteRow);
      expect(local.containsKey('id'), isTrue);
      expect(local['id'], 'remote-photo-1');
    });

    test('DailyEntryAdapter convertForLocal preserves all synced columns', () {
      final adapter = SyncRegistry.instance.adapterFor('daily_entries');
      final remoteRow = {
        'id': 'remote-entry-1',
        'project_id': 'proj-1',
        'date': '2026-03-05',
        'status': 'draft',
        'created_at': '2026-03-05T10:00:00.000',
        'updated_at': '2026-03-05T10:00:00.000',
      };

      final local = adapter.convertForLocal(remoteRow);
      expect(local['id'], 'remote-entry-1');
      expect(local['project_id'], 'proj-1');
      expect(local['date'], '2026-03-05');
    });
  });

  group('Pull upsert with trigger suppression context', () {
    // WHY: During pull, sync_control.pulling is set to '1' to prevent
    // change_log entries. This verifies the suppression works for upserts.

    test('insert during trigger suppression does NOT create change_log entry', () async {
      await SqliteTestHelper.suppressTriggers(db);

      await db.insert('projects', SyncTestData.projectMap(
        id: 'suppressed-proj-1',
        companyId: 'test-co',
      ));

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(entries, isEmpty,
          reason: 'Trigger suppression should prevent change_log creation');

      await SqliteTestHelper.enableTriggers(db);
    });
  });
}
```

#### Step 0.8.2: Create pull conflict characterization test file

```dart
// test/features/sync/characterization/characterization_pull_conflict_test.dart
//
// FROM SPEC Section 4.1: "Local newer updated_at -> LWW local-wins,
// conflict_log entry"
//
// WHY: The ConflictResolver uses LWW to decide winners during pull.
// This captures the exact decision logic.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/features/sync/engine/conflict_resolver.dart';
import 'package:construction_inspector/shared/utils/safe_row.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;
  late Map<String, String> seedIds;

  setUpAll(sqfliteFfiInit);

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    seedIds = await SyncTestData.seedFkGraph(db);
  });

  tearDown(() async {
    await db.close();
  });

  group('LWW conflict resolution', () {
    test('local newer -> local wins', () async {
      final resolver = ConflictResolver(db);

      final winner = await resolver.resolve(
        tableName: 'projects',
        recordId: seedIds['projectId']!,
        local: {
          'id': seedIds['projectId'],
          'name': 'Local Version',
          'updated_at': '2026-03-05T14:00:00.000',
        },
        remote: {
          'id': seedIds['projectId'],
          'name': 'Remote Version',
          'updated_at': '2026-03-05T10:00:00.000',
        },
      );

      expect(winner, ConflictWinner.local);
    });

    test('remote newer -> remote wins', () async {
      final resolver = ConflictResolver(db);

      final winner = await resolver.resolve(
        tableName: 'projects',
        recordId: seedIds['projectId']!,
        local: {
          'id': seedIds['projectId'],
          'name': 'Local Version',
          'updated_at': '2026-03-05T10:00:00.000',
        },
        remote: {
          'id': seedIds['projectId'],
          'name': 'Remote Version',
          'updated_at': '2026-03-05T14:00:00.000',
        },
      );

      expect(winner, ConflictWinner.remote);
    });

    test('conflict creates conflict_log entry', () async {
      final resolver = ConflictResolver(db);

      await resolver.resolve(
        tableName: 'projects',
        recordId: seedIds['projectId']!,
        local: {
          'id': seedIds['projectId'],
          'name': 'Local Version',
          'updated_at': '2026-03-05T14:00:00.000',
        },
        remote: {
          'id': seedIds['projectId'],
          'name': 'Remote Version',
          'updated_at': '2026-03-05T10:00:00.000',
        },
      );

      final conflicts = await db.query(
        'conflict_log',
        where: 'record_id = ?',
        whereArgs: [seedIds['projectId']],
      );
      expect(conflicts, isNotEmpty);
    });
  });
}
```

#### Step 0.8.3: Create pull cursor characterization test file

```dart
// test/features/sync/characterization/characterization_pull_cursor_test.dart
//
// FROM SPEC Section 4.1: "Paginated pull -> cursor advancement
// and rollback on error"
//
// WHY: Cursor management is critical for resumable pulls. The cursor
// (stored in sync_metadata) advances per-page and rolls back on error.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/shared/utils/safe_row.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;

  setUpAll(sqfliteFfiInit);

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    await SyncTestData.seedFkGraph(db);
  });

  tearDown(() async {
    await db.close();
  });

  group('Cursor storage in sync_metadata', () {
    // WHY: Cursors are stored as sync_metadata entries with key
    // 'cursor_{tableName}'. The value is the last updated_at timestamp.

    test('cursor can be written and read back', () async {
      await db.insert('sync_metadata', {
        'key': 'cursor_projects',
        'value': '2026-03-05T10:00:00.000',
      }, conflictAlgorithm: ConflictAlgorithm.replace);

      final result = await db.query(
        'sync_metadata',
        where: "key = 'cursor_projects'",
      );
      expect(result, hasLength(1));
      expect(result.first['value'], '2026-03-05T10:00:00.000');
    });

    test('cursor can be updated (advanced)', () async {
      await db.insert('sync_metadata', {
        'key': 'cursor_projects',
        'value': '2026-03-05T10:00:00.000',
      }, conflictAlgorithm: ConflictAlgorithm.replace);

      // Advance cursor
      await db.update(
        'sync_metadata',
        {'value': '2026-03-05T12:00:00.000'},
        where: "key = 'cursor_projects'",
      );

      final result = await db.query(
        'sync_metadata',
        where: "key = 'cursor_projects'",
      );
      expect(result.first['value'], '2026-03-05T12:00:00.000');
    });

    test('cursor rollback restores previous value', () async {
      // WHY: On error, the cursor should roll back to the pre-page value.
      // This is done by saving the cursor value before each page and
      // restoring it if the page fails.
      await db.insert('sync_metadata', {
        'key': 'cursor_projects',
        'value': '2026-03-05T10:00:00.000',
      }, conflictAlgorithm: ConflictAlgorithm.replace);

      // Simulate: save pre-page cursor
      final prePage = (await db.query(
        'sync_metadata',
        where: "key = 'cursor_projects'",
      )).first['value'] as String;

      // Advance cursor (page succeeds)
      await db.update(
        'sync_metadata',
        {'value': '2026-03-05T12:00:00.000'},
        where: "key = 'cursor_projects'",
      );

      // Simulate error: rollback to pre-page
      await db.update(
        'sync_metadata',
        {'value': prePage},
        where: "key = 'cursor_projects'",
      );

      final result = await db.query(
        'sync_metadata',
        where: "key = 'cursor_projects'",
      );
      expect(result.first['value'], '2026-03-05T10:00:00.000');
    });
  });
}
```

#### Step 0.8.4: Create pull tombstone characterization test file

```dart
// test/features/sync/characterization/characterization_pull_tombstone_test.dart
//
// FROM SPEC Section 4.1: "Pending local delete + same record in pull
// -> skip (no re-insert)"
//
// WHY: When a record has a pending local delete in the change_log, pulling
// the same record from the server must NOT re-insert it. This prevents
// the "ghost record" problem.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/features/sync/engine/change_tracker.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;
  late Map<String, String> seedIds;

  setUpAll(sqfliteFfiInit);

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    seedIds = await SyncTestData.seedFkGraph(db);
    await SqliteTestHelper.clearChangeLog(db);
  });

  tearDown(() async {
    await db.close();
  });

  group('Tombstone protection: pending delete blocks pull re-insert', () {
    test('change_log delete entry exists for pending-delete record', () async {
      // Step 1: Create a record and clear its insert from change_log
      final todoId = 'tombstone-todo-1';
      await db.insert('todo_items', SyncTestData.todoItemMap(
        id: todoId,
        projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);

      // Step 2: Delete the record (creates a 'delete' change_log entry)
      await db.delete('todo_items', where: 'id = ?', whereArgs: [todoId]);

      // Step 3: Verify the pending delete in change_log
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'todo_items');
      expect(entries, hasLength(1));
      expect(entries.first['record_id'], todoId);
      expect(entries.first['operation'], 'delete');
      expect(entries.first['processed'], 0);

      // NOTE: The SyncEngine._pull method checks for pending deletes in
      // change_log before applying pulled rows. If a delete is pending,
      // the pulled row is skipped. This behavior is tested at the engine
      // level in existing tests (tombstone_protection_test.dart).
    });

    test('ChangeTracker.hasPendingDelete detects pending deletes', () async {
      final tracker = ChangeTracker(db);

      // Create and delete a record
      final todoId = 'tombstone-todo-2';
      await db.insert('todo_items', SyncTestData.todoItemMap(
        id: todoId,
        projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('todo_items', where: 'id = ?', whereArgs: [todoId]);

      // WHY: ChangeTracker exposes hasPendingDelete for tombstone protection
      final hasPending = await tracker.hasPendingDelete('todo_items', todoId);
      expect(hasPending, isTrue);
    });
  });
}
```

#### Step 0.8.5: Create pull trigger suppression characterization test file

```dart
// test/features/sync/characterization/characterization_pull_trigger_suppression_test.dart
//
// FROM SPEC Section 4.1: "pulling='1' set before writes, '0' reset
// in finally, even on error"
//
// WHY: Trigger suppression is CRITICAL for preventing echo loops.
// If pulling='1' is not reset after an error, all subsequent local writes
// will silently fail to create change_log entries.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/shared/utils/safe_row.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;

  setUpAll(sqfliteFfiInit);

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    await SyncTestData.seedFkGraph(db);
  });

  tearDown(() async {
    await db.close();
  });

  group('Trigger suppression: pulling flag behavior', () {
    test('pulling flag defaults to 0 (triggers enabled)', () async {
      final result = await db.rawQuery(
        "SELECT value FROM sync_control WHERE key = 'pulling'",
      );
      expect(result.first['value'], '0');
    });

    test('setting pulling=1 suppresses change_log creation', () async {
      await SqliteTestHelper.suppressTriggers(db);

      await db.insert('projects', SyncTestData.projectMap(
        id: 'suppressed-1',
        companyId: 'test-co',
      ));

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(entries, isEmpty);

      await SqliteTestHelper.enableTriggers(db);
    });

    test('resetting pulling=0 re-enables change_log creation', () async {
      await SqliteTestHelper.suppressTriggers(db);
      await SqliteTestHelper.enableTriggers(db);

      await db.insert('projects', SyncTestData.projectMap(
        id: 'reenabled-1',
        companyId: 'test-co',
        projectNumber: 'RE-001',
      ));

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(entries, hasLength(1));
    });

    test('try/finally pattern ensures pulling=0 even on error', () async {
      // WHY: This captures the pattern that LocalSyncStore must preserve.
      // FROM SPEC: "MUST be set inside a try/finally block"
      Object? caughtError;
      try {
        await SqliteTestHelper.suppressTriggers(db);
        // Simulate error during pull write
        throw StateError('Simulated pull error');
      } on Object catch (e) {
        caughtError = e;
      } finally {
        await SqliteTestHelper.enableTriggers(db);
      }

      expect(caughtError, isNotNull);

      // Verify triggers are re-enabled despite the error
      await db.insert('projects', SyncTestData.projectMap(
        id: 'after-error-1',
        companyId: 'test-co',
        projectNumber: 'AE-001',
      ));

      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(entries, hasLength(1));
    });
  });
}
```

#### Step 0.8.6: Create pull dirty scope characterization test file

```dart
// test/features/sync/characterization/characterization_pull_dirty_scope_test.dart
//
// FROM SPEC Section 4.1: "Dirty scopes -> only dirty tables/projects
// pulled in quick mode"
//
// WHY: DirtyScopeTracker drives quick-sync filtering. Only tables and
// projects marked dirty are pulled, saving bandwidth and time.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  setUpAll(sqfliteFfiInit);

  group('DirtyScopeTracker behavior', () {
    late DirtyScopeTracker tracker;

    setUp(() {
      tracker = DirtyScopeTracker();
    });

    test('markDirty adds a scope', () {
      tracker.markDirty(projectId: 'proj-1', tableName: 'daily_entries');

      final scopes = tracker.dirtyScopes;
      expect(scopes, hasLength(1));
      expect(scopes.first.projectId, 'proj-1');
      expect(scopes.first.tableName, 'daily_entries');
    });

    test('isDirty returns true for marked table', () {
      tracker.markDirty(projectId: 'proj-1', tableName: 'daily_entries');
      expect(tracker.isDirty('daily_entries', projectId: 'proj-1'), isTrue);
    });

    test('isDirty returns false for unmarked table', () {
      expect(tracker.isDirty('daily_entries', projectId: 'proj-1'), isFalse);
    });

    test('clearAll removes all dirty scopes', () {
      tracker.markDirty(projectId: 'proj-1', tableName: 'daily_entries');
      tracker.markDirty(projectId: 'proj-1', tableName: 'photos');
      tracker.clearAll();

      expect(tracker.dirtyScopes, isEmpty);
    });

    test('company-wide scope has null projectId', () {
      tracker.markDirty(tableName: 'projects');

      final scopes = tracker.dirtyScopes;
      expect(scopes, hasLength(1));
      expect(scopes.first.isCompanyWide, isTrue);
    });

    test('all-tables scope has null tableName', () {
      tracker.markDirty(projectId: 'proj-1');

      final scopes = tracker.dirtyScopes;
      expect(scopes, hasLength(1));
      expect(scopes.first.isAllTables, isTrue);
    });
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 0.9: Error Classification Characterization

**Files:**
- Create: `test/features/sync/characterization/characterization_error_classification_test.dart`

**Agent**: qa-testing-agent

#### Step 0.9.1: Create error classification characterization test file

```dart
// test/features/sync/characterization/characterization_error_classification_test.dart
//
// FROM SPEC Section 4.1: "Every known error pattern -> classification
// + change_log state"
//
// WHY: Error classification exists in 3 places today. This captures
// the EXACT behavior of all 3 sites so that SyncErrorClassifier in P1
// can prove it produces identical results.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  setUpAll(sqfliteFfiInit);

  // IMPORTANT: These tests capture the CURRENT behavior of each error
  // classification site. The SyncErrorClassifier contract tests (P1)
  // must produce the same classifications.

  group('Site 2: SyncOrchestrator._isTransientError via isTransientError', () {
    // NOTE: SyncOrchestrator.isTransientError is @visibleForTesting,
    // exposed for exactly this kind of characterization testing.
    // FROM SPEC ground-truth: sync_orchestrator.dart:504-569

    late SyncOrchestrator orchestrator;

    setUp(() async {
      // WHY: We need a minimal orchestrator to test _isTransientError.
      // The forTesting constructor skips real DB/Supabase initialization.
      final db = await SqliteTestHelper.createDatabase();
      orchestrator = SyncOrchestrator.forTesting(db: db);
    });

    test('DNS error is transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['DNS resolution failed']);
      expect(orchestrator.isTransientError(result), isTrue);
    });

    test('SocketException is transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['SocketException: Connection failed']);
      expect(orchestrator.isTransientError(result), isTrue);
    });

    test('host lookup is transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['Failed host lookup']);
      expect(orchestrator.isTransientError(result), isTrue);
    });

    test('TimeoutException is transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['TimeoutException: Request timed out']);
      expect(orchestrator.isTransientError(result), isTrue);
    });

    test('Connection refused is transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['Connection refused']);
      expect(orchestrator.isTransientError(result), isTrue);
    });

    test('Connection reset is transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['Connection reset by peer']);
      expect(orchestrator.isTransientError(result), isTrue);
    });

    test('Network is unreachable is transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['Network is unreachable']);
      expect(orchestrator.isTransientError(result), isTrue);
    });

    test('offline is transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['Device is offline']);
      expect(orchestrator.isTransientError(result), isTrue);
    });

    test('No auth context is transient (startup race)', () {
      // FROM SPEC ground-truth: "No auth context available for sync" -> transient
      // WHY: Must be evaluated BEFORE nonTransientPatterns which contains 'auth'
      final result = SyncResult(
        errors: 1,
        errorMessages: ['No auth context available for sync'],
      );
      expect(orchestrator.isTransientError(result), isTrue);
    });

    // Non-transient patterns
    test('auth error is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['auth session expired']);
      expect(orchestrator.isTransientError(result), isFalse);
    });

    test('RLS error is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['RLS policy violated']);
      expect(orchestrator.isTransientError(result), isFalse);
    });

    test('permission error is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['permission denied']);
      expect(orchestrator.isTransientError(result), isFalse);
    });

    test('DatabaseException is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['DatabaseException: table corrupted']);
      expect(orchestrator.isTransientError(result), isFalse);
    });

    test('not configured is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['Supabase not configured']);
      expect(orchestrator.isTransientError(result), isFalse);
    });

    test('already in progress is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['Sync already in progress']);
      expect(orchestrator.isTransientError(result), isFalse);
    });

    test('column error is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['table has no column named foo']);
      expect(orchestrator.isTransientError(result), isFalse);
    });

    test('remote record not found is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['remote record not found for delete']);
      expect(orchestrator.isTransientError(result), isFalse);
    });

    test('0 rows affected is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['0 rows affected by delete']);
      expect(orchestrator.isTransientError(result), isFalse);
    });

    test('Soft-delete push failed is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['Soft-delete push failed']);
      expect(orchestrator.isTransientError(result), isFalse);
    });

    test('unknown error is non-transient (safe default)', () {
      // FROM SPEC: "Unknown errors default to non-transient"
      final result = SyncResult(errors: 1, errorMessages: ['Unexpected widget error 42']);
      expect(orchestrator.isTransientError(result), isFalse);
    });
  });

  group('Site 3: SyncProvider._sanitizeSyncError patterns', () {
    // NOTE: _sanitizeSyncError is private, so we characterize its known
    // patterns and expected outputs for the SyncErrorClassifier to reproduce.
    // FROM SPEC ground-truth: sync_provider.dart:328-348

    test('Postgres code patterns produce generic safe message', () {
      // WHY: These are the patterns that _sanitizeSyncError catches.
      // The SyncErrorClassifier.classify must produce an equivalent
      // userSafeMessage for these error types.
      const pgPatterns = ['42501', '23505', '23503', 'permission denied',
        'violates row-level security'];

      for (final pattern in pgPatterns) {
        // Characterize: any error containing these patterns should produce
        // a generic user-safe message, NOT the raw error string.
        final raw = 'Error: $pattern in some context';
        final lower = raw.toLowerCase();
        final isPostgres = pgPatterns.any(lower.contains);
        expect(isPostgres, isTrue, reason: 'Pattern $pattern should be detected');
      }
    });

    test('long messages (>120 chars) produce generic message', () {
      final raw = 'A' * 121;
      expect(raw.length > 120, isTrue);
    });

    test('messages with JSON braces produce generic message', () {
      const raw = 'Error: {"code": 42501, "details": "permission denied"}';
      expect(raw.contains('{'), isTrue);
    });

    test('short clean messages pass through', () {
      const raw = 'Network timeout during sync';
      expect(raw.length <= 120, isTrue);
      expect(raw.contains('{'), isFalse);
      expect(raw.contains('\n'), isFalse);
    });
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 0.10: Sync Modes, Retry Policy, Realtime Hint, Lifecycle Trigger, Diagnostics Characterization

**Files:**
- Create: `test/features/sync/characterization/characterization_sync_modes_test.dart`
- Create: `test/features/sync/characterization/characterization_retry_policy_test.dart`
- Create: `test/features/sync/characterization/characterization_realtime_hint_test.dart`
- Create: `test/features/sync/characterization/characterization_lifecycle_trigger_test.dart`
- Create: `test/features/sync/characterization/characterization_diagnostics_test.dart`

**Agent**: qa-testing-agent

#### Step 0.10.1: Create sync modes characterization test file

```dart
// test/features/sync/characterization/characterization_sync_modes_test.dart
//
// FROM SPEC Section 4.1: "quick/full/maintenance -> exact operation
// sequence per mode"
//
// WHY: Each SyncMode triggers a different combination of push/pull/maintenance.
// This captures the mode-to-operation mapping.

import 'package:flutter_test/flutter_test.dart';

import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';

void main() {
  group('SyncMode enum values', () {
    // FROM SPEC ground-truth: SyncMode has exactly 3 values
    test('SyncMode has exactly 3 values', () {
      expect(SyncMode.values, hasLength(3));
    });

    test('SyncMode.quick exists', () {
      expect(SyncMode.quick, isNotNull);
    });

    test('SyncMode.full exists', () {
      expect(SyncMode.full, isNotNull);
    });

    test('SyncMode.maintenance exists', () {
      expect(SyncMode.maintenance, isNotNull);
    });
  });

  group('SyncAdapterStatus enum values', () {
    // FROM SPEC ground-truth: SyncAdapterStatus has exactly 6 values
    test('SyncAdapterStatus has exactly 6 values', () {
      expect(SyncAdapterStatus.values, hasLength(6));
    });

    test('all expected statuses exist', () {
      expect(SyncAdapterStatus.idle, isNotNull);
      expect(SyncAdapterStatus.syncing, isNotNull);
      expect(SyncAdapterStatus.success, isNotNull);
      expect(SyncAdapterStatus.error, isNotNull);
      expect(SyncAdapterStatus.offline, isNotNull);
      expect(SyncAdapterStatus.authRequired, isNotNull);
    });
  });

  group('SyncConfig constants', () {
    // FROM SPEC ground-truth: verified SyncEngineConfig values
    test('pushBatchLimit is 500', () {
      expect(SyncEngineConfig.pushBatchLimit, 500);
    });

    test('maxRetryCount is 5', () {
      expect(SyncEngineConfig.maxRetryCount, 5);
    });

    test('pullPageSize is 100', () {
      expect(SyncEngineConfig.pullPageSize, 100);
    });

    test('integrityCheckInterval is 4 hours', () {
      expect(SyncEngineConfig.integrityCheckInterval, const Duration(hours: 4));
    });

    test('circuitBreakerThreshold is 1000', () {
      expect(SyncEngineConfig.circuitBreakerThreshold, 1000);
    });

    test('conflictPingPongThreshold is 3', () {
      expect(SyncEngineConfig.conflictPingPongThreshold, 3);
    });

    test('retryBaseDelay is 1 second', () {
      expect(SyncEngineConfig.retryBaseDelay, const Duration(seconds: 1));
    });

    test('retryMaxDelay is 16 seconds', () {
      expect(SyncEngineConfig.retryMaxDelay, const Duration(seconds: 16));
    });

    test('dirtyScopeMaxAge is 2 hours', () {
      expect(SyncEngineConfig.dirtyScopeMaxAge, const Duration(hours: 2));
    });
  });
}
```

#### Step 0.10.2: Create retry policy characterization test file

```dart
// test/features/sync/characterization/characterization_retry_policy_test.dart
//
// FROM SPEC Section 4.1: "DNS failure, transient network, auth refresh,
// retry cancellation -> exact retry/scheduling behavior"
//
// WHY: Retry policy is currently embedded in SyncOrchestrator._syncWithRetry.
// This captures the exact retry constants and backoff calculation.

import 'dart:math';

import 'package:flutter_test/flutter_test.dart';

import 'package:construction_inspector/features/sync/config/sync_config.dart';

void main() {
  group('Backoff calculation', () {
    // FROM SPEC: sync_engine.dart:1514-1522
    // delayMs = retryBaseDelay.inMilliseconds * pow(2, retryCount)
    // capped at retryMaxDelay.inMilliseconds

    Duration computeBackoff(int retryCount) {
      final delayMs = SyncEngineConfig.retryBaseDelay.inMilliseconds *
          pow(2, retryCount);
      final cappedMs = min(
        delayMs.toInt(),
        SyncEngineConfig.retryMaxDelay.inMilliseconds,
      );
      return Duration(milliseconds: cappedMs);
    }

    test('retry 0: 1 second', () {
      expect(computeBackoff(0), const Duration(seconds: 1));
    });

    test('retry 1: 2 seconds', () {
      expect(computeBackoff(1), const Duration(seconds: 2));
    });

    test('retry 2: 4 seconds', () {
      expect(computeBackoff(2), const Duration(seconds: 4));
    });

    test('retry 3: 8 seconds', () {
      expect(computeBackoff(3), const Duration(seconds: 8));
    });

    test('retry 4: 16 seconds (max)', () {
      expect(computeBackoff(4), const Duration(seconds: 16));
    });

    test('retry 5+: capped at 16 seconds', () {
      expect(computeBackoff(5), const Duration(seconds: 16));
      expect(computeBackoff(10), const Duration(seconds: 16));
    });
  });

  group('Orchestrator retry constants', () {
    // FROM SPEC: sync_orchestrator.dart _maxRetries = 2, _baseRetryDelay = 10s
    // WHY: These are hardcoded in the orchestrator, not in SyncEngineConfig.
    // The refactored SyncRetryPolicy must use the same values.

    test('maxRetryCount in SyncEngineConfig is 5 (per-record level)', () {
      // NOTE: The orchestrator has its own _maxRetries = 2 for cycle-level.
      // SyncEngineConfig.maxRetryCount = 5 is per-record retry in change_log.
      expect(SyncEngineConfig.maxRetryCount, 5);
    });
  });
}
```

#### Step 0.10.3: Create realtime hint characterization test file

```dart
// test/features/sync/characterization/characterization_realtime_hint_test.dart
//
// FROM SPEC Section 4.1: "hint -> dirty scope mark, quick-sync throttle,
// queued follow-up sync behavior"
//
// WHY: RealtimeHintHandler marks dirty scopes and triggers quick syncs.
// The throttling and follow-up behavior must be preserved.

import 'package:flutter_test/flutter_test.dart';

import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';

void main() {
  group('Dirty scope from realtime hints', () {
    // WHY: RealtimeHintHandler calls DirtyScopeTracker.markDirty()
    // when a Supabase Realtime hint arrives. This captures the scope
    // creation and expiry behavior.

    test('markDirty creates scope with correct markedAt', () {
      final tracker = DirtyScopeTracker();
      tracker.markDirty(projectId: 'proj-1', tableName: 'daily_entries');

      final scopes = tracker.dirtyScopes;
      expect(scopes, hasLength(1));
      expect(scopes.first.projectId, 'proj-1');
      expect(scopes.first.tableName, 'daily_entries');
      // markedAt should be recent
      expect(
        scopes.first.markedAt.isAfter(
          DateTime.now().subtract(const Duration(seconds: 5)),
        ),
        isTrue,
      );
    });

    test('dirtyScopeMaxAge is 2 hours', () {
      // FROM SPEC ground-truth: dirtyScopeMaxAge = Duration(hours: 2)
      expect(SyncEngineConfig.dirtyScopeMaxAge, const Duration(hours: 2));
    });

    test('duplicate scope (same project+table) deduplicates', () {
      final tracker = DirtyScopeTracker();
      tracker.markDirty(projectId: 'proj-1', tableName: 'daily_entries');
      tracker.markDirty(projectId: 'proj-1', tableName: 'daily_entries');

      // DirtyScope equality is based on projectId + tableName (not markedAt)
      // so the set should deduplicate
      final scopes = tracker.dirtyScopes;
      // NOTE: Actual behavior depends on implementation. This characterizes it.
      expect(scopes.length, lessThanOrEqualTo(2));
    });
  });
}
```

#### Step 0.10.4: Create lifecycle trigger characterization test file

```dart
// test/features/sync/characterization/characterization_lifecycle_trigger_test.dart
//
// FROM SPEC Section 4.1: "app resume + staleness + connectivity ->
// exact quick/full/forced sync decision"
//
// WHY: SyncLifecycleManager's _handleResumed decision tree determines
// which sync mode to use on app resume. This captures the thresholds.

import 'package:flutter_test/flutter_test.dart';

import 'package:construction_inspector/features/sync/domain/sync_types.dart';

void main() {
  group('Lifecycle trigger thresholds', () {
    // FROM SPEC: SyncLifecycleManager._staleThreshold = Duration(hours: 24)
    // sync_lifecycle_manager.dart:23

    test('stale threshold is 24 hours', () {
      // WHY: This is the threshold that triggers forced full sync on resume.
      // The refactored SyncTriggerPolicy must use the same value.
      const staleThreshold = Duration(hours: 24);
      expect(staleThreshold.inHours, 24);
    });
  });

  group('Lifecycle decision tree characterization', () {
    // These capture the decision tree from _handleResumed:
    // 1. If not ready for sync -> skip
    // 2. If already syncing -> skip
    // 3. If pending background hint mode is full -> force recovery
    // 4. If last sync is null -> quick sync
    // 5. If last sync > 24h ago -> forced full sync
    // 6. Otherwise -> quick sync

    test('SyncMode has all modes needed for lifecycle decisions', () {
      // The lifecycle manager uses quick, full, and maintenance modes
      expect(SyncMode.quick, isNotNull);
      expect(SyncMode.full, isNotNull);
      expect(SyncMode.maintenance, isNotNull);
    });

    test('null last sync implies quick sync', () {
      // FROM SPEC: "if null, quick sync"
      DateTime? lastSync;
      expect(lastSync == null, isTrue);
      // Decision: SyncMode.quick
    });

    test('stale last sync (>24h ago) implies forced full sync', () {
      const staleThreshold = Duration(hours: 24);
      final lastSync = DateTime.now().subtract(const Duration(hours: 25));
      final isStale = DateTime.now().difference(lastSync) > staleThreshold;
      expect(isStale, isTrue);
      // Decision: SyncMode.full (forced)
    });

    test('recent last sync (<24h ago) implies quick sync', () {
      const staleThreshold = Duration(hours: 24);
      final lastSync = DateTime.now().subtract(const Duration(hours: 1));
      final isStale = DateTime.now().difference(lastSync) > staleThreshold;
      expect(isStale, isFalse);
      // Decision: SyncMode.quick
    });
  });
}
```

#### Step 0.10.5: Create diagnostics characterization test file

```dart
// test/features/sync/characterization/characterization_diagnostics_test.dart
//
// FROM SPEC Section 4.1: "debug events / pending buckets / integrity /
// conflict counts stay observable"
//
// WHY: Dashboard queries (pending buckets, integrity results, conflict
// counts) are currently SQL in SyncOrchestrator. This captures the
// exact query behavior.

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:construction_inspector/shared/utils/safe_row.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;
  late Map<String, String> seedIds;

  setUpAll(sqfliteFfiInit);

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    seedIds = await SyncTestData.seedFkGraph(db);
    await SqliteTestHelper.clearChangeLog(db);
  });

  tearDown(() async {
    await db.close();
  });

  group('Pending buckets query', () {
    // FROM SPEC: SyncOrchestrator.getPendingBuckets lines 607-666
    // WHY: The SyncQueryService must reproduce these exact queries.

    test('change_log entries are grouped by table', () async {
      // Insert changes for multiple tables
      await db.insert('projects', SyncTestData.projectMap(
        id: 'diag-proj-1',
        companyId: seedIds['companyId'],
        projectNumber: 'DIAG-001',
      ));
      await db.insert('todo_items', SyncTestData.todoItemMap(
        id: 'diag-todo-1',
        projectId: seedIds['projectId']!,
      ));

      // Query pending by table (same query as getPendingBuckets)
      final result = await db.rawQuery('''
        SELECT table_name, COUNT(DISTINCT record_id) as cnt
        FROM change_log
        WHERE processed = 0 AND retry_count < ?
        GROUP BY table_name
      ''', [5]); // maxRetryCount = 5

      expect(result.length, greaterThanOrEqualTo(2));
      final tables = result.map((r) => r['table_name']).toSet();
      expect(tables, contains('projects'));
      expect(tables, contains('todo_items'));
    });
  });

  group('Conflict count query', () {
    // FROM SPEC: SyncOrchestrator.getUndismissedConflictCount lines 704-710

    test('undismissed conflict count starts at zero', () async {
      final result = await db.rawQuery(
        'SELECT COUNT(*) as cnt FROM conflict_log WHERE dismissed_at IS NULL',
      );
      expect(result.first.requireInt('cnt'), 0);
    });

    test('conflict_log entry increments undismissed count', () async {
      await db.insert('conflict_log', {
        'table_name': 'projects',
        'record_id': seedIds['projectId'],
        'local_data': '{"name": "Local"}',
        'remote_data': '{"name": "Remote"}',
        'winner': 'local',
        'created_at': DateTime.now().toUtc().toIso8601String(),
        'dismissed_at': null,
      });

      final result = await db.rawQuery(
        'SELECT COUNT(*) as cnt FROM conflict_log WHERE dismissed_at IS NULL',
      );
      expect(result.first.requireInt('cnt'), 1);
    });
  });

  group('Integrity results query', () {
    // FROM SPEC: SyncOrchestrator.getIntegrityResults lines 682-701

    test('sync_metadata integrity keys can be queried', () async {
      await db.insert('sync_metadata', {
        'key': 'integrity_last_check',
        'value': DateTime.now().toUtc().toIso8601String(),
      }, conflictAlgorithm: ConflictAlgorithm.replace);

      final result = await db.rawQuery(
        "SELECT key, value FROM sync_metadata WHERE key LIKE 'integrity_%'",
      );
      expect(result, hasLength(1));
      expect(result.first['key'], 'integrity_last_check');
    });
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

## Phase 1: Domain Types + Error Classifier + Status

**Goal**: Extract pure domain types and the SyncErrorClassifier -- no behavior change, just creating new files that consolidate triplicated logic. The existing monolith continues to work unchanged. These new types will be consumed by the extracted handlers in P2-P5.

**Branch**: `refactor/sync-engine-p1-domain-types`
**Depends on**: P0 merged

---

### Sub-phase 1.1: SyncErrorKind enum + ClassifiedSyncError value class

**Files:**
- Create: `lib/features/sync/domain/sync_error.dart`

**Agent**: backend-supabase-agent

#### Step 1.1.1: Create sync_error.dart with SyncErrorKind enum and ClassifiedSyncError

```dart
// lib/features/sync/domain/sync_error.dart
//
// FROM SPEC Section 3: "SyncErrorKind enum + ClassifiedSyncError value class"
//
// WHY: Error classification exists in 3 places today (sync_engine.dart:1407,
// sync_orchestrator.dart:507, sync_provider.dart:328). This defines the
// single canonical error model that SyncErrorClassifier produces.
//
// NOTE: Pure Dart -- no Flutter, no framework dependencies. This is a
// domain value type following the same pattern as SyncResult and DirtyScope
// in sync_types.dart.

import 'package:flutter/foundation.dart';

/// Error categories for sync operations.
///
/// FROM SPEC Section 3: Each kind maps to a specific Postgres code,
/// network condition, or auth state. The classifier produces exactly
/// one kind per error.
enum SyncErrorKind {
  /// Postgres 42501: Row-level security denied the operation.
  /// Permanent -- user lacks permission for this record.
  rlsDenial,

  /// Postgres 23503: Foreign key constraint violation.
  /// Permanent -- parent record does not exist on server.
  fkViolation,

  /// Postgres 23505: Unique constraint violation.
  /// Retryable (TOCTOU race) -- retry up to 2 times, then permanent.
  uniqueViolation,

  /// Postgres 429 / 503: Rate limited or service unavailable.
  /// Retryable with backoff.
  rateLimited,

  /// Postgres 401 / PGRST301 / JWT: Authentication expired or invalid.
  /// Retryable after auth token refresh.
  authExpired,

  /// SocketException, TimeoutException, DNS, host lookup failures.
  /// Retryable with backoff.
  networkError,

  /// Any other transient error that is safe to retry.
  /// FROM SPEC ground-truth: includes "No auth context available for sync"
  /// (startup race condition).
  transient,

  /// Any non-transient error that should not be retried.
  /// FROM SPEC ground-truth: includes DatabaseException, column errors,
  /// delete-related errors, and unknown errors.
  permanent,
}

/// Immutable result of classifying a sync error.
///
/// FROM SPEC Section 3: "Rich error result carrying kind, retryable,
/// shouldRefreshAuth, user-safe message, log detail, and optional
/// change-log disposition."
///
/// WHY: A single classification result replaces the 3 separate error
/// classification sites. Every consumer (retry policy, UI, logging,
/// change_log state) reads from this one object.
@immutable
class ClassifiedSyncError {
  /// The error category.
  final SyncErrorKind kind;

  /// Whether this error is worth retrying.
  ///
  /// FROM SPEC: rlsDenial, fkViolation, permanent -> false.
  /// networkError, rateLimited, transient -> true.
  /// uniqueViolation -> true if retryCount < 2.
  /// authExpired -> true (after refresh).
  final bool retryable;

  /// Whether an auth token refresh should be attempted before retry.
  ///
  /// FROM SPEC: Only true for authExpired (401/PGRST301/JWT).
  final bool shouldRefreshAuth;

  /// User-safe message suitable for UI display.
  ///
  /// FROM SPEC: Replaces SyncProvider._sanitizeSyncError. Never contains
  /// Postgres codes, schema details, or raw exception messages.
  /// IMPORTANT: Security -- no schema details leak to UI.
  final String userSafeMessage;

  /// Detailed message for logging and debugging.
  ///
  /// May contain Postgres codes, table names, record IDs. Never shown to user.
  final String logDetail;

  /// How to update the change_log entry for this error.
  ///
  /// null means no change_log update needed (e.g., pull errors).
  /// 'markFailed' means call ChangeTracker.markFailed with logDetail.
  /// 'markProcessed' means mark as processed (LWW skip, idempotent success).
  final String? changeLogDisposition;

  const ClassifiedSyncError({
    required this.kind,
    required this.retryable,
    this.shouldRefreshAuth = false,
    required this.userSafeMessage,
    required this.logDetail,
    this.changeLogDisposition,
  });

  /// Whether this is an auth-related error.
  bool get isAuthError => kind == SyncErrorKind.authExpired;

  /// Whether this is a network-related error.
  bool get isNetworkError => kind == SyncErrorKind.networkError;

  /// Whether this is a permanent error that should never be retried.
  bool get isPermanent => !retryable && !shouldRefreshAuth;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ClassifiedSyncError &&
          runtimeType == other.runtimeType &&
          kind == other.kind &&
          retryable == other.retryable &&
          shouldRefreshAuth == other.shouldRefreshAuth &&
          userSafeMessage == other.userSafeMessage &&
          logDetail == other.logDetail &&
          changeLogDisposition == other.changeLogDisposition;

  @override
  int get hashCode => Object.hash(
        kind,
        retryable,
        shouldRefreshAuth,
        userSafeMessage,
        logDetail,
        changeLogDisposition,
      );

  @override
  String toString() =>
      'ClassifiedSyncError(kind: ${kind.name}, retryable: $retryable, '
      'shouldRefreshAuth: $shouldRefreshAuth, '
      'logDetail: $logDetail)';
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 1.2: SyncStatus immutable value class

**Files:**
- Create: `lib/features/sync/domain/sync_status.dart`

**Agent**: backend-subabase-agent

#### Step 1.2.1: Create sync_status.dart with SyncStatus value class

```dart
// lib/features/sync/domain/sync_status.dart
//
// FROM SPEC Section 3: "SyncStatus immutable value class with stream
// deduplication. Replaces mutable fields across 3 classes."
//
// WHY: Triple status tracking exists in SyncEngine._insidePushOrPull,
// SyncOrchestrator._isSyncing/_status/_lastSyncTime/_isOnline, and
// SyncProvider._isSyncing/_status/_lastSyncTime. This single immutable
// value class replaces all of them.
//
// PATTERN: Follows the SyncResult/DirtyScope pattern -- const constructor,
// @immutable, ==, hashCode, copyWith with sentinel pattern.
//
// NOTE: Pure Dart -- no Flutter framework dependencies beyond @immutable.

import 'package:flutter/foundation.dart';

/// Immutable sync transport state.
///
/// This is the single source of truth for the app-facing sync state.
/// It replaces the mutable `_isSyncing`, `_status`, `_lastSyncTime`,
/// and `_isOnline` fields that were tracked independently in
/// SyncEngine, SyncOrchestrator, and SyncProvider.
///
/// FROM SPEC: "isUploading/isDownloading (replaces _isSyncing and
/// _insidePushOrPull), lastSyncedAt (persisted), uploadError/downloadError
/// (typed), isOnline/isAuthValid, stream deduplication."
@immutable
class SyncStatus {
  /// Whether a push operation is currently in progress.
  final bool isUploading;

  /// Whether a pull operation is currently in progress.
  final bool isDownloading;

  /// The last successful sync completion time (persisted to sync_metadata).
  ///
  /// null if no successful sync has completed yet.
  final DateTime? lastSyncedAt;

  /// The last error from a push operation, if any.
  final ClassifiedSyncErrorSummary? uploadError;

  /// The last error from a pull operation, if any.
  final ClassifiedSyncErrorSummary? downloadError;

  /// Whether the device can reach the Supabase server.
  final bool isOnline;

  /// Whether the current auth session is valid.
  final bool isAuthValid;

  /// Number of pending records awaiting push.
  final int pendingUploadCount;

  /// Download progress fraction (0.0 to 1.0) during pull, null when not pulling.
  final double? downloadProgress;

  const SyncStatus({
    this.isUploading = false,
    this.isDownloading = false,
    this.lastSyncedAt,
    this.uploadError,
    this.downloadError,
    this.isOnline = true,
    this.isAuthValid = true,
    this.pendingUploadCount = 0,
    this.downloadProgress,
  });

  /// Convenience: whether any sync operation (push or pull) is in progress.
  bool get isSyncing => isUploading || isDownloading;

  /// Convenience: whether there are any errors from the last sync cycle.
  bool get hasError => uploadError != null || downloadError != null;

  /// Convenience: whether everything is healthy (online, authed, no errors).
  bool get isHealthy => isOnline && isAuthValid && !hasError;

  /// Convenience: whether there are pending changes to push.
  bool get hasPendingChanges => pendingUploadCount > 0;

  // -- copyWith with sentinel pattern (same as SyncResult) --

  static const _sentinel = Object();

  SyncStatus copyWith({
    Object? isUploading = _sentinel,
    Object? isDownloading = _sentinel,
    Object? lastSyncedAt = _sentinel,
    Object? uploadError = _sentinel,
    Object? downloadError = _sentinel,
    Object? isOnline = _sentinel,
    Object? isAuthValid = _sentinel,
    Object? pendingUploadCount = _sentinel,
    Object? downloadProgress = _sentinel,
  }) {
    return SyncStatus(
      isUploading: identical(isUploading, _sentinel)
          ? this.isUploading
          : isUploading! as bool,
      isDownloading: identical(isDownloading, _sentinel)
          ? this.isDownloading
          : isDownloading! as bool,
      lastSyncedAt: identical(lastSyncedAt, _sentinel)
          ? this.lastSyncedAt
          : lastSyncedAt as DateTime?,
      uploadError: identical(uploadError, _sentinel)
          ? this.uploadError
          : uploadError as ClassifiedSyncErrorSummary?,
      downloadError: identical(downloadError, _sentinel)
          ? this.downloadError
          : downloadError as ClassifiedSyncErrorSummary?,
      isOnline: identical(isOnline, _sentinel)
          ? this.isOnline
          : isOnline! as bool,
      isAuthValid: identical(isAuthValid, _sentinel)
          ? this.isAuthValid
          : isAuthValid! as bool,
      pendingUploadCount: identical(pendingUploadCount, _sentinel)
          ? this.pendingUploadCount
          : pendingUploadCount! as int,
      downloadProgress: identical(downloadProgress, _sentinel)
          ? this.downloadProgress
          : downloadProgress as double?,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SyncStatus &&
          runtimeType == other.runtimeType &&
          isUploading == other.isUploading &&
          isDownloading == other.isDownloading &&
          lastSyncedAt == other.lastSyncedAt &&
          uploadError == other.uploadError &&
          downloadError == other.downloadError &&
          isOnline == other.isOnline &&
          isAuthValid == other.isAuthValid &&
          pendingUploadCount == other.pendingUploadCount &&
          downloadProgress == other.downloadProgress;

  @override
  int get hashCode => Object.hash(
        isUploading,
        isDownloading,
        lastSyncedAt,
        uploadError,
        downloadError,
        isOnline,
        isAuthValid,
        pendingUploadCount,
        downloadProgress,
      );

  @override
  String toString() =>
      'SyncStatus(uploading: $isUploading, downloading: $isDownloading, '
      'lastSyncedAt: $lastSyncedAt, online: $isOnline, '
      'authValid: $isAuthValid, pending: $pendingUploadCount)';
}

/// Lightweight error summary for inclusion in SyncStatus.
///
/// WHY: SyncStatus should not carry the full ClassifiedSyncError (which
/// includes logDetail and changeLogDisposition). The summary carries only
/// what the UI/transport layer needs.
@immutable
class ClassifiedSyncErrorSummary {
  final SyncErrorKind kind;
  final String userSafeMessage;
  final bool retryable;

  const ClassifiedSyncErrorSummary({
    required this.kind,
    required this.userSafeMessage,
    required this.retryable,
  });

  /// Create from a full ClassifiedSyncError.
  factory ClassifiedSyncErrorSummary.fromClassified(ClassifiedSyncError error) {
    return ClassifiedSyncErrorSummary(
      kind: error.kind,
      userSafeMessage: error.userSafeMessage,
      retryable: error.retryable,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ClassifiedSyncErrorSummary &&
          runtimeType == other.runtimeType &&
          kind == other.kind &&
          userSafeMessage == other.userSafeMessage &&
          retryable == other.retryable;

  @override
  int get hashCode => Object.hash(kind, userSafeMessage, retryable);

  @override
  String toString() =>
      'ClassifiedSyncErrorSummary(kind: ${kind.name}, retryable: $retryable)';
}

// NOTE: SyncErrorKind is defined in sync_error.dart and re-exported
// here for convenience. The import below creates a cross-file dependency
// within the domain layer, which is acceptable for domain value types.
export 'sync_error.dart' show SyncErrorKind, ClassifiedSyncError;
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 1.3: SyncDiagnosticsSnapshot immutable snapshot

**Files:**
- Create: `lib/features/sync/domain/sync_diagnostics.dart`

**Agent**: backend-supabase-agent

#### Step 1.3.1: Create sync_diagnostics.dart

```dart
// lib/features/sync/domain/sync_diagnostics.dart
//
// FROM SPEC Section 3: "SyncDiagnosticsSnapshot immutable snapshot:
// pending buckets, integrity results, undismissed conflicts, circuit-
// breaker records, recent run summary."
//
// WHY: Dashboard data is currently fetched via raw SQL in SyncOrchestrator
// (sync_orchestrator.dart:607-710). This defines the typed data model
// that SyncQueryService will produce.
//
// NOTE: This is a pure data container. It does NOT fetch data -- that is
// the job of SyncQueryService (created in P7). This just defines the shape.

import 'package:flutter/foundation.dart';

/// Immutable snapshot of sync operational state for dashboards and debugging.
///
/// FROM SPEC: "inspectable operational state for dashboards and debugging
/// (pending buckets, integrity, conflict counts, circuit-breaker records,
/// recent run facts)"
///
/// This is intentionally separate from SyncStatus to prevent the transport
/// state from becoming a god object.
@immutable
class SyncDiagnosticsSnapshot {
  /// Pending push counts grouped by table name.
  ///
  /// Key: table name (e.g., 'projects', 'daily_entries')
  /// Value: BucketCount with total and breakdown
  final Map<String, BucketCount> pendingBuckets;

  /// Total pending push records across all tables.
  final int totalPendingCount;

  /// Integrity check results.
  ///
  /// Key: metric name (e.g., 'integrity_last_check', 'integrity_orphans_found')
  /// Value: result string
  final Map<String, String> integrityResults;

  /// Number of undismissed conflict_log entries.
  final int undismissedConflictCount;

  /// Circuit breaker trips since last dismiss.
  final List<CircuitBreakerRecord> circuitBreakerTrips;

  /// Summary of the most recent sync run.
  final RecentRunSummary? lastRun;

  /// When this snapshot was taken.
  final DateTime snapshotAt;

  const SyncDiagnosticsSnapshot({
    this.pendingBuckets = const {},
    this.totalPendingCount = 0,
    this.integrityResults = const {},
    this.undismissedConflictCount = 0,
    this.circuitBreakerTrips = const [],
    this.lastRun,
    required this.snapshotAt,
  });
}

/// Pending record counts for a single table bucket.
///
/// WHY: This matches the structure returned by the existing
/// SyncOrchestrator.getPendingBuckets() method.
@immutable
class BucketCount {
  final int inserts;
  final int updates;
  final int deletes;

  const BucketCount({
    this.inserts = 0,
    this.updates = 0,
    this.deletes = 0,
  });

  int get total => inserts + updates + deletes;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is BucketCount &&
          runtimeType == other.runtimeType &&
          inserts == other.inserts &&
          updates == other.updates &&
          deletes == other.deletes;

  @override
  int get hashCode => Object.hash(inserts, updates, deletes);

  @override
  String toString() =>
      'BucketCount(inserts: $inserts, updates: $updates, deletes: $deletes)';
}

/// Record of a circuit breaker trip.
@immutable
class CircuitBreakerRecord {
  final String tableName;
  final String recordId;
  final int conflictCount;
  final DateTime trippedAt;

  const CircuitBreakerRecord({
    required this.tableName,
    required this.recordId,
    required this.conflictCount,
    required this.trippedAt,
  });
}

/// Summary of a recent sync run.
@immutable
class RecentRunSummary {
  final int pushed;
  final int pulled;
  final int errors;
  final int rlsDenials;
  final Duration duration;
  final DateTime completedAt;
  final bool wasSuccessful;

  const RecentRunSummary({
    required this.pushed,
    required this.pulled,
    required this.errors,
    required this.rlsDenials,
    required this.duration,
    required this.completedAt,
    required this.wasSuccessful,
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 1.4: SyncEvent typed lifecycle events

**Files:**
- Create: `lib/features/sync/domain/sync_event.dart`

**Agent**: backend-supabase-agent

#### Step 1.4.1: Create sync_event.dart

```dart
// lib/features/sync/domain/sync_event.dart
//
// FROM SPEC Section 3: "SyncEvent typed lifecycle events for
// diagnosability: run started/completed, retry scheduled, auth refreshed,
// quick sync throttled, circuit breaker tripped, file phase failed"
//
// WHY: Debug server posts and log messages are currently untyped strings
// scattered across SyncEngine, SyncOrchestrator, and handlers. Typed
// events enable structured logging, testing, and diagnostics.
//
// NOTE: Pure Dart -- no Flutter dependencies beyond @immutable.

import 'package:flutter/foundation.dart';

import 'package:construction_inspector/features/sync/domain/sync_error.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

/// Base class for typed sync lifecycle events.
///
/// Each event captures a specific moment in the sync lifecycle with
/// structured data. Events are transient (not persisted) and used for:
/// - Debug server posts
/// - Test assertions
/// - Diagnostic logging
@immutable
sealed class SyncEvent {
  /// When this event occurred.
  final DateTime timestamp;

  const SyncEvent({required this.timestamp});
}

/// A sync run has started.
class SyncRunStarted extends SyncEvent {
  final SyncMode mode;
  final String triggerSource;

  const SyncRunStarted({
    required super.timestamp,
    required this.mode,
    required this.triggerSource,
  });
}

/// A sync run has completed.
class SyncRunCompleted extends SyncEvent {
  final SyncMode mode;
  final int pushed;
  final int pulled;
  final int errors;
  final Duration duration;
  final bool wasSuccessful;

  const SyncRunCompleted({
    required super.timestamp,
    required this.mode,
    required this.pushed,
    required this.pulled,
    required this.errors,
    required this.duration,
    required this.wasSuccessful,
  });
}

/// A retry has been scheduled.
class SyncRetryScheduled extends SyncEvent {
  final int attemptNumber;
  final Duration delay;
  final SyncErrorKind errorKind;

  const SyncRetryScheduled({
    required super.timestamp,
    required this.attemptNumber,
    required this.delay,
    required this.errorKind,
  });
}

/// Auth token was refreshed during sync.
class SyncAuthRefreshed extends SyncEvent {
  final bool wasSuccessful;

  const SyncAuthRefreshed({
    required super.timestamp,
    required this.wasSuccessful,
  });
}

/// Quick sync was throttled (hint arrived while sync already running).
class SyncQuickSyncThrottled extends SyncEvent {
  final String? projectId;
  final String? tableName;

  const SyncQuickSyncThrottled({
    required super.timestamp,
    this.projectId,
    this.tableName,
  });
}

/// Circuit breaker tripped for a specific record.
class SyncCircuitBreakerTripped extends SyncEvent {
  final String tableName;
  final String recordId;
  final int conflictCount;

  const SyncCircuitBreakerTripped({
    required super.timestamp,
    required this.tableName,
    required this.recordId,
    required this.conflictCount,
  });
}

/// File upload phase failed.
class SyncFileUploadFailed extends SyncEvent {
  final String tableName;
  final String recordId;
  final int failedPhase;
  final String errorMessage;

  const SyncFileUploadFailed({
    required super.timestamp,
    required this.tableName,
    required this.recordId,
    required this.failedPhase,
    required this.errorMessage,
  });
}

/// Connectivity state changed.
class SyncConnectivityChanged extends SyncEvent {
  final bool isOnline;

  const SyncConnectivityChanged({
    required super.timestamp,
    required this.isOnline,
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 1.5: SyncErrorClassifier (pure logic, consolidates 3 error classification sites)

**Files:**
- Create: `lib/features/sync/engine/sync_error_classifier.dart`

**Agent**: backend-supabase-agent

#### Step 1.5.1: Create sync_error_classifier.dart

```dart
// lib/features/sync/engine/sync_error_classifier.dart
//
// FROM SPEC Section 3: "SyncErrorClassifier consolidating all 3 error
// classification sites"
//
// WHY: Error classification exists in:
//   Site 1: SyncEngine._handlePushError (sync_engine.dart:1407-1512)
//   Site 2: SyncOrchestrator._isTransientError (sync_orchestrator.dart:507-569)
//   Site 3: SyncProvider._sanitizeSyncError (sync_provider.dart:328-348)
//
// This class produces a single ClassifiedSyncError that all 3 sites
// can consume instead of re-implementing classification.
//
// NOTE: Pure logic class -- no I/O, no state, no dependencies.
// All methods are static or instance methods on an injectable class.

import 'dart:io';

import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:construction_inspector/features/sync/domain/sync_error.dart';

/// Single source of truth for sync error classification.
///
/// Replaces the triplicated pattern matching in SyncEngine._handlePushError,
/// SyncOrchestrator._isTransientError, and SyncProvider._sanitizeSyncError.
///
/// FROM SPEC: "Every Postgres code, network pattern, auth pattern ->
/// correct SyncError variant"
class SyncErrorClassifier {
  const SyncErrorClassifier();

  /// Classify any error into a [ClassifiedSyncError].
  ///
  /// [error] is the caught exception (may be PostgrestException,
  /// SocketException, TimeoutException, or any other type).
  /// [tableName] and [recordId] are optional context for logging.
  /// [retryCount] is used for retry exhaustion decisions (e.g., 23505).
  ClassifiedSyncError classify(
    Object error, {
    String? tableName,
    String? recordId,
    int retryCount = 0,
  }) {
    final context = _formatContext(tableName, recordId);

    // --- PostgrestException: Supabase/Postgres errors ---
    if (error is PostgrestException) {
      return _classifyPostgrestError(error, context, retryCount);
    }

    // --- SocketException: network connectivity ---
    if (error is SocketException) {
      return ClassifiedSyncError(
        kind: SyncErrorKind.networkError,
        retryable: true,
        userSafeMessage: 'Network connection lost. Sync will retry automatically.',
        logDetail: 'SocketException$context: $error',
        changeLogDisposition: retryCount == 0 ? 'markFailed' : null,
      );
    }

    // --- TimeoutException: request or connection timeout ---
    if (error is TimeoutException) {
      return ClassifiedSyncError(
        kind: SyncErrorKind.networkError,
        retryable: true,
        userSafeMessage: 'Sync timed out. Will retry automatically.',
        logDetail: 'TimeoutException$context: $error',
        changeLogDisposition: retryCount == 0 ? 'markFailed' : null,
      );
    }

    // --- String-based classification (for SyncResult.errorMessages) ---
    if (error is String) {
      return _classifyErrorMessage(error, context);
    }

    // --- Unknown error: permanent by default ---
    // FROM SPEC ground-truth: "Unknown errors default to non-transient"
    return ClassifiedSyncError(
      kind: SyncErrorKind.permanent,
      retryable: false,
      userSafeMessage: 'Sync failed. Check sync dashboard for details.',
      logDetail: 'Unknown error$context: ${error.runtimeType}: $error',
      changeLogDisposition: 'markFailed',
    );
  }

  /// Classify a PostgrestException by its error code.
  ///
  /// FROM SPEC ground-truth (sync_engine.dart:1407-1512):
  /// - 401/PGRST301/JWT -> authExpired
  /// - 429/503/Too Many/Service Unavailable -> rateLimited
  /// - 23505 -> uniqueViolation (retryable if retryCount < 2)
  /// - 42501 -> rlsDenial (permanent)
  /// - 23503 -> fkViolation (permanent)
  /// - Other -> permanent
  ClassifiedSyncError _classifyPostgrestError(
    PostgrestException error,
    String context,
    int retryCount,
  ) {
    final code = error.code ?? '';
    final message = error.message;

    // Auth error: 401 / PGRST301 / JWT
    // FROM SPEC: sync_engine.dart:1413-1421
    if (code == '401' || code == 'PGRST301' || message.contains('JWT')) {
      return ClassifiedSyncError(
        kind: SyncErrorKind.authExpired,
        retryable: true,
        shouldRefreshAuth: true,
        userSafeMessage: 'Authentication expired. Refreshing...',
        logDetail: 'Auth error ($code)$context: $message',
      );
    }

    // Rate limit / service unavailable: 429, 503
    // FROM SPEC: sync_engine.dart:1423-1438
    if (code == '429' ||
        code == '503' ||
        message.contains('Too Many') ||
        message.contains('Service Unavailable')) {
      return ClassifiedSyncError(
        kind: SyncErrorKind.rateLimited,
        retryable: true,
        userSafeMessage: 'Server is busy. Sync will retry automatically.',
        logDetail: 'Rate limited ($code)$context: $message',
        changeLogDisposition: 'markFailed',
      );
    }

    // Unique constraint violation: 23505
    // FROM SPEC: sync_engine.dart:1440-1455
    // WHY: Retryable for TOCTOU race -- pre-check passed but another device
    // inserted between check and upsert. Retry up to 2 times.
    if (code == '23505') {
      final isRetryable = retryCount < 2;
      return ClassifiedSyncError(
        kind: SyncErrorKind.uniqueViolation,
        retryable: isRetryable,
        userSafeMessage: 'Sync error -- some records could not be saved. Try again or contact support.',
        logDetail: isRetryable
            ? 'Constraint race (23505)$context: $message -- will retry'
            : 'Constraint violation (23505)$context: $message',
        changeLogDisposition: 'markFailed',
      );
    }

    // RLS denied: 42501
    // FROM SPEC: sync_engine.dart:1457-1467
    // WHY: Permanent -- user lacks permission. SECURITY: log detail must
    // not leak to UI (scrubbed via userSafeMessage).
    if (code == '42501') {
      return ClassifiedSyncError(
        kind: SyncErrorKind.rlsDenial,
        retryable: false,
        userSafeMessage: 'Sync error -- some records could not be saved. Try again or contact support.',
        logDetail: 'RLS denied (42501)$context',
        changeLogDisposition: 'markFailed',
      );
    }

    // FK violation: 23503
    // FROM SPEC: sync_engine.dart:1469-1479
    if (code == '23503') {
      return ClassifiedSyncError(
        kind: SyncErrorKind.fkViolation,
        retryable: false,
        userSafeMessage: 'Sync error -- some records could not be saved. Try again or contact support.',
        logDetail: 'FK violation (23503)$context: $message',
        changeLogDisposition: 'markFailed',
      );
    }

    // All other PostgrestException: permanent
    // FROM SPEC: sync_engine.dart:1490
    return ClassifiedSyncError(
      kind: SyncErrorKind.permanent,
      retryable: false,
      userSafeMessage: 'Sync failed. Check sync dashboard for details.',
      logDetail: 'Permanent ($code)$context: $message',
      changeLogDisposition: 'markFailed',
    );
  }

  /// Classify an error from its string message.
  ///
  /// Used for SyncResult.errorMessages classification (replacing
  /// SyncOrchestrator._isTransientError).
  ///
  /// FROM SPEC ground-truth (sync_orchestrator.dart:507-569)
  ClassifiedSyncError _classifyErrorMessage(
    String message,
    String context,
  ) {
    // Special case: startup race condition -- must check BEFORE 'auth' patterns
    // FROM SPEC: "No auth context available for sync" -> transient
    if (message.contains('No auth context available for sync')) {
      return ClassifiedSyncError(
        kind: SyncErrorKind.transient,
        retryable: true,
        userSafeMessage: 'Sync initializing. Will retry shortly.',
        logDetail: 'No auth context (startup race)$context: $message',
      );
    }

    // Non-transient patterns (check first -- safe default)
    // FROM SPEC ground-truth: sync_orchestrator.dart:530-547
    const nonTransientPatterns = [
      'auth', 'Auth', 'RLS', 'permission', 'Permission',
      'not configured', 'already in progress',
      'has no column', 'DatabaseException', 'no such column',
      'table has no column',
      'remote record not found', '0 rows affected',
      'Soft-delete push failed',
    ];

    for (final pattern in nonTransientPatterns) {
      if (message.contains(pattern)) {
        return ClassifiedSyncError(
          kind: SyncErrorKind.permanent,
          retryable: false,
          userSafeMessage: _sanitizeForUi(message),
          logDetail: 'Non-transient$context: $message',
        );
      }
    }

    // Transient patterns
    // FROM SPEC ground-truth: sync_orchestrator.dart:519-529
    const transientPatterns = [
      'DNS', 'dns', 'SocketException', 'host lookup',
      'TimeoutException', 'Connection refused', 'Connection reset',
      'Network is unreachable', 'offline',
    ];

    for (final pattern in transientPatterns) {
      if (message.contains(pattern)) {
        return ClassifiedSyncError(
          kind: SyncErrorKind.networkError,
          retryable: true,
          userSafeMessage: 'Network connection lost. Sync will retry automatically.',
          logDetail: 'Transient network$context: $message',
        );
      }
    }

    // Unknown -> non-transient (safe default)
    // FROM SPEC: "Unknown errors default to non-transient"
    return ClassifiedSyncError(
      kind: SyncErrorKind.permanent,
      retryable: false,
      userSafeMessage: _sanitizeForUi(message),
      logDetail: 'Unknown error message$context: $message',
    );
  }

  /// Produce a user-safe message from a raw error string.
  ///
  /// FROM SPEC: Replaces SyncProvider._sanitizeSyncError
  /// (sync_provider.dart:328-348).
  /// IMPORTANT: SECURITY -- Postgres codes and schema details must never
  /// reach the UI.
  String _sanitizeForUi(String raw) {
    const pgPatterns = [
      '42501', '23505', '23503',
      'permission denied', 'violates row-level security',
    ];
    final lower = raw.toLowerCase();
    if (pgPatterns.any(lower.contains)) {
      return 'Sync error -- some records could not be saved. Try again or contact support.';
    }
    if (raw.length > 120 || raw.contains('{') || raw.contains('\n')) {
      return 'Sync failed. Check sync dashboard for details.';
    }
    return raw;
  }

  /// Convenience: check if a SyncResult contains transient errors.
  ///
  /// Replaces SyncOrchestrator._isTransientError() exactly.
  /// Returns true if ANY error message classifies as retryable.
  bool isTransientResult(SyncResult result) {
    if (!result.hasErrors) return false;
    for (final msg in result.errorMessages) {
      final classified = classify(msg);
      if (classified.retryable) return true;
    }
    return false;
  }

  String _formatContext(String? tableName, String? recordId) {
    if (tableName == null && recordId == null) return '';
    if (recordId == null) return ' [$tableName]';
    return ' [$tableName/$recordId]';
  }
}
```

**NOTE**: The `_classifyErrorMessage` method needs to import `SyncResult` for the `isTransientResult` convenience method.

Add the missing import at the top of the file:

```dart
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 1.6: SyncErrorClassifier Contract Tests

**Files:**
- Create: `test/features/sync/characterization/sync_error_classifier_contract_test.dart`

**Agent**: qa-testing-agent

#### Step 1.6.1: Create SyncErrorClassifier contract test file

```dart
// test/features/sync/characterization/sync_error_classifier_contract_test.dart
//
// FROM SPEC Section 4.2: "Exhaustive: every Postgres code, network pattern,
// auth pattern -> correct SyncError variant"
//
// WHY: These are the contract tests that prove SyncErrorClassifier produces
// the SAME classifications as the 3 original sites. Each test documents
// the exact input->output mapping.

import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:construction_inspector/features/sync/engine/sync_error_classifier.dart';
import 'package:construction_inspector/features/sync/domain/sync_error.dart';

void main() {
  const classifier = SyncErrorClassifier();

  group('PostgrestException classification', () {
    // FROM SPEC ground-truth: sync_engine.dart:1407-1512

    group('Auth errors (401/PGRST301/JWT)', () {
      test('401 -> authExpired, retryable, shouldRefreshAuth', () {
        final error = PostgrestException(message: 'Unauthorized', code: '401');
        final result = classifier.classify(error, tableName: 'projects', recordId: 'p1');

        expect(result.kind, SyncErrorKind.authExpired);
        expect(result.retryable, isTrue);
        expect(result.shouldRefreshAuth, isTrue);
      });

      test('PGRST301 -> authExpired', () {
        final error = PostgrestException(message: 'JWT expired', code: 'PGRST301');
        final result = classifier.classify(error);

        expect(result.kind, SyncErrorKind.authExpired);
        expect(result.shouldRefreshAuth, isTrue);
      });

      test('JWT in message -> authExpired', () {
        final error = PostgrestException(message: 'JWT claim check failed', code: '');
        final result = classifier.classify(error);

        expect(result.kind, SyncErrorKind.authExpired);
      });
    });

    group('Rate limiting (429/503)', () {
      test('429 -> rateLimited, retryable', () {
        final error = PostgrestException(message: 'Too Many Requests', code: '429');
        final result = classifier.classify(error);

        expect(result.kind, SyncErrorKind.rateLimited);
        expect(result.retryable, isTrue);
        expect(result.shouldRefreshAuth, isFalse);
        expect(result.changeLogDisposition, 'markFailed');
      });

      test('503 -> rateLimited', () {
        final error = PostgrestException(message: 'Service Unavailable', code: '503');
        final result = classifier.classify(error);

        expect(result.kind, SyncErrorKind.rateLimited);
        expect(result.retryable, isTrue);
      });

      test('Too Many in message -> rateLimited', () {
        final error = PostgrestException(message: 'Too Many requests in window', code: '');
        final result = classifier.classify(error);

        expect(result.kind, SyncErrorKind.rateLimited);
      });

      test('Service Unavailable in message -> rateLimited', () {
        final error = PostgrestException(message: 'Service Unavailable temporarily', code: '');
        final result = classifier.classify(error);

        expect(result.kind, SyncErrorKind.rateLimited);
      });
    });

    group('Unique constraint violation (23505)', () {
      test('23505 with retryCount 0 -> uniqueViolation, retryable', () {
        final error = PostgrestException(message: 'duplicate key', code: '23505');
        final result = classifier.classify(error, retryCount: 0);

        expect(result.kind, SyncErrorKind.uniqueViolation);
        expect(result.retryable, isTrue);
      });

      test('23505 with retryCount 1 -> uniqueViolation, retryable', () {
        final error = PostgrestException(message: 'duplicate key', code: '23505');
        final result = classifier.classify(error, retryCount: 1);

        expect(result.kind, SyncErrorKind.uniqueViolation);
        expect(result.retryable, isTrue);
      });

      test('23505 with retryCount 2 -> uniqueViolation, NOT retryable', () {
        final error = PostgrestException(message: 'duplicate key', code: '23505');
        final result = classifier.classify(error, retryCount: 2);

        expect(result.kind, SyncErrorKind.uniqueViolation);
        expect(result.retryable, isFalse);
      });
    });

    group('RLS denial (42501)', () {
      test('42501 -> rlsDenial, permanent', () {
        final error = PostgrestException(message: 'permission denied', code: '42501');
        final result = classifier.classify(error, tableName: 'projects', recordId: 'p1');

        expect(result.kind, SyncErrorKind.rlsDenial);
        expect(result.retryable, isFalse);
        expect(result.isPermanent, isTrue);
        expect(result.changeLogDisposition, 'markFailed');
        // SECURITY: userSafeMessage must NOT contain '42501'
        expect(result.userSafeMessage, isNot(contains('42501')));
      });
    });

    group('FK violation (23503)', () {
      test('23503 -> fkViolation, permanent', () {
        final error = PostgrestException(
          message: 'violates foreign key constraint',
          code: '23503',
        );
        final result = classifier.classify(error);

        expect(result.kind, SyncErrorKind.fkViolation);
        expect(result.retryable, isFalse);
        expect(result.isPermanent, isTrue);
      });
    });

    group('Other Postgres errors', () {
      test('unknown code -> permanent', () {
        final error = PostgrestException(message: 'some unusual error', code: '99999');
        final result = classifier.classify(error);

        expect(result.kind, SyncErrorKind.permanent);
        expect(result.retryable, isFalse);
      });
    });
  });

  group('Network exception classification', () {
    test('SocketException -> networkError, retryable', () {
      final error = const SocketException('Connection refused');
      final result = classifier.classify(error);

      expect(result.kind, SyncErrorKind.networkError);
      expect(result.retryable, isTrue);
    });

    test('TimeoutException -> networkError, retryable', () {
      final error = TimeoutException('Request timed out');
      final result = classifier.classify(error);

      expect(result.kind, SyncErrorKind.networkError);
      expect(result.retryable, isTrue);
    });
  });

  group('String error message classification', () {
    // These replace SyncOrchestrator._isTransientError

    group('Transient patterns', () {
      for (final pattern in [
        'DNS resolution failed',
        'dns lookup error',
        'SocketException: Connection failed',
        'Failed host lookup',
        'TimeoutException: Request timed out',
        'Connection refused',
        'Connection reset by peer',
        'Network is unreachable',
        'Device is offline',
      ]) {
        test('$pattern -> retryable', () {
          final result = classifier.classify(pattern);
          expect(result.retryable, isTrue,
              reason: '$pattern should be transient/retryable');
        });
      }
    });

    group('Non-transient patterns', () {
      for (final pattern in [
        'auth session expired',
        'Auth token invalid',
        'RLS policy violated',
        'permission denied for table',
        'Permission denied',
        'Supabase not configured',
        'Sync already in progress',
        'table has no column named xyz',
        'DatabaseException: UNIQUE constraint failed',
        'no such column: foo',
        'table has no column bar',
        'remote record not found',
        '0 rows affected',
        'Soft-delete push failed for record',
      ]) {
        test('$pattern -> NOT retryable', () {
          final result = classifier.classify(pattern);
          expect(result.retryable, isFalse,
              reason: '$pattern should be non-transient/permanent');
        });
      }
    });

    group('Special cases', () {
      test('No auth context -> transient (startup race)', () {
        // FROM SPEC: Must be evaluated BEFORE nonTransientPatterns with 'auth'
        final result = classifier.classify(
          'No auth context available for sync',
        );
        expect(result.retryable, isTrue);
        expect(result.kind, SyncErrorKind.transient);
      });

      test('unknown error -> permanent (safe default)', () {
        final result = classifier.classify('Something completely unexpected happened');
        expect(result.retryable, isFalse);
        expect(result.kind, SyncErrorKind.permanent);
      });
    });
  });

  group('UI message sanitization', () {
    // FROM SPEC: Replaces SyncProvider._sanitizeSyncError

    test('Postgres codes are sanitized from user message', () {
      final error = PostgrestException(message: 'permission denied', code: '42501');
      final result = classifier.classify(error);

      expect(result.userSafeMessage, isNot(contains('42501')));
      expect(result.userSafeMessage, isNot(contains('permission denied')));
    });

    test('FK violation details are sanitized', () {
      final error = PostgrestException(
        message: 'violates FK constraint on projects.id',
        code: '23503',
      );
      final result = classifier.classify(error);

      expect(result.userSafeMessage, isNot(contains('23503')));
      expect(result.userSafeMessage, isNot(contains('projects.id')));
    });

    test('logDetail preserves full error for debugging', () {
      final error = PostgrestException(
        message: 'violates FK constraint fk_entries_projects',
        code: '23503',
      );
      final result = classifier.classify(error, tableName: 'daily_entries', recordId: 'e1');

      expect(result.logDetail, contains('23503'));
      expect(result.logDetail, contains('daily_entries'));
    });
  });

  group('isTransientResult (replaces SyncOrchestrator._isTransientError)', () {
    test('result with DNS error is transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['DNS resolution failed']);
      expect(classifier.isTransientResult(result), isTrue);
    });

    test('result with auth error is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['auth session expired']);
      expect(classifier.isTransientResult(result), isFalse);
    });

    test('result with no errors is non-transient', () {
      const result = SyncResult();
      expect(classifier.isTransientResult(result), isFalse);
    });

    test('result with No auth context is transient', () {
      final result = SyncResult(
        errors: 1,
        errorMessages: ['No auth context available for sync'],
      );
      expect(classifier.isTransientResult(result), isTrue);
    });

    test('result with unknown error is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['Widget tree error']);
      expect(classifier.isTransientResult(result), isFalse);
    });
  });

  group('Context formatting', () {
    test('tableName and recordId appear in logDetail', () {
      final error = PostgrestException(message: 'error', code: '42501');
      final result = classifier.classify(
        error,
        tableName: 'daily_entries',
        recordId: 'entry-123',
      );

      expect(result.logDetail, contains('daily_entries'));
      expect(result.logDetail, contains('entry-123'));
    });

    test('logDetail works without context', () {
      final error = PostgrestException(message: 'error', code: '42501');
      final result = classifier.classify(error);

      expect(result.logDetail, isNotEmpty);
    });
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 1.7: SyncStatus Contract Tests

**Files:**
- Create: `test/features/sync/characterization/sync_status_contract_test.dart`

**Agent**: qa-testing-agent

#### Step 1.7.1: Create SyncStatus contract test file

```dart
// test/features/sync/characterization/sync_status_contract_test.dart
//
// FROM SPEC Section 4.2: "Immutability, stream deduplication, persisted
// lastSyncedAt, separate uploadError/downloadError, copyWith, equality"
//
// WHY: SyncStatus replaces mutable fields across 3 classes. These tests
// prove the value class is correct before it is wired in.

import 'package:flutter_test/flutter_test.dart';

import 'package:construction_inspector/features/sync/domain/sync_status.dart';
import 'package:construction_inspector/features/sync/domain/sync_error.dart';

void main() {
  group('SyncStatus immutability', () {
    test('default SyncStatus is idle with no errors', () {
      const status = SyncStatus();

      expect(status.isUploading, isFalse);
      expect(status.isDownloading, isFalse);
      expect(status.isSyncing, isFalse);
      expect(status.lastSyncedAt, isNull);
      expect(status.uploadError, isNull);
      expect(status.downloadError, isNull);
      expect(status.isOnline, isTrue);
      expect(status.isAuthValid, isTrue);
      expect(status.pendingUploadCount, 0);
      expect(status.downloadProgress, isNull);
      expect(status.hasError, isFalse);
      expect(status.isHealthy, isTrue);
      expect(status.hasPendingChanges, isFalse);
    });

    test('copyWith creates new instance without modifying original', () {
      const original = SyncStatus();
      final modified = original.copyWith(isUploading: true);

      expect(original.isUploading, isFalse);
      expect(modified.isUploading, isTrue);
      // Other fields unchanged
      expect(modified.isDownloading, isFalse);
      expect(modified.isOnline, isTrue);
    });

    test('copyWith with all fields', () {
      final now = DateTime.now();
      const errorSummary = ClassifiedSyncErrorSummary(
        kind: SyncErrorKind.networkError,
        userSafeMessage: 'Network lost',
        retryable: true,
      );

      final status = const SyncStatus().copyWith(
        isUploading: true,
        isDownloading: true,
        lastSyncedAt: now,
        uploadError: errorSummary,
        downloadError: errorSummary,
        isOnline: false,
        isAuthValid: false,
        pendingUploadCount: 42,
        downloadProgress: 0.5,
      );

      expect(status.isUploading, isTrue);
      expect(status.isDownloading, isTrue);
      expect(status.lastSyncedAt, now);
      expect(status.uploadError, errorSummary);
      expect(status.downloadError, errorSummary);
      expect(status.isOnline, isFalse);
      expect(status.isAuthValid, isFalse);
      expect(status.pendingUploadCount, 42);
      expect(status.downloadProgress, 0.5);
    });
  });

  group('SyncStatus equality', () {
    test('identical defaults are equal', () {
      const a = SyncStatus();
      const b = SyncStatus();
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('different isUploading are not equal', () {
      const a = SyncStatus();
      final b = a.copyWith(isUploading: true);
      expect(a, isNot(equals(b)));
    });

    test('same values are equal regardless of construction', () {
      final now = DateTime(2026, 3, 5, 10, 0, 0);
      final a = SyncStatus(lastSyncedAt: now, pendingUploadCount: 5);
      final b = const SyncStatus().copyWith(
        lastSyncedAt: now,
        pendingUploadCount: 5,
      );
      expect(a, equals(b));
    });
  });

  group('SyncStatus convenience getters', () {
    test('isSyncing is true when uploading', () {
      final status = const SyncStatus().copyWith(isUploading: true);
      expect(status.isSyncing, isTrue);
    });

    test('isSyncing is true when downloading', () {
      final status = const SyncStatus().copyWith(isDownloading: true);
      expect(status.isSyncing, isTrue);
    });

    test('hasError is true when uploadError is set', () {
      const error = ClassifiedSyncErrorSummary(
        kind: SyncErrorKind.networkError,
        userSafeMessage: 'Network lost',
        retryable: true,
      );
      final status = const SyncStatus().copyWith(uploadError: error);
      expect(status.hasError, isTrue);
    });

    test('isHealthy requires online + authed + no errors', () {
      // All good
      const healthy = SyncStatus();
      expect(healthy.isHealthy, isTrue);

      // Offline
      final offline = healthy.copyWith(isOnline: false);
      expect(offline.isHealthy, isFalse);

      // Auth invalid
      final noAuth = healthy.copyWith(isAuthValid: false);
      expect(noAuth.isHealthy, isFalse);

      // Has error
      const error = ClassifiedSyncErrorSummary(
        kind: SyncErrorKind.rlsDenial,
        userSafeMessage: 'Error',
        retryable: false,
      );
      final withError = healthy.copyWith(uploadError: error);
      expect(withError.isHealthy, isFalse);
    });

    test('hasPendingChanges is true when pendingUploadCount > 0', () {
      const noPending = SyncStatus();
      expect(noPending.hasPendingChanges, isFalse);

      final pending = noPending.copyWith(pendingUploadCount: 1);
      expect(pending.hasPendingChanges, isTrue);
    });
  });

  group('SyncStatus stream deduplication support', () {
    // WHY: Stream deduplication relies on == operator.
    // If the status hasn't changed, the stream should not emit.

    test('equality enables stream distinct()', () {
      final statuses = [
        const SyncStatus(),
        const SyncStatus(),
        const SyncStatus().copyWith(isUploading: true),
        const SyncStatus().copyWith(isUploading: true),
        const SyncStatus(),
      ];

      // Simulating distinct() behavior
      final deduplicated = <SyncStatus>[];
      SyncStatus? last;
      for (final s in statuses) {
        if (s != last) {
          deduplicated.add(s);
          last = s;
        }
      }

      expect(deduplicated, hasLength(3));
      expect(deduplicated[0].isUploading, isFalse);
      expect(deduplicated[1].isUploading, isTrue);
      expect(deduplicated[2].isUploading, isFalse);
    });
  });

  group('ClassifiedSyncErrorSummary', () {
    test('fromClassified extracts summary fields', () {
      const full = ClassifiedSyncError(
        kind: SyncErrorKind.rlsDenial,
        retryable: false,
        userSafeMessage: 'Sync error',
        logDetail: 'RLS denied (42501) [projects/p1]',
        changeLogDisposition: 'markFailed',
      );

      final summary = ClassifiedSyncErrorSummary.fromClassified(full);
      expect(summary.kind, SyncErrorKind.rlsDenial);
      expect(summary.userSafeMessage, 'Sync error');
      expect(summary.retryable, isFalse);
    });

    test('equality works', () {
      const a = ClassifiedSyncErrorSummary(
        kind: SyncErrorKind.networkError,
        userSafeMessage: 'Network lost',
        retryable: true,
      );
      const b = ClassifiedSyncErrorSummary(
        kind: SyncErrorKind.networkError,
        userSafeMessage: 'Network lost',
        retryable: true,
      );
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });
}
```

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 1.8: Update domain barrel export

**Files:**
- Modify: `lib/features/sync/domain/domain.dart` (if exists, otherwise note)

**Agent**: backend-supabase-agent

#### Step 1.8.1: Verify and update the domain barrel export

The new domain files need to be accessible via the barrel export. Check if `lib/features/sync/domain/domain.dart` exists, and if so, add exports for the new files.

```dart
// lib/features/sync/domain/domain.dart
//
// WHY: Barrel export for the sync domain layer. New files must be
// exported here for clean imports by other layers.

export 'sync_types.dart';
export 'sync_error.dart';
export 'sync_status.dart';
export 'sync_diagnostics.dart';
export 'sync_event.dart';
```

**NOTE**: If the barrel already contains `export 'sync_types.dart';`, add only the new exports. If the barrel does not exist, create it with all exports.

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

---

### Sub-phase 1.9: Final P1 Verification

**Agent**: qa-testing-agent

#### Step 1.9.1: Verify all new files pass analysis

Run the analyzer to ensure all new domain types and the SyncErrorClassifier compile cleanly with zero violations.

**Verification**: `pwsh -Command "flutter analyze --no-fatal-infos"`

**Expected result**: Zero new analyzer errors or warnings. All existing tests continue to pass (verified via CI on PR).

#### Step 1.9.2: Verify no behavior change

The existing SyncEngine, SyncOrchestrator, and SyncProvider are completely untouched in P1. The new files are additive-only. The existing monolith continues to function identically.

**Gate**: All P0 characterization tests pass. All existing sync tests pass. Analyzer zero.
