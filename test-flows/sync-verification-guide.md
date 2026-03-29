# Sync Verification Guide (S01-S11)

> Claude-driven dual-device sync verification. This guide is the primary reference
> for executing `/test sync`. Read it fully before starting a sync verification run.

## Environment Setup

### Devices
- **Admin device** (port 4948): Primary device — creates all data
- **Inspector device** (port 4949): Secondary device — pulls and verifies synced data

Both devices must be running the app with `main_driver.dart` entrypoint.

### Credentials
Read from `.claude/test-credentials.secret`:
- Admin account: logged in on port 4948
- Inspector account: logged in on port 4949

> **NOTE:** test-credentials.secret values must never be echoed in reports, checkpoints, or log output.

### Supabase Access
Load from `tools/debug-server/.env.test`:
- `SUPABASE_URL` — project URL
- `SUPABASE_SERVICE_ROLE_KEY` — service role key (bypasses RLS for verification)

> **WARNING:** Service role key grants full database access. Never share conversation logs from test runs.

```bash
# Load env vars for the session
# On Windows: use `py -3` or `python` instead of `python3`
eval $(python3 -c "
import os
for line in open('tools/debug-server/.env.test'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        v = v.strip().strip('\"').strip(\"'\")
        print(f'export {k.strip()}=\"{v}\"')
")
```

```bash
# After testing is complete, unset sensitive environment variables:
unset SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY
```

Avoid running `env` or `printenv` during test sessions to prevent accidental key exposure.

### Per-Run Unique Tag
Generate a 5-char alphanumeric tag at the start of each run:
```bash
# On Windows: use `py -3` or `python` instead of `python3`
RUN_TAG=$(python3 -c "import random,string; print(''.join(random.choices(string.ascii_lowercase + string.digits, k=5)))")
```
All test data uses names prefixed with `VRF-` and embeds this tag to avoid collisions with prior runs.

## Pre-Run Cleanup

Before starting, sweep any leftover VRF- data from prior runs:

1. Query Supabase for projects with `VRF-` prefix:
```bash
curl -s "${SUPABASE_URL}/rest/v1/projects?name=like.VRF-%25&select=id,name" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}"
```

2. If any found, remove from both devices:
```bash
curl -s -X POST http://127.0.0.1:4948/driver/remove-from-device -d '{"project_id":"<id>"}'
curl -s -X POST http://127.0.0.1:4949/driver/remove-from-device -d '{"project_id":"<id>"}'
```

3. Hard-delete from Supabase in FK order (see FK Teardown Order below).

4. Alternatively, use the cleanup utility:
```bash
node tools/debug-server/run-tests.js --cleanup-only
```

## Supabase Query Patterns

### Read records
```bash
curl -s "${SUPABASE_URL}/rest/v1/<table>?<filters>&select=<columns>" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Accept: application/json"
```

### Common filters
- By ID: `?id=eq.<uuid>`
- By project: `?project_id=eq.<uuid>`
- By name prefix: `?name=like.VRF-%25`
- Not deleted: `?is_deleted=eq.false`
- Include deleted: Omit `is_deleted` filter — service role bypasses RLS so all rows are returned

> **WARNING:** Service role bypasses RLS — acceptable ONLY for test verification. Application code must NEVER use service role key.

> Always include VRF- prefix filters on all queries. Do not log raw query responses beyond IDs and names.

### Hard-delete (cleanup only)

> **Safety check:** Before hard-deleting, always query first to confirm only VRF-prefixed records will be affected. Never use broad filters.

```bash
curl -s -X DELETE "${SUPABASE_URL}/rest/v1/<table>?id=eq.<uuid>" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}"
```

## Scrollable Keys Reference

The driver's `/driver/scroll` endpoint requires a `ValueKey` on the scrollable widget itself (not a child).
Use these keys when you need to scroll a screen:

| Screen | Key | Widget Type |
|--------|-----|-------------|
| Entry editor (create/edit) | `entry_editor_scroll` | CustomScrollView |
| Entry review/detail | `entry_review_scroll` | SingleChildScrollView |
| Project details form | `project_details_scroll` | SingleChildScrollView |
| Project locations list | `project_locations_list` | ListView |
| Project contractors list | `project_contractors_list` | ListView |
| Project bid items list | `project_bid_items_list` | ListView |
| Project assignments list | `project_assignments_list` | ListView |
| Settings screen | `settings_list` | ListView |
| Home report preview | `home_report_preview_scroll_view` | SingleChildScrollView (already had key) |

**Usage:**
```bash
# Scroll down by 500px
curl -s -X POST http://127.0.0.1:4948/driver/scroll -d '{"key":"entry_editor_scroll","dx":0,"dy":-500}'
```

> **IMPORTANT:** The `key` must target the scrollable widget, NOT a child widget inside it.
> Child widgets (TextFields, Cards) consume the gesture and prevent scrolling.

## Navigation Map

### Bottom Nav Keys
| Key | Destination | Sentinel (verify arrival) |
|-----|------------|--------------------------|
| `dashboard_nav_button` | Dashboard/Home | `dashboard_new_entry_button` |
| `calendar_nav_button` | Calendar view | — |
| `projects_nav_button` | Projects list | `project_create_button` |
| `settings_nav_button` | Settings | `settings_sync_button` |

### Canonical Sync-via-UI Sequence
```bash
# Admin sync (port 4948)
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_nav_button"}'
sleep 1
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
sleep 3

# Inspector sync (port 4949, 2 rounds for FK deps)
curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_nav_button"}'
sleep 1
curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
sleep 3
curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
sleep 3
```

### Toolbox Navigation
Toolbox sub-screens are TWO levels deep: Dashboard → Toolbox Hub → Sub-screen.
- `dashboard_toolbox_card` → Toolbox hub
- `toolbox_todos_card` → Todos
- `toolbox_calculator_card` → Calculator
- Back from sub-screen → Toolbox Hub (NOT dashboard)
- Back from Toolbox Hub → Dashboard
- Or: tap `dashboard_nav_button` to skip back directly

---

## Android Keyboard Rule

> **WARNING:** After entering text in ANY field on Android, you MUST call `POST /driver/dismiss-keyboard` before tapping buttons. The soft keyboard covers ~40% of the screen. Taps behind it return `{tapped: true}` but never reach the widget. This is the #1 cause of "tap succeeded but nothing happened" failures.

```bash
# After text entry, always dismiss keyboard first
curl -s -X POST http://127.0.0.1:4948/driver/dismiss-keyboard -H "Content-Type: application/json" -d '{}'
sleep 0.3
# Now safe to tap buttons
curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"save_button"}'
```

---

## Cross-Device Sync Protocol

Use this 4-step UI-driven pattern after every data mutation:

### Step 1: Admin Sync via UI
```bash
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_nav_button"}'
sleep 1
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
sleep 3
```
Navigate admin to Settings, tap sync button, wait for completion.

### Step 2: Supabase Verify
Query Supabase REST API to confirm data arrived in the cloud.

### Step 3: Inspector Sync via UI (2 rounds)
```bash
curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_nav_button"}'
sleep 1
curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
sleep 3
curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
sleep 3
```
Two rounds ensure any FK-dependent records that failed on first pull (missing parent) succeed on second.

### Step 4: Inspector UI Verify
Navigate the inspector app to the screen where the synced data should appear, then take a screenshot to confirm visually.
```bash
# Example: verify project exists on inspector's projects screen
curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"projects_nav_button"}'
sleep 1
curl -s http://127.0.0.1:4949/driver/screenshot --output "$RESULTS_DIR/inspector-verify.png"
```

> **BANNED:** Do NOT use `POST /driver/sync` or `GET /driver/local-record` during sync verification. All sync MUST go through the UI. All verification MUST be visual (navigate + screenshot).

