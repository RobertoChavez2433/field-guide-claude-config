# E2E Test Stability - PR Plan (v2)

## Goals
- Eliminate false positives from silent skips and non-hit-testable taps.
- Make tests deterministic within batches where data persists across files.
- Centralize stability logic in helpers and minimize per-test boilerplate.

## Known Behavior / Constraints
- `run_patrol_batched.ps1` resets app data only between batches; data persists across files in the same batch.
- Each `patrolTest` launches a fresh app instance; project selection must happen per test after app launch.

## PR 1: Readiness key + helper hardening

### 1.1 Add a single project-selected readiness key
Steps:
1) Add `TestingKeys.dashboardProjectTitle` (or rename to `projectSelectedIndicator`, pick one) in `lib/shared/testing_keys.dart`.
2) Wire it to the dashboard project title widget.
Files:
- `lib/shared/testing_keys.dart`
- `lib/features/dashboard/...` (project title widget)

### 1.2 Add a fail-loud project selection helper
Steps:
1) Add `ensureSeedProjectSelectedOrFail()` in `patrol_test_helpers.dart`.
2) Navigate to Projects, locate the seed project, `waitForHitTestable` + tap.
3) Wait for the readiness key from 1.1; if missing, call `_logKeyDiagnostics` and throw.
Files:
- `integration_test/patrol/helpers/patrol_test_helpers.dart`
- `integration_test/patrol/fixtures/test_seed_data.dart`
- `lib/shared/testing_keys.dart`

### 1.3 Harden `saveProject()` using hit-testable checks
Steps:
1) Replace `.exists` branching with hit-testable detection (short timeout).
2) `safeTap(..., scroll: true)` the hit-testable button.
3) If neither button is hit-testable, log diagnostics and throw.
4) Post-save wait uses `waitForHitTestable(TestingKeys.addProjectFab, timeout: 5s)`; bump if needed.
Files:
- `integration_test/patrol/helpers/patrol_test_helpers.dart`

### 1.4 Add an optional tap helper for coverage tests
Steps:
1) Add `tapIfHitTestable(Key key, {description})` that logs when missing but does not fail.
2) Use this helper in coverage-style tests where optional UI is expected.
Files:
- `integration_test/patrol/helpers/patrol_test_helpers.dart`

## PR 2: Data isolation strategy (per file)

### 2.1 Adopt explicit reset/seed in files that mutate data
Steps:
1) Use `TestDatabaseHelper.resetAndSeed()` in `setUp` for tests that mutate data.
2) Keep `ensureSeedData()` for read-only flows.
Files:
- `integration_test/patrol/helpers/test_database_helper.dart`
- `integration_test/patrol/e2e_tests/quantities_flow_test.dart`
- `integration_test/patrol/e2e_tests/entry_management_test.dart`
- `integration_test/patrol/e2e_tests/project_setup_flow_test.dart`
- `integration_test/patrol/e2e_tests/settings_theme_test.dart`
- `integration_test/patrol/e2e_tests/project_management_test.dart`
- `integration_test/patrol/e2e_tests/contractors_flow_test.dart`
- `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`

### 2.2 Batch-aware note (optional)
Steps:
1) Add a short comment in `run_patrol_batched.ps1` about data persistence within batch.
Files:
- `run_patrol_batched.ps1`

## PR 3: Flow test fixes (Batch 2 and 3)

### 3.1 Quantities flow: require project selection
Steps:
1) At start of each test, call `h.ensureSeedProjectSelectedOrFail()`.
2) Navigate to Calendar only after readiness key is visible.
Files:
- `integration_test/patrol/e2e_tests/quantities_flow_test.dart`

### 3.2 Entry management + project setup + settings theme
Steps:
1) Replace direct save taps with `h.saveProject()`.
2) Replace add-photo direct taps with `h.safeTap(..., scroll: true)`.
Files:
- `integration_test/patrol/e2e_tests/entry_management_test.dart`
- `integration_test/patrol/e2e_tests/project_setup_flow_test.dart`
- `integration_test/patrol/e2e_tests/settings_theme_test.dart`

## PR 4: Additional flow audits (Batch 4 and other gaps)

### 4.1 Contractors flow
Steps:
1) Replace `.exists` + direct tap patterns for flow-critical actions with `safeTap`.
2) If optional UI, use `tapIfHitTestable`.
Files:
- `integration_test/patrol/e2e_tests/contractors_flow_test.dart`

### 4.2 Navigation and offline sync
Steps:
1) Audit for direct taps and missing project selection; use helpers as needed.
2) Replace any `.exists`-gated taps on required steps.
Files:
- `integration_test/patrol/e2e_tests/navigation_flow_test.dart`
- `integration_test/patrol/e2e_tests/offline_sync_test.dart`

## PR 5: Coverage tests (keep optional behavior, reduce flake)

### 5.1 Update coverage taps to be hit-testable aware
Steps:
1) Replace `.exists` gating with `tapIfHitTestable` to avoid "not hit-testable" failures.
2) Keep non-failing behavior for optional UI.
Files:
- `integration_test/patrol/e2e_tests/ui_button_coverage_test.dart`

## PR 6: Verification

### 6.1 Execute batched runs
Steps:
1) Run `pwsh -File run_patrol_batched.ps1`.
2) If time-limited, run only the batches containing modified files.
Success criteria:
- No silent skips; missing seeds fail with diagnostics.
- No "widget found but not hit-testable" errors.
- Quantities flow tests take >10s and interact with calendar.
Files:
- `run_patrol_batched.ps1`
