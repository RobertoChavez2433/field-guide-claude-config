# PR Plan: Comprehensive TestingKeys Coverage

## Goal
Ensure every actionable UI element (buttons, tabs, dialogs, menu items, toggles, list actions) is wired to `TestingKeys` so future E2E tests can be written without text selectors, and update the new project setup flow test to use keys only.

## Phase 0: Inventory + Key Map (PR Size: small)
### 0.1 Establish scope and naming conventions
- Step: Confirm naming scheme for new keys (prefix by feature, use noun_action). Example: `projectsSearchOpenButton`, `reportExportPdfButton`.
- Step: Add a short key taxonomy section to `lib/shared/testing_keys.dart` to keep future additions consistent.
- Reason: Avoid key drift and future test ambiguity.

### 0.2 Produce an element-to-key mapping table
- Step: Generate a checklist of all unkeyed UI actions discovered in screens/widgets. Reference files below.
- Step: For each action, define a key name and dynamic key signature if needed.
- Reason: Prevent missed coverage and keep key count auditable.
- Files:
  - `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`
  - `lib/features/projects/presentation/screens/project_list_screen.dart`
  - `lib/features/projects/presentation/screens/project_setup_screen.dart`
  - `lib/features/settings/presentation/screens/settings_screen.dart`
  - `lib/features/settings/presentation/screens/personnel_types_screen.dart`
  - `lib/features/entries/presentation/screens/home_screen.dart`
  - `lib/features/entries/presentation/screens/entries_list_screen.dart`
  - `lib/features/entries/presentation/screens/entry_wizard_screen.dart`
  - `lib/features/entries/presentation/screens/report_screen.dart`
  - `lib/features/quantities/presentation/screens/quantities_screen.dart`
  - `lib/features/pdf/presentation/widgets/import_type_dialog.dart`
  - `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`
  - `lib/features/photos/presentation/widgets/photo_source_dialog.dart`
  - `lib/features/photos/presentation/widgets/photo_thumbnail.dart`
  - `lib/features/photos/presentation/widgets/photo_name_dialog.dart`
  - `lib/shared/widgets/confirmation_dialog.dart`
  - `lib/shared/widgets/permission_dialog.dart`
  - `lib/features/auth/presentation/screens/login_screen.dart`
  - `lib/features/auth/presentation/screens/register_screen.dart`
  - `lib/features/auth/presentation/screens/forgot_password_screen.dart`

## Phase 1: Centralize Keys (PR Size: medium) ✅ COMPLETE (Session 98)
### 1.1 Expand `TestingKeys` with comprehensive coverage
- Step: Add new static keys and dynamic key helpers for all actions and dialogs identified in Phase 0.
- Step: Add generic dialog action key helper (e.g., `confirmationDialogAction(String action)`), and remove ad-hoc `Key('confirmation_dialog_...')` usage.
- Reason: Single source of truth avoids hardcoded selectors and flakiness.
- Files:
  - `lib/shared/testing_keys.dart` ✅
  - `lib/shared/widgets/confirmation_dialog.dart` ✅ (already wired)

### 1.2 Wire dialog keys for shared components ✅ COMPLETE (Session 98)
- Step: Add keys to storage permission dialog and shared photo dialogs.
- Reason: These are common in E2E flows (export, photo capture) and need reliable selectors.
- Files:
  - `lib/shared/widgets/permission_dialog.dart` ✅ (4 keys)
  - `lib/features/photos/presentation/widgets/photo_name_dialog.dart` ✅ (6 keys)
  - `lib/features/photos/presentation/widgets/photo_source_dialog.dart` ✅ (already wired)
  - `lib/features/photos/presentation/widgets/photo_thumbnail.dart` ✅ (already wired)

## Phase 2: Feature Wiring (PR Size: large; split if needed) ✅ COMPLETE (Session 98)
### 2.1 Auth flows ✅ COMPLETE (Session 98)
- Step: Add keys to visibility toggles and any missing fields/buttons.
- Reason: Auth tests and future login flows require stable selectors.
- Files:
  - `lib/features/auth/presentation/screens/login_screen.dart` ✅ (5 keys)
  - `lib/features/auth/presentation/screens/register_screen.dart` ✅ (4 keys)
  - `lib/features/auth/presentation/screens/forgot_password_screen.dart` ✅ (1 key)

