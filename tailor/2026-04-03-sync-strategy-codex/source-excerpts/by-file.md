# Source Excerpts — By File

## lib/features/sync/engine/sync_engine.dart

### SyncEngineResult (line 32-70)
```dart
class SyncEngineResult {
  final int pushed;
  final int pulled;
  final int errors;
  final List<String> errorMessages;
  final bool lockFailed;
  final int rlsDenials;
  final int conflicts;
  final int skippedFk;
  final int skippedPush;

  const SyncEngineResult({ ... });

  bool get hasErrors => errors > 0;
  bool get isSuccess => !hasErrors && !lockFailed && conflicts == 0;

  SyncEngineResult operator +(SyncEngineResult other) { ... }
}
```

### SyncEngine constructor (line 153-160)
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

### SyncEngine.resetState (line 204-213)
```dart
Future<void> resetState() async {
    try {
      await db.execute(
        "UPDATE sync_control SET value = '0' WHERE key = 'pulling'",
      );
    } catch (e) {
      Logger.sync('[SyncEngine] resetState best-effort reset: $e');
    }
    await _mutex.forceReset(lockedBy);
  }
```

### SyncEngine.pushAndPull (line 216-360)
See patterns/sync-engine-pattern.md for full source.

### SyncEngine._push (line 421-561)
See patterns/sync-engine-pattern.md for full source.

### SyncEngine._pull (line 1452-1556)
See patterns/sync-engine-pattern.md for full source.

---

## lib/features/sync/application/sync_orchestrator.dart

### SyncOrchestrator.initialize (line 149-182)
See patterns/orchestrator-pattern.md for full source.

### SyncOrchestrator.syncLocalAgencyProjects (line 241-318)
See patterns/orchestrator-pattern.md for full source.

### SyncOrchestrator._syncWithRetry (line 325-410)
```dart
Future<SyncResult> _syncWithRetry() async {
    SyncResult lastResult = const SyncResult();
    for (int attempt = 0; attempt < _maxRetries; attempt++) {
      if (attempt > 0) {
        final delay = _baseRetryDelay * (1 << attempt);
        await Future<void>.delayed(delay);
      }
      final dnsOk = await checkDnsReachability();
      if (!dnsOk) { continue; }
      lastResult = await _doSync();
      if (!lastResult.hasErrors) return lastResult;
      if (!_isTransientError(lastResult)) return lastResult;
    }
    // Schedule background retry after 60s
    _backgroundRetryTimer = Timer(const Duration(seconds: 60), () async {
      if (_disposed) return;
      final dnsOk = await checkDnsReachability();
      if (dnsOk && !_disposed) await syncLocalAgencyProjects();
    });
    return lastResult;
  }
```

### SyncOrchestrator._doSync (line 413-448)
See patterns/orchestrator-pattern.md for full source.

---

## lib/features/sync/application/sync_lifecycle_manager.dart

### Full class (line 14-155)
Key fields:
```dart
class SyncLifecycleManager with WidgetsBindingObserver {
  final SyncOrchestrator _syncOrchestrator;
  Timer? _debounceTimer;
  static const Duration _staleThreshold = Duration(hours: 24);

  bool Function()? isReadyForSync;
  Future<void> Function()? onAppResumed;
  void Function(bool)? onStaleDataWarning;
  void Function(bool)? onForcedSyncInProgress;
}
```

All methods documented in patterns/lifecycle-manager-pattern.md.

---

## lib/features/sync/application/fcm_handler.dart

### fcmBackgroundMessageHandler (line 13-25)
```dart
Future<void> fcmBackgroundMessageHandler(RemoteMessage message) async {
  // Currently just logs — no sync trigger in background
}
```

### FcmHandler class (line 28-140)
All methods documented in patterns/fcm-handler-pattern.md.

---

## lib/features/sync/config/sync_config.dart

