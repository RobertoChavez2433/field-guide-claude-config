# Consolidated Implementation Plan: Pre-PR Fixes for Sync Engine Rewrite

**Created**: 2026-03-06
**Status**: BRAINSTORMED — decisions locked
**Branch**: `feat/sync-engine-rewrite`
**Sources**: Merged from `2026-03-06-critical-fixes.md` + `2026-03-06-data-layer-fixes.md`

---

## Executive Summary

Seven workstreams must be completed before the `feat/sync-engine-rewrite` PR is merged to main. Four are critical sync/data fixes discovered during device testing. Two are cleanup workstreams. One is already implemented.

| # | Workstream | Severity | Source |
|---|-----------|----------|--------|
| WS1 | Register sync adapters in production | CRITICAL | Fix 2B + data-layer WS1 (merged) |
| WS2 | Fix sync pull scoping + project list UX | CRITICAL | Fix 2A + brainstorm decisions |
| WS3 | Populate `companies` table locally | CRITICAL | Fix 1 |
| WS4 | Eager project row INSERT | CRITICAL | Fix 3 |
| WS5 | Deprecate `entry_personnel` table (5 phases) | MEDIUM | data-layer WS2 |
| WS6 | Permissions UX (role-based ViewOnlyBanner) | LOW | data-layer WS3 |
| WS7 | Android permissions dialog auto-advance | FIXED | Already done this session |

Current DB version: **31**. Final after all workstreams: **33**.

---

## Key Design Decisions (Brainstormed & Locked)

These decisions were made during a structured brainstorm and override all prior plan assumptions.

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Project data source on first login | **Hybrid**: local first, Supabase fallback if empty+online | Works offline after first load |
| Load behavior when tapping company project | **Confirm dialog → immediate load + background sync** | User stays in control, no blocking wait |
| Project list layout | **Two sections with headers**: "My Projects" + "Company Projects" | Clear visual distinction |
| Project metadata sync | **Pull ALL company project metadata automatically** (ScopeType.direct) | "Company Projects" section always populated |
| Child data sync | **Only for projects in `synced_projects`** (user must explicitly load) | Prevents downloading 2 years of data |
| Loaded vs unloaded distinction | **`synced_projects` table** (existing design) | No schema change needed |
| Auto-enrollment | **NO auto-enrollment of pulled projects**. Only locally-created projects and explicitly-loaded projects get enrolled | User controls data footprint |

### Resulting Sync Scoping Model

```
SyncEngine pulls:
  projects table     → ALL company projects (ScopeType.direct, company_id filter)
  locations table    → ONLY synced_projects (ScopeType.viaProject)
  daily_entries      → ONLY synced_projects
  photos             → ONLY synced_projects (ScopeType.viaEntry)
  bid_items          → ONLY synced_projects
  contractors        → ONLY synced_projects
  equipment          → ONLY synced_projects (ScopeType.viaContractor)
  ... all other child tables scoped to synced_projects

Project List Screen:
  MY PROJECTS     = projects WHERE id IN (SELECT project_id FROM synced_projects)
  COMPANY PROJECTS = projects WHERE id NOT IN (SELECT project_id FROM synced_projects)
                     (section hidden if offline or all projects already loaded)
```

### User Flows

**New user at existing company:**
```
Login → Dashboard → "View Projects" → Project List Screen
  ├── MY PROJECTS: (empty)
  ├── COMPANY PROJECTS: (fetched from Supabase or local after first sync)
  │   └── Tap "Springfield DWSRF" → Confirm dialog → Load Project
  │       1. Insert project metadata locally (if not already synced)
  │       2. Insert into synced_projects
  │       3. Navigate to project dashboard
  │       4. Background sync pulls child data (entries, photos, etc.)
  └── [+] Create New Project
```

**Returning user on new device:**
Same flow — local DB is empty, first sync pulls all project metadata, user selects which to load.

**New user at new company:**
```
Login → Dashboard → "View Projects" → Project List Screen
  ├── MY PROJECTS: (empty)
  ├── COMPANY PROJECTS: (empty — no projects exist yet)
  └── [+] Create New Project → auto-enrolled in synced_projects
```

---

## Prior Adversarial Review Findings (Incorporated)

