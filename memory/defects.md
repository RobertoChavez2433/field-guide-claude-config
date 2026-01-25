# Defects Log

Critical patterns to avoid. Archive: `defects-archive.md`

## Format
```
### Title
**Pattern**: What to avoid
**Prevention**: How to avoid
```

---

## Active Patterns

### Async Context Safety
**Pattern**: Using context after await without mounted check
**Prevention**: Always `if (!mounted) return;` before setState/context after await
**Example**:
```dart
await someAsyncOp();
if (!mounted) return;  // REQUIRED
context.read<Provider>();
```

### Async in dispose()
**Pattern**: Calling async methods in dispose() - context already deactivated
**Prevention**: Use `WidgetsBindingObserver.didChangeAppLifecycleState` for lifecycle saves

### Unsafe Collection Access
**Pattern**: .first on empty list, firstWhere without orElse
**Prevention**: Use `.where().firstOrNull` pattern
```dart
// BAD: throws on empty
items.first
items.firstWhere((e) => e.id == id)

// GOOD: returns null safely
items.where((e) => e.id == id).firstOrNull
```

### Supabase Instance Access
**Pattern**: Accessing Supabase.instance without checking configuration
**Prevention**: Always check `SupabaseConfig.isConfigured` first
```dart
final user = SupabaseConfig.isConfigured
    ? Supabase.instance.client.auth.currentUser
    : null;
```

### Test Delays
**Pattern**: Using hardcoded Future.delayed() in tests
**Prevention**: Use condition-based waits
```dart
// BAD
await Future.delayed(Duration(seconds: 2));

// GOOD
await $.waitUntilVisible(finder);
```

### Rethrow in Callbacks
**Pattern**: Using `rethrow` in .catchError() or onError callbacks
**Prevention**: Use `throw error` in callbacks, `rethrow` only in catch blocks

### Hardcoded Test Widget Keys
**Pattern**: Using `Key('widget_name')` directly in both widgets and tests
**Prevention**:
- Always use `TestingKeys` class from `lib/shared/testing_keys.dart`
- Never hardcode `Key('...')` in widgets or tests
- Add new keys to TestingKeys when adding testable widgets
**Impact**: 14+ tests excluded from test bundle, navigation helpers broken
**Ref**: @.claude/plans/e2e-testing-remediation-plan.md

### Missing TestingKeys for Dialog Buttons
**Pattern**: UI dialogs (confirmation, sign out, delete) missing TestingKeys on action buttons
**Prevention**:
- When creating dialogs with action buttons, always add TestingKeys
- Check if test helpers need to interact with the dialog (especially confirmation flows)
- Common missing: confirm buttons, cancel buttons in AlertDialog actions
**Impact**: E2E tests fail because helpers can't tap dialog buttons
**Example**: Sign out dialog "Sign Out" button needed `TestingKeys.signOutConfirmButton`

### TestingKeys Defined But Not Wired
**Pattern**: Adding a key to TestingKeys class but not assigning it to the actual widget
**Prevention**:
- When adding a TestingKey, immediately wire it to the widget: `key: TestingKeys.myKey`
- Search for the key in lib/ to verify it's used: `grep -r "TestingKeys.myKey" lib/`
- Test helpers using undefined keys will timeout waiting for widgets that "don't exist"
**Impact**: `waitForAppReady()` timeouts, tests can't find screens/buttons
**Example**: `TestingKeys.loginScreen` was defined but never added to login_screen.dart Scaffold

### E2E Tests Missing Supabase Credentials
**Pattern**: Running patrol tests without passing SUPABASE_URL and SUPABASE_ANON_KEY
**Prevention**:
- Always use `run_patrol.ps1` which loads from `.env.local`
- Or manually pass: `--dart-define="SUPABASE_URL=xxx" --dart-define="SUPABASE_ANON_KEY=yyy"`
- Without credentials, `SupabaseConfig.isConfigured` returns false → auth bypassed entirely
**Impact**: App goes straight to home screen, auth tests fail expecting login screen
**Example**: Tests timeout because `forceLogoutIfNeeded()` returns early when Supabase not configured

### dismissKeyboard() Closes Dialogs on Android
**Pattern**: Using `h.dismissKeyboard()` (which calls `$.native.pressBack()`) inside dialogs
**Prevention**:
- Use `scrollTo()` to make buttons visible instead
- Or tap outside text field to dismiss keyboard
- Never use pressBack when inside a dialog - it closes the entire dialog
**Impact**: Tests fail with "widget not found" because dialog was dismissed
**Example**: contractors_flow_test save button not found after dismissKeyboard

### Gradle File Lock on Test Results
**Pattern**: Gradle creates .lck files in androidTest-results that prevent subsequent test runs
**Prevention**:
- Kill stale Java/Gradle processes before running tests
- Clean test results: `rm -rf build/app/outputs/androidTest-results`
- Use `pwsh -Command "Get-Process -Name java | Stop-Process -Force"` if needed
**Impact**: Test execution fails with "Cannot access output property 'resultsDir'" error
**Example**: `utp.0.log.lck` file prevents test runner from starting

### Raw app.main() in Patrol Tests
**Pattern**: Using `app.main()` directly without the helper pattern
**Prevention**:
- Always use `PatrolTestConfig.createHelpers($, 'test_name')`
- Call `h.launchAppAndWait()` instead of `app.main()`
- Call `h.signInIfNeeded()` after launch for authenticated screens
- Use `h.waitForVisible()` instead of `$.waitUntilVisible()`
**Impact**: Tests fail because no sign-in performed, stuck on login screen
**Example**: navigation_flow_test couldn't find bottomNavigationBar because auth was required

### Git Bash Silent Output on Windows
**Pattern**: Running Flutter/Patrol commands through Git Bash loses stdout/stderr
**Prevention**:
- Always run E2E tests through PowerShell: `pwsh -File run_patrol_batched.ps1`
- Or wrap commands: `pwsh -Command "flutter build apk --debug"`
- Git Bash swallows output from Flutter's build system
**Impact**: Commands appear to complete instantly with no output, debugging impossible
**Example**: `flutter build apk --debug 2>&1` returns nothing in Git Bash but works in PowerShell

### Repeated Test Runs Corrupt App State
**Pattern**: Running E2E tests repeatedly without resetting device/app state between runs
**Prevention**:
- Reset app state before running tests: `adb shell pm clear com.fvconstruction.construction_inspector`
- Use `run_patrol_batched.ps1` which resets between batches
- Don't spam tests trying to debug - one run, analyze, fix, reset, retry
**Impact**: Tests that would pass fail due to stale database/login state from prior runs
**Example**: Auth tests fail because user already signed in from previous test run

### Test Helper Missing scrollTo() Before tap()
**Pattern**: Calling `$(finder).tap()` on widgets that may be below the fold
**Prevention**:
- Always call `$(finder).scrollTo()` before `$(finder).tap()` for form fields
- Widgets found but "not hit-testable" means they're off-screen
- Apply to: `fillEntryField()`, `selectFromDropdown()`, `saveEntry()`
**Impact**: TimeoutException - "Found 1 widget... did not find any visible (hit-testable) widgets"
**Example**: entry_wizard_activities field exists but couldn't be tapped until scrolled into view

---

<!-- Add new defects above this line -->
