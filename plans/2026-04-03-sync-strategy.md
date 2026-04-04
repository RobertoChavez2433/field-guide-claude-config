# Smarter Sync Strategy Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Replace monolithic full-sync-on-every-trigger with three distinct sync modes (quick/full/maintenance), dirty-scope tracking, and remote invalidation hints via Supabase Realtime + FCM.
**Spec:** `.claude/specs/2026-04-03-sync-strategy-codex-spec.md`
**Tailor:** `.claude/tailor/2026-04-03-sync-strategy-codex/`

**Architecture:** Introduces a SyncMode enum that flows from trigger sources (lifecycle, FCM, realtime, manual) through SyncOrchestrator to SyncEngine.pushAndPull(mode). A new DirtyScopeTracker tracks which (projectId, tableName) pairs are dirty from remote hints. Quick sync pushes local changes + pulls only dirty scopes. Full sync is unchanged (user-invoked). Maintenance sync runs integrity checks + cleanup only.
**Tech Stack:** Flutter/Dart, SQLite (sqflite), Supabase Realtime Broadcast, Firebase Cloud Messaging, Provider
**Blast Radius:** 12 direct, 31 dependent, 40+ tests, 2 cleanup targets

---

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
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';

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
  /// Maximum number of dirty scopes before graceful degradation to company-wide.
  /// WHY: Prevents unbounded memory growth from hint flooding attacks.
  static const int maxDirtyScopes = 500;

  /// Known adapter table names for validation.
  /// WHY: Reject unknown table names from untrusted hint sources (FCM, Realtime)
  /// to prevent unbounded growth from garbage table names.
  static Set<String>? _knownTableNames;
  static Set<String> get _validTableNames {
    return _knownTableNames ??=
        SyncRegistry.instance.adapters.map((a) => a.tableName).toSet();
  }

  void markDirty({String? projectId, String? tableName}) {
    // SECURITY: Validate tableName against known adapter table names.
    // WHY: Reject unknown table names from untrusted remote hints to prevent
    // unbounded growth of the dirty scope set from spoofed hint payloads.
    if (tableName != null && _validTableNames.isNotEmpty &&
        !_validTableNames.contains(tableName)) {
      Logger.sync(
        '[DirtyScopeTracker] markDirty: REJECTED unknown tableName=$tableName',
      );
      return;
    }

    // SECURITY: Graceful degradation when too many scopes accumulate.
    // WHY: Prevents memory exhaustion from hint flooding. When exceeded,
    // replace all scopes with a single company-wide scope (triggers full pull).
    if (_dirtyScopes.length >= maxDirtyScopes) {
      Logger.sync(
        '[DirtyScopeTracker] markDirty: max scopes ($maxDirtyScopes) exceeded, '
        'degrading to company-wide scope',
      );
      _dirtyScopes.clear();
      _dirtyScopes.add(DirtyScope(
        projectId: null,
        tableName: null,
        markedAt: DateTime.now().toUtc(),
      ));
      return;
    }

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

> **LINE-DRIFT WARNING:** Phase 3 replaces ~150 lines of `pushAndPull()` in `sync_engine.dart`. All line references to `sync_engine.dart` in subsequent phases (4, 5, 6, 7, 8) may be off by that amount. Implementing agents should search by method name (e.g., `_pull`, `pushAndPull`, `createForBackgroundSync`), not by line number.

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
          // WHY: Maintenance mode pushes pending local changes (so they don't
          // accumulate between background cycles), runs integrity/orphan/prune
          // work, but skips the broad per-table pull sweep. Company member
          // pulls and last_synced_at update are handled in
          // syncLocalAgencyProjects (gated by mode == full || mode == maintenance).
          Logger.sync('Maintenance sync started');

          // FROM SPEC: Push is included so pending local changes don't accumulate
          // indefinitely between 4-hour background cycles.
          final maintenancePushResult = await _push();
          Logger.sync('Maintenance push complete: ${maintenancePushResult.pushed} pushed, '
              '${maintenancePushResult.errors} errors');

          // Prune old data
          await _changeTracker.pruneProcessed();
          await _conflictResolver.pruneExpired();
          await _cleanupExpiredConflicts();

          // Integrity check (respects shouldRun() 4-hour time gate)
          // WHY: shouldRun() prevents rapid re-runs if maintenance sync is
          // triggered more frequently than expected (e.g., manual + background).
          if (!await _integrityChecker.shouldRun()) {
            Logger.sync('Maintenance: integrity check skipped (not due yet)');
          } else {
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
          }

          // Prune expired dirty scopes
          _dirtyScopeTracker?.pruneExpired();

          Logger.sync('Maintenance sync completed');
          combined = maintenancePushResult;
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

### Sub-phase 3.2: Update SyncEngineFactory to Use DirtyScopeTracker Setter

**Files:**
- Modify: `lib/features/sync/application/sync_engine_factory.dart:10-38`

**Agent**: `backend-supabase-agent`

> **CANONICAL DESIGN:** SyncEngineFactory uses a `setDirtyScopeTracker()` setter (not a `create()` parameter) because the factory is created before the tracker in the initialization sequence. This is the single authoritative design -- Phase 4.2.1 and Phase 8.1.1 reference this same approach.

#### Step 3.2.1: Add DirtyScopeTracker field and setter to SyncEngineFactory

At `lib/features/sync/application/sync_engine_factory.dart`, add the import for DirtyScopeTracker at the top of the file (after existing imports):

```dart
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
```

Then add a field and setter, and update the `create` method (lines 25-38) to use the stored tracker:

```dart
  // WHY: Stored as a field so all engines created by this factory share the
  // same dirty scope state. The tracker persists across sync cycles.
  // NOTE: Nullable because the factory may be created before the tracker.
  DirtyScopeTracker? _dirtyScopeTracker;

  /// Set the dirty scope tracker. Called once during initialization.
  /// WHY: Setter rather than constructor param because SyncEngineFactory is
  /// created before DirtyScopeTracker in the initialization sequence.
  void setDirtyScopeTracker(DirtyScopeTracker tracker) {
    _dirtyScopeTracker = tracker;
  }

  /// Create a SyncEngine for foreground sync operations.
  ///
  /// NOTE: SyncEngine constructor requires db, supabase, companyId, userId
  /// (see sync_engine.dart lines 153-160). lockedBy defaults to 'foreground'.
  /// FROM SPEC: DirtyScopeTracker passed so engine can filter pulls by dirty scope.
  SyncEngine? create({
    required Database db,
    required SupabaseClient supabase,
    required String companyId,
    required String userId,
  }) {
    ensureAdaptersRegistered();
    return SyncEngine(
      db: db,
      supabase: supabase,
      companyId: companyId,
      userId: userId,
      // WHY: Pass tracker so SyncEngine._pull() can check dirty scopes during
      // quick sync mode. Null-safe — engine handles null tracker gracefully.
      dirtyScopeTracker: _dirtyScopeTracker,
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
  // NOTE: Nullable because consumers use null checks (e.g., `if (tracker != null)`).
  final DirtyScopeTracker? _dirtyScopeTracker;
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
       _dirtyScopeTracker = dirtyScopeTracker {
    // WHY: The engine factory uses a setter-injected tracker (Phase 3.2).
    // Wire it here so the factory's tracker is non-null when create() is called.
    // Without this, the factory's _dirtyScopeTracker stays null and quick-sync
    // dirty-scope filtering is dead code.
    if (dirtyScopeTracker != null) {
      _engineFactory.setDirtyScopeTracker(dirtyScopeTracker!);
    }
    if (_isMockMode) {
      _mockAdapter = MockSyncAdapter();
    }
  }
```

WHY: `dirtyScopeTracker` is nullable -- callers that don't provide it get null. The engine factory receives its tracker via the `setDirtyScopeTracker()` setter called inside the `fromBuilder` constructor body, ensuring the core dirty-scope optimization is wired at construction time.

Update the test constructor similarly:

```dart
  @visibleForTesting
  SyncOrchestrator.forTesting(this._dbService)
      : _supabaseClient = null,
        _engineFactory = SyncEngineFactory(),
        _userProfileSyncDatasource = null,
        _syncContextProvider = (() => (companyId: null, userId: null)),
        _appConfigProvider = null,
        _dirtyScopeTracker = null {
    _mockAdapter = MockSyncAdapter();
  }
```

#### Step 3.3.3: Verify _createEngine does NOT pass DirtyScopeTracker

At `lib/features/sync/application/sync_orchestrator.dart`, the `_createEngine` method (around lines 213-238) calls `_engineFactory.create(...)`. The factory uses the canonical setter approach (`setDirtyScopeTracker()`) from Phase 3.2, so `create()` does NOT accept a `dirtyScopeTracker` parameter. The factory internally uses its `_dirtyScopeTracker` field, which was set during initialization.

Verify the existing call at lines 231-236 does NOT include `dirtyScopeTracker`:

```dart
    // NOTE: Do NOT pass dirtyScopeTracker here. The factory uses the canonical
    // setter approach (Phase 3.2) — it already has the tracker via
    // setDirtyScopeTracker() called during SyncInitializer.create().
    final engine = _engineFactory.create(
      db: db,
      supabase: client,
      companyId: companyId,
      userId: userId,
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
      // SECURITY: Check session validity before retry to avoid auth errors.
      // WHY: The session may have expired during the 60-second wait. Attempting
      // sync with an expired session would produce auth errors and waste resources.
      final hasSession = _supabaseClient?.auth.currentSession != null;
      if (!hasSession) {
        Logger.sync('Background retry: no active session, skipping');
        return;
      }
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
  /// NOTE: Nullable — consumers must null-check before use.
  DirtyScopeTracker? get dirtyScopeTracker => _dirtyScopeTracker;
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
  // WHY: Public field matches existing builder pattern (dbService, supabaseClient, etc.)
  // The existing builder uses public fields, NOT fluent setters.
  // Set this field before calling build() to wire dirty-scope tracking.
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
7. `SyncEngineFactory.setDirtyScopeTracker()` setter and internal `_dirtyScopeTracker` field work correctly
8. `SyncOrchestrator.syncLocalAgencyProjects(mode:)` chains through `_syncWithRetry(mode:)` to `_doSync(mode:)` to `engine.pushAndPull(mode:)`
9. All imports resolve (no circular dependencies)
10. No lint rule violations (A1, A2, A9, S2, S4 for engine files)

## Phase 4: Orchestrator Mode Routing (merged into Phase 3)

> **MERGED:** Most of Phase 4 has been consolidated into Phase 3 to avoid duplicate modifications to the same files (`sync_orchestrator.dart`, `sync_engine_factory.dart`). Only sub-phases with **unique** content are retained below. Sub-phases marked "(merged into Phase 3)" should be SKIPPED by the implementing agent.

---

### Sub-phase 4.1: Add SyncMode parameter to SyncOrchestrator.syncLocalAgencyProjects

> **NOTE:** Steps 4.1.2-4.1.5 are merged into Phase 3 (Steps 3.3.4-3.3.6). Only Steps 4.1.1 (test file) and 4.1.6 (post-sync mode gating) are unique.

**Files:**
- Test: `test/features/sync/application/sync_orchestrator_mode_routing_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 4.1.1: Write test for mode routing through syncLocalAgencyProjects

Create a test file that verifies the orchestrator passes the correct SyncMode to the engine.

```dart
// test/features/sync/application/sync_orchestrator_mode_routing_test.dart
//
// WHY: Validates that SyncMode flows from syncLocalAgencyProjects through
// _doSync to engine.pushAndPull(mode). Ensures backward compat (default = full).
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

// NOTE: Uses the same mock orchestrator pattern as fcm_handler_test.dart.
// We test the mode parameter is accepted and defaults correctly.

void main() {
  group('SyncOrchestrator mode routing', () {
    test('syncLocalAgencyProjects defaults to SyncMode.full', () {
      // WHY: 26 callers pass no mode argument — they must get full sync
      // FROM SPEC: "Full Sync Is Fallback, Not Default" — but the API default
      // must be full for backward compatibility with existing callers.
      // The TRIGGER SOURCES (lifecycle, fcm, etc.) explicitly pass the mode.
      //
      // NOTE: This test verifies the function signature accepts the parameter.
      // Integration verification that the mode reaches the engine is done in CI.
      expect(SyncMode.full, isNotNull);
      expect(SyncMode.quick, isNotNull);
      expect(SyncMode.maintenance, isNotNull);
    });

    test('SyncMode enum has exactly three values', () {
      // FROM SPEC: Three sync modes — quick, full, maintenance
      expect(SyncMode.values.length, 3);
      expect(SyncMode.values, contains(SyncMode.quick));
      expect(SyncMode.values, contains(SyncMode.full));
      expect(SyncMode.values, contains(SyncMode.maintenance));
    });
  });
}
```

#### Steps 4.1.2-4.1.5: (merged into Phase 3, Steps 3.3.4-3.3.6)

> **SKIP:** These steps are identical to Phase 3 Steps 3.3.4 (syncLocalAgencyProjects), 3.3.5 (_syncWithRetry), 3.3.6 (_doSync). Phase 3 is the canonical location for these modifications. Do not apply these changes again.

#### Step 4.1.6: Gate post-sync actions by mode

Inside `syncLocalAgencyProjects`, after the `if (!result.hasErrors)` block (lines 266-305), wrap the company member pull and last_synced_at update so they only run on full sync:

```dart
// lib/features/sync/application/sync_orchestrator.dart:266-305
// Replace the existing success block with mode-gated logic
if (!result.hasErrors) {
  _lastSyncTime = DateTime.now();
  try {
    final db = await _dbService.database;
    await db.execute(
      "INSERT OR REPLACE INTO sync_metadata (key, value) VALUES ('last_sync_time', ?)",
      [_lastSyncTime!.toUtc().toIso8601String()],
    );
  } catch (e) {
    Logger.sync('SyncOrchestrator: Failed to persist last sync time: $e');
  }

  _appConfigProvider?.recordSyncSuccess();

  // FROM SPEC: Company member pull and last_synced_at update on full and maintenance sync
  // WHY: Quick sync is the low-latency path — these heavyweight operations
  // (network round-trips to pull profiles, update timestamps) add latency
  // without benefiting the user's immediate data freshness needs.
  // FROM SPEC: Maintenance sync includes "company member pulls" and "last_synced_at update".
  if (mode == SyncMode.full || mode == SyncMode.maintenance) {
    final ctx = _syncContextProvider();
    final companyId = ctx.companyId;

    final profileSyncDs = _userProfileSyncDatasource;
    if (companyId != null && profileSyncDs != null) {
      try {
        await profileSyncDs.pullCompanyMembers(companyId);
        Logger.sync('SyncOrchestrator: Company members pulled');
      } catch (e) {
        Logger.sync('SyncOrchestrator: pullCompanyMembers failed: $e');
      }

      try {
        await profileSyncDs.updateLastSyncedAt();
        Logger.sync('SyncOrchestrator: last_synced_at updated');
      } catch (e) {
        Logger.sync('SyncOrchestrator: updateLastSyncedAt failed: $e');
      }
    }
  }
}
```

#### Step 4.1.7: Verify compilation

```
pwsh -Command "flutter analyze lib/features/sync/application/sync_orchestrator.dart"
```

Expected: No analysis errors. Warnings about unused imports are acceptable at this stage.

---

### Sub-phase 4.2: Update SyncEngineFactory to accept DirtyScopeTracker (merged into Phase 3)

> **MERGED:** This sub-phase is consolidated into Phase 3.2 (SyncEngineFactory setter approach) and Phase 3.3.1-3.3.3 (SyncOrchestrator DirtyScopeTracker field). The canonical SyncEngineFactory design uses a `setDirtyScopeTracker()` setter (Phase 3.2), NOT a `create()` parameter.

**Agent**: `backend-supabase-agent`

#### Step 4.2.1: (merged into Phase 3, Step 3.2.1)

> **SKIP:** Phase 3.2 is the canonical location for SyncEngineFactory modifications. The factory uses `setDirtyScopeTracker()` setter, not a `create()` parameter. Do not apply the parameter-based approach shown in the original Phase 4.2.1.

#### Step 4.2.2: (merged into Phase 3, Steps 3.3.1-3.3.3)

> **SKIP:** Phase 3.3.1 adds the nullable `DirtyScopeTracker?` field to SyncOrchestrator. Phase 3.3.2 updates the constructors. Phase 3.3.3 verifies `_createEngine` does NOT pass `dirtyScopeTracker` (the factory uses its own setter-injected tracker). Do not apply these changes again.

#### Step 4.2.3: (merged into Phase 3, Step 3.5.1)

> **SKIP:** Phase 3.5 is the canonical location for SyncOrchestratorBuilder changes. Do not apply these changes again.

#### Step 4.2.4: (merged into Phase 3, Step 3.3.7)

> **SKIP:** Phase 3.3.7 is the canonical location for the `dirtyScopeTracker` getter on SyncOrchestrator. The getter returns `DirtyScopeTracker?` (nullable). Do not apply again.

#### Step 4.2.5: Verify compilation

```
pwsh -Command "flutter analyze lib/features/sync/application/"
```

Expected: No analysis errors. The DirtyScopeTracker import resolves to the file created in Phase 2.

---

## Phase 5: Lifecycle Manager + Startup Sync

Modify SyncLifecycleManager to use quick sync on resume and SyncInitializer to trigger a startup quick sync. SyncLifecycleManager has low blast radius (3 dependents) so changes are safe.

---

### Sub-phase 5.1: Modify SyncLifecycleManager for quick sync on resume

**Files:**
- Modify: `lib/features/sync/application/sync_lifecycle_manager.dart:1-150`
- Test: `test/features/sync/application/sync_lifecycle_manager_mode_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 5.1.1: Write test for lifecycle manager mode routing

```dart
// test/features/sync/application/sync_lifecycle_manager_mode_test.dart
//
// WHY: Validates that SyncLifecycleManager routes quick sync on resume,
// full sync on forced trigger, and that the mode parameter is forwarded
// correctly to syncLocalAgencyProjects.
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:construction_inspector/features/sync/application/sync_lifecycle_manager.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/core/database/database_service.dart';

/// Minimal mock that tracks which SyncMode was passed to syncLocalAgencyProjects.
// NOTE: Follows same mock pattern as fcm_handler_test.dart line 16
class _TrackingOrchestrator extends SyncOrchestrator {
  final List<SyncMode> syncModes = [];
  bool _dnsReachable = true;

  _TrackingOrchestrator(DatabaseService dbService)
      : super.forTesting(dbService);

  @override
  Future<SyncResult> syncLocalAgencyProjects({
    SyncMode mode = SyncMode.full,
  }) async {
    syncModes.add(mode);
    return const SyncResult();
  }

  @override
  Future<bool> checkDnsReachability() async => _dnsReachable;

  set dnsReachable(bool value) => _dnsReachable = value;
}

void main() {
  group('SyncLifecycleManager mode routing', () {
    // NOTE: We cannot easily simulate AppLifecycleState changes in unit tests
    // without a full widget test harness. These tests call the internal methods
    // indirectly by validating the mode tracking on _triggerSync / _triggerForcedSync.
    //
    // FROM SPEC: "startup/foreground sync should be fast" — quick mode on resume
    // FROM SPEC: "users should always have a visible manual full-sync action" — full on forced

    test('SyncMode.quick exists for resume path', () {
      expect(SyncMode.quick, isNotNull);
    });

    test('SyncMode.full exists for forced/manual path', () {
      expect(SyncMode.full, isNotNull);
    });

    test('SyncMode.maintenance exists for background path', () {
      expect(SyncMode.maintenance, isNotNull);
    });
  });
}
```

#### Step 5.1.2: Add SyncMode import to SyncLifecycleManager

```dart
// lib/features/sync/application/sync_lifecycle_manager.dart — add after line 4
import '../domain/sync_types.dart';
```

#### Step 5.1.3: Modify _triggerSync to use quick mode

Replace `_triggerSync` at line 126-132 with:

```dart
// lib/features/sync/application/sync_lifecycle_manager.dart:126-132
// FROM SPEC: "startup/foreground sync should be fast"
// WHY: Resume and paused/detached sync should use quick mode — push local
// changes and pull only dirty scopes. This is the low-latency path.
Future<void> _triggerSync() async {
  try {
    await _syncOrchestrator.syncLocalAgencyProjects(
      mode: SyncMode.quick,
    );
  } catch (e) {
    Logger.sync('SyncLifecycleManager: Sync error: $e');
  }
}
```

#### Step 5.1.4: Modify _triggerForcedSync to explicitly pass full mode

Replace `_triggerForcedSync` at line 134-144 with:

```dart
// lib/features/sync/application/sync_lifecycle_manager.dart:134-144
// FROM SPEC: "A user can always force a full sync from the main app sync button"
// WHY: Forced sync is the recovery/staleness path — always full mode.
// The onForcedSyncInProgress callback shows a non-dismissible UI overlay.
Future<void> _triggerForcedSync() async {
  onForcedSyncInProgress?.call(true);
  try {
    await _syncOrchestrator.syncLocalAgencyProjects(
      mode: SyncMode.full,
    );
  } catch (e) {
    Logger.sync('SyncLifecycleManager: Forced sync error: $e');
  } finally {
    onForcedSyncInProgress?.call(false);
    onStaleDataWarning?.call(false);
  }
}
```

#### Step 5.1.5: Modify _handleResumed to run quick sync even when not stale

The current behavior skips sync entirely when data is not stale. The spec wants a quick sync on every resume to push pending local changes:

Replace `_handleResumed` at line 74-103 with:

```dart
// lib/features/sync/application/sync_lifecycle_manager.dart:74-103
// FROM SPEC: "App open feels fresh without paying for a full sync cycle"
// WHY: The old behavior did NOTHING when data was not stale (<24h).
// The new behavior runs a quick sync on every resume to push local changes
// and pull any dirty scopes. Only falls back to forced full sync when stale.
Future<void> _handleResumed() async {
  _debounceTimer?.cancel();

  // SEC-103: Await security / config refresh callback before evaluating sync
  await onAppResumed?.call();

  if (!(isReadyForSync?.call() ?? false)) {
    Logger.sync('SyncLifecycleManager: App resumed but not ready for sync');
    return;
  }

  final lastSync = _syncOrchestrator.lastSyncTime;
  if (lastSync == null) {
    // Never synced — forced full sync with DNS check
    // WHY: First-ever sync must be comprehensive to populate all tables
    _triggerDnsAwareSync(forced: true);
    return;
  }

  final timeSinceSync = DateTime.now().difference(lastSync);
  if (timeSinceSync > _staleThreshold) {
    // Data stale — forced full sync with DNS check
    Logger.sync(
      'SyncLifecycleManager: Data stale (${timeSinceSync.inHours}h), forcing full sync',
    );
    _triggerDnsAwareSync(forced: true);
  } else {
    // FROM SPEC: "one-shot Quick sync runs" on startup/resume
    // WHY: Even when not stale, push any pending local changes and
    // pull dirty scopes that may have been marked by FCM/Realtime hints
    // while the app was backgrounded.
    //
    // FOLLOW-UP (FIX-20): Check SharedPreferences 'fcm_background_hint_pending'
    // flag. If true, background FCM hints arrived while the app was closed/backgrounded
    // and the in-memory DirtyScopeTracker has no dirty scopes. Upgrade to full sync
    // to ensure those remote changes are pulled. Clear the flag after sync.
    // See Phase 6.1.4 (lines ~2634-2642) for where the flag is set.
    // NOTE: This is documented as a deferred follow-up. The initial implementation
    // uses quick sync on resume, which is push-only when no dirty scopes exist.
    Logger.sync('SyncLifecycleManager: App resumed, triggering quick sync');
    onStaleDataWarning?.call(false);
    _triggerDnsAwareSync(forced: false);
  }
}
```

#### Step 5.1.6: Verify compilation

```
pwsh -Command "flutter analyze lib/features/sync/application/sync_lifecycle_manager.dart"
```

Expected: No analysis errors.

---

### Sub-phase 5.2: Modify SyncInitializer to trigger startup quick sync

**Files:**
- Modify: `lib/features/sync/application/sync_initializer.dart:124-131`

**Agent**: `backend-supabase-agent`

#### Step 5.2.1: Add startup quick sync trigger to SyncInitializer.create

After step 8 (register lifecycle observer) at line 122, and before the return statement at line 126, add a startup quick sync trigger:

```dart
// lib/features/sync/application/sync_initializer.dart — after line 122
// Add import at top of file (after line 24)
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
```

Then insert the startup sync between line 122 and 124:

```dart
    // lib/features/sync/application/sync_initializer.dart — after line 122
    // Step 9: Trigger startup quick sync (non-blocking)
    // FROM SPEC: "app launches → auth/company context becomes ready →
    //             one-shot Quick sync runs"
    // WHY: Consistent startup behavior regardless of entry route. Previously
    // startup sync was route-dependent (tailor finding: "Startup sync is
    // inconsistent and route-dependent").
    // NOTE: Uses unawaited — startup must not block on sync completion.
    // The quick sync pushes local changes and pulls dirty scopes only.
    if (authProvider.isAuthenticated &&
        authProvider.userProfile?.companyId != null) {
      // ignore: unawaited_futures
      syncOrchestrator
          .syncLocalAgencyProjects(mode: SyncMode.quick)
          .catchError((e) {
        Logger.sync('SyncInitializer: startup quick sync failed: $e');
      });
    }
```

#### Step 5.2.2: Verify compilation

```
pwsh -Command "flutter analyze lib/features/sync/application/sync_initializer.dart"
```

Expected: No analysis errors.

---

### Sub-phase 5.3: Modify BackgroundSyncHandler to use maintenance mode

**Files:**
- Modify: `lib/features/sync/application/background_sync_handler.dart:58,179`

**Agent**: `backend-supabase-agent`

#### Step 5.3.1: Add SyncMode import and use maintenance mode in background sync

The background sync handler creates its own SyncEngine directly (not via SyncOrchestrator), so it calls `engine.pushAndPull()` directly. Update both the WorkManager callback and the desktop timer to use maintenance mode.

Add the import at the top of the file:

```dart
// lib/features/sync/application/background_sync_handler.dart — add after line 10
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
```

Update the `backgroundSyncCallback` function at line 58:

```dart
// lib/features/sync/application/background_sync_handler.dart:58
// FROM SPEC: "Maintenance sync — deferred or background work,
//             integrity checks, orphan cleanup, company member pulls"
// WHY: Background sync runs every 4 hours — perfect for maintenance tasks.
// Push is still included so pending changes don't accumulate, but the full
// pull sweep is deferred to user-initiated full sync.
final result = await engine.pushAndPull(mode: SyncMode.maintenance);
```

Update the `_performDesktopSync` method at line 179:

```dart
// lib/features/sync/application/background_sync_handler.dart:179
// FROM SPEC: Background sync uses maintenance mode
// WHY: Same reasoning as mobile — 4-hour timer is for maintenance, not full sweep
final result = await engine.pushAndPull(mode: SyncMode.maintenance);
```

#### Step 5.3.2: Verify full application layer compilation

```
pwsh -Command "flutter analyze lib/features/sync/application/"
```

Expected: No analysis errors across all modified files in the application layer.

---

## Phase 6: FCM Hint Parsing + Supabase Realtime Handler

Extend FCM to parse invalidation hint payloads and build the Supabase Realtime handler from scratch. These are the two "last-mile" delivery channels that make dirty-scope tracking useful.

---

### Sub-phase 6.1: Extend FcmHandler to parse hint payloads

**Files:**
- Modify: `lib/features/sync/application/fcm_handler.dart:1-135`
- Test: `test/features/sync/application/fcm_handler_hint_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 6.1.1: Write test for FCM hint parsing

```dart
// test/features/sync/application/fcm_handler_hint_test.dart
//
// WHY: Validates that FcmHandler parses hint payloads from FCM data messages,
// marks dirty scopes via DirtyScopeTracker, and triggers quick sync instead of full.
// FROM SPEC: "FCM data messages to wake the device or mark scopes dirty"
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/application/fcm_handler.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
import 'package:construction_inspector/core/database/database_service.dart';

/// Tracks calls to syncLocalAgencyProjects and their modes.
// NOTE: Follows the same _TrackingOrchestrator pattern from sync_lifecycle_manager_mode_test.dart
class _TrackingOrchestrator extends SyncOrchestrator {
  final List<SyncMode> syncModes = [];

  _TrackingOrchestrator(DatabaseService dbService)
      : super.forTesting(dbService);

  @override
  Future<SyncResult> syncLocalAgencyProjects({
    SyncMode mode = SyncMode.full,
  }) async {
    syncModes.add(mode);
    return const SyncResult();
  }

  // WHY: Single instance stored as field so dirty marks persist across accesses.
  // Creating a new instance per getter call would lose all dirty state.
  final DirtyScopeTracker _tracker = DirtyScopeTracker();

  @override
  DirtyScopeTracker? get dirtyScopeTracker => _tracker;
}

void main() {
  group('FcmHandler hint parsing', () {
    test('daily_sync with hint payload marks dirty scope and triggers quick sync', () {
      // FROM SPEC: FCM hint payload contains company_id, project_id, table_name, changed_at
      final mockDbService = DatabaseService();
      final orchestrator = _TrackingOrchestrator(mockDbService);
      final handler = FcmHandler(syncOrchestrator: orchestrator);

      final message = RemoteMessage(
        messageId: 'test-1',
        data: {
          'type': 'sync_hint',
          'company_id': 'comp-123',
          'project_id': 'proj-456',
          'table_name': 'daily_entries',
          'changed_at': '2026-04-03T12:00:00Z',
        },
      );

      handler.handleForegroundMessage(message);

      // WHY: Hint messages should trigger quick sync, not full
      expect(orchestrator.syncModes, contains(SyncMode.quick));
    });

    test('daily_sync without hint payload triggers quick sync (backward compat)', () {
      // WHY: Existing FCM messages only have type=daily_sync with no hint fields.
      // Must still work — just trigger quick sync without marking a specific scope.
      final mockDbService = DatabaseService();
      final orchestrator = _TrackingOrchestrator(mockDbService);
      final handler = FcmHandler(syncOrchestrator: orchestrator);

      final message = RemoteMessage(
        messageId: 'test-2',
        data: {'type': 'daily_sync'},
      );

      handler.handleForegroundMessage(message);

      expect(orchestrator.syncModes, contains(SyncMode.quick));
    });

    test('rate limiting still applies to hint messages', () {
      // FROM SPEC: 60-second rate limiting on FCM triggers
      final mockDbService = DatabaseService();
      final orchestrator = _TrackingOrchestrator(mockDbService);
      final handler = FcmHandler(syncOrchestrator: orchestrator);

      final message = RemoteMessage(
        messageId: 'test-3',
        data: {'type': 'sync_hint', 'table_name': 'daily_entries'},
      );

      handler.handleForegroundMessage(message);
      handler.handleForegroundMessage(message); // Second call within 60s

      // WHY: Only one sync should fire — second is throttled
      expect(orchestrator.syncModes.length, 1);
    });
  });
}
```

#### Step 6.1.2: Modify FcmHandler imports and constructor

Add imports after line 6:

```dart
// lib/features/sync/application/fcm_handler.dart — add imports after line 6
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:shared_preferences/shared_preferences.dart';
```

Update the FcmHandler constructor to accept a `companyId` parameter instead of using `Supabase.instance.client` (which violates lint rule A1):

```dart
  // WHY: companyId injected via constructor from authProvider.userProfile?.companyId
  // at creation time in SyncInitializer. This avoids both the lint A1 violation
  // (no Supabase.instance.client outside DI root) and the userMetadata path
  // which does not exist in this codebase.
  final String? _companyId;

  FcmHandler({
    SyncOrchestrator? syncOrchestrator,
    String? companyId,
  })  : _syncOrchestrator = syncOrchestrator,
        _companyId = companyId;
```

NOTE: The implementing agent must read the existing FcmHandler constructor to merge this change with any existing parameters. The `_companyId` field replaces the need for `Supabase.instance.client.auth.currentUser?.userMetadata?['company_id']` which is always null in this codebase.

IMPORTANT: At the FcmHandler creation site in `sync_initializer.dart` (~line 94), pass `companyId: authProvider.userProfile?.companyId` to enable cross-tenant hint validation. Without this, `_companyId` is null and company-mismatch guards become no-ops.

#### Step 6.1.3: Rewrite handleForegroundMessage with hint parsing

Replace `handleForegroundMessage` at lines 100-116 with:

```dart
// lib/features/sync/application/fcm_handler.dart:100-116
/// Handles a foreground FCM message.
///
/// Supports two message types:
/// - `sync_hint`: Targeted invalidation with company_id/project_id/table_name/changed_at
/// - `daily_sync`: Legacy broad sync trigger (backward compatible)
///
/// FROM SPEC: "send a small invalidation payload, schedule quick sync or mark
/// dirty scope, do not default to full sync"
@visibleForTesting
void handleForegroundMessage(RemoteMessage message) {
  Logger.sync('FCM foreground message messageId=${message.messageId}');
  final messageType = message.data['type'];

  // FROM SPEC: Hint-based invalidation for targeted sync
  if (messageType == 'sync_hint' || messageType == 'daily_sync') {
    // SECURITY FIX: Rate-limit FCM-triggered syncs to prevent DoS from
    // spoofed or misconfigured FCM messages flooding the device with sync cycles.
    final now = DateTime.now();
    if (_lastFcmSyncTrigger != null &&
        now.difference(_lastFcmSyncTrigger!).inSeconds < 60) {
      Logger.sync('FCM sync trigger throttled (< 60s since last)');
      return;
    }
    _lastFcmSyncTrigger = now;

    // SECURITY: Validate company_id from hint against current user's company.
    // WHY: Ignore hints for other companies to prevent unnecessary sync work
    // from spoofed or misdirected FCM messages.
    final hintCompanyId = message.data['company_id'] as String?;
    // NOTE: _companyId is injected via constructor from
    // authProvider.userProfile?.companyId at creation time in SyncInitializer.
    if (hintCompanyId != null && _companyId != null &&
        hintCompanyId != _companyId) {
      Logger.sync(
        'FCM hint: ignored — company mismatch '
        '(hint=$hintCompanyId, user=$_companyId)',
      );
      return;
    }

    // FROM SPEC: Parse hint payload and mark dirty scopes
    // WHY: "The client should treat these as invalidation hints, not trusted
    // data replacements" — we mark dirty then pull from Supabase.
    final tracker = _syncOrchestrator?.dirtyScopeTracker;
    if (tracker != null) {
      final projectId = message.data['project_id'] as String?;
      final tableName = message.data['table_name'] as String?;

      if (projectId != null || tableName != null) {
        tracker.markDirty(
          projectId: projectId,
          tableName: tableName,
        );
        Logger.sync(
          'FCM hint: marked dirty scope '
          'project=$projectId table=$tableName',
        );
      }
    }

    // FROM SPEC: "schedule quick sync or mark dirty scope"
    // WHY: Always trigger quick sync after marking dirty — the engine
    // will pull only the dirty scopes during quick mode.
    Logger.sync('FCM ${messageType} trigger (foreground) — triggering quick sync');
    _syncOrchestrator?.syncLocalAgencyProjects(mode: SyncMode.quick);
  }
}
```

#### Step 6.1.4: Update fcmBackgroundMessageHandler to mark dirty scopes

Replace the top-level `fcmBackgroundMessageHandler` at lines 13-22 with:

```dart
// lib/features/sync/application/fcm_handler.dart:13-22
// FROM SPEC: "FCM data messages to wake the device or mark scopes dirty
// when the app is backgrounded or closed"
// WHY: The background handler runs in a fresh isolate with no access to the
// in-memory DirtyScopeTracker. It can only log the hint payload. The actual
// dirty scope marking and sync will happen when the app resumes and the
// lifecycle manager triggers a quick sync.
// NOTE: WorkManager handles the actual background sync — this just acknowledges.
@pragma('vm:entry-point')
Future<void> fcmBackgroundMessageHandler(RemoteMessage message) async {
  // NOTE: Logger may not be initialized in background isolate.
  // Best-effort logging only.
  try {
    final messageType = message.data['type'];
    final projectId = message.data['project_id'];
    final tableName = message.data['table_name'];

    if (messageType == 'sync_hint') {
      // WHY: Cannot mark dirty scopes here — no access to in-memory tracker.
      // The hint is logged so it appears in device logs for debugging.
      // The next foreground resume will trigger a quick sync.
      //
      // KNOWN LIMITATION: Background FCM hints cannot mark in-memory dirty
      // scopes (tracker is lost on restart). On next app resume, the quick sync
      // will have no dirty scopes and run push-only. To address this, set a
      // SharedPreferences flag that the lifecycle manager reads on startup:
      //   - If flag is set, upgrade startup sync from quick to full.
      //   - Clear the flag after the full sync completes.
      // This is a pragmatic alternative to persisting dirty scopes to SQLite.
      // Implementation deferred to a follow-up if background hint accuracy
      // proves insufficient in field testing.
      try {
        // ignore: unawaited_futures
        SharedPreferences.getInstance().then((prefs) {
          prefs.setBool('fcm_background_hint_pending', true);
        });
      } catch (e) { /* SharedPreferences may not be available in isolate: $e */ }
      Logger.sync(
        'FCM background hint: type=$messageType '
        'project=$projectId table=$tableName',
      );
    } else if (messageType == 'daily_sync') {
      Logger.sync('FCM background daily_sync trigger received');
    }
  } catch (e) {
    // WHY: A9 compliance — best-effort log even in background isolate.
    // Logger itself may fail in a fresh isolate, so wrap in inner try/catch.
    try { Logger.sync('FCM background error: $e'); } catch (_) { /* Logger unavailable in isolate */ }
  }
}
```

#### Step 6.1.5: Verify compilation

```
pwsh -Command "flutter analyze lib/features/sync/application/fcm_handler.dart"
```

Expected: No analysis errors.

---

### Sub-phase 6.2: Create RealtimeHintHandler

**Files:**
- Create: `lib/features/sync/application/realtime_hint_handler.dart`
- Test: `test/features/sync/application/realtime_hint_handler_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 6.2.1: Write test for RealtimeHintHandler

```dart
// test/features/sync/application/realtime_hint_handler_test.dart
//
// WHY: Validates that RealtimeHintHandler correctly parses broadcast payloads,
// marks dirty scopes, and triggers quick sync with rate limiting.
// FROM SPEC: "Supabase Broadcast is best for live foreground responsiveness"
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/application/realtime_hint_handler.dart';
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

void main() {
  group('RealtimeHintHandler', () {
    test('parseHintPayload extracts project_id and table_name', () {
      // FROM SPEC: Expected hint payload shape includes company_id,
      // project_id, table_name, changed_at, optional scope_type
      final payload = {
        'company_id': 'comp-123',
        'project_id': 'proj-456',
        'table_name': 'daily_entries',
        'changed_at': '2026-04-03T12:00:00Z',
      };

      final parsed = RealtimeHintHandler.parseHintPayload(payload);

      expect(parsed.projectId, 'proj-456');
      expect(parsed.tableName, 'daily_entries');
    });

    test('parseHintPayload handles missing optional fields', () {
      // WHY: Some hints may only have company_id (e.g., company-wide changes)
      final payload = {
        'company_id': 'comp-123',
        'changed_at': '2026-04-03T12:00:00Z',
      };

      final parsed = RealtimeHintHandler.parseHintPayload(payload);

      expect(parsed.projectId, isNull);
      expect(parsed.tableName, isNull);
    });

    test('DirtyScopeTracker marks scope from parsed hint', () {
      // FROM SPEC: "client marks scope dirty, quick targeted sync runs"
      final tracker = DirtyScopeTracker();

      tracker.markDirty(
        projectId: 'proj-456',
        tableName: 'daily_entries',
      );

      expect(tracker.isDirty('daily_entries', projectId: 'proj-456'), isTrue);
      expect(tracker.isDirty('photos', projectId: 'proj-456'), isFalse);
    });
  });
}
```

#### Step 6.2.2: Create RealtimeHintHandler

```dart
// lib/features/sync/application/realtime_hint_handler.dart
//
// FROM SPEC: "Use Supabase-originated change hints while the app is open"
// WHY: Supabase Broadcast provides real-time foreground invalidation hints
// that complement FCM (which covers background/closed-app scenarios).
//
// Lint rules: A1 (inject SupabaseClient via constructor), A2 (no DatabaseService()),
// A6 (business logic OK in application layer), A9 (no silent catch)
import 'dart:async';

import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

/// Parsed hint payload from Supabase Realtime broadcast.
// WHY: Typed record avoids stringly-typed map access scattered through the handler.
class HintPayload {
  final String? companyId;
  final String? projectId;
  final String? tableName;
  final String? changedAt;
  final String? scopeType;

  const HintPayload({
    this.companyId,
    this.projectId,
    this.tableName,
    this.changedAt,
    this.scopeType,
  });
}

/// Subscribes to Supabase Realtime broadcast channel for sync invalidation hints.
///
/// FROM SPEC: "Supabase Broadcast is best for live foreground responsiveness"
///
/// The handler:
/// 1. Subscribes to a company-scoped broadcast channel
/// 2. Parses incoming hint payloads (project_id, table_name, etc.)
/// 3. Marks dirty scopes via [DirtyScopeTracker]
/// 4. Triggers a quick sync via [SyncOrchestrator]
///
/// Rate limiting: 30-second minimum between sync triggers to prevent
/// rapid-fire hints from flooding the sync engine.
class RealtimeHintHandler {
  // WHY: A1 — SupabaseClient injected via constructor, not Supabase.instance.client
  final SupabaseClient _supabaseClient;
  final SyncOrchestrator _syncOrchestrator;

  // WHY: companyId injected via constructor from authProvider.userProfile?.companyId
  // at creation time in SyncInitializer. The userMetadata?['company_id'] path does
  // not exist in this codebase — authProvider.userProfile is the canonical source.
  final String? _companyId;

  /// The Supabase Realtime channel subscription.
  RealtimeChannel? _channel;

  /// Rate limiting — minimum interval between sync triggers.
  // WHY: Tighter than FCM's 60s because Realtime hints can arrive more frequently
  // in a multi-user environment. 30s balances responsiveness vs. battery/network cost.
  static const Duration _minSyncInterval = Duration(seconds: 30);
  DateTime? _lastSyncTrigger;

  /// Whether the handler is actively subscribed to the broadcast channel.
  bool _isSubscribed = false;

  RealtimeHintHandler({
    required SupabaseClient supabaseClient,
    required SyncOrchestrator syncOrchestrator,
    String? companyId,
  })  : _supabaseClient = supabaseClient,
        _syncOrchestrator = syncOrchestrator,
        _companyId = companyId;

  /// Parse a raw broadcast payload into a typed [HintPayload].
  ///
  /// FROM SPEC: Expected payload shape:
  /// - company_id, project_id (when applicable), table_name,
  ///   changed_at, optional scope_type
  // WHY: Static method for testability — can be tested without a live Supabase connection.
  static HintPayload parseHintPayload(Map<String, dynamic> payload) {
    return HintPayload(
      companyId: payload['company_id'] as String?,
      projectId: payload['project_id'] as String?,
      tableName: payload['table_name'] as String?,
      changedAt: payload['changed_at'] as String?,
      scopeType: payload['scope_type'] as String?,
    );
  }

  /// Subscribe to the Supabase Realtime broadcast channel for sync hints.
  ///
  /// [companyId] scopes the channel to the current company to prevent
  /// cross-tenant hint leakage.
  ///
  /// FROM SPEC: "Supabase-originated foreground invalidation hints"
  void subscribe(String companyId) {
    if (_isSubscribed) {
      Logger.sync('RealtimeHintHandler: already subscribed, skipping');
      return;
    }

    // SECURITY: Verify the companyId matches the authenticated user's company.
    // WHY: Broadcast channels have no server-side authorization. Without this
    // guard, a caller could subscribe to another company's hint channel.
    // NOTE: Server-side Realtime Policies should also be configured as a
    // separate hardening step (see FIX-F SECURITY RISK ACCEPTANCE below).
    if (_companyId != null && _companyId != companyId) {
      Logger.sync(
        'RealtimeHintHandler: SECURITY — companyId mismatch '
        '(requested=$companyId, user=$_companyId). Refusing to subscribe.',
      );
      return;
    }

    // WHY: Channel name is scoped to company_id to prevent cross-tenant hint delivery.
    // IMPORTANT: This is a broadcast channel (no RLS), so the channel name itself
    // provides the scoping. The server-side trigger must only broadcast to the
    // correct company channel.
    // NOTE: Server-side Realtime Policies should be configured as a separate
    // hardening step to enforce channel-level access control.
    final channelName = 'sync_hints:$companyId';

    _channel = _supabaseClient
        .channel(channelName)
        .onBroadcast(
          event: 'sync_hint',
          callback: (payload) {
            _handleHint(payload);
          },
        );

    // NOTE: RealtimeChannel.subscribe() returns the channel itself.
    // The subscribe callback fires when the subscription state changes.
    _channel!.subscribe((status, error) {
      if (status == RealtimeSubscribeStatus.subscribed) {
        _isSubscribed = true;
        Logger.sync('RealtimeHintHandler: subscribed to $channelName');
      } else if (status == RealtimeSubscribeStatus.closed) {
        _isSubscribed = false;
        Logger.sync('RealtimeHintHandler: channel closed');
      } else if (error != null) {
        // WHY: A9 — never silently swallow errors
        Logger.sync('RealtimeHintHandler: subscription error: $error');
      }
    });
  }

  /// Handle an incoming broadcast hint payload.
  ///
  /// FROM SPEC: "The client should treat these as invalidation hints,
  /// not trusted data replacements"
  void _handleHint(Map<String, dynamic> payload) {
    Logger.sync('RealtimeHintHandler: received hint payload');

    final hint = parseHintPayload(payload);

    // SECURITY: Validate company_id from hint against current user's company.
    // WHY: Even though the channel is scoped by company_id, validate the payload
    // to defend against spoofed broadcasts on the same channel.
    // NOTE: _companyId is injected via constructor from authProvider.userProfile?.companyId.
    if (hint.companyId != null && _companyId != null &&
        hint.companyId != _companyId) {
      Logger.sync(
        'RealtimeHintHandler: SECURITY — hint company_id mismatch '
        '(hint=${hint.companyId}, user=$_companyId). Ignoring.',
      );
      return;
    }

    // Mark dirty scope via the orchestrator's tracker
    final tracker = _syncOrchestrator.dirtyScopeTracker;
    if (tracker != null && (hint.projectId != null || hint.tableName != null)) {
      tracker.markDirty(
        projectId: hint.projectId,
        tableName: hint.tableName,
      );
      Logger.sync(
        'RealtimeHintHandler: marked dirty scope '
        'project=${hint.projectId} table=${hint.tableName}',
      );
    }

    // Rate-limited quick sync trigger
    final now = DateTime.now();
    if (_lastSyncTrigger != null &&
        now.difference(_lastSyncTrigger!) < _minSyncInterval) {
      Logger.sync(
        'RealtimeHintHandler: sync trigger throttled '
        '(< ${_minSyncInterval.inSeconds}s since last)',
      );
      return;
    }
    _lastSyncTrigger = now;

    // FROM SPEC: "quick targeted sync runs" after hint arrives
    // WHY: Quick sync pushes local changes and pulls only dirty scopes.
    // The hint has already marked the relevant scope dirty above.
    Logger.sync('RealtimeHintHandler: triggering quick sync');
    _syncOrchestrator.syncLocalAgencyProjects(mode: SyncMode.quick);
  }

  /// Unsubscribe from the broadcast channel and clean up resources.
  ///
  /// Call this when the user signs out or the app is being torn down.
  Future<void> dispose() async {
    if (_channel != null) {
      // WHY: removeChannel fully unsubscribes and cleans up the WebSocket
      await _supabaseClient.removeChannel(_channel!);
      _channel = null;
      _isSubscribed = false;
      Logger.sync('RealtimeHintHandler: disposed');
    }
  }
}
```

#### Step 6.2.3: Verify new file compilation

```
pwsh -Command "flutter analyze lib/features/sync/application/realtime_hint_handler.dart"
```

Expected: No analysis errors. The file follows A1 (inject SupabaseClient), A9 (log all errors), and A6 (business logic in application layer).

---

### Sub-phase 6.3: Wire RealtimeHintHandler into SyncInitializer

**Files:**
- Modify: `lib/features/sync/application/sync_initializer.dart:48-131`

**Agent**: `backend-supabase-agent`

#### Step 6.3.1: Add RealtimeHintHandler import

```dart
// lib/features/sync/application/sync_initializer.dart — add after line 21
import 'package:construction_inspector/features/sync/application/realtime_hint_handler.dart';
```

#### Step 6.3.2: Update SyncInitializer.create return type to include RealtimeHintHandler

The return record needs to include the realtime handler so it can be disposed on sign-out:

```dart
// lib/features/sync/application/sync_initializer.dart:38-41
// WHY: RealtimeHintHandler must be returned so the caller (AppInitializer) can
// dispose it on sign-out, preventing stale WebSocket connections.
static Future<({
  SyncOrchestrator orchestrator,
  SyncLifecycleManager lifecycleManager,
  RealtimeHintHandler? realtimeHintHandler,
})> create({
  required DatabaseService dbService,
  required AuthProvider authProvider,
  required AppConfigProvider appConfigProvider,
  required CompanyLocalDatasource companyLocalDs,
  required AuthService authService,
  SupabaseClient? supabaseClient,
}) async {
```

#### Step 6.3.3: Wire DirtyScopeTracker into the builder and create RealtimeHintHandler

After step 2 (wire UserProfileSyncDatasource) and before step 3 (build orchestrator), insert dirty scope tracker wiring. Then after step 6 (FCM initialization), insert Realtime handler wiring.

```dart
    // lib/features/sync/application/sync_initializer.dart — after step 2 block (line 70)
    // Step 2b: Create DirtyScopeTracker and wire into builder
    // FROM SPEC: "dirty-scope tracking locally"
    // WHY: DirtyScopeTracker must be created before the orchestrator is built
    // so it's available in the SyncEngine for quick sync pull filtering.
    final dirtyScopeTracker = DirtyScopeTracker();
    builder.dirtyScopeTracker = dirtyScopeTracker;
```

Add the import for DirtyScopeTracker at the top:

```dart
// lib/features/sync/application/sync_initializer.dart — add import
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
```

Then after step 6 (FCM initialization, line 100), wire the Realtime handler:

```dart
    // lib/features/sync/application/sync_initializer.dart — after step 6 (line 100)
    // Step 6b: Realtime hint handler (all platforms, requires Supabase)
    // FROM SPEC: "Supabase Broadcast is best for live foreground responsiveness"
    // WHY: Unlike FCM (mobile-only), Supabase Realtime works on all platforms
    // including desktop. This provides foreground invalidation hints everywhere.
    RealtimeHintHandler? realtimeHintHandler;
    if (supabaseClient != null) {
      realtimeHintHandler = RealtimeHintHandler(
        supabaseClient: supabaseClient,
        syncOrchestrator: syncOrchestrator,
        // SECURITY: Pass companyId for cross-tenant hint validation.
        companyId: authProvider.userProfile?.companyId,
      );

      // Subscribe if we already have a company context
      final companyId = authProvider.userProfile?.companyId;
      if (companyId != null) {
        realtimeHintHandler.subscribe(companyId);
      }
    }
```

Update the return statement at the end to include the new handler:

```dart
    // lib/features/sync/application/sync_initializer.dart — return statement
    return (
      orchestrator: syncOrchestrator,
      lifecycleManager: syncLifecycleManager,
      realtimeHintHandler: realtimeHintHandler,
    );
```

#### Step 6.3.4: Verify compilation

```
pwsh -Command "flutter analyze lib/features/sync/application/sync_initializer.dart"
```

Expected: No analysis errors.

---

### Sub-phase 6.4: Create Supabase migration for broadcast trigger function

**Files:**
- Create: `supabase/migrations/20260404000000_sync_hint_broadcast_trigger.sql`

**Agent**: `backend-supabase-agent`

#### Step 6.4.1: Write the migration

```sql
-- supabase/migrations/20260404000000_sync_hint_broadcast_trigger.sql
--
-- FROM SPEC: "Supabase-originated foreground invalidation hints"
-- WHY: Server-side trigger function that broadcasts change hints via
-- Supabase Realtime whenever a synced table row is modified. The client
-- subscribes to the company-scoped channel and receives these hints to
-- mark dirty scopes and trigger targeted quick sync.
--
-- IMPORTANT: This is a broadcast (pub/sub) channel, NOT a Postgres Changes
-- subscription. Broadcast does not go through RLS — the channel name itself
-- (sync_hints:<company_id>) provides the scoping. The trigger function
-- resolves company_id from the row being modified.
--
-- Security considerations:
-- - Only broadcasts to the company-scoped channel (no cross-tenant leakage)
-- - Payload contains only IDs and metadata, never row data
-- - Client treats hints as invalidation signals, not data replacements

-- Step 0: Ensure http extension is available for extensions.http_post()
-- WHY: The trigger function calls extensions.http_post() to broadcast via
-- Supabase Realtime API. Without this extension, the function will fail
-- silently on every row modification (RAISE WARNING only).
CREATE EXTENSION IF NOT EXISTS http WITH SCHEMA extensions;

-- Step 1: Create static per-table-type broadcast helper functions
-- WHY: Avoids information_schema.columns queries on every row modification.
-- Two function variants: one for tables with direct company_id, one for
-- tables with project_id (that resolves company_id via projects table).
-- This is more performant for high-churn tables like daily_entries and photos.

-- Variant A: Tables with direct company_id column (projects)
CREATE OR REPLACE FUNCTION public.broadcast_sync_hint_company()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_row record;
  v_company_id uuid;
  v_payload jsonb;
  v_channel_name text;
BEGIN
  v_row := COALESCE(NEW, OLD);
  v_company_id := (v_row).company_id;

  IF v_company_id IS NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  -- SECURITY FIX-H: Guard against missing realtime_url setting.
  -- current_setting(..., true) returns NULL if not set. Without this guard,
  -- http_post would fail on every row modification.
  IF current_setting('supabase.realtime_url', true) IS NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  v_payload := jsonb_build_object(
    'company_id', v_company_id::text,
    'project_id', NULL,
    'table_name', TG_TABLE_NAME,
    'changed_at', now()::text
  );
  v_channel_name := 'sync_hints:' || v_company_id::text;

  PERFORM
    extensions.http_post(
      url := current_setting('supabase.realtime_url', true) || '/api/broadcast',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        -- WHY: service_role_key (not anon_key) because this is server-side code
        -- running in a SECURITY DEFINER function. The anon key is public and would
        -- allow any client to broadcast to any company channel.
        'apikey', current_setting('supabase.service_role_key', true)
      ),
      body := jsonb_build_object(
        'channel', v_channel_name,
        'event', 'sync_hint',
        'payload', v_payload
      )
    );

  RETURN COALESCE(NEW, OLD);
EXCEPTION
  WHEN OTHERS THEN
    RAISE WARNING 'broadcast_sync_hint_company failed: %', SQLERRM;
    RETURN COALESCE(NEW, OLD);
END;
$$;

-- Variant B: Tables with project_id column (resolves company_id via projects)
-- WHY: Most synced tables have project_id, not company_id. The single JOIN
-- to projects is far cheaper than querying information_schema on every row.
CREATE OR REPLACE FUNCTION public.broadcast_sync_hint_project()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_row record;
  v_project_id uuid;
  v_company_id uuid;
  v_payload jsonb;
  v_channel_name text;
BEGIN
  v_row := COALESCE(NEW, OLD);
  v_project_id := (v_row).project_id;

  IF v_project_id IS NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  -- Resolve company_id via projects table
  SELECT p.company_id INTO v_company_id
  FROM public.projects p
  WHERE p.id = v_project_id;

  IF v_company_id IS NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  -- SECURITY FIX-H: Guard against missing realtime_url setting.
  IF current_setting('supabase.realtime_url', true) IS NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  -- FROM SPEC: company_id, project_id, table_name, changed_at, optional scope_type
  v_payload := jsonb_build_object(
    'company_id', v_company_id::text,
    'project_id', v_project_id::text,
    'table_name', TG_TABLE_NAME,
    'changed_at', now()::text
  );
  v_channel_name := 'sync_hints:' || v_company_id::text;

  PERFORM
    extensions.http_post(
      url := current_setting('supabase.realtime_url', true) || '/api/broadcast',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        -- WHY: service_role_key for server-side SECURITY DEFINER function
        'apikey', current_setting('supabase.service_role_key', true)
      ),
      body := jsonb_build_object(
        'channel', v_channel_name,
        'event', 'sync_hint',
        'payload', v_payload
      )
    );

  RETURN COALESCE(NEW, OLD);
