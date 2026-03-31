# Application Wiring, Startup, Routing — Audit Fix Spec

**Date:** 2026-03-30
**Status:** Approved
**Audit Source:** `.claude/code-reviews/2026-03-30-preprod-audit-layer-application-wiring-startup-routing-codex-review.md`
**Prior Specs:** `2026-03-29-clean-architecture-refactor-spec.md`, `2026-03-29-pre-release-hardening-spec.md`
**Execution Strategy:** Bottom-up (foundations → structural splits → cleanup → tests)

---

## Overview

### Purpose
Fix 11 confirmed findings from the Application Wiring/Startup/Routing preprod audit layer. These are residual defects from the March 29 clean-architecture refactor and March 29 pre-release hardening implementation — the refactor relocated complexity rather than decomposing it, and the hardening layer introduced entrypoint duplication that wasn't reconciled.

### Scope

**In scope:**
- Decompose `AppInitializer` (891 lines, 101 imports) into feature-scoped initializers
- Split `app_router.dart` (932 lines) into router/redirect/scaffold
- Consolidate `main.dart`/`main_driver.dart` entrypoint duplication
- Introduce `CoreDeps.supabaseClient` — eliminate all 7 `Supabase.instance.client` direct accesses
- Extract SyncProviders business logic into application-layer homes
- Delete `driver_main.dart`, `test_harness.dart`, remove `flutter_driver` dep
- Port test_harness screen/flow registry into DriverServer
- Remove dead `appRouter` field from `AppDependencies`
- Make all AppRouter provider dependencies required (fix silent consent bypass)
- Fix stale comments ("pure code-motion" in SyncProviders)
- Full unit test coverage: 12 test files for all decomposed modules

**Out of scope:**
- Sync engine logic changes (wiring only)
- Database schema changes
- UI/presentation changes
- New features or new providers
- Existing test modifications (beyond import updates for renames)

### Success Criteria
- [ ] `AppInitializer.initialize()` under 80 lines (currently 463)
- [ ] `app_router.dart` under 120 lines (currently 932)
- [ ] `main.dart` under 50 lines (currently 223)
- [ ] `main_driver.dart` under 40 lines (currently 121)
- [ ] Zero `Supabase.instance.client` outside `CoreDeps` resolution
- [ ] Zero optional/nullable provider dependencies in AppRouter
- [ ] Zero business logic in any `di/` file
- [ ] `driver_main.dart` and `test_harness.dart` deleted, `flutter_driver` removed from pubspec
- [ ] All new modules have corresponding test files (12 files)
- [ ] Sentry and Aptabase verified initializing and functional
- [ ] App compiles, runs, and passes existing test suite identically

---

## Approach Selected: Bottom-Up Feature-Scoped Decomposition

**Why**: The findings have real dependency chains. Feature initializers must exist before `AppInitializer` can delegate to them. `CoreDeps.supabaseClient` must exist before feature initializers can receive it. The router split is independent but entrypoint consolidation depends on both. Building bottom-up means each phase lands on stable ground.

**Rejected alternatives:**
- **Top-Down**: Visible wins early but requires revisiting entrypoint wiring when feature initializers are introduced later
- **Parallel Tracks**: Fastest wall-clock but merge phase is complex — both streams change how the app starts up

---

## Target Architecture

### File Structure

```
lib/core/di/
├── app_initializer.dart          # Thin orchestrator (~80 lines)
├── app_providers.dart            # Composes feature provider lists (adds consent/support)
├── app_bootstrap.dart            # NEW: post-init wiring (consent, auth listener, router)
├── init_options.dart             # NEW: InitOptions class (driver mode, overrides)
└── core_deps.dart                # NEW: CoreDeps with supabaseClient, dbService, prefs

lib/core/router/
├── app_router.dart               # GoRouter construction (~100 lines)
├── app_redirect.dart             # NEW: redirect matrix (~200 lines)
└── scaffold_with_nav_bar.dart    # NEW: shell widget + banners (~185 lines)

lib/features/<feature>/di/
├── <feature>_providers.dart      # Existing — unchanged
└── <feature>_initializer.dart    # NEW: per-feature async init, receives CoreDeps

lib/features/sync/
├── di/
│   ├── sync_providers.dart       # Slimmed to pure wiring (~60 lines)
│   └── sync_initializer.dart     # NEW: orchestration sequence only
├── application/
│   ├── sync_enrollment_service.dart  # NEW: extracted from sync_providers
│   └── ... (existing files unchanged)
```

