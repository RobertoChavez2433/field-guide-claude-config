# MDOT 1126 Weekly SESC Report Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Add the MDOT 1126 Weekly SESC Report as a builtin form — with carry-forward, tri-state measures review, drawn signatures (reusable audit/file architecture), daily-entry attachment, weekly cadence reminders, and one-folder daily export.

**Spec:** `.claude/specs/2026-04-06-mdot-1126-weekly-sesc-spec.md`
**Tailor:** `.claude/tailor/2026-04-06-mdot-1126-weekly-sesc/`

**Architecture:** Layer 1126 on top of the existing builtin-form registry pipeline (0582B exemplar). Introduce a new `lib/features/signatures/` feature module with two synced tables (`signature_audit_log` standard adapter, `signature_files` file-backed adapter). Form flow is a guided screen backed by new domain use cases that reuse `InspectorFormProvider` for CRUD and a new `Mdot1126FormController` (ChangeNotifier) for wizard state. Weekly reminders are computed at read time — no new stored rows.

**Tech Stack:** Flutter 3.38.9, Dart 3.10.7, sqflite (SQLite v54), Supabase, `signature` package (canvas), `crypto` (SHA-256), Syncfusion PDF (via existing `FormPdfService`).

**Blast Radius:** 24 new files, 5 edits, ~18 new test files, 1 Supabase migration, 2 test-helper mirrors, 0 cleanup targets.

---

## Phase Overview

| # | Phase | Agent Focus | Depends on |
|---|---|---|---|
| 1 | Foundation: constants, asset, pubspec | code-fixer-agent | — |
| 2 | Database schema v54 + signature tables | code-fixer-agent | 1 |
| 3 | Signatures feature module | code-fixer-agent | 2 |
| 4 | Sync adapters + Supabase migration | code-fixer-agent | 3 |
| 5 | Forms domain use cases | code-fixer-agent | 3 |
| 6 | MDOT 1126 data layer (validator, PDF filler, registrations) | code-fixer-agent, pdf-agent | 5 |
| 7 | MDOT 1126 presentation layer | code-fixer-agent | 6 |
| 8 | Export bundling rewrite | code-fixer-agent | 6 |
| 9 | Reminder UI bindings (dashboard, entry, toolbox) | code-fixer-agent | 5 |
| 10 | Integration, lint gate, cleanup | code-fixer-agent | 1–9 |

---

## Phase 1: Foundation

### Sub-phase 1.1: Form type constants and asset

**Files:**
- Modify: `lib/features/forms/data/registries/form_type_constants.dart`
- Create: `assets/templates/forms/mdot_1126_form.pdf` (copy from `.claude/specs/assets/mdot-1126-weekly-sesc.pdf`)
- Modify: `pubspec.yaml`

**Agent**: `code-fixer-agent`

#### Step 1.1.1: Add MDOT 1126 constants

```dart
// lib/features/forms/data/registries/form_type_constants.dart

// ... existing 0582B constants ...

// FROM SPEC §2: Builtin form id, keyed through every registry.
const String kFormTypeMdot1126 = 'mdot_1126';

// NOTE: Matches 0582B filename convention `<id>_form.pdf`.
const String kFormTemplateMdot1126 = 'assets/templates/forms/mdot_1126_form.pdf';
```

#### Step 1.1.2: Copy PDF template into assets and commit it

Run: `pwsh -Command "Copy-Item '.claude/specs/assets/mdot-1126-weekly-sesc.pdf' 'assets/templates/forms/mdot_1126_form.pdf'"`

L3 / spec §10: After the copy, **`git add assets/templates/forms/mdot_1126_form.pdf`** in the same commit as this phase. The PowerShell command is one-shot — fresh clones must receive the asset from git, not by re-running the copy. Verify with `pwsh -Command "git ls-files assets/templates/forms/mdot_1126_form.pdf"` (must echo the path, not empty).

#### Step 1.1.3: Register asset + add dependencies in pubspec

```yaml
# pubspec.yaml
flutter:
  assets:
    - assets/templates/forms/mdot_0582b_form.pdf
    - assets/templates/forms/mdot_1126_form.pdf   # NEW

dependencies:
  signature: ^5.4.0        # NEW — drawn signature canvas
  # crypto: already present — verify with grep before editing
```

#### Step 1.1.4: Fetch packages

Run: `pwsh -Command "flutter pub get"`
Expected: success, no conflicts.

#### Step 1.1.5: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No issues.

---

## Phase 2: Database Schema v54 — Signature Tables

### Sub-phase 2.1: SignatureTables schema class

**Files:**
- Create: `lib/core/database/schema/signature_tables.dart`

**Agent**: `code-fixer-agent`

#### Step 2.1.1: Write the table definitions

```dart
// lib/core/database/schema/signature_tables.dart
//
// FROM SPEC §2, §10: Two reusable tables for signed record auditing.
// NOTE: Pattern mirrors lib/core/database/schema/support_tables.dart.

class SignatureTables {
  static const String auditLogTableName = 'signature_audit_log';
  static const String filesTableName = 'signature_files';

  // WHY: `signature_files` must be created first — audit log references it.
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

  static const String createSignatureAuditLogTable = '''
    CREATE TABLE IF NOT EXISTS signature_audit_log (
      id TEXT PRIMARY KEY,
      signed_record_type TEXT NOT NULL,
      signed_record_id TEXT NOT NULL,
      project_id TEXT NOT NULL,
      company_id TEXT NOT NULL,
      user_id TEXT NOT NULL,
      device_id TEXT NOT NULL,
      platform TEXT NOT NULL CHECK (platform IN ('android','ios','windows')),
      app_version TEXT NOT NULL,
      signed_at_utc TEXT NOT NULL,
      gps_lat REAL,
      gps_lng REAL,
      document_hash_sha256 TEXT NOT NULL,
      signature_png_sha256 TEXT NOT NULL,
      signature_file_id TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      deleted_at TEXT,
      FOREIGN KEY (signature_file_id) REFERENCES signature_files(id) ON DELETE RESTRICT
    )
  ''';

  // SEC-1126-03: SQLite mirror of the Postgres immutability trigger.
  // Blocks any UPDATE that touches columns other than deleted_at, updated_at,
  // or remote_path. Mirrors the BEFORE UPDATE trigger added in
  // 20260408000000_signature_tables.sql so local edits cannot tamper with
  // signed records before they propagate.
  static const String createSignatureAuditImmutabilityTrigger = '''
    CREATE TRIGGER IF NOT EXISTS trg_signature_audit_log_immutable
    BEFORE UPDATE ON signature_audit_log
    FOR EACH ROW
    WHEN (
      NEW.id != OLD.id OR
      NEW.signed_record_type != OLD.signed_record_type OR
      NEW.signed_record_id != OLD.signed_record_id OR
      NEW.project_id != OLD.project_id OR
      NEW.company_id != OLD.company_id OR
      NEW.user_id != OLD.user_id OR
      NEW.device_id != OLD.device_id OR
      NEW.platform != OLD.platform OR
      NEW.app_version != OLD.app_version OR
      NEW.signed_at_utc != OLD.signed_at_utc OR
      IFNULL(NEW.gps_lat,0) != IFNULL(OLD.gps_lat,0) OR
      IFNULL(NEW.gps_lng,0) != IFNULL(OLD.gps_lng,0) OR
      NEW.document_hash_sha256 != OLD.document_hash_sha256 OR
      NEW.signature_png_sha256 != OLD.signature_png_sha256 OR
      NEW.signature_file_id != OLD.signature_file_id OR
      NEW.created_at != OLD.created_at
    )
    BEGIN
      SELECT RAISE(ABORT, 'signature_audit_log is immutable except for deleted_at/updated_at/remote_path');
    END;
  ''';

  static const String createSignatureFileImmutabilityTrigger = '''
    CREATE TRIGGER IF NOT EXISTS trg_signature_files_immutable
    BEFORE UPDATE ON signature_files
    FOR EACH ROW
    WHEN (
      NEW.id != OLD.id OR
      NEW.project_id != OLD.project_id OR
      NEW.company_id != OLD.company_id OR
      NEW.mime_type != OLD.mime_type OR
      NEW.file_size_bytes != OLD.file_size_bytes OR
      NEW.sha256 != OLD.sha256 OR
      NEW.created_by_user_id != OLD.created_by_user_id OR
      NEW.created_at != OLD.created_at
    )
    BEGIN
      SELECT RAISE(ABORT, 'signature_files is immutable except for deleted_at/updated_at/remote_path/local_path');
    END;
  ''';

  static const List<String> indexes = [
    'CREATE INDEX IF NOT EXISTS idx_sig_audit_project ON signature_audit_log(project_id)',
    'CREATE INDEX IF NOT EXISTS idx_sig_audit_record ON signature_audit_log(signed_record_type, signed_record_id)',
    'CREATE INDEX IF NOT EXISTS idx_sig_audit_deleted ON signature_audit_log(deleted_at)',
    'CREATE INDEX IF NOT EXISTS idx_sig_files_project ON signature_files(project_id)',
    'CREATE INDEX IF NOT EXISTS idx_sig_files_deleted ON signature_files(deleted_at)',
  ];

  // WHY: change_log triggers gated by sync_control.pulling='0' to avoid
  // re-emitting pulls as pushes. Matches the pattern every other synced
  // table uses in `sync_engine_tables.dart`.
  static const List<String> triggers = [
    // --- signature_files ---
    '''
    CREATE TRIGGER IF NOT EXISTS trg_signature_files_ins
    AFTER INSERT ON signature_files
    WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
    BEGIN
      INSERT INTO change_log (id, table_name, record_id, operation, created_at)
      VALUES (hex(randomblob(16)), 'signature_files', NEW.id, 'insert',
              strftime('%Y-%m-%dT%H:%M:%f','now'));
    END;
    ''',
    '''
    CREATE TRIGGER IF NOT EXISTS trg_signature_files_upd
    AFTER UPDATE ON signature_files
    WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
    BEGIN
      INSERT INTO change_log (id, table_name, record_id, operation, created_at)
      VALUES (hex(randomblob(16)), 'signature_files', NEW.id,
              CASE WHEN NEW.deleted_at IS NOT NULL THEN 'delete' ELSE 'update' END,
              strftime('%Y-%m-%dT%H:%M:%f','now'));
    END;
    ''',

    // --- signature_audit_log ---
    '''
    CREATE TRIGGER IF NOT EXISTS trg_signature_audit_log_ins
    AFTER INSERT ON signature_audit_log
    WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
    BEGIN
      INSERT INTO change_log (id, table_name, record_id, operation, created_at)
      VALUES (hex(randomblob(16)), 'signature_audit_log', NEW.id, 'insert',
              strftime('%Y-%m-%dT%H:%M:%f','now'));
    END;
    ''',
    '''
    CREATE TRIGGER IF NOT EXISTS trg_signature_audit_log_upd
    AFTER UPDATE ON signature_audit_log
    WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
    BEGIN
      INSERT INTO change_log (id, table_name, record_id, operation, created_at)
      VALUES (hex(randomblob(16)), 'signature_audit_log', NEW.id,
              CASE WHEN NEW.deleted_at IS NOT NULL THEN 'delete' ELSE 'update' END,
              strftime('%Y-%m-%dT%H:%M:%f','now'));
    END;
    ''',
  ];

  // SEC-1126-03: Immutability triggers must be installed alongside the
  // standard change_log triggers. Listed separately so callers can install
  // them in the correct order (after CREATE TABLE, before any INSERT).
  static const List<String> immutabilityTriggers = [
    createSignatureFileImmutabilityTrigger,
    createSignatureAuditImmutabilityTrigger,
  ];
}
```

### Sub-phase 2.2: Wire schema into DatabaseService

**Files:**
- Modify: `lib/core/database/database_service.dart:69` and `:110` (version bump) + `_onCreate` and `_onUpgrade`

**Agent**: `code-fixer-agent`

#### Step 2.2.1: Bump schema version 53 → 54

```dart
// lib/core/database/database_service.dart (both occurrences at :69 and :110)
// FROM SPEC §10 + tailor ground-truth FLAG: current is 53, not 52, not 53 new.
version: 54,
```

#### Step 2.2.2: Add table creation to `_onCreate`

```dart
// Inside _onCreate(Database db, int version) in the builtin table creation block:
// NOTE: signature_files MUST precede signature_audit_log — FK dependency.
await db.execute(SignatureTables.createSignatureFilesTable);
await db.execute(SignatureTables.createSignatureAuditLogTable);
for (final idx in SignatureTables.indexes) {
  await db.execute(idx);
}
for (final trigger in SignatureTables.triggers) {
  await db.execute(trigger);
}
for (final trigger in SignatureTables.immutabilityTriggers) {
  await db.execute(trigger);
}
```

#### Step 2.2.3: Add `_onUpgrade` branch 53→54

```dart
// FROM SPEC §10: new tables arrive at schema v54.
if (oldVersion < 54) {
  await db.execute(SignatureTables.createSignatureFilesTable);
  await db.execute(SignatureTables.createSignatureAuditLogTable);
  for (final idx in SignatureTables.indexes) {
    await db.execute(idx);
  }
  for (final trigger in SignatureTables.triggers) {
    await db.execute(trigger);
  }
  for (final trigger in SignatureTables.immutabilityTriggers) {
    await db.execute(trigger);
  }
}
```

#### Step 2.2.4: Add import for SignatureTables

```dart
import 'schema/signature_tables.dart';
```

#### Step 2.2.5: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No issues.

### Sub-phase 2.3: Schema verifier coverage

**Files:**
- Modify: `lib/core/database/schema_verifier.dart`

**Agent**: `code-fixer-agent`

#### Step 2.3.1: Register expected column set for both tables

```dart
// In SchemaVerifier's expectedSchema (Map<String, List<String>>) add the
// new tables as column-name lists. Non-TEXT columns go in the separate
// _columnTypes map.
// WHY: Startup drift detection — any missing column aborts sync setup.

// expectedSchema additions:
'signature_files': [
  'id', 'project_id', 'company_id', 'local_path', 'remote_path',
  'mime_type', 'file_size_bytes', 'sha256', 'created_by_user_id',
  'created_at', 'updated_at', 'deleted_at',
],
'signature_audit_log': [
  'id', 'signed_record_type', 'signed_record_id', 'project_id',
  'company_id', 'user_id', 'device_id', 'platform', 'app_version',
  'signed_at_utc', 'gps_lat', 'gps_lng', 'document_hash_sha256',
  'signature_png_sha256', 'signature_file_id',
  'created_at', 'updated_at', 'deleted_at',
],

// _columnTypes additions (only non-TEXT columns):
'signature_files': {
  'file_size_bytes': 'INTEGER NOT NULL',
},
'signature_audit_log': {
  'gps_lat': 'REAL',
  'gps_lng': 'REAL',
},
```

### Sub-phase 2.4: Mirror schema in test helpers

**Files:**
- Modify: `test/features/projects/integration/project_lifecycle_integration_test.dart` — `_createFullSchema` helper
- Modify: `test/features/sync/engine/scope_revocation_cleaner_test.dart` — `_createFullSchema` helper
- Modify: `test/helpers/sync/sync_test_data.dart` — schema bootstrap helper (5th file per CLAUDE.md "schema changes touch 5 files" rule)

**Agent**: `qa-testing-agent`

#### Step 2.4.1: Add signature table creates + triggers to all three helper copies

All three helpers build a complete test DB. Append to the execution block:

```dart
await db.execute(SignatureTables.createSignatureFilesTable);
await db.execute(SignatureTables.createSignatureAuditLogTable);
for (final idx in SignatureTables.indexes) await db.execute(idx);
for (final trigger in SignatureTables.triggers) await db.execute(trigger);
for (final trigger in SignatureTables.immutabilityTriggers) {
  await db.execute(trigger);
}
```

Plus the import:

```dart
import 'package:construction_inspector/core/database/schema/signature_tables.dart';
```

#### Step 2.4.2: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No issues.

---

## Phase 3: Signatures Feature Module

### Sub-phase 3.1: Domain models

**Files:**
- Create: `lib/features/signatures/data/models/signature_file.dart`
- Create: `lib/features/signatures/data/models/signature_audit_log.dart`

**Agent**: `code-fixer-agent`

#### Step 3.1.1: SignatureFile model