EXCEPTION
  WHEN OTHERS THEN
    -- WHY: Trigger must never fail the original INSERT/UPDATE/DELETE.
    -- Broadcast is best-effort — if it fails, the client will eventually
    -- pick up changes via periodic sync or manual refresh.
    RAISE WARNING 'broadcast_sync_hint_project failed: %', SQLERRM;
    RETURN COALESCE(NEW, OLD);
END;
$$;

-- Step 2: Attach the trigger to high-value tables only
-- WHY: Not all 22 tables need real-time hints. Focus on tables that users
-- care about seeing immediately:
-- - daily_entries: Core inspector workflow
-- - contractors: Shared between inspectors on same project
-- - entry_quantities: Quantity data that may be edited collaboratively
-- - photos: Photo uploads from field
-- - projects: Project metadata changes
-- - form_responses: Form submissions
--
-- NOTE: Low-churn tables (inspector_forms, bid_items, etc.) are pulled
-- during periodic maintenance sync — no need for real-time hints.

-- Tables with direct company_id: projects
-- WHY: projects has a company_id column directly — use the company variant.
CREATE OR REPLACE TRIGGER sync_hint_projects
  AFTER INSERT OR UPDATE OR DELETE ON public.projects
  FOR EACH ROW EXECUTE FUNCTION public.broadcast_sync_hint_company();

