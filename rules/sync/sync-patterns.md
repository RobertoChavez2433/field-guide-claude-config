---
paths:
  - "lib/features/sync/**/*.dart"
---

# Sync Architecture

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  SyncProvider (subscribes to SyncStatus, reads               │
│    SyncQueryService for diagnostics)                         │
│  Screens: SyncDashboardScreen, ConflictViewerScreen          │
│  Widgets: SyncStatusIcon, DeletionNotificationBanner         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│  SyncCoordinator        — entry point, owns retry loop       │
│  SyncLifecycleManager   — app lifecycle → sync triggers      │
│  SyncRetryPolicy        — retryability, backoff, scheduling  │
│  ConnectivityProbe      — DNS/health checks                  │
│  SyncTriggerPolicy      — lifecycle/stale/hint → sync mode   │
│  PostSyncHooks          — post-sync follow-up (profile, cfg) │
│  SyncQueryService       — dashboard queries (pending, etc.)  │
│  BackgroundSyncHandler  — background sync tasks              │
│  FcmHandler             — FCM push notification handler      │
│  RealtimeHintHandler    — Supabase Realtime → DirtyScope     │
│  SyncEnrollmentService  — project enrollment management      │
│  SyncEngineFactory      — SyncEngine instance creation       │
│  SyncCoordinatorBuilder — builder for SyncCoordinator        │
│  SyncInitializer        — DI/init wiring                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      ENGINE LAYER                            │
│  SyncEngine (slim coordinator ~214 lines):                   │
│    mutex, heartbeat, mode routing — NO direct DB/Supabase    │
│                                                              │
│  I/O Boundaries:                                             │
│    SupabaseSync      — all Supabase row I/O                  │
│    LocalSyncStore    — all sync SQLite I/O                   │
│                                                              │
│  Handlers:                                                   │
│    PushHandler       — change_log → FK-ordered → push        │
│    PullHandler       — adapter iteration → scope → paginate  │
│    FileSyncHandler   — 3-phase upload + EXIF strip           │
│    EnrollmentHandler — project enrollment from assignments   │
│    FkRescueHandler   — missing FK parent fetch               │
│    MaintenanceHandler — integrity, orphan, pruning           │
│                                                              │
│  Supporting:                                                 │
│    SyncErrorClassifier — single error classification source  │
│    ChangeTracker       — reads change_log for pending        │
│    ConflictResolver    — LWW + manual resolution             │
│    IntegrityChecker    — post-sync FK consistency            │
│    DirtyScopeTracker   — remote change hint tracking         │
│    OrphanScanner       — orphaned record detection           │
│    StorageCleanup      — post-sync file cleanup              │
│    SyncMutex           — concurrent sync prevention          │
│    SyncRegistry        — ordered adapter registry            │
│    SyncControlService  — circuit-breaker + health state      │
│    LwwChecker          — last-writer-wins pre-push check     │
│    PushErrorHandler    — push error routing/logging          │
│    PullScopeState      — pull scope tracking per-run         │
│    SyncRunLifecycle     — run start/end bookkeeping          │
│    SyncStatusStore     — status persistence                  │
│    SyncMetadataStore   — sync_metadata reads/writes          │
│    SyncedScopeStore    — synced_projects management          │
│    TriggerStateStore   — trigger suppression control         │
│    LocalRecordStore    — local record CRUD                   │
│    SyncDebugPoster     — debug server HTTP posts             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    TABLE ADAPTERS (22)                       │
│  13 data-driven AdapterConfig (simple_adapters.dart)         │
│  9 class files (complex adapters with custom logic)          │
│  table_adapter.dart (abstract base)                          │
│  adapter_config.dart (config → adapter generator)            │
│  type_converters.dart (column-level type mapping)            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                            │
│  SyncResult        — push/pull result value object           │
│  SyncStatus        — immutable transport state (single SOT)  │
│  SyncErrorKind     — classified error categories             │
│  ClassifiedSyncError — typed error with retryability         │
│  SyncDiagnosticsSnapshot — operational state for dashboards  │
│  SyncEvent         — sealed class lifecycle events           │
│  SyncMode          — full/quick/maintenance                  │
│  DirtyScope        — project+table scope marker              │
│  SyncAdapterStatus — idle/syncing/success/error/offline      │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Push Flow

