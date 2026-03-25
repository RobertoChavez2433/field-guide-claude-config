# Sync & Data Integrity Verification Spec

**Date:** 2026-03-25
**Status:** APPROVED
**Scope:** Full data integrity verification — sync, PDF export, UI additions, remote-delete notification

## Overview

### Purpose
Verify that the Construction Inspector App's sync system works end-to-end: all 17 synced tables create, push, pull, update, delete, and cascade correctly across two real devices. Additionally verify that exported PDFs (IDR + 0582B) contain the correct field values, and that inspectors are notified when projects are remotely deleted.

### Success Criteria
- [ ] All 17 synced tables verified: create via UI → push to Supabase → pull to second device
- [ ] All updatable tables verified: update via UI → push update → pull update
- [ ] All deletable tables verified: delete via UI → push deletion → pull deletion
- [ ] Project deletion cascades soft-deletes to all child tables
- [ ] Inspector notified when admin deletes a project they have locally
- [ ] Inspector's device removes project data after admin unassigns them (without deleting Supabase data)
- [ ] IDR PDF fields match UI-entered data (exact field-value matching)
- [ ] 0582B PDF fields match UI-entered data (exact field-value matching)
- [ ] Both PDFs land in same output folder
- [ ] Cleanup sweep finds zero orphaned records after flows complete

### What This Replaces
The existing 84 L2 scenarios (direct-injection approach via `/driver/create-record` and `seedAndSync`) are scrapped. They bypass the app's UI, skipping enrollment, FK validation, change_log entries, and sync state management — creating test-only bugs that don't exist in production.

## Architecture

### Two-Device Model
| Device | Role | Port | Purpose |
|--------|------|------|---------|
| S21+ (SM-G996U) | Admin | 4948 (via `adb forward`) | Creates projects, assignments, all field data. Primary device. |
| Windows desktop | Inspector | 4949 (localhost) | Pulls data, verifies cross-device sync. Secondary device. |

Both devices run the driver-enabled app (`--dart-define=DEBUG_SERVER=true`). The Node.js debug server orchestrates both simultaneously via HTTP.

### Test Runner
Same Node.js debug server infrastructure (`tools/debug-server/`). Scenarios rewritten to send UI commands (tap, text, scroll, wait) instead of direct SQLite injection.

### Test Data Strategy
Realistic construction data with unique prefixes for traceability:

| Entity | Example Value |
|--------|---------------|
| Project name | `VRF-Oakridge Water Main Replacement` |
| Project number | `VRF-2026-001` |
| Location | `VRF-Station 12+50 to 15+00` |
| Contractor (prime) | `VRF-Midwest Excavating LLC` |
| Contractor (sub) | `VRF-Delta Concrete Services` |
| Equipment | `VRF-CAT 320 Excavator` |
| Bid item | `VRF-6" DIP Water Main` |
| Personnel type | `VRF-Foreman` |
| Activities text | `VRF-Installed 200 LF of 6-inch DIP water main from Sta 12+50 to 14+50` |
| Todo | `VRF-Verify compaction test results before backfill` |

`VRF-` prefix = "Verification Flow" — makes all test data identifiable and sweepable.

## Workstream A: Sync Verification (6 Chained Flows)

### Flow Structure
One continuous end-to-end run. F1 creates the foundation, each subsequent flow builds on it. If F1 fails, everything stops (mirrors real usage).

```
Login both devices
  → F1: Project Setup (7 tables)
    → F2: Daily Entry (5 tables)
      → F3: Photos (1 table + storage)
        → F4: Forms (2 tables)
          → F5: Todos (1 table)
            → F6: Calculator (1 table)
              → Update Phase (all updatable tables)
                → PDF Export Phase
                  → Delete Phase (cascade + notification)
                    → Unassignment Phase (2nd project)
                      → Cleanup Sweep
```

### Step 0: Login Both Devices

**S21+ (Admin):**
1. `POST /driver/navigate {"path": "/login"}` (or check if already logged in via `/driver/ready`)
2. `POST /driver/wait {"key": "login_email_field"}`
3. `POST /driver/text {"key": "login_email_field", "text": "<admin_email>"}` (from `.env.test`)
4. `POST /driver/text {"key": "login_password_field", "text": "<admin_password>"}`
5. `POST /driver/tap {"key": "login_sign_in_button"}`
6. `POST /driver/wait {"key": "dashboard_project_title", "timeoutMs": 15000}`

