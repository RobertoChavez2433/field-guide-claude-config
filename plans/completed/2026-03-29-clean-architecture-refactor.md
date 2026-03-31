# Clean Architecture Refactor Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Decompose main.dart god function into feature-scoped DI modules and introduce Clean Architecture domain layer across all 17 features.
**Spec:** `.claude/specs/2026-03-29-clean-architecture-refactor-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-29-clean-architecture-refactor/`

**Architecture:** Top-down refactor: extract main.dart into feature modules first, then add domain layer (use cases + repository interfaces) feature-by-feature. Provider package retained, no DI framework.
**Tech Stack:** Flutter, Dart, Provider, SQLite (sqflite), Supabase
**Blast Radius:** ~100 new files, ~50 modified, ~30 tests updated, 0 deleted

---

# Phase 1: Feature Module Extraction (Mechanical)

> **Size**: M — ~15 files touched, zero logic changes.
> **Goal**: Move provider registrations from `main.dart` into per-feature provider files and compose them in `lib/core/di/app_providers.dart`. The `_runApp()` god function and `ConstructionInspectorApp` constructor shrink dramatically.

---

## Phase 1: Feature Module Extraction

### Sub-phase 1.1: Create per-feature provider files (Tier 4 features)

**Files:**
- Create: `lib/features/settings/di/settings_providers.dart`
- Create: `lib/features/auth/di/auth_providers.dart`
- Create: `lib/features/projects/di/projects_providers.dart`
- Create: `lib/features/locations/di/locations_providers.dart`
- Create: `lib/features/contractors/di/contractors_providers.dart`
- Create: `lib/features/entries/di/entries_providers.dart`
- Create: `lib/features/quantities/di/quantities_providers.dart`
- Create: `lib/features/photos/di/photos_providers.dart`
- Create: `lib/features/forms/di/forms_providers.dart`
- Create: `lib/features/calculator/di/calculator_providers.dart`
- Create: `lib/features/gallery/di/gallery_providers.dart`
- Create: `lib/features/todos/di/todos_providers.dart`
- Create: `lib/features/pdf/di/pdf_providers.dart`
- Create: `lib/features/weather/di/weather_providers.dart`
**Agent**: `general-purpose`

**NOTE:** Sync module is deferred to Phase 8. Only 14 feature provider files are created here (dashboard and toolbox have no providers, sync is extracted separately in Phase 8 with full init logic).

Each file exports a function that returns `List<SingleChildWidget>`. Parameters are the pre-initialized objects that the provider needs (repositories, services, etc.). No `context.read` inside these functions — dependencies are passed explicitly.

#### Step 1.1.1: Create `lib/features/settings/di/settings_providers.dart`

```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/shared/services/preferences_service.dart';
import 'package:construction_inspector/features/settings/presentation/providers/theme_provider.dart';

/// Settings feature providers (Tier 4).
/// WHY: PreferencesService is Tier 0 (async init) but its provider registration
/// is a simple .value wrapper — no creation logic needed.
List<SingleChildWidget> settingsProviders({
  required PreferencesService preferencesService,
}) {
  return [
    ChangeNotifierProvider.value(value: preferencesService),
    ChangeNotifierProvider(create: (_) => ThemeProvider()),
  ];
}
```

#### Step 1.1.2: Create `lib/features/auth/di/auth_providers.dart`

```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:construction_inspector/core/config/supabase_config.dart';
import 'package:construction_inspector/features/auth/services/auth_service.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/settings/presentation/providers/admin_provider.dart';

/// Auth feature providers (Tier 3-4).
/// WHY: AuthProvider and AppConfigProvider are hoisted (created in _runApp) because
/// they need async init and are referenced by other tiers. Registered as .value.
List<SingleChildWidget> authProviders({
  required AuthService authService,
  required AuthProvider authProvider,
  required AppConfigProvider appConfigProvider,
}) {
  return [
    ChangeNotifierProvider.value(value: authProvider),
    ChangeNotifierProvider.value(value: appConfigProvider),
    Provider<AuthService>.value(value: authService),
    ChangeNotifierProvider(
      create: (_) => AdminProvider(
        SupabaseConfig.isConfigured
            ? Supabase.instance.client
            : SupabaseClient('', ''),
      ),
    ),
  ];
}
```

#### Step 1.1.3: Create `lib/features/projects/di/projects_providers.dart`

This is the largest provider file because ProjectProvider has complex init logic (loadAndRestore, auth listener).

```dart
import 'dart:async';
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/projects/data/repositories/project_repository.dart';
import 'package:construction_inspector/features/projects/data/repositories/project_assignment_repository.dart';
import 'package:construction_inspector/features/projects/data/services/project_lifecycle_service.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_provider.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_settings_provider.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_sync_health_provider.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_import_runner.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_assignment_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';

/// Project feature providers (Tier 4).
/// WHY: ProjectProvider creation includes loadAndRestore logic and auth listener
/// wiring. This is a mechanical move — all logic is identical to main.dart lines 827-901.
List<SingleChildWidget> projectProviders({
  required ProjectRepository projectRepository,
  required ProjectAssignmentProvider projectAssignmentProvider,
  required ProjectSettingsProvider projectSettingsProvider,
  required ProjectSyncHealthProvider projectSyncHealthProvider,
  required ProjectImportRunner projectImportRunner,
  required ProjectLifecycleService projectLifecycleService,
  required AuthProvider authProvider,
  required AppConfigProvider appConfigProvider,
  required SyncOrchestrator syncOrchestrator,
  required DatabaseService dbService,
}) {
  return [
    ChangeNotifierProvider.value(value: projectSettingsProvider),
    ChangeNotifierProvider(
      create: (_) {
        // FROM SPEC (BUG-009): Wire role check for project management defense-in-depth.
        final provider = ProjectProvider(
          projectRepository,
          canManageProjects: () => authProvider.canManageProjects,
        );
        // Link settings provider for persisting project selection
        provider.setSettingsProvider(projectSettingsProvider);

        // Helper: load projects by company and restore the last-selected project.
        Future<void> loadAndRestore(String? companyId) async {
          await provider.loadProjectsByCompany(companyId);
          if (projectSettingsProvider.autoLoadEnabled &&
              projectSettingsProvider.lastProjectId != null) {
            provider.setRestoringProject(true);
            final project = provider.getProjectById(
              projectSettingsProvider.lastProjectId!,
            );
            if (project != null) {
              provider.setSelectedProject(project);
            } else {
              projectSettingsProvider.setLastProjectId(null);
            }
            provider.setRestoringProject(false);
          }
          provider.setInitializing(false);
        }

        final initialCompanyId = authProvider.userProfile?.companyId;
        loadAndRestore(initialCompanyId);

        String? lastLoadedCompanyId = initialCompanyId;
        void onAuthChanged() {
          final newCompanyId = authProvider.userProfile?.companyId;
          final isAuth = authProvider.isAuthenticated;
          // FIX T95/T96: Reset lastLoadedCompanyId on sign-out
          if (!isAuth) {
            lastLoadedCompanyId = null;
            provider.clearScreenCache();
          }
          if (newCompanyId != null && newCompanyId != lastLoadedCompanyId) {
            lastLoadedCompanyId = newCompanyId;
            provider.setInitializing(true);
            loadAndRestore(newCompanyId);
            // FIX T95/T96: Trigger sync on login
            unawaited(syncOrchestrator.syncLocalAgencyProjects());
          }
          if (isAuth) {
            unawaited(appConfigProvider.checkConfig());
          }
        }
        authProvider.addListener(onAuthChanged);

        return provider;
      },
    ),
    // FIX 1 (HIGH): ProjectAssignmentProvider registered AFTER ProjectProvider.
    // FIX 2 (HIGH): Hoisted and registered with .value so clear() is called on sign-out.
    ChangeNotifierProvider.value(value: projectAssignmentProvider),
    Provider<ProjectLifecycleService>.value(value: projectLifecycleService),
    ChangeNotifierProvider.value(value: projectSyncHealthProvider),
    ChangeNotifierProvider.value(value: projectImportRunner),
  ];
}
```

#### Step 1.1.4: Create `lib/features/locations/di/locations_providers.dart`

```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/features/locations/data/repositories/location_repository.dart';
import 'package:construction_inspector/features/locations/presentation/providers/location_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';

/// Location feature providers (Tier 4).
List<SingleChildWidget> locationProviders({
  required LocationRepository locationRepository,
  required AuthProvider authProvider,
}) {
  return [
    ChangeNotifierProvider(
      create: (_) {
        final p = LocationProvider(locationRepository);
        p.canWrite = () => authProvider.canEditFieldData;
        return p;
      },
    ),
  ];
}
```

#### Step 1.1.5: Create `lib/features/contractors/di/contractors_providers.dart`

```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/features/contractors/data/repositories/contractor_repository.dart';
import 'package:construction_inspector/features/contractors/data/repositories/equipment_repository.dart';
import 'package:construction_inspector/features/contractors/data/repositories/personnel_type_repository.dart';
import 'package:construction_inspector/features/contractors/presentation/providers/contractor_provider.dart';
import 'package:construction_inspector/features/contractors/presentation/providers/equipment_provider.dart';
import 'package:construction_inspector/features/contractors/presentation/providers/personnel_type_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';

/// Contractor feature providers (Tier 4).
List<SingleChildWidget> contractorProviders({
  required ContractorRepository contractorRepository,
  required EquipmentRepository equipmentRepository,
  required PersonnelTypeRepository personnelTypeRepository,
  required AuthProvider authProvider,
}) {
  return [
    ChangeNotifierProvider(
      create: (_) {
        final p = ContractorProvider(contractorRepository);
        p.canWrite = () => authProvider.canEditFieldData;
        return p;
      },
    ),
    ChangeNotifierProvider(
      create: (_) {
        final p = EquipmentProvider(equipmentRepository);
        p.canWrite = () => authProvider.canEditFieldData;
        return p;
      },
    ),
    ChangeNotifierProvider(
      create: (_) {
        final p = PersonnelTypeProvider(personnelTypeRepository);
        p.canWrite = () => authProvider.canEditFieldData;
        return p;
      },
    ),
  ];
}
```

#### Step 1.1.6: Create `lib/features/entries/di/entries_providers.dart`

```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/features/entries/data/repositories/daily_entry_repository.dart';
import 'package:construction_inspector/features/entries/data/repositories/entry_export_repository.dart';
import 'package:construction_inspector/features/entries/data/repositories/document_repository.dart';
import 'package:construction_inspector/features/entries/presentation/providers/daily_entry_provider.dart';
import 'package:construction_inspector/features/entries/presentation/providers/calendar_format_provider.dart';
import 'package:construction_inspector/features/entries/presentation/providers/entry_export_provider.dart';
import 'package:construction_inspector/features/forms/data/repositories/form_response_repository.dart';
import 'package:construction_inspector/features/forms/presentation/providers/form_export_provider.dart';
import 'package:construction_inspector/features/forms/presentation/providers/document_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/services/document_service.dart';

/// Entry feature providers (Tier 4).
/// WHY: EntryExportProvider depends on FormExportProvider via context.read —
/// it MUST be registered AFTER forms_providers in the MultiProvider list.
/// DocumentProvider also lives here because it's entry-scoped (documents attach to entries).
List<SingleChildWidget> entryProviders({
  required DailyEntryRepository dailyEntryRepository,
  required EntryExportRepository entryExportRepository,
  required FormResponseRepository formResponseRepository,
  required DocumentRepository documentRepository,
  required DocumentService documentService,
  required AuthProvider authProvider,
}) {
  return [
    ChangeNotifierProvider(
      create: (_) {
        final p = DailyEntryProvider(dailyEntryRepository);
        p.canWrite = () => authProvider.canEditFieldData;
        return p;
      },
    ),
    ChangeNotifierProvider(create: (_) => CalendarFormatProvider()),
    // WHY: EntryExportProvider uses context.read<FormExportProvider>() — the forms
    // module MUST be registered before this module in app_providers.dart.
    ChangeNotifierProvider(
      create: (context) => EntryExportProvider(
        entryRepository: dailyEntryRepository,
        entryExportRepository: entryExportRepository,
        formResponseRepository: formResponseRepository,
        formExportProvider: context.read<FormExportProvider>(),
      ),
    ),
    ChangeNotifierProvider(
      create: (_) => DocumentProvider(
        repository: formResponseRepository,
        documentRepository: documentRepository,
        documentService: documentService,
      ),
    ),
  ];
}
```

#### Step 1.1.7: Create `lib/features/quantities/di/quantities_providers.dart`

```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/features/quantities/data/repositories/bid_item_repository.dart';
import 'package:construction_inspector/features/quantities/data/repositories/entry_quantity_repository.dart';
import 'package:construction_inspector/features/quantities/presentation/providers/bid_item_provider.dart';
import 'package:construction_inspector/features/quantities/presentation/providers/entry_quantity_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';

/// Quantity feature providers (Tier 4).
List<SingleChildWidget> quantityProviders({
  required BidItemRepository bidItemRepository,
  required EntryQuantityRepository entryQuantityRepository,
  required AuthProvider authProvider,
}) {
  return [
    ChangeNotifierProvider(
      create: (_) {
        final p = BidItemProvider(bidItemRepository);
        p.canWrite = () => authProvider.canEditFieldData;
        return p;
      },
    ),
    ChangeNotifierProvider(
      create: (_) => EntryQuantityProvider(entryQuantityRepository),
    ),
  ];
}
```

#### Step 1.1.8: Create `lib/features/photos/di/photos_providers.dart`

```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/features/photos/data/repositories/photo_repository.dart';
import 'package:construction_inspector/features/photos/presentation/providers/photo_provider.dart';
import 'package:construction_inspector/services/photo_service.dart';
import 'package:construction_inspector/services/image_service.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';

/// Photo feature providers (Tier 4).
List<SingleChildWidget> photoProviders({
  required PhotoRepository photoRepository,
  required PhotoService photoService,
  required ImageService imageService,
  required AuthProvider authProvider,
}) {
  return [
    ChangeNotifierProvider(
      create: (_) => PhotoProvider(
        photoRepository,
        canWrite: () => authProvider.canEditFieldData,
      ),
    ),
    Provider<PhotoService>.value(value: photoService),
    Provider<ImageService>.value(value: imageService),
  ];
}
```

#### Step 1.1.9: Create `lib/features/forms/di/forms_providers.dart`

```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/features/forms/forms.dart';
import 'package:construction_inspector/features/forms/data/registries/form_calculator_registry.dart';
import 'package:construction_inspector/features/forms/data/repositories/form_export_repository.dart';
import 'package:construction_inspector/features/forms/presentation/providers/form_export_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';

/// Form feature providers (Tier 4).
/// WHY: FormExportProvider MUST be registered before EntryExportProvider (entries module)
/// because EntryExportProvider uses context.read<FormExportProvider>().
List<SingleChildWidget> formProviders({
  required InspectorFormRepository inspectorFormRepository,
  required FormResponseRepository formResponseRepository,
  required FormExportRepository formExportRepository,
  required FormPdfService formPdfService,
  required AuthProvider authProvider,
}) {
  return [
    ChangeNotifierProvider(
      create: (_) {
        final p = InspectorFormProvider(
          inspectorFormRepository,
          formResponseRepository,
          FormCalculatorRegistry.instance,
        );
        p.canWrite = () => authProvider.canEditFieldData;
        return p;
      },
    ),
    Provider<FormPdfService>.value(value: formPdfService),
    // WHY: Must be registered before entries module (EntryExportProvider reads this).
    ChangeNotifierProvider(
      create: (_) => FormExportProvider(
        repository: formResponseRepository,
        formExportRepository: formExportRepository,
        pdfService: formPdfService,
      ),
    ),
  ];
}
```

#### Step 1.1.10: Create `lib/features/calculator/di/calculator_providers.dart`

```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/features/calculator/calculator.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';

/// Calculator feature providers (Tier 4).
List<SingleChildWidget> calculatorProviders({
  required CalculationHistoryLocalDatasource calculationHistoryDatasource,
  required AuthProvider authProvider,
}) {
  return [
    ChangeNotifierProvider(
      create: (_) {
        final p = CalculatorProvider(calculationHistoryDatasource);
        p.canWrite = () => authProvider.canEditFieldData;
        return p;
      },
    ),
  ];
}
```

#### Step 1.1.11: Create `lib/features/gallery/di/gallery_providers.dart`

```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/features/photos/data/repositories/photo_repository.dart';
import 'package:construction_inspector/features/entries/data/repositories/daily_entry_repository.dart';
import 'package:construction_inspector/features/gallery/gallery.dart';

/// Gallery feature providers (Tier 4).
/// WHY: GalleryProvider has cross-feature deps (photo + entry repositories).
/// This is acceptable — gallery is a read-only aggregation view.
List<SingleChildWidget> galleryProviders({
  required PhotoRepository photoRepository,
  required DailyEntryRepository dailyEntryRepository,
}) {
  return [
    ChangeNotifierProvider(
      create: (_) => GalleryProvider(photoRepository, dailyEntryRepository),
    ),
  ];
}
```

#### Step 1.1.12: Create `lib/features/todos/di/todos_providers.dart`

```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/features/todos/todos.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';

/// Todo feature providers (Tier 4).
List<SingleChildWidget> todoProviders({
  required TodoItemLocalDatasource todoItemDatasource,
  required AuthProvider authProvider,
}) {
  return [
    ChangeNotifierProvider(
      create: (_) {
        final p = TodoProvider(todoItemDatasource);
        p.canWrite = () => authProvider.canEditFieldData;
        return p;
      },
    ),
  ];
}
```

#### Step 1.1.13: Create `lib/features/pdf/di/pdf_providers.dart`

```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/features/pdf/services/services.dart';
import 'package:construction_inspector/features/pdf/services/extraction/runner/extraction_job_runner.dart';

/// PDF feature providers (Tier 4).
List<SingleChildWidget> pdfProviders({
  required PdfService pdfService,
}) {
  return [
    Provider<PdfService>.value(value: pdfService),
    ChangeNotifierProvider(create: (_) => ExtractionJobRunner()),
  ];
}
```

#### Step 1.1.14: Create `lib/features/weather/di/weather_providers.dart`

```dart
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/features/weather/services/weather_service.dart';

/// Weather feature providers (Tier 4).
List<SingleChildWidget> weatherProviders({
  required WeatherService weatherService,
}) {
  return [
    Provider<WeatherService>.value(value: weatherService),
  ];
}
```

#### ~~Step 1.1.15: Create sync_providers.dart~~ **SKIPPED — deferred to Phase 8**

> Sync provider registration stays in `main.dart` until Phase 8 extracts it with full init logic (orchestrator creation, lifecycle manager, FCM wiring, 100-line onPullComplete lambda). Creating a partial sync_providers.dart here would conflict with Phase 8's complete extraction.

---

### Sub-phase 1.2: Create `app_providers.dart` composition root

**Files:**
- Create: `lib/core/di/app_providers.dart`

**Agent**: `backend-data-layer-agent`

#### Step 1.2.1: Create `lib/core/di/app_providers.dart`

This file composes all per-feature provider lists in tier order. It takes the same hoisted objects that `_runApp()` creates and spreads the feature lists into a single flat `List<SingleChildWidget>`.

