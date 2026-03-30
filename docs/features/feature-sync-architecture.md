---
feature: sync
type: architecture
scope: Cloud Synchronization & Multi-Backend Support
updated: 2026-03-30
---

# Sync Feature Architecture

## Layer Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  SyncProvider (ChangeNotifier)                               │
│  Screens: SyncDashboardScreen, ConflictViewerScreen          │
│  Widgets: SyncStatusIcon, DeletionNotificationBanner         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│  SyncOrchestrator — multi-backend router                     │
│  SyncLifecycleManager — app lifecycle triggers               │
│  BackgroundSyncHandler — WorkManager background tasks        │
│  FcmHandler — FCM push notification handler                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      ENGINE LAYER                            │
│  SyncEngine — core push/pull orchestration                   │
│  ChangeTracker, ConflictResolver, IntegrityChecker           │
│  SyncMutex, SyncRegistry, OrphanScanner, StorageCleanup      │
│  ScopeType, SyncControlService                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 TABLE ADAPTERS (22 concrete)                 │
│  TableAdapter (abstract base)                                │
│  One adapter per syncable table                              │
│  TypeConverters (shared column-level utility)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                            │
│  SyncResult, SyncAdapterStatus (sync_types.dart)             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│  SyncEngine handles all Supabase I/O directly                │
│  MockSyncAdapter — test environments (no-network mock)       │
│  ConflictRepository + DeletionNotificationRepository         │
└─────────────────────────────────────────────────────────────┘
```

## Engine Layer

**Location**: `lib/features/sync/engine/`

| Class | File | Purpose |
|-------|------|---------|
| `SyncEngine` | `sync_engine.dart` | Core orchestration: push/pull loop, conflict dispatch, circuit breaker |
| `ChangeTracker` | `change_tracker.dart` | Reads `change_log` table; groups pending changes by table |
| `ConflictResolver` | `conflict_resolver.dart` | Last-writer-wins + manual resolution support |
| `IntegrityChecker` | `integrity_checker.dart` | Post-sync FK consistency validation |
| `SyncMutex` | `sync_mutex.dart` | Prevents concurrent sync runs |
| `SyncRegistry` | `sync_registry.dart` | Ordered list of all active `TableAdapter` instances |
| `OrphanScanner` | `orphan_scanner.dart` | Detects local records with no valid FK parent |
| `StorageCleanup` | `storage_cleanup.dart` | Deletes local files after successful remote upload |
| `ScopeType` | `scope_type.dart` | Enum: `direct`, `viaProject`, `viaEntry`, `viaContractor` |
| `SyncControlService` | `sync_control_service.dart` | Suppresses `change_log` triggers during pull/draft-save operations |

`SyncEngineResult` is the internal result type returned by `SyncEngine.pushAndPull()`. It is mapped to `SyncResult` by `SyncOrchestrator` before propagating to the UI.

## Application Layer

**Location**: `lib/features/sync/application/`

| Class | File | Purpose |
|-------|------|---------|
| `SyncOrchestrator` | `sync_orchestrator.dart` | Routes sync to `SyncEngine` (real) or `MockSyncAdapter` (test). Handles retry with exponential backoff, auth context polling, background retry timer, and post-sync profile pulls. |
| `SyncLifecycleManager` | `sync_lifecycle_manager.dart` | `WidgetsBindingObserver`. Triggers debounced sync on `paused`/`detached`; checks staleness on `resumed`. |
| `BackgroundSyncHandler` | `background_sync_handler.dart` | WorkManager task runner. Runs in a fresh Dart isolate on Android/iOS. |
| `FcmHandler` | `fcm_handler.dart` | Initializes Firebase Messaging, stores FCM tokens, and dispatches foreground `daily_sync` messages to `SyncOrchestrator`. Rate-limited to 60s between triggers. |

`BucketCount` is a value class defined alongside `SyncOrchestrator`. It holds `total` and a per-table `breakdown` map for grouped pending-count display on the dashboard.

## Table Adapters

**Location**: `lib/features/sync/adapters/`

All adapters extend `TableAdapter` (abstract base class). They are pure configuration + conversion objects; `SyncEngine` handles all Supabase I/O.

Key `TableAdapter` properties:
- `tableName` — must match SQLite/Supabase table name exactly
- `scopeType` — tenant scoping strategy (`ScopeType`)
- `fkDependencies` — tables that must be pushed first
- `converters` — column-level `TypeConverter` instances
- `localOnlyColumns` / `remoteOnlyColumns` — stripped during conversion
- `insertOnly` — true for append-only tables (e.g., `consent_records`)
- `isFileAdapter` — true for photo/document/export adapters (3-phase storage push)
- `naturalKeyColumns` — used for UNIQUE constraint pre-check before upsert

### Concrete Adapters (22)

| Adapter | Table |
|---------|-------|
| `ProjectAdapter` | `projects` |
| `LocationAdapter` | `locations` |
| `ContractorAdapter` | `contractors` |
| `EquipmentAdapter` | `equipment` |
| `PersonnelTypeAdapter` | `personnel_types` |
| `BidItemAdapter` | `bid_items` |
| `DailyEntryAdapter` | `daily_entries` |
| `EntryContractorsAdapter` | `entry_contractors` |
| `EntryEquipmentAdapter` | `entry_equipment` |
| `EntryPersonnelCountsAdapter` | `entry_personnel_counts` |
| `EntryQuantitiesAdapter` | `entry_quantities` |
| `PhotoAdapter` | `photos` |
| `InspectorFormAdapter` | `inspector_forms` |
| `FormResponseAdapter` | `form_responses` |
| `FormExportAdapter` | `form_exports` |
| `EntryExportAdapter` | `entry_exports` |
| `DocumentAdapter` | `documents` |
| `TodoItemAdapter` | `todo_items` |
| `ProjectAssignmentAdapter` | `project_assignments` |
| `CalculationHistoryAdapter` | `calculation_history` |
| `ConsentRecordAdapter` | `user_consent_records` |
| `SupportTicketAdapter` | `support_tickets` |

`TypeConverters` (`type_converters.dart`) is a shared utility, not a table adapter.

## Config

**Location**: `lib/features/sync/config/sync_config.dart`

Thresholds, retry limits, batch sizes, and feature flags for the sync engine.

## Domain

**Location**: `lib/features/sync/domain/sync_types.dart`

- `SyncResult` — immutable value object: `pushed`, `pulled`, `errors`, `errorMessages`, `rlsDenials`, `skippedPush`. Supports `+` operator for combining results.
- `SyncAdapterStatus` — enum: `idle`, `syncing`, `success`, `error`, `offline`, `authRequired`

## Data Layer

**Location**: `lib/features/sync/data/`

| Class | File | Purpose |
|-------|------|---------|
| `MockSyncAdapter` | `data/adapters/mock_sync_adapter.dart` | No-network mock for test mode (`TestModeConfig.useMockData=true`) |
| `ConflictRepository` | `data/repositories/conflict_repository.dart` | Thin wrapper around `ConflictLocalDatasource` |
| `DeletionNotificationRepository` | `data/repositories/deletion_notification_repository.dart` | Thin wrapper around `DeletionNotificationLocalDatasource` |
| `ConflictLocalDatasource` | `data/datasources/local/conflict_local_datasource.dart` | SQLite reads from `conflict_log` |
| `DeletionNotificationLocalDatasource` | `data/datasources/local/deletion_notification_local_datasource.dart` | SQLite reads from deletion notification table |

## Presentation Layer

**Location**: `lib/features/sync/presentation/`

### SyncProvider

`lib/features/sync/presentation/providers/sync_provider.dart` — `ChangeNotifier`.

Key state:
- `status: SyncAdapterStatus`
- `pendingCount: int`
- `pendingBuckets: Map<String, BucketCount>`
- `lastSyncTime: DateTime?`
- `lastError: String?`
- `isSyncing: bool`
- `isStaleDataWarning: bool`
- `isForcedSyncInProgress: bool`
- `circuitBreakerTripped: bool` + `circuitBreakerTrips` list
- `pendingNotifications: List<String>` — queued assignment messages

Key methods:
- `syncAll()` — trigger full sync via `SyncOrchestrator`
- `refreshStatus()` — refresh pending counts
- `setStaleDataWarning(bool)` — wired from `SyncLifecycleManager`
- `setForcedSyncInProgress(bool)` — wired from `SyncLifecycleManager`
- `addNotification(String)` — called by auto-enrollment on assignment pull

### Screens

| Screen | File |
|--------|------|
| `SyncDashboardScreen` | `screens/sync_dashboard_screen.dart` |
| `ConflictViewerScreen` | `screens/conflict_viewer_screen.dart` |

### Widgets

| Widget | File |
|--------|------|
| `SyncStatusIcon` | `widgets/sync_status_icon.dart` |
| `DeletionNotificationBanner` | `widgets/deletion_notification_banner.dart` |

## DI Wiring

**Location**: `lib/features/sync/di/sync_providers.dart` — `SyncProviders` class.

`SyncProviders.initialize()` runs before `runApp()`:
1. Creates `SyncOrchestrator` and calls `initialize()`
2. Injects `UserProfileSyncDatasource` for post-sync member pulls
3. Creates `SyncLifecycleManager` and wires auth-readiness check
4. Wires `AuthProvider` listener to update company/user context on auth changes
5. Wires `onPullComplete` for auto-enrollment on `project_assignments` pull
6. Initializes `FcmHandler` on mobile (fire-and-forget)
7. Wires `AppConfigProvider` for stale-banner clearance on sync success

`SyncProviders.providers()` returns the `MultiProvider` list:
- `Provider<SyncRegistry>` (singleton, value)
- `Provider<SyncOrchestrator>` (value)
- `Provider<DeletionNotificationRepository>`
- `Provider<ConflictRepository>`
- `ChangeNotifierProvider<SyncProvider>` (wires lifecycle callbacks and health provider update)

## Sync Operation Flow

```
User triggers sync (Settings screen, Dashboard, or auto-reconnect)
    ↓
