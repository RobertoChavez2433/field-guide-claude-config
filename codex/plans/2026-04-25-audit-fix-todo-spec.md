# Audit Fix To-Do Spec

## Summary

Create a repo-tracked checklist and iterate through the audit in narrow,
verified slices. The active lane fixes existing bugs, audit blockers, alert
noise, and stale architecture issues without changing app workflows. New-feature
work is parked.

Primary order: close low-blast-radius hygiene first, then pay-app data
integrity, sync repair visibility, PDF heuristic removal with replay proof,
migration test coverage, then architecture/debt items.

## 0. Tracker Setup + No-Code Closures

- [x] Create the Codex checklist file with sections matching this spec.
- [x] Mark closure-only items as no-code: GH #311, #308, #295, #287, #281, #280, #279, #278, Audit H4.
- [x] Record parked/new-feature items separately: #89 SQLCipher, #178 immutable-model lints, #127 zip/merged bundle decision, #129 signed URL decision, #91/#92 OCR migration limits.
- [x] Keep AGENTS/Codex guardrails visible while completing the tracker: use `.codex/` as the alias entrypoint, avoid `MOCK_AUTH`, test real behavior, and treat UI E2E as a bug-discovery gate.

### No-Code Closures

- GH #311: Closure-only; no app code change in this lane.
- GH #308: Closure-only; no app code change in this lane.
- GH #295: Closure-only; no app code change in this lane.
- GH #287: Closure-only; no app code change in this lane.
- GH #281: Closure-only; no app code change in this lane.
- GH #280: Closure-only; no app code change in this lane.
- GH #279: Closure-only; no app code change in this lane.
- GH #278: Closure-only; no app code change in this lane.
- Audit H4: Closure-only; no app code change in this lane.

### Parked / New-Feature Items

- GH #89 SQLCipher/database encryption: parked as feature work.
- GH #178 immutable-model lints: parked as feature/tooling expansion.
- GH #127 zip/merged bundle decision: parked pending product decision.
- GH #129 signed URL decision: parked pending product/security decision.
- GH #91/#92 OCR migration limits: parked as OCR migration/feature scope.

## 1. Tiny Safe Fixes First

- [x] H1: update stale `go_router` docs to AutoRoute/AppNavigator guidance.
- [x] H3: export `sync_run_metrics.dart` from sync domain barrel.
- [x] H10: fix pay-app import regex typo only.
- [x] H14: replace raw `FilledButton` with `AppButton.primary`.
- [x] H19: pass captured stack traces into auth/sync listener logging.
- [x] B7 partial: add missing `printing` override WHY comment.
- [x] #292: fix fixed-length list mutation at the narrow consumer/provider seam.
- [x] #293: stop throwing uncaught `StateError` for active-sync skip; preserve warning behavior.
- [x] #294/#306: downgrade retryable network logs and remove/hash UUIDs in RLS-denial messages.
- [x] #300/#301/#302/#285: suppress expected validation/transient errors from Sentry without hiding user-facing feedback.

### Verification

- `flutter test test/core/config/sentry_pii_filter_test.dart`
- `flutter test test/features/quantities/data/repositories/bid_item_repository_impl_test.dart`
- `flutter test test/core/di/app_initializer_test.dart`
- `flutter analyze`
- `dart run custom_lint`

## 2. Pay-App Integrity Slice

- [x] B1: collapse duplicate cleanup, remove misleading retained-source log, and rollback created artifact rows if replace-path pay-app update fails.
- [x] #288: implement near-term defensive null-out before pay-app update when `export_artifact_id` points to a missing local artifact.
- [x] #289: preserve or log the original database cause before returning generic repository failure.
- [x] B5 companion: move pay-app export directory resolution/file deletion into `ExportArtifactFileService` or a sibling data-side service; remove `path_provider` from the pay-app domain use case.
- [x] Add behavior tests for rollback, dangling artifact FK null-out, and update-failure cause visibility.

### Verification

