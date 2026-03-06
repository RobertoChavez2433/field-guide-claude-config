# Section D: Phases 4-7, Risk & Cutover — Implementation Plan

## Pre-requisites

Before starting any Phase 4 work, the following must be complete and verified:

1. **Phase 0 (Schema + Security)**: All Supabase migrations deployed and passing.
2. **Phase 1 (Change Tracking Foundation)**: SQLite v30 migration installed; change_log, conflict_log, sync_control, sync_lock, synced_projects, sync_metadata, user_certifications tables created; triggers installed on all 16 synced tables; schema verifier updated with new tables.
3. **Phase 2 (Sync Engine Core)**: SyncEngine, SyncMutex, ChangeTracker, ConflictResolver, TableAdapter base class, SyncRegistry, SyncConfig, IntegrityChecker — all implemented and unit-tested with mock adapters.
4. **Phase 3 (Table Adapters)**: All 16 table adapters implemented and tested (projects, locations, contractors, bid_items, personnel_types, equipment, daily_entries, inspector_forms, form_responses, todo_items, calculation_history, entry_equipment, entry_quantities, entry_contractors, entry_personnel_counts, photos — except Photo has only the basic adapter without three-phase logic).

**Key infrastructure available from Phases 1-3:**
- `lib/features/sync/engine/sync_engine.dart` — Push/pull orchestrator
- `lib/features/sync/engine/change_tracker.dart` — Reads change_log
- `lib/features/sync/engine/conflict_resolver.dart` — LWW + conflict_log
- `lib/features/sync/engine/sync_mutex.dart` — Advisory lock
- `lib/features/sync/engine/integrity_checker.dart` — Drift detection
- `lib/features/sync/engine/sync_registry.dart` — Adapter registration
- `lib/features/sync/engine/adapters/` — All table adapters
- `lib/features/sync/engine/converters/` — Type converters
- `lib/core/database/schema/sync_engine_tables.dart` — New engine table DDL

---

## Step 1: Phase 4 — Photo Adapter (Three-Phase Push)

**Agent**: `backend-data-layer-agent`
**Goal**: Replace the basic PhotoAdapter (from Phase 3) with three-phase photo push logic, implement storage cleanup, orphan detection, and refactor all hard-delete `deleteByEntryId()` methods to soft-delete.

### 1.1 PhotoAdapter Three-Phase Push Override

**File to modify**: `lib/features/sync/engine/adapters/photo_adapter.dart`

The PhotoAdapter was created in Phase 3 with basic column mapping, but its `push()` method delegates to the default `TableAdapter.push()`. Override it with three-phase logic:

**Implementation:**

```dart
@override
Future<PushResult> push(ChangeLogEntry entry, SupabaseClient client) async {
  // For delete operations, use default behavior (send DELETE by record_id)
  if (entry.operation == 'delete') {
    return super.push(entry, client);
  }

  // For insert/update operations, use three-phase logic
  final localRecord = await readLocal(entry.recordId);
  if (localRecord == null) {
    return PushResult.skip(reason: 'Record not found locally');
  }

  final remotePayload = convertForRemote(localRecord);
  final filePath = localRecord['file_path'] as String?;
  final existingRemotePath = localRecord['remote_path'] as String?;

  // --- Phase 1: Upload file to Supabase Storage ---
  String? remotePath = existingRemotePath;
  if (filePath != null && filePath.isNotEmpty) {
    final file = File(filePath);
    if (await file.exists()) {
      // Check if file already exists in storage (idempotent re-upload)
      if (existingRemotePath != null && existingRemotePath.isNotEmpty) {
        // File already uploaded (previous attempt succeeded at Phase 1)
        // Skip upload, proceed to Phase 2
        remotePath = existingRemotePath;
      } else {
        // Build company-scoped path: entries/{companyId}/{entryId}/{filename}
        final companyId = _getCompanyId();
        final entryId = localRecord['entry_id'] as String;
        final filename = localRecord['filename'] as String;
        final path = 'entries/$companyId/$entryId/$filename';

        try {
          remotePath = await _uploadFile(client, file, path);
        } catch (e) {
          // Phase 1 failure — return retry
          return PushResult.retry(error: 'File upload failed: $e');
        }
      }
    }
  }

  // --- Phase 2: Upsert metadata to Supabase photos table ---
  // CRITICAL (fixes NEW-4): Use fresh remotePath from Phase 1,
  // NOT the stale value from the local map
  if (remotePath != null) {
    remotePayload['remote_path'] = remotePath;
  }

  try {
    await client
        .from(tableName)
        .upsert(remotePayload, onConflict: 'id');
  } catch (e) {
    // Phase 2 failure — file exists in storage, retry metadata only next cycle
    return PushResult.retry(error: 'Metadata upsert failed: $e');
  }

  // --- Phase 3: Mark local record as synced ---
  // Only after both Phase 1 and Phase 2 succeed (fixes NEW-3)
  try {
    await updateLocal(entry.recordId, {
      'remote_path': remotePath,
    });
    return PushResult.success();
  } catch (e) {
    // Phase 3 failure — next cycle will skip upload (remote_path set),
    // upsert metadata (idempotent), then mark synced
    return PushResult.retry(error: 'Local mark-synced failed: $e');
  }
}
```

**Key behaviors:**
- Phase 1 failure: Next cycle re-uploads the file (idempotent if file exists in storage).
- Phase 2 failure: File exists in storage. Next cycle skips upload (remote_path already set locally if Phase 1 succeeded previously, or re-uploads then upserts).
- Phase 1 + Phase 2 succeed, Phase 3 fails: Next cycle detects remote_path is set locally, skips upload, upserts metadata (idempotent), marks synced.

**Helper methods to add:**

```dart
Future<String> _uploadFile(SupabaseClient client, File file, String path) async {
  // Validate path format (SEC-NEW-7 defense-in-depth)
  _validateStoragePath(path);
  final bytes = await compute(_readFileBytesIsolate, file.path);
  if (bytes == null) throw Exception('Failed to read file: ${file.path}');
  await client.storage.from('entry-photos').uploadBinary(path, bytes);
  return path;
}

void _validateStoragePath(String path) {
  final pattern = RegExp(
    r'^entries/[a-f0-9-]+/[a-f0-9-]+/[a-zA-Z0-9_.-]+\.(jpg|jpeg|png|heic)$',
  );
  if (!pattern.hasMatch(path)) {
    throw ArgumentError('Invalid storage path: $path');
  }
}
```

### 1.2 Photo Soft-Delete Push

In the same `push()` method, ensure that when a photo has `deleted_at` set (soft-delete), the metadata upsert sends the `deleted_at` timestamp to Supabase. The `convertForRemote()` method from Phase 3 should already include `deleted_at` in the payload. Verify this is the case.

**File**: `lib/features/sync/engine/adapters/photo_adapter.dart`

Verify that `convertForRemote()` includes:
```dart
if (localRecord['deleted_at'] != null) {
  remotePayload['deleted_at'] = localRecord['deleted_at'];
  remotePayload['deleted_by'] = localRecord['deleted_by'];
}
```

### 1.3 Storage Cleanup Phase

**File to create**: `lib/features/sync/engine/storage_cleanup.dart`

This runs after the push phase and deletes storage files for photos that have been soft-deleted for 30+ days and then purged.

```dart
class StorageCleanup {
  final SupabaseClient _client;
  final DatabaseService _dbService;

  StorageCleanup(this._client, this._dbService);

  /// Delete storage files for photos that have been hard-deleted (purged from SQLite)
  /// but whose storage files may still exist.
  ///
  /// Called after each push cycle. Reads from a `storage_cleanup_queue` that gets
  /// populated when SoftDeleteService.hardDeleteWithSync() processes photo purges.
  Future<int> cleanupExpiredPhotos() async {
    final database = await _dbService.database;

    // Read pending cleanup entries
    final pending = await database.query(
      'storage_cleanup_queue',
      where: 'status = ?',
      whereArgs: ['pending'],
      orderBy: 'created_at ASC',
      limit: 50,
    );

    int cleaned = 0;
    for (final entry in pending) {
      final remotePath = entry['remote_path'] as String?;
      if (remotePath != null && remotePath.isNotEmpty) {
        try {
          await _client.storage.from('entry-photos').remove([remotePath]);
          cleaned++;
        } catch (e) {
          // Log but continue — orphan scanner will catch stragglers
        }
      }

      // Mark as processed regardless of success (orphan scanner is fallback)
      await database.update(
        'storage_cleanup_queue',
        {'status': 'processed', 'processed_at': DateTime.now().toUtc().toIso8601String()},
        where: 'id = ?',
        whereArgs: [entry['id']],
      );
    }

    return cleaned;
  }
}
```

**Note**: The `storage_cleanup_queue` table should be added in the Phase 1 migration (v30). If it was not included, add it in a v31 migration during Phase 4. Schema:

```sql
CREATE TABLE storage_cleanup_queue (
  id TEXT PRIMARY KEY,
  remote_path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL,
  processed_at TEXT
)
```

### 1.4 Orphan Scanner

**File to create**: `lib/features/sync/engine/orphan_scanner.dart`

Queries the local `photos` table for all known remote_paths, then lists all files in Supabase Storage under the company prefix, and flags any storage files that have no corresponding DB row and are older than 24 hours.

```dart
class OrphanScanner {
  final SupabaseClient _client;
  final DatabaseService _dbService;
  static const String _bucket = 'entry-photos';

  OrphanScanner(this._client, this._dbService);

  /// Scan for orphaned storage files.
  /// Returns a list of orphaned paths for logging/alerting.
  Future<List<String>> scan(String companyId) async {
    // 1. Get all known remote_paths from local photos table
    final database = await _dbService.database;
    final localPhotos = await database.query(
      'photos',
      columns: ['remote_path'],
      where: 'remote_path IS NOT NULL AND remote_path != ?',
      whereArgs: [''],
    );
    final knownPaths = localPhotos
        .map((r) => r['remote_path'] as String)
        .toSet();

    // 2. List storage files under company prefix
    final prefix = 'entries/$companyId/';
    final storageFiles = await _client.storage
        .from(_bucket)
        .list(path: prefix);

    // 3. Recursively list entry subdirectories
    final allStoragePaths = <String>[];
    for (final dir in storageFiles) {
      if (dir.name.isEmpty) continue;
      final entryPrefix = '$prefix${dir.name}/';
      final files = await _client.storage
          .from(_bucket)
          .list(path: entryPrefix);
      for (final file in files) {
        if (file.name.isNotEmpty) {
          allStoragePaths.add('$entryPrefix${file.name}');
        }
      }
    }

    // 4. Diff: storage paths not in known local paths
    final orphans = allStoragePaths
        .where((path) => !knownPaths.contains(path))
        .toList();

    // 5. Filter by age > 24h (using file metadata if available)
    // Note: Supabase storage list returns metadata with created_at;
    // for simplicity, flag all orphans and let cleanup handle age check

    return orphans;
  }
}
```

### 1.5 Refactor `deleteByEntryId()` to Soft-Delete