SyncProvider.syncAll()
    ↓
SyncOrchestrator.syncLocalAgencyProjects()
    ↓
  [DNS reachability check]  ← HTTP HEAD to Supabase health endpoint
    ↓
SyncEngine.pushAndPull()
    ↓
SyncMutex.acquire()                         # Prevents concurrent syncs
    ↓
ChangeTracker.getPendingChanges()           # Reads change_log (processed=0)
    ↓
For each TableAdapter (ordered by SyncRegistry):
    ├─→ adapter.convertForRemote(localRecord)
    ├─→ push local changes to Supabase
    ├─→ pull remote changes
    ├─→ adapter.convertForLocal(remoteRecord)
    └─→ ConflictResolver.resolve(conflicts)
    ↓
IntegrityChecker.validate()                 # Post-sync FK consistency
    ↓
SyncMutex.release()
    ↓
SyncEngineResult → mapped to SyncResult
    ↓
onSyncComplete callback fires
    ↓
SyncProvider.notifyListeners() → UI rebuilds
```

## Change Tracking Pattern

SQLite triggers automatically insert into `change_log` on every INSERT, UPDATE, and DELETE to tracked tables. `ChangeTracker` reads unprocessed entries (`processed=0`) to determine what to push. There is no `sync_queue` table.

```
Local Write (any tracked table)
    ↓  [SQLite trigger fires]