```dart
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/shared/services/preferences_service.dart';
import 'package:construction_inspector/features/auth/services/auth_service.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/projects/data/repositories/project_repository.dart';
import 'package:construction_inspector/features/projects/data/repositories/project_assignment_repository.dart';
import 'package:construction_inspector/features/projects/data/services/project_lifecycle_service.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_settings_provider.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_sync_health_provider.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_import_runner.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_assignment_provider.dart';
import 'package:construction_inspector/features/locations/data/repositories/location_repository.dart';
import 'package:construction_inspector/features/contractors/data/repositories/contractor_repository.dart';
import 'package:construction_inspector/features/contractors/data/repositories/equipment_repository.dart';
import 'package:construction_inspector/features/contractors/data/repositories/personnel_type_repository.dart';
import 'package:construction_inspector/features/entries/data/repositories/daily_entry_repository.dart';
import 'package:construction_inspector/features/entries/data/repositories/entry_export_repository.dart';
import 'package:construction_inspector/features/entries/data/repositories/document_repository.dart';
import 'package:construction_inspector/features/quantities/data/repositories/bid_item_repository.dart';
import 'package:construction_inspector/features/quantities/data/repositories/entry_quantity_repository.dart';
import 'package:construction_inspector/features/photos/data/repositories/photo_repository.dart';
import 'package:construction_inspector/features/forms/forms.dart';
import 'package:construction_inspector/features/forms/data/repositories/form_export_repository.dart';
import 'package:construction_inspector/features/calculator/calculator.dart';
import 'package:construction_inspector/features/todos/todos.dart';
import 'package:construction_inspector/features/pdf/services/services.dart';
import 'package:construction_inspector/features/weather/services/weather_service.dart';
import 'package:construction_inspector/services/photo_service.dart';
import 'package:construction_inspector/services/image_service.dart';
import 'package:construction_inspector/services/document_service.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/features/sync/application/sync_lifecycle_manager.dart';

// Per-feature provider files
import 'package:construction_inspector/features/settings/di/settings_providers.dart';
import 'package:construction_inspector/features/auth/di/auth_providers.dart';
import 'package:construction_inspector/features/projects/di/projects_providers.dart';
import 'package:construction_inspector/features/locations/di/locations_providers.dart';
import 'package:construction_inspector/features/contractors/di/contractors_providers.dart';
import 'package:construction_inspector/features/entries/di/entries_providers.dart';
import 'package:construction_inspector/features/quantities/di/quantities_providers.dart';
import 'package:construction_inspector/features/photos/di/photos_providers.dart';
import 'package:construction_inspector/features/forms/di/forms_providers.dart';
import 'package:construction_inspector/features/calculator/di/calculator_providers.dart';
import 'package:construction_inspector/features/gallery/di/gallery_providers.dart';
import 'package:construction_inspector/features/todos/di/todos_providers.dart';
import 'package:construction_inspector/features/pdf/di/pdf_providers.dart';
import 'package:construction_inspector/features/weather/di/weather_providers.dart';
// Sync providers: registered inline until Phase 8 extracts them
import 'package:provider/provider.dart';
import 'package:construction_inspector/features/sync/data/sync_registry.dart';
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';

/// Composes all feature provider lists in tier order.
///
/// TIER ORDER (must be preserved):
/// - Tier 0: Settings (PreferencesService — async init, .value wrapper)
/// - Tier 3: Auth (AuthProvider, AppConfigProvider — hoisted, .value wrappers)
/// - Tier 4: Feature providers (depend on auth + repositories)
///   - projects → locations → contractors → quantities → entries
///   - photos → forms → entries (forms before entries: EntryExportProvider reads FormExportProvider)
///   - calculator → gallery → todos → pdf → weather
/// - Tier 5: Sync (depends on auth + feature providers)
///
/// WHY: Tier 1 (datasources) and Tier 2 (repositories) are created in _runApp()
/// and passed as parameters — they don't appear as providers in the widget tree.
List<SingleChildWidget> buildAppProviders({
  // Tier 0
  required PreferencesService preferencesService,
  required DatabaseService dbService,
  // Tier 3
  required AuthService authService,
  required AuthProvider authProvider,
  required AppConfigProvider appConfigProvider,
  // Tier 4 dependencies (repositories + services created in _runApp)
  required ProjectRepository projectRepository,
  required ProjectAssignmentProvider projectAssignmentProvider,
  required ProjectSettingsProvider projectSettingsProvider,
  required ProjectSyncHealthProvider projectSyncHealthProvider,
  required ProjectImportRunner projectImportRunner,
  required ProjectLifecycleService projectLifecycleService,
  required LocationRepository locationRepository,
  required ContractorRepository contractorRepository,
  required EquipmentRepository equipmentRepository,
  required PersonnelTypeRepository personnelTypeRepository,
  required DailyEntryRepository dailyEntryRepository,
  required EntryExportRepository entryExportRepository,
  required DocumentRepository documentRepository,
  required DocumentService documentService,
  required BidItemRepository bidItemRepository,
  required EntryQuantityRepository entryQuantityRepository,
  required PhotoRepository photoRepository,
  required PhotoService photoService,
  required ImageService imageService,
  required InspectorFormRepository inspectorFormRepository,
  required FormResponseRepository formResponseRepository,
  required FormExportRepository formExportRepository,
  required FormPdfService formPdfService,
  required CalculationHistoryLocalDatasource calculationHistoryDatasource,
  required TodoItemLocalDatasource todoItemDatasource,
  required PdfService pdfService,
  required WeatherService weatherService,
  // Tier 5
  required SyncOrchestrator syncOrchestrator,
  required SyncLifecycleManager syncLifecycleManager,
}) {
  return [
    // ── Tier 0: Settings ──
    ...settingsProviders(preferencesService: preferencesService),

    // ── Tier 3: Auth ──
    ...authProviders(
      authService: authService,
      authProvider: authProvider,
      appConfigProvider: appConfigProvider,
    ),

    // ── Tier 4: Feature providers (order matters for context.read deps) ──
    ...projectProviders(
      projectRepository: projectRepository,
      projectAssignmentProvider: projectAssignmentProvider,
      projectSettingsProvider: projectSettingsProvider,
      projectSyncHealthProvider: projectSyncHealthProvider,
      projectImportRunner: projectImportRunner,
      projectLifecycleService: projectLifecycleService,
      authProvider: authProvider,
      appConfigProvider: appConfigProvider,
      syncOrchestrator: syncOrchestrator,
      dbService: dbService,
    ),
    ...locationProviders(
      locationRepository: locationRepository,
      authProvider: authProvider,
    ),
    ...contractorProviders(
      contractorRepository: contractorRepository,
      equipmentRepository: equipmentRepository,
      personnelTypeRepository: personnelTypeRepository,
      authProvider: authProvider,
    ),
    ...quantityProviders(
      bidItemRepository: bidItemRepository,
      entryQuantityRepository: entryQuantityRepository,
      authProvider: authProvider,
    ),
    ...photoProviders(
      photoRepository: photoRepository,
      photoService: photoService,
      imageService: imageService,
      authProvider: authProvider,
    ),
    // WHY: forms MUST come before entries — EntryExportProvider reads FormExportProvider.
    ...formProviders(
      inspectorFormRepository: inspectorFormRepository,
      formResponseRepository: formResponseRepository,
      formExportRepository: formExportRepository,
      formPdfService: formPdfService,
      authProvider: authProvider,
    ),
    ...entryProviders(
      dailyEntryRepository: dailyEntryRepository,
      entryExportRepository: entryExportRepository,
      formResponseRepository: formResponseRepository,
      documentRepository: documentRepository,
      documentService: documentService,
      authProvider: authProvider,
    ),
    ...calculatorProviders(
      calculationHistoryDatasource: calculationHistoryDatasource,
      authProvider: authProvider,
    ),
    ...galleryProviders(
      photoRepository: photoRepository,
      dailyEntryRepository: dailyEntryRepository,
    ),
    ...todoProviders(
      todoItemDatasource: todoItemDatasource,
      authProvider: authProvider,
    ),
    ...pdfProviders(pdfService: pdfService),
    ...weatherProviders(weatherService: weatherService),

    // ── Tier 5: Sync (inline until Phase 8 extracts into sync_providers.dart) ──
    Provider<SyncRegistry>.value(value: SyncRegistry.instance),
    Provider<SyncOrchestrator>.value(value: syncOrchestrator),
    ChangeNotifierProvider(
      create: (_) => SyncProvider(syncOrchestrator: syncOrchestrator),
    ),
  ];
}
```

---

### Sub-phase 1.3: Rewire `ConstructionInspectorApp` to use `buildAppProviders()`

**Files:**
- Modify: `lib/main.dart:557-596` (runApp call)
- Modify: `lib/main.dart:733-1069` (ConstructionInspectorApp class)

**Agent**: `general-purpose`

#### Step 1.3.1: Slim down the `ConstructionInspectorApp` constructor

Replace the 37-parameter constructor with a single `providers` parameter and an `appRouter` parameter. The class no longer holds references to repositories or services — those are in the provider list.

New constructor (replaces lines 733-808):

```dart
class ConstructionInspectorApp extends StatelessWidget {
  final List<SingleChildWidget> providers;
  final AppRouter appRouter;

  const ConstructionInspectorApp({
    super.key,
    required this.providers,
    required this.appRouter,
  });
```

#### Step 1.3.2: Replace the `build()` method's inline provider list

Replace the 38-entry `MultiProvider(providers: [...])` block (lines 812-1056) with:

```dart
  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: providers,
      child: Consumer<ThemeProvider>(
        builder: (context, themeProvider, _) {
          return MaterialApp.router(
            title: 'Field Guide',
            debugShowCheckedModeBanner: false,
            theme: themeProvider.currentTheme,
            routerConfig: appRouter.router,
          );
        },
      ),
    );
  }
}
```

#### Step 1.3.3: Update the `runApp()` call in `_runApp()`

Replace lines 557-595 with:

```dart
  runApp(
    ConstructionInspectorApp(
      providers: buildAppProviders(
        preferencesService: preferencesService,
        dbService: dbService,
        authService: authService,
        authProvider: authProvider,
        appConfigProvider: appConfigProvider,
        projectRepository: projectRepository,
        projectAssignmentProvider: projectAssignmentProvider,
        projectSettingsProvider: projectSettingsProvider,
        projectSyncHealthProvider: projectSyncHealthProvider,
        projectImportRunner: projectImportRunner,
        projectLifecycleService: projectLifecycleService,
        locationRepository: locationRepository,
        contractorRepository: contractorRepository,
        equipmentRepository: equipmentRepository,
        personnelTypeRepository: personnelTypeRepository,
        dailyEntryRepository: dailyEntryRepository,
        entryExportRepository: entryExportRepository,
        documentRepository: documentRepository,
        documentService: documentService,
        bidItemRepository: bidItemRepository,
        entryQuantityRepository: entryQuantityRepository,
        photoRepository: photoRepository,
        photoService: photoService,
        imageService: imageService,
        inspectorFormRepository: inspectorFormRepository,
        formResponseRepository: formResponseRepository,
        formExportRepository: formExportRepository,
        formPdfService: formPdfService,
        calculationHistoryDatasource: calculationHistoryDatasource,
        todoItemDatasource: todoItemDatasource,
        pdfService: pdfService,
        weatherService: weatherService,
        syncOrchestrator: syncOrchestrator,
        syncLifecycleManager: syncLifecycleManager,
      ),
      appRouter: appRouter,
    ),
  );
```

#### Step 1.3.4: Add import for `buildAppProviders`

Add to the imports section of `main.dart`:

```dart
import 'package:construction_inspector/core/di/app_providers.dart';
```

#### Step 1.3.5: Clean up unused imports from `main.dart`

Remove all provider-specific imports that are no longer directly referenced in `main.dart`. These include:
- `ThemeProvider` import (line 77)
- `AdminProvider` import (line 78)
- `CalendarFormatProvider` import (line 83)
- `GalleryProvider` import (line 84)
- `SyncRegistry` import (line 80)
- `SyncProvider` import (line 81)
- All other provider imports that were only used in the `ConstructionInspectorApp.build()` method

Keep imports that are still used in `_runApp()` (e.g., `AuthProvider`, `AppConfigProvider`, `SyncOrchestrator`, etc.).

#### Step 1.3.6: Move `seedBuiltinForms()` and `_registerFormScreens()` to forms module

Move `seedBuiltinForms()` (lines 651-675) and `_registerFormScreens()` (lines 602-644) from `main.dart` into a new file:

**Create**: `lib/features/forms/di/forms_init.dart`

```dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/forms/forms.dart';
import 'package:construction_inspector/features/forms/data/registries/builtin_forms.dart';
import 'package:construction_inspector/features/forms/data/registries/form_screen_registry.dart';
import 'package:construction_inspector/features/forms/data/registries/form_quick_action_registry.dart';

/// Seeds builtin forms if not already present and registers their capabilities.
/// WHY: Registry-driven seeding checks each form by ID instead of using
/// hasBuiltinForms() which only checks "any exist". This is additive —
/// new builtin forms get seeded even if older ones already exist.
/// Public so main_driver.dart can call it too (BUG-S04 fix).
Future<void> seedBuiltinForms(InspectorFormRepository formRepository) async {
  for (final config in builtinForms) {
    try {
      final existingResult = await formRepository.getFormById(config.id);
      if (existingResult.isSuccess && existingResult.data != null) {
        config.registerCapabilities();
        continue;
      }
      final result = await formRepository.createForm(config.toInspectorForm());
      if (result.isSuccess) {
        config.registerCapabilities();
      } else {
        Logger.db('Failed to seed ${config.id}: ${result.error}');
      }
    } catch (e) {
      Logger.db('seedBuiltinForms threw for ${config.id}: $e');
    }
  }
}

/// Register form-specific screen builders and quick actions in the UI layer.
/// WHY: Screen/action registration uses Flutter widgets/navigation, must happen in UI layer.
/// Called once after seedBuiltinForms during app startup.
void registerFormScreens() {
  FormScreenRegistry.instance.register(
    'mdot_0582b',
    ({required String formId, required String responseId, required String projectId}) {
      return MdotHubScreen(responseId: responseId);
    },
  );

  FormQuickActionRegistry.instance.register('mdot_0582b', [
    FormQuickAction(
      icon: Icons.add,
      label: '+ Test',
      execute: (context, response) {
        context.pushNamed(
          'quick-test-entry',
          pathParameters: {'responseId': response.id},
        );
      },
    ),
    FormQuickAction(
      icon: Icons.science_outlined,
      label: '+ Proctor',
      execute: (context, response) {
        context.pushNamed(
          'proctor-entry',
          pathParameters: {'responseId': response.id},
        );
      },
    ),
    FormQuickAction(
      icon: Icons.scale_outlined,
      label: '+ Weights',
      execute: (context, response) {
        context.pushNamed(
          'weights-entry',
          pathParameters: {'responseId': response.id},
        );
      },
    ),
  ]);
}
```

Then update `main.dart` to import and call `registerFormScreens()` (renamed from `_registerFormScreens()`) and `seedBuiltinForms()` from the new location:

```dart
import 'package:construction_inspector/features/forms/di/forms_init.dart';
```

And replace the calls at lines 269-273:
```dart
  await seedBuiltinForms(inspectorFormRepository);
  registerFormScreens();
```

Remove the old function bodies from `main.dart` (lines 599-675).

**IMPORTANT**: Check if `main_driver.dart` imports `seedBuiltinForms` from `main.dart`. If so, update that import to point to `forms_init.dart`.

---

### Sub-phase 1.4: Extract `_runApp()` body into `AppInitializer`

**Files:**
- Create: `lib/core/di/app_initializer.dart`
- Modify: `lib/main.dart`

**Agent**: `backend-data-layer-agent`

**Goal:** Move ALL datasource creation, repository creation, service creation, and auth wiring out of `_runApp()` into a dedicated `AppInitializer` class. This is what actually gets `main.dart` to ~50 lines.

#### Step 1.4.1: Create `lib/core/di/app_initializer.dart`

Create an `AppInitializer` class with a static `Future<AppDependencies> initialize()` method that:

1. Creates `DatabaseService` and initializes it
2. Creates all datasources (local + remote)
3. Creates all repositories
4. Creates all services (`AuthService`, `ProjectLifecycleService`, etc.)
5. Creates `AuthProvider`, `AppConfigProvider`, and any other providers that need async init
6. Runs sync initialization (orchestrator, lifecycle manager, FCM wiring) — or delegates to `SyncProviders.initialize()` if Phase 8 runs first
7. Returns all created objects in an `AppDependencies` record or class

```dart
/// Encapsulates all app initialization that was previously in main.dart _runApp().
/// Returns a dependency container that _runApp() passes to buildAppProviders().
class AppInitializer {
  /// Initialize all app dependencies. Called once from _runApp().
  static Future<AppDependencies> initialize() async {
    // All datasource, repository, service, and provider creation
    // moves here from _runApp() body
    ...
    return AppDependencies(
      dbService: dbService,
      authProvider: authProvider,
      appConfigProvider: appConfigProvider,
      // ... all other deps needed by buildAppProviders()
      router: appRouter,
    );
  }
}

/// Container for all initialized dependencies.
/// Passed to buildAppProviders() and ConstructionInspectorApp.
class AppDependencies {
  final DatabaseService dbService;
  final AuthProvider authProvider;
  final AppConfigProvider appConfigProvider;
  // ... all other fields
  final GoRouter router;

  const AppDependencies({
    required this.dbService,
    required this.authProvider,
    required this.appConfigProvider,
    // ...
    required this.router,
  });
}
```

#### Step 1.4.2: Slim down `_runApp()` in `main.dart`

Replace the entire `_runApp()` body with:

```dart
Future<void> _runApp() async {
  final deps = await AppInitializer.initialize();
  runApp(
    MultiProvider(
      providers: buildAppProviders(deps),
      child: ConstructionInspectorApp(router: deps.router),
    ),
  );
}
```

#### Step 1.4.3: Update `buildAppProviders()` signature

Update `lib/core/di/app_providers.dart` to accept `AppDependencies` instead of individual parameters:

```dart
List<SingleChildWidget> buildAppProviders(AppDependencies deps) {
  return [
    ...settingsProviders(preferencesService: deps.preferencesService),
    ...authProviders(authService: deps.authService, authProvider: deps.authProvider, ...),
    // ... spread all feature providers using deps fields
  ];
}
```

**IMPORTANT:** This is a mechanical code-motion refactor. Zero logic changes. Every line from `_runApp()` moves character-for-character into `AppInitializer.initialize()`.

**Verification:** `main.dart` should be ~50 lines after this step (imports + main() + _runApp() + ConstructionInspectorApp minimal class).

---

### Sub-phase 1.5: Update `main_driver.dart`

**Files:**
- Modify: `lib/core/driver/main_driver.dart`

**Agent**: `general-purpose`

#### Step 1.5.1: Update `seedBuiltinForms` import

If `main_driver.dart` imports `seedBuiltinForms` from `package:construction_inspector/main.dart`, change it to:

```dart
import 'package:construction_inspector/features/forms/di/forms_init.dart';
```

#### Step 1.5.2: Update `main_driver.dart` to use new `ConstructionInspectorApp` constructor

`main_driver.dart` has its own `_runApp()` that constructs `ConstructionInspectorApp` with the full 37-param constructor. After Phase 1.3 changes the constructor to `({required providers, required appRouter})`, `main_driver.dart` will not compile.

**What to do:**
1. Import `AppInitializer` and `buildAppProviders` into `main_driver.dart`.
2. Replace the driver's `_runApp()` body to use the same `AppInitializer` + `buildAppProviders()` pattern as `main.dart`.
3. After calling `buildAppProviders()`, append the driver-specific test harness providers (e.g., `DriverTestHarnessProvider`, `HttpDriverServer`) to the provider list before passing to `ConstructionInspectorApp`.
4. Construct `ConstructionInspectorApp` with the new 2-param constructor: `ConstructionInspectorApp(providers: [...allProviders, ...driverProviders], appRouter: appRouter)`.

**IMPORTANT:** Preserve all driver-specific wiring (test harness, HTTP driver server, seed data). Only the `ConstructionInspectorApp` construction pattern changes.

---

### Sub-phase 1.6: Verification

**Agent**: `general-purpose`

#### Step 1.5.1: Run static analysis

```
pwsh -Command "flutter analyze"
```

Expected: 0 errors. Warnings about unused imports are acceptable and will be cleaned in the next step.

#### Step 1.5.2: Fix any unused import warnings

Remove any imports flagged as unused by the analyzer.

#### Step 1.5.3: Re-run static analysis

```
pwsh -Command "flutter analyze"
```

Expected: 0 errors, 0 new warnings.

#### Step 1.5.4: Run tests

```
pwsh -Command "flutter test"
```

Expected: Same pass/fail count as before this phase. This is a mechanical move — no logic changed.

#### Step 1.5.5: Verify provider count

Manual check: count the providers in `buildAppProviders()` return list. The total spread entries must equal the 38 providers from the original `MultiProvider` in `ConstructionInspectorApp.build()`. Use grep to count:

```
Grep for "Provider" in app_providers.dart and count spread lists.
Grep for "Provider" in original main.dart MultiProvider block.
```

---

## Summary of Changes

| Metric | Before | After |
|--------|--------|-------|
| `main.dart` lines | ~1,069 | ~50 (imports + main + _runApp + minimal ConstructionInspectorApp) |
| `ConstructionInspectorApp` constructor params | 37 | 1 (`router`) |
| Provider registration location | Inline in `build()` | 14 per-feature `di/` files (sync deferred to Phase 8) |
| Composition root | None | `lib/core/di/app_providers.dart` |
| Initialization logic | In `_runApp()` god function | In `lib/core/di/app_initializer.dart` |
| `_runApp()` body | ~700 lines of init logic | 3 lines: initialize + runApp |
| `seedBuiltinForms` + `_registerFormScreens` | In `main.dart` | In `lib/features/forms/di/forms_init.dart` |

## Files Created (17)
1. `lib/features/settings/di/settings_providers.dart`
2. `lib/features/auth/di/auth_providers.dart`
3. `lib/features/projects/di/projects_providers.dart`
4. `lib/features/locations/di/locations_providers.dart`
5. `lib/features/contractors/di/contractors_providers.dart`
6. `lib/features/entries/di/entries_providers.dart`
7. `lib/features/quantities/di/quantities_providers.dart`
8. `lib/features/photos/di/photos_providers.dart`
9. `lib/features/forms/di/forms_providers.dart`
10. `lib/features/calculator/di/calculator_providers.dart`
11. `lib/features/gallery/di/gallery_providers.dart`
12. `lib/features/todos/di/todos_providers.dart`
13. `lib/features/pdf/di/pdf_providers.dart`
14. `lib/features/weather/di/weather_providers.dart`
15. `lib/core/di/app_providers.dart`
16. `lib/core/di/app_initializer.dart`
17. `lib/features/forms/di/forms_init.dart`

**NOTE:** `lib/features/sync/di/sync_providers.dart` is created in Phase 8, not here.

## Files Modified (2)
1. `lib/main.dart` — Slim constructor, use `buildAppProviders()`, remove moved functions
2. `lib/core/driver/main_driver.dart` — Update `seedBuiltinForms` import + update to new `ConstructionInspectorApp` 2-param constructor


---

# Phase 2: Core Domain Infrastructure

> **Goal:** Create shared base classes and patterns that all features will use during Clean Architecture migration. This phase is ADDITIVE ONLY — no existing code is modified or broken.

---

## Sub-phase 2.1: UseCase Base Class
**Files:**
- Create: `lib/shared/domain/use_case.dart`
**Agent**: `backend-data-layer-agent`

### Step 2.1.1: Create the UseCase abstract class

Create `lib/shared/domain/use_case.dart`:

```dart
/// Base class for all use cases in the application.
///
/// WHY: Use cases encapsulate a single business operation, making business logic
/// testable independently of UI and data layers. Each use case is a callable
/// class that takes typed params and returns a typed result.
///
/// Usage:
///   class GetContractors extends UseCase<List<Contractor>, GetContractorsParams> {
///     final ContractorRepository _repo;
///     GetContractors(this._repo);
///
///     @override
///     Future<List<Contractor>> call(GetContractorsParams params) async {
///       return _repo.getByProjectId(params.projectId);
///     }
///   }
abstract class UseCase<Type, Params> {
  /// Execute the use case with the given parameters.
  Future<Type> call(Params params);
}

/// Sentinel class for use cases that don't require parameters.
///
/// WHY: Avoids nullable params or `void` generics. Provides a clear signal
/// that a use case needs no input.
///
/// Usage:
///   class GetAllProjects extends UseCase<List<Project>, NoParams> {
///     @override
///     Future<List<Project>> call(NoParams params) async { ... }
///   }
///   // Invoke: getAllProjects(const NoParams());
class NoParams {
  const NoParams();
}

/// Parameters for project-scoped operations.
///
/// WHY: Most entities in this app are project-scoped. This avoids repeating
/// a `projectId` field in every feature's params class.
class ProjectParams {
  final String projectId;
  const ProjectParams({required this.projectId});
}

/// Parameters for single-entity lookup by ID.
class IdParams {
  final String id;
  const IdParams({required this.id});
}
```

---

## ~~Sub-phase 2.2: UseCaseResult Type~~ **REMOVED (YAGNI)**

> **Removed by review fix.** `UseCaseResult` is not consumed by any subsequent phase. Use cases return domain types directly or use the existing `RepositoryResult`. A use-case-specific result type will be introduced when a concrete need arises.

---

## Sub-phase 2.3: Domain Barrel Export
**Files:**
- Create: `lib/shared/domain/domain.dart`
**Agent**: `backend-data-layer-agent`

### Step 2.3.1: Create barrel export for domain layer

Create `lib/shared/domain/domain.dart`:

```dart
/// Barrel export for shared domain infrastructure.
///
/// WHY: Single import for all domain base classes. Features import
/// `package:construction_inspector/shared/domain/domain.dart` instead of
/// individual files.
export 'use_case.dart';
```

---

## ~~Sub-phase 2.4: BaseUseCaseListProvider~~ **REMOVED (YAGNI)**

> **Removed by review fix.** `BaseUseCaseListProvider` is not consumed by any subsequent phase. `BaseListProvider` continues to be used directly with domain repository interfaces. A use-case-aware base provider will be introduced when providers are decoupled from repositories in a future refactor.

---

## Sub-phase 2.5: Update Barrel Export for Providers
**Files:**
- Modify: `lib/shared/providers/` (add barrel if missing, or update existing)
**Agent**: `backend-data-layer-agent`

### Step 2.5.1: Ensure the new provider base class is exported

If `lib/shared/shared.dart` exists and exports providers, add the new file to it.
If provider-level barrel exports exist, add there too.

Add to `lib/shared/shared.dart` (at the appropriate location among existing exports):

```dart
export 'domain/domain.dart';
```

Do NOT remove any existing exports. This is additive only.

---

## Sub-phase 2.6: Unit Tests for Domain Infrastructure
**Files:**
- Create: `test/shared/domain/use_case_test.dart`
**Agent**: `qa-testing-agent`

### Step 2.6.1: Test UseCase base class and params

Create `test/shared/domain/use_case_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/shared/domain/domain.dart';

/// Concrete test implementation of UseCase.
class AddNumbers extends UseCase<int, AddNumbersParams> {
  @override
  Future<int> call(AddNumbersParams params) async {
    return params.a + params.b;
  }
}

class AddNumbersParams {
  final int a;
  final int b;
  const AddNumbersParams(this.a, this.b);
}

/// Test UseCase with NoParams.
class GetConstant extends UseCase<String, NoParams> {
  @override
  Future<String> call(NoParams params) async => 'constant_value';
}

void main() {
  group('UseCase', () {
    test('can be called with typed params', () async {
      final useCase = AddNumbers();
      final result = await useCase(AddNumbersParams(2, 3));
      expect(result, 5);
    });

    test('works with NoParams', () async {
      final useCase = GetConstant();
      final result = await useCase(const NoParams());
      expect(result, 'constant_value');
    });
  });

  group('ProjectParams', () {
    test('holds projectId', () {
      const params = ProjectParams(projectId: 'proj-123');
      expect(params.projectId, 'proj-123');
    });
  });

  group('IdParams', () {
    test('holds id', () {
      const params = IdParams(id: 'item-456');
      expect(params.id, 'item-456');
    });
  });
}
```

### ~~Step 2.6.2: Test UseCaseResult~~ **REMOVED** (Sub-phase 2.2 removed)

### ~~Step 2.6.3: Test BaseUseCaseListProvider~~ **REMOVED** (Sub-phase 2.4 removed)

---

## Sub-phase 2.7: Verify
**Files:** (none modified)
**Agent**: `backend-data-layer-agent`

### Step 2.7.1: Run static analysis

```
pwsh -Command "flutter analyze"
```

Expect zero new warnings/errors from the files created in this phase.

### Step 2.7.2: Run tests

```
pwsh -Command "flutter test test/shared/domain/"
```

All tests must pass. If any fail, fix before proceeding.

### Step 2.7.3: Run full test suite to confirm no regressions

```
pwsh -Command "flutter test"
```

Since this phase is additive-only, zero existing tests should break.

---

## Summary of Created Files

| File | Purpose |
|------|---------|
| `lib/shared/domain/use_case.dart` | UseCase, NoParams, ProjectParams, IdParams base classes |
| `lib/shared/domain/domain.dart` | Barrel export for domain layer |
| `test/shared/domain/use_case_test.dart` | Tests for UseCase base + param classes |

## Migration Notes for Phase 3+

When migrating a feature (e.g., locations):
1. Create abstract domain repository interface: `lib/features/locations/domain/repositories/location_repository.dart`
2. Rename concrete repository to `LocationRepositoryImpl implements LocationRepository`
3. Create feature use cases: `lib/features/locations/domain/use_cases/get_locations.dart` — each takes the abstract interface
4. Update provider to depend on the abstract repository interface type
5. Update provider constructor wiring in `main.dart`
6. Add `dispose()` to provider, fix catch blocks


---

## Phase 3: CRUD Features Domain Layer (Batch)

Add domain layer with abstract repository interfaces and pass-through use cases for 9 CRUD-like features. Also add `dispose()` to providers and fix `catch(_)` / `catch (e)` blocks missing Logger calls.

**Pattern per feature:** (A) Create domain interface, (B) Rename concrete repo to `*Impl`, (C) Create pass-through use cases, (D) Update provider to reference interface type, (E) Add `dispose()`, (F) Fix catch blocks, (G) Update barrel exports and feature module wiring.

---

### Sub-phase 3.1: Locations (Reference Implementation)
**Agent:** `backend-data-layer-agent`

This sub-phase establishes the full pattern. All subsequent sub-phases replicate it.

#### Step 3.1.1: Create domain repository interface
**Create:** `lib/features/locations/domain/repositories/location_repository.dart`

```dart
import 'package:construction_inspector/features/locations/data/models/location.dart';
import 'package:construction_inspector/shared/models/paged_result.dart';
import 'package:construction_inspector/shared/repositories/base_repository.dart';

/// Domain interface for location data access.
///
/// Presentation layer depends on this interface, not the concrete implementation.
/// This enables testing with fakes and swapping implementations.
abstract class LocationRepository implements ProjectScopedRepository<Location> {
  // --- inherited from ProjectScopedRepository / BaseRepository ---
  // getById, getAll, getPaged, getCount, save, delete
  // getByProjectId, getByProjectIdPaged, getCountByProject, create, update

  /// Search locations by name within a project.
  Future<List<Location>> search(String projectId, String query);

  /// Update an existing location (named variant, delegates to update()).
  Future<RepositoryResult<Location>> updateLocation(Location location);

  /// Delete all locations for a project.
  Future<void> deleteByProjectId(String projectId);

  /// Insert multiple locations (for seeding/import).
  Future<void> insertAll(List<Location> locations);
}
```

Every public method from the current `LocationRepository` concrete class (15 methods) must appear in the interface. The inherited methods from `ProjectScopedRepository<Location>` cover: `getById`, `getAll`, `getPaged`, `getCount`, `save`, `delete`, `getByProjectId`, `getByProjectIdPaged`, `getCountByProject`, `create`, `update`. The remaining 4 feature-specific methods are declared explicitly.

#### Step 3.1.2: Rename concrete repository to LocationRepositoryImpl
**Rename:** `lib/features/locations/data/repositories/location_repository.dart` -> `lib/features/locations/data/repositories/location_repository_impl.dart`

- Rename class `LocationRepository` -> `LocationRepositoryImpl`
- Add `implements LocationRepository` (the domain interface)
- Add import: `import 'package:construction_inspector/features/locations/domain/repositories/location_repository.dart';`
- Keep all existing code unchanged

#### Step 3.1.3: Create pass-through use cases
**Create:** `lib/features/locations/domain/usecases/get_locations.dart`

```dart
class GetLocations {
  final LocationRepository _repository;
  GetLocations(this._repository);
  Future<List<Location>> call(String projectId) => _repository.getByProjectId(projectId);
}
```

**Create:** `lib/features/locations/domain/usecases/create_location.dart`

```dart
class CreateLocation {
  final LocationRepository _repository;
  CreateLocation(this._repository);
  Future<RepositoryResult<Location>> call(Location location) => _repository.create(location);
}
```

**Create:** `lib/features/locations/domain/usecases/update_location.dart`

```dart
class UpdateLocation {
  final LocationRepository _repository;
  UpdateLocation(this._repository);
  Future<RepositoryResult<Location>> call(Location location) => _repository.update(location);
}
```

**Create:** `lib/features/locations/domain/usecases/delete_location.dart`

```dart
class DeleteLocation {
  final LocationRepository _repository;
  DeleteLocation(this._repository);
  Future<void> call(String id) => _repository.delete(id);
}
```

**Create:** `lib/features/locations/domain/usecases/search_locations.dart`

```dart
class SearchLocations {
  final LocationRepository _repository;
  SearchLocations(this._repository);
  Future<List<Location>> call(String projectId, String query) => _repository.search(projectId, query);
}
```

These are intentionally thin pass-through wrappers. Business logic lives in the repository impl. Use cases exist to establish the pattern for when real cross-cutting concerns (logging, caching, auth checks) are added later.

#### Step 3.1.4: Update provider to use domain interface type
**Edit:** `lib/features/locations/presentation/providers/location_provider.dart`

- Change `BaseListProvider<Location, LocationRepository>` to `BaseListProvider<Location, LocationRepository>` (where `LocationRepository` now imports from the domain interface, not the concrete class)
- Update import from `data/repositories/location_repository.dart` to `domain/repositories/location_repository.dart`

**IMPORTANT:** The `BaseListProvider<T, R extends ProjectScopedRepository<T>>` generic constraint means the domain interface must extend `ProjectScopedRepository<Location>`, which it already does via `implements`.

#### Step 3.1.5: Add dispose() to LocationProvider
**Edit:** `lib/features/locations/presentation/providers/location_provider.dart`

Add at the end of the class:

```dart
@override
void dispose() {
  // Clean up any resources
  super.dispose();
}
```

Note: `BaseListProvider` does not override `dispose()` from `ChangeNotifier`, so subclasses should add it to ensure cleanup if subscriptions/timers are added later.

#### Step 3.1.6: Fix catch blocks in touched files
**Audit:** `location_repository_impl.dart` - No bare `catch(_)` blocks (current code has no try/catch). No changes needed for this feature.

#### Step 3.1.7: Create barrel exports for domain layer
**Create:** `lib/features/locations/domain/domain.dart`

```dart
export 'repositories/location_repository.dart';
export 'usecases/get_locations.dart';
export 'usecases/create_location.dart';
export 'usecases/update_location.dart';
export 'usecases/delete_location.dart';
export 'usecases/search_locations.dart';
```

**Create:** `lib/features/locations/domain/repositories/repositories.dart`

```dart
export 'location_repository.dart';
```

**Create:** `lib/features/locations/domain/usecases/usecases.dart`

```dart
export 'get_locations.dart';
export 'create_location.dart';
export 'update_location.dart';
export 'delete_location.dart';
export 'search_locations.dart';
```

**Edit:** `lib/features/locations/locations.dart` - Add `export 'domain/domain.dart';`

**Edit:** `lib/features/locations/data/repositories/repositories.dart` - Change export from `location_repository.dart` to `location_repository_impl.dart`

#### Step 3.1.8: Update all import references
**Global find-replace** across the codebase:
- Any file importing `features/locations/data/repositories/location_repository.dart` that uses the type `LocationRepository` (not `LocationRepositoryImpl`) should switch to importing from `features/locations/domain/repositories/location_repository.dart`
- Files that construct `LocationRepository(datasource)` must change to `LocationRepositoryImpl(datasource)` and import the impl
- Key files to check: `lib/main.dart`, any feature modules, test files

#### Step 3.1.9: Update existing tests
**Edit:** `test/features/locations/data/repositories/location_repository_test.dart`
- Rename class references from `LocationRepository` to `LocationRepositoryImpl`
- Update imports

#### Step 3.1.10: Verify
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test test/features/locations/"
```

---

### Sub-phase 3.2: Photos
**Agent:** `backend-data-layer-agent`

#### Step 3.2.1: Create domain repository interface
**Create:** `lib/features/photos/domain/repositories/photo_repository.dart`

```dart
abstract class PhotoRepository implements BaseRepository<Photo> {
  Future<RepositoryResult<Photo>> createPhoto(Photo photo);
  Future<RepositoryResult<Photo>> getPhotoById(String id);
  Future<RepositoryResult<List<Photo>>> getPhotosForEntry(String entryId);
  Future<RepositoryResult<List<Photo>>> getPhotosForProject(String projectId);
  Future<PagedResult<Photo>> getByProjectIdPaged(String projectId, {required int offset, required int limit});
  Future<RepositoryResult<Photo>> updatePhoto(Photo photo);
  Future<RepositoryResult<void>> deletePhoto(String id, {bool deleteFile = true});
  Future<RepositoryResult<void>> deletePhotosForEntry(String entryId, {bool deleteFiles = true});
  Future<RepositoryResult<int>> getPhotoCountForEntry(String entryId);
  Future<RepositoryResult<int>> getPhotoCountForProject(String projectId);
  Future<RepositoryResult<void>> updateEntryId(String photoId, String newEntryId);
}
```

Note: `PhotoRepository` implements `BaseRepository<Photo>` (not `ProjectScopedRepository`) because the existing concrete class does too. All 11 feature-specific methods plus 6 inherited from `BaseRepository`.

#### Step 3.2.2: Rename concrete to PhotoRepositoryImpl
**Rename:** `lib/features/photos/data/repositories/photo_repository.dart` -> `photo_repository_impl.dart`
- Class: `PhotoRepository` -> `PhotoRepositoryImpl implements PhotoRepository`

#### Step 3.2.3: Create pass-through use cases
**Create:** `lib/features/photos/domain/usecases/`
- `get_photos_for_entry.dart` - wraps `getPhotosForEntry`
- `get_photos_for_project.dart` - wraps `getPhotosForProject`
- `create_photo.dart` - wraps `createPhoto`
- `update_photo.dart` - wraps `updatePhoto`
- `delete_photo.dart` - wraps `deletePhoto`

#### Step 3.2.4: Update PhotoProvider to use domain interface
**Edit:** `lib/features/photos/presentation/providers/photo_provider.dart`
- Change `final PhotoRepository _repository;` type to import from domain interface
- Constructor type stays the same name but references the abstract class

#### Step 3.2.5: Add dispose() to PhotoProvider
**Edit:** `lib/features/photos/presentation/providers/photo_provider.dart`

```dart
@override
void dispose() {
  super.dispose();
}
```

#### Step 3.2.6: Fix catch blocks
**Audit** `photo_repository_impl.dart`: All catch blocks already have `Logger.photo(...)` calls. No changes needed.

#### Step 3.2.7: Create barrel exports + update feature module
**Create:** `lib/features/photos/domain/domain.dart`, `repositories/repositories.dart`, `usecases/usecases.dart`
**Edit:** `lib/features/photos/photos.dart` - add `export 'domain/domain.dart';`
**Edit:** `lib/features/photos/data/repositories/repositories.dart` - change to `photo_repository_impl.dart`

#### Step 3.2.8: Update imports across codebase
Key consumers: `PhotoProvider`, `GalleryProvider`, `lib/main.dart`, any screen that constructs `PhotoRepository`.
**CRITICAL:** `GalleryProvider` depends on `PhotoRepository` - must update to import from domain interface.

#### Step 3.2.9: Update tests
No existing `photo_repository_test.dart` found. No test changes needed.

#### Step 3.2.10: Verify
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test test/features/photos/"
```

---

### Sub-phase 3.3: Contractors
**Agent:** `backend-data-layer-agent`

#### Step 3.3.1: Create domain repository interface
**Create:** `lib/features/contractors/domain/repositories/contractor_repository.dart`

```dart
abstract class ContractorRepository implements ProjectScopedRepository<Contractor> {
  Future<Contractor?> getPrimeByProjectId(String projectId);
  Future<List<Contractor>> getSubsByProjectId(String projectId);
  Future<RepositoryResult<Contractor>> updateContractor(Contractor contractor);
  Future<void> deleteByProjectId(String projectId);
  Future<void> insertAll(List<Contractor> contractors);
  Future<List<String>> getMostFrequentIds(String projectId, {int limit = 5});
}
```

Inherited from `ProjectScopedRepository`: `getById`, `getAll`, `getPaged`, `getCount`, `save`, `delete`, `getByProjectId`, `getByProjectIdPaged`, `getCountByProject`, `create`, `update`.

#### Step 3.3.2: Rename concrete to ContractorRepositoryImpl
**Rename:** `lib/features/contractors/data/repositories/contractor_repository.dart` -> `contractor_repository_impl.dart`

#### Step 3.3.3: Create pass-through use cases
**Create:** `lib/features/contractors/domain/usecases/`
- `get_contractors.dart` - wraps `getByProjectId`
- `create_contractor.dart` - wraps `create`
- `update_contractor.dart` - wraps `update`
- `delete_contractor.dart` - wraps `delete`
- `get_frequent_contractor_ids.dart` - wraps `getMostFrequentIds`

#### Step 3.3.4: Update ContractorProvider to domain interface
**Edit:** `lib/features/contractors/presentation/providers/contractor_provider.dart`
- Change `BaseListProvider<Contractor, ContractorRepository>` import to domain interface
- Note: `loadFrequentContractorIds` accesses `repository.getMostFrequentIds` directly - this works because the interface exposes it

#### Step 3.3.5: Add dispose() to ContractorProvider
Already has `clear()` override; add `dispose()`.

#### Step 3.3.6: Fix catch blocks
**Audit** `contractor_provider.dart` line 76: `catch (e)` in `loadFrequentContractorIds` already has `Logger.db(...)`. No changes needed.

#### Step 3.3.7: Barrel exports + feature module
**Create:** `lib/features/contractors/domain/domain.dart`, `repositories/repositories.dart`, `usecases/usecases.dart`
**Edit:** `lib/features/contractors/contractors.dart` - add domain export
**Edit:** `lib/features/contractors/data/repositories/repositories.dart` - change `contractor_repository.dart` to `contractor_repository_impl.dart`

#### Step 3.3.8: Update imports + existing tests
**Edit:** `test/features/contractors/data/repositories/contractor_repository_test.dart` - rename references

#### Step 3.3.9: Verify
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test test/features/contractors/"
```

---

### Sub-phase 3.4: Equipment
**Agent:** `backend-data-layer-agent`

#### Step 3.4.1: Create domain repository interface
**Create:** `lib/features/contractors/domain/repositories/equipment_repository.dart`

Note: Equipment lives under contractors feature directory.

```dart
abstract class EquipmentRepository implements BaseRepository<Equipment> {
  Future<List<Equipment>> getByContractorId(String contractorId);
  Future<List<Equipment>> getByContractorIds(List<String> contractorIds);
  Future<RepositoryResult<Equipment>> create(Equipment equipment);
  Future<RepositoryResult<Equipment>> updateEquipment(Equipment equipment);
  Future<void> deleteByContractorId(String contractorId);
  Future<int> getCountByContractor(String contractorId);
  Future<List<Equipment>> getByContractorIdSortedByUsage(String contractorId, String projectId);
  Future<Map<String, int>> getUsageCountsByProject(String projectId);
  Future<void> insertAll(List<Equipment> equipment);
}
```

Note: `EquipmentRepository` implements `BaseRepository<Equipment>` (not `ProjectScopedRepository`) matching the existing concrete class.

#### Step 3.4.2: Rename concrete to EquipmentRepositoryImpl
**Rename:** `lib/features/contractors/data/repositories/equipment_repository.dart` -> `equipment_repository_impl.dart`

#### Step 3.4.3: Create pass-through use cases
**Create:** `lib/features/contractors/domain/usecases/`
- `get_equipment_for_contractor.dart`
- `create_equipment.dart`
- `update_equipment.dart`
- `delete_equipment.dart`

#### Step 3.4.4: Update EquipmentProvider to domain interface
**Edit:** `lib/features/contractors/presentation/providers/equipment_provider.dart`
- Change `final EquipmentRepository _repository;` import to domain interface

#### Step 3.4.5: Add dispose() to EquipmentProvider
Add `dispose()` override.

#### Step 3.4.6: Fix catch blocks
**Audit** `equipment_provider.dart`: Multiple `catch (e)` blocks (lines 66, 97, 174, 214, 239, 253) all set `_error` string but do NOT call Logger. **FIX:** Add `Logger.db(...)` call to each catch block:
- Line 66: `Logger.db('[EquipmentProvider] loadEquipmentForContractor error: $e');`
- Line 97-98: `Logger.db('[EquipmentProvider] loadEquipmentForContractors error: $e');`
- Line 132: `Logger.db('[EquipmentProvider] loadEquipmentForContractorsSortedByUsage error: $e');`
- Line 174: `Logger.db('[EquipmentProvider] createEquipment error: $e');`
- Line 214: `Logger.db('[EquipmentProvider] updateEquipment error: $e');`
- Line 239: `Logger.db('[EquipmentProvider] deleteEquipment error: $e');`
- Line 253: `Logger.db('[EquipmentProvider] deleteEquipmentForContractor error: $e');`

#### Step 3.4.7: Barrel exports
**Edit:** `lib/features/contractors/domain/repositories/repositories.dart` - add `equipment_repository.dart` export
**Edit:** `lib/features/contractors/domain/usecases/usecases.dart` - add equipment use case exports
**Edit:** `lib/features/contractors/data/repositories/repositories.dart` - change `equipment_repository.dart` to `equipment_repository_impl.dart`

#### Step 3.4.8: Update imports + tests
**Edit:** `test/features/contractors/data/repositories/equipment_repository_test.dart`

#### Step 3.4.9: Verify
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test test/features/contractors/"
```

---

### Sub-phase 3.5: PersonnelTypes
**Agent:** `backend-data-layer-agent`

#### Step 3.5.1: Create domain repository interface
**Create:** `lib/features/contractors/domain/repositories/personnel_type_repository.dart`

```dart
abstract class PersonnelTypeRepository implements ProjectScopedRepository<PersonnelType> {
  Future<List<PersonnelType>> getByContractor(String projectId, String contractorId);
  Future<RepositoryResult<PersonnelType>> updateType(PersonnelType type);
  Future<void> deleteByProjectId(String projectId);
  Future<void> reorderTypes(String projectId, List<String> orderedIds);
  Future<int> getNextSortOrderForContractor(String projectId, String contractorId);
  Future<int> getNextSortOrder(String projectId);
  Future<void> insertAll(List<PersonnelType> types);
}
```

#### Step 3.5.2: Rename concrete to PersonnelTypeRepositoryImpl
**Rename:** `lib/features/contractors/data/repositories/personnel_type_repository.dart` -> `personnel_type_repository_impl.dart`

#### Step 3.5.3: Create pass-through use cases
**Create:** `lib/features/contractors/domain/usecases/`
- `get_personnel_types.dart`
- `create_personnel_type.dart`
- `update_personnel_type.dart`
- `delete_personnel_type.dart`

#### Step 3.5.4: Update PersonnelTypeProvider to domain interface
**Edit:** `lib/features/contractors/presentation/providers/personnel_type_provider.dart`
- Change `BaseListProvider<PersonnelType, PersonnelTypeRepository>` import to domain interface
- Note: `loadTypesForContractor` and `createDefaultTypesForContractor` access `repository.getByContractor` and `repository.create` - both must be on the interface

