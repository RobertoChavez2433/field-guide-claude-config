# Defects: Sync

Active patterns for sync. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [SYNC] 2026-03-28: Unconditional change_log wipe after soft-delete cascade loses deletions when RPC fails (BUG-S09)
**Pattern**: `cascadeSoftDeleteProject()` deleted ALL unprocessed change_log entries and removed from synced_projects unconditionally. When the Supabase RPC failed (offline, JWT expiry), the change_log entries created by UPDATE triggers were wiped, leaving no mechanism to sync the deletion.
**Prevention**: Any cleanup of change_log or synced_projects after a server-dependent operation must be conditional on the server call succeeding. Use a `rpcSucceeded` flag to gate cleanup.
**Ref**: @lib/services/soft_delete_service.dart:132-143

### [SYNC] 2026-03-28: ConflictAlgorithm.ignore silently drops valid records on UNIQUE slot collision (BUG-S10-1)
**Pattern**: Pull path uses `ConflictAlgorithm.ignore` which silently drops INSERTs when a soft-deleted local record occupies the same UNIQUE slot (not just PK). Affects project_assignments (UNIQUE on project_id+user_id) and any table with multi-column UNIQUE constraints.
**Prevention**: When insert returns rowId==0, fall back to UPDATE by PK. Added in S667 at sync_engine.dart:1530.
**Ref**: @lib/features/sync/engine/sync_engine.dart:1530

### [SYNC] 2026-03-28: getUnprocessedChanges had no retry_count filter — infinite failure loop (BUG-S10-2)
**Pattern**: `change_tracker.getUnprocessedChanges()` queried `WHERE processed = 0` with no retry_count cap. Entries that failed 5+ times kept being retried every sync cycle, causing persistent error snackbars.
**Prevention**: Always filter exhausted entries: `AND retry_count < maxRetryCount`. Added in S667. Exhausted entries auto-purge after 7 days via `purgeOldFailures()`.
**Ref**: @lib/features/sync/engine/change_tracker.dart:68

### [DATA] 2026-03-28: Child table models must include project_id in toMap() for sync push (BUG-S02-1/2)
**Pattern**: entry_contractors and entry_quantities toMap() omitted project_id. The sync engine reads raw SQLite rows for push, so if the column is NULL in the DB, it pushes NULL to Supabase. Missing project_id breaks RLS-based pull to other devices.
**Prevention**: All synced child tables must: (1) include project_id field in Dart model, (2) include it in toMap(), (3) auto-resolve from parent entry on insert if not provided. Cross-reference entry_equipment for the correct pattern. Fixed in S667.
**Ref**: @lib/features/quantities/data/models/entry_quantity.dart, @lib/features/contractors/data/datasources/local/entry_contractors_local_datasource.dart

### [CONFIG] 2026-03-27: Seeded data invisible without project_assignments
**Pattern**: Inserting bid_items directly into Supabase is not enough for sync. The sync engine requires a `project_assignments` row for the user to enroll the project into `synced_projects`. Without it, `_syncedProjectIds` is empty and all `viaProject` adapters skip the project entirely.
**Prevention**: When seeding project data in Supabase, always create a `project_assignments` row for target users. The enrollment chain is: `project_assignments` pull → `_enrollProjectsFromAssignments()` → `synced_projects` → child adapters pull.
**Ref**: `lib/features/sync/engine/sync_engine.dart:1644` (`inFilter('project_id', _syncedProjectIds)`)

### [CONFIG] 2026-03-27: enforce_created_by trigger nullifies service role inserts
**Pattern**: `enforce_created_by()` trigger stamps `created_by_user_id = auth.uid()`. When using service role key, `auth.uid()` returns NULL, so all inserted rows have `created_by_user_id = NULL` — even if explicitly set in the INSERT. This can break FK constraints and RLS visibility.
**Prevention**: For seeding, authenticate as a real user via OTP flow (`admin.generateLink` + `verifyOtp`) rather than using the service role key directly.
**Ref**: `supabase/migrations/20260222100000_multi_tenant_foundation.sql:358`

## Recently Fixed (Session 667)

### BUG-S02-1/2: entry_contractors/entry_quantities missing project_id (S666→S667)
**Fix**: Added projectId field to both models + toMap(). Override insert() in quantity datasource to auto-resolve from parent entry. v42 migration backfills NULLs. Added to tablesWithDirectProjectId. Triggers reinstalled.

### BUG-S10-2: Corrupted change_log infinite retry loop (S666→S667)
**Fix**: Added retry_count < maxRetryCount filter to getUnprocessedChanges(). Added PK collision guard in ID remap. v42 migration cleans orphaned entries.

### BUG-S10-1: Assignment pull silently dropped by UNIQUE constraint (S666→S667)
**Fix**: Pull path now falls back to UPDATE by PK when insert returns rowId==0.

### BUG-S03-1: Photo file_path NOT NULL blocks cross-device pull (S666→S667)
**Fix**: Made photos.file_path nullable in SQLite (v42 migration recreates table). Matches Supabase schema.

### BUG-S09-1: Inspector sees admin's trash (S666→S667)
**Fix**: Trash screen now filters by deleted_by for non-admins. Table list restricted. Empty trash scoped.

## Previously Fixed (Session 614)

### BUG-A: _pushDelete missing server timestamp writeback (Session 613→614)
**Fix**: Added `.select('updated_at, deleted_by')` + writeback with `pulling='1'` suppression. Added `conflicts`/`skippedFk` to `SyncEngineResult`. Verified via H001-H005 hypothesis markers.

### BUG-17: Re-login wipes all data (Session 608→610)
**Fix**: Removed `clearLocalCompanyData` from logout. Added company-switch guard in `signIn()`. Auto-enrollment via `_enrollProjectsFromAssignments()`.

### BUG-15: Integrity RPC cascade failure (Session 608→610)
**Fix**: Migration `20260320000003` added `entry_contractors` to allowlist, switched to `RETURNS TABLE`, fixed alias bug.

### BUG-006: Stale _isOnline flag (Session 591→610)
**Fix**: `checkDnsReachability()` called before every `isSupabaseOnline` read in `project_list_screen.dart` + defense-in-depth inside `_syncWithRetry()`.

### BUG-005: synced_projects enrollment gap (Session 591→610)
**Fix**: `_enrollProjectsFromAssignments()` runs unconditionally after `project_assignments` pull. Fresh-restore cursor guard. Orphan cleaner deadlock prevention via `_projectsAdapterCompleted`.

<!-- Add defects above this line -->
