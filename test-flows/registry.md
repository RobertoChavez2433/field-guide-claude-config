# Unified Test Flow Registry

> Auto-updated by test agents after each run. Manual edits will be overwritten.

## Format
- **Driver Steps**: HTTP driver endpoint sequence (abbreviated)
- **Verify-Logs**: Debug server log categories to scan for errors
- **Status**: PASS / FAIL / UNTESTED / BLOCKED / MANUAL
- **Last Run**: ISO date of most recent execution
- **MANUAL**: Flow requires capabilities the HTTP driver lacks (OTP email, file picker, ADB offline toggle, camera hardware)

---

## Tier 0: Auth & Smoke (T01-T04)

> Prerequisite: app launched with driver entrypoint, credentials in `.claude/test-credentials.secret`.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| T01 | Login (Admin) | user_profiles | tap(login_email) → text(login_email,"admin@email") → tap(login_password) → text(login_password,"pass") → tap(login_submit) → wait(dashboard_screen) | auth | UNTESTED | - | First flow, no deps |
| T02 | Navigate All Tabs | N/A | tap(calendar_nav) → wait(calendar_screen) → tap(projects_nav) → wait(projects_screen) → tap(settings_nav) → wait(settings_screen) → tap(dashboard_nav) → wait(dashboard_screen) | nav | UNTESTED | - | Depends: T01 |
| T03 | Sign Out | N/A | tap(settings_nav) → tap(sign_out_tile) → tap(sign_out_confirm) → wait(login_screen) | auth | UNTESTED | - | Depends: T01 |
| T04 | Login (Inspector) | user_profiles | tap(login_email) → text(login_email,"inspector@email") → tap(login_password) → text(login_password,"pass") → tap(login_submit) → wait(dashboard_screen) | auth | UNTESTED | - | Separate session; verifies inspector role access |

## Tier 1: Project Setup — Admin (T05-T14)

> Admin creates a project with all sub-entities. Foundation for all subsequent tiers.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| T05 | Create Project | projects | tap(projects_nav) → tap(project_create_fab) → text(project_name,"E2E Test Project") → text(project_number,"E2E-001") → text(client_name,"E2E Client") → tap(project_save) → wait(project_list) | sync,db | UNTESTED | - | Depends: T01 |
| T06 | Add Location | locations | tap(project_card) → tap(project_edit) → tap(locations_tab) → tap(add_location) → text(location_name,"E2E Location A") → tap(location_dialog_add) → tap(project_save) | sync,db | UNTESTED | - | Depends: T05 |
| T07 | Add Second Location | locations | tap(project_card) → tap(project_edit) → tap(locations_tab) → tap(add_location) → text(location_name,"E2E Location B") → tap(location_dialog_add) → tap(project_save) | sync,db | UNTESTED | - | Depends: T05; needed for multi-location entry tests |
| T08 | Add Prime Contractor | contractors | tap(project_edit) → tap(contractors_tab) → tap(add_contractor) → text(contractor_name,"E2E Prime Co") → tap(contractor_type_prime) → tap(contractor_save) | sync,db | UNTESTED | - | Depends: T05 |
| T09 | Add Sub Contractor | contractors | tap(contractors_tab) → tap(add_contractor) → text(contractor_name,"E2E Sub Co") → tap(contractor_type_sub) → tap(contractor_save) | sync,db | UNTESTED | - | Depends: T05 |
| T10 | Add Equipment to Contractor | equipment | tap(contractor_card_prime) → tap(add_equipment) → text(equipment_name,"E2E Excavator") → tap(equipment_save) | sync,db | UNTESTED | - | Depends: T08 |
| T11 | Add Pay Item (Manual) | bid_items | tap(project_edit) → tap(payitems_tab) → tap(add_payitem) → tap(payitem_source_manual) → text(item_number,"E2E-100") → text(item_desc,"HMA Surface Course") → text(item_qty,"500") → text(item_unit,"TON") → tap(bid_item_save) | sync,db | UNTESTED | - | Depends: T05 |
| T12 | Add Second Pay Item | bid_items | tap(payitems_tab) → tap(add_payitem) → tap(payitem_source_manual) → text(item_number,"E2E-200") → text(item_desc,"Concrete Pavement") → text(item_qty,"1000") → text(item_unit,"SY") → tap(bid_item_save) | sync,db | UNTESTED | - | Depends: T05; needed for multi-quantity tests |
| T13 | Add Project Assignment | project_assignments | tap(project_edit) → tap(assignments_tab) → tap(add_assignment) → tap(user_select_inspector) → tap(assignment_save) | sync,db | UNTESTED | - | Depends: T05; assigns inspector user |
| T14 | Search Projects | N/A | tap(projects_nav) → tap(search_icon) → text(search_field,"E2E") → wait(project_card) → screenshot | nav | UNTESTED | - | Depends: T05 |

