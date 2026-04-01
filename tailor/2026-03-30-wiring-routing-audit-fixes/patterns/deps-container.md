# Pattern: Feature Deps Container

## How We Do It
Each feature group has a typed container class that holds all dependencies created during initialization. These are plain immutable classes with `const` constructors and `required` fields — no logic, no factory methods. `AppDependencies` aggregates all feature deps into a single object passed to `buildAppProviders()`.

## Exemplars

### CoreDeps (`lib/core/di/app_initializer.dart:115-143`)
```dart
class CoreDeps {
  final DatabaseService dbService;
  final PreferencesService preferencesService;
  final PhotoService photoService;
  final ImageService imageService;
  final TrashRepository trashRepository;
  final SoftDeleteService softDeleteService;
  final PermissionService permissionService;

  const CoreDeps({
    required this.dbService,
    required this.preferencesService,
    required this.photoService,
    required this.imageService,
    required this.trashRepository,
    required this.softDeleteService,
    required this.permissionService,
  });

  CoreDeps copyWith({PhotoService? photoService}) => CoreDeps(
        dbService: dbService,
        preferencesService: preferencesService,
        photoService: photoService ?? this.photoService,
        imageService: imageService,
        trashRepository: trashRepository,
        softDeleteService: softDeleteService,
        permissionService: permissionService,
      );
}
```

### AuthDeps (`lib/core/di/app_initializer.dart:146-156`)
```dart
class AuthDeps {
  final AuthService authService;
  final AuthProvider authProvider;
  final AppConfigProvider appConfigProvider;

  const AuthDeps({
    required this.authService,
    required this.authProvider,
    required this.appConfigProvider,
  });
}
```

### AppDependencies (`lib/core/di/app_initializer.dart:267-355`)
```dart
class AppDependencies {
  final CoreDeps core;
  final AuthDeps auth;
  final ProjectDeps project;
  final EntryDeps entry;
  final FormDeps form;
  final SyncDeps sync;
  final FeatureDeps feature;
  final AppRouter appRouter;  // NOTE: spec says to remove this field

  const AppDependencies({
    required this.core,
    required this.auth,
    required this.project,
    required this.entry,
    required this.form,
    required this.sync,
    required this.feature,
    required this.appRouter,
  });

  // Convenience accessors (30+ getters delegating to sub-deps)
  // e.g.: DatabaseService get dbService => core.dbService;
  // NOTE: spec identifies these as compatibility surface to evaluate
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| CoreDeps constructor | app_initializer.dart:124 | `const CoreDeps({required ...})` | Creating core deps container |
| CoreDeps.copyWith | app_initializer.dart:134 | `CoreDeps copyWith({PhotoService? photoService})` | Driver mode photo service swap |
| AppDependencies constructor | app_initializer.dart:277 | `const AppDependencies({required ...})` | Assembling all deps |
| AppDependencies.copyWith | app_initializer.dart:348 | `AppDependencies copyWith({PhotoService? photoService})` | Driver mode substitution |

## Imports
```dart
import 'package:construction_inspector/core/di/app_initializer.dart';
// For individual types:
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/shared/services/preferences_service.dart';
import 'package:construction_inspector/services/photo_service.dart';
// etc. — each field type has its own import
```
