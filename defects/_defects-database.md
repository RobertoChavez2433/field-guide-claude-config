# Database Defects

## Active Patterns

### [DATA] 2026-02-22: Migration ordering — index before column addition
**Pattern**: v24 migration created `idx_projects_company ON projects(company_id)` BEFORE the `ALTER TABLE ADD COLUMN company_id` ran, causing `SqliteException: no such column`.
**Prevention**: Always place `_addColumnIfNotExists` calls BEFORE any `CREATE INDEX` that references the new column. Review migration blocks for column-then-index ordering.
**Ref**: @lib/core/database/database_service.dart (oldVersion < 24 block)

### [DATA] 2026-02-22: Shared singleton DB causes flaky test lock contention
**Pattern**: Multiple test files using the production `DatabaseService()` singleton share a single on-disk SQLite file. When one file's "Close and Reopen" test triggers re-init, the WAL lock blocks concurrent INSERTs in other files → `SqliteException(5): database is locked`.
**Prevention**: Use `DatabaseService.forTesting()` (in-memory DB) for test files that don't specifically test the production DB lifecycle. Only `database_service_test.dart` should use the production singleton.
**Ref**: @test/core/database/extraction_schema_migration_test.dart, @test/core/database/database_service_test.dart
