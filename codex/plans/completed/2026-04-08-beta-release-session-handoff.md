Date: 2026-04-08
Branch: `sync-engine-refactor`
Status: in progress

# Beta Release Session Handoff

This handoff captures the exact overnight checkpoint so the next session can resume without re-auditing the same ground.

Canonical tracker reference:
- [2026-04-08-beta-central-tracker.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-08-beta-central-tracker.md)
- [2026-04-08-beta-research-inventory.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-08-beta-research-inventory.md)

## Completed This Session

- Re-read the Notion audit export and merged its findings into the unified beta queue.
- Added dead-code cleanup as an explicit beta gate in the unified TODO.
- Closed the standalone form-export validation gap so standalone form export uses export-time validation.
- Added direct form-proof coverage for MDOT 0582B and MDOT 1126 filler/validator paths.
- Re-verified IDR field mapping against the live template and current `PdfService` field map.
- Verified debug PDF generation for shipped templates and exposed debug PDF preview in the forms UI.
- Closed the shipped-forms export proof matrix against live templates and UI-entered data for:
  - IDR
  - MDOT 0582B
  - MDOT 1126
- Fixed stale export mappings so:
  - 0582B now writes the actual shipped header / standards / remarks field names
  - 0582B latest proctor weights now land in the shipped `1st`...`5th` fields
  - 1126 now merges wizard header edits from `responseData['header']` with legacy `headerData`
  - 1126 now writes the actual shipped template fields and uses `Button1` as the signature field name
- Refactored pay-app provider flows behind explicit domain endpoints instead of provider-direct repository access for:
  - pay-app list loading
  - next pay-app number suggestion
  - range validation
  - export preparation
  - pay-app detail loading
  - export-artifact load/delete
  - export-artifact localization
  - export-artifact creation
- Added pay-app proof coverage for:
  - real `.xlsx` workbook cell output
  - same-range replacement preflight
  - overlap-block path
  - export history load/delete
  - detail-screen load/save-copy/share
  - remote-only artifact download/localization before comparison import
  - duplicate contractor row remap-to-review behavior
- Decoupled contractor-comparison discrepancy PDF export from direct `path_provider` lookup by injecting the comparison-report file save seam.
- Added discrepancy export proof for:
  - successful PDF write + export-artifact metadata persistence
  - metadata-create failure cleanup of the local PDF artifact
- Moved generic form-viewer export through `ExportFormUseCase` so standalone form export now persists/shareable PDF artifacts instead of only marking rows exported.
- Added controller proof for the generic form-viewer export path, including preview-required, successful export artifact creation, and null-export failure.
- Added `no_repository_import_in_presentation_logic` with no legacy allowlist so all remaining provider/controller repository drift is surfaced immediately.
- Burned down additional architecture drift by moving these presentation flows behind domain use cases:
  - calculator history load/save/delete
  - todo load/query/mutation flows
  - settings support ticket submission + log-upload flow
- Burned down the next architecture wave by standardizing list-style and stateful presentation seams behind injected use cases for:
  - contractors / equipment / personnel types
  - locations
  - daily entries base list access
  - bid items / entry quantities
  - project assignment selection
  - settings admin / consent
  - entry contractor editing load/save state
- Moved auth sign-out sync-hint teardown behind `RealtimeHintHandler.deactivateChannelForSignOut(...)` so auth no longer owns the private-channel RPC directly.
- Reworked signatures DI wiring so async database resolution now lives in `SignaturesDependencyFactory` instead of the `/di/` file.
- Logged sync delete-change metadata decode failures instead of silently swallowing malformed payloads.
- Closed the half-wired route-restoration gap by persisting/restoring `PreferencesService.lastRoute` through `AppRouter` and filtering non-restorable routes by URI path, including query-param cases.
- Standardized production `go_router` callers onto named routes and added `prefer_named_go_router_navigation` so new hardcoded route strings are surfaced immediately.
- Repaired the stale shell/settings router tests by replacing broken private-field `SyncProvider` mocks with the real provider seam plus lightweight query stubs.
- Replaced the placeholder project-save navigation test with a real route/service-backed widget proof.

## Current Verified Commands