## Tier 2: Daily Entry Creation (T15-T23)

> Full entry creation with all sub-entities attached.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| T15 | Create Daily Entry (Draft) | daily_entries | tap(calendar_nav) → tap(add_entry_fab) → tap(location_dropdown) → tap(location_select_a) → tap(weather_dropdown) → tap(weather_sunny) → text(temp_low,"45") → text(temp_high,"72") → text(activities,"E2E test activities") → tap(save_draft) | sync,db | UNTESTED | - | Depends: T06 |
| T16 | Add Entry Safety Fields | daily_entries | tap(entry_card) → tap(report_safety_section) → wait(report_site_safety_field) → text(report_site_safety_field,"E2E safety notes") → text(report_sesc_field,"E2E SESC") → text(report_traffic_field,"E2E traffic") → text(report_visitors_field,"E2E visitor") | sync,db | UNTESTED | - | Depends: T15; tap safety card to enter edit mode first |
| T17 | Add Contractor to Entry | entry_contractors | tap(entry_card) → tap(contractors_section_add) → tap(select_contractor_prime) → tap(contractor_entry_save) | sync,db | UNTESTED | - | Depends: T08,T15 |
| T18 | Add Personnel Count | entry_personnel_counts | tap(personnel_add) → text(personnel_count,"5") → tap(personnel_save) | sync,db | UNTESTED | - | Depends: T17 |
| T19 | Add Equipment Usage | entry_equipment | tap(equipment_usage_add) → tap(select_equipment_excavator) → tap(equipment_usage_save) | sync,db | UNTESTED | - | Depends: T10,T15 |
| T20 | Log Quantity | entry_quantities | tap(quantities_section_add) → tap(select_bid_item) → text(quantity_value,"10.5") → text(quantity_notes,"E2E qty note") → tap(quantity_save) | sync,db | PASS | 2026-03-21 | Bid item autocomplete keys working |
| T21 | Use Quantity Calculator (HMA) | entry_quantities | tap(quantities_section_add) → tap(calculator_launch) → text(calc_width,"20") → text(calc_length,"100") → text(calc_depth,"4") → text(calc_density,"145") → tap(calculate_btn) → tap(use_result) | sync,db | MANUAL | - | Calculator not wired from entry screen; use standalone calculator (T38) instead |
| T22 | Attach Photo (inject-photo) | photos | tap(photos_section_add) → inject-photo(test.jpg) → text(photo_caption,"E2E test photo") → tap(photo_save) → wait(photo_thumbnail) | sync,photo | UNTESTED | - | Depends: T15 |
| T23 | Attach Second Photo | photos | tap(photos_section_add) → inject-photo(test2.jpg) → text(photo_caption,"E2E photo 2") → tap(photo_save) → wait(photo_thumbnail) | sync,photo | UNTESTED | - | Depends: T15; needed for gallery tests |

## Tier 3: Entry Lifecycle (T24-T30)

