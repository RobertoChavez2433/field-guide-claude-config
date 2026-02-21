# Universal dart-mcp Widget Test Harness — Design & Implementation Plan

**Created**: 2026-02-21 | **Updated**: 2026-02-21 (Session 428)
**Status**: Design complete. Ready for implementation.

---

## Problem Statement

Testing individual widgets/screens in the Construction Inspector app currently requires either:
1. **Launching the full app** via `driver_main.dart` — boots 24+ providers, auth, sync, database, router — just to reach one screen
2. **Widget tests** via `flutter test` — fast but no real rendering, no visual verification, no dart-mcp interaction

The MCP connection is unstable under the full app's resource load. A lightweight harness that renders **one screen at a time** reduces resource pressure and gives dart-mcp a more stable connection.

---

## Design Decisions (All Resolved)

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Screen selection mechanism | **Config file** (`harness_config.json`) | Claude writes JSON (reliable Write tool), then `launch_app` (one MCP call). Zero flutter_driver round-trips to select screen. Most stable option. |
| 2 | Entry point location | **`lib/test_harness.dart`** | Same pattern as existing `driver_main.dart`. Guaranteed to work with `launch_app(target:)`. Not imported by production code. |
| 3 | Provider mapping | **Universal superset of mocked providers** | Mocked providers are lightweight (in-memory). Savings come from not booting SQLite/Supabase/auth/sync, not from fewer providers. No per-screen mapping to maintain. |
| 4 | Navigation handling | **Real GoRouter with stub routes** | Target screen renders normally. Navigation calls land on a placeholder instead of crashing. No full router boot. |
| 5 | Widget keys | **Add as implementation step** | 0582B screens have zero ValueKeys. Must add before harness is useful for interaction testing. |
| 6 | Reusability scope | **Start 0582B, design universal** | Registry pattern accepts any screen. Initial implementation covers 5 0582B screens. |
| 7 | Production code | **Untouched** | Harness lives entirely in `lib/test_harness.dart` + `test/harness/`. Only addition to prod code is ValueKeys (non-breaking). |
| 8 | dart-define support | **Not available** in `launch_app()` | Confirmed: dart-mcp `launch_app` only accepts `root`, `device`, `target`. Config file approach works around this. |

---

## Architecture

```
lib/test_harness.dart              ← Entry point (like driver_main.dart)
│
├─ enableFlutterDriverExtension()
├─ Reads harness_config.json from project root
├─ Looks up screen in screenRegistry
├─ Builds minimal MaterialApp:
│   ├─ AppTheme (real theme for accurate rendering)
│   ├─ GoRouter (stub routes)
│   └─ MultiProvider (universal mocked superset)
│       └─ The target widget
└─ runApp()

harness_config.json                ← Written by Claude before each launch
│
├─ "screen": "ProctorEntryScreen"
├─ "data": { "responseId": "test-123", ... }
└─ (Optional future fields)

test/harness/                      ← Support files
├─ screen_registry.dart            ← Map<String, WidgetBuilder>
├─ mock_provider_superset.dart     ← All mocked providers
├─ stub_router.dart                ← GoRouter with placeholder routes
└─ test_data_builders.dart         ← Realistic domain test data
```

### Config File Format

```json
{
  "screen": "ProctorEntryScreen",
  "data": {
    "responseId": "test-response-001",
    "formType": "mdot_0582b"
  }
}
```

### Launch Sequence (dart-mcp)

```
1. Claude writes harness_config.json (Write tool — no MCP)
2. launch_app(
     root: "C:\Users\rseba\Projects\Field Guide App",
     device: "windows",
     target: "lib/test_harness.dart"
   )
3. connect_dart_tooling_daemon(uri: <dtdUri>)
4. flutter_driver screenshot → verify widget rendered
5. flutter_driver tap/enter_text/get_text → interact
6. flutter_driver screenshot → verify result
```

---

## Components to Build

### 1. Screen Registry (`test/harness/screen_registry.dart`)

```dart
typedef ScreenBuilder = Widget Function(Map<String, dynamic> data);

final Map<String, ScreenBuilder> screenRegistry = {
  // 0582B screens (initial)
  'ProctorEntryScreen': (data) => ProctorEntryScreen(responseId: data['responseId']),
  'QuickTestEntryScreen': (data) => QuickTestEntryScreen(responseId: data['responseId']),
  'WeightsEntryScreen': (data) => WeightsEntryScreen(responseId: data['responseId']),
  'FormViewerScreen': (data) => FormViewerScreen(responseId: data['responseId']),
  'FormsListScreen': (_) => const FormsListScreen(),
  // Future: any screen in the app
};
```

### 2. Mock Provider Superset (`test/harness/mock_provider_superset.dart`)

