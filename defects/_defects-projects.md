# Defects: Projects

Active patterns for projects. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

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

### [TEST] 2026-03-03: create-project flow — Save button does not auto-navigate back (auto-test)
**Status**: OPEN
**Source**: Automated test run 2026-03-03-1933-run.md
**Symptom**: On the New Project screen, tapping Save while a text field is focused and the keyboard is open triggers the DB insert (confirmed via flutter log: `INSERT projects id=b56304be`) but the screen does not pop off the navigation stack. The form remains open showing the entered data. Tapping Save a second time after keyboard is dismissed also does not navigate back — only tapping the Back button returns to the project list. The project itself is created correctly; this is purely a navigation UX bug.
**Logcat**: `I flutter : [DB] [19:37:15.990] INSERT projects id=b56304be-1d2d-4861-97ae-758ea794eceb` — insert succeeded; no navigation event followed.
**Screenshot**: .claude/test-results/2026-03-03-1933-run/screenshots/create-project-step7.png (form still open after Save)
**Suggested cause**: The save handler likely calls `Navigator.pop()` or uses GoRouter to navigate back, but if the keyboard is open and the field still has focus, the navigation event may be swallowed or the keyboard dismissal is consuming the back gesture. Alternatively, the save callback may be returning early on a validation path when focus is active. Check the onPressed handler for the Save button in the project editor screen — confirm Navigator.pop/GoRouter.pop is called unconditionally after successful save.

<!-- Add defects above this line -->
