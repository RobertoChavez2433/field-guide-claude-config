# Sync System Rewrite + Settings Redesign — Implementation Plan

**Date**: 2026-03-04 | **Sessions**: 495 (brainstorm), 496 (adversarial review), 497 (integration)
**Scope**: Replace broken sync system, fix 30+ gaps, redesign settings, profile expansion, comprehensive testing
**Ground Truth**: `.claude/plans/2026-03-04-sync-system-audit-report.md` (19 gaps)
**PRD Alignment**: `.claude/prds/2026-02-21-project-based-architecture-prd.md`
**Deferred**: Firebase/FCM background sync (leave as stub)

---

## Design Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Change tracking | SQLite triggers + change_log table (zero manual queueOperation calls) |
| 2 | Pull strategy | Incremental cursor (updated_at) with 5-second safety margin + 4-hour integrity check |
| 3 | Conflict resolution | Last-write-wins + conflict_log table with user-visible UI |
| 4 | Engine architecture | Table adapter registry — one adapter class per synced table |
| 5 | User transparency | App bar colored icon + toast on failure + Sync Dashboard in Settings |
| 6 | Testing | Per-adapter unit tests + integration harness + stage trace scorecard |
| 7 | Photo lifecycle | Three-phase atomic sync (upload → metadata upsert → mark synced) |
| 8 | Implementation order | Bottom-up: schema → engine → adapters → UI |
| 9 | Settings | Full redesign: remove dead code, restructure sections, migrate prefs |
| 10 | Trigger suppression | sync_control gate table; startup force-reset every cycle |
| 11 | Sync lock | Hybrid SQLite advisory lock; 5-min stale timeout; non-reentrant |
| 12 | Table count | 16 adapters; entry_personnel deprecated; user_certifications outside engine |
| 13 | Conflict log PII | Changed columns only; 7-day expiry; 30-day undismissed warning |
| 14 | change_log pruning | Delete processed entries older than 7 days after each cycle |
| 15 | Cutover strategy | Big Bang — build on feature branch, remove old code on merge, no coexistence |
| 16 | First-sync | User-driven project selection via synced_projects table |
| 17 | Profile | Expand user_profiles; new user_certifications table; no SharedPreferences fallback |

---

## Gaps Addressed (30 total)

### Original Audit (19 confirmed)
GAP-1 through GAP-19 — all confirmed by 5 research agents. See audit report for details.

### New Gaps Found by Research Agents (11 additional)

| ID | Severity | Description |
|----|----------|-------------|
| NEW-1 | CRITICAL | Storage RLS `foldername(name)[1]` checks literal `'entries'` vs companyId — blocks all photo uploads |
| NEW-3 | HIGH | Photo upload + metadata upsert not atomic — orphaned storage files |
| NEW-4 | HIGH | Photo push sends stale `remote_path: null` from pre-upload SQLite map |
| NEW-5 | HIGH | `created_by_user_id` never stamped at entry creation time |
| NEW-6 | HIGH | `enforce_created_by` trigger fires INSERT only — UPDATE allows attribution fraud |
| NEW-7 | HIGH | Deactivated admins can still call admin RPCs (role check ignores status) |
| NEW-8 | HIGH | 8 pull functions lack company-scoped client-side filter |
| NEW-9 | HIGH | `inspector_forms.template_bytes` BLOB vs BYTEA — no conversion |
| NEW-10 | HIGH | No mutex on concurrent `syncAll()` — TOCTOU race |
| NEW-12 | MEDIUM | Daily entry submit/undo/batchSubmit don't update sync tracking |
| NEW-13 | MEDIUM | No "edit own records only" enforcement (PRD decision 7) — deferred |

---

## Architecture

### New Sync Engine Structure

```
lib/features/sync/
  engine/
    sync_engine.dart           # Push/pull orchestrator with mutex
    change_tracker.dart        # Reads change_log, groups by table
    conflict_resolver.dart     # LWW + conflict_log writes
    integrity_checker.dart     # 4-hour count+max+checksum comparison
    sync_mutex.dart            # SQLite advisory lock
  adapters/
    table_adapter.dart         # Base class (abstract)
    type_converters.dart       # BoolInt, JsonMap, Timestamp, Bytea converters
    project_adapter.dart
    location_adapter.dart
    contractor_adapter.dart
    equipment_adapter.dart
    bid_item_adapter.dart
    personnel_type_adapter.dart
    daily_entry_adapter.dart
    photo_adapter.dart         # Override: three-phase upload
    entry_equipment_adapter.dart
    entry_quantities_adapter.dart
    entry_contractors_adapter.dart
    entry_personnel_counts_adapter.dart
    inspector_form_adapter.dart
    form_response_adapter.dart
    todo_item_adapter.dart
    calculation_history_adapter.dart
  config/
    sync_registry.dart         # Declares all adapters + dependency order
    sync_config.dart           # Chunk sizes, timeouts, retry policy
  presentation/
    providers/
      sync_provider.dart       # Updated — reads from new engine
    widgets/
      sync_status_icon.dart    # App bar icon (green/yellow/red) — replaces SyncStatusBanner
      sync_toast.dart          # Toast notifications on failure
      deletion_notification_banner.dart  # KEPT — powers deletion notifications
    screens/
      sync_dashboard_screen.dart      # Full dashboard in Settings
      conflict_viewer_screen.dart     # View/dismiss/restore conflicts
      project_selection_screen.dart   # NEW — user chooses which projects to download
```

**16 synced data tables — NOT 17.** `entry_personnel` is a legacy dead table superseded by `entry_personnel_counts`. It does NOT get an adapter, triggers, or scorecard entry.

### Table Adapter Base Class

```dart
abstract class TableAdapter {
  String get tableName;
  String get companyScope;          // 'company_id', 'project_id', or 'entry_id'
  ScopeType get scopeType;          // direct, oneHop, twoHop
  List<String> get fkDependencies;  // tables that must push before this one
  Map<String, TypeConverter> get converters;  // column → converter
  List<String> get localOnlyColumns;  // columns stripped from push payload
  List<String> get remoteOnlyColumns; // columns stripped from pull payload
  bool get supportsSoftDelete => true;

  Map<String, dynamic> convertForRemote(Map<String, dynamic> local);
  Map<String, dynamic> convertForLocal(Map<String, dynamic> remote);
  Future<void> validate(Map<String, dynamic> record);  // pre-push validation

  /// Extract a human-readable name for deletion notifications.
  String extractRecordName(Map<String, dynamic> record) =>
      record['name']?.toString() ?? record['title']?.toString() ?? record['id']?.toString() ?? 'Unknown';

  /// Columns that should be stamped with current user ID before push.
  /// Override in adapters that have user-tracking columns.
  Map<String, String> get userStampColumns => {};
  // Example override in DailyEntryAdapter:
  //   Map<String, String> get userStampColumns => {'updated_by_user_id': 'current_user_id'};
}
```

### Sync Control Table (Decision 1 / ADV-1)

The sync_control table gates trigger execution during pull and purge operations to prevent the trigger-pull feedback loop. Every sync cycle starts with a force-reset of this value to `'0'` to recover from any crash mid-pull.

```sql
CREATE TABLE IF NOT EXISTS sync_control (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
INSERT OR IGNORE INTO sync_control (key, value) VALUES ('pulling', '0');
```

**Startup force-reset**: At the start of every sync cycle (before acquiring the lock):
```dart
await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
```

**ONE exception**: When local wins a conflict during pull, the engine manually INSERTs a change_log entry (bypassing suppressed triggers) to ensure the local-wins version is pushed back to the server.

### Change Log Table (SQLite)

```sql
CREATE TABLE IF NOT EXISTS change_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name TEXT NOT NULL,
  record_id TEXT NOT NULL,
  operation TEXT NOT NULL,  -- 'insert', 'update', 'delete'
  changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
  processed INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  metadata TEXT              -- JSON, e.g. {"source": "orphan_scan"}
);
CREATE INDEX idx_change_log_unprocessed ON change_log(processed, table_name);
```

**Pruning (Decision 9)**: After each successful sync cycle, delete processed entries older than 7 days:
```sql
DELETE FROM change_log
WHERE processed = 1
  AND changed_at < strftime('%Y-%m-%dT%H:%M:%f', 'now', '-7 days');
```
Unprocessed entries are NEVER pruned.

### SQLite Trigger Template (per synced table)

Triggers include a `WHEN` clause that checks the `sync_control` table. When `pulling = '1'`, triggers are suppressed to prevent the trigger-pull feedback loop.

```sql
CREATE TRIGGER IF NOT EXISTS trg_{table}_insert AFTER INSERT ON {table}
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('{table}', NEW.id, 'insert');
END;

CREATE TRIGGER IF NOT EXISTS trg_{table}_update AFTER UPDATE ON {table}
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('{table}', NEW.id, 'update');
END;

CREATE TRIGGER IF NOT EXISTS trg_{table}_delete AFTER DELETE ON {table}
WHEN (SELECT value FROM sync_control WHERE key = 'pulling') = '0'
BEGIN
  INSERT INTO change_log (table_name, record_id, operation)
  VALUES ('{table}', OLD.id, 'delete');
END;
```

**Explicit 16-table trigger list**:
1. projects
2. locations
3. contractors
4. equipment
5. bid_items
6. personnel_types
7. daily_entries
8. photos
9. entry_equipment
10. entry_quantities
11. entry_contractors
12. entry_personnel_counts
13. inspector_forms
14. form_responses
15. todo_items
16. calculation_history

**Excluded tables**: `entry_personnel` (legacy dead table), `extraction_metrics`, `stage_metrics` (local-only, no Supabase counterpart), `sync_control`, `sync_metadata`, `change_log`, `conflict_log`, `deletion_notifications`, `sync_lock` (engine infrastructure tables).

### Conflict Log Table (SQLite)

```sql
CREATE TABLE IF NOT EXISTS conflict_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name TEXT NOT NULL,
  record_id TEXT NOT NULL,
  winner TEXT NOT NULL,         -- 'local' or 'remote'
  lost_data TEXT NOT NULL,      -- JSON of changed columns only (Decision 8 PII mitigation)
  detected_at TEXT NOT NULL,
  dismissed_at TEXT,            -- NULL until user dismisses
  expires_at TEXT NOT NULL      -- Auto-cleanup date (detected_at + 7 days)
);
CREATE INDEX idx_conflict_log_expires ON conflict_log(expires_at);
```

### Conflict Log PII Mitigation (Decision 8)

The `lost_data` column stores only the diff (changed columns), not the full record:

```dart
Map<String, dynamic> computeLostData(Map<String, dynamic> winner, Map<String, dynamic> loser) {
  final diff = <String, dynamic>{'id': loser['id']};
  for (final key in loser.keys) {
    if (loser[key] != winner[key]) {
      diff[key] = loser[key];
    }
  }
  return diff;
}
```

Auto-expiry rules:
- `expires_at` set to `detected_at + 7 days`
- Dismissed conflicts auto-deleted after expiry:
  ```sql
  DELETE FROM conflict_log
  WHERE dismissed_at IS NOT NULL
    AND expires_at < strftime('%Y-%m-%dT%H:%M:%f', 'now');
  ```
- Undismissed conflicts kept indefinitely; warning shown for conflicts older than 30 days.

### Sync Lock Table (Decision 2 / ADV-20)