Provides ALL providers the app uses, all backed by in-memory mocks:

| Provider | Mock Source |
|----------|------------|
| `InspectorFormProvider` | New mock with in-memory FormResponseRepository |
| `ProjectProvider` | Existing `MockProjectRepository` |
| `PreferencesService` | In-memory SharedPreferences |
| `FormPdfService` | No-op stub (returns empty PDF bytes) |
| `DailyEntryProvider` | Existing mock pattern |
| `ContractorProvider` | Existing mock pattern |
| `AuthProvider` | Pre-authenticated stub |
| `SyncService` | No-op (never syncs) |
| `DatabaseService` | In-memory SQLite or no-op |
| ... | All 24+ providers mocked |

### 3. Stub Router (`test/harness/stub_router.dart`)

```dart
GoRouter buildStubRouter(Widget targetScreen) {
  return GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(path: '/', builder: (_, __) => targetScreen),
      // Catch-all for any navigation the screen attempts
      GoRoute(path: '/:any', builder: (_, state) => Scaffold(
        body: Center(child: Text('Stub: ${state.uri}')),
      )),
    ],
  );
}
```

### 4. Test Data Builders (`test/harness/test_data_builders.dart`)

```dart
class HarnessTestData {
  static FormResponse sampleFormResponse({
    String? id,
    String formType = 'mdot_0582b',
  }) => FormResponse(id: id ?? 'test-${Uuid().v4()}', ...);

  static Project sampleProject() => Project(name: 'Test Project', ...);
  // Realistic domain data for each entity
}
```

### 5. Entry Point (`lib/test_harness.dart`)

```dart
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_driver/driver_extension.dart';
// ... imports for registry, providers, router, theme

void main() {
  enableFlutterDriverExtension();

  final configFile = File('harness_config.json');
  final config = configFile.existsSync()
      ? jsonDecode(configFile.readAsStringSync()) as Map<String, dynamic>
      : {'screen': 'FormsListScreen', 'data': {}};

  final screenName = config['screen'] as String;
  final data = (config['data'] as Map<String, dynamic>?) ?? {};

  final builder = screenRegistry[screenName];
  if (builder == null) {
    runApp(MaterialApp(home: Scaffold(
      body: Center(child: Text('Unknown screen: $screenName')),
    )));
    return;
  }

  final targetWidget = builder(data);
  final router = buildStubRouter(targetWidget);

  runApp(
    MultiProvider(
      providers: buildMockProviderSuperset(data),
      child: MaterialApp.router(
        theme: AppTheme.lightTheme,
        darkTheme: AppTheme.darkTheme,
        routerConfig: router,
      ),
    ),
  );
}
```

---

## Existing Infrastructure to Reuse

| Asset | Location | Reuse |
|-------|----------|-------|
| TestingKeys | `lib/shared/testing_keys/` | Widget identification via flutter_driver |
| Mock repos | `test/helpers/mocks/mock_repositories.dart` | Project, Location, etc. mocks |
| Mock services | `test/helpers/mocks/mock_services.dart` | SyncService, AuthService stubs |
| Provider wrapper | `test/helpers/provider_wrapper.dart` | `createTestAppWithProviders()` pattern |
| driver_main.dart | `lib/driver_main.dart` | Reference for flutter_driver extension setup |
| App theme | `lib/core/theme/app_theme.dart` | Real theme for accurate rendering |
| Golden test helpers | `test/golden/test_helpers.dart` | `goldenTestWrapper()` MaterialApp pattern |

---

## Implementation Phases

### Phase 1: Harness Skeleton (entry point + registry + config)
**Files**: `lib/test_harness.dart`, `test/harness/screen_registry.dart`, `test/harness/stub_router.dart`
**Agent**: `frontend-flutter-specialist-agent`
**Scope**:
- Create `lib/test_harness.dart` with `enableFlutterDriverExtension()` + config file reader
- Create screen registry with one test screen (simple `Scaffold` with "Hello Harness" text)
- Create stub GoRouter
- Write `harness_config.json` and verify launch via dart-mcp
**Verification**: `launch_app(target: "lib/test_harness.dart")` → screenshot shows "Hello Harness"

### Phase 2: Mock Provider Superset
**Files**: `test/harness/mock_provider_superset.dart`, `test/harness/test_data_builders.dart`
**Agent**: `backend-data-layer-agent`
**Scope**:
- Build universal mock provider list covering all 24+ app providers
- Reuse existing mocks from `test/helpers/mocks/`
- Create new mocks only where missing (InspectorFormProvider, FormPdfService, etc.)
- Build test data factories for 0582B domain entities (FormResponse, proctor rows, test rows)
**Verification**: Harness boots with full provider tree, no missing-provider exceptions

