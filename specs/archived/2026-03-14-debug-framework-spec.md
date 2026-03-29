# Debug Framework Spec — Unified Logging, HTTP Log Server, and Debug Skill

**Date:** 2026-03-14
**Status:** Final — adversarial review complete, all MUST-FIX items addressed

---

## 1. Overview

### Purpose
Design and build a runtime debugging and inspection framework for the Construction Inspector App. Three components:

1. **Unified Logger** — A single logging API consolidating `AppLogger` + `DebugLogger`. File transport is always-on (categorized logs for users to send for support). HTTP transport is opt-in for developer debug sessions only.
2. **HTTP Log Server** — A lightweight Node.js server collecting structured, hypothesis-tagged logs over HTTP during active debug sessions. Claude reads from it. Supports clear-between-reproductions, category filtering, and cross-platform collection (Windows desktop, Android devices via ADB port forwarding).
3. **Debug Skill** — A redesigned `systematic-debugging` skill orchestrating the workflow: check for orphaned markers → check log coverage → instrument gaps → user reproduces → Claude reads structured logs from server → hypothesis confirmation → fix → justify instrumentation retention. Solo mode for standard bugs, Opus research agent running in parallel for deep sessions.

### Scope

**Included:**
- Unified logger design (single API, file transport always-on, HTTP transport opt-in)
- Sensitive data filter on HTTP transport (blocklist scrubbing PII/tokens before sending)
- HTTP log server (Node.js, structured JSON, hypothesis tagging, clear/filter endpoints)
- ADB port forwarding setup for Android device → dev machine log delivery (USB only)
- Redesigned SKILL.md with log-first workflow and deep debug agent mode
- 4 reference files rebuilt from scratch with audited, accurate codebase content
- Hypothesis tagging with region markers for instrumentation lifecycle
- Instrumentation retention review with keep/remove justification
- Debug session logs preserved in `.claude/debug-sessions/` (scrubbed of sensitive data)
- Orphaned marker recovery from crashed previous sessions

**Not included (future work):**
- Full testing pyramid design (unit/widget/integration/E2E strategy)
- External crash reporting (Sentry, Crashlytics)
- Production log aggregation
- CI/CD test integration
- WiFi-based Android debugging (removed — security risk on shared networks)

### Success Criteria
- [ ] Single `Logger` API with file transport (always-on, user-facing) and HTTP transport (debug sessions only)
- [ ] Sensitive data filter scrubs PII/tokens from HTTP transport before sending
- [ ] Existing categorized file logging preserved and enhanced — users can still send logs for support
- [ ] HTTP log server accepts structured logs, supports clear/filter, readable by Claude
- [ ] Android devices deliver logs to dev machine via ADB USB port forwarding
- [ ] Debug skill defaults to reading server logs before reading code
- [ ] Hypothesis tagging with region markers enables clean instrumentation lifecycle
- [ ] Orphaned markers from crashed sessions detected and cleaned on session start
- [ ] Every codebase reference in the skill is verified against current source
- [ ] Deep debug mode launches Opus research agent running in background for true parallel investigation
- [ ] Mandatory cleanup verification — zero stray `#region debug-hypothesis` markers after every session
- [ ] Session logs preserved in `.claude/debug-sessions/` (scrubbed, with retention policy)
- [ ] `DEBUG_SERVER` blocked in release builds by both runtime assertion and build script guard

---

## 2. Technical Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────┐
│                    Flutter App                       │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │            Unified Logger API                │    │
│  │  Logger.sync(msg, {data})                    │    │
│  │  Logger.pdf(msg, {data})                     │    │
│  │  Logger.db(msg, {data})                      │    │
│  │  Logger.auth(msg, {data})                    │    │
│  │  Logger.ocr(msg, {data})                     │    │
│  │  Logger.nav(msg, {data})                     │    │
│  │  Logger.ui(msg, {data})                      │    │
│  │  Logger.error(msg, {error, stack, category}) │    │
│  │  Logger.hypothesis(id, category, msg, {data})│    │
│  └──────────┬──────────────────┬────────────────┘    │
│             │                  │                      │
│     ┌───────▼───────┐  ┌──────▼──────────┐          │
│     │ File Transport │  │ HTTP Transport  │          │
│     │ (always on)    │  │ (DEBUG_SERVER   │          │
│     │                │  │  compile-time   │          │
│     │ sync.log       │  │  gated, tree-   │          │
│     │ pdf_import.log │  │  shaken from    │          │
│     │ database.log   │  │  release builds)│          │
│     │ auth.log       │  │                 │          │
│     │ ocr.log        │  │ Sensitive data  │          │
│     │ errors.log     │  │ filter applied  │          │
│     │ navigation.log │  │ before sending  │          │
│     │ ui.log         │  └──────┬──────────┘          │
│     │ app_session.log│         │                      │
│     └────────────────┘         │                      │
└────────────────────────────────┼──────────────────────┘
                                 │
          ┌──────────────────────┘
          │  localhost:3947 (direct on Windows)
          │  adb reverse tcp:3947 tcp:3947 (Android USB)
          │
┌─────────▼─────────────────────────────────────┐
│           Debug Log Server (Node.js)           │
│                                                │
│  POST /log      — receive structured log entry │
│  POST /clear    — wipe logs for fresh repro    │
│  GET  /logs     — return all collected logs    │
│  GET  /logs?hypothesis=A — filter by hypothesis│
│  GET  /logs?category=sync — filter by category │
│  GET  /logs?since=<ISO8601> — time window      │
│  GET  /logs?level=error — filter by level      │
│  GET  /logs?last=50 — most recent N entries    │
│  GET  /health   — server status check          │
│  GET  /categories — category counts            │
│                                                │
│  Storage: in-memory (max 30k entries, 100MB)   │
│  Format: NDJSON                                │
│  SIGINT handler: dumps to last-session.ndjson  │
│  CLI: --port <N> (default 3947)                │
└────────────────────────────────────────────────┘
          │
          │  Claude reads via Bash (curl)
          ▼
