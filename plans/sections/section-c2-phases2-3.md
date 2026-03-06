# Section C2: Phases 2 & 3 -- Implementation Plan

**Source Plan**: `.claude/plans/2026-03-04-sync-rewrite-and-settings-redesign.md` (lines 1433-1527)
**Architecture Reference**: `.claude/plans/sections/section-a-architecture.md` (Steps 9-16)
**Analysis**: Verified against codebase by analysis agent
**Current DB Version**: 29 (at `lib/core/database/database_service.dart:54`)

**PREREQUISITE**: Phase 1 (Section A -- architecture, schema, migration, adapters) must be complete and all integration tests passing before Phase 2 begins. The 5 engine tables (`sync_control`, `change_log`, `conflict_log`, `sync_lock`, `synced_projects`), all 16 triggers, the `TableAdapter` base class, all 16 concrete adapters, `SyncRegistry`, `SyncConfig`, `ScopeType`, and all 4 `TypeConverter` implementations must be in place.

---

## Step 1: Phase 2 -- Sync Engine Core

Phase 2 builds the runtime engine classes that read/write the infrastructure tables from Phase 1. No table adapters are connected yet -- mock adapters are used in tests.

### 1.1 SyncMutex

**File**: `lib/features/sync/engine/sync_mutex.dart`
**Action**: Create
**Depends on**: Phase 1 (sync_lock table exists)

The SyncMutex provides a cross-isolate lock using the `sync_lock` SQLite table. It guarantees only one sync process (foreground or background WorkManager isolate) runs at a time.

#### 1.1.1 Class definition

```dart
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';

/// SQLite advisory lock for cross-isolate sync mutex.
///
/// Uses the sync_lock table (single-row, id=1) to ensure only one
/// sync process runs at a time, even across foreground and background isolates.
///
/// The lock has a stale timeout (5 minutes by default) to recover from crashes.
class SyncMutex {
  final Database _db;

  SyncMutex(this._db);

  /// Try to acquire the lock. Returns true if successful.
  ///
  /// Steps:
  /// 1. Expire stale locks older than [SyncEngineConfig.staleLockTimeout]
  /// 2. INSERT the lock row. If row already exists (another process holds it),
  ///    the INSERT fails and we return false.
  Future<bool> tryAcquire(String lockedBy) async {
    // Expire stale locks (crash recovery)
    final timeoutMinutes = SyncEngineConfig.staleLockTimeout.inMinutes;
    await _db.execute(
      "DELETE FROM sync_lock WHERE locked_at < strftime('%Y-%m-%dT%H:%M:%f', 'now', '-$timeoutMinutes minutes')",
    );

    try {
      await _db.execute(
        "INSERT INTO sync_lock (id, locked_at, locked_by) VALUES (1, strftime('%Y-%m-%dT%H:%M:%f', 'now'), ?)",
        [lockedBy],
      );
      return true;
    } catch (_) {
      // Row already exists -- another process holds the lock
      return false;
    }
  }

  /// Release the lock.
  Future<void> release() async {
    await _db.execute('DELETE FROM sync_lock WHERE id = 1');
  }

  /// Force-clear all locks. Called on app startup and in SyncEngine constructor.
  Future<void> forceReset() async {
    await _db.execute('DELETE FROM sync_lock');
  }
}
```

#### 1.1.2 Key behaviors

- **Constructor**: Takes a single `Database` parameter.
- **`tryAcquire(String lockedBy)`**: The `lockedBy` parameter is either `'foreground'` or `'background'`. Stale lock expiry uses `SyncEngineConfig.staleLockTimeout` (5 minutes). The INSERT into the single-row table (CHECK constraint `id = 1`) fails if another lock is held, returning `false`.
- **`release()`**: Deletes the lock row unconditionally.
- **`forceReset()`**: Deletes ALL rows from sync_lock. Called on app startup and in the `SyncEngine` constructor to recover from any prior crash.
- **Non-reentrancy**: The sync_lock table enforces `id = 1` uniqueness. The engine adds a debug-mode assertion (`_insidePushOrPull`) as a secondary guard.

---

### 1.2 ChangeTracker

**File**: `lib/features/sync/engine/change_tracker.dart`
**Action**: Create
**Depends on**: Phase 1 (change_log table exists)

The ChangeTracker reads trigger-populated `change_log` entries, groups them by table for the push flow, and provides mark/prune operations.

#### 1.2.1 ChangeEntry data class

```dart
/// A single change_log entry.
class ChangeEntry {
  final int id;
  final String tableName;
  final String recordId;
  final String operation; // 'insert', 'update', 'delete'
  final String changedAt;
  final int retryCount;
  final String? errorMessage;
  final String? metadata;

  ChangeEntry({
    required this.id,
    required this.tableName,
    required this.recordId,
    required this.operation,
    required this.changedAt,
    required this.retryCount,
    this.errorMessage,
    this.metadata,
  });

  factory ChangeEntry.fromMap(Map<String, dynamic> map) {
    return ChangeEntry(
      id: map['id'] as int,
      tableName: map['table_name'] as String,
      recordId: map['record_id'] as String,
      operation: map['operation'] as String,
      changedAt: map['changed_at'] as String,
      retryCount: map['retry_count'] as int,
      errorMessage: map['error_message'] as String?,
      metadata: map['metadata'] as String?,
    );
  }
}
```

#### 1.2.2 ChangeTracker class definition

```dart
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/core/logging/debug_logger.dart';

class ChangeTracker {
  final Database _db;

  ChangeTracker(this._db);
```

#### 1.2.3 Methods

**`getUnprocessedChanges()`** -- returns `Future<Map<String, List<ChangeEntry>>>`

1. Query total unprocessed count: `SELECT COUNT(*) as cnt FROM change_log WHERE processed = 0`
2. If count > `SyncEngineConfig.pushAnomalyThreshold` (1000), log anomaly via `DebugLogger.sync()`
3. Query entries: `SELECT * FROM change_log WHERE processed = 0 ORDER BY changed_at ASC LIMIT {pushBatchLimit}` (limit = 500)
4. Group results by `table_name`, preserving order within each group
5. Return the grouped map

**`hasFailedEntries(String tableName)`** -- returns `Future<bool>`

Query: `SELECT COUNT(*) as cnt FROM change_log WHERE processed = 0 AND table_name = ? AND retry_count >= {maxRetryCount}`
Returns true if count > 0. Used by the FK dependency pre-check in push flow.

**`markProcessed(int changeId)`** -- returns `Future<void>`

Update: `UPDATE change_log SET processed = 1 WHERE id = ?`

**`markFailed(int changeId, String errorMessage)`** -- returns `Future<void>`

Update: `UPDATE change_log SET error_message = ?, retry_count = retry_count + 1 WHERE id = ?`

**`insertManualChange(String tableName, String recordId, String operation)`** -- returns `Future<void>`

Insert: `INSERT INTO change_log (table_name, record_id, operation) VALUES (?, ?, ?)`
Used when local wins a conflict during pull (bypasses suppressed triggers). This is the ONE exception to the rule that only triggers populate change_log.

**`pruneProcessed()`** -- returns `Future<int>`

Delete: `DELETE FROM change_log WHERE processed = 1 AND changed_at < strftime('%Y-%m-%dT%H:%M:%f', 'now', '-{changeLogRetention.inDays} days')`
Returns the number of deleted rows. Called after each successful sync cycle.

---

### 1.3 ConflictResolver

**File**: `lib/features/sync/engine/conflict_resolver.dart`
**Action**: Create
**Depends on**: Phase 1 (conflict_log table exists)

The ConflictResolver implements Last-Write-Wins (LWW) comparison and logs conflicts with changed-columns-only diffs to minimize PII exposure.

#### 1.3.1 ConflictWinner enum

```dart
enum ConflictWinner { local, remote }
```

#### 1.3.2 Class definition

```dart
import 'dart:convert';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';

class ConflictResolver {
  final Database _db;

  ConflictResolver(this._db);
```