**Windows (Inspector):** Same flow on port 4949 with inspector credentials.

### F1: Project Setup (7 tables)

**Tables:** `projects`, `project_assignments`, `locations`, `contractors`, `equipment`, `bid_items`, `personnel_types`

**Create on S21+ (Admin):**

1. **Project** — navigate to `/project/new` → fill `project_name_field` ("VRF-Oakridge Water Main Replacement"), `project_number_field` ("VRF-2026-001"), `project_client_field` ("VRF-City of Oakridge") → tap `project_save_button`

2. **Locations** — tap `project_locations_tab` → tap `project_add_location_button` → fill `location_name_field` ("VRF-Station 12+50 to 15+00"), `location_description_field` ("Main trench section") → tap `location_dialog_add`. Add a second: "VRF-Pump Station Site"

3. **Contractors** — tap `project_contractors_tab` → tap `contractor_add_button` → fill `contractor_name_field` ("VRF-Midwest Excavating LLC"), select `contractor_type_prime` → tap `contractor_save_button`. Add sub: "VRF-Delta Concrete Services" with `contractor_type_sub`

4. **Equipment** — expand prime contractor card → tap `project_add_equipment_button` → fill `equipment_name_field` ("VRF-CAT 320 Excavator"), `equipment_description_field` ("Tracked excavator") → tap `equipment_dialog_add`. Add: "VRF-Bomag BW211 Roller"

5. **Bid Items** — tap `project_payitems_tab` → tap `project_add_pay_item_button` → tap `pay_item_source_manual` → fill `pay_item_number_field` ("VRF-301.01"), `pay_item_description_field` ("VRF-6\" DIP Water Main"), `pay_item_quantity_field` ("2000"), select unit → tap `pay_item_dialog_save`

6. **Personnel Types** — navigate to Settings → tap `settings_personnel_types_tile` → tap `personnel_types_add_button` → fill `personnel_type_name_field` ("VRF-Foreman"), `personnel_type_short_code_field` ("VF") → tap `add_personnel_type_confirm`. Add: "VRF-Operator" ("VO"), "VRF-Laborer" ("VL")

7. **Project Assignment** — navigate back to project edit → tap `project_assignments_tab` → tap `assignment_tile(<inspector_user_id>)` to assign inspector

8. **Save** — tap `project_save_button`

**Sync + Verify Push:**
1. `POST S21+:/driver/sync {}` → poll `sync-status` until idle
2. For each table: `verifier.getRecord(table, id)` — confirm record exists in Supabase with correct field values
3. Verify `project_assignments` has `assigned_by` = admin user ID

**Pull to Windows (Inspector):**
1. `POST Windows:/driver/sync {}` → poll until idle (may need 2 rounds — first enrolls project from assignment, second pulls project-scoped data)
2. For each table: `GET Windows:/driver/local-record?table=X&id=Y` — confirm record exists locally on Windows
3. Verify `synced_projects` includes the new project ID

### F2: Daily Entry (5 tables)

**Tables:** `daily_entries`, `entry_contractors`, `entry_equipment`, `entry_personnel_counts`, `entry_quantities`

**Create on S21+ (Admin):**

1. **Daily Entry** — tap `add_entry_fab` → wait for `entry_wizard_scroll_view` → select location from `entry_wizard_location_dropdown` (tap `location_option_<locationId>`) → select weather `weather_condition_sunny` → fill `entry_wizard_temp_low` ("42"), `entry_wizard_temp_high` ("67") → fill `entry_wizard_activities` ("VRF-Installed 200 LF of 6-inch DIP water main from Sta 12+50 to 14+50")

2. **Entry Contractors** — tap `report_add_contractor_button` → tap `report_add_contractor_item_<contractorId>` for prime contractor → tap `report_save_contractor_button`. Repeat for sub.

3. **Entry Equipment** — tap `report_equipment_checkbox_<equipmentId>` for each piece of equipment (toggles `was_used`)

4. **Entry Personnel Counts** — tap `contractor_counter_plus_<typeId>` for each personnel type on each contractor. E.g., prime contractor: 2 foremen, 3 operators, 5 laborers.

5. **Entry Quantities** — tap `report_add_quantity_button` → select bid item from `bid_item_picker_<bidItemId>` → fill `quantity_amount_field` ("200"), `quantity_notes_field` ("VRF-Sta 12+50 to 14+50, 6\" DIP") → tap `quantity_dialog_save`