┌────────────────────────────────────────────────┐
│           Debug Skill (Claude)                  │
│                                                 │
│  Solo Mode:                                     │
│    Claude reads server → analyzes → hypothesizes│
│    → instruments gaps → user reproduces         │
│    → reads again → confirms root cause          │
│                                                 │
│  Deep Debug Mode:                               │
│    + Opus research agent in background          │
│    + Agent forms hypotheses from code reading   │
│    + Claude correlates agent findings with logs  │
└─────────────────────────────────────────────────┘
```

### Log Entry Schema

```json
{
  "timestamp": "2026-03-14T10:23:45.001Z",
  "category": "sync",
  "level": "debug",
  "message": "adapter push completed",
  "data": {
    "adapter": "ProjectAdapter",
    "rowCount": 3,
    "duration_ms": 142
  },
  "hypothesis": null,
  "deviceId": "DESKTOP-ABC123"
}
```

- `hypothesis`: `null` for permanent logging, `"A"`-`"E"` for hypothesis-tagged debug instrumentation
- `deviceId`: `Platform.localHostname` by default — distinguishes logs from multiple devices hitting the same server
- `data`: any `Map<String, dynamic>` — structured, AI-readable. **Scrubbed of sensitive keys before HTTP transport sends** (see Security section). **Truncated to 4KB serialized** — larger payloads replaced with `{"_truncated": true, "_size": N, "_keys": [...]}`
- `source` field: **not auto-populated**. Dart lacks `__FILE__`/`__LINE__` macros and `StackTrace.current` is expensive. Developers may optionally pass `source` as a key in `data` when manually useful, but it is not part of the schema contract.

### Compile-Time Gating

```dart
class Logger {
  static const _httpEnabled = bool.fromEnvironment('DEBUG_SERVER');

  static void sync(String msg, {Map<String, dynamic>? data}) {
    _fileTransport.write(category: 'sync', msg: msg, data: data);
    if (_httpEnabled) {
      assert(!kReleaseMode, 'DEBUG_SERVER must not be enabled in release builds');
      _httpTransport.send(category: 'sync', msg: msg, data: _scrub(data));
    }
  }

  // Hypothesis logs ONLY go to HTTP transport — ephemeral debug artifacts
  static void hypothesis(String id, String category, String msg,
      {Map<String, dynamic>? data}) {
    if (_httpEnabled) {
      assert(!kReleaseMode, 'DEBUG_SERVER must not be enabled in release builds');
      _httpTransport.send(
        category: category, msg: msg, data: _scrub(data), hypothesis: id);
    }
  }

  /// Scrubs sensitive keys before HTTP transmission.
  /// File transport is NOT scrubbed — local files are user-controlled.
  static Map<String, dynamic>? _scrub(Map<String, dynamic>? data) {
    if (data == null) return null;
    const sensitiveKeys = {
      'access_token', 'refresh_token', 'token', 'jwt',
      'password', 'secret', 'api_key', 'apiKey', 'anon_key',
      'anonKey', 'service_role_key', 'email', 'phone',
      'cert_number', 'inspector_name', 'inspector_initials',
    };
    final scrubbed = data.map((k, v) =>
      MapEntry(k, sensitiveKeys.contains(k.toLowerCase()) ? '[REDACTED]' : v));
    // Truncate large payloads
    final serialized = jsonEncode(scrubbed);
    if (serialized.length > 4096) {
      return {'_truncated': true, '_size': serialized.length, '_keys': scrubbed.keys.toList()};
    }
    return scrubbed;
  }
}
```

- `bool.fromEnvironment` is tree-shaken by Dart compiler — HTTP transport code removed from release binaries
- `assert(!kReleaseMode)` catches any build misconfiguration at runtime (defense-in-depth)
- `_scrub()` removes sensitive keys and truncates large payloads before HTTP transmission
- File transport is NOT scrubbed — local files are user-controlled and already contain this data
- `Logger.hypothesis()` only writes to HTTP — never touches file logs
- All other `Logger.*()` calls write to files always, and additionally to HTTP when enabled

### Security Constraints

| Concern | Mitigation |
|---------|-----------|
| HTTP transport in production | Compile-time gated via `DEBUG_SERVER`. Tree-shaken from release. Runtime `assert(!kReleaseMode)`. Build script rejects `DEBUG_SERVER` in release builds. |
| Sensitive data in logs | Blocklist filter scrubs tokens, PII, API keys from HTTP transport. File transport unaffected (already local). |
| Large data payloads | 4KB per-entry limit on HTTP transport. Truncated with key list preserved. |
| Port exposure on device | No port opened on device. ADB reverse maps device's localhost to dev machine. |
| Port forwarding for field users | `adb reverse` requires USB + authorized ADB. Only dev runs this manually. Not in app. |
| Server access | Binds to `127.0.0.1` only. Only accessible from dev machine. |
| Session logs in `.claude/` | Scrubbed of sensitive data before writing. Added to config repo `.gitignore`. 30-day retention policy. |
| WiFi debugging | **Removed from spec.** Plaintext HTTP on shared networks is unacceptable. USB-only for Android. |

### Platform-Specific Log Access

| Platform | How Claude reads logs | Setup required |
|----------|----------------------|----------------|
| Windows desktop | `curl http://127.0.0.1:3947/logs` | Start server, run app with `DEBUG_SERVER=true` |
| Android (USB) | Same curl — ADB reverse maps the port | `adb reverse tcp:3947 tcp:3947` once per session |

---

## 3. Unified Logger Design

### Current State (Being Replaced)

Two overlapping loggers:

**`AppLogger`** (`lib/core/logging/app_logger.dart`):
- Flat session file: `field_guide_logs/app_log_<timestamp>.txt`
- Hooks `debugPrint` globally via `_installDebugPrintHook()`
- Installs `FlutterError.onError` and `PlatformDispatcher.instance.onError`
- Captures all `print()` via `ZoneSpecification`
- `AppLifecycleLogger` attached as `WidgetsBindingObserver`
- Gated by `APP_FILE_LOGGING` compile-time flag (default: true)

**`DebugLogger`** (`lib/core/logging/debug_logger.dart`):
- Category-based, separate files in `Troubleshooting/Detailed App Wide Logs/session_YYYY-MM-DD_HH-MM-SS/`
- 9 log files: `app_session.log`, `ocr.log`, `pdf_import.log`, `sync.log`, `database.log`, `auth.log`, `navigation.log`, `errors.log`, `ui.log`
- Structured data support: `data: {'key': value}` JSON-encoded inline
- Build metadata: `BUILD_SHA`, `BUILD_BRANCH`, `BUILD_TIME`
- Always on, no opt-out flag

**`AppRouteObserver`** (`lib/core/logging/app_route_observer.dart`):
- `NavigatorObserver` calling `AppLogger.log()` at level `NAV`

### New Unified API

```dart
class Logger {
  // Category methods (replace DebugLogger.sync, .pdf, etc.)
  static void sync(String msg, {Map<String, dynamic>? data});
  static void pdf(String msg, {Map<String, dynamic>? data});
  static void db(String msg, {Map<String, dynamic>? data});
  static void auth(String msg, {Map<String, dynamic>? data});
  static void ocr(String msg, {Map<String, dynamic>? data});
  static void nav(String msg, {Map<String, dynamic>? data});
  static void ui(String msg, {Map<String, dynamic>? data});

  // Error with optional category (defaults to 'app' for deprecation compat)
  static void error(String msg, {Object? error, StackTrace? stack,
    String category = 'app', Map<String, dynamic>? data});

  // Debug session only — compiles out of production
  static void hypothesis(String id, String category, String msg,
    {Map<String, dynamic>? data});

  // Lifecycle
  static Future<void> init();
  static Future<void> close();

  // Structured artifact export (named params for backward compat)
  static Future<String?> writeReport({required String prefix, required Map<String, dynamic> data});
}
```