> Review, submit, edit, undo, delete entries. Multi-day operations.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| T24 | Edit Entry Inline (Location) | daily_entries | tap(entry_card) → tap(location_chip) → tap(location_select_b) → wait(location_updated) | sync,db | PASS | 2026-03-21 | Location dropdown keys working |
| T25 | Edit Entry Inline (Weather) | daily_entries | tap(entry_card) → tap(weather_chip) → tap(weather_cloudy) → wait(weather_updated) | sync,db | PASS | 2026-03-21 | Weather dropdown keys working |
| T26 | Create Second Entry (Day 2) | daily_entries | tap(calendar_nav) → tap(calendar_next_day) → tap(add_entry_fab) → tap(location_dropdown) → tap(location_select_a) → text(activities,"Day 2 activities") → tap(save_draft) | sync,db | UNTESTED | - | Depends: T06; creates entry on different date |
| T27 | Review Drafts → Mark Ready | daily_entries | tap(dashboard_nav) → tap(review_drafts_card) → tap(select_all) → tap(review_selected) → tap(mark_ready) → tap(mark_ready) → wait(review_summary) | sync,db | UNTESTED | - | Depends: T15,T26 |
| T28 | Submit Entries (Batch) | daily_entries | tap(submit_entries_btn) → tap(submit_confirm) → wait(dashboard_screen) | sync,db | UNTESTED | - | Depends: T27 |
| T29 | Undo Submission | daily_entries | tap(calendar_nav) → tap(entry_card) → tap(undo_submission_btn) → tap(undo_confirm) → wait(draft_status) | sync,db | UNTESTED | - | Depends: T28 |
| T30 | Delete Entry | daily_entries | tap(entry_card) → tap(overflow_menu) → tap(delete_entry) → tap(delete_confirm) → wait(calendar_screen) | sync,db | UNTESTED | - | Depends: T26; deletes Day 2 entry |

## Tier 4: Toolbox (T31-T40)

> Todos CRUD, forms lifecycle, calculator, gallery browsing.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| T31 | Create Todo | todo_items | tap(toolbox_nav) → tap(todos_tile) → tap(add_todo_fab) → text(todo_title,"E2E Todo Item") → text(todo_desc,"Test description") → tap(todo_priority_high) → tap(todo_save) | sync,db | UNTESTED | - | Depends: T05 |
| T32 | Edit Todo | todo_items | tap(todo_card) → text(todo_title,"E2E Todo Updated") → tap(todo_save) | sync,db | UNTESTED | - | Depends: T31 |
| T33 | Complete Todo | todo_items | tap(todo_checkbox) → wait(todo_completed) | sync,db | UNTESTED | - | Depends: T31 |
| T34 | Delete Todo | todo_items | tap(todo_delete_icon) → tap(delete_confirm) | sync,db | UNTESTED | - | Depends: T31 |
| T35 | Create Form Response (0582B) | form_responses | tap(toolbox_nav) → tap(forms_tile) → tap(new_0582b_btn) → wait(mdot_hub_screen) | sync,db | UNTESTED | - | Depends: T05 |
| T36 | Fill Form Fields | form_responses | text(form_structure_name,"E2E Structure") → text(form_test_density,"128.5") → text(form_test_moisture,"6.2") → tap(form_save) | sync,db | UNTESTED | - | Depends: T35 |
| T37 | Submit Form | form_responses | tap(form_submit_btn) → tap(submit_confirm) → wait(form_submitted_status) | sync,db | MANUAL | - | Section-by-section submit, no global submit button |
| T38 | Calculator — HMA | calculation_history | tap(toolbox_nav) → tap(calculator_tile) → tap(hma_tab) → text(calc_width,"20") → text(calc_length,"100") → text(calc_depth,"4") → text(calc_density,"145") → tap(calculate_btn) → wait(result_card) → screenshot | db | UNTESTED | - | Depends: T01 |
| T39 | Calculator — Concrete | calculation_history | tap(concrete_tab) → text(calc_width,"10") → text(calc_length,"50") → text(calc_depth,"6") → tap(calculate_btn) → wait(result_card) → screenshot | db | UNTESTED | - | Depends: T01 |
| T40 | Gallery — Browse & Filter | N/A | tap(toolbox_nav) → tap(gallery_tile) → wait(gallery_grid) → tap(filter_btn) → tap(filter_today) → wait(gallery_filtered) → tap(clear_filters) → screenshot | nav | UNTESTED | - | Depends: T22; needs photos to exist |

## Tier 5: PDF & Export (T41-T43)

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| T41 | Export Entry as PDF | N/A (local) | tap(entry_card) → tap(export_pdf_icon) → wait(pdf_actions_dialog) → tap(pdf_preview) → wait(pdf_ready) → screenshot | pdf | UNTESTED | - | Depends: T15 |
| T42 | Export Entry Folder (with Photos) | N/A (local) | tap(entry_card) → tap(export_pdf_icon) → wait(pdf_actions_dialog) → tap(pdf_save) → wait(folder_saved) → screenshot | pdf | UNTESTED | - | Depends: T22; entry must have photos |
| T43 | Form PDF Export | N/A (local) | tap(form_card) → tap(form_export_pdf) → wait(pdf_ready) → screenshot | pdf | UNTESTED | - | Depends: T37 |

