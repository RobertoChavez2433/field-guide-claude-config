
## Phase 3: Router Split

**Goal:** Extract redirect logic and ScaffoldWithNavBar out of `app_router.dart` (932 lines) into focused files, then slim the router to ~500 lines.

### Sub-phase 3.1: Create `app_redirect.dart`

- **File:** `lib/core/router/app_redirect.dart` (NEW)
- **Agent:** `general-purpose`
- **Estimated time:** 5 minutes

**WHY:** The redirect function is 185 lines of security-critical gate logic embedded inside `_buildRouter()`. Extracting it into its own class makes each gate testable in isolation and removes `context.read<AppConfigProvider>()` -- a silent-fail antipattern where the try-catch swallows provider-not-found errors in release.

**CRITICAL CHANGES from current code:**
1. `AppConfigProvider` is now injected via constructor (not read from context) -- eliminates the try-catch at gates 5-6
2. `ConsentProvider` is now `required` (not nullable) -- eliminates null checks at gate 7
3. `isRestorableRoute` moves here as a static method (it uses `_kNonRestorableRoutes` which lives in this file)

**Create this file with this EXACT content.** The full Dart source code is provided inline in the spec context (KEY SOURCE CODE > Sub-phase 3.1). Key design points:

- New class `AppRedirect` with constructor taking `required AuthProvider`, `required ConsentProvider`, `required AppConfigProvider`
- Single public method `String? redirect(BuildContext context, GoRouterState state)`
- Move `_kOnboardingRoutes` and `_kNonRestorableRoutes` into this file
- Static `isRestorableRoute` method
- Private gate methods: `_checkConfigBypass()`, `_checkPasswordRecovery()`, `_checkOnboardingRedirect()`, `_checkProfileRouting()`
- Gate return convention: `''` means "allow (return null)", a path string means "redirect", `null` means "continue to next gate"
- CRITICAL: Replace `context.read<AppConfigProvider>()` try-catch with injected `_appConfigProvider` field
- CRITICAL: Replace `_consentProvider != null` null check with direct `_consentProvider.hasConsented` (no longer nullable)

---

### Sub-phase 3.2: Create `scaffold_with_nav_bar.dart`

- **File:** `lib/core/router/scaffold_with_nav_bar.dart` (NEW)
- **Agent:** `frontend-flutter-specialist-agent`
- **Estimated time:** 3 minutes

**WHY:** ScaffoldWithNavBar is 185 lines of UI code that has nothing to do with routing. Extracting it makes the shell widget independently testable.

**Create this file -- direct extraction of lines 747-931 from current `app_router.dart`.** Zero logic changes. Only change is the import block:

```
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/theme/field_guide_colors.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/projects/presentation/widgets/project_switcher.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';
import 'package:construction_inspector/features/pdf/presentation/widgets/extraction_banner.dart';
import 'package:construction_inspector/shared/shared.dart';
```

Then paste the entire ScaffoldWithNavBar class body verbatim from app_router.dart lines 747-931.

---

### Sub-phase 3.3: Slim `app_router.dart`

- **File:** `lib/core/router/app_router.dart` (MODIFY)
- **Agent:** `general-purpose`
- **Estimated time:** 5 minutes

**WHY:** With redirect logic in `app_redirect.dart` and ScaffoldWithNavBar in its own file, `app_router.dart` becomes a thin routing table (~500 lines).

**CHANGES:**

1. **Remove** `_kOnboardingRoutes`, `_kNonRestorableRoutes` constants (now in `app_redirect.dart`)
2. **Remove** entire `ScaffoldWithNavBar` class (lines 747-931)
3. **Remove** entire redirect closure body (lines 157-342)
4. **Remove** `isRestorableRoute` static method (now on `AppRedirect`)
5. **Remove** imports only needed by redirect: `flutter/foundation.dart`, `supabase_config.dart`, `test_mode_config.dart`, `auth/data/models/models.dart`, `provider.dart`
6. **Remove** imports only needed by ScaffoldWithNavBar: `field_guide_colors.dart`, `project_switcher.dart`, `sync_orchestrator.dart`, `sync_provider.dart`, `extraction_banner.dart`, `shared.dart`
7. **Add** imports: `app_redirect.dart`, `scaffold_with_nav_bar.dart`
8. **Add** `required AppConfigProvider appConfigProvider` to constructor
9. **Change** `ConsentProvider? consentProvider` to `required ConsentProvider consentProvider`
10. **Add** `_appConfigProvider` field
11. **Update** `refreshListenable`: `Listenable.merge([_authProvider, _consentProvider, _appConfigProvider])`
12. **Update** `redirect:`: `AppRedirect(authProvider: _authProvider, consentProvider: _consentProvider, appConfigProvider: _appConfigProvider).redirect`