Replaces the Completer-based mutex. Works across isolates (foreground + WorkManager background). Startup reset occurs in `SyncEngine` constructor and on app startup.

```sql
CREATE TABLE IF NOT EXISTS sync_lock (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  locked_at TEXT NOT NULL,
  locked_by TEXT NOT NULL  -- 'foreground' or 'background'
);
```

Lock acquisition:
```dart
Future<bool> tryAcquireLock(String lockedBy) async {
  // Expire stale locks older than 5 minutes (crash recovery)
  await db.execute(
    "DELETE FROM sync_lock WHERE locked_at < strftime('%Y-%m-%dT%H:%M:%f', 'now', '-5 minutes')"
  );
  try {
    await db.execute(
      "INSERT INTO sync_lock (id, locked_at, locked_by) VALUES (1, strftime('%Y-%m-%dT%H:%M:%f', 'now'), ?)",
      [lockedBy],
    );
    return true;
  } catch (_) {
    return false;
  }
}

Future<void> releaseLock() async {
  await db.execute("DELETE FROM sync_lock WHERE id = 1");
}
```

**Non-reentrancy invariant**: `push()` and `pull()` MUST NOT call each other. The lock is non-reentrant by design. Add assertion in debug mode:
```dart
assert(!_insidePushOrPull, 'SyncEngine: push/pull must not be called reentrantly');
```

**Startup reset**: `DELETE FROM sync_lock` on app startup and in `SyncEngine` constructor.

### Sync Metadata Table (SQLite)

```sql
CREATE TABLE IF NOT EXISTS sync_metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
-- Keys: 'last_sync_time', 'last_pull_{tableName}' per table,
--        'last_integrity_check', 'integrity_check_result'
```

### Push Flow (Decision 3)

```
SyncEngine.push():
  1. Force-reset sync_control.pulling = '0' (startup safety)
  2. DELETE FROM sync_lock (startup safety in constructor)
  3. Acquire SQLite advisory lock
     - If lock held, abort push (another process is syncing)
  4. Read unprocessed change_log entries
     - ORDER BY changed_at ASC (oldest first)
     - LIMIT 500 per cycle (Decision 3 rate limiting)
     - If unprocessed count > 1000, log anomaly to sync dashboard
  5. Group by table_name
  6. Sort tables by FK dependency order (registry)
  7. For each table:
     a. PRE-CHECK (Decision 3): Query change_log for any unprocessed/failed entries
        in parent tables (fkDependencies). If any parent has failed entries
        (retry_count >= max), SKIP this table entirely. Log: "Blocked by
        parent sync failure in {parentTable}." Surface in dashboard.
     b. Get adapter from registry
     c. For each change:
        - If operation = 'delete' (Decision 3):
           - Send DELETE to Supabase using record_id from change_log
           - Do NOT attempt to read local record (it's already gone)
           - If Supabase record already gone (404), treat as success (benign no-op)
        - If operation = 'insert' or 'update':
           - Read current record from SQLite
           - adapter.validate(record)
           - adapter.convertForRemote(record)
           - Stamp user-tracking columns: for each entry in adapter.userStampColumns,
             set payload[column] = currentUserId (from AuthProvider) (Decision 3)
           - Push to Supabase (upsert)
        - On success: mark change_log entry processed=1
        - On failure — classify error (Decision 3):
           - 401 Unauthorized: attempt token refresh. If refresh succeeds,
             retry immediately. If refresh fails, abort entire sync cycle, surface
             "re-login required." NEVER increment retry_count for auth failures.
           - 429 Too Many Requests / 503 Service Unavailable / network timeout:
             RETRYABLE. Exponential backoff (1s, 2s, 4s, 8s, 16s cap).
             Increment retry_count.
           - 400 Bad Request / 403 Forbidden / 404 Not Found:
             PERMANENT. Set error_message, increment retry_count.
           - If retry_count >= max (5): leave unprocessed, surface in UI
             as "permanently failed — manual intervention required"
  8. Prune change_log: DELETE WHERE processed = 1
     AND changed_at < NOW() - 7 days (Decision 9)
  9. Prune conflict_log: DELETE WHERE dismissed_at IS NOT NULL
     AND expires_at < NOW() (Decision 8)
  10. Release lock
```

### Pull Flow (Decision 1, Decision 4)

```
SyncEngine.pull():
  1. Force-reset sync_control.pulling = '0' (startup safety)
  2. Acquire SQLite advisory lock (shared with push — sequential, not concurrent)
  3. Set sync_control.pulling = '1' (suppress triggers during pull)
  try:
  4. For each table in registry (dependency order):
     a. Get adapter
     b. Read last_pull_{table} cursor from sync_metadata
     c. Query Supabase: SELECT * WHERE updated_at > cursor - INTERVAL '5 seconds'
        - 5-second safety margin accounts for transaction start vs commit time skew
        - Apply company scope filter (adapter.companyScope)
        - Paginate in chunks of 100
     d. For each remote record:
        - adapter.convertForLocal(record)
        - Deduplicate: skip if local record has identical updated_at (safety margin overlap)
        - Check local: SELECT WHERE id = record.id
        - If not exists locally:
           - If remote has deleted_at set: SKIP (don't insert already-deleted records)
           - Otherwise: INSERT into local SQLite
        - If exists locally:
           - ConflictResolver.resolve(local, remote) → winner
           - ConflictResolver MUST compare the server-assigned updated_at from the pulled
             record, never the local client's outbound updated_at
           - If timestamps are equal: remote wins (deterministic tiebreaker). A conflict_log
             entry IS created so the user can review the potential data loss.
           - If remote wins: UPDATE local, log conflict (changed columns only)
           - If local wins (edit-wins):
              - UPDATE local record to keep local version
              - Log conflict
              - EXPLICITLY INSERT into change_log: operation='update', record_id=record.id
                (bypasses suppressed triggers — this is the ONE case where pull creates
                a change_log entry, to ensure local-wins version is pushed back)
        - If remote record has deleted_at set AND deleted_by != current_user_id:
           - Create deletion_notification row:
             > NOTE: `deletion_notifications` already exists in SQLite — defined in
             > `lib/core/database/schema/sync_tables.dart:22`. Do NOT create it in the migration.
             ```dart
             await db.insert('deletion_notifications', {
               'id': Uuid().v4(),
               'record_id': record['id'],
               'table_name': adapter.tableName,
               'project_id': record['project_id'] ?? localRecord?['project_id'],
               'record_name': adapter.extractRecordName(localRecord ?? record),
               'deleted_by': record['deleted_by'],
               'deleted_by_name': lookupUserName(record['deleted_by']),
               'deleted_at': record['deleted_at'],
               'seen': 0,
             });
             ```
           - This preserves existing DeletionNotificationBanner behavior
     e. Update last_pull_{table} cursor = max(remote.updated_at)
  5. Update last_sync_time
  finally:
  6. Set sync_control.pulling = '0' (re-enable triggers — guaranteed even on exception)
  7. Release lock
```

### First-Sync Strategy: User-Driven Project Selection (Decision 4)

When a user first joins a company or installs the app, they choose which projects to download:

1. **Project Selection Screen** (`/sync/project-selection`): Queries Supabase `projects` table directly (not local SQLite). Inspector browses and searches all company projects. Tapping a project marks it for sync.
2. **`synced_projects` table** (SQLite): `(project_id TEXT PRIMARY KEY, synced_at TEXT)`. Records which projects the user has selected to download.
3. **Pull scoping**: The pull flow filters by `project_id IN (SELECT project_id FROM synced_projects)` for all project-scoped tables. Projects not in `synced_projects` are never pulled to the local device.
4. **`is_active` is separate**: The `is_active` column on projects is an admin-level concept (hide from project lists). It is NOT used for sync filtering.
5. **First-sync pull flow**: After project selection, a full pull runs for all selected projects. Progress indicator shown per table. App is read-only for already-pulled tables while sync continues.
6. **Interrupted first sync**: Do NOT update cursor for incomplete tables. Next sync resumes.

### Integrity Checker (4-Hour Cycle)

```
IntegrityChecker.run():
  For each table in registry:
    1. Local:  SELECT COUNT(*) as count, MAX(updated_at) as max_ts,
                      SUM(hash of all record IDs) as id_checksum
               WHERE deleted_at IS NULL
    2. Remote: Call get_table_integrity(table_name) RPC
       Returns: count, max_updated_at, id_checksum (all company-scoped)
    3. Compare count, max_ts, AND id_checksum
    4. If any mismatch:
       - Log drift to sync_metadata
       - Reset last_pull_{table} cursor to NULL (triggers full re-pull)
       - Surface in Sync Dashboard
    5. Store result: last_integrity_check = now, per-table pass/fail

  Orphan scanner runs as part of integrity check cycle (see below).
```

### Isolate Strategy

`BackgroundSyncHandler` runs in a WorkManager isolate. It MUST instantiate its own `SyncEngine` — NOT share the foreground instance. The SQLite advisory lock prevents conflicts between the two instances.

```dart
class BackgroundSyncHandler {
  Future<void> onSync() async {
    final db = await DatabaseService.instance.database;
    final engine = SyncEngine(db: db, lockedBy: 'background');
    if (!await engine.tryAcquireLock()) return; // Foreground is syncing
    try {
      await engine.pushAndPull();
    } finally {
      await engine.releaseLock();
    }
  }
}
```

### Photo Adapter (Three-Phase)

```
PhotoAdapter.push(change):
  Phase 1: Upload file
    - Check if remote_path already exists in storage → skip upload
    - Upload file to bucket 'entry-photos', path entries/{companyId}/{entryId}/{filename}
    - Get actual remote_path from response

  Phase 2: Upsert metadata
    - Build payload with remote_path from Phase 1 (not stale map)
    - Upsert to Supabase photos table

  Phase 3: Mark local synced (ONLY after 1+2 succeed)
    - Update local photos row: remote_path, processed in change_log

  Failure handling:
    - Phase 1 fails: change_log stays unprocessed, retry next cycle
    - Phase 2 fails: file exists in storage, retry Phase 2 only
    - Phase 3 fails: local stays unprocessed, next cycle re-runs
      (Phase 1 detects file exists → skip → Phase 2 upserts → Phase 3 marks)

PhotoAdapter.handleDelete(change):
  - Push deleted_at to Supabase photos table
  - Storage cleanup: separate post-sync phase
    - Query Supabase for photos WHERE deleted_at IS NOT NULL
      AND deleted_at < NOW() - 30 days
    - Delete storage files for those records
    - Hard-delete Supabase rows
```

### Orphan Scanner Algorithm

The orphan scanner detects storage files that have no corresponding database row.

**Algorithm**:
1. Query Supabase `photos` table for all `remote_path` values for this company:
   `SELECT remote_path FROM photos WHERE project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())`
2. List Storage files by company prefix: `entries/{companyId}/`
3. Diff: files in Storage but NOT in photos table = orphans
4. For orphans older than 24 hours (to avoid flagging in-progress uploads):
   - Log to `change_log` with `metadata: {"source": "orphan_scan"}`
   - Surface in Sync Dashboard as "Orphaned storage files detected"
   - Do NOT auto-delete — require manual confirmation or admin action

**Trigger**: Runs as part of the 4-hour integrity check cycle.

### Tables Outside New Engine Scope