## Tier 6: Settings & Profile (T44-T52)

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| T44 | Edit Profile | user_profiles | tap(settings_nav) → tap(edit_profile_tile) → text(display_name,"E2E Test Admin") → text(cert_number,"CERT-001") → text(phone,"5551234567") → text(initials,"ETA") → tap(save_profile) | sync,db | PASS | 2026-03-21 | Profile name field + save button accessible |
| T45 | Change Theme | N/A | tap(settings_nav) → tap(theme_toggle) → screenshot → tap(theme_toggle) → screenshot | ui | UNTESTED | - | Depends: T01; visual verification via screenshot |
| T46 | Edit Gauge Number | N/A (local pref) | tap(settings_nav) → tap(gauge_number_tile) → text(gauge_number_field,"12345") → tap(gauge_save) → screenshot | db | PASS | 2026-03-21 | Dialog keys accessible on fresh launch |
| T47 | Edit Initials | N/A (local pref) | tap(settings_nav) → tap(initials_tile) → text(initials_field,"TST") → tap(initials_save) → screenshot | db | PASS | 2026-03-21 | Dialog keys accessible on fresh launch |
| T48 | Toggle Auto-Load Last Project | N/A (local pref) | tap(settings_nav) → tap(auto_load_toggle) → screenshot | ui | UNTESTED | - | Depends: T01 |
| T49 | View Sync Dashboard | N/A | tap(settings_nav) → tap(sync_dashboard_tile) → wait(sync_dashboard_screen) → screenshot | sync | UNTESTED | - | Depends: T01 |
| T51 | Restore from Trash | varies | tap(settings_nav) → tap(trash_tile) → wait(trash_screen) → tap(restore_btn) → tap(restore_confirm) → screenshot | db | UNTESTED | - | Depends: T30 (needs a deleted entry) |
| T52 | Clear Cached Exports | N/A | tap(settings_nav) → tap(clear_cache_tile) → tap(clear_cache_confirm) → screenshot | db | UNTESTED | - | Depends: T01 |

## Tier 7: Admin Operations (T53-T58)

> Admin-only flows. Requires admin login (T01).

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| T53 | Open Admin Dashboard | N/A | tap(settings_nav) → tap(admin_dashboard_tile) → wait(admin_dashboard_screen) → screenshot | nav | UNTESTED | - | Depends: T01 (admin) |
| T54 | View Team Members | user_profiles | tap(team_member_card) → wait(member_detail_sheet) → screenshot | db | UNTESTED | - | Depends: T53 |
| T55 | Change Member Role | user_profiles | tap(team_member_card) → tap(role_dropdown) → tap(role_engineer) → tap(role_save_confirm) → screenshot | sync,db | UNTESTED | - | Depends: T53; changes inspector→engineer |
| T56 | Approve Join Request | company_join_requests | tap(pending_request_card) → tap(approve_role_inspector) → tap(approve_confirm) → screenshot | sync,auth | MANUAL | - | Requires a pending join request + second account |
| T57 | Reject Join Request | company_join_requests | tap(pending_request_card) → tap(reject_btn) → tap(reject_confirm) → screenshot | sync,auth | MANUAL | - | Requires a pending join request + second account |
| T58 | Archive Project | projects | tap(projects_nav) → tap(archive_btn) → wait(project_archived) → tap(archived_tab) → screenshot | sync,db | UNTESTED | - | Depends: T05 |

## Tier 8: Edit & Update Mutations (T59-T67)