### Initialization Flow

```
main.dart / main_driver.dart
  │
  ├── [driver only] DriverServer.start()
  │
  └── AppInitializer.initialize(options)
        │
        ├── Phase 1: CoreDeps.create(options)
        │     └── prefs, db, supabaseClient, permissions, analytics, logging
        │
        ├── Phase 2: Feature initializers (receive CoreDeps)
        │     ├── AuthInitializer.create(coreDeps) → AuthDeps
        │     ├── ProjectInitializer.create(coreDeps, authDeps) → ProjectDeps
        │     ├── EntryInitializer.create(coreDeps, ...) → EntryDeps
        │     ├── FormInitializer.create(coreDeps) → FormDeps
        │     └── ... (each feature returns typed deps)
        │
        ├── Phase 3: SyncInitializer.create(coreDeps, authDeps, ...)
        │     └── orchestrator, lifecycleManager (wiring only)
        │
        ├── Phase 4: AppBootstrap.configure(deps, options)
        │     ├── consent/support provider creation
        │     ├── auth listener wiring
        │     ├── Sentry consent gate
        │     └── AppRouter construction (all providers required)
        │
        └── Returns fully-assembled AppDependencies
              │
              └── runApp(MultiProvider(buildAppProviders(deps), ...))
```

### Key Design Decisions

1. **CoreDeps is the DI root** — `supabaseClient`, `dbService`, `preferencesService` live here. Every feature initializer receives `CoreDeps` as its first parameter. No global singleton access anywhere downstream.

2. **Feature initializers are static factory methods** — `AuthInitializer.create(coreDeps)` returns `AuthDeps`. No classes to instantiate, no state to manage. Pure construction functions.

3. **AppBootstrap handles post-init wiring** — Consent providers, auth listeners, Sentry consent gate, and router construction all live in one place. Both `main.dart` and `main_driver.dart` get identical behavior through `InitOptions`.

4. **AppRouter takes all providers as required** — No nullable `ConsentProvider?`, no try-catch `context.read<AppConfigProvider>()`. If a provider is missing, it's a compile-time error, not a silent runtime bypass.

5. **Provider graph assembled in one place** — `buildAppProviders(deps)` returns everything including consent/support. No second assembly step in the app widget.

6. **Sentry and Aptabase always on** — Consent is mandatory company policy. Consent gate is blocking and non-skippable. No conditional SDK initialization — both initialize unconditionally in AppBootstrap.

---

## Router Split

### app_router.dart (~100 lines)

Composition only — constructs GoRouter, delegates redirect to `AppRedirect`, delegates shell to `ScaffoldWithNavBar`.

```dart
AppRouter({
  required AuthProvider authProvider,
  required ConsentProvider consentProvider,
  required AppConfigProvider appConfigProvider,
})
```

All three providers **required**. No nullable, no try-catch fallback. `refreshListenable` always merges all three.

### app_redirect.dart (~200 lines)

New class `AppRedirect` owns the full redirect matrix. Constructor receives the same three providers. Single public method:

```dart
String? redirect(BuildContext context, GoRouterState state)
```

The 10+ gate sequence (in current order):
1. Password recovery deep link
2. Auth check (unauthenticated → login)
3. Force update gate
4. Force reauth gate
5. Consent gate
6. Onboarding gate
7. Profile completion gate
8. Pending approval gate
9. Admin-only route guard
10. Project-required route guard

Each gate is a private method for readability. No silent skips — if a provider is missing, it's a compile error because all are required in the constructor.

### scaffold_with_nav_bar.dart (~185 lines)

Extracted as a standalone `StatelessWidget`. Receives providers via `context.watch`/`context.read` from the widget tree (correct for presentation-layer reads).

Contains:
- Bottom navigation bar with index calculation
- Project switcher in app bar
- Banner stack: SyncRetryBanner, VersionBanner, StaleConfigWarning, OfflineBanner, ExtractionBanner
- TestingKeys assignments

### Import Cleanup