- `flutter test test/features/pay_applications/domain/usecases/persist_pay_app_export_use_case_test.dart`
- `flutter test test/features/pay_applications/domain/usecases/export_pay_app_use_case_test.dart`
- `flutter test test/features/pay_applications/domain/usecases/export_pay_app_use_case_excel_proof_test.dart`
- `flutter test test/features/pay_applications/domain/usecases/delete_export_artifact_use_case_test.dart`
- `flutter analyze`
- `dart run custom_lint`

## 3. Sync Repair + Harness Reliability

- [x] B2: show the dashboard repair tile when either `blockedCount > 0` or `failedRepairCount > 0`; keep existing repair action.
- [x] H6: document repair-job retention/tombstone policy; do not remove jobs yet.
- [x] #303: make UI E2E preflight fail clearly unless sync queue is drained and not syncing.
- [x] #307/#305: make CI service-role and seeded-auth preflights unconditional and early.
- [x] Add widget/provider tests for repair-required banner/status/tile and harness preflight unit coverage where available.

### Verification

- `flutter test test/features/sync/presentation/controllers/sync_dashboard_controller_test.dart test/features/sync/presentation/providers/sync_provider_test.dart test/features/sync/presentation/screens/sync_dashboard_screen_test.dart`
- `pwsh -NoProfile -File tools/testing/Test-TestingHarness.ps1`
- `flutter analyze`
- `dart run custom_lint`

## 4. PDF Extraction Safety

- [x] B3: remove only the three description-specific quantity override branches in `ValueNormalizer`.
- [x] Confirm no duplicate override exists in `value_normalizer_steps.dart`.
- [x] Preserve existing generic OCR repair behavior; do not replace with new heuristics in the same slice.
- [ ] Run targeted normalizer tests, then full PDF replay; record regressions as real OCR gaps or stale fixtures.
- [x] H13: add a round-trip serializer test for `OcrCropPageResult` before considering generated serialization.
- [x] #42: add root-isolate assertion only if it can be done without changing production flow.

### Verification

- `flutter test test/features/pdf/extraction/stages/post_processing/artifact_cleaning_unit_rules_test.dart test/features/pdf/extraction/stages/ocr_page_recognition_worker_payload_test.dart`
- `flutter test test/features/pdf/extraction/pipeline/extraction_pipeline_normalized_replay_test.dart test/features/pdf/extraction/integration/gocr_downstream_replay_test.dart`
- `flutter test test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart test/features/pdf/extraction/pipeline/stage_trace_sink_test.dart test/features/pdf/extraction/pipeline/stage_trace_diagnostics_test.dart`
- `flutter analyze`
- `dart run custom_lint`
- Full opt-in replay attempted with `--dart-define=RUN_GOCR_DOWNSTREAM_REPLAY=true`; blocked because `.tmp/gocr_ocr_cache` is absent in this workspace.

## 5. Migration Coverage

- [x] B4: add a shared migration fixture helper for opening pre-version schemas.
- [x] Add dedicated tests for v48, v50, v52, v54, v55, v59, v60, v62, v63.
- [x] Re-run existing v43, v57, v58, v61 migration tests to prove no fixture drift.
- [x] Keep migrations behavior-only; no schema redesign in this slice.

### Verification

- `flutter test test/core/database/late_migration_versions_test.dart test/core/database/migration_v43_test.dart test/core/database/migration_v57_test.dart test/core/database/migration_v58_test.dart test/core/database/migration_v61_test.dart`
- `dart analyze test/_helpers/migration_test_helper.dart test/core/database/late_migration_versions_test.dart test/core/database/migration_v57_test.dart test/core/database/migration_v58_test.dart test/core/database/migration_v61_test.dart`
- `flutter analyze`
- `dart run custom_lint`

## 6. Lifecycle/UI Bug Fixes

