# Implementation Plan: PDF Extraction Regression + Sync Failure Fix

**Last Updated**: 2026-03-02 (Rev 3 — dual adversarial review incorporated)
**Status**: READY
**Branch**: `fix/sync-dns-resilience` (sync changes uncommitted), `main` (PDF changes committed)

## Overview

Two critical issues plus three newly-discovered data-flow bugs require a coordinated fix:

1. **PDF extraction regression** (commit `22f2d7b`): Geometry-aware crop upscaler causes Tesseract comma/period misreads, inflating project budget to $357B.
2. **Sync infrastructure bugs**: Triple DNS checking, duplicate onSyncComplete callbacks, missing company context on the orchestrator path.
3. **NEW — Pull phase crash**: Remote `daily_entries.test_results` column crashes local INSERT because `_convertForLocal()` does NOT strip unknown columns despite its doc comment.
4. **NEW — First-sync push storm**: `_lastSyncTime` is in-memory only — every cold start pushes ALL local data (including corrupted bid items) before pull.
5. **NEW — Retry amplification**: Schema errors classified as transient → 3x retry loop pushes corrupted data 3 times per sync attempt.

## Adversarial Review Log

| Rev | Date | Reviewers | Findings |
|-----|------|-----------|----------|
| Rev 1 | 2026-03-02 | Single adversarial | 4 CRITICAL findings |
| Rev 2 | 2026-03-02 | Single adversarial | Incorporated Rev 1 |
| Rev 3 | 2026-03-02 | Dual Opus adversarial (crash-paths + completeness) | 10 findings: 3 CRITICAL, 4 HIGH, 2 MEDIUM, 1 LOW. Added Phase 0, updated Phases 1-3. |

## Phase Ordering & Parallel Safety

```
Phase 0 (Sync Data-Flow)  ──MUST COMPLETE FIRST──►  Phase 1 (Sync Fix)  ─┐
                                                                          ├─► Phase 3 (Guards)
                           ──CAN RUN IN PARALLEL──►  Phase 2 (PDF Fix)  ─┘
```

- **Phase 0** MUST complete before Phase 1. Without column stripping and `_lastSyncTime` persistence, Phase 1's sync improvements will accelerate corruption propagation.
- **Phase 0** and **Phase 2** have ZERO file overlap and CAN run in parallel.
- **Phase 1** depends on Phase 0. Phase 1 and Phase 2 have zero file overlap.
- **Phase 3** depends on Phase 1 + Phase 2.

---

## Phase 0: Sync Data-Flow Fixes (MUST-FIX-FIRST)

**Agent**: `backend-supabase-agent`
**Priority**: CRITICAL — without these, Phase 1 makes corruption WORSE
**Adversarial source**: CRASH-1, CRASH-2, CRASH-5, CRASH-7, CRASH-4 (dual review)

### Task 0.1: Implement Column Stripping in `_convertForLocal()`

**Files**:
- `lib/services/sync_service.dart` lines 753-801

**Problem**: Doc comment at line 755 claims "Strips unknown columns not present in local schema" but the implementation does ZERO column stripping. When Supabase returns `daily_entries` records with `test_results` (dropped locally in migration 18→19 at `database_service.dart:692-698`), `_upsertLocalRecords()` at line 1240 calls `db.insert(tableName, localRecord)` with the unknown key → SQLite throws `DatabaseException: table daily_entries has no column named test_results` → pull phase crashes entirely.

**Steps**:
1. Add a column name cache field to `SyncService`:
   ```dart
   final Map<String, Set<String>> _localColumnCache = {};
   ```
2. Add a helper method to query and cache local table columns:
   ```dart
   Future<Set<String>> _getLocalColumns(String tableName) async {
     if (_localColumnCache.containsKey(tableName)) {
       return _localColumnCache[tableName]!;
     }
     final db = await _dbService.database;
     final columns = await db.rawQuery("PRAGMA table_info('$tableName')");
     final names = columns.map((c) => c['name'] as String).toSet();
     _localColumnCache[tableName] = names;
     return names;
   }
   ```
3. At the end of `_convertForLocal()` (before `return result;` at line 800), add column stripping:
   ```dart
   // Strip unknown columns not present in local schema
   final validColumns = await _getLocalColumns(tableName);
   result.removeWhere((key, _) => !validColumns.contains(key));
   ```
