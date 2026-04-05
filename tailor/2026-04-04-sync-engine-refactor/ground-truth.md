# Ground Truth

All literals verified against the actual codebase as of 2026-04-04.

## File Paths

| Path | Status | Notes |
|------|--------|-------|
| `lib/features/sync/engine/sync_engine.dart` | VERIFIED | 2374 lines, SyncEngine class at line 83 |
| `lib/features/sync/application/sync_orchestrator.dart` | VERIFIED | 730 lines, SyncOrchestrator at line 33 |
| `lib/features/sync/presentation/providers/sync_provider.dart` | VERIFIED | 368 lines, SyncProvider at line 18 |
| `lib/features/sync/adapters/table_adapter.dart` | VERIFIED | 180 lines, abstract class at line 15 |
| `lib/features/sync/engine/sync_registry.dart` | VERIFIED | 107 lines, registerSyncAdapters() + SyncRegistry class |
| `lib/features/sync/domain/sync_types.dart` | VERIFIED | 109 lines, SyncResult + SyncAdapterStatus + SyncMode + DirtyScope |
| `lib/features/sync/application/sync_lifecycle_manager.dart` | VERIFIED | 261 lines, SyncLifecycleManager at line 18 |
| `lib/features/sync/application/realtime_hint_handler.dart` | VERIFIED | ~300 lines, RealtimeHintHandler at line 29 |
| `lib/features/sync/application/background_sync_handler.dart` | VERIFIED | ~120 lines, BackgroundSyncHandler at line 20 |
| `lib/features/sync/application/sync_initializer.dart` | VERIFIED | 197 lines, SyncInitializer at line 37 |
| `lib/features/sync/application/sync_enrollment_service.dart` | VERIFIED | 124 lines, SyncEnrollmentService at line 14 |
| `lib/features/sync/application/sync_engine_factory.dart` | VERIFIED | 63 lines, SyncEngineFactory at line 11 |
| `lib/features/sync/application/sync_orchestrator_builder.dart` | VERIFIED | 72 lines, SyncOrchestratorBuilder at line 12 |
| `lib/features/sync/config/sync_config.dart` | VERIFIED | 47 lines, SyncEngineConfig class |
| `lib/features/sync/di/sync_providers.dart` | VERIFIED | SyncProviders.initialize + .providers |
| `lib/features/sync/engine/change_tracker.dart` | VERIFIED | ChangeTracker with getPendingCount |
| `lib/features/sync/engine/conflict_resolver.dart` | VERIFIED | ConflictResolver class |
| `lib/features/sync/engine/integrity_checker.dart` | VERIFIED | IntegrityChecker class |
| `lib/features/sync/engine/dirty_scope_tracker.dart` | VERIFIED | DirtyScopeTracker class |
| `lib/features/sync/engine/orphan_scanner.dart` | VERIFIED | OrphanScanner class |
| `lib/features/sync/engine/storage_cleanup.dart` | VERIFIED | StorageCleanup class |
| `lib/features/sync/engine/sync_mutex.dart` | VERIFIED | SyncMutex class |
| 22 adapter files in `lib/features/sync/adapters/` | VERIFIED | All 22 + table_adapter.dart + type_converters.dart = 24 files |

## Table Names (from adapter tableName overrides)

| Adapter Class | `tableName` Value | Status |
|---------------|-------------------|--------|
| ProjectAdapter | `projects` | VERIFIED |
| ProjectAssignmentAdapter | `project_assignments` | VERIFIED |
| LocationAdapter | `locations` | VERIFIED |
| ContractorAdapter | `contractors` | VERIFIED |
| EquipmentAdapter | `equipment` | VERIFIED |
| BidItemAdapter | `bid_items` | VERIFIED |
| PersonnelTypeAdapter | `personnel_types` | VERIFIED |
| DailyEntryAdapter | `daily_entries` | VERIFIED |
| PhotoAdapter | `photos` | VERIFIED |
| EntryEquipmentAdapter | `entry_equipment` | VERIFIED |
| EntryQuantitiesAdapter | `entry_quantities` | VERIFIED |
| EntryContractorsAdapter | `entry_contractors` | VERIFIED |
| EntryPersonnelCountsAdapter | `entry_personnel_counts` | VERIFIED |
| InspectorFormAdapter | `inspector_forms` | VERIFIED |
| FormResponseAdapter | `form_responses` | VERIFIED |
| FormExportAdapter | `form_exports` | VERIFIED |
| EntryExportAdapter | `entry_exports` | VERIFIED |
| DocumentAdapter | `documents` | VERIFIED |
| TodoItemAdapter | `todo_items` | VERIFIED |
| CalculationHistoryAdapter | `calculation_history` | VERIFIED |
| SupportTicketAdapter | `support_tickets` | VERIFIED |
| ConsentRecordAdapter | `user_consent_records` | VERIFIED |