After split:
- `app_router.dart`: ~10 imports
- `app_redirect.dart`: ~8 imports
- `scaffold_with_nav_bar.dart`: ~22 imports (banner/widget/provider imports move here)

---

## Entrypoint Consolidation

### main.dart (~40 lines, down from 223)

Sentry wrapper + initialize + runApp. PII scrubbing callbacks (`_beforeSendSentry`, `_beforeSendTransaction`) stay here — Sentry-specific, not app wiring. `ConstructionInspectorApp` becomes a thin `MaterialApp.router` wrapper with no provider splicing.

### main_driver.dart (~30 lines, down from 121)

DriverServer start + initialize with `InitOptions(isDriverMode: true)` + runApp. No Sentry wrapper. No duplicated auth listener, consent wiring, or router construction.

### InitOptions

```dart
class InitOptions {
  final bool isDriverMode;                    // skips Sentry, swaps photo service
  final PhotoService? photoServiceOverride;   // TestPhotoService for driver
  final SupabaseClient? supabaseClientOverride; // mock for tests

  const InitOptions({
    this.isDriverMode = false,
    this.photoServiceOverride,
    this.supabaseClientOverride,
  });
}
```

### What Moves Where

| Currently in main.dart/main_driver.dart | Moves to |
|----------------------------------------|----------|
| Consent/support provider creation | `AppBootstrap.configure()` |
| Auth listener (sign-out consent clear, sign-in audit) | `AppBootstrap.configure()` |
| Sentry consent gate (`enableSentryReporting`) | `AppBootstrap.configure()` |
| AppRouter construction | `AppBootstrap.configure()` |
| Provider graph assembly (consent/support splice) | `buildAppProviders()` |

### Deletions

| File | Action |
|------|--------|
| `lib/driver_main.dart` | Delete entirely |
| `lib/test_harness.dart` | Delete entirely |
| `pubspec.yaml` flutter_driver dep | Remove |

### Test Harness Migration

`test_harness.dart`'s screen/flow registry and in-memory DB concept gets ported into DriverServer:
- `DriverServer` gains a `/harness` endpoint accepting JSON config
- Screen registry and flow registry move to `lib/core/driver/`
- In-memory DB setup becomes `lib/core/driver/test_db_factory.dart`

---

## SyncProviders Extraction

### What Moves Where

| Currently in sync_providers.dart | Lines | Destination |
|----------------------------------|-------|-------------|
| Assignment auto-enrollment logic | 91-140 | `SyncEnrollmentService.enrollAssignedProjects()` (NEW) |
| Unassignment transaction logic | 141-187 | `SyncEnrollmentService.unenrollRemovedProjects()` (NEW) |
| FCM initialization | 189-198 | `FcmHandler.initialize()` (EXISTS — expand) |
| Lifecycle observer (inactivity, config refresh, force-reauth) | 200-223 | `SyncLifecycleManager.configureAuthLifecycle()` (EXISTS — expand) |
| "Pure code-motion" stale comment | 32 | Delete |

### New File: sync_enrollment_service.dart

Location: `lib/features/sync/application/sync_enrollment_service.dart`

```dart
class SyncEnrollmentService {
  final DatabaseService _db;
  final SyncOrchestrator _orchestrator;

  Future<void> enrollAssignedProjects(String userId) async { ... }
  Future<void> unenrollRemovedProjects(String userId) async { ... }
}
```

### sync_providers.dart After (~60 lines)

Pure wiring only. `SyncProviders.initialize()` calls `SyncInitializer.create()` which orchestrates: create orchestrator → create lifecycle manager → call enrollment → call FCM init → call lifecycle configuration. `SyncProviders.providers()` returns the provider list (unchanged).

---

## Testing Strategy

### New Test Files (12 total)

