# Dependency Graph: Wiring/Routing Audit Fixes

**Generated:** 2026-03-30
**Spec:** `.claude/specs/2026-03-30-wiring-routing-audit-fixes-spec.md`

---

## Direct Changes

### 1. `lib/core/di/app_initializer.dart` (891 lines → ~80)

**Current structure (line ranges):**
- Lines 115-143: `class CoreDeps` — 7 fields, `copyWith` method. **Needs `supabaseClient` added.**
- Lines 146-156: `class AuthDeps` — 3 fields (authService, authProvider, appConfigProvider)
- Lines 159-187: `class ProjectDeps` — 12 fields
- Lines 190-208: `class EntryDeps` — 7 fields
- Lines 211-223: `class FormDeps` — 4 fields
- Lines 226-234: `class SyncDeps` — 2 fields (orchestrator, lifecycleManager)
- Lines 237-263: `class FeatureDeps` — 11 fields
- Lines 267-353: `class AppDependencies` — aggregates all *Deps + `appRouter` field + 40+ convenience accessors + `copyWith`
- Lines 358-822: `class AppInitializer` — single static `initialize()` method (463 lines!)
- Lines 824-881: Private helpers (`_initDebugLogging`, `_ensureLogDirectoryWritable`)
- Lines 884-891: `_NoOpProjectRemoteDatasource`