**NOTE:** `isRestorableRoute` moved to `AppRedirect`. Find and update all callers:
```
pwsh -Command "Select-String -Path 'lib/**/*.dart' -Pattern 'AppRouter\.isRestorableRoute' -Recurse"
```
Update each to `AppRedirect.isRestorableRoute` and add the `app_redirect.dart` import.

---

### Sub-phase 3.4: Verify

- **Agent:** `general-purpose`
- **Estimated time:** 2 minutes

```
pwsh -Command "flutter analyze"
```

---

## Phase 4: AppBootstrap

**Goal:** Create `AppBootstrap` to absorb all consent/auth/Sentry/router wiring duplicated between `main.dart` and `main_driver.dart`.

### Sub-phase 4.1: Create `app_bootstrap.dart`

- **File:** `lib/core/di/app_bootstrap.dart` (NEW)
- **Agent:** `general-purpose`
- **Estimated time:** 5 minutes

**WHY:** `main.dart` lines 128-176 and `main_driver.dart` lines 69-107 contain identical consent/auth-listener/router wiring. `AppBootstrap.configure()` absorbs this into a single call site.

**What it absorbs:**
1. `createConsentAndSupportProviders()` logic from `consent_support_factory.dart` (datasource/repository/provider construction)
2. `consentProvider.loadConsentState()` call
3. `enableSentryReporting()` call (gated on `!isDriverMode`)
4. Auth listener (consent clear on sign-out, deferred audit on sign-in)
5. `AppRouter` construction with all three required providers

**Create this file with this EXACT content.** Key design:

- Class `AppBootstrap` with static `BootstrapResult configure({required AppDependencies deps, bool isDriverMode = false})`
- `BootstrapResult` holds `appRouter`, `consentProvider`, `supportProvider`
- Step 1: Create ConsentLocalDatasource, ConsentRepository, ConsentProvider (same wiring as consent_support_factory.dart)
- Step 2: Create SupportLocalDatasource, SupportRepository, LogUploadRemoteDatasource, SupportProvider
- Step 3: `consentProvider.loadConsentState()` -- must be before AppRouter
- Step 4: `if (!isDriverMode && consentProvider.hasConsented) enableSentryReporting();`
- Step 5: Auth listener: sign-out clears consent + disables analytics; sign-in writes deferred audit
- Step 6: Construct AppRouter with all three required providers

**Imports needed:**

```
import 'package:construction_inspector/core/config/sentry_consent.dart';
import 'package:construction_inspector/core/config/supabase_config.dart';
import 'package:construction_inspector/core/analytics/analytics.dart';
import 'package:construction_inspector/core/di/app_initializer.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/core/router/app_router.dart';
import 'package:construction_inspector/features/settings/data/datasources/consent_local_datasource.dart';
import 'package:construction_inspector/features/settings/data/datasources/support_local_datasource.dart';
import 'package:construction_inspector/features/settings/data/datasources/remote/log_upload_remote_datasource.dart';
import 'package:construction_inspector/features/settings/data/repositories/consent_repository.dart';
import 'package:construction_inspector/features/settings/data/repositories/support_repository.dart';
import 'package:construction_inspector/features/settings/presentation/providers/consent_provider.dart';
import 'package:construction_inspector/features/settings/presentation/providers/support_provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
```

### Sub-phase 4.2: Verify

```
pwsh -Command "flutter analyze"
```

---

## Phase 5: Entrypoint Consolidation

**Goal:** Slim `main.dart` and `main_driver.dart` to use `AppBootstrap.configure()`, remove `appRouter` from `AppDependencies`.

### Sub-phase 5.1: Slim `main.dart`

- **File:** `lib/main.dart` (MODIFY)
- **Agent:** `general-purpose`
- **Estimated time:** 4 minutes

**CHANGES:**
1. **Remove** import: `consent_support_factory.dart`
2. **Add** import: `app_bootstrap.dart`
3. **Replace** `_runApp()` lines 120-186 with:

```
Future<void> _runApp() async {
  final deps = await AppInitializer.initialize(logDirOverride: kAppLogDirOverride);
  Analytics.trackAppLaunch();
  final bootstrap = AppBootstrap.configure(deps: deps);
  runApp(
    ConstructionInspectorApp(
      providers: buildAppProviders(deps),
      appRouter: bootstrap.appRouter,
      consentProvider: bootstrap.consentProvider,
      supportProvider: bootstrap.supportProvider,
    ),
  );
}
```