### 2.2 Dashboard + Projects ✅ COMPLETE (Session 98)
- Step: Key "View Projects", "Switch project", and dashboard CTA buttons.
- Step: Key project list search open/close, retry, archive toggle, delete flows.
- Step: Key project setup dialogs for locations/contractors/equipment/pay items.
- Reason: Project creation/edit flows are core E2E paths.
- Files:
  - `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` ✅ (5 keys)
  - `lib/features/projects/presentation/screens/project_list_screen.dart` ✅ (8 keys)
  - `lib/features/projects/presentation/screens/project_setup_screen.dart` ✅ (24 keys)

### 2.3 Settings + Personnel Types ✅ COMPLETE (Session 98)
- Step: Key edit name/initials dialogs, sign-out dialog, clear cache dialog.
- Step: Key personnel type add/edit/delete dialogs and actions.
- Reason: Settings and personnel types are common cross-cutting test steps.
- Files:
  - `lib/features/settings/presentation/screens/settings_screen.dart` ✅ (9 keys)
  - `lib/features/settings/presentation/screens/personnel_types_screen.dart` ✅ (15 keys)

### 2.4 Entries (Home, List, Wizard, Report) ✅ COMPLETE (Session 98)
- Step: Key calendar controls, view/create project CTAs, and preview actions.
- Step: Key entries list filters, refresh, retry, delete dialog.
- Step: Key entry wizard add personnel/equipment dialogs and action buttons.
- Step: Key report actions (export/share/menu, photo dialog actions).
- Reason: E2E entry flows rely on these elements.
- Files:
  - `lib/features/entries/presentation/screens/home_screen.dart` ✅ COMPLETE (Session 97)
  - `lib/features/entries/presentation/screens/entries_list_screen.dart` ✅ COMPLETE (Session 98)
  - `lib/features/entries/presentation/screens/entry_wizard_screen.dart` ✅ COMPLETE (Session 97)
  - `lib/features/entries/presentation/screens/report_screen.dart` ✅ COMPLETE (Session 98)

**Session 97 Keys Added**:
- Home Screen (10 keys): `homeJumpToLatestButton`, `homeCreateProjectButton`, `homeViewProjectsButton`, `homeSwitchProjectButton`, `homeCreateEntryButton`, `homeViewFullReportButton`, `homeCalendarFormatMonth`, `homeCalendarFormatTwoWeeks`, `homeCalendarFormatWeek`
- Entry Wizard (1 key): `wizardAddEquipmentButton(contractorId)`

**Session 98 Keys Added**:
- Entries List (8 keys): `entriesListFilterButton`, `entriesListClearFilterButton`, `entriesListRefreshButton`, `entriesListRetryButton`, `entriesListCreateEntryButton`, `entriesListClearFilterEmptyButton`, `entriesListDeleteCancelButton`, `entriesListDeleteConfirmButton`
- Report Screen (50+ keys): Export, menu, sections, contractors, quantities, photos, PDF dialogs

### 2.5 Quantities + PDF Import ✅ COMPLETE (Session 98)
- Step: Key import/sort/search controls and PDF dialogs.
- Step: Key import preview actions and edit dialogs.
- Reason: Quantities and PDF import are complex flows and need stable hooks.
- Files:
  - `lib/features/quantities/presentation/screens/quantities_screen.dart` ✅ (8 keys)
  - `lib/features/pdf/presentation/widgets/import_type_dialog.dart` ✅ (5 keys)
  - `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart` ✅ (14 keys)

## Phase 3: Test Update (PR Size: small)
### 3.1 Update project setup E2E test to keys-only
- Step: Replace text-based finders with `TestingKeys` selectors for all interactions.
- Reason: Enforce consistency with new key coverage.
- File:
  - `integration_test/patrol/e2e_tests/project_setup_flow_test.dart`

## Phase 4: Verification (PR Size: small)
### 4.1 Targeted E2E checks
- Step: Run project setup flow test and at least one smoke/navigation test to verify new keys don’t regress UI.
- Suggested commands:
  - `pwsh -File run_patrol.ps1 -TestFile "integration_test/patrol/e2e_tests/project_setup_flow_test.dart"`
  - `pwsh -File run_patrol.ps1 -TestFile "integration_test/patrol/e2e_tests/navigation_flow_test.dart"`

## Notes
- Existing keys already cover many core flows; new keys should be additive and non-breaking.
- If Phase 2 grows too large, split by feature (Projects, Entries, Settings) into separate PRs.