The following tables continue to be synced outside the new engine's scope. They do NOT get adapters or triggers:

- `companies` — pulled by `pullCompanyMembers()`
- `user_profiles` — pulled by `UserProfileSyncDatasource`
- `company_join_requests` — pulled by orchestrator
- `user_certifications` (NEW) — synced via `UserProfileSyncDatasource` path alongside user_profiles

### BYTEA Converter Specification

```dart
class ByteaConverter implements TypeConverter {
  /// SQLite BLOB (Uint8List) → Supabase BYTEA (base64 string)
  dynamic toRemote(dynamic value) {
    if (value == null) return null;
    return base64Encode(value as Uint8List);
  }

  /// Supabase BYTEA (base64 string via PostgREST) → SQLite BLOB (Uint8List)
  dynamic toLocal(dynamic value) {
    if (value == null) return null;
    return base64Decode(value as String);
  }
}
```
Supabase PostgREST accepts and returns BYTEA as base64-encoded strings.

### Auth Token Refresh on 401

```dart
Future<bool> _handleAuthError() async {
  final session = Supabase.instance.client.auth.currentSession;
  if (session == null) return false;
  try {
    await Supabase.instance.client.auth.refreshSession();
    return true;
  } catch (_) {
    return false;
  }
}
```
NEVER increment `retry_count` for 401 errors.

---

## Settings Redesign

### Current Problems Found

1. **Jumbled section ordering** — Profile and Account are far apart; sync is sandwiched between
2. **4 dead toggles** — auto_fetch_weather, auto_sync_wifi, auto_fill_enabled, use_last_values (saved but never checked at runtime)
3. **3 dead stubs** — Backup Data, Restore Data, Help & Support (show "coming soon" snackbar)
4. **2 static displays posing as settings** — Company Template, Weather API (unactionable)
5. **1 orphaned widget** — `EditInspectorDialog` (zero call sites)
6. **Duplicate navigation** — "Default Signature Name" and "Edit Profile" both go to /edit-profile
7. **4 dead preference keys** — show_only_manual_fields, last_route_location, prefill_project_form:*, prefill_prompted:*
8. **3 profile fields still reading from PreferencesService** — forms/PDF should read from user_profiles
9. **`inspector_agency` written but never consumed** — dead storage
10. **`gauge_number` stored in PreferencesService** — must move to user_profiles

### New Settings Structure

```
Settings Screen (reorganized sections):

1. ACCOUNT
   ├── Profile summary (name, role, company — read-only)
   ├── Edit Profile → /edit-profile
   ├── Admin Dashboard → /admin-dashboard (admin only)
   └── Sign Out

2. SYNC & DATA
   ├── Sync status indicator (last sync, pending, errors)
   ├── [Sync Now] button
   ├── Sync Dashboard → /sync-dashboard (NEW)
   ├── Manage Synced Projects → /sync/project-selection (NEW)
   ├── Trash → /settings/trash (with badge count)
   └── Clear Cached Exports

3. FORM SETTINGS
   ├── Gauge Number (editable text field — moved from PreferencesService to user_profiles)
   ├── Initials (editable text field — auto-derived from displayName, manually overridable)
   └── PDF Template (display: MDOT DWR or FVK IDR — read-only info)

4. APPEARANCE
   ├── Theme selector (Dark / Light / High Contrast)
   ├── Auto-Load toggle (from ProjectSettingsProvider)
   └── (future: font size, field conditions presets)

5. ABOUT
   ├── Version
   ├── Licenses
   └── Help & Support → link to docs/support (wire up or remove)
```

### Removed Items

| Item | Reason |
|------|--------|
| Auto-Fill toggle | Dead — never checked at runtime. Remove toggle, auto-fill always on. |
| Use Last Values toggle | Dead — never checked. Remove. |
| Auto-Sync on WiFi toggle | Dead — sync never checks it. Defer to future WiFi-aware sync. |
| Auto-fetch Weather toggle | Dead — weather service never checks it. Remove or wire up in weather feature. |
| Backup Data / Restore Data | Stubs — no implementation. Remove until built. |
| Default Signature Name tile | Duplicate of Edit Profile. Remove. |
| Weather API display | Unactionable static info. Remove. |
| Company Template display | Move to Form Settings as read-only info. |
| `EditInspectorDialog` widget | Orphaned — zero call sites. Delete file. |
| `show_only_manual_fields` pref key | Dead — never read. Remove from PreferencesService. |
| `last_route_location` pref key | Dead — route restore was removed. Remove. |
| `prefill_project_form:*` key family | Dead — getter/setter have zero callers. Remove. |
| `prefill_prompted:*` key family | Dead — zero callers. Remove. |
| `inspector_agency` pref key | Dead — written but never consumed by forms or PDF. Remove. |

### Profile Expansion (Decision 12)

The `user_profiles` table gains new columns:

| Column | Type | Notes |
|--------|------|-------|
| `email` | TEXT | Read-only display; synced from auth |
| `agency` | TEXT | Replaces dead `inspector_agency` pref key |
| `initials` | TEXT | Auto-derived from displayName; manually overridable in Settings |
| `gauge_number` | TEXT | Moved from PreferencesService |

`cert_number` is removed from `user_profiles` and migrated to the new `user_certifications` table.

### New Table: user_certifications

```sql
CREATE TABLE user_certifications (
  id TEXT PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  cert_type TEXT NOT NULL,
  cert_number TEXT NOT NULL,
  expiry_date DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, cert_type)
);
```

Synced via `UserProfileSyncDatasource` (NOT the new engine). Local SQLite mirror uses same schema with TEXT id and TEXT timestamps.

### Migration: PreferencesService → user_profiles (Decision 12)

**Single source of truth**: `AuthProvider.userProfile`. No SharedPreferences fallback.

| Consumer | Current Source | New Source |
|----------|---------------|------------|
| `mdot_hub_screen.dart` auto-fill | `PreferencesService.inspectorName/certNumber/phone` | `AuthProvider.userProfile.displayName/certNumber/phone` |
| `form_viewer_screen.dart` auto-fill | `PreferencesService.inspectorName/certNumber/phone` | `AuthProvider.userProfile.displayName/certNumber/phone` |
| `pdf_data_builder.dart` fallback | `prefs.getString('inspector_name')` | `AuthProvider.userProfile.displayName` |
| `entry_photos_section.dart` initials | Raw `SharedPreferences('inspector_initials')` | `AuthProvider.userProfile.initials` |
| Gauge number | `PreferencesService.gaugeNumber` | `AuthProvider.userProfile.gaugeNumber` |

**PII Cleanup from SharedPreferences**: After migration, explicitly delete all legacy PII keys:

```dart
Future<void> cleanupLegacyPiiFromPrefs(PreferencesService prefs) async {
  for (final key in [
    'inspector_name', 'cert_number', 'phone',
    'inspector_initials', 'inspector_agency', 'gauge_number',
  ]) {
    await prefs.remove(key);
  }
}
```

This runs once on first launch after the Settings redesign release.

---

## Security Fixes

| Fix | Gap | Details |
|-----|-----|---------|
| Storage RLS policy | NEW-1 | **BLOCKING — Phase 0 first task.** Change all 3 storage policies from `[1]` to `[2]` to compare companyId. |
| Admin RPC status check | NEW-7 | All 6 admin RPCs: `is_approved_admin()` as FIRST check, with `SET search_path = public` |
| enforce_created_by on UPDATE | NEW-6 | COALESCE-based `lock_created_by()` trigger — preserves original, allows first-time stamping, prevents erasure |
| Stamp created_by_user_id | NEW-5 | `DailyEntry()`, `Photo()`, all model constructors: read `AuthProvider.userId` at creation time |
| Secure password change | GAP-19 | Set `secure_password_change = true` in `supabase/config.toml` |
| Purge handler | GAP-3 | Add `case 'purge':` to `_processSyncQueueItem` (interim fix until old SyncService is replaced). Purge uses sync_control gate to bypass triggers. |

---

## Schema Alignment Migration

### Supabase Migration (Phase 0)