### SyncEngineConfig (line 1-43)
```dart
class SyncEngineConfig {
  SyncEngineConfig._();
  static const int pushBatchLimit = 500;
  static const int pushAnomalyThreshold = 1000;
  static const int maxRetryCount = 5;
  static const int pullPageSize = 100;
  static const Duration pullSafetyMargin = Duration(seconds: 5);
  static const Duration integrityCheckInterval = Duration(hours: 4);
  static const int maxConsecutiveResets = 3;
  static const Duration staleLockTimeout = Duration(minutes: 15);
  static const Duration changeLogRetention = Duration(days: 7);
  static const Duration conflictLogRetention = Duration(days: 7);
  static const Duration conflictWarningAge = Duration(days: 30);
  static const Duration retryBaseDelay = Duration(seconds: 1);
  static const Duration retryMaxDelay = Duration(seconds: 16);
  static const int circuitBreakerThreshold = 1000;
  static const int conflictPingPongThreshold = 3;
  static const int cursorResetMinDiff = 5;
  static const double cursorResetPercentThreshold = 0.10;
  static const Duration orphanMinAge = Duration(hours: 24);
  static const int orphanMaxPerCycle = 50;
}
```

---

## lib/features/sync/engine/scope_type.dart

### ScopeType (line 13-29)
```dart
enum ScopeType {
  direct,        // company_id
  viaProject,    // project_id IN synced_projects
  viaEntry,      // same SQL as viaProject (denormalized)
  viaContractor, // contractor_id chain
}
```

---

## lib/features/sync/engine/change_tracker.dart

### Full class (line 43-215)
See patterns/change-tracker-pattern.md for full source.

---

## lib/features/sync/adapters/table_adapter.dart

### Full class (line 15-180)
See patterns/adapter-scope-pattern.md for full source.

---

## lib/features/sync/presentation/providers/sync_provider.dart

### SyncProvider class (line 18-347)
Key state:
```dart
class SyncProvider extends ChangeNotifier {
  SyncAdapterStatus _status = SyncAdapterStatus.idle;
  DateTime? _lastSyncTime;
  int _pendingCount = 0;
  Map<String, BucketCount> _pendingBuckets = {};
  bool _isSyncing = false;
  bool _isStaleDataWarning = false;
  bool _isForcedSyncInProgress = false;
  int _consecutiveFailures = 0;
  bool _circuitBreakerTripped = false;
}
```

Key method:
```dart
Future<SyncResult> sync() async {
    return await _syncOrchestrator.syncLocalAgencyProjects();
  }
```

---

## lib/features/sync/presentation/widgets/sync_status_icon.dart

### SyncStatusIcon (line 15-54)
```dart
class SyncStatusIcon extends StatelessWidget {
  Widget build(BuildContext context) {
    return Consumer<SyncProvider>(
      builder: (context, syncProvider, _) {
        return IconButton(
          key: TestingKeys.syncProgressSpinner,
          icon: Icon(icon, color: color, size: 20),
          onPressed: () => context.push('/sync/dashboard'),
          tooltip: _getTooltip(syncProvider),
        );
      },
    );
  }
}
```

Currently used ONLY in `home_screen.dart:375`. NOT in scaffold_with_nav_bar.

---

## lib/features/sync/application/sync_initializer.dart

### SyncInitializer.create (line 38-130)
See patterns/orchestrator-pattern.md for wiring chain.

---

## lib/features/sync/application/background_sync_handler.dart

### BackgroundSyncHandler.initialize (line 94-134)
```dart
static Future<void> initialize({
    required DatabaseService dbService,
    SupabaseClient? supabaseClient,
  }) async {
    if (Platform.isAndroid || Platform.isIOS) {
      await Workmanager().registerPeriodicTask(
        kBackgroundSyncTaskName,
        kBackgroundSyncTaskName,
        frequency: const Duration(hours: 4),
        constraints: Constraints(networkType: NetworkType.connected),
      );
    } else {
      // Desktop: Timer with random jitter (0-30 min)
      final jitter = Duration(minutes: Random().nextInt(30));
      _desktopSyncTimer = Timer.periodic(
        const Duration(hours: 4) + jitter,
        (_) => _performDesktopSync(),
      );
    }
  }
```

---

## lib/core/router/routes/sync_routes.dart

### Full file (line 1-19)
```dart
List<RouteBase> syncRoutes() => [
  GoRoute(
    path: '/sync/dashboard',
    name: 'sync-dashboard',
    builder: (context, state) => const SyncDashboardScreen(),
  ),
  GoRoute(
    path: '/sync/conflicts',
    name: 'sync-conflicts',
    builder: (context, state) => const ConflictViewerScreen(),
  ),
];
```
