# Backend Data Layer Agent Memory

## Architecture Overview

Feature-First Clean Architecture. All data layer code lives in feature modules — there is NO `lib/data/` directory (legacy structure, empty). `lib/services/database_service.dart` does NOT exist; the correct path is `lib/core/database/database_service.dart`.

```
lib/features/[feature]/data/
├── models/         # Entity classes
├── repositories/   # Business logic + validation
└── datasources/
    ├── local/      # SQLite CRUD via GenericLocalDatasource
    └── remote/     # Supabase API calls
```

## Repository Pattern

### BaseRepository (abstract)

`lib/shared/repositories/base_repository.dart`

```dart
abstract class BaseRepository<T> {
  Future<T?> getById(String id);
  Future<List<T>> getAll();
  Future<PagedResult<T>> getPaged({required int offset, required int limit});
  Future<int> getCount();
  Future<void> save(T item);   // upsert: insert or update
  Future<void> delete(String id);
}
```

### ProjectScopedRepository (abstract)

Extends `BaseRepository<T>` with project-scoped operations:
- `getByProjectId(projectId)`, `getByProjectIdPaged(...)`, `getCountByProject(...)`
- `create(item)` → `RepositoryResult<T>` (with validation)
- `update(item)` → `RepositoryResult<T>` (with validation)

### RepositoryResult

```dart
class RepositoryResult<T> {
  final T? data;
  final String? error;
  final bool isSuccess;

  factory RepositoryResult.success(T data);
  factory RepositoryResult.failure(String error);
  factory RepositoryResult.empty();
}
```

### Concrete Repository Pattern

Repositories coordinate local datasource access and add business logic:

```dart
class ProjectRepository implements BaseRepository<Project> {
  final ProjectLocalDatasource _localDatasource;
  final DatabaseService _databaseService;

  // Standard: delegates to local datasource
  Future<Project?> getById(String id) => _localDatasource.getById(id);

  // With validation: checks uniqueness before insert
  Future<RepositoryResult<Project>> create(Project project) async {
    final existing = await _localDatasource.getByProjectNumber(project.projectNumber);
    if (existing != null) return RepositoryResult.failure('Already exists');
    await _localDatasource.insert(project);
    return RepositoryResult.success(project);
  }

  // With sync-control: suppresses change_log triggers for draft operations
  Future<void> saveDraftSuppressed(Project project) async {
    final db = await _databaseService.database;
    await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
    try {
      await save(project);
    } finally {
      await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
    }
  }
}
```

## Datasource Pattern

### BaseLocalDatasource (abstract interface)

`lib/shared/datasources/base_local_datasource.dart`

Methods: `getById`, `getAll`, `insert`, `update`, `delete`, `insertAll`

### GenericLocalDatasource (abstract generic implementation)

`lib/shared/datasources/generic_local_datasource.dart`

Provides full CRUD + soft-delete + pagination. Subclasses only need to implement:

```dart
abstract class GenericLocalDatasource<T> implements BaseLocalDatasource<T> {
  DatabaseService get db;
  String get tableName;
  String get defaultOrderBy;
  T fromMap(Map<String, dynamic> map);
  Map<String, dynamic> toMap(T item);
  String getId(T item);
}
```

### Concrete Local Datasource

```dart
class ProjectLocalDatasource extends GenericLocalDatasource<Project> {
  @override final DatabaseService db;
  ProjectLocalDatasource(this.db);

  @override String get tableName => 'projects';
  @override String get defaultOrderBy => 'name ASC';
  @override Project fromMap(Map<String, dynamic> map) => Project.fromMap(map);
  @override Map<String, dynamic> toMap(Project item) => item.toMap();
  @override String getId(Project item) => item.id;

  // Custom query using getWhere() helper
  Future<List<Project>> getActive() => getWhere(
    where: 'is_active = ?', whereArgs: [1],
  );
}
```

### GenericLocalDatasource Built-In Methods

| Method | Behavior |
|--------|----------|
| `getById(id)` | Filters `deleted_at IS NULL AND id = ?` |
| `getByIdIncludingDeleted(id)` | No soft-delete filter (restore/conflict use) |
| `getAll()` | Filters `deleted_at IS NULL`, ordered by `defaultOrderBy` |
| `insert(item)` | Standard SQLite insert with Logger.db |
| `update(item)` | Updates by ID with Logger.db |
| `delete(id)` | Delegates to `softDelete(id)` — sets `deleted_at` |
| `softDelete(id, {userId?})` | Sets `deleted_at`, `deleted_by`, `updated_at` |
| `restore(id)` | Clears `deleted_at`, `deleted_by`, updates `updated_at` |
| `hardDelete(id)` | Permanently removes row (for purge/delete-forever) |
| `getDeleted()` | Returns soft-deleted records (Trash screen) |
| `purgeExpired({retentionDays=30})` | Hard-deletes rows with `deleted_at` older than N days |
| `insertAll(items)` | Batch insert via `db.batch()` |
| `getWhere(...)` | Custom WHERE + automatic soft-delete filter |
| `countWhere(...)` | Counted query with soft-delete filter |
| `getPaged(...)` | Paginated query, excludes soft-deleted |