> Modify existing entities and verify sync push.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| T59 | Edit Project Details | projects | tap(project_card) → tap(project_edit) → text(project_name,"E2E Updated Project") → tap(project_save) | sync,db | UNTESTED | - | Depends: T05 |
| T60 | Edit Contractor | contractors | tap(project_edit) → tap(contractors_tab) → tap(contractor_card) → text(contractor_name,"E2E Prime Updated") → tap(contractor_save) | sync,db | UNTESTED | - | Depends: T08 |
| T61 | Edit Pay Item | bid_items | tap(project_edit) → tap(payitems_tab) → tap(bid_item_edit) → text(item_desc,"HMA Surface Updated") → tap(bid_item_save) | sync,db | UNTESTED | - | Depends: T11 |
| T62 | Edit Entry Activities | daily_entries | tap(entry_card) → tap(report_activities_section) → wait(report_activities_field) → text(report_activities_field,"Updated activities text") → wait(auto_save) | sync,db | UNTESTED | - | Depends: T15; tap activities card to enter edit mode first |
| T63 | Edit Entry Temperature | daily_entries | tap(entry_card) → tap(report_temperature_section) → wait(report_temp_low_field) → text(report_temp_low_field,"50") → text(report_temp_high_field,"80") → wait(auto_save) | sync,db | UNTESTED | - | Depends: T15; tap temperature row to enter edit mode first |
| T64 | Edit Quantity Value | entry_quantities | tap(entry_card) → tap(quantity_row) → text(quantity_value,"25.0") → tap(quantity_save) | sync,db | UNTESTED | - | Depends: T20 |
| T65 | Unarchive Project | projects | tap(projects_nav) → tap(archived_tab) → tap(activate_btn) → wait(project_active) | sync,db | UNTESTED | - | Depends: T58 |
| T66 | Remove Assignment | project_assignments | tap(project_edit) → tap(assignments_tab) → tap(remove_assignment) → tap(remove_confirm) | sync,db | UNTESTED | - | Depends: T13 |
| T67 | Add Personnel Type | personnel_types | tap(entry_card) → tap(personnel_types_add) → text(personnel_type_name,"Laborer") → tap(type_save) | sync,db | MANUAL | - | Personnel types management not wired from entry screen; screen exists but not reachable |

## Tier 9: Delete Operations (T68-T77)

> Soft-delete entities and verify sync push of deletion.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| T68 | Delete Photo | photos | tap(entry_card) → tap(photo_thumbnail) → tap(photo_delete) → tap(delete_confirm) | sync,photo | UNTESTED | - | Depends: T23 (deletes second photo) |
| T69 | Delete Equipment | equipment | tap(project_edit) → tap(contractors_tab) → tap(contractor_card) → tap(equipment_delete) → tap(delete_confirm) | sync,db | UNTESTED | - | Depends: T10 |
| T70 | Delete Contractor | contractors | tap(project_edit) → tap(contractors_tab) → tap(contractor_delete_sub) → tap(delete_confirm) | sync,db | UNTESTED | - | Depends: T09 (deletes sub) |
| T71 | Delete Location | locations | tap(project_edit) → tap(locations_tab) → tap(location_delete_b) → tap(delete_confirm) | sync,db | UNTESTED | - | Depends: T07 (deletes Location B) |
| T72 | Delete Pay Item | bid_items | tap(project_edit) → tap(payitems_tab) → tap(bid_item_delete) → tap(delete_confirm) | sync,db | UNTESTED | - | Depends: T12 (deletes second pay item) |
| T73 | Delete Todo | todo_items | tap(toolbox_nav) → tap(todos_tile) → tap(todo_delete) → tap(delete_confirm) | sync,db | UNTESTED | - | Depends: T31 |
| T74 | Delete Form Response | form_responses | tap(toolbox_nav) → tap(forms_tile) → tap(form_card) → tap(form_delete) → tap(delete_confirm) | sync,db | UNTESTED | - | Depends: T35 |
| T75 | Remove Project from Device | projects (local) | tap(projects_nav) → long_press(project_card) → tap(delete_from_device) → wait(project_removed) | db | UNTESTED | - | Depends: T05; device-only removal |
| T76 | Delete Remote Project (Admin) | projects | tap(projects_nav) → tap(company_tab) → long_press(remote_project_card) → tap(delete_remote) → tap(delete_confirm) | sync,db | MANUAL | - | Requires remote-only project visible to admin |
| T77 | Permanently Delete from Trash | varies | tap(settings_nav) → tap(trash_tile) → tap(delete_forever_btn) → tap(delete_confirm) → screenshot | db | UNTESTED | - | Depends: T68 or T30 (needs trashed item) |

## Sync Verification — Claude-Driven (S01-S10)