#### Step 3.5.5: Add dispose() to PersonnelTypeProvider

#### Step 3.5.6: Fix catch blocks
**Audit** `personnel_type_provider.dart`:
- Line 79: `rethrow;` in `loadTypesForContractor` - acceptable, but the comment says "Error will be handled by calling code". Consider adding `Logger.db(...)` before rethrow.
- Line 227: `catch (e)` in `reorderTypes` - no Logger call. **FIX:** Add `Logger.db('[PersonnelTypeProvider] reorderTypes error: $e');`

#### Step 3.5.7: Barrel exports
**Edit:** `lib/features/contractors/domain/repositories/repositories.dart` - add `personnel_type_repository.dart`
**Edit:** `lib/features/contractors/data/repositories/repositories.dart` - change to `personnel_type_repository_impl.dart`

#### Step 3.5.8: Update imports + tests
**Edit:** `test/features/contractors/data/repositories/personnel_type_repository_test.dart`

#### Step 3.5.9: Verify
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test test/features/contractors/"
```

---

### Sub-phase 3.6: BidItems (Quantities)
**Agent:** `backend-data-layer-agent`

#### Step 3.6.1: Extract domain types from provider
**Move** `DuplicateStrategy` enum and `ImportBatchResult` class from `lib/features/quantities/presentation/providers/bid_item_provider.dart` to:
**Create:** `lib/features/quantities/domain/models/import_batch_result.dart`

These are domain concepts (import strategy, batch result) that do not belong in the presentation layer. The provider file keeps using them via import.

#### Step 3.6.2: Create domain repository interface
**Create:** `lib/features/quantities/domain/repositories/bid_item_repository.dart`

```dart
abstract class BidItemRepository implements ProjectScopedRepository<BidItem> {
  Future<BidItem?> getByItemNumber(String projectId, String itemNumber);
  Future<List<BidItem>> search(String projectId, String query);
  Future<RepositoryResult<BidItem>> updateBidItem(BidItem bidItem);
  Future<void> deleteByProjectId(String projectId);
  Future<void> insertAll(List<BidItem> bidItems);
}
```

#### Step 3.6.3: Rename concrete to BidItemRepositoryImpl
**Rename:** `lib/features/quantities/data/repositories/bid_item_repository.dart` -> `bid_item_repository_impl.dart`

#### Step 3.6.4: Create pass-through use cases
**Create:** `lib/features/quantities/domain/usecases/`
- `get_bid_items.dart`
- `create_bid_item.dart`
- `update_bid_item.dart`
- `delete_bid_item.dart`
- `search_bid_items.dart`
- `import_bid_items.dart` - wraps `insertAll` (batch import)

#### Step 3.6.5: Update BidItemProvider
**Edit:** `lib/features/quantities/presentation/providers/bid_item_provider.dart`
- Change `BaseListProvider<BidItem, BidItemRepository>` import to domain interface
- Replace inline `DuplicateStrategy`/`ImportBatchResult` with import from domain models
- Remove the class/enum definitions from this file (moved in 3.6.1)

#### Step 3.6.6: Add dispose() to BidItemProvider
Override `dispose()` with `super.dispose()`.

#### Step 3.6.7: Fix catch blocks
**Audit** `bid_item_provider.dart`:
- Line 274: `catch (e, stack)` in `importBatch` insertAll - already has `Logger.error(...)`. OK.
- Line 288: `catch (e)` in importBatch replace loop - no Logger. **FIX:** Add `Logger.db('[BidItemProvider] importBatch replace error: $e');`
- Line 339: `catch (e)` in `loadItemsPaged` - no Logger. **FIX:** Add `Logger.db('[BidItemProvider] loadItemsPaged error: $e');`
- Line 402: `catch (e)` in `loadMoreItems` - no Logger. **FIX:** Add `Logger.db('[BidItemProvider] loadMoreItems error: $e');`

#### Step 3.6.8: Barrel exports + feature module
**Create:** `lib/features/quantities/domain/domain.dart`, `repositories/repositories.dart`, `models/models.dart`, `usecases/usecases.dart`
**Edit:** `lib/features/quantities/quantities.dart` - add domain export
**Edit:** `lib/features/quantities/data/repositories/repositories.dart` - change to `bid_item_repository_impl.dart`

#### Step 3.6.9: Verify
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test test/features/quantities/"
```

---

### Sub-phase 3.7: EntryQuantities
**Agent:** `backend-data-layer-agent`

#### Step 3.7.1: Create domain repository interface
**Create:** `lib/features/quantities/domain/repositories/entry_quantity_repository.dart`

```dart
abstract class EntryQuantityRepository implements BaseRepository<EntryQuantity> {
  Future<List<EntryQuantity>> getByEntryId(String entryId);
  Future<List<EntryQuantity>> getByBidItemId(String bidItemId);
  Future<double> getTotalUsedForBidItem(String bidItemId);
  Future<Map<String, double>> getTotalUsedByProject(String projectId);
  Future<RepositoryResult<EntryQuantity>> create(EntryQuantity quantity);
  Future<RepositoryResult<EntryQuantity>> updateQuantity(EntryQuantity quantity);
  Future<void> deleteByEntryId(String entryId);
  Future<void> deleteByBidItemId(String bidItemId);
  Future<int> getCountByEntry(String entryId);
  Future<void> insertAll(List<EntryQuantity> quantities);
  Future<RepositoryResult<void>> saveQuantitiesForEntry(String entryId, List<EntryQuantity> quantities);
}
```

Note: Implements `BaseRepository<EntryQuantity>` (not `ProjectScopedRepository`) matching existing.

#### Step 3.7.2: Rename concrete to EntryQuantityRepositoryImpl
**Rename:** `lib/features/quantities/data/repositories/entry_quantity_repository.dart` -> `entry_quantity_repository_impl.dart`

#### Step 3.7.3: Create pass-through use cases
**Create:** `lib/features/quantities/domain/usecases/`
- `get_entry_quantities.dart` - wraps `getByEntryId`
- `save_entry_quantities.dart` - wraps `saveQuantitiesForEntry`
- `get_total_used_by_project.dart` - wraps `getTotalUsedByProject`

#### Step 3.7.4: Update EntryQuantityProvider to domain interface
**Edit:** `lib/features/quantities/presentation/providers/entry_quantity_provider.dart`
- Change `final EntryQuantityRepository _repository;` import to domain interface

#### Step 3.7.5: Add dispose() to EntryQuantityProvider

#### Step 3.7.6: Fix catch blocks
**Audit** `entry_quantity_provider.dart`: Multiple `catch (e)` blocks (lines 63, 81, 121, 164, 199, 219, 265). All set `_error` but none call Logger. **FIX all:**
- Add `Logger.db('[EntryQuantityProvider] <methodName> error: $e');` to each catch block

#### Step 3.7.7: Barrel exports
**Edit:** `lib/features/quantities/domain/repositories/repositories.dart` - add `entry_quantity_repository.dart`
**Edit:** `lib/features/quantities/data/repositories/repositories.dart` - change to `entry_quantity_repository_impl.dart`

#### Step 3.7.8: Verify
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test test/features/quantities/"
```

---

### Sub-phase 3.8: Todos
**Agent:** `backend-data-layer-agent`

This feature has NO repository - the provider talks directly to the datasource. We must create both a repository and domain interface.

#### Step 3.8.1: Create concrete TodoItemRepository
**Create:** `lib/features/todos/data/repositories/todo_item_repository_impl.dart`

```dart
class TodoItemRepositoryImpl implements TodoItemRepository {
  final TodoItemLocalDatasource _localDatasource;
  TodoItemRepositoryImpl(this._localDatasource);

  Future<TodoItem?> getById(String id) => _localDatasource.getById(id);
  Future<List<TodoItem>> getAll() => _localDatasource.getAll();
  Future<List<TodoItem>> getByProjectId(String projectId) => _localDatasource.getByProjectId(projectId);
  Future<List<TodoItem>> getByEntryId(String entryId) => _localDatasource.getByEntryId(entryId);
  Future<List<TodoItem>> getIncomplete({String? projectId}) => _localDatasource.getIncomplete(projectId: projectId);
  Future<List<TodoItem>> getCompleted({String? projectId}) => _localDatasource.getCompleted(projectId: projectId);
  Future<List<TodoItem>> getByPriority(TodoPriority priority, {String? projectId}) =>
      _localDatasource.getByPriority(priority, projectId: projectId);
  Future<List<TodoItem>> getOverdue({String? projectId}) => _localDatasource.getOverdue(projectId: projectId);
  Future<List<TodoItem>> getDueToday({String? projectId}) => _localDatasource.getDueToday(projectId: projectId);
  Future<TodoItem> create(TodoItem todo) => _localDatasource.create(todo);
  Future<void> save(TodoItem item) async {
    final existing = await _localDatasource.getById(item.id);
    if (existing == null) {
      await _localDatasource.insert(item);
    } else {
      await _localDatasource.update(item);
    }
  }
  Future<void> update(TodoItem todo) => _localDatasource.update(todo);
  Future<TodoItem> toggleComplete(String id) => _localDatasource.toggleComplete(id);
  Future<void> delete(String id) => _localDatasource.deleteTodo(id);
  Future<int> deleteByProjectId(String projectId) => _localDatasource.deleteByProjectId(projectId);
  Future<int> deleteCompleted({String? projectId}) => _localDatasource.deleteCompleted(projectId: projectId);
  Future<int> getIncompleteCount({String? projectId}) => _localDatasource.getIncompleteCount(projectId: projectId);
  // BaseRepository stubs
  Future<int> getCount() => _localDatasource.getCount();
  Future<PagedResult<TodoItem>> getPaged({required int offset, required int limit}) =>
      _localDatasource.getPaged(offset: offset, limit: limit);
}
```

#### Step 3.8.2: Create domain repository interface
**Create:** `lib/features/todos/domain/repositories/todo_item_repository.dart`

```dart
abstract class TodoItemRepository {
  Future<TodoItem?> getById(String id);
  Future<List<TodoItem>> getAll();
  Future<List<TodoItem>> getByProjectId(String projectId);
  Future<List<TodoItem>> getByEntryId(String entryId);
  Future<List<TodoItem>> getIncomplete({String? projectId});
  Future<List<TodoItem>> getCompleted({String? projectId});
  Future<List<TodoItem>> getByPriority(TodoPriority priority, {String? projectId});
  Future<List<TodoItem>> getOverdue({String? projectId});
  Future<List<TodoItem>> getDueToday({String? projectId});
  Future<TodoItem> create(TodoItem todo);
  Future<void> save(TodoItem item);
  Future<void> update(TodoItem todo);
  Future<TodoItem> toggleComplete(String id);
  Future<void> delete(String id);
  Future<int> deleteByProjectId(String projectId);
  Future<int> deleteCompleted({String? projectId});
  Future<int> getIncompleteCount({String? projectId});
}
```

Note: Does NOT extend `BaseRepository` or `ProjectScopedRepository` since the existing datasource API doesn't match those patterns (e.g., `create` returns `TodoItem`, not `RepositoryResult`). Keep it simple; upgrade to `ProjectScopedRepository` in a future phase if needed.

#### Step 3.8.3: Create pass-through use cases
**Create:** `lib/features/todos/domain/usecases/`
- `get_todos.dart` - wraps `getByProjectId`
- `create_todo.dart` - wraps `create`
- `toggle_todo.dart` - wraps `toggleComplete`
- `delete_todo.dart` - wraps `delete`

#### Step 3.8.4: Update TodoProvider to use repository
**Edit:** `lib/features/todos/presentation/providers/todo_provider.dart`
- Change `final TodoItemLocalDatasource _datasource;` to `final TodoItemRepository _repository;`
- Replace all `_datasource.xxx()` calls with `_repository.xxx()` method calls
- Update constructor: `TodoProvider(this._repository);`
- The method signatures on the interface match the datasource, so the call sites inside the provider are 1:1 renames

#### Step 3.8.5: Add dispose() to TodoProvider

#### Step 3.8.6: Fix catch blocks
**Audit** `todo_provider.dart`: All `catch (e)` blocks already have `Logger.ui(...)` calls. No changes needed.

#### Step 3.8.7: Barrel exports + feature module
**Create:** `lib/features/todos/data/repositories/repositories.dart` (new - didn't exist before)

```dart
export 'todo_item_repository_impl.dart';
```

**Create:** `lib/features/todos/domain/domain.dart`, `repositories/repositories.dart`, `usecases/usecases.dart`
**Edit:** `lib/features/todos/todos.dart` - add domain and data/repositories exports, remove direct datasource export from barrel (provider no longer uses it directly)

#### Step 3.8.8: Update main.dart and wiring
Where `TodoProvider(todoItemLocalDatasource)` is constructed, change to `TodoProvider(TodoItemRepositoryImpl(todoItemLocalDatasource))`.

#### Step 3.8.9: Update tests
**Edit:** `test/features/todos/data/datasources/todo_item_local_datasource_test.dart` - no changes (tests datasource directly)
May need to create `test/features/todos/data/repositories/todo_item_repository_impl_test.dart` if coverage requirements demand it - but since it is pure pass-through, defer to a future phase.

#### Step 3.8.10: Verify
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test test/features/todos/"
```

---

### Sub-phase 3.9: Calculator
**Agent:** `backend-data-layer-agent`

Same pattern as Todos - no repository exists, provider uses datasource directly.

#### Step 3.9.1: Create concrete CalculationHistoryRepository
**Create:** `lib/features/calculator/data/repositories/calculation_history_repository_impl.dart`

```dart
class CalculationHistoryRepositoryImpl implements CalculationHistoryRepository {
  final CalculationHistoryLocalDatasource _localDatasource;
  CalculationHistoryRepositoryImpl(this._localDatasource);

  Future<CalculationHistory?> getById(String id) => _localDatasource.getById(id);
  Future<List<CalculationHistory>> getAll() => _localDatasource.getAll();
  Future<List<CalculationHistory>> getByProjectId(String projectId) => _localDatasource.getByProjectId(projectId);
  Future<List<CalculationHistory>> getByEntryId(String entryId) => _localDatasource.getByEntryId(entryId);
  Future<List<CalculationHistory>> getByType(CalculationType type) => _localDatasource.getByType(type);
  Future<List<CalculationHistory>> getRecent({int limit = 10}) => _localDatasource.getRecent(limit: limit);
  Future<CalculationHistory> create(CalculationHistory calculation) => _localDatasource.create(calculation);
  Future<void> save(CalculationHistory item) async {
    final existing = await _localDatasource.getById(item.id);
    if (existing == null) {
      await _localDatasource.insert(item);
    } else {
      await _localDatasource.update(item);
    }
  }
  Future<void> delete(String id) async { await _localDatasource.deleteCalculation(id); }
  Future<int> deleteByProjectId(String projectId) => _localDatasource.deleteByProjectId(projectId);
}
```

#### Step 3.9.2: Create domain repository interface
**Create:** `lib/features/calculator/domain/repositories/calculation_history_repository.dart`

```dart
abstract class CalculationHistoryRepository {
  Future<CalculationHistory?> getById(String id);
  Future<List<CalculationHistory>> getAll();
  Future<List<CalculationHistory>> getByProjectId(String projectId);
  Future<List<CalculationHistory>> getByEntryId(String entryId);
  Future<List<CalculationHistory>> getByType(CalculationType type);
  Future<List<CalculationHistory>> getRecent({int limit = 10});
  Future<CalculationHistory> create(CalculationHistory calculation);
  Future<void> save(CalculationHistory item);
  Future<void> delete(String id);
  Future<int> deleteByProjectId(String projectId);
}
```

#### Step 3.9.3: Create pass-through use cases
**Create:** `lib/features/calculator/domain/usecases/`
- `get_calculation_history.dart` - wraps `getByProjectId` / `getRecent`
- `save_calculation.dart` - wraps `create`
- `delete_calculation.dart` - wraps `delete`

#### Step 3.9.4: Update CalculatorProvider to use repository
**Edit:** `lib/features/calculator/presentation/providers/calculator_provider.dart`
- Change `final CalculationHistoryLocalDatasource _datasource;` to `final CalculationHistoryRepository _repository;`
- Replace all `_datasource.xxx()` calls with `_repository.xxx()`
- Update constructor

#### Step 3.9.5: Add dispose() to CalculatorProvider

#### Step 3.9.6: Fix catch blocks
**Audit** `calculator_provider.dart`: All `catch (e)` blocks already have `Logger.ui(...)` calls. No changes needed.

#### Step 3.9.7: Barrel exports + feature module
**Create:** `lib/features/calculator/data/repositories/repositories.dart`
**Create:** `lib/features/calculator/domain/domain.dart`, `repositories/repositories.dart`, `usecases/usecases.dart`
**Edit:** `lib/features/calculator/calculator.dart` - add domain and data/repositories exports

#### Step 3.9.8: Update main.dart wiring
Change `CalculatorProvider(calculationHistoryLocalDatasource)` to `CalculatorProvider(CalculationHistoryRepositoryImpl(calculationHistoryLocalDatasource))`.

#### Step 3.9.9: Verify
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test test/features/calculator/"
```

---

### Sub-phase 3.10: Gallery (Cross-Feature Consumer)
**Agent:** `backend-data-layer-agent`

Gallery has no datasource or repository of its own. It consumes `PhotoRepository` and `DailyEntryRepository` from other features. The domain layer here consists of use cases only.

#### Step 3.10.1: Create gallery-specific use cases
**Create:** `lib/features/gallery/domain/usecases/get_gallery_photos.dart`

```dart
class GetGalleryPhotos {
  final PhotoRepository _photoRepository;
  GetGalleryPhotos(this._photoRepository);
  Future<RepositoryResult<List<Photo>>> call(String projectId) =>
      _photoRepository.getPhotosForProject(projectId);
}
```

**Create:** `lib/features/gallery/domain/usecases/get_gallery_entries.dart`

```dart
class GetGalleryEntries {
  final DailyEntryRepository _entryRepository;
  GetGalleryEntries(this._entryRepository);
  Future<List<DailyEntry>> call(String projectId) =>
      _entryRepository.getByProjectId(projectId);
}
```

Note: `DailyEntryRepository` is not being refactored in this phase (it's in the entries feature and not one of the 9 CRUD features). The gallery use case references the existing concrete type. When entries gets its domain layer in a future phase, this import will update.

#### Step 3.10.2: Update GalleryProvider
**Edit:** `lib/features/gallery/presentation/providers/gallery_provider.dart`
- Change `PhotoRepository` import to domain interface (from sub-phase 3.2)
- `DailyEntryRepository` stays as-is (concrete, not refactored this phase)

#### Step 3.10.3: Add dispose() to GalleryProvider

#### Step 3.10.4: Fix catch blocks
**Audit** `gallery_provider.dart`:
- Line 74: `catch (e)` in `loadPhotosForProject` - has Logger call. OK.

No additional fixes needed.

#### Step 3.10.5: Barrel exports
**Create:** `lib/features/gallery/domain/domain.dart`, `usecases/usecases.dart`
**Edit:** `lib/features/gallery/gallery.dart` - add domain export

#### Step 3.10.6: Verify
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
```

---

### Sub-phase 3.11: Final Integration Verification
**Agent:** `backend-data-layer-agent`

#### Step 3.11.1: Full static analysis
```
pwsh -Command "flutter analyze"
```
Fix any remaining import errors, type mismatches, or missing exports.

#### Step 3.11.2: Full test suite
```
pwsh -Command "flutter test"
```
Fix any test failures caused by renamed types or changed imports.

#### Step 3.11.3: Verify BaseListProvider generic constraint compatibility
Confirm that all `BaseListProvider<T, R>` subclasses still compile with `R` being the domain interface (which extends/implements `ProjectScopedRepository<T>`):
- `LocationProvider<Location, LocationRepository>` (domain interface)
- `ContractorProvider<Contractor, ContractorRepository>` (domain interface)
- `PersonnelTypeProvider<PersonnelType, PersonnelTypeRepository>` (domain interface)
- `BidItemProvider<BidItem, BidItemRepository>` (domain interface)

The key constraint is `R extends ProjectScopedRepository<T>` on `BaseListProvider`. The domain interfaces must all extend/implement `ProjectScopedRepository<T>` for this to work. Equipment and EntryQuantity providers do NOT use `BaseListProvider` (they extend `ChangeNotifier` directly), so they are unaffected.

---

### Summary of new files created (per feature):

| Feature | domain/repositories/ | domain/usecases/ | domain/models/ | data/repositories/ (renamed) |
|---------|---------------------|-------------------|----------------|------------------------------|
| locations | `location_repository.dart` | 5 use cases | - | `location_repository_impl.dart` |
| photos | `photo_repository.dart` | 5 use cases | - | `photo_repository_impl.dart` |
| contractors | `contractor_repository.dart` | 5 use cases | - | `contractor_repository_impl.dart` |
| equipment | `equipment_repository.dart` | 4 use cases | - | `equipment_repository_impl.dart` |
| personnel_types | `personnel_type_repository.dart` | 4 use cases | - | `personnel_type_repository_impl.dart` |
| bid_items | `bid_item_repository.dart` | 6 use cases | `import_batch_result.dart` | `bid_item_repository_impl.dart` |
| entry_quantities | `entry_quantity_repository.dart` | 3 use cases | - | `entry_quantity_repository_impl.dart` |
| todos | `todo_item_repository.dart` | 4 use cases | - | `todo_item_repository_impl.dart` (NEW) |
| calculator | `calculation_history_repository.dart` | 3 use cases | - | `calculation_history_repository_impl.dart` (NEW) |
| gallery | - | 2 use cases | - | - (no repo) |

**Total new files:** ~9 interfaces + ~41 use cases + 1 extracted model + ~9 renamed impls + ~27 barrel files = ~87 files
**Total modified files:** ~9 providers + ~4 test files + barrel exports + main.dart wiring = ~20 files

### Catch block fixes summary:
| File | Fixes needed |
|------|-------------|
| `equipment_provider.dart` | 7 catch blocks missing Logger |
| `entry_quantity_provider.dart` | 7 catch blocks missing Logger |
| `bid_item_provider.dart` | 2 catch blocks missing Logger |
| `personnel_type_provider.dart` | 1 catch block missing Logger |


---

## Phase 4: Auth Domain Layer (Heaviest Extraction)

Break AuthProvider (977 lines, 48 methods) into focused use cases. Fix 4 layer violations where presentation code calls Supabase/SQLite directly.

