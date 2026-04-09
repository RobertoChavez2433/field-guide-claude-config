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

### 8. High | Confirmed
The default verification path is not exercising the integration-test surfaces that multiple tests and comments still treat as the place for "real" startup and widget coverage.

Evidence:

- CI only runs analyzer and `flutter test`:
  - `.github/workflows/e2e-tests.yml:83`
  - `.github/workflows/e2e-tests.yml:104`
- The app-level smoke test explicitly defers real startup pumping to `integration_test/`:
  - `test/widget_test.dart:2`
  - `test/widget_test.dart:11`
- The repo still contains active `integration_test/` files outside Patrol:
  - `integration_test/mp_extraction_integration_test.dart`
  - `integration_test/springfield_report_test.dart`
  - `integration_test/rendering_diagnostic_test.dart`
  - `integration_test/generate_mp_fixtures_test.dart`

Why this matters:

- A green default suite still does not prove the app bootstrap, rendered startup path, or integration diagnostics run correctly.
- The testing story currently depends on a directory that the main CI workflow never executes.

### 9. Medium | Confirmed
The Patrol-to-new-testing-system migration left stale and partially broken references across workflows, docs, and generated artifacts.

Evidence:

- Both workflow files still point at a plan file that does not exist in `.claude/plans/`:
  - `.github/workflows/e2e-tests.yml:22`
  - `.github/workflows/nightly-e2e.yml:2`
- Both workflow files also point at `integration_test/_deprecated/patrol/`, but that directory is not present:
  - `.github/workflows/e2e-tests.yml:23`
  - `.github/workflows/nightly-e2e.yml:3`
- `integration_test/test_bundle.dart` is still generated Patrol scaffolding even though it intentionally contains no tests:
  - `integration_test/test_bundle.dart:1`
  - `integration_test/test_bundle.dart:13`
  - `integration_test/test_bundle.dart:21`
  - `integration_test/test_bundle.dart:36`
- The top-level README still advertises Patrol scripts as the testing entrypoint:
  - `README.md:79`
  - `README.md:80`
- The repo's testing rule/docs layer still centers Patrol:
  - `.claude/rules/testing/patrol-testing.md:14`
  - `.claude/docs/guides/testing/e2e-test-setup.md:5`

Why this matters:

- Contributors are given conflicting signals about what the authoritative E2E/integration path is.
- Missing file references and empty generated Patrol scaffolding are dead process surface area, not just harmless comments.

Classification: stale post-migration tooling drift.

### 10. Medium | Confirmed
Several screen test files are still labeled and organized as if they provide meaningful presentation coverage, but they mostly assert local boolean/math/model behavior instead of the real screen contracts.

Evidence:

- `test/features/quantities/presentation/screens/quantities_screen_test.dart:7` says full widget coverage lives in Patrol, while the file itself is dominated by local list/filter/value assertions.
- `test/features/entries/presentation/screens/entry_editor_screen_test.dart:11` says real coverage requires Patrol, while the file mostly tests detached field-validation and collection logic.
- `test/features/projects/presentation/screens/project_setup_screen_logic_test.dart:10` and `test/features/projects/presentation/screens/project_setup_screen_ui_state_test.dart:8` frame themselves as screen coverage, but rely on boolean state simulations rather than the widget tree.
- `test/features/todos/presentation/screens/todos_screen_test.dart:8-12` explicitly says widget rendering lives in `integration_test/`, while the file mostly tests helper sorting/filtering logic.
- `test/features/gallery/presentation/screens/gallery_screen_test.dart:9` similarly defers real widget coverage and tests pure filter helpers.

Why this matters:

- File names and group names overstate how much real presentation behavior is being verified.
- Screen regressions in routing, provider wiring, visual states, and actual interaction contracts can slip through while these files still pass.

### 11. Medium | Confirmed
The thin helper and harness surfaces used to simplify tests are themselves lightly verified and encourage non-production app composition.

Evidence:

- `test/helpers/provider_wrapper.dart:5-30` only wraps children in `MaterialApp` and optional `ChangeNotifierProvider`s; it does not model the production router, shell, startup, or service graph.
- `test/helpers/README.md:125-127` recommends those wrappers as the default pattern for "complex tests".
- `test/helpers/README.md:140-142` still documents an old tree shape (`presentation/`, `widget_test.dart` as app-level widget tests) that no longer matches the current test layout closely.
- Repo-wide search found no direct tests covering:
  - `lib/test_harness/harness_providers.dart`
  - `lib/test_harness/stub_router.dart`
  - `lib/test_harness/flow_registry.dart`
  - `lib/test_harness/screen_registry.dart`
- Those harness files still compose their own large provider/router world and retain stale form-era routing:
  - `lib/test_harness/harness_providers.dart:95`
  - `lib/test_harness/harness_providers.dart:155`
  - `lib/test_harness/stub_router.dart:4`
  - `lib/test_harness/stub_router.dart:22`
  - `lib/test_harness/flow_registry.dart:30`
  - `lib/test_harness/flow_registry.dart:48`
  - `lib/test_harness/screen_registry.dart:84`

Why this matters:

- The helpers make it easy to write passing tests against a much simpler environment than production.
- Because the harness layer itself is unverified, the suite can inherit blind spots from its own test infrastructure.

### 12. Medium | Confirmed
Part of the PDF diagnostic verification stack depends on manually generated fixtures and local machine inputs that the automated quality gates do not enforce.

Evidence:

- `test/features/pdf/services/mp/mp_stage_trace_diagnostic_test.dart:18-19` requires regenerating fixtures via `integration_test/generate_mp_fixtures_test.dart`, and the diagnostic groups are skipped when fixtures are not populated:
  - `test/features/pdf/services/mp/mp_stage_trace_diagnostic_test.dart:605`
  - `test/features/pdf/services/mp/mp_stage_trace_diagnostic_test.dart:730`
- `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart` declares the current fixture state is empty/incomplete and skips multiple checks:
  - `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart:11-13`
  - `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart:161`
  - `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart:220`
  - `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart:318`
  - `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart:360`
  - `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart:411`
  - `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart:441`
  - `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart:492`
- The fixture generator itself needs a Windows device target and an external PDF path:
  - `integration_test/generate_mp_fixtures_test.dart:15-16`
  - `integration_test/generate_mp_fixtures_test.dart:25-28`

Why this matters:

- These diagnostics can silently drop out of effective coverage when fixtures are stale, absent, or not regenerated on the right machine.
- The current quality gates do not verify the prerequisites needed for those tests to remain meaningful.

### 13. High | Confirmed
The deprecated Patrol and `flutter_driver` stacks are not just historical references; they are still wired into the live test manifest and non-production entrypoints.

Evidence:

- `pubspec.yaml:119-121` still declares both `flutter_driver` and `integration_test` as dev dependencies.
- `pubspec.yaml:133-138` still declares `patrol: ^4.1.0` and a live `patrol.test_directory: integration_test` configuration.
- `lib/test_harness.dart:14,18` still imports `package:flutter_driver/driver_extension.dart` and calls `enableFlutterDriverExtension()`.
- `lib/driver_main.dart:2,7` still imports `package:flutter_driver/driver_extension.dart` and calls `enableFlutterDriverExtension()`.
- `integration_test/test_bundle.dart:7-8,12-13,21,24,40-41,44` is still generated Patrol scaffolding that initializes `PatrolBinding` and `PatrolAppService` even though the file also says all Patrol E2E tests were moved away.

Why this matters:

- The repository is carrying three concurrent verification stories at once: `integration_test`, Patrol-generated glue, and `flutter_driver` entrypoints.
- That makes it harder to tell which stack is canonical, which dependencies are still intentional, and which toolchain contracts can be safely removed later.

Classification: stale post-migration tooling drift that is still part of the active test surface.

### 14. Medium | Confirmed
`integration_test/grant-permissions.sh` is stale enough to misconfigure the current Android app under test.

Evidence:

- `integration_test/grant-permissions.sh:4,8-9,44` still tells users to run the script before `patrol test`.
- `integration_test/grant-permissions.sh:16` hardcodes `PACKAGE="com.example.construction_inspector"`.
- The live Android app id is `com.fieldguideapp.inspector`:
  - `android/app/build.gradle.kts:21`
  - `android/app/build.gradle.kts:37`

Why this matters:

- This is not just an outdated comment. Running the script as documented targets the wrong package name, so the permission grants do not line up with the current app identity.
- That weakens one of the few remaining pieces of scripted device-test setup and can create false negatives or wasted debugging time.

### 15. Medium | Confirmed
The shared test-helper documentation is materially stale and includes broken imports, obsolete screen examples, and an outdated test-tree contract.

Evidence:

- `test/helpers/README.md:12,48,84` still recommends importing helper files via `package:construction_inspector/test/helpers/...`, even though these are repo test files rather than package-library imports.
- `test/helpers/README.md:85` references `package:construction_inspector/presentation/widgets/project_card.dart`, which does not exist in the current tree.
- `test/helpers/README.md:101-119` uses `HomeScreen` and `DashboardScreen` as example widgets, but those examples are not backed by current imports in the file and reflect older structure assumptions.
- `test/helpers/README.md:140-142` still documents a simplified `test/presentation/` + app-level `widget_test.dart` tree shape that no longer reflects the current repo layout closely.
- Direct path checks during this pass confirmed:
  - `lib/presentation/widgets/project_card.dart` does not exist
  - `lib/presentation/screens/home_screen.dart` does not exist

Why this matters:

- The docs that are supposed to make writing tests easier now encode broken examples and outdated structure assumptions.
- That creates friction for future cleanup and increases the chance that contributors copy obsolete patterns into new tests.

### 16. Medium | Confirmed
The test/tooling layer is carrying substantial unresolved analyzer hygiene debt, including deprecated API use inside active golden tests.

Evidence:

- A targeted `flutter analyze test lib/test_harness integration_test` run during this pass reported `219 issues`.
- Representative integration/harness hygiene findings from that run:
  - `integration_test/cell_crop_diagnostic_test.dart:24` unnecessary import
  - `integration_test/grid_line_drift_test.dart:20` unused import
  - `lib/test_harness/harness_providers.dart:15` unnecessary import
  - `test/features/auth/domain/use_cases/sign_in_use_case_test.dart:8-9` unused imports
  - `test/features/projects/presentation/screens/project_setup_screen_test.dart:37` dead code
- Representative deprecated test API usage from the same analyzer run:
  - `test/golden/components/dashboard_widgets_test.dart:17,38,132,142,175,189,322` still uses deprecated `AppTheme` color members such as `primaryCyan`, `success`, `warning`, `error`, `textPrimary`, `textSecondary`, and `surfaceHighlight`
  - `test/golden/widgets/project_card_test.dart:147,152,169,178,182,196,206` still uses the same deprecated theme members

Why this matters:

- The verification layer is not clean enough to serve as a strong integrity gate for the rest of the app.
- When tests and harness code carry this much local hygiene debt, analyzer noise in the verification stack itself can hide more meaningful regressions.

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
- No default CI job runs the current `integration_test/` directory, despite several comments and placeholder tests treating it as the location for real widget/integration coverage.
- No direct tests verify the test harness itself: `harness_providers`, `stub_router`, `flow_registry`, or `screen_registry`.
- No executable replacement is present in-repo for the deprecated Patrol widget/E2E coverage claims still referenced by several screen test files.
- PDF diagnostic coverage depends on manual fixture generation and local environment setup, but the automated gates do not enforce fixture freshness or availability.
- No guard verifies whether `flutter_driver`, Patrol config, and generated `integration_test/test_bundle.dart` are still intentionally part of the canonical test stack.
- No validation keeps device-test helper scripts aligned with the live Android application id or current integration-test command path.
- No lint or review gate keeps golden tests and test harness code off deprecated theme APIs, dead code, and stale imports.
- No documentation check keeps `test/helpers/README.md` examples aligned with the current repo structure and import reality.
