# Section C1: Test Infrastructure, Phase 0 & Phase 1 -- Implementation Plan

**Date**: 2026-03-05
**Scope**: Test infrastructure setup, Phase 0 (Schema + Security) verification, Phase 1 (Change Tracking Foundation)
**Parent Plan**: `.claude/plans/2026-03-04-sync-rewrite-and-settings-redesign.md`
**Dependencies**: Section B (Schema SQL) provides the Supabase migration SQL. Section A provides engine architecture context.

---

## Step 1: Test Infrastructure Setup

This step creates the shared test utilities that all subsequent sync tests depend on. Every file here must be created before any Phase 1 or Phase 2 test can run.

### 1.1 SQLite Test Helper

**File**: `test/helpers/sync/sqlite_test_helper.dart`
**Action**: Create
**Purpose**: Provides an in-memory SQLite database with the full v30 schema, all 48 triggers installed, and sync infrastructure tables. Every sync-related test file imports this helper.

```dart
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/core/database/schema/schema.dart';

/// Creates an in-memory SQLite database with full v30 schema + triggers.
///
/// Usage:
///   final db = await SqliteTestHelper.createDatabase();
///   addTearDown(() => db.close());
class SqliteTestHelper {
  /// Create a fresh in-memory database with full schema and triggers.
  static Future<Database> createDatabase() async {
    sqfliteFfiInit();
    final db = await databaseFactoryFfi.openDatabase(
      inMemoryDatabasePath,
      options: OpenDatabaseOptions(
        version: 30,
        onCreate: _onCreate,
        onConfigure: (db) async {
          await db.rawQuery('PRAGMA foreign_keys=ON');
        },
      ),
    );
    return db;
  }

  static Future<void> _onCreate(Database db, int version) async {
    // --- Core tables ---
    await db.execute(CoreTables.createCompaniesTable);
    await db.execute(CoreTables.createUserProfilesTable);
    await db.execute(CoreTables.createCompanyJoinRequestsTable);
    await db.execute(CoreTables.createProjectsTable);
    await db.execute(CoreTables.createLocationsTable);

    // --- Contractor tables ---
    await db.execute(ContractorTables.createContractorsTable);
    await db.execute(ContractorTables.createEquipmentTable);

    // --- Quantity tables ---
    await db.execute(QuantityTables.createBidItemsTable);

    // --- Entry tables ---
    await db.execute(EntryTables.createDailyEntriesTable);
    await db.execute(EntryTables.createEntryContractorsTable);
    await db.execute(EntryTables.createEntryEquipmentTable);

    // --- Personnel tables ---
    await db.execute(PersonnelTables.createPersonnelTypesTable);
    await db.execute(PersonnelTables.createEntryPersonnelCountsTable);
    await db.execute(PersonnelTables.createEntryPersonnelTable);

    // --- Quantity junction ---
    await db.execute(QuantityTables.createEntryQuantitiesTable);

    // --- Photo tables ---
    await db.execute(PhotoTables.createPhotosTable);

    // --- Sync tables (legacy + new) ---
    await db.execute(SyncTables.createSyncQueueTable);
    await db.execute(SyncTables.createDeletionNotificationsTable);

    // --- Toolbox tables ---
    await db.execute(ToolboxTables.createInspectorFormsTable);
    await db.execute(ToolboxTables.createFormResponsesTable);
    await db.execute(ToolboxTables.createTodoItemsTable);
    await db.execute(ToolboxTables.createCalculationHistoryTable);

    // --- Extraction metrics tables ---
    await db.execute(ExtractionTables.createExtractionMetricsTable);
    await db.execute(ExtractionTables.createStageMetricsTable);

    // --- Sync metadata ---
    await db.execute('''
      CREATE TABLE IF NOT EXISTS sync_metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      )
    ''');

    // --- v30 new tables ---
    await db.execute('''
      CREATE TABLE IF NOT EXISTS sync_control (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      )
    ''');
    await db.execute(
      "INSERT OR IGNORE INTO sync_control (key, value) VALUES ('pulling', '0')",
    );

    await db.execute('''
      CREATE TABLE IF NOT EXISTS change_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL,
        record_id TEXT NOT NULL,
        operation TEXT NOT NULL,
        changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
        processed INTEGER NOT NULL DEFAULT 0,
        error_message TEXT,
        retry_count INTEGER NOT NULL DEFAULT 0,
        metadata TEXT
      )
    ''');
    await db.execute(
      'CREATE INDEX IF NOT EXISTS idx_change_log_unprocessed ON change_log(processed, table_name)',
    );

    await db.execute('''
      CREATE TABLE IF NOT EXISTS conflict_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL,
        record_id TEXT NOT NULL,
        winner TEXT NOT NULL,
        lost_data TEXT NOT NULL,
        detected_at TEXT NOT NULL,
        dismissed_at TEXT,
        expires_at TEXT NOT NULL
      )
    ''');
    await db.execute(
      'CREATE INDEX IF NOT EXISTS idx_conflict_log_expires ON conflict_log(expires_at)',
    );

    await db.execute('''
      CREATE TABLE IF NOT EXISTS sync_lock (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        locked_at TEXT NOT NULL,
        locked_by TEXT NOT NULL
      )
    ''');

    await db.execute('''
      CREATE TABLE IF NOT EXISTS synced_projects (
        project_id TEXT PRIMARY KEY,
        synced_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
      )
    ''');

    await db.execute('''
      CREATE TABLE IF NOT EXISTS user_certifications (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        cert_type TEXT NOT NULL,
        cert_number TEXT NOT NULL,
        expiry_date TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
        UNIQUE(user_id, cert_type)
      )
    ''');

    // --- All indexes ---
    for (final index in CoreTables.indexes) {
      await db.execute(index);
    }
    for (final index in ContractorTables.indexes) {
      await db.execute(index);
    }
    for (final index in PersonnelTables.indexes) {
      await db.execute(index);
    }
    for (final index in EntryTables.indexes) {
      await db.execute(index);
    }
    for (final index in QuantityTables.indexes) {
      await db.execute(index);
    }
    for (final index in PhotoTables.indexes) {
      await db.execute(index);
    }
    for (final index in SyncTables.indexes) {
      await db.execute(index);
    }
    for (final index in ToolboxTables.indexes) {
      await db.execute(index);
    }
    for (final index in ExtractionTables.indexes) {
      await db.execute(index);
    }
    await db.execute(
      'CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_company_number ON projects(company_id, project_number)',
    );

    // --- Install all 48 triggers ---
    await _installTriggers(db);
  }

  /// Install all 48 change tracking triggers (16 tables x 3 operations).
  static Future<void> _installTriggers(Database db) async {
    const tables = [
      'projects',
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

    for (final table in tables) {
      await db.execute('''
        CREATE TRIGGER IF NOT EXISTS trg_${table}_insert AFTER INSERT ON $table
        WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
        BEGIN
          INSERT INTO change_log (table_name, record_id, operation)
          VALUES ('$table', NEW.id, 'insert');
        END
      ''');

      await db.execute('''
        CREATE TRIGGER IF NOT EXISTS trg_${table}_update AFTER UPDATE ON $table
        WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
        BEGIN
          INSERT INTO change_log (table_name, record_id, operation)
          VALUES ('$table', NEW.id, 'update');
        END
      ''');

      await db.execute('''
        CREATE TRIGGER IF NOT EXISTS trg_${table}_delete AFTER DELETE ON $table
        WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
        BEGIN
          INSERT INTO change_log (table_name, record_id, operation)
          VALUES ('$table', OLD.id, 'delete');
        END
      ''');
    }
  }

  /// Suppress triggers by setting sync_control.pulling = '1'.
  /// Call this before inserting test seed data that should not create change_log entries.
  static Future<void> suppressTriggers(Database db) async {
    await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
  }

  /// Re-enable triggers by resetting sync_control.pulling = '0'.
  static Future<void> enableTriggers(Database db) async {
    await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
  }

  /// Clear all change_log entries. Useful between test cases.
  static Future<void> clearChangeLog(Database db) async {
    await db.execute('DELETE FROM change_log');
  }

  /// Get all unprocessed change_log entries for a specific table.
  static Future<List<Map<String, dynamic>>> getChangeLogEntries(
    Database db,
    String tableName,
  ) async {
    return db.query(
      'change_log',
      where: 'table_name = ? AND processed = 0',
      whereArgs: [tableName],
      orderBy: 'id ASC',
    );
  }

  /// Get total count of unprocessed change_log entries.
  static Future<int> getUnprocessedCount(Database db) async {
    final result = await db.rawQuery(
      'SELECT COUNT(*) as cnt FROM change_log WHERE processed = 0',
    );
    return result.first['cnt'] as int;
  }
}
```

**Key design decisions**:
- Uses `sqflite_common_ffi` with `inMemoryDatabasePath` for fast, isolated tests
- Mirrors `database_service.dart` `_onCreate` exactly, plus v30 additions
- Trigger installation via loop over the 16 synced tables (matches the explicit list from the plan)
- Provides `suppressTriggers`/`enableTriggers` for seeding test data without polluting change_log
- Each test creates its own database instance -- no shared state between tests

### 1.2 Mock Supabase Client

**File**: `test/helpers/sync/mock_supabase_client.dart`
**Action**: Create
**Purpose**: Provides a mock Supabase client that simulates upsert, select, delete, and RPC calls. Used by adapter and engine integration tests.

```dart
import 'package:mocktail/mocktail.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class MockSupabaseClient extends Mock implements SupabaseClient {}
class MockSupabaseQueryBuilder extends Mock implements SupabaseQueryBuilder {}
class MockPostgrestFilterBuilder extends Mock implements PostgrestFilterBuilder {}
class MockPostgrestResponse extends Mock implements PostgrestResponse {}
class MockGoTrueClient extends Mock implements GoTrueClient {}
class MockSupabaseStorageClient extends Mock implements SupabaseStorageClient {}
class MockStorageFileApi extends Mock implements StorageFileApi {}

/// Configures a [MockSupabaseClient] to return mock query builders
/// for a given table name.
///
/// Usage:
///   final client = MockSupabaseClient();
///   final queryBuilder = setupMockTable(client, 'projects');
///   when(() => queryBuilder.upsert(any())).thenAnswer((_) async => ...);
MockSupabaseQueryBuilder setupMockTable(
  MockSupabaseClient client,
  String tableName,
) {
  final queryBuilder = MockSupabaseQueryBuilder();
  when(() => client.from(tableName)).thenReturn(queryBuilder);
  return queryBuilder;
}

/// Sets up a mock auth client with a fixed user ID.
MockGoTrueClient setupMockAuth(
  MockSupabaseClient client, {
  String userId = 'test-user-id',
  String email = 'test@example.com',
}) {
  final auth = MockGoTrueClient();
  when(() => client.auth).thenReturn(auth);
  // Additional auth mock setup as needed per test
  return auth;
}

/// Sets up mock storage client for photo adapter tests.
MockStorageFileApi setupMockStorage(
  MockSupabaseClient client, {
  String bucketName = 'entry-photos',
}) {
  final storage = MockSupabaseStorageClient();
  final fileApi = MockStorageFileApi();
  when(() => client.storage).thenReturn(storage);
  when(() => storage.from(bucketName)).thenReturn(fileApi);
  return fileApi;
}
```

