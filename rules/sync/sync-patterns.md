---
paths:
  - "lib/features/sync/**/*.dart"
---

# Sync Architecture

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  lib/features/sync/presentation/providers/sync_provider.dart │
│  • Exposes sync state to UI                                  │
│  • Screens: SyncDashboardScreen, ConflictViewerScreen        │
│  • Widgets: SyncStatusIcon, DeletionNotificationBanner       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│  lib/features/sync/application/sync_orchestrator.dart        │
│  lib/features/sync/application/sync_lifecycle_manager.dart   │
│  lib/features/sync/application/background_sync_handler.dart  │
│  lib/features/sync/application/fcm_handler.dart              │
│  • Routes sync based on ProjectMode                          │
│  • Manages app-lifecycle-driven sync triggers                │
│  • Handles FCM push notifications for sync signals           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      ENGINE LAYER                            │
│  lib/features/sync/engine/sync_engine.dart                   │
│  lib/features/sync/engine/sync_control_service.dart          │
│  • SyncEngine: core sync orchestration                       │
│  • ChangeTracker: reads change_log for pending changes       │
│  • ConflictResolver: handles data conflicts                  │
│  • IntegrityChecker: post-sync consistency                   │
│  • SyncMutex: prevents concurrent syncs                      │
│  • SyncRegistry: ordered table adapter registry              │
│  • OrphanScanner: detects orphaned local records             │
│  • StorageCleanup: post-sync file cleanup                    │
│  • ScopeType: tenant-scope enum (direct/viaProject/etc.)     │
│  • SyncControlService: circuit-breaker + health UI state     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    TABLE ADAPTERS (22)                       │
│  lib/features/sync/adapters/table_adapter.dart (base)        │
│  • One adapter per syncable table                            │
│  • Pure configuration + conversion objects                   │
│  • Declares FK ordering, scope type, type converters         │
│  • TypeConverters for column-level data type mapping         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                            │
│  lib/features/sync/domain/sync_types.dart                    │
│  • SyncResult value object (pushed/pulled/errors/rlsDenials) │
│  • SyncAdapterStatus enum                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│  lib/features/sync/data/adapters/mock_sync_adapter.dart      │
│  • Mock adapter for test environments (no-network)           │
│  • Supabase I/O is handled directly by SyncEngine — there   │
│    is no separate supabase_sync_adapter.dart file            │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Sync Operation Flow

```
User Action (Settings, Dashboard, or auto-reconnect)
    │
    ▼
SyncProvider.syncAll()
    │
    ▼
SyncOrchestrator.syncProject(project)
    │
    ▼
SyncEngine.syncAll()
    │
    ├─► SyncMutex.acquire()
    ├─► ChangeTracker.getPendingChanges()   ← reads change_log table
    ├─► For each TableAdapter (ordered by SyncRegistry):
    │   ├─► adapter.convertForRemote(localRecord)
    │   ├─► TableAdapter.push(records)        ← interface contract
    │   ├─► TableAdapter.pull(lastSyncTimestamp) ← interface contract
    │   ├─► adapter.convertForLocal(remoteRecord)
    │   └─► ConflictResolver.resolve(conflicts)
    │
    │   NOTE: SyncEngine calls the TableAdapter interface only.
    │   The SyncEngine handles all Supabase I/O directly — the
    │   TableAdapter is the contract, not any separate adapter class.
    ├─► IntegrityChecker.validate()
    └─► SyncMutex.release()
```

### Change Tracking

SQLite triggers automatically populate the `change_log` table on every INSERT, UPDATE, and DELETE to syncable tables. The `ChangeTracker` class reads unprocessed `change_log` entries to determine what needs pushing to Supabase. There is no `sync_queue` table.

```
Local Write (any table)
    │
    ▼  [SQLite trigger fires]
change_log row inserted (table, record_id, operation, processed=0)
    │
    ▼  [next sync cycle]
ChangeTracker.getPendingChanges() → groups by table
    │
    ▼
SyncEngine pushes records, marks entries processed=1
```

### Multi-Backend Flow

```
SyncOrchestrator.syncProject(project)
    │
    ├─► if ProjectMode.localAgency
    │   └─► SyncEngine
    │       └─► Supabase Backend
    │
    └─► if ProjectMode.mdot (future)
        └─► AASHTOWareSyncAdapter
            └─► AASHTOWare OpenAPI
```

## Class Relationships

