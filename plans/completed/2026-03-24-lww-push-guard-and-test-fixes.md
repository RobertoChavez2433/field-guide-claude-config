# LWW Push Guard + Test Bug Fixes — Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Add a Last-Write-Wins guard to `_pushUpsert()` and `_pushPhotoThreePhase()` so the sync engine skips pushing when the server already has a newer version. Also fix 3 JS test bugs (wrong column names, missing FK parameter).
**Design Decisions:** Database is ground truth. Server-newer means skip push (server wins). Soft-delete push does NOT get the guard. Write conflict_log entry on skip (auditable). Surface user-facing notification when pushes are skipped.

**Architecture:** Before each upsert, the engine pre-fetches the server's `updated_at` via a lightweight `.select('updated_at').eq('id', recordId).maybeSingle()`. If the server timestamp is >= the local timestamp, the push is skipped, a conflict_log entry is written (via `ConflictResolver.resolve()`), and the skipped count propagates up through `SyncEngineResult` -> `SyncResult` -> `SyncProvider` as a user-facing notification.
**Tech Stack:** Dart/Flutter (sync engine), Node.js/JavaScript (test scenarios)
**Blast Radius:** 5 Dart files modified, 1 new Dart test file, 3 JS files fixed

---

## Phase 1: LWW Guard in Sync Engine (Dart)

### Sub-phase 1.1: Add `skippedPushCount` to SyncEngineResult
**Files:** `lib/features/sync/engine/sync_engine.dart`
**Agent:** `backend-supabase-agent`

#### Step 1.1.1: Add field to SyncEngineResult

In `lib/features/sync/engine/sync_engine.dart` around lines 32-66, add `skippedPush` field to `SyncEngineResult`:

```dart
class SyncEngineResult {
  final int pushed;
  final int pulled;
  final int errors;
  final List<String> errorMessages;
  final bool lockFailed;
  final int rlsDenials;
  final int conflicts;
  final int skippedFk;
  final int skippedPush;  // <-- ADD

  const SyncEngineResult({
    this.pushed = 0,
    this.pulled = 0,
    this.errors = 0,
    this.errorMessages = const [],
    this.lockFailed = false,
    this.rlsDenials = 0,
    this.conflicts = 0,
    this.skippedFk = 0,
    this.skippedPush = 0,  // <-- ADD
  });

  bool get hasErrors => errors > 0;
  bool get isSuccess => !hasErrors && !lockFailed && conflicts == 0;

  SyncEngineResult operator +(SyncEngineResult other) {
    return SyncEngineResult(
      pushed: pushed + other.pushed,
      pulled: pulled + other.pulled,
      errors: errors + other.errors,
      errorMessages: [...errorMessages, ...other.errorMessages],
      rlsDenials: rlsDenials + other.rlsDenials,
      conflicts: conflicts + other.conflicts,
      skippedFk: skippedFk + other.skippedFk,
      skippedPush: skippedPush + other.skippedPush,  // <-- ADD
    );
  }
}
```

#### Step 1.1.2: Add `_skippedPushCount` instance variable

In `lib/features/sync/engine/sync_engine.dart` around line 98 (near `_rlsDenialCount`), add:

```dart
/// Count of LWW-skipped pushes during the current push cycle.
int _skippedPushCount = 0;
```

#### Step 1.1.3: Reset counter in pushAndPull()

In `lib/features/sync/engine/sync_engine.dart` around line 206 (in `pushAndPull()` where `_rlsDenialCount = 0` is), add:

```dart
_skippedPushCount = 0;
```

#### Step 1.1.4: Wire `_skippedPushCount` into `_push()` return

In `lib/features/sync/engine/sync_engine.dart` around line 514 (the `return SyncEngineResult(` in `_push()`), add `skippedPush: _skippedPushCount`:

```dart
return SyncEngineResult(
  pushed: pushed,
  errors: errors,
  errorMessages: errorMessages,
  rlsDenials: _rlsDenialCount,
  skippedPush: _skippedPushCount,  // <-- ADD
);
```

