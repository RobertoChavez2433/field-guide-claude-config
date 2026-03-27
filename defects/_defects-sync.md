# Defects: Sync

Active patterns for sync. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [CONFIG] 2026-03-27: Seeded data invisible without project_assignments
**Pattern**: Inserting bid_items directly into Supabase is not enough for sync. The sync engine requires a `project_assignments` row for the user to enroll the project into `synced_projects`. Without it, `_syncedProjectIds` is empty and all `viaProject` adapters skip the project entirely.
**Prevention**: When seeding project data in Supabase, always create a `project_assignments` row for target users. The enrollment chain is: `project_assignments` pull → `_enrollProjectsFromAssignments()` → `synced_projects` → child adapters pull.
**Ref**: `lib/features/sync/engine/sync_engine.dart:1644` (`inFilter('project_id', _syncedProjectIds)`)

### [CONFIG] 2026-03-27: enforce_created_by trigger nullifies service role inserts
**Pattern**: `enforce_created_by()` trigger stamps `created_by_user_id = auth.uid()`. When using service role key, `auth.uid()` returns NULL, so all inserted rows have `created_by_user_id = NULL` — even if explicitly set in the INSERT. This can break FK constraints and RLS visibility.
**Prevention**: For seeding, authenticate as a real user via OTP flow (`admin.generateLink` + `verifyOtp`) rather than using the service role key directly.
**Ref**: `supabase/migrations/20260222100000_multi_tenant_foundation.sql:358`

### [CONFIG] 2026-03-27: RAISE LOG not captured in Supabase Cloud production
**Pattern**: `cascade_project_soft_delete` and `admin_soft_delete_project` use `RAISE LOG` for audit events. Supabase Cloud's default log level is `WARNING` — `LOG` events are silently discarded in production.
**Prevention**: Use `RAISE NOTICE` or insert into an `audit_log` table for production-visible audit trails.
**Ref**: @supabase/migrations/20260326200001_fix_cascade_entry_personnel.sql:113

### [DATA] 2026-03-26: Schema divergence — project_assignments missing audit/soft-delete columns
**Pattern**: `project_assignments` was created without `created_by_user_id`, `deleted_at`, `deleted_by` — the only table out of 17 missing these. Sync engine stamps `created_by_user_id` unconditionally on ALL payloads, causing PGRST204 rejection. Also `entry_personnel_counts` missing `created_at` on Supabase. Schema verifier missing entries for infrastructure tables.
**Prevention**: When adding a new synced table, cross-reference against the standard column template (created_by_user_id, deleted_at, deleted_by, created_at, updated_at). Add to schema_verifier.dart expectedSchema. Add to purge_soft_deleted_records(). Run column-level audit before first sync test.
**Ref**: @.claude/plans/2026-03-26-schema-divergence-fix.md

### [CONFIG] 2026-03-26: Projects SELECT RLS policy too broad — inspector sees all company projects (BUG-4, SECURITY)
**Pattern**: Original `company_projects_select` policy only checked `company_id = get_my_company_id()`, granting every company member SELECT on all company projects. Inspector could pull projects they weren't assigned to. The `20260319200000_tighten_project_rls.sql` migration tightened INSERT/UPDATE/DELETE but deliberately skipped SELECT.
**Prevention**: When writing RLS policies for role-gated resources, always include an assignment/membership check for non-admin roles on SELECT. Don't assume SELECT is safe just because write policies are locked down.
**Ref**: @supabase/migrations/20260326000000_tighten_project_select_rls.sql

### [FLUTTER] 2026-03-25: DeletionNotificationBanner raw SQL in presentation layer
**Pattern**: Widget directly calls `db.query()` and `db.update()` against `deletion_notifications` table — violates architecture rule (no raw SQL in presentation).
**Prevention**: Always route DB access through a repository. Pre-existing tech debt — flagged with TODO, not introduced by integrity verification plan.
**Ref**: @lib/features/sync/presentation/widgets/deletion_notification_banner.dart

### [BUG] 2026-03-24: Sync engine crashes on server-side hard-deleted records
**Pattern**: When records exist in local SQLite but have been hard-deleted from Supabase (not soft-deleted), the sync engine fails and puts the app into a permanent "offline" state. App requires Settings > Clear Data to recover. Discovered when test cleanup hard-deleted SYNCTEST-* projects from Supabase — the phone app that had synced them could no longer sync at all.
**Root cause**: Sync engine doesn't handle the case where local records reference server records that no longer exist. Likely the push path tries to push a change for a record the server rejects, or the pull path encounters an inconsistency it can't resolve.
**Impact**: Any server-side hard-delete (admin purge, data migration, etc.) can brick the app for affected users.
**Fix needed**: Sync engine must detect orphaned local records (exist locally but not on server) and purge them gracefully instead of crashing. Consider adding an orphan-detection pass to the pull cycle.
**Ref**: Discovered in S635 during sync verification testing.

### [CONFIG] 2026-03-23: Sync verification scenarios use assumed names instead of actual codebase values
**Pattern**: All 94 L2/L3 scenarios hardcode route paths (`/projects/create`), widget keys (`save_project_button`), and API names that don't exist in the app. Passed 14 review sweeps because reviews checked internal consistency (spec ↔ plan) but never cross-referenced against live code (`app_router.dart`, `testing_keys/*.dart`).
**Prevention**: Ground Truth Verification added to writing-plans skill. Every string literal in plan code must be looked up against the actual source of truth before approval.
**Ref**: `tools/debug-server/scenarios/L2/*.js`, `.claude/skills/writing-plans/skill.md`

## Recently Fixed (Session 614)

### BUG-A: _pushDelete missing server timestamp writeback (Session 613→614)
**Fix**: Added `.select('updated_at, deleted_by')` + writeback with `pulling='1'` suppression. Added `conflicts`/`skippedFk` to `SyncEngineResult`. Verified via H001-H005 hypothesis markers.

### BUG-17: Re-login wipes all data (Session 608→610)
**Fix**: Removed `clearLocalCompanyData` from logout. Added company-switch guard in `signIn()`. Auto-enrollment via `_enrollProjectsFromAssignments()`.

### BUG-15: Integrity RPC cascade failure (Session 608→610)
**Fix**: Migration `20260320000003` added `entry_contractors` to allowlist, switched to `RETURNS TABLE`, fixed alias bug.

### BUG-006: Stale _isOnline flag (Session 591→610)
**Fix**: `checkDnsReachability()` called before every `isSupabaseOnline` read in `project_list_screen.dart` + defense-in-depth inside `_syncWithRetry()`.

### BUG-005: synced_projects enrollment gap (Session 591→610)
**Fix**: `_enrollProjectsFromAssignments()` runs unconditionally after `project_assignments` pull. Fresh-restore cursor guard. Orphan cleaner deadlock prevention via `_projectsAdapterCompleted`.

<!-- Add defects above this line -->
