# Defects Archive

Historical defects moved from defects.md or already fixed. Reference only.

---

## Archived Active Patterns (2026-01)

These were active patterns that didn't make the top 15 in defects.md.

### [E2E] 2026-01-16: Inadequate E2E Test Debugging
**Pattern**: Declaring test success based on partial output without analyzing full logs
**Prevention**: Search logs for `TimeoutException`, `hanging`; check duration (>60s = likely hanging)

### [E2E] 2026-01-15: Test Delays
**Pattern**: Using hardcoded `Future.delayed()` in tests
**Prevention**: Use condition-based waits: `await $.waitUntilVisible(finder);`

### [E2E] 2026-01-14: Hardcoded Test Widget Keys
**Pattern**: Using `Key('widget_name')` directly in widgets and tests
**Prevention**: Always use `TestingKeys` class from `lib/shared/testing_keys/testing_keys.dart`

### [E2E] 2026-01-13: Missing TestingKeys for Dialog Buttons
**Pattern**: UI dialogs missing TestingKeys on action buttons
**Prevention**: When creating dialogs with action buttons, always add TestingKeys

### [E2E] 2026-01-12: E2E Tests Missing Supabase Credentials
**Pattern**: Running patrol tests without SUPABASE_URL and SUPABASE_ANON_KEY
**Prevention**: Always use `run_patrol.ps1` which loads from `.env.local`

### [E2E] 2026-01-11: Gradle File Lock on Test Results
**Pattern**: Gradle creates .lck files preventing subsequent test runs
**Prevention**: Kill stale Java/Gradle processes; clean `build/app/outputs/androidTest-results`

### [E2E] 2026-01-10: Raw app.main() in Patrol Tests
**Pattern**: Using `app.main()` directly without the helper pattern
**Prevention**: Use `PatrolTestConfig.createHelpers($, 'test_name')`, `h.launchAppAndWait()`

### [E2E] 2026-01-09: Repeated Test Runs Corrupt App State
**Pattern**: Running E2E tests repeatedly without resetting device/app state
**Prevention**: Reset app state: `adb shell pm clear com.fvconstruction.construction_inspector`

### [E2E] 2026-01-08: Keyboard Covers Text Field After Tap
**Pattern**: Tapping text field opens keyboard, which covers the field
**Prevention**: After tapping text field, call `scrollTo()` again before `enterText()`

### [E2E] 2026-01-07: assertVisible Without Scroll
**Pattern**: Calling `h.assertVisible(key, msg)` on elements below the fold
**Prevention**: Always `$(key).scrollTo()` before `h.assertVisible()` for below-fold elements

### [E2E] 2026-01-06: .exists Doesn't Mean Hit-Testable
**Pattern**: Using `.exists` to check if widget is ready before `.tap()`
**Prevention**: `.exists` is true for widgets below fold; use `safeTap(..., scroll: true)`

### [DATA] 2026-01-05: Rethrow in Callbacks
**Pattern**: Using `rethrow` in `.catchError()` or `onError` callbacks
**Prevention**: Use `throw error` in callbacks, `rethrow` only in catch blocks

---

## Fixed Defects (2026-01)

### 2026-01-21: PatrolIntegrationTester.takeScreenshot() Doesn't Exist [FIXED]
**Issue**: Patrol tests fail - `takeScreenshot` isn't defined for PatrolIntegrationTester
**Fix**: Use graceful fallback pattern; screenshot is `$.native.takeScreenshot()` or skip

### 2026-01-21: Patrol openApp() Empty Package Name [FIXED]
**Issue**: `openApp()` passed empty package name
**Fix**: Always pass explicit appId: `$.native.openApp(appId: 'com.package.name')`

### 2026-01-21: Test Orchestrator Version Doesn't Exist [FIXED]
**Issue**: Could not find androidx.test:orchestrator:1.5.2
**Fix**: Use version 1.6.1 (latest)

### 2026-01-21: Patrol Tests Fail Before App Initializes [FIXED]
**Issue**: Tests couldn't find widgets after app.main()
**Fix**: Add delay after pumpAndSettle for apps with async init

### 2026-01-20: ProjectProvider Unsafe firstWhere [FIXED]
**Issue**: .first on empty list throws, unchecked firstWhere throws
**Fix**: Use .where().firstOrNull pattern across all providers

### 2026-01-20: Hardcoded Supabase Credentials [FIXED]
**Issue**: Supabase URL and anon key committed to git
**Fix**: Use String.fromEnvironment(), added isConfigured check

### 2026-01-20: copyWithNull Test Failures [FIXED]
**Issue**: Tests referenced copyWithNull() but models only have copyWith()
**Fix**: Removed failing tests from repository test files

### 2026-01-21: Patrol Tests Build but Execute 0 Tests [FIXED]
**Issue**: 69 tests built but 0 executed
**Fix**: Target `integration_test/test_bundle.dart` (auto-generated), not manual aggregator

### 2026-01-21: Patrol CLI "Failed to read Java version" [FIXED]
**Issue**: Patrol couldn't read Java version on Windows
**Fix**: Install Android SDK Command-line Tools from SDK Manager

### 2026-01-21: Patrol MainActivityTest.java Outdated API [FIXED]
**Issue**: PatrolTestRule API doesn't exist in Patrol 3.20.0
**Fix**: Use Parameterized JUnit pattern from Patrol example

### 2026-01-21: Seed Data Missing NOT NULL Timestamps [FIXED]
**Issue**: NOT NULL constraint failed on entry_personnel.created_at
**Fix**: Added timestamps to all insert operations

### 2026-01-21: SyncService Crashes When Supabase Not Configured [FIXED]
**Issue**: App crashes accessing Supabase.instance without credentials
**Fix**: Made _supabase nullable, check SupabaseConfig.isConfigured

### 2026-01-21: Gradle Configuration Cache Incompatible [FIXED]
**Issue**: Configuration cache error with Flutter
**Fix**: Disable org.gradle.configuration-cache

### 2026-01-21: Patrol Test Hangs at Gradle Config [FIXED]
**Issue**: Circular dependency in build.gradle.kts
**Fix**: Remove evaluationDependsOn block

### 2026-01-21: Stale Compilation Cache [FIXED]
**Issue**: False compilation errors after code changes
**Fix**: Run `flutter clean && flutter pub get`

### 2026-01-21: Invalid rethrow in catchError [FIXED]
**Issue**: `rethrow` used in .catchError() callback
**Fix**: Use `throw error` instead of `rethrow` in callbacks

### 2026-01-21: Router Accesses Supabase.instance Without Check [FIXED]
**Issue**: Router crashed without Supabase config
**Fix**: Check SupabaseConfig.isConfigured before Supabase.instance

---

## Unfixed but Low Priority

### 2026-01-21: GoTrueClient Mock Signature Mismatch
**Issue**: Mock missing captchaToken, channel parameters
**Fix Needed**: Update auth_service_test.dart mocks

### 2026-01-21: Missing TestWidgetsFlutterBinding
**Issue**: SyncService tests crash without binding
**Fix Needed**: Add TestWidgetsFlutterBinding.ensureInitialized()

### 2026-01-21: Wrong Package Name in Test Helper
**Issue**: test_sorting.dart imports construction_app
**Fix Needed**: Change to construction_inspector

### 2026-01-21: Mock Repository Method Names Mismatch
**Issue**: Mock methods don't match test expectations
**Fix Needed**: Rename mock methods or use mocktail
