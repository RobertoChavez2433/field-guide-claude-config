# Sync Verification Fixes — Context Bundle

> Gathered by 2 Opus exploration agents. Feed to plan writer.

## TODO List (16 items)

### CRITICAL
1. Create 8 spec-named L1 test files (C1-C4, H1-H2, M1-M2)
2. Add 3 spec-required enhancements to existing test files
3. Fix fk_ordering_test and adapter_registry_test to test real code
4. Fix TestRunner L3 dual-device context

### HIGH
5. S4 conflict scenarios — add local-wins reverse direction
6. X3 — admin edit should use device UI, not server-side bypass
7. X4 — verify child record cascade on Supabase
8. Add --clean CLI flag to run-tests.js
9. Add retry/skip logic to TestRunner

### MEDIUM
10. step() error handling — throw instead of swallow
11. cleanup() should soft-delete, not hard-delete
12. X7 — add Storage file upload verification
13. X10 — expand FK chain depth to 7 tables
14. X6 — strengthen convergence check + conflict_log
15. Add report persistence to file
16. Add request timeout to SupabaseVerifier

---

# PART A: Dart/Flutter Context (Tasks 1-3)

## CRITICAL-1: 8 New Test Files

### Risk C1/C2 — Pull Cursor Safety (`pull_cursor_safety_test.dart`)

**Production code:**
- `lib/features/sync/engine/sync_engine.dart:1262-1445` — `_pullTable()` method
  - Cursor read: lines 1264-1271, reads from `sync_metadata` table key `last_pull_{tableName}`
  - Cursor advance: lines 1436-1442, writes `maxUpdatedAt` to `sync_metadata` only after full page processing
  - `maxUpdatedAt` tracked at line 1416-1420
  - FK-skipped records: line 1354-1360 — `DatabaseException` containing `FOREIGN KEY` increments `_pullSkippedFkCount` and `continue`s

**Key finding:** The `continue` at line 1359 skips `maxUpdatedAt` tracking for FK-skipped records. Cursor only advances past successfully processed records. The `maxUpdatedAt` tracking at lines 1416-1420 is at same indentation as if/else, meaning it runs for EVERY record — INCLUDING FK-skipped ones. This IS the C1/C2 bug.

**What to test:** Cursor only advances past successfully processed records. FK-skipped records do NOT advance cursor. Page failure prevents cursor advance.

### Risk C1 — Pull Transaction Atomicity (`pull_transaction_test.dart`)

**Production code:**
- `sync_engine.dart:1262-1445` — `_pullTable()` processes records one-by-one, NOT in a transaction
- No transaction wrapping around page processing loop (lines 1277-1427)
- Partial page failure: records 1-49 inserted, cursor advances to record 49's updated_at

**What to test:** Pull batch atomicity. Partial page failure should not advance cursor. This test should EXPOSE the risk.

### Risk C3 — Cascade Soft Delete (`cascade_soft_delete_test.dart`)

**Production code:**
- `lib/services/soft_delete_service.dart:1-484` — `SoftDeleteService`
  - `cascadeSoftDeleteProject()`: lines 50-149
    - `_projectChildTables`: locations, contractors, daily_entries, bid_items, personnel_types, photos, form_responses, todo_items, calculation_history (9 tables)
    - Equipment via contractor subquery: lines 74-82
    - Entry junction tables: entry_contractors, entry_equipment, entry_personnel_counts, entry_quantities (4 tables, lines 85-101)
    - Project itself: lines 104-114
    - change_log/conflict_log cleanup: lines 119-136
    - synced_projects removal: lines 141-146
  - `_childToParentOrder`: 15 tables (lines 15-31)

**What to test:** Soft-deleting project marks all children deleted across 15 child tables via SoftDeleteService.

**Test approach:** Create full FK graph via `SyncTestData.seedFkGraph()`, add entry junctions, call `cascadeSoftDeleteProject()`, verify `deleted_at` on ALL 15 tables.

### Risk C4 — Trigger Suppression Recovery (`trigger_suppression_recovery_test.dart`)

**Production code:**
- `sync_engine.dart:203-216` — `pushAndPull()` entry: line 214 unconditionally resets `sync_control.pulling='0'`
- Triggers: all 48 check `WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'`
- Pull sets pulling='1' at line 1167-1169, resets in finally at lines 1248-1250

**What to test:** Stuck pulling='1' is reset by next pushAndPull(). Post-recovery edits generate change_log entries. Can test at SQLite level.

### Risk H1 — Conflict Clock Skew (`conflict_clock_skew_test.dart`)