#### 1.3.3 `resolve()` method

Signature: `Future<ConflictWinner> resolve({required String tableName, required String recordId, required Map<String, dynamic> local, required Map<String, dynamic> remote})`

**LWW comparison rules:**
1. Extract `local['updated_at']` and `remote['updated_at']` as `String?`
2. MUST compare the **server-assigned** `updated_at` from the pulled record, never the local client's outbound `updated_at`
3. If either timestamp is null: **remote wins** (safety default)
4. If `remoteUpdatedAt.compareTo(localUpdatedAt) >= 0`: **remote wins** (equal timestamps = remote wins as deterministic tiebreaker)
5. If local `updated_at` is strictly newer: **local wins**

**Conflict logging:**
1. Determine loser: if remote wins, loser = local; if local wins, loser = remote
2. Compute diff using `_computeLostData(winnerData, loserData)` -- only changed columns, always includes `id`
3. Set `detected_at` = `DateTime.now().toUtc().toIso8601String()`
4. Set `expires_at` = `detected_at + SyncEngineConfig.conflictLogRetention` (7 days)
5. Insert into `conflict_log`: `table_name`, `record_id`, `winner` ('local' or 'remote'), `lost_data` (JSON-encoded diff), `detected_at`, `expires_at`

#### 1.3.4 `_computeLostData()` method

```dart
Map<String, dynamic> _computeLostData(
  Map<String, dynamic> winner,
  Map<String, dynamic> loser,
) {
  final diff = <String, dynamic>{'id': loser['id']};
  for (final key in loser.keys) {
    if (loser[key] != winner[key]) {
      diff[key] = loser[key];
    }
  }
  return diff;
}
```

This stores only the columns that differ between winner and loser, plus the record `id` for identification. This is the Decision 8 PII mitigation -- full records are never stored in conflict_log.

#### 1.3.5 `pruneExpired()` method

```sql
DELETE FROM conflict_log
WHERE dismissed_at IS NOT NULL
  AND expires_at < strftime('%Y-%m-%dT%H:%M:%f', 'now')
```

Only dismissed conflicts are auto-deleted. Undismissed conflicts are kept indefinitely. A warning is shown in the UI for undismissed conflicts older than 30 days.

---

### 1.4 SyncEngine

**File**: `lib/features/sync/engine/sync_engine.dart`
**Action**: Create
**Depends on**: SyncMutex (1.1), ChangeTracker (1.2), ConflictResolver (1.3), IntegrityChecker (Section A Step 12), SyncRegistry (Section A Step 7), SyncConfig (Section A Step 8), all adapters (Section A Step 6)

This is the core push/pull orchestrator that replaces the legacy `SyncService` push/pull logic.

#### 1.4.1 SyncEngineResult

```dart
class SyncEngineResult {
  final int pushed;
  final int pulled;
  final int errors;
  final List<String> errorMessages;
  final bool lockFailed;

  const SyncEngineResult({
    this.pushed = 0,
    this.pulled = 0,
    this.errors = 0,
    this.errorMessages = const [],
    this.lockFailed = false,
  });

  bool get hasErrors => errors > 0;
  bool get isSuccess => !hasErrors && !lockFailed;

  SyncEngineResult operator +(SyncEngineResult other) {
    return SyncEngineResult(
      pushed: pushed + other.pushed,
      pulled: pulled + other.pulled,
      errors: errors + other.errors,
      errorMessages: [...errorMessages, ...other.errorMessages],
    );
  }
}
```

#### 1.4.2 Progress callback typedef

```dart
typedef SyncProgressCallback = void Function(String tableName, int processed, int? total);
```

#### 1.4.3 Constructor

```dart
class SyncEngine {
  final Database db;
  final SupabaseClient supabase;
  final String companyId;
  final String userId;
  final String lockedBy;

  late final SyncMutex _mutex;
  late final ChangeTracker _changeTracker;
  late final ConflictResolver _conflictResolver;
  late final IntegrityChecker _integrityChecker;
  final SyncRegistry _registry = SyncRegistry.instance;

  bool _insidePushOrPull = false; // Debug-mode reentrancy guard

  SyncProgressCallback? onProgress;

  SyncEngine({
    required this.db,
    required this.supabase,
    required this.companyId,
    required this.userId,
    this.lockedBy = 'foreground',
    this.onProgress,
  }) {
    _mutex = SyncMutex(db);
    _changeTracker = ChangeTracker(db);
    _conflictResolver = ConflictResolver(db);
    _integrityChecker = IntegrityChecker(db, supabase);
  }
```

Parameters:
- `db`: SQLite database instance (from `DatabaseService`)
- `supabase`: Supabase client (from `Supabase.instance.client`)
- `companyId`: Current user's company ID (from `AuthProvider.userProfile.companyId`)
- `userId`: Current user's ID (for user-stamp columns and deletion notifications)
- `lockedBy`: `'foreground'` or `'background'` (for sync_lock attribution)
- `onProgress`: Optional callback for UI progress tracking

#### 1.4.4 `resetState()` method

Called on app startup and before each sync cycle:
```dart
Future<void> resetState() async {
  await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
  await _mutex.forceReset();
}
```

#### 1.4.5 `pushAndPull()` -- top-level orchestrator

```
pushAndPull():
  1. Force-reset sync_control.pulling = '0' (startup safety)
  2. Acquire lock via _mutex.tryAcquire(lockedBy)
     - If lock held, return SyncEngineResult(lockFailed: true)
  3. Assert !_insidePushOrPull (debug-mode reentrancy guard)
  4. Set _insidePushOrPull = true
  try:
  5. Execute _push()
  6. Execute _pull()
  7. Prune: _changeTracker.pruneProcessed()
  8. Prune: _conflictResolver.pruneExpired()
  9. Integrity check: if _integrityChecker.shouldRun(), run it (catch errors, don't fail sync)
  10. Return pushResult + pullResult
  finally:
  11. Set _insidePushOrPull = false
  12. Release lock via _mutex.release()
```

#### 1.4.6 `_push()` -- push flow

```
_push():
  1. Call _changeTracker.getUnprocessedChanges() -> grouped by table
  2. Iterate tables in _registry.dependencyOrder (FK order)
  3. For each table with changes:
     a. Get adapter from _registry.adapterFor(tableName)
     b. FK DEPENDENCY PRE-CHECK:
        - For each parent in adapter.fkDependencies:
          if _changeTracker.hasFailedEntries(parent):
            - Mark all changes for this table as failed: "Blocked by parent sync failure in {parent}"
            - Log: "BLOCKED: {tableName} skipped due to failed entries in {parent}"
            - Skip this table
     c. For each change entry:
        - If operation == 'delete': call _pushDelete(adapter, change)
        - If operation == 'insert' or 'update': call _pushUpsert(adapter, change)
        - On success: _changeTracker.markProcessed(change.id)
        - On failure: _handlePushError(error, change)
        - Report progress: onProgress(tableName, processedInTable, changes.length)
  4. Return SyncEngineResult with pushed/errors counts
```

#### 1.4.7 `_pushDelete()` -- delete operations

```dart
Future<void> _pushDelete(TableAdapter adapter, ChangeEntry change) async {
  try {
    await supabase.from(adapter.tableName).delete().eq('id', change.recordId);
  } on PostgrestException catch (e) {
    // 404 or "not found" = record already gone on server = benign no-op
    if (e.code == '404' || e.message.contains('not found') || e.code == 'PGRST116') {
      return; // Success -- record already deleted remotely
    }
    rethrow;
  }
}
```

Key: Uses `record_id` from the change_log entry only. Does NOT attempt to read the local record (it is already hard-deleted). If the Supabase record is already gone (404), this is treated as success.

#### 1.4.8 `_pushUpsert()` -- insert/update operations