```
Local Write (any syncable table)
    │
    ▼  [SQLite trigger fires]
change_log row inserted (table, record_id, operation, processed=0)
    │
    ▼  [next sync cycle]
ChangeTracker.getPendingChanges() → groups by table
    │
    ▼
PushHandler (FK-ordered via SyncRegistry)
    │
    ├─► adapter.convertForRemote(localRecord)
    ├─► LwwChecker: fetch server updated_at, skip if stale
    ├─► SupabaseSync.upsertRecord / deleteRecord / insertOnlyRecord
    ├─► PushErrorHandler: classify via SyncErrorClassifier, route error
    └─► ChangeTracker: mark change_log entries processed=1
```

### Pull Flow

```
SyncEngine routes mode → PullHandler
    │
    ▼
PullHandler (adapter iteration via SyncRegistry)
    │
    ├─► PullScopeState: determine which scopes to pull
    ├─► For each adapter (FK-ordered):
    │   ├─► LocalSyncStore: suppress triggers (pulling='1')
    │   ├─► SupabaseSync: paginated SELECT since last cursor
    │   ├─► adapter.convertForLocal(remoteRecord)
    │   ├─► ConflictResolver.resolve() for update conflicts
    │   ├─► LocalSyncStore: upsert local records
    │   ├─► FkRescueHandler: fetch missing FK parents
    │   └─► LocalSyncStore: restore triggers (pulling='0')
    ├─► EnrollmentHandler: check project_assignments for new enrollments
    └─► Update sync cursors in sync_metadata
```

### Sync Request Flow

```
User Action / Lifecycle / Hint / FCM
    │
    ▼
SyncTriggerPolicy → decides SyncMode (full/quick/maintenance)
    │
    ▼
SyncCoordinator.sync()
    │
    ├─► ConnectivityProbe.checkOnline()
    ├─► SyncRetryPolicy: decide if retry is appropriate
    ├─► SyncEngine.run(mode)
    │   ├─► SyncMutex.acquire()
    │   ├─► Push (if not maintenance-only)
    │   ├─► Pull
    │   ├─► MaintenanceHandler (if full/maintenance mode)
    │   └─► SyncMutex.release()
    ├─► PostSyncHooks.run() (profile refresh, config update)
    └─► SyncRetryPolicy: schedule retry on transient failure
```

### Multi-Backend Flow

```
SyncCoordinator.sync()
    │
    ├─► if real mode (Local Agency)
    │   └─► SyncEngine → SupabaseSync → Supabase Backend
    │
    └─► if TestModeConfig.useMockData
        └─► MockSyncAdapter (no network)
```

## Status vs Diagnostics Split

| Concept | Class | Purpose | Update Frequency |
|---------|-------|---------|-----------------|
| Transport state | `SyncStatus` | isUploading/isDownloading, lastSyncedAt, errors, isOnline | Every sync state change |
| Operational state | `SyncDiagnosticsSnapshot` | pending buckets, integrity, conflicts, circuit-breaker | On-demand (dashboard refresh) |
| Lifecycle signals | `SyncEvent` | sealed class events: run started/completed, retry, auth refresh, CB trip | Transient (not persisted) |

**SyncStatus** is the single source of truth for transport state. It replaces the mutable `_isSyncing`, `_status`, `_lastSyncTime`, and `_isOnline` fields that were scattered across SyncEngine, SyncOrchestrator, and SyncProvider.

**SyncDiagnosticsSnapshot** is fetched by `SyncQueryService` and consumed by dashboard screens. It does NOT stream — it's a point-in-time snapshot.

