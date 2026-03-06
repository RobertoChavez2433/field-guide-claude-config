# Section A: Architecture & Engine Design -- Implementation Plan

**Source Plan**: `.claude/plans/2026-03-04-sync-rewrite-and-settings-redesign.md` (lines 1-571)
**Analysis**: Verified against codebase by analysis agent (19 verified, 7 discrepancies, 10 ambiguities, 12 missing details, 7 sequence concerns)
**Current DB Version**: 29 (at `lib/core/database/database_service.dart:54`)

---

## Pre-requisites

Before any step in this plan can begin:

1. **Branch**: Work on feature branch `feat/sync-engine-rewrite` (or whatever the active feature branch is). Never commit directly to main.
2. **No old-system changes**: The old `SyncService` in `lib/services/sync_service.dart` must remain functional during development. The new engine is built alongside it. The cutover (removing old code, rewiring providers) happens in a later section.
3. **Supabase access**: The `get_table_integrity()` RPC (Step 11) requires Supabase migration authoring. The Supabase migration file must be written but does NOT need to be applied until integration testing.
4. **Dependencies**: No new pub packages are required. All code uses `sqflite`, `supabase_flutter`, `uuid`, and `dart:convert` which are already in the project.

---

## Step 1: New SQLite Engine Tables -- Schema Definitions

**File**: `lib/core/database/schema/sync_engine_tables.dart`
**Action**: Create
**Depends on**: Nothing

This file defines the 5 new SQLite tables used by the sync engine: `sync_control`, `change_log`, `conflict_log`, `sync_lock`, and `synced_projects`. These are separate from the existing `sync_tables.dart` (which holds `sync_queue` and `deletion_notifications`).

### 1.1 Create the schema file

Create `lib/core/database/schema/sync_engine_tables.dart` with the following content:

```dart
import 'dart:convert';

/// Sync engine infrastructure tables.
///
/// These tables support the new trigger-based sync engine.
/// They are separate from sync_tables.dart which holds the legacy sync_queue.
class SyncEngineTables {
  /// sync_control: gates trigger execution during pull/purge.
  /// The 'pulling' key suppresses triggers when set to '1'.
  static const String createSyncControlTable = '''
    CREATE TABLE IF NOT EXISTS sync_control (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )
  ''';

  /// Seed the initial sync_control row.
  static const String seedSyncControl = '''
    INSERT OR IGNORE INTO sync_control (key, value) VALUES ('pulling', '0')
  ''';

  /// change_log: trigger-populated change tracking, replaces sync_queue.
  static const String createChangeLogTable = '''
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
  ''';

  /// conflict_log: stores LWW conflict history for user review.
  static const String createConflictLogTable = '''
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
  ''';

  /// sync_lock: SQLite advisory lock for cross-isolate mutex.
  static const String createSyncLockTable = '''
    CREATE TABLE IF NOT EXISTS sync_lock (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      locked_at TEXT NOT NULL,
      locked_by TEXT NOT NULL
    )
  ''';

  /// synced_projects: tracks which projects the user chose to download.
  static const String createSyncedProjectsTable = '''
    CREATE TABLE IF NOT EXISTS synced_projects (
      project_id TEXT PRIMARY KEY,
      synced_at TEXT NOT NULL
    )
  ''';

  /// Indexes for sync engine tables.
  static const List<String> indexes = [
    'CREATE INDEX IF NOT EXISTS idx_change_log_unprocessed ON change_log(processed, table_name)',
    'CREATE INDEX IF NOT EXISTS idx_conflict_log_expires ON conflict_log(expires_at)',
    'CREATE INDEX IF NOT EXISTS idx_change_log_changed_at ON change_log(changed_at)',
  ];

  /// Generate the 3 triggers (INSERT, UPDATE, DELETE) for a given table.
  /// Triggers check sync_control.pulling = '0' before logging changes.
  static List<String> triggersForTable(String tableName) {
    return [
      '''
      CREATE TRIGGER IF NOT EXISTS trg_${tableName}_insert
      AFTER INSERT ON $tableName
      WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
      BEGIN
        INSERT INTO change_log (table_name, record_id, operation)
        VALUES ('$tableName', NEW.id, 'insert');
      END
      ''',
      '''
      CREATE TRIGGER IF NOT EXISTS trg_${tableName}_update
      AFTER UPDATE ON $tableName
      WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
      BEGIN
        INSERT INTO change_log (table_name, record_id, operation)
        VALUES ('$tableName', NEW.id, 'update');
      END
      ''',
      '''
      CREATE TRIGGER IF NOT EXISTS trg_${tableName}_delete
      AFTER DELETE ON $tableName
      WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
      BEGIN
        INSERT INTO change_log (table_name, record_id, operation)
        VALUES ('$tableName', OLD.id, 'delete');
      END
      ''',
    ];
  }

  /// The exact 16 tables that get triggers. Order matches FK dependency order.
  static const List<String> triggeredTables = [
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
}
```

### 1.2 Export from schema barrel

**File**: `lib/core/database/schema/schema.dart`
**Action**: Modify

Add after the last export line:
```dart
export 'sync_engine_tables.dart';
```

---

## Step 2: Database Migration (v30)

**File**: `lib/core/database/database_service.dart`
**Action**: Modify
**Depends on**: Step 1

### 2.1 Bump database version

Change line 54 from:
```dart
      version: 29,
```
to:
```dart
      version: 30,
```

Also change line 90 (in-memory database) from `version: 29` to `version: 30`.

### 2.2 Update `_onCreate` to include new tables and triggers

At the end of the `_onCreate` method (after the sync_metadata creation block around line 168, before `_createIndexes`), add:

```dart
    // Sync engine infrastructure tables (v30)
    await db.execute(SyncEngineTables.createSyncControlTable);
    await db.execute(SyncEngineTables.seedSyncControl);
    await db.execute(SyncEngineTables.createChangeLogTable);
    await db.execute(SyncEngineTables.createConflictLogTable);
    await db.execute(SyncEngineTables.createSyncLockTable);
    await db.execute(SyncEngineTables.createSyncedProjectsTable);

    // Create triggers for all 16 synced tables
    for (final table in SyncEngineTables.triggeredTables) {
      for (final trigger in SyncEngineTables.triggersForTable(table)) {
        await db.execute(trigger);
      }
    }
```

### 2.3 Update `_createIndexes` to include sync engine indexes

At the end of the `_createIndexes` method (after extraction metrics indexes), add:

```dart
    // Sync engine indexes
    for (final index in SyncEngineTables.indexes) {
      await db.execute(index);
    }
```

### 2.4 Add migration v30 in `_onUpgrade`

After the `if (oldVersion < 29)` block (around line 1153), add:

```dart
    // Migration from version 29 to 30: Sync engine infrastructure
    // Creates sync_control, change_log, conflict_log, sync_lock, synced_projects
    // and installs triggers on all 16 synced tables.
    if (oldVersion < 30) {
      // 1. Create infrastructure tables FIRST (triggers reference them)
      await db.execute(SyncEngineTables.createSyncControlTable);
      await db.execute(SyncEngineTables.seedSyncControl);
      await db.execute(SyncEngineTables.createChangeLogTable);
      await db.execute(SyncEngineTables.createConflictLogTable);
      await db.execute(SyncEngineTables.createSyncLockTable);
      await db.execute(SyncEngineTables.createSyncedProjectsTable);

      // 2. Create indexes
      for (final index in SyncEngineTables.indexes) {
        await db.execute(index);
      }

      // 3. Install triggers AFTER tables exist
      for (final table in SyncEngineTables.triggeredTables) {
        for (final trigger in SyncEngineTables.triggersForTable(table)) {
          await db.execute(trigger);
        }
      }

      // 4. Auto-populate synced_projects for existing users.
      // Without this, upgrading users would see no data after the migration
      // because the pull flow filters by synced_projects.
      final now = DateTime.now().toIso8601String();
      await db.execute('''
        INSERT OR IGNORE INTO synced_projects (project_id, synced_at)
        SELECT id, '$now' FROM projects
      ''');

      // 5. Migrate existing sync_queue entries to change_log.
      // This preserves any un-pushed changes from the old system.
      await db.execute('''
        INSERT INTO change_log (table_name, record_id, operation, changed_at, processed)
        SELECT table_name, record_id, operation, created_at, 0
        FROM sync_queue
      ''');

      // 6. Clear stale sync lock from any prior crash
      await db.execute('DELETE FROM sync_lock');
    }
```

**[CORRECTION]** The analysis (5.1) found that existing `sync_queue` entries represent un-pushed changes. The migration above includes step 5 to migrate them into `change_log`, preventing data loss. The original plan did not address this transition.

**[CORRECTION]** The analysis (5.2) found that triggers MUST be created AFTER the `sync_control` and `change_log` tables. The migration above sequences correctly: tables first, then triggers.

---

## Step 3: SchemaVerifier Update

**File**: `lib/core/database/schema_verifier.dart`
**Action**: Modify
**Depends on**: Step 1

### 3.1 Add new tables to `expectedSchema`

In the `expectedSchema` map (around line 20), add the following entries. Insert them after the existing `deletion_notifications` entry (around line 130) in the `// ---- Sync tables ----` section:

```dart
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
```

### 3.2 Add column type overrides for new tables

In the `_columnTypes` map, add:

```dart
    'change_log': {
      'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
      'processed': 'INTEGER NOT NULL DEFAULT 0',
      'retry_count': 'INTEGER NOT NULL DEFAULT 0',
    },
    'conflict_log': {
      'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
    },
    'sync_lock': {
      'id': 'INTEGER PRIMARY KEY CHECK (id = 1)',
    },
```

> Note: `SchemaVerifier.verify()` skips tables that don't exist yet, so adding these entries is safe even before the migration runs.

---

## Step 4: ScopeType Enum and TypeConverter Interface

**File**: `lib/features/sync/engine/scope_type.dart`
**Action**: Create
**Depends on**: Nothing

**[CORRECTION]** The analysis (3.1) identified that `ScopeType` is referenced by `TableAdapter` but never defined. This step defines it with clear semantics for each variant.

### 4.1 Create the ScopeType enum

