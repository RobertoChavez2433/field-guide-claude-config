# Wiring And Routing Audit

Date: 2026-03-30
Layer: application startup, composition root, router, app-wide wiring

## Findings

### 1. High | Confirmed
Duplicate router composition is still present after the DI refactor.

Evidence:

- `lib/core/di/app_initializer.dart:267-285` defines `AppDependencies.appRouter`.
- `lib/core/di/app_initializer.dart:751` creates `final appRouter = AppRouter(authProvider: authProvider);`
- `lib/core/di/app_initializer.dart:820` returns that router inside `AppDependencies`.
- `lib/main.dart:173-181` discards `deps.appRouter` and constructs a second `AppRouter`.
- `lib/main_driver.dart:100-107` explicitly documents that `deps.appRouter` is unusable because it lacks `consentProvider`, then constructs another one.

Why this matters:

- Startup has two router construction paths, not one source of truth.
- `AppDependencies.appRouter` is effectively dead state.
- Future route/guard changes can land in one path and silently miss the other.

Classification: stale post-refactor drift.

### 2. High | Confirmed
The refactor moved the startup god object from `main.dart` into `AppInitializer`, but did not materially reduce startup coupling.

Evidence:

- `lib/core/di/app_initializer.dart` is `815` lines.
- It currently owns logging bootstrap, analytics bootstrap, SQLite init, OCR init, Supabase init, Firebase init, repository creation, form seeding, router creation, sync creation, background sync registration, auth lifecycle hooks, app-config checks, and feature service creation.

Why this matters:

- Startup behavior is still centralized in one large mutable orchestration file.
- The file is difficult to regression-test because responsibilities are mixed.
- Cleanup work in one domain now has a large blast radius through startup.

Classification: architecture debt that survived the March 29 refactor.

### 3. Medium | Confirmed
`SyncProviders.initialize()` is no longer a narrow DI module; it now embeds business logic, local transactions, lifecycle wiring, FCM wiring, and UI-facing notification flow.

Evidence:

- `lib/features/sync/di/sync_providers.dart:32` still describes the file as "Pure code-motion refactor".
- `lib/features/sync/di/sync_providers.dart:91-187` contains assignment auto-enrollment and unassignment transaction logic.
- `lib/features/sync/di/sync_providers.dart:189-221` also owns FCM initialization and lifecycle observer registration.

Why this matters:

- Wiring and business behavior are coupled in the same module.
- That weakens the value of the DI split and makes sync startup harder to reason about and test in isolation.

Classification: drift introduced during recent sync/DI consolidation.

### 4. Medium | Confirmed
Critical startup/routing paths are under-tested relative to their complexity.

Evidence:

- No direct test files exist for:
  - `test/core/di/app_initializer_test.dart`
  - `test/core/router/app_router_test.dart`
  - `test/features/sync/di/sync_providers_test.dart`
  - `test/features/sync/application/background_sync_handler_test.dart`

Why this matters:

- The green test suite does not exercise the highest-risk startup composition logic.
- Recent regressions in consent gating and startup routing are more likely to slip through comments/manual reasoning than executable tests.

### 5. Medium | Confirmed
`AppDependencies` still exposes compatibility accessors and a router field that the runtime no longer uses.

Evidence:

- `lib/core/di/app_initializer.dart:288-350` keeps a large compatibility surface.
- `lib/core/di/app_initializer.dart:350` preserves `appRouter` in `copyWith`, despite `main.dart` and `main_driver.dart` building their own routers.

Why this matters:

- The compatibility layer is carrying dead or ambiguous responsibilities.
- It increases the odds that future code reads the wrong dependency source.

### 6. Medium | Confirmed
`AppRouter` still has a mixed dependency contract: some gates are constructor-injected, while others depend on provider lookup from the widget tree.

Evidence:

- `lib/core/router/app_router.dart:87-94` makes `ConsentProvider` optional for backward compatibility with tests.
- `lib/core/router/app_router.dart:154-156` changes redirect refresh behavior depending on whether that optional provider was supplied.
- `lib/core/router/app_router.dart:215-230` reads `AppConfigProvider` via `context.read` inside the redirect callback and catches missing-provider failures by logging them.

Why this matters:

- Routing is not fully defined by the composition root; some route behavior still depends on provider presence deeper in the tree.
- Tests can bypass parts of the redirect matrix simply by omitting providers, which weakens confidence in routing coverage.
- This mixed contract is one reason `main.dart` and `main_driver.dart` had to compensate with bespoke router construction.

### 7. Medium | Confirmed
The top-level provider graph is still assembled in multiple places instead of one canonical composition root.

Evidence:

- `lib/core/di/app_providers.dart:37-137` builds the main provider list from `AppDependencies`.
- `lib/main.dart:178-183` passes that list into `ConstructionInspectorApp`.
- `lib/main.dart:204-209` then adds `consentProvider` and `supportProvider` manually in a second provider assembly step inside the app widget.

Why this matters:

- The full runtime provider graph is not represented in one place.
- Reviewing or testing app-wide wiring requires reading both the DI module and the app widget entrypoint.
- This weakens the value of `buildAppProviders()` as the apparent single source of truth.

### 8. Medium | Confirmed
`main.dart` and `main_driver.dart` still duplicate the consent/auth lifecycle wiring rather than sharing one entrypoint-safe bootstrap path.

Evidence:

- `lib/main.dart:127-169` builds consent/support providers, loads consent state, toggles Sentry consent, and attaches an auth listener for sign-in/sign-out side effects.
- `lib/main_driver.dart:68-98` repeats the same sequence with a "mirror the auth listener" comment.

Why this matters:

- Behavioral parity between normal mode and driver mode now depends on manual duplication.
- Future changes to consent, telemetry, or auth-lifecycle side effects can land in one entrypoint and silently miss the other.
- This is wiring drift, not business logic, so it belongs in the composition root rather than being duplicated at the edge.

### 9. High | Confirmed
`AppInitializer` still bypasses the DI boundary and pulls `Supabase.instance.client` directly in several startup paths, so the refactor did not actually make the composition root singleton-free.

Evidence:

- `lib/core/di/app_initializer.dart:465` says the project lifecycle service should use an injected client rather than the singleton.
- `lib/core/di/app_initializer.dart:468` still passes `Supabase.instance.client` directly into `ProjectLifecycleService`.
- `lib/core/di/app_initializer.dart:527` constructs `ProjectRemoteDatasourceImpl(Supabase.instance.client)`.
- `lib/core/di/app_initializer.dart:548` constructs `CompanyMembersRepository(Supabase.instance.client)`.
- `lib/core/di/app_initializer.dart:588` constructs `UserProfileRemoteDatasource(Supabase.instance.client)`.
- `lib/core/di/app_initializer.dart:597` constructs `AuthService(Supabase.instance.client)`.
- `lib/core/di/app_initializer.dart:642` passes `Supabase.instance.client` directly into `AuthProvider`.
- `lib/core/di/app_initializer.dart:679` constructs `AppConfigRepository(Supabase.instance.client)`.

Why this matters:

- The startup layer still has hidden global runtime dependencies even after the DI split.
- Reusing the initializer in tests, alternate runtimes, or stricter harnesses still depends on ambient global Supabase state.
- The comments and actual ownership model now disagree, which is an integrity problem in the composition root itself.

Classification: stale post-refactor DI drift.

### 10. Medium | Confirmed
The entrypoint contract is still split across the active HTTP-driver bootstrap and older `flutter_driver` bootstraps, leaving a stale startup surface in the repo.

Evidence:

- `lib/main_driver.dart:8` documents the current driver entrypoint as `flutter run --target=lib/main_driver.dart --dart-define=DEBUG_SERVER=true`.
- `lib/main_driver.dart:57-66` starts `DriverServer`, which is the current driver-mode bootstrap behavior.
- `lib/driver_main.dart:2-7` is still a separate `flutter_driver` entrypoint that only enables `enableFlutterDriverExtension()` and forwards to production `main()`.
- `lib/test_harness.dart:14-18` is a second `flutter_driver`-based bootstrap that also enables `enableFlutterDriverExtension()`.
- `pubspec.yaml:119` still carries `flutter_driver` as a dev dependency.
- `.claude/rules/testing/patrol-testing.md:8-9` still names both `lib/test_harness.dart` and `lib/driver_main.dart` as active test files.
- Repo search found no active `.github`, `.vscode`, or README references that target `lib/driver_main.dart`; current active planning references center on `lib/main_driver.dart` and `lib/test_harness.dart`.

Why this matters:

- There is no single authoritative answer for which non-production app bootstrap is current.
- `lib/driver_main.dart` is now primarily compatibility surface area around an older driving stack, not a clearly maintained path.
- Keeping multiple overlapping bootstraps makes it easier for future test or tooling changes to land on the wrong entrypoint.

Classification: stale legacy entrypoint left behind after the driver/testing migration.

### 11. Medium | Confirmed
`app_router.dart` is still a hybrid composition file that mixes redirect policy, route registration, shell chrome, sync/config banners, and testing-key ownership in one place.

Evidence:

- `lib/core/router/app_router.dart` is `876` lines with `39` imports.
- `lib/core/router/app_router.dart:147-343` owns the top-level redirect matrix.
- `lib/core/router/app_router.dart:425-745` owns the route table and route-specific extra parsing.
- `lib/core/router/app_router.dart:747-876` also owns `ScaffoldWithNavBar`.
- `lib/core/router/app_router.dart:770-845` wires `SyncProvider`, `AppConfigProvider`, retry banners, stale-data banners, and offline banners into the shell.
- `lib/core/router/app_router.dart:765` injects `ProjectSwitcher` into the app bar.
- `lib/core/router/app_router.dart:795` and `lib/core/router/app_router.dart:804` render `VersionBanner` and `StaleConfigWarning`.
- `lib/core/router/app_router.dart:870-872` renders `ExtractionBanner` and assigns `TestingKeys.bottomNavigationBar`.
- `lib/core/router/app_router.dart:14-39` imports broad shared and feature presentation barrels directly into the router layer.

Why this matters:

- Route-policy changes and shell-UI changes share one large file and one import surface.
- This increases blast radius for startup and navigation work and makes router integrity harder to verify in isolation.
- It also keeps the routing layer tightly coupled to broad presentation barrels and shared compatibility surfaces rather than a narrower navigation contract.

Classification: structural integrity debt that survived the routing refactor.

## Coverage Gaps

- No direct tests for startup composition, router redirect matrix, or background sync bootstrap.
- The existing suite passing does not verify that the composed production app uses the same routing/wiring objects that `AppInitializer` constructs.
- No direct router tests cover the combined password-recovery, force-update, force-reauth, onboarding, and consent redirect matrix in one place.
- No direct test verifies that `main.dart` and `main_driver.dart` keep equivalent consent/router/bootstrap behavior.
- No direct test verifies that `AppInitializer.initialize()` can be composed without relying on ambient `Supabase.instance` state.
- No direct test or tooling contract identifies the canonical non-production bootstrap among `lib/main_driver.dart`, `lib/test_harness.dart`, and `lib/driver_main.dart`.
- No direct test covers `ScaffoldWithNavBar` shell behavior as a unit separate from the full router graph.