- `flutter analyze`
- `flutter test test/features/pay_applications/presentation/providers`
- `flutter test test/features/pay_applications/presentation/providers/contractor_comparison_provider_test.dart`
- `flutter test test/features/pay_applications/domain/usecases`
- `flutter test test/features/pay_applications/presentation/providers/pay_application_provider_test.dart`
- `flutter test test/features/pay_applications/presentation/providers/export_artifact_provider_test.dart`
- `flutter test test/features/pay_applications/presentation/widgets/export_artifact_history_list_test.dart`
- `flutter test test/features/pay_applications/presentation/screens/pay_application_detail_screen_test.dart`
- `flutter test test/features/quantities/presentation/screens/quantities_screen_export_flow_test.dart`
- `flutter test test/features/quantities/presentation/screens/quantities_screen_pay_app_export_flow_test.dart`
- `flutter test test/features/forms/presentation/controllers/form_viewer_controller_test.dart`
- `flutter test test/features/forms/data/pdf/mdot_0582b_pdf_filler_test.dart`
- `flutter test test/features/forms/data/pdf/mdot_1126_pdf_filler_test.dart`
- `flutter test test/features/forms/services/form_pdf_service_test.dart`
- `flutter test test/features/forms/services/form_pdf_service_debug_test.dart`
- `flutter test test/features/forms/services/form_export_mapping_matrix_test.dart`
- `flutter test test/features/forms/domain/usecases/export_form_use_case_test.dart`
- `flutter test test/services/pdf_field_mapping_test.dart`
- `flutter test test/services/pdf_service_debug_test.dart`
- `flutter test test/features/todos/presentation/providers/todo_provider_filter_test.dart`
- `flutter test test/features/todos/presentation/screens/todos_screen_test.dart`
- `flutter test test/features/calculator/presentation/screens/calculator_screen_test.dart`
- `flutter test test/features/settings/about_section_test.dart`
- `flutter test test/features/settings/presentation/screens/help_support_screen_test.dart`
- `flutter test test/features/entries/presentation/controllers/contractor_editing_controller_test.dart`
- `flutter test test/features/entries/presentation/providers/daily_entry_provider_filter_test.dart`
- `flutter test test/features/projects/presentation/providers/project_assignment_provider_test.dart`
- `flutter test test/features/settings/presentation/providers/consent_provider_test.dart`
- `flutter test test/features/auth/domain/use_cases/sign_out_use_case_test.dart`
- `flutter test test/features/pdf/presentation/screens/mp_import_preview_screen_test.dart`
- `flutter test test/features/quantities/presentation/providers/entry_quantity_provider_extra_test.dart`
- `flutter test test/core/router/app_router_test.dart`
- `flutter test test/core/di/app_bootstrap_test.dart`
- `flutter test test/core/router/scaffold_with_nav_bar_test.dart`
- `flutter test test/features/projects/presentation/screens/project_save_navigation_test.dart`
- `flutter test test/features/sync/presentation/screens/sync_dashboard_screen_test.dart`
- `flutter test test/features/settings/presentation/screens/settings_screen_test.dart`
- `flutter test test/features/forms/presentation/screens/form_gallery_screen_test.dart`
- `dart test test/architecture/prefer_named_go_router_navigation_test.dart` (under `fg_lint_packages/field_guide_lints`)
- `dart run custom_lint` (currently 21 issues remaining)

## Immediate Next Focus

The forms export proof matrix is now closed. The next active beta lane is back to architecture drift and sync-safe cleanup while keeping the newly-green forms export contract intact.

- Priority order:
  - align the driver flow/screen registry with the production router shell + forms contract before relying on driver validation for beta
  - continue the remaining repository-drift cleanup exposed by `no_repository_import_in_presentation_logic`, starting with auth / gallery / photos / projects
  - resume the sync-specific lint and proof backlog around `sync_run_state_store.dart`
- Keep validating:
  - `flutter analyze`
  - pay-app presentation/provider proof stays green after the shared form export changes
  - forms export matrix stays green for IDR / 0582B / 1126
  - no new provider-direct repository drift or local filesystem coupling is introduced
  - named-route navigation stays the only production pattern for go_router callers
  - `dart run custom_lint` backlog continues trending down from 58 -> 50 -> 48 -> 44 -> 42 -> 35 -> 21

## Current Custom Lint Blockers

- Remaining repository-drift hotspots:
  - auth `auth_provider`
  - gallery `gallery_provider`
  - photos `photo_provider`
  - projects `project_provider`