## SyncConfig Constants

| Constant | Value | Status |
|----------|-------|--------|
| `pushBatchLimit` | 500 | VERIFIED (sync_config.dart:4) |
| `pushAnomalyThreshold` | 1000 | VERIFIED |
| `maxRetryCount` | 5 | VERIFIED |
| `pullPageSize` | 100 | VERIFIED |
| `pullSafetyMargin` | Duration(seconds: 5) | VERIFIED |
| `integrityCheckInterval` | Duration(hours: 4) | VERIFIED |
| `staleLockTimeout` | Duration(minutes: 15) | VERIFIED |
| `changeLogRetention` | Duration(days: 7) | VERIFIED |
| `conflictLogRetention` | Duration(days: 7) | VERIFIED |
| `conflictWarningAge` | Duration(days: 30) | VERIFIED |
| `retryBaseDelay` | Duration(seconds: 1) | VERIFIED |
| `retryMaxDelay` | Duration(seconds: 16) | VERIFIED |
| `circuitBreakerThreshold` | 1000 | VERIFIED |
| `conflictPingPongThreshold` | 3 | VERIFIED |
| `orphanMinAge` | Duration(hours: 24) | VERIFIED |
| `orphanMaxPerCycle` | 50 | VERIFIED |
| `dirtyScopeMaxAge` | Duration(hours: 2) | VERIFIED |

## Enum Values

| Enum | Values | Status |
|------|--------|--------|
| `SyncAdapterStatus` | idle, syncing, success, error, offline, authRequired | VERIFIED (sync_types.dart:69) |
| `SyncMode` | quick, full, maintenance | VERIFIED (sync_types.dart:72-81) |
| `ScopeType` | direct, viaProject, viaEntry, viaContractor | VERIFIED (scope_type.dart) |

## Error Code Patterns (verified in SyncEngine._handlePushError)

| Code/Pattern | Classification | Source |
|-------------|---------------|--------|
| `401`, `PGRST301`, `JWT` | Auth refresh → retry | sync_engine.dart:1413-1421 |
| `429`, `503`, `Too Many`, `Service Unavailable` | Rate limit → backoff retry | sync_engine.dart:1423-1438 |
| `23505` | Constraint violation → retry (2x) then permanent | sync_engine.dart:1440-1455 |
| `42501` | RLS denied → permanent | sync_engine.dart:1457-1467 |
| `23503` | FK violation → permanent | sync_engine.dart:1469-1479 |
| `SocketException`, `TimeoutException` | Network → backoff retry | sync_engine.dart:1485-1500 |

## Error Patterns in SyncOrchestrator._isTransientError

| Category | Patterns | Status |
|----------|----------|--------|
| Transient | `DNS`, `dns`, `SocketException`, `host lookup`, `TimeoutException`, `Connection refused`, `Connection reset`, `Network is unreachable`, `offline` | VERIFIED |
| Non-transient | `auth`, `Auth`, `RLS`, `permission`, `Permission`, `not configured`, `already in progress`, `has no column`, `DatabaseException`, `no such column`, `table has no column`, `remote record not found`, `0 rows affected`, `Soft-delete push failed` | VERIFIED |
| Special case | `No auth context available for sync` → transient (startup race) | VERIFIED |

## Error Patterns in SyncProvider._sanitizeSyncError

| Patterns | Action | Status |
|----------|--------|--------|
| `42501`, `23505`, `23503`, `permission denied`, `violates row-level security` | Generic safe message | VERIFIED (sync_provider.dart:328-348) |

## @visibleForTesting Methods in SyncEngine

| Method | Line | Status |
|--------|------|--------|
| `pushDeleteRemote` | 761 | VERIFIED |
| `upsertRemote` | 785 | VERIFIED |
| `insertOnlyRemote` | 806 | VERIFIED |
| `fetchServerUpdatedAt` | 833 | VERIFIED |
| `shouldSkipLwwPush` | 856 | VERIFIED |
| `pushDeleteForTesting` | 897 | VERIFIED |
| `validateAndStampCompanyId` | 910 | VERIFIED |
| `pushUpsertForTesting` | 935 | VERIFIED |

