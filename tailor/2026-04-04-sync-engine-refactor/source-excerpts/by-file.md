# Source Excerpts — By File

## lib/features/sync/engine/sync_engine.dart (2374 lines)

### Imports (lines 1-25)
```dart
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:image/image.dart' as img;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:uuid/uuid.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/features/sync/engine/change_tracker.dart';
import 'package:construction_inspector/features/sync/engine/conflict_resolver.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
import 'package:construction_inspector/features/sync/engine/integrity_checker.dart';
import 'package:construction_inspector/features/sync/engine/orphan_scanner.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';
import 'package:construction_inspector/features/sync/engine/storage_cleanup.dart';
import 'package:construction_inspector/features/sync/engine/sync_mutex.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';
import 'package:construction_inspector/shared/utils/safe_row.dart';
```

### SyncEngineResult (lines 35-73)
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
  final int skippedPush;

  const SyncEngineResult({
    this.pushed = 0, this.pulled = 0, this.errors = 0,
    this.errorMessages = const [], this.lockFailed = false,
    this.rlsDenials = 0, this.conflicts = 0,
    this.skippedFk = 0, this.skippedPush = 0,
  });

  bool get hasErrors => errors > 0;
  bool get isSuccess => !hasErrors && !lockFailed && conflicts == 0;

  SyncEngineResult operator +(SyncEngineResult other) {
    return SyncEngineResult(
      pushed: pushed + other.pushed, pulled: pulled + other.pulled,
      errors: errors + other.errors,
      errorMessages: [...errorMessages, ...other.errorMessages],
      rlsDenials: rlsDenials + other.rlsDenials,
      conflicts: conflicts + other.conflicts,
      skippedFk: skippedFk + other.skippedFk,
      skippedPush: skippedPush + other.skippedPush,
    );
  }
}
```

### Constructor (lines 83-169)
```dart
class SyncEngine {
  final Database db;
  final SupabaseClient supabase;
  final String companyId;
  final String userId;
  final String lockedBy;

  final SyncMutex _mutex;
  final ChangeTracker _changeTracker;
  final ConflictResolver _conflictResolver;
  final IntegrityChecker _integrityChecker;
  final OrphanScanner _orphanScanner;
  final StorageCleanup _storageCleanup;
  final SyncRegistry _registry = SyncRegistry.instance;
  final DirtyScopeTracker? _dirtyScopeTracker;

  bool _insidePushOrPull = false;
  int _rlsDenialCount = 0;
  int _skippedPushCount = 0;
  int _pullConflictCount = 0;
  int _pullSkippedFkCount = 0;

  SyncProgressCallback? onProgress;
  Future<void> Function(String tableName, int pulledCount)? onPullComplete;
  void Function(String tableName, String recordId, int conflictCount)? onCircuitBreakerTrip;

  List<String> _syncedProjectIds = [];
  List<String> _syncedContractorIds = [];
  bool _projectsAdapterCompleted = false;
  final Map<String, Set<String>> _localColumnsCache = {};

