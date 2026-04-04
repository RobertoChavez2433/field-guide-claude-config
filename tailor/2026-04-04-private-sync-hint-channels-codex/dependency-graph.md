# Dependency Graph

## Direct Changes

| File | Symbols | Change Type |
|------|---------|-------------|
| `lib/features/sync/application/realtime_hint_handler.dart` | `RealtimeHintHandler`, `HintPayload` | MODIFY — replace `subscribe()` with private channel registration + subscription |
| `lib/features/sync/application/sync_initializer.dart` | `SyncInitializer.create()` | MODIFY — wire device_install_id and channel registration into startup |
| `lib/core/bootstrap/app_initializer.dart` | Auth listener block (L117-262) | MODIFY — update rebind flow for private channel re-registration |
| `supabase/migrations/20260404000000_sync_hint_broadcast_trigger.sql` | `broadcast_sync_hint_company()`, `broadcast_sync_hint_project()`, `broadcast_sync_hint_contractor()` | MODIFY — replace single-channel broadcast with per-device fan-out |
| `supabase/functions/daily-sync-push/index.ts` | `serve()` handler | MODIFY — query sync_hint_subscriptions for per-device FCM fan-out |
| NEW: `supabase/migrations/YYYYMMDDHHMMSS_sync_hint_subscriptions.sql` | `sync_hint_subscriptions` table, `register_sync_hint_channel()` RPC | CREATE |
| NEW: device_install_id persistence (in PreferencesService or dedicated service) | | CREATE |

## Upstream Dependencies (what changed files import)

```
realtime_hint_handler.dart
  ├── logger.dart
  ├── sync_orchestrator.dart
  │   ├── database_service.dart
  │   ├── dirty_scope_tracker.dart
  │   ├── sync_engine.dart
  │   ├── sync_registry.dart
  │   └── app_config_provider.dart
  └── sync_types.dart (DirtyScope, SyncMode)

sync_initializer.dart
  ├── database_service.dart
  ├── auth_provider.dart
  ├── auth_service.dart
  ├── app_config_provider.dart
  ├── company_local_datasource.dart
  ├── realtime_hint_handler.dart
  ├── fcm_handler.dart
  ├── sync_orchestrator.dart
  ├── sync_orchestrator_builder.dart
  ├── sync_lifecycle_manager.dart
  ├── sync_enrollment_service.dart
  └── dirty_scope_tracker.dart

app_initializer.dart
  ├── supabase_config.dart
  ├── database_service.dart
  ├── sync_providers.dart
  ├── realtime_hint_handler.dart
  ├── fcm_handler.dart
  └── sync_types.dart
```

## Downstream Consumers (what imports changed files)

```
realtime_hint_handler.dart ← imported by:
  ├── app_initializer.dart (auth listener rebinding)
  ├── sync_initializer.dart (initial creation)
  ├── sync_providers.dart (DI delegation)
  ├── fcm_handler.dart (uses parseHintPayload, dirtyScopeFromHint statics)
  └── realtime_hint_handler_test.dart

sync_initializer.dart ← imported by:
  └── sync_providers.dart

sync_orchestrator.dart ← imported by:
  ├── 30 files (production + test)
  ├── Key: app_initializer, sync_providers, fcm_handler, realtime_hint_handler
  └── UI: project_list_screen, sync_provider, admin_dashboard_screen, sign_out_dialog
```

## Data Flow Diagram

```
                                     ┌──────────────────┐
                                     │  SQL Trigger      │
                                     │  (table mutation) │
                                     └────────┬─────────┘
                                              │
                                 ┌────────────┴────────────┐
                                 ▼                         ▼
                    ┌─────────────────────┐   ┌──────────────────────┐
                    │ broadcast_sync_hint  │   │ invoke_daily_sync    │
                    │ _company/_project/   │   │ _push (edge fn)      │
                    │ _contractor          │   │                      │
                    └────────┬────────────┘   └────────┬─────────────┘
                             │                          │
              ┌──────────────┴──────────┐               │
              ▼  CURRENT (predictable)  ▼  NEW (opaque) │
    ┌───────────────────┐  ┌──────────────────────┐     │
    │ sync_hints:       │  │ sync_hint_subscript.  │     │
    │ {company_id}      │  │ lookup by company_id  │     │
    │ (single channel)  │  │ → N device channels   │     │
    └────────┬──────────┘  └────────┬─────────────┘     │
             │                       │                    │
             ▼                       ▼                    ▼
    ┌───────────────────┐  ┌───────────────────┐  ┌──────────────┐
    │ RealtimeHint      │  │ RealtimeHint      │  │ FCM push to  │
    │ Handler (client)  │  │ Handler (client)  │  │ device tokens│
    │ subscribe()       │  │ subscribePrivate() │  │              │
    └────────┬──────────┘  └────────┬──────────┘  └──────┬───────┘
             │                       │                     │
             ▼                       ▼                     ▼
    ┌──────────────────────────────────────────────────────────────┐
    │ DirtyScopeTracker.markDirty() → SyncOrchestrator.quickSync  │
    └──────────────────────────────────────────────────────────────┘
```