**SyncEvent** is a sealed class with exhaustive pattern matching. Used for debug server posts, test assertions, and diagnostic logging.

## Error Classification

`SyncErrorClassifier` is the **single source of truth** for error classification. It replaces the triplicated classification in the old SyncEngine._handlePushError, SyncOrchestrator._isTransientError, and SyncProvider._sanitizeSyncError.

| SyncErrorKind | Postgres/Network Pattern | Retryable |
|---------------|-------------------------|-----------|
| `rlsDenial` | 42501 | No (permanent) |
| `fkViolation` | 23503 | No (permanent) |
| `uniqueViolation` | 23505 | Yes (up to 2, TOCTOU race) |
| `rateLimited` | 429, 503 | Yes (with backoff) |
| `authExpired` | 401, PGRST301, JWT | Yes (after token refresh) |
| `networkError` | SocketException, Timeout, DNS | Yes (with backoff) |
| `transient` | Other retryable | Yes |
| `permanent` | Other non-retryable | No |

## Adapters

### Base Class

`lib/features/sync/adapters/table_adapter.dart` — abstract class. PushHandler calls `convertForRemote()` before push; PullHandler calls `convertForLocal()` after pull. Adapters are pure configuration + conversion objects; handlers do all I/O.

Key properties:
- `tableName` — must match SQLite/Supabase table name exactly
- `scopeType` — how this table is tenant-scoped (`ScopeType`)
- `fkDependencies` — tables that must be pushed first (FK parents)
- `converters` — column-level `TypeConverter` instances
- `localOnlyColumns` / `remoteOnlyColumns` — stripped during conversion
- `insertOnly` — true for append-only tables (e.g., consent_records)
- `isFileAdapter` — true for photo/document/export adapters (3-phase upload)
- `naturalKeyColumns` — for UNIQUE constraint pre-check (prevents 23505 errors)

### Data-Driven Simple Adapters (13)

Defined in `lib/features/sync/adapters/simple_adapters.dart` as `AdapterConfig` instances. Each generates a `TableAdapter` via `AdapterConfig.toAdapter()` at registration.

| Table | Scope | FK Dependencies |
|-------|-------|----------------|
| `projects` | direct | — |
| `project_assignments` | direct | projects |
| `locations` | viaProject | projects |
| `contractors` | viaProject | projects |
| `bid_items` | viaProject | projects |
| `personnel_types` | viaProject | projects |
| `daily_entries` | viaProject | projects, locations |
| `entry_contractors` | viaEntry | daily_entries, contractors |
| `entry_personnel_counts` | viaEntry | daily_entries, personnel_types |
| `entry_quantities` | viaEntry | daily_entries, bid_items |
| `todo_items` | viaProject | projects |
| `calculation_history` | direct | — |
| `entry_exports` | viaEntry | daily_entries (file adapter) |

### Complex Class Adapters (9)

These have custom logic beyond property overrides and remain as class files:

| File | Table | Why Complex |
|------|-------|-------------|
| `consent_record_adapter.dart` | user_consent_records | insertOnly + custom validation |
| `daily_entry_adapter.dart` | daily_entries | Custom convertForRemote/Local with weather/GPS |
| `document_adapter.dart` | documents | File adapter with storage path logic |
| `entry_equipment_adapter.dart` | entry_equipment | Junction table with quantity fields |
| `equipment_adapter.dart` | equipment | Contractor FK + type converters |
| `form_response_adapter.dart` | form_responses | JSON field handling |
| `inspector_form_adapter.dart` | inspector_forms | is_builtin guard + template logic |
| `photo_adapter.dart` | photos | File adapter with EXIF stripping |
| `support_ticket_adapter.dart` | support_tickets | insertOnly + attachment handling |

### Registration Order

Registration order in `SyncRegistry` is load-bearing — it defines FK dependency order for push. Parents must be pushed before children.

