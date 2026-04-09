# Features And Business Logic Audit

Date: 2026-03-30
Layer: feature behavior, domain logic, form infrastructure, feature completeness

## Findings

### 1. High | Confirmed
Form generalization is still partial. The new registry architecture exists, but 0582B assumptions still leak through active production code.

Evidence:

- `lib/features/forms/data/models/inspector_form.dart:217-218` still exposes `is0582B`.
- `lib/features/forms/presentation/providers/inspector_form_provider.dart:384-396` still hardcodes `'mdot_0582b'` for proctor-row normalization.
- `lib/features/forms/presentation/screens/mdot_hub_screen.dart:719-723` still searches for the builtin form with explicit 0582B heuristics.
- `lib/core/database/schema_verifier.dart:286` and `lib/core/database/database_service.dart:799,812` still default/coalesce form type to 0582B.

Why this matters:

- The form system is structurally generalized but behaviorally still single-form-biased.
- Adding another form type will still collide with hidden 0582B assumptions.

### 2. High | Confirmed
`FormGalleryScreen` does not use registry-backed initial data when creating new forms.

Evidence:

- `lib/features/forms/presentation/screens/form_gallery_screen.dart:147-154`
- New responses are created with `responseData: '{}'` regardless of form type.

Why this matters:

- The code bypasses form-specific initial state factories.
- Any form that expects structured default data will either degrade or require fallback logic elsewhere.

Classification: unfinished recent work from the forms-infrastructure rollout.

### 3. High | Confirmed
`FormPdfService.generateFilledPdf()` builds a synthetic asset path that diverges from the seeded builtin template path.

Evidence:

- `lib/features/forms/data/services/form_pdf_service.dart:1141-1145` builds a stub form with `templatePath: 'assets/forms/$formType.pdf'`.
- Builtin form registration uses `assets/templates/forms/mdot_0582b_form.pdf` in `lib/features/forms/data/registries/builtin_forms.dart`.
- `generateFilledPdf()` is not dead code:
  - `lib/features/forms/domain/usecases/export_form_use_case.dart:30` calls it directly.

Why this matters:

- Export behavior depends on a template path convention that does not match the current builtin registration path.
- This is a brittle export path for the current 0582B form and an obvious hazard for future forms.

### 4. Medium | Confirmed
The deprecated 0582B-only screen is still part of the maintained feature surface.

Evidence:

- `lib/features/forms/presentation/screens/forms_list_screen.dart` still hardcodes 0582B creation, listing, copy, and labels.
- `lib/features/forms/presentation/screens/screens.dart:3` still exports it.
- `lib/test_harness/screen_registry.dart:84` and `lib/test_harness/flow_registry.dart:33,48,210,225` still wire it into harness flows.

Why this matters:

- This is no longer just historical code sitting on disk; it is still part of non-production runtime surfaces and tests.
- It increases maintenance cost and keeps old assumptions alive.

Classification: stale post-refactor drift.

### 5. Medium | Confirmed
The support-ticket feature is operationally incomplete even though the schema and UI landed.

Evidence:

- `lib/features/settings/presentation/providers/support_provider.dart:131-133`
- The provider persists locally, but explicitly defers the sync trigger.

Why this matters:

- The feature looks complete at the UI layer but is still relying on later sync side effects to reach the backend.
- This should be treated as unfinished recent work, not dead code.

### 6. Medium | Confirmed
The supposedly generic `FormResponse` model still carries substantial 0582B-specific structure and legacy compatibility behavior.

Evidence:

- `lib/features/forms/data/models/form_response.dart:210-251` exposes `parsedTestRows` and `parsedProctorRows` as 0582B-specific convenience getters.
- `lib/features/forms/data/models/form_response.dart:298-330` exposes `withTableRow`, `withProctorRows`, and `withTestRows`, again in 0582B-shaped terms.
- `lib/features/forms/data/models/form_response.dart:73-78,138-160,223-229` still preserves deprecated `tableRows` compatibility paths.

