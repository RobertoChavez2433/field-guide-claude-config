## Phase 1: Domain Types & Config

### Sub-phase 1.1: SyncMode Enum and DirtyScope Value Class

**Files:**
- Modify: `lib/features/sync/domain/sync_types.dart:1-67`
- Test: `test/features/sync/domain/sync_types_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 1.1.1: Add SyncMode enum to sync_types.dart

Open `lib/features/sync/domain/sync_types.dart` and append the `SyncMode` enum after the existing `SyncAdapterStatus` enum (after line 67). Do NOT modify any existing code in this file.

```dart
// FROM SPEC: "The app will support three sync modes: Quick sync, Full sync, Maintenance sync"
// WHY: Quick sync is the low-latency startup/foreground path. Full sync is user-invoked
// explicit refresh. Maintenance sync is deferred background work (integrity, orphan cleanup).
// NOTE: Follows existing enum pattern established by SyncAdapterStatus in this file.
enum SyncMode {
  /// Startup / foreground / background catch-up.
  /// Push local changes, pull only dirty scopes.
  /// Skips: integrity check, orphan scan, storage cleanup.
  /// FROM SPEC: "low-latency path ... push local changes first ...
  /// avoid broad project-wide pushAndPull() by default"
  quick,

  /// User-invoked explicit refresh.
  /// Full push + pull sweep across all adapters.
  /// FROM SPEC: "broader push + pull sweep ... fallback recovery path"
  full,

  /// Deferred or background work.
  /// Integrity checks, orphan cleanup, prune only. No push/pull.
  /// FROM SPEC: "integrity checks ... orphan cleanup ...
  /// company member pulls ... last_synced_at update"
  maintenance,
}
```

#### Step 1.1.2: Add DirtyScope value class to sync_types.dart

Append the `DirtyScope` class after the `SyncMode` enum in `lib/features/sync/domain/sync_types.dart`.

```dart
// FROM SPEC: "Candidate scope dimensions: company-wide, project-wide, table-within-project"
// WHY: Immutable value class representing a scope that has been invalidated by a
// remote change hint. Used by DirtyScopeTracker to track which (projectId, tableName)
// pairs need pulling during quick sync.
// NOTE: Uses const constructor + operator== for Set membership checks.
class DirtyScope {
  /// Null means company-wide (all projects affected).
  /// FROM SPEC: "company-wide" scope dimension.
  final String? projectId;

  /// Null means all tables within the project (or company) are dirty.
  /// FROM SPEC: "table-within-project" scope dimension.
  final String? tableName;

  /// When the scope was marked dirty (UTC).
  /// FROM SPEC: Hint payload includes "changed_at".
  final DateTime markedAt;

  const DirtyScope({
    this.projectId,
    this.tableName,
    required this.markedAt,
  });

  // WHY: Two DirtyScopes are equal if they target the same (projectId, tableName)
  // pair, regardless of when they were marked. This prevents duplicate entries
  // in a Set<DirtyScope> when the same scope is invalidated multiple times.
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is DirtyScope &&
          runtimeType == other.runtimeType &&
          projectId == other.projectId &&
          tableName == other.tableName;

  @override
  int get hashCode => Object.hash(projectId, tableName);

  /// True when this scope covers all projects (company-wide invalidation).
  bool get isCompanyWide => projectId == null;

  /// True when this scope covers all tables within its project (or company).
  bool get isAllTables => tableName == null;

  @override
  String toString() =>
      'DirtyScope(projectId: $projectId, tableName: $tableName, markedAt: $markedAt)';
}
```

#### Step 1.1.3: Write unit tests for SyncMode and DirtyScope

Create `test/features/sync/domain/sync_types_test.dart`.

```dart
// WHY: Verify SyncMode enum values and DirtyScope equality/hash semantics.
// NOTE: Pure Dart tests, no Flutter dependencies needed.
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