```
_pushUpsert(adapter, change):
  1. Read local record: SELECT * FROM {table} WHERE id = {change.recordId}
  2. If no local record found: log skip, return (record was deleted locally after trigger fired)
  3. adapter.validate(localRecord) -- throws on invalid data
  4. var payload = adapter.convertForRemote(localRecord)
  5. Stamp userStampColumns: for each col in adapter.userStampColumns.keys, set payload[col] = userId
  6. Stamp company_id on projects if null/empty: payload['company_id'] = companyId
  7. Stamp created_by_user_id if not set: payload['created_by_user_id'] = userId
  8. If adapter is PhotoAdapter: call _pushPhotoThreePhase() and return
  9. Otherwise: supabase.from(adapter.tableName).upsert(payload)
```

#### 1.4.9 `_pushPhotoThreePhase()` -- three-phase photo push

```
_pushPhotoThreePhase(adapter, change, localRecord, payload):
  Phase 1: Upload file
    - Check if remote_path already exists on local record -> skip upload
    - If not: read file bytes from file_path, upload to 'entry-photos' bucket
      at path 'entries/{companyId}/{entryId}/{filename}'
    - Get remotePath from upload response or existing remote_path

  Phase 2: Upsert metadata
    - Set payload['remote_path'] = remotePath (FRESH from Phase 1, not stale)
    - Upsert to Supabase photos table

  Phase 3: Mark local synced
    - UPDATE local photos row: remote_path = remotePath, sync_status = 'synced'
    - sync_status is set here because photo UI code reads it for upload indicators

  Failure handling:
    - Phase 1 fails: change_log stays unprocessed, retry next cycle
    - Phase 2 fails: file exists in storage; next cycle Phase 1 detects it, skips, retries Phase 2
    - Phase 3 fails: next cycle re-runs; Phase 1 detects file exists, Phase 2 upserts, Phase 3 marks
```

#### 1.4.10 Error classification in `_handlePushError()`

```
_handlePushError(error, change) -> bool (true = handled/retryable, false = permanent):

  If error is PostgrestException:
    - 401 / JWT error:
      * Call _handleAuthError() to refresh token
      * If refresh succeeds: return true (retry immediately, do NOT increment retry_count)
      * If refresh fails: throw StateError('Auth refresh failed, aborting sync')
        (aborts entire sync cycle, surfaces "re-login required" in UI)
      * NEVER increment retry_count for auth failures

    - 429 (Too Many Requests) / 503 (Service Unavailable):
      * RETRYABLE. Call _changeTracker.markFailed(change.id, 'Retryable: {code}')
      * return true
      * Note: Exponential backoff (1s, 2s, 4s, 8s, 16s cap) applies at the cycle level

    - 400 (Bad Request) / 403 (Forbidden) / 404 (Not Found):
      * PERMANENT. Call _changeTracker.markFailed(change.id, 'Permanent: {message}')
      * return false
      * If retry_count >= maxRetryCount (5): leave unprocessed, surface in UI as
        "permanently failed -- manual intervention required"

  If error is SocketException / TimeoutException:
    * Network error -- retryable. markFailed(change.id, 'Network error')
    * return true

  Otherwise:
    * Unknown error. markFailed(change.id, error.toString())
    * return false
```

#### 1.4.11 Auth token refresh

```dart
Future<bool> _handleAuthError() async {
  final session = Supabase.instance.client.auth.currentSession;
  if (session == null) return false;
  try {
    await Supabase.instance.client.auth.refreshSession();
    return true;
  } catch (_) {
    return false;
  }
}
```

#### 1.4.12 `_pull()` -- pull flow

```
_pull():
  1. Load synced project IDs: _loadSyncedProjectIds()
  2. Set sync_control.pulling = '1' (suppress triggers)
  try:
  3. For each adapter in _registry.adapters (dependency order):
     - Call _pullTable(adapter)
     - Catch errors per-table (don't abort entire pull)
  4. Update last_sync_time in sync_metadata
  finally:
  5. Set sync_control.pulling = '0' (re-enable triggers -- GUARANTEED even on exception)
```

The `try/finally` block is CRITICAL. If the pull throws an exception mid-way, triggers must be re-enabled or subsequent local edits will not be tracked.

#### 1.4.13 `_pullTable()` -- per-table pull

```
_pullTable(adapter):
  1. Read cursor: SELECT value FROM sync_metadata WHERE key = 'last_pull_{tableName}'
  2. Paginated loop (pageSize = 100):
     a. Build Supabase query: supabase.from(tableName).select()
     b. Apply scope filter via _applyScopeFilter(query, adapter)
     c. If cursor exists: apply safety margin (cursor - 5 seconds) with .gte('updated_at', ...)
     d. Order by updated_at ASC, paginate with .range(offset, offset + pageSize - 1)
     e. For each remote record in page:
        - Convert: adapter.convertForLocal(remoteRaw)
        - Query local: SELECT * FROM {table} WHERE id = recordId

        If NOT exists locally:
          - If remote.deleted_at != null: SKIP (don't insert already-deleted records)
          - Strip unknown columns (PRAGMA table_info check)
          - INSERT with ConflictAlgorithm.ignore

        If EXISTS locally:
          - Deduplicate: if local.updated_at == remote.updated_at, SKIP (safety margin overlap)
          - Conflict resolution: _conflictResolver.resolve(tableName, recordId, local, remote)
          - If REMOTE WINS: UPDATE local record with remote data (strip unknown columns)
          - If LOCAL WINS (edit-wins):
            * Keep local version (no update)
            * Log conflict
            * EXPLICITLY INSERT change_log entry: _changeTracker.insertManualChange(tableName, recordId, 'update')
              This bypasses suppressed triggers -- ensures local-wins version is pushed back on next cycle

        Deletion notification:
          - If remote.deleted_at != null AND remote.deleted_by != null AND remote.deleted_by != userId:
            * Create deletion_notification row with:
              id: Uuid().v4()
              record_id: remote['id']
              table_name: adapter.tableName
              project_id: remote['project_id'] ?? localRecord?['project_id']
              record_name: adapter.extractRecordName(localRecord ?? remote)
              deleted_by: remote['deleted_by']
              deleted_by_name: lookup from user_profiles table
              deleted_at: remote['deleted_at']
              seen: 0
          - If remote.deleted_by == userId: do NOT create notification (user deleted it themselves)

        Track max updated_at for cursor update

     f. If page.length < pageSize: stop
        Else: offset += pageSize

  3. Update cursor: INSERT OR REPLACE INTO sync_metadata (key, value) VALUES ('last_pull_{tableName}', maxUpdatedAt)
```

#### 1.4.14 `_applyScopeFilter()` -- pull query scoping

```dart
PostgrestFilterBuilder _applyScopeFilter(
  PostgrestFilterBuilder query,
  TableAdapter adapter,
) {
  switch (adapter.scopeType) {
    case ScopeType.direct:
      // projects: filter by company_id directly
      return query.eq('company_id', companyId);
    case ScopeType.viaProject:
      // Tables with project_id: filter by synced project IDs
      return query.inFilter('project_id', _syncedProjectIds);
    case ScopeType.viaEntry:
      // Tables with entry_id: Supabase-side, filter by project_id
      // (photos, entry_equipment, etc. have project_id on Supabase via joins or denormalization)
      return query.inFilter('project_id', _syncedProjectIds);
    case ScopeType.viaContractor:
      // equipment: filter by contractor IDs within synced projects
      return query.inFilter('contractor_id', _syncedContractorIds);
  }
}
```

The engine caches `_syncedProjectIds` and `_syncedContractorIds` at the start of each pull cycle via `_loadSyncedProjectIds()`.

#### 1.4.15 `_loadSyncedProjectIds()` -- cached scope IDs

```dart
List<String> _syncedProjectIds = [];
List<String> _syncedContractorIds = [];

Future<void> _loadSyncedProjectIds() async {
  final rows = await db.query('synced_projects');
  _syncedProjectIds = rows.map((r) => r['project_id'] as String).toList();

  if (_syncedProjectIds.isNotEmpty) {
    final contractors = await db.query(
      'contractors',
      columns: ['id'],
      where: 'project_id IN (${_syncedProjectIds.map((_) => '?').join(',')})',
      whereArgs: _syncedProjectIds,
    );
    _syncedContractorIds = contractors.map((r) => r['id'] as String).toList();
  }
}
```