**What moves where:**
| Content | Lines | Destination |
|---------|-------|-------------|
| `CoreDeps` class | 115-143 | `lib/core/di/core_deps.dart` (add `supabaseClient`) |
| `AuthDeps`, `ProjectDeps`, `EntryDeps`, `FormDeps`, `SyncDeps`, `FeatureDeps` | 146-263 | Stay in `app_initializer.dart` (they're tiny data classes) |
| `AppDependencies` class | 267-353 | Stay — remove `appRouter` field |
| `initialize()` Phase 1: prefs, logging, config, db, Supabase, Firebase | 362-461 | `CoreDeps.create(options)` in `core_deps.dart` |
| `initialize()` Phase 2: datasources + repositories | 471-568 | Feature initializer static methods |
| `initialize()` Phase 3: auth use cases + providers | 574-648 | `AuthInitializer.create(coreDeps)` |
| `initialize()` Phase 4: lifecycle, version, appConfig | 651-684 | Part of AuthInitializer or AppInitializer orchestrator |
| `initialize()` Phase 5: SyncProviders.initialize() | 686-701 | Stays (already delegated) |
| `initialize()` Phase 6: project providers, auth listener | 703-748 | Feature initializer or AppBootstrap |
| `initialize()` Phase 7: AppRouter creation | 751 | `AppBootstrap.configure()` |
| `initialize()` Phase 8: assemble AppDependencies | 759-821 | Remains in thin orchestrator |
| `_initDebugLogging` + `_ensureLogDirectoryWritable` | 824-881 | Stay as private helpers |
| `_NoOpProjectRemoteDatasource` | 884-891 | Stay |

**Supabase.instance.client usages IN app_initializer.dart (7 occurrences):**
- Line 468: `ProjectLifecycleService(...supabaseClient: Supabase.instance.client)`
- Line 527: `ProjectRemoteDatasourceImpl(Supabase.instance.client)`
- Line 548: `CompanyMembersRepository(Supabase.instance.client)`
- Line 588: `UserProfileRemoteDatasource(Supabase.instance.client)`
- Line 597: `AuthService(Supabase.instance.client)`
- Line 642: `AuthProvider(...supabaseClient: Supabase.instance.client)`
- Line 679: `AppConfigRepository(Supabase.instance.client)`

All 7 → replace with `coreDeps.supabaseClient`

### 2. `lib/core/router/app_router.dart` (932 lines → ~100)

**Current structure:**
- Lines 1-40: Imports (40 imports!)
- Lines 43-55: `_kOnboardingRoutes` const set
- Lines 59-75: `_kNonRestorableRoutes` const set
- Lines 77-745: `class AppRouter` with:
  - Constructor (lines 90-94): takes `AuthProvider` required, `ConsentProvider?` optional
  - `_buildRouter()` (lines 147-745): GoRouter construction including:
    - Redirect matrix (lines 157-342): ~185 lines of redirect logic
    - Route definitions (lines 343-420): auth/onboarding/full-screen routes
    - ShellRoute (lines 425-745): shell builder + all shell routes
- Lines 747-931: `class ScaffoldWithNavBar` (185 lines)

**Split target:**
| Content | Lines | Destination |
|---------|-------|-------------|
| Redirect matrix | 157-342 | `app_redirect.dart` → `AppRedirect` class |
| ScaffoldWithNavBar | 747-931 | `scaffold_with_nav_bar.dart` |
| Route constants | 43-75 | `app_redirect.dart` (used by redirect logic) |
| GoRouter construction + routes | remaining | stays in `app_router.dart` |

**AppRouter constructor change:** `ConsentProvider?` → `required ConsentProvider`; add `required AppConfigProvider`

### 3. `lib/main.dart` (223 lines → ~40)

**Current structure:**
- Lines 28-64: `_beforeSendSentry()` — PII scrubbing (stays in main.dart per spec)
- Lines 68-74: `_beforeSendTransaction()` — transaction scrubbing (stays)
- Lines 81-118: `main()` — SentryFlutter.init wrapper (stays)
- Lines 120-186: `_runApp()` — consent factory, consent load, Sentry gate, auth listener, AppRouter, runApp
- Lines 188-222: `ConstructionInspectorApp` widget

**What moves to AppBootstrap:**
- Lines 128-134: `createConsentAndSupportProviders(...)` call
- Lines 142-148: consent load + Sentry gate
- Lines 155-169: auth listener (consent clear on sign-out, deferred audit on sign-in)
- Lines 173-176: AppRouter construction
- Lines 204-209: Provider splicing (consent/support into MultiProvider)

### 4. `lib/main_driver.dart` (121 lines → ~30)

**Duplicated code with main.dart (lines 68-107):**
- Lines 69-75: `createConsentAndSupportProviders(...)` — identical
- Lines 76-78: consent load + Sentry gate — identical
- Lines 84-98: auth listener — identical
- Lines 104-107: AppRouter construction — identical

All → `AppBootstrap.configure(deps, options)`

### 5. `lib/features/sync/di/sync_providers.dart` (285 lines → ~60)

**Business logic to extract:**
| Content | Lines | Destination |
|---------|-------|-------------|
| Auto-enrollment on assignment pull | 91-187 | `SyncEnrollmentService.enrollAssignedProjects()` |
| FCM initialization | 194-198 | Already in `FcmHandler.initialize()` — call stays |
| Lifecycle observer wiring | 200-226 | Already in `SyncLifecycleManager` — wiring stays |
| Stale comment "pure code-motion" | 32 | Delete |

### 6. Files to DELETE

| File | Lines | Reason |
|------|-------|--------|
| `lib/driver_main.dart` | 10 | Stale `flutter_driver` shim (just calls `enableFlutterDriverExtension()` + `app.main()`) |
| `lib/test_harness.dart` | 136 | Port concept to DriverServer `/harness` endpoint |
| `pubspec.yaml` flutter_driver dep | 1 | No longer needed |

### 7. Files to CREATE

| File | Est. Lines | Purpose |
|------|------------|---------|
| `lib/core/di/core_deps.dart` | ~80 | CoreDeps with supabaseClient + static `create(InitOptions)` |
| `lib/core/di/init_options.dart` | ~20 | InitOptions class |
| `lib/core/di/app_bootstrap.dart` | ~100 | Post-init wiring (consent, auth listener, router, Sentry gate) |
| `lib/core/router/app_redirect.dart` | ~220 | Redirect matrix class |
| `lib/core/router/scaffold_with_nav_bar.dart` | ~200 | Shell widget + banners |
| `lib/features/sync/application/sync_enrollment_service.dart` | ~120 | Enrollment/unenrollment business logic |
| `lib/features/sync/di/sync_initializer.dart` | ~50 | Sync init orchestration (thin) |
| `lib/core/driver/test_db_factory.dart` | ~30 | In-memory DB setup (from test_harness concept) |

---

## Dependent Files (callers of changed symbols)

### AppDependencies consumers
- `lib/main.dart` — creates & passes to `buildAppProviders()` and `ConstructionInspectorApp`
- `lib/main_driver.dart` — same pattern
- `lib/core/di/app_providers.dart` — `buildAppProviders(AppDependencies deps)`

### AppRouter consumers
- `lib/main.dart:173-176` — constructs AppRouter
- `lib/main_driver.dart:104-107` — constructs AppRouter
- `lib/core/di/app_initializer.dart:751` — constructs AppRouter (dead — audit finding)
- `test/core/router/form_screen_registry_test.dart` — may reference router

### SyncProviders consumers
- `lib/core/di/app_initializer.dart:686-692` — calls `SyncProviders.initialize()`
- `lib/core/di/app_providers.dart:130-136` — calls `SyncProviders.providers()`

### ScaffoldWithNavBar consumers
- `lib/core/router/app_router.dart:428` — shell builder creates `ScaffoldWithNavBar(child: child)`

### ConsentProvider consumers (redirect-related)
- `lib/core/router/app_router.dart:240-244` — consent gate reads `_consentProvider.hasConsented`
- `lib/main.dart:142-148` — loads consent state, sets Sentry gate
- `lib/main_driver.dart:76-78` — same

### Supabase.instance.client consumers (outside app_initializer — NOT changing):
- `lib/shared/datasources/base_remote_datasource.dart:11` — getter
- `lib/features/auth/di/auth_providers.dart:57`
- `lib/features/settings/di/consent_support_factory.dart:46`
- `lib/features/sync/di/sync_providers.dart:58`
- `lib/features/sync/application/sync_orchestrator.dart:225,384`
- `lib/features/sync/application/background_sync_handler.dart:49,151`
- (Spec scopes CoreDeps to app_initializer only — these stay as-is)

---

## Test Files

### Existing (may need import updates)
- `test/core/router/form_screen_registry_test.dart` — verify no breakage from router split

### New (12 files per spec)
1. `test/core/di/app_initializer_test.dart`
2. `test/core/di/core_deps_test.dart`
3. `test/core/di/app_bootstrap_test.dart`
4. `test/core/router/app_redirect_test.dart`
5. `test/core/router/app_router_test.dart`
6. `test/core/router/scaffold_with_nav_bar_test.dart`
7. `test/features/sync/di/sync_providers_test.dart`
8. `test/features/sync/application/sync_enrollment_service_test.dart`
9. `test/features/sync/application/background_sync_handler_test.dart`
10. `test/core/di/entrypoint_equivalence_test.dart`
11. `test/core/di/sentry_integration_test.dart`
12. `test/core/di/analytics_integration_test.dart`

---

## Dead Code to Remove

| Item | Location | Reason |
|------|----------|--------|
| `appRouter` field in AppDependencies | `app_initializer.dart:274` | Audit finding — AppRouter is created after init, not during |
| AppRouter construction in initialize() | `app_initializer.dart:751` | Dead — main.dart creates its own AppRouter with ConsentProvider |
| "Pure code-motion" comment | `sync_providers.dart:32` | Stale comment |
| `consent_support_factory.dart` | `lib/features/settings/di/` | Evaluate — may be absorbed into AppBootstrap |

---

## Data Flow Diagram

```
main.dart / main_driver.dart
  │
  ├─ [main.dart only] SentryFlutter.init(appRunner: ...)
  ├─ [driver only] DriverServer.start()
  │
  └─ AppInitializer.initialize(InitOptions)
       │
       ├─ Phase 1: CoreDeps.create(options)
       │    ├─ PreferencesService.init()
       │    ├─ Aptabase init (consent-gated)
       │    ├─ Logger init
       │    ├─ DatabaseService init
       │    ├─ Supabase.initialize()  ← stores client in CoreDeps
       │    ├─ Firebase.initializeApp()
       │    ├─ TesseractInitializer.initialize()
       │    └─ Returns CoreDeps(dbService, prefs, supabaseClient, ...)
       │
       ├─ Phase 2: Feature initializers (all receive CoreDeps)
       │    ├─ Datasource + Repository construction (20+ instances)
       │    ├─ AuthInitializer → AuthDeps (authService, authProvider, appConfigProvider)
       │    ├─ ProjectInitializer → ProjectDeps (12 fields)
       │    ├─ EntryInitializer → EntryDeps (7 fields)
       │    ├─ FormInitializer → FormDeps (4 fields)
       │    └─ FeatureInitializer → FeatureDeps (11 fields)
       │
       ├─ Phase 3: SyncProviders.initialize() → SyncDeps
       │
       ├─ Phase 4: Lifecycle wiring (version check, auth listener, project settings)
       │
       └─ Returns AppDependencies (no appRouter)
            │
            └─ AppBootstrap.configure(deps, options)
                 ├─ createConsentAndSupportProviders()
                 ├─ consentProvider.loadConsentState()
                 ├─ enableSentryReporting() if consented
                 ├─ Auth listener (consent clear, deferred audit)
                 ├─ AppRouter(authProvider, consentProvider, appConfigProvider) ← ALL REQUIRED
                 └─ Returns BootstrapResult(appRouter, consentProvider, supportProvider)
                      │
                      └─ runApp(ConstructionInspectorApp(
                           providers: buildAppProviders(deps),
                           appRouter, consentProvider, supportProvider
                         ))
```

---

## Blast Radius Summary

| Category | Count |
|----------|-------|
| Files to create | 8 source + 12 test = 20 |
| Files to modify | 10 |
| Files to delete | 2 + 1 pubspec line |
| Direct symbols changed | ~25 |
| Dependent files (import updates) | ~5 |
| Test files (new) | 12 |
| Supabase.instance.client replacements | 7 (in app_initializer only) |