Why this matters:

- The model layer is still biased toward one form family even after the registry-based generalization.
- A second real form type would still inherit a domain model whose convenience API is shaped around 0582B semantics.
- The refactor changed naming and registration first, but the core response model remains only partially generalized.

### 7. Medium | Confirmed
`FormViewerScreen` is generic only at the shell level; the substantive body still treats 0582B as the only fully supported form.

Evidence:

- `lib/features/forms/presentation/screens/form_viewer_screen.dart:266-267` titles the screen from `response.formType`, implying generic support.
- `lib/features/forms/presentation/screens/form_viewer_screen.dart:297-306` conditionally renders tests, proctors, and standards only when `response.formType == 'mdot_0582b'`.

Why this matters:

- Non-0582B forms currently fall back to a reduced viewer experience rather than a truly form-driven renderer.
- This is feature incompleteness, not just UI debt, because the runtime behavior differs by hidden form-type assumptions.

### 8. High | Confirmed
The form route fallback cannot recover custom-screen dispatch when `formType` is missing from the URL.

Evidence:

- `lib/core/router/app_router.dart:694-715` only checks `FormScreenRegistry` when `state.uri.queryParameters['formType']` is present; otherwise it falls straight through to `FormViewerScreen(responseId: responseId)`.
- `lib/features/forms/presentation/screens/form_viewer_screen.dart:50-76` loads the response by ID, but it never re-consults `FormScreenRegistry` after the response's real `formType` is known.
- `lib/features/forms/data/repositories/form_response_repository.dart:361-366` still exposes `getFormTypeForResponse()`, which shows the architecture anticipated a response-ID-only lookup path, but that lookup is not used by the router fallback.

Why this matters:

- Old links, deep links, or internal navigation surfaces that omit the `formType` query param will not land on the form's registered custom screen.
- For `mdot_0582b`, that means the route can bypass `MdotHubScreen` and open the generic viewer instead.
- The registry architecture is therefore only reliable when every caller remembers to thread `formType` through the route contract.

Classification: stale post-refactor contract drift.

### 9. Medium | Confirmed
Form creation still has multiple competing source-of-truth implementations instead of one authoritative contract.

Evidence:

- `lib/features/entries/presentation/widgets/entry_forms_section.dart:72-84` creates new responses from `FormInitialDataFactory`.
- `lib/features/forms/presentation/screens/form_gallery_screen.dart:149-153` creates new responses with `responseData: '{}'`, bypassing the registry-backed initial-data factory entirely.
- `lib/features/forms/presentation/screens/forms_list_screen.dart:58-75` still hand-builds a bespoke 0582B payload with `chart_standards`, `operating_standards`, and `remarks`.
- `test/features/forms/presentation/screens/form_gallery_screen_test.dart:359-373` explicitly codifies the `FormGalleryScreen` behavior that creates responses with `responseData: '{}'`.

Why this matters:

- The same form type is initialized differently depending on whether it is started from an entry, the new gallery, or the legacy 0582B list.
- The registry-based forms architecture is not yet the sole owner of response bootstrapping semantics.
- Any future form type will need coordinated edits across multiple creation paths unless this is consolidated later.

Classification: mixed stale drift plus unfinished recent work from the forms-infrastructure rollout.

### 10. High | Confirmed
Header auto-fill still depends on ambient `ProjectProvider.selectedProject` state instead of the response's own `projectId`.

Evidence:

- `lib/features/forms/presentation/screens/form_viewer_screen.dart:84-95` auto-fills empty headers from `context.read<ProjectProvider>().selectedProject`.
- `lib/features/forms/presentation/screens/mdot_hub_screen.dart:170-181` does the same in the 0582B-specific screen.
- In both screens, the response has already been loaded by ID before auto-fill runs, so the form's authoritative `projectId` is available on the loaded model.

