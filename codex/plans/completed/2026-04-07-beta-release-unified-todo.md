Date: 2026-04-07
Branch: `sync-engine-refactor`
Status key: `[ ]` pending, `[-]` in progress, `[x]` done, `[!]` blocked

# Beta Release Unified TODO

This is the single execution queue for the current release push.

Canonical tracker reference:
- [2026-04-08-beta-central-tracker.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-08-beta-central-tracker.md)
- [2026-04-08-beta-research-inventory.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-08-beta-research-inventory.md)

It consolidates:
- sync release-proof work
- pay-app/export work
- MDOT 1126 / forms compliance work
- Notion audit findings from `2026-04-07`
- code-backed audit findings from this session
- app-wide architecture / decomposition / lint standardization

## Finish Criteria

The beta gate is not met until all of the following are true:

- `flutter analyze` is clean.
- targeted export / pay-app / forms / sync tests are clean.
- all remaining god files, large classes, providers, controllers, helpers, and large methods are decomposed into logical endpoints with enforceable lint coverage.
- the layering model is standardized app-wide around explicit endpoints and domain/use-case boundaries rather than provider-direct repository drift.
- dead code, stale exports, abandoned helpers, and superseded scaffolding are removed or explicitly justified.
- forms export is proven correct for the shipped forms and the exported output matches the UI-entered data in the expected PDF/Excel locations.
- pay-app export is fully finished per spec, not merely partially wired.
- sync remains release-green while the cleanup lands.
- UI-system gaps called out in the audit are either closed or explicitly descoped before beta.

## Operating Rules

- No new product features unless required to finish an already-shipped feature per spec.
- No god files and no god methods.
- Treat file size and member size as architecture problems, not style issues.
- Prefer decomposition into named endpoint files with clear ownership over adding more helpers into oversized files.
- Any architecture cleanup that changes behavior must be followed by targeted verification.
- No lint suppressions, analyzer excludes, or “temporary” bypasses.

## Immediate Red-State Recovery

[x] Fix current `flutter analyze` failures and keep it green after each wave
Current confirmed failures:
- dead export in `lib/features/entries/data/datasources/remote/remote_datasources.dart`
- stale sync test overrides missing `requireDirtyScopes`

[x] Fix the broken pay-app export widget flow test
Current confirmed break: `test/features/quantities/presentation/screens/quantities_screen_pay_app_export_flow_test.dart` mocks `ProjectProvider`, but `selectedProject` is now an extension-backed getter over private provider state.

[x] Re-run export-focused tests and capture current proof baseline
Current proof:
- `test/features/pay_applications/domain/usecases/export_pay_app_use_case_test.dart`
- `test/features/pay_applications/data/services/pay_app_excel_exporter_test.dart`
- `test/features/forms/domain/usecases/export_form_use_case_test.dart`
- `test/features/entries/domain/usecases/export_entry_use_case_test.dart`

[x] Resolve the local Flutter test crash caused by stale generated native-assets manifest
Note: removing `build/unit_test_assets/NativeAssetsManifest.json` unblocked the focused `flutter test` runs.

## Architecture Standardization

[ ] Define the app-wide layering target as the required default
Target shape:
- presentation -> controller/provider endpoint
- controller/provider -> domain use case
- use case -> repository interface
- repository impl -> datasource/service

[ ] Audit and eliminate provider -> repository direct drift across the app
Notion audit finding: layering consistency is `6/10`; use-case-driven in 6 features vs provider->repository direct in 14 features.
Current remaining drift hotspots from this pass:
- closed in this wave:
  - `lib/features/pay_applications/presentation/providers/contractor_comparison_provider.dart`
  - `lib/features/calculator/presentation/providers/calculator_provider.dart`
  - `lib/features/todos/presentation/providers/todo_provider.dart`
  - `lib/features/settings/presentation/providers/support_provider.dart`
  - `lib/features/settings/presentation/providers/{admin_provider,consent_provider}.dart`
  - `lib/features/contractors/presentation/providers/{contractor_provider,equipment_provider,personnel_type_provider}.dart`
  - `lib/features/locations/presentation/providers/location_provider.dart`
  - `lib/features/projects/presentation/providers/project_assignment_provider.dart`
  - `lib/features/quantities/presentation/providers/{bid_item_batch_import,bid_item_provider,entry_quantity_provider}.dart`
  - `lib/features/entries/presentation/providers/daily_entry_provider.dart`
  - `lib/features/entries/presentation/controllers/{contractor_editing_controller,contractor_editing_loader,contractor_editing_save,pdf_data_builder}.dart`