The plan requires converting hard-delete `deleteByEntryId()` methods to soft-delete for four datasources. This ensures that when an entry is deleted, its children are soft-deleted (generating `operation='update'` change_log entries that push `deleted_at` to Supabase) instead of hard-deleted (which generates `operation='delete'` entries that bypass 30-day trash retention).

#### 1.5.1 PhotoLocalDatasource.deleteByEntryId()

**File**: `lib/features/photos/data/datasources/local/photo_local_datasource.dart`
**Line**: 42-49

**Before:**
```dart
Future<int> deleteByEntryId(String entryId) async {
  final database = await db.database;
  return database.delete(
    tableName,
    where: 'entry_id = ?',
    whereArgs: [entryId],
  );
}
```

**After:**
```dart
/// Soft-delete all photos for an entry.
///
/// Sets deleted_at/deleted_by instead of hard-deleting, so change_log
/// triggers generate 'update' operations that push deleted_at to Supabase
/// and honor 30-day trash retention.
Future<int> softDeleteByEntryId(String entryId, {String? userId}) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();
  return database.update(
    tableName,
    {
      'deleted_at': now,
      'deleted_by': userId,
      'updated_at': now,
    },
    where: 'entry_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId],
  );
}
```

**Also update all callers** — search for `deleteByEntryId` calls on photo datasource:
- `lib/features/photos/data/repositories/photo_repository.dart:125` — update call to `softDeleteByEntryId(entryId, userId: userId)`

#### 1.5.2 EntryEquipmentLocalDatasource.deleteByEntryId()

**File**: `lib/features/contractors/data/datasources/local/entry_equipment_local_datasource.dart`
**Line**: 70-77

**Before:**
```dart
Future<void> deleteByEntryId(String entryId) async {
  final database = await db.database;
  await database.delete(
    tableName,
    where: 'entry_id = ?',
    whereArgs: [entryId],
  );
}
```

**After:**
```dart
Future<void> softDeleteByEntryId(String entryId, {String? userId}) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();
  await database.update(
    tableName,
    {
      'deleted_at': now,
      'deleted_by': userId,
      'updated_at': now,
    },
    where: 'entry_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId],
  );
}
```

#### 1.5.3 EntryQuantityLocalDatasource.deleteByEntryId()

**File**: `lib/features/quantities/data/datasources/local/entry_quantity_local_datasource.dart`
**Line**: 81-87

**Before:**
```dart
Future<void> deleteByEntryId(String entryId) async {
  final database = await db.database;
  await database.delete(
    tableName,
    where: 'entry_id = ?',
    whereArgs: [entryId],
  );
}
```

**After:**
```dart
Future<void> softDeleteByEntryId(String entryId, {String? userId}) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();
  await database.update(
    tableName,
    {
      'deleted_at': now,
      'deleted_by': userId,
      'updated_at': now,
    },
    where: 'entry_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId],
  );
}
```

**Update callers:**
- `lib/features/quantities/data/repositories/entry_quantity_repository.dart:97` and `:141` — update to `softDeleteByEntryId`

#### 1.5.4 FormResponseLocalDatasource.deleteByEntryId()

**File**: `lib/features/forms/data/datasources/local/form_response_local_datasource.dart`
**Line**: 85-91

**Before:**
```dart
Future<void> deleteByEntryId(String entryId) async {
  final database = await db.database;
  await database.delete(
    tableName,
    where: 'entry_id = ?',
    whereArgs: [entryId],
  );
}
```

**After:**
```dart
Future<void> softDeleteByEntryId(String entryId, {String? userId}) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();
  await database.update(
    tableName,
    {
      'deleted_at': now,
      'deleted_by': userId,
      'updated_at': now,
    },
    where: 'entry_id = ? AND deleted_at IS NULL',
    whereArgs: [entryId],
  );
}
```

**Update callers:**
- `lib/features/forms/data/repositories/form_response_repository.dart:225` — update to `softDeleteByEntryId`

#### 1.5.5 saveForEntry() DELETE+re-INSERT Pattern

[CORRECTION] The plan mentions `deleteByEntryId()` refactoring but does not explicitly address the `saveForEntry()` DELETE+re-INSERT pattern that exists in:

- `lib/features/contractors/data/datasources/local/entry_personnel_local_datasource.dart:74-90` (entry_personnel table)
- `lib/features/contractors/data/datasources/local/entry_equipment_local_datasource.dart:80-96` (entry_equipment table)

These methods delete all records for an entry and re-insert, which with change_log triggers will generate N DELETE + M INSERT entries for what is logically a single "replace" operation. Phase 3 already addresses `entry_contractors_local_datasource.setForEntry()` with a diff-based approach. The same pattern should be applied here:

**For `entry_equipment_local_datasource.saveForEntry()`:**
1. Read existing records for the entry: `SELECT * FROM entry_equipment WHERE entry_id = ?`
2. Compute diff: which IDs are new (insert), which are removed (soft-delete), which are unchanged (skip)
3. Soft-delete removed records, insert new records, leave unchanged alone
4. This minimizes change_log entries and prevents data loss on network failure

**For `entry_personnel_local_datasource.saveForEntry()`:**
The `entry_personnel` table is a LEGACY table that is NOT synced (confirmed: no adapter, no triggers). The `saveForEntry()` method for this table can remain as-is since it only affects local data. However, the `saveCountsForEntryContractor()` and `saveAllCountsForEntry()` methods on the SAME datasource affect the `entry_personnel_counts` table, which IS synced. These methods also use DELETE+re-INSERT.

[CORRECTION] The plan says to delete `entry_personnel_local_datasource.dart` entirely in Phase 7c, but this file manages BOTH the legacy `entry_personnel` table AND the active `entry_personnel_counts` table. The file CANNOT be deleted. Instead:
- **Rename** the file to `entry_personnel_counts_local_datasource.dart`
- **Remove** only the `entry_personnel`-specific methods (getByEntryId, getByEntryAndContractor, upsert, deleteByEntryId, saveForEntry) — lines 28-90
- **Keep** all `entry_personnel_counts` methods (lines 92-213)
- **Refactor** `saveCountsForEntryContractor()` and `saveAllCountsForEntry()` to use diff-based approach instead of DELETE+re-INSERT

### 1.6 Wire Storage Cleanup and Orphan Scanner into SyncEngine

**File to modify**: `lib/features/sync/engine/sync_engine.dart`

After the push phase completes:
1. Run `StorageCleanup.cleanupExpiredPhotos()`
2. Orphan scanner is wired into the integrity check cycle (see Phase 5, Step 2.4)

### 1.7 Phase 4 Tests

All tests listed in the original plan:

| Test | Description |
|------|-------------|
| Three-phase success | upload -> metadata -> mark synced |
| Phase 1 failure -> retry re-uploads | File upload fails, next cycle re-uploads |
| Phase 2 failure -> file exists in storage -> retry metadata only | Metadata upsert fails, file already in storage |
| Phase 1+2 succeed, Phase 3 fails -> next cycle skips upload, upserts, marks | Local update fails, next cycle recovers |
| Soft-delete photo -> push -> remote has deleted_at | Soft-deleted photo pushed with deleted_at |
| Storage cleanup: 30-day-expired photos cleaned from bucket | Purged photo files cleaned from storage |
| Orphan detection: storage file with no DB row -> flagged | Orphaned file detected |
| deleteByEntryId() sets deleted_at instead of hard-deleting | Verify soft-delete behavior |
| deleteByEntryId() generates change_log UPDATE entries (not DELETE) | Verify trigger generates update operation |
| Soft-deleted photos pushed with deleted_at to Supabase | 30-day trash honored |

---

## Step 2: Phase 5 — Integrity Checker + Incremental Pull

**Agent**: `backend-data-layer-agent`
**Goal**: Wire incremental pull with per-table cursors into SyncEngine, integrate IntegrityChecker on 4-hour schedule, connect orphan scanner.

### 2.1 Incremental Pull Cursor Logic

**File to modify**: `lib/features/sync/engine/sync_engine.dart`

The pull phase of SyncEngine needs to use per-table cursors stored in `sync_metadata`.

**Implementation for each table's pull:**

```dart
Future<void> pullTable(String tableName, TableAdapter adapter) async {
  final cursor = await _getCursor(tableName);

  List<Map<String, dynamic>> remoteRecords;
  if (cursor == null) {
    // First sync / missing cursor: full pull for selected projects (Decision 4)
    remoteRecords = await adapter.pullFull(
      _client,
      projectFilter: await _getSyncedProjectIds(),
    );
  } else {
    // Incremental pull: WHERE updated_at > cursor - 5 seconds (clock skew margin)
    final safetyMargin = cursor.subtract(const Duration(seconds: 5));
    remoteRecords = await adapter.pullIncremental(
      _client,
      since: safetyMargin,
      projectFilter: await _getSyncedProjectIds(),
    );
  }

  // Suppress triggers during pull
  await _setSyncControlPulling(true);
  try {
    for (final record in remoteRecords) {
      final localRecord = await adapter.readLocal(record['id']);
      if (localRecord == null) {
        // New record — insert locally
        await adapter.insertLocal(adapter.convertForLocal(record));
      } else {
        // Existing record — use ConflictResolver (LWW)
        final resolution = _conflictResolver.resolve(
          localRecord: localRecord,
          remoteRecord: record,
          adapter: adapter,
        );
        await resolution.apply(adapter);
      }

      // Handle deletion notifications
      if (record['deleted_at'] != null) {
        final deletedBy = record['deleted_by'] as String?;
        if (deletedBy != null && deletedBy != _currentUserId) {
          await _createDeletionNotification(tableName, record);
        }
      }
    }

    // Advance cursor ONLY on complete successful pull
    if (remoteRecords.isNotEmpty) {
      final maxUpdatedAt = remoteRecords
          .map((r) => DateTime.parse(r['updated_at'] as String))
          .reduce((a, b) => a.isAfter(b) ? a : b);
      await _setCursor(tableName, maxUpdatedAt);
    }
  } finally {
    await _setSyncControlPulling(false);
  }
}
```

**Cursor management helpers:**

**File**: `lib/features/sync/engine/sync_engine.dart` (or extracted to a `cursor_manager.dart`)

```dart
Future<DateTime?> _getCursor(String tableName) async {
  final database = await _dbService.database;
  final result = await database.query(
    'sync_metadata',
    where: 'key = ?',
    whereArgs: ['last_pull_$tableName'],
  );
  if (result.isEmpty) return null;
  final value = result.first['value'] as String?;
  if (value == null || value.isEmpty) return null;
  return DateTime.parse(value);
}

Future<void> _setCursor(String tableName, DateTime cursor) async {
  final database = await _dbService.database;
  await database.rawInsert('''
    INSERT OR REPLACE INTO sync_metadata (key, value)
    VALUES (?, ?)
  ''', ['last_pull_$tableName', cursor.toUtc().toIso8601String()]);
}

Future<List<String>> _getSyncedProjectIds() async {
  final database = await _dbService.database;
  final result = await database.query('synced_projects', columns: ['project_id']);
  return result.map((r) => r['project_id'] as String).toList();
}
```

