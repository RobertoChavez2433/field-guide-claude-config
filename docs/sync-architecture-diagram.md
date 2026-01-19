# Sync Architecture Diagram

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  lib/features/sync/presentation/providers/sync_provider.dart │
│  • Exposes sync state to UI                                  │
│  • Wraps legacy SyncService for backward compatibility       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│  lib/features/sync/application/sync_orchestrator.dart        │
│  • Routes sync based on ProjectMode                          │
│  • Coordinates multiple adapters                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                            │
│  lib/features/sync/domain/sync_adapter.dart                  │
│  • SyncAdapter interface                                     │
│  • SyncResult value object                                   │
│  • SyncAdapterStatus enum                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│  lib/features/sync/data/adapters/supabase_sync_adapter.dart  │
│  • Implements SyncAdapter                                    │
│  • Wraps legacy SyncService                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    LEGACY SERVICE                            │
│  lib/services/sync_service.dart                              │
│  • Full Supabase sync implementation                         │
│  • Connectivity monitoring                                   │
│  • Push/pull logic                                           │
│  • Queue management                                          │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Sync Operation Flow

```
User Action (Settings Screen)
    │
    ▼
SyncProvider.sync()
    │
    ▼
SyncService.syncAll()  [legacy]
    │
    ├─► Push pending changes → Supabase
    │
    └─► Pull remote changes → SQLite
```

### Future Multi-Backend Flow

```
User Action
    │
    ▼
SyncOrchestrator.syncProject(project)
    │
    ├─► if ProjectMode.localAgency
    │   └─► SupabaseSyncAdapter
    │       └─► SyncService (legacy)
    │           └─► Supabase Backend
    │
    └─► if ProjectMode.mdot
        └─► AASHTOWareSyncAdapter (future)
            └─► AASHTOWare OpenAPI
```

## Class Relationships

```
┌──────────────────┐
│  SyncAdapter     │  <<interface>>
│ ─────────────── │
│ + syncAll()      │
│ + syncProject()  │
│ + syncEntry()    │
│ + syncPhoto()    │
└────────▲─────────┘
         │
         │ implements
         │
┌────────┴──────────────┐
│ SupabaseSyncAdapter   │
│ ───────────────────── │
│ - _legacySyncService  │
│ + syncAll()           │
│ + syncProject()       │
└────────┬──────────────┘
         │
         │ wraps
         │
┌────────▼──────────────┐
│   SyncService         │  [LEGACY]
│ ───────────────────── │
│ - _dbService          │
│ - _supabase           │
│ + syncAll()           │
│ + queueOperation()    │
└───────────────────────┘
```

## File Organization

```
lib/features/sync/
├── sync.dart                           # Feature entry point
│
├── domain/                             # Business rules & interfaces
│   ├── domain.dart                     # Barrel export
│   └── sync_adapter.dart               # Interface + enums
│
├── data/                               # External data sources
│   ├── data.dart                       # Barrel export
│   └── adapters/
│       ├── adapters.dart               # Barrel export
│       └── supabase_sync_adapter.dart  # Supabase implementation
│
├── application/                        # Use cases & orchestration
│   ├── application.dart                # Barrel export
│   └── sync_orchestrator.dart          # Multi-backend router
│
└── presentation/                       # UI layer
    ├── presentation.dart               # Barrel export
    └── providers/
        ├── providers.dart              # Barrel export
        └── sync_provider.dart          # ChangeNotifier for UI
```

## Import Patterns

### Internal (within sync feature)
```dart
// From sync_provider.dart
import '../../domain/sync_adapter.dart';
import '../../../services/sync_service.dart' as legacy;
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
// - SyncAdapter
// - SyncResult
// - SyncAdapterStatus
// - SupabaseSyncAdapter
// - SyncOrchestrator
// - SyncProvider
```

## Backward Compatibility

Old imports still work via re-exports:

```dart
// OLD (deprecated but functional)
import 'package:construction_inspector/services/sync/sync_adapter.dart';
import 'package:construction_inspector/services/sync/supabase_sync_adapter.dart';
import 'package:construction_inspector/services/sync/sync_orchestrator.dart';
import 'package:construction_inspector/presentation/providers/sync_provider.dart';

// All automatically redirect to new locations
```
