# Pattern: Dependency Injection

## How We Do It
Each feature has a `*Initializer` class with `static *Deps create(CoreDeps coreDeps)` that imperatively creates datasources and repositories (Tier 1-2). A `*Deps` const container holds the instances. The `*_providers.dart` file returns `List<SingleChildWidget>` for Tier 3-5 providers registered in the widget tree. `AppDependencies` aggregates all `*Deps` and is passed to `buildAppProviders()`.

## Exemplars

### FormInitializer (`lib/features/forms/di/form_initializer.dart`)
```dart
class FormInitializer {
  FormInitializer._();

  static FormDeps create(CoreDeps coreDeps) {
    final dbService = coreDeps.dbService;

    // Tier 1: Datasources
    final formResponseLocal = FormResponseLocalDatasource(dbService);
    final formExportLocal = FormExportLocalDatasource(dbService);
    // ...

    // Tier 2: Repositories
    final formResponseRepo = FormResponseRepositoryImpl(formResponseLocal);
    final formExportRepo = FormExportRepositoryImpl(formExportLocal);
    // ...

    return FormDeps(
      formResponseRepository: formResponseRepo,
      formExportRepository: formExportRepo,
      // ...
    );
  }
}
```

### AppDependencies (`lib/core/di/app_dependencies.dart:182`)
```dart
class AppDependencies {
  const AppDependencies({
    required this.core,
    required this.auth,
    required this.project,
    required this.entry,
    required this.form,
    required this.sync,
    required this.feature,
  });
  final CoreDeps core;
  final AuthDeps auth;
  // ...
}
```

### Provider Registration (`lib/core/di/app_providers.dart:70`)
Tier 4 order: projects -> locations -> contractors -> quantities -> entries -> photos -> forms -> entries -> calculator -> gallery -> todos -> pdf -> weather.

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `buildAppProviders` | `app_providers.dart:40` | `List<SingleChildWidget> buildAppProviders(AppDependencies deps, {...})` | Compose all providers |

## Where to Add Pay App DI
1. Create `PayAppDeps` container in `app_dependencies.dart`
2. Create `PayAppInitializer` in `lib/features/pay_applications/di/pay_app_initializer.dart`
3. Create `payAppProviders()` in `lib/features/pay_applications/di/pay_app_providers.dart`
4. Add to `AppDependencies` and `buildAppProviders` in Tier 4 (after quantities, since pay apps depend on bid items/quantities)

## Imports
```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/core/di/app_dependencies.dart';
```
