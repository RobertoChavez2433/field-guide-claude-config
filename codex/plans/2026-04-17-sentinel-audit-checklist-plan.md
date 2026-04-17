# Sentinel Audit Checklist Plan

Date: 2026-04-17

Status: P0-P2 implementation complete; P3 live dual-device rerun deferred.

Latest implementation note, 2026-04-17:

- P0 route root sentinels and route-visible screen contracts are implemented for the first audit batch.
- P1 entry/review dialogs plus PDF and M&P progress dialogs now have root/action/state sentinels.
- P0 root audit was rerun before the second batch; the previously listed P0 roots are visibly wired, and `EntryPdfPreviewScreen` now uses `entryPdfPreviewScreen` as the canonical root while retaining `reportPdfPreviewDialog` as a compatibility subtree.
- P1/P2 second batch now covers pay-app detail, contractor comparison, manual match, export history, form gallery, MDOT 1126/1174, gallery viewer, project delete sheet, calculator history delete, and PDF/M&P preview empty/blocked states.
- Entry review now exposes stable action/state sentinels for to-do comments, ready/skipped counts, review-summary sections, submit confirmation, and submit progress; the driver contracts advertise those sentinels.
- Stale form, MDOT row, quantity row/card, document, contractor, and report workflow sentinel definitions that had no production widget attachment were removed instead of preserved as false reference points.
- Generic `AppDialog` helpers now keep their shared default keys but accept workflow-specific root/action keys at call sites; the remaining string-only `TestingKeys` constants were converted to real `Key` sentinels.
- Verification so far:
  - `flutter test test/core/driver/registry_alignment_test.dart`
  - `flutter test test/core/router/app_router_test.dart`
  - root sentinel widget tests split by surface:
    - `test/core/driver/root_sentinel_auth_widget_test.dart`
    - `test/core/driver/root_sentinel_entry_form_widget_test.dart`
    - `test/core/driver/root_sentinel_project_widget_test.dart`
  - targeted widget tests for entry PDF preview, pay-app/contractor/export-history dialogs, project delete sheet, calculator history, PDF/M&P preview states, form gallery, and gallery viewer
  - targeted widget tests for entry-review/review-summary sentinels, entry-editor dialogs, PDF/M&P import progress dialogs, and generic `AppDialog` workflow-specific keys
  - `flutter analyze`
  - `dart run custom_lint`
- Latest gate status: P0-P2 implementation and automated static/widget verification are complete. The S21/S10 live dual-device rerun remains intentionally open and deferred by request so it can be run as the next manual device pass.

Source of truth: this checklist is the completion gate for the next sentinel-hardening pass. Each implementation pass should re-open this file, mark confirmed fixes, and only close the pass when the relevant route, driver contract, widget sentinel, and verification test all agree.

## Audit Inputs

- CodeMunch was re-indexed against the current working tree on 2026-04-17: `local/Field_Guide_App-37debbe5`, 16,477 symbols.
- Router surfaces reviewed:
  - `lib/core/router/app_router.dart`
  - `lib/core/router/routes/auth_routes.dart`
  - `lib/core/router/routes/entry_routes.dart`
  - `lib/core/router/routes/form_routes.dart`
  - `lib/core/router/routes/pay_app_routes.dart`
  - `lib/core/router/routes/project_routes.dart`
  - `lib/core/router/routes/settings_routes.dart`
  - `lib/core/router/routes/sync_routes.dart`
  - `lib/core/router/routes/toolbox_routes.dart`
- Driver surfaces reviewed:
  - `lib/core/driver/screen_contract_registry.dart`
  - `lib/core/driver/screen_registry.dart`
  - `lib/core/driver/flows/forms_flow_definitions.dart`
  - `lib/core/driver/flows/navigation_flow_definitions.dart`
  - `lib/core/driver/flows/verification_flow_definitions.dart`
  - `test/core/driver/registry_alignment_test.dart`
- Sentinel exports reviewed under `lib/shared/testing_keys/`.
- Workflow hot spots reviewed from the latest route/button/widget audit:
  - entries and review dialogs
  - PDF/M&P import progress
  - pay-app import/export/compare
  - forms and MDOT form states
  - gallery/photo viewer
  - destructive project and calculator history dialogs

## Sentinel Policy