| # | File | Tests | Priority |
|---|------|-------|----------|
| 1 | `test/core/di/app_initializer_test.dart` | Orchestrator calls initializers in correct order; returns fully-populated AppDependencies; works with mock SupabaseClient via InitOptions; driver mode swaps photo service | HIGH |
| 2 | `test/core/di/core_deps_test.dart` | CoreDeps.create() with real DB + mock Supabase; with null Supabase (offline-only); all fields populated | HIGH |
| 3 | `test/core/di/app_bootstrap_test.dart` | Consent/support providers created; auth listener wired (sign-out clears consent, sign-in triggers audit); AppRouter constructed with all required providers; Sentry consent gate respects consent state | HIGH |
| 4 | `test/core/router/app_redirect_test.dart` | Each of the 10+ redirect gates independently; gate ordering; all providers required — no silent bypass; password recovery deep link; unauthenticated → login; force update blocks; consent gate blocks | HIGH |
| 5 | `test/core/router/app_router_test.dart` | GoRouter construction; route paths resolve; refreshListenable merges all providers; initial location override | MED |
| 6 | `test/core/router/scaffold_with_nav_bar_test.dart` | Bottom nav index calculation; banner visibility per state; project switcher conditional | MED |
| 7 | `test/features/sync/di/sync_providers_test.dart` | initialize() calls services in correct order; providers() returns correct list; no business logic in module | MED |
| 8 | `test/features/sync/application/sync_enrollment_service_test.dart` | enrollAssignedProjects inserts correct records; unenrollRemovedProjects transaction; notification queueing | MED |
| 9 | `test/features/sync/application/background_sync_handler_test.dart` | WorkManager registration; callback dispatches sync; handles missing DB | MED |
| 10 | `test/core/di/entrypoint_equivalence_test.dart` | buildAppProviders() returns identical provider types for production and driver mode | MED |
| 11 | `test/core/di/sentry_integration_test.dart` | Sentry initializes during bootstrap; PII scrubbing in beforeSend; DSN from env; crash capture produces valid event | HIGH |
| 12 | `test/core/di/analytics_integration_test.dart` | Aptabase initializes during bootstrap; trackEvent fires; analytics disabled in driver mode | MED |

### Testing Approach

- **Feature initializers**: Static factory methods taking `CoreDeps` — tests pass mock `SupabaseClient` and real in-memory `DatabaseService`
- **Redirect matrix**: `AppRedirect` is a pure class — construct with mock providers, set state, assert redirect path
- **ScaffoldWithNavBar**: Standard widget tests with `pumpWidget`, mock providers in tree
- **Entrypoint equivalence**: Calls `buildAppProviders()` with both mode deps, compares provider type lists
- **Sentry/Aptabase**: Verify initialization and our integration seams (PII scrubbing, event capture)

### What We Don't Test
- Sentry/Aptabase SDK internals
- Existing feature provider logic (already covered)
- Existing sync engine/adapter tests (already 60+ files)
- Actual Supabase network calls

---

## Security Implications

### Security Positive Changes

| Change | Security Impact |
|--------|----------------|
| AppRouter providers all required | Eliminates silent consent bypass — missing provider = compile error |
| Supabase client via CoreDeps | Eliminates ambient global state — testable composition root |
| Single auth listener location | Eliminates drift risk — consent-clear-on-signout in one place |
| Redirect matrix in dedicated file | Auditability — 10+ security gates in one file with 100% test coverage |

### Security Invariants Preserved

| Invariant | Current Location | After Refactor |
|-----------|-----------------|----------------|
| Consent gate blocks all app access | `app_router.dart:240-245` | `app_redirect.dart` — required ConsentProvider |
| Sign-out clears consent state | `main.dart:157` + `main_driver.dart:86` | `AppBootstrap.configure()` — single auth listener |
| Force-reauth on config flag | `app_router.dart:215-230` (try-catch) | `app_redirect.dart` — required AppConfigProvider, no try-catch |
| Inactivity timeout forces sign-out | `sync_providers.dart:200-210` | `SyncLifecycleManager.configureAuthLifecycle()` |
| Assignment enrollment scoped to user | `sync_providers.dart:91-140` | `SyncEnrollmentService.enrollAssignedProjects()` |
| PII scrubbing before Sentry send | `main.dart:28-66` | Stays in `main.dart` |

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Redirect gate ordering changes during extraction | `app_redirect_test.dart` verifies exact gate sequence |
| Auth listener lost during consolidation | `app_bootstrap_test.dart` verifies sign-out clears consent |
| SyncEnrollmentService loses transaction atomicity | `sync_enrollment_service_test.dart` verifies transaction wrapping |
| InitOptions.isDriverMode accidentally ships | 4-layer security: build.ps1 blocks, compile-time const, kReleaseMode, separate entrypoint |

