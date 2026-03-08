# Implementation Plan: Critical Data Layer & Permissions Fixes

**Created**: 2026-03-06
**Status**: DRAFT — awaiting user brainstorm
**Branch**: `feat/sync-engine-rewrite` (same branch, pre-PR fixes)

---

## Executive Summary

Four critical defects discovered during device testing of the sync engine rewrite. All must be fixed before the `feat/sync-engine-rewrite` PR is merged to main.

| # | Fix | Severity | Root Cause |
|---|-----|----------|------------|
| 1 | `companies` table never populated locally | CRITICAL | FK chain: `user_profiles.company_id -> companies.id`. No code path inserts into local `companies`. Sync of user profiles always fails. |
| 2A | `synced_projects` gate blocks ALL sync pulls | CRITICAL | `sync_engine.dart:616-618` early-returns if `synced_projects` is empty, blocking even `ScopeType.direct` adapters (projects) that don't need it. |
| 2B | `SyncRegistry.registerAdapters()` never called | CRITICAL | Only called in test code. Adapter list empty in production. Push/pull processes 0 tables. |
| 3 | Pre-generated project UUID causes FK violations | CRITICAL | `project_setup_screen.dart:66` generates UUID but doesn't INSERT project until Save. Child records (bid_items, locations, contractors) fail FK check. |
| 4 | v30 migration column mismatch | FIXED | `entry_personnel_counts` rebuild SELECTed non-existent columns. Already patched this session. Verified complete. |

**Also fixed this session** (not part of this plan):
- Permissions dialog auto-advance (`permission_dialog.dart`) — converted to StatefulWidget with `WidgetsBindingObserver` lifecycle re-check

---

## Overlap with Data Layer Fixes Plan

**Fix 2B overlaps with `2026-03-06-data-layer-fixes.md` WS1.** The data-layer plan has a better approach: creates a shared `registerSyncAdapters()` top-level function called from both foreground (`SyncOrchestrator.initialize()`) AND background isolate (`backgroundSyncHandler`). We adopt that approach here.

No other overlaps. The data-layer plan's WS2 (entry_personnel deprecation) and WS3 (role-based permissions) are independent work items.

---

## Execution Order (Dependencies)

```
Fix 2B (register adapters) ─── must be first, everything else depends on it
    │
    ├── Fix 2A (remove blanket pull gate) ─── enables project sync
    │       │
    │       └── Fix 1 (companies FK) ─── enables user_profiles sync
    │
    └── Fix 3 (eager project INSERT) ─── independent, can parallel with 2A/1
```

---

## Fix 2B: Register Sync Adapters in Production

**Agent**: `backend-data-layer-agent`
**Risk**: LOW — purely additive
**Files**: 3

### Root Cause

`SyncRegistry.registerAdapters()` is only called in `test/features/sync/engine/adapter_integration_test.dart:38`. In production, `SyncRegistry.instance.adapters` is empty. Push/pull loops iterate 0 adapters and silently succeed.

### Changes

**File 1: `lib/features/sync/engine/sync_registry.dart`**

Add a top-level function after the class (adopted from data-layer-fixes WS1):

```dart
/// Register all 16 table adapters in FK dependency order.
/// Called from both foreground (SyncOrchestrator) and background
/// (backgroundSyncCallback) initialization paths.
void registerSyncAdapters() {
  SyncRegistry.instance.registerAdapters([
    ProjectAdapter(),
    LocationAdapter(),
    ContractorAdapter(),
    EquipmentAdapter(),
    BidItemAdapter(),
    PersonnelTypeAdapter(),
    DailyEntryAdapter(),
    PhotoAdapter(),
    EntryEquipmentAdapter(),
    EntryQuantitiesAdapter(),
    EntryContractorsAdapter(),
    EntryPersonnelCountsAdapter(),
    InspectorFormAdapter(),
    FormResponseAdapter(),
    TodoItemAdapter(),
    CalculationHistoryAdapter(),
  ]);
}
```

Plus 16 adapter imports at the top of the file.

**File 2: `lib/features/sync/application/sync_orchestrator.dart`**

In `initialize()`, after the mock-adapter block (~line 107), before `sync_metadata` query:

```dart
if (!_isMockMode) {
  registerSyncAdapters();
  DebugLogger.sync('SyncOrchestrator: Registered ${SyncRegistry.instance.adapters.length} adapters');
}
```

Import: `import '../engine/sync_registry.dart';`

**File 3: `lib/features/sync/application/background_sync_handler.dart`**

In `backgroundSyncCallback()`, after Supabase init (~line 38), before `SyncEngine.createForBackgroundSync()`:

```dart
registerSyncAdapters(); // Isolates don't share static state
```

Import: `import '../engine/sync_registry.dart';`

### Verification

- `flutter analyze` — 0 issues
- `flutter test test/features/sync/` — all pass
- Manual: trigger sync → push/pull counts > 0 in debug logs

---

## Fix 2A: Remove Blanket Sync Pull Gate

**Agent**: `backend-data-layer-agent`
**Risk**: LOW — makes pull more granular
**Files**: 2

### Root Cause

`sync_engine.dart:616-618` — `_pull()` early-returns when `_syncedProjectIds` is empty:

```dart
if (_syncedProjectIds.isEmpty) {
  DebugLogger.sync('Pull: no synced projects, skipping');
  return const SyncEngineResult();
}
```

This blocks ALL adapters, including `ProjectAdapter` which uses `ScopeType.direct` (filtered by `company_id`, not `project_id`).

### Changes

**File 1: `lib/features/sync/engine/sync_engine.dart`**

Replace the 3-line early-return (lines 616-618) with per-adapter skip logic inside the pull loop:

```dart
// Remove the early-return. Direct-scope adapters (e.g. projects) always run.
// Skip viaProject/viaEntry/viaContractor adapters when no projects are synced.
```

Inside the `for (final adapter in _registry.adapters)` loop, add before `_pullTable(adapter)`:

```dart
if (_syncedProjectIds.isEmpty &&
    adapter.scopeType != ScopeType.direct) {
  DebugLogger.sync('Pull skip (no synced projects): ${adapter.tableName}');
  continue;
}
```

Also, after `_pullTable()` completes for the `projects` adapter, auto-enroll pulled projects into `synced_projects`:

```dart
if (adapter.tableName == 'projects' && count > 0) {
  // Auto-enroll pulled projects so subsequent adapters can pull their data
  final projects = await db.query('projects', columns: ['id']);
  for (final p in projects) {
    await db.insert('synced_projects', {
      'project_id': p['id'] as String,
      'synced_at': DateTime.now().toUtc().toIso8601String(),
    }, conflictAlgorithm: ConflictAlgorithm.ignore);
  }
  await _loadSyncedProjectIds(); // Refresh the cached list
}
```

**File 2: `lib/features/projects/presentation/screens/project_setup_screen.dart`**

In `_saveProject()`, after successful project creation/update, auto-insert into `synced_projects`:

```dart
// Auto-enroll locally-created project for sync
final db = await DatabaseService().database;
await db.insert('synced_projects', {
  'project_id': _projectId,
  'synced_at': DateTime.now().toUtc().toIso8601String(),
}, conflictAlgorithm: ConflictAlgorithm.ignore);
```

### Design Decision: Auto-enroll ALL pulled projects?

**Question for user**: When the `projects` adapter pulls company projects from Supabase, should ALL of them be auto-enrolled in `synced_projects`? Or should only locally-created projects be auto-enrolled, and server projects require manual selection?

- **Option A**: Auto-enroll all → simplest, user sees all company data immediately
- **Option B**: Auto-enroll local only, server projects via selection screen → user controls data footprint
- **Option C**: Auto-enroll all on first sync, then user manages via selection screen → best onboarding experience

### Verification

- Fresh install → sync pulls projects (ScopeType.direct) even with empty `synced_projects`
- Locally-created project auto-enrolled in `synced_projects`
- After projects are enrolled, subsequent sync pulls locations/contractors/entries

---

## Fix 1: Populate `companies` Table Locally

**Agent**: `backend-data-layer-agent`
**Risk**: MEDIUM — touches auth flow
**Files**: 4

### Root Cause

