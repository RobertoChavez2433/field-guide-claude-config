# Backend-Supabase Agent Memory

## Supabase CLI Usage

Always access via `npx supabase` (bare `supabase` command not available):

```bash
npx supabase db push               # Push pending migrations to remote
npx supabase db pull               # Pull remote schema changes
npx supabase db diff               # Diff local vs remote schema
npx supabase migration new <name>  # Create timestamped migration file
npx supabase status                # Check Supabase status
npx supabase db reset              # Reset database (dev only!)
npx supabase functions list        # List edge functions
```

Migration files land in `supabase/migrations/` with timestamp naming:
`YYYYMMDDHHMMSS_descriptive_name.sql`

## RLS Policy Patterns

All user-facing tables use company-scoped RLS. The standard pattern:

```sql
-- Enable RLS first
ALTER TABLE daily_entries ENABLE ROW LEVEL SECURITY;

-- Read: own company only (uses get_my_company_id() helper)
CREATE POLICY "company_select" ON daily_entries FOR SELECT TO authenticated
  USING (company_id = get_my_company_id());

-- Insert: own company, not viewer
CREATE POLICY "company_insert" ON daily_entries FOR INSERT TO authenticated
  WITH CHECK (company_id = get_my_company_id() AND NOT is_viewer());

-- Update: own company, not viewer
CREATE POLICY "company_update" ON daily_entries FOR UPDATE TO authenticated
  USING (company_id = get_my_company_id())
  WITH CHECK (company_id = get_my_company_id() AND NOT is_viewer());

-- Delete: not used directly — soft-delete only (deleted_at)
```

### Key RLS Helper Functions

- `get_my_company_id()` — returns the caller's company_id from user_profiles
- `is_viewer()` — returns true if caller has viewer role (read-only)
- `is_approved_admin()` — returns true if caller is admin + approved

### Storage Bucket RLS

Upload path format: `entries/{companyId}/{entryId}/{filename}`

```sql
-- Use index [2] for companyId (NOT [1] which is 'entries' literal)
CREATE POLICY "company_photo_select" ON storage.objects
  FOR SELECT TO authenticated
  USING (bucket_id = 'entry-photos'
    AND (storage.foldername(name))[2] = get_my_company_id()::text);
```

**Critical gotcha**: Using `[1]` in storage policies matches the literal folder name 'entries', not the companyId. Always use `[2]`.

## Migration Workflow

### Creating a Migration

1. `npx supabase migration new add_caption_to_photos`
2. Edit the generated file in `supabase/migrations/`
3. Test locally with `npx supabase db diff`
4. Push with `npx supabase db push`

### Migration File Conventions

```sql
-- Always use IF EXISTS / IF NOT EXISTS for idempotency
ALTER TABLE photos ADD COLUMN IF NOT EXISTS caption TEXT;
CREATE INDEX IF NOT EXISTS idx_photos_caption ON photos(caption);
ALTER TABLE photos ADD CONSTRAINT check_something CHECK (...);
```

### Trigger Idempotency

When creating triggers in migrations, always `DROP TRIGGER IF EXISTS` first:

```sql
DROP TRIGGER IF EXISTS trg_mytable_stamp_deleted_by ON mytable;
CREATE TRIGGER trg_mytable_stamp_deleted_by
  BEFORE UPDATE ON mytable
  FOR EACH ROW EXECUTE FUNCTION stamp_deleted_by();
```

This makes migrations re-runnable without error.

## Sync Engine Architecture

The sync engine is a complete rewrite on branch `feat/sync-engine-rewrite`. All architecture below reflects that branch.

### Layer Stack (top to bottom)

```
SyncProvider (UI)
  → SyncOrchestrator (multi-backend router, retry logic)
    → SyncEngine (core orchestration per project, handles Supabase I/O)
      → SyncRegistry (22 ordered TableAdapters)
        → TableAdapter (push/pull/conflict per table)
```

### Key Engine Components

| Component | File | Purpose |
|-----------|------|---------|
| `SyncEngine` | `engine/sync_engine.dart` | Core push/pull cycle |
| `ChangeTracker` | `engine/change_tracker.dart` | Reads trigger-populated `change_log` |
| `ConflictResolver` | `engine/conflict_resolver.dart` | LWW conflict resolution |
| `SyncMutex` | `engine/sync_mutex.dart` | SQLite advisory lock (single-row sync_lock table) |
| `SyncRegistry` | `engine/sync_registry.dart` | Ordered adapter registry |
| `IntegrityChecker` | `engine/integrity_checker.dart` | Post-sync consistency validation |
| `OrphanScanner` | `engine/orphan_scanner.dart` | Orphan record detection |
| `SyncOrchestrator` | `application/sync_orchestrator.dart` | Retry + multi-backend routing |
| `BackgroundSyncHandler` | `application/background_sync_handler.dart` | Background sync triggers |

### Conflict Resolution (LWW)

Spec Section 3I rules:
1. Both timestamps null → remote wins (safety default)
2. Remote null, local valid → local wins
3. Local null, remote valid → remote wins
4. Remote `updated_at` >= local `updated_at` → remote wins (equal = remote wins)
5. Local `updated_at` strictly > remote → local wins

