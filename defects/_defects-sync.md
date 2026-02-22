# Defects: Sync

Active patterns for sync. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [DATA] 2026-02-22: queueOperation() no-op after provider migration
**Pattern**: When migrating `SyncProvider` from `SyncService` to `SyncOrchestrator`, `queueOperation()` body was changed to call `scheduleLocalAgencySync()` without passing any arguments — silently dropping individual record syncs.
**Prevention**: After refactoring provider methods, verify the new call passes ALL original parameters. Test with a round-trip: create record → check sync_queue table → confirm operation queued.
**Ref**: @lib/features/sync/presentation/providers/sync_provider.dart

### [CONFIG] 2026-02-22: Supabase migration assumes table state without verifying
**Pattern**: Writing `ALTER TABLE RENAME COLUMN` or `CREATE INDEX` on columns that may not exist if prior schema SQL was partially applied.
**Prevention**: Always use `DO $$ ... IF EXISTS` conditional blocks for column renames. Use `ADD COLUMN IF NOT EXISTS` for idempotent column additions. Never assume standalone SQL files were applied — verify via `information_schema.columns`.
**Ref**: `supabase/migrations/20260222000000_catchup_v23.sql` (failed twice before fix)

### [CONFIG] 2026-02-22: Supabase schema drift — standalone SQL vs CLI migrations
**Pattern**: Schema SQL files outside `supabase/migrations/` (e.g., `supabase_schema_v3.sql`, `supabase_schema_v4_rls.sql`) may or may not be applied to remote. CLI only tracks files in `migrations/`.
**Prevention**: All schema changes must be in `supabase/migrations/` with timestamp prefix. Never use standalone SQL files for production schema changes.

<!-- Add defects above this line -->
