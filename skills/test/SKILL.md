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

### Per-Flow Checklist
- [ ] Driver response checked (200 = pass, 404/408 = fail)
- [ ] Verify expected state after action (use `/driver/wait` or `/driver/find`, NOT sleep)

### Per-Tier Checklist
- [ ] Error log scan: `curl -s "http://127.0.0.1:3947/logs/errors?since=<TIER_START>"`
- [ ] `checkpoint.json` updated with all flow results
- [ ] `report.md` updated with tier results table
- [ ] Screenshot review: only view screenshots for FAILED flows

### Per-Run Outputs (only two files)
- **`checkpoint.json`** — machine-readable state, updated per-tier
- **`report.md`** — human-readable results, updated per-tier
- Tier files are static reference docs — do NOT update them during runs
- Bugs are tracked in GitHub Issues

### HARD RULES — SYNC FLOWS

These rules are **non-negotiable** for S01-S21. Violating them wastes cycles and requires user correction.

1. **NEVER use `POST /driver/sync`** — sync ONLY via UI: tap `settings_nav_button` → tap `settings_sync_button`, wait for `sync-status` completion, tap again if the flow requires a second pull pass.
2. **Every sync mutation must be proven in 5 places when applicable**:
   - sender UI action
   - sender SQLite row / queue state
   - Supabase row or storage object
   - receiver SQLite row / queue state
   - receiver UI state
3. **Use `GET /driver/local-record` and `GET /driver/change-log` as required diagnostics**, not as a replacement for UI verification. UI remains mandatory, but SQLite and queue verification are also mandatory.
4. **After text entry on Android**, call `POST /driver/dismiss-keyboard` before tapping any buttons. The keyboard covers the bottom of the screen and taps return 200 but never reach the widget.
5. **After every navigation tap**, verify arrival with `/driver/find?key=<sentinel>` where sentinel is a key known to exist on the target screen.
6. **Read `lib/shared/testing_keys/*.dart` before each flow** — do not waste cycles querying `/driver/tree` for keys that are already documented.
7. **Check debug server logs after every sync**:
   - `curl -s "http://127.0.0.1:3947/logs/errors?since=<START>"`
   - `curl -s "http://127.0.0.1:3947/logs?since=<START>&category=sync&format=text"`
8. **Toolbox sub-screens need TWO backs to reach dashboard** — Todos/Calculator/Gallery are inside Toolbox, which is itself a sub-screen of Dashboard. Press back once to reach Toolbox hub, again to reach Dashboard.

## Credentials
`.claude/test-credentials.secret` — gitignored JSON with admin + inspector accounts.

**WARNING: Special characters in passwords** — The `!` and `$` characters in credential values trigger bash history/variable expansion inside single-quoted curl `-d` strings. Always use `--data-raw` with escaped double quotes for credential fields:
```bash
# WRONG — ! triggers history expansion in bash
curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key": "login_password_field", "text": "!T1esr11993"}'

# CORRECT — --data-raw with escaped JSON
curl -s -X POST http://127.0.0.1:4948/driver/text --data-raw "{\"key\": \"login_password_field\", \"text\": \"!T1esr11993\"}"
```

## Bash Tool Constraints

### Variables Do NOT Persist Between Calls
Each `Bash` tool invocation starts a **fresh shell**. Variables set in one call do not exist in the next.

```bash
# WRONG — ID is empty in the second Bash call
# Call 1:
TODO_ID="abc-123"
# Call 2 (separate Bash invocation):
curl -s -X POST .../tap -d "{\"key\":\"todo_checkbox_${TODO_ID}\"}"  # TODO_ID is empty!

# CORRECT — inline the value, or chain in one call
curl -s -X POST .../tap -d '{"key":"todo_checkbox_abc-123"}'

# CORRECT — chain commands in one Bash call with &&
TODO_ID="abc-123" && curl -s -X POST .../tap -d "{\"key\":\"todo_checkbox_${TODO_ID}\"}"
```