```sql
-- Fix GAP-10: Add updated_at to entry_contractors and entry_personnel_counts
ALTER TABLE entry_contractors ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE entry_personnel_counts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

UPDATE entry_contractors SET updated_at = created_at WHERE updated_at IS NULL;
UPDATE entry_personnel_counts SET updated_at = created_at WHERE updated_at IS NULL;

CREATE TRIGGER update_entry_contractors_updated_at
  BEFORE UPDATE ON entry_contractors
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_entry_personnel_counts_updated_at
  BEFORE UPDATE ON entry_personnel_counts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Fix GAP-9: Add soft-delete columns to inspector_forms
ALTER TABLE inspector_forms ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE inspector_forms ADD COLUMN IF NOT EXISTS deleted_by UUID REFERENCES auth.users(id);

-- Fix ADV-33: form_responses.form_id FK alignment
ALTER TABLE form_responses ALTER COLUMN form_id DROP NOT NULL;
ALTER TABLE form_responses DROP CONSTRAINT IF EXISTS form_responses_form_id_fkey;

-- Fix ADV-31: calculation_history.updated_at nullability mismatch
UPDATE calculation_history SET updated_at = COALESCE(updated_at, created_at, NOW())
WHERE updated_at IS NULL;
ALTER TABLE calculation_history ALTER COLUMN updated_at SET NOT NULL;
ALTER TABLE calculation_history ALTER COLUMN updated_at SET DEFAULT NOW();

-- Fix ADV-9: NOT NULL constraint on project_id for toolbox tables
-- Step 1: Backfill orphaned records
UPDATE inspector_forms
SET project_id = COALESCE(
  (SELECT de.project_id FROM daily_entries de WHERE de.id = inspector_forms.entry_id),
  (SELECT p.id FROM projects p WHERE p.company_id = (
    SELECT up.company_id FROM user_profiles up WHERE up.id = inspector_forms.created_by_user_id
  ) ORDER BY p.created_at LIMIT 1)
)
WHERE project_id IS NULL;

UPDATE todo_items
SET project_id = COALESCE(
  (SELECT de.project_id FROM daily_entries de WHERE de.id = todo_items.entry_id),
  (SELECT p.id FROM projects p WHERE p.company_id = (
    SELECT up.company_id FROM user_profiles up WHERE up.id = todo_items.created_by_user_id
  ) ORDER BY p.created_at LIMIT 1)
)
WHERE project_id IS NULL;

UPDATE calculation_history
SET project_id = COALESCE(
  (SELECT de.project_id FROM daily_entries de WHERE de.id = calculation_history.entry_id),
  (SELECT p.id FROM projects p WHERE p.company_id = (
    SELECT up.company_id FROM user_profiles up WHERE up.id = calculation_history.created_by_user_id
  ) ORDER BY p.created_at LIMIT 1)
)
WHERE project_id IS NULL;

-- Step 2: Hard-delete any remaining orphans
DELETE FROM inspector_forms WHERE project_id IS NULL;
DELETE FROM todo_items WHERE project_id IS NULL;
DELETE FROM calculation_history WHERE project_id IS NULL;

-- Step 3: Add NOT NULL constraints
ALTER TABLE inspector_forms ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE todo_items ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE calculation_history ALTER COLUMN project_id SET NOT NULL;

-- Fix NEW-1: Storage RLS — fix foldername index (BLOCKING first task)
-- Diagnostic query to verify path structure:
--   SELECT name,
--          (storage.foldername(name))[1] AS idx1,
--          (storage.foldername(name))[2] AS idx2,
--          (storage.foldername(name))[3] AS idx3
--   FROM storage.objects
--   WHERE bucket_id = 'entry-photos'
--   LIMIT 5;
-- Expected: [1]='entries', [2]=companyId, [3]=entryId
-- Fix: change all policies from [1] to [2]
DROP POLICY IF EXISTS "company_photo_select" ON storage.objects;
CREATE POLICY "company_photo_select" ON storage.objects
  FOR SELECT TO authenticated
  USING (bucket_id = 'entry-photos'
    AND (storage.foldername(name))[2] = get_my_company_id()::text);

DROP POLICY IF EXISTS "company_photo_insert" ON storage.objects;
CREATE POLICY "company_photo_insert" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'entry-photos'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
    AND NOT is_viewer());

DROP POLICY IF EXISTS "company_photo_delete" ON storage.objects;
CREATE POLICY "company_photo_delete" ON storage.objects
  FOR DELETE TO authenticated
  USING (bucket_id = 'entry-photos'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
    AND NOT is_viewer());

-- Fix NEW-7 + ADV-25: Admin RPC status checks
-- is_approved_admin() MUST be the FIRST check in every admin RPC
CREATE OR REPLACE FUNCTION is_approved_admin()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM user_profiles
    WHERE id = auth.uid() AND role = 'admin' AND status = 'approved'
  )
$$ LANGUAGE sql SECURITY DEFINER STABLE SET search_path = public;

-- Example rewrite for approve_join_request (apply same pattern to all 6):
CREATE OR REPLACE FUNCTION approve_join_request(
  request_id UUID,
  assigned_role TEXT DEFAULT 'inspector'
) RETURNS VOID AS $$
DECLARE
  v_company_id UUID;
  v_target_user_id UUID;
BEGIN
  -- is_approved_admin() MUST be first
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Not an approved admin';
  END IF;

  SELECT jr.company_id, jr.user_id INTO v_company_id, v_target_user_id
  FROM company_join_requests jr
  WHERE jr.id = request_id AND jr.status = 'pending';

  IF NOT FOUND THEN RAISE EXCEPTION 'Request not found or not pending'; END IF;
  IF v_company_id != get_my_company_id() THEN RAISE EXCEPTION 'Not your company'; END IF;
  IF assigned_role NOT IN ('inspector', 'engineer', 'viewer')
    THEN RAISE EXCEPTION 'Invalid role'; END IF;

  UPDATE company_join_requests
  SET status = 'approved', resolved_at = now(), resolved_by = auth.uid()
  WHERE id = request_id;

  UPDATE user_profiles
  SET company_id = v_company_id, role = assigned_role, status = 'approved', updated_at = now()
  WHERE id = v_target_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Apply same pattern (is_approved_admin FIRST, SET search_path = public) to:
-- reject_join_request, update_member_role, deactivate_member, reactivate_member, promote_to_admin

-- Fix NEW-6 + ADV-24: COALESCE-based lock_created_by() trigger on UPDATE
CREATE OR REPLACE FUNCTION lock_created_by()
RETURNS TRIGGER AS $$
BEGIN
  -- Preserves original, allows first-time stamping on legacy records (NULL),
  -- prevents erasure to NULL
  NEW.created_by_user_id = COALESCE(OLD.created_by_user_id, NEW.created_by_user_id, auth.uid());
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Apply BEFORE UPDATE triggers on all 16 synced data tables:
CREATE TRIGGER lock_created_by_projects
  BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_locations
  BEFORE UPDATE ON locations FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_contractors
  BEFORE UPDATE ON contractors FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_equipment
  BEFORE UPDATE ON equipment FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_bid_items
  BEFORE UPDATE ON bid_items FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_personnel_types
  BEFORE UPDATE ON personnel_types FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_daily_entries
  BEFORE UPDATE ON daily_entries FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_photos
  BEFORE UPDATE ON photos FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_entry_equipment
  BEFORE UPDATE ON entry_equipment FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_entry_quantities
  BEFORE UPDATE ON entry_quantities FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_entry_contractors
  BEFORE UPDATE ON entry_contractors FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_entry_personnel_counts
  BEFORE UPDATE ON entry_personnel_counts FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_inspector_forms
  BEFORE UPDATE ON inspector_forms FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_form_responses
  BEFORE UPDATE ON form_responses FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_todo_items
  BEFORE UPDATE ON todo_items FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_calculation_history
  BEFORE UPDATE ON calculation_history FOR EACH ROW EXECUTE FUNCTION lock_created_by();

-- Fix ADV-2: Force updated_at = NOW() on INSERT (anti-spoofing)
CREATE OR REPLACE FUNCTION enforce_insert_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Apply BEFORE INSERT triggers on all 16 synced data tables:
CREATE TRIGGER enforce_insert_updated_at_projects
  BEFORE INSERT ON projects FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_locations
  BEFORE INSERT ON locations FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_contractors
  BEFORE INSERT ON contractors FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_equipment
  BEFORE INSERT ON equipment FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_bid_items
  BEFORE INSERT ON bid_items FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_personnel_types
  BEFORE INSERT ON personnel_types FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_daily_entries
  BEFORE INSERT ON daily_entries FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_photos
  BEFORE INSERT ON photos FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_entry_equipment
  BEFORE INSERT ON entry_equipment FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_entry_quantities
  BEFORE INSERT ON entry_quantities FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_entry_contractors
  BEFORE INSERT ON entry_contractors FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_entry_personnel_counts
  BEFORE INSERT ON entry_personnel_counts FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_inspector_forms
  BEFORE INSERT ON inspector_forms FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_form_responses
  BEFORE INSERT ON form_responses FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_todo_items
  BEFORE INSERT ON todo_items FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_calculation_history
  BEFORE INSERT ON calculation_history FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();

-- ADV-15: Server-side backup for updated_by_user_id stamping
CREATE OR REPLACE FUNCTION stamp_updated_by()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_TABLE_NAME = 'daily_entries' THEN
    NEW.updated_by_user_id = auth.uid();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

DROP TRIGGER IF EXISTS stamp_updated_by_daily_entries ON daily_entries;
CREATE TRIGGER stamp_updated_by_daily_entries
  BEFORE UPDATE ON daily_entries FOR EACH ROW EXECUTE FUNCTION stamp_updated_by();

-- ADV-22 + ADV-23: Integrity checker RPC with id_checksum
CREATE OR REPLACE FUNCTION get_table_integrity(p_table_name TEXT)
RETURNS TABLE (
  row_count BIGINT,
  max_updated_at TIMESTAMPTZ,
  id_checksum BIGINT
) AS $$
DECLARE
  v_company_id UUID;
  v_sql TEXT;
BEGIN
  v_company_id := get_my_company_id();
  IF v_company_id IS NULL THEN
    RAISE EXCEPTION 'No company context';
  END IF;

  -- Validate table name against allowlist to prevent SQL injection
  IF p_table_name NOT IN (
    'projects', 'locations', 'contractors', 'equipment', 'bid_items',
    'personnel_types', 'daily_entries', 'photos', 'entry_equipment',
    'entry_quantities', 'entry_contractors', 'entry_personnel_counts',
    'inspector_forms', 'form_responses', 'todo_items', 'calculation_history'
  ) THEN
    RAISE EXCEPTION 'Invalid table name: %', p_table_name;
  END IF;

  IF p_table_name = 'projects' THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE company_id = %L AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSIF p_table_name IN ('locations', 'contractors', 'bid_items', 'personnel_types', 'daily_entries',
                          'inspector_forms', 'todo_items', 'calculation_history') THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSIF p_table_name = 'equipment' THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE contractor_id IN (SELECT id FROM contractors WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L)) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSIF p_table_name = 'photos' THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE entry_id IN (SELECT id FROM daily_entries WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L)) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSIF p_table_name = 'form_responses' THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSE
    -- entry_equipment, entry_quantities, entry_contractors, entry_personnel_counts
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE entry_id IN (SELECT id FROM daily_entries WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L)) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  END IF;

  RETURN QUERY EXECUTE v_sql;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE SET search_path = public;

-- Decision 12: Profile expansion — add columns to user_profiles
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS agency TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS initials TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS gauge_number TEXT;

-- Decision 12: New user_certifications table
CREATE TABLE IF NOT EXISTS user_certifications (
  id TEXT PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  cert_type TEXT NOT NULL,
  cert_number TEXT NOT NULL,
  expiry_date DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, cert_type)
);

CREATE TRIGGER update_user_certifications_updated_at
  BEFORE UPDATE ON user_certifications
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Decision 12: Migrate cert_number from user_profiles to user_certifications
INSERT INTO user_certifications (id, user_id, cert_type, cert_number, created_at, updated_at)
SELECT gen_random_uuid()::text, id, 'primary', cert_number, created_at, updated_at
FROM user_profiles
WHERE cert_number IS NOT NULL;

-- After migration verify, drop cert_number from user_profiles:
-- ALTER TABLE user_profiles DROP COLUMN IF EXISTS cert_number;

-- Decision 4 (First-Sync): synced_projects table in Supabase (mirrors local)
-- This is a local-device concept; the Supabase-side version is optional metadata only.
-- The SQLite version (see v30 migration below) is the authoritative source for pull scoping.

-- Set secure_password_change
-- In supabase/config.toml: secure_password_change = true
```

### SQLite Migration (v30)

```sql
-- Add sync_control table (Decision 1)
CREATE TABLE IF NOT EXISTS sync_control (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
INSERT OR IGNORE INTO sync_control (key, value) VALUES ('pulling', '0');

-- Add change_log table (with metadata column)
CREATE TABLE IF NOT EXISTS change_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name TEXT NOT NULL,
  record_id TEXT NOT NULL,
  operation TEXT NOT NULL,
  changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
  processed INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_change_log_unprocessed ON change_log(processed, table_name);

-- Add conflict_log table (with expires_at column)
CREATE TABLE IF NOT EXISTS conflict_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name TEXT NOT NULL,
  record_id TEXT NOT NULL,
  winner TEXT NOT NULL,
  lost_data TEXT NOT NULL,
  detected_at TEXT NOT NULL,
  dismissed_at TEXT,
  expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conflict_log_expires ON conflict_log(expires_at);

-- Add sync_lock table (Decision 2)
CREATE TABLE IF NOT EXISTS sync_lock (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  locked_at TEXT NOT NULL,
  locked_by TEXT NOT NULL
);

-- Add synced_projects table (Decision 4 - first-sync project selection)
CREATE TABLE IF NOT EXISTS synced_projects (
  project_id TEXT PRIMARY KEY,
  synced_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
);

-- Add user_certifications table (Decision 12)
CREATE TABLE IF NOT EXISTS user_certifications (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  cert_type TEXT NOT NULL,
  cert_number TEXT NOT NULL,
  expiry_date TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
  UNIQUE(user_id, cert_type)
);

-- Add profile expansion columns to user_profiles local cache
-- (mirror Supabase schema expansion from Phase 0)
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS agency TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS initials TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS gauge_number TEXT;

-- Fix GAP-11: Fix empty-string timestamp defaults on entry_personnel_counts
-- Requires table rebuild (SQLite cannot ALTER DEFAULT)

-- Install triggers on all 16 synced tables (INSERT/UPDATE/DELETE) with WHEN clause
-- (see trigger template above — explicit list of 16 tables only)

-- Add UNIQUE index on projects(company_id, project_number)
CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_company_number ON projects(company_id, project_number);

-- Bump schema version to v30
```

