# Field Guide App Comprehensive Plan (Production Readiness + Form Streamlining)

**Created**: 2026-01-28  
**Purpose**: Merge CODEX Production Readiness Plan with the Form Streamlining Plan into a single, PR-sized, detailed roadmap.

---

## Review Findings (Gaps + Risks to Address)

1) **Auto-fill overwrite and provenance risk**  
- Current plan assumes auto-fill can run freely, but no explicit rule for *never overwriting user-edited values* or for storing provenance per field.  
- Add explicit `{value, source, confidence, isUserEdited}` handling and a user toggle for “clear auto-filled only.”

2) **Template drift risk**  
- No explicit detection for updated PDFs (field name changes = silent breaks).  
- Add template hashing + re-mapping prompt and store template metadata.

3) **Field registry needs repeat/group support**  
- The registry model does not account for repeated semantic fields (e.g., multiple tests, multiple locations).  
- Add `repeat_group` and `repeat_index` so one semantic name can map to multiple PDF fields.

4) **Calculation engine safety**  
- Plan suggests generic formulas; no guardrails for divide-by-zero or invalid input.  
- Use a whitelist parser or dedicated functions per form type; add rounding rules and safe defaults.

5) **Carry-forward defaults missing**  
- The plan does not cover “last-used values” for non-project fields.  
- Add `form_field_cache` for per-project carry-forward and a UI toggle per form.

6) **Preview caching and perf**  
- PDF preview can be heavy; no cache invalidation or state hash logic.  
- Add preview byte cache keyed by form-state hash, plus manual refresh.

7) **Mapping UI bulk tools**  
- Mapping UI is manual; needs “bulk apply category,” search, and confidence filtering to scale.



8) **Asset-only template loading**  
- Form PDFs currently load only from assets, so imported PDFs will not render.  
- Add a template loader that supports asset + file-system sources, and persist source metadata.

9) **Non-text PDF fields unsupported**  
- Current PDF fill only handles text fields; checkboxes/radios/dropdowns are ignored.  
- Extend field types and fill logic before relying on mapping UI for complex forms.

10) **No metadata store for auto-fill provenance**  
- `FormResponse` only stores `response_data` and `table_rows`, so source tracking and “clear auto-filled only” are not possible.  
- Add a response metadata map (or separate table) to store `source`, `confidence`, and `is_user_edited` per field.

11) **Auto-fill context not guaranteed loaded**  
- Auto-fill currently reads providers without loading their data first.  
- Ensure providers are hydrated or read directly from repositories before auto-fill runs.

12) **Density field naming mismatch**  
- Parsing keywords and planned calculator fields use different names (e.g., `moisture_content` vs `moisture_pcf`).  
- Align naming across parsing, registry, calculations, and PDF mapping.

13) **Registry + template data not in sync path**  
- New tables won’t sync unless remote schema and sync service include them.  
- Add Supabase tables + sync adapter updates for registry, aliases, and template metadata.
---

## Consolidated PR-Sized Roadmap

### Phase 1 (PR): Safety Net + Baseline Verification
**Goal**: Reduce regression risk before large refactors.

**1.1** Expand Patrol flows for critical paths  
- Files: `integration_test/`, `test_driver/`, `patrol.yaml`  
- Instructions: add/extend flows for entry/report/project/toolbox; ensure at least one run per PR.

**1.2** Add focused widget tests for mega screens  
- Files: `test/features/entries/`, `test/features/projects/`, `test/features/quantities/`  
- Instructions: presence/assertion tests (no golden snapshots); cover navigation and main actions.

---

### Phase 2 (PR): Toolbox Refactor Set A (Structure + DI + Provider Safety)
**Goal**: Address missing items from Code Review Plan PR1.

