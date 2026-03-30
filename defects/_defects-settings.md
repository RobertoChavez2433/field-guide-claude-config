# Defects: Settings

Active patterns for settings. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

<!-- RESOLVED 2026-03-30 BUG-S09-1: Trash screen must scope queries by role and ownership — Fixed in S667. Non-admin queries filter by deleted_by = currentUserId; inspector role excluded from project-level tables. Ref: lib/features/settings/presentation/screens/trash_screen.dart:56 -->

### [CONFIG] 2026-03-27: MANAGE_EXTERNAL_STORAGE prompts on every app launch
**Pattern**: `_ensureLogDirectoryWritable()` in `main.dart` requested `Permission.manageExternalStorage` but that permission was never declared in `AndroidManifest.xml`. Android always reported it as `denied`, so the request dialog fired on every launch. Additionally, `_initDebugLogging` opened a `FilePicker.getDirectoryPath()` dialog on mobile when no saved log dir existed.
**Prevention**: Never request permissions not declared in AndroidManifest.xml. On mobile, use app-specific directories (`getApplicationDocumentsDirectory`) instead of requesting dangerous storage permissions. File logging should silently fall back to app-specific dirs.
**Ref**: `lib/main.dart:621-631`, `android/app/src/main/AndroidManifest.xml`

### [CONFIG] 2026-03-18: get_pending_requests_with_profiles RPC varchar/text type mismatch (Session 588)
**Pattern**: `auth.users.email` is `character varying` but the RPC `RETURNS TABLE` declares `email TEXT`. PostgreSQL rejects the mismatch: "Returned type character varying does not match expected type text in column 10." Same risk for any column sourced from `auth.users` or tables with `varchar` columns.
**Prevention**: Always cast columns from external tables (especially `auth.users`) to match the declared return type: `COALESCE(au.email, '')::TEXT`. Apply `::TEXT` casts proactively on all `RETURNS TABLE` RPC columns.
**Ref**: @supabase/migrations/20260313100001_pending_requests_rpc.sql:16

### [CONFIG] 2026-03-18: OrphanScanner references photos.company_id which doesn't exist (Session 588)
**Pattern**: OrphanScanner query uses `photos.company_id` but the `photos` table has no `company_id` column. Needs to join through `daily_entries` or `projects` to resolve company scope.
**Prevention**: Before writing Supabase queries that reference columns, verify the column exists on the target table. Photos are scoped via `entry_id → daily_entries.project_id → projects.company_id`.
**Ref**: OrphanScanner scan — PostgrestException code 42703

<!-- Add defects above this line -->
