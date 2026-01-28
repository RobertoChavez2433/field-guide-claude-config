# CODEX Production Readiness Plan (Verified + Organized)

**Created**: 2026-01-28  
**Purpose**: Validate older plans against the current codebase, flag what is complete vs missing, and provide a PR-sized, test-safe roadmap toward production readiness.

---

## Baseline LOC (Dart)
- Total (lib + test + integration_test): 66,512
- lib: 38,952
- test: 20,035
- integration_test: 7,525

## Estimated LOC After Plan Completion (Range)
- lib: –800 to –2,500 net lines (duplication reduced, some extraction overhead)
- test + integration_test: +1,000 to +3,000 (new/updated tests)
- Total: ~65,000 to ~69,000 lines

---

## Verification Matrix (Old Plans vs Current Codebase)

### A) Code Review Improvements Plan (2026-01-27)
**Status**: Mostly NOT implemented; one item complete.

- Extract Form Fill widgets: **Missing**. `lib/features/toolbox/presentation/screens/form_fill_screen.dart` still contains inline builders; no extracted widgets under `lib/features/toolbox/presentation/widgets/`.
- Extract entry_wizard dialogs: **Missing**. Dialogs still inline in `lib/features/entries/presentation/screens/entry_wizard_screen.dart`.
- Extract report dialogs: **Missing**. Dialogs still inline in `lib/features/entries/presentation/screens/report_screen.dart`.
- Service injection for parsing/PDF services: **Missing**. `FormParsingService` and `FormPdfService` still instantiated directly in `lib/features/toolbox/presentation/screens/form_fill_screen.dart`.
- Immutable list updates in `lib/features/toolbox/presentation/providers/inspector_form_provider.dart`: **Missing**. Direct list mutations remain in `lib/features/toolbox/presentation/providers/inspector_form_provider.dart`.
- Rename datasource tests: **Missing**. Files still exist as `test/features/toolbox/data/datasources/inspector_form_local_datasource_test.dart` and `test/features/toolbox/data/datasources/todo_item_local_datasource_test.dart`.
- Migrate deprecated barrel imports: **Complete**. No active imports found; only a commented line remains in `lib/presentation/providers/providers.dart`.
- Template load error handling: **Missing**. No `try/catch` around `rootBundle.load` in `lib/features/toolbox/data/services/form_pdf_service.dart`.
- FieldFormatter utility: **Missing**. No `lib/shared/utils/field_formatter.dart`.
- Parsing regex constants: **Missing**. Regex are inline in `lib/features/toolbox/data/services/form_parsing_service.dart`.
- Safe `firstWhere` in tests: **Missing**. `firstWhere` without `orElse` remains in `test/features/toolbox/services/form_parsing_service_test.dart`.
- Externalize form definitions to JSON: **Missing**. No `assets/data/forms/` and `FormSeedService` remains code-based.
- SyncNotifyingMixin: **Missing**. No shared mixin in `lib/shared/providers/`.
- DRY data-layer utilities: **Missing**. No shared helpers; repositories are still largely bespoke.
- Separate Photos vs Form Attachments in report: **Partial/Missing**. `lib/features/entries/presentation/screens/report_screen.dart` has a combined “Attachments” section that includes photo count.
- Supabase migrations: **Unverified**. Migration files exist in `supabase/migrations/`, but execution status is unknown.

### B) Session 1 Plan (Mega Screens + Performance)
**Status**: Not implemented (core items still present).

- Sliverize report/entry wizard/home: **Missing**. `SingleChildScrollView` remains in `lib/features/entries/presentation/screens/report_screen.dart`, `lib/features/entries/presentation/screens/entry_wizard_screen.dart`, and `lib/features/entries/presentation/screens/home_screen.dart`.
- Extract sections into widgets with localized rebuilds: **Mostly missing**. Screens remain monolithic. Some shared widgets exist (e.g., `lib/features/photos/presentation/widgets/photo_thumbnail.dart`, `lib/features/entries/presentation/widgets/contractor_editor_widget.dart`).
- Home calendar efficiency: **Missing**. `eventLoader` still filters `entryProvider.entries` in `lib/features/entries/presentation/screens/home_screen.dart`.
- Thumbnail caching: **Missing**. `PhotoThumbnail` creates `ImageService` and a new `FutureBuilder` per build in `lib/features/photos/presentation/widgets/photo_thumbnail.dart`.

