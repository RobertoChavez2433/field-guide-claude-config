# Defects: Sync

Active patterns for sync. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [DATA] 2026-03-20: Re-login wipes all data — project enrollment broken after clearLocalCompanyData — BUG-17 (Session 608)
**Pattern**: `clearLocalCompanyData` wipes ALL SQLite tables on sign-out. On re-login, sync pulls project metadata but marks them as "available (unenrolled)". All 15 child table pulls skip with "no loaded projects". Tapping project card + manual sync don't fix it — projects never register as "loaded". User sees project names but 0 entries, 0 pay items, 0 contractors.
**Prevention**: After re-login sync, auto-enroll all company projects in `synced_projects`. Or: `fetchRemoteProjects` must populate `synced_projects` for every project it downloads, not just mark them "available".
**Ref**: @lib/features/sync/engine/sync_engine.dart, @lib/features/auth/data/datasources/auth_service.dart

### [DATA] 2026-03-20: Integrity RPC returns -1 for ALL tables — cascade failure from missing entry_contractors — BUG-15 (Session 608)
**Pattern**: `get_table_integrity()` RPC has a hardcoded allowlist. `entry_contractors` is NOT in the list, causing P0001 error. This cascade-fails the entire RPC, returning -1 for ALL 16 tables. Integrity drift detection is completely non-functional.
**Prevention**: Keep the RPC allowlist in sync with the app's sync registry. Add `entry_contractors` with proper 2-hop company scoping (entry_id → daily_entries.project_id → projects.company_id).
**Ref**: @supabase/migrations/20260320000001_fix_integrity_rpc.sql

### [DATA] 2026-03-18: _refresh() silently skips sync based on stale _isOnline flag — BUG-006 (Session 591)
**Pattern**: `project_list_screen._refresh()` checks `orchestrator.isSupabaseOnline` before calling `syncLocalAgencyProjects()`. Once `_isOnline=false` (from any SocketException), `_refresh()` never calls `checkDnsReachability()` to re-test — it just reads the stale cached flag. Manual sync button becomes a no-op with zero user feedback. Only `fetchRemoteProjects()` (local SQLite read) runs, giving illusion of activity.
**Prevention**: Always call `checkDnsReachability()` in `_refresh()` before checking `isSupabaseOnline`. Or remove the gate entirely and let `syncLocalAgencyProjects()` handle connectivity internally via its retry logic.
**Ref**: @lib/features/projects/presentation/screens/project_list_screen.dart:73, @lib/features/sync/application/sync_orchestrator.dart:127

### [DATA] 2026-03-18: synced_projects enrollment gap — project exists locally but sync skips all child tables — BUG-005 (Session 591)
**Pattern**: Inspector device has `enrolled projects=1` in SQLite but `synced_projects entries=0`. The sync engine uses `synced_projects` to scope project-level pulls, so ALL 15 project-scoped tables are skipped ("Pull skip (no loaded projects)"). The project appears in the UI but is a dead shell with no data and no way to receive data via sync.
**Prevention**: Ensure every code path that inserts into the local `projects` table also creates a `synced_projects` row. Add a defensive check in `fetchRemoteProjects()` to detect and repair orphaned projects missing enrollment.
**Ref**: @lib/features/sync/engine/sync_engine.dart:1304, @lib/features/projects/presentation/providers/project_provider.dart

### [DATA] 2026-03-18: _pushUpsert writes back server updated_at without suppressing change_log trigger (Session 588)
**Pattern**: After successful Supabase upsert, `_pushUpsert()` writes the server-assigned `updated_at` back to local SQLite via `db.update()`. This fires the `AFTER UPDATE` trigger which inserts a new `change_log` row with `processed=0`. The original change gets marked processed, but the phantom entry doesn't — pending count never drops to 0.
**Prevention**: Wrap all local DB writes that are sync-engine bookkeeping (not user data) with `pulling=1` guard to suppress triggers. The photo push path (`_pushPhotoThreePhase`) already does this correctly.
**Ref**: @lib/features/sync/engine/sync_engine.dart:620-628

<!-- Add defects above this line -->