| ID | Severity | Issue | Resolution |
|----|----------|-------|------------|
| AR-1 | CRITICAL | `.inFilter()` with empty contractor list crashes Supabase | Fixed in WS2: separate skip guards per scope type |
| AR-3 | CRITICAL | Auto-enrollment enrolls draft projects | **Resolved by design**: NO auto-enrollment. User explicitly loads projects. |
| AR-5 | HIGH | `Company.toMap()` includes column absent from local table | Fixed in WS3: add `created_by_user_id` column to local schema |
| AR-6 | HIGH | Incomplete EntryPersonnel removal targets in controller | Fixed in WS5 Phase 5.3: explicit removal list |
| AR-7 | HIGH | Enrollment runs on every project edit | Fixed in WS2: gate to new projects only |
| C1 | CRITICAL | pdf_data_builder missing PersonnelTypeProvider | Fixed in WS5 Phase 5.3 |
| C2 | CRITICAL | Variable shadowing in pdf_data_builder loop | Fixed in WS5 Phase 5.3 |
| H3 | HIGH | controller loadForEntry references not removed | Fixed in WS5 Phase 5.3 |
| H4 | HIGH | No transaction wrapper on v32 backfill | Fixed in WS5 Phase 5.1 |
| H5 | HIGH | N+1 query in backfill | Fixed in WS5 Phase 5.1 |
| M1 | MEDIUM | BaseListProvider._error is file-private | Fixed in WS6 Task A |

---

## Dependency Chain & Execution Order

```
WS1 (register adapters)          ──── MUST be first; all sync depends on it
  │
  ├── WS2 (fix pull scoping + project list UX)
  │     │
  │     └── WS3 (companies FK)   ──── enables user_profiles sync
  │
  └── WS4 (eager project INSERT) ──── independent, can parallel with WS2/WS3

WS5 (entry_personnel deprecation) ── AFTER WS1-WS4
  Phase 5.1 → 5.2 → 5.3 → 5.4 → 5.5 (strictly sequential)

WS6 (permissions UX)              ── AFTER WS5
WS7 (permissions dialog)          ── ALREADY DONE
```

---

## WS1: Register Sync Adapters in Production

**Agent**: `backend-data-layer-agent`
**Risk**: LOW — purely additive
**Files**: 3

### Root Cause

`SyncRegistry.registerAdapters()` (sync_registry.dart:26) only called in test code. Production adapter list is empty. Push/pull loops iterate 0 adapters silently. Background sync runs in a separate Dart isolate — singletons not shared.

### Changes

**File 1: `lib/features/sync/engine/sync_registry.dart`**

Add 16 adapter imports. Add top-level function after class:

```dart
/// Register all 16 table adapters in FK dependency order.
/// Called from both foreground (SyncOrchestrator) and background
/// (backgroundSyncCallback) initialization paths.
/// Safe to call multiple times — clears and re-registers.
void registerSyncAdapters() {
  SyncRegistry.instance.registerAdapters([
    ProjectAdapter(), LocationAdapter(), ContractorAdapter(),
    EquipmentAdapter(), BidItemAdapter(), PersonnelTypeAdapter(),
    DailyEntryAdapter(), PhotoAdapter(), EntryEquipmentAdapter(),
    EntryQuantitiesAdapter(), EntryContractorsAdapter(),
    EntryPersonnelCountsAdapter(), InspectorFormAdapter(),
    FormResponseAdapter(), TodoItemAdapter(), CalculationHistoryAdapter(),
  ]);
}
```

**File 2: `lib/features/sync/application/sync_orchestrator.dart`**

In `initialize()`, after mock-adapter block (~line 107):
```dart
if (!_isMockMode) {
  registerSyncAdapters();
  DebugLogger.sync('Registered ${SyncRegistry.instance.adapters.length} adapters');
}
```

**File 3: `lib/features/sync/application/background_sync_handler.dart`**

In `backgroundSyncCallback()`, after Supabase init (~line 38):
```dart
registerSyncAdapters(); // Isolates don't share static state
```

### Verification
- [ ] `flutter analyze` — 0 issues
- [ ] `flutter test test/features/sync/` — all pass
- [ ] Manual: trigger sync → adapter count logged > 0

---

