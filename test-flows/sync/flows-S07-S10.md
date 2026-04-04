# Sync Flows S07-S10: Update + PDF + Delete + Cleanup

> Compaction pause after S09 — checkpoint written, user prompted to continue.

---

## S07: Update All

**Tables:** All updatable tables
**Depends:** S01-S06

**Admin (4948):**

Update each entity type created in S01-S06:

1. **Project name**: Navigate to project → tap edit → update name field → save:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"projects_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_edit_menu_item_<projectId>"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"project_name_field","text":"VRF-Oakridge '"${RUN_TAG}"' Phase 2"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_save_button"}'
   sleep 2
   ```

2. **Location**: Edit location name → append " Ext" → save:
   ```bash
   # Navigate to project edit → locations tab → tap edit on location 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_edit_menu_item_<projectId>"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_locations_tab"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"location_edit_button_<locationId1>"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"location_name_field","text":"VRF-Station 12+50 '"${RUN_TAG}"' Ext"}'
   # location_dialog_add is reused as the confirm button for both add and edit dialogs
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"location_dialog_add"}'
   sleep 1
   ```

3. **Contractor**: Edit contractor name → append " LLC" → save:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_contractors_tab"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_edit_button_<contractorId1>"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"contractor_name_field","text":"VRF-Midwest Excavating '"${RUN_TAG}"' LLC"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_save_button"}'
   sleep 1
   ```

4. **Equipment**: Edit equipment name via UI → navigate to project edit → contractors tab → expand contractor card → tap equipment edit → update name → save.
   ```bash
   # Navigate to contractor card, expand it, edit equipment via UI
   # Key patterns: contractor_card_<id>, equipment_edit_button_<id>, equipment_name_field, equipment_dialog_add
   ```

5. **Bid item**: Edit description → append " (Modified)" → save.

6. **Personnel type**: Edit name → save.

7. **Daily entry**: Edit activities text → append " [updated]":
   ```bash
   # Navigate to entry → edit → update activities field
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"entry_card_<entryId>"}'
   sleep 1
   # entry_edit_button is section-scoped. Use the activities section key.
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"entry_edit_button_activities"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"entry_wizard_activities","text":"VRF-Excavation and grading operations '"${RUN_TAG}"' [updated]"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"entry_wizard_save_draft"}'
   sleep 2
   ```

8. **Photo**: Edit description field via UI — navigate to entry → tap photo → edit caption → save.

9. **Entry equipment**: Toggle equipment on/off via entry edit wizard.

10. **Entry personnel count**: Increment count via entry edit wizard.

11. **Form response**: Edit remarks field via form edit screen.

12. **Entry quantity**: Update value via entry edit wizard.

13. **Todo**: Update title → append " [done]":
    ```bash
    curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_toolbox_card"}'
    sleep 1
    curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"toolbox_todos_card"}'
    sleep 1
    # Tap the todo card to open the edit dialog (key pattern: todo_card_<todoId>)
    curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"todo_card_<todoId1>"}'
    sleep 1
    curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"todos_title_field","text":"VRF-Check rebar spacing '"${RUN_TAG}"' [done]"}'
    curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"todos_save_button"}'
    sleep 1
    ```

After all updates:
- Sync admin
- Supabase verify: spot-check 3-4 key updates (project name, entry activities, todo title)
- Inspector sync x2 → verify updated project name locally

---

## S08: PDF Export

**Tables:** N/A (output artifact)
**Depends:** S07

**Prerequisite:** Verify pdftk is installed: `pdftk --version`. If not available, verify the PDF by checking the file exists and its size is > 1000 bytes instead of using pdftk field inspection.

**Admin (4948):**

1. Navigate to entry → export PDF:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"report_export_pdf_button"}'
   sleep 1
   ```

2. Enter filename → save → wait 5s for generation.

3. ADB pull the PDF (15s timeout):
   ```bash
   # Find the PDF on device, pull via adb
   # If timeout → FAIL S08, continue to S09
   ```

4. Verify with pdftk:
   ```bash
   pdftk <pulled.pdf> dump_data_fields_utf8
   # Check for expected field values
   ```

5. Export 0582B form PDF → verify similarly.

**If ADB times out:** Record FAIL for S08, continue to S09. PDF export is non-blocking.

---

## S09: Delete Cascade

**Tables:** All child tables of project 1
**Depends:** S07

**Admin (4948):**

1. Navigate to projects list:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"projects_nav_button"}'
   sleep 1
   ```