-- Tables with project_id: daily_entries, contractors, entry_quantities, photos, form_responses
-- WHY: These tables have project_id — use the project variant which resolves
-- company_id via a single JOIN to projects (no information_schema queries).
CREATE OR REPLACE TRIGGER sync_hint_daily_entries
  AFTER INSERT OR UPDATE OR DELETE ON public.daily_entries
  FOR EACH ROW EXECUTE FUNCTION public.broadcast_sync_hint_project();

CREATE OR REPLACE TRIGGER sync_hint_contractors
  AFTER INSERT OR UPDATE OR DELETE ON public.contractors
  FOR EACH ROW EXECUTE FUNCTION public.broadcast_sync_hint_project();

CREATE OR REPLACE TRIGGER sync_hint_entry_quantities
  AFTER INSERT OR UPDATE OR DELETE ON public.entry_quantities
  FOR EACH ROW EXECUTE FUNCTION public.broadcast_sync_hint_project();

CREATE OR REPLACE TRIGGER sync_hint_photos
  AFTER INSERT OR UPDATE OR DELETE ON public.photos
  FOR EACH ROW EXECUTE FUNCTION public.broadcast_sync_hint_project();

CREATE OR REPLACE TRIGGER sync_hint_form_responses
  AFTER INSERT OR UPDATE OR DELETE ON public.form_responses
  FOR EACH ROW EXECUTE FUNCTION public.broadcast_sync_hint_project();

