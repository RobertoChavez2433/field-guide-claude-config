# Sync System Rewrite — Bulletproof Implementation Plan

**Date**: 2026-03-05
**Source**: Derived from `.claude/plans/2026-03-04-sync-rewrite-and-settings-redesign.md` (original plan)
**Process**: 4 analysis agents verified against codebase → 5 writer agents produced detailed steps → merged here
**Sections**: A (architecture), B (schema/security), C1 (tests/phases 0-1), C2 (phases 2-3), D (phases 4-7)

---

## Table of Contents

- **Part 1: Architecture & Engine Design** (Section A)
  - Steps 1-12: Schema, migration, adapters, registry, config, mutex, change tracker, conflict resolver, integrity checker
- **Part 2: Schema, Security & Settings** (Section B)
  - Steps 1-11: Supabase migration, config, UserProfile expansion, SQLite v30, PreferencesService cleanup, consumer migration, PII cleanup, purge handler, settings redesign
- **Part 3: Test Infrastructure & Phases 0-1** (Section C1)
  - Test helpers, Phase 0 (schema + security verification), Phase 1 (change tracking foundation)
- **Part 4: Phases 2-3 — Engine & Adapters** (Section C2)
  - Phase 2 (adapter tests), Phase 3 (engine integration tests)
- **Part 5: Phases 4-7 & Cutover** (Section D)
  - Phase 4 (photo three-phase push), Phase 5 (integrity wiring), Phase 6 (UI + settings), Phase 7 (cutover + cleanup), Phase 7i (test file cleanup)

---

> **IMPORTANT: Incremental Build+Test Phasing**
>
> Implementation follows the original plan's incremental build+test approach. Each phase
> builds code, tests it, and must pass its completion gate before proceeding. Code from
> Part 1 (architecture definitions) serves as the design reference; actual file creation
> happens phase-by-phase.
>
> - Phase 0: Deploy Supabase schema + security --> test --> gate
> - Phase 1: Build SQLite schema + triggers --> test schema + triggers --> gate
> - Phase 2: Build engine core --> test engine --> gate
> - Phase 3: Build adapters --> test adapters --> gate
> - Phase 4: Build photo adapter --> test photo lifecycle --> gate
> - Phase 5: Build integrity checker integration --> test --> gate
> - Phase 6: Build UI + settings --> test UI --> gate
> - Phase 7: Cutover + final validation --> full regression --> merge

---

# Part 1: Architecture & Engine Design


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

