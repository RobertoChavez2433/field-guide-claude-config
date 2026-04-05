# Source Excerpts — By Concern

Organized by the spec's decomposition targets.

---

## Concern 1: Error Classification (→ SyncErrorClassifier)

### Site 1: SyncEngine._handlePushError (sync_engine.dart:1407-1512)

Pattern-matches `PostgrestException.code`:
- `401` / `PGRST301` / `JWT` → auth refresh → retry
- `429` / `503` / `Too Many` / `Service Unavailable` → rate limit → backoff retry
- `23505` → constraint violation → retry (2x) then permanent
- `42501` → RLS denied → permanent, increment `_rlsDenialCount`
- `23503` → FK violation → permanent
- `SocketException` / `TimeoutException` → network → backoff retry
- All other PostgrestException → permanent

### Site 2: SyncOrchestrator._isTransientError (sync_orchestrator.dart:507-569)

Pattern-matches error message strings:
- **Transient**: `DNS`, `dns`, `SocketException`, `host lookup`, `TimeoutException`, `Connection refused`, `Connection reset`, `Network is unreachable`, `offline`
- **Non-transient**: `auth`, `Auth`, `RLS`, `permission`, `Permission`, `not configured`, `already in progress`, `has no column`, `DatabaseException`, `no such column`, `table has no column`, `remote record not found`, `0 rows affected`, `Soft-delete push failed`
- **Special case**: `No auth context available for sync` → transient (startup race), evaluated BEFORE nonTransientPatterns
- **Default**: unknown → non-transient (safe default)

### Site 3: SyncProvider._sanitizeSyncError (sync_provider.dart:328-348)

Pattern-matches for UI display:
- Postgres codes `42501`, `23505`, `23503`, `permission denied`, `violates row-level security` → generic safe message
- Messages > 120 chars, containing `{` or `\n` → "Sync failed. Check sync dashboard for details."
- Otherwise → pass through

### Consolidation Target

All three sites must merge into `SyncErrorClassifier` producing `ClassifiedSyncError` with:
- `kind` (SyncErrorKind enum)
- `retryable` (bool)
- `shouldRefreshAuth` (bool)
- `userSafeMessage` (String)
- `logDetail` (String)
- `changeLogDisposition` (optional — how to mark the change_log entry)

---

## Concern 2: Triple Status Tracking (→ SyncStatus)

### SyncEngine state (sync_engine.dart:99)
```dart
bool _insidePushOrPull = false; // Debug-mode reentrancy guard
```

### SyncOrchestrator state (sync_orchestrator.dart:79-84)
```dart
bool _isSyncing = false;
bool get isSyncing => _isSyncing;
SyncAdapterStatus _status = SyncAdapterStatus.idle;
DateTime? _lastSyncTime;
bool _isOnline = true;
```

### SyncProvider state (sync_provider.dart:21-29)
```dart
SyncAdapterStatus _status = SyncAdapterStatus.idle;
DateTime? _lastSyncTime;
bool _isSyncing = false;
```

### Consolidation Target