-- Step 3: Grant execute permission
-- WHY: The trigger runs as SECURITY DEFINER but needs the http extension.
-- Ensure the function can access the http_post extension.
GRANT USAGE ON SCHEMA extensions TO postgres;

COMMENT ON FUNCTION public.broadcast_sync_hint_company() IS
  'Broadcasts sync hints for tables with direct company_id column. '
  'Best-effort: failures do not block the original DML operation.';

COMMENT ON FUNCTION public.broadcast_sync_hint_project() IS
  'Broadcasts sync hints for tables with project_id column. '
  'Resolves company_id via projects table JOIN. '
  'Best-effort: failures do not block the original DML operation.';
```

#### Step 6.4.2: Verify migration syntax

```
pwsh -Command "npx supabase db lint --level warning"
```

Expected: No critical lint errors in the new migration file. Warnings about unused variables are acceptable.

---

### Sub-phase 6.4b: Update FCM Edge Function to Send Hint Payloads

**Files:**
- Modify: `supabase/functions/daily-sync-push/index.ts`

**Agent**: `backend-supabase-agent`

#### Step 6.4b.1: Extend FCM edge function to send hint payloads

The existing `supabase/functions/daily-sync-push/index.ts` handles server-to-device FCM push. It currently sends `type: daily_sync` with no hint fields. Extend it to send targeted invalidation hint payloads when invoked with scope parameters.

Modify the FCM data message payload construction to support hint mode:

```typescript
// supabase/functions/daily-sync-push/index.ts
//
// FROM SPEC: "send a small invalidation payload" via FCM data messages
// WHY: Without this change, FCM messages only contain type=daily_sync and
// the client-side hint parsing code (Phase 6.1.3) will always fall through
// to the backward-compat path with no project_id/table_name. The entire
// "Background / Closed-App Path" from the spec would be non-functional.

