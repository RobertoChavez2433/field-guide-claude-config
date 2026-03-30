---
feature: todos
type: architecture
updated: 2026-03-30
---

# Todos Feature Architecture

## Directory Structure

```
lib/features/todos/
├── todos.dart                                        # Feature barrel export
├── di/
│   └── todos_providers.dart                          # DI wiring (Tier 4)
├── data/
│   ├── datasources/
│   │   ├── local/
│   │   │   └── todo_item_local_datasource.dart       # SQLite CRUD
│   │   └── remote/
│   │       └── todo_item_remote_datasource.dart      # Supabase reads/writes
│   ├── models/
│   │   └── todo_item.dart                            # TodoItem model + TodoPriority enum
│   └── repositories/
│       ├── repositories.dart
│       └── todo_item_repository_impl.dart            # Repository implementation
├── domain/
│   ├── domain.dart
│   └── repositories/
│       ├── repositories.dart
│       └── todo_item_repository.dart                 # TodoItemRepository interface
└── presentation/
    ├── providers/
    │   └── todo_provider.dart                        # TodoProvider + TodoFilter + TodoSort
    └── screens/
        └── todos_screen.dart                         # TodosScreen
```

## Data Layer

### Models

| Model | Purpose |
|-------|---------|
| `TodoItem` | Core task record — title, description, due date, priority, completion status, optional project/entry association |
| `TodoPriority` | Enum — `low`, `normal`, `high` (stored as smallint index in Supabase) |

#### TodoItem Fields

| Field | Type | Notes |
|-------|------|-------|
| `id` | `String` | UUID, auto-generated |
| `projectId` | `String?` | Optional project association |
| `entryId` | `String?` | Optional daily entry association |
| `title` | `String` | Required |
| `description` | `String?` | Optional detail |
| `isCompleted` | `bool` | Default false |
| `dueDate` | `DateTime?` | Optional; enables overdue/due-today computed properties |
| `priority` | `TodoPriority` | Default `normal` |
| `createdAt` | `DateTime` | Auto-populated |
| `updatedAt` | `DateTime` | Updated on every `copyWith` |
| `createdByUserId` | `String?` | Supabase auth user ID |

Computed properties: `isOverdue`, `isDueToday`, `priorityLabel`.

Priority serialization: stored as `int` index (`0`=low, `1`=normal, `2`=high) in both SQLite and Supabase. Deserialization supports both legacy int and new string formats.

### Local Datasource

| Class | Responsibility |
|-------|---------------|
| `TodoItemLocalDatasource` | SQLite CRUD for todo items — get by id/project/entry/priority/overdue/due-today, create, update, toggle complete, delete, deleteCompleted, getIncompleteCount |

### Remote Datasource

| Class | Responsibility |
|-------|---------------|
| `TodoItemRemoteDatasource` | Supabase reads/writes for todo items — mirrors local datasource operations for sync |

### Repository

| Class | Responsibility |
|-------|---------------|
| `TodoItemRepositoryImpl` | Coordinates `TodoItemLocalDatasource` and `TodoItemRemoteDatasource`; implements `TodoItemRepository` |

## Domain Layer

### Repository Interface

| Class | Responsibility |
|-------|---------------|
| `TodoItemRepository` | Abstract interface — `getById`, `getAll`, `getByProjectId`, `getByEntryId`, `getIncomplete`, `getCompleted`, `getByPriority`, `getOverdue`, `getDueToday`, `create`, `save`, `update`, `toggleComplete`, `delete`, `deleteByProjectId`, `deleteCompleted`, `getIncompleteCount` |

No use cases — this is a standard CRUD feature. All orchestration lives in `TodoProvider`.

## Presentation Layer

### Providers

| Class | Type | Responsibility |
|-------|------|---------------|
| `TodoProvider` | `ChangeNotifier` | Todo list state, CRUD actions, filter/sort, badge count, viewer-role write guard |
| `TodoFilter` | `enum` | In-memory filter applied to loaded list: `all`, `active`, `completed` |
| `TodoSort` | `enum` | In-memory sort: `defaultSort`, `dueDate`, `priority`, `newest` |

`TodoProvider` holds a `canWrite` callback (set from `AuthProvider.canEditFieldData`) that blocks all write operations for viewer-role users.

Default sort order: incomplete first, then by priority (high to low), then by due date (earliest first), then by creation date (newest first).

Repository-backed query methods (`loadByPriority`, `loadOverdue`, `loadDueToday`) replace the in-memory list entirely and are distinct from the in-memory `TodoFilter`.

### Screens (1 total)

| Screen | Purpose |
|--------|---------|
| `TodosScreen` | Main task list — filter chips, sort controls, create/edit/delete todo items, completion toggle |

`TodosScreen` reads `ProjectProvider` to scope the displayed todos to the currently selected project.

## DI Wiring (`di/todos_providers.dart`)

`todoProviders(...)` returns a `List<SingleChildWidget>` (Tier 4):

- `ChangeNotifierProvider` for `TodoProvider` — constructed with `TodoItemRepository` and a `canWrite` closure bound to `AuthProvider.canEditFieldData`

Requires `TodoItemRepository` and `AuthProvider` passed in from the app-level DI setup.

## Architectural Patterns

### Standard Clean Architecture CRUD
Single model, single repository interface + implementation, local + remote datasources for offline-first with sync. No use case classes — the feature is simple enough that `TodoProvider` acts as the orchestration layer directly.

### Viewer-Role Write Guard
All mutating methods in `TodoProvider` check `canWrite()` before proceeding. The `canWrite` callback is injected at construction time via `todos_providers.dart` from `AuthProvider.canEditFieldData`. This prevents viewers from creating, modifying, or deleting todos without introducing auth coupling into the domain layer.

### Dual Filtering Model
Two complementary filtering mechanisms coexist:
- **In-memory** (`TodoFilter` / `TodoSort`): Applied instantly to the currently loaded list via `_getFilteredAndSortedTodos()`.
- **Repository-backed** (`loadByPriority`, `loadOverdue`, `loadDueToday`): Triggers a fresh database query and replaces the list. Used for filter chips that require server-side semantics (e.g., overdue requires date comparison).

### Priority Serialization
`TodoPriority` is stored as a smallint index in Supabase (not a string) to match the PostgreSQL column type. `fromMap` supports both int and string formats for backward compatibility.

## Relationships to Other Features

| Feature | Relationship |
|---------|-------------|
| **Toolbox** | Navigates to `TodosScreen`; reads `TodoProvider.getIncompleteCount()` for hub badge |
| **Entries** | `TodoProvider.getByEntryId()` surfaces linked todos in the entry editor |
| **Auth** | `AuthProvider.canEditFieldData` injected as `canWrite` guard; `AuthProvider` passed to DI |
| **Projects** | `ProjectProvider` consumed on `TodosScreen` to scope the todo list to the active project |
| **Sync** | SQLite triggers auto-populate `change_log` on todo mutations; no per-model sync status needed |
