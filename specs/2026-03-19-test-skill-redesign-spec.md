# Test Skill Redesign Spec

## Overview

### Purpose
Redesign the `/test` skill to support HTTP driver-based automation (cross-platform), integrate the debug server for sync lifecycle verification and runtime error detection, and use `verify-sync.ps1` for Supabase data confirmation. Merge the two flow registries into a unified registry that auto-updates after runs.

### Scope

**In scope:**
- HTTP driver endpoints in the Flutter app (debug-only, gated behind `DEBUG_SERVER`)
- Custom app entrypoint `main_driver.dart` using `IntegrationTestWidgetsFlutterBinding`
- Test flow agents that interact with the app via HTTP driver
- Debug server polling for sync status + error log scanning
- Supabase verification via `verify-sync.ps1` as inline post-sync check
- Merged unified flow registry with auto-update
- Build script `-DebugServer` flag for Android debug builds
- Driver authentication via per-session random token
- `TestPhotoService` override for inject-photo
- Script-based test result pruning (`tools/prune-test-results.ps1`)
- Proof with Tier 1 Foundation (T01-T06) + Daily Entry Lifecycle (T07-T13) + PDF Export (T14)

**Out of scope:**
- Remaining flow implementation beyond the 14 proof flows (expand later by adding flow definitions)
- Patrol test migration
- flutter_driver Dart scripts (replaced by HTTP driver)
- UIAutomator XML parsing (replaced by HTTP driver)
- iOS support (dart:io HttpServer requires entitlements on iOS)
- Android network_security_config.xml (Android 12+ permits localhost cleartext by default)

### Success Criteria
- 14 proof flows execute on Windows desktop via HTTP driver
- After each sync flow, debug server confirms sync completed + no errors
- After sync, `verify-sync.ps1` confirms data in Supabase
- PDF export flow produces non-zero file with no debug log errors
- Flow registry auto-updates with PASS/FAIL/SKIP + date
- Same skill works on Android when device is connected

---

## Architecture

### Orchestrator Model

**Claude (in-conversation) is the orchestrator.** No headless CLI process, no separate orchestrator agent.

- Claude parses flags, resolves dependencies, dispatches agents sequentially, presents results
- Between tiers, user and Claude discuss findings, decide next steps, pivot as needed
- The `/test` skill is instructions for Claude, not a separate process
- Agents grouped by tier (3 agents total), sequential execution (single test surface)

```
User <-> Claude (orchestrator-in-conversation)
              |
              |-- dispatch tier agent (Task, one per tier, sequential)
              |      |
              |      |-- POST /driver/tap, /driver/text, etc. -> Flutter app
              |      |-- GET /sync/status -> debug server
              |      |-- GET /logs?since=<start>&level=error -> debug server
              |      |-- pwsh verify-sync.ps1 -CountOnly -> Supabase
              |      |-- Write flow report, update registry
              |      |-- Return: 1-line-per-flow status
              |
              |-- present tier results, discuss with user
              |-- dispatch next tier agent
```

### Agent Grouping

| Agent | Flows | Rationale |
|-------|-------|-----------|
| Tier 1 agent | T01-T06 (foundation) | All share project state, sequential deps |
| Tier 2 agent | T07-T13 (daily entry) | All share entry state, sequential deps |
| Tier 3 agent | T14 (PDF export) | Single flow, distinct verification |

3 agent launches instead of 14. Discussion points between each tier.

### IntegrationTestWidgetsFlutterBinding

The HTTP driver is built on top of `IntegrationTestWidgetsFlutterBinding` — the only Flutter-supported way to reliably:
- `find.byKey()` — locate widgets by ValueKey
- `tap()` — simulate taps with proper gesture handling and hit testing
- `pumpAndSettle()` — pump frames until animations complete
- `takeScreenshot()` — capture the current render tree as PNG

