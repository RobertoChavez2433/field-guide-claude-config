# Pattern: Sync Engine

## How We Do It
The sync engine uses a change_log-driven push/pull model. SQLite triggers on 20 tables insert rows into change_log on INSERT/UPDATE/DELETE. ChangeTracker reads unprocessed entries grouped by table. SyncEngine._push() iterates by table in FK dependency order (via SyncRegistry's 22 adapters), pushes each change to Supabase, marks processed. _pull() fetches updated_at-cursored rows from Supabase and upserts locally with ConflictAlgorithm.ignore + rowId==0 fallback. The pulling flag in sync_control suppresses triggers during pull to prevent echo loops.

## Exemplars

### ChangeTracker.getUnprocessedChanges (lib/features/sync/engine/change_tracker.dart:53)
Queries change_log WHERE processed=0 AND retry_count < maxRetryCount, limited to pushBatchLimit. Groups by table_name. Logs anomaly if total exceeds threshold.

### SyncRegistry (lib/features/sync/engine/sync_registry.dart:63)
Singleton with 22 adapters registered in FK dependency order:
Project → ProjectAssignment → Location → Contractor → Equipment → BidItem → PersonnelType → DailyEntry → Photo → EntryEquipment → EntryQuantities → EntryContractors → EntryPersonnelCounts → InspectorForm → FormResponse → FormExport → EntryExport → Document → TodoItem → CalculationHistory → SupportTicket → ConsentRecord

### SyncEngineTables.triggersForTable (lib/core/database/schema/sync_engine_tables.dart:177)
Generates INSERT/UPDATE/DELETE triggers for a table that insert into change_log. 20 tables have triggers (22 adapters minus 2 push-only).

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `SyncEngine.pushAndPull` | sync_engine.dart:214 | `Future<SyncEngineResult> pushAndPull()` | Full sync cycle |
| `SyncEngine.pushOnly` | sync_engine.dart:387 | `Future<SyncEngineResult> pushOnly()` | Push local changes only |
| `SyncEngine.pullOnly` | sync_engine.dart:400 | `Future<SyncEngineResult> pullOnly()` | Pull remote changes only |
| `ChangeTracker.getUnprocessedChanges` | change_tracker.dart:53 | `Future<Map<String, List<ChangeEntry>>> getUnprocessedChanges()` | Read pending push queue |
| `ChangeTracker.markProcessed` | change_tracker.dart:99 | `Future<void> markProcessed(int changeId)` | Mark change as pushed |
| `ChangeTracker.markFailed` | change_tracker.dart:109 | `Future<void> markFailed(int changeId, String errorMessage)` | Mark change as failed |
| `SyncRegistry.adapterFor` | sync_registry.dart:93 | `TableAdapter adapterFor(String tableName)` | Get adapter by table name |
| `SyncRegistry.dependencyOrder` | sync_registry.dart:107 | `List<String> get dependencyOrder` | FK-ordered table list |

## Imports
```dart
import 'package:construction_inspector/features/sync/engine/sync_engine.dart';
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
```

## Lint Rules Targeting This Pattern
- S1: `conflict_algorithm_ignore_guard` — must check rowId==0 after ConflictAlgorithm.ignore
- S2: `change_log_cleanup_requires_success` — no unconditional change_log wipe
- S3: `sync_control_inside_transaction` — pulling flag must be set inside transaction
- S4: `no_sync_status_column` — no sync_status in schema/models (deprecated)
- S5: `tomap_includes_project_id` — synced child models must include project_id
- S8: `sync_time_on_success_only` — _lastSyncTime only updated in success path