This file defines the 6 new SQLite tables used by the sync engine: `sync_control`, `change_log`, `conflict_log`, `sync_lock`, `synced_projects`, and `sync_metadata`. These are separate from the existing `sync_tables.dart` (which holds `sync_queue` and `deletion_notifications`).

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

  // > **Population Strategy [FIX: A1]**: The `synced_projects` table is populated by user action —
  // > when the user picks or creates a project, it is inserted into `synced_projects`. The sync
  // > engine only syncs data for projects in this table. A hook must be added to the project
  // > creation/selection flow to call `INSERT OR IGNORE INTO synced_projects (project_id, synced_at) VALUES (?, ?)`.

  /// sync_metadata: stores per-table pull cursors and integrity check state.
  /// Keys: 'last_sync_time', 'last_pull_{tableName}' per table,
  ///        'last_integrity_check', 'integrity_check_result'
  static const String createSyncMetadataTable = '''
    CREATE TABLE IF NOT EXISTS sync_metadata (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
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
    await db.execute(SyncEngineTables.createSyncMetadataTable);

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
      await db.execute(SyncEngineTables.createSyncMetadataTable);

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
    'sync_metadata': [
      'key', 'value',
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

  /// Filter by project_id (for tables that get project_id via denormalization).
  /// [FIX: A2] After denormalization, viaEntry and viaProject generate identical SQL.
  /// Kept separate for semantic clarity about the entity relationship.
  ///
  /// Table has entry_id linking to daily_entries (e.g., photos, entry_equipment,
  /// entry_quantities, entry_contractors, entry_personnel_counts).
  /// NOTE: After junction table denormalization (project_id added to these tables),
  /// viaEntry generates the same SQL as viaProject. The enum variant is retained
  /// for semantic documentation of the table hierarchy.
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

**Application-level project_id stamping for junction tables**: When creating `entry_equipment`, `entry_quantities`, `entry_contractors`, or `entry_personnel_counts` records in the application layer, stamp `project_id` from the parent `daily_entry`. This ensures the denormalized column is always populated for new records. Example in the provider/repository layer:
```dart
final entry = await getEntry(entryId);
await db.insert('entry_equipment', {
  ...equipmentData,
  'project_id': entry['project_id'],  // Stamp from parent
});
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

  // -- Remote Config (ADV-62) --
  // Future enhancement: read sync config from an `app_config` Supabase table
  // to enable remote kill switch, dynamic batch sizes, etc.
  // For now, all values are hardcoded above with safe defaults.
  // The `app_config` table concept:
  //   CREATE TABLE app_config (key TEXT PRIMARY KEY, value JSONB NOT NULL, updated_at TIMESTAMPTZ DEFAULT NOW());
  // Client reads on startup, falls back to hardcoded values if unreachable.
  // Keys: 'sync_enabled', 'push_batch_limit', 'pull_page_size', 'integrity_check_interval'
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

  /// Force-clear locks. If lockedBy is provided, clear only that owner's lock.
  /// If null, clear only stale locks (older than staleLockTimeout).
  /// [FIX: C3] Made lockedBy optional for crash-recovery use from resetState().
  Future<void> forceReset([String? lockedBy]) async {
    if (lockedBy != null) {
      await _db.execute(
        'DELETE FROM sync_lock WHERE locked_by = ?',
        [lockedBy],
      );
    } else {
      final timeoutMinutes = SyncEngineConfig.staleLockTimeout.inMinutes;
      await _db.execute(
        "DELETE FROM sync_lock WHERE locked_at < strftime('%Y-%m-%dT%H:%M:%f', 'now', '-$timeoutMinutes minutes')",
      );
    }
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

  /// Increment retry count without marking as failed.
  /// Used when scheduling an in-cycle retry for transient errors.
  /// **[FIX: C2]** Added missing incrementRetry() method (called by _handlePushError but previously undefined).
  Future<void> incrementRetry(int changeId) async {
    await _db.execute(
      'UPDATE change_log SET retry_count = retry_count + 1 WHERE id = ?',
      [changeId],
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
    -- [FIX: C6] These junction tables get project_id via denormalization.
    -- Use project_id IN (...) rather than entry_id join chain.
    v_query := format(
      'SELECT COUNT(*), MAX(updated_at) FROM %I WHERE deleted_at IS NULL AND project_id IN (SELECT id FROM projects WHERE company_id = %L)',
      p_table_name, v_company_id
    );
  END IF;

  EXECUTE v_query INTO v_count, v_max_updated_at;
  v_count := COALESCE(v_count, 0);

  -- Compute id_checksum using djb2 algorithm matching Dart client
  -- **[FIX: C6]** Rebuilt ID checksum query to fix SQL syntax error (AND after ORDER BY)
  -- and align with denormalization decision. The WHERE clause is fully built before ORDER BY.
  FOR v_id IN
    EXECUTE CASE
      WHEN p_table_name = 'projects' THEN
        format(
          'SELECT id::TEXT FROM %I WHERE deleted_at IS NULL AND company_id = %L ORDER BY id',
          p_table_name, v_company_id
        )
      WHEN p_table_name IN ('locations', 'contractors', 'bid_items', 'personnel_types',
                             'daily_entries', 'inspector_forms', 'form_responses',
                             'todo_items', 'calculation_history') THEN
        format(
          'SELECT id::TEXT FROM %I WHERE deleted_at IS NULL AND project_id IN (SELECT id FROM projects WHERE company_id = %L) ORDER BY id',
          p_table_name, v_company_id
        )
      WHEN p_table_name = 'equipment' THEN
        format(
          'SELECT id::TEXT FROM %I WHERE deleted_at IS NULL AND contractor_id IN (SELECT id FROM contractors WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L)) ORDER BY id',
          p_table_name, v_company_id
        )
      ELSE -- photos, entry_equipment, entry_quantities, entry_contractors, entry_personnel_counts
        format(
          'SELECT id::TEXT FROM %I WHERE deleted_at IS NULL AND project_id IN (SELECT id FROM projects WHERE company_id = %L) ORDER BY id',
          p_table_name, v_company_id
        )
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

> **ENGINE BOOKKEEPING RULE**: All engine-internal writes that should NOT generate change_log entries
> (updating `remote_path`, `sync_status`, pruning processed change_log entries, updating sync cursors)
> must be wrapped in `sync_control.pulling='1'` / `finally pulling='0'`. This reuses the same trigger
> suppression mechanism as the pull flow. Without this, engine bookkeeping writes would generate
> spurious change_log entries that would be pushed back to Supabase in the next cycle.

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
      // [P2-7 fix] Clear column cache after each cycle to pick up schema changes
      _localColumnCache.clear();
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

      // **[FIX: H3]** Added inner retry loop. Previous code returned true from
      // _handlePushError but never re-executed the operation. The inner loop
      // retries within the same cycle (max 2 attempts per record).
      int processedInTable = 0;
      for (final change in changes) {
        bool succeeded = false;
        int retryAttempt = 0;
        const maxRetriesPerCycle = 2;

        while (!succeeded && retryAttempt < maxRetriesPerCycle) {
          try {
            if (change.operation == 'delete') {
              await _pushDelete(adapter, change);
            } else {
              await _pushUpsert(adapter, change);
            }
            await _changeTracker.markProcessed(change.id);
            pushed++;
            succeeded = true;
          } catch (e) {
            final shouldRetry = await _handlePushError(e, change);
            if (shouldRetry && retryAttempt < maxRetriesPerCycle - 1) {
              retryAttempt++;
              continue; // Retry once after backoff
            } else if (!shouldRetry) {
              errors++;
              errorMessages.add('${change.tableName}/${change.recordId}: $e');
            }
            break;
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
      // [P4-2 fix] Use upsert: true for idempotent re-uploads (prevents 409 on retry)
      final file = await _readFile(filePath);
      await supabase.storage
          .from('entry-photos')
          .uploadBinary(expectedPath, file,
            fileOptions: const FileOptions(upsert: true));
      remotePath = expectedPath;
    }

    // Phase 2: Upsert metadata with FRESH remote_path from Phase 1
    payload['remote_path'] = remotePath;
    await supabase.from('photos').upsert(payload);

    // Phase 3: Mark local as synced (update remote_path)
    // RULE: All engine bookkeeping writes must suppress triggers via pulling='1'
    // to prevent change_log entries for engine-internal state updates.
    await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
    try {
      await db.update(
        'photos',
        {'remote_path': remotePath, 'sync_status': 'synced'},
        where: 'id = ?',
        whereArgs: [change.recordId],
      );
    } finally {
      await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
    }
  }

  /// Read file bytes. Isolated for testability.
  Future<List<int>> _readFile(String path) async {
    final file = await compute(_readFileBytes, path);
    return file;
  }

  /// **[FIX: C4]** Corrected from Java syntax to dart:io File.
  static List<int> _readFileBytes(String path) {
    return File(path).readAsBytesSync(); // dart:io File
  }

  /// Handle push errors with retry/backoff/auth-refresh logic.
  /// Returns true if the error was handled (retry scheduled), false if permanent.
  ///
  /// **[FIX: C5]** PostgrestException.code contains PostgREST codes (PGRST*), not HTTP status
  /// codes. Updated all checks from HTTP status strings to PostgREST error codes.
  Future<bool> _handlePushError(Object error, ChangeEntry change) async {
    if (error is PostgrestException) {
      final code = error.code;

      // Auth error: PostgREST JWT/auth codes -- attempt token refresh, then retry ONCE
      if (code == 'PGRST301' || code == 'PGRST302' || error.message.contains('JWT')) {
        final refreshed = await _handleAuthError();
        if (refreshed) {
          // Auth refreshed -- retry the SAME ChangeEntry once (max 2 attempts per record per cycle)
          // Do NOT increment retry_count for auth failures
          return true; // Caller retries this change entry
        }
        // Refresh failed -- abort entire cycle
        throw StateError('Auth refresh failed, aborting sync');
      }

      // Rate-limit / server overload: Retryable with within-cycle exponential backoff
      // Maximum 2 attempts per record per cycle: delay, retry once, then mark failed
      // PostgREST 5xx codes or rate-limit messages
      if (error.message.contains('rate limit') ||
          error.message.contains('too many') ||
          code?.startsWith('PGRST5') == true) {
        final delay = Duration(
          milliseconds: (SyncEngineConfig.retryBaseDelay.inMilliseconds *
              (1 << change.retryCount.clamp(0, 4)))
              .clamp(0, SyncEngineConfig.retryMaxDelay.inMilliseconds),
        );
        await Future.delayed(delay);
        // After delay, return true to signal ONE retry attempt.
        // If the retry also fails, the second call to _handlePushError will markFailed.
        if (change.retryCount == 0) {
          await _changeTracker.incrementRetry(change.id);
          return true; // Retry once
        }
        // Second failure -- mark as failed, do not retry again this cycle
        await _changeTracker.markFailed(change.id, 'Retryable: $code (max retries reached)');
        return false;
      }

      // Permanent errors:
      // - Constraint violation (PGRST205/PGRST206) or unique/FK message
      // - Permission denied (PGRST304 or 'permission denied')
      // - Not found (PGRST116 or 'not found')
      await _changeTracker.markFailed(change.id, 'Permanent: ${error.message}');
      return false;
    }

    // [P4-3 fix] StorageException handling for photo uploads
    if (error is StorageException) {
      final statusCode = error.statusCode;
      if (statusCode == '409') {
        // 409 Conflict: File already uploaded (idempotent -- skip)
        return true;
      }
      if (statusCode == '403') {
        // 403 Forbidden: Permanent (wrong bucket/path permissions)
        await _changeTracker.markFailed(change.id, 'Storage permanent: 403 Forbidden');
        return false;
      }
      if (statusCode == '413') {
        // 413 Payload Too Large: Permanent (file exceeds size limit)
        await _changeTracker.markFailed(change.id, 'Storage permanent: 413 file too large');
        return false;
      }
      // 5xx: Retryable storage errors
      if (change.retryCount == 0) {
        await _changeTracker.incrementRetry(change.id);
        return true;
      }
      await _changeTracker.markFailed(change.id, 'Storage error: $statusCode (max retries reached)');
      return false;
    }

    // Network errors: Retryable with delay + one retry (max 2 attempts per record per cycle)
    if (error.toString().contains('SocketException') ||
        error.toString().contains('TimeoutException')) {
      final delay = Duration(
        milliseconds: (SyncEngineConfig.retryBaseDelay.inMilliseconds *
            (1 << change.retryCount.clamp(0, 4)))
            .clamp(0, SyncEngineConfig.retryMaxDelay.inMilliseconds),
      );
      await Future.delayed(delay);
      if (change.retryCount == 0) {
        await _changeTracker.incrementRetry(change.id);
        return true; // Retry once
      }
      await _changeTracker.markFailed(change.id, 'Network error (max retries reached)');
      return false;
    }

    // Unknown error -- permanent, no retry
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
    // [P2-5 fix] Load synced project IDs BEFORE starting pull, not just in pseudocode
    await _loadSyncedProjectIds();

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
          // [FIX: H2] Reload scope IDs after pulling tables that expand the scope.
          // Pulling contractors adds new rows to the local DB which broadens the
          // contractor_id filter for equipment. Pulling daily_entries could add
          // project_id references used by viaEntry junction tables.
          if (adapter.tableName == 'contractors' || adapter.tableName == 'daily_entries') {
            await _loadSyncedProjectIds();
          }
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
  ///
  /// [FIX: C1/H1] Empty-list guards added: inFilter([]) sends no WHERE clause and returns
  /// ALL rows. Each case now short-circuits with a guaranteed-empty filter when the ID
  /// lists are empty (user has no synced projects/contractors yet).
  PostgrestFilterBuilder _applyScopeFilter(
    PostgrestFilterBuilder query,
    TableAdapter adapter,
  ) {
    switch (adapter.scopeType) {
      case ScopeType.direct:
        // projects: filter by company_id
        return query.eq('company_id', companyId);
      case ScopeType.viaProject:
      case ScopeType.viaEntry:
        // [FIX: C1/H1] Both use project_id after denormalization. Guard empty list.
        // viaEntry generates same SQL as viaProject after junction-table denormalization
        // (project_id added directly to junction tables; see ScopeType.viaEntry doc).
        if (_syncedProjectIds.isEmpty) return query.eq('id', '___nonexistent___');
        return query.inFilter('project_id', _syncedProjectIds);
      case ScopeType.viaContractor:
        // equipment: filter by contractor_id in synced projects
        if (_syncedContractorIds.isEmpty) return query.eq('id', '___nonexistent___');
        return query.inFilter('contractor_id', _syncedContractorIds);
    }
  }

  // Cached project/contractor IDs for pull scoping
  List<String> _syncedProjectIds = [];
  List<String> _syncedContractorIds = [];

  /// Load synced project IDs and related contractor IDs before pull.
  /// Must be called at the start of each pull cycle, and after pulling
  /// `contractors` or `daily_entries` to expand scope for subsequent tables.
  Future<void> _loadSyncedProjectIds() async {
    final rows = await db.query('synced_projects');
    _syncedProjectIds = rows.map((r) => r['project_id'] as String).toList();

    // Also load contractor IDs for equipment scoping
    // [FIX: H10/P1] Added deleted_at IS NULL to exclude soft-deleted contractors.
    if (_syncedProjectIds.isNotEmpty) {
      final contractors = await db.query(
        'contractors',
        columns: ['id'],
        where: 'deleted_at IS NULL AND project_id IN (${_syncedProjectIds.map((_) => '?').join(',')})',
        whereArgs: _syncedProjectIds,
      );
      _syncedContractorIds = contractors.map((r) => r['id'] as String).toList();
    } else {
      _syncedContractorIds = [];
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
| 1 | `lib/core/database/schema/sync_engine_tables.dart` | Schema definitions for 6 new tables + triggers |
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
| 3 | `lib/core/database/schema_verifier.dart` | Add 6 new tables to expectedSchema |

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

## Tables Outside New Engine Scope

The following tables are synced outside the new engine's scope. They do NOT get adapters or triggers:

- **`companies`** -- pulled by `pullCompanyMembers()`
- **`user_profiles`** -- pulled by `UserProfileSyncDatasource`
- **`company_join_requests`** -- pulled by orchestrator
- **`user_certifications`** (NEW) -- synced via `UserProfileSyncDatasource` alongside user_profiles

These tables have their own dedicated sync paths that predate the engine. They are intentionally excluded from the adapter registry and do not participate in the change_log/trigger system.

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

---

# Part 2: Schema, Security & Settings


## Pre-requisites

Before any of this section can be implemented:

1. **Branch**: Work on the existing `fix/sync-dns-resilience` branch or a dedicated `feature/section-b-schema-security` branch
2. **Current DB version**: SQLite is at v29 (`lib/core/database/database_service.dart:54`). This section bumps it to v30.
3. **Latest Supabase migration**: `20260304200000_drop_sync_status_from_supabase.sql`. New migration(s) must use a timestamp after `20260304200000`.
4. **No uncommitted schema changes**: Verify `git status` shows no pending changes to `database_service.dart` or `supabase/migrations/`.
5. **Section A (Sync Engine Core)** does NOT need to be complete first. Section B is independently deployable. However, the `sync_control`, `change_log`, `conflict_log`, `sync_lock`, and `synced_projects` tables in the v30 SQLite migration are shared with Section A. If Section A has already created them, skip those CREATE TABLE statements.

---

## Implementation Order Summary

The steps below are ordered by dependency:

1. **Step 1**: Supabase migration SQL file (all server-side schema + security changes in one atomic migration)
2. **Step 2**: `supabase/config.toml` -- secure_password_change
3. **Step 3**: UserProfile model expansion (add 4 new fields)
4. **Step 4**: SQLite v30 migration (schema tables + `database_service.dart`)
5. **Step 5**: PreferencesService dead code removal
6. **Step 6**: Consumer migration (PreferencesService -> AuthProvider.userProfile)
7. **Step 7**: PII cleanup from SharedPreferences
8. **Step 8**: Purge handler in SyncService
9. **Step 9**: Settings screen redesign
10. **Step 10**: Delete orphaned EditInspectorDialog widget
11. **Step 11**: Verification checklist

---

## Step 1: Supabase Migration -- Schema Alignment + Security Fixes

**File**: `supabase/migrations/20260305000000_schema_alignment_and_security.sql`
**Action**: Create
**Depends on**: Nothing (first step)

This is the complete, single-file Supabase migration. Every SQL statement below goes into this one file, in this exact order.

### 1.1 Migration ordering rationale

The SQL is ordered to satisfy dependencies:
- GAP-9 (inspector_forms soft-delete) MUST come before `get_table_integrity` RPC (which filters by `deleted_at IS NULL` on all 16 tables)
- `is_approved_admin()` function MUST come before admin RPC rewrites
- `user_certifications` table MUST exist before cert_number data migration
- Storage RLS fix is first because it is a BLOCKING security fix

### 1.2 Complete SQL file content

```sql
-- Migration: Schema alignment, security fixes, and profile expansion
-- Date: 2026-03-05
-- Covers: NEW-1 (Storage RLS), NEW-6 (lock_created_by), NEW-7 (Admin RPCs),
--         GAP-9 (inspector_forms soft-delete), GAP-10 (updated_at triggers),
--         GAP-19 (secure_password_change — config.toml, not SQL),
--         ADV-2 (enforce_insert_updated_at), ADV-9 (NOT NULL project_id),
--         ADV-15 (stamp_updated_by), ADV-22/23 (get_table_integrity),
--         ADV-25 (is_approved_admin), ADV-31 (calculation_history updated_at),
--         Decision 12 (profile expansion, user_certifications)

-- ============================================================================
-- PART 0: BLOCKING SECURITY FIX — Storage RLS (NEW-1)
-- ============================================================================
-- Current policies use (storage.foldername(name))[1] which matches 'entries'
-- (a constant string), not the companyId. Upload path is:
--   entries/{companyId}/{entryId}/{filename}
-- So [1]='entries', [2]=companyId, [3]=entryId.
-- Fix: change [1] to [2] in all three policies.

DROP POLICY IF EXISTS "company_photo_select" ON storage.objects;
CREATE POLICY "company_photo_select" ON storage.objects
  FOR SELECT TO authenticated
  USING (bucket_id = 'entry-photos'
    AND (storage.foldername(name))[2] = get_my_company_id()::text);

DROP POLICY IF EXISTS "company_photo_insert" ON storage.objects;
CREATE POLICY "company_photo_insert" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'entry-photos'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
    AND NOT is_viewer());

DROP POLICY IF EXISTS "company_photo_delete" ON storage.objects;
CREATE POLICY "company_photo_delete" ON storage.objects
  FOR DELETE TO authenticated
  USING (bucket_id = 'entry-photos'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
    AND NOT is_viewer());

-- ============================================================================
-- PART 1: GAP-9 — Add soft-delete columns to inspector_forms on Supabase
-- ============================================================================
-- inspector_forms has deleted_at/deleted_by on SQLite (toolbox_tables.dart:24-25)
-- but is MISSING them on Supabase. Required before get_table_integrity RPC.

ALTER TABLE inspector_forms ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE inspector_forms ADD COLUMN IF NOT EXISTS deleted_by UUID REFERENCES auth.users(id);

CREATE INDEX IF NOT EXISTS idx_inspector_forms_deleted_at ON inspector_forms(deleted_at);

-- Update purge function to include inspector_forms
CREATE OR REPLACE FUNCTION purge_soft_deleted_records()
RETURNS void
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  -- Leaf junction tables (deepest children first)
  -- [FIX: H5] entry_personnel is ACTIVE (26 file references, has datasources).
  -- Must remain in purge function despite being described as "legacy" elsewhere.
  DELETE FROM entry_quantities WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM entry_equipment WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM entry_personnel WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM entry_personnel_counts WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM entry_contractors WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Photos (depend on entries and projects)
  DELETE FROM photos WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Toolbox tables (including inspector_forms)
  DELETE FROM form_responses WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM inspector_forms WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM todo_items WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM calculation_history WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Personnel types
  DELETE FROM personnel_types WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Bid items
  DELETE FROM bid_items WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Equipment (depends on contractors)
  DELETE FROM equipment WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Daily entries (depend on projects)
  DELETE FROM daily_entries WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Contractors (depend on projects)
  DELETE FROM contractors WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Locations (depend on projects)
  DELETE FROM locations WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Projects (top-level parent -- deleted last)
  DELETE FROM projects WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  RAISE LOG 'purge_soft_deleted_records: completed at %', NOW();
END;
$$;

-- ============================================================================
-- PART 2: GAP-10 — updated_at triggers for entry_contractors & entry_personnel_counts
-- ============================================================================
-- [CORRECTION] The updated_at COLUMNS already exist on Supabase (added in
-- multi_tenant_foundation.sql:1048,1050). The ALTER TABLE ADD COLUMN is
-- idempotent (IF NOT EXISTS) so it's safe but redundant. The TRIGGERS however
-- do NOT exist yet — those are what's actually needed.

-- Idempotent column adds (no-op if already exist)
ALTER TABLE entry_contractors ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE entry_personnel_counts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Backfill any NULL updated_at values from created_at
UPDATE entry_contractors SET updated_at = created_at WHERE updated_at IS NULL;
UPDATE entry_personnel_counts SET updated_at = created_at WHERE updated_at IS NULL;

-- Create the missing triggers (these are the actual fix)
-- [FIX: C8] All trigger creation must be idempotent (DROP IF EXISTS before CREATE).
-- Matches existing pattern in multi_tenant_foundation.sql lines 367-433.
DROP TRIGGER IF EXISTS update_entry_contractors_updated_at ON entry_contractors;
CREATE TRIGGER update_entry_contractors_updated_at
  BEFORE UPDATE ON entry_contractors
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_entry_personnel_counts_updated_at ON entry_personnel_counts;
CREATE TRIGGER update_entry_personnel_counts_updated_at
  BEFORE UPDATE ON entry_personnel_counts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PART 3: ADV-31 — calculation_history.updated_at NOT NULL + default
-- ============================================================================

UPDATE calculation_history SET updated_at = COALESCE(updated_at, created_at, NOW())
WHERE updated_at IS NULL;
ALTER TABLE calculation_history ALTER COLUMN updated_at SET NOT NULL;
ALTER TABLE calculation_history ALTER COLUMN updated_at SET DEFAULT NOW();

-- ============================================================================
-- PART 4: ADV-33 — form_responses.form_id FK alignment
-- ============================================================================
-- [CORRECTION] This was ALREADY fixed in catchup_v23.sql:247,253-266.
-- The DROP NOT NULL and DROP CONSTRAINT were already applied.
-- Including idempotent versions here for safety — these are no-ops.

ALTER TABLE form_responses ALTER COLUMN form_id DROP NOT NULL;
ALTER TABLE form_responses DROP CONSTRAINT IF EXISTS form_responses_form_id_fkey;

-- ============================================================================
-- PART 5: ADV-9 — NOT NULL constraint on project_id for toolbox tables
-- ============================================================================

-- Step 1: Backfill orphaned records
-- [REVIEWED] inspector_forms has no entry_id column. Use form_responses join instead.
UPDATE inspector_forms
SET created_by_user_id = COALESCE(
  (SELECT DISTINCT fr.created_by_user_id
   FROM form_responses fr
   WHERE fr.form_id = inspector_forms.id
   LIMIT 1),
  (SELECT up.id FROM user_profiles up
   WHERE up.company_id = (SELECT p.company_id FROM projects p WHERE p.id = inspector_forms.project_id)
   LIMIT 1)
)
WHERE created_by_user_id IS NULL;

UPDATE todo_items
SET project_id = COALESCE(
  (SELECT de.project_id FROM daily_entries de WHERE de.id = todo_items.entry_id),
  (SELECT p.id FROM projects p WHERE p.company_id = (
    SELECT up.company_id FROM user_profiles up WHERE up.id = todo_items.created_by_user_id
  ) ORDER BY p.created_at LIMIT 1)
)
WHERE project_id IS NULL;

UPDATE calculation_history
SET project_id = COALESCE(
  (SELECT de.project_id FROM daily_entries de WHERE de.id = calculation_history.entry_id),
  (SELECT p.id FROM projects p WHERE p.company_id = (
    SELECT up.company_id FROM user_profiles up WHERE up.id = calculation_history.created_by_user_id
  ) ORDER BY p.created_at LIMIT 1)
)
WHERE project_id IS NULL;

-- Step 2: Hard-delete any remaining orphans that couldn't be backfilled
DELETE FROM inspector_forms WHERE project_id IS NULL;
DELETE FROM todo_items WHERE project_id IS NULL;
DELETE FROM calculation_history WHERE project_id IS NULL;

-- Step 3: Add NOT NULL constraints
ALTER TABLE inspector_forms ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE todo_items ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE calculation_history ALTER COLUMN project_id SET NOT NULL;

-- ============================================================================
-- PART 6: NEW-7 + ADV-25 — is_approved_admin() and Admin RPC rewrites
-- ============================================================================
-- All 6 admin RPCs currently check `role = 'admin'` but NOT `status = 'approved'`.
-- They also lack `SET search_path = public`.
-- Fix: create is_approved_admin() helper, rewrite all 6 RPCs.

CREATE OR REPLACE FUNCTION is_approved_admin()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM user_profiles
    WHERE id = auth.uid() AND role = 'admin' AND status = 'approved'
  )
$$ LANGUAGE sql SECURITY DEFINER STABLE SET search_path = public;

-- 6a: approve_join_request
CREATE OR REPLACE FUNCTION approve_join_request(
  request_id UUID,
  assigned_role TEXT DEFAULT 'inspector'
) RETURNS VOID AS $$
DECLARE
  v_company_id UUID;
  v_target_user_id UUID;
BEGIN
  -- is_approved_admin() MUST be first
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Not an approved admin';
  END IF;

  SELECT jr.company_id, jr.user_id INTO v_company_id, v_target_user_id
  FROM company_join_requests jr
  WHERE jr.id = request_id AND jr.status = 'pending';

  IF NOT FOUND THEN RAISE EXCEPTION 'Request not found or not pending'; END IF;
  IF v_company_id != get_my_company_id() THEN RAISE EXCEPTION 'Not your company'; END IF;
  IF assigned_role NOT IN ('inspector', 'engineer', 'viewer')
    THEN RAISE EXCEPTION 'Invalid role'; END IF;

  UPDATE company_join_requests
  SET status = 'approved', resolved_at = now(), resolved_by = auth.uid()
  WHERE id = request_id;

  UPDATE user_profiles
  SET company_id = v_company_id, role = assigned_role, status = 'approved', updated_at = now()
  WHERE id = v_target_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 6b: reject_join_request
CREATE OR REPLACE FUNCTION reject_join_request(request_id UUID)
RETURNS VOID AS $$
DECLARE
  v_company_id UUID;
BEGIN
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Not an approved admin';
  END IF;

  SELECT company_id INTO v_company_id
  FROM company_join_requests WHERE id = request_id AND status = 'pending';

  IF NOT FOUND THEN RAISE EXCEPTION 'Request not found or not pending'; END IF;
  IF v_company_id != get_my_company_id() THEN RAISE EXCEPTION 'Not your company'; END IF;

  UPDATE company_join_requests
  SET status = 'rejected', resolved_at = now(), resolved_by = auth.uid()
  WHERE id = request_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 6c: update_member_role
CREATE OR REPLACE FUNCTION update_member_role(target_user_id UUID, new_role TEXT)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_company_id UUID;
  v_target_company_id UUID;
  v_admin_count INTEGER;
BEGIN
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Not an approved admin';
  END IF;

  v_company_id := get_my_company_id();
  IF v_company_id IS NULL THEN RAISE EXCEPTION 'No company'; END IF;

  IF new_role NOT IN ('inspector', 'engineer', 'viewer')
    THEN RAISE EXCEPTION 'Invalid role'; END IF;

  SELECT company_id INTO v_target_company_id FROM user_profiles WHERE id = target_user_id;
  IF v_target_company_id != v_company_id THEN RAISE EXCEPTION 'User not in your company'; END IF;

  -- Last-admin guard: if demoting an admin, ensure at least one admin remains
  IF (SELECT role FROM user_profiles WHERE id = target_user_id) = 'admin' THEN
    SELECT count(*) INTO v_admin_count FROM user_profiles
      WHERE company_id = v_company_id AND role = 'admin' AND status = 'approved';
    IF v_admin_count <= 1 THEN RAISE EXCEPTION 'Cannot remove last admin'; END IF;
  END IF;

  UPDATE user_profiles
  SET role = new_role, updated_at = now()
  WHERE id = target_user_id;
END;
$$;

-- 6d: deactivate_member
CREATE OR REPLACE FUNCTION deactivate_member(target_user_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_company_id UUID;
  v_target_company_id UUID;
  v_admin_count INTEGER;
BEGIN
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Not an approved admin';
  END IF;

  v_company_id := get_my_company_id();
  IF v_company_id IS NULL THEN RAISE EXCEPTION 'No company'; END IF;

  SELECT company_id INTO v_target_company_id FROM user_profiles WHERE id = target_user_id;
  IF v_target_company_id != v_company_id THEN RAISE EXCEPTION 'User not in your company'; END IF;

  -- Last-admin guard
  IF (SELECT role FROM user_profiles WHERE id = target_user_id) = 'admin' THEN
    SELECT count(*) INTO v_admin_count FROM user_profiles
      WHERE company_id = v_company_id AND role = 'admin' AND status = 'approved';
    IF v_admin_count <= 1 THEN RAISE EXCEPTION 'Cannot deactivate last admin'; END IF;
  END IF;

  UPDATE user_profiles
  SET status = 'deactivated', updated_at = now()
  WHERE id = target_user_id;
END;
$$;

-- 6e: reactivate_member
CREATE OR REPLACE FUNCTION reactivate_member(target_user_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_company_id UUID;
  v_target_company_id UUID;
BEGIN
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Not an approved admin';
  END IF;

  v_company_id := get_my_company_id();
  IF v_company_id IS NULL THEN RAISE EXCEPTION 'No company'; END IF;

  SELECT company_id INTO v_target_company_id FROM user_profiles WHERE id = target_user_id;
  IF v_target_company_id != v_company_id THEN RAISE EXCEPTION 'User not in your company'; END IF;

  UPDATE user_profiles
  SET status = 'approved', updated_at = now()
  WHERE id = target_user_id;
END;
$$;

-- 6f: promote_to_admin
CREATE OR REPLACE FUNCTION promote_to_admin(target_user_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_company_id UUID;
  v_target_company_id UUID;
  v_target_status TEXT;
BEGIN
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Not an approved admin';
  END IF;

  v_company_id := get_my_company_id();
  IF v_company_id IS NULL THEN RAISE EXCEPTION 'No company'; END IF;

  SELECT company_id, status INTO v_target_company_id, v_target_status
    FROM user_profiles WHERE id = target_user_id;
  IF v_target_company_id != v_company_id THEN RAISE EXCEPTION 'User not in your company'; END IF;
  IF v_target_status != 'approved' THEN RAISE EXCEPTION 'User must be approved first'; END IF;

  UPDATE user_profiles
  SET role = 'admin', updated_at = now()
  WHERE id = target_user_id;
END;
$$;

-- ============================================================================
-- PART 7: NEW-6 + ADV-24 — lock_created_by() trigger on UPDATE
-- ============================================================================
-- This is a SEPARATE function from the existing enforce_created_by() (INSERT).
-- lock_created_by() fires BEFORE UPDATE to prevent created_by_user_id erasure.
-- COALESCE logic: preserves original; allows first-time stamping on legacy
-- records (NULL); prevents erasure to NULL.

CREATE OR REPLACE FUNCTION lock_created_by()
RETURNS TRIGGER AS $$
BEGIN
  NEW.created_by_user_id = COALESCE(OLD.created_by_user_id, NEW.created_by_user_id, auth.uid());
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Apply BEFORE UPDATE triggers on all 16 synced data tables
-- [FIX: C8] DROP IF EXISTS before each CREATE for idempotency.
DROP TRIGGER IF EXISTS lock_created_by_projects ON projects;
CREATE TRIGGER lock_created_by_projects
  BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_locations ON locations;
CREATE TRIGGER lock_created_by_locations
  BEFORE UPDATE ON locations FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_contractors ON contractors;
CREATE TRIGGER lock_created_by_contractors
  BEFORE UPDATE ON contractors FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_equipment ON equipment;
CREATE TRIGGER lock_created_by_equipment
  BEFORE UPDATE ON equipment FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_bid_items ON bid_items;
CREATE TRIGGER lock_created_by_bid_items
  BEFORE UPDATE ON bid_items FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_personnel_types ON personnel_types;
CREATE TRIGGER lock_created_by_personnel_types
  BEFORE UPDATE ON personnel_types FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_daily_entries ON daily_entries;
CREATE TRIGGER lock_created_by_daily_entries
  BEFORE UPDATE ON daily_entries FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_photos ON photos;
CREATE TRIGGER lock_created_by_photos
  BEFORE UPDATE ON photos FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_entry_equipment ON entry_equipment;
CREATE TRIGGER lock_created_by_entry_equipment
  BEFORE UPDATE ON entry_equipment FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_entry_quantities ON entry_quantities;
CREATE TRIGGER lock_created_by_entry_quantities
  BEFORE UPDATE ON entry_quantities FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_entry_contractors ON entry_contractors;
CREATE TRIGGER lock_created_by_entry_contractors
  BEFORE UPDATE ON entry_contractors FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_entry_personnel_counts ON entry_personnel_counts;
CREATE TRIGGER lock_created_by_entry_personnel_counts
  BEFORE UPDATE ON entry_personnel_counts FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_inspector_forms ON inspector_forms;
CREATE TRIGGER lock_created_by_inspector_forms
  BEFORE UPDATE ON inspector_forms FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_form_responses ON form_responses;
CREATE TRIGGER lock_created_by_form_responses
  BEFORE UPDATE ON form_responses FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_todo_items ON todo_items;
CREATE TRIGGER lock_created_by_todo_items
  BEFORE UPDATE ON todo_items FOR EACH ROW EXECUTE FUNCTION lock_created_by();
DROP TRIGGER IF EXISTS lock_created_by_calculation_history ON calculation_history;
CREATE TRIGGER lock_created_by_calculation_history
  BEFORE UPDATE ON calculation_history FOR EACH ROW EXECUTE FUNCTION lock_created_by();

-- ============================================================================
-- PART 8: ADV-2 — enforce_insert_updated_at() anti-spoofing trigger
-- ============================================================================
-- Forces updated_at = NOW() on INSERT so clients cannot send stale timestamps.

CREATE OR REPLACE FUNCTION enforce_insert_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Apply BEFORE INSERT triggers on all 16 synced data tables
-- [FIX: C8] DROP IF EXISTS before each CREATE for idempotency.
DROP TRIGGER IF EXISTS enforce_insert_updated_at_projects ON projects;
CREATE TRIGGER enforce_insert_updated_at_projects
  BEFORE INSERT ON projects FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_locations ON locations;
CREATE TRIGGER enforce_insert_updated_at_locations
  BEFORE INSERT ON locations FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_contractors ON contractors;
CREATE TRIGGER enforce_insert_updated_at_contractors
  BEFORE INSERT ON contractors FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_equipment ON equipment;
CREATE TRIGGER enforce_insert_updated_at_equipment
  BEFORE INSERT ON equipment FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_bid_items ON bid_items;
CREATE TRIGGER enforce_insert_updated_at_bid_items
  BEFORE INSERT ON bid_items FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_personnel_types ON personnel_types;
CREATE TRIGGER enforce_insert_updated_at_personnel_types
  BEFORE INSERT ON personnel_types FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_daily_entries ON daily_entries;
CREATE TRIGGER enforce_insert_updated_at_daily_entries
  BEFORE INSERT ON daily_entries FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_photos ON photos;
CREATE TRIGGER enforce_insert_updated_at_photos
  BEFORE INSERT ON photos FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_entry_equipment ON entry_equipment;
CREATE TRIGGER enforce_insert_updated_at_entry_equipment
  BEFORE INSERT ON entry_equipment FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_entry_quantities ON entry_quantities;
CREATE TRIGGER enforce_insert_updated_at_entry_quantities
  BEFORE INSERT ON entry_quantities FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_entry_contractors ON entry_contractors;
CREATE TRIGGER enforce_insert_updated_at_entry_contractors
  BEFORE INSERT ON entry_contractors FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_entry_personnel_counts ON entry_personnel_counts;
CREATE TRIGGER enforce_insert_updated_at_entry_personnel_counts
  BEFORE INSERT ON entry_personnel_counts FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_inspector_forms ON inspector_forms;
CREATE TRIGGER enforce_insert_updated_at_inspector_forms
  BEFORE INSERT ON inspector_forms FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_form_responses ON form_responses;
CREATE TRIGGER enforce_insert_updated_at_form_responses
  BEFORE INSERT ON form_responses FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_todo_items ON todo_items;
CREATE TRIGGER enforce_insert_updated_at_todo_items
  BEFORE INSERT ON todo_items FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
DROP TRIGGER IF EXISTS enforce_insert_updated_at_calculation_history ON calculation_history;
CREATE TRIGGER enforce_insert_updated_at_calculation_history
  BEFORE INSERT ON calculation_history FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();

-- ============================================================================
-- PART 9: ADV-15 — Server-side stamp_updated_by trigger for daily_entries
-- ============================================================================

CREATE OR REPLACE FUNCTION stamp_updated_by()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_TABLE_NAME = 'daily_entries' THEN
    NEW.updated_by_user_id = auth.uid();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

DROP TRIGGER IF EXISTS stamp_updated_by_daily_entries ON daily_entries;
CREATE TRIGGER stamp_updated_by_daily_entries
  BEFORE UPDATE ON daily_entries FOR EACH ROW EXECUTE FUNCTION stamp_updated_by();

-- ============================================================================
-- PART 10: ADV-22 + ADV-23 — get_table_integrity RPC with id_checksum
-- ============================================================================
-- NOTE: This RPC uses `deleted_at IS NULL` on ALL tables. GAP-9 (PART 1 above)
-- must have already added deleted_at to inspector_forms before this works.

CREATE OR REPLACE FUNCTION get_table_integrity(p_table_name TEXT)
RETURNS TABLE (
  row_count BIGINT,
  max_updated_at TIMESTAMPTZ,
  id_checksum BIGINT
) AS $$
DECLARE
  v_company_id UUID;
  v_sql TEXT;
BEGIN
  v_company_id := get_my_company_id();
  IF v_company_id IS NULL THEN
    RAISE EXCEPTION 'No company context';
  END IF;

  -- Validate table name against allowlist to prevent SQL injection
  IF p_table_name NOT IN (
    'projects', 'locations', 'contractors', 'equipment', 'bid_items',
    'personnel_types', 'daily_entries', 'photos', 'entry_equipment',
    'entry_quantities', 'entry_contractors', 'entry_personnel_counts',
    'inspector_forms', 'form_responses', 'todo_items', 'calculation_history'
  ) THEN
    RAISE EXCEPTION 'Invalid table name: %', p_table_name;
  END IF;

  IF p_table_name = 'projects' THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE company_id = %L AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSIF p_table_name IN ('locations', 'contractors', 'bid_items', 'personnel_types', 'daily_entries',
                          'inspector_forms', 'todo_items', 'calculation_history') THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSIF p_table_name = 'equipment' THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE contractor_id IN (SELECT id FROM contractors WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L)) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSIF p_table_name = 'photos' THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE entry_id IN (SELECT id FROM daily_entries WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L)) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSIF p_table_name = 'form_responses' THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSE
    -- entry_equipment, entry_quantities, entry_contractors, entry_personnel_counts
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE entry_id IN (SELECT id FROM daily_entries WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L)) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  END IF;

  RETURN QUERY EXECUTE v_sql;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE SET search_path = public;

-- ============================================================================
-- PART 11: Decision 12 — Profile expansion: add columns to user_profiles
-- ============================================================================

ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS agency TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS initials TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS gauge_number TEXT;

-- ============================================================================
-- PART 12: Decision 12 — New user_certifications table
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_certifications (
  id TEXT PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  cert_type TEXT NOT NULL,
  cert_number TEXT NOT NULL,
  expiry_date DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, cert_type)
);

CREATE TRIGGER update_user_certifications_updated_at
  BEFORE UPDATE ON user_certifications
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS policies for user_certifications
-- [CORRECTION] The original plan omitted RLS policies. Adding them here
-- following the same pattern as user_profiles.
ALTER TABLE user_certifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_certifications_select" ON user_certifications
  FOR SELECT TO authenticated
  USING (user_id IN (
    SELECT id FROM user_profiles WHERE company_id = get_my_company_id()
  ));

CREATE POLICY "user_certifications_insert" ON user_certifications
  FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid() AND NOT is_viewer());

CREATE POLICY "user_certifications_update" ON user_certifications
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid() AND NOT is_viewer())
  WITH CHECK (user_id = auth.uid() AND NOT is_viewer());

CREATE POLICY "user_certifications_delete" ON user_certifications
  FOR DELETE TO authenticated
  USING (user_id = auth.uid() AND NOT is_viewer());

-- ============================================================================
-- PART 13: Decision 12 — Migrate cert_number from user_profiles to user_certifications
-- ============================================================================

INSERT INTO user_certifications (id, user_id, cert_type, cert_number, created_at, updated_at)
SELECT gen_random_uuid()::text, id, 'primary', cert_number, created_at, updated_at
FROM user_profiles
WHERE cert_number IS NOT NULL
ON CONFLICT (user_id, cert_type) DO NOTHING;

-- NOTE: Do NOT drop cert_number column from user_profiles yet.
-- It remains as a read-only fallback until the app migration is verified.
-- A future migration will: ALTER TABLE user_profiles DROP COLUMN IF EXISTS cert_number;

-- ============================================================================
-- PART 14: Fix ALL SECURITY DEFINER functions to add SET search_path = public
-- ============================================================================
-- The following 5 SECURITY DEFINER functions lack SET search_path = public,
-- which is a search_path hijack vulnerability. Recreate all of them with the fix.
-- CREATE OR REPLACE preserves existing trigger bindings.
--
-- Functions being fixed:
--   1. enforce_created_by() — INSERT trigger on all 16 synced tables
--   2. get_my_company_id() — used by RLS policies
--   3. is_viewer() — used by RLS policies
--   4. create_company() — company creation RPC
--   5. search_companies() — company search RPC

-- 1. enforce_created_by()
CREATE OR REPLACE FUNCTION enforce_created_by()
RETURNS TRIGGER AS $$
BEGIN
  NEW.created_by_user_id = auth.uid();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 2. get_my_company_id()
-- > **[FIX: C7 — SECURITY CRITICAL]** The `AND status = 'approved'` guard MUST be preserved.
-- > Removing it allows deactivated users to pass ALL 76+ RLS policies that depend on this function.
-- > This is a privilege escalation vulnerability.
CREATE OR REPLACE FUNCTION get_my_company_id()
RETURNS UUID AS $$
BEGIN
  RETURN (SELECT company_id FROM user_profiles WHERE id = auth.uid() AND status = 'approved');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 3. is_viewer()
-- [FIX: A5] Keep as LANGUAGE sql (not plpgsql). Function is a single query with no
-- procedural logic. SQL language is more performant and matches original.
CREATE OR REPLACE FUNCTION is_viewer()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM user_profiles
    WHERE id = auth.uid() AND role = 'viewer' AND status = 'approved'
  )
$$ LANGUAGE sql SECURITY DEFINER SET search_path = public;

-- 4. create_company() — full body must be verified against current implementation
-- CREATE OR REPLACE FUNCTION create_company(...)
-- ... (preserve existing function body, add SET search_path = public)
-- $$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 5. search_companies() — full body must be verified against current implementation
-- CREATE OR REPLACE FUNCTION search_companies(...)
-- ... (preserve existing function body, add SET search_path = public)
-- $$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- NOTE: For functions 4 and 5, the implementation agent must read the current
-- function bodies from Supabase and recreate them with SET search_path = public.
-- The function signatures and bodies must be preserved exactly.

-- ============================================================================
-- PART 15: Denormalize project_id onto junction tables for simpler pull queries
-- ============================================================================
-- Entry-scoped junction tables (entry_equipment, entry_quantities,
-- entry_contractors, entry_personnel_counts) lack a direct project_id column,
-- forcing complex multi-hop joins during pull. Adding project_id enables
-- simple WHERE project_id IN (...) filters, matching viaProject behavior.

-- [FIX: C1] Denormalize project_id onto junction tables for uniform pull scoping.
-- This allows both the pull engine and IntegrityChecker RPC to use project_id IN (...) directly.
-- NOTE: The new project_id column is for pull filtering only, not RLS enforcement.
-- These tables already have RLS through their existing policies (via entry_id join).
-- Add project_id column
ALTER TABLE entry_equipment ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id);
ALTER TABLE entry_quantities ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id);
ALTER TABLE entry_contractors ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id);
ALTER TABLE entry_personnel_counts ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id);

-- Backfill from daily_entries
UPDATE entry_equipment SET project_id = (SELECT project_id FROM daily_entries WHERE id = entry_equipment.entry_id) WHERE project_id IS NULL;
UPDATE entry_quantities SET project_id = (SELECT project_id FROM daily_entries WHERE id = entry_quantities.entry_id) WHERE project_id IS NULL;
UPDATE entry_contractors SET project_id = (SELECT project_id FROM daily_entries WHERE id = entry_contractors.entry_id) WHERE project_id IS NULL;
UPDATE entry_personnel_counts SET project_id = (SELECT project_id FROM daily_entries WHERE id = entry_personnel_counts.entry_id) WHERE project_id IS NULL;

-- Create indexes for pull performance
CREATE INDEX IF NOT EXISTS idx_entry_equipment_project ON entry_equipment(project_id);
CREATE INDEX IF NOT EXISTS idx_entry_quantities_project ON entry_quantities(project_id);
CREATE INDEX IF NOT EXISTS idx_entry_contractors_project ON entry_contractors(project_id);
CREATE INDEX IF NOT EXISTS idx_entry_personnel_counts_project ON entry_personnel_counts(project_id);
```

---

## Step 2: Supabase Config -- secure_password_change

**File**: `supabase/config.toml`
**Action**: Modify
**Depends on**: Nothing

### 2.1 Change secure_password_change

At line 207, change:

**Before**:
```toml
secure_password_change = false
```

**After**:
```toml
secure_password_change = true
```

This is GAP-19. Users will need to reauthenticate (or have logged in recently) before changing their password.

---

## Step 3: UserProfile Model Expansion

**File**: `lib/features/auth/data/models/user_profile.dart`
**Action**: Modify
**Depends on**: Nothing (can be done in parallel with Steps 1-2)

### 3.1 Add 4 new fields to the class

Add after the existing `phone` field (line 12-13):

```dart
  final String? email;
  final String? agency;
  final String? initials;
  final String? gaugeNumber;
```

The full field list becomes:
```dart
  final String userId;
  final String? displayName;
  final String? certNumber;
  final String? phone;
  final String? email;       // NEW
  final String? agency;      // NEW
  final String? initials;    // NEW
  final String? gaugeNumber; // NEW
  final String? position;
  final String? companyId;
  final UserRole role;
  final MembershipStatus status;
  final DateTime? lastSyncedAt;
  final DateTime createdAt;
  final DateTime updatedAt;
```

### 3.2 Update the constructor

Add the 4 new optional parameters:

```dart
  UserProfile({
    String? userId,
    this.displayName,
    this.certNumber,
    this.phone,
    this.email,        // NEW
    this.agency,       // NEW
    this.initials,     // NEW
    this.gaugeNumber,  // NEW
    this.position,
    this.companyId,
    this.role = UserRole.inspector,
    this.status = MembershipStatus.pending,
    this.lastSyncedAt,
    DateTime? createdAt,
    DateTime? updatedAt,
  })  : userId = userId ?? const Uuid().v4(),
        createdAt = createdAt ?? DateTime.now(),
        updatedAt = updatedAt ?? DateTime.now();
```

### 3.3 Update copyWith()

Add the 4 new parameters:

```dart
  UserProfile copyWith({
    String? userId,
    String? displayName,
    String? certNumber,
    String? phone,
    String? email,        // NEW
    String? agency,       // NEW
    String? initials,     // NEW
    String? gaugeNumber,  // NEW
    String? position,
    String? companyId,
    UserRole? role,
    MembershipStatus? status,
    DateTime? lastSyncedAt,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return UserProfile(
      userId: userId ?? this.userId,
      displayName: displayName ?? this.displayName,
      certNumber: certNumber ?? this.certNumber,
      phone: phone ?? this.phone,
      email: email ?? this.email,            // NEW
      agency: agency ?? this.agency,          // NEW
      initials: initials ?? this.initials,    // NEW
      gaugeNumber: gaugeNumber ?? this.gaugeNumber, // NEW
      position: position ?? this.position,
      companyId: companyId ?? this.companyId,
      role: role ?? this.role,
      status: status ?? this.status,
      lastSyncedAt: lastSyncedAt ?? this.lastSyncedAt,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
```

### 3.4 Update toMap()

Add the 4 new fields to the map (after `phone`):

```dart
      if (email != null) 'email': email,
      if (agency != null) 'agency': agency,
      if (initials != null) 'initials': initials,
      if (gaugeNumber != null) 'gauge_number': gaugeNumber,
```

### 3.5 Update fromMap()

Add the 4 new fields to the factory:

```dart
      email: map['email'] as String?,
      agency: map['agency'] as String?,
      initials: map['initials'] as String?,
      gaugeNumber: map['gauge_number'] as String?,
```

### 3.6 Update fromJson()

Add the 4 new fields to the factory (same as fromMap):

```dart
      email: json['email'] as String?,
      agency: json['agency'] as String?,
      initials: json['initials'] as String?,
      gaugeNumber: json['gauge_number'] as String?,
```

### 3.7 Update toUpsertJson()

Add the new user-editable fields (email is read-only from auth, so omit it):

```dart
      if (agency != null) 'agency': agency,
      if (initials != null) 'initials': initials,
      if (gaugeNumber != null) 'gauge_number': gaugeNumber,
```

### 3.8 Update toJson()

Add the 4 new fields:

```dart
      if (email != null) 'email': email,
      if (agency != null) 'agency': agency,
      if (initials != null) 'initials': initials,
      if (gaugeNumber != null) 'gauge_number': gaugeNumber,
```

### 3.9 Add convenience getter for effective initials

Add after the `isViewer` getter:

```dart
  /// Get effective initials: use stored initials if set, otherwise derive from displayName.
  String get effectiveInitials {
    if (initials != null && initials!.isNotEmpty) {
      return initials!;
    }
    return _generateInitialsFromName(displayName ?? '');
  }

  static String _generateInitialsFromName(String name) {
    if (name.trim().isEmpty) return '';
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.length >= 2) {
      return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
    }
    return parts.first.substring(0, parts.first.length.clamp(0, 2)).toUpperCase();
  }
```

Note: The `generateInitialsFromName` function already exists in `lib/shared/utils/string_utils.dart`. You may import and use that instead of duplicating. Check the import:
```dart
import 'package:construction_inspector/shared/utils/string_utils.dart';
```
Then use `generateInitialsFromName(displayName ?? '')` directly.

---

## Step 4: SQLite v30 Migration

**File**: `lib/core/database/database_service.dart`
**Action**: Modify
**Depends on**: Step 3 (UserProfile model must have new fields for fresh-install schema)

Also modify:
- `lib/core/database/schema/core_tables.dart` (fresh-install schema)
- `lib/core/database/schema/sync_tables.dart` (new tables for fresh installs)

### 4.1 Bump database version

**File**: `lib/core/database/database_service.dart`

Change line 54 from:
```dart
      version: 29,
```
to:
```dart
      version: 30,
```

Also change line 90 (the in-memory database version):
```dart
      version: 30,
```

### 4.2 Update fresh-install schema: core_tables.dart

**File**: `lib/core/database/schema/core_tables.dart`

Update the `createUserProfilesTable` constant to include the 4 new columns. Change the table definition (lines 60-74) to:

```dart
  static const String createUserProfilesTable = '''
    CREATE TABLE IF NOT EXISTS user_profiles (
      id TEXT PRIMARY KEY,
      company_id TEXT,
      role TEXT NOT NULL DEFAULT 'inspector',
      status TEXT NOT NULL DEFAULT 'pending',
      display_name TEXT,
      cert_number TEXT,
      phone TEXT,
      email TEXT,
      agency TEXT,
      initials TEXT,
      gauge_number TEXT,
      position TEXT,
      last_synced_at TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
    )
  ''';
```

### 4.3 Update fresh-install schema: sync_tables.dart

**File**: `lib/core/database/schema/sync_tables.dart`

Add the new tables to SyncTables class. Add after the existing `createDeletionNotificationsTable`:

```dart
  /// Sync control table -- key-value store for sync state flags
  static const String createSyncControlTable = '''
    CREATE TABLE IF NOT EXISTS sync_control (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )
  ''';

  /// Change log table -- tracks local changes for push sync
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

  /// Conflict log table -- records LWW conflict resolutions
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

  /// Sync lock table -- single-row mutex for sync operations
  static const String createSyncLockTable = '''
    CREATE TABLE IF NOT EXISTS sync_lock (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      locked_at TEXT NOT NULL,
      locked_by TEXT NOT NULL
    )
  ''';

  /// Synced projects table -- tracks which projects are synced to this device
  static const String createSyncedProjectsTable = '''
    CREATE TABLE IF NOT EXISTS synced_projects (
      project_id TEXT PRIMARY KEY,
      synced_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
    )
  ''';

  /// User certifications table -- mirrors Supabase user_certifications
  static const String createUserCertificationsTable = '''
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
  ''';
```

Also add the new indexes to the `indexes` list:

```dart
  static const List<String> indexes = [
    'CREATE INDEX idx_sync_queue_table ON sync_queue(table_name)',
    'CREATE INDEX idx_sync_queue_created ON sync_queue(created_at)',
    'CREATE INDEX idx_deletion_notifications_seen ON deletion_notifications(seen)',
    'CREATE INDEX idx_deletion_notifications_project ON deletion_notifications(project_id)',
    // New indexes for v30 tables
    'CREATE INDEX IF NOT EXISTS idx_change_log_unprocessed ON change_log(processed, table_name)',
    'CREATE INDEX IF NOT EXISTS idx_conflict_log_expires ON conflict_log(expires_at)',
  ];
```

### 4.4 Update _onCreate to create the new tables

**File**: `lib/core/database/database_service.dart`

Find the `_onCreate` method and add the new table creations after the existing sync tables. The exact location depends on where sync tables are created. Add:

```dart
    await db.execute(SyncTables.createSyncControlTable);
    await db.execute(SyncTables.createChangeLogTable);
    await db.execute(SyncTables.createConflictLogTable);
    await db.execute(SyncTables.createSyncLockTable);
    await db.execute(SyncTables.createSyncedProjectsTable);
    await db.execute(SyncTables.createUserCertificationsTable);
```

Also add the seed value for sync_control:
```dart
    await db.execute("INSERT OR IGNORE INTO sync_control (key, value) VALUES ('pulling', '0')");
```

### 4.5 Add v30 migration block

**File**: `lib/core/database/database_service.dart`

Add after the v29 migration block (after line 1153). Insert before the closing `}` of `_onUpgrade`:

```dart
    if (oldVersion < 30) {
      // Decision 1: sync_control table
      await db.execute('''
        CREATE TABLE IF NOT EXISTS sync_control (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        )
      ''');
      await db.execute("INSERT OR IGNORE INTO sync_control (key, value) VALUES ('pulling', '0')");

      // Change log table (with metadata column)
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

      // Conflict log table (with expires_at column)
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

      // Decision 2: sync_lock table
      await db.execute('''
        CREATE TABLE IF NOT EXISTS sync_lock (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          locked_at TEXT NOT NULL,
          locked_by TEXT NOT NULL
        )
      ''');

      // Decision 4: synced_projects table
      await db.execute('''
        CREATE TABLE IF NOT EXISTS synced_projects (
          project_id TEXT PRIMARY KEY,
          synced_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
        )
      ''');

      // Decision 12: user_certifications table
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

      // Decision 12: Profile expansion columns on user_profiles
      // [CORRECTION] SQLite does NOT support ALTER TABLE ... ADD COLUMN IF NOT EXISTS.
      // Must use the _addColumnIfNotExists() helper (defined at line 225).
      await _addColumnIfNotExists(db, 'user_profiles', 'email', 'TEXT');
      await _addColumnIfNotExists(db, 'user_profiles', 'agency', 'TEXT');
      await _addColumnIfNotExists(db, 'user_profiles', 'initials', 'TEXT');
      await _addColumnIfNotExists(db, 'user_profiles', 'gauge_number', 'TEXT');

      // Denormalize project_id onto junction tables for simpler pull queries
      // (mirrors Supabase migration PART 15)
      await _addColumnIfNotExists(db, 'entry_equipment', 'project_id', 'TEXT');
      await _addColumnIfNotExists(db, 'entry_quantities', 'project_id', 'TEXT');
      await _addColumnIfNotExists(db, 'entry_contractors', 'project_id', 'TEXT');
      await _addColumnIfNotExists(db, 'entry_personnel_counts', 'project_id', 'TEXT');

      // Backfill project_id from parent daily_entries
      await db.execute('''
        UPDATE entry_equipment SET project_id = (
          SELECT project_id FROM daily_entries WHERE id = entry_equipment.entry_id
        ) WHERE project_id IS NULL
      ''');
      await db.execute('''
        UPDATE entry_quantities SET project_id = (
          SELECT project_id FROM daily_entries WHERE id = entry_quantities.entry_id
        ) WHERE project_id IS NULL
      ''');
      await db.execute('''
        UPDATE entry_contractors SET project_id = (
          SELECT project_id FROM daily_entries WHERE id = entry_contractors.entry_id
        ) WHERE project_id IS NULL
      ''');
      await db.execute('''
        UPDATE entry_personnel_counts SET project_id = (
          SELECT project_id FROM daily_entries WHERE id = entry_personnel_counts.entry_id
        ) WHERE project_id IS NULL
      ''');

      // UNIQUE index on projects(company_id, project_number)
      await db.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_company_number ON projects(company_id, project_number)',
      );
    }
```

---

## Step 5: PreferencesService Dead Code Removal

**File**: `lib/shared/services/preferences_service.dart`
**Action**: Modify
**Depends on**: Step 6 must be done first (consumers must stop reading these before we remove them)

**IMPORTANT**: Steps 5 and 6 are interrelated. Do Step 6 (consumer migration) first to remove all callers, THEN do Step 5 (dead code removal). Otherwise the code won't compile.

### 5.1 Remove dead preference key constants

Remove these lines:
- Line 20: `static const String keyInspectorAgency = 'inspector_agency';`
- Line 25: `static const String keyShowOnlyManualFields = 'show_only_manual_fields';`
- Line 26: `static const String keyLastRoute = 'last_route_location';`
- Line 29: `static const String _prefillKeyPrefix = 'prefill_project_form';`
- Line 30: `static const String _prefillPromptedPrefix = 'prefill_prompted';`

### 5.2 Remove dead toggle key constants

Remove these lines:
- Line 21: `static const String keyAutoFetchWeather = 'auto_fetch_weather';`
- Line 22: `static const String keyAutoSyncWifi = 'auto_sync_wifi';`
- Line 23: `static const String keyUseLastValues = 'use_last_values';`
- Line 24: `static const String keyAutoFillEnabled = 'auto_fill_enabled';`

### 5.3 Remove dead methods

Remove the following method blocks entirely:

1. **inspectorAgency getter/setter** (lines 128-139):
   - `String? get inspectorAgency`
   - `Future<void> setInspectorAgency(String value)`

2. **autoFetchWeather getter/setter** (lines 146-156):
   - `bool get autoFetchWeather`
   - `Future<void> setAutoFetchWeather(bool value)`

3. **autoSyncWifi getter/setter** (lines 158-169):
   - `bool get autoSyncWifi`
   - `Future<void> setAutoSyncWifi(bool value)`

4. **useLastValues getter/setter** (lines 171-182):
   - `bool get useLastValues`
   - `Future<void> setUseLastValues(bool value)`

5. **autoFillEnabled getter/setter** (lines 184-195):
   - `bool get autoFillEnabled`
   - `Future<void> setAutoFillEnabled(bool value)`

6. **showOnlyManualFields getter/setter** (lines 197-208):
   - `bool? get showOnlyManualFields`
   - `Future<void> setShowOnlyManualFields(bool value)`

7. **lastRoute getter/setter/clear** (lines 210-225):
   - `String? get lastRoute`
   - `Future<void> setLastRoute(String location)`
   - `Future<void> clearLastRoute()`

8. **prefill helpers and methods** (lines 268-309):
   - `String _prefillKey(String projectId, String formId)`
   - `String _prefillPromptedKey(String projectId, String formId)`
   - `Map<String, dynamic>? getProjectFormPrefill(String projectId, String formId)`
   - `Future<void> setProjectFormPrefill(...)`
   - `bool getProjectFormPrefillPrompted(String projectId, String formId)`
   - `Future<void> setProjectFormPrefillPrompted(...)`

### 5.4 Update inspectorProfile getter

The current `inspectorProfile` getter (line 316-322) references `inspectorAgency` which was removed. Update it:

**Before** (line 316-322):
```dart
  Map<String, String?> get inspectorProfile => {
        'name': inspectorName,
        'initials': effectiveInitials,
        'phone': inspectorPhone,
        'cert_number': inspectorCertNumber,
        'agency': inspectorAgency,
      };
```

**After**:
```dart
  Map<String, String?> get inspectorProfile => {
        'name': inspectorName,
        'initials': effectiveInitials,
        'phone': inspectorPhone,
        'cert_number': inspectorCertNumber,
      };
```

### 5.5 Add the `remove` method if not present

The PII cleanup in Step 7 calls `prefs.remove(key)`. Verify that `PreferencesService` has a `remove` method. If not, add one:

```dart
  /// Remove a single preference key.
  Future<void> remove(String key) async {
    _ensureInitialized();
    await _prefs!.remove(key);
  }
```

### 5.6 Remove ALL PII accessor methods

**[FIX: H6]** The following PII getters/setters must ALSO be removed in Step 5
(after all consumers in Step 6 are migrated):

- `inspectorName` getter/setter (lines 55-65)
- `inspectorInitials` getter/setter (lines 68-78)
- `inspectorPhone` getter/setter (lines 90-100)
- `inspectorCertNumber` getter/setter (lines 103-113)
- `inspectorProfile` getter (line 316)
- `hasInspectorProfile` getter (line 325)

**Removal order**: Step 6 (migrate consumers) MUST complete before Step 5 removes these methods.
`gaugeNumber` getter/setter (lines 116-126) is NOT PII (equipment ID) and may be kept.

---

## Step 6: Consumer Migration (PreferencesService -> AuthProvider.userProfile)

**Action**: Modify multiple files
**Depends on**: Step 3 (UserProfile model must have new fields)

### 6.1 mdot_hub_screen.dart

**File**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart`

At the `_hydrate` method (around line 150-165), change the auto-fill data source from PreferencesService to AuthProvider.

**Before** (lines 153-164):
```dart
      final prefs = context.read<PreferencesService>();
      final auto = _autoFillService.buildHeaderData(
        date: DateTime.now().toIso8601String().split('T').first,
        controlSectionId: project?.controlSectionId,
        jobNumber: project?.projectNumber,
        routeStreet: project?.routeStreet,
        gaugeNumber: prefs.gaugeNumber,
        inspector: prefs.inspectorName,
        certNumber: prefs.inspectorCertNumber,
        phone: prefs.inspectorPhone,
        constructionEng: project?.constructionEng,
      );
```

**After**:
```dart
      final userProfile = context.read<AuthProvider>().userProfile;
      final auto = _autoFillService.buildHeaderData(
        date: DateTime.now().toIso8601String().split('T').first,
        controlSectionId: project?.controlSectionId,
        jobNumber: project?.projectNumber,
        routeStreet: project?.routeStreet,
        gaugeNumber: userProfile?.gaugeNumber,
        inspector: userProfile?.displayName,
        certNumber: userProfile?.certNumber,
        phone: userProfile?.phone,
        constructionEng: project?.constructionEng,
      );
```

Also update the imports: ensure `AuthProvider` is imported. Remove the `PreferencesService` import if it is no longer used in this file.

### 6.2 form_viewer_screen.dart

**File**: `lib/features/forms/presentation/screens/form_viewer_screen.dart`

At the `_applyAutoFillIfNeeded` method (around line 75-91):

**Before** (lines 78-90):
```dart
    final prefs = context.read<PreferencesService>();
    _header = _autoFillService.buildHeaderData(
      projectNumber: project?.projectNumber,
      projectName: project?.name,
      date: DateTime.now().toIso8601String().split('T').first,
      inspector: prefs.inspectorName,
      controlSectionId: project?.controlSectionId,
      routeStreet: project?.routeStreet,
      constructionEng: project?.constructionEng,
      certNumber: prefs.inspectorCertNumber,
      phone: prefs.inspectorPhone,
      gaugeNumber: prefs.gaugeNumber,
    );
```

**After**:
```dart
    final userProfile = context.read<AuthProvider>().userProfile;
    _header = _autoFillService.buildHeaderData(
      projectNumber: project?.projectNumber,
      projectName: project?.name,
      date: DateTime.now().toIso8601String().split('T').first,
      inspector: userProfile?.displayName,
      controlSectionId: project?.controlSectionId,
      routeStreet: project?.routeStreet,
      constructionEng: project?.constructionEng,
      certNumber: userProfile?.certNumber,
      phone: userProfile?.phone,
      gaugeNumber: userProfile?.gaugeNumber,
    );
```

Update imports: add `AuthProvider`, remove `PreferencesService` if unused.

### 6.3 pdf_data_builder.dart

**File**: `lib/features/entries/presentation/controllers/pdf_data_builder.dart`

At lines 122-135, remove the SharedPreferences fallback and use AuthProvider instead.

**Before** (lines 122-135):
```dart
    // Get inspector name — prefer attribution repository when createdByUserId
    // is available; fall back to SharedPreferences for backward compat.
    String inspectorName;
    if (attributionRepository != null && entry.createdByUserId != null) {
      inspectorName = await attributionRepository.getDisplayName(entry.createdByUserId);
      // If attribution returned 'Unknown', fall back to SharedPreferences value.
      if (inspectorName == 'Unknown') {
        final prefs = await SharedPreferences.getInstance();
        inspectorName = prefs.getString('inspector_name') ?? 'Inspector';
      }
    } else {
      final prefs = await SharedPreferences.getInstance();
      inspectorName = prefs.getString('inspector_name') ?? 'Inspector';
    }
```

**After**:
```dart
    // Get inspector name — prefer attribution repository when createdByUserId
    // is available; fall back to AuthProvider.userProfile.displayName.
    String inspectorName;
    if (attributionRepository != null && entry.createdByUserId != null) {
      inspectorName = await attributionRepository.getDisplayName(entry.createdByUserId);
      if (inspectorName == 'Unknown') {
        inspectorName = userProfile?.displayName ?? 'Inspector';
      }
    } else {
      inspectorName = userProfile?.displayName ?? 'Inspector';
    }
```

This requires passing `userProfile` as a parameter to the build method. Check the method signature and add `UserProfile? userProfile` as a parameter. The caller must pass `context.read<AuthProvider>().userProfile`.

Remove the `import 'package:shared_preferences/shared_preferences.dart';` if it is no longer used.

### 6.4 entry_photos_section.dart

**File**: `lib/features/entries/presentation/widgets/entry_photos_section.dart`

At lines 87-88, replace SharedPreferences access with AuthProvider.

**Before** (lines 87-88):
```dart
    final prefs = await SharedPreferences.getInstance();
    final initials = prefs.getString('inspector_initials') ?? 'XX';
```

**After**:
```dart
    final authProvider = context.read<AuthProvider>();
    final initials = authProvider.userProfile?.effectiveInitials ?? 'XX';
```

This requires:
1. Adding `import 'package:provider/provider.dart';` if not present
2. Adding the AuthProvider import
3. Removing the `SharedPreferences` import if unused
4. The method using `context` -- if this is an async method without `BuildContext`, the `AuthProvider` must be captured before the `await`. Check the method to ensure `context` is accessible here. If the widget is a `StatefulWidget`, `context` is available via the state.

### 6.5 `harness_providers.dart` (test harness)

**File**: `lib/test_harness/harness_providers.dart`
**Action**: Modify

**[FIX: C9]** This file calls `preferencesService.hasInspectorProfile`, `setInspectorName`,
`setInspectorCertNumber`, `setInspectorPhone` (lines 105-108). After Step 5 removes these
methods, this file will fail to compile.

Update to use `AuthProvider.userProfile` for test data seeding, or create test-specific
profile setup that writes directly to Supabase user_profiles.

### 6.6 `auth_provider.dart` — Legacy migration block

**File**: `lib/features/auth/presentation/providers/auth_provider.dart`
**Action**: Modify

**[FIX: C9]** Lines 461-500 contain a legacy migration block that reads `prefs.inspectorCertNumber`,
`prefs.inspectorPhone`, `prefs.inspectorName` and clears them by setting to empty string.
After Step 5 removes these methods, this code will fail to compile.

Remove this entire legacy migration block. The PII cleanup in Step 7 handles the
SharedPreferences key removal at the storage level.

**[FIX: H13]** Complete auto-fill migration manifest. The following files read inspector
profile data and must be updated to source from AuthProvider.userProfile before PII
accessors are removed:

1. `lib/features/forms/presentation/screens/form_viewer_screen.dart` — reads gauge_number, inspector name
2. `lib/features/forms/presentation/screens/mdot_hub_screen.dart` — reads inspector data for header
3. `lib/features/forms/presentation/widgets/hub_header_content.dart` — displays inspector info
4. `lib/features/forms/data/services/form_pdf_service.dart` — accepts inspector params for PDF
5. `lib/features/entries/presentation/controllers/pdf_data_builder.dart` — builds PDF with inspector details
6. `lib/features/pdf/services/pdf_service.dart` — stamps PDFs with inspector data
7. `lib/features/auth/data/repositories/user_attribution_repository.dart` — user data
8. `lib/test_harness/harness_seed_data.dart` — test seeds

---

## Step 7: PII Cleanup from SharedPreferences

**File**: `lib/shared/services/preferences_service.dart` (add method)
**File**: `lib/main.dart` or app initialization code (call it once)
**Action**: Modify
**Depends on**: Step 6 (all consumers must be migrated before deleting PII)

### 7.1 Add cleanup method to PreferencesService

Add this method to the `PreferencesService` class:

```dart
  /// One-time cleanup of legacy PII keys from SharedPreferences.
  /// Called once after the Settings redesign migration.
  /// Uses a pref key gate to ensure it only runs once.
  Future<void> cleanupLegacyPii() async {
    _ensureInitialized();
    const gateKey = 'pii_cleanup_v1_done';
    if (_prefs!.getBool(gateKey) == true) return;

    for (final key in [
      'inspector_name',
      'cert_number',            // keyInspectorCertNumber value
      'inspector_cert_number',  // alternate key used by some flows
      'phone',
      'inspector_phone',
      'inspector_initials',
      'inspector_agency',
      'gauge_number',
    ]) {
      await _prefs!.remove(key);
    }

    await _prefs!.setBool(gateKey, true);
  }
```

### 7.2 Call cleanup on app startup

**File**: `lib/main.dart` (or wherever `PreferencesService.initialize()` is called)

After the preferences service is initialized and the user is authenticated, call:

```dart
await preferencesService.cleanupLegacyPii();
```

Place this after the `preferencesService.initialize()` call, ideally gated behind authentication being confirmed (so we know user_profiles data is available as the source of truth).

---

## Step 8: Purge Handler in SyncService

**File**: `lib/services/sync_service.dart`
**Action**: Modify
**Depends on**: Nothing

### 8.1 Add purge case to _processSyncQueueItem

At the `_processSyncQueueItem` method (line 691-718), add a `case 'purge':` block.

**Before** (lines 699-717):
```dart
    switch (operation) {
      case 'insert':
      case 'update':
        // Get current local data and upsert to remote
        final localData = await db.query(
          tableName,
          where: 'id = ?',
          whereArgs: [recordId],
        );
        if (localData.isNotEmpty) {
          await _supabase!
              .from(tableName)
              .upsert(_convertForRemote(tableName, localData.first));
        }
        break;
      case 'delete':
        await _supabase!.from(tableName).delete().eq('id', recordId);
        break;
    }
```

**After**:
```dart
    switch (operation) {
      case 'insert':
      case 'update':
        // Get current local data and upsert to remote
        final localData = await db.query(
          tableName,
          where: 'id = ?',
          whereArgs: [recordId],
        );
        if (localData.isNotEmpty) {
          await _supabase!
              .from(tableName)
              .upsert(_convertForRemote(tableName, localData.first));
        }
        break;
      case 'delete':
        await _supabase!.from(tableName).delete().eq('id', recordId);
        break;
      case 'purge':
        // GAP-3: Hard-delete expired soft-deleted records on the server.
        // Uses sync_control gate to bypass triggers during purge.
        await _supabase!.from(tableName).delete().eq('id', recordId);
        // Also remove the local record if it still exists
        await db.delete(tableName, where: 'id = ?', whereArgs: [recordId]);
        break;
    }
```

---

## Step 9: Settings Screen Redesign

**File**: `lib/features/settings/presentation/screens/settings_screen.dart`
**Action**: Modify (full rewrite of the build method body)
**Depends on**: Steps 3, 4, 5, 6 (model expansion + consumer migration + dead code removal)

### 9.1 Remove dead state variables and methods

Remove these state variables (lines 23-26):
```dart
  bool _autoFetchWeather = true;
  bool _autoSyncWifi = true;
  bool _autoFillEnabled = true;
  bool _useLastValues = true;
```

Remove the `_loadSettings` method (lines 41-49).

Remove the 4 toggle methods (lines 51-73):
- `_toggleAutoFetchWeather`
- `_toggleAutoSyncWifi`
- `_toggleAutoFillEnabled`
- `_toggleUseLastValues`

Remove the `_loadSettings()` call from `initState` (line 33). Keep `_loadTrashCount()`.

### 9.2 Rewrite the build method with new section ordering

The new section ordering is:

**1. ACCOUNT** (was split across Profile + Account)
```
Profile summary (name, role, company -- read-only)
Edit Profile -> /edit-profile
Admin Dashboard -> /admin-dashboard (admin only)
Sign Out
```

**2. SYNC & DATA** (was split across Cloud Sync + Data)
```
SyncSection widget (existing -- shows sync status, sync now button)
Trash -> /settings/trash (with badge count)
Clear Cached Exports
```

**3. FORM SETTINGS** (new section -- replaces Form Auto-Fill and pulls from PDF Export)
```
Gauge Number (editable text field -- reads/writes AuthProvider.userProfile.gaugeNumber)
Initials (editable text field -- reads/writes AuthProvider.userProfile.initials)
PDF Template (display: read-only info from AppTerminology)
```

**4. APPEARANCE** (same as before + Auto-Load from Project)
```
ThemeSection widget (existing)
Auto-Load toggle (from ProjectSettingsProvider)
```

**5. ABOUT** (same, minus Help & Support stub)
```
Version
Licenses
```

### 9.3 Exact widgets to REMOVE from the build method

| Widget/Tile | Current Location | Reason |
|-------------|-----------------|--------|
| `SectionHeader('Form Auto-Fill')` + both SwitchListTiles | lines 134-155 | Dead toggles |
| `SectionHeader('Project')` + Auto-Load toggle | lines 157-174 | Moved to APPEARANCE |
| `SectionHeader('Cloud Sync')` + Auto-Sync WiFi toggle | lines 213-227 | Dead toggle; SyncSection moves to SYNC & DATA |
| `SectionHeader('PDF Export')` + Company Template tile + Default Signature Name tile | lines 229-250 | Company Template -> Form Settings read-only; Signature Name is duplicate |
| `SectionHeader('Weather')` + Weather API tile + Auto-fetch Weather toggle | lines 253-273 | Dead toggle + unactionable display |
| Backup Data tile | lines 281-291 | Dead stub |
| Restore Data tile | lines 293-303 | Dead stub |
| Help & Support tile | lines 382-391 | Dead stub |

### 9.4 Exact widgets to ADD

1. **FORM SETTINGS section** with:
   - Gauge Number editable `ListTile` with trailing edit icon. On tap, show a dialog to edit `AuthProvider.userProfile.gaugeNumber`, then save via profile update.
   - Initials editable `ListTile`. Same pattern.
   - PDF Template read-only `ListTile` showing `AppTerminology.pdfTemplateDescription`.

2. **Auto-Load toggle** moved into the APPEARANCE section (after ThemeSection).

### 9.5 New section ordering skeleton

```dart
body: ListView(
  children: [
    // 1. ACCOUNT
    SectionHeader(title: 'Account'),
    // Profile summary: name, role, company (read-only) -- same Consumer<AuthProvider> as current Profile section
    // Edit Profile tile
    // Admin Dashboard tile (admin only)
    // Sign Out tile
    const Divider(),

    // 2. SYNC & DATA
    SectionHeader(title: 'Sync & Data'),
    const SyncSection(),
    // Trash tile (with badge count) -- moved from Data section
    // Clear Cached Exports tile -- moved from Data section
    const Divider(),

    // 3. FORM SETTINGS
    SectionHeader(title: 'Form Settings'),
    // Gauge Number tile (editable)
    // Initials tile (editable)
    // PDF Template tile (read-only)
    const Divider(),

    // 4. APPEARANCE
    SectionHeader(title: 'Appearance'),
    const ThemeSection(),
    // Auto-Load toggle (moved from Project section)
    const Divider(),

    // 5. ABOUT
    SectionHeader(title: 'About'),
    // Version tile
    // Licenses tile
    const SizedBox(height: 32),
  ],
),
```

### 9.6 Gauge Number and Initials editable tiles

For the Gauge Number and Initials tiles in FORM SETTINGS, use inline editing. Example pattern for Gauge Number:

```dart
Consumer<AuthProvider>(
  builder: (context, authProvider, _) {
    final profile = authProvider.userProfile;
    return ListTile(
      leading: const Icon(Icons.speed),
      title: const Text('Gauge Number'),
      subtitle: Text(profile?.gaugeNumber ?? 'Not set'),
      trailing: const Icon(Icons.edit, size: 18),
      onTap: () => _showEditDialog(
        context,
        title: 'Gauge Number',
        currentValue: profile?.gaugeNumber ?? '',
        onSave: (value) async {
          await authProvider.updateProfile(
            profile!.copyWith(gaugeNumber: value),
          );
        },
      ),
    );
  },
),
```

Implement a reusable `_showEditDialog` method:

```dart
Future<void> _showEditDialog(
  BuildContext context, {
  required String title,
  required String currentValue,
  required Future<void> Function(String) onSave,
}) async {
  final controller = TextEditingController(text: currentValue);
  final result = await showDialog<String>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text('Edit $title'),
      content: TextField(
        controller: controller,
        autofocus: true,
        decoration: InputDecoration(hintText: 'Enter $title'),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
        TextButton(
          onPressed: () => Navigator.pop(ctx, controller.text),
          child: const Text('Save'),
        ),
      ],
    ),
  );
  if (result != null && result != currentValue) {
    await onSave(result);
  }
}
```

Note: `authProvider.updateProfile()` must exist. If it does not, it needs to be added to `AuthProvider` to update the local user_profiles SQLite row and push to Supabase. Check the existing AuthProvider for an `updateProfile` method; if missing, add one that calls the user_profiles repository.

---

## Step 10: Delete Orphaned EditInspectorDialog Widget

**Depends on**: Step 9 (settings screen no longer references it)

### 10.1 Delete the widget file

**File to delete**: `lib/features/settings/presentation/widgets/edit_inspector_dialog.dart`

### 10.2 Remove the barrel export

**File**: `lib/features/settings/presentation/widgets/widgets.dart`

Remove line 4:
```dart
export 'edit_inspector_dialog.dart';
```

The file becomes:
```dart
export 'section_header.dart';
export 'theme_section.dart';
export 'sync_section.dart';
export 'sign_out_dialog.dart';
export 'clear_cache_dialog.dart';
export 'member_detail_sheet.dart';
```

### 10.3 Clean up testing keys

**File**: `lib/shared/testing_keys/testing_keys.dart` (or wherever settings testing keys are defined)

Search for and remove any testing keys related to `EditInspectorDialog`:
- `editInspectorNameDialog`
- `editInitialsDialog`
- Any other keys prefixed with `editInspector`

Also remove dead settings toggle testing keys:
- `settingsAutoFillToggle`
- `settingsUseLastValuesToggle`
- `settingsAutoSyncToggle`
- `settingsAutoWeatherToggle`
- `settingsAutoFillSection`

---

## Step 11: Verification Checklist

After all steps are complete, verify:

### 11.1 Compilation check

```
pwsh -Command "flutter analyze"
```

No errors should relate to removed preferences, missing fields, or import issues.

### 11.2 Supabase migration dry-run

Before applying the migration to production:
1. Apply to a staging/local Supabase instance first
2. Verify all 6 admin RPCs work with the `is_approved_admin()` check
3. Verify storage policies with a test upload: the path `entries/{companyId}/{entryId}/test.jpg` should only be accessible by users in that company
4. Verify `get_table_integrity('inspector_forms')` no longer fails (GAP-9 applied)
5. Verify `user_certifications` has proper RLS by testing SELECT/INSERT with different user contexts

### 11.3 SQLite migration test

1. Fresh install: all v30 tables are created correctly
2. Upgrade from v29: `_addColumnIfNotExists` runs for the 4 new user_profiles columns
3. Verify `user_profiles` table has `email`, `agency`, `initials`, `gauge_number` columns after migration

### 11.4 Consumer migration verification

Verify each consumer reads from `AuthProvider.userProfile` instead of `PreferencesService`:
- `mdot_hub_screen.dart` -- auto-fill uses `userProfile.gaugeNumber`, etc.
- `form_viewer_screen.dart` -- auto-fill uses `userProfile.displayName`, etc.
- `pdf_data_builder.dart` -- no more `SharedPreferences.getInstance()`
- `entry_photos_section.dart` -- uses `userProfile.effectiveInitials`

### 11.5 Settings screen visual check

Run the app and navigate to Settings. Verify:
- Sections appear in order: Account, Sync & Data, Form Settings, Appearance, About
- No dead toggles (Auto-Fill, Use Last Values, Auto-Sync WiFi, Auto-Fetch Weather)
- No dead stubs (Backup, Restore, Help & Support)
- No Weather API display, no Company Template in wrong section
- Gauge Number and Initials are editable
- PDF Template is read-only

### 11.6 PII cleanup verification

After first launch post-migration:
- Check SharedPreferences no longer contains: `inspector_name`, `cert_number`, `inspector_cert_number`, `phone`, `inspector_phone`, `inspector_initials`, `inspector_agency`, `gauge_number`
- Check `pii_cleanup_v1_done` is `true`

---

## Corrections Summary

| ID | Original Plan Claim | Correction |
|----|---------------------|------------|
| [CORRECTION-1] | ADV-33: `ALTER TABLE form_responses ALTER COLUMN form_id DROP NOT NULL` | Already applied in `20260222000000_catchup_v23.sql:247,253-266`. Included as idempotent no-op for safety. |
| [CORRECTION-2] | GAP-10: `ALTER TABLE entry_contractors ADD COLUMN updated_at` | Column already exists (added in `multi_tenant_foundation.sql:1048`). Only the UPDATE triggers are actually needed. ALTERs kept as idempotent no-ops. |
| [CORRECTION-3] | SQLite v30: `ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS email TEXT` | `IF NOT EXISTS` is invalid SQLite syntax. Must use `_addColumnIfNotExists()` helper at `database_service.dart:225`. |
| [CORRECTION-4] | user_certifications table: no RLS policies | Original plan omitted RLS. Added SELECT/INSERT/UPDATE/DELETE policies following same pattern as user_profiles. |
| [CORRECTION-5] | PII cleanup: "runs once on first launch" | No single-run mechanism was specified. Added `pii_cleanup_v1_done` pref key gate to ensure one-time execution. |
| [CORRECTION-6] | PreferencesService path | Actual path is `lib/shared/services/preferences_service.dart`, not in `lib/features/settings/`. |

---

## Files Modified/Created Summary

| Action | File Path |
|--------|-----------|
| CREATE | `supabase/migrations/20260305000000_schema_alignment_and_security.sql` |
| MODIFY | `supabase/config.toml` (line 207: secure_password_change = true) |
| MODIFY | `lib/features/auth/data/models/user_profile.dart` (4 new fields) |
| MODIFY | `lib/core/database/database_service.dart` (version bump + v30 migration) |
| MODIFY | `lib/core/database/schema/core_tables.dart` (user_profiles fresh schema) |
| MODIFY | `lib/core/database/schema/sync_tables.dart` (6 new table definitions) |
| MODIFY | `lib/shared/services/preferences_service.dart` (dead code removal + cleanup method) |
| MODIFY | `lib/features/forms/presentation/screens/mdot_hub_screen.dart` (consumer migration) |
| MODIFY | `lib/features/forms/presentation/screens/form_viewer_screen.dart` (consumer migration) |
| MODIFY | `lib/features/entries/presentation/controllers/pdf_data_builder.dart` (consumer migration) |
| MODIFY | `lib/features/entries/presentation/widgets/entry_photos_section.dart` (consumer migration) |
| MODIFY | `lib/services/sync_service.dart` (purge handler) |
| MODIFY | `lib/features/settings/presentation/screens/settings_screen.dart` (full redesign) |
| DELETE | `lib/features/settings/presentation/widgets/edit_inspector_dialog.dart` |
| MODIFY | `lib/features/settings/presentation/widgets/widgets.dart` (remove export) |
| MODIFY | Testing keys file (remove dead keys) |
| MODIFY | `lib/main.dart` (add PII cleanup call) |

---

# Part 3: Test Infrastructure & Phases 0-1


**Date**: 2026-03-05
**Scope**: Test infrastructure setup, Phase 0 (Schema + Security) verification, Phase 1 (Change Tracking Foundation)
**Parent Plan**: `.claude/plans/2026-03-04-sync-rewrite-and-settings-redesign.md`
**Dependencies**: Section B (Schema SQL) provides the Supabase migration SQL. Section A provides engine architecture context.

---

## Step 1: Test Infrastructure Setup

This step creates the shared test utilities that all subsequent sync tests depend on. Every file here must be created before any Phase 1 or Phase 2 test can run.

**[FIX: C10]** Add `mocktail: ^1.0.0` to `pubspec.yaml` dev_dependencies before writing any mock-based tests.
Current pubspec has no mocking library. All `MockSupabaseClient`, `MockDatabase`, etc. classes require mocktail.

```yaml
dev_dependencies:
  mocktail: ^1.0.0  # Required for sync engine tests
```

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

    // --- Sync engine tables (v30) ---
    // [FIX: C11] Test helper MUST use SyncEngineTables constants as single source of truth.
    // Do NOT inline DDL. This prevents schema drift between test helper, constants, and migration.
    await db.execute(SyncEngineTables.createSyncControlTable);
    await db.execute(SyncEngineTables.seedSyncControl);
    await db.execute(SyncEngineTables.createChangeLogTable);
    await db.execute(SyncEngineTables.createConflictLogTable);
    await db.execute(SyncEngineTables.createSyncLockTable);
    await db.execute(SyncEngineTables.createSyncedProjectsTable);
    await db.execute(SyncEngineTables.createSyncMetadataTable);
    for (final table in SyncEngineTables.triggeredTables) {
      for (final trigger in SyncEngineTables.triggersForTable(table)) {
        await db.execute(trigger);
      }
    }
    for (final index in SyncEngineTables.indexes) {
      await db.execute(index);
    }

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
  // [FIX: C12] project_id added per denormalization decision (C1).
  static Map<String, dynamic> entryEquipmentMap({
    String? id,
    required String entryId,
    required String equipmentId,
    String? projectId,  // NEW: denormalized project_id
    int wasUsed = 1,
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'entry_id': entryId,
    'equipment_id': equipmentId,
    'project_id': projectId,  // NEW
    'was_used': wasUsed,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 10. entry_quantities ---
  // [FIX: C12] project_id added per denormalization decision (C1).
  static Map<String, dynamic> entryQuantityMap({
    String? id,
    required String entryId,
    required String bidItemId,
    String? projectId,  // NEW: denormalized project_id
    double quantity = 10.0,
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'entry_id': entryId,
    'bid_item_id': bidItemId,
    'project_id': projectId,  // NEW
    'quantity': quantity,
    'notes': null,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 11. entry_contractors ---
  // [FIX: C12] project_id added per denormalization decision (C1).
  static Map<String, dynamic> entryContractorMap({
    String? id,
    required String entryId,
    required String contractorId,
    String? projectId,  // NEW: denormalized project_id
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'entry_id': entryId,
    'contractor_id': contractorId,
    'project_id': projectId,  // NEW
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // --- 12. entry_personnel_counts ---
  // [FIX: C12] project_id added per denormalization decision (C1).
  static Map<String, dynamic> entryPersonnelCountMap({
    String? id,
    required String entryId,
    required String contractorId,
    required String typeId,
    String? projectId,  // NEW: denormalized project_id
    int count = 3,
    String? createdByUserId = 'test-user',
  }) => {
    'id': id ?? _uuid.v4(),
    'entry_id': entryId,
    'contractor_id': contractorId,
    'type_id': typeId,
    'project_id': projectId,  // NEW
    'count': count,
    'created_at': _ts(),
    'updated_at': _ts(),
    'created_by_user_id': createdByUserId,
    'deleted_at': null,
    'deleted_by': null,
  };

  // NOTE [FIX: C12]: seedFkGraph and any callers that insert into these junction tables
  // should pass projectId from the seeded project for accurate denormalization testing.

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

**IMPORTANT**: PART 0 (Storage RLS fix) should be deployed as a **separate migration file** before the main migration, to protect the storage RLS fix from rollback if later PARTs fail. If the main migration is rolled back, the critical storage RLS fix remains in place.

Deploy the migration file(s) containing all 16 PARTs (0-15) in order:

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
| 2.2.15 | PART 14 | Security | Fix all SECURITY DEFINER functions to add `SET search_path = public` |
| 2.2.16 | PART 15 | Sync perf | Denormalize `project_id` onto junction tables for simpler pull queries |

> **DEFERRED TO BACKLOG**: The original PARTs 15-16 (ADV-13/NEW-13 "edit_own_records" RLS UPDATE policies, ADV-60 admin_audit_log table) are deferred to a future migration. They are not required for the sync rewrite and can be implemented independently. The denormalization step has been re-numbered as PART 15.

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

**PREREQUISITE: Phase 0 completion gate must pass before proceeding to Phase 1.**

All items in 2.5.x must pass before proceeding to Phase 1. Record results in `.claude/test-results/phase0-verification.md`.

### 2.7 Security Notes (from Deferred Security Review)

The following items from the adversarial security review are handled as follows:

- **ADV-55** (SQLite encryption / sqlcipher): **EXCLUDED from this plan.** Tracked separately as a future blocker. See dedicated sqlcipher migration plan when created.
- **ADV-61** (Viewer role reads all company data): **Intentional design decision.** Company-wide read access for viewers is by design. No action needed.
- **ADV-63** (change_log tamper protection on rooted device): **Accepted risk.** RLS prevents cross-tenant damage. Anomaly detection for impossible timestamps will be added to the IntegrityChecker (Phase 5) -- flag change_log entries with `changed_at` timestamps in the future or before the user's account creation date.

---

## Step 3: Phase 1 -- Change Tracking Foundation

**PREREQUISITE: Phase 0 completion gate must pass before starting Phase 1.**

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
    project_id TEXT,
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

// Step 2: Copy data, replacing empty strings with proper timestamps, including project_id
await db.execute('''
  INSERT INTO entry_personnel_counts_new
    (id, entry_id, contractor_id, type_id, count, project_id,
     created_at, updated_at, created_by_user_id, deleted_at, deleted_by)
  SELECT
    id, entry_id, contractor_id, type_id, count, project_id,
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