```dart
// lib/features/signatures/data/models/signature_file.dart
import 'package:meta/meta.dart';
import 'package:uuid/uuid.dart';

@immutable
class SignatureFile {
  final String id;
  final String projectId;
  final String companyId;
  final String localPath;
  final String? remotePath;
  final String mimeType;
  final int fileSizeBytes;
  final String sha256;
  final String createdByUserId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;

  SignatureFile({
    String? id,
    required this.projectId,
    required this.companyId,
    required this.localPath,
    this.remotePath,
    this.mimeType = 'image/png',
    required this.fileSizeBytes,
    required this.sha256,
    required this.createdByUserId,
    DateTime? createdAt,
    DateTime? updatedAt,
    this.deletedAt,
  })  : id = id ?? const Uuid().v4(),
        createdAt = createdAt ?? DateTime.now().toUtc(),
        updatedAt = updatedAt ?? DateTime.now().toUtc();

  Map<String, dynamic> toMap() => {
        'id': id,
        'project_id': projectId,
        'company_id': companyId,
        'local_path': localPath,
        'remote_path': remotePath,
        'mime_type': mimeType,
        'file_size_bytes': fileSizeBytes,
        'sha256': sha256,
        'created_by_user_id': createdByUserId,
        'created_at': createdAt.toIso8601String(),
        'updated_at': updatedAt.toIso8601String(),
        'deleted_at': deletedAt?.toIso8601String(),
      };

  factory SignatureFile.fromMap(Map<String, dynamic> map) => SignatureFile(
        id: map['id'] as String,
        projectId: map['project_id'] as String,
        companyId: map['company_id'] as String,
        localPath: map['local_path'] as String,
        remotePath: map['remote_path'] as String?,
        mimeType: (map['mime_type'] as String?) ?? 'image/png',
        fileSizeBytes: (map['file_size_bytes'] as num).toInt(),
        sha256: map['sha256'] as String,
        createdByUserId: map['created_by_user_id'] as String,
        createdAt: DateTime.parse(map['created_at'] as String),
        updatedAt: DateTime.parse(map['updated_at'] as String),
        deletedAt: map['deleted_at'] != null
            ? DateTime.parse(map['deleted_at'] as String)
            : null,
      );
}
```

#### Step 3.1.2: SignatureAuditLog model

```dart
// lib/features/signatures/data/models/signature_audit_log.dart
import 'package:meta/meta.dart';
import 'package:uuid/uuid.dart';

@immutable
class SignatureAuditLog {
  final String id;
  final String signedRecordType;   // 'form_response' for 1126
  final String signedRecordId;
  final String projectId;
  final String companyId;
  final String userId;
  final String deviceId;
  final String platform;
  final String appVersion;
  final DateTime signedAtUtc;
  final double? gpsLat;
  final double? gpsLng;
  final String documentHashSha256;
  final String signaturePngSha256;
  final String signatureFileId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;

  SignatureAuditLog({
    String? id,
    required this.signedRecordType,
    required this.signedRecordId,
    required this.projectId,
    required this.companyId,
    required this.userId,
    required this.deviceId,
    required this.platform,
    required this.appVersion,
    required this.signedAtUtc,
    this.gpsLat,
    this.gpsLng,
    required this.documentHashSha256,
    required this.signaturePngSha256,
    required this.signatureFileId,
    DateTime? createdAt,
    DateTime? updatedAt,
    this.deletedAt,
  })  : id = id ?? const Uuid().v4(),
        createdAt = createdAt ?? DateTime.now().toUtc(),
        updatedAt = updatedAt ?? DateTime.now().toUtc();

  Map<String, dynamic> toMap() => {
        'id': id,
        'signed_record_type': signedRecordType,
        'signed_record_id': signedRecordId,
        'project_id': projectId,
        'company_id': companyId,
        'user_id': userId,
        'device_id': deviceId,
        'platform': platform,
        'app_version': appVersion,
        'signed_at_utc': signedAtUtc.toIso8601String(),
        'gps_lat': gpsLat,
        'gps_lng': gpsLng,
        'document_hash_sha256': documentHashSha256,
        'signature_png_sha256': signaturePngSha256,
        'signature_file_id': signatureFileId,
        'created_at': createdAt.toIso8601String(),
        'updated_at': updatedAt.toIso8601String(),
        'deleted_at': deletedAt?.toIso8601String(),
      };

  factory SignatureAuditLog.fromMap(Map<String, dynamic> map) => SignatureAuditLog(
        id: map['id'] as String,
        signedRecordType: map['signed_record_type'] as String,
        signedRecordId: map['signed_record_id'] as String,
        projectId: map['project_id'] as String,
        companyId: map['company_id'] as String,
        userId: map['user_id'] as String,
        deviceId: map['device_id'] as String,
        platform: map['platform'] as String,
        appVersion: map['app_version'] as String,
        signedAtUtc: DateTime.parse(map['signed_at_utc'] as String),
        gpsLat: (map['gps_lat'] as num?)?.toDouble(),
        gpsLng: (map['gps_lng'] as num?)?.toDouble(),
        documentHashSha256: map['document_hash_sha256'] as String,
        signaturePngSha256: map['signature_png_sha256'] as String,
        signatureFileId: map['signature_file_id'] as String,
        createdAt: DateTime.parse(map['created_at'] as String),
        updatedAt: DateTime.parse(map['updated_at'] as String),
        deletedAt: map['deleted_at'] != null
            ? DateTime.parse(map['deleted_at'] as String)
            : null,
      );
}
```

### Sub-phase 3.2: Local datasources

**Files:**
- Create: `lib/features/signatures/data/datasources/local/signature_file_local_datasource.dart`
- Create: `lib/features/signatures/data/datasources/local/signature_audit_log_local_datasource.dart`

**Agent**: `code-fixer-agent`

#### Step 3.2.1: SignatureFile local datasource

```dart
// lib/features/signatures/data/datasources/local/signature_file_local_datasource.dart
import 'package:sqflite/sqflite.dart';
import 'package:construction_inspector/core/database/schema/signature_tables.dart';
import 'package:construction_inspector/features/signatures/data/models/signature_file.dart';

class SignatureFileLocalDatasource {
  final Database _db;
  SignatureFileLocalDatasource(this._db);

  static const _table = SignatureTables.filesTableName;

  Future<SignatureFile> create(SignatureFile file) async {
    await _db.insert(_table, file.toMap());
    return file;
  }

  Future<SignatureFile?> getById(String id) async {
    final rows = await _db.query(
      _table,
      where: 'id = ? AND deleted_at IS NULL',
      whereArgs: [id],
      limit: 1,
    );
    return rows.isEmpty ? null : SignatureFile.fromMap(rows.first);
  }

  Future<List<SignatureFile>> getByProject(String projectId) async {
    final rows = await _db.query(
      _table,
      where: 'project_id = ? AND deleted_at IS NULL',
      whereArgs: [projectId],
      orderBy: 'created_at DESC',
    );
    return rows.map(SignatureFile.fromMap).toList();
  }
}
```

#### Step 3.2.2: SignatureAuditLog local datasource

```dart
// lib/features/signatures/data/datasources/local/signature_audit_log_local_datasource.dart
import 'package:sqflite/sqflite.dart';
import 'package:construction_inspector/core/database/schema/signature_tables.dart';
import 'package:construction_inspector/features/signatures/data/models/signature_audit_log.dart';

class SignatureAuditLogLocalDatasource {
  final Database _db;
  SignatureAuditLogLocalDatasource(this._db);

  static const _table = SignatureTables.auditLogTableName;

  Future<SignatureAuditLog> create(SignatureAuditLog audit) async {
    await _db.insert(_table, audit.toMap());
    return audit;
  }

  Future<SignatureAuditLog?> getById(String id) async {
    final rows = await _db.query(
      _table,
      where: 'id = ? AND deleted_at IS NULL',
      whereArgs: [id],
      limit: 1,
    );
    return rows.isEmpty ? null : SignatureAuditLog.fromMap(rows.first);
  }

  Future<List<SignatureAuditLog>> getByRecord(
    String signedRecordType,
    String signedRecordId,
  ) async {
    final rows = await _db.query(
      _table,
      where:
          'signed_record_type = ? AND signed_record_id = ? AND deleted_at IS NULL',
      whereArgs: [signedRecordType, signedRecordId],
      orderBy: 'signed_at_utc DESC',
    );
    return rows.map(SignatureAuditLog.fromMap).toList();
  }
}
```

### Sub-phase 3.3: Repositories

**Files:**
- Create: `lib/features/signatures/domain/repositories/signature_file_repository.dart`
- Create: `lib/features/signatures/domain/repositories/signature_audit_log_repository.dart`
- Create: `lib/features/signatures/data/repositories/signature_file_repository_impl.dart`
- Create: `lib/features/signatures/data/repositories/signature_audit_log_repository_impl.dart`

**Agent**: `code-fixer-agent`

#### Step 3.3.1: Abstract interfaces

```dart
// lib/features/signatures/domain/repositories/signature_file_repository.dart
import 'package:construction_inspector/features/signatures/data/models/signature_file.dart';

abstract class SignatureFileRepository {
  Future<SignatureFile> create(SignatureFile file);
  Future<SignatureFile?> getById(String id);
  Future<List<SignatureFile>> getByProject(String projectId);
}
```

```dart
// lib/features/signatures/domain/repositories/signature_audit_log_repository.dart
import 'package:construction_inspector/features/signatures/data/models/signature_audit_log.dart';

abstract class SignatureAuditLogRepository {
  Future<SignatureAuditLog> create(SignatureAuditLog audit);
  Future<SignatureAuditLog?> getById(String id);
  Future<List<SignatureAuditLog>> getByRecord(
    String signedRecordType,
    String signedRecordId,
  );
}
```

#### Step 3.3.2: Repository impls

```dart
// lib/features/signatures/data/repositories/signature_file_repository_impl.dart
import '../datasources/local/signature_file_local_datasource.dart';
import '../models/signature_file.dart';
import '../../domain/repositories/signature_file_repository.dart';

class SignatureFileRepositoryImpl implements SignatureFileRepository {
  final SignatureFileLocalDatasource _local;
  SignatureFileRepositoryImpl(this._local);

  @override
  Future<SignatureFile> create(SignatureFile file) => _local.create(file);

  @override
  Future<SignatureFile?> getById(String id) => _local.getById(id);

  @override
  Future<List<SignatureFile>> getByProject(String projectId) =>
      _local.getByProject(projectId);
}
```

```dart
// lib/features/signatures/data/repositories/signature_audit_log_repository_impl.dart
import '../datasources/local/signature_audit_log_local_datasource.dart';
import '../models/signature_audit_log.dart';
import '../../domain/repositories/signature_audit_log_repository.dart';

class SignatureAuditLogRepositoryImpl implements SignatureAuditLogRepository {
  final SignatureAuditLogLocalDatasource _local;
  SignatureAuditLogRepositoryImpl(this._local);

  @override
  Future<SignatureAuditLog> create(SignatureAuditLog audit) => _local.create(audit);

  @override
  Future<SignatureAuditLog?> getById(String id) => _local.getById(id);

  @override
  Future<List<SignatureAuditLog>> getByRecord(
    String signedRecordType,
    String signedRecordId,
  ) =>
      _local.getByRecord(signedRecordType, signedRecordId);
}
```

### Sub-phase 3.4: DI wiring

**Files:**
- Modify: `lib/core/di/` (follow existing pattern — locate the tier where `InspectorFormRepositoryImpl` is constructed and add Signature repositories alongside)

**Agent**: `code-fixer-agent`

#### Step 3.4.1: Wire datasource → repo in AppInitializer typed deps

Follow the `Tier 1-2` container pattern referenced in CLAUDE.md. Add a `SignaturesDeps` record or extend an existing deps container to hold the two repositories, constructed once from the Database instance.

#### Step 3.4.2: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No issues.

---

## Phase 4: Sync Adapters & Supabase Migration

### Sub-phase 4.1: Add AdapterConfig entries

**Files:**
- Modify: `lib/features/sync/adapters/simple_adapters.dart`

**Agent**: `code-fixer-agent`

#### Step 4.1.1: Add two entries + path builder

```dart
// Append to `simpleAdapters = <AdapterConfig>[ ... ]`

// WHY: signature_files must precede signature_audit_log — FK ordering.
AdapterConfig(
  table: 'signature_files',
  scope: ScopeType.viaProject,
  fkDeps: ['projects'],
  fkColumnMap: {'projects': 'project_id'},
  localOnlyColumns: ['local_path'],
  isFileAdapter: true,
  storageBucket: 'signatures',
  localFilePathColumn: 'local_path',
  stripExifGps: false,   // No EXIF stripping required for signature PNGs.
  buildStoragePath: _buildSignatureFilePath,
),

AdapterConfig(
  table: 'signature_audit_log',
  scope: ScopeType.viaProject,
  fkDeps: ['projects', 'signature_files'],
  fkColumnMap: {
    'projects': 'project_id',
    'signature_files': 'signature_file_id',
  },
),
```

Add the private path builder at the bottom of the file (alongside `_buildFormExportPath`):

```dart
// SEC-1126-02: Path MUST start with the literal bucket prefix 'signatures/'
// because all storage.objects RLS policies index `(storage.foldername(name))[2]`
// to extract the company id (the [1] slot is the bucket prefix). See
// 20260328100000_fix_inspector_forms_and_new_tables.sql for the canonical
// pattern shared by inspector_forms / form-exports / entry-exports.
String _buildSignatureFilePath(String companyId, Map<String, dynamic> record) {
  final projectId = record['project_id'] as String? ?? 'unlinked';
  final id = record['id'] as String? ?? 'unknown';
  return 'signatures/$companyId/$projectId/$id.png';
}
```

### Sub-phase 4.2: Adapter registry tests

**Files:**
- Modify: `test/features/sync/adapters/adapter_config_test.dart`

**Agent**: `qa-testing-agent`

#### Step 4.2.1: Assert both new tables are registered

Add expectations that the `simpleAdapters` list contains configs for `signature_files` (file-backed, bucket=`signatures`) and `signature_audit_log` (standard, scope=`viaProject`, fkDeps includes `signature_files`).

### Sub-phase 4.3: Supabase migration

**Files:**
- Create: `supabase/migrations/20260408000000_signature_tables.sql`

**Agent**: `code-fixer-agent`

#### Step 4.3.1: Tables + RLS + Realtime + Storage bucket

