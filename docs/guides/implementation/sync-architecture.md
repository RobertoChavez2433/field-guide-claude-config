# Sync Architecture Guide

## Overview

The sync system follows a decomposed architecture where a slim coordinator (`SyncEngine`, ~214 lines) delegates to focused handler classes. The system has four key design principles:

1. **I/O Boundaries** — All Supabase I/O goes through `SupabaseSync`; all sync SQLite I/O goes through `LocalSyncStore`. No handler touches I/O directly.
2. **Control Plane Separation** — Retry policy, connectivity checks, trigger decisions, and post-sync hooks are injected classes, not inline code.
3. **Status vs Diagnostics Split** — Transport state (`SyncStatus`) is separate from operational state (`SyncDiagnosticsSnapshot`) and lifecycle signals (`SyncEvent`).
4. **Data-Driven Adapters** — 13 of 22 adapters are declared as `AdapterConfig` data; only 9 with custom logic remain as classes.

## Engine Layer

### I/O Boundaries

| Class | File | Responsibility |
|-------|------|---------------|
| `SupabaseSync` | `engine/supabase_sync.dart` | All Supabase row I/O: upsert, delete, select, auth refresh on 401, rate limit handling. Pure I/O — no policy decisions. |
| `LocalSyncStore` | `engine/local_sync_store.dart` | All sync SQLite I/O: record reads/writes, cursor management, trigger suppression (`pulling='1'/'0'` in try/finally), column cache (`PRAGMA table_info`), server timestamp writeback, unknown column stripping. Composes `TriggerStateStore`, `LocalRecordStore`, `SyncMetadataStore`, `SyncedScopeStore`. |

### Handlers

| Class | File | Responsibility |
|-------|------|---------------|
| `PushHandler` | `engine/push_handler.dart` | Reads `ChangeTracker` for pending changes, iterates in FK order via `SyncRegistry`, calls `adapter.convertForRemote()`, routes through `LwwChecker` and `SupabaseSync`, handles errors via `PushErrorHandler` + `SyncErrorClassifier`. |
| `PullHandler` | `engine/pull_handler.dart` | Iterates adapters in FK order, manages `PullScopeState`, paginates via `SupabaseSync`, calls `adapter.convertForLocal()`, resolves conflicts via `ConflictResolver`, writes via `LocalSyncStore`, delegates FK rescue to `FkRescueHandler` and enrollment to `EnrollmentHandler`. |
| `FileSyncHandler` | `engine/file_sync_handler.dart` | Three-phase file upload: (1) upload to storage bucket, (2) strip EXIF GPS if configured, (3) update `remote_path` bookmark. |
| `EnrollmentHandler` | `engine/enrollment_handler.dart` | Checks `project_assignments` for new enrollments during pull. Adds newly assigned projects to `synced_projects`. |
| `FkRescueHandler` | `engine/fk_rescue_handler.dart` | When a pulled record references a FK parent that doesn't exist locally, fetches the parent from Supabase. Prevents FK constraint violations during pull. |
| `MaintenanceHandler` | `engine/maintenance_handler.dart` | Runs during `full` and `maintenance` sync modes: integrity check via `IntegrityChecker`, orphan scan via `OrphanScanner`, change_log pruning. |

### Slim Coordinator

`SyncEngine` (`engine/sync_engine.dart`, ~214 lines) knows NOTHING about SQLite, Supabase, or individual table adapters. It:
1. Acquires `SyncMutex`
2. Emits `SyncRunLifecycle` start event
3. Routes by `SyncMode`: push → pull → maintenance
4. Releases mutex in `finally`

### Supporting Classes

| Class | File | Purpose |
|-------|------|---------|
| `SyncErrorClassifier` | `engine/sync_error_classifier.dart` | Single source of truth for error classification. Maps Postgres codes, network errors, auth failures → `ClassifiedSyncError`. |
| `ChangeTracker` | `engine/change_tracker.dart` | Reads `change_log` table; groups pending changes by table. |
| `ConflictResolver` | `engine/conflict_resolver.dart` | Last-writer-wins resolution + manual resolution support. Writes to `conflict_log`. |
| `IntegrityChecker` | `engine/integrity_checker.dart` | Post-sync FK consistency validation. |
| `DirtyScopeTracker` | `engine/dirty_scope_tracker.dart` | Tracks remote change hints (project+table granular). Degrades to company-wide at >=500 scopes. Scopes expire after 2h. Drives quick sync pull filtering. |
| `OrphanScanner` | `engine/orphan_scanner.dart` | Detects local records with no valid FK parent. |
| `StorageCleanup` | `engine/storage_cleanup.dart` | Deletes local files after successful remote upload. |
| `SyncMutex` | `engine/sync_mutex.dart` | Prevents concurrent sync runs. Stale lock timeout: 15min. |
| `SyncRegistry` | `engine/sync_registry.dart` | Ordered list of all active `TableAdapter` instances. Order = FK dependency order. |
| `SyncControlService` | `engine/sync_control_service.dart` | Circuit-breaker state + health metrics for UI. |
| `LwwChecker` | `engine/lww_checker.dart` | Pre-push check: fetches server `updated_at`, skips push if local is stale. |
| `PushErrorHandler` | `engine/push_error_handler.dart` | Routes push errors through `SyncErrorClassifier`, logs, and decides retry. |

## Control Plane (Application Layer)