**Production code:**
- `lib/features/sync/engine/conflict_resolver.dart:27-90` — `resolve()` method
  - LWW: `remoteUpdatedAt.compareTo(localUpdatedAt) >= 0` (line 50) — lexicographic string comparison
  - No clock skew normalization

**What to test:** LWW with timestamps offset by 1s, 5m, 1h. Near-simultaneous timestamps.

### Risk H2 — Photo Partial Failure (`photo_partial_failure_test.dart`)

**Production code:**
- `sync_engine.dart:868-972` — `_pushPhotoThreePhase()`
  - Phase 1: Upload file (880-917)
  - Phase 2: Upsert metadata (921-945), on failure: cleanup uploaded file (933-944)
  - Phase 3: Mark local synced (947-971) with trigger suppression
  - Idempotency: existing remotePath skips Phase 1 (line 880)
  - StorageException 409: treated as success (908-914)

**What to test:** Phase 1+2 failure -> cleanup. Phase 1+2+3 failure -> safe idempotent re-push.

### Risk M1 — Tombstone Protection (`tombstone_protection_test.dart`)

**Production code:**
- `sync_engine.dart:1322-1335` — Pull tombstone check: queries change_log for unprocessed delete entry, skips insert if found

**What to test:** Local soft-delete not overridden by remote edit when tombstone in change_log.

### Risk M2 — Change Log Purge Safety (`change_log_purge_safety_test.dart`)

**Production code:**
- `lib/features/sync/engine/change_tracker.dart:131-176`
  - `pruneProcessed()`: lines 134-141 — deletes processed entries > 7 days
  - `purgeOldFailures()`: lines 165-176 — deletes unprocessed with retry_count >= 5 AND > 7 days
- Config: `maxRetryCount=5`, `changeLogRetention=7 days`

**Note:** `change_tracker_purge_test.dart` already covers M2 well. New file should add edge cases (exact boundary, entries at 7-day mark, retry_count exactly 5 vs 4).

---

## CRITICAL-2: 3 Enhancements

### conflict_resolver_test.dart — Ping-Pong Circuit Breaker

**Current file:** 454 lines, tests LWW, conflict logging, null timestamps, ping-pong basics, pruneExpired
**Production code:** `sync_engine.dart:1399-1411` — circuit breaker checks `getConflictCount >= conflictPingPongThreshold` (3), skips re-push
**What to add:** Test that 3+ consecutive local-wins suppresses `insertManualChange()` (stops re-push)
**Existing separate file:** `conflict_resolver_pingpong_test.dart` (55 lines) tests getConflictCount and threshold detection

### change_tracker_test.dart — Auto-Purge Then Circuit Breaker

**Current file:** 400 lines, tests getUnprocessedChanges, markProcessed/Failed, circuit breaker basics
**Production code:** `sync_engine.dart:392-409` — push flow: if tripped, purge, re-check, if still tripped → blocked
**What to add:** Auto-purge-then-recheck flow (>1000 pending → purge old failures → recheck)
**Existing separate file:** `change_tracker_circuit_breaker_test.dart` (66 lines) tests below/at/above threshold

### cascade_delete_trigger_test.dart — NEW file

Test `SoftDeleteService.cascadeSoftDeleteProject()` and `cascadeSoftDeleteEntry()` with full FK graph.

---

## CRITICAL-3: Fix Hardcoded Tests

### fk_ordering_test.dart
- **Current:** Tests hardcoded `_tableInsertOrder` (lines 5-23), no production imports
- **Real code:** `lib/features/sync/engine/sync_registry.dart:24-44` — `registerSyncAdapters()`, `SyncRegistry.dependencyOrder` getter
- **Fix:** Import `sync_registry.dart`, call `registerSyncAdapters()`, test `SyncRegistry.instance.dependencyOrder`

### adapter_registry_test.dart
- **Current:** Tests hardcoded `expectedTables` (lines 7-13), no production imports
- **Real code:** Same `sync_registry.dart` — `SyncRegistry.instance.adapters` after registration
- **Fix:** Import `sync_registry.dart`, test `.adapters.length == 17`, verify table names, verify project_assignments pull-only

---

## Shared Dart Context

### Test Helper API (`test/helpers/sync/sqlite_test_helper.dart`)
- `createDatabase()` → in-memory SQLite with full schema + triggers (version 37)
- `suppressTriggers(db)` → sets pulling='1'
- `enableTriggers(db)` → sets pulling='0'
- `clearChangeLog(db)` → deletes all change_log rows
- `getChangeLogEntries(db, tableName)` → unprocessed entries for table
- `getUnprocessedCount(db)` → total unprocessed count