---

## Testing Strategy

### Stage Trace Scorecard (Sync Round-Trip Verification)

```
Scorecard: Sync Stage Trace
═══════════════════════════════════════════════════════════════
Table                    | Trigger | Convert→ | Push | Pull | Convert← | LWW  | Score
─────────────────────────|---------|----------|------|------|----------|------|──────
projects                 |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
locations                |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
contractors              |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
equipment                |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
bid_items                |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
personnel_types          |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
daily_entries            |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
photos                   |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
entry_equipment          |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
entry_quantities         |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
entry_contractors        |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
entry_personnel_counts   |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
inspector_forms          |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
form_responses           |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
todo_items               |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
calculation_history      |   OK    |    OK    |  OK  |  OK  |    OK    |  OK  | 6/6
═══════════════════════════════════════════════════════════════
TOTAL: 16/16 tables × 6 stages = 96/96 OK
```

Each stage:
- **Trigger**: INSERT/UPDATE/DELETE on SQLite → change_log row created (with WHEN clause check)
- **Convert→**: `adapter.convertForRemote()` produces valid Supabase payload
- **Push**: Supabase accepts the payload (upsert succeeds)
- **Pull**: Incremental pull retrieves the record (with 5-second safety margin)
- **Convert←**: `adapter.convertForLocal()` produces valid SQLite map
- **LWW**: Conflict resolver picks correct winner when both sides modified

### Test Suite Per Phase

Each implementation phase has a mandatory test suite that must pass before proceeding.

**Phase 1 integration tests are explicit prerequisites for Phase 2**: Phase 1 must include integration tests with real SQLite database, installed triggers, actual operations, and verified change_log contents.

### Per-Adapter Unit Tests

```
test/features/sync/adapters/
  project_adapter_test.dart
  daily_entry_adapter_test.dart
  photo_adapter_test.dart
  ... (16 total, one per synced table)

Per test file:
  ✓ convertForRemote: all columns mapped correctly
  ✓ convertForRemote: type conversions round-trip (bool↔int, JSON↔Map, etc.)
  ✓ convertForRemote: local-only columns stripped
  ✓ convertForRemote: null/empty handling for every nullable column
  ✓ convertForLocal: all columns mapped correctly
  ✓ convertForLocal: remote-only columns stripped
  ✓ convertForLocal: JSONB auto-decoded Maps re-encoded as strings
  ✓ convertForLocal: deleted_at/deleted_by handled
  ✓ validate: rejects invalid records (missing required fields)
  ✓ fkDependencies: correctly declares parent tables
  ✓ companyScope: correct scope column and type
  ✓ pull query applies correct company scope filter
```

### Engine Unit Tests

```
test/features/sync/engine/
  change_tracker_test.dart
    ✓ reads unprocessed entries grouped by table
    ✓ marks entries processed
    ✓ respects retry_count limit
    ✓ handles concurrent reads safely
    ✓ with 600 unprocessed entries, only returns 500 (oldest first)
    ✓ anomaly flag set when unprocessed count > 1000

  conflict_resolver_test.dart
    ✓ remote wins when remote.updated_at > local.updated_at
    ✓ local wins when local.updated_at > remote.updated_at
    ✓ logs conflict with changed-columns-only lost_data JSON
    ✓ handles null updated_at (treats as epoch)
    ✓ handles empty-string updated_at gracefully
    ✓ soft-delete conflict: edit-wins when local edited after remote deleted
    ✓ equal timestamps: remote wins AND conflict_log entry created (tiebreaker)
    ✓ ConflictResolver uses server-assigned updated_at from pulled record, not local outbound timestamp

  integrity_checker_test.dart
    ✓ detects count mismatch → resets cursor
    ✓ detects max_ts mismatch → resets cursor
    ✓ detects id_checksum mismatch → resets cursor
    ✓ passes when counts, timestamps, and checksums match
    ✓ stores result in sync_metadata

  sync_mutex_test.dart
    ✓ SQLite advisory lock blocks concurrent syncAll() calls
    ✓ second caller returns false (lock held)
    ✓ releases on exception
    ✓ stale lock (>5 minutes) is auto-expired
```

### Integration Tests

```
test/features/sync/integration/
  push_pull_roundtrip_test.dart
    ✓ Create record locally → push → read from mock Supabase → matches
    ✓ Create on mock Supabase → pull → read from SQLite → matches
    ✓ Full round-trip: local → push → pull on fresh DB → identical

  conflict_resolution_test.dart
    ✓ Both sides modified → LWW picks correct winner
    ✓ Loser's data preserved in conflict_log (changed columns only)
    ✓ Conflict count exposed to UI layer

  soft_delete_sync_test.dart
    ✓ Soft-delete locally → push → remote has deleted_at
    ✓ Soft-delete remotely → pull → local has deleted_at
    ✓ Purge locally → push → remote hard-deleted
    ✓ Restore locally → push → remote has deleted_at=NULL
    ✓ Edit-wins: local edit after remote delete → local wins

  photo_lifecycle_test.dart
    ✓ Three-phase upload: file → metadata → mark synced
    ✓ Phase 1 failure: retry uploads file
    ✓ Phase 2 failure: file exists, retry metadata only
    ✓ Soft-delete photo → push deleted_at → storage cleanup
    ✓ Orphan detection: file in storage with no DB row

  integrity_check_test.dart
    ✓ Injected count drift → detected → cursor reset → full re-pull
    ✓ Injected checksum drift → detected → cursor reset
    ✓ No drift → all tables pass → no re-pull

  trigger_feedback_loop_test.dart
    ✓ Pull inserts records → no change_log entries created (triggers suppressed)
    ✓ Pull with edit-wins conflict → exactly 1 change_log entry for local winner
    ✓ sync_control.pulling reset to '0' after pull completes
    ✓ sync_control.pulling reset to '0' after pull throws exception
    ✓ Startup force-reset: sync_control.pulling='0' at start of every cycle

  deletion_notification_test.dart
    ✓ SyncEngine pull: remote soft-delete by different user creates deletion_notification row
    ✓ SyncEngine pull: remote soft-delete by SAME user does NOT create deletion_notification

  project_selection_test.dart
    ✓ Project selection screen queries Supabase directly (not local SQLite)
    ✓ Selecting project writes to synced_projects table
    ✓ Pull flow filters by synced_projects for project-scoped tables
    ✓ Project not in synced_projects is not pulled
```

### Widget Tests (Settings + Sync UI)

```
test/features/settings/
  settings_screen_test.dart
    ✓ Sections render in correct order (ACCOUNT, SYNC & DATA, FORM SETTINGS, APPEARANCE, ABOUT)
    ✓ Admin Dashboard hidden for non-admins
    ✓ Dead stubs removed (no Backup/Restore/Help stubs)
    ✓ Gauge number field is editable and persists to user_profiles
    ✓ Initials field editable and persists to user_profiles
    ✓ Auto-Load toggle present in APPEARANCE
    ✓ Manage Synced Projects link present in SYNC & DATA

test/features/sync/presentation/
  sync_status_icon_test.dart
    ✓ Green when synced
    ✓ Yellow when pending
    ✓ Red when errors
  sync_dashboard_screen_test.dart
    ✓ Shows per-table health
    ✓ Shows recent activity log
    ✓ Shows conflict count with tap-to-view
    ✓ Integrity check result displayed
  conflict_viewer_test.dart
    ✓ Lists conflicts with lost data preview
    ✓ Dismiss marks dismissed_at
    ✓ Restore re-applies lost data and queues push
    ✓ Restore runs adapter.validate() before applying — valid data succeeds
    ✓ Restore with invalid lost_data shows validation error
    ✓ Restore on purged record shows "permanently deleted" message
  project_selection_screen_test.dart
    ✓ Lists company projects from Supabase
    ✓ Search filters results
    ✓ Tapping project adds to synced_projects
    ✓ Already-synced projects are visually marked
```

---

## Implementation Phases

### Phase 0: Schema + Security
**Agent**: `backend-supabase-agent`
**Scope**: Supabase migration with all security fixes, new tables, profile expansion

Tasks:
- [ ] **FIRST TASK — BLOCKING**: Diagnose and fix storage RLS `foldername` index (NEW-1)
  - Run diagnostic query on existing storage objects to confirm [1]='entries', [2]=companyId
  - Fix all 3 storage policies from `[1]` to `[2]`
  - All subsequent Phase 0 tasks are blocked until this is resolved
- [ ] Add `updated_at` to `entry_contractors` and `entry_personnel_counts` (GAP-10)
- [ ] Add `deleted_at`/`deleted_by` to `inspector_forms` (GAP-9)
- [ ] Backfill and add NOT NULL on `calculation_history.updated_at` (ADV-31)
- [ ] Backfill and add NOT NULL on `project_id` for `inspector_forms`, `todo_items`, `calculation_history` (ADV-9)
- [ ] Drop NOT NULL + FK constraint on `form_responses.form_id` (ADV-33)
- [ ] **PREREQUISITE CHECK**: Verify `update_updated_at_column()` function exists in Supabase before running migration (used by entry_contractors + entry_personnel_counts triggers)
- [ ] **PREREQUISITE CHECK**: Verify `equipment` table already has `deleted_at`/`deleted_by` columns (required by `get_table_integrity()` RPC which filters `AND deleted_at IS NULL` on all 16 tables)
- [ ] Create `is_approved_admin()` helper with `SET search_path = public` (NEW-7)
- [ ] Update all 6 admin RPCs: `is_approved_admin()` as FIRST check, `SET search_path = public` (NEW-7)
- [ ] Create COALESCE-based `lock_created_by()` trigger on all 16 data tables (NEW-6)
- [ ] Create `enforce_insert_updated_at()` trigger on all 16 data tables (ADV-2)
- [ ] Create `stamp_updated_by()` trigger on `daily_entries` (ADV-15)
- [ ] Create `get_table_integrity()` RPC with id_checksum (Decision 5)
- [ ] Add profile expansion columns to `user_profiles` (Decision 12)
- [ ] Create `user_certifications` table with UNIQUE(user_id, cert_type) (Decision 12)
- [ ] Migrate `cert_number` from `user_profiles` to `user_certifications` (Decision 12)
- [ ] Set `secure_password_change = true` in `supabase/config.toml` (GAP-19)
- [ ] Interim fix: add `case 'purge':` to `_processSyncQueueItem` (GAP-3) — uses sync_control gate
- [ ] Document NEW-13 (edit own records only) as explicitly deferred to post-rewrite security hardening. Create backlogged plan entry.
- [ ] Deploy migration + verify

