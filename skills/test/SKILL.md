---
name: test
description: Run E2E test flows via HTTP driver automation
---

# /test — HTTP Driver Test Skill

## Overview
Runs end-to-end test flows against the running app via HTTP driver endpoints (port 4948).
The app must be launched with `main_driver.dart` entrypoint. Main Claude executes all
flows directly via curl — no sub-agents, no orchestrator layer.

## HARD RULES — NEVER SKIP

After **EVERY flow**, complete this checklist:
- [ ] Driver response checked (200 = pass, 404/408 = fail)
- [ ] Logs scanned: `curl -s "http://127.0.0.1:3947/logs?since=<START>&level=error"`
- [ ] Widget tree verified (for data-creation flows): `/driver/tree?filter=<expected>`
- [ ] Sync waited + verified (for mutation flows)
- [ ] `checkpoint.json` updated
- [ ] `registry.md` Status + Last Run updated

After **EVERY tier**, additionally:
- [ ] `report.md` updated with tier results table
- [ ] Screenshot review: only view screenshots for FAILED flows

### HARD RULES — SYNC FLOWS

These rules are **non-negotiable** for S01-S10. Violating them wastes cycles and requires user correction.

1. **NEVER use `POST /driver/sync`** — sync ONLY via UI: tap `settings_nav_button` → tap `settings_sync_button`, wait 3s, tap again if needed.
2. **NEVER use `GET /driver/local-record` for verification** — navigate the inspector app to the screen where the data appears and take a screenshot. Visual verification only.
3. **After text entry on Android**, call `POST /driver/dismiss-keyboard` before tapping any buttons. The keyboard covers the bottom of the screen and taps return 200 but never reach the widget.
4. **After every navigation tap**, verify arrival with `/driver/find?key=<sentinel>` where sentinel is a key known to exist on the target screen.
5. **Read `lib/shared/testing_keys/*.dart` before each flow** — do not waste cycles querying `/driver/tree` for keys that are already documented.
6. **Check debug server logs after every sync**: `curl -s "http://127.0.0.1:3947/logs?since=<START>&level=error"` AND `curl -s "http://127.0.0.1:3947/logs?since=<START>&category=sync"`.
7. **Toolbox sub-screens need TWO backs to reach dashboard** — Todos/Calculator/Gallery are inside Toolbox, which is itself a sub-screen of Dashboard. Press back once to reach Toolbox hub, again to reach Dashboard.

## Credentials
`.claude/test-credentials.secret` — gitignored JSON with admin + inspector accounts.

## Usage

```
/test                              # Show available tiers
/test auth                         # T01-T04 (Auth & Smoke)
/test project-setup                # T05-T14 (Project Setup)
/test entries                      # T15-T23 (Daily Entry Creation)
/test lifecycle                    # T24-T30 (Entry Lifecycle)
/test toolbox                      # T31-T40 (Toolbox)
/test pdf                          # T41-T43 (PDF & Export)
/test settings                     # T44-T52 (Settings & Profile)
/test admin                        # T53-T58 (Admin Operations)
/test edits                        # T59-T67 (Edit Mutations)
/test deletes                      # T68-T77 (Delete Operations)
/test sync                         # S01-S10 (Claude-driven dual-device)
/test S01                          # Single sync flow
/test S01-S03                      # Range of sync flows
/test sync --resume                # Resume from checkpoint
/test permissions                  # T85-T91 (Role Verification)
/test navigation                   # T92-T96 (Nav & Dashboard)
/test T03                          # Single flow
/test T15-T23                      # Range
/test full                         # All tiers, sequential
/test --resume                     # Resume from checkpoint
/test admin --role admin           # Explicit role
/test permissions --role inspector # Inspector role
```

## Tier Alias Map

```
auth         → T01-T04
project-setup → T05-T14
entries      → T15-T23
lifecycle    → T24-T30
toolbox      → T31-T40
pdf          → T41-T43
settings     → T44-T52
admin        → T53-T58
edits        → T59-T67
deletes      → T68-T77
sync         → S01-S10 (Claude-driven dual-device verification)
permissions  → T85-T91
navigation   → T92-T96
```

