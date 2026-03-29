# Debug Skill Driver Integration -- Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Integrate the HTTP driver server (port 4948) into the systematic-debugging skill so Claude can autonomously launch the app, reproduce bugs, verify hypotheses via logs, and confirm fixes without requiring the user to manually tap through the app.

**Blast Radius:** 4 files (3 modify, 1 create), all `.claude/` config, 0 app code

---

## Phase 0: Secure Credentials

### Sub-phase 0.1: Add `*.secret` to `.claude/.gitignore`
**Files:** Modify `.claude/.gitignore`
**Agent:** general-purpose

Check if `.claude/.gitignore` already contains a `*.secret` pattern. If not, append:

```
*.secret
```

This prevents test credentials (`test-credentials.secret`) and any future `.secret` files from leaking to the config repo.

---

## Phase 1: Create Driver Integration Reference

### Sub-phase 1.1: Write driver-integration.md
**Files:** Create `.claude/skills/systematic-debugging/references/driver-integration.md`
**Agent:** general-purpose

Create this file with the full content below:

```markdown
# Driver Integration Reference

Reference for using the HTTP driver server (port 4948) during debug sessions. The driver enables autonomous bug reproduction and fix verification without manual user interaction.

---

## Driver API Quick Reference

Base URL: `http://127.0.0.1:4948`

### Widget Interaction

| Endpoint | Method | Body | Success | Failure |
|----------|--------|------|---------|---------|
| `/driver/tap` | POST | `{"key": "widget_key"}` | 200 | 404 (not found) |
| `/driver/text` | POST | `{"key": "field_key", "text": "value"}` | 200 | 404 |
| `/driver/scroll` | POST | `{"key": "scrollable_key", "dx": 0, "dy": -300}` | 200 | 404 |
| `/driver/scroll-to-key` | POST | `{"scrollable": "scroll_key", "target": "target_key", "maxScrolls": 20}` | 200 | 404/408 |
| `/driver/back` | POST | (none) | 200 | -- |

### Query & Wait

| Endpoint | Method | Body/Params | Success | Failure |
|----------|--------|-------------|---------|---------|
| `/driver/wait` | POST | `{"key": "widget_key", "timeoutMs": 15000}` | 200 | 408 (timeout) |
| `/driver/find` | GET | `?key=widget_key` | 200 `{"exists": true/false}` | -- |
| `/driver/ready` | GET | -- | 200 `{"ready": true, "screen": "/current-route"}` | 503 |
| `/driver/tree` | GET | `?keysOnly=true` or `?filter=prefix` | 200 (widget tree) | -- |
| `/driver/screenshot` | GET | -- | 200 (PNG bytes) | -- |

### App Lifecycle

| Endpoint | Method | Body | Success | Failure |
|----------|--------|------|---------|---------|
| `/driver/hot-restart` | POST | (none) | 200 | 500 |

### HTTP Status Codes

- **200** -- Success
- **404** -- Widget not found (key does not exist in current widget tree)
- **408** -- Wait timeout (widget did not appear within timeout)
- **500** -- Internal error (app crash, hot-restart failure)

---

## Login Procedure

### Read credentials

```bash
# Credentials are in JSON format at .claude/test-credentials.secret
# Fields: admin.email, admin.password, inspector.email, inspector.password
```

### Login as admin

```bash
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key": "login_email_field"}'
curl -s -X POST http://127.0.0.1:4948/driver/text -H "Content-Type: application/json" -d '{"key": "login_email_field", "text": "{{admin_email}}"}'
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key": "login_password_field"}'
curl -s -X POST http://127.0.0.1:4948/driver/text -H "Content-Type: application/json" -d '{"key": "login_password_field", "text": "{{admin_password}}"}'
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key": "login_sign_in_button"}'
curl -s -X POST http://127.0.0.1:4948/driver/wait -H "Content-Type: application/json" -d '{"key": "dashboard_screen", "timeoutMs": 15000}'
```

### Login as inspector

Same sequence but use `inspector.email` and `inspector.password` from credentials file.

### Sign out (to switch roles)

```bash
# 1. Navigate to settings
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key": "settings_nav_button"}'
# 2. Wait for settings screen to load
curl -s -X POST http://127.0.0.1:4948/driver/wait -H "Content-Type: application/json" -d '{"key": "settings_screen", "timeoutMs": 5000}'
# 3. Scroll to sign-out tile
curl -s -X POST http://127.0.0.1:4948/driver/scroll-to-key -H "Content-Type: application/json" -d '{"scrollable": "settings_screen", "target": "settings_sign_out_tile", "maxScrolls": 10}'
# 4. Tap sign-out tile
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key": "settings_sign_out_tile"}'
# 5. Wait for confirm dialog
curl -s -X POST http://127.0.0.1:4948/driver/wait -H "Content-Type: application/json" -d '{"key": "sign_out_confirm_button", "timeoutMs": 3000}'
# 6. Tap confirm
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key": "sign_out_confirm_button"}'
curl -s -X POST http://127.0.0.1:4948/driver/wait -H "Content-Type: application/json" -d '{"key": "login_screen", "timeoutMs": 10000}'
```