#### 1.4.16 `_createDeletionNotification()` -- deletion notification helper

Looks up the deleter's display_name from user_profiles, then inserts into `deletion_notifications` (table already exists in SQLite from `sync_tables.dart:22`).

#### 1.4.17 `_getLocalColumns()` -- column validation helper

Caches PRAGMA table_info results per table per cycle. Used to strip remote columns that don't exist in local SQLite schema before INSERT/UPDATE, preventing "no such column" errors.

---

### 1.5 SoftDeleteService Purge Redesign

**File**: `lib/services/soft_delete_service.dart`
**Action**: Modify
**Depends on**: Phase 1 (sync_control, change_log tables exist)

The current `SoftDeleteService.purgeExpiredRecords()` method hard-DELETEs rows. In the trigger-based engine, hard DELETEs fire the `AFTER DELETE` trigger, which would insert `operation='delete'` change_log entries. But these purged records are ALREADY deleted on Supabase -- we don't want to push DELETE operations for records that the server already knows are gone.

#### 1.5.1 Redesigned `purgeExpiredRecords()`

The purge flow must suppress triggers during hard DELETE, then manually insert `operation='delete'` change_log entries for any records that need remote cleanup.

```
purgeExpiredRecords(retentionDays, lastSyncTime):
  1. Calculate cutoff timestamp using MAX(local_clock, lastSyncTime) - retentionDays
  2. Set sync_control.pulling = '1' (suppress triggers during hard DELETE)
  try:
  3. For each table in _childToParentOrder:
     a. SELECT id FROM {table} WHERE deleted_at IS NOT NULL AND deleted_at < cutoff
     b. DELETE FROM {table} WHERE deleted_at IS NOT NULL AND deleted_at < cutoff
     c. For each deleted ID:
        - INSERT INTO change_log (table_name, record_id, operation) VALUES (table, id, 'delete')
        - This manually-inserted change_log entry ensures the delete is pushed to Supabase
  finally:
  4. Set sync_control.pulling = '0' (re-enable triggers)
```

#### 1.5.2 Redesigned `hardDeleteWithSync()`

The current method accepts a `queueSync` callback parameter. This must be removed and replaced with direct change_log insertion.

**Before** (current):
```dart
Future<void> hardDeleteWithSync(
  String tableName,
  String id, {
  required Future<void> Function(String table, String recordId, String operation) queueSync,
}) async {
  final database = await _dbService.database;
  await database.delete(tableName, where: 'id = ?', whereArgs: [id]);
  await queueSync(tableName, id, 'purge');
}
```

**After** (redesigned):
```dart
Future<void> hardDeleteWithSync(String tableName, String id) async {
  final database = await _dbService.database;

  // Suppress triggers during hard delete
  await database.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
  try {
    await database.delete(tableName, where: 'id = ?', whereArgs: [id]);
    // Manually insert change_log entry for remote delete
    await database.insert('change_log', {
      'table_name': tableName,
      'record_id': id,
      'operation': 'delete',
    });
  } finally {
    await database.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
  }
}
```

Key changes:
- Remove `queueSync` callback parameter (breaking change -- callers must be updated)
- Use `sync_control.pulling = '1'` to suppress the AFTER DELETE trigger
- Manually INSERT `change_log` entry with `operation='delete'` after the hard delete
- Use `try/finally` to guarantee trigger re-enablement

#### 1.5.3 Cascade soft-delete methods (no change needed)

`cascadeSoftDeleteProject()` and `cascadeSoftDeleteEntry()` use UPDATE to set `deleted_at`. This fires the AFTER UPDATE trigger, which produces `operation='update'` change_log entries. The push flow reads the local record, finds `deleted_at` set, and upserts it to Supabase with the soft-delete timestamp. No changes needed to cascade methods.

#### 1.5.4 Callers to update

Search for all callers of `hardDeleteWithSync` and remove the `queueSync` parameter:
- `lib/features/entries/presentation/providers/` (trash-related providers)
- Any screen that offers "Delete Forever" from trash

---

### 1.6 Phase 2 Tests

All test files go in `test/features/sync/engine/`.

#### 1.6.1 ChangeTracker tests
**File**: `test/features/sync/engine/change_tracker_test.dart`

Tests:
- `reads grouped changes from change_log, ordered by changed_at ASC`
- `marks entries as processed (processed = 1)`
- `respects retry limit in hasFailedEntries()`
- `with 600 unprocessed entries, getUnprocessedChanges() only returns 500 (oldest first)`
- `anomaly flag logged when unprocessed count > 1000`
- `insertManualChange() creates an entry that appears in next getUnprocessedChanges()`
- `pruneProcessed() deletes entries older than 7 days with processed=1`
- `pruneProcessed() does NOT delete unprocessed entries regardless of age`
- `markFailed() increments retry_count and sets error_message`

#### 1.6.2 ConflictResolver tests
**File**: `test/features/sync/engine/conflict_resolver_test.dart`

Tests:
- `remote wins when remote.updated_at > local.updated_at`
- `local wins when local.updated_at > remote.updated_at`
- `remote wins when timestamps are equal (deterministic tiebreaker) + conflict_log entry created`
- `remote wins when local.updated_at is null`
- `remote wins when remote.updated_at is null`
- `remote wins when both timestamps are null`
- `lost_data contains ONLY changed columns (not full record) -- Decision 8 PII mitigation`
- `lost_data always includes id field`
- `conflict_log entry has expires_at = detected_at + 7 days`
- `pruneExpired() deletes dismissed + expired entries`
- `pruneExpired() keeps undismissed entries even if expired`
- `pruneExpired() keeps dismissed entries that are not yet expired`
- Soft-delete edit-wins scenario: local has deleted_at=null (user re-edited), remote has deleted_at set. Local's updated_at > remote's => local wins, change_log entry created.

#### 1.6.3 SyncMutex tests
**File**: `test/features/sync/engine/sync_mutex_test.dart`

Tests:
- `tryAcquire() returns true on first call`
- `tryAcquire() returns false when lock already held`
- `release() allows subsequent tryAcquire() to succeed`
- `stale lock (older than 5 minutes) is auto-expired`
- `forceReset() clears lock regardless of age`
- `locked_by is recorded correctly ('foreground' or 'background')`

#### 1.6.4 SyncEngine tests (with mock adapters)
**File**: `test/features/sync/engine/sync_engine_test.dart`

Tests:
- `push processes changes in FK dependency order`
- `push skips table when parent has failed entries (parent-blocking check)`
- `push delete operation sends DELETE by record_id, no local read attempted`
- `push delete treats 404 as success (benign no-op)`
- `push upsert calls adapter.validate() then adapter.convertForRemote()`
- `push stamps userStampColumns with current userId`
- `push stamps company_id on projects if null`
- `push stamps created_by_user_id if not set`
- `401 triggers token refresh, retry_count NOT incremented`
- `401 with failed refresh aborts entire sync cycle`
- `429 triggers markFailed with retryable status`
- `400/403/404 triggers markFailed with permanent status`
- `pull suppresses triggers (sync_control.pulling = '1') during pull`
- `pull re-enables triggers even on exception (try/finally guarantee)`
- `pull: remote soft-delete by different user creates deletion_notification row`
- `pull: remote soft-delete by SAME user does NOT create deletion_notification`
- `pull: edit-wins conflict creates explicit change_log entry via insertManualChange()`
- `pull: skips already-deleted records that don't exist locally`
- `pull: deduplicates records with identical updated_at`
- `pull: applies scope filter based on synced_projects`
- `pushAndPull() acquires lock, runs push+pull, releases lock`
- `pushAndPull() returns lockFailed when lock held by another process`
- `pushAndPull() calls pruneProcessed() and pruneExpired() after sync`
- `pushAndPull() runs integrity check if due`
- `pushAndPull() releases lock even on exception (finally block)`