### 2.2 TableAdapter Pull Methods

**File to modify**: `lib/features/sync/engine/adapters/table_adapter.dart` (base class)

Add two pull methods:

```dart
/// Full pull — first sync or cursor reset.
/// Scoped to selected projects via synced_projects.
Future<List<Map<String, dynamic>>> pullFull(
  SupabaseClient client, {
  required List<String> projectFilter,
});

/// Incremental pull — only records updated since `since` timestamp.
Future<List<Map<String, dynamic>>> pullIncremental(
  SupabaseClient client, {
  required DateTime since,
  required List<String> projectFilter,
});
```

Each table adapter overrides these with the appropriate Supabase query. Project-scoped tables filter by `project_id IN (...)`. Company-scoped tables (like projects itself) filter by company_id.

### 2.3 IntegrityChecker Integration

**File to modify**: `lib/features/sync/engine/integrity_checker.dart` (created in Phase 2)

Wire the IntegrityChecker to run every 4 hours via the existing BackgroundSyncHandler schedule (which already fires every 4 hours).

**File to modify**: `lib/features/sync/engine/sync_engine.dart`

Add an integrity check step that runs when the last check was > 4 hours ago:

```dart
Future<void> runIntegrityCheckIfDue() async {
  final lastCheck = await _getMetadata('last_integrity_check');
  final lastCheckTime = lastCheck != null ? DateTime.parse(lastCheck) : null;

  if (lastCheckTime != null &&
      DateTime.now().difference(lastCheckTime) < const Duration(hours: 4)) {
    return; // Not due yet
  }

  final results = await _integrityChecker.check(_client, _dbService);

  for (final result in results) {
    if (result.hasDrift) {
      // Reset cursor for this table — next pull will be a full pull
      await _clearCursor(result.tableName);
      // Store result for UI
      await _storeIntegrityResult(result);
    }
  }

  await _setMetadata('last_integrity_check', DateTime.now().toUtc().toIso8601String());
}
```

The IntegrityChecker calls the `get_table_integrity()` Supabase RPC (created in Phase 0) which returns:
- `record_count` — number of non-deleted records
- `max_updated_at` — latest updated_at timestamp
- `id_checksum` — MD5 of sorted IDs

It compares these against local SQLite values. Any mismatch triggers a cursor reset for that table.

### 2.4 Wire Orphan Scanner into Integrity Check Cycle

**File to modify**: `lib/features/sync/engine/sync_engine.dart`

After integrity check completes, run the orphan scanner:

```dart
Future<void> runIntegrityCheckIfDue() async {
  // ... existing integrity check logic ...

  // Run orphan scanner as part of integrity cycle
  final orphans = await _orphanScanner.scan(_companyId);
  if (orphans.isNotEmpty) {
    await _storeMetadata('orphan_count', orphans.length.toString());
    // Log orphans but do not auto-delete — manual review required
  }
}
```

### 2.5 Surface Integrity Results in sync_metadata

**File to modify**: `lib/features/sync/engine/sync_engine.dart`

Store per-table integrity results so the Sync Dashboard UI (Phase 6) can display them:

```dart
Future<void> _storeIntegrityResult(IntegrityResult result) async {
  final database = await _dbService.database;
  await database.rawInsert('''
    INSERT OR REPLACE INTO sync_metadata (key, value)
    VALUES (?, ?)
  ''', [
    'integrity_${result.tableName}',
    jsonEncode({
      'checked_at': DateTime.now().toUtc().toIso8601String(),
      'has_drift': result.hasDrift,
      'local_count': result.localCount,
      'remote_count': result.remoteCount,
      'drift_type': result.driftType?.name,
    }),
  ]);
}
```

### 2.6 Phase 5 Tests

| Test | Description |
|------|-------------|
| Incremental pull: only fetches records newer than cursor minus 5s margin | Verify WHERE clause |
| Deduplication: records within safety margin overlap are not re-inserted | Upsert handles duplicates |
| Full pull on first sync (cursor is null) — scoped to synced_projects | Verify project filter |
| Cursor advances after successful pull | Cursor stored in sync_metadata |
| Cursor NOT updated for incomplete tables during interrupted first sync | Verify cursor safety |
| Integrity check: injected count drift -> detected -> cursor reset | Count mismatch triggers reset |
| Integrity check: injected checksum drift -> detected -> cursor reset | Checksum mismatch triggers reset |
| Integrity check: no drift -> passes -> no re-pull | Clean tables not disturbed |
| Integrity check result stored and retrievable | sync_metadata has result |

---

## Step 3: Phase 6 — UI + Settings Redesign + Profile Expansion

**Agent**: `frontend-flutter-specialist-agent`
**Goal**: Replace SyncStatusBanner with SyncStatusIcon, create Sync Dashboard and Conflict Viewer screens, restructure Settings screen, migrate profile reads from PreferencesService to AuthProvider, fix GAP-17 and GAP-18.

### 3.1 SyncStatusIcon Widget

**File to create**: `lib/features/sync/presentation/widgets/sync_status_icon.dart`

Replaces `SyncStatusBanner`. A compact app bar icon with color coding:
- Green: all synced, no pending changes
- Yellow: sync in progress or pending changes
- Red: sync error or offline with pending changes

```dart
class SyncStatusIcon extends StatelessWidget {
  const SyncStatusIcon({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<SyncProvider>(
      builder: (context, syncProvider, _) {
        final color = _getColor(syncProvider);
        final icon = _getIcon(syncProvider);
        return IconButton(
          key: TestingKeys.syncStatusIndicator,
          icon: Icon(icon, color: color, size: 20),
          onPressed: () => context.push('/sync/dashboard'),
          tooltip: _getTooltip(syncProvider),
        );
      },
    );
  }

  Color _getColor(SyncProvider provider) {
    if (provider.hasErrors) return Colors.red;
    if (provider.isSyncing || provider.hasPendingChanges) return Colors.amber;
    return Colors.green;
  }

  IconData _getIcon(SyncProvider provider) {
    if (provider.hasErrors) return Icons.sync_problem;
    if (provider.isSyncing) return Icons.sync;
    return Icons.cloud_done;
  }

  String _getTooltip(SyncProvider provider) {
    if (provider.hasErrors) return 'Sync error';
    if (provider.isSyncing) return 'Syncing...';
    if (provider.hasPendingChanges) return 'Changes pending';
    return 'All synced';
  }
}
```

### 3.2 Toast Notifications on Sync Failure

**File to modify**: `lib/features/sync/presentation/providers/sync_provider.dart`

Add a toast notification when sync fails. Use a `GlobalKey<ScaffoldMessengerState>` or an overlay-based approach:

```dart
void _onSyncStatusChanged(SyncStatus status) {
  if (status == SyncStatus.error && _lastError != null) {
    _showSyncErrorToast(_lastError!);
  }
  notifyListeners();
}
```

### 3.3 SyncDashboardScreen

**File to create**: `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`

Route: `/sync/dashboard`

Content:
- Per-table health cards (pending count, last sync time, last integrity check result)
- Recent activity log (last N sync operations from sync_metadata)
- Pending/failed counts summary
- Integrity check results (from sync_metadata `integrity_{table}` entries)
- Manual sync button
- Link to Conflict Viewer

**Register route** in `lib/core/router/app_router.dart`.

### 3.4 ConflictViewerScreen

**File to create**: `lib/features/sync/presentation/screens/conflict_viewer_screen.dart`

Route: `/sync/conflicts`

Content:
- List of conflict_log entries (not yet dismissed)
- Each row shows: table, record name, detected_at, conflict type
- Tap to expand: shows lost_data JSON
- Actions per conflict:
  - **Dismiss**: sets `dismissed_at` on the conflict_log entry
  - **Restore**: reads lost_data, reads current record, merges, validates via `adapter.validate()`, updates SQLite, marks dismissed

**Restore flow implementation:**
```dart
Future<void> restoreConflict(ConflictLogEntry conflict) async {
  final adapter = _syncRegistry.getAdapter(conflict.tableName);
  final lostData = jsonDecode(conflict.lostData) as Map<String, dynamic>;

  // Read current record
  final currentRecord = await adapter.readLocal(conflict.recordId);
  if (currentRecord == null) {
    // Record was purged — cannot restore
    _showError('This record has been permanently deleted and cannot be restored.');
    return;
  }

  // Merge lost_data into current record
  final merged = {...currentRecord, ...lostData};

  // Validate
  final validationResult = adapter.validate(merged);
  if (!validationResult.isValid) {
    _showError('Cannot restore: ${validationResult.errors.join(", ")}');
    return;
  }

  // Apply
  await adapter.updateLocal(conflict.recordId, merged);

  // Mark dismissed
  await _markDismissed(conflict.id);
}
```

### 3.5 ProjectSelectionScreen

**File to create**: `lib/features/sync/presentation/screens/project_selection_screen.dart`

Route: `/sync/project-selection`

Content:
- Queries Supabase directly for all projects in the user's company
- Search bar to filter projects
- Tap to add/remove from local `synced_projects` table
- Already-synced projects are visually marked (checkmark)

### 3.6 DeletionNotificationBanner

**File to keep**: `lib/features/sync/presentation/widgets/deletion_notification_banner.dart`

Wire to new engine's `deletion_notifications` table. The banner already exists; update its data source to read from the `deletion_notifications` table populated by the new SyncEngine pull flow (instead of whatever legacy mechanism it used).

### 3.7 Fix GAP-17: getDatesWithEntries Missing deleted_at Filter

**File**: `lib/features/entries/data/datasources/local/daily_entry_local_datasource.dart`
**Line**: 80-89

**Before:**
```dart
final maps = await database.rawQuery(
  'SELECT DISTINCT date FROM $tableName WHERE project_id = ? ORDER BY date DESC',
  [projectId],
);
```

**After:**
```dart
final maps = await database.rawQuery(
  'SELECT DISTINCT date FROM $tableName WHERE project_id = ? AND deleted_at IS NULL ORDER BY date DESC',
  [projectId],
);
```

### 3.8 Fix GAP-18: location_local_datasource.search() Missing deleted_at Filter

**File**: `lib/features/locations/data/datasources/local/location_local_datasource.dart`
**Line**: 28-34

**Before:**
```dart
Future<List<Location>> search(String projectId, String query) async {
  final searchPattern = '%$query%';
  return getWhere(
    where: 'project_id = ? AND (name LIKE ? OR station LIKE ?)',
    whereArgs: [projectId, searchPattern, searchPattern],
  );
}
```

**After:**
```dart
Future<List<Location>> search(String projectId, String query) async {
  final searchPattern = '%$query%';
  return getWhere(
    where: 'project_id = ? AND (name LIKE ? OR station LIKE ?) AND deleted_at IS NULL',
    whereArgs: [projectId, searchPattern, searchPattern],
  );
}
```

### 3.9 Settings Redesign

**File to modify**: `lib/features/settings/presentation/screens/settings_screen.dart`