**Custom entrypoint**: `lib/main_driver.dart`
- Initializes `IntegrationTestWidgetsFlutterBinding` instead of `WidgetsFlutterBinding`
- Starts the HTTP driver server on port `4948`
- Generates a random auth token via `Random.secure()`, logs it to stdout + debug server
- Registers `TestPhotoService` override for inject-photo
- Runs the normal app via `runApp()`

**Launch command** (Windows):
```
pwsh -Command "flutter run --target=lib/main_driver.dart -d windows --dart-define=DEBUG_SERVER=true --dart-define-from-file=.env"
```

**Launch command** (Android):
```
pwsh -File tools/build.ps1 -Platform android -BuildType debug -DebugServer -Target lib/main_driver.dart
adb install -r releases/android/debug/app-debug.apk
adb reverse tcp:3947 tcp:3947
adb reverse tcp:4948 tcp:4948
adb shell am start -n com.fieldguideapp.inspector/.MainActivity
```

### HTTP Driver (in-app, debug-only)

Runs inside the Flutter app on port **4948** (separate from debug server on 3947). Gated behind `DEBUG_SERVER=true`. Tree-shaken from release builds.

**Four layers prevent release exposure:**
1. Build script (`build.ps1`): blocks `DEBUG_SERVER=true` in release builds at compile time
2. Dart constant: `const bool.fromEnvironment('DEBUG_SERVER')` compiles to `false` when not defined
3. Runtime guard: `kReleaseMode` check as defense-in-depth
4. Custom entrypoint: `main_driver.dart` is only used for testing — production uses `main.dart`

**Authentication:** Per-session random token generated at startup via `Random.secure()`. All requests require `Authorization: Bearer <token>`. Token is logged to stdout and POST'd to debug server at startup. Requests without valid token receive `403`. Origin header blocking mirrors the debug server pattern.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/driver/tap` | Tap a widget by ValueKey |
| `POST` | `/driver/text` | Enter text into a field by ValueKey |
| `POST` | `/driver/scroll` | Scroll a scrollable by ValueKey |
| `POST` | `/driver/scroll-to-key` | Scroll until a specific key is visible |
| `GET` | `/driver/find` | Check if a widget with key exists |
| `GET` | `/driver/screenshot` | Capture current screen as PNG |
| `GET` | `/driver/tree` | Dump widget tree (default depth=5, configurable via `?depth=N`) |
| `GET` | `/driver/ready` | Returns `{ready: true, screen: "..."}` after first frame renders |
| `POST` | `/driver/back` | Navigate back |
| `POST` | `/driver/wait` | Wait for a key to appear (with timeout, pumps frames until visible+hittable) |
| `POST` | `/driver/inject-photo` | Inject a test image via TestPhotoService |
| `POST` | `/driver/inject-file` | Inject a file path via sandboxed temp directory |

**Threading model:** HTTP requests arrive on Dart event loop. Driver dispatches to main isolate via `WidgetsBinding.instance.scheduleTask()` or `StreamController`. Awaits result, returns HTTP response. All widget interaction runs on the main UI thread.

**`/driver/wait` semantics:** Pumps frames via `pumpAndSettle()` until the widget exists AND is visible AND is hittable AND animations are complete. Not a busy-poll — uses the test binding's frame pump.

### inject-photo / inject-file Security

Both endpoints validate:
- Path is within the app's sandboxed temp directory (`getTemporaryDirectory()`)
- File extension is in allowlist: `jpg`, `png`, `webp` (photo) / `pdf` (file)
- File size is capped at 10 MB
- Path cannot contain `..` or absolute paths outside temp dir
- Agent pre-stages test files to temp dir before calling inject

**`inject-photo` mechanism:** `main_driver.dart` registers a `TestPhotoService` that extends `PhotoService`. When the inject endpoint is called, `TestPhotoService` writes the image to the correct directory and returns the path as if `image_picker` selected it. The normal photo pipeline (EXIF handling, filename sanitization, thumbnail generation) still runs.

### Verification Pipeline (per sync flow)