## Log Scanning

After every operation, check for errors:
```bash
START_TIME="<iso-timestamp-before-operation>"
curl -s "http://127.0.0.1:3947/logs?since=${START_TIME}&level=error"
```

Also check sync-specific logs after sync:
```bash
curl -s "http://127.0.0.1:3947/logs?since=${START_TIME}&category=sync"
```

Any error-level log entries = investigate before proceeding.

## FK Teardown Order

When hard-deleting test data from Supabase, delete in this order to avoid FK violations:

1. `entry_personnel_counts`
2. `entry_equipment`
3. `entry_quantities`
4. `entry_contractors`
5. `photos`
6. `form_exports` (FK: form_response_id → before form_responses)
7. `calculation_history`
8. `todo_items`
9. `form_responses`
10. `entry_exports` (FK: entry_id → before daily_entries)
11. `documents` (FK: entry_id → before daily_entries)
12. `daily_entries`
13. `equipment`
14. `personnel_types`
15. `bid_items`
16. `contractors`
17. `locations`
18. `inspector_forms`
19. `project_assignments`
20. `projects`

## Checkpoint Schema

Write `.claude/test_results/<run>/checkpoint.json` after every flow:

```json
{
  "run_id": "2026-03-25_14-30",
  "suite": "sync",
  "platform": "dual (android:4948 + windows:4949)",
  "results_dir": ".claude/test_results/2026-03-25_14-30",
  "run_tag": "k1a2b",
  "completed": { "S01": "PASS", "S02": "PASS" },
  "next_flow": "S03",
  "ctx": {
    "project_id": "uuid",
    "project2Id": "uuid",
    "locationIds": ["uuid"],
    "contractorIds": ["uuid"],
    "equipmentIds": ["uuid"],
    "bidItemIds": ["uuid"],
    "personnelTypeIds": ["uuid"],
    "entryId": "uuid",
    "entryContractorIds": ["uuid"],
    "entryEquipmentIds": ["uuid"],
    "entryPersonnelCountIds": ["uuid"],
    "entryQuantityIds": ["uuid"],
    "photoIds": ["uuid"],
    "formResponseIds": ["uuid"],
    "formExportIds": ["uuid"],
    "entryExportIds": ["uuid"],
    "documentIds": ["uuid"],
    "todoIds": ["uuid"],
    "calculationIds": ["uuid"],
    "assignmentId": "uuid"
  },
  "bugs": [],
  "observations": []
}
```

The `ctx` object carries all entity IDs created during the run. This enables:
- Resume from any checkpoint (IDs survive context compaction)
- Cleanup of specific records on failure
- Cross-flow references (e.g., S02 uses `ctx.projectId` from S01)

## Compaction Pauses

After S03, S06, and S09, output:
```
**Checkpoint written. Say 'continue' to proceed.**
```

On resume:
1. Find latest run dir in `.claude/test_results/`
2. Read `checkpoint.json`
3. Load `ctx` to restore all entity IDs
4. **Restore screen state** (see Resume Protocol below)
5. Continue from `next_flow`

## Resume Protocol

After compaction or `--resume`, restore screen state before continuing:

1. **Check both devices are reachable:**
   ```bash
   curl -s http://127.0.0.1:4948/driver/ready
   curl -s http://127.0.0.1:4949/driver/ready
   ```
   If unreachable, wait 5s and retry. If still unreachable, ask user to reconnect.

2. **Navigate both to dashboard:**
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key":"dashboard_nav_button"}'
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"dashboard_nav_button"}'
   ```

3. **Verify correct project is selected** on both devices (take screenshots).

4. **Check debug server is up:**
   ```bash
   curl -s "http://127.0.0.1:3947/logs?limit=1"
   ```

5. **Dismiss any stale overlays:**
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/dismiss-overlays -H "Content-Type: application/json" -d '{}'
   curl -s -X POST http://127.0.0.1:4949/driver/dismiss-overlays -H "Content-Type: application/json" -d '{}'
   ```