## Prerequisites (automated)
1. Run: `pwsh -File tools/start-driver.ps1 -Platform windows` (or `-Platform android`)
2. Script handles: stale process cleanup, debug server, app launch, and readiness gate
3. No manual setup required

### Pre-flight Cleanup (built into start-driver.ps1)
- **Android**: Force-stops app on all devices, clears stale ADB forwards/reverses (frees port 4948)
- **Windows**: Kills `construction_inspector` process
- **IMPORTANT**: Use `adb forward` (host→device) for driver port, NOT `adb reverse` (which binds the port on-device and conflicts with the driver server)

## Execution Model

Main Claude executes all flows directly — no sub-agents dispatched.

1. **Setup**: Create timestamped results dir, read credentials, record start time
2. **Per-flow**: Execute curl commands → check response → scan logs → update checkpoint
3. **Per-tier**: Update report.md with tier results table
4. **Checkpoint**: Written after every flow for resume capability
5. **Report**: Updated after every tier (not just at the end)

### Setup
```bash
RESULTS_DIR=".claude/test_results/$(date +%Y-%m-%d_%H-%M)"
mkdir -p "$RESULTS_DIR"
```

Read credentials from `.claude/test-credentials.secret`.
Read testing keys from `lib/shared/testing_keys/*.dart` as needed per flow.

### Checkpoint File
Write `.claude/test_results/<run>/checkpoint.json` **after every flow**:
```json
{
  "run_id": "2026-03-20_10-00",
  "platform": "windows",
  "results_dir": ".claude/test_results/2026-03-20_10-00",
  "current_role": "admin",
  "completed": {
    "admin": { "T01": "PASS", "T02": "FAIL" },
    "inspector": {}
  },
  "next_flow": "T03",
  "bugs": [
    { "role": "admin", "flow": "T02", "desc": "widget not found", "screenshot": "admin-T02-fail.png" }
  ],
  "observations": [
    "Sync took 8s on T01 — slower than expected"
  ]
}
```

### Per-Flow Execution
For each flow:
1. Record start time: `pwsh -Command "Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ'"`
2. Execute driver steps (curl commands — see HTTP Driver Endpoints below)
3. `sleep 1` between navigation actions
4. After data mutation, poll sync status (30s timeout):
   ```bash
   for i in $(seq 1 30); do
     STATUS=$(curl -s http://127.0.0.1:3947/sync/status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('state','unknown'))" 2>/dev/null || echo "error")
     if [ "$STATUS" = "completed" ] || [ "$STATUS" = "idle" ]; then break; fi
     sleep 1
   done
   ```
5. Check logs: `curl -s "http://127.0.0.1:3947/logs?since=<START>&level=error"`
6. Take screenshot: `curl -s http://127.0.0.1:4948/driver/screenshot --output "$RESULTS_DIR/<role>-<flow>.png"`
7. Update `checkpoint.json`
8. Update `.claude/test-flows/registry.md` (Status + Last Run)

## Failure Detection (Without Viewing Screenshots)

Use these signals — do NOT view screenshots inline unless failure is detected:

| Signal | Meaning | Action |
|--------|---------|--------|
| Driver returns 404 | Widget not found | Record missing key, FAIL flow |
| Driver returns 408 | Wait timeout | FAIL flow |
| `/logs?level=error` has entries | Runtime error | FAIL flow, log the error |
| `/driver/tree?filter=<text>` missing | Expected data absent | FAIL flow |
| `/driver/find?key=X` → `exists: false` | Widget doesn't exist | FAIL flow |
| Sync doesn't reach idle in 30s | Sync failure | Capture `/sync/status`, FAIL flow |

**Screenshots**: Save to disk ALWAYS. View ONLY when a failure signal is detected.

## Compaction Protocol (Every 2 Tiers)

After 2 tiers complete:
1. Write full checkpoint with all results so far
2. Update report.md with both tiers' results
3. Output: **"Checkpoint written. Say 'continue' to proceed."**