```
┌──────────────────┐
│  TableAdapter    │  <<abstract>>
│ ─────────────── │
│ + tableName      │
│ + scopeType      │
│ + fkDependencies │
│ + converters     │
│ + insertOnly     │
│ + convertForRemote() │
│ + convertForLocal()  │
└────────▲─────────┘
         │ extends (22 concrete adapters)
    [see Adapters section below]

┌──────────────────┐     ┌──────────────────┐
│   SyncEngine     │────►│  SyncRegistry    │
│ ─────────────── │     │ (ordered adapters)│
│ + syncAll()      │     └──────────────────┘
│ + syncProject()  │
└────────┬─────────┘
         │ uses
    ┌────┴────┐
    ▼         ▼
┌──────────┐ ┌───────────────┐
│ Change   │ │ Conflict      │
│ Tracker  │ │ Resolver      │
└──────────┘ └───────────────┘
```

## Adapters

### Base Class

`lib/features/sync/adapters/table_adapter.dart` — abstract class. The SyncEngine calls `convertForRemote()` before push and `convertForLocal()` after pull. Adapters are pure configuration + conversion objects; the engine handles all Supabase I/O.

Key properties:
- `tableName` — must match SQLite/Supabase table name exactly
- `scopeType` — how this table is tenant-scoped (`ScopeType`)
- `fkDependencies` — tables that must be pushed first (FK parents)
- `converters` — column-level `TypeConverter` instances
- `localOnlyColumns` / `remoteOnlyColumns` — stripped during conversion
- `insertOnly` — true for append-only tables (e.g., consent_records — legal audit trail)
- `isFileAdapter` — true for photo/document/export adapters (3-phase storage bucket push)
- `naturalKeyColumns` — for UNIQUE constraint pre-check before upsert (prevents 23505 errors)

### Concrete Adapters (22)

| Adapter | Table |
|---------|-------|
| `ProjectAdapter` | projects |
| `LocationAdapter` | locations |
| `ContractorAdapter` | contractors |
| `EquipmentAdapter` | equipment |
| `PersonnelTypeAdapter` | personnel_types |
| `BidItemAdapter` | bid_items |
| `DailyEntryAdapter` | daily_entries |
| `EntryContractorsAdapter` | entry_contractors |
| `EntryEquipmentAdapter` | entry_equipment |
| `EntryPersonnelCountsAdapter` | entry_personnel_counts |
| `EntryQuantitiesAdapter` | entry_quantities |
| `PhotoAdapter` | photos |
| `InspectorFormAdapter` | inspector_forms |
| `FormResponseAdapter` | form_responses |
| `FormExportAdapter` | form_exports |
| `EntryExportAdapter` | entry_exports |
| `DocumentAdapter` | documents |
| `TodoItemAdapter` | todo_items |
| `ProjectAssignmentAdapter` | project_assignments |
| `CalculationHistoryAdapter` | calculation_history |
| `ConsentRecordAdapter` | user_consent_records |
| `SupportTicketAdapter` | support_tickets |
| `TypeConverters` | (shared utility, not a table adapter) |

## Engine Components

| Class | File | Purpose |
|-------|------|---------|
| `SyncEngine` | `engine/sync_engine.dart` | Core orchestration: push/pull loop, conflict dispatch |
| `ChangeTracker` | `engine/change_tracker.dart` | Reads `change_log`; groups pending changes by table |
| `ConflictResolver` | `engine/conflict_resolver.dart` | Last-writer-wins + manual resolution support |
| `IntegrityChecker` | `engine/integrity_checker.dart` | Post-sync FK consistency validation |
| `SyncMutex` | `engine/sync_mutex.dart` | Prevents concurrent sync runs |
| `SyncRegistry` | `engine/sync_registry.dart` | Ordered list of all active `TableAdapter` instances |
| `OrphanScanner` | `engine/orphan_scanner.dart` | Detects local records with no valid FK parent |
| `StorageCleanup` | `engine/storage_cleanup.dart` | Deletes local files after successful remote upload |
| `ScopeType` | `engine/scope_type.dart` | Enum: `direct`, `viaProject`, `viaEntry`, `viaContractor` |
| `SyncControlService` | `engine/sync_control_service.dart` | Circuit-breaker state + health metrics for UI |

## Application Layer

| Class | File | Purpose |
|-------|------|---------|
| `SyncOrchestrator` | `application/sync_orchestrator.dart` | Multi-backend router; dispatches to SyncEngine (real) or MockSyncAdapter (test) |
| `SyncLifecycleManager` | `application/sync_lifecycle_manager.dart` | Triggers sync on app foreground / reconnect events |
| `BackgroundSyncHandler` | `application/background_sync_handler.dart` | Schedules and runs background sync tasks |
| `FcmHandler` | `application/fcm_handler.dart` | Processes FCM push notifications that signal remote changes |

## Config, Domain, and DI

### Config

`lib/features/sync/config/sync_config.dart` — thresholds, retry limits, batch sizes, and feature flags for the sync engine.

### Domain