- `user_profiles` has `FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE` (core_tables.dart:73)
- `PRAGMA foreign_keys=ON` enforced (database_service.dart:61)
- `CompanyLocalDatasource` exists but is never instantiated
- `AuthProvider.createCompany()` writes to Supabase only, stores result in `_company` in-memory
- `clearLocalCompanyData()` wipes `companies` on sign-out
- No sync adapter for `companies` table

### Changes (in application order)

**File 1: `lib/features/auth/services/auth_service.dart`**

Add `getCompanyById()` method (~line 215):

```dart
Future<Company?> getCompanyById(String companyId) async {
  final ds = _companyDs;
  if (ds == null) return null;
  return ds.getById(companyId);
}
```

`CompanyRemoteDatasource.getById()` already exists at company_remote_datasource.dart:21-30.

**File 2: `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart`**

Add `CompanyLocalDatasource` constructor param. In `pullCompanyMembers()`, before inserting profiles, ensure company row exists locally:

```dart
// Ensure FK parent exists: user_profiles.company_id -> companies.id
final existingCompany = await _companyLocalDatasource.getById(companyId);
if (existingCompany == null) {
  final response = await _client
      .from('companies')
      .select()
      .eq('id', companyId)
      .maybeSingle();
  if (response != null) {
    await _companyLocalDatasource.upsert(Company.fromJson(response));
  }
}
```

This is the **critical defensive fix** — even if other paths fail to write the company, sync won't blow up.

**File 3: `lib/features/auth/presentation/providers/auth_provider.dart`**

Add `CompanyRepository?` constructor param + field.

In `createCompany()` (~line 570), after `_company = company`:
```dart
await _companyRepository?.save(company);
```

In `loadUserProfile()` (~line 510), after profile is set, ensure company exists locally:
```dart
final companyId = _userProfile?.companyId;
if (companyId != null && _companyRepository != null) {
  try {
    final existing = await _companyRepository!.getById(companyId);
    if (existing == null) {
      final remoteCompany = await _authService.getCompanyById(companyId);
      if (remoteCompany != null) {
        await _companyRepository!.save(remoteCompany);
      }
    }
  } catch (e) {
    debugPrint('[AuthProvider] company fetch failed: $e');
  }
}
```

**File 4: `lib/main.dart`**

Instantiate `CompanyLocalDatasource` + `CompanyRepository` (after ~line 202):
```dart
final companyLocalDatasource = CompanyLocalDatasource(dbService);
final companyRepository = CompanyRepository(companyLocalDatasource);
```

Pass to `AuthProvider` construction (~line 254):
```dart
companyRepository: companyRepository,
```

Pass `companyLocalDatasource` to `UserProfileSyncDatasource` construction (~line 237):
```dart
UserProfileSyncDatasource(Supabase.instance.client, userProfileLocalDs, companyLocalDatasource),
```

### Verification

- Sign in → company persisted to local SQLite
- Sync → `pullCompanyMembers` succeeds (no FK violation)
- Sign out → sign in → company repopulated from Supabase

---

## Fix 3: Eager Project Row Insert

**Agent**: `frontend-flutter-specialist-agent`
**Risk**: MEDIUM — changes project creation flow
**Files**: 2

### Root Cause

`project_setup_screen.dart:66` generates `_projectId = Uuid().v4()` but doesn't INSERT until Save (line 786). Child records via tabs (locations, contractors, bid items, PDF import) all reference `_projectId` and fail FK check.

5 child-record entry points use `_projectId!` before Save:
- `_showAddLocationDialog()` (line 592)
- `_showAddContractorDialog()` (line 596)
- `_showAddBidItemDialog()` (line 604)
- `MpImportHelper.importMeasurementPayment()` (line 692)
- `PdfImportHelper.importFromPdf()` (line 703)

### Changes

**File 1: `lib/features/projects/presentation/providers/project_provider.dart`**

Add helper method:

```dart
/// Add project to in-memory list if not already present.
/// Used after eager draft INSERT to keep provider state consistent.
void addToListIfAbsent(Project project) {
  if (!_projects.any((p) => p.id == project.id)) {
    _projects.add(project);
    notifyListeners();
  }
}
```

