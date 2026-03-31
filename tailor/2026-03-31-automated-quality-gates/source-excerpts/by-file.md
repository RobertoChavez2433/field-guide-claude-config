# Source Excerpts — By File

## lib/core/di/app_providers.dart

### buildAppProviders (L37-138)
Full source in patterns/di-provider-pattern.md. Composes tier-ordered provider list from AppDependencies. Key insight: tier order matters (Tier 0 → 3 → 4 → 5). Each feature module exports a `*Providers()` function.

## lib/core/theme/field_guide_colors.dart

### FieldGuideColors class (L12-218)
Full source in patterns/three-tier-color-system.md. ThemeExtension with 16 semantic colors, 3 const theme instances (dark, light, highContrast), `of(context)` accessor.

## lib/core/theme/app_theme.dart

### AppTheme class (L9-1775+)
1775+ lines. 3 theme getters, ~40 @Deprecated color constants, 3 non-deprecated utility methods. Each @Deprecated annotation includes the replacement path. The theme getters (`darkTheme`, `lightTheme`, `highContrastTheme`) are NOT deprecated and register `FieldGuideColors` as a ThemeExtension.

## lib/core/di/app_initializer.dart

### AppDependencies class (L267-355)
Container with 7 sub-containers. 40+ convenience getters. `copyWith` supports hot-reload of PhotoService.

### AppInitializer.initialize (L359-822)
~460 lines. Creates DatabaseService, PreferencesService, all repositories, all datasources, all providers, SyncOrchestrator. This is the ONLY place Supabase.instance.client should be accessed.

## lib/services/soft_delete_service.dart

### SoftDeleteService class (L9-558)
Full source in patterns/soft-delete-pattern.md. 7 methods, 2 static table lists, 1 bucket map. Key methods: cascadeSoftDeleteProject, cascadeSoftDeleteEntry, restoreWithCascade, purgeExpiredRecords, hardDeleteWithSync.

## lib/shared/datasources/generic_local_datasource.dart

### GenericLocalDatasource class (L22-270)
23 methods. Full method list in patterns/datasource-pattern.md. Key: `_whereWithDeletedFilter` appends `deleted_at IS NULL` to all queries. `delete()` delegates to `softDelete()`.

## lib/core/logging/logger.dart

### Logger class (L27-1072)
51 methods total. 11 category loggers (sync, pdf, db, auth, ocr, nav, ui, photo, lifecycle, bg, error). File logging with rotation. HTTP posting. Sensitive data scrubbing. Full method list in patterns/logger-pattern.md.

## lib/shared/testing_keys/testing_keys.dart

### TestingKeys class (L64-1094)
90 static Key methods. Mix of const Keys and parameterized factory methods. Covers all 17 features. Full list available in file outline data.

## lib/features/sync/engine/sync_engine.dart

### SyncEngine class (L83-2060+)
~2000 lines. Core methods: pushAndPull, _push, _pull, _pushUpsert, _pushDelete, _pullTable. Uses ConflictAlgorithm.ignore with rowId==0 fallback (the correct pattern that 7 other locations need to adopt). LWW conflict resolution. Three-phase file upload. GPS EXIF stripping.

## lib/features/sync/engine/sync_registry.dart

### registerSyncAdapters (L29-61)
22 adapters in FK dependency order. 2 push-only (SupportTicket, ConsentRecord).

### SyncRegistry class (L63-107)
Singleton. `registerAdapters`, `adapterFor`, `dependencyOrder`.

## lib/features/sync/engine/change_tracker.dart

### ChangeTracker class (L43-196)
12 methods. Key: `getUnprocessedChanges` with batch limit and anomaly detection. `markProcessed`, `markFailed`, `pruneProcessed`, `isCircuitBreakerTripped`, `getPendingCount`, `purgeOldFailures`.

## lib/core/database/schema/sync_engine_tables.dart

### SyncEngineTables class (L5-177+)
`triggersForTable` generates INSERT/UPDATE/DELETE triggers for change_log. Schema definitions for sync_control, change_log, sync_metadata, conflict_log, storage_cleanup_queue, deletion_notifications, synced_projects.

## lib/core/database/database_service.dart

### DatabaseService class (L8-2023)
Singleton factory. `_onCreate` (L104) creates all tables. `_createIndexes` (L193). `_onUpgrade` (L280) handles 43+ migration versions. `_addColumnIfNotExists` utility.

## lib/core/router/app_router.dart

### AppRouter class (L77-745)
GoRouter-based. Onboarding routes set, non-restorable routes set. `_buildRouter` creates the full route tree with ShellRoute for nav bar.
