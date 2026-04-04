# Pattern: Sync Orchestrator (Application Layer Routing)

## How We Do It
SyncOrchestrator wraps SyncEngine with retry logic, status management, and auth context resolution. It provides a single public method `syncLocalAgencyProjects()` that ALL trigger sources call. The orchestrator creates a fresh SyncEngine per cycle via `SyncEngineFactory.create()`, delegates to `engine.pushAndPull()`, and handles transient error retries with exponential backoff. It also manages post-sync actions (company member pull, last_synced_at update).

## Exemplars

### SyncOrchestrator.syncLocalAgencyProjects (sync_orchestrator.dart:241-318)
```dart
Future<SyncResult> syncLocalAgencyProjects() async {
    _backgroundRetryTimer?.cancel();
    final earlyCtx = _syncContextProvider();
    if (earlyCtx.companyId == null) {
      return const SyncResult();
    }
    Analytics.trackManualSync();
    _updateStatus(SyncAdapterStatus.syncing);
    _isSyncing = true;
    try {
      final result = await _syncWithRetry();
      _updateStatus(result.hasErrors ? SyncAdapterStatus.error : SyncAdapterStatus.success);
      onSyncComplete?.call(result);
      if (!result.hasErrors) {
        _lastSyncTime = DateTime.now();
        // Persist last_sync_time, pull company members, update last_synced_at...
      }
      return result;
    } finally {
      _isSyncing = false;
    }
  }
```

### SyncOrchestrator._doSync (sync_orchestrator.dart:413-448)
```dart
Future<SyncResult> _doSync() async {
    final engine = await _createEngine();
    if (engine == null) {
      return const SyncResult(errors: 1, errorMessages: ['No auth context']);
    }
    try {
      engine.onPullComplete = onPullComplete;
      engine.onCircuitBreakerTrip = onCircuitBreakerTrip;
      final engineResult = await engine.pushAndPull();
      return SyncResult(
        pushed: engineResult.pushed,
        pulled: engineResult.pulled,
        errors: engineResult.errors,
        // ...
      );
    } catch (e, stack) {
      return SyncResult(errors: 1, errorMessages: ['SyncEngine error: $e']);
    }
  }
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `syncLocalAgencyProjects` | `sync_orchestrator.dart:241` | `Future<SyncResult> syncLocalAgencyProjects()` | ALL sync triggers |
| `_doSync` | `sync_orchestrator.dart:413` | `Future<SyncResult> _doSync()` | Single sync cycle |
| `_syncWithRetry` | `sync_orchestrator.dart:325` | `Future<SyncResult> _syncWithRetry()` | Retry wrapper with backoff |
| `initialize` | `sync_orchestrator.dart:149` | `Future<void> initialize()` | Register adapters, load last sync time |
| `checkDnsReachability` | `sync_orchestrator.dart:524` | `Future<bool> checkDnsReachability()` | Pre-sync DNS check |
| `getPendingBuckets` | `sync_orchestrator.dart:550` | `Future<Map<String, BucketCount>> getPendingBuckets()` | UI pending count display |
| `getPendingCount` | `sync_orchestrator.dart:610` | `Future<int> getPendingCount()` | Total pending changes |

## Imports
```dart
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/core/analytics/analytics.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/features/sync/engine/sync_engine.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';
```

## Gap Analysis for Spec

**Single entry point problem**: `syncLocalAgencyProjects()` is the ONLY way to sync. All callers get the same full push+pull cycle. The spec wants `syncLocalAgencyProjects(mode: SyncMode.quick)` or separate methods like `quickSync()` and `fullSync()`.

**Extension point**: Add a `SyncMode` parameter to `syncLocalAgencyProjects()` (defaulting to full for backward compat), and pass it through `_doSync()` to `engine.pushAndPull(mode)`.