4. Note: This changes `_convertForLocal()` from sync to async. Update the call site at line 1228:
   ```dart
   final localRecord = await _convertForLocal(tableName, record);
   ```
5. Clear `_localColumnCache` at the start of `syncAll()` to pick up any schema changes from migrations that ran between syncs.

**Rationale**: This is the systemic fix — not just for `test_results` but for ANY future column drift between Supabase and local SQLite. Runtime `PRAGMA table_info()` with caching is more robust than a hardcoded allowlist.

### Task 0.2: Persist `_lastSyncTime` to SQLite

**Files**:
- `lib/services/sync_service.dart` lines 136, 368, 450
- `lib/core/database/database_service.dart` — add `sync_metadata` table

**Problem**: `_lastSyncTime` at line 136 is `DateTime?` in memory only. Every cold start → null → `_pushBaseData()` at line 609 treats it as first sync → pushes ALL local data (including corrupted bid items with 1000x unitPrice). Push happens BEFORE pull (line 488 vs 442), so bad data reaches Supabase before corrections arrive.

**Steps**:
1. **Add `sync_metadata` table** to `database_service.dart` in `_onCreate`:
   ```sql
   CREATE TABLE IF NOT EXISTS sync_metadata (
     key TEXT PRIMARY KEY,
     value TEXT NOT NULL
   );
   ```
2. **Add migration** in `_onUpgrade` (bump DB version to 25, alongside bid_amount migration):
   ```dart
   if (oldVersion < 25) {
     await db.execute('''
       CREATE TABLE IF NOT EXISTS sync_metadata (
         key TEXT PRIMARY KEY,
         value TEXT NOT NULL
       )
     ''');
     await _addColumnIfNotExists(db, 'bid_items', 'bid_amount', 'REAL');
   }
   ```
3. **Add load/save helpers** to `SyncService`:
   ```dart
   Future<void> _loadLastSyncTime() async {
     final db = await _dbService.database;
     final rows = await db.query('sync_metadata',
       where: "key = ?", whereArgs: ['last_sync_time']);
     if (rows.isNotEmpty) {
       _lastSyncTime = DateTime.tryParse(rows.first['value'] as String);
     }
   }

   Future<void> _saveLastSyncTime(DateTime time) async {
     final db = await _dbService.database;
     await db.insert('sync_metadata',
       {'key': 'last_sync_time', 'value': time.toIso8601String()},
       conflictAlgorithm: ConflictAlgorithm.replace);
   }
   ```
4. **Call `_loadLastSyncTime()`** at the start of `syncAll()` (before the `_isOnline` check at line 386). This lazy-loads on first sync attempt.
5. **Replace** `_lastSyncTime = DateTime.now();` at lines 368 and 450 with:
   ```dart
   _lastSyncTime = DateTime.now();
   await _saveLastSyncTime(_lastSyncTime!);
   ```

**Rationale**: Persisting `_lastSyncTime` ensures cold starts after a successful sync skip the full-push path. Only genuinely first-ever syncs (or database wipes) trigger a full push.

### Task 0.3: Persist `SyncOrchestrator._lastSyncTime`

**Files**:
- `lib/features/sync/application/sync_orchestrator.dart` line ~46, ~135

**Problem**: The orchestrator has its own `_lastSyncTime` (also in-memory only). `SyncLifecycleManager._handleResumed()` reads `_syncOrchestrator.lastSyncTime` to decide staleness — always null on cold start → always forces sync.

**Steps**:
1. After `_syncWithRetry()` returns in `syncLocalAgencyProjects()`, read the SyncService's persisted `_lastSyncTime` through the adapter instead of maintaining a separate field:
   ```dart
   // In syncLocalAgencyProjects(), after _syncWithRetry():
   _lastSyncTime = DateTime.now();
   ```
2. **Alternative (simpler)**: Have the orchestrator read `_lastSyncTime` from the adapter's SyncService on initialization:
   ```dart
   Future<void> initialize() async {
     // ... existing init ...
     // Load persisted last sync time from adapter's SyncService
     final adapter = _localAgencyAdapter;
     if (adapter is SupabaseSyncAdapter) {
       _lastSyncTime = adapter.lastSyncTime;
     }
   }
   ```
3. Expose `lastSyncTime` getter on `SupabaseSyncAdapter` that delegates to `_legacySyncService.lastSyncTime`.

