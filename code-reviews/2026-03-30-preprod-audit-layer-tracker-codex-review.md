# Per-Layer Audit Tracker

Date: 2026-03-30
Mode: read-only reporting only
Goal: run another isolated wave one layer at a time, focused on code quality, deprecated code/imports, dead or stale compatibility surface, and layer integrity; append only verified findings to the existing layer reports

## Fresh-Pass Protocol

For each layer pass:

1. Reload only this tracker, the audit index, and the target layer report.
2. Re-read only the code, tests, git history, and analyzer signals relevant to that layer.
3. Verify:
   - core behavior and wiring for that layer
   - code quality and integrity boundaries for that layer
   - dead code or stale references
   - unfinished recent work that should not be misclassified as dead
   - deprecated or legacy imports, bootstraps, barrels, and compatibility shims
   - unused imports, unused members, and hygiene debt
   - duplicated logic or duplicated entry points
   - test coverage and tooling gaps relevant to that layer
4. Append findings to the existing layer report.
5. Do not clean up code in this phase.

Note: I cannot force platform compaction on demand, but I can emulate the intended "fresh set of eyes" by isolating each pass to one layer and reloading only the relevant local context before reviewing it.

## Layer TODO

- [x] Wiring / Startup / Routing
  Report: `2026-03-30-preprod-audit-wiring-routing-codex-review.md`
  Scope: composition root, app startup, router contract, route guards, app-wide bootstrap duplication

- [x] Data / Database / Sync
  Report: `2026-03-30-preprod-audit-data-sync-codex-review.md`
  Scope: schema, migrations, datasources, repositories, sync engine/bootstrap, local/remote boundary integrity

- [x] Providers / State
  Report: `2026-03-30-preprod-audit-providers-state-codex-review.md`
  Scope: provider ordering, notifier ownership, cross-provider coupling, state-layer dead code and hygiene

- [x] Services / Integrations
  Report: `2026-03-30-preprod-audit-services-integrations-codex-review.md`
  Scope: logging, telemetry, background services, PDF/image integrations, support/help integrations

- [x] Features / Business Logic
  Report: `2026-03-30-preprod-audit-features-business-logic-codex-review.md`
  Scope: form infrastructure, feature completeness, domain-model drift, hidden special cases

- [x] Screens / Navigation UX
  Report: `2026-03-30-preprod-audit-screens-navigation-codex-review.md`
  Scope: screen behavior, user flows, stale UI surfaces, presentation dead code, navigation consistency

- [ ] Shared UI / Cross-Cutting Hygiene
  Report: `2026-03-30-preprod-audit-shared-ui-hygiene-codex-review.md`
  Scope: theme tokens, shared utilities, testing keys, deprecated compatibility layers, cross-cutting hygiene

- [ ] Tests / Tooling / Quality Gates
  Report: `2026-03-30-preprod-audit-tests-tooling-codex-review.md`
  Scope: coverage gaps, stale fixtures, CI gates, skips/suppressions, misleading test surfaces

## Current Pass

- Completed: Wiring / Startup / Routing
- Completed: Data / Database / Sync
- Completed: Providers / State
- Completed: Services / Integrations
- Completed: Features / Business Logic
- Completed: Screens / Navigation UX
- Next recommended pass: Shared UI / Cross-Cutting Hygiene

## Pass Log

- Data / Database / Sync
  Result: completed code-quality / deprecated-surface / integrity sweep
  New additions: `query_mixins.dart` still exports an unused shared batch-mixin API, `sync_queue_migration_test.dart` preserves a manually recreated legacy migration surface instead of the live engine path, entry presentation/controllers still depend directly on local datasource types, and the report now documents that this dead compatibility/test surface is not meaningful coverage for the current data architecture

- Providers / State
  Result: completed code-quality / deprecated-surface / integrity sweep
  New additions: targeted analyzer output still carries `38` provider-layer hygiene issues, several provider DI files retain redundant imports after the barrel refactor, provider barrel files have drifted into partial compatibility shims with low or zero usage, `lib/test_harness/harness_providers.dart` remains a second hand-built provider composition root, and provider-module comments still misstate runtime ordering as compile-time enforcement or reference stale pre-refactor `main.dart` line ranges

- Services / Integrations
  Result: completed code-quality / deprecated-surface / integrity sweep
  New additions: `ImageService` is still process-global singleton state behind DI-managed provider wiring, `WeatherServiceInterface` remains effectively unused compatibility surface while production code binds concrete `WeatherService`, geolocation/permission flow is duplicated between `WeatherService` and `PhotoService`, and the report now documents missing direct coverage for the singleton image path, the consent/support factory path, and the unused weather abstraction