#### Step 1.1.5: Include skippedPush in pushAndPull() logging

In `lib/features/sync/engine/sync_engine.dart` around line 316 (the sync cycle summary log), update to include `skippedPush`:

Change:
```dart
Logger.sync('Sync cycle: pushed=${combined.pushed} pulled=${combined.pulled} '
    'errors=${combined.errors} conflicts=${combined.conflicts} '
    'skippedFk=${combined.skippedFk} duration=${stopwatch.elapsedMilliseconds}ms');
```

To:
```dart
Logger.sync('Sync cycle: pushed=${combined.pushed} pulled=${combined.pulled} '
    'errors=${combined.errors} conflicts=${combined.conflicts} '
    'skippedFk=${combined.skippedFk} skippedPush=${combined.skippedPush} '
    'duration=${stopwatch.elapsedMilliseconds}ms');
```

Also update the `_postSyncStatus` map on line ~320 to include `'skippedPush': combined.skippedPush`.

---

### Sub-phase 1.2: Add `fetchServerUpdatedAt()` helper
**Files:** `lib/features/sync/engine/sync_engine.dart`
**Agent:** `backend-supabase-agent`

#### Step 1.2.1: Add fetchServerUpdatedAt method

Add this method to the `SyncEngine` class, near the existing `pushDeleteRemote()` method (around line 656):

```dart
/// Fetch the server's updated_at for a record. Returns null if the record
/// does not exist on the server (first push).
///
/// Extracted as an overrideable method so unit tests can stub the server
/// response without a live Supabase connection.
@visibleForTesting
Future<DateTime?> fetchServerUpdatedAt(String tableName, String recordId) async {
  final row = await supabase
      .from(tableName)
      .select('updated_at')
      .eq('id', recordId)
      .maybeSingle();
  if (row == null) return null;
  final ts = row['updated_at'] as String?;
  if (ts == null) return null;
  return DateTime.parse(ts);
}
```

<!-- WHY @visibleForTesting + public: same pattern as pushDeleteRemote() on line 656. -->

---

### Sub-phase 1.3: Add LWW guard to `_pushUpsert()`
**Files:** `lib/features/sync/engine/sync_engine.dart`
**Agent:** `backend-supabase-agent`

#### Step 1.3.1: Insert LWW check after photo routing, before Supabase upsert

In `lib/features/sync/engine/sync_engine.dart`, AFTER the photo routing check (which ends at line 799 with `return;` + closing brace), and BEFORE the `// Upsert to Supabase` comment (line 801), insert.

**IMPORTANT:** The guard MUST be placed AFTER the photo routing check (lines 796-799), NOT before it. Photo records are routed to `_pushPhotoThreePhase()` which has its own LWW guard (Phase 1.4). If the guard were placed before the photo check, photo records would hit this guard and return early — never reaching `_pushPhotoThreePhase`, making the Phase 1.4 guard dead code.

Insert:

```dart
    // LWW push guard: skip push if server already has a newer version.
    // WHY: Prevents local stale data from overwriting a newer server record.
    // This is a defensive safety net — conflicts are rare (one inspector per project).
    // Runs AFTER natural-key remap (correct ID) and AFTER photo routing
    // (photos have their own guard in _pushPhotoThreePhase).
    // Design note: soft-delete push is intentionally excluded from LWW guard.
    // Soft-delete intent always propagates regardless of timestamps. However,
    // this decision MUST be revisited if an "undelete" feature is ever built,
    // since undelete could conflict with a newer soft-delete on the server.
    final recordId = payload['id'] as String;
    final localUpdatedAt = payload['updated_at'] as String?;
    final serverTs = await fetchServerUpdatedAt(adapter.tableName, recordId);
    if (serverTs != null && localUpdatedAt != null) {
      final localTs = DateTime.parse(localUpdatedAt);
      if (serverTs.compareTo(localTs) >= 0) {
        // Server is newer or equal — skip push, log conflict for audit trail
        Logger.sync(
          'LWW push skip: ${adapter.tableName}/$recordId — '
          'server=$serverTs >= local=$localTs',
        );
        // Write conflict_log entry so the skip is auditable
        await _conflictResolver.resolve(
          tableName: adapter.tableName,
          recordId: recordId,
          local: payload,
          remote: {'id': recordId, 'updated_at': serverTs.toUtc().toIso8601String()},
        );
        _skippedPushCount++;
        // markProcessed by the caller is intentional (not an error). The next
        // pull cycle is expected to overwrite the local record with the server's
        // newer version, bringing local back in sync.
        return;
      }
    }
```