**Note**: `mocktail` is already a dev dependency in the project (verify in `pubspec.yaml`). If not present, add: `mocktail: ^1.0.4` under `dev_dependencies`.

### 1.3 Test Data Factory

**File**: `test/helpers/sync/sync_test_data.dart`
**Action**: Create
**Purpose**: Factory methods that produce valid `Map<String, dynamic>` rows for all 16 synced tables, suitable for direct SQLite insertion. Extends the existing `TestData` class in `test/helpers/test_helpers.dart` with raw map factories needed by trigger and adapter tests.

```dart
import 'package:uuid/uuid.dart';

/// Raw map factories for all 16 synced tables.
///
/// These produce maps suitable for `db.insert(tableName, map)` calls.
/// Each factory generates valid data with all required columns populated.
/// Optional columns default to null unless overridden.
class SyncTestData {
  static const _uuid = Uuid();
  static String _ts() =>
      DateTime.now().toUtc().toIso8601String();

  // --- 1. projects ---
  static Map<String, dynamic> projectMap({
    String? id,
    String name = 'Test Project',
    String projectNumber = 'TP-001',
    String? companyId = 'test-company',
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'name': name,
    'project_number': projectNumber,
    'client_name': null,
    'description': null,
    'created_at': _ts(),
    'updated_at': _ts(),
    'is_active': 1,
    'mode': 'localAgency',
    'mdot_contract_id': null,
    'mdot_project_code': null,
    'mdot_county': null,
    'mdot_district': null,
    'control_section_id': null,
    'route_street': null,
    'construction_eng': null,
    'company_id': companyId,
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 2. locations ---
  static Map<String, dynamic> locationMap({
    String? id,
    required String projectId,
    String name = 'Test Location',
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'project_id': projectId,
    'name': name,
    'description': null,
    'latitude': null,
    'longitude': null,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 3. contractors ---
  static Map<String, dynamic> contractorMap({
    String? id,
    required String projectId,
    String name = 'Test Contractor',
    String type = 'sub',
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'project_id': projectId,
    'name': name,
    'type': type,
    'contact_name': null,
    'phone': null,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 4. equipment ---
  static Map<String, dynamic> equipmentMap({
    String? id,
    required String contractorId,
    String name = 'Test Equipment',
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'contractor_id': contractorId,
    'name': name,
    'description': null,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 5. bid_items ---
  static Map<String, dynamic> bidItemMap({
    String? id,
    required String projectId,
    String itemNumber = '1000',
    String description = 'Test Item',
    String unit = 'EA',
    double bidQuantity = 100.0,
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'project_id': projectId,
    'item_number': itemNumber,
    'description': description,
    'unit': unit,
    'bid_quantity': bidQuantity,
    'unit_price': null,
    'bid_amount': null,
    'measurement_payment': null,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 6. personnel_types ---
  static Map<String, dynamic> personnelTypeMap({
    String? id,
    required String projectId,
    String? contractorId,
    String name = 'Foreman',
    String? shortCode = 'FM',
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'project_id': projectId,
    'contractor_id': contractorId,
    'name': name,
    'short_code': shortCode,
    'sort_order': 0,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 7. daily_entries ---
  static Map<String, dynamic> dailyEntryMap({
    String? id,
    required String projectId,
    String? locationId,
    String? date,
    String status = 'draft',
    String syncStatus = 'pending',
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'project_id': projectId,
    'location_id': locationId,
    'date': date ?? DateTime.now().toIso8601String().split('T').first,
    'weather': null,
    'temp_low': null,
    'temp_high': null,
    'activities': null,
    'site_safety': null,
    'sesc_measures': null,
    'traffic_control': null,
    'visitors': null,
    'extras_overruns': null,
    'signature': null,
    'signed_at': null,
    'status': status,
    'submitted_at': null,
    'revision_number': 0,
    'created_at': _ts(),
    'updated_at': _ts(),
    'sync_status': syncStatus,
    'created_by_user_id': createdByUserId,
    'updated_by_user_id': null,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 8. photos ---
  static Map<String, dynamic> photoMap({
    String? id,
    required String entryId,
    required String projectId,
    String filePath = '/test/photo.jpg',
    String filename = 'photo.jpg',
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'entry_id': entryId,
    'project_id': projectId,
    'file_path': filePath,
    'filename': filename,
    'remote_path': null,
    'notes': null,
    'caption': null,
    'location_id': null,
    'latitude': null,
    'longitude': null,
    'captured_at': _ts(),
    'sync_status': 'pending',
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 9. entry_equipment ---
  static Map<String, dynamic> entryEquipmentMap({
    String? id,
    required String entryId,
    required String equipmentId,
    int wasUsed = 1,
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'entry_id': entryId,
    'equipment_id': equipmentId,
    'was_used': wasUsed,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 10. entry_quantities ---
  static Map<String, dynamic> entryQuantityMap({
    String? id,
    required String entryId,
    required String bidItemId,
    double quantity = 10.0,
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'entry_id': entryId,
    'bid_item_id': bidItemId,
    'quantity': quantity,
    'notes': null,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 11. entry_contractors ---
  static Map<String, dynamic> entryContractorMap({
    String? id,
    required String entryId,
    required String contractorId,
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'entry_id': entryId,
    'contractor_id': contractorId,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 12. entry_personnel_counts ---
  static Map<String, dynamic> entryPersonnelCountMap({
    String? id,
    required String entryId,
    required String contractorId,
    required String typeId,
    int count = 3,
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'entry_id': entryId,
    'contractor_id': contractorId,
    'type_id': typeId,
    'count': count,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 13. inspector_forms ---
  static Map<String, dynamic> inspectorFormMap({
    String? id,
    required String projectId,
    String name = 'MDOT 0582B',
    String templatePath = 'assets/forms/mdot_0582b.pdf',
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'project_id': projectId,
    'name': name,
    'template_path': templatePath,
    'field_definitions': null,
    'parsing_keywords': null,
    'table_row_config': null,
    'is_builtin': 0,
    'template_source': 'asset',
    'template_hash': null,
    'template_version': 1,
    'template_field_count': null,
    'template_bytes': null,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 14. form_responses ---
  static Map<String, dynamic> formResponseMap({
    String? id,
    String formType = 'mdot_0582b',
    String? formId,
    String? entryId,
    required String projectId,
    String responseData = '{}',
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'form_type': formType,
    'form_id': formId,
    'entry_id': entryId,
    'project_id': projectId,
    'header_data': '{}',
    'response_data': responseData,
    'table_rows': null,
    'response_metadata': null,
    'status': 'open',
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 15. todo_items ---
  static Map<String, dynamic> todoItemMap({
    String? id,
    required String projectId,
    String? entryId,
    String title = 'Test Todo',
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'project_id': projectId,
    'entry_id': entryId,
    'title': title,
    'description': null,
    'is_completed': 0,
    'due_date': null,
    'priority': 0,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 16. calculation_history ---
  static Map<String, dynamic> calculationHistoryMap({
    String? id,
    required String projectId,
    String? entryId,
    String calcType = 'area',
    String inputData = '{"length": 10, "width": 5}',
    String resultData = '{"area": 50}',
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'project_id': projectId,
    'entry_id': entryId,
    'calc_type': calcType,
    'input_data': inputData,
    'result_data': resultData,
    'notes': null,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  /// Seed a complete FK graph (company -> project -> location -> entry)
  /// with triggers suppressed so change_log stays clean.
  /// Returns a map of entity IDs for downstream use.
  static Future<Map<String, String>> seedFkGraph(Database db) async {
    await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");

    final companyId = _uuid.v4();
    final projectId = _uuid.v4();
    final locationId = _uuid.v4();
    final entryId = _uuid.v4();
    final contractorId = _uuid.v4();
    final equipmentId = _uuid.v4();
    final bidItemId = _uuid.v4();
    final personnelTypeId = _uuid.v4();

    await db.insert('companies', {
      'id': companyId, 'name': 'Test Co',
      'created_at': _ts(), 'updated_at': _ts(),
    });
    await db.insert('projects', projectMap(
      id: projectId, companyId: companyId,
    ));
    await db.insert('locations', locationMap(
      id: locationId, projectId: projectId,
    ));
    await db.insert('daily_entries', dailyEntryMap(
      id: entryId, projectId: projectId, locationId: locationId,
    ));
    await db.insert('contractors', contractorMap(
      id: contractorId, projectId: projectId,
    ));
    await db.insert('equipment', equipmentMap(
      id: equipmentId, contractorId: contractorId,
    ));
    await db.insert('bid_items', bidItemMap(
      id: bidItemId, projectId: projectId,
    ));
    await db.insert('personnel_types', personnelTypeMap(
      id: personnelTypeId, projectId: projectId,
    ));

    await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");

    return {
      'companyId': companyId,
      'projectId': projectId,
      'locationId': locationId,
      'entryId': entryId,
      'contractorId': contractorId,
      'equipmentId': equipmentId,
      'bidItemId': bidItemId,
      'personnelTypeId': personnelTypeId,
    };
  }
}
```

**Note**: The `seedFkGraph` helper requires importing `sqflite_common_ffi` for the `Database` type. Add the import at the top of the file.

### 1.4 Adapter Test Harness Base Class

**File**: `test/helpers/sync/adapter_test_harness.dart`
**Action**: Create (Phase 2 will use this, but define the base now)
**Purpose**: Base class that all 16 adapter test files extend. Provides boilerplate for DB setup, mock Supabase, and standard test assertions.

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'sqlite_test_helper.dart';
import 'mock_supabase_client.dart';
import 'sync_test_data.dart';

/// Base harness for adapter unit tests.
///
/// Subclass this and implement [createAdapter], [tableName],
/// [createTestRecord], and [expectedRemoteKeys].
///
/// Provides:
/// - Fresh in-memory DB per test group
/// - Mock Supabase client
/// - Seeded FK graph
/// - Standard test assertions for convertForRemote/convertForLocal/validate
abstract class AdapterTestHarness {
  late Database db;
  late MockSupabaseClient mockClient;
  late Map<String, String> seedIds;