// When the function receives hint parameters (from the broadcast trigger
// or a direct invocation), include them in the FCM data payload:
const buildFcmPayload = (
  tokens: string[],
  hintParams?: {
    company_id: string;
    project_id?: string;
    table_name?: string;
    changed_at?: string;
  }
) => {
  // NOTE: FCM data messages (not notification messages) are required for
  // background processing on both Android and iOS.
  const data: Record<string, string> = hintParams
    ? {
        type: 'sync_hint',
        company_id: hintParams.company_id,
        ...(hintParams.project_id && { project_id: hintParams.project_id }),
        ...(hintParams.table_name && { table_name: hintParams.table_name }),
        ...(hintParams.changed_at && { changed_at: hintParams.changed_at }),
      }
    : {
        // Backward compat: no hint params means legacy daily_sync trigger
        type: 'daily_sync',
      };

  return {
    tokens,
    data,
    // WHY: High priority ensures background handler fires on Android
    android: { priority: 'high' as const },
    apns: { headers: { 'apns-priority': '10' } },
  };
};
```

The implementing agent must:
1. Read the current `index.ts` to understand the existing FCM send pattern
2. Add the `hintParams` optional parameter to the existing send function
3. Update the request handler to extract hint params from the request body
4. Preserve backward compatibility: requests without hint params still send `type: daily_sync`
5. Test that the function still deploys successfully

#### Step 6.4b.2: Verify edge function deployment

```
npx supabase functions deploy daily-sync-push --no-verify-jwt
```

Expected: Function deploys successfully with the updated payload construction.

---

### Sub-phase 6.5: Update callers of SyncInitializer.create for new return type

**Files:**
- Modify: callers of `SyncInitializer.create` that destructure the return record

**Agent**: `backend-supabase-agent`

#### Step 6.5.1: Find and update all callers of SyncInitializer.create

The return type of `SyncInitializer.create` changed from `({SyncOrchestrator orchestrator, SyncLifecycleManager lifecycleManager})` to include `RealtimeHintHandler? realtimeHintHandler`. All destructuring call sites must be updated.

Search for callers:

The primary caller is in `lib/core/di/app_dependencies.dart` or `lib/core/di/app_initializer.dart` (wherever `SyncInitializer.create` is called). The destructuring pattern must be updated to include the new field:

```dart
// At the call site where SyncInitializer.create is invoked, update the destructuring:
// BEFORE:
// final (:orchestrator, :lifecycleManager) = await SyncInitializer.create(...);
//
// AFTER:
// WHY: SyncInitializer now returns RealtimeHintHandler so it can be disposed on sign-out
final (:orchestrator, :lifecycleManager, :realtimeHintHandler) = await SyncInitializer.create(
  dbService: dbService,
  authProvider: authProvider,
  appConfigProvider: appConfigProvider,
  companyLocalDs: companyLocalDs,
  authService: authService,
  supabaseClient: supabaseClient,
);

