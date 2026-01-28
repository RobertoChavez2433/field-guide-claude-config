# Toolbox Implementation Plan (Consolidated Remediation, PR-Sized)

**Last Updated**: 2026-01-27

## Scope Summary (Do Not Drift)
This plan merges the original toolbox implementation scope with missed/incorrect items discovered during audit. It focuses only on:
1. Auto-load last selected project (reliability + tests).
2. Pay items natural sort (spec alignment if needed).
3. Contractor dialog dropdown clipping fix.
4. Toolbox feature set: Forms, Calculator, Gallery, To-Do's (including data sync, PDF mapping, auto-fill, and tests).
5. Dashboard toolbox card placement/order.
6. IDR attachment integration for form PDFs.

Anything outside this scope requires explicit approval.

---

## Baseline State (Verified)
- **Database version**: 13
- **Current tables**: 18 (includes toolbox tables)
- **Analyzer status**: previously 0 errors during toolbox phase work
- **Toolbox routes**: Forms, Calculator, Gallery, To-Do's exist

---

## Ground Rules (Non-Negotiable)
- No test breakages between PRs.
- Any UI key changes must ship with test updates in the same PR.
- Update `integration_test/patrol/REQUIRED_UI_KEYS.md` in the same PR as any key change.
- Schema changes require `DatabaseService` migration + `user_version` bump + `test/core/database/database_service_test.dart` updates in the same PR.
- Do not remove old keys until `rg` confirms no references remain.
- Locations feature stays available in Project Setup; only dashboard card placement is changed.

---

## Confirmed Code Touchpoints (Current State)
- Dashboard stat cards:
  - `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:246`
  - Current order: Entries, Toolbox, Pay Items, Contractors
  - Required order: **Entries, Pay Items, Contractors, Toolbox**
- Contractor dialog dropdown:
  - `_showAddContractorDialog()` in `lib/features/projects/presentation/screens/project_setup_screen.dart:604`
  - Missing `SingleChildScrollView`, `isExpanded`, `menuMaxHeight`
- Auto-load selection:
  - `ProjectSettingsProvider` in `lib/features/projects/presentation/providers/project_settings_provider.dart`
  - Auto-load flow in `lib/main.dart:287`
- Natural sort:
  - Utility in `lib/shared/utils/natural_sort.dart`
  - Tests in `test/shared/natural_sort_test.dart`
- Toolbox data tables:
  - SQLite: `lib/core/database/database_service.dart` (version 13)
  - Supabase: `supabase/migrations/20260126000000_toolbox_tables.sql`
- Sync registration:
  - `lib/services/sync_service.dart:_initDatasources()` (no toolbox registrations)
- Forms:
  - Seed data: `lib/features/toolbox/data/services/form_seed_service.dart`
  - PDF export: `lib/features/toolbox/data/services/form_pdf_service.dart`
  - Auto-fill: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`

---

## PR 1: Dashboard Order + Auto-Load Reliability

### Subphase 1.1: Dashboard card order
1. Reorder quick stats cards to:
   - Entries
   - Pay Items
   - Contractors
   - Toolbox
2. File: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:246`

