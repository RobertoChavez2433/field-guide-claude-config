# Sync Verification Framework

> Shared setup, patterns, and protocols for executing `/test sync` (S01-S19).
> This file is loaded once at the start of any sync run. Individual flow steps
> are in the companion `flows-*.md` files.

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

> See `skills/test/references/driver-and-navigation.md` for the full scrollable keys table, driver endpoints, and screen sentinels.

Key reminder: The `key` parameter in `/driver/scroll` must target the **scrollable widget itself** (e.g., `entry_editor_scroll`), NOT a child widget. Most-used keys during sync flows: `entry_editor_scroll`, `project_details_scroll`, `project_contractors_list`, `settings_list`.

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

> See `skills/test/references/driver-and-navigation.md` for the full navigation map, common navigation patterns, and project key disambiguation.

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

> See `skills/test/references/driver-and-navigation.md` for the full Android gotchas reference (snackbar blocking, toolbox depth).

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