- [x] Every app-router `GoRoute` that can render a screen must have a stable root sentinel on the rendered screen's root scaffold, root layout, or equivalent top-level host.
- [x] Every driver `ScreenContract.rootKey` must be visibly rendered by the screen it names.
- [x] Every route-visible screen with a root sentinel must have an intentional driver stance:
  - a `ScreenContract`, or
  - an explicit documented exclusion if it is not part of driver flows.
- [x] Every driver-flow-only route must be documented as virtual driver coverage or promoted into the app router.
- [x] Every workflow-critical action must have a `TestingKeys` action sentinel.
- [x] Every modal, dialog, and bottom sheet that gates a workflow must have a root sentinel plus keyed confirm/cancel/destructive actions.
- [x] Every observable loading, empty, error, blocked, permission, denied, import/export progress, and sync state that a dual-device run may need to distinguish must have a state sentinel.
- [x] Do not add test-only hooks or `MOCK_AUTH`. Sentinels must observe real production widgets and real backend-authenticated flows.

## P0: Root Sentinel And Contract Alignment

These items block reliable route-level dual-device verification.

### Missing Or Weak Route Root Sentinels

- [x] Attach `TestingKeys.updatePasswordScreen` to the root of `UpdatePasswordScreen`.
  - Route: `/update-password` in `lib/core/router/routes/auth_routes.dart`.
  - Current finding: only `TestingKeys.updatePasswordScreenTitle` is used in production.
  - Key exists: `lib/shared/testing_keys/auth_keys.dart`.

- [x] Attach `TestingKeys.updateRequiredScreen` to the root of `UpdateRequiredScreen`.
  - Route: `/update-required`.
  - Key exists but no production root usage was found.

- [x] Attach `TestingKeys.profileSetupScreen` to the root of `ProfileSetupScreen`.
  - Route: `/profile-setup`.
  - Key exists but no production root usage was found.

- [x] Attach `TestingKeys.companySetupScreen` to the root of `CompanySetupScreen`.
  - Route: `/company-setup`.
  - Key exists but no production root usage was found.

- [x] Attach `TestingKeys.pendingApprovalScreen` to the root of `PendingApprovalScreen`.
  - Route: `/pending-approval`.
  - Key exists but no production root usage was found.

- [x] Attach `TestingKeys.accountStatusScreen` to the root of `AccountStatusScreen`.
  - Route: `/account-status`.
  - Key exists but no production root usage was found.

- [x] Attach `TestingKeys.entryEditorScreen` to the actual `EntryEditorScreen` root.
  - Routes: `/entry/:projectId/:date`, `/report/:entryId`.
  - Existing contracts already expect `TestingKeys.entryEditorScreen`.
  - Current finding: production usage was not found outside driver contracts/tests/exports.

- [x] Attach `TestingKeys.formNewDispatcherScreen` to the root of `FormNewDispatcherScreen`.
  - Route: `/form/new/:formId`.
  - Key exists but no production root usage was found.

- [x] Attach `TestingKeys.helpSupportScreen` to the root of `HelpSupportScreen`.
  - Route: `/help-support`.
  - Key exists but no production root usage was found.

- [x] Attach `TestingKeys.legalDocumentScreen` to the root of `LegalDocumentScreen`.
  - Route: `/legal-document`.
  - Key exists but no production root usage was found.

- [x] Attach `TestingKeys.ossLicensesScreen` to the root of `OssLicensesScreen`.
  - Route: `/oss-licenses`.
  - Key exists but no production root usage was found.

### Contracted Roots That Are Not Actually Distinguishable

- [x] Resolve `ProjectSetupNewScreen` and `ProjectSetupEditScreen` contract root behavior.
  - Current contracts expect `TestingKeys.projectSetupNewScreen` and `TestingKeys.projectSetupEditScreen`.
  - Actual `ProjectSetupScreen` root currently uses `TestingKeys.projectSetupScreen`.
  - Choose one:
    - attach mode-specific root sentinels based on create/edit mode, or
    - collapse the driver contracts to the generic `ProjectSetupScreen` contract and remove mode-specific route-root expectations.

- [x] Resolve `EntryEditorCreateScreen` and `EntryEditorReportScreen` contract semantics.
  - Current contracts share `TestingKeys.entryEditorScreen`.
  - If the driver must distinguish create vs report mode, add visible mode/state sentinels.
  - If not, document both as route aliases for the same root contract.