Conflicts logged to `conflict_log` table. Only column diffs stored (PII mitigation, Decision 8).

### Circuit Breaker

Trips when unprocessed `change_log` entries exceed `SyncEngineConfig.circuitBreakerThreshold`. Auto-purges entries >7 days old with 3+ retries.

### Sync Mutex

Uses single-row `sync_lock` table (id=1). Heartbeat every 60s. Stale after 2 min no heartbeat or 15 min absolute lock age. Prevents concurrent sync across foreground/background isolates.

### Retry Logic

`SyncOrchestrator` retries up to 3 times with exponential backoff (5s, 10s, 20s). After exhaustion, schedules a background retry via `Timer` (60s). Distinguishes transient errors (DNS, SocketException, TimeoutException) from non-transient (auth, RLS, schema errors). Non-transient errors fail immediately.

### Reachability Check

Uses HTTP HEAD to Supabase REST endpoint (not `InternetAddress.lookup()`). Reason: `InternetAddress.lookup()` fails with errno=7 on Android even with working internet.

### Change Log

SQLite triggers on all 16 synced tables populate `change_log` automatically. The ONE exception: when local wins a conflict during pull, `ChangeTracker.insertManualChange()` is called directly (bypasses suppressed triggers).

### Sync Control Suppression

Set `sync_control` flag to suppress triggers during pull or draft operations:

```dart
await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
try {
  // operations that should NOT trigger change_log
} finally {
  await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
}
```

### Sync Buckets (Dashboard Display)

```dart
static const Map<String, List<String>> syncBuckets = {
  'Projects': ['projects', 'bid_items', 'locations', 'todo_items'],
  'Entries': ['daily_entries', 'contractors', 'equipment',
              'entry_contractors', 'entry_equipment',
              'entry_quantities', 'entry_personnel_counts'],
  'Forms': ['inspector_forms', 'form_responses'],
  'Photos': ['photos'],
};
```

## Database Functions

### Auto-Update Timestamp Trigger

```sql
CREATE OR REPLACE FUNCTION update_updated_at() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_timestamp BEFORE UPDATE ON daily_entries
FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

### Soft Delete Stamp Trigger

`stamp_deleted_by()` — SECURITY DEFINER — enforces `auth.uid()` on `deleted_by` column regardless of client-supplied value. Applied to all 16 synced tables.

### Useful RPCs

- `create_company(name)` — creates company, assigns caller as admin
- `search_companies(query)` — full-text company search
- `update_last_synced_at()` — SECURITY DEFINER, updates `last_synced_at` on caller's profile (RLS blocks client-side update)
- `get_table_integrity(table_name)` — post-sync consistency check
- `is_approved_admin()` — helper used in admin-only RLS policies

## Soft Delete System

All 16 synced tables have `deleted_at TIMESTAMPTZ` and `deleted_by UUID` columns.

- Soft-delete: set `deleted_at = NOW()`. Record stays in SQLite for 30-day trash + sync propagation.
- Hard-delete: purged by `purge_soft_deleted_records()` pg_cron job (daily at 03:00 UTC, records older than 30 days).
- Supabase-side: `stamp_deleted_by()` BEFORE UPDATE trigger enforces `auth.uid()` on `deleted_by`.

## Performance Optimization

```sql
-- Partial index for pending sync
-- **DEPRECATED**: `sync_status` columns are no longer used. The sync engine uses `change_log` triggers. This index pattern is historical only.
CREATE INDEX idx_entries_pending ON daily_entries(id) WHERE sync_status = 'pending';

-- Composite index for common queries
CREATE INDEX idx_entries_project_date ON daily_entries(project_id, date DESC);

-- Index for soft-delete filter (every synced table has this)
CREATE INDEX idx_entries_deleted_at ON daily_entries(deleted_at);
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `PGRST205` | Table not found | Check spelling, run migration |
| `23503` | FK violation | Ensure parent record exists locally first |
| `23505` | Unique violation | Check for duplicate IDs |
| `42501` | RLS policy denied | Check policies, verify company_id set |
| `42P01` | Undefined table | Run pending migrations |

## Common Gotchas

- **Mock mode**: Set `MOCK_DATA=true` dart-define to bypass all network calls. `SyncOrchestrator` routes to `MockSyncAdapter` instead of `SyncEngine`.
- **Auth context race**: `SyncOrchestrator._createEngine()` polls up to 15s for companyId/userId before giving up. "No auth context available for sync" is transient (startup race), not a fatal auth failure.
- **Background retry Timer**: Cancel via `_backgroundRetryTimer?.cancel()` when a new sync starts. Guards against `_disposed` flag and validates session before retrying.
- **FK ordering**: `SyncRegistry` defines a specific adapter registration order. Parent tables must sync before children.
- **`last_sync_time` only updates on success**: Previously updated unconditionally, which poisoned staleness detection. Only update after error-free sync.
- **Company data isolation**: `AuthService.clearLocalCompanyData()` wipes all 17 data tables + auth cache on company switch. Must run before loading new company data.
