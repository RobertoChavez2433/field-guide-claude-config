# Multi-Feature Implementation Plan (Detailed, Multi-PR)

**Last Updated**: 2026-01-26 (Review & Amendments Applied)

## Scope Summary (Do Not Drift)
This plan covers four features only:
1. Auto-load last selected project (with a settings toggle).
2. Pay items natural numeric sorting.
3. Contractor dialog dropdown clipping fix.
4. Toolbox (replace dashboard Locations stat card with Toolbox entry point, plus Forms/Calculator/Gallery/To-Do's feature set).

Anything outside the above scope requires explicit approval.

---

## Baseline State (Verified 2026-01-26)
- **Database version**: 12
- **Current tables**: 14 (projects, locations, contractors, equipment, bid_items, daily_entries, personnel_types, entry_personnel, entry_personnel_counts, entry_equipment, entry_contractors, entry_quantities, photos, sync_queue)
- **Analyzer status**: 0 errors
- **Test suite**: 363 passing

---

## Ground Rules (Non-Negotiable)
- No test breakages between PRs.
- Any UI key changes must ship with test updates in the same PR.
- Update `integration_test/patrol/REQUIRED_UI_KEYS.md` in the same PR as any key change.
- Schema changes require `DatabaseService` migration + `user_version` bump + `test/core/database/database_service_test.dart` updates in the same PR.
- Do not remove old keys until `rg` confirms no references remain.
- Locations feature stays available in Project Setup; only the dashboard card is replaced.

---

## Confirmed Code Touchpoints (Verified)
- Dashboard Locations card:
  - Rendered in `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:245-261`
  - Key: `TestingKeys.dashboardLocationsCard` in `lib/shared/testing_keys.dart:62`
  - Tests referencing it:
    - `integration_test/patrol/e2e_tests/navigation_flow_test.dart`
    - `integration_test/patrol/e2e_tests/ui_button_coverage_test.dart` (2 references)
    - `integration_test/patrol/helpers/patrol_test_helpers.dart`
- Contractor dialog dropdown:
  - `_showAddContractorDialog()` in `lib/features/projects/presentation/screens/project_setup_screen.dart:604`
  - Key at line 624: `TestingKeys.contractorTypeDropdown`
  - Tests reference dropdown key:
    - `integration_test/patrol/e2e_tests/project_setup_flow_test.dart:98`
    - `integration_test/patrol/e2e_tests/contractors_flow_test.dart:125`
    - `integration_test/patrol/e2e_tests/ui_button_coverage_test.dart:312`
- Pay item sorting:
  - Production: `lib/features/quantities/presentation/providers/bid_item_provider.dart:30` (currently lexicographic)
  - Tests: `test/helpers/test_sorting.dart:22-30` (currently numeric)
- DB schema tests:
  - `test/core/database/database_service_test.dart` asserts `user_version` and expected tables.

---

## Key Decisions (Finalized)

### 1. Auto-load Invalid Project: **Clear Selection**
When auto-load is enabled but stored project ID is invalid/deleted, stay on empty dashboard state. Safer - no unexpected behavior.

### 2. Natural Sort: **Case-Sensitive (ASCII Order)**
Alphanumeric items use ASCII order: uppercase letters sort before lowercase.
- Example: "1A" < "1B" < "1a" < "1b"
- Decimals: Split on dot (treat "10.5" as segments `10` then `.5` as string)
- Negatives: Treat `-` as text character

### 3. Form Template Storage: **assets/templates/forms/**
Copy MDOT templates from `Pre-development and brainstorming/Form Templates for export/` to `assets/templates/forms/`. Follows existing `idr_template.pdf` pattern.

Available templates:
- `1174R Concrete.pdf` - Inspector's Report of Concrete Placed
- `Moisture & Density Determiniation - Nuclear Method MDOT 0582B.pdf` - Density testing

---

## Phase 0: Planning Baseline + Definitions (PR 0)
### Subphase 0.1: Baseline test run and capture
1. Run baseline:
   - `flutter analyze`
   - `flutter test`
2. Run Patrol subset that touches dashboard and project setup:
   - `integration_test/patrol/e2e_tests/navigation_flow_test.dart`
   - `integration_test/patrol/e2e_tests/ui_button_coverage_test.dart`
   - `integration_test/patrol/e2e_tests/project_setup_flow_test.dart`
   - `integration_test/patrol/e2e_tests/contractors_flow_test.dart`
3. Record failures (if any) and note pre-existing test instability.
4. **Record current database version**: 12

### Subphase 0.2: Sorting rule definition (documented expectations)
1. Define exact sort behavior (convert to tests):
   - Natural numeric sort where digit sequences compare as integers.
   - **Text segments compare case-sensitively (ASCII order)** - uppercase before lowercase.
   - Decimal handling: treat "10.5" as segments `10` then `.5` (string).
   - Negative handling: treat `-` as text character (not numeric negative).
2. Convert expected behavior into unit tests before implementation.

---

## Phase 1: Auto-Load Last Project (PR 1)
### Subphase 1.1: Settings persistence provider
1. Create `lib/features/projects/presentation/providers/project_settings_provider.dart`.
2. Use `SharedPreferences` keys:
   - `last_selected_project_id`
   - `auto_load_last_project` (default true)
3. Expose:
   - `bool autoLoadEnabled`
   - `String? lastProjectId`
   - `Future<void> setAutoLoadEnabled(bool)`
   - `Future<void> setLastProjectId(String?)`
4. Ensure:
   - All writes await completion.
   - `notifyListeners()` called after mutation.

### Subphase 1.2: Project selection persistence
1. In `ProjectProvider`, hook project selection flow to persist last project ID.
2. Ensure selection does not trigger save if `autoLoadEnabled == false`.
3. When project is deleted or archived, clear stored ID if it matches the removed project.

### Subphase 1.3: App start auto-load workflow
1. In `main.dart`, register `ProjectSettingsProvider`.
2. Ensure order:
   - Load projects first (`ProjectProvider.loadProjects()`).
   - Then, if `autoLoadEnabled`, apply `selectProject(lastProjectId)`.
3. Guard against empty project list (should remain empty state).
4. **If stored ID is missing or invalid: Clear selection and stay empty.**

### Subphase 1.4: Dashboard auto-load data fetch
1. Ensure `_loadProjectData()` in `ProjectDashboardScreen` is called once after selection is set.
2. Avoid double loads:
   - If selection changes, handle one fetch per selection change.
3. Confirm no exceptions if selection is null.

### Subphase 1.5: Settings UI toggle
1. Add a toggle to `lib/features/settings/presentation/screens/settings_screen.dart`.
2. Add test key `TestingKeys.settingsAutoLoadProjectToggle`.
3. Toggle must persist across restarts.

### Tests (PR 1)
- Unit:
  - `ProjectSettingsProvider` defaults (auto-load = true).
  - `setLastProjectId` persistence and clearing.
  - Invalid project ID clears selection.
- Widget:
  - Simulate startup where `autoLoadEnabled=true` and a valid project exists -> dashboard shows project title.
  - Simulate startup where `autoLoadEnabled=false` -> empty dashboard state.
  - Simulate startup with invalid stored ID -> empty dashboard state.
- Patrol:
  - Add/extend a flow to toggle auto-load off/on.
  - Ensure empty state flow remains possible when toggle off.

---

## Phase 2: Pay Items Natural Sorting (PR 2)
### Subphase 2.1: Add natural sort utility
1. Create `lib/shared/utils/natural_sort.dart`.
2. Implement `naturalCompare(String a, String b)`.
3. Use:
   - RegExp split on digit vs non-digit segments.
   - Compare numeric segments as ints.
   - **Compare text segments case-sensitively (ASCII order)** - uppercase before lowercase.

### Subphase 2.2: Apply to provider and tests
1. Update `BidItemProvider.sortItems()` to use natural sort.
2. Update `test/helpers/test_sorting.dart` `sortBidItems()` to use the same logic.

### Subphase 2.3: Define and validate edge cases
1. Add unit tests to `test/shared/natural_sort_test.dart`:
   - `["1","2","10"]` -> `1,2,10`
   - `["1A","1B","1a","1b"]` -> `1A,1B,1a,1b` (uppercase first)
   - `["10.5","2.1","10.25"]` -> `10.25,10.5,2.1` (decimal as string segments)
   - `["-1","0","1"]` -> `-1,0,1` (dash as text)

### Tests (PR 2)
- Unit: `natural_sort.dart` with edge cases.
- Regression: `flutter test` to confirm no ordering mismatches.

---

## Phase 3: Contractor Dialog Dropdown Fix (PR 3)
### Subphase 3.1: UI fix in Project Setup
1. Wrap dialog content in `SingleChildScrollView`.
2. Add `isExpanded: true` and `menuMaxHeight: 300` to dropdown.
3. Ensure field focus and keyboard behavior remain intact.

### Subphase 3.2: Visual regression
1. Re-run relevant Patrol tests.
2. If any golden snapshots change (unlikely but possible), update them in the same PR.

### Tests (PR 3)
- Patrol:
  - `project_setup_flow_test.dart`
  - `contractors_flow_test.dart`
  - `ui_button_coverage_test.dart`
- Ensure dropdown is tappable and menu opens without clipping.

---

## Phase 4: Toolbox Foundation (PR 4)
### Subphase 4.1: SQLite schema (local)
1. Add tables to `lib/core/database/database_service.dart`:
   - `inspector_forms`
   - `form_responses`
   - `todo_items`
   - `calculation_history`
2. Add indexes for project/entry queries where appropriate.
3. **Bump `user_version` from 12 to 13**.
4. Update `test/core/database/database_service_test.dart`:
   - New table presence (18 tables total).
   - Column checks for each new table.
   - Updated user_version expectation (13).

### Subphase 4.2: Supabase schema
1. Add SQL migration: **`supabase/migrations/YYYYMMDDHHMMSS_toolbox_tables.sql`**
2. Use JSONB for structured fields.
3. Add indexes matching SQLite.
4. Enable RLS and add policies consistent with existing table patterns.

### Subphase 4.3: Sync registration
1. **Create `*RemoteDatasource` classes for each new table.**
2. **Register in `lib/services/sync_service.dart` `_initDatasources()` method (lines 77-133).**
3. Queue operations via `_syncService.queueOperation(tableName, recordId, operation)`.
4. Add a lightweight test that new tables are in sync table list.

### Subphase 4.4: Router + dashboard card
1. Add toolbox routes in `lib/core/router/app_router.dart`.
2. Replace dashboard Locations card with Toolbox card.
3. Remove LocationProvider usage from the quick stats row if no longer needed.
4. Add `TestingKeys.dashboardToolboxCard`.

### Subphase 4.5: Toolbox home UI
1. Create `ToolboxHomeScreen` with four cards:
   - Forms
   - Calculator
   - Gallery
   - To-Do's
2. Ensure navigation routes resolve (even if screens are placeholders).

### Subphase 4.6: Copy form templates to assets
1. Copy from `Pre-development and brainstorming/Form Templates for export/`:
   - `1174R Concrete.pdf` -> `assets/templates/forms/mdot_1174r_concrete.pdf`
   - `Moisture & Density...MDOT 0582B.pdf` -> `assets/templates/forms/mdot_0582b_density.pdf`
2. Update `pubspec.yaml` assets section.

### Tests (PR 4)
- Widget:
  - `ToolboxHomeScreen` renders and navigates to child routes.
- Patrol updates:
  - Replace Locations card taps with Toolbox card taps.
  - Update `integration_test/patrol/REQUIRED_UI_KEYS.md`.
  - Update `navigation_flow_test.dart` and `ui_button_coverage_test.dart`.
  - **Update `patrol_test_helpers.dart`**

---

## Phase 5: Forms Data Layer (PR 5)
### Subphase 5.1: Data models
1. Create models:
   - `InspectorForm`
   - `FormResponse`
2. Add JSON (de)serialization.
3. Include fields for template path, field definitions, parsing keywords, and `tableRows`.

### Subphase 5.2: Datasources + repositories
1. Add local datasources for forms and responses.
2. Add repository interfaces and concrete implementations.
3. Add providers to manage form lists and active responses.

### Subphase 5.3: Seed initial forms
1. Add MDOT form templates as built-in data loaded from `assets/templates/forms/`.
2. Ensure they load on first run or via seed migration.

### Tests (PR 5)
- Unit: model serialization.
- Unit: datasource CRUD (create/update/delete).
- Widget: forms list screen can display seeded forms.

---

## Phase 6: Forms UI + Hybrid Input (PR 6)
### Subphase 6.1: Forms selection UI
1. Add Forms screen to select forms per entry.
2. Create "open" FormResponse records when forms are selected.

### Subphase 6.2: Hybrid input UI
1. Add quick-entry text field + structured fields.
2. "Add Test" appends to `tableRows`.
3. Auto-fill fields from project/entry data.

### Tests (PR 6)
- Widget: hybrid input populates structured fields and creates table rows.
- Unit: UI logic for add-row and clearing input.

---

## Phase 7: Smart Parsing Engine (PR 7)
### Subphase 7.1: Parsing rules
1. Build keyword matching for 1174R + 0582B.
2. Support synonyms and common shorthand.
3. Map parsed tokens to fields and table rows.

### Subphase 7.2: Parser integration
1. Plug parsing into hybrid input UI.
2. Show parsed values for confirmation before saving.

### Tests (PR 7)
- Unit: parsing keywords and edge cases.
- Unit: calculated fields (e.g., compaction).

---

## Phase 8: PDF Export (PR 8)
### Subphase 8.1: PDF mapping
1. Map form fields to PDF template field names.
2. Use existing pdf service patterns from `lib/features/pdf/services/pdf_service.dart`.

### Subphase 8.2: Export storage
1. Export each form as a separate PDF file.
2. Add filenames to IDR attachments (same pattern as photos).

### Tests (PR 8)
- Integration: fill and export PDF with known values.
- Regression: existing PDF export tests continue to pass.

---

## Phase 9: Calculator (PR 9)
### Subphase 9.1: Domain logic
1. Implement HMA and Concrete calculators.
2. Store calculation history in new table.

### Subphase 9.2: UI integration
1. Add Calculator screen.
2. Add integration in quantities screen (calculate -> fill result).

### Tests (PR 9)
- Unit: calculator formula validation.
- Widget: calculator UI flow and result return.

---

## Phase 10: Gallery (PR 10)
### Subphase 10.1: Gallery screen
1. Reuse `PhotoProvider.loadPhotosForProject()` to aggregate all project photos.
2. Add filtering by date/entry in UI layer.

### Tests (PR 10)
- Widget: gallery grid loads photos.
- Patrol: navigation to gallery from toolbox.

---

## Phase 11: To-Do's (PR 11)
### Subphase 11.1: Data + UI
1. Implement `TodoItem` model, datasource, repository, provider.
2. Add Todos screen with add/edit/complete.

### Tests (PR 11)
- Unit: CRUD on todo items.
- Widget: completion toggles and sorting.

---

## Appendix A: Patrol Test Delta Map (Concrete Updates)
### Dashboard Locations Card -> Toolbox Card
- `integration_test/patrol/e2e_tests/navigation_flow_test.dart`
  - Replace tap target `TestingKeys.dashboardLocationsCard` with `TestingKeys.dashboardToolboxCard`.
  - Update test name and assertion to verify Toolbox home.
- `integration_test/patrol/e2e_tests/ui_button_coverage_test.dart`
  - Replace all uses of `TestingKeys.dashboardLocationsCard` with `TestingKeys.dashboardToolboxCard`.
  - Update log strings.
  - Add check for Toolbox screen visibility, then navigate back.
- **`integration_test/patrol/helpers/patrol_test_helpers.dart`**
  - Update `dashboardLocationsCard` -> `dashboardToolboxCard` reference.
- `integration_test/patrol/REQUIRED_UI_KEYS.md`
  - Add `dashboardToolboxCard`.
  - Remove `dashboardLocationsCard` only after `rg` shows no references.

### Contractor Dialog Fix
- `integration_test/patrol/e2e_tests/project_setup_flow_test.dart`
  - Ensure dropdown still opens; avoid timing assumptions.
- `integration_test/patrol/e2e_tests/contractors_flow_test.dart`
  - Ensure Prime selection still works with scrollable dialog.
- `integration_test/patrol/e2e_tests/ui_button_coverage_test.dart`
  - Verify dropdown tap still works after scrollable content.

### Auto-Load Project Toggle
- `integration_test/patrol/REQUIRED_UI_KEYS.md`
  - Add `settingsAutoLoadProjectToggle`.
- `integration_test/patrol/e2e_tests/settings_theme_test.dart` or a new test
  - Add a small flow to toggle auto-load off/on and verify persistence.

### Pay Item Sorting
- `integration_test/patrol/e2e_tests/quantities_flow_test.dart`
  - If order is asserted, update expected order to natural sort.

### Toolbox Navigation
- `integration_test/patrol/e2e_tests/ui_button_coverage_test.dart`
  - Add taps for Forms/Calculator/Gallery/To-Do's cards once screens exist.
- `integration_test/patrol/e2e_tests/navigation_flow_test.dart`
  - Add "dashboard -> toolbox -> forms" nav test (when implemented).

---

## Appendix B: Key Additions (Complete List)

### PR 1 Keys
- `TestingKeys.settingsAutoLoadProjectToggle`

### PR 4 Keys
- `TestingKeys.dashboardToolboxCard`
- `TestingKeys.toolboxHomeScreen`
- `TestingKeys.toolboxFormsCard`
- `TestingKeys.toolboxCalculatorCard`
- `TestingKeys.toolboxGalleryCard`
- `TestingKeys.toolboxTodosCard`

### Later PR Keys (define when UI exists)
- Form-related keys (PR 5-8)
- Calculator keys (PR 9)
- Gallery keys (PR 10)
- Todo keys (PR 11)

---

## Appendix C: Per-PR Checklist Template (with Context)
Use this at the top of each PR section to ensure completeness and test safety.

### Checklist
- **PR scope summary**: (1-3 sentences, concrete)
- **Files touched**: (list all files)
- **Keys added/changed**: (list keys; confirm updates to REQUIRED_UI_KEYS)
- **DB changes**: (tables, migrations, user_version updates)
- **Sync changes**: (table registration in SyncService._initDatasources())
- **Test updates**: (unit/widget/golden/patrol updates + files)
- **Manual verification**: (flows or devices to manually verify)
- **Risk notes**: (why this PR could break tests or behavior)

### Reasoning/Context
- Forces every PR to declare scope and risk explicitly, preventing silent UI key or schema changes from slipping in without tests.
- Ensures each PR documents the exact blast radius (files + tests), which reduces later debugging time.
- Captures manual verification expectations up front (important for UI and export flows).

---

## Appendix D: Risk Log (with Reasoning)
Track risks by phase with mitigation and test strategy. Update this as PRs progress.

### Risk 1: Dashboard Locations -> Toolbox replacement breaks Patrol flows
- **Why it matters**: Patrol tests explicitly tap `TestingKeys.dashboardLocationsCard` in multiple files.
- **Impact**: Immediate E2E failures; blocked CI.
- **Mitigation**: Add `dashboardToolboxCard`, update tests in same PR, update REQUIRED_UI_KEYS.
- **Validation**: Run Patrol subset in Phase 4.

### Risk 2: Auto-load project causes tests expecting empty dashboard to fail
- **Why it matters**: Auto-load changes the default state at launch.
- **Impact**: Widget tests and Patrol flows may fail if they assert "No Project Selected".
- **Mitigation**: Add toggle; tests that need empty state should disable auto-load.
- **Validation**: Add a Patrol toggle test and widget tests for both paths.

### Risk 3: Natural sort changes expected order in existing tests
- **Why it matters**: Tests already assume numeric ordering in helpers, but UI uses string compare.
- **Impact**: Behavior changes are correct but tests might still assert old order.
- **Mitigation**: Update `test/helpers/test_sorting.dart` and add explicit natural sort tests.
- **Validation**: Run unit tests and any quantities flows that assert order.

### Risk 4: Contractor dialog scroll wrapper changes layout/keys
- **Why it matters**: Changing dialog layout can affect hit-testing or overlays.
- **Impact**: Patrol tests that tap dropdown may fail.
- **Mitigation**: Keep existing keys; ensure dropdown still opens and closes reliably.
- **Validation**: Run contractor-related Patrol tests.

### Risk 5: New tables break database tests or migrations
- **Why it matters**: `database_service_test.dart` asserts tables and version.
- **Impact**: Unit test failures and runtime migrations if user_version not updated.
- **Mitigation**: Update tests and migrations in same PR; bump version from 12 to 13.
- **Validation**: Run `test/core/database/database_service_test.dart` and `flutter test`.

### Risk 6: Sync registration gaps lead to silent data loss
- **Why it matters**: Toolbox data must sync; missing registration silently drops records.
- **Impact**: Data consistency and future sync failures.
- **Mitigation**: Create RemoteDatasources and register in `SyncService._initDatasources()`.
- **Validation**: Add a lightweight sync registration test or a manual sync sanity check.

### Risk 7: PDF export integration breaks existing PDF tests
- **Why it matters**: PDF logic already exists; new forms might interfere.
- **Impact**: Regression in PDF tests or export flows.
- **Mitigation**: Keep PDF service changes isolated; add targeted integration test.
- **Validation**: Run PDF tests and manual export check.

### Risk 8: Patrol key drift across phases
- **Why it matters**: Patrol relies on stable keys in REQUIRED_UI_KEYS.
- **Impact**: Test flakiness or failures across PRs.
- **Mitigation**: Enforce key updates in the same PR and remove old keys only after `rg` shows no references.
- **Validation**: Run Patrol subset after each PR with key changes.

### Risk 9: patrol_test_helpers.dart not updated
- **Why it matters**: Helper file contains `dashboardLocationsCard` reference used by multiple tests.
- **Impact**: All tests using this helper will fail.
- **Mitigation**: Update helper in PR 4 alongside other test updates.
- **Validation**: Run full Patrol suite after PR 4.

### Risk 10: Form templates not in assets
- **Why it matters**: Templates must be bundled with app for PDF filling.
- **Impact**: Runtime asset load failure when filling forms.
- **Mitigation**: Copy templates to `assets/templates/forms/` in PR 4, update pubspec.yaml.
- **Validation**: Verify assets load in debug build before PR merge.