`lib/features/sync/domain/sync_types.dart` — shared value types used across all sync layers:
- `SyncResult` — immutable result object: `pushed`, `pulled`, `errors`, `errorMessages`, `rlsDenials`, `skippedPush`. Supports `+` operator for combining results.
- `SyncAdapterStatus` — enum: `idle`, `syncing`, `success`, `error`, `offline`, `authRequired`

### DI

`lib/features/sync/di/sync_providers.dart` — Provider definitions that wire together SyncEngine, ChangeTracker, SyncRegistry, SyncOrchestrator, and all concrete adapters.

## File Organization

```
lib/features/sync/
├── sync.dart                           # Feature entry point
│
├── adapters/                           # 22 table adapters + base
│   ├── table_adapter.dart              # Abstract base class
│   ├── type_converters.dart            # Shared type conversion utilities
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
├── engine/                             # Core sync engine
│   ├── sync_engine.dart                # Main sync orchestration
│   ├── change_tracker.dart             # Reads change_log table
│   ├── conflict_resolver.dart          # Conflict resolution
│   ├── integrity_checker.dart          # Post-sync validation
│   ├── sync_mutex.dart                 # Concurrency control
│   ├── sync_registry.dart              # Ordered adapter registry
│   ├── orphan_scanner.dart             # Orphan record detection
│   ├── scope_type.dart                 # Sync scope enumeration
│   ├── storage_cleanup.dart            # Post-sync file cleanup
│   └── sync_control_service.dart       # Circuit-breaker + health UI
│
├── domain/                             # Business rules & value types
│   ├── domain.dart                     # Barrel export
│   └── sync_types.dart                 # SyncResult, SyncAdapterStatus
│
├── data/                               # External data sources
│   ├── data.dart                       # Barrel export
│   └── adapters/
│       ├── adapters.dart               # Barrel export
│       └── mock_sync_adapter.dart      # Testing mock (no-network)
│
├── application/                        # Use cases & orchestration
│   ├── application.dart                # Barrel export
│   ├── sync_orchestrator.dart          # Multi-backend router
│   ├── sync_lifecycle_manager.dart     # App-lifecycle sync triggers
│   ├── background_sync_handler.dart    # Background sync
│   └── fcm_handler.dart               # FCM push notification handler
│
├── config/
│   └── sync_config.dart                # Sync configuration
│
├── di/
│   └── sync_providers.dart             # DI wiring for all sync components
│
└── presentation/                       # UI layer
    ├── presentation.dart               # Barrel export
    ├── providers/
    │   └── sync_provider.dart          # ChangeNotifier for UI
    ├── screens/
    │   ├── sync_dashboard_screen.dart
    │   └── conflict_viewer_screen.dart
    └── widgets/
        ├── sync_status_icon.dart
        └── deletion_notification_banner.dart
```

## Import Patterns

### Internal (within sync feature)
```dart
// From sync_provider.dart
import '../../engine/sync_engine.dart';
import '../../domain/sync_types.dart';
```

### External (from other features)
```dart
// From settings_screen.dart
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
```

### Via barrel export
```dart
// Import entire feature
import 'package:construction_inspector/features/sync/sync.dart';

// Now have access to:
// - SyncResult, SyncAdapterStatus
// - MockSyncAdapter
// - SyncOrchestrator, BackgroundSyncHandler, SyncLifecycleManager, FcmHandler
// - SyncEngine, ChangeTracker, ConflictResolver
// - TableAdapter, all concrete adapters
// - SyncProvider
```

## Sync Testing

Sync correctness is verified via a 3-layer system:

- **Layer 1** — Unit tests (fast, no device needed):
  `pwsh -Command "flutter test test/features/sync/engine/"`

### Layer 2 & Layer 3 Sync Testing

Sync integration testing is Claude-driven via test flows. See `.claude/test-flows/sync-verification-guide.md` for the current workflow.

> **Note:** The previous `run-tests.js --layer L2/L3` CLI commands have been removed. Use the Claude-driven verification guide instead.

**IMPORTANT**: Always use the app UI to create/modify test data for sync testing. Never use raw SQL, Supabase REST writes, or direct `change_log` inserts (except the one documented exception in `ChangeTracker.manualInsert()`). Bypassing the UI skips the SQLite trigger that populates `change_log`, so changes will never sync.


## Enforced Invariants (Lint Rules)

- **sync_control flag MUST be inside transaction** (S3) -- set pulling='1' inside try/finally
- **change_log cleanup MUST be conditional on RPC success** (S2) -- never unconditional DELETE
- **ConflictAlgorithm.ignore MUST have rowId==0 fallback** (S1) -- check return value, UPDATE on 0
- **No sync_status column** (S4) -- deprecated pattern, only change_log is used
- **toMap() MUST include project_id for synced child models** (S5)
- **_lastSyncTime only updated in success path** (S8)
