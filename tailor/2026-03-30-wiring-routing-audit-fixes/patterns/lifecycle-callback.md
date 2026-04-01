# Pattern: Lifecycle Callback Wiring

## How We Do It
`SyncLifecycleManager` uses nullable function fields as extension points. The caller (currently `SyncProviders.initialize()`) wires callbacks after construction. This avoids constructor parameter explosion and allows different wiring in test vs production. The lifecycle manager itself only knows about `SyncOrchestrator` — all other dependencies are injected via callbacks. The spec extracts the callback wiring from `sync_providers.dart` into `SyncInitializer` or the lifecycle manager itself.

## Exemplar

### SyncLifecycleManager Callback Fields (`lib/features/sync/application/sync_lifecycle_manager.dart:22-32`)
```dart
class SyncLifecycleManager with WidgetsBindingObserver {
  bool Function()? isReadyForSync;
  void Function(bool isStale)? onStaleDataWarning;
  void Function(bool inProgress)? onForcedSyncInProgress;
  Future<void> Function()? onAppResumed;

  SyncLifecycleManager(this._syncOrchestrator);
}
```

### Callback Wiring in SyncProviders (`lib/features/sync/di/sync_providers.dart:210-235`)
```dart
// Configure lifecycle manager readiness check
syncLifecycleManager.isReadyForSync = () {
  return authProvider.isAuthenticated &&
      authProvider.userProfile?.companyId != null;
};

// Task 1.13: Foreground resume hook
syncLifecycleManager.onAppResumed = () async {
  if (!authProvider.isAuthenticated) return;
  final timedOut = await authProvider.checkInactivityTimeout();
  if (timedOut) return;
  await authProvider.updateLastActive();
  if (appConfigProvider.isRefreshDue) {
    await appConfigProvider.checkConfig();
    if (appConfigProvider.requiresReauth) {
      await authProvider.handleForceReauth(appConfigProvider.reauthReason);
    }
  }
};

// Register lifecycle observer
WidgetsBinding.instance.addObserver(syncLifecycleManager);
```

### SyncOrchestrator Callback Fields (`lib/features/sync/application/sync_orchestrator.dart:94-98`)
```dart
Future<void> Function(String tableName, int pulledCount)? onPullComplete;
void Function(String message)? onNewAssignmentDetected;
```

### Provider Callback Wiring in SyncProviders.providers (`sync_providers.dart:257-285`)
```dart
ChangeNotifierProvider(create: (_) {
  final syncProvider = SyncProvider(syncOrchestrator);
  syncLifecycleManager.onStaleDataWarning = (isStale) {
    syncProvider.setStaleDataWarning(isStale);
  };
  syncLifecycleManager.onForcedSyncInProgress = (inProgress) {
    syncProvider.setForcedSyncInProgress(inProgress);
  };
  syncProvider.onSyncCycleComplete = () async {
    final counts = await projectLifecycleService.getAllUnsyncedCounts();
    projectSyncHealthProvider.updateCounts(counts);
  };
  syncOrchestrator.onNewAssignmentDetected = (message) {
    syncProvider.addNotification(message);
  };
  return syncProvider;
}),
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| SyncLifecycleManager constructor | sync_lifecycle_manager.dart:34 | `SyncLifecycleManager(this._syncOrchestrator)` | Creating lifecycle manager |
| SyncLifecycleManager.dispose | sync_lifecycle_manager.dart:147 | `void dispose()` | Cleanup |
| SyncOrchestrator constructor | sync_orchestrator.dart:104 | `SyncOrchestrator(this._dbService, {SupabaseClient? supabaseClient})` | Creating orchestrator |
| SyncOrchestrator.initialize | sync_orchestrator.dart:154 | `Future<void> initialize()` | Initial setup |
| SyncOrchestrator.setUserProfileSyncDatasource | sync_orchestrator.dart:119 | `void setUserProfileSyncDatasource(UserProfileSyncDatasource ds)` | Inject profile sync |
| SyncOrchestrator.setSyncContextProvider | sync_orchestrator.dart:125 | `void setSyncContextProvider(...)` | Inject auth context |
| SyncOrchestrator.setAppConfigProvider | sync_orchestrator.dart:131 | `void setAppConfigProvider(AppConfigProvider provider)` | Wire stale banner reset |
| SyncOrchestrator.setAdapterCompanyContext | sync_orchestrator.dart:136 | `void setAdapterCompanyContext({String? companyId, String? userId})` | Set company scope |
| FcmHandler constructor | fcm_handler.dart:42 | `FcmHandler({AuthService? authService, SyncOrchestrator? syncOrchestrator})` | Creating FCM handler |
| FcmHandler.initialize | fcm_handler.dart:48 | `Future<void> initialize({String? userId})` | FCM registration |
| BackgroundSyncHandler.initialize | background_sync_handler.dart | `static Future<void> initialize({required DatabaseService dbService})` | Background sync registration |

## Imports
```dart
import 'package:construction_inspector/features/sync/application/sync_lifecycle_manager.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/features/sync/application/fcm_handler.dart';
import 'package:construction_inspector/features/sync/application/background_sync_handler.dart';
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
```