```dart
/// How a table relates to the company tenant scope.
///
/// Used by the sync engine to determine how to filter records during pull:
/// - [direct]: Table has a `company_id` column. Filter: `company_id = ?`
/// - [viaProject]: Table has a `project_id` column. Filter:
///   `project_id IN (SELECT project_id FROM synced_projects)`
/// - [viaEntry]: Table has an `entry_id` column linking to daily_entries.
///   Filter: `entry_id IN (SELECT id FROM daily_entries WHERE project_id IN
///   (SELECT project_id FROM synced_projects))`
/// - [viaContractor]: Table links through contractor_id -> contractors.project_id.
///   Filter: `contractor_id IN (SELECT id FROM contractors WHERE project_id IN
///   (SELECT project_id FROM synced_projects))`
enum ScopeType {
  /// Table has company_id directly (e.g., projects).
  direct,

  /// Table has project_id (e.g., locations, contractors, bid_items, daily_entries).
  viaProject,

  /// Table has entry_id linking to daily_entries (e.g., photos, entry_equipment,
  /// entry_quantities, entry_contractors, entry_personnel_counts).
  viaEntry,

  /// Table has contractor_id linking to contractors (e.g., equipment).
  viaContractor,
}
```

> **Design decision**: The original plan used `direct`, `oneHop`, `twoHop` which were ambiguous. The analysis found these were undefined. We replace them with semantically clear names that map directly to query patterns. This is NOT a feature addition -- it resolves the ambiguity while implementing the same scoping the plan intended.

### 4.2 Create the TypeConverter interface

**File**: `lib/features/sync/adapters/type_converters.dart`
**Action**: Create
**Depends on**: Nothing

```dart
import 'dart:convert';
import 'dart:typed_data';

/// Base interface for column-level type conversion between SQLite and Supabase.
abstract class TypeConverter {
  /// Convert a local SQLite value to a Supabase-compatible value.
  dynamic toRemote(dynamic value);

  /// Convert a Supabase value to a local SQLite-compatible value.
  dynamic toLocal(dynamic value);
}

/// Converts SQLite INTEGER (0/1) <-> Supabase BOOLEAN (true/false).
///
/// Used by: projects.is_active, entry_equipment.was_used,
/// inspector_forms.is_builtin, todo_items.is_completed
class BoolIntConverter implements TypeConverter {
  const BoolIntConverter();

  @override
  dynamic toRemote(dynamic value) {
    if (value == null) return null;
    return value == 1 || value == true;
  }

  @override
  dynamic toLocal(dynamic value) {
    if (value == null) return null;
    return value == true ? 1 : 0;
  }
}

/// Converts SQLite TEXT (JSON string) <-> Supabase JSONB (Map/List).
///
/// Used by: form_responses.response_data, form_responses.header_data,
/// form_responses.response_metadata, form_responses.table_rows,
/// inspector_forms.field_definitions, inspector_forms.parsing_keywords,
/// inspector_forms.table_row_config
class JsonMapConverter implements TypeConverter {
  const JsonMapConverter();

  @override
  dynamic toRemote(dynamic value) {
    if (value == null) return null;
    if (value is String) {
      // Already a JSON string from SQLite -- parse to Map/List for Supabase JSONB
      try {
        return jsonDecode(value);
      } catch (_) {
        return value; // Not valid JSON, pass through
      }
    }
    return value; // Already a Map/List
  }

  @override
  dynamic toLocal(dynamic value) {
    if (value == null) return null;
    if (value is Map || value is List) {
      return jsonEncode(value);
    }
    return value; // Already a String
  }
}

/// Passes timestamps through unchanged.
///
/// Both SQLite and Supabase store ISO 8601 strings. This converter exists
/// as a no-op placeholder in case we later need timezone normalization.
class TimestampConverter implements TypeConverter {
  const TimestampConverter();

  @override
  dynamic toRemote(dynamic value) => value;

  @override
  dynamic toLocal(dynamic value) => value;
}

/// Converts SQLite BLOB (Uint8List) <-> Supabase BYTEA (base64 string).
///
/// Supabase PostgREST accepts and returns BYTEA as base64-encoded strings.
/// Used by: inspector_forms.template_bytes
class ByteaConverter implements TypeConverter {
  const ByteaConverter();

  @override
  dynamic toRemote(dynamic value) {
    if (value == null) return null;
    return base64Encode(value as Uint8List);
  }

  @override
  dynamic toLocal(dynamic value) {
    if (value == null) return null;
    if (value is String) {
      return base64Decode(value);
    }
    return value; // Already Uint8List
  }
}
```

---

## Step 5: TableAdapter Base Class

**File**: `lib/features/sync/adapters/table_adapter.dart`
**Action**: Create
**Depends on**: Step 4

### 5.1 Create the abstract base class

```dart
import 'package:construction_inspector/features/sync/engine/scope_type.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';

/// Abstract base class for per-table sync adapters.
///
/// Each of the 16 synced tables has a concrete subclass that declares:
/// - Table name and scope type for pull filtering
/// - FK dependencies for push ordering
/// - Type converters for column-level data transformation
/// - Local-only / remote-only column lists
///
/// The SyncEngine calls [convertForRemote] before push and [convertForLocal]
/// after pull. The engine handles all Supabase I/O; adapters are pure
/// configuration + conversion objects.
abstract class TableAdapter {
  /// The SQLite/Supabase table name (must match exactly).
  String get tableName;

  /// How this table is scoped to the company tenant.
  ScopeType get scopeType;

  /// Tables that must be pushed before this one (FK parents).
  /// Empty list for root tables (e.g., projects).
  List<String> get fkDependencies;

  /// Column-level type converters. Keys are column names.
  /// Override in subclasses that need conversion (bool/int, jsonb, bytea).
  Map<String, TypeConverter> get converters => const {};

  /// Columns that exist locally but should NOT be sent to Supabase.
  /// Always includes 'sync_status' for tables that have it.
  List<String> get localOnlyColumns => const [];

  /// Columns that exist remotely but should NOT be written locally.
  /// Typically empty. Override if Supabase has columns not in SQLite.
  List<String> get remoteOnlyColumns => const [];

  /// Whether this table supports soft-delete (deleted_at/deleted_by).
  /// All 16 synced tables support soft-delete.
  bool get supportsSoftDelete => true;

  /// Columns that should be stamped with the current user ID before push.
  /// Key = column name, Value = ignored (always stamped with current userId).
  ///
  /// Example: `{'updated_by_user_id': 'current'}` on DailyEntryAdapter.
  Map<String, String> get userStampColumns => const {};

  /// Convert a local SQLite row map to a Supabase-compatible map.
  ///
  /// Default implementation:
  /// 1. Strips [localOnlyColumns]
  /// 2. Applies [converters] (toRemote) to each mapped column
  Map<String, dynamic> convertForRemote(Map<String, dynamic> local) {
    final result = Map<String, dynamic>.from(local);

    // Strip local-only columns
    for (final col in localOnlyColumns) {
      result.remove(col);
    }

    // Apply type converters
    for (final entry in converters.entries) {
      if (result.containsKey(entry.key)) {
        result[entry.key] = entry.value.toRemote(result[entry.key]);
      }
    }

    return result;
  }

  /// Convert a Supabase row map to a local SQLite-compatible map.
  ///
  /// Default implementation:
  /// 1. Strips [remoteOnlyColumns]
  /// 2. Applies [converters] (toLocal) to each mapped column
  Map<String, dynamic> convertForLocal(Map<String, dynamic> remote) {
    final result = Map<String, dynamic>.from(remote);

    // Strip remote-only columns
    for (final col in remoteOnlyColumns) {
      result.remove(col);
    }

    // Apply type converters
    for (final entry in converters.entries) {
      if (result.containsKey(entry.key)) {
        result[entry.key] = entry.value.toLocal(result[entry.key]);
      }
    }

    return result;
  }

  /// Pre-push validation. Throws on invalid data.
  /// Default: no-op. Override in adapters that need validation.
  ///
  /// Example: PhotoAdapter validates that file_path is not null for inserts.
  Future<void> validate(Map<String, dynamic> record) async {}

  /// Extract a human-readable name for deletion notifications.
  /// Falls back through name -> title -> id -> 'Unknown'.
  String extractRecordName(Map<String, dynamic> record) {
    return record['name']?.toString() ??
        record['title']?.toString() ??
        record['id']?.toString() ??
        'Unknown';
  }
}
```

**[CORRECTION]** Analysis (2.5) noted that the existing `_extractRecordName()` returns `null` while the plan returns `'Unknown'`. The plan's `'Unknown'` fallback is a deliberate improvement -- it prevents null `record_name` in `deletion_notifications`. This is the correct behavior.

---

## Step 6: Concrete Table Adapters (16 adapters)

**Directory**: `lib/features/sync/adapters/`
**Action**: Create 16 files
**Depends on**: Step 4, Step 5

Each adapter below specifies its complete content. The adapters are listed in FK dependency order (the order they must be pushed).

### 6.1 ProjectAdapter

**File**: `lib/features/sync/adapters/project_adapter.dart`

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class ProjectAdapter extends TableAdapter {
  @override
  String get tableName => 'projects';

  @override
  ScopeType get scopeType => ScopeType.direct;

  @override
  List<String> get fkDependencies => const [];

  @override
  Map<String, TypeConverter> get converters => const {
    'is_active': BoolIntConverter(),
  };

  @override
  List<String> get localOnlyColumns => const ['sync_status'];
}
```

### 6.2 LocationAdapter

**File**: `lib/features/sync/adapters/location_adapter.dart`

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class LocationAdapter extends TableAdapter {
  @override
  String get tableName => 'locations';

  @override
  ScopeType get scopeType => ScopeType.viaProject;

  @override
  List<String> get fkDependencies => const ['projects'];
}
```

### 6.3 ContractorAdapter

**File**: `lib/features/sync/adapters/contractor_adapter.dart`

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class ContractorAdapter extends TableAdapter {
  @override
  String get tableName => 'contractors';

  @override
  ScopeType get scopeType => ScopeType.viaProject;

  @override
  List<String> get fkDependencies => const ['projects'];
}
```

### 6.4 EquipmentAdapter

**File**: `lib/features/sync/adapters/equipment_adapter.dart`

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class EquipmentAdapter extends TableAdapter {
  @override
  String get tableName => 'equipment';

  @override
  ScopeType get scopeType => ScopeType.viaContractor;

  @override
  List<String> get fkDependencies => const ['contractors'];
}
```

### 6.5 BidItemAdapter

**File**: `lib/features/sync/adapters/bid_item_adapter.dart`

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class BidItemAdapter extends TableAdapter {
  @override
  String get tableName => 'bid_items';

  @override
  ScopeType get scopeType => ScopeType.viaProject;

  @override
  List<String> get fkDependencies => const ['projects'];
}
```

### 6.6 PersonnelTypeAdapter

**File**: `lib/features/sync/adapters/personnel_type_adapter.dart`

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class PersonnelTypeAdapter extends TableAdapter {
  @override
  String get tableName => 'personnel_types';

  @override
  ScopeType get scopeType => ScopeType.viaProject;

  @override
  List<String> get fkDependencies => const ['projects', 'contractors'];
}
```

### 6.7 DailyEntryAdapter

**File**: `lib/features/sync/adapters/daily_entry_adapter.dart`

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class DailyEntryAdapter extends TableAdapter {
  @override
  String get tableName => 'daily_entries';

  @override
  ScopeType get scopeType => ScopeType.viaProject;

  @override
  List<String> get fkDependencies => const ['projects', 'locations'];

  @override
  List<String> get localOnlyColumns => const ['sync_status'];

  @override
  Map<String, String> get userStampColumns => const {
    'updated_by_user_id': 'current',
  };
}
```

### 6.8 PhotoAdapter

**File**: `lib/features/sync/adapters/photo_adapter.dart`

This adapter is special: it overrides push behavior with three-phase upload. The three-phase logic is NOT in this adapter class -- it is in the `SyncEngine` which has special-case handling for photos. The adapter provides the configuration.

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

/// Photo adapter with three-phase push support.
///
/// The SyncEngine detects `isPhotoAdapter == true` and routes to
/// the three-phase push flow (upload file -> upsert metadata -> mark synced).
class PhotoAdapter extends TableAdapter {
  @override
  String get tableName => 'photos';

  @override
  ScopeType get scopeType => ScopeType.viaEntry;

  @override
  List<String> get fkDependencies => const ['daily_entries', 'projects'];

  @override
  List<String> get localOnlyColumns => const ['sync_status', 'file_path'];

  /// Marker for the engine to use three-phase push instead of standard upsert.
  bool get isPhotoAdapter => true;

  @override
  Future<void> validate(Map<String, dynamic> record) async {
    // For new photos (inserts), file_path must be present for upload
    if (record['file_path'] == null || (record['file_path'] as String).isEmpty) {
      throw StateError('Photo record ${record['id']} has no file_path');
    }
  }
}
```

### 6.9 EntryEquipmentAdapter

**File**: `lib/features/sync/adapters/entry_equipment_adapter.dart`

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class EntryEquipmentAdapter extends TableAdapter {
  @override
  String get tableName => 'entry_equipment';

  @override
  ScopeType get scopeType => ScopeType.viaEntry;

  @override
  List<String> get fkDependencies => const ['daily_entries', 'equipment'];

  @override
  Map<String, TypeConverter> get converters => const {
    'was_used': BoolIntConverter(),
  };
}
```

### 6.10 EntryQuantitiesAdapter

**File**: `lib/features/sync/adapters/entry_quantities_adapter.dart`

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class EntryQuantitiesAdapter extends TableAdapter {
  @override
  String get tableName => 'entry_quantities';

  @override
  ScopeType get scopeType => ScopeType.viaEntry;

  @override
  List<String> get fkDependencies => const ['daily_entries', 'bid_items'];
}
```

### 6.11 EntryContractorsAdapter

**File**: `lib/features/sync/adapters/entry_contractors_adapter.dart`

**[CORRECTION]** Analysis (2.1, 2.2) notes `entry_contractors` has NEVER been synced before. This adapter enables net-new sync capability for this table.

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class EntryContractorsAdapter extends TableAdapter {
  @override
  String get tableName => 'entry_contractors';

  @override
  ScopeType get scopeType => ScopeType.viaEntry;

  @override
  List<String> get fkDependencies => const ['daily_entries', 'contractors'];
}
```

### 6.12 EntryPersonnelCountsAdapter

**File**: `lib/features/sync/adapters/entry_personnel_counts_adapter.dart`

**[CORRECTION]** Analysis (2.1, 2.2) notes `entry_personnel_counts` has NEVER been synced before. This adapter enables net-new sync capability for this table.

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class EntryPersonnelCountsAdapter extends TableAdapter {
  @override
  String get tableName => 'entry_personnel_counts';

  @override
  ScopeType get scopeType => ScopeType.viaEntry;

  @override
  List<String> get fkDependencies => const [
    'daily_entries',
    'contractors',
    'personnel_types',
  ];
}
```

### 6.13 InspectorFormAdapter

**File**: `lib/features/sync/adapters/inspector_form_adapter.dart`

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class InspectorFormAdapter extends TableAdapter {
  @override
  String get tableName => 'inspector_forms';

  @override
  ScopeType get scopeType => ScopeType.viaProject;

  @override
  List<String> get fkDependencies => const ['projects'];

  @override
  Map<String, TypeConverter> get converters => const {
    'is_builtin': BoolIntConverter(),
    'template_bytes': ByteaConverter(),
    'field_definitions': JsonMapConverter(),
    'parsing_keywords': JsonMapConverter(),
    'table_row_config': JsonMapConverter(),
  };
}
```

**[CORRECTION]** Analysis (2.4, 4.10) notes that `template_bytes` BLOB<->BYTEA conversion does NOT exist in the current system (gap NEW-9). This adapter adds it as a net-new fix.

### 6.14 FormResponseAdapter

**File**: `lib/features/sync/adapters/form_response_adapter.dart`

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class FormResponseAdapter extends TableAdapter {
  @override
  String get tableName => 'form_responses';

  @override
  ScopeType get scopeType => ScopeType.viaProject;

  @override
  List<String> get fkDependencies => const ['projects', 'inspector_forms'];

  @override
  Map<String, TypeConverter> get converters => const {
    'response_data': JsonMapConverter(),
    'header_data': JsonMapConverter(),
    'response_metadata': JsonMapConverter(),
    'table_rows': JsonMapConverter(),
  };
}
```

### 6.15 TodoItemAdapter

**File**: `lib/features/sync/adapters/todo_item_adapter.dart`

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class TodoItemAdapter extends TableAdapter {
  @override
  String get tableName => 'todo_items';

  @override
  ScopeType get scopeType => ScopeType.viaProject;

  @override
  List<String> get fkDependencies => const ['projects'];

  @override
  Map<String, TypeConverter> get converters => const {
    'is_completed': BoolIntConverter(),
  };
}
```

### 6.16 CalculationHistoryAdapter

**File**: `lib/features/sync/adapters/calculation_history_adapter.dart`

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

class CalculationHistoryAdapter extends TableAdapter {
  @override
  String get tableName => 'calculation_history';

  @override
  ScopeType get scopeType => ScopeType.viaProject;

  @override
  List<String> get fkDependencies => const ['projects'];
}
```

---

## Step 7: Sync Registry

**File**: `lib/features/sync/config/sync_registry.dart`
**Action**: Create
**Depends on**: Step 5, Step 6

### 7.1 Create the registry

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/project_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/location_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/contractor_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/equipment_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/bid_item_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/personnel_type_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/daily_entry_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/photo_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/entry_equipment_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/entry_quantities_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/entry_contractors_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/entry_personnel_counts_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/inspector_form_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/form_response_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/todo_item_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/calculation_history_adapter.dart';

/// Central registry of all table adapters.
///
/// Provides:
/// - [adapters]: all adapters in FK dependency order (push order)
/// - [adapterFor]: lookup by table name
/// - [dependencyOrder]: table names in push order
class SyncRegistry {
  SyncRegistry._();

  /// Singleton instance.
  static final SyncRegistry instance = SyncRegistry._();

  /// All adapters in FK dependency order.
  /// Push processes tables in this order to satisfy foreign key constraints.
  /// Pull processes tables in the same order.
  final List<TableAdapter> adapters = [
    ProjectAdapter(),
    LocationAdapter(),
    ContractorAdapter(),
    EquipmentAdapter(),
    BidItemAdapter(),
    PersonnelTypeAdapter(),
    DailyEntryAdapter(),
    PhotoAdapter(),
    EntryEquipmentAdapter(),
    EntryQuantitiesAdapter(),
    EntryContractorsAdapter(),
    EntryPersonnelCountsAdapter(),
    InspectorFormAdapter(),
    FormResponseAdapter(),
    TodoItemAdapter(),
    CalculationHistoryAdapter(),
  ];

  /// Lookup adapter by table name.
  late final Map<String, TableAdapter> _byName = {
    for (final a in adapters) a.tableName: a,
  };

  /// Get adapter for a table name. Throws if not found.
  TableAdapter adapterFor(String tableName) {
    final adapter = _byName[tableName];
    if (adapter == null) {
      throw ArgumentError('No adapter registered for table: $tableName');
    }
    return adapter;
  }

  /// Table names in FK dependency order.
  late final List<String> dependencyOrder =
      adapters.map((a) => a.tableName).toList();
}
```

---

## Step 8: Sync Configuration

**File**: `lib/features/sync/config/sync_config.dart`
**Action**: Create
**Depends on**: Nothing

### 8.1 Create the config

```dart
/// Configuration constants for the sync engine.
///
/// All tunable parameters are centralized here. Values are from the plan's
/// design decisions.
class SyncEngineConfig {
  SyncEngineConfig._();

  // -- Push --
  /// Maximum change_log entries to process per push cycle (Decision 3).
  static const int pushBatchLimit = 500;

  /// Anomaly threshold: log warning if unprocessed count exceeds this.
  static const int pushAnomalyThreshold = 1000;

  /// Maximum retries before marking a change as permanently failed.
  static const int maxRetryCount = 5;

  // -- Pull --
  /// Number of records per Supabase page during pull.
  static const int pullPageSize = 100;

  /// Safety margin subtracted from the pull cursor to catch transaction skew.
  static const Duration pullSafetyMargin = Duration(seconds: 5);

  // -- Integrity --
  /// How often the integrity checker runs.
  static const Duration integrityCheckInterval = Duration(hours: 4);

  // -- Lock --
  /// Stale lock timeout for crash recovery.
  static const Duration staleLockTimeout = Duration(minutes: 5);

  // -- Pruning --
  /// Age after which processed change_log entries are deleted.
  static const Duration changeLogRetention = Duration(days: 7);

  /// Age after which dismissed conflict_log entries are deleted.
  static const Duration conflictLogRetention = Duration(days: 7);

  /// Age threshold for warning about undismissed conflicts.
  static const Duration conflictWarningAge = Duration(days: 30);

  // -- Retry backoff --
  /// Base delay for exponential backoff on retryable errors.
  static const Duration retryBaseDelay = Duration(seconds: 1);

  /// Maximum delay cap for exponential backoff.
  static const Duration retryMaxDelay = Duration(seconds: 16);
}
```

---

## Step 9: SyncMutex (Advisory Lock)

**File**: `lib/features/sync/engine/sync_mutex.dart`
**Action**: Create
**Depends on**: Step 1, Step 2

### 9.1 Create the mutex

```dart
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';

/// SQLite advisory lock for cross-isolate sync mutex.
///
/// Uses the sync_lock table (single-row, id=1) to ensure only one
/// sync process runs at a time, even across foreground and background isolates.
///
/// The lock has a stale timeout (5 minutes by default) to recover from crashes.
class SyncMutex {
  final Database _db;

  SyncMutex(this._db);

  /// Try to acquire the lock. Returns true if successful.
  ///
  /// Steps:
  /// 1. Expire stale locks older than [SyncEngineConfig.staleLockTimeout]
  /// 2. INSERT the lock row. If row already exists (another process holds it),
  ///    the INSERT fails and we return false.
  Future<bool> tryAcquire(String lockedBy) async {
    // Expire stale locks (crash recovery)
    final timeoutMinutes = SyncEngineConfig.staleLockTimeout.inMinutes;
    await _db.execute(
      "DELETE FROM sync_lock WHERE locked_at < strftime('%Y-%m-%dT%H:%M:%f', 'now', '-$timeoutMinutes minutes')",
    );

    try {
      await _db.execute(
        "INSERT INTO sync_lock (id, locked_at, locked_by) VALUES (1, strftime('%Y-%m-%dT%H:%M:%f', 'now'), ?)",
        [lockedBy],
      );
      return true;
    } catch (_) {
      // Row already exists -- another process holds the lock
      return false;
    }
  }

  /// Release the lock.
  Future<void> release() async {
    await _db.execute('DELETE FROM sync_lock WHERE id = 1');
  }

  /// Force-clear all locks. Called on app startup and in SyncEngine constructor.
  Future<void> forceReset() async {
    await _db.execute('DELETE FROM sync_lock');
  }
}
```

---

## Step 10: ChangeTracker

**File**: `lib/features/sync/engine/change_tracker.dart`
**Action**: Create
**Depends on**: Step 1, Step 2

### 10.1 Create the change tracker

```dart
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/core/logging/debug_logger.dart';

/// A single change_log entry.
class ChangeEntry {
  final int id;
  final String tableName;
  final String recordId;
  final String operation; // 'insert', 'update', 'delete'
  final String changedAt;
  final int retryCount;
  final String? errorMessage;
  final String? metadata;

  ChangeEntry({
    required this.id,
    required this.tableName,
    required this.recordId,
    required this.operation,
    required this.changedAt,
    required this.retryCount,
    this.errorMessage,
    this.metadata,
  });

  factory ChangeEntry.fromMap(Map<String, dynamic> map) {
    return ChangeEntry(
      id: map['id'] as int,
      tableName: map['table_name'] as String,
      recordId: map['record_id'] as String,
      operation: map['operation'] as String,
      changedAt: map['changed_at'] as String,
      retryCount: map['retry_count'] as int,
      errorMessage: map['error_message'] as String?,
      metadata: map['metadata'] as String?,
    );
  }
}

/// Reads and manages change_log entries.
///
/// The change_log is populated by SQLite triggers (not by application code).
/// The ChangeTracker reads unprocessed entries, grouped by table, for the
/// push flow to process.
class ChangeTracker {
  final Database _db;

  ChangeTracker(this._db);

  /// Read unprocessed change_log entries, ordered by changed_at ASC.
  /// Limited to [SyncEngineConfig.pushBatchLimit] per cycle.
  ///
  /// Returns entries grouped by table_name, preserving order within each group.
  Future<Map<String, List<ChangeEntry>>> getUnprocessedChanges() async {
    // Check total count for anomaly detection
    final countResult = await _db.rawQuery(
      'SELECT COUNT(*) as cnt FROM change_log WHERE processed = 0',
    );
    final totalCount = countResult.first['cnt'] as int;
    if (totalCount > SyncEngineConfig.pushAnomalyThreshold) {
      DebugLogger.sync(
        'ANOMALY: $totalCount unprocessed change_log entries (threshold: ${SyncEngineConfig.pushAnomalyThreshold})',
      );
    }

    final rows = await _db.query(
      'change_log',
      where: 'processed = 0',
      orderBy: 'changed_at ASC',
      limit: SyncEngineConfig.pushBatchLimit,
    );

    final grouped = <String, List<ChangeEntry>>{};
    for (final row in rows) {
      final entry = ChangeEntry.fromMap(row);
      grouped.putIfAbsent(entry.tableName, () => []).add(entry);
    }
    return grouped;
  }

  /// Check if a table has any unprocessed entries with failed retries.
  /// Used by the FK dependency pre-check in the push flow.
  Future<bool> hasFailedEntries(String tableName) async {
    final result = await _db.rawQuery(
      'SELECT COUNT(*) as cnt FROM change_log '
      'WHERE processed = 0 AND table_name = ? AND retry_count >= ?',
      [tableName, SyncEngineConfig.maxRetryCount],
    );
    return (result.first['cnt'] as int) > 0;
  }

  /// Mark a change_log entry as successfully processed.
  Future<void> markProcessed(int changeId) async {
    await _db.update(
      'change_log',
      {'processed': 1},
      where: 'id = ?',
      whereArgs: [changeId],
    );
  }

  /// Mark a change_log entry as failed with an error message.
  /// Increments retry_count.
  Future<void> markFailed(int changeId, String errorMessage) async {
    await _db.execute(
      'UPDATE change_log SET error_message = ?, retry_count = retry_count + 1 WHERE id = ?',
      [errorMessage, changeId],
    );
  }

  /// Manually insert a change_log entry.
  /// Used when local wins a conflict during pull (bypasses suppressed triggers).
  Future<void> insertManualChange(String tableName, String recordId, String operation) async {
    await _db.insert('change_log', {
      'table_name': tableName,
      'record_id': recordId,
      'operation': operation,
    });
  }

  /// Prune old processed entries (Decision 14).
  /// Deletes entries older than [SyncEngineConfig.changeLogRetention].
  Future<int> pruneProcessed() async {
    final days = SyncEngineConfig.changeLogRetention.inDays;
    final result = await _db.rawDelete(
      "DELETE FROM change_log WHERE processed = 1 "
      "AND changed_at < strftime('%Y-%m-%dT%H:%M:%f', 'now', '-$days days')",
    );
    return result;
  }
}
```

**[CORRECTION]** Analysis (3.9, 2.6) noted the plan mislabels pruning as "Decision 9" when it is actually "Decision 14". This plan uses the correct reference.

---

## Step 11: ConflictResolver

**File**: `lib/features/sync/engine/conflict_resolver.dart`
**Action**: Create
**Depends on**: Step 1, Step 2

### 11.1 Create the conflict resolver

```dart
import 'dart:convert';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';

/// Result of a conflict resolution.
enum ConflictWinner { local, remote }

/// Resolves conflicts using Last-Write-Wins (LWW) strategy.
///
/// Rules:
/// - If remote.updated_at > local.updated_at -> remote wins
/// - If local.updated_at > remote.updated_at -> local wins
/// - If timestamps are equal -> remote wins (deterministic tiebreaker)
///
/// All conflicts are logged to conflict_log with changed-columns-only diff.
class ConflictResolver {
  final Database _db;

  ConflictResolver(this._db);

  /// Resolve a conflict between local and remote versions.
  ///
  /// Returns [ConflictWinner.remote] or [ConflictWinner.local].
  /// Logs the conflict to conflict_log with the losing side's changed data.
  Future<ConflictWinner> resolve({
    required String tableName,
    required String recordId,
    required Map<String, dynamic> local,
    required Map<String, dynamic> remote,
  }) async {
    final localUpdatedAt = local['updated_at'] as String?;
    final remoteUpdatedAt = remote['updated_at'] as String?;

    // Compare server-assigned updated_at (the plan says MUST compare server timestamps)
    ConflictWinner winner;
    if (remoteUpdatedAt == null || localUpdatedAt == null) {
      winner = ConflictWinner.remote; // Safety: remote wins if either is null
    } else if (remoteUpdatedAt.compareTo(localUpdatedAt) >= 0) {
      // Remote >= local: remote wins (equal timestamps = remote wins as tiebreaker)
      winner = ConflictWinner.remote;
    } else {
      // Local is strictly newer
      winner = ConflictWinner.local;
    }

    // Compute diff: only changed columns from the loser
    final loser = winner == ConflictWinner.remote ? local : remote;
    final winnerData = winner == ConflictWinner.remote ? remote : local;
    final lostData = _computeLostData(winnerData, loser);

    // Log to conflict_log
    final now = DateTime.now().toUtc().toIso8601String();
    final expiresAt = DateTime.now().toUtc()
        .add(SyncEngineConfig.conflictLogRetention)
        .toIso8601String();

    await _db.insert('conflict_log', {
      'table_name': tableName,
      'record_id': recordId,
      'winner': winner == ConflictWinner.remote ? 'remote' : 'local',
      'lost_data': jsonEncode(lostData),
      'detected_at': now,
      'expires_at': expiresAt,
    });

    return winner;
  }

  /// Compute the diff: only columns where loser differs from winner.
  /// Always includes 'id' for identification.
  Map<String, dynamic> _computeLostData(
    Map<String, dynamic> winner,
    Map<String, dynamic> loser,
  ) {
    final diff = <String, dynamic>{'id': loser['id']};
    for (final key in loser.keys) {
      if (loser[key] != winner[key]) {
        diff[key] = loser[key];
      }
    }
    return diff;
  }

  /// Prune expired dismissed conflicts.
  /// Dismissed conflicts auto-delete after expires_at.
  /// Undismissed conflicts are kept indefinitely.
  Future<int> pruneExpired() async {
    final result = await _db.rawDelete(
      "DELETE FROM conflict_log "
      "WHERE dismissed_at IS NOT NULL "
      "AND expires_at < strftime('%Y-%m-%dT%H:%M:%f', 'now')",
    );
    return result;
  }
}
```

---

## Step 12: IntegrityChecker

**File**: `lib/features/sync/engine/integrity_checker.dart`
**Action**: Create
**Depends on**: Step 7, Step 8

### 12.1 Create the integrity checker

**[CORRECTION]** Analysis (3.6) notes that SQLite has no built-in hash function. We use Dart-side computation: query all record IDs, sort them, concatenate, and hash with a simple checksum. The Supabase RPC must use the same algorithm.

```dart
import 'dart:convert';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:construction_inspector/features/sync/config/sync_registry.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/core/logging/debug_logger.dart';

/// Per-table integrity check result.
class TableIntegrityResult {
  final String tableName;
  final bool passed;
  final int localCount;
  final int remoteCount;
  final String? localMaxUpdatedAt;
  final String? remoteMaxUpdatedAt;
  final int localIdChecksum;
  final int remoteIdChecksum;
  final String? mismatchReason;

  TableIntegrityResult({
    required this.tableName,
    required this.passed,
    required this.localCount,
    required this.remoteCount,
    this.localMaxUpdatedAt,
    this.remoteMaxUpdatedAt,
    required this.localIdChecksum,
    required this.remoteIdChecksum,
    this.mismatchReason,
  });
}

/// 4-hour integrity checker.
///
/// Compares local vs remote: count, max(updated_at), and id checksum.
/// On mismatch, resets the pull cursor for that table to trigger a full re-pull.
class IntegrityChecker {
  final Database _db;
  final SupabaseClient _supabase;

  IntegrityChecker(this._db, this._supabase);

  /// Check if it's time to run (last check was > 4 hours ago).
  Future<bool> shouldRun() async {
    final rows = await _db.query(
      'sync_metadata',
      where: "key = ?",
      whereArgs: ['last_integrity_check'],
    );
    if (rows.isEmpty) return true;

    final lastCheck = DateTime.tryParse(rows.first['value'] as String);
    if (lastCheck == null) return true;

    return DateTime.now().difference(lastCheck) > SyncEngineConfig.integrityCheckInterval;
  }

  /// Run integrity checks for all tables.
  Future<List<TableIntegrityResult>> run() async {
    final results = <TableIntegrityResult>[];

    for (final adapter in SyncRegistry.instance.adapters) {
      try {
        final result = await _checkTable(adapter.tableName);
        results.add(result);

        if (!result.passed) {
          DebugLogger.sync(
            'INTEGRITY DRIFT: ${adapter.tableName} - ${result.mismatchReason}',
          );
          // Reset pull cursor to trigger full re-pull
          await _db.delete(
            'sync_metadata',
            where: "key = ?",
            whereArgs: ['last_pull_${adapter.tableName}'],
          );
        }
      } catch (e) {
        DebugLogger.error('Integrity check failed for ${adapter.tableName}', error: e);
        results.add(TableIntegrityResult(
          tableName: adapter.tableName,
          passed: false,
          localCount: -1,
          remoteCount: -1,
          localIdChecksum: 0,
          remoteIdChecksum: 0,
          mismatchReason: 'Check failed: $e',
        ));
      }
    }

    // Store check timestamp
    final now = DateTime.now().toUtc().toIso8601String();
    await _db.insert(
      'sync_metadata',
      {'key': 'last_integrity_check', 'value': now},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );

    return results;
  }

  Future<TableIntegrityResult> _checkTable(String tableName) async {
    // Local stats
    final localCountResult = await _db.rawQuery(
      'SELECT COUNT(*) as cnt FROM $tableName WHERE deleted_at IS NULL',
    );
    final localCount = localCountResult.first['cnt'] as int;

    final localMaxResult = await _db.rawQuery(
      'SELECT MAX(updated_at) as max_ts FROM $tableName WHERE deleted_at IS NULL',
    );
    final localMaxTs = localMaxResult.first['max_ts'] as String?;

    // Local ID checksum: sum of hashCode of all IDs (sorted for determinism)
    final localIds = await _db.rawQuery(
      'SELECT id FROM $tableName WHERE deleted_at IS NULL ORDER BY id',
    );
    final localChecksum = _computeIdChecksum(
      localIds.map((r) => r['id'] as String).toList(),
    );

    // Remote stats via RPC
    final rpcResult = await _supabase.rpc('get_table_integrity', params: {
      'p_table_name': tableName,
    });

    final remoteCount = rpcResult['count'] as int;
    final remoteMaxTs = rpcResult['max_updated_at'] as String?;
    final remoteChecksum = rpcResult['id_checksum'] as int;

    // Compare
    String? mismatchReason;
    if (localCount != remoteCount) {
      mismatchReason = 'Count mismatch: local=$localCount, remote=$remoteCount';
    } else if (localMaxTs != remoteMaxTs) {
      mismatchReason = 'Max updated_at mismatch: local=$localMaxTs, remote=$remoteMaxTs';
    } else if (localChecksum != remoteChecksum) {
      mismatchReason = 'ID checksum mismatch: local=$localChecksum, remote=$remoteChecksum';
    }

    return TableIntegrityResult(
      tableName: tableName,
      passed: mismatchReason == null,
      localCount: localCount,
      remoteCount: remoteCount,
      localMaxUpdatedAt: localMaxTs,
      remoteMaxUpdatedAt: remoteMaxTs,
      localIdChecksum: localChecksum,
      remoteIdChecksum: remoteChecksum,
      mismatchReason: mismatchReason,
    );
  }

  /// Compute a deterministic checksum from a sorted list of record IDs.
  ///
  /// Uses a simple djb2-like hash to produce a stable integer.
  /// The Supabase RPC must use the same algorithm (see migration).
  static int _computeIdChecksum(List<String> sortedIds) {
    int hash = 5381;
    for (final id in sortedIds) {
      for (int i = 0; i < id.length; i++) {
        hash = ((hash << 5) + hash + id.codeUnitAt(i)) & 0x7FFFFFFF;
      }
    }
    return hash;
  }
}
```

### 12.2 Supabase RPC migration

**File**: `supabase/migrations/20260305000000_add_get_table_integrity_rpc.sql`
**Action**: Create

```sql
-- Integrity checker RPC: returns count, max_updated_at, and id_checksum
-- for a given table, scoped to the calling user's company.
--
-- The id_checksum uses the same djb2 algorithm as the Dart client:
--   hash = 5381; for each char c in each id: hash = ((hash << 5) + hash + ascii(c)) & 0x7FFFFFFF
--
-- This function is SECURITY DEFINER to allow dynamic table access while
-- maintaining company scoping via get_my_company_id().
CREATE OR REPLACE FUNCTION get_table_integrity(p_table_name TEXT)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_count INTEGER;
  v_max_updated_at TIMESTAMPTZ;
  v_checksum INTEGER := 5381;
  v_id TEXT;
  v_char INTEGER;
  v_company_id UUID;
  v_query TEXT;
BEGIN
  -- Get caller's company
  v_company_id := get_my_company_id();
  IF v_company_id IS NULL THEN
    RAISE EXCEPTION 'No company context';
  END IF;

  -- Validate table name (prevent SQL injection)
  IF p_table_name NOT IN (
    'projects', 'locations', 'contractors', 'equipment', 'bid_items',
    'personnel_types', 'daily_entries', 'photos', 'entry_equipment',
    'entry_quantities', 'entry_contractors', 'entry_personnel_counts',
    'inspector_forms', 'form_responses', 'todo_items', 'calculation_history'
  ) THEN
    RAISE EXCEPTION 'Invalid table name: %', p_table_name;
  END IF;

  -- Build company-scoped query based on table
  IF p_table_name = 'projects' THEN
    v_query := format(
      'SELECT COUNT(*), MAX(updated_at) FROM %I WHERE deleted_at IS NULL AND company_id = %L',
      p_table_name, v_company_id
    );
  ELSIF p_table_name IN ('locations', 'contractors', 'bid_items', 'personnel_types',
                          'daily_entries', 'inspector_forms', 'form_responses',
                          'todo_items', 'calculation_history') THEN
    v_query := format(
      'SELECT COUNT(*), MAX(updated_at) FROM %I WHERE deleted_at IS NULL AND project_id IN (SELECT id FROM projects WHERE company_id = %L)',
      p_table_name, v_company_id
    );
  ELSIF p_table_name = 'equipment' THEN
    v_query := format(
      'SELECT COUNT(*), MAX(updated_at) FROM %I WHERE deleted_at IS NULL AND contractor_id IN (SELECT id FROM contractors WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L))',
      p_table_name, v_company_id
    );
  ELSIF p_table_name IN ('photos', 'entry_equipment', 'entry_quantities',
                          'entry_contractors', 'entry_personnel_counts') THEN
    v_query := format(
      'SELECT COUNT(*), MAX(updated_at) FROM %I WHERE deleted_at IS NULL AND entry_id IN (SELECT id FROM daily_entries WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L))',
      p_table_name, v_company_id
    );
  END IF;

  EXECUTE v_query INTO v_count, v_max_updated_at;
  v_count := COALESCE(v_count, 0);

  -- Compute id_checksum using djb2 algorithm matching Dart client
  FOR v_id IN
    EXECUTE format(
      'SELECT id::TEXT FROM %I WHERE deleted_at IS NULL ORDER BY id',
      p_table_name
    ) || CASE
      WHEN p_table_name = 'projects' THEN format(' AND company_id = %L', v_company_id)
      ELSE ''
    END
  LOOP
    FOR i IN 1..length(v_id) LOOP
      v_char := ascii(substring(v_id FROM i FOR 1));
      v_checksum := ((v_checksum * 33) + v_char) & x'7FFFFFFF'::INTEGER;
    END LOOP;
  END LOOP;

  RETURN json_build_object(
    'count', v_count,
    'max_updated_at', v_max_updated_at,
    'id_checksum', v_checksum
  );
END;
$$;
```

> **Note**: The djb2 implementation in SQL uses `hash * 33` which is equivalent to `(hash << 5) + hash`. The Supabase RPC and Dart client MUST produce identical checksums. Unit tests in a later section will verify this.

---

## Step 13: SyncEngine (Push/Pull Orchestrator)

**File**: `lib/features/sync/engine/sync_engine.dart`
**Action**: Create
**Depends on**: Steps 4-12

This is the core orchestrator. It implements the push and pull flows from the plan.

### 13.1 Create the engine

```dart
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:uuid/uuid.dart';

import 'package:construction_inspector/core/logging/debug_logger.dart';
import 'package:construction_inspector/features/sync/engine/sync_mutex.dart';
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';
import 'package:construction_inspector/features/sync/engine/conflict_resolver.dart';
import 'package:construction_inspector/features/sync/engine/integrity_checker.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';
import 'package:construction_inspector/features/sync/config/sync_registry.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/photo_adapter.dart';

/// Result of a sync engine cycle.
class SyncEngineResult {
  final int pushed;
  final int pulled;
  final int errors;
  final List<String> errorMessages;
  final bool lockFailed;

  const SyncEngineResult({
    this.pushed = 0,
    this.pulled = 0,
    this.errors = 0,
    this.errorMessages = const [],
    this.lockFailed = false,
  });

  bool get hasErrors => errors > 0;
  bool get isSuccess => !hasErrors && !lockFailed;

  SyncEngineResult operator +(SyncEngineResult other) {
    return SyncEngineResult(
      pushed: pushed + other.pushed,
      pulled: pulled + other.pulled,
      errors: errors + other.errors,
      errorMessages: [...errorMessages, ...other.errorMessages],
    );
  }

  @override
  String toString() =>
      'SyncEngineResult(pushed: $pushed, pulled: $pulled, errors: $errors, lockFailed: $lockFailed)';
}

/// Progress callback: (tableName, processedInTable, totalInTable).
typedef SyncProgressCallback = void Function(String tableName, int processed, int? total);

/// The new sync engine orchestrator.
///
/// Replaces the legacy SyncService push/pull logic.
/// Uses trigger-based change_log instead of manual queueOperation calls.
///
/// Constructor parameters:
/// - [db]: SQLite database instance
/// - [supabase]: Supabase client
/// - [companyId]: Current user's company ID
/// - [userId]: Current user's ID (for user-stamp columns and deletion notifications)
/// - [lockedBy]: 'foreground' or 'background' (for sync_lock attribution)
class SyncEngine {
  final Database db;
  final SupabaseClient supabase;
  final String companyId;
  final String userId;
  final String lockedBy;

  late final SyncMutex _mutex;
  late final ChangeTracker _changeTracker;
  late final ConflictResolver _conflictResolver;
  late final IntegrityChecker _integrityChecker;
  final SyncRegistry _registry = SyncRegistry.instance;

  /// Debug-mode assertion guard for non-reentrancy.
  bool _insidePushOrPull = false;

  /// Optional progress callback.
  SyncProgressCallback? onProgress;

  SyncEngine({
    required this.db,
    required this.supabase,
    required this.companyId,
    required this.userId,
    this.lockedBy = 'foreground',
    this.onProgress,
  }) {
    _mutex = SyncMutex(db);
    _changeTracker = ChangeTracker(db);
    _conflictResolver = ConflictResolver(db);
    _integrityChecker = IntegrityChecker(db, supabase);
  }

  /// Force-reset sync_control and sync_lock.
  /// Called on app startup and before each sync cycle.
  Future<void> resetState() async {
    await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
    await _mutex.forceReset();
  }

  /// Run a full push-then-pull cycle.
  Future<SyncEngineResult> pushAndPull() async {
    // Force-reset sync_control (startup safety)
    await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");

    // Acquire lock
    if (!await _mutex.tryAcquire(lockedBy)) {
      DebugLogger.sync('Lock held by another process, aborting sync');
      return const SyncEngineResult(lockFailed: true);
    }

    try {
      assert(!_insidePushOrPull, 'SyncEngine: push/pull must not be called reentrantly');
      _insidePushOrPull = true;

      final pushResult = await _push();
      final pullResult = await _pull();

      // Pruning
      await _changeTracker.pruneProcessed();
      await _conflictResolver.pruneExpired();

      // Integrity check (if due)
      if (await _integrityChecker.shouldRun()) {
        try {
          await _integrityChecker.run();
        } catch (e) {
          DebugLogger.error('Integrity check failed', error: e);
        }
      }

      return pushResult + pullResult;
    } finally {
      _insidePushOrPull = false;
      await _mutex.release();
    }
  }

  /// Push local changes to Supabase.
  Future<SyncEngineResult> _push() async {
    int pushed = 0;
    int errors = 0;
    final errorMessages = <String>[];

    final grouped = await _changeTracker.getUnprocessedChanges();

    // Process tables in FK dependency order
    for (final tableName in _registry.dependencyOrder) {
      final changes = grouped[tableName];
      if (changes == null || changes.isEmpty) continue;

      final adapter = _registry.adapterFor(tableName);

      // FK dependency pre-check: skip if parent has permanently failed entries
      bool blocked = false;
      for (final parent in adapter.fkDependencies) {
        if (await _changeTracker.hasFailedEntries(parent)) {
          DebugLogger.sync('BLOCKED: $tableName skipped due to failed entries in $parent');
          for (final change in changes) {
            await _changeTracker.markFailed(
              change.id,
              'Blocked by parent sync failure in $parent',
            );
          }
          errors += changes.length;
          errorMessages.add('$tableName blocked by $parent');
          blocked = true;
          break;
        }
      }
      if (blocked) continue;

      int processedInTable = 0;
      for (final change in changes) {
        try {
          if (change.operation == 'delete') {
            await _pushDelete(adapter, change);
          } else {
            await _pushUpsert(adapter, change);
          }
          await _changeTracker.markProcessed(change.id);
          pushed++;
        } catch (e) {
          final errorHandled = await _handlePushError(e, change);
          if (!errorHandled) {
            errors++;
            errorMessages.add('${change.tableName}/${change.recordId}: $e');
          }
        }
        processedInTable++;
        onProgress?.call(tableName, processedInTable, changes.length);
      }
    }

    return SyncEngineResult(pushed: pushed, errors: errors, errorMessages: errorMessages);
  }

  /// Push a delete operation.
  Future<void> _pushDelete(TableAdapter adapter, ChangeEntry change) async {
    try {
      await supabase.from(adapter.tableName).delete().eq('id', change.recordId);
    } on PostgrestException catch (e) {
      // 404 or "not found" = record already gone = benign no-op
      if (e.code == '404' || e.message.contains('not found') || e.code == 'PGRST116') {
        DebugLogger.sync('Delete no-op: ${adapter.tableName}/${change.recordId} already gone');
        return;
      }
      rethrow;
    }
  }

  /// Push an insert or update operation.
  Future<void> _pushUpsert(TableAdapter adapter, ChangeEntry change) async {
    // Read current local record
    final rows = await db.query(
      adapter.tableName,
      where: 'id = ?',
      whereArgs: [change.recordId],
    );

    if (rows.isEmpty) {
      // Record deleted locally after change_log entry was created.
      // This is handled by the separate 'delete' operation in change_log.
      DebugLogger.sync('Skip upsert: ${adapter.tableName}/${change.recordId} no longer exists locally');
      return;
    }

    final localRecord = rows.first;

    // Validate
    await adapter.validate(localRecord);

    // Convert for remote
    var payload = adapter.convertForRemote(Map<String, dynamic>.from(localRecord));

    // Stamp user-tracking columns
    for (final col in adapter.userStampColumns.keys) {
      payload[col] = userId;
    }

    // Stamp company_id on projects
    if (adapter.tableName == 'projects') {
      if (payload['company_id'] == null || payload['company_id'] == '') {
        payload['company_id'] = companyId;
      }
    }

    // Stamp created_by_user_id if not already set
    if (!payload.containsKey('created_by_user_id') || payload['created_by_user_id'] == null) {
      payload['created_by_user_id'] = userId;
    }

    // Special handling for photos: three-phase push
    if (adapter is PhotoAdapter) {
      await _pushPhotoThreePhase(adapter, change, localRecord, payload);
      return;
    }

    // Strip columns not in local schema from payload to prevent Supabase errors
    // for columns that exist locally but not remotely (handled by localOnlyColumns)
    // and ensure we're not sending file_path for photos, etc.
    await supabase.from(adapter.tableName).upsert(payload);
  }

  /// Three-phase photo push (Decision 7 / NEW-3 / NEW-4 fix).
  Future<void> _pushPhotoThreePhase(
    PhotoAdapter adapter,
    ChangeEntry change,
    Map<String, dynamic> localRecord,
    Map<String, dynamic> payload,
  ) async {
    final filePath = localRecord['file_path'] as String?;
    final entryId = localRecord['entry_id'] as String;
    final filename = localRecord['filename'] as String;
    final existingRemotePath = localRecord['remote_path'] as String?;

    // Phase 1: Upload file (skip if already uploaded)
    String remotePath;
    final expectedPath = 'entries/$companyId/$entryId/$filename';

    if (existingRemotePath != null && existingRemotePath.isNotEmpty) {
      // File may already be uploaded from a prior partial push
      remotePath = existingRemotePath;
    } else {
      if (filePath == null || filePath.isEmpty) {
        throw StateError('Photo ${change.recordId} has no file_path for upload');
      }
      // Upload to storage
      final file = await _readFile(filePath);
      await supabase.storage
          .from('entry-photos')
          .uploadBinary(expectedPath, file);
      remotePath = expectedPath;
    }

    // Phase 2: Upsert metadata with FRESH remote_path from Phase 1
    payload['remote_path'] = remotePath;
    await supabase.from('photos').upsert(payload);

    // Phase 3: Mark local as synced (update remote_path)
    await db.update(
      'photos',
      {'remote_path': remotePath, 'sync_status': 'synced'},
      where: 'id = ?',
      whereArgs: [change.recordId],
    );
  }

  /// Read file bytes. Isolated for testability.
  Future<List<int>> _readFile(String path) async {
    final file = await compute(_readFileBytes, path);
    return file;
  }

  static List<int> _readFileBytes(String path) {
    return java.io.File(path).readAsBytesSync();
    // NOTE: Implementation agent should use dart:io File here.
    // The actual code is: import 'dart:io'; File(path).readAsBytesSync()
  }

  /// Handle push errors with retry/backoff/auth-refresh logic.
  /// Returns true if the error was handled (retry scheduled), false if permanent.
  Future<bool> _handlePushError(Object error, ChangeEntry change) async {
    if (error is PostgrestException) {
      final code = error.code;

      // 401: Auth error -- attempt token refresh
      if (code == '401' || error.message.contains('JWT')) {
        final refreshed = await _handleAuthError();
        if (refreshed) {
          // Retry immediately -- do NOT increment retry_count
          return true;
        }
        // Refresh failed -- abort entire cycle
        throw StateError('Auth refresh failed, aborting sync');
      }

      // 429 / 503 / network: Retryable
      if (code == '429' || code == '503') {
        await _changeTracker.markFailed(change.id, 'Retryable: $code');
        return true;
      }

      // 400 / 403 / 404: Permanent
      await _changeTracker.markFailed(change.id, 'Permanent: ${error.message}');
      return false;
    }

    // Network errors
    if (error.toString().contains('SocketException') ||
        error.toString().contains('TimeoutException')) {
      await _changeTracker.markFailed(change.id, 'Network error');
      return true;
    }

    // Unknown error
    await _changeTracker.markFailed(change.id, error.toString());
    return false;
  }

  /// Auth token refresh (plan lines 560-570).
  Future<bool> _handleAuthError() async {
    final session = Supabase.instance.client.auth.currentSession;
    if (session == null) return false;
    try {
      await Supabase.instance.client.auth.refreshSession();
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Pull remote changes to local SQLite.
  Future<SyncEngineResult> _pull() async {
    int pulled = 0;
    int errors = 0;
    final errorMessages = <String>[];

    // Enable trigger suppression
    await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");

    try {
      for (final adapter in _registry.adapters) {
        try {
          final count = await _pullTable(adapter);
          pulled += count;
        } catch (e) {
          errors++;
          errorMessages.add('Pull ${adapter.tableName}: $e');
          DebugLogger.error('Pull failed for ${adapter.tableName}', error: e);
        }
      }

      // Update last sync time
      final now = DateTime.now().toUtc().toIso8601String();
      await db.insert(
        'sync_metadata',
        {'key': 'last_sync_time', 'value': now},
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    } finally {
      // ALWAYS re-enable triggers, even on exception
      await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
    }

    return SyncEngineResult(pulled: pulled, errors: errors, errorMessages: errorMessages);
  }

  /// Pull a single table.
  Future<int> _pullTable(TableAdapter adapter) async {
    int pulled = 0;

    // Read cursor
    final cursorRows = await db.query(
      'sync_metadata',
      where: "key = ?",
      whereArgs: ['last_pull_${adapter.tableName}'],
    );
    String? cursor = cursorRows.isNotEmpty ? cursorRows.first['value'] as String : null;

    // Build Supabase query with scope filter and cursor
    String? maxUpdatedAt;
    int offset = 0;
    bool hasMore = true;

    while (hasMore) {
      var query = supabase.from(adapter.tableName).select();

      // Apply scope filter based on synced_projects
      query = _applyScopeFilter(query, adapter);

      // Apply cursor with safety margin
      if (cursor != null) {
        final cursorTime = DateTime.parse(cursor)
            .subtract(SyncEngineConfig.pullSafetyMargin);
        query = query.gte('updated_at', cursorTime.toIso8601String());
      }

      // Paginate
      final page = await query
          .order('updated_at', ascending: true)
          .range(offset, offset + SyncEngineConfig.pullPageSize - 1);

      if (page.isEmpty) {
        hasMore = false;
        break;
      }

      for (final remoteRaw in page) {
        final remote = adapter.convertForLocal(Map<String, dynamic>.from(remoteRaw));
        final recordId = remote['id'] as String;

        // Deduplicate: skip if local has identical updated_at
        final localRows = await db.query(
          adapter.tableName,
          where: 'id = ?',
          whereArgs: [recordId],
        );

        if (localRows.isEmpty) {
          // Not exists locally
          if (remote['deleted_at'] != null) {
            // Skip already-deleted records
            continue;
          }
          // Strip unknown columns from remote before insert
          final validColumns = await _getLocalColumns(adapter.tableName);
          remote.removeWhere((key, _) => !validColumns.contains(key));

          await db.insert(adapter.tableName, remote,
              conflictAlgorithm: ConflictAlgorithm.ignore);
          pulled++;
        } else {
          // Exists locally: conflict resolution
          final localRecord = localRows.first;

          // Deduplicate: skip if identical updated_at (safety margin overlap)
          if (localRecord['updated_at'] == remote['updated_at']) {
            continue;
          }

          final winner = await _conflictResolver.resolve(
            tableName: adapter.tableName,
            recordId: recordId,
            local: Map<String, dynamic>.from(localRecord),
            remote: remote,
          );

          if (winner == ConflictWinner.remote) {
            // Remote wins: update local
            final validColumns = await _getLocalColumns(adapter.tableName);
            remote.removeWhere((key, _) => !validColumns.contains(key));
            await db.update(adapter.tableName, remote,
                where: 'id = ?', whereArgs: [recordId]);
            pulled++;
          } else {
            // Local wins: keep local, but push local version back
            // This is the ONE case where pull creates a change_log entry
            await _changeTracker.insertManualChange(
              adapter.tableName,
              recordId,
              'update',
            );
          }
        }

        // Handle deletion notification
        if (remote['deleted_at'] != null &&
            remote['deleted_by'] != null &&
            remote['deleted_by'] != userId) {
          await _createDeletionNotification(adapter, remote, localRows.isNotEmpty ? localRows.first : null);
        }

        // Track max updated_at for cursor
        final remoteTs = remoteRaw['updated_at'] as String?;
        if (remoteTs != null) {
          if (maxUpdatedAt == null || remoteTs.compareTo(maxUpdatedAt) > 0) {
            maxUpdatedAt = remoteTs;
          }
        }
      }

      if (page.length < SyncEngineConfig.pullPageSize) {
        hasMore = false;
      } else {
        offset += SyncEngineConfig.pullPageSize;
      }
    }

    // Update cursor
    if (maxUpdatedAt != null) {
      await db.insert(
        'sync_metadata',
        {'key': 'last_pull_${adapter.tableName}', 'value': maxUpdatedAt},
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    }

    return pulled;
  }

  /// Apply company-scope filter to a Supabase query based on adapter's ScopeType.
  ///
  /// [CORRECTION] Analysis (3.1) found scope types were undefined. This implements
  /// concrete query filters for each scope type.
  PostgrestFilterBuilder _applyScopeFilter(
    PostgrestFilterBuilder query,
    TableAdapter adapter,
  ) {
    switch (adapter.scopeType) {
      case ScopeType.direct:
        // projects: filter by company_id
        return query.eq('company_id', companyId);
      case ScopeType.viaProject:
        // Tables with project_id: filter by synced projects
        // NOTE: This requires the synced_projects to be loaded.
        // The engine loads synced project IDs at the start of pull.
        return query.inFilter('project_id', _syncedProjectIds);
      case ScopeType.viaEntry:
        // Tables with entry_id: filter by entries in synced projects
        // NOTE: Supabase PostgREST supports inner joins via !inner
        return query.inFilter('project_id', _syncedProjectIds);
      case ScopeType.viaContractor:
        // equipment: filter by contractor_id in synced projects
        return query.inFilter('contractor_id', _syncedContractorIds);
    }
  }

  // Cached project/contractor IDs for pull scoping
  List<String> _syncedProjectIds = [];
  List<String> _syncedContractorIds = [];

  /// Load synced project IDs and related contractor IDs before pull.
  /// Must be called at the start of each pull cycle.
  Future<void> _loadSyncedProjectIds() async {
    final rows = await db.query('synced_projects');
    _syncedProjectIds = rows.map((r) => r['project_id'] as String).toList();

    // Also load contractor IDs for equipment scoping
    if (_syncedProjectIds.isNotEmpty) {
      final contractors = await db.query(
        'contractors',
        columns: ['id'],
        where: 'project_id IN (${_syncedProjectIds.map((_) => '?').join(',')})',
        whereArgs: _syncedProjectIds,
      );
      _syncedContractorIds = contractors.map((r) => r['id'] as String).toList();
    }
  }

  /// Create a deletion notification for records deleted by other users.
  Future<void> _createDeletionNotification(
    TableAdapter adapter,
    Map<String, dynamic> remote,
    Map<String, dynamic>? localRecord,
  ) async {
    // Look up the deleter's display name
    final deletedBy = remote['deleted_by'] as String;
    String? deletedByName;
    try {
      final profiles = await db.query(
        'user_profiles',
        columns: ['display_name'],
        where: 'id = ?',
        whereArgs: [deletedBy],
      );
      if (profiles.isNotEmpty) {
        deletedByName = profiles.first['display_name'] as String?;
      }
    } catch (_) {}

    await db.insert('deletion_notifications', {
      'id': const Uuid().v4(),
      'record_id': remote['id'],
      'table_name': adapter.tableName,
      'project_id': remote['project_id'] ?? localRecord?['project_id'],
      'record_name': adapter.extractRecordName(localRecord ?? remote),
      'deleted_by': deletedBy,
      'deleted_by_name': deletedByName,
      'deleted_at': remote['deleted_at'],
      'seen': 0,
    });
  }

  /// Cache for local column names (cleared per cycle).
  final Map<String, Set<String>> _localColumnCache = {};

  Future<Set<String>> _getLocalColumns(String tableName) async {
    if (_localColumnCache.containsKey(tableName)) {
      return _localColumnCache[tableName]!;
    }
    final columns = await db.rawQuery("PRAGMA table_info('$tableName')");
    final names = columns.map((c) => c['name'] as String).toSet();
    _localColumnCache[tableName] = names;
    return names;
  }
}
```

**Important implementation notes for the agent:**

1. The `_readFile` / `_readFileBytes` static method above has a placeholder. Replace with:
   ```dart
   import 'dart:io' as io;
   static List<int> _readFileBytes(String path) {
     return io.File(path).readAsBytesSync();
   }
   ```

2. **[CORRECTION]** Analysis (4.5) noted missing method signatures. The engine above provides the complete constructor and public API.

3. **[CORRECTION]** Analysis (4.6) found the plan did not specify how adapters access Supabase. The engine handles all Supabase calls -- adapters are pure configuration/conversion objects that never touch Supabase directly.

4. **[CORRECTION]** Analysis (4.7) found the plan does not clarify soft-delete vs hard-delete in change_log. Soft-delete (setting `deleted_at`) fires an `AFTER UPDATE` trigger producing `operation = 'update'`. Hard delete fires `AFTER DELETE` producing `operation = 'delete'`. The push flow handles both correctly: `update` reads the local record (which includes `deleted_at`), and `delete` sends DELETE to Supabase.

5. **[CORRECTION]** Analysis (4.9) found `company_id` injection was unspecified. The engine receives `companyId` via constructor, matching the existing pattern where `SyncService.setCompanyContext()` stores `_companyId`. The foreground wires it from `AuthProvider.userProfile.companyId`; the background isolate reads it from `Supabase.instance.client.auth.currentUser` metadata.

6. **[CORRECTION]** Analysis (4.12) found progress tracking was missing. The engine provides an `onProgress` callback matching the existing `SyncAdapter.onProgressUpdate` pattern.

7. The `_pull()` method must call `_loadSyncedProjectIds()` before the table loop. Add this call at the start of `_pull()`, right after the trigger suppression line.

---

## Step 14: Barrel Exports for New Files

**File**: `lib/features/sync/engine/engine.dart`
**Action**: Create
**Depends on**: Steps 4, 9, 10, 11, 12, 13

```dart
export 'scope_type.dart';
export 'sync_engine.dart';
export 'sync_mutex.dart';
export 'change_tracker.dart';
export 'conflict_resolver.dart';
export 'integrity_checker.dart';
```

**File**: `lib/features/sync/adapters/adapters.dart`
**Action**: Modify (this file already exists)
**Depends on**: Step 5, Step 6

The existing `lib/features/sync/data/adapters/adapters.dart` exports the old adapters. Create a NEW barrel at the engine-level path:

**File**: `lib/features/sync/adapters/sync_adapters.dart`
**Action**: Create

```dart
export 'table_adapter.dart';
export 'type_converters.dart';
export 'project_adapter.dart';
export 'location_adapter.dart';
export 'contractor_adapter.dart';
export 'equipment_adapter.dart';
export 'bid_item_adapter.dart';
export 'personnel_type_adapter.dart';
export 'daily_entry_adapter.dart';
export 'photo_adapter.dart';
export 'entry_equipment_adapter.dart';
export 'entry_quantities_adapter.dart';
export 'entry_contractors_adapter.dart';
export 'entry_personnel_counts_adapter.dart';
export 'inspector_form_adapter.dart';
export 'form_response_adapter.dart';
export 'todo_item_adapter.dart';
export 'calculation_history_adapter.dart';
```

**File**: `lib/features/sync/config/config.dart`
**Action**: Create

```dart
export 'sync_registry.dart';
export 'sync_config.dart';
```

---

## Step 15: SyncResult Class Consolidation

**Action**: Decide which SyncResult to use
**Depends on**: Step 13

**[CORRECTION]** Analysis (4.6) found two `SyncResult` classes:
- `lib/services/sync_service.dart:73` (legacy, 112 lines)
- `lib/features/sync/domain/sync_adapter.dart:6` (clean architecture version)

The new engine defines its own `SyncEngineResult` class (Step 13) to avoid coupling to either. During the cutover section (not this section), the legacy `SyncResult` will be removed and `SyncProvider` will be updated to use `SyncEngineResult`. For now, both coexist.

**No code changes needed in this step** -- this is a documentation note for the cutover section.

---

## Step 16: sync_status Column Handling

**Action**: Document transition strategy
**Depends on**: Step 6

**[CORRECTION]** Analysis (4.7, 4.8) asks how `sync_status` columns on `daily_entries` and `photos` are handled.

**Resolution**: The `sync_status` column is:
1. Listed in `localOnlyColumns` on `DailyEntryAdapter` and `PhotoAdapter` -- so it is stripped from push payloads (same behavior as current `_convertForRemote`).
2. NOT set on pull -- the new engine does not set `sync_status = 'synced'` on pulled records. This is a deliberate simplification: the `change_log` trigger system replaces `sync_status` for tracking. The column remains in the schema but is no longer read by the engine.
3. The column is NOT removed in the v30 migration. A later migration (in the cutover section) will drop it after the old SyncService is removed.

**For the PhotoAdapter specifically**: `sync_status` is set to `'synced'` in Phase 3 of the three-phase push (`_pushPhotoThreePhase`). This is necessary because photo-related UI code still reads `sync_status` to show upload indicators.

---

## Summary: Files Created and Modified

### New Files (26 total)

| # | File | Purpose |
|---|------|---------|
| 1 | `lib/core/database/schema/sync_engine_tables.dart` | Schema definitions for 5 new tables + triggers |
| 2 | `lib/features/sync/engine/scope_type.dart` | ScopeType enum |
| 3 | `lib/features/sync/adapters/type_converters.dart` | TypeConverter interface + 4 implementations |
| 4 | `lib/features/sync/adapters/table_adapter.dart` | Abstract base class |
| 5 | `lib/features/sync/adapters/project_adapter.dart` | Projects adapter |
| 6 | `lib/features/sync/adapters/location_adapter.dart` | Locations adapter |
| 7 | `lib/features/sync/adapters/contractor_adapter.dart` | Contractors adapter |
| 8 | `lib/features/sync/adapters/equipment_adapter.dart` | Equipment adapter |
| 9 | `lib/features/sync/adapters/bid_item_adapter.dart` | Bid items adapter |
| 10 | `lib/features/sync/adapters/personnel_type_adapter.dart` | Personnel types adapter |
| 11 | `lib/features/sync/adapters/daily_entry_adapter.dart` | Daily entries adapter |
| 12 | `lib/features/sync/adapters/photo_adapter.dart` | Photos adapter (three-phase) |
| 13 | `lib/features/sync/adapters/entry_equipment_adapter.dart` | Entry equipment adapter |
| 14 | `lib/features/sync/adapters/entry_quantities_adapter.dart` | Entry quantities adapter |
| 15 | `lib/features/sync/adapters/entry_contractors_adapter.dart` | Entry contractors adapter (NEW sync) |
| 16 | `lib/features/sync/adapters/entry_personnel_counts_adapter.dart` | Entry personnel counts adapter (NEW sync) |
| 17 | `lib/features/sync/adapters/inspector_form_adapter.dart` | Inspector forms adapter (+BYTEA fix) |
| 18 | `lib/features/sync/adapters/form_response_adapter.dart` | Form responses adapter |
| 19 | `lib/features/sync/adapters/todo_item_adapter.dart` | Todo items adapter |
| 20 | `lib/features/sync/adapters/calculation_history_adapter.dart` | Calculation history adapter |
| 21 | `lib/features/sync/config/sync_registry.dart` | Adapter registry + dependency order |
| 22 | `lib/features/sync/config/sync_config.dart` | Engine configuration constants |
| 23 | `lib/features/sync/engine/sync_mutex.dart` | SQLite advisory lock |
| 24 | `lib/features/sync/engine/change_tracker.dart` | change_log reader/writer |
| 25 | `lib/features/sync/engine/conflict_resolver.dart` | LWW conflict resolution |
| 26 | `lib/features/sync/engine/integrity_checker.dart` | 4-hour count+max+checksum comparison |
| 27 | `lib/features/sync/engine/sync_engine.dart` | Push/pull orchestrator |
| 28 | `lib/features/sync/engine/engine.dart` | Barrel export |
| 29 | `lib/features/sync/adapters/sync_adapters.dart` | Barrel export |
| 30 | `lib/features/sync/config/config.dart` | Barrel export |
| 31 | `supabase/migrations/20260305000000_add_get_table_integrity_rpc.sql` | Supabase RPC for integrity checker |

### Modified Files (3 total)

| # | File | Change |
|---|------|--------|
| 1 | `lib/core/database/schema/schema.dart` | Add `sync_engine_tables.dart` export |
| 2 | `lib/core/database/database_service.dart` | Bump to v30, add migration, update onCreate |
| 3 | `lib/core/database/schema_verifier.dart` | Add 5 new tables to expectedSchema |

---

## Implementation Order (Dependency Graph)

```
Step 1  (schema definitions)     -- no deps
Step 4  (ScopeType + TypeConverters) -- no deps
Step 5  (TableAdapter base)      -- depends on Step 4
Step 6  (16 concrete adapters)   -- depends on Steps 4, 5
Step 7  (SyncRegistry)           -- depends on Steps 5, 6
Step 8  (SyncConfig)             -- no deps

Step 2  (Migration v30)          -- depends on Step 1
Step 3  (SchemaVerifier)         -- depends on Step 1

Step 9  (SyncMutex)              -- depends on Steps 1, 2
Step 10 (ChangeTracker)          -- depends on Steps 1, 2, 8
Step 11 (ConflictResolver)       -- depends on Steps 1, 2, 8
Step 12 (IntegrityChecker)       -- depends on Steps 7, 8
Step 13 (SyncEngine)             -- depends on ALL above
Step 14 (Barrel exports)         -- depends on ALL above
```

**Recommended batch order:**
1. Batch 1 (parallel): Steps 1, 4, 8
2. Batch 2 (parallel): Steps 2, 3, 5
3. Batch 3 (parallel): Step 6 (all 16 adapters)
4. Batch 4: Step 7
5. Batch 5 (parallel): Steps 9, 10, 11
6. Batch 6: Step 12
7. Batch 7: Step 13
8. Batch 8: Steps 14, 15, 16

---

## Corrections Summary

| ID | Source | Issue | Resolution |
|----|--------|-------|------------|
| C1 | Analysis 2.1 | Plan says "Replaces Completer-based mutex" | [CORRECTION] Current system uses boolean status guard, not Completer. Code already correct. |
| C2 | Analysis 2.1 | `entry_contractors` and `entry_personnel_counts` never synced | [CORRECTION] Noted in adapter steps 6.11 and 6.12. These are net-new sync capabilities. |
| C3 | Analysis 3.1 | `ScopeType` enum undefined | [CORRECTION] Defined in Step 4 with 4 variants instead of 3. |
| C4 | Analysis 3.2 | `synced_projects` creation unspecified | [CORRECTION] Created in Step 1 schema + Step 2 migration. Auto-populated for existing users. |
| C5 | Analysis 3.5 | `id_checksum` hashing unspecified | [CORRECTION] Step 12 uses djb2 algorithm in both Dart and SQL. |
| C6 | Analysis 3.9 | Plan mislabels pruning as "Decision 9" | [CORRECTION] Correctly referenced as "Decision 14" in Step 10. |
| C7 | Analysis 4.5 | `SyncEngine` constructor/API unspecified | [CORRECTION] Full constructor with 6 parameters defined in Step 13. |
| C8 | Analysis 4.6 | `SyncResult` class duplication | [CORRECTION] New `SyncEngineResult` class avoids coupling. Step 15 documents transition. |
| C9 | Analysis 4.7 | `sync_status` column transition | [CORRECTION] Step 16 documents: stripped from push, not set on pull, column kept for now. |
| C10 | Analysis 4.9 | `company_id` injection unspecified | [CORRECTION] Injected via `SyncEngine` constructor. Step 13 note 5. |
| C11 | Analysis 5.1 | `sync_queue` data migration | [CORRECTION] Step 2.4 includes migration of sync_queue -> change_log entries. |
| C12 | Analysis 5.2 | Trigger creation order | [CORRECTION] Step 2.4 creates tables before triggers. |

---

## Out of Scope for Section A

The following items from the plan are covered in OTHER sections (not this one):

- **UI components**: `sync_status_icon.dart`, `sync_toast.dart`, `sync_dashboard_screen.dart`, `conflict_viewer_screen.dart`, `project_selection_screen.dart` -- these are in the Presentation section.
- **Provider rewiring**: Updating `SyncProvider`, `SyncOrchestrator`, `SyncLifecycleManager` to use the new engine -- this is in the Cutover section.
- **BackgroundSyncHandler rewrite** -- this is in the Cutover section (depends on engine being fully tested).
- **Orphan Scanner** -- this is in the Integrity section (runs as part of the 4-hour integrity cycle but has Supabase Storage API dependencies).
- **Removing old code**: `SyncService`, `SupabaseSyncAdapter`, `queueOperation` callers -- this is in the Cutover section.
- **SyncStatusBanner replacement** -- this is in the Presentation section.
- **Supabase storage RLS fix** (NEW-1) -- this is in the Supabase section.
- **Settings redesign** -- this is in Section B.
