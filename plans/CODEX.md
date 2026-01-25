# PR Plan: Stabilize E2E Entry + Sync Tests (Comprehensive Findings)

## Problem Summary
Entry-related E2E tests still hang on hit-testable waits and scrolls. Failures now span Entry Wizard readiness (locations never hit-testable), scrolls to lower sections, and offline sync flows where `entry_wizard_activities` is found but not hit-testable. Logs show inconsistent artifacts (XML missing on one run, logcat files empty), making diagnosis slower.

## Findings (Past + Current)
- Entry Wizard location dropdown times out as not hit-testable (5s timeout), indicating locations never finish loading or UI never becomes hit-testable. Evidence: `C:\Users\rseba\Projects\Field Guide App\build\app\outputs\androidTest-results\connected\debug\TEST-SM-G996U - 13-_app-.xml`.
- Entry Wizard lower sections (e.g., `entry_quantities_section`) time out in `scrollToWizardSection`, indicating scroll targeting isn’t reliable when sections aren’t hit-testable. Evidence: `C:\Users\rseba\Projects\Field Guide App\build\app\outputs\androidTest-results\connected\debug\SM-G996U - 13\testlog\test-results.log`.
- `waitForEntryWizardReady` now times out at 20s in “Cancel entry creation” (wizard never reaches ready state). Evidence: `C:\Users\rseba\Projects\Field Guide App\build\app\outputs\androidTest-results\connected\debug\SM-G996U - 13\testlog\test-results.log`.
- Offline sync tests now fail on `entry_wizard_activities` found but not hit-testable, indicating scroll/visibility regression in `fillEntryField` usage. Evidence: `C:\Users\rseba\Projects\Field Guide App\build\app\outputs\androidTest-results\connected\debug\SM-G996U - 13\testlog\test-results.log`.
- Some tests still wait for calendar after submit, but app navigates to report on submit; mismatched expectations caused timeouts in prior runs. Evidence: `lib/features/entries/presentation/screens/entry_wizard_screen.dart`, `integration_test/patrol/e2e_tests/navigation_flow_test.dart`.
- `TestingKeys.entryWizardSave` is defined but not wired in UI; tests referencing it timed out previously. Evidence: `lib/shared/testing_keys.dart`, `integration_test/patrol/e2e_tests/offline_sync_test.dart` (historical).
- Logcat files for entry tests are zero bytes; XML report was missing in one run and reappeared later, reducing diagnostics. Evidence: `C:\Users\rseba\Projects\Field Guide App\build\app\outputs\androidTest-results\connected\debug\SM-G996U - 13\logcat-*.txt`, `C:\Users\rseba\Projects\Field Guide App\build\app\outputs\androidTest-results\connected\debug\TEST-SM-G996U - 13-_app-.xml`.
- UTP log shows transport cancellation noise (HTTP/2 RST_STREAM); not necessarily causal but indicates unstable test reporting. Evidence: `C:\Users\rseba\Projects\Field Guide App\build\app\outputs\androidTest-results\connected\debug\SM-G996U - 13\utp.0.log`.

## Phase 1: Re-audit logs + artifacts (PR Size: small)
### 1.1 Re-check test artifacts while runs finish
- Step: Re-scan the latest `test-results.log`, XML, and logcat for new errors and confirm the XML report exists every run.
- Reason: Confirms we are acting on current failures and the right binaries are in use.
- Files:
  - `C:\Users\rseba\Projects\Field Guide App\build\app\outputs\androidTest-results\connected\debug\SM-G996U - 13\testlog\test-results.log`
  - `C:\Users\rseba\Projects\Field Guide App\build\app\outputs\androidTest-results\connected\debug\TEST-SM-G996U - 13-_app-.xml`
  - `C:\Users\rseba\Projects\Field Guide App\build\app\outputs\androidTest-results\connected\debug\SM-G996U - 13\logcat-*.txt`

### 1.2 Add log capture hooks for entry failures
- Step: Capture `adb logcat -s flutter` output during entry tests into per-test files.
- Reason: Current logcat files are empty for failing entry tests.
- Files:
  - `scripts/run_patrol.ps1` or `run_patrol_batched.ps1`

