# Dependency Graph: Test Skill Redesign

## Direct Changes

### New Files (5)

| File | Type | Purpose |
|------|------|---------|
| `lib/main_driver.dart` | Dart | Custom entrypoint: IntegrationTestWidgetsFlutterBinding + HTTP driver + TestPhotoService |
| `lib/core/driver/driver_server.dart` | Dart | HTTP driver server on port 4948 (routes, auth, widget interaction) |
| `lib/core/driver/test_photo_service.dart` | Dart | TestPhotoService extends PhotoService — inject-photo mechanism |
| `tools/prune-test-results.ps1` | PowerShell | Test result retention (keep last 5 runs) |
| `.claude/test-flows/registry.md` | Markdown | Merged unified flow registry (replaces both existing registries) |

### Modified Files (4)

| File | Lines | Change |
|------|-------|--------|
| `tools/build.ps1` | 1-151 | Add `-DebugServer` switch, `-Target` parameter, MOCK_AUTH+DEBUG_SERVER block |
| `.gitignore` | varies | Broaden `.env.secret` → `*.secret` |
| `.claude/skills/test/SKILL.md` | 1-80 | Full rewrite to HTTP driver architecture |
| `.claude/agents/test-wave-agent.md` | 1-60 | Rewrite for HTTP driver, sonnet model, tier-based grouping |

## Key Symbol Dependencies

### main.dart Entrypoint Pattern (main_driver.dart must mirror)

```
main() → WidgetsFlutterBinding.ensureInitialized() → _runApp()
_runApp():
  - PreferencesService init
  - _initDebugLogging()
  - TestModeConfig.logStatus()
  - DatabaseService.initializeFfi() + database init
  - Tesseract OCR init
  - Supabase.initialize()
  - Firebase init (mobile only)
  - BackgroundSyncHandler.initialize()
  - All datasources + repositories
  - PhotoService(photoRepository)
  - SyncOrchestrator init + wiring
  - AuthProvider + ProjectSettingsProvider
  - App lifecycle (version, force reauth)
  - SyncLifecycleManager + lifecycle observer
  - AppRouter
  - runApp(ConstructionInspectorApp(...))
```

**main_driver.dart differences:**
1. `IntegrationTestWidgetsFlutterBinding.ensureInitialized()` instead of `WidgetsFlutterBinding`
2. Start `DriverServer` on port 4948 with random auth token
3. Log auth token to stdout + POST to debug server
4. Register `TestPhotoService` instead of `PhotoService`
5. Rest of `_runApp()` logic is identical — reuse via shared function or duplicate

### PhotoService (lib/services/photo_service.dart:12-385)

Key methods TestPhotoService needs to override:
- `capturePhoto()` → ImagePicker camera (override to return injected file)
- `pickFromGallery()` → ImagePicker gallery (override to return injected file)
- Constructor: `PhotoService(PhotoRepository repository)` — super call needed

**Existing pattern**: `StubPhotoService` (lib/test_harness/stub_services.dart:20-47) extends PhotoService and returns null for all capture/pick methods. TestPhotoService is different — it needs a completer/queue mechanism to inject files on demand.

### TestModeConfig (lib/core/config/test_mode_config.dart:21-138)

- `debugServerEnabled` = `bool.fromEnvironment('DEBUG_SERVER')` — already exists
- Used by `SyncEngine._postSyncStatus()` and `Logger._sendHttp()`
- No changes needed to TestModeConfig itself

### SyncEngine._postSyncStatus (lib/features/sync/engine/sync_engine.dart:315-341)

- POSTs to `http://127.0.0.1:3947/sync/status`
- Guarded by `_debugServerEnabled` + `kReleaseMode`
- Debug server stores in `latestSyncStatus` variable
- GET /sync/status returns latest status — agents poll this

### Debug Server (tools/debug-server/server.js)

