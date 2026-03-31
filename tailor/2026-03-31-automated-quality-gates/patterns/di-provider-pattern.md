# Pattern: DI / Provider Composition

## How We Do It
Dependencies are created in `AppInitializer.initialize()` which returns an `AppDependencies` container. This container is passed to `buildAppProviders()` which composes a tier-ordered `List<SingleChildWidget>` for `MultiProvider`. Each feature module exports a `*Providers()` function that returns its slice of the provider list. The key invariant is that `Supabase.instance.client` and `DatabaseService()` are resolved ONCE in the DI root and injected everywhere via constructors.

## Exemplars

### buildAppProviders (lib/core/di/app_providers.dart:37)
```dart
List<SingleChildWidget> buildAppProviders(AppDependencies deps) {
  return [
    // Tier 0: Core services
    Provider<DatabaseService>.value(value: deps.dbService),
    Provider<PermissionService>.value(value: deps.permissionService),
    ...settingsProviders(
      preferencesService: deps.preferencesService,
      trashRepository: deps.trashRepository,
      softDeleteService: deps.softDeleteService,
    ),
    // Tier 3: Auth
    ...authProviders(
      authService: deps.authService,
      authProvider: deps.authProvider,
      appConfigProvider: deps.appConfigProvider,
    ),
    // Tier 4: Feature providers (order matters)
    ...projectProviders(...),
    ...locationProviders(...),
    ...contractorProviders(...),
    // ... more features ...
    // Tier 5: Sync
    ...SyncProviders.providers(...),
  ];
}
```

### AppDependencies (lib/core/di/app_initializer.dart:267)
Container class with 7 sub-containers: `CoreDeps`, `AuthDeps`, `ProjectDeps`, `EntryDeps`, `FormDeps`, `SyncDeps`, `FeatureDeps` + `appRouter`. Convenience getters delegate to sub-containers.

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `buildAppProviders` | app_providers.dart:37 | `List<SingleChildWidget> buildAppProviders(AppDependencies deps)` | Compose full provider tree |
| `AppInitializer.initialize` | app_initializer.dart:359 | `static Future<AppDependencies> initialize({String logDirOverride = ''})` | App startup, creates all deps |
| `authProviders` | auth_providers.dart:44 | `List<SingleChildWidget> authProviders({...})` | Auth feature provider slice |
| `SyncProviders.providers` | sync_providers.dart:236 | `static List<SingleChildWidget> providers({...})` | Sync feature provider slice |

## Imports
```dart
import 'package:construction_inspector/core/di/app_initializer.dart';
import 'package:construction_inspector/core/di/app_providers.dart';
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
```

## Lint Rules Targeting This Pattern
- A1: `avoid_supabase_singleton` — Supabase.instance.client only in DI root
- A2: `no_direct_database_construction` — DatabaseService() only in DI root
- A7: `single_composition_root` — Provider construction only in buildAppProviders()
- A8: `no_service_construction_in_widgets` — no PermissionService() etc. in widgets
- A15: `no_duplicate_service_instances` — same class constructed 2+ times in DI