#### 3.1.11 Upgrade-Path Data Migrations (v30 _onUpgrade, AFTER tables + triggers)

These migration steps run inside the v30 `_onUpgrade` block, AFTER all tables are created and triggers are installed. They migrate existing data to populate the new infrastructure tables.

**Step 1: Auto-populate `synced_projects` from existing `projects`**

Existing users already have projects in their local database. Populate `synced_projects` so the pull scope includes all their current projects:

```sql
INSERT OR IGNORE INTO synced_projects (project_id, synced_at)
SELECT id, strftime('%Y-%m-%dT%H:%M:%fZ', 'now') FROM projects
```

**Step 2: Migrate `sync_queue` entries to `change_log`**

The old `sync_queue` table may contain unprocessed sync operations. Migrate them to the new `change_log` table so they are not lost:

```sql
INSERT INTO change_log (table_name, record_id, operation, changed_at, processed)
SELECT table_name, record_id, operation, created_at, 0 FROM sync_queue
```

**Step 3: Log migration counts**

After both migration steps, log the counts for debugging:

```dart
final syncedCount = (await db.rawQuery('SELECT COUNT(*) as c FROM synced_projects')).first['c'] as int;
final migratedCount = (await db.rawQuery(
  "SELECT COUNT(*) as c FROM change_log WHERE changed_at IN (SELECT created_at FROM sync_queue)"
)).first['c'] as int;
debugPrint('v30 migration: populated $syncedCount synced_projects, migrated $migratedCount sync_queue entries');
```

**Step 4: Clear stale sync_lock**

Prevent stale locks from a previous app crash from blocking the first sync after upgrade:

```sql
DELETE FROM sync_lock
```

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

### 3.2.1 Update Schema File Constants + _onCreate

After tables and triggers are created in the v30 migration, the schema file constants and `_onCreate` must also be updated so that fresh installs create the correct schema.

#### 3.2.1.1 Update `personnel_tables.dart`

**File**: `lib/core/database/schema/personnel_tables.dart`
**Action**: Modify

1. Fix GAP-11 defaults: Change empty-string defaults (`DEFAULT ''`) to ISO timestamp defaults (`DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))`) for `created_at` and `updated_at` columns in the `entry_personnel_counts` CREATE TABLE constant.
2. Add `project_id TEXT` column to the `entry_personnel_counts` CREATE TABLE constant (for project_id denormalization).

#### 3.2.1.2 Update `entry_tables.dart`

**File**: `lib/core/database/schema/entry_tables.dart`
**Action**: Modify

Add `project_id TEXT` column to the `entry_contractors` and `entry_equipment` CREATE TABLE constants (for project_id denormalization).

#### 3.2.1.3 Update `quantity_tables.dart`

**File**: `lib/core/database/schema/quantity_tables.dart`
**Action**: Modify

Add `project_id TEXT` column to the `entry_quantities` CREATE TABLE constant (for project_id denormalization).

#### 3.2.1.4 Create `sync_engine_tables.dart`

**File**: `lib/core/database/schema/sync_engine_tables.dart`
**Action**: Create

Define all 7 new table DDL constants (one per table):
1. `sync_control` (from 3.1.1)
2. `change_log` (from 3.1.2)
3. `conflict_log` (from 3.1.3)
4. `sync_lock` (from 3.1.4)
5. `synced_projects` (from 3.1.5)
6. `sync_metadata` (already exists in sync_tables.dart -- verify location)
7. `storage_cleanup_queue` (from Decision 10, P4-4)

Each constant is a `static const String` matching the exact DDL from sections 3.1.1-3.1.5 above plus the storage_cleanup_queue schema.

#### 3.2.1.5 Update `_onCreate` in `database_service.dart`

**File**: `lib/core/database/database_service.dart`
**Action**: Modify

