# PR Plan: Stabilize Entry Wizard E2E Hit-Testability

## Problem Summary
Entry lifecycle tests intermittently fail with "found but not hit-testable" on `entry_wizard_activities`. The Entry Wizard is a long `SingleChildScrollView`; the activities field can be off-screen or partially obscured (keyboard), so taps target a non-hit-testable center point.

## Goals
- Make Entry Wizard scrolling deterministic for E2E tests.
- Ensure text fields and dropdowns are hit-testable before interaction.
- Keep changes minimal and isolated to the Entry Wizard test flow.

## Phase 1: Add Deterministic Scroll Targets (PR Size: small)
### 1.1 Add a scroll view key for the Entry Wizard
- Step: Add `TestingKeys.entryWizardScrollView`.
- Step: Wire the key to the `SingleChildScrollView` in the Entry Wizard.
- Reason: Tests need a stable scrollable to target when bringing fields into view.
- Files:
  - `lib/shared/testing_keys.dart`
  - `lib/features/entries/presentation/screens/entry_wizard_screen.dart`

### 1.2 Add a hit-testable scroll helper
- Step: Add a helper in `PatrolTestHelpers` that:
  - dismisses the keyboard,
  - scrolls using `view: find.byKey(TestingKeys.entryWizardScrollView)`,
  - calls `ensureVisible`, and
  - asserts `hitTestable()` before tap.
- Step: Use this helper inside `fillEntryField` and `selectFromDropdown` so all entry wizard inputs benefit.
- Reason: Centralizing this logic prevents repeated, flaky scroll/tap sequences in tests.
- Files:
  - `integration_test/patrol/helpers/patrol_test_helpers.dart`

## Phase 2: Update Entry Wizard E2E Tests (PR Size: small)
### 2.1 Entry lifecycle flow
- Step: Remove direct `scrollTo()` calls and rely on the updated helper methods.
- Step: Add explicit keyboard dismiss before lower-section interactions if needed.
- Reason: Keeps the test aligned with the new deterministic scroll behavior.
- Files:
  - `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`

### 2.2 Entry management flow
- Step: Replace any direct scroll/tap sequences with helper usage for activities/weather fields.
- Reason: Avoid the same hit-testable failure in related entry tests.
- Files:
  - `integration_test/patrol/e2e_tests/entry_management_test.dart`

## Phase 3: Verification (PR Size: small)
### 3.1 Targeted patrol runs
- Step: Run entry lifecycle and entry management tests in isolation to confirm no hit-testable errors.
- Suggested commands:
  - `pwsh -File run_patrol.ps1 -TestFile "integration_test/patrol/e2e_tests/entry_lifecycle_test.dart"`
  - `pwsh -File run_patrol.ps1 -TestFile "integration_test/patrol/e2e_tests/entry_management_test.dart"`
- Reason: Confirms the fix eliminates intermittent scroll/tap failures without regressing other flows.