**Depends on:** Phase 3 (repository pattern established)

---

### Sub-phase 4.1: Create AppConfigRepository (Fix AppConfigProvider violation)

**Files:**
- `lib/features/auth/data/repositories/app_config_repository.dart` (NEW)
- `lib/features/auth/presentation/providers/app_config_provider.dart` (EDIT)
- `lib/main.dart` (EDIT — wire repository into provider)

**Agent:** auth-agent

**What:**
1. Create `AppConfigRepository` in `lib/features/auth/data/repositories/`:
   - Constructor takes `SupabaseClient?` (nullable for offline/unconfigured)
   - Method: `Future<Map<String, String>> fetchConfig({Duration timeout})` — wraps the `Supabase.instance.client.from('app_config').select()` call currently at `app_config_provider.dart:148-156`
   - Returns `Map<String, String>` of key-value pairs (same shape as current `configMap`)
2. Edit `AppConfigProvider`:
   - Add `AppConfigRepository` constructor parameter
   - Replace `Supabase.instance.client.from('app_config').select()` at line 148 with `_repository.fetchConfig(timeout: _fetchTimeout)`
   - Remove `import 'package:supabase_flutter/supabase_flutter.dart'`
   - Remove `import 'package:construction_inspector/core/config/supabase_config.dart'` — move the `isConfigured` check into the repository
3. Wire in `main.dart` — construct `AppConfigRepository` with `Supabase.instance.client` and pass to `AppConfigProvider`

**Verify:** `pwsh -Command "flutter analyze"` — no `Supabase.instance` references in `app_config_provider.dart`

---

### Sub-phase 4.2: Fix SettingsScreen Direct Supabase Calls

**Files:**
- `lib/features/auth/data/repositories/user_profile_repository.dart` (EDIT — add remote update methods)
- `lib/features/auth/data/datasources/remote/user_profile_remote_datasource.dart` (EDIT — add update methods)
- `lib/features/settings/presentation/screens/settings_screen.dart` (EDIT)

**Agent:** frontend-flutter-specialist-agent

**What:**
1. Add to `UserProfileRemoteDatasource`:
   - `Future<void> updateGaugeNumber(String userId, String gaugeNumber)` — wraps the Supabase call at `settings_screen.dart:72-75`
   - `Future<void> updateInitials(String userId, String? initials)` — wraps the call at `settings_screen.dart:118-124`
2. Add `UserProfileRemoteDatasource` as a second constructor parameter to `UserProfileRepository`:
   - `UserProfileRepository(this._localDatasource, {UserProfileRemoteDatasource? remoteDatasource})`
   - Add methods: `updateGaugeNumber(String userId, String gaugeNumber)` and `updateInitials(String userId, String? initials)` — delegate to remote datasource, include `updated_at` timestamp
3. Edit `SettingsScreen`:
   - Add `UserProfileRepository` via `context.read<UserProfileRepository>()` (must be provided in widget tree — check `main.dart`)
   - Replace `_editGaugeNumber` Supabase call (lines 72-75) with `userProfileRepository.updateGaugeNumber(userId, result)`
   - Replace `_editInitials` Supabase call (lines 118-124) with `userProfileRepository.updateInitials(userId, result.isEmpty ? null : result)`
   - Remove `import 'package:supabase_flutter/supabase_flutter.dart'`
4. If `UserProfileRepository` is not already provided in the widget tree, add it to `main.dart`

**SECURITY:** Preserve the `updated_at` timestamp behavior — both current calls set `DateTime.now().toUtc().toIso8601String()`. The repository methods must do the same.

**Verify:** `pwsh -Command "flutter analyze"` — no `Supabase.instance` references in `settings_screen.dart`

---

### Sub-phase 4.3: Fix AuthProvider Company-Switch Direct DB Query

**Files:**
- `lib/features/auth/data/repositories/company_repository.dart` (EDIT)
- `lib/features/auth/presentation/providers/auth_provider.dart` (EDIT)

**Agent:** auth-agent

**What:**
1. Add method to `CompanyRepository`:
   - `Future<String?> getCachedCompanyId()` — queries local companies table, returns first company's ID or null
   - Implementation: `final company = await getMyCompany(); return company?.id;`
   - This replaces the raw `db.query('companies', limit: 1)` at `auth_provider.dart:324`
2. Edit `AuthProvider.signIn()` (lines 319-336):
   - Replace `final db = await dbService.database; final cachedCompanies = await db.query('companies', limit: 1);` with `final cachedCompanyId = await _companyRepository?.getCachedCompanyId();`
   - Remove the intermediate `cachedCompanyId` extraction from `cachedCompanies.first['id']`
   - Update the comparison: `if (guardProfile != null && guardProfile.companyId != null && cachedCompanyId != null && guardProfile.companyId != cachedCompanyId)`
   - Remove `_databaseService` usage from signIn — it should only go through repositories

**SECURITY INVARIANT:** The `clear local data BEFORE switching company` logic at line 331 (`AuthService.clearLocalCompanyData(dbService)`) must be preserved exactly. Only the *read* is being moved to repository; the clear still needs `DatabaseService` (it wipes multiple tables).

**Verify:** `pwsh -Command "flutter analyze"`

---

### Sub-phase 4.4: Extract Auth Use Cases (Sign In / Sign Up / Sign Out)

**Files:**
- `lib/features/auth/domain/use_cases/sign_in_use_case.dart` (NEW)
- `lib/features/auth/domain/use_cases/sign_up_use_case.dart` (NEW)
- `lib/features/auth/domain/use_cases/sign_out_use_case.dart` (NEW)
- `lib/features/auth/presentation/providers/auth_provider.dart` (EDIT)

**Agent:** auth-agent

**What:**
1. Create `lib/features/auth/domain/use_cases/` directory
2. **SignInUseCase:**
   - Dependencies: `AuthService`, `CompanyRepository`, `DatabaseService?`
   - Method: `Future<SignInResult> execute({required String email, required String password})`
   - Extract lines 306-365 from `AuthProvider.signIn()` — the actual auth call, company-switch guard, and error handling
   - Return type `SignInResult` (sealed class or simple class with `user`, `guardProfile`, `error` fields)
   - AuthProvider.signIn() becomes: call use case, set state from result, call loadUserProfile
3. **SignUpUseCase:**
   - Dependencies: `AuthService`
   - Method: `Future<SignUpResult> execute({required String email, required String password, String? fullName})`
   - Extract lines 256-289 from `AuthProvider.signUp()`
4. **SignOutUseCase:**
   - Dependencies: `AuthService`, `PreferencesService?`, `FlutterSecureStorage`
   - Method: `Future<bool> execute()`
   - Extract lines 379-400 from `AuthProvider.signOut()` — the actual signOut call, BackgroundSyncHandler.dispose(), secure storage clear
   - Also used by `signOutLocally()` and `forceReauthOnly()` (shared cleanup logic)