## Engine Components

| Class | File | Purpose |
|-------|------|---------|
| `SyncEngine` | `engine/sync_engine.dart` | Slim coordinator (~214 lines): mutex, heartbeat, mode routing |
| `PushHandler` | `engine/push_handler.dart` | Change_log → FK-ordered → route per record → SupabaseSync |
| `PullHandler` | `engine/pull_handler.dart` | Adapter iteration → scope filter → paginate → LocalSyncStore |
| `SupabaseSync` | `engine/supabase_sync.dart` | All Supabase row I/O (upsert, delete, select, auth refresh) |
| `LocalSyncStore` | `engine/local_sync_store.dart` | All sync SQLite I/O (records, cursors, triggers, column cache) |
| `FileSyncHandler` | `engine/file_sync_handler.dart` | 3-phase file upload + EXIF GPS strip |
| `SyncErrorClassifier` | `engine/sync_error_classifier.dart` | Single error classification source |
| `EnrollmentHandler` | `engine/enrollment_handler.dart` | Project enrollment from assignments |
| `FkRescueHandler` | `engine/fk_rescue_handler.dart` | Missing FK parent fetch |
| `MaintenanceHandler` | `engine/maintenance_handler.dart` | Integrity, orphan scan, pruning |
| `ChangeTracker` | `engine/change_tracker.dart` | Reads change_log; groups pending by table |
| `ConflictResolver` | `engine/conflict_resolver.dart` | Last-writer-wins + manual resolution |
| `IntegrityChecker` | `engine/integrity_checker.dart` | Post-sync FK consistency validation |
| `DirtyScopeTracker` | `engine/dirty_scope_tracker.dart` | Remote change hint tracking (project+table granular) |
| `OrphanScanner` | `engine/orphan_scanner.dart` | Detects local records with no valid FK parent |
| `StorageCleanup` | `engine/storage_cleanup.dart` | Deletes local files after successful remote upload |
| `SyncMutex` | `engine/sync_mutex.dart` | Prevents concurrent sync runs |
| `SyncRegistry` | `engine/sync_registry.dart` | Ordered list of all active TableAdapter instances |
| `SyncControlService` | `engine/sync_control_service.dart` | Circuit-breaker state + health metrics for UI |
| `LwwChecker` | `engine/lww_checker.dart` | Last-writer-wins pre-push timestamp check |
| `PushErrorHandler` | `engine/push_error_handler.dart` | Push error routing and logging |
| `PullScopeState` | `engine/pull_scope_state.dart` | Per-run pull scope tracking |
| `SyncRunLifecycle` | `engine/sync_run_lifecycle.dart` | Run start/end bookkeeping |
| `SyncStatusStore` | `engine/sync_status_store.dart` | Status persistence |
| `SyncMetadataStore` | `engine/sync_metadata_store.dart` | sync_metadata table reads/writes |
| `SyncedScopeStore` | `engine/synced_scope_store.dart` | synced_projects management |
| `TriggerStateStore` | `engine/trigger_state_store.dart` | Trigger suppression control |
| `LocalRecordStore` | `engine/local_record_store.dart` | Local record CRUD operations |
| `SyncDebugPoster` | `engine/sync_debug_poster.dart` | Debug server HTTP posts |
| `ScopeType` | `engine/scope_type.dart` | Enum: direct, viaProject, viaEntry, viaContractor |
| `SyncEngineResult` | `engine/sync_engine_result.dart` | Engine-level result wrapper |

## Application Layer

