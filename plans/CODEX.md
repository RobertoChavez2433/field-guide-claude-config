# CODEX Review - E2E/Golden Testing

Date: 2026-01-22

## Findings (ordered by severity)
- Critical: Patrol bundle and batched runner only include top-level tests; `integration_test/patrol/e2e_tests` and `integration_test/patrol/isolated` do not run at all, so E2E coverage is lower than expected.
  - Files: `integration_test/test_bundle.dart`, `run_patrol_batched.ps1`
- High: Project tests reference deprecated keys (`projects_tab`, `project_card_`) that do not match UI keys (`projects_nav_button`, `project_card_{id}`), so tests are no-ops or fail to find targets.
  - Files: `integration_test/patrol/project_management_test.dart`, `lib/core/router/app_router.dart`, `lib/features/projects/presentation/screens/project_list_screen.dart`
- High: Helper key drift (`#nav_home`, `#nav_projects`, `#nav_dashboard`, `#nav_settings`, `#settings_sign_out_button`) does not exist in UI, breaking helper-based flows.
  - Files: `integration_test/helpers/auth_test_helper.dart`, `integration_test/helpers/navigation_helper.dart`, `lib/core/router/app_router.dart`, `lib/features/settings/presentation/screens/settings_screen.dart`
- High: Entry wizard tests expect nonexistent keys (`entry_wizard_save`, `entry_wizard_finalize`, `entry_wizard_complete`) and treat `entry_wizard_save_draft` as a normal button even though it only appears in the unsaved-changes dialog.
  - Files: `integration_test/patrol/entry_management_test.dart`, `lib/features/entries/presentation/screens/entry_wizard_screen.dart`, `lib/shared/widgets/confirmation_dialog.dart`
- High: Confirmation dialog cancel key mismatch (`confirmation_dialog_cancel` vs `cancel_dialog_button`/`unsaved_changes_cancel`) breaks cancel flows.
  - Files: `integration_test/patrol/helpers/patrol_test_helpers.dart`, `lib/shared/widgets/confirmation_dialog.dart`
- Medium: Auth gating inconsistent; several tests assume home screen and will fail when Supabase auth is configured.
  - Files: `integration_test/patrol/entry_management_test.dart`, `integration_test/patrol/offline_mode_test.dart`
- Medium: Docs and helpers are out of sync (helper constructor, nav keys), causing confusion and broken usage.
  - Files: `integration_test/patrol/helpers/README.md`, `integration_test/helpers/README.md`
- Medium: Project helper uses text-based finders that do not match label text (e.g., "Project Name *"), making it brittle.
  - Files: `integration_test/patrol/helpers/patrol_test_helpers.dart`, `lib/features/projects/presentation/screens/project_setup_screen.dart`
- Low: Golden tests define a tolerant comparator but do not wire it globally; `test/golden/pdf/failures` contains generated artifacts.
  - Files: `test/golden/test_helpers.dart`, `test/golden/pdf/failures/`
- Low: Patrol version in docs does not match `pubspec.yaml`.
  - Files: `integration_test/patrol/README.md`, `pubspec.yaml`

## Why this matters
- Tests that do not run or cannot find widgets give a false sense of coverage.
- Key drift causes flaky or no-op tests, which undermines confidence and wastes debugging time.
- Lack of a single, reliable startup/auth path means tests are sensitive to environment setup.
- E2E scale requires deterministic selectors, predictable data setup, and isolated state resets.

## Plan (high-level)
1. Decide E2E runtime mode (offline bypass vs test account login) and add a single "ensure-ready" helper to standardize startup and auth.
2. Normalize selectors by aligning test keys and helpers with actual UI keys; add missing UI keys where needed.
3. Update Patrol targets and the batch runner so `e2e_tests` and `isolated` suites run.
4. Convert brittle finders to key-based selectors (e.g., `project_name_field`).
5. Remove hard sleeps in E2E tests; prefer `waitUntilVisible` and condition-based waits.
6. Stabilize goldens: wire a global comparator and ignore generated failure artifacts.

## Suggested next actions
- Fix the Patrol bundle and batch runner first so new E2E tests actually execute.
- Then reconcile keys + helpers to eliminate the biggest class of failures.