---

## Flow Protocols

### S01: Project Setup

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

### S02: Daily Entry

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

### S03: Photos

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

---

### S04: Forms

**Tables:** inspector_forms, form_responses
**Depends:** S02

**Admin (4948):**

1. Navigate to entry → add form:
   ```bash
   # Navigate to dashboard → tap entry card → wait for report screen
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"entry_card_<ctx.entryId>"}'
   sleep 2
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"report_add_form_button"}'
   sleep 1
   ```

2. Select 0582B form → fill header fields → save.

   Look for the form selection dialog that appears after tapping `report_add_form_button`. Tap the 0582B form entry in the list (key pattern likely `form_selection_item_<formId>` or a labeled list tile — identify the 0582B entry by its visible label). Then fill in any required header fields in the form editor and tap the save or confirm button to persist the form response.

3. Cross-device sync protocol (4-step).

**Supabase Verify:** Query `form_responses` by project_id.

**Capture:** `ctx.formResponseIds`

---

### S05: Todos

**Tables:** todo_items
**Depends:** S01

**Admin (4948):**

1. Navigate to toolbox → todos:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_nav_button"}'
   sleep 1
   # Toolbox is accessed via dashboard card, not bottom nav
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_toolbox_card"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"toolbox_todos_card"}'
   sleep 1
   ```

2. Create todo:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"todos_add_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"todos_title_field","text":"VRF-Check rebar spacing '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"todos_save_button"}'
   sleep 1
   ```

3. Cross-device sync protocol (4-step).

**Supabase Verify:** Query `todo_items` by project_id.

**Capture:** `ctx.todoIds`

---

### S06: Calculator

**Tables:** calculation_history
**Depends:** S01

**Admin (4948):**

1. Navigate to toolbox → calculator:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_nav_button"}'
   sleep 1
   # Toolbox is accessed via dashboard card, not bottom nav
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_toolbox_card"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"toolbox_calculator_card"}'
   sleep 1
   ```

2. Select HMA tab → fill fields → calculate → save:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"calculator_hma_tab"}'
   sleep 1
   # HMA inputs: area (sq ft), thickness (inches), density (lbs/cu ft)
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"calculator_hma_area","text":"2400"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"calculator_hma_thickness","text":"4"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"calculator_hma_density","text":"145"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"calculator_hma_calculate_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"calculator_hma_save_button"}'
   sleep 1
   ```

3. Cross-device sync protocol (4-step).

**Supabase Verify:** Query `calculation_history` by project_id.

**Capture:** `ctx.calculationIds`

**--- COMPACTION PAUSE ---**

---

### S07: Update All

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

### S08: PDF Export

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

### S09: Delete Cascade

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

### S10: Unassignment + Cleanup

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

---

### S11: Documents Sync Verification

**Tables:** documents
**Bucket:** entry-documents
**Depends:** S02 (needs existing entry)

**Protocol:**

1. Admin (4948): inject document via `inject-document-direct`:
   ```bash
   # Encode a small test PDF to base64
   BASE64_DOC=$(python3 -c "import base64; print(base64.b64encode(b'%PDF-1.4 test document content').decode())")
   curl -s -X POST http://127.0.0.1:4948/driver/inject-document-direct \
     -H "Content-Type: application/json" \
     -d "{\"base64Data\":\"${BASE64_DOC}\",\"filename\":\"vrf-test-doc-${RUN_TAG}.pdf\",\"entryId\":\"<entryId>\",\"projectId\":\"<projectId>\"}"
   # Capture documentId from response
   ```

