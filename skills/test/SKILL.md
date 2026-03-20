---
name: test
description: Run E2E test flows via HTTP driver automation
agents:
  - .claude/agents/test-wave-agent.md
---

# /test — HTTP Driver Test Skill

## Overview
Runs end-to-end test flows against the running app via HTTP driver endpoints (port 4948).
The app must be launched with `main_driver.dart` entrypoint. Widgets are driven via HTTP
requests — cross-platform (Android + Windows).

## Credentials
`.claude/test-credentials.secret` — gitignored JSON with admin + inspector accounts.

## Usage

```
/test                     # Run all flows (T01-T14) as admin
/test T01-T06             # Run Tier 1 Foundation only
/test T07-T13             # Run Tier 2 Daily Entry Lifecycle only
/test T14                 # Run Tier 3 PDF Export only
/test T03                 # Run single flow
/test overnight           # Full autonomous run — both roles, all flows, compaction-safe
/test full                # Alias for overnight
```

## Prerequisites (automated)
1. Orchestrator runs: `pwsh -File tools/start-driver.ps1 -Platform windows`
2. Script handles debug server, app launch, and readiness gate
3. No manual setup required

For Android: `pwsh -File tools/start-driver.ps1 -Platform android`

## Architecture

### Agent Mode (short runs: `/test T01-T06`)
Dispatches a test-wave-agent per tier. Agent interacts with the driver via curl.
```
Claude (orchestrator)
  ├─ Tier 1 agent (T01-T06) — sequential
  ├─ Tier 2 agent (T07-T13) — sequential (after Tier 1)
  └─ Tier 3 agent (T14)     — sequential (after Tier 2)
```

### Autonomous Mode (overnight: `/test overnight`)
The orchestrator runs ALL flows **directly** — no sub-agents. Uses a checkpoint file
to survive context compaction and resume seamlessly.

```
Claude (orchestrator) — runs flows directly via curl
  ├─ Creates checkpoint.json at start
  ├─ Executes one flow at a time: curl → verify sync → check logs → screenshot
  ├─ Updates checkpoint.json after EACH flow
  ├─ After all flows as admin → signs out → signs in as inspector → repeats
  └─ Writes report.md with all findings at the end
```

## Autonomous Mode — Detailed Protocol

### 1. Setup
```bash
RESULTS_DIR=".claude/test_results/$(date +%Y-%m-%d_%H-%M)"
mkdir -p "$RESULTS_DIR"
```

Read credentials from `.claude/test-credentials.secret`.
Read testing keys from `lib/shared/testing_keys/*.dart` as needed per flow.

### 2. Checkpoint File
Write `.claude/test_results/<run>/checkpoint.json` **after every flow**:
```json
{
  "run_id": "2026-03-19_21-34",
  "platform": "windows",
  "results_dir": ".claude/test_results/2026-03-19_21-34",
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

### 3. After Compaction — Resume Protocol
When context is compacted, the orchestrator MUST:
1. Read `.claude/test_results/` to find the latest run directory
2. Read `checkpoint.json` from that directory
3. Read the credentials file: `.claude/test-credentials.secret`
4. Take a screenshot to assess current app state
5. Read the testing keys file needed for `next_flow`
6. Resume execution from `next_flow`

### 4. Per-Flow Execution
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
6. Take screenshot
7. If PASS: delete screenshot. If FAIL: keep as `<role>-<flow>-fail.png`
8. Update `checkpoint.json`
9. Update `.claude/test-flows/registry.md`

### 5. Role Switch
After all flows complete as admin:
1. Sign out: `settings_nav_button` → `settings_sign_out_tile` → `sign_out_confirm_button`
2. Wait for `login_screen`
3. Log in as inspector (credentials from `.claude/test-credentials.secret`)
4. Run all flows again — inspector will hit permission denials on some actions, **that's expected and should be logged**
5. Update `checkpoint.json` with `current_role: "inspector"`

### 6. Report
After both roles complete, write `.claude/test_results/<run>/report.md`:
```markdown
# Test Run Report — <date> <time>

## Admin Results
| Flow | Status | Notes |
|------|--------|-------|
| T01  | PASS   |       |
| T02  | FAIL   | location button not found |

## Inspector Results
| Flow | Status | Notes |
|------|--------|-------|
| T01  | BLOCKED | No create project button (expected — inspector can't create) |

## Bugs Found
- **[BUG]** <description> — screenshot: `admin-T02-fail.png`

## Permission Denials (Inspector)
- T01: No FAB visible (correct — inspector cannot create projects)
- T06: Cannot manage assignments (correct)

## Observations
- Sync averaged 3s per flow
- Ghost project appeared after interrupted creation (known defect)
```

## Agent Mode — Dispatch Instructions

Before dispatching, create the timestamped results dir (see Setup above).

The orchestrator prompt MUST include:
1. **Platform** (windows or android)
2. **Flow range** (e.g., T01-T06)
3. **Current app state** (which screen, logged in as who)
4. **Shared state from prior tiers** — e.g., "T01 created project 'E2E Test Project'"
5. **Results directory path**

### Flow Dependencies

**Tier 1 (T01-T06)** — All flows operate on ONE project:
- T01 creates "E2E Test Project" → saves it
- T02-T06 navigate to that project's setup screen and use different tabs
- Tabs: Details, Locations, Contractors, Pay Items, Assignments
- Agent must NOT create a new project for each flow

**Tier 2 (T07-T13)** — All flows operate on the T01 project:
- T07 creates a daily entry for the T01 project
- T08-T11 add data to that entry
- T12-T13 use the toolbox within the T01 project context

**Tier 3 (T14)** — Uses the entry from T07

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
| POST | /driver/scroll | {"key": "X", "dx": 0, "dy": -300} |
| POST | /driver/scroll-to-key | {"scrollable": "X", "target": "Y", "maxScrolls": 20} |
| POST | /driver/back | {} |
| POST | /driver/wait | {"key": "X", "timeoutMs": 10000} |
| POST | /driver/inject-photo | {"data": "<base64>", "filename": "test.jpg"} |
| POST | /driver/inject-file | {"data": "<base64>", "filename": "doc.pdf"} |

> `/driver/screenshot` returns `image/png` binary. Use `curl --output <path>`.

## Teardown

After test run completes:
```
pwsh -File tools/stop-driver.ps1
```

Add `-IncludeDebugServer` to also kill the debug server.

## Error Handling
- **Driver unreachable:** retry once after 2s, then FAIL
- **Element not found:** take screenshot, wait 3s, retry once, then FAIL
- **Sync timeout (30s):** capture /sync/status, FAIL flow, continue
- **App crash:** detect via /driver/ready timeout, capture last logs, restart driver

## Flow Registry
`.claude/test-flows/registry.md` — unified registry with all flows and run history.

## Test Data Safety
- All test projects use "E2E " prefix
- Cleanup: `pwsh -File tools/verify-sync.ps1 -Cleanup -ProjectName "E2E*" -DryRun`

## Windows Bash Constraints
- **NO `jq`** — use `python3 -c "import json..."` for JSON parsing
- **NO multi-line heredocs with curl**
- **ALWAYS `pwsh -Command "..."`** for PowerShell
- Special chars (`!`, `$`) in curl JSON: use double-quoted -d flag