**Key decisions:**
- AuthProvider remains the ChangeNotifier state holder — use cases are stateless operation objects
- Mock auth branching stays in AuthProvider (it's a test concern, not domain logic)
- Use cases do NOT call `notifyListeners()` — AuthProvider does that after calling the use case
- `_parseAuthError` and `_parseOtpError` stay on AuthProvider (presentation-layer error mapping)

**Verify:** `pwsh -Command "flutter analyze"`

---

### Sub-phase 4.5: Extract Profile & Company Use Cases

**Files:**
- `lib/features/auth/domain/use_cases/load_profile_use_case.dart` (NEW)
- `lib/features/auth/domain/use_cases/switch_company_use_case.dart` (NEW)
- `lib/features/auth/domain/use_cases/migrate_preferences_use_case.dart` (NEW)
- `lib/features/auth/presentation/providers/auth_provider.dart` (EDIT)

**Agent:** auth-agent

**What:**
1. **LoadProfileUseCase:**
   - Dependencies: `AuthService`, `CompanyRepository`, `PreferencesService?`, `DatabaseService?`
   - Method: `Future<LoadProfileResult> execute(String userId, {UserProfile? preloadedProfile})`
   - Extract lines 554-685 from `loadUserProfile()` — remote fetch, legacy migration, company persistence, offline fallback
   - Return type includes: `userProfile`, `company`, `shouldSignOut` (for stale session detection)
   - AuthProvider.loadUserProfile() becomes: call use case, set `_userProfile`/`_company` from result, cache in attributionRepository
2. **SwitchCompanyUseCase:**
   - Dependencies: `CompanyRepository`, `DatabaseService`, `AuthService`
   - Method: `Future<bool> detectAndHandle(String userId, UserProfile? guardProfile)`
   - Extract the company-switch guard from signIn (lines 319-343) into a reusable check
   - **SECURITY:** `AuthService.clearLocalCompanyData(dbService)` MUST be called internally by the use case before returning `true`. The caller must NOT be responsible for clearing data — the use case encapsulates the entire clear-then-switch flow to prevent cross-company data leakage. Add inline comment: `// SECURITY: clear MUST happen inside this use case, not in caller, to prevent cross-company data leakage`
3. **MigratePreferencesUseCase:**
   - Dependencies: `AuthService`, `PreferencesService`
   - Method: `Future<UserProfile> execute(UserProfile remoteProfile)`
   - Extract lines 570-615 from loadUserProfile — the cert/phone/name migration logic
   - Returns the (possibly migrated) profile

**SECURITY INVARIANTS:**
- SwitchCompanyUseCase: clear MUST happen inside this use case, not in caller, to prevent cross-company data leakage. The use case calls `AuthService.clearLocalCompanyData(dbService)` internally before returning. Add comment: `// SECURITY: clear MUST happen inside this use case, not in caller, to prevent cross-company data leakage`
- LoadProfileUseCase: stale session detection triggers signOut — use case returns `shouldSignOut: true`, AuthProvider calls signOut()
- Offline fallback: if remote fetch fails, use case queries local DB — preserves admin permissions for offline cold start

**Verify:** `pwsh -Command "flutter analyze"`

---

### Sub-phase 4.6: Extract Inactivity & Mock Auth Use Cases

**Files:**
- `lib/features/auth/domain/use_cases/check_inactivity_use_case.dart` (NEW)
- `lib/features/auth/presentation/providers/auth_provider.dart` (EDIT)

**Agent:** auth-agent

**What:**
1. **CheckInactivityUseCase:**
   - Dependencies: `FlutterSecureStorage`
   - Method: `Future<bool> execute()` — returns true if timeout exceeded (caller should sign out)
   - Method: `Future<void> updateLastActive()` — updates timestamp
   - Extract lines 884-916 from AuthProvider
   - Static `inactivityThreshold` of 7 days stays as a constant
   - **SECURITY:** The use case only *checks*. AuthProvider calls `signOut()` if result is true. This preserves the "force sign-out" guarantee without the use case needing auth dependencies.
2. **Mock auth stays on AuthProvider** — it's purely a test/development concern (gated by `TestModeConfig.useMockAuth`). The 4 mock methods (`_initMockAuth`, `_mockSignIn`, `_mockSignOut`, `_mockSignUp`, `_mockResetPassword`) total ~100 lines and are already well-isolated with the `if (TestModeConfig.useMockAuth)` guards. Extracting them into a strategy object adds indirection without architectural benefit since they only exist in debug builds.
3. Update AuthProvider:
   - Replace `checkInactivityTimeout()` body with: `final timedOut = await _checkInactivityUseCase.execute(); if (timedOut) await signOut(); return timedOut;`
   - Replace `updateLastActive()` body with delegation to use case
   - Remove `_secureStorage` field and `_inactivityThreshold` constant from AuthProvider (moved to use case)
   - Keep `_clearSecureStorageOnSignOut()` on AuthProvider since it's called from multiple sign-out paths and is 5 lines

**Verify:** `pwsh -Command "flutter analyze"`

---

### Sub-phase 4.7: Wire Use Cases in main.dart & Update AuthProvider Constructor

**Files:**
- `lib/main.dart` (EDIT)
- `lib/features/auth/presentation/providers/auth_provider.dart` (EDIT)

**Agent:** auth-agent

**What:**
1. Update `AuthProvider` constructor to accept use cases:
   ```dart
   AuthProvider(
     this._authService, {
     PreferencesService? preferencesService,
     DatabaseService? databaseService,
     CompanyRepository? companyRepository,
     SignInUseCase? signInUseCase,
     SignOutUseCase? signOutUseCase,
     SignUpUseCase? signUpUseCase,
     LoadProfileUseCase? loadProfileUseCase,
     CheckInactivityUseCase? checkInactivityUseCase,
   })
   ```
   - Use cases are optional for backwards compatibility with existing tests
   - When null, AuthProvider falls back to inline implementation (migration path)
2. Wire in `main.dart`:
   - Construct use cases with their dependencies
   - Pass to AuthProvider
3. Final AuthProvider line count target: ~450-550 lines (down from 977)
   - State fields + getters: ~100 lines (unchanged)
   - Auth methods (thin delegation): ~150 lines
   - Mock auth: ~100 lines
   - Constructor + listener + helpers: ~100 lines

**Verify:** `pwsh -Command "flutter analyze"` and `pwsh -Command "flutter test"`

---

### Sub-phase 4.8: Unit Tests for Use Cases

**Files:**
- `test/features/auth/domain/use_cases/sign_in_use_case_test.dart` (NEW)
- `test/features/auth/domain/use_cases/sign_out_use_case_test.dart` (NEW)
- `test/features/auth/domain/use_cases/check_inactivity_use_case_test.dart` (NEW)
- `test/features/auth/domain/use_cases/load_profile_use_case_test.dart` (NEW)
- `test/features/auth/presentation/providers/auth_provider_test.dart` (EDIT — update for new constructor)

**Agent:** qa-testing-agent

**What:**
1. **SignInUseCase tests:**
   - Happy path: valid credentials return user + null guardProfile
   - Company switch detected: returns guardProfile = null (cleared)
   - AuthException: returns error message
   - Network error: returns generic error
2. **SignOutUseCase tests:**
   - Happy path: calls authService.signOut, disposes BackgroundSyncHandler, clears secure storage
   - Error: returns false, does not throw
3. **CheckInactivityUseCase tests:**
   - No stored timestamp (first launch): writes timestamp, returns false
   - Within 7 days: returns false
   - Beyond 7 days: returns true (caller signs out)
   - Parse error: returns false (fail open)
4. **LoadProfileUseCase tests:**
   - Remote profile loaded: returns profile + company
   - Legacy migration triggered: returns migrated profile
   - Remote fails, local fallback succeeds: returns cached profile
   - Stale session (profile null, user exists): returns shouldSignOut = true
5. **Update existing auth_provider_test.dart:**
   - Update AuthProvider construction to pass mock use cases (or null to use inline fallback)
   - Ensure existing tests still pass

**Verify:** `pwsh -Command "flutter test test/features/auth/"`

---

### Summary: Layer Violations Fixed

| # | Location | Violation | Fixed In |
|---|----------|-----------|----------|
| 1 | `auth_provider.dart:323` | Raw `db.query('companies')` | Sub-phase 4.3 — CompanyRepository.getCachedCompanyId() |
| 2 | `app_config_provider.dart:148` | `Supabase.instance.client.from('app_config')` | Sub-phase 4.1 — AppConfigRepository.fetchConfig() |
| 3 | `settings_screen.dart:72` | `Supabase.instance.client.from('user_profiles').update(gauge)` | Sub-phase 4.2 — UserProfileRepository.updateGaugeNumber() |
| 4 | `settings_screen.dart:118` | `Supabase.instance.client.from('user_profiles').update(initials)` | Sub-phase 4.2 — UserProfileRepository.updateInitials() |

### Execution Order

Sub-phases 4.1, 4.2, 4.3 are independent (can run in parallel).
Sub-phases 4.4, 4.5, 4.6 depend on 4.3 (company repository method used by use cases).
Sub-phase 4.7 depends on 4.4-4.6 (wires all use cases).
Sub-phase 4.8 depends on 4.7 (tests the final wired state).

```
4.1 ─────────────────────────┐
4.2 ─────────────────────────┤
4.3 ──┬─────────────────────┤
      │                      │
      ├── 4.4 ──┐            │
      ├── 4.5 ──┼── 4.7 ── 4.8
      └── 4.6 ──┘
```


---

## Phase 5: Projects Domain Layer (Second Heaviest)

Break `ProjectProvider` (800 lines, 54 symbols) into use cases. Fix `ProjectSetupScreen` and `ProjectProvider` layer violations (6 total). `ProjectProvider` stays as state holder, delegates to use cases. Raw DB queries move into repository methods first, then use cases wrap those.

### Sub-phase 5.1: Create SyncedProjectRepository and Extend ProjectAssignmentRepository

**Files:**
- `lib/features/projects/data/repositories/synced_project_repository.dart` (NEW)
- `lib/features/projects/data/repositories/project_assignment_repository.dart` (EDIT)
- `lib/features/projects/data/repositories/project_repository.dart` (EDIT)
- `lib/features/projects/data/repositories/repositories.dart` (EDIT — barrel export)

**Agent**: backend-data-layer-agent

**What:**

1. **Create `SyncedProjectRepository`** with these methods extracted from `ProjectProvider` raw DB queries:
   - `getAll()` — returns all synced_projects rows (used by `fetchRemoteProjects` line 697)
   - `getUnassignedAtMap()` — returns `Map<String, String?>` of project_id -> unassigned_at (used by `loadAssignments` line 237-241)
   - `enroll(String projectId)` — insert into synced_projects with synced_at timestamp (used by `enrollProject` line 255-268 AND `project_setup_screen.dart` line 985-993)
   - `unenroll(String projectId)` — delete from synced_projects (used by `unenrollProject` line 274-285)

2. **Add to `ProjectRepository`:**
   - `getCreatedByUserId(String projectId)` — queries `projects` table for `created_by_user_id` column only (used by `deleteProject` auth check, line 555-560). Returns `String?`.
   - `getMetadataByCompanyId(String companyId)` — returns lightweight project rows with only `id, name, project_number, company_id, is_active, updated_at` columns (used by `fetchRemoteProjects` line 702-707). Returns `List<Map<String, dynamic>>` or a dedicated lightweight model.

3. **Update barrel export** `repositories.dart` to include `SyncedProjectRepository`.

**Verification:** `pwsh -Command "flutter analyze"` — no new warnings.

**Why these groupings:**
- `synced_projects` is a distinct local-only table tracking device enrollment, not part of the `projects` table. It deserves its own repository.
- `getCreatedByUserId` belongs in `ProjectRepository` since it queries the `projects` table.
- `getMetadataByCompanyId` belongs in `ProjectRepository` as a lightweight variant of existing `getByCompanyId`.

---

### Sub-phase 5.2: Create CompanyMembersRepository

**Files:**
- `lib/features/projects/data/repositories/company_members_repository.dart` (NEW)
- `lib/features/projects/data/repositories/repositories.dart` (EDIT — barrel export)
- `lib/features/projects/data/models/assignable_member.dart` (NEW)

**Agent**: backend-data-layer-agent

**What:**

1. **Extract `AssignableMember` model** from `project_assignment_provider.dart` (line 9-17) into a standalone model file at `lib/features/projects/data/models/assignable_member.dart`. The class in the provider file becomes a re-export or import from the model file. This is needed because the model will be used by both the repository and the provider.

2. **Create `CompanyMembersRepository`** with one method:
   - `getApprovedMembers(String companyId)` — wraps the Supabase query currently at `project_setup_screen.dart:181-196`:
     ```
     Supabase.instance.client.from('user_profiles').select('id, display_name, role')
       .eq('company_id', companyId).eq('status', 'approved')
     ```
   - Returns `List<AssignableMember>`.
   - Handles safe casting (the FIX 5 pattern from line 190).

3. **Update barrel export.**

**Verification:** `pwsh -Command "flutter analyze"` — no new warnings.

**Why a separate repo:** `user_profiles` is an auth-domain table accessed via Supabase (not local SQLite). It doesn't fit in `ProjectRepository` or `ProjectAssignmentRepository`. A small dedicated repository keeps the Supabase import isolated from presentation.

---

### Sub-phase 5.3: Create Use Cases

**Files:**
- `lib/features/projects/domain/use_cases/delete_project_use_case.dart` (NEW)
- `lib/features/projects/domain/use_cases/load_assignments_use_case.dart` (NEW)
- `lib/features/projects/domain/use_cases/fetch_remote_projects_use_case.dart` (NEW)
- `lib/features/projects/domain/use_cases/load_company_members_use_case.dart` (NEW)

**Agent**: backend-data-layer-agent

**What:**

1. **`DeleteProjectUseCase`**
   - Dependencies: `ProjectRepository`, `ProjectRemoteDatasource`, `DatabaseService`, `SoftDeleteService` factory or provider
   - Method: `Future<DeleteProjectResult> call({required String projectId, required String currentUserId, required bool isAdmin})`
   - Extracts lines 542-620 from `ProjectProvider.deleteProject`:
     - Step 1: Auth check via `projectRepository.getCreatedByUserId(projectId)` (replaces raw DB query at line 555)
     - Step 2: Remote soft-delete via `_remoteDatasource.softDeleteProject(projectId)` (see below)
     - Step 3: Local cascade via `SoftDeleteService.cascadeSoftDeleteProject`
   - Returns a result object with `success`, `error`, and `rpcSucceeded` fields
   - **CRITICAL:** Preserve exact authorization logic and cascade order. The RPC must fire BEFORE local cascade.

   **ProjectRemoteDatasource interface** (domain layer, keeps Supabase out of use case):
   - Create `lib/features/projects/domain/repositories/project_remote_datasource.dart`:
     ```dart
     /// Domain-layer interface for remote project operations.
     /// Keeps Supabase imports out of use cases.
     abstract class ProjectRemoteDatasource {
       /// Soft-delete a project via remote RPC.
       Future<void> softDeleteProject(String projectId);
     }
     ```
   - Create `lib/features/projects/data/datasources/remote/project_remote_datasource_impl.dart`:
     ```dart
     import 'package:supabase_flutter/supabase_flutter.dart';
     import 'package:construction_inspector/features/projects/domain/repositories/project_remote_datasource.dart';

     class ProjectRemoteDatasourceImpl implements ProjectRemoteDatasource {
       final SupabaseClient _client;
       ProjectRemoteDatasourceImpl(this._client);

       @override
       Future<void> softDeleteProject(String projectId) async {
         await _client.rpc('admin_soft_delete_project', params: {'p_project_id': projectId});
       }
     }
     ```
   - The use case calls `_remoteDatasource.softDeleteProject(projectId)` instead of `Supabase.instance.client.rpc(...)` directly.

2. **`LoadAssignmentsUseCase`**
   - Dependencies: `ProjectAssignmentRepository`, `SyncedProjectRepository`
   - Method: `Future<AssignmentState> call(String userId)`
   - Extracts lines 221-249 from `ProjectProvider.loadAssignments`:
     - Gets assigned project IDs via `projectAssignmentRepository.getAssignedProjectIds(userId)` (already exists!)
     - Gets synced project unassigned_at map via `syncedProjectRepository.getUnassignedAtMap()`
   - Returns `AssignmentState` record/class with `Set<String> assignedProjectIds` and `Map<String, String?> syncedProjectUnassignedAt`

3. **`FetchRemoteProjectsUseCase`**
   - Dependencies: `ProjectRepository`, `SyncedProjectRepository`
   - Method: `Future<FetchRemoteProjectsResult> call(String companyId)`
   - Extracts lines 680-745 from `ProjectProvider.fetchRemoteProjects`:
     - Reloads local projects via `projectRepository.getByCompanyId(companyId)`
     - Gets enrolled IDs via `syncedProjectRepository.getAll()` -> map to set
     - Gets all project metadata via `projectRepository.getMetadataByCompanyId(companyId)`
     - Computes remote-only projects (all minus enrolled)
   - Returns result with `List<Project> localProjects`, `List<Project> remoteProjects`, `Set<String> allKnownProjectIds`

4. **`LoadCompanyMembersUseCase`**
   - Dependencies: `CompanyMembersRepository`
   - Method: `Future<List<AssignableMember>> call(String companyId)`
   - Thin wrapper — but exists so `ProjectSetupScreen` doesn't import a repository directly
   - Can add caching later (company members rarely change mid-session)

**Verification:** `pwsh -Command "flutter analyze"` — no new warnings.

---

### Sub-phase 5.4: Rewire ProjectProvider to Use Cases

**Files:**
- `lib/features/projects/presentation/providers/project_provider.dart` (EDIT)

**Agent**: backend-data-layer-agent

**What:**

1. **Add use case dependencies** to `ProjectProvider` constructor:
   - `DeleteProjectUseCase`
   - `LoadAssignmentsUseCase`
   - `FetchRemoteProjectsUseCase`
   - All optional with late initialization or nullable, to avoid breaking existing construction sites before Phase 5.5 wires DI.

2. **Replace `deleteProject` body** (lines 542-620):
   - Delegate to `DeleteProjectUseCase.call(projectId: id, currentUserId: currentUserId, isAdmin: isAdmin)`
   - Keep only the state management part: remove from `_projects`, clear `_selectedProject`, clear settings, set `_isLoading`/`_error`, `notifyListeners()`
   - **Remove:** `import 'package:supabase_flutter/supabase_flutter.dart'` (if no other usage remains)
   - **Remove:** `import 'package:construction_inspector/services/soft_delete_service.dart'`

3. **Replace `loadAssignments` body** (lines 221-249):
   - Delegate to `LoadAssignmentsUseCase.call(userId)`
   - Assign result fields to `_assignedProjectIds` and `_syncedProjectUnassignedAt`
   - Call `_buildMergedView()` and `notifyListeners()`
   - **Remove:** `DatabaseService dbService` parameter — use case carries its own deps
   - **BREAKING CHANGE:** All callers of `loadAssignments` must be updated (Sub-phase 5.5)

4. **Replace `fetchRemoteProjects` body** (lines 680-745):
   - Delegate to `FetchRemoteProjectsUseCase.call(_companyId!)`
   - Assign result fields to `_projects`, `_remoteProjects`, `_allKnownProjectIds`
   - Call `_buildMergedView()` and `notifyListeners()`

5. **Replace `enrollProject` and `unenrollProject`** (lines 253-286):
   - Delegate to `SyncedProjectRepository.enroll()` and `.unenroll()`
   - Remove `DatabaseService dbService` parameter
   - **BREAKING CHANGE:** All callers must be updated (Sub-phase 5.5)

6. **Remove `_databaseService` field** if no remaining direct DB access.

7. **Remove `import 'package:sqflite/sqflite.dart'`** if no remaining usage.

**Verification:** `pwsh -Command "flutter analyze"` — expect errors from callers not yet updated (fixed in 5.5).

**Net effect on ProjectProvider:** ~250 lines removed (deleteProject: ~80, loadAssignments: ~30, fetchRemoteProjects: ~65, enrollProject: ~15, unenrollProject: ~15, imports/fields: ~15). Provider drops from ~800 to ~550 lines. Remaining code is pure state management + UI getters.

---

### Sub-phase 5.5: Rewire ProjectSetupScreen and Fix All Callers

**Files:**
- `lib/features/projects/presentation/screens/project_setup_screen.dart` (EDIT)
- `lib/features/projects/presentation/providers/project_assignment_provider.dart` (EDIT)
- `lib/main.dart` (EDIT — DI wiring)
- Any other callers of `loadAssignments`, `enrollProject`, `unenrollProject` (search required)

**Agent**: frontend-flutter-specialist-agent

**What:**

1. **Fix `project_setup_screen.dart` line 181-196** (Supabase direct query):
   - Replace `Supabase.instance.client.from('user_profiles').select(...)` with `LoadCompanyMembersUseCase.call(companyId)`
   - Inject `LoadCompanyMembersUseCase` via `context.read<>()` or pass through provider
   - Remove `import 'package:supabase_flutter/supabase_flutter.dart'` from this file

2. **Fix `project_setup_screen.dart` line 985-993** (raw DB insert into synced_projects):
   - Replace `db.insert('synced_projects', ...)` with `context.read<ProjectProvider>().enrollProject(projectId)`
   - Or call `SyncedProjectRepository.enroll()` directly via provider
   - Remove `import 'package:sqflite/sqflite.dart'` from this file if no other usage

3. **Update `project_assignment_provider.dart`:**
   - Change `AssignableMember` class to import from `data/models/assignable_member.dart`
   - Keep re-export for backward compatibility if other files import it from here

4. **Update all callers** of `ProjectProvider.loadAssignments(userId, dbService)`:
   - Search for `.loadAssignments(` across codebase
   - Update signature to `.loadAssignments(userId)` (no more dbService param)

5. **Update all callers** of `ProjectProvider.enrollProject(projectId, dbService)` and `.unenrollProject(projectId, dbService)`:
   - Search for `.enrollProject(` and `.unenrollProject(` across codebase
   - Update signature to `.enrollProject(projectId)` (no more dbService param)

6. **Wire DI in `main.dart`:**
   - Create `SyncedProjectRepository` and `CompanyMembersRepository` instances
   - Create use case instances with their dependencies
   - Pass use cases to `ProjectProvider` constructor
   - Register `LoadCompanyMembersUseCase` as a provider (or make accessible through existing provider)

**Verification:** `pwsh -Command "flutter analyze"` — zero errors/warnings.

---

### Sub-phase 5.6: Update Existing Tests

**Files:**
- `test/features/projects/data/repositories/project_repository_test.dart` (EDIT)
- `test/features/projects/presentation/providers/project_provider_merged_view_test.dart` (EDIT)
- `test/features/projects/presentation/providers/project_provider_tabs_test.dart` (EDIT)
- `test/features/projects/presentation/providers/project_assignment_provider_test.dart` (EDIT)
- `test/features/projects/domain/use_cases/delete_project_use_case_test.dart` (NEW)
- `test/features/projects/domain/use_cases/load_assignments_use_case_test.dart` (NEW)
- `test/features/projects/domain/use_cases/fetch_remote_projects_use_case_test.dart` (NEW)
- `test/features/projects/data/repositories/synced_project_repository_test.dart` (NEW)

**Agent**: qa-testing-agent

**What:**

1. **Fix existing `project_provider_merged_view_test.dart`:**
   - Update `ProjectProvider` construction to pass use case mocks
   - Update `loadAssignments` calls to new signature (no dbService)
   - Ensure all existing assertions still pass

2. **Fix existing `project_provider_tabs_test.dart`:**
   - Same pattern — update constructor and method signatures

3. **Fix existing `project_assignment_provider_test.dart`:**
   - Update `AssignableMember` import path if changed

4. **New `delete_project_use_case_test.dart`:**
   - Test authorization: creator can delete, non-creator non-admin cannot
   - Test RPC failure path: local cascade still runs, rpcSucceeded=false
   - Test project not found: returns error
   - Test successful path: RPC + cascade both fire in order
   - Mock: `ProjectRepository`, `SoftDeleteService`, Supabase client (or abstract the RPC call)

5. **New `load_assignments_use_case_test.dart`:**
   - Test returns correct assigned IDs and unassigned_at map
   - Test empty state (no assignments, no synced_projects)

6. **New `fetch_remote_projects_use_case_test.dart`:**
   - Test merging: enrolled projects excluded from remote list
   - Test allKnownProjectIds includes both enrolled and unenrolled
   - Test null updated_at handling (fallback to DateTime.now)

7. **New `synced_project_repository_test.dart`:**
   - Test enroll/unenroll CRUD
   - Test getAll and getUnassignedAtMap

**Verification:** `pwsh -Command "flutter test"` — all tests pass (existing + new).

---

### Layer Violation Resolution Summary

| # | Location | Violation | Fixed In | Resolution |
|---|----------|-----------|----------|------------|
| 1 | `project_provider.dart:223` | Raw DB query on project_assignments | 5.4 | Delegates to `LoadAssignmentsUseCase` -> `ProjectAssignmentRepository.getAssignedProjectIds()` (already exists) |
| 2 | `project_provider.dart:255` | Raw DB query on synced_projects | 5.4 | Delegates to `SyncedProjectRepository.enroll()` / `.unenroll()` / `.getUnassignedAtMap()` |
| 3 | `project_provider.dart:275` | Raw DB query on projects | 5.4 | Delegates to `FetchRemoteProjectsUseCase` -> `ProjectRepository.getMetadataByCompanyId()` |
| 4 | `project_provider.dart:585` | Direct `Supabase.instance.client.rpc()` | 5.3/5.4 | Moved into `DeleteProjectUseCase` |
| 5 | `project_setup_screen.dart:181` | Direct `Supabase.instance.client.from('user_profiles').select()` | 5.5 | Replaced with `LoadCompanyMembersUseCase` -> `CompanyMembersRepository` |
| 6 | `project_setup_screen.dart:985` | `dbService.database` raw insert into synced_projects | 5.5 | Replaced with `SyncedProjectRepository.enroll()` via provider |

### Risk Notes

- **DeleteProjectUseCase is security-critical.** The authorization check (creator OR admin) and the cascade order (RPC before local) must be preserved exactly. Review the use case test coverage before merging.
- **Supabase RPC abstraction:** `DeleteProjectUseCase` will still import `supabase_flutter` directly for the RPC call. A future phase could abstract this behind a `ProjectRemoteService` interface, but that is out of scope for Phase 5.
- **Breaking signature changes** in `loadAssignments`, `enrollProject`, `unenrollProject` require a codebase-wide search for all callers. Sub-phase 5.5 must not skip any.
- **`AssignableMember` extraction** may break imports in files that import it from `project_assignment_provider.dart`. The barrel export must maintain backward compatibility.


---

## Phase 6: Forms & Entries Domain Layer

> **Goal**: Extract domain interfaces (abstract repository contracts) and use cases for the forms and entries features. Providers switch from depending on concrete repositories to depending on abstract interfaces. Cross-feature imports (e.g., `EntryExportProvider` consuming `FormExportProvider`) go through domain-layer interfaces.

> **Prerequisite**: Phases 1-5 complete (shared domain infrastructure, base use case classes, and other features already migrated).

---

### Sub-phase 6.1: Forms Domain — Repository Interfaces

**Files:**
- Create: `lib/features/forms/domain/domain.dart`
- Create: `lib/features/forms/domain/repositories/form_response_repository.dart`
- Create: `lib/features/forms/domain/repositories/inspector_form_repository.dart`
- Create: `lib/features/forms/domain/repositories/form_export_repository.dart`
- Create: `lib/features/forms/domain/repositories/repositories.dart`
- Modify: `lib/features/forms/data/repositories/form_response_repository.dart`
- Modify: `lib/features/forms/data/repositories/inspector_form_repository.dart`
- Modify: `lib/features/forms/data/repositories/form_export_repository.dart`

**Agent**: `backend-data-layer-agent`

**What to do:**

1. Create `lib/features/forms/domain/repositories/form_response_repository.dart`:
   - Abstract class `FormResponseRepository` with all public methods from the current concrete `FormResponseRepository`:
     - `createResponse(FormResponse)`, `getResponseById(String)`, `getResponsesForForm(String)`, `getResponsesForEntry(String)`, `getResponsesForProject(String)`, `getResponsesByStatus(FormResponseStatus)`, `getResponsesByProjectAndStatus(String, FormResponseStatus)`, `updateResponse(FormResponse)`, `submitResponse(String)`, `markAsExported(String)`, `deleteResponse(String)`, `deleteResponsesForEntry(String)`, `getResponseCountForForm(String)`, `getResponseCountForEntry(String)`, `getResponseCountForProject(String)`, `getRecentResponses({required String formId, String? projectId, int limit})`, `getById(String)`, `getAll()`, `save(FormResponse)`, `delete(String)`
   - Return types match existing: `RepositoryResult<FormResponse>`, `RepositoryResult<List<FormResponse>>`, etc.
   - Import models from `lib/features/forms/data/models/models.dart` (models stay in data layer)

2. Create `lib/features/forms/domain/repositories/inspector_form_repository.dart`:
   - Abstract class `InspectorFormRepository` with:
     - `createForm(InspectorForm)`, `getFormById(String)`, `getFormsForProject(String)`, `getBuiltinForms()`, `updateForm(InspectorForm)`, `deleteForm(String)`, `getAll()`, `getById(String)`, `save(InspectorForm)`, `delete(String)`

3. Create `lib/features/forms/domain/repositories/form_export_repository.dart`:
   - Abstract class `FormExportRepository` with:
     - `create(FormExport)`, `getById(String)`, `getAll()`, `save(FormExport)`, `delete(String)`, `getByProjectId(String)`, `getByEntryId(String)`, `getByFormResponseId(String)`

4. Rename concrete repositories to `*Impl` and make them `implements` their interface:
   - `FormResponseRepository` (concrete, in data/) -> rename to `FormResponseRepositoryImpl implements FormResponseRepository`
   - `InspectorFormRepository` (concrete, in data/) -> rename to `InspectorFormRepositoryImpl implements InspectorFormRepository`
   - `FormExportRepository` (concrete, in data/) -> rename to `FormExportRepositoryImpl implements FormExportRepository`
   - Keep existing `implements BaseRepository<T>` — the interface extends or mirrors it
   - Update all imports/references to concrete classes throughout the codebase (main.dart, DI files, tests)

5. Create barrel exports:
   - `lib/features/forms/domain/repositories/repositories.dart` — exports all 3 interfaces
   - `lib/features/forms/domain/domain.dart` — exports `repositories/repositories.dart`

**WHY interfaces live in forms/domain/**: `FormResponseRepository` is consumed by 5 providers across 4 features. The interface in `forms/domain/` is the canonical import point for cross-feature consumers. This avoids circular dependencies — other features depend on the interface, not the concrete data layer.

---

### Sub-phase 6.2: Forms Domain — Use Cases

**Files:**
- Create: `lib/features/forms/domain/usecases/calculate_form_field_use_case.dart`
- Create: `lib/features/forms/domain/usecases/normalize_proctor_row_use_case.dart`
- Create: `lib/features/forms/domain/usecases/export_form_use_case.dart`
- Create: `lib/features/forms/domain/usecases/load_form_responses_use_case.dart`
- Create: `lib/features/forms/domain/usecases/save_form_response_use_case.dart`
- Create: `lib/features/forms/domain/usecases/submit_form_response_use_case.dart`
- Create: `lib/features/forms/domain/usecases/delete_form_response_use_case.dart`
- Create: `lib/features/forms/domain/usecases/load_forms_use_case.dart`
- Create: `lib/features/forms/domain/usecases/manage_documents_use_case.dart`
- Create: `lib/features/forms/domain/usecases/usecases.dart`
- Modify: `lib/features/forms/domain/domain.dart`

**Agent**: `backend-data-layer-agent`

**What to do:**

1. **CalculateFormFieldUseCase** — extracts lines 406-429 from `InspectorFormProvider`:
   - Deps: `FormResponseRepository`, `FormCalculatorRegistry`
   - Method: `Future<FormResponse?> call(String responseId, String rowType)`
   - Logic: load response, look up calculator from registry, get empty row, append to response data, save via repository
   - This is real business logic (calculator dispatch) — not a pass-through

2. **NormalizeProctorRowUseCase** — extracts lines 370-397 from `InspectorFormProvider`:
   - Deps: `FormResponseRepository`
   - Method: `Future<FormResponse?> call({required String responseId, required Map<String, dynamic> row})`
   - Logic: normalize weight data, remove chart_type, parse weights_20_10, set wet_soil_mold_g, append to proctor rows, save
   - Mark with `@Deprecated` matching the existing annotation
   - This is real business logic (MDOT 0582B normalization) — not a pass-through

3. **ExportFormUseCase** — extracts logic from `FormExportProvider.exportFormToPdf`:
   - Deps: `FormResponseRepository`, `FormExportRepository`, `FormPdfService`
   - Method: `Future<String?> call(String responseId, {String? currentUserId})`
   - Logic: fetch response, generate PDF bytes, save temp file, create FormExport metadata row
   - SEC: Filename generation stays inline (no user input in filename)

4. **Pass-through use cases** (LoadFormResponsesUseCase, SaveFormResponseUseCase, SubmitFormResponseUseCase, DeleteFormResponseUseCase, LoadFormsUseCase):
   - Each wraps a single repository method
   - Deps: the relevant `FormResponseRepository` or `InspectorFormRepository`
   - These exist for interface consistency — providers depend on use cases, not repositories

5. **ManageDocumentsUseCase** — extracts logic from `DocumentProvider`:
   - Deps: `FormResponseRepository`, `DocumentRepository`, `DocumentService`
   - Methods: `loadDocuments(projectId, {formType})`, `loadEntryDocuments(entryId)`, `attachDocument(...)`, `deleteDocument(id)`
   - NOTE: `FormResponseSummary` class moves into this use case file or stays in the provider (it's a presentation mapping). Decision: keep `FormResponseSummary` in presentation since it's a view model.

6. Barrel export `usecases.dart` and update `domain.dart`.

---

### Sub-phase 6.3: Forms Providers — Switch to Use Cases

**Files:**
- Modify: `lib/features/forms/presentation/providers/inspector_form_provider.dart`
- Modify: `lib/features/forms/presentation/providers/form_export_provider.dart`
- Modify: `lib/features/forms/presentation/providers/document_provider.dart`
- Modify: `lib/features/forms/presentation/providers/providers.dart`

**Agent**: `frontend-flutter-specialist-agent`

**What to do:**

1. **InspectorFormProvider** — replace repository + registry deps with use cases:
   - Constructor changes from `(InspectorFormRepository, FormResponseRepository, FormCalculatorRegistry)` to accepting use cases: `LoadFormsUseCase`, `LoadFormResponsesUseCase`, `SaveFormResponseUseCase`, `SubmitFormResponseUseCase`, `DeleteFormResponseUseCase`, `CalculateFormFieldUseCase`, `NormalizeProctorRowUseCase`
   - Pass-through methods (loadFormsForProject, loadResponsesForEntry, etc.) delegate to use cases
   - `appendRow()` delegates to `CalculateFormFieldUseCase`
   - `appendMdot0582bProctorRow()` delegates to `NormalizeProctorRowUseCase`
   - State management (list caching, notifyListeners, canWrite guards) stays in provider
   - Provider still owns `_forms`, `_responses`, `_isLoading`, `_error` state

2. **FormExportProvider** — replace repos + service with use case:
   - Constructor changes to accept `ExportFormUseCase`
   - `exportFormToPdf()` delegates to use case, retains `_isExporting` / `_errorMessage` state management

3. **DocumentProvider** — replace repos + service with use case:
   - Constructor changes to accept `ManageDocumentsUseCase`
   - All methods delegate, provider retains list state + loading flags
   - `FormResponseSummary` stays in this file (view model, not domain)

4. Update barrel export `providers.dart` if needed.

**IMPORTANT**: Do NOT change the public API of any provider. Screens and widgets calling these providers must not need changes. Only constructor signatures change (wired in `main.dart` or provider setup).

---

### Sub-phase 6.4: Entries Domain — Repository Interfaces

**Files:**
- Create: `lib/features/entries/domain/domain.dart`
- Create: `lib/features/entries/domain/repositories/daily_entry_repository.dart`
- Create: `lib/features/entries/domain/repositories/entry_export_repository.dart`
- Create: `lib/features/entries/domain/repositories/document_repository.dart`
- Create: `lib/features/entries/domain/repositories/repositories.dart`
- Modify: `lib/features/entries/data/repositories/daily_entry_repository.dart`
- Modify: `lib/features/entries/data/repositories/entry_export_repository.dart`
- Modify: `lib/features/entries/data/repositories/document_repository.dart`

**Agent**: `backend-data-layer-agent`

**What to do:**

1. Create `DailyEntryRepository` abstract class with all public methods from the current concrete `DailyEntryRepository`:
   - All `ProjectScopedRepository<DailyEntry>` methods
   - `getByDate(projectId, date)`, `getByDateRange(projectId, start, end)`, `getByLocationId(locationId)`, `getByStatus(projectId, status)`, `getDatesWithEntries(projectId)`, `updateStatus(id, status)`, `submit(id, signature)`, `deleteByProjectId(projectId)`, `getCountByDate(projectId, date)`, `insertAll(entries)`, `getLastEntrySafetyFields(projectId)`, `getDraftEntries(projectId)`, `batchSubmit(entryIds)`, `undoSubmission(entryId)`

2. Create `EntryExportRepository` abstract class:
   - `getById(String)`, `getAll()`, `save(EntryExport)`, `delete(String)`, `create(EntryExport)`, `getByProjectId(String)`, `getByEntryId(String)`

3. Create `DocumentRepository` abstract class:
   - `getById(String)`, `getAll()`, `save(Document)`, `delete(String)`, `create(Document)`, `update(Document)`, `getByProjectId(String)`, `getByEntryId(String)`, `getCountByEntryId(String)`
   - Include `static const allowedFileTypes` or move validation logic to a use case

4. Rename concrete repositories to `*Impl` and make them implement their interfaces:
   - `DailyEntryRepository` (concrete, in data/) -> rename to `DailyEntryRepositoryImpl implements DailyEntryRepository`
   - `EntryExportRepository` (concrete, in data/) -> rename to `EntryExportRepositoryImpl implements EntryExportRepository`
   - `DocumentRepository` (concrete, in data/) -> rename to `DocumentRepositoryImpl implements DocumentRepository`
   - Update all imports/references to concrete classes throughout the codebase (main.dart, DI files, tests)

5. Barrel exports: `repositories.dart` -> `domain.dart`.

---

### Sub-phase 6.5: Entries Domain — Use Cases

**Files:**
- Create: `lib/features/entries/domain/usecases/submit_entry_use_case.dart`
- Create: `lib/features/entries/domain/usecases/undo_submit_entry_use_case.dart`
- Create: `lib/features/entries/domain/usecases/batch_submit_entries_use_case.dart`
- Create: `lib/features/entries/domain/usecases/export_entry_use_case.dart`
- Create: `lib/features/entries/domain/usecases/load_entries_use_case.dart`
- Create: `lib/features/entries/domain/usecases/manage_entry_use_case.dart`
- Create: `lib/features/entries/domain/usecases/calendar_entries_use_case.dart`
- Create: `lib/features/entries/domain/usecases/usecases.dart`
- Modify: `lib/features/entries/domain/domain.dart`

**Agent**: `backend-data-layer-agent`

**What to do:**

1. **SubmitEntryUseCase**:
   - Deps: `DailyEntryRepository`
   - Method: `Future<RepositoryResult<void>> call(String id, String signature)`
   - Delegates to `repository.submit(id, signature)`

2. **UndoSubmitEntryUseCase**:
   - Deps: `DailyEntryRepository`
   - Method: `Future<RepositoryResult<void>> call(String entryId)`
   - Delegates to `repository.undoSubmission(entryId)`

3. **BatchSubmitEntriesUseCase**:
   - Deps: `DailyEntryRepository`
   - Method: `Future<RepositoryResult<DateTime>> call(List<String> entryIds)`
   - Delegates to `repository.batchSubmit(entryIds)`

4. **ExportEntryUseCase** — extracts logic from `EntryExportProvider.exportAllFormsForEntry`:
   - Deps: `DailyEntryRepository`, `EntryExportRepository`, `FormResponseRepository` (cross-feature import from forms/domain/), `ExportFormUseCase` (cross-feature import from forms/domain/)
   - Method: `Future<List<String>> call(String entryId, {String? currentUserId})`
   - Logic: load entry, load form responses for entry, delegate each to ExportFormUseCase, create EntryExport metadata row
   - **Cross-feature**: imports `FormResponseRepository` from `forms/domain/repositories/` and `ExportFormUseCase` from `forms/domain/usecases/`

5. **Pass-through use cases** (LoadEntriesUseCase, ManageEntryUseCase, CalendarEntriesUseCase):
   - Wrap repository methods for CRUD, date queries, calendar markers
   - CalendarEntriesUseCase: `getDatesWithEntries(projectId)`, `getByDate(projectId, date)`

6. Barrel export `usecases.dart` and update `domain.dart`.

---

### Sub-phase 6.6: Entries Providers — Switch to Use Cases

**Files:**
- Modify: `lib/features/entries/presentation/providers/daily_entry_provider.dart`
- Modify: `lib/features/entries/presentation/providers/entry_export_provider.dart`
- Modify: `lib/features/entries/presentation/providers/calendar_format_provider.dart`
- Modify: `lib/features/entries/presentation/providers/providers.dart`

**Agent**: `frontend-flutter-specialist-agent`

**What to do:**

1. **DailyEntryProvider** — replace `DailyEntryRepository` with use cases:
   - Constructor changes: accept `LoadEntriesUseCase`, `ManageEntryUseCase`, `SubmitEntryUseCase`, `UndoSubmitEntryUseCase`, `BatchSubmitEntriesUseCase`, `CalendarEntriesUseCase`
   - NOTE: `DailyEntryProvider extends BaseListProvider<DailyEntry, DailyEntryRepository>`. The generic parameter `R extends ProjectScopedRepository<T>` must now accept the interface: `BaseListProvider<DailyEntry, DailyEntryRepository>` — verify `DailyEntryRepository extends ProjectScopedRepository<DailyEntry>` in the interface definition (sub-phase 6.4)
   - All state management (date maps, pagination, selected date) stays in provider
   - Pass-through methods delegate to use cases

2. **EntryExportProvider** — replace deps with use case:
   - Constructor changes to accept `ExportEntryUseCase`
   - `exportAllFormsForEntry()` delegates to use case
   - Retains `_isExporting`, `_exportedPaths`, `_errorMessage` state
   - **Removes direct dependency on `FormExportProvider`** — cross-feature coordination now handled by `ExportEntryUseCase` in the domain layer

3. **CalendarFormatProvider** — no domain dependencies:
   - This provider has zero repository deps (pure UI state + SharedPreferences)
   - No use cases needed. Leave as-is.
   - Confirm in barrel export it's still exported

4. Update barrel export `providers.dart`.

**Controllers stay in presentation**: `EntryEditingController`, `ContractorEditingController`, `PhotoAttachmentManager`, `FormAttachmentManager`, `PdfDataBuilder` are UI coordination logic. They remain in `presentation/controllers/` unchanged.

---

### Sub-phase 6.7: Provider Wiring Update

**Files:**
- Modify: `lib/main.dart` (or wherever providers are registered with `MultiProvider`/`ChangeNotifierProvider`)

**Agent**: `frontend-flutter-specialist-agent`

**What to do:**

1. Update provider registration to construct use cases and inject them:
   - `InspectorFormProvider` now takes use cases instead of repositories
   - `FormExportProvider` now takes `ExportFormUseCase`
   - `DocumentProvider` now takes `ManageDocumentsUseCase`
   - `DailyEntryProvider` now takes entry use cases
   - `EntryExportProvider` now takes `ExportEntryUseCase`

2. **Ordering constraint preserved**: `FormExportProvider` (or its underlying `ExportFormUseCase`) must still be created before `EntryExportProvider` / `ExportEntryUseCase`. Since `ExportEntryUseCase` takes `ExportFormUseCase` as a constructor param (not `context.read`), the ordering is now compile-time enforced instead of runtime-dependent.

3. Verify `CalendarFormatProvider` registration unchanged (no deps to update).

---

### Sub-phase 6.8: Tests — Domain Layer

**Files:**
- Create: `test/features/forms/domain/usecases/calculate_form_field_use_case_test.dart`
- Create: `test/features/forms/domain/usecases/normalize_proctor_row_use_case_test.dart`
- Create: `test/features/forms/domain/usecases/export_form_use_case_test.dart`
- Create: `test/features/entries/domain/usecases/submit_entry_use_case_test.dart`
- Create: `test/features/entries/domain/usecases/undo_submit_entry_use_case_test.dart`
- Create: `test/features/entries/domain/usecases/batch_submit_entries_use_case_test.dart`
- Create: `test/features/entries/domain/usecases/export_entry_use_case_test.dart`

**Agent**: `qa-testing-agent`

**What to do:**

1. **CalculateFormFieldUseCase tests** (highest value — real business logic):
   - Mock `FormResponseRepository` and `FormCalculatorRegistry`
   - Test: returns null when response not found
   - Test: returns null when no calculator registered for form type
   - Test: appends proctor_rows via emptyProctorRow()
   - Test: appends test_rows via emptyTestRow()
   - Test: returns null for unknown rowType

2. **NormalizeProctorRowUseCase tests** (highest value — MDOT-specific logic):
   - Test: removes chart_type from row
   - Test: trims and filters empty weights_20_10 values
   - Test: sets wet_soil_mold_g from last weight value
   - Test: handles empty weights list
   - Test: appends to existing proctor rows

3. **ExportFormUseCase tests**:
   - Mock `FormResponseRepository`, `FormExportRepository`, `FormPdfService`
   - Test: returns null when response not found
   - Test: returns null when PDF generation fails
   - Test: creates FormExport metadata row on success
   - Test: returns saved file path on success

4. **Entry use case tests** (submit, undo, batch):
   - Mock `DailyEntryRepository`
   - Test: delegates to repository correctly
   - Test: batch submit with empty list returns failure
   - Test: undo on non-submitted entry returns failure

5. **ExportEntryUseCase tests** (cross-feature):
   - Mock `DailyEntryRepository`, `EntryExportRepository`, `FormResponseRepository`, `ExportFormUseCase`
   - Test: returns empty list when entry not found
   - Test: exports each form response via ExportFormUseCase
   - Test: creates EntryExport metadata row with first PDF path

6. **Existing tests must still pass**:
   - `test/features/forms/data/repositories/form_export_repository_test.dart`
   - `test/features/forms/data/repositories/form_response_repository_test.dart`
   - `test/features/entries/data/repositories/document_repository_test.dart`
   - `test/features/entries/data/repositories/entry_export_repository_test.dart`
   - `test/features/entries/presentation/providers/calendar_format_provider_test.dart`

**Verification commands:**
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
```

---

### Dependency Graph

```
Sub-phase 6.1 (forms repo interfaces)
    │
    ├──► Sub-phase 6.2 (forms use cases) ──► Sub-phase 6.3 (forms providers)
    │                                                │
    │                                                ▼
    │                                        Sub-phase 6.7 (wiring)
    │                                                ▲
Sub-phase 6.4 (entries repo interfaces)              │
    │                                                │
    ├──► Sub-phase 6.5 (entries use cases) ─► Sub-phase 6.6 (entries providers)
    │         │
    │         └── depends on 6.1 + 6.2 (cross-feature: FormResponseRepository, ExportFormUseCase)
    │
    └──► Sub-phase 6.8 (tests) — runs after 6.7

Parallelizable: 6.1 and 6.4 can run in parallel.
Parallelizable: 6.2 and 6.4 can run in parallel (6.2 only needs 6.1).
Sequential: 6.5 depends on 6.1 + 6.2 + 6.4.
Sequential: 6.3 depends on 6.2; 6.6 depends on 6.5.
Sequential: 6.7 depends on 6.3 + 6.6.
Sequential: 6.8 depends on 6.7.
```

### File Count Summary

| Sub-phase | New | Modified | Agent |
|-----------|-----|----------|-------|
| 6.1 | 5 | 3 | backend-data-layer-agent |
| 6.2 | 10 | 1 | backend-data-layer-agent |
| 6.3 | 0 | 4 | frontend-flutter-specialist-agent |
| 6.4 | 5 | 3 | backend-data-layer-agent |
| 6.5 | 8 | 1 | backend-data-layer-agent |
| 6.6 | 0 | 4 | frontend-flutter-specialist-agent |
| 6.7 | 0 | 1 | frontend-flutter-specialist-agent |
| 6.8 | 7 | 0 | qa-testing-agent |
| **Total** | **35** | **17** | |


---

# Clean Architecture Refactor — Phase 7: Remaining Features + Cleanup

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Add domain layer scaffolding for dashboard, settings, weather, toolbox, pdf. Fix trash_screen layer violation. Fix remaining `catch(_)` blocks. Dead code removal. Final verification.

---

## Phase 7: Remaining Features + Cleanup

### Sub-phase 7.1: Settings — TrashRepository + Fix Layer Violation
**Files:**
- Create: `lib/features/settings/data/repositories/trash_repository.dart`
- Create: `lib/features/settings/domain/domain.dart` (barrel)
- Modify: `lib/features/settings/presentation/screens/trash_screen.dart`
- Modify: `lib/features/settings/settings.dart` (barrel update)
**Agent:** `backend-data-layer-agent`

#### Step 7.1.1: Create TrashRepository
Create `lib/features/settings/data/repositories/trash_repository.dart` that encapsulates the raw DB queries currently in `trash_screen.dart`.

The repository must expose:
```dart
class TrashRepository {
  final DatabaseService _dbService;
  TrashRepository(this._dbService);

  /// Fetch all soft-deleted records grouped by table name.
  /// [tables] — which tables to scan.
  /// [adminMode] — if false, filters by [userId] (deleted_by).
  Future<Map<String, List<Map<String, dynamic>>>> getDeletedItems({
    required Map<String, String> tables,
    required bool adminMode,
    String? userId,
  });
}
```

**WHY:** `trash_screen.dart:54` and `:68` both call `_dbService.database` directly and run raw `database.query()` from the presentation layer. This violates the architecture rule: "Raw SQL in presentation layer → Move to repository/datasource layer."

Implementation details (extracted from `trash_screen.dart:65-99`):
- For each table key in `tables`, run `database.query(table, where: ..., orderBy: 'deleted_at DESC')`
- Admin mode: `where = 'deleted_at IS NOT NULL'`
- Non-admin mode: `where = 'deleted_at IS NOT NULL AND deleted_by = ?'` with `whereArgs: [userId]`
- Wrap each table query in `try/catch (e) { Logger.db(...) }` — tables may not exist
- Return `Map<String, List<Map<String, dynamic>>>` (only non-empty results)

#### Step 7.1.2: Update trash_screen.dart to use TrashRepository
In `lib/features/settings/presentation/screens/trash_screen.dart`:

1. Remove `import 'package:construction_inspector/core/database/database_service.dart';`
2. Add `import 'package:construction_inspector/features/settings/data/repositories/trash_repository.dart';`
3. Replace field `final _dbService = DatabaseService();` with `late final TrashRepository _trashRepository;`
4. In `_initService()` (line 53-57): replace the `_dbService.database` call with creating a `TrashRepository(DatabaseService())` and assigning to `_trashRepository`. Remove the `SoftDeleteService(database)` init that depends on raw DB — instead get the database from DatabaseService and pass to SoftDeleteService as before, but through the repository or keep SoftDeleteService init separate.

   Revised `_initService()`:
   ```dart
   Future<void> _initService() async {
     final dbService = DatabaseService();
     _trashRepository = TrashRepository(dbService);
     final database = await dbService.database;
     _softDeleteService = SoftDeleteService(database);
     _loadDeletedItems();
   }
   ```

5. In `_loadDeletedItems()` (lines 65-107): replace the entire raw DB query loop with:
   ```dart
   Future<void> _loadDeletedItems() async {
     setState(() => _isLoading = true);
     final auth = context.read<AuthProvider>();
     final grouped = await _trashRepository.getDeletedItems(
       tables: _tableLabels,
       adminMode: auth.isAdmin,
       userId: auth.userId,
     );
     if (mounted) {
       setState(() {
         _groupedItems = grouped;
         _isLoading = false;
       });
     }
   }
   ```

**WHY:** Eliminates both layer violations (lines 54 and 68). The presentation layer now only talks to a repository, never to raw DB.

#### Step 7.1.3: Create AdminRepository interface (Fix AdminProvider SupabaseClient violation)

`AdminProvider` currently receives raw `SupabaseClient` in its constructor — a layer violation (presentation depends on infrastructure).

1. Create `lib/features/settings/domain/repositories/admin_repository.dart`:
   ```dart
   /// Domain interface for admin operations.
   /// Eliminates AdminProvider's direct dependency on SupabaseClient.
   abstract class AdminRepository {
     Future<List<Map<String, dynamic>>> getPendingUsers(String companyId);
     Future<void> approveUser(String userId);
     Future<void> rejectUser(String userId);
     Future<void> updateUserRole(String userId, String role);
     // ... add other methods matching AdminProvider's current Supabase calls
   }
   ```

2. Rename existing `AdminRepository` (if one exists in data/) to `AdminRepositoryImpl implements AdminRepository`. If no concrete class exists yet, create `lib/features/settings/data/repositories/admin_repository_impl.dart`:
   ```dart
   class AdminRepositoryImpl implements AdminRepository {
     final SupabaseClient _client;
     AdminRepositoryImpl(this._client);
     // ... implement all methods by wrapping current Supabase calls from AdminProvider
   }
   ```

3. Update `AdminProvider` constructor: change `SupabaseClient` parameter to `AdminRepository`.

4. Update `auth_providers.dart` (or wherever `AdminProvider` is wired): create `AdminRepositoryImpl(supabaseClient)` and pass it to `AdminProvider`.

**WHY:** AdminProvider is the last provider directly importing `SupabaseClient`. This fix ensures zero presentation-layer files import Supabase.

#### Step 7.1.4: Create settings domain barrel
Create `lib/features/settings/domain/domain.dart`:
```dart
// Settings domain layer — currently empty (admin use cases stay in provider,
// theme is pure UI state). Placeholder for future use cases.
```

Update `lib/features/settings/settings.dart` barrel to export `domain/domain.dart`.

**WHY:** Every feature gets a `domain/` directory per the Clean Architecture spec, even if initially empty.

---

### Sub-phase 7.1B: Provider Dispose Sweep

**Goal:** Ensure ALL providers have proper `dispose()` overrides. Phase 3 added dispose() to 10 CRUD providers. This sub-phase covers the remaining providers listed below (19 entries).

**Agent:** `backend-data-layer-agent`

#### Already handled in Phase 3 (no action needed):
- LocationProvider
- PhotoProvider
- ContractorProvider
- EquipmentProvider
- PersonnelTypeProvider
- BidItemProvider
- EntryQuantityProvider
- TodoProvider
- CalculatorProvider
- GalleryProvider

#### Step 7.1B.1: Add dispose() to remaining 19 providers

For each provider below, add a `@override void dispose()` method that cleans up the specified resources, then calls `super.dispose()`.

| Provider | File | Cleanup needed |
|----------|------|----------------|
| `AuthProvider` | `lib/features/auth/presentation/providers/auth_provider.dart` | Cancel `_authSubscription` (StreamSubscription) |
| `ProjectProvider` | `lib/features/projects/presentation/providers/project_provider.dart` | Remove auth listener added in Phase 1 projects_providers.dart (if rewired in Phase 5, verify no dangling listener) |
| `InspectorFormProvider` | `lib/features/forms/presentation/providers/inspector_form_provider.dart` | `super.dispose()` |
| `FormExportProvider` | `lib/features/forms/presentation/providers/form_export_provider.dart` | `super.dispose()` |
| `DocumentProvider` | `lib/features/forms/presentation/providers/document_provider.dart` | `super.dispose()` |
| `SyncProvider` | `lib/features/sync/presentation/providers/sync_provider.dart` | Cancel any periodic timers |
| `DailyEntryProvider` | `lib/features/entries/presentation/providers/daily_entry_provider.dart` | `super.dispose()` |
| `EntryExportProvider` | `lib/features/entries/presentation/providers/entry_export_provider.dart` | `super.dispose()` |
| `CalendarFormatProvider` | `lib/features/entries/presentation/providers/calendar_format_provider.dart` | `super.dispose()` |
| `AppConfigProvider` | `lib/features/auth/presentation/providers/app_config_provider.dart` | `super.dispose()` |
| `AdminProvider` | `lib/features/settings/presentation/providers/admin_provider.dart` | `super.dispose()` |
| `ThemeProvider` | `lib/features/settings/presentation/providers/theme_provider.dart` | `super.dispose()` |
| `ProjectAssignmentProvider` | `lib/features/projects/presentation/providers/project_assignment_provider.dart` | `super.dispose()` |
| `ProjectSettingsProvider` | `lib/features/projects/presentation/providers/project_settings_provider.dart` | `super.dispose()` |
| `ProjectSyncHealthProvider` | `lib/features/projects/presentation/providers/project_sync_health_provider.dart` | `super.dispose()` |
| `ProjectImportRunner` | `lib/features/projects/presentation/providers/project_import_runner.dart` | `super.dispose()` |
| `EntryEditingController` | `lib/features/entries/presentation/providers/entry_editing_controller.dart` | `super.dispose()` |
| `ExtractionJobRunner` | `lib/features/pdf/services/extraction_job_runner.dart` | Cancel any isolate refs or timer refs |
| `PreferencesService` | `lib/shared/services/preferences_service.dart` | `super.dispose()` |

**NOTE:** Some of these (e.g., `ThemeProvider`, `CalendarFormatProvider`) may have no resources to clean up beyond `super.dispose()`. Add the override anyway for consistency and future-proofing — it ensures the dispose chain is never accidentally broken.

**Verification:** Search all `ChangeNotifier` subclasses in `lib/` for missing `dispose()` overrides:
```
Grep for "extends ChangeNotifier" and "with ChangeNotifier" in lib/ — cross-reference with dispose() in same file.
```

---

### Sub-phase 7.2: Dashboard + Toolbox — Empty Domain Scaffolding
**Files:**
- Create: `lib/features/dashboard/domain/domain.dart`
- Create: `lib/features/toolbox/domain/domain.dart`
- Modify: `lib/features/dashboard/dashboard.dart` (barrel update)
- Modify: `lib/features/toolbox/toolbox.dart` (barrel update)
**Agent:** `backend-data-layer-agent`

#### Step 7.2.1: Create dashboard domain barrel
Create `lib/features/dashboard/domain/domain.dart`:
```dart
// Dashboard domain layer — presentation-only feature, reads from other
// feature providers. Placeholder for future dashboard-specific use cases.
```

Update `lib/features/dashboard/dashboard.dart` to export `domain/domain.dart`.

#### Step 7.2.2: Create toolbox domain barrel
Create `lib/features/toolbox/domain/domain.dart`:
```dart
// Toolbox domain layer — hub screen only, delegates to calculator/forms/gallery/todos.
// Placeholder for future cross-feature use cases.
```

Update `lib/features/toolbox/toolbox.dart` to export `domain/domain.dart`.

**WHY:** Future-proofing per spec. Empty domain dirs are low-cost markers that every feature follows the Clean Architecture pattern.

---

### Sub-phase 7.3: Weather — Domain Interface
**Files:**
- Create: `lib/features/weather/domain/domain.dart`
- Create: `lib/features/weather/domain/weather_service_interface.dart`
- Modify: `lib/features/weather/services/weather_service.dart`
- Modify: `lib/features/weather/weather.dart` (barrel update)
**Agent:** `backend-data-layer-agent`

#### Step 7.3.1: Create WeatherServiceInterface
Create `lib/features/weather/domain/weather_service_interface.dart`:
```dart
import '../services/weather_service.dart';

/// Domain contract for weather data retrieval.
/// Allows substitution of mock implementations in tests.
abstract class WeatherServiceInterface {
  Future<WeatherData?> fetchWeatherForCurrentLocation(DateTime date);
  Future<WeatherData?> fetchWeather(double lat, double lon, DateTime date);
}
```

**WHY:** WeatherService has concrete dependencies on `http`, `geolocator`, and test mode config. An interface allows test doubles without the `TestModeConfig` global flag pattern.

#### Step 7.3.2: Implement the interface on WeatherService
In `lib/features/weather/services/weather_service.dart`, add `implements WeatherServiceInterface` to the `WeatherService` class declaration (line 26):

Change:
```dart
class WeatherService {
```
To:
```dart
class WeatherService implements WeatherServiceInterface {
```

No other changes needed — `WeatherService` already has the matching method signatures.

#### Step 7.3.3: Create weather domain barrel
Create `lib/features/weather/domain/domain.dart`:
```dart
export 'weather_service.dart';
```

Update `lib/features/weather/weather.dart` to export `domain/domain.dart`.

---

### Sub-phase 7.4: PDF — Domain Scaffolding
**Files:**
- Create: `lib/features/pdf/domain/domain.dart`
- Modify: `lib/features/pdf/pdf.dart` (barrel update)
**Agent:** `pdf-agent`

#### Step 7.4.1: Create pdf domain barrel
Create `lib/features/pdf/domain/domain.dart`:
```dart
// PDF domain layer — extraction pipeline is already properly layered in services/.
// ExtractionJobRunner stays in services (it IS the domain logic).
// Placeholder for future extraction use case abstractions.
```

Update `lib/features/pdf/pdf.dart` to export `domain/domain.dart`.

**WHY:** PDF's `ExtractionJobRunner` (17,360 bytes) and pipeline stages are already properly layered in `services/`. No refactoring needed — just the domain directory marker. `catch(_)` fixes in PDF extraction stages are explicitly OUT OF SCOPE per spec.

---

### Sub-phase 7.5: Fix Remaining `catch(_)` Blocks
**Files:**
- Modify: `lib/services/soft_delete_service.dart` (lines 108, 121, 142, 511)
- Modify: `lib/services/image_service.dart` (lines 155, 174, 188)
- Modify: `lib/shared/services/preferences_service.dart` (line 130)
- Modify: `lib/shared/utils/field_formatter.dart` (lines 56, 60)
- Modify: `lib/core/config/config_validator.dart` (line 90)
- Modify: `lib/core/driver/driver_server.dart` (lines 194, 253, 568, 587, 594, 628, 1347, 1572, 1693)
- Modify: `lib/features/auth/presentation/screens/pending_approval_screen.dart` (lines 94, 113)
- Modify: `lib/features/settings/presentation/screens/trash_screen.dart` (lines 96, 284, 298) — if any remain after 7.1
**Agent:** `backend-data-layer-agent`

#### Step 7.5.1: Fix pattern — convert `catch(_)` to `catch(e)` with Logger
For every `catch(_)` in the files listed above, apply this transformation:

**Pattern A** — catch that silently swallows (most cases):
```dart
// BEFORE
} catch (_) {
  // comment or empty
}

// AFTER
} catch (e) {
  Logger.<category>('[ClassName] <method> error: $e');
}
```

**Pattern B** — catch that returns a fallback value (field_formatter, config_validator, preferences_service):
```dart
// BEFORE
} catch (_) {
  return null;  // or return false, etc.
}

// AFTER
} catch (e) {
  Logger.log('[ClassName] <method> parse error: $e', level: 'WARN');
  return null;
}
```

**Pattern C** — nested catch in image_service (lines 155, 174, 188) where the catch wraps a Logger call:
```dart
// These are `try { Logger.photo(...) } catch (_) {}` — the Logger call itself is wrapped.
// Convert to: `try { Logger.photo(...) } catch (e) { /* Logger failed, no safe fallback */ }`
// These are acceptable as-is since they're guarding against Logger failures.
// SKIP these — they are catch-around-logger patterns, not swallowed errors.
```

