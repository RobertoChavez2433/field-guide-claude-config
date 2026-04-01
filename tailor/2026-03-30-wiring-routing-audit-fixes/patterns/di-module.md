# Pattern: DI Module

## How We Do It
Each feature's DI module is a class with two static methods: `initialize()` for pre-widget-tree async work that returns a typed result, and `providers()` that returns `List<SingleChildWidget>` for the MultiProvider tree. The class itself is never instantiated — all methods are static. `SyncProviders` is the exemplar of this pattern, though currently it violates the pattern by embedding business logic in `initialize()`.

## Exemplars

### SyncProviders (`lib/features/sync/di/sync_providers.dart:32-291`)
```dart
class SyncProviders {
  /// Pre-widget-tree initialization.
  static Future<({
    SyncOrchestrator orchestrator,
    SyncLifecycleManager lifecycleManager,
  })> initialize({
    required DatabaseService dbService,
    required AuthProvider authProvider,
    required AppConfigProvider appConfigProvider,
    required CompanyLocalDatasource companyLocalDs,
    required AuthService authService,
    SupabaseClient? supabaseClient,
  }) async {
    final syncOrchestrator = SyncOrchestrator(dbService, supabaseClient: supabaseClient);
    await syncOrchestrator.initialize();
    // ... 200+ lines of wiring + business logic ...
    return (orchestrator: syncOrchestrator, lifecycleManager: syncLifecycleManager);
  }

  /// Returns provider list for MultiProvider.
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
        // Wire callbacks...
        return syncProvider;
      }),
    ];
  }
}
```

### Feature Provider Functions (alternative pattern)
Other features use standalone functions instead of classes:
```dart
// lib/features/auth/di/auth_providers.dart:43
List<SingleChildWidget> authProviders({
  required AuthService authService,
  required AuthProvider authProvider,
  required AppConfigProvider appConfigProvider,
  required SupabaseClient? supabaseClient,
}) { ... }

// lib/features/projects/di/projects_providers.dart:23
List<SingleChildWidget> projectProviders({
  required ProjectRepository projectRepository,
  // ... 15 more required params
}) { ... }
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| SyncProviders.initialize | sync_providers.dart:38 | `static Future<({SyncOrchestrator, SyncLifecycleManager})> initialize({...})` | Pre-widget-tree sync setup |
| SyncProviders.providers | sync_providers.dart:242 | `static List<SingleChildWidget> providers({...})` | Sync provider list for MultiProvider |
| authProviders | auth_providers.dart:43 | `List<SingleChildWidget> authProviders({...})` | Auth provider list |
| projectProviders | projects_providers.dart:23 | `List<SingleChildWidget> projectProviders({...})` | Project provider list |

## Imports
```dart
import 'package:construction_inspector/features/sync/di/sync_providers.dart';
import 'package:construction_inspector/features/auth/di/auth_providers.dart';
import 'package:construction_inspector/features/projects/di/projects_providers.dart';
import 'package:provider/single_child_widget.dart';
```