**2.1** Extract Form Fill widgets  
- Files: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`, `lib/features/toolbox/presentation/widgets/` (create)  
- Instructions: move section widgets into dedicated files to reduce rebuild scope.

**2.2** Inject parsing/PDF services via Provider  
- Files: `lib/main.dart`, `lib/features/toolbox/presentation/screens/form_fill_screen.dart`  
- Instructions: wire service injection; do not instantiate services in the widget tree.

**2.3** Fix mutable list updates  
- Files: `lib/features/toolbox/presentation/providers/inspector_form_provider.dart`  
- Instructions: replace in-place mutations with immutable list copies; confirm notifier updates.

**2.4** Rename datasource tests  
- Files: `test/features/toolbox/data/datasources/inspector_form_local_datasource_test.dart`, `test/features/toolbox/data/datasources/todo_item_local_datasource_test.dart`  
- Instructions: rename to match actual subject under test.

---

### Phase 3 (PR): Toolbox Refactor Set B (Resilience + Utilities)
**Goal**: Address missing items from Code Review Plan PR2.

**3.1** Add template load error handling  
- Files: `lib/features/toolbox/data/services/form_pdf_service.dart`  
- Instructions: wrap template load with `try/catch` and surface clear UI errors.

**3.2** Add FieldFormatter utility  
- Files: `lib/shared/utils/field_formatter.dart` (create), `lib/shared/utils/utils.dart`, `lib/features/toolbox/data/services/form_pdf_service.dart`, `lib/features/toolbox/presentation/screens/form_fill_screen.dart`  
- Instructions: centralize numeric/date formatting and padding rules.

**3.3** Extract parsing regex constants  
- Files: `lib/features/toolbox/data/services/form_parsing_service.dart`  
- Instructions: move regex to named constants; add comments for expected formats.

**3.4** Add `orElse` to `firstWhere` in tests  
- Files: `test/features/toolbox/services/form_parsing_service_test.dart`  
- Instructions: avoid brittle test crashes when data changes.

**3.5** Externalize form definitions to JSON assets  
- Files: `assets/data/forms/` (create), `pubspec.yaml`, `lib/features/toolbox/data/services/form_seed_service.dart`  
- Instructions: move builtin form definitions to JSON for easier maintenance.

---

### Phase 4 (PR): Form Registry + Template Metadata Foundation
**Goal**: Single source of truth for all fields + forward-compatible template tracking.

**4.1** Add registry + alias tables (additive migration)  
- Files: `lib/core/database/database_service.dart`  
- Instructions: add `form_field_registry` + `field_semantic_aliases` with indices on `(form_id)`, `(semantic_name)`, `(is_auto_fillable)`.

**4.2** Add template metadata storage  
- Files: `lib/core/database/database_service.dart`, `lib/features/toolbox/data/models/inspector_form.dart`  
- Instructions: add `template_source`, `template_path`, `template_hash`, `template_version`, `template_field_count` (or new `form_templates` table).

**4.3** Extend field model for repeat + formatting  
- Files: `lib/features/toolbox/data/models/form_field_entry.dart`, `lib/features/toolbox/data/models/models.dart`  
- Instructions: add `pdf_field_type`, `value_type`, `repeat_group`, `repeat_index`, `value_format`, `default_value`, `calculation_formula`, `depends_on`.

**4.4** Registry datasource + service population  
- Files: `lib/features/toolbox/data/datasources/local/form_field_registry_datasource.dart`, `lib/features/toolbox/data/repositories/form_field_registry_repository.dart`, `lib/features/toolbox/data/services/field_registry_service.dart`, `lib/features/toolbox/data/services/form_seed_service.dart`  
- Instructions: backfill registry from builtins; seed aliases for known synonyms.

---

### Phase 5 (PR): Smart Auto-Fill + Carry-Forward Defaults
**Goal**: Eliminate repeated entry across IDR + other forms and respect user edits.

**5.1** AutoFill engine with provenance  
- Files: `lib/features/toolbox/data/services/auto_fill_engine.dart`, `lib/features/toolbox/presentation/screens/form_fill_screen.dart`  
- Instructions: return `{value, source, confidence}`; do not overwrite user-edited values unless empty or explicitly allowed.

**5.2** Inspector profile expansion + preferences service  
- Files: `lib/features/settings/presentation/screens/settings_screen.dart`, `lib/shared/services/preferences_service.dart`, `lib/main.dart`  
- Instructions: add inspector phone/cert/agency; use single preferences service to supply auto-fill.

**5.3** Carry-forward cache for non-project fields  
- Files: `lib/core/database/database_service.dart`, `lib/features/toolbox/data/services/field_registry_service.dart`, `lib/features/toolbox/presentation/providers/form_fill_provider.dart`  
- Instructions: add `form_field_cache` keyed by `(project_id, semantic_name)`; opt-in per field via registry; add “Use last value” toggle per form.

**5.4** UI auto-fill indicators + bulk apply  
- Files: `lib/features/toolbox/presentation/widgets/form_fill_widgets.dart`, `lib/features/toolbox/presentation/screens/form_fill_screen.dart`  
- Instructions: show chip with source; add “Auto-fill all” and “clear auto-filled only.”


**5.5** Auto-fill context hydration  
- Files: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`, `lib/features/toolbox/presentation/providers/inspector_form_provider.dart`  
- Instructions: ensure contractor/location/entry providers are loaded before auto-fill, or move auto-fill to repository queries that don’t depend on provider state.