### Migration Map

| Current | New | Notes |
|---------|-----|-------|
| `DebugLogger.sync(msg)` | `Logger.sync(msg)` | Drop `Debug` prefix |
| `DebugLogger.sync(msg, data: {...})` | `Logger.sync(msg, data: {...})` | Preserved |
| `DebugLogger.error(msg, error: e, stack: s)` | `Logger.error(msg, error: e, stack: s)` | Category defaults to `'app'` |
| `AppLogger.log(msg, level: 'INFO')` | `Logger.ui(msg)` or appropriate category | No more generic — pick a category |
| `AppLogger.log(msg, level: 'NAV')` | `Logger.nav(msg)` | Direct mapping |
| `AppLogger.log(msg, level: 'ERROR')` | `Logger.error(msg)` | Category defaults to `'app'` |
| `AppLogger.writeJsonReport(prefix: p, data: d)` | `Logger.writeReport(prefix: p, data: d)` | Named params preserved |
| `debugPrint('[BACKGROUND_SYNC] ...')` | `Logger.sync('...')` | Bare debugPrints migrated |
| `AppRouteObserver` → `AppLogger` | `AppRouteObserver` → `Logger.nav()` | Observer stays |
| `AppLifecycleLogger` → `AppLogger` | `AppLifecycleLogger` → `Logger.ui()` | Same |

### What Stays

- Categorized file output (`sync.log`, `pdf_import.log`, etc.)
- Session directory structure (`session_YYYY-MM-DD_HH-MM-SS/`)
- Build metadata in session header
- `debugPrint` hook capturing all `debugPrint` output
- Global error handlers
- Always-on in all builds

### What Changes

- Single import everywhere: `import '.../core/logging/logger.dart'`
- Two loggers → one class with two transports
- `hypothesis()` method is new — HTTP transport only
- Log entries gain consistent JSON structure across both transports
- HTTP transport scrubs sensitive data and truncates large payloads
- `error()` defaults category to `'app'` for backward compat with `DebugLogger.error()`
- `writeReport()` keeps named parameters for backward compat with `AppLogger.writeJsonReport()`

### File Transport Output Format

Human-readable for field users:
```
[2026-03-14T10:23:45.001Z][SYNC] adapter push completed | {"adapter":"ProjectAdapter","rowCount":3}
[2026-03-14T10:23:45.142Z][SYNC][ERROR] push failed | {"adapter":"EntryAdapter","error":"FK violation"}
  Stack: #0 EntryAdapter.push (sync_adapter.dart:47)
         #1 SyncEngine.pushChanges (sync_engine.dart:251)
```

### Migration Path

1. Build `Logger` class with file transport matching current `DebugLogger` output
2. Add HTTP transport behind `DEBUG_SERVER` flag with sensitive data filter
3. Alias old APIs — `DebugLogger.sync()` forwards to `Logger.sync()` (deprecation, not breakage)
4. Migrate call sites by priority:
   - **P1 (providers):** 29 of 30 providers use bare `debugPrint` (~380 calls across ~50 files). Migrate highest-traffic providers first: `SyncProvider`, `AuthProvider`, `DailyEntryProvider`, `ProjectProvider`
   - **P2 (background sync):** `BackgroundSyncHandler` from bare `debugPrint` to `Logger.sync()`
   - **P3 (navigation):** `AppRouteObserver` from `AppLogger` to `Logger.nav()`
   - **P4 (remaining):** All other call sites, feature by feature
5. Remove old `AppLogger` and `DebugLogger` classes after full migration
6. Fill coverage gaps naturally during debug sessions

### Current Logging Coverage Gaps

| Layer | Coverage | Gap |
|-------|----------|-----|
| Sync engine | **Excellent** — every lock, circuit breaker, adapter push/pull, cursor, integrity check logged via `DebugLogger.sync()` | None |
| PDF pipeline | **Good** — `ExtractionPipeline` logs every stage boundary; `GridLineRemover` and `PostProcessorV2` log warnings/repairs | Individual stages (2B-i through 4E.5) have no internal logging |
| Database (GenericLocalDatasource) | **Good** — every INSERT, UPDATE, SOFT_DELETE, RESTORE, HARD_DELETE, PURGE logged via `DebugLogger.db()` | None |
| Auth | **Minimal** — `DebugLogger.auth()` used in `main.dart` for session events only | `AuthService` and `AuthProvider` use bare `debugPrint` |
| Providers | **Poor** — 29 of 30 providers use bare `debugPrint` only | Only `BidItemProvider` uses `DebugLogger` directly |
| Navigation | **Good** — `AppRouteObserver` captures all push/pop/replace/remove | Uses `AppLogger` not `DebugLogger` (goes to flat file, not `navigation.log`) |
| Background sync | **Poor** — `BackgroundSyncHandler` uses bare `debugPrint('[BACKGROUND_SYNC] ...')` | Not routed to `sync.log` |
| OCR | **Minimal** — `DebugLogger.ocr()` exists but usage is sparse | `TesseractEngineV2` logging unclear |

---

## 4. HTTP Log Server Design

### Location

```
tools/debug-server/
  server.js          # ~180 lines, zero dependencies
  README.md          # Setup instructions
```

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/log` | Receive a structured log entry |
| `POST` | `/clear` | Wipe all collected logs for fresh reproduction |
| `GET` | `/logs` | Return all collected logs (NDJSON — one entry per line) |
| `GET` | `/logs?hypothesis=A` | Filter by hypothesis ID |
| `GET` | `/logs?category=sync` | Filter by category |
| `GET` | `/logs?since=<ISO8601>` | Filter by time window |
| `GET` | `/logs?level=error` | Filter by level |
| `GET` | `/logs?last=50` | Most recent N entries |
| `GET` | `/logs?deviceId=<id>` | Filter by device |
| `GET` | `/health` | `{"status":"ok","entries":142,"memoryMB":12,"uptime":3600}` |
| `GET` | `/categories` | `{"sync":47,"pdf":12,"db":83}` |

Filters are combinable: `/logs?category=sync&hypothesis=A&since=2026-03-14T10:00:00Z`

`/logs` returns **NDJSON** (one JSON object per line) instead of a JSON array. For 30k entries, a JSON array could be 10MB+. NDJSON streams better and Claude can process it line by line.

### Storage

- In-memory array, **max 30,000 entries AND max 100MB total memory**
- Oldest dropped when either limit hit
- Session-lived — start when debugging, kill when done
- `POST /clear` between reproductions
- **SIGINT/SIGTERM handler**: on shutdown, dumps current logs to `tools/debug-server/last-session.ndjson` before exiting (~5 lines of code, prevents total log loss on accidental Ctrl-C)

### CLI Arguments

```bash
node tools/debug-server/server.js              # default port 3947
node tools/debug-server/server.js --port 4000  # custom port
```

### Server-Side Entry Enrichment

Each received entry gets:
- `id` — auto-incrementing integer for ordering
- `receivedAt` — server-side ISO8601 timestamp

### Server Startup Banner

```
[debug-server] Listening on 127.0.0.1:3947
[debug-server] Logs may contain sensitive data — do not expose this port
[debug-server] Use POST /clear between reproductions
[debug-server] Ctrl-C dumps logs to last-session.ndjson before exit
```

### How Claude Interacts

```bash
# Health check
curl -s http://127.0.0.1:3947/health

