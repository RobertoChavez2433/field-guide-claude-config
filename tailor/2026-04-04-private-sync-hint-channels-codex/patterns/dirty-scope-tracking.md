# Pattern: Dirty Scope Tracking

## How We Do It

The `DirtyScopeTracker` maintains a set of `DirtyScope` objects representing invalidated data regions (company-wide, project-scoped, or table+project-scoped). Remote hints (Broadcast or FCM) call `markDirty()`, and the sync engine reads `isDirty()` / `dirtyProjectIdsFor()` to determine which tables/projects need pulling. The tracker validates table names against `SyncRegistry`, caps at 500 scopes (degrading to company-wide), and supports expiration-based pruning. This pattern is unchanged by the private channel spec — only the source of `markDirty()` calls changes (from predictable channel to opaque channel).

## Exemplars

### DirtyScopeTracker (`lib/features/sync/engine/dirty_scope_tracker.dart:7`)

```dart
class DirtyScopeTracker {
  static const int maxDirtyScopes = 500;
  final Set<DirtyScope> _dirtyScopes = {};

  void markDirty({String? projectId, String? tableName}) {
    final scope = DirtyScope(
      projectId: projectId, tableName: tableName, markedAt: DateTime.now().toUtc(),
    );
    // Validate table name against registry
    if (tableName != null && !_validTableNames.contains(tableName)) return;
    // Cap at maxDirtyScopes, degrade to company-wide
    if (!removedExisting && _dirtyScopes.length >= maxDirtyScopes) {
      _dirtyScopes..clear()..add(DirtyScope(projectId: null, tableName: null, ...));
      return;
    }
    _dirtyScopes.add(scope);
  }

  bool isDirty(String tableName, {String? projectId}) { ... }
  Set<String> dirtyProjectIdsFor(String tableName, Iterable<String> allProjectIds) { ... }
  void clearAll() { ... }
  int pruneExpired() { ... }
}
```

### DirtyScope (`lib/features/sync/domain/sync_types.dart:84`)

```dart
@immutable
class DirtyScope {
  final String? projectId;
  final String? tableName;
  final DateTime markedAt;

  bool get isCompanyWide => projectId == null;
  bool get isAllTables => tableName == null;
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `markDirty()` | `dirty_scope_tracker.dart:17` | `void markDirty({String? projectId, String? tableName})` | Record invalidation from any source |
| `isDirty()` | `dirty_scope_tracker.dart:57` | `bool isDirty(String tableName, {String? projectId})` | Check if a table/project needs pulling |
| `hasDirtyScopes` | `dirty_scope_tracker.dart:83` | `bool get hasDirtyScopes` | Quick check for any pending invalidations |
| `dirtyProjectIdsFor()` | `dirty_scope_tracker.dart:103` | `Set<String> dirtyProjectIdsFor(String tableName, Iterable<String> allProjectIds)` | Get affected project IDs for a table |
| `clearAll()` | `dirty_scope_tracker.dart:89` | `void clearAll()` | Reset after successful sync |
| `pruneExpired()` | `dirty_scope_tracker.dart:96` | `int pruneExpired()` | Remove stale scopes |

## Imports

```dart
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';
```