```
HTTP driver: create data -> trigger sync
    |
Poll GET /sync/status (debug server) -- wait for state: "completed"
    |
GET /logs?since=<flow-start-time>&category=sync -- scan for sync errors/warnings
GET /logs?since=<flow-start-time>&level=error -- catch any runtime errors
    |
Run verify-sync.ps1 -Table X -Filter Y -CountOnly -- confirm data in Supabase
    |
Record result in flow report + update registry
```

Three verification layers per sync flow:
1. **Sync lifecycle** -- did it complete or fail?
2. **Debug server logs** -- any errors, warnings, or unexpected behavior? (uses `since=` timestamp to scope to current flow only)
3. **Supabase data** -- did the data actually land correctly? (agents use `-CountOnly` to avoid PII in flow reports)

For non-sync flows, only layer 2 runs.

### Platform Differences

| Concern | Windows | Android |
|---------|---------|---------|
| App launch | `flutter run --target=lib/main_driver.dart -d windows --dart-define=DEBUG_SERVER=true --dart-define-from-file=.env` | `build.ps1 -DebugServer -Target lib/main_driver.dart` -> `adb install` -> `adb reverse` (ports 3947+4948) -> `adb shell am start` |
| Everything else | HTTP driver + debug server (identical) | HTTP driver + debug server (identical) |

### Agent Model

All test agents use **sonnet** (per user preference: sonnet minimum for all agents).

---

## Unified Flow Registry

Merge the existing ADB registry (`.claude/test-flows/registry.md`, 30 flows + 12 journeys) and the sync verification registry (`.claude/test_results/flow_registry.md`, 42 flows) into one file at `.claude/test-flows/registry.md`.

### Merge Strategy

- Overlapping flows merge -- sync verification steps added to existing flow definitions
- New sync-only flows added as new entries
- Each flow gains new fields: `driver`, `verify-sync`, `verify-logs`

### Flow Definition Format

```yaml
### create-project
- feature: projects
- tier: foundation
- timeout: 120s
- deps: [login]
- driver: http                    # http (HTTP driver) | adb (legacy fallback)
- verify-sync:                    # Supabase verification (null for non-sync flows)
    table: projects
    filter: "name=like.E2E*"
- verify-logs: [sync]             # debug server log categories to check
- steps:
    1. Tap projects nav -> POST /driver/tap {key: "projects_nav_button"}
    2. Tap create -> POST /driver/tap {key: "project_create_button"}
    ...
- verify: Project appears in list. Supabase has matching row.
```

### Auto-Update

After each flow completes, the agent updates the registry with Status, Last Run date, and Notes.

---

## Proof Flows

### Tier 1: Foundation (T01-T06) — Single Agent

| ID | Flow | Table | Verification |
|----|------|-------|-------------|
| T01 | Create project "E2E Test Project" | `projects` | verify-sync + debug logs |
| T02 | Add location | `locations` | verify-sync |
| T03 | Add contractor | `contractors` | verify-sync |
| T04 | Add equipment | `equipment` | verify-sync |
| T05 | Add pay item | `bid_items` | verify-sync |
| T06 | Add project assignment | `project_assignments` | verify-sync |

### Tier 2: Daily Entry Full Lifecycle (T07-T13) — Single Agent

| ID | Flow | Table | Verification |
|----|------|-------|-------------|
| T07 | Create daily entry | `daily_entries` | verify-sync |
| T08 | Add personnel log | `entry_personnel_counts` | verify-sync |
| T09 | Add equipment usage | `entry_equipment` | verify-sync |
| T10 | Log quantities | `entry_quantities` | verify-sync |
| T11 | Attach photo (via inject-photo) | `photos` | verify-sync |
| T12 | Create todo | `todo_items` | verify-sync |
| T13 | Fill inspector form | `inspector_forms` | verify-sync |

### Tier 3: PDF Export (T14) — Single Agent

| ID | Flow | Verification |
|----|------|-------------|
| T14 | Export daily entry to PDF | PDF file exists, non-zero bytes, no debug log errors |

### Flow Dependencies