# Clear before reproduction
curl -s -X POST http://127.0.0.1:3947/clear

# Read all logs after reproduction
curl -s http://127.0.0.1:3947/logs

# Filter to hypothesis A
curl -s "http://127.0.0.1:3947/logs?hypothesis=A"

# Category counts
curl -s http://127.0.0.1:3947/categories

# Check ADB connection is alive (before reading)
curl -s --max-time 2 http://127.0.0.1:3947/health || echo "Server unreachable — check ADB"
```

### Error Handling

| Scenario | Behavior |
|----------|----------|
| Server not running | App's HTTP transport silently drops logs (fire-and-forget). File transport unaffected. |
| Server full (30k entries or 100MB) | Oldest entries dropped. Warning in server console. |
| Malformed POST body | 400 response, logged. App continues. |
| App sends faster than server | HTTP transport uses fire-and-forget async — never blocks app's main thread. |
| Ctrl-C / SIGINT | Dumps logs to `last-session.ndjson`, then exits. |
| ADB disconnect mid-session | HTTP transport silently drops logs. Debug skill checks `/health` before reading. |

### Session Setup

**Windows Desktop:**
```bash
# Terminal 1: Start server
node tools/debug-server/server.js

# Terminal 2: Run app with HTTP transport enabled
pwsh -Command "flutter run -d windows --dart-define=DEBUG_SERVER=true --dart-define-from-file=.env"
```

**Android Device (USB):**
```bash
# Terminal 1: Start server
node tools/debug-server/server.js

# Terminal 2: Port forward
adb reverse tcp:3947 tcp:3947

# Terminal 3: Run app with HTTP transport enabled
pwsh -Command "flutter run --dart-define=DEBUG_SERVER=true --dart-define-from-file=.env"
```

Note: `tools/build.ps1` is for release builds and will **reject** `DEBUG_SERVER=true`. For debug sessions, use `flutter run` directly with `--dart-define`.

---

## 5. Debug Skill Workflow

### Entry Point

User invokes `/debug`. Claude asks:

```
Is this a quick bug or a deep debug session?

A) Quick — I'll handle it solo using logs and investigation
B) Deep — Launch an Opus research agent to trace code in parallel
```

### Solo Mode Phases

```
Phase 1: TRIAGE
  Scan codebase for orphaned #region debug-hypothesis markers
    from a crashed previous session
  If found → present to user: clean up first or adopt
  Check if DEBUG_SERVER is running (curl /health)
  If not → guide user to start server + app
  If yes → POST /clear to reset logs

Phase 2: COVERAGE CHECK
  Identify likely code path for the bug
  Read relevant source files
  Assess Logger coverage on the path
  ├─ Good coverage → skip to Phase 4
  └─ Gaps found → Phase 3

Phase 3: INSTRUMENT GAPS
  Add Logger.hypothesis() calls with region markers:
    // #region debug-hypothesis-A: description
    Logger.hypothesis('A', 'sync', 'msg', data: {...});
    // #endregion debug-hypothesis-A

  Add permanent Logger calls for structural gaps:
    Logger.sync('adapter push completed', data: {...});

  NEVER log session objects, user profiles, or auth responses
    in hypothesis instrumentation (see auth logging restrictions)

  Present instrumentation plan → USER GATE
  Apply after approval

Phase 4: REPRODUCE
  Tell user exactly what to reproduce
  Ask narrowing questions:
    - Every time or intermittent?
    - One device or all?
    - When did it stop working?
    - What were you doing right before?
    - Pattern: after sync? specific action? app open a while?
  User reproduces, says "done"

  Before reading logs: check /health to verify server reachable
  If health check fails → guide user to verify ADB connection
    and re-run adb reverse tcp:3947 tcp:3947

Phase 5: EVIDENCE ANALYSIS
  Read logs: curl /logs, filter by hypothesis/category/time/device
  Analyze: variable values, execution order, timing gaps,
  missing expected entries

Phase 6: ROOT CAUSE REPORT
  Present findings with log entries as proof:
    - Root cause (with evidence)
    - Which hypotheses confirmed/rejected
    - Proposed fix approach
    - Files to change
  → USER GATE

Phase 7: FIX
  Implement targeted fix
  POST /clear → user reproduces → read logs to confirm

Phase 8: INSTRUMENTATION REVIEW
  For each hypothesis region:
    KEEP (with justification) or REMOVE (with reason)
  For each permanent addition:
    KEEP (with justification) or REMOVE
  User decides per-item

Phase 9: CLEANUP (HARD GATE)
  - [ ] All hypothesis regions removed from source
  - [ ] Global search confirms zero #region debug-hypothesis markers
  - [ ] Global search confirms zero #endregion debug-hypothesis markers
  - [ ] Session log written to .claude/debug-sessions/ (scrubbed)
  - [ ] User confirms cleanup is complete
  Session CANNOT end without all 5 checks passing.

Phase 10: DEFECT LOG
  If new pattern discovered → write to
  .claude/defects/_defects-{feature}.md
```

### Deep Debug Mode

Everything above, plus an Opus research agent launched in the background at Phase 1. The agent works while Claude handles triage, instrumentation, and user interaction.

```
TRULY PARALLEL (run_in_background: true):

Main Agent (Claude)              Research Agent (Opus, background)
─────────────────────            ──────────────────────
Phase 1: Triage                  Receives bug description
  Scan orphaned markers          Starts tracing code path
  Check server health
Phase 2: Coverage check          Reads files, git blame/history
Phase 3: Instrument gaps         Checks defect files + past sessions
Phase 4: Guide reproduction      Verifies contracts at boundaries
  Ask narrowing questions        Forms 3 ranked hypotheses
  User reproducing...            Identifies logging gaps
