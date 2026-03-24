---
paths:
  - "lib/features/sync/**/*.dart"
---

<!-- TODO: Remove [BRANCH: feat/sync-engine-rewrite] annotations from 5 section headings after branch merges to main -->

# Sync Architecture Diagram

## Layer Diagram [BRANCH: feat/sync-engine-rewrite]

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  lib/features/sync/presentation/providers/sync_provider.dart │
│  • Exposes sync state to UI                                  │
│  • Screens: SyncDashboard, ConflictViewer, ProjectSelection  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│  lib/features/sync/application/sync_orchestrator.dart        │
│  lib/features/sync/application/background_sync_handler.dart  │
│  • Routes sync based on ProjectMode                          │
│  • Coordinates adapters and background sync triggers         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      ENGINE LAYER                            │
│  lib/features/sync/engine/sync_engine.dart                   │
│  • SyncEngine: core sync orchestration                       │
│  • ChangeTracker: identifies pending changes                 │
│  • ConflictResolver: handles data conflicts                  │
│  • IntegrityChecker: post-sync consistency                   │
│  • SyncMutex: prevents concurrent syncs                      │
│  • SyncRegistry: ordered table adapter registry              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    TABLE ADAPTERS (17)                       │
│  lib/features/sync/adapters/table_adapter.dart (base)        │
│  • One adapter per syncable table                            │
│  • Handles push/pull/conflict for its table                  │
│  • TypeConverters for data type mapping                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                            │
│  lib/features/sync/domain/sync_adapter.dart                  │
│  lib/features/sync/domain/sync_types.dart                    │
│  • SyncAdapter interface                                     │
│  • SyncResult value object                                   │
│  • SyncAdapterStatus enum                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│  lib/features/sync/data/adapters/supabase_sync_adapter.dart  │
│  • Implements SyncAdapter for Supabase backend               │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Sync Operation Flow [BRANCH: feat/sync-engine-rewrite]

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
    ├─► ChangeTracker.getPendingChanges()
    ├─► For each TableAdapter (ordered by SyncRegistry):
    │   ├─► adapter.push(pendingRecords)
    │   ├─► adapter.pull(lastSyncTimestamp)
    │   └─► ConflictResolver.resolve(conflicts)
    ├─► IntegrityChecker.validate()
    └─► SyncMutex.release()
```

### Multi-Backend Flow

```
User Action
    │
    ▼
SyncOrchestrator.syncProject(project)
    │
    ├─► if ProjectMode.localAgency
    │   └─► SupabaseSyncAdapter
    │       └─► Supabase Backend
    │
    └─► if ProjectMode.mdot
        └─► AASHTOWareSyncAdapter (future)
            └─► AASHTOWare OpenAPI
```

## Class Relationships [BRANCH: feat/sync-engine-rewrite]

```
┌──────────────────┐
│  SyncAdapter     │  <<interface>>
│ ─────────────── │
│ + syncAll()      │
│ + syncProject()  │
└────────▲─────────┘
         │ implements
┌────────┴──────────────┐
│ SupabaseSyncAdapter   │
└───────────────────────┘

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

┌──────────────────┐
│  TableAdapter    │  <<abstract>>
│ ─────────────── │
│ + push()         │
│ + pull()         │
│ + tableName      │
└────────▲─────────┘
         │ extends (17 concrete adapters)
```

## File Organization [BRANCH: feat/sync-engine-rewrite]

```
lib/features/sync/
├── sync.dart                           # Feature entry point
│
├── adapters/                           # 17 table adapters + base
│   ├── table_adapter.dart              # Abstract base class
│   ├── type_converters.dart            # Shared type conversion
│   ├── project_adapter.dart            # ... through ...
│   └── photo_adapter.dart              # 17 concrete adapters
│
├── engine/                             # Core sync engine
│   ├── sync_engine.dart                # Main sync orchestration
│   ├── change_tracker.dart             # Tracks pending changes
│   ├── conflict_resolver.dart          # Conflict resolution
│   ├── integrity_checker.dart          # Post-sync validation
│   ├── sync_mutex.dart                 # Concurrency control
│   ├── sync_registry.dart              # Ordered adapter registry
│   ├── orphan_scanner.dart             # Orphan record detection
│   ├── scope_type.dart                 # Sync scope enumeration
│   └── storage_cleanup.dart            # Post-sync cleanup
│
├── domain/                             # Business rules & interfaces
│   ├── domain.dart                     # Barrel export
│   ├── sync_adapter.dart               # Interface + enums
│   └── sync_types.dart                 # Shared type definitions
│
├── data/                               # External data sources
│   ├── data.dart                       # Barrel export
│   └── adapters/
│       ├── adapters.dart               # Barrel export
│       ├── supabase_sync_adapter.dart  # Supabase implementation
│       └── mock_sync_adapter.dart      # Testing mock
│
├── application/                        # Use cases & orchestration
│   ├── application.dart                # Barrel export
│   ├── sync_orchestrator.dart          # Multi-backend router
│   └── background_sync_handler.dart    # Background sync triggers
│
├── config/
│   └── sync_config.dart                # Sync configuration
│
└── presentation/                       # UI layer
    ├── presentation.dart               # Barrel export
    ├── providers/
    │   └── sync_provider.dart          # ChangeNotifier for UI
    ├── screens/
    │   ├── sync_dashboard_screen.dart
    │   ├── conflict_viewer_screen.dart
    │   └── project_selection_screen.dart
    └── widgets/
        ├── sync_status_banner.dart
        ├── sync_status_icon.dart
        └── deletion_notification_banner.dart
```

## Import Patterns [BRANCH: feat/sync-engine-rewrite]

### Internal (within sync feature)
```dart
// From sync_provider.dart
import '../../domain/sync_adapter.dart';
import '../../engine/sync_engine.dart';
```

### External (from other features)
```dart
// From settings_screen.dart
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';
import 'package:construction_inspector/features/sync/domain/sync_adapter.dart';
```

### Via barrel export
```dart
// Import entire feature
import 'package:construction_inspector/features/sync/sync.dart';

// Now have access to:
// - SyncAdapter, SyncResult, SyncAdapterStatus
// - SupabaseSyncAdapter
// - SyncOrchestrator, BackgroundSyncHandler
// - SyncEngine, ChangeTracker, ConflictResolver
// - SyncProvider
```

## Sync Testing

Sync correctness is verified via a 3-layer system:

- **Layer 1** — Unit tests (fast, no device needed):
  `pwsh -Command "flutter test test/features/sync/engine/"`
- **Layer 2** — Per-table push/pull/conflict scenarios (requires device + Supabase):
  `node tools/debug-server/run-tests.js --layer L2`
- **Layer 3** — Cross-cutting scenarios (multi-device, offline, RLS):
  `node tools/debug-server/run-tests.js --layer L3`

Scenario files live in `tools/debug-server/scenarios/`. Results are accessible via
`GET /test-status` on the debug server (port 3947).
