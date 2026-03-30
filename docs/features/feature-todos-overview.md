---
feature: todos
type: overview
scope: Task management with priorities
updated: 2026-03-30
---

# Todos Feature Overview

## Purpose

The Todos feature provides task management for construction inspectors — create, track, and prioritize to-do items. Todos can be scoped to a project or a daily entry, and support priority levels, due dates, and completion tracking.

## Key Responsibilities

- **Todo CRUD**: Create, read, update, and delete to-do items
- **Priority Levels**: Three-tier priority system — low, normal, high
- **Due Date Tracking**: Optional due dates with overdue and due-today detection
- **Completion Tracking**: Toggle completion status; bulk-delete completed items
- **Filtering & Sorting**: In-memory filter (all/active/completed) and sort (default/dueDate/priority/newest); repository-backed query filters (overdue, due today, high priority)
- **Project & Entry Scoping**: Todos optionally linked to a project or daily entry
- **Role Guard**: Write operations blocked when `AuthProvider.canEditFieldData` is false (viewer role)
- **Badge Count**: `getIncompleteCount()` for the Toolbox hub card badge

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/todos/di/todos_providers.dart` | DI wiring — registers `TodoProvider` with role guard |
| `lib/features/todos/data/models/todo_item.dart` | `TodoItem` model + `TodoPriority` enum |
| `lib/features/todos/data/datasources/local/todo_item_local_datasource.dart` | SQLite CRUD for todo items |
| `lib/features/todos/data/datasources/remote/todo_item_remote_datasource.dart` | Supabase reads/writes for todo items |
| `lib/features/todos/data/repositories/todo_item_repository_impl.dart` | Repository implementation — coordinates local + remote |
| `lib/features/todos/domain/repositories/todo_item_repository.dart` | `TodoItemRepository` interface |
| `lib/features/todos/presentation/providers/todo_provider.dart` | `TodoProvider` — state, filtering, sorting, write guard |
| `lib/features/todos/presentation/screens/todos_screen.dart` | `TodosScreen` — main task list UI |

## Screens (1)

| Screen | Route Trigger |
|--------|--------------|
| `TodosScreen` | Navigated to from Toolbox hub |

## Providers (1)

| Provider | Responsibility |
|----------|---------------|
| `TodoProvider` | Todo list state, CRUD actions, filter/sort, incomplete badge count, viewer-role write guard |

## Data Sources

- **SQLite**: Local todo item storage via `TodoItemLocalDatasource`
- **Supabase**: Remote sync via `TodoItemRemoteDatasource`

## Integration Points

**Depends on:**
- `auth` — `AuthProvider.canEditFieldData` for write guard; `AuthProvider` passed to DI
- `projects` — `ProjectProvider` used on `TodosScreen` to scope todos to a project
- `core/database` — SQLite access

**Required by:**
- `toolbox` — navigates to `TodosScreen`; reads `TodoProvider.getIncompleteCount()` for hub card badge
- `entries` — `TodoProvider.getByEntryId()` used in entry editor to display linked todos

## Offline Behavior

Todos are **fully offline-capable**. All CRUD operates against local SQLite. Changes are captured in the `change_log` table via SQLite triggers and pushed to Supabase during the next sync cycle.
