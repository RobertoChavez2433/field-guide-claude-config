---
name: systematic-debugging
description: Log-first root cause analysis framework with HTTP server integration, hypothesis tagging, and structured cleanup gates
user-invocable: true
---

# Systematic Debugging Skill

**Purpose**: Interactive root cause analysis framework with log-first investigation. Investigates bugs WITH the user, never autonomously.

## CRITICAL: This Skill Is Interactive

**This skill runs in the main conversation.** Code changes require explicit user approval.

- **Show progress** at every step — the user must see what you're doing
- **Present findings** after each phase before moving on
- **NEVER write code** without explicit user approval
- **NEVER skip to implementation** — investigation comes first, always
- **Deep mode only**: subagents run for parallel read-only research

## Iron Law

> **NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST**

Every fix must be preceded by understanding WHY the bug exists. Guessing wastes time and creates new bugs.

---

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

---

## Phase 1: TRIAGE

**Goal**: Establish clean baseline before touching anything.

### 1.1 Scan for orphaned hypothesis markers

Search for leftover markers from previous sessions:

```bash
# Search entire codebase for hypothesis markers
Grep "hypothesis(" lib/ --output_mode=files_with_matches
```

If any found: list them to the user. Ask if they belong to this session or are orphaned. Orphaned markers MUST be removed before continuing.

### 1.2 Check server health (Deep mode only)

```bash
curl http://127.0.0.1:3947/health
```

Expected response: `{"status":"ok","entries":N,"maxEntries":30000,"memoryMB":N,"uptimeSeconds":N}`

If server not running, prompt user to start it:
```
node tools/debug-server/server.js
```

For Android devices, set up ADB port forwarding:
```
adb reverse tcp:3947 tcp:3947
```

### 1.3 Clear previous session logs (Deep mode only)

```bash
curl -X POST http://127.0.0.1:3947/clear
```

This ensures evidence from this session is not mixed with old data.

### 1.4 Check known defects

Query GitHub Issues for the relevant feature:

```bash
gh issue list --repo RobertoChavez2433/construction-inspector-tracking-app --label "{feature}" --state open --json number,title,body --limit 20
```

Scan issue titles and bodies for categories: `[ASYNC]`, `[SYNC]`, `[DATA]`, `[CONFIG]`, `[SCHEMA]`, `[FLUTTER]`, `[E2E]`, `[MIGRATION]`.

If a known pattern matches: apply documented prevention. May resolve without further investigation.

**Present triage findings to user before Phase 2.**

---

## Phase 2: COVERAGE CHECK

**Goal**: Understand what the Logger already captures in the relevant code path.

### 2.1 Identify the code path

Use codebase-tracing-paths.md to map the likely flow. Example: "Sync not pushing entries" → SyncProvider → SyncOrchestrator → SyncEngine → TableAdapter.

### 2.2 Assess existing Logger coverage

For each file in the path:
```bash
Grep "Logger\." lib/features/sync/engine/sync_engine.dart --output_mode=content
```

Note: which entry/exit points are already logged? Which boundaries have no coverage?

### 2.3 Identify gaps

List boundaries that have zero Logger calls. These are blind spots where the bug could hide undetected.

**Present coverage map to user before Phase 3.**

---

## Phase 3: INSTRUMENT GAPS

**Goal**: Add targeted instrumentation so the bug leaves evidence.

### 3.1 Add hypothesis markers at key boundaries

Use `Logger.hypothesis()` for temporary markers scoped to this session:

**Auth restriction**: NEVER log tokens, passwords, API keys, or session secrets — even in hypothesis markers. See auth blocklist in log-investigation-and-instrumentation.md.

```dart
Logger.hypothesis('H001', 'sync', 'SyncEngine.push entry point', data: {
  'pendingCount': pendingChanges.length,
  'userId': currentUserId,
});
```

Naming convention: `H001`, `H002`, etc. (reset each session).

### 3.2 Fill permanent Logger gaps

If a code boundary has no Logger coverage at all (not just missing hypothesis markers), add a permanent Logger call using the appropriate category:

```dart
Logger.sync('SyncEngine.push', data: {'table': tableName, 'operation': op});
```

These are KEPT after the session (they fill genuine coverage gaps).

### 3.3 Proceed to Phase 3.5

Instrumentation is complete. Phase 3.5 (LAUNCH DRIVER) will build and launch the app with the driver entrypoint and `DEBUG_SERVER=true` flag.

**Do NOT manually run `flutter run` here** -- `start-driver.ps1` handles the build, launch, and readiness polling in one step.

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

---

## Phase 5: EVIDENCE ANALYSIS

**Goal**: Read log evidence to form a data-driven hypothesis.

### 5.1 Fetch hypothesis-tagged logs

```bash
curl "http://127.0.0.1:3947/logs?hypothesis=H001&last=100"
curl "http://127.0.0.1:3947/logs?hypothesis=H002&last=100"
```

### 5.2 Fetch by category

```bash
curl "http://127.0.0.1:3947/logs?category=sync&last=50"
curl "http://127.0.0.1:3947/logs?category=error&last=20"
```

### 5.3 Check available categories

```bash
curl http://127.0.0.1:3947/categories
```

### 5.4 Read agent research (Deep mode)

If the research agent has completed, read its output. Integrate its findings with the log evidence.

### 5.5 Identify the failure point

The failure point is where expected log entries STOP appearing or where values diverge from expected. Document:
- Last correct log entry (file:line, hypothesis ID, value)
- First incorrect/missing log entry
- Any error entries in the error category

### 5.6 Quick mode investigation

