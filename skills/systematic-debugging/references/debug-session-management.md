# Debug Session Management

Reference for server setup, session lifecycle, cleanup rules, deep mode agent management, and reproduction interviews.

---

## Server Setup Checklist

### Start the debug server

```bash
node tools/debug-server/server.js
```

Expected output:
```
Debug server listening on http://127.0.0.1:3947
```

Leave this terminal open for the duration of the session.

### Android: ADB port forwarding

Required every time you connect a device or restart ADB:

```bash
adb devices          # confirm device listed
adb reverse tcp:3947 tcp:3947
```

Verify forwarding is active:
```bash
adb forward --list   # should show tcp:3947
```

### Launch app with debug server enabled

Android:
```bash
pwsh -Command "flutter run -d <device-serial> --dart-define=DEBUG_SERVER=true"
```

Windows desktop:
```bash
pwsh -Command "flutter run -d windows --dart-define=DEBUG_SERVER=true"
```

**Security note**: `DEBUG_SERVER=true` is blocked in release builds by `tools/build.ps1`. Never add it to `.env`.

### Verify connection

```bash
curl http://127.0.0.1:3947/health
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
2. Reuses the current Android driver build when inputs are unchanged, or rebuilds when they are stale
3. Launches the app with `--target=lib/main_driver.dart --dart-define=DEBUG_SERVER=true`
4. Sets up Android ports with `adb reverse tcp:3947 tcp:3947` and `adb forward tcp:4948 tcp:4948`
5. Supports a second desktop driver instance with `-DriverPort 4949`
6. Polls readiness until both servers respond

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

DEFECT LOG (GitHub Issues) (Phase 10)
  └─> Record new patterns to GitHub Issue

END
```

---

## Cleanup Gate Rules

Phase 9 is a hard gate. The session is NOT complete until:

1. Every `Logger.hypothesis()` call added in this session is deleted from source files
2. Global search `Grep "hypothesis(" lib/` returns zero matches
3. Session log written to `.claude/debug-sessions/YYYY-MM-DD_{bug-slug}.md`
4. 30-day retention pruning completed (check folder, ask user to confirm deletions)

**Enforcement**: If a hypothesis marker is found in a later code review or by another agent, it represents a cleanup failure. The session log must record it as an open item.

---

## Deep Mode: Research Agent Management

### When to use Deep mode

Use Deep mode when the bug is:
- Intermittent (hard to reproduce reliably)
- Involves async timing or race conditions
- Touches multiple subsystems
- Has no obvious error message to trace
- Has already resisted Quick mode investigation

### Launching the research agent

At session start (before Phase 1), invoke `debug-research-agent` with context:

```
Launch debug-research-agent with run_in_background: true.
Provide:
- Bug description: [one sentence]
- Suspected code paths: [list from codebase-tracing-paths.md]
- Hypothesis to investigate: [what you think might be wrong]
```

### Stop conditions for the agent

The agent stops when it has either:
- Exhausted 15 tool calls
- Produced a complete research report

Do NOT re-launch the agent after it completes. Read its output once in Phase 5.

### Reading agent output

The agent produces:
- Code path trace with file:line references
- Potential root causes ranked by likelihood
- Related defects found in GitHub Issues
- Suggested `Logger.hypothesis()` instrumentation points

Integrate these with the actual log evidence from the server. Agent research is a hypothesis source — log evidence is the ground truth.

---

## Reproduction Interview Questions

Ask all five before the user reproduces the bug:

1. **Steps**: "What exact steps trigger the bug? Walk me through from app launch."
2. **Frequency**: "How often does it happen — always, intermittent, only after specific actions, only first launch?"
3. **Environment**: "What device and OS? Android version? Windows?"
4. **Regression**: "When did this last work correctly?"
5. **Changes**: "What changed since it last worked — commits, new data entered, permissions changed, app reinstalled?"

These answers narrow the hypothesis space before log evidence is collected. Document the answers in the session log.

---

## 30-Day Retention Pruning

Session logs in `.claude/debug-sessions/` older than 30 days should be reviewed for deletion.

During Phase 9:

```bash
ls -la .claude/debug-sessions/
```

Identify files with dates more than 30 days before today. List them and ask the user:

> "These session logs are older than 30 days: [list]. Delete them to comply with retention policy?"

Wait for explicit confirmation before deleting. Do NOT auto-delete.

---

## Quick Server Reference

| Command | Purpose |
|---------|---------|
| `curl http://127.0.0.1:3947/health` | Check server running + entry count |
| `curl "http://127.0.0.1:3947/logs?last=20"` | Recent logs |
| `curl "http://127.0.0.1:3947/logs?hypothesis=H001"` | Filter by hypothesis |
| `curl "http://127.0.0.1:3947/logs?category=sync"` | Filter by category |
| `curl http://127.0.0.1:3947/categories` | List active categories |
| `curl -X POST http://127.0.0.1:3947/clear` | Clear buffer |
| `adb reverse tcp:3947 tcp:3947` | Android port forwarding |

### Driver Server

See `driver-integration.md` for the full driver API reference, login procedures, and repro-steps JSON format.

**Launch/stop commands:**

| Command | Purpose |
|---------|---------|
| `pwsh -File tools/start-driver.ps1 -Platform windows` | Start driver environment |
| `pwsh -File tools/start-driver.ps1 -Platform windows -DriverPort 4949` | Start second desktop driver instance |
| `pwsh -File tools/start-driver.ps1 -Platform android -ForceRebuild` | Force Android driver rebuild + reinstall |
| `pwsh -File tools/stop-driver.ps1` | Stop app (keep debug server) |
| `pwsh -File tools/stop-driver.ps1 -IncludeDebugServer` | Stop app + debug server |
