# Pattern: Database Schema

## How We Do It
Each logical group of tables has a schema class in `lib/core/database/schema/` with static `const String create*Table` SQL statements and a `static const List<String> indexes` list. Tables are created in `DatabaseService._onCreate()` and verified by `SchemaVerifier._columnTypes`. Triggers are registered via `SyncEngineTables.triggeredTables`. Schema changes touch 5+ files.

## Exemplars

### EntryExportTables (`lib/core/database/schema/entry_export_tables.dart`)
```dart
class EntryExportTables {
  static const String createEntryExportsTable = '''
    CREATE TABLE IF NOT EXISTS entry_exports (
      id TEXT PRIMARY KEY,
      entry_id TEXT,
      project_id TEXT NOT NULL,
      file_path TEXT,
      remote_path TEXT,
      filename TEXT NOT NULL,
      file_size_bytes INTEGER,
      exported_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (entry_id) REFERENCES daily_entries(id) ON DELETE CASCADE,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
  ''';

  static const List<String> indexes = [
    'CREATE INDEX IF NOT EXISTS idx_entry_exports_project ON entry_exports(project_id)',
    'CREATE INDEX IF NOT EXISTS idx_entry_exports_entry ON entry_exports(entry_id)',
    'CREATE INDEX IF NOT EXISTS idx_entry_exports_deleted_at ON entry_exports(deleted_at)',
  ];
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `_onCreate` | `database_service.dart:150` | `Future<void> _onCreate(Database db, int version)` | Executes all CREATE TABLE + triggers |
| `_createIndexes` | `database_service.dart:239` | `Future<void> _createIndexes(Database db)` | Executes all CREATE INDEX |
| `_onUpgrade` | `database_service.dart:326` | `Future<void> _onUpgrade(Database db, int oldVersion, int newVersion)` | Migration path |
| `triggersForTable` | `sync_engine_tables.dart:186` | `static List<String> triggersForTable(String tableName)` | Generate INSERT/UPDATE/DELETE triggers |

## 5-File Checklist for Schema Changes
1. `lib/core/database/schema/<new_tables>.dart` — CREATE TABLE + indexes
2. `lib/core/database/database_service.dart` — `_onCreate`, `_createIndexes`, `_onUpgrade`, version bump
3. `lib/core/database/schema_verifier.dart` — `_columnTypes` entries for new tables
4. `test/core/database/schema_verifier_test.dart` — assertions for new tables
5. `test/core/database/database_service_test.dart` — migration + creation tests
6. `lib/core/database/schema/sync_engine_tables.dart` — `triggeredTables` + `tablesWithDirectProjectId`

## Imports
```dart
// Schema files have no imports — pure static SQL strings
```