When you discover a dynamic ID (project UUID, entry UUID, todo UUID), either:
1. **Inline it directly** in subsequent curl calls in the same Bash invocation
2. **Chain all commands that need the ID** in a single `&&`-joined Bash call
3. **Copy-paste the literal value** into the next Bash call — do not reference a variable from a prior call

### Wait-Then-Act, Not Sleep-Then-Act
**NEVER** use `sleep N` followed by an action hoping the UI is ready. **ALWAYS** use `/driver/wait` to confirm the target widget exists before interacting with it.

```bash
# WRONG — blind sleep, widget may not be ready
curl -s -X POST .../tap -d '{"key":"add_button"}'
sleep 1
curl -s -X POST .../text -d '{"key":"name_field","text":"foo"}'

# CORRECT — wait confirms widget exists before acting
curl -s -X POST .../tap -d '{"key":"add_button"}'
curl -s -X POST http://127.0.0.1:4948/driver/wait -d '{"key":"name_field","timeoutMs":5000}'
curl -s -X POST .../text -d '{"key":"name_field","text":"foo"}'
```

The **only** acceptable `sleep` is `sleep 0.3` between rapid sequential text entries on the same screen (where all fields are already rendered).

### Dialog Reopen Pattern
After saving/closing a dialog, the UI needs a frame to rebuild before the same dialog can be reopened. Always verify the dialog closed, then verify the add button is ready, then verify the dialog reopened:

```bash
# Save first dialog
curl -s -X POST .../tap -d '{"key":"dialog_save_button"}'
# Wait for dialog to close — verify by checking a NON-dialog widget reappears
curl -s -X POST http://127.0.0.1:4948/driver/wait -d '{"key":"add_button","timeoutMs":5000}'
# Now reopen
curl -s -X POST .../tap -d '{"key":"add_button"}'
# Verify dialog opened
curl -s -X POST http://127.0.0.1:4948/driver/wait -d '{"key":"dialog_name_field","timeoutMs":5000}'
# Now safe to interact
curl -s -X POST .../text -d '{"key":"dialog_name_field","text":"second item"}'
```

## Reference Loading

Before executing, read the files mapped to your command. Load reference files on first use, then as-needed.

| Command | Files to Read |
|---|---|
| Any tier (first use) | `skills/test/references/driver-and-navigation.md` + `skills/test/references/debug-server-and-logs.md` |
| `auth`, `project-setup` | `test-flows/tiers/setup-and-auth.md` |
| `entries`, `lifecycle` | `test-flows/tiers/entry-crud.md` |
| `toolbox`, `pdf` | `test-flows/tiers/toolbox-and-pdf.md` |
| `pay-app`, `exports` | `test-flows/tiers/pay-app-and-exports.md` + `test-flows/tiers/toolbox-and-pdf.md` |
| `settings`, `admin` | `test-flows/tiers/settings-and-admin.md` |
| `edits`, `deletes` | `test-flows/tiers/mutations.md` |
| `permissions`, `navigation` | `test-flows/tiers/verification.md` |
| `sync` or `S01-S21` | `test-flows/sync/framework.md` + relevant flow group file (see below) |
| Single flow (e.g., `T15`) | Tier file containing that flow |
| `full` or `--resume` | `test-flows/flow-dependencies.md` + tier files as you reach each tier |
| Manual flows | `test-flows/tiers/manual-flows.md` |

### Sync Flow Group Files
| Flows | File | Notes |
|---|---|---|
| S01-S03 | `test-flows/sync/flows-S01-S03.md` | Compaction pause after S03 |
| S04-S06 | `test-flows/sync/flows-S04-S06.md` | Compaction pause after S06 |
| S07-S10 | `test-flows/sync/flows-S07-S10.md` | Compaction pause after S09 |
| S11-S21 | `test-flows/sync/flows-S11-S19.md` | Advanced sync flows, exports, support, consent |

