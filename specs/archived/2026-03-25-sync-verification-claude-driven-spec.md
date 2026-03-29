# Sync Verification — Claude-Driven Flows

**Date**: 2026-03-25
**Status**: APPROVED
**Replaces**: Node.js integrity-runner system (integrity-runner.js + scenarios/integrity/*.js)

---

## Overview

Replace the Node.js integrity-runner with Claude-driven sync verification flows (S01-S10) that follow the same execution model as the /test skill. Claude drives two devices via curl, verifies data in Supabase via REST API, and tracks results via checkpoint/report/registry.

### Why

The JS-driven system fails opaquely — can't inspect widget trees mid-flow, can't adapt to unexpected UI states, and can't debug timing issues. Claude-driven flows let us react in real time.

### Success Criteria

1. All 10 flows registered in registry.md, executable via `/test sync`
2. Cross-device verification works (admin creates → Supabase verified → inspector pulls → device verified)
3. Unique per-run data prevents collisions between runs
4. Cleanup at start catches orphans from prior failed runs; post-run sweep treats leftovers as FAIL
5. Checkpoint after each flow enables resume; compaction pauses after S03, S06, S09
6. All deleted JS infrastructure removed from the codebase
7. Report updated after every flow — bugs, log anomalies, and verification results preserved on disk

---

## Deletion List

### Files to Delete

- `tools/debug-server/integrity-runner.js`
- `tools/debug-server/scenarios/integrity/*.js` (10 files: F1-F6, U1, P1, D1, D2)
- `tools/debug-server/scenarios/integrity/` (directory)
- `tools/debug-server/scenarios/deprecated/` (entire directory — old L2/L3)
- `tools/debug-server/test-runner.js` (L2/L3 orchestrator)
- `tools/debug-server/device-orchestrator.js` (Claude uses curl instead)
- `tools/debug-server/scenario-helpers.js` (factories/helpers no longer needed)

### Files to Modify

- `tools/debug-server/run-tests.js` — Strip to `--cleanup-only` mode only; remove `--suite=integrity`, `--layer`, `--table`, `--filter`, L2/L3 paths
- `.claude/skills/test/skill.md` — Update sync tier alias, add dual-device + Supabase sections
- `.claude/test-flows/registry.md` — Add S01-S10 tier, remove old sync/L2/L3 references

### Files to Create

- `.claude/test-flows/sync-verification-guide.md` — Companion reference doc for Claude

### Files That Stay

- `tools/debug-server/server.js` (debug server on port 3947)
- `tools/debug-server/supabase-verifier.js` (used by `--cleanup-only`)
- `tools/debug-server/run-tests.js` (stripped to cleanup-only)
- `tools/debug-server/nuke-all-data.js` (emergency wipe)
- `tools/debug-server/.env.test` (credentials)

---

## Flow Registry

### 10 Flows, S-Prefixed

| ID | Flow | Tables | Devices | Depends |
|----|------|--------|---------|---------|
| S01 | Project Setup | projects, project_assignments, locations, contractors, equipment, bid_items, personnel_types | Admin creates, Inspector pulls | Login |
| S02 | Daily Entry | daily_entries, entry_contractors, entry_equipment, entry_personnel_counts, entry_quantities | Admin creates, Inspector pulls | S01 |
| S03 | Photos | photos | Admin injects, Inspector pulls | S02 |
| S04 | Forms | inspector_forms (verify), form_responses (create) | Admin creates, Inspector pulls | S02 |
| S05 | Todos | todo_items | Admin creates, Inspector pulls | S01 |
| S06 | Calculator | calculation_history | Admin creates, Inspector pulls | S01 |
| S07 | Update All | All updatable tables | Admin updates, Supabase verified, Inspector pulls | S01-S06 |
| S08 | PDF Export | N/A (output artifact) | Admin exports, ADB pull, pdftk verify | S07 |
| S09 | Delete Cascade | All child tables of project 1 | Admin deletes, cascade verified, Inspector notified | S07 |
| S10 | Unassignment + Cleanup | project_assignments, project 2 | Admin unassigns, Inspector loses access, Admin deletes project 2 | S01 |

### Compaction Pauses

- After S03 (creation phase 1 complete)
- After S06 (creation phase 2 complete)
- After S09 (delete cascade complete)

At each pause: write full checkpoint, update report, output "Checkpoint written. Say 'continue' to proceed."

### Post-Run Sweep

After S10, Claude curls Supabase for any remaining `VRF-*` records across all tables. If any records found → FAIL with details of what D1/D2 failed to clean up.

---

## Per-Flow Execution Model

Same pattern as T-flows, extended for dual-device + Supabase:

1. Record start time
2. Execute curl commands (tap/text/navigate on port 4948 or 4949)
3. After every mutation: check debug server logs for errors
4. Sync device(s): `POST /driver/sync`, poll sync status
5. Verify Supabase: curl REST API with service role key
6. Verify device local records: `GET /driver/local-record`
7. Check error logs: `GET localhost:3947/logs?since=<START>&level=error`
8. Take screenshot on failure
9. Update checkpoint.json (includes all collected IDs in `ctx`)
10. Update report.md
11. Update registry.md (Status + Last Run)

### Unique Per-Run Data

Each run generates a 5-char tag: `date +%s | python3 -c "import sys; print(int(sys.stdin.read()))" | python3 -c "import sys; n=int(sys.stdin.read()); s=''; digits='0123456789abcdefghijklmnopqrstuvwxyz'; exec('while n:\\n s=digits[n%36]+s;n//=36'); print(s[-5:])""`

All VRF test data includes the tag:
- Project name: `VRF-Oakridge {tag}`
- Project number: `VRF-{tag}-001`
- Location: `VRF-Station 12+50 {tag}`
- Contractor: `VRF-Midwest Excavating {tag}`
- etc.

---

## Supabase Verification Pattern

Claude reads `.env.test` once at run start to get `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

### Query Records

```bash
curl -s "${SUPABASE_URL}/rest/v1/<table>?<filters>" \
  -H "apikey: ${KEY}" \
  -H "Authorization: Bearer ${KEY}" \
  -H "Accept: application/json"
```

Filters use PostgREST syntax: `name=like.VRF-*`, `project_id=eq.<uuid>`, etc.

### Hard Delete (cleanup)

```bash
curl -s -X DELETE "${SUPABASE_URL}/rest/v1/<table>?id=eq.<uuid>" \
  -H "apikey: ${KEY}" \
  -H "Authorization: Bearer ${KEY}"
```

### FK Teardown Order

For cleanup, delete children first:
1. entry_personnel_counts
2. entry_equipment
3. entry_quantities
4. entry_contractors
5. photos
6. calculation_history
7. todo_items
8. form_responses
9. daily_entries
10. equipment
11. personnel_types
12. bid_items
13. contractors
14. locations
15. inspector_forms
16. project_assignments
17. projects

---

## Cross-Device Sync Protocol

4-step pattern used after every data mutation:

1. **Admin sync**: `curl -s -X POST http://127.0.0.1:4948/driver/sync -H "Content-Type: application/json"`
2. **Supabase verify**: curl REST API to confirm data arrived
3. **Inspector sync** (2 rounds): `curl -s -X POST http://127.0.0.1:4949/driver/sync` × 2 (round 1 enrolls project, round 2 pulls scoped data)
4. **Inspector verify**: `curl -s "http://127.0.0.1:4949/driver/local-record?table=X&id=Y"`

---

## Pre-Run Cleanup

Before S01:

1. Read `.env.test` for Supabase credentials
2. Verify both devices ready: `GET /driver/ready` on ports 4948 and 4949
3. Query Supabase for all `VRF-*` projects: `GET /rest/v1/projects?name=like.VRF-%`
4. For each found project:
   - `POST localhost:4948/driver/remove-from-device` with `{"project_id": "<id>"}`
   - `POST localhost:4949/driver/remove-from-device` with `{"project_id": "<id>"}`
5. Hard-delete all VRF records from Supabase in FK teardown order
6. Log cleanup results in report

---

## Log Scanning Protocol

After every sync operation and every UI mutation:

1. `curl -s "http://127.0.0.1:3947/logs?since=<STEP_START>&level=error"` — runtime errors
2. `curl -s "http://127.0.0.1:3947/logs?since=<STEP_START>&category=sync"` — sync-specific issues
3. All errors recorded immediately in report with flow ID, timestamp, and full error text
4. Errors don't necessarily fail the flow (some may be warnings) — Claude uses judgment, but all are logged

---

## Report Protocol

File: `.claude/test_results/<run>/report.md`

Updated after **every flow** (not just per-tier):

### Report Sections

1. **Flow Results Table** — S01-S10 with PASS/FAIL/SKIP status, duration, notes
2. **Bugs Found** — Unexpected behavior even if flow passed (e.g., slow sync, extra error logs, unexpected widget states)
3. **Log Anomalies** — Errors or warnings from debug server, grouped by flow
4. **Supabase Verification Results** — Record counts per table after each flow (expected vs actual)
5. **Cross-Device Discrepancies** — Cases where admin and inspector data don't match
6. **Post-Run Sweep Results** — What the final VRF sweep found (should be 0; any non-zero is a FAIL)

The report is the **source of truth** for the run. If context gets compacted, the report preserves everything.

---

## Checkpoint Schema

File: `.claude/test_results/<run>/checkpoint.json`

Extended from T-flow checkpoint to include `ctx`:

```json
{
  "run_id": "2026-03-25_14-30",
  "suite": "sync",
  "platform": "dual (android:4948 + windows:4949)",
  "results_dir": ".claude/test_results/2026-03-25_14-30",
  "run_tag": "k1a2b",
  "completed": {
    "S01": "PASS",
    "S02": "PASS",
    "S03": "FAIL"
  },
  "next_flow": "S04",
  "ctx": {
    "projectId": "uuid",
    "project2Id": "uuid",
    "locationIds": ["uuid", "uuid"],
    "contractorIds": ["uuid", "uuid"],
    "equipmentIds": ["uuid", "uuid"],
    "bidItemIds": ["uuid"],
    "personnelTypeIds": ["uuid", "uuid", "uuid"],
    "entryId": "uuid",
    "entryContractorIds": ["uuid", "uuid"],
    "entryEquipmentIds": ["uuid", "uuid"],
    "entryPersonnelCountIds": ["uuid", "uuid", "uuid"],
    "entryQuantityIds": ["uuid"],
    "photoIds": ["uuid"],
    "formResponseIds": ["uuid"],
    "todoIds": ["uuid"],
    "calculationIds": ["uuid"],
    "assignmentId": "uuid"
  },
  "supabase_url": "https://...",
  "bugs": [],
  "observations": []
}
```

Note: Service role key is NOT stored in checkpoint — re-read from `.env.test` on resume.

---

## Edge Cases & Failure Handling

### ADB Flakiness (S08 only)
ADB commands can hang. For S08 (PDF export), if ADB hangs for 15s, Claude kills the command, records S08 as FAIL with "ADB timeout", and continues to S09. ADB is only needed for S08 — all other flows use HTTP driver only.

### Device Disconnects
Before each flow, Claude checks `/driver/ready` on both ports. If either device is unreachable, Claude pauses and asks user to reconnect rather than failing silently.

### Sync Errors
`POST /driver/sync` returns `{success, pushed, pulled, errors}`. If `errors` is non-empty, Claude logs in report but continues — some sync errors are transient. If `pushed: 0` when pushes expected, that's a FAIL.

### Already Logged In
Before login, Claude checks for `login_email_field`. If not found → device already logged in → skip login.

### Context Exhaustion
Compaction at S03/S06/S09 plus checkpoint.json with all IDs means Claude can resume even if context is fully compressed. Report on disk is the backstop.

---

## Dart Changes

Already applied this session (keep as-is):

- `lib/core/driver/driver_server.dart` — `DRIVER_PORT` dart-define override. Allows Windows inspector on port 4949.
- `lib/main_driver.dart` — Log message uses `${driverServer.port}` instead of hardcoded 4948.

No other Dart changes needed. Missing widget keys at runtime are handled by the /test skill's missing-key protocol.

---

## Skill & Registry Updates

### skill.md Changes

1. Tier alias: `sync → S01-S10` (replace old `node run-tests.js` reference)
2. Usage examples: `/test sync`, `/test S01`, `/test S01-S03`, `/test sync --resume`
3. New section: dual-device setup (ports 4948/4949, readiness check)
4. New section: Supabase verification (load .env.test, curl patterns)
5. Sync-specific compaction: pauses after S03, S06, S09

### registry.md Changes

1. New tier: "Sync Verification (S01-S10)" with all 10 flows
2. Remove old sync/L2/L3 references

### New File

`.claude/test-flows/sync-verification-guide.md` — companion reference with:
- Environment setup
- Supabase query patterns
- Cross-device sync protocol
- Pre-run cleanup procedure
- Post-run sweep (leftovers = FAIL)
- Log scanning protocol
- Report protocol
- FK teardown order
- Per-flow detailed steps (every widget key, every Supabase query, every verification)

---

## Detailed Flow Steps

### S01: Project Setup

**Admin device (port 4948):**

1. Navigate to `/project/new`
2. Enter: `project_name_field` = `VRF-Oakridge {tag}`, `project_number_field` = `VRF-{tag}-001`, `project_client_field` = `VRF-City of Oakridge {tag}`
3. Tap `project_save_button`, wait 2s
4. Sync admin, query Supabase for project by name → capture `projectId`
5. Navigate to `/project/{projectId}/edit`
6. Tap `project_locations_tab`, create 2 locations via `project_add_location_button` → `location_name_field` → `location_dialog_add`
7. Tap `project_contractors_tab`, create 2 contractors via `contractor_add_button` → `contractor_name_field` → `contractor_type_prime`/`contractor_type_sub` → `contractor_save_button`
8. Expand contractor card, create 2 equipment via `project_add_equipment_button` → `equipment_name_field` → `equipment_dialog_add`
9. Tap `project_payitems_tab`, create 1 bid item via `project_add_pay_item_button` → `pay_item_source_manual` → fields → `pay_item_dialog_save`
10. Navigate to `/settings`, tap `settings_personnel_types_tile`, create 3 personnel types
11. Navigate back to project edit, tap `project_assignments_tab`, tap `assignment_tile_{INSPECTOR_USER_ID}`, tap `project_save_button`
12. Sync admin

**Supabase verification**: Query all 7 tables, capture IDs into ctx

**Inspector device (port 4949):**
13. Sync inspector (2 rounds)
14. Verify projects, locations, contractors exist locally via `/driver/local-record`

**Second project for D2:**
15. Create `VRF-Unassign Test {tag}` project, assign inspector, sync both devices, capture `project2Id`

### S02: Daily Entry

**Admin device:**
1. Navigate to `/`, tap `add_entry_fab`
2. Select location, weather, enter temperatures and activities
3. Add 2 entry contractors, toggle equipment, add personnel counts, add quantity
4. Tap `entry_wizard_save_draft`, sync admin

**Supabase verification**: Query daily_entries, entry_contractors, entry_equipment, entry_personnel_counts, entry_quantities — capture all IDs

**Inspector**: Sync, verify entry exists locally

### S03: Photos

**Admin device:**
1. `POST /driver/inject-photo-direct` with test JPEG, entryId, projectId
2. Sync admin

**Supabase verification**: Query photos by entry_id, capture photoIds

**Inspector**: Sync, verify photo exists locally

**--- COMPACTION PAUSE ---**

### S04: Forms

**Admin device:**
1. Navigate to `/entry/{entryId}/edit`
2. Tap `report_add_form_button`, select 0582B form, fill header fields, save

**Supabase verification**: Query form_responses, capture formResponseIds

**Inspector**: Sync, verify form response exists locally

### S05: Todos

**Admin device:**
1. Navigate to `/toolbox`, tap `toolbox_todos_card`
2. Create todo via `todos_add_button` → fields → `todos_save_button`
3. Sync admin

**Supabase verification**: Query todo_items, capture todoIds

**Inspector**: Sync, verify todo exists locally

### S06: Calculator

**Admin device:**
1. Navigate to `/toolbox`, tap `toolbox_calculator_card`
2. Tap `calculator_hma_tab`, enter area/thickness/density, calculate, save
3. Sync admin

**Supabase verification**: Query calculation_history, capture calculationIds

**Inspector**: Sync, verify calculation exists locally

**--- COMPACTION PAUSE ---**

### S07: Update All

**Admin device**: Update project name, location, contractor, equipment, bid item, personnel type, daily entry activities, photo description, toggle equipment, increment personnel count, form response remarks, entry quantity, todo title. Sync admin.

**Supabase verification**: Spot-check key updates (project name contains "Phase 2", location updated, contractor updated)

**Inspector**: Sync, verify updated project name pulled

### S08: PDF Export

**Admin device:**
1. Navigate to entry, tap `report_export_pdf_button`, enter filename, save
2. Wait 5s for generation
3. `adb pull` IDR PDF from device (15s timeout)
4. If pull succeeds: run `pdftk dump_data_fields_utf8`, verify field values match post-update data
5. Export 0582B PDF similarly, verify header fields

If ADB times out → FAIL S08, continue to S09.

### S09: Delete Cascade

**Admin device:**
1. Navigate to `/projects`, tap `project_remove_{projectId}`
2. Two-step delete dialog: continue → type project name → delete forever
3. Sync admin

**Supabase verification**: `verifyCascadeDelete` — all 14 child tables soft-deleted, project_assignments hard-deleted

**Inspector**: Sync, check for `deletion_notification_banner`, verify project gone from local DB

**--- COMPACTION PAUSE ---**

### S10: Unassignment + Cleanup

**Inspector**: Verify project2 exists locally

**Admin device:**
1. Navigate to project2 edit, tap assignments tab, toggle off inspector, save
2. Sync admin

**Supabase verification**: Project2 still exists (not deleted), assignment row hard-deleted

**Inspector**: Sync, verify project2 removed from local DB

**Cleanup:**
1. Admin deletes project2 via UI (same delete dialog flow)
2. Sync admin

**Post-run sweep**: Query all VRF tables in Supabase. Any remaining records → FAIL.