**Rationale**: One source of truth for last sync time (persisted in SQLite via SyncService), read by orchestrator on init.

### Task 0.4: Add Schema Errors to Non-Transient Error Patterns

**Files**:
- `lib/features/sync/application/sync_orchestrator.dart` lines 249-257

**Problem**: When the pull crashes on `test_results` (a `DatabaseException`), `_isTransientError()` defaults to `return true` at line 271 (treating unknown errors as transient). This triggers 3 retries, each pushing ALL local data again. Schema mismatches are deterministic — retrying cannot fix them.

**Steps**:
1. Add to the `nonTransientPatterns` list at line 249:
   ```dart
   'has no column',
   'DatabaseException',
   'no such column',
   'table has no column',
   ```
2. This ensures schema-mismatch errors fail fast (1 attempt) instead of retrying 3 times.

**Rationale**: Deterministic errors (schema mismatch, type errors) should not be retried. This prevents the 3x push amplification on every sync attempt.

### Task 0.5: Remove Orphan Standalone SyncService

**Files**:
- `lib/main.dart` lines 227, 269, 345, 477, 507

**Problem**: `main.dart:227` creates a standalone `SyncService` that is NEVER used for sync (the orchestrator creates its own internally). This orphan holds a live `Connectivity().onConnectivityChanged` subscription, has `setCompanyContext()` called on it uselessly (line 269), and could be accidentally used by future code for a rogue sync with no company context.

**Steps**:
1. Delete `final syncService = SyncService(dbService);` at line 227.
2. Delete `syncService.setCompanyContext(...)` call at line 269 (Task 1.2 replaces this with the orchestrator path).
3. Remove `syncService` from `ConstructionInspectorApp` constructor parameter (line 345) and stored field (line 477).
4. Verify no widget references `Provider<SyncService>` — all sync goes through `SyncProvider` → `SyncOrchestrator`.
5. If any widget still needs a `SyncService` reference, expose it through the orchestrator's adapter.

**Rationale**: Eliminates resource leak (duplicate connectivity listener), eliminates confusion vector (two SyncService instances with different company context), makes the architecture single-path.

### Phase 0 Quality Gate

1. `pwsh -Command "flutter analyze"` — no new issues
2. `pwsh -Command "flutter test"` — all existing tests pass
3. Manual verification:
   - [ ] Pull phase handles remote columns not in local schema (e.g., `test_results`) without crashing
   - [ ] Cold start after successful sync does NOT trigger full push (`[SYNC] Not first sync, skipping base data push`)
   - [ ] Schema error on pull does NOT trigger retry loop (check logs for retry count = 0)
   - [ ] No `SyncService` instance exists outside the orchestrator's adapter

---

## Phase 1: Sync Fix (Depends on Phase 0)

**Agent**: `backend-supabase-agent`
**Priority**: HIGH — sync is completely broken in production
**Depends on**: Phase 0 completed (column stripping + lastSyncTime persistence prevent corruption amplification)

### Task 1.1: Remove DNS Check from SyncService.syncAll()

**Files**:
- `lib/services/sync_service.dart` lines 397-410 — remove the `_checkDnsReachability()` block

**Steps**:
1. Delete the DNS reachability check block at lines 397-410 in `syncAll()`. The orchestrator layer (`SyncOrchestrator._syncWithRetry()` at lines 180-204) already performs DNS checks before each retry attempt via `SupabaseSyncAdapter.checkDnsReachability()`. Having DNS checks at both layers means DNS is checked 2-3 times per sync attempt (once in SyncService, once per retry in orchestrator, once in lifecycle manager).
2. Keep the `_isOnline` check at lines 386-395 (that is a lightweight connectivity_plus check, not DNS).
3. Keep the `_checkDnsReachability()` method itself — it is still called by `_scheduleDnsRetry()` for timer-based recovery.

**Rationale**: DNS checks should live at exactly ONE layer (the orchestrator). SyncService is a low-level push/pull engine; it should not make network reachability decisions.

### Task 1.2: Wire setCompanyContext() to Orchestrator's Internal Adapter

**Files**:
- `lib/main.dart` lines 264-274 — replace orphan calls with orchestrator calls
- `lib/features/sync/application/sync_orchestrator.dart` — add `setAdapterCompanyContext()` method

