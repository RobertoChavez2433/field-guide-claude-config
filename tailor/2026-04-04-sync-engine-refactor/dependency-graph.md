# Dependency Graph

## Direct Changes

| File | Key Symbols | Change Type |
|------|-------------|-------------|
| `lib/features/sync/engine/sync_engine.dart` | `SyncEngine` (2374 lines, 42 methods) | Decompose into ~10 classes |
| `lib/features/sync/application/sync_orchestrator.dart` | `SyncOrchestrator` (730 lines) | Refactor into SyncCoordinator + extracted helpers |
| `lib/features/sync/presentation/providers/sync_provider.dart` | `SyncProvider` (368 lines, 36 methods) | Remove layer violations, subscribe to SyncStatus stream |
| `lib/features/sync/adapters/table_adapter.dart` | `TableAdapter` (180 lines) | Slim + add AdapterConfig for data-driven registration |
| `lib/features/sync/engine/sync_registry.dart` | `SyncRegistry` (107 lines) | Refactor from singleton to injectable instance |
| `lib/features/sync/application/sync_lifecycle_manager.dart` | `SyncLifecycleManager` (261 lines) | Extract trigger policy to SyncTriggerPolicy |
| `lib/features/sync/application/realtime_hint_handler.dart` | `RealtimeHintHandler` (~300 lines) | Extract trigger policy to SyncTriggerPolicy |
| `lib/features/sync/application/background_sync_handler.dart` | `BackgroundSyncHandler` (~120 lines) | Extract trigger coordination |
| `lib/features/sync/application/sync_initializer.dart` | `SyncInitializer` (160 lines) | Update wiring for new class boundaries |
| `lib/features/sync/domain/sync_types.dart` | `SyncResult`, `SyncMode`, `DirtyScope` | Add SyncStatus, SyncErrorKind, ClassifiedSyncError, SyncDiagnosticsSnapshot, SyncEvent |
| 22 adapter files | 22 `TableAdapter` subclasses | 13 become data-driven config, 9 remain as classes |

## New Files

| File | Class | Purpose |
|------|-------|---------|
| `lib/features/sync/engine/push_handler.dart` | `PushHandler` | Push orchestration extracted from SyncEngine |
| `lib/features/sync/engine/pull_handler.dart` | `PullHandler` | Pull orchestration extracted from SyncEngine |
| `lib/features/sync/engine/supabase_sync.dart` | `SupabaseSync` | All Supabase row I/O |
| `lib/features/sync/engine/local_sync_store.dart` | `LocalSyncStore` | All sync-related SQLite I/O |
| `lib/features/sync/engine/file_sync_handler.dart` | `FileSyncHandler` | Three-phase file upload + EXIF stripping |
| `lib/features/sync/engine/sync_error_classifier.dart` | `SyncErrorClassifier` | Single error categorization source |
| `lib/features/sync/engine/enrollment_handler.dart` | `EnrollmentHandler` | Enrollment from assignments |
| `lib/features/sync/engine/fk_rescue_handler.dart` | `FkRescueHandler` | FK rescue during pull |
| `lib/features/sync/engine/maintenance_handler.dart` | `MaintenanceHandler` | Integrity, orphan, pruning orchestration |
| `lib/features/sync/application/sync_coordinator.dart` | `SyncCoordinator` | Replaces SyncOrchestrator |
| `lib/features/sync/application/sync_retry_policy.dart` | `SyncRetryPolicy` | Retry + backoff + scheduling |
| `lib/features/sync/application/connectivity_probe.dart` | `ConnectivityProbe` | DNS/health checks |
| `lib/features/sync/application/sync_trigger_policy.dart` | `SyncTriggerPolicy` | Lifecycle/stale/hint trigger decisions |
| `lib/features/sync/application/post_sync_hooks.dart` | `PostSyncHooks` | Profile refresh, config freshness, enrollment |
| `lib/features/sync/application/sync_query_service.dart` | `SyncQueryService` | Dashboard-facing diagnostics queries |
| `lib/features/sync/domain/sync_status.dart` | `SyncStatus` | Immutable status value + stream |
| `lib/features/sync/domain/sync_error.dart` | `SyncErrorKind`, `ClassifiedSyncError` | Error categorization types |
| `lib/features/sync/domain/sync_diagnostics.dart` | `SyncDiagnosticsSnapshot` | Dashboard diagnostics snapshot |
| `lib/features/sync/domain/sync_event.dart` | `SyncEvent` | Typed lifecycle events |