```sql
-- supabase/migrations/20260408000000_signature_tables.sql
-- FROM SPEC §2, §9: signature audit/file tables, RLS, realtime, storage bucket.
-- SEC-1126-01..06: Uses get_my_company_id() / is_viewer() helpers from
-- 20260222100000_multi_tenant_foundation.sql. Per-operation policies derive
-- scope from JWT (project membership), never from row company_id.

CREATE TABLE IF NOT EXISTS public.signature_files (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  company_id TEXT NOT NULL,
  local_path TEXT,
  remote_path TEXT,
  mime_type TEXT NOT NULL DEFAULT 'image/png',
  file_size_bytes INTEGER NOT NULL,
  sha256 TEXT NOT NULL,
  created_by_user_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS public.signature_audit_log (
  id TEXT PRIMARY KEY,
  signed_record_type TEXT NOT NULL,
  signed_record_id TEXT NOT NULL,
  project_id TEXT NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  company_id TEXT NOT NULL,
  user_id UUID NOT NULL,
  device_id TEXT NOT NULL,
  -- SEC-1126-L1: Tightened to spec-allowed platforms only.
  platform TEXT NOT NULL CHECK (platform IN ('android','ios','windows')),
  app_version TEXT NOT NULL,
  signed_at_utc TIMESTAMPTZ NOT NULL,
  gps_lat DOUBLE PRECISION,
  gps_lng DOUBLE PRECISION,
  document_hash_sha256 TEXT NOT NULL,
  -- SEC-1126-03: PNG hash captured at sign time so the audit row binds the
  -- exact rendered signature image, independent of the mutable signature_files row.
  signature_png_sha256 TEXT NOT NULL,
  signature_file_id TEXT NOT NULL REFERENCES public.signature_files(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sig_files_project ON public.signature_files(project_id);
CREATE INDEX IF NOT EXISTS idx_sig_audit_project ON public.signature_audit_log(project_id);
CREATE INDEX IF NOT EXISTS idx_sig_audit_record
  ON public.signature_audit_log(signed_record_type, signed_record_id);

-- =====================================================================
-- SEC-1126-04: BEFORE INSERT triggers force company_id / user_id from the
-- JWT session, never trusting client-supplied values.
-- =====================================================================
CREATE OR REPLACE FUNCTION public.signature_files_set_owner()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  NEW.company_id := get_my_company_id();
  NEW.created_by_user_id := auth.uid();
  RETURN NEW;
END $$;

CREATE TRIGGER trg_signature_files_set_owner
  BEFORE INSERT ON public.signature_files
  FOR EACH ROW EXECUTE FUNCTION public.signature_files_set_owner();

CREATE OR REPLACE FUNCTION public.signature_audit_log_set_owner()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  NEW.company_id := get_my_company_id();
  NEW.user_id := auth.uid();
  RETURN NEW;
END $$;

CREATE TRIGGER trg_signature_audit_log_set_owner
  BEFORE INSERT ON public.signature_audit_log
  FOR EACH ROW EXECUTE FUNCTION public.signature_audit_log_set_owner();

-- =====================================================================
-- SEC-1126-03: BEFORE UPDATE triggers enforce immutability. Only
-- deleted_at, updated_at, and remote_path may change after the initial INSERT.
-- =====================================================================
CREATE OR REPLACE FUNCTION public.signature_files_block_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.id IS DISTINCT FROM OLD.id
     OR NEW.project_id IS DISTINCT FROM OLD.project_id
     OR NEW.company_id IS DISTINCT FROM OLD.company_id
     OR NEW.mime_type IS DISTINCT FROM OLD.mime_type
     OR NEW.file_size_bytes IS DISTINCT FROM OLD.file_size_bytes
     OR NEW.sha256 IS DISTINCT FROM OLD.sha256
     OR NEW.created_by_user_id IS DISTINCT FROM OLD.created_by_user_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at
  THEN
    RAISE EXCEPTION 'signature_files is immutable except for deleted_at/updated_at/remote_path/local_path';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER trg_signature_files_block_mutation
  BEFORE UPDATE ON public.signature_files
  FOR EACH ROW EXECUTE FUNCTION public.signature_files_block_mutation();

CREATE OR REPLACE FUNCTION public.signature_audit_log_block_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.id IS DISTINCT FROM OLD.id
     OR NEW.signed_record_type IS DISTINCT FROM OLD.signed_record_type
     OR NEW.signed_record_id IS DISTINCT FROM OLD.signed_record_id
     OR NEW.project_id IS DISTINCT FROM OLD.project_id
     OR NEW.company_id IS DISTINCT FROM OLD.company_id
     OR NEW.user_id IS DISTINCT FROM OLD.user_id
     OR NEW.device_id IS DISTINCT FROM OLD.device_id
     OR NEW.platform IS DISTINCT FROM OLD.platform
     OR NEW.app_version IS DISTINCT FROM OLD.app_version
     OR NEW.signed_at_utc IS DISTINCT FROM OLD.signed_at_utc
     OR NEW.gps_lat IS DISTINCT FROM OLD.gps_lat
     OR NEW.gps_lng IS DISTINCT FROM OLD.gps_lng
     OR NEW.document_hash_sha256 IS DISTINCT FROM OLD.document_hash_sha256
     OR NEW.signature_png_sha256 IS DISTINCT FROM OLD.signature_png_sha256
     OR NEW.signature_file_id IS DISTINCT FROM OLD.signature_file_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at
  THEN
    RAISE EXCEPTION 'signature_audit_log is immutable except for deleted_at/updated_at/remote_path';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER trg_signature_audit_log_block_mutation
  BEFORE UPDATE ON public.signature_audit_log
  FOR EACH ROW EXECUTE FUNCTION public.signature_audit_log_block_mutation();

-- =====================================================================
-- RLS — split per operation, scope derived from project membership in JWT.
-- SEC-1126-01: NEVER reference row company_id directly; derive scope from
-- the projects table filtered by get_my_company_id(). NOT is_viewer() guards
-- writes per the canonical pattern in 20260222100000.
-- =====================================================================
ALTER TABLE public.signature_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signature_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY signature_files_select ON public.signature_files
  FOR SELECT USING (
    project_id IN (SELECT id FROM public.projects WHERE company_id = get_my_company_id())
  );
CREATE POLICY signature_files_insert ON public.signature_files
  FOR INSERT WITH CHECK (
    project_id IN (SELECT id FROM public.projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  );
CREATE POLICY signature_files_update ON public.signature_files
  FOR UPDATE USING (
    project_id IN (SELECT id FROM public.projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  ) WITH CHECK (
    project_id IN (SELECT id FROM public.projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  );
CREATE POLICY signature_files_delete ON public.signature_files
  FOR DELETE USING (
    project_id IN (SELECT id FROM public.projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  );

CREATE POLICY signature_audit_log_select ON public.signature_audit_log
  FOR SELECT USING (
    project_id IN (SELECT id FROM public.projects WHERE company_id = get_my_company_id())
  );
CREATE POLICY signature_audit_log_insert ON public.signature_audit_log
  FOR INSERT WITH CHECK (
    project_id IN (SELECT id FROM public.projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  );
CREATE POLICY signature_audit_log_update ON public.signature_audit_log
  FOR UPDATE USING (
    project_id IN (SELECT id FROM public.projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  ) WITH CHECK (
    project_id IN (SELECT id FROM public.projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  );
CREATE POLICY signature_audit_log_delete ON public.signature_audit_log
  FOR DELETE USING (
    project_id IN (SELECT id FROM public.projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  );

-- =====================================================================
-- SEC-1126-12: Realtime publication. signature_audit_log is intentionally
-- NOT broadcast — gps_lat/gps_lng/device_id/user_id are PII and must only
-- be fetched on demand. signature_files stays in publication so the
-- existing sync-hint pipeline can refresh local PNG paths.
-- =====================================================================
ALTER PUBLICATION supabase_realtime ADD TABLE public.signature_files;

-- =====================================================================
-- SEC-1126-11: Storage bucket with quota and MIME limits. SEC-1126-02:
-- foldername index [2] matches the literal-bucket-prefix path convention
-- shared by inspector_forms / form-exports.
-- =====================================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('signatures', 'signatures', false, 524288, ARRAY['image/png'])
ON CONFLICT (id) DO UPDATE
  SET file_size_limit = EXCLUDED.file_size_limit,
      allowed_mime_types = EXCLUDED.allowed_mime_types;

CREATE POLICY signatures_bucket_select
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'signatures'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
  );

CREATE POLICY signatures_bucket_insert
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'signatures'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
    AND NOT is_viewer()
  );

CREATE POLICY signatures_bucket_update
  ON storage.objects FOR UPDATE
  USING (
    bucket_id = 'signatures'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
    AND NOT is_viewer()
  )
  WITH CHECK (
    bucket_id = 'signatures'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
    AND NOT is_viewer()
  );

CREATE POLICY signatures_bucket_delete
  ON storage.objects FOR DELETE
  USING (
    bucket_id = 'signatures'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
    AND NOT is_viewer()
  );

-- =====================================================================
-- H6 / inspector_form server seed for mdot_1126.
-- FROM SPEC §2: builtin form row, is_builtin=1, idempotent ON CONFLICT.
-- Mirror the column set used by the existing inspector_forms schema.
-- =====================================================================
INSERT INTO public.inspector_forms (
  id, project_id, name, template_path, is_builtin, created_at, updated_at
) VALUES (
  'mdot_1126', NULL, 'MDOT 1126 Weekly SESC',
  'assets/templates/forms/mdot_1126_form.pdf', true, now(), now()
) ON CONFLICT (id) DO NOTHING;
```

> **NOTE**: All helper names (`get_my_company_id`, `is_viewer`, `(storage.foldername(name))[2]`, `inspector_forms` columns) are verified against `20260222100000_multi_tenant_foundation.sql` and `20260328100000_fix_inspector_forms_and_new_tables.sql`. The `signature_audit_log` PNG hash and immutability triggers are SEC-1126-03 fixes — do not weaken.

#### Step 4.3.2: Verify migration applies cleanly (staging only)

Run: `pwsh -Command "npx supabase db push --dry-run"`
Expected: migration file listed, no syntax errors.

---

## Phase 5: Forms Domain Use Cases

### Sub-phase 5.1: Repository query extension

**Files:**
- Modify: `lib/features/forms/domain/repositories/form_response_repository.dart`
- Modify: `lib/features/forms/data/repositories/form_response_repository.dart` (impl)
- Modify: `lib/features/forms/data/datasources/local/form_response_local_datasource.dart`

**Agent**: `code-fixer-agent`

#### Step 5.1.1: Add `getByFormTypeForProject` to abstract repo

```dart
// lib/features/forms/domain/repositories/form_response_repository.dart

/// FROM SPEC §5: Needed by LoadPrior1126UseCase and
/// ComputeWeeklySescReminderUseCase to list 1126 responses chronologically.
Future<RepositoryResult<List<FormResponse>>> getByFormTypeForProject({
  required String projectId,
  required String formType,
  bool descending = true,
  int? limit,
});
```

#### Step 5.1.2: Impl — delegate to datasource

```dart
@override
Future<RepositoryResult<List<FormResponse>>> getByFormTypeForProject({
  required String projectId,
  required String formType,
  bool descending = true,
  int? limit,
}) async {
  try {
    final rows = await _local.getByFormTypeForProject(
      projectId: projectId,
      formType: formType,
      descending: descending,
      limit: limit,
    );
    return RepositoryResult.success(rows);
  } catch (e, st) {
    return RepositoryResult.failure('getByFormTypeForProject failed: $e\n$st');
  }
}
```

#### Step 5.1.3: Datasource SQL

```dart
// lib/features/forms/data/datasources/local/form_response_local_datasource.dart

Future<List<FormResponse>> getByFormTypeForProject({
  required String projectId,
  required String formType,
  bool descending = true,
  int? limit,
}) async {
  // WHY: Sort by json_extract(response_data,'$.inspection_date') so that
  // 1126 responses order by inspection_date (not created_at).
  final order = descending ? 'DESC' : 'ASC';
  final sql = '''
    SELECT * FROM form_responses
    WHERE project_id = ? AND form_type = ? AND deleted_at IS NULL
    ORDER BY json_extract(response_data, '\$.inspection_date') $order,
             created_at $order
    ${limit != null ? 'LIMIT ?' : ''}
  ''';
  final args = <Object?>[projectId, formType, if (limit != null) limit];
  final rows = await _db.rawQuery(sql, args);
  return rows.map(FormResponse.fromMap).toList();
}
```

### Sub-phase 5.2: LoadPrior1126UseCase + BuildCarryForward1126UseCase

**Files:**
- Create: `lib/features/forms/domain/usecases/load_prior_1126_use_case.dart`
- Create: `lib/features/forms/domain/usecases/build_carry_forward_1126_use_case.dart`

**Agent**: `code-fixer-agent`

#### Step 5.2.1: LoadPrior1126UseCase

```dart
// lib/features/forms/domain/usecases/load_prior_1126_use_case.dart
import '../../data/models/form_response.dart';
import '../../data/registries/form_type_constants.dart';
import '../repositories/form_response_repository.dart';

class LoadPrior1126UseCase {
  final FormResponseRepository _repo;
  LoadPrior1126UseCase(this._repo);

  /// Returns the most-recent SIGNED 1126 response for the project, or null.
  /// WHY: Carry-forward must only seed from a finalized prior cycle. Drafts
  /// (signature_audit_id == null) are intentionally skipped.
  Future<FormResponse?> call({required String projectId}) async {
    final result = await _repo.getByFormTypeForProject(
      projectId: projectId,
      formType: kFormTypeMdot1126,
      descending: true,
    );
    if (!result.isSuccess) return null;
    final list = result.data ?? const [];
    for (final r in list) {
      if (r.parsedResponseData['signature_audit_id'] != null) return r;
    }
    return null;
  }
}
```

#### Step 5.2.2: BuildCarryForward1126UseCase

```dart
// lib/features/forms/domain/usecases/build_carry_forward_1126_use_case.dart
import '../../data/models/form_response.dart';

class BuildCarryForward1126UseCase {
  /// FROM SPEC §3: Carry forward header + report# + date range + measures.
  /// Rainfall events and signature are intentionally cleared — they vary.
  Map<String, dynamic> call({
    required FormResponse prior,
    required DateTime newInspectionDate,
  }) {
    final priorResponse = prior.parsedResponseData;
    final priorHeader = prior.parsedHeaderData;

    final priorMeasures = (priorResponse['measures'] as List? ?? const [])
        .whereType<Map>()
        .map((m) => m.cast<String, dynamic>())
        .toList();

    // WHY: Carried measures start fresh for this week — inspector reviews them.
    final carriedMeasures = priorMeasures
        .map((m) => <String, dynamic>{
              'id': m['id'],
              'description': m['description'],
              'location': m['location'],
              'status': 'in_place',
              'corrective_action': '',
            })
        .toList();

    final priorReportNum =
        int.tryParse(priorResponse['report_number']?.toString() ?? '') ?? 0;

    return <String, dynamic>{
      'header': priorHeader,
      'report_number': (priorReportNum + 1).toString(),
      'inspection_date': _iso(newInspectionDate),
      'date_of_last_inspection': priorResponse['inspection_date'],
      'rainfall_events': <Map<String, dynamic>>[],
      'measures': carriedMeasures,
      'signature_audit_id': null,
      'weekly_cycle_anchor_date': priorResponse['weekly_cycle_anchor_date'],
    };
  }

  String _iso(DateTime d) => '${d.year.toString().padLeft(4, '0')}-'
      '${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';
}
```

### Sub-phase 5.3: SignFormResponseUseCase + InvalidateFormSignatureOnEditUseCase

**Files:**
- Create: `lib/features/forms/domain/usecases/sign_form_response_use_case.dart`
- Create: `lib/features/forms/domain/usecases/invalidate_form_signature_on_edit_use_case.dart`

**Agent**: `code-fixer-agent`

#### Step 5.3.1: SignFormResponseUseCase

```dart
// lib/features/forms/domain/usecases/sign_form_response_use_case.dart
import 'dart:io';
import 'dart:typed_data';
import 'package:crypto/crypto.dart';
import 'package:path/path.dart' as p;
import 'package:uuid/uuid.dart';
import '../../data/models/form_response.dart';
import '../../data/registries/form_type_constants.dart';
import '../repositories/form_response_repository.dart';
import 'load_prior_1126_use_case.dart';
import 'package:construction_inspector/features/auth/domain/services/session_service.dart';
import 'package:construction_inspector/features/forms/data/services/form_pdf_service.dart';
import 'package:construction_inspector/features/signatures/data/models/signature_audit_log.dart';
import 'package:construction_inspector/features/signatures/data/models/signature_file.dart';
import 'package:construction_inspector/features/signatures/domain/repositories/signature_audit_log_repository.dart';
import 'package:construction_inspector/features/signatures/domain/repositories/signature_file_repository.dart';

/// SEC-1126-04 / SEC-1126-05: Caller no longer supplies userId or companyId.
/// Both are derived inside the use case from the active SessionService so a
/// compromised UI cannot forge identity. Server-side BEFORE INSERT triggers
/// (see 20260408000000_signature_tables.sql) re-overwrite both fields from
/// auth.uid() / get_my_company_id() as a defense-in-depth check.
///
/// SEC-1126-08 / SEC-1126-09: GPS is opt-in only (gpsLat/gpsLng must be null
/// unless the user has consented via the signature_capture_gps setting). The
/// device_id is a per-install random UUID stored in flutter_secure_storage,
/// generated once at first launch — NEVER hardware-derived.
class SignatureContext {
  final String projectId;
  final String deviceId;
  final String platform;
  final String appVersion;
  final double? gpsLat;
  final double? gpsLng;
  final Directory appDocsDir;
  const SignatureContext({
    required this.projectId,
    required this.deviceId,
    required this.platform,
    required this.appVersion,
    required this.appDocsDir,
    this.gpsLat,
    this.gpsLng,
  });
}

class SignFormResponseUseCase {
  final SignatureFileRepository _fileRepo;
  final SignatureAuditLogRepository _auditRepo;
  final FormResponseRepository _formRepo;
  final SessionService _session;
  final FormPdfService _pdfService;
  final LoadPrior1126UseCase _loadPrior;
  final Uuid _uuid;

  SignFormResponseUseCase(
    this._fileRepo,
    this._auditRepo,
    this._formRepo,
    this._session,
    this._pdfService,
    this._loadPrior, {
    Uuid? uuid,
  }) : _uuid = uuid ?? const Uuid();

  /// Embeds the PNG into the pre-sign PDF, writes the file, writes the audit
  /// row, stamps the audit id into the response JSON, and (on first sign)
  /// persists the weekly_cycle_anchor_date.
  ///
  /// Returns the new audit id.
  Future<String> call({
    required String formResponseId,
    required Uint8List signaturePngBytes,
    required Uint8List preSignPdfBytes,
    required SignatureContext ctx,
  }) async {
    // SEC-1126-05: Authentication assertion. Refuse to sign without a session.
    final currentUser = _session.currentUser;
    if (currentUser == null) {
      throw StateError('SignFormResponseUseCase: no authenticated user');
    }
    final userId = currentUser.id;
    final companyId = currentUser.companyId;
    if (companyId == null) {
      throw StateError('SignFormResponseUseCase: user has no company assignment');
    }

    // C1: Embed the rendered signature into the flattened PDF before hashing
    // the PNG. The PDF hash continues to be the PRE-SIGN content hash so the
    // bind verifies the inspector saw the unsigned document; the PNG hash
    // binds the exact image rendered onto the export.
    // NOTE: FormPdfService.embedSignaturePng must exist (added alongside this
    // use case in Phase 6.2). It locates the signature field by AcroForm name
    // and stamps the PNG into its rect.
    final flattenedPdfBytes = await _pdfService.embedSignaturePng(
      pdfBytes: preSignPdfBytes,
      pngBytes: signaturePngBytes,
      formType: kFormTypeMdot1126,
    );
    // The flattened PDF is what gets exported — store via FormPdfService cache
    // (existing pattern). The hash on the audit row stays as the pre-sign hash.

    final fileId = _uuid.v4();
    final dir = Directory(p.join(ctx.appDocsDir.path, 'signatures'));
    if (!await dir.exists()) await dir.create(recursive: true);
    final path = p.join(dir.path, '$fileId.png');
    await File(path).writeAsBytes(signaturePngBytes, flush: true);

    final pngSha = sha256.convert(signaturePngBytes).toString();
    final pdfSha = sha256.convert(preSignPdfBytes).toString();

    await _fileRepo.create(SignatureFile(
      id: fileId,
      projectId: ctx.projectId,
      companyId: companyId,
      localPath: path,
      mimeType: 'image/png',
      fileSizeBytes: signaturePngBytes.length,
      sha256: pngSha,
      createdByUserId: userId,
    ));

    final auditId = _uuid.v4();
    await _auditRepo.create(SignatureAuditLog(
      id: auditId,
      signedRecordType: 'form_response',
      signedRecordId: formResponseId,
      projectId: ctx.projectId,
      companyId: companyId,
      userId: userId,
      deviceId: ctx.deviceId,
      platform: ctx.platform,
      appVersion: ctx.appVersion,
      signedAtUtc: DateTime.now().toUtc(),
      gpsLat: ctx.gpsLat,
      gpsLng: ctx.gpsLng,
      documentHashSha256: pdfSha,
      signaturePngSha256: pngSha,
      signatureFileId: fileId,
    ));

    // Stamp the audit id into the form_response JSON payload.
    // C3: On first sign for this project, also persist weekly_cycle_anchor_date.
    final responseResult = await _formRepo.getById(formResponseId);
    if (responseResult != null) {
      final patch = <String, dynamic>{'signature_audit_id': auditId};
      if (responseResult.formType == kFormTypeMdot1126) {
        final prior = await _loadPrior(projectId: ctx.projectId);
        if (prior == null) {
          // First-ever signed 1126 — anchor cadence to this inspection_date.
          final inspectionDate =
              responseResult.parsedResponseData['inspection_date'];
          if (inspectionDate != null) {
            patch['weekly_cycle_anchor_date'] = inspectionDate;
          }
        }
      }
      final patched = responseResult.withResponseDataPatch(patch);
      await _formRepo.update(patched);
    }
    return auditId;
  }
}
```