- Features / Business Logic
  Result: completed code-quality / deprecated-surface / integrity sweep
  New additions: the unified `EntryEditorScreen` still carries an orphaned `_autoFetchWeather()` flow and unused `_isFetchingWeather` state with no production call sites, the `forms.dart` barrel still acts as an overly broad compatibility surface that keeps legacy form screens and mixed-layer contracts public, repository implementations across entries/forms/projects still show widespread post-refactor `@override` hygiene drift, and the report now documents missing coverage for the real weather-fetch path, the forms feature public import contract, and repository-interface hygiene

- Screens / Navigation UX
  Result: completed code-quality / deprecated-surface / integrity sweep
  New additions: legacy `FormFillScreen` still survives as a harness/test-facing screen alias even though production routing no longer uses it, active project-setup and help/support flows still rely on deprecated `DropdownButtonFormField.value` usage, several auth/forms screens retain redundant imports after the `shared.dart` barrel migration, and the report now documents that `form_sub_screens_test.dart` only exercises legacy delegation paths while the deprecated dropdown-backed controls still lack direct widget coverage

- Wiring / Startup / Routing
  Result: completed code-quality / deprecated-surface / integrity sweep
  New additions: `AppInitializer` still reaches into `Supabase.instance.client` directly across multiple startup services, `lib/driver_main.dart` remains as a stale legacy `flutter_driver` entrypoint beside `main_driver.dart` and `test_harness.dart`, `app_router.dart` still mixes redirect policy with shell chrome and testing-key ownership, and the report now documents missing tests around canonical bootstrap ownership and singleton-free startup composition

- Wiring / Startup / Routing
  Result: completed additional fresh scoped sweep
  New additions: split composition root, duplicated consent/auth entrypoint bootstrap, missing parity tests between `main.dart` and `main_driver.dart`

- Data / Database / Sync
  Result: completed additional fresh scoped sweep
  New additions: schema verifier only repairs missing columns, `SyncOrchestrator` still depends on post-construction setter wiring, `updateLastSyncedAt()` ignores its `userId` parameter, schema repair ownership is split across migrations and post-open verification, and the report now documents that existing sync tests mostly bypass the real production bootstrap path

- Providers / State
  Result: completed additional fresh scoped sweep
  New additions: provider-layer write guards are inconsistent and often patched after construction, sync/auth listener ownership lacks symmetric teardown in the provider layer, and the report now documents that provider tests and the test harness bypass meaningful parts of the real production provider graph

- Services / Integrations
  Result: completed additional fresh scoped sweep
  New additions: `PdfService` still self-composes nested export services and private permission wiring, `PermissionService` ownership is split between DI and ad hoc construction, mobile background sync registration is not unregistered on sign-out paths, support/log upload ownership still lives partly in the presentation provider and manual factory wiring, and the report now documents shallow or misleading coverage for PDF, support, image, weather, photo, permission, and document service surfaces

- Features / Business Logic
  Result: completed additional fresh scoped sweep
  New additions: `/form/:responseId` fallback still cannot re-dispatch to a registered custom form screen when `formType` is missing, form creation semantics remain split across `EntryFormsSection`, `FormGalleryScreen`, and the legacy `FormsListScreen`, header auto-fill still depends on ambient selected-project state instead of the response's own `projectId`, `ExportEntryUseCase` still records only the first exported file as the entry-level artifact, and the report now documents missing coverage for route fallback, creation-path parity, cross-project autofill, and bundled entry export semantics

- Screens / Navigation UX
  Result: completed additional fresh scoped sweep
  New additions: `FormGalleryScreen` can retain stale documents when project context clears, `ProjectSetupScreen` still exposes the Assignments tab in new-project flow despite its edit-only contract, the harness navigation flows still bypass the production shell container, and the report now documents placeholder or non-router test coverage across project save/navigation, project setup, settings, project list, and null-project form gallery behavior

- Shared UI / Cross-Cutting Hygiene
  Result: completed additional fresh scoped sweep
  New additions: `shared.dart` is acting as a catch-all compatibility barrel across `84` production imports, shared testing keys still preserve alias-collisions and unused legacy API surface, `SearchBarField` does not handle controller replacement safely, `ContextualFeedbackOverlay` can strand a global overlay after the caller unmounts, and the report now documents missing direct widget coverage for the shared banner/dialog/search/overlay surfaces

- Tests / Tooling / Quality Gates
  Result: completed additional fresh scoped sweep
  New additions: default CI and `flutter test` verification still do not execute the current `integration_test/` surfaces that several tests rely on for "real" coverage, Patrol deprecation left stale and partially broken workflow/doc references behind, multiple screen test files are still mislabeled as meaningful presentation coverage while asserting detached helper logic, the helper/harness infrastructure is itself lightly verified and composes a non-production app environment, and PDF diagnostic verification still depends on manual fixture generation and local machine inputs outside the automated gates