On resume (after compaction or `--resume`):
1. Read `.claude/test_results/` to find the latest run directory
2. Read `checkpoint.json` from that directory
3. Read credentials: `.claude/test-credentials.secret`
4. Read last screenshot path (if failure investigation needed)
5. **Restore screen state on both devices:**
   - Check both devices are reachable: `curl -s http://127.0.0.1:4948/driver/ready` and `curl -s http://127.0.0.1:4949/driver/ready`
   - Navigate both to dashboard: tap `dashboard_nav_button`
   - Verify correct project is selected (screenshot or `/driver/find`)
   - Check debug server is up: `curl -s http://127.0.0.1:3947/logs?limit=1`
6. Continue from `next_flow`

**NEVER view screenshots inline unless failure detected.**

## Missing-Key Protocol

When a flow fails with 404 (widget not found):
1. Record the missing key name
2. Continue executing remaining flows in the tier
3. After tier completes, spawn a **background** Task agent (`frontend-flutter-specialist-agent`) to:
   - Find the widget in presentation code
   - Add the key constant to the appropriate `testing_keys/*.dart` file
   - Add the `Key` to the widget
4. Continue testing other tiers while agent works
5. After agent completes + app restart (`POST /driver/hot-restart`), retry failed flows

## Role Handling

Always explicit — no automatic role switching.

| Flag | Behavior |
|------|----------|
| `--role admin` | Default if unspecified |
| `--role inspector` | Inspector account from credentials |

Inspector-specific flows: T85-T91 (Role Verification tier).

### Role Switch Procedure
1. Sign out: `settings_nav_button` → `settings_sign_out_tile` → `sign_out_confirm_button`
2. Wait for `login_screen`
3. Log in with target role credentials
4. Update `checkpoint.json` with new `current_role`

## Report Format

Write/update `.claude/test_results/<run>/report.md` after each tier:

```markdown
# Test Run Report — <date> <time>

## <Tier Name> Results
| Flow | Status | Notes |
|------|--------|-------|
| T01  | PASS   |       |
| T02  | FAIL   | widget not found: some_key |

## Bugs Found
- **[BUG]** <description> — screenshot: `admin-T02-fail.png`

## Observations
- Sync averaged 3s per flow
```

## Key Reference: Testing Keys

All widget keys live in `lib/shared/testing_keys/` (13 files). Read the relevant file
before interacting with a feature. Keys are discoverable at runtime via
`GET /driver/find?key=KEY_NAME`.

| File | Class | Domain |
|------|-------|--------|
| `auth_keys.dart` | `AuthTestingKeys` | Login, registration |
| `common_keys.dart` | `CommonTestingKeys` | Shared widgets (dialogs, snackbars) |
| `contractors_keys.dart` | `ContractorsTestingKeys` | Contractor management |
| `entries_keys.dart` | `EntriesTestingKeys` | Daily entries |
| `locations_keys.dart` | `LocationsTestingKeys` | Location management |
| `navigation_keys.dart` | `NavigationTestingKeys` | Bottom nav, drawer |
| `photos_keys.dart` | `PhotosTestingKeys` | Photo capture/gallery |
| `projects_keys.dart` | `ProjectsTestingKeys` | Project CRUD |
| `quantities_keys.dart` | `QuantitiesTestingKeys` | Quantity tracking |
| `settings_keys.dart` | `SettingsTestingKeys` | App settings |
| `sync_keys.dart` | `SyncTestingKeys` | Sync UI |
| `testing_keys.dart` | — | Barrel export |
| `toolbox_keys.dart` | `ToolboxTestingKeys` | Toolbox hub |

## Finding E2E Projects by Name

Project cards use dynamic keys with UUIDs (`project_card_<uuid>`). To find them:
```bash
curl -s "http://127.0.0.1:4948/driver/tree?depth=15" | python3 -c "
import sys, json
tree = json.load(sys.stdin).get('tree', '')
for line in tree.split('\n'):
    if 'E2E' in line or 'project_card_' in line or 'project_edit_menu' in line:
        print(line.strip())
"
```

## HTTP Driver Endpoints (port 4948)

Binds to loopback (127.0.0.1) only — no auth required.