## WS2: Fix Sync Pull Scoping + Project List UX

**Agent**: `backend-data-layer-agent` + `frontend-flutter-specialist-agent`
**Risk**: MEDIUM — changes sync behavior + UI
**Files**: 3
**Depends on**: WS1

### Root Cause

1. `sync_engine.dart:616-618` early-returns when `_syncedProjectIds` is empty, blocking ALL adapters including `ProjectAdapter` (ScopeType.direct) which should always pull company project metadata.
2. Project list screen only shows local projects. No way to discover or load company projects from Supabase.

### Changes

**File 1: `lib/features/sync/engine/sync_engine.dart`**

Remove the 3-line blanket early-return (lines 616-618). Replace with per-adapter skip logic inside the pull loop. **[AR-1 FIX]**: Separate guards for each scope type to prevent `.inFilter([])` crash:

```dart
// Inside the for (final adapter in _registry.adapters) loop, before _pullTable:

// ScopeType.direct (e.g. projects) — always runs, uses company_id filter
if (adapter.scopeType == ScopeType.direct) {
  // No skip — always pull
} else if (_syncedProjectIds.isEmpty) {
  // No loaded projects — skip all project-scoped adapters
  DebugLogger.sync('Pull skip (no loaded projects): ${adapter.tableName}');
  continue;
} else if (adapter.scopeType == ScopeType.viaContractor &&
           _syncedContractorIds.isEmpty) {
  // Have projects but no contractors yet — skip equipment
  DebugLogger.sync('Pull skip (no contractors): ${adapter.tableName}');
  continue;
}
```

**NO auto-enrollment of pulled projects.** The projects adapter pulls metadata only. Projects land in local `projects` table but NOT in `synced_projects`. They appear in the "Company Projects" section of the project list. User must explicitly load them.

**File 2: `lib/features/projects/presentation/screens/project_list_screen.dart`**

Modify to show two sections: "My Projects" and "Company Projects".

**My Projects** = local projects where `id IN synced_projects`:
```dart
// Query from ProjectProvider (already loaded from local DB)
final myProjects = provider.projects.where((p) =>
  syncedProjectIds.contains(p.id)).toList();
```

**Company Projects** = local projects where `id NOT IN synced_projects`:
```dart
final companyProjects = provider.projects.where((p) =>
  !syncedProjectIds.contains(p.id)).toList();
```

Load `syncedProjectIds` from the database at screen init:
```dart
final db = await DatabaseService().database;
final rows = await db.query('synced_projects');
final syncedIds = rows.map((r) => r['project_id'] as String).toSet();
```

**Tap on My Project** → `projectProvider.selectProject(id)` → navigate to dashboard (existing behavior).

**Tap on Company Project** → show confirm dialog:
```dart
showDialog(
  builder: (_) => AlertDialog(
    title: Text('Load Project?'),
    content: Text('${project.name}\n${project.projectNumber}'),
    actions: [
      TextButton(onPressed: () => Navigator.pop(context), child: Text('Cancel')),
      ElevatedButton(
        onPressed: () async {
          // 1. Insert into synced_projects
          await db.insert('synced_projects', {
            'project_id': project.id,
            'synced_at': DateTime.now().toUtc().toIso8601String(),
          }, conflictAlgorithm: ConflictAlgorithm.ignore);
          // 2. Select the project
          projectProvider.selectProject(project.id);
          // 3. Navigate to dashboard
          Navigator.pop(context);
          context.goNamed('dashboard');
          // 4. Background sync will pull child data on next cycle
        },
        child: Text('Load Project'),
      ),
    ],
  ),
);
```

**Empty state handling**:
- No local projects AND offline → show "Create New Project" only
- No local projects AND online → first sync hasn't run yet; show loading or prompt
- Company Projects section hidden when all projects are already loaded

**File 3: `lib/features/projects/presentation/screens/project_setup_screen.dart`**

In `_saveProject()`, after successful new project creation, auto-enroll in `synced_projects` (locally-created projects are always "loaded"):

```dart
// Only for new projects, not edits [AR-7 FIX]
if (!isEditing) {
  final db = context.read<DatabaseService>().database; // [AR-12 FIX]
  await db.insert('synced_projects', {
    'project_id': _projectId,
    'synced_at': DateTime.now().toUtc().toIso8601String(),
  }, conflictAlgorithm: ConflictAlgorithm.ignore);
}
```

