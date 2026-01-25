# PR Plan: Rebuild Entry Lifecycle + Entry Management E2E Tests

## Problem Summary
- Current entry tests are fragmented and rely on ad hoc scrolling, which does not match the structured logging + helper-driven style used in `auth_flow_test.dart` and `contractors_flow_test.dart`. This increases flakiness and makes failures hard to diagnose. Files: `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`, `integration_test/patrol/e2e_tests/entry_management_test.dart`, `integration_test/patrol/helpers/patrol_test_helpers.dart`.
- The requested flow exercises several Entry Wizard sections (location, weather, personnel, equipment, quantities, activities) that are spread across multiple widgets and dialogs. Some dialogs do not yet wire their fields/actions to `TestingKeys`, which blocks reliable interaction. Files: `lib/features/entries/presentation/screens/entry_wizard_screen.dart`, `lib/features/entries/presentation/widgets/entry_basics_section.dart`, `lib/shared/testing_keys.dart`.
- You want end-to-end tests to press all clickable/tappable UI elements and open their dialogs, so missing keys or untested buttons are a coverage gap. Files: `lib/shared/testing_keys.dart`, `integration_test/patrol/REQUIRED_UI_KEYS.md`.
- The seed data names/IDs must be used directly instead of hardcoded strings to keep tests deterministic. Files: `integration_test/patrol/fixtures/test_seed_data.dart`, `integration_test/patrol/helpers/patrol_test_helpers.dart`.

## Target Flow (for the rebuilt entry lifecycle test)
Login -> View projects -> Select seed project -> Calendar bottom nav -> Create entry:
- Choose a location (seed location)
- Weather auto-fetch (verify auto-filled temps; if not filled, tap `TestingKeys.weatherFetchButton`)
- Add a personnel type, increment counts (+1 each)
- Toggle equipment for prime and sub contractor
- Select a subcontractor
- Add activities paragraph
- Add quantities (choose multiple bid items)
- Delete a contractor (actual delete of the subcontractor record created for tests)
- Delete a personnel type
- Generate report and verify report screen
- Exhaustively test the report edit screen: press all clickable/tappable elements and open/close every dialog on the report screen

## Open Questions / Assumptions
- Contractor deletion should be performed in the Contractors setup UI using `TestingKeys.contractorDeleteButton(...)` (not just deselecting in the Entry Wizard). If that delete action is missing, we will add it.
- Weather auto-fetch: the test will assert auto-filled values if available, otherwise it will tap `TestingKeys.weatherFetchButton` and verify temps are populated (no hard fail on fetch errors unless you want it strict).
- Personnel types may be empty by default; the flow will add a type via the Entry Wizard dialog, which currently has no TestingKeys wired to its fields/buttons.

## Phase 1: Map the UI and required keys (PR Size: small)
### 1.1 Compare entry tests to auth/contractor test style
- Step: Review auth and contractor tests to capture the expected structure: helper-driven steps, explicit waits, and logging.
- Reason: Rebuilt entry tests should follow this pattern for consistent diagnostics.
- Files:
  - `integration_test/patrol/e2e_tests/auth_flow_test.dart`
  - `integration_test/patrol/e2e_tests/contractors_flow_test.dart`
  - `integration_test/patrol/helpers/patrol_test_helpers.dart`

### 1.2 Map each target flow step to concrete widgets and keys
- Step: Trace the Entry Wizard and Report UI to list which keys are already wired and which are missing for:
  - Location + weather controls
  - Contractor selection
  - Personnel type add/delete
  - Equipment add/toggle/delete
  - Quantities add/select/edit/delete
  - Generate report
- Reason: The new tests must use `TestingKeys` end-to-end; missing wiring must be identified before rebuilding tests.
- Files:
  - `lib/features/entries/presentation/widgets/entry_basics_section.dart`
  - `lib/features/entries/presentation/screens/entry_wizard_screen.dart`
  - `lib/features/entries/presentation/screens/report_screen.dart`
  - `lib/shared/testing_keys.dart`

### 1.3 Align seed data usage with deterministic IDs
- Step: Document which seed IDs/names will be used for location, contractors, and bid items in the new test flow.
- Reason: Avoid hardcoded strings and reduce flaky selector failures.
- Files:
  - `integration_test/patrol/fixtures/test_seed_data.dart`

### 1.4 Build a UI coverage checklist (clickables + dialogs)
- Step: Enumerate every clickable/tappable element and dialog across the entry + report + contractor setup surfaces and map them to `TestingKeys`.
- Step: Flag any missing keys for addition in Phase 2.
- Reason: You want a comprehensive suite that presses all UI buttons and opens all dialogs, so we need a coverage matrix before writing tests.
- Files:
  - `lib/shared/testing_keys.dart`
  - `integration_test/patrol/REQUIRED_UI_KEYS.md`

## Phase 2: Add missing TestingKeys and helpers for the flow (PR Size: medium)
### 2.1 Wire Entry Wizard dialogs to TestingKeys
- Step: Add keys for the add-personnel-type dialog fields and actions, and the add-equipment dialog fields/actions.
- Step: Add keys for delete actions if the test requires explicit deletion (personnel type delete, equipment delete, contractor delete).
- Reason: The flow requires creating and removing items reliably without relying on text-only finders or long-press gestures.
- Files:
  - `lib/shared/testing_keys.dart`
  - `lib/features/entries/presentation/screens/entry_wizard_screen.dart`

