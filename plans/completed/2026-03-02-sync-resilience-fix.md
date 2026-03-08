# Implementation Plan: Sync Resilience Fix

**Last Updated**: 2026-03-02
**Status**: READY (post-adversarial review)
**Trigger**: S25 Ultra device logs from 2026-03-01 showing 100% sync failure rate across 2 sessions due to DNS resolution failures, zero database CRUD logging, and orphaned projects from interrupted extractions.

## Problem Summary

Three issues were identified from production device logs:

1. **DNS Resolution Failure (P1)**: Every sync attempt failed with `Failed host lookup: 'vsqvkxvvmnnhdajtgblj.supabase.co'`. The `connectivity_plus` plugin reported "online" (WiFi connected) but DNS was unreachable. No retry, no backoff, no user notification. Data never synced.

2. **Database CRUD Logging Gap (P2)**: `database.log` contains ZERO INSERT/UPDATE operations. The `GenericLocalDatasource` methods (`insert`, `insertAll`, `update`, `delete`) do not call `DebugLogger.db()`. This makes it impossible to diagnose from logs whether data was actually written to SQLite.

3. **Orphaned Project from Interrupted Extraction (P3)**: Extraction #2 (project `c3ff53b2`) was interrupted at Stage 2B-i when the app was killed. The project record exists in SQLite with no bid items. When the user restarted, a new project ID (`6ae9fdba`) was created for the re-extraction, leaving `c3ff53b2` orphaned.

## Architecture Note: Two SyncResult Classes

There are two `SyncResult` classes in the codebase. Agents must be aware of which is used where:

| Class | Location | Used By |
|-------|----------|---------|
| `SyncResult` (legacy) | `lib/services/sync_service.dart:72` | `SyncService.syncAll()` return type |
| `SyncResult` (adapter) | `lib/features/sync/domain/sync_adapter.dart:6` | `SyncOrchestrator`, `SyncProvider`, `SyncAdapter` interface |

Both classes already have `errorMessages: List<String>`. Mapping between them happens in `SupabaseSyncAdapter._mapLegacyResult()` at `lib/features/sync/data/adapters/supabase_sync_adapter.dart:172`.

**Rule**: SyncService returns legacy `SyncResult`. SyncOrchestrator and all consumers above it use the adapter `SyncResult`. No new fields are needed on either class for this plan.

## Architecture Note: Sync Resilience Layer Split

DNS reachability checking lives in `SyncService` (the layer that owns connectivity state). Retry-with-backoff lives in `SyncOrchestrator` (the layer that orchestrates sync calls). Consecutive failure tracking lives in `SyncProvider` (the layer that drives UI state). This split follows the existing responsibility boundaries:

- **SyncService** -- owns `_isOnline`, `_isDnsReachable`, connectivity listeners, low-level sync execution
- **SyncOrchestrator** -- orchestrates adapter calls, retry logic, delegates DNS checks via `checkDnsReachability()`
- **SyncProvider** -- UI state, `_consecutiveFailures`, `hasPersistentSyncFailure`

## Phase 1: Sync Resilience -- DNS-Aware Retry with Exponential Backoff

**Agent**: `backend-data-layer-agent`
**Priority**: P1 -- Critical (blocks all data sync)
**Branch**: `fix/sync-dns-resilience`

### Problem

The `SyncService.syncAll()` method at `lib/services/sync_service.dart:290` checks `_isOnline` (from `connectivity_plus`) before syncing. However, `connectivity_plus` only checks if a network interface is active (WiFi/cellular) -- it does NOT verify DNS resolution or actual internet reachability. When DNS fails, every Supabase HTTP call throws a `SocketException` with `Failed host lookup`, but the service treats this as a generic error with no retry logic.

The sync queue retry mechanism at `lib/services/sync_service.dart:427-448` only applies to individual queue items and caps at 5 attempts with no backoff delay. The `syncAll()` method itself (push + pull) has no retry at all.

### Task 1.1: Add DNS Reachability Check to SyncService

**Files**:
- `lib/services/sync_service.dart` -- Add `_checkDnsReachability()` method, add `_isDnsReachable` boolean, integrate into sync flow

**Steps**:
1. Add a new private method `_checkDnsReachability()` that performs a lightweight DNS lookup for the Supabase host before attempting sync:
   ```
   Future<bool> _checkDnsReachability() async
   ```
   - Extract the bare hostname using `Uri.parse(SupabaseConfig.url).host` (SupabaseConfig.url is a full URL like `'https://vsqvkxvvmnnhdajtgblj.supabase.co'` -- `InternetAddress.lookup()` requires a bare hostname, not a URL)
   - Use `InternetAddress.lookup(hostname)` on the extracted hostname
   - Wrap in try/catch for `SocketException` -- return false on DNS failure
   - Set a timeout of 5 seconds to avoid hanging
   - Log result via `DebugLogger.sync()`
   - Note: `dart:io` is already imported in this file