#### 1.6.5 SoftDeleteService purge tests
**File**: `test/services/soft_delete_service_test.dart` (update existing)

Tests:
- `purgeExpiredRecords() suppresses triggers during hard delete`
- `purgeExpiredRecords() inserts change_log entries for purged records`
- `purgeExpiredRecords() re-enables triggers even on error (try/finally)`
- `hardDeleteWithSync() no longer requires queueSync callback`
- `hardDeleteWithSync() suppresses triggers and manually inserts change_log`

---

## Step 2: Phase 3 -- Table Adapters

Phase 3 implements the 16 concrete table adapters that were defined in Section A Step 6. Each adapter is a pure configuration/conversion object -- no Supabase I/O. The SyncEngine handles all network calls; adapters only declare schema mapping, type converters, and validation rules.

**Implementation order** (FK dependency chain):
1. projects (root)
2. locations, contractors, bid_items, personnel_types (one-hop via project_id)
3. equipment (via contractor_id)
4. daily_entries (via project_id)
5. photos (via entry_id)
6. entry_equipment, entry_quantities (via entry_id)
7. entry_contractors, entry_personnel_counts (via entry_id -- formerly unsynced, GAP-6)
8. inspector_forms, form_responses, todo_items, calculation_history (via project_id)

### 2.1 ProjectAdapter

**File**: `lib/features/sync/adapters/project_adapter.dart`
**Class**: `ProjectAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'projects'` |
| `scopeType` | `ScopeType.direct` |
| `fkDependencies` | `const []` (root table) |
| `converters` | `{'is_active': BoolIntConverter()}` |
| `localOnlyColumns` | `const ['sync_status']` |
| `remoteOnlyColumns` | `const []` |
| `userStampColumns` | `const {}` |

**SQLite columns** (from `core_tables.dart`):
`id, name, project_number, client_name, description, created_at, updated_at, is_active, mode, mdot_contract_id, mdot_project_code, mdot_county, mdot_district, control_section_id, route_street, construction_eng, company_id, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. Strip `sync_status` (listed in localOnlyColumns -- note: projects table does NOT have this column in current schema, so stripping is a no-op safety measure)
2. Convert `is_active`: SQLite `INTEGER 0/1` -> Supabase `BOOLEAN true/false` via `BoolIntConverter.toRemote()`

**`convertForLocal()`**:
1. Convert `is_active`: Supabase `BOOLEAN` -> SQLite `INTEGER` via `BoolIntConverter.toLocal()`

**`validate()` rules**:
- Reject records with `project_number` that duplicates an existing project in the same `company_id` (query local SQLite: `SELECT id FROM projects WHERE project_number = ? AND company_id = ? AND id != ?`)
- Implementation: override `validate()` -- NOTE: this requires `Database` access. The validate method must accept a `Database` parameter or the adapter must receive it in its constructor. **Resolution**: The SyncEngine passes the Database to validate() via a context parameter, OR the validation is done in the engine before calling the adapter. The recommended approach: the engine performs this validation for ProjectAdapter specifically, since adapter.validate() is designed for simple field checks. The duplicate check is a cross-record query.
- **Alternative (recommended)**: Add an optional `Database? db` parameter to `TableAdapter.validate()` for adapters that need cross-record queries. ProjectAdapter overrides to check duplicates.

**`extractRecordName()`**: Default implementation returns `record['name']` which is the project name.

---

### 2.2 LocationAdapter

**File**: `lib/features/sync/adapters/location_adapter.dart`
**Class**: `LocationAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'locations'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `core_tables.dart`):
`id, project_id, name, description, latitude, longitude, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**: No type conversions needed. Default implementation passes all columns through.

**`convertForLocal()`**: No type conversions needed.

**`validate()`**: No special validation (default no-op).

**`extractRecordName()`**: Default returns `record['name']`.

---

### 2.3 ContractorAdapter

**File**: `lib/features/sync/adapters/contractor_adapter.dart`
**Class**: `ContractorAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'contractors'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `contractor_tables.dart`):
`id, project_id, name, type, contact_name, phone, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**: No conversions. All columns map directly.

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Default returns `record['name']`.

---

### 2.4 EquipmentAdapter

**File**: `lib/features/sync/adapters/equipment_adapter.dart`
**Class**: `EquipmentAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'equipment'` |
| `scopeType` | `ScopeType.viaContractor` |
| `fkDependencies` | `const ['contractors']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `contractor_tables.dart`):
`id, contractor_id, name, description, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**Note on scope**: Equipment does NOT have a `project_id` column. It scopes through `contractor_id -> contractors.project_id`. The `ScopeType.viaContractor` filter uses `_syncedContractorIds` (pre-loaded from local contractors table).

**`convertForRemote()`**: No conversions.

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Default returns `record['name']`.

---

### 2.5 BidItemAdapter

**File**: `lib/features/sync/adapters/bid_item_adapter.dart`
**Class**: `BidItemAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'bid_items'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `quantity_tables.dart`):
`id, project_id, item_number, description, unit, bid_quantity, unit_price, bid_amount, measurement_payment, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**: No conversions. `bid_quantity`, `unit_price`, `bid_amount` are REAL in both SQLite and Supabase (NUMERIC/FLOAT8).

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Override to return `record['item_number']` + ` - ` + `record['description']` for more meaningful deletion notification names.

---

### 2.6 PersonnelTypeAdapter

**File**: `lib/features/sync/adapters/personnel_type_adapter.dart`
**Class**: `PersonnelTypeAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'personnel_types'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects', 'contractors']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `personnel_tables.dart`):
`id, project_id, contractor_id, name, short_code, sort_order, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**: No conversions.

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Default returns `record['name']`.

---

### 2.7 DailyEntryAdapter

**File**: `lib/features/sync/adapters/daily_entry_adapter.dart`
**Class**: `DailyEntryAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'daily_entries'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects', 'locations']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const ['sync_status']` |
| `remoteOnlyColumns` | `const []` |
| `userStampColumns` | `const {'updated_by_user_id': 'current'}` |

**SQLite columns** (from `entry_tables.dart`):
`id, project_id, location_id, date, weather, temp_low, temp_high, activities, site_safety, sesc_measures, traffic_control, visitors, extras_overruns, signature, signed_at, status, submitted_at, revision_number, created_at, updated_at, sync_status, created_by_user_id, updated_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. Strip `sync_status` (local-only column)
2. No type conversions needed -- all columns map directly

The SyncEngine additionally stamps `updated_by_user_id` with the current `userId` before push, as declared by `userStampColumns`.

**`convertForLocal()`**: No conversions. `sync_status` is NOT set on pull (the change_log trigger system replaces sync_status tracking).

**`validate()`**: No special validation (project_id is NOT NULL in schema, enforced at DB level).

**`extractRecordName()`**: Override to return `record['date']` + ` entry` for meaningful notification names (e.g., "2026-03-04 entry").

---

### 2.8 PhotoAdapter

**File**: `lib/features/sync/adapters/photo_adapter.dart`
**Class**: `PhotoAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'photos'` |
| `scopeType` | `ScopeType.viaEntry` |
| `fkDependencies` | `const ['daily_entries', 'projects']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const ['sync_status', 'file_path']` |
| `remoteOnlyColumns` | `const []` |
| `isPhotoAdapter` | `true` (marker for SyncEngine three-phase routing) |

**SQLite columns** (from `photo_tables.dart`):
`id, entry_id, project_id, file_path, filename, remote_path, notes, caption, location_id, latitude, longitude, captured_at, sync_status, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. Strip `sync_status` (local-only)
2. Strip `file_path` (local-only -- device filesystem path, not meaningful on server)
3. `filename` IS included in payload (used for storage path construction)
4. `remote_path` IS included (set by three-phase push)

**`convertForLocal()`**: No type conversions. `file_path` from remote is ignored (not in remote payload). `sync_status` is NOT set on pull.