In the `_onCreate` method, add calls to execute all `SyncEngineTables` constants so that fresh installs get the complete v30 schema without running migrations:
```dart
// Sync engine infrastructure tables
await db.execute(SyncEngineTables.createSyncControlTable);
await db.execute("INSERT OR IGNORE INTO sync_control (key, value) VALUES ('pulling', '0')");
await db.execute(SyncEngineTables.createChangeLogTable);
await db.execute(SyncEngineTables.createConflictLogTable);
await db.execute(SyncEngineTables.createSyncLockTable);
await db.execute(SyncEngineTables.createSyncedProjectsTable);
await db.execute(SyncEngineTables.createStorageCleanupQueueTable);
// Install all 48 triggers
// ... (same trigger installation loop as in 3.2)
```

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

Add the 7 new tables to `expectedSchema`:

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
'sync_metadata': [
  'key', 'value',
],
'user_certifications': [
  'id', 'user_id', 'cert_type', 'cert_number', 'expiry_date',
  'created_at', 'updated_at',
],
```

> **Note**: This is now 7 new tables (6 sync engine + user_certifications).

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

#### 3.5.5 sync_queue Migration Test (FIX: H7)

**File**: `test/features/sync/schema/sync_queue_migration_test.dart`
**Action**: Create

**[FIX: H7]** Add migration test: `sync_queue` → `change_log` data preservation

```dart
test('v30 migration copies sync_queue entries to change_log', () async {
  // 1. Create v29 database with sync_queue entries
  // 2. Run v30 migration
  // 3. Verify change_log has entries with correct column mapping:
  //    sync_queue.table_name → change_log.table_name
  //    sync_queue.record_id → change_log.record_id
  //    sync_queue.operation → change_log.operation
  //    sync_queue.created_at → change_log.changed_at
  //    change_log.processed = 0 (all unprocessed)
});
```

#### 3.5.6 CASCADE DELETE Trigger Tests (FIX: H8)

**File**: `test/features/sync/triggers/cascade_delete_trigger_test.dart`
**Action**: Create

**[FIX: H8]** Add CASCADE DELETE trigger tests:

```dart
test('CASCADE DELETE on project fires delete triggers for entries and photos', () async {
  // 1. Create project → entry → photo chain
  // 2. Clear change_log
  // 3. DELETE project (cascades)
  // 4. Verify change_log has delete entries for entry AND photo
});

test('CASCADE DELETE with pulling=1 does NOT fire triggers', () async {
  // 1. Set sync_control pulling='1'
  // 2. DELETE project (cascades)
  // 3. Verify change_log is empty
});
```

### 3.6 Phase 1 Completion Gate

All items below must pass before proceeding to Phase 2:

- [ ] All 48 triggers verified (3.5.1) -- `pwsh -Command "flutter test test/features/sync/triggers/change_log_trigger_test.dart"`
- [ ] Trigger behavior tests pass (3.5.2) -- `pwsh -Command "flutter test test/features/sync/triggers/trigger_behavior_test.dart"`
- [ ] Schema table tests pass (3.5.3) -- `pwsh -Command "flutter test test/features/sync/schema/sync_schema_test.dart"`
- [ ] entry_personnel_counts rebuild verified (3.5.4) -- `pwsh -Command "flutter test test/features/sync/schema/entry_personnel_counts_rebuild_test.dart"`
- [ ] Schema verifier includes all 7 new tables (sync_control, change_log, conflict_log, sync_lock, synced_projects, sync_metadata, user_certifications)
- [ ] `created_by_user_id` stamped at model creation for DailyEntry and Photo (at minimum)
- [ ] SQLite version bumped to 30
- [ ] **Cascade soft-delete benchmark**: Cascade soft-delete 500 records with triggers installed. Target: <500ms on mid-range device. If >500ms, optimize triggers before proceeding to Phase 2. Test procedure: create 500 records across parent/child tables, soft-delete the parent, measure total time including all trigger-generated change_log entries.
- [ ] Full test suite passes -- `pwsh -Command "flutter test"`

Record results in `.claude/test-results/phase1-verification.md`.

---

## Appendix: Canonical v30 Migration Sequence (Dart)

> **CANONICAL REFERENCE**: This is the authoritative ordering for the v30 migration block in `database_service.dart`. If any section above conflicts with this order, this appendix takes precedence.

**[FIX: H15]** Wrap v30 migration in a transaction for crash safety:

```dart
if (oldVersion < 30) {
  await db.transaction((txn) async {
    // 1. Create all infrastructure tables (atomic)
    await txn.execute(SyncEngineTables.createSyncControlTable);
    await txn.execute(SyncEngineTables.seedSyncControl);
    await txn.execute(SyncEngineTables.createChangeLogTable);
    // ... all tables, indexes, triggers ...
  });

  // 2. Non-critical operations outside transaction (can retry)
  try {
    await db.execute('''
      INSERT OR IGNORE INTO synced_projects (project_id, synced_at)
      SELECT id, '${DateTime.now().toIso8601String()}' FROM projects
    ''');
    await db.execute('''
      INSERT INTO change_log (table_name, record_id, operation, changed_at, processed)
      SELECT table_name, record_id, operation, created_at, 0 FROM sync_queue
    ''');
  } catch (e) {
    DebugLogger.error('V30: Non-critical migration step failed', error: e);
  }
}
```

Reserve v32 migration slot for forward-only recovery if v30/v31 partially fails.

```dart
// Migration from version 29 to 30: Sync engine foundation
if (oldVersion < 30) {
  // === Phase A: Create infrastructure tables + seed ===
  // 3.1.1: sync_control table
  await db.execute('''CREATE TABLE IF NOT EXISTS sync_control (...)''');
  await db.execute("INSERT OR IGNORE INTO sync_control (key, value) VALUES ('pulling', '0')");

  // 3.1.2: change_log table + index
  await db.execute('''CREATE TABLE IF NOT EXISTS change_log (...)''');
  await db.execute('CREATE INDEX IF NOT EXISTS idx_change_log_unprocessed ...');

  // 3.1.3: conflict_log table + index
  await db.execute('''CREATE TABLE IF NOT EXISTS conflict_log (...)''');
  await db.execute('CREATE INDEX IF NOT EXISTS idx_conflict_log_expires ...');

  // 3.1.4: sync_lock table
  await db.execute('''CREATE TABLE IF NOT EXISTS sync_lock (...)''');

  // 3.1.5: synced_projects table
  await db.execute('''CREATE TABLE IF NOT EXISTS synced_projects (...)''');

  // 3.1.6: user_certifications table
  await db.execute('''CREATE TABLE IF NOT EXISTS user_certifications (...)''');

  // P4-4: storage_cleanup_queue table
  await db.execute('''CREATE TABLE IF NOT EXISTS storage_cleanup_queue (...)''');

  // === Phase B: Create indexes ===
  // (indexes for change_log, conflict_log already created above with their tables)

  // === Phase C: Profile expansion columns ===
  // 3.1.7: Profile expansion columns
  await _addColumnIfNotExists(db, 'user_profiles', 'email', 'TEXT');
  await _addColumnIfNotExists(db, 'user_profiles', 'agency', 'TEXT');
  await _addColumnIfNotExists(db, 'user_profiles', 'initials', 'TEXT');
  await _addColumnIfNotExists(db, 'user_profiles', 'gauge_number', 'TEXT');

  // === Phase D: project_id denormalization + backfill ===
  // Add project_id to junction tables (3 via ALTER TABLE, 1 via rebuild)
  await _addColumnIfNotExists(db, 'entry_equipment', 'project_id', 'TEXT');
  await _addColumnIfNotExists(db, 'entry_quantities', 'project_id', 'TEXT');
  await _addColumnIfNotExists(db, 'entry_contractors', 'project_id', 'TEXT');
  // entry_personnel_counts gets project_id via rebuild below

  // Backfill project_id from parent daily_entries (3 tables)
  await db.execute('''UPDATE entry_equipment SET project_id = (
    SELECT project_id FROM daily_entries WHERE id = entry_equipment.entry_id
  ) WHERE project_id IS NULL''');
  await db.execute('''UPDATE entry_quantities SET project_id = (
    SELECT project_id FROM daily_entries WHERE id = entry_quantities.entry_id
  ) WHERE project_id IS NULL''');
  await db.execute('''UPDATE entry_contractors SET project_id = (
    SELECT project_id FROM daily_entries WHERE id = entry_contractors.entry_id
  ) WHERE project_id IS NULL''');

  // === Phase E: entry_personnel_counts rebuild (with project_id) ===
  // 3.1.8: GAP-11 fix -- MUST be before triggers
  await db.execute('''CREATE TABLE IF NOT EXISTS entry_personnel_counts_new (
    ... includes project_id TEXT ...
  )''');
  await db.execute('''INSERT INTO entry_personnel_counts_new
    (... project_id ...) SELECT ... project_id ... FROM entry_personnel_counts''');
  await db.execute('DROP TABLE entry_personnel_counts');
  await db.execute('ALTER TABLE entry_personnel_counts_new RENAME TO entry_personnel_counts');
  await db.execute('CREATE INDEX IF NOT EXISTS idx_entry_personnel_counts_entry ...');
  await db.execute('CREATE INDEX IF NOT EXISTS idx_entry_personnel_counts_type ...');
  await db.execute('CREATE INDEX IF NOT EXISTS idx_entry_personnel_counts_deleted_at ...');
  // Backfill project_id for entry_personnel_counts (may already have values from copy)
  await db.execute('''UPDATE entry_personnel_counts SET project_id = (
    SELECT project_id FROM daily_entries WHERE id = entry_personnel_counts.entry_id
  ) WHERE project_id IS NULL''');

  // === Phase F: UNIQUE index on projects ===
  // 3.1.9
  await db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_company_number ...');

  // === Phase G: Install all 48 triggers (AFTER table rebuild) ===
  // 3.2
  const syncedTables = ['projects', 'locations', ...]; // 16 tables
  for (final table in syncedTables) {
    // INSERT, UPDATE, DELETE triggers with sync_control WHEN clause
  }

  // === Phase H: Auto-populate synced_projects (3.1.11 Step 1) ===
  await db.execute('''INSERT OR IGNORE INTO synced_projects (project_id, synced_at)
    SELECT id, strftime('%Y-%m-%dT%H:%M:%fZ', 'now') FROM projects''');

  // === Phase I: Migrate sync_queue to change_log (3.1.11 Step 2) ===
  await db.execute('''INSERT INTO change_log (table_name, record_id, operation, changed_at, processed)
    SELECT table_name, record_id, operation, created_at, 0 FROM sync_queue''');

  // === Phase J: Clear stale sync_lock (3.1.11 Step 4) ===
  await db.execute('DELETE FROM sync_lock');

  // === Phase K: Log migration counts (3.1.11 Step 3) ===
  // debugPrint('v30 migration: populated N synced_projects, migrated N sync_queue entries');
}
```

**Order is critical**:
1. Infrastructure tables + seed first
2. Indexes
3. Profile expansion columns
4. project_id denormalization + backfill
5. entry_personnel_counts rebuild (with project_id) -- MUST be before triggers
6. UNIQUE index on projects
7. Install 48 triggers -- MUST be after rebuild (DROP TABLE removes triggers)
8. Auto-populate synced_projects
9. Migrate sync_queue to change_log
10. Clear stale sync_lock

---

# Part 4: Phases 2-3 — Engine & Adapters


**Source Plan**: `.claude/plans/2026-03-04-sync-rewrite-and-settings-redesign.md` (lines 1433-1527)
**Architecture Reference**: `.claude/plans/sections/section-a-architecture.md` (Steps 9-16)
**Analysis**: Verified against codebase by analysis agent
**Current DB Version**: 29 (at `lib/core/database/database_service.dart:54`)

**PREREQUISITE**: Phase 1 (Section A -- architecture, schema, migration, adapters) must be complete and all integration tests passing before Phase 2 begins. The 5 engine tables (`sync_control`, `change_log`, `conflict_log`, `sync_lock`, `synced_projects`), all 16 triggers, the `TableAdapter` base class, all 16 concrete adapters, `SyncRegistry`, `SyncConfig`, `ScopeType`, and all 4 `TypeConverter` implementations must be in place.

---

## Step 1: Phase 2 -- Sync Engine Core

**PREREQUISITE: Phase 1 completion gate must pass before starting Phase 2.**

Phase 2 builds the runtime engine classes that read/write the infrastructure tables from Phase 1. No table adapters are connected yet -- mock adapters are used in tests.

### 1.1 SyncMutex

**File**: `lib/features/sync/engine/sync_mutex.dart`
**Action**: Create
**Depends on**: Phase 1 (sync_lock table exists)

The SyncMutex provides a cross-isolate lock using the `sync_lock` SQLite table. It guarantees only one sync process (foreground or background WorkManager isolate) runs at a time.

#### 1.1.1 Class definition

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

  /// Force-clear locks owned by this process. Called on app startup and in SyncEngine constructor.
  /// [P2-4 fix] Only clear our own lock, not locks held by other processes (e.g., WorkManager).
  Future<void> forceReset(String lockedBy) async {
    await _db.execute('DELETE FROM sync_lock WHERE locked_by = ?', [lockedBy]);
  }
}
```

#### 1.1.2 Key behaviors

- **Constructor**: Takes a single `Database` parameter.
- **`tryAcquire(String lockedBy)`**: The `lockedBy` parameter is either `'foreground'` or `'background'`. Stale lock expiry uses `SyncEngineConfig.staleLockTimeout` (5 minutes). The INSERT into the single-row table (CHECK constraint `id = 1`) fails if another lock is held, returning `false`.
- **`release()`**: Deletes the lock row unconditionally.
- **`forceReset()`**: Deletes ALL rows from sync_lock. Called on app startup and in the `SyncEngine` constructor to recover from any prior crash.
- **Non-reentrancy**: The sync_lock table enforces `id = 1` uniqueness. The engine adds a debug-mode assertion (`_insidePushOrPull`) as a secondary guard.

---

### 1.2 ChangeTracker

**File**: `lib/features/sync/engine/change_tracker.dart`
**Action**: Create
**Depends on**: Phase 1 (change_log table exists)

The ChangeTracker reads trigger-populated `change_log` entries, groups them by table for the push flow, and provides mark/prune operations.

#### 1.2.1 ChangeEntry data class

```dart
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
```

#### 1.2.2 ChangeTracker class definition

```dart
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/core/logging/debug_logger.dart';

class ChangeTracker {
  final Database _db;

  ChangeTracker(this._db);
```

#### 1.2.3 Methods

**`getUnprocessedChanges()`** -- returns `Future<Map<String, List<ChangeEntry>>>`

1. Query total unprocessed count: `SELECT COUNT(*) as cnt FROM change_log WHERE processed = 0`
2. If count > `SyncEngineConfig.pushAnomalyThreshold` (1000), log anomaly via `DebugLogger.sync()`
3. Query entries: `SELECT * FROM change_log WHERE processed = 0 ORDER BY changed_at ASC LIMIT {pushBatchLimit}` (limit = 500)
4. Group results by `table_name`, preserving order within each group
5. Return the grouped map

**`hasFailedEntries(String tableName)`** -- returns `Future<bool>`

Query: `SELECT COUNT(*) as cnt FROM change_log WHERE processed = 0 AND table_name = ? AND retry_count >= {maxRetryCount}`
Returns true if count > 0. Used by the FK dependency pre-check in push flow.

**`markProcessed(int changeId)`** -- returns `Future<void>`

Update: `UPDATE change_log SET processed = 1 WHERE id = ?`

**`markFailed(int changeId, String errorMessage)`** -- returns `Future<void>`

Update: `UPDATE change_log SET error_message = ?, retry_count = retry_count + 1 WHERE id = ?`

**`insertManualChange(String tableName, String recordId, String operation)`** -- returns `Future<void>`

Insert: `INSERT INTO change_log (table_name, record_id, operation) VALUES (?, ?, ?)`
Used when local wins a conflict during pull (bypasses suppressed triggers). This is the ONE exception to the rule that only triggers populate change_log.

**`pruneProcessed()`** -- returns `Future<int>`

Delete: `DELETE FROM change_log WHERE processed = 1 AND changed_at < strftime('%Y-%m-%dT%H:%M:%f', 'now', '-{changeLogRetention.inDays} days')`
Returns the number of deleted rows. Called after each successful sync cycle.

---

### 1.3 ConflictResolver

**File**: `lib/features/sync/engine/conflict_resolver.dart`
**Action**: Create
**Depends on**: Phase 1 (conflict_log table exists)

The ConflictResolver implements Last-Write-Wins (LWW) comparison and logs conflicts with changed-columns-only diffs to minimize PII exposure.

#### 1.3.1 ConflictWinner enum

```dart
enum ConflictWinner { local, remote }
```

#### 1.3.2 Class definition

```dart
import 'dart:convert';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';

class ConflictResolver {
  final Database _db;

  ConflictResolver(this._db);
```

#### 1.3.3 `resolve()` method

Signature: `Future<ConflictWinner> resolve({required String tableName, required String recordId, required Map<String, dynamic> local, required Map<String, dynamic> remote})`

**LWW comparison rules:**
1. Extract `local['updated_at']` and `remote['updated_at']` as `String?`
2. MUST compare the **server-assigned** `updated_at` from the pulled record, never the local client's outbound `updated_at`
3. If either timestamp is null: **remote wins** (safety default)
4. If `remoteUpdatedAt.compareTo(localUpdatedAt) >= 0`: **remote wins** (equal timestamps = remote wins as deterministic tiebreaker)
5. If local `updated_at` is strictly newer: **local wins**

**Conflict logging:**
1. Determine loser: if remote wins, loser = local; if local wins, loser = remote
2. Compute diff using `_computeLostData(winnerData, loserData)` -- only changed columns, always includes `id`
3. Set `detected_at` = `DateTime.now().toUtc().toIso8601String()`
4. Set `expires_at` = `detected_at + SyncEngineConfig.conflictLogRetention` (7 days)
5. Insert into `conflict_log`: `table_name`, `record_id`, `winner` ('local' or 'remote'), `lost_data` (JSON-encoded diff), `detected_at`, `expires_at`

#### 1.3.4 `_computeLostData()` method

```dart
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
```

This stores only the columns that differ between winner and loser, plus the record `id` for identification. This is the Decision 8 PII mitigation -- full records are never stored in conflict_log.

#### 1.3.5 `pruneExpired()` method

```sql
DELETE FROM conflict_log
WHERE dismissed_at IS NOT NULL
  AND expires_at < strftime('%Y-%m-%dT%H:%M:%f', 'now')
```

Only dismissed conflicts are auto-deleted. Undismissed conflicts are kept indefinitely. A warning is shown in the UI for undismissed conflicts older than 30 days.

---

### 1.4 SyncEngine

**File**: `lib/features/sync/engine/sync_engine.dart`
**Action**: Create
**Depends on**: SyncMutex (1.1), ChangeTracker (1.2), ConflictResolver (1.3), IntegrityChecker (Section A Step 12), SyncRegistry (Section A Step 7), SyncConfig (Section A Step 8), all adapters (Section A Step 6)

This is the core push/pull orchestrator that replaces the legacy `SyncService` push/pull logic.

#### 1.4.1 SyncEngineResult

```dart
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
}
```

#### 1.4.2 Progress callback typedef

```dart
typedef SyncProgressCallback = void Function(String tableName, int processed, int? total);
```

#### 1.4.3 Constructor

```dart
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

  bool _insidePushOrPull = false; // Debug-mode reentrancy guard

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
```

Parameters:
- `db`: SQLite database instance (from `DatabaseService`)
- `supabase`: Supabase client (from `Supabase.instance.client`)
- `companyId`: Current user's company ID (from `AuthProvider.userProfile.companyId`)
- `userId`: Current user's ID (for user-stamp columns and deletion notifications)
- `lockedBy`: `'foreground'` or `'background'` (for sync_lock attribution)
- `onProgress`: Optional callback for UI progress tracking

#### 1.4.4 `resetState()` method

Called on app startup and before each sync cycle:
```dart
Future<void> resetState() async {
  await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
  await _mutex.forceReset();
}
```

#### 1.4.5 `pushAndPull()` -- top-level orchestrator

**[FIX: A3]** Explicit method signatures for SyncEngine:

```dart
Future<SyncEngineResult> pushAndPull() async { ... }
Future<SyncEngineResult> pushOnly() async { ... }  // For testing
Future<SyncEngineResult> pullOnly() async { ... }  // For testing
```

```
pushAndPull():
  1. Force-reset sync_control.pulling = '0' (startup safety)
  2. Acquire lock via _mutex.tryAcquire(lockedBy)
     - If lock held, return SyncEngineResult(lockFailed: true)
  3. Assert !_insidePushOrPull (debug-mode reentrancy guard)
  4. Set _insidePushOrPull = true
  try:
  5. Execute _push()
  6. Execute _pull()
  7. Prune: _changeTracker.pruneProcessed()
  8. Prune: _conflictResolver.pruneExpired()
  9. Integrity check: if _integrityChecker.shouldRun(), run it (catch errors, don't fail sync)
  10. Return pushResult + pullResult
  finally:
  11. Set _insidePushOrPull = false
  12. Release lock via _mutex.release()
```

#### 1.4.6 `_push()` -- push flow

```
_push():
  1. Call _changeTracker.getUnprocessedChanges() -> grouped by table
  2. Iterate tables in _registry.dependencyOrder (FK order)
  3. For each table with changes:
     a. Get adapter from _registry.adapterFor(tableName)
     b. FK DEPENDENCY PRE-CHECK:
        - For each parent in adapter.fkDependencies:
          if _changeTracker.hasFailedEntries(parent):
            - Mark all changes for this table as failed: "Blocked by parent sync failure in {parent}"
            - Log: "BLOCKED: {tableName} skipped due to failed entries in {parent}"
            - Skip this table
     c. For each change entry:
        - If operation == 'delete': call _pushDelete(adapter, change)
        - If operation == 'insert' or 'update': call _pushUpsert(adapter, change)
        - On success: _changeTracker.markProcessed(change.id)
        - On failure: _handlePushError(error, change)
        - Report progress: onProgress(tableName, processedInTable, changes.length)
  4. Return SyncEngineResult with pushed/errors counts
```

#### 1.4.7 `_pushDelete()` -- delete operations

```dart
Future<void> _pushDelete(TableAdapter adapter, ChangeEntry change) async {
  try {
    await supabase.from(adapter.tableName).delete().eq('id', change.recordId);
  } on PostgrestException catch (e) {
    // 404 or "not found" = record already gone on server = benign no-op
    if (e.code == '404' || e.message.contains('not found') || e.code == 'PGRST116') {
      return; // Success -- record already deleted remotely
    }
    rethrow;
  }
}
```

Key: Uses `record_id` from the change_log entry only. Does NOT attempt to read the local record (it is already hard-deleted). If the Supabase record is already gone (404), this is treated as success.

#### 1.4.8 `_pushUpsert()` -- insert/update operations

```
_pushUpsert(adapter, change):
  1. Read local record: SELECT * FROM {table} WHERE id = {change.recordId}
  2. If no local record found: log skip, return (record was deleted locally after trigger fired)
  3. adapter.validate(localRecord) -- throws on invalid data
  4. var payload = adapter.convertForRemote(localRecord)
  5. Stamp userStampColumns: for each col in adapter.userStampColumns.keys, set payload[col] = userId
  6. Stamp company_id on projects if null/empty: payload['company_id'] = companyId
  7. Stamp created_by_user_id if not set: payload['created_by_user_id'] = userId
  8. If adapter is PhotoAdapter: call _pushPhotoThreePhase() and return
  9. Otherwise: supabase.from(adapter.tableName).upsert(payload)
```

#### 1.4.9 `_pushPhotoThreePhase()` -- three-phase photo push

```
_pushPhotoThreePhase(adapter, change, localRecord, payload):
  Phase 1: Upload file
    - Check if remote_path already exists on local record -> skip upload
    - If not: read file bytes from file_path, upload to 'entry-photos' bucket
      at path 'entries/{companyId}/{entryId}/{filename}'
    - Get remotePath from upload response or existing remote_path

  Phase 2: Upsert metadata
    - Set payload['remote_path'] = remotePath (FRESH from Phase 1, not stale)
    - Upsert to Supabase photos table

  Phase 3: Mark local synced (engine bookkeeping — suppress triggers)
    - Wrap in sync_control.pulling='1' / finally pulling='0'
    - UPDATE local photos row: remote_path = remotePath, sync_status = 'synced'
    - sync_status is set here because photo UI code reads it for upload indicators
    - RULE: All engine bookkeeping writes (remote_path updates, sync_status updates,
      pruning processed change_log entries) must be wrapped in pulling='1'/finally '0'
      to prevent trigger-generated change_log entries for internal state changes

  Failure handling:
    - Phase 1 fails: change_log stays unprocessed, retry next cycle
    - Phase 2 fails: file exists in storage; next cycle Phase 1 detects it, skips, retries Phase 2
    - Phase 3 fails: next cycle re-runs; Phase 1 detects file exists, Phase 2 upserts, Phase 3 marks
```

#### 1.4.10 Error classification in `_handlePushError()`

```
_handlePushError(error, change) -> bool (true = retry once, false = permanent/exhausted):

  RULE: Maximum 2 attempts per record per cycle. After delay or auth refresh,
  retry the SAME ChangeEntry once. If the retry also fails, mark as failed.

  If error is PostgrestException:
    - 401 / JWT error:
      * Call _handleAuthError() to refresh token
      * If refresh succeeds: return true (retry the SAME change entry once)
      * If refresh fails: throw StateError('Auth refresh failed, aborting sync')
        (aborts entire sync cycle, surfaces "re-login required" in UI)
      * NEVER increment retry_count for auth failures

    - 429 (Too Many Requests) / 503 (Service Unavailable):
      * RETRYABLE with WITHIN-CYCLE exponential backoff.
      * Apply `await Future.delayed()` with exponential backoff:
        delays of 1s, 2s, 4s, 8s, 16s cap (using SyncEngineConfig.retryBaseDelay/retryMaxDelay).
      * Backoff formula: `min(retryBaseDelay * pow(2, change.retryCount), retryMaxDelay)`
      * If retryCount == 0: incrementRetry(), return true (retry once after delay)
      * If retryCount > 0: markFailed() -- max retries exhausted this cycle
      * return false

    - 400 (Bad Request) / 403 (Forbidden) / 404 (Not Found):
      * PERMANENT. Call _changeTracker.markFailed(change.id, 'Permanent: {message}')
      * return false
      * If retry_count >= maxRetryCount (5): leave unprocessed, surface in UI as
        "permanently failed -- manual intervention required"

  If error is SocketException / TimeoutException:
    * Network error -- retryable with within-cycle exponential backoff.
    * Apply `await Future.delayed()` with same backoff formula as 429/503.
    * If retryCount == 0: incrementRetry(), return true (retry once after delay)
    * If retryCount > 0: markFailed() -- max retries exhausted this cycle
    * return false

  Otherwise:
    * Unknown error. markFailed(change.id, error.toString())
    * return false (permanent, no retry)
```

#### 1.4.11 Auth token refresh

```dart
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
```

#### 1.4.12 `_pull()` -- pull flow

```
_pull():
  1. Load synced project IDs: _loadSyncedProjectIds()
  2. Set sync_control.pulling = '1' (suppress triggers)
  try:
  3. For each adapter in _registry.adapters (dependency order):
     - Call _pullTable(adapter)
     - Catch errors per-table (don't abort entire pull)
  4. Update last_sync_time in sync_metadata
  finally:
  5. Set sync_control.pulling = '0' (re-enable triggers -- GUARANTEED even on exception)
```

The `try/finally` block is CRITICAL. If the pull throws an exception mid-way, triggers must be re-enabled or subsequent local edits will not be tracked.

#### 1.4.13 `_pullTable()` -- per-table pull

```
_pullTable(adapter):
  1. Read cursor: SELECT value FROM sync_metadata WHERE key = 'last_pull_{tableName}'
  2. Paginated loop (pageSize = 100):
     a. Build Supabase query: supabase.from(tableName).select()
     b. Apply scope filter via _applyScopeFilter(query, adapter)
     c. If cursor exists: apply safety margin (cursor - 5 seconds) with .gte('updated_at', ...)
     d. Order by updated_at ASC, paginate with .range(offset, offset + pageSize - 1)
     e. For each remote record in page:
        - Convert: adapter.convertForLocal(remoteRaw)
        - Query local: SELECT * FROM {table} WHERE id = recordId

        If NOT exists locally:
          - If remote.deleted_at != null: SKIP (don't insert already-deleted records)
          - Strip unknown columns (PRAGMA table_info check)
          - INSERT with ConflictAlgorithm.ignore

        If EXISTS locally:
          - Deduplicate: if local.updated_at == remote.updated_at, SKIP (safety margin overlap)
          - Conflict resolution: _conflictResolver.resolve(tableName, recordId, local, remote)
          - If REMOTE WINS: UPDATE local record with remote data (strip unknown columns)
          - If LOCAL WINS (edit-wins):
            * Keep local version (no update)
            * Log conflict
            * EXPLICITLY INSERT change_log entry: _changeTracker.insertManualChange(tableName, recordId, 'update')
              This bypasses suppressed triggers -- ensures local-wins version is pushed back on next cycle

        Deletion notification:
          - If remote.deleted_at != null AND remote.deleted_by != null AND remote.deleted_by != userId:
            * Create deletion_notification row with:
              id: Uuid().v4()
              record_id: remote['id']
              table_name: adapter.tableName
              project_id: remote['project_id'] ?? localRecord?['project_id']
              record_name: adapter.extractRecordName(localRecord ?? remote)
              deleted_by: remote['deleted_by']
              deleted_by_name: lookup from user_profiles table
              deleted_at: remote['deleted_at']
              seen: 0
          - If remote.deleted_by == userId: do NOT create notification (user deleted it themselves)

        Track max updated_at for cursor update

     f. If page.length < pageSize: stop
        Else: offset += pageSize

  3. Update cursor: INSERT OR REPLACE INTO sync_metadata (key, value) VALUES ('last_pull_{tableName}', maxUpdatedAt)
```

#### 1.4.14 `_applyScopeFilter()` -- pull query scoping

> **`is_active` clarification**: The `is_active` column on projects is an admin-level concept (hide from project lists). It is NOT used for sync filtering. Sync filtering uses `synced_projects` only.

```dart
PostgrestFilterBuilder _applyScopeFilter(
  PostgrestFilterBuilder query,
  TableAdapter adapter,
) {
  switch (adapter.scopeType) {
    case ScopeType.direct:
      // projects: filter by company_id directly
      return query.eq('company_id', companyId);
    case ScopeType.viaProject:
      // Tables with project_id: filter by synced project IDs
      return query.inFilter('project_id', _syncedProjectIds);
    case ScopeType.viaEntry:
      // Tables with entry_id: filter by project_id (available after denormalization)
      // viaEntry generates the same SQL as viaProject thanks to junction table
      // denormalization, but the enum variant is kept for semantic documentation
      // of the table hierarchy.
      return query.inFilter('project_id', _syncedProjectIds);
    case ScopeType.viaContractor:
      // equipment: filter by contractor IDs within synced projects
      return query.inFilter('contractor_id', _syncedContractorIds);
  }
}
```

The engine caches `_syncedProjectIds` and `_syncedContractorIds` at the start of each pull cycle via `_loadSyncedProjectIds()`.

#### 1.4.15 `_loadSyncedProjectIds()` -- cached scope IDs

```dart
List<String> _syncedProjectIds = [];
List<String> _syncedContractorIds = [];

Future<void> _loadSyncedProjectIds() async {
  final rows = await db.query('synced_projects');
  _syncedProjectIds = rows.map((r) => r['project_id'] as String).toList();

  if (_syncedProjectIds.isNotEmpty) {
    // [P2-6 fix] Exclude soft-deleted contractors from scope
    final contractors = await db.query(
      'contractors',
      columns: ['id'],
      where: 'project_id IN (${_syncedProjectIds.map((_) => '?').join(',')}) AND deleted_at IS NULL',
      whereArgs: _syncedProjectIds,
    );
    _syncedContractorIds = contractors.map((r) => r['id'] as String).toList();
  }
}
```

#### 1.4.16 `_createDeletionNotification()` -- deletion notification helper

Looks up the deleter's display_name from user_profiles, then inserts into `deletion_notifications` (table already exists in SQLite from `sync_tables.dart:22`).

#### 1.4.17 `_getLocalColumns()` -- column validation helper

Caches PRAGMA table_info results per table per cycle. Used to strip remote columns that don't exist in local SQLite schema before INSERT/UPDATE, preventing "no such column" errors.

---

### 1.5 SoftDeleteService Purge Redesign

**File**: `lib/services/soft_delete_service.dart`
**Action**: Modify
**Depends on**: Phase 1 (sync_control, change_log tables exist)

The current `SoftDeleteService.purgeExpiredRecords()` method hard-DELETEs rows. In the trigger-based engine, hard DELETEs fire the `AFTER DELETE` trigger, which would insert `operation='delete'` change_log entries. But these purged records are ALREADY deleted on Supabase -- we don't want to push DELETE operations for records that the server already knows are gone.

#### 1.5.1 Redesigned `purgeExpiredRecords()`

The purge flow must suppress triggers during hard DELETE, then manually insert `operation='delete'` change_log entries for any records that need remote cleanup.

```
purgeExpiredRecords(retentionDays, lastSyncTime):
  1. Calculate cutoff timestamp using MAX(local_clock, lastSyncTime) - retentionDays
  2. Set sync_control.pulling = '1' (suppress triggers during hard DELETE)
  try:
  3. For each table in _childToParentOrder:
     a. SELECT id FROM {table} WHERE deleted_at IS NOT NULL AND deleted_at < cutoff
     b. DELETE FROM {table} WHERE deleted_at IS NOT NULL AND deleted_at < cutoff
     c. For each deleted ID:
        - INSERT INTO change_log (table_name, record_id, operation) VALUES (table, id, 'delete')
        - This manually-inserted change_log entry ensures the delete is pushed to Supabase
  finally:
  4. Set sync_control.pulling = '0' (re-enable triggers)
```