| Method | Endpoint | Body/Params |
|--------|----------|-------------|
| GET | /driver/ready | — |
| GET | /driver/find?key=X | — |
| GET | /driver/screenshot | — |
| GET | /driver/tree?depth=N | — |
| POST | /driver/tap | {"key": "X"} |
| POST | /driver/text | {"key": "X", "text": "Y"} |
| POST | /driver/scroll | {"key": "X", "dx": 0, "dy": -300} — **key must be on the scrollable widget itself** |
| POST | /driver/scroll-to-key | {"scrollable": "X", "target": "Y", "maxScrolls": 20} — scrollable must have a ValueKey |
| POST | /driver/back | {} |
| POST | /driver/wait | {"key": "X", "timeoutMs": 10000} |
| POST | /driver/inject-photo | {"data": "<base64>", "filename": "test.jpg"} |
| POST | /driver/inject-photo-direct | {"base64Data": "...", "filename": "...", "entryId": "...", "projectId": "..."} |
| POST | /driver/inject-file | {"data": "<base64>", "filename": "doc.pdf"} |
| POST | /driver/hot-restart | {} |

> `/driver/screenshot` returns `image/png` binary. Use `curl --output <path>`.

### Scrollable Keys (for /driver/scroll)

The `key` parameter in `/driver/scroll` and `/driver/scroll-to-key` must target a **ValueKey on the scrollable widget itself** — NOT a child widget. Targeting a child (e.g., a TextField or Card) will cause the child to consume the gesture and the page won't scroll.

| Screen | Scroll Key | Notes |
|--------|-----------|-------|
| Entry editor (create/edit) | `entry_editor_scroll` | Main entry form |
| Entry review/detail | `entry_review_scroll` | Entry report view |
| Project details form | `project_details_scroll` | Name, number, client fields |
| Project locations list | `project_locations_list` | Locations tab in project edit |
| Project contractors list | `project_contractors_list` | Contractors tab |
| Project bid items list | `project_bid_items_list` | Pay items tab |
| Project assignments list | `project_assignments_list` | Assignments tab |
| Settings screen | `settings_list` | Main settings ListView |

**Example — scroll entry editor down 500px:**
```bash
curl -s -X POST http://127.0.0.1:4948/driver/scroll -d '{"key":"entry_editor_scroll","dx":0,"dy":-500}'
```

**Example — scroll-to-key to find save button:**
```bash
curl -s -X POST http://127.0.0.1:4948/driver/scroll-to-key -d '{"scrollable":"entry_editor_scroll","target":"entry_wizard_save_draft","maxScrolls":10}'
```

## Flow Dependencies

**Tier 0 (T01-T04)** — Auth & Smoke: Login, navigate, sign out, inspector login
**Tier 1 (T05-T14)** — Project Setup: T05 creates "E2E Test Project", T06-T14 add sub-entities
**Tier 2 (T15-T23)** — Daily Entry Creation: Creates entries on the T05 project
**Tier 3 (T24-T30)** — Entry Lifecycle: Edit/submit/approve entries from Tier 2
**Tier 4 (T31-T40)** — Toolbox: Calculator, forms, gallery, todos
**Tier 5 (T41-T43)** — PDF & Export: Generate/view PDFs for Tier 2 entries
**Tier 6 (T44-T52)** — Settings & Profile
**Tier 7 (T53-T58)** — Admin Operations
**Tier 8 (T59-T67)** — Edit Mutations: Edit entities from earlier tiers
**Tier 9 (T68-T77)** — Delete Operations: Delete entities (run last before cleanup)
**Sync (S01-S10)** — Claude-driven dual-device sync verification (admin:4948, inspector:4949)
  S01 (Project Setup) → S02 (Daily Entry) → S03 (Photos) → S04 (Forms) → S05 (Todos) → S06 (Calculator) → S07 (Update All) → S08 (PDF Export) → S09 (Delete Cascade) → S10 (Unassignment + Cleanup)
**Tier 11 (T85-T91)** — Role Verification (inspector role)
**Tier 12 (T92-T96)** — Nav & Dashboard

## Sync Verification (Dual-Device) — S01-S10

Claude drives two devices via HTTP driver endpoints and verifies data in Supabase via REST API.

