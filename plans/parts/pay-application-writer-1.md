## Phase 1: Database Schema & Migration

### Sub-phase 1.1: Create export_artifact_tables.dart schema file

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/core/database/schema/export_artifact_tables.dart`

#### Step 1.1.1: Create the schema file with CREATE TABLE statements and indexes

Create the schema file following the `EntryExportTables` pattern (see `lib/core/database/schema/entry_export_tables.dart`). This file defines two tables: `export_artifacts` (the unified export history parent) and `pay_applications` (pay-app-specific child).

```dart
// lib/core/database/schema/export_artifact_tables.dart

// WHY: Schema files are pure static SQL strings with no imports.
// FROM SPEC: Section 2 "Data Model" defines ExportArtifact + PayApplication entities.
// NOTE: Follows EntryExportTables pattern — static const SQL + static const indexes.

class ExportArtifactTables {
  // FROM SPEC: ExportArtifact is the unified parent for all exported artifacts.
  // Fields: id, project_id, artifact_type, artifact_subtype, source_record_id,
  // title, filename, local_path, remote_path, mime_type, status,
  // created_at, updated_at, created_by_user_id, deleted_at, deleted_by.
  static const String createExportArtifactsTable = '''
    CREATE TABLE IF NOT EXISTS export_artifacts (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      artifact_type TEXT NOT NULL,
      artifact_subtype TEXT,
      source_record_id TEXT,
      title TEXT NOT NULL,
      filename TEXT NOT NULL,
      local_path TEXT,
      remote_path TEXT,
      mime_type TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'exported',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
  ''';

  // FROM SPEC: PayApplication child entity — one row per saved exported pay app.
  // Fields: id, export_artifact_id, project_id, application_number,
  // period_start, period_end, previous_application_id,
  // total_contract_amount, total_earned_this_period, total_earned_to_date,
  // notes, created_at, updated_at, created_by_user_id, deleted_at, deleted_by.
  // FROM SPEC: Unique constraint on (project_id, period_start, period_end) for
  // exact-range identity. Unique constraint on (project_id, application_number)
  // for pay-app number uniqueness.
  static const String createPayApplicationsTable = '''
    CREATE TABLE IF NOT EXISTS pay_applications (
      id TEXT PRIMARY KEY,
      export_artifact_id TEXT NOT NULL,
      project_id TEXT NOT NULL,
      application_number INTEGER NOT NULL,
      period_start TEXT NOT NULL,
      period_end TEXT NOT NULL,
      previous_application_id TEXT,
      total_contract_amount REAL NOT NULL,
      total_earned_this_period REAL NOT NULL,
      total_earned_to_date REAL NOT NULL,
      notes TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (export_artifact_id) REFERENCES export_artifacts(id) ON DELETE CASCADE,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
      FOREIGN KEY (previous_application_id) REFERENCES pay_applications(id) ON DELETE SET NULL
    )
  ''';

  // NOTE: Index all FK columns and deleted_at per schema-patterns.md.
  // IMPORTANT: Unique indexes include deleted_at IS NULL filter so soft-deleted
  // rows do not block new rows with the same range or number.
  static const List<String> indexes = [
    'CREATE INDEX IF NOT EXISTS idx_export_artifacts_project ON export_artifacts(project_id)',
    'CREATE INDEX IF NOT EXISTS idx_export_artifacts_type ON export_artifacts(artifact_type)',
    'CREATE INDEX IF NOT EXISTS idx_export_artifacts_deleted_at ON export_artifacts(deleted_at)',
    'CREATE INDEX IF NOT EXISTS idx_pay_applications_project ON pay_applications(project_id)',
    'CREATE INDEX IF NOT EXISTS idx_pay_applications_artifact ON pay_applications(export_artifact_id)',
    'CREATE INDEX IF NOT EXISTS idx_pay_applications_previous ON pay_applications(previous_application_id)',
    'CREATE INDEX IF NOT EXISTS idx_pay_applications_deleted_at ON pay_applications(deleted_at)',
    // FROM SPEC: "Unique constraint on pay-app range identity: one saved pay app
    // per exact project_id + period_start + period_end"
    // WHY: SQLite partial unique index — only enforced for non-deleted rows.
    '''CREATE UNIQUE INDEX IF NOT EXISTS idx_pay_applications_range
       ON pay_applications(project_id, period_start, period_end)
       WHERE deleted_at IS NULL''',
    // FROM SPEC: "Number must remain unique within the project"
    '''CREATE UNIQUE INDEX IF NOT EXISTS idx_pay_applications_number
       ON pay_applications(project_id, application_number)
       WHERE deleted_at IS NULL''',
  ];
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/core/database/schema/export_artifact_tables.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 1.2: Register schema in barrel export

**Agent**: `code-fixer-agent`

**Files:**
- Modify: `lib/core/database/schema/schema.dart:21` (add export)

#### Step 1.2.1: Add export for export_artifact_tables.dart

Add the new export to `lib/core/database/schema/schema.dart` after line 21 (after `export 'support_tables.dart';`).

```dart
// Add after line 21:
export 'export_artifact_tables.dart';
```

The file should end with:
```dart
export 'consent_tables.dart';
export 'support_tables.dart';
export 'export_artifact_tables.dart';
```

**Verification:**
```
pwsh -Command "flutter analyze lib/core/database/schema/schema.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 1.3: Add table creation to DatabaseService._onCreate

**Agent**: `code-fixer-agent`

**Files:**
- Modify: `lib/core/database/database_service.dart:205` (add table creation in _onCreate)

#### Step 1.3.1: Add export_artifacts and pay_applications table creation

In `_onCreate` at `lib/core/database/database_service.dart`, insert the following after line 205 (after `await db.execute(SupportTables.createSupportTicketsTable);`) and before the `sync_metadata` table creation (line 208):

```dart
    // Export artifact tables (v52)
    // FROM SPEC: Unified export history layer + pay application child table.
    await db.execute(ExportArtifactTables.createExportArtifactsTable);
    await db.execute(ExportArtifactTables.createPayApplicationsTable);
```

WHY: Fresh installs create all tables in `_onCreate`. Existing installs use `_onUpgrade` (Step 1.5.1).
NOTE: Insert BEFORE sync_metadata and sync engine tables because export_artifacts has FK to projects only (already created), and pay_applications has FK to export_artifacts (just created).

**Verification:**
```
pwsh -Command "flutter analyze lib/core/database/database_service.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 1.4: Add indexes to DatabaseService._createIndexes

**Agent**: `code-fixer-agent`

**Files:**
- Modify: `lib/core/database/database_service.dart:305-307` (add index loop in _createIndexes)

#### Step 1.4.1: Add index creation loop for export artifact tables

In `_createIndexes` at `lib/core/database/database_service.dart`, insert the following after line 306 (after the `SupportTables.indexes` loop, before the closing `}` of `_createIndexes`):

```dart
    // Export artifact indexes (v52)
    for (final index in ExportArtifactTables.indexes) {
      await db.execute(index);
    }
```

**Verification:**
```
pwsh -Command "flutter analyze lib/core/database/database_service.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 1.5: Add migration v51->v52 in _onUpgrade and bump version

**Agent**: `code-fixer-agent`

**Files:**
- Modify: `lib/core/database/database_service.dart:69` (version bump to 52)
- Modify: `lib/core/database/database_service.dart:107` (version bump to 52 in in-memory)
- Modify: `lib/core/database/database_service.dart:2149` (add migration block after v51)

#### Step 1.5.1: Add version 52 migration block

Add the following migration block after line 2149 (after the closing `}` of the `if (oldVersion < 51)` block):

```dart
    // FROM SPEC: v52 — Export artifacts + pay applications tables
    // WHY: Unified export history layer (ExportArtifact) + pay application child.
    if (oldVersion < 52) {
      // Create export_artifacts table
      await db.execute(ExportArtifactTables.createExportArtifactsTable);
      // Create pay_applications table
      await db.execute(ExportArtifactTables.createPayApplicationsTable);

      // Create indexes
      for (final index in ExportArtifactTables.indexes) {
        await db.execute(index);
      }

      // Install change_log triggers for new synced tables
      for (final table in ['export_artifacts', 'pay_applications']) {
        for (final trigger in SyncEngineTables.triggersForTable(table)) {
          await db.execute(trigger);
        }
      }

      Logger.db(
        'Migration v52: created export_artifacts + pay_applications tables with triggers',
      );
    }
```

#### Step 1.5.2: Bump database version from 51 to 52

At `lib/core/database/database_service.dart:69`, change:
```dart
      version: 51,
```
to:
```dart
      version: 52,
```

At `lib/core/database/database_service.dart:107`, change:
```dart
      version: 51,
```
to:
```dart
      version: 52,
```

**Verification:**
```
pwsh -Command "flutter analyze lib/core/database/database_service.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 1.6: Register tables in SyncEngineTables

**Agent**: `code-fixer-agent`

**Files:**
- Modify: `lib/core/database/schema/sync_engine_tables.dart:155-156` (add to triggeredTables)
- Modify: `lib/core/database/schema/sync_engine_tables.dart:168-169` (add to tablesWithDirectProjectId)

#### Step 1.6.1: Add to triggeredTables

At `lib/core/database/schema/sync_engine_tables.dart:155`, add the two new tables before the closing `];` of `triggeredTables` (after `'user_consent_records'` on line 155):

```dart
    'export_artifacts',
    'pay_applications',
```

The end of the list becomes:
```dart
    'support_tickets',
    'user_consent_records',
    'export_artifacts',
    'pay_applications',
  ];
```

WHY: Tables in `triggeredTables` get INSERT/UPDATE/DELETE triggers that populate `change_log` for sync. Both new tables must be synced.
NOTE: The list comment says "22 tables" -- update to "24 tables" in the comment on line 132.