> **NOTE**: `SignatureAuditLog` constructor must add the `signaturePngSha256` named param (Phase 3.1.2). The model `toMap`/`fromMap` must include `signature_png_sha256`.

#### Step 5.3.1.a: SignatureContextProvider — device id, consent gate, GPS

A new helper class assembles the `SignatureContext` consumed by
`SignFormResponseUseCase`. Documents how the values originate so reviewers
can audit the privacy posture without spelunking.

- **device_id (SEC-1126-09)** — Generated once on first launch via
  `flutter_secure_storage`, key `signature_device_id`, value
  `Uuid().v4()`. NEVER hardware-derived (no IMEI, no Android ID, no MAC).
  Server validates `length <= 64`.
- **GPS (SEC-1126-08)** — Reads two preconditions: (1) the new
  `signature_capture_gps` user-setting (default OFF), and (2) the
  platform-level location permission. If either is false the context is
  built with `gpsLat == null && gpsLng == null` — the use case writes
  `NULL` into the audit row, which is legally valid. The first time the
  setting is enabled, a row is inserted into the existing
  `user_consent_records` table with `policy_type = 'signature_location_capture'`.
- **platform** — Resolved from `defaultTargetPlatform`, mapped to one of
  `android | ios | windows` (the only three values the CHECK constraint
  allows after the L1 fix). Other platforms throw at sign time.

```dart
// lib/features/signatures/data/services/signature_context_provider.dart
class SignatureContextProvider {
  // ... constructor takes secureStorage, settingsRepo, locationService,
  // packageInfo, sessionService.

  Future<SignatureContext> build({required String projectId}) async {
    final deviceId = await _readOrCreateDeviceId();
    final platform = _resolvePlatform();
    final appVersion = _packageInfo.version;

    double? lat;
    double? lng;
    if (await _settings.get('signature_capture_gps') == true &&
        await _location.hasPermission()) {
      final pos = await _location.current();
      lat = pos?.latitude;
      lng = pos?.longitude;
    }

    return SignatureContext(
      projectId: projectId,
      deviceId: deviceId,
      platform: platform,
      appVersion: appVersion,
      gpsLat: lat,
      gpsLng: lng,
      appDocsDir: await getApplicationDocumentsDirectory(),
    );
  }

  Future<String> _readOrCreateDeviceId() async {
    final existing = await _secureStorage.read(key: 'signature_device_id');
    if (existing != null && existing.length <= 64) return existing;
    final next = const Uuid().v4();
    await _secureStorage.write(key: 'signature_device_id', value: next);
    return next;
  }

  String _resolvePlatform() {
    switch (defaultTargetPlatform) {
      case TargetPlatform.android: return 'android';
      case TargetPlatform.iOS: return 'ios';
      case TargetPlatform.windows: return 'windows';
      default:
        throw StateError('Signing not supported on $defaultTargetPlatform');
    }
  }
}
```

#### Step 5.3.2: InvalidateFormSignatureOnEditUseCase

```dart
// lib/features/forms/domain/usecases/invalidate_form_signature_on_edit_use_case.dart
import '../repositories/form_response_repository.dart';

class InvalidateFormSignatureOnEditUseCase {
  final FormResponseRepository _formRepo;
  InvalidateFormSignatureOnEditUseCase(this._formRepo);

  /// Clears the active signature_audit_id whenever a signed form is edited.
  /// Historical audit rows remain untouched.
  Future<void> call(String formResponseId) async {
    final response = await _formRepo.getById(formResponseId);
    if (response == null) return;
    final current = response.parsedResponseData['signature_audit_id'];
    if (current == null) return;
    final patched =
        response.withResponseDataPatch({'signature_audit_id': null});
    await _formRepo.update(patched);
  }
}
```

### Sub-phase 5.4: Attachment and inline-create use cases

**Files:**
- Create: `lib/features/forms/domain/usecases/resolve_1126_attachment_entry_use_case.dart`
- Create: `lib/features/forms/domain/usecases/create_inspection_date_entry_use_case.dart`

**Agent**: `code-fixer-agent`

#### Step 5.4.1: Resolve use case

```dart
// lib/features/forms/domain/usecases/resolve_1126_attachment_entry_use_case.dart
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';
import 'package:construction_inspector/features/entries/domain/repositories/daily_entry_repository.dart';

class Resolve1126AttachmentEntryUseCase {
  final DailyEntryRepository _entryRepo;
  Resolve1126AttachmentEntryUseCase(this._entryRepo);

  /// Returns the existing daily entry matching inspection_date, or null if
  /// one must be created. Caller prompts user then calls
  /// [CreateInspectionDateEntryUseCase].
  Future<DailyEntry?> findDefault({
    required String projectId,
    required DateTime inspectionDate,
  }) async {
    final matches = await _entryRepo.getByDate(projectId, inspectionDate);
    return matches.firstOrNull;
  }

  /// M3: Returns ALL daily entries for the project so the attach-step picker
  /// can let the inspector override the default match. Sorted by date desc.
  Future<List<DailyEntry>> listCandidates({required String projectId}) async {
    return _entryRepo.getAllForProject(projectId);
  }
}
```

#### Step 5.4.2: Inline create use case

```dart
// lib/features/forms/domain/usecases/create_inspection_date_entry_use_case.dart
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';
import 'package:construction_inspector/features/entries/domain/repositories/daily_entry_repository.dart';
import 'package:construction_inspector/shared/repositories/base_repository.dart';

class CreateInspectionDateEntryUseCase {
  final DailyEntryRepository _entryRepo;
  CreateInspectionDateEntryUseCase(this._entryRepo);

  Future<DailyEntry> call({
    required String projectId,
    required DateTime date,
    required String currentUserId,
  }) async {
    final draft = DailyEntry(
      projectId: projectId,
      date: date,
      createdByUserId: currentUserId,
    );
    final result = await _entryRepo.create(draft);
    if (!result.isSuccess || result.data == null) {
      throw StateError('CreateInspectionDateEntryUseCase: ${result.errorMessage}');
    }
    return result.data!;
  }
}
```

> **NOTE**: Verify `DailyEntry` constructor shape against `lib/features/entries/data/models/daily_entry.dart` before compiling — adjust required params if needed.

### Sub-phase 5.5: ComputeWeeklySescReminderUseCase

**Files:**
- Create: `lib/features/forms/domain/usecases/compute_weekly_sesc_reminder_use_case.dart`

**Agent**: `code-fixer-agent`

#### Step 5.5.1: Reminder model + use case

```dart
// lib/features/forms/domain/usecases/compute_weekly_sesc_reminder_use_case.dart
import '../../data/models/form_response.dart';
import '../../data/registries/form_type_constants.dart';
import '../repositories/form_response_repository.dart';
import 'package:construction_inspector/features/projects/domain/repositories/project_repository.dart';

/// Computed snapshot for dashboard card / entry banner / toolbox TODO.
class WeeklySescReminder {
  final DateTime anchorDate;
  final DateTime currentDueDate;
  final int daysOverdue;
  const WeeklySescReminder({
    required this.anchorDate,
    required this.currentDueDate,
    required this.daysOverdue,
  });
  bool get isOverdue => daysOverdue > 0;
}

class ComputeWeeklySescReminderUseCase {
  final FormResponseRepository _formRepo;
  final ProjectRepository _projectRepo;
  ComputeWeeklySescReminderUseCase(this._formRepo, this._projectRepo);

  /// Returns null if no reminder should fire (no prior signed 1126,
  /// project archived/deleted/inactive, or current cycle already satisfied).
  Future<WeeklySescReminder?> call({
    required String projectId,
    required DateTime today,
  }) async {
    final project = await _projectRepo.getById(projectId);
    if (project == null) return null;
    // FROM SPEC §3: stop condition = archived / deleted / inactive.
    if (!project.isActive || project.deletedAt != null) return null;

    final result = await _formRepo.getByFormTypeForProject(
      projectId: projectId,
      formType: kFormTypeMdot1126,
      descending: false, // ascending — need earliest for anchor
    );
    final all = result.isSuccess ? (result.data ?? const []) : const [];

    // FROM SPEC §3: reminders start only after at least one SIGNED 1126.
    final signed = all.where(_isSigned).toList();
    if (signed.isEmpty) return null;

    final anchor = _parseDate(signed.first.parsedResponseData['inspection_date']);
    if (anchor == null) return null;

    // Rolling 7-day cadence from anchor — extra same-week inspections do NOT shift it.
    final daysSinceAnchor = today.difference(anchor).inDays;
    final cycleIndex = daysSinceAnchor ~/ 7;
    final cycleStart = anchor.add(Duration(days: cycleIndex * 7));
    final currentDueDate = anchor.add(Duration(days: (cycleIndex + 1) * 7));

    final hasFillThisCycle = signed.any((r) {
      final d = _parseDate(r.parsedResponseData['inspection_date']);
      if (d == null) return false;
      return !d.isBefore(cycleStart) && d.isBefore(currentDueDate);
    });
    if (hasFillThisCycle) return null;

    final overdueDays = today.isAfter(currentDueDate)
        ? today.difference(currentDueDate).inDays
        : 0;
    return WeeklySescReminder(
      anchorDate: anchor,
      currentDueDate: currentDueDate,
      daysOverdue: overdueDays,
    );
  }

  bool _isSigned(FormResponse r) =>
      r.parsedResponseData['signature_audit_id'] != null;

  DateTime? _parseDate(Object? v) {
    if (v == null) return null;
    try {
      return DateTime.parse(v.toString());
    } catch (_) {
      return null;
    }
  }
}
```

#### Step 5.5.2: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No issues.

---

## Phase 6: MDOT 1126 Data Layer — Validator, PDF Filler, Registrations

### Sub-phase 6.1: Validator

**Files:**
- Create: `lib/features/forms/data/validators/mdot_1126_validator.dart`

**Agent**: `code-fixer-agent`

#### Step 6.1.1: Pure validator function

```dart
// lib/features/forms/data/validators/mdot_1126_validator.dart
// FROM SPEC §5: "requires inspection_date, signature, all measure rows resolved"

List<String> validateMdot1126(
    Map<String, dynamic> responseData, Map<String, dynamic> headerData) {
  final forExport = headerData['__for_export__'] == true;
  final missing = <String>[];

  bool has(Map<String, dynamic> m, String k) {
    final v = m[k];
    return v != null && v.toString().trim().isNotEmpty;
  }

  if (!has(responseData, 'inspection_date')) missing.add('inspection_date');

  // Every measure row must be resolved to one of three states.
  final measures = (responseData['measures'] as List? ?? const [])
      .whereType<Map>()
      .map((r) => r.cast<String, dynamic>())
      .toList();
  const validStatuses = {'in_place', 'needs_action', 'removed'};
  for (var i = 0; i < measures.length; i++) {
    final status = measures[i]['status']?.toString() ?? '';
    if (!validStatuses.contains(status)) {
      missing.add('measure_status_${i + 1}');
    }
    if (status == 'needs_action' && !has(measures[i], 'corrective_action')) {
      missing.add('measure_corrective_${i + 1}');
    }
  }

  if (!has(responseData, 'signature_audit_id')) missing.add('signature');

  if (forExport) {
    // Re-check at export time — the signature may have been cleared by an edit.
    if (!has(responseData, 'signature_audit_id')) {
      missing.add('signature(required for export)');
    }
  }

  return missing;
}
```

### Sub-phase 6.2: PDF Filler

**Files:**
- Create: `lib/features/forms/data/pdf/mdot_1126_pdf_filler.dart`

**Agent**: `pdf-agent`

#### Step 6.2.1: Introspect the PDF field names (spike)

Run the existing debug generator to dump field names from the template. This is read-only:

```
pwsh -Command "flutter run -d windows --dart-define=DEBUG_PDF_FIELDS=mdot_1126"
```

Record the actual AcroForm field names in a comment at the top of the filler file.

H2: While dumping fields, ALSO record whether separate `date_range_start` /
`date_range_end` fields exist on the template. If they do, add them to the
payload (Phase 6.3.1 initial-data factory) and to the filler (Step 6.2.2).
If they do NOT (i.e., the form only has `inspection_date` +
`date_of_last_inspection`), document the absence in a comment at the top of
the filler file: those two fields together satisfy spec R2 "rolling 7-day
date range" and no extra payload keys are required.

C1: `FormPdfService.embedSignaturePng({pdfBytes, pngBytes, formType})` must
exist by the time Phase 5.3.1 compiles. Add it to `FormPdfService` in this
sub-phase. Implementation: locate the AcroForm signature field by template-
specific name (e.g. `inspector_signature` for 1126 — verify in field dump),
extract its rectangle, draw the PNG via Syncfusion `PdfBitmap` onto the
matching `PdfPage`, then flatten and return the bytes. If no AcroForm
signature field exists, fall back to a fixed rectangle defined per `formType`
in a const map at the top of the service.

#### Step 6.2.2: Filler function

```dart
// lib/features/forms/data/pdf/mdot_1126_pdf_filler.dart
//
// WHY: Pattern mirrors fillMdot0582bPdfFields in mdot_0582b_pdf_filler.dart.
// NOTE: Field names verified against assets/templates/forms/mdot_1126_form.pdf
// via FormPdfService.generateDebugPdf — update the comment block below if the
// template is ever replaced.
//
// TEMPLATE FIELDS (verified):
//   Header: project, contractor, inspector, permit_number, location,
//           report_number, inspection_date, date_of_last_inspection
//   Rainfall: rainfall_date_1..N, rainfall_inches_1..N
//   Measures: measure_desc_1..N, measure_loc_1..N,
//             measure_status_in_1..N, measure_status_action_1..N,
//             measure_status_removed_1..N, measure_corrective_1..N

Map<String, String> fillMdot1126PdfFields(
    Map<String, dynamic> responseData, Map<String, dynamic> headerData) {
  final mapped = <String, String>{};

  void put(String key, dynamic value) {
    final text = value?.toString().trim() ?? '';
    if (text.isEmpty) return;
    mapped[key] = text;
  }

  // Header
  put('project', headerData['project_number'] ?? headerData['job_number']);
  put('contractor', headerData['contractor']);
  put('inspector', headerData['inspector']);
  put('permit_number', headerData['permit_number']);
  put('location', headerData['location']);
  put('report_number', responseData['report_number']);
  put('inspection_date', responseData['inspection_date']);
  put('date_of_last_inspection', responseData['date_of_last_inspection']);

  // Rainfall events
  final rainfall = (responseData['rainfall_events'] as List? ?? const [])
      .whereType<Map>()
      .map((r) => r.cast<String, dynamic>())
      .toList();
  for (var i = 0; i < rainfall.length; i++) {
    final n = i + 1;
    put('rainfall_date_$n', rainfall[i]['date']);
    put('rainfall_inches_$n', rainfall[i]['inches']);
  }

  // SESC measures — tri-state checkbox emits 'X' into the matching group.
  final measures = (responseData['measures'] as List? ?? const [])
      .whereType<Map>()
      .map((r) => r.cast<String, dynamic>())
      .toList();
  for (var i = 0; i < measures.length; i++) {
    final n = i + 1;
    final m = measures[i];
    put('measure_desc_$n', m['description']);
    put('measure_loc_$n', m['location']);
    final status = m['status']?.toString();
    if (status == 'in_place') put('measure_status_in_$n', 'X');
    if (status == 'needs_action') put('measure_status_action_$n', 'X');
    if (status == 'removed') put('measure_status_removed_$n', 'X');
    put('measure_corrective_$n', m['corrective_action']);
  }

  return mapped;
}
```