### Subphase 1.2: Auto-load data fetch timing
1. Ensure `_loadProjectData()` is called after auto-selection completes.
2. Guard against double-loads.
3. File: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:20`

### Subphase 1.3: Archive clears auto-load selection
1. When a project is archived (`toggleActive`), clear stored last project ID if it matches.
2. File: `lib/features/projects/presentation/providers/project_provider.dart:258`

### Tests (PR 1)
- Widget:
  - Startup with auto-load enabled selects project and loads dashboard data.
  - Auto-load disabled leaves empty dashboard.
- Patrol:
  - Toggle auto-load on/off and verify persistence.
- Files:
  - `test/features/projects/presentation/...` (new)
  - `integration_test/patrol/e2e_tests/...` (new or update)

---

## PR 2: Contractor Dialog Dropdown Fix (Phase 3)

### Subphase 2.1: UI fixes
1. Wrap dialog content in `SingleChildScrollView`.
2. Add `isExpanded: true` and `menuMaxHeight: 300` to dropdown.
3. File: `lib/features/projects/presentation/screens/project_setup_screen.dart:604`

### Tests (PR 2)
- Patrol:
  - `integration_test/patrol/e2e_tests/project_setup_flow_test.dart`
  - `integration_test/patrol/e2e_tests/contractors_flow_test.dart`
  - `integration_test/patrol/e2e_tests/ui_button_coverage_test.dart`

---

## PR 3: PDF Field Mapping + Table Rows

### Subphase 3.1: Discover real PDF field names
1. Use `FormPdfService.generateDebugPdf()` to list actual field names.
2. File: `lib/features/toolbox/data/services/form_pdf_service.dart:261`

### Subphase 3.2: Update mappings
1. Update `pdfField` mappings in seed data to match real template fields.
2. File: `lib/features/toolbox/data/services/form_seed_service.dart:68`

### Subphase 3.3: Table row mapping
1. Replace generic `notes/results/test_results` mapping with row-by-row fill.
2. File: `lib/features/toolbox/data/services/form_pdf_service.dart:79`

### Tests (PR 3)
- Integration: export PDFs with known values.
- File: `test/features/toolbox/services/form_pdf_service_test.dart`

---

## PR 4: Form Auto-Fill Expansion

### Subphase 4.1: Expand auto-fill
1. Auto-fill contractor, location, inspector name (when empty).
2. File: `lib/features/toolbox/presentation/screens/form_fill_screen.dart:121`

### Tests (PR 4)
- Widget test for auto-fill behavior.
- File: `test/features/toolbox/presentation/screens/form_fill_screen_test.dart`

---

## PR 5: Sync Registration for Toolbox Tables

### Subphase 5.1: Remote datasources
1. Add remote datasources:
   - `lib/features/toolbox/data/datasources/remote/inspector_form_remote_datasource.dart`
   - `lib/features/toolbox/data/datasources/remote/form_response_remote_datasource.dart`
   - `lib/features/toolbox/data/datasources/remote/todo_item_remote_datasource.dart`
   - `lib/features/toolbox/data/datasources/remote/calculation_history_remote_datasource.dart`

### Subphase 5.2: SyncService registration
1. Register in `_initDatasources()`.
2. File: `lib/services/sync_service.dart:121`

### Subphase 5.3: Queue operations
1. Ensure create/update/delete operations queue in sync.
2. Files: toolbox repositories/providers under `lib/features/toolbox/...`

### Tests (PR 5)
- Add test to ensure toolbox tables are registered in sync list.
- File: `test/services/sync_service_test.dart` (new/extend)

---

## PR 6: IDR Attachment Integration ✅ COMPLETE

### Subphase 6.1: Attach exports to IDR ✅
1. Added `FormAttachment` class to hold form response + template pairs.
2. Extended `IdrPdfData` with `formAttachments` list.
3. Updated `_formatAttachments` to include form names with status labels.
4. Updated `_writeExportFiles` to generate and include form PDFs in folder export.
5. Trigger folder export when form attachments exist (even without photos).
6. Updated `report_screen.dart` to fetch entry-linked form responses.
7. Files:
   - `lib/features/pdf/services/pdf_service.dart` - FormAttachment, IdrPdfData extension, export logic
   - `lib/features/entries/presentation/screens/report_screen.dart` - Fetch form responses

### Tests (PR 6) ✅
- 8 unit tests for form attachment functionality in `test/services/pdf_service_test.dart`

---

## PR 7: Natural Sort Spec Alignment ✅ COMPLETE

### Subphase 7.1: Align decimal handling ✅
1. Verified implementation correctly uses 3-segment parsing: `["10", ".", "5"]`
2. Updated documentation to match actual behavior (was incorrectly documented as 2-segment)
3. This ensures pay item suffixes are compared numerically (201.01, 201.2, 201.10)
4. Fixed lint warning by converting library-level doc comments to regular comments
5. File: `lib/shared/utils/natural_sort.dart`

---

## PR 8: Missing Tests Bundle (Plan Compliance)

### Subphase 8.1: Datasource CRUD tests
- `test/features/toolbox/data/datasources/inspector_form_local_datasource_test.dart`
- `test/features/toolbox/data/datasources/todo_item_local_datasource_test.dart`

### Subphase 8.2: Forms list + hybrid input widget tests
- `test/features/toolbox/presentation/screens/forms_list_screen_test.dart`
- `test/features/toolbox/presentation/screens/form_fill_screen_test.dart` (if not already in PR 4)

### Subphase 8.3: Calculator UI flow widget test
- `test/features/toolbox/presentation/screens/calculator_screen_test.dart`

### Subphase 8.4: Gallery widget test
- `test/features/toolbox/presentation/screens/gallery_screen_test.dart`

### Subphase 8.5: Todos widget test
- `test/features/toolbox/presentation/screens/todos_screen_test.dart`

---

## Validation Checklist (After Each PR)
- [ ] Analyzer: 0 errors
- [ ] All new tests pass
- [ ] Existing tests pass
- [ ] Patrol flows relevant to PR pass
- [ ] No key regressions (REQUIRED_UI_KEYS updated if needed)