- [x] #269: mirror `main_driver.dart` zone pattern in `main.dart`.
- [x] #276: add mounted guards after awaits in `ProjectListScreen._refresh`.
- [x] #284: reset support provider silently during dispose.
- [x] #282: add mounted guards before delayed navigation/pop suspect paths.
- [x] #259: add existing consent revoke action to Settings and route back to consent flow.
- [x] S10 Entries red-screen bug: capture screenshot/log evidence on the S10 tablet for the red screen on the Entry screen / Entries tab before changing code.
- [x] S10 Review Submit E2E flow: add a UI testing flow that reviews the 13-entry batch and attempts submit, capturing screenshot/log/sync evidence for the current submit error.
- [x] Testing harness catalog gap: restore the settings backward traversal flow and saved-export action-probe coverage so the no-device harness contract passes.
- [x] #304: add and run analytics nav-switch regression flow on S21 admin; close after no duplicate `GlobalKey` reproduced.
- [x] #270: reproduce RenderFlex overflow from full Flutter test evidence, fix Gallery photo viewer attribution/layout source, and close.
- [x] #286: reproduce first with fuller runtime evidence before code changes.
- [x] #210: add current entry PDF contractor-field regression proof and close.
- [x] S10 Calendar tab overflow: fix the tablet `RenderFlex` overflow found while reproducing #286, then re-run the primary-tabs flow on the S10 tablet.

### S10 Entries Red-Screen Evidence

- Before: `tools/testing/test-results/2026-04-25/20260425-s10-entries-red-screen-evidence/S10/screenshot-current.png` captured the `Review Drafts` red screen on `SM_X920` / `R52X90378YB`; assertion was Provider `context.select` used outside widget `build`.
- Fix: moved `RolePolicy` / auth selections in `DraftsListScreen` and `EntryReviewScreen` into the actual `build` methods and passed plain values into responsive helper callbacks.
- Companion compile blocker: restored missing generated testing keys through `tools/gen-keys/keys.yaml` and regenerated the typed key catalog.
- After: `tools/testing/test-results/2026-04-25/20260425-s10-entries-red-screen-evidence/S10/screenshot-drafts-after-fix.png` shows the real `Review Drafts` UI; `current-route-drafts-after-fix.json` reports `DraftsListScreen`, `interactionReady=true`, and the post-fix log scan found no Provider/context assertion.
- Verification:
  - `flutter test test/features/entries/presentation/widgets/draft_entry_tile_test.dart test/features/entries/presentation/screens/entry_review_sentinel_test.dart`
  - `dart analyze test/features/entries/presentation/screens/entry_review_sentinel_test.dart lib/features/entries/presentation/screens/drafts_list_screen.dart lib/features/entries/presentation/screens/entry_review_screen.dart lib/features/entries/presentation/screens/entry_review_layout.dart`
  - `dart run tools/gen-keys/generate_keys.dart --check`

### S10 Review Submit E2E Evidence

- Added canonical UI flow `entries-review-submit-ui-flow`. It seeds an exact 13-entry draft review batch through `entry_review_batch`, opens Review Drafts, selects all, reviews all 13 as ready, opens the submit dialog, confirms submit, and requires the dashboard route after submit.
- Deterministic seed behavior is covered by `flutter test test/core/driver/driver_seed_handler_test.dart`.
- S10 run `tools/testing/test-results/2026-04-25/20260425-s10-review-submit-e2e-confirm/summary.json` passed on `SM_X920` / `R52X90378YB` as `office_technician`: 18 UI steps, 4 screenshots, 0 runtime errors, 0 layout defects, 0 failed actions. Final sync evidence showed 13 unprocessed `daily_entries` change-log rows after submit, with 0 blocked rows.

### Testing Harness Catalog Evidence

- Added `settings-backward-traversal-ui-flow` as a settings-owned tap-back proof from Settings into Sync Dashboard and back to Settings.
- Corrected the document gallery action probe from the stale `documents` feature tag to the required `saved_exports` feature tag.
- Verification: `pwsh -NoProfile -File tools/testing/Test-TestingHarness.ps1` passed on 2026-04-25 with 35 self-test files green.

