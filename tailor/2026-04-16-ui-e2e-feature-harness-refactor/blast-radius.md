# Blast Radius

## Test harness — `.claude/`

**Delete after cutover:**
- `.claude/test-flows/tiers/setup-and-auth.md`
- `.claude/test-flows/tiers/entry-crud.md`
- `.claude/test-flows/tiers/toolbox-and-pdf.md`
- `.claude/test-flows/tiers/pay-app-and-exports.md`
- `.claude/test-flows/tiers/settings-and-admin.md`
- `.claude/test-flows/tiers/mutations.md`
- `.claude/test-flows/tiers/verification.md`
- `.claude/test-flows/tiers/manual-flows.md` (UX-relevant IDs absorbed; sync-only IDs move to a residual `manual-flows.md` at the root or stay as-is — writer decides)

**Rewrite:**
- `.claude/test-flows/flow-dependencies.md` → feature taxonomy index.
- `.claude/skills/test/SKILL.md` — the `Required References` list names every `tiers/*` file. Replace with `features/*` references.

**Create (16 files per spec § Feature Taxonomy):**
- `.claude/test-flows/features/auth.md`
- `.claude/test-flows/features/dashboard.md`
- `.claude/test-flows/features/projects.md`
- `.claude/test-flows/features/entries.md`
- `.claude/test-flows/features/forms.md`
- `.claude/test-flows/features/pay_applications.md`
- `.claude/test-flows/features/quantities.md`
- `.claude/test-flows/features/analytics.md`
- `.claude/test-flows/features/pdf.md`
- `.claude/test-flows/features/gallery.md`
- `.claude/test-flows/features/toolbox.md`
- `.claude/test-flows/features/calculator.md`
- `.claude/test-flows/features/todos.md`
- `.claude/test-flows/features/settings.md`
- `.claude/test-flows/features/sync_ui.md`
- `.claude/test-flows/features/contractors.md`

**Untouched (out of scope):**
- `.claude/test-flows/sync/*.md` (S01-S21 dual-device harness).

## Driver surface — `lib/core/driver/`

**New:**
- `/driver/seed` endpoint shell. Likely additions: `DriverSeedRoutes` class + `DriverSeedHandler` + wiring in `DriverServer._handleRequest`. Implementation delegates to `HarnessSeedData.seedBaseData` / `seedScreenData` / `seedPayAppData`. Decision point flagged in `ground-truth.md`.

**Modify:**
- `lib/core/driver/screen_registry.dart` — additions as new screens get explicit harness entry points.
- `lib/core/driver/screen_contract_registry.dart` — expansion to cover every sync-visible screen per rubric item 11.
- `lib/core/driver/flows/forms_flow_definitions.dart` / `navigation_flow_definitions.dart` / `verification_flow_definitions.dart` — fold old chain flows into feature-scoped definitions or retire individual entries.
- `lib/core/driver/driver_server.dart` — wire seed handler.
- `lib/core/driver/harness_seed_data.dart` — extend `seedScreenData` switch with new precondition names from feature specs.

**Cleanup targets (likely retirements once features cut over):**
- `flowRegistry` entries whose only consumer was an old-tier chain flow.

## Sentinel keys — `lib/shared/testing_keys/`

Additions per rubric item 3 ("screen exposes one unique sentinel for `/driver/find`"). Ownership:
- `auth_keys.dart` — add sentinels for any login/consent screens still missing one.
- `entries_keys.dart` — confirm `entriesListScreen`, `reviewScreen`, `reviewSummaryScreen`, `draftListScreen` sentinels exist; add what is missing.
- `projects_keys.dart` — `projectListScreen`, `projectSetupScreen`, `projectDashboardScreen` sentinels.
- `settings_keys.dart` — every settings sub-screen sentinel (`settingsScreen`, `editProfileScreen`, `trashScreen`, `adminDashboardScreen`, `personnelTypesScreen`, `appLockSettingsScreen`, `consentScreen`, `savedExportsScreen`, `legalDocumentScreen`, `ossLicensesScreen`, `helpSupportScreen`).
- `toolbox_keys.dart` — sentinels for `toolboxHomeScreen`, `calculatorScreen`, `galleryScreen`, `todosScreen`.
- `pay_app_keys.dart` — sentinels for `payAppDetailScreen`, `contractorComparisonScreen`.
- `sync_keys.dart` — already has `syncDashboardScreen` and `conflictViewerScreen`.
- `contractors_keys.dart` — `contractorSelectionScreen` sentinel.
- `documents_keys.dart` / `support_keys.dart` / `consent_keys.dart` / `photos_keys.dart` / `locations_keys.dart` / `quantities_keys.dart` / `common_keys.dart` — extend as per-feature specs declare new interactive widgets.

