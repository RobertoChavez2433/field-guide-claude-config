# Pattern: Provider Graph Composition

## How We Do It
`buildAppProviders()` is a single function that assembles the complete provider tree in strict tier order. It takes `AppDependencies` and returns `List<SingleChildWidget>`. Each feature contributes its own provider list via a spread (`...featureProviders(...)`). The tier order is: Tier 0 (settings/prefs) → Tier 3 (auth) → Tier 4 (features in dependency order) → Tier 5 (sync). Currently, consent/support providers are spliced in separately at the app widget level — a gap the spec fixes.

## Exemplar

### buildAppProviders (`lib/core/di/app_providers.dart:37-139`)
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
      supabaseClient: deps.supabaseClient,
    ),

    // Tier 4: Feature providers (order matters)
    ...projectProviders(...),
    ...locationProviders(...),
    ...contractorProviders(...),
    ...quantityProviders(...),
    ...photoProviders(...),
    ...formProviders(...),     // forms MUST come before entries
    ...entryProviders(...),
    ...calculatorProviders(...),
    ...galleryProviders(...),
    ...todoProviders(...),
    ...pdfProviders(...),
    ...weatherProviders(...),

    // Tier 5: Sync
    ...SyncProviders.providers(...),
  ];
}
```

### Current Provider Splicing Gap (`lib/main.dart:205-209`)
```dart
// ConstructionInspectorApp.build():
return MultiProvider(
  providers: [
    ...providers,                                           // from buildAppProviders
    ChangeNotifierProvider.value(value: consentProvider),    // SPLICE - should be in buildAppProviders
    ChangeNotifierProvider.value(value: supportProvider),    // SPLICE - should be in buildAppProviders
  ],
  child: Consumer<ThemeProvider>(...),
);
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| buildAppProviders | app_providers.dart:37 | `List<SingleChildWidget> buildAppProviders(AppDependencies deps)` | Assembling full provider tree |
| settingsProviders | settings_providers.dart | `List<SingleChildWidget> settingsProviders({...})` | Settings tier |
| authProviders | auth_providers.dart:43 | `List<SingleChildWidget> authProviders({...})` | Auth tier |

## Imports
```dart
import 'package:construction_inspector/core/di/app_providers.dart';
import 'package:construction_inspector/core/di/app_initializer.dart'; // for AppDependencies
import 'package:provider/single_child_widget.dart';
```