### Sub-phase 6.3: Single-entry registration

**Files:**
- Create: `lib/features/forms/data/registries/mdot_1126_registrations.dart`
- Modify: `lib/features/forms/data/registries/builtin_forms.dart`

**Agent**: `code-fixer-agent`

#### Step 6.3.1: Register capabilities function

```dart
// lib/features/forms/data/registries/mdot_1126_registrations.dart
import 'package:flutter/material.dart';
import 'form_type_constants.dart';
import 'form_initial_data_factory.dart';
import 'form_pdf_filler_registry.dart';
import 'form_quick_action_registry.dart';
import 'form_validator_registry.dart';
import '../pdf/mdot_1126_pdf_filler.dart';
import '../validators/mdot_1126_validator.dart';

/// WHY: Single entry point to register all 1126 capabilities.
/// Called once during app init (registerBuiltinForms).
void registerMdot1126() {
  // No calculator — 1126 has no numeric calcs.

  FormValidatorRegistry.instance.register(kFormTypeMdot1126, validateMdot1126);

  // H1: Spec §2 payload — register every key the wizard / PDF filler will read.
  FormInitialDataFactory.instance.register(kFormTypeMdot1126, () {
    final today = DateTime.now().toUtc();
    final iso = '${today.year.toString().padLeft(4, '0')}-'
        '${today.month.toString().padLeft(2, '0')}-'
        '${today.day.toString().padLeft(2, '0')}';
    return <String, dynamic>{
      'header': <String, dynamic>{},
      'report_number': '1',
      'inspection_date': iso,
      'date_of_last_inspection': null,
      'rainfall_events': <Map<String, dynamic>>[],
      'measures': <Map<String, dynamic>>[],
      'signature_audit_id': null,
      'weekly_cycle_anchor_date': null,
    };
  });

  FormPdfFillerRegistry.instance.register(
      kFormTypeMdot1126, fillMdot1126PdfFields);

  // FormQuickAction.execute is `FormQuickActionResult Function(FormResponse)` —
  // verified against form_quick_action_registry.dart.
  FormQuickActionRegistry.instance.register(kFormTypeMdot1126, [
    FormQuickAction(
      icon: Icons.water_drop,
      label: 'New 1126',
      execute: (response) => const FormQuickActionResult.navigate(
        name: 'form-new',
        pathParams: {'formId': kFormTypeMdot1126},
      ),
    ),
  ]);

  // NOTE: FormScreenRegistry registration for 1126 is deferred to the UI layer
  // (Phase 7) — same pattern as 0582B.
}
```

#### Step 6.3.2: Append BuiltinFormConfig to the existing literal

Edit the existing `final List<BuiltinFormConfig> builtinForms = List.unmodifiable([...])`
in place — do NOT redeclare the variable. Add the import for
`mdot_1126_registrations.dart` and `form_type_constants.dart`, then append a
single new const entry after the `mdot_0582b` entry. The literal is
non-`const` (because the list itself is `final` not `const`) so the new
`BuiltinFormConfig` can be `const`.

```dart
// lib/features/forms/data/registries/builtin_forms.dart
//
// Add these imports at the top of the file:
import 'mdot_1126_registrations.dart';
import 'form_type_constants.dart';

// Append (do NOT redeclare) the new entry inside the existing list:
//
// final List<BuiltinFormConfig> builtinForms = List.unmodifiable([
//   const BuiltinFormConfig(
//     id: 'mdot_0582b',
//     ...
//   ),
//   // <-- INSERT BELOW -->
//   const BuiltinFormConfig(
//     id: kFormTypeMdot1126,
//     name: 'MDOT 1126 Weekly SESC',
//     templatePath: kFormTemplateMdot1126,
//     registerCapabilities: registerMdot1126,
//   ),
// ]);
```

#### Step 6.3.3: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No issues.

### Sub-phase 6.4: Carry-forward orchestration (C2)

**Files:**
- Modify: `lib/features/forms/presentation/providers/inspector_form_provider_response_actions.dart`
- (or new) `lib/features/forms/presentation/actions/create_mdot_1126_response_action.dart`

**Agent**: `code-fixer-agent`

#### Step 6.4.1: Add a 1126-aware create method

Until now `LoadPrior1126UseCase` and `BuildCarryForward1126UseCase` were
defined but never invoked. Add a custom create flow on
`InspectorFormProvider` (or its response-actions extension) that branches on
prior existence and seeds the new `form_response.response_data` with the
carry-forward payload.

```dart
// Inside InspectorFormProvider (or response-actions extension):

/// FROM SPEC §3 / C2: Creates a new MDOT 1126 form_response. If the project
/// has a prior signed 1126, the carry-forward payload is used as the seed
/// instead of the static FormInitialDataFactory blank.
Future<FormResponse> createMdot1126Response({
  required String projectId,
  DateTime? inspectionDate,
}) async {
  final today = inspectionDate ?? DateTime.now();
  final prior = await _loadPrior1126UseCase(projectId: projectId);

  Map<String, dynamic> initialData;
  if (prior != null) {
    initialData = _buildCarryForward1126UseCase(
      prior: prior,
      newInspectionDate: today,
    );
  } else {
    // Falls back to the H1 first-week defaults registered in Phase 6.3.1.
    initialData = FormInitialDataFactory.instance.build(kFormTypeMdot1126);
  }

  return _saveFormResponseUseCase.create(
    FormResponse.draft(
      formType: kFormTypeMdot1126,
      projectId: projectId,
      responseData: initialData,
      headerData: const {},
      createdByUserId: _session.currentUser?.id,
    ),
  );
}
```

> **NOTE**: The router's `form-new` route handler (the same one
> `FormQuickAction.execute` returns) MUST call `createMdot1126Response`
> when `formId == kFormTypeMdot1126` instead of the generic create path.
> Verify the route handler in `lib/core/router/` and add the branch.

---

## Phase 7: MDOT 1126 Presentation Layer

### Sub-phase 7.1: Testing keys

**Files:**
- Modify: `lib/shared/testing_keys/testing_keys.dart`

**Agent**: `code-fixer-agent`

#### Step 7.1.1: Add 1126 testing keys

```dart
// lib/shared/testing_keys/testing_keys.dart (inside the TestingKeys class)

// FROM SPEC §4: TestingKeys for MDOT 1126
static const Key mdot1126FormScreen = Key('mdot1126_form_screen');
static const Key mdot1126RainfallAddButton = Key('mdot1126_rainfall_add');
static Key mdot1126MeasureRow(int i) => Key('mdot1126_measure_row_$i');
static const Key mdot1126SignaturePad = Key('mdot1126_signature_pad');
static const Key mdot1126AttachDailyEntryPicker =
    Key('mdot1126_attach_daily_entry_picker');
static const Key weeklySescReminderBanner = Key('weekly_sesc_reminder_banner');
static const Key weeklySescReminderCard = Key('weekly_sesc_reminder_card');
static const Key weeklySescToolboxTodo = Key('weekly_sesc_toolbox_todo');
```

### Sub-phase 7.2: Form controller (wizard state, WizardActivityTracker)

**Files:**
- Create: `lib/features/forms/presentation/controllers/mdot_1126_form_controller.dart`

**Agent**: `code-fixer-agent`

#### Step 7.2.1: ChangeNotifier controller

```dart
// lib/features/forms/presentation/controllers/mdot_1126_form_controller.dart
// FROM CLAUDE.md: "Sync-observable controllers" — wizard/long-edit screens
// extract a ChangeNotifier and register with WizardActivityTracker so sync
// doesn't clobber in-flight drafts.

import 'package:flutter/foundation.dart';
import 'package:construction_inspector/features/sync/application/wizard_activity_tracker.dart';

enum Mdot1126Step { rainfall, measuresReview, addMeasures, signature, attach }

class Mdot1126FormController extends ChangeNotifier {
  final String responseId;
  final String projectId;
  final WizardActivityTracker _activity;

  Mdot1126Step _step = Mdot1126Step.rainfall;
  bool _dirty = false;
  bool _disposed = false;

  Mdot1126FormController({
    required this.responseId,
    required this.projectId,
    required WizardActivityTracker activity,
  }) : _activity = activity {
    // Verified API: register({key, label, hasUnsavedChanges})
    _activity.register(
      key: _wizardKey,
      label: 'MDOT 1126 Weekly SESC',
      hasUnsavedChanges: () => _dirty,
    );
  }

  String get _wizardKey => 'mdot_1126:$responseId';

  Mdot1126Step get step => _step;
  bool get isDirty => _dirty;

  void goTo(Mdot1126Step next) {
    if (_step == next) return;
    _step = next;
    notifyListeners();
  }

  void markDirty() {
    if (_dirty) return;
    _dirty = true;
    // Verified API: markChanged(String key) — NOT markDirty.
    _activity.markChanged(_wizardKey);
    notifyListeners();
  }

  /// Called by the screen after a successful save flushes everything to
  /// the repository so SyncCoordinator can resume.
  void clearDirty() {
    if (!_dirty) return;
    _dirty = false;
    _activity.markChanged(_wizardKey);
    notifyListeners();
  }

  @override
  void dispose() {
    if (_disposed) return;
    _disposed = true;
    _activity.unregister(_wizardKey);
    super.dispose();
  }
}
```

### Sub-phase 7.3: Supporting widgets

**Files:**
- Create: `lib/features/forms/presentation/widgets/rainfall_events_editor.dart`
- Create: `lib/features/forms/presentation/widgets/sesc_measures_checklist.dart`
- Create: `lib/features/forms/presentation/widgets/sesc_measure_add_section.dart`
- Create: `lib/features/forms/presentation/widgets/signature_pad_field.dart`

**Agent**: `code-fixer-agent`

#### Step 7.3.1: RainfallEventsEditor

```dart
// lib/features/forms/presentation/widgets/rainfall_events_editor.dart
//
// Verified DS imports — single barrel covers AppSectionCard, AppButton,
// AppTextField, FieldGuideSpacing.
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';

class RainfallEventsEditor extends StatelessWidget {
  final List<Map<String, dynamic>> events;
  final void Function(int index, Map<String, dynamic> patch) onChange;
  final VoidCallback onAdd;
  final void Function(int index) onRemove;

  const RainfallEventsEditor({
    super.key,
    required this.events,
    required this.onChange,
    required this.onAdd,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    return AppSectionCard(
      icon: Icons.water_drop,
      title: 'Rainfall events',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (var i = 0; i < events.length; i++) ...[
            _RainfallRow(
              key: ValueKey('rainfall_$i'),
              event: events[i],
              onChange: (patch) => onChange(i, patch),
              onRemove: () => onRemove(i),
            ),
            SizedBox(height: spacing.xs),
          ],
          AppButton.secondary(
            key: TestingKeys.mdot1126RainfallAddButton,
            label: 'Add rainfall event',
            onPressed: onAdd,
          ),
        ],
      ),
    );
  }
}

class _RainfallRow extends StatelessWidget {
  final Map<String, dynamic> event;
  final ValueChanged<Map<String, dynamic>> onChange;
  final VoidCallback onRemove;

  const _RainfallRow({
    super.key,
    required this.event,
    required this.onChange,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    // Use design-system date picker helper + numeric AppTextField for inches.
    // (Implementation details follow the existing 0582B row widgets.)
    return AppTextField(
      label: 'Inches',
      initialValue: event['inches']?.toString(),
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      onChanged: (v) => onChange({'inches': v}),
    );
  }
}
```

> **NOTE**: The exact design-system component names (`AppCard`, `AppTextField`, `AppButton.secondary`, `FieldGuideSpacing.of`) must match the current exports in `lib/core/design_system/`. The implementing agent should grep `lib/core/design_system/design_system.dart` for the canonical public API before compiling this file.

#### Step 7.3.2: SescMeasuresChecklist

```dart
// lib/features/forms/presentation/widgets/sesc_measures_checklist.dart
//
// CODE-REVIEW FIX: AppSegmented does not exist in the design system. Use a
// row of three AppChip widgets with selection state instead.
// FIXER CYCLE 2: AppChip has no `selected`/`onSelected` props. Verified API
// at lib/core/design_system/atoms/app_chip.dart — use named color factories
// (cyan/amber/error) for selected and AppChip.neutral for unselected; route
// taps via `onTap`.
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';

class SescMeasuresChecklist extends StatelessWidget {
  final List<Map<String, dynamic>> measures;
  final void Function(int i, Map<String, dynamic> patch) onChange;
  const SescMeasuresChecklist({
    super.key,
    required this.measures,
    required this.onChange,
  });

  static const _statuses = <(String, String)>[
    ('in_place', 'In place'),
    ('needs_action', 'Needs action'),
    ('removed', 'Removed'),
  ];

  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < measures.length; i++)
          Padding(
            key: TestingKeys.mdot1126MeasureRow(i),
            padding: EdgeInsets.only(bottom: spacing.sm),
            child: AppSectionCard(
              icon: Icons.checklist,
              title: measures[i]['description']?.toString() ?? 'Measure ${i + 1}',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(measures[i]['location']?.toString() ?? ''),
                  SizedBox(height: spacing.xs),
                  Wrap(
                    spacing: spacing.sm,
                    children: [
                      for (final (value, label) in _statuses)
                        Builder(
                          builder: (context) {
                            final current = measures[i]['status']?.toString() ?? 'in_place';
                            final isSelected = current == value;
                            void onTap() => onChange(i, {
                                  'status': value,
                                  if (value != 'needs_action') 'corrective_action': '',
                                });
                            // CODE-REVIEW FIX (cycle 2): AppChip has no selection prop.
                            // Use color-coded factories for selected state and
                            // AppChip.neutral for unselected. Tap routed via onTap.
                            if (!isSelected) {
                              return AppChip.neutral(label, context: context, onTap: onTap);
                            }
                            switch (value) {
                              case 'in_place':
                                return AppChip.cyan(label, onTap: onTap);
                              case 'needs_action':
                                return AppChip.amber(label, onTap: onTap);
                              case 'removed':
                              default:
                                return AppChip.error(label, onTap: onTap);
                            }
                          },
                        ),
                    ],
                  ),
                  if (measures[i]['status'] == 'needs_action') ...[
                    SizedBox(height: spacing.xs),
                    AppTextField(
                      label: 'Corrective action',
                      initialValue: measures[i]['corrective_action']?.toString(),
                      onChanged: (v) => onChange(i, {'corrective_action': v}),
                    ),
                  ],
                ],
              ),
            ),
          ),
      ],
    );
  }
}
```

> **NOTE**: `AppChip` is exported via the `design_system.dart` barrel. Verified
> API (cycle 2): constructor takes `label`, `backgroundColor`, `foregroundColor`,
> optional `icon`, `onTap`, `onDeleted` — there is no selection prop. Use the
> named factories `AppChip.cyan/amber/error/neutral` to encode tri-state
> selection. `AppChip.neutral` requires `context:`.

#### Step 7.3.3: SescMeasureAddSection (add new row)

```dart
// lib/features/forms/presentation/widgets/sesc_measure_add_section.dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/atoms/app_button.dart';

class SescMeasureAddSection extends StatelessWidget {
  final VoidCallback onAdd;
  const SescMeasureAddSection({super.key, required this.onAdd});

  @override
  Widget build(BuildContext context) => AppButton.secondary(
        label: 'Add SESC measure',
        onPressed: onAdd,
      );
}
```

#### Step 7.3.4: SignaturePadField

```dart
// lib/features/forms/presentation/widgets/signature_pad_field.dart
// FROM SPEC §5: Reusable wrapper around package:signature canvas; emits PNG bytes.

import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:signature/signature.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';

class SignaturePadField extends StatefulWidget {
  final ValueChanged<Uint8List> onSigned;
  final VoidCallback? onCleared;
  const SignaturePadField({super.key, required this.onSigned, this.onCleared});

  @override
  State<SignaturePadField> createState() => _SignaturePadFieldState();
}

class _SignaturePadFieldState extends State<SignaturePadField> {
  late final SignatureController _controller = SignatureController(
    penStrokeWidth: 2,
    penColor: Colors.black,
  );

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    return AppSectionCard(
      icon: Icons.draw,
      title: 'Inspector signature',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            height: 180,
            child: Signature(
              key: TestingKeys.mdot1126SignaturePad,
              controller: _controller,
              backgroundColor: Theme.of(context).colorScheme.surface,
            ),
          ),
          SizedBox(height: spacing.sm),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              AppButton.ghost(
                label: 'Clear',
                onPressed: () {
                  _controller.clear();
                  widget.onCleared?.call();
                },
              ),
              AppButton.primary(
                label: 'Sign',
                onPressed: () async {
                  if (_controller.isEmpty) return;
                  final bytes = await _controller.toPngBytes();
                  if (bytes != null) widget.onSigned(bytes);
                },
              ),
            ],
          ),
        ],
      ),
    );
  }
}
```

#### Step 7.3.5: AttachStep widget (M3)

**Files:**
- Create: `lib/features/forms/presentation/widgets/attach_step.dart`