All new keys must be re-exported by `lib/shared/testing_keys/testing_keys.dart` (facade).

## Presentation sweep (blanket — 57 `_screen.dart` files)

**300-line audit failures (45 files) — decomposition required:**

| Lines | File |
|---:|---|
| 680 | `lib/features/calculator/presentation/widgets/hma_calculator_tab.dart` |
| 677 | `lib/features/forms/presentation/screens/mdot_1174r_form_screen.dart` |
| 669 | `lib/features/quantities/presentation/widgets/quantities_pay_app_export_flow.dart` |
| 577 | `lib/features/forms/presentation/screens/mdot_1174r_sections.dart` |
| 565 | `lib/features/entries/presentation/screens/entry_review_screen.dart` |
| 560 | `lib/features/settings/presentation/screens/app_lock_settings_screen.dart` |
| 545 | `lib/features/forms/presentation/screens/mdot_1126_form_screen.dart` |
| 525 | `lib/features/forms/presentation/screens/form_gallery_screen.dart` |
| 512 | `lib/features/forms/presentation/screens/mdot_1126_steps.dart` |
| 490 | `lib/features/calculator/presentation/widgets/concrete_calculator_tab.dart` |
| 478 | `lib/features/sync/presentation/screens/conflict_viewer_screen.dart` |
| 469 | `lib/features/settings/presentation/screens/consent_screen.dart` |
| 467 | `lib/features/analytics/presentation/screens/project_analytics_screen.dart` |
| 440 | `lib/features/settings/presentation/screens/edit_profile_screen.dart` |
| 436 | `lib/features/settings/presentation/screens/admin_dashboard_screen.dart` |
| 428 | `lib/features/pay_applications/presentation/dialogs/pay_app_date_range_dialog.dart` |
| 427 | `lib/features/forms/presentation/widgets/hub_quick_test_content.dart` |
| 387 | `lib/features/forms/presentation/widgets/form_workflow_shell.dart` |
| 384 | `lib/features/projects/presentation/widgets/project_contractors_tab_body.dart` |
| 383 | `lib/features/sync/presentation/widgets/sync_dashboard_status_widgets.dart` |
| 380 | `lib/features/entries/presentation/controllers/pdf_data_builder.dart` |
| 377 | `lib/features/entries/presentation/screens/entry_editor_state_mixin.dart` |
| 377 | `lib/features/forms/presentation/support/form_pdf_action_owner.dart` |
| 373 | `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` |
| 372 | `lib/features/entries/presentation/screens/drafts_list_screen.dart` |
| 370 | `lib/features/pay_applications/presentation/screens/pay_application_detail_screen.dart` |
| 363 | `lib/features/settings/presentation/widgets/admin_dashboard_widgets.dart` |
| 357 | `lib/features/forms/presentation/widgets/form_repeated_row_composer.dart` |
| 356 | `lib/features/entries/presentation/screens/review_summary_screen.dart` |
| 355 | `lib/features/settings/presentation/screens/help_support_screen.dart` |
| 354 | `lib/features/sync/presentation/support/conflict_presentation_mapper.dart` |
| 345 | `lib/features/entries/presentation/widgets/entry_contractors_section.dart` |
| 337 | `lib/features/auth/presentation/providers/app_config_provider.dart` |
| 335 | `lib/features/forms/presentation/widgets/form_viewer_sections.dart` |
| 329 | `lib/features/pay_applications/presentation/screens/contractor_comparison_screen.dart` |
| 325 | `lib/features/entries/presentation/screens/entry_editor_screen.dart` |
| 321 | `lib/features/forms/presentation/screens/form_viewer_screen.dart` |
| 320 | `lib/features/sync/presentation/widgets/sync_dashboard_diagnostics_widgets.dart` |
| 315 | `lib/features/todos/presentation/screens/todos_screen.dart` |
| 314 | `lib/features/entries/presentation/widgets/entry_contractors_section_actions.dart` |
| 311 | `lib/features/forms/presentation/widgets/hub_compact_accordion_sections.dart` |
| 311 | `lib/features/calculator/presentation/widgets/concrete_shape_input_cards.dart` |
| 307 | `lib/features/entries/presentation/controllers/entry_editing_controller.dart` |
| 304 | `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart` |
| 301 | `lib/features/analytics/presentation/providers/project_analytics_provider.dart` |