```
T01 (project) -> T02 (location), T03 (contractor), T05 (pay item), T06 (assignment)
T03 (contractor) -> T04 (equipment)
T01 (project) -> T07 (entry)
T07 (entry) -> T08 (personnel), T09 (equipment usage), T10 (quantities), T11 (photo), T12 (todo), T13 (form)
T07 (entry) -> T14 (PDF export)
```

### Cleanup

After the proof run: `verify-sync.ps1 -Cleanup -ProjectName "E2E Test Project"` removes all test data from Supabase.

If cleanup fails, abort the next run and alert the user. Pre-run: delete all SQLite records with "E2E " prefix to prevent stale local state from prior failed runs.

---

## Error Handling

### Agent-Level

| Scenario | Action |
|----------|--------|
| HTTP driver endpoint unreachable | Retry once after 2s. If still down, FAIL with "driver not responding" |
| Element not found by key | Wait 3s, retry with pumpAndSettle. If still missing, check debug logs, FAIL with element name |
| Sync doesn't complete within 30s | Check `GET /sync/status` for error state. FAIL with sync state details |
| verify-sync.ps1 finds no data | FAIL -- data didn't land in Supabase. Include table name and filter |
| Debug server logs show errors | Record in flow report. If `level=error` with sync/db category, FAIL |
| App crashes mid-flow | Detect via HTTP driver timeout. FAIL, capture last debug logs |
| PDF export produces 0-byte file | FAIL with file path and debug log excerpt |

### Orchestrator-Level (Claude)

| Scenario | Action |
|----------|--------|
| Flow FAILs | Present failure + debug logs to user. Ask: continue, investigate, or stop? |
| Dependency failed | Auto-SKIP dependent flows. Report which were skipped and why |
| Debug server not running | Detect before dispatching. Start it or ask user |
| App not running | Detect before dispatching. Launch it or ask user |
| Agent returns unexpected output | Read flow report from disk, present raw findings |
| Cleanup fails | Abort next run, alert user |

### Test Data Safety

- All test projects use `"E2E "` prefix -- enforced by agents
- Cleanup via `verify-sync.ps1 -Cleanup` after run
- Agents never modify non-test data
- HTTP driver endpoints are debug-only (tree-shaken from release, custom entrypoint)
- Driver requires per-session auth token
- Agents use `-CountOnly` for verify-sync (no PII in flow reports)
- `MOCK_AUTH=true` and `DEBUG_SERVER=true` must NOT be combined in the same build (enforced in build.ps1)

---

## Output & Registry

### Run Directory Structure

```
.claude/test-results/
  YYYY-MM-DD_HHmm_{descriptor}/
    run-summary.md
    screenshots/{flow}-{step:02d}-{desc}.png
    flows/{flow}.md                # includes sync verification results
    debug-logs/{flow}-logs.json    # debug server logs snapshot per flow
```

### Flow Report Format

```markdown
# Flow: T01 -- Create Project + Push

**Status**: PASS
**Duration**: 45s
**Feature**: projects

## Steps
1. Tap projects nav -> SUCCESS
2. Tap create button -> SUCCESS
3. Enter "E2E Test Project" -> SUCCESS
4. Tap save -> SUCCESS
5. Trigger sync -> SUCCESS

## Sync Verification
- **Sync status**: completed (2.3s)
- **Debug logs**: 0 errors, 3 info
- **Supabase**: projects row count confirmed (1 row)

## Notes
{observations}
```

### Retention

Script-based pruning via `tools/prune-test-results.ps1` — keeps last 5 run directories, deletes oldest. Called at the start of every test run (not reliant on agent memory).

---

## Build Script Changes

### `build.ps1` updates

1. **New `-DebugServer` switch**: Appends `--dart-define=DEBUG_SERVER=true` to build args. Only valid with `-BuildType debug`.
2. **New `-Target` parameter**: Specifies custom entrypoint (default: `lib/main.dart`). Used with `lib/main_driver.dart` for testing.
3. **Block `MOCK_AUTH + DEBUG_SERVER` combination**: If `.env` contains both `MOCK_AUTH=true` and the `-DebugServer` flag is set, error out.
4. **Existing release guard unchanged**: `DEBUG_SERVER=true` in `.env` with non-debug build type still errors.

