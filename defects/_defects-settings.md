# Defects: Settings

Active patterns for settings. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [CONFIG] 2026-03-18: get_pending_requests_with_profiles RPC varchar/text type mismatch (Session 588)
**Pattern**: `auth.users.email` is `character varying` but the RPC `RETURNS TABLE` declares `email TEXT`. PostgreSQL rejects the mismatch: "Returned type character varying does not match expected type text in column 10." Same risk for any column sourced from `auth.users` or tables with `varchar` columns.
**Prevention**: Always cast columns from external tables (especially `auth.users`) to match the declared return type: `COALESCE(au.email, '')::TEXT`. Apply `::TEXT` casts proactively on all `RETURNS TABLE` RPC columns.
**Ref**: @supabase/migrations/20260313100001_pending_requests_rpc.sql:16

### [CONFIG] 2026-03-18: OrphanScanner references photos.company_id which doesn't exist (Session 588)
**Pattern**: OrphanScanner query uses `photos.company_id` but the `photos` table has no `company_id` column. Needs to join through `daily_entries` or `projects` to resolve company scope.
**Prevention**: Before writing Supabase queries that reference columns, verify the column exists on the target table. Photos are scoped via `entry_id → daily_entries.project_id → projects.company_id`.
**Ref**: OrphanScanner scan — PostgrestException code 42703

<!-- Add defects above this line -->
