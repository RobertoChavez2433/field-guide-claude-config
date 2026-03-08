---
feature: sync
type: architecture
scope: Cloud Synchronization & Multi-Backend Support
updated: 2026-03-08
---

# Sync Feature Architecture

## Data Model

### Core Entities

| Entity | Fields | Type | Notes |
|--------|--------|------|-------|
| **SyncResult** | pushed, pulled, errors, errorMessages | Value Object | Result of sync operation |
| **SyncAdapterStatus** | idle, syncing, success, error, offline, authRequired | Enum | Current adapter state |
| **PendingOperation** | entityId, entityType, operationType, timestamp, retryCount | Internal | Queued operation in sync queue |

### Key Models

**SyncResult**:
- Returns from all sync operations
- `pushed`: count of items sent to backend
- `pulled`: count of items received from backend
- `errors`: count of failed operations
- `errorMessages`: list of error details
- Helper: `isSuccess` (errors == 0), `hasErrors` (errors > 0), `total` (pushed + pulled)

**SyncAdapterStatus**:
- `idle`: No sync in progress, ready for next operation
- `syncing`: Sync operation currently in progress
- `success`: Last sync completed without errors
- `error`: Last sync had failures
- `offline`: No network connectivity
- `authRequired`: Authentication needed (Supabase only)

**SyncAdapter Interface** (implemented by all backends):
- `name: String` - "Supabase", "AASHTOWare", etc.
- `status: SyncAdapterStatus` - Current state
- `isOnline: bool` - Network reachability
- `lastSyncTime: DateTime?` - Last successful sync timestamp
- `requiresAuthentication: bool` - Auth mandatory before sync

## Relationships

### ProjectMode → SyncAdapter (1-1)
```
Project (mode: ProjectMode)
    ├─→ ProjectMode.localAgency
    │   └─→ SupabaseSyncAdapter
    │       └─→ Supabase Backend
    │
    └─→ ProjectMode.mdot
        └─→ AASHTOWareSyncAdapter (future)
            └─→ AASHTOWare OpenAPI
```

### SyncEngine → TableAdapters (1-N) [BRANCH: feat/sync-engine-rewrite]
```
SyncEngine.syncAll()
    ├─→ SyncRegistry provides ordered list of TableAdapters
    ├─→ ChangeTracker identifies pending changes per table
    ├─→ For each TableAdapter:
    │   ├─→ Push local changes to remote
    │   ├─→ Pull remote changes to local
    │   └─→ ConflictResolver handles conflicts
    └─→ IntegrityChecker validates post-sync consistency
```

### TableAdapters (17 concrete) [BRANCH: feat/sync-engine-rewrite]
```
TableAdapter (base)
    ├─→ ProjectAdapter
    ├─→ LocationAdapter
    ├─→ ContractorAdapter
    ├─→ EquipmentAdapter
    ├─→ PersonnelTypeAdapter
    ├─→ BidItemAdapter
    ├─→ DailyEntryAdapter
    ├─→ EntryContractorsAdapter
    ├─→ EntryEquipmentAdapter
    ├─→ EntryPersonnelCountsAdapter
    ├─→ EntryQuantitiesAdapter
    ├─→ InspectorFormAdapter
    ├─→ FormResponseAdapter
    ├─→ TodoItemAdapter
    ├─→ CalculationHistoryAdapter
    ├─→ PhotoAdapter
    └─→ TypeConverters (shared utility)
```

### Entity → SyncStatus (1-1)
```
Entity (Project, DailyEntry, Photo, etc.)
    └─→ syncStatus: enum
        ├─ pending (queued for next sync)
        ├─ synced (in sync with remote)
        └─ error (last sync failed)
```

### Sync Operation Flow [BRANCH: feat/sync-engine-rewrite]
```
User triggers sync (Settings screen, Dashboard, or auto-reconnect)
    ↓
SyncProvider.syncAll()
    ↓
SyncOrchestrator.syncProject(project)
    ↓
SyncEngine.syncAll()
    ↓
SyncMutex.acquire()                         # Prevents concurrent syncs
    ↓
ChangeTracker.getPendingChanges()           # Identifies dirty records
    ↓
For each TableAdapter (ordered by SyncRegistry):
    ├─→ adapter.push(pendingRecords)        # Push local changes
    ├─→ adapter.pull(lastSyncTimestamp)      # Pull remote changes
    └─→ ConflictResolver.resolve(conflicts) # Handle conflicts
    ↓
IntegrityChecker.validate()                 # Post-sync consistency check
    ↓
SyncMutex.release()
    ↓
SyncResult returned
```

