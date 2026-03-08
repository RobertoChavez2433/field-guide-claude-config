# Sync UX Fixes: Auth Race, Config Banner, Bucket Counts

**Created**: 2026-03-06
**Status**: BRAINSTORMED — decisions locked
**Branch**: `feat/sync-engine-rewrite`

---

## Executive Summary

Three sync UX issues discovered during device testing. All are fixable without schema changes.

| # | Workstream | Severity | Root Cause |
|---|-----------|----------|------------|
| FIX-A | Auth context race condition | CRITICAL | Sync fires before user profile loads |
| FIX-B | Stale config banner always showing | HIGH | checkConfig() fails due to same auth race; not linked to sync success |
| FIX-C | Sync pending count redesign | MEDIUM | Raw change_log counts confuse inspectors |

---

## Key Design Decisions (Brainstormed & Locked)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Auth context fix approach | **Guard + retry (5s)** | Least invasive; handles offline-first field use |
| Banner staleness logic | **Unified: last sync OR last config check** | Banner shows only when NEITHER sync nor checkConfig() has succeeded in 24h. Either one resets the clock. |
| Banner behavior | **Persistent until server contact** | No dismiss button — it clears automatically when sync or config check succeeds. Stays if truly offline for 24h+ |
| Pending count model | **4 inspector-friendly buckets** | Projects, Entries, Forms, Photos |
| Count method | **Unique records** (COUNT DISTINCT record_id) | "How many things need syncing" not "how many DB operations" |
| Settings display | **Compact inline bucket counts** | `Pending: 132 proj | 0 entries | 0 forms | 0 photos` |
| Dashboard display | **Expandable bucket detail** | Bucket total + tap to see sub-item breakdown |

### Bucket Definitions

| Bucket | Icon | Tables Included |
|--------|------|-----------------|
| **Projects** | folder | `projects`, `bid_items`, `locations`, `todo_items` |
| **Entries** | book | `daily_entries`, `contractors`, `equipment`, `entry_contractors`, `entry_equipment`, `entry_quantities`, `entry_personnel_counts` |
| **Forms** | description | `inspector_forms`, `form_responses` |
| **Photos** | camera | `photos` |

Any table not in a bucket (e.g., `calculation_history`, `personnel_types`) rolls into a hidden "other" count not shown in UI but included in the total.

---

## FIX-A: Auth Context Race Condition

**Agent**: `backend-data-layer-agent`
**Risk**: LOW — additive guard, no behavior change when auth is available
**Files**: 1

### Root Cause

`SyncOrchestrator._createEngine()` (sync_orchestrator.dart:137) returns null when `_companyId` or `_userId` is null. In `main.dart:300-315`, `updateSyncContext()` reads from `authProvider.userProfile?.companyId`, which is populated asynchronously by `loadUserProfile()`. If sync fires before profile loads (race condition on cold start), the error "No auth context available for sync" is displayed.

### Changes

**File 1: `lib/features/sync/application/sync_orchestrator.dart`**

Modify `_createEngine()` (~line 137) to add a retry loop when context is missing:

```dart
Future<SyncEngine?> _createEngine() async {
  var companyId = _companyId;
  var userId = _userId;

  // Guard + retry: auth context may not be set yet on cold start
  if (companyId == null || userId == null) {
    const maxWait = Duration(seconds: 5);
    const pollInterval = Duration(milliseconds: 500);
    final deadline = DateTime.now().add(maxWait);

    while (DateTime.now().isBefore(deadline)) {
      await Future.delayed(pollInterval);
      companyId = _companyId;
      userId = _userId;
      if (companyId != null && userId != null) break;
    }
  }

  if (companyId == null || userId == null) {
    DebugLogger.sync('SyncOrchestrator: Cannot create SyncEngine - missing context '
        '(companyId=$companyId, userId=$userId) after retry');
    return null;
  }

  // ... rest of existing engine creation code
}
```

