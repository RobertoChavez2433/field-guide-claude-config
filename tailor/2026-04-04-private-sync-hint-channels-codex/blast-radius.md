# Blast Radius

## RealtimeHintHandler (class)

- **Risk Score**: 0.81 (high — touches bootstrap chain)
- **Direct dependents**: 5
- **Depth-2 dependents**: 5 (potential via transitive import)

### Depth 1 (direct — risk 1.0)
| File | References | Impact |
|------|-----------|--------|
| `lib/core/bootstrap/app_initializer.dart` | 2 | Creates, rebinds, disposes handler in auth listener |
| `lib/features/sync/application/fcm_handler.dart` | 2 | Uses static methods: `parseHintPayload`, `dirtyScopeFromHint` |
| `lib/features/sync/application/sync_initializer.dart` | 3 | Creates handler, calls `subscribe()` |
| `lib/features/sync/di/sync_providers.dart` | 1 | Return type in `initialize()` |
| `test/features/sync/application/realtime_hint_handler_test.dart` | 9 | Full test coverage |

### Depth 2 (transitive — risk 0.62)
| File | Impact |
|------|--------|
| `lib/core/di/app_bootstrap.dart` | Imports app_initializer |
| `lib/core/di/app_providers.dart` | Imports sync_providers |
| `lib/main.dart` | Imports app_initializer |
| `lib/main_driver.dart` | Imports app_initializer |
| `test/features/sync/application/fcm_handler_test.dart` | Imports fcm_handler |

## HintPayload (class)

- **Risk Score**: 0.81
- **Direct dependents**: 5 (same file importers)
- **Confirmed references**: 0 (used internally + via statics, not directly imported by name)
- **Impact**: Low — only used inside `realtime_hint_handler.dart` and via static methods

## SyncOrchestrator (class)

- **Total importers**: 30 files (production + test)
- **Key production consumers**: app_initializer, sync_providers, fcm_handler, realtime_hint_handler, sync_initializer, sync_enrollment_service, project_provider, sync_provider
- **Impact**: NOT being modified directly — only its consumers change how they interact with hints

## DirtyScopeTracker (class)

- **Importers**: 9 files
- **Production**: sync_engine_factory, sync_initializer, sync_orchestrator, sync_orchestrator_builder, sync_engine
- **Test**: fcm_handler_test, realtime_hint_handler_test, sync_lifecycle_manager_test, dirty_scope_tracker_test
- **Impact**: NOT being modified — upstream consumer flow unchanged

## SQL Trigger Functions

All 3 trigger functions broadcast to `sync_hints:{company_id}`. Change affects:
- 20 table triggers (listed in ground-truth.md)
- Edge function fan-out (daily-sync-push)
- Every company in the system

## Dead Code Targets (sync-related)

No sync-related dead code found at confidence >= 0.8.