### Phase 3: 0582B Screen Integration
**Files**: Update `test/harness/screen_registry.dart`, potentially screen constructors
**Agent**: `frontend-flutter-specialist-agent`
**Scope**:
- Register all 5 0582B screens in the registry
- Wire up InspectorFormProvider with test data so screens render populated
- Test each screen: write config → launch → screenshot → verify rendered content
- Fix any provider dependency issues discovered during integration
**Verification**: Each 0582B screen renders with test data via harness

### Phase 4: Add ValueKeys to 0582B Screens
**Files**: `lib/features/toolbox/presentation/screens/*.dart`, `lib/shared/testing_keys/testing_keys.dart`
**Agent**: `frontend-flutter-specialist-agent`
**Scope**:
- Audit all 5 0582B screens for interactive elements (buttons, text fields, dropdowns, chips)
- Add `ValueKey` constants to `TestingKeys` class
- Apply keys to widgets in screen source files
- Verify keys visible via flutter_driver `waitFor(ByValueKey('key_name'))`
**Verification**: flutter_driver can find and interact with all key elements on each screen

### Phase 5: Documentation Updates
**Files**: `.claude/CLAUDE.md`, `.claude/rules/testing/patrol-testing.md`
**Agent**: Inline (no subagent needed)
**Scope**:
- Add "Widget Test Harness" section to CLAUDE.md (launch sequence, config format, usage)
- Update `patrol-testing.md`: replace outdated Marionette section with harness instructions
- Add harness to the testing strategy (3-tier → 4-tier)
- Document how to add new screens to the registry
**Verification**: Documentation is accurate, no references to Marionette

### Phase 6: Validation Run
**Agent**: `qa-testing-agent`
**Scope**:
- End-to-end validation: write config → launch harness → interact with each 0582B screen
- Verify: screenshots, tap interactions, text entry, navigation stubs
- Document findings in `.claude/test-results/`
- Confirm MCP stability is improved vs full-app launch
**Verification**: All 5 screens interactive via harness with stable MCP connection

---

## Documentation Plan

### CLAUDE.md Addition (new section after "UI Testing via dart-mcp")

```markdown
## Widget Test Harness (Isolated Screen Testing)

Lightweight entry point that renders a single screen with mocked providers.
Less resource-intensive than full app — more stable MCP connection.

### Launch Sequence
1. Write `harness_config.json` in project root:
   {"screen": "ProctorEntryScreen", "data": {"responseId": "test-123"}}
2. launch_app(root: "...", device: "windows", target: "lib/test_harness.dart")
3. connect_dart_tooling_daemon(uri: <dtdUri>)
4. flutter_driver commands (screenshot, tap, enter_text, etc.)

### Available Screens
[Registry list — updated as screens are added]

### Adding a New Screen
1. Add entry to `test/harness/screen_registry.dart`
2. Add ValueKeys to the screen's widgets
3. Add keys to `lib/shared/testing_keys/testing_keys.dart`
No other changes needed — providers are universal.
```

### patrol-testing.md Updates

- **Remove**: Entire "Marionette MCP" section (lines 185-210) — Marionette was removed in Session 409
- **Replace with**: Widget Test Harness section (config format, launch sequence, available screens)
- **Update**: Testing Strategy from 3-tier to 4-tier:
  1. Unit tests (`test/`) — models, repos, providers, services
  2. Widget test harness (`lib/test_harness.dart`) — isolated screen rendering + interaction via dart-mcp
  3. dart-mcp full app (`lib/driver_main.dart`) — full app E2E with flutter_driver
  4. Manual checklist — `.claude/docs/guides/testing/manual-testing-checklist.md`

---

## Success Criteria

- [ ] Can launch a single 0582B screen via dart-mcp without booting full app
- [ ] Can interact with the screen (tap, enter text) via flutter_driver
- [ ] Can take screenshots for visual verification
- [ ] Mock data is realistic and configurable via harness_config.json
- [ ] Adding a new screen to the harness takes < 5 minutes (one registry entry)
- [ ] Production code remains untouched (only ValueKey additions)
- [ ] Harness works on Windows (primary dev platform)
- [ ] MCP connection is more stable than full-app launch
- [ ] CLAUDE.md and patrol-testing.md document the harness with explicit instructions
- [ ] Marionette references removed from all documentation

---

## References

- **dart-mcp launch_app signature**: `root`, `device`, `target` only (no `--dart-define`)
- **Existing driver entry point**: `lib/driver_main.dart`
- **App provider tree**: `lib/main.dart`
- **Mock infrastructure**: `test/helpers/mocks/`
- **Testing keys**: `lib/shared/testing_keys/testing_keys.dart`
- **CLAUDE.md UI Testing section**: Launch sequence and flutter_driver limitations