## Pre-Run Data Verification

Before starting a `/test full` run, verify the app state is suitable for testing:

### Check for Prior E2E Projects
```bash
curl -s "http://127.0.0.1:4948/driver/tree?depth=15" | python3 -c "
import sys, json, re
tree = json.load(sys.stdin).get('tree', '')
cards = re.findall(r'project_card_[a-f0-9-]+', tree)
print(f'Found {len(cards)} project cards')
for c in cards: print(f'  {c}')
"
```

### Decision Tree
- **0 projects**: Clean slate — proceed with T05 (create fresh)
- **E2E project exists from today**: Reuse it — skip T05, verify sub-entities exist, continue from first missing tier
- **E2E project exists from prior day**: Create fresh with new timestamp — old project may have stale data

### Verifying Freshness of Pre-Existing Data
When an entity already exists (e.g., entry with contractors from a prior run), verify it's usable:
1. Check the data is associated with the correct project (not a different E2E run)
2. Confirm sub-entities match what the current tier expects (e.g., 2 locations, 2 contractors)
3. Mark the flow as `PASS (pre-existing)` in the checkpoint — do NOT mark as `SKIP`

## Usage

```
/test                              # Show available tiers
/test auth                         # T01-T04 (Auth & Smoke)
/test project-setup                # T05-T14 (Project Setup)
/test entries                      # T15-T23 (Daily Entry Creation)
/test lifecycle                    # T24-T30 (Entry Lifecycle)
/test toolbox                      # T31-T40 (Toolbox)
/test pdf                          # T41-T43 (PDF & Export)
/test pay-app                      # P01-P06 (Pay App & Exported-History)
/test exports                      # P01-P06 (Pay App & Exported-History)
/test settings                     # T44-T52 (Settings & Profile)
/test admin                        # T53-T58 (Admin Operations)
/test edits                        # T59-T67 (Edit Mutations)
/test deletes                      # T68-T77 (Delete Operations)
/test sync                         # S01-S21 (Claude-driven dual-device + full SQLite/change_log/Supabase verification)
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
pay-app      → P01-P06
exports      → P01-P06
settings     → T44-T52
admin        → T53-T58
edits        → T59-T67
deletes      → T68-T77
sync         → S01-S21 (dual-device verification + SQLite/change_log/Supabase/storage proofs + sync-mode coverage)
permissions  → T85-T91
navigation   → T92-T96
```

## Pay App / Export Coverage

Supplemental flows `P01-P06` in `test-flows/tiers/pay-app-and-exports.md`
cover:

- exported-artifact history visibility
- same-range replace with pay-app number preservation
- overlap-block behavior
- pay-app delete propagation
- contractor comparison import plus discrepancy PDF export
- saved pay-app artifact sync/delete verification

## Prerequisites (automated)
1. Run: `pwsh -File tools/start-driver.ps1 -Platform windows` (or `-Platform android`)
2. Script handles: stale process cleanup, driver build freshness checks, Android install reuse, app launch, and readiness gate
3. No manual setup required

### Smart Driver Startup
- Android driver startup now reuses the last good driver APK by default.
- A rebuild happens only when tracked driver inputs changed (`lib/`, `assets/`, `android/`, `pubspec.*`, `.env`) or when `-ForceRebuild` is passed.
- Android reinstall is skipped when the cached driver build already matches the connected device install.
- Dual-instance sync runs can launch the inspector desktop app on port `4949`:
  `pwsh -File tools/start-driver.ps1 -Platform windows -DriverPort 4949`

### Mid-Test Rebuilds (after code fixes)

**CRITICAL: NEVER call `build.ps1` without `-Driver` during testing.** The default is `-BuildType release`, which produces a release artifact instead of a driver build.