> Dual-device sync verification. Claude drives admin (port 4948) and inspector (port 4949), verifies data via Supabase REST API.
> Reference: `.claude/test-flows/sync-verification-guide.md`

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| S01 | Project Setup | projects, project_assignments, locations, contractors, equipment, bid_items, personnel_types | Admin: create project + sub-entities + assignment → sync → Inspector: sync x2 → verify locally | sync,db | UNTESTED | - | Creates 2 projects (main + unassign test); captures all entity IDs |
| S02 | Daily Entry | daily_entries, entry_contractors, entry_equipment, entry_personnel_counts, entry_quantities | Admin: create full entry → sync → Inspector: sync x2 → verify locally | sync,db | UNTESTED | - | Depends: S01 |
| S03 | Photos | photos | Admin: inject-photo-direct → sync → Inspector: sync x2 → verify locally | sync,photo | UNTESTED | - | Depends: S02; COMPACTION PAUSE after |
| S04 | Forms | inspector_forms, form_responses, form_exports | Admin: create 0582B response → export PDF → sync → Inspector: sync x2 → verify locally; verify inspector_forms builtins exist via REST | sync,db | UNTESTED | - | Depends: S02 |
| S05 | Todos | todo_items | Admin: create todo → sync → Inspector: sync x2 → verify locally | sync,db | UNTESTED | - | Depends: S01 |
| S06 | Calculator | calculation_history | Admin: HMA calculation → save → sync → Inspector: sync x2 → verify locally | sync,db | UNTESTED | - | Depends: S01; COMPACTION PAUSE after |
| S07 | Update All | All updatable tables, documents, form_exports, entry_exports | Admin: update project, location, contractor, equipment, bid_item, personnel_type, entry fields, photo, form, todo, calculator, document notes → sync → Inspector: verify | sync,db | UNTESTED | - | Depends: S01-S06 |
| S08 | PDF Export | entry_exports | Admin: export IDR + 0582B PDFs → verify entry_exports row with remote_path → ADB pull → pdftk verify fields | pdf | UNTESTED | - | Depends: S07; ADB timeout → FAIL S08, continue to S09 |
| S09 | Delete Cascade | All child tables of project 1 | Admin: two-step delete → sync → Supabase: verify 17 child tables soft-deleted → Inspector: deletion banner → verify gone | sync,db | PASS | 2026-03-27 | RPC + cascade trigger + RLS fix + orphan cleaner all working. Inspector pulls 21 tombstones, shows deletion banner, project auto-evicted on 2nd sync. |
| S10 | Unassignment + Cleanup | project_assignments, projects | Admin: unassign inspector from project 2 → sync → Inspector: verify project 2 removed → Admin: delete project 2 → post-run VRF sweep (20 synced tables) | sync,db | FAIL | 2026-03-27 | BUG-S01-2: Assignment toggle doesn't persist soft-delete to SQLite/change_log. Pre-existing bug. |
| S11 | Documents | documents | Admin: inject-document-direct → sync → Supabase: verify documents row + storage file → Inspector: sync x2 → verify document visible | sync,db | UNTESTED | - | Depends: S02; bucket: entry-documents |

## Tier 11: Role & Permission Verification (T85-T91)

> Switch to inspector role and verify restricted actions are blocked.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| T85 | Inspector: No Create Project FAB | N/A | login_as(inspector) → tap(projects_nav) → screenshot → assert_not_visible(project_create_fab) | auth | UNTESTED | - | Depends: T04; FAB must be absent |
| T86 | Inspector: No Admin Dashboard | N/A | tap(settings_nav) → screenshot → assert_not_visible(admin_dashboard_tile) | auth | UNTESTED | - | Depends: T04 |
| T87 | Inspector: Can Create Entry | daily_entries | tap(calendar_nav) → tap(add_entry_fab) → tap(location_dropdown) → tap(location_select_a) → text(activities,"Inspector entry") → tap(save_draft) | sync,db,auth | UNTESTED | - | Depends: T04,T06 |
| T88 | Inspector: Can Create Todo | todo_items | tap(toolbox_nav) → tap(todos_tile) → tap(add_todo_fab) → text(todo_title,"Inspector Todo") → tap(todo_save) | sync,db | UNTESTED | - | Depends: T04 |
| T89 | Inspector: Cannot Archive Project | N/A | tap(projects_nav) → tap(project_card) → screenshot → assert_not_visible(archive_btn) | auth | UNTESTED | - | Depends: T04 |
| T90 | Inspector: Project Edit Read-Only | N/A | tap(project_card) → tap(project_edit) → screenshot → assert_not_visible(project_save_btn) | auth | UNTESTED | - | Depends: T04; fields should be read-only |
| T91 | Inspector: Route Guard /project/new | N/A | POST /driver/navigate {"path":"/project/new"} → wait(projects_screen) → screenshot | auth,nav | UNTESTED | - | Depends: T04; should redirect to /projects; uses /driver/navigate endpoint |

