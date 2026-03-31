# Clean Architecture Refactor Spec

## Overview

### Purpose
Decompose the main.dart god function into feature-scoped DI modules and introduce a Clean Architecture domain layer across all 17 features, eliminating layer violations, provider memory leaks, and swallowed errors.

### Scope

**In scope:**
- **#1 main.dart God Function**: Extract `_runApp()` (470 lines, 56 objects, 38 providers) into feature modules
- **#2 No Domain Layer**: Domain layer (use cases + repository interfaces) for all 17 features
- **#4/#13 Layer Violations**: Eliminate all presentation→DB (8 files) and presentation→Supabase (5 locations) direct access
- **#5 ProjectProvider God Class**: Break apart ProjectProvider (800 lines, 54 symbols) into focused use cases
- **#8 Silent catch(_) Blocks**: Replace silent catch blocks in all touched files with proper error handling
- **#12 Provider Dispose Gap**: Add `dispose()` to all 25 providers missing it

**Out of scope:** Sync engine restructuring, freezed/immutable models, crash reporting (#9), i18n (#14), DB encryption (#11), home_screen mega-widget (#7), E2E tests (#10), database_service monolith (#3)

### Success Criteria
- [ ] `main.dart` under 50 lines
- [ ] Zero `Supabase.instance.client` or raw `db.query()` calls in any `presentation/` file
- [ ] Every feature has `domain/` with use cases (pass-through for CRUD, real extraction for complex)
- [ ] All providers have `dispose()` overrides
- [ ] Zero silent `catch(_)` blocks in refactored files
- [ ] App compiles and runs identically before and after

---

## Approach Selected: Top-Down (main.dart First)

**Why**: Immediate visible win (main.dart 1069→~30 lines in Phase 1), creates module boundaries that contain all subsequent work, enables incremental feature migration.

**Rejected alternatives:**
- **Bottom-Up (Data Layer First)**: Safer but main.dart stays ugly until the end, longest time to visible improvement
- **Vertical Slices (One Feature End-to-End)**: Proves the pattern but harder to parallelize, main.dart messy until every feature done

---

## Target Architecture

### Feature Structure
```
lib/features/<name>/
├── <name>_providers.dart          # NEW: exports List<SingleChildWidget>
├── domain/                        # NEW
│   ├── entities/                  # Re-export or wrap data models
│   ├── repositories/              # Abstract interfaces
│   └── usecases/                  # Business logic units
├── data/
│   ├── datasources/local/
│   ├── datasources/remote/
│   ├── models/
│   ├── repositories/              # Concrete implementations (*Impl)
│   └── services/
└── presentation/
    ├── providers/                 # Thin — delegates to use cases
    ├── screens/
    └── widgets/
```

### Data Flow
```
BEFORE: Screen → Provider → Repository → Datasource → SQLite
AFTER:  Screen → Provider → UseCase → Repository (interface) → Datasource → SQLite
```

### Use Case Pattern
```dart
// Pass-through (CRUD features like locations, photos):
class GetLocations {
  final LocationRepository _repository;
  GetLocations(this._repository);
  Future<List<Location>> call(String projectId) => _repository.getByProjectId(projectId);
}

// Real extraction (complex features like auth, projects):
class DeleteProject {
  final ProjectRepository _projectRepo;
  final SoftDeleteService _softDelete;
  // ... all deps that currently live in ProjectProvider.deleteProject()
  Future<void> call(String projectId) async { /* extracted logic */ }
}
```

### Feature Module Pattern
```dart
// lib/features/locations/locations_providers.dart
List<SingleChildWidget> locationProviders(DatabaseService db) => [
  Provider(create: (_) => LocationLocalDatasource(db)),
  Provider(create: (ctx) => LocationRepositoryImpl(ctx.read<LocationLocalDatasource>())),
  Provider<GetLocations>(create: (ctx) => GetLocations(ctx.read<LocationRepository>())),
  ChangeNotifierProvider(create: (ctx) => LocationProvider(
    getLocations: ctx.read<GetLocations>(),
    // ...
  )),
];
```

### main.dart Target
```dart
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final db = await DatabaseService.initialize();
  final prefs = PreferencesService()..initialize();
  // ... 3-4 async inits

  runApp(MultiProvider(
    providers: appProviders(db, prefs),
    child: const ConstructionInspectorApp(),
  ));
}
```

### Repository Interface Pattern
```dart
// domain/repositories/location_repository.dart
abstract class LocationRepository {
  Future<List<Location>> getByProjectId(String projectId);
  Future<void> save(Location item);
  Future<void> delete(String id);
}

// data/repositories/location_repository_impl.dart
class LocationRepositoryImpl implements LocationRepository { ... }
```

### BaseListProvider Evolution
The existing `BaseListProvider<T, R extends ProjectScopedRepository<T>>` will be updated to accept use cases instead of repositories directly. Subclasses that currently extend it (Location, Contractor, Equipment, BidItem, PersonnelType) will be migrated to inject use cases.

---

## Phase Ordering

### Phase 1: Feature Module Extraction (Mechanical)
**What**: Move existing provider registrations from `main.dart` into per-feature `<name>_providers.dart` files. Create `lib/core/di/app_providers.dart` that composes them.
**Touches**: `main.dart`, 17 new `*_providers.dart` files, 1 new `app_providers.dart`
**Risk**: Low — pure code movement, no logic changes
**Validation**: App compiles and runs identically

### Phase 2: Core Domain Infrastructure
**What**: Create shared base classes: `UseCase<T>` abstract, repository interfaces pattern, error types for use case results. Update `BaseListProvider` to accept use cases.
**Touches**: `lib/shared/` (new domain base classes)
**Risk**: Low — additive only

### Phase 3: CRUD Features (Batch — 8 features)
**What**: Add `domain/` with interfaces + pass-through use cases for: locations, photos, contractors, equipment, personnel_types, quantities (bid_items + entry_quantities), todos, calculator, gallery
**Touches**: Each feature gets `domain/` dir, provider updated to inject use cases, repository renamed to `*Impl`
**Risk**: Low — mechanical pattern replication
**Includes**: dispose() + catch block fixes for each

### Phase 4: Auth (Heaviest Extraction)
**What**: Break AuthProvider (977 lines, 48 methods) into use cases: `SignIn`, `SignOut`, `SignUp`, `LoadProfile`, `SwitchCompany`, `CheckInactivity`, `MigratePreferences`, `MockAuth`. Fix AppConfigProvider's direct Supabase call.
**Touches**: auth feature entirely, `SettingsScreen` (2 Supabase violations)
**Risk**: High — auth state machine is complex, touches security
**Includes**: Move `SettingsScreen` Supabase calls behind proper repository

### Phase 5: Projects (Second Heaviest)
**What**: Break ProjectProvider (800 lines, 54 symbols) into use cases: `DeleteProject`, `LoadMergedProjects`, `LoadAssignments`, `FetchRemoteProjects`, `SelectProject`. Fix `ProjectSetupScreen` direct Supabase call. Fix `ProjectProvider` direct Supabase RPC call.
**Touches**: projects feature entirely, ProjectSetupScreen
**Risk**: Medium-High — authorization logic, soft-delete cascades, RPC calls

### Phase 6: Forms & Entries
**What**: Domain layer for forms (InspectorFormProvider 449 lines — calculator dispatch, row normalization) and entries (DailyEntryProvider, controllers, EntryExportProvider cross-feature dep on FormExportProvider).
**Touches**: forms + entries features
**Risk**: Medium — cross-feature dependencies between form/entry exports

### Phase 7: Remaining Features + Cleanup
**What**: Domain layer for dashboard, settings, weather, toolbox, pdf. Final sweep for any remaining catch blocks. Verify zero layer violations. Remove any dead code from extraction.
**Touches**: remaining features, final audit
**Risk**: Low — mostly thin features

### Phase 8: Sync Module Registration (Minimal Touch)
**What**: Move sync provider registration into `sync_providers.dart`. No logic changes. The 10 setter injections move as-is into the feature module.
**Touches**: sync registration only — no engine/orchestrator changes
**Risk**: Low — code movement only

### Ordering Rationale
- Phase 1 first: creates module boundaries that contain all subsequent work
- Phase 2 before features: shared patterns must exist before replication
- Phase 3 (CRUD batch): proves the pattern at scale before hard ones
- Phases 4-5 (auth/projects): isolated, riskiest, done carefully not batched
- Phase 8 last: sync works, don't risk it

---

## Initialization Order

Feature modules must preserve the current initialization tier order:
```
Tier 0: DatabaseService, PreferencesService (async init)
Tier 1: Datasources (all depend on DatabaseService)
Tier 2: Repositories (depend on datasources)
Tier 3: Use Cases (depend on repositories)
Tier 4: Auth stack (AuthService, AuthProvider — many things depend on these)
Tier 5: Feature providers (depend on auth + repositories/use cases)
Tier 6: Sync, Router (depend on auth + feature providers)
```
`app_providers.dart` must spread feature module lists in this tier order with documenting comments.

---

## Cross-Feature Dependencies

These must be preserved during extraction:
- `GalleryProvider` → `PhotoRepository` (photos) + `DailyEntryRepository` (entries)
- `EntryExportProvider` → `FormExportProvider` (ordering-sensitive `context.read`)
- `FormResponseRepository` → consumed by 5 different features (forms, entries, gallery, export providers)
- `AuthProvider.canEditFieldData` closure → injected into 12+ providers via `canWrite`

Shared repositories that serve multiple features stay registered in the owning feature's module, with explicit cross-feature documentation.

---

## Provider Dispose

25 providers need `dispose()`. Common patterns:
- Cancel `Timer` instances (SyncProvider, SyncLifecycleManager)
- Remove listeners on `AuthProvider`, `SyncOrchestrator`
- Call `super.dispose()` on all ChangeNotifier subclasses
- Null out callback references to break retain cycles

---

## Silent Catch Block Strategy

For the ~58 `catch(_)` replacements in touched files:
- **CRUD operations**: catch specific exceptions, set `_error` on provider, log via `Logger`
- **Auth operations**: catch `AuthException`, surface user-friendly message
- **DB operations**: catch `DatabaseException`, log + set error state
- **Rule**: Never swallow — minimum action is `Logger.error()` with context

---

## Security Implications

### Auth Extraction Invariants
When extracting AuthProvider into use cases, these security invariants must be preserved exactly:
- `SwitchCompanyUseCase` must still clear local data before switching — cannot leave stale data from another company
- `CheckInactivityUseCase` must still force sign-out after 7 days — secure storage read/write must stay atomic
- `canEditFieldData` closure must still propagate to all 12+ providers

### Layer Violation Fixes (Security Positive)
Moving these out of presentation is a security improvement:
- `ProjectSetupScreen` querying `user_profiles` directly → moves behind repository with proper scoping
- `SettingsScreen` updating `user_profiles` directly → moves behind repository
- `ProjectProvider` calling `admin_soft_delete_project` RPC → moves into `DeleteProjectUseCase` where authorization check is explicit and testable

### Not Affected
- No Supabase schema, RLS policies, or remote datasource changes
- No new endpoints, data flows, or storage
- All changes are client-side architecture only

---

## Testing Strategy

### Per-Phase Validation
Every phase must pass before the next:
- `pwsh -Command "flutter analyze"` — zero new warnings
- `pwsh -Command "flutter test"` — all existing tests pass
- Manual app launch — verify affected feature works

### Unit Tests for New Use Cases
- **Complex features** (auth, projects, forms, entries): each extracted use case gets a unit test
- **CRUD features**: no new tests for pass-through use cases — existing tests cover them

### Existing Test Updates
- Tests mocking repositories will need to mock domain interfaces instead
- `test/helpers/mocks/mock_providers.dart` updated as provider constructors change
- Provider tests that inject repositories now inject use cases

### Regression Risk Areas
| Area | Risk | Verification |
|------|------|-------------|
| Auth state machine | High | Manual sign-in/sign-out/switch-company flow |
| Project delete cascade | High | Manual delete + verify sync |
| Provider initialization order | Medium | App cold start on device |
| Cross-feature gallery/export | Medium | Open gallery, export entry |
| BaseListProvider migration | Medium | CRUD operations on any list screen |

---

## Migration/Cleanup

### Dead Code After Refactoring
- `ConstructionInspectorApp` constructor's 37 named parameters → replaced by `context.read` inside feature modules
- `_runApp()` function body → replaced by `app_providers.dart` composition
- `seedBuiltinForms()` and `_registerFormScreens()` → move into forms feature module
- `updateSyncContext()` → moves into sync feature module
- `_initDebugLogging()` → moves into core module

### Singleton Registries
5 hidden singletons move into respective feature modules (no longer hidden):
- `FormValidatorRegistry.instance` → forms module
- `FormCalculatorRegistry.instance` → forms module
- `FormScreenRegistry.instance` → forms module
- `FormQuickActionRegistry.instance` → forms module
- `SyncRegistry.instance` → sync module

### Import Cleanup
- Repository interfaces keep original names (e.g., `LocationRepository`)
- Concrete implementations renamed to `*Impl` (e.g., `LocationRepositoryImpl`)
- Barrel files updated per feature

### File Count Impact
| Type | Added | Modified | Deleted |
|------|-------|----------|---------|
| Feature modules (`*_providers.dart`) | 17 | — | — |
| `app_providers.dart` | 1 | — | — |
| Domain dirs (entities/repos/usecases) | ~51 dirs | — | — |
| Use case files | ~60-80 | — | — |
| Repository interfaces | ~20 | — | — |
| Repository impls (rename) | — | ~20 | — |
| Provider files (rewire) | — | ~25 | — |
| `main.dart` | — | 1 (gutted) | — |
| Screen fixes (layer violations) | — | 5 | — |

Estimated ~100 new files, ~50 modified files, 0 deleted (renames only).

---

## Existing Codebase Reference

### Current Provider Inventory (38 in MultiProvider)
| Provider | Feature | Type | Byte Size | Notes |
|----------|---------|------|-----------|-------|
| AuthProvider | auth | ChangeNotifier | 35,170 | 977 lines, 48 methods — heaviest extraction |
| ProjectProvider | projects | ChangeNotifier | 27,798 | 800 lines, 54 symbols — second heaviest |
| InspectorFormProvider | forms | ChangeNotifier | 14,551 | Calculator dispatch, row normalization |
| SyncProvider | sync | ChangeNotifier | 11,403 | Delegates to SyncOrchestrator — leave alone |
| EntryEditingController | entries | ChangeNotifier | 9,350 | In presentation/controllers/ |
| EntryQuantityProvider | quantities | ChangeNotifier | 8,749 | |
| AppConfigProvider | auth | ChangeNotifier | 8,701 | Direct Supabase call to fix |
| AdminProvider | settings | ChangeNotifier | 8,262 | |
| EquipmentProvider | contractors | ChangeNotifier | 7,926 | Extends BaseListProvider |
| TodoProvider | todos | ChangeNotifier | 7,518 | Multi-criteria sort logic |
| PhotoProvider | photos | ChangeNotifier | 5,861 | |
| GalleryProvider | gallery | ChangeNotifier | 5,542 | Cross-feature deps |
| CalculatorProvider | calculator | ChangeNotifier | 5,410 | |
| ProjectAssignmentProvider | projects | ChangeNotifier | 5,270 | |
| ProjectSettingsProvider | projects | ChangeNotifier | 5,268 | |
| CalendarFormatProvider | entries | ChangeNotifier | 3,478 | |
| EntryExportProvider | entries | ChangeNotifier | 3,159 | Cross-feature: reads FormExportProvider |
| DocumentProvider | forms | ChangeNotifier | 3,131 | |
| ThemeProvider | settings | ChangeNotifier | 2,917 | |
| FormExportProvider | forms | ChangeNotifier | 2,653 | |
| ProjectImportRunner | projects | ChangeNotifier | 2,284 | |
| ProjectSyncHealthProvider | projects | ChangeNotifier | 1,522 | |
| ExtractionJobRunner | pdf | ChangeNotifier | 17,360 | |
| PreferencesService | core | ChangeNotifier | 5,786 | |
| + 14 Provider.value registrations | various | Provider | — | Services, DB, Sync |

### Current Repository Inventory (22 repositories)
| Repository | Feature | Base Class | Byte Size |
|------------|---------|------------|-----------|
| FormResponseRepository | forms | — | 12,761 |
| ProjectRepository | projects | — | 8,189 |
| DailyEntryRepository | entries | — | 8,207 |
| PhotoRepository | photos | — | 7,779 |
| InspectorFormRepository | forms | — | 7,440 |
| PersonnelTypeRepository | contractors | ProjectScopedRepository | 4,968 |
| EntryQuantityRepository | quantities | ProjectScopedRepository | 4,617 |
| BidItemRepository | quantities | ProjectScopedRepository | 4,548 |
| ContractorRepository | contractors | ProjectScopedRepository | 4,519 |
| EquipmentRepository | contractors | ProjectScopedRepository | 4,478 |
| AdminRepository | settings | — | 4,488 |
| LocationRepository | locations | ProjectScopedRepository | 4,067 |
| DocumentRepository | entries | — | 3,905 |
| ProjectAssignmentRepository | projects | — | 2,916 |
| UserAttributionRepository | auth | — | 2,603 |
| FormExportRepository | forms | — | 2,502 |
| EntryExportRepository | entries | — | 2,187 |
| UserProfileRepository | auth | — | 1,106 |
| CompanyRepository | auth | — | 919 |

### Existing Base Classes (preserve and extend)
- `BaseRepository<T>` — abstract: getById, getAll, getPaged, getCount, save, delete
- `ProjectScopedRepository<T>` extends BaseRepository — adds: getByProjectId, getByProjectIdPaged, getCountByProject, create, update
- `BaseLocalDatasource<T>` — abstract: getById, getAll, insert, update, delete, insertAll
- `BaseListProvider<T, R extends ProjectScopedRepository<T>>` — CRUD state management with loadItems, createItem, updateItem, deleteItem, canWrite check
- `PagedListProvider<T, R extends ProjectScopedRepository<T>>` — extends BaseListProvider with pagination

### Layer Violations to Fix (13 total)
| File | Violation | Fix |
|------|-----------|-----|
| `settings/presentation/screens/settings_screen.dart:72` | `Supabase.instance.client` update gauge_number | Move to UserProfileRepository |
| `settings/presentation/screens/settings_screen.dart:118` | `Supabase.instance.client` update initials | Move to UserProfileRepository |
| `auth/presentation/providers/app_config_provider.dart:148` | `Supabase.instance.client` query app_config | Move to AppConfigRepository |
| `projects/presentation/providers/project_provider.dart:585` | `Supabase.instance.client.rpc` admin_soft_delete | Move to DeleteProjectUseCase |
| `projects/presentation/screens/project_setup_screen.dart:181` | `Supabase.instance.client` query user_profiles | Move to CompanyMembersRepository |
| + 8 files with raw `DatabaseService.database.query()` in presentation | Direct DB access | Move behind repository/use case |

### Sync Feature (Reference Architecture — Do Not Modify Logic)
```
lib/features/sync/
├── domain/          # SyncResult, SyncAdapterStatus (thin)
├── application/     # SyncOrchestrator (634 lines), SyncLifecycleManager, BackgroundSyncHandler, FcmHandler
├── engine/          # SyncEngine (2021 lines), ChangeTracker, ConflictResolver, IntegrityChecker, etc.
├── adapters/        # 22 table adapters
├── config/          # SyncConfig
├── data/            # MockSyncAdapter
└── presentation/    # SyncProvider (thin wrapper), screens, widgets
```
Only touch: move registration into `sync_providers.dart`. No logic changes.