- [x] Resolve `EntryPdfPreviewScreen` root naming.
  - Existing widget/test uses `TestingKeys.reportPdfPreviewDialog`.
  - `TestingKeys.entryPdfPreviewScreen` exists but is not used.
  - Choose one canonical sentinel and remove or reattach the other.
  - Latest decision: `TestingKeys.entryPdfPreviewScreen` is the canonical root; `TestingKeys.reportPdfPreviewDialog` remains attached as a nested compatibility sentinel for existing report-PDF flows/tests.

### Route-Visible Screens Missing Driver Contracts

- [x] Add `ScreenContract` coverage for `RegisterScreen`.
  - Route: `/register`.
  - Root exists: `TestingKeys.registerScreen`.
  - Registry exists, but contract is missing.

- [x] Add `ScreenContract` coverage for `ForgotPasswordScreen`.
  - Route: `/forgot-password`.
  - Root exists: `TestingKeys.forgotPasswordScreen`.
  - Registry exists, but contract is missing.

- [x] Add `ScreenContract` coverage for `OtpVerificationScreen`.
  - Route: `/verify-otp`.
  - Root exists via split layout.

- [x] Add `ScreenContract` coverage for `UpdatePasswordScreen` after the root sentinel is attached.
  - Route: `/update-password`.

- [x] Add `ScreenContract` coverage for `UpdateRequiredScreen` after the root sentinel is attached.
  - Route: `/update-required`.

- [x] Add `ScreenContract` coverage for `ConsentScreen`.
  - Route: `/consent`.
  - Root exists via `ConsentTestingKeys.consentScreen`.

- [x] Add `ScreenContract` coverage for `ProfileSetupScreen` after the root sentinel is attached.
  - Route: `/profile-setup`.

- [x] Add `ScreenContract` coverage for `CompanySetupScreen` after the root sentinel is attached.
  - Route: `/company-setup`.

- [x] Add `ScreenContract` coverage for `PendingApprovalScreen` after the root sentinel is attached.
  - Route: `/pending-approval`.

- [x] Add `ScreenContract` coverage for `AccountStatusScreen` after the root sentinel is attached.
  - Route: `/account-status`.

- [x] Add `ScreenContract` coverage for `HomeScreen`.
  - Route: `/calendar`.
  - Root exists: `TestingKeys.homeScreen`.
  - Registry exists, but contract is missing.

- [x] Add `ScreenContract` coverage for `DraftsListScreen`.
  - Route: `/drafts/:projectId`.
  - Root exists: `TestingKeys.draftsListScreen`.

- [x] Add `ScreenContract` coverage for `SettingsSavedExportsScreen`.
  - Route: `/settings/saved-exports`.
  - Root exists: `TestingKeys.settingsSavedExportsScreen`.
  - Also update `settings_deep_link_entry` so it seeds `SettingsSavedExportsScreen`, not just `SettingsScreen`.

- [x] Add `ScreenContract` coverage for `FormNewDispatcherScreen` after the root sentinel is attached.
  - Route: `/form/new/:formId`.

- [x] Add `ScreenContract` coverage for `HelpSupportScreen` after the root sentinel is attached.
  - Route: `/help-support`.

- [x] Add `ScreenContract` coverage for `LegalDocumentScreen` after the root sentinel is attached.
  - Route: `/legal-document`.

- [x] Add `ScreenContract` coverage for `OssLicensesScreen` after the root sentinel is attached.
  - Route: `/oss-licenses`.

### Driver-Only Route Clarification

- [x] Decide whether `/form/:responseId/test`, `/form/:responseId/proctor`, and `/form/:responseId/weights` are intentionally driver-only routes.
  - They exist in `forms_flow_definitions.dart`.
  - They do not exist in the current app `form_routes.dart`.
  - If they are intended production routes, add app-router entries.
  - If they are intentionally virtual driver routes, document them in `forms_flow_definitions.dart` and add an allowlist to the route/contract alignment test.

## P1: Workflow Action, Dialog, And State Sentinels

These items do not always block route detection, but they make user flows brittle or ambiguous in dual-device testing.

### Entry Editor And Review

- [x] Add dialog root and action sentinels for undo submission in `entry_editor_dialogs.dart`.
  - Existing buttons are partially keyed; the dialog host is not.

- [x] Add dialog root and action sentinels for add-location in `entry_editor_dialogs.dart`.
  - Current finding: dialog and actions are unkeyed.

- [x] Add dialog root and action sentinels for discard-empty-draft in `entry_editor_dialogs.dart`.
  - Current finding: dialog and actions are unkeyed.

- [x] Add complete dialog/action sentinels for entry date collision in `entry_editor_dialogs.dart`.
  - Current finding: only two actions are keyed.

