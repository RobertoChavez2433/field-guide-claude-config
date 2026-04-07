# Pattern: Schema Table Definition

## How We Do It

Each schema table is a small class under `lib/core/database/schema/` that exposes a `tableName` constant, a `createXTable` const SQL string, and an `indexes` list of `CREATE INDEX IF NOT EXISTS` statements. Timestamp columns use `strftime('%Y-%m-%dT%H:%M:%f', 'now')` defaults. `deleted_at` is nullable TEXT for soft-delete. Every synced table also gets `change_log` triggers (gated by `sync_control.pulling='0'`) wired up inside `DatabaseService._onCreate` / `_onUpgrade`. `SchemaVerifier` holds the expected column list for startup drift detection.

Per CLAUDE.md "schema changes touch 5 files":
1. `database_service.dart` — version bump + `_onCreate` table creation + upgrade step + triggers
2. `schema/<table>_tables.dart` — new class file
3. `schema_verifier.dart` — register expected column set
4. Test helper `_createFullSchema` mirrors (in `test/features/projects/...` and `test/features/sync/...`)
5. Test fixtures if any (e.g. `test/helpers/sync/sync_test_data.dart`)

## Exemplar: `SupportTables` (schema/support_tables.dart)

```dart
class SupportTables {
  static const String tableName = 'support_tickets';

  static const String createSupportTicketsTable = '''
    CREATE TABLE IF NOT EXISTS support_tickets (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      subject TEXT,
      message TEXT NOT NULL,
      app_version TEXT NOT NULL,
      platform TEXT NOT NULL,
      log_file_path TEXT,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'resolved'))
    )
  ''';

  static const List<String> indexes = [
    'CREATE INDEX IF NOT EXISTS idx_support_tickets_user ON support_tickets(user_id)',
    'CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status)',
    'CREATE INDEX IF NOT EXISTS idx_support_tickets_updated_at ON support_tickets(updated_at)',
  ];
}
```

## 1126 Application

```dart
// lib/core/database/schema/signature_tables.dart
class SignatureTables {
  static const String auditLogTableName = 'signature_audit_log';
  static const String filesTableName = 'signature_files';

  static const String createSignatureAuditLogTable = '''
    CREATE TABLE IF NOT EXISTS signature_audit_log (
      id TEXT PRIMARY KEY,
      signed_record_type TEXT NOT NULL,
      signed_record_id TEXT NOT NULL,
      project_id TEXT NOT NULL,
      company_id TEXT NOT NULL,
      user_id TEXT NOT NULL,
      device_id TEXT NOT NULL,
      platform TEXT NOT NULL CHECK (platform IN ('android','ios','windows','macos','linux')),
      app_version TEXT NOT NULL,
      signed_at_utc TEXT NOT NULL,
      gps_lat REAL,
      gps_lng REAL,
      document_hash_sha256 TEXT NOT NULL,
      signature_file_id TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      deleted_at TEXT,
      FOREIGN KEY (signature_file_id) REFERENCES signature_files(id)
    )
  ''';

  static const String createSignatureFilesTable = '''
    CREATE TABLE IF NOT EXISTS signature_files (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      company_id TEXT NOT NULL,
      local_path TEXT NOT NULL,
      remote_path TEXT,
      mime_type TEXT NOT NULL DEFAULT 'image/png',
      file_size_bytes INTEGER NOT NULL,
      sha256 TEXT NOT NULL,
      created_by_user_id TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      deleted_at TEXT
    )
  ''';

  static const List<String> indexes = [
    'CREATE INDEX IF NOT EXISTS idx_sig_audit_project ON signature_audit_log(project_id)',
    'CREATE INDEX IF NOT EXISTS idx_sig_audit_record ON signature_audit_log(signed_record_type, signed_record_id)',
    'CREATE INDEX IF NOT EXISTS idx_sig_audit_deleted ON signature_audit_log(deleted_at)',
    'CREATE INDEX IF NOT EXISTS idx_sig_files_project ON signature_files(project_id)',
    'CREATE INDEX IF NOT EXISTS idx_sig_files_deleted ON signature_files(deleted_at)',
  ];
}
```

And the change_log triggers (gated — see `sync_engine_tables.dart` for the pattern):

```sql
CREATE TRIGGER IF NOT EXISTS trg_signature_audit_log_ins
AFTER INSERT ON signature_audit_log
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (id, table_name, record_id, operation, created_at)
  VALUES (hex(randomblob(16)), 'signature_audit_log', NEW.id, 'insert',
          strftime('%Y-%m-%dT%H:%M:%f','now'));
END;

-- plus UPDATE + soft-delete triggers, and same triple for signature_files
```

## Schema Version Bump

`DatabaseService` currently declares `version: 53` in two places (lines 69 and 110). Bump **both** to 54 and add a new branch in `_onUpgrade`:

```dart
if (oldVersion < 54) {
  await db.execute(SignatureTables.createSignatureFilesTable);
  await db.execute(SignatureTables.createSignatureAuditLogTable);
  for (final idx in SignatureTables.indexes) {
    await db.execute(idx);
  }
  // Triggers (6 total)
  for (final trigger in _signatureChangeLogTriggers) {
    await db.execute(trigger);
  }
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|---|---|---|---|
| `SchemaVerifier.verify(db)` | `schema_verifier.dart:506` | `static Future<SchemaReport> verify(Database db)` | Runs on startup — must know new columns |
| `SoftDeleteService.hardDeleteWithSync` | `soft_delete_service.dart:852` | `Future<void> hardDeleteWithSync(String tableName, String id)` | For test cleanup only; production uses soft-delete |

## Imports

```dart
// Schema class is pure Dart — no imports beyond sqflite's Database.
```