Tests:
- [ ] Upload a photo → verify RLS accepts it
- [ ] Deactivated admin calls `approve_join_request` → verify rejection
- [ ] UPDATE `created_by_user_id` on record with existing value → verify trigger preserves original
- [ ] UPDATE `created_by_user_id` on legacy record (NULL) → verify trigger allows first-time stamping via auth.uid()
- [ ] UPDATE `created_by_user_id` to NULL on any record → verify trigger prevents erasure
- [ ] Verify `updated_at` trigger fires on entry_contractors/entry_personnel_counts
- [ ] Verify inspector_forms soft-delete columns exist
- [ ] Verify `calculation_history.updated_at` is NOT NULL after migration
- [ ] Verify `project_id` is NOT NULL on all 3 toolbox tables after migration
- [ ] INSERT with client-supplied `updated_at = '2099-01-01'` → verify server forces `NOW()`
- [ ] Verify user_certifications table exists and UNIQUE constraint is enforced
- [ ] Verify user_profiles has email, agency, initials, gauge_number columns

### Phase 1: Change Tracking Foundation
**Agent**: `backend-data-layer-agent`
**Scope**: SQLite v30 migration — change_log, conflict_log, triggers, sync_control, new tables

**PREREQUISITE**: Phase 0 tests must all pass. Phase 1 integration tests are prerequisites for Phase 2.

Tasks:
- [ ] Create `sync_control` table with `pulling = '0'` default (Decision 1)
- [ ] Create `change_log` table in SQLite schema (with metadata column)
- [ ] Create `conflict_log` table in SQLite schema (with expires_at column — Decision 8)
- [ ] Create `sync_lock` table in SQLite schema (Decision 2)
- [ ] Create `synced_projects` table in SQLite schema (Decision 4)
- [ ] Add `user_certifications` table to SQLite schema (Decision 12)
- [ ] Add profile expansion columns to local user_profiles table (email, agency, initials, gauge_number)
- [ ] Create SQLite triggers for all 16 synced tables (INSERT/UPDATE/DELETE) with WHEN clause
- [ ] Fix empty-string defaults on `entry_personnel_counts` (GAP-11) — table rebuild
- [ ] Add `sync_metadata` entries for per-table cursors
- [ ] Add UNIQUE index on `projects(company_id, project_number)` in SQLite
- [ ] Add `AND (deleted_at IS NULL)` filter to `SyncStatusMixin.getPendingSync()` for transition safety
- [ ] Stamp `created_by_user_id` at model creation: DailyEntry, Photo, all models (NEW-5)
- [ ] Schema verifier: add change_log, conflict_log, sync_control, sync_lock, synced_projects, user_certifications to verified tables
- [ ] Bump SQLite schema to v30

Tests (stage trace — trigger stage):
- [ ] For each of 16 tables: INSERT → verify change_log row with operation='insert'
- [ ] For each of 16 tables: UPDATE → verify change_log row with operation='update'
- [ ] For each of 16 tables: DELETE → verify change_log row with operation='delete'
- [ ] Soft-delete → verify change_log captures the UPDATE (deleted_at set)
- [ ] Batch insert → verify all rows logged
- [ ] Verify `created_by_user_id` populated on new DailyEntry creation
- [ ] Submit entry → verify change_log row with operation='update'
- [ ] Undo submit → verify change_log row with operation='update'
- [ ] batchSubmit 10 entries → verify 10 change_log rows
- [ ] **Integration test**: Real SQLite DB, install triggers, INSERT/UPDATE/DELETE, verify change_log
- [ ] **Trigger suppression test**: Set sync_control.pulling='1', INSERT record, verify NO change_log entry
- [ ] **Startup force-reset test**: After crash with pulling='1', startup resets to '0'
- [ ] Verify `extraction_metrics` and `stage_metrics` do NOT have triggers installed

### Phase 2: Sync Engine Core
**Agent**: `backend-data-layer-agent`
**Scope**: Engine classes, no table adapters yet (mock adapters for testing)

**PREREQUISITE**: Phase 1 integration tests must all pass.

Tasks:
- [ ] `SyncMutex` — SQLite advisory lock with 5-min stale timeout + startup reset (Decision 2)
- [ ] `ChangeTracker` — reads change_log, groups by table, respects retry limit, enforces max 500/cycle (Decision 3)
- [ ] `ConflictResolver` — LWW comparison + conflict_log writes (changed columns only — Decision 8)
- [ ] ConflictResolver: set `expires_at = detected_at + 7 days` on conflict_log entries
- [ ] `SyncEngine` — push/pull orchestrator skeleton with error classification (Decision 3)
- [ ] **Redesign `SoftDeleteService` purge flow** for trigger-based engine:
  - Remove `queueSync` callback parameter from `hardDeleteWithSync()`
  - Purge path: set `sync_control.pulling='1'` → hard DELETE → reset `pulling='0'` → manually INSERT `change_log` entry with `operation='delete'`
  - Normal soft-delete path: triggers auto-create `change_log` entries (no manual intervention)
- [ ] SyncEngine: startup force-reset `sync_control.pulling = '0'` and `DELETE FROM sync_lock` at start of every cycle
- [ ] SyncEngine: add conflict_log cleanup step — delete expired+dismissed entries each sync cycle
- [ ] SyncEngine: add change_log pruning — delete processed entries older than 7 days (Decision 9)
- [ ] SyncEngine: implement sync_control gate for pull operations (`try/finally` guarantees reset)
- [ ] SyncEngine: implement deletion notification creation in pull flow when remote soft-deletes arrive from different users
- [ ] SyncEngine: parent-blocking check before pushing child tables (Decision 3)
- [ ] SyncEngine: handle delete operations using record_id only (no local read) (Decision 3)
- [ ] SyncEngine: auth token refresh on 401, never increment retry_count for auth failures (Decision 3)
- [ ] SyncEngine: edit-wins path explicitly inserts change_log entry (bypassing trigger suppression)
- [ ] `TableAdapter` base class (abstract) with extractRecordName, userStampColumns
- [ ] `SyncRegistry` — adapter registration + dependency ordering
- [ ] `SyncConfig` — chunk sizes, retry limits, timeouts, maxPushPerCycle = 500
- [ ] `IntegrityChecker` — 4-hour count+max+checksum comparison logic (Decision 5)
- [ ] Benchmark: cascade soft-delete of 500 records with triggers. Target: <500ms on mid-range device.

Tests:
- [ ] ChangeTracker: reads grouped changes, marks processed, respects retry limit
- [ ] ChangeTracker: with 600 unprocessed entries, only returns 500 (oldest first)
- [ ] ChangeTracker: anomaly flag set when unprocessed count > 1000
- [ ] ConflictResolver: all LWW scenarios (remote wins, local wins, null timestamps, soft-delete edit-wins)
- [ ] ConflictResolver: equal timestamps → remote wins + conflict_log entry
- [ ] ConflictResolver: lost_data contains only changed columns
- [ ] SyncMutex: SQLite lock blocks concurrent calls, expires stale locks
- [ ] IntegrityChecker: detects drift (count, max_ts, checksum), resets cursors
- [ ] SyncEngine: push/pull with mock adapters
- [ ] SyncEngine: push skips table when parent has failed entries
- [ ] SyncEngine: delete operation sends DELETE by record_id, no local read
- [ ] SyncEngine: 401 triggers token refresh, no retry_count increment
- [ ] SyncEngine: 429 triggers exponential backoff
- [ ] SyncEngine pull: remote soft-delete by different user creates deletion_notification row
- [ ] SyncEngine pull: remote soft-delete by SAME user does NOT create deletion_notification
- [ ] SyncEngine pull: triggers suppressed during pull, re-enabled after (even on exception)
- [ ] SyncEngine pull: edit-wins conflict creates explicit change_log entry

### Phase 3: Table Adapters
**Agent**: `backend-data-layer-agent` (data) + `backend-supabase-agent` (type conversions)
**Scope**: One adapter per synced table, tested individually

Implementation order (FK dependency):
1. `projects` (root — companyScope: direct)
2. `locations`, `contractors`, `bid_items`, `personnel_types` (one-hop via project_id)
3. `equipment` (one-hop via contractor_id → projects)
4. `daily_entries` (one-hop via project_id)
5. `inspector_forms`, `form_responses`, `todo_items`, `calculation_history` (one-hop via project_id)
6. `entry_equipment`, `entry_quantities` (two-hop via entry_id → daily_entries)
7. `entry_contractors`, `entry_personnel_counts` (two-hop — formerly unsynced, GAP-6)

Per adapter:
- [ ] Column mapping (local ↔ remote)
- [ ] Type converters (BoolInt, JsonMap, Timestamp, Bytea as needed)
- [ ] FK dependencies declared
- [ ] Company scope column and type
- [ ] Local-only columns (file_path, filename for photos)
- [ ] Validation rules
- [ ] JSONB conversion for inspector_forms (field_definitions, parsing_keywords) and calculation_history (input_data, result_data) (GAP-16)
- [ ] BYTEA conversion for inspector_forms.template_bytes using ByteaConverter (base64) (NEW-9)
- [ ] `daily_entry_adapter`: override `userStampColumns` to return `{'updated_by_user_id': 'current_user_id'}`
- [ ] `daily_entry_adapter.convertForRemote()`: stamp `updated_by_user_id` with current user ID
- [ ] Refactor `entry_contractors_local_datasource.setForEntry()` to diff-based approach:
  - Compute diff: insert new, soft-delete removed, leave unchanged alone
  - Eliminates N DELETE + M INSERT change_log entries for a single logical "replace"
  - Prevents data loss on network failure mid-push
- [ ] `inspector_form_adapter.validate()`: reject records with null project_id
- [ ] `todo_item_adapter.validate()`: reject records with null project_id
- [ ] `calculation_history_adapter.validate()`: reject records with null project_id
- [ ] `project_adapter.validate()`: reject duplicate project_number within same company_id
- [ ] `form_response_adapter.validate()`: handle NULL `form_id` gracefully (NOT rejected — constraint was dropped)
- [ ] Pull query for each adapter scoped to `synced_projects`: add `project_id IN (SELECT project_id FROM synced_projects)` filter where applicable

Tests (stage trace — convert stages):
- [ ] Per adapter: convertForRemote produces valid payload
- [ ] Per adapter: convertForLocal produces valid SQLite map
- [ ] Per adapter: round-trip (local → remote → local) preserves all data
- [ ] Per adapter: null/empty handling for every nullable column
- [ ] Per adapter: type converters round-trip correctly
- [ ] Per adapter: pull query applies correct company scope filter
- [ ] Per adapter: pull query respects synced_projects filter
- [ ] Integration: full push/pull roundtrip per table against mock Supabase

### Phase 4: Photo Adapter
**Agent**: `backend-data-layer-agent`
**Scope**: Three-phase photo sync, storage cleanup, orphan detection

Tasks:
- [ ] `PhotoAdapter` extends `TableAdapter` — override push with three-phase logic
- [ ] Phase 1: Upload file (check existing, skip if present)
- [ ] Phase 2: Upsert metadata (include fresh remote_path from Phase 1, not stale map — fixes NEW-4)
- [ ] Phase 3: Mark local synced (only after 1+2 succeed — fixes NEW-3)
- [ ] Photo soft-delete push (send deleted_at to Supabase)
- [ ] Storage cleanup phase: delete files for 30-day-expired soft-deleted photos
- [ ] Orphan scanner: query photos table, list storage by company prefix, diff, flag orphans >24h old
- [ ] Refactor `PhotoLocalDatasource.deleteByEntryId()` to soft-delete:
  - Change from hard DELETE to `UPDATE photos SET deleted_at = ?, deleted_by = ? WHERE entry_id = ?`
  - Hard DELETE generates `operation='delete'` entries that bypass 30-day trash retention
  - Soft-delete generates `operation='update'` entries that correctly push deleted_at to Supabase