- [x] Add root and action sentinels for the review-comment dialog in `entry_review_screen.dart`.
  - Include save/cancel action keys.

- [x] Ensure entry review actions that produce todos, skipped entries, submitted entries, and review summaries have stable action/state keys.

### PDF Import And M&P Import

- [x] Add a root state sentinel to the PDF import progress dialog in `pdf_import_workflow.dart`.
  - This dialog is non-dismissible and must be targetable when extraction stalls.

- [x] Add a root state sentinel to the M&P import progress dialog in `mp_import_helper.dart`.
  - This dialog is non-dismissible and must be targetable when extraction stalls.

- [x] Add state sentinels for import preview blocked/error/empty states where they are not already covered.
  - Include `pdfPreviewErrorBanner` in driver `stateKeys` where relevant.

### Pay Applications, Contractor Comparison, And Export History

- [x] Add root and action sentinels to the replace-confirm dialog in `contractor_comparison_screen.dart`.

- [x] Add a dialog root sentinel to `manual_match_add_row_dialog.dart`.
  - Add action keys for save/cancel if missing.

- [x] Add root/action sentinels to the export artifact history info dialog in `export_artifact_history_list.dart`.

- [x] Add state sentinels to `PayApplicationDetailScreen` loading and not-found states.

- [x] Add or verify action sentinels for pay-app detail share/download/export/delete/compare actions.

- [x] Add state sentinels for contractor comparison loading, empty, import-failed, replacement-required, and export-progress states.

### Forms And MDOT Form Surfaces

- [x] Add loading/error/empty state sentinels to `FormGalleryScreen`.

- [x] Add loading/error/empty state sentinels to `form_gallery_saved_views.dart`.

- [x] Add loading/error/empty or unavailable-state sentinels to `Mdot1126FormScreen`.

- [x] Attach or verify `TestingKeys.mdot1174rFormScreen` on the `Mdot1174rFormScreen` root.

- [x] Add loading/error/empty or unavailable-state sentinels to `Mdot1174rFormScreen`.

- [x] Add dialog root and action sentinels to the inline field-edit dialog in `form_viewer_secondary_sections.dart`.

- [x] Review stale form sentinels and either wire or remove them:
  - `formCard`
  - `formResponsesButton`
  - `formResponseOpenButton`
  - `formResponseDeleteButton`
  - `mdot1174RowField`
  - Latest decision: removed these obsolete definitions and facade exports after confirming no production/test attachment.

### Gallery And Photo Viewer

- [x] Add root/action sentinels to `gallery_photo_viewer.dart`.
  - Include close/back, delete/share/save actions if present.

- [x] Add or verify gallery loading state sentinel in `gallery_screen.dart`.
  - `galleryEmptyState` exists; keep it wired.
  - Verify `galleryErrorState` and `galleryRetryButton` are wired anywhere error UI is displayed.

### Projects, Quantities, Calculator, And Shared Modals

- [x] Add a bottom-sheet host sentinel to project removal flows in `project_list_delete_actions.dart`.

- [x] Add a dialog root sentinel to calculator-history delete confirmation in `calculator_history_section.dart`.
  - Buttons are keyed; the dialog root is not.

- [x] Review quantity row/card sentinels and either wire or remove stale definitions:
  - `quantityCard`
  - `quantityEditButton`
  - `quantityDeleteButton`
  - Latest decision: removed these obsolete definitions and facade exports after confirming no production/test attachment.

- [x] Review document and contractor stale sentinels and either wire or remove them:
  - `documentCard`
  - `documentDeleteButton`
  - `contractorDeleteButton`
  - Latest decision: removed these obsolete definitions and facade exports after confirming no production/test attachment.

- [x] Review report workflow stale sentinels and either wire or remove them:
  - `entryEditButton`
  - `reportPersonnelCounter`
  - `reportEquipmentCheckbox`
  - `reportQuantitySwapButton`
  - `wizardAddEquipmentButton`
  - Latest decision: removed these obsolete definitions and facade exports after confirming no production attachment; the one absence-only widget-test assertion was removed with the stale key.

- [x] Reduce ambiguity from generic shared `AppDialog` sentinels.
  - Current shared generic confirmation/unsaved-change keys are too broad for multi-step manual verification.
  - Keep shared defaults, but allow workflow-specific dialog keys at the call site for high-risk flows.
  - Latest decision: `showConfirmation`, `showDeleteConfirmation`, and `showUnsavedChanges` now accept optional workflow-specific dialog/action keys while preserving default keys.

