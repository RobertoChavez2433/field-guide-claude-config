# Sync Verification Scenario Ground Truth Fixes — Dependency Analysis

## Scope

94 JavaScript scenario files + 1 helper file in `tools/debug-server/`.
**Zero Dart changes required** — all fixes are to JS test scenarios.

## Files Affected

### Direct Changes (95 files)

| Category | Files | Change Type |
|----------|-------|-------------|
| Helpers | `tools/debug-server/scenario-helpers.js` | Bug fix: contractor type |
| L2 S1-push | 16 files in `scenarios/L2/*-S1-push.js` | Route + key + logic rewrites |
| L2 S2-update-push | 16 files in `scenarios/L2/*-S2-update-push.js` | Route + key + logic rewrites |
| L2 S3-delete-push | 16 files in `scenarios/L2/*-S3-delete-push.js` | Route + key + logic rewrites |
| L2 S4-conflict | 17 files in `scenarios/L2/*-S4-conflict.js` | Minor field/column fixes |
| L2 S5-fresh-pull | 17 files in `scenarios/L2/*-S5-fresh-pull.js` | Minor field fixes |
| L3 X1-X10 | 10 files in `scenarios/L3/X*.js` | Route + key + logic rewrites |

### Dependent Files (0)

No Dart code depends on scenario file content.

### Test Files (self — scenarios ARE the tests)

The scenarios themselves are the test files being fixed.

## Change Classification

### Type 1: CLEAN scenarios (driver-only, no route/key issues) — ~50 files

These scenarios use only driver commands (`/driver/create-record`, `/driver/update-record`, etc.) and Supabase verifier calls. They need at most minor column/field corrections.

**Tables with all-clean S4+S5**: All 17 tables
**Tables with all-clean S1-S3**: entry-contractors, entry-equipment, entry-personnel-counts, entry-quantities, calculation-history (S2-S3 only), photos-S1, photos-S2

Fixes needed in clean scenarios:
- `type: 'general'` → `'prime'` in any contractor seed (via helpers fix)
- `form_type: 'inspector'` → `'inspection'` in form-responses S3/S4/S5
- `status: 'in_review'` → `activities: 'Local conflict edit'` in daily-entries-S4
- `conflict_log` table reference → verify if this table exists (used in all S4 scenarios)

### Type 2: ROUTE-ONLY fixes — ~8 scenarios

Scenarios where the route is wrong but keys and logic are correct:

| Scenario | Current Route | Correct Route |
|----------|--------------|---------------|
| projects-S1-push | `/projects/create` | `/project/new` |
| projects-S2-update-push | `/projects/${id}/edit` | `/project/${id}/edit` |
| projects-S3-delete-push | `/projects/${id}/settings` | `/project/${id}/edit` (+ rewrite delete flow) |
| daily-entries-S1-push | `/projects/${id}/entries/create` | `/entry/${projectId}/${date}` |
| daily-entries-S2-update-push | `/projects/${id}/entries/${id}/edit` | `/entry/${projectId}/${date}?entryId=${id}` |
| calculation-history-S1-push | `/projects/${id}/calculator` | `/calculator` |
| X1 (admin creates) | `/projects/create` | `/project/new` |

### Type 3: CONVERT-TO-DRIVER — ~20 scenarios

Scenarios where the feature has NO standalone route and must be rewritten to use driver commands:

| Table | Affected Scenarios | Reason |
|-------|-------------------|--------|
| locations | S1, S2, S3 | Locations embedded in entry editor / project setup |
| contractors | S1, S2, S3 | Contractors embedded in project setup |
| equipment | S1, S2, S3 | Equipment embedded in contractor editor |
| bid-items | S1, S2, S3 | Bid items embedded in project setup |
| personnel-types | S1, S2, S3 | Personnel types in project setup (list only at `/personnel-types/:projectId`) |
| inspector-forms | S1, S2, S3 | No form creation UI — forms are built-in templates |
| form-responses | S1, S3 | S1: form fill via `/form/:responseId` but requires response creation first; S3: no delete route |
| todo-items | S2, S3 | No route for individual todo operations |
| photos | S3 | No route for photo deletion |
| daily-entries | S3 | No direct delete route — delete is via report menu |