**Reference guide:** `.claude/test-flows/sync-verification-guide.md`

### Setup
- Admin device: port 4948 (Android or Windows)
- Inspector device: port 4949 (second device)
- Supabase credentials: `tools/debug-server/.env.test` (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
- Test credentials: `.claude/test-credentials.secret`

### Driver Endpoints Used
All standard endpoints (tap, text, wait, scroll, etc.) plus:
- `POST /driver/dismiss-keyboard` — unfocus + hide soft keyboard (call before tapping buttons after text entry)
- `POST /driver/dismiss-overlays` — clear snackbars and material banners blocking taps
- `GET /driver/current-route` — returns `{route, hasBottomNav, canPop}` for navigation verification
- `GET /driver/find?key=X` — enhanced: now returns `enabled` (bool) and `visible` (bool) fields
- `POST /driver/remove-from-device` — remove project from device locally
- `POST /driver/inject-photo-direct` — inject photo with entry/project association

### BANNED Endpoints (Sync Flows)

These endpoints exist but must **NEVER** be used during sync verification (S01-S10):

| Endpoint | Why Banned | Use Instead |
|----------|-----------|-------------|
| `POST /driver/sync` | Bypasses UI, hides sync bugs | Tap `settings_nav_button` → `settings_sync_button` |
| `GET /driver/local-record` | Bypasses UI verification | Navigate to screen + screenshot |

### Cross-Device Sync Protocol (UI-Driven, 4-Step)
After every data mutation:
1. **Admin sync via UI**: tap `settings_nav_button` → tap `settings_sync_button` → wait 3s
2. **Supabase verify**: curl REST API to confirm data arrived in the cloud
3. **Inspector sync via UI** (2 rounds): tap `settings_nav_button` → tap `settings_sync_button` → wait 3s → tap `settings_sync_button` again → wait 3s
4. **Inspector UI verify**: navigate the inspector app to the screen where synced data should appear → take screenshot to confirm

### Supabase Verification Pattern
```bash
curl -s "${SUPABASE_URL}/rest/v1/<table>?<filters>" \
  -H "apikey: ${KEY}" \
  -H "Authorization: Bearer ${KEY}" \
  -H "Accept: application/json"
```

### Per-Run Unique Data Tag
Every run generates a 5-char alphanumeric tag. All test data uses prefix `VRF-` with this tag embedded in names to avoid collisions.

### Compaction Pauses
After S03, S06, and S09 — checkpoint written, user prompted to continue.

### Post-Run Sweep
After S10, query all 17 synced tables for `VRF-*` records. Any remaining = FAIL.

## Teardown

After test run completes:
```
pwsh -File tools/stop-driver.ps1
```
Add `-IncludeDebugServer` to also kill the debug server.

## Error Handling
- **Driver unreachable:** retry once after 2s, then FAIL
- **Element not found (404):** take screenshot, wait 3s, retry once, then FAIL
- **Wait timeout (408):** FAIL flow, continue
- **Sync timeout (30s):** capture /sync/status, FAIL flow, continue
- **App crash:** detect via /driver/ready timeout, capture last logs, try `POST /driver/hot-restart`

## Flow Registry
`.claude/test-flows/registry.md` — unified registry with all flows and run history.

## Test Data Safety
- All test projects use "E2E " prefix
- **CRITICAL**: Always use timestamped project names (e.g., "E2E Test 1711046095") to avoid collisions with prior runs
- When a prior E2E project already exists, REUSE it instead of creating a new one (tap into it, verify sub-entities)
- Cleanup: `pwsh -File tools/verify-sync.ps1 -Cleanup -ProjectName "E2E*" -DryRun` (still valid for data cleanup; sync correctness verification is now Claude-driven — see `/test sync` (S01-S10) or run `node tools/debug-server/run-tests.js --cleanup-only` for data cleanup only)

## Android Gotchas

### Keyboard Blocking
After entering text in any field on Android, the soft keyboard covers the bottom ~40% of the screen. Taps on widgets behind the keyboard return `200 {tapped: true}` but the tap never reaches the widget.

**Fix:** Always call `POST /driver/dismiss-keyboard` before tapping buttons after text entry:
```bash
curl -s -X POST http://127.0.0.1:4948/driver/dismiss-keyboard -H "Content-Type: application/json" -d '{}'
sleep 0.3
curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"save_button"}'
```

### Snackbar Blocking
Persistent snackbars (e.g., sync errors) overlay the bottom of the screen and block taps on project cards and action buttons.

**Fix:** Call `POST /driver/dismiss-overlays` to clear all snackbars and banners:
```bash
curl -s -X POST http://127.0.0.1:4948/driver/dismiss-overlays -H "Content-Type: application/json" -d '{}'
```

### Toolbox Navigation Depth
Toolbox sub-screens (Todos, Calculator, Gallery, Forms) are **two levels deep** from Dashboard:
- Dashboard → Toolbox Hub → Sub-screen
- Back from sub-screen → Toolbox Hub (NOT dashboard)
- Back from Toolbox Hub → Dashboard
- Bottom nav is NOT visible inside Toolbox sub-screens

Always use `POST /driver/back` twice, or tap `dashboard_nav_button` to return to dashboard directly.

## Error Recovery Protocol

### Tap returns 200 but nothing happens
1. Check `GET /driver/current-route` — you may be on the wrong screen
2. Call `POST /driver/dismiss-keyboard` — keyboard may be blocking
3. Call `POST /driver/dismiss-overlays` — snackbar may be blocking
4. Verify widget with `GET /driver/find?key=X` — check `enabled` and `visible` fields
5. Take screenshot to visually confirm state

### Widget not found (404)
1. Check you are on the correct screen: `GET /driver/current-route`
2. Try scrolling: the widget may be off-screen (use `POST /driver/scroll-to-key`)
3. Read `testing_keys/*.dart` to verify the exact key name
4. As last resort, use `/driver/tree?filter=<partial>` to discover the actual key

### Sync appears to fail
1. Check debug server logs: `curl -s "http://127.0.0.1:3947/logs?since=<START>&category=sync"`
2. Check for error-level logs: `curl -s "http://127.0.0.1:3947/logs?since=<START>&level=error"`
3. Dismiss any error snackbars: `POST /driver/dismiss-overlays`
4. Retry sync via UI (settings_nav_button → settings_sync_button)
5. If still failing, take screenshot and record as bug

## Navigation Reference

### Bottom Nav Destinations
| Key | Destination | Sentinel Key |
|-----|------------|--------------|
| `dashboard_nav_button` | Dashboard/Home | `dashboard_new_entry_button` |
| `calendar_nav_button` | Calendar view | `calendar_nav_button` (stays highlighted) |
| `projects_nav_button` | Projects list | `project_create_button` |
| `settings_nav_button` | Settings | `settings_sync_button` |

### Common Navigation Patterns
| Action | Sequence |
|--------|----------|
| Sync via UI | `settings_nav_button` → `settings_sync_button` (wait 3s) |
| Create entry | `dashboard_nav_button` → `dashboard_new_entry_button` |
| Edit project | `projects_nav_button` → `project_edit_menu_item_<id>` |
| Open toolbox | `dashboard_nav_button` → `dashboard_toolbox_card` |
| Open todos | Toolbox → `toolbox_todos_card` |
| Open calculator | Toolbox → `toolbox_calculator_card` |
| Return to dashboard from toolbox sub-screen | `POST /driver/back` x2, or tap `dashboard_nav_button` |

### Project-Related Key Disambiguation
| Key Pattern | Purpose |
|-------------|---------|
| `project_card_<id>` | Tap to select/open project |
| `project_edit_menu_item_<id>` | Tap to enter project edit mode |
| `project_create_button` | Create new project (also aliased as `add_project_fab`) |
| `project_save_button` | Save project edits |
| `project_remove_<id>` | Delete project (triggers two-step confirmation) |

## Windows Bash Constraints
- **NO `jq`** — use `python3 -c "import json..."` for JSON parsing
- **NO multi-line heredocs with curl**
- **ALWAYS `pwsh -Command "..."`** for PowerShell
- Special chars (`!`, `$`) in curl JSON: use double-quoted -d flag