### Not Affected
- No Supabase schema, RLS, or migration changes
- No new endpoints or data flows
- No changes to encryption, auth tokens, or session management
- All changes are client-side wiring only

---

## Migration/Cleanup

### New Files (9 source + 12 test)

| File | Purpose | Est. Lines |
|------|---------|------------|
| `lib/core/di/core_deps.dart` | CoreDeps class with supabaseClient, dbService, prefs, permissions | ~60 |
| `lib/core/di/init_options.dart` | InitOptions class | ~20 |
| `lib/core/di/app_bootstrap.dart` | Post-init wiring (consent, auth listener, router) | ~80 |
| `lib/core/router/app_redirect.dart` | Redirect matrix | ~200 |
| `lib/core/router/scaffold_with_nav_bar.dart` | Shell widget + banners | ~185 |
| `lib/features/sync/application/sync_enrollment_service.dart` | Enrollment/unenrollment logic | ~100 |
| `lib/features/sync/di/sync_initializer.dart` | Sync initialization orchestration | ~40 |
| `lib/core/driver/test_db_factory.dart` | In-memory DB setup (from test_harness) | ~30 |
| 12 test files | Per testing strategy | ~1200 total |

### Modified Files

| File | Change | Lines After |
|------|--------|------------|
| `lib/core/di/app_initializer.dart` | Thin orchestrator | ~80 (from 891) |
| `lib/core/di/app_providers.dart` | Add consent/support to tier list | ~150 (from 139) |
| `lib/core/router/app_router.dart` | Composition only | ~100 (from 932) |
| `lib/main.dart` | Sentry wrapper + initialize + runApp | ~40 (from 223) |
| `lib/main_driver.dart` | DriverServer + initialize with options + runApp | ~30 (from 121) |
| `lib/features/sync/di/sync_providers.dart` | Pure wiring only | ~60 (from 285) |
| `lib/features/sync/application/fcm_handler.dart` | Absorb FCM init | minor |
| `lib/features/sync/application/sync_lifecycle_manager.dart` | Absorb lifecycle wiring | minor |
| `lib/core/driver/driver_server.dart` | Gain /harness endpoint | ~50 added |
| `pubspec.yaml` | Remove flutter_driver | -1 line |

### Deleted Files

| File | Reason |
|------|--------|
| `lib/driver_main.dart` | Stale flutter_driver shim |
| `lib/test_harness.dart` | Ported to DriverServer |

### Dead Code Removal

- `appRouter` field, constructor param, and `copyWith` entry from `AppDependencies`
- `AppRouter` construction at `app_initializer.dart:751`
- "Pure code-motion" comment at `sync_providers.dart:32`
- `consent_support_factory.dart` — evaluate if absorbed into AppBootstrap makes it deletable

### Net Impact

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| New source files | — | 9 | +9 |
| New test files | — | 12 | +12 |
| Deleted files | — | 2 | -2 |
| `app_initializer.dart` | 891 lines | ~80 | -811 |
| `app_router.dart` | 932 lines | ~100 | -832 |
| `main.dart` | 223 lines | ~40 | -183 |

---

## Decisions Log

| Decision | Chosen | Rejected | Rationale |
|----------|--------|----------|-----------|
| AppInitializer decomposition | Feature-scoped initializers | Phased modules, Private methods | Completes original spec vision, testable boundaries per feature |
| AppRouter split | Three-file split | Four-file, Two-file | Addresses core issue without over-splitting route table |
| Entrypoint consolidation | Extend AppInitializer | Shared bootstrap function, Extract shared pieces | Achieves "main.dart under 50 lines", single source of truth |
| Supabase DI | CoreDeps first-class field | Local variable, Injectable param | Good architecture early prevents growing debt |
| SyncProviders extraction | Existing application layer | Separate initializer file | Business logic has natural existing homes |
| Stale entrypoints | Delete both, port to DriverServer | Keep test_harness, Leave as-is | Clean sweep, single testing stack |
| Test coverage | Full unit coverage (12 files) | Critical-path only, Integration-focused | All decomposed modules tested, 100% redirect branch coverage |
| Execution strategy | Bottom-up | Top-down, Parallel tracks | Deep dependency chains — build on stable ground |
| Sentry/Aptabase | Always on, consent mandatory | Conditional gating | Company policy — blocking consent gate, no opt-out |