Why this matters:

- Opening a response while a different project is selected can inject the wrong project metadata into an otherwise empty header.
- The behavior depends on whichever project happens to be active in UI state, not the project that owns the response.
- This is a data-integrity risk, not just presentation drift, because the user can subsequently save the mismatched header back to the response.

### 11. Medium | Confirmed
`ExportEntryUseCase` still exposes "bundle export" behavior without a real bundle artifact or matching metadata model.

Evidence:

- `lib/features/entries/domain/usecases/export_entry_use_case.dart:50-57` explicitly documents that bundle merging is deferred and persists only `paths.first` into the `EntryExport` row.
- `test/features/entries/domain/usecases/export_entry_use_case_test.dart:147-155` verifies that one path is returned per attached form response.
- `test/features/entries/domain/usecases/export_entry_use_case_test.dart:157-166` verifies that only a single `EntryExport` metadata row is created when exports exist.

Why this matters:

- Multi-form entries generate multiple PDF files, but the entry-level export history only has one canonical file path.
- Any feature that treats `EntryExport` as "the exported entry artifact" is operating on an incomplete representation.
- This is clearly unfinished recent work rather than dead code, because the use case is active and tested in its current partial state.

### 12. Medium | Confirmed
The unified entry editor still carries an orphaned weather auto-fetch implementation that is no longer connected to live UI behavior.

Evidence:

- `lib/features/entries/presentation/screens/entry_editor_screen.dart:99` still defines `_isFetchingWeather`.
- `lib/features/entries/presentation/screens/entry_editor_screen.dart:467-522` still contains `_mapConditionToWeather()` and `_autoFetchWeather()`, including a direct `WeatherService.fetchWeatherForCurrentLocation(...)` call and persistence back into `DailyEntryProvider`.
- Repo-wide search for `_autoFetchWeather(` and `_isFetchingWeather` only found those declarations/usages inside `entry_editor_screen.dart`; there are no production call sites that invoke the flow or render the loading state.
- `test/features/entries/presentation/screens/entry_editor_screen_test.dart:567-570` does not exercise the real screen path; it only asserts a local `const isFetchingWeather = true`.

Why this matters:

- The screen still owns asynchronous weather-fetch logic, state, and service coupling that no longer participates in runtime behavior.
- This increases maintenance surface in the main entry workflow while giving a false impression that weather auto-fetch is still a supported feature.
- Classification: unfinished recent work or abandoned logic from the unified entry-editor rollout, not harmless dead code.

### 13. Medium | Confirmed
The form feature's public import surface is still an overly broad compatibility barrel, which keeps stale screens and mixed-layer contracts live.

Evidence:

- `lib/features/forms/forms.dart:1-3` re-exports the entire data, domain, and presentation trees.
- `lib/features/forms/presentation/presentation.dart:1-4` re-exports `screens/screens.dart`, and `lib/features/forms/presentation/screens/screens.dart:1-4` still exports `forms_list_screen.dart` alongside the newer gallery/viewer surfaces.
- `lib/core/router/app_router.dart:25`, `lib/core/di/app_initializer.dart:27`, `lib/test_harness/flow_registry.dart:4`, `lib/test_harness/screen_registry.dart:5`, `lib/features/forms/di/forms_init.dart:3`, and `lib/features/forms/di/forms_providers.dart:3` all import `package:construction_inspector/features/forms/forms.dart`.
- The targeted analyzer run flags `lib/features/forms/di/forms_providers.dart:5-16` for eleven unnecessary imports because the same symbols are already being pulled in through the broad `forms.dart` barrel.
- Harness flows still resolve obsolete form surfaces through this same public barrel: `lib/test_harness/flow_registry.dart:33-55,210-232` and `lib/test_harness/screen_registry.dart:84-105`.

Why this matters:

- The feature no longer has a curated public contract; importing "forms" also re-exports obsolete screens and cross-layer implementation details.
- The broad barrel keeps the legacy `FormsListScreen` and related 0582B-only flow reachable even as the registry/gallery architecture becomes the intended path.
- This is integrity drift in the feature boundary, not just import style preference.

### 14. Medium | Confirmed
The domain/repository refactor remains mechanically incomplete across feature-owned repositories, leaving contract hygiene uneven in active implementations.

Evidence:

- The targeted analyzer run reports `annotate_overrides` drift across repository implementations that now sit behind feature-domain interfaces:
  - `lib/features/entries/data/repositories/daily_entry_repository.dart:46,51,60,65,70,94,105,110,145,155,160,185,195,205,228`
  - `lib/features/entries/data/repositories/document_repository.dart:62,86,109,113,117`
  - `lib/features/entries/data/repositories/entry_export_repository.dart:53,69,73`
  - `lib/features/forms/data/repositories/form_response_repository.dart:19,42,56,69,82,95,108,127,150,181,214,228,239,250,261,276`
  - `lib/features/forms/data/repositories/form_export_repository.dart:55,75,79,83`
  - `lib/features/forms/data/repositories/inspector_form_repository.dart:15,36,50,63,87,141`
  - `lib/features/projects/data/repositories/project_repository.dart:37,42,47,52,70,76,93,111,140,147,163,188,193,221`
- Representative implementations such as `lib/features/entries/data/repositories/daily_entry_repository.dart:38-228`, `lib/features/forms/data/repositories/form_response_repository.dart:16-276`, `lib/features/forms/data/repositories/inspector_form_repository.dart:13-141`, and `lib/features/projects/data/repositories/project_repository.dart:33-221` show many interface methods still written as plain methods rather than explicit overrides.

Why this matters:

- The feature packages now advertise domain/repository boundaries, but the implementations still show refactor residue rather than fully normalized contracts.
- This weakens reviewability and makes interface drift easier to miss in some of the most central business-logic repositories in the app.
- Classification: incomplete post-refactor hygiene, not a runtime bug by itself.

## Coverage Gaps

- Form feature tests exist for both `FormGalleryScreen` and `FormsListScreen`, which is useful, but the coexistence itself is part of the drift problem.
- No direct test exists for the `FormPdfService.generateFilledPdf()` asset-path convention against real builtin form registrations.
- No direct test file exists for `InspectorFormProvider`, even though it now concentrates form loading, response creation, save/update flows, and 0582B-specific normalization.
- No route-level test verifies `/form/:responseId` behavior when `formType` is omitted for a response whose registered type has a custom screen.
- `test/features/forms/presentation/screens/form_gallery_screen_test.dart:359-373` codifies the current `responseData: '{}'` creation path, but there is still no parity test asserting that `FormGalleryScreen`, `EntryFormsSection`, and the legacy `FormsListScreen` initialize equivalent response shapes for the same form type.
- No test covers the auto-fill mismatch risk where `ProjectProvider.selectedProject` does not match `response.projectId` in either `FormViewerScreen` or `MdotHubScreen`.
- `test/features/entries/domain/usecases/export_entry_use_case_test.dart` verifies path counts and single-row metadata creation, but there is no test asserting the intended end-state for bundled entry exports or guarding against the current first-path-only representation.
- `test/features/entries/presentation/screens/entry_editor_screen_test.dart:567-570` treats weather-fetch loading as a placeholder boolean assertion, and no direct test was found that proves the production `EntryEditorScreen` can invoke or render the `_autoFetchWeather()` path.
- No test was found that locks down the intended public import contract for the forms feature; current coverage allows `forms.dart` to keep exporting legacy screens and mixed-layer implementation symbols without detection.
- No hygiene-focused test or lint gate currently protects the feature-owned repository implementations from continuing contract drift after the domain/repository refactor; the `annotate_overrides` findings are only caught opportunistically by analyzer output.