2. Two-step delete (soft-delete the project):
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_remove_<projectId>"}'
   sleep 1
   # Two-step delete: tap continue → type project name to confirm → tap delete forever
   # Step 1: tap continue/proceed button
   # Step 2: type project name in confirmation field, then tap delete forever button
   ```

3. Sync admin.

4. **Supabase verify cascade**: Query all 17 child tables — every record with `project_id=<projectId>` should have `is_deleted=true`. Project assignments should be hard-deleted.

   Tables to check: entry_personnel_counts, entry_equipment, entry_quantities, entry_contractors, photos, calculation_history, todo_items, form_responses, form_exports, entry_exports, documents, daily_entries, equipment, personnel_types, bid_items, contractors, locations, inspector_forms.

   ```bash
   # Additional 3 new table checks
   curl -s "${SUPABASE_URL}/rest/v1/form_exports?project_id=eq.<projectId>&deleted_at=is.null&select=id" ... # expect 0 rows
   curl -s "${SUPABASE_URL}/rest/v1/entry_exports?project_id=eq.<projectId>&deleted_at=is.null&select=id" ... # expect 0 rows
   curl -s "${SUPABASE_URL}/rest/v1/documents?project_id=eq.<projectId>&deleted_at=is.null&select=id" ...    # expect 0 rows
   ```

   Project assignments: query should return 0 rows (hard-deleted).

5. Inspector sync via UI (2 rounds) → check for `deletion_notification_banner` → verify project gone from local device:
   ```bash
   # Sync via UI (NEVER use POST /driver/sync)
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
   sleep 3
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
   sleep 3
   curl -s http://127.0.0.1:4949/driver/find?key=deletion_notification_banner
   # Response {exists: true} = banner is visible (deletion notification shown correctly).
   # If {exists: false}, the deletion notification was not shown — record as observation or bug.
   # Navigate to projects list and screenshot to verify project is no longer visible
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"projects_nav_button"}'
   sleep 1
   curl -s http://127.0.0.1:4949/driver/screenshot --output "$RESULTS_DIR/S09-inspector-project-deleted.png"
   ```

**--- COMPACTION PAUSE ---**

---

## S10: Unassignment + Cleanup

**Tables:** project_assignments, projects
**Depends:** S01

**Inspector (4949):**
1. Verify project2 exists locally via UI (navigate to projects list and screenshot):
   ```bash
   # NEVER use GET /driver/local-record — verify via UI instead
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"projects_nav_button"}'
   sleep 1
   curl -s http://127.0.0.1:4949/driver/screenshot --output "$RESULTS_DIR/S10-inspector-project2-exists.png"
   # Visually confirm project2 (VRF-Unassign Test) is in the list
   ```

**Admin (4948):**
2. Edit project2 → assignments tab → toggle off inspector → save → sync:
   ```bash
   # Navigate to project2 edit → assignments tab
   # Toggle off inspector assignment
   # Save → sync
   ```

3. **Supabase verify**: project2 still exists, but assignment is hard-deleted:
   ```bash
   curl -s "${SUPABASE_URL}/rest/v1/projects?id=eq.<project2Id>&select=id,name" ...
   curl -s "${SUPABASE_URL}/rest/v1/project_assignments?project_id=eq.<project2Id>&select=id" ...
   # projects: 1 row. assignments: 0 rows.
   ```

**Inspector (4949):**
4. Sync x2 via UI → verify project2 is removed from local device (unassigned = no longer visible):
   ```bash
   # Sync via UI (NEVER use POST /driver/sync)
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
   sleep 3
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
   sleep 3
   # Verify project2 is gone — navigate to projects list and screenshot
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"projects_nav_button"}'
   sleep 1
   curl -s http://127.0.0.1:4949/driver/screenshot --output "$RESULTS_DIR/S10-inspector-project2-removed.png"
   # Visually confirm project2 (VRF-Unassign Test) is no longer in the list
   ```

**Admin (4948):**
5. Delete project2 → sync (cleanup):
   ```bash
   # Two-step delete project2, sync admin
   ```

**Post-Run Sweep:**
Query all 20 synced tables for any records with `VRF-` in name/description fields. Any remaining records = FAIL.

Also check the 3 new tables:
```bash
curl -s "${SUPABASE_URL}/rest/v1/form_exports?project_id=eq.<project2Id>&select=id" ...
curl -s "${SUPABASE_URL}/rest/v1/entry_exports?project_id=eq.<project2Id>&select=id" ...
curl -s "${SUPABASE_URL}/rest/v1/documents?project_id=eq.<project2Id>&select=id" ...
```

```bash
# Check projects
curl -s "${SUPABASE_URL}/rest/v1/projects?name=like.VRF-%25&select=id,name" ...
# Check locations
curl -s "${SUPABASE_URL}/rest/v1/locations?name=like.VRF-%25&select=id,name" ...
# Check contractors
curl -s "${SUPABASE_URL}/rest/v1/contractors?name=like.VRF-%25&select=id,name" ...
# ... repeat for all tables with name/description fields
```

If any VRF records remain, record them in the report as FAIL.