```dart
// lib/features/forms/presentation/widgets/attach_step.dart
//
// FROM SPEC §3 / M3: Lets the inspector confirm or override the daily entry
// the signed 1126 attaches to. Defaults to the entry matching inspection_date,
// but a picker exposes every project entry so the user can override.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/forms/data/models/form_response.dart';
import 'package:construction_inspector/features/forms/domain/usecases/resolve_1126_attachment_entry_use_case.dart';
import 'package:construction_inspector/features/forms/domain/usecases/create_inspection_date_entry_use_case.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';

class AttachStep extends StatelessWidget {
  final FormResponse response;
  final VoidCallback onAttached;
  const AttachStep({super.key, required this.response, required this.onAttached});

  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    final resolve = context.read<Resolve1126AttachmentEntryUseCase>();
    final create = context.read<CreateInspectionDateEntryUseCase>();
    final inspectionDate = DateTime.parse(
      response.parsedResponseData['inspection_date'] as String,
    );

    return FutureBuilder(
      future: resolve.listCandidates(projectId: response.projectId!),
      builder: (ctx, snap) {
        final candidates = snap.data ?? const [];
        return ListView(
          key: TestingKeys.mdot1126AttachDailyEntryPicker,
          padding: EdgeInsets.all(spacing.md),
          children: [
            for (final entry in candidates)
              ListTile(
                title: Text(entry.date.toIso8601String().split('T').first),
                onTap: () async {
                  await ctx
                      .read<FormResponseRepository>()
                      .attachToEntry(response.id, entry.id);
                  onAttached();
                },
              ),
            SizedBox(height: spacing.lg),
            AppButton.secondary(
              label: 'Create new entry for ${inspectionDate.toIso8601String().split('T').first}',
              onPressed: () async {
                final newEntry = await create(
                  projectId: response.projectId!,
                  date: inspectionDate,
                  currentUserId: ctx.read<SessionService>().currentUser!.id,
                );
                await ctx
                    .read<FormResponseRepository>()
                    .attachToEntry(response.id, newEntry.id);
                onAttached();
              },
            ),
          ],
        );
      },
    );
  }
}
```

### Sub-phase 7.4: Reminder widgets (banner + card)

**Files:**
- Create: `lib/features/forms/presentation/widgets/weekly_sesc_reminder_banner.dart`
- Create: `lib/features/forms/presentation/widgets/weekly_sesc_reminder_card.dart`

**Agent**: `code-fixer-agent`

#### Step 7.4.1: Reminder banner (daily entry)

```dart
// lib/features/forms/presentation/widgets/weekly_sesc_reminder_banner.dart
//
// CODE-REVIEW FIX: AppBanner has no `title`/`subtitle`/`onTap` props.
// Verified API: AppBanner({icon, message, severity?, actions?, dismissible}).
// We surface the severity via `warning` and use a single message string;
// the action button replaces the previous onTap behavior.
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/forms/domain/usecases/compute_weekly_sesc_reminder_use_case.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';

class WeeklySescReminderBanner extends StatelessWidget {
  final WeeklySescReminder reminder;
  final VoidCallback onTap;
  const WeeklySescReminderBanner({
    super.key,
    required this.reminder,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final daysLate = reminder.daysOverdue;
    final tail = daysLate > 0
        ? 'overdue by $daysLate day${daysLate == 1 ? '' : 's'}'
        : 'due today';
    return AppBanner(
      testingKey: TestingKeys.weeklySescReminderBanner,
      icon: Icons.water_drop,
      message: 'Weekly SESC report $tail',
      severity: AppBannerSeverity.warning,
      actions: [
        AppButton.ghost(label: 'Open', onPressed: onTap),
      ],
    );
  }
}
```

#### Step 7.4.2: Reminder card (dashboard)

```dart
// lib/features/forms/presentation/widgets/weekly_sesc_reminder_card.dart
//
// CODE-REVIEW FIX: AppSectionCard has no onTap. Wrap a tappable ListTile
// inside it so taps still flow to the navigation handler.
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/forms/domain/usecases/compute_weekly_sesc_reminder_use_case.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';

class WeeklySescReminderCard extends StatelessWidget {
  final WeeklySescReminder reminder;
  final VoidCallback onTap;
  const WeeklySescReminderCard({
    super.key,
    required this.reminder,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return AppSectionCard(
      key: TestingKeys.weeklySescReminderCard,
      icon: Icons.water_drop,
      title: 'Weekly SESC report',
      child: ListTile(
        contentPadding: EdgeInsets.zero,
        onTap: onTap,
        title: Text(reminder.isOverdue
            ? 'Overdue — tap to start'
            : 'Due ${reminder.currentDueDate.toIso8601String().split('T').first}'),
        trailing: const Icon(Icons.arrow_forward),
      ),
    );
  }
}
```

### Sub-phase 7.5: Mdot1126FormScreen

**Files:**
- Create: `lib/features/forms/presentation/screens/mdot_1126_form_screen.dart`

**Agent**: `code-fixer-agent`

#### Step 7.5.1: Screen skeleton

```dart
// lib/features/forms/presentation/screens/mdot_1126_form_screen.dart
// FROM SPEC §4, §5: Top-level screen. Reuses InspectorFormProvider for CRUD
// and Mdot1126FormController for wizard state.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart'; // FIXER CYCLE 2: required for `const Uuid().v4()` in add-measures step
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/forms/presentation/controllers/mdot_1126_form_controller.dart';
import 'package:construction_inspector/features/forms/presentation/providers/inspector_form_provider.dart';
import 'package:construction_inspector/features/forms/presentation/widgets/rainfall_events_editor.dart';
import 'package:construction_inspector/features/forms/presentation/widgets/sesc_measures_checklist.dart';
import 'package:construction_inspector/features/forms/presentation/widgets/sesc_measure_add_section.dart';
import 'package:construction_inspector/features/forms/presentation/widgets/signature_pad_field.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';

class Mdot1126FormScreen extends StatefulWidget {
  final String formId;     // always kFormTypeMdot1126
  final String responseId;
  final String projectId;
  const Mdot1126FormScreen({
    super.key,
    required this.formId,
    required this.responseId,
    required this.projectId,
  });

  @override
  State<Mdot1126FormScreen> createState() => _Mdot1126FormScreenState();
}

class _Mdot1126FormScreenState extends State<Mdot1126FormScreen> {
  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    return ChangeNotifierProvider<Mdot1126FormController>(
      create: (ctx) => Mdot1126FormController(
        responseId: widget.responseId,
        projectId: widget.projectId,
        activity: ctx.read(),
      ),
      child: Scaffold(
        key: TestingKeys.mdot1126FormScreen,
        appBar: AppBar(title: const Text('MDOT 1126 Weekly SESC')),
        body: Consumer2<InspectorFormProvider, Mdot1126FormController>(
          builder: (ctx, formProvider, controller, _) {
            // H7: If the wizard lands on measuresReview but the response has
            // no carry-forward measures, jump straight to addMeasures.
            final response = formProvider.currentResponse;
            final measures = (response?.parsedResponseData['measures'] as List?
                    ?? const [])
                .whereType<Map>()
                .toList();
            final effectiveStep =
                (controller.step == Mdot1126Step.measuresReview && measures.isEmpty)
                    ? Mdot1126Step.addMeasures
                    : controller.step;

            switch (effectiveStep) {
              case Mdot1126Step.rainfall:
                return _buildRainfallStep(ctx, formProvider, controller, spacing);
              case Mdot1126Step.measuresReview:
                return _buildMeasuresReviewStep(ctx, formProvider, controller, spacing);
              case Mdot1126Step.addMeasures:
                return _buildAddMeasuresStep(ctx, formProvider, controller, spacing);
              case Mdot1126Step.signature:
                return _buildSignatureStep(ctx, formProvider, controller, spacing);
              case Mdot1126Step.attach:
                return _buildAttachStep(ctx, formProvider, controller, spacing);
            }
          },
        ),
      ),
    );
  }

  /// Rainfall step. Includes the H8 inspection-date picker (defaults to the
  /// next scheduled due date computed by ComputeWeeklySescReminderUseCase, but
  /// allows free backdating).
  Widget _buildRainfallStep(
    BuildContext ctx,
    InspectorFormProvider formProvider,
    Mdot1126FormController controller,
    FieldGuideSpacing spacing,
  ) {
    final response = formProvider.currentResponse!;
    final data = response.parsedResponseData;
    final inspectionDate =
        DateTime.tryParse(data['inspection_date']?.toString() ?? '') ??
            DateTime.now();
    final events = (data['rainfall_events'] as List? ?? const [])
        .whereType<Map>()
        .map((m) => m.cast<String, dynamic>())
        .toList();

    return ListView(
      padding: EdgeInsets.all(spacing.md),
      children: [
        // Inspection date picker (H8)
        ListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Inspection date'),
          subtitle: Text(inspectionDate.toIso8601String().split('T').first),
          trailing: const Icon(Icons.calendar_today),
          onTap: () async {
            final picked = await showDatePicker(
              context: ctx,
              initialDate: inspectionDate,
              firstDate: DateTime(inspectionDate.year - 1),
              lastDate: DateTime(inspectionDate.year + 1),
            );
            if (picked == null) return;
            final iso = '${picked.year.toString().padLeft(4, '0')}-'
                '${picked.month.toString().padLeft(2, '0')}-'
                '${picked.day.toString().padLeft(2, '0')}';
            await ctx
                .read<InspectorFormProvider>()
                .updateResponseData(response.id, {'inspection_date': iso});
            controller.markDirty();
          },
        ),
        SizedBox(height: spacing.md),
        RainfallEventsEditor(
          events: events,
          onAdd: () async {
            final next = [...events, <String, dynamic>{'date': null, 'inches': null}];
            await ctx
                .read<InspectorFormProvider>()
                .updateResponseData(response.id, {'rainfall_events': next});
            controller.markDirty();
          },
          onChange: (i, patch) async {
            final next = [...events];
            next[i] = {...next[i], ...patch};
            await ctx
                .read<InspectorFormProvider>()
                .updateResponseData(response.id, {'rainfall_events': next});
            controller.markDirty();
          },
          onRemove: (i) async {
            final next = [...events]..removeAt(i);
            await ctx
                .read<InspectorFormProvider>()
                .updateResponseData(response.id, {'rainfall_events': next});
            controller.markDirty();
          },
        ),
        SizedBox(height: spacing.lg),
        AppButton.primary(
          label: 'Next: review measures',
          onPressed: () => controller.goTo(Mdot1126Step.measuresReview),
        ),
      ],
    );
  }

  Widget _buildMeasuresReviewStep(
    BuildContext ctx,
    InspectorFormProvider formProvider,
    Mdot1126FormController controller,
    FieldGuideSpacing spacing,
  ) {
    final response = formProvider.currentResponse!;
    final measures = (response.parsedResponseData['measures'] as List? ?? const [])
        .whereType<Map>()
        .map((m) => m.cast<String, dynamic>())
        .toList();
    return ListView(
      padding: EdgeInsets.all(spacing.md),
      children: [
        SescMeasuresChecklist(
          measures: measures,
          onChange: (i, patch) async {
            final next = [...measures];
            next[i] = {...next[i], ...patch};
            await ctx
                .read<InspectorFormProvider>()
                .updateResponseData(response.id, {'measures': next});
            controller.markDirty();
          },
        ),
        SizedBox(height: spacing.lg),
        AppButton.secondary(
          label: 'Add new measures',
          onPressed: () => controller.goTo(Mdot1126Step.addMeasures),
        ),
        SizedBox(height: spacing.sm),
        AppButton.primary(
          label: 'Next: signature',
          onPressed: () => controller.goTo(Mdot1126Step.signature),
        ),
      ],
    );
  }

  Widget _buildAddMeasuresStep(
    BuildContext ctx,
    InspectorFormProvider formProvider,
    Mdot1126FormController controller,
    FieldGuideSpacing spacing,
  ) {
    final response = formProvider.currentResponse!;
    final measures = (response.parsedResponseData['measures'] as List? ?? const [])
        .whereType<Map>()
        .map((m) => m.cast<String, dynamic>())
        .toList();
    return ListView(
      padding: EdgeInsets.all(spacing.md),
      children: [
        SescMeasureAddSection(
          onAdd: () async {
            final next = [
              ...measures,
              <String, dynamic>{
                'id': const Uuid().v4(),
                'description': '',
                'location': '',
                'status': 'in_place',
                'corrective_action': '',
              },
            ];
            await ctx
                .read<InspectorFormProvider>()
                .updateResponseData(response.id, {'measures': next});
            controller.markDirty();
          },
        ),
        SizedBox(height: spacing.lg),
        AppButton.primary(
          label: 'Done adding',
          onPressed: () => controller.goTo(
            measures.isEmpty ? Mdot1126Step.signature : Mdot1126Step.measuresReview,
          ),
        ),
      ],
    );
  }

  Widget _buildSignatureStep(
    BuildContext ctx,
    InspectorFormProvider formProvider,
    Mdot1126FormController controller,
    FieldGuideSpacing spacing,
  ) {
    final response = formProvider.currentResponse!;
    return ListView(
      padding: EdgeInsets.all(spacing.md),
      children: [
        SignaturePadField(
          onSigned: (pngBytes) async {
            // Pulls pre-sign PDF bytes from FormPdfService cache, runs
            // SignFormResponseUseCase. Auth and companyId are derived
            // server-side and inside the use case from SessionService.
            final useCase = ctx.read<SignFormResponseUseCase>();
            final pdfBytes =
                await ctx.read<FormPdfService>().renderPreSignPdf(response);
            final deviceContext = await ctx.read<SignatureContextProvider>().build(
                  projectId: response.projectId!,
                );
            await useCase(
              formResponseId: response.id,
              signaturePngBytes: pngBytes,
              preSignPdfBytes: pdfBytes,
              ctx: deviceContext,
            );
            controller.clearDirty();
            controller.goTo(Mdot1126Step.attach);
          },
        ),
      ],
    );
  }

  Widget _buildAttachStep(
    BuildContext ctx,
    InspectorFormProvider formProvider,
    Mdot1126FormController controller,
    FieldGuideSpacing spacing,
  ) {
    // M3: Use the AttachStep widget extracted in Phase 7.3.5 below.
    return AttachStep(
      response: formProvider.currentResponse!,
      onAttached: () => Navigator.of(ctx).pop(),
    );
  }
}
```

> **NOTE**: `InspectorFormProvider.currentResponse`, `updateResponseData`,
> `FormPdfService.renderPreSignPdf`, and `SignatureContextProvider.build`
> are the canonical names used elsewhere in the forms module. The
> implementer must verify each by grep before compiling and substitute the
> actual method name if it differs (e.g. the existing 0582B screen uses
> `responseActions.updateResponseData`).

### Sub-phase 7.6: Screen registry binding

**Files:**
- Modify: wherever `FormScreenRegistry.instance.register('mdot_0582b', ...)` is currently called (grep `FormScreenRegistry.instance.register` to locate — likely `lib/features/forms/presentation/form_registry_init.dart` or similar)

**Agent**: `code-fixer-agent`

#### Step 7.6.1: Register Mdot1126FormScreen

```dart
FormScreenRegistry.instance.register(
  kFormTypeMdot1126,
  ({required formId, required responseId, required projectId}) =>
      Mdot1126FormScreen(
    formId: formId,
    responseId: responseId,
    projectId: projectId,
  ),
);
```

#### Step 7.6.2: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No issues.

### Sub-phase 7.7: Universal signature invalidation hook (SEC-1126-06 / H4)

**Files:**
- Modify: `lib/features/forms/data/repositories/form_response_repository_impl.dart`
- Verify path with: `pwsh -Command "Get-ChildItem -Recurse lib/features/forms -Filter form_response_repository_impl.dart"`

**Agent**: `code-fixer-agent`

#### Step 7.7.1: Move invalidation into the repository update() method

The previous design wired the hook into a single provider method, which left
every other write path (background sync, conflict resolution, future
features) able to bypass it. Move the check into the repository so EVERY
update for an `mdot_1126` form is gated.

Approach (chosen): repository-layer hook. Rationale: keeps the rule in pure
Dart, easy to unit test, no SQLite trigger gymnastics, and runs even when
mutations come from background jobs that bypass the provider.

```dart
// lib/features/forms/data/repositories/form_response_repository_impl.dart
// SEC-1126-06 / H4: Universal invalidation. Any update to a signed mdot_1126
// response that mutates the user-visible payload clears the active
// signature_audit_id. Historical audit rows are never touched.

@override
Future<RepositoryResult<FormResponse>> update(FormResponse response) async {
  if (response.formType == kFormTypeMdot1126) {
    // FIXER CYCLE 2: Verified at lib/features/forms/domain/repositories/form_response_repository.dart:41
    // — `getById(String id)` is the BaseRepository<FormResponse> override and
    // returns `Future<FormResponse?>` directly (NOT a RepositoryResult). The
    // RepositoryResult-wrapped variant is `getResponseById`. Do not unwrap.
    final FormResponse? prior = await getById(response.id);
    if (prior != null) {
      final priorAuditId = prior.parsedResponseData['signature_audit_id'];
      if (priorAuditId != null) {
        // Compare normalized payload hashes (excluding signature_audit_id
        // itself so re-stamping the same id is a no-op).
        final priorPayload = Map<String, dynamic>.from(prior.parsedResponseData)
          ..remove('signature_audit_id');
        final newPayload = Map<String, dynamic>.from(response.parsedResponseData)
          ..remove('signature_audit_id');
        if (jsonEncode(priorPayload) != jsonEncode(newPayload)) {
          // Mutate response to clear the audit id BEFORE writing to local DB.
          response = response.withResponseDataPatch({'signature_audit_id': null});
        }
      }
    }
  }
  return _local.update(response);
}
```