### Type 4: KEY-ONLY fixes — ~5 scenarios

Scenarios where the route is correct or fixable but widget keys are wrong:

| Key Used (wrong) | Correct Key | Where |
|-----------------|-------------|-------|
| `save_project_button` | `project_save_button` | projects-S1, S2, X1 |
| `save_entry_button` | `entry_wizard_save_draft` | daily-entries-S1, X2, X3, X5, X6 |
| `submit_entry_button` | `entry_wizard_submit` | daily-entries-S2 |
| `activities_field` | `entry_wizard_activities` or `report_activities_field` | X3 |
| `run_calculation_button` | `calculator_hma_calculate_button` (type-specific) | calc-history-S1 |
| `todo_title_field` | `todos_title_field` | todo-items-S1 |
| `save_todo_button` | `todos_save_button` | todo-items-S1 |

### Type 5: STRUCTURAL BUG fixes — 4 project-assignments + 2 L3 scenarios

**project-assignments S2-S5:**
- `callRpc('admin_assign_project_member', ...)` → RPC doesn't exist
- Fix: use `verifier.insertRecord('project_assignments', { id, project_id, user_id, company_id, assigned_by, assigned_at, updated_at })`
- Fix: query by `project_id + user_id` instead of using local `assignmentId`

**L3 X8, X9 (RLS isolation):**
- `verifier.authenticateAs()` and `verifier.resetAuth()` DO exist (lines 214, 265 of supabase-verifier.js)
- These scenarios are likely OK — need minor field/route fixes only

## Verified Ground Truth Reference

### Route Map (from app_router.dart)

| Feature | Route | Named Route | Params |
|---------|-------|-------------|--------|
| Project create | `/project/new` | `project-new` | — |
| Project edit | `/project/:projectId/edit` | `project-edit` | path: projectId; query: tab |
| Entry editor | `/entry/:projectId/:date` | `entry` | path: projectId, date; query: locationId, entryId |
| Report | `/report/:entryId` | `report` | path: entryId |
| Calculator | `/calculator` | `calculator` | — |
| Todos | `/todos` | `todos` | — |
| Forms list | `/forms` | `forms` | — |
| Form fill | `/form/:responseId` | `form-fill` | path: responseId |
| Personnel types | `/personnel-types/:projectId` | `personnel-types` | path: projectId |
| Sync dashboard | `/sync/dashboard` | `sync-dashboard` | — |

### Key Map (from lib/shared/testing_keys/*.dart)

**Projects** (ProjectsTestingKeys):
- `project_name_field`, `project_number_field`, `project_client_field`, `project_description_field`
- `project_save_button`, `project_cancel_button`, `project_create_button`
- `project_details_tab`, `project_locations_tab`, `project_contractors_tab`, `project_payitems_tab`
- `project_add_location_button`, `project_add_equipment_button`, `project_add_pay_item_button`
- Delete flow: `project_delete_first_dialog` → `project_delete_continue_button` → `project_delete_second_dialog` → `project_delete_text_field` → `project_delete_forever_button`

**Entries** (EntriesTestingKeys):
- `entry_wizard_save_draft`, `entry_wizard_submit`, `entry_wizard_close`, `entry_wizard_cancel`
- `entry_wizard_activities`, `entry_wizard_location_dropdown`, `entry_wizard_weather_dropdown`
- `entry_wizard_temp_low`, `entry_wizard_temp_high`
- `entry_delete_button_$entryId` (dynamic)
- Report: `report_delete_menu_item`, `report_delete_confirm_button`, `report_activities_field`

**Locations** (LocationsTestingKeys):
- `location_name_field`, `location_description_field`
- `location_dialog_cancel`, `location_dialog_add`

**Contractors** (ContractorsTestingKeys):
- `contractor_name_field`, `contractor_type_dropdown`
- `contractor_save_button`, `contractor_cancel_button`, `contractor_add_button`
- `contractor_delete_$id` (dynamic)