**`validate()`**:
- For new photos (inserts): `file_path` must be non-null and non-empty (needed for Phase 1 upload)
- For updates: `file_path` may be null if remote_path already exists (file was previously uploaded)

**Three-phase push**: Handled by `SyncEngine._pushPhotoThreePhase()`, not by the adapter itself. The adapter provides configuration; the engine provides behavior.

**`extractRecordName()`**: Override to return `record['filename']` or `record['caption']`.

---

### 2.9 EntryEquipmentAdapter

**File**: `lib/features/sync/adapters/entry_equipment_adapter.dart`
**Class**: `EntryEquipmentAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'entry_equipment'` |
| `scopeType` | `ScopeType.viaEntry` |
| `fkDependencies` | `const ['daily_entries', 'equipment']` |
| `converters` | `{'was_used': BoolIntConverter()}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `entry_tables.dart`):
`id, entry_id, equipment_id, was_used, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. Convert `was_used`: SQLite `INTEGER 0/1` -> Supabase `BOOLEAN true/false`

**`convertForLocal()`**:
1. Convert `was_used`: Supabase `BOOLEAN` -> SQLite `INTEGER 0/1`

**`validate()`**: No special validation.

**`extractRecordName()`**: Override to return a descriptive string, e.g., `'Equipment for entry ${record['entry_id']}'`.

---

### 2.10 EntryQuantitiesAdapter

**File**: `lib/features/sync/adapters/entry_quantities_adapter.dart`
**Class**: `EntryQuantitiesAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'entry_quantities'` |
| `scopeType` | `ScopeType.viaEntry` |
| `fkDependencies` | `const ['daily_entries', 'bid_items']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `quantity_tables.dart`):
`id, entry_id, bid_item_id, quantity, notes, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**: No conversions. `quantity` is REAL in both systems.

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Override to return `'Quantity: ${record['quantity']}'`.

---

### 2.11 EntryContractorsAdapter

**File**: `lib/features/sync/adapters/entry_contractors_adapter.dart`
**Class**: `EntryContractorsAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'entry_contractors'` |
| `scopeType` | `ScopeType.viaEntry` |
| `fkDependencies` | `const ['daily_entries', 'contractors']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `entry_tables.dart`):
`id, entry_id, contractor_id, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**IMPORTANT**: This table has NEVER been synced before (GAP-6). This adapter enables net-new sync capability.

**`convertForRemote()`**: No conversions. All columns map directly.

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Default returns `record['id']`.

---

### 2.12 EntryPersonnelCountsAdapter

**File**: `lib/features/sync/adapters/entry_personnel_counts_adapter.dart`
**Class**: `EntryPersonnelCountsAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'entry_personnel_counts'` |
| `scopeType` | `ScopeType.viaEntry` |
| `fkDependencies` | `const ['daily_entries', 'contractors', 'personnel_types']` |
| `converters` | `const {}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `personnel_tables.dart`):
`id, entry_id, contractor_id, type_id, count, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**IMPORTANT**: This table has NEVER been synced before (GAP-6). This adapter enables net-new sync capability. It has three FK dependencies (`daily_entries`, `contractors`, `personnel_types`).

**`convertForRemote()`**: No conversions. `count` is INTEGER in both systems.

**`convertForLocal()`**: No conversions.

**`validate()`**: No special validation.

**`extractRecordName()`**: Override to return `'Personnel count: ${record['count']}'`.

---

### 2.13 InspectorFormAdapter

**File**: `lib/features/sync/adapters/inspector_form_adapter.dart`
**Class**: `InspectorFormAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'inspector_forms'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects']` |
| `converters` | See below |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**Converters map:**
```dart
{
  'is_builtin': BoolIntConverter(),
  'template_bytes': ByteaConverter(),
  'field_definitions': JsonMapConverter(),
  'parsing_keywords': JsonMapConverter(),
  'table_row_config': JsonMapConverter(),
}
```

**SQLite columns** (from `toolbox_tables.dart`):
`id, project_id, name, template_path, field_definitions, parsing_keywords, table_row_config, is_builtin, template_source, template_hash, template_version, template_field_count, template_bytes, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. `is_builtin`: SQLite `INTEGER 0/1` -> Supabase `BOOLEAN`
2. `template_bytes`: SQLite `BLOB (Uint8List)` -> Supabase `BYTEA (base64 string)` -- **NEW-9 fix**: this conversion did NOT exist in the old sync system
3. `field_definitions`: SQLite `TEXT (JSON string)` -> Supabase `JSONB (Map/List)` -- **GAP-16 fix**
4. `parsing_keywords`: SQLite `TEXT (JSON string)` -> Supabase `JSONB (Map/List)` -- **GAP-16 fix**
5. `table_row_config`: SQLite `TEXT (JSON string)` -> Supabase `JSONB (Map/List)`

**`convertForLocal()`**: Reverse of above:
1. `is_builtin`: Supabase `BOOLEAN` -> SQLite `INTEGER`
2. `template_bytes`: Supabase `BYTEA (base64)` -> SQLite `BLOB (Uint8List)`
3. `field_definitions`: Supabase `JSONB` -> SQLite `TEXT (JSON string)`
4. `parsing_keywords`: Supabase `JSONB` -> SQLite `TEXT (JSON string)`
5. `table_row_config`: Supabase `JSONB` -> SQLite `TEXT (JSON string)`

**`validate()`**: Reject records with null `project_id`. Override:
```dart
@override
Future<void> validate(Map<String, dynamic> record) async {
  if (record['project_id'] == null) {
    throw StateError('InspectorForm ${record['id']} has null project_id');
  }
}
```

**`extractRecordName()`**: Default returns `record['name']`.

---

### 2.14 FormResponseAdapter

**File**: `lib/features/sync/adapters/form_response_adapter.dart`
**Class**: `FormResponseAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'form_responses'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects', 'inspector_forms']` |
| `converters` | See below |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**Converters map:**
```dart
{
  'response_data': JsonMapConverter(),
  'header_data': JsonMapConverter(),
  'response_metadata': JsonMapConverter(),
  'table_rows': JsonMapConverter(),
}
```

