---
paths:
  - "lib/features/**/data/**/*.dart"
  - "lib/core/database/**/*.dart"
  - "lib/services/**/*.dart"
---

# Backend/Data Layer Guidelines

## Common Commands
```bash
flutter test test/features/projects/        # Test specific feature
flutter test test/features/                 # Test all features
flutter test test/                          # Run all tests
npx supabase db diff                        # Check schema changes
npx supabase migration new name             # Create migration
# Database location (Windows): %LOCALAPPDATA%\construction_inspector\construction_inspector.db
```

## Architecture

### Feature-First Organization
**All data layer implementation** lives in feature modules:
```
lib/features/[feature]/data/
├── models/         # Entity classes (*.dart)
├── repositories/   # Business logic + validation
└── datasources/    # CRUD operations (local + remote)
```

**IMPORTANT**:
- `lib/data/` is EMPTY (legacy structure, no files)
- `lib/services/database_service.dart` does NOT exist
- Correct path: `lib/core/database/database_service.dart`

**Example Feature Structure** (Projects feature):
```
lib/features/projects/
├── data/
│   ├── data.dart                      # Barrel export
│   ├── models/
│   │   └── project.dart               # Project model
│   ├── repositories/
│   │   └── project_repository.dart    # Business logic
│   └── datasources/
│       ├── local/
│       │   └── project_local_datasource.dart
│       └── remote/
│           └── project_remote_datasource.dart
└── presentation/
    ├── presentation.dart              # Barrel export
    ├── providers/
    │   └── project_provider.dart
    ├── screens/
    │   └── project_list_screen.dart
    └── widgets/
        └── project_card.dart
```

**13 Features** (all follow same pattern):
auth, contractors, dashboard, entries, locations, pdf, photos, projects, quantities, settings, sync, toolbox, weather

### Database Schema Organization
```
lib/core/database/
├── database_service.dart  # Main database class (version 20)
├── seed_data_service.dart # Sample data seeding
├── seed_data_loader.dart  # Load seed data from JSON
└── schema/                # Modular table definitions
    ├── schema.dart           # Barrel export (imports all tables)
    ├── core_tables.dart      # projects, locations
    ├── contractor_tables.dart # contractors, equipment
    ├── entry_tables.dart      # daily_entries, entry_contractors, entry_equipment
    ├── personnel_tables.dart  # personnel_types, entry_personnel, entry_personnel_counts
    ├── quantity_tables.dart   # bid_items, entry_quantities
    ├── photo_tables.dart      # photos
    ├── toolbox_tables.dart    # toolbox talks
    └── sync_tables.dart       # sync metadata
```

## Code Style

### Model Pattern
See `lib/features/projects/data/models/project.dart` for reference implementation.

```dart
// Example: lib/features/projects/data/models/project.dart
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

  Project copyWith({String? name}) => Project(
    id: id,
    name: name ?? this.name,
    createdAt: createdAt,
    updatedAt: DateTime.now(),  // Always update
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

### Repository Pattern
```dart
abstract class BaseRepository<T> {
  Future<List<T>> getAll();
  Future<T?> getById(String id);
  Future<void> insert(T item);
  Future<void> update(T item);
  Future<void> delete(String id);
}
```

### Datasource Pattern
See `lib/features/projects/data/datasources/` for reference implementations.

```dart
// Local (SQLite): lib/features/projects/data/datasources/local/project_local_datasource.dart
class ProjectLocalDatasource {
  final DatabaseService _db;

  Future<List<Project>> getAll() async {
    final db = await _db.database;
    final maps = await db.query('projects', orderBy: 'name ASC');
    return maps.map((m) => Project.fromMap(m)).toList();
  }

  Future<void> insert(Project project) async {
    final db = await _db.database;
    await db.insert('projects', project.toMap());
  }
}

// Remote (Supabase): lib/features/projects/data/datasources/remote/project_remote_datasource.dart
class ProjectRemoteDatasource {
  final SupabaseClient _client;

  Future<List<Project>> getAll() async {
    final response = await _client
        .from('projects')
        .select()
        .order('name', ascending: true);
    return (response as List).map((m) => Project.fromMap(m)).toList();
  }
}
```

## State Management

### Provider for Data
See `lib/features/projects/presentation/providers/project_provider.dart` for reference.

```dart
// lib/features/projects/presentation/providers/project_provider.dart
class ProjectProvider extends ChangeNotifier {
  final ProjectRepository _repository;
  List<Project> _projects = [];
  bool _isLoading = false;
  String? _error;

  List<Project> get projects => _projects;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> loadProjects() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _projects = await _repository.getAll();
    } catch (e) {
      _error = e.toString();
    }

    _isLoading = false;
    notifyListeners();
  }
}
```

## Database

### Schema Files
Schema definitions: `lib/core/database/schema/` (modular table definitions)
Database service: `lib/core/database/database_service.dart`
Seed data: `lib/core/database/seed_data_service.dart`, `seed_data_loader.dart`
Current version: 20 (see `lib/core/database/database_service.dart`)

### Indexes
Add indexes on:
- Foreign key columns
- Frequently filtered columns (date, status)
- Search columns (name, title)

### Migrations
```dart
if (oldVersion < 9) {
  await db.execute('ALTER TABLE examples ADD COLUMN new_field TEXT');
}
```

## Sync (Offline-First)

### Sync Status Enum
```dart
enum SyncStatus { pending, synced, error, failed }
```

### Sync Flow
1. Save locally first (immediate)
2. Queue for sync
3. Process queue when online
4. Use last-write-wins (updated_at)

## Error Handling
```dart
class RepositoryResult<T> {
  final T? data;
  final String? error;
  bool get isSuccess => error == null;
}
```

## Logging
```dart
debugPrint('DB: Query executed in ${sw.elapsed}');
```

## Pull Request Template
```markdown
## Data Layer Changes
- [ ] Feature module: [auth/contractors/entries/etc.]
- [ ] Model changes: [description]
- [ ] Repository changes: [description]
- [ ] Datasource changes: [Local/Remote/Both]
- [ ] Migration required: Yes/No
- [ ] Sync impact: None/Local/Remote/Both
- [ ] Database version bump: [current] → [new]

## Files Changed
- [ ] lib/features/[feature]/data/models/
- [ ] lib/features/[feature]/data/repositories/
- [ ] lib/features/[feature]/data/datasources/
- [ ] lib/core/database/database_service.dart (if migration)
- [ ] lib/core/database/schema/ (if schema change)

## Testing
- [ ] Unit tests for models (toMap/fromMap)
- [ ] Repository tests with mocks
- [ ] Migration tested (upgrade path from previous version)
- [ ] Existing data preserved after migration
```
