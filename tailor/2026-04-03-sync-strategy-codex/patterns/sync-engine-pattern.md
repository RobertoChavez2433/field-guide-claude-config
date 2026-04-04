# Pattern: Sync Engine (Core Push/Pull)

## How We Do It
SyncEngine is a stateful class created fresh per sync cycle by SyncEngineFactory. It takes a Database, SupabaseClient, companyId, and userId. The single `pushAndPull()` method acquires a mutex, runs `_push()` (change_log → FK order → per-record upsert), then `_pull()` (all adapters → cursor-based paginated fetch), then maintenance (prune, integrity check, orphan scan). There is currently NO mode differentiation — every sync runs the full pipeline.

## Exemplars

### SyncEngine.pushAndPull (sync_engine.dart:216-360)
```dart
Future<SyncEngineResult> pushAndPull() async {
    _rlsDenialCount = 0;
    _pullConflictCount = 0;
    _pullSkippedFkCount = 0;
    _skippedPushCount = 0;

    // Crash recovery for pulling=1 stuck state
    try {
      await db.execute(
        "UPDATE sync_control SET value = '0' WHERE key = 'pulling'",
      );
    } catch (e) {
      Logger.sync('[SyncEngine] crash recovery reset: $e');
    }

    if (!await _mutex.tryAcquire(lockedBy)) {
      return const SyncEngineResult(lockFailed: true);
    }
    _postSyncStatus({'type': 'sync_state', 'state': 'started'});

    _insidePushOrPull = true;
    final stopwatch = Stopwatch()..start();
    final heartbeatTimer = Timer.periodic(
      const Duration(seconds: 60), (_) => _mutex.heartbeat(),
    );
    var combined = const SyncEngineResult();
    try {
      final pushResult = await _push();
      await _storageCleanup.cleanupExpiredFiles();
      final pullResult = await _pull();
      await _changeTracker.pruneProcessed();
      await _conflictResolver.pruneExpired();
      // Integrity check on 4-hour schedule...
      combined = pushResult + pullResult;
    } finally {
      heartbeatTimer.cancel();
      _insidePushOrPull = false;
      await _mutex.release();
    }
    return combined;
  }
```

### SyncEngine Constructor (sync_engine.dart:153-160)
```dart
SyncEngine({
    required this.db,
    required this.supabase,
    required this.companyId,
    required this.userId,
    this.lockedBy = 'foreground',
    this.onProgress,
  })
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `pushAndPull` | `sync_engine.dart:216` | `Future<SyncEngineResult> pushAndPull()` | Full sync cycle (current only mode) |
| `_push` | `sync_engine.dart:421` | `Future<SyncEngineResult> _push()` | Push local changes via change_log |
| `_pull` | `sync_engine.dart:1452` | `Future<SyncEngineResult> _pull()` | Pull all adapters cursor-based |
| `pullOnly` | `sync_engine.dart:406` | `Future<SyncEngineResult> pullOnly()` | Pull-only (testing) |
| `resetState` | `sync_engine.dart:204` | `Future<void> resetState()` | Crash recovery reset |

## Imports
```dart
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
```

## Gap Analysis for Spec

The spec requires three modes (quick, full, maintenance). Currently:
- `pushAndPull()` is monolithic — push + pull + prune + integrity + orphan scan
- `_pull()` iterates ALL adapters unconditionally
- No concept of "pull only dirty scopes"
- `pullOnly()` exists but is test-only and still pulls everything

**Extension points**: Add a `SyncMode` enum parameter to `pushAndPull()` that controls which sub-phases run. Quick mode = push only (or push + dirty-scope pull). Full mode = current behavior. Maintenance mode = integrity + orphan scan only.
