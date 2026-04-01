# Source Excerpts — By File

## lib/core/di/app_initializer.dart (891 lines)

### CoreDeps (lines 115-143)
```dart
class CoreDeps {
  final DatabaseService dbService;
  final PreferencesService preferencesService;
  final PhotoService photoService;
  final ImageService imageService;
  final TrashRepository trashRepository;
  final SoftDeleteService softDeleteService;
  final PermissionService permissionService;

  const CoreDeps({
    required this.dbService,
    required this.preferencesService,
    required this.photoService,
    required this.imageService,
    required this.trashRepository,
    required this.softDeleteService,
    required this.permissionService,
  });

  CoreDeps copyWith({PhotoService? photoService}) => CoreDeps(
        dbService: dbService,
        preferencesService: preferencesService,
        photoService: photoService ?? this.photoService,
        imageService: imageService,
        trashRepository: trashRepository,
        softDeleteService: softDeleteService,
        permissionService: permissionService,
      );
}
```

### AuthDeps (lines 146-156)
```dart
class AuthDeps {
  final AuthService authService;
  final AuthProvider authProvider;
  final AppConfigProvider appConfigProvider;

  const AuthDeps({
    required this.authService,
    required this.authProvider,
    required this.appConfigProvider,
  });
}
```

### ProjectDeps (lines 159-187)
```dart
class ProjectDeps {
  final ProjectRepository projectRepository;
  final ProjectAssignmentProvider projectAssignmentProvider;
  final ProjectSettingsProvider projectSettingsProvider;
  final ProjectSyncHealthProvider projectSyncHealthProvider;
  final ProjectImportRunner projectImportRunner;
  final ProjectLifecycleService projectLifecycleService;
  final SyncedProjectRepository syncedProjectRepository;
  final CompanyMembersRepository? companyMembersRepository;
  final DeleteProjectUseCase deleteProjectUseCase;
  final LoadAssignmentsUseCase loadAssignmentsUseCase;
  final FetchRemoteProjectsUseCase fetchRemoteProjectsUseCase;
  final LoadCompanyMembersUseCase? loadCompanyMembersUseCase;

  const ProjectDeps({...});
}
```

### EntryDeps (lines 190-208)
```dart
class EntryDeps {
  final DailyEntryRepository dailyEntryRepository;
  final EntryExportRepository entryExportRepository;
  final DocumentRepository documentRepository;
  final DocumentService documentService;
  final EntryPersonnelCountsLocalDatasource entryPersonnelCountsDatasource;
  final EntryEquipmentLocalDatasource entryEquipmentDatasource;
  final EntryContractorsLocalDatasource entryContractorsDatasource;

  const EntryDeps({...});
}
```

### FormDeps (lines 211-223)
```dart
class FormDeps {
  final InspectorFormRepository inspectorFormRepository;
  final FormResponseRepository formResponseRepository;
  final FormExportRepository formExportRepository;
  final FormPdfService formPdfService;

  const FormDeps({...});
}
```

### SyncDeps (lines 226-234)
```dart
class SyncDeps {
  final SyncOrchestrator syncOrchestrator;
  final SyncLifecycleManager syncLifecycleManager;

  const SyncDeps({...});
}
```

### FeatureDeps (lines 237-263)
```dart
class FeatureDeps {
  final LocationRepository locationRepository;
  final ContractorRepository contractorRepository;
  final EquipmentRepository equipmentRepository;
  final PersonnelTypeRepository personnelTypeRepository;
  final BidItemRepository bidItemRepository;
  final EntryQuantityRepository entryQuantityRepository;
  final PhotoRepository photoRepository;
  final CalculationHistoryRepository calculationHistoryRepository;
  final TodoItemRepository todoItemRepository;
  final PdfService pdfService;
  final WeatherService weatherService;

  const FeatureDeps({...});
}
```

### AppDependencies (lines 267-355)
Key fields: `core`, `auth`, `project`, `entry`, `form`, `sync`, `feature`, `appRouter`
30+ convenience getters delegating to sub-deps (lines 288-335).
`supabaseClient` getter at line 337: `SupabaseConfig.isConfigured ? Supabase.instance.client : null`
`copyWith` at line 348 for driver mode photo service swap.

### AppInitializer.initialize() (lines 361-885)
Full source in `get_symbol_source` output. Key sections:
- **Lines 361-400**: PreferencesService, Aptabase analytics
- **Lines 401-410**: Debug logging, TestModeConfig, ConfigValidator
- **Lines 411-430**: SQLite FFI, DatabaseService, TrashRepository, SoftDeleteService
- **Lines 431-460**: Tesseract OCR init
- **Lines 461-480**: Supabase.initialize(), Firebase.initializeApp()
- **Lines 465-470**: ProjectLifecycleService (uses Supabase.instance.client)
- **Lines 471-530**: Local datasources + repositories
- **Lines 527-530**: ProjectRemoteDatasourceImpl (uses Supabase.instance.client)
- **Lines 548-550**: CompanyMembersRepository (uses Supabase.instance.client)
- **Lines 571-600**: Auth datasources (uses Supabase.instance.client x3)
- **Lines 601-645**: Auth use cases + AuthProvider
- **Lines 660-690**: App lifecycle (version gate, force reauth)
- **Lines 691-700**: AppConfigProvider, SyncProviders.initialize()
- **Lines 700-740**: BackgroundSyncHandler, auth listener
- **Lines 745-760**: Inactivity check, config check
- **Lines 751**: AppRouter construction (dead — overridden in entrypoints)
- **Lines 755-885**: Return AppDependencies + helper methods

