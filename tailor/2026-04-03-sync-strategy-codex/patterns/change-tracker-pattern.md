# Pattern: Change Tracker (Push Source of Truth)

## How We Do It
SQLite triggers auto-populate the `change_log` table on every INSERT, UPDATE, and DELETE to tracked tables. `ChangeTracker` reads unprocessed entries, groups them by table, and provides mark/prune/circuit-breaker operations. The change_log is the SOLE push source of truth — there is no per-record `sync_status` field, no duplicate sync queue, no dirty flag on models. The spec explicitly confirms this pattern should NOT change.

## Exemplars

### ChangeTracker (change_tracker.dart:43-215)
```dart
class ChangeTracker {
  final Database _db;
  ChangeTracker(this._db);

  Future<Map<String, List<ChangeEntry>>> getUnprocessedChanges() async {
    // Check total count for anomaly detection
    // Query with batch limit, excluding retry-exhausted entries
    // Group by table_name, preserving order
  }

  Future<void> markProcessed(int changeId) async { ... }
  Future<void> markFailed(int changeId, String errorMessage) async { ... }
  Future<bool> isCircuitBreakerTripped() async { ... }
  Future<int> getPendingCount() async { ... }
  Future<int> pruneProcessed() async { ... }
  Future<int> purgeOldFailures() async { ... }
  Future<Set<String>> getPendingRecordIds(String table) async { ... }
  Future<bool> hasFailedRecord(String tableName, String recordId) async { ... }
}
```

### ChangeEntry (change_tracker.dart:6-41)
```dart
class ChangeEntry {
  final int id;
  final String tableName;
  final String recordId;
  final String operation;  // 'insert', 'update', 'delete'
  final String changedAt;
  final int processed;     // 0 = pending, 1 = done
  final int retryCount;
  final String? errorMessage;
  final String? projectId;
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `getUnprocessedChanges` | `change_tracker.dart:54` | `Future<Map<String, List<ChangeEntry>>> getUnprocessedChanges()` | Start of push cycle |
| `markProcessed` | `change_tracker.dart:102` | `Future<void> markProcessed(int changeId)` | After successful push |
| `markFailed` | `change_tracker.dart:112` | `Future<void> markFailed(int changeId, String errorMessage)` | After push error |
| `isCircuitBreakerTripped` | `change_tracker.dart:160` | `Future<bool> isCircuitBreakerTripped()` | Pre-push safety check |
| `getPendingCount` | `change_tracker.dart:175` | `Future<int> getPendingCount()` | UI pending display |
| `pruneProcessed` | `change_tracker.dart:141` | `Future<int> pruneProcessed()` | Post-sync cleanup |
| `purgeOldFailures` | `change_tracker.dart:189` | `Future<int> purgeOldFailures()` | Circuit breaker recovery |
| `insertManualChange` | `change_tracker.dart:127` | `Future<void> insertManualChange(String, String, String)` | Conflict resolution re-push |
| `hasFailedRecord` | `change_tracker.dart:206` | `Future<bool> hasFailedRecord(String tableName, String recordId)` | Per-record FK blocking |

## Imports
```dart
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
```

## Gap Analysis for Spec

**Change tracker is preserved as-is**: The spec explicitly states "The existing `change_log` pattern remains the authoritative local push mechanism. No per-record `sync_status` rollback. No duplicate sync queue." This pattern is stable.

**Quick sync push is already fast**: `getUnprocessedChanges()` returns only unprocessed entries, limited to 500. A quick sync that only pushes is already efficient.

**change_log has project_id**: Column was added in migration v38. This enables per-project change detection — useful for dirty scope tracking.
