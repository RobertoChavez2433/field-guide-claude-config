# Sync Verification System — Dependency Graph

## Direct Changes

### 1. New Driver Endpoints (Dart — lib/core/driver/)

| File | Symbol | Change Type | Lines |
|------|--------|------------|-------|
| `lib/core/driver/driver_server.dart` | `DriverServer` | MODIFY | 42-990 |
| | `_handleRequest` | MODIFY (add 5 new route branches) | ~85-130 |
| | `_handleSync` | CREATE | new |
| | `_handleSyncStatus` | CREATE | new |
| | `_handleRemoveFromDevice` | CREATE | new |
| | `_handleLocalRecord` | CREATE | new |
| | `_handleCreateRecord` | CREATE | new |

**Dependencies for new endpoints:**
- `_handleSync` needs: `SyncOrchestrator` (or direct `SyncEngine.pushAndPull()`)
- `_handleRemoveFromDevice` needs: `ProjectLifecycleService.removeFromDevice()`
- `_handleLocalRecord` needs: `DatabaseService` (raw SQLite query by table+id)
- `_handleCreateRecord` needs: Repository access per table (or generic datasource)

**Current DriverServer constructor:** `DriverServer({required testPhotoService, required photoRepository, port})`
Must add: sync orchestrator/engine reference, database service reference

### 2. Debug Server Expansion (Node.js — tools/debug-server/)

| File | Change Type | Purpose |
|------|------------|---------|
| `tools/debug-server/server.js` | MODIFY | Add new route handlers for sync verification, device orchestration |
| `tools/debug-server/lib/supabase-verifier.js` | CREATE | Service-role + per-role Supabase queries |
| `tools/debug-server/lib/device-orchestrator.js` | CREATE | Multi-device command dispatch + ADB airplane mode |
| `tools/debug-server/lib/test-runner.js` | CREATE | Scenario executor + pass/fail reporter |
| `tools/debug-server/lib/scenario-helpers.js` | CREATE | Shared test data naming, FK setup, teardown |
| `tools/debug-server/run-tests.js` | CREATE | CLI entry point |
| `tools/debug-server/scenarios/*.js` | CREATE | 17 table scenario files + 10 cross-cutting |

### 3. Layer 1 Unit Tests (Dart — test/features/sync/)

| File | Change Type | Risk Covered |
|------|------------|-------------|
| `test/features/sync/engine/pull_cursor_safety_test.dart` | CREATE | C1, C2 |
| `test/features/sync/engine/pull_transaction_test.dart` | CREATE | C1 |
| `test/features/sync/engine/cascade_soft_delete_test.dart` | CREATE | C3 |
| `test/features/sync/engine/trigger_suppression_recovery_test.dart` | CREATE | C4 |
| `test/features/sync/engine/conflict_clock_skew_test.dart` | CREATE | H1 |
| `test/features/sync/engine/photo_partial_failure_test.dart` | CREATE | H2 |
| `test/features/sync/engine/tombstone_protection_test.dart` | CREATE | M1 |
| `test/features/sync/engine/change_log_purge_safety_test.dart` | CREATE | M2 |
| `test/features/sync/engine/conflict_resolver_test.dart` | MODIFY | ping-pong circuit breaker |
| `test/features/sync/engine/change_tracker_test.dart` | MODIFY | circuit breaker threshold |
| `test/features/sync/triggers/cascade_delete_trigger_test.dart` | MODIFY | soft-delete cascade |

### 4. Config/Doc Cleanup (non-code)

| File | Change Type |
|------|------------|
| `.claude/test-flows/registry.md` | MODIFY — remove T78-T84, T50, M06; remove Verify-Sync column |
| `.claude/rules/sync/sync-patterns.md` | MODIFY — update testing section |
| `.claude/rules/testing/patrol-testing.md` | MODIFY — update sync testing section |
| `.claude/memory/MEMORY.md` | MODIFY — update test results section |

## Dependent Files (callers/consumers, 2+ levels)

| File | Dependency | Impact |
|------|-----------|--------|
| `lib/main.dart` | Creates DriverServer | Constructor change propagates |
| `lib/features/sync/application/sync_orchestrator.dart` | SyncOrchestrator.syncNow() | Called by new /driver/sync endpoint |
| `lib/features/projects/data/services/project_lifecycle_service.dart` | removeFromDevice() | Called by new /driver/remove-from-device |
| `lib/features/sync/engine/sync_engine.dart` | pushAndPull(), _pull(), _pullTable() | Tested by L1 unit tests |
| `lib/features/sync/engine/conflict_resolver.dart` | ConflictResolver.resolve() | Tested by L1 + L2 |
| `lib/features/sync/engine/change_tracker.dart` | ChangeTracker | Tested by L1 |
| `lib/services/soft_delete_service.dart` | cascadeSoftDeleteProject/Entry | Tested by L1 cascade tests |
| `lib/features/sync/adapters/*.dart` | All 17 adapters | Tested indirectly via L2 |
| `lib/features/sync/config/sync_config.dart` | SyncEngineConfig thresholds | Referenced in L1 tests |