### C) Session 2 Plan (Pagination Audit + Fix Strategy)
**Status**: Not implemented.

- Local datasource paging: **Missing**. `GenericLocalDatasource` and `ProjectScopedDatasource` lack `limit/offset` support (see `lib/shared/datasources/generic_local_datasource.dart`, `lib/shared/datasources/project_scoped_datasource.dart`).
- Remote datasource paging: **Missing**. `BaseRemoteDatasource` only supports `getAll`; no paging/range methods (see `lib/shared/datasources/base_remote_datasource.dart`).
- Repository paging APIs: **Missing**. No `getPage`/`getByProjectIdPage` variants in repositories.
- Paged providers: **Missing**. No `PagedListProvider` or equivalents in `lib/shared/providers/`.
- UI pagination: **Missing**. `lib/features/entries/presentation/screens/entries_list_screen.dart`, `lib/features/projects/presentation/screens/project_list_screen.dart`, `lib/features/quantities/presentation/screens/quantities_screen.dart`, and photo grids load full lists.
- Sync chunking: **Missing**. `lib/services/sync_service.dart` uses full `getAll` pulls and pushes.

### D) Session 3 Plan (DRY/KISS Refactor + Optimization)
**Status**: Partially implemented; major items missing.

- Shared widgets/dialogs: **Missing** for most screens. Shared `PhotoThumbnail` and `ContractorEditorWidget` exist, but no shared empty state/search widgets.
- Controller + validation consolidation: **Missing**. Validation and controller wiring still duplicated.
- Formatting + messaging helpers: **Missing**. Date/number formatting and Snackbar messages are duplicated across screens.
- Performance refactor: **Missing**. Mega screens still rebuild large trees.
- Test impact plan: **Partial**. Testing keys exist but are centralized in a single large file (`lib/shared/testing_keys.dart`).

---

## Effort Estimates (Rough, per PR Phase)
- Phase 1: M (test additions, Patrol updates)
- Phase 2: M (widget extraction + DI + provider fixes)
- Phase 3: M (utilities + assets + test tweaks)
- Phase 4: L (dialog extraction across mega screens)
- Phase 5: L (sliverization + perf fixes)
- Phase 6: M (data-layer paging primitives)
- Phase 7: L (provider/UI paging + sync chunking)
- Phase 8: M–L (DRY/KISS utilities + shared patterns)
- Phase 9: L (large file decomposition + data/theme split)
- Phase 10: S–M (migrations + config + TODO triage)

---

## Updated PR Roadmap (Comprehensive, Test-Safe)

### Phase 1 (PR): Safety Net + Baseline Verification
**Goal**: Reduce regression risk before large refactors.

**1.1** Add or expand Patrol flows for critical paths  
- Files: `integration_test/`, `test_driver/`, `patrol.yaml`  
- Reasoning: Ensures entry/report/project/toolbox flows survive refactors.

**1.2** Add focused widget tests for mega screens  
- Files: `test/features/entries/`, `test/features/projects/`, `test/features/quantities/`  
- Reasoning: Lightweight presence/assertion tests reduce risk without brittle snapshots.

---

### Phase 2 (PR): Toolbox Refactor Set A (Structure + DI + Provider Safety)
**Goal**: Address missing items from Code Review Plan PR1.

**2.1** Extract Form Fill widgets  
- Files: `lib/features/toolbox/presentation/screens/form_fill_screen.dart` + new widgets under `lib/features/toolbox/presentation/widgets/` (create)  
- Reasoning: Reduce file size and rebuild scope.

