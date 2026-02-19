---
paths:
  - "lib/**/*.dart"
---

# Architectural Patterns

## Overview

This document captures the architectural decisions and patterns used throughout the Construction Inspector app.

## Layer Architecture

The app follows a **Feature-First Clean Architecture** with clear separation:

```
lib/
├── core/        # Cross-cutting (router, theme, config, database)
│   └── database/
│       └── schema/  # Schema files organized by domain
├── shared/      # Base classes, common utilities
├── features/    # 13 feature modules
│   └── [feature]/
│       ├── data/         # Models, repositories, datasources
│       └── presentation/ # Screens, widgets, providers
│       # Note: No domain/ layer in most features (only sync uses full Clean Architecture)
└── services/    # Cross-cutting services
```

## Model Pattern

All data models follow a consistent structure. Reference: `lib/features/projects/data/models/project.dart:1-65`

### Standard Model Template

1. **Immutable fields** with final keyword
2. **UUID-based IDs** - Auto-generated if not provided
3. **Timestamp management** - `createdAt`, `updatedAt` auto-populated
4. **copyWith()** method for immutable updates
5. **toMap()** for SQLite/JSON serialization
6. **fromMap()** factory for deserialization

Example from `lib/features/contractors/data/models/contractor.dart:3-6`:
- Enums defined at file top (e.g., `ContractorType`)
- Helper getters for enum checks (e.g., `isPrime`, `isSub`)

### Nullable vs Required Fields

- Required: `id`, foreign keys, core identifiers
- Nullable: optional metadata, GPS coordinates, timestamps for optional actions

## Database Pattern

Single SQLite database with foreign key relationships. Reference: `lib/core/database/database_service.dart:1-180`

### Table Naming Convention

- Plural snake_case: `daily_entries`, `bid_items`, `entry_personnel`
- Junction tables: `entry_` prefix + related entity

### Indexing Strategy

Indexes on:
- All foreign key columns
- Frequently filtered columns (e.g., `date`)

Reference: `lib/core/database/database_service.dart:155-166`

## Navigation Pattern

Uses **go_router** with shell routes for persistent bottom nav. Reference: `lib/core/router/app_router.dart:1-110`

### Route Structure

- **Shell routes**: Screens with bottom navigation bar
- **Full-screen routes**: Wizard flows, detail views without nav bar

### Parameter Passing

- Path parameters for required IDs: `/entry/:projectId/:date`
- Query parameters for optional data: `?locationId=abc`

## State Management

Provider pattern implemented with:
- `ChangeNotifier` for reactive state
- `context.read<T>()` for actions (one-time reads)
- `Consumer<T>` or `context.watch<T>()` for rebuilds

### Loading Pattern

Use `addPostFrameCallback` to load data after widget is built:

```dart
@override
void initState() {
  super.initState();
  WidgetsBinding.instance.addPostFrameCallback((_) {
    _loadData();
  });
}
```

This prevents "setState during build" errors. Reference: `lib/features/entries/presentation/screens/home_screen.dart:32-35`

### Async Context Safety

Check `mounted` before using context after async operations:

```dart
Future<void> _doSomething() async {
  await someAsyncOperation();
  if (!mounted) return;
  context.read<Provider>().doThing();
}
```

## Anti-Patterns to Avoid

| Anti-Pattern | Why | Fix |
|--------------|-----|-----|
| `setState()` in `dispose()` | Widget already deactivated | Use `WidgetsBindingObserver` lifecycle |
| `Provider.of(context)` after async | Context may be invalid | Check `mounted` first |
| Hardcoded colors | Inconsistent theming | Use `AppTheme.*` constants |
| Skip barrel exports | Breaks imports | Update `models.dart`, `providers.dart` |
| `firstWhere` without `orElse` | Throws on empty | Use `.where(...).firstOrNull` |
| Save in `dispose()` | Context deactivated | Use `WidgetsBindingObserver.didChangeAppLifecycleState` |
| `.first` on empty list | Throws exception | Check `.isEmpty` or use `.firstOrNull` |

## Offline-First Pattern

### Sync Status

All syncable entities include `syncStatus` field:
- `pending` - Local changes not yet synced
- `synced` - In sync with server
- `error` - Sync failed

Reference: `lib/features/entries/data/models/daily_entry.dart:26`

### Photo Storage

Photos stored locally with:
- `filePath` - Local device path
- `remotePath` - Cloud storage URL (null until synced)

Reference: `lib/features/photos/data/models/photo.dart:1-65`

## Barrel Exports

Group related exports in a single file for cleaner imports.

## Enum Handling

Enums serialized/deserialized using `.name` and `.values.byName()`:

```dart
// Serialize
'type': type.name

// Deserialize
type: ContractorType.values.byName(map['type'] as String)
```

Reference: `lib/features/contractors/data/models/contractor.dart:47-53`