#### 3.9.1 Restructure Sections

New section order:
1. **Account** — Display Name (read-only from AuthProvider), Email (read-only), Edit Profile link, Sign Out
2. **Sync & Data** — Sync Dashboard link, Manage Synced Projects link, Trash link, Clear Cache
3. **Form Settings** — Company Template (read-only), Gauge Number (editable, persists to user_profiles), Initials (editable, auto-derived from displayName, manually overridable)
4. **Appearance** — Theme selector, Auto-Load toggle (from ProjectSettingsProvider)
5. **About** — Version, Licenses

#### 3.9.2 Remove Dead Toggles

Remove from `_SettingsScreenState`:
- `_autoFetchWeather` field and `_toggleAutoFetchWeather()` method
- `_autoSyncWifi` field and `_toggleAutoSyncWifi()` method
- `_autoFillEnabled` field and `_toggleAutoFillEnabled()` method
- `_useLastValues` field and `_toggleUseLastValues()` method

Remove from build():
- Auto-fill enabled toggle widget
- Use last values toggle widget
- Auto-sync on WiFi toggle widget
- Auto-fetch weather toggle widget

#### 3.9.3 Remove Dead Stubs

Remove from build():
- Backup Data tile (with snackbar stub)
- Restore Data tile (with snackbar stub)
- Help & Support tile (with snackbar stub)

#### 3.9.4 Remove Duplicate

Remove "Default Signature Name" tile if it duplicates profile name display.

#### 3.9.5 Remove Unactionable Displays

Remove Weather API tile (display-only, non-configurable).

#### 3.9.6 Move Company Template

Move Company Template read-only info tile from current location to the Form Settings section.

#### 3.9.7 Add Gauge Number Field

In Form Settings section, add an editable ListTile for Gauge Number:
- Reads from `AuthProvider.userProfile.gaugeNumber`
- On edit, updates `user_profiles.gauge_number` in Supabase
- No PreferencesService fallback (Decision 12)

#### 3.9.8 Add Initials Field

In Form Settings section, add an editable ListTile for Initials:
- Auto-derived from displayName (first letter of each word)
- Manually overridable
- Reads from `AuthProvider.userProfile.initials`
- On edit, updates `user_profiles.initials` in Supabase

#### 3.9.9 Keep Auto-Load Toggle

In APPEARANCE section, keep the Auto-Load toggle from ProjectSettingsProvider.

#### 3.9.10 Delete EditInspectorDialog Widget

**File to delete**: `lib/features/settings/presentation/widgets/edit_inspector_dialog.dart`

This widget is orphaned (zero call sites). Delete it.

**Also update barrel export**: `lib/features/settings/presentation/widgets/widgets.dart` — remove the export line for `edit_inspector_dialog.dart`.

#### 3.9.11 Remove Dead Pref Keys

These keys will be cleaned up in Phase 7g (PreferencesService Cleanup). For now, the settings screen simply stops reading them.

### 3.10 Migrate Form Auto-Fill Reads

**Decision 12**: All form auto-fill reads come from `AuthProvider.userProfile`. No fallback to PreferencesService.

#### 3.10.1 Fix entry_photos_section.dart

**File**: `lib/features/entries/presentation/widgets/entry_photos_section.dart`
**Line**: 88

**Before:**
```dart
final initials = prefs.getString('inspector_initials') ?? 'XX';
```

**After:**
```dart
final authProvider = context.read<AuthProvider>();
final initials = authProvider.userProfile?.initials ?? 'XX';
```

Remove the `SharedPreferences` import and `prefs` variable if no longer needed.

#### 3.10.2 Fix pdf_data_builder.dart

**File**: `lib/features/entries/presentation/controllers/pdf_data_builder.dart`
**Lines**: 130, 134

**Before:**
```dart
inspectorName = prefs.getString('inspector_name') ?? 'Inspector';
// ... (line 134 similar)
inspectorName = prefs.getString('inspector_name') ?? 'Inspector';
```

**After:**
```dart
inspectorName = authProvider.userProfile?.displayName ?? 'Inspector';
// ... (line 134 similar)
inspectorName = authProvider.userProfile?.displayName ?? 'Inspector';
```

The pdf_data_builder needs to receive the AuthProvider (or the userProfile directly) as a constructor parameter instead of using SharedPreferences.

#### 3.10.3 Fix form_response_repository.dart

**File**: `lib/features/forms/data/repositories/form_response_repository.dart`
**Line**: 385

**Before:**
```dart
requireHeader('cert_number', 'cert_number');
```

Ensure the auto-fill pipeline resolves `cert_number` from `user_certifications` via AuthProvider, not from PreferencesService. The `requireHeader` call itself may not need to change — the data source it reads from needs to be updated to point to `AuthProvider.userProfile.certifications` or a query to the local `user_certifications` table.

### 3.11 PII Cleanup from SharedPreferences

**File to modify**: `lib/main.dart` (or `lib/features/auth/services/auth_service.dart`)

On first launch after update, delete all legacy PII keys from SharedPreferences:

```dart
Future<void> _cleanupLegacyPiiKeys() async {
  final prefs = await SharedPreferences.getInstance();
  final migrated = prefs.getBool('pii_migrated_to_user_profiles') ?? false;
  if (migrated) return;

  // Delete legacy PII keys
  final keysToDelete = [
    'inspector_name', 'inspector_initials', 'inspector_phone',
    'inspector_cert_number', 'inspector_agency', 'gauge_number',
  ];
  for (final key in keysToDelete) {
    await prefs.remove(key);
  }

  await prefs.setBool('pii_migrated_to_user_profiles', true);
}
```

### 3.12 Edit Profile Screen Updates

**File to modify**: `lib/features/settings/presentation/screens/edit_profile_screen.dart`

Update to show/edit:
- `displayName` (editable)
- `email` (read-only)
- `agency` (editable)
- `initials` (editable, with auto-derive option)
- `phone` (editable)

All reads/writes go through AuthProvider -> user_profiles (Supabase).

### 3.13 Wire UserProfileSyncDatasource for user_certifications

**File to modify**: `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart`

Ensure that when user profiles are synced, the `user_certifications` table is also synced (pull certifications for the current user).

### 3.14 Conflict Log Auto-Cleanup

**File to modify**: `lib/features/sync/engine/sync_engine.dart`

Add cleanup step in sync cycle: auto-dismiss conflicts older than 30 days.

```dart
Future<void> _cleanupExpiredConflicts() async {
  final database = await _dbService.database;
  final thirtyDaysAgo = DateTime.now().subtract(const Duration(days: 30)).toUtc().toIso8601String();
  await database.update(
    'conflict_log',
    {'dismissed_at': DateTime.now().toUtc().toIso8601String()},
    where: 'dismissed_at IS NULL AND detected_at < ?',
    whereArgs: [thirtyDaysAgo],
  );
}
```

### 3.15 Phase 6 Tests

| Test | Description |
|------|-------------|
| Widget: settings sections render in correct order | Account, Sync & Data, Form Settings, Appearance, About |
| Widget: dead items are gone | No auto-fill, use-last-values, auto-sync, auto-weather toggles |
| Widget: gauge number field editable, persists to user_profiles | Not PreferencesService |
| Widget: initials field editable, persists to user_profiles | Auto-derive or manual |
| Widget: Auto-Load toggle present in APPEARANCE | From ProjectSettingsProvider |
| Widget: Manage Synced Projects link present | In Sync & Data section |
| Widget: sync icon colors match state | Green/yellow/red |
| Widget: sync dashboard shows correct per-table data | Health cards |
| Widget: conflict viewer shows lost data | JSON display |
| Widget: conflict viewer restore runs validate() — valid succeeds | Happy path |
| Widget: conflict viewer restore with invalid data shows error | Validation error |
| Widget: conflict viewer restore on purged record shows "permanently deleted" | Record gone |
| Widget: project selection screen lists projects from Supabase | Direct query |
| Widget: project selection search filters results | Search works |
| Integration: form auto-fill reads from userProfile (no prefs fallback) | Decision 12 |

---

## Step 4: Phase 7 — Cutover + Cleanup

**Cutover strategy (Decision 10)**: Big Bang. The new engine is built entirely on the feature branch. The old SyncService remains functional throughout Phases 0-6. When Phase 7 is complete and all tests pass, the old code is deleted and the branch is merged. No dual-write period. No feature flag. Git history is the rollback mechanism.

### 4.0 Phase 7 Prerequisites

Before starting Phase 7:
- All Phase 6 tests pass
- New SyncEngine is fully functional with all 16 table adapters
- All new UI screens are implemented and tested

### 4.0.1 Wire New SyncEngine into App Lifecycle

**File to modify**: `lib/main.dart`

Replace old SyncService initialization with new SyncEngine:
- Remove `SyncService` creation
- Create `SyncEngine` with `DatabaseService` and `SupabaseClient`
- Register all table adapters via `SyncRegistry`
- Provide `SyncEngine` to the widget tree

**File to modify**: `lib/features/sync/application/sync_orchestrator.dart`

Update `SyncOrchestrator` to delegate to new SyncEngine instead of old SupabaseSyncAdapter/SyncService:
- Replace `_localAgencyAdapter` (which wraps old SyncService) with new SyncEngine
- Update `syncLocalAgencyProjects()` to call `SyncEngine.sync()`
- Remove dependency on `SupabaseSyncAdapter`

**File to modify**: `lib/features/sync/presentation/providers/sync_provider.dart`

Update `SyncProvider` to read state from new SyncEngine:
- Status from SyncEngine (not old adapter status)
- Pending count from change_log (not sync_queue)
- Last sync time from sync_metadata

**File to modify**: `lib/features/sync/application/background_sync_handler.dart`

Update `backgroundSyncCallback()` and `_performDesktopSync()`:
- Replace `SyncService(db)` with new SyncEngine instantiation
- SyncEngine uses SQLite advisory lock (sync_lock table), so concurrent foreground/background sync is prevented automatically

**Before (line 76-79 of background_sync_handler.dart):**
```dart
final syncService = SyncService(db);
syncService.setCompanyContext(companyId: companyId, userId: userId);
final result = await syncService.syncAll();
```

**After:**
```dart
final engine = SyncEngine(db, Supabase.instance.client, companyId: companyId, userId: userId);
// Advisory lock prevents concurrent foreground sync
final result = await engine.sync();
```

Same change for `_performDesktopSync()` (lines 195-198).

### 4.0.2 Verify SyncLifecycleManager

**File**: `lib/features/sync/application/sync_lifecycle_manager.dart`

This file calls `_syncOrchestrator.syncLocalAgencyProjects()` and `_syncOrchestrator.lastSyncTime`. Since we updated the orchestrator in 4.0.1, verify these methods still work. The SyncLifecycleManager itself does not need changes — it delegates to the orchestrator.

### 4.0.3 FcmHandler Verification