### 2.2 Add helper methods to match auth/contractor test style
- Step: Extend helpers with targeted, logged actions (ex: select seed project, wait for weather auto-fill, add personnel type, increment counters, toggle equipment, add quantities, delete personnel type, generate report).
- Reason: Keeps entry tests short and readable like `auth_flow_test.dart` and `contractors_flow_test.dart`.
- Files:
  - `integration_test/patrol/helpers/patrol_test_helpers.dart`

### 2.3 Add delete contractor coverage in setup flow
- Step: Add or wire delete buttons for contractor cards in project setup so tests can delete the subcontractor created for testing.
- Step: Add helper for delete confirmation dialog handling on contractor delete.
- Reason: The requested flow includes deleting the subcontractor record, which is currently only testable if delete UI is keyed.
- Files:
  - `lib/shared/testing_keys.dart`
  - `lib/features/projects/presentation/screens/project_setup_screen.dart`
  - `integration_test/patrol/helpers/patrol_test_helpers.dart`

## Phase 3: Rebuild entry_lifecycle_test.dart (PR Size: medium)
### 3.1 Replace existing tests with one full-flow scenario
- Step: Create a single "E2E: entry creation + report edit flow" test that follows the target flow exactly and uses helper methods with explicit waits and logging.
- Step: Use `TestSeedData.projectId`, `TestSeedData.locationId`, `TestSeedData.subContractorId`, `TestSeedData.bidItemId`/`bidItemId2` for deterministic selection.
- Step: On the report screen, tap every clickable/tappable element and open/close all dialogs (export, menu, edit sections, add quantity, add photo, delete dialogs), then assert sections via `TestingKeys.report*`.
- Reason: This provides end-to-end coverage plus exhaustive report edit coverage in a single, stable test.
- Files:
  - `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`
  - `integration_test/patrol/fixtures/test_seed_data.dart`

### 3.2 Expand coverage to hit more Entry Wizard UI buttons
- Step: Add sub-steps to exercise all buttons and dialogs in the Entry Wizard during the same flow:
  - Tap `TestingKeys.weatherFetchButton` (if auto-fetch did not populate temps).
  - Add personnel type via dialog (name + short code), then increment and decrement counters via `TestingKeys.personnelIncrement(...)` / `TestingKeys.personnelDecrement(...)`.
  - Add equipment via dialog, toggle equipment chips, and confirm delete equipment flow (if delete UI is added).
  - Add quantity via quantity dialog + bid item picker search, edit quantity inline, then delete a quantity.
  - Open add photo flow and cancel (to hit the buttons without needing a real file).
- Reason: Ensures exhaustive coverage of all Entry Wizard clickables.
- Files:
  - `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`
  - `integration_test/patrol/helpers/patrol_test_helpers.dart`
  - `lib/shared/testing_keys.dart`
  - `lib/features/entries/presentation/screens/entry_wizard_screen.dart`

## Phase 4: Rebuild entry_management_test.dart (PR Size: medium)
### 4.1 Consolidate to a small set of focused, stable tests
- Step: Replace the current multi-test set with 2-3 tests that validate key entry behaviors (open wizard, edit existing entry, cancel flow) using the same helper-driven style.
- Step: Remove redundant, brittle scroll-based tests in favor of the new helpers.
- Reason: Keeps entry management tests consistent with the auth/contractor patterns and avoids flakiness.
- Files:
  - `integration_test/patrol/e2e_tests/entry_management_test.dart`
  - `integration_test/patrol/helpers/patrol_test_helpers.dart`

### 4.2 Keep a separate report-screen coverage test (optional backstop)
- Step: If desired, keep a focused report test that opens a seeded entry report and replays all report clickables as a safety net.
- Reason: Provides a faster regression check when the full entry lifecycle test is too slow.
- Files:
  - `integration_test/patrol/e2e_tests/entry_management_test.dart`
  - `lib/shared/testing_keys.dart`
  - `lib/features/entries/presentation/screens/report_screen.dart`

## Phase 5: Expand comprehensive UI button coverage (PR Size: medium)
### 5.1 Add per-screen "button coverage" tests
- Step: Create targeted tests that open each screen and press all tappable widgets, then open and close each dialog:
  - Projects list + project setup tabs
  - Contractors setup
  - Quantities screen
  - Settings screen (toggles, dialogs)
- Reason: Provides broad, deterministic coverage of all UI clickables beyond entry/report flows.
- Files:
  - `integration_test/patrol/e2e_tests/*`
  - `integration_test/patrol/helpers/patrol_test_helpers.dart`
  - `lib/shared/testing_keys.dart`

## Phase 6: Verification (PR Size: small)
### 5.1 Targeted patrol runs
- Step: Run rebuilt entry tests individually to verify stability.
- Suggested commands:
  - `pwsh -File run_patrol.ps1 -TestFile "integration_test/patrol/e2e_tests/entry_lifecycle_test.dart"`
  - `pwsh -File run_patrol.ps1 -TestFile "integration_test/patrol/e2e_tests/entry_management_test.dart"`
- Reason: Confirms the new flows work end-to-end without the existing stuck states.
