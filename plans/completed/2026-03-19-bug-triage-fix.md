# S591 Bug Triage Fix Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Fix 13 bugs from S591 device testing: permission model rewrite (canWrite → canManageProjects + canEditFieldData), sync engine deadlock/retry/DNS fixes, UI gating, route guards, RLS tightening, and stale state cleanup.
**Spec:** `.claude/specs/2026-03-19-bug-triage-fix-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-19-bug-triage-fix/`

**Architecture:** Replace the always-true `canWrite` permission with two granular getters (`canManageProjects` for admin/engineer project management, `canEditFieldData` for all roles' field data editing). Fix sync engine race conditions (orphan cleaner firing before projects adapter, no retry after exhaustion, stale DNS flags). Gate UI actions per the new permission matrix and add route-level guards.
**Tech Stack:** Flutter/Dart, SQLite (sqflite), Supabase (RLS/PostgreSQL), GoRouter
**Blast Radius:** 14 direct files, ~24 files with canWrite references, 10 main.dart injection sites, 1 new RLS migration, 6+ test files

---

## Phase 1: Permission Model (Auth Layer)
### Sub-phase 1.1: Add New Permission Getters to UserRole
**Files:**
- Modify: `lib/features/auth/data/models/user_role.dart:36`
- Test: `test/features/auth/data/models/user_role_test.dart`
**Agent:** auth-agent

#### Step 1.1.1: Add canManageProjects and canEditFieldData to UserRole enum
In `lib/features/auth/data/models/user_role.dart`, add new getters AFTER the existing `canWrite` getter (do NOT remove canWrite yet — compile-time break protection):

```dart
// FIND (line ~36):
  bool get canWrite => true;

// ADD AFTER:
  /// Whether this role can create, archive, delete, or edit project-level details.
  /// FROM SPEC: admin + engineer only.
  bool get canManageProjects => this == admin || this == engineer;

  /// Whether this role can edit field data (contractors, equipment, personnel,
  /// locations, pay items, entries, photos, todos, forms).
  /// FROM SPEC: all roles can edit field data.
  bool get canEditFieldData => true;
```

#### Step 1.1.2: Verify
Run: `pwsh -Command "flutter test test/features/auth/data/models/"`
Expected: PASS (existing tests still pass, canWrite unchanged)

---

### Sub-phase 1.2: Add New Permission Getters to UserProfile
**Files:**
- Modify: `lib/features/auth/data/models/user_profile.dart:65`
**Agent:** auth-agent

#### Step 1.2.1: Add delegation getters to UserProfile
In `lib/features/auth/data/models/user_profile.dart`, add after the existing `canWrite` getter:

```dart
// FIND (line ~65):
  bool get canWrite => role.canWrite;

// ADD AFTER:
  /// FROM SPEC: admin + engineer only.
  bool get canManageProjects => role.canManageProjects;

  /// FROM SPEC: all roles.
  bool get canEditFieldData => role.canEditFieldData;
```

#### Step 1.2.2: Verify
Run: `pwsh -Command "flutter test test/features/auth/"`
Expected: PASS

---

### Sub-phase 1.3: Add New Permission Getters to AuthProvider + Remove Dead Code
**Files:**
- Modify: `lib/features/auth/presentation/providers/auth_provider.dart:183,194,212`
**Agent:** auth-agent

#### Step 1.3.1: Remove dead canEditProject getter (BUG-012)
In `lib/features/auth/presentation/providers/auth_provider.dart`, delete:

```dart
// DELETE (line ~212):
  bool get canEditProject => canWrite;
```

#### Step 1.3.2: Add new permission getters
After the existing `canWrite` getter (line ~183), add:

```dart
// FIND (line ~183):
  bool get canWrite => _userProfile?.role.canWrite ?? false;

// ADD AFTER:
  /// FROM SPEC: admin + engineer can manage projects (create, archive, delete, edit details).
  bool get canManageProjects => _userProfile?.canManageProjects ?? false;

  /// FROM SPEC: all roles can edit field data.
  bool get canEditFieldData => _userProfile?.canEditFieldData ?? false;
```

#### Step 1.3.3: Verify
Run: `pwsh -Command "flutter test test/features/auth/"`
Expected: PASS

---

## Phase 2: Sync Engine Fixes
### Sub-phase 2.1: BUG-005/002 — Orphan Cleaner Guard + Post-Assignment Reload
**Files:**
- Modify: `lib/features/sync/engine/sync_engine.dart:1035-1100,1304-1348`
- Test: `test/features/sync/engine/sync_engine_test.dart`
**Agent:** backend-supabase-agent

#### Step 2.1.1: Add _projectsAdapterCompleted flag
In `sync_engine.dart`, add a field near the other state fields:

```dart
// ADD near other state fields (e.g., near _syncedProjectIds declaration):
  /// FROM SPEC (BUG-005): Guards orphan cleaner from running before projects adapter has populated the table.
  /// Reset to false at start of _pull(), set true after projects adapter completes.
  bool _projectsAdapterCompleted = false;
```

#### Step 2.1.2: Reset flag at start of _pull()
In `_pull()` method (line ~1035), add right after the method opens:

```dart
// FIND (inside _pull, near top, before _loadSyncedProjectIds call):
  Future<SyncEngineResult> _pull() async {
    await _loadSyncedProjectIds();

// REPLACE WITH:
  Future<SyncEngineResult> _pull() async {
    _projectsAdapterCompleted = false; // WHY: BUG-005 — reset before each pull cycle
    await _loadSyncedProjectIds();
```

#### Step 2.1.3: Set flag after projects adapter and reload after project_assignments
In `_pull()`, find the block that reloads after the projects adapter (line ~1068-1070) and extend it:

```dart
// FIND (line ~1068-1070):
        if (adapter.tableName == 'projects' && count > 0) {
          await _loadSyncedProjectIds();
        }

// REPLACE WITH:
        if (adapter.tableName == 'projects') {
          _projectsAdapterCompleted = true; // WHY: BUG-005 — orphan cleaner now safe to run
          if (count > 0) {
            await _loadSyncedProjectIds();
          }
        }
        // FROM SPEC (BUG-005): After project_assignments adapter runs, new synced_projects
        // entries exist. Reload so subsequent adapters see the updated project scope.
        if (adapter.tableName == 'project_assignments' && count > 0) {
          await _loadSyncedProjectIds();
        }
```

#### Step 2.1.4: Guard orphan cleaner in _loadSyncedProjectIds
In `_loadSyncedProjectIds()` (line ~1312-1327), wrap the orphan cleaner:

```dart
// FIND the orphan cleaner block (line ~1312-1327, inside _loadSyncedProjectIds):
  if (_syncedProjectIds.isNotEmpty) {
    final existingProjects = await db.query('projects', columns: ['id'],
        where: 'id IN ($placeholders)', whereArgs: _syncedProjectIds);
    final existingIds = existingProjects.map((r) => r['id'] as String).toSet();
    final orphanIds = _syncedProjectIds.where((id) => !existingIds.contains(id)).toList();
    if (orphanIds.isNotEmpty) {
      await db.delete('synced_projects',
          where: 'project_id IN ($orphanPlaceholders)', whereArgs: orphanIds);
      _syncedProjectIds = _syncedProjectIds.where((id) => existingIds.contains(id)).toList();
    }

// REPLACE WITH:
  if (_syncedProjectIds.isNotEmpty) {
    // FROM SPEC (BUG-005): Only run orphan cleaner AFTER the projects adapter has completed.
    // On a fresh device, synced_projects entries from project_assignments enrollment arrive
    // before the projects adapter runs. Without this guard, ALL entries look orphaned because
    // the projects table is still empty, causing a deadlock where no project data ever syncs.
    if (_projectsAdapterCompleted) {
      final placeholders = _syncedProjectIds.map((_) => '?').join(',');
      final existingProjects = await db.query('projects', columns: ['id'],
          where: 'id IN ($placeholders)', whereArgs: _syncedProjectIds);
      final existingIds = existingProjects.map((r) => r['id'] as String).toSet();
      final orphanIds = _syncedProjectIds.where((id) => !existingIds.contains(id)).toList();
      if (orphanIds.isNotEmpty) {
        final orphanPlaceholders = orphanIds.map((_) => '?').join(',');
        Logger.sync('Cleaning ${orphanIds.length} orphaned synced_projects entries');
        await db.delete('synced_projects',
            where: 'project_id IN ($orphanPlaceholders)', whereArgs: orphanIds);
        _syncedProjectIds = _syncedProjectIds.where((id) => existingIds.contains(id)).toList();
      }
    } else {
      Logger.sync('Skipping orphan cleaner — projects adapter has not completed yet');
    }

    // Load contractors for synced projects (existing logic preserved)
    // NOTE: This block continues the existing code after the orphan cleaner.
    // The rest of _loadSyncedProjectIds (contractor loading) is UNCHANGED.
```

#### Step 2.1.5: Verify
Run: `pwsh -Command "flutter test test/features/sync/"`
Expected: PASS

---

### Sub-phase 2.2: BUG-004 — Auto-Reschedule After Retry Exhaustion
**Files:**
- Modify: `lib/features/sync/application/sync_orchestrator.dart:214-285,292-346`
**Agent:** backend-supabase-agent

#### Step 2.2.1: Add _backgroundRetryTimer field
In `sync_orchestrator.dart`, add near other state fields:

```dart
// ADD near other fields:
  /// FROM SPEC (BUG-004): Cancellable timer for background retry after exhaustion.
  Timer? _backgroundRetryTimer;
```

Also ensure `dart:async` is imported (it should be already for Future/Completer, but Timer needs it too).

#### Step 2.2.2: Cancel timer at start of syncLocalAgencyProjects
In `syncLocalAgencyProjects()` (line ~214), add at the top of the method body:

```dart
// FIND (line ~214, start of method body):
  Future<SyncResult> syncLocalAgencyProjects() async {
    if (_companyId == null) {

// REPLACE WITH:
  Future<SyncResult> syncLocalAgencyProjects() async {
    // FROM SPEC (BUG-004): Cancel any pending background retry to prevent overlap.
    _backgroundRetryTimer?.cancel();
    _backgroundRetryTimer = null;
    if (_companyId == null) {
```

#### Step 2.2.3: Schedule retry after exhaustion in _syncWithRetry
In `_syncWithRetry()` (line ~292-346), after the for loop exhausts, add:

```dart
// FIND (end of _syncWithRetry, after the for loop, before the final return):
  // BUG-004: No background retry scheduled after exhaustion
  return lastResult;

// REPLACE WITH:
  // FROM SPEC (BUG-004): Schedule a background retry after 60s when all attempts are exhausted.
  // Uses a cancellable Timer (not Future.delayed) so syncLocalAgencyProjects() can cancel it.
  Logger.sync('All $_maxRetries retry attempts exhausted. Scheduling background retry in 60s.');
  _backgroundRetryTimer?.cancel();
  _backgroundRetryTimer = Timer(const Duration(seconds: 60), () async {
    // WHY: Must be async to await DNS check. Guard against disposed state.
    if (_disposed) return;
    // FROM SPEC: Re-check DNS before retrying to avoid futile retry loops.
    final dnsOk = await checkDnsReachability();
    if (dnsOk && !_disposed) {
      syncLocalAgencyProjects();
    }
  });
  return lastResult;
```

#### Step 2.2.4: Add _disposed flag and clean up timer on dispose
Add a `bool _disposed = false;` field near `_backgroundRetryTimer`. Then in the dispose/cleanup method:

```dart
// ADD field near _backgroundRetryTimer:
  bool _disposed = false;

// ADD to dispose or equivalent cleanup method:
    _disposed = true;
    _backgroundRetryTimer?.cancel();
    _backgroundRetryTimer = null;
```

#### Step 2.2.5: Verify
Run: `pwsh -Command "flutter test test/features/sync/"`
Expected: PASS

---

---

## Phase 3: Project List Screen
### Sub-phase 3.1: BUG-006 Screen-Side DNS Fixes
**Files:**
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart:62-82,88-91,507-539`
**Agent:** frontend-flutter-specialist-agent

#### Step 3.1.1: Fix _refresh to call checkDnsReachability before checking isSupabaseOnline
```dart
// FIND (line ~62-82, the _refresh method):
  Future<void> _refresh() async {
    if (!mounted) return;
    final authProvider = context.read<AuthProvider>();
    final orchestrator = context.read<SyncOrchestrator>();
    final projectProvider = context.read<ProjectProvider>();
    await authProvider.refreshUserProfile();
    try {
      if (orchestrator.isSupabaseOnline) {
        await orchestrator.syncLocalAgencyProjects();
      }
    } catch (e) { Logger.sync('Refresh sync failed: $e'); }
    if (!mounted) return;
    await projectProvider.fetchRemoteProjects();
  }

// REPLACE WITH:
  Future<void> _refresh() async {
    if (!mounted) return;
    final authProvider = context.read<AuthProvider>();
    final orchestrator = context.read<SyncOrchestrator>();
    final projectProvider = context.read<ProjectProvider>();
    await authProvider.refreshUserProfile();
    try {
      // FROM SPEC (BUG-006): Must re-check DNS before trusting isSupabaseOnline flag.
      await orchestrator.checkDnsReachability();
      if (orchestrator.isSupabaseOnline) {
        await orchestrator.syncLocalAgencyProjects();
      }
    } catch (e) { Logger.sync('Refresh sync failed: $e'); }
    if (!mounted) return;
    await projectProvider.fetchRemoteProjects();
  }
```

#### Step 3.1.2: Fix _checkNetwork to call checkDnsReachability
```dart
// FIND (line ~88-91):
  bool _checkNetwork() {
    final orchestrator = context.read<SyncOrchestrator>();
    return orchestrator.isSupabaseOnline;
  }

// REPLACE WITH:
  // WHY (BUG-006): DNS check is async but some callers need a sync read.
  // Provide both: async version for pre-action checks, sync for cached reads.
  Future<bool> _checkNetworkAsync() async {
    final orchestrator = context.read<SyncOrchestrator>();
    // FROM SPEC (BUG-006): Always re-check DNS before reading the cached flag.
    await orchestrator.checkDnsReachability();
    return orchestrator.isSupabaseOnline;
  }

  /// Sync version — reads cached flag only (no DNS re-check).
  bool _checkNetwork() {
    final orchestrator = context.read<SyncOrchestrator>();
    return orchestrator.isSupabaseOnline;
  }
```

**Known caller**: `_handleImport` at line ~108 calls `_checkNetwork()` synchronously within an async method. Update to use the async version:
```dart
// FIND in _handleImport (line ~108):
  final hasNetwork = _checkNetwork();

// REPLACE WITH:
  final hasNetwork = await _checkNetworkAsync();
```

#### Step 3.1.3: Fix _showRemovalDialog to refresh DNS before gating
```dart
// FIND (line ~507-539, start of _showRemovalDialog):
  Future<void> _showRemovalDialog(MergedProjectEntry entry) async {
    final orchestrator = context.read<SyncOrchestrator>();
    final isOnline = orchestrator.isSupabaseOnline;

// REPLACE WITH:
  Future<void> _showRemovalDialog(MergedProjectEntry entry) async {
    final orchestrator = context.read<SyncOrchestrator>();
    // FROM SPEC (BUG-006): Refresh DNS before gating syncAndRemove option.
    await orchestrator.checkDnsReachability();
    final isOnline = orchestrator.isSupabaseOnline;
```

#### Step 3.1.4: Verify
Run: `pwsh -Command "flutter test test/features/projects/"`
Expected: PASS

---

### Sub-phase 3.2: BUG-001 — Stale selectedProject After removeFromDevice
**Files:**
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart:171-209`
**Agent:** frontend-flutter-specialist-agent

#### Step 3.2.1: Clear selectedProject in _handleRemoveFromDevice
```dart
// FIND (line ~171-209, inside _handleRemoveFromDevice, after the successful removal and before/after the snackbar):
    if (!mounted) return;
    await context.read<ProjectProvider>().fetchRemoteProjects();
    if (!mounted) return;
    SnackBarHelper.showSuccess(context, 'Project removed from device');

// REPLACE WITH:
    if (!mounted) return;
    // FROM SPEC (BUG-001): Clear selectedProject if it matches the removed project.
    final projectProvider = context.read<ProjectProvider>();
    if (projectProvider.selectedProject?.id == projectId) {
      projectProvider.clearSelectedProject();
    }
    // FROM SPEC (BUG-001): Clear from settings/recents too.
    context.read<ProjectSettingsProvider>().clearIfMatches(projectId);
    await projectProvider.fetchRemoteProjects();
    if (!mounted) return;
    SnackBarHelper.showSuccess(context, 'Project removed from device');
```

NOTE: The agent must verify that `ProjectSettingsProvider` is accessible via `context.read` at this point. If not already provided, it needs to be imported and available in the widget tree. Check that `clearIfMatches` takes a String projectId param (the dependency graph says it does at project_settings_provider.dart:148-165).

#### Step 3.2.2: Verify
Run: `pwsh -Command "flutter test test/features/projects/"`
Expected: PASS

---

### Sub-phase 3.3: BUG-003/008/009 — Project Card Permission Gating + Tap Targets
**Files:**
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart:584-783`
**Agent:** frontend-flutter-specialist-agent

#### Step 3.3.1: Change _buildProjectCard signature
Replace the single `canWrite` bool parameter with two separate parameters:

```dart
// FIND the _buildProjectCard method signature:
  Widget _buildProjectCard(... canWrite, ...) {

// REPLACE the canWrite parameter with:
  // FROM SPEC: Split into two permissions per the permission matrix.
  bool canManageProjects,  // admin + engineer: archive, delete
  bool canEditFieldData,   // all roles: edit button (navigates to field data tabs)
```

NOTE: The agent must find the exact signature. The key change is replacing one `bool canWrite` with two bools.

#### Step 3.3.2: Update edit button gating (BUG-008)
```dart
// FIND (line ~740, edit button):
  onPressed: canWrite ? () { context.pushNamed('project-edit', ...); } : null,

// REPLACE WITH:
  // FROM SPEC (BUG-008): Edit button gated by canEditFieldData (true for all roles).
  // Inspector needs to reach field data tabs (contractors, locations, pay items).
  onPressed: canEditFieldData ? () { context.pushNamed('project-edit', ...); } : null,
```

#### Step 3.3.3: Add provider-level guard to toggleActive (defense-in-depth)
In `lib/features/projects/presentation/providers/project_provider.dart`, add a role check at the top of `toggleActive` (line ~531):

```dart
// FIND (line ~531):
  Future<bool> toggleActive(String id) async {
    // Find the project safely
    final project = _projects.where((p) => p.id == id).firstOrNull;

// REPLACE WITH:
  Future<bool> toggleActive(String id) async {
    // FROM SPEC (BUG-009): Defense-in-depth — reject archive/activate from unauthorized roles.
    // UI should already hide the button, but this guards against programmatic calls.
    if (!(_canManageProjects?.call() ?? false)) {
      _error = 'Only admins and engineers can archive or activate projects';
      notifyListeners();
      return false;
    }
    // Find the project safely
    final project = _projects.where((p) => p.id == id).firstOrNull;
```

This requires adding a `_canManageProjects` callback field to `ProjectProvider`, similar to the existing `canWrite` pattern on `BaseListProvider`. Add the field:

```dart
// ADD field to ProjectProvider:
  /// FROM SPEC (BUG-009): Role check for project management actions.
  bool Function()? _canManageProjects;
  set canManageProjects(bool Function() value) => _canManageProjects = value;
```

Wire it in `lib/main.dart` where ProjectProvider is created (the agent should find the ChangeNotifierProvider for ProjectProvider and add `p.canManageProjects = () => authProvider.canManageProjects;` after creation).

#### Step 3.3.4: Update archive button gating (BUG-009)
```dart
// FIND (line ~755, archive button):
  onPressed: canWrite ? () { context.read<ProjectProvider>().toggleActive(project.id); } : null,

// REPLACE WITH:
  // FROM SPEC (BUG-009): Archive/activate gated by canManageProjects (hidden for inspector).
  if (canManageProjects) ...[
    const SizedBox(width: 8),
    IconButton(
      key: TestingKeys.projectArchiveToggleButton(project.id),
      icon: Icon(project.isActive ? Icons.archive_outlined : Icons.unarchive_outlined),
      onPressed: () { context.read<ProjectProvider>().toggleActive(project.id); },
      tooltip: project.isActive ? 'Archive' : 'Activate',
      iconSize: 20,
      // FROM SPEC (BUG-003): Minimum 48x48 tap target.
      constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
    ),
  ],
```

NOTE: The agent must check the exact structure. If the archive button is currently always rendered, wrap it in the `if (canManageProjects)` conditional. The `const SizedBox(width: 8)` before it should also be inside the conditional.

#### Step 3.3.4: Fix tap target sizes (BUG-003)
For the edit button (and any other IconButtons with `constraints: const BoxConstraints()` and `padding: EdgeInsets.zero`):

```dart
// FIND (edit button constraints):
  padding: EdgeInsets.zero, constraints: const BoxConstraints(),

// REPLACE WITH:
  // FROM SPEC (BUG-003): Minimum 48x48 tap target per Material guidelines.
  constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
```

Apply the same fix to any other IconButtons in the card that have undersized constraints.

#### Step 3.3.5: Update all callers of _buildProjectCard
Update `_buildMyProjectsTab`, `_buildCompanyTab`, and `_buildArchivedTab` to pass the new params:

```dart
// FIND in each tab method (e.g., _buildMyProjectsTab at ~379-413):
  _buildProjectCard(... canWrite: authProvider.canWrite, ...)

// REPLACE WITH:
  _buildProjectCard(
    ...
    canManageProjects: authProvider.canManageProjects,
    canEditFieldData: authProvider.canEditFieldData,
    ...
  )
```

Repeat for all three tab methods.

#### Step 3.3.6: Verify
Run: `pwsh -Command "flutter test test/features/projects/"`
Expected: PASS

---

### Sub-phase 3.4: BUG-014 — Inspector Download Guard
**Files:**
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart:140-165,415-472`
**Agent:** frontend-flutter-specialist-agent

#### Step 3.4.1: Gate download in _showDownloadConfirmation or Company tab
In `_showDownloadConfirmation` (line ~140-165) or at the call site in `_buildCompanyTab`, add the inspector guard:

```dart
// In _buildCompanyTab, where the download action is wired up for each project card:
// FROM SPEC (BUG-014): Inspector cannot download unassigned projects.
// MergedProjectEntry already has isAssigned field.
final authProvider = context.read<AuthProvider>();
final isInspector = authProvider.userProfile?.role == UserRole.inspector;

// When building the download button/action:
if (!entry.isAssigned && isInspector) {
  // Disable download, show tooltip explaining why
  // onPressed: null,
  // tooltip: 'Only assigned projects can be downloaded',
}
```

NOTE: The agent must find the exact download button/action in the Company tab and apply the gate. The `MergedProjectEntry` already has `isAssigned`. The exact widget structure needs inspection — this may be a download icon, a button, or a list tile action.

#### Step 3.4.2: Verify
Run: `pwsh -Command "flutter test test/features/projects/"`
Expected: PASS

---

## Phase 4: Project Setup & Dashboard
### Sub-phase 4.1: BUG-011 — Dashboard Navigation + Staleness Guard
**Files:**
- Modify: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`
**Agent:** frontend-flutter-specialist-agent

#### Step 4.1.1: Add staleness guard for selectedProject
At the top of the build method or in the data-loading logic:

```dart
// FROM SPEC (BUG-001): If selectedProject ID is not in the projects list, treat as null.
// This prevents stale references after removeFromDevice.
final projectProvider = context.watch<ProjectProvider>();
final selectedProject = projectProvider.selectedProject;
if (selectedProject != null && !projectProvider.projects.any((p) => p.id == selectedProject.id)) {
  // WHY: Project was removed from device but selectedProject wasn't cleared (defensive guard).
  WidgetsBinding.instance.addPostFrameCallback((_) {
    projectProvider.clearSelectedProject();
  });
  // Show "no project selected" state instead of stale data
}
```

NOTE: The agent must find where `selectedProject` is consumed on the dashboard and insert this guard. The exact location depends on the widget structure.

#### Step 4.1.2: Ensure Contractors/Locations cards navigate for ALL roles (BUG-011)
Verify that the Contractors and Locations summary cards on the dashboard navigate to the project-edit screen's respective tabs. Per the spec, all roles should be able to navigate there (inspector can edit field data). If there's a `canWrite` guard on these navigation actions, replace with `canEditFieldData` or remove the guard entirely since all roles have field data access.

#### Step 4.1.3: Verify
Run: `pwsh -Command "flutter test test/features/dashboard/"`
Expected: PASS

---

### Sub-phase 4.2: Details Tab Read-Only for Inspector
**Files:**
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart`
- Modify: `lib/shared/widgets/view_only_banner.dart:12-41`
**Agent:** frontend-flutter-specialist-agent

#### Step 4.2.1: Add optional message param to ViewOnlyBanner
```dart
// FIND (view_only_banner.dart, class definition):
class ViewOnlyBanner extends StatelessWidget {
  const ViewOnlyBanner({super.key});

// REPLACE WITH:
class ViewOnlyBanner extends StatelessWidget {
  const ViewOnlyBanner({super.key, this.message});

  /// FROM SPEC (SC-8): Customizable message for different contexts.
  final String? message;
```

And where the text is rendered:

```dart
// FIND the hardcoded "View-only mode" text:
  'View-only mode'

// REPLACE WITH:
  message ?? 'View-only mode'
```

#### Step 4.2.2: Make Details tab read-only for inspector in ProjectSetupScreen
In the Details tab of `project_setup_screen.dart`:

```dart
// The agent must find the Details tab content (likely the first tab).
// When !canManageProjects (inspector):
// 1. Show ViewOnlyBanner with custom message
// 2. Make all text fields read-only (readOnly: true or enabled: false)
// 3. Hide the Save button

final authProvider = context.read<AuthProvider>();
final canManageProjects = authProvider.canManageProjects;

// At top of Details tab content:
if (!canManageProjects) ...[
  ViewOnlyBanner(
    // FROM SPEC: "Project details are managed by admins and engineers"
    message: 'Project details are managed by admins and engineers',
  ),
],

// For each text field in the Details tab:
// Add: readOnly: !canManageProjects,
// OR: enabled: canManageProjects,

// For the Save button:
if (canManageProjects) ...[
  // existing save button
],
```

NOTE: The agent must inspect the actual Details tab structure. The key fields are likely project name, description, project number, etc. The other tabs (Contractors, Locations, Pay Items) should remain editable for all roles — only the Details tab is restricted.

#### Step 4.2.3: Verify
Run: `pwsh -Command "flutter test test/features/projects/"`
Expected: PASS

---

## Phase 5: Router & Integration
### Sub-phase 5.1: BUG-007 — Route Guard for /project/new
**Files:**
- Modify: `lib/core/router/app_router.dart:124-615`
**Agent:** frontend-flutter-specialist-agent

#### Step 5.1.1: Add /project/new redirect in top-level GoRouter redirect
In the `_buildRouter` method's `redirect:` callback (line ~124-615), the redirect already uses
`_authProvider` (instance field on `AppRouter`, confirmed at line ~129). The guard MUST go
inside the `if (profile != null)` block (around line ~231) — AFTER the profile/company/status
checks — so it doesn't fire during profile loading or when profile is null. Place it alongside
the existing `/admin-dashboard` guard (around line ~265):

```dart
// FIND (near line ~265, the existing admin dashboard guard):
      // Guard admin dashboard — non-admins are redirected to settings
      if (location == '/admin-dashboard') {
        final isAdmin = _authProvider.userProfile?.isAdmin ?? false;
        if (!isAdmin) return '/settings';
      }

// ADD BEFORE the return null:
      // FROM SPEC (BUG-007): Guard project creation — inspector cannot create projects.
      // IMPORTANT: Must be inside `if (profile != null)` block to avoid firing during load.
      if (location == '/project/new') {
        if (!(_authProvider.canManageProjects)) {
          return '/projects';
        }
      }
```

#### Step 5.1.2: Verify /project/:id/edit is NOT guarded
Per the spec, `/project/:id/edit` should allow all roles (inspector needs contractor/location/pay-item tabs). Verify no redirect exists for this route. If one does, remove it.

#### Step 5.1.3: Verify
Run: `pwsh -Command "flutter test test/core/router/"`
Expected: PASS (if router tests exist)

---

### Sub-phase 5.2: BUG-006 — Global Offline Indicator in ScaffoldWithNavBar
**Files:**
- Modify: `lib/core/router/app_router.dart:627-747`
**Agent:** frontend-flutter-specialist-agent

#### Step 5.2.1: Add offline indicator banner
In `ScaffoldWithNavBar.build` (line ~627-747), in the banners list area (around line 660-710):

```dart
// FROM SPEC (BUG-006): Global offline indicator so users know network state.
// Add to the existing banners list (alongside version update, stale config, etc.)
final syncOrchestrator = context.watch<SyncOrchestrator>();
if (!syncOrchestrator.isSupabaseOnline) ...[
  MaterialBanner(
    content: const Text('You are offline. Changes will sync when connection is restored.'),
    leading: const Icon(Icons.cloud_off, color: Colors.orange),
    backgroundColor: Colors.orange.shade50,
    actions: [
      TextButton(
        onPressed: () async {
          await syncOrchestrator.checkDnsReachability();
        },
        child: const Text('Retry'),
      ),
    ],
  ),
],
```

NOTE: The agent must integrate this into the existing banner system. If banners use a `List<Widget>` that's built up and displayed in a Column, add this entry. Match the existing banner styling pattern.

#### Step 5.2.2: Verify
Run: `pwsh -Command "flutter test test/core/"`
Expected: PASS

---

### Sub-phase 5.3: main.dart Injection Sites (10 sites)
**Files:**
- Modify: `lib/main.dart:782,789,796,803,810,820,836,874,883,895`
**Agent:** general-purpose

#### Step 5.3.1: Migrate all 10 canWrite injection sites to canEditFieldData
This is a mechanical find-replace. All 10 sites follow the same pattern:

```dart
// FIND (at each of the 10 lines):
  p.canWrite = () => authProvider.canWrite;
  // OR for PhotoProvider:
  canWrite: () => authProvider.canWrite,

// REPLACE WITH:
  p.canWrite = () => authProvider.canEditFieldData;
  // OR for PhotoProvider:
  canWrite: () => authProvider.canEditFieldData,
```

// WHY: BaseListProvider.canWrite field name is kept internally (rename is Phase 8 cleanup
// consideration), but the injected value changes from the always-true canWrite to canEditFieldData
// (also always true for now, but semantically correct and future-proof).

Lines to change:
1. Line 782: LocationProvider
2. Line 789: ContractorProvider
3. Line 796: EquipmentProvider
4. Line 803: BidItemProvider
5. Line 810: DailyEntryProvider
6. Line 820: PhotoProvider
7. Line 836: PersonnelTypeProvider
8. Line 874: InspectorFormProvider
9. Line 883: CalculatorProvider
10. Line 895: TodoProvider

#### Step 5.3.2: Verify
Run: `pwsh -Command "flutter test test/"`
Expected: PASS (full test suite)

---

## Phase 6: RLS Migration
### Sub-phase 6.1: BUG-015 — Tighten Project RLS Policies
**Files:**
- Create: `supabase/migrations/20260319200000_tighten_project_rls.sql`
**Agent:** backend-supabase-agent

#### Step 6.1.1: Create migration file

**CRITICAL**: Policy names MUST match existing names exactly. The INSERT policy is named
`"company_projects_insert"` (created in `20260222100000_multi_tenant_foundation.sql:451`).
The UPDATE policy is named `"company_projects_update"` (last recreated in
`20260317100002_inspector_delete_guard.sql:12`). The DELETE policy is named
`"company_projects_delete"` (in `20260222100000`). Using wrong names will leave old
permissive policies active — PostgreSQL picks the most permissive matching policy.

```sql
-- Migration: Tighten project INSERT, UPDATE, and DELETE RLS policies (BUG-015)
-- FROM SPEC: Inspectors should NOT be able to create, update, or delete projects.
-- Previously gated by NOT is_viewer() which is always TRUE (no viewers exist).
-- Now gated by is_admin_or_engineer() (function from 20260319100000).

-- Step 1: Replace is_viewer() function body with SELECT FALSE + deprecation comment.
-- WHY: Do NOT drop is_viewer() — 70+ RLS clauses across 8 migration files reference it.
-- Replacing body is safe: existing `AND NOT is_viewer()` clauses evaluate to `AND TRUE`.
CREATE OR REPLACE FUNCTION public.is_viewer()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT FALSE;
$$;
COMMENT ON FUNCTION public.is_viewer() IS
  'DEPRECATED: Viewer role removed in 20260317. Always returns FALSE. '
  '70+ policy clauses still reference this function. Batch cleanup deferred.';

-- Step 2: Tighten INSERT policy on projects table.
-- Old (from 20260222100000:451-453): company_id = get_my_company_id() AND NOT is_viewer()
-- New: company_id = get_my_company_id() AND is_admin_or_engineer()
DROP POLICY IF EXISTS "company_projects_insert" ON public.projects;
CREATE POLICY "company_projects_insert" ON public.projects
  FOR INSERT TO authenticated
  WITH CHECK (
    company_id = get_my_company_id()
    AND is_admin_or_engineer()
  );

-- Step 3: Tighten UPDATE policy on projects table.
-- Old (from 20260317100002:14-43): complex policy with NOT is_viewer() + deleted_at guards.
-- New: Replace NOT is_viewer() with is_admin_or_engineer() while PRESERVING the
-- deleted_at / created_by_user_id / is_approved_admin() soft-delete guard clauses.
-- WHY: The soft-delete guards allow owners and admins to restore deleted projects.
-- Dropping them would prevent engineers who created a project from restoring it.
DROP POLICY IF EXISTS "company_projects_update" ON public.projects;
CREATE POLICY "company_projects_update" ON public.projects
  FOR UPDATE TO authenticated
  USING (
    company_id = get_my_company_id()
    AND is_admin_or_engineer()
    AND (
      deleted_at IS NULL
      OR created_by_user_id = auth.uid()
      OR is_approved_admin()
    )
  )
  WITH CHECK (
    company_id = get_my_company_id()
    AND is_admin_or_engineer()
    AND (
      (deleted_at IS NULL)
      OR (created_by_user_id = auth.uid() OR is_approved_admin())
    )
    AND NOT (
      deleted_at IS NOT NULL
      AND NOT (created_by_user_id = auth.uid() OR is_approved_admin())
    )
  );

-- Step 4: Tighten DELETE policy on projects table (SEC-002 finding).
-- Old (from 20260222100000): company_id = get_my_company_id() AND NOT is_viewer()
-- With is_viewer() returning FALSE, any authenticated company member could hard-delete.
-- FROM SPEC: Inspector cannot manage projects — restrict to admin/engineer.
DROP POLICY IF EXISTS "company_projects_delete" ON public.projects;
CREATE POLICY "company_projects_delete" ON public.projects
  FOR DELETE TO authenticated
  USING (
    company_id = get_my_company_id()
    AND is_admin_or_engineer()
  );
```

#### Step 6.1.2: Verify
Run: `pwsh -Command "npx supabase db diff"` (optional — validates migration syntax against local schema)
Expected: Clean diff showing only the intended changes

---

## Phase 7: Tests
### Sub-phase 7.1: Permission Model Unit Tests
**Files:**
- Create or Modify: `test/features/auth/data/models/user_role_test.dart`
**Agent:** qa-testing-agent

#### Step 7.1.1: Add tests for new permission getters
```dart
group('canManageProjects', () {
  test('admin can manage projects', () {
    expect(UserRole.admin.canManageProjects, isTrue);
  });
  test('engineer can manage projects', () {
    expect(UserRole.engineer.canManageProjects, isTrue);
  });
  test('inspector cannot manage projects', () {
    expect(UserRole.inspector.canManageProjects, isFalse);
  });
});

group('canEditFieldData', () {
  test('admin can edit field data', () {
    expect(UserRole.admin.canEditFieldData, isTrue);
  });
  test('engineer can edit field data', () {
    expect(UserRole.engineer.canEditFieldData, isTrue);
  });
  test('inspector can edit field data', () {
    expect(UserRole.inspector.canEditFieldData, isTrue);
  });
});
```

#### Step 7.1.2: Verify
Run: `pwsh -Command "flutter test test/features/auth/data/models/user_role_test.dart"`
Expected: PASS

---

### Sub-phase 7.2: Project List Widget Tests
**Files:**
- Modify: `test/features/projects/presentation/screens/project_list_screen_test.dart`
**Agent:** qa-testing-agent

#### Step 7.2.1: Add tests for permission-gated UI elements
```dart
group('Inspector permission gating', () {
  // Setup: mock AuthProvider with inspector role

  testWidgets('inspector sees edit button enabled', (tester) async {
    // FROM SPEC (BUG-008/MF-6): Edit button stays enabled for inspector.
    // canEditFieldData is true for all roles.
    // Verify: edit IconButton is enabled (onPressed is not null)
  });

  testWidgets('inspector does not see archive button', (tester) async {
    // FROM SPEC (BUG-009): Archive gated by canManageProjects.
    // Verify: archive IconButton is not in the widget tree for inspector
  });

  testWidgets('inspector cannot download unassigned project', (tester) async {
    // FROM SPEC (BUG-014): Download disabled for unassigned + inspector.
    // Verify: download action is disabled and tooltip shown
  });

  testWidgets('admin sees archive button', (tester) async {
    // Verify: archive IconButton is present and enabled for admin
  });
});

group('Tap targets (BUG-003)', () {
  testWidgets('edit button has minimum 48x48 tap target', (tester) async {
    // Verify: IconButton constraints include minWidth: 48, minHeight: 48
  });
});
```

#### Step 7.2.2: Verify
Run: `pwsh -Command "flutter test test/features/projects/presentation/screens/project_list_screen_test.dart"`
Expected: PASS

---

### Sub-phase 7.3: Sync Engine Tests
**Files:**
- Modify: `test/features/sync/engine/sync_engine_test.dart`
**Agent:** qa-testing-agent

#### Step 7.3.1: Add test for orphan cleaner guard (BUG-005)
```dart
group('BUG-005: Orphan cleaner guard', () {
  test('orphan cleaner does not run before projects adapter completes', () async {
    // Setup: Fresh database with synced_projects entries but no projects rows
    // Act: Call _loadSyncedProjectIds (via _pull or directly)
    // Verify: synced_projects entries are NOT deleted
  });

  test('orphan cleaner runs after projects adapter completes', () async {
    // Setup: Database with synced_projects entries, some not in projects table
    // Act: Simulate _pull where projects adapter runs first, then _loadSyncedProjectIds
    // Verify: Orphan entries ARE cleaned
  });

  test('synced project IDs reload after project_assignments adapter', () async {
    // Setup: project_assignments adapter pulls new entries
    // Verify: _syncedProjectIds includes newly enrolled projects
  });
});
```

#### Step 7.3.2: Add test for background retry timer (BUG-004)
```dart
group('BUG-004: Background retry', () {
  test('timer scheduled after retry exhaustion', () async {
    // Setup: Mock all DNS checks to fail
    // Act: Call _syncWithRetry
    // Verify: _backgroundRetryTimer is not null after exhaustion
  });

  test('timer cancelled at start of syncLocalAgencyProjects', () async {
    // Setup: Set _backgroundRetryTimer to a non-null Timer
    // Act: Call syncLocalAgencyProjects
    // Verify: Previous timer was cancelled
  });
});
```

#### Step 7.3.3: Verify
Run: `pwsh -Command "flutter test test/features/sync/"`
Expected: PASS

---

### Sub-phase 7.4: Details Tab Read-Only Tests
**Files:**
- Modify: `test/features/projects/presentation/screens/project_setup_screen_ui_state_test.dart`
**Agent:** qa-testing-agent

#### Step 7.4.1: Add test for inspector Details tab read-only
```dart
group('Inspector Details tab (BUG-009 defense-in-depth)', () {
  testWidgets('inspector sees ViewOnlyBanner on Details tab', (tester) async {
    // Setup: Mock AuthProvider with inspector role (canManageProjects = false)
    // Build ProjectSetupScreen with a project ID
    // Verify: ViewOnlyBanner widget is present
    // Verify: Banner text contains "managed by admins and engineers"
  });

  testWidgets('inspector does not see Save button on Details tab', (tester) async {
    // Setup: same as above
    // Verify: Save button is not in widget tree
  });

  testWidgets('admin sees Save button on Details tab', (tester) async {
    // Setup: Mock AuthProvider with admin role (canManageProjects = true)
    // Verify: Save button is present and enabled
  });
});
```

#### Step 7.4.2: Verify
Run: `pwsh -Command "flutter test test/features/projects/presentation/screens/project_setup_screen_ui_state_test.dart"`
Expected: PASS

---

## Phase 8: Bulk canWrite Migration

### Sub-phase 8.1: Migrate Remaining canWrite References Across Codebase
**Files:**
- Modify: ~24 files across `lib/` that reference `canWrite`
**Agent:** frontend-flutter-specialist-agent

#### Step 8.1.1: Categorize and migrate all remaining canWrite references

The spec identifies ~139 `canWrite` occurrences across 24 files. Phases 1-5 already handle:
- Auth model (Phase 1): new getters added
- main.dart injection (Phase 5.3): 10 sites migrated
- project_list_screen (Phase 3.3): signature change done

Remaining sites fall into two categories:
1. **Project management actions** (~15 sites): Replace `canWrite` with `canManageProjects`
   - Any guard that controls project create/archive/delete/edit-details
   - Example: `if (authProvider.canWrite)` before a `createProject()` call → `authProvider.canManageProjects`

2. **Field data actions** (~87+ sites): Replace `canWrite` with `canEditFieldData`
   - All guards on contractors, equipment, personnel types, locations, pay items, entries, photos, todos, forms
   - All `BaseListProvider` subclass internal guards (these are fed by the injection sites already migrated)
   - Example: `if (!canWrite())` in provider write guards → `if (!canWrite())` (KEEP — field name unchanged, injection already changed)

**Process**: The agent must:
1. Run `Grep for "canWrite" in lib/` (excluding auth model files already handled)
2. For each occurrence, determine if it's a project-management action or field-data action
3. Replace accordingly
4. Run `pwsh -Command "flutter analyze"` after each batch to catch compile errors

**NOTE**: Many `canWrite` references are internal to `BaseListProvider` subclasses (the `canWrite()` callback). These are already correct — they call the injected function which now delegates to `canEditFieldData`. The internal field NAME stays `canWrite` for now (renaming is optional cleanup). Only references to `authProvider.canWrite`, `userProfile.canWrite`, or `role.canWrite` need updating.

#### Step 8.1.2: Verify
Run: `pwsh -Command "flutter analyze"`
Expected: No errors

Run: `pwsh -Command "flutter test"`
Expected: All tests PASS

---

## Phase 9: Cleanup
### Sub-phase 9.1: Remove Old canWrite Getters
**Files:**
- Modify: `lib/features/auth/data/models/user_role.dart`
- Modify: `lib/features/auth/data/models/user_profile.dart`
- Modify: `lib/features/auth/presentation/providers/auth_provider.dart`
**Agent:** general-purpose

#### Step 9.1.1: Remove canWrite from UserRole
```dart
// DELETE from user_role.dart:
  bool get canWrite => true;
```

#### Step 9.1.2: Remove canWrite from UserProfile
```dart
// DELETE from user_profile.dart:
  bool get canWrite => role.canWrite;
```

#### Step 9.1.3: Remove canWrite from AuthProvider
```dart
// DELETE from auth_provider.dart:
  bool get canWrite => _userProfile?.role.canWrite ?? false;
```

#### Step 9.1.4: Update CanWriteCallback typedef in PhotoProvider
In `lib/features/photos/presentation/providers/photo_provider.dart` at line 10:

```dart
// FIND:
typedef CanWriteCallback = bool Function();

// This typedef is used internally. Verify it's still referenced. If only used for the
// canWrite field (which now maps to canEditFieldData), keep it. The name is fine — it's
// an internal implementation detail.
```

#### Step 9.1.5: Grep verify zero remaining references to authProvider.canWrite
Run: `Grep for "authProvider.canWrite" and "\.canWrite" across lib/` to find any remaining references. All should be migrated. The only remaining `canWrite` should be:
- `BaseListProvider.canWrite` field (internal, fed by `canEditFieldData`)
- `CanWriteCallback` typedef (internal)
- Provider-internal `canWrite` fields that were re-wired in Phase 5.3

Any reference to `authProvider.canWrite` or `role.canWrite` or `userProfile.canWrite` must be migrated.

#### Step 9.1.6: Verify full build
Run: `pwsh -Command "flutter analyze"`
Expected: No errors (warnings acceptable)

Run: `pwsh -Command "flutter test"`
Expected: All tests PASS

---

## Summary

| Phase | Bugs Fixed | Files Changed | Risk |
|-------|-----------|---------------|------|
| 1. Permission Model | BUG-012 | 3 | Low — additive only |
| 2. Sync Engine | BUG-002, BUG-004, BUG-005 | 2 | Medium — sync logic |
| 3. Project List Screen | BUG-001, BUG-003, BUG-006, BUG-008, BUG-009, BUG-014 | 2 | Medium — many touch points |
| 4. Setup & Dashboard | BUG-011 | 3 | Low |
| 5. Router & Integration | BUG-007, BUG-006 (offline indicator) | 3 | Low — additive |
| 6. RLS Migration | BUG-015 | 1 (new) | High — production DB |
| 7. Tests | — | 4+ | Low |
| 8. Bulk canWrite Migration | — | ~24 | Medium — many sites |
| 9. Cleanup | — | 3 | Medium — compile-time break |

**Total:** 13 bugs fixed, ~30 files modified, 1 new migration, 4+ test files updated.

## Review Findings Addressed

| Finding | Severity | Resolution |
|---------|----------|------------|
| RLS policy names were placeholders | CRITICAL | Fixed: exact names `company_projects_insert/update/delete` |
| UPDATE policy dropped soft-delete guards | CRITICAL | Fixed: preserved `deleted_at`/`created_by_user_id`/`is_approved_admin()` clauses |
| DELETE policy not tightened | CRITICAL | Fixed: added Step 4 in migration |
| Timer callback missing async + DNS check | HIGH | Fixed: `async` callback with `checkDnsReachability()` guard |
| Missing bulk canWrite migration | HIGH | Fixed: added Phase 8 |
| `_checkNetwork` async conversion breaks caller | HIGH | Fixed: dual sync/async methods, explicit `_handleImport` fix |
| Orphan cleaner snippet unclosed braces | HIGH | Fixed: complete brace structure shown |
| Route guard before profile null check | HIGH | Fixed: placed inside `if (profile != null)` block |
| `toggleActive()` no provider guard | MEDIUM | Fixed: added `_canManageProjects` callback + guard |
| Timer use-after-dispose | MEDIUM | Fixed: `_disposed` flag guard |
| No Details tab read-only test | MEDIUM | Fixed: added Sub-phase 7.4 |
| No-op Sub-phase 2.3 | MEDIUM | Fixed: removed |