**Note**: Spec says 9, actual count is 8. Also `SyncOrchestrator.isTransientError` (line 504) and `SyncOrchestrator.forTesting` (line 138) have `@visibleForTesting`.

## Triple Status Tracking (verified)

| State | SyncEngine | SyncOrchestrator | SyncProvider |
|-------|-----------|-----------------|-------------|
| Is syncing | `_insidePushOrPull` (line 99) | `_isSyncing` (line 79) | `_isSyncing` (line 29) |
| Status enum | none | `_status` (line 82) | `_status` (line 21) |
| Last sync time | writes `sync_metadata` | `_lastSyncTime` (line 84) | `_lastSyncTime` (line 22) / falls back to orchestrator |

## Layer Violations (verified)

| Violation | Location | Status |
|-----------|----------|--------|
| SQL in SyncOrchestrator.getPendingBuckets | Lines 607-666 (3 rawQuery calls) | VERIFIED |
| SQL in SyncOrchestrator.getIntegrityResults | Lines 682-701 | VERIFIED |
| SQL in SyncOrchestrator.getUndismissedConflictCount | Lines 704-710 | VERIFIED |
| SQL in SyncOrchestrator.initialize | Lines 165-198 (sync_metadata query) | VERIFIED |
| SQL in SyncOrchestrator.syncLocalAgencyProjects | Lines 304-314 (sync_metadata query) | VERIFIED |
| SyncProvider exposes raw orchestrator | Line 22: `SyncOrchestrator get orchestrator` | VERIFIED |
| SyncProvider._sanitizeSyncError Postgres codes | Lines 328-348 | VERIFIED |
| SyncOrchestrator._appConfigProvider.recordSyncSuccess() | Line 324 | VERIFIED |
| SyncOrchestrator._userProfileSyncDatasource.pullCompanyMembers | Lines 331-340 | VERIFIED |
| SyncEngine depends on `image` package | Import line 7: `package:image/image.dart` | VERIFIED |

## Lint Rules for New Files

| New File Path | Active Lint Rules | Key Constraints |
|---------------|-------------------|-----------------|
| `lib/features/sync/engine/push_handler.dart` | Global rules (A1-A17, D1-D10, S2, S4, S8) | No presentation imports |
| `lib/features/sync/engine/pull_handler.dart` | Global rules | No presentation imports |
| `lib/features/sync/engine/supabase_sync.dart` | Global rules | No presentation imports |
| `lib/features/sync/engine/local_sync_store.dart` | Global rules | No presentation imports |
| `lib/features/sync/engine/file_sync_handler.dart` | Global rules | No presentation imports |
| `lib/features/sync/engine/sync_error_classifier.dart` | Global rules | No presentation imports, pure logic |
| `lib/features/sync/engine/enrollment_handler.dart` | Global rules | No presentation imports |
| `lib/features/sync/engine/fk_rescue_handler.dart` | Global rules | No presentation imports |
| `lib/features/sync/engine/maintenance_handler.dart` | Global rules | No presentation imports |
| `lib/features/sync/application/sync_coordinator.dart` | Global rules | No presentation imports |
| `lib/features/sync/application/sync_retry_policy.dart` | Global rules | No presentation imports |
| `lib/features/sync/application/connectivity_probe.dart` | Global rules | No presentation imports |
| `lib/features/sync/application/sync_trigger_policy.dart` | Global rules | No presentation imports |
| `lib/features/sync/application/post_sync_hooks.dart` | Global rules | No presentation imports |
| `lib/features/sync/application/sync_query_service.dart` | Global rules | No presentation imports |
| `lib/features/sync/domain/sync_status.dart` | Global rules | Pure Dart, no Flutter/framework deps |
| `lib/features/sync/domain/sync_error.dart` | Global rules | Pure Dart |
| `lib/features/sync/domain/sync_diagnostics.dart` | Global rules | Pure Dart |
| `lib/features/sync/domain/sync_event.dart` | Global rules | Pure Dart |

**None** of the new files match `*/presentation/*`, `*/di/*`, or `*/data/models/*` path patterns, so only global lint rules apply.
