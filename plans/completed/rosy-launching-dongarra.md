# Universal dart-mcp Widget Test Harness — Design & Implementation Plan

**Created**: 2026-02-21 | **Updated**: 2026-02-21 (Session 431 — revised after brainstorming audit)
**Status**: Design complete. Ready for implementation.

---

## Problem Statement

Testing individual widgets/screens in the Construction Inspector app currently requires either:
1. **Launching the full app** via `driver_main.dart` — boots 25 providers, auth, sync, database, router — just to reach one screen
2. **Widget tests** via `flutter test` — fast but no real rendering, no visual verification, no dart-mcp interaction

The MCP connection is unstable under the full app's resource load. A lightweight harness that renders **one screen at a time** reduces resource pressure and gives dart-mcp a more stable connection.

---

## Design Decisions (All Resolved)

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Screen selection mechanism | **Config file** (`harness_config.json`) | Claude writes JSON (reliable Write tool), then `launch_app` (one MCP call). Zero flutter_driver round-trips to select screen. Most stable option. |
| 2 | Entry point location | **`lib/test_harness.dart`** | Same pattern as existing `driver_main.dart`. Guaranteed to work with `launch_app(target:)`. Not imported by production code. |
| 3 | Provider strategy | **In-memory SQLite with real stack** | Real datasources → real repos → real providers backed by RAM. Zero type mismatches. Screens use exact same provider classes as production. No mock maintenance. |
| 4 | Navigation handling | **Stub GoRouter with `onException` handler** | Target screen at `/`. Any navigation attempt redirects back via `onException`. No crash on `goNamed` or multi-segment paths. |
| 5 | Widget keys | **Add as implementation step** | 0582B screens have zero ValueKeys. Must add before harness is useful for interaction testing. |
| 6 | Reusability scope | **Start 0582B, design universal** | Registry pattern accepts any screen. Initial implementation covers 5 0582B screens + all standalone screens. |
| 7 | Production code changes | **Minimal** | Only two changes: (a) `DatabaseService.forTesting()` named constructor for in-memory mode, (b) ValueKeys on screen widgets. Both non-breaking. |
| 8 | dart-define support | **Not available** in `launch_app()` | Confirmed: dart-mcp `launch_app` only accepts `root`, `device`, `target`. Config file approach works around this. |
| 9 | Data seeding strategy | **Two-tier** | Base seed (project, locations, entries) runs on every launch. Screen-specific `data` field provides overrides/additions. Most screens need zero custom config. |
| 10 | I/O services | **No-op stubs** | 5 services that do real I/O (FormPdfService, PdfService, WeatherService, PhotoService, ImageService) get thin stub replacements. Everything else uses real code. |

---

## Architecture

```
lib/test_harness.dart              ← Entry point (like driver_main.dart)
│
├─ enableFlutterDriverExtension()
├─ DatabaseService.initializeFfi() + DatabaseService.forTesting()
├─ Reads harness_config.json from project root
├─ Initializes in-memory SQLite database
├─ Creates real datasources → real repos → real providers
├─ Seeds base test data (project, locations, entries)
├─ Seeds screen-specific data from config
├─ Looks up screen in screenRegistry
├─ Builds MaterialApp:
│   ├─ ThemeProvider (real theme for accurate rendering)
│   ├─ GoRouter (stub with onException handler)
│   └─ MultiProvider (25 real providers + 5 stub services)
│       └─ The target widget
└─ runApp()

harness_config.json                ← Written by Claude before each launch
│
├─ "screen": "ProctorEntryScreen"
├─ "data": { "responseId": "test-123", ... }
└─ (Optional future fields)

test/harness/                      ← Support files
├─ screen_registry.dart            ← Map<String, ScreenBuilder>
├─ harness_providers.dart          ← Real provider tree backed by in-memory SQLite
├─ harness_seed_data.dart          ← Base seed + screen-specific seed helpers
├─ stub_router.dart                ← GoRouter with onException handler
└─ stub_services.dart              ← No-op stubs for 5 I/O services
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

### 1. DatabaseService.forTesting() — Production Code Change

**File**: `lib/core/database/database_service.dart`

Add a named constructor that creates an in-memory database instead of a file-based one:

```dart
class DatabaseService {
  static final DatabaseService _instance = DatabaseService._internal();
  factory DatabaseService() => _instance;
  DatabaseService._internal();

