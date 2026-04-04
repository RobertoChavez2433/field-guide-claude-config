# Source Excerpts — By Concern

Organized by spec section for plan writer consumption.

---

## Concern 1: Sync Modes (Quick / Full / Maintenance)

### Current State: No mode differentiation

All paths call the same method chain:
```
trigger → syncLocalAgencyProjects() → _syncWithRetry() → _doSync() → engine.pushAndPull()
```

**SyncOrchestrator._doSync** (sync_orchestrator.dart:413-448):
Creates engine, calls `engine.pushAndPull()` — always full cycle.

**SyncEngine.pushAndPull** (sync_engine.dart:216-360):
Always runs: push → storage cleanup → pull (all adapters) → prune → integrity check → orphan scan.

**What needs to change**:
- Add `SyncMode` enum: `quick`, `full`, `maintenance`
- `pushAndPull(mode)` gates sub-phases by mode
- Quick: push + pull dirty scopes only (skip integrity, orphan, storage cleanup)
- Full: current behavior
- Maintenance: integrity + orphan scan + prune only
- `syncLocalAgencyProjects({SyncMode mode = SyncMode.full})` passes mode through

---

## Concern 2: Manual Sync Must Be Global

### Current State: Sync action buried

**SyncStatusIcon** (sync_status_icon.dart:15-54):
Used ONLY in `home_screen.dart:375` (entry list screen). Not in global scaffold.

**scaffold_with_nav_bar.dart**: Does NOT contain SyncStatusIcon.

**Sync dashboard route**: `/sync/dashboard` (sync_routes.dart:10).

**What needs to change**:
- Add SyncStatusIcon (or equivalent manual sync button) to `scaffold_with_nav_bar.dart` so it appears on ALL screens
- Or add to each screen's app bar individually (more work, less maintainable)
- SyncStatusIcon already has the right behavior (Consumer<SyncProvider>, push to dashboard)

---

## Concern 3: Change Log Remains Push Source of Truth

### Current State: Already correct

**ChangeTracker** (change_tracker.dart:43-215):
Reads from `change_log` table populated by SQLite triggers. No per-record sync_status.

**change_log schema** (via SyncEngineTables):
- `id`, `table_name`, `record_id`, `operation`, `changed_at`, `processed`, `retry_count`, `error_message`, `project_id`

**Spec confirms**: "No per-record sync_status rollback. No duplicate sync queue."

**No changes needed** to ChangeTracker or change_log schema.

---

## Concern 4: Remote Freshness — Hint-Driven Invalidation

### Current State: No remote invalidation infrastructure

**Supabase Realtime**: Zero usage anywhere in codebase (grep confirmed).

**FCM foreground handler** (fcm_handler.dart:100-116):
Only checks `data['type'] == 'daily_sync'`, triggers full sync. No hint parsing.

**FCM background handler** (fcm_handler.dart:13-25):
Top-level function, currently just logs.

**What needs to be built**:
1. **DirtyScopeTracker** (new file): Tracks dirty (company_id, project_id, table_name) tuples
2. **RealtimeHintHandler** (new file): Subscribes to Supabase Realtime broadcast channel, parses hint payloads, marks scopes dirty via DirtyScopeTracker, triggers quick sync
3. **FCM hint parsing**: Extend `handleForegroundMessage` to parse hint payload → mark scopes dirty → trigger quick sync (not full)
4. **Server-side broadcast**: Supabase DB trigger or edge function that broadcasts change hints when data is modified

---

## Concern 5: Full Sync Is Fallback, Not Default

### Current State: Full sync IS the default

**SyncLifecycleManager._handleResumed** (sync_lifecycle_manager.dart:74-103):
On app resume, if stale (>24h) → `_triggerDnsAwareSync(forced: true)` → `syncLocalAgencyProjects()` → full pushAndPull.

If not stale, does nothing (no sync at all).

**FcmHandler.handleForegroundMessage** (fcm_handler.dart:100-116):
Always triggers `syncLocalAgencyProjects()` → full sync.

**BackgroundSyncHandler** (background_sync_handler.dart:94-134):
Every 4 hours → full sync.

**What needs to change**:
- Resume: Run quick sync (push + pull dirty only), NOT full sync
- FCM: Parse hint → mark dirty → quick sync
- Background: Keep as maintenance sync (integrity + prune)
- Manual: Keep as full sync (user-invoked)
- Add new resume-sync path: push local changes + pull only scopes marked dirty

---

## Concern 6: Scope Model (Dirty-Scope Awareness)

### Current State: No dirty-scope tracking

**ScopeType** (scope_type.dart:13-29):
Static enum on each adapter. Determines HOW to filter pulls, not WHEN.

**_pull() loop** (sync_engine.dart:1452-1556):
Iterates ALL adapters unconditionally. The only skips are:
- `adapter.skipPull` (ConsentRecordAdapter, SupportTicketAdapter)
- Empty `_syncedProjectIds` → skip project-scoped
- Empty `_syncedContractorIds` → skip viaContractor

**change_log.project_id** (added in v38):
Already exists — enables per-project change detection.

**What needs to be built**:
- `DirtyScopeTracker` class with:
  - `markDirty(String? projectId, String? tableName)` — from hints
  - `getDirtyScopes() → Set<DirtyScope>` — for quick pull
  - `clearAll()` — after full sync
  - `isDirty(String tableName, String? projectId) → bool` — per-adapter check
- Quick pull: `_pull()` checks `DirtyScopeTracker.isDirty(adapter.tableName)` before pulling each adapter
- Full pull: ignores dirty tracking, pulls everything (current behavior)

---

## Concern 7: Startup Sync Behavior

### Current State: Route-dependent

**SyncInitializer.create** (sync_initializer.dart:38-130):
Wires lifecycle manager but does NOT trigger initial sync.

**SyncLifecycleManager._handleResumed** (sync_lifecycle_manager.dart:74-103):
Only fires on lifecycle state change (not on initial launch).

**Actual startup sync**: Triggered by UI code after auth context loads (varies by entry point).

**What needs to change**:
- Consistent startup: After auth context ready → run quick sync (push + pull dirty)
- Not a full sweep
- Wire into SyncInitializer.create or the bootstrap chain