| Scenario | Command |
|----------|---------|
| Android relaunch (reuse if fresh) | `pwsh -File tools/start-driver.ps1 -Platform android` |
| Android force rebuild + reinstall | `pwsh -File tools/start-driver.ps1 -Platform android -ForceRebuild` |
| Windows relaunch | `pwsh -File tools/start-driver.ps1 -Platform windows` |
| Windows inspector on port 4949 | `pwsh -File tools/start-driver.ps1 -Platform windows -DriverPort 4949` |
| Hot restart (no rebuild) | `curl -s -X POST http://127.0.0.1:4948/driver/hot-restart -d '{}'` |

**Prefer hot restart** when changes are hot-reloadable (UI, widget keys). Only rebuild when changes touch native code, entrypoints, or dependencies.

### Pre-flight Cleanup (built into start-driver.ps1)
- **Android**: Force-stops app on all devices, clears stale ADB forwards/reverses for the selected driver port
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
1. Record tier start time (once per tier, not per flow): `pwsh -Command "Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ'"`
2. Execute driver steps — use `/driver/wait` to verify state transitions, NOT `sleep`
3. After data mutation, poll sync status (30s timeout):
   ```bash
   for i in $(seq 1 30); do
     STATUS=$(curl -s http://127.0.0.1:3947/sync/status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('state','unknown'))" 2>/dev/null || echo "error")
     if [ "$STATUS" = "completed" ] || [ "$STATUS" = "idle" ]; then break; fi
     sleep 1
   done
   ```
4. Take screenshot: `curl -s http://127.0.0.1:4948/driver/screenshot --output "$RESULTS_DIR/<role>-<flow>.png"`

### Per-Tier Wrap-Up
After all flows in a tier complete:
1. Check for errors (one curl — no parsing needed):
   ```bash
   curl -s "http://127.0.0.1:3947/logs/errors?since=<TIER_START>"
   ```
2. Get log summary for the report:
   ```bash
   curl -s "http://127.0.0.1:3947/logs/summary?since=<TIER_START>"
   ```
3. Update `checkpoint.json` with all flow results
4. Update `report.md` with tier results table

## Failure Detection

Use these signals to detect failures **without viewing screenshots**:

| Signal | Meaning | Action |
|--------|---------|--------|
| Driver returns 404 | Widget not found | Record missing key, FAIL flow |
| Driver returns 408 | Wait timeout | FAIL flow |
| `/logs/errors` shows new errors | Runtime error | FAIL flow, log the error |
| `/driver/find?key=X` → `exists: false` | Widget doesn't exist | FAIL flow |
| Sync doesn't reach idle in 30s | Sync failure | Capture `/sync/status`, FAIL flow |

### Screenshot Rules
- **Save to disk**: ALWAYS, after every flow (`curl --output`)
- **View inline**: ONLY when a failure signal above is detected
- **State confusion is NOT a failure** — use sentinel key checks (see `references/driver-and-navigation.md`), not screenshots
- Each inline screenshot view costs significant context tokens — prefer `/driver/find` checks which are free

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
3. After tier completes, spawn a **background** Task agent (`code-fixer-agent`) to:
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
4. Run post-login normalization (see below)
5. Update `checkpoint.json` with new `current_role`

### Post-Login State Normalization

After every login (initial or role switch), the app may land on intermediate screens before the dashboard is usable. **Always run these checks after login:**

**Step 1: Handle consent screen** — The consent/ToS screen appears after sign-out + re-login or on first launch. Check and handle:
```bash
ROUTE=$(curl -s http://127.0.0.1:4948/driver/current-route | python3 -c "import sys,json; print(json.load(sys.stdin).get('route',''))")
if [ "$ROUTE" = "/consent" ]; then
  # Scroll to bottom to enable accept button
  for i in $(seq 1 10); do
    curl -s -X POST http://127.0.0.1:4948/driver/scroll -d '{"key":"consent_scroll_view","dx":0,"dy":-500}'
    sleep 0.3
  done
  sleep 0.5
  curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"consent_accept_button"}'
  curl -s -X POST http://127.0.0.1:4948/driver/wait -d '{"key":"dashboard_nav_button","timeoutMs":10000}'
fi
```

