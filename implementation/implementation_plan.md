# Feature-First Reorganization Plan
## Construction Inspector Flutter App

**Note:** In the previous session, all 4 specialist agents completed successfully but encountered "Permission to use Write has been auto-denied (prompts unavailable)" errors when trying to write their outputs. This plan consolidates all their recommendations.

---

## Executive Summary

Reorganize from layer-first (`lib/{data, presentation, services}`) to feature-first (`lib/{core, shared, features/*}`) architecture across 15 phases. The app remains functional after each phase.

**Current State:** 108 Dart files, 264 tests
**Estimated Effort:** 10-12 working days

---

## Target Structure

```
lib/
├── main.dart
├── core/
│   ├── config/supabase_config.dart
│   ├── database/
│   │   ├── database_service.dart
│   │   └── seed_data_service.dart
│   ├── router/app_router.dart
│   ├── theme/app_theme.dart
│   └── transitions/page_transitions.dart
├── shared/
│   ├── models/sync_status.dart
│   ├── widgets/permission_dialog.dart
│   └── datasources/
│       ├── base_local_datasource.dart
│       └── base_remote_datasource.dart
└── features/
    ├── auth/
    │   ├── presentation/{screens/, providers/}
    │   └── services/auth_service.dart
    ├── projects/
    │   ├── data/{models/, datasources/, repositories/}
    │   └── presentation/{screens/, providers/}
    ├── locations/
    │   ├── data/{models/, datasources/, repositories/}
    │   └── presentation/providers/
    ├── contractors/
    │   ├── data/{models/, datasources/, repositories/}
    │   └── presentation/providers/
    ├── quantities/
    │   ├── data/{models/, datasources/, repositories/}
    │   └── presentation/{screens/, providers/}
    ├── entries/
    │   ├── data/{models/, datasources/, repositories/}
    │   └── presentation/{screens/, providers/}
    ├── photos/
    │   ├── data/{models/, datasources/, repositories/}
    │   ├── presentation/{widgets/, providers/}
    │   └── services/{photo_service, image_service}
    ├── pdf/
    │   ├── presentation/screens/
    │   └── services/{pdf_service, pdf_import_service}
    ├── sync/
    │   ├── domain/{sync_adapter, sync_result}
    │   ├── data/adapters/supabase_sync_adapter.dart
    │   ├── application/sync_orchestrator.dart
    │   └── presentation/providers/sync_provider.dart
    ├── dashboard/
    │   └── presentation/screens/project_dashboard_screen.dart
    ├── settings/
    │   └── presentation/{screens/, providers/theme_provider}
    └── weather/
        └── services/weather_service.dart
```

---

## Implementation Phases

### Phase 0: Preparation
1. Create git backup branch: `git checkout -b backup/pre-feature-first`
2. Create working branch: `git checkout -b feature/feature-first-reorganization`
3. Run `flutter test` and `flutter analyze` (baseline)
4. Create empty target directories

### Phase 1: Core Reorganization
**Files to move:**
- `lib/services/database_service.dart` → `lib/core/database/database_service.dart`
- `lib/services/seed_data_service.dart` → `lib/core/database/seed_data_service.dart`

**Update imports in:** main.dart, sync_service, all datasources

### Phase 2: Shared Layer Setup
**Files to move:**
- `lib/data/datasources/local/base_local_datasource.dart` → `lib/shared/datasources/`
- `lib/data/datasources/remote/base_remote_datasource.dart` → `lib/shared/datasources/`
- `lib/data/repositories/base_repository.dart` → `lib/shared/repositories/`
- `lib/data/models/sync_status.dart` → `lib/shared/models/`
- `lib/presentation/widgets/permission_dialog.dart` → `lib/shared/widgets/`

### Phase 3: Auth Feature (4 files)
Move: login_screen, register_screen, forgot_password_screen, auth_provider, auth_service

### Phase 4: Projects Feature (14 files)
Move: project.dart, project_mode.dart, location.dart + datasources + repositories + providers + screens

