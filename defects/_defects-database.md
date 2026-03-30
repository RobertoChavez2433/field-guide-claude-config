# Database Defects

## Active Patterns

### [CONFIG] 2026-03-29: Supabase migration used UUID for app table PKs/FKs — remote schema uses TEXT
**Pattern**: New table CREATE statements used `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` and `UUID REFERENCES` for FK columns, but all existing app tables use `TEXT PRIMARY KEY` with app-generated UUIDs. Only `created_by_user_id`/`deleted_by` are UUID (reference `auth.users`).
**Prevention**: Always check existing table id types before writing new CREATE TABLE migrations. App tables = TEXT PKs. Auth references = UUID.
**Ref**: @supabase/migrations/20260328100000_fix_inspector_forms_and_new_tables.sql

<!-- RESOLVED 2026-03-30: BackgroundSyncHandler.close() closes singleton DB on mobile isolate exit — close() call no longer exists in the code. Ref: lib/features/sync/application/background_sync_handler.dart -->

### [CONFIG] 2026-02-22: Supabase RLS policies assumed columns that don't exist
**Pattern**: Multi-tenant migration wrote one-hop `project_id` RLS policies for `entry_quantities` and `equipment`, but those tables have no `project_id` column. `entry_quantities` joins via `entry_id → daily_entries`, `equipment` joins via `contractor_id → contractors`.
**Prevention**: Before writing RLS policies, verify the actual table schema (check CREATE TABLE in migrations or SQLite schema files). Use two-hop subqueries for junction tables without direct FK to projects.
**Ref**: @supabase/migrations/20260222100000_multi_tenant_foundation.sql (Parts 7E, 7H)

### [CONFIG] 2026-02-22: Catch-up migration created updated_at triggers on tables without updated_at column
**Pattern**: `update_*_updated_at` triggers reference `NEW.updated_at`, but tables like `bid_items`, `personnel_types` didn't have `updated_at` in the original Supabase baseline. Trigger fires on any UPDATE (including backfill) and crashes.
**Prevention**: Always add `ALTER TABLE ADD COLUMN IF NOT EXISTS updated_at` BEFORE creating `BEFORE UPDATE` triggers that reference `NEW.updated_at`. Or add safety columns at the top of dependent migrations.
**Ref**: @supabase/migrations/20260222100000_multi_tenant_foundation.sql (Part 10C)

### [DATA] 2026-02-22: Migration ordering — index before column addition
**Pattern**: v24 migration created `idx_projects_company ON projects(company_id)` BEFORE the `ALTER TABLE ADD COLUMN company_id` ran, causing `SqliteException: no such column`.
**Prevention**: Always place `_addColumnIfNotExists` calls BEFORE any `CREATE INDEX` that references the new column. Review migration blocks for column-then-index ordering.
**Ref**: @lib/core/database/database_service.dart (oldVersion < 24 block)

### [DATA] 2026-02-22: Shared singleton DB causes flaky test lock contention
**Pattern**: Multiple test files using the production `DatabaseService()` singleton share a single on-disk SQLite file. When one file's "Close and Reopen" test triggers re-init, the WAL lock blocks concurrent INSERTs in other files → `SqliteException(5): database is locked`.
**Prevention**: Use `DatabaseService.forTesting()` (in-memory DB) for test files that don't specifically test the production DB lifecycle. Only `database_service_test.dart` should use the production singleton.
**Ref**: @test/core/database/extraction_schema_migration_test.dart, @test/core/database/database_service_test.dart