**Steps**:
1. Add a new method `setAdapterCompanyContext()` to `SyncOrchestrator` that delegates to `_localAgencyAdapter`:
   ```dart
   void setAdapterCompanyContext({String? companyId, String? userId}) {
     final adapter = _localAgencyAdapter;
     if (adapter is SupabaseSyncAdapter) {
       adapter.setCompanyContext(companyId: companyId, userId: userId);
     }
   }
   ```
2. In `main.dart`, update `updateSyncContext()` to call the orchestrator instead of the removed orphan syncService:
   ```dart
   void updateSyncContext() {
     final profile = authProvider.userProfile;
     final userId = authProvider.userId;
     final companyId = profile?.companyId;
     syncOrchestrator.setAdapterCompanyContext(companyId: companyId, userId: userId);
   }
   ```
3. Call during initial context setup and wire to auth listener.

**Rationale**: Without this, all sync operations via the orchestrator path lack `company_id` and `created_by_user_id`. This is a pre-existing bug hidden because sync was never completing.

### Task 1.3: Prevent Duplicate onSyncComplete During Retries

**Files**:
- `lib/features/sync/application/sync_orchestrator.dart` lines 115-118, 130-134
- `lib/features/sync/data/adapters/supabase_sync_adapter.dart` lines 87-89

**Problem chain**:
1. `SyncService.syncAll()` fires `onSyncComplete` at line 474
2. `SupabaseSyncAdapter.initialize()` wires `_legacySyncService.onSyncComplete` to `onSyncComplete?.call()` (line 87-88)
3. `SyncOrchestrator.initialize()` wires `_localAgencyAdapter.onSyncComplete` to `onSyncComplete?.call()` (line 115-117)
4. `SyncProvider._setupListeners()` wires `_syncOrchestrator.onSyncComplete` to increment `_consecutiveFailures` (line 33-46)
5. When `_syncWithRetry()` calls `syncAll()` 3 times (attempt + 2 retries), `_consecutiveFailures` gets incremented 3 times from ONE logical sync operation.

**Steps**:
1. **Remove adapter wiring** at `sync_orchestrator.dart` lines 115-118.
2. **Fire `onSyncComplete` directly** from `syncLocalAgencyProjects()`, ONCE after `_syncWithRetry()` returns:
   ```dart
   final result = await _syncWithRetry();
   _updateStatus(result.hasErrors ? SyncAdapterStatus.error : SyncAdapterStatus.success);
   _lastSyncTime = DateTime.now();
   onSyncComplete?.call(result);  // Fire exactly once
   ```
3. These two steps are **atomic** — both must be done together.

**Rationale**: The UI should see exactly ONE completion event per logical sync operation.

### Task 1.4: Fix Orphan Cleanup Two-Pass Dead Code

**Files**:
- `lib/services/startup_cleanup_service.dart`

**Problem**: `run()` calls `_cleanupOrphanedProjects()` once. The two-pass logic needs two calls within the same repository instance lifetime.

**Steps**:
1. Call `cleanupOrphanedProjects()` twice in sequence (Option A):
   ```dart
   Future<void> _cleanupOrphanedProjects() async {
     try {
       await _projectRepository.cleanupOrphanedProjects();  // Pass 1: mark
       final orphanedCount = await _projectRepository.cleanupOrphanedProjects();  // Pass 2: delete
       if (orphanedCount > 0) {
         DebugLogger.db('Cleaned up $orphanedCount orphaned projects on startup');
       }
     } catch (e) {
       DebugLogger.error('Startup orphan cleanup failed: $e');
     }
   }
   ```
2. In `project_repository.dart:184`, replace `orphans.firstWhere` with `.where(...).firstOrNull` + null guard.

### Task 1.5: Fix SyncStatusBanner Dismiss Reset (LOW)

**Files**:
- `lib/features/sync/presentation/widgets/sync_status_banner.dart` lines 144-148

**Steps**:
1. Only reset `_isDismissed` when transitioning FROM non-error TO new error state.
2. Move state mutation out of `build()` into `didChangeDependencies()` or `addPostFrameCallback()`.
3. Replace status-change logic:
   ```dart
   if (syncProvider.status != _lastStatus) {
     final wasError = _lastStatus == SyncAdapterStatus.error ||
         _lastStatus == SyncAdapterStatus.offline;
     final isError = syncProvider.status == SyncAdapterStatus.error ||
         syncProvider.status == SyncAdapterStatus.offline;
     _lastStatus = syncProvider.status;
     if (isError && !wasError) {
       _isDismissed = false;
     }
   }
   ```