### Test Data API (`test/helpers/sync/sync_test_data.dart`)
- `projectMap()`, `locationMap()`, `contractorMap()`, `equipmentMap()`, `bidItemMap()`, `personnelTypeMap()`, `dailyEntryMap()`, `photoMap()`, `entryEquipmentMap()`, `entryQuantityMap()`, `entryContractorMap()`, `entryPersonnelCountMap()`, `inspectorFormMap()`, `formResponseMap()`, `todoItemMap()`, `calculationHistoryMap()`
- `seedFkGraph(db)` → seeds company→project→location→entry→contractor→equipment→bid_item→personnel_type, returns ID map

### DB Schema FK Tree
```
projects (root)
├── project_assignments (pull-only, no triggers)
├── locations (FK: project_id ON DELETE CASCADE)
├── contractors (FK: project_id ON DELETE CASCADE)
│   ├── equipment (FK: contractor_id ON DELETE CASCADE)
│   └── personnel_types (FK: project_id + contractor_id)
├── bid_items (FK: project_id ON DELETE CASCADE)
├── daily_entries (FK: project_id + location_id ON DELETE CASCADE)
│   ├── photos (FK: entry_id + project_id)
│   ├── entry_equipment (FK: entry_id + equipment_id)
│   ├── entry_quantities (FK: entry_id + bid_item_id)
│   ├── entry_contractors (FK: entry_id + contractor_id)
│   └── entry_personnel_counts (FK: entry_id + contractor_id + type_id)
├── inspector_forms (FK: project_id)
│   └── form_responses (FK: form_id + entry_id + project_id)
├── todo_items (FK: project_id)
└── calculation_history (FK: project_id)
```

16 triggered tables. project_assignments is pull-only (no triggers).

### Sync Config Constants
- pushBatchLimit=500, pushAnomalyThreshold=1000, maxRetryCount=5
- pullPageSize=100, pullSafetyMargin=5s, changeLogRetention=7d
- conflictLogRetention=7d, circuitBreakerThreshold=1000, conflictPingPongThreshold=3