---

### Phase 6 (PR): Calculation Engine + 0582B Density Automation
**Goal**: Derived fields update instantly, with safe formulas and rounding rules.

**6.1** Safe calculation service  
- Files: `lib/features/toolbox/data/services/form_calculation_service.dart`, `lib/features/toolbox/data/services/density_calculator_service.dart`  
- Instructions: whitelist operators or explicit handlers; protect divide-by-zero; store per-field precision.

**6.2** Registry-driven calculations  
- Files: `lib/features/toolbox/data/models/form_field_entry.dart`, `lib/features/toolbox/presentation/screens/form_fill_screen.dart`  
- Instructions: recompute on dependency changes; mark calculated fields read-only with override toggle.

**6.3** 0582B field definitions + tests  
- Files: `lib/features/toolbox/data/services/form_seed_service.dart`, `test/features/toolbox/services/`  
- Instructions: add wet/moisture/max density inputs and outputs; unit tests for rounding and edge cases.


**6.4** Align density field naming + parsing  
- Files: `lib/features/toolbox/data/services/form_parsing_service.dart`, `lib/features/toolbox/data/services/form_seed_service.dart`  
- Instructions: standardize `wet_density`, `moisture_pcf`/`moisture_percent`, `max_density`, `percent_compaction` across parsing keywords, registry, and PDF fields.

---

### Phase 7 (PR): Live Preview + Form Entry UX Cleanup
**Goal**: See the PDF while filling; reduce guesswork on 0582B + 1174.

**7.1** Split form fill screen into tabs  
- Files: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`, `lib/features/toolbox/presentation/widgets/form_fields_tab.dart`, `lib/features/toolbox/presentation/widgets/form_preview_tab.dart`, `lib/features/toolbox/presentation/widgets/form_fill_widgets.dart`  
- Instructions: fields tab + preview tab; on large screens allow split view.

**7.2** Preview byte caching + error states  
- Files: `lib/features/toolbox/data/services/form_pdf_service.dart`, `lib/features/toolbox/presentation/widgets/form_preview_tab.dart`  
- Instructions: cache preview bytes per form-state hash; show errors on missing template or render failure.

**7.3** Form header with test history  
- Files: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`, `lib/features/toolbox/presentation/widgets/form_fill_widgets.dart`  
- Instructions: show last tests for this form/project; allow “copy previous values” for non-project fields.


**7.4** Non-text field fill support  
- Files: `lib/features/toolbox/data/services/form_pdf_service.dart`, `lib/features/toolbox/data/models/form_field_entry.dart`  
- Instructions: add support for checkbox/radio/dropdown fields using `pdf_field_type`; map values safely.

---

### Phase 8 (PR): PDF Field Discovery + Mapping UI
**Goal**: Add new forms by importing a PDF and confirming mappings.

**8.1** Field discovery service (AcroForm scan)  
- Files: `lib/features/toolbox/data/services/field_discovery_service.dart`  
- Instructions: read field names/types; normalize names; match against aliases with confidence.

