# Dependency Graph: Sync Test Redesign + Hard-Delete Fix

## Direct Changes

### Dart (Sync Engine Fixes)

| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/features/sync/engine/sync_engine.dart` | `_pushDelete` | 547-633 | MODIFY — remove StateError throw at 600-605, replace with Logger.sync + return |
| `lib/features/sync/engine/sync_engine.dart` | `pushAndPull` | 203-330 | MODIFY — add `purgeOrphans()` call in integrity check block (~line 290) |
| `lib/features/sync/engine/integrity_checker.dart` | `IntegrityChecker` | 43-263 | MODIFY — add `purgeOrphans()` method |
| `lib/features/sync/application/sync_orchestrator.dart` | `_isTransientError` | 414-462 | MODIFY — add nonTransientPatterns, flip default to false |

### JavaScript (Test Infrastructure)

| File | Symbol | Change Type |
|------|--------|-------------|
| `tools/debug-server/scenario-helpers.js` | entire file | MODIFY — add TestContext class, 8 new make*() factories, 5 common helpers, fix existing factories |
| `tools/debug-server/run-tests.js` | `TestRunner` | MODIFY — add setupSharedFixture(), teardownSharedFixture(), SYNCTEST-* sweep, --cleanup-only/--keep-fixture flags, pass ctx to scenarios |
| `tools/debug-server/supabase-verifier.js` | `SupabaseVerifier` | MODIFY — add hardDelete() method for teardown |
| `tools/debug-server/scenarios/L2/*.js` | 84 files | REWRITE — all scenarios receive ctx, use shared fixture, soft-delete own records |
| `tools/debug-server/scenarios/L3/*.js` | 10 files | REWRITE — receive ctx, use shared fixture |

### Widget Keys (if missing)

| File | Keys to Verify |
|------|---------------|
| `lib/shared/testing_keys/projects_keys.dart` | `projectCreateButton`, `projectNameField`, `projectNumberField`, `projectSaveButton` |
| `lib/shared/testing_keys/entries_keys.dart` | Entry creation form keys (date, location, save) |
| `lib/shared/testing_keys/toolbox_keys.dart` | `todosAddButton`, `todosTitleField`, `todosSaveButton`, `calculatorSaveButton` |

## Dependent Files (Callers — 2+ levels)

| File | Why Affected |
|------|-------------|
| `lib/features/sync/application/sync_orchestrator.dart` | Calls `_syncWithRetry` → `_doSync` → `engine.pushAndPull()` → `_push()` → `_pushDelete()` |
| `lib/features/sync/engine/change_tracker.dart` | `markProcessed()` / `markFailed()` called from `_pushDelete()` flow |
| `lib/features/sync/engine/sync_engine.dart::_push` | Catches errors from `_routeAndPush` → `_pushDelete` |
| `lib/features/sync/engine/sync_engine.dart::_handlePushError` | Handles errors thrown by `_pushDelete` — StateError path changes |
| `test/features/sync/engine/integrity_checker_test.dart` | Existing tests for IntegrityChecker — new `purgeOrphans()` needs tests |

## Test Files

| File | Purpose |
|------|---------|
| `test/features/sync/engine/integrity_checker_test.dart` | Existing — add purgeOrphans() tests |
| `test/features/sync/engine/sync_engine_test.dart` | Existing — add _pushDelete empty response test |
| `test/features/sync/application/sync_orchestrator_test.dart` | Existing — add _isTransientError new patterns test |

## Data Flow

```
App UI → Provider → Repository → SQLite (local)
                                    ↓
                              change_log trigger
                                    ↓
                          SyncEngine._push()
                                    ↓
                    _routeAndPush() → _pushDelete()
                                    ↓
                    Supabase .update().eq('id', ...)
                                    ↓
                  response.isEmpty? ──→ [FIX A] Log + return (was: throw StateError)
                                    ↓
                    _handlePushError catches → markFailed
                                    ↓
                    SyncEngineResult(errors: N)
                                    ↓
                    SyncOrchestrator._syncWithRetry()
                                    ↓
                    _isTransientError() ──→ [FIX C] nonTransient patterns + default false
                                    ↓
                    Retry loop / background timer / error status
```

```
IntegrityChecker.run() (4-hour schedule)
    ↓
[FIX B] purgeOrphans() — NEW
    ├── For each table (parents first):
    │   ├── SELECT id FROM local WHERE deleted_at IS NULL
    │   ├── Filter: only synced projects, skip pending change_log
    │   ├── SELECT id FROM supabase WHERE id IN (batch)
    │   └── Diff: local - server = orphans → local soft-delete (pulling=1)
    └── Return orphan count
```

## 17 Synced Tables (FK Dependency Order)

From `registerSyncAdapters()` in `sync_registry.dart:24-44`:

```
1.  projects
2.  project_assignments
3.  locations
4.  contractors
5.  equipment
6.  bid_items
7.  personnel_types
8.  daily_entries
9.  photos
10. entry_equipment
11. entry_quantities
12. entry_contractors
13. entry_personnel_counts
14. inspector_forms
15. form_responses
16. todo_items
17. calculation_history
```

## Blast Radius Summary

| Category | Count |
|----------|-------|
| Direct Dart changes | 4 files, 4 symbols |
| Direct JS changes | 3 infra files + 94 scenario files |
| Widget key files | 3 files (verify + fix if missing) |
| Dependent Dart files | 5 files |
| Test files to update | 3 existing test files |
| New test coverage | purgeOrphans unit tests, _pushDelete empty response test, _isTransientError pattern tests |

## Key Source Excerpts

### _pushDelete — The Bug (sync_engine.dart:600-605)

```dart
// BUG-C: 0 rows affected — record doesn't exist on server
if (response.isEmpty) {
  throw StateError(
    'Soft-delete push failed: ${adapter.tableName}/${change.recordId} '
    '— remote record not found (0 rows affected)',
  );
}
```

### _isTransientError — The Default Branch (sync_orchestrator.dart:456-461)

```dart
// Default: treat unknown errors as transient (safer to retry)
return true;
```

Current nonTransientPatterns:
```dart
final nonTransientPatterns = [
  'auth', 'Auth', 'RLS', 'permission', 'Permission',
  'not configured', 'already in progress', 'has no column',
  'DatabaseException', 'no such column', 'table has no column',
];
```

### IntegrityChecker.run() — Where purgeOrphans() Goes (pushAndPull:283-304)

```dart
// Integrity check (4-hour schedule, catch errors -- don't fail sync)
if (await _integrityChecker.shouldRun()) {
  try {
    final integrityResults = await _integrityChecker.run();
    for (final result in integrityResults) {
      await _storeIntegrityResult(result);
      if (result.driftDetected) {
        await _clearCursor(result.tableName);
      }
    }
    // Run orphan scanner as part of integrity cycle.
    final orphans = await _orphanScanner.scan(companyId, autoDelete: true);
    // ... FIX B: Add purgeOrphans() call here
  } catch (e) {
    Logger.error('Integrity check failed', error: e);
  }
}
```

### IntegrityChecker Constructor (integrity_checker.dart:43-48)

```dart
class IntegrityChecker {
  final Database _db;
  final SupabaseClient _supabase;
  IntegrityChecker(this._db, this._supabase);
```

Already has both `_db` and `_supabase` — perfect for purgeOrphans() which needs both.

### SyncEngine Constructor (sync_engine.dart:153)

```dart
_integrityChecker = IntegrityChecker(db, supabase);
```

### Registered Adapters FK Order (sync_registry.dart:24-44)

```dart
void registerSyncAdapters() {
  SyncRegistry.instance.registerAdapters([
    ProjectAdapter(),
    ProjectAssignmentAdapter(),
    LocationAdapter(),
    ContractorAdapter(),
    EquipmentAdapter(),
    BidItemAdapter(),
    PersonnelTypeAdapter(),
    DailyEntryAdapter(),
    PhotoAdapter(),
    EntryEquipmentAdapter(),
    EntryQuantitiesAdapter(),
    EntryContractorsAdapter(),
    EntryPersonnelCountsAdapter(),
    InspectorFormAdapter(),
    FormResponseAdapter(),
    TodoItemAdapter(),
    CalculationHistoryAdapter(),
  ]);
}
```

### Widget Keys Verified (projects_keys.dart, toolbox_keys.dart)

**Project creation S1:**
- `projectCreateButton` — exists
- `projectNameField` — exists
- `projectNumberField` — exists
- `projectSaveButton` — exists

**Todo creation S1:**
- `todosAddButton` — exists
- `todosTitleField` — exists
- `todosSaveButton` — exists

**Calculator S1:**
- `calculatorSaveButton` — exists
- `calculatorHmaArea`, `calculatorHmaThickness`, `calculatorHmaDensity` — exist
- `calculatorCalculateButton` — exists

**Entries S1:**
- Need to verify `EntriesTestingKeys` (file too large for search, will need direct read)
