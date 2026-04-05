# Pattern: DI Initialization

## How We Do It

Sync DI uses a two-step pattern: `SyncInitializer.create()` builds and wires all components pre-widget-tree, then `SyncProviders.providers()` creates the ChangeNotifierProvider entries for the widget tree. The SyncOrchestratorBuilder enforces that all required deps are set before build, preventing mutation after build.

## Exemplar: SyncInitializer.create()

```dart
// lib/features/sync/application/sync_initializer.dart:43-197
static Future<({
  SyncOrchestrator orchestrator,
  SyncLifecycleManager lifecycleManager,
  FcmHandler? fcmHandler,
  RealtimeHintHandler? realtimeHintHandler,
})> create({
  required DatabaseService dbService,
  required AuthProvider authProvider,
  required AppConfigProvider appConfigProvider,
  required CompanyLocalDatasource companyLocalDs,
  required AuthService authService,
  SupabaseClient? supabaseClient,
  PreferencesService? preferencesService,
}) async {
  // Step 1: Prepare builder
  final builder = SyncOrchestratorBuilder()
    ..dbService = dbService
    ..supabaseClient = supabaseClient
    ..appConfigProvider = appConfigProvider
    ..syncContextProvider = () => (
      companyId: authProvider.userProfile?.companyId,
      userId: authProvider.userId,
    );

  // Step 2: Wire optional UserProfileSyncDatasource
  // Step 3: Build orchestrator (fully configured, no setters)
  final syncOrchestrator = builder.build();
  await syncOrchestrator.initialize();

  // Step 4: Create lifecycle manager
  final syncLifecycleManager = SyncLifecycleManager(syncOrchestrator);

  // Step 5: Wire enrollment service
  final enrollmentService = SyncEnrollmentService(
    dbService: dbService, orchestrator: syncOrchestrator,
  );
  syncOrchestrator.onPullComplete = (tableName, pulledCount) async { /* ... */ };

  // Step 6: FCM initialization (mobile only)
  // Step 7: Wire lifecycle callbacks
  // Step 8: Register lifecycle observer

  return (orchestrator: syncOrchestrator, lifecycleManager: syncLifecycleManager, ...);
}
```

## Exemplar: SyncOrchestratorBuilder

```dart
// lib/features/sync/application/sync_orchestrator_builder.dart:12-72
class SyncOrchestratorBuilder {
  DatabaseService? dbService;
  SupabaseClient? supabaseClient;
  SyncEngineFactory? engineFactory;
  UserProfileSyncDatasource? userProfileSyncDatasource;
  ({String? companyId, String? userId}) Function()? syncContextProvider;
  AppConfigProvider? appConfigProvider;
  DirtyScopeTracker? dirtyScopeTracker;
  String? companyId;
  String? userId;
  bool _built = false;  // SEC-A3: prevent accidental reuse

  SyncOrchestrator build() {
    if (_built) throw StateError('build() already called');
    if (dbService == null) throw StateError('dbService required');
    // ... validation ...
    _built = true;
    return SyncOrchestrator.fromBuilder(/* all fields */);
  }
}
```

## Exemplar: SyncProviders.providers()

```dart
// lib/features/sync/di/sync_providers.dart:59-95
static List<SingleChildWidget> providers({
  required SyncOrchestrator syncOrchestrator,
  required SyncLifecycleManager syncLifecycleManager,
  required ProjectLifecycleService projectLifecycleService,
  required ProjectSyncHealthProvider projectSyncHealthProvider,
  required DatabaseService dbService,
}) {
  return [
    Provider<SyncRegistry>.value(value: SyncRegistry.instance),
    Provider<SyncOrchestrator>.value(value: syncOrchestrator),
    Provider<DeletionNotificationRepository>(create: (_) => ...),
    Provider<ConflictRepository>(create: (_) => ...),
    ChangeNotifierProvider(create: (_) {
      final syncProvider = SyncProvider(syncOrchestrator);
      // Wire lifecycle manager callbacks
      syncLifecycleManager.onStaleDataWarning = syncProvider.setStaleDataWarning;
      syncLifecycleManager.onForcedSyncInProgress = syncProvider.setForcedSyncInProgress;
      syncProvider.onSyncCycleComplete = () => projectSyncHealthProvider.refreshFromService(...);
      syncOrchestrator.onNewAssignmentDetected = syncProvider.addNotification;
      return syncProvider;
    }),
  ];
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| SyncInitializer.create | sync_initializer.dart:43 | `static Future<(...)> create({...})` | Pre-widget-tree sync wiring |
| SyncProviders.initialize | sync_providers.dart:29 | `static Future<(...)> initialize({...})` | Delegates to SyncInitializer.create |
| SyncProviders.providers | sync_providers.dart:59 | `static List<SingleChildWidget> providers({...})` | Widget-tree provider list |
| SyncOrchestratorBuilder.build | sync_orchestrator_builder.dart:38 | `SyncOrchestrator build()` | Build validated orchestrator |

## After Refactor

The initializer must wire the new classes in this order:
1. `SyncErrorClassifier` (pure, no deps)
2. `SyncStatusStore` (stream controller)
3. `LocalSyncStore`, `SupabaseSync` (I/O boundaries)
4. `PushHandler`, `PullHandler`, `FileSyncHandler`, `FkRescueHandler`, `EnrollmentHandler`, `MaintenanceHandler`
5. `SyncEngine` (slim coordinator)
6. `SyncRetryPolicy`, `ConnectivityProbe`
7. `SyncCoordinator` (replaces SyncOrchestrator)
8. `SyncTriggerPolicy`, `PostSyncHooks`
9. `SyncQueryService`
10. `SyncProvider` (subscribes to SyncStatus stream + SyncQueryService)

## Imports

```dart
import 'package:construction_inspector/features/sync/application/sync_initializer.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator_builder.dart';
import 'package:construction_inspector/features/sync/di/sync_providers.dart';
```