<!-- NOTE: If serverTs is null (first push) or localUpdatedAt is null, the guard
     is bypassed and the upsert proceeds normally. This is correct behavior. -->

---

### Sub-phase 1.4: Add LWW guard to `_pushPhotoThreePhase()`
**Files:** `lib/features/sync/engine/sync_engine.dart`
**Agent:** `backend-supabase-agent`

#### Step 1.4.1: Insert LWW check at the start of _pushPhotoThreePhase

In `lib/features/sync/engine/sync_engine.dart` at the beginning of `_pushPhotoThreePhase()` (line ~923, after the method signature and local variable declarations for filePath/filename/entryId/remotePath), insert BEFORE the `// Phase 1: Upload file` comment:

```dart
    // LWW push guard for photos — same logic as _pushUpsert guard.
    // SECURITY: This guard MUST remain BEFORE Phase 1 file upload to prevent
    // storage leaks (orphaned uploaded files that are never referenced by a
    // database row). If the guard fires after upload, the file is already in
    // storage but the upsert is skipped, leaving an unreferenced blob.
    final recordId = payload['id'] as String;
    final localUpdatedAt = payload['updated_at'] as String?;
    final serverTs = await fetchServerUpdatedAt(adapter.tableName, recordId);
    if (serverTs != null && localUpdatedAt != null) {
      final localTs = DateTime.parse(localUpdatedAt);
      if (serverTs.compareTo(localTs) >= 0) {
        Logger.sync(
          'LWW push skip (photo): ${adapter.tableName}/$recordId — '
          'server=$serverTs >= local=$localTs',
        );
        await _conflictResolver.resolve(
          tableName: adapter.tableName,
          recordId: recordId,
          local: payload,
          remote: {'id': recordId, 'updated_at': serverTs.toUtc().toIso8601String()},
        );
        _skippedPushCount++;
        return;
      }
    }
```

---

### Sub-phase 1.5: Add test entry point
**Files:** `lib/features/sync/engine/sync_engine.dart`
**Agent:** `backend-supabase-agent`

#### Step 1.5.1: Add pushUpsertForTesting method

Near the existing `pushDeleteForTesting` method (line ~678), add:

```dart
  /// Test-only entry point for [_pushUpsert].
  ///
  /// Allows unit tests to exercise the LWW push guard without wiring
  /// a full push/pull cycle. Same pattern as [pushDeleteForTesting].
  @visibleForTesting
  Future<void> pushUpsertForTesting(
    TableAdapter adapter,
    ChangeEntry change,
  ) =>
      _pushUpsert(adapter, change);
```

---

### Sub-phase 1.6: Extract `upsertRemote()` for testability
**Files:** `lib/features/sync/engine/sync_engine.dart`
**Agent:** `backend-supabase-agent`

#### Step 1.6.1: Extract the Supabase upsert call into an overrideable method

Extract the Supabase upsert call in `_pushUpsert()` (lines 803-807) into its own `@visibleForTesting` method called `upsertRemote()`, following the exact same pattern as `pushDeleteRemote()` (lines 656-670). Add this method near `pushDeleteRemote()`:

```dart
/// Upsert a record to Supabase and return the server response.
///
/// Extracted as an overrideable method so unit tests can stub the upsert
/// without a live Supabase connection. Same pattern as [pushDeleteRemote].
@visibleForTesting
Future<Map<String, dynamic>> upsertRemote(String tableName, Map<String, dynamic> payload) async {
  return await supabase
      .from(tableName)
      .upsert(payload)
      .select('updated_at')
      .single();
}
```

Then replace the inline upsert call in `_pushUpsert()` (lines 803-807):

**Before:**
```dart
final response = await supabase
    .from(adapter.tableName)
    .upsert(payload)
    .select('updated_at')
    .single();
```

**After:**
```dart
final response = await upsertRemote(adapter.tableName, payload);
```

Similarly, replace the inline upsert in `_pushPhotoThreePhase()` (lines 974-978) with a call to `upsertRemote()`.

#### Step 1.6.2: Update test subclass to override `upsertRemote()`

The `_LwwTestSyncEngine` test subclass must override `upsertRemote()` to set `upsertCalled = true` and return a stub response instead of hitting real Supabase. See the test code in Phase 3 for the override.

---

#### Step 1.5.2: Verify Phase 1 compiles

```
pwsh -Command "flutter analyze lib/features/sync/engine/sync_engine.dart"
```

Expected: No errors. Warnings OK.

---

## Phase 2: Notification Plumbing (Dart)

### Sub-phase 2.1: Add `skippedPush` to SyncResult
**Files:** `lib/features/sync/domain/sync_types.dart`
**Agent:** `backend-supabase-agent`

#### Step 2.1.1: Add field to SyncResult

In `lib/features/sync/domain/sync_types.dart`, add `skippedPush` to:
1. The field declaration (after `rlsDenials`)
2. The constructor (after `this.rlsDenials = 0`)
3. The `copyWith()` method
4. The `operator +` method

```dart
class SyncResult {
  final int pushed;
  final int pulled;
  final int errors;
  final List<String> errorMessages;
  final int rlsDenials;
  final int skippedPush;  // <-- ADD

  const SyncResult({
    this.pushed = 0,
    this.pulled = 0,
    this.errors = 0,
    this.errorMessages = const [],
    this.rlsDenials = 0,
    this.skippedPush = 0,  // <-- ADD
  });

  bool get hasErrors => errors > 0;
  int get total => pushed + pulled;
  bool get isSuccess => !hasErrors;

  SyncResult copyWith({
    int? pushed,
    int? pulled,
    int? errors,
    List<String>? errorMessages,
    int? rlsDenials,
    int? skippedPush,  // <-- ADD
  }) {
    return SyncResult(
      pushed: pushed ?? this.pushed,
      pulled: pulled ?? this.pulled,
      errors: errors ?? this.errors,
      errorMessages: errorMessages ?? this.errorMessages,
      rlsDenials: rlsDenials ?? this.rlsDenials,
      skippedPush: skippedPush ?? this.skippedPush,  // <-- ADD
    );
  }

  SyncResult operator +(SyncResult other) {
    return SyncResult(
      pushed: pushed + other.pushed,
      pulled: pulled + other.pulled,
      errors: errors + other.errors,
      errorMessages: [...errorMessages, ...other.errorMessages],
      rlsDenials: rlsDenials + other.rlsDenials,
      skippedPush: skippedPush + other.skippedPush,  // <-- ADD
    );
  }

  @override
  String toString() => 'SyncResult(pushed: $pushed, pulled: $pulled, errors: $errors)';
}
```

---

### Sub-phase 2.2: Map skippedPush in SyncOrchestrator
**Files:** `lib/features/sync/application/sync_orchestrator.dart`
**Agent:** `backend-supabase-agent`

#### Step 2.2.1: Add skippedPush to _doSync() mapping

In `lib/features/sync/application/sync_orchestrator.dart` around line 402 (the `return SyncResult(` in `_doSync()`), add `skippedPush`:

```dart
      return SyncResult(
        pushed: engineResult.pushed,
        pulled: engineResult.pulled,
        errors: engineResult.errors,
        errorMessages: engineResult.errorMessages,
        rlsDenials: engineResult.rlsDenials,
        skippedPush: engineResult.skippedPush,  // <-- ADD
      );
```

---

### Sub-phase 2.3: Surface notification in SyncProvider
**Files:** `lib/features/sync/presentation/providers/sync_provider.dart`
**Agent:** `frontend-flutter-agent`

#### Step 2.3.1: Add skippedPush notification to onSyncComplete

In `lib/features/sync/presentation/providers/sync_provider.dart` inside the `_setupListeners()` method, in the `_syncOrchestrator.onSyncComplete = (result) {` callback, AFTER the `_refreshPendingCount();` call (line ~156) and BEFORE `if (onSyncCycleComplete != null)` (line ~159), add:

```dart
      // LWW push skip notification: surface to user when pushes were skipped
      // because the server had newer data.
      if (result.skippedPush > 0) {
        final noun = result.skippedPush == 1 ? 'record was' : 'records were';
        addNotification(
          '${result.skippedPush} $noun not pushed — '
          'server already has newer data.',
        );
      }
```

#### Step 2.3.2: Verify Phase 2 compiles

```
pwsh -Command "flutter analyze lib/features/sync/"
```

Expected: No errors. Warnings OK.

---

## Phase 3: Unit Tests (Dart)

### Sub-phase 3.1: Create LWW test file
**Files:** `test/features/sync/engine/sync_engine_lww_test.dart` (NEW)
**Agent:** `backend-supabase-agent`

#### Step 3.1.1: Create test file

Create `test/features/sync/engine/sync_engine_lww_test.dart` with the following structure. Uses the subclass-based stub pattern from `sync_engine_delete_test.dart`:

```dart
// test/features/sync/engine/sync_engine_lww_test.dart
//
// Unit tests for LWW push guard:
//   - Server newer: push skipped
//   - Server older: push proceeds
//   - First push (no server record): push proceeds
//   - Null local timestamp: push proceeds
//   - Photo path: push skipped when server newer

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/features/sync/adapters/location_adapter.dart';
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';
import 'package:construction_inspector/features/sync/engine/sync_engine.dart';

import '../../../helpers/sync/sync_test_helpers.dart';

void main() {
  setUpAll(() {
    sqfliteFfiInit();
  });

  // -------------------------------------------------------------------------
  // LWW push guard tests
  //
  // Uses _LwwTestSyncEngine — a test subclass that overrides:
  //   - fetchServerUpdatedAt() → returns a configurable DateTime
  //   - the Supabase upsert (via upsertRemote override) → captures calls
  // -------------------------------------------------------------------------

  group('LWW push guard: _pushUpsert', () {
    late Database db;
    late Map<String, String> seedIds;

    setUp(() async {
      db = await SqliteTestHelper.createDatabase();
      seedIds = await SyncTestData.seedFkGraph(db);
      await SqliteTestHelper.clearChangeLog(db);
    });

    tearDown(() async {
      await db.close();
    });

    test('skips push when server has newer updated_at', () async {
      final locationId = seedIds['locationId']!;
      // Set local updated_at to a known time
      final localTime = DateTime.utc(2026, 3, 24, 10, 0, 0);
      await SqliteTestHelper.suppressTriggers(db);
      await db.update(
        'locations',
        {'updated_at': localTime.toIso8601String()},
        where: 'id = ?',
        whereArgs: [locationId],
      );
      await SqliteTestHelper.enableTriggers(db);

      // Insert change_log entry
      await db.rawInsert('''
        INSERT INTO change_log (table_name, record_id, operation, processed, changed_at, retry_count)
        VALUES ('locations', ?, 'insert', 0, datetime('now'), 0)
      ''', [locationId]);

      final changeRows = await db.query(
        'change_log',
        where: 'table_name = ? AND record_id = ? AND processed = 0',
        whereArgs: ['locations', locationId],
        limit: 1,
      );
      final change = ChangeEntry.fromMap(changeRows.first);

      // Server has NEWER timestamp
      final serverTime = DateTime.utc(2026, 3, 24, 11, 0, 0);
      final engine = _LwwTestSyncEngine(db, serverUpdatedAt: serverTime);

      await engine.pushUpsertForTesting(LocationAdapter(), change);

      // Upsert should NOT have been called
      expect(engine.upsertCalled, isFalse, reason: 'Push should be skipped when server is newer');

      // Conflict log should have an entry
      final conflicts = await db.query('conflict_log',
        where: 'table_name = ? AND record_id = ?',
        whereArgs: ['locations', locationId],
      );
      expect(conflicts, isNotEmpty, reason: 'Conflict should be logged for audit');
    });

    test('proceeds with push when server has older updated_at', () async {
      final locationId = seedIds['locationId']!;
      final localTime = DateTime.utc(2026, 3, 24, 12, 0, 0);
      await SqliteTestHelper.suppressTriggers(db);
      await db.update(
        'locations',
        {'updated_at': localTime.toIso8601String()},
        where: 'id = ?',
        whereArgs: [locationId],
      );
      await SqliteTestHelper.enableTriggers(db);

      await db.rawInsert('''
        INSERT INTO change_log (table_name, record_id, operation, processed, changed_at, retry_count)
        VALUES ('locations', ?, 'insert', 0, datetime('now'), 0)
      ''', [locationId]);

      final changeRows = await db.query(
        'change_log',
        where: 'table_name = ? AND record_id = ? AND processed = 0',
        whereArgs: ['locations', locationId],
        limit: 1,
      );
      final change = ChangeEntry.fromMap(changeRows.first);

      // Server has OLDER timestamp
      final serverTime = DateTime.utc(2026, 3, 24, 10, 0, 0);
      final engine = _LwwTestSyncEngine(db, serverUpdatedAt: serverTime);

      await engine.pushUpsertForTesting(LocationAdapter(), change);

      expect(engine.upsertCalled, isTrue, reason: 'Push should proceed when local is newer');
    });

    test('proceeds with push on first push (no server record)', () async {
      final locationId = seedIds['locationId']!;

      await db.rawInsert('''
        INSERT INTO change_log (table_name, record_id, operation, processed, changed_at, retry_count)
        VALUES ('locations', ?, 'insert', 0, datetime('now'), 0)
      ''', [locationId]);

      final changeRows = await db.query(
        'change_log',
        where: 'table_name = ? AND record_id = ? AND processed = 0',
        whereArgs: ['locations', locationId],
        limit: 1,
      );
      final change = ChangeEntry.fromMap(changeRows.first);

      // Server returns null (record doesn't exist yet)
      final engine = _LwwTestSyncEngine(db, serverUpdatedAt: null);

      await engine.pushUpsertForTesting(LocationAdapter(), change);

      expect(engine.upsertCalled, isTrue, reason: 'First push should always proceed');
    });

    test('proceeds when local updated_at is null', () async {
      final locationId = seedIds['locationId']!;
      await SqliteTestHelper.suppressTriggers(db);
      await db.update(
        'locations',
        {'updated_at': null},
        where: 'id = ?',
        whereArgs: [locationId],
      );
      await SqliteTestHelper.enableTriggers(db);

      await db.rawInsert('''
        INSERT INTO change_log (table_name, record_id, operation, processed, changed_at, retry_count)
        VALUES ('locations', ?, 'insert', 0, datetime('now'), 0)
      ''', [locationId]);

      final changeRows = await db.query(
        'change_log',
        where: 'table_name = ? AND record_id = ? AND processed = 0',
        whereArgs: ['locations', locationId],
        limit: 1,
      );
      final change = ChangeEntry.fromMap(changeRows.first);

      final serverTime = DateTime.utc(2026, 3, 24, 11, 0, 0);
      final engine = _LwwTestSyncEngine(db, serverUpdatedAt: serverTime);

      await engine.pushUpsertForTesting(LocationAdapter(), change);

      expect(engine.upsertCalled, isTrue,
          reason: 'Null local timestamp should bypass guard and push');
    });
  });
}

// ---------------------------------------------------------------------------
// Test subclass: overrides Supabase network calls
// ---------------------------------------------------------------------------

/// Builds a placeholder SupabaseClient for compile-time type checking.
/// Methods that touch supabase are replaced by overrides in test subclasses.
/// Only synthetic, non-functional values are permitted here.
/// Never paste real Supabase keys.
SupabaseClient _buildNullSupabase() {
  return SupabaseClient(
    'https://placeholder.supabase.co',
    'test-anon-key-not-a-real-token',
  );
}

class _LwwTestSyncEngine extends SyncEngine {
  final DateTime? _serverUpdatedAt;
  bool upsertCalled = false;

  _LwwTestSyncEngine(
    Database db, {
    required DateTime? serverUpdatedAt,
  })  : _serverUpdatedAt = serverUpdatedAt,
        super(
          db: db,
          supabase: _buildNullSupabase(),
          companyId: 'test-company',
          userId: 'test-user',
        );

  @override
  Future<DateTime?> fetchServerUpdatedAt(String tableName, String recordId) async {
    return _serverUpdatedAt;
  }

  @override
  Future<Map<String, dynamic>> upsertRemote(String tableName, Map<String, dynamic> payload) async {
    upsertCalled = true;
    // Return a stub response matching the shape _pushUpsert expects
    return {'updated_at': payload['updated_at'] ?? DateTime.now().toUtc().toIso8601String()};
  }
}
```