[CORRECTION] The plan says "Verify `FcmHandler` is a no-op stub — confirm it does not call old SyncService methods." This is WRONG. `FcmHandler` is a full 104-line Firebase Messaging implementation at `lib/features/sync/application/fcm_handler.dart`. It:
- Initializes Firebase Messaging on Android/iOS
- Requests notification permissions
- Saves FCM token to Supabase via `AuthService.saveFcmToken()`
- Registers background and foreground message handlers
- Foreground `daily_sync` messages are acknowledged but ignored (sync handled by WorkManager)

**FcmHandler does NOT call old SyncService methods.** It only calls `AuthService.saveFcmToken()` and prints debug messages. No changes needed for FcmHandler. The plan's claim that it is a "no-op stub" is incorrect, but the conclusion (no action needed) is still correct — it has no dependency on the old sync system.

### 4.0.4 Update MockSyncAdapter

**File to modify**: `lib/features/sync/data/adapters/mock_sync_adapter.dart`

Update `MockSyncAdapter` to implement the new engine interfaces used for test mode. The mock adapter currently implements `SyncAdapter` which includes `queueOperation()`, `markProjectSynced()`, `markEntrySynced()`, `markPhotoSynced()`, and the old `sync()` method.

After Phase 7, these will be removed. The mock adapter needs to implement whatever interface the new SyncEngine exposes for test mode. If the SyncOrchestrator still uses mock detection, update the mock to implement the new adapter interface.

### 4.0.5 Drain Accumulated change_log

On first sync after wiring the new engine, process ALL accumulated change_log entries (which have been building up since Phase 1 installed triggers). The SyncEngine's normal push flow handles this automatically — `ChangeTracker` reads unprocessed entries from change_log.

No special code needed, but add a log message:
```dart
final pendingCount = await _changeTracker.getUnprocessedCount();
if (pendingCount > 0) {
  debugPrint('[SYNC_ENGINE] Draining $pendingCount accumulated change_log entries');
}
```

---

### 4.1 Phase 7a: Model & Enum Cleanup

#### 4.1.1 Remove syncStatus from DailyEntry Model

**File**: `lib/features/entries/data/models/daily_entry.dart`

**Remove field declaration (line 29):**
```dart
// DELETE: final SyncStatus syncStatus;
```

**Remove import (line 2):**
```dart
// DELETE: import 'package:construction_inspector/shared/models/sync_status.dart';
```

**Remove constructor parameter (line 58):**
```dart
// DELETE: this.syncStatus = SyncStatus.pending,
```

**Remove copyWith parameter (line 82):**
```dart
// DELETE: SyncStatus? syncStatus,
```

**Remove copyWith body reference (line 107):**
```dart
// DELETE: syncStatus: syncStatus ?? this.syncStatus,
```

**Remove from toMap() (line 135):**
```dart
// DELETE: 'sync_status': syncStatus.toJson(),
```

**Remove from fromMap() (line 190):**
```dart
// DELETE: syncStatus: SyncStatus.fromJson(map['sync_status'] as String?),
```

#### 4.1.2 Remove syncStatus from Photo Model

**File**: `lib/features/photos/data/models/photo.dart`

**Remove import (line 2):**
```dart
// DELETE: import 'package:construction_inspector/shared/models/sync_status.dart';
```

**Remove field declaration (line 17):**
```dart
// DELETE: final SyncStatus syncStatus;
```

**Remove constructor parameter (line 37):**
```dart
// DELETE: this.syncStatus = SyncStatus.pending,
```

**Remove copyWith parameter (line 60):**
```dart
// DELETE: SyncStatus? syncStatus,
```

**Remove copyWith body reference (line 76):**
```dart
// DELETE: syncStatus: syncStatus ?? this.syncStatus,
```

**Remove from toMap() (line 97):**
```dart
// DELETE: 'sync_status': syncStatus.toJson(),
```

**Remove from fromMap() (line 118):**
```dart
// DELETE: syncStatus: SyncStatus.fromJson(map['sync_status'] as String?),
```

#### 4.1.3 Delete SyncStatus Enum File

**File to delete**: `lib/shared/models/sync_status.dart`

Remove the entire file (32 lines).