#### 1.5.2 Redesigned `hardDeleteWithSync()`

The current method accepts a `queueSync` callback parameter. This must be removed and replaced with direct change_log insertion.

**Before** (current):
```dart
Future<void> hardDeleteWithSync(
  String tableName,
  String id, {
  required Future<void> Function(String table, String recordId, String operation) queueSync,
}) async {
  final database = await _dbService.database;
  await database.delete(tableName, where: 'id = ?', whereArgs: [id]);
  await queueSync(tableName, id, 'purge');
}
```

**After** (redesigned):
```dart
Future<void> hardDeleteWithSync(String tableName, String id) async {
  final database = await _dbService.database;

  // Suppress triggers during hard delete
  await database.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
  try {
    await database.delete(tableName, where: 'id = ?', whereArgs: [id]);
    // Manually insert change_log entry for remote delete
    await database.insert('change_log', {
      'table_name': tableName,
      'record_id': id,
      'operation': 'delete',
    });
  } finally {
    await database.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
  }
}
```

Key changes:
- Remove `queueSync` callback parameter (breaking change -- callers must be updated)
- Use `sync_control.pulling = '1'` to suppress the AFTER DELETE trigger
- Manually INSERT `change_log` entry with `operation='delete'` after the hard delete
- Use `try/finally` to guarantee trigger re-enablement

#### 1.5.3 Cascade soft-delete methods (no change needed)

`cascadeSoftDeleteProject()` and `cascadeSoftDeleteEntry()` use UPDATE to set `deleted_at`. This fires the AFTER UPDATE trigger, which produces `operation='update'` change_log entries. The push flow reads the local record, finds `deleted_at` set, and upserts it to Supabase with the soft-delete timestamp. No changes needed to cascade methods.

#### 1.5.4 Callers to update

Search for all callers of `hardDeleteWithSync` and remove the `queueSync` parameter:
- `lib/features/entries/presentation/providers/` (trash-related providers)
- Any screen that offers "Delete Forever" from trash

---

### 1.6 Phase 2 Tests

All test files go in `test/features/sync/engine/`.

#### 1.6.1 ChangeTracker tests
**File**: `test/features/sync/engine/change_tracker_test.dart`

Tests:
- `reads grouped changes from change_log, ordered by changed_at ASC`
- `marks entries as processed (processed = 1)`
- `respects retry limit in hasFailedEntries()`
- `with 600 unprocessed entries, getUnprocessedChanges() only returns 500 (oldest first)`
- `anomaly flag logged when unprocessed count > 1000`
- `insertManualChange() creates an entry that appears in next getUnprocessedChanges()`
- `pruneProcessed() deletes entries older than 7 days with processed=1`
- `pruneProcessed() does NOT delete unprocessed entries regardless of age`
- `markFailed() increments retry_count and sets error_message`

#### 1.6.2 ConflictResolver tests
**File**: `test/features/sync/engine/conflict_resolver_test.dart`

Tests:
- `remote wins when remote.updated_at > local.updated_at`
- `local wins when local.updated_at > remote.updated_at`
- `remote wins when timestamps are equal (deterministic tiebreaker) + conflict_log entry created`
- `remote wins when local.updated_at is null`
- `remote wins when remote.updated_at is null`
- `remote wins when both timestamps are null`
- `lost_data contains ONLY changed columns (not full record) -- Decision 8 PII mitigation`
- `lost_data always includes id field`
- `conflict_log entry has expires_at = detected_at + 7 days`
- `pruneExpired() deletes dismissed + expired entries`
- `pruneExpired() keeps undismissed entries even if expired`
- `pruneExpired() keeps dismissed entries that are not yet expired`
- Soft-delete edit-wins scenario: local has deleted_at=null (user re-edited), remote has deleted_at set. Local's updated_at > remote's => local wins, change_log entry created.

#### 1.6.3 SyncMutex tests
**File**: `test/features/sync/engine/sync_mutex_test.dart`

Tests:
- `tryAcquire() returns true on first call`
- `tryAcquire() returns false when lock already held`
- `release() allows subsequent tryAcquire() to succeed`
- `stale lock (older than 5 minutes) is auto-expired`
- `forceReset() clears lock regardless of age`
- `locked_by is recorded correctly ('foreground' or 'background')`

#### 1.6.4 SyncEngine tests (with mock adapters)
**File**: `test/features/sync/engine/sync_engine_test.dart`

Tests:
- `push processes changes in FK dependency order`
- `push skips table when parent has failed entries (parent-blocking check)`
- `push delete operation sends DELETE by record_id, no local read attempted`
- `push delete treats 404 as success (benign no-op)`
- `push upsert calls adapter.validate() then adapter.convertForRemote()`
- `push stamps userStampColumns with current userId`
- `push stamps company_id on projects if null`
- `push stamps created_by_user_id if not set`
- `401 triggers token refresh, retry_count NOT incremented`
- `401 with failed refresh aborts entire sync cycle`
- `429 triggers within-cycle exponential backoff AND markFailed with retryable status`
  - Verify actual delay behavior: mock a 429 response, measure that `Future.delayed()` is called with increasing delays (1s, 2s, 4s based on retryCount)
  - Verify delay is capped at 16s (SyncEngineConfig.retryMaxDelay)
- `503 triggers same exponential backoff as 429`
- `Network timeout triggers exponential backoff before markFailed`
- `400/403/404 triggers markFailed with permanent status`
- `pull suppresses triggers (sync_control.pulling = '1') during pull`
- `pull re-enables triggers even on exception (try/finally guarantee)`
- `pull: remote soft-delete by different user creates deletion_notification row`
- `pull: remote soft-delete by SAME user does NOT create deletion_notification`
- `pull: edit-wins conflict creates explicit change_log entry via insertManualChange()`
- `pull: skips already-deleted records that don't exist locally`
- `pull: deduplicates records with identical updated_at`
- `pull: applies scope filter based on synced_projects`
- `pushAndPull() acquires lock, runs push+pull, releases lock`
- `pushAndPull() returns lockFailed when lock held by another process`
- `pushAndPull() calls pruneProcessed() and pruneExpired() after sync`
- `pushAndPull() runs integrity check if due`
- `pushAndPull() releases lock even on exception (finally block)`

#### 1.6.5 SoftDeleteService purge tests
**File**: `test/services/soft_delete_service_test.dart` (update existing)

Tests:
- `purgeExpiredRecords() suppresses triggers during hard delete`
- `purgeExpiredRecords() inserts change_log entries for purged records`
- `purgeExpiredRecords() re-enables triggers even on error (try/finally)`
- `hardDeleteWithSync() no longer requires queueSync callback`
- `hardDeleteWithSync() suppresses triggers and manually inserts change_log`

### 1.7 Phase 2 Completion Gate

- [ ] `pwsh -Command "flutter analyze"` -- 0 issues
- [ ] `pwsh -Command "flutter test"` -- all pass
- [ ] SyncMutex tests pass (lock acquisition, release, force reset, stale lock detection)
- [ ] ChangeTracker tests pass (read unprocessed, group by table, mark failed, prune processed)
- [ ] ConflictResolver tests pass (LWW resolution, conflict_log insertion, prune expired)
- [ ] SyncEngine tests pass (push ordering, pull trigger suppression, error handling, retry logic)
- [ ] SoftDeleteService purge tests pass (trigger suppression during purge, change_log insertion)
- [ ] Results recorded to `.claude/test-results/phase2-verification.md`

---

## Step 2: Phase 3 -- Table Adapters

**PREREQUISITE: Phase 2 completion gate must pass before starting Phase 3.**

Phase 3 implements the 16 concrete table adapters that were defined in Section A Step 6. Each adapter is a pure configuration/conversion object -- no Supabase I/O. The SyncEngine handles all network calls; adapters only declare schema mapping, type converters, and validation rules.

**Implementation order** (FK dependency chain):
1. projects (root)
2. locations, contractors, bid_items, personnel_types (one-hop via project_id)
3. equipment (via contractor_id)
4. daily_entries (via project_id)
5. photos (via entry_id)
6. entry_equipment, entry_quantities (via entry_id)
7. entry_contractors, entry_personnel_counts (via entry_id -- formerly unsynced, GAP-6)
8. inspector_forms, form_responses, todo_items, calculation_history (via project_id)

### 2.1 ProjectAdapter

**File**: `lib/features/sync/adapters/project_adapter.dart`
**Class**: `ProjectAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'projects'` |
| `scopeType` | `ScopeType.direct` |
| `fkDependencies` | `const []` (root table) |
| `converters` | `{'is_active': BoolIntConverter()}` |
| `localOnlyColumns` | `const ['sync_status']` |
| `remoteOnlyColumns` | `const []` |
| `userStampColumns` | `const {}` |

**SQLite columns** (from `core_tables.dart`):
`id, name, project_number, client_name, description, created_at, updated_at, is_active, mode, mdot_contract_id, mdot_project_code, mdot_county, mdot_district, control_section_id, route_street, construction_eng, company_id, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. Strip `sync_status` (listed in localOnlyColumns -- note: projects table does NOT have this column in current schema, so stripping is a no-op safety measure)
2. Convert `is_active`: SQLite `INTEGER 0/1` -> Supabase `BOOLEAN true/false` via `BoolIntConverter.toRemote()`

**`convertForLocal()`**:
1. Convert `is_active`: Supabase `BOOLEAN` -> SQLite `INTEGER` via `BoolIntConverter.toLocal()`

**`validate()` rules**:
- Reject records with `project_number` that duplicates an existing project in the same `company_id` (query local SQLite: `SELECT id FROM projects WHERE project_number = ? AND company_id = ? AND id != ?`)
- Implementation: override `validate()` -- NOTE: this requires `Database` access. The validate method must accept a `Database` parameter or the adapter must receive it in its constructor. **Resolution**: The SyncEngine passes the Database to validate() via a context parameter, OR the validation is done in the engine before calling the adapter. The recommended approach: the engine performs this validation for ProjectAdapter specifically, since adapter.validate() is designed for simple field checks. The duplicate check is a cross-record query.
- **Alternative (recommended)**: Add an optional `Database? db` parameter to `TableAdapter.validate()` for adapters that need cross-record queries. ProjectAdapter overrides to check duplicates.

**`extractRecordName()`**: Default implementation returns `record['name']` which is the project name.

---

### 2.2 LocationAdapter

**File**: `lib/features/sync/adapters/location_adapter.dart`
**Class**: `LocationAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'locations'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `core_tables.dart`):
`id, project_id, name, description, latitude, longitude, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**: No type conversions needed. Default implementation passes all columns through.

**`convertForLocal()`**: No type conversions needed.

**`validate()`**: No special validation (default no-op).

**`extractRecordName()`**: Default returns `record['name']`.

---

### 2.3 ContractorAdapter

**File**: `lib/features/sync/adapters/contractor_adapter.dart`
**Class**: `ContractorAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'contractors'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `contractor_tables.dart`):
`id, project_id, name, type, contact_name, phone, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**: No conversions. All columns map directly.

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Default returns `record['name']`.

---

### 2.4 EquipmentAdapter

**File**: `lib/features/sync/adapters/equipment_adapter.dart`
**Class**: `EquipmentAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'equipment'` |
| `scopeType` | `ScopeType.viaContractor` |
| `fkDependencies` | `const ['contractors']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `contractor_tables.dart`):
`id, contractor_id, name, description, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**Note on scope**: Equipment does NOT have a `project_id` column. It scopes through `contractor_id -> contractors.project_id`. The `ScopeType.viaContractor` filter uses `_syncedContractorIds` (pre-loaded from local contractors table).

**`convertForRemote()`**: No conversions.

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Default returns `record['name']`.

---

### 2.5 BidItemAdapter

**File**: `lib/features/sync/adapters/bid_item_adapter.dart`
**Class**: `BidItemAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'bid_items'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `quantity_tables.dart`):
`id, project_id, item_number, description, unit, bid_quantity, unit_price, bid_amount, measurement_payment, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**: No conversions. `bid_quantity`, `unit_price`, `bid_amount` are REAL in both SQLite and Supabase (NUMERIC/FLOAT8).

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Override to return `record['item_number']` + ` - ` + `record['description']` for more meaningful deletion notification names.

---

### 2.6 PersonnelTypeAdapter

**File**: `lib/features/sync/adapters/personnel_type_adapter.dart`
**Class**: `PersonnelTypeAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'personnel_types'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects', 'contractors']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `personnel_tables.dart`):
`id, project_id, contractor_id, name, short_code, sort_order, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**: No conversions.

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Default returns `record['name']`.

---

### 2.7 DailyEntryAdapter

**File**: `lib/features/sync/adapters/daily_entry_adapter.dart`
**Class**: `DailyEntryAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'daily_entries'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects', 'locations']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const ['sync_status']` |
| `remoteOnlyColumns` | `const []` |
| `userStampColumns` | `const {'updated_by_user_id': 'current'}` |

**SQLite columns** (from `entry_tables.dart`):
`id, project_id, location_id, date, weather, temp_low, temp_high, activities, site_safety, sesc_measures, traffic_control, visitors, extras_overruns, signature, signed_at, status, submitted_at, revision_number, created_at, updated_at, sync_status, created_by_user_id, updated_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. Strip `sync_status` (local-only column)
2. No type conversions needed -- all columns map directly

The SyncEngine additionally stamps `updated_by_user_id` with the current `userId` before push, as declared by `userStampColumns`.

**`convertForLocal()`**: No conversions. `sync_status` is NOT set on pull (the change_log trigger system replaces sync_status tracking).

**`validate()`**: No special validation (project_id is NOT NULL in schema, enforced at DB level).

**`extractRecordName()`**: Override to return `record['date']` + ` entry` for meaningful notification names (e.g., "2026-03-04 entry").

---

### 2.8 PhotoAdapter

**File**: `lib/features/sync/adapters/photo_adapter.dart`
**Class**: `PhotoAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'photos'` |
| `scopeType` | `ScopeType.viaEntry` |
| `fkDependencies` | `const ['daily_entries', 'projects']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const ['sync_status', 'file_path']` |
| `remoteOnlyColumns` | `const []` |
| `isPhotoAdapter` | `true` (marker for SyncEngine three-phase routing) |

**SQLite columns** (from `photo_tables.dart`):
`id, entry_id, project_id, file_path, filename, remote_path, notes, caption, location_id, latitude, longitude, captured_at, sync_status, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. Strip `sync_status` (local-only)
2. Strip `file_path` (local-only -- device filesystem path, not meaningful on server)
3. `filename` IS included in payload (used for storage path construction)
4. `remote_path` IS included (set by three-phase push)

**`convertForLocal()`**: No type conversions. `file_path` from remote is ignored (not in remote payload). `sync_status` is NOT set on pull.

**`validate()`**:
- For new photos (inserts): `file_path` must be non-null and non-empty (needed for Phase 1 upload)
- For updates: `file_path` may be null if remote_path already exists (file was previously uploaded)

**Three-phase push**: Handled by `SyncEngine._pushPhotoThreePhase()`, not by the adapter itself. The adapter provides configuration; the engine provides behavior.

**`extractRecordName()`**: Override to return `record['filename']` or `record['caption']`.

---

### 2.9 EntryEquipmentAdapter

**File**: `lib/features/sync/adapters/entry_equipment_adapter.dart`
**Class**: `EntryEquipmentAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'entry_equipment'` |
| `scopeType` | `ScopeType.viaEntry` |
| `fkDependencies` | `const ['daily_entries', 'equipment']` |
| `converters` | `{'was_used': BoolIntConverter()}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `entry_tables.dart`):
`id, entry_id, equipment_id, was_used, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. Convert `was_used`: SQLite `INTEGER 0/1` -> Supabase `BOOLEAN true/false`

**`convertForLocal()`**:
1. Convert `was_used`: Supabase `BOOLEAN` -> SQLite `INTEGER 0/1`

**`validate()`**: No special validation.

**`extractRecordName()`**: Override to return a descriptive string, e.g., `'Equipment for entry ${record['entry_id']}'`.

---

### 2.10 EntryQuantitiesAdapter

**File**: `lib/features/sync/adapters/entry_quantities_adapter.dart`
**Class**: `EntryQuantitiesAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'entry_quantities'` |
| `scopeType` | `ScopeType.viaEntry` |
| `fkDependencies` | `const ['daily_entries', 'bid_items']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `quantity_tables.dart`):
`id, entry_id, bid_item_id, quantity, notes, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**: No conversions. `quantity` is REAL in both systems.

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Override to return `'Quantity: ${record['quantity']}'`.

---

### 2.11 EntryContractorsAdapter

**File**: `lib/features/sync/adapters/entry_contractors_adapter.dart`
**Class**: `EntryContractorsAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'entry_contractors'` |
| `scopeType` | `ScopeType.viaEntry` |
| `fkDependencies` | `const ['daily_entries', 'contractors']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `entry_tables.dart`):
`id, entry_id, contractor_id, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**IMPORTANT**: This table has NEVER been synced before (GAP-6). This adapter enables net-new sync capability.

**`convertForRemote()`**: No conversions. All columns map directly.

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Default returns `record['id']`.

---

### 2.12 EntryPersonnelCountsAdapter

**File**: `lib/features/sync/adapters/entry_personnel_counts_adapter.dart`
**Class**: `EntryPersonnelCountsAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'entry_personnel_counts'` |
| `scopeType` | `ScopeType.viaEntry` |
| `fkDependencies` | `const ['daily_entries', 'contractors', 'personnel_types']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `personnel_tables.dart`):
`id, entry_id, contractor_id, type_id, count, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**IMPORTANT**: This table has NEVER been synced before (GAP-6). This adapter enables net-new sync capability. It has three FK dependencies (`daily_entries`, `contractors`, `personnel_types`).

**`convertForRemote()`**: No conversions. `count` is INTEGER in both systems.

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Override to return `'Personnel count: ${record['count']}'`.

---

### 2.13 InspectorFormAdapter

**File**: `lib/features/sync/adapters/inspector_form_adapter.dart`
**Class**: `InspectorFormAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'inspector_forms'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects']` |
| `converters` | See below |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**Converters map:**
```dart
{
  'is_builtin': BoolIntConverter(),
  'template_bytes': ByteaConverter(),
  'field_definitions': JsonMapConverter(),
  'parsing_keywords': JsonMapConverter(),
  'table_row_config': JsonMapConverter(),
}
```

**SQLite columns** (from `toolbox_tables.dart`):
`id, project_id, name, template_path, field_definitions, parsing_keywords, table_row_config, is_builtin, template_source, template_hash, template_version, template_field_count, template_bytes, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. `is_builtin`: SQLite `INTEGER 0/1` -> Supabase `BOOLEAN`
2. `template_bytes`: SQLite `BLOB (Uint8List)` -> Supabase `BYTEA (base64 string)` -- **NEW-9 fix**: this conversion did NOT exist in the old sync system
3. `field_definitions`: SQLite `TEXT (JSON string)` -> Supabase `JSONB (Map/List)` -- **GAP-16 fix**
4. `parsing_keywords`: SQLite `TEXT (JSON string)` -> Supabase `JSONB (Map/List)` -- **GAP-16 fix**
5. `table_row_config`: SQLite `TEXT (JSON string)` -> Supabase `JSONB (Map/List)`

**`convertForLocal()`**: Reverse of above:
1. `is_builtin`: Supabase `BOOLEAN` -> SQLite `INTEGER`
2. `template_bytes`: Supabase `BYTEA (base64)` -> SQLite `BLOB (Uint8List)`
3. `field_definitions`: Supabase `JSONB` -> SQLite `TEXT (JSON string)`
4. `parsing_keywords`: Supabase `JSONB` -> SQLite `TEXT (JSON string)`
5. `table_row_config`: Supabase `JSONB` -> SQLite `TEXT (JSON string)`

**`validate()`**: No-op (default). Override NOT needed.
```dart
// [P3-1 fix] Do NOT reject null project_id — built-in forms may have null project_id.
// project_id is nullable for built-in forms/items that are not tied to a specific project.
// The base class validate() is sufficient.
```

**`extractRecordName()`**: Default returns `record['name']`.

---

### 2.14 FormResponseAdapter

**File**: `lib/features/sync/adapters/form_response_adapter.dart`
**Class**: `FormResponseAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'form_responses'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects', 'inspector_forms']` |
| `converters` | See below |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**Converters map:**
```dart
{
  'response_data': JsonMapConverter(),
  'header_data': JsonMapConverter(),
  'response_metadata': JsonMapConverter(),
  'table_rows': JsonMapConverter(),
}
```

**SQLite columns** (from `toolbox_tables.dart`):
`id, form_type, form_id, entry_id, project_id, header_data, response_data, table_rows, response_metadata, status, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. `response_data`: SQLite `TEXT (JSON)` -> Supabase `JSONB`
2. `header_data`: SQLite `TEXT (JSON)` -> Supabase `JSONB`
3. `response_metadata`: SQLite `TEXT (JSON)` -> Supabase `JSONB` (nullable)
4. `table_rows`: SQLite `TEXT (JSON)` -> Supabase `JSONB` (nullable)

**`convertForLocal()`**: Reverse of above.

**`validate()`**: Handle NULL `form_id` gracefully -- do NOT reject. The FK constraint on form_id was dropped (form_responses can exist without a parent inspector_form).

**`extractRecordName()`**: Override to return `record['form_type']` for meaningful names.

---

### 2.15 TodoItemAdapter

**File**: `lib/features/sync/adapters/todo_item_adapter.dart`
**Class**: `TodoItemAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'todo_items'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects']` |
| `converters` | `{'is_completed': BoolIntConverter()}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `toolbox_tables.dart`):
`id, project_id, entry_id, title, description, is_completed, due_date, priority, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. `is_completed`: SQLite `INTEGER 0/1` -> Supabase `BOOLEAN`

**`convertForLocal()`**:
1. `is_completed`: Supabase `BOOLEAN` -> SQLite `INTEGER`

**`validate()`**: No-op (default). Override NOT needed.
```dart
// [P3-1 fix] Do NOT reject null project_id — built-in todo items may have null project_id.
// project_id is nullable for built-in forms/items that are not tied to a specific project.
// The base class validate() is sufficient.
```

**`extractRecordName()`**: Override to return `record['title']`.

---

### 2.16 CalculationHistoryAdapter

**File**: `lib/features/sync/adapters/calculation_history_adapter.dart`
**Class**: `CalculationHistoryAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'calculation_history'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects']` |
| `converters` | See below |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**Converters map:**
```dart
{
  'input_data': JsonMapConverter(),
  'result_data': JsonMapConverter(),
}
```

**SQLite columns** (from `toolbox_tables.dart`):
`id, project_id, entry_id, calc_type, input_data, result_data, notes, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. `input_data`: SQLite `TEXT (JSON)` -> Supabase `JSONB` -- **GAP-16 fix**
2. `result_data`: SQLite `TEXT (JSON)` -> Supabase `JSONB` -- **GAP-16 fix**

**`convertForLocal()`**: Reverse of above.

**`validate()`**: No-op (default). Override NOT needed.
```dart
// [P3-1 fix] Do NOT reject null project_id — built-in calculation items may have null project_id.
// project_id is nullable for built-in forms/items that are not tied to a specific project.
// The base class validate() is sufficient.
```

**`extractRecordName()`**: Override to return `record['calc_type']`.

---

### 2.17 entry_contractors Refactor (Diff-Based Approach)

**File**: `lib/features/contractors/data/datasources/local/entry_contractors_local_datasource.dart`
**Action**: Modify
**Depends on**: EntryContractorsAdapter (2.11), Phase 1 triggers on entry_contractors

The current `setForEntry()` method uses a destructive pattern: DELETE ALL existing rows for an entry, then INSERT all new rows. With the trigger-based engine, this produces N DELETE + M INSERT change_log entries for a single logical "replace" operation, creating excessive sync traffic and risk of data loss on network failure mid-push.

#### 2.17.1 Current implementation (to be replaced)

```dart
Future<void> setForEntry(String entryId, List<String> contractorIds) async {
  final database = await db.database;
  await database.transaction((txn) async {
    // Delete existing
    await txn.delete(_tableName, where: 'entry_id = ?', whereArgs: [entryId]);
    // Insert new
    final now = DateTime.now().toIso8601String();
    for (final contractorId in contractorIds) {
      await txn.insert(_tableName, {
        'id': 'ec-$entryId-$contractorId',
        'entry_id': entryId,
        'contractor_id': contractorId,
        'created_at': now,
      });
    }
  });
}
```

#### 2.17.2 Diff-based replacement

```dart
Future<void> setForEntry(String entryId, List<String> contractorIds) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();

  await database.transaction((txn) async {
    // 1. Get existing contractor IDs for this entry
    final existing = await txn.query(
      _tableName,
      columns: ['id', 'contractor_id'],
      where: 'entry_id = ? AND deleted_at IS NULL',
      whereArgs: [entryId],
    );
    final existingIds = existing.map((r) => r['contractor_id'] as String).toSet();
    final desiredIds = contractorIds.toSet();

    // 2. Compute diff
    final toAdd = desiredIds.difference(existingIds);
    final toRemove = existingIds.difference(desiredIds);
    // Items in both sets: leave unchanged (no change_log entries generated)

    // 3. Soft-delete removed contractors (triggers 'update' in change_log)
    for (final contractorId in toRemove) {
      await txn.update(
        _tableName,
        {
          'deleted_at': now,
          'deleted_by': null, // Could stamp userId if available
          'updated_at': now,
        },
        where: 'entry_id = ? AND contractor_id = ? AND deleted_at IS NULL',
        whereArgs: [entryId, contractorId],
      );
    }

    // 4. Insert new contractors (triggers 'insert' in change_log)
    // [P3-2 fix] Before INSERT, check if a soft-deleted row exists with the same
    // (entry_id, contractor_id). If so, UPDATE it (clear deleted_at, refresh updated_at)
    // instead of INSERT. This prevents duplicate rows and preserves the record's history.
    // Apply the same pattern for other junction tables (entry_equipment, entry_quantities,
    // entry_personnel_counts).
    for (final contractorId in toAdd) {
      final softDeleted = await txn.query(
        _tableName,
        where: 'entry_id = ? AND contractor_id = ? AND deleted_at IS NOT NULL',
        whereArgs: [entryId, contractorId],
      );
      if (softDeleted.isNotEmpty) {
        // Resurrect the soft-deleted row
        await txn.update(
          _tableName,
          {'deleted_at': null, 'deleted_by': null, 'updated_at': now},
          where: 'entry_id = ? AND contractor_id = ? AND deleted_at IS NOT NULL',
          whereArgs: [entryId, contractorId],
        );
      } else {
        // [P3-3 fix] Include project_id in INSERT, looked up from parent daily_entries
        final entryRows = await txn.query(
          'daily_entries', columns: ['project_id'],
          where: 'id = ?', whereArgs: [entryId],
        );
        final projectId = entryRows.isNotEmpty ? entryRows.first['project_id'] as String? : null;

        // Insert new row
        await txn.insert(_tableName, {
          'id': 'ec-$entryId-$contractorId',
          'entry_id': entryId,
          'contractor_id': contractorId,
          'project_id': projectId,
          'created_at': now,
          'updated_at': now,
        });
      }
    }
  });
}
```

Key improvements:
- **Unchanged rows are left alone**: No change_log entries generated for contractors that remain
- **Removed contractors are soft-deleted**: Fires AFTER UPDATE trigger with `operation='update'` (the engine pushes the soft-delete timestamp to Supabase)
- **New contractors are inserted**: Fires AFTER INSERT trigger with `operation='insert'`
- **Prevents data loss**: If network fails mid-push, only the individual add/remove operations need to retry, not the entire set replacement

#### 2.17.3 Also update `removeAllForEntry()`

The current `removeAllForEntry()` does a hard DELETE. Change to soft-delete:

```dart
Future<void> removeAllForEntry(String entryId) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();
  await database.update(
    _tableName,
    {'deleted_at': now, 'updated_at': now},
    where: 'entry_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId],
  );
}
```

#### 2.17.4 Update `remove()` method

Change from hard DELETE to soft-delete:

```dart
Future<void> remove(String entryId, String contractorId) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();
  await database.update(
    _tableName,
    {'deleted_at': now, 'updated_at': now},
    where: 'entry_id = ? AND contractor_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId, contractorId],
  );
}
```

#### 2.17.5 Update `getByEntryId()` to exclude soft-deleted

```dart
Future<List<EntryContractor>> getByEntryId(String entryId) async {
  final database = await db.database;
  final maps = await database.query(
    _tableName,
    where: 'entry_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId],
  );
  return maps.map((m) => EntryContractor.fromMap(m)).toList();
}
```

---

### 2.18 Pull Query Scoping to synced_projects

All adapters with `ScopeType.viaProject`, `ScopeType.viaEntry`, or `ScopeType.viaContractor` have their pull queries filtered through `synced_projects`. This is implemented in `SyncEngine._applyScopeFilter()` (Step 1.4.14), not in the adapters themselves.

**Scope filter rules by ScopeType:**

| ScopeType | Supabase filter | Tables |
|-----------|----------------|--------|
| `direct` | `.eq('company_id', companyId)` | projects |
| `viaProject` | `.inFilter('project_id', syncedProjectIds)` | locations, contractors, bid_items, personnel_types, daily_entries, inspector_forms, form_responses, todo_items, calculation_history |
| `viaEntry` | `.inFilter('project_id', syncedProjectIds)` | photos, entry_equipment, entry_quantities, entry_contractors, entry_personnel_counts |
| `viaContractor` | `.inFilter('contractor_id', syncedContractorIds)` | equipment |

**Note on viaEntry**: After the junction table denormalization (Supabase migration PART 15 + SQLite v30 migration), all 4 entry-scoped junction tables (`entry_equipment`, `entry_quantities`, `entry_contractors`, `entry_personnel_counts`) now have a `project_id` column. This means `viaEntry` generates the same `WHERE project_id IN (...)` filter as `viaProject`. The `viaEntry` enum variant is retained for semantic documentation of the table hierarchy -- it makes it clear these tables are children of `daily_entries`, not direct children of `projects`.

No fallback to `entry_id` filtering is needed after denormalization.

---

### 2.19 Phase 3 Tests

All test files go in `test/features/sync/adapters/`.

#### 2.19.1 Per-adapter round-trip tests (one file per adapter)

For EACH of the 16 adapters, create a test file at:
`test/features/sync/adapters/{table}_adapter_test.dart`

Each file must include these test cases:

**Convert tests:**
- `convertForRemote() produces valid Supabase payload`
  - All localOnlyColumns are stripped
  - Type converters applied correctly (BoolInt, JsonMap, Bytea)
  - All remaining columns present
- `convertForLocal() produces valid SQLite map`
  - All remoteOnlyColumns are stripped
  - Type converters applied in reverse
- `round-trip: local -> remote -> local preserves all data`
  - Start with a valid local record, convertForRemote, convertForLocal, assert equality
- `null/empty handling for every nullable column`
  - Test null values pass through converters without error
  - Test empty strings where applicable

**Type converter round-trip tests** (for adapters with converters):
- `BoolIntConverter: 0 -> false -> 0, 1 -> true -> 1, null -> null`
- `JsonMapConverter: '{"a":1}' -> {"a":1} -> '{"a":1}'`
- `ByteaConverter: Uint8List -> base64 string -> Uint8List` (inspector_forms only)

**Validation tests:**
- `validate() accepts valid records` (all adapters)
- **[FIX: H9]** These 3 adapters explicitly ACCEPT null project_id (per [P3-1 fix] annotations
  at InspectorFormAdapter, TodoItemAdapter, CalculationHistoryAdapter). Test expectations must match:
  - `inspector_forms`: `validate() accepts null project_id for built-in forms`
  - `todo_items`: `validate() accepts null project_id for non-project todos`
  - `calculation_history`: `validate() accepts null project_id`
  - Do NOT write tests asserting rejection of null project_id for these 3 adapters.
- `validate() accepts null form_id on form_responses` (not rejected)
- `validate() rejects duplicate project_number` (projects -- if cross-record validation is implemented)
- `validate() rejects photos with null file_path` (photos)

**Scope and dependency tests:**
- `scopeType is correct`
- `fkDependencies lists correct parent tables`
- `localOnlyColumns are correct`
- `extractRecordName() returns meaningful value`

#### 2.19.2 Adapter test file list

| # | File | Table |
|---|------|-------|
| 1 | `test/features/sync/adapters/project_adapter_test.dart` | projects |
| 2 | `test/features/sync/adapters/location_adapter_test.dart` | locations |
| 3 | `test/features/sync/adapters/contractor_adapter_test.dart` | contractors |
| 4 | `test/features/sync/adapters/equipment_adapter_test.dart` | equipment |
| 5 | `test/features/sync/adapters/bid_item_adapter_test.dart` | bid_items |
| 6 | `test/features/sync/adapters/personnel_type_adapter_test.dart` | personnel_types |
| 7 | `test/features/sync/adapters/daily_entry_adapter_test.dart` | daily_entries |
| 8 | `test/features/sync/adapters/photo_adapter_test.dart` | photos |
| 9 | `test/features/sync/adapters/entry_equipment_adapter_test.dart` | entry_equipment |
| 10 | `test/features/sync/adapters/entry_quantities_adapter_test.dart` | entry_quantities |
| 11 | `test/features/sync/adapters/entry_contractors_adapter_test.dart` | entry_contractors |
| 12 | `test/features/sync/adapters/entry_personnel_counts_adapter_test.dart` | entry_personnel_counts |
| 13 | `test/features/sync/adapters/inspector_form_adapter_test.dart` | inspector_forms |
| 14 | `test/features/sync/adapters/form_response_adapter_test.dart` | form_responses |
| 15 | `test/features/sync/adapters/todo_item_adapter_test.dart` | todo_items |
| 16 | `test/features/sync/adapters/calculation_history_adapter_test.dart` | calculation_history |

#### 2.19.3 entry_contractors refactor tests
**File**: `test/features/contractors/data/datasources/local/entry_contractors_local_datasource_test.dart`

Tests:
- `setForEntry() with new contractors inserts only new rows (change_log: N inserts)`
- `setForEntry() with removed contractors soft-deletes them (change_log: N updates, not deletes)`
- `setForEntry() with unchanged contractors generates NO change_log entries`
- `setForEntry() with mixed add/remove only affects changed rows`
- `remove() soft-deletes instead of hard-deleting`
- `removeAllForEntry() soft-deletes all rows for an entry`
- `getByEntryId() excludes soft-deleted rows`

#### 2.19.4 Pull scope integration tests
**File**: `test/features/sync/engine/pull_scope_test.dart`

Tests:
- `pull applies company_id filter for projects (ScopeType.direct)`
- `pull applies project_id IN synced_projects for viaProject tables`
- `pull applies entry_id filter for viaEntry tables without project_id`
- `pull applies contractor_id filter for equipment (ScopeType.viaContractor)`
- `pull respects synced_projects -- unselected projects are NOT pulled`
- `pull handles empty synced_projects gracefully (no crash, no data pulled)`

#### 2.19.5 Integration round-trip tests
**File**: `test/features/sync/engine/adapter_integration_test.dart`

Tests (per table, against mock Supabase):
- `full push round-trip: local insert -> change_log -> push -> Supabase has record`
- `full pull round-trip: Supabase has record -> pull -> local has record`
- `push/pull round-trip preserves all data for each table`

---

## Summary: Implementation Dependencies

```
Phase 1 (Section A) MUST be complete
    |
    v