### Phase 1 Quality Gate

1. `pwsh -Command "flutter analyze"` — no new issues
2. `pwsh -Command "flutter test"` — all existing tests pass
3. Manual verification:
   - [ ] DNS check only fires once per sync attempt
   - [ ] `_consecutiveFailures` increments by exactly 1 per logical sync failure
   - [ ] Company context reaches SyncService inside SupabaseSyncAdapter
   - [ ] Banner stays dismissed after user taps close, until a new error category appears

---

## Phase 2: PDF Extraction Fix (Can run parallel with Phase 0)

**Agent**: `pdf-agent`
**Priority**: HIGH — budget display is $357B instead of ~$7.88M

### Task 2.1: Revert Crop Upscaler to Uniform DPI

**Files**:
- `lib/features/pdf/services/extraction/shared/crop_upscaler.dart` lines 22-30, 118-144

**Steps**:
1. Remove the geometry-aware constants (`kBoostDpi`, `kWidthCeiling`).
2. Simplify `computeScaleFactor()` to use uniform DPI:
   ```dart
   double computeScaleFactor(double renderDpi, int width, int height) {
     if (!renderDpi.isFinite || renderDpi <= 0 || width <= 0 || height <= 0) {
       return 1.0;
     }
     if (renderDpi >= kTargetDpi) return 1.0;
     final dpiScale = kTargetDpi / renderDpi;
     final outputCap = min(
       kMaxScaleFactor,
       min(kMaxOutputDimension / width, kMaxOutputDimension / height),
     );
     final maxAllowedScale = outputCap < 1.0 ? 1.0 : outputCap;
     return min(dpiScale, maxAllowedScale).clamp(1.0, kMaxScaleFactor).toDouble();
   }
   ```

**Rationale**: The geometry-aware boost (up to 900 DPI for narrow columns) causes comma/period confusion in Tesseract, inflating unitPrice 1000x via math backsolve.

### Task 2.2: Update Crop Upscaler Tests

**Files**:
- `test/features/pdf/extraction/shared/crop_upscaler_test.dart`

**Steps**:
1. Remove test cases asserting geometry-aware boost behavior.
2. Ensure all tests assert uniform kTargetDpi=600 scaling regardless of crop width.
3. Verify edge cases: renderDpi >= 600 returns 1.0, renderDpi=0 returns 1.0, etc.

### Task 2.3: Preserve bidAmount Through ResultConverter into BidItem Model

**Files**:
- `lib/features/quantities/data/models/bid_item.dart` — add `bidAmount` field
- `lib/core/database/schema/quantity_tables.dart` — add `bid_amount` column to schema
- `lib/core/database/database_service.dart` — migration (combined with sync_metadata in Phase 0)
- `lib/features/pdf/data/models/parsed_bid_item.dart` — add `bidAmount` field, update `toBidItem()`, update `fromBidItem()`
- `lib/features/pdf/services/extraction/pipeline/result_converter.dart` — pass bidAmount

**Steps**:
1. **Add `bidAmount` to `BidItem` model** (`bid_item.dart`):
   - Add `final double? bidAmount;` field
   - Add to constructor, `copyWith()`, `toMap()` (key: `'bid_amount'`), `fromMap()`

2. **Add column to SQLite schema** (`quantity_tables.dart`):
   - Add `bid_amount REAL` to the CREATE TABLE statement (after `unit_price`)

3. **Migration** (combined with Task 0.2 in `database_service.dart`):
   - DB version bump to 25 covers both `sync_metadata` table and `bid_amount` column:
     ```dart
     if (oldVersion < 25) {
       await db.execute('CREATE TABLE IF NOT EXISTS sync_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)');
       await _addColumnIfNotExists(db, 'bid_items', 'bid_amount', 'REAL');
     }
     ```

4. **Pass bidAmount in ResultConverter** (`result_converter.dart`):
   - Add `bidAmount` field to legacy `ParsedBidItem` (constructor + copyWith)
   - Update `ResultConverter.toPdfImportResult()` to pass `bidAmount: v2Item.bidAmount`
   - Update `ParsedBidItem.toBidItem()` to pass `bidAmount: bidAmount`