#### Step 1.6.2: Add to tablesWithDirectProjectId

At `lib/core/database/schema/sync_engine_tables.dart:168`, add the two new tables. Both `export_artifacts` and `pay_applications` have a direct `project_id` column.

The list becomes:
```dart
  static const List<String> tablesWithDirectProjectId = [
    'project_assignments', 'locations', 'contractors', 'bid_items',
    'personnel_types', 'daily_entries', 'photos', 'todo_items',
    'entry_contractors', 'entry_quantities', 'entry_equipment',
    'documents', 'entry_exports', 'form_exports',
    'export_artifacts', 'pay_applications',
  ];
```

WHY: Tables with direct `project_id` produce `NEW.project_id` in change_log triggers. Without this, the triggers would produce NULL project_id, breaking project-scoped sync.

**Verification:**
```
pwsh -Command "flutter analyze lib/core/database/schema/sync_engine_tables.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 1.7: Update SchemaVerifier _columnTypes

**Agent**: `code-fixer-agent`

**Files:**
- Modify: `lib/core/database/schema_verifier.dart` (add entries to both `_expectedColumns` and `_columnTypes`)

#### Step 1.7.1: Add _expectedColumns entries for new tables

In `lib/core/database/schema_verifier.dart`, add entries to the `_expectedColumns` map. Insert after the `'entry_exports'` block (around line 251) and before the `'documents'` block:

```dart
    // ---- Export artifact tables (v52) ----
    'export_artifacts': [
      'id', 'project_id', 'artifact_type', 'artifact_subtype',
      'source_record_id', 'title', 'filename', 'local_path',
      'remote_path', 'mime_type', 'status',
      'created_at', 'updated_at', 'created_by_user_id',
      'deleted_at', 'deleted_by',
    ],
    'pay_applications': [
      'id', 'export_artifact_id', 'project_id', 'application_number',
      'period_start', 'period_end', 'previous_application_id',
      'total_contract_amount', 'total_earned_this_period',
      'total_earned_to_date', 'notes',
      'created_at', 'updated_at', 'created_by_user_id',
      'deleted_at', 'deleted_by',
    ],
```

#### Step 1.7.2: Add _columnTypes entries for new tables

In `lib/core/database/schema_verifier.dart`, add entries to the `_columnTypes` map (after the `'user_consent_records'` block around line 432, before the closing `};`):

```dart
    'export_artifacts': {
      'status': "TEXT NOT NULL DEFAULT 'exported'",
    },
    'pay_applications': {
      'application_number': 'INTEGER NOT NULL',
      'total_contract_amount': 'REAL NOT NULL',
      'total_earned_this_period': 'REAL NOT NULL',
      'total_earned_to_date': 'REAL NOT NULL',
    },
```

WHY: SchemaVerifier catches migration drift. If a column type changes, the verifier reports it. Default types (TEXT) do not need entries -- only non-TEXT types and types with DEFAULT clauses.

**Verification:**
```
pwsh -Command "flutter analyze lib/core/database/schema_verifier.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 1.8: Add sync adapter configs for new tables

**Agent**: `code-fixer-agent`

**Files:**
- Modify: `lib/features/sync/adapters/simple_adapters.dart:177-178` (add 2 AdapterConfig entries)
- Modify: `lib/features/sync/engine/sync_registry.dart:47-48` (add 2 adapter registrations)

#### Step 1.8.1: Add AdapterConfig entries for export_artifacts and pay_applications

At `lib/features/sync/adapters/simple_adapters.dart`, insert the following before the closing `];` on line 178 (after the `form_exports` AdapterConfig):

```dart

  // FROM SPEC: export_artifacts — file-aware, project-scoped.
  // WHY: Unified export history parent. isFileAdapter=true because the
  // exported file (xlsx/pdf) syncs through the file-sync pipeline.
  // localOnlyColumns: local_path is device-specific, stripped on push.
  AdapterConfig(
    table: 'export_artifacts',
    scope: ScopeType.viaProject,
    fkDeps: ['projects'],
    fkColumnMap: {'projects': 'project_id'},
    localOnlyColumns: ['local_path'],
    isFileAdapter: true,
    storageBucket: 'export-artifacts',
    buildStoragePath: _buildExportArtifactPath,
    extractRecordName: _extractExportArtifactName,
  ),

  // FROM SPEC: pay_applications — data-only, project-scoped.
  // WHY: Child of export_artifacts. No file attachment — the file
  // lives on the parent export_artifacts row.
  // NOTE: previous_application_id is self-referential FK. Pull ordering
  // handles this because all pay_applications for a project pull together.
  AdapterConfig(
    table: 'pay_applications',
    scope: ScopeType.viaProject,
    fkDeps: ['export_artifacts', 'projects'],
    fkColumnMap: {
      'export_artifacts': 'export_artifact_id',
      'projects': 'project_id',
    },
  ),
```

Also add the two helper functions at the bottom of the file (after `_extractExportRecordName` or the last existing helper):

```dart
/// Build storage path for export artifact files.
/// Pattern: {projectId}/export-artifacts/{filename}
String _buildExportArtifactPath(Map<String, dynamic> record) {
  final projectId = record['project_id'] as String? ?? 'unknown';
  final filename = record['filename'] as String? ?? 'unknown';
  return '$projectId/export-artifacts/$filename';
}

/// Extract display name from export artifact record.
String _extractExportArtifactName(Map<String, dynamic> record) {
  return record['title'] as String? ?? record['filename'] as String? ?? 'Export';
}
```

#### Step 1.8.2: Register new adapters in sync_registry.dart

At `lib/features/sync/engine/sync_registry.dart`, insert the two new adapters after `simpleByTable['form_exports']!` (line 47) and before `simpleByTable['entry_exports']!` (line 48):

```dart
    simpleByTable['export_artifacts']!,          // NEW: unified export history parent
    simpleByTable['pay_applications']!,          // NEW: pay application child
```

The registration order becomes:
```dart
    simpleByTable['form_exports']!,           // was: FormExportAdapter()
    simpleByTable['export_artifacts']!,       // NEW: unified export history parent
    simpleByTable['pay_applications']!,       // NEW: pay application child
    simpleByTable['entry_exports']!,          // was: EntryExportAdapter()
```

WHY: FK dependency order is load-bearing. `export_artifacts` depends only on `projects` (already registered). `pay_applications` depends on `export_artifacts` (just registered). Both must come before any table that might reference them.

IMPORTANT: The `simpleAdapters` list count in the doc comment at line 5 says "13 simple table adapters" -- update to "15 simple table adapters".

**Verification:**
```
pwsh -Command "flutter analyze lib/features/sync/adapters/simple_adapters.dart"
pwsh -Command "flutter analyze lib/features/sync/engine/sync_registry.dart"
```
Expected: No analysis issues found for either file.

---

### Sub-phase 1.9: Schema verification tests

**Agent**: `qa-testing-agent`

**Files:**
- Modify: `test/core/database/schema_verifier_test.dart` (add assertions for new tables)
- Modify: `test/core/database/database_service_test.dart` (add migration test)

#### Step 1.9.1: Add schema_verifier_test assertions for export_artifacts and pay_applications

Add test cases to `test/core/database/schema_verifier_test.dart` that verify the two new tables appear in `_expectedColumns` and have correct column counts. Follow the pattern of existing table assertions in that file.

The test should verify:
- `export_artifacts` has 16 columns: id, project_id, artifact_type, artifact_subtype, source_record_id, title, filename, local_path, remote_path, mime_type, status, created_at, updated_at, created_by_user_id, deleted_at, deleted_by
- `pay_applications` has 16 columns: id, export_artifact_id, project_id, application_number, period_start, period_end, previous_application_id, total_contract_amount, total_earned_this_period, total_earned_to_date, notes, created_at, updated_at, created_by_user_id, deleted_at, deleted_by

#### Step 1.9.2: Add database_service_test for v52 migration

Add a test to `test/core/database/database_service_test.dart` that verifies the v52 migration creates both tables and their indexes on an existing v51 database. Follow the pattern of existing migration tests in that file.

**Verification:**
CI handles all test execution. Local gate:
```
pwsh -Command "flutter analyze test/core/database/"
```
Expected: No analysis issues found.

---

## Phase 2: Export Artifact Data Layer

### Sub-phase 2.1: Create ExportArtifact model

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/features/pay_applications/data/models/export_artifact.dart`

#### Step 2.1.1: Create ExportArtifact data model

Follow the `EntryExport` pattern (`lib/features/entries/data/models/entry_export.dart`). String timestamps (ISO 8601), UUID default, sentinel copyWith, toMap/fromMap.

```dart
// lib/features/pay_applications/data/models/export_artifact.dart

import 'package:uuid/uuid.dart';

// FROM SPEC: Section 2 "Data Model" — ExportArtifact is the unified parent
// for all exported artifacts (entry PDFs, form PDFs, pay applications, etc.).
// NOTE: Follows EntryExport pattern — String timestamps, UUID default, sentinel copyWith.
class ExportArtifact {
  final String id;
  final String projectId;
  final String artifactType;
  final String? artifactSubtype;
  final String? sourceRecordId;
  final String title;
  final String filename;
  final String? localPath;
  final String? remotePath;
  final String mimeType;
  final String status;
  final String createdAt;
  final String updatedAt;
  final String? createdByUserId;
  final String? deletedAt;
  final String? deletedBy;

  ExportArtifact({
    String? id,
    required this.projectId,
    required this.artifactType,
    this.artifactSubtype,
    this.sourceRecordId,
    required this.title,
    required this.filename,
    this.localPath,
    this.remotePath,
    required this.mimeType,
    String? status,
    String? createdAt,
    String? updatedAt,
    this.createdByUserId,
    this.deletedAt,
    this.deletedBy,
  })  : id = id ?? const Uuid().v4(),
        status = status ?? 'exported',
        createdAt = createdAt ?? DateTime.now().toUtc().toIso8601String(),
        updatedAt = updatedAt ?? DateTime.now().toUtc().toIso8601String();