Phase 2 Step 1.1 (SyncMutex)          -- depends on sync_lock table
Phase 2 Step 1.2 (ChangeTracker)       -- depends on change_log table
Phase 2 Step 1.3 (ConflictResolver)    -- depends on conflict_log table
    |
    v
Phase 2 Step 1.4 (SyncEngine)         -- depends on 1.1, 1.2, 1.3, IntegrityChecker, all adapters
Phase 2 Step 1.5 (SoftDeleteService)   -- depends on sync_control, change_log tables
Phase 2 Step 1.6 (Tests)              -- depends on all Phase 2 code
    |
    v
Phase 3 Steps 2.1-2.16 (Adapters)     -- already created in Section A, this section documents specs
Phase 3 Step 2.17 (entry_contractors)  -- can be done in parallel with adapter testing
Phase 3 Step 2.18 (Pull scoping)       -- implemented in SyncEngine, documented here
Phase 3 Step 2.19 (Tests)             -- depends on all Phase 3 code
```

**Recommended batch order:**
1. Batch 1 (parallel): SyncMutex, ChangeTracker, ConflictResolver
2. Batch 2: SyncEngine (depends on Batch 1)
3. Batch 3 (parallel): SoftDeleteService redesign, entry_contractors refactor
4. Batch 4: Phase 2 tests
5. Batch 5: Phase 3 adapter tests (all 16 adapters)
6. Batch 6: Pull scope integration tests + adapter round-trip integration tests

### Phase 3 Completion Gate

- [ ] `pwsh -Command "flutter analyze"` -- 0 issues
- [ ] `pwsh -Command "flutter test"` -- all pass
- [ ] All 16 adapter tests pass (column mapping, converters, validation, scope type)
- [ ] entry_contractors diff-based refactor tests pass (soft-delete resurrect, project_id inclusion)
- [ ] Pull scope tests pass (viaProject, viaEntry, viaContractor filtering)
- [ ] Adapter round-trip tests pass (convertForRemote -> convertForLocal identity)
- [ ] Results recorded to `.claude/test-results/phase3-verification.md`

---

## Corrections and Clarifications

| ID | Source | Issue | Resolution |
|----|--------|-------|------------|
| C1 | Analysis | `ScopeType` had 3 variants (direct/oneHop/twoHop) | Replaced with 4 semantically clear variants: direct, viaProject, viaEntry, viaContractor |
| C2 | Analysis | `entry_contractors` and `entry_personnel_counts` never synced | Noted as GAP-6 net-new sync. Adapters enable this. |
| C3 | Plan | `projects` listed `sync_status` in localOnlyColumns | Projects table does NOT have sync_status column. Stripping is a no-op safety measure. |
| C4 | Plan | viaEntry tables pull filter assumed project_id on Supabase | Photos have project_id, but entry_equipment/entry_quantities/entry_contractors/entry_personnel_counts may not. Fallback to entry_id filter documented. |
| C5 | Plan | `hardDeleteWithSync` had `queueSync` callback | Redesigned to use direct sync_control/change_log manipulation. Breaking change for callers. |
| C6 | Analysis | `setForEntry()` destructive DELETE-ALL pattern | Refactored to diff-based approach: soft-delete removed, insert new, leave unchanged. |
| C7 | Plan | `calculation_history` had no JSONB converters | Added JsonMapConverter for input_data and result_data (GAP-16). |
| C8 | Plan | Decision 9 mislabeled | Correctly referenced as Decision 14 for pruning. |

---

# Part 5: Phases 4-7 & Cutover


## Pre-requisites

Before starting any Phase 4 work, the following must be complete and verified:

1. **Phase 0 (Schema + Security)**: All Supabase migrations deployed and passing.
2. **Phase 1 (Change Tracking Foundation)**: SQLite v30 migration installed; change_log, conflict_log, sync_control, sync_lock, synced_projects, sync_metadata, user_certifications tables created; triggers installed on all 16 synced tables; schema verifier updated with new tables.
3. **Phase 2 (Sync Engine Core)**: SyncEngine, SyncMutex, ChangeTracker, ConflictResolver, TableAdapter base class, SyncRegistry, SyncConfig, IntegrityChecker — all implemented and unit-tested with mock adapters.
4. **Phase 3 (Table Adapters)**: All 16 table adapters implemented and tested (projects, locations, contractors, bid_items, personnel_types, equipment, daily_entries, inspector_forms, form_responses, todo_items, calculation_history, entry_equipment, entry_quantities, entry_contractors, entry_personnel_counts, photos — except Photo has only the basic adapter without three-phase logic).

**Key infrastructure available from Phases 1-3:**
- `lib/features/sync/engine/sync_engine.dart` — Push/pull orchestrator
- `lib/features/sync/engine/change_tracker.dart` — Reads change_log
- `lib/features/sync/engine/conflict_resolver.dart` — LWW + conflict_log
- `lib/features/sync/engine/sync_mutex.dart` — Advisory lock
- `lib/features/sync/engine/integrity_checker.dart` — Drift detection
- `lib/features/sync/engine/sync_registry.dart` — Adapter registration
- `lib/features/sync/engine/adapters/` — All table adapters
- `lib/features/sync/engine/converters/` — Type converters
- `lib/core/database/schema/sync_engine_tables.dart` — New engine table DDL

---

## Step 1: Phase 4 — Photo Adapter (Three-Phase Push)

**PREREQUISITE: Phase 3 completion gate must pass before starting Phase 4.**

**Agent**: `backend-data-layer-agent`
**Goal**: Replace the basic PhotoAdapter (from Phase 3) with three-phase photo push logic, implement storage cleanup, orphan detection, EXIF GPS stripping (ADV-56), and refactor all hard-delete `deleteByEntryId()` methods to soft-delete.

### 1.1 PhotoAdapter Configuration (Three-Phase Push is Engine-Owned)

> **SUPERSEDED**: The adapter-owned three-phase push code originally planned here has been replaced.
> Three-phase push is engine-owned via `SyncEngine._pushPhotoThreePhase()` (Part 1, Step 13).
> The PhotoAdapter provides **configuration only** (column mapping, converters, validation, scope).
> It does NOT override `push()`. The SyncEngine detects `adapter is PhotoAdapter` and routes
> to `_pushPhotoThreePhase()` automatically.

**File to modify**: `lib/features/sync/engine/adapters/photo_adapter.dart`

The PhotoAdapter remains a pure configuration object from Phase 3. No `push()` override needed.

**Helper methods to add to SyncEngine (not PhotoAdapter):**

The `_validateStoragePath()` method belongs on SyncEngine for defense-in-depth path validation:

```dart
void _validateStoragePath(String path) {
  final pattern = RegExp(
    r'^entries/[a-f0-9-]+/[a-f0-9-]+/[a-zA-Z0-9_.-]+\.(jpg|jpeg|png|heic)$',
  );
  if (!pattern.hasMatch(path)) {
    throw ArgumentError('Invalid storage path: $path');
  }
}
```

### 1.1.1 EXIF GPS Stripping Before Upload (ADV-56)

Before uploading photo bytes in Phase 1, strip EXIF GPS metadata to prevent location data leakage. Add a pre-upload step:

```dart
// In _uploadFile(), before uploadBinary():
// Strip EXIF GPS data from image bytes for privacy
final strippedBytes = _stripExifGps(bytes);
await client.storage.from('entry-photos').uploadBinary(path, strippedBytes);
```

Implementation options:
1. Use the `image` package to read/write EXIF, removing GPS-related tags
2. Use a lightweight EXIF stripper that preserves orientation but removes GPS coordinates
3. If no pure-Dart EXIF stripping library is suitable, document as a follow-up task with a `// TODO(ADV-56): Strip EXIF GPS before upload` comment

> **Note (ADV-58)**: Photo upload idempotency race (two devices uploading the same path simultaneously) is low priority. UUIDs in the filename mitigate this. Document as a known edge case in the PhotoAdapter class docstring.

### 1.2 Photo Soft-Delete Push

In the same `push()` method, ensure that when a photo has `deleted_at` set (soft-delete), the metadata upsert sends the `deleted_at` timestamp to Supabase. The `convertForRemote()` method from Phase 3 should already include `deleted_at` in the payload. Verify this is the case.

**File**: `lib/features/sync/engine/adapters/photo_adapter.dart`

Verify that `convertForRemote()` includes:
```dart
if (localRecord['deleted_at'] != null) {
  remotePayload['deleted_at'] = localRecord['deleted_at'];
  remotePayload['deleted_by'] = localRecord['deleted_by'];
}
```

### 1.3 Storage Cleanup Phase

**File to create**: `lib/features/sync/engine/storage_cleanup.dart`

This runs after the push phase and deletes storage files for photos that have been soft-deleted for 30+ days and then purged.

```dart
class StorageCleanup {
  final SupabaseClient _client;
  final DatabaseService _dbService;

  StorageCleanup(this._client, this._dbService);

  /// Delete storage files for photos that have been hard-deleted (purged from SQLite)
  /// but whose storage files may still exist.
  ///
  /// Called after each push cycle. Reads from a `storage_cleanup_queue` that gets
  /// populated when SoftDeleteService.hardDeleteWithSync() processes photo purges.
  Future<int> cleanupExpiredPhotos() async {
    final database = await _dbService.database;

    // Read pending cleanup entries
    final pending = await database.query(
      'storage_cleanup_queue',
      where: 'status = ?',
      whereArgs: ['pending'],
      orderBy: 'created_at ASC',
      limit: 50,
    );

    int cleaned = 0;
    for (final entry in pending) {
      final remotePath = entry['remote_path'] as String?;
      if (remotePath != null && remotePath.isNotEmpty) {
        try {
          await _client.storage.from('entry-photos').remove([remotePath]);
          cleaned++;
        } catch (e) {
          // Log but continue — orphan scanner will catch stragglers
        }
      }

      // Mark as processed regardless of success (orphan scanner is fallback)
      await database.update(
        'storage_cleanup_queue',
        {'status': 'processed', 'processed_at': DateTime.now().toUtc().toIso8601String()},
        where: 'id = ?',
        whereArgs: [entry['id']],
      );
    }

    return cleaned;
  }
}
```

**[P4-4]** The `storage_cleanup_queue` table is included in the Phase 1 v30 migration and in `SyncEngineTables` schema constants (7 tables total: sync_control, change_log, conflict_log, sync_lock, synced_projects, sync_metadata, storage_cleanup_queue). Schema:

```sql
CREATE TABLE IF NOT EXISTS storage_cleanup_queue (
  id TEXT PRIMARY KEY,
  remote_path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
  processed_at TEXT
)
```

**Photo-specific purge method**: When `SoftDeleteService` hard-deletes a photo record during purge, it must first read the photo's `remote_path` and insert a row into `storage_cleanup_queue` before the hard DELETE:

```dart
// In SoftDeleteService, before hard-deleting a photo:
if (tableName == 'photos') {
  final photo = await database.query('photos', columns: ['remote_path'], where: 'id = ?', whereArgs: [id]);
  final remotePath = photo.isNotEmpty ? photo.first['remote_path'] as String? : null;
  if (remotePath != null && remotePath.isNotEmpty) {
    await database.insert('storage_cleanup_queue', {
      'id': const Uuid().v4(),
      'remote_path': remotePath,
      'status': 'pending',
    });
  }
}
```

### 1.4 Orphan Scanner

**File to create**: `lib/features/sync/engine/orphan_scanner.dart`

**[FIX: C13]** Orphan scanner MUST query the Supabase `photos` table (not local SQLite)
to get known remote_paths. In multi-device companies, local SQLite only has THIS device's
photos. Querying Supabase sees all devices' photos, preventing false orphan detection.

Queries the **remote** `photos` table for all known remote_paths, then lists all files in Supabase Storage under the company prefix, and flags any storage files that have no corresponding DB row and are older than 24 hours.

```dart
class OrphanScanner {
  final SupabaseClient _client;
  final DatabaseService _dbService;
  static const String _bucket = 'entry-photos';

  OrphanScanner(this._client, this._dbService);

  /// Scan for orphaned storage files.
  /// Returns a list of orphaned paths for logging/alerting.
  Future<List<String>> scan(String companyId) async {
    // 1. Query REMOTE photos table (sees all devices' uploads)
    final remotePhotos = await _client
        .from('photos')
        .select('remote_path')
        .not('remote_path', 'is', null)
        .not('remote_path', 'eq', '');

    final knownPaths = (remotePhotos as List)
        .map((r) => r['remote_path'] as String)
        .toSet();

    // 2. List storage files under company prefix
    final prefix = 'entries/$companyId/';
    final storageFiles = await _client.storage
        .from(_bucket)
        .list(path: prefix);

    // 3. Recursively list entry subdirectories
    final allStoragePaths = <String>[];
    for (final dir in storageFiles) {
      if (dir.name.isEmpty) continue;
      final entryPrefix = '$prefix${dir.name}/';
      final files = await _client.storage
          .from(_bucket)
          .list(path: entryPrefix);
      for (final file in files) {
        if (file.name.isNotEmpty) {
          allStoragePaths.add('$entryPrefix${file.name}');
        }
      }
    }

    // 4. Diff: storage paths not in known local paths
    final orphans = allStoragePaths
        .where((path) => !knownPaths.contains(path))
        .toList();

    // 5. Filter by age > 24h (using file metadata if available)
    // Note: Supabase storage list returns metadata with created_at;
    // for simplicity, flag all orphans and let cleanup handle age check

    return orphans;
  }
}
```

### 1.5 Refactor `deleteByEntryId()` to Soft-Delete

The plan requires converting hard-delete `deleteByEntryId()` methods to soft-delete for four datasources. This ensures that when an entry is deleted, its children are soft-deleted (generating `operation='update'` change_log entries that push `deleted_at` to Supabase) instead of hard-deleted (which generates `operation='delete'` entries that bypass 30-day trash retention).

#### 1.5.1 PhotoLocalDatasource.deleteByEntryId()

**File**: `lib/features/photos/data/datasources/local/photo_local_datasource.dart`
**Line**: 42-49

**Before:**
```dart
Future<int> deleteByEntryId(String entryId) async {
  final database = await db.database;
  return database.delete(
    tableName,
    where: 'entry_id = ?',
    whereArgs: [entryId],
  );
}
```

**After:**
```dart
/// Soft-delete all photos for an entry.
///
/// Sets deleted_at/deleted_by instead of hard-deleting, so change_log
/// triggers generate 'update' operations that push deleted_at to Supabase
/// and honor 30-day trash retention.
Future<int> softDeleteByEntryId(String entryId, {String? userId}) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();
  return database.update(
    tableName,
    {
      'deleted_at': now,
      'deleted_by': userId,
      'updated_at': now,
    },
    where: 'entry_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId],
  );
}
```

**Also update all callers** — search for `deleteByEntryId` calls on photo datasource:
- `lib/features/photos/data/repositories/photo_repository.dart:125` — update call to `softDeleteByEntryId(entryId, userId: userId)`

#### 1.5.2 EntryEquipmentLocalDatasource.deleteByEntryId()

**File**: `lib/features/contractors/data/datasources/local/entry_equipment_local_datasource.dart`
**Line**: 70-77

**Before:**
```dart
Future<void> deleteByEntryId(String entryId) async {
  final database = await db.database;
  await database.delete(
    tableName,
    where: 'entry_id = ?',
    whereArgs: [entryId],
  );
}
```

**After:**
```dart
Future<void> softDeleteByEntryId(String entryId, {String? userId}) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();
  await database.update(
    tableName,
    {
      'deleted_at': now,
      'deleted_by': userId,
      'updated_at': now,
    },
    where: 'entry_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId],
  );
}
```

#### 1.5.3 EntryQuantityLocalDatasource.deleteByEntryId()

**File**: `lib/features/quantities/data/datasources/local/entry_quantity_local_datasource.dart`
**Line**: 81-87

**Before:**
```dart
Future<void> deleteByEntryId(String entryId) async {
  final database = await db.database;
  await database.delete(
    tableName,
    where: 'entry_id = ?',
    whereArgs: [entryId],
  );
}
```

**After:**
```dart
Future<void> softDeleteByEntryId(String entryId, {String? userId}) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();
  await database.update(
    tableName,
    {
      'deleted_at': now,
      'deleted_by': userId,
      'updated_at': now,
    },
    where: 'entry_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId],
  );
}
```

**Update callers:**
- `lib/features/quantities/data/repositories/entry_quantity_repository.dart:97` and `:141` — update to `softDeleteByEntryId`

#### 1.5.4 FormResponseLocalDatasource.deleteByEntryId()

**File**: `lib/features/forms/data/datasources/local/form_response_local_datasource.dart`
**Line**: 85-91

**Before:**
```dart
Future<void> deleteByEntryId(String entryId) async {
  final database = await db.database;
  await database.delete(
    tableName,
    where: 'entry_id = ?',
    whereArgs: [entryId],
  );
}
```

**After:**
```dart
Future<void> softDeleteByEntryId(String entryId, {String? userId}) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();
  await database.update(
    tableName,
    {
      'deleted_at': now,
      'deleted_by': userId,
      'updated_at': now,
    },
    where: 'entry_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId],
  );
}
```

**Update callers:**
- `lib/features/forms/data/repositories/form_response_repository.dart:225` — update to `softDeleteByEntryId`

#### 1.5.5 saveForEntry() DELETE+re-INSERT Pattern

[CORRECTION] The plan mentions `deleteByEntryId()` refactoring but does not explicitly address the `saveForEntry()` DELETE+re-INSERT pattern that exists in:

- `lib/features/contractors/data/datasources/local/entry_personnel_local_datasource.dart:74-90` (entry_personnel table)
- `lib/features/contractors/data/datasources/local/entry_equipment_local_datasource.dart:80-96` (entry_equipment table)

These methods delete all records for an entry and re-insert, which with change_log triggers will generate N DELETE + M INSERT entries for what is logically a single "replace" operation. Phase 3 already addresses `entry_contractors_local_datasource.setForEntry()` with a diff-based approach. The same pattern should be applied here:

**For `entry_equipment_local_datasource.saveForEntry()`:**
1. Read existing records for the entry: `SELECT * FROM entry_equipment WHERE entry_id = ?`
2. Compute diff: which IDs are new (insert), which are removed (soft-delete), which are unchanged (skip)
3. Soft-delete removed records, insert new records, leave unchanged alone
4. This minimizes change_log entries and prevents data loss on network failure

**For `entry_personnel_local_datasource.saveForEntry()`:**
The `entry_personnel` table is a LEGACY table that is NOT synced (confirmed: no adapter, no triggers). The `saveForEntry()` method for this table can remain as-is since it only affects local data. However, the `saveCountsForEntryContractor()` and `saveAllCountsForEntry()` methods on the SAME datasource affect the `entry_personnel_counts` table, which IS synced. These methods also use DELETE+re-INSERT.

[CORRECTION] The plan says to delete `entry_personnel_local_datasource.dart` entirely in Phase 7c, but this file manages BOTH the legacy `entry_personnel` table AND the active `entry_personnel_counts` table. The file CANNOT be deleted. Instead:
- **Rename** the file to `entry_personnel_counts_local_datasource.dart`
- **Remove** only the `entry_personnel`-specific methods (getByEntryId, getByEntryAndContractor, upsert, deleteByEntryId, saveForEntry) — lines 28-90
- **Keep** all `entry_personnel_counts` methods (lines 92-213)
- **Refactor** `saveCountsForEntryContractor()` and `saveAllCountsForEntry()` to use diff-based approach instead of DELETE+re-INSERT

### 1.6 Wire Storage Cleanup and Orphan Scanner into SyncEngine

**File to modify**: `lib/features/sync/engine/sync_engine.dart`

After the push phase completes:
1. Run `StorageCleanup.cleanupExpiredPhotos()`
2. Orphan scanner is wired into the integrity check cycle (see Phase 5, Step 2.4)

### 1.7 Phase 4 Tests

All tests listed in the original plan:

| Test | Description |
|------|-------------|
| Three-phase success | upload -> metadata -> mark synced |
| Phase 1 failure -> retry re-uploads | File upload fails, next cycle re-uploads |
| Phase 2 failure -> file exists in storage -> retry metadata only | Metadata upsert fails, file already in storage |
| Phase 1+2 succeed, Phase 3 fails -> next cycle skips upload, upserts, marks | Local update fails, next cycle recovers |
| Soft-delete photo -> push -> remote has deleted_at | Soft-deleted photo pushed with deleted_at |
| Storage cleanup: 30-day-expired photos cleaned from bucket | Purged photo files cleaned from storage |
| Orphan detection: storage file with no DB row -> flagged | Orphaned file detected |
| deleteByEntryId() sets deleted_at instead of hard-deleting | Verify soft-delete behavior |
| deleteByEntryId() generates change_log UPDATE entries (not DELETE) | Verify trigger generates update operation |
| Soft-deleted photos pushed with deleted_at to Supabase | 30-day trash honored |

### Phase 4 Completion Gate

- [ ] `pwsh -Command "flutter analyze"` -- 0 issues
- [ ] `pwsh -Command "flutter test"` -- all pass
- [ ] Three-phase push test passes (upload -> metadata -> mark synced, with idempotent re-upload)
- [ ] Soft-delete photo push test passes (deleted_at sent to Supabase)
- [ ] `storage_cleanup_queue` table exists in v30 migration and SyncEngineTables schema
- [ ] StorageException handling test passes (409=skip, 403=permanent, 413=permanent, 5xx=retry)
- [ ] deleteByEntryId() soft-delete test passes (generates UPDATE change_log, not DELETE)
- [ ] Photo purge inserts into storage_cleanup_queue before hard delete
- [ ] Results recorded to `.claude/test-results/phase4-verification.md`

---

## Step 2: Phase 5 — Integrity Wiring + Verification

**PREREQUISITE: Phase 4 completion gate must pass before starting Phase 5.**

**Agent**: `backend-data-layer-agent`
**Goal**: Wire already-built components (IntegrityChecker, OrphanScanner) into SyncEngine, store results for UI, and write verification tests. Phase 5 is **wiring-only** -- no new pull/push logic is added here (that lives in Part 1 Step 13).

> **REMOVED**: Duplicate `pullTable()` logic, `pullFull()`/`pullIncremental()` adapter methods,
> non-existent `check()` call, `hasDrift`/`driftType` references. The pull flow is already
> fully defined in Part 1 Step 13 (`_pull()` and `_pullTable()`). Phase 5 does not
> redefine it. IntegrityChecker and OrphanScanner were already created in Phase 2.

### 2.1 Wire IntegrityChecker.shouldRun()/run() into SyncEngine

**File to modify**: `lib/features/sync/engine/sync_engine.dart`

The `pushAndPull()` method (Part 1 Step 13) already calls `_integrityChecker.shouldRun()` and `_integrityChecker.run()`. Phase 5 ensures this wiring is correct and the IntegrityChecker:

1. Uses `shouldRun()` to check if 4+ hours have elapsed since last check (reads `sync_metadata.last_integrity_check`)
2. Calls `run()` which invokes the `get_table_integrity()` Supabase RPC for each synced table
3. Compares remote count/max_updated_at/id_checksum against local values
4. On mismatch: resets the per-table cursor in `sync_metadata` (next pull becomes a full pull)

### 2.2 Wire OrphanScanner into Post-Integrity-Check Flow

**File to modify**: `lib/features/sync/engine/sync_engine.dart`

After IntegrityChecker completes, run OrphanScanner:

```dart
// In pushAndPull(), after integrity check:
if (await _integrityChecker.shouldRun()) {
  try {
    final integrityResults = await _integrityChecker.run();
    // Store results for UI (2.3)
    for (final result in integrityResults) {
      await _storeIntegrityResult(result);
      if (result.driftDetected) {
        await _clearCursor(result.tableName);
      }
    }
    // Run orphan scanner as part of integrity cycle
    final orphans = await _orphanScanner.scan(_companyId);
    if (orphans.isNotEmpty) {
      await _storeMetadata('orphan_count', orphans.length.toString());
    }
  } catch (e) {
    DebugLogger.error('Integrity check failed', error: e);
  }
}
```

### 2.3 Store Integrity Results in sync_metadata for Sync Dashboard UI

**File to modify**: `lib/features/sync/engine/sync_engine.dart`

Store per-table integrity results so the Sync Dashboard UI (Phase 6) can display them:

```dart
Future<void> _storeIntegrityResult(IntegrityResult result) async {
  final database = await _dbService.database;
  await database.rawInsert('''
    INSERT OR REPLACE INTO sync_metadata (key, value)
    VALUES (?, ?)
  ''', [
    'integrity_${result.tableName}',
    jsonEncode({
      'checked_at': DateTime.now().toUtc().toIso8601String(),
      'drift_detected': result.driftDetected,
      'local_count': result.localCount,
      'remote_count': result.remoteCount,
    }),
  ]);
}
```

### 2.4 Fix Integrity RPC SQL Syntax Bug

**File**: The `get_table_integrity()` RPC defined in Phase 0 (Section B, PART 10) has a SQL syntax issue: an `AND` clause appears before `ORDER BY` where it should not. Fix:

```sql
-- BEFORE (buggy):
SELECT ... FROM {table} WHERE deleted_at IS NULL AND ORDER BY id
-- AFTER (fixed):
SELECT ... FROM {table} WHERE deleted_at IS NULL ORDER BY id
```

### 2.5 Canonicalize RPC to Use hashtext Algorithm

Ensure the `get_table_integrity()` RPC uses the same `hashtext` algorithm defined in Section B for the id_checksum calculation. The local SQLite IntegrityChecker must compute the same hash. Both sides:
1. Sort IDs alphabetically
2. Concatenate with no separator
3. Apply hash (PostgreSQL: `md5()`, SQLite: custom MD5 or string hash)

### 2.6 Phase 5 Verification Tests

| Test | Description |
|------|-------------|
| IntegrityChecker.shouldRun() returns false when last check < 4 hours ago | Schedule check |
| IntegrityChecker.shouldRun() returns true when no previous check exists | First run |
| IntegrityChecker.run() detects injected count drift -> resets cursor | Count mismatch |
| IntegrityChecker.run() detects injected checksum drift -> resets cursor | ID mismatch |
| IntegrityChecker.run() passes when no drift -> cursor not reset | Clean state |
| Integrity result stored in sync_metadata and retrievable | Storage check |
| OrphanScanner runs after integrity check, results stored | Wiring check |
| Cursor reset triggers full pull on next cycle | Recovery path |
| Integrity check failure does not abort sync cycle | Error isolation |

### 2.7 Phase 5 Completion Gate

- [ ] `flutter analyze` -- 0 issues
- [ ] `flutter test` -- all pass
- [ ] IntegrityChecker wired into pushAndPull() and runs on 4-hour schedule
- [ ] OrphanScanner wired into post-integrity flow
- [ ] Integrity results stored in sync_metadata
- [ ] SQL syntax bug in integrity RPC fixed
- [ ] All 9 Phase 5 verification tests pass
- [ ] Results recorded to `.claude/test-results/phase5-verification.md`

---

## Step 3: Phase 6 — UI + Settings Redesign + Profile Expansion

**PREREQUISITE: Phase 5 completion gate must pass before starting Phase 6.**

**Agent**: `frontend-flutter-specialist-agent`
**Goal**: Replace SyncStatusBanner with SyncStatusIcon, create Sync Dashboard and Conflict Viewer screens, restructure Settings screen, migrate profile reads from PreferencesService to AuthProvider, fix GAP-17 and GAP-18.

### 3.1 SyncStatusIcon Widget

**File to create**: `lib/features/sync/presentation/widgets/sync_status_icon.dart`

Replaces `SyncStatusBanner`. A compact app bar icon with color coding:
- Green: all synced, no pending changes
- Yellow: sync in progress or pending changes
- Red: sync error or offline with pending changes

```dart
class SyncStatusIcon extends StatelessWidget {
  const SyncStatusIcon({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<SyncProvider>(
      builder: (context, syncProvider, _) {
        final color = _getColor(syncProvider);
        final icon = _getIcon(syncProvider);
        return IconButton(
          key: TestingKeys.syncProgressSpinner, // [Decision 12] Renamed from syncStatusIndicator
          icon: Icon(icon, color: color, size: 20),
          onPressed: () => context.push('/sync/dashboard'),
          tooltip: _getTooltip(syncProvider),
        );
      },
    );
  }

  Color _getColor(SyncProvider provider) {
    // [Decision 12] Use hasPersistentSyncFailure instead of hasErrors
    if (provider.hasPersistentSyncFailure) return Colors.red;
    if (provider.isSyncing || provider.hasPendingChanges) return Colors.amber;
    return Colors.green;
  }

  IconData _getIcon(SyncProvider provider) {
    if (provider.hasPersistentSyncFailure) return Icons.sync_problem;
    if (provider.isSyncing) return Icons.sync;
    return Icons.cloud_done;
  }

  String _getTooltip(SyncProvider provider) {
    if (provider.hasPersistentSyncFailure) return 'Sync error';
    if (provider.isSyncing) return 'Syncing...';
    if (provider.hasPendingChanges) return 'Changes pending';
    return 'All synced';
  }
}
```

### 3.2 Toast Notifications on Sync Failure

**File to modify**: `lib/features/sync/presentation/providers/sync_provider.dart`

Add a toast notification when sync fails. Use a `GlobalKey<ScaffoldMessengerState>` or an overlay-based approach:

```dart
// [Decision 12] Use SyncAdapterStatus instead of SyncStatus
void _onSyncStatusChanged(SyncAdapterStatus status) {
  if (status == SyncAdapterStatus.error && _lastError != null) {
    _showSyncErrorToast(_lastError!);
  }
  notifyListeners();
}
```

### 3.3 SyncDashboardScreen

**File to create**: `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`

Route: `/sync/dashboard`

Content:
- Per-table health cards (pending count, last sync time, last integrity check result)
- Recent activity log (last N sync operations from sync_metadata)
- Pending/failed counts summary
- Integrity check results (from sync_metadata `integrity_{table}` entries)
- Manual sync button
- Link to Conflict Viewer

**Register route** in `lib/core/router/app_router.dart`.

### 3.4 ConflictViewerScreen

**File to create**: `lib/features/sync/presentation/screens/conflict_viewer_screen.dart`

Route: `/sync/conflicts`

Content:
- List of conflict_log entries (not yet dismissed)
- Each row shows: table, record name, detected_at, conflict type
- Tap to expand: shows lost_data JSON
- Actions per conflict:
  - **Dismiss**: sets `dismissed_at` on the conflict_log entry
  - **Restore**: reads lost_data, reads current record, merges, validates via `adapter.validate()`, updates SQLite, marks dismissed

**Restore flow implementation:**
```dart
Future<void> restoreConflict(ConflictLogEntry conflict) async {
  final adapter = _syncRegistry.getAdapter(conflict.tableName);
  final lostData = jsonDecode(conflict.lostData) as Map<String, dynamic>;

  // [Decision 12] Use raw DatabaseService queries with adapter's tableName
  // instead of adapter.readLocal()/updateLocal() which don't exist on TableAdapter
  final database = await _dbService.database;
  final tableName = adapter.tableName;

  // Read current record
  final records = await database.query(
    tableName, where: 'id = ?', whereArgs: [conflict.recordId],
  );
  if (records.isEmpty) {
    // Record was purged — cannot restore
    _showError('This record has been permanently deleted and cannot be restored.');
    return;
  }
  final currentRecord = records.first;

  // Merge lost_data into current record
  final merged = {...currentRecord, ...lostData};

  // Validate
  final validationResult = adapter.validate(merged);
  if (!validationResult.isValid) {
    _showError('Cannot restore: ${validationResult.errors.join(", ")}');
    return;
  }

  // Apply
  await database.update(
    tableName, merged,
    where: 'id = ?', whereArgs: [conflict.recordId],
  );

  // Mark dismissed
  await _markDismissed(conflict.id);
}
```