<!-- The upsertRemote() extraction is handled in Sub-phase 1.6. The test subclass
     overrides upsertRemote() to set upsertCalled = true and return a stub response. -->

#### Step 3.1.2: Verify tests pass

```
pwsh -Command "flutter test test/features/sync/engine/sync_engine_lww_test.dart"
```

Expected: All tests pass.

---

## Phase 4: JS Test Bug Fixes

### Sub-phase 4.1: Fix daily-entries-S2 column name
**Files:** `tools/debug-server/scenarios/L2/daily-entries-S2-update-push.js`
**Agent:** `backend-supabase-agent`

#### Step 4.1.1: Replace `notes` with `activities`

In `tools/debug-server/scenarios/L2/daily-entries-S2-update-push.js`:

- Line 10: `const updatedNotes = \`SYNCTEST-updated-notes-${Date.now()}\`;` -> `const updatedActivities = \`SYNCTEST-updated-activities-${Date.now()}\`;`
- Line 11: `{ notes: updatedNotes }` -> `{ activities: updatedActivities }`
- Line 15: `serverRow.notes !== updatedNotes` -> `serverRow.activities !== updatedActivities`
- Line 16: `expected ${updatedNotes}, got ${serverRow.notes}` -> `expected ${updatedActivities}, got ${serverRow.activities}`

<!-- WHY: daily_entries table has an `activities` column, not `notes`. The JS test
     was written against an outdated schema. Confirmed via daily_entry.dart model. -->

---

### Sub-phase 4.2: Fix daily-entries-S4 conflict field
**Files:** `tools/debug-server/scenarios/L2/daily-entries-S4-conflict.js`
**Agent:** `backend-supabase-agent`

#### Step 4.2.1: Replace `notes` with `activities` in conflict phases

In `tools/debug-server/scenarios/L2/daily-entries-S4-conflict.js`:

- Line 11: `field: 'notes'` -> `field: 'activities'`
- Line 16: `field: 'notes'` -> `field: 'activities'`
- Line 12: `'SYNCTEST-local-notes-1'` -> `'SYNCTEST-local-activities-1'`
- Line 12: `'SYNCTEST-remote-notes-1'` -> `'SYNCTEST-remote-activities-1'`
- Line 17: `'SYNCTEST-local-notes-2'` -> `'SYNCTEST-local-activities-2'`
- Line 17: `'SYNCTEST-remote-notes-2'` -> `'SYNCTEST-remote-activities-2'`