6. **Safety fields** — fill `entry_wizard_site_safety` ("VRF-Hard hats, safety vests required"), `entry_wizard_sesc_measures` ("VRF-Silt fence installed along south property line"), `entry_wizard_traffic_control` ("VRF-Flaggers on SR-47 at intersection"), `entry_wizard_visitors` ("VRF-City engineer on-site 10am-2pm")

7. **Save** — tap `entry_wizard_save_draft` (or `entry_wizard_submit`)

**Sync + Verify Push:**
1. Sync S21+ → verify all 5 tables in Supabase
2. Verify `entry_contractors` junction records, `entry_equipment.was_used` values, `entry_personnel_counts` with correct counts, `entry_quantities` amount

**Pull to Windows:**
1. Sync Windows → verify all 5 tables locally via `local-record`

### F3: Photos (1 table + storage bucket)

**Table:** `photos`

**Create on S21+ (Admin):**
1. Navigate to entry editor for the entry created in F2
2. `POST /driver/inject-photo-direct {"base64Data": "<valid-jpeg>", "filename": "VRF-trench-section.jpg", "entryId": "<entryId>", "projectId": "<projectId>"}`
3. Wait for photo thumbnail to appear

**Sync + Verify Push:**
1. Sync S21+ → verify `photos` record in Supabase
2. Verify file exists in Supabase Storage bucket `entry-photos` at expected path (`entries/<companyId>/<entryId>/VRF-trench-section.jpg`)

**Pull to Windows:**
1. Sync Windows → verify `photos` record locally with `remote_path` set

### F4: Forms (2 tables)

**Tables:** `inspector_forms`, `form_responses`

**Note:** `inspector_forms` are built-in system templates — they sync from the app's seed data. We verify `form_responses` created through UI, which exercises the form fill → sync path. The `inspector_forms` records are verified to exist in Supabase as a precondition.

**Create on S21+ (Admin):**
1. Navigate to entry editor → tap `report_add_form_button` (or `entry_wizard_add_form`)
2. Select 0582B from `form_selection_dialog` → tap `form_selection_item_<formId>`
3. Fill header fields via the MDOT Hub UI:
   - `hub_header_field_control_section_id` → "VRF-CS-2026-01"
   - `hub_header_field_job_number` → "VRF-2026-001"
   - `hub_header_field_route_street` → "VRF-SR-47"
   - `hub_header_field_construction_eng` → "VRF-J. Martinez"
   - `hub_header_field_asst_eng` → "VRF-K. Patel"
4. Add proctor data (proctor weights, setup fields)
5. Add test row data (station, depth, counts)
6. Save via form save button

**Sync + Verify Push:**
1. Sync S21+ → verify `form_responses` in Supabase with correct `parsed_header_data` and `parsed_response_data`
2. Verify `inspector_forms` record exists in Supabase (seeded, not user-created)

**Pull to Windows:**
1. Sync Windows → verify `form_responses` locally

### F5: Todos (1 table)

**Table:** `todo_items`

**Create on S21+ (Admin):**
1. Navigate to Toolbox → tap `toolbox_todos_card` → tap `todos_add_button`
2. Fill `todos_title_field` ("VRF-Verify compaction test results before backfill")
3. Fill `todos_description_field` ("VRF-Review 0582B results and confirm 95% compaction achieved")
4. Tap `todos_save_button`

**Sync + Verify Push + Pull to Windows:** Standard pattern.

### F6: Calculator (1 table)

**Table:** `calculation_history`

**Create on S21+ (Admin):**
1. Navigate to Toolbox → tap `toolbox_calculator_card`
2. Tap `calculator_hma_tab`
3. Fill `calculator_hma_area` ("5000"), `calculator_hma_thickness` ("3"), `calculator_hma_density` ("145")
4. Tap `calculator_hma_calculate_button`
5. Tap `calculator_save_button`

**Sync + Verify Push + Pull to Windows:** Standard pattern.

### Update Phase

After all 6 flows complete, update records across all updatable tables:

| Table | What to Update | UI Path |
|-------|---------------|---------|
| `projects` | Name → append " Phase 2" | Project edit → `project_name_field` |
| `locations` | Name → "VRF-Station 15+00 to 18+00" | Project edit → Locations tab → edit button (NEW UI) |
| `contractors` | Name → append " Inc." | Project edit → `contractor_edit_button_<id>` |
| `equipment` | Name → "VRF-CAT 330 Excavator" | Project edit → equipment edit button (NEW UI) |
| `bid_items` | Description → append " (modified)" | Project edit → `pay_item_edit_<id>` |
| `personnel_types` | Name → "VRF-Lead Foreman" | Settings → `personnel_type_edit_button_<id>` |
| `daily_entries` | Activities → append " Completed hydro test." | Entry editor → `report_activities_field` |
| `entry_quantities` | Amount → "250" | Entry editor → `report_quantity_edit_<id>` |
| `entry_personnel_counts` | Increment laborer count | Entry editor → `contractor_counter_plus_<typeId>` |
| `photos` | Description → "VRF-Updated trench photo" | Entry editor → photo thumbnail → `report_photo_description_field` |
| `form_responses` | Remarks → append " VRF-Retest required" | Form viewer → `mdot0582b_viewer_remarks_field` |
| `todo_items` | Title → append " - URGENT" | Todos → tap `todo_card_<id>` → edit |
| `entry_contractors` | (implicit — managed by adding/removing from entry) | — |
| `entry_equipment` | Toggle a different equipment item | `report_equipment_checkbox_<id>` |

**Tables NOT updated (no UI or not applicable):**
- `project_assignments` — toggle is create/delete, not update
- `calculation_history` — append-only, no update UI
- `inspector_forms` — system templates, read-only

**After all updates:** Sync S21+ → verify all updates in Supabase → Sync Windows → verify all updates pulled.

## Workstream B: PDF Export Verification

### Step 1: Export IDR

1. Navigate to entry editor for the daily entry
2. Tap `report_export_pdf_button`
3. Handle export filename dialog: `export_filename_field` → "VRF-IDR-Oakridge" → tap `export_filename_save_button`
4. Wait for export to complete
5. `adb pull` the PDF from device storage to local filesystem

### Step 2: Export 0582B

1. Navigate to entry editor → tap the form response thumbnail
2. Tap export/PDF button in form viewer
3. Handle export dialog → "VRF-0582B-Oakridge"
4. `adb pull` the PDF

### Step 3: Verify IDR Field Values

Read the exported PDF and verify exact field-value matches:

| PDF Field | Expected Value |
|-----------|---------------|
| `Text10` | Today's date formatted |
| `Text11` | `VRF-2026-001` |
| `Text15` | `VRF-Oakridge Water Main Replacement Phase 2` (post-update) |
| `Text12` | `Sunny` |
| `Text13` | `42 - 67` |
| `Namegdzf` | `VRF-Midwest Excavating LLC Inc.` (post-update) |
| `QntyForeman` | `2` |
| `QntyOperator` | `3` |
| `QntyLaborer` | `6` (post-update increment) |
| `sfdasd` | `VRF-Delta Concrete Services` |
| `ggggsssssssssss` | `VRF-CAT 330 Excavator` (post-update) |
| `Text3` | Contains `VRF-Installed 200 LF` + `Completed hydro test.` |
| `asfdasdfWER` | `VRF-Hard hats, safety vests required` |
| `HJTYJH` | `VRF-Silt fence installed along south property line` |
| `Text5#loioliol0` | `VRF-Flaggers on SR-47 at intersection` |
| `iol8ol` | `VRF-City engineer on-site 10am-2pm` |
| `8olyk,l` | Contains `VRF-301.01` and `250` (post-update) |
| `Text6` | Contains `VRF-trench-section.jpg` and `0582B` form reference |

### Step 4: Verify 0582B Field Values

| PDF Field | Expected Value |
|-----------|---------------|
| `control_section_id` | `VRF-CS-2026-01` |
| `job_number` | `VRF-2026-001` |
| `route_street` | `VRF-SR-47` |
| `construction_eng` | `VRF-J. Martinez` |
| `asst_eng` | `VRF-K. Patel` |
| `remarks` | Contains `VRF-Retest required` (post-update) |
| Test/proctor rows | Match entered values |

### Verification Method

The debug server reads the exported PDF using a PDF parsing library (or shells out to a CLI tool like `pdftk dump_data_fields` or `qpdf`). Each field name is looked up and its value compared to the expected string. Failures report: `MISMATCH: field "Text15" expected "VRF-Oakridge..." got "..."`.

## Workstream C: UI Additions

### C1: Location Edit Button

