# Tests And Tooling Audit

Date: 2026-03-30
Layer: automated tests, fixtures, CI quality gates, verification infrastructure

## Verification Snapshot

- `flutter analyze` failed on 2026-03-30 with `383 issues`.
- `flutter test` passed on 2026-03-30 on the current working tree.
- The repository currently contains `483` files under `test/`.

## Findings

### 1. High | Confirmed
The highest-risk post-refactor composition paths still lack direct tests.

Evidence:

- No direct test files exist for:
  - `test/core/di/app_initializer_test.dart`
  - `test/core/router/app_router_test.dart`
  - `test/features/sync/application/background_sync_handler_test.dart`
  - `test/features/sync/di/sync_providers_test.dart`
  - `test/core/di/app_providers_test.dart`

Why this matters:

- The suite is green without directly exercising the startup, routing, and background-sync edges most likely to regress after the recent refactors.
- This leaves major pre-production risks to comments and manual reasoning instead of executable verification.

### 2. High | Confirmed
The test and harness surface still actively preserves the stale `FormsListScreen` flow.

Evidence:

- Harness routing still exposes the old flow:
  - `lib/test_harness/flow_registry.dart:29-49`
  - `lib/test_harness/flow_registry.dart:206-226`
  - `lib/test_harness/screen_registry.dart:84`
- Shared test keys still preserve the same screen contract:
  - `lib/shared/testing_keys/toolbox_keys.dart:19-49`
- The stale screen still has its own dedicated test file:
  - `test/features/forms/presentation/screens/forms_list_screen_test.dart:1-220`

Why this matters:

- The tests are not just tolerating stale surface area; they are helping maintain it.
- That increases the chance that cleanup work on the old forms path will appear risky because the harness and tests still depend on it.

Classification: stale post-refactor drift.

### 3. Medium | Confirmed
Some form fixtures and tests still encode outdated template-path assumptions.

Evidence:

- `test/helpers/sync/sync_test_data.dart:314` still defaults builtin form templates to `assets/forms/mdot_0582b.pdf`.
- Active production builtin registration uses `assets/templates/forms/mdot_0582b_form.pdf`:
  - `lib/features/forms/data/registries/builtin_forms.dart:8-10`
- `test/features/forms/services/form_pdf_service_test.dart:277-289` verifies `resolveTemplatePath` against the newer `assets/templates/forms/mdot_0582b_form.pdf` path.

Why this matters:

- The test suite is encoding two different builtin-template conventions at once.
- That weakens the value of fixtures as a source of truth and makes template-path regressions easier to miss.

### 4. Medium | Confirmed
Some tests are validating simplified or incomplete form behavior instead of the more complete registry-driven behavior the refactor is aiming for.

Evidence:

- `test/features/forms/presentation/screens/form_gallery_screen_test.dart:247,266,338,343,373` repeatedly asserts or constructs new forms with `responseData: '{}'`.
- The production concern is that `FormGalleryScreen` also creates new responses with `responseData: '{}'`:
  - `lib/features/forms/presentation/screens/form_gallery_screen.dart:149-155`
- The registry already has a form-specific initial-data mechanism:
  - `lib/features/forms/data/registries/mdot_0582b_registrations.dart:19-26`

Why this matters:

- The tests currently normalize the same incomplete behavior found in production instead of exposing it.
- That reduces the odds of catching regressions when form initialization is eventually generalized properly.

Classification: unfinished recent work being unintentionally locked in by tests.

### 5. Medium | Confirmed
CI quality gates are softer than the current pre-production audit standard.

Evidence:

- `.github/workflows/e2e-tests.yml:83` runs `flutter analyze --no-fatal-infos`
- `.github/workflows/e2e-tests.yml:104` runs `flutter test --coverage`
- `.github/workflows/e2e-tests.yml:109-110` uploads coverage with `fail_ci_if_error: false`
- No coverage threshold or analyzer-zero policy is defined in this workflow file.

Why this matters:

- The workflow proves the app can be analyzed and tested in CI, but it does not enforce the stricter hygiene bar this audit is targeting.
- A pre-production cleanup effort benefits from gates that stop analyzer debt and weak coverage from quietly persisting.

### 6. Medium | Confirmed
The test tree contains a non-trivial number of skips and lint suppressions, which marks real verification blind spots.

Evidence:

- There are `12` `skip:` occurrences under `test/`.
- There are `32` `ignore_for_file` or `// ignore:` suppressions under `test/`.
- Representative examples:
  - `test/features/pdf/services/mp/mp_stage_trace_diagnostic_test.dart:605,730`
  - `test/features/pdf/extraction/integration/full_pipeline_integration_test.dart:658`
  - `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart:161,220,318,360,411,441,492`
  - `test/features/forms/data/models/form_response_test.dart:60,90,113`
  - `test/features/sync/adapters/form_response_adapter_test.dart:3`

Why this matters:

- Some suppressions are pragmatic, but at this volume they also signal parts of the suite that are harder to trust as clean regression detectors.
- The skipped tests cluster around diagnostics and fixture-heavy paths, which are exactly the areas that tend to drift quietly.

### 7. Medium | Confirmed
At least one stale screen test file no longer matches the real behavior of the screen it is named after.

Evidence:

- `test/features/forms/presentation/screens/forms_list_screen_test.dart:5-8` explicitly says it is testing screen logic rather than the real widget because full widget testing is deferred.
- That same file tests generic builtin/custom form filtering and multi-form behavior:
  - `test/features/forms/presentation/screens/forms_list_screen_test.dart:82-157`
- The actual screen is hardcoded around 0582B creation and listing:
  - `lib/features/forms/presentation/screens/forms_list_screen.dart:40-92`
  - `lib/features/forms/presentation/screens/forms_list_screen.dart:166-170`

Why this matters:

- The file name implies real screen coverage, but the assertions are mostly detached model logic and no longer describe the actual screen implementation closely.
- This is a test-hygiene problem, not just a naming issue, because it can create false confidence about stale UI coverage.

## Coverage Gaps

- No direct tests for startup/router composition: `AppInitializer`, `AppRouter`, `app_providers`.
- No direct tests for background-sync/bootstrap edges: `BackgroundSyncHandler`, `SyncProviders`.
- No direct tests for schema/runtime repair edges: `SchemaVerifier`.
- No direct tests for recent settings/support additions:
  - `support_provider`
  - `consent_support_factory`
  - `log_upload_remote_datasource`
  - `user_certification_local_datasource`
- No direct test file for `InspectorFormProvider`, despite it being a major hub in the new form architecture.
- `ExportFormUseCase` tests stub out PDF generation and do not verify the real template-resolution path that is currently divergent from builtin registration.