**8.2** Field mapping workflow  
- Files: `lib/features/toolbox/presentation/screens/form_import_screen.dart`, `lib/features/toolbox/presentation/screens/field_mapping_screen.dart`, `lib/core/router/app_router.dart`  
- Instructions: mapping UI with searchable semantics, category, autofill toggle/source, confidence chips, and bulk apply tools.

**8.3** Template storage + re-mapping detection  
- Files: `lib/features/toolbox/data/models/inspector_form.dart`, `lib/features/toolbox/data/services/field_registry_service.dart`  
- Instructions: store PDF bytes/path and hash; if template hash changes, prompt re-map.


**8.4** Imported template persistence validation  
- Files: `lib/features/toolbox/presentation/screens/form_import_screen.dart`, `lib/features/toolbox/data/services/field_registry_service.dart`  
- Instructions: validate file still exists or rehydrate from stored bytes; block mapping if template missing.

---

### Phase 9 (PR): Integration, QA, and Backward Compatibility
**Goal**: Ensure registry/preview doesn’t break older forms or data.

**9.1** Backward compat + fallback reading  
- Files: `lib/features/toolbox/data/services/form_pdf_service.dart`, `lib/features/toolbox/data/services/form_seed_service.dart`  
- Instructions: registry is primary; fallback to legacy `fieldDefinitions` if missing.

**9.2** E2E + widget tests for form flows  
- Files: `test/features/toolbox/`, `integration_test/`  
- Instructions: auto-fill + calculation + preview + export; regression coverage for 0582B and 1174.

**9.3** Developer docs + mapping checklist  
- Files: `docs/forms/` (create), `README.md`  
- Instructions: document add-form flow, mapping steps, and auto-fill resolution order.


**9.4** Sync registry + template metadata  
- Files: `lib/services/sync_service.dart`, `supabase/migrations/`, `lib/features/toolbox/data/datasources/remote/`  
- Instructions: add remote tables for registry/aliases/template metadata and include in sync pull/push flows.

---

### Phase 10 (PR): Entry + Report Dialog Extraction
**Goal**: Reduce mega screen size and isolate dialog logic.

**10.1** Extract entry_wizard dialogs  
- Files: `lib/features/entries/presentation/screens/entry_wizard_screen.dart`, `lib/features/entries/presentation/widgets/` (create)  
- Instructions: move dialogs into widgets, wire inputs via callbacks.

**10.2** Extract report dialogs + contractor sheet  
- Files: `lib/features/entries/presentation/screens/report_screen.dart`, `lib/features/entries/presentation/screens/report_widgets/` (create)  
- Instructions: centralize dialog layout and validation.

**10.3** Shared confirmation/permission dialogs  
- Files: `lib/shared/widgets/confirmation_dialog.dart`, `lib/shared/widgets/permission_dialog.dart`, update callers in `lib/features/entries/presentation/screens/report_screen.dart`, `lib/features/entries/presentation/screens/entry_wizard_screen.dart`, `lib/features/settings/presentation/screens/settings_screen.dart`, `lib/features/projects/presentation/screens/project_setup_screen.dart`  
- Instructions: use shared dialogs for consistent UX.

---

### Phase 11 (PR): Mega Screen Performance Pass
**Goal**: Address performance issues in large screens.

**11.1** Sliverize report + entry wizard  
- Files: `lib/features/entries/presentation/screens/report_screen.dart`, `lib/features/entries/presentation/screens/entry_wizard_screen.dart`  
- Instructions: switch to SliverList/SliverToBoxAdapter and avoid huge column trees.

**11.2** Home screen calendar optimization  
- Files: `lib/features/entries/presentation/screens/home_screen.dart`, `lib/features/entries/presentation/providers/daily_entry_provider.dart`  
- Instructions: precompute event map keyed by date.

**11.3** Photo thumbnail caching  
- Files: `lib/features/photos/presentation/widgets/photo_thumbnail.dart`, `lib/services/image_service.dart`  
- Instructions: reuse/cached ImageService and avoid new futures per build.

---

### Phase 12 (PR): Pagination Foundations (Data Layer)
**Goal**: Implement paging primitives.