**Colors.* offenders (107 files, 166 occurrences)** — full list too long to inline; `grep "Colors\." lib/features/**/presentation/**/*.dart` reproduces it. Highest-density files in presentation:
- `lib/features/entries/presentation/utils/weather_helpers.dart` (8)
- `lib/features/entries/presentation/screens/review_summary_screen.dart` (11)
- `lib/features/pdf/presentation/widgets/mp_import_preview_sections.dart` (5)
- `lib/features/sync/presentation/screens/conflict_viewer_screen.dart` (4)
- `lib/features/settings/presentation/widgets/admin_dashboard_widgets.dart` (4)
- `lib/features/entries/presentation/widgets/home_calendar_section.dart` (4)
- Conflict/sync diagnostics widgets (multiple 3-3 hits).

Replace with `Theme.of(context).colorScheme.*` or `FieldGuideColors.of(context)` per `rules/frontend/flutter-ui.md`.

**Hardcoded `Key('…')` offenders (5 files, 10 occurrences):**
- `lib/features/sync/presentation/widgets/sync_dashboard_diagnostics_widgets.dart`
- `lib/features/sync/presentation/support/conflict_presentation_mapper.dart` (6)
- `lib/features/forms/presentation/widgets/rainfall_events_editor.dart`
- `lib/features/gallery/presentation/widgets/gallery_filter_sheet.dart`
- `lib/features/entries/presentation/controllers/entry_activities_controller.dart`

Replace with typed `TestingKeys.*` and own the sentinel in the correct per-feature `*_keys.dart`.

## Presentation — Screen contract gaps

Screens in `screenRegistry` but **missing from `screenContracts`**. Writer must decide which need contracts under rubric item 11:

- `LoginScreen`, `RegisterScreen`, `ForgotPasswordScreen`
- `HomeScreen`, `ProjectDashboardScreen`
- `SettingsScreen`
- `EntryEditorScreen` / `EntryEditorCreateScreen` / `EntryEditorReportScreen`
- `ProjectSetupScreen` / `ProjectSetupNewScreen` / `ProjectSetupEditScreen`
- `QuantityCalculatorScreen`
- `ToolboxHomeScreen`
- `QuickTestEntryScreen`, `ProctorEntryScreen`, `WeightsEntryScreen`
- `CalculatorScreen`, `GalleryScreen`, `TodosScreen`, `EditProfileScreen`, `AdminDashboardScreen`

## PDF AcroForm helper

**New:**
- `lib/shared/testing/pdf_acroform_inspector.dart` (location TBD; writer picks — suggested placement `lib/shared/testing/` or `test/support/`).
- Test support utility for golden byte-compare fallback of flattened forms.

**Touch:**
- No production code change required — the helper is test-scope and consumes `syncfusion_flutter_pdf` exactly as `FormPdfFieldWriter` already does.

## Plan / PR shape

Single PR on `gocr-integration` (per spec § Blast Radius Budget → Rollback). Commits may land per-feature cutover, but delivery is one merge. `flutter analyze`, `dart run custom_lint`, `scripts/audit_ui_file_sizes.ps1`, `scripts/validate_sync_adapter_registry.py` must stay green at every commit.
