# Ground Truth

## Route Paths

| Literal | Source File | Line | Status |
|---------|------------|------|--------|
| `/sync/dashboard` | `lib/core/router/routes/sync_routes.dart` | 10 | VERIFIED |
| `/sync/conflicts` | `lib/core/router/routes/sync_routes.dart` | 14 | VERIFIED |
| `context.push('/sync/dashboard')` | `lib/features/sync/presentation/widgets/sync_status_icon.dart` | 28 | VERIFIED |

## DB Table Names

| Literal | Source File | Line | Status |
|---------|------------|------|--------|
| `change_log` | `lib/core/database/database_service.dart` | multiple | VERIFIED |
| `sync_control` | `lib/core/database/database_service.dart` | 84 | VERIFIED |
| `sync_metadata` | `lib/core/database/database_service.dart` | 208, 984 | VERIFIED |
| `synced_projects` | `lib/core/database/database_service.dart` | 1376-1401 | VERIFIED |

## Enum Values

| Literal | Source File | Line | Status |
|---------|------------|------|--------|
| `ScopeType.direct` | `lib/features/sync/engine/scope_type.dart` | 15 | VERIFIED |
| `ScopeType.viaProject` | `lib/features/sync/engine/scope_type.dart` | 18 | VERIFIED |
| `ScopeType.viaEntry` | `lib/features/sync/engine/scope_type.dart` | 23 | VERIFIED |
| `ScopeType.viaContractor` | `lib/features/sync/engine/scope_type.dart` | 28 | VERIFIED |
| `SyncAdapterStatus.idle` | `lib/features/sync/domain/sync_types.dart` | 61 | VERIFIED |
| `SyncAdapterStatus.syncing` | `lib/features/sync/domain/sync_types.dart` | 62 | VERIFIED |
| `SyncAdapterStatus.success` | `lib/features/sync/domain/sync_types.dart` | 63 | VERIFIED |
| `SyncAdapterStatus.error` | `lib/features/sync/domain/sync_types.dart` | 64 | VERIFIED |
| `SyncAdapterStatus.offline` | `lib/features/sync/domain/sync_types.dart` | 65 | VERIFIED |
| `SyncAdapterStatus.authRequired` | `lib/features/sync/domain/sync_types.dart` | 66 | VERIFIED |

## SyncEngineConfig Constants

| Literal | Value | Source File | Line | Status |
|---------|-------|------------|------|--------|
| `pushBatchLimit` | 500 | `lib/features/sync/config/sync_config.dart` | 5 | VERIFIED |
| `pushAnomalyThreshold` | 1000 | `lib/features/sync/config/sync_config.dart` | 6 | VERIFIED |
| `maxRetryCount` | 5 | `lib/features/sync/config/sync_config.dart` | 7 | VERIFIED |
| `pullPageSize` | 100 | `lib/features/sync/config/sync_config.dart` | 10 | VERIFIED |
| `pullSafetyMargin` | 5 seconds | `lib/features/sync/config/sync_config.dart` | 11 | VERIFIED |
| `integrityCheckInterval` | 4 hours | `lib/features/sync/config/sync_config.dart` | 14 | VERIFIED |
| `staleLockTimeout` | 15 minutes | `lib/features/sync/config/sync_config.dart` | 19 | VERIFIED |
| `changeLogRetention` | 7 days | `lib/features/sync/config/sync_config.dart` | 22 | VERIFIED |
| `circuitBreakerThreshold` | 1000 | `lib/features/sync/config/sync_config.dart` | 31 | VERIFIED |
| `orphanMinAge` | 24 hours | `lib/features/sync/config/sync_config.dart` | 41 | VERIFIED |

## Key Method Signatures

| Method | File:Line | Signature | Status |
|--------|-----------|-----------|--------|
| `pushAndPull` | `sync_engine.dart:216` | `Future<SyncEngineResult> pushAndPull()` | VERIFIED |
| `_push` | `sync_engine.dart:421` | `Future<SyncEngineResult> _push()` | VERIFIED |
| `_pull` | `sync_engine.dart:1452` | `Future<SyncEngineResult> _pull()` | VERIFIED |
| `pullOnly` | `sync_engine.dart:406` | `Future<SyncEngineResult> pullOnly()` | VERIFIED |
| `syncLocalAgencyProjects` | `sync_orchestrator.dart:241` | `Future<SyncResult> syncLocalAgencyProjects()` | VERIFIED |
| `_doSync` | `sync_orchestrator.dart:413` | `Future<SyncResult> _doSync()` | VERIFIED |
| `_handleResumed` | `sync_lifecycle_manager.dart:74` | `Future<void> _handleResumed()` | VERIFIED |
| `handleForegroundMessage` | `fcm_handler.dart:100` | `void handleForegroundMessage(RemoteMessage message)` | VERIFIED |
| `SyncProvider.sync` | `sync_provider.dart:283` | `Future<SyncResult> sync()` | VERIFIED |

## Widget/Key Names

| Literal | Source File | Line | Status |
|---------|------------|------|--------|
| `TestingKeys.syncProgressSpinner` | `sync_status_icon.dart` | 26 | VERIFIED |
| `SyncStatusIcon` used in `home_screen.dart` | `home_screen.dart` | 375 | VERIFIED |

## Flagged Discrepancies

| Item | Expected | Actual | Impact |
|------|----------|--------|--------|
| SyncStatusIcon in scaffold_with_nav_bar | Spec wants global sync action in "main app chrome" | SyncStatusIcon only in HomeScreen app bar, NOT in scaffold_with_nav_bar | Must add to global scaffold or all screen app bars |
| Supabase Realtime/Broadcast | Spec requires foreground invalidation hints | **Zero** Supabase Realtime code exists anywhere in codebase | Must be built from scratch — new dependency, new handler |
| FCM hint payload | Spec expects company_id/project_id/table_name/changed_at | FCM only checks `type == 'daily_sync'`, triggers full sync | FCM handler must be extended to parse hint payloads |

## Lint Rules for New Files

| New File Path | Active Rules |
|---------------|-------------|
| `lib/features/sync/engine/dirty_scope_tracker.dart` | A1, A2, A9, S2, S4 (global rules) |
| `lib/features/sync/application/realtime_hint_handler.dart` | A1, A2, A6, A9 (global + application layer) |