### Remote Datasource Pattern

```dart
class ProjectRemoteDatasource {
  final SupabaseClient _client;

  Future<List<Project>> getAll() async {
    final response = await _client.from('projects').select().order('name');
    return (response as List).map((m) => Project.fromMap(m)).toList();
  }
}
```

## Soft Delete System

### Critical Rule

**NEVER call `db.delete()` directly on user-facing tables.** Always use `SoftDeleteService` or repository `delete()` which delegates to `GenericLocalDatasource.softDelete()`.

The only exceptions are:
- `discardDraft()` in repositories (draft data never finalized, sync suppressed)
- `purgeExpired()` for records older than 30 days
- `hardDelete()` for explicit "Delete Forever" actions

### Soft Delete Columns (all 16 synced tables)

```sql
deleted_at TIMESTAMPTZ  -- when deleted (null = active)
deleted_by UUID         -- who deleted
```

### Soft Delete Filter

`GenericLocalDatasource` applies `deleted_at IS NULL` to ALL read queries automatically. No manual filtering needed in subclasses.

### Sync Control for Delete Suppression

When performing operations that should not trigger `change_log` (drafts, pull operations):

```dart
final db = await _databaseService.database;
await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
try {
  // operations
} finally {
  await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
}
```

This is the same pattern used in `SyncEngine` during pull operations.

## Model Pattern

All models follow this standard structure. Reference: `lib/features/projects/data/models/project.dart`

```dart
class Project {
  final String id;
  final String name;
  final DateTime createdAt;
  final DateTime updatedAt;

  Project({
    String? id,
    required this.name,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) : id = id ?? const Uuid().v4(),
       createdAt = createdAt ?? DateTime.now(),
       updatedAt = updatedAt ?? DateTime.now();

  Project copyWith({String? name, ...}) => Project(
    id: id,
    name: name ?? this.name,
    createdAt: createdAt,
    updatedAt: DateTime.now(),  // Always update timestamp
  );

  Map<String, dynamic> toMap() => {
    'id': id,
    'name': name,
    'created_at': createdAt.toIso8601String(),
    'updated_at': updatedAt.toIso8601String(),
  };

  factory Project.fromMap(Map<String, dynamic> map) => Project(
    id: map['id'] as String,
    name: map['name'] as String,
    createdAt: DateTime.parse(map['created_at'] as String),
    updatedAt: DateTime.parse(map['updated_at'] as String),
  );
}
```

### Enum Serialization

```dart
// Serialize
'type': type.name   // ContractorType.sub → 'sub'

// Deserialize
type: ContractorType.values.byName(map['type'] as String)
```

**Note**: Per-row sync_status fields are deprecated. The sync engine uses `change_log` triggers. See `rules/sync/sync-patterns.md`.

## Database Service

`lib/core/database/database_service.dart` — Singleton.

- Current version: **46** (increment for each migration)
- WAL mode enabled (Decision 17): `PRAGMA journal_mode=WAL` — supports concurrent access from background isolates
- Foreign keys enabled: `PRAGMA foreign_keys=ON`
- `SchemaVerifier.verify(db)` runs on every open (self-healing for missed migrations)
- Testing: `DatabaseService.forTesting()` returns in-memory singleton

### Schema Files (modular by domain)

```
lib/core/database/schema/
├── schema.dart              # Barrel export
├── core_tables.dart         # projects, locations, companies, user_profiles
├── contractor_tables.dart   # contractors, equipment
├── entry_tables.dart        # daily_entries, entry_contractors, entry_equipment
├── personnel_tables.dart    # personnel_types, entry_personnel, entry_personnel_counts
├── quantity_tables.dart     # bid_items, entry_quantities
├── photo_tables.dart        # photos
├── toolbox_tables.dart      # inspector_forms, form_responses, todo_items, calculation_history
└── sync_tables.dart         # change_log, conflict_log, sync_lock, sync_metadata, sync_control, ...
```

### SQLite Migration Pattern