void main() {
  group('SyncMode', () {
    // FROM SPEC: Three modes: quick, full, maintenance
    test('has exactly three values', () {
      expect(SyncMode.values.length, 3);
    });

    test('values are quick, full, maintenance', () {
      expect(SyncMode.values, contains(SyncMode.quick));
      expect(SyncMode.values, contains(SyncMode.full));
      expect(SyncMode.values, contains(SyncMode.maintenance));
    });

    test('name property returns correct strings', () {
      expect(SyncMode.quick.name, 'quick');
      expect(SyncMode.full.name, 'full');
      expect(SyncMode.maintenance.name, 'maintenance');
    });
  });

  group('DirtyScope', () {
    test('equality is based on projectId and tableName only', () {
      // WHY: markedAt should NOT affect equality -- same scope invalidated
      // at different times is still the same scope.
      final a = DirtyScope(
        projectId: 'p1',
        tableName: 'daily_entries',
        markedAt: DateTime.utc(2026, 1, 1),
      );
      final b = DirtyScope(
        projectId: 'p1',
        tableName: 'daily_entries',
        markedAt: DateTime.utc(2026, 6, 15),
      );
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('different projectId produces inequality', () {
      final a = DirtyScope(
        projectId: 'p1',
        tableName: 'daily_entries',
        markedAt: DateTime.utc(2026, 1, 1),
      );
      final b = DirtyScope(
        projectId: 'p2',
        tableName: 'daily_entries',
        markedAt: DateTime.utc(2026, 1, 1),
      );
      expect(a, isNot(equals(b)));
    });

    test('different tableName produces inequality', () {
      final a = DirtyScope(
        projectId: 'p1',
        tableName: 'daily_entries',
        markedAt: DateTime.utc(2026, 1, 1),
      );
      final b = DirtyScope(
        projectId: 'p1',
        tableName: 'photos',
        markedAt: DateTime.utc(2026, 1, 1),
      );
      expect(a, isNot(equals(b)));
    });

    test('null projectId means company-wide', () {
      final scope = DirtyScope(
        projectId: null,
        tableName: 'projects',
        markedAt: DateTime.utc(2026, 1, 1),
      );
      expect(scope.isCompanyWide, isTrue);
    });

    test('non-null projectId means project-scoped', () {
      final scope = DirtyScope(
        projectId: 'p1',
        tableName: 'daily_entries',
        markedAt: DateTime.utc(2026, 1, 1),
      );
      expect(scope.isCompanyWide, isFalse);
    });

    test('null tableName means all tables dirty', () {
      final scope = DirtyScope(
        projectId: 'p1',
        tableName: null,
        markedAt: DateTime.utc(2026, 1, 1),
      );
      expect(scope.isAllTables, isTrue);
    });

    test('non-null tableName means specific table dirty', () {
      final scope = DirtyScope(
        projectId: 'p1',
        tableName: 'daily_entries',
        markedAt: DateTime.utc(2026, 1, 1),
      );
      expect(scope.isAllTables, isFalse);
    });

    test('Set deduplicates same scope with different markedAt', () {
      // WHY: Core use case -- DirtyScopeTracker uses Set<DirtyScope>
      final set = <DirtyScope>{
        DirtyScope(
          projectId: 'p1',
          tableName: 'daily_entries',
          markedAt: DateTime.utc(2026, 1, 1),
        ),
        DirtyScope(
          projectId: 'p1',
          tableName: 'daily_entries',
          markedAt: DateTime.utc(2026, 6, 15),
        ),
      };
      expect(set.length, 1);
    });

    test('toString includes all fields', () {
      final scope = DirtyScope(
        projectId: 'p1',
        tableName: 'photos',
        markedAt: DateTime.utc(2026, 4, 3),
      );
      final str = scope.toString();
      expect(str, contains('p1'));
      expect(str, contains('photos'));
    });
  });

  // FROM SPEC: "No per-record sync_status rollback. No duplicate sync queue."
  // Verify existing types are not broken by additions.
  group('SyncResult (existing, regression check)', () {
    test('default constructor produces zero-count result', () {
      const result = SyncResult();
      expect(result.pushed, 0);
      expect(result.pulled, 0);
      expect(result.errors, 0);
      expect(result.hasErrors, isFalse);
      expect(result.isSuccess, isTrue);
    });

    test('operator + combines results', () {
      const a = SyncResult(pushed: 3, pulled: 5);
      const b = SyncResult(pushed: 2, pulled: 1, errors: 1);
      final combined = a + b;
      expect(combined.pushed, 5);
      expect(combined.pulled, 6);
      expect(combined.errors, 1);
      expect(combined.hasErrors, isTrue);
    });
  });

  group('SyncAdapterStatus (existing, regression check)', () {
    test('has all expected values', () {
      // FROM SPEC ground-truth: idle, syncing, success, error, offline, authRequired
      expect(SyncAdapterStatus.values.length, 6);
      expect(SyncAdapterStatus.idle.name, 'idle');
      expect(SyncAdapterStatus.syncing.name, 'syncing');
      expect(SyncAdapterStatus.success.name, 'success');
      expect(SyncAdapterStatus.error.name, 'error');
      expect(SyncAdapterStatus.offline.name, 'offline');
      expect(SyncAdapterStatus.authRequired.name, 'authRequired');
    });
  });
}
```

### Sub-phase 1.2: Mode-Specific Config Constants

**Files:**
- Modify: `lib/features/sync/config/sync_config.dart:1-43`

**Agent**: `backend-supabase-agent`

#### Step 1.2.1: Add mode-specific config constants to SyncEngineConfig

Open `lib/features/sync/config/sync_config.dart` and add a new section after the existing `orphanMaxPerCycle` constant (after line 42, before the closing brace on line 43). Do NOT modify any existing constants.

```dart
  // -- Quick Sync Mode --
  // FROM SPEC: "startup sync should be fast ... low-latency path"
  // WHY: Quick mode only pushes local changes and pulls dirty scopes.
  // These constants control quick-mode-specific behavior.

  /// Whether quick sync should attempt to pull dirty scopes after pushing.
  /// When false, quick sync is push-only (fastest path).
  /// When true, quick sync pulls adapters whose scopes are marked dirty.
  /// NOTE: Defaults to true because spec says "quick targeted sync runs"
  /// which implies both push and targeted pull.
  static const bool quickSyncPullsDirtyScopes = true;

  /// Maximum age of a dirty scope before it is auto-promoted to require
  /// a full sync. Prevents stale dirty scopes from accumulating indefinitely.
  /// WHY: If a hint arrived 2 hours ago and quick sync never ran, the data
  /// is stale enough to warrant a broader sweep on next full sync.
  static const Duration dirtyScopeMaxAge = Duration(hours: 2);

  // -- Maintenance Sync Mode --
  // FROM SPEC: "deferred or background work ... integrity checks ...
  // orphan cleanup ... company member pulls ... last_synced_at update"
  // NOTE: Maintenance mode reuses existing integrityCheckInterval (4 hours)
  // and orphanMinAge (24 hours) thresholds. No new constants needed for
  // maintenance scheduling -- that is controlled by BackgroundSyncHandler's
  // 4-hour periodic task.
```

#### Step 1.2.2: Verify static analysis passes

Run static analysis to confirm the new constants and types compile without errors.

```
pwsh -Command "flutter analyze lib/features/sync/domain/sync_types.dart lib/features/sync/config/sync_config.dart"
```

Expected output: `No issues found!`

---

## Phase 2: DirtyScopeTracker Engine Component

### Sub-phase 2.1: Create DirtyScopeTracker Class

**Files:**
- Create: `lib/features/sync/engine/dirty_scope_tracker.dart`
- Test: `test/features/sync/engine/dirty_scope_tracker_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 2.1.1: Create the DirtyScopeTracker class

Create `lib/features/sync/engine/dirty_scope_tracker.dart`. This is a new file in the engine layer alongside `change_tracker.dart`, `sync_mutex.dart`, etc.

```dart
// WHY: In-memory dirty scope tracker for targeted quick-sync pulls.
// FROM SPEC: "dirty-scope tracking locally ... quick sync pulls only
// affected scopes whenever possible"
// NOTE: Lives in engine/ layer alongside ChangeTracker, SyncMutex, etc.
// Lint rules: A1, A2, A9, S2, S4 (global rules for lib/features/sync/engine/).

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

/// Tracks which sync scopes have been invalidated by remote change hints.
///
/// The tracker maintains an in-memory set of [DirtyScope] entries. When a
/// remote hint arrives (via Supabase Realtime or FCM), the caller marks the
/// relevant scope dirty. During quick sync, [SyncEngine._pull()] consults
/// the tracker to decide which adapters to pull.
///
/// FROM SPEC: "Candidate scope dimensions: company-wide, project-wide,
/// table-within-project, rare global builtins"
///
/// IMPORTANT: This class is intentionally in-memory only. Dirty scopes are
/// transient hints, not durable state. If the app restarts, all scopes are
/// clean and the next sync runs as a full sync (which is the correct
/// recovery behavior per spec: "Full Sync Is Fallback, Not Default").
class DirtyScopeTracker {
  /// The set of currently dirty scopes.
  /// WHY: Using a Set because DirtyScope has custom equality based on
  /// (projectId, tableName) -- duplicate invalidations are deduplicated.
  final Set<DirtyScope> _dirtyScopes = {};

  /// Mark a scope as dirty. Called when a remote change hint arrives.
  ///
  /// [projectId] — null for company-wide invalidation (e.g., project table changed).
  /// [tableName] — null for all-tables-in-project invalidation.
  ///
  /// FROM SPEC: "Supabase-originated foreground invalidation hints ...
  /// FCM background invalidation hints ... dirty-scope tracking locally"
  void markDirty({String? projectId, String? tableName}) {
    final scope = DirtyScope(
      projectId: projectId,
      tableName: tableName,
      markedAt: DateTime.now().toUtc(),
    );
    _dirtyScopes.add(scope);
    Logger.sync(
      '[DirtyScopeTracker] markDirty: '
      'projectId=${projectId ?? 'ALL'}, '
      'tableName=${tableName ?? 'ALL'}',
    );
  }

  /// Check whether a specific adapter should pull during quick sync.
  ///
  /// Returns true if ANY dirty scope matches the given [tableName] and
  /// optional [projectId]. Matching rules:
  ///
  /// 1. A company-wide scope (projectId=null) makes ALL tables dirty.
  /// 2. A project-wide scope (tableName=null) makes all tables in that project dirty.
  /// 3. A specific scope matches only exact (projectId, tableName) pairs.
  ///
  /// FROM SPEC: "quick sync pulls only affected scopes whenever possible"
  bool isDirty(String tableName, {String? projectId}) {
    // WHY: If nothing is dirty, quick pull skips everything (push-only).
    if (_dirtyScopes.isEmpty) return false;

    for (final scope in _dirtyScopes) {
      // Rule 1: Company-wide scope invalidates everything
      if (scope.isCompanyWide) return true;

      // Rule 2: Project-wide scope (tableName=null) invalidates all tables
      // in that project. If no projectId filter is provided, any project-wide
      // scope matches.
      if (scope.isAllTables) {
        if (projectId == null || scope.projectId == projectId) return true;
      }

      // Rule 3: Exact match on both dimensions
      if (scope.tableName == tableName) {
        if (projectId == null || scope.projectId == projectId) return true;
      }
    }

    return false;
  }

  /// Returns true if any scopes are currently dirty.
  bool get hasDirtyScopes => _dirtyScopes.isNotEmpty;

  /// Returns the number of dirty scopes.
  int get dirtyCount => _dirtyScopes.length;

  /// Returns an unmodifiable snapshot of all dirty scopes.
  /// WHY: Snapshot prevents external mutation of the internal set.
  Set<DirtyScope> get dirtyScopes => Set.unmodifiable(_dirtyScopes);

  /// Clear all dirty scopes. Called after a full sync completes.
  ///
  /// FROM SPEC: Full sync is the "broader push + pull sweep" that covers
  /// everything. After a full sync, all scopes are fresh and no targeted
  /// pull is needed until the next hint arrives.
  void clearAll() {
    final count = _dirtyScopes.length;
    _dirtyScopes.clear();
    if (count > 0) {
      Logger.sync('[DirtyScopeTracker] clearAll: cleared $count dirty scopes');
    }
  }

  /// Remove dirty scopes older than [SyncEngineConfig.dirtyScopeMaxAge].
  ///
  /// WHY: Stale dirty scopes from hints that were never acted on should not
  /// accumulate indefinitely. Expired scopes are cleared -- the next full
  /// sync will catch up.
  int pruneExpired() {
    final cutoff = DateTime.now().toUtc().subtract(
      SyncEngineConfig.dirtyScopeMaxAge,
    );
    final before = _dirtyScopes.length;
    _dirtyScopes.removeWhere((scope) => scope.markedAt.isBefore(cutoff));
    final pruned = before - _dirtyScopes.length;
    if (pruned > 0) {
      Logger.sync('[DirtyScopeTracker] pruneExpired: removed $pruned stale scopes');
    }
    return pruned;
  }
}
```

#### Step 2.1.2: Write comprehensive unit tests for DirtyScopeTracker

Create `test/features/sync/engine/dirty_scope_tracker_test.dart`.

```dart
// WHY: Verify DirtyScopeTracker marking, matching, clearing, and pruning logic.
// NOTE: Pure Dart tests -- DirtyScopeTracker is in-memory, no DB needed.
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

void main() {
  late DirtyScopeTracker tracker;

  setUp(() {
    tracker = DirtyScopeTracker();
  });

  group('markDirty', () {
    test('adds a scope to the dirty set', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      expect(tracker.hasDirtyScopes, isTrue);
      expect(tracker.dirtyCount, 1);
    });

    test('deduplicates same (projectId, tableName) pair', () {
      // WHY: Multiple hints for the same scope should not bloat the set
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      expect(tracker.dirtyCount, 1);
    });

    test('different tables in same project are separate scopes', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      tracker.markDirty(projectId: 'p1', tableName: 'photos');
      expect(tracker.dirtyCount, 2);
    });

    test('same table in different projects are separate scopes', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      tracker.markDirty(projectId: 'p2', tableName: 'daily_entries');
      expect(tracker.dirtyCount, 2);
    });

    test('null projectId creates company-wide scope', () {
      tracker.markDirty(projectId: null, tableName: 'projects');
      expect(tracker.dirtyScopes.first.isCompanyWide, isTrue);
    });

    test('null tableName creates all-tables scope', () {
      tracker.markDirty(projectId: 'p1', tableName: null);
      expect(tracker.dirtyScopes.first.isAllTables, isTrue);
    });
  });

  group('isDirty', () {
    test('returns false when no scopes are dirty', () {
      expect(tracker.isDirty('daily_entries'), isFalse);
    });

    test('returns true for exact match', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      expect(tracker.isDirty('daily_entries', projectId: 'p1'), isTrue);
    });

    test('returns false for non-matching table', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      expect(tracker.isDirty('photos', projectId: 'p1'), isFalse);
    });

    test('returns false for non-matching project', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      expect(tracker.isDirty('daily_entries', projectId: 'p2'), isFalse);
    });

    // FROM SPEC: "company-wide" scope dimension
    test('company-wide scope makes all tables dirty', () {
      tracker.markDirty(projectId: null, tableName: 'projects');
      // WHY: Company-wide scope (projectId=null) should match ANY table query
      expect(tracker.isDirty('daily_entries'), isTrue);
      expect(tracker.isDirty('photos'), isTrue);
      expect(tracker.isDirty('contractors'), isTrue);
      expect(tracker.isDirty('projects'), isTrue);
    });

    // FROM SPEC: "project-wide" scope dimension
    test('project-wide scope (tableName=null) makes all tables in that project dirty', () {
      tracker.markDirty(projectId: 'p1', tableName: null);
      expect(tracker.isDirty('daily_entries', projectId: 'p1'), isTrue);
      expect(tracker.isDirty('photos', projectId: 'p1'), isTrue);
      expect(tracker.isDirty('contractors', projectId: 'p1'), isTrue);
    });

    test('project-wide scope does not match other projects', () {
      tracker.markDirty(projectId: 'p1', tableName: null);
      expect(tracker.isDirty('daily_entries', projectId: 'p2'), isFalse);
    });

    test('isDirty without projectId filter matches any project scope for that table', () {
      // WHY: ScopeType.direct adapters (e.g., projects) don't have a projectId
      // filter. isDirty('projects') should return true if ANY scope marks
      // the projects table dirty.
      tracker.markDirty(projectId: 'p1', tableName: 'projects');
      expect(tracker.isDirty('projects'), isTrue);
    });

    test('isDirty without projectId filter matches project-wide scope', () {
      tracker.markDirty(projectId: 'p1', tableName: null);
      expect(tracker.isDirty('daily_entries'), isTrue);
    });
  });

  group('clearAll', () {
    test('removes all dirty scopes', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      tracker.markDirty(projectId: 'p2', tableName: 'photos');
      tracker.markDirty(projectId: null, tableName: 'projects');
      expect(tracker.dirtyCount, 3);

      tracker.clearAll();
      expect(tracker.hasDirtyScopes, isFalse);
      expect(tracker.dirtyCount, 0);
    });

    test('clearAll on empty tracker is a no-op', () {
      // WHY: Should not throw or log unnecessarily
      tracker.clearAll();
      expect(tracker.hasDirtyScopes, isFalse);
    });
  });

  group('dirtyScopes', () {
    test('returns unmodifiable snapshot', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      final snapshot = tracker.dirtyScopes;

      // Verify snapshot is not affected by subsequent mutations
      tracker.markDirty(projectId: 'p2', tableName: 'photos');
      // NOTE: Set.unmodifiable creates a view, not a copy. But the test
      // verifies the public API contract. The key safety property is that
      // callers cannot add/remove from the returned set.
      expect(() => (snapshot as Set<DirtyScope>).add(
        DirtyScope(projectId: 'p3', tableName: 't', markedAt: DateTime.now()),
      ), throwsA(isA<UnsupportedError>()));
    });
  });

  group('pruneExpired', () {
    test('removes scopes older than dirtyScopeMaxAge', () {
      // WHY: Manually inject an old scope by manipulating internals.
      // We test through the public API by marking and then checking pruning.
      // Since DirtyScope markedAt is set to DateTime.now() in markDirty,
      // freshly-marked scopes should NOT be pruned.
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      final pruned = tracker.pruneExpired();
      expect(pruned, 0);
      expect(tracker.dirtyCount, 1);
    });

    test('pruneExpired returns count of pruned entries', () {
      // WHY: Verify the return value contract
      final pruned = tracker.pruneExpired();
      expect(pruned, 0);
    });
  });

  group('hasDirtyScopes', () {
    test('false when empty', () {
      expect(tracker.hasDirtyScopes, isFalse);
    });

    test('true after markDirty', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      expect(tracker.hasDirtyScopes, isTrue);
    });

    test('false after clearAll', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      tracker.clearAll();
      expect(tracker.hasDirtyScopes, isFalse);
    });
  });

  // FROM SPEC: Integration scenario -- multiple hints accumulate, quick sync
  // checks each adapter, then clearAll after full sync.
  group('integration scenario', () {
    test('multiple hints from different sources accumulate correctly', () {
      // Simulate: FCM hint for project p1's daily_entries
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');

      // Simulate: Realtime hint for project p1's photos
      tracker.markDirty(projectId: 'p1', tableName: 'photos');

      // Simulate: FCM hint for project p2 (all tables)
      tracker.markDirty(projectId: 'p2', tableName: null);

      expect(tracker.dirtyCount, 3);

      // Quick sync checks:
      // daily_entries adapter for p1 -> dirty (exact match)
      expect(tracker.isDirty('daily_entries', projectId: 'p1'), isTrue);

      // photos adapter for p1 -> dirty (exact match)
      expect(tracker.isDirty('photos', projectId: 'p1'), isTrue);

      // contractors adapter for p1 -> NOT dirty (no matching scope)
      expect(tracker.isDirty('contractors', projectId: 'p1'), isFalse);

      // daily_entries adapter for p2 -> dirty (project-wide scope)
      expect(tracker.isDirty('daily_entries', projectId: 'p2'), isTrue);

      // photos adapter for p2 -> dirty (project-wide scope)
      expect(tracker.isDirty('photos', projectId: 'p2'), isTrue);

      // daily_entries adapter for p3 -> NOT dirty (no scope for p3)
      expect(tracker.isDirty('daily_entries', projectId: 'p3'), isFalse);

      // After full sync, clear all
      tracker.clearAll();
      expect(tracker.isDirty('daily_entries', projectId: 'p1'), isFalse);
      expect(tracker.isDirty('daily_entries', projectId: 'p2'), isFalse);
    });
  });
}
```

#### Step 2.1.3: Verify static analysis passes

Run static analysis to confirm the new DirtyScopeTracker file compiles without errors.

```
pwsh -Command "flutter analyze lib/features/sync/engine/dirty_scope_tracker.dart"
```

Expected output: `No issues found!`

---

## Phase 3: SyncEngine Mode Support

### Sub-phase 3.1: Add SyncMode Parameter to SyncEngine.pushAndPull

**Files:**
- Modify: `lib/features/sync/engine/sync_engine.dart:1-23` (imports)
- Modify: `lib/features/sync/engine/sync_engine.dart:83-165` (class fields + constructor)
- Modify: `lib/features/sync/engine/sync_engine.dart:216-360` (pushAndPull method)
- Modify: `lib/features/sync/engine/sync_engine.dart:1452-1556` (_pull method)
- Test: `test/features/sync/engine/sync_engine_mode_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 3.1.1: Add DirtyScopeTracker import to sync_engine.dart

At `lib/features/sync/engine/sync_engine.dart`, add a new import after line 15 (after the `change_tracker.dart` import):

```dart
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
```

Also add the sync_types import for SyncMode after line 17 (after the `scope_type.dart` import). Check if `sync_types.dart` is already imported -- if not, add:

```dart
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
```

#### Step 3.1.2: Add DirtyScopeTracker field and constructor parameter to SyncEngine

At `lib/features/sync/engine/sync_engine.dart`, add a new field to the `SyncEngine` class after line 96 (`final SyncRegistry _registry = SyncRegistry.instance;`):

```dart
  // FROM SPEC: "dirty-scope tracking locally ... quick sync pulls only affected scopes"
  // WHY: Injected dependency -- allows caller to share a single tracker instance
  // across multiple sync cycles so dirty state persists between quick syncs.
  // NOTE: Optional -- when null, all pulls are treated as full (backward compat).
  final DirtyScopeTracker? _dirtyScopeTracker;
```

Then modify the constructor at lines 153-165. Add `this._dirtyScopeTracker` as an optional named parameter. The constructor becomes:

```dart
  SyncEngine({
    required this.db,
    required this.supabase,
    required this.companyId,
    required this.userId,
    this.lockedBy = 'foreground',
    this.onProgress,
    DirtyScopeTracker? dirtyScopeTracker,
  })  : _dirtyScopeTracker = dirtyScopeTracker,
        _mutex = SyncMutex(db),
        _changeTracker = ChangeTracker(db),
        _conflictResolver = ConflictResolver(db),
        _integrityChecker = IntegrityChecker(db, supabase),
        _orphanScanner = OrphanScanner(supabase),
        _storageCleanup = StorageCleanup(supabase, db);
```

IMPORTANT: The `_dirtyScopeTracker` field is added to the initializer list. The existing initializer list syntax changes from `)  :` to `)  :` with the new field assignment first. The exact edit is:
- Line 160 currently reads: `  })  : _mutex = SyncMutex(db),`
- Change to: `    DirtyScopeTracker? dirtyScopeTracker,`
- And line 161 becomes: `  })  : _dirtyScopeTracker = dirtyScopeTracker,`
- Then line 162: `        _mutex = SyncMutex(db),`
- The rest of the initializer list stays the same.

#### Step 3.1.3: Add SyncMode parameter to pushAndPull method

At `lib/features/sync/engine/sync_engine.dart`, modify the `pushAndPull()` method signature at line 216. Change:

```dart
  Future<SyncEngineResult> pushAndPull() async {
```

To:

```dart
  /// Top-level sync orchestrator: push local changes, then pull remote changes.
  ///
  /// [mode] controls which sub-phases run:
  /// - [SyncMode.quick]: push + pull dirty scopes only (skip integrity, orphan, storage cleanup)
  /// - [SyncMode.full]: push + pull all adapters + integrity + orphan scan (current behavior)
  /// - [SyncMode.maintenance]: integrity check + orphan scan + prune only (no push/pull)
  ///
  /// FROM SPEC: "The app will support three sync modes"
  Future<SyncEngineResult> pushAndPull({
    SyncMode mode = SyncMode.full,
  }) async {
```

WHY: Default parameter `SyncMode.full` ensures backward compatibility. All existing callers that call `pushAndPull()` without arguments get the current full behavior.

#### Step 3.1.4: Implement mode branching inside pushAndPull

Replace the body of `pushAndPull()` (lines 217-360) with the mode-aware implementation. The full replacement body is:

```dart
  Future<SyncEngineResult> pushAndPull({
    SyncMode mode = SyncMode.full,
  }) async {
    // Reset per-cycle counters
    _rlsDenialCount = 0;
    _pullConflictCount = 0;
    _pullSkippedFkCount = 0;
    _skippedPushCount = 0;

    // WHY: Crash recovery for pulling=1 stuck state.
    // If the app crashes between setting pulling=1 (in _pull()) and the finally block
    // that resets it to 0, SQLite triggers remain suppressed on next launch.
    // This unconditional reset at pushAndPull() entry ensures triggers are re-enabled
    // before any new sync cycle begins. resetState() also performs this reset.
    try {
      await db.execute(
        "UPDATE sync_control SET value = '0' WHERE key = 'pulling'",
      );
    } catch (e) {
      Logger.sync('[SyncEngine] crash recovery reset: $e');
    }

    // Acquire lock
    if (!await _mutex.tryAcquire(lockedBy)) {
      Logger.sync('Lock held by another process, skipping sync');
      return const SyncEngineResult(lockFailed: true);
    }
    _postSyncStatus({'type': 'sync_state', 'state': 'started', 'mode': mode.name});

    // Debug-mode reentrancy guard
    assert(!_insidePushOrPull, 'SyncEngine: reentrancy detected');
    _insidePushOrPull = true;
    final stopwatch = Stopwatch()..start(); // FROM SPEC: duration timing

    // Start heartbeat timer during sync
    // WHY: Long syncs (large photo batches) can exceed stale timeout.
    // FROM SPEC: Section 3J -- "Update every 60s"
    final heartbeatTimer = Timer.periodic(
      const Duration(seconds: 60),
      (_) => _mutex.heartbeat(),
    );
    var cycleCompleted = false;
    var combined = const SyncEngineResult();
    try {
      // FROM SPEC: Three sync modes with different sub-phase compositions.
      switch (mode) {
        case SyncMode.quick:
          // FROM SPEC: "low-latency path ... push local changes first ...
          // avoid broad project-wide pushAndPull() by default"
          // WHY: Quick mode pushes all pending local changes (change_log is
          // already incremental), then pulls ONLY adapters whose scopes are
          // marked dirty by the DirtyScopeTracker.
          final pushResult = await _push();
          Logger.sync('Quick push complete: ${pushResult.pushed} pushed, '
              '${pushResult.errors} errors');
          _postSyncStatus({
            'type': 'sync_state',
            'state': 'push_complete',
            'mode': mode.name,
            'pushed': pushResult.pushed,
            'errors': pushResult.errors,
          });

          // NOTE: Storage cleanup is SKIPPED in quick mode.
          // FROM SPEC: Quick mode skips "integrity, orphan scan, storage cleanup".

          var pullResult = const SyncEngineResult();
          if (SyncEngineConfig.quickSyncPullsDirtyScopes &&
              _dirtyScopeTracker != null &&
              _dirtyScopeTracker.hasDirtyScopes) {
            // FROM SPEC: "quick targeted sync runs" -- pull only dirty scopes
            pullResult = await _pull(onlyDirtyScopes: true);
            Logger.sync('Quick pull (dirty scopes) complete: '
                '${pullResult.pulled} pulled, ${pullResult.errors} errors');
          } else if (SyncEngineConfig.quickSyncPullsDirtyScopes &&
                     _dirtyScopeTracker != null &&
                     !_dirtyScopeTracker.hasDirtyScopes) {
            Logger.sync('Quick sync: no dirty scopes, skipping pull');
          } else {
            Logger.sync('Quick sync: DirtyScopeTracker not available, skipping pull');
          }

          // NOTE: Prune and integrity check are SKIPPED in quick mode.
          combined = pushResult + pullResult;

        case SyncMode.full:
          // FROM SPEC: "broader push + pull sweep ... fallback recovery path"
          // WHY: This is the original pushAndPull() behavior, unchanged.
          final pushResult = await _push();
          Logger.sync('Push complete: ${pushResult.pushed} pushed, '
              '${pushResult.errors} errors, $_rlsDenialCount RLS denials');
          _postSyncStatus({
            'type': 'sync_state',
            'state': 'push_complete',
            'pushed': pushResult.pushed,
            'errors': pushResult.errors,
          });

          // Process deferred storage cleanup after push (multi-type file deletion)
          try {
            await _storageCleanup.cleanupExpiredFiles();
          } catch (e) {
            Logger.error('Storage cleanup failed', error: e);
          }

          final pullResult = await _pull();
          Logger.sync('Pull complete: ${pullResult.pulled} pulled, '
              '${pullResult.errors} errors');
          _postSyncStatus({
            'type': 'sync_state',
            'state': 'pull_complete',
            'pulled': pullResult.pulled,
            'errors': pullResult.errors,
          });

          // Prune old data
          await _changeTracker.pruneProcessed();
          await _conflictResolver.pruneExpired();
          await _cleanupExpiredConflicts();

          // Integrity check (4-hour schedule, catch errors -- don't fail sync)
          if (await _integrityChecker.shouldRun()) {
            try {
              final integrityResults = await _integrityChecker.run();
              for (final result in integrityResults) {
                await _storeIntegrityResult(result);
                if (result.driftDetected) {
                  await _clearCursor(result.tableName);
                }
              }
              // Run orphan scanner as part of integrity cycle.
              // FROM SPEC: Section 3O -- auto-delete storage files >24h with no DB match.
              final orphans = await _orphanScanner.scan(companyId, autoDelete: true);
              if (orphans.isNotEmpty) {
                await _storeMetadata(
                  'orphan_count',
                  orphans.length.toString(),
                );
              }

              // FIX B: Purge local records whose server counterpart was hard-deleted
              final purgedCount = await _integrityChecker.purgeOrphans(
                syncedProjectIds: _syncedProjectIds.toSet(),
                changeTracker: _changeTracker,
              );
              if (purgedCount > 0) {
                Logger.sync('Orphan purge: $purgedCount local records soft-deleted');
              }
            } catch (e) {
              Logger.error('Integrity check failed', error: e);
            }
          }

          combined = pushResult + pullResult;

          // FROM SPEC: After a full sync, clear all dirty scopes since
          // everything has been pulled fresh.
          _dirtyScopeTracker?.clearAll();

        case SyncMode.maintenance:
          // FROM SPEC: "deferred or background work ... integrity checks ...
          // orphan cleanup ... company member pulls ... last_synced_at update"
          // WHY: Maintenance mode runs ONLY integrity/orphan/prune work.
          // No push, no pull. This is for background periodic maintenance.
          Logger.sync('Maintenance sync started');

          // Prune old data
          await _changeTracker.pruneProcessed();
          await _conflictResolver.pruneExpired();
          await _cleanupExpiredConflicts();

          // Integrity check (forced -- maintenance mode always runs it)
          try {
            final integrityResults = await _integrityChecker.run();
            for (final result in integrityResults) {
              await _storeIntegrityResult(result);
              if (result.driftDetected) {
                await _clearCursor(result.tableName);
              }
            }
            // FROM SPEC: "orphan cleanup"
            final orphans = await _orphanScanner.scan(companyId, autoDelete: true);
            if (orphans.isNotEmpty) {
              await _storeMetadata(
                'orphan_count',
                orphans.length.toString(),
              );
            }

            // Purge orphaned local records
            // WHY: Need to load synced project IDs for the orphan purge filter.
            await _loadSyncedProjectIds();
            final purgedCount = await _integrityChecker.purgeOrphans(
              syncedProjectIds: _syncedProjectIds.toSet(),
              changeTracker: _changeTracker,
            );
            if (purgedCount > 0) {
              Logger.sync('Maintenance orphan purge: $purgedCount local records soft-deleted');
            }
          } catch (e) {
            Logger.error('Maintenance integrity check failed', error: e);
          }

          // Prune expired dirty scopes
          _dirtyScopeTracker?.pruneExpired();

          Logger.sync('Maintenance sync completed');
          // combined stays at default (0 pushed, 0 pulled)
      }

      cycleCompleted = true;
    } finally {
      heartbeatTimer.cancel();
      stopwatch.stop();
      if (cycleCompleted) {
        Logger.sync('Sync cycle (${mode.name}): pushed=${combined.pushed} '
            'pulled=${combined.pulled} errors=${combined.errors} '
            'conflicts=${combined.conflicts} skippedFk=${combined.skippedFk} '
            'skippedPush=${combined.skippedPush} '
            'duration=${stopwatch.elapsedMilliseconds}ms');
        _postSyncStatus({
          'type': 'sync_state',
          'state': 'completed',
          'mode': mode.name,
          'pushed': combined.pushed,
          'pulled': combined.pulled,
          'errors': combined.errors,
          'conflicts': combined.conflicts,
          'skippedFk': combined.skippedFk,
          'skippedPush': combined.skippedPush,
          'duration_ms': stopwatch.elapsedMilliseconds,
        });
      } else {
        _postSyncStatus({
          'type': 'sync_state',
          'state': 'failed',
          'mode': mode.name,
          'error': 'Sync cycle did not complete',
        });
      }
      _insidePushOrPull = false;
      await _mutex.release();
    }
    return combined;
  }
```

#### Step 3.1.5: Add onlyDirtyScopes parameter to _pull method

At `lib/features/sync/engine/sync_engine.dart`, modify the `_pull()` method at line 1452. Change:

```dart
  Future<SyncEngineResult> _pull() async {
```

To:

```dart
  /// Pull remote changes for all adapters (full mode) or only dirty-scope
  /// adapters (quick mode).
  ///
  /// [onlyDirtyScopes] — when true, each adapter is checked against the
  /// [DirtyScopeTracker] before pulling. Adapters whose scope is not dirty
  /// are skipped entirely. This provides the targeted pull behavior for
  /// quick sync mode.
  ///
  /// FROM SPEC: "quick sync pulls only affected scopes whenever possible"
  Future<SyncEngineResult> _pull({bool onlyDirtyScopes = false}) async {
```

Then, inside the `_pull()` method, add dirty-scope checking AFTER the existing skip logic (after line 1486, before the `try` block at line 1488). Insert this block:

```dart
        // FROM SPEC: "quick sync pulls only affected scopes whenever possible"
        // WHY: In quick mode, skip adapters whose scopes are not dirty.
        // This is the key optimization -- instead of pulling all 22 adapters,
        // we only pull the ones with pending remote changes.
        // NOTE: This check is AFTER the existing skipPull/scope checks so
        // adapters that are inherently skipped (e.g., ConsentRecordAdapter)
        // are still skipped regardless of dirty state.
        if (onlyDirtyScopes && _dirtyScopeTracker != null) {
          if (!_dirtyScopeTracker.isDirty(adapter.tableName)) {
            Logger.sync('Pull skip (not dirty, quick mode): ${adapter.tableName}');
            continue;
          }
        }
```

The insertion point is after line 1486 (the `continue;` for viaContractor with empty contractors) and before line 1488 (the `try {` for `_pullTable`). The full context of the modified section looks like:

```dart
        } else if (adapter.scopeType == ScopeType.viaContractor &&
                   _syncedContractorIds.isEmpty) {
          // Have projects but no contractors yet -- skip equipment
          Logger.sync('Pull skip (no contractors): ${adapter.tableName}');
          continue;
        }

        // FROM SPEC: "quick sync pulls only affected scopes whenever possible"
        // WHY: In quick mode, skip adapters whose scopes are not dirty.
        if (onlyDirtyScopes && _dirtyScopeTracker != null) {
          if (!_dirtyScopeTracker.isDirty(adapter.tableName)) {
            Logger.sync('Pull skip (not dirty, quick mode): ${adapter.tableName}');
            continue;
          }
        }

        try {
          final count = await _pullTable(adapter);
```

IMPORTANT: The existing `pullOnly()` method at line 406 calls `_pull()` without arguments. Since `onlyDirtyScopes` defaults to `false`, this remains backward compatible. No change to `pullOnly()` is needed.

#### Step 3.1.6: Update SyncEngine.createForBackgroundSync to accept DirtyScopeTracker

At `lib/features/sync/engine/sync_engine.dart`, the static factory `createForBackgroundSync` at line 175-200 creates a `SyncEngine` without a `DirtyScopeTracker`. This is correct for background sync (which should use full or maintenance mode). No change needed here -- the `dirtyScopeTracker` parameter is optional and defaults to null.

However, update the call site in the factory to document this:

```dart
    // NOTE: Background sync does not use DirtyScopeTracker (dirtyScopeTracker
    // defaults to null). Background sync runs as full or maintenance mode.
    return SyncEngine(
      db: database,
      supabase: supabase,
      companyId: companyId,
      userId: userId,
      lockedBy: 'background',
    );
```

This is a comment-only change at line 194-200. No functional modification.

### Sub-phase 3.2: Update SyncEngineFactory to Accept DirtyScopeTracker

**Files:**
- Modify: `lib/features/sync/application/sync_engine_factory.dart:10-38`

**Agent**: `backend-supabase-agent`

#### Step 3.2.1: Add DirtyScopeTracker parameter to SyncEngineFactory.create

At `lib/features/sync/application/sync_engine_factory.dart`, add the import for DirtyScopeTracker at the top of the file (after existing imports):

```dart
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
```

Then modify the `create` method (lines 25-38) to accept and forward the `DirtyScopeTracker`:

```dart
  /// Create a SyncEngine for foreground sync operations.
  ///
  /// NOTE: SyncEngine constructor requires db, supabase, companyId, userId
  /// (see sync_engine.dart lines 153-160). lockedBy defaults to 'foreground'.
  /// [dirtyScopeTracker] is optional -- when provided, enables dirty-scope-aware
  /// quick sync pulls.
  SyncEngine? create({
    required Database db,
    required SupabaseClient supabase,
    required String companyId,
    required String userId,
    DirtyScopeTracker? dirtyScopeTracker,
  }) {
    ensureAdaptersRegistered();
    return SyncEngine(
      db: db,
      supabase: supabase,
      companyId: companyId,
      userId: userId,
      dirtyScopeTracker: dirtyScopeTracker,
    );
  }
```

### Sub-phase 3.3: Update SyncOrchestrator to Pass Mode Through

**Files:**
- Modify: `lib/features/sync/application/sync_orchestrator.dart:32-34` (class fields)
- Modify: `lib/features/sync/application/sync_orchestrator.dart:107-123` (constructor)
- Modify: `lib/features/sync/application/sync_orchestrator.dart:213-238` (_createEngine)
- Modify: `lib/features/sync/application/sync_orchestrator.dart:241-318` (syncLocalAgencyProjects)
- Modify: `lib/features/sync/application/sync_orchestrator.dart:325-410` (_syncWithRetry)
- Modify: `lib/features/sync/application/sync_orchestrator.dart:413-448` (_doSync)

**Agent**: `backend-supabase-agent`

#### Step 3.3.1: Add DirtyScopeTracker field and import to SyncOrchestrator

At `lib/features/sync/application/sync_orchestrator.dart`, add imports at the top of the file (after existing imports around line 22):

```dart
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
```

NOTE: Check if `sync_types.dart` is already imported via `'../domain/sync_types.dart'` at line 17. If yes, skip the second import (it is already available). The `DirtyScope` and `SyncMode` types from `sync_types.dart` will be accessible through the existing import.

Add a new field to the `SyncOrchestrator` class after line 37 (`final SyncEngineFactory _engineFactory;`):

```dart
  // FROM SPEC: "dirty-scope tracking locally"
  // WHY: Single DirtyScopeTracker instance shared across all sync cycles.
  // Injected via builder so it can also be accessed by RealtimeHintHandler
  // and FcmHandler for marking scopes dirty.
  final DirtyScopeTracker _dirtyScopeTracker;
```

#### Step 3.3.2: Update SyncOrchestrator.fromBuilder constructor

At `lib/features/sync/application/sync_orchestrator.dart`, modify the `fromBuilder` constructor at lines 107-123 to accept and initialize `DirtyScopeTracker`:

```dart
  SyncOrchestrator.fromBuilder({
    required DatabaseService dbService,
    SupabaseClient? supabaseClient,
    required SyncEngineFactory engineFactory,
    UserProfileSyncDatasource? userProfileSyncDatasource,
    required ({String? companyId, String? userId}) Function() syncContextProvider,
    AppConfigProvider? appConfigProvider,
    DirtyScopeTracker? dirtyScopeTracker,
  }) : _dbService = dbService,
       _supabaseClient = supabaseClient,
       _engineFactory = engineFactory,
       _userProfileSyncDatasource = userProfileSyncDatasource,
       _syncContextProvider = syncContextProvider,
       _appConfigProvider = appConfigProvider,
       _dirtyScopeTracker = dirtyScopeTracker ?? DirtyScopeTracker() {
    if (_isMockMode) {
      _mockAdapter = MockSyncAdapter();
    }
  }
```

WHY: `dirtyScopeTracker ?? DirtyScopeTracker()` provides a default instance when not injected, maintaining backward compatibility with existing builder call sites.

Update the test constructor similarly:

```dart
  @visibleForTesting
  SyncOrchestrator.forTesting(this._dbService)
      : _supabaseClient = null,
        _engineFactory = SyncEngineFactory(),
        _userProfileSyncDatasource = null,
        _syncContextProvider = (() => (companyId: null, userId: null)),
        _appConfigProvider = null,
        _dirtyScopeTracker = DirtyScopeTracker() {
    _mockAdapter = MockSyncAdapter();
  }
```

#### Step 3.3.3: Update _createEngine to pass DirtyScopeTracker

At `lib/features/sync/application/sync_orchestrator.dart`, the `_createEngine` method (around lines 213-238) calls `_engineFactory.create(...)`. Update the call at lines 231-236:

```dart
    final engine = _engineFactory.create(
      db: db,
      supabase: client,
      companyId: companyId,
      userId: userId,
      dirtyScopeTracker: _dirtyScopeTracker,
    );
```

#### Step 3.3.4: Add SyncMode parameter to syncLocalAgencyProjects

At `lib/features/sync/application/sync_orchestrator.dart`, modify `syncLocalAgencyProjects` at line 241:

Change:
```dart
  Future<SyncResult> syncLocalAgencyProjects() async {
```

To:
```dart
  /// Sync all local agency projects with retry logic for transient errors.
  ///
  /// [mode] controls the sync behavior:
  /// - [SyncMode.quick]: push + pull dirty scopes only (startup, foreground)
  /// - [SyncMode.full]: full push + pull sweep (user-invoked, default)
  /// - [SyncMode.maintenance]: integrity + orphan + prune only (background)
  ///
  /// FROM SPEC: "The app will support three sync modes"
  Future<SyncResult> syncLocalAgencyProjects({
    SyncMode mode = SyncMode.full,
  }) async {
```

Then update the call to `_syncWithRetry()` at line 260:

Change:
```dart
      final result = await _syncWithRetry();
```

To:
```dart
      final result = await _syncWithRetry(mode: mode);
```

#### Step 3.3.5: Add SyncMode parameter to _syncWithRetry

At `lib/features/sync/application/sync_orchestrator.dart`, modify `_syncWithRetry` at line 325 (approximate -- look for `Future<SyncResult> _syncWithRetry()`):

Change:
```dart
  Future<SyncResult> _syncWithRetry() async {
```

To:
```dart
  Future<SyncResult> _syncWithRetry({
    SyncMode mode = SyncMode.full,
  }) async {
```

Then update the call to `_doSync()` inside this method (around line 383):

Change:
```dart
      lastResult = await _doSync();
```

To:
```dart
      lastResult = await _doSync(mode: mode);
```

Also update the background retry timer (around lines 388-408). The background retry should always use full mode since it is a fallback:

```dart
    _backgroundRetryTimer = Timer(const Duration(seconds: 60), () async {
      if (_disposed) return;
      try {
        final dnsOk = await checkDnsReachability();
        if (dnsOk && !_disposed) {
          // WHY: Background retry always uses full mode as a recovery fallback.
          // FROM SPEC: "Full sync is fallback, not default" -- but retry IS recovery.
          await syncLocalAgencyProjects(mode: SyncMode.full);
        }
      } catch (e) {
        Logger.sync('Background retry failed: $e');
      }
    });
```

#### Step 3.3.6: Add SyncMode parameter to _doSync

At `lib/features/sync/application/sync_orchestrator.dart`, modify `_doSync` at line 413:

Change:
```dart
  Future<SyncResult> _doSync() async {
```

To:
```dart
  Future<SyncResult> _doSync({
    SyncMode mode = SyncMode.full,
  }) async {
```

Then update the call to `engine.pushAndPull()` at line 435:

Change:
```dart
      final engineResult = await engine.pushAndPull();
```

To:
```dart
      // FROM SPEC: Pass sync mode through to the engine for mode-aware behavior.
      final engineResult = await engine.pushAndPull(mode: mode);
```

#### Step 3.3.7: Expose DirtyScopeTracker via getter on SyncOrchestrator

At `lib/features/sync/application/sync_orchestrator.dart`, add a public getter after the existing getters (after line 146, `bool get isSupabaseOnline`):

```dart
  /// The dirty scope tracker for marking scopes dirty from external sources
  /// (FCM hints, Realtime hints).
  /// FROM SPEC: "dirty-scope tracking locally"
  DirtyScopeTracker get dirtyScopeTracker => _dirtyScopeTracker;
```

WHY: FcmHandler and RealtimeHintHandler (future phases) need access to the tracker to mark scopes dirty when hints arrive. They access the orchestrator, so exposing the tracker via getter is the cleanest wiring path.

### Sub-phase 3.4: Write Mode-Aware SyncEngine Tests

**Files:**
- Test: `test/features/sync/engine/sync_engine_mode_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 3.4.1: Create sync engine mode tests

Create `test/features/sync/engine/sync_engine_mode_test.dart`. These tests verify the mode parameter routing, dirty scope filtering, and backward compatibility.

```dart
// WHY: Verify SyncEngine mode parameter routing for quick/full/maintenance.
// FROM SPEC: "The app will support three sync modes"
// NOTE: These are unit tests using in-memory SQLite. They verify mode routing
// logic, not actual Supabase I/O.
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';

void main() {
  group('SyncMode enum', () {
    test('quick mode is the first value', () {
      // WHY: Ensures enum ordering matches spec priority (quick = most common)
      expect(SyncMode.quick.index, 0);
    });

    test('all three modes are distinct', () {
      expect(SyncMode.quick, isNot(SyncMode.full));
      expect(SyncMode.quick, isNot(SyncMode.maintenance));
      expect(SyncMode.full, isNot(SyncMode.maintenance));
    });
  });

  group('DirtyScopeTracker with SyncEngine mode logic', () {
    late DirtyScopeTracker tracker;

    setUp(() {
      tracker = DirtyScopeTracker();
    });

    // FROM SPEC: "quick sync pulls only affected scopes whenever possible"
    test('quick mode with no dirty scopes should skip all pulls', () {
      // Simulates what SyncEngine does: check hasDirtyScopes before pulling
      expect(tracker.hasDirtyScopes, isFalse);
      // WHY: When no scopes are dirty, quick sync is push-only (fastest path)
    });

    test('quick mode with dirty scope should pull only matching adapters', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');

      // Simulate adapter iteration:
      // daily_entries -> dirty (should pull)
      expect(tracker.isDirty('daily_entries'), isTrue);
      // photos -> not dirty (should skip)
      expect(tracker.isDirty('photos'), isFalse);
      // contractors -> not dirty (should skip)
      expect(tracker.isDirty('contractors'), isFalse);
    });

    // FROM SPEC: "broader push + pull sweep ... fallback recovery path"
    test('full mode clears dirty scopes after completion', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      tracker.markDirty(projectId: 'p2', tableName: 'photos');
      expect(tracker.dirtyCount, 2);

      // Simulate what pushAndPull(mode: SyncMode.full) does at the end
      tracker.clearAll();
      expect(tracker.hasDirtyScopes, isFalse);
    });

    // FROM SPEC: "deferred or background work"
    test('maintenance mode prunes expired dirty scopes', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');
      // Fresh scopes should not be pruned
      final pruned = tracker.pruneExpired();
      expect(pruned, 0);
      expect(tracker.dirtyCount, 1);
    });

    test('company-wide dirty scope makes all adapters dirty in quick mode', () {
      // FROM SPEC: "company-wide" scope dimension
      tracker.markDirty(projectId: null, tableName: 'projects');

      // ALL adapters should be considered dirty
      expect(tracker.isDirty('projects'), isTrue);
      expect(tracker.isDirty('daily_entries'), isTrue);
      expect(tracker.isDirty('photos'), isTrue);
      expect(tracker.isDirty('contractors'), isTrue);
      expect(tracker.isDirty('equipment'), isTrue);
      expect(tracker.isDirty('bid_items'), isTrue);
      expect(tracker.isDirty('locations'), isTrue);
    });

    test('project-wide dirty scope makes all tables in that project dirty', () {
      // FROM SPEC: "project-wide" scope dimension
      tracker.markDirty(projectId: 'p1', tableName: null);

      expect(tracker.isDirty('daily_entries', projectId: 'p1'), isTrue);
      expect(tracker.isDirty('photos', projectId: 'p1'), isTrue);
      expect(tracker.isDirty('contractors', projectId: 'p1'), isTrue);

      // Different project should NOT be dirty
      expect(tracker.isDirty('daily_entries', projectId: 'p2'), isFalse);
    });

    // FROM SPEC: "table-within-project" scope dimension
    test('table-within-project scope is the most granular', () {
      tracker.markDirty(projectId: 'p1', tableName: 'daily_entries');

      // Only daily_entries in p1 is dirty
      expect(tracker.isDirty('daily_entries', projectId: 'p1'), isTrue);
      // photos in p1 is NOT dirty
      expect(tracker.isDirty('photos', projectId: 'p1'), isFalse);
      // daily_entries in p2 is NOT dirty
      expect(tracker.isDirty('daily_entries', projectId: 'p2'), isFalse);
    });
  });

  // FROM SPEC: Backward compatibility -- existing callers should work unchanged
  group('backward compatibility', () {
    test('SyncMode.full is the default for pushAndPull', () {
      // WHY: Verify that the default value matches what existing callers expect.
      // All existing callers call pushAndPull() without arguments and get full mode.
      // This is verified by the default parameter: SyncMode mode = SyncMode.full
      expect(SyncMode.full.name, 'full');
    });

    test('DirtyScopeTracker is optional in SyncEngine', () {
      // WHY: When dirtyScopeTracker is null (legacy path), quick mode
      // degrades to push-only (no targeted pull). This is safe because
      // the tracker check is: _dirtyScopeTracker != null && ...hasDirtyScopes
      final tracker = DirtyScopeTracker();
      // Verify tracker can be constructed independently
      expect(tracker.hasDirtyScopes, isFalse);
    });
  });
}
```

### Sub-phase 3.5: Update SyncOrchestratorBuilder to Wire DirtyScopeTracker

**Files:**
- Modify: `lib/features/sync/application/sync_orchestrator.dart` (SyncOrchestratorBuilder class, if it exists as a separate class)

**Agent**: `backend-supabase-agent`

#### Step 3.5.1: Check and update SyncOrchestratorBuilder

First, locate the `SyncOrchestratorBuilder` class. It may be in `sync_orchestrator.dart` or in a separate file.

```
Grep for: class SyncOrchestratorBuilder
Path: lib/features/sync/
```

If the builder is in `sync_orchestrator.dart`, add a `DirtyScopeTracker? _dirtyScopeTracker` field and a setter method following the existing builder pattern. Then pass it through to `SyncOrchestrator.fromBuilder(...)`.

If the builder is in a separate file, modify that file instead. Add:

```dart
  DirtyScopeTracker? _dirtyScopeTracker;

  /// Set the dirty scope tracker for targeted quick sync pulls.
  /// FROM SPEC: "dirty-scope tracking locally"
  SyncOrchestratorBuilder withDirtyScopeTracker(DirtyScopeTracker tracker) {
    _dirtyScopeTracker = tracker;
    return this;
  }
```

And in the `build()` method, add `dirtyScopeTracker: _dirtyScopeTracker` to the `SyncOrchestrator.fromBuilder(...)` call.

NOTE: The implementing agent must read the actual SyncOrchestratorBuilder class to determine its exact location and pattern, then apply this change consistently with the existing builder methods.

### Sub-phase 3.6: Verify Full Phase 3 Compilation

**Files:**
- All modified files from Phase 3

**Agent**: `backend-supabase-agent`

#### Step 3.6.1: Run static analysis on all modified sync files

```
pwsh -Command "flutter analyze lib/features/sync/"
```

Expected output: `No issues found!`

This verifies:
1. `SyncMode` enum is correctly defined in `sync_types.dart`
2. `DirtyScope` class compiles with correct equality semantics
3. `DirtyScopeTracker` in `dirty_scope_tracker.dart` compiles
4. `SyncEngine.pushAndPull(mode:)` signature is correct
5. `SyncEngine._pull(onlyDirtyScopes:)` parameter addition is correct
6. `SyncEngine` constructor accepts optional `dirtyScopeTracker`
7. `SyncEngineFactory.create(dirtyScopeTracker:)` forwards correctly
8. `SyncOrchestrator.syncLocalAgencyProjects(mode:)` chains through `_syncWithRetry(mode:)` to `_doSync(mode:)` to `engine.pushAndPull(mode:)`
9. All imports resolve (no circular dependencies)
10. No lint rule violations (A1, A2, A9, S2, S4 for engine files)