**2.2** Inject parsing/PDF services via Provider  
- Files: `lib/main.dart`, `lib/features/toolbox/presentation/screens/form_fill_screen.dart`  
- Reasoning: Better testability and lifecycle management.

**2.3** Fix mutable list updates  
- Files: `lib/features/toolbox/presentation/providers/inspector_form_provider.dart`  
- Reasoning: Avoid subtle state bugs with ChangeNotifier.

**2.4** Rename datasource tests  
- Files: `test/features/toolbox/data/datasources/inspector_form_local_datasource_test.dart`, `test/features/toolbox/data/datasources/todo_item_local_datasource_test.dart`  
- Reasoning: Align file names with actual test scope.

---

### Phase 3 (PR): Toolbox Refactor Set B (Resilience + Utilities)
**Goal**: Address missing items from Code Review Plan PR2.

**3.1** Add template load error handling  
- Files: `lib/features/toolbox/data/services/form_pdf_service.dart`  
- Reasoning: Prevent crashes when templates are missing.

**3.2** Add FieldFormatter utility and replace duplicates  
- Files: `lib/shared/utils/field_formatter.dart` (create), `lib/shared/utils/utils.dart`, `lib/features/toolbox/data/services/form_pdf_service.dart`, `lib/features/toolbox/presentation/screens/form_fill_screen.dart`  
- Reasoning: Centralize field formatting logic.

**3.3** Extract parsing regex constants  
- Files: `lib/features/toolbox/data/services/form_parsing_service.dart`  
- Reasoning: Improves readability and consistency.

**3.4** Add `orElse` to `firstWhere` in tests  
- Files: `test/features/toolbox/services/form_parsing_service_test.dart`  
- Reasoning: Avoid brittle tests.

**3.5** Externalize form definitions to JSON assets  
- Files: `assets/data/forms/` (create), `pubspec.yaml`, `lib/features/toolbox/data/services/form_seed_service.dart`  
- Reasoning: Data updates without code churn.

---

### Phase 4 (PR): Entry + Report Dialog Extraction
**Goal**: Reduce mega screen size and isolate dialog logic.

**4.1** Extract entry_wizard dialogs  
- Files: `lib/features/entries/presentation/screens/entry_wizard_screen.dart`, new widgets under `lib/features/entries/presentation/widgets/` (create)  
- Reasoning: Testable, reusable dialogs.

**4.2** Extract report dialogs + contractor sheet  
- Files: `lib/features/entries/presentation/screens/report_screen.dart`, new widgets under `lib/features/entries/presentation/screens/report_widgets/` (create)  
- Reasoning: Smaller file and clearer separation.

**4.3** Replace inline confirmation/permission dialogs with shared helpers  
- Files: `lib/shared/widgets/confirmation_dialog.dart`, `lib/shared/widgets/permission_dialog.dart`, update callers in `lib/features/entries/presentation/screens/report_screen.dart`, `lib/features/entries/presentation/screens/entry_wizard_screen.dart`, `lib/features/settings/presentation/screens/settings_screen.dart`, `lib/features/projects/presentation/screens/project_setup_screen.dart`  
- Reasoning: Consistent UX and fewer duplicated dialogs.

---

### Phase 5 (PR): Mega Screen Performance Pass
**Goal**: Address Session 1 performance issues.

**5.1** Sliverize report + entry wizard  
- Files: `lib/features/entries/presentation/screens/report_screen.dart`, `lib/features/entries/presentation/screens/entry_wizard_screen.dart`  
- Reasoning: Reduce layout cost and improve large list performance.

**5.2** Home screen calendar optimization  
- Files: `lib/features/entries/presentation/screens/home_screen.dart`, `lib/features/entries/presentation/providers/daily_entry_provider.dart`  
- Reasoning: Avoid O(n) filtering per day in `eventLoader`.

**5.3** Photo thumbnail caching  
- Files: `lib/features/photos/presentation/widgets/photo_thumbnail.dart`, `lib/services/image_service.dart`  
- Reasoning: Avoid re-creating thumbnail futures on rebuild.

