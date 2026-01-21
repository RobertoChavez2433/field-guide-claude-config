# Architectural Patterns

## Overview

This document captures the architectural decisions and patterns used throughout the Construction Inspector app.

## Layer Architecture

The app follows a **Feature-First Clean Architecture** with clear separation:

```
lib/
├── core/        # Cross-cutting (router, theme, config, database)
├── shared/      # Base classes, common utilities
├── features/    # 12 feature modules (auth, entries, projects, etc.)
│   └── [feature]/
│       ├── data/         # Models, repositories, datasources
│       └── presentation/ # Screens, widgets, providers
├── data/        # LEGACY: barrel re-exports
├── presentation/# LEGACY: barrel re-exports
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

## UI Component Patterns

### Screen Structure

Standard screen template from `lib/features/entries/presentation/screens/home_screen.dart`:

1. `StatefulWidget` for screens with local state
2. `initState()` for initialization
3. `dispose()` for cleanup
4. Private `_build*()` methods for UI sections
5. Private action methods (e.g., `_createNewEntry()`)

### Card-Based Lists

List items rendered as tappable cards with:
- Leading icon/avatar
- Title and subtitle
- Trailing status indicator or action button

Reference: `lib/features/projects/presentation/screens/project_list_screen.dart:35-85`

### Split View / Master-Detail Pattern

Used in Calendar screen for entry list + report preview:

```
┌─────────────────────────────────────────────────┐
│ [Calendar Header + Month View]                  │
├─────────────────────────────────────────────────┤
│ Entry List (180px)  │  Report Preview (flex)    │
│ ┌────────────────┐  │ ┌───────────────────────┐ │
│ │ ▶ Location A   │  │ │ Weather: Sunny        │ │
│ │   Draft        │  │ │ Activities: ...       │ │
│ │                │  │ │ Safety: ...           │ │
│ │   Location B   │  │ │ [Edit] buttons        │ │
│ │   Complete     │  │ │                       │ │
│ └────────────────┘  │ └───────────────────────┘ │
└─────────────────────────────────────────────────┘
```

Implementation pattern (Reference: `lib/features/entries/presentation/screens/home_screen.dart:395-410`):
- Track `_selectedEntryId` state for highlighting
- Left panel: Fixed-width `SizedBox` with `ListView.builder`
- Right panel: `Expanded` widget with scrollable content
- Selection state updates preview via `setState()`
- Edit buttons pass section identifier as query parameter

Reference: `lib/features/entries/presentation/screens/home_screen.dart:326-760`

### Form Organization

Multi-step forms use Flutter's `Stepper` widget with:
- Step validation before advancing
- Custom controls builder for navigation buttons
- Form state preserved across steps

Reference: `lib/features/entries/presentation/screens/entry_wizard_screen.dart:80-95`

## Theming Pattern

Centralized theme with brand colors. Reference: `lib/core/theme/app_theme.dart:1-95`

### Color Naming

- Primary brand colors: `primaryBlue`, `secondaryBlue`
- Semantic colors: `success`, `warning`, `error`
- Domain-specific: `sunny`, `rainy`, `overcast` (weather tags)

### Theme Usage

Access via `Theme.of(context)` or direct `AppTheme.primaryBlue` for custom widgets.

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

### Clickable Stat Cards Pattern

Dashboard stat cards use `InkWell` wrapper with `onTap` parameter:

```dart
Widget _buildStatCard(String label, String value, IconData icon, Color color, {VoidCallback? onTap}) {
  return Card(
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: // ... content
    ),
  );
}
```

Reference: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:265-295`

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

Reference: `lib/data/models/models.dart` (legacy barrel export for backward compatibility).

## Enum Handling

Enums serialized/deserialized using `.name` and `.values.byName()`:

```dart
// Serialize
'type': type.name

// Deserialize
type: ContractorType.values.byName(map['type'] as String)
```

Reference: `lib/features/contractors/data/models/contractor.dart:47-53`