### Verification
- [ ] Fresh install → first sync pulls ALL company project metadata
- [ ] Project list shows "Company Projects" section with unloaded projects
- [ ] Tap company project → confirm → project loads, child data syncs in background
- [ ] Create new project → auto-enrolled in `synced_projects`
- [ ] Edit existing project → NO redundant enrollment
- [ ] Offline → "Company Projects" section hidden, "Create New Project" available
- [ ] Empty contractor list → equipment adapter skipped (no crash)

---

## WS3: Populate `companies` Table Locally

**Agent**: `backend-data-layer-agent`
**Risk**: MEDIUM
**Files**: 4
**Depends on**: WS1

### Root Cause

`user_profiles` has FK to `companies(id)`. `CompanyLocalDatasource` exists but never instantiated. `pullCompanyMembers()` inserts profiles → FK fails.

### Changes

**File 1: `lib/features/auth/services/auth_service.dart`** (~line 215)

Add `getCompanyById(String companyId)` method. `CompanyRemoteDatasource.getById()` already exists.

**File 2: `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart`**

Add `CompanyLocalDatasource` constructor param. In `pullCompanyMembers()`, before profile loop, ensure company exists locally:

```dart
final existingCompany = await _companyLocalDatasource.getById(companyId);
if (existingCompany == null) {
  final response = await _client.from('companies').select().eq('id', companyId).maybeSingle();
  if (response != null) {
    await _companyLocalDatasource.upsert(Company.fromJson(response));
  }
}
```

**File 3: `lib/features/auth/presentation/providers/auth_provider.dart`**

Add `CompanyRepository?` constructor param. In `createCompany()` (~line 570): `await _companyRepository?.save(company)`. In `loadUserProfile()` (~line 511): fetch+persist company if not locally cached.

**File 4: `lib/main.dart`**

**[AR-9 FIX]**: Instantiate `CompanyLocalDatasource` + `CompanyRepository` BEFORE `UserProfileSyncDatasource` construction. Pass to `AuthProvider` and `UserProfileSyncDatasource`.

**[AR-5 FIX]**: Add `created_by_user_id TEXT` column to local `companies` table via `_addColumnIfNotExists` in the next DB migration (can piggyback on v32).

### Verification
- [ ] Sign in → company in local `companies` table
- [ ] Sync → `pullCompanyMembers` succeeds (no FK violation)
- [ ] Sign out → sign in → company repopulated from Supabase

---

## WS4: Eager Project Row INSERT

**Agent**: `frontend-flutter-specialist-agent`
**Risk**: MEDIUM
**Files**: 2
**Can parallel with**: WS2, WS3

### Root Cause

`project_setup_screen.dart:66` generates UUID but doesn't INSERT until Save. 5 child-record entry points use `_projectId!` before Save → FK violation.

### Changes

**File 1: `lib/features/projects/presentation/providers/project_provider.dart`**

Add `addToListIfAbsent(Project)` helper method.

**File 2: `lib/features/projects/presentation/screens/project_setup_screen.dart`**

Add `_projectInserted` flag + `_insertDraftProject()` async method called from `initState` post-frame callback (new projects only). Uses `repository.save()` (bypasses duplicate-number check) with minimal project (`name: '', projectNumber: ''`).

Modify `_saveProject()` new-project branch: if `_projectInserted`, call `updateProject()` + `addToListIfAbsent()` instead of `createProject()`.

**Draft projects are NOT enrolled in `synced_projects`** — enrollment happens in `_saveProject()` AFTER the user fills in real data and saves. This prevents empty drafts from being pushed to Supabase (resolves AR-3 by design).

### Edge Cases
- Abandoned drafts: `StartupCleanupService` cleans up (empty, >30min, `created_at == updated_at`)
- Eager insert fails: fallback to `createProject()` path
- Duplicate check: `'' != 'real_number'` → runs against new value

### Verification
- [ ] Create project → import PDF → bid items save (no FK error)
- [ ] Add location before Save → works
- [ ] Abandon → restart → orphan cleaned up
- [ ] Draft project NOT pushed to Supabase (not in synced_projects until Save)