### `.gitignore` updates

- Broaden `.env.secret` to `*.secret` to catch variants like `.env.secret.bak`
- Verify `.claude/test-results/` is gitignored in both app repo and claude-config repo

---

## New Files

| File | Purpose |
|------|---------|
| `lib/main_driver.dart` | Custom entrypoint with IntegrationTestWidgetsFlutterBinding + HTTP driver server |
| `lib/core/driver/driver_server.dart` | HTTP driver server implementation (routes, auth, widget interaction) |
| `lib/core/driver/test_photo_service.dart` | TestPhotoService override for inject-photo |
| `tools/prune-test-results.ps1` | Script-based test result pruning |
| `.claude/test-flows/registry.md` | Merged unified flow registry (replaces both existing registries) |

### Modified Files

| File | Change |
|------|--------|
| `tools/build.ps1` | Add `-DebugServer`, `-Target`, MOCK_AUTH+DEBUG_SERVER block |
| `.gitignore` | Broaden `.env.secret` -> `*.secret` |
| `.claude/skills/test/SKILL.md` | Full rewrite to new architecture |
| `.claude/agents/test-wave-agent.md` | Rewrite for HTTP driver, sonnet model, tier-based grouping |

---

## Decisions Made

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| HTTP driver over flutter_driver | Cross-platform, agent autonomy, no Dart test files needed | flutter_driver (requires Dart scripts, less agent autonomy), ADB-only (Windows blocked) |
| IntegrationTestWidgetsFlutterBinding | Only Flutter-supported way to tap/find/pump widgets reliably | Raw element tree walk (fragile, no frame pump, unsupported) |
| Custom entrypoint (main_driver.dart) | Separates test binding from production binding | Shared main.dart with conditional binding (risk of test code in prod) |
| Per-session random auth token | Driver is bidirectional control surface, needs auth. Rotating token prevents replay | Static token (can be captured), no auth (any localhost process can control app) |
| Port 4948 for driver | Avoids conflict with debug server on 3947. Both need ADB forwarding on Android | Same port (conflict), dynamic port (harder to discover) |
| Claude as orchestrator | Interactive discussion during testing, no headless CLI needed | Headless orchestrator (can't discuss findings), separate orchestrator agent |
| Group by tier (3 agents) | Reduces startup overhead from 14 to 3 launches. Discuss between tiers | One-per-flow (slow), one agent for all (no discussion points) |
| TestPhotoService override | Bypasses system dialog while keeping photo pipeline intact (EXIF, sanitization) | Direct SQLite insert (skips pipeline), mock image_picker (complex package mocking) |
| Inline verification with -CountOnly | Catches failures at exact flow without persisting PII in reports | Full row output (PII risk), post-run verification (harder to trace) |
| Script-based pruning | Reliable retention, doesn't depend on agent memory | Agent-enforced (can forget), no pruning (PII accumulation) |
| Merged registry | Single source of truth for all test coverage | Separate registries (duplicate tracking, confusing) |
| Sonnet for agents | User preference: sonnet minimum | Haiku (too weak per user preference) |
| since= for log queries | Prevents cross-flow log bleed, accurate per-flow error detection | last=N (may include prior flow's logs) |
| /driver/tree depth=5 default | Captures meaningful widgets without internal Flutter plumbing | No limit (megabytes of JSON), depth=3 (misses some useful nodes) |
| *.secret gitignore pattern | Catches .env.secret.bak and similar variants | Exact match (misses variants) |
| Skip network_security_config | Android 12+ permits localhost cleartext by default, minSdk=31 | Add config (unnecessary for current minSdk) |
| Skip company_id cleanup scope | E2E prefix is sufficient safety guard | Add company_id (over-engineering for single-dev project) |