**Logger category mapping:**
| File | Logger category |
|------|----------------|
| `soft_delete_service.dart` | `Logger.db()` |
| `image_service.dart` | SKIP (catch-around-logger) |
| `preferences_service.dart` | `Logger.log(..., level: 'WARN')` |
| `field_formatter.dart` | `Logger.log(..., level: 'WARN')` |
| `config_validator.dart` | `Logger.log(..., level: 'WARN')` |
| `driver_server.dart` | `Logger.log()` |
| `pending_approval_screen.dart` | `Logger.auth()` |
| `trash_screen.dart` | Already fixed in 7.1 (repository handles logging) |

**WHY:** Architecture anti-pattern rule: "`catch(_)` without logging — Silently swallows errors, makes debugging impossible." Every catch must log or have an explicit documented reason.

**IMPORTANT:** For `field_formatter.dart` lines 56 and 60 (the nested date parsing catch blocks), these are parse-fallback patterns. Add `Logger.log` only to the **outer** catch. The inner `catch(_)` on `DateTime.parse` fallback is acceptable since the outer catch already handles the failure path. However, for consistency, convert both to `catch (e)` and log only the outer one.

**IMPORTANT:** For `driver_server.dart` — this file has 9 `catch(_)` blocks. Many are in test-driver HTTP handler code. Apply the same pattern but use `Logger.log('[DriverServer] ...')`. Since this is test infrastructure, logging is still valuable for debugging E2E test failures.

