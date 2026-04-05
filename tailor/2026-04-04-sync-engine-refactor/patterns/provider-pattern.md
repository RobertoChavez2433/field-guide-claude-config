# Pattern: Sync Provider (Presentation Layer)

## How We Do It

SyncProvider extends `ChangeNotifier` and acts as the bridge between the sync system and the UI. It subscribes to `SyncOrchestrator.onSyncComplete` for result callbacks, maintains independent status tracking (the third source of truth), and exposes properties for the dashboard/indicator widgets. The refactor removes the raw orchestrator exposure and independent status tracking, replacing them with a SyncStatus stream subscription.

## Exemplar: SyncProvider

### Fields and Status Tracking (sync_provider.dart:18-49)

```dart
class SyncProvider extends ChangeNotifier {
  final SyncOrchestrator _syncOrchestrator;

  SyncOrchestrator get orchestrator => _syncOrchestrator;  // LAYER VIOLATION

  SyncAdapterStatus _status = SyncAdapterStatus.idle;      // TRIPLE STATUS #3
  DateTime? _lastSyncTime;                                   // TRIPLE STATUS #3
  int _pendingCount = 0;
  Map<String, BucketCount> _pendingBuckets = {};
  String? _lastError;
  bool _isSyncing = false;                                   // TRIPLE STATUS #3
  bool _isStaleDataWarning = false;
  bool _isForcedSyncInProgress = false;
  int _consecutiveFailures = 0;
  bool _circuitBreakerTripped = false;
  bool _syncErrorSnackbarVisible = false;
  DateTime? _circuitBreakerDismissedAt;

  final List<({String tableName, String recordId, int conflictCount})>
      _circuitBreakerTrips = [];
  final List<String> _pendingNotifications = [];

  SyncErrorToastCallback? onSyncErrorToast;
  VoidCallback? onSyncCycleComplete;
```

### _sanitizeSyncError — Postgres Codes in Provider (sync_provider.dart:328-348)

```dart
String _sanitizeSyncError(String raw) {
  const pgPatterns = [
    '42501', '23505', '23503',
    'permission denied', 'violates row-level security',
  ];
  final lower = raw.toLowerCase();
  if (pgPatterns.any(lower.contains)) {
    return 'Sync error — some records could not be saved. Try again or contact support.';
  }
  final sanitized = raw;
  if (sanitized.length > 120 || sanitized.contains('{') || sanitized.contains('\n')) {
    return 'Sync failed. Check sync dashboard for details.';
  }
  return sanitized;
}
```

**This is the third error classification site** — duplicates logic from SyncEngine._handlePushError and SyncOrchestrator._isTransientError.

### Sync Entry Points (sync_provider.dart:285-300)

```dart
Future<SyncResult> sync() async => fullSync();

Future<SyncResult> fullSync() async {
  return _syncOrchestrator.syncLocalAgencyProjects(
    mode: SyncMode.full, recordManualTrigger: true,
  );
}

Future<SyncResult> quickSync() async {
  return _syncOrchestrator.syncLocalAgencyProjects(mode: SyncMode.quick);
}
```

### Status Getters (sync_provider.dart:193-233)

```dart
SyncAdapterStatus get status => _status;
bool get isSyncing => _isSyncing;
bool get isOnline => _syncOrchestrator.isSupabaseOnline;
DateTime? get lastSyncTime => _lastSyncTime ?? _syncOrchestrator.lastSyncTime;
int get pendingCount => _pendingCount;
bool get hasPendingChanges => _pendingCount > 0;
Map<String, BucketCount> get pendingBuckets => _pendingBuckets;
int get totalPendingCount => _pendingBuckets.values.fold(0, (sum, b) => sum + b.total);
String? get lastError => _lastError;
int get consecutiveFailures => _consecutiveFailures;
bool get hasPersistentSyncFailure => _consecutiveFailures >= 2;
bool get isStaleDataWarning => _isStaleDataWarning;
bool get isForcedSyncInProgress => _isForcedSyncInProgress;
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| sync | sync_provider.dart:285 | `Future<SyncResult> sync()` | Default sync trigger |
| fullSync | sync_provider.dart:288 | `Future<SyncResult> fullSync()` | Full manual sync |
| quickSync | sync_provider.dart:295 | `Future<SyncResult> quickSync()` | Quick dirty-scope sync |
| setStaleDataWarning | sync_provider.dart:236 | `void setStaleDataWarning(bool isStale)` | Lifecycle → UI stale warning |
| setForcedSyncInProgress | sync_provider.dart:244 | `void setForcedSyncInProgress(bool inProgress)` | Lifecycle → UI forced sync indicator |
| addNotification | (present) | `void addNotification(String message)` | Queue enrollment notifications |
| dismissCircuitBreaker | (present) | `Future<void> dismissCircuitBreaker(...)` | User action to dismiss CB |

## Imports

```dart
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
```

## After Refactor

SyncProvider should:
1. Subscribe to `SyncStatus` stream (replacing independent `_isSyncing`, `_status`, `_lastSyncTime`)
2. Read diagnostics from `SyncDiagnosticsSnapshot` / `SyncQueryService` (replacing `getPendingBuckets` passthrough)
3. Remove `get orchestrator` (raw exposure)
4. Delete `_sanitizeSyncError` (use `ClassifiedSyncError.userSafeMessage` from `SyncErrorClassifier`)
5. Trigger sync via `SyncCoordinator` instead of `SyncOrchestrator`