| Class | File | Purpose |
|-------|------|---------|
| `SyncCoordinator` | `application/sync_coordinator.dart` | Entry point for sync requests. Replaces `SyncOrchestrator`. Owns retry loop. Routes to `SyncEngine` (real) or `MockSyncAdapter` (test). No SQL queries — those moved to `SyncQueryService`. |
| `SyncRetryPolicy` | `application/sync_retry_policy.dart` | Pure logic: decides retryability from `ClassifiedSyncError`, calculates exponential backoff delay, schedules background retry timer. |
| `ConnectivityProbe` | `application/connectivity_probe.dart` | DNS/health checks. Injected into `SyncCoordinator` (not inline). |
| `SyncTriggerPolicy` | `application/sync_trigger_policy.dart` | Maps lifecycle events (app resume, reconnect), stale data thresholds, and realtime hints to a `SyncMode` decision. |
| `PostSyncHooks` | `application/post_sync_hooks.dart` | App-level post-sync follow-up: profile refresh, config sync. Inverted dependency — coordinator calls hooks, doesn't know what they do. |
| `SyncQueryService` | `application/sync_query_service.dart` | Dashboard queries: pending buckets, integrity results, conflict counts, sync metadata. Reads from `LocalSyncStore`. Produces `SyncDiagnosticsSnapshot`. |
| `SyncLifecycleManager` | `application/sync_lifecycle_manager.dart` | `WidgetsBindingObserver`: triggers sync on app foreground/reconnect via `SyncTriggerPolicy`. |
| `BackgroundSyncHandler` | `application/background_sync_handler.dart` | Schedules and runs background sync tasks. |
| `FcmHandler` | `application/fcm_handler.dart` | Processes FCM push notifications that signal remote changes. |
| `RealtimeHintHandler` | `application/realtime_hint_handler.dart` | Subscribes to Supabase Realtime channels. Marks `DirtyScopeTracker` on hints. Triggers quick sync. |
| `SyncEnrollmentService` | `application/sync_enrollment_service.dart` | Manages `synced_projects` enrollment/unenrollment when `project_assignments` are pulled. |
| `SyncEngineFactory` | `application/sync_engine_factory.dart` | Factory for creating `SyncEngine` instances (foreground + background). Ensures adapters registered. |
| `SyncCoordinatorBuilder` | `application/sync_coordinator_builder.dart` | Builder pattern for `SyncCoordinator`. Validates all required deps at `build()`. |
| `SyncInitializer` | `application/sync_initializer.dart` | DI/initialization for sync feature. Wires coordinator, lifecycle, enrollment, FCM, and realtime in correct order. |

## Status vs Diagnostics

### SyncStatus (Transport State)

Immutable value class (`domain/sync_status.dart`). Single source of truth replacing mutable fields scattered across 3 classes.

Fields: `isUploading`, `isDownloading`, `lastSyncedAt`, `uploadError`, `downloadError`, `isOnline`, `isAuthValid`.

Updated on every sync state change. Streamed to `SyncProvider`.

### SyncDiagnosticsSnapshot (Operational State)

Immutable snapshot (`domain/sync_diagnostics.dart`). Fetched on-demand by `SyncQueryService`.

Fields: `pendingBuckets`, `totalPendingCount`, `integrityResults`, `undismissedConflictCount`, `circuitBreakerTrips`, `lastRun`, `snapshotTime`.

### SyncEvent (Lifecycle Signals)

Sealed class hierarchy (`domain/sync_event.dart`). Transient — not persisted.

Events: `SyncRunStarted`, `SyncRunCompleted`, `RetryScheduled`, `AuthRefreshed`, `QuickSyncThrottled`, `CircuitBreakerTripped`, `FilePhaseResult`.

## Adapter Pattern

### AdapterConfig (Data-Driven)

`adapters/adapter_config.dart` defines a configuration class. `adapters/simple_adapters.dart` lists 13 configs. Each generates a `TableAdapter` via `AdapterConfig.toAdapter()` at registration time.

Properties: `table`, `scope`, `fkDeps`, `fkColumnMap`, `converters`, `supportsSoftDelete`, `isFileAdapter`, `storageBucket`, `stripExifGps`, `buildStoragePath`, `insertOnly`, `skipPull`, `skipIntegrityCheck`, `naturalKeyColumns`.

### Complex Adapters (Class Files)

9 adapters have custom logic (conversion, validation, file handling) beyond what `AdapterConfig` can express. They extend `TableAdapter` directly.

### Registration Order

Registration in `SyncRegistry` is load-bearing — it defines FK dependency order. Parents must be registered (and therefore pushed) before children. The order in `simple_adapters.dart` is for readability; `SyncRegistry` controls actual ordering.

## Testing Strategy

| Layer | Name | Purpose | Count |
|-------|------|---------|-------|
| 1 | Characterization | Behavior contracts capturing pre-refactor behavior | ~22 tests |
| 2 | Contract | TDD interface contracts for extracted classes | Per-class |
| 3 | Isolation | Per-class deep coverage with mocked dependencies | Per-class |
| 4 | Integration | Multi-component interaction verification | Cross-class |
| 5 | E2E | 10 test driver flows for full system verification | 10 flows |

Test files are organized to mirror the source structure:
- `test/features/sync/characterization/` — Layer 1
- `test/features/sync/engine/` — Layers 2-4 engine tests
- `test/features/sync/application/` — Layers 2-4 application tests
- `test/features/sync/adapters/` — Adapter-specific tests

## Key Invariants

1. `SyncEngine` has NO direct DB or Supabase access
2. All trigger suppression goes through `LocalSyncStore` → `TriggerStateStore`
3. Error classification goes through `SyncErrorClassifier` only
4. `SyncStatus` is the single transport state source of truth
5. Adapter registration order = FK dependency order (load-bearing)
6. `change_log` is trigger-only — never manually INSERT
7. `sync_control.pulling` MUST be in try/finally blocks
