# Blast Radius

## Summary

| Symbol | Direct Dependents | Total (2-hop) | Risk Score |
|--------|-------------------|---------------|------------|
| `SyncEngine` class | 7 (3 lib, 4 test) | 38 | 0.69 |
| `SyncOrchestrator` class | 30 (16 lib, 14 test) | 61 | 0.80 |
| `SyncProvider` class | 13 (6 lib, 7 test) | 19 | 0.88 |
| `TableAdapter` class | 28 (25 lib, 3 test) | 68 | 0.77 |

## SyncEngine Blast Radius

### Direct Dependents (Depth 1) — 7 files
- `sync/application/background_sync_callback.dart` (2 refs)
- `sync/application/sync_engine_factory.dart` (8 refs) — **highest coupling**
- `sync/application/sync_orchestrator.dart` (11 refs) — **highest coupling**
- `test/sync/engine/sync_engine_delete_test.dart` (2 refs)
- `test/sync/engine/sync_engine_e2e_test.dart` (4 refs)
- `test/sync/engine/sync_engine_lww_test.dart` (1 ref)
- `test/sync/engine/sync_engine_test.dart` (13 refs) — **most references**

### SyncEngine Subclasses (test-only)
- `_EmptyResponseSyncEngine` (sync_engine_delete_test.dart:363)
- `_LwwTestSyncEngine` (sync_engine_lww_test.dart:169)
- `_NullTimestampLwwTestSyncEngine` (sync_engine_lww_test.dart:205)

### Migration Note
SyncEngine subclasses in tests will break when the class API changes. These tests must be rewritten as characterization tests against the new handler classes.

## SyncOrchestrator Blast Radius

### Direct Dependents (Depth 1) — 30 files

**Production (16)**:
- `app_dependencies.dart` (1 ref)
- `driver_server.dart` (5 refs) — driver status API
- `scaffold_with_nav_bar.dart` (1 ref) — sync UI indicator
- `projects_providers.dart` (1 ref) — DI
- `project_provider.dart` (1 ref)
- `project_list_screen.dart` (6 refs)
- `project_setup_screen.dart` (1 ref)
- `admin_dashboard_screen.dart` (1 ref)
- `sign_out_dialog.dart` (1 ref)
- `fcm_handler.dart` (2 refs)
- `realtime_hint_handler.dart` (2 refs)
- `sync_enrollment_service.dart` (2 refs)
- `sync_initializer.dart` (1 ref)
- `sync_orchestrator_builder.dart` (4 refs)
- `sync_providers.dart` (3 refs)
- `sync_provider.dart` (6 refs)

**Test (14)**: Various sync and presentation tests

### SyncOrchestrator Subclasses (test-only)
- `MockSyncOrchestrator` (scaffold_with_nav_bar_test.dart:23)
- `_TrackingOrchestrator` (fcm_handler_test.dart:14)
- `_MockSyncOrchestrator` (sync_engine_circuit_breaker_test.dart:12)

## SyncProvider Blast Radius

### Direct Dependents — 13 confirmed files
- `sync_dashboard_screen.dart` (8 refs) — **heaviest consumer**
- `sync_status_icon.dart` (4 refs)
- `sync_section.dart` (3 refs)
- `scaffold_with_nav_bar.dart` (1 ref)
- `sign_out_dialog.dart` (1 ref)
- `sync_providers.dart` (2 refs) — DI wiring
- 7 test files

### Depth 2 (6 additional files)
- `app_initializer.dart`, `app_providers.dart`, `app_router.dart`, `sync_routes.dart`, `project_list_screen.dart`, `settings_screen.dart`

## TableAdapter Blast Radius

### Direct Dependents — 28 files
- All 22 concrete adapter subclasses (1 ref each)
- `integrity_checker.dart` (1 ref)
- `sync_engine.dart` (11 refs) — **highest coupling**
- `sync_registry.dart` (4 refs)
- 3 test files

### TableAdapter Subclasses — 22 production + 1 test
All 22 production adapters extend `TableAdapter`. One test stub: `_StubAdapter` (conflict_local_datasource_test.dart:13).

## Dead Code Targets (sync-related)

296 sync-related dead symbols detected (confidence >= 0.8). Key categories:
- **Test helpers**: `sync_test_data.dart` (19 dead symbols), `sync_engine_test_helpers.dart` (2 dead functions)
- **Unused test files**: `sync_engine_validation_test.dart`, `sync_engine_tables_test.dart`, `change_tracker_circuit_breaker_test.dart`, `orphan_scanner_test.dart`
- **Schema**: `sync_tables.dart` (1 dead class)

These are candidates for cleanup during or after the refactor.

## Import Chain: Feature Boundary Crossings

SyncOrchestrator is imported by files outside `features/sync/`:
- `core/di/app_dependencies.dart`
- `core/driver/driver_server.dart`
- `core/router/scaffold_with_nav_bar.dart`
- `features/projects/` (3 files)
- `features/settings/` (2 files)
- `features/auth/` (indirectly via DI)

These boundary crossings must be preserved or replaced with equivalent interfaces during refactor.