  static const _sentinel = Object();

  ExportArtifact copyWith({
    Object? id = _sentinel,
    Object? projectId = _sentinel,
    Object? artifactType = _sentinel,
    Object? artifactSubtype = _sentinel,
    Object? sourceRecordId = _sentinel,
    Object? title = _sentinel,
    Object? filename = _sentinel,
    Object? localPath = _sentinel,
    Object? remotePath = _sentinel,
    Object? mimeType = _sentinel,
    Object? status = _sentinel,
    Object? createdAt = _sentinel,
    Object? updatedAt = _sentinel,
    Object? createdByUserId = _sentinel,
    Object? deletedAt = _sentinel,
    Object? deletedBy = _sentinel,
  }) {
    return ExportArtifact(
      id: identical(id, _sentinel) ? this.id : id as String?,
      projectId: identical(projectId, _sentinel) ? this.projectId : projectId! as String,
      artifactType: identical(artifactType, _sentinel) ? this.artifactType : artifactType! as String,
      artifactSubtype: identical(artifactSubtype, _sentinel) ? this.artifactSubtype : artifactSubtype as String?,
      sourceRecordId: identical(sourceRecordId, _sentinel) ? this.sourceRecordId : sourceRecordId as String?,
      title: identical(title, _sentinel) ? this.title : title! as String,
      filename: identical(filename, _sentinel) ? this.filename : filename! as String,
      localPath: identical(localPath, _sentinel) ? this.localPath : localPath as String?,
      remotePath: identical(remotePath, _sentinel) ? this.remotePath : remotePath as String?,
      mimeType: identical(mimeType, _sentinel) ? this.mimeType : mimeType! as String,
      status: identical(status, _sentinel) ? this.status : status as String?,
      createdAt: identical(createdAt, _sentinel) ? this.createdAt : createdAt as String?,
      updatedAt: identical(updatedAt, _sentinel) ? this.updatedAt : updatedAt as String?,
      createdByUserId: identical(createdByUserId, _sentinel) ? this.createdByUserId : createdByUserId as String?,
      deletedAt: identical(deletedAt, _sentinel) ? this.deletedAt : deletedAt as String?,
      deletedBy: identical(deletedBy, _sentinel) ? this.deletedBy : deletedBy as String?,
    );
  }

  Map<String, dynamic> toMap() => {
    'id': id,
    'project_id': projectId,
    'artifact_type': artifactType,
    'artifact_subtype': artifactSubtype,
    'source_record_id': sourceRecordId,
    'title': title,
    'filename': filename,
    'local_path': localPath,
    'remote_path': remotePath,
    'mime_type': mimeType,
    'status': status,
    'created_at': createdAt,
    'updated_at': updatedAt,
    'created_by_user_id': createdByUserId,
    'deleted_at': deletedAt,
    'deleted_by': deletedBy,
  };

  factory ExportArtifact.fromMap(Map<String, dynamic> map) => ExportArtifact(
    id: map['id'] as String,
    projectId: map['project_id'] as String,
    artifactType: map['artifact_type'] as String,
    artifactSubtype: map['artifact_subtype'] as String?,
    sourceRecordId: map['source_record_id'] as String?,
    title: map['title'] as String,
    filename: map['filename'] as String,
    localPath: map['local_path'] as String?,
    remotePath: map['remote_path'] as String?,
    mimeType: map['mime_type'] as String,
    status: map['status'] as String,
    createdAt: map['created_at'] as String,
    updatedAt: map['updated_at'] as String,
    createdByUserId: map['created_by_user_id'] as String?,
    deletedAt: map['deleted_at'] as String?,
    deletedBy: map['deleted_by'] as String?,
  );
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/data/models/export_artifact.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 2.2: Create ExportArtifactLocalDatasource

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/features/pay_applications/data/datasources/local/export_artifact_local_datasource.dart`

#### Step 2.2.1: Create the local datasource extending ProjectScopedDatasource

Follow `FormExportLocalDatasource` pattern (`lib/features/forms/data/datasources/local/form_export_local_datasource.dart`).

```dart
// lib/features/pay_applications/data/datasources/local/export_artifact_local_datasource.dart

import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/shared/datasources/project_scoped_datasource.dart';
import 'package:construction_inspector/features/pay_applications/data/models/export_artifact.dart';

// WHY: Follows ProjectScopedDatasource pattern — export_artifacts has project_id.
// NOTE: Inherits getByProjectId, getByProjectIdPaged, getCountByProject,
// softDeleteByProjectId, getDeletedByProjectId from ProjectScopedDatasource.
class ExportArtifactLocalDatasource extends ProjectScopedDatasource<ExportArtifact> {
  @override
  final DatabaseService db;

  ExportArtifactLocalDatasource(this.db);

  @override
  String get tableName => 'export_artifacts';

  @override
  String get defaultOrderBy => 'created_at DESC';

  @override
  ExportArtifact fromMap(Map<String, dynamic> map) => ExportArtifact.fromMap(map);

  @override
  Map<String, dynamic> toMap(ExportArtifact item) => item.toMap();

  @override
  String getId(ExportArtifact item) => item.id;

  // FROM SPEC: ExportArtifactProvider.getByType — filter by artifact_type.
  // WHY: The exported Forms history surface filters by type.
  Future<List<ExportArtifact>> getByType(String projectId, String artifactType) async {
    final database = await db.database;
    final results = await database.query(
      tableName,
      where: 'project_id = ? AND artifact_type = ? AND deleted_at IS NULL',
      whereArgs: [projectId, artifactType],
      orderBy: defaultOrderBy,
    );
    return results.map(fromMap).toList();
  }

  // WHY: Retrieve all artifacts for a project, optionally filtered by multiple types.
  Future<List<ExportArtifact>> getByTypes(String projectId, List<String> types) async {
    if (types.isEmpty) return getByProjectId(projectId);
    final database = await db.database;
    final placeholders = List.filled(types.length, '?').join(', ');
    final results = await database.query(
      tableName,
      where: 'project_id = ? AND artifact_type IN ($placeholders) AND deleted_at IS NULL',
      whereArgs: [projectId, ...types],
      orderBy: defaultOrderBy,
    );
    return results.map(fromMap).toList();
  }