```dart
// In database_service.dart onUpgrade
onUpgrade: (db, oldVersion, newVersion) async {
  if (oldVersion < 46) {
    await db.execute('ALTER TABLE photos ADD COLUMN caption TEXT');
    await db.execute('CREATE INDEX IF NOT EXISTS idx_photos_caption ON photos(caption)');
  }
}

// Safe: check if column exists before adding
final columns = await db.rawQuery("PRAGMA table_info(photos)");
final hasCaption = columns.any((c) => c['name'] == 'caption');
if (!hasCaption) {
  await db.execute('ALTER TABLE photos ADD COLUMN caption TEXT');
}
```

**CRITICAL**: Always increment `_databaseVersion` when changing schema. Failing to do so silently skips migrations on existing installs.

### Database File Location

- Android: app's internal storage (SQLite managed by sqflite)
- Windows desktop: `%LOCALAPPDATA%\construction_inspector\construction_inspector.db`

## Schema Conventions

### Table Naming

- Plural snake_case: `daily_entries`, `bid_items`, `entry_personnel`
- Junction tables: `entry_` prefix + related entity

### Column Naming

- snake_case: `project_id`, `created_at`
- Foreign keys: `{entity}_id` pattern
- Timestamps: `created_at TEXT NOT NULL`, `updated_at TEXT NOT NULL`, `synced_at TEXT`
- Soft delete: `deleted_at TEXT`, `deleted_by TEXT`

### ID Convention

TEXT UUIDs (not INTEGER autoincrement). Generated via `Uuid().v4()`.

### Standard Columns Pattern

```sql
CREATE TABLE IF NOT EXISTS my_table (
  id TEXT PRIMARY KEY,
  company_id TEXT NOT NULL,   -- multi-tenant FK
  project_id TEXT,            -- project scope if applicable
  -- domain columns
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted_at TEXT,
  deleted_by TEXT,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
)
```

### Index Strategy

Always index:
1. All foreign key columns
2. Frequently filtered columns (`date`, `status`)
3. `deleted_at` (every synced table)
4. Search columns (`name`, `title`)

```sql
CREATE INDEX IF NOT EXISTS idx_entries_project_id ON daily_entries(project_id);
CREATE INDEX IF NOT EXISTS idx_entries_deleted_at ON daily_entries(deleted_at);
CREATE INDEX IF NOT EXISTS idx_entries_date ON daily_entries(date);
```

## Logging

```dart
// All DB operations must log through Logger.db()
Logger.db('INSERT $tableName id=${getId(item)}');
Logger.db('UPDATE $tableName id=${getId(item)}');
Logger.db('SOFT_DELETE $tableName id=$id');
Logger.db('QUERY ${results.length} rows from $tableName');
```

Never use `debugPrint` — it's not captured by the logging system.

## Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| `db.delete()` without soft-delete check | Use `SoftDeleteService` or `repository.delete()` |
| Raw SQL in presentation layer | Move to repository or datasource |
| `firstWhere` without `orElse` | Use `.where(...).firstOrNull` |
| `catch (_)` without logging | Add `Logger.db(...)` or `Logger.error(...)` |
| Hardcoded IDs in queries | Use parameterized queries `WHERE id = ?` |
| Missing FK index | Always `CREATE INDEX IF NOT EXISTS idx_{table}_{column}` |
| Version bump skipped | Always increment `_databaseVersion` with schema changes |
| `lib/data/` directory | Does not exist. Use `lib/features/[feature]/data/` |

## Two-Pass Orphan Cleanup

`ProjectRepository.cleanupOrphanedProjects()` uses a two-pass safety system:
- **Pass 1**: Query orphaned projects → store as `_orphanCandidates` (no delete)
- **Pass 2**: Re-query orphans → intersect with candidates → delete only confirmed orphans

Prevents accidental deletion of projects that were briefly orphaned due to race conditions.

## PagedResult Model

```dart
class PagedResult<T> {
  final List<T> items;
  final int totalCount;
  final int offset;
  final int limit;

  bool get hasMore => offset + items.length < totalCount;
}
```

## Database Debugging

```dart
// List all tables
final tables = await db.rawQuery(
  "SELECT name FROM sqlite_master WHERE type='table'"
);

// Show table schema
final schema = await db.rawQuery("PRAGMA table_info(projects)");

// Check indexes
final indexes = await db.rawQuery(
  "SELECT name, tbl_name FROM sqlite_master WHERE type='index'"
);

// Verify foreign key pragma
await db.rawQuery("PRAGMA foreign_keys");
```