#### Step 7.5.2: Add Logger import where missing
Files that may not already import Logger:
- `lib/shared/utils/field_formatter.dart` — check and add `import 'package:construction_inspector/core/logging/logger.dart';`
- `lib/core/config/config_validator.dart` — check and add import
- `lib/features/auth/presentation/screens/pending_approval_screen.dart` — check and add import

**NOTE:** `soft_delete_service.dart` and `driver_server.dart` likely already import Logger. Verify before adding duplicates.

---

### Sub-phase 7.6: Dead Code Removal
**Files:**
- Modify: `lib/main.dart` — remove unused imports (audit after phases 1-6 changes)
- Any files modified in phases 1-6 that have leftover unused imports
**Agent:** `backend-data-layer-agent`

#### Step 7.6.1: Run flutter analyze to find dead code
```
pwsh -Command "flutter analyze"
```

Review output for:
- `unused_import` warnings in any modified files
- `unused_local_variable` warnings
- `dead_code` warnings

#### Step 7.6.2: Fix all analyzer warnings from phase 1-6 changes
For each warning, remove the unused import/variable/code.

**IMPORTANT:** Do NOT touch files that were not modified in this refactor. Only clean up dead code introduced or exposed by the refactoring work.

#### Step 7.6.3: Verify main.dart state
After phases 1-6, `main.dart` should be ~50 lines. The `_runApp()` body should be 3 lines (call `AppInitializer.initialize()`, then `runApp()`). `ConstructionInspectorApp` should have 1 constructor param (`router`). If this is not the case, something was missed in Phase 1 Sub-phase 1.4 — go back and fix it.

---

### Sub-phase 7.7: Final Verification Sweep
**Files:** All modified files from phases 1-7
**Agent:** `qa-testing-agent`

#### Step 7.7.1: Run static analysis
```
pwsh -Command "flutter analyze"
```
Must pass with zero errors. Warnings are acceptable only if pre-existing (not introduced by this refactor).

#### Step 7.7.2: Run test suite
```
pwsh -Command "flutter test"
```
All tests must pass.

#### Step 7.7.3: Verify success criteria checklist
Run these verification checks:

1. **Zero `Supabase.instance.client` in presentation layer:**
   Search `lib/**/presentation/` for `Supabase.instance.client` — must return zero hits.

2. **Zero raw `dbService.database` in presentation layer:**
   Search `lib/**/presentation/` for `dbService.database` or `_dbService.database` — must return zero hits.

3. **Every feature has `domain/` directory:**
   Verify these directories exist:
   - `lib/features/dashboard/domain/`
   - `lib/features/settings/domain/`
   - `lib/features/weather/domain/`
   - `lib/features/toolbox/domain/`
   - `lib/features/pdf/domain/`
   - (Plus any from earlier phases: sync already has one)

4. **Zero `catch(_)` in refactored files (sync/pdf excluded):**
   Search all files modified in this phase for `catch (_)` — must return zero hits (excluding `lib/features/sync/` and `lib/features/pdf/services/extraction/`).

5. **`flutter analyze` clean:**
   Already verified in 7.7.1.

6. **`flutter test` passes:**
   Already verified in 7.7.2.

#### Step 7.7.4: Document any deferred items
If any success criteria cannot be met, document the specific items and why in a comment block at the top of this plan file. Do NOT silently skip criteria.

---

## Dispatch Groups

| Group | Sub-phases | Parallelizable | Notes |
|-------|-----------|----------------|-------|
| A | 7.1, 7.1B, 7.2, 7.3, 7.4 | Yes — all independent | Domain scaffolding + trash fix + dispose sweep |
| B | 7.5 | After A (trash_screen catch blocks depend on 7.1) | catch(_) sweep |
| C | 7.6 | After B (need all changes landed) | Dead code cleanup |
| D | 7.7 | After C (final verification) | Analyze + test + checklist |

## Commands
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
pwsh -Command "flutter pub get"
```


---

## Phase 8: Sync Module Registration (Minimal Touch)

**Goal:** Move all sync-related instantiation and provider registration out of `main.dart` into a dedicated `sync_providers.dart` module. Zero logic changes — pure code-motion refactor.

**Why this is last:** Sync is the most complex wiring (originally main.dart lines 278–542, 956–992, now in `AppInitializer`). It has 10 setter injections, a 100-line `onPullComplete` lambda, lifecycle observer registration, FCM initialization, and cross-cutting dependencies on `AuthProvider`, `AppConfigProvider`, `DatabaseService`, and `ProjectLifecycleService`. Moving it last means all its dependencies are already modularized by earlier phases.

### Sub-phase 8.1: Create SyncProviders Module

**Files:**
- `lib/features/sync/di/sync_providers.dart` (NEW)
- `lib/features/sync/di/di.dart` (NEW — barrel export)

**Agent:** backend-supabase-agent

**Steps:**

1. Create `lib/features/sync/di/sync_providers.dart` with a `SyncProviders` class containing two static methods:

   ```dart
   /// Pre-widget-tree initialization. Called from main() before runApp().
   /// Returns a record of the initialized sync objects that main() passes
   /// to ConstructionInspectorApp.
   static Future<({
     SyncOrchestrator orchestrator,
     SyncLifecycleManager lifecycleManager,
   })> initialize({
     required DatabaseService dbService,
     required AuthProvider authProvider,
     required AppConfigProvider appConfigProvider,
   }) async { ... }
   ```

   ```dart
   /// Returns the list of Provider entries for MultiProvider.
   /// Called from ConstructionInspectorApp.build().
   static List<SingleChildWidget> providers({
     required SyncOrchestrator syncOrchestrator,
     required SyncLifecycleManager syncLifecycleManager,
     required ProjectLifecycleService projectLifecycleService,
     required ProjectSyncHealthProvider projectSyncHealthProvider,
   }) { ... }
   ```

2. Move the following code blocks **AS-IS** from `AppInitializer.initialize()` (originally `main.dart` `_runApp()`) into `SyncProviders.initialize()`:

   - `SyncOrchestrator` instantiation + `await syncOrchestrator.initialize()` (line 279–280)
   - `CompanyLocalDatasource` + `CompanyRepository` instantiation (lines 284–285) — these exist solely for sync wiring, so they move with it
   - `UserProfileSyncDatasource` conditional creation + `setUserProfileSyncDatasource()` (lines 289–297)
   - `SyncLifecycleManager` instantiation (line 300)
   - `updateSyncContext()` closure + `authProvider.addListener(updateSyncContext)` (lines 349–358)
   - `setSyncContextProvider()` call (lines 361–364)
   - `onPullComplete` 100-line lambda **AS-IS** (lines 369–465)
   - FCM initialization block — conditional mobile-only (lines 468–471)
   - `setAppConfigProvider()` call (line 479)
   - `isReadyForSync` wiring (lines 520–523)
   - `onAppResumed` wiring (lines 526–539)
   - `WidgetsBinding.instance.addObserver(syncLifecycleManager)` (line 542)

   **CRITICAL:** The `onPullComplete` lambda (lines 369–465) must move character-for-character. It contains security fixes (FIX 3, FIX 4, FIX 5, FIX 6, CRIT-4) and transaction logic. Do NOT refactor, rename, or reformat it.

   **CRITICAL:** `BackgroundSyncHandler.initialize()` (line 211) stays in `main.dart` — it runs before sync orchestrator exists and only needs `dbService`. Do NOT move it.

3. Move the following provider registrations **AS-IS** from `ConstructionInspectorApp.build()` into `SyncProviders.providers()`:

   - `Provider<SyncRegistry>.value(value: SyncRegistry.instance)` (line 956)
   - `Provider<SyncOrchestrator>.value(value: syncOrchestrator)` (lines 958–959)
   - `ChangeNotifierProvider` for `SyncProvider` including all wiring (lines 960–992): `onStaleDataWarning`, `onForcedSyncInProgress`, `onSyncCycleComplete`, `onNewAssignmentDetected`

4. Create barrel export `lib/features/sync/di/di.dart`:
   ```dart
   export 'sync_providers.dart';
   ```

**Verification:**
- `SyncProviders.initialize()` returns a record — no global state, no singletons
- `SyncProviders.providers()` returns `List<SingleChildWidget>` — composable with other modules
- The `onPullComplete` lambda is byte-identical to the original
- `CompanyRepository` is returned from `initialize()` if `AuthProvider` still needs it (check if auth phase already provides it — if so, accept it as a parameter instead of creating it)

### Sub-phase 8.2: Wire SyncProviders into AppInitializer and app_providers.dart

**Files:**
- `lib/core/di/app_initializer.dart` (MODIFY)
- `lib/core/di/app_providers.dart` (MODIFY)

**Agent:** backend-supabase-agent

**Steps:**

1. Add import for `sync_providers.dart` in `app_initializer.dart`:
   ```dart
   import 'package:construction_inspector/features/sync/di/sync_providers.dart';
   ```

2. In `AppInitializer.initialize()`, replace the sync initialization block with:
   ```dart
   // Initialize sync module (orchestrator, lifecycle manager, FCM, all wiring)
   final syncResult = await SyncProviders.initialize(
     dbService: dbService,
     authProvider: authProvider,
     appConfigProvider: appConfigProvider,
   );
   final syncOrchestrator = syncResult.orchestrator;
   final syncLifecycleManager = syncResult.lifecycleManager;
   ```

   **Note:** `authProvider` must be created BEFORE this call in `AppInitializer.initialize()`. Verify ordering is preserved.

   **Note:** `CompanyRepository` is also needed by `AuthProvider`. If `AuthProvider` creates it internally or receives it from an earlier phase's module, then `SyncProviders` can create its own instance. If `AuthProvider` receives the same instance, then `SyncProviders.initialize()` must either accept it as a parameter or return it. Check the dependency: `AuthProvider` constructor takes `companyRepository` — so the `CompanyLocalDatasource` + `CompanyRepository` instantiation must stay in `AppInitializer` (or move to an auth module in an earlier phase). **Resolve this by keeping `companyRepository` creation in `AppInitializer` and passing it into `SyncProviders.initialize()`:**

   Update the `initialize()` signature to accept `companyRepository`:
   ```dart
   static Future<...> initialize({
     required DatabaseService dbService,
     required AuthProvider authProvider,
     required AppConfigProvider appConfigProvider,
     required CompanyLocalDatasource companyLocalDs,
   }) async { ... }
   ```

3. In `app_providers.dart`, replace the inline sync provider entries (the `// Tier 5: Sync` block added in Phase 1) with a spread of `SyncProviders.providers()`:
   ```dart
   ...SyncProviders.providers(
     syncOrchestrator: syncOrchestrator,
     syncLifecycleManager: syncLifecycleManager,
     projectLifecycleService: projectLifecycleService,
     projectSyncHealthProvider: projectSyncHealthProvider,
   ),
   ```
   Add the import for `sync_providers.dart` in `app_providers.dart` and remove the now-unnecessary inline `Provider<SyncRegistry>`, `Provider<SyncOrchestrator>`, and `ChangeNotifierProvider<SyncProvider>` entries.

4. Remove now-unused sync imports from `app_initializer.dart` (moved into `SyncProviders`):
   - `user_profile_local_datasource.dart`
   - `user_profile_sync_datasource.dart`
   - `fcm_handler.dart`

   **Keep** these imports in `app_initializer.dart` (still used directly):
   - `background_sync_handler.dart` — `BackgroundSyncHandler.initialize()` stays in `AppInitializer`
   - `company_local_datasource.dart` — passed to both `AuthProvider` and `SyncProviders`
   - `company_repository.dart` — passed to `AuthProvider`

5. Remove the `SyncRegistry`, `SyncOrchestrator`, and `SyncProvider` inline imports from `app_providers.dart` that were added as a stopgap in Phase 1 — they are now encapsulated in `SyncProviders.providers()`.

### Sub-phase 8.3: Verify and Clean Up

**Files:**
- `lib/features/sync/di/sync_providers.dart` (VERIFY)
- `lib/main.dart` (VERIFY)

**Agent:** backend-supabase-agent

**Steps:**

1. Run static analysis:
   ```
   pwsh -Command "flutter analyze"
   ```
   Fix any unused import warnings or type mismatches.

2. Run full test suite:
   ```
   pwsh -Command "flutter test"
   ```
   All existing tests must pass with zero changes. If any test fails, it means a dependency was broken during the move — fix the wiring, do NOT modify test expectations.

3. Verify `main.dart` line count. After Phase 1 Sub-phase 1.4, `main.dart` should already be ~50 lines. Phase 8 moves sync init into `SyncProviders` which is called from `AppInitializer`, so `main.dart` itself should not change further. Verify `app_initializer.dart` has the sync init block properly delegated to `SyncProviders.initialize()`.

4. Verify `sync_providers.dart` has NO logic changes:
   - No renamed variables
   - No reordered statements
   - No added/removed null checks
   - No modified lambda bodies
   - Comments preserved (especially security fix annotations: FIX 3, FIX 4, FIX 5, FIX 6, CRIT-4, SEC-101, SEC-102)

5. Grep for orphaned references:
   - Search `main.dart` for `syncOrchestrator.set` — should be zero (all setter calls moved)
   - Search `main.dart` for `syncOrchestrator.on` — should be zero (all callback wiring moved)
   - Search `main.dart` for `syncLifecycleManager.` — should only be in `ConstructionInspectorApp` constructor/field declarations and the `providers:` spread call
   - Search `main.dart` for `FcmHandler` — should be zero (moved)

**Commands:**
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
```

---



---

## Review Findings Addressed

| Fix # | Issue | Resolution |
|-------|-------|------------|
| 1 | main.dart 50-line target unreachable | Added Sub-phase 1.4: `AppInitializer` class extracts entire `_runApp()` body into `lib/core/di/app_initializer.dart`. Updated summary table and Step 7.6.3 to reflect ~50 line target. |
| 2 | 15+ providers missing dispose() | Added Sub-phase 7.1B "Provider Dispose Sweep" with explicit table of all 25 providers, what to clean up, and which are already handled by Phase 3. |
| 3 | Phase 1 vs Phase 8 sync_providers.dart conflict | Step 1.1.15 now skipped — sync module deferred entirely to Phase 8. File count updated from 15 to 14 feature provider files. |
| 4 | Forms I-prefix naming inconsistency | All `I`-prefixed interfaces (`IFormResponseRepository`, `IInspectorFormRepository`, etc.) renamed to match project convention: abstract = `FooRepository`, concrete = `FooRepositoryImpl`. Applied to both forms and entries features. |
| 5 | YAGNI: BaseUseCaseListProvider and UseCaseResult unused | Sub-phases 2.2, 2.4, and their test sub-phases (2.6.2, 2.6.3) removed. Barrel exports updated. Migration notes updated. |
| 6 | DeleteProjectUseCase imports Supabase in domain layer | Added `ProjectRemoteDatasource` interface in domain/ with `softDeleteProject()` method and `ProjectRemoteDatasourceImpl` in data/datasources/remote/. Use case depends on interface, not Supabase directly. |
| 7 | SwitchCompanyUseCase should clear data internally | Updated to call `clearLocalCompanyData` internally instead of returning a flag. Security comment added. |
| 8 | AdminProvider receives raw SupabaseClient | Added Step 7.1.3: `AdminRepository` interface in settings/domain/ with `AdminRepositoryImpl` wrapping Supabase calls. AdminProvider depends on interface. |
| 9 | Tech stack typo: "drift" should be "sqflite" | Fixed in header. |
| 10 | (R2) app_providers.dart imports non-existent sync_providers.dart | Removed sync import and `...syncProviders()` spread from Phase 1.2. Added inline sync provider registrations (`SyncRegistry`, `SyncOrchestrator`, `SyncProvider`) with comment noting Phase 8 will extract them. Updated Phase 8.2 to modify `app_providers.dart` instead of `main.dart`. |
| 11 | (R2) main_driver.dart 37-param constructor not updated | Added Step 1.5.2 to Sub-phase 1.5: update `main_driver.dart` to use new 2-param `ConstructionInspectorApp` constructor with `AppInitializer` + `buildAppProviders()` pattern, preserving driver-specific test harness providers. |
| 12 | (R2) Stale test command referencing removed file | Removed `test/shared/providers/base_use_case_list_provider_test.dart` from Step 2.7.2 test command. Now runs only `test/shared/domain/`. |
| 13 | (R2) Inconsistent `_interface.dart` file naming in Phase 6 | Renamed all `*_interface.dart` references in Phase 6 (forms + entries) to bare names matching Phase 3 convention. E.g., `form_response_repository_interface.dart` -> `form_response_repository.dart` in `domain/repositories/`. |
| 14 | (R2) Phase 7.1B provider count inconsistency | Updated prose from "remaining 15" to "remaining 19" to match actual table row count. Also removed hardcoded "ALL 25" total since 10 + 19 = 29. |
| 15 | (R2) Phase 8 references `_runApp()` lines that no longer exist | Updated Phase 8 to reference `AppInitializer.initialize()` instead of `_runApp()`. Sub-phase 8.2 now modifies `app_initializer.dart` and `app_providers.dart` instead of `main.dart`. All line-number references to original `main.dart` marked as "originally in main.dart". |

---

## Validation Checklist

- [ ] `main.dart` under 50 lines
- [ ] Zero `Supabase.instance.client` in any `presentation/` file
- [ ] Zero raw `dbService.database` in any `presentation/` file
- [ ] Every feature has `domain/` directory
- [ ] All providers have `dispose()` override
- [ ] Zero `catch(_)` in refactored files
- [ ] `pwsh -Command "flutter analyze"` — clean
- [ ] `pwsh -Command "flutter test"` — all pass
- [ ] App cold-starts correctly on device
- [ ] Auth sign-in/sign-out/switch-company works
- [ ] Project create/delete/select works
- [ ] Sync push/pull works