## Repository Pattern

### SyncAdapter Interface

**Abstract Methods**:
```dart
Future<SyncResult> syncAll()                  // Full sync (all entities)
Future<SyncResult> syncProject(Project p)     // Single project + children
Future<SyncResult> syncEntry(DailyEntry e)    // Single entry + photos
Future<SyncResult> syncPhoto(Photo p)         // Single photo
Future<int> getPendingCount()                 // Count pending operations
```

**Callbacks**:
```dart
void Function(SyncAdapterStatus)? onStatusChanged      // Status transitions
void Function(SyncResult)? onSyncComplete              // Sync finished
void Function(int, int?)? onProgressUpdate             // Progress (processed, total)
```

### SupabaseSyncAdapter

**Location**: `lib/features/sync/data/adapters/supabase_sync_adapter.dart`

- Implements SyncAdapter interface for Supabase backend
- Returns SyncResult for each operation
- Callbacks invoke on status/progress changes

### SyncOrchestrator

**Location**: `lib/features/sync/application/sync_orchestrator.dart`

- Routes based on `ProjectMode`
- Maintains adapter instances per mode
- Handles auth verification before sync operations

### SyncEngine [BRANCH: feat/sync-engine-rewrite]

**Location**: `lib/features/sync/engine/sync_engine.dart`

- Core sync engine coordinating all sync operations
- Uses SyncRegistry for ordered table adapter execution
- Delegates to ChangeTracker, ConflictResolver, IntegrityChecker
- SyncMutex prevents concurrent sync operations

### BackgroundSyncHandler [BRANCH: feat/sync-engine-rewrite]

**Location**: `lib/features/sync/application/background_sync_handler.dart`

- Handles background sync triggers (connectivity changes, app lifecycle)
- Coordinates with SyncOrchestrator for deferred syncs

## State Management

### Provider Type: ChangeNotifier

**SyncProvider** (`lib/features/sync/presentation/providers/sync_provider.dart`):

```dart
class SyncProvider extends ChangeNotifier {
  SyncAdapterStatus _status = SyncAdapterStatus.idle;
  SyncResult? _lastResult;
  double _progress = 0.0;
  bool _isOnline = true;
  int _pendingCount = 0;
  String? _error;

  // Getters
  SyncAdapterStatus get status
  SyncResult? get lastResult
  double get progress              // 0.0-1.0 progress bar
  bool get isOnline
  int get pendingCount
  String? get error
}
```

### Key Methods

```dart
Future<void> syncAll()             // Trigger full sync
Future<void> syncProject(p)        // Sync specific project
Future<void> syncEntry(e)          // Sync specific entry
Future<void> refreshStatus()       // Update isOnline, pendingCount
void _onStatusChanged(status)      // Internal: adapter status callback
void _onProgressUpdate(p, t)       // Internal: progress callback
```

### Lifecycle

```
App Start
    ↓
SyncProvider initialized (status=idle, isOnline=true)
    ↓
Connectivity service detects online/offline transition
    ↓
_onConnectivityChanged() called
    ↓
If online: scheduleDebouncedSync() queues sync
    ↓
User returns to app (AppLifecycle.resumed)
    ↓
Deferred sync executes → syncAll()
    ↓
SyncAdapter callbacks trigger
    ├─→ onStatusChanged(syncing)
    ├─→ onProgressUpdate(processed, total)
    └─→ onSyncComplete(result)
    ↓
SyncProvider._updateUI() called
    ├─→ status = success/error
    ├─→ lastResult = result
    └─→ notifyListeners()
    ↓
UI rebuilds with success/error state
```

## Offline Behavior

### Push Operations
- **Online**: Changes pushed to backend immediately (or debounced)
- **Offline**: Changes queued in SQLite with `syncStatus: pending`
- **On Reconnect**: Queued changes pushed automatically

### Pull Operations
- **Online**: Remote changes fetched and merged to SQLite
- **Offline**: Pull skipped; local data unchanged
- **On Reconnect**: Remote changes fetched on next sync

### Conflict Resolution (Simple, Last-Write-Wins)
- If entity modified offline and remotely:
  - Remote version overwrites local (assuming remote has later timestamp)
  - Warning logged but no user intervention needed
- Future enhancement: Configurable conflict strategies per entity type

### Sync Status Transitions

