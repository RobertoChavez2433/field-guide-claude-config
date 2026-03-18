# Defects: Sync

Active patterns for sync. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [DATA] 2026-03-18: _pushUpsert writes back server updated_at without suppressing change_log trigger (Session 588)
**Pattern**: After successful Supabase upsert, `_pushUpsert()` writes the server-assigned `updated_at` back to local SQLite via `db.update()`. This fires the `AFTER UPDATE` trigger which inserts a new `change_log` row with `processed=0`. The original change gets marked processed, but the phantom entry doesn't — pending count never drops to 0.
**Prevention**: Wrap all local DB writes that are sync-engine bookkeeping (not user data) with `pulling=1` guard to suppress triggers. The photo push path (`_pushPhotoThreePhase`) already does this correctly.
**Ref**: @lib/features/sync/engine/sync_engine.dart:620-628

### [DATA] 2026-03-18: Permanent offline trap — _isOnline never recovers once false (Session 587)
**Pattern**: `_syncWithRetry()` only called `checkDnsReachability()` on retry attempts (attempt > 0), not the first attempt. `SyncLifecycleManager._handleResumed()` read cached `isSupabaseOnline` before calling `checkDnsReachability()`. Once `_isOnline=false`, no code path ever re-tested it → app stuck offline permanently even with good connectivity.
**Prevention**: Always call `checkDnsReachability()` before trusting `_isOnline`. Never gate a DNS re-check on the cached result of a previous DNS check. Every sync attempt (including first) must verify connectivity. Admin/UI retry must call the live check, not read the cache.
**Ref**: @lib/features/sync/application/sync_orchestrator.dart:288, @lib/features/sync/application/sync_lifecycle_manager.dart:88

### [DATA] 2026-03-18: Delete Forever skips Supabase — raw database.delete() bypasses change_log (Session 587)
**Pattern**: `TrashScreen._confirmDeleteForever()` called `database.delete()` directly instead of `SoftDeleteService.hardDeleteWithSync()`. No change_log entry created, so sync never pushed the delete to Supabase. Remote record persisted and was re-downloaded on next pull.
**Prevention**: Never use raw `database.delete()` for user-facing delete operations. Always use `SoftDeleteService.hardDeleteWithSync()` which suppresses triggers, hard-deletes, and manually inserts a change_log entry.
**Ref**: @lib/features/settings/presentation/screens/trash_screen.dart:316

### [CONFIG] 2026-03-16: InternetAddress.lookup fails on Android despite good connectivity (Session 580)
**Pattern**: `SyncOrchestrator.checkDnsReachability()` used `InternetAddress.lookup(hostname)` which fails with errno=7 on Android even when `ping` from device shell resolves fine. Known Android issue — Dart's DNS lookup doesn't bind to the correct network interface after fresh install or process restart. Caused "Sync error - Device is offline" with good WiFi.
**Prevention**: Use HTTP HEAD request to the actual endpoint instead of raw DNS lookup. `http.head(Uri.parse('${SupabaseConfig.url}/rest/v1/'))` uses the HTTP client which properly binds to the active network interface. Also add `ACCESS_NETWORK_STATE` permission.
**Ref**: @lib/features/sync/application/sync_orchestrator.dart:420-447

### [DATA] 2026-03-16: RLS UPDATE policy allows any non-viewer to soft-delete any project (Session 580)
**Pattern**: `company_projects_update` policy at `20260222100000_multi_tenant_foundation.sql:454-456` only checks `NOT is_viewer()`. Any inspector/engineer can `UPDATE projects SET deleted_at = NOW()` on any project in the company. The owner/admin authorization gate claimed in the spec does not exist at the RLS layer.
**Prevention**: Tighten WITH CHECK: when `deleted_at` transitions NULL→non-NULL, require `created_by_user_id = auth.uid() OR is_approved_admin()`. New migration needed — see project lifecycle spec Section 12.
**Ref**: @supabase/migrations/20260222100000_multi_tenant_foundation.sql:454-456

<!-- Add defects above this line -->