### Reproduce-First Issue Evidence

- GH #304: added `analytics-nav-switch-regression-ui-flow` with legacy alias `analytics-nav-bar-switch-mid-flow`. S21 admin run `tools/testing/test-results/2026-04-25/20260425-s21-admin-analytics-nav-switch-regression-route/summary.json` passed with `/` -> `/analytics/harness-project-001` -> `/settings`, 3 screenshots, 0 failed actions, and 0 runtime errors; issue closed.
- GH #270: full `flutter test` evidence in `.tmp/flutter-test-full.log` reproduced the overflow in `GalleryPhotoViewer`. `UserAttributionText` now falls back to `Unknown` when no `AuthProvider` is scoped, and the gallery photo info panel is bounded/scrollable. Verification: `flutter test test/features/gallery/presentation/screens/gallery_screen_test.dart` and `dart analyze lib/features/auth/presentation/widgets/user_attribution_text.dart lib/features/gallery/presentation/widgets/gallery_photo_viewer.dart`; issue closed.
- GH #210: added `PdfService Multiple Contractors with Equipment generated IDR preserves contractor names in template fields`. The test uses the original observed contractor names, generates the current editable IDR, reads the resulting AcroForm fields back, and verifies `Namegdzf` / `sfdasd` contain the real contractor names. Verification: `flutter test test/services/pdf_service_test.dart`; issue closed.
- GH #286: S10 repro sweep did not reproduce the reported semantics owner assertion after the current fixes. Clean S10 evidence:
  `tools/testing/test-results/2026-04-25/20260425-s10-primary-tabs-after-calendar-overflow-fix/summary.json`,
  `tools/testing/test-results/2026-04-25/20260425-s10-semantics-settings-lifecycle-repro/summary.json`, and
  `tools/testing/test-results/2026-04-25/20260425-s10-semantics-review-submit-repro/summary.json` all passed with 0 runtime errors and 0 failed actions; log scans found no `semantics.dart`, `owner!._nodes.containsKey`, `SemanticsNode`, duplicate `GlobalKey`, `FlutterError`, or `AssertionError` evidence. Issue closed as fixed/currently non-reproducible with reopen criteria for fresh app-frame route evidence.
- S10 Calendar tab overflow: the first #286 primary-tabs repro run at `tools/testing/test-results/2026-04-25/20260425-s10-semantics-primary-tabs-repro/summary.json` failed on `primary-tabs-responsiveness-ui-flow-switch-dashboard-to-calendar` with `A RenderFlex overflowed by 21 pixels on the bottom`. The wide home-screen layout now wraps `_CalendarSectionSelector` in a non-primary `SingleChildScrollView` inside the existing flexible region. Verification: `dart analyze lib/features/entries/presentation/widgets/home_screen_body.dart`; S10 hot reload; `tools/testing/test-results/2026-04-25/20260425-s10-primary-tabs-after-calendar-overflow-fix/summary.json` passed with 0 runtime errors and 0 failed actions.

### Lifecycle/UI Verification

- `flutter test test/features/settings/presentation/screens/settings_screen_test.dart test/features/settings/presentation/screens/help_support_screen_test.dart test/features/settings/presentation/providers/consent_provider_test.dart test/features/projects/presentation/screens/project_list_screen_test.dart test/features/entries/presentation/widgets/draft_entry_tile_test.dart test/features/entries/presentation/screens/entry_review_sentinel_test.dart`
- `flutter test test/features/todos/presentation/screens/todos_screen_test.dart`
- `flutter test test/features/pay_applications/presentation/screens/pay_application_detail_screen_test.dart`
- `flutter test test/services/pdf_service_test.dart`
- `dart analyze lib/features/entries/presentation/widgets/home_screen_body.dart`
- `dart analyze lib/main.dart lib/features/projects/presentation/screens/project_list_screen.dart lib/features/settings/presentation/providers/support_provider.dart lib/features/settings/presentation/screens/help_support_screen.dart lib/features/settings/presentation/widgets/settings_about_section.dart test/features/settings/presentation/screens/settings_screen_test.dart lib/features/entries/presentation/screens/drafts_list_screen.dart lib/features/entries/presentation/screens/entry_review_screen.dart lib/features/entries/presentation/screens/entry_review_layout.dart`
- `dart run custom_lint`