## Tier 12: Navigation & Dashboard (T92-T96)

> Verify dashboard cards, quick stats links, and deep navigation paths.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| T92 | Dashboard → Entries List | N/A | tap(dashboard_nav) → tap(entries_stat_card) → wait(entries_list_screen) → screenshot | nav | UNTESTED | - | Depends: T15 |
| T93 | Dashboard → Quantities | N/A | tap(dashboard_nav) → tap(payitems_stat_card) → wait(quantities_screen) → screenshot | nav | UNTESTED | - | Depends: T11 |
| T94 | Dashboard → Toolbox | N/A | tap(dashboard_nav) → tap(toolbox_stat_card) → wait(toolbox_screen) → screenshot | nav | UNTESTED | - | Depends: T01 |
| T95 | Quantities → Bid Item Detail | N/A | tap(quantities_screen) → tap(bid_item_card) → wait(bid_item_detail_sheet) → screenshot | nav | PASS | 2026-03-21 | BUG-17 fix verified — 2 pay items after re-login |
| T96 | Gallery → Photo Viewer | N/A | tap(toolbox_nav) → tap(gallery_tile) → tap(photo_thumbnail) → wait(photo_viewer) → screenshot | nav | PASS | 2026-03-21 | BUG-17 fix verified — 2 photos in gallery after re-login |

## Manual-Only Flows (M01-M08)

> These flows require capabilities the HTTP driver cannot provide. Run manually on device.

| ID | Flow | Why Manual | Verify | Status | Last Run | Notes |
|----|------|-----------|--------|--------|----------|-------|
| M01 | Register New Account | Requires OTP email verification | Check user_profiles in Supabase | MANUAL | - | Full: register → OTP → profile-setup → company-setup |
| M02 | Forgot Password → Reset | Requires OTP email delivery | Login with new password | MANUAL | - | Full: forgot-password → OTP → update-password |
| M03 | Import Pay Items from PDF | Requires FilePicker + OCR pipeline | Check bid_items count in project | MANUAL | - | Full: project edit → pay items → PDF import → preview → import |
| M04 | Import M&P from PDF | Requires FilePicker | Check bid_items enrichment | MANUAL | - | Full: project edit → pay items → M&P import → preview → apply |
| M05 | Capture Photo (Camera) | Requires camera hardware | Check photos table | MANUAL | - | Full: entry → photos → camera → name dialog → save |
| M07 | Download Remote Project | Requires remote-only project | Check synced_projects locally | MANUAL | - | Full: company tab → tap remote → download → verify |
| M08 | Deactivate/Reactivate Member | Requires second active member | Check user_profiles status | MANUAL | - | Admin: member sheet → deactivate → reactivate |
| M09 | Submit Form (Section-by-Section) | 0582B uses proctor/test section sends, no global submit | Check form_responses status | MANUAL | - | Was T37 — no single submit button to automate |
| M12 | Use Quantity Calculator from Entry | Calculator not launchable from entry report screen | Check entry_quantities count | MANUAL | - | Was T21 — calculator not wired from entry context |
| M13 | Add Personnel Type from Entry | Personnel types management not reachable from entry | Check personnel_types count | MANUAL | - | Was T67 — PersonnelTypesScreen exists but no tile/route to it |
| M10 | Approve Join Request | Requires pending join request from second account | Check user_profiles approval | MANUAL | - | Was T56 — no pending requests exist for automation |
| M11 | Reject Join Request | Requires pending join request from second account | Check company_join_requests rejection | MANUAL | - | Was T57 — no pending requests exist for automation |

---

## Flow Count Summary