---

### Phase 6 (PR): Pagination Foundations (Data Layer)
**Goal**: Implement Session 2 groundwork aligned to current architecture.

**6.1** Add paging to local datasources  
- Files: `lib/shared/datasources/generic_local_datasource.dart`, `lib/shared/datasources/project_scoped_datasource.dart`  
- Reasoning: Required for any large-table scaling.

**6.2** Add paging to remote datasources  
- Files: `lib/shared/datasources/base_remote_datasource.dart`  
- Reasoning: Enables Supabase range-based paging.

**6.3** Add repository paging APIs  
- Files: `lib/shared/repositories/base_repository.dart`, `lib/features/*/data/repositories/` (existing)  
- Reasoning: Keep existing APIs while enabling incremental migration.

---

### Phase 7 (PR): Pagination + Sync in Providers and UI
**Goal**: Use paging in UI and sync.

**7.1** Create `PagedListProvider<T>`  
- Files: `lib/shared/providers/` (create new file)  
- Reasoning: Standard paging pattern for heavy lists.

**7.2** Migrate heavy providers  
- Files: `lib/features/entries/presentation/providers/daily_entry_provider.dart`, `lib/features/quantities/presentation/providers/bid_item_provider.dart`, `lib/features/projects/presentation/providers/project_provider.dart`, `lib/features/photos/presentation/providers/photo_provider.dart`  
- Reasoning: Avoid loading entire datasets.

**7.3** UI pagination  
- Files: `lib/features/entries/presentation/screens/entries_list_screen.dart`, `lib/features/projects/presentation/screens/project_list_screen.dart`, `lib/features/quantities/presentation/screens/quantities_screen.dart`, `lib/features/entries/presentation/screens/report_screen.dart`  
- Reasoning: Infinite scroll without jank.

**7.4** Sync chunking  
- Files: `lib/services/sync_service.dart`  
- Reasoning: Replace full `getAll` pulls with paged or incremental sync.

---

### Phase 8 (PR): DRY/KISS Utilities + Shared UI Patterns
**Goal**: Reduce duplication while keeping KISS.

**8.1** Shared search bar and empty state widgets  
- Files: `lib/shared/widgets/` (add new widgets alongside existing), update `lib/features/projects/presentation/screens/project_list_screen.dart`, `lib/features/quantities/presentation/screens/quantities_screen.dart`, `lib/features/entries/presentation/screens/entries_list_screen.dart`  
- Reasoning: Reduce repeated UI patterns.

**8.2** Validation + formatting helpers  
- Files: `lib/shared/utils/validators.dart` (create), `lib/shared/utils/formatters.dart` (create)  
- Reasoning: Consistent input handling across screens.

**8.3** Snackbar helper  
- Files: `lib/shared/utils/snackbar_helper.dart` (create), update screens using repeated SnackBar blocks  
- Reasoning: DRY for user messages.

**8.4** Shared controller helpers for entry/report/home  
- Files: `lib/features/entries/presentation/controllers/` (create), update `lib/features/entries/presentation/screens/entry_wizard_screen.dart`, `lib/features/entries/presentation/screens/report_screen.dart`, `lib/features/entries/presentation/screens/home_screen.dart`  
- Reasoning: Reduce duplicated controller wiring and validation across mega screens.

**8.5** Consolidate date/number formatting to shared utils  
- Files: `lib/shared/utils/formatters.dart`, update usages in `lib/features/entries/presentation/screens/entries_list_screen.dart`, `lib/features/entries/presentation/screens/report_screen.dart`, `lib/features/entries/presentation/screens/home_screen.dart`, `lib/features/quantities/presentation/screens/quantities_screen.dart`, `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`, `lib/features/toolbox/data/services/form_pdf_service.dart`, `lib/features/toolbox/presentation/screens/form_fill_screen.dart`, `lib/features/pdf/services/pdf_service.dart`, `lib/features/pdf/services/photo_pdf_service.dart`  
- Reasoning: Consistent formats and single-source maintenance.