## 7. Architecture Cleanup

- [x] B5 remaining: remove `path_provider` from `export_entry_use_case`; inventory remaining `dart:io` domain imports and handle only when a low-risk production seam exists.
- [x] B6: centralize driver tappability/enabled-state policy in `DriverWidgetInspector`, remove `as dynamic`, then decompose scroll-to-key helpers without changing route responses.
- [x] B7: add `PATCHES.md` to each `*_patched` tree with upstream version, changed files, and rationale.
- [x] Prefer broad architecture lint guardrails for recurring bug classes where practical: Provider usage outside build/responsive callbacks, plugin imports in domain code, route/widget construction drift, generated testing-key drift, and sync/data ownership boundaries. Use narrow one-off lint rules only when the recurring pattern is genuinely narrow.
- [x] Broad provider-thinness guardrail review: keep using existing size/import-direction/provider-read lint pressure rather than adding a narrow one-off auth lint in this slice.
- [ ] Thin-provider architecture follow-up: audit `AuthProvider` and other large providers so providers stay UI-state adapters over use cases/repositories, and prefer broad size/complexity/import-direction lint pressure where it helps keep providers thin.
- [ ] H2/H5/H7/H9/H11/H12/H15/H16/H17/H18: burn down as separate cleanup commits after blocker tests are green.

### Architecture Verification

- `ExportEntryUseCase` no longer imports `path_provider`; app DI injects `getApplicationDocumentsDirectory`.
- Remaining feature-domain `dart:io` imports inventoried for later seams: forms export/signing, entry bundle/entry PDF export, settings support-ticket attachment, and sync application runtime wiring.
- `DomainMustBePureDart` now blocks common Flutter plugin imports such as `path_provider` and `printing` from feature domain code.
- `ProviderListenOnlyInBuild` now blocks production `context.watch` / `context.select` calls outside widget `build` methods; existing violations were moved to build boundaries.
- `MaxFileLength` already classifies `auth_provider.dart`, route guards, `main.dart`, `main_driver.dart`, and `AppWidget` as auth/security seams with 150-line warning and 250-line hard-fail thresholds. Current `auth_provider.dart` is 219 lines, so it is a real refactor candidate under the broad rule without needing a narrow auth-provider-only lint. Other provider thinness pressure comes from the existing import-direction rules (`NoRepositoryImportInPresentationLogic`, data/domain presentation boundaries) plus provider read/write guardrail lints.
- `DriverWidgetInspector.enabledStateFor` owns driver enabled-state policy; `driver_shell_handler.dart` no longer uses `as dynamic`; scroll-to-key response payload construction is split into helper functions.
- `third_party/custom_lint_patched/PATCHES.md`, `third_party/dartcv4_patched/PATCHES.md`, and `third_party/printing_patched/PATCHES.md` document upstream version, changed files, and rationale.
- Verification:
  - `flutter test test/features/entries/domain/usecases/export_entry_use_case_test.dart test/features/entries/presentation/providers/entry_export_provider_test.dart`
  - `dart test fg_lint_packages/field_guide_lints/test/architecture/domain_must_be_pure_dart_test.dart fg_lint_packages/field_guide_lints/test/architecture/provider_listen_only_in_build_test.dart`
  - `flutter test test/core/driver/driver_interaction_readiness_contract_test.dart test/core/driver/driver_widget_inspector_test.dart`
  - `dart analyze lib/features/entries/domain/usecases/export_entry_use_case.dart lib/features/entries/di/entries_providers.dart lib/core/driver/driver_interaction_handler_scroll_to_key_route.dart lib/core/driver/driver_widget_inspector.dart lib/core/driver/driver_shell_handler.dart`
  - `dart run custom_lint`