4. **Keep** everything else: `main()`, `_beforeSendSentry`, `_beforeSendTransaction`, `kAppLogDirOverride`, `ConstructionInspectorApp`

---

### Sub-phase 5.2: Slim `main_driver.dart`

- **File:** `lib/main_driver.dart` (MODIFY)
- **Agent:** `general-purpose`
- **Estimated time:** 3 minutes

**CHANGES:**
1. **Remove** imports: `sentry_consent.dart`, `app_router.dart`, `consent_support_factory.dart`, `analytics.dart`
2. **Add** import: `app_bootstrap.dart`
3. **Replace** lines 68-107 (consent factory through AppRouter construction) with single line:
   `final bootstrap = AppBootstrap.configure(deps: deps, isDriverMode: true);`
4. **Update** `runApp(...)` to use `bootstrap.appRouter`, `bootstrap.consentProvider`, `bootstrap.supportProvider`
5. **Keep** DriverServer setup, TestPhotoService swap, RepaintBoundary wrapper

---

### Sub-phase 5.3: Remove `appRouter` from `AppInitializer` and `AppDependencies`

- **File:** `lib/core/di/app_initializer.dart` (MODIFY)
- **Agent:** `general-purpose`
- **Estimated time:** 3 minutes

**Surgical edits (do NOT rewrite the entire file):**

1. **Remove** import at line 8: `import 'package:construction_inspector/core/router/app_router.dart';`
2. **Remove** field at line 275: `final AppRouter appRouter;`
3. **Remove** from constructor at line 285: `required this.appRouter,`
4. **Remove** from `copyWith` return at line 350: `appRouter: appRouter,`
5. **Remove** dead code at line 750-751: `final appRouter = AppRouter(authProvider: authProvider);`
6. **Remove** from `AppDependencies(...)` return at line 820: `appRouter: appRouter,`

---

### Sub-phase 5.4: Verify `app_providers.dart`

- **File:** `lib/core/di/app_providers.dart` (NO CHANGES)
- `buildAppProviders` never accesses `deps.appRouter`. Just verify:

```
pwsh -Command "flutter analyze"
```

---

### Sub-phase 5.5: Full verification

```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
```

Search for tests that instantiate `AppRouter` directly and update them:
```
pwsh -Command "Select-String -Path 'test/**/*.dart' -Pattern 'AppRouter\(' -Recurse"
```

Each needs all three required params: `authProvider`, `consentProvider`, `appConfigProvider`.

Also search for `AppRouter.isRestorableRoute` in tests -- update to `AppRedirect.isRestorableRoute`.

---

## Phase 6: AppDependencies Cleanup

**Goal:** Remove dead code left over from the refactor.

### Sub-phase 6.1: Remove `appRouter` from `AppDependencies`

Already done in Sub-phase 5.3. This sub-phase exists for spec completeness.

---

### Sub-phase 6.2: Delete `consent_support_factory.dart`

- **File:** `lib/features/settings/di/consent_support_factory.dart` (DELETE)
- **Agent:** `general-purpose`
- **Estimated time:** 2 minutes

**WHY:** Its logic is now in `AppBootstrap.configure()`. The file is dead code.

**Before deleting**, verify no imports remain:
```
pwsh -Command "Select-String -Path 'lib/**/*.dart' -Pattern 'consent_support_factory' -Recurse"
```
Expected: zero matches. Then delete:
```
pwsh -Command "Remove-Item 'lib/features/settings/di/consent_support_factory.dart'"
```

---

### Sub-phase 6.3: Clean dead code

Verify no remaining references:
```
pwsh -Command "Select-String -Path 'lib/**/*.dart' -Pattern 'createConsentAndSupportProviders' -Recurse"
pwsh -Command "Select-String -Path 'lib/**/*.dart' -Pattern 'ConsentSupportResult' -Recurse"
```
Expected: zero matches for both.

---

### Sub-phase 6.4: Final verification

```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
```

**Line count targets:**
- `app_router.dart`: ~500 lines (was 932) -- route definitions only
- `app_redirect.dart`: ~210 lines -- redirect logic with private gate methods
- `scaffold_with_nav_bar.dart`: ~185 lines -- UI shell widget
- `app_bootstrap.dart`: ~110 lines -- consent/auth/Sentry/router wiring
- `main.dart _runApp()`: ~12 lines (was 67)
- `main_driver.dart _runApp()`: ~25 lines (was 78)