**Step 2: Verify project selected** — The dashboard requires an active project. If no project is selected, the "New Entry" button won't appear:
```bash
EXISTS=$(curl -s "http://127.0.0.1:4948/driver/find?key=dashboard_new_entry_button" | python3 -c "import sys,json; print(json.load(sys.stdin).get('exists',False))")
if [ "$EXISTS" = "False" ]; then
  # Navigate to projects, select first available
  curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"projects_nav_button"}'
  sleep 1
  # Find and tap first project card (use tree search)
  CARD=$(curl -s "http://127.0.0.1:4948/driver/tree?depth=15" | python3 -c "
import sys, json
tree = json.load(sys.stdin).get('tree','')
for line in tree.split('\n'):
    if 'project_card_' in line:
        import re
        m = re.search(r\"project_card_[a-f0-9-]+\", line)
        if m: print(m.group(0)); break
")
  if [ -n "$CARD" ]; then
    curl -s -X POST http://127.0.0.1:4948/driver/tap -d "{\"key\":\"$CARD\"}"
    sleep 1
    curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_nav_button"}'
  fi
fi
```

**Step 3: Dismiss overlays** — Clear any stale snackbars or banners:
```bash
curl -s -X POST http://127.0.0.1:4948/driver/dismiss-overlays -d '{}'
```

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

All widget keys live in `lib/shared/testing_keys/` (16 files: 15 feature-specific + 1 barrel export). Read the relevant file
before interacting with a feature. Keys are discoverable at runtime via
`GET /driver/find?key=KEY_NAME`.

| File | Class | Domain |
|------|-------|--------|
| `auth_keys.dart` | `AuthTestingKeys` | Login, registration |
| `common_keys.dart` | `CommonTestingKeys` | Shared widgets (dialogs, snackbars) |
| `consent_keys.dart` | `ConsentTestingKeys` | Consent/ToS screens |
| `contractors_keys.dart` | `ContractorsTestingKeys` | Contractor management |
| `documents_keys.dart` | `DocumentsTestingKeys` | Documents management |
| `entries_keys.dart` | `EntriesTestingKeys` | Daily entries |
| `locations_keys.dart` | `LocationsTestingKeys` | Location management |
| `navigation_keys.dart` | `NavigationTestingKeys` | Bottom nav, drawer |
| `photos_keys.dart` | `PhotosTestingKeys` | Photo capture/gallery |
| `projects_keys.dart` | `ProjectsTestingKeys` | Project CRUD |
| `quantities_keys.dart` | `QuantitiesTestingKeys` | Quantity tracking |
| `settings_keys.dart` | `SettingsTestingKeys` | App settings |
| `support_keys.dart` | `SupportTestingKeys` | Support/help screens |
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

## Test Data Safety
- All test projects use "E2E " prefix
- **CRITICAL**: Always use timestamped project names (e.g., "E2E Test 1711046095") to avoid collisions with prior runs
- When a prior E2E project already exists, REUSE it instead of creating a new one (tap into it, verify sub-entities)
- Cleanup: `pwsh -File tools/verify-sync.ps1 -Cleanup -ProjectName "E2E*" -DryRun` (still valid for data cleanup; sync correctness verification is now Claude-driven — see `/test sync` (S01-S21) or run `node tools/debug-server/run-tests.js --cleanup-only` for data cleanup only)

## Windows Bash Constraints
- **NO `jq`** — use `python3 -c "import json..."` for JSON parsing (but prefer `?format=text` endpoints which need no parsing)
- **NO multi-line heredocs with curl**
- **ALWAYS `pwsh -Command "..."`** for PowerShell
- **Special chars (`!`, `$`) in curl JSON** — see Credentials section for `--data-raw` pattern. Applies to ALL curl calls with user-supplied text, not just credentials.
- **Bash variables don't persist between Bash tool calls** — see "Bash Tool Constraints" section