---

## WS5: Deprecate `entry_personnel` Table

**Phases**: 5 (strictly sequential)
**Risk**: MEDIUM
**Depends on**: WS1-WS4 complete
**DB version**: 31 → 32 (Phase 5.1) → 33 (Phase 5.4)

### Phase 5.1 — Safety Backfill (DB v32)

**File**: `database_service.dart`

- **[H4 FIX]**: Wrap backfill in `db.transaction()` for atomicity
- **[H5 FIX]**: Pre-load ALL `personnel_types` in one query before loop
- **[H1 FIX]**: Filter `ep.deleted_at IS NULL` in orphan query
- JOIN `personnel_types` for real type_ids (format `personnel-type-{projectId}-{shortCode}`)
- **[AR-5 FIX]**: Add `_addColumnIfNotExists(db, 'companies', 'created_by_user_id', 'TEXT')` (piggybacking on v32)
- Version bump: 31 → 32

### Phase 5.2 — Remove Display Fallbacks

**Files**: `home_screen.dart`, `entry_contractors_section.dart`
- Delete `if (contractorsWithData.isEmpty)` legacy fallback blocks
- Replace with direct `personnelCounts` fold

### Phase 5.3 — Remove Backend Dual-Write

**Files**: 5
- `contractor_editing_controller.dart` — remove ALL of: `_personnelDatasource` field (line 34), constructor param (line 40), `_personnel` field (line 53), `personnel` getter (line 74), `_personnelDatasource.getByEntryId()` call (line 117), `_personnel = personnel` (line 146), dual-write block (lines 250-299), `_personnelDatasource.saveForEntry()` (line 324), `_personnel = updatedPersonnel` (line 328) **[AR-6 + H3 FIX]**
- `pdf_data_builder.dart` — **[C1]** add `PersonnelTypeProvider` param, **[C2]** rename loop var to `contractorEntry`
- `entry_editor_screen.dart` — remove `_personnelDatasource`, update controller + PDF call
- `home_screen.dart` — update controller construction
- `contractor_local_datasource.dart` — rewrite `getMostFrequentIds()` SQL to use `entry_personnel_counts`

### Phase 5.4 — Drop Table (DB v33)

**Files**: 7
- `database_service.dart` — v33 migration: DROP TABLE, remove from `_onCreate`, bump to 33
- `personnel_tables.dart` — delete `createEntryPersonnelTable` + 2 indexes
- `schema_verifier.dart` — remove `entry_personnel` from expected schema + `_columnTypes`
- `auth_service.dart` — remove from `clearLocalCompanyData` list
- `database_service_test.dart` — remove assertion
- `mock_database.dart` — remove CREATE TABLE
- `sqlite_test_helper.dart` — remove CREATE TABLE

### Phase 5.5 — Code Cleanup

DELETE: `entry_personnel.dart`, `entry_personnel_local_datasource.dart`, `entry_personnel_test.dart`
UPDATE: barrel exports, `test_helpers.dart`, `pdf_service_test.dart`, `README.md`

---

## WS6: Permissions UX (Role-Based View-Only)

**Depends on**: WS5

### Task A: Standardize Provider Silent Failures

**[M1 FIX]**: Add `checkWritePermission(String action)` to `BaseListProvider` itself (since `_error` is file-private). Standalone providers get their own copy.

### Task B: Add ViewOnlyBanner to 7 Data-Editing Screens

Pattern: `if (context.watch<AuthProvider>().isViewer) const ViewOnlyBanner()`

### Task C: Admin Dashboard Redirect

`app_router.dart:216` — change `return '/'` to `return '/settings'` for non-admins.

---

## WS7: Android Permissions Dialog Auto-Advance (DONE)

Already implemented this session. `permission_dialog.dart` converted to StatefulWidget with `WidgetsBindingObserver`. No further changes needed.

---

## Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Adapter order wrong | LOW | HIGH | Order matches `SyncEngineTables.triggeredTables` |
| Background isolate misses registration | LOW | HIGH | `registerSyncAdapters()` in both paths |
| Company fetch slow/fails | MEDIUM | LOW | try/catch + defensive guard in pullCompanyMembers |
| Empty `.inFilter([])` crash | LOW | HIGH | Separate skip guards per scope type (AR-1) |
| Draft projects pushed to Supabase | LOW | HIGH | Not enrolled until Save (AR-3 resolved by design) |
| First sync flood | MEDIUM | MEDIUM | v31 marks pre-cutover as processed |
| v32 backfill FK violation | LOW | HIGH | JOINs personnel_types; transaction-wrapped (H4) |
| PDF personnel breaks | MEDIUM | HIGH | Verified with test before Phase 5.4 |
| Variable shadowing in pdf_data_builder | LOW | HIGH | Explicit rename (C2) |
| BaseListProvider._error access | LOW | MEDIUM | checkWritePermission in base class (M1) |

---

## Commit Structure

```
fix(sync): register 16 adapters in foreground + background init
fix(sync): replace blanket pull gate with per-adapter scope check
feat(projects): two-section project list with load-from-company flow
fix(auth): populate companies table locally for FK integrity
fix(projects): eager-insert draft project row before child records
feat(db): v32 safety backfill entry_personnel_counts + companies column
refactor(entries): remove entry_personnel display fallbacks
refactor(contractors): remove dual-write bridge, update PDF path
feat(db): v33 drop entry_personnel table, update tests
chore(cleanup): delete entry_personnel model, datasource, and tests
fix(permissions): standardize provider write-guard error messages
feat(ui): add ViewOnlyBanner to all data-editing screens
fix(router): redirect non-admins from admin-dashboard to /settings
```

---

## Agent Assignment

| Agent | Workstreams |
|-------|-------------|
| `backend-data-layer-agent` | WS1, WS2 (sync_engine.dart), WS3, WS5 (5.1, 5.3, 5.4, 5.5), WS6 Task A |
| `frontend-flutter-specialist-agent` | WS2 (project_list_screen.dart), WS4, WS5 (5.2), WS6 Tasks B + C |

---

## Complete File List

### WS1 (3 files)
- `lib/features/sync/engine/sync_registry.dart`
- `lib/features/sync/application/sync_orchestrator.dart`
- `lib/features/sync/application/background_sync_handler.dart`

### WS2 (3 files)
- `lib/features/sync/engine/sync_engine.dart`
- `lib/features/projects/presentation/screens/project_list_screen.dart`
- `lib/features/projects/presentation/screens/project_setup_screen.dart`

### WS3 (4 files)
- `lib/features/auth/services/auth_service.dart`
- `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart`
- `lib/features/auth/presentation/providers/auth_provider.dart`
- `lib/main.dart`

### WS4 (2 files)
- `lib/features/projects/presentation/providers/project_provider.dart`
- `lib/features/projects/presentation/screens/project_setup_screen.dart`

### WS5 (21 files across 5 phases)
- `lib/core/database/database_service.dart`
- `lib/core/database/schema/personnel_tables.dart`
- `lib/core/database/schema_verifier.dart`
- `lib/features/auth/services/auth_service.dart`
- `lib/features/entries/presentation/screens/home_screen.dart`
- `lib/features/entries/presentation/widgets/entry_contractors_section.dart`
- `lib/features/entries/presentation/controllers/contractor_editing_controller.dart`
- `lib/features/entries/presentation/controllers/pdf_data_builder.dart`
- `lib/features/entries/presentation/screens/entry_editor_screen.dart`
- `lib/features/contractors/data/datasources/local/contractor_local_datasource.dart`
- `lib/features/contractors/data/models/entry_personnel.dart` (DELETE)
- `lib/features/contractors/data/datasources/local/entry_personnel_local_datasource.dart` (DELETE)
- `lib/features/contractors/data/models/models.dart`
- `lib/features/contractors/data/datasources/local/local_datasources.dart`
- `test/features/contractors/data/models/entry_personnel_test.dart` (DELETE)
- `test/services/pdf_service_test.dart`
- `test/helpers/test_helpers.dart`
- `test/helpers/README.md`
- `test/helpers/mock_database.dart`
- `test/core/database/database_service_test.dart`
- `test/helpers/sync/sqlite_test_helper.dart`

### WS6 (up to 19 files)
- `lib/shared/providers/base_list_provider.dart`
- 10 provider files
- 7 screen files
- `lib/core/router/app_router.dart`