  SyncEngine({
    required this.db, required this.supabase,
    required this.companyId, required this.userId,
    this.lockedBy = 'foreground', this.onProgress,
    DirtyScopeTracker? dirtyScopeTracker,
  }) : _dirtyScopeTracker = dirtyScopeTracker,
       _mutex = SyncMutex(db),
       _changeTracker = ChangeTracker(db),
       _conflictResolver = ConflictResolver(db),
       _integrityChecker = IntegrityChecker(db, supabase),
       _orphanScanner = OrphanScanner(supabase),
       _storageCleanup = StorageCleanup(supabase, db);
```

### @visibleForTesting methods (8 total)
- `pushDeleteRemote` (line 761) — Supabase DELETE
- `upsertRemote` (line 785) — Supabase UPSERT
- `insertOnlyRemote` (line 806) — Supabase INSERT
- `fetchServerUpdatedAt` (line 833) — LWW timestamp fetch
- `shouldSkipLwwPush` (line 856) — LWW guard
- `pushDeleteForTesting` (line 897) — test entry for _pushDelete
- `validateAndStampCompanyId` (line 910) — company_id stamp
- `pushUpsertForTesting` (line 935) — test entry for _pushUpsert

---

## lib/features/sync/application/sync_orchestrator.dart (730 lines)

### Fields (lines 62-84)
```dart
final DatabaseService _dbService;
final SupabaseClient? _supabaseClient;
final SyncEngineFactory _engineFactory;
final UserProfileSyncDatasource? _userProfileSyncDatasource;
final ({String? companyId, String? userId}) Function() _syncContextProvider;
final AppConfigProvider? _appConfigProvider;
final DirtyScopeTracker? _dirtyScopeTracker;
MockSyncAdapter? _mockAdapter;
bool _disposed = false;
bool _isSyncing = false;
SyncAdapterStatus _status = SyncAdapterStatus.idle;
DateTime? _lastSyncTime;
bool _isOnline = true;
Timer? _backgroundRetryTimer;
```

### Callback fields (lines 88-101)
```dart
Future<void> Function(String tableName, int pulledCount)? onPullComplete;
void Function(SyncResult result)? onSyncComplete;
void Function(String message)? onNewAssignmentDetected;
void Function(String tableName, String recordId, int conflictCount)? onCircuitBreakerTrip;
```

### SQL in orchestrator (5 locations)
1. `initialize()` — sync_metadata query
2. `syncLocalAgencyProjects()` — sync_metadata query
3. `getPendingBuckets()` — 3 rawQuery calls on change_log
4. `getIntegrityResults()` — rawQuery on sync_metadata
5. `getUndismissedConflictCount()` — rawQuery on conflict_log

---

## lib/features/sync/presentation/providers/sync_provider.dart (368 lines)

### Full field set (lines 18-49)
See patterns/provider-pattern.md for full extraction.

### Key layer violations
1. `get orchestrator` (line 22) — raw SyncOrchestrator exposure
2. `_sanitizeSyncError()` (lines 328-348) — Postgres code matching in presentation layer

---

## lib/features/sync/domain/sync_types.dart (109 lines)

Full file: `SyncResult` (lines 4-66), `SyncAdapterStatus` (line 69), `SyncMode` (lines 72-81), `DirtyScope` (lines 84-109).

---

## lib/features/sync/adapters/table_adapter.dart (180 lines)

Full abstract class with 20 overridable properties/methods. See patterns/adapter-pattern.md.

---

## lib/features/sync/engine/sync_registry.dart (107 lines)

`registerSyncAdapters()` (lines 29-54) + `SyncRegistry` class (lines 63-107). Singleton via `SyncRegistry.instance`. 22 adapters registered in FK order.

---

## lib/features/sync/config/sync_config.dart (47 lines)

```dart
class SyncEngineConfig {
  SyncEngineConfig._();
  static const int pushBatchLimit = 500;
  static const int pushAnomalyThreshold = 1000;
  static const int maxRetryCount = 5;
  static const int pullPageSize = 100;
  static const Duration pullSafetyMargin = Duration(seconds: 5);
  static const Duration integrityCheckInterval = Duration(hours: 4);
  static const int maxConsecutiveResets = 3;
  static const Duration staleLockTimeout = Duration(minutes: 15);
  static const Duration changeLogRetention = Duration(days: 7);
  static const Duration conflictLogRetention = Duration(days: 7);
  static const Duration conflictWarningAge = Duration(days: 30);
  static const Duration retryBaseDelay = Duration(seconds: 1);
  static const Duration retryMaxDelay = Duration(seconds: 16);
  static const int circuitBreakerThreshold = 1000;
  static const int conflictPingPongThreshold = 3;
  static const int cursorResetMinDiff = 5;
  static const double cursorResetPercentThreshold = 0.10;
  static const Duration orphanMinAge = Duration(hours: 24);
  static const int orphanMaxPerCycle = 50;
  static const bool quickSyncPullsDirtyScopes = true;
  static const Duration dirtyScopeMaxAge = Duration(hours: 2);
}
```

---

## lib/features/sync/application/sync_lifecycle_manager.dart (261 lines)

### Callback fields (lines 28-39)
```dart
bool Function()? isReadyForSync;
String? Function()? companyIdProvider;
void Function(bool isStale)? onStaleDataWarning;
void Function(bool inProgress)? onForcedSyncInProgress;
Future<void> Function()? onAppResumed;
```

### _staleThreshold (line 23)
```dart
static const Duration _staleThreshold = Duration(hours: 24);
```

---

## lib/features/sync/application/sync_enrollment_service.dart (124 lines)

Full source in patterns. Key: `handleAssignmentPull()` runs inside a SQLite transaction, enrolls new projects into synced_projects, marks unassigned projects.

---

## lib/features/sync/application/sync_engine_factory.dart (63 lines)

Factory that ensures adapters are registered, then creates SyncEngine instances for foreground and background contexts.

---

## lib/features/sync/application/sync_orchestrator_builder.dart (72 lines)

Builder with `_built` flag preventing reuse. Validates required fields at build() time.