- still open:
  - `lib/features/auth/presentation/providers/auth_provider.dart`
  - `lib/features/gallery/presentation/providers/gallery_provider.dart`
  - `lib/features/photos/presentation/providers/photo_provider.dart`
  - `lib/features/projects/presentation/providers/project_provider.dart`

[ ] Add or tighten lint rules that enforce:
- no provider/controller direct repository access outside approved legacy exceptions
- no oversized file/class/method/provider/controller/helper endpoints
- no mixed feature ownership in a single endpoint file
- no business logic in DI wiring
- no hidden cross-feature export/sync bypasses
- no driver-layer generic mutation of protected sync tables
Progress in this wave:
- `prefer_named_go_router_navigation` now exposes raw `context.go/push/replace` string paths in production navigation code
- app navigation callers were standardized onto named routes before enabling the rule, so new drift is exposed without preserving legacy route-string duplication

[ ] Decide and codify hard size limits for beta
User intent:
- files under 300 LOC
- large methods under the same decomposition mindset
- classes/providers/controllers/helpers split into logical endpoints before beta

[ ] Create one architecture audit pass for every remaining large surface
Priority targets already confirmed:
- `lib/core/database/database_service.dart`
- `lib/core/driver/driver_server.dart`
- `lib/features/forms/data/services/form_pdf_service.dart`
- `lib/features/pdf/services/extraction/extraction_pipeline.dart`
- `lib/features/pdf/services/pdf_service.dart`
- `lib/features/sync/engine/integrity_checker.dart`
- `lib/features/sync/engine/local_sync_store.dart`
- `lib/features/projects/data/services/project_lifecycle_service.dart`

## Dead Code Cleanup

[ ] Run a repo-wide dead-code audit and keep folding findings into this unified queue

[ ] Remove confirmed dead exports, dead files, stale barrels, abandoned helpers, and superseded scaffolding from the recent refactor waves

[ ] Audit high-noise recent additions for abandonment after the sync/pay-app/forms push
Targets from current branch state:
- unused compatibility shims
- stale generated artifacts / manifests / caches
- abandoned intermediate driver/test harness endpoints
- dead migration/debug helpers left behind during sync-hint churn

[ ] Add guardrails where dead code keeps recurring
Examples:
- stale barrel exports pointing at deleted implementations
- leftover compatibility files no longer imported anywhere
- dead driver/test harness endpoints after architecture moves
- orphaned pay-app/forms/sync helper files after decomposition

## Forms Export Correctness

[x] Close the standalone form-export validation gap
Current confirmed audit finding:
- entry bundle export validates attached forms at export time before writing artifacts
- standalone `ExportFormUseCase` appears to skip the same export-time validator gate
- this creates a likely stale-signature / incomplete-form bypass for single-form export

[x] Audit 0582B export end-to-end against UI-entered data -> PDF field mapping
Verification target:
- verify debug PDF path exists
- verify exported PDF field placement is correct
- verify no historical IDR-style mapping regressions remain in shared PDF code

Current verified slice:
- added direct unit coverage for `fillMdot0582bPdfFields`
- added direct unit coverage for `validateMdot0582B`
- reran `test/features/forms/services/form_pdf_service_test.dart`
- debug PDF generation is verified for the shipped 0582B template
- exported PDF now proves live header fields, standards rows, latest proctor weights, and remarks placement against the shipped template via `test/features/forms/services/form_export_mapping_matrix_test.dart`

[x] Audit IDR export end-to-end against UI-entered data -> PDF field mapping
User note:
- IDR has had export problems in the past
- there should be a debug PDF path for this flow

Current verified slice:
- `test/services/pdf_field_mapping_test.dart` now passes against the live template and current `PdfService` field map
- `tools/verify_idr_mapping.py` was updated to the current equipment field names used by `PdfService`
- exported PDF now proves live UI-entered header / contractor / personnel / equipment / narrative placement against the shipped template via `test/features/forms/services/form_export_mapping_matrix_test.dart`

