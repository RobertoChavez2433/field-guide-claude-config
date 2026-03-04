# Defects: Sync

Active patterns for sync. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [ASYNC] 2026-03-03: _handleResumed() must await security callbacks before sync
**Pattern**: Synchronous `void _handleResumed()` calls `onAppResumed?.call()` (returns Future) without awaiting. Security checks (inactivity timeout, config refresh) race with sync trigger.
**Prevention**: Make lifecycle handlers `async` when they invoke async callbacks. Always await security checks before evaluating sync readiness.
**Ref**: @lib/features/sync/application/sync_lifecycle_manager.dart:74-88

### [DATA] 2026-03-02: _convertForLocal() Does Not Strip Unknown Columns (Session 480)
**Pattern**: Doc comment claims "Strips unknown columns not present in local schema" but implementation does ZERO stripping. When Supabase returns columns not in local SQLite (e.g., `daily_entries.test_results` dropped in migration 18->19), `_upsertLocalRecords` INSERT throws `DatabaseException: table has no column named test_results`. Pull phase crashes entirely. Systemic — affects ANY future schema drift.
**Prevention**: Implement actual column stripping via `PRAGMA table_info()` with caching. Strip unknown keys from result map before INSERT/UPDATE.
**Ref**: @lib/services/sync_service.dart:755-801

### [DATA] 2026-03-02: _lastSyncTime In-Memory Only — Full Push Every Cold Start (Session 480)
**Pattern**: `_lastSyncTime` is `DateTime?` in memory (line 136). Every cold start = null. `_pushBaseData()` checks `_lastSyncTime == null` → treats as first sync → pushes ALL local data unconditionally. Push happens BEFORE pull (line 488 vs 442), so corrupted data reaches Supabase before corrections arrive. Same problem on `SyncOrchestrator._lastSyncTime`.
**Prevention**: Persist `_lastSyncTime` to SQLite `sync_metadata` table. Load on init, save after successful sync.
**Ref**: @lib/services/sync_service.dart:136,609, @lib/features/sync/application/sync_orchestrator.dart:46

### [DATA] 2026-03-02: Schema Errors Classified as Transient — 3x Retry Amplification (Session 480)
**Pattern**: `_isTransientError()` defaults `return true` for unknown errors (line 271). SQLite `DatabaseException` (schema mismatch) matches no non-transient pattern → retries 3x. Each retry pushes ALL local data again (due to in-memory `_lastSyncTime`), amplifying corruption propagation.
**Prevention**: Add `'has no column'`, `'DatabaseException'`, `'no such column'` to `nonTransientPatterns` in `_isTransientError()`.
**Ref**: @lib/features/sync/application/sync_orchestrator.dart:249-271

### [TEST] 2026-03-03: entry_equipment and entry_quantities pull fails — wrong column in Supabase query (auto-test)
**Status**: OPEN
**Source**: Automated test run 2026-03-03-1933-run.md
**Symptom**: During manual sync via "Sync Now", pull phase logs two errors:
  - `ERROR pulling entry_equipment chunk at offset 0: PostgrestException(message: column entry_equipment.created_at does not exist, code: 42703, hint: Perhaps you meant to reference the column "entry_equipment.updated_at".)`
  - `ERROR pulling entry_quantities chunk at offset 0: PostgrestException(message: column entry_quantities.created_at does not exist, code: 42703, hint: Perhaps you meant to reference the column "entry_quantities.updated_at".)`
Both tables return 0 records. `SyncResult.errors` reports 0 (errors swallowed). UI shows "Synced" despite pull failures for these tables.
**Logcat**: `[SYNC] ERROR pulling entry_equipment chunk at offset 0: PostgrestException(message: column entry_equipment.created_at does not exist, code: 42703...)` / `[SYNC] ERROR pulling entry_quantities chunk at offset 0: PostgrestException(message: column entry_quantities.created_at does not exist, code: 42703...)`
**Screenshot**: sync-check-final.png (UI shows Synced with no error indication)
**Suggested cause**: The Supabase query for `entry_equipment` and `entry_quantities` orders/filters by `created_at`, but those tables use `updated_at` as the timestamp column. Likely a schema migration renamed or omitted `created_at` on these tables. Fix: update pull query column reference from `created_at` to `updated_at` for these two tables. Also: SyncResult should count pull-phase PostgrestExceptions as errors so UI accurately reflects partial sync failure.

### [TEST] 2026-03-03: pullCompanyMembers FOREIGN KEY constraint failure silently drops user_profiles sync (auto-test)
**Status**: OPEN
**Source**: Automated test run 2026-03-03-1933-run.md
**Symptom**: `[SYNC] SyncOrchestrator: pullCompanyMembers failed: DatabaseException(FOREIGN KEY constraint failed (code 787 SQLITE_CONSTRAINT_FOREIGNKEY[787])) sql 'INSERT INTO user_profiles ...'`. User profile record (id=88054934-9cc5-4af3-b1c6-38f262a7da23) fails to upsert locally. Error swallowed — UI shows "Synced".
**Logcat**: `[SYNC] [19:42:26.246] SyncOrchestrator: pullCompanyMembers failed: DatabaseException(FOREIGN KEY constraint failed (code 787 SQLITE_CONSTRAINT_FOREIGNKEY[787])) sql 'INSERT INTO user_profiles (id, display_name, phone, position, company_id, role, status, last_synced_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)' args [88054934-9cc5-4af3-b1c6-38f262a7da23, Robert Sebastian, (616) 370-5927, Construction Technician, 26fe92cd-7044-4412-9a09-5c5f49a292f9, admin, approved, ...]`
**Screenshot**: sync-check-final.png
**Suggested cause**: user_profiles INSERT references a company_id or related FK that doesn't yet exist in local SQLite. Could be ordering issue (companies table not yet populated when user_profiles is pulled), or FK constraint on a column that references a record not yet local. Fix: ensure companies are pulled before user_profiles, or use `PRAGMA foreign_keys = OFF` selectively for sync upserts, or upsert with INSERT OR REPLACE and deferred FK checks.

<!-- Add defects above this line -->