### Phase 5: Locations Feature (5 files)
Move: location model, datasources, repository, provider

### Phase 6: Contractors Feature (20 files - largest)
Move: contractor, equipment, personnel_type, entry_personnel, entry_equipment + all datasources/repositories/providers

### Phase 7: Quantities Feature (10 files)
Move: bid_item, entry_quantity + datasources + repositories + providers + screen

### Phase 8: Entries Feature (8 files + screens)
Move: daily_entry + home_screen, entry_wizard, report_screen, entries_list + providers

### Phase 9: Photos Feature (7 files)
Move: photo model + datasources + repository + provider + services + widgets

### Phase 10: PDF Feature (3 files)
Move: pdf_import_preview_screen, pdf_service, pdf_import_service

### Phase 11: Sync Feature (Centralized)
**Recommended: Centralize all sync code**
Move:
- sync_orchestrator.dart → `features/sync/application/`
- sync_adapter.dart → `features/sync/domain/`
- supabase_sync_adapter.dart → `features/sync/data/adapters/`
- All remote datasources → `features/sync/data/datasources/`
- sync_provider.dart → `features/sync/presentation/providers/`

**Deprecate:** `lib/services/sync_service.dart` (798 lines - use SyncOrchestrator instead)

### Phase 12: Dashboard Feature (1 file)
Move: project_dashboard_screen.dart

### Phase 13: Settings Feature (3 files)
Move: settings_screen, personnel_types_screen, theme_provider

### Phase 14: Weather Feature (1 file)
Move: weather_service.dart

### Phase 15: Final Cleanup
1. Delete old barrel exports (models.dart, repositories.dart, providers.dart, etc.)
2. Delete empty directories
3. Create root feature barrel: `lib/features/features.dart`
4. Update main.dart to use feature barrel imports
5. Update CLAUDE.md documentation

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Remote datasources | Centralize in `features/sync/` | Tightly coupled to sync logic, easier to add AASHTOWare |
| sync_status.dart | Move to `shared/models/` | Used by 9+ entities across features |
| supabase_config.dart | Stay in `core/config/` | Used by auth + sync + storage (shared) |
| database_service.dart | Move to `core/database/` | Infrastructure, not a domain feature |
| Providers | Stay under `presentation/` | UI state management is presentation concern |

---

## Barrel Export Strategy

**Feature barrel (public API):**
```dart
// lib/features/projects/projects.dart
export 'data/models/project.dart';
export 'data/repositories/project_repository.dart';
export 'presentation/providers/project_provider.dart';
// DON'T export: datasources, internal widgets, screens (accessed via router)
```

---

## Critical Files to Update

| File | Changes |
|------|---------|
| `lib/main.dart` | Replace 30+ imports with feature barrels |
| `lib/core/router/app_router.dart` | Update screen imports |
| `lib/services/sync_service.dart` | Mark deprecated, migrate to SyncOrchestrator |
| `lib/data/models/models.dart` | Remove after features migrated |

---

## Verification Steps

After each phase:
```bash
flutter analyze   # 0 errors
flutter test      # All 264 tests pass
flutter run -d windows  # Smoke test
```

Final verification:
- [ ] App launches without errors
- [ ] All screens navigate correctly
- [ ] Database operations work
- [ ] Sync functionality works
- [ ] Photo capture works
- [ ] PDF generation works
- [ ] Auth flows work

---

## Rollback Strategy

Each phase creates a working state. If issues arise:
```bash
git stash
# Fix issue
git stash pop
```

For major issues:
```bash
git reset --hard backup/pre-feature-first
```

---

## Benefits

1. **Feature isolation** - All auth code in `features/auth/`
2. **Clear dependencies** - Explicit cross-feature imports
3. **Scalability** - Add new features without touching existing code
4. **Better testability** - Feature-level test organization
5. **AASHTOWare ready** - Sync feature supports multiple backends
