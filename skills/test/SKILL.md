---
name: test
description: Run E2E test flows via HTTP driver automation
agents:
  - .claude/agents/test-wave-agent.md
---

# /test — HTTP Driver Test Skill

## Overview
Runs end-to-end test flows against the running app via HTTP driver endpoints (port 4948).
The app must be launched with `main_driver.dart` entrypoint. Agents interact with widgets
via HTTP instead of ADB/UIAutomator, making this cross-platform (Android + Windows).

## Prerequisites
1. Debug server running: `node tools/debug-server/server.js`
2. App launched with driver entrypoint:
   - **Windows:** `pwsh -Command "flutter run --target=lib/main_driver.dart -d windows --dart-define=DEBUG_SERVER=true --dart-define-from-file=.env"`
   - **Android:** `pwsh -File tools/build.ps1 -Platform android -BuildType debug -DebugServer -Target lib/main_driver.dart` → install → `adb reverse tcp:3947 tcp:3947` + `adb reverse tcp:4948 tcp:4948`
3. Auth token captured from flutter run stdout (look for `DRIVER_AUTH_TOKEN=<token>`)
   - **Note:** On Android, the token appears in logcat (filter for "DRIVER_AUTH_TOKEN"), not the build terminal.

## Usage

```
/test                     # Run all 14 proof flows (T01-T14)
/test T01-T06             # Run Tier 1 Foundation only
/test T07-T13             # Run Tier 2 Daily Entry Lifecycle only
/test T14                 # Run Tier 3 PDF Export only
/test T03                 # Run single flow
```

## Architecture

```
Claude (orchestrator)
  ├─ Tier 1 agent (T01-T06) — sequential
  ├─ Tier 2 agent (T07-T13) — sequential (after Tier 1 passes)
  └─ Tier 3 agent (T14)     — sequential (after Tier 2 passes)
```

Each agent:
1. Uses auth token captured from flutter run stdout (provided by orchestrator)
2. Executes driver steps via HTTP (port 4948)
3. Polls sync status via debug server (port 3947)
4. Scans logs for errors
5. Runs verify-sync.ps1 for Supabase confirmation
6. Updates registry with results

## HTTP Driver Endpoints (port 4948)

All require `Authorization: Bearer <token>` header.

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

> **Note:** `/driver/screenshot` returns `image/png` binary, not JSON. Use `curl --output <path>` to save.

## Verification Pipeline (per flow)

```
HTTP driver: create data → trigger sync
    ↓
Poll GET /sync/status (debug server) — wait for completed or idle (30s timeout)
    ↓
GET /logs?since=<start>&category=sync — check for sync errors
GET /logs?since=<start>&level=error — check for runtime errors
    ↓
pwsh -File tools/verify-sync.ps1 -Table X -Filter Y -CountOnly
    ↓
Update .claude/test-flows/registry.md
```

## Error Handling
- **Driver unreachable:** retry once after 2s, then FAIL
- **Element not found:** wait 3s with pumpAndSettle retry, then FAIL
- **Sync timeout (30s):** check /sync/status for error state, FAIL
- **verify-sync no data:** FAIL
- **Logs show errors:** FAIL if sync/db category
- **App crash:** detect via /driver/ready timeout, capture last logs

## Flow Registry
`.claude/test-flows/registry.md` — unified registry with all flows and run history.

## Test Data Safety
- All test projects use "E2E " prefix
- Cleanup: `pwsh -File tools/verify-sync.ps1 -Cleanup -ProjectName "E2E*" -DryRun`
- Results pruning: `pwsh -File tools/prune-test-results.ps1`
