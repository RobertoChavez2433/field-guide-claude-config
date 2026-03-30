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

## Coverage Gaps

- No direct tests for startup composition, router redirect matrix, or background sync bootstrap.
- The existing suite passing does not verify that the composed production app uses the same routing/wiring objects that `AppInitializer` constructs.
- No direct router tests cover the combined password-recovery, force-update, force-reauth, onboarding, and consent redirect matrix in one place.
- No direct test verifies that `main.dart` and `main_driver.dart` keep equivalent consent/router/bootstrap behavior.
