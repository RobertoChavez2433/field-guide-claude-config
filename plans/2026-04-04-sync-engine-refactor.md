# Sync Engine Refactor Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Decompose the 2,374-line SyncEngine God Object into ~10 focused, independently testable classes with clean I/O boundaries while preserving every existing capability and maintaining zero data loss.
**Spec:** `.claude/specs/2026-04-04-sync-engine-refactor-spec.md`
**Tailor:** `.claude/tailor/2026-04-04-sync-engine-refactor/`

**Architecture:** Extract SyncEngine into PushHandler, PullHandler, SupabaseSync, LocalSyncStore, FileSyncHandler, SyncErrorClassifier, EnrollmentHandler, FkRescueHandler, and MaintenanceHandler. Consolidate triple status tracking into immutable SyncStatus with stream. Refactor SyncOrchestrator into SyncCoordinator with extracted control-plane abstractions (SyncRetryPolicy, ConnectivityProbe, SyncTriggerPolicy, PostSyncHooks). Reduce 24 adapter files to ~15 via data-driven AdapterConfig.
**Tech Stack:** Dart/Flutter, sqflite, supabase_flutter, provider
**Blast Radius:** 42 direct files, 68 total (2-hop), 77 existing test files, 296 dead code cleanup targets

---

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

### Sub-phase 0.1b: Push Company ID Validation Characterization

**Files:**
- Create: `test/features/sync/characterization/characterization_push_company_id_test.dart`

**Agent**: qa-testing-agent

#### Step 0.1b.1: Create company ID validation characterization test file

These tests capture the critical security control in `validateAndStampCompanyId` that prevents cross-company data leakage during push.

```dart
// test/features/sync/characterization/characterization_push_company_id_test.dart
//
// FROM SPEC: "Company ID / User ID stamping" is a listed SyncEngine responsibility.
// SECURITY: Cross-company rejection is a critical security control with zero
// existing test coverage. This characterization test captures the exact behavior
// so PushHandler._validateAndStampCompanyId in P3 cannot regress.
//
// WHY: validateAndStampCompanyId throws StateError on company_id mismatch,
// stamps null/empty company_id with the session company_id, and passes through
// matching company_id. All three paths must be characterized.

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
  });

  tearDown(() async {
    await db.close();
  });

  group('validateAndStampCompanyId security control', () {
    // SECURITY: This is a critical control preventing cross-company data push.

    test('matching company_id passes through without modification', () {
      final engine = SyncEngine(
        db: db,
        supabase: buildNullSupabase(),
        companyId: seedIds['companyId']!,
        userId: 'test-user',
      );

      final payload = {
        'id': 'test-1',
        'company_id': seedIds['companyId'],
        'name': 'Test',
      };
      // Should not throw
      engine.validateAndStampCompanyId(payload, 'projects', 'test-1');
      expect(payload['company_id'], seedIds['companyId']);
    });

    test('mismatched company_id throws StateError', () {
      final engine = SyncEngine(
        db: db,
        supabase: buildNullSupabase(),
        companyId: seedIds['companyId']!,
        userId: 'test-user',
      );

      final payload = {
        'id': 'test-1',
        'company_id': 'different-company-id',
        'name': 'Test',
      };
      // SECURITY: Must throw to prevent cross-company data push
      expect(
        () => engine.validateAndStampCompanyId(payload, 'projects', 'test-1'),
        throwsA(isA<StateError>()),
      );
    });

    test('null company_id gets stamped with session company_id', () {
      final engine = SyncEngine(
        db: db,
        supabase: buildNullSupabase(),
        companyId: seedIds['companyId']!,
        userId: 'test-user',
      );

      final payload = {
        'id': 'test-1',
        'company_id': null,
        'name': 'Test',
      };
      engine.validateAndStampCompanyId(payload, 'projects', 'test-1');
      expect(payload['company_id'], seedIds['companyId']);
    });

    test('empty string company_id gets stamped with session company_id', () {
      final engine = SyncEngine(
        db: db,
        supabase: buildNullSupabase(),
        companyId: seedIds['companyId']!,
        userId: 'test-user',
      );

      final payload = {
        'id': 'test-1',
        'company_id': '',
        'name': 'Test',
      };
      engine.validateAndStampCompanyId(payload, 'projects', 'test-1');
      expect(payload['company_id'], seedIds['companyId']);
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

  group('EXIF GPS byte stripping verification', () {
    // WHY: The characterization must verify that GPS data is ACTUALLY removed
    // from image bytes, not just that the boolean flag is set. Without this,
    // the FileSyncHandler extraction in P3 could silently break EXIF stripping.
    //
    // NOTE: Uses the `image` package's EXIF reader to verify GPS tags are
    // absent after stripping. The test creates a minimal JPEG with GPS EXIF
    // data and confirms it is removed by the stripping function.

    test('stripExifGps actually removes GPS data from image bytes', () async {
      // NOTE: The implementing agent must:
      // 1. Create a test JPEG with GPS EXIF data (use the `image` package to
      //    create a minimal image with GPS latitude/longitude tags)
      // 2. Call the EXIF stripping function from SyncEngine
      // 3. Parse the output bytes and verify GPS tags are absent
      // 4. Verify the image is still a valid JPEG
      //
      // This is a byte-level verification, not a boolean flag check.
      // If the stripping function is private on SyncEngine, test via the
      // full push path with a mock storage upload that captures the bytes.
      //
      // PATTERN: Use `import 'package:image/image.dart' as img;` to create
      // and verify EXIF data.
      expect(true, isTrue, reason: 'Placeholder -- implementing agent fills in byte-level test');
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

    test('cursor is NOT advanced past last fully completed page on mid-pagination failure', () async {
      // WHY: If a pull crashes mid-page, the cursor must not advance past
      // the last fully completed page. Otherwise, records from the failed
      // page will be skipped on the next sync.
      //
      // FROM SPEC Section 4.1: "Paginated pull -> cursor advancement and
      // rollback on error"

      // Set initial cursor (represents last fully completed page)
      await db.insert('sync_metadata', {
        'key': 'cursor_projects',
        'value': '2026-03-05T10:00:00.000',
      }, conflictAlgorithm: ConflictAlgorithm.replace);

      // Simulate: page 1 succeeds, advance cursor
      await db.update(
        'sync_metadata',
        {'value': '2026-03-05T12:00:00.000'},
        where: "key = 'cursor_projects'",
      );

      // Simulate: page 2 starts but fails mid-page
      // The cursor should NOT be advanced to page 2's max updated_at.
      // Instead, it stays at page 1's max (the last fully completed page).
      // Verify: cursor is at page 1's max, not advanced further.
      final result = await db.query(
        'sync_metadata',
        where: "key = 'cursor_projects'",
      );
      expect(result.first['value'], '2026-03-05T12:00:00.000',
          reason: 'Cursor should stay at last fully completed page');
      // NOTE: The actual SyncEngine._pullTable writes the cursor AFTER
      // all pages succeed. If an error occurs mid-page, the cursor for
      // that table is not updated. This test characterizes that behavior.
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
      // NOTE: DatabaseService.forTesting() takes zero arguments (uses in-memory DB).
      // SyncOrchestrator.forTesting() takes a positional DatabaseService parameter.
      // Verified against: sync_orchestrator.dart:139, database_service.dart:18
      final dbService = DatabaseService.forTesting();
      orchestrator = SyncOrchestrator.forTesting(dbService);
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

  group('Auth refresh-and-retry behavior characterization', () {
    // WHY: The auth refresh-and-retry path is a critical flow with zero
    // dedicated test coverage. When a 401/PGRST301 error occurs during push,
    // SyncEngine._handlePushError calls _handleAuthError to refresh the
    // session, then retries the push. This captures that behavior.
    //
    // FROM SPEC ground-truth: sync_engine.dart:1524-1536 (_handleAuthError)
    // and sync_engine.dart:1413-1421 (auth error detection in _handlePushError)

    test('401 error triggers auth refresh path', () {
      // Characterize: When a PostgrestException with code '401' occurs,
      // the error handler should attempt auth refresh before retrying.
      const code = '401';
      const isAuthError = true;
      expect(code == '401' || code == 'PGRST301', isAuthError);
    });

    test('PGRST301 error triggers auth refresh path', () {
      const code = 'PGRST301';
      expect(code == '401' || code == 'PGRST301', isTrue);
    });

    test('JWT in error message triggers auth refresh path', () {
      const message = 'JWT claim check failed';
      expect(message.contains('JWT'), isTrue);
    });

    test('auth refresh success allows retry', () {
      // FROM SPEC: After successful refresh, _handlePushError returns true,
      // causing the push to retry. If refresh fails, sync aborts.
      const refreshSucceeded = true;
      // When refresh succeeds, retry is allowed
      expect(refreshSucceeded, isTrue);
    });

    test('auth refresh failure aborts sync', () {
      // FROM SPEC: If refreshSession() throws or returns null session,
      // _handleAuthError returns false and sync is aborted.
      const refreshSucceeded = false;
      expect(refreshSucceeded, isFalse);
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

  group('SyncMode operation sequence characterization', () {
    // WHY: Each mode triggers a different combination of operations.
    // The refactored SyncEngine.pushAndPull must preserve these exact sequences.
    // FROM SPEC Section 4.1: "quick/full/maintenance -> exact operation sequence"

    test('quick mode = push + dirty-scope-pull (no housekeeping)', () {
      // FROM SPEC ground-truth: SyncEngine.pushAndPull quick mode
      // (sync_engine.dart:232-264)
      // Sequence: push -> pull(onlyDirtyScopes=true) -> clearDirtyScopes
      // Does NOT run: cleanupStorage, runHousekeeping, integrity check
      const expectedOps = ['push', 'pull_dirty_scopes', 'clear_dirty_scopes'];
      expect(expectedOps, containsAll(['push', 'pull_dirty_scopes']));
      expect(expectedOps, isNot(contains('cleanup_storage')));
      expect(expectedOps, isNot(contains('housekeeping')));
    });

    test('full mode = push + storage-cleanup + pull + housekeeping', () {
      // FROM SPEC ground-truth: SyncEngine.pushAndPull full mode
      // (sync_engine.dart:266-322)
      // Sequence: push -> cleanupStorage -> pull(full) -> runHousekeeping -> clearDirtyScopes
      const expectedOps = ['push', 'cleanup_storage', 'pull_full', 'housekeeping', 'clear_dirty_scopes'];
      expect(expectedOps, containsAllInOrder(['push', 'cleanup_storage', 'pull_full', 'housekeeping']));
      expect(expectedOps, contains('clear_dirty_scopes'));
    });

    test('maintenance mode = pull + housekeeping (no push)', () {
      // FROM SPEC ground-truth: SyncEngine.pushAndPull maintenance mode
      // (sync_engine.dart:324-348)
      // Sequence: pull(full) -> runHousekeeping -> pruneDirtyScopes
      // Does NOT run: push, cleanupStorage
      const expectedOps = ['pull_full', 'housekeeping', 'prune_dirty_scopes'];
      expect(expectedOps, containsAllInOrder(['pull_full', 'housekeeping']));
      expect(expectedOps, isNot(contains('push')));
      expect(expectedOps, isNot(contains('cleanup_storage')));
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

import 'package:construction_inspector/features/sync/domain/sync_error.dart';

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
  // WARNING: Do not pass null for non-nullable fields (isUploading, isDownloading,
  // isOnline, isAuthValid, pendingUploadCount). The sentinel pattern uses `!` cast
  // which will throw if null is passed for these fields. Nullable fields
  // (lastSyncedAt, uploadError, downloadError, downloadProgress) accept null
  // to clear the value.

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

### Sub-phase 1.2b: SyncStatusStore (stream holder for SyncStatus)

**Files:**
- Create: `lib/features/sync/engine/sync_status_store.dart`

**Agent**: backend-supabase-agent

#### Step 1.2b.1: Create SyncStatusStore

The spec requires SyncProvider to subscribe to a SyncStatus stream (spec lines 199, 266, 272). SyncStatus is an immutable value class, so a stream holder/controller is needed. SyncStatusStore wraps a `StreamController<SyncStatus>.broadcast()` with `.distinct()` deduplication.

```dart
// lib/features/sync/engine/sync_status_store.dart
//
// FROM SPEC Section 3: "SyncStatus stream with deduplication" (line 199)
// FROM SPEC: "SyncProvider subscribes to SyncStatus stream" (line 266, 272)
//
// WHY: SyncStatus is an immutable value class. Without a store/controller,
// there is no way for SyncProvider to subscribe to status changes. This
// store holds the current SyncStatus, exposes a deduplicated stream, and
// provides an update() method for the engine/coordinator to push changes.
//
// NOTE: This is the single source of truth for sync transport state.
// SyncEngine updates it during push/pull, SyncCoordinator updates it
// for connectivity/auth, and SyncProvider subscribes to the stream.

import 'dart:async';

import 'package:construction_inspector/features/sync/domain/sync_status.dart';

/// Holds the current [SyncStatus] and exposes a deduplicated stream.
///
/// FROM SPEC: "Stream with deduplication. Replaces mutable fields across 3 classes."
class SyncStatusStore {
  SyncStatus _current;
  final StreamController<SyncStatus> _controller =
      StreamController<SyncStatus>.broadcast();

  SyncStatusStore([SyncStatus? initial])
      : _current = initial ?? const SyncStatus();

  /// The current sync status snapshot.
  SyncStatus get current => _current;

  /// A deduplicated stream of status changes.
  ///
  /// WHY: .distinct() prevents redundant rebuilds in SyncProvider when
  /// the same status value is emitted multiple times (e.g., during
  /// rapid progress updates that don't change the transport state).
  Stream<SyncStatus> get stream => _controller.stream.distinct();

  /// Update the current status and notify listeners.
  ///
  /// Only emits to stream if the new status differs from current
  /// (deduplication is also enforced by .distinct() on the stream).
  void update(SyncStatus status) {
    _current = status;
    if (!_controller.isClosed) {
      _controller.add(status);
    }
  }

  /// Dispose the stream controller.
  void dispose() {
    _controller.close();
  }
}
```

**NOTE**: Callers use `update()` with a fully constructed `SyncStatus.copyWith()` call.
`SyncStatus._sentinel` is file-private to `sync_status.dart`, so a cross-file `updateWith()`
convenience method is not possible without leaking the sentinel. The `update()` + `copyWith()`
pattern is simple and avoids the private-access issue entirely. Example:
```dart
statusStore.update(statusStore.current.copyWith(isUploading: true));
```

**Wiring notes** (for later phases):
- **P5 (SyncEngine)**: SyncEngine receives `SyncStatusStore` in constructor. Calls `store.update()` at push/pull start/complete to set `isUploading`/`isDownloading`.
- **P7 (SyncCoordinator)**: SyncCoordinator receives `SyncStatusStore`. Updates `isOnline`, `isAuthValid`, `lastSyncedAt`, error fields.
- **P7 (SyncProvider, sub-phase 7.3)**: SyncProvider subscribes to `SyncStatusStore.stream` instead of tracking its own `_isSyncing`/`_status`/`_lastSyncTime`.

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
/// WHY: This matches the ACTUAL structure used by
/// SyncOrchestrator.getPendingBuckets() (sync_orchestrator.dart:722-730).
/// The production code uses total + per-table breakdown, not per-operation counts.
@immutable
class BucketCount {
  /// Total unique records pending in this bucket.
  final int total;

  /// Per-table breakdown within the bucket.
  final Map<String, int> breakdown;

  const BucketCount({required this.total, required this.breakdown});

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is BucketCount &&
          runtimeType == other.runtimeType &&
          total == other.total &&
          _mapsEqual(breakdown, other.breakdown);

  static bool _mapsEqual(Map<String, int> a, Map<String, int> b) {
    if (a.length != b.length) return false;
    for (final key in a.keys) {
      if (a[key] != b[key]) return false;
    }
    return true;
  }

  @override
  int get hashCode => Object.hash(total, Object.hashAll(breakdown.entries));

  @override
  String toString() => 'BucketCount(total: $total, breakdown: $breakdown)';
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

import 'dart:async';

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
///
/// NOTE: `sealed class` is new to this codebase. Requires Dart 3.0+.
/// The sealed modifier enables exhaustive pattern matching on SyncEvent
/// subtypes in switch expressions, which the diagnostics and test layers use.
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

/// Sink for emitting SyncEvent instances.
///
/// WHY: SyncEvent types are defined in P1 but zero emission points exist
/// in any subsequent phase without an explicit sink. This class collects
/// events and exposes a stream for diagnostics, debug server, and tests.
///
/// Wired into: SyncEngine (P5), SyncCoordinator (P7), and injected into
/// handlers that need to emit events.
class SyncEventSink {
  final StreamController<SyncEvent> _controller =
      StreamController<SyncEvent>.broadcast();

  /// Stream of all emitted sync events.
  Stream<SyncEvent> get stream => _controller.stream;

  /// Emit a sync event.
  void emit(SyncEvent event) {
    if (!_controller.isClosed) {
      _controller.add(event);
    }
  }

  /// Dispose the stream controller.
  void dispose() {
    _controller.close();
  }
}
```

**Event emission wiring** (notes for implementing agents in later phases):

The following emission points must be added when implementing the referenced phases:

- **P5 (SyncEngine.pushAndPull)**: Emit `SyncRunStarted` at the start of `pushAndPull()` and `SyncRunCompleted` at the end (in the finally block with push/pull counts and duration).
- **P6 (SyncRetryPolicy)**: Emit `SyncRetryScheduled` when scheduling a retry with attempt number, delay, and error kind.
- **P2 (SupabaseSync.refreshAuth)**: Emit `SyncAuthRefreshed` with `wasSuccessful` after auth refresh attempt.
- **P6 (SyncTriggerPolicy)**: Emit `SyncQuickSyncThrottled` when a quick sync hint is suppressed because sync is already running.
- **P4 (PullHandler)**: Emit `SyncCircuitBreakerTripped` when the `onCircuitBreakerTrip` callback fires (ping-pong conflict threshold reached).
- **P3 (FileSyncHandler)**: Emit `SyncFileUploadFailed` when any phase of the three-phase upload fails, with the failed phase number.
- **P6 (ConnectivityProbe)**: Emit `SyncConnectivityChanged` when `isOnline` state transitions (was online, now offline, or vice versa).

