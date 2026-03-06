# Defects: Sync

Active patterns for sync. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [DATA] 2026-03-05: PostgREST error codes are PGRST*, not HTTP status codes (Session 504)
**Pattern**: Plan checked `PostgrestException.code == '401'` / `'429'` / `'503'`, but `.code` contains PostgREST codes like `'PGRST301'`, `'PGRST116'`, never raw HTTP status codes. All error handling checks silently failed to match.
**Prevention**: Always check PostgREST codes (PGRST301=JWT, PGRST304=RLS, PGRST116=not found) with message-based fallbacks. Never assume HTTP status codes on Supabase exceptions.
**Ref**: @lib/services/sync_service.dart (_isTransientError pattern), plan FIX C5

### [DATA] 2026-03-05: Plan-stage API drift — code samples reference non-existent methods/properties (Session 503)
**Pattern**: Multi-part plans written by different agents reference APIs that don't exist in the codebase or contradict each other (e.g., `adapter.readLocal()` when adapters are config-only, `provider.hasErrors` when actual getter is `hasPersistentSyncFailure`, 3 conflicting RPC definitions). Causes compile failures when implementing.
**Prevention**: Every code sample in a plan must be verified against the actual codebase interface before finalizing. Per-phase review agents should cross-reference all method/property/type names against the codebase.
**Ref**: Phase 5 (3 conflicting RPCs), Phase 6 (5 wrong API refs), Phase 4 (competing implementations)

### [DATA] 2026-03-05: Fresh-install path neglected in migrations (Session 503)
**Pattern**: `_onUpgrade` migrations add tables/columns/triggers but `_onCreate` and schema file constants are never updated. Fresh installs at the new version skip `_onUpgrade` entirely and get stale schemas (missing columns, wrong defaults, no triggers).
**Prevention**: Every migration change MUST also update: (1) the schema file constant, (2) `_onCreate` calls, (3) `SchemaVerifier` column lists. Add a "fresh-install gate" test.
**Ref**: Phase 1 review — 6 critical issues from neglected _onCreate

### [DATA] 2026-03-04: sync_status leaks to Supabase — infinite pending loop (Session 493, FIXED)
**Pattern**: `sync_status` column existed on both SQLite and Supabase. Push sent `sync_status='pending'` to Supabase. Pull returned it back, overwriting local `'synced'` → permanent "2 pending changes" that never clear. Any column meant as local-only tracking must be stripped from all remote I/O paths.
**Prevention**: FIXED by (1) stripping sync_status from `_convertForRemote()` + both remote datasource `toMap()`, (2) forcing `'synced'` in `_convertForLocal()`, (3) dropping column from Supabase. Rule: local-only columns must be stripped at BOTH push and pull boundaries.
**Ref**: @lib/services/sync_service.dart (_convertForRemote, _convertForLocal), @lib/features/entries/data/datasources/remote/daily_entry_remote_datasource.dart, @lib/features/photos/data/datasources/remote/photo_remote_datasource.dart

### [DATA] 2026-03-04: Hard-delete resurrection — local DELETE not propagated to Supabase (Session 491, FIXED)
**Pattern**: `ProjectRepository.delete()` did hard `DELETE FROM projects` in SQLite but never called `queueOperation('projects', id, 'delete')`. Next sync pull re-inserted the project from Supabase. Systemic — affected all synced tables. No `deleted_at` column existed anywhere.
**Prevention**: FIXED by soft-delete system (Session 491). All deletes now set `deleted_at` + `deleted_by`. Sync propagates soft-deletes bidirectionally. 30-day purge cleans up.
**Ref**: @lib/services/soft_delete_service.dart, @lib/shared/datasources/generic_local_datasource.dart

<!-- Add defects above this line -->