### _NoOpProjectRemoteDatasource (lines 889-894)
```dart
class _NoOpProjectRemoteDatasource implements ProjectRemoteDatasource {
  @override
  Future<void> softDeleteProject(String projectId) async {}
}
```

---

## lib/core/router/app_router.dart (931 lines)

### Constants (lines 43-75)
- `_kOnboardingRoutes` (Set<String>): profile-setup, company-setup, pending-approval, account-status
- `_kNonRestorableRoutes` (Set<String>): 12 routes excluded from persistence

### AppRouter class (lines 77-745)
- Constructor (lines 90-96): takes `AuthProvider` required, `ConsentProvider?` optional
- `setInitialLocation` (line 98)
- `isRestorableRoute` static (line 105)
- `router` getter (line 108) — lazy `_buildRouter()`
- `_mpResultFromJobResult` static helper (line 113-144)
- `_buildRouter()` (lines 146-745): GoRouter with redirect + route table
  - Redirect matrix (lines 155-340)
  - Route table (lines 345-745): 42 routes

### ScaffoldWithNavBar class (lines 747-931)
- `_projectContextRoutes` constant: `{'/', '/calendar'}`
- `build()` (lines 756-920): Scaffold + Consumer2<SyncProvider, AppConfigProvider>
  - Sync error toast callback wiring (lines 775-790)
  - Banners: VersionBanner, StaleConfigWarning, stale sync, offline (lines 792-860)
  - Bottom nav with ExtractionBanner (lines 862-920)
- `_calculateSelectedIndex` (lines 922-927)
- `_onItemTapped` (lines 929-931)

---

## lib/main.dart (223 lines)

### `kAppLogDirOverride` constant (line 18)
### `_beforeSendSentry` (lines 28-64) — PII scrubbing for Sentry events
### `_beforeSendTransaction` (lines 68-74) — Consent gate for Sentry transactions
### `main()` (lines 81-118) — SentryFlutter.init wrapper
### `_runApp()` (lines 120-187) — Full init + consent + auth listener + router + runApp
### `ConstructionInspectorApp` (lines 189-223) — StatelessWidget with MultiProvider + MaterialApp.router

---

## lib/main_driver.dart (121 lines)

### `kAppLogDirOverride` constant (line 25)
### `main()` (lines 30-41) — runZonedGuarded (no Sentry)
### `_runApp()` (lines 43-121) — Init + PhotoService swap + DriverServer + consent + auth listener + router + runApp

---

## lib/features/sync/di/sync_providers.dart (291 lines)

### SyncProviders class (lines 32-291)
- `initialize()` (lines 38-240): 200+ lines mixing wiring + business logic
  - Lines 55-70: SyncOrchestrator creation + UserProfileSyncDatasource injection
  - Lines 72-90: Auth context wiring
  - Lines 91-187: **BUSINESS LOGIC** — enrollment/unenrollment (moves to SyncEnrollmentService)
  - Lines 189-198: **FCM init** (moves to FcmHandler)
  - Lines 200-235: **Lifecycle wiring** (moves to SyncLifecycleManager or SyncInitializer)
- `providers()` (lines 242-291): Pure wiring — provider list

---

## lib/features/settings/di/consent_support_factory.dart (55 lines)

### ConsentSupportResult (lines 16-24)
### createConsentAndSupportProviders (lines 29-55)
Full source in patterns/consent-factory.md.

---

## lib/core/driver/driver_server.dart

### DriverServer constructor (lines 69-77)
```dart
DriverServer({
  required this.testPhotoService,
  required PhotoRepository photoRepository,
  DocumentRepository? documentRepository,
  this.syncOrchestrator,
  this.databaseService,
  this.projectLifecycleService,
  this.port = const int.fromEnvironment('DRIVER_PORT', defaultValue: 4948),
})
```

### DriverServer.start (lines 89-98)
```dart
Future<void> start() async {
  if (kReleaseMode || kProfileMode) {
    throw StateError('DriverServer must not run in release or profile mode');
  }
  _server = await HttpServer.bind(InternetAddress.loopbackIPv4, port, shared: true);
  _server!.listen(_handleRequest);
}
```

---

## lib/driver_main.dart (9 lines)

```dart
void main() {
  enableFlutterDriverExtension();
  app.main();
}
```

---

## lib/test_harness.dart (135 lines)

### main() (lines 18-115) — Full harness bootstrap with screen/flow registry
### _readHarnessConfig() (lines 117-133) — JSON config reader
### _defaultHarnessConfig (line 135) — Default to ProjectDashboardScreen

---

## lib/test_harness/harness_providers.dart (324 lines)

### buildHarnessProviders (lines 94-324)
230 lines of datasource/repository/provider creation — mirrors AppInitializer but with stubs.

---

## lib/test_harness/ (6 files)

| File | Purpose | Imports |
|------|---------|---------|
| `stub_router.dart` | GoRouter stubs for single-screen + flow modes | go_router |
| `flow_registry.dart` | Multi-screen flow definitions | GoRoute, screen imports |
| `screen_registry.dart` | Screen name → widget builder map | Screen imports |
| `harness_seed_data.dart` | Default seed data for harness | DatabaseService |
| `stub_services.dart` | Stub implementations (100% dead code) | Service interfaces |
| `harness_providers.dart` | Full provider tree for harness | All provider/repo types |