change_log row inserted (table, record_id, operation, processed=0)
    ↓  [next sync cycle]
ChangeTracker.getPendingChanges() → grouped by table
    ↓
SyncEngine pushes records, marks entries processed=1
```

`SyncControlService.runSuppressed()` temporarily sets `sync_control.pulling = '1'`, which causes triggers to skip `change_log` inserts. Used during pull writes and draft saves to prevent false dirty-records.

## Offline Behavior

- **Push (offline)**: Changes stay in `change_log` with `processed=0`. On reconnect, next sync cycle pushes them.
- **Pull (offline)**: Skipped. Local data unchanged.
- **Staleness**: `SyncLifecycleManager` tracks `lastSyncTime`. On resume after >24h, forces a sync. If DNS unreachable, emits `isStaleDataWarning` to `SyncProvider`.
- **Retry**: `SyncOrchestrator` retries up to 3 times with exponential backoff (5s, 10s, 20s). On exhaustion, schedules a 60s background retry via `Timer`. Non-transient errors (RLS, auth, schema) skip retry.

## Circuit Breaker

If a record repeatedly fails to push, `SyncEngine` trips the circuit breaker for that `(tableName, recordId)` pair. `SyncOrchestrator.onCircuitBreakerTrip` forwards the event to `SyncProvider`, which sets `circuitBreakerTripped = true` and appends to `circuitBreakerTrips`. The UI shows a banner; user dismisses to resume.

## Multi-Backend Routing

```
SyncOrchestrator
    ├─► TestModeConfig.useMockData = true → MockSyncAdapter (no network)
    └─► TestModeConfig.useMockData = false → SyncEngine (Supabase I/O)
        └─► Future: AASHTOWareSyncAdapter (ProjectMode.mdot)