  // NEW: Testing constructor for in-memory database
  static DatabaseService? _testInstance;
  DatabaseService._forTesting();

  static DatabaseService forTesting() {
    _testInstance ??= DatabaseService._forTesting();
    return _testInstance!;
  }

  // Existing _database field becomes instance-level for test instance
  Database? _testDatabase;

  Future<Database> get database async {
    if (_testDatabase != null) return _testDatabase!;
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  // NEW: Initialize in-memory database
  Future<Database> initInMemory() async {
    _testDatabase = await openDatabase(
      inMemoryDatabasePath,
      version: 23,
      onCreate: _onCreate,
      onUpgrade: _onUpgrade,
    );
    return _testDatabase!;
  }
}
```

This is the **only production code change** beyond ValueKeys. It's non-breaking — production path is untouched.

### 2. Screen Registry (`test/harness/screen_registry.dart`)

```dart
typedef ScreenBuilder = Widget Function(Map<String, dynamic> data);

final Map<String, ScreenBuilder> screenRegistry = {
  // Forms (0582B)
  'ProctorEntryScreen': (data) => ProctorEntryScreen(responseId: data['responseId']),
  'QuickTestEntryScreen': (data) => QuickTestEntryScreen(responseId: data['responseId']),
  'WeightsEntryScreen': (data) => WeightsEntryScreen(responseId: data['responseId']),
  'FormViewerScreen': (data) => FormViewerScreen(responseId: data['responseId']),
  'FormFillScreen': (data) => FormFillScreen(responseId: data['responseId']),
  'FormsListScreen': (_) => const FormsListScreen(),
  // Dashboard & Navigation
  'ProjectDashboardScreen': (_) => const ProjectDashboardScreen(),
  'HomeScreen': (_) => const HomeScreen(),
  'ProjectListScreen': (_) => const ProjectListScreen(),
  'SettingsScreen': (_) => const SettingsScreen(),
  // Entries
  'EntriesListScreen': (_) => const EntriesListScreen(),
  'EntryEditorScreen': (data) => EntryEditorScreen(
    projectId: data['projectId'] ?? 'test-project-001',
    date: data['date'] != null ? DateTime.parse(data['date']) : null,
    locationId: data['locationId'],
    entryId: data['entryId'],
  ),
  // Toolbox features
  'ToolboxHomeScreen': (_) => const ToolboxHomeScreen(),
  'CalculatorScreen': (_) => const CalculatorScreen(),
  'GalleryScreen': (_) => const GalleryScreen(),
  'TodosScreen': (_) => const TodosScreen(),
  // Quantities
  'QuantitiesScreen': (_) => const QuantitiesScreen(),
  'QuantityCalculatorScreen': (data) => QuantityCalculatorScreen(
    entryId: data['entryId'] ?? 'test-entry-001',
  ),
  // Projects
  'ProjectSetupScreen': (data) => ProjectSetupScreen(
    projectId: data['projectId'],
  ),
  // Settings
  'PersonnelTypesScreen': (data) => PersonnelTypesScreen(
    projectId: data['projectId'] ?? 'test-project-001',
  ),
  // Auth (for completeness — usually tested separately)
  'LoginScreen': (_) => const LoginScreen(),
  'RegisterScreen': (_) => const RegisterScreen(),
  'ForgotPasswordScreen': (_) => const ForgotPasswordScreen(),
};
```

**26 screens registered.** Only PDF import screens excluded (they require `state.extra` objects that can't be serialized via JSON config).

### 3. Harness Providers (`test/harness/harness_providers.dart`)

Uses the **real** datasource → repo → provider stack, backed by in-memory SQLite:

```dart
Future<List<SingleChildWidget>> buildHarnessProviders(
  DatabaseService dbService,
  Map<String, dynamic> data,
) async {
  // Real datasources backed by in-memory DB
  final projectDs = ProjectLocalDatasource(dbService);
  final locationDs = LocationLocalDatasource(dbService);
  final contractorDs = ContractorLocalDatasource(dbService);
  final equipmentDs = EquipmentLocalDatasource(dbService);
  final bidItemDs = BidItemLocalDatasource(dbService);
  final dailyEntryDs = DailyEntryLocalDatasource(dbService);
  final entryQuantityDs = EntryQuantityLocalDatasource(dbService);
  final personnelTypeDs = PersonnelTypeLocalDatasource(dbService);
  final photoDs = PhotoLocalDatasource(dbService);
  final inspectorFormDs = InspectorFormLocalDatasource(dbService);
  final formResponseDs = FormResponseLocalDatasource(dbService);
  final calcHistoryDs = CalculationHistoryLocalDatasource(dbService);
  final todoItemDs = TodoItemLocalDatasource(dbService);

  // Real repositories
  final projectRepo = ProjectRepository(projectDs);
  final locationRepo = LocationRepository(locationDs);
  final contractorRepo = ContractorRepository(contractorDs);
  final equipmentRepo = EquipmentRepository(equipmentDs);
  final bidItemRepo = BidItemRepository(bidItemDs);
  final dailyEntryRepo = DailyEntryRepository(dailyEntryDs);
  final entryQuantityRepo = EntryQuantityRepository(entryQuantityDs);
  final personnelTypeRepo = PersonnelTypeRepository(personnelTypeDs);
  final photoRepo = PhotoRepository(photoDs);
  final inspectorFormRepo = InspectorFormRepository(inspectorFormDs);
  final formResponseRepo = FormResponseRepository(formResponseDs);

  // Stub services (I/O services that can't use real implementations)
  final stubSyncService = StubSyncService();
  final stubPhotoService = StubPhotoService();
  final stubFormPdfService = StubFormPdfService();
  final stubPdfService = StubPdfService();
  final stubWeatherService = StubWeatherService();
  final stubImageService = StubImageService();

  // Preferences (in-memory)
  final preferencesService = PreferencesService();
  await preferencesService.initialize();

  // Auth (unauthenticated — Supabase not configured)
  final authService = AuthService(null);

  final projectSettingsProvider = ProjectSettingsProvider();
  await projectSettingsProvider.initialize();

  return [
    // ChangeNotifier providers (real implementations)
    ChangeNotifierProvider.value(value: preferencesService),
    ChangeNotifierProvider(create: (_) => AuthProvider(authService)),
    ChangeNotifierProvider(create: (_) => ThemeProvider()),
    ChangeNotifierProvider.value(value: projectSettingsProvider),
    ChangeNotifierProvider(create: (_) => ProjectProvider(projectRepo)),
    ChangeNotifierProvider(create: (_) => LocationProvider(locationRepo)),
    ChangeNotifierProvider(create: (_) => ContractorProvider(contractorRepo)),
    ChangeNotifierProvider(create: (_) => EquipmentProvider(equipmentRepo)),
    ChangeNotifierProvider(create: (_) => BidItemProvider(bidItemRepo)),
    ChangeNotifierProvider(create: (_) => DailyEntryProvider(dailyEntryRepo)),
    ChangeNotifierProvider(create: (_) => EntryQuantityProvider(entryQuantityRepo)),
    ChangeNotifierProvider(create: (_) => PhotoProvider(photoRepo)),
    ChangeNotifierProvider(create: (_) => PersonnelTypeProvider(personnelTypeRepo)),
    ChangeNotifierProvider(create: (_) => SyncProvider(stubSyncService)),
    ChangeNotifierProvider(create: (_) => CalendarFormatProvider()),
    ChangeNotifierProvider(create: (_) => InspectorFormProvider(
      inspectorFormRepo, formResponseRepo, syncService: stubSyncService,
    )),
    ChangeNotifierProvider(create: (_) => CalculatorProvider(
      calcHistoryDs, syncService: stubSyncService,
    )),
    ChangeNotifierProvider(create: (_) => GalleryProvider(photoRepo, dailyEntryRepo)),
    ChangeNotifierProvider(create: (_) => TodoProvider(
      todoItemDs, syncService: stubSyncService,
    )),
    // Non-ChangeNotifier services (stubs for I/O)
    Provider<PhotoService>.value(value: stubPhotoService),
    Provider<FormPdfService>.value(value: stubFormPdfService),
    Provider<PdfService>.value(value: stubPdfService),
    Provider<WeatherService>.value(value: stubWeatherService),
    Provider<ImageService>.value(value: stubImageService),
    Provider<DatabaseService>.value(value: dbService),
  ];
}
```

**Key insight**: 20 of 25 providers use the real implementation. Only 5 I/O services are stubbed.

### 4. Stub Services (`test/harness/stub_services.dart`)

```dart
/// No-op SyncService — never syncs, always reports success
class StubSyncService extends SyncService {
  StubSyncService() : super(/* in-memory db */);
  // Override sync methods to no-op
}

/// No-op PhotoService — skip file system operations
class StubPhotoService implements PhotoService { ... }

/// No-op FormPdfService — returns empty PDF bytes
class StubFormPdfService implements FormPdfService { ... }

/// No-op PdfService — returns empty bytes
class StubPdfService implements PdfService { ... }

/// No-op WeatherService — returns null/default weather
class StubWeatherService implements WeatherService { ... }

/// No-op ImageService — returns input unchanged
class StubImageService implements ImageService { ... }
```

**Note**: Exact stub signatures depend on each service's public API. Implementation phase will determine if `extends` or `implements` is appropriate based on constructor requirements.

### 5. Stub Router (`test/harness/stub_router.dart`)

```dart
GoRouter buildStubRouter(Widget targetScreen) {
  return GoRouter(
    initialLocation: '/',
    onException: (context, state, router) {
      // Any unmatched navigation (goNamed, go, push) loops back to target
      router.go('/');
    },
    routes: [
      GoRoute(path: '/', builder: (_, __) => targetScreen),
    ],
  );
}
```

**Why `onException` instead of catch-all**: The plan's original `/:any` pattern only catches single-segment paths. `goNamed('proctor-entry', ...)` throws because the name doesn't exist. `onException` catches everything — named routes, multi-segment paths, any navigation attempt.

### 6. Harness Seed Data (`test/harness/harness_seed_data.dart`)

Two-tier seeding:

```dart
/// Base seed — runs on every harness launch
/// Provides the minimum context most screens need
Future<void> seedBaseData(DatabaseService db) async {
  final rawDb = await db.database;

  // One project (auto-selected in ProjectProvider)
  await rawDb.insert('projects', {
    'id': 'test-project-001',
    'name': 'Harness Test Project',
    'project_number': 'HTP-001',
    'is_active': 1,
    'sync_status': 'synced',
    'created_at': DateTime.now().toIso8601String(),
    'updated_at': DateTime.now().toIso8601String(),
  });

  // Two locations
  await rawDb.insert('locations', {
    'id': 'test-location-001',
    'project_id': 'test-project-001',
    'name': 'Main Site',
    'sync_status': 'synced',
    'created_at': DateTime.now().toIso8601String(),
    'updated_at': DateTime.now().toIso8601String(),
  });
  await rawDb.insert('locations', {
    'id': 'test-location-002',
    'project_id': 'test-project-001',
    'name': 'Secondary Site',
    'sync_status': 'synced',
    'created_at': DateTime.now().toIso8601String(),
    'updated_at': DateTime.now().toIso8601String(),
  });

  // One daily entry
  await rawDb.insert('daily_entries', {
    'id': 'test-entry-001',
    'project_id': 'test-project-001',
    'location_id': 'test-location-001',
    'date': DateTime.now().toIso8601String(),
    'status': 'draft',
    'sync_status': 'synced',
    'created_at': DateTime.now().toIso8601String(),
    'updated_at': DateTime.now().toIso8601String(),
  });

  // One contractor
  await rawDb.insert('contractors', {
    'id': 'test-contractor-001',
    'project_id': 'test-project-001',
    'name': 'Test Contractor Inc.',
    'type': 'prime',
    'sync_status': 'synced',
    'created_at': DateTime.now().toIso8601String(),
    'updated_at': DateTime.now().toIso8601String(),
  });
}

/// Screen-specific seed — adds extra data based on config
Future<void> seedScreenData(DatabaseService db, String screen, Map<String, dynamic> data) async {
  switch (screen) {
    case 'ProctorEntryScreen':
    case 'QuickTestEntryScreen':
    case 'WeightsEntryScreen':
    case 'FormViewerScreen':
    case 'FormFillScreen':
      await _seedFormData(db, data);
      break;
    // Add cases as needed for other screens
  }
}

Future<void> _seedFormData(DatabaseService db, Map<String, dynamic> data) async {
  final rawDb = await db.database;
  final responseId = data['responseId'] ?? 'test-response-001';
  // Seed inspector_forms and form_responses tables
  // ... specific to form type
}
```

### 7. Entry Point (`lib/test_harness.dart`)

```dart
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_driver/driver_extension.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/theme/app_theme.dart';
import '../test/harness/screen_registry.dart';
import '../test/harness/harness_providers.dart';
import '../test/harness/harness_seed_data.dart';
import '../test/harness/stub_router.dart';

void main() async {
  enableFlutterDriverExtension();
  WidgetsFlutterBinding.ensureInitialized();

  // Read config
  final configFile = File('harness_config.json');
  final config = configFile.existsSync()
      ? jsonDecode(configFile.readAsStringSync()) as Map<String, dynamic>
      : {'screen': 'FormsListScreen', 'data': {}};

  final screenName = config['screen'] as String;
  final data = (config['data'] as Map<String, dynamic>?) ?? {};

  // Lookup screen
  final builder = screenRegistry[screenName];
  if (builder == null) {
    runApp(MaterialApp(home: Scaffold(
      body: Center(child: Text('Unknown screen: $screenName')),
    )));
    return;
  }

  // Initialize in-memory database
  DatabaseService.initializeFfi();
  final dbService = DatabaseService.forTesting();
  await dbService.initInMemory();

  // Seed data (two-tier)
  await seedBaseData(dbService);
  await seedScreenData(dbService, screenName, data);

  // Build providers (real stack + stub services)
  final providers = await buildHarnessProviders(dbService, data);

  // Build target widget
  final targetWidget = builder(data);
  final router = buildStubRouter(targetWidget);

  runApp(
    MultiProvider(
      providers: providers,
      child: Consumer<ThemeProvider>(
        builder: (context, themeProvider, _) {
          return MaterialApp.router(
            title: 'Harness',
            theme: themeProvider.currentTheme,
            routerConfig: router,
          );
        },
      ),
    ),
  );
}
```

**Note on imports**: `test/harness/` files importing from `lib/` is standard (test → lib). But `lib/test_harness.dart` importing from `test/harness/` requires a `package:` path or relative path that works at build time. **Implementation must verify this works** — may need to move harness support files to `lib/test_harness/` instead if test imports don't resolve at compile time.

---

## Existing Infrastructure to Reuse

| Asset | Location | Reuse |
|-------|----------|-------|
| TestingKeys | `lib/shared/testing_keys/` | Widget identification via flutter_driver |
| driver_main.dart | `lib/driver_main.dart` | Reference for flutter_driver extension setup |
| App theme | `lib/core/theme/app_theme.dart` | Real theme for accurate rendering |
| Database schema | `lib/core/database/schema/` | In-memory DB uses same schema |
| All datasources | `lib/features/*/data/datasources/` | Used directly with in-memory DB |
| All repositories | `lib/features/*/data/repositories/` | Used directly with real datasources |
| All providers | `lib/features/*/presentation/providers/` | Used directly with real repos |

**Note**: The existing mock repos/providers in `test/helpers/mocks/` are **NOT used** by the harness. The harness uses the real stack instead, avoiding type mismatches.

---

## Implementation Phases

### Phase 0: DatabaseService.forTesting() (production code change)
**Files**: `lib/core/database/database_service.dart`
**Agent**: `backend-data-layer-agent`
**Scope**:
- Add `DatabaseService.forTesting()` named constructor
- Add `initInMemory()` method that creates in-memory SQLite
- Verify existing tests still pass (`flutter test`)
**Verification**: `flutter test` green. `DatabaseService.forTesting().initInMemory()` returns a working Database.

### Phase 1: Harness Skeleton (entry point + registry + stub router + config)
**Files**: `lib/test_harness.dart`, `test/harness/screen_registry.dart`, `test/harness/stub_router.dart`
**Agent**: `frontend-flutter-specialist-agent`
**Scope**:
- Create `lib/test_harness.dart` with `enableFlutterDriverExtension()` + config file reader
- Create screen registry with one test screen (simple `Scaffold` with "Hello Harness" text)
- Create stub GoRouter with `onException` handler
- Write `harness_config.json` and verify launch via dart-mcp
- **Resolve import path issue**: determine if `test/harness/` files can be imported from `lib/test_harness.dart`, or if harness support files need to live under `lib/test_harness/`
**Verification**: `launch_app(target: "lib/test_harness.dart")` → screenshot shows "Hello Harness"

### Phase 2: Provider Stack + Seed Data
**Files**: `test/harness/harness_providers.dart` (or `lib/test_harness/`), `test/harness/harness_seed_data.dart`, `test/harness/stub_services.dart`
**Agent**: `backend-data-layer-agent`
**Scope**:
- Build `buildHarnessProviders()` with all 25 providers (20 real + 5 stubs)
- Create 5 stub services (SyncService, PhotoService, FormPdfService, PdfService, WeatherService, ImageService)
- Build `seedBaseData()` — one project, two locations, one entry, one contractor
- Build `seedScreenData()` — form-specific seed for 0582B screens
- Wire into `lib/test_harness.dart`
**Verification**: Harness boots with full provider tree, no missing-provider exceptions. Screenshot shows real themed UI.

### Phase 3: Screen Integration (0582B + standalone screens)
**Files**: Update `screen_registry.dart`
**Agent**: `frontend-flutter-specialist-agent`
**Scope**:
- Register all 26 screens in the registry
- Wire up ProjectProvider with base-seed project (auto-select after loadProjects)
- Test 0582B screens: write config → launch → screenshot → verify rendered content
- Test standalone screens (Calculator, Gallery, Todos, Dashboard): verify they render with base seed only
- Fix any provider dependency issues discovered during integration
**Verification**: Each registered screen renders via harness. Screenshot visual verification.

### Phase 4: Add ValueKeys to 0582B Screens
**Files**: `lib/features/forms/presentation/screens/*.dart`, `lib/shared/testing_keys/testing_keys.dart`
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
- Test switching screens: stop app → change config → relaunch → verify different screen
- Test error case: unknown screen name → verify "Unknown screen" message
- Document findings in `.claude/test-results/`
- Confirm MCP stability is improved vs full-app launch
**Verification**: All 5 0582B screens interactive via harness with stable MCP connection

---

## Brainstorming Audit Findings (Session 431)

Issues discovered during implementation readiness audit:

| # | Finding | Resolution |
|---|---------|------------|
| 1 | Existing mock repos/providers don't implement real types — `MockProjectRepository` is not a `ProjectRepository` | Use in-memory SQLite with real stack instead of mocks |
| 2 | `DatabaseService` is a singleton — can't create in-memory instance | Add `forTesting()` named constructor (Phase 0) |
| 3 | Config `data` field only covers constructor params, not provider state | Two-tier seeding: base seed for common state + screen-specific overrides |
| 4 | Stub router catch-all `/:any` doesn't handle `goNamed` or multi-segment paths | Replace with `onException` handler that redirects to `/` |
| 5 | 5 I/O services (FormPdfService, PdfService, WeatherService, PhotoService, ImageService) can't use real implementations in harness | Create thin no-op stubs |
| 6 | `lib/test_harness.dart` importing from `test/harness/` may not compile | Phase 1 resolves: may need `lib/test_harness/` directory instead |

---

## Documentation Plan

### CLAUDE.md Addition (new section after "UI Testing via dart-mcp")

```markdown
## Widget Test Harness (Isolated Screen Testing)

Lightweight entry point that renders a single screen with real providers backed by in-memory SQLite.
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
1. Add entry to screen registry (one line)
2. Add ValueKeys to the screen's interactive widgets
3. Add keys to `lib/shared/testing_keys/testing_keys.dart`
No provider changes needed — all 25 providers are already available.

### Data Seeding
- Base seed auto-creates: 1 project, 2 locations, 1 entry, 1 contractor
- Screen-specific data passed via config `data` field
- Most screens work with just `{"screen": "ScreenName"}` — no data needed
```

### patrol-testing.md Updates

- **Remove**: Entire "Marionette MCP" section — Marionette was removed in Session 409
- **Replace with**: Widget Test Harness section (config format, launch sequence, available screens)
- **Update**: Testing Strategy from 3-tier to 4-tier:
  1. Unit tests (`test/`) — models, repos, providers, services
  2. Widget test harness (`lib/test_harness.dart`) — isolated screen rendering + interaction via dart-mcp
  3. dart-mcp full app (`lib/driver_main.dart`) — full app E2E with flutter_driver
  4. Manual checklist — `.claude/docs/guides/testing/manual-testing-checklist.md`

---

## Success Criteria

- [ ] Can launch a single screen via dart-mcp without booting full app
- [ ] Can interact with the screen (tap, enter text) via flutter_driver
- [ ] Can take screenshots for visual verification
- [ ] Base seed provides enough context for most screens without custom config
- [ ] Screen-specific data is configurable via harness_config.json
- [ ] Adding a new screen to the harness takes < 5 minutes (one registry entry)
- [ ] Production code changes are minimal (DatabaseService.forTesting + ValueKeys only)
- [ ] Harness works on Windows (primary dev platform)
- [ ] MCP connection is more stable than full-app launch
- [ ] CLAUDE.md and patrol-testing.md document the harness with explicit instructions
- [ ] Marionette references removed from all documentation
- [ ] 26 screens registered and verified renderable

---

## References

- **dart-mcp launch_app signature**: `root`, `device`, `target` only (no `--dart-define`)
- **Existing driver entry point**: `lib/driver_main.dart`
- **App provider tree**: `lib/main.dart` (25 providers, lines 481-565)
- **Database schema**: `lib/core/database/schema/` (version 23, 13 datasources)
- **Testing keys**: `lib/shared/testing_keys/testing_keys.dart`
- **CLAUDE.md UI Testing section**: Launch sequence and flutter_driver limitations
