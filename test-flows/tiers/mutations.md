# Tier 8: Edit & Update Mutations (T59-T67)

> Modify existing entities and verify sync push.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Notes |
|----|------|----------|--------------|-------------|-------|
| T59 | Edit Project Details | projects | tap(project_card) → tap(project_edit) → text(project_name,"E2E Updated Project") → tap(project_save) | sync,db | Depends: T05 |
| T60 | Edit Contractor | contractors | tap(project_edit) → tap(contractors_tab) → tap(contractor_card) → text(contractor_name,"E2E Prime Updated") → tap(contractor_save) | sync,db | Depends: T08 |
| T61 | Edit Pay Item | bid_items | tap(project_edit) → tap(payitems_tab) → tap(bid_item_edit) → text(item_desc,"HMA Surface Updated") → tap(bid_item_save) | sync,db | Depends: T11 |
| T62 | Edit Entry Activities | daily_entries | tap(entry_card) → tap(report_activities_section) → wait(report_activities_field) → text(report_activities_field,"Updated activities text") → wait(auto_save) | sync,db | Depends: T15; tap activities card to enter edit mode first |
| T63 | Edit Entry Temperature | daily_entries | tap(entry_card) → tap(report_temperature_section) → wait(report_temp_low_field) → text(report_temp_low_field,"50") → text(report_temp_high_field,"80") → wait(auto_save) | sync,db | Depends: T15; tap temperature row to enter edit mode first |
| T64 | Edit Quantity Value | entry_quantities | tap(entry_card) → tap(quantity_row) → text(quantity_value,"25.0") → tap(quantity_save) | sync,db | Depends: T20 |
| T65 | Unarchive Project | projects | tap(projects_nav) → tap(archived_tab) → tap(activate_btn) → wait(project_active) | sync,db | Depends: T58 |
| T66 | Remove Assignment | project_assignments | tap(project_edit) → tap(assignments_tab) → tap(remove_assignment) → tap(remove_confirm) | sync,db | Depends: T13 |
| T67 | Add Personnel Type | personnel_types | tap(entry_card) → tap(personnel_types_add) → text(personnel_type_name,"Laborer") → tap(type_save) | sync,db | Personnel types management not wired from entry screen; screen exists but not reachable |

---

# Tier 9: Delete Operations (T68-T77)

> Soft-delete entities and verify sync push of deletion.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Notes |
|----|------|----------|--------------|-------------|-------|
| T68 | Delete Photo | photos | tap(entry_card) → tap(photo_thumbnail) → tap(photo_delete) → tap(delete_confirm) | sync,photo | Depends: T23 (deletes second photo) |
| T69 | Delete Equipment | equipment | tap(project_edit) → tap(contractors_tab) → tap(contractor_card) → tap(equipment_delete) → tap(delete_confirm) | sync,db | Depends: T10 |
| T70 | Delete Contractor | contractors | tap(project_edit) → tap(contractors_tab) → tap(contractor_delete_sub) → tap(delete_confirm) | sync,db | Depends: T09 (deletes sub) |
| T71 | Delete Location | locations | tap(project_edit) → tap(locations_tab) → tap(location_delete_b) → tap(delete_confirm) | sync,db | Depends: T07 (deletes Location B) |
| T72 | Delete Pay Item | bid_items | tap(project_edit) → tap(payitems_tab) → tap(bid_item_delete) → tap(delete_confirm) | sync,db | Depends: T12 (deletes second pay item) |
| T73 | Delete Todo | todo_items | tap(toolbox_nav) → tap(todos_tile) → tap(todo_delete) → tap(delete_confirm) | sync,db | Depends: T31 |
| T74 | Delete Form Response | form_responses | tap(toolbox_nav) → tap(forms_tile) → tap(form_card) → tap(form_delete) → tap(delete_confirm) | sync,db | Depends: T35 |
| T75 | Remove Project from Device | projects (local) | tap(projects_nav) → long_press(project_card) → tap(delete_from_device) → wait(project_removed) | db | Depends: T05; device-only removal |
| T76 | Delete Remote Project (Admin) | projects | tap(projects_nav) → tap(company_tab) → long_press(remote_project_card) → tap(delete_remote) → tap(delete_confirm) | sync,db | Requires remote-only project visible to admin |
| T77 | Permanently Delete from Trash | varies | tap(settings_nav) → tap(trash_tile) → tap(delete_forever_btn) → tap(delete_confirm) → screenshot | db | Depends: T68 or T30 (needs trashed item) |