**12.1** Add paging to local datasources  
- Files: `lib/shared/datasources/generic_local_datasource.dart`, `lib/shared/datasources/project_scoped_datasource.dart`

**12.2** Add paging to remote datasources  
- Files: `lib/shared/datasources/base_remote_datasource.dart`

**12.3** Add repository paging APIs  
- Files: `lib/shared/repositories/base_repository.dart`, `lib/features/*/data/repositories/`

---

### Phase 13 (PR): Pagination + Sync in Providers and UI
**Goal**: Use paging in UI and sync.

**13.1** Create `PagedListProvider<T>`  
- Files: `lib/shared/providers/` (create)

**13.2** Migrate heavy providers  
- Files: `lib/features/entries/presentation/providers/daily_entry_provider.dart`, `lib/features/quantities/presentation/providers/bid_item_provider.dart`, `lib/features/projects/presentation/providers/project_provider.dart`, `lib/features/photos/presentation/providers/photo_provider.dart`

**13.3** UI pagination  
- Files: `lib/features/entries/presentation/screens/entries_list_screen.dart`, `lib/features/projects/presentation/screens/project_list_screen.dart`, `lib/features/quantities/presentation/screens/quantities_screen.dart`, `lib/features/entries/presentation/screens/report_screen.dart`

**13.4** Sync chunking  
- Files: `lib/services/sync_service.dart`

---

### Phase 14 (PR): DRY/KISS Utilities + Shared UI Patterns
**Goal**: Reduce duplication while keeping KISS.

**14.1** Shared search bar + empty state widgets  
- Files: `lib/shared/widgets/` (add), update `lib/features/projects/presentation/screens/project_list_screen.dart`, `lib/features/quantities/presentation/screens/quantities_screen.dart`, `lib/features/entries/presentation/screens/entries_list_screen.dart`

**14.2** Validation + formatting helpers  
- Files: `lib/shared/utils/validators.dart` (create), `lib/shared/utils/formatters.dart` (create)

**14.3** Snackbar helper  
- Files: `lib/shared/utils/snackbar_helper.dart` (create)

**14.4** Shared controller helpers for entry/report/home  
- Files: `lib/features/entries/presentation/controllers/` (create), update entry/report/home screens

**14.5** Centralize SharedPreferences access  
- Files: `lib/shared/services/preferences_service.dart` (create), update settings/entries/projects/themes/toolbox

---

### Phase 15 (PR): Large File Decomposition (Non-entry Screens)
**Goal**: Reduce maintenance risk on large screens and services.

**15.1** Project setup + dashboard extraction  
- Files: `lib/features/projects/presentation/screens/project_setup_screen.dart`, `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`

**15.2** Quantities + settings extraction  
- Files: `lib/features/quantities/presentation/screens/quantities_screen.dart`, `lib/features/settings/presentation/screens/settings_screen.dart`

**15.3** Seed data and theme splitting  
- Files: `lib/core/database/seed_data_service.dart`, `assets/data/seed/` (create), `lib/core/theme/app_theme.dart`

**15.4** Testing keys split  
- Files: `lib/shared/testing_keys.dart` → `lib/shared/testing_keys/` (create folder)

**15.5** Database service schema split  
- Files: `lib/core/database/database_service.dart` → `lib/core/database/schema/` (create)

---

### Phase 16 (PR): Release Hardening + Infra Readiness
**Goal**: Prepare production configs and data integrity.

**16.1** Supabase migrations + RLS verification  
- Files: `supabase/migrations/supabase_schema_v3.sql`, `supabase/migrations/supabase_schema_v4_rls.sql`

**16.2** Config validation  
- Files: `lib/main.dart` or app init in `lib/core/`

**16.3** TODO triage  
- Files: `lib/features/sync/application/sync_orchestrator.dart`, `lib/features/photos/data/datasources/local/photo_local_datasource.dart`

---

## Suggested Execution Order (High Impact First)
1) Phases 1–3 (safety net + toolbox resilience)
2) Phases 4–9 (form streamlining core)
3) Phases 10–11 (dialog extraction + perf)
4) Phases 12–13 (pagination + sync)
5) Phases 14–16 (DRY + decomposition + release hardening)
