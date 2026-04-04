# Tier 0: Auth & Smoke (T01-T04)

> Prerequisite: app launched with driver entrypoint, credentials in `.claude/test-credentials.secret`.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Notes |
|----|------|----------|--------------|-------------|-------|
| T01 | Login (Admin) | user_profiles | tap(login_email) → text(login_email,"admin@email") → tap(login_password) → text(login_password,"pass") → tap(login_submit) → wait(dashboard_screen) | auth | First flow, no deps |
| T02 | Navigate All Tabs | N/A | tap(calendar_nav) → wait(calendar_screen) → tap(projects_nav) → wait(projects_screen) → tap(settings_nav) → wait(settings_screen) → tap(dashboard_nav) → wait(dashboard_screen) | nav | Depends: T01 |
| T03 | Sign Out | N/A | tap(settings_nav) → tap(sign_out_tile) → tap(sign_out_confirm) → wait(login_screen) | auth | Depends: T01 |
| T04 | Login (Inspector) | user_profiles | tap(login_email) → text(login_email,"inspector@email") → tap(login_password) → text(login_password,"pass") → tap(login_submit) → wait(dashboard_screen) | auth | Separate session; verifies inspector role access |

---

# Tier 1: Project Setup — Admin (T05-T14)

> Admin creates a project with all sub-entities. Foundation for all subsequent tiers.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Notes |
|----|------|----------|--------------|-------------|-------|
| T05 | Create Project | projects | tap(projects_nav) → tap(project_create_fab) → text(project_name,"E2E Test Project") → text(project_number,"E2E-001") → text(client_name,"E2E Client") → tap(project_save) → wait(project_list) | sync,db | Depends: T01 |
| T06 | Add Location | locations | tap(project_card) → tap(project_edit) → tap(locations_tab) → tap(add_location) → text(location_name,"E2E Location A") → tap(location_dialog_add) → tap(project_save) | sync,db | Depends: T05 |
| T07 | Add Second Location | locations | tap(project_card) → tap(project_edit) → tap(locations_tab) → tap(add_location) → text(location_name,"E2E Location B") → tap(location_dialog_add) → tap(project_save) | sync,db | Depends: T05; needed for multi-location entry tests |
| T08 | Add Prime Contractor | contractors | tap(project_edit) → tap(contractors_tab) → tap(add_contractor) → text(contractor_name,"E2E Prime Co") → tap(contractor_type_prime) → tap(contractor_save) | sync,db | Depends: T05 |
| T09 | Add Sub Contractor | contractors | tap(contractors_tab) → tap(add_contractor) → text(contractor_name,"E2E Sub Co") → tap(contractor_type_sub) → tap(contractor_save) | sync,db | Depends: T05 |
| T10 | Add Equipment to Contractor | equipment | tap(contractor_card_prime) → tap(add_equipment) → text(equipment_name,"E2E Excavator") → tap(equipment_save) | sync,db | Depends: T08 |
| T11 | Add Pay Item (Manual) | bid_items | tap(project_edit) → tap(payitems_tab) → tap(add_payitem) → tap(payitem_source_manual) → text(item_number,"E2E-100") → text(item_desc,"HMA Surface Course") → text(item_qty,"500") → text(item_unit,"TON") → tap(bid_item_save) | sync,db | Depends: T05 |
| T12 | Add Second Pay Item | bid_items | tap(payitems_tab) → tap(add_payitem) → tap(payitem_source_manual) → text(item_number,"E2E-200") → text(item_desc,"Concrete Pavement") → text(item_qty,"1000") → text(item_unit,"SY") → tap(bid_item_save) | sync,db | Depends: T05; needed for multi-quantity tests |
| T13 | Add Project Assignment | project_assignments | tap(project_edit) → tap(assignments_tab) → tap(add_assignment) → tap(user_select_inspector) → tap(assignment_save) | sync,db | Depends: T05; assigns inspector user |
| T14 | Search Projects | N/A | tap(projects_nav) → tap(search_icon) → text(search_field,"E2E") → wait(project_card) → screenshot | nav | Depends: T05 |