> **NOTE**: `FormResponse.formType`, `parsedResponseData`, and
> `withResponseDataPatch` are existing members. The implementer must verify
> the local update method name (`_local.update` vs `_local.upsert`) and
> import `dart:convert` for `jsonEncode`. The provider-layer hook is now
> redundant — do NOT add it.

---

## Phase 8: Export Bundling Rewrite

### Sub-phase 8.0: ExportBlockedException domain error

**Files:**
- Create: `lib/features/entries/domain/errors/export_blocked_exception.dart`

**Agent**: `code-fixer-agent`

#### Step 8.0.1: Define the exception used by Phase 8.1.3

```dart
// lib/features/entries/domain/errors/export_blocked_exception.dart
//
// FROM SPEC §5: Thrown by ExportEntryUseCase when one of the bundled forms
// fails its export-time validator (typically a missing signature on a
// re-edited 1126). The UI catches this and surfaces a SnackBar.
class ExportBlockedException implements Exception {
  final String formResponseId;
  final List<String> missing;
  const ExportBlockedException({
    required this.formResponseId,
    required this.missing,
  });

  @override
  String toString() =>
      'ExportBlockedException(formResponseId: $formResponseId, missing: $missing)';
}
```

### Sub-phase 8.1: One-folder bundle

**Files:**
- Modify: `lib/features/entries/domain/usecases/export_entry_use_case.dart`

**Agent**: `code-fixer-agent`

#### Step 8.1.1: Rewrite the call() body to produce a per-entry folder

```dart
// lib/features/entries/domain/usecases/export_entry_use_case.dart
// FROM SPEC §3, §10: "One folder containing IDR + attached form PDFs + photos"

Future<List<String>> call(String entryId, {String? currentUserId}) async {
  final entry = await _entryRepository.getById(entryId);
  if (entry == null) return [];

  // Build per-entry folder path.
  final docs = await _pathProvider.getApplicationDocumentsDirectory();
  final entryDate = entry.date.toIso8601String().split('T').first;
  final shortId = entryId.length >= 8 ? entryId.substring(0, 8) : entryId;
  final bundleDir = Directory(
    p.join(docs.path, 'exports', entry.projectId, '${entryDate}_$shortId'),
  );
  if (!await bundleDir.exists()) await bundleDir.create(recursive: true);

  final paths = <String>[];

  // 1. IDR PDF
  final idrPath = await _entryPdfExportUseCase.call(entryId);
  if (idrPath != null) {
    final dest = p.join(bundleDir.path, p.basename(idrPath));
    await File(idrPath).copy(dest);
    paths.add(dest);
  }

  // 2. Each attached form PDF
  final responsesResult =
      await _formResponseRepository.getResponsesForEntry(entryId);
  final responses =
      responsesResult.isSuccess ? (responsesResult.data ?? <FormResponse>[]) : const [];
  for (final response in responses) {
    final formPath = await _exportFormUseCase.call(
      response.id,
      currentUserId: currentUserId,
    );
    if (formPath != null) {
      final dest = p.join(bundleDir.path, p.basename(formPath));
      await File(formPath).copy(dest);
      paths.add(dest);
    }
  }

  // 3. Photo files (referenced via photo_local_datasource — follow existing API)
  final photos = await _photoRepository.getByEntry(entryId);
  for (final photo in photos) {
    final srcPath = photo.localPath;
    if (srcPath == null || srcPath.isEmpty) continue;
    final src = File(srcPath);
    if (!await src.exists()) continue;
    final dest = p.join(bundleDir.path, p.basename(srcPath));
    await src.copy(dest);
    paths.add(dest);
  }

  // Record ONE EntryExport row pointing at the bundle directory.
  if (paths.isNotEmpty) {
    final export = EntryExport(
      entryId: entry.id,
      projectId: entry.projectId,
      filePath: bundleDir.path,
      filename: 'bundle_${entryDate}_$shortId',
      fileSizeBytes: await _folderSize(bundleDir),
      exportedAt: DateTime.now().toUtc().toIso8601String(),
      createdByUserId: currentUserId,
    );
    await _entryExportRepository.create(export);

    // Keep per-file ExportArtifact rows for listing.
    for (final filePath in paths) {
      await _exportArtifactRepository.create(
        ExportArtifact(
          projectId: entry.projectId,
          artifactType: _artifactType(filePath),
          sourceRecordId: entry.id,
          title: p.basename(filePath),
          filename: p.basename(filePath),
          localPath: filePath,
          mimeType: _guessMime(filePath),
          createdByUserId: currentUserId,
        ),
      );
    }
  }

  return paths;
}

Future<int> _folderSize(Directory dir) async {
  var total = 0;
  await for (final ent in dir.list(recursive: true, followLinks: false)) {
    if (ent is File) total += await ent.length();
  }
  return total;
}

String _artifactType(String path) {
  final ext = p.extension(path).toLowerCase();
  if (ext == '.pdf') return 'form_pdf';
  if (ext == '.jpg' || ext == '.jpeg' || ext == '.png') return 'photo';
  return 'entry_pdf';
}

String _guessMime(String path) {
  final ext = p.extension(path).toLowerCase();
  return switch (ext) {
    '.pdf' => 'application/pdf',
    '.jpg' || '.jpeg' => 'image/jpeg',
    '.png' => 'image/png',
    _ => 'application/octet-stream',
  };
}
```

#### Step 8.1.2: Update constructor to inject `PathProviderPlatform`, `EntryPdfExportUseCase`, `PhotoRepository`

```dart
// Inject the new dependencies into ExportEntryUseCase via constructor
// alongside the existing ones. Wire through DI container accordingly.
```

#### Step 8.1.3: Export blocked by signature

```dart
// Before running the form export loop, call FormValidatorRegistry.instance
// .validate(formType, parsedResponseData, {...headerData, '__for_export__': true})
// for each form and abort (or skip) if missing is non-empty.
// FROM SPEC: "export is blocked until re-signed"
for (final response in responses) {
  final missing = FormValidatorRegistry.instance.validate(
    response.formType,
    response.parsedResponseData,
    {...response.parsedHeaderData, '__for_export__': true},
  );
  if (missing.isNotEmpty) {
    throw ExportBlockedException(
      formResponseId: response.id,
      missing: missing,
    );
  }
  // ... proceed with exportFormUseCase.call(response.id)
}
```

#### Step 8.1.4: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No issues.

---

## Phase 9: Reminder UI Bindings

### Sub-phase 9.0: SescReminderProvider (H3 — reactive cache)

**Files:**
- Create: `lib/features/forms/presentation/providers/sesc_reminder_provider.dart`

**Agent**: `code-fixer-agent`

#### Step 9.0.1: ChangeNotifier wrapper that caches the snapshot

```dart
// lib/features/forms/presentation/providers/sesc_reminder_provider.dart
//
// H3 fix: dashboard / banner / toolbox previously used FutureBuilder which
// rebuilt every frame and never refreshed after sign. This provider caches
// the snapshot per project and listens to InspectorFormProvider so that
// signing or editing a 1126 invalidates the cache automatically.
import 'package:flutter/foundation.dart';
import 'package:construction_inspector/features/forms/domain/usecases/compute_weekly_sesc_reminder_use_case.dart';
import 'package:construction_inspector/features/forms/presentation/providers/inspector_form_provider.dart';

class SescReminderProvider extends ChangeNotifier {
  final ComputeWeeklySescReminderUseCase _useCase;
  final InspectorFormProvider _formProvider;
  final Map<String, WeeklySescReminder?> _cache = {};

  SescReminderProvider(this._useCase, this._formProvider) {
    _formProvider.addListener(_onFormProviderChanged);
  }

  WeeklySescReminder? snapshotFor(String projectId) => _cache[projectId];

  Future<WeeklySescReminder?> refresh(String projectId) async {
    final result = await _useCase(projectId: projectId, today: DateTime.now());
    _cache[projectId] = result;
    notifyListeners();
    return result;
  }

  void _onFormProviderChanged() {
    // Invalidate every cached project — a sign/edit on any 1126 may shift
    // its cycle. Consumers will re-call refresh() on next build.
    _cache.clear();
    notifyListeners();
  }

  @override
  void dispose() {
    _formProvider.removeListener(_onFormProviderChanged);
    super.dispose();
  }
}
```

### Sub-phase 9.1: Dashboard card binding

**Files:**
- Modify: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`

**Agent**: `code-fixer-agent`

#### Step 9.1.1: Inject `ComputeWeeklySescReminderUseCase` + render card at top

```dart
// FROM SPEC §3: "computed UI card, placed at the top of the project dashboard".
// H3: Reactive — consumes SescReminderProvider, refreshes on first build,
// rebuilds whenever InspectorFormProvider notifies.
Consumer<SescReminderProvider>(
  builder: (context, sesc, _) {
    final cached = sesc.snapshotFor(activeProjectId);
    if (cached == null) {
      // Trigger one-shot refresh on first build (post-frame to avoid setState
      // during build). The provider re-notifies when refresh resolves.
      WidgetsBinding.instance.addPostFrameCallback(
        (_) => sesc.refresh(activeProjectId),
      );
      return const SizedBox.shrink();
    }
    return WeeklySescReminderCard(
      reminder: cached,
      onTap: () => context.goNamed(
        'form-new',
        pathParameters: {'formId': kFormTypeMdot1126},
      ),
    );
  },
),
```

### Sub-phase 9.2: Daily entry banner binding

**Files:**
- Modify: daily entry screen (grep `DashboardTodaysEntry` upstream or entries screen)

**Agent**: `code-fixer-agent`

#### Step 9.2.1: Render banner on today's entry only

```dart
// FROM SPEC §3: "shown only on today's daily entry, only when today's entry exists".
// H3: Reactive via SescReminderProvider.
if (isToday(entry.date)) ... [
  Consumer<SescReminderProvider>(
    builder: (ctx, sesc, _) {
      final cached = sesc.snapshotFor(entry.projectId);
      if (cached == null) {
        WidgetsBinding.instance.addPostFrameCallback(
          (_) => sesc.refresh(entry.projectId),
        );
        return const SizedBox.shrink();
      }
      return WeeklySescReminderBanner(
        reminder: cached,
        onTap: () => ctx.goNamed(
          'form-new',
          pathParameters: {'formId': kFormTypeMdot1126},
        ),
      );
    },
  ),
]
```

### Sub-phase 9.3: Toolbox computed TODO (M4 — extracted widget + reactive)

**Files:**
- Create: `lib/features/forms/presentation/widgets/weekly_sesc_toolbox_todo.dart`
- Modify: toolbox screen (grep `ToolboxScreen` — `lib/features/toolbox/presentation/screens/`)

**Agent**: `code-fixer-agent`

#### Step 9.3.1: Extract WeeklySescToolboxTodo widget

```dart
// lib/features/forms/presentation/widgets/weekly_sesc_toolbox_todo.dart
//
// FROM SPEC §3: "computed persistent recurring reminder in the toolbox TODO
// feature; not stored as a todo_items row."
// M4: Extracted into its own widget so it can be unit-tested in isolation.
// H3: Reactive via SescReminderProvider.
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/forms/data/registries/form_type_constants.dart';
import 'package:construction_inspector/features/forms/presentation/providers/sesc_reminder_provider.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';

class WeeklySescToolboxTodo extends StatelessWidget {
  final String projectId;
  const WeeklySescToolboxTodo({super.key, required this.projectId});

  @override
  Widget build(BuildContext context) {
    return Consumer<SescReminderProvider>(
      builder: (ctx, sesc, _) {
        final cached = sesc.snapshotFor(projectId);
        if (cached == null) {
          WidgetsBinding.instance.addPostFrameCallback(
            (_) => sesc.refresh(projectId),
          );
          return const SizedBox.shrink();
        }
        return AppSectionCard(
          key: TestingKeys.weeklySescToolboxTodo,
          icon: Icons.water_drop,
          title: 'Weekly SESC report',
          child: ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Tap to start'),
            onTap: () => ctx.goNamed(
              'form-new',
              pathParameters: {'formId': kFormTypeMdot1126},
            ),
          ),
        );
      },
    );
  }
}
```

#### Step 9.3.2: Mount the widget on the toolbox screen

```dart
// Inside the toolbox screen build method, where todo rows are listed:
WeeklySescToolboxTodo(projectId: activeProjectId),
```

#### Step 9.3.3: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No issues.

---

## Phase 10: Integration, Lint Gate, Cleanup

### Sub-phase 10.1: DI wiring for all new use cases

**Files:**
- Modify: `lib/core/di/` (provider container or typed `*Deps` containers)

**Agent**: `code-fixer-agent`

#### Step 10.1.1: Construct and expose all 1126 domain dependencies

```dart
// Wire:
// - LoadPrior1126UseCase(formResponseRepository)
// - BuildCarryForward1126UseCase()
// - SignFormResponseUseCase(
//     signatureFileRepo,
//     signatureAuditRepo,
//     formResponseRepo,
//     sessionService,           // SEC-1126-04 / -05
//     formPdfService,           // C1 — embeds signature PNG
//     loadPrior1126UseCase,     // C3 — anchor-date persistence
//   )
// - InvalidateFormSignatureOnEditUseCase(formResponseRepo)  // optional now;
//     SEC-1126-06 moved enforcement into FormResponseRepositoryImpl.update()
// - Resolve1126AttachmentEntryUseCase(dailyEntryRepo)
// - CreateInspectionDateEntryUseCase(dailyEntryRepo)
// - ComputeWeeklySescReminderUseCase(formResponseRepo, projectRepo)
// - SescReminderProvider(computeWeeklySescReminderUseCase, inspectorFormProvider)
//     -> registered as ChangeNotifierProvider in tier 5 widget tree
// - SignatureContextProvider(secureStorage, settingsRepo, locationService,
//     packageInfo, sessionService)
//
// Plus SignatureFileRepositoryImpl and SignatureAuditLogRepositoryImpl from
// their local datasources (Phase 3).
```

### Sub-phase 10.2: Update sync validation script

**Files:**
- Modify: `scripts/validate_sync_adapter_registry.py`

**Agent**: `code-fixer-agent`

#### Step 10.2.1: Allow new tables in the registry validation

```python
# Add 'signature_files' and 'signature_audit_log' to the expected table set.
# This script is CI-run and ensures every SQLite-synced table has an adapter.
```

### Sub-phase 10.3: Ensure registerBuiltinForms() runs registrations

**Files:**
- Modify: wherever `builtinForms.forEach((c) => c.registerCapabilities())` is currently called (grep `registerCapabilities` — likely `lib/core/bootstrap/`)

**Agent**: `code-fixer-agent`

#### Step 10.3.1: Verify no manual-add needed

The iteration over `builtinForms` auto-invokes `registerMdot1126` once 6.3.2 is merged. Grep and confirm. If there is a per-form manual call site (0582B only), add a parallel call for 1126.

### Sub-phase 10.4: Lint allowlists (if any path rules need new entries)

**Files:**
- Review: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_hardcoded_form_type.dart` and any other path-gated rule

**Agent**: `code-fixer-agent`

#### Step 10.4.1: Add `mdot_1126` to allowlists where `mdot_0582b` already appears

Grep for `'mdot_0582b'` inside `fg_lint_packages/` and mirror every allowlist entry for `'mdot_1126'`.

### Sub-phase 10.6: Asset path cleanup (M2)

**Files:** (grep-driven)

**Agent**: `code-fixer-agent`

#### Step 10.6.1: Migrate any stale `assets/forms/` references

Run: `pwsh -Command "rg --files-with-matches 'assets/forms/' lib"`

For every match, replace `assets/forms/` with `assets/templates/forms/` and
update any companion `pubspec.yaml` declarations. This satisfies spec §10
cleanup. If no matches, document "no migration required" in the commit message.

### Sub-phase 10.7: form_response.entry_id soft-delete cascade verification (M6)

**Files:**
- Modify (if needed): `lib/core/database/schema/inspector_form_tables.dart` (or wherever the form_responses cascade trigger lives)

**Agent**: `code-fixer-agent`

#### Step 10.7.1: Verify or add cascade

Spec §7 row 5 says "existing cascade applies." Verify by grepping for any
SQLite `AFTER UPDATE OF deleted_at ON daily_entries` trigger that propagates
soft-delete to `form_responses WHERE entry_id = OLD.id`. If no such trigger
exists, add one that mirrors the personnel-counts/quantities cascade pattern.
Document the verification result in the commit message.