**Equipment** (LocationsTestingKeys — shared file):
- `equipment_name_field`, `equipment_description_field`
- `equipment_dialog_cancel`, `equipment_dialog_add`

**Bid Items / Pay Items** (QuantitiesTestingKeys):
- `pay_item_number_field`, `pay_item_description_field`, `pay_item_quantity_field`, `pay_item_unit_dropdown`
- `pay_item_dialog_save`, `pay_item_dialog_cancel`

**Todos** (ToolboxTestingKeys):
- `todos_title_field`, `todos_description_field`
- `todos_save_button`, `todos_add_button`
- `todo_checkbox_$todoId`, `todo_delete_button_$todoId` (dynamic)
- `todos_delete_confirm_button`, `todos_delete_cancel_button`

**Calculator** (ToolboxTestingKeys):
- `calculator_hma_calculate_button`, `calculator_concrete_calculate_button`, etc. (per type)
- `calculator_save_button`, `calculator_clear_button`
- `calculator_hma_area`, `calculator_hma_thickness`, `calculator_hma_density`

**Forms** (ToolboxTestingKeys):
- `form_start_button_$formId`, `form_response_delete_button_$responseId` (dynamic)
- `form_delete_confirm_button`, `form_delete_cancel_button`
- `mdot_hub_save_button`, `mdot_hub_pdf_button`

**Common** (CommonTestingKeys):
- `delete_confirm_button`, `confirm_dialog_button`, `cancel_dialog_button`

**Sync** (SyncTestingKeys):
- `sync_now_tile`, `sync_view_conflicts_tile`

### Column/Schema Gotchas

- `ContractorType` enum: only `prime` and `sub` (NOT `general`)
- `EntryStatus` enum: only `draft` and `submitted` (NOT `in_review`)
- `form_type`: canonical column is `form_type`; `form_id` is legacy alias; helpers use `'inspection'`
- `todo_items.priority`: INTEGER index (0=low, 1=normal, 2=high), not enum name
- `entry_contractors`: deterministic ID `ec-$entryId-$contractorId`
- `entry_personnel_counts`: column is `type_id` (NOT `personnel_type_id`); deterministic ID `epc-$entryId-$contractorId-$typeId`
- `bid_items`: SQLite column `bid_quantity`; Supabase column needs verification
- `photos.file_path`: nullable, stripped before push

### Driver Server Endpoints (from lib/core/driver/driver_server.dart)

Both exist:
- `POST /driver/inject-photo` — standard photo injection
- `POST /driver/inject-photo-direct` — direct photo injection (no UI)
- `POST /driver/create-record` — for junction tables
- `POST /driver/update-record` — update local record
- `POST /driver/remove-from-device` — remove project from device
- `POST /driver/navigate` — navigate to route
- `POST /driver/tap` — tap widget by key
- `POST /driver/text` — enter text by key
- `GET /driver/find` — find widget by key
- `GET /driver/local-record` — get local SQLite record
- `GET /driver/change-log` — get change log
- `POST /driver/sync` — trigger sync
- `GET /driver/sync-status` — get sync status
- `GET /driver/ready` — health check

### DeviceOrchestrator Methods (from device-orchestrator.js)

Wrapper methods:
- `device.navigate(route)` → `POST /driver/navigate`
- `device.tap(key)` → `POST /driver/tap`
- `device.enterText(key, text)` → `POST /driver/text`
- `device.find(key)` → `GET /driver/find`
- `device.triggerSync()` → `POST /driver/sync`
- `device.getSyncStatus()` → `GET /driver/sync-status`
- `device.getLocalRecord(table, id)` → `GET /driver/local-record`
- `device.getChangeLog(table)` → `GET /driver/change-log`
- `device.createRecord(table, record)` → `POST /driver/create-record`
- `device._request(method, path, body)` — raw HTTP (used for update-record, inject-photo etc.)

## Blast Radius

- **Direct**: 95 JS files (94 scenarios + 1 helper)
- **Dependent**: 0 (scenarios are leaf-node test files)
- **Tests**: N/A (scenarios ARE the tests)
- **Cleanup**: 0 (no dead code to remove)