### 3.5 ProjectSelectionScreen

**File to create**: `lib/features/sync/presentation/screens/project_selection_screen.dart`

Route: `/sync/project-selection`

Content:
- Queries Supabase directly for all projects in the user's company
- Search bar to filter projects
- Tap to add/remove from local `synced_projects` table
- Already-synced projects are visually marked (checkmark)

### 3.6 DeletionNotificationBanner

**File to keep**: `lib/features/sync/presentation/widgets/deletion_notification_banner.dart`

Wire to new engine's `deletion_notifications` table. The banner already exists; update its data source to read from the `deletion_notifications` table populated by the new SyncEngine pull flow (instead of whatever legacy mechanism it used).

### 3.7 Fix GAP-17: getDatesWithEntries Missing deleted_at Filter

**File**: `lib/features/entries/data/datasources/local/daily_entry_local_datasource.dart`
**Line**: 80-89

**Before:**
```dart
final maps = await database.rawQuery(
  'SELECT DISTINCT date FROM $tableName WHERE project_id = ? ORDER BY date DESC',
  [projectId],
);
```

**After:**
```dart
final maps = await database.rawQuery(
  'SELECT DISTINCT date FROM $tableName WHERE project_id = ? AND deleted_at IS NULL ORDER BY date DESC',
  [projectId],
);
```

### 3.8 Fix GAP-18: location_local_datasource.search() Missing deleted_at Filter

**File**: `lib/features/locations/data/datasources/local/location_local_datasource.dart`
**Line**: 28-34

**Before:**
```dart
Future<List<Location>> search(String projectId, String query) async {
  final searchPattern = '%$query%';
  return getWhere(
    where: 'project_id = ? AND (name LIKE ? OR station LIKE ?)',
    whereArgs: [projectId, searchPattern, searchPattern],
  );
}
```

**After:**
```dart
Future<List<Location>> search(String projectId, String query) async {
  final searchPattern = '%$query%';
  return getWhere(
    where: 'project_id = ? AND (name LIKE ? OR station LIKE ?) AND deleted_at IS NULL',
    whereArgs: [projectId, searchPattern, searchPattern],
  );
}
```

### 3.9 Settings Redesign

**File to modify**: `lib/features/settings/presentation/screens/settings_screen.dart`

#### 3.9.1 Restructure Sections

New section order:
1. **Account** — Display Name (read-only from AuthProvider), Email (read-only), Edit Profile link, Sign Out
2. **Sync & Data** — Sync Dashboard link, Manage Synced Projects link, Trash link, Clear Cache
3. **Form Settings** — Company Template (read-only), Gauge Number (editable, persists to user_profiles), Initials (editable, auto-derived from displayName, manually overridable)
4. **Appearance** — Theme selector, Auto-Load toggle (from ProjectSettingsProvider)
5. **About** — Version, Licenses

#### 3.9.2 Remove Dead Toggles

Remove from `_SettingsScreenState`:
- `_autoFetchWeather` field and `_toggleAutoFetchWeather()` method
- `_autoSyncWifi` field and `_toggleAutoSyncWifi()` method
- `_autoFillEnabled` field and `_toggleAutoFillEnabled()` method
- `_useLastValues` field and `_toggleUseLastValues()` method

Remove from build():
- Auto-fill enabled toggle widget
- Use last values toggle widget
- Auto-sync on WiFi toggle widget
- Auto-fetch weather toggle widget

#### 3.9.3 Remove Dead Stubs

Remove from build():
- Backup Data tile (with snackbar stub)
- Restore Data tile (with snackbar stub)
- Help & Support tile (with snackbar stub)

#### 3.9.4 Remove Duplicate

Remove "Default Signature Name" tile if it duplicates profile name display.

#### 3.9.5 Remove Unactionable Displays

Remove Weather API tile (display-only, non-configurable).

#### 3.9.6 Move Company Template

Move Company Template read-only info tile from current location to the Form Settings section.

#### 3.9.7 Add Gauge Number Field

In Form Settings section, add an editable ListTile for Gauge Number:
- Reads from `AuthProvider.userProfile.gaugeNumber`
- On edit, updates `user_profiles.gauge_number` in Supabase
- No PreferencesService fallback (Decision 12)

#### 3.9.8 Add Initials Field

In Form Settings section, add an editable ListTile for Initials:
- Auto-derived from displayName (first letter of each word)
- Manually overridable
- Reads from `AuthProvider.userProfile.initials`
- On edit, updates `user_profiles.initials` in Supabase

#### 3.9.9 Keep Auto-Load Toggle

In APPEARANCE section, keep the Auto-Load toggle from ProjectSettingsProvider.

#### 3.9.10 Delete EditInspectorDialog Widget

**File to delete**: `lib/features/settings/presentation/widgets/edit_inspector_dialog.dart`

This widget is orphaned (zero call sites). Delete it.

**Also update barrel export**: `lib/features/settings/presentation/widgets/widgets.dart` — remove the export line for `edit_inspector_dialog.dart`.

#### 3.9.11 Remove Dead Pref Keys

These keys will be cleaned up in Phase 7g (PreferencesService Cleanup). For now, the settings screen simply stops reading them.

### 3.10 Migrate Form Auto-Fill Reads

**Decision 12**: All form auto-fill reads come from `AuthProvider.userProfile`. No fallback to PreferencesService.

#### 3.10.1 Fix entry_photos_section.dart

**File**: `lib/features/entries/presentation/widgets/entry_photos_section.dart`
**Line**: 88

**Before:**
```dart
final initials = prefs.getString('inspector_initials') ?? 'XX';
```

**After:**
```dart
final authProvider = context.read<AuthProvider>();
// [Decision 12] Use effectiveInitials (auto-derives from displayName if initials is null)
final initials = authProvider.userProfile?.effectiveInitials ?? 'XX';
```

Remove the `SharedPreferences` import and `prefs` variable if no longer needed.

#### 3.10.2 Fix pdf_data_builder.dart

**File**: `lib/features/entries/presentation/controllers/pdf_data_builder.dart`
**Lines**: 130, 134

**Before:**
```dart
inspectorName = prefs.getString('inspector_name') ?? 'Inspector';
// ... (line 134 similar)
inspectorName = prefs.getString('inspector_name') ?? 'Inspector';
```

**After:**
```dart
inspectorName = authProvider.userProfile?.displayName ?? 'Inspector';
// ... (line 134 similar)
inspectorName = authProvider.userProfile?.displayName ?? 'Inspector';
```

The pdf_data_builder needs to receive the AuthProvider (or the userProfile directly) as a constructor parameter instead of using SharedPreferences.

#### 3.10.3 Fix form_response_repository.dart

**File**: `lib/features/forms/data/repositories/form_response_repository.dart`
**Line**: 385

**Before:**
```dart
requireHeader('cert_number', 'cert_number');
```

Ensure the auto-fill pipeline resolves `cert_number` from `user_certifications` via AuthProvider, not from PreferencesService. The `requireHeader` call itself may not need to change — the data source it reads from needs to be updated to point to `AuthProvider.userProfile.certifications` or a query to the local `user_certifications` table.

### 3.11 PII Cleanup from SharedPreferences

**File to modify**: `lib/main.dart` (or `lib/features/auth/services/auth_service.dart`)

On first launch after update, delete all legacy PII keys from SharedPreferences:

```dart
Future<void> _cleanupLegacyPiiKeys() async {
  final prefs = await SharedPreferences.getInstance();
  final migrated = prefs.getBool('pii_migrated_to_user_profiles') ?? false;
  if (migrated) return;

  // Delete legacy PII keys
  final keysToDelete = [
    'inspector_name', 'inspector_initials', 'inspector_phone',
    'inspector_cert_number', 'inspector_agency', 'gauge_number',
  ];
  for (final key in keysToDelete) {
    await prefs.remove(key);
  }

  await prefs.setBool('pii_migrated_to_user_profiles', true);
}
```

### 3.12 Edit Profile Screen Updates

**File to modify**: `lib/features/settings/presentation/screens/edit_profile_screen.dart`

Update to show/edit:
- `displayName` (editable)
- `email` (read-only)
- `agency` (editable)
- `initials` (editable, with auto-derive option)
- `phone` (editable)

All reads/writes go through AuthProvider -> user_profiles (Supabase).

### 3.13 Wire UserProfileSyncDatasource for user_certifications

**File to modify**: `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart`

Ensure that when user profiles are synced, the `user_certifications` table is also synced (pull certifications for the current user).

### 3.14 Conflict Log Auto-Cleanup

**File to modify**: `lib/features/sync/engine/sync_engine.dart`

Add cleanup step in sync cycle: auto-dismiss conflicts older than 30 days.

```dart
Future<void> _cleanupExpiredConflicts() async {
  final database = await _dbService.database;
  final thirtyDaysAgo = DateTime.now().subtract(const Duration(days: 30)).toUtc().toIso8601String();
  await database.update(
    'conflict_log',
    {'dismissed_at': DateTime.now().toUtc().toIso8601String()},
    where: 'dismissed_at IS NULL AND detected_at < ?',
    whereArgs: [thirtyDaysAgo],
  );
}
```

### 3.15 Phase 6 Tests

| Test | Description |
|------|-------------|
| Widget: settings sections render in correct order | Account, Sync & Data, Form Settings, Appearance, About |
| Widget: dead items are gone | No auto-fill, use-last-values, auto-sync, auto-weather toggles |
| Widget: gauge number field editable, persists to user_profiles | Not PreferencesService |
| Widget: initials field editable, persists to user_profiles | Auto-derive or manual |
| Widget: Auto-Load toggle present in APPEARANCE | From ProjectSettingsProvider |
| Widget: Manage Synced Projects link present | In Sync & Data section |
| Widget: sync icon colors match state | Green/yellow/red |
| Widget: sync dashboard shows correct per-table data | Health cards |
| Widget: conflict viewer shows lost data | JSON display |
| Widget: conflict viewer restore runs validate() — valid succeeds | Happy path |
| Widget: conflict viewer restore with invalid data shows error | Validation error |
| Widget: conflict viewer restore on purged record shows "permanently deleted" | Record gone |
| Widget: project selection screen lists projects from Supabase | Direct query |
| Widget: project selection search filters results | Search works |
| Integration: form auto-fill reads from userProfile (no prefs fallback) | Decision 12 |

---

## Step 4: Phase 7 — Cutover + Cleanup

**PREREQUISITE: Phase 6 completion gate must pass before starting Phase 7.**

**Cutover strategy (Decision 10)**: Big Bang. The new engine is built entirely on the feature branch. The old SyncService remains functional throughout Phases 0-6. When Phase 7 is complete and all tests pass, the old code is deleted and the branch is merged. No dual-write period. No feature flag. Git history is the rollback mechanism.

### 4.0 Phase 7 Prerequisites

Before starting Phase 7:
- All Phase 6 tests pass
- New SyncEngine is fully functional with all 16 table adapters
- All new UI screens are implemented and tested

### 4.0.1 Wire New SyncEngine into App Lifecycle

**File to modify**: `lib/main.dart`

Replace old SyncService initialization with new SyncEngine:
- Remove `SyncService` creation
- Create `SyncEngine` with `DatabaseService` and `SupabaseClient`
- Register all table adapters via `SyncRegistry`
- Provide `SyncEngine` to the widget tree

**File to modify**: `lib/features/sync/application/sync_orchestrator.dart`

Update `SyncOrchestrator` to delegate to new SyncEngine instead of old SupabaseSyncAdapter/SyncService:
- Replace `_localAgencyAdapter` (which wraps old SyncService) with new SyncEngine
- Update `syncLocalAgencyProjects()` to call `SyncEngine.sync()`
- Remove dependency on `SupabaseSyncAdapter`

**File to modify**: `lib/features/sync/presentation/providers/sync_provider.dart`

Update `SyncProvider` to read state from new SyncEngine:
- Status from SyncEngine (not old adapter status)
- Pending count from change_log (not sync_queue)
- Last sync time from sync_metadata

**File to modify**: `lib/features/sync/application/background_sync_handler.dart`

Update `backgroundSyncCallback()` and `_performDesktopSync()`:
- Replace `SyncService(db)` with new SyncEngine instantiation
- SyncEngine uses SQLite advisory lock (sync_lock table), so concurrent foreground/background sync is prevented automatically

**Before (line 76-79 of background_sync_handler.dart):**
```dart
final syncService = SyncService(db);
syncService.setCompanyContext(companyId: companyId, userId: userId);
final result = await syncService.syncAll();
```

**After:**
```dart
// ADV-57: Verify auth session before starting background sync
final session = Supabase.instance.client.auth.currentSession;
if (session == null) {
  DebugLogger.sync('Background sync aborted: no active auth session');
  return;
}

final engine = SyncEngine(db, Supabase.instance.client, companyId: companyId, userId: userId);
// Advisory lock prevents concurrent foreground sync
final result = await engine.sync();
```

Same change for `_performDesktopSync()` (lines 195-198). Always check `currentSession` before instantiating SyncEngine in background isolates.

**[FIX: H12]** Background isolates cannot access foreground providers. Add a factory method to `SyncEngine`:

```dart
/// Factory for constructing SyncEngine in a fresh background isolate.
static Future<SyncEngine?> createForBackgroundSync({
  required DatabaseService dbService,
  required SupabaseClient supabase,
  String lockedBy = 'background',
}) async {
  final user = supabase.auth.currentUser;
  if (user == null) return null;

  final userProfile = await supabase
      .from('user_profiles')
      .select('company_id')
      .eq('id', user.id)
      .maybeSingle();
  final companyId = userProfile?['company_id'] as String?;
  if (companyId == null) return null;

  final db = await dbService.database;
  return SyncEngine(db: db, supabase: supabase, companyId: companyId, userId: user.id, lockedBy: lockedBy);
}
```

The background callback in `background_sync_handler.dart` should use this factory instead of
manually constructing dependencies.

### 4.0.2 Verify SyncLifecycleManager

**File**: `lib/features/sync/application/sync_lifecycle_manager.dart`

This file calls `_syncOrchestrator.syncLocalAgencyProjects()` and `_syncOrchestrator.lastSyncTime`. Since we updated the orchestrator in 4.0.1, verify these methods still work. The SyncLifecycleManager itself does not need changes — it delegates to the orchestrator.

### 4.0.3 FcmHandler Verification

[CORRECTION] The plan says "Verify `FcmHandler` is a no-op stub — confirm it does not call old SyncService methods." This is WRONG. `FcmHandler` is a full 104-line Firebase Messaging implementation at `lib/features/sync/application/fcm_handler.dart`. It:
- Initializes Firebase Messaging on Android/iOS
- Requests notification permissions
- Saves FCM token to Supabase via `AuthService.saveFcmToken()`
- Registers background and foreground message handlers
- Foreground `daily_sync` messages are acknowledged but ignored (sync handled by WorkManager)

**FcmHandler does NOT call old SyncService methods.** It only calls `AuthService.saveFcmToken()` and prints debug messages. No changes needed for FcmHandler. The plan's claim that it is a "no-op stub" is incorrect, but the conclusion (no action needed) is still correct — it has no dependency on the old sync system.

### 4.0.4 Update MockSyncAdapter

**File to modify**: `lib/features/sync/data/adapters/mock_sync_adapter.dart`

Update `MockSyncAdapter` to implement the new engine interfaces used for test mode. The mock adapter currently implements `SyncAdapter` which includes `queueOperation()`, `markProjectSynced()`, `markEntrySynced()`, `markPhotoSynced()`, and the old `sync()` method.

After Phase 7, these will be removed. The mock adapter needs to implement whatever interface the new SyncEngine exposes for test mode. If the SyncOrchestrator still uses mock detection, update the mock to implement the new adapter interface.

### 4.0.5 Cutover Step: Mark stale change_log entries as processed

**[FIX: H4/H14]** During Phases 1-6, triggers accumulated change_log entries while the old
SyncService was still running. These entries represent already-synced data and must NOT be
re-pushed by the new engine.

Before wiring the new engine, run:
```dart
// Mark all pre-cutover change_log entries as processed
await db.execute("UPDATE change_log SET processed = 1 WHERE processed = 0");
```

This gives the new engine a clean slate. No history is lost — the old SyncService already
pushed this data via sync_queue.

### 4.0.6 Drain Accumulated change_log

On first sync after wiring the new engine, process ALL newly accumulated change_log entries (those generated after the cutover mark in 4.0.5). The SyncEngine's normal push flow handles this automatically — `ChangeTracker` reads unprocessed entries from change_log.

No special code needed, but add a log message:
```dart
final pendingCount = await _changeTracker.getUnprocessedCount();
if (pendingCount > 0) {
  debugPrint('[SYNC_ENGINE] Draining $pendingCount accumulated change_log entries');
}
```

---

### 4.1 Phase 7a: Model & Enum Cleanup

#### 4.1.1 Remove syncStatus from DailyEntry Model

**File**: `lib/features/entries/data/models/daily_entry.dart`

**Remove field declaration (line 29):**
```dart
// DELETE: final SyncStatus syncStatus;
```

**Remove import (line 2):**
```dart
// DELETE: import 'package:construction_inspector/shared/models/sync_status.dart';
```

**Remove constructor parameter (line 58):**
```dart
// DELETE: this.syncStatus = SyncStatus.pending,
```

**Remove copyWith parameter (line 82):**
```dart
// DELETE: SyncStatus? syncStatus,
```

**Remove copyWith body reference (line 107):**
```dart
// DELETE: syncStatus: syncStatus ?? this.syncStatus,
```

**Remove from toMap() (line 135):**
```dart
// DELETE: 'sync_status': syncStatus.toJson(),
```

**Remove from fromMap() (line 190):**
```dart
// DELETE: syncStatus: SyncStatus.fromJson(map['sync_status'] as String?),
```

#### 4.1.2 Remove syncStatus from Photo Model

**File**: `lib/features/photos/data/models/photo.dart`

**Remove import (line 2):**
```dart
// DELETE: import 'package:construction_inspector/shared/models/sync_status.dart';
```

**Remove field declaration (line 17):**
```dart
// DELETE: final SyncStatus syncStatus;
```

**Remove constructor parameter (line 37):**
```dart
// DELETE: this.syncStatus = SyncStatus.pending,
```

**Remove copyWith parameter (line 60):**
```dart
// DELETE: SyncStatus? syncStatus,
```

**Remove copyWith body reference (line 76):**
```dart
// DELETE: syncStatus: syncStatus ?? this.syncStatus,
```

**Remove from toMap() (line 97):**
```dart
// DELETE: 'sync_status': syncStatus.toJson(),
```

**Remove from fromMap() (line 118):**
```dart
// DELETE: syncStatus: SyncStatus.fromJson(map['sync_status'] as String?),
```

#### 4.1.3 Delete SyncStatus Enum File

**File to delete**: `lib/shared/models/sync_status.dart`

Remove the entire file (32 lines).