## Test Files That Exercise Affected Code

| File | Exercises |
|------|----------|
| `test/features/sync/engine/sync_engine_test.dart` | SyncEngine integration |
| `test/features/sync/engine/conflict_resolver_test.dart` | ConflictResolver LWW |
| `test/features/sync/engine/change_tracker_test.dart` | ChangeTracker |
| `test/features/sync/triggers/cascade_delete_trigger_test.dart` | CASCADE behavior |
| `test/features/sync/triggers/trigger_behavior_test.dart` | Trigger edge cases |
| `test/features/sync/engine/sync_engine_e2e_test.dart` | E2E sync tests |
| `test/helpers/sync/sqlite_test_helper.dart` | Test DB setup (used by all L1) |

## Key Source Context

### Adapter Registry Order (17 tables in FK order)
```
ProjectAdapter → ProjectAssignmentAdapter → LocationAdapter → ContractorAdapter →
EquipmentAdapter → BidItemAdapter → PersonnelTypeAdapter → DailyEntryAdapter →
PhotoAdapter → EntryEquipmentAdapter → EntryQuantitiesAdapter →
EntryContractorsAdapter → EntryPersonnelCountsAdapter → InspectorFormAdapter →
FormResponseAdapter → TodoItemAdapter → CalculationHistoryAdapter
```

### SyncEngineConfig Values
- pushBatchLimit: 500, maxRetryCount: 5
- pullPageSize: 100, pullSafetyMargin: 5s
- circuitBreakerThreshold: 1000
- conflictPingPongThreshold: 3
- changeLogRetention: 7 days, conflictLogRetention: 7 days

### DriverServer Current Endpoints (port 4948)
- GET /driver/ready, /driver/find, /driver/screenshot, /driver/tree
- POST /driver/tap, /driver/text, /driver/scroll, /driver/scroll-to-key
- POST /driver/back, /driver/wait, /driver/navigate, /driver/hot-restart
- POST /driver/inject-photo, /driver/inject-file, /driver/inject-photo-direct

### Debug Server Current Endpoints (port 3947)
- POST /log, /clear, /sync-status
- GET /logs, /health, /categories, /sync-status

### Existing Test Helper
`SqliteTestHelper.createDatabase()` — in-memory SQLite with full schema v37 + 48 triggers + all indexes.
Helper methods: `suppressTriggers()`, `enableTriggers()`, `clearChangeLog()`, `getChangeLogEntries()`, `getUnprocessedCount()`.

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│ Debug Server (Node.js, port 3947)                            │
│ ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐    │
│ │ Test Runner   │ │ Device Orch. │ │ Supabase Verifier   │    │
│ │ (run-tests.js)│ │              │ │ (service role + JWT)│    │
│ └──────┬───────┘ └──────┬───────┘ └──────────┬──────────┘    │
│        │                │                     │               │
│        └────────────────┼─────────────────────┘               │
│                         │                                     │
│    ┌────────────────────┼───────────────────────┐             │
│    │ Scenario Files     │                       │             │
│    │ (per-table × 5)    ▼                       │             │
│    │              ┌──────────┐                   │             │
│    │              │ ADB Ctrl │ (airplane mode)   │             │
│    │              └──────────┘                   │             │
│    └────────────────────────────────────────────┘             │
└────────────┬─────────────────────────┬───────────────────────┘
             │                         │
     ┌───────▼───────┐       ┌────────▼────────┐
     │ Windows App    │       │ Samsung App      │
     │ Driver :3948   │       │ Driver :3949     │
     │ (admin role)   │       │ (inspector role) │
     │                │       │ (via ADB forward)│
     │ NEW endpoints: │       │ Same endpoints   │
     │ /driver/sync   │       │                  │
     │ /driver/sync-  │       │                  │
     │   status       │       │                  │
     │ /driver/remove-│       │                  │
     │   from-device  │       │                  │
     │ /driver/local- │       │                  │
     │   record       │       │                  │
     │ /driver/create-│       │                  │
     │   record       │       │                  │
     └───────┬───────┘       └────────┬────────┘
             │                         │
             └──────────┬──────────────┘
                        │
               ┌────────▼────────┐
               │ Supabase (cloud)│
               │ 17 synced tables│
               │ Storage buckets │
               └─────────────────┘
```

## Blast Radius Summary

| Category | Count |
|----------|-------|
| Direct files modified | 3 (DriverServer, server.js, test registry) |
| Direct files created | ~35 (8 L1 tests, 27 scenarios, 5 debug-server modules, CLI) |
| Dependent files | 9 |
| Test files affected | 11 (8 new + 3 enhanced) |
| Config/doc cleanup | 4 |
| **Total** | **~62 files** |