### Verification
- [ ] Cold start → sync succeeds (no "No auth context" error)
- [ ] Logged out → sync still gracefully fails (doesn't retry forever)
- [ ] Offline start → no crash, sync skipped

---

## FIX-B: Unified Server Contact Banner

**Agent**: `backend-data-layer-agent`
**Risk**: LOW — changes staleness check logic, no new network calls
**Files**: 3

### Root Cause

`AppConfigProvider.isConfigStale` only checks `_lastConfigCheckAt`, which is updated exclusively by `checkConfig()`. If `checkConfig()` fails on startup (auth race, network), the banner shows permanently — even if sync is working fine. The banner should represent "have we talked to the server at all in 24h?" not "has this specific config fetch run?"

### Design

Unify staleness to check: `max(lastConfigCheck, lastSyncSuccess) > 24h ago`.

- `checkConfig()` success → resets the 24h clock
- Successful sync → also resets the 24h clock
- Banner only shows when NEITHER has happened in 24h
- No dismiss button — it clears automatically when server contact is made

### Changes

**File 1: `lib/features/auth/presentation/providers/app_config_provider.dart`**

Add a `_lastSyncSuccessAt` field and setter. Modify `isConfigStale` to check both timestamps:

```dart
DateTime? _lastSyncSuccessAt;

/// Called by SyncOrchestrator after a successful sync cycle.
void recordSyncSuccess() {
  _lastSyncSuccessAt = DateTime.now().toUtc();
  notifyListeners(); // triggers banner rebuild
}

bool get isConfigStale {
  // Use the MOST RECENT of config check or sync success
  final lastContact = _latestServerContact;
  if (lastContact == null) return true;
  return DateTime.now().toUtc().difference(lastContact) > _staleThreshold;
}

DateTime? get _latestServerContact {
  if (_lastConfigCheckAt == null) return _lastSyncSuccessAt;
  if (_lastSyncSuccessAt == null) return _lastConfigCheckAt;
  return _lastConfigCheckAt!.isAfter(_lastSyncSuccessAt!)
      ? _lastConfigCheckAt
      : _lastSyncSuccessAt;
}
```

Also persist `_lastSyncSuccessAt` to secure storage (same pattern as `_lastConfigCheckAt`) and restore it in `restoreLastCheckTimestamp()`.

**File 2: `lib/features/sync/application/sync_orchestrator.dart`**

Add an `AppConfigProvider?` reference (optional, set via setter). After successful sync in `_doSync()`:

```dart
AppConfigProvider? _appConfigProvider;
void setAppConfigProvider(AppConfigProvider provider) {
  _appConfigProvider = provider;
}

// In _doSync(), after successful pushAndPull:
if (result.errors == 0) {
  _appConfigProvider?.recordSyncSuccess();
}
```

**File 3: `lib/main.dart`**

Wire the provider after SyncOrchestrator creation (~line 315 area):

```dart
syncOrchestrator.setAppConfigProvider(appConfigProvider);
```

### Verification
- [ ] Successful sync → banner clears (even if checkConfig() hasn't run)
- [ ] Successful checkConfig() → banner clears (even if sync hasn't run)
- [ ] Neither in 24h → banner shows
- [ ] App restart → banner state restored from secure storage
- [ ] Failed sync + failed checkConfig() → banner stays (correct)
- [ ] Offline for 25h → banner shows on next open (correct)

---

## FIX-C: Sync Pending Count Bucket Redesign

**Agent**: `frontend-flutter-specialist-agent` (UI) + `backend-data-layer-agent` (query)
**Risk**: MEDIUM — changes pending count query + two screens
**Files**: 4

### Data Layer Changes

**File 1: `lib/features/sync/application/sync_orchestrator.dart`**

Replace `getPendingCount()` (~line 375) which returns a single int, with `getPendingBuckets()`:

```dart
/// Bucket definitions for inspector-friendly pending count display.
static const Map<String, List<String>> syncBuckets = {
  'Projects': ['projects', 'bid_items', 'locations', 'todo_items'],
  'Entries': ['daily_entries', 'contractors', 'equipment',
              'entry_contractors', 'entry_equipment',
              'entry_quantities', 'entry_personnel_counts'],
  'Forms': ['inspector_forms', 'form_responses'],
  'Photos': ['photos'],
};

/// Returns pending unique record counts grouped by bucket.
/// Each bucket counts DISTINCT record_ids (not operations).
Future<Map<String, BucketCount>> getPendingBuckets() async {
  final db = await _databaseService.database;
  final result = <String, BucketCount>{};

  for (final entry in syncBuckets.entries) {
    final bucketName = entry.key;
    final tables = entry.value;
    final placeholders = tables.map((_) => '?').join(',');

    // Total unique records for the bucket
    final totalRows = await db.rawQuery(
      'SELECT COUNT(DISTINCT record_id) as cnt FROM change_log '
      'WHERE processed = 0 AND table_name IN ($placeholders)',
      tables,
    );
    final total = totalRows.first['cnt'] as int? ?? 0;

    // Per-table breakdown (for dashboard expandable view)
    final breakdown = <String, int>{};
    for (final table in tables) {
      final rows = await db.rawQuery(
        'SELECT COUNT(DISTINCT record_id) as cnt FROM change_log '
        'WHERE processed = 0 AND table_name = ?',
        [table],
      );
      breakdown[table] = rows.first['cnt'] as int? ?? 0;
    }

    result[bucketName] = BucketCount(total: total, breakdown: breakdown);
  }

  // Count anything not in a bucket
  final allBucketTables = syncBuckets.values.expand((t) => t).toList();
  final otherPlaceholders = allBucketTables.map((_) => '?').join(',');
  final otherRows = await db.rawQuery(
    'SELECT COUNT(DISTINCT record_id) as cnt FROM change_log '
    'WHERE processed = 0 AND table_name NOT IN ($otherPlaceholders)',
    allBucketTables,
  );
  final otherCount = otherRows.first['cnt'] as int? ?? 0;
  if (otherCount > 0) {
    result['Other'] = BucketCount(total: otherCount, breakdown: {'other': otherCount});
  }

  return result;
}
```

Add the `BucketCount` class (in same file or a small model):

```dart
class BucketCount {
  final int total;
  final Map<String, int> breakdown;
  const BucketCount({required this.total, required this.breakdown});
}
```

Keep existing `getPendingCount()` for backwards compat (used by sync status checks). It can delegate to `getPendingBuckets()`:

```dart
Future<int> getPendingCount() async {
  final buckets = await getPendingBuckets();
  return buckets.values.fold(0, (sum, b) => sum + b.total);
}
```

### UI Changes

**File 2: `lib/features/sync/presentation/providers/sync_provider.dart`**

Add bucket state fields and refresh method:

```dart
Map<String, BucketCount> _pendingBuckets = {};
Map<String, BucketCount> get pendingBuckets => _pendingBuckets;

int get totalPendingCount =>
    _pendingBuckets.values.fold(0, (sum, b) => sum + b.total);

Future<void> refreshPendingBuckets() async {
  _pendingBuckets = await _orchestrator.getPendingBuckets();
  notifyListeners();
}
```

Update `_refreshPendingCount()` (~line 161) to also refresh buckets.

**File 3: `lib/features/settings/presentation/screens/settings_screen.dart`**

Replace the current "X pending changes" ListTile in the Sync & Data section with compact bucket display:

```
Pending: 132 proj | 0 entries | 0 forms | 0 photos
```

Use `Consumer<SyncProvider>` to read `pendingBuckets`. Format as a single-line `Text` widget with pipe separators. Only show buckets with count > 0 in color, grey out zero buckets.

**File 4: `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`**

Replace the current `_buildPendingCard()` (~line 243) which shows raw table names, with expandable bucket cards:

```
Pending Changes (132 total)

▼ Projects .................. 132
   projects .............. 1
   bid items ........... 131
   locations ............. 0
   todos ................. 0

▶ Entries ..................... 0
▶ Forms ....................... 0
▶ Photos ...................... 0
```

Each bucket is an `ExpansionTile`:
- Title: bucket name + icon + count
- Children: per-table breakdown rows
- Initially collapsed; auto-expand if count > 0

Human-readable table names mapping:
```dart
static const _tableDisplayNames = {
  'projects': 'Projects',
  'bid_items': 'Bid Items',
  'locations': 'Locations',
  'todo_items': 'Todos',
  'daily_entries': 'Entries',
  'contractors': 'Contractors',
  'equipment': 'Equipment',
  'entry_contractors': 'Entry Contractors',
  'entry_equipment': 'Entry Equipment',
  'entry_quantities': 'Quantities',
  'entry_personnel_counts': 'Personnel Counts',
  'inspector_forms': 'Forms',
  'form_responses': 'Responses',
  'photos': 'Photos',
};
```

### Verification
- [ ] Settings screen shows compact bucket counts
- [ ] Sync Dashboard shows expandable buckets with per-table breakdown
- [ ] Counts match unique records (not operations)
- [ ] Zero-count buckets shown but visually dimmed
- [ ] "Other" bucket only appears if orphan tables exist
- [ ] Total across all buckets matches old `getPendingCount()` value

---

## Dependency Chain & Execution Order

```
FIX-A (auth guard+retry)    ──── MUST be first; fixes root sync failure
  │
  ├── FIX-B (config+sync link) ──── depends on sync actually working
  │
  └── FIX-C (bucket counts)    ──── independent, can parallel with FIX-B
```

---

## Complete File List

### FIX-A (1 file)
- `lib/features/sync/application/sync_orchestrator.dart`

### FIX-B (3 files)
- `lib/features/auth/presentation/providers/app_config_provider.dart`
- `lib/features/sync/application/sync_orchestrator.dart`
- `lib/main.dart`

### FIX-C (4 files)
- `lib/features/sync/application/sync_orchestrator.dart`
- `lib/features/sync/presentation/providers/sync_provider.dart`
- `lib/features/settings/presentation/screens/settings_screen.dart`
- `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`

### Total unique files: 6

---

## Commit Structure

```
fix(sync): add auth context guard+retry for cold start race condition
fix(sync): trigger checkConfig() after successful sync to clear stale banner
feat(sync): redesign pending counts with inspector-friendly bucket grouping
```

---

## Agent Assignment

| Agent | Workstreams |
|-------|-------------|
| `backend-data-layer-agent` | FIX-A, FIX-B, FIX-C (sync_orchestrator.dart, app_config_provider.dart, main.dart) |
| `frontend-flutter-specialist-agent` | FIX-C (settings_screen.dart, sync_dashboard_screen.dart, sync_provider.dart) |

---

## Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Retry loop delays sync start by 5s | LOW | LOW | Only triggers when context is missing; 500ms poll interval |
| checkConfig() fails after sync | LOW | LOW | Banner stays (safe); no regression |
| Bucket query slow on large change_log | LOW | MEDIUM | Uses index on change_log(processed); DISTINCT is bounded by table count |
| Table not assigned to bucket | LOW | LOW | "Other" catch-all bucket handles it |
| getPendingCount() regression | LOW | HIGH | Delegates to getPendingBuckets().sum; same underlying data |