Current routes (port 3947):
- POST /log, GET /logs (with since= filter), POST /clear
- GET /health, GET /categories
- POST /sync/status, GET /sync/status

**New route needed**: POST /driver/token (driver server posts its auth token here)

### ConstructionInspectorApp.build (lib/main.dart:705-924)

Provider tree includes `Provider<PhotoService>.value(value: photoService)`.
main_driver.dart must provide `TestPhotoService` here instead.

### build.ps1 (tools/build.ps1:1-151)

Current params: `-Platform` (mandatory), `-BuildType` (default: release), `-Clean`
Current guards: DEBUG_SERVER=true blocked in non-debug builds

**New additions:**
1. `-DebugServer` switch → appends `--dart-define=DEBUG_SERVER=true`
2. `-Target` string parameter → replaces default `lib/main.dart` entrypoint
3. MOCK_AUTH+DEBUG_SERVER mutual exclusion check

## Dependent Files (callers of changed symbols)

| File | Dependency |
|------|-----------|
| `lib/main.dart` | Pattern source for main_driver.dart |
| `lib/services/photo_service.dart` | Base class for TestPhotoService |
| `lib/test_harness/stub_services.dart` | Pattern reference for TestPhotoService |
| `lib/features/sync/engine/sync_engine.dart` | Posts sync status to debug server |
| `tools/debug-server/server.js` | Receives sync status + needs driver token endpoint |
| `lib/core/config/test_mode_config.dart` | DEBUG_SERVER constant (no change needed) |

## Test Files

No unit tests for driver_server.dart or main_driver.dart — these are test infrastructure themselves.
The proof flows (T01-T14) serve as integration tests.

## Dead Code to Clean Up

| Item | Action |
|------|--------|
| `.claude/test_results/flow_registry.md` | Delete after merge into unified registry |
| `.claude/skills/test/references/adb-commands.md` | Delete (ADB replaced by HTTP driver) |
| `.claude/skills/test/references/uiautomator-parsing.md` | Delete (UIAutomator replaced by HTTP driver) |

## Data Flow Diagram

```
Flutter App (main_driver.dart)
  ├─ IntegrationTestWidgetsFlutterBinding
  ├─ DriverServer (port 4948, auth token)
  │   ├─ POST /driver/tap → find.byKey() → tester.tap() → response
  │   ├─ POST /driver/text → find.byKey() → tester.enterText() → response
  │   ├─ GET /driver/find → find.byKey() → exists? → response
  │   ├─ GET /driver/screenshot → tester.takeScreenshot() → PNG bytes
  │   ├─ POST /driver/wait → pumpAndSettle() loop → visible+hittable
  │   ├─ POST /driver/inject-photo → TestPhotoService.inject() → queued file
  │   └─ POST /driver/inject-file → validated temp path → response
  ├─ TestPhotoService (extends PhotoService)
  │   └─ capturePhoto()/pickFromGallery() → return injected file from queue
  └─ Normal app via runApp(ConstructionInspectorApp(...))

Debug Server (port 3947, tools/debug-server/server.js)
  ├─ POST /sync/status ← SyncEngine._postSyncStatus()
  ├─ GET /sync/status → agents poll for sync completion
  ├─ GET /logs?since=X&level=error → agents check for runtime errors
  └─ POST /driver/token ← DriverServer posts auth token at startup

Agent (Claude subagent)
  ├─ POST http://localhost:4948/driver/* (with Bearer token) → HTTP driver
  ├─ GET http://localhost:3947/sync/status → sync completion check
  ├─ GET http://localhost:3947/logs?since=X → error detection
  └─ pwsh verify-sync.ps1 -CountOnly → Supabase verification
```

## Blast Radius Summary

| Category | Count |
|----------|-------|
| New files | 5 |
| Modified files | 4 |
| Dependent files (read-only) | 6 |
| Dead code to clean | 3 |
| Test files | 0 (proof flows are the tests) |
