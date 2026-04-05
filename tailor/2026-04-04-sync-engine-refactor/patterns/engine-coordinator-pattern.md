# Pattern: Engine Coordinator (SyncEngine)

## How We Do It

SyncEngine is currently a God Object at 2374 lines with 42 methods. It holds Database + SupabaseClient directly, creates all sub-components (ChangeTracker, ConflictResolver, IntegrityChecker, OrphanScanner, StorageCleanup) in its constructor, and mixes push orchestration, pull orchestration, Supabase I/O, SQLite I/O, file upload, EXIF stripping, error classification, enrollment, FK rescue, and maintenance in one class. The refactor preserves every behavior while decomposing into focused classes.

## Exemplar: Current SyncEngine Constructor + Key Methods

### Constructor (sync_engine.dart:155-169)

```dart
SyncEngine({
  required this.db,
  required this.supabase,
  required this.companyId,
  required this.userId,
  this.lockedBy = 'foreground',
  this.onProgress,
  DirtyScopeTracker? dirtyScopeTracker,
}) : _dirtyScopeTracker = dirtyScopeTracker,
     _mutex = SyncMutex(db),
     _changeTracker = ChangeTracker(db),
     _conflictResolver = ConflictResolver(db),
     _integrityChecker = IntegrityChecker(db, supabase),
     _orphanScanner = OrphanScanner(supabase),
     _storageCleanup = StorageCleanup(supabase, db);
```

### pushAndPull (sync_engine.dart:221)

```dart
Future<SyncEngineResult> pushAndPull({SyncMode mode = SyncMode.full})
```

This is the top-level entry point. Mode-aware routing:
- `full`: push + pull all + maintenance
- `quick`: push + pull dirty scopes only
- `maintenance`: pull only + integrity + orphan + pruning

### _push (sync_engine.dart:473) — ~200 lines

Reads change_log via ChangeTracker, iterates in FK order, routes each change to upsert/delete/file-push, handles skip/block decisions.

### _pull (sync_engine.dart:1542) — ~200 lines

Iterates adapters in FK order, paginates via cursor, applies scope filters, calls ConflictResolver, fires onPullComplete callback, runs FK rescue.

### _handlePushError (sync_engine.dart:1407) — ~100 lines

Pattern-matches PostgrestException codes, SocketException, TimeoutException. Returns true for retry, false for permanent failure. This becomes `SyncErrorClassifier`.

### _pushFileThreePhase (sync_engine.dart:1227) — ~110 lines

Phase 1: Upload binary to storage bucket. Phase 2: Upsert metadata to Supabase. Phase 3: Bookmark remote_path locally. Has cleanup on Phase 2 failure.

### _stripExifGps (sync_engine.dart:1366) — ~30 lines

Uses `package:image` to decode JPEG, clear GPS EXIF, re-encode.

### _rescueParentProject (sync_engine.dart:2175) — ~50 lines

Fetches missing project from Supabase, inserts locally, enrolls in synced_projects.

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| pushAndPull | sync_engine.dart:221 | `Future<SyncEngineResult> pushAndPull({SyncMode mode})` | Top-level sync entry point |
| pushOnly | sync_engine.dart:445 | `Future<SyncEngineResult> pushOnly()` | Push-only (testing) |
| pullOnly | sync_engine.dart:458 | `Future<SyncEngineResult> pullOnly()` | Pull-only (testing) |
| resetState | sync_engine.dart:209 | `Future<void> resetState()` | Reset pulling flag + mutex |
| createForBackgroundSync | sync_engine.dart:179 | `static Future<SyncEngine?> createForBackgroundSync(...)` | Background isolate factory |
| _getLocalColumns | (private) | cached PRAGMA table_info lookup | Column filtering |
| _stripUnknownColumns | (private) | strips remote columns not in local schema | Pull safety |

## Imports

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