**Current state:** Locations in ProjectSetupScreen have add + delete only.
**Change:** Add an edit icon button on each location card. Tapping opens the same `LocationDialog` pre-filled with current name and description. Save updates the record in SQLite (fires change_log trigger).
**Testing key:** `location_edit_button_<locationId>`

### C2: Equipment Edit Button

**Current state:** Equipment shows as chips with delete only.
**Change:** Add an edit icon on each equipment chip/card. Tapping opens the same `EquipmentDialog` pre-filled. Save updates the record.
**Testing key:** `equipment_edit_button_<equipmentId>`

### C3: Calculation History Delete Button

**Current state:** Calculator history is append-only, no delete.
**Change:** Add a delete icon button on each history tile. Tapping shows confirmation dialog. Confirm soft-deletes the record (sets `deleted_at`).
**Testing keys:** `calculation_history_delete_button_<id>`, `calculation_history_delete_confirm`, `calculation_history_delete_cancel`

### C4: Remote-Delete Notification (wire existing widget)

**Current state:** `DeletionNotificationBanner` widget exists in `lib/features/sync/presentation/widgets/deletion_notification_banner.dart`. The sync engine already creates `deletion_notifications` rows when a remotely-deleted record is pulled. But the banner is not placed anywhere in the widget tree — inspectors see nothing.
**Change:** Place `DeletionNotificationBanner` in `ProjectListScreen` body (alongside existing `ProjectImportBanner`). Filter to `table_name = 'projects'` for project-specific messaging.
**Testing key:** Add `deletion_notification_banner` key to the widget. Existing `deletion_notifications` table schema already has `record_name`, `table_name`, `deleted_by_name`, `seen`.

## Delete Phase

### Step 1: Delete Project (Cascade Test)

**On S21+ (Admin):**
1. Navigate to project list → tap `project_remove_<id>` on the VRF project
2. Confirm deletion through the multi-step dialog (`project_delete_first_dialog` → `project_delete_continue_button` → `project_delete_second_dialog` → type project name in `project_delete_text_field` → `project_delete_forever_button`)
3. Sync S21+

**Verify cascade in Supabase:**
All child records must have `deleted_at IS NOT NULL`:
- `locations` (2 records)
- `contractors` (2 records)
- `equipment` (2 records)
- `bid_items` (1 record)
- `personnel_types` (3 records)
- `daily_entries` (1 record)
- `entry_contractors` (2 records)
- `entry_equipment` (2 records)
- `entry_personnel_counts` (N records)
- `entry_quantities` (1 record)
- `photos` (1 record)
- `form_responses` (1 record)
- `todo_items` (1 record)
- `calculation_history` (1 record)
- `project_assignments` — hard-deleted (row should not exist)

**Verify on Windows (Inspector):**
1. Sync Windows
2. Verify `deletion_notification_banner` appears with project name and admin's name
3. Verify project no longer appears in project list
4. Verify all child records removed from local SQLite

### Step 2: Unassignment Test (Second Project)

**Setup (earlier in the flow, after F1):**
1. Admin creates a second project: "VRF-Unassign Test Project" ("VRF-2026-002")
2. Admin assigns inspector
3. Both devices sync — inspector has the project locally

**Unassignment:**
1. Admin navigates to second project → Assignments tab → untoggle `assignment_tile_<inspectorUserId>`
2. Admin saves and syncs

**Verify:**
1. Supabase: project still exists, `project_assignments` row for inspector is hard-deleted
2. Windows syncs → project_assignment no longer returned by pull
3. Inspector's `synced_projects` no longer includes this project
4. Project data removed from inspector's local SQLite
5. Supabase: project and all its data remain intact (only the assignment was removed)

**Cleanup:**
1. Admin deletes the second project through UI (same cascade as Step 1)
2. Sync both devices

## Cleanup Sweep (Safety Net)

After all flows complete:
1. `sweepSynctestRecords()` — query all 17 tables in Supabase for records with `VRF-` prefix
2. Hard-delete any found (FK-ordered, children first)
3. Report: `CLEAN: 0 orphaned records` or `WARNING: deleted N orphaned records`
4. Both devices: verify no `VRF-` prefixed records remain locally

## Test Execution

### Prerequisites
- `.env.test` configured with admin/inspector credentials, Supabase URL, service role key, company ID, user IDs
- S21+ running driver APK, ADB forwarded (`adb forward tcp:4948 tcp:4948`)
- Windows running driver app on port 4949
- Both devices on network (Supabase reachable)