Phase 5: Read logs
  Check if agent is done →       ← Agent results ready
  Read agent output
CORRELATE:
  Agent code hypotheses
  + runtime log evidence
  = root cause
Phases 6-10 same as solo
```

Claude checks the agent's output after reading logs (Phase 5). If the agent is still working, Claude proceeds with log analysis and checks again before presenting the root cause report.

### Research Agent Spec

| Field | Value |
|-------|-------|
| Name | `debug-research-agent` |
| Model | `claude-opus-4-6` |
| Type | `general-purpose` |
| Tools | `Read, Grep, Glob, Bash(git log, git blame, git diff)` |
| Disallowed | `Edit, Write, Task` — read-only |
| Launch | `Task` tool, **`run_in_background: true`** |

**Agent tasks:**
1. Trace data flow through app layers for the suspect code path
2. `git log` / `git blame` on suspect files for recent changes
3. Check `.claude/defects/_defects-{feature}.md` for known patterns
4. Check `.claude/debug-sessions/` for past sessions on same area
5. Verify contracts at layer boundaries (caller/callee type alignment)
6. Form up to 3 ranked hypotheses with file:line evidence
7. Identify logging gaps in the code path

**Agent does NOT:** modify files, instrument code, interact with user, read logs from server, spawn sub-agents.

### Stop Conditions

- **3+ failed fix attempts** — escalate to deep mode (if solo) or reassess
- **Fix requires 5+ files** — present scope to user before proceeding
- **Can't explain root cause** — go back to instrumentation, add more logging
- **Fix suppresses symptoms** — log evidence should disprove; if upstream data still wrong, keep investigating

---

## 6. Region Markers & Instrumentation Lifecycle

### Hypothesis Instrumentation

```dart
// #region debug-hypothesis-A: checking if item is null at repository entry
Logger.hypothesis('A', 'sync', 'item state at repository entry',
  data: {'itemId': item?.id, 'isNull': item == null});
// #endregion debug-hypothesis-A
```

Rules:
- Marker includes hypothesis ID + human-readable description
- One hypothesis per region
- Max 5 active hypotheses per session (A-E)
- `Logger.hypothesis()` only writes to HTTP transport
- **NEVER log auth session objects, user profile maps, or Supabase auth responses** in hypothesis instrumentation

### Permanent Instrumentation (Gap-Filling)

```dart
// Fills sync adapter coverage gap — added 2026-03-14
Logger.sync('adapter push completed',
  data: {'adapter': adapter.tableName, 'rowCount': count, 'duration_ms': elapsed});
```

### Auth Logging Restrictions

The following MUST NEVER appear in `data` maps for any log call (hypothesis or permanent):
- Supabase session objects (contain `access_token`, `refresh_token`)
- User profile maps (contain `email`, `phone`, `cert_number`, `inspector_name`)
- Request/response bodies from Supabase auth endpoints
- `.env` values or API keys

Log **identifiers** (user ID, company ID) and **state** (role, status, isAuthenticated) instead of full objects.

### Retention Review (Phase 8)

**Hypothesis instrumentation (default: remove):**
```
REMOVE — Hypothesis A region in sync_engine.dart:247
  Purpose: Tested whether item was null at repository entry
  Verdict: Confirmed — root cause, now fixed
  Reason: Null case no longer occurs. Permanent logging covers path.
```

**Gap-filling instrumentation (default: keep, must justify):**
```
KEEP — Logger.sync() in project_adapter.dart:89
  Purpose: Logs adapter push result with row count and duration
  Reason: ProjectAdapter had zero push-path logging. Catches
  timeout issues, partial pushes, performance degradation.
```

User approves/overrides each item.

### Cleanup Verification (Phase 9 — HARD GATE)

1. Remove all `#region debug-hypothesis-*` / `#endregion debug-hypothesis-*` blocks
2. Search entire codebase: `Grep "#region debug-hypothesis"` → must return 0 matches
3. Search entire codebase: `Grep "#endregion debug-hypothesis"` → must return 0 matches
4. Write session log to `.claude/debug-sessions/YYYY-MM-DD-<topic>/session-log.md` (**scrubbed of sensitive data**)
5. Prune session logs older than 30 days
6. User confirms cleanup is complete

**Session cannot end without all checks passing.**

### Session Log Format

```
.claude/debug-sessions/
  YYYY-MM-DD-<topic>/
    session-log.md
```

Contents (all log data scrubbed of sensitive keys before writing):
- Bug description
- Root cause found (with evidence)
- All hypotheses tested: confirmed/rejected with log data
- Every instrumentation addition: file, line, what it logged
- Disposition: KEPT (with justification) or REMOVED
- Cleanup verification: "Searched codebase — 0 debug-hypothesis markers found"
- Files modified (final list)

**Retention:** Sessions older than 30 days are pruned during Phase 9 cleanup. `.claude/debug-sessions/` is added to the config repo's `.gitignore` to prevent accidental commits of potentially sensitive data.

---

## 7. Codebase Architecture Reference (Audited 2026-03-14)

This section documents the current accurate architecture for use in the skill and reference files.

### Data Flow Pattern

```
Screen → Provider → Repository → Datasource → SQLite
                                                  ↕ (sync time only)
                                            SyncEngine → Supabase
```

Repositories only wire local datasources. Remote datasource files exist but are used exclusively through sync adapters, not the normal write path.

### Provider Layer (30 providers)