  /// The table name this adapter manages (e.g., 'projects').
  String get tableName;

  /// Create a test record map for this table, using IDs from seedIds.
  Map<String, dynamic> createTestRecord(Map<String, String> seedIds);

  /// Expected keys in the remote (Supabase) payload after convertForRemote.
  Set<String> get expectedRemoteKeys;

  /// Keys that should be stripped from remote payload (local-only columns).
  Set<String> get strippedLocalKeys => {'sync_status'};

  Future<void> setUp() async {
    db = await SqliteTestHelper.createDatabase();
    mockClient = MockSupabaseClient();
    seedIds = await SyncTestData.seedFkGraph(db);
  }

  Future<void> tearDown() async {
    await db.close();
  }

  /// Insert a record into the local table and return its ID.
  Future<String> insertLocal(Map<String, dynamic> record) async {
    await db.insert(tableName, record);
    return record['id'] as String;
  }

  /// Assert that change_log has exactly [count] unprocessed entries for this table.
  Future<void> expectChangeLogCount(int count) async {
    final entries = await SqliteTestHelper.getChangeLogEntries(db, tableName);
    expect(entries.length, count,
        reason: 'Expected $count change_log entries for $tableName');
  }

  /// Assert that a change_log entry exists with the given operation and record_id.
  Future<void> expectChangeLogEntry({
    required String recordId,
    required String operation,
  }) async {
    final entries = await db.query(
      'change_log',
      where: 'table_name = ? AND record_id = ? AND operation = ? AND processed = 0',
      whereArgs: [tableName, recordId, operation],
    );
    expect(entries, isNotEmpty,
        reason: 'Expected change_log entry: $tableName/$recordId/$operation');
  }
}
```

### 1.5 Barrel Export

**File**: `test/helpers/sync/sync_test_helpers.dart`
**Action**: Create
**Purpose**: Single import for all sync test utilities.

```dart
export 'sqlite_test_helper.dart';
export 'mock_supabase_client.dart';
export 'sync_test_data.dart';
export 'adapter_test_harness.dart';
```

### 1.6 Verification

After creating all 5 files above, verify:
- [ ] `pwsh -Command "flutter test test/helpers/sync/"` -- should find no tests (helpers only) but should compile
- [ ] Import `test/helpers/sync/sync_test_helpers.dart` in a scratch test to confirm it resolves

---

## Step 2: Phase 0 -- Schema + Security (Supabase)

**Agent**: `backend-supabase-agent`
**Prerequisite**: None. Phase 0 is the first implementation step.
**SQL Source**: Section B (`section-b-schema-security.md`) Step 1 contains the complete SQL migration file. Do NOT duplicate SQL here -- reference Section B for the actual DDL.

Phase 0 deploys the Supabase migration that fixes all server-side schema gaps and security issues. Each sub-step below corresponds to a PART in the Section B SQL file, deployed as a single atomic migration.

### 2.1 Pre-flight Checks

Before running the migration, manually verify these prerequisites:

- [ ] **PREREQ-1**: Verify `update_updated_at_column()` function exists in Supabase.
  - Query: `SELECT proname FROM pg_proc WHERE proname = 'update_updated_at_column';`
  - This function is used by the new `entry_contractors` and `entry_personnel_counts` triggers (Section B PART 2).
  - If missing: CREATE it first (should already exist from `multi_tenant_foundation.sql`).

- [ ] **PREREQ-2**: Verify `equipment` table already has `deleted_at`/`deleted_by` columns.
  - Query: `SELECT column_name FROM information_schema.columns WHERE table_name = 'equipment' AND column_name IN ('deleted_at', 'deleted_by');`
  - Required by `get_table_integrity()` RPC which filters `AND deleted_at IS NULL` on all 16 tables.

- [ ] **PREREQ-3**: Verify `get_my_company_id()` function exists.
  - Query: `SELECT proname FROM pg_proc WHERE proname = 'get_my_company_id';`
  - Used by storage RLS policies and `get_table_integrity()` RPC.

- [ ] **PREREQ-4**: Verify `is_viewer()` function exists.
  - Query: `SELECT proname FROM pg_proc WHERE proname = 'is_viewer';`
  - Used by storage RLS insert/delete policies.

- [ ] **PREREQ-5**: Run the Storage RLS diagnostic query BEFORE applying the fix, to confirm path structure:
  ```sql
  SELECT name,
         (storage.foldername(name))[1] AS idx1,
         (storage.foldername(name))[2] AS idx2,
         (storage.foldername(name))[3] AS idx3
  FROM storage.objects
  WHERE bucket_id = 'entry-photos'
  LIMIT 5;
  ```
  - Expected: `[1]='entries'`, `[2]=companyId`, `[3]=entryId`

### 2.2 Migration Deployment

**File**: `supabase/migrations/20260305000000_schema_alignment_and_security.sql`
**Action**: Create (content defined in Section B Step 1.2)

Deploy the single migration file containing all 14 PARTs in order:

| Step | Section B PART | Gap/Decision | Description |
|------|---------------|--------------|-------------|
| 2.2.1 | PART 0 | NEW-1 (CRITICAL) | Fix Storage RLS -- change `[1]` to `[2]` in all 3 policies |
| 2.2.2 | PART 1 | GAP-9 | Add `deleted_at`/`deleted_by` to `inspector_forms` on Supabase |
| 2.2.3 | PART 2 | GAP-10 | Add `updated_at` triggers on `entry_contractors` and `entry_personnel_counts` |
| 2.2.4 | PART 3 | ADV-31 | Backfill + NOT NULL on `calculation_history.updated_at` |
| 2.2.5 | PART 4 | ADV-33 | Drop NOT NULL + FK on `form_responses.form_id` (idempotent) |
| 2.2.6 | PART 5 | ADV-9 | Backfill + NOT NULL on `project_id` for 3 toolbox tables |
| 2.2.7 | PART 6 | NEW-7 + ADV-25 | Create `is_approved_admin()` + rewrite all 6 admin RPCs |
| 2.2.8 | PART 7 | NEW-6 + ADV-24 | Create `lock_created_by()` trigger on all 16 tables |
| 2.2.9 | PART 8 | ADV-2 | Create `enforce_insert_updated_at()` trigger on all 16 tables |
| 2.2.10 | PART 9 | ADV-15 | Create `stamp_updated_by()` trigger on `daily_entries` |
| 2.2.11 | PART 10 | ADV-22/23 | Create `get_table_integrity()` RPC with id_checksum |
| 2.2.12 | PART 11 | Decision 12 | Add profile expansion columns to `user_profiles` |
| 2.2.13 | PART 12 | Decision 12 | Create `user_certifications` table with RLS |
| 2.2.14 | PART 13 | Decision 12 | Migrate `cert_number` data to `user_certifications` |
| 2.2.15 | PART 14 | Security | Fix `enforce_created_by()` to add `SET search_path = public` |

**Deployment command**:
```bash
supabase db push
```
Or apply via Supabase Dashboard SQL editor if not using CLI.

### 2.3 Config Change

**File**: `supabase/config.toml`
**Action**: Modify (Section B Step 2)
**Change**: Set `secure_password_change = true` (GAP-19)

### 2.4 Interim Purge Handler

**File**: `lib/services/sync_service.dart`
**Action**: Modify (Section B Step 8)
**Change**: Add `case 'purge':` to `_processSyncQueueItem` (GAP-3)
**Note**: This is a temporary fix using the old sync service. The new engine in Phase 2+ replaces this entirely.

### 2.5 Phase 0 Verification Tests

These are manual verification tests run against the live Supabase instance after migration deployment. They are NOT automated unit tests (Supabase server-side behavior cannot be unit-tested locally).

#### 2.5.1 Storage RLS Verification (NEW-1)

**Test**: Upload a photo via the app
- [ ] Sign in as an approved inspector
- [ ] Create a daily entry, attach a photo
- [ ] Trigger sync
- [ ] **PASS**: Photo uploads successfully (no RLS error)
- [ ] **VERIFY**: Check storage.objects -- file path has correct companyId at `[2]`

#### 2.5.2 Admin RPC Status Check (NEW-7)

**Test**: Deactivated admin calls `approve_join_request`
- [ ] Set a test admin's status to `'deactivated'` in `user_profiles`
- [ ] Call `approve_join_request` as that admin
- [ ] **PASS**: RPC raises `'Not an approved admin'` exception
- [ ] Reset admin status back to `'approved'`

#### 2.5.3 lock_created_by Trigger (NEW-6)

**Test 1**: UPDATE `created_by_user_id` on record with existing value
- [ ] Find a record with non-NULL `created_by_user_id`
- [ ] `UPDATE projects SET created_by_user_id = 'attacker-id' WHERE id = ?`
- [ ] **PASS**: `created_by_user_id` remains the original value (trigger preserves it)

**Test 2**: UPDATE `created_by_user_id` on legacy record (NULL)
- [ ] Find or create a record with `created_by_user_id = NULL`
- [ ] `UPDATE projects SET created_by_user_id = 'new-user-id' WHERE id = ?`
- [ ] **PASS**: `created_by_user_id` is now set to `'new-user-id'` (first-time stamping allowed)

**Test 3**: UPDATE `created_by_user_id` to NULL
- [ ] `UPDATE projects SET created_by_user_id = NULL WHERE id = ?`
- [ ] **PASS**: `created_by_user_id` retains old value (COALESCE prevents erasure)

#### 2.5.4 enforce_insert_updated_at Trigger (ADV-2)

**Test**: INSERT with client-supplied `updated_at = '2099-01-01'`
- [ ] `INSERT INTO projects (id, name, ..., updated_at) VALUES (..., '2099-01-01T00:00:00')`
- [ ] `SELECT updated_at FROM projects WHERE id = ?`
- [ ] **PASS**: `updated_at` is approximately `NOW()`, not `2099-01-01`

#### 2.5.5 updated_at Triggers (GAP-10)

**Test**: Verify trigger fires on entry_contractors and entry_personnel_counts
- [ ] `UPDATE entry_contractors SET contractor_id = contractor_id WHERE id = ?`
- [ ] **PASS**: `updated_at` value changed to approximately `NOW()`
- [ ] Repeat for `entry_personnel_counts`

#### 2.5.6 inspector_forms Soft-Delete (GAP-9)

**Test**: Verify columns exist
- [ ] `SELECT deleted_at, deleted_by FROM inspector_forms LIMIT 1`
- [ ] **PASS**: Query succeeds (columns exist)

#### 2.5.7 calculation_history NOT NULL (ADV-31)

**Test**: Verify constraint
- [ ] `SELECT COUNT(*) FROM calculation_history WHERE updated_at IS NULL`
- [ ] **PASS**: Count = 0
- [ ] `INSERT INTO calculation_history (id, ...) VALUES (...) /* omit updated_at */`
- [ ] **PASS**: Row has `updated_at = NOW()` (default applied)

#### 2.5.8 project_id NOT NULL (ADV-9)

**Test**: Verify constraint on all 3 tables
- [ ] `INSERT INTO inspector_forms (id, name, ...) VALUES (...) /* project_id = NULL */`
- [ ] **PASS**: INSERT fails with NOT NULL violation
- [ ] Repeat for `todo_items` and `calculation_history`

#### 2.5.9 user_certifications Table (Decision 12)

**Test 1**: Table exists and UNIQUE constraint works
- [ ] `INSERT INTO user_certifications (id, user_id, cert_type, cert_number) VALUES ('test1', ?, 'primary', '12345')`
- [ ] **PASS**: Insert succeeds
- [ ] `INSERT INTO user_certifications (id, user_id, cert_type, cert_number) VALUES ('test2', ?, 'primary', '67890')`
- [ ] **PASS**: Insert fails with UNIQUE violation (same user_id + cert_type)

**Test 2**: Profile expansion columns exist
- [ ] `SELECT email, agency, initials, gauge_number FROM user_profiles LIMIT 1`
- [ ] **PASS**: Query succeeds (columns exist)

#### 2.5.10 get_table_integrity RPC (ADV-22/23)

**Test**: Call RPC for each table
- [ ] `SELECT * FROM get_table_integrity('projects')`
- [ ] **PASS**: Returns `row_count`, `max_updated_at`, `id_checksum` columns
- [ ] `SELECT * FROM get_table_integrity('invalid_table')`
- [ ] **PASS**: Raises exception `'Invalid table name: invalid_table'`

#### 2.5.11 Deferred Item Documentation (NEW-13)

- [ ] Create backlogged plan entry at `.claude/backlogged-plans/2026-03-xx-edit-own-records-only.md`
- [ ] Document that NEW-13 (edit own records only) is explicitly deferred to post-rewrite security hardening

### 2.6 Phase 0 Completion Gate

All items in 2.5.x must pass before proceeding to Phase 1. Record results in `.claude/test-results/phase0-verification.md`.

---

## Step 3: Phase 1 -- Change Tracking Foundation

**Agent**: `backend-data-layer-agent`
**Prerequisite**: Phase 0 tests must all pass. Phase 1 integration tests are prerequisites for Phase 2.
**Scope**: SQLite v30 migration -- change_log, conflict_log, triggers, sync_control, new tables, model changes, schema verifier updates.

This phase creates the local SQLite infrastructure that the new sync engine will depend on. All changes are in `database_service.dart` and the schema verifier, plus model-level `created_by_user_id` stamping.

### 3.1 New SQLite Tables

All new tables are created in the v30 migration block inside `database_service.dart`'s `_onUpgrade` method, guarded by `if (oldVersion < 30)`.

**File**: `lib/core/database/database_service.dart`
**Action**: Modify -- add v30 migration block after the v29 block (line ~1153)

#### 3.1.1 sync_control Table (Decision 1)

Gates trigger execution during pull/purge operations. Every sync cycle starts by force-resetting `pulling` to `'0'`.

```sql
CREATE TABLE IF NOT EXISTS sync_control (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
INSERT OR IGNORE INTO sync_control (key, value) VALUES ('pulling', '0');
```

#### 3.1.2 change_log Table

Captures every INSERT/UPDATE/DELETE on synced tables via triggers. The engine reads unprocessed entries to determine what to push.

```sql
CREATE TABLE IF NOT EXISTS change_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name TEXT NOT NULL,
  record_id TEXT NOT NULL,
  operation TEXT NOT NULL,
  changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
  processed INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_change_log_unprocessed ON change_log(processed, table_name);
```

#### 3.1.3 conflict_log Table (Decision 8)

Stores LWW conflict outcomes with changed-columns-only `lost_data` for user review.

```sql
CREATE TABLE IF NOT EXISTS conflict_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name TEXT NOT NULL,
  record_id TEXT NOT NULL,
  winner TEXT NOT NULL,
  lost_data TEXT NOT NULL,
  detected_at TEXT NOT NULL,
  dismissed_at TEXT,
  expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conflict_log_expires ON conflict_log(expires_at);
```

#### 3.1.4 sync_lock Table (Decision 2)

SQLite advisory lock for cross-isolate mutex (foreground vs WorkManager background).

```sql
CREATE TABLE IF NOT EXISTS sync_lock (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  locked_at TEXT NOT NULL,
  locked_by TEXT NOT NULL
);
```

#### 3.1.5 synced_projects Table (Decision 4)

Tracks which projects the user has selected to download. Pull flow filters by this table.

```sql
CREATE TABLE IF NOT EXISTS synced_projects (
  project_id TEXT PRIMARY KEY,
  synced_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
);
```

#### 3.1.6 user_certifications Table (Decision 12)

Local mirror of the Supabase `user_certifications` table created in Phase 0.

```sql
CREATE TABLE IF NOT EXISTS user_certifications (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  cert_type TEXT NOT NULL,
  cert_number TEXT NOT NULL,
  expiry_date TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
  UNIQUE(user_id, cert_type)
);
```

#### 3.1.7 Profile Expansion Columns (Decision 12)

Add 4 new columns to the local `user_profiles` table cache, mirroring the Supabase expansion from Phase 0.

```dart
await _addColumnIfNotExists(db, 'user_profiles', 'email', 'TEXT');
await _addColumnIfNotExists(db, 'user_profiles', 'agency', 'TEXT');
await _addColumnIfNotExists(db, 'user_profiles', 'initials', 'TEXT');
await _addColumnIfNotExists(db, 'user_profiles', 'gauge_number', 'TEXT');
```

#### 3.1.8 entry_personnel_counts Table Rebuild (GAP-11)

Fix empty-string timestamp defaults (`created_at DEFAULT ''` and `updated_at DEFAULT ''`) that were introduced in the v27 migration. SQLite cannot ALTER DEFAULT, so a table rebuild is required.

```dart
// GAP-11: Fix empty-string defaults on entry_personnel_counts
// Step 1: Create new table with correct defaults
await db.execute('''
  CREATE TABLE IF NOT EXISTS entry_personnel_counts_new (
    id TEXT PRIMARY KEY,
    entry_id TEXT NOT NULL,
    contractor_id TEXT NOT NULL,
    type_id TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
    created_by_user_id TEXT,
    deleted_at TEXT,
    deleted_by TEXT,
    FOREIGN KEY (entry_id) REFERENCES daily_entries(id) ON DELETE CASCADE,
    FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE CASCADE,
    FOREIGN KEY (type_id) REFERENCES personnel_types(id) ON DELETE CASCADE
  )
''');

// Step 2: Copy data, replacing empty strings with proper timestamps
await db.execute('''
  INSERT INTO entry_personnel_counts_new
    (id, entry_id, contractor_id, type_id, count,
     created_at, updated_at, created_by_user_id, deleted_at, deleted_by)
  SELECT
    id, entry_id, contractor_id, type_id, count,
    CASE WHEN created_at = '' THEN strftime('%Y-%m-%dT%H:%M:%f', 'now') ELSE created_at END,
    CASE WHEN updated_at = '' THEN strftime('%Y-%m-%dT%H:%M:%f', 'now') ELSE updated_at END,
    created_by_user_id, deleted_at, deleted_by
  FROM entry_personnel_counts
''');

// Step 3: Drop old table and rename
await db.execute('DROP TABLE entry_personnel_counts');
await db.execute('ALTER TABLE entry_personnel_counts_new RENAME TO entry_personnel_counts');

// Step 4: Recreate indexes
await db.execute(
  'CREATE INDEX IF NOT EXISTS idx_entry_personnel_counts_entry ON entry_personnel_counts(entry_id)',
);
await db.execute(
  'CREATE INDEX IF NOT EXISTS idx_entry_personnel_counts_type ON entry_personnel_counts(type_id)',
);
await db.execute(
  'CREATE INDEX IF NOT EXISTS idx_entry_personnel_counts_deleted_at ON entry_personnel_counts(deleted_at)',
);
```

**IMPORTANT**: The table rebuild must happen BEFORE trigger installation (3.2), because `DROP TABLE` removes any triggers attached to the old table. Triggers are installed after the rebuild.

#### 3.1.9 UNIQUE Index on Projects

Prevents duplicate project numbers within a company.

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_company_number ON projects(company_id, project_number);
```

#### 3.1.10 Bump Schema Version

**File**: `lib/core/database/database_service.dart`
**Action**: Change `version: 29` to `version: 30` at lines 54 and 90.

### 3.2 All 48 Triggers (Complete DDL)

These triggers fire on INSERT, UPDATE, and DELETE for all 16 synced tables. Each trigger includes a `WHEN` clause that checks `sync_control.pulling = '0'` to prevent the trigger-pull feedback loop.

All 48 triggers are installed inside the `if (oldVersion < 30)` migration block, AFTER the table rebuild (3.1.8) and AFTER all new tables are created.

**IMPORTANT**: The trigger DDL below uses `CREATE TRIGGER IF NOT EXISTS` for idempotency. The test helper (Step 1.1) installs these same triggers via a loop. The migration must install them explicitly.

#### Trigger 1: trg_projects_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_projects_insert AFTER INSERT ON projects
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('projects', NEW.id, 'insert');
END;
```

#### Trigger 2: trg_projects_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_projects_update AFTER UPDATE ON projects
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('projects', NEW.id, 'update');
END;
```

#### Trigger 3: trg_projects_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_projects_delete AFTER DELETE ON projects
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('projects', OLD.id, 'delete');
END;
```

#### Trigger 4: trg_locations_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_locations_insert AFTER INSERT ON locations
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('locations', NEW.id, 'insert');
END;
```

#### Trigger 5: trg_locations_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_locations_update AFTER UPDATE ON locations
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('locations', NEW.id, 'update');
END;
```

#### Trigger 6: trg_locations_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_locations_delete AFTER DELETE ON locations
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('locations', OLD.id, 'delete');
END;
```

#### Trigger 7: trg_contractors_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_contractors_insert AFTER INSERT ON contractors
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('contractors', NEW.id, 'insert');
END;
```

#### Trigger 8: trg_contractors_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_contractors_update AFTER UPDATE ON contractors
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('contractors', NEW.id, 'update');
END;
```

#### Trigger 9: trg_contractors_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_contractors_delete AFTER DELETE ON contractors
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('contractors', OLD.id, 'delete');
END;
```

#### Trigger 10: trg_equipment_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_equipment_insert AFTER INSERT ON equipment
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('equipment', NEW.id, 'insert');
END;
```

#### Trigger 11: trg_equipment_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_equipment_update AFTER UPDATE ON equipment
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('equipment', NEW.id, 'update');
END;
```

#### Trigger 12: trg_equipment_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_equipment_delete AFTER DELETE ON equipment
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('equipment', OLD.id, 'delete');
END;
```

#### Trigger 13: trg_bid_items_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_bid_items_insert AFTER INSERT ON bid_items
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('bid_items', NEW.id, 'insert');
END;
```

#### Trigger 14: trg_bid_items_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_bid_items_update AFTER UPDATE ON bid_items
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('bid_items', NEW.id, 'update');
END;
```

#### Trigger 15: trg_bid_items_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_bid_items_delete AFTER DELETE ON bid_items
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('bid_items', OLD.id, 'delete');
END;
```

#### Trigger 16: trg_personnel_types_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_personnel_types_insert AFTER INSERT ON personnel_types
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('personnel_types', NEW.id, 'insert');
END;
```

#### Trigger 17: trg_personnel_types_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_personnel_types_update AFTER UPDATE ON personnel_types
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('personnel_types', NEW.id, 'update');
END;
```

#### Trigger 18: trg_personnel_types_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_personnel_types_delete AFTER DELETE ON personnel_types
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('personnel_types', OLD.id, 'delete');
END;
```

#### Trigger 19: trg_daily_entries_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_daily_entries_insert AFTER INSERT ON daily_entries
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('daily_entries', NEW.id, 'insert');
END;
```

#### Trigger 20: trg_daily_entries_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_daily_entries_update AFTER UPDATE ON daily_entries
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('daily_entries', NEW.id, 'update');
END;
```

#### Trigger 21: trg_daily_entries_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_daily_entries_delete AFTER DELETE ON daily_entries
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('daily_entries', OLD.id, 'delete');
END;
```

#### Trigger 22: trg_photos_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_photos_insert AFTER INSERT ON photos
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('photos', NEW.id, 'insert');
END;
```

#### Trigger 23: trg_photos_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_photos_update AFTER UPDATE ON photos
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('photos', NEW.id, 'update');
END;
```

#### Trigger 24: trg_photos_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_photos_delete AFTER DELETE ON photos
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('photos', OLD.id, 'delete');
END;
```

#### Trigger 25: trg_entry_equipment_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_entry_equipment_insert AFTER INSERT ON entry_equipment
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('entry_equipment', NEW.id, 'insert');
END;
```

#### Trigger 26: trg_entry_equipment_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_entry_equipment_update AFTER UPDATE ON entry_equipment
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('entry_equipment', NEW.id, 'update');
END;
```

#### Trigger 27: trg_entry_equipment_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_entry_equipment_delete AFTER DELETE ON entry_equipment
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('entry_equipment', OLD.id, 'delete');
END;
```

#### Trigger 28: trg_entry_quantities_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_entry_quantities_insert AFTER INSERT ON entry_quantities
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('entry_quantities', NEW.id, 'insert');
END;
```

#### Trigger 29: trg_entry_quantities_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_entry_quantities_update AFTER UPDATE ON entry_quantities
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('entry_quantities', NEW.id, 'update');
END;
```

#### Trigger 30: trg_entry_quantities_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_entry_quantities_delete AFTER DELETE ON entry_quantities
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('entry_quantities', OLD.id, 'delete');
END;
```

#### Trigger 31: trg_entry_contractors_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_entry_contractors_insert AFTER INSERT ON entry_contractors
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('entry_contractors', NEW.id, 'insert');
END;
```

#### Trigger 32: trg_entry_contractors_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_entry_contractors_update AFTER UPDATE ON entry_contractors
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('entry_contractors', NEW.id, 'update');
END;
```

#### Trigger 33: trg_entry_contractors_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_entry_contractors_delete AFTER DELETE ON entry_contractors
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('entry_contractors', OLD.id, 'delete');
END;
```

#### Trigger 34: trg_entry_personnel_counts_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_entry_personnel_counts_insert AFTER INSERT ON entry_personnel_counts
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('entry_personnel_counts', NEW.id, 'insert');
END;
```

#### Trigger 35: trg_entry_personnel_counts_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_entry_personnel_counts_update AFTER UPDATE ON entry_personnel_counts
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('entry_personnel_counts', NEW.id, 'update');
END;
```

#### Trigger 36: trg_entry_personnel_counts_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_entry_personnel_counts_delete AFTER DELETE ON entry_personnel_counts
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('entry_personnel_counts', OLD.id, 'delete');
END;
```

#### Trigger 37: trg_inspector_forms_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_inspector_forms_insert AFTER INSERT ON inspector_forms
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('inspector_forms', NEW.id, 'insert');
END;
```

#### Trigger 38: trg_inspector_forms_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_inspector_forms_update AFTER UPDATE ON inspector_forms
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('inspector_forms', NEW.id, 'update');
END;
```

#### Trigger 39: trg_inspector_forms_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_inspector_forms_delete AFTER DELETE ON inspector_forms
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('inspector_forms', OLD.id, 'delete');
END;
```

#### Trigger 40: trg_form_responses_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_form_responses_insert AFTER INSERT ON form_responses
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('form_responses', NEW.id, 'insert');
END;
```

#### Trigger 41: trg_form_responses_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_form_responses_update AFTER UPDATE ON form_responses
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('form_responses', NEW.id, 'update');
END;
```

#### Trigger 42: trg_form_responses_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_form_responses_delete AFTER DELETE ON form_responses
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('form_responses', OLD.id, 'delete');
END;
```

#### Trigger 43: trg_todo_items_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_todo_items_insert AFTER INSERT ON todo_items
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('todo_items', NEW.id, 'insert');
END;
```

#### Trigger 44: trg_todo_items_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_todo_items_update AFTER UPDATE ON todo_items
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('todo_items', NEW.id, 'update');
END;
```

#### Trigger 45: trg_todo_items_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_todo_items_delete AFTER DELETE ON todo_items
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('todo_items', OLD.id, 'delete');
END;
```

#### Trigger 46: trg_calculation_history_insert
```sql
CREATE TRIGGER IF NOT EXISTS trg_calculation_history_insert AFTER INSERT ON calculation_history
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('calculation_history', NEW.id, 'insert');
END;
```

#### Trigger 47: trg_calculation_history_update
```sql
CREATE TRIGGER IF NOT EXISTS trg_calculation_history_update AFTER UPDATE ON calculation_history
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('calculation_history', NEW.id, 'update');
END;
```

#### Trigger 48: trg_calculation_history_delete
```sql
CREATE TRIGGER IF NOT EXISTS trg_calculation_history_delete AFTER DELETE ON calculation_history
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('calculation_history', OLD.id, 'delete');
END;
```

#### Trigger Installation in Dart Migration Code

In `database_service.dart`, the v30 migration installs all 48 triggers via a loop (same approach as the test helper, since the DDL is identical for each table):

```dart
// Install change tracking triggers on all 16 synced tables
const syncedTables = [
  'projects',
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

for (final table in syncedTables) {
  await db.execute('''
    CREATE TRIGGER IF NOT EXISTS trg_${table}_insert AFTER INSERT ON $table
    WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
    BEGIN
      INSERT INTO change_log (table_name, record_id, operation)
      VALUES ('$table', NEW.id, 'insert');
    END
  ''');

  await db.execute('''
    CREATE TRIGGER IF NOT EXISTS trg_${table}_update AFTER UPDATE ON $table
    WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
    BEGIN
      INSERT INTO change_log (table_name, record_id, operation)
      VALUES ('$table', NEW.id, 'update');
    END
  ''');

  await db.execute('''
    CREATE TRIGGER IF NOT EXISTS trg_${table}_delete AFTER DELETE ON $table
    WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
    BEGIN
      INSERT INTO change_log (table_name, record_id, operation)
      VALUES ('$table', OLD.id, 'delete');
    END
  ''');
}
```

**Excluded tables** (NO triggers): `entry_personnel` (legacy dead table), `extraction_metrics`, `stage_metrics` (local-only), `sync_control`, `sync_metadata`, `change_log`, `conflict_log`, `deletion_notifications`, `sync_lock`, `synced_projects`, `user_certifications`, `companies`, `user_profiles`, `company_join_requests`, `sync_queue`.

### 3.3 Model Changes

#### 3.3.1 Stamp created_by_user_id at Model Creation (NEW-5)

Currently, `created_by_user_id` is a nullable field on all models but is never stamped at creation time. Fix: read the current user ID from `AuthProvider` at construction time.

**Affected files** (all model constructors that produce new records):

| File | Model | Change |
|------|-------|--------|
| `lib/features/entries/data/models/daily_entry.dart` | `DailyEntry` | Already has `createdByUserId` field -- ensure callers pass it |
| `lib/features/photos/data/models/photo.dart` | `Photo` | Already has `createdByUserId` field -- ensure callers pass it |
| `lib/features/contractors/data/models/contractor.dart` | `Contractor` | Ensure callers pass `createdByUserId` |
| `lib/features/contractors/data/models/equipment.dart` | `Equipment` | Ensure callers pass `createdByUserId` |
| `lib/features/locations/data/models/location.dart` | `Location` | Ensure callers pass `createdByUserId` |
| `lib/features/quantities/data/models/bid_item.dart` | `BidItem` | Ensure callers pass `createdByUserId` |
| `lib/features/contractors/data/models/personnel_type.dart` | `PersonnelType` | Ensure callers pass `createdByUserId` |

**Pattern**: In each repository's `create()` method, read the user ID from the provider and pass it to the model constructor:

```dart
// In repository create method:
Future<DailyEntry> create({
  required String projectId,
  // ... other params
  required String? createdByUserId,  // Add this parameter
}) async {
  final entry = DailyEntry(
    projectId: projectId,
    // ...
    createdByUserId: createdByUserId,
  );
  await _db.insert('daily_entries', entry.toMap());
  return entry;
}
```

**In the provider/screen layer**, get the user ID from `AuthProvider`:
```dart
final userId = context.read<AuthProvider>().currentUserId;
await repo.create(
  projectId: projectId,
  createdByUserId: userId,
);
```

**Note**: The exact file changes depend on the current state of each model's constructor and callers. The implementing agent must trace each model's creation sites and ensure `createdByUserId` is populated from `AuthProvider.currentUserId`.

#### 3.3.2 Add `AND (deleted_at IS NULL)` to SyncStatusMixin

**File**: `lib/shared/mixins/sync_status_mixin.dart` (or wherever `SyncStatusMixin.getPendingSync()` is defined)
**Action**: Modify the pending sync query to exclude soft-deleted records.

This is a transition safety measure: during the rewrite, the old sync service's `getPendingSync()` should not attempt to sync records that have been soft-deleted. The new engine handles soft-deletes via the change_log.

```dart
// Before:
'SELECT COUNT(*) FROM $tableName WHERE sync_status = ?', ['pending']

// After:
'SELECT COUNT(*) FROM $tableName WHERE sync_status = ? AND (deleted_at IS NULL)', ['pending']
```

### 3.4 Schema Verifier Updates

**File**: `lib/core/database/schema_verifier.dart`
**Action**: Modify

Add the 6 new tables to `expectedSchema`:

```dart
// Add to expectedSchema map:
'sync_control': [
  'key', 'value',
],
'change_log': [
  'id', 'table_name', 'record_id', 'operation', 'changed_at',
  'processed', 'error_message', 'retry_count', 'metadata',
],
'conflict_log': [
  'id', 'table_name', 'record_id', 'winner', 'lost_data',
  'detected_at', 'dismissed_at', 'expires_at',
],
'sync_lock': [
  'id', 'locked_at', 'locked_by',
],
'synced_projects': [
  'project_id', 'synced_at',
],
'user_certifications': [
  'id', 'user_id', 'cert_type', 'cert_number', 'expiry_date',
  'created_at', 'updated_at',
],
```

Also add the profile expansion columns to the existing `user_profiles` entry:

```dart
// Update 'user_profiles' entry to include new columns:
'user_profiles': [
  'id', 'company_id', 'role', 'status', 'display_name', 'cert_number',
  'phone', 'position', 'last_synced_at', 'created_at', 'updated_at',
  'email', 'agency', 'initials', 'gauge_number',  // <-- Decision 12 additions
],
```

Add column type overrides for the new tables in `_columnTypes`:

```dart
// Add to _columnTypes map:
'change_log': {
  'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
  'processed': 'INTEGER NOT NULL DEFAULT 0',
  'retry_count': 'INTEGER NOT NULL DEFAULT 0',
},
'sync_lock': {
  'id': 'INTEGER PRIMARY KEY CHECK (id = 1)',
},
'deletion_notifications': {
  'seen': 'INTEGER NOT NULL DEFAULT 0',
},
```

**Note**: The schema verifier only adds missing columns; it does NOT create missing tables. The v30 migration creates the tables. The verifier acts as a safety net for columns that might be missing on edge-case upgrade paths.

### 3.5 Phase 1 Tests

All Phase 1 tests use the test infrastructure from Step 1. These are automated tests that run with `pwsh -Command "flutter test"`.

#### 3.5.1 Trigger Tests (Stage Trace -- Trigger Stage)

**File**: `test/features/sync/triggers/change_log_trigger_test.dart`
**Action**: Create
**Purpose**: Verify that all 48 triggers correctly create change_log entries for INSERT, UPDATE, and DELETE operations on all 16 synced tables.

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;
  late Map<String, String> seedIds;

  setUpAll(() {
    sqfliteFfiInit();
  });

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    seedIds = await SyncTestData.seedFkGraph(db);
    await SqliteTestHelper.clearChangeLog(db);
  });

  tearDown(() async {
    await db.close();
  });

  // --- projects ---
  group('projects triggers', () {
    test('INSERT creates change_log entry with operation=insert', () async {
      final id = 'test-project-insert';
      await db.insert('projects', SyncTestData.projectMap(
        id: id, companyId: seedIds['companyId'],
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(entries.length, 1);
      expect(entries.first['record_id'], id);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry with operation=update', () async {
      await db.update('projects', {'name': 'Updated'},
          where: 'id = ?', whereArgs: [seedIds['projectId']]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(entries.length, 1);
      expect(entries.first['record_id'], seedIds['projectId']);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry with operation=delete', () async {
      // Insert a fresh project (so FK constraints don't block delete)
      final id = 'project-to-delete';
      await db.insert('projects', SyncTestData.projectMap(
        id: id, companyId: seedIds['companyId'],
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('projects', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(entries.length, 1);
      expect(entries.first['record_id'], id);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- locations ---
  group('locations triggers', () {
    test('INSERT creates change_log entry with operation=insert', () async {
      final id = 'test-location-insert';
      await db.insert('locations', SyncTestData.locationMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'locations');
      expect(entries.length, 1);
      expect(entries.first['record_id'], id);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry with operation=update', () async {
      await db.update('locations', {'name': 'Updated'},
          where: 'id = ?', whereArgs: [seedIds['locationId']]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'locations');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry with operation=delete', () async {
      final id = 'location-to-delete';
      await db.insert('locations', SyncTestData.locationMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('locations', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'locations');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- contractors ---
  group('contractors triggers', () {
    test('INSERT creates change_log entry with operation=insert', () async {
      final id = 'test-contractor-insert';
      await db.insert('contractors', SyncTestData.contractorMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'contractors');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry with operation=update', () async {
      await db.update('contractors', {'name': 'Updated'},
          where: 'id = ?', whereArgs: [seedIds['contractorId']]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'contractors');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry with operation=delete', () async {
      final id = 'contractor-to-delete';
      await db.insert('contractors', SyncTestData.contractorMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('contractors', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'contractors');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- equipment ---
  group('equipment triggers', () {
    test('INSERT creates change_log entry with operation=insert', () async {
      final id = 'test-equipment-insert';
      await db.insert('equipment', SyncTestData.equipmentMap(
        id: id, contractorId: seedIds['contractorId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'equipment');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry with operation=update', () async {
      await db.update('equipment', {'name': 'Updated'},
          where: 'id = ?', whereArgs: [seedIds['equipmentId']]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'equipment');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry with operation=delete', () async {
      final id = 'equipment-to-delete';
      await db.insert('equipment', SyncTestData.equipmentMap(
        id: id, contractorId: seedIds['contractorId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('equipment', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'equipment');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- bid_items ---
  group('bid_items triggers', () {
    test('INSERT creates change_log entry', () async {
      final id = 'test-bid-item-insert';
      await db.insert('bid_items', SyncTestData.bidItemMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'bid_items');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry', () async {
      await db.update('bid_items', {'description': 'Updated'},
          where: 'id = ?', whereArgs: [seedIds['bidItemId']]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'bid_items');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry', () async {
      final id = 'bid-item-to-delete';
      await db.insert('bid_items', SyncTestData.bidItemMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('bid_items', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'bid_items');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- personnel_types ---
  group('personnel_types triggers', () {
    test('INSERT creates change_log entry', () async {
      final id = 'test-personnel-type-insert';
      await db.insert('personnel_types', SyncTestData.personnelTypeMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'personnel_types');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry', () async {
      await db.update('personnel_types', {'name': 'Updated'},
          where: 'id = ?', whereArgs: [seedIds['personnelTypeId']]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'personnel_types');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry', () async {
      final id = 'personnel-type-to-delete';
      await db.insert('personnel_types', SyncTestData.personnelTypeMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('personnel_types', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'personnel_types');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- daily_entries ---
  group('daily_entries triggers', () {
    test('INSERT creates change_log entry', () async {
      final id = 'test-entry-insert';
      await db.insert('daily_entries', SyncTestData.dailyEntryMap(
        id: id, projectId: seedIds['projectId']!,
        locationId: seedIds['locationId'],
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'daily_entries');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry', () async {
      await db.update('daily_entries', {'activities': 'Updated'},
          where: 'id = ?', whereArgs: [seedIds['entryId']]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'daily_entries');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry', () async {
      final id = 'entry-to-delete';
      await db.insert('daily_entries', SyncTestData.dailyEntryMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('daily_entries', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'daily_entries');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- photos ---
  group('photos triggers', () {
    test('INSERT creates change_log entry', () async {
      final id = 'test-photo-insert';
      await db.insert('photos', SyncTestData.photoMap(
        id: id, entryId: seedIds['entryId']!,
        projectId: seedIds['projectId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'photos');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry', () async {
      // Insert a photo first (seeded graph doesn't include one)
      final id = 'photo-for-update';
      await db.insert('photos', SyncTestData.photoMap(
        id: id, entryId: seedIds['entryId']!,
        projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.update('photos', {'caption': 'Updated'},
          where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'photos');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry', () async {
      final id = 'photo-to-delete';
      await db.insert('photos', SyncTestData.photoMap(
        id: id, entryId: seedIds['entryId']!,
        projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('photos', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'photos');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- entry_equipment ---
  group('entry_equipment triggers', () {
    test('INSERT creates change_log entry', () async {
      final id = 'test-entry-equip-insert';
      await db.insert('entry_equipment', SyncTestData.entryEquipmentMap(
        id: id, entryId: seedIds['entryId']!,
        equipmentId: seedIds['equipmentId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'entry_equipment');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry', () async {
      final id = 'entry-equip-for-update';
      await db.insert('entry_equipment', SyncTestData.entryEquipmentMap(
        id: id, entryId: seedIds['entryId']!,
        equipmentId: seedIds['equipmentId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.update('entry_equipment', {'was_used': 0},
          where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'entry_equipment');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry', () async {
      final id = 'entry-equip-to-delete';
      await db.insert('entry_equipment', SyncTestData.entryEquipmentMap(
        id: id, entryId: seedIds['entryId']!,
        equipmentId: seedIds['equipmentId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('entry_equipment', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'entry_equipment');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- entry_quantities ---
  group('entry_quantities triggers', () {
    test('INSERT creates change_log entry', () async {
      final id = 'test-entry-qty-insert';
      await db.insert('entry_quantities', SyncTestData.entryQuantityMap(
        id: id, entryId: seedIds['entryId']!,
        bidItemId: seedIds['bidItemId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'entry_quantities');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry', () async {
      final id = 'entry-qty-for-update';
      await db.insert('entry_quantities', SyncTestData.entryQuantityMap(
        id: id, entryId: seedIds['entryId']!,
        bidItemId: seedIds['bidItemId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.update('entry_quantities', {'quantity': 20.0},
          where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'entry_quantities');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry', () async {
      final id = 'entry-qty-to-delete';
      await db.insert('entry_quantities', SyncTestData.entryQuantityMap(
        id: id, entryId: seedIds['entryId']!,
        bidItemId: seedIds['bidItemId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('entry_quantities', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'entry_quantities');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- entry_contractors ---
  group('entry_contractors triggers', () {
    test('INSERT creates change_log entry', () async {
      final id = 'test-entry-contractor-insert';
      await db.insert('entry_contractors', SyncTestData.entryContractorMap(
        id: id, entryId: seedIds['entryId']!,
        contractorId: seedIds['contractorId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'entry_contractors');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry', () async {
      final id = 'entry-contractor-for-update';
      await db.insert('entry_contractors', SyncTestData.entryContractorMap(
        id: id, entryId: seedIds['entryId']!,
        contractorId: seedIds['contractorId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.update('entry_contractors',
          {'updated_at': DateTime.now().toIso8601String()},
          where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'entry_contractors');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry', () async {
      final id = 'entry-contractor-to-delete';
      await db.insert('entry_contractors', SyncTestData.entryContractorMap(
        id: id, entryId: seedIds['entryId']!,
        contractorId: seedIds['contractorId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('entry_contractors', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'entry_contractors');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- entry_personnel_counts ---
  group('entry_personnel_counts triggers', () {
    test('INSERT creates change_log entry', () async {
      final id = 'test-epc-insert';
      await db.insert('entry_personnel_counts', SyncTestData.entryPersonnelCountMap(
        id: id, entryId: seedIds['entryId']!,
        contractorId: seedIds['contractorId']!,
        typeId: seedIds['personnelTypeId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'entry_personnel_counts');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry', () async {
      final id = 'epc-for-update';
      await db.insert('entry_personnel_counts', SyncTestData.entryPersonnelCountMap(
        id: id, entryId: seedIds['entryId']!,
        contractorId: seedIds['contractorId']!,
        typeId: seedIds['personnelTypeId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.update('entry_personnel_counts', {'count': 5},
          where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'entry_personnel_counts');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry', () async {
      final id = 'epc-to-delete';
      await db.insert('entry_personnel_counts', SyncTestData.entryPersonnelCountMap(
        id: id, entryId: seedIds['entryId']!,
        contractorId: seedIds['contractorId']!,
        typeId: seedIds['personnelTypeId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('entry_personnel_counts', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'entry_personnel_counts');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- inspector_forms ---
  group('inspector_forms triggers', () {
    test('INSERT creates change_log entry', () async {
      final id = 'test-form-insert';
      await db.insert('inspector_forms', SyncTestData.inspectorFormMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'inspector_forms');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry', () async {
      final id = 'form-for-update';
      await db.insert('inspector_forms', SyncTestData.inspectorFormMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.update('inspector_forms', {'name': 'Updated'},
          where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'inspector_forms');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry', () async {
      final id = 'form-to-delete';
      await db.insert('inspector_forms', SyncTestData.inspectorFormMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('inspector_forms', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'inspector_forms');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- form_responses ---
  group('form_responses triggers', () {
    test('INSERT creates change_log entry', () async {
      final id = 'test-response-insert';
      await db.insert('form_responses', SyncTestData.formResponseMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'form_responses');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry', () async {
      final id = 'response-for-update';
      await db.insert('form_responses', SyncTestData.formResponseMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.update('form_responses', {'response_data': '{"key":"val"}'},
          where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'form_responses');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry', () async {
      final id = 'response-to-delete';
      await db.insert('form_responses', SyncTestData.formResponseMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('form_responses', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'form_responses');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- todo_items ---
  group('todo_items triggers', () {
    test('INSERT creates change_log entry', () async {
      final id = 'test-todo-insert';
      await db.insert('todo_items', SyncTestData.todoItemMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'todo_items');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry', () async {
      final id = 'todo-for-update';
      await db.insert('todo_items', SyncTestData.todoItemMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.update('todo_items', {'title': 'Updated'},
          where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'todo_items');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry', () async {
      final id = 'todo-to-delete';
      await db.insert('todo_items', SyncTestData.todoItemMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('todo_items', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'todo_items');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });

  // --- calculation_history ---
  group('calculation_history triggers', () {
    test('INSERT creates change_log entry', () async {
      final id = 'test-calc-insert';
      await db.insert('calculation_history', SyncTestData.calculationHistoryMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'calculation_history');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'insert');
    });

    test('UPDATE creates change_log entry', () async {
      final id = 'calc-for-update';
      await db.insert('calculation_history', SyncTestData.calculationHistoryMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.update('calculation_history', {'notes': 'Updated'},
          where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'calculation_history');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('DELETE creates change_log entry', () async {
      final id = 'calc-to-delete';
      await db.insert('calculation_history', SyncTestData.calculationHistoryMap(
        id: id, projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.clearChangeLog(db);
      await db.delete('calculation_history', where: 'id = ?', whereArgs: [id]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'calculation_history');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'delete');
    });
  });
}
```

#### 3.5.2 Trigger Behavior Tests

**File**: `test/features/sync/triggers/trigger_behavior_test.dart`
**Action**: Create
**Purpose**: Tests for soft-delete, batch operations, trigger suppression, and startup force-reset.

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;
  late Map<String, String> seedIds;

  setUpAll(() {
    sqfliteFfiInit();
  });

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
    seedIds = await SyncTestData.seedFkGraph(db);
    await SqliteTestHelper.clearChangeLog(db);
  });

  tearDown(() async {
    await db.close();
  });

  group('soft-delete tracking', () {
    test('setting deleted_at creates change_log UPDATE entry', () async {
      final now = DateTime.now().toUtc().toIso8601String();
      await db.update('projects',
          {'deleted_at': now, 'deleted_by': 'test-user'},
          where: 'id = ?', whereArgs: [seedIds['projectId']]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
      expect(entries.first['record_id'], seedIds['projectId']);
    });
  });

  group('batch operations', () {
    test('batch insert creates change_log entry for each row', () async {
      final ids = List.generate(10, (i) => 'batch-entry-$i');
      for (final id in ids) {
        await db.insert('daily_entries', SyncTestData.dailyEntryMap(
          id: id, projectId: seedIds['projectId']!,
        ));
      }
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'daily_entries');
      expect(entries.length, 10);
      for (int i = 0; i < 10; i++) {
        expect(entries[i]['operation'], 'insert');
      }
    });
  });

  group('submit/undo entry tracking', () {
    test('submit entry creates change_log UPDATE entry', () async {
      final entryId = seedIds['entryId']!;
      await db.update('daily_entries',
          {'status': 'submitted', 'submitted_at': DateTime.now().toIso8601String()},
          where: 'id = ?', whereArgs: [entryId]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'daily_entries');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('undo submit creates change_log UPDATE entry', () async {
      final entryId = seedIds['entryId']!;
      // Submit first
      await db.update('daily_entries',
          {'status': 'submitted'}, where: 'id = ?', whereArgs: [entryId]);
      await SqliteTestHelper.clearChangeLog(db);
      // Undo
      await db.update('daily_entries',
          {'status': 'draft', 'submitted_at': null},
          where: 'id = ?', whereArgs: [entryId]);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'daily_entries');
      expect(entries.length, 1);
      expect(entries.first['operation'], 'update');
    });

    test('batchSubmit 10 entries creates 10 change_log rows', () async {
      // Create 10 entries
      final entryIds = <String>[];
      for (int i = 0; i < 10; i++) {
        final id = 'batch-submit-$i';
        entryIds.add(id);
        await db.insert('daily_entries', SyncTestData.dailyEntryMap(
          id: id, projectId: seedIds['projectId']!,
        ));
      }
      await SqliteTestHelper.clearChangeLog(db);
      // Batch submit
      for (final id in entryIds) {
        await db.update('daily_entries',
            {'status': 'submitted'}, where: 'id = ?', whereArgs: [id]);
      }
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'daily_entries');
      expect(entries.length, 10);
    });
  });

  group('trigger suppression (sync_control gate)', () {
    test('pulling=1 suppresses INSERT trigger', () async {
      await SqliteTestHelper.suppressTriggers(db);
      await db.insert('daily_entries', SyncTestData.dailyEntryMap(
        id: 'suppressed-insert', projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.enableTriggers(db);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'daily_entries');
      expect(entries.length, 0, reason: 'Trigger should be suppressed when pulling=1');
    });

    test('pulling=1 suppresses UPDATE trigger', () async {
      await SqliteTestHelper.suppressTriggers(db);
      await db.update('projects', {'name': 'Suppressed Update'},
          where: 'id = ?', whereArgs: [seedIds['projectId']]);
      await SqliteTestHelper.enableTriggers(db);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'projects');
      expect(entries.length, 0);
    });

    test('pulling=1 suppresses DELETE trigger', () async {
      // Create a record to delete (with triggers suppressed so no insert log)
      await SqliteTestHelper.suppressTriggers(db);
      await db.insert('todo_items', SyncTestData.todoItemMap(
        id: 'suppressed-delete', projectId: seedIds['projectId']!,
      ));
      // Delete while still suppressed
      await db.delete('todo_items', where: 'id = ?', whereArgs: ['suppressed-delete']);
      await SqliteTestHelper.enableTriggers(db);
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'todo_items');
      expect(entries.length, 0);
    });

    test('re-enabling triggers (pulling=0) resumes logging', () async {
      await SqliteTestHelper.suppressTriggers(db);
      await db.insert('locations', SyncTestData.locationMap(
        id: 'suppressed-loc', projectId: seedIds['projectId']!,
      ));
      await SqliteTestHelper.enableTriggers(db);
      // Now insert with triggers active
      await db.insert('locations', SyncTestData.locationMap(
        id: 'active-loc', projectId: seedIds['projectId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'locations');
      expect(entries.length, 1);
      expect(entries.first['record_id'], 'active-loc');
    });
  });

  group('startup force-reset', () {
    test('simulated crash with pulling=1 is recoverable', () async {
      // Simulate crash: set pulling=1 and leave it
      await SqliteTestHelper.suppressTriggers(db);
      // Simulate startup: force-reset
      await SqliteTestHelper.enableTriggers(db);
      // Verify triggers work after reset
      await db.insert('contractors', SyncTestData.contractorMap(
        id: 'after-reset', projectId: seedIds['projectId']!,
      ));
      final entries = await SqliteTestHelper.getChangeLogEntries(db, 'contractors');
      expect(entries.length, 1);
    });
  });

  group('excluded tables', () {
    test('extraction_metrics does NOT have triggers', () async {
      // Verify no trigger exists by checking sqlite_master
      final triggers = await db.rawQuery(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='extraction_metrics'",
      );
      expect(triggers, isEmpty,
          reason: 'extraction_metrics is local-only and should NOT have change tracking triggers');
    });

    test('stage_metrics does NOT have triggers', () async {
      final triggers = await db.rawQuery(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='stage_metrics'",
      );
      expect(triggers, isEmpty,
          reason: 'stage_metrics is local-only and should NOT have change tracking triggers');
    });
  });
}
```

#### 3.5.3 Schema Tables Test

**File**: `test/features/sync/schema/sync_schema_test.dart`
**Action**: Create
**Purpose**: Verify that all v30 tables are created correctly with the right columns and constraints.

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;

  setUpAll(() {
    sqfliteFfiInit();
  });

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
  });

  tearDown(() async {
    await db.close();
  });

  group('sync_control table', () {
    test('exists with key and value columns', () async {
      final cols = await db.rawQuery('PRAGMA table_info(sync_control)');
      final names = cols.map((c) => c['name']).toSet();
      expect(names, containsAll(['key', 'value']));
    });

    test('has pulling=0 default row', () async {
      final rows = await db.query('sync_control',
          where: "key = 'pulling'");
      expect(rows.length, 1);
      expect(rows.first['value'], '0');
    });
  });

  group('change_log table', () {
    test('exists with all required columns', () async {
      final cols = await db.rawQuery('PRAGMA table_info(change_log)');
      final names = cols.map((c) => c['name']).toSet();
      expect(names, containsAll([
        'id', 'table_name', 'record_id', 'operation',
        'changed_at', 'processed', 'error_message',
        'retry_count', 'metadata',
      ]));
    });

    test('has unprocessed index', () async {
      final indexes = await db.rawQuery(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_change_log_unprocessed'",
      );
      expect(indexes, isNotEmpty);
    });
  });

  group('conflict_log table', () {
    test('exists with all required columns', () async {
      final cols = await db.rawQuery('PRAGMA table_info(conflict_log)');
      final names = cols.map((c) => c['name']).toSet();
      expect(names, containsAll([
        'id', 'table_name', 'record_id', 'winner',
        'lost_data', 'detected_at', 'dismissed_at', 'expires_at',
      ]));
    });

    test('has expires index', () async {
      final indexes = await db.rawQuery(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_conflict_log_expires'",
      );
      expect(indexes, isNotEmpty);
    });
  });

  group('sync_lock table', () {
    test('exists with id CHECK constraint (id = 1)', () async {
      final cols = await db.rawQuery('PRAGMA table_info(sync_lock)');
      final names = cols.map((c) => c['name']).toSet();
      expect(names, containsAll(['id', 'locked_at', 'locked_by']));
    });

    test('rejects id != 1', () async {
      expect(
        () async => await db.insert('sync_lock', {
          'id': 2,
          'locked_at': DateTime.now().toIso8601String(),
          'locked_by': 'test',
        }),
        throwsA(anything),
      );
    });
  });

  group('synced_projects table', () {
    test('exists with project_id and synced_at', () async {
      final cols = await db.rawQuery('PRAGMA table_info(synced_projects)');
      final names = cols.map((c) => c['name']).toSet();
      expect(names, containsAll(['project_id', 'synced_at']));
    });
  });

  group('user_certifications table', () {
    test('exists with all required columns', () async {
      final cols = await db.rawQuery('PRAGMA table_info(user_certifications)');
      final names = cols.map((c) => c['name']).toSet();
      expect(names, containsAll([
        'id', 'user_id', 'cert_type', 'cert_number',
        'expiry_date', 'created_at', 'updated_at',
      ]));
    });

    test('enforces UNIQUE(user_id, cert_type)', () async {
      await db.insert('user_certifications', {
        'id': 'cert-1',
        'user_id': 'user-a',
        'cert_type': 'primary',
        'cert_number': '12345',
        'created_at': DateTime.now().toIso8601String(),
        'updated_at': DateTime.now().toIso8601String(),
      });
      expect(
        () async => await db.insert('user_certifications', {
          'id': 'cert-2',
          'user_id': 'user-a',
          'cert_type': 'primary',
          'cert_number': '67890',
          'created_at': DateTime.now().toIso8601String(),
          'updated_at': DateTime.now().toIso8601String(),
        }),
        throwsA(anything),
      );
    });
  });

  group('projects UNIQUE index', () {
    test('idx_projects_company_number exists', () async {
      final indexes = await db.rawQuery(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_projects_company_number'",
      );
      expect(indexes, isNotEmpty);
    });
  });

  group('trigger count verification', () {
    test('exactly 48 change tracking triggers installed', () async {
      final triggers = await db.rawQuery(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_%'",
      );
      expect(triggers.length, 48,
          reason: '16 tables x 3 operations = 48 triggers');
    });
  });
}
```

#### 3.5.4 entry_personnel_counts Rebuild Test (GAP-11)

**File**: `test/features/sync/schema/entry_personnel_counts_rebuild_test.dart`
**Action**: Create
**Purpose**: Verify that the GAP-11 table rebuild fixed empty-string defaults.

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  late Database db;

  setUpAll(() {
    sqfliteFfiInit();
  });

  setUp(() async {
    db = await SqliteTestHelper.createDatabase();
  });

  tearDown(() async {
    await db.close();
  });

  group('entry_personnel_counts defaults', () {
    test('created_at default is ISO8601 timestamp, not empty string', () async {
      // Seed FK graph for required parent rows
      final seedIds = await SyncTestData.seedFkGraph(db);

      // Insert without specifying created_at/updated_at to test defaults
      await db.execute('''
        INSERT INTO entry_personnel_counts
          (id, entry_id, contractor_id, type_id, count)
        VALUES
          ('epc-default-test', '${seedIds['entryId']}',
           '${seedIds['contractorId']}', '${seedIds['personnelTypeId']}', 1)
      ''');

      final result = await db.query('entry_personnel_counts',
          where: 'id = ?', whereArgs: ['epc-default-test']);
      expect(result.length, 1);

      final createdAt = result.first['created_at'] as String;
      final updatedAt = result.first['updated_at'] as String;

      expect(createdAt, isNot(equals('')),
          reason: 'created_at should not be empty string after GAP-11 fix');
      expect(updatedAt, isNot(equals('')),
          reason: 'updated_at should not be empty string after GAP-11 fix');

      // Verify it parses as a valid datetime
      expect(() => DateTime.parse(createdAt), returnsNormally);
      expect(() => DateTime.parse(updatedAt), returnsNormally);
    });

    test('table has correct FK constraints after rebuild', () async {
      final fks = await db.rawQuery(
        'PRAGMA foreign_key_list(entry_personnel_counts)',
      );
      final referencedTables = fks.map((fk) => fk['table']).toSet();
      expect(referencedTables, containsAll([
        'daily_entries', 'contractors', 'personnel_types',
      ]));
    });
  });
}
```

### 3.6 Phase 1 Completion Gate

All items below must pass before proceeding to Phase 2:

- [ ] All 48 triggers verified (3.5.1) -- `pwsh -Command "flutter test test/features/sync/triggers/change_log_trigger_test.dart"`
- [ ] Trigger behavior tests pass (3.5.2) -- `pwsh -Command "flutter test test/features/sync/triggers/trigger_behavior_test.dart"`
- [ ] Schema table tests pass (3.5.3) -- `pwsh -Command "flutter test test/features/sync/schema/sync_schema_test.dart"`
- [ ] entry_personnel_counts rebuild verified (3.5.4) -- `pwsh -Command "flutter test test/features/sync/schema/entry_personnel_counts_rebuild_test.dart"`
- [ ] Schema verifier includes all 6 new tables
- [ ] `created_by_user_id` stamped at model creation for DailyEntry and Photo (at minimum)
- [ ] SQLite version bumped to 30
- [ ] Full test suite passes -- `pwsh -Command "flutter test"`

Record results in `.claude/test-results/phase1-verification.md`.

---

## Appendix: Complete v30 Migration Block (Dart)

For reference, the complete migration block in `database_service.dart` follows this structure:

```dart
// Migration from version 29 to 30: Sync engine foundation
if (oldVersion < 30) {
  // 3.1.1: sync_control table
  await db.execute('''CREATE TABLE IF NOT EXISTS sync_control (...)''');
  await db.execute("INSERT OR IGNORE INTO sync_control ...");

  // 3.1.2: change_log table
  await db.execute('''CREATE TABLE IF NOT EXISTS change_log (...)''');
  await db.execute('CREATE INDEX IF NOT EXISTS idx_change_log_unprocessed ...');

  // 3.1.3: conflict_log table
  await db.execute('''CREATE TABLE IF NOT EXISTS conflict_log (...)''');
  await db.execute('CREATE INDEX IF NOT EXISTS idx_conflict_log_expires ...');

  // 3.1.4: sync_lock table
  await db.execute('''CREATE TABLE IF NOT EXISTS sync_lock (...)''');

  // 3.1.5: synced_projects table
  await db.execute('''CREATE TABLE IF NOT EXISTS synced_projects (...)''');

  // 3.1.6: user_certifications table
  await db.execute('''CREATE TABLE IF NOT EXISTS user_certifications (...)''');

  // 3.1.7: Profile expansion columns
  await _addColumnIfNotExists(db, 'user_profiles', 'email', 'TEXT');
  await _addColumnIfNotExists(db, 'user_profiles', 'agency', 'TEXT');
  await _addColumnIfNotExists(db, 'user_profiles', 'initials', 'TEXT');
  await _addColumnIfNotExists(db, 'user_profiles', 'gauge_number', 'TEXT');

  // 3.1.8: entry_personnel_counts table rebuild (GAP-11) -- MUST be before triggers
  await db.execute('''CREATE TABLE IF NOT EXISTS entry_personnel_counts_new (...)''');
  await db.execute('''INSERT INTO entry_personnel_counts_new ... FROM entry_personnel_counts''');
  await db.execute('DROP TABLE entry_personnel_counts');
  await db.execute('ALTER TABLE entry_personnel_counts_new RENAME TO entry_personnel_counts');
  await db.execute('CREATE INDEX IF NOT EXISTS idx_entry_personnel_counts_entry ...');
  await db.execute('CREATE INDEX IF NOT EXISTS idx_entry_personnel_counts_type ...');
  await db.execute('CREATE INDEX IF NOT EXISTS idx_entry_personnel_counts_deleted_at ...');

  // 3.1.9: UNIQUE index on projects
  await db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_company_number ...');

  // 3.2: Install all 48 triggers (AFTER table rebuild)
  const syncedTables = ['projects', 'locations', ...]; // 16 tables
  for (final table in syncedTables) {
    // INSERT, UPDATE, DELETE triggers with sync_control WHEN clause
  }
}
```

**Order is critical**: Tables first, then the entry_personnel_counts rebuild, then indexes, then triggers. Triggers must come last because `DROP TABLE` in the rebuild removes any pre-existing triggers on the old table.