### Command
```bash
node tools/debug-server/run-tests.js --suite=integrity --devices=dual
```

### Expected Output
```
=== Sync & Data Integrity Verification ===

[LOGIN] Admin (S21+:4948).............. OK
[LOGIN] Inspector (Windows:4949)....... OK

[F1] Project Setup (7 tables)
  Create project...................... OK
  Create 2 locations.................. OK
  Create 2 contractors................ OK
  Create 2 equipment.................. OK
  Create 1 bid item................... OK
  Create 3 personnel types............ OK
  Assign inspector.................... OK
  Sync S21+........................... OK (pushed 18 records)
  Verify Supabase (7 tables).......... OK
  Sync Windows........................ OK (pulled 18 records)
  Verify Windows local (7 tables)..... OK

[F2] Daily Entry (5 tables).......... OK
[F3] Photos (1 table + storage)...... OK
[F4] Forms (2 tables)................ OK
[F5] Todos (1 table)................. OK
[F6] Calculator (1 table)............ OK

[UPDATE] All updatable tables
  Update 14 records................... OK
  Sync + verify push.................. OK
  Sync + verify pull.................. OK

[PDF] IDR Export
  Export.............................. OK
  Field verification (18 fields)...... OK (18/18 match)

[PDF] 0582B Export
  Export.............................. OK
  Field verification (16 fields)...... OK (16/16 match)

[DELETE] Project Cascade
  Delete project...................... OK
  Verify cascade (15 tables).......... OK
  Sync Windows........................ OK
  Notification banner visible......... OK
  Local cleanup verified.............. OK

[UNASSIGN] Second Project
  Setup + assign...................... OK
  Unassign + sync..................... OK
  Inspector data removed.............. OK
  Supabase data intact................ OK
  Cleanup second project.............. OK

[SWEEP] Cleanup
  Supabase orphans.................... 0
  Local orphans (S21+)................ 0
  Local orphans (Windows)............. 0

=== RESULT: ALL PASSED ===
```

## Rejected Alternatives

### Per-table isolated scenarios (84 scenarios)
Rejected because: overcomplicated, doesn't mirror real usage, required direct injection that bypassed the UI and created test-only bugs.

### S4 Conflict scenarios
Rejected because: RLS prevents cross-user writes. An inspector cannot write to another inspector's entries. Conflict testing is testing something that can't happen in production.

### Single-device with simulated server seeds
Rejected because: two real devices are available. No simulation needed.

## Dependencies

### Must be built before test flows run:
1. **C1:** Location edit button (for update-push verification)
2. **C2:** Equipment edit button (for update-push verification)
3. **C3:** Calculation history delete button (for delete-push verification)
4. **C4:** Wire `DeletionNotificationBanner` into `ProjectListScreen`

### Must exist:
- `.env.test` with all credentials
- Driver APK built and deployed to S21+
- Windows driver app built and runnable on port 4949
- ADB forwarding configured

## Key Files

| File | Purpose |
|------|---------|
| `tools/debug-server/run-tests.js` | CLI entry point (needs new `--suite=integrity` mode) |
| `tools/debug-server/test-runner.js` | Orchestration (needs dual-device support rewrite) |
| `tools/debug-server/device-orchestrator.js` | HTTP client for driver endpoints |
| `tools/debug-server/supabase-verifier.js` | Supabase verification + cleanup |
| `lib/core/driver/driver_server.dart` | All driver endpoints |
| `lib/shared/testing_keys/` | All widget keys |
| `lib/features/pdf/services/pdf_service.dart` | IDR PDF field mapping |
| `lib/features/forms/data/services/form_pdf_service.dart` | 0582B PDF field mapping |
| `lib/features/sync/presentation/widgets/deletion_notification_banner.dart` | Remote-delete notification (needs wiring) |
| `lib/features/projects/presentation/screens/project_list_screen.dart` | Where to place notification banner |

## PDF Field Mapping Reference