2. Add a separate `_isDnsReachable` boolean field (default `true`), distinct from `_isOnline`:
   - `_isOnline` tracks network interface state (from `connectivity_plus`)
   - `_isDnsReachable` tracks whether DNS resolution succeeds
   - This separation is critical: setting `_isOnline = false` on DNS failure blocks ALL subsequent syncs until `connectivity_plus` fires a new event (which may never happen if WiFi stays connected). Using a separate boolean allows DNS to be re-checked independently.
   - Add a public getter: `bool get isDnsReachable => _isDnsReachable;`

3. Add a `_dnsRetryTimer` field (follows existing `_syncDebounceTimer` pattern). When DNS fails:
   - Set `_isDnsReachable = false`
   - Schedule a timer-based DNS re-check after 30 seconds: `_dnsRetryTimer = Timer(Duration(seconds: 30), () async { ... })`
   - If re-check succeeds, set `_isDnsReachable = true` and call `scheduleDebouncedSync()`
   - Cancel timer on `dispose()` alongside `_syncDebounceTimer`
   - This ensures recovery even if `connectivity_plus` never fires a new event

4. Modify `syncAll()` to call `_checkDnsReachability()` after the `_isOnline` check (line ~319). If DNS is unreachable:
   - Set `_isDnsReachable = false` (NOT `_isOnline = false`)
   - Start the `_dnsRetryTimer` for automatic re-check
   - Update status to `SyncOpStatus.offline`
   - Log: `DebugLogger.sync('DNS unreachable for Supabase host -- treating as offline')`
   - Return a SyncResult with error message: `'DNS resolution failed -- device may be on a captive portal or restricted network'`

5. Add the same DNS check to the connectivity change handler at line ~215. When `connectivity_plus` reports online, verify with DNS before scheduling sync.

6. Add a public `checkDnsReachability()` method (non-underscore) that delegates to `_checkDnsReachability()` and returns the result. This is needed by `SyncOrchestrator` for Task 1.2 retry logic and by `SyncLifecycleManager` for Task 1.3.

7. **Platform note**: DNS check uses `dart:io` `InternetAddress.lookup()` which works on Android, iOS, and Windows. Ensure the 5-second timeout behaves correctly on Windows (test manually).

### Task 1.2: Add Exponential Backoff Retry to SyncOrchestrator

**Files**:
- `lib/features/sync/application/sync_orchestrator.dart` -- Add retry wrapper around `syncLocalAgencyProjects()`

**Note**: `sync_adapter.dart` requires ZERO changes. Both `SyncResult` classes already have `errorMessages: List<String>` which is sufficient for error reporting through the retry logic.

**Steps**:
1. Add retry constants to `SyncOrchestrator`:
   ```
   static const int _maxRetries = 3;
   static const Duration _baseRetryDelay = Duration(seconds: 5);
   ```