---

## Repro Steps JSON Format

Repro steps are saved to the debug session folder as `repro-steps.json`. This enables re-execution during fix verification (Phase 7).

> **Note:** `repro-steps.json` is an agent-readable record, not a machine-executed script. The agent reads each step and translates it to the corresponding curl command at runtime. There is no automated JSON runner -- the agent interprets the steps sequentially.

```json
{
  "description": "Bug description in one sentence",
  "preconditions": {
    "account": "admin",
    "startScreen": "/dashboard"
  },
  "steps": [
    {"action": "tap", "key": "widget_key"},
    {"action": "text", "key": "field_key", "text": "value"},
    {"action": "wait", "key": "screen_key", "timeoutMs": 10000},
    {"action": "scroll", "key": "scrollable_key", "dx": 0, "dy": -300},
    {"action": "scroll-to-key", "scrollable": "scroll_key", "target": "target_key", "maxScrolls": 20},
    {"action": "back"},
    {"action": "sleep", "ms": 1000},
    {"action": "find", "key": "widget_key"}
  ],
  "assertions": [
    {"type": "hypothesis_fired", "tag": "H001", "expect": "substring to find in message"},
    {"type": "hypothesis_not_fired", "tag": "H002"},
    {"type": "no_errors", "since": "start"}
  ]
}
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `description` | Yes | One-sentence bug description |
| `preconditions.account` | Yes | `"admin"` or `"inspector"` -- which test account to log in as |
| `preconditions.startScreen` | No | Route to navigate to before starting steps (default: wherever login lands) |
| `steps[].action` | Yes | One of: `tap`, `text`, `wait`, `scroll`, `scroll-to-key`, `back`, `sleep`, `find` |
| `steps[].key` | Depends | Widget key (required for `tap`, `text`, `wait`, `scroll`, `find`) |
| `steps[].text` | `text` only | Text to enter in field |
| `steps[].timeoutMs` | `wait` only | Max wait in ms (default 10000) |
| `steps[].dx`, `steps[].dy` | `scroll` only | Scroll delta pixels |
| `steps[].scrollable`, `steps[].target` | `scroll-to-key` | Scrollable container key and target widget key |
| `steps[].maxScrolls` | `scroll-to-key` | Max scroll attempts (default 20) |
| `steps[].ms` | `sleep` only | Sleep duration in ms |
| `assertions[].type` | Yes | One of: `hypothesis_fired`, `hypothesis_not_fired`, `no_errors` |
| `assertions[].tag` | hypothesis types | Hypothesis tag (e.g., `H001`) |
| `assertions[].expect` | `hypothesis_fired` | Substring expected in hypothesis log message |
| `assertions[].since` | `no_errors` | `"start"` = since repro began |

### Placeholder Resolution

- `{{admin_email}}`, `{{admin_password}}` -- resolved from `.claude/test-credentials.secret` at runtime
- `{{inspector_email}}`, `{{inspector_password}}` -- same, for inspector account
- **NEVER** hardcode credentials in `repro-steps.json`

---

## Assertion Patterns

### hypothesis_fired

Check that a hypothesis marker logged at least one entry containing the expected substring:

```bash
curl -s "http://127.0.0.1:3947/logs?hypothesis=H001&last=100"
```

Parse the JSON response. At least one entry's `message` field must contain the `expect` substring. If zero entries returned, the assertion fails.

### hypothesis_not_fired

Check that a hypothesis marker was NOT triggered:

```bash
curl -s "http://127.0.0.1:3947/logs?hypothesis=H002&last=100"
```

The response must contain zero entries. If any entries exist, the assertion fails.

### no_errors

Check that no error-category logs appeared since repro started:

```bash
curl -s "http://127.0.0.1:3947/logs?category=error&last=50"
```

Filter entries by timestamp (after repro start time). Zero entries = pass.

---

## Fallback Rules

The driver is a convenience, not a hard dependency. If it fails, fall back to manual guidance.

### Driver unreachable (connection refused)

1. Retry 3 times with 5-second intervals
2. If still unreachable: inform user, switch to manual reproduction
3. Manual fallback = original Phase 4.3 behavior (guide user through steps verbally)

### Widget not found (404)

1. Dump the widget tree for diagnosis:
   ```bash
   curl -s "http://127.0.0.1:4948/driver/tree?keysOnly=true"
   ```
2. Present the available keys to the user
3. Ask if the key name has changed or if the widget is on a different screen
4. Check `lib/shared/testing_keys/` for the correct key

### Wait timeout (408)

1. Log which step timed out and what key was being waited for
2. Check current route -- the app may not have navigated as expected
3. Dump tree to see current state
4. Ask user if there is a prerequisite step missing

### App crash (connection refused after previously working)

1. Inform user: "App appears to have crashed during reproduction"
2. Offer to relaunch: `pwsh -File tools/start-driver.ps1 -Platform <platform>`
3. After relaunch, re-login and resume from the last successful step

### Hot-restart failure (500 from /driver/hot-restart)

1. Full relaunch via `pwsh -File tools/start-driver.ps1 -Platform <platform>`
2. Re-login and re-execute repro steps from scratch

---

## Testing Keys Reference

Keys are defined in `lib/shared/testing_keys/*.dart` (13 files). The barrel export is `lib/shared/testing_keys/testing_keys.dart`.

### Commonly Used Keys

**Navigation:**
- `dashboard_nav_button` -- Bottom nav: Dashboard
- `calendar_nav_button` -- Bottom nav: Calendar
- `projects_nav_button` -- Bottom nav: Projects
- `settings_nav_button` -- Bottom nav: Settings
- `add_entry_fab` -- FAB: Add entry
- `add_project_fab` -- FAB: Add project

**Authentication:**
- `login_screen` -- Login screen root
- `login_email_field` -- Email text field
- `login_password_field` -- Password text field
- `login_sign_in_button` -- Sign in button
- `settings_sign_out_tile` -- Sign out tile in settings
- `sign_out_confirm_button` -- Confirm sign out dialog

**Screens (for wait assertions):**
- `dashboard_screen` -- Dashboard loaded
- `login_screen` -- Login screen loaded

### Dynamic Keys

Some keys include entity UUIDs and cannot be known statically:
- `entry_card_{entryId}` -- Entry list items
- `project_card_{projectId}` -- Project list items
- `personnel_type_card_{typeId}` -- Personnel type items

To discover dynamic keys at runtime:
```bash
# Filter tree by key prefix
curl -s "http://127.0.0.1:4948/driver/tree?filter=entry_card"
```

### Key File Organization

| File | Feature |
|------|---------|
| `auth_keys.dart` | Login, register, forgot password, OTP |
| `navigation_keys.dart` | Bottom nav, FABs |
| `entries_keys.dart` | Entry wizard, report, calendar |
| `projects_keys.dart` | Project setup, project list |
| `settings_keys.dart` | Settings, profile, personnel types, sync |
| `common_keys.dart` | Confirmation dialogs, date pickers |
| `contractors_keys.dart` | Contractor editor |
| `locations_keys.dart` | Location management |
| `photos_keys.dart` | Photo capture, gallery |
| `quantities_keys.dart` | Quantity entry |
| `sync_keys.dart` | Sync dashboard |
| `toolbox_keys.dart` | Calculator, forms, gallery, todos |

---

## Platform Notes

> **Note:** All manual launch/stop commands below are wrapped by `start-driver.ps1` and `stop-driver.ps1`. Prefer using the scripts rather than running these commands individually. The scripts handle debug server startup, ADB port forwarding, readiness polling, and teardown in one step.

### Windows

- Driver and debug server both on localhost -- no port forwarding needed
- Launch: `pwsh -File tools/start-driver.ps1 -Platform windows`
- Kill: `pwsh -File tools/stop-driver.ps1`

### Android

- ADB reverse for BOTH ports:
  ```bash
  adb reverse tcp:4948 tcp:4948
  adb reverse tcp:3947 tcp:3947
  ```
- `start-driver.ps1` handles ADB reverse automatically
- Launch: `pwsh -File tools/start-driver.ps1 -Platform android`
- Kill: `pwsh -File tools/stop-driver.ps1`

### Verify Both Servers

```bash
# Debug server (logs)
curl -s http://127.0.0.1:3947/health

# Driver server (widget control) -- use /driver/ready for health check
curl -s "http://127.0.0.1:4948/driver/ready"
# 200 with {"ready": true, "screen": "/current-route"} means driver is up
```
```

---

## Phase 2: Update Debug Session Management Reference

### Sub-phase 2.1: Update session lifecycle and server setup
**Files:** Modify `.claude/skills/systematic-debugging/references/debug-session-management.md`
**Agent:** general-purpose

#### Edit 1: Add driver server section after the existing "Verify connection" block (after line 56, before the `---` on line 57)

**OLD (lines 55-57):**
```
# Expected: {"status":"ok","entries":0,"maxEntries":30000,"memoryMB":N,"uptimeSeconds":N}
```

---
```

**NEW:**
```
# Expected: {"status":"ok","entries":0,"maxEntries":30000,"memoryMB":N,"uptimeSeconds":N}
```

### Driver server (autonomous reproduction)

The driver server (port 4948) enables Claude to tap widgets, enter text, and navigate the app without user intervention. It is started automatically by `start-driver.ps1`.

**Launch both servers + app in one command:**
```bash
pwsh -File tools/start-driver.ps1 -Platform windows   # or android
```

This script:
1. Starts the debug server (port 3947) if not already running
2. Launches the app with `--target=lib/main_driver.dart --dart-define=DEBUG_SERVER=true`
3. Sets up ADB reverse ports for Android (both 3947 and 4948)
4. Polls readiness until both servers respond

**Verify driver is running:**
```bash
curl -s "http://127.0.0.1:4948/driver/ready"
# 200 with {"ready": true, "screen": "/current-route"} means driver is up
```

**Stop the app (keeps debug server):**
```bash
pwsh -File tools/stop-driver.ps1
```

**Stop everything (app + debug server):**
```bash
pwsh -File tools/stop-driver.ps1 -IncludeDebugServer
```

See `driver-integration.md` for full API reference, login procedures, and repro-steps JSON format.

---
```

#### Edit 2: Update session lifecycle diagram (lines 59-104)

**OLD (lines 59-104):**
```
## Session Lifecycle

```
START
  └─> Choose mode (Quick / Deep)
  └─> If Deep: start server, launch research agent
  └─> POST /clear to reset log buffer

TRIAGE (Phase 1)
  └─> Scan for orphaned hypothesis markers
  └─> Check known defects

COVERAGE CHECK (Phase 2)
  └─> Map Logger coverage in affected code path

INSTRUMENT (Phase 3)
  └─> Add hypothesis markers H001, H002...
  └─> Fill permanent gaps

REPRODUCE (Phase 4)
  └─> Interview user
  └─> Guide reproduction steps

ANALYZE (Phase 5)
  └─> curl logs with hypothesis + category filters
  └─> Read research agent output (Deep mode)

ROOT CAUSE REPORT (Phase 6)
  └─> Present findings
  └─> USER GATE — wait for approval

FIX (Phase 7)
  └─> Implement approved fix
  └─> POST /clear, re-verify

CLEANUP (Phase 9)
  └─> Remove ALL hypothesis() markers
  └─> Global search — must return zero
  └─> Write session log
  └─> Prune 30-day retention

DEFECT LOG (Phase 10)
  └─> Record new patterns to defect file

END
```
```

**NEW:**
```
## Session Lifecycle

```
START
  └─> Choose mode (Quick / Deep)
  └─> If Deep: launch research agent
  └─> POST /clear to reset log buffer

TRIAGE (Phase 1)
  └─> Scan for orphaned hypothesis markers
  └─> Check known defects

COVERAGE CHECK (Phase 2)
  └─> Map Logger coverage in affected code path

INSTRUMENT (Phase 3)
  └─> Add hypothesis markers H001, H002...
  └─> Fill permanent gaps

LAUNCH DRIVER (Phase 3.5)
  └─> pwsh -File tools/start-driver.ps1 (starts debug server + app + driver)
  └─> Poll readiness (script handles this)
  └─> Login via test credentials from .claude/test-credentials.secret
  └─> Fallback: if driver unreachable after 3 retries, switch to manual

REPRODUCE (Phase 4)
  └─> Interview user (5 questions)
  └─> Write repro-steps.json from user description
  └─> Execute repro steps via driver HTTP calls
  └─> Check hypothesis markers on debug server
  └─> Present evidence to user
  └─> Fallback: manual guidance if driver unavailable

ANALYZE (Phase 5)
  └─> curl logs with hypothesis + category filters
  └─> Read research agent output (Deep mode)

ROOT CAUSE REPORT (Phase 6)
  └─> Present findings
  └─> USER GATE — wait for approval

FIX (Phase 7)
  └─> Implement approved fix
  └─> Hot-restart via POST /driver/hot-restart
  └─> POST /clear, re-execute repro-steps.json
  └─> Assert hypothesis markers show correct behavior
  └─> Run flutter test for regressions
  └─> Fallback: full relaunch if hot-restart fails

CLEANUP (Phase 9)
  └─> Remove ALL hypothesis() markers
  └─> Global search — must return zero
  └─> Write session log
  └─> Prune 30-day retention
  └─> Stop driver: pwsh -File tools/stop-driver.ps1

DEFECT LOG (Phase 10)
  └─> Record new patterns to defect file

END
```
```

#### Edit 3: Add driver commands to Quick Server Reference table (after line 207, at end of file)

**Append after the existing table:**

```

### Driver Server

See `driver-integration.md` for the full driver API reference, login procedures, and repro-steps JSON format.

**Launch/stop commands:**

| Command | Purpose |
|---------|---------|
| `pwsh -File tools/start-driver.ps1 -Platform windows` | Start driver environment |
| `pwsh -File tools/stop-driver.ps1` | Stop app (keep debug server) |
| `pwsh -File tools/stop-driver.ps1 -IncludeDebugServer` | Stop app + debug server |
```

---

## Phase 3: Update Main Skill File

### Sub-phase 3.1: Update Entry section and add reference
**Files:** Modify `.claude/skills/systematic-debugging/SKILL.md`
**Agent:** general-purpose

#### Edit 1: Update mode table and Deep mode setup (lines 29-50)

WHY: Both modes now get driver capability. Deep mode still adds the research agent. The debug server is started by `start-driver.ps1`, so manual server setup is removed from entry.

**OLD (lines 29-50):**
```
## Entry: Choose Debug Mode

**Ask the user before starting:**

> "Quick mode (direct investigation, no server needed) or Deep mode (log server + background research agent)?"

| Mode | Use When | Setup |
|------|----------|-------|
| Quick | Clear repro, no race conditions, obvious error | None |
| Deep | Intermittent bug, state corruption, async timing, unknown origin | Start debug server, launch research agent |

**Deep mode setup** (do before Phase 1):
1. Load reference files (see below)
2. Launch `debug-research-agent` with `run_in_background: true`, passing the issue description and suspected code paths
3. Continue with Phase 1 while agent researches in parallel

**Reference files** (load on entry):
- `@.claude/skills/systematic-debugging/references/log-investigation-and-instrumentation.md`
- `@.claude/skills/systematic-debugging/references/codebase-tracing-paths.md`
- `@.claude/skills/systematic-debugging/references/defects-integration.md`
- `@.claude/skills/systematic-debugging/references/debug-session-management.md`
```

**NEW:**
```
## Entry: Choose Debug Mode

**Ask the user before starting:**

> "Quick mode (direct investigation) or Deep mode (adds background research agent for parallel analysis)?"
>
> Both modes launch the driver for autonomous reproduction and log collection.

| Mode | Use When | Setup |
|------|----------|-------|
| Quick | Clear repro, no race conditions, obvious error | Driver + debug server (via start-driver.ps1) |
| Deep | Intermittent bug, state corruption, async timing, unknown origin | Driver + debug server + research agent |

**Deep mode setup** (do before Phase 1):
1. Load reference files (see below)
2. Launch `debug-research-agent` with `run_in_background: true`, passing the issue description and suspected code paths
3. Continue with Phase 1 while agent researches in parallel

**Reference files** (load on entry):
- `@.claude/skills/systematic-debugging/references/log-investigation-and-instrumentation.md`
- `@.claude/skills/systematic-debugging/references/codebase-tracing-paths.md`
- `@.claude/skills/systematic-debugging/references/defects-integration.md`
- `@.claude/skills/systematic-debugging/references/debug-session-management.md`
- `@.claude/skills/systematic-debugging/references/driver-integration.md`
```

### Sub-phase 3.2: Remove manual rebuild from Phase 3 (INSTRUMENT GAPS)
**Files:** Modify `.claude/skills/systematic-debugging/SKILL.md`
**Agent:** general-purpose

#### Edit 2: Replace Phase 3.3 rebuild step (lines 158-171)

WHY: The rebuild step is now handled by Phase 3.5 (LAUNCH DRIVER), which uses `start-driver.ps1`. Keeping a separate rebuild here would be redundant and confusing. Replace with a note that Phase 3.5 handles the rebuild.

**OLD (lines 158-171):**
```
### 3.3 Rebuild app

Deep mode (Android):
```
pwsh -Command "flutter run -d <device> --dart-define=DEBUG_SERVER=true"
```

Windows:
```
pwsh -Command "flutter run -d windows --dart-define=DEBUG_SERVER=true"
```

**Do NOT use `--dart-define=DEBUG_SERVER=true` in release builds.**
```

**NEW:**
```
### 3.3 Proceed to Phase 3.5

Instrumentation is complete. Phase 3.5 (LAUNCH DRIVER) will build and launch the app with the driver entrypoint and `DEBUG_SERVER=true` flag.

**Do NOT manually run `flutter run` here** -- `start-driver.ps1` handles the build, launch, and readiness polling in one step.
```

### Sub-phase 3.3: Add Phase 3.5 (LAUNCH DRIVER)
**Files:** Modify `.claude/skills/systematic-debugging/SKILL.md`
**Agent:** general-purpose

#### Edit 3: Insert Phase 3.5 between Phase 3 and Phase 4 (after line 172, before line 174)

WHY: This is the new phase that launches the app with the driver, logs in, and prepares for autonomous reproduction.

**OLD (lines 172-174):**
```
---

## Phase 4: REPRODUCE
```

**NEW:**
```
---

## Phase 3.5: LAUNCH DRIVER

**Goal**: Launch the app with driver and debug server, log in with test credentials.

### 3.5.1 Determine platform

Ask the user: "Windows or Android?" (or infer from context if already established).

### 3.5.2 Launch driver environment

```bash
pwsh -File tools/start-driver.ps1 -Platform windows  # or android
```

This script handles:
- Starting the debug server (port 3947) if not already running
- Building and launching the app with `--target=lib/main_driver.dart --dart-define=DEBUG_SERVER=true`
- ADB reverse ports for Android (3947 + 4948)
- Polling readiness until both servers respond

### 3.5.3 Login with test credentials

Read `.claude/test-credentials.secret` for the appropriate account (default: `admin` unless the bug requires `inspector`).

Execute the login sequence:

```bash
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key": "login_email_field"}'
curl -s -X POST http://127.0.0.1:4948/driver/text -H "Content-Type: application/json" -d '{"key": "login_email_field", "text": "<email>"}'
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key": "login_password_field"}'
curl -s -X POST http://127.0.0.1:4948/driver/text -H "Content-Type: application/json" -d '{"key": "login_password_field", "text": "<password>"}'
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key": "login_sign_in_button"}'
curl -s -X POST http://127.0.0.1:4948/driver/wait -H "Content-Type: application/json" -d '{"key": "dashboard_screen", "timeoutMs": 15000}'
```

### 3.5.4 Verify readiness

Confirm both servers are healthy:
```bash
curl -s http://127.0.0.1:3947/health           # debug server
curl -s "http://127.0.0.1:4948/driver/find?key=dashboard_screen"  # driver + app (200 with {"exists": true})
```

### 3.5.5 Fallback

If the driver is unreachable after 3 retries (5s intervals):
1. Inform the user: "Driver server not responding. Falling back to manual reproduction."
2. Skip to Phase 4 in manual mode (original behavior: user taps through the app)
3. Phase 7 verification also falls back to manual

**Clear logs before proceeding:**
```bash
curl -X POST http://127.0.0.1:3947/clear
```

---

## Phase 4: REPRODUCE
```

### Sub-phase 3.4: Rewrite Phase 4 (REPRODUCE) for autonomous execution
**Files:** Modify `.claude/skills/systematic-debugging/SKILL.md`
**Agent:** general-purpose

#### Edit 4: Replace Phase 4 content (lines 174-206 in original, now shifted by Phase 3.5 insertion)

WHY: Phase 4 now uses the driver for autonomous reproduction. The user interview is kept (4.1) but the reproduction itself is automated. Manual fallback preserved.

**OLD (the entire Phase 4 section, starting from the line after `## Phase 4: REPRODUCE`):**
```
**Goal**: Get clean, reliable reproduction with logs flowing.

### 4.1 User interview

Ask the user these five questions before they reproduce:

1. What exact steps trigger the bug?
2. How often does it happen (always, intermittent, first-launch only)?
3. What device/platform?
4. When did this last work correctly?
5. What changed since it last worked (commits, data, permissions)?

### 4.2 ADB health check (Android only)

```bash
adb devices
adb reverse tcp:3947 tcp:3947
```

Confirm device is listed and port forwarding is active.

### 4.3 Guide reproduction

Have the user follow the exact steps. Watch for any app crash output in the terminal. Confirm log entries are flowing to the server:

```bash
curl "http://127.0.0.1:3947/logs?last=5"
```

If no entries appear: the app is not reaching the server. Check ADB forwarding, DEBUG_SERVER flag, and server status.
```

**NEW:**
```
**Goal**: Reproduce the bug autonomously via driver, with log evidence flowing.

### 4.1 User interview

Ask the user these five questions to understand the bug:

1. What exact steps trigger the bug?
2. How often does it happen (always, intermittent, first-launch only)?
3. What device/platform?
4. When did this last work correctly?
5. What changed since it last worked (commits, data, permissions)?

### 4.2 Write repro-steps.json

Based on the user's description, write a `repro-steps.json` file to the debug session folder (`.claude/debug-sessions/`). See `driver-integration.md` for the JSON format.

Map the user's natural language steps to driver actions:
- "Tap the settings icon" -> `{"action": "tap", "key": "settings_nav_button"}`
- "Enter my email" -> `{"action": "text", "key": "login_email_field", "text": "{{admin_email}}"}`
- "Wait for the dashboard to load" -> `{"action": "wait", "key": "dashboard_screen", "timeoutMs": 10000}`
- "Scroll down to the sync section" -> `{"action": "scroll-to-key", "scrollable": "settings_screen", "target": "settings_sync_tile", "maxScrolls": 10}`

Use `/driver/tree?keysOnly=true` to discover the correct keys if unsure.

Include assertions that map to the hypothesis markers added in Phase 3.

**Post-generation credential check:** After writing `repro-steps.json`, grep the file for any values from `test-credentials.secret` (emails, passwords, UUIDs). If any raw credential values are found, replace them with the corresponding `{{placeholder}}` tokens (e.g., `{{admin_email}}`, `{{admin_password}}`). Credentials must never be hardcoded in the JSON file.

### 4.3 Execute repro steps via driver

Execute each step in `repro-steps.json` sequentially using curl commands:

```bash
# Example: execute a tap step
curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key": "settings_nav_button"}'
```

After each step, briefly check for errors:
```bash
curl -s "http://127.0.0.1:3947/logs?category=error&last=5"
```

If a step returns 404 (widget not found): dump tree, identify correct key, update repro-steps.json, and retry.

### 4.4 Check hypothesis markers

After all steps execute, check each hypothesis marker:

```bash
curl -s "http://127.0.0.1:3947/logs?hypothesis=H001&last=100"
curl -s "http://127.0.0.1:3947/logs?hypothesis=H002&last=100"
```

Record which markers fired, with what values, and which did not fire.

### 4.5 Present evidence to user

Show the user:
- Which repro steps executed successfully
- Which hypothesis markers fired (with key data values)
- Which markers did NOT fire (indicating the code path was not reached)
- Any errors logged during reproduction

**Credential scrubbing:** When presenting hypothesis evidence, apply Phase 9.3 scrubbing rules -- truncate UUIDs to first 8 characters, redact emails to `u***@***.com`, and redact personal names. Never display raw credential values from test-credentials.secret in output.

This evidence feeds directly into Phase 5 (Evidence Analysis).

### 4.6 Fallback: manual reproduction

If the driver is not running (Phase 3.5 fallback was triggered) or a step fails with connection refused:

1. Present the repro-steps.json to the user as a guide
2. Ask them to manually follow the steps
3. Monitor logs via debug server as they reproduce:
   ```bash
   curl "http://127.0.0.1:3947/logs?last=5"
   ```
4. If no log entries appear: check ADB forwarding, DEBUG_SERVER flag, and server status
```

### Sub-phase 3.5: Rewrite Phase 7 (FIX) for autonomous verification
**Files:** Modify `.claude/skills/systematic-debugging/SKILL.md`
**Agent:** general-purpose

#### Edit 5: Replace Phase 7 content (lines 302-333 in original)

WHY: Phase 7 now uses hot-restart + automated re-execution of repro steps instead of asking the user to manually re-test.

**OLD (the entire Phase 7 section, starting from the line after `## Phase 7: FIX`):**
```
**Goal**: Implement the approved fix and verify it resolves the bug.

### 7.1 Implement fix

Apply the approved changes. One change at a time.

### 7.2 Clear logs

```bash
curl -X POST http://127.0.0.1:3947/clear
```

### 7.3 Verify fix

Have the user reproduce the original steps. Confirm:
- Bug no longer occurs
- Hypothesis markers show the new correct flow
- No new errors in error category

```bash
curl "http://127.0.0.1:3947/logs?category=error&last=20"
```

### 7.4 Check for regressions

Run targeted tests for the affected feature:
```bash
pwsh -Command "flutter test test/features/{feature}/"
```
```

**NEW:**
```
**Goal**: Implement the approved fix and verify it resolves the bug autonomously.

### 7.1 Implement fix

Apply the approved changes. One change at a time.

### 7.2 Hot-restart the app

Apply changes without a full rebuild:

```bash
curl -s -X POST http://127.0.0.1:4948/driver/hot-restart
```

If hot-restart fails (500 response), fall back to full relaunch:
```bash
pwsh -File tools/stop-driver.ps1
pwsh -File tools/start-driver.ps1 -Platform <platform>
```

After restart, re-login using the test credentials (same procedure as Phase 3.5.3).

### 7.3 Clear logs

```bash
curl -X POST http://127.0.0.1:3947/clear
```

### 7.4 Re-execute repro steps

Re-run the same `repro-steps.json` from Phase 4.2 via driver curl commands (same as Phase 4.3).

### 7.5 Assert fix via hypothesis markers

Check each assertion from `repro-steps.json`:

- **`hypothesis_fired`**: The marker should now show CORRECT values (contrast with pre-fix values from Phase 4.4)
- **`hypothesis_not_fired`**: A previously-firing marker should now be silent (if the fix prevents the bad path)
- **`no_errors`**: Zero error-category entries since log clear

```bash
curl -s "http://127.0.0.1:3947/logs?hypothesis=H001&last=100"
curl -s "http://127.0.0.1:3947/logs?category=error&last=20"
```

Present a before/after comparison to the user:

```
VERIFICATION RESULTS

Marker | Before Fix          | After Fix           | Status
H001   | pendingCount=3      | pendingCount=3      | SAME (expected)
H002   | never fired         | fired, pushed=true  | FIXED
errors | FK constraint fail  | (none)              | FIXED
```

### 7.6 Check for regressions

Run targeted tests for the affected feature:
```bash
pwsh -Command "flutter test test/features/{feature}/"
```

### 7.7 Present verification results

Show the user the full before/after comparison and test results. Confirm the fix is accepted before proceeding to Phase 8.

### 7.8 Fallback: manual verification

If the driver is not available:
1. Ask the user to reproduce the original steps after the fix
2. Monitor logs via debug server
3. Confirm the bug no longer occurs via log evidence
```

### Sub-phase 3.6: Add driver teardown to Phase 9 (CLEANUP)
**Files:** Modify `.claude/skills/systematic-debugging/SKILL.md`
**Agent:** general-purpose

#### Edit 6: Add driver teardown after 30-day retention pruning (after line 411 in original, at the end of Phase 9)

WHY: The driver should be stopped at session end so it does not consume resources. Debug server is left running (user may want to review logs).

**OLD (lines 407-412):**
```
**Scrubbing rules**: No user data, no actual log values that could contain PII, no credentials.

### 9.4 Prune 30-day retention

Check `.claude/debug-sessions/` for session logs older than 30 days. List any found and ask user to confirm deletion.
```

**NEW:**
```
**Scrubbing rules**: No user data, no actual log values that could contain PII, no credentials.

### 9.4 Prune 30-day retention

Check `.claude/debug-sessions/` for session logs older than 30 days. List any found and ask user to confirm deletion.

### 9.5 Stop driver

Kill the app process (but leave the debug server running so the user can review logs):

```bash
pwsh -File tools/stop-driver.ps1
```

NOTE: Do NOT use `-IncludeDebugServer` unless the user explicitly asks. They may want to browse logs after the session.
```

### Sub-phase 3.7: Update Quick Reference table
**Files:** Modify `.claude/skills/systematic-debugging/SKILL.md`
**Agent:** general-purpose

#### Edit 7: Replace the Quick Reference table (lines 472-487)

**OLD (lines 472-487):**
```
## Quick Reference

| Phase | Goal | Hard Gate |
|-------|------|-----------|
| Entry | Choose mode, load refs | Ask user |
| 1 TRIAGE | Clean baseline | Present findings |
| 2 COVERAGE CHECK | Map Logger coverage | Present coverage map |
| 3 INSTRUMENT GAPS | Add hypothesis markers | Auth restriction enforced |
| 4 REPRODUCE | Get clean repro | User confirms repro |
| 5 EVIDENCE ANALYSIS | Read log data | Identify failure point |
| 6 ROOT CAUSE REPORT | Present findings | USER GATE — wait for approval |
| 7 FIX | Implement approved fix | Verify + regression check |
| 8 INSTRUMENTATION REVIEW | Keep vs remove decision | User confirms keeps |
| 9 CLEANUP | Remove ALL hypothesis() | Global search must return zero |
| 10 DEFECT LOG | Record new patterns | — |
```

**NEW:**
```
## Quick Reference

| Phase | Goal | Hard Gate |
|-------|------|-----------|
| Entry | Choose mode, load refs | Ask user |
| 1 TRIAGE | Clean baseline | Present findings |
| 2 COVERAGE CHECK | Map Logger coverage | Present coverage map |
| 3 INSTRUMENT GAPS | Add hypothesis markers | Auth restriction enforced |
| 3.5 LAUNCH DRIVER | Start app + driver, login | Driver ready or manual fallback |
| 4 REPRODUCE | Autonomous repro via driver | Evidence presented to user |
| 5 EVIDENCE ANALYSIS | Read log data | Identify failure point |
| 6 ROOT CAUSE REPORT | Present findings | USER GATE -- wait for approval |
| 7 FIX | Implement fix, hot-restart, re-verify | Before/after comparison shown |
| 8 INSTRUMENTATION REVIEW | Keep vs remove decision | User confirms keeps |
| 9 CLEANUP | Remove markers, stop driver | Global search must return zero |
| 10 DEFECT LOG | Record new patterns | -- |
```

---

## Phase 4: Verification

### Sub-phase 4.1: Validate all cross-references
**Agent:** general-purpose

Check the following:

1. **SKILL.md references driver-integration.md**: Confirm the Entry section includes `@.claude/skills/systematic-debugging/references/driver-integration.md` in the reference files list.

2. **Phase 3.5 references start-driver.ps1**: Confirm `tools/start-driver.ps1` is referenced with correct flags (`-Platform windows` / `-Platform android`).

3. **Phase 4 references driver-integration.md**: Confirm step 4.2 says "See `driver-integration.md` for the JSON format."

4. **Phase 7 references repro-steps.json**: Confirm step 7.4 says "Re-run the same `repro-steps.json` from Phase 4.2."

5. **Phase 9 references stop-driver.ps1**: Confirm step 9.5 runs `pwsh -File tools/stop-driver.ps1`.

6. **debug-session-management.md references driver-integration.md**: Confirm the new driver server section says "See `driver-integration.md` for full API reference."

7. **Session lifecycle diagram**: Confirm it includes LAUNCH DRIVER between INSTRUMENT and REPRODUCE, and shows driver teardown in CLEANUP.

8. **No stale references to manual `flutter run` in Phase 3.3**: Confirm the old build commands are replaced with the note about Phase 3.5.

### Sub-phase 4.2: Verify file count

Confirm exactly 4 files were touched:
- Modified: `.claude/.gitignore` (added `*.secret` pattern)
- Created: `.claude/skills/systematic-debugging/references/driver-integration.md`
- Modified: `.claude/skills/systematic-debugging/references/debug-session-management.md`
- Modified: `.claude/skills/systematic-debugging/SKILL.md`

No app code files should have been changed.
