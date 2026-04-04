# Pattern: Sync Lifecycle Manager (App State → Sync Trigger)

## How We Do It
SyncLifecycleManager mixes in `WidgetsBindingObserver` and routes app lifecycle events (resumed, paused, detached) to sync triggers. On resume, it checks staleness against a 24-hour threshold and triggers a DNS-aware full sync if data is stale. On pause/detach, it debounces a push-only sync. All code paths eventually call `syncOrchestrator.syncLocalAgencyProjects()` — the same full sync as manual triggers.

## Exemplars

### SyncLifecycleManager._handleResumed (sync_lifecycle_manager.dart:74-103)
```dart
Future<void> _handleResumed() async {
    _debounceTimer?.cancel();
    await onAppResumed?.call(); // SEC-103: security checks first
    if (!(isReadyForSync?.call() ?? false)) return;

    final lastSync = _syncOrchestrator.lastSyncTime;
    if (lastSync == null) {
      _triggerDnsAwareSync(forced: true); // Never synced
      return;
    }

    final timeSinceSync = DateTime.now().difference(lastSync);
    if (timeSinceSync > _staleThreshold) {
      _triggerDnsAwareSync(forced: true); // Data stale
    } else {
      onStaleDataWarning?.call(false);
    }
  }
```

### SyncLifecycleManager (full class structure, sync_lifecycle_manager.dart:14-155)
Key fields:
- `_staleThreshold` = 24 hours (hardcoded)
- `_debounceTimer` for pause/detach
- Callbacks: `isReadyForSync`, `onAppResumed`, `onStaleDataWarning`, `onForcedSyncInProgress`

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `didChangeAppLifecycleState` | `sync_lifecycle_manager.dart:37` | `void didChangeAppLifecycleState(AppLifecycleState state)` | Lifecycle router |
| `_handleResumed` | `sync_lifecycle_manager.dart:74` | `Future<void> _handleResumed()` | Foreground resume |
| `_handlePaused` | `sync_lifecycle_manager.dart:54` | `void _handlePaused()` | Background transition |
| `_triggerDnsAwareSync` | `sync_lifecycle_manager.dart:109` | `Future<void> _triggerDnsAwareSync({required bool forced})` | DNS check + sync |
| `_triggerSync` | `sync_lifecycle_manager.dart:126` | `Future<void> _triggerSync()` | Calls syncLocalAgencyProjects |
| `_triggerForcedSync` | `sync_lifecycle_manager.dart:134` | `Future<void> _triggerForcedSync()` | Forced sync with UI state |

## Imports
```dart
import 'package:construction_inspector/core/logging/logger.dart';
```

## Gap Analysis for Spec

**Resume = full sync**: Currently `_handleResumed()` triggers full `syncLocalAgencyProjects()` whenever stale. The spec wants quick sync on resume (push local + pull dirty scopes only).

**No quick path**: Both `_triggerSync()` and `_triggerForcedSync()` call the same method. Spec wants them to be `quickSync()` (resume) vs `fullSync()` (forced).

**Stale threshold is fixed**: 24 hours hardcoded. Spec doesn't change this, but configurable threshold in SyncEngineConfig would be cleaner.