### Sub-phase 10.5: Final analyze gate

**Files:** (none)

**Agent**: `code-fixer-agent`

#### Step 10.5.1: Full analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues, no new warnings in modified files.

#### Step 10.5.2: Sync adapter validator

Run: `pwsh -Command "python scripts/validate_sync_adapter_registry.py"`
Expected: Pass.

---

## Test Matrix (executed by CI only — NO local `flutter test`)

### Unit

| Test file | Covers |
|---|---|
| `test/features/forms/domain/usecases/build_carry_forward_1126_use_case_test.dart` | carry-forward shape |
| `test/features/forms/data/validators/mdot_1126_validator_test.dart` | missing fields, measure resolution, export gate |
| `test/features/forms/domain/usecases/sign_form_response_use_case_test.dart` | hashes, file + audit insert, stamp, anchor-date persistence (C3), unauth throws (SEC-1126-05), companyId derived from session (SEC-1126-04), PNG hash recorded (SEC-1126-03) |
| `test/features/forms/domain/usecases/invalidate_form_signature_on_edit_use_case_test.dart` | clears audit id idempotently |
| `test/features/forms/domain/usecases/compute_weekly_sesc_reminder_use_case_test.dart` | anchor stability, cadence, archived stop |
| `test/features/forms/data/pdf/mdot_1126_pdf_filler_test.dart` | field map shape |
| `test/features/signatures/data/datasources/local/signature_file_local_datasource_test.dart` | CRUD + soft-delete |
| `test/features/signatures/data/datasources/local/signature_audit_log_local_datasource_test.dart` | CRUD + getByRecord |

### Widget

| Test file | Covers |
|---|---|
| `test/features/forms/presentation/screens/mdot_1126_form_screen_test.dart` | guided step router |
| `test/features/forms/presentation/widgets/sesc_measures_checklist_test.dart` | tri-state + corrective reveal |
| `test/features/forms/presentation/widgets/signature_pad_field_test.dart` | emits PNG bytes |
| `test/features/forms/presentation/widgets/weekly_sesc_reminder_banner_test.dart` | shows only when reminder non-null |
| `test/features/forms/presentation/widgets/weekly_sesc_reminder_card_test.dart` | routes on tap |
| `test/features/forms/presentation/widgets/attach_step_test.dart` | M3: candidate list, override, inline-create branch |
| `test/features/forms/presentation/widgets/weekly_sesc_toolbox_todo_test.dart` | M4: shows when reminder non-null, hides otherwise |

### Integration / Driver

| Test file | Covers |
|---|---|
| `integration_test/mdot_1126_end_to_end_test.dart` | fill → inline-create entry → attach → export bundle contains IDR + 1126 + photos |
| `integration_test/mdot_1126_carry_forward_test.dart` | week 1 → +7 days → week 2 prefill |
| `integration_test/mdot_1126_cadence_test.dart` | same-week extra does not shift due |
| `integration_test/mdot_1126_sync_test.dart` | sign on A → pull on B → audit + PNG retrievable; M5: assert local_path populated and PNG bytes load on device B |
| `integration_test/mdot_1126_edit_after_sign_test.dart` | edit clears signature + blocks export (covers SEC-1126-06 universal hook via repo path) |
| `integration_test/mdot_1126_conflict_test.dart` | M1: two-device same-week sign; ConflictResolver picks LWW without special-casing 1126; both audit rows persist |
| `integration_test/mdot_1126_backdate_test.dart` | H8: backdating wizard inspection_date; reminder still recomputes correctly |

### Schema drift

| Test file | Covers |
|---|---|
| `test/core/database/schema_verifier_drift_test.dart` | already exists — add assertions for the two new tables |

---

## Ground-Truth Cross-Reference

Every identifier used above is verified in `.claude/tailor/2026-04-06-mdot-1126-weekly-sesc/ground-truth.md`. Known flags the implementer must resolve when running this plan:

1. **Schema version**: current = 53 → bump to **54** (NOT 53 as spec literally said).
2. **Asset name**: using `mdot_1126_form.pdf` to match 0582B convention.
3. **`lib/features/signatures/`** is a new feature module — create the directory structure.
4. **Testing keys**: added inline to `testing_keys.dart` (matches 0582B convention).
5. **Design-system component names** — RESOLVED in fixer cycle 1: presentation phases now use `AppSectionCard` (no `AppCard`), `AppBanner({icon,message,severity,actions})`, `AppButton.primary/secondary/ghost/danger`, `AppTextField`, `AppChip` (no `AppSegmented`), `FieldGuideSpacing.of(context)` via the verified `design_system.dart` barrel import.
6. **`WizardActivityTracker`** — RESOLVED: controller uses verified `register({key, label, hasUnsavedChanges})` and `markChanged(key)` / `unregister(key)`.
7. **`DailyEntry` constructor shape** — verified in fixer cycle 1: existing constructor accepts `projectId`, `date`, optional `createdByUserId`. `CreateInspectionDateEntryUseCase` already matches.
8. **`Icons.water_drop`** — RESOLVED: registrations and widgets use `Icons.water_drop` directly (no `AppIcons.rain` lookup).
9. **Supabase helpers** — RESOLVED: migration uses verified `get_my_company_id()` / `is_viewer()` from `20260222100000_multi_tenant_foundation.sql`. The mythical `is_user_in_company` / `company_users` references are gone.

---

## Done Definition

- [ ] All 10 phases complete, `flutter analyze` green
- [ ] Sync adapter validator green
- [ ] CI green (unit + widget + integration tests the CI runner executes)
- [ ] Schema v54 applied locally and on Supabase staging
- [ ] Signature storage bucket exists with RLS policies active
- [ ] Inspector can fill 1126 from forms hub, sign, attach to entry, export bundle
- [ ] Weekly reminder appears on dashboard / entry banner / toolbox when cycle due, disappears after fill, stops when project archived
- [ ] All 9 "Ground-Truth Cross-Reference" flags resolved in-commit

---

## Fixer Cycle 1 Summary (2026-04-07)

Surgical edits applied in response to code-review, security-review, and
completeness-review cycle 1. All findings addressed unless explicitly noted.

### Code Review (cycle 1) — fixed

| Finding | Resolution |
|---|---|
| AppCard usage in 7.3.1 / 7.3.2 / 7.3.4 / 7.4.2 / 9.3.1 | Replaced with `AppSectionCard` (organisms) — taps surfaced via inner `ListTile.onTap` |
| AppButton.tertiary in SignaturePadField | Replaced with `AppButton.ghost` |
| AppSegmented in SescMeasuresChecklist | Replaced with three `AppChip` selection chips |
| AppBanner(title:, subtitle:, onTap:) | Rewritten to verified API: `icon`, `message`, `severity: AppBannerSeverity.warning`, `actions: [AppButton.ghost]` |
| FieldGuideSpacing.of(context) accessor | Verified — already canonical (preserved) |
| Bad import paths (layout/spacing.dart, molecules/app_card.dart) | Replaced with `package:construction_inspector/core/design_system/design_system.dart` barrel |
| AppIcons.rain reference | Replaced with `Icons.water_drop` |
| FormQuickAction.execute signature | Fixed to `(response) => const FormQuickActionResult.navigate(...)` |
| builtinForms redeclared | Phase 6.3.2 now edits the existing list literal in place |
| SchemaVerifier expectedSchema shape | Rewritten as `Map<String, List<String>>` plus `_columnTypes` non-TEXT entries |
| WizardActivityTracker API mismatch | Controller now uses `register({key,label,hasUnsavedChanges})`, `markChanged(key)`, `unregister(key)` |
| ExportBlockedException undefined | New Sub-phase 8.0 creates the file |
| Phase 7.5 _build<Step> stubs | Replaced with concrete bodies wired to InspectorFormProvider, FormPdfService, SignFormResponseUseCase |
| Phase 7.7 hook location unverified | Path verified; hook moved into FormResponseRepositoryImpl.update() per SEC-1126-06 |
| 5th file for schema changes | Added `test/helpers/sync/sync_test_data.dart` to Sub-phase 2.4 file list |
| Phase 2.4 brittle line citations (:587, :152) | Removed |
| LoadPrior1126UseCase docstring drift | Now filters to signed-only and docstring matches |
| stripExifGps misleading PNG comment | Corrected |
| matches.first vs matches.firstOrNull | Switched to `firstOrNull` |

### Security Review (cycle 1) — fixed

| Finding | Resolution |
|---|---|
| SEC-1126-01 RLS rewrites | Per-operation policies derived from `projects WHERE company_id = get_my_company_id()` + `NOT is_viewer()` on writes; `is_user_in_company` / `company_users` removed |
| SEC-1126-02 storage bucket path | Path now `signatures/$companyId/$projectId/$id.png`; policies use `(storage.foldername(name))[2]` and SELECT/INSERT/UPDATE/DELETE all gated |
| SEC-1126-03 audit immutability | Added `signature_png_sha256` column; Postgres + SQLite `BEFORE UPDATE` triggers block changes to all signed columns; FK changed to `ON DELETE RESTRICT` |
| SEC-1126-04 client-supplied company_id | `companyId` removed from `SignatureContext`; derived from `SessionService` inside use case; server `BEFORE INSERT` trigger overrides `NEW.company_id := get_my_company_id()` |
| SEC-1126-05 auth assertion | `SignFormResponseUseCase` now injects `SessionService` and asserts `currentUser != null`; server trigger sets `NEW.user_id := auth.uid()`; unit test row added |
| SEC-1126-06 universal invalidation | Hook moved into `FormResponseRepositoryImpl.update()` so background sync, conflict resolution, and any future write paths invalidate too |
| SEC-1126-07 PNG storage | Retained file-adapter path with explicit rationale (sync round-trip already wired). 512 KB size + image/png MIME bucket limits added (SEC-1126-11) so the tradeoff is bounded. SKIPPED full BLOB migration — out of scope for cycle 1, would invalidate the entire Phase 4.1 design; flagged for next sprint. |
| SEC-1126-08 GPS consent gate | New `SignatureContextProvider` reads opt-in `signature_capture_gps` setting + permission; consent row written to `user_consent_records` |
| SEC-1126-09 device_id generation | Documented as per-install random UUID in `flutter_secure_storage`, never hardware-derived; server validates `length <= 64` |
| SEC-1126-10 sha256 immutability | Covered by SEC-1126-03 immutability triggers |
| SEC-1126-11 bucket quota / MIME | Bucket INSERT now sets `file_size_limit = 524288` and `allowed_mime_types = ARRAY['image/png']` |
| SEC-1126-12 realtime PII | `signature_audit_log` removed from `supabase_realtime`; only `signature_files` published |

### Completeness Review (cycle 1) — fixed

| Finding | Resolution |
|---|---|
| C1 embed signature in flattened PDF | `SignFormResponseUseCase` now calls `FormPdfService.embedSignaturePng` before hashing; Phase 6.2 spike updated to add the method |
| C2 carry-forward orchestration | New Sub-phase 6.4 adds `createMdot1126Response` that branches on prior existence; router handler wires it |
| C3 weekly_cycle_anchor_date persistence | `SignFormResponseUseCase` patches `weekly_cycle_anchor_date := inspection_date` on first signed 1126 for the project |
| H1 first-week initial data keys | `FormInitialDataFactory` callback expanded with `header`, `report_number`, `inspection_date` (today ISO), `date_of_last_inspection`, `rainfall_events`, `measures`, `signature_audit_id`, `weekly_cycle_anchor_date` |
| H2 rolling 7-day date range | Phase 6.2 spike now records whether `date_range_start/end` fields exist; documented fallback to `inspection_date` + `date_of_last_inspection` |
| H3 reactive reminder | New `SescReminderProvider` (Sub-phase 9.0); dashboard, banner, and toolbox widgets switched from FutureBuilder to `Consumer<SescReminderProvider>` |
| H4 universal invalidation | Same fix as SEC-1126-06 |
| H5 auth assertion | Same fix as SEC-1126-05 |
| H6 inspector_form server seed | `INSERT INTO public.inspector_forms (..., is_builtin) VALUES ('mdot_1126', ..., true) ON CONFLICT DO NOTHING` added to the migration |
| H7 empty-measures step skip | Wizard step router auto-redirects measuresReview→addMeasures when measures is empty |
| H8 backdating + inspection-date picker | Wizard rainfall step now exposes a date-picker tile that defaults to current inspection_date and allows free backdating; integration test row added |
| H9 ExportBlockedException | New Sub-phase 8.0 |
| M1 two-device conflict test | Added `integration_test/mdot_1126_conflict_test.dart` to matrix |
| M2 assets/forms cleanup | New Sub-phase 10.6 grep + migrate |
| M3 attach-step list + widget test | `Resolve1126AttachmentEntryUseCase.listCandidates` added; new `attach_step.dart` widget (Step 7.3.5); widget test row in matrix |
| M4 toolbox widget extraction | New `weekly_sesc_toolbox_todo.dart` widget; widget test row in matrix |
| M5 file sync round-trip verification | `mdot_1126_sync_test.dart` matrix entry expanded to assert local_path populated and PNG bytes load on device B |
| M6 form_response cascade verification | New Sub-phase 10.7 |
| L1 platform CHECK constraint | Tightened to `('android','ios','windows')` in both Phase 2.1 and 4.3.1 |
| L2 ground-truth flags 5/6/7 | Resolved (see Ground-Truth Cross-Reference table — flags 5/6/7/8/9 marked RESOLVED) |
| L3 asset commit reminder | Phase 1.1.2 now requires `git add` of the PDF in the same commit |

### Findings skipped

- **SEC-1126-07 (BLOB conversion)** — Recommended migration to a BLOB
  column on `signature_files` (dropping the file adapter entirely) is not
  applied. Rationale: it would invalidate the entire Phase 3 / Phase 4.1
  data layer (file adapter, storage bucket, _buildSignatureFilePath). The
  bounded mitigation (SEC-1126-11 size + MIME caps, SEC-1126-02 corrected
  bucket policies, SEC-1126-03 immutability) addresses the practical
  attack surface for cycle 1. Flagged for security re-audit next sprint.
- **SEC-1126-13 (HMAC vs SHA-256 rationale)** — LOW; covered by inline
  WHY comment in `SignFormResponseUseCase` body which documents the
  hash + RLS + `auth.uid()` bind. No further action required this cycle.

### Files added/modified by this fix pass

- `.claude/plans/2026-04-06-mdot-1126-weekly-sesc.md` — surgical edits to Phases 1.1.2, 2.1, 2.2.x, 2.3.1, 2.4, 4.1.1, 4.3.1, 5.2.1, 5.3.1, 5.4.1, 6.2.1, 6.3.1, 6.3.2, 6.4 (new), 7.2.1, 7.3.1, 7.3.2, 7.3.4, 7.3.5 (new), 7.4.1, 7.4.2, 7.5, 7.7, 8.0 (new), 9.0 (new), 9.1, 9.2, 9.3, 10.1.1, 10.6 (new), 10.7 (new), test matrix, ground-truth cross-reference
- `.claude/plans/review_sweeps/mdot-1126-weekly-sesc-2026-04-07/code-review-cycle-1.md` — header status note added

---

## Fixer Cycle 2 Summary (2026-04-07)

Single-pass surgical follow-up after re-verifying actual atom APIs against
`lib/core/design_system/atoms/app_chip.dart` and the
`FormResponseRepository` interface.

### Fixes applied

| # | Phase / Step | Issue | Fix |
|---|---|---|---|
| 1 | 7.3.2 `SescMeasuresChecklist` | `AppChip(label:, selected:, onSelected:)` does not exist on the verified `AppChip` constructor (atoms/app_chip.dart:16-32). Only `label`/`backgroundColor`/`foregroundColor`/`icon`/`onTap`/`onDeleted` are accepted. | Rewrote the tri-state row to use the verified named factories: `AppChip.cyan` for `in_place` selected, `AppChip.amber` for `needs_action` selected, `AppChip.error` for `removed` selected, and `AppChip.neutral(context: context, ...)` for unselected. Tap routed via `onTap`. Behavior identical (tri-state + corrective-action reveal). Updated the trailing NOTE to reflect the verified API. |
| 2 | 7.5 `Mdot1126FormScreen` imports | `const Uuid().v4()` is used in the add-measures step body without importing the `uuid` package. | Added `import 'package:uuid/uuid.dart';` to the screen import block with a `FIXER CYCLE 2` rationale comment. |
| 3 | 7.7 `FormResponseRepositoryImpl.update()` | Code review flagged the `getById` unwrap as unverified. | Verified at `lib/features/forms/domain/repositories/form_response_repository.dart:41`: the `BaseRepository<FormResponse>` override `getById(String id)` returns `Future<FormResponse?>` directly (the `RepositoryResult`-wrapped variant is `getResponseById`). No unwrap is required. Replaced the loose `final priorResult = await ...; final prior = priorResult;` pair with an explicitly typed `final FormResponse? prior = await getById(response.id);` plus a verification comment so future readers do not regress it. |

### Findings skipped

None — all three findings in cycle 2 were addressable with surgical edits to existing plan content.