  // WHY: Look up a specific artifact by its source record (e.g., find
  // the export artifact for a specific pay application).
  Future<ExportArtifact?> getBySourceRecordId(String sourceRecordId) async {
    final database = await db.database;
    final results = await database.query(
      tableName,
      where: 'source_record_id = ? AND deleted_at IS NULL',
      whereArgs: [sourceRecordId],
      limit: 1,
    );
    return results.isEmpty ? null : fromMap(results.first);
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/data/datasources/local/export_artifact_local_datasource.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 2.3: Create ExportArtifactRemoteDatasource

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/features/pay_applications/data/datasources/remote/export_artifact_remote_datasource.dart`

#### Step 2.3.1: Create the remote datasource extending BaseRemoteDatasource

Follow `FormExportRemoteDatasource` pattern (`lib/features/forms/data/datasources/remote/form_export_remote_datasource.dart`).

```dart
// lib/features/pay_applications/data/datasources/remote/export_artifact_remote_datasource.dart

import 'package:construction_inspector/shared/datasources/base_remote_datasource.dart';
import 'package:construction_inspector/features/pay_applications/data/models/export_artifact.dart';

// WHY: Standard BaseRemoteDatasource implementation for Supabase sync.
// NOTE: Used by sync engine for push/pull, not called directly by repositories.
class ExportArtifactRemoteDatasource extends BaseRemoteDatasource<ExportArtifact> {
  ExportArtifactRemoteDatasource(super.supabase);

  @override
  String get tableName => 'export_artifacts';

  @override
  ExportArtifact fromMap(Map<String, dynamic> map) => ExportArtifact.fromMap(map);

  @override
  Map<String, dynamic> toMap(ExportArtifact item) => item.toMap();
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/data/datasources/remote/export_artifact_remote_datasource.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 2.4: Create ExportArtifactRepository interface

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/features/pay_applications/domain/repositories/export_artifact_repository.dart`

#### Step 2.4.1: Create the abstract repository interface

Follow `FormExportRepository` pattern (`lib/features/forms/domain/repositories/form_export_repository.dart`). Extends `BaseRepository<ExportArtifact>` with project-scoped and type-filtered methods.

```dart
// lib/features/pay_applications/domain/repositories/export_artifact_repository.dart

import 'package:construction_inspector/shared/repositories/base_repository.dart';
import 'package:construction_inspector/features/pay_applications/data/models/export_artifact.dart';

// FROM SPEC: ExportArtifactProvider methods map to these repository operations.
// WHY: Abstract interface in domain/ layer — impl in data/ layer.
abstract class ExportArtifactRepository implements BaseRepository<ExportArtifact> {
  /// Create a new export artifact with validation.
  Future<RepositoryResult<ExportArtifact>> create(ExportArtifact artifact);

  /// Get all artifacts for a project.
  Future<List<ExportArtifact>> getByProjectId(String projectId);

  /// Get artifacts filtered by type (e.g., 'pay_application', 'entry_pdf').
  Future<List<ExportArtifact>> getByType(String projectId, String artifactType);

  /// Get artifacts filtered by multiple types.
  Future<List<ExportArtifact>> getByTypes(String projectId, List<String> types);

  /// Get artifact by source record ID (e.g., find artifact for a pay app).
  Future<ExportArtifact?> getBySourceRecordId(String sourceRecordId);
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/domain/repositories/export_artifact_repository.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 2.5: Create ExportArtifactRepositoryImpl

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/features/pay_applications/data/repositories/export_artifact_repository_impl.dart`

#### Step 2.5.1: Create the repository implementation

Follow `FormExportRepositoryImpl` pattern (`lib/features/forms/data/repositories/form_export_repository.dart`). Wraps local datasource with error handling.

```dart
// lib/features/pay_applications/data/repositories/export_artifact_repository_impl.dart

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/pay_applications/domain/repositories/export_artifact_repository.dart';
import 'package:construction_inspector/shared/repositories/base_repository.dart';
import 'package:construction_inspector/shared/models/paged_result.dart';
import 'package:construction_inspector/features/pay_applications/data/models/export_artifact.dart';
import 'package:construction_inspector/features/pay_applications/data/datasources/local/export_artifact_local_datasource.dart';

// WHY: Wraps datasource with RepositoryResult error handling.
// NOTE: Follows FormExportRepositoryImpl pattern.
class ExportArtifactRepositoryImpl implements ExportArtifactRepository {
  final ExportArtifactLocalDatasource _localDatasource;

  ExportArtifactRepositoryImpl(this._localDatasource);

  @override
  Future<ExportArtifact?> getById(String id) async {
    try {
      return await _localDatasource.getById(id);
    } on Exception catch (e) {
      Logger.error(
        '[ExportArtifactRepository] getById failed for id=$id',
        error: e,
      );
      return null;
    }
  }

  @override
  Future<List<ExportArtifact>> getAll() {
    return _localDatasource.getAll();
  }

  @override
  Future<PagedResult<ExportArtifact>> getPaged({
    required int offset,
    required int limit,
  }) {
    return _localDatasource.getPaged(offset: offset, limit: limit);
  }

  @override
  Future<int> getCount() {
    return _localDatasource.getCount();
  }

  @override
  Future<void> save(ExportArtifact item) async {
    final existing = await _localDatasource.getById(item.id);
    if (existing != null) {
      await _localDatasource.update(item);
    } else {
      await _localDatasource.insert(item);
    }
  }

  @override
  Future<void> delete(String id) async {
    await _localDatasource.softDelete(id);
  }

  @override
  Future<RepositoryResult<ExportArtifact>> create(ExportArtifact artifact) async {
    try {
      // WHY: Validate required fields before persisting.
      if (artifact.filename.isEmpty) {
        return RepositoryResult.failure('Filename is required');
      }
      if (artifact.title.isEmpty) {
        return RepositoryResult.failure('Title is required');
      }
      if (artifact.artifactType.isEmpty) {
        return RepositoryResult.failure('Artifact type is required');
      }
      // SEC-F05: Filename sanitization — reject path traversal or dangerous characters.
      if (RegExp(r'\.\.').hasMatch(artifact.filename) ||
          artifact.filename.contains('/') ||
          artifact.filename.contains('\\')) {
        return RepositoryResult.failure('Invalid filename');
      }
      await _localDatasource.insert(artifact);
      return RepositoryResult.success(artifact);
    } on Exception catch (e) {
      Logger.db('[ExportArtifactRepository] create failed: $e');
      return RepositoryResult.failure('Failed to save record');
    }
  }

  @override
  Future<List<ExportArtifact>> getByProjectId(String projectId) {
    return _localDatasource.getByProjectId(projectId);
  }

  @override
  Future<List<ExportArtifact>> getByType(String projectId, String artifactType) {
    return _localDatasource.getByType(projectId, artifactType);
  }

  @override
  Future<List<ExportArtifact>> getByTypes(String projectId, List<String> types) {
    return _localDatasource.getByTypes(projectId, types);
  }

  @override
  Future<ExportArtifact?> getBySourceRecordId(String sourceRecordId) {
    return _localDatasource.getBySourceRecordId(sourceRecordId);
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/data/repositories/export_artifact_repository_impl.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 2.6: ExportArtifact unit tests

**Agent**: `qa-testing-agent`

**Files:**
- Create: `test/features/pay_applications/data/models/export_artifact_test.dart`
- Create: `test/features/pay_applications/data/repositories/export_artifact_repository_test.dart`

#### Step 2.6.1: Create ExportArtifact model unit test

Test:
- Constructor with defaults (id auto-generated, timestamps auto-generated, status defaults to 'exported')
- `fromMap` / `toMap` round-trip
- `copyWith` with sentinel logic (null vs. not-provided)
- All 16 fields serialize correctly

#### Step 2.6.2: Create ExportArtifactRepository unit test

Test:
- `create` succeeds with valid artifact
- `create` fails with empty filename
- `create` fails with path traversal in filename (SEC-F05)
- `create` fails with empty title
- `getByProjectId` returns project-scoped results
- `getByType` filters by artifact_type
- `save` inserts when not existing, updates when existing
- `delete` soft-deletes (sets deleted_at)

**Verification:**
CI handles all test execution. Local gate:
```
pwsh -Command "flutter analyze test/features/pay_applications/"
```
Expected: No analysis issues found.

---

## Phase 3: Pay Application Data Layer

### Sub-phase 3.1: Create PayApplication model

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/features/pay_applications/data/models/pay_application.dart`

#### Step 3.1.1: Create PayApplication data model

Follow the `EntryExport` pattern. String timestamps (ISO 8601), UUID default, sentinel copyWith, toMap/fromMap. Uses `int` for `applicationNumber` and `double` for monetary amounts.

```dart
// lib/features/pay_applications/data/models/pay_application.dart

import 'package:uuid/uuid.dart';

// FROM SPEC: Section 2 "Data Model" — PayApplication child entity.
// One row per saved exported pay app, referencing its ExportArtifact parent.
// NOTE: Follows EntryExport pattern — String timestamps, UUID default, sentinel copyWith.
class PayApplication {
  final String id;
  final String exportArtifactId;
  final String projectId;
  final int applicationNumber;
  final String periodStart;
  final String periodEnd;
  final String? previousApplicationId;
  final double totalContractAmount;
  final double totalEarnedThisPeriod;
  final double totalEarnedToDate;
  final String? notes;
  final String createdAt;
  final String updatedAt;
  final String? createdByUserId;
  final String? deletedAt;
  final String? deletedBy;

  PayApplication({
    String? id,
    required this.exportArtifactId,
    required this.projectId,
    required this.applicationNumber,
    required this.periodStart,
    required this.periodEnd,
    this.previousApplicationId,
    required this.totalContractAmount,
    required this.totalEarnedThisPeriod,
    required this.totalEarnedToDate,
    this.notes,
    String? createdAt,
    String? updatedAt,
    this.createdByUserId,
    this.deletedAt,
    this.deletedBy,
  })  : id = id ?? const Uuid().v4(),
        createdAt = createdAt ?? DateTime.now().toUtc().toIso8601String(),
        updatedAt = updatedAt ?? DateTime.now().toUtc().toIso8601String();

  static const _sentinel = Object();

  PayApplication copyWith({
    Object? id = _sentinel,
    Object? exportArtifactId = _sentinel,
    Object? projectId = _sentinel,
    Object? applicationNumber = _sentinel,
    Object? periodStart = _sentinel,
    Object? periodEnd = _sentinel,
    Object? previousApplicationId = _sentinel,
    Object? totalContractAmount = _sentinel,
    Object? totalEarnedThisPeriod = _sentinel,
    Object? totalEarnedToDate = _sentinel,
    Object? notes = _sentinel,
    Object? createdAt = _sentinel,
    Object? updatedAt = _sentinel,
    Object? createdByUserId = _sentinel,
    Object? deletedAt = _sentinel,
    Object? deletedBy = _sentinel,
  }) {
    return PayApplication(
      id: identical(id, _sentinel) ? this.id : id as String?,
      exportArtifactId: identical(exportArtifactId, _sentinel) ? this.exportArtifactId : exportArtifactId! as String,
      projectId: identical(projectId, _sentinel) ? this.projectId : projectId! as String,
      applicationNumber: identical(applicationNumber, _sentinel) ? this.applicationNumber : applicationNumber! as int,
      periodStart: identical(periodStart, _sentinel) ? this.periodStart : periodStart! as String,
      periodEnd: identical(periodEnd, _sentinel) ? this.periodEnd : periodEnd! as String,
      previousApplicationId: identical(previousApplicationId, _sentinel) ? this.previousApplicationId : previousApplicationId as String?,
      totalContractAmount: identical(totalContractAmount, _sentinel) ? this.totalContractAmount : totalContractAmount! as double,
      totalEarnedThisPeriod: identical(totalEarnedThisPeriod, _sentinel) ? this.totalEarnedThisPeriod : totalEarnedThisPeriod! as double,
      totalEarnedToDate: identical(totalEarnedToDate, _sentinel) ? this.totalEarnedToDate : totalEarnedToDate! as double,
      notes: identical(notes, _sentinel) ? this.notes : notes as String?,
      createdAt: identical(createdAt, _sentinel) ? this.createdAt : createdAt as String?,
      updatedAt: identical(updatedAt, _sentinel) ? this.updatedAt : updatedAt as String?,
      createdByUserId: identical(createdByUserId, _sentinel) ? this.createdByUserId : createdByUserId as String?,
      deletedAt: identical(deletedAt, _sentinel) ? this.deletedAt : deletedAt as String?,
      deletedBy: identical(deletedBy, _sentinel) ? this.deletedBy : deletedBy as String?,
    );
  }

  Map<String, dynamic> toMap() => {
    'id': id,
    'export_artifact_id': exportArtifactId,
    'project_id': projectId,
    'application_number': applicationNumber,
    'period_start': periodStart,
    'period_end': periodEnd,
    'previous_application_id': previousApplicationId,
    'total_contract_amount': totalContractAmount,
    'total_earned_this_period': totalEarnedThisPeriod,
    'total_earned_to_date': totalEarnedToDate,
    'notes': notes,
    'created_at': createdAt,
    'updated_at': updatedAt,
    'created_by_user_id': createdByUserId,
    'deleted_at': deletedAt,
    'deleted_by': deletedBy,
  };

  factory PayApplication.fromMap(Map<String, dynamic> map) => PayApplication(
    id: map['id'] as String,
    exportArtifactId: map['export_artifact_id'] as String,
    projectId: map['project_id'] as String,
    applicationNumber: map['application_number'] as int,
    periodStart: map['period_start'] as String,
    periodEnd: map['period_end'] as String,
    previousApplicationId: map['previous_application_id'] as String?,
    totalContractAmount: (map['total_contract_amount'] as num).toDouble(),
    totalEarnedThisPeriod: (map['total_earned_this_period'] as num).toDouble(),
    totalEarnedToDate: (map['total_earned_to_date'] as num).toDouble(),
    notes: map['notes'] as String?,
    createdAt: map['created_at'] as String,
    updatedAt: map['updated_at'] as String,
    createdByUserId: map['created_by_user_id'] as String?,
    deletedAt: map['deleted_at'] as String?,
    deletedBy: map['deleted_by'] as String?,
  );
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/data/models/pay_application.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 3.2: Create PayApplicationLocalDatasource

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/features/pay_applications/data/datasources/local/pay_application_local_datasource.dart`

#### Step 3.2.1: Create the local datasource with custom query methods

Extends `ProjectScopedDatasource<PayApplication>`. Adds custom methods required by the spec: range lookup, overlap detection, next application number.

```dart
// lib/features/pay_applications/data/datasources/local/pay_application_local_datasource.dart

import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/shared/datasources/project_scoped_datasource.dart';
import 'package:construction_inspector/features/pay_applications/data/models/pay_application.dart';

// WHY: Follows ProjectScopedDatasource pattern — pay_applications has project_id.
// FROM SPEC: PayApplicationRepository needs range-based, number-based, and
// export-artifact-based queries for the pay-app export and validation flows.
class PayApplicationLocalDatasource extends ProjectScopedDatasource<PayApplication> {
  @override
  final DatabaseService db;

  PayApplicationLocalDatasource(this.db);

  @override
  String get tableName => 'pay_applications';

  @override
  String get defaultOrderBy => 'application_number DESC';

  @override
  PayApplication fromMap(Map<String, dynamic> map) => PayApplication.fromMap(map);

  @override
  Map<String, dynamic> toMap(PayApplication item) => item.toMap();

  @override
  String getId(PayApplication item) => item.id;

  // FROM SPEC: "getByExportArtifactId" — find the pay app child for a given artifact.
  Future<PayApplication?> getByExportArtifactId(String exportArtifactId) async {
    final database = await db.database;
    final results = await database.query(
      tableName,
      where: 'export_artifact_id = ? AND deleted_at IS NULL',
      whereArgs: [exportArtifactId],
      limit: 1,
    );
    return results.isEmpty ? null : fromMap(results.first);
  }

  // FROM SPEC: "getLastByProject" — most recent pay app for chaining.
  // WHY: Used to determine default period_start (day after last period_end)
  // and to set previous_application_id on new pay apps.
  Future<PayApplication?> getLastByProject(String projectId) async {
    final database = await db.database;
    final results = await database.query(
      tableName,
      where: 'project_id = ? AND deleted_at IS NULL',
      whereArgs: [projectId],
      orderBy: 'application_number DESC',
      limit: 1,
    );
    return results.isEmpty ? null : fromMap(results.first);
  }

  // FROM SPEC: "findByDateRange" — find exact match for replace-flow.
  // WHY: Exact same project + period_start + period_end = same pay app identity.
  Future<PayApplication?> findByDateRange(
    String projectId,
    String periodStart,
    String periodEnd,
  ) async {
    final database = await db.database;
    final results = await database.query(
      tableName,
      where: 'project_id = ? AND period_start = ? AND period_end = ? AND deleted_at IS NULL',
      whereArgs: [projectId, periodStart, periodEnd],
      limit: 1,
    );
    return results.isEmpty ? null : fromMap(results.first);
  }

  // FROM SPEC: "getNextApplicationNumber" — auto-assign chronological number.
  // WHY: MAX(application_number) + 1 for the project.
  Future<int> getNextApplicationNumber(String projectId) async {
    final database = await db.database;
    final result = await database.rawQuery(
      'SELECT MAX(application_number) as max_num FROM $tableName WHERE project_id = ? AND deleted_at IS NULL',
      [projectId],
    );
    if (result.isEmpty || result.first['max_num'] == null) {
      return 1;
    }
    return (result.first['max_num']! as int) + 1;
  }

  // FROM SPEC: "findOverlapping" — detect overlapping non-identical ranges.
  // WHY: Overlapping non-identical ranges must be blocked per spec Section 3.
  // An overlap exists when: existing.start < new.end AND existing.end > new.start
  // AND it's NOT an exact match (which would trigger replace flow instead).
  Future<List<PayApplication>> findOverlapping(
    String projectId,
    String periodStart,
    String periodEnd,
  ) async {
    final database = await db.database;
    final results = await database.query(
      tableName,
      where: '''project_id = ? AND deleted_at IS NULL
        AND period_start < ? AND period_end > ?
        AND NOT (period_start = ? AND period_end = ?)''',
      whereArgs: [projectId, periodEnd, periodStart, periodStart, periodEnd],
      orderBy: defaultOrderBy,
    );
    return results.map(fromMap).toList();
  }

  // WHY: Check if a specific application number is already used in this project.
  // FROM SPEC: "Number must remain unique within the project"
  Future<bool> isNumberUsed(String projectId, int applicationNumber) async {
    final database = await db.database;
    final result = await database.rawQuery(
      'SELECT COUNT(*) as cnt FROM $tableName WHERE project_id = ? AND application_number = ? AND deleted_at IS NULL',
      [projectId, applicationNumber],
    );
    return (result.first['cnt'] as int) > 0;
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/data/datasources/local/pay_application_local_datasource.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 3.3: Create PayApplicationRemoteDatasource

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/features/pay_applications/data/datasources/remote/pay_application_remote_datasource.dart`

#### Step 3.3.1: Create the remote datasource

```dart
// lib/features/pay_applications/data/datasources/remote/pay_application_remote_datasource.dart

import 'package:construction_inspector/shared/datasources/base_remote_datasource.dart';
import 'package:construction_inspector/features/pay_applications/data/models/pay_application.dart';

// WHY: Standard BaseRemoteDatasource implementation for Supabase sync.
// NOTE: Used by sync engine for push/pull, not called directly by repositories.
class PayApplicationRemoteDatasource extends BaseRemoteDatasource<PayApplication> {
  PayApplicationRemoteDatasource(super.supabase);

  @override
  String get tableName => 'pay_applications';

  @override
  PayApplication fromMap(Map<String, dynamic> map) => PayApplication.fromMap(map);

  @override
  Map<String, dynamic> toMap(PayApplication item) => item.toMap();
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/data/datasources/remote/pay_application_remote_datasource.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 3.4: Create PayApplicationRepository interface

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/features/pay_applications/domain/repositories/pay_application_repository.dart`

#### Step 3.4.1: Create the abstract repository interface

```dart
// lib/features/pay_applications/domain/repositories/pay_application_repository.dart

import 'package:construction_inspector/shared/repositories/base_repository.dart';
import 'package:construction_inspector/features/pay_applications/data/models/pay_application.dart';

// FROM SPEC: PayApplicationRepository — exact-range identity, overlap blocking,
// chronological number rules.
// WHY: Abstract interface in domain/ layer. Custom methods support the pay-app
// export flow validation (range checking, number assignment, overlap detection).
abstract class PayApplicationRepository implements BaseRepository<PayApplication> {
  /// Create a new pay application with validation.
  Future<RepositoryResult<PayApplication>> create(PayApplication payApp);

  /// Get all pay applications for a project.
  Future<List<PayApplication>> getByProjectId(String projectId);

  /// Get the pay application child of a specific export artifact.
  Future<PayApplication?> getByExportArtifactId(String exportArtifactId);

  /// Get the most recent pay application for a project (highest application_number).
  Future<PayApplication?> getLastByProject(String projectId);

  /// Find an exact-match pay app for the given date range (replace-flow identity).
  Future<PayApplication?> findByDateRange(
    String projectId,
    String periodStart,
    String periodEnd,
  );

  /// Get the next auto-assigned application number for a project.
  Future<int> getNextApplicationNumber(String projectId);

  /// Find overlapping non-identical pay-app ranges (for blocking).
  Future<List<PayApplication>> findOverlapping(
    String projectId,
    String periodStart,
    String periodEnd,
  );

  /// Check if a specific application number is already used in this project.
  Future<bool> isNumberUsed(String projectId, int applicationNumber);
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/domain/repositories/pay_application_repository.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 3.5: Create PayApplicationRepositoryImpl

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/features/pay_applications/data/repositories/pay_application_repository_impl.dart`

#### Step 3.5.1: Create the repository implementation

```dart
// lib/features/pay_applications/data/repositories/pay_application_repository_impl.dart

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/pay_applications/domain/repositories/pay_application_repository.dart';
import 'package:construction_inspector/shared/repositories/base_repository.dart';
import 'package:construction_inspector/shared/models/paged_result.dart';
import 'package:construction_inspector/features/pay_applications/data/models/pay_application.dart';
import 'package:construction_inspector/features/pay_applications/data/datasources/local/pay_application_local_datasource.dart';

// WHY: Wraps datasource with RepositoryResult error handling and validation.
// NOTE: Follows FormExportRepositoryImpl pattern.
class PayApplicationRepositoryImpl implements PayApplicationRepository {
  final PayApplicationLocalDatasource _localDatasource;

  PayApplicationRepositoryImpl(this._localDatasource);

  @override
  Future<PayApplication?> getById(String id) async {
    try {
      return await _localDatasource.getById(id);
    } on Exception catch (e) {
      Logger.error(
        '[PayApplicationRepository] getById failed for id=$id',
        error: e,
      );
      return null;
    }
  }

  @override
  Future<List<PayApplication>> getAll() {
    return _localDatasource.getAll();
  }

  @override
  Future<PagedResult<PayApplication>> getPaged({
    required int offset,
    required int limit,
  }) {
    return _localDatasource.getPaged(offset: offset, limit: limit);
  }

  @override
  Future<int> getCount() {
    return _localDatasource.getCount();
  }

  @override
  Future<void> save(PayApplication item) async {
    final existing = await _localDatasource.getById(item.id);
    if (existing != null) {
      await _localDatasource.update(item);
    } else {
      await _localDatasource.insert(item);
    }
  }

  @override
  Future<void> delete(String id) async {
    await _localDatasource.softDelete(id);
  }

  @override
  Future<RepositoryResult<PayApplication>> create(PayApplication payApp) async {
    try {
      // WHY: Validate business rules before persisting.
      // FROM SPEC: "application_number must remain unique within the project"
      if (payApp.applicationNumber <= 0) {
        return RepositoryResult.failure('Application number must be positive');
      }
      if (payApp.periodStart.isEmpty || payApp.periodEnd.isEmpty) {
        return RepositoryResult.failure('Period start and end are required');
      }
      // FROM SPEC: period_start must be before period_end
      if (payApp.periodStart.compareTo(payApp.periodEnd) >= 0) {
        return RepositoryResult.failure('Period start must be before period end');
      }
      if (payApp.exportArtifactId.isEmpty) {
        return RepositoryResult.failure('Export artifact ID is required');
      }

      await _localDatasource.insert(payApp);
      return RepositoryResult.success(payApp);
    } on Exception catch (e) {
      Logger.db('[PayApplicationRepository] create failed: $e');
      // WHY: SQLite unique index violation means duplicate range or number.
      final msg = e.toString();
      if (msg.contains('UNIQUE constraint failed')) {
        if (msg.contains('idx_pay_applications_range')) {
          return RepositoryResult.failure(
            'A pay application with this exact date range already exists',
          );
        }
        if (msg.contains('idx_pay_applications_number')) {
          return RepositoryResult.failure(
            'This application number is already used in this project',
          );
        }
      }
      return RepositoryResult.failure('Failed to save pay application');
    }
  }

  @override
  Future<List<PayApplication>> getByProjectId(String projectId) {
    return _localDatasource.getByProjectId(projectId);
  }

  @override
  Future<PayApplication?> getByExportArtifactId(String exportArtifactId) {
    return _localDatasource.getByExportArtifactId(exportArtifactId);
  }

  @override
  Future<PayApplication?> getLastByProject(String projectId) {
    return _localDatasource.getLastByProject(projectId);
  }

  @override
  Future<PayApplication?> findByDateRange(
    String projectId,
    String periodStart,
    String periodEnd,
  ) {
    return _localDatasource.findByDateRange(projectId, periodStart, periodEnd);
  }

  @override
  Future<int> getNextApplicationNumber(String projectId) {
    return _localDatasource.getNextApplicationNumber(projectId);
  }

  @override
  Future<List<PayApplication>> findOverlapping(
    String projectId,
    String periodStart,
    String periodEnd,
  ) {
    return _localDatasource.findOverlapping(projectId, periodStart, periodEnd);
  }

  @override
  Future<bool> isNumberUsed(String projectId, int applicationNumber) {
    return _localDatasource.isNumberUsed(projectId, applicationNumber);
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/data/repositories/pay_application_repository_impl.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 3.6: PayApplication unit tests

**Agent**: `qa-testing-agent`

**Files:**
- Create: `test/features/pay_applications/data/models/pay_application_test.dart`
- Create: `test/features/pay_applications/data/repositories/pay_application_repository_test.dart`

#### Step 3.6.1: Create PayApplication model unit test

Test:
- Constructor with defaults (id auto-generated, timestamps auto-generated)
- `fromMap` / `toMap` round-trip with all 16 fields
- `copyWith` with sentinel logic (null vs. not-provided)
- Numeric fields (`applicationNumber`, `totalContractAmount`, etc.) serialize correctly
- `previousApplicationId` nullable handling

#### Step 3.6.2: Create PayApplicationRepository unit test

Test:
- `create` succeeds with valid pay app
- `create` fails with non-positive application_number
- `create` fails with period_start >= period_end
- `create` fails with empty exportArtifactId
- `getByProjectId` returns project-scoped results
- `getLastByProject` returns highest application_number
- `findByDateRange` returns exact match
- `findOverlapping` returns overlapping non-identical ranges
- `findOverlapping` excludes exact matches
- `getNextApplicationNumber` returns MAX+1 or 1 for empty project
- `isNumberUsed` returns true for existing, false for unused

**Verification:**
CI handles all test execution. Local gate:
```
pwsh -Command "flutter analyze test/features/pay_applications/"
```
Expected: No analysis issues found.

---

## Phase 4: Pay Application Export Logic

### Sub-phase 4.1: Add getQuantitiesByDateRange to EntryQuantity data layer

**Agent**: `code-fixer-agent`

**Files:**
- Modify: `lib/features/quantities/data/datasources/local/entry_quantity_local_datasource.dart` (add method)
- Modify: `lib/features/quantities/domain/repositories/entry_quantity_repository.dart` (add method to interface)
- Modify: `lib/features/quantities/data/repositories/entry_quantity_repository_impl.dart` (add method impl)
- Modify: `lib/features/quantities/presentation/providers/entry_quantity_provider.dart` (add provider method)

#### Step 4.1.1: Add getByDateRange to EntryQuantityLocalDatasource

At the end of `lib/features/quantities/data/datasources/local/entry_quantity_local_datasource.dart` (before the closing `}` of the class, around line 135), add:

```dart
  /// Get quantities for a project within a date range.
  /// FROM SPEC: Pay app export queries entry_quantities joined with daily_entries
  /// to filter by the pay-app date range (period_start to period_end).
  /// WHY: Returns a map of bidItemId -> total quantity for that range, which
  /// the PayAppExcelExporter uses to compute "earned this period."
  /// NOTE: Joins entry_quantities with daily_entries to filter by date range.
  /// Dates stored as ISO 8601 strings, so string comparison works for date filtering.
  Future<Map<String, double>> getByDateRange(
    String projectId,
    String startDate,
    String endDate,
  ) async {
    final database = await db.database;
    final result = await database.rawQuery(
      '''
      SELECT eq.bid_item_id, SUM(eq.quantity) as total
      FROM $tableName eq
      INNER JOIN daily_entries de ON eq.entry_id = de.id
      WHERE de.project_id = ?
        AND de.date >= ?
        AND de.date <= ?
        AND eq.deleted_at IS NULL
        AND de.deleted_at IS NULL
      GROUP BY eq.bid_item_id
    ''',
      [projectId, startDate, endDate],
    );

    final Map<String, double> totals = {};
    for (final row in result) {
      final bidItemId = row['bid_item_id'] as String;
      final total = (row['total'] as num?)?.toDouble() ?? 0.0;
      totals[bidItemId] = total;
    }
    return totals;
  }
```

#### Step 4.1.2: Add getByDateRange to EntryQuantityRepository interface

At the end of `lib/features/quantities/domain/repositories/entry_quantity_repository.dart` (before the closing `}` of the abstract class, around line 103), add:

```dart
  /// Get total quantities per bid item for a project within a date range.
  /// FROM SPEC: Used by PayAppExcelExporter to compute "earned this period."
  Future<Map<String, double>> getByDateRange(
    String projectId,
    String startDate,
    String endDate,
  );
```

#### Step 4.1.3: Add getByDateRange to EntryQuantityRepositoryImpl

At the end of `lib/features/quantities/data/repositories/entry_quantity_repository_impl.dart` (before the closing `}` of the class, around line 175), add:

```dart
  @override
  Future<Map<String, double>> getByDateRange(
    String projectId,
    String startDate,
    String endDate,
  ) {
    return _localDatasource.getByDateRange(projectId, startDate, endDate);
  }
```

#### Step 4.1.4: Add getQuantitiesByDateRange to EntryQuantityProvider

At the end of `lib/features/quantities/presentation/providers/entry_quantity_provider.dart` (before the closing `}` of the class, around line 323), add:

```dart
  /// Get total quantities per bid item for a project within a date range.
  /// FROM SPEC: Used by pay app export to compute "earned this period."
  /// WHY: Provider method delegates to repository; does NOT cache because
  /// date range queries are one-off export computations, not live state.
  Future<Map<String, double>> getQuantitiesByDateRange(
    String projectId,
    DateTime start,
    DateTime end,
  ) async {
    try {
      // NOTE: daily_entries.date is stored as ISO 8601 date string (YYYY-MM-DD).
      // Convert DateTime to date-only string for comparison.
      final startDate = start.toIso8601String().substring(0, 10);
      final endDate = end.toIso8601String().substring(0, 10);
      return await _repository.getByDateRange(projectId, startDate, endDate);
    } on Exception catch (e) {
      Logger.db('[EntryQuantityProvider] getQuantitiesByDateRange error: $e');
      return {};
    }
  }
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/quantities/"
```
Expected: No analysis issues found.

---

### Sub-phase 4.2: Add excel dependency to pubspec.yaml

**Agent**: `code-fixer-agent`

**Files:**
- Modify: `pubspec.yaml` (add `excel` package dependency)

#### Step 4.2.1: Add the excel package dependency

Add `excel: ^4.0.6` (or latest compatible) to the `dependencies:` section of `pubspec.yaml`. This is the Dart-native Excel read/write library used for G703-style workbook generation.

WHY: The spec requires `.xlsx` export. The `excel` package is a pure Dart library with no native dependencies, compatible with all platforms.

After adding:
```
pwsh -Command "flutter pub get"
```
Expected: Resolves successfully with no version conflicts.

**Verification:**
```
pwsh -Command "flutter analyze"
```
Expected: No new analysis issues introduced.

---

### Sub-phase 4.3: Create PayAppExcelExporter service

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/features/pay_applications/data/services/pay_app_excel_exporter.dart`

#### Step 4.3.1: Create the G703-style Excel exporter service

This service generates a G703-format `.xlsx` workbook from bid items, date-range quantities, and optional prior pay app data. It is a pure data service with no Flutter dependencies.

```dart
// lib/features/pay_applications/data/services/pay_app_excel_exporter.dart

import 'dart:io';
import 'dart:typed_data';
import 'package:excel/excel.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/quantities/data/models/bid_item.dart';
import 'package:construction_inspector/features/pay_applications/data/models/pay_application.dart';

// FROM SPEC: PayAppExcelExporter — generates G703-style workbook.
// WHY: Pure service class. Receives precomputed data, produces xlsx bytes.
// No repository or database access — the use case feeds it data.
class PayAppExcelExporter {
  /// Result of generating a pay app Excel file.
  /// Contains the file bytes and computed summary totals.
  PayAppExcelExporter();

  /// Generate a G703-style pay application workbook.
  ///
  /// [bidItems] — all bid items for the project, sorted by item number.
  /// [periodQuantities] — map of bidItemId -> quantity earned this period.
  /// [cumulativeQuantities] — map of bidItemId -> total quantity earned to date
  ///   (including this period).
  /// [previousPayApp] — prior pay app for chaining totals (null for first pay app).
  /// [applicationNumber] — the assigned pay-app number.
  /// [periodStart] / [periodEnd] — the covered date range (ISO 8601 date strings).
  /// [projectName] — project display name for the header.
  ///
  /// Returns the generated xlsx file as bytes.
  Uint8List generate({
    required List<BidItem> bidItems,
    required Map<String, double> periodQuantities,
    required Map<String, double> cumulativeQuantities,
    required PayApplication? previousPayApp,
    required int applicationNumber,
    required String periodStart,
    required String periodEnd,
    required String projectName,
  }) {
    final excel = Excel.createExcel();
    // WHY: Default sheet is 'Sheet1' — rename to 'G703'.
    excel.rename('Sheet1', 'G703');
    final sheet = excel['G703'];

    // -- Header rows --
    // FROM SPEC: G703-style layout with header information.
    _writeHeader(
      sheet,
      projectName: projectName,
      applicationNumber: applicationNumber,
      periodStart: periodStart,
      periodEnd: periodEnd,
    );

    // -- Column headers (row 5, 0-indexed) --
    // FROM SPEC: G703 columns: Item No, Description, Unit, Scheduled Value,
    // Previous Work Complete, This Period, Materials Stored, Total Completed,
    // % Complete, Balance to Finish
    const headerRow = 5;
    final headers = [
      'Item No.',
      'Description of Work',
      'Unit',
      'Scheduled Value',
      'From Previous\nApplication',
      'This Period',
      'Materials\nPresently Stored',
      'Total Completed\n& Stored to Date',
      '% (G/C)',
      'Balance to\nFinish (C-G)',
    ];

    for (var col = 0; col < headers.length; col++) {
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: col, rowIndex: headerRow)).value =
          TextCellValue(headers[col]);
    }

    // Column letter references for formula clarity:
    // A=Item No, B=Description, C=Unit, D=Scheduled Value,
    // E=From Previous, F=This Period, G=Materials Stored,
    // H=Total Completed, I=% Complete, J=Balance to Finish

    // -- Data rows --
    var dataRow = headerRow + 1;
    double totalScheduledValue = 0;
    double totalPreviousWork = 0;
    double totalThisPeriod = 0;
    double totalCompletedToDate = 0;

    for (final bidItem in bidItems) {
      final scheduledValue = bidItem.bidAmount ?? (bidItem.bidQuantity * (bidItem.unitPrice ?? 0));
      final periodQty = periodQuantities[bidItem.id] ?? 0.0;
      final cumulativeQty = cumulativeQuantities[bidItem.id] ?? 0.0;
      final unitPrice = bidItem.unitPrice ?? 0.0;

      // WHY: "earned" amounts are quantity * unit_price for G703.
      final earnedThisPeriod = periodQty * unitPrice;
      final earnedToDate = cumulativeQty * unitPrice;
      // WHY: Previous = total to date minus this period's contribution.
      final previousWork = earnedToDate - earnedThisPeriod;
      final percentComplete = scheduledValue > 0 ? (earnedToDate / scheduledValue) : 0.0;
      final balanceToFinish = scheduledValue - earnedToDate;

      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 0, rowIndex: dataRow)).value =
          TextCellValue(bidItem.itemNumber);
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 1, rowIndex: dataRow)).value =
          TextCellValue(bidItem.description);
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 2, rowIndex: dataRow)).value =
          TextCellValue(bidItem.unit);
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 3, rowIndex: dataRow)).value =
          DoubleCellValue(scheduledValue);
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 4, rowIndex: dataRow)).value =
          DoubleCellValue(previousWork);
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 5, rowIndex: dataRow)).value =
          DoubleCellValue(earnedThisPeriod);
      // Column 6: Materials Presently Stored — always 0 for v1 (not tracked).
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 6, rowIndex: dataRow)).value =
          DoubleCellValue(0);
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 7, rowIndex: dataRow)).value =
          DoubleCellValue(earnedToDate);
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 8, rowIndex: dataRow)).value =
          DoubleCellValue(percentComplete);
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 9, rowIndex: dataRow)).value =
          DoubleCellValue(balanceToFinish);

      totalScheduledValue += scheduledValue;
      totalPreviousWork += previousWork;
      totalThisPeriod += earnedThisPeriod;
      totalCompletedToDate += earnedToDate;

      dataRow++;
    }

    // -- Totals row --
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 1, rowIndex: dataRow)).value =
        const TextCellValue('TOTALS');
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 3, rowIndex: dataRow)).value =
        DoubleCellValue(totalScheduledValue);
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 4, rowIndex: dataRow)).value =
        DoubleCellValue(totalPreviousWork);
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 5, rowIndex: dataRow)).value =
        DoubleCellValue(totalThisPeriod);
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 6, rowIndex: dataRow)).value =
        const DoubleCellValue(0);
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 7, rowIndex: dataRow)).value =
        DoubleCellValue(totalCompletedToDate);
    final totalPercent = totalScheduledValue > 0
        ? (totalCompletedToDate / totalScheduledValue)
        : 0.0;
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 8, rowIndex: dataRow)).value =
        DoubleCellValue(totalPercent);
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 9, rowIndex: dataRow)).value =
        DoubleCellValue(totalScheduledValue - totalCompletedToDate);

    Logger.db(
      '[PayAppExcelExporter] Generated G703 workbook: '
      '${bidItems.length} items, app #$applicationNumber, '
      'period $periodStart to $periodEnd',
    );

    final bytes = excel.encode();
    if (bytes == null) {
      throw StateError('Failed to encode Excel workbook');
    }
    return Uint8List.fromList(bytes);
  }

  /// Write the G703 header block (rows 0-4).
  void _writeHeader(
    Sheet sheet, {
    required String projectName,
    required int applicationNumber,
    required String periodStart,
    required String periodEnd,
  }) {
    // Row 0: Title
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 0, rowIndex: 0)).value =
        const TextCellValue('APPLICATION AND CERTIFICATE FOR PAYMENT');

    // Row 1: Project name
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 0, rowIndex: 1)).value =
        const TextCellValue('PROJECT:');
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 1, rowIndex: 1)).value =
        TextCellValue(projectName);

    // Row 2: Application number
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 0, rowIndex: 2)).value =
        const TextCellValue('APPLICATION NO:');
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 1, rowIndex: 2)).value =
        IntCellValue(applicationNumber);

    // Row 3: Period
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 0, rowIndex: 3)).value =
        const TextCellValue('PERIOD TO:');
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 1, rowIndex: 3)).value =
        TextCellValue('$periodStart to $periodEnd');
  }

  /// Save generated bytes to a file and return the file path.
  /// WHY: Callers need the local file path for ExportArtifact.localPath.
  Future<String> saveToFile(
    Uint8List bytes, {
    required String directory,
    required String filename,
  }) async {
    final file = File('$directory/$filename');
    await file.writeAsBytes(bytes);
    Logger.db('[PayAppExcelExporter] Saved to ${file.path}');
    return file.path;
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/data/services/pay_app_excel_exporter.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 4.4: Create ExportPayAppUseCase

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/features/pay_applications/domain/usecases/export_pay_app_use_case.dart`

#### Step 4.4.1: Create the export orchestration use case

This use case orchestrates the full pay app export flow: query bid items, query quantities by date range, compute totals, generate xlsx, save ExportArtifact + PayApplication rows.

```dart
// lib/features/pay_applications/domain/usecases/export_pay_app_use_case.dart

import 'dart:io';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/pay_applications/data/models/export_artifact.dart';
import 'package:construction_inspector/features/pay_applications/data/models/pay_application.dart';
import 'package:construction_inspector/features/pay_applications/data/services/pay_app_excel_exporter.dart';
import 'package:construction_inspector/features/pay_applications/domain/repositories/export_artifact_repository.dart';
import 'package:construction_inspector/features/pay_applications/domain/repositories/pay_application_repository.dart';
import 'package:construction_inspector/features/quantities/domain/repositories/bid_item_repository.dart';
import 'package:construction_inspector/features/quantities/domain/repositories/entry_quantity_repository.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

// FROM SPEC: ExportPayAppUseCase orchestrates the full export flow.
// Data flow: query bid items -> query quantities by date range -> compute
// totals -> generate xlsx -> save ExportArtifact + PayApplication rows.
// WHY: Domain use case keeps export logic out of the provider layer.
class ExportPayAppUseCase {
  final BidItemRepository _bidItemRepository;
  final EntryQuantityRepository _entryQuantityRepository;
  final ExportArtifactRepository _exportArtifactRepository;
  final PayApplicationRepository _payApplicationRepository;
  final PayAppExcelExporter _excelExporter;

  ExportPayAppUseCase({
    required BidItemRepository bidItemRepository,
    required EntryQuantityRepository entryQuantityRepository,
    required ExportArtifactRepository exportArtifactRepository,
    required PayApplicationRepository payApplicationRepository,
    required PayAppExcelExporter excelExporter,
  })  : _bidItemRepository = bidItemRepository,
        _entryQuantityRepository = entryQuantityRepository,
        _exportArtifactRepository = exportArtifactRepository,
        _payApplicationRepository = payApplicationRepository,
        _excelExporter = excelExporter;

  /// Export result containing both the artifact and the pay app rows.
  /// [localPath] is the device file path for sharing.
  Future<ExportPayAppResult> execute({
    required String projectId,
    required String projectName,
    required String periodStart,
    required String periodEnd,
    required int applicationNumber,
    String? previousApplicationId,
    String? notes,
    String? createdByUserId,
    String? existingPayAppIdToReplace,
  }) async {
    Logger.db(
      '[ExportPayAppUseCase] Starting export: project=$projectId, '
      'period=$periodStart to $periodEnd, app#=$applicationNumber',
    );

    // Step 1: Query all bid items for the project.
    // FROM SPEC: "query bid items" in the generation flow.
    final bidItems = await _bidItemRepository.getByProjectId(projectId);
    if (bidItems.isEmpty) {
      throw StateError('No bid items found for project $projectId');
    }
    // Sort by item number for consistent G703 output.
    bidItems.sort((a, b) => a.itemNumber.compareTo(b.itemNumber));

    // Step 2: Query quantities for the date range (this period).
    // FROM SPEC: "query entries" -> filter by date range.
    final periodQuantities = await _entryQuantityRepository.getByDateRange(
      projectId,
      periodStart,
      periodEnd,
    );

    // Step 3: Query cumulative quantities (all time up to period_end).
    // WHY: G703 "Total Completed & Stored to Date" = cumulative.
    final cumulativeQuantities = await _entryQuantityRepository.getByDateRange(
      projectId,
      '1900-01-01', // NOTE: Earliest possible date to capture all history.
      periodEnd,
    );

    // Step 4: Get previous pay app for chaining.
    PayApplication? previousPayApp;
    if (previousApplicationId != null) {
      previousPayApp = await _payApplicationRepository.getById(previousApplicationId);
    }

    // Step 5: Compute summary totals.
    double totalContractAmount = 0;
    double totalEarnedThisPeriod = 0;
    double totalEarnedToDate = 0;

    for (final bidItem in bidItems) {
      final scheduledValue = bidItem.bidAmount ?? (bidItem.bidQuantity * (bidItem.unitPrice ?? 0));
      totalContractAmount += scheduledValue;

      final periodQty = periodQuantities[bidItem.id] ?? 0.0;
      final cumulativeQty = cumulativeQuantities[bidItem.id] ?? 0.0;
      final unitPrice = bidItem.unitPrice ?? 0.0;

      totalEarnedThisPeriod += periodQty * unitPrice;
      totalEarnedToDate += cumulativeQty * unitPrice;
    }

    // Step 6: Generate the xlsx workbook.
    // FROM SPEC: "build G703-style workbook"
    final bytes = _excelExporter.generate(
      bidItems: bidItems,
      periodQuantities: periodQuantities,
      cumulativeQuantities: cumulativeQuantities,
      previousPayApp: previousPayApp,
      applicationNumber: applicationNumber,
      periodStart: periodStart,
      periodEnd: periodEnd,
      projectName: projectName,
    );

    // Step 7: Save the file to device storage.
    final appDir = await getApplicationDocumentsDirectory();
    final exportDir = Directory('${appDir.path}/exports/pay-applications');
    if (!exportDir.existsSync()) {
      await exportDir.create(recursive: true);
    }
    // SEC-F05: Sanitized filename — no user input in the path component.
    final filename = 'PayApp_${applicationNumber}_${periodStart}_$periodEnd.xlsx';
    final localPath = await _excelExporter.saveToFile(
      bytes,
      directory: exportDir.path,
      filename: filename,
    );

    // Step 8: If replacing, soft-delete the prior artifact + pay app.
    if (existingPayAppIdToReplace != null) {
      final existingPayApp = await _payApplicationRepository.getById(existingPayAppIdToReplace);
      if (existingPayApp != null) {
        await _payApplicationRepository.delete(existingPayApp.id);
        await _exportArtifactRepository.delete(existingPayApp.exportArtifactId);
        Logger.db(
          '[ExportPayAppUseCase] Replaced existing pay app ${existingPayApp.id}',
        );
      }
    }

    // Step 9: Persist ExportArtifact row.
    // FROM SPEC: "Persist ExportArtifact + PayApplication rows"
    final artifactId = const Uuid().v4();
    final artifact = ExportArtifact(
      id: artifactId,
      projectId: projectId,
      artifactType: 'pay_application',
      title: 'Pay Application #$applicationNumber ($periodStart - $periodEnd)',
      filename: filename,
      localPath: localPath,
      mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      createdByUserId: createdByUserId,
    );
    final artifactResult = await _exportArtifactRepository.create(artifact);
    if (!artifactResult.isSuccess) {
      throw StateError(
        'Failed to save export artifact: ${artifactResult.error}',
      );
    }

    // Step 10: Persist PayApplication row.
    final payApp = PayApplication(
      exportArtifactId: artifactId,
      projectId: projectId,
      applicationNumber: applicationNumber,
      periodStart: periodStart,
      periodEnd: periodEnd,
      previousApplicationId: previousApplicationId,
      totalContractAmount: totalContractAmount,
      totalEarnedThisPeriod: totalEarnedThisPeriod,
      totalEarnedToDate: totalEarnedToDate,
      notes: notes,
      createdByUserId: createdByUserId,
    );
    final payAppResult = await _payApplicationRepository.create(payApp);
    if (!payAppResult.isSuccess) {
      // WHY: Roll back artifact if pay app save fails.
      await _exportArtifactRepository.delete(artifactId);
      throw StateError(
        'Failed to save pay application: ${payAppResult.error}',
      );
    }

    Logger.db(
      '[ExportPayAppUseCase] Export complete: artifact=$artifactId, '
      'payApp=${payApp.id}, file=$localPath',
    );

    return ExportPayAppResult(
      artifact: artifact,
      payApplication: payApp,
      localPath: localPath,
    );
  }
}

/// Result of a pay app export operation.
class ExportPayAppResult {
  final ExportArtifact artifact;
  final PayApplication payApplication;
  final String localPath;

  const ExportPayAppResult({
    required this.artifact,
    required this.payApplication,
    required this.localPath,
  });
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/domain/usecases/export_pay_app_use_case.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 4.5: Create models barrel export

**Agent**: `code-fixer-agent`

**Files:**
- Create: `lib/features/pay_applications/data/models/models.dart`

#### Step 4.5.1: Create barrel file for pay_applications models

```dart
// lib/features/pay_applications/data/models/models.dart

// WHY: Barrel file for clean imports.
export 'export_artifact.dart';
export 'pay_application.dart';
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/data/models/models.dart"
```
Expected: No analysis issues found.

---

### Sub-phase 4.6: Export logic unit tests

**Agent**: `qa-testing-agent`

**Files:**
- Create: `test/features/pay_applications/data/services/pay_app_excel_exporter_test.dart`
- Create: `test/features/pay_applications/domain/usecases/export_pay_app_use_case_test.dart`
- Create: `test/features/quantities/data/datasources/local/entry_quantity_local_datasource_date_range_test.dart`

#### Step 4.6.1: Create PayAppExcelExporter unit test

Test:
- `generate` produces non-empty Uint8List
- Generated workbook has a 'G703' sheet
- Header rows contain project name and application number
- Column headers match G703 format (10 columns)
- Data rows match bid item count
- Totals row sums correctly
- Percent complete = totalEarnedToDate / totalScheduledValue
- Balance to finish = totalScheduledValue - totalEarnedToDate
- Zero quantities produce 0.0 values (not errors)
- Empty bid items list throws StateError (handled by use case)

#### Step 4.6.2: Create ExportPayAppUseCase unit test

Test with mock repositories:
- Full export flow succeeds and returns ExportPayAppResult with artifact + payApp + localPath
- Empty bid items throws StateError
- Artifact save failure throws StateError
- PayApp save failure rolls back artifact (delete called)
- Replace flow soft-deletes prior pay app and artifact before saving new ones
- Period quantities are passed through to exporter
- Cumulative quantities use '1900-01-01' as start date
- Previous pay app is fetched when previousApplicationId is provided

#### Step 4.6.3: Create EntryQuantityLocalDatasource getByDateRange test

Test:
- Returns correct totals for quantities within date range
- Excludes quantities outside date range
- Excludes soft-deleted quantities
- Returns empty map when no quantities exist
- Groups by bid_item_id correctly

**Verification:**
CI handles all test execution. Local gate:
```
pwsh -Command "flutter analyze test/features/pay_applications/"
pwsh -Command "flutter analyze test/features/quantities/"
```
Expected: No analysis issues found.
