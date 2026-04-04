# Dependency Graph

## Direct Changes

The spec proposes changes across these key files/areas:

| File | Change Type | Line Range |
|------|------------|------------|
| `lib/features/sync/engine/sync_engine.dart` | Modify (add quick/full mode support) | 83-1556 |
| `lib/features/sync/application/sync_orchestrator.dart` | Modify (add sync mode parameter) | 32-660 |
| `lib/features/sync/application/sync_lifecycle_manager.dart` | Modify (quick sync on resume) | 14-155 |
| `lib/features/sync/application/fcm_handler.dart` | Modify (hint-based invalidation) | 28-140 |
| `lib/features/sync/engine/scope_type.dart` | Extend (dirty scope tracking) | 13-29 |
| `lib/features/sync/config/sync_config.dart` | Extend (mode-specific config) | 1-43 |
| `lib/features/sync/presentation/providers/sync_provider.dart` | Modify (expose mode) | 18-347 |
| `lib/features/sync/presentation/widgets/sync_status_icon.dart` | Modify (global placement) | 15-54 |
| `lib/core/router/scaffold_with_nav_bar.dart` | Modify (add global sync action) | NEW |
| NEW: `lib/features/sync/engine/dirty_scope_tracker.dart` | Create | - |
| NEW: `lib/features/sync/application/realtime_hint_handler.dart` | Create | - |

## Upstream Dependencies (from SyncEngine)

```
SyncEngine
├── imports: logger.dart, sync_config.dart, sync_registry.dart,
│            change_tracker.dart, integrity_checker.dart, scope_type.dart,
│            table_adapter.dart
├── imported by: sync_orchestrator.dart, sync_engine_factory.dart,
│                background_sync_handler.dart
│
SyncOrchestrator (107 nodes in full graph)
├── imports: logger.dart, analytics.dart, database_service.dart,
│            supabase_config.dart, test_mode_config.dart,
│            user_profile_sync_datasource.dart, app_config_provider.dart,
│            sync_types.dart, mock_sync_adapter.dart, sync_config.dart,
│            sync_engine.dart, sync_registry.dart
├── imported by: 26 files (see blast-radius.md)
│
SyncLifecycleManager (16 nodes)
├── imports: logger.dart
├── imported by: sync_initializer.dart, sync_providers.dart, app_dependencies.dart
│
FcmHandler (21 nodes)
├── imports: logger.dart, auth_service.dart, sync_orchestrator.dart
├── imported by: sync_initializer.dart, fcm_handler_test.dart
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│                   TRIGGER SOURCES                    │
│                                                      │
│  App Resume ──► SyncLifecycleManager                │
│  FCM Message ──► FcmHandler                          │
│  User Tap ──► SyncProvider                           │
│  Background ──► BackgroundSyncHandler                │
│  [NEW] Supabase Realtime ──► RealtimeHintHandler     │
│                                                      │
│  ALL currently call: syncLocalAgencyProjects()        │
│  SPEC wants: Quick vs Full vs Maintenance modes       │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              SyncOrchestrator                        │
│  syncLocalAgencyProjects() → _syncWithRetry()        │
│                              → _doSync()             │
│                                 → engine.pushAndPull()│
│                                                      │
│  SPEC wants: Quick sync path that skips broad pull   │
│  SPEC wants: Mode parameter to route differently     │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              SyncEngine                              │
│  pushAndPull() → _push() → _pull()                  │
│                                                      │
│  _push(): change_log → FK order → per-record push    │
│  _pull(): ALL adapters → cursor-based per-table      │
│                                                      │
│  SPEC wants: Targeted pull (only dirty scopes)       │
│  SPEC wants: Push-only quick mode                    │
└─────────────────────────────────────────────────────┘
```

## Key Wiring Chain

```
main.dart
  └─► AppInitializer.initialize()
        └─► SyncInitializer.create()
              ├─► SyncOrchestratorBuilder → SyncOrchestrator
              ├─► SyncLifecycleManager(orchestrator)
              ├─► SyncEnrollmentService(dbService, orchestrator)
              ├─► FcmHandler(authService, orchestrator)
              └─► WidgetsBinding.addObserver(lifecycleManager)
```
