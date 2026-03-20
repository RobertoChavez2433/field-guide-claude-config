# Defects: Projects

Active patterns for projects. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [FLUTTER] 2026-03-18: canWrite=true for inspector — root cause of 10 permission gaps — BUG-008 (Session 591)
**Pattern**: `UserRole.canWrite` returns `true` for ALL roles including inspector. This property gates 102 call sites across 24 files (edit pencil, archive toggle, add location/contractor/pay item buttons). Inspector has full write access everywhere. Additionally, no route guards on `/project/new` or `/project/:id/edit` (BUG-007), and dashboard Contractors card deep-links into unguarded edit screen (BUG-011).
**Prevention**: Replace `canWrite` with granular permissions (`canEditProject`, `canArchiveProject`, `canManageSetup`). Add route guards in `app_router.dart` redirect function. Gate setup screen tabs behind role checks.
**Ref**: @lib/features/auth/data/models/user_role.dart:36, @lib/core/router/app_router.dart:428-444, @lib/features/projects/presentation/screens/project_list_screen.dart:740,762

### [CONFIG] 2026-03-17: SyncOrchestrator not registered as Provider — crashes project management (Session 585)
**Pattern**: `project_list_screen.dart` calls `context.read<SyncOrchestrator>()` in 3 places (network check, import, delete sheet) but `SyncOrchestrator` was never added to the MultiProvider tree in `main.dart`. Every project management action crashes with `ProviderNotFoundException`. The orchestrator was passed to `SyncProvider` constructor but never registered as its own Provider.
**Prevention**: When a widget calls `context.read<T>()`, verify `T` is registered in the MultiProvider tree. Search `main.dart` for `Provider<T>` before using `context.read<T>()` in any screen.
**Ref**: @lib/main.dart (missing), @lib/features/projects/presentation/screens/project_list_screen.dart:52,85,114

### [DATA] 2026-03-17: Background sync auto-enrolls ALL company projects defeating selective import (Session 585)
**Pattern**: BLOCKER-38 fix in `_pullTable()` auto-enrolled every pulled project into `synced_projects`. Since ProjectAdapter uses `ScopeType.direct` (pulls ALL company projects), every background sync enrolled everything, causing all child data to download. This defeats the Import-based UX where users choose which projects to download.
**Prevention**: `synced_projects` INSERT should ONLY happen via explicit user action (download confirmation, project creation, manual toggle). Never auto-enroll in the sync engine's pull path.
**Ref**: @lib/features/sync/engine/sync_engine.dart:1082-1088

### [DATA] 2026-03-19: App kill during project creation leaves orphaned empty project record (Session 600)
**Pattern**: If the app is killed (force-close, crash, OS reclaim) while the user is on the project creation screen, a project record with no name/number gets persisted to SQLite. This happens because the project row is eagerly inserted (to satisfy FK constraints for child tabs) but the user never completed the form or tapped Save. On next launch the ghost project appears in the project list with blank name and number.
**Symptom**: Project list shows a card with no name, no project number, just "No client" and "Today".
**Prevention**: On app startup, scan for projects with NULL/empty name and delete them (cleanup service). Or: mark eagerly-inserted records with a `draft` status and filter them from the project list query until explicitly saved.
**Ref**: @lib/features/projects/presentation/screens/project_setup_screen.dart:66

### [DATA] 2026-03-06: Pre-generated project UUID causes FK violations for child records (Session 507)
**Pattern**: `project_setup_screen.dart:66` generates `_projectId = Uuid().v4()` but doesn't INSERT project row until Save. Child records (bid_items, locations, contractors) added via tabs reference this ID and fail FK check against `projects(id)` since `PRAGMA foreign_keys=ON`.
**Prevention**: Eagerly INSERT a minimal project row when UUID is generated. Use `repository.save()` (bypasses duplicate check). `StartupCleanupService` handles orphaned drafts. Don't enroll draft in `synced_projects` until Save.
**Ref**: @lib/features/projects/presentation/screens/project_setup_screen.dart:66

