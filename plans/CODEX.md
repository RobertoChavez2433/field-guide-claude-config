# E2E Test Determinism & Logging - PR Plan

## Goals
- Eliminate silent passes and flaky timeouts by enforcing fail-loud preconditions.
- Make navigation and entry flows deterministic with screen-ready markers.
- Improve logging so failures show app state, not just the missing widget.

## PR 1: Logging & diagnostics baseline

### 1.1 Add a compact screen-state logger
Steps:
1) Add `logScreenState({String context})` to `patrol_test_helpers.dart`.
2) Log presence + hit-testable status of:
   - bottom nav
   - dashboard cards
   - projects FAB
   - calendar FAB
   - entry wizard close
3) Call `logScreenState()` at the start of each navigation and entry test.
Files:
- `integration_test/patrol/helpers/patrol_test_helpers.dart`
- `integration_test/patrol/e2e_tests/navigation_flow_test.dart`
- `integration_test/patrol/e2e_tests/entry_management_test.dart`
- `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`
- `integration_test/patrol/e2e_tests/quantities_flow_test.dart`

### 1.2 Harden failure diagnostics
Steps:
1) Ensure `safeTap`, `waitForVisible`, and `waitForHitTestable` log both `exists` and `hitTestable` on failure.
2) Add a short list of “expected next keys” to `dumpFailureDiagnostics` for common flows (dashboard, projects, calendar, entry wizard).
Files:
- `integration_test/patrol/helpers/patrol_test_helpers.dart`

## PR 2: Fail‑loud preconditions (no silent passes)

### 2.1 Replace silent skips with explicit failures
Steps:
1) Search for `return;` after `exists` checks in flow tests and replace with fail‑loud helpers.
2) Convert flow tests to `ensureSeedProjectSelectedOrFail()` where needed.
Files:
- `integration_test/patrol/e2e_tests/quantities_flow_test.dart`
- `integration_test/patrol/e2e_tests/photo_flow_test.dart`
- `integration_test/patrol/e2e_tests/entry_management_test.dart`
- `integration_test/patrol/e2e_tests/navigation_flow_test.dart`
- `integration_test/patrol/e2e_tests/offline_sync_test.dart`
- `integration_test/patrol/e2e_tests/contractors_flow_test.dart`

### 2.2 Make coverage tests explicit about skips
Steps:
1) Add `tapIfHitTestable` return value handling that logs “SKIPPED” when missing.
2) Add a counter and fail the test if skips exceed a threshold (ex: >20%).
Files:
- `integration_test/patrol/helpers/patrol_test_helpers.dart`
- `integration_test/patrol/e2e_tests/ui_button_coverage_test.dart`

## PR 3: Navigation determinism

### 3.1 Require project selection for nav tests
Steps:
1) Add `await h.ensureSeedProjectSelectedOrFail();` to all navigation tests that expect dashboard/calendar to work.
2) After each tab tap, `waitForVisible` a screen‑specific key (dashboard card, add project FAB, add entry FAB, settings tile).
Files:
- `integration_test/patrol/e2e_tests/navigation_flow_test.dart`

### 3.2 Remove raw `.tap()` for tabs
Steps:
1) Replace tab taps with `safeTap` to guarantee hit‑testable interaction.
2) Ensure each nav action ends with a readiness check.
Files:
- `integration_test/patrol/e2e_tests/navigation_flow_test.dart`

## PR 4: Entry‑flow waits and timeouts

### 4.1 Replace fixed sleeps with condition waits
Steps:
1) Remove `pumpAndWait` delays that follow deterministic actions (open wizard, open report, save entry).
2) Replace with `waitForHitTestable` on the next expected element.
Files:
- `integration_test/patrol/e2e_tests/entry_management_test.dart`
- `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`
- `integration_test/patrol/e2e_tests/quantities_flow_test.dart`

### 4.2 Tighten entry wizard readiness
Steps:
1) Reduce `waitForEntryWizardReady` default timeout if stable (ex: 12s).
2) Add a single retry when loading is detected to avoid long stalls.
Files:
- `integration_test/patrol/helpers/patrol_test_helpers.dart`

### 4.3 Report screen readiness
Steps:
1) Add a report‑screen readiness key (or reliable existing key).
2) Update `waitForReportScreen()` to use the readiness key instead of menu button.
Files:
- `lib/shared/testing_keys.dart`
- `lib/features/report/...` (report header widget)
- `integration_test/patrol/helpers/patrol_test_helpers.dart`

## PR 5: Batch data isolation

### 5.1 Reset/seed per test in state‑mutating files
Steps:
1) Use `resetAndSeed()` in `setUp()` for files that write data.
2) Keep `ensureSeedData()` for read‑only flows.
Files:
- `integration_test/patrol/helpers/test_database_helper.dart`
- `integration_test/patrol/e2e_tests/entry_management_test.dart`
- `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`
- `integration_test/patrol/e2e_tests/quantities_flow_test.dart`
- `integration_test/patrol/e2e_tests/project_management_test.dart`
- `integration_test/patrol/e2e_tests/contractors_flow_test.dart`

## PR 6: Verification

### 6.1 Run batched tests
Steps:
1) Run `pwsh -File run_patrol_batched.ps1`.
2) If time‑limited, run only affected batches.
Success criteria:
- No silent passes; missing preconditions fail with diagnostics.
- Navigation tests no longer stall on Projects.
- Entry flow tests avoid long fixed waits and complete within expected time.
Files:
- `run_patrol_batched.ps1`