**SQLite columns** (from `toolbox_tables.dart`):
`id, form_type, form_id, entry_id, project_id, header_data, response_data, table_rows, response_metadata, status, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. `response_data`: SQLite `TEXT (JSON)` -> Supabase `JSONB`
2. `header_data`: SQLite `TEXT (JSON)` -> Supabase `JSONB`
3. `response_metadata`: SQLite `TEXT (JSON)` -> Supabase `JSONB` (nullable)
4. `table_rows`: SQLite `TEXT (JSON)` -> Supabase `JSONB` (nullable)

**`convertForLocal()`**: Reverse of above.

**`validate()`**: Handle NULL `form_id` gracefully -- do NOT reject. The FK constraint on form_id was dropped (form_responses can exist without a parent inspector_form).

**`extractRecordName()`**: Override to return `record['form_type']` for meaningful names.

---

### 2.15 TodoItemAdapter

**File**: `lib/features/sync/adapters/todo_item_adapter.dart`
**Class**: `TodoItemAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'todo_items'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects']` |
| `converters` | `{'is_completed': BoolIntConverter()}` |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**SQLite columns** (from `toolbox_tables.dart`):
`id, project_id, entry_id, title, description, is_completed, due_date, priority, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. `is_completed`: SQLite `INTEGER 0/1` -> Supabase `BOOLEAN`

**`convertForLocal()`**:
1. `is_completed`: Supabase `BOOLEAN` -> SQLite `INTEGER`

**`validate()`**: Reject records with null `project_id`:
```dart
@override
Future<void> validate(Map<String, dynamic> record) async {
  if (record['project_id'] == null) {
    throw StateError('TodoItem ${record['id']} has null project_id');
  }
}
```

**`extractRecordName()`**: Override to return `record['title']`.

---

### 2.16 CalculationHistoryAdapter

**File**: `lib/features/sync/adapters/calculation_history_adapter.dart`
**Class**: `CalculationHistoryAdapter extends TableAdapter`

| Property | Value |
|----------|-------|
| `tableName` | `'calculation_history'` |
| `scopeType` | `ScopeType.viaProject` |
| `fkDependencies` | `const ['projects']` |
| `converters` | See below |
| `localOnlyColumns` | `const []` |
| `remoteOnlyColumns` | `const []` |

**Converters map:**
```dart
{
  'input_data': JsonMapConverter(),
  'result_data': JsonMapConverter(),
}
```

**SQLite columns** (from `toolbox_tables.dart`):
`id, project_id, entry_id, calc_type, input_data, result_data, notes, created_at, updated_at, created_by_user_id, deleted_at, deleted_by`

**`convertForRemote()`**:
1. `input_data`: SQLite `TEXT (JSON)` -> Supabase `JSONB` -- **GAP-16 fix**
2. `result_data`: SQLite `TEXT (JSON)` -> Supabase `JSONB` -- **GAP-16 fix**

**`convertForLocal()`**: Reverse of above.

**`validate()`**: Reject records with null `project_id`:
```dart
@override
Future<void> validate(Map<String, dynamic> record) async {
  if (record['project_id'] == null) {
    throw StateError('CalculationHistory ${record['id']} has null project_id');
  }
}
```

**`extractRecordName()`**: Override to return `record['calc_type']`.

---

### 2.17 entry_contractors Refactor (Diff-Based Approach)

**File**: `lib/features/contractors/data/datasources/local/entry_contractors_local_datasource.dart`
**Action**: Modify
**Depends on**: EntryContractorsAdapter (2.11), Phase 1 triggers on entry_contractors

The current `setForEntry()` method uses a destructive pattern: DELETE ALL existing rows for an entry, then INSERT all new rows. With the trigger-based engine, this produces N DELETE + M INSERT change_log entries for a single logical "replace" operation, creating excessive sync traffic and risk of data loss on network failure mid-push.

#### 2.17.1 Current implementation (to be replaced)

```dart
Future<void> setForEntry(String entryId, List<String> contractorIds) async {
  final database = await db.database;
  await database.transaction((txn) async {
    // Delete existing
    await txn.delete(_tableName, where: 'entry_id = ?', whereArgs: [entryId]);
    // Insert new
    final now = DateTime.now().toIso8601String();
    for (final contractorId in contractorIds) {
      await txn.insert(_tableName, {
        'id': 'ec-$entryId-$contractorId',
        'entry_id': entryId,
        'contractor_id': contractorId,
        'created_at': now,
      });
    }
  });
}
```

#### 2.17.2 Diff-based replacement

```dart
Future<void> setForEntry(String entryId, List<String> contractorIds) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();

  await database.transaction((txn) async {
    // 1. Get existing contractor IDs for this entry
    final existing = await txn.query(
      _tableName,
      columns: ['id', 'contractor_id'],
      where: 'entry_id = ? AND deleted_at IS NULL',
      whereArgs: [entryId],
    );
    final existingIds = existing.map((r) => r['contractor_id'] as String).toSet();
    final desiredIds = contractorIds.toSet();

    // 2. Compute diff
    final toAdd = desiredIds.difference(existingIds);
    final toRemove = existingIds.difference(desiredIds);
    // Items in both sets: leave unchanged (no change_log entries generated)

    // 3. Soft-delete removed contractors (triggers 'update' in change_log)
    for (final contractorId in toRemove) {
      await txn.update(
        _tableName,
        {
          'deleted_at': now,
          'deleted_by': null, // Could stamp userId if available
          'updated_at': now,
        },
        where: 'entry_id = ? AND contractor_id = ? AND deleted_at IS NULL',
        whereArgs: [entryId, contractorId],
      );
    }

    // 4. Insert new contractors (triggers 'insert' in change_log)
    for (final contractorId in toAdd) {
      await txn.insert(_tableName, {
        'id': 'ec-$entryId-$contractorId',
        'entry_id': entryId,
        'contractor_id': contractorId,
        'created_at': now,
        'updated_at': now,
      });
    }
  });
}
```

Key improvements:
- **Unchanged rows are left alone**: No change_log entries generated for contractors that remain
- **Removed contractors are soft-deleted**: Fires AFTER UPDATE trigger with `operation='update'` (the engine pushes the soft-delete timestamp to Supabase)
- **New contractors are inserted**: Fires AFTER INSERT trigger with `operation='insert'`
- **Prevents data loss**: If network fails mid-push, only the individual add/remove operations need to retry, not the entire set replacement

#### 2.17.3 Also update `removeAllForEntry()`

The current `removeAllForEntry()` does a hard DELETE. Change to soft-delete:

```dart
Future<void> removeAllForEntry(String entryId) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();
  await database.update(
    _tableName,
    {'deleted_at': now, 'updated_at': now},
    where: 'entry_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId],
  );
}
```

#### 2.17.4 Update `remove()` method

Change from hard DELETE to soft-delete:

```dart
Future<void> remove(String entryId, String contractorId) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();
  await database.update(
    _tableName,
    {'deleted_at': now, 'updated_at': now},
    where: 'entry_id = ? AND contractor_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId, contractorId],
  );
}
```

#### 2.17.5 Update `getByEntryId()` to exclude soft-deleted

```dart
Future<List<EntryContractor>> getByEntryId(String entryId) async {
  final database = await db.database;
  final maps = await database.query(
    _tableName,
    where: 'entry_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId],
  );
  return maps.map((m) => EntryContractor.fromMap(m)).toList();
}
```

---

### 2.18 Pull Query Scoping to synced_projects

All adapters with `ScopeType.viaProject`, `ScopeType.viaEntry`, or `ScopeType.viaContractor` have their pull queries filtered through `synced_projects`. This is implemented in `SyncEngine._applyScopeFilter()` (Step 1.4.14), not in the adapters themselves.

**Scope filter rules by ScopeType:**

| ScopeType | Supabase filter | Tables |
|-----------|----------------|--------|
| `direct` | `.eq('company_id', companyId)` | projects |
| `viaProject` | `.inFilter('project_id', syncedProjectIds)` | locations, contractors, bid_items, personnel_types, daily_entries, inspector_forms, form_responses, todo_items, calculation_history |
| `viaEntry` | `.inFilter('project_id', syncedProjectIds)` | photos, entry_equipment, entry_quantities, entry_contractors, entry_personnel_counts |
| `viaContractor` | `.inFilter('contractor_id', syncedContractorIds)` | equipment |

**Note on viaEntry**: The Supabase tables for entry-scoped data (photos, entry_equipment, etc.) may not have a direct `project_id` column. If they do not, the filter must be applied differently:
- Option A: The Supabase view/RPC provides project_id via a join
- Option B: The engine queries entry_ids locally first, then uses `.inFilter('entry_id', entryIds)`
- **Recommended**: Check if these tables have `project_id` on Supabase. Photos DO have `project_id`. For entry_equipment, entry_quantities, entry_contractors, entry_personnel_counts: these likely do NOT have project_id on Supabase. The engine should fall back to querying local daily_entries for entry_ids within synced projects, then filtering by entry_id.

**Fallback for tables without project_id on Supabase:**

```dart
case ScopeType.viaEntry:
  // If table has project_id on Supabase (photos): use it
  if (adapter.tableName == 'photos') {
    return query.inFilter('project_id', _syncedProjectIds);
  }
  // Otherwise: filter by entry_id from local daily_entries
  return query.inFilter('entry_id', _syncedEntryIds);
