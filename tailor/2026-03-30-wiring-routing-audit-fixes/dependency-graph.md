# Dependency Graph

## Direct Changes

| File | Symbols | Change Type |
|------|---------|-------------|
| `lib/core/di/app_initializer.dart` | AppInitializer, CoreDeps, AuthDeps, ProjectDeps, EntryDeps, FormDeps, SyncDeps, FeatureDeps, AppDependencies, _NoOpProjectRemoteDatasource | Major refactor (891→~80 lines) |
| `lib/core/di/app_providers.dart` | buildAppProviders | Minor (add consent/support) |
| `lib/core/router/app_router.dart` | AppRouter, ScaffoldWithNavBar | Split into 3 files (932→~100 lines) |
| `lib/main.dart` | main, _runApp, ConstructionInspectorApp, _beforeSendSentry, _beforeSendTransaction | Slim (223→~40 lines) |
| `lib/main_driver.dart` | main, _runApp | Slim (121→~30 lines) |
| `lib/features/sync/di/sync_providers.dart` | SyncProviders | Extract business logic (285→~60 lines) |
| `lib/features/sync/application/fcm_handler.dart` | FcmHandler | Minor (absorb FCM init from sync_providers) |
| `lib/features/sync/application/sync_lifecycle_manager.dart` | SyncLifecycleManager | Minor (absorb lifecycle wiring) |
| `lib/core/driver/driver_server.dart` | DriverServer | Add /harness endpoint |
| `lib/driver_main.dart` | main | DELETE |
| `lib/test_harness.dart` | main, _readHarnessConfig | DELETE |
| `lib/features/settings/di/consent_support_factory.dart` | createConsentAndSupportProviders, ConsentSupportResult | Evaluate absorption into AppBootstrap |

## New Files

| File | Purpose |
|------|---------|
| `lib/core/di/core_deps.dart` | CoreDeps with supabaseClient field |
| `lib/core/di/init_options.dart` | InitOptions (driver mode, overrides) |
| `lib/core/di/app_bootstrap.dart` | Post-init wiring (consent, auth listener, router) |
| `lib/core/router/app_redirect.dart` | Redirect matrix (~200 lines) |
| `lib/core/router/scaffold_with_nav_bar.dart` | Shell widget + banners (~185 lines) |
| `lib/features/sync/application/sync_enrollment_service.dart` | Enrollment/unenrollment logic |
| `lib/features/sync/di/sync_initializer.dart` | Sync initialization orchestration |
| `lib/core/driver/test_db_factory.dart` | In-memory DB setup (from test_harness) |

## Import Graph: app_initializer.dart

**165 nodes, 427 edges (depth 2)**

### Direct imports (97 files)
Key imports that will change during refactor:
- `lib/core/router/app_router.dart` — will move to app_bootstrap.dart
- `lib/core/config/supabase_config.dart` — Supabase.instance.client calls move to CoreDeps
- `lib/features/sync/di/sync_providers.dart` — will call SyncInitializer instead
- All local datasource files — will move to feature initializers
- All repository impl files — will move to feature initializers

### Direct importers (3 files)
- `lib/core/di/app_providers.dart` — reads AppDependencies
- `lib/main.dart` — calls AppInitializer.initialize()
- `lib/main_driver.dart` — calls AppInitializer.initialize()

## Import Graph: app_router.dart

**82 nodes, 118 edges (depth 2)**

### Direct imports (38 files)
Key imports that will split:
- Redirect-only: `app_config_provider.dart`, `auth_provider.dart`, `supabase_config.dart`, `test_mode_config.dart`
- Scaffold-only: `sync_provider.dart`, `project_switcher.dart`, banners, `testing_keys.dart`, `field_guide_colors.dart`
- Route-table: all screen imports (auth, entries, dashboard, projects, quantities, settings, pdf, calculator, forms, etc.)

### Direct importers (3 files)
- `lib/core/di/app_initializer.dart` — creates AppRouter (will move to app_bootstrap.dart)
- `lib/main.dart` — creates AppRouter (will move to app_bootstrap.dart)
- `lib/main_driver.dart` — creates AppRouter (will move to app_bootstrap.dart)

## Import Graph: sync_providers.dart

**70 nodes, 110 edges (depth 2)**

### Direct imports (21 files)
Business logic imports that move to sync_enrollment_service.dart:
- `lib/features/auth/data/datasources/local/company_local_datasource.dart`
- `lib/features/auth/data/datasources/local/user_profile_local_datasource.dart`
- `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart`

### Direct importers (2 files)
- `lib/core/di/app_initializer.dart`
- `lib/core/di/app_providers.dart`

## Import Graph: main.dart

**150 nodes, 185 edges (depth 2)**

### Direct imports (12 files)
- `lib/core/router/app_router.dart` — moves to app_bootstrap.dart
- `lib/core/config/sentry_consent.dart` — stays (Sentry gate)
- `lib/core/di/app_providers.dart` — stays
- `lib/core/di/app_initializer.dart` — stays
- `lib/features/settings/di/consent_support_factory.dart` — moves to app_bootstrap.dart
- `lib/features/settings/presentation/providers/consent_provider.dart` — moves to app_bootstrap.dart
- `lib/features/settings/presentation/providers/support_provider.dart` — moves to app_bootstrap.dart

### Direct importers (2 files)
- `lib/main_driver.dart` — imports ConstructionInspectorApp
- `test/widget_test.dart` — imports for testing

## Data Flow Diagram

```
main.dart / main_driver.dart
  │
  ├── [driver only] DriverServer.start()
  │
  └── AppInitializer.initialize(options)           ← CURRENT: 891-line god method
        │
        ├── CoreDeps.create(options)                ← NEW: extract from lines 361-470
        │     ├── PreferencesService.initialize()
        │     ├── Aptabase.init() [if consent]
        │     ├── _initDebugLogging()
        │     ├── DatabaseService()
        │     ├── TrashRepository, SoftDeleteService
        │     ├── TesseractInitializer.initialize()
        │     ├── Supabase.initialize() [if configured]
        │     ├── Firebase.initializeApp() [mobile only]
        │     └── supabaseClient field              ← NEW: replaces 7x Supabase.instance.client
        │
        ├── AuthInitializer.create(coreDeps)        ← NEW: extract from lines 571-690
        │     ├── AuthService, AuthProvider
        │     ├── AppConfigProvider
        │     └── Version gate (force reauth on upgrade)
        │
        ├── ProjectInitializer.create(coreDeps, authDeps)  ← NEW: extract from lines 470-570
        │     ├── Local datasources + repositories
        │     ├── Use cases (delete, load assignments, fetch remote)
        │     └── ProjectSettingsProvider, ProjectImportRunner
        │
        ├── EntryInitializer.create(coreDeps)       ← NEW: extract from lines 555-575
        ├── FormInitializer.create(coreDeps)        ← NEW: extract from lines 500-520
        │
        ├── SyncInitializer.create(coreDeps, authDeps, ...)  ← NEW
        │     └── SyncProviders.initialize() → SyncEnrollmentService
        │
        └── AppBootstrap.configure(deps, options)   ← NEW: extract from main.dart:120-187
              ├── createConsentAndSupportProviders()
              ├── consentProvider.loadConsentState()
              ├── enableSentryReporting() [if consented]
              ├── Auth listener (sign-out consent clear, sign-in audit)
              └── AppRouter(authProvider, consentProvider)  ← ALL providers required
```