**Update barrel exports** — find and remove `export 'sync_status.dart'` from:
- `lib/shared/models/models.dart` (or wherever it's exported)
- `lib/shared/shared.dart` (if re-exported)

#### 4.1.4 Remove getSyncStatusColor()

**File**: `lib/core/theme/colors.dart`
**Lines**: 172-183

**Delete:**
```dart
static Color getSyncStatusColor(String status) {
  switch (status.toLowerCase()) {
    case 'pending':
      return statusWarning;
    case 'synced':
      return statusSuccess;
    case 'error':
      return statusError;
    default:
      return textSecondary;
  }
}
```

**File**: `lib/core/theme/app_theme.dart`
**Line**: 1540

**Delete:**
```dart
static Color getSyncStatusColor(String status) => AppColors.getSyncStatusColor(status);
```

#### 4.1.5 Clean Up Remaining sync_status References in Datasources

**File**: `lib/features/entries/data/datasources/remote/daily_entry_remote_datasource.dart`
**Line**: 17

**Delete:**
```dart
map.remove('sync_status'); // BLOCKER-27: local-only field
```

This line is no longer needed because `DailyEntry.toMap()` will no longer include `sync_status`.

**File**: `lib/features/photos/data/datasources/remote/photo_remote_datasource.dart`
**Line**: 21

**Delete:**
```dart
map.remove('sync_status'); // BLOCKER-27: local-only field
```

Same reason — `Photo.toMap()` will no longer include `sync_status`.

**File**: `lib/features/entries/data/repositories/daily_entry_repository.dart`
**Line**: 235

**Before:**
```dart
'sync_status': 'pending',
```

**Delete this line.** The batch submit operation no longer needs to set sync_status — the change_log trigger handles tracking.

**Also remove import** of `sync_status.dart` from this file (line 2).

**File**: `lib/features/entries/data/datasources/local/daily_entry_local_datasource.dart`

**Line 73 — delete `getPendingSync()` method entirely (lines 71-77):**
```dart
// DELETE entire method - replaced by change_log
Future<List<DailyEntry>> getPendingSync() async {
  return getWhere(
    where: "sync_status != 'synced'",
    whereArgs: [],
    orderBy: 'updated_at ASC',
  );
}
```

**Line 93 — delete `updateSyncStatus()` method entirely (lines 93-104):**
```dart
// DELETE entire method - replaced by change_log
Future<void> updateSyncStatus(String id, String status) async { ... }
```

**Line 107 — update `updateStatus()` method (lines 107-119):**

[CORRECTION] The plan says `daily_entry_local_datasource.updateStatus()` "also handles entry status (needs refactoring, not deletion)." This is correct. The method updates the entry's `status` field (draft/submitted) and currently also sets `sync_status: 'pending'`. Remove only the sync_status line:

**Before:**
```dart
Future<void> updateStatus(String id, EntryStatus status) async {
  final database = await db.database;
  await database.update(
    tableName,
    {
      'status': status.name,
      'updated_at': DateTime.now().toIso8601String(),
      'sync_status': 'pending',
    },
    where: 'id = ?',
    whereArgs: [id],
  );
}
```

**After:**
```dart
Future<void> updateStatus(String id, EntryStatus status) async {
  final database = await db.database;
  await database.update(
    tableName,
    {
      'status': status.name,
      'updated_at': DateTime.now().toIso8601String(),
    },
    where: 'id = ?',
    whereArgs: [id],
  );
}
```

---

### 4.2 Phase 7b: Auth & Sign-Out Cleanup

**File**: `lib/features/auth/services/auth_service.dart`

**Line 328** — Currently in `clearLocalCompanyData()`, the tables list includes `'sync_queue'`. Replace with new engine tables.

**Before (lines 315-331):**
```dart
final tables = [
  'daily_entries', 'photos', 'entry_equipment',
  'entry_quantities', 'entry_personnel', 'entry_personnel_counts',
  'entry_contractors',
  'contractors', 'equipment', 'bid_items',
  'personnel_types',
  'locations',
  'inspector_forms',
  'projects',
  'user_profiles',
  'companies',
  'company_join_requests',
  'sync_queue',
  'stage_metrics',
  'extraction_metrics',
];
```

**After:**
```dart
final tables = [
  'daily_entries', 'photos', 'entry_equipment',
  'entry_quantities', 'entry_personnel', 'entry_personnel_counts',
  'entry_contractors',
  'contractors', 'equipment', 'bid_items',
  'personnel_types',
  'locations',
  'inspector_forms',
  'projects',
  'user_profiles',
  'companies',
  'company_join_requests',
  // New sync engine tables (replaces sync_queue)
  'change_log',
  'conflict_log',
  'sync_lock',
  'sync_metadata',
  'synced_projects',
  // Metrics tables
  'stage_metrics',
  'extraction_metrics',
];
```

---

### 4.3 Phase 7c: entry_personnel Legacy Cleanup

[CORRECTION] The plan says to delete `entry_personnel_local_datasource.dart` entirely, but this file manages BOTH the legacy `entry_personnel` table AND the active `entry_personnel_counts` table. The file CANNOT simply be deleted.

#### 4.3.1 Split the Datasource File

**File**: `lib/features/contractors/data/datasources/local/entry_personnel_local_datasource.dart`

**Step 1**: Create new file for entry_personnel_counts only:

**File to create**: `lib/features/contractors/data/datasources/local/entry_personnel_counts_local_datasource.dart`

Move lines 92-213 (all `entry_personnel_counts` methods) into a new class `EntryPersonnelCountsLocalDatasource`:

```dart
import 'package:construction_inspector/core/database/database_service.dart';

/// Local SQLite datasource for entry_personnel_counts.
///
/// Manages dynamic personnel type counts per entry/contractor.
class EntryPersonnelCountsLocalDatasource {
  final DatabaseService db;
  static const String _countsTable = 'entry_personnel_counts';

  EntryPersonnelCountsLocalDatasource(this.db);

  // ... move all entry_personnel_counts methods here (getCountsByEntryId,
  // saveCountsForEntryContractor, saveAllCountsForEntry, deleteCountsByEntryId,
  // getTotalCountForEntry) ...
}
```

**Step 2**: Update all imports that use `EntryPersonnelLocalDatasource` for counts methods.

Search for imports of `entry_personnel_local_datasource.dart`:
```
lib/features/entries/presentation/controllers/contractor_editing_controller.dart
```
This file uses `_personnelDatasource.saveCountsForEntryContractor()` — update import to new file and class name.

**Step 3**: Delete `entry_personnel_local_datasource.dart`

After extracting counts methods, the remaining `entry_personnel` methods are dead code (the legacy table has no adapter, no triggers, no Supabase sync). Delete the original file.

#### 4.3.2 Delete entry_personnel_remote_datasource.dart

**File to delete**: `lib/features/contractors/data/datasources/remote/entry_personnel_remote_datasource.dart`

This 32-line file is dead code — the entry_personnel table is not synced.

#### 4.3.3 Update Barrel Exports

**File**: `lib/features/contractors/data/datasources/local/local_datasources.dart`

**Before:**
```dart
export 'entry_personnel_local_datasource.dart';
```

**After:**
```dart
export 'entry_personnel_counts_local_datasource.dart';
```

**File**: `lib/features/contractors/data/datasources/remote/remote_datasources.dart`

**Remove:**
```dart
export 'entry_personnel_remote_datasource.dart';
```

#### 4.3.4 Remove entry_personnel from SoftDeleteService Cascade Lists

**File**: `lib/services/soft_delete_service.dart`

**Line 18** — `_childToParentOrder` list: Remove `'entry_personnel'` (keep `'entry_personnel_counts'`).

**Line 83** — `cascadeSoftDeleteEntry()` entryChildTables list: Remove `'entry_personnel'` (keep `'entry_personnel_counts'`).

**Line 121** (or wherever `cascadeRestoreEntry` is) — Remove `'entry_personnel'` from restore list (keep `'entry_personnel_counts'`).

---

### 4.4 Phase 7d: Seed Data & Test Harness

#### 4.4.1 Remove sync_status from Seed Data

**File**: `lib/core/database/seed_data_service.dart`
**Line**: 381

**Delete:**
```dart
'sync_status': 'synced',
```

The daily_entries table will no longer have a `sync_status` column after migration v31.

#### 4.4.2 Migrate cert_number in Test Harness Seed

**File**: `lib/test_harness/harness_seed_data.dart`
**Line**: 230

**Before:**
```dart
'cert_number': 'CERT-001',
```

**After:** Replace with a `user_certifications` seed entry (cert_number is now in the separate user_certifications table, not user_profiles or SharedPreferences).

Add to the seed data function:
```dart
await database.insert('user_certifications', {
  'id': 'cert-seed-001',
  'user_id': seedUserId,
  'cert_type': 'primary',
  'cert_number': 'CERT-001',
  'created_at': now,
  'updated_at': now,
});
```

And remove the `'cert_number'` key from whatever map it was in (likely a user_profiles seed entry).

#### 4.4.3 Remove sync_status from Test Harness Seed

Search `lib/test_harness/harness_seed_data.dart` for any `sync_status` references and remove them.

---

### 4.5 Phase 7e: Schema Verifier Cleanup

**File**: `lib/core/database/schema_verifier.dart`

#### 4.5.1 Remove sync_status from daily_entries Column List

**Line 64:**

**Before:**
```dart
'daily_entries': [
  'id', 'project_id', 'location_id', 'date', 'weather',
  'temp_low', 'temp_high', 'activities', 'site_safety', 'sesc_measures',
  'traffic_control', 'visitors', 'extras_overruns', 'signature', 'signed_at',
  'status', 'submitted_at', 'revision_number',
  'created_at', 'updated_at', 'sync_status',
  'created_by_user_id', 'updated_by_user_id',
  'deleted_at', 'deleted_by',
],
```

**After:**
```dart
'daily_entries': [
  'id', 'project_id', 'location_id', 'date', 'weather',
  'temp_low', 'temp_high', 'activities', 'site_safety', 'sesc_measures',
  'traffic_control', 'visitors', 'extras_overruns', 'signature', 'signed_at',
  'status', 'submitted_at', 'revision_number',
  'created_at', 'updated_at',
  'created_by_user_id', 'updated_by_user_id',
  'deleted_at', 'deleted_by',
],
```

#### 4.5.2 Remove sync_status from photos Column List

**Line 114:**

**Before:**
```dart
'photos': [
  'id', 'entry_id', 'project_id', 'file_path', 'filename',
  'remote_path', 'notes', 'caption', 'location_id',
  'latitude', 'longitude', 'captured_at', 'sync_status',
  'created_at', 'updated_at', 'created_by_user_id',
  'deleted_at', 'deleted_by',
],
```

**After:**
```dart
'photos': [
  'id', 'entry_id', 'project_id', 'file_path', 'filename',
  'remote_path', 'notes', 'caption', 'location_id',
  'latitude', 'longitude', 'captured_at',
  'created_at', 'updated_at', 'created_by_user_id',
  'deleted_at', 'deleted_by',
],
```

#### 4.5.3 Remove sync_status from Self-Heal Definitions

**Line 188:**

**Before (daily_entries self-heal):**
```dart
'daily_entries': {
  ...
  'sync_status': "TEXT DEFAULT 'pending'",
  ...
},
```

**After:** Remove the `'sync_status'` entry entirely from the daily_entries self-heal map.

**Line 218:**

**Before (photos self-heal):**
```dart
'photos': {
  ...
  'sync_status': "TEXT DEFAULT 'pending'",
  ...
},
```

**After:** Remove the `'sync_status'` entry entirely from the photos self-heal map.

#### 4.5.4 Remove sync_queue from Verified Tables

**Line 120:**

**Before:**
```dart
'sync_queue': [
  'id', 'table_name', 'record_id', 'operation', 'payload',
  'created_at', 'attempts', 'last_error',
],
```

**After:** Delete this entire entry. The sync_queue table no longer exists.

**Also remove** the sync_queue self-heal entry (line 224):
```dart
'sync_queue': {
  'attempts': 'INTEGER DEFAULT 0',
},
```

#### 4.5.5 Add New Engine Tables to Verified Tables

These should already have been added in Phase 1 (the plan says so in Phase 1 tasks). Verify they exist:

```dart
'change_log': [
  'id', 'table_name', 'record_id', 'operation', 'old_data', 'new_data',
  'metadata', 'created_at', 'processed_at', 'retry_count',
],
'conflict_log': [
  'id', 'table_name', 'record_id', 'conflict_type', 'local_data',
  'remote_data', 'lost_data', 'winner', 'detected_at', 'dismissed_at',
  'expires_at',
],
'sync_control': [
  'id', 'pulling',
],
'sync_lock': [
  'id', 'locked_by', 'locked_at', 'expires_at',
],
'synced_projects': [
  'project_id', 'added_at',
],
'user_certifications': [
  'id', 'user_id', 'cert_type', 'cert_number',
  'created_at', 'updated_at',
],
```

If not already present, add them now.

---

### 4.6 Phase 7f: Testing Keys Cleanup

**File**: `lib/shared/testing_keys/settings_keys.dart`

#### 4.6.1 Remove Dead Inspector Profile Keys

The plan lists these keys to remove:
- `settingsInspectorNameTile` (line 86)
- `settingsInspectorInitialsTile` (line 87)
- `settingsInspectorAgencyTile` (line 90)
- `editInspectorNameDialog` (line 56)
- `editInspectorNameCancel` (line 59)
- `editInspectorNameSave` (line 62)
- `editInspectorAgencyDialog` (line 100)
- `editInspectorAgencySave` (line 101)
- `settingsUseLastValuesToggle` (line 106)

[CORRECTION] The plan's list is INCOMPLETE. Also remove these dead keys for the phone/cert dialogs that the analysis flagged:
- `settingsInspectorPhoneTile` (line 88) — if the phone tile is removed from settings
- `settingsInspectorCertTile` (line 89) — if the cert tile is removed from settings
- `editInspectorPhoneDialog` (line 96) — if the phone dialog is removed
- `editInspectorPhoneSave` (line 97) — if the phone dialog is removed
- `editInspectorCertDialog` (line 98) — if the cert dialog is removed
- `editInspectorCertSave` (line 99) — if the cert dialog is removed

**Determination**: If the Edit Profile screen (Step 3.12) replaces individual dialog-based editing with a full profile editor screen, then ALL the individual dialog keys are dead and should be removed. If the Edit Profile screen still uses individual edit dialogs per field, keep the relevant keys.

**Conservative approach**: Remove only the keys the plan explicitly lists PLUS the `settingsUseLastValuesToggle`. Keep phone/cert keys if the Edit Profile screen is uncertain. The implementation agent should verify at implementation time.

#### 4.6.2 Update testing_keys.dart Barrel Export

**File**: `lib/shared/testing_keys/testing_keys.dart`

Verify that no removed keys are re-exported here. Since the keys are static members of `SettingsTestingKeys`, not individual exports, this file likely just exports `settings_keys.dart` and no changes are needed.

---

### 4.7 Phase 7g: PreferencesService Cleanup

**File**: `lib/shared/services/preferences_service.dart`

#### 4.7.1 Remove inspectorProfile Getter

[CORRECTION] The plan references `buildInspectorProfile()` method at "~line 320". The actual method is a **getter** named `inspectorProfile` at line 316, not a method called `buildInspectorProfile()`.

**Line 316-322 — Delete:**
```dart
Map<String, String?> get inspectorProfile => {
      'name': inspectorName,
      'initials': effectiveInitials,
      'phone': inspectorPhone,
      'cert_number': inspectorCertNumber,
      'agency': inspectorAgency,
    };
```

**Also delete `hasInspectorProfile` getter (line 325-326):**
```dart
bool get hasInspectorProfile =>
    inspectorName != null && inspectorName!.isNotEmpty;
```

#### 4.7.2 Remove Dead Pref Key Constants

**Lines 15-20 — Remove these constants:**
```dart
static const String keyInspectorName = 'inspector_name';       // line 15
static const String keyInspectorInitials = 'inspector_initials'; // line 16
static const String keyInspectorPhone = 'inspector_phone';      // line 17
static const String keyInspectorCertNumber = 'inspector_cert_number'; // line 18
static const String keyInspectorAgency = 'inspector_agency';    // line 20
```

**Also remove the corresponding getter/setter methods:**
- `inspectorName` getter (line 57) and `setInspectorName()` setter (line 63)
- `inspectorInitials` getter (line 70) and `setInspectorInitials()` setter (line 76)
- `inspectorPhone` getter (line 92) and `setInspectorPhone()` setter (line 98)
- `inspectorCertNumber` getter (line 105) and `setInspectorCertNumber()` setter (line 111)
- `inspectorAgency` getter (line 131) and `setInspectorAgency()` setter (line 137)
- `effectiveInitials` getter (if it exists — derives initials from name)

**Also remove these dead pref keys** (from Phase 6 task list):
- `show_only_manual_fields` key and accessor
- `last_route_location` key and accessor
- `prefill_*` family keys and accessors (all keys starting with `prefill_`)
- `inspector_agency` key (already listed above)
- `gauge_number` key and accessor (if stored in prefs — now in user_profiles)

**Also remove dead toggle accessors:**
- `autoFetchWeather` getter and `setAutoFetchWeather()` setter
- `autoSyncWifi` getter and `setAutoSyncWifi()` setter
- `autoFillEnabled` getter and `setAutoFillEnabled()` setter
- `useLastValues` getter and `setUseLastValues()` setter

---

### 4.8 Phase 7h: Final Verification — Remove Old Sync Infrastructure

This is the largest single cleanup step. It removes the old SyncService and all its supporting infrastructure.

#### 4.8.1 Delete Old SyncService

**File to delete**: `lib/services/sync_service.dart` (1535 lines)

This removes:
- `SyncOpStatus` enum
- `SyncConfig` class
- `SyncProgressCallback` typedef
- `SyncResult` class
- `SyncService` class with all methods including:
  - `syncAll()`
  - `_pushBaseData()`
  - `_pushPendingEntries()`
  - `_pushPendingPhotos()`
  - `queueOperation()`
  - All private helper methods

**Update all imports** that reference `sync_service.dart`:
- `lib/features/sync/data/adapters/supabase_sync_adapter.dart` — this file wraps old SyncService, delete it (see 4.8.2)
- `lib/test_harness/stub_services.dart` — update StubSyncService (see 4.8.5)
- `lib/features/sync/application/background_sync_handler.dart` — already updated in 4.0.1

#### 4.8.2 Delete SupabaseSyncAdapter (Old Wrapper)

**File to delete**: `lib/features/sync/data/adapters/supabase_sync_adapter.dart`

This file wraps the old SyncService. With the new SyncEngine, this wrapper is dead code.

**Update barrel exports:**
- `lib/features/sync/data/adapters/adapters.dart` — remove export of `supabase_sync_adapter.dart`
- `lib/features/sync/data/data.dart` — verify no re-export

#### 4.8.3 Delete SyncStatusBanner Widget

**File to delete**: `lib/features/sync/presentation/widgets/sync_status_banner.dart`

This is replaced by `SyncStatusIcon` (created in Phase 6).

#### 4.8.4 Update home_screen.dart

**File**: `lib/features/entries/presentation/screens/home_screen.dart`

**Line 27 — Remove import:**
```dart
// DELETE: import 'package:construction_inspector/features/sync/presentation/widgets/sync_status_banner.dart';
```

**Line 381 — Replace widget:**

**Before:**
```dart
const SyncStatusBanner(),
```

**After:**
```dart
// SyncStatusBanner removed — SyncStatusIcon is now in the AppBar
// (If the SyncStatusIcon is in the app bar, this line can be deleted entirely.
// If it should appear in the body, replace with the new widget.)
```

The `SyncStatusIcon` should be placed in the app bar (via `AppBar(actions: [const SyncStatusIcon()])`) rather than in the body. Update the home_screen's AppBar to include it.

#### 4.8.5 Update StubSyncService

**File**: `lib/test_harness/stub_services.dart`

`StubSyncService` extends `SyncService`. Since we're deleting `SyncService`, either:
- Delete `StubSyncService` entirely if no test harness code references it
- Replace with a `StubSyncEngine` that implements the new engine interface

**Lines 15-39:**

**Before:**
```dart
class StubSyncService extends SyncService {
  StubSyncService(super.dbService);
  @override
  Future<SyncResult> syncAll() async => SyncResult();
  @override
  Future<void> queueOperation(...) async {}
  @override
  Future<int> getPendingCount() async => 0;
  @override
  void scheduleDebouncedSync() {}
  @override
  void dispose() {}
}
```

**After:**
```dart
class StubSyncEngine {
  Future<void> sync() async {}
  Future<int> getPendingCount() async => 0;
  void dispose() {}
}
```

#### 4.8.6 Remove SyncStatusMixin

**File**: `lib/shared/datasources/query_mixins.dart`
**Lines 34-71**

**Delete the entire `SyncStatusMixin`:**
```dart
// DELETE: mixin SyncStatusMixin { ... } (lines 35-71)
```

Also delete the comment on line 34:
```dart
// DELETE: /// Mixin for entities with sync_status column
```

Keep `BatchOperationsMixin` (lines 1-32) — it is not related to the old sync system.

**Search for classes that use `SyncStatusMixin`** and remove the mixin:
```
rg 'with.*SyncStatusMixin' lib/
```

#### 4.8.7 Remove SyncAdapter Interface (Old)

**File**: `lib/features/sync/domain/sync_adapter.dart`

This defines the old `SyncAdapter` abstract class with `queueOperation()`, `markProjectSynced()`, etc. If the new SyncEngine no longer uses this interface, delete it.

If the SyncOrchestrator still references it for the mock adapter pattern, update the interface to match the new engine's API.

#### 4.8.8 Remove All queueOperation() Calls

Complete inventory of files with `queueOperation` calls:

**1. `lib/features/calculator/presentation/providers/calculator_provider.dart`**
- Line 151: `await _syncOrchestrator?.queueOperation('calculation_history', record.id, 'insert');` — DELETE
- Line 171: `await _syncOrchestrator?.queueOperation('calculation_history', id, 'delete');` — DELETE

**2. `lib/features/forms/presentation/providers/inspector_form_provider.dart`**
- Line 219: `await _syncOrchestrator?.queueOperation(...)` — DELETE
- Line 249: `await _syncOrchestrator?.queueOperation(...)` — DELETE
- Line 279: `await _syncOrchestrator?.queueOperation(...)` — DELETE
- Line 305: `await _syncOrchestrator?.queueOperation(...)` — DELETE
- Line 331: `await _syncOrchestrator?.queueOperation(...)` — DELETE

**3. `lib/features/todos/presentation/providers/todo_provider.dart`**
[CORRECTION] The plan says 4 calls, but there are actually 5:
- Line 125: `await _syncOrchestrator?.queueOperation('todo_items', todo.id, 'insert');` — DELETE
- Line 148: `await _syncOrchestrator?.queueOperation('todo_items', todo.id, 'update');` — DELETE
- Line 167: `await _syncOrchestrator?.queueOperation('todo_items', id, 'update');` — DELETE
- Line 187: `await _syncOrchestrator?.queueOperation('todo_items', id, 'delete');` — DELETE
- Line 210: `await _syncOrchestrator?.queueOperation('todo_items', id, 'delete');` — DELETE

**4. `lib/features/settings/presentation/screens/personnel_types_screen.dart`**
- Line 104: `await syncProvider.queueOperation(...)` — DELETE
- Line 239: `await syncProvider.queueOperation(...)` — DELETE
- Line 337: `await syncProvider.queueOperation(...)` — DELETE
- Line 397: `await syncProvider.queueOperation(...)` — DELETE

**5. `lib/features/sync/presentation/providers/sync_provider.dart`**
- Line 157-163: `queueOperation()` method definition — DELETE entire method

**6. `lib/features/sync/application/sync_orchestrator.dart`**
- Line 366 (comment) + Line 371-377: `queueOperation()` method definition — DELETE entire method

**7. `lib/features/sync/data/adapters/supabase_sync_adapter.dart`**
- Lines 110, 117, 124, 135-141: All `queueOperation` calls and method — FILE DELETED in 4.8.2

**8. `lib/features/sync/data/adapters/mock_sync_adapter.dart`**
- Lines 98-105: `queueOperation()` method — DELETE (or update interface per 4.8.7)

**9. `lib/features/sync/domain/sync_adapter.dart`**
- Line 115: `queueOperation()` interface definition — DELETE (or file deleted per 4.8.7)

**10. `lib/services/sync_service.dart`**
- Lines 1358, 1466: `queueOperation()` — FILE DELETED in 4.8.1

**11. `lib/test_harness/stub_services.dart`**
- Line 24: `queueOperation()` stub — UPDATED in 4.8.5

**Why these deletions are safe**: The change_log triggers installed in Phase 1 automatically capture all INSERT/UPDATE/DELETE operations. Manual `queueOperation()` calls are no longer needed.

#### 4.8.9 Remove sync_status Column from SQLite (Migration v31)

**File to modify**: `lib/core/database/database_service.dart`

Add migration v31 that removes `sync_status` from `daily_entries` and `photos` tables, and drops the `sync_queue` table.

**IMPORTANT**: SQLite on Android < API 35 does NOT support `ALTER TABLE DROP COLUMN`. Must use the table rebuild pattern.

```dart
if (oldVersion < 31) {
  // ---- Remove sync_status from daily_entries (table rebuild) ----
  await db.execute('''
    CREATE TABLE daily_entries_new (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      location_id TEXT,
      date TEXT NOT NULL,
      weather TEXT,
      temp_low INTEGER,
      temp_high INTEGER,
      activities TEXT,
      site_safety TEXT,
      sesc_measures TEXT,
      traffic_control TEXT,
      visitors TEXT,
      extras_overruns TEXT,
      signature TEXT,
      signed_at TEXT,
      status TEXT NOT NULL DEFAULT 'draft',
      submitted_at TEXT,
      revision_number INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      updated_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
      FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL
    )
  ''');
  await db.execute('''
    INSERT INTO daily_entries_new
    SELECT id, project_id, location_id, date, weather, temp_low, temp_high,
           activities, site_safety, sesc_measures, traffic_control, visitors,
           extras_overruns, signature, signed_at, status, submitted_at,
           revision_number, created_at, updated_at,
           created_by_user_id, updated_by_user_id, deleted_at, deleted_by
    FROM daily_entries
  ''');
  await db.execute('DROP TABLE daily_entries');
  await db.execute('ALTER TABLE daily_entries_new RENAME TO daily_entries');

  // Recreate indexes (sync_status index is NOT recreated)
  await db.execute('CREATE INDEX idx_daily_entries_project ON daily_entries(project_id)');
  await db.execute('CREATE INDEX idx_daily_entries_location ON daily_entries(location_id)');
  await db.execute('CREATE INDEX idx_daily_entries_date ON daily_entries(date)');
  await db.execute('CREATE INDEX idx_daily_entries_project_date ON daily_entries(project_id, date)');
  await db.execute('CREATE INDEX idx_daily_entries_deleted_at ON daily_entries(deleted_at)');

  // Recreate change_log triggers for daily_entries (since table was dropped and recreated)
  // ... (trigger DDL from Phase 1)

  // ---- Remove sync_status from photos (table rebuild) ----
  await db.execute('''
    CREATE TABLE photos_new (
      id TEXT PRIMARY KEY,
      entry_id TEXT NOT NULL,
      project_id TEXT NOT NULL,
      file_path TEXT NOT NULL,
      filename TEXT NOT NULL,
      remote_path TEXT,
      notes TEXT,
      caption TEXT,
      location_id TEXT,
      latitude REAL,
      longitude REAL,
      captured_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (entry_id) REFERENCES daily_entries(id) ON DELETE CASCADE,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
      FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL
    )
  ''');
  await db.execute('''
    INSERT INTO photos_new
    SELECT id, entry_id, project_id, file_path, filename, remote_path,
           notes, caption, location_id, latitude, longitude, captured_at,
           created_at, updated_at, created_by_user_id, deleted_at, deleted_by
    FROM photos
  ''');
  await db.execute('DROP TABLE photos');
  await db.execute('ALTER TABLE photos_new RENAME TO photos');

  // Recreate indexes (sync_status index is NOT recreated)
  await db.execute('CREATE INDEX idx_photos_entry ON photos(entry_id)');
  await db.execute('CREATE INDEX idx_photos_project ON photos(project_id)');
  await db.execute('CREATE INDEX idx_photos_deleted_at ON photos(deleted_at)');

  // Recreate change_log triggers for photos
  // ... (trigger DDL from Phase 1)

  // ---- Drop sync_queue table ----
  await db.execute('DROP TABLE IF EXISTS sync_queue');

  // ---- Drop sync_status indexes (already gone from table rebuilds) ----
  // idx_daily_entries_sync_status — already gone
  // idx_photos_sync_status — already gone
}
```

**Increment database version** to 31.

**CRITICAL**: After table rebuild, the change_log triggers for `daily_entries` and `photos` must be recreated (DROP TABLE removes them). Copy the trigger DDL from Phase 1.

#### 4.8.10 Update Schema Definition Files

**File**: `lib/core/database/schema/entry_tables.dart`

**Line 28 — Delete:**
```dart
sync_status TEXT DEFAULT 'pending',
```

**Line 78 — Delete:**
```dart
'CREATE INDEX idx_daily_entries_sync_status ON daily_entries(sync_status)',
```

**File**: `lib/core/database/schema/photo_tables.dart`

**Line 20 — Delete:**
```dart
sync_status TEXT DEFAULT 'pending',
```

**Line 36 — Delete:**
```dart
'CREATE INDEX idx_photos_sync_status ON photos(sync_status)',
```

**File**: `lib/core/database/schema/sync_tables.dart`

Remove the `createSyncQueueTable` definition and its indexes:

**Lines 6-17 — Delete or comment out:**
```dart
static const String createSyncQueueTable = '''
  CREATE TABLE sync_queue ( ... )
''';
```

**Lines 37-38 — Delete:**
```dart
'CREATE INDEX idx_sync_queue_table ON sync_queue(table_name)',
'CREATE INDEX idx_sync_queue_created ON sync_queue(created_at)',
```

Keep `createDeletionNotificationsTable` and its indexes — those are still used.

#### 4.8.11 Update database_service.dart Schema References

**File**: `lib/core/database/database_service.dart`

**Line 392-397 — Delete sync_status indexes from initial schema creation:**
```dart
// DELETE: 'CREATE INDEX IF NOT EXISTS idx_daily_entries_sync_status ON daily_entries(sync_status)',
// DELETE: 'CREATE INDEX IF NOT EXISTS idx_photos_sync_status ON photos(sync_status)',
```

**Lines 945, 977, 1000, 1053, 1080, 1095** — These are in migration code for older versions. Do NOT modify migration code for versions < 31 — those migrations run on fresh installs and must remain valid for the version they target. The v31 migration handles the cleanup.

**Line 239-257** — Migration v2 (creates sync_queue table). Do NOT delete — this migration still needs to run on devices upgrading from v1. The v31 migration drops the table afterward.

#### 4.8.12 Remove deleteAll() from BaseRemoteDatasource (or restrict)

**File**: `lib/shared/datasources/base_remote_datasource.dart`
**Line**: 90-91

Currently has an assert:
```dart
Future<void> deleteAll() async {
  assert(!kReleaseMode, 'deleteAll() is not allowed in release builds');
```

**Options:**
1. Delete entirely (recommended by the plan)
2. Move to a test-only subclass

**Recommended approach**: Delete the method. Any test code that needs it can use direct Supabase client calls.

Also remove `deleteAll()` from:
- `lib/shared/datasources/base_local_datasource.dart:32` — the abstract interface
- `lib/shared/datasources/generic_local_datasource.dart:210` — the implementation

#### 4.8.13 Remove _pushBaseData, _pushPendingEntries, _pushPendingPhotos

These are all in `lib/services/sync_service.dart` which is being deleted in 4.8.1. No separate action needed.

#### 4.8.14 Drop Supabase sync_status Column (Separate Migration)

**File**: `supabase/migrations/20260304200000_drop_sync_status_from_supabase.sql`

This migration file already exists (per git status). It removes the `sync_status` column from Supabase tables. Deploy this migration when Phase 7 is complete.

---

## Step 5: Verification Checklist

### 5.1 Dead Code Grep Commands

After all Phase 7 changes, run these grep commands. **All must return zero matches** in `lib/`:

```bash
# 1. sync_status — should be completely removed from lib/
rg 'sync_status' lib/
# Expected: 0 matches

# 2. sync_queue — should be completely removed from lib/
# EXCEPTION: database_service.dart migration code for versions < 31 may still reference it
rg 'sync_queue' lib/ --glob '!**/database_service.dart'
# Expected: 0 matches

# 3. queueOperation — should be completely removed from lib/
rg 'queueOperation' lib/
# Expected: 0 matches

# 4. SyncStatusMixin — should be completely removed from lib/
rg 'SyncStatusMixin' lib/
# Expected: 0 matches

# 5. markSynced — should be completely removed from lib/
rg 'markSynced' lib/
# Expected: 0 matches

# 6. SyncStatusBanner — should be completely removed from lib/
rg 'SyncStatusBanner' lib/
# Expected: 0 matches

# 7. SyncService import — should be completely removed from lib/
rg "import.*sync_service" lib/
# Expected: 0 matches (may need to exclude test harness if StubSyncEngine still imports)

# 8. getSyncStatusColor — should be completely removed from lib/
rg 'getSyncStatusColor' lib/
# Expected: 0 matches

# 9. SyncStatus enum — should be completely removed from lib/
rg 'SyncStatus\.' lib/
# Expected: 0 matches

# 10. Old sync adapter wrapper — should be completely removed from lib/
rg 'SupabaseSyncAdapter' lib/
# Expected: 0 matches

# 11. _pushBaseData, _pushPendingEntries, _pushPendingPhotos — should be completely removed
rg '_pushBaseData|_pushPendingEntries|_pushPendingPhotos' lib/
# Expected: 0 matches

# 12. entry_personnel_local_datasource (old file) — should be deleted
rg 'entry_personnel_local_datasource' lib/
# Expected: 0 matches (replaced by entry_personnel_counts_local_datasource)

# 13. entry_personnel_remote_datasource (old file) — should be deleted
rg 'entry_personnel_remote_datasource' lib/
# Expected: 0 matches

# 14. EditInspectorDialog — should be deleted
rg 'EditInspectorDialog|edit_inspector_dialog' lib/
# Expected: 0 matches

# 15. buildInspectorProfile / inspectorProfile getter in prefs
rg 'inspectorProfile|buildInspectorProfile' lib/shared/services/preferences_service.dart
# Expected: 0 matches

# 16. Raw SharedPreferences access for inspector fields
rg "prefs\.getString\('inspector_" lib/
# Expected: 0 matches
```

### 5.2 Compile Check

```bash
pwsh -Command "flutter analyze"
```

Expected: zero errors, zero warnings related to sync infrastructure.

### 5.3 Full Test Suite

```bash
pwsh -Command "flutter test"
```

Expected: all existing tests pass (some may need updates for removed sync_status field).

### 5.4 Stage Trace Scorecard

Run full stage trace: 16 tables x 6 stages = 96 checks.

Stages:
1. **Trigger**: INSERT/UPDATE/DELETE -> change_log entry created
2. **Read**: ChangeTracker reads grouped changes
3. **Convert-Remote**: convertForRemote produces valid payload
4. **Push**: Supabase upsert/delete succeeds
5. **Convert-Local**: convertForLocal produces valid SQLite map
6. **Pull**: Incremental pull with cursor, deduplication, conflict resolution

All 96/96 must be OK.

### 5.5 Integration Tests

| Test | Description |
|------|-------------|
| Sync on connectivity restore | Push + incremental pull |
| Sync on app open (stale) | Forced sync |
| Manual sync via Sync Dashboard | Button triggers sync |
| Soft-delete -> push -> pull on second device -> deleted | End-to-end soft-delete |
| Purge from trash -> push -> gone from Supabase | Purge bypasses triggers via sync_control gate |
| Photo full lifecycle | Create -> sync -> edit caption -> sync -> soft-delete -> sync -> purge |
| Conflict scenario | Both sides edit -> LWW -> conflict logged -> visible in UI |
| Integrity check | Runs every 4 hours, results visible in dashboard |
| New team member first sync | Project selection -> select projects -> full pull |
| Settings | All new sections render, no dead items, gauge number and initials work |
| BackgroundSyncHandler | Spawns own SyncEngine, advisory lock prevents concurrent foreground sync |
| SyncLifecycleManager | Calls through rewired orchestrator successfully |
| MockSyncAdapter | Implements new engine interfaces, test mode works |
| user_certifications | Syncs alongside user_profiles, UNIQUE constraint respected |
| Profile expansion | gauge_number, initials, agency read from user_profiles (not prefs) |
| Sign-out wipes new engine tables | change_log, conflict_log, sync_lock, sync_metadata, synced_projects |
| Sign-out does NOT reference sync_queue | Table no longer exists |
| Seed data inserts succeed | Without sync_status column |
| entry_personnel datasource files deleted | No imports reference them |
| SoftDeleteService cascade lists | Do NOT include entry_personnel |
| Schema verifier validates new engine tables | On startup |
| Schema verifier does NOT reference sync_status or sync_queue | Clean |
| Dead testing keys removed | From settings_keys.dart |
| entry_photos_section reads from AuthProvider | Not raw SharedPreferences |
| form_response_repository resolves cert_number | From user_certifications, not PreferencesService |
| DailyEntry.toMap()/fromMap() | Do NOT include sync_status |
| Photo.toMap()/fromMap() | Do NOT include sync_status |

### 5.6 Database Migration Test

Test on **minSdk 24 device** (Android 7.0) to verify the table rebuild migration works on old SQLite versions that lack `ALTER TABLE DROP COLUMN`.

Steps:
1. Install previous version (with sync_status columns and sync_queue table)
2. Insert test data in daily_entries and photos with various sync_status values
3. Upgrade to new version
4. Verify all data preserved (minus sync_status column)
5. Verify sync_queue table is gone
6. Verify new indexes exist
7. Verify change_log triggers still fire on the rebuilt tables

### 5.7 Corrections Summary

| Item | Plan Said | Actual Finding | Resolution |
|------|-----------|----------------|------------|
| FcmHandler | "no-op stub" | Full 104-line Firebase Messaging implementation | No changes needed — it does not call old SyncService methods |
| entry_personnel_local_datasource | "Delete entire file" | Manages BOTH entry_personnel AND entry_personnel_counts | Split file: extract counts methods to new class, then delete original |
| todo_provider queueOperation calls | "4 calls" | 5 calls (insert, update, update, delete, delete) | Remove all 5 |
| PreferencesService method | `buildInspectorProfile()` | `inspectorProfile` getter (not a method) | Delete the getter at line 316 |
| Dead testing keys | List of 9 keys | Missing phone/cert dialog keys | Add phone/cert dialog keys if Edit Profile screen replaces dialogs |
| daily_entry_local_datasource.updateStatus() | Not explicitly mentioned | Also sets sync_status: 'pending' — needs refactoring, not deletion | Remove only the sync_status line from the update map |
| saveForEntry() pattern | Not explicitly addressed | DELETE+re-INSERT bypasses change_log trigger intent | Refactor to diff-based approach for entry_equipment; entry_personnel can stay (legacy, unsynced) |
| Schema *.dart files | Not mentioned | entry_tables.dart and photo_tables.dart have sync_status in DDL | Update both schema definition files |