- [x] Convert the remaining test-only string constants in `testing_keys.dart` into real sentinels or remove them if obsolete.

## P2: Automated Alignment Tests

- [x] Extend `test/core/driver/registry_alignment_test.dart` so it catches more than exported key names.
  - It currently verifies contracts are backed by registry entries and root keys are exported `TestingKeys`.
  - Add coverage for route-visible screens that have no `ScreenContract`.
  - Add coverage for `screenRegistry` entries that intentionally do or do not need contracts.
  - Add an allowlist for driver-only virtual routes.

- [x] Add a route/contract alignment fixture or helper.
  - It should compare app `GoRoute` paths, driver-flow `GoRoute` paths, and `ScreenContract.routes`.
  - It should fail on accidental stale contract routes.
  - It should allow documented virtual driver routes such as form sub-screens if that decision is retained.

- [x] Add widget tests for newly attached root sentinels.
  - Auth/onboarding root screens.
  - Entry editor root.
  - Form new dispatcher root.
  - Support/legal/OSS roots.
  - Project setup create/edit root behavior after the design decision above.
  - Latest evidence: root coverage is split across `test/core/driver/root_sentinel_auth_widget_test.dart`, `test/core/driver/root_sentinel_entry_form_widget_test.dart`, and `test/core/driver/root_sentinel_project_widget_test.dart` to stay inside the import-count lint budget.

- [x] Add widget tests for newly keyed high-risk dialogs.
  - [x] Entry editor dialogs.
  - [x] Review comment/review-summary submit sentinels.
  - [x] PDF/M&P import progress dialogs.
  - [x] Contractor comparison replace-confirm dialog.
  - [x] Manual match add-row dialog.
  - [x] Export artifact history info dialog.
  - [x] Calculator history delete dialog.
  - [x] Project removal bottom sheet.

- [x] Update driver screen contracts with action and state keys after widgets are keyed.
  - Do not add contract keys before the production widgets render them.
  - Latest complete batch: updated for pay-app detail, contractor comparison, form gallery/viewer, gallery, project delete sheet, calculator history, PDF/M&P preview empty/blocked states, and entry review/review summary sentinels.

## P3: Dual-Device Verification Gate

Run this after P0-P2 are complete.

- [x] Run static and unit/widget checks:
  - `flutter analyze`
  - `dart run custom_lint`
  - `flutter test test/core/driver/registry_alignment_test.dart`
  - `flutter test test/core/router/app_router_test.dart`
  - targeted widget tests for each newly keyed root/dialog/state.
  - Latest evidence: all commands above passed on 2026-04-17, including the targeted root/dialog/state batch.

- [ ] Re-run the dual-device S21/S10 driver flows with real auth and real backend state.
  - Deferred by request; keep this open for the next live device pass.

- [ ] Treat a flow cell as failed if any of these occur:
  - the expected root sentinel is missing,
  - a route lands on an unexpected root sentinel,
  - a workflow-critical dialog cannot be targeted,
  - a loading/error/empty/blocked state is visible but not identifiable,
  - screenshots show layout/runtime defects,
  - sync state or debug logs show backend/sync defects.

- [ ] Save new test artifacts under `.claude/test-results/<timestamp>-sentinel-audit-rerun-*`.
  - Deferred with the S21/S10 live rerun.

- [x] Update this checklist with pass/fail notes and any newly discovered sentinel gaps.

## Suggested Implementation Order

1. P0 root attachments for already-exported keys.
2. P0 screen contract additions for route-visible screens.
3. P0 contract cleanup for project setup, entry editor mode aliases, entry PDF preview naming, and driver-only form sub-routes.
4. P1 workflow dialog/state/action sentinels.
5. P2 registry and route alignment tests.
6. P3 dual-device rerun.

## Completion Definition

- [x] Every app `GoRoute` has either a rendered root sentinel contract or a documented exclusion.
- [x] Every `ScreenContract.rootKey` is rendered by the intended production screen.
- [x] Driver-flow-only routes are intentionally documented and tested.
- [x] Workflow-critical dialogs and bottom sheets have root/action sentinels.
- [x] Observable workflow states have state sentinels.
- [x] Alignment tests fail when route, registry, contract, or `TestingKeys` drift apart.
- [ ] Dual-device S21/S10 rerun produces no missing-sentinel failures and no hidden UI/sync defects.
  - Deferred by request; this is the remaining live verification gate.