5. **Update `ParsedBidItem.fromBidItem()` factory** (`parsed_bid_item.dart:77-91`):
   - Add `bidAmount: item.bidAmount` to the constructor call.
   - Called at `pdf_import_service.dart:64` for PDF re-imports.

6. **Supabase migration + push safety net** (REVISED — Rev 3):
   - **Option A**: Add Supabase migration: `ALTER TABLE bid_items ADD COLUMN bid_amount REAL;`
   - **Option B (NEW — safety net)**: ALSO strip `bid_amount` from `_convertForRemote()` payload:
     ```dart
     // In _convertForRemote(), after existing conversions:
     if (tableName == 'bid_items') {
       result.remove('bid_amount');  // Local-only until Supabase migration confirmed
     }
     ```
   - **Decision**: Implement BOTH. Option B is the safety net — if the Supabase migration is delayed or fails, bid item sync still works (just without `bid_amount` remotely). Remove the Option B strip after confirming the migration is applied.
   - **NOTE**: Task 0.1's `_convertForLocal()` column stripping also protects the PULL direction — if a remote `bid_amount` column arrives before a local schema update, it gets stripped.

**Rationale**: The v2 pipeline correctly extracts `bidAmount` but it is LOST at the `ResultConverter` boundary. Dual safety (Option A + B) prevents sync breakage regardless of migration timing.

### Task 2.4: Use bidAmount for Budget Calculation Across ALL Display Sites

**Files** (REVISED — Rev 3, added site 6):
- `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` lines 309-318
- `lib/features/quantities/presentation/widgets/bid_item_detail_sheet.dart` line 33
- `lib/features/quantities/presentation/widgets/bid_item_card.dart` line 20
- `lib/features/quantities/presentation/screens/quantities_screen.dart` lines 147, 244-245
- `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart` lines 396-399 **(NEW — Rev 3)**

**Steps**:
1. **Dashboard totalBudget** — prefer `bidAmount`:
   ```dart
   final itemValue = item.bidAmount ?? (item.bidQuantity * (item.unitPrice ?? 0));
   totalBudget += itemValue;
   ```
2. **Dashboard totalUsed** — derive unit price from `bidAmount / bidQuantity` when available:
   ```dart
   final effectiveUnitPrice = (item.bidAmount != null && item.bidQuantity > 0)
       ? item.bidAmount! / item.bidQuantity
       : (item.unitPrice ?? 0);
   totalUsed += usedQty * effectiveUnitPrice;
   ```
3. **Bid Item Detail Sheet** — at `bid_item_detail_sheet.dart:33`, same `bidAmount ??` pattern.
4. **Bid Item Card** — at `bid_item_card.dart:20`, same pattern.
5. **Quantities Screen** — at `quantities_screen.dart:147` and `:244-245`, same pattern.
6. **(NEW — Rev 3) PDF Import Preview** — at `pdf_import_preview_screen.dart:396-399`, when `ParsedBidItem.bidAmount` is available, show `effectiveUnitPrice = bidAmount / bidQuantity` and/or the total `bidAmount`. This is the last user-visible quality gate before import — showing inflated `unitPrice` here defeats its purpose.

**Rationale**: All 6 display sites use `bidQuantity * unitPrice`. Corrupted `unitPrice` (1000x inflated) propagates to all of them. Using `bidAmount` as source of truth at every site provides defense-in-depth.

### Task 2.5: Regenerate Golden Fixtures

**Files**:
- `test/features/pdf/extraction/fixtures/*.json`

**Steps**:
1. After reverting the upscaler, regenerate all golden fixtures:
   ```
   pwsh -Command "flutter test integration_test/generate_golden_fixtures_test.dart -d windows --dart-define='SPRINGFIELD_PDF=C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf'"
   ```
2. Verify 131 items / 0.993 quality / $7.88M baseline.
3. Run golden test: `pwsh -Command "flutter test test/features/pdf/extraction/golden/"`

**Note**: Requires Springfield PDF on disk (BLOCKER-10). If unavailable, defer fixture regen.

### Phase 2 Quality Gate