2. Admin sync via UI:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
   sleep 3
   ```

3. **Supabase REST verify:**
   ```bash
   curl -s "${SUPABASE_URL}/rest/v1/documents?entry_id=eq.<entryId>&deleted_at=is.null&select=id,filename,remote_path" \
     -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
     -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}"
   # Expect 1 row with remote_path non-null
   ```

4. **Storage verify:**
   ```bash
   curl -s -X POST "${SUPABASE_URL}/storage/v1/object/list/entry-documents" \
     -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
     -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
     -H "Content-Type: application/json" \
     -d "{\"prefix\":\"<companyId>/<projectId>/\",\"limit\":100}"
   # Expect at least 1 file matching the injected document
   ```

5. Inspector (4949) sync x2 via UI:
   ```bash
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
   sleep 3
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
   sleep 3
   ```

6. Inspector UI verify: navigate to entry → verify document attachment visible → screenshot.

7. Capture `ctx.documentIds` for use in S09 cascade verification.

**If document UI not yet wired:** Record as OBSERVATION (not FAIL), continue to S09.

---

## Storage Bucket Verification Pattern

Use this pattern to verify files were uploaded to a storage bucket:

```bash
# Verify file exists in bucket
curl -s -X POST "${SUPABASE_URL}/storage/v1/object/list/<bucket>" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"prefix":"<companyId>/<projectId>/","limit":100}'
```

### Bucket Names
| Table | Bucket |
|-------|--------|
| photos | entry-photos |
| form_exports | form-exports |
| entry_exports | entry-exports |
| documents | entry-documents |

---

## Report Protocol

Write `.claude/test_results/<run>/report.md` with these 8 sections:

### 1. Header
```markdown
# Sync Verification Report — <date> <time>
Platform: dual (android:4948 + windows:4949)
Run Tag: <RUN_TAG>
```

### 2. Results Table
```markdown
## Results
| Flow | Status | Duration | Notes |
|------|--------|----------|-------|
| S01  | PASS   | 45s      |       |
| S02  | PASS   | 30s      |       |
```

### 3. Supabase Verification Summary
```markdown
## Supabase Verification
| Table | Records Created | Records Verified | Cascade Deleted | Notes |
|-------|----------------|-----------------|-----------------|-------|
```

### 4. Cross-Device Sync Results
```markdown
## Cross-Device Sync
| Flow | Admin→Cloud | Cloud→Inspector | Latency | Notes |
|------|-------------|-----------------|---------|-------|
```

### 5. Log Anomalies
```markdown
## Log Anomalies
| Flow | Level | Category | Message | Timestamp |
|------|-------|----------|---------|-----------|
```

### 6. Bugs Found
```markdown
## Bugs Found
- **[BUG]** <description> — flow: S0X
```

### 7. Post-Run Sweep Results
```markdown
## Post-Run Sweep
| Table | VRF Records Found | Status |
|-------|-------------------|--------|
| projects | 0 | CLEAN |
```

### 8. Observations
```markdown
## Observations
- Sync averaged Xs per operation
- <any notable findings>
```

## Edge Cases

### ADB Flakiness
- If `adb` commands fail, retry once after 3s
- If S08 PDF pull fails, record FAIL for S08 only, continue to S09
- ADB is only needed for S08 (PDF export)

### Device Disconnects
- Before each flow, verify device is reachable: `curl -s http://127.0.0.1:<port>/driver/ready`
- If unreachable, retry once after 5s
- If still unreachable, **pause and ask user to reconnect** rather than failing silently
- Write checkpoint before pausing so progress is preserved

### Sync Errors
- If sync returns non-200, capture response body and error logs
- Retry sync once after 5s
- If still failing, FAIL the current flow

### Already Logged In
- Both devices should already be logged in before starting S01
- If a device shows the login screen, log in with the appropriate credentials from `.claude/test-credentials.secret`
- If re-login is needed, use the driver API to enter credentials rather than manual input, to avoid exposure in screen recordings or screenshots.

### Context Exhaustion
- The compaction pauses after S03, S06, S09 are designed to prevent this
- If context is exhausted mid-flow, the checkpoint has all IDs needed to resume
- On resume, read checkpoint.json and restore all `ctx` values before continuing