| Provider | File | Base Class | Uses DebugLogger? |
|----------|------|-----------|-------------------|
| `AuthProvider` | `lib/features/auth/presentation/providers/auth_provider.dart` | `ChangeNotifier` | No (bare debugPrint) |
| `AppConfigProvider` | `lib/features/auth/presentation/providers/app_config_provider.dart` | `ChangeNotifier` | No |
| `CalculatorProvider` | `lib/features/calculator/presentation/providers/calculator_provider.dart` | `ChangeNotifier` | No |
| `ContractorProvider` | `lib/features/contractors/presentation/providers/contractor_provider.dart` | `BaseListProvider` | No |
| `EquipmentProvider` | `lib/features/contractors/presentation/providers/equipment_provider.dart` | `BaseListProvider` | No |
| `PersonnelTypeProvider` | `lib/features/contractors/presentation/providers/personnel_type_provider.dart` | `BaseListProvider` | No |
| `DailyEntryProvider` | `lib/features/entries/presentation/providers/daily_entry_provider.dart` | `BaseListProvider` | No |
| `InspectorFormProvider` | `lib/features/forms/presentation/providers/inspector_form_provider.dart` | `BaseListProvider` | No |
| `GalleryProvider` | `lib/features/gallery/presentation/providers/gallery_provider.dart` | `ChangeNotifier` | No |
| `LocationProvider` | `lib/features/locations/presentation/providers/location_provider.dart` | `BaseListProvider` | No |
| `PhotoProvider` | `lib/features/photos/presentation/providers/photo_provider.dart` | `BaseListProvider` | No |
| `ProjectProvider` | `lib/features/projects/presentation/providers/project_provider.dart` | `ChangeNotifier` | No |
| `ProjectSettingsProvider` | `lib/features/projects/presentation/providers/project_settings_provider.dart` | `ChangeNotifier` | No |
| `BidItemProvider` | `lib/features/quantities/presentation/providers/bid_item_provider.dart` | `BaseListProvider` | **Yes** |
| `EntryQuantityProvider` | `lib/features/quantities/presentation/providers/entry_quantity_provider.dart` | `BaseListProvider` | No |
| `AdminProvider` | `lib/features/settings/presentation/providers/admin_provider.dart` | `ChangeNotifier` | No |
| `ThemeProvider` | `lib/features/settings/presentation/providers/theme_provider.dart` | `ChangeNotifier` | No |
| `SyncProvider` | `lib/features/sync/presentation/providers/sync_provider.dart` | `ChangeNotifier` | No |
| `TodoProvider` | `lib/features/todos/presentation/providers/todo_provider.dart` | `BaseListProvider` | No |

Note: bare `debugPrint` calls ARE captured by `AppLogger`'s hook → written to flat session file at level `DEBUG`. But they are NOT routed to categorized `DebugLogger` files.

### Sync Engine Components

| Component | Class | File | Key Methods |
|-----------|-------|------|-------------|
| Engine | `SyncEngine` | `lib/features/sync/engine/sync_engine.dart` | `pushAndPull()`, `pushOnly()`, `pullOnly()`, `resetState()` |
| Orchestrator | `SyncOrchestrator` | `lib/features/sync/application/sync_orchestrator.dart` | `initialize()`, `syncLocalAgencyProjects()`, `getPendingBuckets()`, `checkDnsReachability()` |
| Change Tracker | `ChangeTracker` | `lib/features/sync/engine/change_tracker.dart` | `getUnprocessedChanges()`, `markProcessed()`, `markFailed()`, `isCircuitBreakerTripped()` |
| Conflict Resolver | `ConflictResolver` | `lib/features/sync/engine/conflict_resolver.dart` | `resolve()` — LWW on `updated_at` |
| Integrity Checker | `IntegrityChecker` | `lib/features/sync/engine/integrity_checker.dart` | `shouldRun()`, `run()` — compares local vs remote counts/timestamps |
| Mutex | `SyncMutex` | `lib/features/sync/engine/sync_mutex.dart` | `tryAcquire()`, `heartbeat()`, `release()`, `forceReset()` |
| Registry | `SyncRegistry` | `lib/features/sync/engine/sync_registry.dart` | `registerAdapters()`, `adapterFor()`, `dependencyOrder` |
| Orphan Scanner | `OrphanScanner` | `lib/features/sync/engine/orphan_scanner.dart` | `scan()` — finds storage files with no DB row |
| Storage Cleanup | `StorageCleanup` | `lib/features/sync/engine/storage_cleanup.dart` | `cleanupExpiredPhotos()` — deferred photo deletion |
| Background Handler | `BackgroundSyncHandler` | `lib/features/sync/application/background_sync_handler.dart` | `initialize()`, `cancelAll()` — WorkManager periodic |
| Lifecycle Manager | `SyncLifecycleManager` | `lib/features/sync/application/sync_lifecycle_manager.dart` | `WidgetsBindingObserver` — staleness/resume handling |
| Config | `SyncEngineConfig` | `lib/features/sync/config/sync_config.dart` | All constants (pushBatchLimit=500, pullPageSize=100, etc.) |

### 16 Sync Adapters (FK Dependency Order)

| # | Class | Table | Scope | FK Dependencies |
|---|-------|-------|-------|----------------|
| 1 | `ProjectAdapter` | `projects` | `direct` | — |
| 2 | `LocationAdapter` | `locations` | `viaProject` | projects |
| 3 | `ContractorAdapter` | `contractors` | `viaProject` | projects |
| 4 | `EquipmentAdapter` | `equipment` | `viaContractor` | contractors |
| 5 | `BidItemAdapter` | `bid_items` | `viaProject` | projects |
| 6 | `PersonnelTypeAdapter` | `personnel_types` | `viaProject` | projects, contractors |
| 7 | `DailyEntryAdapter` | `daily_entries` | `viaProject` | projects, locations |
| 8 | `PhotoAdapter` | `photos` | `viaEntry` | daily_entries, projects |
| 9 | `EntryEquipmentAdapter` | `entry_equipment` | `viaEntry` | daily_entries, equipment |
| 10 | `EntryQuantitiesAdapter` | `entry_quantities` | `viaEntry` | daily_entries, bid_items |
| 11 | `EntryContractorsAdapter` | `entry_contractors` | `viaEntry` | daily_entries, contractors |
| 12 | `EntryPersonnelCountsAdapter` | `entry_personnel_counts` | `viaEntry` | daily_entries, contractors, personnel_types |
| 13 | `InspectorFormAdapter` | `inspector_forms` | `viaProject` | projects |
| 14 | `FormResponseAdapter` | `form_responses` | `viaProject` | projects |
| 15 | `TodoItemAdapter` | `todo_items` | `viaProject` | projects |
| 16 | `CalculationHistoryAdapter` | `calculation_history` | `viaProject` | projects |

All adapters in `lib/features/sync/adapters/`. Base class: `TableAdapter` (`table_adapter.dart`).

### PDF Pipeline Stages

All in `lib/features/pdf/services/extraction/stages/`:

| Stage | Class | What It Does |
|-------|-------|-------------|
| 0 | `DocumentQualityProfiler` | PDF quality analysis, extraction strategy |
| 2B-i | `PageRendererV2` | PDF → raster images via pdfrx |
| 2B-ii | `ImagePreprocessorV2` | Grayscale + contrast enhancement |
| 2B-ii.5 | `GridLineDetector` | Detect table grid lines |
| 2B-ii.6 | `GridLineRemover` | Remove grid lines via OpenCV inpainting |
| 2B-iii | `TextRecognizerV2` | Tesseract OCR → `OcrElement` objects |
| 3 | `ElementValidator` | Validate + coordinate-normalize OCR elements |
| Pre-4B | `RowClassifierV3` + `HeaderConsolidator` | Provisional row classification |
| 4B | `RegionDetectorV2` + `SyntheticRegionBuilder` | Table region detection |
| 4C | `ColumnDetectorV2` | Semantic column boundaries |
| 4A | `RowClassifierV3` (final) | Final classification with column map |
| 4A post | `HeaderConsolidator` | Multi-line header consolidation |
| 4A.5 | `RowMerger` | Continuation row merging |
| 4D | `CellExtractorV2` | Cell value extraction → `CellGrid` |
| 4D.5 | `NumericInterpreter` | Raw text → typed numeric values |
| 4E | `RowParserV3` | Grid rows → `ParsedItems` |
| 4E.5 | `FieldConfidenceScorer` | Per-field confidence scoring |
| 5 | `PostProcessorV2` | Deduplication, value normalization |
| 6 | `QualityValidator` | Overall quality score, status determination |