## Public Interfaces / Seams

- Add or extend a data-side export artifact file service for directory
  resolution and local file cleanup; domain use cases receive the service or
  path provider abstraction, not Flutter plugins.
- Add a pay-app repository/local datasource helper that can validate or null
  missing `export_artifact_id` before update.
- Add sync dashboard state consumption for `failedRepairCount`; no new user
  workflow, only visibility of the existing repair action.
- Add migration test helper APIs under `test/_helpers/`; no production API
  changes.

## Verification Plan

- Run after each slice: `flutter analyze` and `dart run custom_lint`.
- Run targeted tests per slice, then `flutter test` after Sprint-1 blockers.
- For PDF changes: run targeted normalizer tests plus full-corpus PDF replay
  and preserve artifact summary.
- For sync/UI changes: run focused widget/provider tests, then S21 UI/sync
  preflight gate.
- Final acceptance: clean working candidate with `flutter analyze`,
  `dart run custom_lint`, and the in-scope Flutter test gates. The nightly
  sync-soak harness pass is disabled as an acceptance blocker per user
  direction on 2026-04-25.

### Current Gate Status

- `flutter analyze`: clean on 2026-04-25 after the S10 calendar overflow fix and attribution fallback logging repair.
- `dart run custom_lint`: clean on 2026-04-25 after logging the attribution fallback branch.
- `dart run tools/gen-keys/generate_keys.dart --check`: clean on 2026-04-25; typed key outputs are byte-identical.
- `pwsh -NoProfile -File tools/testing/Test-TestingHarness.ps1`: clean on 2026-04-25 after restoring settings backward traversal and saved-export action-probe catalog coverage; 35 self-test files passed.
- Focused touched tests: `flutter test test/services/pdf_service_test.dart test/features/gallery/presentation/screens/gallery_screen_test.dart` passed on 2026-04-25.
- S10 UI repro/verification flows: `entries-review-submit-ui-flow`, `settings-lifecycle-proof-ui-flow`, and post-fix `primary-tabs-responsiveness-ui-flow` passed on 2026-04-25 with 0 runtime errors and 0 failed actions.
- `flutter test`: refreshed on 2026-04-25 and logged to `.tmp/flutter-test-full-latest.log`; full-suite gate is not green. Fixed three suite-discovery failures by renaming the PDF service part-files away from `_test.dart` and verifying `flutter test test/services/pdf_service_test.dart`. The full suite still fails at 54 failures. Current failure groups are:
  - stale driver/app diagnostics contracts: driver data-sync route table, app-region auth diagnostics shape, and the printing patch newline-sensitive contract;
  - 33 remaining no-`main()` test fragments under auth, project lifecycle/list, quantities, and sync engine surfaces;
  - existing widget/form expectation drift: equipment manager autofocus and MDOT 1126 collapse/discard tests;
  - pay-app/export/PDF extraction expectation drift: generated pay-app ID expectations, GOCR fixture-contract source assertions, `QualityReport.isValid`, and row parser duplicate-semantics behavior;
  - project/sync contract drift: project provider sync-mode tests, file-sync storage-path validation, pull conflict/change-log behavior, LWW conflict logging, and mutable seed photo fixture count.
  Focused tests listed above passed for the changed slices.
- Full opt-in GOCR/PDF replay: still blocked by missing `.tmp/gocr_ocr_cache`. The cache-free PDF unit/smoke gates listed in section 4 passed again on 2026-04-25.
- Nightly sync-soak harness pass: disabled as an acceptance blocker per user
  direction on 2026-04-25.

## Assumptions

- SQLCipher/database encryption is excluded from this bug-fix lane as new
  feature work.
- Do not add new app workflows unless required to honor existing UI copy or fix
  an existing defect.
- Prefer defensive fixes and alert-noise reduction over behavior redesign.
- Existing stable app behavior is the baseline; any fix that changes output
  needs before/after proof.