**Update barrel exports** — find and remove `export 'sync_status.dart'` from:
- `lib/shared/models/models.dart` (or wherever it's exported)
- `lib/shared/shared.dart` (if re-exported)

#### 4.1.4 Remove getSyncStatusColor()

**File**: `lib/core/theme/colors.dart`
**Lines**: 172-183

**Delete:**
```dart
static Color getSyncStatusColor(String status) {
  switch (status.toLowerCase()) {
    case 'pending':
      return statusWarning;
    case 'synced':
      return statusSuccess;
    case 'error':
      return statusError;
    default:
      return textSecondary;
  }
}
```

**File**: `lib/core/theme/app_theme.dart`
**Line**: 1540

**Delete:**
```dart
static Color getSyncStatusColor(String status) => AppColors.getSyncStatusColor(status);
```

#### 4.1.5 Clean Up Remaining sync_status References in Datasources

**File**: `lib/features/entries/data/datasources/remote/daily_entry_remote_datasource.dart`
**Line**: 17

**Delete:**
```dart
map.remove('sync_status'); // BLOCKER-27: local-only field
```

This line is no longer needed because `DailyEntry.toMap()` will no longer include `sync_status`.

**File**: `lib/features/photos/data/datasources/remote/photo_remote_datasource.dart`
**Line**: 21

**Delete:**
```dart
map.remove('sync_status'); // BLOCKER-27: local-only field
```

Same reason — `Photo.toMap()` will no longer include `sync_status`.

**File**: `lib/features/entries/data/repositories/daily_entry_repository.dart`
**Line**: 235

**Before:**
```dart
'sync_status': 'pending',
```

**Delete this line.** The batch submit operation no longer needs to set sync_status — the change_log trigger handles tracking.

**Also remove import** of `sync_status.dart` from this file (line 2).

**File**: `lib/features/entries/data/datasources/local/daily_entry_local_datasource.dart`

**Line 73 — delete `getPendingSync()` method entirely (lines 71-77):**
```dart
// DELETE entire method - replaced by change_log
Future<List<DailyEntry>> getPendingSync() async {
  return getWhere(
    where: "sync_status != 'synced'",
    whereArgs: [],
    orderBy: 'updated_at ASC',
  );
}
```

**Line 93 — delete `updateSyncStatus()` method entirely (lines 93-104):**
```dart
// DELETE entire method - replaced by change_log
Future<void> updateSyncStatus(String id, String status) async { ... }
```

**Line 107 — update `updateStatus()` method (lines 107-119):**

[CORRECTION] The plan says `daily_entry_local_datasource.updateStatus()` "also handles entry status (needs refactoring, not deletion)." This is correct. The method updates the entry's `status` field (draft/submitted) and currently also sets `sync_status: 'pending'`. Remove only the sync_status line:

**Before:**
```dart
Future<void> updateStatus(String id, EntryStatus status) async {
  final database = await db.database;
  await database.update(
    tableName,
    {
      'status': status.name,
      'updated_at': DateTime.now().toIso8601String(),
      'sync_status': 'pending',
    },
    where: 'id = ?',
    whereArgs: [id],
  );
}
```

**After:**
```dart
Future<void> updateStatus(String id, EntryStatus status) async {
  final database = await db.database;
  await database.update(
    tableName,
    {
      'status': status.name,
      'updated_at': DateTime.now().toIso8601String(),
    },
    where: 'id = ?',
    whereArgs: [id],
  );
}
```

---

### 4.2 Phase 7b: Auth & Sign-Out Cleanup

**File**: `lib/features/auth/services/auth_service.dart`

**Line 328** — Currently in `clearLocalCompanyData()`, the tables list includes `'sync_queue'`. Replace with new engine tables.

**Before (lines 315-331):**
```dart
final tables = [
  'daily_entries', 'photos', 'entry_equipment',
  'entry_quantities', 'entry_personnel', 'entry_personnel_counts',
  'entry_contractors',
  'contractors', 'equipment', 'bid_items',
  'personnel_types',
  'locations',
  'inspector_forms',
  'projects',
  'user_profiles',
  'companies',
  'company_join_requests',
  'sync_queue',
  'stage_metrics',
  'extraction_metrics',
];
```

**After:**
```dart
final tables = [
  'daily_entries', 'photos', 'entry_equipment',
  'entry_quantities', 'entry_personnel', 'entry_personnel_counts',
  'entry_contractors',
  'contractors', 'equipment', 'bid_items',
  'personnel_types',
  'locations',
  'inspector_forms',
  'projects',
  'user_profiles',
  'companies',
  'company_join_requests',
  // New sync engine tables (replaces sync_queue)
  'change_log',
  'conflict_log',
  'sync_lock',
  'sync_metadata',
  'synced_projects',
  // [FIX: H11] storage_cleanup_queue MUST be included in the sign-out wipe list.
  // Without this, pending cleanup entries from a previous user could delete another
  // company's photos after re-sign-in.
  'storage_cleanup_queue',
  // Metrics tables
  'stage_metrics',
  'extraction_metrics',
];
```

---

### 4.3 Phase 7c: entry_personnel Legacy Cleanup

[CORRECTION] The plan says to delete `entry_personnel_local_datasource.dart` entirely, but this file manages BOTH the legacy `entry_personnel` table AND the active `entry_personnel_counts` table. The file CANNOT simply be deleted.

#### 4.3.1 Split the Datasource File

**File**: `lib/features/contractors/data/datasources/local/entry_personnel_local_datasource.dart`

**Step 1**: Create new file for entry_personnel_counts only:

**File to create**: `lib/features/contractors/data/datasources/local/entry_personnel_counts_local_datasource.dart`

Move lines 92-213 (all `entry_personnel_counts` methods) into a new class `EntryPersonnelCountsLocalDatasource`:

```dart
import 'package:construction_inspector/core/database/database_service.dart';

/// Local SQLite datasource for entry_personnel_counts.
///
/// Manages dynamic personnel type counts per entry/contractor.
class EntryPersonnelCountsLocalDatasource {
  final DatabaseService db;
  static const String _countsTable = 'entry_personnel_counts';

  EntryPersonnelCountsLocalDatasource(this.db);

  // ... move all entry_personnel_counts methods here (getCountsByEntryId,
  // saveCountsForEntryContractor, saveAllCountsForEntry, deleteCountsByEntryId,
  // getTotalCountForEntry) ...
}
```

**Step 2**: Update all imports that use `EntryPersonnelLocalDatasource` for counts methods.

Search for imports of `entry_personnel_local_datasource.dart`:
```
lib/features/entries/presentation/controllers/contractor_editing_controller.dart
```
This file uses `_personnelDatasource.saveCountsForEntryContractor()` — update import to new file and class name.

**Step 3**: Delete `entry_personnel_local_datasource.dart`

After extracting counts methods, the remaining `entry_personnel` methods are dead code (the legacy table has no adapter, no triggers, no Supabase sync). Delete the original file.

#### 4.3.2 Delete entry_personnel_remote_datasource.dart

**File to delete**: `lib/features/contractors/data/datasources/remote/entry_personnel_remote_datasource.dart`

This 32-line file is dead code — the entry_personnel table is not synced.

#### 4.3.3 Update Barrel Exports

**File**: `lib/features/contractors/data/datasources/local/local_datasources.dart`

**Before:**
```dart
export 'entry_personnel_local_datasource.dart';
```

**After:**
```dart
export 'entry_personnel_counts_local_datasource.dart';
```

**File**: `lib/features/contractors/data/datasources/remote/remote_datasources.dart`

**Remove:**
```dart
export 'entry_personnel_remote_datasource.dart';
```

#### 4.3.4 Remove entry_personnel from SoftDeleteService Cascade Lists

**File**: `lib/services/soft_delete_service.dart`

**Line 18** — `_childToParentOrder` list: Remove `'entry_personnel'` (keep `'entry_personnel_counts'`).

**Line 83** — `cascadeSoftDeleteEntry()` entryChildTables list: Remove `'entry_personnel'` (keep `'entry_personnel_counts'`).

**Line 121** (or wherever `cascadeRestoreEntry` is) — Remove `'entry_personnel'` from restore list (keep `'entry_personnel_counts'`).

---

### 4.4 Phase 7d: Seed Data & Test Harness

#### 4.4.1 Remove sync_status from Seed Data

**File**: `lib/core/database/seed_data_service.dart`
**Line**: 381

**Delete:**
```dart
'sync_status': 'synced',
```

The daily_entries table will no longer have a `sync_status` column after migration v31.

#### 4.4.2 Migrate cert_number in Test Harness Seed

**File**: `lib/test_harness/harness_seed_data.dart`
**Line**: 230

**Before:**
```dart
'cert_number': 'CERT-001',
```

**After:** Replace with a `user_certifications` seed entry (cert_number is now in the separate user_certifications table, not user_profiles or SharedPreferences).

Add to the seed data function:
```dart
await database.insert('user_certifications', {
  'id': 'cert-seed-001',
  'user_id': seedUserId,
  'cert_type': 'primary',
  'cert_number': 'CERT-001',
  'created_at': now,
  'updated_at': now,
});
```

And remove the `'cert_number'` key from whatever map it was in (likely a user_profiles seed entry).

#### 4.4.3 Remove sync_status from Test Harness Seed

Search `lib/test_harness/harness_seed_data.dart` for any `sync_status` references and remove them.

---

### 4.5 Phase 7e: Schema Verifier Cleanup

**File**: `lib/core/database/schema_verifier.dart`

#### 4.5.1 Remove sync_status from daily_entries Column List

**Line 64:**

**Before:**
```dart
'daily_entries': [
  'id', 'project_id', 'location_id', 'date', 'weather',
  'temp_low', 'temp_high', 'activities', 'site_safety', 'sesc_measures',
  'traffic_control', 'visitors', 'extras_overruns', 'signature', 'signed_at',
  'status', 'submitted_at', 'revision_number',
  'created_at', 'updated_at', 'sync_status',
  'created_by_user_id', 'updated_by_user_id',
  'deleted_at', 'deleted_by',
],
```

**After:**
```dart
'daily_entries': [
  'id', 'project_id', 'location_id', 'date', 'weather',
  'temp_low', 'temp_high', 'activities', 'site_safety', 'sesc_measures',
  'traffic_control', 'visitors', 'extras_overruns', 'signature', 'signed_at',
  'status', 'submitted_at', 'revision_number',
  'created_at', 'updated_at',
  'created_by_user_id', 'updated_by_user_id',
  'deleted_at', 'deleted_by',
],
```

#### 4.5.2 Remove sync_status from photos Column List

**Line 114:**

**Before:**
```dart
'photos': [
  'id', 'entry_id', 'project_id', 'file_path', 'filename',
  'remote_path', 'notes', 'caption', 'location_id',
  'latitude', 'longitude', 'captured_at', 'sync_status',
  'created_at', 'updated_at', 'created_by_user_id',
  'deleted_at', 'deleted_by',
],
```

**After:**
```dart
'photos': [
  'id', 'entry_id', 'project_id', 'file_path', 'filename',
  'remote_path', 'notes', 'caption', 'location_id',
  'latitude', 'longitude', 'captured_at',
  'created_at', 'updated_at', 'created_by_user_id',
  'deleted_at', 'deleted_by',
],
```

#### 4.5.3 Remove sync_status from Self-Heal Definitions

**Line 188:**

**Before (daily_entries self-heal):**
```dart
'daily_entries': {
  ...
  'sync_status': "TEXT DEFAULT 'pending'",
  ...
},
```

**After:** Remove the `'sync_status'` entry entirely from the daily_entries self-heal map.

**Line 218:**

**Before (photos self-heal):**
```dart
'photos': {
  ...
  'sync_status': "TEXT DEFAULT 'pending'",
  ...
},
```

**After:** Remove the `'sync_status'` entry entirely from the photos self-heal map.

#### 4.5.4 Remove sync_queue from Verified Tables

**Line 120:**

**Before:**
```dart
'sync_queue': [
  'id', 'table_name', 'record_id', 'operation', 'payload',
  'created_at', 'attempts', 'last_error',
],
```

**After:** Delete this entire entry. The sync_queue table no longer exists.

**Also remove** the sync_queue self-heal entry (line 224):
```dart
'sync_queue': {
  'attempts': 'INTEGER DEFAULT 0',
},
```

#### 4.5.5 Add New Engine Tables to Verified Tables

These should already have been added in Phase 1 (the plan says so in Phase 1 tasks). Verify they exist:

```dart
'change_log': [
  'id', 'table_name', 'record_id', 'operation', 'old_data', 'new_data',
  'metadata', 'created_at', 'processed_at', 'retry_count',
],
'conflict_log': [
  'id', 'table_name', 'record_id', 'conflict_type', 'local_data',
  'remote_data', 'lost_data', 'winner', 'detected_at', 'dismissed_at',
  'expires_at',
],
'sync_control': [
  'id', 'pulling',
],
'sync_lock': [
  'id', 'locked_by', 'locked_at', 'expires_at',
],
'synced_projects': [
  'project_id', 'added_at',
],
'user_certifications': [
  'id', 'user_id', 'cert_type', 'cert_number',
  'created_at', 'updated_at',
],
```

If not already present, add them now.

---

### 4.6 Phase 7f: Testing Keys Cleanup

**File**: `lib/shared/testing_keys/settings_keys.dart`

#### 4.6.1 Remove Dead Inspector Profile Keys

The plan lists these keys to remove:
- `settingsInspectorNameTile` (line 86)
- `settingsInspectorInitialsTile` (line 87)
- `settingsInspectorAgencyTile` (line 90)
- `editInspectorNameDialog` (line 56)
- `editInspectorNameCancel` (line 59)
- `editInspectorNameSave` (line 62)
- `editInspectorAgencyDialog` (line 100)
- `editInspectorAgencySave` (line 101)
- `settingsUseLastValuesToggle` (line 106)

[CORRECTION] The plan's list is INCOMPLETE. Also remove these dead keys for the phone/cert dialogs that the analysis flagged:
- `settingsInspectorPhoneTile` (line 88) — if the phone tile is removed from settings
- `settingsInspectorCertTile` (line 89) — if the cert tile is removed from settings
- `editInspectorPhoneDialog` (line 96) — if the phone dialog is removed
- `editInspectorPhoneSave` (line 97) — if the phone dialog is removed
- `editInspectorCertDialog` (line 98) — if the cert dialog is removed
- `editInspectorCertSave` (line 99) — if the cert dialog is removed

**Determination**: If the Edit Profile screen (Step 3.12) replaces individual dialog-based editing with a full profile editor screen, then ALL the individual dialog keys are dead and should be removed. If the Edit Profile screen still uses individual edit dialogs per field, keep the relevant keys.

**Conservative approach**: Remove only the keys the plan explicitly lists PLUS the `settingsUseLastValuesToggle`. Keep phone/cert keys if the Edit Profile screen is uncertain. The implementation agent should verify at implementation time.

#### 4.6.2 Update testing_keys.dart Barrel Export

**File**: `lib/shared/testing_keys/testing_keys.dart`

Verify that no removed keys are re-exported here. Since the keys are static members of `SettingsTestingKeys`, not individual exports, this file likely just exports `settings_keys.dart` and no changes are needed.

---

### 4.7 Phase 7g: PreferencesService Cleanup

**File**: `lib/shared/services/preferences_service.dart`

#### 4.7.1 Remove inspectorProfile Getter

[CORRECTION] The plan references `buildInspectorProfile()` method at "~line 320". The actual method is a **getter** named `inspectorProfile` at line 316, not a method called `buildInspectorProfile()`.

**Line 316-322 — Delete:**
```dart
Map<String, String?> get inspectorProfile => {
      'name': inspectorName,
      'initials': effectiveInitials,
      'phone': inspectorPhone,
      'cert_number': inspectorCertNumber,
      'agency': inspectorAgency,
    };
```

**Also delete `hasInspectorProfile` getter (line 325-326):**
```dart
bool get hasInspectorProfile =>
    inspectorName != null && inspectorName!.isNotEmpty;
```

#### 4.7.2 Remove Dead Pref Key Constants

**Lines 15-20 — Remove these constants:**
```dart
static const String keyInspectorName = 'inspector_name';       // line 15
static const String keyInspectorInitials = 'inspector_initials'; // line 16
static const String keyInspectorPhone = 'inspector_phone';      // line 17
static const String keyInspectorCertNumber = 'inspector_cert_number'; // line 18
static const String keyInspectorAgency = 'inspector_agency';    // line 20
```

**Also remove the corresponding getter/setter methods:**
- `inspectorName` getter (line 57) and `setInspectorName()` setter (line 63)
- `inspectorInitials` getter (line 70) and `setInspectorInitials()` setter (line 76)
- `inspectorPhone` getter (line 92) and `setInspectorPhone()` setter (line 98)
- `inspectorCertNumber` getter (line 105) and `setInspectorCertNumber()` setter (line 111)
- `inspectorAgency` getter (line 131) and `setInspectorAgency()` setter (line 137)
- `effectiveInitials` getter (if it exists — derives initials from name)

**Also remove these dead pref keys** (from Phase 6 task list):
- `show_only_manual_fields` key and accessor
- `last_route_location` key and accessor
- `prefill_*` family keys and accessors (all keys starting with `prefill_`)
- `inspector_agency` key (already listed above)
- `gauge_number` key and accessor (if stored in prefs — now in user_profiles)

**Also remove dead toggle accessors:**
- `autoFetchWeather` getter and `setAutoFetchWeather()` setter
- `autoSyncWifi` getter and `setAutoSyncWifi()` setter
- `autoFillEnabled` getter and `setAutoFillEnabled()` setter
- `useLastValues` getter and `setUseLastValues()` setter

---

### 4.8 Phase 7h: Final Verification — Remove Old Sync Infrastructure

This is the largest single cleanup step. It removes the old SyncService and all its supporting infrastructure.

#### 4.8.1 Delete Old SyncService

**File to delete**: `lib/services/sync_service.dart` (1535 lines)

This removes:
- `SyncOpStatus` enum
- `SyncConfig` class
- `SyncProgressCallback` typedef
- `SyncResult` class
- `SyncService` class with all methods including:
  - `syncAll()`
  - `_pushBaseData()`
  - `_pushPendingEntries()`
  - `_pushPendingPhotos()`
  - `queueOperation()`
  - All private helper methods

**Update all imports** that reference `sync_service.dart`:
- `lib/features/sync/data/adapters/supabase_sync_adapter.dart` — this file wraps old SyncService, delete it (see 4.8.2)
- `lib/test_harness/stub_services.dart` — update StubSyncService (see 4.8.5)
- `lib/features/sync/application/background_sync_handler.dart` — already updated in 4.0.1

#### 4.8.2 Delete SupabaseSyncAdapter (Old Wrapper)

**File to delete**: `lib/features/sync/data/adapters/supabase_sync_adapter.dart`

This file wraps the old SyncService. With the new SyncEngine, this wrapper is dead code.

**Update barrel exports:**
- `lib/features/sync/data/adapters/adapters.dart` — remove export of `supabase_sync_adapter.dart`
- `lib/features/sync/data/data.dart` — verify no re-export

#### 4.8.3 Delete SyncStatusBanner Widget

**File to delete**: `lib/features/sync/presentation/widgets/sync_status_banner.dart`

This is replaced by `SyncStatusIcon` (created in Phase 6).

#### 4.8.4 Update home_screen.dart

**File**: `lib/features/entries/presentation/screens/home_screen.dart`

**Line 27 — Remove import:**
```dart
// DELETE: import 'package:construction_inspector/features/sync/presentation/widgets/sync_status_banner.dart';
```

**Line 381 — Replace widget:**

**Before:**
```dart
const SyncStatusBanner(),
```

**After:**
```dart
// SyncStatusBanner removed — SyncStatusIcon is now in the AppBar
// (If the SyncStatusIcon is in the app bar, this line can be deleted entirely.
// If it should appear in the body, replace with the new widget.)
```

The `SyncStatusIcon` should be placed in the app bar (via `AppBar(actions: [const SyncStatusIcon()])`) rather than in the body. Update the home_screen's AppBar to include it.

#### 4.8.5 Update StubSyncService

**File**: `lib/test_harness/stub_services.dart`

`StubSyncService` extends `SyncService`. Since we're deleting `SyncService`, either:
- Delete `StubSyncService` entirely if no test harness code references it
- Replace with a `StubSyncEngine` that implements the new engine interface

**Lines 15-39:**

**Before:**
```dart
class StubSyncService extends SyncService {
  StubSyncService(super.dbService);
  @override
  Future<SyncResult> syncAll() async => SyncResult();
  @override
  Future<void> queueOperation(...) async {}
  @override
  Future<int> getPendingCount() async => 0;
  @override
  void scheduleDebouncedSync() {}
  @override
  void dispose() {}
}
```

**After:**
```dart
class StubSyncEngine {
  Future<void> sync() async {}
  Future<int> getPendingCount() async => 0;
  void dispose() {}
}
```

#### 4.8.6 Remove SyncStatusMixin

**File**: `lib/shared/datasources/query_mixins.dart`
**Lines 34-71**

**Delete the entire `SyncStatusMixin`:**
```dart
// DELETE: mixin SyncStatusMixin { ... } (lines 35-71)
```

Also delete the comment on line 34:
```dart
// DELETE: /// Mixin for entities with sync_status column
```

Keep `BatchOperationsMixin` (lines 1-32) — it is not related to the old sync system.

**Search for classes that use `SyncStatusMixin`** and remove the mixin:
```
rg 'with.*SyncStatusMixin' lib/
```

#### 4.8.7 Extract Sync Types + Remove Old SyncAdapter Interface

**Step 1: Extract types to new file**

**File to create**: `lib/features/sync/domain/sync_types.dart`

Extract `SyncResult` and `SyncAdapterStatus` from the old `sync_adapter.dart` into this new file. These types are still used by the new engine and adapters.

```dart
/// Result of a sync operation (used by SyncEngine and adapters).
class SyncResult {
  final int pushed;
  final int pulled;
  final int errors;
  final List<String> errorMessages;
  // ... (preserve existing fields)
}

/// Status of a sync adapter (used by SyncProvider for UI state).
enum SyncAdapterStatus {
  idle,
  syncing,
  error,
  offline,
}
```

**Step 2: Delete old interface**

**File to delete**: `lib/features/sync/domain/sync_adapter.dart`

Delete the old `SyncAdapter` abstract class (with `queueOperation()`, `markProjectSynced()`, etc.). The extracted types now live in `sync_types.dart`.

**[FIX: A4]** Keep `MockSyncAdapter` during transition for E2E test flows that still use
the old `SyncProvider`. Add a new `SyncEngineMock` for unit tests of the new engine.
Delete both `SyncAdapter` interface and `MockSyncAdapter` only after ALL test flows are
migrated to the new engine.

**Step 3: Update all imports**

Replace all `import '...sync_adapter.dart'` with `import '...sync_types.dart'` across the codebase.

#### 4.8.8 Remove All queueOperation() Calls

Complete inventory of files with `queueOperation` calls:

**1. `lib/features/calculator/presentation/providers/calculator_provider.dart`**
- Line 151: `await _syncOrchestrator?.queueOperation('calculation_history', record.id, 'insert');` — DELETE
- Line 171: `await _syncOrchestrator?.queueOperation('calculation_history', id, 'delete');` — DELETE

**2. `lib/features/forms/presentation/providers/inspector_form_provider.dart`**
- Line 219: `await _syncOrchestrator?.queueOperation(...)` — DELETE
- Line 249: `await _syncOrchestrator?.queueOperation(...)` — DELETE
- Line 279: `await _syncOrchestrator?.queueOperation(...)` — DELETE
- Line 305: `await _syncOrchestrator?.queueOperation(...)` — DELETE
- Line 331: `await _syncOrchestrator?.queueOperation(...)` — DELETE

**3. `lib/features/todos/presentation/providers/todo_provider.dart`**
[CORRECTION] The plan says 4 calls, but there are actually 5:
- Line 125: `await _syncOrchestrator?.queueOperation('todo_items', todo.id, 'insert');` — DELETE
- Line 148: `await _syncOrchestrator?.queueOperation('todo_items', todo.id, 'update');` — DELETE
- Line 167: `await _syncOrchestrator?.queueOperation('todo_items', id, 'update');` — DELETE
- Line 187: `await _syncOrchestrator?.queueOperation('todo_items', id, 'delete');` — DELETE
- Line 210: `await _syncOrchestrator?.queueOperation('todo_items', id, 'delete');` — DELETE

**4. `lib/features/settings/presentation/screens/personnel_types_screen.dart`**
- Line 104: `await syncProvider.queueOperation(...)` — DELETE
- Line 239: `await syncProvider.queueOperation(...)` — DELETE
- Line 337: `await syncProvider.queueOperation(...)` — DELETE
- Line 397: `await syncProvider.queueOperation(...)` — DELETE

**5. `lib/features/sync/presentation/providers/sync_provider.dart`**
- Line 157-163: `queueOperation()` method definition — DELETE entire method

**6. `lib/features/sync/application/sync_orchestrator.dart`**
- Line 366 (comment) + Line 371-377: `queueOperation()` method definition — DELETE entire method

**7. `lib/features/sync/data/adapters/supabase_sync_adapter.dart`**
- Lines 110, 117, 124, 135-141: All `queueOperation` calls and method — FILE DELETED in 4.8.2

**8. `lib/features/sync/data/adapters/mock_sync_adapter.dart`**
- Lines 98-105: `queueOperation()` method — DELETE (or update interface per 4.8.7)

**9. `lib/features/sync/domain/sync_adapter.dart`**
- Line 115: `queueOperation()` interface definition — DELETE (or file deleted per 4.8.7)

**10. `lib/services/sync_service.dart`**
- Lines 1358, 1466: `queueOperation()` — FILE DELETED in 4.8.1

**11. `lib/test_harness/stub_services.dart`**
- Line 24: `queueOperation()` stub — UPDATED in 4.8.5

**Why these deletions are safe**: The change_log triggers installed in Phase 1 automatically capture all INSERT/UPDATE/DELETE operations. Manual `queueOperation()` calls are no longer needed.

#### 4.8.9 Remove sync_status Column from SQLite (Migration v31)

**File to modify**: `lib/core/database/database_service.dart`

Add migration v31 that removes `sync_status` from `daily_entries` and `photos` tables, and drops the `sync_queue` table.

**IMPORTANT**: SQLite on Android < API 35 does NOT support `ALTER TABLE DROP COLUMN`. Must use the table rebuild pattern.

```dart
if (oldVersion < 31) {
  // ---- Remove sync_status from daily_entries (table rebuild) ----
  await db.execute('''
    CREATE TABLE daily_entries_new (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      location_id TEXT,
      date TEXT NOT NULL,
      weather TEXT,
      temp_low INTEGER,
      temp_high INTEGER,
      activities TEXT,
      site_safety TEXT,
      sesc_measures TEXT,
      traffic_control TEXT,
      visitors TEXT,
      extras_overruns TEXT,
      signature TEXT,
      signed_at TEXT,
      status TEXT NOT NULL DEFAULT 'draft',
      submitted_at TEXT,
      revision_number INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      updated_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
      FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL
    )
  ''');
  await db.execute('''
    INSERT INTO daily_entries_new
    SELECT id, project_id, location_id, date, weather, temp_low, temp_high,
           activities, site_safety, sesc_measures, traffic_control, visitors,
           extras_overruns, signature, signed_at, status, submitted_at,
           revision_number, created_at, updated_at,
           created_by_user_id, updated_by_user_id, deleted_at, deleted_by
    FROM daily_entries
  ''');
  await db.execute('DROP TABLE daily_entries');
  await db.execute('ALTER TABLE daily_entries_new RENAME TO daily_entries');

  // Recreate indexes (sync_status index is NOT recreated)
  await db.execute('CREATE INDEX idx_daily_entries_project ON daily_entries(project_id)');
  await db.execute('CREATE INDEX idx_daily_entries_location ON daily_entries(location_id)');
  await db.execute('CREATE INDEX idx_daily_entries_date ON daily_entries(date)');
  await db.execute('CREATE INDEX idx_daily_entries_project_date ON daily_entries(project_id, date)');
  await db.execute('CREATE INDEX idx_daily_entries_deleted_at ON daily_entries(deleted_at)');

  // [FIX: C14] After table rebuild, triggers must be recreated using SyncEngineTables constants.
  // Recreate change_log triggers for daily_entries (since DROP TABLE removes them).
  for (final trigger in SyncEngineTables.triggersForTable('daily_entries')) {
    await db.execute(trigger);
  }

  // ---- Remove sync_status from photos (table rebuild) ----
  await db.execute('''
    CREATE TABLE photos_new (
      id TEXT PRIMARY KEY,
      entry_id TEXT NOT NULL,
      project_id TEXT NOT NULL,
      file_path TEXT NOT NULL,
      filename TEXT NOT NULL,
      remote_path TEXT,
      notes TEXT,
      caption TEXT,
      location_id TEXT,
      latitude REAL,
      longitude REAL,
      captured_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (entry_id) REFERENCES daily_entries(id) ON DELETE CASCADE,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
      FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL
    )
  ''');
  await db.execute('''
    INSERT INTO photos_new
    SELECT id, entry_id, project_id, file_path, filename, remote_path,
           notes, caption, location_id, latitude, longitude, captured_at,
           created_at, updated_at, created_by_user_id, deleted_at, deleted_by
    FROM photos
  ''');
  await db.execute('DROP TABLE photos');
  await db.execute('ALTER TABLE photos_new RENAME TO photos');

  // Recreate indexes (sync_status index is NOT recreated)
  await db.execute('CREATE INDEX idx_photos_entry ON photos(entry_id)');
  await db.execute('CREATE INDEX idx_photos_project ON photos(project_id)');
  await db.execute('CREATE INDEX idx_photos_deleted_at ON photos(deleted_at)');

  // [FIX: C14] Recreate change_log triggers for photos using SyncEngineTables constants.
  // List ALL tables that v31 rebuilds: daily_entries and photos.
  // Both DROP TABLE operations remove their triggers; both must be recreated.
  for (final trigger in SyncEngineTables.triggersForTable('photos')) {
    await db.execute(trigger);
  }

  // ---- Drop sync_queue table ----
  await db.execute('DROP TABLE IF EXISTS sync_queue');

  // ---- Drop sync_status indexes (already gone from table rebuilds) ----
  // idx_daily_entries_sync_status — already gone
  // idx_photos_sync_status — already gone
}
```

**Increment database version** to 31.

**CRITICAL**: After table rebuild, the change_log triggers for `daily_entries` and `photos` must be recreated (DROP TABLE removes them). Copy the trigger DDL from Phase 1.

#### 4.8.10 Update Schema Definition Files

**File**: `lib/core/database/schema/entry_tables.dart`

**Line 28 — Delete:**
```dart
sync_status TEXT DEFAULT 'pending',
```

**Line 78 — Delete:**
```dart
'CREATE INDEX idx_daily_entries_sync_status ON daily_entries(sync_status)',
```

**File**: `lib/core/database/schema/photo_tables.dart`

**Line 20 — Delete:**
```dart
sync_status TEXT DEFAULT 'pending',
```

**Line 36 — Delete:**
```dart
'CREATE INDEX idx_photos_sync_status ON photos(sync_status)',
```

**File**: `lib/core/database/schema/sync_tables.dart`

Remove the `createSyncQueueTable` definition and its indexes:

**Lines 6-17 — Delete or comment out:**
```dart
static const String createSyncQueueTable = '''
  CREATE TABLE sync_queue ( ... )
''';
```

**Lines 37-38 — Delete:**
```dart
'CREATE INDEX idx_sync_queue_table ON sync_queue(table_name)',
'CREATE INDEX idx_sync_queue_created ON sync_queue(created_at)',
```

Keep `createDeletionNotificationsTable` and its indexes — those are still used.

#### 4.8.11 Update database_service.dart Schema References

**File**: `lib/core/database/database_service.dart`

**Line 392-397 — Delete sync_status indexes from initial schema creation:**
```dart
// DELETE: 'CREATE INDEX IF NOT EXISTS idx_daily_entries_sync_status ON daily_entries(sync_status)',
// DELETE: 'CREATE INDEX IF NOT EXISTS idx_photos_sync_status ON photos(sync_status)',
```

**Lines 945, 977, 1000, 1053, 1080, 1095** — These are in migration code for older versions. Do NOT modify migration code for versions < 31 — those migrations run on fresh installs and must remain valid for the version they target. The v31 migration handles the cleanup.

**Line 239-257** — Migration v2 (creates sync_queue table). Do NOT delete — this migration still needs to run on devices upgrading from v1. The v31 migration drops the table afterward.

#### 4.8.12 Remove deleteAll() from BaseRemoteDatasource (or restrict)

**File**: `lib/shared/datasources/base_remote_datasource.dart`
**Line**: 90-91

Currently has an assert:
```dart
Future<void> deleteAll() async {
  assert(!kReleaseMode, 'deleteAll() is not allowed in release builds');
```

**Options:**
1. Delete entirely (recommended by the plan)
2. Move to a test-only subclass

**Recommended approach**: Delete the method. Any test code that needs it can use direct Supabase client calls.

Also remove `deleteAll()` from:
- `lib/shared/datasources/base_local_datasource.dart:32` — the abstract interface
- `lib/shared/datasources/generic_local_datasource.dart:210` — the implementation

#### 4.8.13 Remove _pushBaseData, _pushPendingEntries, _pushPendingPhotos

These are all in `lib/services/sync_service.dart` which is being deleted in 4.8.1. No separate action needed.

#### 4.8.14 Drop Supabase sync_status Column (Separate Migration)

**File**: `supabase/migrations/20260304200000_drop_sync_status_from_supabase.sql`

This migration file already exists (per git status). It removes the `sync_status` column from Supabase tables. Deploy this migration when Phase 7 is complete.

### 4.9 Phase 7i: Test File Cleanup

After all production code cleanup in Phase 7a-7h, clean up the test files that reference removed APIs.

#### 4.9.1 DELETE test files (no longer valid)

- **`test/services/sync_service_test.dart`** -- Tests for old SyncService which is deleted in 4.8.1. Delete entirely.
- **`test/golden/components/sync_status_test.dart`** -- Tests for old SyncStatus widget. Delete entirely.

#### 4.9.2 UPDATE test helper files

- **`test/helpers/test_helpers.dart`** -- Remove sync_status imports, remove sync_status parameters from helper functions.
- **`test/helpers/mocks/mock_repositories.dart`** -- Remove `getPendingSync()`, `markSynced()`, and any other old sync methods from mock repositories.
- **`test/helpers/mock_database.dart`** -- Remove `sync_status` column from test table schemas. Remove `sync_queue` table creation from test database setup.
- **`test/helpers/mocks/mock_services.dart`** -- Remove old SyncService mock. Add mock for new SyncEngine if needed.

#### 4.9.3 UPDATE model test files

- **`test/data/models/daily_entry_test.dart`** -- Remove `syncStatus` field assertions from toMap/fromMap/copyWith tests. Remove SyncStatus enum imports.
- **`test/data/models/photo_test.dart`** -- Remove `syncStatus` field assertions from toMap/fromMap/copyWith tests. Remove SyncStatus enum imports.

#### 4.9.4 UPDATE repository test files

- **`test/data/repositories/daily_entry_repository_test.dart`** -- Remove `sync_status` column from mock query results. Remove `markSynced()` test cases.
- **`test/data/repositories/photo_repository_test.dart`** -- Remove `sync_status` column from mock query results. Remove `markSynced()` test cases.

#### 4.9.5 UPDATE provider test files

- **`test/features/sync/presentation/providers/sync_provider_test.dart`** -- Update to test against new SyncEngine API instead of old SyncService. Replace `SyncStatus` references with `SyncAdapterStatus`.

---

## Step 5: Verification Checklist

### 5.1 Dead Code Grep Commands

After all Phase 7 changes (including Phase 7i test cleanup), run these grep commands. **All must return zero matches** in both `lib/` and `test/` (unless noted):

```bash
# 1. sync_status — should be completely removed from lib/
rg 'sync_status' lib/
# Expected: 0 matches

# 2. sync_queue — should be completely removed from lib/
# EXCEPTION: database_service.dart migration code for versions < 31 may still reference it
rg 'sync_queue' lib/ --glob '!**/database_service.dart'
# Expected: 0 matches

# 3. queueOperation — should be completely removed from lib/
rg 'queueOperation' lib/
# Expected: 0 matches

# 4. SyncStatusMixin — should be completely removed from lib/
rg 'SyncStatusMixin' lib/
# Expected: 0 matches

# 5. markSynced — should be completely removed from lib/
rg 'markSynced' lib/
# Expected: 0 matches

# 6. SyncStatusBanner — should be completely removed from lib/
rg 'SyncStatusBanner' lib/
# Expected: 0 matches

# 7. SyncService import — should be completely removed from lib/
rg "import.*sync_service" lib/
# Expected: 0 matches (may need to exclude test harness if StubSyncEngine still imports)

# 8. getSyncStatusColor — should be completely removed from lib/
rg 'getSyncStatusColor' lib/
# Expected: 0 matches

# 9. SyncStatus enum — should be completely removed from lib/
rg 'SyncStatus\.' lib/
# Expected: 0 matches

# 10. Old sync adapter wrapper — should be completely removed from lib/
rg 'SupabaseSyncAdapter' lib/
# Expected: 0 matches

# 11. _pushBaseData, _pushPendingEntries, _pushPendingPhotos — should be completely removed
rg '_pushBaseData|_pushPendingEntries|_pushPendingPhotos' lib/
# Expected: 0 matches

# 12. entry_personnel_local_datasource (old file) — should be deleted
rg 'entry_personnel_local_datasource' lib/
# Expected: 0 matches (replaced by entry_personnel_counts_local_datasource)

# 13. entry_personnel_remote_datasource (old file) — should be deleted
rg 'entry_personnel_remote_datasource' lib/
# Expected: 0 matches

# 14. EditInspectorDialog — should be deleted
rg 'EditInspectorDialog|edit_inspector_dialog' lib/
# Expected: 0 matches

# 15. buildInspectorProfile / inspectorProfile getter in prefs
rg 'inspectorProfile|buildInspectorProfile' lib/shared/services/preferences_service.dart
# Expected: 0 matches

# 16. Raw SharedPreferences access for inspector fields
rg "prefs\.getString\('inspector_" lib/
# Expected: 0 matches

# === TEST DIRECTORY CHECKS (Phase 7i) ===

# 17. sync_status in test files — should be removed after Phase 7i cleanup
rg 'sync_status' test/
# Expected: 0 matches (EXCEPTION: test migration code may still reference it)

# 18. SyncService references in test files — should be removed
rg 'SyncService' test/
# Expected: 0 matches

# 19. sync_queue in test files — should be removed
rg 'sync_queue' test/
# Expected: 0 matches

# 20. Old SyncStatus enum in test files
rg 'SyncStatus\.' test/
# Expected: 0 matches (replaced by SyncAdapterStatus)

# 21. getPendingSync/markSynced in test mocks
rg 'getPendingSync|markSynced' test/
# Expected: 0 matches
```

### 5.2 Compile Check

```bash
pwsh -Command "flutter analyze"
```

Expected: zero errors, zero warnings related to sync infrastructure.

### 5.3 Full Test Suite

```bash
pwsh -Command "flutter test"
```

Expected: all existing tests pass (some may need updates for removed sync_status field).

### 5.4 Stage Trace Scorecard

Run full stage trace: 16 tables x 6 stages = 96 checks.

Stages:
1. **Trigger**: INSERT/UPDATE/DELETE -> change_log entry created
2. **Read**: ChangeTracker reads grouped changes
3. **Convert-Remote**: convertForRemote produces valid payload
4. **Push**: Supabase upsert/delete succeeds
5. **Convert-Local**: convertForLocal produces valid SQLite map
6. **Pull**: Incremental pull with cursor, deduplication, conflict resolution

All 96/96 must be OK.

### 5.5 Integration Tests

| Test | Description |
|------|-------------|
| Sync on connectivity restore | Push + incremental pull |
| Sync on app open (stale) | Forced sync |
| Manual sync via Sync Dashboard | Button triggers sync |
| Soft-delete -> push -> pull on second device -> deleted | End-to-end soft-delete |
| Purge from trash -> push -> gone from Supabase | Purge bypasses triggers via sync_control gate |
| Photo full lifecycle | Create -> sync -> edit caption -> sync -> soft-delete -> sync -> purge |
| Conflict scenario | Both sides edit -> LWW -> conflict logged -> visible in UI |
| Integrity check | Runs every 4 hours, results visible in dashboard |
| New team member first sync | Project selection -> select projects -> full pull |
| Settings | All new sections render, no dead items, gauge number and initials work |
| BackgroundSyncHandler | Spawns own SyncEngine, advisory lock prevents concurrent foreground sync |
| SyncLifecycleManager | Calls through rewired orchestrator successfully |
| MockSyncAdapter | Implements new engine interfaces, test mode works |
| user_certifications | Syncs alongside user_profiles, UNIQUE constraint respected |
| Profile expansion | gauge_number, initials, agency read from user_profiles (not prefs) |
| Sign-out wipes new engine tables | change_log, conflict_log, sync_lock, sync_metadata, synced_projects |
| Sign-out does NOT reference sync_queue | Table no longer exists |
| Seed data inserts succeed | Without sync_status column |
| entry_personnel datasource files deleted | No imports reference them |
| SoftDeleteService cascade lists | Do NOT include entry_personnel |
| Schema verifier validates new engine tables | On startup |
| Schema verifier does NOT reference sync_status or sync_queue | Clean |
| Dead testing keys removed | From settings_keys.dart |
| entry_photos_section reads from AuthProvider | Not raw SharedPreferences |
| form_response_repository resolves cert_number | From user_certifications, not PreferencesService |
| DailyEntry.toMap()/fromMap() | Do NOT include sync_status |
| Photo.toMap()/fromMap() | Do NOT include sync_status |

### 5.6 Database Migration Test

Test on **minSdk 24 device** (Android 7.0) to verify the table rebuild migration works on old SQLite versions that lack `ALTER TABLE DROP COLUMN`.

Steps:
1. Install previous version (with sync_status columns and sync_queue table)
2. Insert test data in daily_entries and photos with various sync_status values
3. Upgrade to new version
4. Verify all data preserved (minus sync_status column)
5. Verify sync_queue table is gone
6. Verify new indexes exist
7. Verify change_log triggers still fire on the rebuilt tables

### 5.7 Corrections Summary

| Item | Plan Said | Actual Finding | Resolution |
|------|-----------|----------------|------------|
| FcmHandler | "no-op stub" | Full 104-line Firebase Messaging implementation | No changes needed — it does not call old SyncService methods |
| entry_personnel_local_datasource | "Delete entire file" | Manages BOTH entry_personnel AND entry_personnel_counts | Split file: extract counts methods to new class, then delete original |
| todo_provider queueOperation calls | "4 calls" | 5 calls (insert, update, update, delete, delete) | Remove all 5 |
| PreferencesService method | `buildInspectorProfile()` | `inspectorProfile` getter (not a method) | Delete the getter at line 316 |
| Dead testing keys | List of 9 keys | Missing phone/cert dialog keys | Add phone/cert dialog keys if Edit Profile screen replaces dialogs |
| daily_entry_local_datasource.updateStatus() | Not explicitly mentioned | Also sets sync_status: 'pending' — needs refactoring, not deletion | Remove only the sync_status line from the update map |
| saveForEntry() pattern | Not explicitly addressed | DELETE+re-INSERT bypasses change_log trigger intent | Refactor to diff-based approach for entry_equipment; entry_personnel can stay (legacy, unsynced) |
| Schema *.dart files | Not mentioned | entry_tables.dart and photo_tables.dart have sync_status in DDL | Update both schema definition files |

---

# Appendix A: Risk Mitigation

(Copied from original plan for reference)

| Risk | Mitigation |
|------|------------|
| New engine has bugs old system didn't | Big Bang on feature branch -- old SyncService stays functional throughout development. Stage trace scorecard (96/96) is the quality gate before merge. Git history is the rollback mechanism. |
| SQLite triggers add write latency | Benchmark: triggers add ~1ms per single write. Cascade benchmark (500 records) target: <500ms on mid-range device. Purge operations bypass triggers via sync_control gate. |
| Migration v30 is complex (table rebuild for entry_personnel_counts) | Test migration on copy of production DB before deploying. Schema verifier catches drift. |
| Photo three-phase adds push complexity | Each phase is independently testable. Failure at any phase is recoverable. Orphan scanner detects abandoned uploads. |
| Settings redesign breaks user muscle memory | Sections are reorganized but all kept items are still present. No functional loss. Auto-Load toggle preserved in APPEARANCE. |
| Incremental pull misses records due to clock skew | 5-second safety margin on cursor comparison. 4-hour integrity check with id_checksum catches drift much faster than daily. |
| Migration v31 DROP COLUMN on old Android | SQLite < 3.35.0 (Android < API 35) lacks ALTER TABLE DROP COLUMN. Use table rebuild pattern (CREATE -> INSERT INTO SELECT -> DROP -> RENAME). Test on minSdk 24 device. |
| SoftDeleteService purge bypass with triggers | Purge flow sets sync_control.pulling='1' to suppress triggers, then manually inserts change_log entry. try/finally guarantees reset. Unit test required. |
| Cleanup misses stale references | Phase 7h dead code grep (`sync_status`, `sync_queue`, `queueOperation`, `SyncStatusMixin`, `markSynced`, `SyncStatusBanner`) must return zero hits before merge. |
| Trigger-pull feedback loop | sync_control table gates trigger execution during pull. WHEN clause prevents change_log entries during pull. Startup force-reset recovers from crash. |
| Concurrent sync from foreground + background | SQLite advisory lock with 5-minute auto-expiry replaces Completer mutex. Works across isolates. |
| Auth token expires during long sync | 401 triggers token refresh. Auth failures never increment retry_count. Refresh failure aborts sync with "re-login required." |
| First sync overwhelming for large companies | User-driven project selection -- user chooses what to download. Pull scoped to synced_projects only. Progress indicator per table. |
| profile reads break during auth flow | No fallback to prefs -- if userProfile is null, form auto-fill shows empty. This is correct behavior (user not logged in). |

---

# Appendix B: Agent Assignments

(Copied from original plan for reference)

| Phase | Primary Agent | Secondary Agent |
|-------|--------------|-----------------|
| 0 | backend-supabase-agent | security-agent (review) |
| 1 | backend-data-layer-agent | qa-testing-agent (trigger tests) |
| 2 | backend-data-layer-agent | qa-testing-agent (engine tests) |
| 3 | backend-data-layer-agent | backend-supabase-agent (type conversions) |
| 4 | backend-data-layer-agent | qa-testing-agent (photo lifecycle tests) |
| 5 | backend-data-layer-agent | qa-testing-agent (integrity tests) |
| 6 | frontend-flutter-specialist-agent | code-review-agent (settings cleanup) |
| 7 | backend-data-layer-agent | code-review-agent (full review) |

---

# Appendix C: Success Criteria

(Copied from original plan for reference)

1. **Stage trace scorecard**: 16 tables x 6 stages = 96/96 OK
2. **Zero sync gaps**: All 30 documented gaps resolved
3. **PRD alignment**: created_by_user_id stamped, sync-on-save works for ALL tables, conflict visibility
4. **Settings clean**: No dead toggles, no stubs, no orphaned widgets, logical section ordering
5. **User transparency**: Sync failures visible via toast + dashboard, conflicts browsable
6. **Self-healing**: 4-hour integrity check with id_checksum catches and corrects drift automatically
7. **All tests pass**: Unit + integration + widget + stage trace
8. **Profile clean**: All profile data from user_profiles via AuthProvider; no prefs fallback; PII cleaned from SharedPreferences
9. **First-sync experience**: User selects projects; only chosen projects pulled; progress visible