1. `pwsh -Command "flutter analyze"` — no new issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Verification:
   - [ ] `CropUpscaler.computeScaleFactor()` returns uniform scale for all crop widths
   - [ ] `BidItem.bidAmount` persists through SQLite round-trip
   - [ ] Dashboard budget displays ~$7.88M (not $357B)
   - [ ] PDF import preview shows correct unitPrice from bidAmount
   - [ ] Golden fixtures show 131 items / 0.993 quality score

---

## Phase 3: Regression Guards

**Agent**: `qa-testing-agent`
**Priority**: MEDIUM — prevents future regressions
**Depends on**: Phase 0 + Phase 1 + Phase 2 completed

### Task 3.1: Budget Sanity Check (REVISED — Rev 3)

**Files**:
- `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`
- `lib/features/quantities/presentation/screens/quantities_screen.dart` **(NEW — Rev 3)**

**Steps**:
1. Extract sanity check logic into a shared utility:
   ```dart
   // lib/features/quantities/utils/budget_sanity_checker.dart
   class BudgetSanityChecker {
     static bool hasDiscrepancy(List<BidItem> items, {double threshold = 0.10}) {
       double recalculated = 0, fromBidAmount = 0;
       int bidAmountCount = 0;
       for (final item in items) {
         recalculated += item.bidQuantity * (item.unitPrice ?? 0);
         if (item.bidAmount != null) {
           fromBidAmount += item.bidAmount!;
           bidAmountCount++;
         }
       }
       return bidAmountCount > 0 && recalculated > 0 &&
           ((fromBidAmount - recalculated).abs() / recalculated) > threshold;
     }
   }
   ```
2. Use in both `project_dashboard_screen.dart` and `quantities_screen.dart`.
3. Show amber warning chip and log via `DebugLogger.db()`.

### Task 3.2: Golden Assertion for Individual Item Values

**Files**:
- `test/features/pdf/extraction/golden/springfield_golden_test.dart`

**Steps**:
1. Add spot-check assertions for items that had comma/period errors:
   ```dart
   final item39 = items.firstWhere((i) => i.itemNumber == '39');
   expect(item39.quantity, closeTo(9235, 1));
   expect(item39.unitPrice, closeTo(139.1, 0.1));
   expect(item39.bidAmount, closeTo(1284588.50, 1));
   ```
2. Cover items 12, 15, 38, 39, 52, 62, 64, 73, 121.

### Task 3.3: Sync Consecutive Failure Count Test

**Files**:
- `test/features/sync/presentation/providers/sync_provider_test.dart`

**Steps**:
1. Verify `_consecutiveFailures` increments by exactly 1 per logical sync operation.
2. Verify reset to 0 on success.

### Task 3.4: SyncService Data-Handling Tests (NEW — Rev 3)

**Files**:
- `test/services/sync_service_test.dart` (new)

**Steps**:
1. Test that pulling a record with unknown column does NOT throw (validates Task 0.1).
2. Test that `_pushBaseData` does NOT push all data when `_lastSyncTime` is non-null (validates Task 0.2).
3. Test that boolean conversion works for all table/column pairs.
4. Test `ParsedBidItem.fromBidItem()` round-trip preserves `bidAmount` (validates Task 2.3 step 5).

### Phase 3 Quality Gate

1. `pwsh -Command "flutter analyze"` — no new issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Verification:
   - [ ] Budget discrepancy warning appears on both dashboard and quantities screen
   - [ ] Golden test catches comma/period swaps at item level
   - [ ] Sync failure count test validates exactly-once semantics
   - [ ] SyncService data-handling tests all pass

---

## File Overlap Analysis (Parallel Safety)

