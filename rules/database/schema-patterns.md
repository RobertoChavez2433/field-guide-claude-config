---
paths:
  - "lib/core/database/**/*.dart"
---

# Database Schema Patterns

## Quick Reference

### Key Files
See `rules/backend/data-layer.md` for the full schema file tree. This file focuses on schema patterns and migration conventions.

### Current Version
See `database_service.dart` for current version (increment for migrations).

## Table Naming Conventions

### Standard Tables
- Plural snake_case: `daily_entries`, `bid_items`, `entry_personnel`
- Junction tables: `entry_` prefix + related entity

### Column Names
- snake_case: `project_id`, `created_at`
- Foreign keys: `{entity}_id` pattern
- Timestamps: `created_at`, `updated_at`, `synced_at`

## Schema Definition Pattern

### Table Creation
```dart
// In schema/[domain]_tables.dart
const String createProjectsTable = '''
  CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    contract_number TEXT,
    start_date TEXT,
    end_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )
''';
```

### Index Creation
```dart
// Always index:
// 1. Foreign key columns
// 2. Frequently filtered columns (date, status)
// 3. Search columns (name, title)

const String createProjectsIndexes = '''
  CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
''';
```

### Foreign Keys
```dart
// Enable foreign keys (done in database_service.dart)
await db.execute('PRAGMA foreign_keys = ON');

// Table with foreign key
const String createDailyEntriesTable = '''
  CREATE TABLE IF NOT EXISTS daily_entries (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    date TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
  )
''';
```

## Migration Pattern

### Version Increment
```dart
// In database_service.dart
// Current version: 46 — increment for each migration

// openDatabase pattern (version + onConfigure for PRAGMAs)
final db = await openDatabase(
  path,
  version: 46,
  onCreate: _onCreate,
  onUpgrade: _onUpgrade,
  onConfigure: (db) async {
    // Use rawQuery — Android API 36 rejects PRAGMA via execute()
    await db.rawQuery('PRAGMA journal_mode=WAL');
    await db.rawQuery('PRAGMA foreign_keys=ON');
  },
);

// In onUpgrade callback
onUpgrade: (db, oldVersion, newVersion) async {
  if (oldVersion < 46) {
    await db.execute('ALTER TABLE photos ADD COLUMN caption TEXT');
    await db.execute('CREATE INDEX idx_photos_caption ON photos(caption)');
  }
}
```

### Safe Migration
```dart
// Check if column exists before adding
final columns = await db.rawQuery("PRAGMA table_info(photos)");
final hasCaption = columns.any((c) => c['name'] == 'caption');
if (!hasCaption) {
  await db.execute('ALTER TABLE photos ADD COLUMN caption TEXT');
}
```

### Data Migration
```dart
// Migrate data during version upgrade
if (oldVersion < 20) {
  // Add new column
  await db.execute('ALTER TABLE entries ADD COLUMN status TEXT DEFAULT "draft"');
  // Migrate existing data
  await db.execute("UPDATE entries SET status = 'complete' WHERE activities IS NOT NULL");
}
```

## Common Patterns

### Sync Status Column

**DEPRECATED**: Per-row `sync_status` columns are no longer used. The sync engine uses the `change_log` table populated by SQLite triggers. Do not add `sync_status` columns to new tables.

### Timestamps
```sql
created_at TEXT NOT NULL,
updated_at TEXT NOT NULL,
synced_at TEXT
```

### Soft Delete
```sql
deleted_at TEXT,
deleted_by TEXT
```

## Anti-Patterns

### DON'T: Missing Indexes on FKs
```dart
// BAD - no index on foreign key
'project_id TEXT REFERENCES projects(id)'

// GOOD - index on foreign key
'project_id TEXT REFERENCES projects(id)'
// + CREATE INDEX idx_entries_project ON entries(project_id);
```

### DON'T: Hardcoded IDs
```dart
// BAD
'SELECT * FROM projects WHERE id = "abc123"'

// GOOD - use parameterized queries
await db.query('projects', where: 'id = ?', whereArgs: [projectId]);
```

### DON'T: Skip Version Bump
```dart
// BAD - schema changed but version unchanged
// This won't trigger migration on existing installs!

// GOOD - always increment version with schema changes
// Increment _databaseVersion (currently 46) for every schema change
```

## Debugging

```dart
// List all tables
final tables = await db.rawQuery(
  "SELECT name FROM sqlite_master WHERE type='table'"
);
Logger.db('Tables: $tables');

// Show table schema
final schema = await db.rawQuery("PRAGMA table_info(projects)");
Logger.db('Schema: $schema');

// Check indexes
final indexes = await db.rawQuery(
  "SELECT name, tbl_name FROM sqlite_master WHERE type='index'"
);
Logger.db('Indexes: $indexes');
```

## Quality Checklist

- [ ] All tables have appropriate indexes on FKs and filtered columns
- [ ] Foreign keys have ON DELETE CASCADE where appropriate
- [ ] Timestamps use ISO 8601 format (TEXT in SQLite)
- [ ] TEXT IDs used consistently (not INTEGER autoincrement)
- [ ] Version incremented for schema changes
- [ ] Migration tested from previous version
- [ ] Query performance verified with EXPLAIN

## Pull Request Template
```markdown
## Database Changes
- [ ] Schema tables affected: [list]
- [ ] Version bump: [old] -> [new]
- [ ] Migration tested (upgrade from previous version)
- [ ] Indexes added for new FKs/filters

## Testing
- [ ] Fresh install works
- [ ] Upgrade from previous version preserves data
- [ ] Queries use indexes (EXPLAIN ANALYZE)
```