Without a log server, use:
```bash
# ADB logcat for Android
adb logcat -s flutter | grep -i error

# Flutter console (terminal running flutter run)
# Look for exceptions and stack traces
```

---

## Phase 6: ROOT CAUSE REPORT

**Goal**: Present findings for user approval before touching any code.

### Report format

Present a structured report:

```
ROOT CAUSE ANALYSIS

Bug: [one-sentence description]

Evidence:
- H001 fired at sync_engine.dart:142 with pendingCount=3
- H002 never fired → push() not reached
- Error log: "FK constraint failed" at 14:23:05.441

Root Cause:
The sync engine is not calling push() when pendingCount > 0 because [specific condition].
The upstream origin is [file:line] where [condition] prevents the call.

Proposed Fix:
[Describe the fix — do NOT implement yet]

Files that would change:
- lib/features/sync/engine/sync_engine.dart (line ~142)

Risk: Low / Medium / High — [reason]
```

### USER GATE — stop here

**STOP. Present the report. Wait for user approval.**

User options:
- "Approved" → proceed to Phase 7
- "Investigate more" → return to Phase 5
- "Wrong direction" → return to Phase 2
- "Defer" → skip to Phase 9 (cleanup only)

**NEVER auto-proceed to implementation.**

---

## Phase 7: FIX

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

---

## Phase 8: INSTRUMENTATION REVIEW

**Goal**: Decide which markers to keep and which to remove.

### For each hypothesis marker added in Phase 3:

| Decision | Criteria |
|----------|----------|
| REMOVE | Temporary hypothesis tag (H001, H002, etc.) — always remove |
| KEEP | Fills a genuine permanent coverage gap with no other Logger call at that boundary |

Present a table to the user:

```
Marker  | File:Line           | Decision | Reason
H001    | sync_engine.dart:142 | REMOVE   | Hypothesis confirmed, gap now covered by H002's permanent replacement
H002    | sync_engine.dart:198 | KEEP     | No other Logger.sync() at this push() entry point
```

Wait for user confirmation on any "KEEP" decisions.

---

## Phase 9: CLEANUP HARD GATE

**This phase is MANDATORY. It cannot be skipped.**

### 9.1 Remove ALL hypothesis markers

For every marker marked REMOVE in Phase 8:

1. Find and delete the `Logger.hypothesis()` call
2. Verify the file compiles (no dangling variables)

### 9.2 Global search — no markers left behind

```bash
Grep "hypothesis(" lib/ --output_mode=files_with_matches
```

**If this returns ANY results: stop. Remove remaining markers. Re-run search.**

Zero results required to proceed.

### 9.3 Write session log

Create a scrubbed session log at `.claude/debug-sessions/YYYY-MM-DD_{bug-slug}.md`:

```markdown
# Debug Session: {bug-slug}
Date: YYYY-MM-DD
Duration: ~Xh
Mode: Quick / Deep

## Bug
[One-sentence description]

## Root Cause
[Finding, with file:line references]

## Fix Applied
[What was changed and why]

## Markers Added (Permanent)
- Logger.sync() at sync_engine.dart:198 — push() entry coverage

## Markers Removed
- H001, H002 — hypothesis confirmed and removed
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

---

## Phase 10: DEFECT LOG

**Goal**: Record new patterns for future prevention.

If this bug represents a new pattern not already in GitHub Issues for this feature:

1. Identify category: `[ASYNC]`, `[SYNC]`, `[DATA]`, `[CONFIG]`, `[SCHEMA]`, `[FLUTTER]`, `[E2E]`, `[MIGRATION]`
2. Create a GitHub Issue:

```bash
pwsh -File tools/create-defect-issue.ps1 `
    -Title "[CATEGORY] YYYY-MM-DD: Brief Title" `
    -Feature "{feature}" `
    -Type "defect" `
    -Priority "{priority}" `
    -Layer @("{layer:...}") `
    -Body "**Pattern**: What caused the issue`n**Prevention**: How to avoid it next time" `
    -Ref "lib/features/sync/engine/sync_engine.dart:142"
```

---

## Red Flags — STOP and Return to Phase 1

These thought patterns mean you're off-track:

- "Let me just try one more thing…"
- "I think I see the problem" (before log evidence confirms it)
- "This is probably caused by…" (without data)
- "The fix didn't work but the next one will"
- Starting to modify code before you can explain WHY the bug exists

## Stop Conditions

**STOP and reassess if:**
- 3+ failed fix attempts — likely architectural issue
- Fix requires changing 5+ files — scope too broad, needs plan
- You can't explain root cause in one sentence — go back to Phase 5
- "Fix" suppresses symptoms without addressing cause

## User Signals

| User says | Your response |
|-----------|---------------|
| "Stop guessing" | Return to Phase 5. State evidence you have and what's unknown. |
| "Ultrathink this" | Reason through full system before touching code. |
| "Walk me through it" | Explain data flow from log evidence, not assumption. |
| "You've been on this too long" | Summarize hypotheses, what's ruled out, ask for guidance. |

## Rationalization Prevention

| If You Think... | Stop And... |
|-----------------|-------------|
| "Let me just try this quick fix" | Form a hypothesis first, check Phase 5 |
| "I'll add a retry and see if it helps" | Find the root cause |
| "The tests are flaky, I'll skip them" | Find why they're flaky |
| "One more fix and it'll work" | Count attempts — if ≥ 3, STOP |
| "I see the problem" | Verify with log evidence before touching code |
| "The pattern is too long to trace fully" | That's exactly when you must trace it |

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