[x] Audit MDOT 1126 export end-to-end against UI-entered data -> PDF field mapping
Priority checks:
- signature-required export gate
- carry-forward correctness
- attachment behavior
- final filled PDF mapping fidelity

Current verified slice:
- added direct unit coverage for `fillMdot1126PdfFields`
- added direct unit coverage for `validateMdot1126`
- debug PDF generation is verified for the shipped 1126 template
- export now merges wizard header edits from `responseData['header']` with legacy `headerData`
- exported PDF now proves live report header, rainfall summary, weekly reporting period, row mapping, and shipped signature field presence (`Button1`) via `test/features/forms/services/form_export_mapping_matrix_test.dart`

[x] Build a per-form export proof matrix
Minimum shipped forms:
- IDR
- MDOT 0582B
- MDOT 1126

[ ] Add missing forms domain tests
Notion finding: only `2/15` form use cases were covered at audit time; current tree still shows only 3 test files under `test/features/forms/domain/usecases/`.
Priority missing coverage:
- weekly SESC reminder logic where it affects shipped flow correctness
- export-time validation behavior

[x] Add the missing 1126/signature-chain domain tests
Completed coverage:
- `sign_form_response_use_case`
- `invalidate_form_signature_on_edit_use_case`
- `build_carry_forward_1126_use_case`
- `load_prior_1126_use_case`

## Pay Application Completion

[ ] Re-verify the full pay-app export flow from real UI entry point
Current implementation exists:
- Quantities screen export trigger
- Excel generation
- artifact persistence
- save/share/detail routing
Remaining bar:
- prove it is reachable, spec-complete, and polished
Current verified slice:
- `test/features/quantities/presentation/screens/quantities_screen_pay_app_export_flow_test.dart`
- `test/features/quantities/presentation/screens/quantities_screen_export_flow_test.dart`
- verified real UI path for export, replacement, duplicate-block, save-copy, and detail navigation

[ ] Verify pay-app Excel output against UI-entered/source data
User intent:
- finish the full feature per spec
- exported data must land in the correct places
Current verified slice:
- `test/features/pay_applications/data/services/pay_app_excel_exporter_test.dart`
- `test/features/pay_applications/domain/usecases/export_pay_app_use_case_excel_proof_test.dart`
- verified saved workbook cells against source bid items, prior pay-app linkage, period quantities, cumulative quantities, and totals

[x] Decompose pay-app presentation/application logic out of the heavy provider
Audit finding:
- pay-applications currently has one use case backing a `227`-LOC provider
- logic should move toward explicit controller/use-case endpoints before beta
Completed:
- provider no longer talks to `PayApplicationRepository` directly
- added `LoadPayApplicationsUseCase`
- added `ValidatePayAppRangeUseCase`
- added `SuggestNextPayAppNumberUseCase`
- added `PreparePayAppExportUseCase`
- added direct domain coverage for range validation and export preparation
- fixed and covered the exact-match replacement preflight path

[ ] Verify same-range replacement preserves identity, file linkage, and history behavior
Current verified slice:
- `test/features/pay_applications/domain/usecases/export_pay_app_use_case_test.dart`
- `test/features/pay_applications/domain/usecases/prepare_pay_app_export_use_case_test.dart`

[ ] Verify overlap-block path creates no hidden rows/files
Current verified slice:
- provider + screen coverage now exercises the duplicate/blocked preflight path

[ ] Verify pay-app detail save/share/download flows after export
Current verified slice:
- `test/features/pay_applications/presentation/screens/pay_application_detail_screen_test.dart`
- verified detail-screen load, save-copy, and share actions against the new detail/artifact use-case layer

[ ] Verify contractor comparison flow and discrepancy export against the saved pay-app artifact path
Current verified slice:
- duplicate contractor match normalization now proves only one imported row can own a pay item and the duplicate is reset to review
- remote-only saved pay-app artifacts now prove the comparison flow localizes/downloads the synced workbook before parsing
- discrepancy PDF export now writes through an injected comparison-report file-save seam instead of calling `getApplicationDocumentsDirectory()` directly from the provider
- discrepancy PDF provider proof now covers both successful PDF write + metadata persistence and cleanup when artifact creation fails