| Class | File | Purpose |
|-------|------|---------|
| `SyncCoordinator` | `application/sync_coordinator.dart` | Entry point for sync requests, owns retry loop (replaces SyncOrchestrator) |
| `SyncLifecycleManager` | `application/sync_lifecycle_manager.dart` | App lifecycle → sync triggers |
| `SyncRetryPolicy` | `application/sync_retry_policy.dart` | Retryability, backoff, background scheduling |
| `ConnectivityProbe` | `application/connectivity_probe.dart` | DNS/health checks |
| `SyncTriggerPolicy` | `application/sync_trigger_policy.dart` | Lifecycle/stale/hint → sync mode decision |
| `PostSyncHooks` | `application/post_sync_hooks.dart` | Post-sync app-level follow-up (profile refresh, config) |
| `SyncQueryService` | `application/sync_query_service.dart` | Dashboard queries (pending buckets, integrity, conflicts) |
| `BackgroundSyncHandler` | `application/background_sync_handler.dart` | Schedules and runs background sync tasks |
| `FcmHandler` | `application/fcm_handler.dart` | Processes FCM push notifications for sync signals |
| `RealtimeHintHandler` | `application/realtime_hint_handler.dart` | Supabase Realtime → DirtyScopeTracker → quick sync |
| `SyncEnrollmentService` | `application/sync_enrollment_service.dart` | synced_projects enrollment/unenrollment management |
| `SyncEngineFactory` | `application/sync_engine_factory.dart` | Factory for SyncEngine instances (foreground + background) |
| `SyncCoordinatorBuilder` | `application/sync_coordinator_builder.dart` | Builder pattern for SyncCoordinator with validation |
| `SyncInitializer` | `application/sync_initializer.dart` | DI/init wiring for sync subsystem |

## SyncMode Enum

Defined in `lib/features/sync/domain/sync_types.dart`:

| Mode | Behavior |
|------|----------|
| `quick` | Push local changes + pull only dirty scopes (triggered by realtime hints) |
| `full` | Push + pull all tables + maintenance (integrity check, orphan purge) |
| `maintenance` | Pull + housekeeping (integrity check, orphan cleanup, pruning) |

## SyncConfig Values

Defined in `lib/features/sync/config/sync_config.dart` (`SyncEngineConfig`):

| Constant | Value | Purpose |
|----------|-------|---------|
| `pushBatchLimit` | 500 | Max records per push batch |
| `pushAnomalyThreshold` | 1000 | Anomaly detection threshold for push count |
| `maxRetryCount` | 5 | Max push retry attempts |
| `pullPageSize` | 100 | Records per pull page |
| `pullSafetyMargin` | 5s | Safety margin for pull cursors |
| `circuitBreakerThreshold` | 1000 | Error count before circuit breaker trips |
| `conflictPingPongThreshold` | 3 | Max consecutive local-wins before stopping |
| `integrityCheckInterval` | 4h | Min interval between integrity checks |
| `staleLockTimeout` | 15min | Sync mutex lock expiry |
| `changeLogRetention` | 7d | Processed change_log entry retention |
| `conflictLogRetention` | 7d | Conflict log entry retention |
| `dirtyScopeMaxAge` | 2h | Dirty scope expiry in DirtyScopeTracker |
| `orphanMinAge` | 24h | Min age before orphan records are purged |
| `orphanMaxPerCycle` | 50 | Max orphans purged per maintenance cycle |
| `retryBaseDelay` | 1s | Base delay for exponential backoff |
| `retryMaxDelay` | 16s | Max delay for exponential backoff |

## Change Tracking

SQLite triggers automatically populate the `change_log` table on every INSERT, UPDATE, and DELETE to syncable tables. `ChangeTracker` reads unprocessed entries to determine what needs pushing. There is no `sync_queue` table.

```
Local Write (any syncable table)
    │
    ▼  [SQLite trigger fires]
change_log row inserted (table, record_id, operation, processed=0)
    │
    ▼  [next sync cycle]
ChangeTracker.getPendingChanges() → groups by table
    │
    ▼
PushHandler pushes records, marks entries processed=1
```

## Trigger Suppression (`sync_control.pulling`)

**CRITICAL**: All change_log triggers have a WHEN clause:
```sql
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
```