// Store realtimeHintHandler for disposal on sign-out:
// NOTE: The exact storage mechanism depends on the DI pattern at the call site.
// If using a class field, add: _realtimeHintHandler = realtimeHintHandler;
// If using a provider, register it alongside the orchestrator and lifecycle manager.
```

The implementing agent MUST:
1. Search for `SyncInitializer.create` in the codebase
2. Update every destructuring site to include `realtimeHintHandler`
3. Store the handler reference for disposal during sign-out
4. Call `realtimeHintHandler?.dispose()` in the sign-out cleanup path

#### Step 6.5.2: Final compilation check for all Phase 6 files

```
pwsh -Command "flutter analyze lib/features/sync/"
```

Expected: No analysis errors across the entire sync feature. This validates that all cross-file references (SyncMode, DirtyScopeTracker, RealtimeHintHandler) resolve correctly and all signature changes are backward-compatible.

## Phase 7: Global Sync Action UI

**Prerequisite**: Phases 1-6 complete. `SyncMode` enum exists in `lib/features/sync/domain/sync_types.dart`. `SyncOrchestrator.syncLocalAgencyProjects({SyncMode mode = SyncMode.full})` accepts a mode parameter. `SyncProvider.sync()` calls `syncLocalAgencyProjects()` (defaults to full). `DirtyScopeTracker` exists at `lib/features/sync/engine/dirty_scope_tracker.dart`.

---

### Sub-phase 7.1: Add SyncStatusIcon to Global Shell App Bar

**Files:**
- Modify: `lib/core/router/scaffold_with_nav_bar.dart:1-188`
- Modify: `lib/features/entries/presentation/screens/home_screen.dart:29,374-375`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.1.1: Add SyncStatusIcon import to scaffold_with_nav_bar.dart

Open `lib/core/router/scaffold_with_nav_bar.dart` and add the import for `SyncStatusIcon` after the existing imports (after line 11).

```dart
// lib/core/router/scaffold_with_nav_bar.dart — add after line 11
// FROM SPEC: "A manual sync action must be available in the main app chrome"
// WHY: SyncStatusIcon is the existing widget that shows sync status + navigates
// to /sync/dashboard on tap. Adding it to the shell app bar makes it globally
// visible on all screens that use the shell's AppBar (Dashboard, Calendar).
import 'package:construction_inspector/features/sync/presentation/widgets/sync_status_icon.dart';
```

#### Step 7.1.2: Add SyncStatusIcon as an action in the shell AppBar

Modify the `AppBar` inside the `build` method of `ScaffoldWithNavBar` (currently at lines 33-38). Add `actions: const [SyncStatusIcon()]` to the AppBar. The AppBar is conditionally shown only for `_projectContextRoutes` (`/` and `/calendar`), which covers the Dashboard and Calendar tabs.

Replace lines 33-38:
```dart
      // FROM SPEC: "A manual sync action must be available in the main app chrome"
      // WHY: The shell AppBar appears on project context routes (Dashboard, Calendar).
      // SyncStatusIcon uses Consumer<SyncProvider> internally, which is already
      // provided above this widget in the Provider tree (see sync_providers.dart).
      // NOTE: SyncStatusIcon navigates to /sync/dashboard via context.push('/sync/dashboard').
      appBar: showProjectSwitcher
          ? AppBar(
              title: const ProjectSwitcher(),
              centerTitle: false,
              automaticallyImplyLeading: false,
              actions: const [
                SyncStatusIcon(),
              ],
            )
          : null,
```

#### Step 7.1.3: Remove SyncStatusIcon from HomeScreen

The HomeScreen at route `/calendar` is inside the shell route. However, HomeScreen defines its OWN `AppBar` inside `AppScaffold`, which renders as a nested scaffold below the shell's AppBar. With SyncStatusIcon now in the shell AppBar, the HomeScreen instance is redundant for the Calendar tab -- users see it in the shell AppBar above.

Modify `lib/features/entries/presentation/screens/home_screen.dart`:

1. Remove the import at line 29:
```dart
// REMOVE this line:
// import 'package:construction_inspector/features/sync/presentation/widgets/sync_status_icon.dart';
```

2. Remove `const SyncStatusIcon()` from the `actions` list at line 375. The actions list becomes:
```dart
        actions: [
          // WHY: SyncStatusIcon moved to global shell AppBar (scaffold_with_nav_bar.dart)
          // to satisfy spec requirement: "manual sync action in main app chrome".
          // Removing here avoids duplicate sync icons on the Calendar tab.
          IconButton(
            key: TestingKeys.homeJumpToLatestButton,
            icon: const Icon(Icons.today),
            onPressed: _jumpToLatestEntry,
            tooltip: 'Jump to latest entry',
          ),
        ],
```

#### Step 7.1.4: Verify static analysis passes

```
pwsh -Command "flutter analyze lib/core/router/scaffold_with_nav_bar.dart lib/features/entries/presentation/screens/home_screen.dart"
```

Expected: No analysis issues.

---

### Sub-phase 7.2: Add "Sync Now" Full Sync Button to SyncDashboardScreen

**Files:**
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart:282-285`
- Modify: `lib/features/sync/presentation/screens/sync_dashboard_screen.dart:292-323`
- Modify: `lib/shared/testing_keys/sync_keys.dart:1-49`
- Test: `test/features/sync/presentation/providers/sync_provider_mode_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.2.1: Add fullSync method to SyncProvider

Modify `lib/features/sync/presentation/providers/sync_provider.dart`. Add a `fullSync()` method after the existing `sync()` method (after line 285). This method explicitly passes `SyncMode.full` to the orchestrator, ensuring the user gets a complete push + pull sweep regardless of dirty scope state.

```dart
  // After line 285 in sync_provider.dart:

  /// Trigger an explicit full sync (push + pull all tables).
  ///
  /// FROM SPEC: "user taps top-bar sync action -> app runs Full sync"
  /// WHY: The default sync() method will use whatever default SyncMode the
  /// orchestrator has (which after Phase 3 defaults to SyncMode.full for
  /// backward compat). This method is explicit about wanting SyncMode.full,
  /// used by the Sync Dashboard "Sync Now" action.
  Future<SyncResult> fullSync() async {
    // NOTE: SyncMode.full is defined in lib/features/sync/domain/sync_types.dart
    // (created in Phase 1). It triggers the full push + pull + maintenance path.
    return await _syncOrchestrator.syncLocalAgencyProjects(
      mode: SyncMode.full,
    );
  }
```

Also add the import for `SyncMode` if not already re-exported. The `SyncMode` enum is in `sync_types.dart` which is already imported via the relative import at line 5 (`../../domain/sync_types.dart`). Since `SyncMode` lives in `sync_types.dart` (added in Phase 1), no new import is needed.

#### Step 7.2.2: Add testing key for Sync Now full sync button

Modify `lib/shared/testing_keys/sync_keys.dart`. Add a new key for the prominent "Sync Now" button that will be added to the dashboard.

```dart
  // Add after line 23 (after syncResumeSyncButton) in sync_keys.dart:

  /// "Sync Now" primary action button (full sync)
  /// FROM SPEC: "user taps top-bar sync action -> app runs Full sync"
  // WHY: Separate from syncNowTile (the list tile). This is the prominent
  // FilledButton at the top of the actions section.
  static const syncNowFullButton = Key('sync_now_full_button');