- Remaining non-layering errors:
  - `sync_run_state_store.dart` raw SQL / delete / try-finally issues
  - `sync_run_state_store_test.dart` missing soft-delete filter proof
  - `driver_diagnostics_handler.dart` / `realtime_hint_handler.dart` missing post-RPC refresh warning follow-up
- Remaining routing validation gaps:
  - `lib/core/driver/flows/navigation_flow_definitions.dart` still models dashboard/calendar/projects/settings as standalone routes instead of the production `ShellRoute` + `ScaffoldWithNavBar`
  - `lib/core/driver/screen_registry.dart` and `lib/core/driver/flows/forms_flow_definitions.dart` still expose legacy `FormsListScreen` / `FormFillScreen` routes instead of the production `FormGalleryScreen` + `/form/:responseId` contract

## Files Most Recently Touched

- `.codex/plans/2026-04-07-beta-release-unified-todo.md`
- `lib/features/pay_applications/di/pay_app_providers.dart`
- `lib/features/pay_applications/domain/domain.dart`
- `lib/features/pay_applications/domain/models/*`
- `lib/features/pay_applications/domain/usecases/*`
- `lib/features/pay_applications/presentation/providers/pay_application_provider.dart`
- `lib/features/pay_applications/presentation/providers/export_artifact_provider.dart`
- `lib/features/pay_applications/presentation/providers/contractor_comparison_provider.dart`
- `lib/features/pay_applications/presentation/providers/contractor_comparison_provider_commands.dart`
- `lib/features/pay_applications/presentation/providers/contractor_comparison_provider_load_actions.dart`
- `lib/features/pay_applications/presentation/providers/contractor_comparison_provider_owner_data.dart`
- `lib/features/pay_applications/presentation/screens/pay_application_detail_screen.dart`
- `lib/features/pay_applications/presentation/screens/pay_application_detail_file_ops.dart`
- `test/features/pay_applications/domain/usecases/*`
- `test/features/pay_applications/presentation/providers/contractor_comparison_provider_test.dart`
- `test/features/pay_applications/presentation/providers/export_artifact_provider_test.dart`
- `test/features/pay_applications/presentation/providers/pay_application_provider_test.dart`
- `test/features/pay_applications/presentation/screens/pay_application_detail_screen_test.dart`
- `test/features/pay_applications/presentation/widgets/export_artifact_history_list_test.dart`
- `test/features/quantities/presentation/screens/quantities_screen_export_flow_test.dart`
- `test/features/quantities/presentation/screens/quantities_screen_pay_app_export_flow_test.dart`
- `lib/core/router/app_router.dart`
- `lib/core/router/shell_banners.dart`
- `lib/features/auth/presentation/screens/{account_status_screen,company_setup_screen,forgot_password_screen,login_screen,otp_verification_screen,pending_approval_screen,profile_setup_screen,register_screen,update_password_screen}.dart`
- `lib/features/entries/presentation/screens/{drafts_list_screen,entry_review_screen,review_summary_screen}.dart`
- `lib/features/forms/presentation/screens/form_new_dispatcher_screen.dart`
- `lib/features/settings/presentation/screens/{consent_screen,settings_screen}.dart`
- `lib/features/settings/presentation/widgets/{settings_account_section,settings_sync_data_section}.dart`
- `lib/features/sync/presentation/widgets/{deletion_notification_banner,sync_dashboard_actions_section,sync_status_icon}.dart`
- `lib/features/projects/presentation/widgets/project_contractors_tab_body.dart`
- `fg_lint_packages/field_guide_lints/lib/architecture/rules/prefer_named_go_router_navigation.dart`
- `fg_lint_packages/field_guide_lints/test/architecture/prefer_named_go_router_navigation_test.dart`

## Current Resume Order

1. Replace `test/features/projects/presentation/screens/project_save_navigation_test.dart` with a real route/service-backed proof.
2. Align the driver flow/screen registry with the production shell/forms routing contract and remove the legacy form screen surfaces from driver validation.
3. Continue the next provider/controller/repository drift cleanup wave in auth / gallery / photos / projects.
4. Resume the sync-specific lint/proof backlog around `sync_run_state_store.dart` and adjacent executor/state-store contracts.