```

## Relationships

**Depends on**:
- Every syncable feature's repositories (projects, entries, contractors, equipment, photos, forms, todos, etc.)
- `AuthProvider` / `AuthService` for auth context and FCM token storage
- `DatabaseService` (SQLite, change_log, sync_metadata, sync_control tables)
- `ProjectLifecycleService` for post-sync health counts
- `AppConfigProvider` for stale-banner clearance

**Required by**:
- Settings feature — sync section (trigger, status, pending count)
- Projects feature — `ProjectSyncHealthProvider` (unsynced counts per project)
- Dashboard feature — `SyncStatusIcon` widget

## File Locations

```
lib/features/sync/
├── sync.dart                                   # Feature entry point / barrel
│
├── adapters/                                   # 22 table adapters + base
│   ├── table_adapter.dart
│   ├── type_converters.dart
│   ├── project_adapter.dart
│   ├── location_adapter.dart
│   ├── contractor_adapter.dart
│   ├── equipment_adapter.dart
│   ├── personnel_type_adapter.dart
│   ├── bid_item_adapter.dart
│   ├── daily_entry_adapter.dart
│   ├── entry_contractors_adapter.dart
│   ├── entry_equipment_adapter.dart
│   ├── entry_personnel_counts_adapter.dart
│   ├── entry_quantities_adapter.dart
│   ├── photo_adapter.dart
│   ├── inspector_form_adapter.dart
│   ├── form_response_adapter.dart
│   ├── form_export_adapter.dart
│   ├── entry_export_adapter.dart
│   ├── document_adapter.dart
│   ├── todo_item_adapter.dart
│   ├── project_assignment_adapter.dart
│   ├── calculation_history_adapter.dart
│   ├── consent_record_adapter.dart
│   └── support_ticket_adapter.dart
│
├── engine/
│   ├── sync_engine.dart
│   ├── change_tracker.dart
│   ├── conflict_resolver.dart
│   ├── integrity_checker.dart
│   ├── sync_mutex.dart
│   ├── sync_registry.dart
│   ├── orphan_scanner.dart
│   ├── scope_type.dart
│   ├── storage_cleanup.dart
│   └── sync_control_service.dart
│
├── domain/
│   ├── domain.dart
│   └── sync_types.dart                         # SyncResult, SyncAdapterStatus
│
├── data/
│   ├── data.dart
│   ├── adapters/
│   │   ├── adapters.dart
│   │   └── mock_sync_adapter.dart
│   ├── repositories/
│   │   ├── conflict_repository.dart
│   │   └── deletion_notification_repository.dart
│   └── datasources/
│       └── local/
│           ├── conflict_local_datasource.dart
│           └── deletion_notification_local_datasource.dart
│
├── application/
│   ├── application.dart
│   ├── sync_orchestrator.dart
│   ├── sync_lifecycle_manager.dart
│   ├── background_sync_handler.dart
│   └── fcm_handler.dart
│
├── config/
│   └── sync_config.dart
│
├── di/
│   └── sync_providers.dart
│
└── presentation/
    ├── presentation.dart
    ├── providers/
    │   ├── providers.dart
    │   └── sync_provider.dart
    ├── screens/
    │   ├── sync_dashboard_screen.dart
    │   └── conflict_viewer_screen.dart
    └── widgets/
        ├── sync_status_icon.dart
        └── deletion_notification_banner.dart
```

## Import Patterns

```dart
// Within sync feature
import 'package:construction_inspector/features/sync/engine/sync_engine.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';

// From other features
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

// Via barrel
import 'package:construction_inspector/features/sync/sync.dart';
```

## Testing Notes

- Unit tests: `test/features/sync/engine/`
- Layer 2 (per-table push/pull): `node tools/debug-server/run-tests.js --layer L2`
- Layer 3 (cross-cutting, multi-device, RLS): `node tools/debug-server/run-tests.js --layer L3`

**Always use the app UI to create/modify test data.** Raw SQL inserts bypass SQLite triggers — `change_log` never gets populated, so records will never sync.