---

### Sub-phase 4.3: Fix project-assignments-S5 missing user_id
**Files:** `tools/debug-server/scenarios/L2/project-assignments-S5-fresh-pull.js`
**Agent:** `backend-supabase-agent`

#### Step 4.3.1: Pass user_id override to makeProjectAssignment

In `tools/debug-server/scenarios/L2/project-assignments-S5-fresh-pull.js` line 8:

Change:
```js
const record = makeProjectAssignment(ctx);
```

To:
```js
const record = makeProjectAssignment(ctx, { user_id: ctx.adminUserId });
```

<!-- WHY: Default makeProjectAssignment uses ctx.inspectorUserId. But S5 (fresh-pull)
     seeds via admin auth, so the RLS policy requires user_id to match the
     authenticated user. Without this, the INSERT fails with an RLS denial. -->

**RLS verification note:** The implementer MUST verify that the RLS SELECT policy on `project_assignments` allows the inspector device to see assignments with `user_id = adminUserId`. If the SELECT policy filters by `user_id = auth.uid()`, the inspector will not see the admin-created record and the fresh-pull assertion will fail. In that case, use a different approach — e.g., create a second inspector user for seeding, or use a service-role key for the seed step.

---

## Phase 5: Build + Smoke Test

### Sub-phase 5.1: Full analysis
**Agent:** `backend-supabase-agent`

#### Step 5.1.1: Run flutter analyze

```
pwsh -Command "flutter analyze"
```

Expected: No errors.

#### Step 5.1.2: Run existing sync engine tests

```
pwsh -Command "flutter test test/features/sync/engine/"
```

Expected: All tests pass (existing delete tests + new LWW tests).

#### Step 5.1.3: Run all unit tests

```
pwsh -Command "flutter test"
```

Expected: All tests pass.

---

## Summary of All Changes

### Modified Files (Dart — 5 files)
| File | Change |
|------|--------|
| `lib/features/sync/engine/sync_engine.dart` | `skippedPush` field on `SyncEngineResult`, `_skippedPushCount` counter, `fetchServerUpdatedAt()`, LWW guard in `_pushUpsert()` and `_pushPhotoThreePhase()`, `pushUpsertForTesting()`, extracted `upsertRemote()` |
| `lib/features/sync/domain/sync_types.dart` | `skippedPush` field on `SyncResult` |
| `lib/features/sync/application/sync_orchestrator.dart` | Map `skippedPush` in `_doSync()` |
| `lib/features/sync/presentation/providers/sync_provider.dart` | Notification when pushes skipped |

### New Files (Dart — 1 file)
| File | Purpose |
|------|---------|
| `test/features/sync/engine/sync_engine_lww_test.dart` | Unit tests for LWW push guard |

### Modified Files (JS — 3 files)
| File | Change |
|------|--------|
| `tools/debug-server/scenarios/L2/daily-entries-S2-update-push.js` | `notes` -> `activities` |
| `tools/debug-server/scenarios/L2/daily-entries-S4-conflict.js` | `notes` -> `activities` |
| `tools/debug-server/scenarios/L2/project-assignments-S5-fresh-pull.js` | Add `{ user_id: ctx.adminUserId }` |

### Edge Cases Handled
- **First push** (no server record): `fetchServerUpdatedAt` returns null, guard bypassed
- **Null local timestamp**: guard bypassed, push proceeds
- **Natural key remap**: LWW check runs AFTER remap (uses remapped `payload['id']`)
- **Clock skew**: mitigated because `updated_at` is always server-originated
- **Soft-delete**: excluded by design (delete intent always propagates)
- **Photo push**: LWW check runs BEFORE Phase 1 file upload (avoids wasted bandwidth)
- **TOCTOU race**: acceptable (millisecond window, same pattern as existing unique constraint pre-check)