**8.6** Centralize SharedPreferences access  
- Files: `lib/shared/services/preferences_service.dart` (create), update `lib/features/entries/presentation/screens/entry_wizard_screen.dart`, `lib/features/entries/presentation/screens/report_screen.dart`, `lib/features/settings/presentation/screens/settings_screen.dart`, `lib/features/projects/presentation/providers/project_settings_provider.dart`, `lib/features/entries/presentation/providers/calendar_format_provider.dart`, `lib/features/settings/presentation/providers/theme_provider.dart`, `lib/features/toolbox/presentation/screens/form_fill_screen.dart`  
- Reasoning: Reduce duplication and make preferences testable/mocked.

---

### Phase 9 (PR): Large File Decomposition (Non-entry Screens)
**Goal**: Reduce maintenance risk on large screens and services.

**9.1** Project setup + dashboard extraction  
- Files: `lib/features/projects/presentation/screens/project_setup_screen.dart`, `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`  
- Reasoning: These are among the largest files.

**9.2** Quantities + settings extraction  
- Files: `lib/features/quantities/presentation/screens/quantities_screen.dart`, `lib/features/settings/presentation/screens/settings_screen.dart`  
- Reasoning: Modular widgets improve testability.

**9.3** Seed data and theme splitting  
- Files: `lib/core/database/seed_data_service.dart`, `assets/data/seed/` (create), `lib/core/theme/app_theme.dart`  
- Reasoning: Reduce massive single-file data/theme blocks.

**9.4** Testing keys split  
- Files: `lib/shared/testing_keys.dart` → `lib/shared/testing_keys/` (create folder)  
- Reasoning: Reduce merge conflicts and improve navigation.

**9.5** Database service schema split  
- Files: `lib/core/database/database_service.dart` → per-feature schema helpers under `lib/core/database/schema/` (create)  
- Reasoning: The DB schema file is large and high-churn; splitting reduces conflicts and improves reviewability.

---

### Phase 10 (PR): Release Hardening + Infra Readiness
**Goal**: Prepare production configs and data integrity.

**10.1** Supabase migrations + RLS verification  
- Files: `supabase/migrations/supabase_schema_v3.sql`, `supabase/migrations/supabase_schema_v4_rls.sql`  
- Reasoning: Security and schema integrity.

**10.2** Config validation  
- Files: `lib/main.dart` or app init in `lib/core/`  
- Reasoning: Fail fast on missing env vars.

**10.3** TODO triage  
- Files: `lib/features/sync/application/sync_orchestrator.dart`, `lib/features/photos/data/datasources/local/photo_local_datasource.dart`  
- Reasoning: Remove ambiguous release blockers.

---

## Additional Refactor Opportunities Observed (Not in Old Plans)
- Consider extracting PDF-related logic into smaller services: `lib/features/pdf/services/pdf_service.dart` and toolbox PDF generation in `lib/features/toolbox/data/services/form_pdf_service.dart` are both large and could be split by domain (IDR vs form export).
- Extract repeated UI blocks in `lib/features/projects/presentation/screens/project_setup_screen.dart` (location/contractor/equipment/pay item dialogs share patterns).
- Introduce a shared `ImageService` instance (or cache) instead of re-creating per build in `lib/features/photos/presentation/widgets/photo_thumbnail.dart`.

---

## Verification Checklist (Per PR)
- `flutter analyze`
- `flutter test`
- Run Patrol flows for touched screens
- Confirm TestingKeys remain stable

---

## Suggested Execution Order (High Impact First)
1) Phase 1 (Safety net)
2) Phases 2–3 (Toolbox stability + utilities)
3) Phase 4 (Dialogs extraction)
4) Phase 5 (Performance pass)
5) Phases 6–7 (Pagination + sync scaling)
6) Phases 8–10 (DRY, decomposition, release hardening)