- [ ] Audit and refactor all hard-delete `deleteByEntryId()` methods:
  - `entry_equipment_local_datasource.deleteByEntryId()`
  - `entry_quantity_local_datasource.deleteByEntryId()`
  - `form_response_local_datasource.deleteByEntryId()`

Tests:
- [ ] Three-phase success: upload → metadata → mark synced
- [ ] Phase 1 failure → retry re-uploads
- [ ] Phase 2 failure → file exists in storage → retry metadata only
- [ ] Phase 1+2 succeed, Phase 3 fails → next cycle skips upload, upserts, marks
- [ ] Soft-delete photo → push → remote has deleted_at
- [ ] Storage cleanup: 30-day-expired photos cleaned from bucket
- [ ] Orphan detection: storage file with no DB row → flagged
- [ ] `deleteByEntryId()` sets deleted_at instead of hard-deleting
- [ ] `deleteByEntryId()` generates change_log UPDATE entries (not DELETE)
- [ ] Soft-deleted photos are pushed with deleted_at to Supabase (30-day trash honored)

### Phase 5: Integrity Checker + Incremental Pull
**Agent**: `backend-data-layer-agent`
**Scope**: 4-hour integrity check, incremental pull cursors, project selection pull

Tasks:
- [ ] Wire incremental pull into SyncEngine: `WHERE updated_at > last_pull_{table} - INTERVAL '5 seconds'`
- [ ] First sync / missing cursor: full pull for selected projects (Decision 4)
- [ ] Store per-table `last_pull_{table}` cursor in sync_metadata
- [ ] IntegrityChecker integration: schedule every 4 hours via WorkManager (Decision 5)
- [ ] IntegrityChecker: compare count + max_ts + id_checksum via get_table_integrity RPC
- [ ] Drift detection → cursor reset → targeted full re-pull
- [ ] Surface integrity results in sync_metadata for UI
- [ ] Orphan scanner wired into integrity check cycle (Decision 5)

Tests:
- [ ] Incremental pull: only fetches records newer than cursor minus 5-second margin
- [ ] Deduplication: records within safety margin overlap are not re-inserted
- [ ] Full pull on first sync (cursor is null) — scoped to synced_projects
- [ ] Cursor advances after successful pull
- [ ] Cursor NOT updated for incomplete tables during interrupted first sync
- [ ] Integrity check: injected count drift → detected → cursor reset
- [ ] Integrity check: injected checksum drift → detected → cursor reset
- [ ] Integrity check: no drift → passes → no re-pull
- [ ] Integrity check result stored and retrievable

### Phase 6: UI + Settings Redesign + Profile Expansion
**Agent**: `frontend-flutter-specialist-agent`
**Scope**: New sync UI, settings restructure, dead code removal, profile expansion UI

Sync UI tasks:
- [ ] `SyncStatusIcon` widget — app bar, colored (green/yellow/red) — replaces `SyncStatusBanner`
- [ ] Toast notifications on sync failure (with error detail)
- [ ] `SyncDashboardScreen` — per-table health, recent activity, pending/failed counts, integrity check results
- [ ] `ConflictViewerScreen` — list conflicts, view lost data, dismiss/restore
  - Restore action MUST run `adapter.validate()` on lost_data before applying
  - If validation fails, show user-facing error
  - If record was purged, show "permanently deleted and cannot be restored"
  - Restore flow: read lost_data → read current record → merge → validate → UPDATE SQLite → mark dismissed
- [ ] `ProjectSelectionScreen` (`/sync/project-selection`) — query Supabase directly, search, tap to add to synced_projects
- [ ] Conflict log cleanup: auto-dismiss conflicts older than 30 days
- [ ] Wire Sync Dashboard into Settings > Sync & Data section
- [ ] Wire Project Selection Screen into Settings > Sync & Data section
- [ ] `DeletionNotificationBanner` — KEEP, wire to new engine's deletion_notifications table
- [ ] Fix GAP-17: Add `AND deleted_at IS NULL` to `getDatesWithEntries` query
- [ ] Fix GAP-18: Add `AND deleted_at IS NULL` to `location_local_datasource.search()`

Settings redesign tasks:
- [ ] Restructure sections: Account → Sync & Data → Form Settings → Appearance → About
- [ ] Remove dead toggles: auto_fill_enabled, use_last_values, auto_sync_wifi, auto_fetch_weather
- [ ] Remove dead stubs: Backup Data, Restore Data, Help & Support snackbars
- [ ] Remove duplicate: "Default Signature Name" tile
- [ ] Remove unactionable displays: Weather API tile
- [ ] Move Company Template display to Form Settings (read-only info)
- [ ] Add editable Gauge Number field to Form Settings (reads/writes user_profiles.gauge_number)
- [ ] Add editable Initials field to Form Settings (auto-derived from displayName; manually overridable)
- [ ] Keep Auto-Load toggle in APPEARANCE section (from ProjectSettingsProvider)
- [ ] Delete `EditInspectorDialog` widget (orphaned — zero call sites)
- [ ] Remove dead pref keys: show_only_manual_fields, last_route_location, prefill_* families, inspector_agency
- [ ] Migrate form auto-fill reads: PreferencesService → AuthProvider.userProfile (NO fallback — Decision 12)
- [ ] **Fix `entry_photos_section.dart:88`**: Raw `SharedPreferences` access `prefs.getString('inspector_initials')` bypasses PreferencesService entirely — must inject AuthProvider or read `userProfile.initials` from context
- [ ] **Update `form_response_repository.dart:384-385`**: `requireHeader('cert_number', ...)` — ensure auto-fill pipeline resolves cert_number from `user_certifications` via AuthProvider (not from PreferencesService)
- [ ] Update PDF data builder: source = userProfile.displayName (no prefs fallback — Decision 12)
  - `pdf_data_builder.dart:130,134` — two `prefs.getString('inspector_name')` calls to replace
- [ ] PII cleanup: delete all legacy PII keys from SharedPreferences on first launch after update
- [ ] Update Edit Profile screen to show/edit: displayName, email (read-only), agency, initials, phone
- [ ] Wire UserProfileSyncDatasource to sync user_certifications alongside user_profiles

Tests:
- [ ] Widget test: settings sections render in correct order
- [ ] Widget test: dead items are gone
- [ ] Widget test: gauge number field editable, persists to user_profiles (not PreferencesService)
- [ ] Widget test: initials field editable, persists to user_profiles
- [ ] Widget test: Auto-Load toggle present in APPEARANCE
- [ ] Widget test: Manage Synced Projects link present
- [ ] Widget test: sync icon colors match state
- [ ] Widget test: sync dashboard shows correct per-table data
- [ ] Widget test: conflict viewer shows lost data
- [ ] Widget test: conflict viewer restore runs validate() — valid succeeds
- [ ] Widget test: conflict viewer restore with invalid data shows error
- [ ] Widget test: conflict viewer restore on purged record shows "permanently deleted"
- [ ] Widget test: project selection screen lists projects from Supabase
- [ ] Widget test: project selection search filters results
- [ ] Integration: form auto-fill reads from userProfile (no prefs fallback)

### Phase 7: Cutover + Cleanup (Decision 10 — Big Bang)
**Agent**: `backend-data-layer-agent` + `code-review-agent`
**Scope**: Wire new engine into app, remove old system entirely, full regression

**Cutover strategy (Decision 10)**: Big Bang. The new engine is built entirely on the feature branch (`fix/sync-rewrite` or similar). The old SyncService remains functional throughout Phases 0-6 on the feature branch — it is the active sync system during development. When Phase 7 is complete and all tests pass, the old code is deleted and the branch is merged. No dual-write period. No feature flag. No coexistence spec. Git history is the rollback mechanism.

Tasks:
- [ ] Wire new SyncEngine into app lifecycle (replace old SyncService calls)
- [ ] Update SyncOrchestrator to delegate to new engine
- [ ] Update SyncProvider to read from new engine state
- [ ] Update BackgroundSyncHandler: instantiate its own SyncEngine, use SQLite advisory lock
- [ ] Drain accumulated change_log: first sync after wiring processes all accumulated entries
- [ ] **Verify `SyncLifecycleManager`** works with rewired orchestrator
- [ ] **Verify `FcmHandler`** is a no-op stub — confirm it does not call old SyncService methods
- [ ] **Update `MockSyncAdapter`** to implement new engine interfaces for test mode
- [ ] Remove old SyncService (1535 lines)
- [ ] Remove `sync_status` columns from all tables (SQLite migration v31)
  - **NOTE**: SQLite on Android < API 35 does not support `ALTER TABLE DROP COLUMN`. Must use table rebuild pattern: CREATE new table → INSERT INTO SELECT → DROP old → ALTER TABLE RENAME.
  - Tables requiring rebuild: `daily_entries`, `photos`
- [ ] Remove `sync_queue` table (SQLite migration v31)
- [ ] Remove `sync_status` indexes: `idx_daily_entries_sync_status`, `idx_photos_sync_status`
- [ ] Remove all `queueOperation()` calls from providers AND screens:
  - `calculator_provider.dart` (2 calls: insert, delete)
  - `inspector_form_provider.dart` (5 calls)
  - `todo_provider.dart` (4 calls: insert, update, update, delete)
  - **`personnel_types_screen.dart` (4 calls — this is a SCREEN, not a provider)**
  - `sync_provider.dart` (interface method + 1 call)
  - `sync_orchestrator.dart` (interface method + 1 call)
  - `supabase_sync_adapter.dart` (4 calls)
  - `sync_adapter.dart` (interface definition)
  - `mock_sync_adapter.dart` (1 call)
  - `stub_services.dart` (1 call)
- [ ] Remove `SyncStatusMixin` and `SyncStatus` enum
  - **BEFORE removing**: Verify the Phase 1 `AND deleted_at IS NULL` filter is in place
- [ ] Remove `SyncStatusBanner` widget (replaced by SyncStatusIcon in Phase 6)
- [ ] **Update `home_screen.dart:381`**: Replace `const SyncStatusBanner()` with new `SyncStatusIcon` widget
- [ ] Remove `_pushBaseData`, `_pushPendingEntries`, `_pushPendingPhotos`
- [ ] Remove `deleteAll()` from BaseRemoteDatasource (or restrict to test-only subclass)
- [ ] Verify `entry_personnel` has no triggers, no adapter, no Supabase migration — confirm legacy status

#### Phase 7a: Model & Enum Cleanup
- [ ] **Remove `syncStatus` field from `DailyEntry` model** (`features/entries/data/models/daily_entry.dart:29`):
  - Remove field declaration, constructor param, copyWith param
  - Remove `'sync_status': syncStatus.toJson()` from `toMap()`
  - Remove `syncStatus: SyncStatus.fromJson(...)` from `fromMap()`
- [ ] **Remove `syncStatus` field from `Photo` model** (same pattern as DailyEntry)
- [ ] **Delete `shared/models/sync_status.dart`** (entire SyncStatus enum file)
- [ ] **Remove `getSyncStatusColor()` from `core/theme/colors.dart:172`** and `core/theme/app_theme.dart:1540`

