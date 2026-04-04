# Blast Radius

## Per-Symbol Impact

### SyncOrchestrator (highest risk)
- **Risk score**: 0.79
- **Direct dependents**: 26 confirmed, 31 potential
- **Key consumers** (production):
  - `app_dependencies.dart` — DI registration
  - `driver_server.dart` — test driver (5 refs)
  - `scaffold_with_nav_bar.dart` — nav bar integration
  - `project_list_screen.dart` — project sync trigger (6 refs)
  - `sync_provider.dart` — UI state bridge (5 refs)
  - `fcm_handler.dart` — FCM sync trigger
  - `sync_enrollment_service.dart` — project enrollment
  - `sync_initializer.dart` — initialization
- **Tests**: 11 test files reference SyncOrchestrator

### ScopeType (highest confirmed refs)
- **Risk score**: 0.90
- **Direct dependents**: 44 confirmed, 15 potential
- **Impact**: Every single table adapter uses ScopeType. Changes to this enum affect ALL 22 adapters + sync engine + 20 test files.
- **Safe extension**: Adding new enum values is backward-compatible. Modifying semantics of existing values is high-risk.

### SyncEngine
- **Risk score**: 0.69
- **Direct dependents**: 10 confirmed, 27 potential
- **Key consumers**: sync_orchestrator.dart (11 refs), sync_engine_factory.dart (8 refs), background_sync_handler.dart (3 refs)
- **Tests**: 6 test files

### TableAdapter
- **Risk score**: 0.78
- **Direct dependents**: 28 confirmed, 38 potential
- **Descendants**: 22 concrete adapters + 1 test stub
- **Impact**: Any change to TableAdapter interface affects all 22 adapters

### ChangeTracker
- **Risk score**: 0.86
- **Direct dependents**: 9 confirmed, 7 potential
- **Key consumers**: sync_engine.dart (2 refs), integrity_checker.dart (1 ref)
- **Tests**: 7 test files

### SyncLifecycleManager
- **Risk score**: 0.70
- **Direct dependents**: 3 confirmed, 10 potential
- **Key consumers**: app_dependencies.dart, sync_initializer.dart, sync_providers.dart
- **Impact**: Low blast radius — changes are contained

## Class Hierarchies

### SyncEngine
- No ancestors
- 3 test descendants (all in test files): `_LwwTestSyncEngine`, `_EmptyResponseSyncEngine`, `_NullTimestampLwwTestSyncEngine`

### TableAdapter (abstract)
- No ancestors
- 22 production descendants (one per synced table)
- 1 test descendant: `_StubAdapter`

### SyncOrchestrator
- No ancestors
- 3 test descendants: `MockSyncOrchestrator`, `_TrackingOrchestrator`, `_MockSyncOrchestrator`

## Dead Code (sync-related, file-level)

Notable dead files (zero importers, production code):
- `lib/core/database/schema/sync_tables.dart` — unused schema file
- `lib/features/settings/presentation/widgets/sync_section.dart` — unreferenced widget
- Barrel exports with zero importers: `sync.dart`, `application.dart`, `data.dart`, `di.dart`, `domain.dart`, `presentation.dart`, `providers.dart`

Supabase function:
- `supabase/functions/daily-sync-push/index.ts` — edge function for FCM sync trigger (no local importers expected)

## Summary Counts

| Category | Count |
|----------|-------|
| Direct production files affected | 12 |
| Potential production files affected | 31 |
| Test files affected | 40+ |
| Dead code files (sync-related) | 8 barrel exports + 2 unused |
| Cleanup targets | `sync_section.dart`, `sync_tables.dart` |
