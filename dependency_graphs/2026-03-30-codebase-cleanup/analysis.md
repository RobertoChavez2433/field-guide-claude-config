# Codebase Cleanup — Dependency Analysis

**Date**: 2026-03-30
**Source**: 5 parallel opus audit agents (CodeMunch dead code, TODOs/scaffolds, provider/route wiring, deferred implementations, layer violations, UI-unreachable features)

## DI Architecture

### File Structure
- `lib/core/di/app_initializer.dart` — Creates all datasources, repositories, services, use cases
- `lib/core/di/app_providers.dart` — `buildAppProviders(deps)` composes all feature provider lists
- `lib/main.dart` — `_runApp()` calls `AppInitializer.initialize()`, then `buildAppProviders(deps)`
- Per-feature DI: `lib/features/*/di/*_providers.dart`

### Dependency Classes (app_initializer.dart)
- `CoreDeps`: DatabaseService, PreferencesService, PhotoService, ImageService
- `AuthDeps`: AuthService, AuthProvider, AppConfigProvider
- `ProjectDeps`: ProjectRepository + 10 project-related deps
- `EntryDeps`: DailyEntryRepository, EntryExportRepository, DocumentRepository, DocumentService
- `FormDeps`: InspectorFormRepository, FormResponseRepository, FormExportRepository, FormPdfService
- `SyncDeps`: SyncOrchestrator, SyncLifecycleManager
- `FeatureDeps`: Location/Contractor/Equipment/PersonnelType/BidItem/EntryQuantity/Photo/Calculator/Todo repos + PdfService + WeatherService
- `AppDependencies`: Aggregates all above with convenience accessors

### Provider Tier Order (app_providers.dart)
- Tier 0: Settings (PreferencesService)
- Tier 3: Auth (AuthProvider, AppConfigProvider)
- Tier 4: Projects → Locations → Contractors → Quantities → Photos → **Forms** → **Entries** (forms MUST come before entries) → Calculator → Gallery → Todos → PDF → Weather
- Tier 5: Sync

## Router Structure (app_router.dart)
- Shell routes with bottom nav: `/` (home), `/calendar`, `/toolbox`, `/settings`
- Full-screen routes: `/project/setup/:projectId`, `/entry/:projectId/:date`, etc.
- Form routes: `/forms` (gallery), `/form/:responseId` (dispatches via FormScreenRegistry)
- Toolbox routes: `/calculator`, `/gallery`, `/todos`
- Sync routes: `/sync/dashboard`, `/sync/conflicts`
- Quantity routes: `/quantity-calculator/:entryId` (EXISTS but unreachable)
- Personnel route: `/personnel-types/:projectId` (EXISTS but unreachable)

## Key Files Per Plan Area

### Plan Writer 1: Critical Fixes + DI Wiring
- `lib/features/settings/presentation/screens/trash_screen.dart` — creates DatabaseService() inline (C1)
- `lib/features/photos/presentation/widgets/photo_thumbnail.dart` — ImageService per widget (C2)
- `lib/features/settings/presentation/providers/support_provider.dart` — direct Supabase access (C3)
- `lib/features/entries/presentation/screens/home_screen.dart:183-187` — 3 inline datasources
- `lib/features/entries/presentation/screens/entry_editor_screen.dart:159-162` — 3 inline datasources
- `lib/services/image_service.dart:131-153` — thumbnail doesn't resize
- `lib/core/logging/logger.dart:113-117` — log rotation not implemented
- `lib/features/settings/di/settings_providers.dart` — needs TrashRepository, SoftDeleteService, PermissionService
- `lib/core/di/app_initializer.dart` — needs new service registrations

### Plan Writer 2: UI-Unreachable Feature Wiring
- `lib/features/quantities/presentation/screens/quantity_calculator_screen.dart` — full screen, no nav to it
- `lib/features/settings/presentation/screens/personnel_types_screen.dart` — full screen, no nav to it
- `lib/features/entries/presentation/providers/entry_export_provider.dart` — never called from UI
- `lib/features/forms/presentation/providers/form_export_provider.dart` — never called from UI
- `lib/features/projects/data/models/project.dart` — MDOT fields + header fields (copyWith has them all)
- `lib/features/projects/presentation/screens/project_setup_screen.dart:366-399` — _buildDetailsTab missing MDOT/header fields
- `lib/core/config/app_terminology.dart` — setMode() never called
- `lib/features/forms/presentation/screens/form_viewer_screen.dart` — built but not routable
- `lib/core/design_system/` — 22 components unused

### Plan Writer 3: Deferred Implementations + Layer Fixes
- `lib/features/entries/presentation/widgets/entry_forms_section.dart:304` — _openDocument placeholder
- `lib/features/settings/data/repositories/support_repository.dart:8` — sync deferred
- `lib/features/settings/data/repositories/consent_repository.dart:9` — sync deferred
- `lib/features/sync/presentation/screens/conflict_viewer_screen.dart` — raw SQL in presentation
- `lib/features/sync/presentation/widgets/deletion_notification_banner.dart` — raw SQL in presentation
- `lib/core/router/app_router.dart:694` — hardcoded formType
- `lib/features/forms/di/forms_providers.dart:46` — deprecated NormalizeProctorRowUseCase
- `lib/features/forms/presentation/providers/inspector_form_provider.dart:385` — deprecated addProctorRow
- `lib/main.dart:76-79` — Sentry tracesSampleRate = 0.0
- `lib/features/settings/presentation/providers/consent_provider.dart:26` — hardcoded policy version
- `lib/features/projects/data/repositories/project_repository.dart:68` — SyncControl suppression inline
- `lib/features/auth/data/repositories/user_attribution_repository.dart:77` — inline Supabase
- `lib/features/projects/data/services/project_lifecycle_service.dart:362` — inline Supabase RPC
- `lib/core/theme/app_theme.dart` — ~80 self-deprecated constant references
- 4 deprecated deleteByEntryId methods in datasources

### Plan Writer 4: Scaffolded Repository Methods → Provider/UI Wiring
- DailyEntry: 7 methods (getByDateRange, getByLocationId, getByStatus, updateStatus, batchUpdateStatus, getPagedAll, getCountAll)
- Todo: 8 methods (getByEntryId, getByPriority, getOverdue, getDueToday, getIncompleteCount, getIncomplete, getCompleted, deleteByProjectId)
- Document: 6 methods (getByFileType, getByProjectId, getAll, getPaged, getCount, save)
- EntryExport: 6 methods (getByProjectId, getByEntryId, getAll, getPaged, getCount, save)
- FormExport: 7 methods (getByProjectId, getByEntryId, getByFormResponseId, getAll, getPaged, getCount, save)
- Photo: 3 methods (deletePhotosForEntry, getPhotoCountForEntry, getPhotoCountForProject)
- EntryQuantity: 4 methods (getByBidItemId, deleteByEntryId, deleteByBidItemId, getCountByEntry)

## Blast Radius Summary
- **Direct changes**: ~50 files
- **Dependent files**: ~80 files (callers of modified APIs)
- **Tests**: ~30 test files need updates
- **New files**: ~15 (new datasources, repositories, services)