Orchestrator: `ExtractionPipeline` (`lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`) — runs re-extraction loop (max 3 attempts), selects best by `overallScore`.

OCR: `TesseractEngineV2` (`lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart`)

### Auth Flow

| Component | Class | File |
|-----------|-------|------|
| Service | `AuthService` | `lib/features/auth/services/auth_service.dart` |
| Provider | `AuthProvider` | `lib/features/auth/presentation/providers/auth_provider.dart` |
| Config provider | `AppConfigProvider` | `lib/features/auth/presentation/providers/app_config_provider.dart` |
| Password validator | `PasswordValidator` | `lib/features/auth/services/password_validator.dart` |
| Mock config | `TestModeConfig` | `lib/core/config/test_mode_config.dart` |

Auth state: `StreamSubscription<AuthState>` on Supabase auth changes. Mock path: `MOCK_AUTH=true` compile-time flag, asserts `!kReleaseMode`.

### Database

- **Schema version:** 34
- **Migration thresholds:** 2-9, 13-14, 17-34 (28 steps)
- **Key tables:** projects, locations, contractors, equipment, bid_items, personnel_types, daily_entries, photos, entry_equipment, entry_quantities, entry_contractors, entry_personnel_counts, inspector_forms, form_responses, todo_items, calculation_history, companies, user_profiles, sync_metadata, sync_control, change_log, conflict_log, sync_lock, synced_projects, storage_cleanup_queue, deletion_notifications, extraction_metrics, stage_metrics
- **Service:** `DatabaseService` (`lib/core/database/database_service.dart`)
- **WAL mode** enabled on all production databases
- **`SchemaVerifier.verify(db)`** runs on every open for self-healing

### Compile-Time Flags

All in `TestModeConfig` (`lib/core/config/test_mode_config.dart`):

| Flag | Default | Purpose |
|------|---------|---------|
| `PATROL_TEST` | false | Disables background timers for testing |
| `MOCK_AUTH` | false | Bypasses Supabase auth |
| `AUTO_LOGIN` | false | Auto-login with mock credentials |
| `MOCK_WEATHER` | false | Deterministic weather data |
| `MOCK_DATA` | false | SQLite-only, no Supabase sync |
| `APP_FILE_LOGGING` | true | Enable/disable `AppLogger` file output |
| `BUILD_SHA` / `BUILD_BRANCH` / `BUILD_TIME` | "unknown" | Build metadata in logs |
| `DEBUG_SERVER` | false | **NEW** — Enable HTTP log transport |

---

## 8. Reference Files (4 files)

### File 1: `log-investigation-and-instrumentation.md`

**Combines** log-first investigation + instrumentation patterns (formerly files 1 and 3):

**Reading logs from the server:**
- Filtering strategies (hypothesis, category, time window, level, last N, deviceId)
- What to look for: missing expected entries, unexpected values, timing gaps, ordering anomalies
- Platform-specific access (Windows curl direct, Android ADB USB)
- Correlating log timestamps with user actions
- Reading structured `data` fields vs. message text
- ADB reconnection: check `/health` before reading; re-run `adb reverse` if unreachable

**Assessing and building coverage:**
- How to assess logging coverage on a code path
- Where to instrument: layer boundaries, decision points, error paths, before/after async calls
- Hypothesis tagging conventions (A-E, region markers, descriptions)
- Permanent vs hypothesis instrumentation — when to use each
- Category selection guide:
  - `Logger.sync()` — sync engine, adapters, change tracker, mutex
  - `Logger.pdf()` — pipeline stages, OCR, extraction
  - `Logger.db()` — SQLite operations, migrations, schema
  - `Logger.auth()` — auth service, session, tokens (**NEVER log session objects or user profiles**)
  - `Logger.ocr()` — Tesseract operations, per-cell extraction
  - `Logger.nav()` — route changes, navigation events
  - `Logger.ui()` — UI events, lifecycle, provider state changes
- Retention review process with justification templates
- Cleanup verification checklist

### File 2: `codebase-tracing-paths.md`

Flutter-specific tracing paths audited against current codebase. For each path:
- Layer chain with exact class names and file paths
- Which `Logger.*` categories to filter on
- Common failure points

Paths documented:
- **Widget not updating** → Provider (`ChangeNotifier`) → `notifyListeners()` → object identity
- **Sync failure** → `SyncOrchestrator.syncLocalAgencyProjects()` → `SyncEngine.pushAndPull()` → adapter → Supabase
- **Sync adapter push skip** → `ChangeTracker.hasFailedEntries()` → FK dependency check → registration order in `SyncRegistry`
- **PDF pipeline failure** → `ExtractionPipeline` → Stage 0 through 6 → re-extraction loop
- **Auth flow failure** → `AuthService` → `AuthProvider` → session state
- **Navigation not working** → `AppRouteObserver` → GoRouter → async context
- **FK constraint violation** → adapter dependency order → soft-delete vs hard-delete
- **Change tracker drift** → SQLite triggers → `sync_control.pulling` flag → trigger suppression
- **Provider state stale after sync** → `SyncProvider` → feature provider → `loadItems()` on sync completion
- **Background sync failure** → `BackgroundSyncHandler` → `SyncEngine.createForBackgroundSync()` → isolate context

### File 3: `defects-integration.md`

Audited and updated:
- Check `.claude/defects/_defects-{feature}.md` before debugging
- Check `.claude/debug-sessions/` for past sessions on same area
- 8 pattern categories: `[ASYNC]`, `[E2E]`, `[FLUTTER]`, `[DATA]`, `[CONFIG]`, `[SYNC]`, `[MIGRATION]`, `[SCHEMA]`
- 15 feature defect files (paths verified)
- Document new patterns during debugging
- Standard format with pattern, prevention, reference

### File 4: `debug-session-management.md`

