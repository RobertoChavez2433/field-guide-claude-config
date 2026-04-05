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

Keys are defined in `lib/shared/testing_keys/*.dart` (16 files: 15 feature-specific + 1 barrel export). The barrel export is `lib/shared/testing_keys/testing_keys.dart`.

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
- Second app instance for sync verification: `pwsh -File tools/start-driver.ps1 -Platform windows -DriverPort 4949`
- Kill: `pwsh -File tools/stop-driver.ps1`

### Android

- `start-driver.ps1` reuses the cached driver APK when tracked inputs are unchanged. Pass `-ForceRebuild` to force a rebuild.
- Android uses mixed port direction:
  ```bash
  adb reverse tcp:3947 tcp:3947
  adb forward tcp:4948 tcp:4948
  ```
- `start-driver.ps1` handles this automatically
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