| File | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Conflict? |
|------|---------|---------|---------|---------|-----------|
| `lib/services/sync_service.dart` | Task 0.1, 0.2 | Task 1.1 | — | — | **Phase 0→1 sequential** |
| `lib/main.dart` | Task 0.5 | Task 1.2 | — | — | **Phase 0→1 sequential** |
| `lib/features/sync/application/sync_orchestrator.dart` | Task 0.3, 0.4 | Task 1.2, 1.3 | — | — | **Phase 0→1 sequential** |
| `lib/core/database/database_service.dart` | Task 0.2 | — | Task 2.3 | — | **Phase 0+2 share migration block** |
| `lib/features/sync/data/adapters/supabase_sync_adapter.dart` | — | Task 1.3 | — | — | No |
| `lib/services/startup_cleanup_service.dart` | — | Task 1.4 | — | — | No |
| `lib/features/sync/presentation/widgets/sync_status_banner.dart` | — | Task 1.5 | — | — | No |
| `lib/features/pdf/services/extraction/shared/crop_upscaler.dart` | — | — | Task 2.1 | — | No |
| `lib/features/quantities/data/models/bid_item.dart` | — | — | Task 2.3 | — | No |
| `lib/core/database/schema/quantity_tables.dart` | — | — | Task 2.3 | — | No |
| `lib/features/pdf/data/models/parsed_bid_item.dart` | — | — | Task 2.3 | — | No |
| `lib/features/pdf/services/extraction/pipeline/result_converter.dart` | — | — | Task 2.3 | — | No |
| `lib/features/quantities/presentation/widgets/*` | — | — | Task 2.4 | — | No |
| `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart` | — | — | Task 2.4 | — | No |
| `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` | — | — | Task 2.4 | Task 3.1 | **Phase 2→3 sequential** |
| `lib/features/quantities/presentation/screens/quantities_screen.dart` | — | — | Task 2.4 | Task 3.1 | **Phase 2→3 sequential** |
| `test/**` | — | — | Task 2.5 | Task 3.2-3.4 | **Phase 2→3 sequential** |

**Key**: Phase 0 and Phase 2 share `database_service.dart` (migration block only — combine into single version bump). Phase 0 touches `sync_service.dart` and `sync_orchestrator.dart` which Phase 1 also needs — hence Phase 0 MUST complete first. Phase 2 is fully independent of Phase 0/1.

---

## Agent Assignments Summary

| Phase | Agent | Can Run In Parallel? |
|-------|-------|---------------------|
| Phase 0 (Sync Data-Flow) | `backend-supabase-agent` | Yes — parallel with Phase 2 |
| Phase 1 (Sync Fix) | `backend-supabase-agent` | No — after Phase 0 |
| Phase 2 (PDF Fix) | `pdf-agent` + `backend-data-layer-agent` | Yes — parallel with Phase 0 |
| Phase 3 (Guards) | `qa-testing-agent` | No — after Phase 0 + 1 + 2 |

## Commit Strategy

1. **Commit A** (sync data-flow fix): Phase 0 changes on `fix/sync-dns-resilience`
2. **Commit B** (sync fix): Phase 1 changes on `fix/sync-dns-resilience`
3. **Commit C** (PDF extraction fix): Phase 2 changes on `fix/sync-dns-resilience` (or new branch)
4. **Commit D** (regression guards): Phase 3 changes
5. Supabase migration (`ALTER TABLE bid_items ADD COLUMN bid_amount REAL; ALTER TABLE daily_entries DROP COLUMN IF EXISTS test_results;`) deployed between Commits C and D

## Risk Assessment (REVISED — Rev 3)

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| **Deploying Phase 1 before Phase 0 accelerates corruption** | **HIGH** | Phase 0 MUST complete first. Plan ordering enforces this. |
| **`_convertForLocal()` async change breaks call sites** | Medium | Only one call site (line 1228). Add `await` and verify. |
| **`_lastSyncTime` persistence migration fails on old devices** | Low | `CREATE TABLE IF NOT EXISTS` is idempotent. `sync_metadata` is independent. |
| **bid_amount in toMap() breaks Supabase sync** | Medium (was HIGH) | Option A + Option B safety net. Strip `bid_amount` from `_convertForRemote()` until migration confirmed. |
| **Remote `test_results` column on Supabase** | Medium | Task 0.1 column stripping handles this generically. Also deploy `ALTER TABLE daily_entries DROP COLUMN IF EXISTS test_results;` to Supabase. |
| Golden fixture regen blocked by missing PDF (BLOCKER-10) | Medium | Verify upscaler revert via unit tests; defer fixture regen |
| Removing orphan SyncService breaks widgets | Low | Grep for `Provider<SyncService>` and `SyncService` in widget tree. All sync goes through `SyncOrchestrator`. |
| Schema error non-transient classification is too broad | Low | Only add specific patterns (`has no column`, `DatabaseException`). Unknown errors still retry by default. |
| SyncLifecycleManager callback wiring race on slow devices | Low | Narrow window. Next app resume re-triggers. Fix deferred to future cleanup. |