## Upstream Dependencies (SyncEngine imports)

```
sync_engine.dart imports:
  ├── dart:async, dart:convert, dart:io, dart:math
  ├── package:flutter/foundation.dart
  ├── package:image/image.dart (EXIF stripping — moves to FileSyncHandler)
  ├── package:sqflite_common_ffi/sqflite_ffi.dart
  ├── package:supabase_flutter/supabase_flutter.dart
  ├── package:uuid/uuid.dart
  ├── core/logging/logger.dart
  ├── sync/adapters/table_adapter.dart
  ├── sync/config/sync_config.dart
  ├── sync/engine/change_tracker.dart
  ├── sync/engine/conflict_resolver.dart
  ├── sync/domain/sync_types.dart
  ├── sync/engine/dirty_scope_tracker.dart
  ├── sync/engine/integrity_checker.dart
  ├── sync/engine/orphan_scanner.dart
  ├── sync/engine/scope_type.dart
  ├── sync/engine/storage_cleanup.dart
  ├── sync/engine/sync_mutex.dart
  ├── sync/engine/sync_registry.dart
  └── shared/utils/safe_row.dart
```

## Downstream Dependents (who imports SyncEngine)

| File | How Used |
|------|----------|
| `sync/application/sync_orchestrator.dart` | Creates + calls `pushAndPull()` |
| `sync/application/sync_engine_factory.dart` | Factory creates `SyncEngine` instances |
| `sync/application/background_sync_callback.dart` | Creates `SyncEngine` for background |
| 4 test files | Direct engine construction for testing |

## SyncOrchestrator Downstream (30 importers)

| Category | Files |
|----------|-------|
| **Production lib/** | `app_dependencies.dart`, `driver_server.dart`, `scaffold_with_nav_bar.dart`, `projects_providers.dart`, `project_provider.dart`, `project_list_screen.dart`, `project_setup_screen.dart`, `admin_dashboard_screen.dart`, `sign_out_dialog.dart`, `fcm_handler.dart`, `realtime_hint_handler.dart`, `sync_enrollment_service.dart`, `sync_initializer.dart`, `sync_orchestrator_builder.dart`, `sync_providers.dart`, `sync_provider.dart` |
| **Test files** | 14 test files across engine, application, presentation |

## SyncProvider Downstream (13 confirmed importers)

| File | References |
|------|------------|
| `sync_dashboard_screen.dart` | 8 |
| `sync_status_icon.dart` | 4 |
| `sync_section.dart` | 3 |
| `scaffold_with_nav_bar.dart` | 1 |
| `sign_out_dialog.dart` | 1 |
| `sync_providers.dart` | 2 |
| 7 test files | Various |

## Data Flow (ASCII)

```
                    SyncProvider
                        │
                   reads/triggers
                        │
                        ▼
         SyncOrchestrator (→ SyncCoordinator)
           │              │              │
    ┌──────┘      ┌──────┘      ┌──────┘
    ▼              ▼              ▼
 Lifecycle    Realtime       Background
 Manager      Hint           Sync
    │         Handler        Handler
    │              │              │
    └──────┬───────┘──────────────┘
           ▼
      SyncEngine (→ slim coordinator)
      ┌────┼────┐
      ▼    ▼    ▼
   Push  Pull  Maintenance
  Handler Handler Handler
      │    │
      ▼    ▼
  SupabaseSync + LocalSyncStore
      │              │
      ▼              ▼
  Supabase       SQLite DB
```