#### Phase 7b: Auth & Sign-Out Cleanup
- [ ] **Update `auth_service.dart:328`**: Sign-out currently wipes `sync_queue`. Replace with cleanup of new engine tables:
  - `DELETE FROM change_log`
  - `DELETE FROM conflict_log`
  - `DELETE FROM sync_lock`
  - `DELETE FROM sync_metadata`
  - `DELETE FROM synced_projects`

#### Phase 7c: entry_personnel Legacy Cleanup
- [ ] **Delete `features/contractors/data/datasources/local/entry_personnel_local_datasource.dart`** (dead table datasource)
- [ ] **Delete `features/contractors/data/datasources/remote/entry_personnel_remote_datasource.dart`** (dead table datasource)
- [ ] **Remove `entry_personnel` from `SoftDeleteService` cascade lists** (3 locations):
  - `soft_delete_service.dart:18` — table list
  - `soft_delete_service.dart:82` — cascade delete list
  - `soft_delete_service.dart:121` — cascade restore list
- [ ] Remove any barrel file exports for entry_personnel datasources

#### Phase 7d: Seed Data & Test Harness
- [ ] **Update `core/database/seed_data_service.dart:381`**: Remove `'sync_status': 'synced'` from seed data
- [ ] **Update `test_harness/harness_seed_data.dart:230`**: Migrate `'cert_number': 'CERT-001'` to new `user_certifications` seed entry
- [ ] **Update `test_harness/harness_seed_data.dart`**: Remove any `sync_status` references from seed data

#### Phase 7e: Schema Verifier Cleanup
- [ ] **Update `schema_verifier.dart`**: Remove `sync_status` from verified column lists:
  - Line 64: daily_entries columns
  - Line 114: photos columns
  - Line 188: daily_entries self-heal definitions
  - Line 218: photos self-heal definitions
- [ ] **Update `schema_verifier.dart`**: Remove `sync_queue` from verified tables (line 120)
- [ ] **Update `schema_verifier.dart`**: Add new engine tables to verified tables list:
  - `change_log`, `conflict_log`, `sync_control`, `sync_lock`, `synced_projects`, `sync_metadata`, `user_certifications`

#### Phase 7f: Testing Keys Cleanup
- [ ] **Remove dead testing keys from `shared/testing_keys/settings_keys.dart`**:
  - `settingsInspectorNameTile`, `settingsInspectorInitialsTile`, `settingsInspectorAgencyTile`
  - `editInspectorNameDialog`, `editInspectorNameCancel`, `editInspectorNameSave`
  - `editInspectorAgencyDialog`, `editInspectorAgencySave`
  - `settingsUseLastValuesToggle`
- [ ] Update `shared/testing_keys/testing_keys.dart` if any re-exported keys were removed

#### Phase 7g: PreferencesService Cleanup
- [ ] **Remove or update `PreferencesService.buildInspectorProfile()` method** (~line 320) which assembles profile data from SharedPreferences keys — superseded by `AuthProvider.userProfile`
- [ ] **Remove dead pref key constants** from `PreferencesService`:
  - `keyInspectorCertNumber` (line 18)
  - (keys already listed in Phase 6: inspector_name, inspector_initials, inspector_agency, gauge_number, show_only_manual_fields, last_route_location, prefill_* families)

#### Phase 7h: Final Verification
- [ ] Code review: verify no references to old sync patterns (`sync_status`, `sync_queue`, `queueOperation`, `SyncStatusMixin`, `markSynced`)
- [ ] Full regression test
- [ ] Stage trace scorecard: run all 16 tables × 6 stages = 96 checks

Tests:
- [ ] Full stage trace scorecard: 96/96 OK
- [ ] Sync on connectivity restore: push + incremental pull
- [ ] Sync on app open (stale): forced sync
- [ ] Manual sync via Sync Dashboard
- [ ] Soft-delete → push → pull on second device → deleted
- [ ] Purge from trash → push → gone from Supabase (purge bypasses triggers via sync_control gate)
- [ ] Photo full lifecycle: create → sync → edit caption → sync → soft-delete → sync → purge
- [ ] Conflict scenario: both sides edit → LWW → conflict logged → visible in UI
- [ ] Integrity check: runs every 4 hours, results visible in dashboard
- [ ] New team member first sync: project selection screen → select projects → full pull for selected projects
- [ ] Settings: all new sections render, no dead items, gauge number and initials work
- [ ] BackgroundSyncHandler: spawns own SyncEngine, advisory lock prevents concurrent foreground sync
- [ ] SyncLifecycleManager: calls through rewired orchestrator successfully
- [ ] MockSyncAdapter: implements new engine interfaces, test mode works
- [ ] user_certifications: syncs alongside user_profiles, UNIQUE constraint respected
- [ ] Profile expansion: gauge_number, initials, agency read from user_profiles (not prefs)
- [ ] Sign-out wipes new engine tables (change_log, conflict_log, sync_lock, sync_metadata, synced_projects)
- [ ] Sign-out does NOT reference sync_queue (table no longer exists)
- [ ] Seed data inserts succeed without sync_status column
- [ ] entry_personnel datasource files are deleted and no imports reference them
- [ ] SoftDeleteService cascade lists do NOT include entry_personnel
- [ ] Schema verifier validates all new engine tables on startup
- [ ] Schema verifier does NOT reference sync_status or sync_queue
- [ ] Dead testing keys are removed from settings_keys.dart
- [ ] `entry_photos_section.dart` reads initials from AuthProvider.userProfile (not raw SharedPreferences)
- [ ] `form_response_repository.dart` resolves cert_number from user_certifications (not PreferencesService)
- [ ] `DailyEntry.toMap()`/`fromMap()` do NOT include sync_status
- [ ] `Photo.toMap()`/`fromMap()` do NOT include sync_status
- [ ] **Dead code grep**: `rg 'sync_status|sync_queue|queueOperation|SyncStatusMixin|markSynced|SyncStatusBanner' lib/` returns zero matches

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| New engine has bugs old system didn't | Big Bang on feature branch — old SyncService stays functional throughout development. Stage trace scorecard (96/96) is the quality gate before merge. Git history is the rollback mechanism. |
| SQLite triggers add write latency | Benchmark: triggers add ~1ms per single write. Cascade benchmark (500 records) target: <500ms on mid-range device. Purge operations bypass triggers via sync_control gate. |
| Migration v30 is complex (table rebuild for entry_personnel_counts) | Test migration on copy of production DB before deploying. Schema verifier catches drift. |
| Photo three-phase adds push complexity | Each phase is independently testable. Failure at any phase is recoverable. Orphan scanner detects abandoned uploads. |
| Settings redesign breaks user muscle memory | Sections are reorganized but all kept items are still present. No functional loss. Auto-Load toggle preserved in APPEARANCE. |
| Incremental pull misses records due to clock skew | 5-second safety margin on cursor comparison. 4-hour integrity check with id_checksum catches drift much faster than daily. |
| Migration v31 DROP COLUMN on old Android | SQLite < 3.35.0 (Android < API 35) lacks ALTER TABLE DROP COLUMN. Use table rebuild pattern (CREATE → INSERT INTO SELECT → DROP → RENAME). Test on minSdk 24 device. |
| SoftDeleteService purge bypass with triggers | Purge flow sets sync_control.pulling='1' to suppress triggers, then manually inserts change_log entry. try/finally guarantees reset. Unit test required. |
| Cleanup misses stale references | Phase 7h dead code grep (`sync_status`, `sync_queue`, `queueOperation`, `SyncStatusMixin`, `markSynced`, `SyncStatusBanner`) must return zero hits before merge. |
| Trigger-pull feedback loop | sync_control table gates trigger execution during pull. WHEN clause prevents change_log entries during pull. Startup force-reset recovers from crash. |
| Concurrent sync from foreground + background | SQLite advisory lock with 5-minute auto-expiry replaces Completer mutex. Works across isolates. |
| Auth token expires during long sync | 401 triggers token refresh. Auth failures never increment retry_count. Refresh failure aborts sync with "re-login required." |
| First sync overwhelming for large companies | User-driven project selection — user chooses what to download. Pull scoped to synced_projects only. Progress indicator per table. |
| profile reads break during auth flow | No fallback to prefs — if userProfile is null, form auto-fill shows empty. This is correct behavior (user not logged in). |

---

## Agent Assignments

| Phase | Primary Agent | Secondary Agent |
|-------|--------------|-----------------|
| 0 | backend-supabase-agent | security-agent (review) |
| 1 | backend-data-layer-agent | qa-testing-agent (trigger tests) |
| 2 | backend-data-layer-agent | qa-testing-agent (engine tests) |
| 3 | backend-data-layer-agent | backend-supabase-agent (type conversions) |
| 4 | backend-data-layer-agent | qa-testing-agent (photo lifecycle tests) |
| 5 | backend-data-layer-agent | qa-testing-agent (integrity tests) |
| 6 | frontend-flutter-specialist-agent | code-review-agent (settings cleanup) |
| 7 | backend-data-layer-agent | code-review-agent (full review) |

---

## Success Criteria

1. **Stage trace scorecard**: 16 tables × 6 stages = 96/96 OK
2. **Zero sync gaps**: All 30 documented gaps resolved
3. **PRD alignment**: created_by_user_id stamped, sync-on-save works for ALL tables, conflict visibility
4. **Settings clean**: No dead toggles, no stubs, no orphaned widgets, logical section ordering
5. **User transparency**: Sync failures visible via toast + dashboard, conflicts browsable
6. **Self-healing**: 4-hour integrity check with id_checksum catches and corrects drift automatically
7. **All tests pass**: Unit + integration + widget + stage trace
8. **Profile clean**: All profile data from user_profiles via AuthProvider; no prefs fallback; PII cleaned from SharedPreferences
9. **First-sync experience**: User selects projects; only chosen projects pulled; progress visible

---

## Deferred Security Hardening

Items identified during adversarial review, explicitly deferred to a post-rewrite security hardening pass:

| ID | Finding | Recommendation | Priority |
|----|---------|---------------|----------|
| ADV-13 (NEW-13) | No "edit own records only" enforcement (PRD decision 7) | Defer to post-rewrite. Requires RLS UPDATE policies checking created_by_user_id. | HIGH |
| ADV-55 | SQLite database encryption (sqflite, not sqlcipher) | Track as separate security hardening task. | HIGH |
| ADV-56 | EXIF GPS stripping before photo upload | Track as separate privacy task. | MEDIUM |
| ADV-57 | Background sync auth session verification | Check `currentSession` before starting sync in BackgroundSyncHandler. | MEDIUM |
| ADV-58 | Photo upload idempotency race (two devices, same path) | Low probability in practice (UUIDs in filename). Document as known edge case. | LOW |
| ADV-59 | `deleteAll()` in BaseRemoteDatasource | Remove in Phase 7 cleanup. | MEDIUM |
| ADV-60 | No audit trail for admin RPC calls | Consider `admin_audit_log` table in future. | LOW |
| ADV-61 | Viewer role can read all company data | Intentional design decision (company-wide read access). | LOW |
| ADV-62 | Sync config hardcoded — no remote kill switch | Consider `app_config` table with hardcoded fallbacks. | LOW |
| ADV-63 | change_log tamper protection on rooted device | Accept as inherent risk; RLS prevents cross-tenant damage. Add anomaly detection for impossible timestamps. | LOW |