**File 2: `lib/features/projects/presentation/screens/project_setup_screen.dart`**

**Change A**: Add flag + eager insert method:

```dart
bool _projectInserted = false;
```

In `initState`, after the `addPostFrameCallback` that clears providers, add:

```dart
if (!isEditing) {
  _insertDraftProject();
}
```

```dart
Future<void> _insertDraftProject() async {
  if (_projectId == null) return;
  try {
    final authProvider = context.read<AuthProvider>();
    final projectProvider = context.read<ProjectProvider>();
    final draftProject = Project(
      id: _projectId!,
      name: '',
      projectNumber: '',
      companyId: authProvider.userProfile?.companyId,
      createdByUserId: authProvider.userId,
    );
    // Use repository.save() which bypasses duplicate-number check
    await projectProvider.repository.save(draftProject);
    _projectInserted = true;
  } catch (e) {
    debugPrint('[ProjectSetup] Draft insert failed: $e');
    // Fallback: _saveProject() will use createProject() path
  }
}
```

**Change B**: Modify `_saveProject()` new-project branch:

```dart
if (_projectInserted) {
  // Row already exists — update with real values
  success = await projectProvider.updateProject(fullProject);
  if (success) {
    projectProvider.addToListIfAbsent(fullProject);
  }
} else {
  // Fallback: eager insert never ran
  success = await projectProvider.createProject(fullProject);
}
```

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| User adds children then taps Save | Works — project row exists, FK satisfied |
| User abandons without saving | `StartupCleanupService` cleans up after 30 min (empty project, `created_at == updated_at`) |
| Eager insert fails (DB not ready) | `_projectInserted = false`, falls through to normal `createProject()` |
| Two projects created simultaneously | Each has unique UUID, no conflict |
| `updateProject()` duplicate check | `'' != 'real_number'` → check runs against new value, correct |

### Verification

- Create new project → navigate to Pay Items tab → import PDF → bid items save successfully
- Abandon project creation → wait 30 min → orphan cleanup removes draft
- Create project, fill all fields, Save → project appears in list correctly

---

## Fix 4: v30 Migration Column Mismatch — VERIFIED COMPLETE

Already fixed this session. The `entry_personnel_counts` rebuild SELECT now only references columns that exist in the old table. v31 `daily_entries` and `photos` rebuilds verified correct. No other INSERT...SELECT has column mismatch issues.

No further changes needed.

---

## Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `loadUserProfile` company fetch slow/fails | MEDIUM | LOW | try/catch with fallback; defensive guard in `pullCompanyMembers` |
| Auto-enrolled projects pull too much data | LOW | MEDIUM | `ConflictAlgorithm.ignore` is idempotent; user can manage via selection screen |
| Eager project insert races with provider state | LOW | LOW | `_projectInserted` flag; `addToListIfAbsent` is idempotent |
| Background sync isolate misses adapter registration | LOW | HIGH | `registerSyncAdapters()` called in both foreground AND background paths |
| First sync pushes accumulated change_log entries | MEDIUM | MEDIUM | v31 marks pre-cutover entries as processed; only post-v31 changes sync |

---

## Testing Checklist

### After Fix 2B
- [ ] `flutter analyze` — 0 issues
- [ ] `flutter test test/features/sync/` — all pass
- [ ] Manual: trigger sync → adapter count logged > 0

### After Fix 2A
- [ ] Fresh install → sync pulls projects (ScopeType.direct runs)
- [ ] Create project locally → auto-enrolled in `synced_projects`
- [ ] Subsequent sync pulls locations/contractors for enrolled projects

### After Fix 1
- [ ] Sign in → company row exists in local `companies` table
- [ ] Sync → `pullCompanyMembers` succeeds
- [ ] Sign out → sign in → company repopulated

### After Fix 3
- [ ] Create project → import PDF → bid items save (no FK error)
- [ ] Create project → add location → saves (no FK error)
- [ ] Abandon project → orphan cleanup handles it

---

## Commit Structure

```
fix(sync): register 16 adapters in foreground + background init
fix(sync): replace blanket pull gate with per-adapter scope check
fix(auth): populate companies table locally for FK integrity
fix(projects): eager-insert draft project row before child records
```