### IDR Fields
| PDF Field | Data Source | UI Key |
|-----------|-----------|--------|
| `Text10` | `DailyEntry.date` | `entry_date_field` |
| `Text11` | `Project.projectNumber` | `project_number_field` |
| `Text15` | `Project.name` | `project_name_field` |
| `Text12` | `DailyEntry.weather` | `entry_wizard_weather_dropdown` |
| `Text13` | `DailyEntry.tempLow` + `tempHigh` | `entry_wizard_temp_low/high` |
| `Namegdzf` | `Contractor[prime].name` | `contractor_name_field` |
| `QntyForeman/Operator/Laborer` | `EntryPersonnel[prime].counts` | `contractor_counter_plus_<typeId>` |
| `sfdasd` | `Contractor[sub1].name` | `contractor_name_field` |
| `ggggsssssssssss` | `Equipment[prime][0].name` | `equipment_name_field` |
| `Text3` | `DailyEntry.activities` | `entry_wizard_activities` |
| `asfdasdfWER` | `DailyEntry.siteSafety` | `entry_wizard_site_safety` |
| `HJTYJH` | `DailyEntry.sescMeasures` | `entry_wizard_sesc_measures` |
| `Text5#loioliol0` | `DailyEntry.trafficControl` | `entry_wizard_traffic_control` |
| `iol8ol` | `DailyEntry.visitors` | `entry_wizard_visitors` |
| `8olyk,l` | `EntryQuantity[]` formatted | `report_add_quantity_button` |
| `Text6` | Photos + form attachments | `report_add_photo_button` |

### 0582B Fields
| PDF Field | Data Source | UI Key |
|-----------|-----------|--------|
| `date` | `parsedHeaderData['date']` | `hub_header_field_date` |
| `control_section_id` | `parsedHeaderData['control_section_id']` | `hub_header_field_control_section_id` |
| `job_number` | `parsedHeaderData['job_number']` | `hub_header_field_job_number` |
| `route_street` | `parsedHeaderData['route_street']` | `hub_header_field_route_street` |
| `gauge_number` | `parsedHeaderData['gauge_number']` | `hub_header_field_gauge_number` |
| `inspector` | `parsedHeaderData['inspector']` | `hub_header_field_inspector` |
| `construction_eng` | `parsedHeaderData['construction_eng']` | `hub_header_field_construction_eng` |
| `asst_eng` | `parsedHeaderData['asst_eng']` | `hub_header_field_asst_eng` |
| `{n}Row{r}` (cols 1-16) | Test row data | `hub_test_field_<field>` |
| `{L}Row{r}` (cols A-J) | Proctor row data | `hub_proctor_setup_field_<field>` |
| `remarks` | `parsedResponseData['remarks']` | `mdot0582b_viewer_remarks_field` |

## Sync Table Coverage Matrix

| # | Table | Flow | Create | Update | Delete | Push | Pull | Notes |
|---|-------|------|--------|--------|--------|------|------|-------|
| 1 | `projects` | F1 | UI | UI | UI | yes | yes | Admin only for CRUD |
| 2 | `project_assignments` | F1 | UI (toggle) | N/A | UI (toggle) | yes | yes | Hard delete, admin only |
| 3 | `locations` | F1 | UI | UI (NEW) | UI | yes | yes | Edit button added (C1) |
| 4 | `contractors` | F1 | UI | UI | UI | yes | yes | |
| 5 | `equipment` | F1 | UI | UI (NEW) | UI | yes | yes | Edit button added (C2), viaContractor scope |
| 6 | `bid_items` | F1 | UI | UI | UI | yes | yes | |
| 7 | `personnel_types` | F1 | UI | UI | UI | yes | yes | Via Settings screen |
| 8 | `daily_entries` | F2 | UI | UI | UI | yes | yes | |
| 9 | `entry_contractors` | F2 | UI (implicit) | N/A | UI (implicit) | yes | yes | Junction table |
| 10 | `entry_equipment` | F2 | UI (toggle) | UI (toggle) | UI (toggle) | yes | yes | |
| 11 | `entry_personnel_counts` | F2 | UI (counter) | UI (counter) | UI (counter→0) | yes | yes | |
| 12 | `entry_quantities` | F2 | UI | UI | UI | yes | yes | |
| 13 | `photos` | F3 | inject-photo-direct | UI | UI | yes | yes | Native dialog blocks automation |
| 14 | `inspector_forms` | F4 | Seeded (built-in) | N/A | N/A | verified exists | verified exists | System templates |
| 15 | `form_responses` | F4 | UI | UI | UI | yes | yes | Via entry editor + form viewer |
| 16 | `todo_items` | F5 | UI | UI | UI | yes | yes | |
| 17 | `calculation_history` | F6 | UI | N/A (append-only) | UI (NEW) | yes | yes | Delete button added (C3) |