```

Where `_syncedEntryIds` is loaded at pull start:
```dart
final entries = await db.query(
  'daily_entries',
  columns: ['id'],
  where: 'project_id IN (${_syncedProjectIds.map((_) => '?').join(',')})',
  whereArgs: _syncedProjectIds,
);
_syncedEntryIds = entries.map((r) => r['id'] as String).toList();
```

**Warning**: If `_syncedEntryIds` is large (thousands of entries), the `.inFilter()` may hit Supabase URL length limits. In that case, chunk the filter into multiple requests of 200 entry_ids each.

---

### 2.19 Phase 3 Tests

All test files go in `test/features/sync/adapters/`.

#### 2.19.1 Per-adapter round-trip tests (one file per adapter)

For EACH of the 16 adapters, create a test file at:
`test/features/sync/adapters/{table}_adapter_test.dart`

Each file must include these test cases:

**Convert tests:**
- `convertForRemote() produces valid Supabase payload`
  - All localOnlyColumns are stripped
  - Type converters applied correctly (BoolInt, JsonMap, Bytea)
  - All remaining columns present
- `convertForLocal() produces valid SQLite map`
  - All remoteOnlyColumns are stripped
  - Type converters applied in reverse
- `round-trip: local -> remote -> local preserves all data`
  - Start with a valid local record, convertForRemote, convertForLocal, assert equality
- `null/empty handling for every nullable column`
  - Test null values pass through converters without error
  - Test empty strings where applicable

**Type converter round-trip tests** (for adapters with converters):
- `BoolIntConverter: 0 -> false -> 0, 1 -> true -> 1, null -> null`
- `JsonMapConverter: '{"a":1}' -> {"a":1} -> '{"a":1}'`
- `ByteaConverter: Uint8List -> base64 string -> Uint8List` (inspector_forms only)

**Validation tests:**
- `validate() accepts valid records` (all adapters)
- `validate() rejects records with null project_id` (inspector_forms, todo_items, calculation_history)
- `validate() accepts null form_id on form_responses` (not rejected)
- `validate() rejects duplicate project_number` (projects -- if cross-record validation is implemented)
- `validate() rejects photos with null file_path` (photos)

**Scope and dependency tests:**
- `scopeType is correct`
- `fkDependencies lists correct parent tables`
- `localOnlyColumns are correct`
- `extractRecordName() returns meaningful value`

#### 2.19.2 Adapter test file list

| # | File | Table |
|---|------|-------|
| 1 | `test/features/sync/adapters/project_adapter_test.dart` | projects |
| 2 | `test/features/sync/adapters/location_adapter_test.dart` | locations |
| 3 | `test/features/sync/adapters/contractor_adapter_test.dart` | contractors |
| 4 | `test/features/sync/adapters/equipment_adapter_test.dart` | equipment |
| 5 | `test/features/sync/adapters/bid_item_adapter_test.dart` | bid_items |
| 6 | `test/features/sync/adapters/personnel_type_adapter_test.dart` | personnel_types |
| 7 | `test/features/sync/adapters/daily_entry_adapter_test.dart` | daily_entries |
| 8 | `test/features/sync/adapters/photo_adapter_test.dart` | photos |
| 9 | `test/features/sync/adapters/entry_equipment_adapter_test.dart` | entry_equipment |
| 10 | `test/features/sync/adapters/entry_quantities_adapter_test.dart` | entry_quantities |
| 11 | `test/features/sync/adapters/entry_contractors_adapter_test.dart` | entry_contractors |
| 12 | `test/features/sync/adapters/entry_personnel_counts_adapter_test.dart` | entry_personnel_counts |
| 13 | `test/features/sync/adapters/inspector_form_adapter_test.dart` | inspector_forms |
| 14 | `test/features/sync/adapters/form_response_adapter_test.dart` | form_responses |
| 15 | `test/features/sync/adapters/todo_item_adapter_test.dart` | todo_items |
| 16 | `test/features/sync/adapters/calculation_history_adapter_test.dart` | calculation_history |

#### 2.19.3 entry_contractors refactor tests
**File**: `test/features/contractors/data/datasources/local/entry_contractors_local_datasource_test.dart`

Tests:
- `setForEntry() with new contractors inserts only new rows (change_log: N inserts)`
- `setForEntry() with removed contractors soft-deletes them (change_log: N updates, not deletes)`
- `setForEntry() with unchanged contractors generates NO change_log entries`
- `setForEntry() with mixed add/remove only affects changed rows`
- `remove() soft-deletes instead of hard-deleting`
- `removeAllForEntry() soft-deletes all rows for an entry`
- `getByEntryId() excludes soft-deleted rows`

#### 2.19.4 Pull scope integration tests
**File**: `test/features/sync/engine/pull_scope_test.dart`

Tests:
- `pull applies company_id filter for projects (ScopeType.direct)`
- `pull applies project_id IN synced_projects for viaProject tables`
- `pull applies entry_id filter for viaEntry tables without project_id`
- `pull applies contractor_id filter for equipment (ScopeType.viaContractor)`
- `pull respects synced_projects -- unselected projects are NOT pulled`
- `pull handles empty synced_projects gracefully (no crash, no data pulled)`

#### 2.19.5 Integration round-trip tests
**File**: `test/features/sync/engine/adapter_integration_test.dart`

Tests (per table, against mock Supabase):
- `full push round-trip: local insert -> change_log -> push -> Supabase has record`
- `full pull round-trip: Supabase has record -> pull -> local has record`
- `push/pull round-trip preserves all data for each table`

---

## Summary: Implementation Dependencies

```
Phase 1 (Section A) MUST be complete
    |
    v
Phase 2 Step 1.1 (SyncMutex)          -- depends on sync_lock table
Phase 2 Step 1.2 (ChangeTracker)       -- depends on change_log table
Phase 2 Step 1.3 (ConflictResolver)    -- depends on conflict_log table
    |
    v
Phase 2 Step 1.4 (SyncEngine)         -- depends on 1.1, 1.2, 1.3, IntegrityChecker, all adapters
Phase 2 Step 1.5 (SoftDeleteService)   -- depends on sync_control, change_log tables
Phase 2 Step 1.6 (Tests)              -- depends on all Phase 2 code
    |
    v
Phase 3 Steps 2.1-2.16 (Adapters)     -- already created in Section A, this section documents specs
Phase 3 Step 2.17 (entry_contractors)  -- can be done in parallel with adapter testing
Phase 3 Step 2.18 (Pull scoping)       -- implemented in SyncEngine, documented here
Phase 3 Step 2.19 (Tests)             -- depends on all Phase 3 code
```

**Recommended batch order:**
1. Batch 1 (parallel): SyncMutex, ChangeTracker, ConflictResolver
2. Batch 2: SyncEngine (depends on Batch 1)
3. Batch 3 (parallel): SoftDeleteService redesign, entry_contractors refactor
4. Batch 4: Phase 2 tests
5. Batch 5: Phase 3 adapter tests (all 16 adapters)
6. Batch 6: Pull scope integration tests + adapter round-trip integration tests

---

## Corrections and Clarifications

| ID | Source | Issue | Resolution |
|----|--------|-------|------------|
| C1 | Analysis | `ScopeType` had 3 variants (direct/oneHop/twoHop) | Replaced with 4 semantically clear variants: direct, viaProject, viaEntry, viaContractor |
| C2 | Analysis | `entry_contractors` and `entry_personnel_counts` never synced | Noted as GAP-6 net-new sync. Adapters enable this. |
| C3 | Plan | `projects` listed `sync_status` in localOnlyColumns | Projects table does NOT have sync_status column. Stripping is a no-op safety measure. |
| C4 | Plan | viaEntry tables pull filter assumed project_id on Supabase | Photos have project_id, but entry_equipment/entry_quantities/entry_contractors/entry_personnel_counts may not. Fallback to entry_id filter documented. |
| C5 | Plan | `hardDeleteWithSync` had `queueSync` callback | Redesigned to use direct sync_control/change_log manipulation. Breaking change for callers. |
| C6 | Analysis | `setForEntry()` destructive DELETE-ALL pattern | Refactored to diff-based approach: soft-delete removed, insert new, leave unchanged. |
| C7 | Plan | `calculation_history` had no JSONB converters | Added JsonMapConverter for input_data and result_data (GAP-16). |
| C8 | Plan | Decision 9 mislabeled | Correctly referenced as Decision 14 for pruning. |