Single `SyncStatus` immutable value class with stream:
- `isUploading` / `isDownloading` (replaces `_isSyncing` and `_insidePushOrPull`)
- `lastSyncedAt` (persisted, replaces `_lastSyncTime` in 3 places)
- `uploadError` / `downloadError` (typed, replaces `_status` enum)
- `isOnline` / `isAuthValid` (replaces `_isOnline` and auth checks)
- Stream deduplication (don't emit if value unchanged)

---

## Concern 3: Push Orchestration (→ PushHandler)

### Current location: SyncEngine._push (sync_engine.dart:473, ~200 lines)

Flow:
1. `_changeTracker.getUnprocessedChanges()` — read change_log
2. Group by table in FK dependency order via `_registry.dependencyOrder`
3. For each change: lookup adapter, check `shouldSkipPush`, check FK blocking via `fkColumnMap`
4. Route to `_pushUpsert`, `_pushDelete`, or `_pushFileThreePhase`
5. Handle errors via `_handlePushError`
6. Mark processed via `_changeTracker.markProcessed`

Dependencies (to inject): `LocalSyncStore` (replaces direct DB), `SupabaseSync` (replaces direct Supabase), `ChangeTracker`, `SyncRegistry`, `SyncErrorClassifier`, `FileSyncHandler` (for file adapters).

---

## Concern 4: Pull Orchestration (→ PullHandler)

### Current location: SyncEngine._pull (sync_engine.dart:1542, ~200 lines)

Flow:
1. Load synced project IDs
2. For each adapter in registry order (skip if `skipPull`):
   - Apply scope filter based on `scopeType`
   - Paginate via cursor (`updated_at > ?`, limit `pullPageSize`)
   - For each page: strip unknown columns, `convertForLocal`, upsert with trigger suppression
   - Call `ConflictResolver` on conflicts
   - Update cursor
   - Fire `onPullComplete` callback
3. FK rescue if 23503 during upsert
4. Run maintenance if mode requires it

Dependencies (to inject): `LocalSyncStore`, `SupabaseSync`, `ConflictResolver`, `SyncRegistry`, `DirtyScopeTracker`, `EnrollmentHandler` (via callback), `FkRescueHandler`.

---

## Concern 5: File Upload (→ FileSyncHandler)

### Current location: SyncEngine._pushFileThreePhase (sync_engine.dart:1227, ~110 lines)

Three-phase flow:
1. **Phase 1**: Read local file, strip EXIF GPS if flagged, upload to storage bucket. Handle 409 (already exists) as idempotent.
2. **Phase 2**: Upsert metadata to Supabase with `remote_path`. On failure: cleanup Phase 1 upload.
3. **Phase 3**: Bookmark `remote_path` locally with trigger suppression.

### EXIF stripping: SyncEngine._stripExifGps (sync_engine.dart:1366, ~30 lines)
Uses `package:image/image.dart` to decode, clear GPS, re-encode.

Dependencies: `package:image`, `SupabaseSync` (storage), `LocalSyncStore` (bookkeeping).

---

## Concern 6: Retry/Backoff (→ SyncRetryPolicy)

### Current location: SyncOrchestrator._syncWithRetry (sync_orchestrator.dart:372-459)

- `_maxRetries = 2` (declared in orchestrator)
- `_baseRetryDelay = Duration(seconds: 10)` (declared in orchestrator)
- Backoff: `_baseRetryDelay * (1 << attempt)` → 10s, 20s
- DNS check before every attempt
- On exhaustion: schedule 60s background Timer, cancellable by next manual sync
- Background timer: checks session validity, DNS, then retries full sync

### Engine-level backoff: SyncEngine._computeBackoff (private)
Used for per-record retry in push error handling.

---

## Concern 7: DNS/Connectivity (→ ConnectivityProbe)

### Current location: SyncOrchestrator.checkDnsReachability (sync_orchestrator.dart:581-603)

```dart
Future<bool> checkDnsReachability() async {
  if (_isMockMode) return true;
  try {
    final uri = Uri.parse('${SupabaseConfig.url}/rest/v1/');
    final response = await http.head(uri).timeout(const Duration(seconds: 5));
    _isOnline = true;
    return true;
  } on SocketException { _isOnline = false; return false; }
  on TimeoutException { _isOnline = false; return false; }
  on Exception { _isOnline = false; return false; }
}
```

Also called from SyncLifecycleManager._triggerDnsAwareSync.

---

## Concern 8: Lifecycle/Hint Trigger Policy (→ SyncTriggerPolicy)

### SyncLifecycleManager._handleResumed (sync_lifecycle_manager.dart:158-210)

Decision tree:
1. Await `onAppResumed` (config refresh, inactivity check)
2. Check `isReadyForSync`
3. Check `isSyncing` (skip if already running)
4. `consumePendingBackgroundHintMode()` — if full, force recovery sync
5. Check last sync time → if null, quick sync; if stale (>24h), forced full; else quick

### RealtimeHintHandler — marks dirty scopes, triggers quick sync

### SyncLifecycleManager callbacks
```dart
bool Function()? isReadyForSync;
String? Function()? companyIdProvider;
void Function(bool isStale)? onStaleDataWarning;
void Function(bool inProgress)? onForcedSyncInProgress;
Future<void> Function()? onAppResumed;
```

---

## Concern 9: Post-Sync Hooks (→ PostSyncHooks)

### Current location: SyncOrchestrator.syncLocalAgencyProjects (lines 316-340)

After successful sync:
1. `_appConfigProvider?.recordSyncSuccess()` — clears stale config banner
2. `_userProfileSyncDatasource?.pullCompanyMembers(companyId)` — refresh profiles
3. `_userProfileSyncDatasource?.updateLastSyncedAt()` — update last_synced_at

These are unrelated to sync itself — they're app-level follow-up concerns.

---

## Concern 10: Dashboard Queries (→ SyncQueryService)

### SQL queries currently in SyncOrchestrator

| Method | Query | Purpose |
|--------|-------|---------|
| `getPendingBuckets` | `SELECT COUNT(DISTINCT record_id) FROM change_log WHERE processed=0 AND retry_count < ?` | Pending counts by bucket |
| `getIntegrityResults` | `SELECT key, value FROM sync_metadata WHERE key LIKE 'integrity_%'` | Integrity check results |
| `getUndismissedConflictCount` | `SELECT COUNT(*) FROM conflict_log WHERE dismissed_at IS NULL` | Undismissed conflicts |

All 3 should move to `SyncQueryService` backed by `LocalSyncStore`.

---

## Concern 11: Enrollment (→ EnrollmentHandler)

### Current location: SyncEnrollmentService (sync_enrollment_service.dart:14-124)

Already well-scoped. The refactor renames/moves it to `EnrollmentHandler` in the engine layer, since it's called during pull (inside trigger suppression).

---

## Concern 12: FK Rescue (→ FkRescueHandler)

### Current location: SyncEngine._rescueParentProject (sync_engine.dart:2175-2221)

Fetches missing parent project from Supabase during pull when a child record has no local parent. Inserts + enrolls in synced_projects. ~50 lines.
