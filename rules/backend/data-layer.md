---
paths:
  - "lib/data/**/*.dart"
  - "lib/services/**/*.dart"
---

# Backend/Data Layer Guidelines

## Common Commands
```bash
flutter test test/data/             # Test data layer
flutter test test/services/         # Test services
sqlite3 path/to/db.sqlite           # Inspect database
npx supabase db diff                # Check schema changes
npx supabase migration new name     # Create migration
```

## Code Style

### Model Pattern
```dart
class Example {
  final String id;
  final String name;
  final DateTime createdAt;
  final DateTime updatedAt;

  Example({
    String? id,
    required this.name,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) : id = id ?? const Uuid().v4(),
       createdAt = createdAt ?? DateTime.now(),
       updatedAt = updatedAt ?? DateTime.now();

  Example copyWith({String? name}) => Example(
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

  factory Example.fromMap(Map<String, dynamic> map) => Example(
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
```dart
// Local (SQLite)
class ExampleLocalDatasource {
  final DatabaseService _db;

  Future<List<Example>> getAll() async {
    final db = await _db.database;
    final maps = await db.query('examples');
    return maps.map((m) => Example.fromMap(m)).toList();
  }
}

// Remote (Supabase)
class ExampleRemoteDatasource {
  final SupabaseClient _client;

  Future<List<Example>> getAll() async {
    final response = await _client.from('examples').select();
    return response.map((m) => Example.fromMap(m)).toList();
  }
}
```

## State Management

### Provider for Data
```dart
class ExampleProvider extends ChangeNotifier {
  final ExampleRepository _repository;
  List<Example> _items = [];
  bool _isLoading = false;
  String? _error;

  Future<void> loadItems() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _items = await _repository.getAll();
    } catch (e) {
      _error = e.toString();
    }

    _isLoading = false;
    notifyListeners();
  }
}
```

## Database

### Schema Version
Current: v8 (see `lib/core/database/database_service.dart`)

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
- [ ] Model changes:
- [ ] Repository changes:
- [ ] Migration required: Yes/No
- [ ] Sync impact: None/Local/Remote

## Testing
- [ ] Unit tests for models
- [ ] Repository tests with mocks
- [ ] Migration tested (upgrade path)
```