- Set to `'1'` during pull operations to prevent pull-writes from generating push entries (avoids echo loops)
- MUST be set inside a try/finally block — always reset to `'0'` in the finally
- Reset to `'0'` on every app startup in `DatabaseService.onOpen` to recover from crash-during-pull
- All trigger suppression is owned by `LocalSyncStore` via `TriggerStateStore`

### is_builtin trigger guard

`inspector_forms` triggers have an additional WHEN clause: `AND NEW.is_builtin != 1`. This skips server-seeded reference data so they never generate change_log entries.

## File Organization

```
lib/features/sync/
├── sync.dart                              # Feature barrel export
│
├── adapters/                              # 22 table adapters
│   ├── table_adapter.dart                 # Abstract base class
│   ├── adapter_config.dart                # Data-driven config → adapter generator
│   ├── simple_adapters.dart               # 13 AdapterConfig instances
│   ├── type_converters.dart               # Column-level type conversion
│   ├── consent_record_adapter.dart        # Complex: insertOnly + validation
│   ├── daily_entry_adapter.dart           # Complex: weather/GPS conversion
│   ├── document_adapter.dart              # Complex: file adapter
│   ├── entry_equipment_adapter.dart       # Complex: junction + quantities
│   ├── equipment_adapter.dart             # Complex: contractor FK + converters
│   ├── form_response_adapter.dart         # Complex: JSON fields
│   ├── inspector_form_adapter.dart        # Complex: is_builtin guard
│   ├── photo_adapter.dart                 # Complex: file + EXIF
│   └── support_ticket_adapter.dart        # Complex: insertOnly + attachments
│
├── engine/                                # Core sync engine
│   ├── sync_engine.dart                   # Slim coordinator (~214 lines)
│   ├── supabase_sync.dart                 # Supabase row I/O boundary
│   ├── local_sync_store.dart              # SQLite I/O boundary
│   ├── push_handler.dart                  # Push orchestration
│   ├── pull_handler.dart                  # Pull orchestration
│   ├── file_sync_handler.dart             # 3-phase file upload
│   ├── sync_error_classifier.dart         # Single error classification
│   ├── enrollment_handler.dart            # Project enrollment
│   ├── fk_rescue_handler.dart             # Missing FK parent fetch
│   ├── maintenance_handler.dart           # Integrity + orphan + pruning
│   ├── change_tracker.dart                # change_log reader
│   ├── conflict_resolver.dart             # LWW conflict resolution
│   ├── integrity_checker.dart             # Post-sync FK validation
│   ├── dirty_scope_tracker.dart           # Remote change hints
│   ├── orphan_scanner.dart                # Orphan detection
│   ├── storage_cleanup.dart               # Post-sync file cleanup
│   ├── sync_mutex.dart                    # Concurrency control
│   ├── sync_registry.dart                 # Ordered adapter registry
│   ├── sync_control_service.dart          # Circuit-breaker + health
│   ├── lww_checker.dart                   # LWW pre-push check
│   ├── push_error_handler.dart            # Push error routing
│   ├── pull_scope_state.dart              # Per-run scope tracking
│   ├── sync_run_lifecycle.dart            # Run start/end bookkeeping
│   ├── sync_status_store.dart             # Status persistence
│   ├── sync_metadata_store.dart           # sync_metadata reads/writes
│   ├── synced_scope_store.dart            # synced_projects management
│   ├── trigger_state_store.dart           # Trigger suppression control
│   ├── local_record_store.dart            # Local record CRUD
│   ├── sync_debug_poster.dart             # Debug server HTTP posts
│   ├── scope_type.dart                    # Scope enum
│   └── sync_engine_result.dart            # Engine result wrapper
│
├── domain/                                # Value types
│   ├── domain.dart                        # Barrel export
│   ├── sync_types.dart                    # SyncResult, SyncAdapterStatus, SyncMode, DirtyScope
│   ├── sync_status.dart                   # SyncStatus immutable value class
│   ├── sync_error.dart                    # SyncErrorKind + ClassifiedSyncError
│   ├── sync_diagnostics.dart              # SyncDiagnosticsSnapshot
│   └── sync_event.dart                    # Sealed SyncEvent hierarchy
│
├── data/                                  # External data sources
│   ├── data.dart                          # Barrel export
│   ├── adapters/
│   │   ├── adapters.dart                  # Barrel export
│   │   └── mock_sync_adapter.dart         # Testing mock (no-network)
│   ├── datasources/
│   │   └── local/
│   │       ├── conflict_local_datasource.dart
│   │       └── deletion_notification_local_datasource.dart
│   └── repositories/
│       ├── conflict_repository.dart
│       └── deletion_notification_repository.dart
│
├── application/                           # Orchestration + control plane
│   ├── application.dart                   # Barrel export
│   ├── sync_coordinator.dart              # Entry point (replaces SyncOrchestrator)
│   ├── sync_coordinator_builder.dart      # Builder with validation
│   ├── sync_lifecycle_manager.dart        # App lifecycle triggers
│   ├── sync_retry_policy.dart             # Retry policy
│   ├── connectivity_probe.dart            # Online checks
│   ├── sync_trigger_policy.dart           # Trigger → mode decisions
│   ├── post_sync_hooks.dart               # Post-sync hooks
│   ├── sync_query_service.dart            # Dashboard queries
│   ├── background_sync_handler.dart       # Background sync
│   ├── background_sync_callback.dart      # Background callback
│   ├── fcm_handler.dart                   # FCM handler
│   ├── fcm_background_callback.dart       # FCM background callback
│   ├── realtime_hint_handler.dart         # Realtime hint subscriber
│   ├── sync_enrollment_service.dart       # Enrollment management
│   ├── sync_engine_factory.dart           # SyncEngine factory
│   └── sync_initializer.dart              # Sync subsystem init
│
├── config/
│   └── sync_config.dart                   # SyncEngineConfig thresholds
│
├── di/
│   ├── di.dart                            # Barrel export
│   └── sync_providers.dart                # DI wiring
│
└── presentation/                          # UI layer
    ├── presentation.dart                  # Barrel export
    ├── providers/
    │   ├── providers.dart                 # Barrel export
    │   └── sync_provider.dart             # ChangeNotifier for UI
    ├── screens/
    │   ├── sync_dashboard_screen.dart
    │   └── conflict_viewer_screen.dart
    └── widgets/
        ├── sync_status_icon.dart
        └── deletion_notification_banner.dart
```

