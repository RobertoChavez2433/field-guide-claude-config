# Blast Radius

## Per-Symbol Impact

### AppInitializer (class, line 360)
- **Risk score**: 0.90
- **Direct dependents**: 3
- **Confirmed**: `app_providers.dart` (1 ref), `main.dart` (3 refs), `main_driver.dart` (2 refs)
- **Test**: `test/widget_test.dart` (1 ref)
- **Impact**: HIGH — every entrypoint calls `AppInitializer.initialize()`

### AppRouter (class, line 77)
- **Risk score**: 0.85
- **Direct dependents**: 3
- **Confirmed**: `app_initializer.dart` (5 refs), `main.dart` (4 refs), `main_driver.dart` (3 refs)
- **Potential**: `app_providers.dart`, `test/widget_test.dart`
- **Impact**: HIGH — router construction in 3 places (will consolidate to 1)

### AppDependencies (class, line 267)
- **Risk score**: 0.90
- **Direct dependents**: 3
- **Confirmed**: `app_providers.dart` (2 refs)
- **Potential**: `main.dart`, `main_driver.dart`, `test/widget_test.dart`
- **Impact**: HIGH — return type of AppInitializer.initialize(), input to buildAppProviders()

### SyncProviders (class, line 32)
- **Risk score**: 0.81
- **Direct dependents**: 2
- **Confirmed**: `app_initializer.dart` (3 refs), `app_providers.dart` (1 ref)
- **Potential**: `main.dart`, `main_driver.dart` (via transitive import)
- **Impact**: MEDIUM — business logic extraction, wiring interface unchanged

### buildAppProviders (function, line 37)
- **Risk score**: 0.87
- **Direct dependents**: 2
- **Confirmed**: `main.dart` (1 ref), `main_driver.dart` (1 ref)
- **Potential**: `test/widget_test.dart`
- **Impact**: MEDIUM — will add consent/support providers to list

### ScaffoldWithNavBar (class, line 747)
- **Risk score**: 0.85
- **Direct dependents**: 0 confirmed (used internally via ShellRoute builder)
- **Potential**: 5 files import app_router.dart
- **Impact**: LOW — self-contained widget, extraction is clean cut

### createConsentAndSupportProviders (function, line 29)
- **Risk score**: 0.87
- **Direct dependents**: 2
- **Confirmed**: `main.dart` (1 ref), `main_driver.dart` (1 ref)
- **Impact**: MEDIUM — may be absorbed into AppBootstrap

### ConstructionInspectorApp (class, line 189)
- **Direct dependents**: 2
- **Confirmed importers**: `main_driver.dart` (imports by name), `test/widget_test.dart`
- **Impact**: MEDIUM — constructor params will change (remove consent/support splicing)

## Class Hierarchy

All target classes are **standalone** (no ancestors, no descendants):
- `AppInitializer` — standalone
- `AppRouter` — standalone
- `SyncProviders` — standalone
- `FcmHandler` — standalone
- `DriverServer` — standalone
- `SyncLifecycleManager` — mixin `WidgetsBindingObserver` (external)

No subclass breakage risk.

## Dead Code Targets

### Confirmed Dead (from find_dead_code)

| File | Dead Symbols | Confidence |
|------|-------------|------------|
| `lib/test_harness/stub_services.dart` | 36 (entire file) | 1.0 |
| `test/core/driver/driver_server_sync_status_test.dart` | 5 | 1.0 |
| `test/features/sync/application/fcm_handler_test.dart` | 5 | 1.0 |

### Spec-Identified Dead Code

| Symbol | File | Line | Reason |
|--------|------|------|--------|
| `appRouter` field | `app_initializer.dart` (AppDependencies) | 275 | Runtime never uses it — main.dart/main_driver.dart build their own |
| `appRouter` in `copyWith` | `app_initializer.dart` (AppDependencies) | 348 | Supports dead `appRouter` field |
| AppRouter construction | `app_initializer.dart` (AppInitializer) | 751 | Dead — overridden in both entrypoints |
| "Pure code-motion" comment | `sync_providers.dart` | 32 | Stale docstring |
| Compatibility accessors | `app_initializer.dart` (AppDependencies) | 288-335 | 30+ getters delegating to sub-deps |

## Importer Summary

| File | Importer Count | Key Importers |
|------|---------------|---------------|
| `lib/core/di/app_initializer.dart` | 3 | app_providers, main, main_driver |
| `lib/core/di/app_providers.dart` | 2 | main, main_driver |
| `lib/core/router/app_router.dart` | 3 | app_initializer, main, main_driver |
| `lib/main.dart` | 2 | main_driver (imports ConstructionInspectorApp), widget_test |
| `lib/main_driver.dart` | 0 | Entry point — no importers |
| `lib/features/sync/di/sync_providers.dart` | 2 | app_initializer, app_providers |
| `lib/driver_main.dart` | 0 | Entry point — no importers (safe to delete) |
| `lib/test_harness.dart` | 0 | Entry point — no importers (safe to delete) |
| `lib/features/settings/di/consent_support_factory.dart` | 2 | main, main_driver |
| `lib/test_harness/harness_providers.dart` | 1 | test_harness.dart only |
