# Sync Flows S01-S03: Project + Entry + Photos

> Compaction pause after S03 — checkpoint written, user prompted to continue.

---

## S01: Project Setup

**Tables:** projects, project_assignments, locations, contractors, equipment, bid_items, personnel_types

**Admin (4948):**

1. Navigate to project creation:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"projects_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_create_button"}'
   sleep 1
   ```

2. Fill project fields:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"project_name_field","text":"VRF-Oakridge '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"project_number_field","text":"VRF-'"${RUN_TAG}"'-001"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"project_client_field","text":"VRF-City of Oakridge '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_save_button"}'
   sleep 2
   ```

3. Sync admin via UI and capture project ID from Supabase:
   ```bash
   # Sync via UI (NEVER use POST /driver/sync)
   curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
   sleep 3
   # Query Supabase for the project
   curl -s "${SUPABASE_URL}/rest/v1/projects?name=like.VRF-Oakridge%20${RUN_TAG}%25&select=id,name" \
     -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
     -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}"
   # Capture projectId from response
   ```

4. Edit project — add 2 locations:
   ```bash
   # Navigate to project edit → locations tab
   # NOTE: project_edit_menu_item requires projectId — use project_edit_menu_item_<projectId>
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_edit_menu_item_<projectId>"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_locations_tab"}'
   sleep 1
   # Location 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_add_location_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"location_name_field","text":"VRF-Station 12+50 '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"location_dialog_add"}'
   sleep 1
   # Location 2
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_add_location_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"location_name_field","text":"VRF-Station 25+00 '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"location_dialog_add"}'
   sleep 1
   ```

5. Add 2 contractors:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_contractors_tab"}'
   sleep 1
   # Contractor 1 (Prime)
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_add_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"contractor_name_field","text":"VRF-Midwest Excavating '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_type_prime"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_save_button"}'
   sleep 1
   # Contractor 2 (Sub)
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_add_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"contractor_name_field","text":"VRF-Allied Paving '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_type_sub"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_save_button"}'
   sleep 1
   ```

6. Add equipment to each contractor (expand card first):
   ```bash
   # Expand prime contractor card, add equipment
   # NOTE: contractor_card requires contractorId — tap card to expand
   # Note: equipment is added per-contractor — tap contractor_card_<id> to expand the contractor first
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_card_<contractorId>"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_add_equipment_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"equipment_name_field","text":"VRF-CAT 320 Excavator '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"equipment_dialog_add"}'
   sleep 1
   # Second equipment
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_add_equipment_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"equipment_name_field","text":"VRF-Volvo A40G Hauler '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"equipment_dialog_add"}'
   sleep 1
   ```

7. Add pay item:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_payitems_tab"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_add_pay_item_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"pay_item_source_manual"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"pay_item_number_field","text":"VRF-401"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"pay_item_description_field","text":"VRF-HMA Surface Course '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"pay_item_quantity_field","text":"500"}'
   # Unit is a dropdown, not text field
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"pay_item_unit_dropdown"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"pay_item_unit_ton"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"pay_item_dialog_save"}'
   sleep 1
   ```

8. Add 3 personnel types (via Contractors tab — expand contractor card):
   ```bash
   # Personnel types are added from within the Contractors tab, not Settings.
   # The contractor card must be expanded first (tap to enter editing mode).
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_contractors_tab"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_card_<contractorId1>"}'
   sleep 1
   # Laborer
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_add_personnel_type_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"personnel_type_dialog_name_field","text":"VRF-Laborer '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"personnel_type_dialog_add"}'
   sleep 1
   # Operator
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_add_personnel_type_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"personnel_type_dialog_name_field","text":"VRF-Operator '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"personnel_type_dialog_add"}'
   sleep 1
   # Foreman
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_add_personnel_type_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"personnel_type_dialog_name_field","text":"VRF-Foreman '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"personnel_type_dialog_add"}'
   sleep 1
   ```

9. Assign inspector:
   ```bash
   # Navigate to assignments tab (still in project edit)
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_assignments_tab"}'
   sleep 1
   # Toggle inspector user assignment
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"assignment_tile_<INSPECTOR_USER_ID>"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_save_button"}'
   sleep 2
   ```

10. Sync admin → Supabase verify all 7 tables → capture all entity IDs into `ctx`.

11. Inspector sync (2 rounds) → verify projects, locations, contractors locally.

12. Create second project "VRF-Unassign Test {tag}":
    - Same flow as steps 1-3 but with different name
    - Assign inspector
    - Sync both devices
    - Capture `project2Id` into `ctx`

**Supabase Verify:** Query all 7 tables filtered by `projectId`. Capture IDs for:
- `ctx.locationIds` (2), `ctx.contractorIds` (2), `ctx.equipmentIds` (2)
- `ctx.bidItemIds` (1), `ctx.personnelTypeIds` (3), `ctx.assignmentId` (1)
- `ctx.project2Id` (1)