## Enforced Invariants (Lint Rules)

- **sync_control flag MUST be inside transaction** (S3) -- set pulling='1' inside try/finally
- **change_log cleanup MUST be conditional on RPC success** (S2) -- never unconditional DELETE
- **ConflictAlgorithm.ignore MUST have rowId==0 fallback** (S1) -- check return value, UPDATE on 0
- **No sync_status column** (S4) -- deprecated pattern, only change_log is used
- **toMap() MUST include project_id for synced child models** (S5)
- **_lastSyncTime only updated in success path** (S8)

## Sync Testing

Sync correctness is verified via a multi-layer system:

- **Characterization tests** (Layer 1) — behavior contracts capturing pre-refactor behavior
- **Contract tests** (Layer 2) — TDD interface contracts for extracted classes
- **Isolation tests** (Layer 3) — per-class deep coverage with mocked dependencies
- **Integration tests** (Layer 4) — multi-component interaction verification
- **E2E flows** (Layer 5) — 10 test driver flows for full system verification

**IMPORTANT**: Always use the app UI to create/modify test data for sync testing. Never use raw SQL, Supabase REST writes, or direct `change_log` inserts (except the one documented exception in `ChangeTracker.manualInsert()`). Bypassing the UI skips the SQLite trigger that populates `change_log`, so changes will never sync.