- Server setup instructions per platform (Windows, Android USB only)
- Session lifecycle: start server → connect app → debug → cleanup → write session log
- Orphaned marker recovery on session start
- Session log format, location (`.claude/debug-sessions/`), and scrubbing rules
- 30-day retention policy for session logs
- Cleanup hard gate checklist (5 mandatory checks)
- Deep debug mode: when to use, research agent prompt (run_in_background: true), how to check agent output, how to correlate code hypotheses with log evidence
- Stop conditions (3+ attempts, 5+ files, can't explain, symptom suppression)
- User interview question bank for narrowing investigation
- Escalation rules: solo → deep mode
- ADB reconnection guidance

---

## 9. Build Script Integration

### Release Build Guard

`tools/build.ps1` must reject `DEBUG_SERVER=true` for release builds:

```powershell
# In tools/build.ps1, before flutter build:
if ($BuildType -ne "debug") {
    $envContent = Get-Content $dartDefineFile -ErrorAction SilentlyContinue
    if ($envContent -match "DEBUG_SERVER") {
        Write-Error "SECURITY: DEBUG_SERVER must not be set in .env for release builds"
        exit 1
    }
}
```

### Debug Session Invocation

For debug sessions, use `flutter run` directly (not `tools/build.ps1`):

```bash
# Windows
pwsh -Command "flutter run -d windows --dart-define=DEBUG_SERVER=true --dart-define-from-file=.env"

# Android (after adb reverse tcp:3947 tcp:3947)
pwsh -Command "flutter run --dart-define=DEBUG_SERVER=true --dart-define-from-file=.env"
```

This ensures `--dart-define-from-file=.env` still provides Supabase credentials while `--dart-define=DEBUG_SERVER=true` enables the HTTP transport.

---

## 10. Config Repo `.gitignore` Addition

Add to the `field-guide-claude-config` repository's `.gitignore`:

```
debug-sessions/
```

This prevents session logs (which may reference sensitive data even after scrubbing) from being committed.

---

## 11. Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Log-first vs code-first | Log-first | Runtime evidence is stronger than code-reading guesses; builds coverage over time |
| HTTP server vs file-only | HTTP server | Clearable between reproductions, structured JSON, cross-platform, filterable by Claude |
| Server technology | Node.js, zero deps | Simple, fast, no npm install needed, Claude can read/write it easily |
| Max entries | 30,000 + 100MB memory cap | Generous count buffer with memory safety net |
| Per-entry data cap | 4KB serialized | Prevents memory exhaustion from large data maps (PDF pipeline, full row maps) |
| Hypothesis limit | 5 (A-E) | Enough for parallel testing, not so many it's unmanageable |
| Instrumentation retention | Justify to keep | Prevents dead logging; fills real gaps when justified |
| Cleanup enforcement | Hard gate | Zero stray debug markers; session log preserves evidence |
| Deep debug agent | Opus, read-only, background | Code tracing needs reasoning power; background enables true parallelism |
| Unified logger migration | Incremental with aliases | No big-bang; old API forwards to new, migrate feature by feature |
| `DEBUG_SERVER` gating | Compile-time + runtime assert + build script guard | Three layers of defense against accidental production enablement |
| Sensitive data filter | Blocklist scrub on HTTP transport only | File transport is local (same data already on device); HTTP adds network exposure |
| WiFi debugging | **Removed** | Plaintext HTTP on shared networks is unacceptable; ADB USB is sufficient |
| Session logs | Scrubbed, gitignored, 30-day retention | Balance institutional memory with data hygiene |
| `error()` default category | `'app'` | Backward compat with `DebugLogger.error()` which has no category |
| `writeReport()` signature | Named params | Backward compat with `AppLogger.writeJsonReport(prefix:, data:)` |
| `/logs` response format | NDJSON | Streams better than JSON array for 30k entries; Claude processes line by line |
| Reference files | 4 (combined investigation + instrumentation) | Reduces context overhead; investigation and instrumentation are one workflow |
| `source` field | Not in schema — optional via `data` map | Dart lacks zero-cost source location; `StackTrace.current` too expensive |

---

## 12. Implementation Phases

### Phase 1: HTTP Log Server
- Create `tools/debug-server/server.js` (~180 lines)
- All endpoints: `/log`, `/clear`, `/logs` (NDJSON, with filters + deviceId), `/health` (with memoryMB), `/categories`
- In-memory storage: 30k entry cap + 100MB memory cap
- SIGINT handler dumps to `last-session.ndjson`
- `--port` CLI argument (default 3947)
- Bind to `127.0.0.1` only
- Startup security banner
- Create `tools/debug-server/README.md`

### Phase 2: Unified Logger
- Create `lib/core/logging/logger.dart`
- File transport matching current `DebugLogger` output format
- HTTP transport behind `DEBUG_SERVER` flag with:
  - `assert(!kReleaseMode)` guard
  - Sensitive data blocklist filter (`_scrub()`)
  - 4KB per-entry data truncation
  - `deviceId` field from `Platform.localHostname`
  - Fire-and-forget async (never blocks main thread)
- `hypothesis()` method (HTTP-only)
- `error()` with `category` defaulting to `'app'`
- `writeReport()` with named parameters
- `debugPrint` hook, global error handlers, lifecycle observer
- Add `DEBUG_SERVER` to `TestModeConfig`

### Phase 3: Logger Migration
- Add deprecation forwarding: `DebugLogger.sync()` → `Logger.sync()`, etc.
- **P1:** Highest-traffic providers (`SyncProvider`, `AuthProvider`, `DailyEntryProvider`, `ProjectProvider`)
- **P2:** `BackgroundSyncHandler` from bare `debugPrint` to `Logger.sync()`
- **P3:** `AppRouteObserver` from `AppLogger` to `Logger.nav()`
- **P4:** Remaining providers and call sites, feature by feature
- Remove old `AppLogger` and `DebugLogger` classes after full migration

### Phase 4: Build Script Guard
- Add `DEBUG_SERVER` rejection to `tools/build.ps1` for non-debug builds

### Phase 5: Debug Skill
- Rewrite `SKILL.md` (~350 lines) with log-first workflow
- Create 4 reference files with audited content:
  1. `log-investigation-and-instrumentation.md`
  2. `codebase-tracing-paths.md`
  3. `defects-integration.md`
  4. `debug-session-management.md`
- Create `debug-research-agent` agent definition (`.claude/agents/`)
- Create `.claude/debug-sessions/` directory
- Add `debug-sessions/` to config repo `.gitignore`

### Phase 6: Validation
- Test server with manual curl commands (all endpoints, filters, SIGINT dump)
- Test HTTP transport from Windows desktop app
- Test ADB port forwarding with Android device (S21+ or S25 Ultra)
- Test sensitive data filter (verify tokens/PII are scrubbed)
- Test data truncation (large payload → `_truncated` response)
- Test build script guard (verify release build rejects `DEBUG_SERVER`)
- Run one real debug session end-to-end to validate the full workflow