### [DATA] 2026-03-06: v30 migration SELECTs non-existent columns from old table (Session 507)
**Pattern**: `entry_personnel_counts` rebuild tried to SELECT `project_id`, `created_at`, `updated_at`, `created_by_user_id` from old table that only had `id, entry_id, contractor_id, type_id, count, deleted_at, deleted_by`. Crashed app on startup.
**Prevention**: Before writing INSERT...SELECT migrations, verify source table columns with `PRAGMA table_info` or by tracing which migrations added which columns. Only SELECT columns that exist.
**Ref**: @lib/core/database/database_service.dart:1236-1244 (FIXED)

### [DATA] 2026-03-02: Auth cold-start race — loadProjectsByCompany(null) empties project list
**Pattern**: `ProjectProvider` is created inside `ChangeNotifierProvider.create` which runs during widget build.
At that instant `authProvider.userProfile?.companyId` may be null because `AuthProvider.loadUserProfile()` is async and hasn't resolved yet.
`loadProjectsByCompany(null)` has an explicit early-return guard that sets `_projects = []`.
No listener was wired to re-run `loadProjectsByCompany` when the profile loaded, so the empty list persisted for the whole session.
The duplicate-check query in `ProjectRepository.create()` uses `project.companyId` from the model (filled at form time), not from the provider — so it finds the record while the display query shows empty.
**Symptom**: Home screen shows no projects / "no projects" state. Attempting to create with same project number says "already exists".
**Prevention**: After the initial `loadProjectsByCompany(initialCompanyId)` call, add an `authProvider.addListener` that re-runs `loadProjectsByCompany(newCompanyId)` when `companyId` changes from null to a real value. Use a closure-captured `lastLoadedCompanyId` variable to avoid redundant reloads on unrelated auth events.
**Fix**: `lib/main.dart` — `loadAndRestore` helper + `onAuthChanged` listener in `ProjectProvider.create` block.

### [DATA] 2026-03-03: PRAGMA foreign_keys never enabled — ON DELETE CASCADE is dead code
**Pattern**: All schema tables define `FOREIGN KEY ... ON DELETE CASCADE` (e.g. `daily_entries → projects`, `bid_items → projects`), but `PRAGMA foreign_keys = ON` is never set in `database_service.dart`. SQLite requires this pragma to enforce FKs. As a result, deleting a project via `ProjectRepository.delete()` leaves ALL child rows (bid_items, daily_entries, locations, contractors, entry_quantities, etc.) as orphaned records. The project row is deleted but child data leaks indefinitely.
**Prevention**: Add `PRAGMA foreign_keys = ON` in the `onConfigure` callback (already used for WAL mode). Since it must be set on every connection, `onConfigure` is the correct location.
**Fix**: In `database_service.dart:57` `onConfigure` block, add `await db.rawQuery('PRAGMA foreign_keys=ON')` alongside the WAL pragma.
**Ref**: @lib/core/database/database_service.dart:56-62, @lib/features/projects/data/datasources/local/project_local_datasource.dart:112

### [SYNC] 2026-03-03: SQLite missing UNIQUE constraint on project_number — sync race condition
**Status**: OPEN — BLOCKER-24
**Pattern**: Supabase enforces `UNIQUE(company_id, project_number)` but SQLite has NO such constraint. `ProjectRepository.create()` does a soft check-then-insert (query for duplicate, then insert) which is a classic TOCTOU race. If Save is tapped twice quickly, or sync triggers concurrently, duplicate projects can be created locally. They succeed in SQLite but fail on Supabase sync with unique constraint violation.
**Symptom**: User creates a project, sees "project already exists" error on save — or project appears to be created twice. Sync may fail silently for the duplicate.
**Prevention**: Add `CREATE UNIQUE INDEX idx_project_number_company ON projects(company_id, project_number)` to SQLite schema. Bump DB version. Add migration for existing installs. Consider also adding `sync_status` column to projects (entries have it, projects don't).
**Fix**: `lib/core/database/schema/core_tables.dart` (add index), `lib/core/database/database_service.dart` (migration)
**Ref**: @lib/core/database/schema/core_tables.dart:6-27, @lib/features/projects/data/repositories/project_repository.dart:64-78

<!-- Add defects above this line -->