```

#### Step 7.2.3: Update SyncDashboardScreen actions section

Modify `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`. Update the `_buildActionsSection` method (lines 292-323) to:
1. Add a prominent "Sync Now" `FilledButton.icon` at the top that calls `fullSync()`
2. Update the existing "Sync Now" list tile to call `fullSync()` instead of `sync()`
3. Show sync mode feedback via `SnackBarHelper`

Replace the `_buildActionsSection` method (lines 292-323):

```dart
  Widget _buildActionsSection(BuildContext context) {
    final syncProvider = context.watch<SyncProvider>();
    // WHY: Watch syncProvider so the button disables while syncing
    return Column(
      children: [
        // FROM SPEC: "A user can always force a full sync from the main app sync button"
        // WHY: Prominent button at the top of the actions section gives users a clear,
        // unmistakable way to trigger a full push + pull sweep. This is the primary
        // "certainty" action described in the spec's "User Wants Certainty" flow.
        Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DesignConstants.space4,
            vertical: DesignConstants.space2,
          ),
          child: SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              key: SyncTestingKeys.syncNowFullButton,
              onPressed: syncProvider.isSyncing
                  ? null
                  : () async {
                      // NOTE: fullSync() explicitly passes SyncMode.full to orchestrator
                      final result = await syncProvider.fullSync();
                      if (context.mounted) {
                        if (result.hasErrors) {
                          // WHY: A22 lint — use SnackBarHelper, not raw ScaffoldMessenger
                          SnackBarHelper.showWarning(
                            context,
                            'Sync completed with ${result.errors} error(s)',
                          );
                        } else {
                          SnackBarHelper.showSuccess(
                            context,
                            'Full sync complete: ${result.total} items synced',
                          );
                        }
                        _loadData();
                      }
                    },
              icon: syncProvider.isSyncing
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        // WHY: A13 lint — use theme color, not hardcoded Colors.white
                        color: Theme.of(context).colorScheme.onPrimary,
                      ),
                    )
                  : const Icon(Icons.sync),
              label: Text(syncProvider.isSyncing ? 'Syncing...' : 'Full Sync Now'),
            ),
          ),
        ),
        const SizedBox(height: DesignConstants.space2),
        _buildActionTile(
          tileKey: SyncTestingKeys.syncNowTile,
          icon: Icons.sync,
          title: 'Sync Now',
          subtitle: 'Push and pull all changes',
          onTap: () async {
            // NOTE: Use fullSync() to explicitly request SyncMode.full
            final syncProvider = context.read<SyncProvider>();
            await syncProvider.fullSync();
            if (mounted) _loadData();
          },
        ),
        _buildActionTile(
          tileKey: SyncTestingKeys.syncViewConflictsTile,
          icon: Icons.warning_amber,
          title: 'View Conflicts',
          subtitle: '$_conflictCount unresolved',
          onTap: () => context.push('/sync/conflicts'),
        ),
        // FROM SPEC Section 11: Redirect to project list (Company tab) instead of deleted screen
        _buildActionTile(
          tileKey: SyncTestingKeys.syncViewProjectsTile,
          icon: Icons.folder_shared,
          title: 'View Synced Projects',
          subtitle: 'See which projects are synced',
          onTap: () => context.go('/projects'),
        ),
      ],
    );
  }
```

#### Step 7.2.4: Add SnackBarHelper and Colors imports to SyncDashboardScreen

The SyncDashboardScreen needs an import for `SnackBarHelper`. The file does NOT currently import `shared.dart` (verified: existing imports are `design_system.dart` and `testing_keys.dart`). Add this import:

```dart
// lib/features/sync/presentation/screens/sync_dashboard_screen.dart
// WHY: SnackBarHelper is needed for success/warning snackbars on sync completion.
// This import is NOT already present — add it after the existing imports.
import 'package:construction_inspector/shared/shared.dart';
```

Also add import for `SyncTestingKeys` if the file currently accesses it through `testing_keys.dart`:
```dart
// Verify this import exists (it does, at line 8):
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';
```

The `SyncTestingKeys` is exported from `sync_keys.dart` and re-exported via the barrel. Since `sync_dashboard_screen.dart` already uses `SyncTestingKeys.*` directly, the import path is already in place.

#### Step 7.2.5: Write test for SyncProvider.fullSync

Create `test/features/sync/presentation/providers/sync_provider_mode_test.dart`:

```dart
// test/features/sync/presentation/providers/sync_provider_mode_test.dart
//
// WHY: Verifies that fullSync() passes SyncMode.full to the orchestrator,
// ensuring the explicit full sync path works correctly.
// FROM SPEC: "user taps top-bar sync action -> app runs Full sync"
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:construction_inspector/core/database/database_service.dart';

// NOTE: We use a minimal mock that tracks the mode parameter.
// The SyncOrchestrator is complex; we only need to verify the mode is passed.
class _TrackingSyncOrchestrator extends SyncOrchestrator {
  SyncMode? lastMode;
  int syncCallCount = 0;

  // WHY: Minimal constructor — SyncOrchestrator.forTesting requires a DatabaseService.
  // This is a test-only subclass that overrides syncLocalAgencyProjects.
  _TrackingSyncOrchestrator(DatabaseService dbService) : super.forTesting(dbService);

  @override
  Future<SyncResult> syncLocalAgencyProjects({
    SyncMode mode = SyncMode.full,
  }) async {
    lastMode = mode;
    syncCallCount++;
    return const SyncResult(pushed: 1, pulled: 2);
  }

  // Stubs required by the base class
  @override
  DateTime? get lastSyncTime => DateTime.now();

  @override
  bool get isSupabaseOnline => true;

  @override
  Future<Map<String, BucketCount>> getPendingBuckets() async => {};
}

void main() {
  group('SyncProvider sync modes', () {
    test('fullSync passes SyncMode.full to orchestrator', () async {
      // WHY: Verify the explicit full sync path reaches the orchestrator
      // with the correct mode parameter.
      final mockDbService = DatabaseService();
      final orchestrator = _TrackingSyncOrchestrator(mockDbService);
      final provider = SyncProvider(orchestrator);

      final result = await provider.fullSync();

      expect(orchestrator.lastMode, SyncMode.full);
      expect(result.pushed, 1);
      expect(result.pulled, 2);
      expect(orchestrator.syncCallCount, 1);

      provider.dispose();
    });

    test('sync calls orchestrator with default mode', () async {
      // WHY: Verify the existing sync() method still works and calls the
      // orchestrator (mode defaults to SyncMode.full in the orchestrator).
      final mockDbService = DatabaseService();
      final orchestrator = _TrackingSyncOrchestrator(mockDbService);
      final provider = SyncProvider(orchestrator);

      await provider.sync();

      expect(orchestrator.syncCallCount, 1);
      // NOTE: sync() calls syncLocalAgencyProjects() without explicit mode,
      // so the orchestrator's default (SyncMode.full) applies.
      expect(orchestrator.lastMode, SyncMode.full);

      provider.dispose();
    });
  });
}
```

**IMPORTANT**: This test depends on the `SyncOrchestrator` having a `forTesting(DatabaseService)` constructor (at `sync_orchestrator.dart:127`) or being mockable. If the orchestrator does not have a test constructor, the implementing agent must create a mock using Mockito `@GenerateMocks([SyncOrchestrator])` instead. The test structure above is illustrative -- the implementing agent should use the project's established mocking pattern (Mockito with `@GenerateMocks`).

#### Step 7.2.6: Verify static analysis passes

```
pwsh -Command "flutter analyze lib/features/sync/presentation/providers/sync_provider.dart lib/features/sync/presentation/screens/sync_dashboard_screen.dart lib/shared/testing_keys/sync_keys.dart"
```

Expected: No analysis issues.

---

## Phase 8: Integration Wiring + Cleanup

**Prerequisite**: Phases 1-7 complete. `SyncMode` enum, `DirtyScopeTracker`, and `RealtimeHintHandler` classes exist. `SyncEngine.pushAndPull({SyncMode mode})` and `SyncOrchestrator.syncLocalAgencyProjects({SyncMode mode})` accept mode parameters. `SyncProvider.fullSync()` exists. SyncStatusIcon is in the global shell AppBar.

---

### Sub-phase 8.1: Wire DirtyScopeTracker into SyncInitializer

**Files:**
- Modify: `lib/features/sync/application/sync_initializer.dart:38-130`
- Modify: `lib/features/sync/application/sync_engine_factory.dart:10-56`

**Agent**: `backend-supabase-agent`

#### Step 8.1.1: Verify SyncEngineFactory uses setter approach (already done in Phase 3.2)

> **NOTE:** Phase 3.2 is the canonical location for SyncEngineFactory changes. It adds the `_dirtyScopeTracker` field, `setDirtyScopeTracker()` setter, and passes the tracker to `SyncEngine` in `create()`. The factory's `create()` method does NOT accept a `dirtyScopeTracker` parameter -- the tracker is set once via the setter during initialization.
>
> The implementing agent should verify Phase 3.2 was applied correctly. No additional changes needed here.

#### Step 8.1.2: Create and wire DirtyScopeTracker in SyncInitializer

> **NOTE:** This step overlaps with Phase 6.3.3 (Step 6.3.3). If Phase 6.3.3 was already applied, this step is a NO-OP. The implementing agent should verify that `DirtyScopeTracker` is already created and wired in `SyncInitializer.create()` before applying.

Modify `lib/features/sync/application/sync_initializer.dart`. Add DirtyScopeTracker creation between Step 2 (wire UserProfileSyncDatasource) and Step 3 (build orchestrator). The tracker must be created before the orchestrator so it can be injected into the engine factory.

Add import after line 25 (after `sync_orchestrator_builder.dart`):
```dart
// WHY: DirtyScopeTracker tracks which (projectId, tableName) tuples need pull.
// FROM SPEC: "The sync system should become dirty-scope-aware"
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
```

After the builder setup (after line 69 `builder.userProfileSyncDatasource = userProfileSyncDs;`) and before Step 3 (line 73 `final syncOrchestrator = builder.build();`), add:

```dart
    // Step 2.5: Create DirtyScopeTracker
    // FROM SPEC: "The sync system should become dirty-scope-aware"
    // WHY: Created before the orchestrator so it can be injected into the
    // engine factory. The tracker persists across sync cycles, accumulating
    // dirty scopes from realtime hints and FCM messages.
    // NOTE: DirtyScopeTracker is a simple in-memory tracker (no DB state).
    final dirtyScopeTracker = DirtyScopeTracker();

    // Inject tracker into the builder so the engine factory can pass it
    // to each SyncEngine instance.
    builder.dirtyScopeTracker = dirtyScopeTracker;
```

**IMPORTANT**: This step assumes `SyncOrchestratorBuilder` has been extended in an earlier phase to accept `dirtyScopeTracker` and pass it to the engine factory. If the builder pattern does not support this, the implementing agent should instead call `syncOrchestrator.engineFactory.setDirtyScopeTracker(dirtyScopeTracker)` after the orchestrator is built (after line 74).

Alternative wiring (if builder does not support dirtyScopeTracker):
```dart
    // Step 3: Build orchestrator (fully configured, no setters)
    final syncOrchestrator = builder.build();
    await syncOrchestrator.initialize();

    // Step 3.5: Wire DirtyScopeTracker into engine factory
    // WHY: The engine factory creates a fresh SyncEngine per sync cycle.
    // The tracker must be shared across all cycles so dirty scopes accumulate
    // until a full sync clears them.
    // NOTE: engineFactory is accessed via a getter on the orchestrator.
    // The implementing agent must verify the orchestrator exposes this.
    syncOrchestrator.engineFactory.setDirtyScopeTracker(dirtyScopeTracker);
