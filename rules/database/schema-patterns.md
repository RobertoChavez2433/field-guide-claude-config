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
- snake_case: `project_id`, `created_at`, `sync_status`
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
    sync_status TEXT DEFAULT 'pending',
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
  CREATE INDEX IF NOT EXISTS idx_projects_sync_status ON projects(sync_status);
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
static const int _databaseVersion = 21;  // Increment for each migration

// In onUpgrade callback
onUpgrade: (db, oldVersion, newVersion) async {
  if (oldVersion < 21) {
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

## Seed Data

### Seed Version Tracking
```dart
// In seed_data_service.dart
static const int currentSeedVersion = 5;  // Increment when seed data changes

// Check if reseed needed
final storedVersion = prefs.getInt('seedVersion') ?? 0;
if (storedVersion < currentSeedVersion) {
  await _seedDatabase();
  prefs.setInt('seedVersion', currentSeedVersion);
}
```

### JSON Seed Format
```json
// In assets/seed_data/forms.json
{
  "forms": [
    {
      "id": "form-0582b-v1",
      "name": "MDOT 0582B",
      "fields": [...]
    }
  ]
}
```

## Common Patterns

### Sync Status Column
```sql
sync_status TEXT DEFAULT 'pending'
-- Values: 'pending', 'synced', 'error', 'failed'
```

### Timestamps
```sql
created_at TEXT NOT NULL,
updated_at TEXT NOT NULL,
synced_at TEXT
```

### Soft Delete
```sql
deleted_at TEXT,
is_deleted INTEGER DEFAULT 0
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
static const int _databaseVersion = 21;  // Was 20
```

## Debugging

```dart
// List all tables
final tables = await db.rawQuery(
  "SELECT name FROM sqlite_master WHERE type='table'"
);
debugPrint('Tables: $tables');

// Show table schema
final schema = await db.rawQuery("PRAGMA table_info(projects)");
debugPrint('Schema: $schema');

// Check indexes
final indexes = await db.rawQuery(
  "SELECT name, tbl_name FROM sqlite_master WHERE type='index'"
);
debugPrint('Indexes: $indexes');
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
- [ ] Seed version updated (if seed data changed)

## Testing
- [ ] Fresh install works
- [ ] Upgrade from previous version preserves data
- [ ] Queries use indexes (EXPLAIN ANALYZE)
```