2. Add a private method `_syncWithRetry()` that wraps the adapter's `syncAll()`:
   - **Before each retry attempt**, re-check DNS reachability by calling `_localAgencyAdapter.syncService.checkDnsReachability()` (or expose via SyncOrchestrator's own `checkDnsReachability()` method). This is critical because `SyncService` caches `_isOnline = false` / `_isDnsReachable = false` -- without re-checking, retries immediately get "Device is offline" and burn through all attempts instantly.
   - On failure, check if the error is a transient network error (DNS failure, SocketException, TimeoutException)
   - If transient: wait `_baseRetryDelay * 2^attempt` (5s, 10s, 20s), then re-check DNS, then retry
   - If non-transient (auth error, RLS violation): fail immediately, do not retry
   - Log each retry attempt: `DebugLogger.sync('Retry attempt $n/$_maxRetries after ${delay}s')`
   - After max retries exhausted, return the last SyncResult with accumulated errors

3. Modify `syncLocalAgencyProjects()` to use `_syncWithRetry()` instead of calling `_localAgencyAdapter.syncAll()` directly.

4. Add a `checkDnsReachability()` method to `SyncOrchestrator` that delegates to the adapter's SyncService. This is needed by `SyncLifecycleManager` (which only has a reference to `SyncOrchestrator`, not `SyncService`).

### Task 1.3: Auto-Retry on Connectivity Restoration

**Files**:
- `lib/services/sync_service.dart` -- Enhance `_initConnectivity()` handler
- `lib/features/sync/application/sync_lifecycle_manager.dart` -- Add connectivity-aware resume

**Steps**:
1. In `SyncService._initConnectivity()` at line ~206, when transitioning from offline to online:
   - Before calling `scheduleDebouncedSync()`, first call `_checkDnsReachability()`
   - Only schedule sync if DNS check passes
   - If DNS fails, the `_dnsRetryTimer` (from Task 1.1 step 3) handles the delayed re-check automatically
   - Log: `DebugLogger.sync('Connectivity restored but DNS still failing, will retry in 30s')`

2. In `SyncLifecycleManager._handleResumed()` at line ~70:
   - Call `_syncOrchestrator.checkDnsReachability()` (the delegating method added in Task 1.2 step 4) as an additional condition beyond `isSupabaseOnline`
   - If `isSupabaseOnline` is true but the last sync failed with DNS error, trigger a fresh sync attempt instead of relying on stale state

### Test Plan

**Unit tests** (new file: `test/services/sync_service_dns_test.dart`):
- Test `_checkDnsReachability()` returns false on SocketException
- Test `_isDnsReachable` is set independently of `_isOnline`
- Test `_dnsRetryTimer` fires and re-checks after 30s
- Test `syncAll()` returns DNS error message when DNS unreachable
- Test retry logic in SyncOrchestrator re-checks DNS before each attempt

**Unit tests** (new file: `test/features/sync/application/sync_orchestrator_retry_test.dart`):
- Test exponential backoff timing (5s, 10s, 20s)
- Test non-transient errors skip retry
- Test max retries exhausted returns accumulated errors
- Test DNS re-check before each retry

### Verification
1. `pwsh -Command "flutter analyze"` -- no new issues
2. `pwsh -Command "flutter test"` -- all existing tests pass
3. Manual test: Enable airplane mode, attempt sync, verify graceful "Offline" status. Disable airplane mode, verify sync resumes automatically.
4. Manual test: Connect to WiFi without internet (captive portal), verify DNS check catches the false positive and reports offline.
5. Manual test on Windows: Verify DNS timeout behavior matches Android.

---

## Phase 2: Database CRUD Logging for Diagnostics

**Agent**: `backend-data-layer-agent`
**Priority**: P2 -- High (blocks post-incident diagnostics)
**Branch**: `feat/database-crud-logging`

### Problem

`GenericLocalDatasource` at `lib/shared/datasources/generic_local_datasource.dart` performs all CRUD operations (`insert`, `insertAll`, `update`, `delete`, `deleteAll`) without any logging. The `DebugLogger.db()` method exists but is never called from datasource operations. This means `database.log` cannot answer the fundamental question: "Was data actually written to SQLite?"

### Task 2.1: Add Logging to GenericLocalDatasource CRUD Methods

**Files**:
- `lib/shared/datasources/generic_local_datasource.dart` -- Add `DebugLogger.db()` calls to all write methods

**Steps**:
1. Add import for `DebugLogger` at the top of the file:
   ```dart
   import 'package:construction_inspector/core/logging/debug_logger.dart';
   ```

2. Add logging to each write method. Keep logs concise to avoid performance impact:

   - `insert(T item)` -- After successful insert:
     ```dart
     DebugLogger.db('INSERT $tableName id=${getId(item)}');
     ```

   - `insertAll(List<T> items)` -- After successful batch commit:
     ```dart
     DebugLogger.db('INSERT_BATCH $tableName count=${items.length}');
     ```

   - `update(T item)` -- After successful update:
     ```dart
     DebugLogger.db('UPDATE $tableName id=${getId(item)}');
     ```

   - `delete(String id)` -- After successful delete:
     ```dart
     DebugLogger.db('DELETE $tableName id=$id');
     ```

   - `deleteAll()` -- After successful delete:
     ```dart
     DebugLogger.db('DELETE_ALL $tableName');
     ```

3. Do NOT add logging to read methods (`getById`, `getAll`, `getWhere`, `getPaged`) -- these are too frequent and would bloat logs.

### Task 2.2: Add Logging to ProjectLocalDatasource Custom Methods

**Files**:
- `lib/features/projects/data/datasources/local/project_local_datasource.dart` -- Add logging to `setActive`

**Steps**:
1. Add import for `DebugLogger`.
2. Add logging to `setActive()`:
   ```dart
   DebugLogger.db('UPDATE projects id=$id is_active=$isActive');
   ```

### Task 2.3: Add Logging to BidItemLocalDatasource Context

**Files**:
- `lib/features/quantities/data/datasources/local/bid_item_local_datasource.dart` -- No custom write methods, inherits from `ProjectScopedDatasource`. Confirm logging flows through via `GenericLocalDatasource`.

**Steps**:
1. Verify that `ProjectScopedDatasource` extends `GenericLocalDatasource` (it does, confirmed at `lib/shared/datasources/project_scoped_datasource.dart:12`).
2. No changes needed to this file -- logging will be inherited from Phase 2.1.
3. Add a comment noting logging is inherited for future maintainers.

### Test Plan

**Unit tests** (extend existing: `test/shared/datasources/generic_local_datasource_test.dart` if exists, or create new):
- Test that `insert()` triggers a `DebugLogger.db()` call with correct format
- Test that `insertAll()` logs batch count
- Test that read methods do NOT produce log entries

### Verification
1. `pwsh -Command "flutter analyze"` -- no new issues
2. `pwsh -Command "flutter test"` -- all existing tests pass
3. Manual test: Import a PDF, check `database.log` for `INSERT_BATCH bid_items count=131` entry
4. Manual test: Create a project, check `database.log` for `INSERT projects id=...` entry

---

## Phase 3: Orphaned Project Detection and Cleanup

**Agent**: `backend-data-layer-agent`
**Priority**: P3 -- Medium
**Branch**: `feat/orphaned-project-cleanup`

### Problem

When a PDF extraction is interrupted (app killed, crash), the project record may already be written to SQLite but the bid items (written at the end of extraction) are never saved. This leaves an orphaned project with no bid items. On restart, the user creates a new project for the same PDF, leaving the old orphaned record behind.

### PRAGMA foreign_keys Note

`PRAGMA foreign_keys` is **never enabled** in the current codebase (confirmed: zero matches for `foreign_keys` in `lib/`). This means `ON DELETE CASCADE` foreign key constraints defined in the schema (`personnel_types`, `inspector_forms`, `form_responses`, `todo_items`, `calculation_history`) will NOT fire when a project is deleted via `datasource.delete(project.id)`. Orphan cleanup must therefore delete child records explicitly, or the cleanup must only target projects that have zero children across ALL tables. This plan uses the latter approach (safer).

### Task 3.1: Add Orphaned Project Detection Query

**Files**:
- `lib/features/projects/data/datasources/local/project_local_datasource.dart` -- Add `getOrphanedProjects()` method

**Steps**:
1. Add a new method to detect projects that are true orphans -- zero children across ALL child tables, never manually edited, and older than threshold:
   ```dart
   /// Find projects with no children across any table, never manually edited,
   /// created more than [threshold] ago.
   /// These are likely orphans from interrupted PDF extractions.
   Future<List<Project>> getOrphanedProjects({
     Duration threshold = const Duration(minutes: 30),
   }) async {
     final database = await db.database;
     final cutoff = DateTime.now().subtract(threshold).toIso8601String();
     final results = await database.rawQuery('''
       SELECT p.* FROM projects p
       LEFT JOIN bid_items bi ON bi.project_id = p.id
       LEFT JOIN daily_entries de ON de.project_id = p.id
       LEFT JOIN locations loc ON loc.project_id = p.id
       LEFT JOIN contractors c ON c.project_id = p.id
       LEFT JOIN inspector_forms f ON f.project_id = p.id
       LEFT JOIN todo_items t ON t.project_id = p.id
       LEFT JOIN calculation_history ch ON ch.project_id = p.id
       WHERE bi.id IS NULL
       AND de.id IS NULL
       AND loc.id IS NULL
       AND c.id IS NULL
       AND f.id IS NULL
       AND t.id IS NULL
       AND ch.id IS NULL
       AND p.created_at < ?
       AND p.created_at = p.updated_at
     ''', [cutoff]);
     return results.map(fromMap).toList();
   }
   ```

   Key safety filters:
   - **LEFT JOIN on ALL child tables** (bid_items, daily_entries, locations, contractors, inspector_forms, todo_items, calculation_history) -- only targets projects with zero children across ALL tables, not just zero bid_items
   - **`created_at = updated_at`** -- excludes manually created/edited projects. Users who create projects manually and add data later will have `updated_at > created_at` after any edit. Projects from interrupted extractions are created once and never touched again.
   - **30-minute threshold** -- prevents deleting projects from an extraction that is still in progress

2. Add logging:
   ```dart
   DebugLogger.db('ORPHAN_CHECK found ${results.length} orphaned projects');
   ```

### Task 3.2: Add Two-Pass Cleanup Method to ProjectRepository

**Files**:
- `lib/features/projects/data/repositories/project_repository.dart` -- Add two-pass `cleanupOrphanedProjects()` method

**Steps**:
1. Add a two-pass deletion method to protect against the crash-restart-cleanup race condition (where a project is created, app crashes during extraction, app restarts, and cleanup runs before 30 minutes have elapsed from the perspective of a new process):

   **Pass 1 (mark candidates)**: On first startup call, query orphaned projects and store their IDs in a `_orphanCandidates` set (in-memory, not persisted).

   **Pass 2 (delete confirmed orphans)**: On second startup call (or after a delay within the same session), re-query orphaned projects and only delete those that appear in BOTH the candidate set AND the fresh query. This ensures a project must be orphaned across two separate checks before deletion.

   ```dart
   /// Two-pass orphan cleanup. First call marks candidates.
   /// Second call (next startup or delayed) deletes confirmed orphans.
   /// Returns the number of projects cleaned up.
   Future<int> cleanupOrphanedProjects({
     Duration threshold = const Duration(minutes: 30),
   }) async
   ```

2. Implementation:
   - If `_orphanCandidates` is empty (first pass): query orphans, store IDs, return 0
   - If `_orphanCandidates` is not empty (second pass): query orphans, intersect with candidates, delete the intersection
   - For each confirmed orphan, delete the project record via `datasource.delete(project.id)`
   - Since `PRAGMA foreign_keys` is not enabled, CASCADE won't fire -- but confirmed orphans have zero children across all tables (verified by the query), so there are no child records to cascade
   - Log each deletion: `DebugLogger.db('ORPHAN_CLEANUP deleted project ${project.id} (${project.name})')`
   - Clear `_orphanCandidates` after cleanup
   - Return count of deleted projects

### Task 3.3: Wire Cleanup into App Startup via StartupCleanupService

**Files**:
- `lib/services/startup_cleanup_service.dart` -- NEW file: encapsulates startup cleanup logic
- `lib/main.dart` -- Call `StartupCleanupService.run()` after database initialization

**Steps**:
1. Create a `StartupCleanupService` class that encapsulates all startup cleanup tasks (currently just orphan cleanup, but extensible for future cleanup needs). This avoids cluttering `main.dart` with cleanup logic:
   ```dart
   class StartupCleanupService {
     final ProjectRepository _projectRepository;

     StartupCleanupService(this._projectRepository);

     /// Run all startup cleanup tasks.
     Future<void> run() async {
       await _cleanupOrphanedProjects();
     }

     Future<void> _cleanupOrphanedProjects() async {
       final orphanedCount = await _projectRepository.cleanupOrphanedProjects();
       if (orphanedCount > 0) {
         DebugLogger.db('Cleaned up $orphanedCount orphaned projects on startup');
       }
     }
   }
   ```

2. In `main.dart`, after `await dbService.database;` (around line 123):
   ```dart
   // Startup cleanup
   final projectDatasource = ProjectLocalDatasource(dbService);
   await StartupCleanupService(ProjectRepository(projectDatasource)).run();
   ```

3. Note: The `ProjectLocalDatasource` created here should be reused for `projectRepository` creation at line ~201 to avoid creating the datasource twice. Adjust the code flow so:
   - `projectDatasource` is created once at line ~123
   - Cleanup runs
   - Same `projectDatasource` is reused for `projectRepository` creation at line ~201

### Test Plan

**Unit tests** (new file: `test/features/projects/data/datasources/local/project_local_datasource_orphan_test.dart`):
- Test orphan detection with zero children across all tables -- should be detected
- Test project with bid_items but no entries -- should NOT be detected
- Test project with entries but no bid_items -- should NOT be detected
- Test project where `updated_at > created_at` -- should NOT be detected (manually edited)
- Test project younger than threshold -- should NOT be detected
- Test two-pass deletion: first call returns 0, second call deletes confirmed orphans
- Test two-pass deletion: orphan resolved between passes is not deleted

**Unit tests** (new file: `test/services/startup_cleanup_service_test.dart`):
- Test `run()` delegates to ProjectRepository.cleanupOrphanedProjects()

### Verification
1. `pwsh -Command "flutter analyze"` -- no new issues
2. `pwsh -Command "flutter test"` -- all existing tests pass
3. Manual test: Create a project via PDF import, kill app before extraction completes, restart, verify orphaned project is cleaned up after 30 minutes threshold passes AND a second app restart
4. Check `database.log` for `ORPHAN_CHECK` and `ORPHAN_CLEANUP` entries

---

## Phase 4: Sync Status Visibility in Dashboard UI

**Agent**: `frontend-flutter-specialist-agent`
**Priority**: P4 -- Enhancement
**Branch**: `feat/sync-status-banner`

**Design note**: The `SyncStatusBanner` widget lives in `lib/features/sync/presentation/widgets/` (not `settings/`) because it is a sync-domain widget consumed by multiple screens (home screen, potentially others). The `SyncSection` widget in settings is a settings-specific presentation of sync controls, while `SyncStatusBanner` is a reusable notification component owned by the sync feature.

### Problem

The sync status is currently only visible on the Settings screen (via `SyncSection` widget). When sync fails silently (as happened with DNS failure), the user has no indication that their data is not syncing. The dashboard, where users spend most of their time, shows no sync state.

### Task 4.1: Create a Compact Sync Status Banner Widget

**Files**:
- `lib/features/sync/presentation/widgets/sync_status_banner.dart` -- NEW file

**Steps**:
1. Create a reusable banner widget that shows sync status in a compact horizontal strip:
   - **Idle/Success**: Hidden (no banner shown -- don't clutter UI when things are working)
   - **Syncing**: Blue bar with progress indicator and "Syncing..." text
   - **Error**: Red/amber bar with error icon, "Sync failed" text, and "Retry" button
   - **Offline**: Gray bar with cloud-off icon and "Offline -- changes saved locally" text
   - **Stale data**: Amber bar with warning icon and "Data may be outdated" text

2. Widget should consume `SyncProvider` via `Consumer<SyncProvider>` and react to state changes.

3. Add a "Retry" button on error state that triggers sync using fire-and-forget pattern:
   ```dart
   onPressed: () {
     syncProvider.sync();  // No await -- fire-and-forget, UI updates via listener
   },
   ```

4. Add a dismiss action (X button) that hides the banner until the next status change.

5. Add animation: slide in from top with a `SlideTransition`.

### Task 4.2: Add Consecutive Failure Count to SyncProvider

**Files**:
- `lib/features/sync/presentation/providers/sync_provider.dart` -- Expose consecutive failure count and error detail

**Steps**:
1. Add `_consecutiveFailures` counter, incremented on error, reset on success.
2. Add `consecutiveFailures` getter.
3. Modify `_setupListeners` to track consecutive failures:
   ```dart
   if (result.hasErrors) {
     _consecutiveFailures++;
     _lastError = result.errorMessages.isNotEmpty
         ? result.errorMessages.first
         : 'Sync completed with errors';
   } else {
     _consecutiveFailures = 0;
     _lastError = null;
   }
   ```
4. Add a `bool get hasPersistentSyncFailure => _consecutiveFailures >= 2;` getter that the banner uses to decide whether to show the error state (avoids flashing errors on single transient failures).

**Note**: `_consecutiveFailures` lives ONLY in `SyncProvider` (not in `SyncOrchestrator`). SyncProvider is the UI state layer and is the natural owner of "how many times has the user seen a failure." SyncOrchestrator does not need this field.

### Task 4.3: Integrate Banner into Home Screen

**Files**:
- `lib/features/entries/presentation/screens/home_screen.dart` -- Add `SyncStatusBanner` below app bar

**Steps**:
1. Import `SyncStatusBanner`.
2. Add the banner as the first child in the screen's `Column` body, above the calendar:
   ```dart
   const SyncStatusBanner(),
   ```
3. The banner auto-hides when sync is healthy, so it adds zero visual noise in the normal case.

### Task 4.4: Update SyncSection with Error Detail

**Files**:
- `lib/features/settings/presentation/widgets/sync_section.dart` -- Enhance error display

**Steps**:
1. When `syncProvider.lastError` contains "DNS" or "host lookup", show a user-friendly message:
   ```
   "Unable to reach sync server. Check your internet connection."
   ```
   instead of the raw error string.
2. Add consecutive failure count to the subtitle when failures > 1:
   ```
   "Failed 3 times. Last: 5m ago"
   ```

### Test Plan

**Widget tests** (new file: `test/features/sync/presentation/widgets/sync_status_banner_test.dart`):
- Test banner hidden when sync idle/success
- Test banner visible with correct color/text for each state (syncing, error, offline, stale)
- Test "Retry" button triggers `syncProvider.sync()`
- Test dismiss button hides banner

**Unit tests** (extend: `test/features/sync/presentation/providers/sync_provider_test.dart` if exists):
- Test `_consecutiveFailures` increments on error
- Test `_consecutiveFailures` resets on success
- Test `hasPersistentSyncFailure` returns true at threshold

### Verification
1. `pwsh -Command "flutter analyze"` -- no new issues
2. `pwsh -Command "flutter test"` -- all existing tests pass
3. Manual test: Enable airplane mode, navigate to home screen, verify "Offline" banner appears
4. Manual test: Connect to restricted network (DNS blocked), trigger sync, verify "Sync failed" banner with retry button
5. Manual test: Restore connectivity, tap "Retry", verify banner disappears on success

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| DNS check adds latency to sync start | Low -- lookup is ~50ms on healthy networks, 5s timeout | Timeout prevents blocking; check runs only once per sync cycle |
| Retry backoff delays sync when network recovers | Low -- max 20s delay on 3rd retry | Connectivity change listener triggers immediate sync on restore |
| Orphaned project cleanup deletes intentionally empty projects | Medium -- user might create project manually without importing PDF | `created_at = updated_at` filter excludes manually edited projects + LEFT JOIN on ALL child tables (bid_items, daily_entries, locations, contractors, inspector_forms, todo_items, calculation_history) ensures only truly empty projects are targeted + two-pass deletion requires orphan status across two checks |
| Logging in GenericLocalDatasource impacts performance | Low -- single string concatenation per write, no flush | Using sync `_writeToSinkSync()` which avoids flush overhead |
| Banner widget adds dependency on SyncProvider to HomeScreen | Low -- SyncProvider is already in the widget tree via main.dart | No new provider wiring needed |
| DNS retry timer leak | Low -- timer not cancelled on dispose | Timer stored in `_dnsRetryTimer` field, cancelled in `dispose()` alongside existing `_syncDebounceTimer` |

## File Overlap Analysis (for Parallel Agent Dispatch)

| Phase | Files Modified | Agent |
|-------|---------------|-------|
| Phase 1 | `lib/services/sync_service.dart`, `lib/features/sync/application/sync_orchestrator.dart`, `lib/features/sync/application/sync_lifecycle_manager.dart` | backend-data-layer-agent |
| Phase 2 | `lib/shared/datasources/generic_local_datasource.dart`, `lib/features/projects/data/datasources/local/project_local_datasource.dart` | backend-data-layer-agent |
| Phase 3 | `lib/features/projects/data/datasources/local/project_local_datasource.dart`, `lib/features/projects/data/repositories/project_repository.dart`, `lib/services/startup_cleanup_service.dart` (NEW), `lib/main.dart` | backend-data-layer-agent |
| Phase 4 | `lib/features/sync/presentation/widgets/sync_status_banner.dart` (NEW), `lib/features/sync/presentation/providers/sync_provider.dart`, `lib/features/entries/presentation/screens/home_screen.dart`, `lib/features/settings/presentation/widgets/sync_section.dart` | frontend-flutter-specialist-agent |

**Overlap**: `project_local_datasource.dart` is modified in both Phase 2 and Phase 3. **These phases MUST run sequentially** (Phase 2 before Phase 3).

**Removed overlap**: `sync_adapter.dart` is no longer modified in any phase (Finding 3). `_consecutiveFailures` lives only in SyncProvider (Phase 4), not SyncOrchestrator (Phase 1) (Finding 8).

**Parallelizable**: Phases 1+2 can run in parallel (zero file overlap). Phase 3 depends on Phase 2 (shared file). Phase 4 can run independently of all other phases (Finding 8 correction: `_consecutiveFailures` is self-contained in SyncProvider).

**Recommended execution order**:
1. Phase 1 + Phase 2 + Phase 4 (parallel -- zero file overlap between all three)
2. Phase 3 (sequential, after Phase 2 -- shares `project_local_datasource.dart`)

## Files Modified Summary

| File | Phase | Changes |
|------|-------|---------|
| `lib/services/sync_service.dart` | 1 | DNS reachability check, `_isDnsReachable` boolean, `_dnsRetryTimer`, enhanced connectivity handler, public `checkDnsReachability()` |
| `lib/features/sync/application/sync_orchestrator.dart` | 1 | Retry with exponential backoff (re-checks DNS each attempt), `checkDnsReachability()` delegating method |
| `lib/features/sync/application/sync_lifecycle_manager.dart` | 1 | DNS-aware resume logic via `_syncOrchestrator.checkDnsReachability()` |
| `lib/shared/datasources/generic_local_datasource.dart` | 2 | DebugLogger.db() on all write methods |
| `lib/features/projects/data/datasources/local/project_local_datasource.dart` | 2, 3 | Logging on setActive; getOrphanedProjects() with full child-table LEFT JOINs |
| `lib/features/projects/data/repositories/project_repository.dart` | 3 | Two-pass cleanupOrphanedProjects() |
| `lib/services/startup_cleanup_service.dart` | 3 | NEW: encapsulates startup cleanup tasks |
| `lib/main.dart` | 3 | StartupCleanupService.run() call after DB init |
| `lib/features/sync/presentation/widgets/sync_status_banner.dart` | 4 | NEW: compact sync status banner |
| `lib/features/sync/presentation/providers/sync_provider.dart` | 4 | Consecutive failure count, hasPersistentSyncFailure (sole owner of this state) |
| `lib/features/entries/presentation/screens/home_screen.dart` | 4 | SyncStatusBanner integration |
| `lib/features/settings/presentation/widgets/sync_section.dart` | 4 | User-friendly error messages |

**Files NOT modified** (clarification):
| File | Reason |
|------|--------|
| `lib/features/sync/domain/sync_adapter.dart` | SyncResult already has `errorMessages: List<String>` -- no changes needed |

---

## Adversarial Review Log

| Finding # | Severity | Summary | Action Taken |
|-----------|----------|---------|-------------|
| 1 | CRITICAL | CASCADE deletes won't fire (foreign_keys PRAGMA never enabled); orphan query only checks bid_items | Added PRAGMA note section. Rewrote orphan query to LEFT JOIN on ALL 7 child tables (bid_items, daily_entries, locations, contractors, inspector_forms, todo_items, calculation_history). Added `WHERE ... IS NULL` for each. |
| 2 | CRITICAL | Manually created projects legitimately have zero bid items; 30-min threshold insufficient | Added `AND p.created_at = p.updated_at` filter to exclude manually edited projects. Combined with full child-table LEFT JOINs from Finding 1. |
| 3 | IMPORTANT | Task 1.2 says add `lastErrorMessage` to SyncResult but Files Summary says "no changes needed"; SyncResult already has `errorMessages` | Removed `lastErrorMessage` change from Task 1.2. Added explicit note that `sync_adapter.dart` requires ZERO changes. Removed from File Overlap table. |
| 4 | IMPORTANT | Retry in SyncOrchestrator burns through retries instantly because SyncService caches `_isOnline = false` | Added explicit step in Task 1.2: re-check DNS reachability before each retry attempt. Added `checkDnsReachability()` public method to SyncService (Task 1.1 step 6). |
| 5 | IMPORTANT | Two SyncResult classes not clarified | Added "Architecture Note: Two SyncResult Classes" section with table showing which class is used where and mapping location. |
| 6 | IMPORTANT | `InternetAddress.lookup()` needs bare hostname, not full URL | Added `Uri.parse(SupabaseConfig.url).host` to Task 1.1 step 1 with explicit explanation. |
| 7 | MINOR | dart:io already imported | Noted in Task 1.1 step 1: "dart:io is already imported in this file." No other action. |
| 8 | IMPORTANT | `_consecutiveFailures` added to wrong layer (SyncOrchestrator vs SyncProvider); Phase 4 doesn't depend on Phase 1 | Removed step 4 from Task 1.2. Added note to Task 4.2 that `_consecutiveFailures` lives ONLY in SyncProvider. Updated parallelization notes: Phase 4 can now run independently, enabling 3-way parallel (Phase 1+2+4). |
| 9 | SUGGESTED | Consider `StartupCleanupService` instead of inline cleanup in main.dart | Adopted. Task 3.3 now creates `lib/services/startup_cleanup_service.dart` as a dedicated class. |
| 10 | IMPORTANT | No test plan for any phase | Added "Test Plan" subsection to each phase with specific test file paths and test cases. |
| 11 | IMPORTANT | Race condition: orphan cleanup during active extraction after crash-restart | Replaced single-pass deletion with two-pass approach (mark candidates on first check, delete only confirmed orphans on second check). Documented in Task 3.2. |
| 12 | IMPORTANT | SyncLifecycleManager can't access DNS state (only has SyncOrchestrator ref) | Added `checkDnsReachability()` delegating method to SyncOrchestrator (Task 1.2 step 4). Updated Task 1.3 to use it. |
| 13 | IMPORTANT | `_isOnline = false` on DNS failure blocks ALL syncs until connectivity_plus fires | Replaced with separate `_isDnsReachable` boolean. Added `_dnsRetryTimer` for automatic 30-second re-check. Added timer cancellation in `dispose()`. Documented in Task 1.1 steps 2-3. |
| 14 | SUGGESTED | DNS check should be tested on Windows too | Added platform note in Task 1.1 step 7 and Windows manual test in Phase 1 Verification. |
| 15 | SUGGESTED | Document why sync widget is in sync/ not settings/ | Added design note at top of Phase 4 explaining widget ownership. |
| 16 | MINOR | Line numbers may drift | Noted but not actioned. Agents should search by pattern, not line number. (Standard practice per skill docs.) |
| 17 | SUGGESTED | Store DNS retry timer in a field and cancel on dispose | Adopted. Added `_dnsRetryTimer` field in Task 1.1 step 3, cancelled in `dispose()`. Added to Risk Assessment table. |
| 18 | SUGGESTED | Risk assessment claims "zero bid items + zero entries" but query only checked bid_items | Fixed. Risk assessment row now accurately reflects the full LEFT JOIN on all 7 child tables. |
| 19 | SUGGESTED | Clarify retry button uses fire-and-forget pattern | Added explicit code comment in Task 4.1 step 3 showing fire-and-forget `onPressed` pattern. |
| 20 | SUGGESTED | Document rationale for splitting resilience logic across layers | Added "Architecture Note: Sync Resilience Layer Split" section documenting why DNS check is in SyncService, retry is in SyncOrchestrator, and failure count is in SyncProvider. |
