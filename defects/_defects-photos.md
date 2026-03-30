# Defects: Photos

Active patterns for photos. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [DATA] 2026-03-28: photos.file_path must be nullable in SQLite for cross-device sync (BUG-S03-1)
**Pattern**: Local SQLite had `file_path TEXT NOT NULL` but Supabase had it nullable. Photos pushed without file_path (device-local, stripped via localOnlyColumns). On pull, NULL file_path violated NOT NULL constraint, `ConflictAlgorithm.ignore` silently dropped the record. Every cross-device photo pull failed.
**Prevention**: When a column is device-local (stripped on push via localOnlyColumns), the local schema MUST make it nullable. Otherwise pulled records will be silently rejected. Fixed in v42 migration (S667).
**Ref**: @lib/core/database/schema/photo_tables.dart:11

### [ASYNC] 2026-03-20: TextEditingController used after disposed in photo detail dialog — BUG-9 (Session 608)
**Pattern**: Photo detail dialog controllers are disposed when dialog closes, but async callbacks still reference them. Also triggers `_dependents.isEmpty` assertion failure.
**Prevention**: Check `mounted` before accessing controllers in async callbacks. Cancel pending async work in `dispose()`.
**Ref**: @lib/features/entries/presentation/widgets/photo_detail_dialog.dart

### [E2E] 2026-03-20: inject-photo-direct creates records without file_path — BUG-14 (Session 608)
**Pattern**: `inject-photo-direct` endpoint creates photo records with null `file_path`. Supabase `photos` table has NOT NULL on `file_path`, so injected photos never sync.
**Prevention**: Set a placeholder file_path when creating injected records, or make `file_path` nullable in Supabase.
**Ref**: @lib/core/driver/driver_server.dart

<!-- Add defects above this line -->