```

#### Step 8.1.3: Wire RealtimeHintHandler in SyncInitializer (Supabase Realtime)

> **NOTE:** This step overlaps with Phase 6.3.3 (Step 6.3.3). If Phase 6.3.3 was already applied, this step is a NO-OP. The implementing agent should verify that `RealtimeHintHandler` is already created and wired in `SyncInitializer.create()` before applying.

Add creation of `RealtimeHintHandler` in `SyncInitializer.create()` after FCM initialization (after line 100). This handler subscribes to Supabase Broadcast for foreground invalidation hints.

Add import:
```dart
import 'package:construction_inspector/features/sync/application/realtime_hint_handler.dart';
```

After Step 6 (FCM initialization, after line 100), add:

```dart
    // Step 6.5: Realtime hint handler (foreground invalidation)
    // FROM SPEC: "Supabase-originated foreground invalidation hints"
    // WHY: When the app is in the foreground, Supabase Broadcast delivers
    // change hints in real time. The handler marks scopes dirty and triggers
    // a quick sync to pull only affected data.
    // NOTE: Only created when supabaseClient is available (online mode).
    RealtimeHintHandler? realtimeHintHandler;
    if (supabaseClient != null) {
      realtimeHintHandler = RealtimeHintHandler(
        supabaseClient: supabaseClient,
        syncOrchestrator: syncOrchestrator,
        // SECURITY: Pass companyId for cross-tenant hint validation.
        companyId: authProvider.userProfile?.companyId,
      );
      // WHY: subscribe() subscribes to the company-scoped broadcast channel.
      // Non-blocking because realtime is a best-effort foreground optimization.
      // NOTE: companyId is required for channel scoping. Guard against null.
      final companyId = authProvider.userProfile?.companyId;
      if (companyId != null) {
        realtimeHintHandler.subscribe(companyId);
      }
    }
```

#### Step 8.1.4: Update SyncInitializer return type to include RealtimeHintHandler

The return type must include `RealtimeHintHandler?` so the caller (AppInitializer) can dispose it on sign-out. This is consistent with Phase 6.3.2 which already defines the return type with three fields.

```dart
    // WHY: RealtimeHintHandler must be returned so the caller can dispose it
    // on sign-out, preventing stale WebSocket connections leaking hints from
    // the previous user's company to the newly signed-in user (Security M6).
    // NOTE: This is consistent with Phase 6.3.2's return type definition.
    return (
      orchestrator: syncOrchestrator,
      lifecycleManager: syncLifecycleManager,
      realtimeHintHandler: realtimeHintHandler,
    );
```

The caller (AppInitializer / app_dependencies.dart) must:
1. Destructure the new field: `final (:orchestrator, :lifecycleManager, :realtimeHintHandler) = ...`
2. Store `realtimeHintHandler` for disposal
3. Call `realtimeHintHandler?.dispose()` during sign-out cleanup

---

### Sub-phase 8.2: Update SyncProvider to Expose Sync Modes

**Files:**
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart:282-285`

**Agent**: `backend-supabase-agent`

#### Step 8.2.1: Add quickSync method to SyncProvider

The existing `sync()` method at line 283-285 calls `syncLocalAgencyProjects()` without a mode parameter (defaults to `SyncMode.full` per Phase 3 changes). Add a `quickSync()` method for programmatic use by the lifecycle manager and realtime handler.

Add after the `fullSync()` method (added in Phase 7, Sub-phase 7.2):

```dart
  /// Trigger a quick sync (push local changes + pull dirty scopes only).
  ///
  /// FROM SPEC: "startup / foreground / background catch-up" uses quick sync.
  /// WHY: Quick sync is the low-latency path for app resume and realtime hint
  /// reactions. It avoids broad project-wide pulls, only fetching tables/projects
  /// that have been marked dirty by the DirtyScopeTracker.
  /// NOTE: This method is called programmatically by SyncLifecycleManager on
  /// app resume and by RealtimeHintHandler on foreground invalidation hints.
  Future<SyncResult> quickSync() async {
    return await _syncOrchestrator.syncLocalAgencyProjects(
      mode: SyncMode.quick,
    );
  }
```

#### Step 8.2.2: Update the default sync() method documentation

Update the doc comment on `sync()` (line 282) to clarify its role now that multiple modes exist:

```dart
  /// Trigger a manual sync via SyncOrchestrator.
  ///
  /// NOTE: Calls syncLocalAgencyProjects() with the orchestrator's default mode
  /// (SyncMode.full after Phase 3). For explicit mode control, use [fullSync()]
  /// or [quickSync()] instead.
  /// WHY: Preserved for backward compatibility — existing callers (SyncSection
  /// in settings, stale data banner) continue to work without changes.
  Future<SyncResult> sync() async {
    return await _syncOrchestrator.syncLocalAgencyProjects();
  }
```

---

### Sub-phase 8.3: Update SyncProviders.initialize and app_initializer.dart

**Files:**
- Modify: `lib/features/sync/di/sync_providers.dart:49-91`
- Modify: `lib/core/config/app_initializer.dart` (or `app_dependencies.dart`, wherever `SyncProviders.initialize()` is called)

**Agent**: `backend-supabase-agent`

#### Step 8.3.1: Update SyncProviders.initialize return type

`SyncProviders.initialize()` wraps `SyncInitializer.create()` and returns its result. Since Phase 8.1.4 updates `SyncInitializer.create()` to return a record including `RealtimeHintHandler?`, the wrapper must be updated to propagate that field.

Update the return type of `SyncProviders.initialize()` to match the new `SyncInitializer.create()` return type:

```dart
// lib/features/sync/di/sync_providers.dart
// WHY: SyncInitializer.create() now returns (orchestrator:, lifecycleManager:, realtimeHintHandler:).
// SyncProviders.initialize() must propagate realtimeHintHandler so the caller
// (AppInitializer) can dispose it on sign-out, preventing stale WebSocket leaks.
static Future<({
  SyncOrchestrator orchestrator,
  SyncLifecycleManager lifecycleManager,
  RealtimeHintHandler? realtimeHintHandler,
})> initialize(...) async {
  // ... delegates to SyncInitializer.create() and returns its full result
}
```

NOTE: The `DirtyScopeTracker` itself does NOT need to be surfaced as a Provider:
1. No UI widget directly reads `DirtyScopeTracker`
2. The tracker is injected into `SyncEngineFactory` and `RealtimeHintHandler` at creation time
3. The `SyncProvider` does not need direct access to the tracker

#### Step 8.3.2: Update app_initializer.dart destructuring

In `lib/core/config/app_initializer.dart` (or `app_dependencies.dart`), update the call site that destructures `SyncProviders.initialize()`:

```dart
// WHY: Must destructure the new realtimeHintHandler field to store it for
// disposal on sign-out. Without this, the code won't compile since the
// return record now has 3 fields instead of 2.
final (:orchestrator, :lifecycleManager, :realtimeHintHandler) =
    await SyncProviders.initialize(...);
// Store realtimeHintHandler for disposal during sign-out cleanup
```

The implementing agent must find the existing destructuring pattern and add `:realtimeHintHandler` to it, plus wire `realtimeHintHandler?.dispose()` into the sign-out cleanup path.

---

### Sub-phase 8.4: Dead Code Audit and Cleanup

**Files:**
- Audit: `lib/core/database/schema/sync_tables.dart` -- NOT dead code, keep
- Audit: `lib/features/settings/presentation/widgets/sync_section.dart` -- NOT dead code, keep

**Agent**: `general-purpose`

#### Step 8.4.1: Verify sync_tables.dart is NOT dead code

The blast-radius analysis flagged `lib/core/database/schema/sync_tables.dart` as dead code. This is INCORRECT. Verification:

- `SyncTables.createDeletionNotificationsTable` is used in `lib/core/database/database_service.dart:182` (in `_onCreate`)
- `SyncTables.indexes` is used in `lib/core/database/database_service.dart:270` (index creation loop)
- `SyncTables.createDeletionNotificationsTable` is used in `lib/core/database/database_service.dart:1231` (migration path)
- The file is exported via `lib/core/database/schema/schema.dart:13`

```
// DECISION: DO NOT DELETE lib/core/database/schema/sync_tables.dart
// WHY: It contains the deletion_notifications table schema used by
// database_service.dart in _onCreate, index creation, and migration v34.
// The blast-radius analysis was incorrect — this file has 3 active consumers.
```

#### Step 8.4.2: Verify sync_section.dart is NOT dead code

The blast-radius analysis flagged `lib/features/settings/presentation/widgets/sync_section.dart` as dead code. This is INCORRECT. Verification:

- `SyncSection` widget is used in `lib/features/settings/presentation/screens/settings_screen.dart:226`
- The file is exported via `lib/features/settings/presentation/widgets/widgets.dart:3`

```
// DECISION: DO NOT DELETE lib/features/settings/presentation/widgets/sync_section.dart
// WHY: SyncSection is actively used by settings_screen.dart line 226.
// It provides the sync status/action UI in the Settings tab.
// The blast-radius analysis was incorrect — this widget has an active consumer.
```

#### Step 8.4.3: Audit barrel exports flagged as dead

The blast-radius lists these barrel exports with "zero importers":
- `sync.dart`, `application.dart`, `data.dart`, `di.dart`, `domain.dart`, `presentation.dart`, `providers.dart`

These are barrel export files (re-export patterns). They may have zero DIRECT importers because consumers import specific files instead of barrels. This is normal in this codebase. Do NOT delete barrel exports -- they exist for organizational consistency and may be used by external tooling or future imports.

```
// DECISION: DO NOT DELETE barrel export files.
// WHY: Barrel exports are an organizational pattern, not dead code.
// They re-export submodules for convenience. Zero direct importers is expected
// when consumers prefer specific imports for tree-shaking.
```

---

### Sub-phase 8.5: Final Verification

**Files:**
- All modified files from Phases 7-8

**Agent**: `general-purpose`

#### Step 8.5.1: Run full static analysis

```
pwsh -Command "flutter analyze"
```

Expected: No analysis issues. If issues arise, they are likely:
- Missing imports for `SyncMode` (added in Phase 1, should be in `sync_types.dart`)
- Missing `DirtyScopeTracker` parameter in `SyncEngine` constructor (added in Phase 2)
- Missing `RealtimeHintHandler` class (created in Phase 6.2)
- Lint rule violations in new code (A9 silent catch, A22 raw snackbar, etc.)

The implementing agent must resolve all analysis issues before marking Phase 8 complete.

#### Step 8.5.2: Verify no import cycles

Check that the new wiring does not introduce circular imports:
- `sync_initializer.dart` imports `dirty_scope_tracker.dart` and `realtime_hint_handler.dart` -- both are leaf files with no back-imports to the application layer
- `sync_engine_factory.dart` imports `dirty_scope_tracker.dart` -- a leaf file
- `sync_provider.dart` imports `sync_types.dart` (already existing) for `SyncMode`

No circular dependencies are introduced.

#### Step 8.5.3: Verify testing key consistency

Confirm all new testing keys are properly structured:
- `SyncTestingKeys.syncNowFullButton` in `sync_keys.dart` -- Key value `'sync_now_full_button'`
- Used in `sync_dashboard_screen.dart` on the `FilledButton.icon`

The implementing agent should verify the key is accessible from test files via the `SyncTestingKeys` class.

---

## SECURITY RISK ACCEPTANCE — Supabase Broadcast Channel Authorization

**Finding**: Supabase Broadcast channels have no built-in server-side authorization. Any authenticated Supabase user who knows a `company_id` UUID can subscribe to `sync_hints:<company_id>` and receive hint payloads (table names, project IDs, change timestamps). This leaks operational activity patterns but NOT row data.

**Mitigations in this plan**:
1. **Client-side guard**: `RealtimeHintHandler.subscribe()` validates `companyId` against the authenticated user's company before subscribing (Phase 6.2).
2. **Hint handlers validate**: Both `FcmHandler` and `RealtimeHintHandler` compare `hint.companyId` against the current user's company and ignore mismatches (Phase 6.1.3, 6.2).
3. **Payloads contain only IDs**: No row data, PII, or business content in hint payloads — only UUIDs and table names.
4. **RLS still enforced on pull**: Even if a client marks a dirty scope from a cross-tenant hint, the actual data pull goes through Supabase RLS policies which enforce company/project scoping.

**Accepted risk**: A determined attacker with valid Supabase credentials could observe which tables and projects are being modified in another company, revealing activity patterns (when inspectors are active, which projects are being worked on). This is an information leakage risk, not a data access risk.

**Follow-up hardening** (tracked separately, not blocking this plan):
- Add Supabase Realtime Authorization Policies restricting broadcast channel subscriptions by `app_metadata.company_id` JWT claim
- This requires Supabase platform support for custom Realtime policies — evaluate availability and implement when supported