## Phase 2: Make Entry Wizard readiness deterministic (PR Size: medium)
### 2.1 Add explicit “ready” indicators
- Step: Add `TestingKeys.entryWizardLocationLoading` (already wired) and optionally a new `entryWizardReady` key once providers finish loading.
- Reason: Tests need a reliable signal that locations/contractors/bid items are loaded and the dropdown is hit-testable.
- Files:
  - `lib/features/entries/presentation/screens/entry_wizard_screen.dart`
  - `lib/features/entries/presentation/widgets/entry_basics_section.dart`
  - `lib/shared/testing_keys.dart`

### 2.2 Strengthen readiness waits
- Step: Update `waitForEntryWizardReady` to wait for either the “ready” key or the dropdown being hit-testable, and log provider load failures if any.
- Reason: `waitForEntryWizardReady` is still timing out at 20s, which blocks multiple tests.
- Files:
  - `integration_test/patrol/helpers/patrol_test_helpers.dart`

### 2.3 Ensure deterministic test DB state
- Step: Switch entry-focused tests to `TestDatabaseHelper.resetAndSeed()` in `setUpAll` or `setUp`.
- Reason: Prevent stale DB state causing location/provider load issues.
- Files:
  - `integration_test/patrol/helpers/test_database_helper.dart`
  - `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`
  - `integration_test/patrol/e2e_tests/entry_management_test.dart`
  - `integration_test/patrol/e2e_tests/offline_sync_test.dart`

## Phase 3: Fix scroll + hit-testability (PR Size: medium)
### 3.1 Align scroll pattern with the passing flow
- Step: Replace `scrollToWizardSection` calls with direct `scrollTo()` on the actual field/button (same pattern as `fillEntryField`).
- Reason: `scrollToWizardSection` is still failing to find `entry_quantities_section`.
- Files:
  - `integration_test/patrol/helpers/patrol_test_helpers.dart`
  - `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`
  - `integration_test/patrol/e2e_tests/entry_management_test.dart`

### 3.2 Make `fillEntryField` hit-testable-safe
- Step: Add `ensureVisible` + hit-testable retry loop + keyboard dismiss before entry to avoid “found but not hit-testable” on `entry_wizard_activities`.
- Reason: Offline sync tests now fail at the activities field despite the widget being found.
- Files:
  - `integration_test/patrol/helpers/patrol_test_helpers.dart`
  - `integration_test/patrol/e2e_tests/offline_sync_test.dart`

## Phase 4: Align test expectations with actual navigation (PR Size: small)
### 4.1 Ensure submit flows expect report screen
- Step: Confirm all submit flows use `saveEntry(expectReport: true)` and only wait for calendar after navigating back.
- Reason: Entry wizard submits always route to report; waiting for calendar causes timeouts.
- Files:
  - `integration_test/patrol/helpers/patrol_test_helpers.dart`
  - `integration_test/patrol/e2e_tests/navigation_flow_test.dart`
  - `integration_test/patrol/e2e_tests/offline_sync_test.dart`
  - `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`

## Phase 5: Restore exhaustive coverage with stability (PR Size: medium)
### 5.1 Entry Wizard coverage after readiness/scroll fixes
- Step: Re-enable full Entry Wizard button coverage only after readiness/scroll fixes are stable.
- Reason: Prevents heavy coverage from amplifying flaky prerequisites.
- Files:
  - `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`

### 5.2 Report screen exhaustive coverage
- Step: Ensure report screen button coverage test waits for report screen and uses hit-testable-safe interactions for edit dialogs, quantities, and photo flows.
- Reason: Report coverage is required for the “exhaustive clickables” goal.
- Files:
  - `integration_test/patrol/e2e_tests/entry_management_test.dart`
  - `lib/features/entries/presentation/screens/report_screen.dart`

## Phase 6: Verification (PR Size: small)
### 6.1 Focused test runs
- Step: Re-run entry, offline sync, and navigation tests after fixes.
- Suggested commands:
  - `pwsh -File run_patrol.ps1 -TestFile "integration_test/patrol/e2e_tests/entry_lifecycle_test.dart"`
  - `pwsh -File run_patrol.ps1 -TestFile "integration_test/patrol/e2e_tests/entry_management_test.dart"`
  - `pwsh -File run_patrol.ps1 -TestFile "integration_test/patrol/e2e_tests/offline_sync_test.dart"`
  - `pwsh -File run_patrol.ps1 -TestFile "integration_test/patrol/e2e_tests/navigation_flow_test.dart"`
- Reason: Confirms that readiness, scroll, and navigation fixes eliminate the timeouts.