| Tier | Range | Count | Description |
|------|-------|-------|-------------|
| Tier 0 | T01-T04 | 4 | Auth & Smoke |
| Tier 1 | T05-T14 | 10 | Project Setup (Admin) |
| Tier 2 | T15-T23 | 9 | Daily Entry Creation |
| Tier 3 | T24-T30 | 7 | Entry Lifecycle |
| Tier 4 | T31-T40 | 10 | Toolbox |
| Tier 5 | T41-T43 | 3 | PDF & Export |
| Tier 6 | T44-T52 | 8 | Settings & Profile (T50 removed — replaced by S01-S10 Claude-driven flows) |
| Tier 7 | T53-T58 | 6 | Admin Operations |
| Tier 8 | T59-T67 | 9 | Edit & Update Mutations |
| Tier 9 | T68-T77 | 10 | Delete Operations |
| Sync | S01-S11 | 11 | Sync Verification (Claude-driven, dual-device) |
| Tier 11 | T85-T91 | 7 | Role & Permission Verification |
| Tier 12 | T92-T96 | 5 | Navigation & Dashboard |
| Manual | M01-M13 | 12 | Manual-Only Flows (M06 removed — offline-reconnect covered by S01-S10 sync verification) |
| **Total** | | **106** | **83 automated + 12 manual + 11 sync verification (Claude-driven)** |

## Dependency Chain (Execution Order)

```
T01 (Login Admin)
 ├── T02 (Navigate Tabs)
 ├── T03 (Sign Out) — run last in auth tier
 ├── T05 (Create Project)
 │    ├── T06 (Add Location A)
 │    │    └── T15 (Create Entry)
 │    │         ├── T16 (Safety Fields)
 │    │         ├── T17 (Add Contractor to Entry) → T18 (Personnel) → T19 (Equipment Usage)
 │    │         ├── T20 (Log Quantity) → T21 (Calculator)
 │    │         ├── T22 (Attach Photo) → T23 (Second Photo)
 │    │         ├── T24 (Edit Location) → T25 (Edit Weather)
 │    │         ├── T62 (Edit Activities) → T63 (Edit Temp) → T64 (Edit Qty)
 │    │         ├── T41 (Export PDF) → T42 (Export Folder)
 │    │         └── T68 (Delete Photo)
 │    ├── T07 (Add Location B) → T71 (Delete Location B)
 │    ├── T08 (Prime Contractor) → T10 (Equipment) → T69 (Delete Equipment)
 │    ├── T09 (Sub Contractor) → T70 (Delete Contractor)
 │    ├── T11 (Pay Item 1) → T61 (Edit Pay Item)
 │    ├── T12 (Pay Item 2) → T72 (Delete Pay Item)
 │    ├── T13 (Assignment) → T66 (Remove Assignment)
 │    ├── T14 (Search)
 │    ├── T26 (Day 2 Entry) → T27 (Review) → T28 (Submit) → T29 (Undo) → T30 (Delete)
 │    ├── T31 (Todo) → T32 (Edit) → T33 (Complete) → T34 (Delete)
 │    ├── T35 (Form) → T36 (Fill) → T37 (Submit) → T43 (Export) → T74 (Delete)
 │    ├── T58 (Archive) → T65 (Unarchive)
 │    └── T59 (Edit Project)
 ├── T38 (Calculator HMA) → T39 (Calculator Concrete)
 ├── T40 (Gallery Browse)
 ├── T44-T49, T51-T52 (Settings flows; T50 removed — sync via S01-S10)
 ├── T53-T58 (Admin flows)
 ├── T75 (Remove from Device)
 ├── T92-T96 (Navigation verification)
 └── T51 (Trash Restore) → T77 (Trash Delete Forever)

T04 (Login Inspector) — separate session
 ├── T85-T91 (Permission checks)
 ├── T87 (Inspector Create Entry)
 └── T88 (Inspector Create Todo)

S01 (Project Setup) — dual-device session (admin:4948, inspector:4949)
 ├── S02 (Daily Entry) → S03 (Photos) [COMPACTION]
 ├── S04 (Forms)
 ├── S05 (Todos)
 ├── S06 (Calculator) [COMPACTION]
 ├── S07 (Update All) → S08 (PDF Export) → S11 (Documents) → S09 (Delete Cascade) [COMPACTION]
 └── S10 (Unassignment + Cleanup)
```

## Auto-Update Protocol

After each test run, the agent MUST update:
1. **Status** column: PASS or FAIL
2. **Last Run** column: ISO date (e.g., 2026-03-20)
3. **Notes** column: failure reason if FAIL, cleared on PASS