[ ] Verify sync round-trip for pay-app/export artifacts remains green after cleanup

## Routing Verification And Standardization

[x] Standardize production go_router callers onto named routes instead of hardcoded path strings
Completed:
- auth flow redirects/buttons now use named routes
- settings / sync / review / form-new / personnel-type navigation now uses named routes with explicit path/query params
- router restoration now persists/restores only restorable routes through `PreferencesService.lastRoute`
- `prefer_named_go_router_navigation` now enforces the named-route standard in custom lint

[x] Rebuild settings-screen navigation coverage around the real named routes
Completed:
- `test/features/settings/presentation/screens/settings_screen_test.dart` now uses the real sync-aware provider seam instead of stale private-field mocks
- settings navigation is now proven to `editProfile`, `admin-dashboard`, `sync-dashboard`, and `trash`

[x] Rebuild shell navigation coverage around the current sync/project provider seams
Verified green:
- `test/core/router/scaffold_with_nav_bar_test.dart`

[ ] Align driver/harness forms routing with the production router
Confirmed drift:
- `lib/core/driver/screen_registry.dart` still exposes `FormsListScreen` and `FormFillScreen`
- `lib/core/driver/flows/forms_flow_definitions.dart` still routes `/forms` to `FormsListScreen`
Why this matters:
- production uses `FormGalleryScreen` + `/form/:responseId`
- driver/harness validation can still pass against legacy form surfaces that beta no longer ships as the primary route contract

[x] Replace the placeholder project-save navigation proof with a real route/service-backed test
Verified green:
- `test/features/projects/presentation/screens/project_save_navigation_test.dart`

[ ] Align driver/harness navigation flows with the production shell/forms contract
Confirmed drift:
- `lib/core/driver/flows/navigation_flow_definitions.dart` still bypasses the production `ShellRoute` for dashboard/calendar/projects/settings
- `lib/core/driver/screen_registry.dart` still exposes `FormsListScreen` and `FormFillScreen`
- `lib/core/driver/flows/forms_flow_definitions.dart` still routes `/forms` to `FormsListScreen`
Why this matters:
- production uses `ScaffoldWithNavBar` for the main tabs
- production uses `FormGalleryScreen` + `/form/:responseId`
- driver validation can still pass against legacy navigation surfaces beta no longer treats as canonical

## Sync Closeout And Regression Safety

[ ] Keep the sync release-proof matrix green while cleanup lands

[ ] Re-run the critical sync verification slices after architecture changes touch:
- export artifacts
- form exports
- delete graph
- local sync store
- integrity checker
- driver endpoints

[ ] Continue burning down sync owner / endpoint drift if discovered during decomposition

[ ] Fold any proven sync regressions back into this unified TODO rather than reopening fragmented queues

[ ] Commit and enforce the missing driver mutation lint rule if it is not already on branch
Audit finding:
- `no_driver_generic_mutation_of_protected_sync_tables` was called out as a pre-merge blocker in the audit roadmap

## UI System, Responsive, A11y, i18n

[ ] Review the Notion UI-system findings as active beta work, not optional polish
Current audit findings:
- `AppResponsiveBuilder` used in 1 file
- `Semantics` in 18 places
- `0 i18n`
- responsive/a11y/i18n rated `3.5/10`

[ ] Expand responsive layout adoption beyond the one current `AppResponsiveBuilder` usage

[ ] Audit shell-route and high-traffic screen responsiveness with the design-system layout primitives

[ ] Decide the beta stance on i18n
Current audit finding: no `Intl` / `AppLocalizations` references.
Need explicit outcome:
- ship scaffolding before beta, or
- formally defer and remove it from beta criteria

[ ] Audit accessibility / semantics coverage on high-traffic screens

## Security / Hardening Findings From Audit

[ ] Audit undocumented `codex-admin-sql` edge function

[ ] Gate or remove `debug_emit_sync_hint_self` before beta

[ ] Decide whether sync-hint migration squash and rollback coverage are part of this branch closeout or tracked as pre-merge blockers

## Settings / Data Export / Sensitive Flows