### Common Imports Pattern
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../../../helpers/sync/sync_test_helpers.dart'; // barrel export
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';
import 'package:construction_inspector/features/sync/engine/conflict_resolver.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/services/soft_delete_service.dart';
```

### setUp/tearDown Pattern
```dart
late Database db;
setUpAll(() { sqfliteFfiInit(); });
setUp(() async { db = await SqliteTestHelper.createDatabase(); });
tearDown(() async { await db.close(); });
```

---

# PART B: JS/Node Context (Tasks 4-16)

## CRITICAL-4: TestRunner L3 Dual-Device Fix

**Current run() (test-runner.js:92-115):**
```javascript
const context = { verifier: this.verifier, device: this.device };
await scenarioModule.run(context);
```
Only ONE DeviceOrchestrator created (port 4948).

**L3 destructuring pattern (all 10 files):**
```javascript
async function run({ verifier, adminDevice, inspectorDevice }) {
```

**DeviceOrchestrator constructor:** `constructor(host='localhost', port=4948)`

**Ports:** DriverServer Dart defaults to 4948. Use 4948 (admin) and 4949 (inspector).

**Fix:**
1. Detect L3 via `scenario.layer === 'L3'`
2. Create two DeviceOrchestrators: adminDevice (4948), inspectorDevice (4949)
3. L3 context: `{ verifier, adminDevice, inspectorDevice }`
4. L2 context: `{ verifier, device: this.adminDevice }` (backward compat)
5. Add `--admin-port` and `--inspector-port` CLI flags

**Files:** test-runner.js, run-tests.js

## HIGH-1: S4 Local-Wins Reverse Direction

**Current pattern:** All S4 files create local edit, then remote with future timestamp (+5000ms), so remote always wins LWW.

**Fix:** Add second phase: local edit with timestamp +10000ms (newer), remote with -5000ms (older), sync, verify local wins, verify conflict_log, verify local re-pushed to Supabase.

**All 17 S4 files:**
```
projects-S4-conflict.js, locations-S4-conflict.js, bid-items-S4-conflict.js,
calculation-history-S4-conflict.js, contractors-S4-conflict.js, daily-entries-S4-conflict.js,
entry-contractors-S4-conflict.js, entry-equipment-S4-conflict.js,
entry-personnel-counts-S4-conflict.js, entry-quantities-S4-conflict.js,
equipment-S4-conflict.js, form-responses-S4-conflict.js, inspector-forms-S4-conflict.js,
personnel-types-S4-conflict.js, photos-S4-conflict.js, todo-items-S4-conflict.js,
project-assignments-S4-conflict.js
```

## HIGH-2: X3 Admin Device Edit

**Current:** Admin uses `verifier.updateRecord()` (server-side bypass)
**Fix:** Use `adminDevice.navigate()` + `adminDevice.enterText()` + `adminDevice.tap()` matching inspector pattern
**File:** X3-simultaneous-edit-conflict.js

## HIGH-3: X4 Child Cascade Verification

**Current:** Only verifies project `deleted_at` on Supabase
**Fix:** Add step verifying child tables (locations, daily_entries, todo_items) have `deleted_at` set on Supabase
**File:** X4-admin-deletes-inspector-cascades.js

## HIGH-4: --clean CLI Flag

**Current flags:** --layer, --table, --filter, --dry-run, --device-host, --device-port, --help
**Fix:** Add `--clean` that uses SupabaseVerifier to hard-delete all SYNCTEST-* records in children-first FK order
**Files:** run-tests.js, supabase-verifier.js (add queryByPrefix/bulkDelete)

## HIGH-5: Retry/Skip Logic

**Fix:**
1. 3x retry with 5s backoff around scenarioModule.run()
2. S1 skip logic: track results by table, skip S2-S5 if S1 failed
3. Supabase preflight: callRpc('get_server_time') before running
4. Add `skipped` count to summary
**File:** test-runner.js

## MEDIUM-1: step() Error Handling

**Current:** Returns `{status:'fail'}`, no callers check return
**Fix:** Re-throw error after logging instead of returning fail status
**File:** scenario-helpers.js

## MEDIUM-2: cleanup() Soft-Delete

**Current:** Calls `verifier.deleteRecord()` (hard DELETE)
**Fix:** Add `softDeleteRecord()` to SupabaseVerifier (PATCH deleted_at). Change cleanup() to use it. Keep deleteRecord() for --clean.
**Files:** supabase-verifier.js, scenario-helpers.js

## MEDIUM-3: X7 Storage Verification

**Bucket:** `entry-photos` (from photo_remote_datasource.dart:9)
**Fix:** Add `verifyStorageObject(bucket, path)` to SupabaseVerifier. Add steps to X7 verifying Storage file + local remote_path.
**Files:** supabase-verifier.js, X7-photo-offline-sync.js

## MEDIUM-4: X10 FK Chain Depth

**Current:** 4 levels (project, location, entry, todo)
**Spec:** 7 tables (project + location + contractor + entry + photo + quantities + equipment)
**File:** X10-fk-ordering-under-load.js

## MEDIUM-5: X6 Convergence

**Fix:** Verify BOTH devices converge to same state. Verify conflict_log entry exists.
**File:** X6-offline-conflict-cross-device.js

## MEDIUM-6: Report Persistence

**Fix:** Add `_saveReport(summary)` to TestRunner. Write to `tools/debug-server/reports/sync-verify-{timestamp}.txt`. Add .gitignore entry.
**File:** test-runner.js

## MEDIUM-7: SupabaseVerifier Timeout

**Fix:** Add `req.setTimeout(30000, ...)` to `_request()` matching DeviceOrchestrator pattern.
**File:** supabase-verifier.js

---

## Shared JS Context

### DeviceOrchestrator API
constructor(host, port), isReady(), waitForReady(), triggerSync(), getLocalRecord(table, id), getChangeLog(table), createRecord(table, record), getSyncStatus(), navigate(route), tap(key), enterText(key, text), find(key), _request(method, path, body) [60s timeout]

### SupabaseVerifier API
constructor(url, key), getRecord(table, id), queryRecords(table, filters), verifyRecord(table, id, expected), verifyRecordDeleted(table, id), deleteRecord(table, id) [hard], insertRecord(table, record), updateRecord(table, id, updates), callRpc(fn, params), authenticateAs(role), resetAuth(), _request(method, endpoint, body) [NO timeout]

### ScenarioHelpers API
uuid(), testPrefix(scenario, table), sleep(ms), verify(condition, msg), assertEqual(actual, expected), waitFor(checkFn, desc, timeout, interval), step(name, fn) [swallows errors], cleanup(verifier, records) [hard delete], makeProject(), makeDailyEntry(), makeLocation(), makeContractor(), makeEquipment(), makePersonnelType(), makeBidItem(), makeInspectorForm(), makeFormResponse()

### DriverServer endpoints (Dart)
ready, find, screenshot, tree, tap, text, scroll, scroll-to-key, back, wait, inject-photo, inject-file, inject-photo-direct, navigate, hot-restart, sync, local-record, change-log, create-record, sync-status, remove-from-device

**NOTE:** No `/driver/update-record` endpoint exists. S4 scenarios use `device._request('POST', '/driver/update-record', ...)` which will 404. This may be a pre-existing issue.