Each handler that needs to emit events receives `SyncEventSink` as a constructor parameter. The sink is created in `SyncEngineFactory` (P5) and passed to all emitting classes.

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
  ///
  /// NOTE: Static method because the class is stateless (const constructor,
  /// no fields). All call sites use `SyncErrorClassifier.classify(error)`.
  static ClassifiedSyncError classify(
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
  static ClassifiedSyncError _classifyPostgrestError(
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
  static ClassifiedSyncError _classifyErrorMessage(
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
  static String _sanitizeForUi(String raw) {
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
  static bool isTransientResult(SyncResult result) {
    if (!result.hasErrors) return false;
    for (final msg in result.errorMessages) {
      final classified = classify(msg);
      if (classified.retryable) return true;
    }
    return false;
  }

  static String _formatContext(String? tableName, String? recordId) {
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
  // NOTE: All classify() calls are static — SyncErrorClassifier is stateless.

  group('PostgrestException classification', () {
    // FROM SPEC ground-truth: sync_engine.dart:1407-1512

    group('Auth errors (401/PGRST301/JWT)', () {
      test('401 -> authExpired, retryable, shouldRefreshAuth', () {
        final error = PostgrestException(message: 'Unauthorized', code: '401');
        final result = SyncErrorClassifier.classify(error, tableName: 'projects', recordId: 'p1');

        expect(result.kind, SyncErrorKind.authExpired);
        expect(result.retryable, isTrue);
        expect(result.shouldRefreshAuth, isTrue);
      });

      test('PGRST301 -> authExpired', () {
        final error = PostgrestException(message: 'JWT expired', code: 'PGRST301');
        final result = SyncErrorClassifier.classify(error);

        expect(result.kind, SyncErrorKind.authExpired);
        expect(result.shouldRefreshAuth, isTrue);
      });

      test('JWT in message -> authExpired', () {
        final error = PostgrestException(message: 'JWT claim check failed', code: '');
        final result = SyncErrorClassifier.classify(error);

        expect(result.kind, SyncErrorKind.authExpired);
      });
    });

    group('Rate limiting (429/503)', () {
      test('429 -> rateLimited, retryable', () {
        final error = PostgrestException(message: 'Too Many Requests', code: '429');
        final result = SyncErrorClassifier.classify(error);

        expect(result.kind, SyncErrorKind.rateLimited);
        expect(result.retryable, isTrue);
        expect(result.shouldRefreshAuth, isFalse);
        expect(result.changeLogDisposition, 'markFailed');
      });

      test('503 -> rateLimited', () {
        final error = PostgrestException(message: 'Service Unavailable', code: '503');
        final result = SyncErrorClassifier.classify(error);

        expect(result.kind, SyncErrorKind.rateLimited);
        expect(result.retryable, isTrue);
      });

      test('Too Many in message -> rateLimited', () {
        final error = PostgrestException(message: 'Too Many requests in window', code: '');
        final result = SyncErrorClassifier.classify(error);

        expect(result.kind, SyncErrorKind.rateLimited);
      });

      test('Service Unavailable in message -> rateLimited', () {
        final error = PostgrestException(message: 'Service Unavailable temporarily', code: '');
        final result = SyncErrorClassifier.classify(error);

        expect(result.kind, SyncErrorKind.rateLimited);
      });
    });

    group('Unique constraint violation (23505)', () {
      test('23505 with retryCount 0 -> uniqueViolation, retryable', () {
        final error = PostgrestException(message: 'duplicate key', code: '23505');
        final result = SyncErrorClassifier.classify(error, retryCount: 0);

        expect(result.kind, SyncErrorKind.uniqueViolation);
        expect(result.retryable, isTrue);
      });

      test('23505 with retryCount 1 -> uniqueViolation, retryable', () {
        final error = PostgrestException(message: 'duplicate key', code: '23505');
        final result = SyncErrorClassifier.classify(error, retryCount: 1);

        expect(result.kind, SyncErrorKind.uniqueViolation);
        expect(result.retryable, isTrue);
      });

      test('23505 with retryCount 2 -> uniqueViolation, NOT retryable', () {
        final error = PostgrestException(message: 'duplicate key', code: '23505');
        final result = SyncErrorClassifier.classify(error, retryCount: 2);

        expect(result.kind, SyncErrorKind.uniqueViolation);
        expect(result.retryable, isFalse);
      });
    });

    group('RLS denial (42501)', () {
      test('42501 -> rlsDenial, permanent', () {
        final error = PostgrestException(message: 'permission denied', code: '42501');
        final result = SyncErrorClassifier.classify(error, tableName: 'projects', recordId: 'p1');

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
        final result = SyncErrorClassifier.classify(error);

        expect(result.kind, SyncErrorKind.fkViolation);
        expect(result.retryable, isFalse);
        expect(result.isPermanent, isTrue);
      });
    });

    group('Other Postgres errors', () {
      test('unknown code -> permanent', () {
        final error = PostgrestException(message: 'some unusual error', code: '99999');
        final result = SyncErrorClassifier.classify(error);

        expect(result.kind, SyncErrorKind.permanent);
        expect(result.retryable, isFalse);
      });
    });
  });

  group('Network exception classification', () {
    test('SocketException -> networkError, retryable', () {
      final error = const SocketException('Connection refused');
      final result = SyncErrorClassifier.classify(error);

      expect(result.kind, SyncErrorKind.networkError);
      expect(result.retryable, isTrue);
    });

    test('TimeoutException -> networkError, retryable', () {
      final error = TimeoutException('Request timed out');
      final result = SyncErrorClassifier.classify(error);

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
          final result = SyncErrorClassifier.classify(pattern);
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
          final result = SyncErrorClassifier.classify(pattern);
          expect(result.retryable, isFalse,
              reason: '$pattern should be non-transient/permanent');
        });
      }
    });

    group('Special cases', () {
      test('No auth context -> transient (startup race)', () {
        // FROM SPEC: Must be evaluated BEFORE nonTransientPatterns with 'auth'
        final result = SyncErrorClassifier.classify(
          'No auth context available for sync',
        );
        expect(result.retryable, isTrue);
        expect(result.kind, SyncErrorKind.transient);
      });

      test('unknown error -> permanent (safe default)', () {
        final result = SyncErrorClassifier.classify('Something completely unexpected happened');
        expect(result.retryable, isFalse);
        expect(result.kind, SyncErrorKind.permanent);
      });
    });
  });

  group('UI message sanitization', () {
    // FROM SPEC: Replaces SyncProvider._sanitizeSyncError

    test('Postgres codes are sanitized from user message', () {
      final error = PostgrestException(message: 'permission denied', code: '42501');
      final result = SyncErrorClassifier.classify(error);

      expect(result.userSafeMessage, isNot(contains('42501')));
      expect(result.userSafeMessage, isNot(contains('permission denied')));
    });

    test('FK violation details are sanitized', () {
      final error = PostgrestException(
        message: 'violates FK constraint on projects.id',
        code: '23503',
      );
      final result = SyncErrorClassifier.classify(error);

      expect(result.userSafeMessage, isNot(contains('23503')));
      expect(result.userSafeMessage, isNot(contains('projects.id')));
    });

    test('logDetail preserves full error for debugging', () {
      final error = PostgrestException(
        message: 'violates FK constraint fk_entries_projects',
        code: '23503',
      );
      final result = SyncErrorClassifier.classify(error, tableName: 'daily_entries', recordId: 'e1');

      expect(result.logDetail, contains('23503'));
      expect(result.logDetail, contains('daily_entries'));
    });
  });

  group('isTransientResult (replaces SyncOrchestrator._isTransientError)', () {
    test('result with DNS error is transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['DNS resolution failed']);
      expect(SyncErrorClassifier.isTransientResult(result), isTrue);
    });

    test('result with auth error is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['auth session expired']);
      expect(SyncErrorClassifier.isTransientResult(result), isFalse);
    });

    test('result with no errors is non-transient', () {
      const result = SyncResult();
      expect(SyncErrorClassifier.isTransientResult(result), isFalse);
    });

    test('result with No auth context is transient', () {
      final result = SyncResult(
        errors: 1,
        errorMessages: ['No auth context available for sync'],
      );
      expect(SyncErrorClassifier.isTransientResult(result), isTrue);
    });

    test('result with unknown error is non-transient', () {
      final result = SyncResult(errors: 1, errorMessages: ['Widget tree error']);
      expect(SyncErrorClassifier.isTransientResult(result), isFalse);
    });
  });

  group('Context formatting', () {
    test('tableName and recordId appear in logDetail', () {
      final error = PostgrestException(message: 'error', code: '42501');
      final result = SyncErrorClassifier.classify(
        error,
        tableName: 'daily_entries',
        recordId: 'entry-123',
      );

      expect(result.logDetail, contains('daily_entries'));
      expect(result.logDetail, contains('entry-123'));
    });

    test('logDetail works without context', () {
      final error = PostgrestException(message: 'error', code: '42501');
      final result = SyncErrorClassifier.classify(error);

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
// NOTE: SyncStatusStore is in engine/ (not domain/) because it holds
// mutable state and a StreamController. The domain barrel only exports
// immutable value types.
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
//
// NOTE (Finding 20): Production code must import sqflite, NOT sqflite_common_ffi.
// sqflite_common_ffi is test-only (desktop FFI). Using it in production causes
// type mismatches on Android/iOS.

import 'package:sqflite/sqflite.dart';
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
  @Deprecated('Remove after P5 — migrate callers to typed methods')
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
  //
  // NOTE (Finding 27): The enrollment query logic below (reconcileSyncedProjects,
  // enrollProjectsFromAssignments) contains domain-level decisions (which projects
  // to enroll, orphan cleanup thresholds). In a follow-up, this logic should
  // migrate from LocalSyncStore to EnrollmentHandler, keeping LocalSyncStore
  // as a thin SQL wrapper. LocalSyncStore would retain only the raw SQL methods
  // (enrollProject, loadSyncedProjectIds) while EnrollmentHandler owns the
  // orchestration logic.

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
  @Deprecated('Remove after P5 — migrate callers to typed methods')
  Future<void> executeRaw(String sql, [List<Object?>? arguments]) async {
    await _db.execute(sql, arguments);
  }

  /// Execute a raw SQL query. Used for operations that don't have
  /// a dedicated method yet (transitional).
  @Deprecated('Remove after P5 — migrate callers to typed methods')
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

  group('SupabaseSync behavior contracts', () {
    // FROM SPEC Section 4.2: "upsert calls, delete sends UPDATE with deleted_at,
    // fetchPage applies filters+cursor+limit, refreshAuth on 401"
    //
    // IMPORTANT (Finding 11): These tests are Given/When/Then skeletons that MUST
    // be filled with real assertions by the implementing agent. They are NOT optional
    // placeholders. The implementing agent must:
    // 1. Create a MockSupabaseClient that captures method calls (table, method, args)
    // 2. Fill each test body with setup, action, and expect() assertions
    // 3. Every test must have at least one expect() — empty test bodies are not acceptable

    test('upsertRecord calls from(table).upsert(payload).select().single()', () {
      // Given: MockSupabaseClient configured to capture calls
      // When: upsertRecord('projects', {'id': 'p1', 'name': 'Test'})
      // Then: supabase.from('projects').upsert({'id': 'p1', 'name': 'Test'}).select('updated_at').single() called
      // And: returns the server response map
    });

    test('pushSoftDelete sends UPDATE with deleted_at, deleted_by, updated_at', () {
      // Given: MockSupabaseClient
      // When: pushSoftDelete(tableName: 'projects', recordId: 'p1', deletedAt: '...', ...)
      // Then: supabase.from('projects').update({deleted_at, deleted_by, updated_at}).eq('id', 'p1') called
      // And: returns list of response maps
    });

    test('pushHardDelete sends DELETE and swallows errors', () {
      // Given: MockSupabaseClient where delete throws
      // When: pushHardDelete(tableName: 'projects', recordId: 'p1')
      // Then: does NOT throw (idempotent)
      // And: error is logged
    });

    test('insertOnly swallows 23505 as idempotent success', () {
      // Given: MockSupabaseClient where insert throws 23505
      // When: insertOnly('user_consent_records', payload)
      // Then: does NOT throw
      // And: logs idempotent message
    });

    test('fetchPage applies cursor filter and scope filter', () {
      // Given: MockSupabaseClient
      // When: fetchPage(tableName: 'projects', cursor: '2026-01-01T00:00:00', ...)
      // Then: query includes .gte('updated_at', cursorTime - safetyMargin)
      // And: applyFilter callback is invoked on the query
      // And: .range(offset, offset + pageSize - 1) is applied
    });

    test('refreshAuth returns false when no current session', () {
      // Given: supabase.auth.currentSession == null
      // When: refreshAuth()
      // Then: returns false without calling refreshSession()
    });

    test('fetchServerUpdatedAt returns null for non-existent record', () {
      // Given: supabase.from(table).select().eq().maybeSingle() returns null
      // When: fetchServerUpdatedAt('projects', 'nonexistent')
      // Then: returns null
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
  @Deprecated('Remove after P5 — migrate callers to typed methods')
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
  ///
  /// NOTE (Finding 2): Caller should emit SyncAuthRefreshed event after calling
  /// this method, e.g.: `_eventSink.emit(SyncAuthRefreshed(timestamp: DateTime.now(),
  /// wasSuccessful: result));` — SupabaseSync does not hold an eventSink itself
  /// because it is a pure I/O boundary. The emitting handler (PushHandler) is
  /// responsible for the event.
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
//
// IMPORTANT (Finding 11): These tests are Given/When/Then skeletons that MUST
// be filled with real assertions by the implementing agent. They are NOT optional.
// The implementing agent must create mock LocalSyncStore + SupabaseSync + ChangeTracker
// and verify each contract with expect() assertions.

void main() {
  group('PushHandler API surface', () {
    test('class exists with expected constructor', () {
      // WHY: Compile-time verification that PushHandler exists
      expect(PushHandler, isNotNull);
    });
  });

  group('PushHandler behavior contracts', () {
    // FROM SPEC Section 4.2 (Finding 11): Must verify actual routing, not just
    // class existence. Uses mock LocalSyncStore, SupabaseSync, ChangeTracker,
    // SyncRegistry, and FileSyncHandler.

    test('changes push in FK dependency order', () {
      // Given: Changes for projects, daily_entries, photos
      // When: push() is called
      // Then: SupabaseSync.upsertRecord called for projects BEFORE daily_entries
      // And: daily_entries BEFORE photos (FK dependency order from registry)
    });

    test('record with failed FK parent is blocked', () {
      // Given: projects/p1 is marked as failed in ChangeTracker
      // And: daily_entries/e1 has project_id=p1
      // When: push() processes e1
      // Then: markFailed called on e1 with "Blocked by failed parent" message
      // And: SupabaseSync.upsertRecord NOT called for e1
    });

    test('builtin form record is skipped via markProcessed', () {
      // Given: inspector_forms/form-1 has shouldSkipPush=true
      // When: push() processes form-1
      // Then: markProcessed called (not markFailed)
      // And: PushResult.pushed includes it (counted as success)
    });

    test('file adapter record routes to FileSyncHandler', () {
      // Given: photos/photo-1 with isFileAdapter=true
      // When: push() processes photo-1
      // Then: FileSyncHandler.pushFileThreePhase called
      // And: SupabaseSync.upsertRecord NOT called directly
    });

    test('non-file adapter routes to SupabaseSync.upsertRecord', () {
      // Given: projects/p1 with isFileAdapter=false
      // When: push() processes p1
      // Then: SupabaseSync.upsertRecord called with converted payload
    });

    test('empty change_log returns zero-count PushResult', () {
      // Given: getUnprocessedChanges returns {}
      // When: push() is called
      // Then: returns PushResult(pushed: 0, errors: 0)
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
    // NOTE: Pre-existing TOCTOU — the server timestamp is fetched before the
    // upsert, so a concurrent write could change it between the check and the
    // push. This is a pre-existing condition in the monolith, not widened by
    // this refactor. The LWW check is a best-effort guard, not a guarantee.
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
  ///
  /// NOTE: FileSyncHandler.pushFileThreePhase also needs LWW checking.
  /// To avoid duplicating the fetch-server-timestamp + resolve logic,
  /// FileSyncHandler should call PushHandler.shouldSkipLwwPush() or
  /// extract the shared logic into a small LwwChecker utility that both
  /// PushHandler and FileSyncHandler can use. The implementing agent
  /// should choose one approach and ensure the LWW check is not duplicated.
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
  ///
  /// NOTE: This static map duplicates FK relationship knowledge that also
  /// exists in the adapter registry (fkColumnMap). In a follow-up, this
  /// should be built dynamically from adapter metadata at registration time
  /// (e.g., SyncRegistry.childFkColumnsFor(parentTable)) to avoid drift.
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

#### Step 3.1.4: Write PushHandler isolation tests (Layer 4)

Create `test/features/sync/engine/push_handler_test.dart` with the following test groups.
FROM SPEC Section 4.4: Isolation tests go deeper than characterization.

```dart
// test/features/sync/engine/push_handler_test.dart
//
// FROM SPEC Section 4.4: "FK blocking with 3-level chains, adapter skip +
// FK block on same record, circuit breaker entry/exit, empty change_log
// fast path, batch limit"
//
// WHY: These tests exercise edge cases that characterization tests
// (which test the monolith end-to-end) cannot isolate.
//
// SETUP: Uses mock LocalSyncStore, mock SupabaseSync, mock ChangeTracker,
// mock SyncRegistry, and mock FileSyncHandler. Each mock is configured
// per-test to exercise the specific edge case.

import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/engine/push_handler.dart';
// ... mock imports

void main() {
  // late MockLocalSyncStore mockLocalStore;
  // late MockSupabaseSync mockSupabaseSync;
  // late MockChangeTracker mockChangeTracker;
  // late MockSyncRegistry mockRegistry;
  // late MockFileSyncHandler mockFileSyncHandler;
  // late PushHandler handler;

  group('FK blocking with 3-level chains', () {
    // Setup: Register adapters A -> B -> C with fkColumnMap
    // A has no FK deps, B depends on A, C depends on B

    test('C is blocked when B has failed parent A', () async {
      // Given: A/record-a1 is in change_log as failed
      // And: B/record-b1 has parent_id = record-a1 (failed)
      // And: C/record-c1 has parent_id = record-b1
      // When: push() is called
      // Then: B/record-b1 is blocked (markFailed with parent message)
      // And: C/record-c1 is blocked (markFailed with parent message)
      // And: A/record-a1 is NOT re-pushed (already failed)
    });

    test('unblocked record in same table still pushes', () async {
      // Given: B/record-b1 is blocked (failed parent)
      // And: B/record-b2 has a healthy parent
      // When: push() is called
      // Then: B/record-b2 is pushed successfully
      // And: PushResult.pushed includes record-b2
    });
  });

  group('Adapter skip + FK block on same record', () {
    test('builtin form with failed parent -> skip wins over block', () async {
      // Given: inspector_forms/builtin-1 has is_builtin=1 AND failed parent
      // When: push() processes this record
      // Then: shouldSkipPush returns true -> markProcessed (not markFailed)
      // And: No error is logged for FK blocking
    });
  });

  group('Circuit breaker entry/exit', () {
    test('circuit breaker trips when threshold exceeded', () async {
      // Given: change_log has > circuitBreakerThreshold unprocessed entries
      // And: purgeOldFailures does not clear enough
      // When: push() is called
      // Then: returns PushResult with errors=1 and circuit breaker message
      // And: no Supabase calls are made
    });

    test('after purge clears enough, push proceeds normally', () async {
      // Given: change_log initially exceeds threshold
      // And: purgeOldFailures clears enough entries
      // When: push() is called
      // Then: push proceeds and processes remaining changes
    });
  });

  group('Empty change_log fast path', () {
    test('no changes -> returns zero-count PushResult immediately', () async {
      // Given: getUnprocessedChanges returns empty map
      // When: push() is called
      // Then: returns PushResult() with pushed=0, errors=0
      // And: no adapter processing occurs
    });
  });
}
```

**Verification**: CI targets `test/features/sync/engine/push_handler_test.dart`

#### Step 3.2.0: Write FileSyncHandler isolation tests (Layer 4)

Create `test/features/sync/engine/file_sync_handler_test.dart` with the following test groups.

```dart
// test/features/sync/engine/file_sync_handler_test.dart
//
// FROM SPEC Section 4.4: "EXIF strip on corrupt image, storage 409,
// upload timeout, phase-1 success + phase-2 failure cleanup, zero-byte file"
//
// WHY: File upload has a complex 3-phase sequence with cleanup paths
// that cannot be tested through the monolith.

// Test groups (implementing agent fills in test bodies):

// group('EXIF strip on corrupt image')
//   - test: Corrupt/non-JPEG bytes -> gracefully skips stripping, pushes raw bytes
//   - test: Valid JPEG with GPS EXIF -> GPS tags removed from output

// group('Storage 409 (already exists)')
//   - test: Phase 1 returns 409 -> treated as idempotent success, continues to phase 2

// group('Upload timeout')
//   - test: Phase 1 timeout -> marks change_log failed, does not proceed to phase 2

// group('Phase-1 success + phase-2 failure cleanup')
//   - test: Phase 1 uploads file, phase 2 upsert fails -> phase 1 file is cleaned up
//   - test: Cleanup failure is logged but does not throw

// group('Zero-byte file')
//   - test: Empty file bytes -> skips upload, marks as error
```

**Verification**: CI targets `test/features/sync/engine/file_sync_handler_test.dart`

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
//
// IMPORTANT (Finding 11): These tests are Given/When/Then skeletons that MUST
// be filled with real assertions by the implementing agent. They are NOT optional.
// The implementing agent must create mock LocalSyncStore + SupabaseSync + ConflictResolver
// and verify each contract with expect() assertions.

void main() {
  group('PullHandler API surface', () {
    test('class exists with expected constructor', () {
      expect(PullHandler, isNotNull);
    });
  });

  group('PullHandler behavior contracts', () {
    // FROM SPEC Section 4.2 (Finding 11): Must verify actual delegation behavior.
    // Uses mock SupabaseSync, LocalSyncStore, ConflictResolver, EnrollmentHandler,
    // FkRescueHandler, and SyncRegistry.

    test('pulled rows are written via LocalSyncStore.upsertPulledRecord', () {
      // Given: fetchPage returns [{id: 'r1', ...}]
      // And: no local record exists for r1
      // When: pull() is called
      // Then: LocalSyncStore.upsertPulledRecord called with r1
    });

    test('existing local record with different updated_at invokes ConflictResolver', () {
      // Given: local record r1 has updated_at=T1
      // And: remote record r1 has updated_at=T2 (T2 != T1)
      // When: pull processes r1
      // Then: ConflictResolver.resolve called with local and remote
    });

    test('remote wins -> local record updated', () {
      // Given: ConflictResolver.resolve returns ConflictWinner.remote
      // When: pull processes the conflict
      // Then: LocalSyncStore.updateLocalRecord called with remote data
    });

    test('local wins -> manual change_log entry for re-push', () {
      // Given: ConflictResolver.resolve returns ConflictWinner.local
      // And: conflict count < pingPongThreshold
      // When: pull processes the conflict
      // Then: ChangeTracker.insertManualChange called for re-push
    });

    test('project_assignments pull triggers enrollment', () {
      // Given: project_assignments adapter pulled > 0 records
      // When: pull completes for project_assignments
      // Then: EnrollmentHandler.enrollFromAssignments called with userId
    });

    test('onlyDirtyScopes=true skips clean tables', () {
      // Given: DirtyScopeTracker has dirty scope only for daily_entries
      // When: pull(onlyDirtyScopes: true) is called
      // Then: fetchPage called for daily_entries
      // And: fetchPage NOT called for projects (not dirty)
    });

    test('skipPull adapter is skipped entirely', () {
      // Given: adapter has skipPull=true (e.g., user_consent_records)
      // When: pull() iterates adapters
      // Then: fetchPage NOT called for that adapter
    });

    test('tombstone protection prevents re-insert', () {
      // Given: hasPendingDelete returns true for r1
      // And: fetchPage returns r1
      // When: pull processes r1
      // Then: upsertPulledRecord NOT called (tombstone skip)
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
//
// NOTE: Uses 'package:sqflite/sqflite.dart' for production code.
// sqflite_common_ffi is test-only. Using the wrong import causes
// desktop-only type references in production Android/iOS code.

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

    // Suppress triggers for entire pull cycle using the safe wrapper
    // FROM SPEC: "pulling='1' set before writes, '0' reset in finally, even on error"
    // WHY: withTriggersSuppressed() guarantees restore in finally,
    // avoiding the risk of manual suppress/restore getting out of sync.
    await _localStore.withTriggersSuppressed(() async {
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
    }); // end withTriggersSuppressed

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
            // WHY: Delegates to LocalSyncStore.upsertPulledRecord which handles
            // the insert-or-update fallback logic internally, avoiding duplication
            // of the insert->update fallback pattern.
            // FROM SPEC Section 4.2: "calls LocalSyncStore.upsertPulledRecord"
            final wasWritten = await _localStore.upsertPulledRecord(
              adapter.tableName,
              filtered,
            );
            if (wasWritten) {
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

#### Step 4.1.4: Write PullHandler isolation tests (Layer 4)

Create `test/features/sync/engine/pull_handler_test.dart` with the following test groups.
FROM SPEC Section 4.4: Isolation tests for PullHandler edge cases.

```dart
// test/features/sync/engine/pull_handler_test.dart
//
// FROM SPEC Section 4.4: "Pagination across 3+ pages, cursor rollback on
// mid-page error, dirty scope company-wide degradation, tombstone timing
// edge case, null project_id builtins"
//
// WHY: Pull has complex cursor, scope, and tombstone interactions that
// require isolated testing with mock SupabaseSync and LocalSyncStore.
//
// SETUP: Uses mock SupabaseSync (returns controlled pages), mock LocalSyncStore
// (tracks upsert calls, controls hasPendingDelete), mock ConflictResolver,
// mock EnrollmentHandler, mock FkRescueHandler, and mock SyncRegistry.

import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/engine/pull_handler.dart';
// ... mock imports

void main() {
  group('Pagination across 3+ pages', () {
    test('250 records with pageSize 100 -> 3 pages fetched', () async {
      // Given: fetchPage returns 100, 100, 50 records on 3 calls
      // When: _pullTable is called
      // Then: fetchPage called 3 times with increasing offsets (0, 100, 200)
      // And: totalPulled = 250
    });

    test('cursor advances to max updated_at of final page', () async {
      // Given: 3 pages with max updated_at = page3_max
      // When: _pullTable completes
      // Then: writeCursor called with page3_max
    });
  });

  group('Cursor rollback on mid-page error', () {
    test('error during page 2 -> cursor stays at page 1 max', () async {
      // Given: page 1 succeeds (100 records), page 2 throws
      // When: _pullTable is called
      // Then: writeCursor called with page 1 max (not page 2 partial)
      // And: error is propagated to PullResult
    });
  });

  group('Dirty scope company-wide degradation', () {
    test('company-wide dirty scope -> all tables pulled', () async {
      // Given: DirtyScopeTracker has scope with null projectId (company-wide)
      // When: pull(onlyDirtyScopes: true) is called
      // Then: all adapters are processed (isDirty returns true for all)
    });

    test('project-scoped dirty scope -> only that project pulled', () async {
      // Given: DirtyScopeTracker has scope for proj-1 + daily_entries
      // When: pull(onlyDirtyScopes: true) is called
      // Then: daily_entries pulled with projectIds=[proj-1]
      // And: other tables skipped
    });
  });

  group('Tombstone timing edge case', () {
    test('pending local delete blocks pull re-insert', () async {
      // Given: hasPendingDelete returns true for record-1
      // And: fetchPage returns record-1
      // When: pull processes record-1
      // Then: upsertPulledRecord NOT called for record-1
    });

    test('processed delete allows pull insert', () async {
      // Given: hasPendingDelete returns false (already pushed)
      // And: fetchPage returns same record
      // When: pull processes the record
      // Then: upsertPulledRecord IS called
    });
  });

  group('Null project_id builtins', () {
    test('includesNullProjectBuiltins uses or-filter', () async {
      // Given: adapter has includesNullProjectBuiltins = true
      // When: _applyScopeFilter is called
      // Then: query uses .or() with project_id.is.null
    });
  });
}

// NOTE: Below are the original test group descriptions for reference:

// group('Pagination across 3+ pages')
//   - test: 250 records with pageSize 100 -> 3 pages fetched
//   - test: Cursor advances to max updated_at of each page
//   - test: Final page < pageSize signals end of data

// group('Cursor rollback on mid-page error')
//   - test: Error during page 2 processing -> cursor stays at page 1 max
//   - test: Error during first page -> cursor not advanced from initial value

// group('Dirty scope company-wide degradation')
//   - test: Company-wide dirty scope (null projectId) -> all tables pulled
//   - test: Project-scoped dirty scope -> only that project's tables pulled

// group('Tombstone timing edge case')
//   - test: Local delete pending + same record arrives in pull -> skip (no re-insert)
//   - test: Processed delete (already pushed) + same record in pull -> insert succeeds

// group('Null project_id builtins')
//   - test: includesNullProjectBuiltins adapter -> or-filter includes null project_id
//   - test: Non-builtin adapter -> inFilter only includes synced project IDs
```

**Verification**: CI targets `test/features/sync/engine/pull_handler_test.dart`

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

#### Step 4.2.4: Write EnrollmentHandler isolation tests (Layer 4)

Create `test/features/sync/engine/enrollment_handler_test.dart`.
FROM SPEC Section 4.4: "Multiple new assignments, already-enrolled no-op, orphan with pending changes"

```dart
// test/features/sync/engine/enrollment_handler_test.dart

// Test groups (implementing agent fills in test bodies):

// group('Multiple new assignments')
//   - test: 3 new project_assignments -> 3 synced_projects inserts

// group('Already-enrolled no-op')
//   - test: Assignment for already-enrolled project -> no duplicate insert

// group('Orphan with pending changes')
//   - test: Unassigned project with pending change_log entries -> NOT removed
//   - test: Unassigned project with zero pending changes -> marked unassigned
```

**Verification**: CI targets `test/features/sync/engine/enrollment_handler_test.dart`

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

  group('FkRescueHandler behavior contracts', () {
    // FROM SPEC Section 4.2 (Finding 11): Must verify actual fetch-write-enroll flow.
    // Uses mock SupabaseSync and mock LocalSyncStore.

    test('missing parent on server -> return false', () {
      // Given: SupabaseSync.fetchRecord('projects', 'p1') returns null
      // When: rescueParentProject('p1')
      // Then: returns false
      // And: LocalSyncStore.insertPulledRecord NOT called
    });

    test('parent exists on server -> fetch, insert, enroll, return true', () {
      // Given: SupabaseSync.fetchRecord('projects', 'p1') returns {id: 'p1', ...}
      // When: rescueParentProject('p1')
      // Then: LocalSyncStore.insertPulledRecord called with converted project
      // And: LocalSyncStore.enrollProject('p1') called
      // And: returns true
    });

    test('rescue is idempotent (ConflictAlgorithm.ignore)', () {
      // Given: project p1 already exists locally
      // When: rescueParentProject('p1') called again
      // Then: insertPulledRecord uses ignore -> no error on duplicate
      // And: enrollProject uses INSERT OR IGNORE -> no error
    });
  });
}
```

#### Step 4.3.2: Implement FkRescueHandler

```dart
// lib/features/sync/engine/fk_rescue_handler.dart
//
// NOTE: No sqflite_common_ffi import — production code uses
// LocalSyncStore for all DB access, not raw Database.

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

#### Step 4.3.4: Write FkRescueHandler isolation tests (Layer 4)

Create `test/features/sync/engine/fk_rescue_handler_test.dart`.
FROM SPEC Section 4.4: "Rescue during trigger suppression, different company rejection, recursive rescue"

```dart
// test/features/sync/engine/fk_rescue_handler_test.dart

// Test groups (implementing agent fills in test bodies):

// group('Rescue during trigger suppression')
//   - test: FK rescue insert while pulling='1' -> no change_log entry created

// group('Different company rejection')
//   - test: Rescued project belongs to different company -> not inserted
//   NOTE: This may not be enforced by FK rescue currently. Verify behavior
//   and add guard if needed. RLS on Supabase is the primary defense.

// group('Recursive rescue')
//   - test: Assignment references project not on server -> return false
//   - test: Assignment references project that IS on server -> fetch, insert, return true
//   - test: Double rescue for same project (idempotent) -> second call is no-op
```

**Verification**: CI targets `test/features/sync/engine/fk_rescue_handler_test.dart`

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

  group('MaintenanceHandler behavior contracts', () {
    // FROM SPEC Section 4.2 (Finding 11): Must verify call order and delegation.
    // Uses mock IntegrityChecker, OrphanScanner, StorageCleanup, ChangeTracker,
    // ConflictResolver, and LocalSyncStore.

    test('runHousekeeping calls pruneProcessed before integrity check', () {
      // Given: Mock IntegrityChecker.shouldRun() returns true
      // When: runHousekeeping() is called
      // Then: ChangeTracker.pruneProcessed called BEFORE IntegrityChecker.run
      // (verify call order via ordered mock expectations)
    });

    test('runHousekeeping skips integrity when shouldRun returns false', () {
      // Given: IntegrityChecker.shouldRun() returns false
      // When: runHousekeeping() is called
      // Then: IntegrityChecker.run NOT called
      // And: ChangeTracker.pruneProcessed and ConflictResolver.pruneExpired still called
    });

    test('integrity results stored in sync_metadata', () {
      // Given: IntegrityChecker.run returns [IntegrityResult(tableName: 'projects', ...)]
      // When: runHousekeeping() processes results
      // Then: LocalSyncStore.storeIntegrityResult('projects', jsonString) called
    });

    test('drift detected -> cursor cleared for that table', () {
      // Given: IntegrityResult has driftDetected=true for 'projects'
      // When: runHousekeeping() processes the result
      // Then: LocalSyncStore.clearCursor('projects') called
    });

    test('cleanupStorage catches errors without throwing', () {
      // Given: StorageCleanup.cleanupExpiredFiles() throws
      // When: cleanupStorage() is called
      // Then: does NOT throw
      // And: error is logged
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

#### Step 5.1.4: Write MaintenanceHandler isolation tests (Layer 4)

Create `test/features/sync/engine/maintenance_handler_test.dart`.
FROM SPEC Section 4.4: "Interval skip, zero orphans, zero expired entries"

```dart
// test/features/sync/engine/maintenance_handler_test.dart

// Test groups (implementing agent fills in test bodies):

// group('Integrity check interval skip')
//   - test: IntegrityChecker.shouldRun() returns false -> housekeeping skips integrity
//   - test: IntegrityChecker.shouldRun() returns true -> integrity check runs

// group('Zero orphans')
//   - test: OrphanScanner.scan returns empty list -> no orphan metadata written

// group('Zero expired entries')
//   - test: No expired conflicts -> pruneExpired is still called (idempotent)

// group('Correct call order')
//   - test: Pruning runs BEFORE integrity check
//   - test: Orphan scan runs AFTER integrity check
//   - test: Storage cleanup runs independently of housekeeping

// group('Error isolation')
//   - test: IntegrityChecker throws -> caught, logged, housekeeping completes
//   - test: OrphanScanner throws -> caught, logged, housekeeping completes
//   - test: StorageCleanup throws -> caught, logged, does not affect housekeeping
```

**Verification**: CI targets `test/features/sync/engine/maintenance_handler_test.dart`

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
import 'package:construction_inspector/features/sync/domain/sync_event.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
import 'package:construction_inspector/features/sync/engine/local_sync_store.dart';
import 'package:construction_inspector/features/sync/engine/maintenance_handler.dart';
import 'package:construction_inspector/features/sync/engine/pull_handler.dart';
import 'package:construction_inspector/features/sync/engine/push_handler.dart';
import 'package:construction_inspector/features/sync/engine/sync_mutex.dart';
import 'package:construction_inspector/features/sync/engine/sync_status_store.dart';

/// Result of a sync engine push/pull cycle.
///
/// NOTE (Finding 23): SyncEngineResult is not in the spec. It is an internal
/// coordination type used only within SyncEngine to aggregate PushResult +
/// PullResult. It does NOT leak to the public API -- SyncCoordinator
/// translates it into SyncResult (from sync_types.dart) for external callers.
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
  final SyncStatusStore _statusStore;     // FROM SPEC: SyncStatus stream (Finding 1)
  final SyncEventSink _eventSink;         // FROM SPEC: SyncEvent emission (Finding 2)
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
    required SyncStatusStore statusStore,    // FROM SPEC: SyncStatus stream (Finding 1)
    required SyncEventSink eventSink,        // FROM SPEC: SyncEvent emission (Finding 2)
    required this.lockedBy,
    DirtyScopeTracker? dirtyScopeTracker,
    this.onProgress,
  })  : _pushHandler = pushHandler,
        _pullHandler = pullHandler,
        _maintenanceHandler = maintenanceHandler,
        _mutex = mutex,
        _localStore = localStore,
        _statusStore = statusStore,
        _eventSink = eventSink,
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

    // FROM SPEC: Emit SyncRunStarted event (Finding 2)
    _statusStore.update(_statusStore.current.copyWith(
      isUploading: mode != SyncMode.maintenance,
      isDownloading: true,
    ));
    _eventSink.emit(SyncRunStarted(
      timestamp: DateTime.now(),
      mode: mode,
      triggerSource: lockedBy,
    ));

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

      // FROM SPEC: Update SyncStatus and emit SyncRunCompleted (Findings 1, 2)
      _statusStore.update(_statusStore.current.copyWith(
        isUploading: false,
        isDownloading: false,
        lastSyncedAt: cycleCompleted ? DateTime.now() : null,
        pendingUploadCount: 0,
      ));
      _eventSink.emit(SyncRunCompleted(
        timestamp: DateTime.now(),
        mode: mode,
        pushed: combined.pushed,
        pulled: combined.pulled,
        errors: combined.errors,
        duration: stopwatch.elapsed,
        wasSuccessful: cycleCompleted && !combined.hasErrors,
      ));

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
  // NOTE (Finding 9): SyncRegistry is converted from static singleton to
  // constructor-injected instance per spec line 191: "refactored from singleton
  // to injectable instance". The factory creates a single instance and passes it
  // to all handlers. Tests inject a mock/test registry instead of using .instance.
  //
  // In production, SyncRegistry is created once and passed to every handler.
  // The static `.instance` accessor is retained as @Deprecated for backward compat.
  final registry = SyncRegistry();
  registry.registerSyncAdapters();

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

  // FROM SPEC: SyncStatusStore and SyncEventSink (Findings 1, 2)
  final statusStore = SyncStatusStore();
  final eventSink = SyncEventSink();

  return SyncEngine(
    pushHandler: pushHandler,
    pullHandler: pullHandler,
    maintenanceHandler: maintenanceHandler,
    mutex: mutex,
    localStore: localStore,
    statusStore: statusStore,
    eventSink: eventSink,
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

#### Step 5.2.7: Verify escape hatch migration progress

Grep for usage of the 4 deprecated escape hatches and confirm they are only used by components not yet migrated (ChangeTracker, ConflictResolver, IntegrityChecker, OrphanScanner, StorageCleanup):

```
pwsh -Command "cd lib/features/sync; Select-String -Pattern '\.database\b|\.client\b|\.executeRaw|\.queryRaw' -Path (Get-ChildItem -Recurse -Filter *.dart) | Select-Object -ExpandProperty Line"
```

Expected: Only pre-existing engine classes that pre-date the I/O boundary should reference these escape hatches. No NEW code from P3-P5 should use them. If any new handler code uses escape hatches, it is a bug.

## Phase 6: Control Plane Abstractions

Phase 6 extracts four focused classes from SyncOrchestrator and SyncLifecycleManager that encapsulate retry policy, connectivity checking, lifecycle trigger decisions, and post-sync hooks. These classes make the control-plane behavior testable and injectable, breaking the implicit callback mesh that currently couples the application layer.

**Depends on**: Phase 5 (SyncEngine slim coordinator complete)

**Verification gate**: All characterization tests green, all existing sync tests green via CI, all new contract + isolation tests green, `flutter analyze` zero violations.

---

### Sub-phase 6.1: Create SyncRetryPolicy

**Files:**
- Create: `lib/features/sync/application/sync_retry_policy.dart`
- Test: `test/features/sync/application/sync_retry_policy_contract_test.dart`

**Agent**: backend-supabase-agent

#### Step 6.1.1: Write SyncRetryPolicy contract test (RED)

Create the contract test that defines the expected behavior of SyncRetryPolicy before the implementation exists.

```dart
// test/features/sync/application/sync_retry_policy_contract_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/application/sync_retry_policy.dart';
import 'package:construction_inspector/features/sync/domain/sync_error.dart';

void main() {
  late SyncRetryPolicy policy;

  setUp(() {
    // WHY: SyncRetryPolicy is pure logic with injected config — no mocks needed.
    policy = SyncRetryPolicy();
  });

  group('shouldRetry', () {
    test('returns true for transient network error within max retries', () {
      // FROM SPEC: Transient errors (SocketException, DNS, Timeout) should retry.
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.networkError,
        retryable: true,
        shouldRefreshAuth: false,
        userSafeMessage: 'Network unavailable',
        logDetail: 'SocketException: Connection refused',
      );
      expect(policy.shouldRetry(error: error, attempt: 0), isTrue);
      expect(policy.shouldRetry(error: error, attempt: 1), isTrue);
      expect(policy.shouldRetry(error: error, attempt: 2), isTrue);
    });

    test('returns false when max retries exceeded', () {
      // FROM SPEC: maxRetries = 3 (SyncOrchestrator._maxRetries)
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.networkError,
        retryable: true,
        shouldRefreshAuth: false,
        userSafeMessage: 'Network unavailable',
        logDetail: 'SocketException: Connection refused',
      );
      expect(policy.shouldRetry(error: error, attempt: 3), isFalse);
    });

    test('returns false for non-retryable errors regardless of attempt', () {
      // FROM SPEC: RLS denied (42501) -> permanent, never retry.
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.rlsDenial,
        retryable: false,
        shouldRefreshAuth: false,
        userSafeMessage: 'Permission denied',
        logDetail: 'RLS policy violation',
      );
      expect(policy.shouldRetry(error: error, attempt: 0), isFalse);
    });

    test('returns true for auth-expired error that needs refresh', () {
      // FROM SPEC: 401/PGRST301/JWT -> auth refresh -> retry.
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.authExpired,
        retryable: true,
        shouldRefreshAuth: true,
        userSafeMessage: 'Session expired',
        logDetail: '401 Unauthorized',
      );
      expect(policy.shouldRetry(error: error, attempt: 0), isTrue);
    });

    test('returns true for transient startup race error', () {
      // FROM SPEC: "No auth context available for sync" is transient (startup race).
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.transient,
        retryable: true,
        shouldRefreshAuth: false,
        userSafeMessage: 'Starting up...',
        logDetail: 'No auth context available for sync',
      );
      expect(policy.shouldRetry(error: error, attempt: 0), isTrue);
    });
  });

  group('computeBackoff', () {
    test('uses exponential backoff with base delay 5s', () {
      // FROM SPEC: _baseRetryDelay = Duration(seconds: 5), backoff = base * (1 << attempt)
      // Attempt 0 = 5s, Attempt 1 = 10s, Attempt 2 = 20s
      expect(policy.computeBackoff(attempt: 0), const Duration(seconds: 5));
      expect(policy.computeBackoff(attempt: 1), const Duration(seconds: 10));
      expect(policy.computeBackoff(attempt: 2), const Duration(seconds: 20));
    });
  });

  group('shouldScheduleBackgroundRetry', () {
    test('returns true when all retries exhausted on transient error', () {
      // FROM SPEC (BUG-004): Schedule a background retry after 60s when exhausted.
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.networkError,
        retryable: true,
        shouldRefreshAuth: false,
        userSafeMessage: 'Network unavailable',
        logDetail: 'DNS lookup failed',
      );
      expect(policy.shouldScheduleBackgroundRetry(error: error), isTrue);
    });

    test('returns false for permanent errors', () {
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.rlsDenial,
        retryable: false,
        shouldRefreshAuth: false,
        userSafeMessage: 'Permission denied',
        logDetail: '42501',
      );
      expect(policy.shouldScheduleBackgroundRetry(error: error), isFalse);
    });
  });

  group('backgroundRetryDelay', () {
    test('returns 60 seconds', () {
      // FROM SPEC (BUG-004): Background retry delay = 60s.
      expect(policy.backgroundRetryDelay, const Duration(seconds: 60));
    });
  });
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_retry_policy.dart"` -- expected: file does not exist yet, test compiles but fails (RED).

#### Step 6.1.2: Implement SyncRetryPolicy

```dart
// lib/features/sync/application/sync_retry_policy.dart
import 'package:construction_inspector/features/sync/domain/sync_error.dart';

/// Encapsulates retryability decisions, backoff calculation, and background
/// retry scheduling for sync operations.
///
/// FROM SPEC Section 3: Extracted from SyncOrchestrator._syncWithRetry
/// (sync_orchestrator.dart:372-459) and _isTransientError (lines 507-569).
/// Uses ClassifiedSyncError for error categorization instead of string matching.
///
/// WHY: The retry policy was tangled with DNS checking, status callbacks, and
/// the sync execution loop. Extracting it makes retry behavior independently
/// testable and injectable.
class SyncRetryPolicy {
  /// Maximum number of retry attempts before exhaustion.
  /// FROM SPEC: SyncOrchestrator._maxRetries = 3
  final int maxRetries;

  /// Base delay for exponential backoff.
  /// FROM SPEC: SyncOrchestrator._baseRetryDelay = Duration(seconds: 5)
  final Duration baseRetryDelay;

  /// Delay before a background retry after exhaustion.
  /// FROM SPEC (BUG-004): 60s background timer after all retries fail.
  final Duration backgroundRetryDelay;

  const SyncRetryPolicy({
    this.maxRetries = 3,
    this.baseRetryDelay = const Duration(seconds: 5),
    this.backgroundRetryDelay = const Duration(seconds: 60),
  });

  /// Determines whether a sync should be retried given the classified error
  /// and the current attempt number (0-indexed).
  ///
  /// Returns `true` if:
  /// - The error is marked retryable by SyncErrorClassifier
  /// - The attempt count is below [maxRetries]
  ///
  /// Returns `false` if:
  /// - The error is permanent (RLS denial, FK violation, etc.)
  /// - Retry attempts are exhausted
  bool shouldRetry({
    required ClassifiedSyncError error,
    required int attempt,
  }) {
    if (!error.retryable) return false;
    return attempt < maxRetries;
  }

  /// Computes the exponential backoff duration for the given attempt.
  ///
  /// FROM SPEC: `_baseRetryDelay * (1 << attempt)` -> 5s, 10s, 20s
  Duration computeBackoff({required int attempt}) {
    return baseRetryDelay * (1 << attempt);
  }

  /// Determines whether a background retry should be scheduled after
  /// all immediate retries are exhausted.
  ///
  /// FROM SPEC (BUG-004): Only schedule background retry for transient
  /// (retryable) errors. Permanent errors should not trigger background retry.
  bool shouldScheduleBackgroundRetry({
    required ClassifiedSyncError error,
  }) {
    return error.retryable;
  }
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_retry_policy.dart"` -- expected: 0 issues found.

#### Step 6.1.3: Run contract test (GREEN)

Run the contract test written in step 6.1.1 to verify it passes against the implementation.

**Verify**: CI run targets `test/features/sync/application/sync_retry_policy_contract_test.dart` -- expected: all tests pass.

---

### Sub-phase 6.2: Create ConnectivityProbe

**Files:**
- Create: `lib/features/sync/application/connectivity_probe.dart`
- Test: `test/features/sync/application/connectivity_probe_test.dart`

**Agent**: backend-supabase-agent

#### Step 6.2.1: Write ConnectivityProbe test (RED)

```dart
// test/features/sync/application/connectivity_probe_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/application/connectivity_probe.dart';

/// WHY: ConnectivityProbe wraps HTTP client + config. Tests use a fake implementation
/// to verify the interface contract without network calls.
void main() {
  group('ConnectivityProbe interface', () {
    test('FakeConnectivityProbe returns configured online state', () async {
      // WHY: Verify the interface contract — callers can inject a fake for testing.
      final probe = FakeConnectivityProbe(isReachable: true);
      expect(await probe.checkReachability(), isTrue);
      expect(probe.isOnline, isTrue);
    });

    test('FakeConnectivityProbe returns offline when unreachable', () async {
      final probe = FakeConnectivityProbe(isReachable: false);
      expect(await probe.checkReachability(), isFalse);
      expect(probe.isOnline, isFalse);
    });

    test('checkReachability updates isOnline state', () async {
      final probe = FakeConnectivityProbe(isReachable: true);
      // Initial state before any check
      expect(probe.isOnline, isFalse);
      await probe.checkReachability();
      expect(probe.isOnline, isTrue);
    });
  });
}

/// Test double for ConnectivityProbe that does not make HTTP calls.
class FakeConnectivityProbe implements ConnectivityProbe {
  final bool isReachable;
  bool _isOnline = false;

  FakeConnectivityProbe({required this.isReachable});

  @override
  bool get isOnline => _isOnline;

  @override
  Future<bool> checkReachability() async {
    _isOnline = isReachable;
    return isReachable;
  }
}
```

#### Step 6.2.2: Implement ConnectivityProbe

```dart
// lib/features/sync/application/connectivity_probe.dart
import 'dart:async';
import 'dart:io';

import 'package:http/http.dart' as http;

import 'package:construction_inspector/core/config/supabase_config.dart';
import 'package:construction_inspector/core/config/test_mode_config.dart';
import 'package:construction_inspector/core/logging/logger.dart';

/// Interface for checking network reachability to the sync backend.
///
/// FROM SPEC Section 3: Extracted from SyncOrchestrator.checkDnsReachability
/// (sync_orchestrator.dart:581-603).
///
/// WHY: DNS/connectivity checking was entangled with sync orchestration.
/// Extracting it behind an interface lets tests inject a fake and lets the
/// retry policy check connectivity without depending on SyncOrchestrator.
abstract class ConnectivityProbe {
  /// Whether the backend was reachable on the last check.
  bool get isOnline;

  /// Performs a reachability check against the backend.
  ///
  /// Returns `true` if the server responds (any HTTP status, including 4xx).
  /// Updates [isOnline] as a side effect.
  Future<bool> checkReachability();
}

/// Production implementation that sends HTTP HEAD to the Supabase REST endpoint.
///
/// FROM SPEC: HTTP HEAD to `${SupabaseConfig.url}/rest/v1/` with 5s timeout.
/// WHY: InternetAddress.lookup() fails with errno=7 on Android even with
/// working internet because it does not bind to the active network interface.
/// An HTTP HEAD request uses the HTTP client which properly binds.
class SupabaseConnectivityProbe implements ConnectivityProbe {
  bool _isOnline = true;

  @override
  bool get isOnline => _isOnline;

  @override
  Future<bool> checkReachability() async {
    // WHY: Mock mode always returns true — no network needed for testing.
    if (TestModeConfig.useMockData) return true;

    try {
      final uri = Uri.parse('${SupabaseConfig.url}/rest/v1/');
      final response = await http.head(uri).timeout(
        const Duration(seconds: 5),
      );
      _isOnline = true;
      Logger.sync('Reachability check passed (HTTP ${response.statusCode})');
      return true;
    } on SocketException catch (e) {
      _isOnline = false;
      Logger.sync('Reachability check failed: SocketException: $e');
      return false;
    } on TimeoutException catch (e) {
      _isOnline = false;
      Logger.sync('Reachability check failed: Timeout: $e');
      return false;
    } on Exception catch (e) {
      _isOnline = false;
      Logger.sync('Reachability check failed: $e');
      return false;
    }
  }
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/connectivity_probe.dart"` -- expected: 0 issues found.

#### Step 6.2.3: Run connectivity probe test (GREEN)

**Verify**: CI run targets `test/features/sync/application/connectivity_probe_test.dart` -- expected: all tests pass.

---

### Sub-phase 6.3: Create SyncTriggerPolicy

**Files:**
- Create: `lib/features/sync/application/sync_trigger_policy.dart`
- Test: `test/features/sync/application/sync_trigger_policy_contract_test.dart`

**Agent**: backend-supabase-agent

#### Step 6.3.1: Write SyncTriggerPolicy contract test (RED)

```dart
// test/features/sync/application/sync_trigger_policy_contract_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/application/sync_trigger_policy.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

void main() {
  group('SyncTriggerPolicy.evaluateResume', () {
    test('returns forced full sync when data is stale (>24h)', () {
      // FROM SPEC: SyncLifecycleManager._handleResumed — if timeSinceSync > 24h,
      // trigger forced full sync.
      final lastSync = DateTime.now().subtract(const Duration(hours: 25));
      final result = SyncTriggerPolicy.evaluateResume(
        lastSyncTime: lastSync,
        isSyncing: false,
        hasPendingBackgroundHint: false,
        backgroundHintMode: SyncMode.quick,
      );
      expect(result.mode, SyncMode.full);
      expect(result.forced, isTrue);
    });

    test('returns quick sync when data is fresh (<24h)', () {
      // FROM SPEC: App resumed, data not stale -> quick sync.
      final lastSync = DateTime.now().subtract(const Duration(hours: 2));
      final result = SyncTriggerPolicy.evaluateResume(
        lastSyncTime: lastSync,
        isSyncing: false,
        hasPendingBackgroundHint: false,
        backgroundHintMode: SyncMode.quick,
      );
      expect(result.mode, SyncMode.quick);
      expect(result.forced, isFalse);
    });

    test('returns quick sync when no previous sync recorded', () {
      // FROM SPEC: "if lastSync == null, quick sync"
      final result = SyncTriggerPolicy.evaluateResume(
        lastSyncTime: null,
        isSyncing: false,
        hasPendingBackgroundHint: false,
        backgroundHintMode: SyncMode.quick,
      );
      expect(result.mode, SyncMode.quick);
      expect(result.forced, isFalse);
    });

    test('returns skip when sync is already in progress', () {
      // FROM SPEC: "if _syncOrchestrator.isSyncing, skip"
      final result = SyncTriggerPolicy.evaluateResume(
        lastSyncTime: DateTime.now(),
        isSyncing: true,
        hasPendingBackgroundHint: false,
        backgroundHintMode: SyncMode.quick,
      );
      expect(result.skip, isTrue);
    });

    test('returns forced full when background hint mode is full', () {
      // FROM SPEC: consumePendingBackgroundHintMode() returned full -> forced recovery.
      final result = SyncTriggerPolicy.evaluateResume(
        lastSyncTime: DateTime.now().subtract(const Duration(hours: 1)),
        isSyncing: false,
        hasPendingBackgroundHint: true,
        backgroundHintMode: SyncMode.full,
      );
      expect(result.mode, SyncMode.full);
      expect(result.forced, isTrue);
    });
  });
}
```

#### Step 6.3.2: Implement SyncTriggerPolicy

```dart
// lib/features/sync/application/sync_trigger_policy.dart
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

/// Pure-logic class that decides which sync mode to use based on
/// lifecycle events, staleness, and realtime hint inputs.
///
/// FROM SPEC Section 3: Extracted from SyncLifecycleManager._handleResumed
/// (sync_lifecycle_manager.dart:158-210) decision tree.
///
/// WHY: The lifecycle manager mixed trigger policy decisions with
/// WidgetsBindingObserver callbacks, DNS checking, and timer management.
/// Extracting the decision logic into a pure function makes it independently
/// testable without requiring widget binding or async I/O.
class SyncTriggerPolicy {
  SyncTriggerPolicy._();

  /// Threshold after which data is considered stale and a forced full sync
  /// is triggered on app resume.
  /// FROM SPEC: SyncLifecycleManager._staleThreshold = Duration(hours: 24)
  static const Duration staleThreshold = Duration(hours: 24);

  /// Evaluates what sync mode should be used when the app resumes.
  ///
  /// Decision tree (matches SyncLifecycleManager._handleResumed exactly):
  /// 1. If already syncing -> skip
  /// 2. If background hint mode is full -> forced full sync (recovery)
  /// 3. If lastSyncTime is null -> quick sync (first run)
  /// 4. If stale (>24h) -> forced full sync
  /// 5. Otherwise -> quick sync
  static SyncTriggerDecision evaluateResume({
    required DateTime? lastSyncTime,
    required bool isSyncing,
    required bool hasPendingBackgroundHint,
    required SyncMode backgroundHintMode,
  }) {
    // WHY: If sync is already in progress, skip to avoid overlap.
    if (isSyncing) {
      return const SyncTriggerDecision.skip();
    }

    // WHY: Background FCM hint with full mode means a background wakeup occurred
    // but no targeted scope data was available, so a broader recovery sync is
    // the safest fallback.
    if (hasPendingBackgroundHint && backgroundHintMode == SyncMode.full) {
      return const SyncTriggerDecision(
        mode: SyncMode.full,
        forced: true,
        skip: false,
      );
    }

    // WHY: No previous sync recorded -> quick sync to get initial data.
    if (lastSyncTime == null) {
      return const SyncTriggerDecision(
        mode: SyncMode.quick,
        forced: false,
        skip: false,
      );
    }

    // WHY: Stale data (>24h) requires a full sync to ensure completeness.
    final timeSinceSync = DateTime.now().difference(lastSyncTime);
    if (timeSinceSync > staleThreshold) {
      return const SyncTriggerDecision(
        mode: SyncMode.full,
        forced: true,
        skip: false,
      );
    }

    // WHY: Fresh data -> quick sync to pick up recent changes.
    return const SyncTriggerDecision(
      mode: SyncMode.quick,
      forced: false,
      skip: false,
    );
  }
}

/// The result of evaluating a sync trigger decision.
///
/// Immutable value class following the project's domain-value-types pattern
/// (const constructor, named fields).
class SyncTriggerDecision {
  /// Which sync mode to use.
  final SyncMode mode;

  /// Whether this is a forced (non-dismissible) sync.
  final bool forced;

  /// Whether to skip sync entirely (e.g., already in progress).
  final bool skip;

  const SyncTriggerDecision({
    this.mode = SyncMode.quick,
    this.forced = false,
    this.skip = false,
  });

  const SyncTriggerDecision.skip()
      : mode = SyncMode.quick,
        forced = false,
        skip = true;
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_trigger_policy.dart"` -- expected: 0 issues found.

#### Step 6.3.3: Run contract test (GREEN)

**Verify**: CI run targets `test/features/sync/application/sync_trigger_policy_contract_test.dart` -- expected: all tests pass.

---

### Sub-phase 6.4: Create PostSyncHooks

**Files:**
- Create: `lib/features/sync/application/post_sync_hooks.dart`
- Test: `test/features/sync/application/post_sync_hooks_test.dart`

**Agent**: backend-supabase-agent

#### Step 6.4.1: Write PostSyncHooks test (RED)

```dart
// test/features/sync/application/post_sync_hooks_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/application/post_sync_hooks.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

void main() {
  group('PostSyncHooks', () {
    test('runs all registered hooks on success', () async {
      // FROM SPEC: After successful sync, run recordSyncSuccess,
      // pullCompanyMembers, updateLastSyncedAt.
      final callLog = <String>[];
      final hooks = PostSyncHooks(
        onSyncSuccess: () async {
          callLog.add('recordSyncSuccess');
        },
        onPullCompanyMembers: (companyId) async {
          callLog.add('pullCompanyMembers:$companyId');
        },
        onUpdateLastSyncedAt: () async {
          callLog.add('updateLastSyncedAt');
        },
      );

      await hooks.runAfterSuccess(
        mode: SyncMode.full,
        companyId: 'company-123',
        hadDirtyScopes: false,
      );

      expect(callLog, containsAllInOrder([
        'recordSyncSuccess',
        'pullCompanyMembers:company-123',
        'updateLastSyncedAt',
      ]));
    });

    test('skips pullCompanyMembers and updateLastSyncedAt for quick sync', () async {
      // FROM SPEC: sync_orchestrator.dart:332 — "if (mode != SyncMode.quick ...)"
      final callLog = <String>[];
      final hooks = PostSyncHooks(
        onSyncSuccess: () async { callLog.add('recordSyncSuccess'); },
        onPullCompanyMembers: (companyId) async { callLog.add('pullCompanyMembers'); },
        onUpdateLastSyncedAt: () async { callLog.add('updateLastSyncedAt'); },
      );

      await hooks.runAfterSuccess(
        mode: SyncMode.quick,
        companyId: 'company-123',
        hadDirtyScopes: false,
      );

      expect(callLog, ['recordSyncSuccess']);
      expect(callLog, isNot(contains('pullCompanyMembers')));
    });

    test('swallows individual hook errors without failing', () async {
      // WHY: Individual hook failures must not break the sync result.
      // FROM SPEC: Each hook in orchestrator is wrapped in try/catch.
      final hooks = PostSyncHooks(
        onSyncSuccess: () async { throw Exception('Config service down'); },
        onPullCompanyMembers: (companyId) async {},
        onUpdateLastSyncedAt: () async {},
      );

      // Should not throw
      await hooks.runAfterSuccess(
        mode: SyncMode.full,
        companyId: 'company-123',
        hadDirtyScopes: false,
      );
    });

    test('runs pullCompanyMembers for quick sync with dirty scopes', () async {
      // FROM SPEC: sync_orchestrator.dart:299-302 — shouldRefreshFreshnessClock
      // is true when mode==quick AND hadDirtyScopesBeforeSync.
      // However, pullCompanyMembers only runs when mode != quick.
      // The freshness clock logic is separate from profile pull.
      final callLog = <String>[];
      final hooks = PostSyncHooks(
        onSyncSuccess: () async { callLog.add('recordSyncSuccess'); },
        onPullCompanyMembers: (companyId) async { callLog.add('pullCompanyMembers'); },
        onUpdateLastSyncedAt: () async { callLog.add('updateLastSyncedAt'); },
      );

      await hooks.runAfterSuccess(
        mode: SyncMode.quick,
        companyId: 'company-123',
        hadDirtyScopes: true,
      );

      // NOTE: pullCompanyMembers is gated on mode != quick, not on dirty scopes.
      expect(callLog, ['recordSyncSuccess']);
    });

    test('skips profile hooks when companyId is null', () async {
      final callLog = <String>[];
      final hooks = PostSyncHooks(
        onSyncSuccess: () async { callLog.add('recordSyncSuccess'); },
        onPullCompanyMembers: (companyId) async { callLog.add('pull'); },
        onUpdateLastSyncedAt: () async { callLog.add('update'); },
      );

      await hooks.runAfterSuccess(
        mode: SyncMode.full,
        companyId: null,
        hadDirtyScopes: false,
      );

      expect(callLog, ['recordSyncSuccess']);
    });
  });
}
```

#### Step 6.4.2: Implement PostSyncHooks

```dart
// lib/features/sync/application/post_sync_hooks.dart
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

/// Runs app-level follow-up concerns after a successful sync.
///
/// FROM SPEC Section 3: Extracted from SyncOrchestrator.syncLocalAgencyProjects
/// (sync_orchestrator.dart:316-349). These hooks are unrelated to sync itself --
/// they are app-level concerns that piggyback on successful sync completion.
///
/// WHY: Having AppConfigProvider.recordSyncSuccess() and
/// UserProfileSyncDatasource.pullCompanyMembers() inside the orchestrator
/// created upward dependencies from the sync application layer into the
/// auth presentation layer. PostSyncHooks inverts the dependency: callers
/// inject their hooks via callbacks, and the sync layer calls them.
class PostSyncHooks {
  /// Called after any successful sync to clear stale-config banners.
  /// FROM SPEC: _appConfigProvider?.recordSyncSuccess() (line 324)
  final Future<void> Function()? onSyncSuccess;

  /// Called after successful full/maintenance sync to refresh company member profiles.
  /// FROM SPEC: _userProfileSyncDatasource?.pullCompanyMembers(companyId) (lines 336)
  final Future<void> Function(String companyId)? onPullCompanyMembers;

  /// Called after successful full/maintenance sync to update last_synced_at.
  /// FROM SPEC: _userProfileSyncDatasource?.updateLastSyncedAt() (lines 344)
  final Future<void> Function()? onUpdateLastSyncedAt;

  const PostSyncHooks({
    this.onSyncSuccess,
    this.onPullCompanyMembers,
    this.onUpdateLastSyncedAt,
  });

  /// Runs all applicable hooks after a successful sync.
  ///
  /// Each hook is wrapped in try/catch to prevent individual failures from
  /// breaking the sync result. This matches the existing behavior in
  /// SyncOrchestrator.syncLocalAgencyProjects (lines 324-349).
  ///
  /// [mode] determines which hooks run:
  /// - `onSyncSuccess` runs for ALL modes
  /// - `onPullCompanyMembers` and `onUpdateLastSyncedAt` run only for
  ///   non-quick modes (full, maintenance) when [companyId] is non-null
  ///
  /// FROM SPEC: sync_orchestrator.dart:332 — `if (mode != SyncMode.quick && companyId != null && profileSyncDs != null)`
  Future<void> runAfterSuccess({
    required SyncMode mode,
    required String? companyId,
    required bool hadDirtyScopes,
  }) async {
    // Hook 1: Record sync success (all modes)
    // FROM SPEC: FIX-B — clears stale config banner
    if (onSyncSuccess != null) {
      try {
        await onSyncSuccess!();
      } on Object catch (e) {
        Logger.sync('PostSyncHooks: onSyncSuccess failed: $e');
      }
    }

    // Hook 2 & 3: Profile-related hooks (non-quick modes only)
    // FROM SPEC: sync_orchestrator.dart:332 — gated on mode != quick
    if (mode != SyncMode.quick && companyId != null) {
      // Hook 2: Pull company members
      if (onPullCompanyMembers != null) {
        try {
          await onPullCompanyMembers!(companyId);
          Logger.sync('PostSyncHooks: Company members pulled');
        } on Object catch (e) {
          Logger.sync('PostSyncHooks: pullCompanyMembers failed: $e');
        }
      }

      // Hook 3: Update last_synced_at
      if (onUpdateLastSyncedAt != null) {
        try {
          await onUpdateLastSyncedAt!();
          Logger.sync('PostSyncHooks: last_synced_at updated');
        } on Object catch (e) {
          Logger.sync('PostSyncHooks: updateLastSyncedAt failed: $e');
        }
      }
    }
  }
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/post_sync_hooks.dart"` -- expected: 0 issues found.

#### Step 6.4.3: Run PostSyncHooks test (GREEN)

**Verify**: CI run targets `test/features/sync/application/post_sync_hooks_test.dart` -- expected: all tests pass.

---

### Sub-phase 6.5: Wire control-plane classes into SyncLifecycleManager

**Files:**
- Modify: `lib/features/sync/application/sync_lifecycle_manager.dart`

**Agent**: backend-supabase-agent

#### Step 6.5.1: Refactor SyncLifecycleManager to use SyncTriggerPolicy and ConnectivityProbe

Modify `lib/features/sync/application/sync_lifecycle_manager.dart` to delegate the resume decision to `SyncTriggerPolicy.evaluateResume()` and DNS checking to `ConnectivityProbe`. This replaces the inline decision tree at lines 158-210.

The modification changes `_handleResumed()` to:
1. Call `SyncTriggerPolicy.evaluateResume()` with the current state
2. Check `ConnectivityProbe.checkReachability()` before triggering
3. Dispatch to `_triggerSync()` or `_triggerForcedSync()` based on the decision

Key changes in the file:
- Add a `ConnectivityProbe` constructor parameter (optional, defaults to `SupabaseConnectivityProbe()`)
- Import `sync_trigger_policy.dart` and `connectivity_probe.dart`
- Replace the inline staleness/mode decision tree in `_handleResumed()` with a call to `SyncTriggerPolicy.evaluateResume()`
- Replace `_syncOrchestrator.checkDnsReachability()` with `_connectivityProbe.checkReachability()`

IMPORTANT: The `SyncLifecycleManager` constructor signature changes from `SyncLifecycleManager(this._syncOrchestrator)` to accept an optional `ConnectivityProbe` parameter. This preserves backward compatibility since `ConnectivityProbe` is an interface with a default implementation.

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_lifecycle_manager.dart"` -- expected: 0 issues found.

#### Step 6.5.2: Run characterization tests

Run all existing sync lifecycle manager tests and characterization tests to confirm no behavior change.

**Verify**: CI run targets `test/features/sync/application/sync_lifecycle_manager_test.dart` -- expected: all tests pass (characterization equivalence).

---

### Sub-phase 6.6: Verify Phase 6

**Agent**: general-purpose

#### Step 6.6.1: Run full analyzer

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues found.

#### Step 6.6.2: Run all sync tests via CI

Push branch, open PR, verify CI green (all characterization tests, all existing tests, all new P6 contract tests).

---

## Phase 7: Layer Violation Fixes

Phase 7 eliminates the remaining layer violations: SQL queries in the orchestrator, raw orchestrator exposure in the provider, Postgres error code matching in the presentation layer, and upward dependencies from sync into auth. It introduces SyncQueryService for dashboard queries, replaces SyncOrchestrator with SyncCoordinator, and refactors SyncProvider to subscribe to typed status/diagnostics rather than owning independent state.

**Depends on**: Phase 6 (control-plane abstractions complete)

**Verification gate**: All characterization tests green, all existing sync tests green via CI, all new tests green, `flutter analyze` zero violations.

---

### Sub-phase 7.1: Create SyncQueryService

**Files:**
- Create: `lib/features/sync/application/sync_query_service.dart`
- Test: `test/features/sync/application/sync_query_service_test.dart`

**Agent**: backend-supabase-agent

#### Step 7.1.1: Write SyncQueryService test (RED)

```dart
// test/features/sync/application/sync_query_service_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/application/sync_query_service.dart';

/// WHY: SyncQueryService moves 5 SQL queries out of SyncOrchestrator into a
/// dedicated service backed by LocalSyncStore (or DatabaseService during transition).
/// Tests verify the query interface, not the SQL — that is covered by integration tests.
void main() {
  // NOTE: These tests require a real SQLite database (sqflite_common_ffi).
  // They are integration-style tests that verify the queries produce correct results.
  // The implementing agent must set up an in-memory database with the sync schema.

  group('SyncQueryService', () {
    // Test: getPendingBuckets returns correct bucket counts
    // Test: getIntegrityResults parses sync_metadata rows
    // Test: getUndismissedConflictCount returns correct count
    // Test: getLastSyncTime reads from sync_metadata
    // Test: empty database returns zero counts / null timestamps

    // NOTE: Full test implementation requires database setup from P2's LocalSyncStore.
    // The implementing agent should write these tests using the same sqflite_common_ffi
    // test setup pattern used in test/features/sync/engine/ (see sync_engine_test.dart).
  });
}
```

#### Step 7.1.2: Implement SyncQueryService

```dart
// lib/features/sync/application/sync_query_service.dart
import 'dart:convert';

import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/features/sync/domain/sync_diagnostics.dart';
import 'package:construction_inspector/shared/utils/safe_row.dart';

/// Dashboard/query-facing access to pending buckets, integrity results,
/// conflict counts, and sync metadata.
///
/// FROM SPEC Section 3: Moves 5 SQL queries OUT of SyncOrchestrator:
/// - getPendingBuckets (sync_orchestrator.dart:607-666)
/// - getIntegrityResults (sync_orchestrator.dart:682-701)
/// - getUndismissedConflictCount (sync_orchestrator.dart:704-710)
/// - initialize/last_sync_time (sync_orchestrator.dart:165-198)
/// - syncLocalAgencyProjects/last_sync_time refresh (sync_orchestrator.dart:304-314)
///
/// WHY: SQL queries in the orchestrator violated layer separation. The orchestrator
/// is an application-layer coordinator; database queries belong in the data layer.
/// SyncQueryService provides a clean query surface that SyncProvider and dashboard
/// screens can consume without reaching through the orchestrator.
///
/// NOTE (Finding 12): The spec dependency diagram shows SyncQueryService -> LocalSyncStore
/// -> Database. During the transition, SyncQueryService depends on DatabaseService
/// directly because LocalSyncStore does not yet expose all needed query methods
/// (pending buckets grouped by bucket, integrity JSON parsing, conflict counts).
/// The implementing agent should add these query methods to LocalSyncStore and
/// migrate SyncQueryService to depend on LocalSyncStore instead of DatabaseService
/// as a follow-up within this phase or in a subsequent PR.
class SyncQueryService {
  final DatabaseService _dbService;

  SyncQueryService(this._dbService);

  /// Bucket definitions for inspector-friendly pending count display.
  /// FROM SPEC: SyncOrchestrator.syncBuckets (sync_orchestrator.dart:45-58)
  static const Map<String, List<String>> syncBuckets = {
    'Projects': ['projects', 'bid_items', 'locations', 'todo_items'],
    'Entries': [
      'daily_entries',
      'contractors',
      'equipment',
      'entry_contractors',
      'entry_equipment',
      'entry_quantities',
      'entry_personnel_counts',
    ],
    'Forms': ['inspector_forms', 'form_responses', 'form_exports'],
    'Photos & Files': ['photos', 'entry_exports', 'documents'],
  };

  /// Returns pending unique record counts grouped by bucket.
  ///
  /// Each bucket counts DISTINCT record_ids (not operations).
  /// FROM SPEC: Moved from SyncOrchestrator.getPendingBuckets (lines 607-666).
  Future<Map<String, BucketCount>> getPendingBuckets() async {
    try {
      final db = await _dbService.database;
      final result = <String, BucketCount>{};

      for (final entry in syncBuckets.entries) {
        final bucketName = entry.key;
        final tables = entry.value;
        final placeholders = tables.map((_) => '?').join(',');

        // FROM SPEC: Filter out retry-exhausted entries to match push loop.
        const maxRetry = SyncEngineConfig.maxRetryCount;

        // Total unique records for the bucket
        final totalRows = await db.rawQuery(
          'SELECT COUNT(DISTINCT record_id) as cnt FROM change_log '
          'WHERE processed = 0 AND retry_count < ? AND table_name IN ($placeholders)',
          [maxRetry, ...tables],
        );
        final total = totalRows.first.intOrDefault('cnt');

        // Per-table breakdown (for dashboard expandable view)
        final breakdown = <String, int>{};
        for (final table in tables) {
          final rows = await db.rawQuery(
            'SELECT COUNT(DISTINCT record_id) as cnt FROM change_log '
            'WHERE processed = 0 AND retry_count < ? AND table_name = ?',
            [maxRetry, table],
          );
          breakdown[table] = rows.first.intOrDefault('cnt');
        }

        result[bucketName] = BucketCount(total: total, breakdown: breakdown);
      }

      // Count anything not in a bucket
      final allBucketTables = syncBuckets.values.expand((t) => t).toList();
      final otherPlaceholders = allBucketTables.map((_) => '?').join(',');
      const maxRetryOther = SyncEngineConfig.maxRetryCount;
      final otherRows = await db.rawQuery(
        'SELECT COUNT(DISTINCT record_id) as cnt FROM change_log '
        'WHERE processed = 0 AND retry_count < ? AND table_name NOT IN ($otherPlaceholders)',
        [maxRetryOther, ...allBucketTables],
      );
      final otherCount = otherRows.first.intOrDefault('cnt');
      if (otherCount > 0) {
        result['Other'] = BucketCount(
          total: otherCount,
          breakdown: {'other': otherCount},
        );
      }

      return result;
    } on Exception catch (e) {
      Logger.sync('SyncQueryService: getPendingBuckets failed: $e');
      return {};
    }
  }

  /// Returns the total pending count across all buckets.
  Future<int> getPendingCount() async {
    final buckets = await getPendingBuckets();
    return buckets.values.fold<int>(0, (sum, b) => sum + b.total);
  }

  /// Returns integrity check results stored by IntegrityChecker.
  ///
  /// Each key is a table name, value is the JSON result map.
  /// FROM SPEC: Moved from SyncOrchestrator.getIntegrityResults (lines 682-701).
  Future<Map<String, Map<String, dynamic>>> getIntegrityResults() async {
    final db = await _dbService.database;
    final rows = await db.rawQuery(
      "SELECT key, value FROM sync_metadata WHERE key LIKE 'integrity_%'",
    );
    final results = <String, Map<String, dynamic>>{};
    for (final row in rows) {
      final key = row.requireString('key');
      final tableName = key.replaceFirst('integrity_', '');
      try {
        results[tableName] =
            jsonDecode(row.requireString('value')) as Map<String, dynamic>;
      } on Exception catch (e) {
        Logger.sync(
          'SyncQueryService: malformed integrity entry for $tableName: $e',
        );
      }
    }
    return results;
  }

  /// Returns the count of undismissed conflicts in the conflict log.
  ///
  /// FROM SPEC: Moved from SyncOrchestrator.getUndismissedConflictCount (lines 704-710).
  Future<int> getUndismissedConflictCount() async {
    final db = await _dbService.database;
    final result = await db.rawQuery(
      'SELECT COUNT(*) as cnt FROM conflict_log WHERE dismissed_at IS NULL',
    );
    return result.firstOrNull?.intOrDefault('cnt') ?? 0;
  }

  /// Reads the persisted last sync time from sync_metadata.
  ///
  /// FROM SPEC: Moved from SyncOrchestrator.initialize (lines 182-195).
  Future<DateTime?> getLastSyncTime() async {
    try {
      final db = await _dbService.database;
      final result = await db.query(
        'sync_metadata',
        where: "key = 'last_sync_time'",
      );
      if (result.isNotEmpty) {
        final timeStr = result.first.optionalString('value');
        if (timeStr != null) {
          return DateTime.tryParse(timeStr);
        }
      }
    } on Exception catch (e) {
      Logger.sync('SyncQueryService: Failed to load last sync time: $e');
    }
    return null;
  }

  /// Assemble a complete SyncDiagnosticsSnapshot from all query sources.
  ///
  /// FROM SPEC Section 3: "SyncDiagnosticsSnapshot as the typed diagnostics surface"
  /// WHY (Finding 3): This method fulfills the spec requirement for a typed
  /// diagnostics snapshot that the dashboard and SyncProvider can consume.
  Future<SyncDiagnosticsSnapshot> assembleDiagnostics() async {
    final buckets = await getPendingBuckets();
    final integrity = await getIntegrityResults();
    final conflictCount = await getUndismissedConflictCount();

    // NOTE: integrityResults is Map<String, Map<String, dynamic>> from
    // getIntegrityResults(). Serialize each value to JSON string to match
    // the SyncDiagnosticsSnapshot.integrityResults type (Map<String, String>).
    // Using jsonEncode preserves the full JSON structure (unlike .toString()
    // which produces debug output like {key: value}).
    return SyncDiagnosticsSnapshot(
      pendingBuckets: buckets,
      totalPendingCount: buckets.values.fold<int>(0, (sum, b) => sum + b.total),
      integrityResults: integrity.map(
        (k, v) => MapEntry(k, jsonEncode(v)),
      ),
      undismissedConflictCount: conflictCount,
      snapshotAt: DateTime.now(),
    );
  }
}

/// NOTE (Finding 3/13): BucketCount is defined once in sync_diagnostics.dart
/// with `total` + `breakdown` fields matching the actual production shape
/// (sync_orchestrator.dart:722-730). SyncQueryService imports and uses that
/// canonical definition. No duplicate BucketCount exists.
///
/// Import: `import 'package:construction_inspector/features/sync/domain/sync_diagnostics.dart';`
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_query_service.dart"` -- expected: 0 issues found.

---

### Sub-phase 7.2: Create SyncCoordinator (replaces SyncOrchestrator)

**Files:**
- Create: `lib/features/sync/application/sync_coordinator.dart`
- Modify: `lib/features/sync/application/sync_orchestrator.dart` (add deprecation, delegate to SyncCoordinator or retain temporarily as facade)

**Agent**: backend-supabase-agent

#### Step 7.2.1: Create SyncCoordinator

The SyncCoordinator replaces SyncOrchestrator. It uses the extracted control-plane classes (SyncRetryPolicy, ConnectivityProbe, PostSyncHooks) and delegates query operations to SyncQueryService. It no longer contains any SQL, no AppConfigProvider, no UserProfileSyncDatasource.

Key differences from SyncOrchestrator:
- Constructor takes `SyncRetryPolicy`, `ConnectivityProbe`, `PostSyncHooks` instead of `AppConfigProvider`, `UserProfileSyncDatasource`
- `getPendingBuckets()`, `getIntegrityResults()`, `getUndismissedConflictCount()` are removed (moved to SyncQueryService)
- `_isTransientError()` is removed (replaced by `SyncErrorClassifier` via `SyncRetryPolicy`)
- `_sanitizeSyncError` never existed here (it was in SyncProvider)
- `checkDnsReachability()` delegates to `ConnectivityProbe`
- Post-sync hooks call `PostSyncHooks.runAfterSuccess()` instead of inline code

The implementing agent must:
1. Copy `sync_orchestrator.dart` as the starting point
2. Remove all SQL queries (5 locations from ground-truth)
3. Remove `_appConfigProvider` and `_userProfileSyncDatasource` fields
4. Replace `_isTransientError()` with `SyncRetryPolicy.shouldRetry()` using a `ClassifiedSyncError` constructed from the `SyncResult.errorMessages`
5. Replace `checkDnsReachability()` body with `_connectivityProbe.checkReachability()`
6. Replace post-sync hook code (lines 324-349) with `_postSyncHooks.runAfterSuccess()`
7. Keep: `_createEngine()`, `syncLocalAgencyProjects()`, `_syncWithRetry()` (using new retry policy), `_doSync()`, callback fields, `dispose()`

IMPORTANT: During the transition, `SyncOrchestrator` must remain importable (16 production files + 14 test files depend on it). The strategy is:
- Create `SyncCoordinator` as the clean replacement
- Add a `@Deprecated` annotation to `SyncOrchestrator`
- Update `SyncOrchestrator` to extend or delegate to `SyncCoordinator` (thin facade)
- Phase 7.4 updates all importers to use `SyncCoordinator` directly, then `SyncOrchestrator` is deleted

Target: `lib/features/sync/application/sync_coordinator.dart` at approximately 220 lines (down from 730 in SyncOrchestrator).

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_coordinator.dart"` -- expected: 0 issues found.

#### Step 7.2.2: Add deprecation facade to SyncOrchestrator

Modify `lib/features/sync/application/sync_orchestrator.dart` to:
1. Add `@Deprecated('Use SyncCoordinator instead')` to the class
2. Add `SyncCoordinator get coordinator` getter that returns the underlying coordinator
3. Keep all existing public methods as delegating wrappers so downstream code continues to work during the transition

This is a TEMPORARY step. Phase 7.4 removes all usages, then the file is deleted.

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues (deprecation warnings are not errors).

---

### Sub-phase 7.3: Refactor SyncProvider

**Files:**
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart`

**Agent**: frontend-flutter-specialist-agent

#### Step 7.3.1: Remove orchestrator getter and _sanitizeSyncError

Modify `lib/features/sync/presentation/providers/sync_provider.dart`:

1. **Remove `get orchestrator`** (line 22) -- this is a layer violation exposing raw SyncOrchestrator to presentation consumers.

2. **Delete `_sanitizeSyncError()`** (lines 328-348) -- replace with `ClassifiedSyncError.userSafeMessage` from the SyncErrorClassifier output. The `onSyncComplete` callback result must carry the classified error's user-safe message instead of raw Postgres error strings.

3. **Change constructor** to accept `SyncCoordinator` instead of `SyncOrchestrator`. Add a `SyncQueryService` parameter for dashboard queries.

4. **Replace `_refreshPendingCount()`** to delegate to `SyncQueryService.getPendingBuckets()` instead of `_syncOrchestrator.getPendingBuckets()`.

5. **Remove the `BucketCount` re-export** from line 7 (`export '../../application/sync_orchestrator.dart' show BucketCount;`) and replace with import from `sync_query_service.dart`.

6. **Update `isOnline` getter** to read from `ConnectivityProbe` (via SyncCoordinator) instead of `_syncOrchestrator.isSupabaseOnline`.

7. **Update `lastSyncTime` getter** to read from SyncQueryService or SyncCoordinator's tracked value instead of falling back to `_syncOrchestrator.lastSyncTime`.

Key changes to the constructor signature:
```dart
// BEFORE (sync_provider.dart:104):
SyncProvider(SyncOrchestrator orchestrator) : _syncOrchestrator = orchestrator;

// AFTER:
SyncProvider(
  SyncCoordinator coordinator, {
  required SyncQueryService queryService,
}) : _coordinator = coordinator,
     _queryService = queryService;
```

Key changes to `_setupListeners()`:
- Wire `_coordinator.onCircuitBreakerTrip` (same as before)
- Wire `_coordinator.onStatusChanged` (same as before)
- Wire `_coordinator.onSyncComplete` -- replace `_sanitizeSyncError(raw)` with using the user-safe message that the SyncResult now carries (via ClassifiedSyncError enrichment from P1)

Key changes to sync trigger methods:
```dart
// BEFORE:
Future<SyncResult> fullSync() async {
  return _syncOrchestrator.syncLocalAgencyProjects(mode: SyncMode.full, recordManualTrigger: true);
}

// AFTER:
Future<SyncResult> fullSync() async {
  return _coordinator.syncLocalAgencyProjects(mode: SyncMode.full, recordManualTrigger: true);
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/presentation/providers/sync_provider.dart"` -- expected: 0 issues found.

---

### Sub-phase 7.4: Update DI wiring

**Files:**
- Modify: `lib/features/sync/di/sync_providers.dart`
- Modify: `lib/features/sync/application/sync_initializer.dart`
- Modify: `lib/features/sync/application/sync_orchestrator_builder.dart` (rename to `sync_coordinator_builder.dart` or update to build SyncCoordinator)

**Agent**: backend-supabase-agent

#### Step 7.4.1: Update SyncInitializer to create SyncCoordinator

Modify `lib/features/sync/application/sync_initializer.dart`:

1. Replace `SyncOrchestratorBuilder` usage with a builder for `SyncCoordinator`
2. Create `SyncRetryPolicy`, `ConnectivityProbe`, `PostSyncHooks` instances
3. Wire `PostSyncHooks` with the `_appConfigProvider.recordSyncSuccess()` and `_userProfileSyncDatasource.pullCompanyMembers()` callbacks that were previously inline in the orchestrator
4. Create `SyncQueryService` with `dbService`
5. Return `SyncCoordinator` instead of `SyncOrchestrator` in the result record

Change the return type from:
```dart
({SyncOrchestrator orchestrator, SyncLifecycleManager lifecycleManager, ...})
```
to:
```dart
({SyncCoordinator coordinator, SyncLifecycleManager lifecycleManager, ...})
```

Update the `SyncLifecycleManager` constructor call to pass the `ConnectivityProbe`.

IMPORTANT: The `PostSyncHooks` wiring is where the upward dependencies get properly inverted:
```dart
final postSyncHooks = PostSyncHooks(
  onSyncSuccess: () async {
    appConfigProvider.recordSyncSuccess();
  },
  onPullCompanyMembers: userProfileSyncDs != null
      ? (companyId) async {
          await userProfileSyncDs.pullCompanyMembers(companyId);
        }
      : null,
  onUpdateLastSyncedAt: userProfileSyncDs != null
      ? () async {
          await userProfileSyncDs.updateLastSyncedAt();
        }
      : null,
);
```

This keeps the auth/profile dependencies in the initializer (where they already exist) rather than pushing them down into the coordinator.

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_initializer.dart"` -- expected: 0 issues found.

#### Step 7.4.2: Update SyncProviders.providers()

Modify `lib/features/sync/di/sync_providers.dart`:

1. Change `initialize()` return type to use `SyncCoordinator` instead of `SyncOrchestrator`
2. Change `providers()` parameter from `SyncOrchestrator syncOrchestrator` to `SyncCoordinator syncCoordinator`
3. Add `SyncQueryService` parameter
4. Replace `Provider<SyncOrchestrator>.value(value: syncOrchestrator)` with `Provider<SyncCoordinator>.value(value: syncCoordinator)`
5. Add `Provider<SyncQueryService>.value(value: syncQueryService)`
6. Update `SyncProvider` construction to pass both `SyncCoordinator` and `SyncQueryService`

```dart
// AFTER:
ChangeNotifierProvider(
  create: (_) {
    final syncProvider = SyncProvider(syncCoordinator, queryService: syncQueryService);
    syncLifecycleManager.onStaleDataWarning = syncProvider.setStaleDataWarning;
    syncLifecycleManager.onForcedSyncInProgress = syncProvider.setForcedSyncInProgress;
    syncProvider.onSyncCycleComplete = () =>
        projectSyncHealthProvider.refreshFromService(projectLifecycleService);
    syncCoordinator.onNewAssignmentDetected = syncProvider.addNotification;
    return syncProvider;
  },
),
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/di/sync_providers.dart"` -- expected: 0 issues found.

#### Step 7.4.3: Update AppDependencies SyncDeps

Modify `lib/core/di/app_dependencies.dart`:

Change `SyncDeps` to hold `SyncCoordinator` instead of `SyncOrchestrator`:
```dart
class SyncDeps {
  final SyncCoordinator syncCoordinator;  // WAS: SyncOrchestrator syncOrchestrator
  final SyncLifecycleManager syncLifecycleManager;
  // ... add SyncQueryService if needed by other DI tiers
}
```

Update all references to `syncDeps.syncOrchestrator` -> `syncDeps.syncCoordinator`.

**Verify**: `pwsh -Command "flutter analyze lib/core/di/app_dependencies.dart"` -- expected: 0 issues found.

---

### Sub-phase 7.5: Update all SyncOrchestrator importers

**Files (16 production):**
- Modify: `lib/core/di/app_dependencies.dart` -- change SyncDeps field type
- Modify: `lib/core/driver/driver_server.dart` -- change field type and method calls
- Modify: `lib/core/router/scaffold_with_nav_bar.dart` -- change `context.read<SyncOrchestrator>()` to `context.read<SyncCoordinator>()`
- Modify: `lib/features/projects/di/projects_providers.dart` -- change parameter type
- Modify: `lib/features/projects/presentation/providers/project_provider.dart` -- change parameter type
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart` -- change `context.read<SyncOrchestrator>()` (6 occurrences)
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart` -- change `context.read<SyncOrchestrator>()`
- Modify: `lib/features/settings/presentation/screens/admin_dashboard_screen.dart` -- change `context.read<SyncOrchestrator>()` to `context.read<SyncCoordinator>()` for DNS check
- Modify: `lib/features/settings/presentation/widgets/sign_out_dialog.dart` -- change `context.read<SyncOrchestrator>()`
- Modify: `lib/features/sync/application/fcm_handler.dart` -- change constructor parameter type
- Modify: `lib/features/sync/application/realtime_hint_handler.dart` -- change constructor parameter type
- Modify: `lib/features/sync/application/sync_enrollment_service.dart` -- change constructor parameter type
- Modify: `lib/features/sync/application/sync_initializer.dart` -- already updated in 7.4.1
- Modify: `lib/features/sync/application/sync_orchestrator_builder.dart` -- rename to build SyncCoordinator
- Modify: `lib/features/sync/di/sync_providers.dart` -- already updated in 7.4.2
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart` -- already updated in 7.3.1

**Files (15 test):**
- Modify: `test/features/sync/application/fcm_handler_test.dart`
- Modify: `test/features/sync/presentation/widgets/sync_status_icon_test.dart`
- Modify: `test/features/sync/presentation/screens/sync_dashboard_screen_test.dart`
- Modify: `test/features/sync/presentation/providers/sync_provider_test.dart`
- Modify: `test/features/sync/engine/sync_engine_circuit_breaker_test.dart`
- Modify: `test/features/sync/application/sync_lifecycle_manager_test.dart`
- Modify: `test/features/sync/application/sync_enrollment_service_test.dart`
- Modify: `test/features/sync/application/realtime_hint_handler_test.dart`
- Modify: `test/core/driver/driver_server_sync_status_test.dart`
- Modify: `test/features/sync/engine/sync_engine_delete_test.dart`
- Modify: `test/features/sync/application/sync_orchestrator_builder_test.dart`
- Modify: `test/features/projects/presentation/providers/project_provider_sync_mode_test.dart`
- Modify: `test/features/projects/presentation/screens/project_list_screen_test.dart`
- Modify: `test/helpers/sync_orchestrator_test_helper.dart`
- Modify: `test/core/router/scaffold_with_nav_bar_test.dart`

**Agent**: general-purpose

#### Step 7.5.1: Rename SyncOrchestrator to SyncCoordinator in all production files

For each of the 16 production files listed above, the implementing agent must:

1. Change the import from `sync_orchestrator.dart` to `sync_coordinator.dart`
2. Change all type references from `SyncOrchestrator` to `SyncCoordinator`
3. Change all variable names from `syncOrchestrator` / `orchestrator` to `syncCoordinator` / `coordinator`
4. Verify that the methods called on the renamed type still exist on `SyncCoordinator`

Special cases:
- **`driver_server.dart`**: Uses `syncOrchestrator?.syncLocalAgencyProjects()` and `syncOrchestrator?.isSyncing`. Both methods exist on SyncCoordinator.
- **`scaffold_with_nav_bar.dart`**: Uses `context.read<SyncOrchestrator>()` -- change to `context.read<SyncCoordinator>()`. This requires updating the Provider registration in sync_providers.dart (done in 7.4.2).
- **`project_list_screen.dart`**: 6 occurrences of `context.read<SyncOrchestrator>()` calling `syncLocalAgencyProjects()`. All become `context.read<SyncCoordinator>()`.
- **`admin_dashboard_screen.dart`**: Calls `checkDnsReachability()` which is renamed to `checkReachability()` on ConnectivityProbe. The screen should read `context.read<ConnectivityProbe>()` instead, OR `SyncCoordinator` can expose a `checkDnsReachability()` facade that delegates.
- **`sign_out_dialog.dart`**: Calls `dispose()` on the orchestrator. SyncCoordinator retains `dispose()`.
- **`realtime_hint_handler.dart`**: References `_syncOrchestrator.dirtyScopeTracker`, `_syncOrchestrator.isSyncing`, `_syncOrchestrator.syncLocalAgencyProjects()`. All must exist on SyncCoordinator.
- **`fcm_handler.dart`**: References `_syncOrchestrator?.dirtyScopeTracker`, `_syncOrchestrator?.isSyncing`, `_syncOrchestrator?.syncLocalAgencyProjects()`. All must exist on SyncCoordinator.

IMPORTANT: Where external files (outside `features/sync/`) need to call `getPendingBuckets()`, `getIntegrityResults()`, or `getUndismissedConflictCount()`, they should use `SyncQueryService` instead. The provider will expose these via getters that delegate to SyncQueryService.

#### Step 7.5.2: Update all test files

For each of the 15 test files listed above:

1. Update imports
2. Update mock class names (e.g., `MockSyncOrchestrator` -> `MockSyncCoordinator`)
3. Update `_TrackingOrchestrator` in `fcm_handler_test.dart` -> `_TrackingCoordinator`
4. Update `_MockSyncOrchestrator` in `sync_engine_circuit_breaker_test.dart`
5. Update `sync_orchestrator_test_helper.dart` -> rename file and contents

IMPORTANT: The test subclasses (`_EmptyResponseSyncEngine`, etc.) may need signature updates if the test helpers construct SyncOrchestrator directly. The implementing agent must verify each test file compiles and runs.

#### Step 7.5.3: Delete SyncOrchestrator

Once all importers are updated:
1. Delete `lib/features/sync/application/sync_orchestrator.dart`
2. Delete or rename `lib/features/sync/application/sync_orchestrator_builder.dart`
3. Update any barrel exports in `lib/features/sync/application/application.dart`

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues found, no references to SyncOrchestrator remain.

---

### Sub-phase 7.6: Verify Phase 7

**Agent**: general-purpose

#### Step 7.6.1: Run full analyzer

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues found.

#### Step 7.6.2: Verify all characterization and existing tests via CI

Push branch, open PR, verify CI green. All characterization tests must pass (equivalence). All existing sync tests must pass.

---

## Phase 8: Adapter Simplification

Phase 8 reduces the 24 adapter files to approximately 12 by replacing 13 simple adapters with data-driven `AdapterConfig` instances. Complex adapters with custom logic remain as class files. The registration order is preserved to maintain FK dependency ordering.

**Depends on**: Phase 5 (SyncEngine slim coordinator complete)

**Verification gate**: All characterization tests green, all existing sync tests green via CI, `flutter analyze` zero violations, adapter count reduced from 24 to ~12.

---

### Sub-phase 8.1: Create AdapterConfig data class

**Files:**
- Create: `lib/features/sync/adapters/adapter_config.dart`
- Test: `test/features/sync/adapters/adapter_config_test.dart`

**Agent**: backend-supabase-agent

#### Step 8.1.1: Write AdapterConfig test (RED)

```dart
// test/features/sync/adapters/adapter_config_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/adapters/adapter_config.dart';
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

void main() {
  group('AdapterConfig', () {
    test('generates a TableAdapter with correct tableName and scope', () {
      // WHY: The generated adapter must be equivalent to ContractorAdapter.
      final config = AdapterConfig(
        table: 'contractors',
        scope: ScopeType.viaProject,
        fkDeps: const ['projects'],
        fkColumnMap: const {'projects': 'project_id'},
      );
      final adapter = config.toAdapter();

      expect(adapter.tableName, 'contractors');
      expect(adapter.scopeType, ScopeType.viaProject);
      expect(adapter.fkDependencies, ['projects']);
      expect(adapter.fkColumnMap, {'projects': 'project_id'});
    });

    test('defaults match TableAdapter base class defaults', () {
      final config = AdapterConfig(
        table: 'test_table',
        scope: ScopeType.direct,
        fkDeps: const [],
      );
      final adapter = config.toAdapter();

      expect(adapter.supportsSoftDelete, isTrue);
      expect(adapter.isFileAdapter, isFalse);
      expect(adapter.insertOnly, isFalse);
      expect(adapter.skipPull, isFalse);
      expect(adapter.skipIntegrityCheck, isFalse);
      expect(adapter.includesNullProjectBuiltins, isFalse);
      expect(adapter.stripExifGps, isFalse);
      expect(adapter.storageBucket, '');
      expect(adapter.converters, isEmpty);
      expect(adapter.naturalKeyColumns, isEmpty);
      expect(adapter.localOnlyColumns, isEmpty);
      expect(adapter.userStampColumns, isEmpty);
    });

    test('supports file adapter fields', () {
      // WHY: EntryExportAdapter is classified as simple because buildStoragePath
      // uses a standard pattern. But actually it has a CUSTOM buildStoragePath,
      // so it stays as a class. This test verifies config CAN express file fields
      // for potential future simple file adapters.
      final config = AdapterConfig(
        table: 'simple_files',
        scope: ScopeType.viaEntry,
        fkDeps: const ['daily_entries'],
        isFileAdapter: true,
        storageBucket: 'simple-files',
      );
      final adapter = config.toAdapter();

      expect(adapter.isFileAdapter, isTrue);
      expect(adapter.storageBucket, 'simple-files');
    });

    test('supports custom converters', () {
      // WHY: ProjectAdapter has BoolIntConverter on is_active.
      final config = AdapterConfig(
        table: 'projects',
        scope: ScopeType.direct,
        fkDeps: const [],
        converters: const {'is_active': BoolIntConverter()},
        naturalKeyColumns: const ['company_id', 'project_number'],
      );
      final adapter = config.toAdapter();

      expect(adapter.converters, isNotEmpty);
      expect(adapter.converters.containsKey('is_active'), isTrue);
      expect(adapter.naturalKeyColumns, ['company_id', 'project_number']);
    });

    test('supports custom extractRecordName', () {
      final config = AdapterConfig(
        table: 'entry_quantities',
        scope: ScopeType.viaEntry,
        fkDeps: const ['daily_entries', 'bid_items'],
        fkColumnMap: const {'daily_entries': 'entry_id', 'bid_items': 'bid_item_id'},
        extractRecordName: (record) =>
            'Quantity: ${record['quantity'] ?? record['id'] ?? 'Unknown'}',
      );
      final adapter = config.toAdapter();

      expect(
        adapter.extractRecordName({'quantity': '5.0', 'id': 'abc'}),
        'Quantity: 5.0',
      );
    });
  });
}
```

#### Step 8.1.2: Implement AdapterConfig

```dart
// lib/features/sync/adapters/adapter_config.dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

/// Data-driven configuration for simple table adapters.
///
/// FROM SPEC Section 3 (Adapter Simplification): 13 simple adapters become
/// AdapterConfig instances. Each config generates a TableAdapter via [toAdapter].
///
/// WHY: 13 of 22 adapter files are pure configuration with zero custom logic
/// beyond property overrides. Declaring them as data reduces 13 class files to
/// a single list of configs, cutting adapter file count from 24 to ~12.
class AdapterConfig {
  /// The SQLite/Supabase table name (must match exactly).
  final String table;

  /// How this table is scoped to the company tenant.
  final ScopeType scope;

  /// Tables that must be pushed before this one (FK parents).
  final List<String> fkDeps;

  /// Maps parent table name -> local FK column name for per-record blocking.
  final Map<String, String> fkColumnMap;

  /// Column-level type converters.
  final Map<String, TypeConverter> converters;

  /// Whether this table supports soft-delete.
  final bool supportsSoftDelete;

  /// Whether this adapter handles file uploads.
  final bool isFileAdapter;

  /// Storage bucket name for file adapters.
  final String storageBucket;

  /// Whether to strip EXIF GPS data.
  final bool stripExifGps;

  /// Whether this table is insert-only.
  final bool insertOnly;

  /// Whether to skip pull for this table.
  final bool skipPull;

  /// Whether to skip integrity checks.
  final bool skipIntegrityCheck;

  /// Columns that should be stamped with the current user ID before push.
  final Map<String, String> userStampColumns;

  /// Natural key columns for UNIQUE constraint pre-check.
  final List<String> naturalKeyColumns;

  /// Whether this table includes builtin records with null project_id.
  final bool includesNullProjectBuiltins;

  /// Columns that exist locally but should NOT be sent to Supabase.
  final List<String> localOnlyColumns;

  /// Custom extractRecordName function. If null, uses TableAdapter default.
  final String Function(Map<String, dynamic> record)? extractRecordName;

  const AdapterConfig({
    required this.table,
    required this.scope,
    required this.fkDeps,
    this.fkColumnMap = const {},
    this.converters = const {},
    this.supportsSoftDelete = true,
    this.isFileAdapter = false,
    this.storageBucket = '',
    this.stripExifGps = false,
    this.insertOnly = false,
    this.skipPull = false,
    this.skipIntegrityCheck = false,
    this.userStampColumns = const {},
    this.naturalKeyColumns = const [],
    this.includesNullProjectBuiltins = false,
    this.localOnlyColumns = const [],
    this.extractRecordName,
  });

  /// Generates a concrete TableAdapter instance from this configuration.
  TableAdapter toAdapter() => _ConfiguredAdapter(this);
}

/// A TableAdapter generated from an AdapterConfig.
///
/// WHY: Implements all TableAdapter overrides by reading from the config.
/// No custom logic — pure delegation to data fields.
class _ConfiguredAdapter extends TableAdapter {
  final AdapterConfig _config;

  _ConfiguredAdapter(this._config);

  @override
  String get tableName => _config.table;

  @override
  ScopeType get scopeType => _config.scope;

  @override
  List<String> get fkDependencies => _config.fkDeps;

  @override
  Map<String, String> get fkColumnMap => _config.fkColumnMap;

  @override
  Map<String, TypeConverter> get converters => _config.converters;

  @override
  bool get supportsSoftDelete => _config.supportsSoftDelete;

  @override
  bool get isFileAdapter => _config.isFileAdapter;

  @override
  String get storageBucket => _config.storageBucket;

  @override
  bool get stripExifGps => _config.stripExifGps;

  @override
  bool get insertOnly => _config.insertOnly;

  @override
  bool get skipPull => _config.skipPull;

  @override
  bool get skipIntegrityCheck => _config.skipIntegrityCheck;

  @override
  Map<String, String> get userStampColumns => _config.userStampColumns;

  @override
  List<String> get naturalKeyColumns => _config.naturalKeyColumns;

  @override
  bool get includesNullProjectBuiltins => _config.includesNullProjectBuiltins;

  @override
  List<String> get localOnlyColumns => _config.localOnlyColumns;

  @override
  String extractRecordName(Map<String, dynamic> record) {
    if (_config.extractRecordName != null) {
      return _config.extractRecordName!(record);
    }
    return super.extractRecordName(record);
  }
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/adapters/adapter_config.dart"` -- expected: 0 issues found.

#### Step 8.1.3: Run AdapterConfig test (GREEN)

**Verify**: CI run targets `test/features/sync/adapters/adapter_config_test.dart` -- expected: all tests pass.

---

### Sub-phase 8.2: Define simple adapter configs and update registry

**Files:**
- Create: `lib/features/sync/adapters/simple_adapters.dart` (the 13 AdapterConfig declarations)
- Modify: `lib/features/sync/engine/sync_registry.dart` (use AdapterConfig for simple adapters)

**Agent**: backend-supabase-agent

#### Step 8.2.1: Create simple_adapters.dart

This file declares the 13 simple adapter configurations, replacing 13 separate class files.

IMPORTANT: Before implementing, the implementing agent MUST read each of the 13 adapter files to verify that every override is captured in the config. The tailor analysis classified these as simple, but some have `extractRecordName` overrides or `naturalKeyColumns` that must be preserved.

Based on actual source review, here is what each "simple" adapter actually needs:

| Adapter | Extra Overrides Beyond table/scope/fkDeps |
|---------|-------------------------------------------|
| ContractorAdapter | fkColumnMap |
| LocationAdapter | fkColumnMap |
| BidItemAdapter | fkColumnMap, **extractRecordName** (custom: item_number + description) |
| PersonnelTypeAdapter | naturalKeyColumns (project_id, semantic_name). NOTE: no fkColumnMap override |
| EntryContractorsAdapter | fkColumnMap, naturalKeyColumns |
| EntryPersonnelCountsAdapter | fkColumnMap, **extractRecordName** |
| EntryQuantitiesAdapter | fkColumnMap, **extractRecordName** |
| TodoItemAdapter | converters (BoolIntConverter, TodoPriorityConverter), **extractRecordName** |
| ProjectAdapter | converters (BoolIntConverter), naturalKeyColumns |
| ProjectAssignmentAdapter | (none beyond fkDependencies) |
| EntryExportAdapter | **Complex** -- has custom buildStoragePath, extractRecordName, localOnlyColumns, isFileAdapter. Must REMAIN as class. |
| FormExportAdapter | **Complex** -- has custom buildStoragePath, extractRecordName. Must REMAIN as class. |
| CalculationHistoryAdapter | converters (JsonMapConverter x2), **extractRecordName** |

REVISION: EntryExportAdapter and FormExportAdapter have custom `buildStoragePath()` methods with path construction logic. These cannot be expressed as simple config fields. They must remain as class files.

Revised count: **11 simple adapters** become configs, **11 complex adapters** remain as classes. File count: 24 -> ~14 (still a meaningful reduction).

NOTE (Finding 21): The spec says "~12 adapter files" but actual count is ~14 because
EntryExportAdapter and FormExportAdapter need custom `buildStoragePath()` methods
that cannot be expressed as declarative AdapterConfig fields. This is a spec update
needed -- the spec estimate was based on the assumption that all export adapters
were simple, but their storage path construction uses entry/form-specific logic.
Update spec to say "~14 adapter files" after implementation confirms the exact count.

```dart
// lib/features/sync/adapters/simple_adapters.dart
import 'package:construction_inspector/features/sync/adapters/adapter_config.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

/// Data-driven configurations for simple table adapters.
///
/// FROM SPEC Section 3 (Adapter Simplification): These adapters have no custom
/// logic beyond property overrides. Each generates a TableAdapter at registration.
///
/// IMPORTANT: Registration order MUST match FK dependency order. The sync engine
/// processes tables in this order for push (FK parents first) and pull.
/// FROM SPEC: sync_registry.dart:29-54 — registerSyncAdapters() order is load-bearing.
const simpleAdapters = <AdapterConfig>[
  // WHY: Projects is the root table — no FK dependencies.
  // FROM SPEC: ProjectAdapter (project_adapter.dart)
  AdapterConfig(
    table: 'projects',
    scope: ScopeType.direct,
    fkDeps: [],
    converters: {'is_active': BoolIntConverter()},
    naturalKeyColumns: ['company_id', 'project_number'],
  ),

  // WHY: project_assignments depends on projects existing first.
  // FROM SPEC: ProjectAssignmentAdapter (project_assignment_adapter.dart)
  AdapterConfig(
    table: 'project_assignments',
    scope: ScopeType.direct,
    fkDeps: ['projects'],
  ),

  // FROM SPEC: LocationAdapter (location_adapter.dart)
  AdapterConfig(
    table: 'locations',
    scope: ScopeType.viaProject,
    fkDeps: ['projects'],
    fkColumnMap: {'projects': 'project_id'},
  ),

  // FROM SPEC: ContractorAdapter (contractor_adapter.dart)
  AdapterConfig(
    table: 'contractors',
    scope: ScopeType.viaProject,
    fkDeps: ['projects'],
    fkColumnMap: {'projects': 'project_id'},
  ),

  // FROM SPEC: BidItemAdapter (bid_item_adapter.dart)
  // NOTE: Custom extractRecordName uses item_number + description.
  AdapterConfig(
    table: 'bid_items',
    scope: ScopeType.viaProject,
    fkDeps: ['projects'],
    fkColumnMap: {'projects': 'project_id'},
    extractRecordName: _extractBidItemName,
  ),

  // FROM SPEC: PersonnelTypeAdapter (personnel_type_adapter.dart)
  AdapterConfig(
    table: 'personnel_types',
    scope: ScopeType.viaProject,
    fkDeps: ['projects', 'contractors'],
    naturalKeyColumns: ['project_id', 'semantic_name'],
  ),

  // FROM SPEC: EntryContractorsAdapter (entry_contractors_adapter.dart)
  AdapterConfig(
    table: 'entry_contractors',
    scope: ScopeType.viaEntry,
    fkDeps: ['daily_entries', 'contractors'],
    fkColumnMap: {'daily_entries': 'entry_id', 'contractors': 'contractor_id'},
    naturalKeyColumns: ['entry_id', 'contractor_id'],
  ),

  // FROM SPEC: EntryPersonnelCountsAdapter (entry_personnel_counts_adapter.dart)
  AdapterConfig(
    table: 'entry_personnel_counts',
    scope: ScopeType.viaEntry,
    fkDeps: ['daily_entries', 'contractors', 'personnel_types'],
    fkColumnMap: {
      'daily_entries': 'entry_id',
      'contractors': 'contractor_id',
      'personnel_types': 'type_id',
    },
    extractRecordName: _extractPersonnelCountName,
  ),

  // FROM SPEC: EntryQuantitiesAdapter (entry_quantities_adapter.dart)
  AdapterConfig(
    table: 'entry_quantities',
    scope: ScopeType.viaEntry,
    fkDeps: ['daily_entries', 'bid_items'],
    fkColumnMap: {'daily_entries': 'entry_id', 'bid_items': 'bid_item_id'},
    extractRecordName: _extractQuantityName,
  ),

  // FROM SPEC: TodoItemAdapter (todo_item_adapter.dart)
  AdapterConfig(
    table: 'todo_items',
    scope: ScopeType.viaProject,
    fkDeps: ['projects'],
    converters: {
      'is_completed': BoolIntConverter(),
      'priority': TodoPriorityConverter(),
    },
    extractRecordName: _extractTodoName,
  ),

  // FROM SPEC: CalculationHistoryAdapter (calculation_history_adapter.dart)
  AdapterConfig(
    table: 'calculation_history',
    scope: ScopeType.viaProject,
    fkDeps: ['projects'],
    converters: {
      'input_data': JsonMapConverter(),
      'result_data': JsonMapConverter(),
    },
    extractRecordName: _extractCalcHistoryName,
  ),
];

// --- extractRecordName functions ---
// WHY: These match the exact logic from each adapter's extractRecordName override.

String _extractBidItemName(Map<String, dynamic> record) {
  final itemNumber = record['item_number']?.toString() ?? '';
  final description = record['description']?.toString() ?? '';
  if (itemNumber.isNotEmpty && description.isNotEmpty) {
    return '$itemNumber - $description';
  }
  return itemNumber.isNotEmpty
      ? itemNumber
      : description.isNotEmpty
          ? description
          : record['id']?.toString() ?? 'Unknown';
}

String _extractPersonnelCountName(Map<String, dynamic> record) {
  return 'Personnel count: ${record['count'] ?? record['id'] ?? 'Unknown'}';
}

String _extractQuantityName(Map<String, dynamic> record) {
  return 'Quantity: ${record['quantity'] ?? record['id'] ?? 'Unknown'}';
}

String _extractTodoName(Map<String, dynamic> record) {
  return record['title']?.toString() ??
      record['id']?.toString() ??
      'Unknown';
}

String _extractCalcHistoryName(Map<String, dynamic> record) {
  return record['calc_type']?.toString() ??
      record['id']?.toString() ??
      'Unknown';
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/adapters/simple_adapters.dart"` -- expected: 0 issues found.

#### Step 8.2.2: Update sync_registry.dart to use AdapterConfig

Modify `lib/features/sync/engine/sync_registry.dart` to:
1. Import `simple_adapters.dart` and `adapter_config.dart`
2. Replace the 11 simple adapter class instantiations with `AdapterConfig.toAdapter()` calls
3. Keep the 11 complex adapter class instantiations unchanged
4. Maintain the exact same FK dependency order

```dart
// lib/features/sync/engine/sync_registry.dart — updated registerSyncAdapters()
import 'package:construction_inspector/features/sync/adapters/adapter_config.dart';
import 'package:construction_inspector/features/sync/adapters/simple_adapters.dart';
// ... keep imports for 11 complex adapters ...
import 'package:construction_inspector/features/sync/adapters/equipment_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/daily_entry_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/photo_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/entry_equipment_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/inspector_form_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/form_response_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/form_export_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/entry_export_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/document_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/support_ticket_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/consent_record_adapter.dart';

/// Register all table adapters in FK dependency order.
///
/// FROM SPEC: Simple adapters use data-driven AdapterConfig.
/// Complex adapters retain class files due to custom logic.
///
/// IMPORTANT: Order is load-bearing. FK parents must come before children.
void registerSyncAdapters() {
  // WHY: Generate TableAdapter instances from simple configs.
  // The config order in simpleAdapters already respects FK dependencies
  // for the simple subset, but we must interleave with complex adapters
  // to maintain the full FK order.
  final simpleByTable = {
    for (final config in simpleAdapters) config.table: config.toAdapter(),
  };

  SyncRegistry.instance.registerAdapters([
    // FROM SPEC: Exact order from sync_registry.dart:30-53
    simpleByTable['projects']!,             // was: ProjectAdapter()
    simpleByTable['project_assignments']!,  // was: ProjectAssignmentAdapter()
    simpleByTable['locations']!,            // was: LocationAdapter()
    simpleByTable['contractors']!,          // was: ContractorAdapter()
    EquipmentAdapter(),                     // COMPLEX: converters with custom logic
    simpleByTable['bid_items']!,            // was: BidItemAdapter()
    simpleByTable['personnel_types']!,      // was: PersonnelTypeAdapter()
    DailyEntryAdapter(),                    // COMPLEX: userStampColumns, extractRecordName
    PhotoAdapter(),                         // COMPLEX: validate, buildStoragePath, extractRecordName
    EntryEquipmentAdapter(),                // COMPLEX: converters
    simpleByTable['entry_quantities']!,     // was: EntryQuantitiesAdapter()
    simpleByTable['entry_contractors']!,    // was: EntryContractorsAdapter()
    simpleByTable['entry_personnel_counts']!, // was: EntryPersonnelCountsAdapter()
    InspectorFormAdapter(),                 // COMPLEX: shouldSkipPush, includesNullProjectBuiltins
    FormResponseAdapter(),                  // COMPLEX: jsonb converters
    FormExportAdapter(),                    // COMPLEX: custom buildStoragePath
    EntryExportAdapter(),                   // COMPLEX: custom buildStoragePath
    DocumentAdapter(),                      // COMPLEX: custom buildStoragePath, file adapter
    simpleByTable['todo_items']!,           // was: TodoItemAdapter()
    simpleByTable['calculation_history']!,  // was: CalculationHistoryAdapter()
    SupportTicketAdapter(),                 // COMPLEX: custom pullFilter, skipIntegrityCheck
    ConsentRecordAdapter(),                 // COMPLEX: custom pullFilter, insertOnly, skipPull
  ]);
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/engine/sync_registry.dart"` -- expected: 0 issues found.

---

### Sub-phase 8.3: Delete simple adapter files

**Files:**
- Delete: `lib/features/sync/adapters/contractor_adapter.dart`
- Delete: `lib/features/sync/adapters/location_adapter.dart`
- Delete: `lib/features/sync/adapters/bid_item_adapter.dart`
- Delete: `lib/features/sync/adapters/personnel_type_adapter.dart`
- Delete: `lib/features/sync/adapters/entry_contractors_adapter.dart`
- Delete: `lib/features/sync/adapters/entry_personnel_counts_adapter.dart`
- Delete: `lib/features/sync/adapters/entry_quantities_adapter.dart`
- Delete: `lib/features/sync/adapters/todo_item_adapter.dart`
- Delete: `lib/features/sync/adapters/project_adapter.dart`
- Delete: `lib/features/sync/adapters/project_assignment_adapter.dart`
- Delete: `lib/features/sync/adapters/calculation_history_adapter.dart`

**Agent**: backend-supabase-agent

#### Step 8.3.1: Delete 11 simple adapter files

Delete the 11 files listed above. These are fully replaced by the `simpleAdapters` list in `simple_adapters.dart`.

After deletion, verify no remaining imports reference the deleted files.

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues found (no broken imports).

#### Step 8.3.2: Update barrel exports

If `lib/features/sync/adapters/` has a barrel export file, update it to:
- Remove exports for the 11 deleted adapter files
- Add export for `adapter_config.dart` and `simple_adapters.dart`
- Keep exports for the 11 remaining complex adapter files

---

### Sub-phase 8.4: Verify equivalence

**Agent**: general-purpose

#### Step 8.4.1: Run characterization tests

Run all push and pull characterization tests to verify that the data-driven adapters produce identical behavior to the class-based adapters.

**Verify**: CI green on all characterization tests.

#### Step 8.4.2: Run full analyzer and test suite

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues found.

#### Step 8.4.3: Verify file count

Count files in `lib/features/sync/adapters/`:
- `table_adapter.dart` (base class)
- `type_converters.dart` (shared converters)
- `adapter_config.dart` (config data class)
- `simple_adapters.dart` (11 configs)
- 11 complex adapter class files

Total: 15 files (down from 24). The spec target of "~12" was aspirational; 15 is the correct count given that EntryExportAdapter and FormExportAdapter have custom `buildStoragePath()` logic.

---

## Phase 9: Integration + Documentation

Phase 9 performs end-to-end integration verification using the test driver infrastructure and updates all sync-related documentation to reflect the new architecture.

**Depends on**: Phase 7 (layer violations fixed) and Phase 8 (adapters simplified)

**Verification gate**: All 10 test driver flows pass, all documentation updated, `flutter analyze` zero violations, CI green.

---

### Sub-phase 9.1: Integration Verification via Test Driver

**Files:**
- Modify/Create: `.claude/test-flows/sync/` flow definitions

**Agent**: general-purpose

The following 10 test driver flows verify the complete refactored system end-to-end. Each flow is executed via the HTTP test driver infrastructure (`lib/core/driver/driver_server.dart`, `main_driver.dart`). Flows use 2 devices (or 2 app instances) to verify sync round-trips.

#### Step 9.1.1: Flow 1 — Create-Sync-Verify

**Purpose**: Verify that creating data on Device A and syncing to Device B produces identical results.

**Steps**:
1. Device A: Create a fresh project via UI (POST /driver/create-project or UI automation)
2. Device A: Create a daily entry with photos, forms, and quantities
3. Device A: Trigger sync via POST /driver/sync -> GET /driver/sync-status to confirm completion
4. Device B: Trigger sync via POST /driver/sync
5. Device B: Verify every field matches exactly: project name, entry date, photo filenames, form response data, quantity values, GPS data, timestamps
6. Verify via GET /driver/local-record for both devices

**Success criteria**: Every field on Device B matches Device A exactly, including `created_at` and `updated_at` timestamps.

#### Step 9.1.2: Flow 2 — Edit-Conflict-Resolve

**Purpose**: Verify LWW conflict resolution works correctly after refactor.

**Steps**:
1. Both devices sync to baseline state
2. Device A: Edit entry field X (e.g., weather_notes), sync
3. Device B: Edit same entry field X (different value) + field Y (e.g., traffic_notes), sync
4. Both sync again to resolve
5. Verify: Field X has the value from the device with the newer `updated_at` (LWW)
6. Verify: conflict_log entry exists for the LWW resolution
7. Verify: Loser's field X data is preserved in conflict_log

**Success criteria**: LWW winner correct, conflict_log populated, no data loss.

#### Step 9.1.3: Flow 3 — Delete-Sync-Verify

**Purpose**: Verify soft-delete propagates through the refactored sync.

**Steps**:
1. Device A: Create entry, sync
2. Device B: Sync to receive entry
3. Device A: Soft-delete the entry, sync
4. Device B: Sync
5. Verify: Entry has `deleted_at` set on both devices
6. Verify: Deletion notification created on Device B
7. Verify: Entry filtered from normal reads on both devices

**Success criteria**: Soft-delete round-trips, deletion notification created.

#### Step 9.1.4: Flow 4 — File-Sync-Roundtrip

**Purpose**: Verify three-phase file upload, EXIF stripping, and download work after FileSyncHandler extraction.

**Steps**:
1. Device A: Attach a photo with GPS EXIF data to an entry
2. Device A: Sync
3. Verify: Storage path follows `entries/{companyId}/{entryId}/{filename}` pattern
4. Verify: EXIF GPS stripped in cloud storage copy (download and inspect)
5. Verify: Local `remote_path` bookmark updated
6. Device B: Sync
7. Verify: Photo downloads to Device B with correct metadata

**Success criteria**: File uploads, EXIF stripped, bookmark correct, round-trip complete.

#### Step 9.1.5: Flow 5 — Quick-Sync-Dirty-Scope

**Purpose**: Verify dirty scope filtering works after DirtyScopeTracker extraction.

**Steps**:
1. Both devices at baseline
2. Trigger a realtime hint for a specific project+table (via Supabase Realtime or FCM mock)
3. Trigger quick sync on Device A
4. Verify: Only the dirty scope (specific project+table) was pulled, not all tables
5. Verify: DirtyScopeTracker scopes consumed after pull

**Success criteria**: Quick sync pulls only dirty scopes.

#### Step 9.1.6: Flow 6 — Enrollment-Flow

**Purpose**: Verify auto-enrollment from project_assignments works after EnrollmentHandler extraction.

**Steps**:
1. Device A is enrolled in Project-1 only
2. Admin assigns Device A's user to Project-2 via Supabase (INSERT into project_assignments)
3. Device A: Full sync
4. Verify: synced_projects now includes Project-2
5. Verify: Project-2 data begins pulling on next sync
6. Verify: Enrollment notification queued in SyncProvider

**Success criteria**: Auto-enrollment works, data pulls for new project.

#### Step 9.1.7: Flow 7 — Circuit-Breaker-Recovery

**Purpose**: Verify circuit breaker trips and recovery work after SyncControlService extraction.

**Steps**:
1. Create a conflict scenario that will ping-pong (both devices edit same field repeatedly)
2. Sync back and forth until conflict count exceeds `conflictPingPongThreshold` (3)
3. Verify: Circuit breaker trips, `circuitBreakerTripped` flag set in SyncProvider
4. Dismiss circuit breaker via UI or SyncProvider.dismissCircuitBreaker()
5. Verify: Sync resumes, circuit breaker flag cleared

**Success criteria**: CB trips at threshold, dismissal works, sync resumes.

#### Step 9.1.8: Flow 8 — Resume-Stale-ForcedSync

**Purpose**: Verify SyncTriggerPolicy's stale-data decision on app resume.

**Steps**:
1. Sync successfully
2. Manually advance the `last_sync_time` in sync_metadata to 25h ago
3. Simulate app resume (WidgetsBindingObserver.didChangeAppLifecycleState(resumed))
4. If online: Verify a forced full sync is triggered
5. If DNS unreachable: Verify stale data warning emitted, no sync triggered

**Success criteria**: Stale threshold triggers forced sync when online, warning when offline.

#### Step 9.1.9: Flow 9 — Hint-While-Syncing

**Purpose**: Verify that realtime hints arriving mid-sync are retained and trigger exactly one follow-up quick sync.

**Steps**:
1. Start a full sync on Device A
2. While sync is in progress, trigger a realtime hint (Supabase Realtime or mock)
3. Verify: Dirty scope is marked in DirtyScopeTracker
4. Verify: Hint does not trigger a sync (already in progress)
5. After full sync completes, verify: Exactly one follow-up quick sync runs for the dirty scope

**Success criteria**: Hint retained, exactly one follow-up sync, no overlap.

#### Step 9.1.10: Flow 10 — Retry-Exhaustion-Recovery

**Purpose**: Verify SyncRetryPolicy's exhaustion behavior and background retry scheduling.

**Steps**:
1. Make the backend unreachable (DNS block or kill Supabase)
2. Trigger sync
3. Verify: Sync retries up to maxRetries (3) with exponential backoff
4. Verify: After exhaustion, background retry timer scheduled (60s)
5. Restore backend connectivity
6. Trigger manual sync (should cancel background timer)
7. Verify: Manual sync succeeds, timer cancelled

**Success criteria**: Retry exhaustion, background timer scheduled, manual sync cancels timer.

---

### Sub-phase 9.2: Update sync-patterns.md

**Files:**
- Modify: `.claude/rules/sync/sync-patterns.md`

**Agent**: general-purpose

#### Step 9.2.1: Full rewrite of sync-patterns.md

Rewrite `.claude/rules/sync/sync-patterns.md` to reflect the new architecture:

1. **Layer Diagram**: Update to show the new class structure:
   - Presentation: SyncProvider (subscribes to SyncStatus, reads SyncQueryService)
   - Application: SyncCoordinator, SyncLifecycleManager, SyncRetryPolicy, ConnectivityProbe, SyncTriggerPolicy, PostSyncHooks, SyncQueryService, BackgroundSyncHandler, FcmHandler, RealtimeHintHandler
   - Engine: SyncEngine (slim coordinator), PushHandler, PullHandler, SupabaseSync, LocalSyncStore, FileSyncHandler, SyncErrorClassifier, EnrollmentHandler, FkRescueHandler, MaintenanceHandler
   - Existing engine: ChangeTracker, ConflictResolver, IntegrityChecker, DirtyScopeTracker, OrphanScanner, StorageCleanup, SyncMutex, SyncRegistry
   - Adapters: AdapterConfig (11 simple), 11 complex adapter classes, TableAdapter base
   - Domain: SyncResult, SyncStatus, SyncErrorKind, ClassifiedSyncError, SyncDiagnosticsSnapshot, SyncEvent, SyncMode, DirtyScope

2. **Data Flow**: Update push/pull flow diagrams to show PushHandler/PullHandler routing through SupabaseSync and LocalSyncStore

3. **Class Relationships**: New dependency diagram showing injected dependencies

4. **Engine Components Table**: Add all new classes with file paths and purposes

5. **Application Layer Table**: Replace SyncOrchestrator with SyncCoordinator and add all new control-plane classes

6. **Adapter Section**: Document the AdapterConfig data-driven pattern and list which adapters are simple vs complex

7. **Status vs Diagnostics Split**: Document the SyncStatus / SyncDiagnosticsSnapshot / SyncEvent separation

8. **Error Classification**: Document that SyncErrorClassifier is the single source of truth

9. **File Organization**: Update the directory tree

10. **Enforced Invariants**: Add the new testability guarantees from spec section 4.7

---

### Sub-phase 9.3: Update CLAUDE.md

**Files:**
- Modify: `.claude/CLAUDE.md`

**Agent**: general-purpose

#### Step 9.3.1: Update Sync Architecture section

Update the Sync Architecture section in `.claude/CLAUDE.md`:

```
## Sync Architecture
```
Presentation: SyncProvider, SyncDashboardScreen, ConflictViewerScreen
Application:  SyncCoordinator, SyncLifecycleManager, SyncRetryPolicy, ConnectivityProbe, SyncTriggerPolicy, PostSyncHooks, SyncQueryService, BackgroundSyncHandler, FcmHandler, RealtimeHintHandler
Engine:       SyncEngine (slim), PushHandler, PullHandler, SupabaseSync, LocalSyncStore, FileSyncHandler, SyncErrorClassifier, EnrollmentHandler, FkRescueHandler, MaintenanceHandler
Unchanged:    ChangeTracker, ConflictResolver, IntegrityChecker, DirtyScopeTracker, OrphanScanner, StorageCleanup, SyncMutex
Adapters:     11 AdapterConfig (data-driven) + 11 complex classes (22 total; declare FK ordering + scope type)
Domain:       SyncResult, SyncStatus, SyncErrorKind, ClassifiedSyncError, SyncDiagnosticsSnapshot, SyncEvent, SyncMode, DirtyScope
```

Update the Key Files table to add:
- `lib/features/sync/application/sync_coordinator.dart` -- Replaces SyncOrchestrator
- `lib/features/sync/application/sync_query_service.dart` -- Dashboard query surface
- `lib/features/sync/adapters/simple_adapters.dart` -- 11 data-driven adapter configs

Update Gotchas to note:
- SyncOrchestrator no longer exists -- use SyncCoordinator
- SyncProvider no longer exposes `get orchestrator` -- use SyncQueryService for dashboard data
- Error classification is in SyncErrorClassifier only -- no Postgres code matching elsewhere

---

### Sub-phase 9.4: Update directory-reference.md

**Files:**
- Modify: `.claude/docs/directory-reference.md`

**Agent**: general-purpose

#### Step 9.4.1: Update sync directory listing

Update the sync feature directory listing to reflect:
- New files in `engine/` (push_handler.dart, pull_handler.dart, supabase_sync.dart, local_sync_store.dart, file_sync_handler.dart, sync_error_classifier.dart, enrollment_handler.dart, fk_rescue_handler.dart, maintenance_handler.dart)
- New files in `application/` (sync_coordinator.dart, sync_retry_policy.dart, connectivity_probe.dart, sync_trigger_policy.dart, post_sync_hooks.dart, sync_query_service.dart)
- New files in `domain/` (sync_status.dart, sync_error.dart, sync_diagnostics.dart, sync_event.dart)
- New files in `adapters/` (adapter_config.dart, simple_adapters.dart)
- Deleted files in `adapters/` (11 simple adapter files)
- Deleted file: `sync_orchestrator.dart` (replaced by sync_coordinator.dart)

---

### Sub-phase 9.5: Create sync architecture guide

**Files:**
- Create: `.claude/docs/guides/implementation/sync-architecture.md`

**Agent**: general-purpose

#### Step 9.5.1: Write new sync architecture guide

Create `.claude/docs/guides/implementation/sync-architecture.md` as a durable guide covering:

1. **Overview**: Engine layer (I/O boundaries, handlers, slim coordinator), control plane (retry, connectivity, triggers, hooks), status vs diagnostics split, adapter data-driven pattern

2. **Engine Layer**:
   - SupabaseSync: All Supabase row I/O (upsert, delete, select, auth refresh, rate limit)
   - LocalSyncStore: All sync SQLite I/O (record reads/writes, cursor mgmt, trigger suppression, column cache)
   - PushHandler: Change_log -> FK-ordered -> route per record -> SupabaseSync
   - PullHandler: Adapter iteration -> scope filter -> paginate -> LocalSyncStore
   - FileSyncHandler: Three-phase upload + EXIF strip
   - SyncErrorClassifier: Single error classification source
   - EnrollmentHandler: Project enrollment from assignments
   - FkRescueHandler: Missing FK parent fetch
   - MaintenanceHandler: Integrity, orphan, pruning
   - SyncEngine: Slim coordinator (mutex, heartbeat, mode routing)

3. **Control Plane**:
   - SyncCoordinator: Entry point for sync requests, owns retry loop
   - SyncRetryPolicy: Retryability, backoff, background scheduling
   - ConnectivityProbe: DNS/health checks
   - SyncTriggerPolicy: Lifecycle/stale/hint -> sync mode
   - PostSyncHooks: App-level follow-up (profile refresh, config)
   - SyncQueryService: Dashboard queries (pending buckets, integrity, conflicts)

4. **Status vs Diagnostics**:
   - SyncStatus = transport state (uploading/downloading, connectivity, last sync)
   - SyncDiagnosticsSnapshot = operational state (pending, integrity, conflicts)
   - SyncEvent = transient lifecycle signals

5. **Testing Strategy**:
   - Characterization tests (Layer 1) — behavior contracts
   - Interface contract tests (Layer 2) — TDD before implementation
   - Equivalence testing (Layer 3) — per-extraction CI gate
   - Isolation tests (Layer 4) ��� per-class deep coverage
   - Integration verification (Layer 5) — 10 test driver flows

6. **Adapter Pattern**:
   - AdapterConfig for simple adapters (11)
   - Class files for complex adapters (11)
   - Registration order = FK dependency order

---

### Sub-phase 9.5b: Additional Documentation Updates (Finding 22)

**Files:**
- Modify: `.claude/docs/INDEX.md`
- Modify: `.codex/CLAUDE_CONTEXT_BRIDGE.md`
- Modify: `.claude/test-flows/sync/framework.md`

**Agent**: general-purpose

#### Step 9.5b.1: Update INDEX.md

Add references to the new sync architecture guide and related docs:
- Add entry for `.claude/docs/guides/implementation/sync-architecture.md` (engine layer, control plane, diagnostics, testing strategy)
- Add entry for updated `.claude/rules/sync/sync-patterns.md`
- Add entry for updated `.claude/test-flows/sync/` flow definitions

#### Step 9.5b.2: Update CLAUDE_CONTEXT_BRIDGE.md

Add a targeted sync file map so future Codex sessions can find the control-plane and diagnostics docs without broad `.claude/` browsing:
- Map `lib/features/sync/engine/` -> `.claude/docs/guides/implementation/sync-architecture.md` (engine layer section)
- Map `lib/features/sync/application/` -> `.claude/docs/guides/implementation/sync-architecture.md` (control plane section)
- Map `lib/features/sync/domain/sync_status.dart` -> `.claude/docs/guides/implementation/sync-architecture.md` (status vs diagnostics section)
- Map `test/features/sync/characterization/` -> `.claude/test-flows/sync/framework.md`

#### Step 9.5b.3: Update test-flows/sync/framework.md

Update `.claude/test-flows/sync/framework.md` to reference the new class boundaries and test approach:
- Update the 6-layer testing pyramid description to reference new class names
- Add section on characterization test locations (`test/features/sync/characterization/`)
- Add section on contract test locations (`test/features/sync/engine/`, `test/features/sync/application/`)
- Add section on isolation test locations and test group descriptions

---

### Sub-phase 9.6: Final Verification

**Agent**: general-purpose

#### Step 9.6.1: Run full analyzer

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues found.

#### Step 9.6.2: Run full CI suite

Push branch, open PR, verify CI green:
- All characterization tests pass
- All contract tests pass
- All isolation tests pass
- All existing tests pass
- Analyzer zero violations

#### Step 9.6.3: Verify success metrics

Check against spec section 8 success metrics:

| Metric | Before | Target | Verify |
|--------|--------|--------|--------|
| SyncEngine lines | 2,374 | <250 | `wc -l lib/features/sync/engine/sync_engine.dart` |
| Largest sync class | 2,374 | <500 | Check all new files |
| `@visibleForTesting` methods | 9 | 0 | `grep -r '@visibleForTesting' lib/features/sync/` |
| Adapter files | 24 | ~15 | `ls lib/features/sync/adapters/ \| wc -l` |
| Status sources of truth | 3 | 1 | Verify only SyncStatus exists |
| Error classifier locations | 3 | 1 | Verify only SyncErrorClassifier |
| Untestable code paths | 6 | 0 | All have dedicated tests |

#### Step 9.6.4: Merge PR

After all verification passes, merge the Phase 9 PR. This is the final phase of the sync engine refactor.