[ ] Standardize settings layering
Notion finding:
- 5 concrete settings repos without domain interfaces
- admin / consent / support are sensitive paths
Progress:
- support submission now goes through `SubmitSupportTicketUseCase`
- added domain interfaces for support ticket persistence and support log upload
- admin and consent now also go through domain use cases
- remaining settings closeout is proof/cleanup, not direct provider->repository drift

[ ] Standardize auth layering
Audit finding:
- auth currently has zero domain repository interfaces despite being a primary security boundary

[ ] Audit `WizardActivityTracker` coverage on long-edit flows
Audit finding:
- entries / photos / todos were still flagged as missing tracker coverage in the Notion audit

[ ] Add migration hardening guardrails
Audit findings:
- ~50 recent Supabase migrations have no rollback coverage
- new migrations should require paired rollback coverage in CI

[ ] Decide scope for Settings data export UI versus current release-only export work
Notion finding: data export UI is still missing.
User intent: finish current features only; do not create speculative new scope unless it is already part of the promised shipped feature set.

## Execution Order For Tonight

 [x] Phase 1: capture and consolidate audit + intent into this unified queue
[x] Phase 2: restore green baseline (`flutter analyze`, broken tests, standalone form-export gate)
[x] Phase 3: forms export correctness audit and fixes (IDR, 0582B, 1126)
[-] Phase 4: pay-app spec completion and proof
[ ] Phase 5: architecture/lint standardization wave for remaining large surfaces
[ ] Phase 6: responsive/a11y/i18n decision and UI-system follow-up
[ ] Phase 7: final verification sweep and updated release status

## Confirmed Findings From This Session

[x] Pay-app Excel export exists in code and is wired from Quantities UI
[x] Focused pay-app/form export tests can run locally after clearing stale generated native-assets manifest
[x] `flutter analyze` is currently red
[x] Pay-app export widget flow test is currently broken
[x] Standalone form export likely bypasses export-time validation now enforced by entry-bundle export
[x] Forms use-case coverage remains materially thinner than the shipped form/export surface
[x] `flutter analyze` is green again after the red-state recovery wave
[x] Sync slices updated for `requireDirtyScopes` and rerun clean:
- `sync_coordinator_test`
- `sync_enrollment_service_test`
- `sync_lifecycle_manager_test`
- `sync_provider_test`
- `sync_dashboard_screen_test`
- `sync_status_icon_test`
- `sync_engine_circuit_breaker_test`
[x] Pay-app export widget flow test rerun clean after replacing extension-fragile provider mocks with repository-backed real providers
[x] Added MDOT 1126 mapping + validator unit coverage
[x] Added MDOT 0582B mapping + validator unit coverage
[x] IDR template verification test now matches the live `PdfService` field map and passes
[x] Debug PDF generation now verifies against all shipped templates:
- IDR debug PDF service test passes
- MDOT 0582B debug PDF service test passes
- MDOT 1126 debug PDF service test passes
[x] Forms UI now exposes debug PDF preview for generic form viewer and MDOT 0582B hub
[x] Shipped-form export matrix now passes against live templates and UI-entered data:
- IDR export field placement proved end-to-end
- MDOT 0582B export field placement proved end-to-end, including actual standards/weight/remarks fields
- MDOT 1126 export field placement proved end-to-end, including wizard header merge and shipped signature field name
[x] Forms sub-screen routing test harness was rebuilt around pure delegation instead of brittle provider mocking
[x] Pay-app provider no longer hits the repository directly for list/range/export preparation flows
[x] Added pay-app domain endpoints for list loading, next-number suggestion, range validation, export preparation, detail loading, artifact localization, artifact create/delete
[x] Pay-app Excel proof now verifies real saved workbook cell output against source quantities, prior-pay-app linkage, and totals
[x] Pay-app detail proof now covers detail load, save-copy, share, export history load/delete, and Quantities-screen replacement/duplicate-block flows
[x] `flutter analyze` is green after the contractor-comparison owner-data nullability fix
[x] Contractor-comparison discrepancy export is decoupled from direct `path_provider` lookup
[x] `test/features/pay_applications/presentation/providers/contractor_comparison_provider_test.dart` is green with success + cleanup coverage
[x] `flutter test test/features/pay_applications/presentation/providers` is green after the discrepancy export seam extraction