---

## S02: Daily Entry

**Tables:** daily_entries, entry_contractors, entry_equipment, entry_personnel_counts, entry_quantities
**Depends:** S01

**Admin (4948):**

1. Navigate to dashboard → add entry:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_nav_button"}'
   sleep 1
   # NOTE: Button is dashboard_new_entry_button (not add_entry_fab)
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_new_entry_button"}'
   sleep 2
   ```

2. Fill entry fields — location auto-selects first location, weather defaults to Sunny:
   ```bash
   # Location and weather dropdowns may already have defaults selected.
   # Verify with /driver/find?key=entry_wizard_location_dropdown before tapping.
   # If you need to change location:
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"entry_wizard_location_dropdown"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"location_option_<ctx.locationIds[0]>"}'
   sleep 1
   # Temps
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"entry_wizard_temp_low","text":"62"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"entry_wizard_temp_high","text":"78"}'
   # Activities — NOTE: key is report_activities_field (not entry_wizard_activities)
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"report_activities_field","text":"VRF-Excavation and grading operations '"${RUN_TAG}"'"}'
   sleep 1
   ```

3. Save as draft first (contractors/equipment/quantities are added from the report screen, not the create wizard):
   ```bash
   # Scroll to save button using the scrollable key
   curl -s -X POST http://127.0.0.1:4948/driver/scroll-to-key \
     -d '{"scrollable":"entry_editor_scroll","target":"entry_wizard_save_draft","maxScrolls":10}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"entry_wizard_save_draft"}'
   sleep 2
   ```

4. From the report screen, add 2 entry contractors:
   ```bash
   # After saving, the app navigates to the report screen.
   # Add contractors via the report screen's add contractor button.
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"report_add_contractor_button"}'
   sleep 1
   # Tap contractor items in the add-contractor sheet
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"report_add_contractor_item_<ctx.contractorIds[0]>"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"report_add_contractor_item_<ctx.contractorIds[1]>"}'
   sleep 1
   ```

5. Toggle equipment on report screen:
   ```bash
   # Equipment checkboxes appear within each contractor card on the report screen.
   # Key pattern: report_equipment_checkbox_<equipmentId>
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"report_equipment_checkbox_<ctx.equipmentIds[0]>"}'
   sleep 1
   ```

6. Add personnel counts on report screen:
   ```bash
   # Personnel counters are scoped per contractor on the report screen.
   # Key pattern: report_personnel_counter_<contractorId>_<typeId>
   # These are counter widgets — tap to increment.
   # NOTE: Verify exact key patterns at runtime with /driver/tree?filter=personnel
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"report_personnel_counter_<ctx.contractorIds[0]>_<ctx.personnelTypeIds[0]>"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"report_personnel_counter_<ctx.contractorIds[0]>_<ctx.personnelTypeIds[0]>"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"report_personnel_counter_<ctx.contractorIds[0]>_<ctx.personnelTypeIds[1]>"}'
   sleep 1
   ```

7. Add quantity on report screen:
   ```bash
   # Key: report_add_quantity_button
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"report_add_quantity_button"}'
   sleep 1
   # Tap the bid item in the autocomplete/picker
   # Key pattern: bid_item_option_<bidItemId>
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"bid_item_option_<ctx.bidItemIds[0]>"}'
   sleep 1
   # Enter quantity amount — verify field key at runtime
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"report_quantity_amount_field_<quantityId>","text":"125"}'
   sleep 1
   ```

8. Cross-device sync protocol (4-step). Entry auto-saves on the report screen.

**Supabase Verify:** Query `daily_entries`, `entry_contractors`, `entry_equipment`, `entry_personnel_counts`, `entry_quantities` by project_id.

**Capture:** `ctx.entryId`, `ctx.entryContractorIds`, `ctx.entryEquipmentIds`, `ctx.entryPersonnelCountIds`, `ctx.entryQuantityIds`

---

## S03: Photos

**Tables:** photos
**Depends:** S02

**Admin (4948):**

1. Inject photo directly (no camera needed):
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/inject-photo-direct \
     -d '{"base64Data":"<small-test-jpeg-base64>","filename":"VRF-test-photo-'"${RUN_TAG}"'.jpg","entryId":"<ctx.entryId>","projectId":"<ctx.projectId>"}'
   # NOTE: inject-photo-direct uses camelCase params (projectId, entryId, base64Data)
   # This is different from remove-from-device which uses snake_case (project_id)
   ```

2. Cross-device sync protocol (4-step).

**Supabase Verify:** Query `photos?entry_id=eq.<entryId>`.

**Capture:** `ctx.photoIds`

**--- COMPACTION PAUSE ---**