```
Initial Creation
    ↓
syncStatus = pending (local-only)
    ↓
Sync triggered
    ├─ If push succeeds → syncStatus = synced
    └─ If push fails → syncStatus = error (retry on next sync)
    ↓
If edited while synced
    ├─→ syncStatus = pending (marked dirty)
    └─→ Queued for next sync
```

## Testing Strategy

### Unit Tests (Adapter-level)
- **SupabaseSyncAdapter**: Mock SyncService, verify method delegation
- **SyncOrchestrator**: Mock adapters, verify routing logic
- **SyncResult**: Value object serialization/equality

Location: `test/features/sync/`

### Integration Tests (End-to-End)
- **Full sync flow**: Local changes → Supabase → local pull
- **Offline queue**: Mark pending → go offline → reconnect → verify push
- **Conflict handling**: Offline edit + remote edit → resolve

Location: `test/features/sync/integration/`

### Widget Tests (Provider-level)
- **SyncProvider**: Mock adapter, trigger sync, verify state changes
- **Sync UI**: Display status, progress, error messages correctly

Location: `test/features/sync/providers/`

### Test Coverage
- ≥ 85% for sync adapters
- 100% for SyncResult value object
- 80% for legacy SyncService (high complexity)

## Performance Considerations

### Target Response Times (Soft Guidelines)
- Initial sync (100 items): < 30 seconds
- Incremental sync (5-10 new items): < 5 seconds
- Progress callback update frequency: 0.5-1 second intervals

### Memory Constraints
- Photo payloads: batched in groups of 5 to reduce memory spike
- Large entry syncs: paginated to prevent OOM

### Optimization Opportunities
- Parallel adapter initialization on multi-backend support
- Batch push operations (multi-insert) instead of per-entity
- Progressive sync: Push/pull projects → entries → photos (fail-safe order)

## File Locations

```
lib/features/sync/                      [BRANCH: feat/sync-engine-rewrite]
├── adapters/                           # 17 table adapters + base
│   ├── table_adapter.dart              # Base class for all table adapters
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
│   ├── inspector_form_adapter.dart
│   ├── form_response_adapter.dart
│   ├── todo_item_adapter.dart
│   ├── calculation_history_adapter.dart
│   └── photo_adapter.dart
│
├── engine/                             # Core sync engine
│   ├── sync_engine.dart                # Main engine coordinating sync
│   ├── change_tracker.dart             # Tracks local pending changes
│   ├── conflict_resolver.dart          # Conflict resolution logic
│   ├── integrity_checker.dart          # Post-sync consistency validation
│   ├── sync_mutex.dart                 # Prevents concurrent syncs
│   ├── sync_registry.dart              # Ordered registry of table adapters
│   ├── orphan_scanner.dart             # Detects orphaned records
│   ├── scope_type.dart                 # Sync scope enumeration
│   └── storage_cleanup.dart            # Post-sync storage cleanup
│
├── domain/
│   ├── domain.dart                     # Barrel export
│   ├── sync_adapter.dart               # Interface + SyncResult, SyncAdapterStatus
│   └── sync_types.dart                 # Shared type definitions
│
├── data/
│   ├── data.dart                       # Barrel export
│   └── adapters/
│       ├── adapters.dart               # Barrel export
│       ├── supabase_sync_adapter.dart  # Supabase implementation
│       └── mock_sync_adapter.dart      # Testing mock
│
├── application/
│   ├── application.dart                # Barrel export
│   ├── sync_orchestrator.dart          # Multi-backend router
│   └── background_sync_handler.dart    # Background/lifecycle sync triggers
│
├── config/
│   └── sync_config.dart                # Sync configuration parameters
│
├── presentation/
│   ├── presentation.dart               # Barrel export
│   ├── providers/
│   │   ├── providers.dart              # Barrel export
│   │   └── sync_provider.dart          # ChangeNotifier for UI
│   ├── screens/
│   │   ├── sync_dashboard_screen.dart  # Sync status dashboard
│   │   ├── conflict_viewer_screen.dart # View and resolve conflicts
│   │   └── project_selection_screen.dart
│   └── widgets/
│       ├── sync_status_banner.dart
│       ├── sync_status_icon.dart
│       └── deletion_notification_banner.dart
│
└── sync.dart                           # Feature entry point

lib/core/database/
└── database_service.dart               # SQLite with sync status tracking
```

### Import Pattern

```dart
// Within sync feature
import 'package:construction_inspector/features/sync/domain/sync_adapter.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/features/sync/engine/sync_engine.dart';

// From other features
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';
```
