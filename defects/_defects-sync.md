### [MIGRATION] 2026-04-06: New sync adapters need live remote schema proof before acceptance
**Pattern**: Adding local SQLite schema, sync adapters, and tests for new tables is not enough to claim sync readiness if the target Supabase environment has not applied the matching migration yet.
**Prevention**: Before device-level sync acceptance, verify the live backend exposes the new tables, storage buckets, and policies required by the adapter registration. Treat missing remote schema as a release blocker, not a runtime surprise.
**Ref**: @supabase/migrations/20260406095500_add_pay_app_export_artifacts.sql

### [CONFIG] 2026-04-06: Android native verification can fail from deep Windows worktree paths
**Pattern**: `flusseract`/CMake native builds resolve the real checkout path, so a deep Windows worktree can fail before the app starts even if a drive alias or junction exists.
**Prevention**: Use a short real checkout path for Android/native verification work. Do not rely on a drive alias alone when native build tooling is path-sensitive.
**Ref**: @tools/build.ps1

### [SYNC] 2026-04-06: File-backed sync verification must prove local DB, queue, cloud row, and storage together
**Pattern**: UI-only verification can miss cases where file metadata syncs but the storage object, local cache path, or `change_log` state is wrong.
**Prevention**: Every file-backed sync flow must verify the UI result, SQLite row, `change_log`, Supabase row, and storage object together, especially for destructive and retry/restart paths.
**Ref**: @lib/features/sync/engine/pull_handler.dart
