# Project Management E2E Fix Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Fix the broken project management lifecycle end-to-end: crash on missing Provider, remove auto-enrollment from background sync, add role-based permissions, rewrite project list UI with two sections, add download confirmation, immediate push on create, photo file cleanup, orphan cleanup, full logging, and comprehensive tests.

**Spec:** `.claude/specs/2026-03-17-project-management-e2e-spec.md`

**Architecture:** Screen -> Provider -> Repository -> SQLite (local) -> Supabase (sync)
**Tech Stack:** Flutter, SQLite, Supabase, Provider
**Blast Radius:** 14 direct files, 8 dependent, 7 test updates, 3 new test files, 3 SQL migrations

---

## Phase 1: Provider Fix + Role Changes
> Unblocks everything. P0 crash fix + role enum changes.

### Sub-phase 1.1: Register SyncOrchestrator Provider
**Files:** `lib/main.dart`
**Agent:** backend-data-layer-agent

#### Step 1.1.1: Add `Provider<SyncOrchestrator>.value()` to MultiProvider tree

In `lib/main.dart`, inside `ConstructionInspectorApp.build()`, add the SyncOrchestrator provider. Insert it before the SyncProvider (line ~720).

```dart
// In the providers list, BEFORE the SyncProvider ChangeNotifierProvider:
// ... existing Provider<SyncRegistry>.value(value: SyncRegistry.instance), at ~line 713

// WHY: P0 FIX — project_list_screen.dart calls context.read<SyncOrchestrator>()
// in 3 places. Without this registration, the app crashes with ProviderNotFoundException.
Provider<SyncOrchestrator>.value(value: syncOrchestrator),

// ... existing ChangeNotifierProvider for PersonnelTypeProvider at ~line 714
```

Insert `Provider<SyncOrchestrator>.value(value: syncOrchestrator),` after line 713 (`Provider<SyncRegistry>.value(value: SyncRegistry.instance),`) and before line 714 (`ChangeNotifierProvider(create: (_) { final p = PersonnelTypeProvider(...)`).

---

### Sub-phase 1.2: Remove `viewer` from UserRole enum
**Files:** `lib/features/auth/data/models/user_role.dart`
**Agent:** auth-agent

#### Step 1.2.1: Remove the `viewer` enum value and update methods

Replace the entire `UserRole` enum in `lib/features/auth/data/models/user_role.dart` (lines 5-52):

```dart
/// User roles within a company.
///
/// Must match the Supabase CHECK constraint:
/// `role IN ('admin','engineer','inspector')`.
enum UserRole {
  /// Administrator — can manage company, approve/reject members.
  admin,

  /// Engineer — can read and write data (senior field role).
  engineer,

  /// Inspector — can read and write data (standard field role).
  inspector;

  /// Display label for the role.
  String get displayName {
    switch (this) {
      case UserRole.admin:
        return 'Admin';
      case UserRole.engineer:
        return 'Engineer';
      case UserRole.inspector:
        return 'Inspector';
    }
  }

  /// Whether this user has admin role.
  bool get isAdmin => this == admin;

  /// Whether this user is an engineer.
  bool get isEngineer => this == engineer;

  /// Whether this user can write data.
  /// NOTE: With viewer removed, all 3 remaining roles can write.
  /// FROM SPEC (MF-3): Keep canWrite — 102 occurrences across 24 files depend on it.
  bool get canWrite => true;

  /// Parse from a raw string value (DB/API).
  /// WHY: 'viewer' falls back to 'inspector' for transition period (MF-6).
  static UserRole fromString(String value) {
    switch (value.toLowerCase()) {
      case 'admin':
        return UserRole.admin;
      case 'engineer':
        return UserRole.engineer;
      case 'viewer':
        // FROM SPEC: Viewer -> Inspector fallback during migration transition
        return UserRole.inspector;
      case 'inspector':
      default:
        return UserRole.inspector;
    }
  }
}
```

---

### Sub-phase 1.3: Add role-specific permission methods to AuthProvider
**Files:** `lib/features/auth/presentation/providers/auth_provider.dart`
**Agent:** auth-agent

#### Step 1.3.1: Remove `isViewer` getter and update `canWrite`

In `lib/features/auth/presentation/providers/auth_provider.dart`, replace lines 180-184:

OLD:
```dart
  /// Whether the current user can write data (not a viewer).
  bool get canWrite => _userProfile?.role != UserRole.viewer;

  /// Whether the current user is a viewer.
  bool get isViewer => _userProfile?.role == UserRole.viewer;
```

NEW:
```dart
  /// Whether the current user can write data.
  /// FROM SPEC (MF-3): With viewer removed, all 3 roles can write.
  /// Kept for backward compatibility — 24 files depend on canWrite.
  bool get canWrite => _userProfile?.role?.canWrite ?? false;

  /// Whether the current user is an engineer.
  bool get isEngineer => _userProfile?.role == UserRole.engineer;
```

#### Step 1.3.2: Add project-specific permission methods

After the `isEngineer` getter (new from Step 1.3.1), add:

```dart
  // ============================================================
  // Project Permission Methods (FROM SPEC Section 4)
  // ============================================================

  /// Whether the current user can create projects.
  /// FROM SPEC: Admin and Engineer only.
  bool get canCreateProject =>
      _userProfile?.role == UserRole.admin ||
      _userProfile?.role == UserRole.engineer;

  /// Whether the current user can delete a specific project.
  /// FROM SPEC: Admin can delete any, Engineer can delete own only.
  /// [createdByUserId] is the project's created_by_user_id from SQLite.
  bool canDeleteProject({required String? createdByUserId}) {
    if (isAdmin) return true;
    if (isEngineer && createdByUserId != null && createdByUserId == userId) {
      return true;
    }
    return false;
  }

  /// Whether the current user can edit a specific project.
  /// FROM SPEC: Admin/Engineer can edit all, Inspector can edit assigned.
  /// NOTE: Assignment check is deferred — for now, all roles with canWrite can edit.
  bool get canEditProject => canWrite;
```

---

### Sub-phase 1.4: Fix `isViewer` references across codebase
**Files:** Search for `isViewer` usage across codebase
**Agent:** auth-agent

#### Step 1.4.1: Audit and update all `isViewer` references

Search for ALL occurrences of `isViewer` in `lib/`. Each occurrence should either:
- Be removed (if guarding viewer-specific behavior — viewer no longer exists)
- Be replaced with the appropriate new check

**CRITICAL (CR-CRIT-2):** Known locations that MUST be updated:

1. `lib/features/auth/presentation/providers/auth_provider.dart:184` — already handled in 1.3.1
2. `lib/features/auth/data/models/user_profile.dart:67` — `bool get isViewer => role == UserRole.viewer;` — REMOVE (compile error after viewer removed)
3. **`lib/features/entries/presentation/screens/entry_editor_screen.dart`** — **13 occurrences** (lines 639, 660, 690, 748, 807, 869, 875, 1094, 1099, 1126, 1133, 1167). These use `isViewer` to gate edit interactions (location edit, weather edit, personnel, quantities, etc.). Since viewer no longer exists, replace all `isViewer` checks with `false` (or simply remove the conditional — all 3 roles can edit).
4. `lib/features/settings/presentation/providers/admin_provider.dart` — check if it references `isViewer`
5. `lib/features/auth/presentation/screens/pending_approval_screen.dart` — check
6. `lib/features/projects/presentation/widgets/view_only_banner.dart` — check (may have commented reference)

For each file, if `isViewer` is used as a guard to disable features, remove the guard since viewer role no longer exists. The `isViewer` property on `AuthProvider` should be removed entirely (Step 1.3.1 already handles this).

**Pattern for entry_editor_screen.dart:** Replace all occurrences of:
```dart
if (isViewer) return; // or similar guard
```
with simply removing the guard (all roles can write).

---

## Phase 2: Supabase Migrations
> Three SQL migration files + push to remote.

### Sub-phase 2.1: Remove viewer role migration
**Files:** `supabase/migrations/20260317100000_remove_viewer_role.sql` (NEW)
**Agent:** backend-supabase-agent

#### Step 2.1.1: Create migration file

```sql
-- Migration: Remove viewer role from user_profiles
-- FROM SPEC Section 2 + MF-6: Convert viewer -> inspector, update constraints and RPCs

-- Step 1: Convert existing viewer rows to inspector
UPDATE user_profiles SET role = 'inspector' WHERE role = 'viewer';

-- Step 2: Update CHECK constraint to remove 'viewer'
ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS user_profiles_role_check;
ALTER TABLE user_profiles ADD CONSTRAINT user_profiles_role_check
  CHECK (role IN ('admin', 'engineer', 'inspector'));

-- Step 3: Update approve_join_request RPC to reject 'viewer'
-- WHY (MF-6): Without this, an admin could still approve someone as 'viewer'
-- IMPORTANT (CR-CRIT-1): Parameter names MUST match existing signature exactly:
-- request_id UUID, assigned_role TEXT DEFAULT 'inspector'
-- (from 20260305000000_schema_alignment_and_security.sql:211-241)
-- Minimal change: only update the role validation line to exclude 'viewer'
CREATE OR REPLACE FUNCTION approve_join_request(
  request_id UUID,
  assigned_role TEXT DEFAULT 'inspector'
)
RETURNS void AS $$
DECLARE
  v_user_id UUID;
  v_company_id UUID;
BEGIN
  -- Validate role — 'viewer' removed (was previously allowed)
  IF assigned_role NOT IN ('inspector', 'engineer') THEN
    RAISE EXCEPTION 'Invalid role: %', assigned_role;
  END IF;

  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Only admins can approve requests';
  END IF;

  SELECT user_id, company_id INTO v_user_id, v_company_id
  FROM company_join_requests
  WHERE id = request_id AND company_id = get_my_company_id() AND status = 'pending';

  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'Request not found or not pending';
  END IF;

  UPDATE user_profiles
  SET role = assigned_role, status = 'approved', company_id = v_company_id, updated_at = NOW()
  WHERE user_id = v_user_id;

  UPDATE company_join_requests
  SET status = 'approved', resolved_by = auth.uid(), resolved_at = NOW()
  WHERE id = request_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Step 4: Update update_member_role RPC to reject 'viewer'
-- IMPORTANT (CR-CRIT-1): Parameter names MUST match existing signature:
-- target_user_id UUID, new_role TEXT
CREATE OR REPLACE FUNCTION update_member_role(
  target_user_id UUID,
  new_role TEXT
)
RETURNS void AS $$
BEGIN
  IF new_role NOT IN ('admin', 'engineer', 'inspector') THEN
    RAISE EXCEPTION 'Invalid role: %. Must be admin, engineer, or inspector.', new_role;
  END IF;

  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Only admins can change roles';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM user_profiles
    WHERE user_id = target_user_id AND company_id = get_my_company_id()
  ) THEN
    RAISE EXCEPTION 'User not found in your company';
  END IF;

  IF target_user_id = auth.uid() AND new_role != 'admin' THEN
    RAISE EXCEPTION 'Cannot change your own admin role';
  END IF;

  UPDATE user_profiles SET role = new_role, updated_at = NOW()
  WHERE user_id = target_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- TODO (NH-1): is_viewer() now always returns false since no viewer role exists.
-- Remove from all RLS policies in a future migration.
```

---

### Sub-phase 2.2: Admin soft-delete RPC
**Files:** `supabase/migrations/20260317100001_admin_soft_delete_rpc.sql` (NEW)
**Agent:** backend-supabase-agent

#### Step 2.2.1: Create RPC migration

```sql
-- Migration: Admin-only soft-delete RPC for remote projects
-- FROM SPEC Section 5 + MF-5: SECURITY DEFINER prevents column manipulation

CREATE OR REPLACE FUNCTION admin_soft_delete_project(p_project_id TEXT)
RETURNS void AS $$
BEGIN
  -- WHY (MF-5): SECURITY DEFINER RPC validates admin role server-side.
  -- Prevents raw UPDATE that could manipulate arbitrary columns.
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Only admins can delete projects remotely';
  END IF;

  -- Verify project belongs to caller's company
  IF NOT EXISTS (
    SELECT 1 FROM projects
    WHERE id = p_project_id AND company_id = get_my_company_id()
  ) THEN
    RAISE EXCEPTION 'Project not found or not in your company';
  END IF;

  -- Soft-delete the project
  UPDATE projects
  SET deleted_at = NOW(), deleted_by = auth.uid()::text, updated_at = NOW()
  WHERE id = p_project_id;

  -- Audit log
  RAISE LOG 'admin_soft_delete_project: project=% by=%', p_project_id, auth.uid();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
```

---

### Sub-phase 2.3: Inspector delete guard
**Files:** `supabase/migrations/20260317100002_inspector_delete_guard.sql` (NEW)
**Agent:** backend-supabase-agent

#### Step 2.3.1: Create inspector guard migration

```sql
-- Migration: Prevent inspectors from soft-deleting projects via direct UPDATE
-- FROM SPEC Section 10 + MF-4: Inspector can't set deleted_at on projects

-- NOTE: This adds a WITH CHECK clause to the existing projects UPDATE policy.
-- The implementer must verify the existing policy name from earlier migrations.
-- Expected policy: projects_update_policy or similar.

-- Drop and recreate with WITH CHECK that blocks inspector soft-delete
-- WHY (MF-4): Spec says Inspector: No delete. RLS must enforce this.

DO $$
DECLARE
  v_policy_name text;
BEGIN
  -- Find the existing update policy for projects
  SELECT policyname INTO v_policy_name
  FROM pg_policies
  WHERE tablename = 'projects'
    AND cmd = 'UPDATE'
  LIMIT 1;

  IF v_policy_name IS NOT NULL THEN
    EXECUTE format('DROP POLICY IF EXISTS %I ON projects', v_policy_name);
  END IF;

  -- Recreate with inspector guard
  CREATE POLICY projects_update_policy ON projects
    FOR UPDATE
    USING (
      company_id = get_my_company_id()
      AND is_approved_member()
    )
    WITH CHECK (
      company_id = get_my_company_id()
      AND is_approved_member()
      -- FROM SPEC (MF-4): Block inspectors from setting deleted_at
      -- IMPORTANT (SEC-CRIT-1): get_my_role() does NOT exist. Use inline subquery instead.
      AND NOT (
        EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role = 'inspector' AND status = 'approved')
        AND deleted_at IS NOT NULL
      )
    );
END $$;
```

**NOTE:** The implementer must verify the exact existing policy name and USING clause from the migration files. The inline subquery replaces `get_my_role()` which does not exist in the codebase.

---

### Sub-phase 2.4: Push migrations
**Agent:** backend-supabase-agent

#### Step 2.4.1: Push all three migrations

```bash
npx supabase db push
```

Create corresponding rollback files in `supabase/rollbacks/` for each migration.

---

## Phase 3: Sync Engine Changes
> Remove auto-enrollment, add logging, orphan cleanup.

### Sub-phase 3.1: Remove auto-enrollment from `_pullTable()`
**Files:** `lib/features/sync/engine/sync_engine.dart`
**Agent:** backend-data-layer-agent

#### Step 3.1.1: Remove BLOCKER-38 auto-enrollment code

In `lib/features/sync/engine/sync_engine.dart`, at lines 1082-1089, **delete** the auto-enrollment block inside `_pullTable()`:

```dart
// DELETE these lines (1082-1089):
            // WHY: BLOCKER-38 — pulled projects must be enrolled so child adapters can sync their data.
            if (adapter.tableName == 'projects') {
              await db.insert('synced_projects', {
                'project_id': recordId,
                'synced_at': DateTime.now().toUtc().toIso8601String(),
              }, conflictAlgorithm: ConflictAlgorithm.ignore);
              Logger.sync('Auto-enrolled pulled project: $recordId');
            }
```

The surrounding code should become:

```dart
          if (rowId == 0) {
            Logger.sync('Pull insert ignored (constraint conflict): ${adapter.tableName}/$recordId');
          } else {
            totalPulled++;
            // WHY: Auto-enrollment removed per spec — background sync pulls metadata only.
            // User must explicitly confirm download to enroll in synced_projects.
          }
```

---

### Sub-phase 3.2: Keep `_loadSyncedProjectIds()` reload, remove only auto-enrollment log
**Files:** `lib/features/sync/engine/sync_engine.dart`
**Agent:** backend-data-layer-agent

#### Step 3.2.1: Keep the reload block — only update the log message

**IMPORTANT (CR-HIGH-5):** Do NOT remove the `_loadSyncedProjectIds()` reload from `_pull()`. This reload is necessary so that child adapters (locations, entries, etc.) see newly-enrolled projects from the user's import action. The auto-enrollment INSERT was removed in Sub-phase 3.1, but the reload must stay so that if a user enrolls a project via the UI and background sync runs, the child adapters pick up the new project ID.

In `_pull()` at lines 977-981, **keep** the block but update the log message:

```dart
          // KEEP these lines — reload is necessary for child adapter scoping
          if (adapter.tableName == 'projects' && count > 0) {
            await _loadSyncedProjectIds();
            Logger.sync('Reloaded synced project IDs after pulling $count projects (enrollment unchanged)');
          }
```

---

### Sub-phase 3.3: Add logging to `_handlePushError()`
**Files:** `lib/features/sync/engine/sync_engine.dart`
**Agent:** backend-data-layer-agent

#### Step 3.3.1: Add Logger.sync calls for each error category

In `_handlePushError()` (line 824+), add logging for each branch. The existing code already has some logging (e.g., `Logger.error('RLS DENIED...')` at line 880). Add for the missing categories:

After the 23505 constraint block (line 861-874), the code already handles it. Add explicit logging:

```dart
      // Constraint violation (23505): retryable if TOCTOU race
      if (code == '23505') {
        // FROM SPEC Section 8: Error categorization logging
        Logger.sync('CONSTRAINT 23505: ${change.tableName}/${change.recordId}');
        // ... existing retry logic unchanged ...
      }
```

After the 23503 FK violation block (line 887-893), add:

```dart
      // FK violation (23503): permanent — parent record missing
      if (code == '23503') {
        // FROM SPEC Section 8: Error categorization logging
        Logger.sync('FK VIOLATION 23503: ${change.tableName}/${change.recordId}');
        // ... existing markFailed unchanged ...
      }
```

For 429/503 (line 840-856), add:

```dart
      // Rate limit / service unavailable
      if (code.contains('429') || ...) {
        // FROM SPEC Section 8: Error categorization logging
        Logger.sync('RATE LIMITED: ${change.tableName}/${change.recordId}');
        // ... existing backoff logic unchanged ...
      }
```

For SocketException/TimeoutException (line 903-915), add:

```dart
    if (error is SocketException || error is TimeoutException) {
      // FROM SPEC Section 8: Error categorization logging
      Logger.sync('NETWORK ERROR: ${change.tableName}/${change.recordId}: $error');
      // ... existing backoff logic unchanged ...
    }
```

#### Step 3.3.2: Add `_handleAuthError` logging

In `_handleAuthError()` (line 930), add logging for auth refresh attempts (FROM SPEC Section 8 HIGH):

```dart
  Future<bool> _handleAuthError() async {
    try {
      await supabase.auth.refreshSession();
      // FROM SPEC Section 8: Auth refresh logging
      Logger.auth('Auth refresh attempted: success=true');
      return true;
    } catch (e) {
      Logger.auth('Auth refresh attempted: success=false error=$e');
      return false;
    }
  }
```

---

### Sub-phase 3.4: Add push/pull summary logging
**Files:** `lib/features/sync/engine/sync_engine.dart`
**Agent:** backend-data-layer-agent

#### Step 3.4.1: Add summary logging in `pushAndPull()`

In `pushAndPull()` (line 164), after `final pushResult = await _push();` (line 195), add:

```dart
      final pushResult = await _push();
      // FROM SPEC Section 8: Push summary logging
      Logger.sync('Push complete: ${pushResult.pushed} pushed, ${pushResult.errors} errors, $_rlsDenialCount RLS denials');
```

After `final pullResult = await _pull();` (line 204), add:

```dart
      final pullResult = await _pull();
      // FROM SPEC Section 8: Pull summary logging
      Logger.sync('Pull complete: ${pullResult.pulled} pulled, ${pullResult.errors} errors');
```

#### Step 3.4.2: Add overall cycle summary with duration timing

Wrap the entire sync body in a stopwatch. At the top of `pushAndPull()`, after the mutex acquisition (line 185):

```dart
    _insidePushOrPull = true;
    final stopwatch = Stopwatch()..start(); // FROM SPEC: duration timing
```

In the `return` statement (line 236), replace:

```dart
      return pushResult + pullResult;
```

with:

```dart
      stopwatch.stop();
      final combined = pushResult + pullResult;
      // FROM SPEC Section 8: Overall sync cycle summary
      Logger.sync('Sync cycle: pushed=${combined.pushed} pulled=${combined.pulled} errors=${combined.errors} duration=${stopwatch.elapsedMilliseconds}ms');
      return combined;
```

---

### Sub-phase 3.5: Add orphaned synced_projects cleanup
**Files:** `lib/features/sync/engine/sync_engine.dart`
**Agent:** backend-data-layer-agent

#### Step 3.5.1: Add orphan cleanup to `_loadSyncedProjectIds()`

In `_loadSyncedProjectIds()` (line 1187), add orphan cleanup after loading:

```dart
  Future<void> _loadSyncedProjectIds() async {
    final rows = await db.query('synced_projects');
    _syncedProjectIds =
        rows.map((r) => r['project_id'] as String).toList();

    // FROM SPEC (SC-2): Clean orphaned synced_projects entries
    // WHY: If a project was deleted remotely and pulled as soft-deleted,
    // or hard-deleted and purged, the synced_projects entry becomes orphaned.
    if (_syncedProjectIds.isNotEmpty) {
      final placeholders = _syncedProjectIds.map((_) => '?').join(',');
      final existingProjects = await db.query(
        'projects',
        columns: ['id'],
        where: 'id IN ($placeholders)',
        whereArgs: _syncedProjectIds,
      );
      final existingIds = existingProjects.map((r) => r['id'] as String).toSet();
      final orphanIds = _syncedProjectIds.where((id) => !existingIds.contains(id)).toList();
      if (orphanIds.isNotEmpty) {
        for (final orphanId in orphanIds) {
          await db.delete('synced_projects', where: 'project_id = ?', whereArgs: [orphanId]);
        }
        Logger.sync('Cleaned ${orphanIds.length} orphaned synced_projects entries');
        // Reload after cleanup
        _syncedProjectIds = _syncedProjectIds.where((id) => existingIds.contains(id)).toList();
      }

      // Load contractors for synced projects (existing logic)
      final contractors = await db.query(
        'contractors',
        columns: ['id'],
        where:
            'project_id IN ($placeholders) AND deleted_at IS NULL',
        whereArgs: _syncedProjectIds,
      );
      _syncedContractorIds =
          contractors.map((r) => r['id'] as String).toList();
    } else {
      _syncedContractorIds = [];
    }
  }
```

---

## Phase 4: ProjectProvider + ProjectLifecycleService
> Replace Supabase query with local SQLite, add remote delete method.

### Sub-phase 4.1: Replace `fetchRemoteProjects()` with local SQLite query
**Files:** `lib/features/projects/presentation/providers/project_provider.dart`
**Agent:** backend-data-layer-agent

#### Step 4.1.1: Rewrite `fetchRemoteProjects()` to use local SQLite

Replace the entire `fetchRemoteProjects()` method (lines 444-465) with:

```dart
  /// Refresh the merged project view from local SQLite data.
  ///
  /// FROM SPEC (SC-1): Available Projects comes from local SQLite,
  /// not a Supabase query. Pull-to-refresh triggers sync for freshness.
  /// All company projects are already pulled by background sync as metadata
  /// (ProjectAdapter has ScopeType.direct).
  Future<void> fetchRemoteProjects() async {
    final companyId = _companyId;
    if (companyId == null) return;

    try {
      // Reload local projects
      _projects = await _repository.getByCompanyId(companyId);

      // FROM SPEC: Available = projects NOT in synced_projects AND not deleted
      // These are already in local SQLite from background sync pull.
      final db = await _databaseService.database;
      final enrolledRows = await db.query('synced_projects');
      final enrolledIds = enrolledRows.map((r) => r['project_id'] as String).toSet();

      // FROM SPEC (SC-6): Reduce metadata columns for available projects
      final allProjectRows = await db.query(
        'projects',
        columns: ['id', 'name', 'project_number', 'company_id', 'is_active', 'updated_at'],
        where: 'company_id = ? AND deleted_at IS NULL',
        whereArgs: [companyId],
      );

      _remoteProjects = allProjectRows
          .where((row) => !enrolledIds.contains(row['id'] as String))
          .map((row) => Project(
                id: row['id'] as String,
                name: row['name'] as String? ?? '',
                projectNumber: row['project_number'] as String? ?? '',
                companyId: row['company_id'] as String?,
                isActive: (row['is_active'] as int?) == 1,
                updatedAt: row['updated_at'] != null
                    ? DateTime.tryParse(row['updated_at'] as String) ?? DateTime.now()
                    : DateTime.now(),
              ))
          .toList();

      _buildMergedView();
      notifyListeners();
    } catch (e) {
      Logger.sync('FETCH_LOCAL_PROJECTS_ERROR: $e');
      // NOTE: Don't clear existing data on error — show stale merged view
    }
  }
```

---

### Sub-phase 4.2: Add `deleteFromSupabase()` to ProjectLifecycleService
**Files:** `lib/features/projects/data/services/project_lifecycle_service.dart`
**Agent:** backend-data-layer-agent

#### Step 4.2.1: Add remote-only delete method

Add after `canDeleteFromDatabase()` (after line 298):

```dart
  /// Delete a project remotely via Supabase SECURITY DEFINER RPC.
  /// FROM SPEC Section 5 + MF-5: Admin-only, prevents column manipulation.
  ///
  /// [isAdmin] is a client-side defense-in-depth check (SC-7).
  /// The RPC validates admin role server-side.
  Future<void> deleteFromSupabase(String projectId, {required bool isAdmin}) async {
    if (projectId.trim().isEmpty) {
      throw ArgumentError('projectId must not be empty');
    }
    // FROM SPEC (SC-7): Client-side admin guard
    if (!isAdmin) {
      throw StateError('Only admins can delete remote-only projects');
    }

    // WHY: Import required at top of file
    // NOTE: Add `import 'package:supabase_flutter/supabase_flutter.dart';` to file imports
    await Supabase.instance.client.rpc(
      'admin_soft_delete_project',
      params: {'p_project_id': projectId},
    );

    // Remove from local SQLite metadata cache
    await _db.delete('projects', where: 'id = ?', whereArgs: [projectId]);

    Logger.sync('REMOTE_DELETE projectId=$projectId');
  }
```

Also add `import 'package:supabase_flutter/supabase_flutter.dart';` to the imports section of the file.

#### Step 4.2.2: Add step-by-step logging in `removeFromDevice()`

In `removeFromDevice()`, add logging at each step. Before the transaction (after the unsynced check, ~line 94):

```dart
    Logger.sync('Remove step 1: starting removeFromDevice projectId=$projectId force=$forceOfflineRemoval');
```

Before the return (at line 239):

```dart
    Logger.sync('Remove step FINAL: completed removeFromDevice projectId=$projectId photoPaths=${photoPaths.length}');
```

#### Step 4.2.3: Add `canDeleteFromDatabase()` result logging

In `canDeleteFromDatabase()` (line 275), add logging before the return:

```dart
  Future<bool> canDeleteFromDatabase(
    String projectId,
    String currentUserId, {
    required bool isAdmin,
  }) async {
    // ... existing validation ...

    final rows = await _db.query(
      'projects',
      columns: ['created_by_user_id'],
      where: 'id = ?',
      whereArgs: [projectId],
    );

    if (rows.isEmpty) {
      Logger.sync('Delete permission: $projectId allowed=false (not found)');
      return false;
    }

    final createdBy = rows.first['created_by_user_id'] as String?;
    if (createdBy == null || createdBy.isEmpty) {
      Logger.sync('Delete permission: $projectId allowed=$isAdmin (no creator, admin=$isAdmin)');
      return isAdmin; // NOTE: was returning false; admin should be able to delete ownerless projects
    }
    final result = createdBy == currentUserId;
    Logger.sync('Delete permission: $projectId allowed=$result (creator=$createdBy, current=$currentUserId)');
    return result;
  }
```

**WAIT**: The original code returns `false` for null/empty `createdBy` even if not admin, but the admin check is at the top. So this is fine — admin returns `true` at line 283 before reaching this. Just add the logging lines.

---

## Phase 5: SoftDeleteService — synced_projects cleanup
> Clean up synced_projects when a project is soft-deleted.

### Sub-phase 5.1: Add synced_projects deletion
**Files:** `lib/services/soft_delete_service.dart`
**Agent:** backend-data-layer-agent

#### Step 5.1.1: Add synced_projects cleanup after cascade soft-delete

In `cascadeSoftDeleteProject()` (line 50), after the transaction closes (line 137, after `});`), add:

```dart
    });

    // FROM SPEC Section 5: Remove from synced_projects so project stops participating in sync
    // WHY: Outside the transaction because synced_projects is an enrollment table,
    // not a data table. If the transaction fails, enrollment should remain.
    try {
      await _db.delete('synced_projects', where: 'project_id = ?', whereArgs: [projectId]);
    } catch (e) {
      Logger.db('SYNCED_PROJECTS_CLEANUP error for project=$projectId: $e');
    }

    Logger.db('CASCADE_SOFT_DELETE project=$projectId');
```

Remove the existing `Logger.db('CASCADE_SOFT_DELETE project=$projectId');` at line 139 since it's now part of the new block.

---

## Phase 6: ProjectSetupScreen — Creation Flow
> Immediate push when online, draft prompt on back navigation.

### Sub-phase 6.1: Immediate push on project creation
**Files:** `lib/features/projects/presentation/screens/project_setup_screen.dart`
**Agent:** frontend-flutter-specialist-agent

#### Step 6.1.1: Add SyncOrchestrator import

Add to the imports at the top of `project_setup_screen.dart`:

```dart
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
```

#### Step 6.1.2: Fire-and-forget push after enrollment

In `_saveProject()`, after the successful synced_projects enrollment block (after line 857, before `// Note: No need to reload providers`), add:

```dart
      // FROM SPEC Section 5: Immediate push on project creation
      // WHY: Prevents orphaned children. Non-blocking with banner.
      if (success) {
        try {
          final orchestrator = context.read<SyncOrchestrator>();
          if (orchestrator.isSupabaseOnline) {
            // FROM SPEC: Fire-and-forget push — navigate immediately, push in background
            // Uses syncLocalAgencyProjects which follows SyncRegistry adapter ordering (MF-4 security)
            orchestrator.syncLocalAgencyProjects();
            Logger.sync('Immediate push triggered after project creation: $_projectId');
          } else {
            // FROM SPEC (MF-1): Offline — defer push to next sync cycle, no error shown
            Logger.sync('Project created offline, push deferred: $_projectId');
          }
        } catch (e) {
          // Non-critical: project is saved locally, sync will catch up
          Logger.sync('Immediate push failed (non-critical): $e');
        }
      }
```

---

### Sub-phase 6.2: Draft save/discard prompt on back navigation
**Files:** `lib/features/projects/presentation/screens/project_setup_screen.dart`
**Agent:** frontend-flutter-specialist-agent

#### Step 6.2.1: Rewrite `_handleBackNavigation()` with draft prompt

Replace `_handleBackNavigation()` (lines 223-230) and `_handleBackButton()` (lines 232-234):

```dart
  Future<bool> _handleBackNavigation() async {
    // FROM SPEC: Edit mode — just navigate back, no prompt needed
    if (isEditing) {
      if (context.canPop()) {
        context.pop();
      } else {
        context.goNamed('projects');
      }
      return false;
    }

    // FROM SPEC: New project — prompt save/discard if any data entered
    final hasData = _nameController.text.isNotEmpty ||
        _numberController.text.isNotEmpty ||
        _clientController.text.isNotEmpty ||
        _descriptionController.text.isNotEmpty;

    if (!hasData) {
      // No data entered — discard the empty draft row
      await _discardDraft();
      if (mounted) {
        if (context.canPop()) {
          context.pop();
        } else {
          context.goNamed('projects');
        }
      }
      return false;
    }

    // Show save/discard prompt
    if (!mounted) return false;
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Save as Draft?'),
        content: const Text(
          'You have unsaved changes. Would you like to save this project as a draft or discard it?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, 'discard'),
            child: const Text('Discard'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, 'save'),
            child: const Text('Save Draft'),
          ),
        ],
      ),
    );

    if (!mounted) return false;

    if (result == 'discard') {
      await _discardDraft();
      if (mounted) {
        if (context.canPop()) {
          context.pop();
        } else {
          context.goNamed('projects');
        }
      }
    } else if (result == 'save') {
      // Save draft — just navigate back, the draft row already exists
      // FROM SPEC: Draft shown in "My Projects" with [Draft] badge
      if (context.canPop()) {
        context.pop();
      } else {
        context.goNamed('projects');
      }
    }
    // result == null means dialog dismissed — stay on screen
    return false;
  }

  /// Discard the draft project row and all child records.
  Future<void> _discardDraft() async {
    if (!_projectInserted || _projectId == null) return;
    try {
      final db = await context.read<DatabaseService>().database;
      // Suppress triggers for draft cleanup
      await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
      try {
        // Delete children first (FK order)
        for (final table in ['equipment', 'bid_items', 'contractors', 'locations', 'personnel_types']) {
          await db.delete(table, where: 'project_id = ?', whereArgs: [_projectId]);
        }
        await db.delete('projects', where: 'id = ?', whereArgs: [_projectId]);
        // Clean any change_log entries
        await db.delete('change_log', where: 'project_id = ?', whereArgs: [_projectId]);
        await db.delete('change_log', where: "table_name = 'projects' AND record_id = ?", whereArgs: [_projectId]);
      } finally {
        await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
      }
      Logger.ui('Draft discarded: $_projectId');
    } catch (e) {
      Logger.ui('Draft discard failed: $e');
    }
  }

  void _handleBackButton() {
    _handleBackNavigation();
  }
```

---

## Phase 7: ProjectListScreen Rewrite
> Two sections, download dialog, role perms, photo cleanup, admin remote delete.

### Sub-phase 7.1: Project list screen rewrite
**Files:** `lib/features/projects/presentation/screens/project_list_screen.dart`
**Agent:** frontend-flutter-specialist-agent

This is the most significant UI change. The key modifications are:

#### Step 7.1.1: Update `_refresh()` to trigger sync instead of Supabase query

Replace `_refresh()` (lines 36-39):

```dart
  Future<void> _refresh() async {
    if (!mounted) return;
    // FROM SPEC (SC-5): Refresh role on screen open
    await context.read<AuthProvider>().refreshUserProfile();
    // FROM SPEC: Pull-to-refresh triggers sync for freshness
    try {
      final orchestrator = context.read<SyncOrchestrator>();
      if (orchestrator.isSupabaseOnline) {
        await orchestrator.syncLocalAgencyProjects();
      }
    } catch (e) {
      Logger.sync('Refresh sync failed: $e');
    }
    if (!mounted) return;
    // Rebuild merged view from local data
    await context.read<ProjectProvider>().fetchRemoteProjects();
  }
```

#### Step 7.1.2: Add download confirmation dialog

Add this method after `_handleImport()`:

```dart
  /// FROM SPEC: Download confirmation dialog before import
  Future<void> _showDownloadConfirmation(MergedProjectEntry entry) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Download "${entry.project.name}"?'),
        content: const Text(
          'This will download all project data including entries, photos, '
          'and locations to this device.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Download'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      await _handleImport(entry);
    }
  }
```

#### Step 7.1.3: Add photo file cleanup to `_handleRemoveFromDevice()`

Replace `_handleRemoveFromDevice()` (lines 171-189):

```dart
  Future<void> _handleRemoveFromDevice(String projectId) async {
    final lifecycleService = context.read<ProjectLifecycleService>();
    try {
      // FROM SPEC: removeFromDevice returns photo paths for cleanup
      final photoPaths = await lifecycleService.removeFromDevice(projectId);

      // FROM SPEC: Delete photo files from disk
      for (final path in photoPaths) {
        try {
          final file = File(path);
          if (await file.exists()) {
            await file.delete();
          }
        } catch (e) {
          Logger.sync('Photo file delete failed: $path — $e');
        }
      }
      Logger.sync('Remove complete: $projectId (${photoPaths.length} photos cleaned)');

      if (!mounted) return;
      // Refresh after removal
      await context.read<ProjectProvider>().fetchRemoteProjects();
      if (!mounted) return;
      SnackBarHelper.showSuccess(context, 'Project removed from device');
    } on StateError catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.message)),
        );
      }
    } catch (e) {
      if (!mounted) return;
      SnackBarHelper.showError(context, 'Failed to remove project: $e');
    }
  }
```

Also add `import 'dart:io';` to the file imports.

#### Step 7.1.4: Add admin remote-only delete handler

Add after `_handleDeleteFromDatabase()`:

```dart
  /// FROM SPEC: Admin can delete remote-only projects via Supabase RPC
  Future<void> _handleRemoteDelete(MergedProjectEntry entry) async {
    final authProvider = context.read<AuthProvider>();
    if (!authProvider.isAdmin) {
      if (mounted) {
        SnackBarHelper.showError(context, 'Only admins can delete remote projects');
      }
      return;
    }

    final orchestrator = context.read<SyncOrchestrator>();
    if (!orchestrator.isSupabaseOnline) {
      if (mounted) {
        SnackBarHelper.showError(context, 'Cannot delete while offline');
      }
      return;
    }

    // Confirm before delete
    if (!mounted) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Project?'),
        content: Text(
          'This will permanently delete "${entry.project.name}" from the database for all users. '
          'This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.statusError,
            ),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    try {
      final lifecycleService = context.read<ProjectLifecycleService>();
      await lifecycleService.deleteFromSupabase(entry.project.id, isAdmin: true);
      if (!mounted) return;
      await context.read<ProjectProvider>().fetchRemoteProjects();
      if (!mounted) return;
      SnackBarHelper.showSuccess(context, 'Project deleted from database');
    } catch (e) {
      if (!mounted) return;
      SnackBarHelper.showError(context, 'Failed to delete project: $e');
    }
  }
```

#### Step 7.1.5: Rewrite `build()` method with two sections

Replace the `body:` section of the `build()` method. The key changes:
- Use `canCreateProject` instead of `canWrite` for FAB visibility
- Split entries into `myProjects` and `availableProjects` sections
- Remote-only cards use `_showDownloadConfirmation()` instead of `_handleImport()` directly
- Long-press on available projects shows admin delete for admins
- Long-press on my projects gates by `canDeleteProject`

```dart
  @override
  Widget build(BuildContext context) {
    final authProvider = context.watch<AuthProvider>();
    // FROM SPEC: FAB only for admin/engineer
    final canCreate = authProvider.canCreateProject;

    return Scaffold(
      appBar: AppBar(
        title: _isSearching ? _buildSearchField() : const Text('Projects'),
        actions: [
          if (!_isSearching)
            IconButton(
              key: TestingKeys.projectFilterToggle,
              icon: const Icon(Icons.search),
              onPressed: () => setState(() => _isSearching = true),
            )
          else
            IconButton(
              key: TestingKeys.projectSearchClose,
              icon: const Icon(Icons.close),
              onPressed: () {
                setState(() => _isSearching = false);
                _searchController.clear();
                context.read<ProjectProvider>().clearSearch();
              },
            ),
        ],
      ),
      body: Column(
        children: [
          // Import progress banner (above the list)
          Consumer<ProjectImportRunner>(
            builder: (context, runner, child) =>
                ProjectImportBanner(runner: runner),
          ),

          // Main list
          Expanded(
            child: Consumer<ProjectProvider>(
              builder: (context, provider, _) {
                if (provider.isLoading && provider.mergedProjects.isEmpty) {
                  return const Center(child: CircularProgressIndicator());
                }

                if (provider.error != null && provider.mergedProjects.isEmpty) {
                  return _buildErrorState(provider);
                }

                final entries = _filteredEntries(provider);
                // FROM SPEC: Split into My Projects and Available Projects
                final myProjects = entries.where((e) => !e.isRemoteOnly).toList();
                final availableProjects = entries.where((e) => e.isRemoteOnly).toList();

                if (myProjects.isEmpty && availableProjects.isEmpty) {
                  return _buildEmptyState(
                    provider.searchQuery.isNotEmpty,
                    canWrite: canCreate,
                  );
                }

                final now = DateTime.now();

                return RefreshIndicator(
                  onRefresh: _refresh,
                  child: Consumer<ProjectSyncHealthProvider>(
                    builder: (context, healthProvider, _) {
                      return ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          // MY PROJECTS section
                          if (myProjects.isNotEmpty) ...[
                            _buildSectionHeader('MY PROJECTS', myProjects.length),
                            ...myProjects.map((entry) => _buildProjectCard(
                              context, entry, healthProvider,
                              canWrite: authProvider.canWrite, now: now,
                            )),
                            const SizedBox(height: 24),
                          ],

                          // AVAILABLE PROJECTS section
                          if (availableProjects.isNotEmpty) ...[
                            _buildSectionHeader('AVAILABLE PROJECTS', availableProjects.length),
                            ...availableProjects.map((entry) => _buildProjectCard(
                              context, entry, healthProvider,
                              canWrite: authProvider.canWrite, now: now,
                            )),
                          ],
                        ],
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
      // FROM SPEC: FAB only for admin/engineer
      floatingActionButton: canCreate
          ? FloatingActionButton.extended(
              key: TestingKeys.addProjectFab,
              onPressed: () => context.pushNamed('project-new'),
              icon: const Icon(Icons.add),
              label: const Text('New Project'),
            )
          : null,
    );
  }

  Widget _buildSectionHeader(String title, int count) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        '$title ($count)',
        style: const TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: AppTheme.textTertiary,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
```

#### Step 7.1.6: Update `_buildProjectCard` for download dialog and role-based actions

In `_buildProjectCard()`, change the remote-only tap action:

```dart
        onTap: isRemoteOnly
            ? () => _showDownloadConfirmation(entry) // FROM SPEC: confirmation before import
            : () => _handleSelectProject(project.id),
        // FROM SPEC: Remote-only long-press → admin-only delete via RPC
        onLongPress: isRemoteOnly
            ? (context.read<AuthProvider>().isAdmin
                ? () => _handleRemoteDelete(entry)
                : null)
            : (authProvider.canWrite ? () => _showDeleteSheet(entry) : null),
```

Where `authProvider` needs to be passed in or read. Since the `build()` method now has `authProvider` from `context.watch`, pass it through or use `context.read` inside the card.

**NOTE to implementer:** The `canWrite` parameter on `_buildProjectCard` should be replaced with the `AuthProvider` instance or more granular permissions. The delete long-press on "My Projects" should check `canDeleteProject(createdByUserId: entry.project.createdByUserId)` for proper engineer-only-own filtering. For now, keeping `canWrite` is acceptable since the service layer enforces.

#### Step 7.1.7: Update remote-only card to show "Download" instead of "Import"

In the remote-only card section, change the button label from 'Import' to 'Download' and wire the confirmation:

```dart
                    ElevatedButton.icon(
                      onPressed: () => _showDownloadConfirmation(entry),
                      icon: const Icon(Icons.download, size: 18),
                      label: const Text('Download'),
                      style: ElevatedButton.styleFrom(
                        visualDensity: VisualDensity.compact,
                      ),
                    ),
```

#### Step 7.1.8: Add failed import card state (CR-HIGH-6)

**FROM SPEC (MF-2):** Enrolled projects with incomplete data must show a "Download incomplete" indicator with retry/cancel options. Detect this by checking if a project is enrolled in `synced_projects` but has no child data (e.g., no locations, no daily_entries).

Add a method to detect incomplete imports and render a warning on the card:

```dart
  // WHY (MF-2): Enrolled projects that failed mid-download must show retry/cancel,
  // not a broken card with no affordances.
  Widget _buildIncompleteImportBanner(MergedProjectEntry entry) {
    // FROM SPEC: Card shows "Download incomplete — tap to retry" with cancel option
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.orange.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          const Icon(Icons.warning_amber, color: Colors.orange, size: 18),
          const SizedBox(width: 8),
          const Expanded(
            child: Text(
              'Download incomplete — tap to retry',
              style: TextStyle(color: Colors.orange, fontSize: 12),
            ),
          ),
          TextButton(
            onPressed: () => _handleImport(entry),
            child: const Text('Retry', style: TextStyle(fontSize: 12)),
          ),
          TextButton(
            onPressed: () => _cancelImport(entry),
            child: const Text('Cancel', style: TextStyle(fontSize: 12, color: Colors.grey)),
          ),
        ],
      ),
    );
  }

  Future<void> _cancelImport(MergedProjectEntry entry) async {
    // Remove enrollment — project goes back to Available
    final lifecycleService = context.read<ProjectLifecycleService>();
    try {
      final db = context.read<DatabaseService>();
      final database = await db.database;
      await database.delete('synced_projects',
        where: 'project_id = ?', whereArgs: [entry.project.id]);
      Logger.sync('Import cancelled: ${entry.project.id}');
      if (mounted) {
        await context.read<ProjectProvider>().fetchRemoteProjects();
      }
    } catch (e) {
      Logger.error('Cancel import failed: $e');
    }
  }
```

The `_buildIncompleteImportBanner` should be shown inside `_buildProjectCard()` for "My Projects" cards where the project is enrolled but has zero child data. The `ProjectSyncHealthProvider` can be extended to track import completion status, or a simple heuristic (enrolled but `updated_at` matches `synced_at` within 1 second and no child rows) can be used.

---

## Phase 8: SyncProvider Wiring
> Wire ProjectSyncHealthProvider updates after sync cycles.

### Sub-phase 8.1: Wire health provider updates
**Files:** `lib/features/sync/presentation/providers/sync_provider.dart`
**Agent:** backend-data-layer-agent

#### Step 8.1.1: Add health provider callback

In `SyncProvider`, add a callback field and wire it in the constructor:

```dart
class SyncProvider extends ChangeNotifier {
  final SyncOrchestrator _syncOrchestrator;

  // FROM SPEC: Callback to update ProjectSyncHealthProvider after sync
  VoidCallback? onSyncCycleComplete;

  // ... existing fields ...
```

In `_setupListeners()`, inside `onSyncComplete` callback (line 67), after `_refreshPendingCount();` (line 114), add:

```dart
      _refreshPendingCount();
      // FROM SPEC: Wire ProjectSyncHealthProvider.updateCounts() after sync cycle
      onSyncCycleComplete?.call();
      notifyListeners();
```

#### Step 8.1.2: Wire the callback in main.dart

In `lib/main.dart`, inside the SyncProvider creation block (line 722-732), after `return syncProvider;`, wire the callback:

```dart
        ChangeNotifierProvider(
          create: (_) {
            final syncProvider = SyncProvider(syncOrchestrator);
            // Wire lifecycle manager callbacks to SyncProvider
            syncLifecycleManager.onStaleDataWarning = (isStale) {
              syncProvider.setStaleDataWarning(isStale);
            };
            syncLifecycleManager.onForcedSyncInProgress = (inProgress) {
              syncProvider.setForcedSyncInProgress(inProgress);
            };
            // FROM SPEC: Wire ProjectSyncHealthProvider after sync
            syncProvider.onSyncCycleComplete = () async {
              try {
                final counts = await projectLifecycleService.getAllUnsyncedCounts();
                projectSyncHealthProvider.updateCounts(counts);
              } catch (e) {
                Logger.sync('Health provider update failed: $e');
              }
            };
            return syncProvider;
          },
        ),
```

Also add `import 'package:flutter/foundation.dart';` if `VoidCallback` is not already available (it should be from `package:flutter/material.dart` which is already imported).

---

## Phase 9: Testing — Sync Engine
> Mock-Supabase tests, error categories, photo push.

### Sub-phase 9.1: Sync engine error handling tests
**Files:** `test/features/sync/engine/sync_engine_test.dart` (MODIFY existing)
**Agent:** qa-testing-agent

#### Step 9.1.1: Add `_handlePushError()` error category tests

Add these test cases to the existing sync_engine_test.dart. The tests need to exercise each error path in `_handlePushError()`. Since `_handlePushError` is private, test indirectly through `pushOnly()` with mock Supabase responses.

```dart
  group('Push error categories', () {
    // NOTE: These tests require mock Supabase setup. The existing test infrastructure
    // in sync_engine_test.dart should have the pattern established. Follow it.

    test('42501 RLS denial increments rlsDenialCount and marks failed', () async {
      // Setup: Insert a change_log entry, mock Supabase to throw PostgrestException with code 42501
      // Act: Call pushOnly()
      // Assert:
      //   - result.rlsDenials == 1
      //   - change_log entry has error_message containing 'RLS denied'
      //   - Logger.sync called with 'RLS DENIED (42501): ...'
    });

    test('23503 FK violation marks as permanent failure', () async {
      // Setup: Insert change_log, mock Supabase to throw PostgrestException code 23503
      // Act: Call pushOnly()
      // Assert:
      //   - result.errors == 1
      //   - change_log entry error_message contains 'FK violation'
    });

    test('23505 constraint race retries then fails', () async {
      // Setup: Insert change_log with retry_count = 2, mock 23505 error
      // Act: Call pushOnly()
      // Assert:
      //   - Not retried (retry_count >= 2)
      //   - Marked as failed
    });

    test('429 rate limit backs off and retries on first attempt', () async {
      // Setup: Insert change_log with retry_count = 0, mock 429 error
      // Act: Call pushOnly()
      // Assert:
      //   - result includes retry marking
      //   - Logger.sync called with 'RATE LIMITED'
    });

    test('SocketException marks as retryable network error', () async {
      // Setup: Insert change_log, mock Supabase to throw SocketException
      // Act: Call pushOnly()
      // Assert:
      //   - Logger.sync called with 'NETWORK ERROR'
      //   - First attempt marked as retryable
    });

    test('TimeoutException marks as retryable network error', () async {
      // Setup: Insert change_log, mock Supabase to throw TimeoutException
      // Act: Call pushOnly()
      // Assert: similar to SocketException
    });
  });
```

**NOTE to implementer:** The exact mock setup depends on how the existing tests in `sync_engine_test.dart` mock Supabase. Follow the established pattern. The tests need a real in-memory SQLite database (sqflite_common_ffi) with the full schema, plus a mocked Supabase client.

#### Step 9.1.2: Add push/pull summary logging tests

```dart
  group('Sync cycle summary logging', () {
    test('pushAndPull logs push summary after push completes', () async {
      // Verify Logger.sync is called with 'Push complete:' pattern
    });

    test('pushAndPull logs pull summary after pull completes', () async {
      // Verify Logger.sync is called with 'Pull complete:' pattern
    });

    test('pushAndPull logs overall cycle with duration', () async {
      // Verify Logger.sync is called with 'Sync cycle:' pattern including 'duration='
    });
  });
```

#### Step 9.1.3: Add orphan cleanup tests

```dart
  group('Orphaned synced_projects cleanup', () {
    test('orphaned entries are deleted during _loadSyncedProjectIds', () async {
      // Setup: Insert synced_projects entry for project_id 'orphan-1' with NO matching projects row
      //        Insert synced_projects entry for project_id 'valid-1' WITH matching projects row
      // Act: Call a method that triggers _loadSyncedProjectIds (e.g., pullOnly)
      // Assert:
      //   - synced_projects has 'valid-1' but NOT 'orphan-1'
      //   - Logger.sync called with 'Cleaned 1 orphaned'
    });
  });
```

---

### Sub-phase 9.2: Mock-Supabase end-to-end tests
**Files:** `test/features/sync/engine/sync_engine_e2e_test.dart` (NEW)
**Agent:** qa-testing-agent

#### Step 9.2.1: Create end-to-end test file

```dart
// test/features/sync/engine/sync_engine_e2e_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
// ... other imports ...

/// End-to-end tests for SyncEngine push/pull with mock Supabase.
///
/// FROM SPEC Section 7: Mock-Supabase integration tests for _push()/_pull() end-to-end.
void main() {
  // Initialize sqflite FFI for tests
  sqfliteFfiInit();

  group('Push end-to-end', () {
    late Database db;
    late SyncEngine engine;
    // ... setup ...

    setUp(() async {
      // Create in-memory database with full schema
      // Create mock Supabase client
      // Initialize SyncEngine with mocks
    });

    tearDown(() async {
      await db.close();
    });

    test('push sends pending changes to Supabase in FK order', () async {
      // Setup: Insert project + location + change_log entries
      // Act: pushOnly()
      // Assert: Mock Supabase received upserts in order (projects first, then locations)
    });

    test('push marks change_log entries as processed on success', () async {
      // Setup: Insert change_log entries
      // Act: pushOnly()
      // Assert: All change_log entries have processed = 1
    });

    test('push handles mixed success/failure across tables', () async {
      // Setup: projects succeed, locations fail with 23503
      // Act: pushOnly()
      // Assert: result.pushed > 0, result.errors > 0
    });
  });

  group('Pull end-to-end', () {
    test('pull fetches remote records into local SQLite', () async {
      // Setup: Mock Supabase returns records
      // Act: pullOnly()
      // Assert: Records exist in local SQLite
    });

    test('pull does NOT auto-enroll projects in synced_projects', () async {
      // CRITICAL: This validates the auto-enrollment removal
      // Setup: Mock Supabase returns project records
      // Act: pullOnly()
      // Assert: synced_projects table is EMPTY (no auto-enrollment)
    });

    test('pull resolves conflicts using ConflictResolver', () async {
      // Setup: Local record exists, remote record has different updated_at
      // Act: pullOnly()
      // Assert: Conflict resolved per ConflictResolver logic
    });
  });

  group('Photo three-phase push', () {
    test('photo push: upload file, upsert metadata, mark local', () async {
      // FROM SPEC: Phase 1 upload, Phase 2 upsert, Phase 3 local mark
    });

    test('photo push: Phase 2 failure cleans up uploaded file', () async {
      // FROM SPEC: Phase 2 cleanup on failure
    });
  });
}
```

---

## Phase 10: Testing — Projects
> Import E2E, delete, UI, role permissions.

### Sub-phase 10.1: Project list screen widget tests
**Files:** `test/features/projects/presentation/screens/project_list_screen_test.dart` (MODIFY existing)
**Agent:** qa-testing-agent

#### Step 10.1.1: Add section rendering tests

```dart
  group('Section rendering', () {
    testWidgets('shows MY PROJECTS and AVAILABLE PROJECTS headers', (tester) async {
      // Setup: Provider with both local and remote-only projects
      // Act: Pump ProjectListScreen
      // Assert: find.text('MY PROJECTS (N)') and find.text('AVAILABLE PROJECTS (N)')
    });

    testWidgets('my projects section shows local projects only', (tester) async {
      // Assert: Local projects appear under MY PROJECTS
    });

    testWidgets('available projects section shows remote-only projects', (tester) async {
      // Assert: Remote-only projects appear under AVAILABLE PROJECTS
    });
  });
```

#### Step 10.1.2: Add download confirmation dialog tests

```dart
  group('Download confirmation dialog', () {
    testWidgets('tapping available project shows confirmation dialog', (tester) async {
      // Setup: Remote-only project in provider
      // Act: Tap on available project card
      // Assert: Dialog with 'Download "ProjectName"?' is shown
    });

    testWidgets('cancel button dismisses dialog without importing', (tester) async {
      // Act: Tap Cancel
      // Assert: Dialog dismissed, no import triggered
    });

    testWidgets('download button triggers import flow', (tester) async {
      // Act: Tap Download
      // Assert: Import runner startImport called
    });
  });
```

#### Step 10.1.3: Add role permission tests

```dart
  group('Role permissions', () {
    testWidgets('admin sees FAB and all action buttons', (tester) async {
      // Setup: AuthProvider with admin role
      // Assert: FAB visible, edit/archive/delete buttons enabled
    });

    testWidgets('engineer sees FAB and own-project actions', (tester) async {
      // Setup: AuthProvider with engineer role
      // Assert: FAB visible
    });

    testWidgets('inspector does NOT see FAB', (tester) async {
      // Setup: AuthProvider with inspector role
      // Assert: FAB not found
    });

    testWidgets('inspector cannot long-press for delete', (tester) async {
      // Setup: Inspector role
      // Act: Long press on project card
      // Assert: Delete sheet NOT shown
    });
  });
```

#### Step 10.1.4: Add failed import retry/cancel tests

```dart
  group('Failed import', () {
    testWidgets('failed import shows retry/cancel in banner', (tester) async {
      // Setup: ProjectImportRunner in failed state
      // Act: Pump screen
      // Assert: Banner shows error message with retry option
    });
  });
```

---

### Sub-phase 10.2: Project lifecycle service tests
**Files:** `test/features/projects/data/services/project_lifecycle_service_test.dart` (MODIFY existing)
**Agent:** qa-testing-agent

#### Step 10.2.1: Add delete flow tests

```dart
  group('Delete flows', () {
    test('removeFromDevice returns photo paths and deletes all data', () async {
      // Setup: Project with photos in DB
      // Act: removeFromDevice(projectId)
      // Assert: Returns photo paths, project gone from all tables, synced_projects cleaned
    });

    test('removeFromDevice throws StateError when unsynced changes exist', () async {
      // Setup: Project with unprocessed change_log entries
      // Act + Assert: throws StateError with message about unsynced changes
    });

    test('deleteFromSupabase blocks non-admin', () async {
      // Act + Assert: throws StateError('Only admins can delete remote-only projects')
    });

    test('canDeleteFromDatabase allows admin for any project', () async {
      // Setup: Project created by another user
      // Act: canDeleteFromDatabase(projectId, 'other-user', isAdmin: true)
      // Assert: returns true
    });

    test('canDeleteFromDatabase blocks non-creator non-admin', () async {
      // Setup: Project created by 'user-A'
      // Act: canDeleteFromDatabase(projectId, 'user-B', isAdmin: false)
      // Assert: returns false
    });
  });
```

---

### Sub-phase 10.3: Project setup screen tests
**Files:** `test/features/projects/presentation/screens/project_setup_screen_test.dart` (NEW or MODIFY)
**Agent:** qa-testing-agent

#### Step 10.3.1: Add draft handling and offline creation tests

```dart
  group('Draft handling', () {
    testWidgets('back navigation shows save/discard prompt when data entered', (tester) async {
      // Setup: Pump ProjectSetupScreen, enter text in name field
      // Act: Tap back button
      // Assert: Dialog with 'Save as Draft?' / 'Discard' appears
    });

    testWidgets('discard deletes draft row', (tester) async {
      // Act: Enter data, tap back, tap Discard
      // Assert: Project row deleted from DB
    });

    testWidgets('back with no data navigates without prompt', (tester) async {
      // Act: Tap back without entering data
      // Assert: No dialog shown, navigated back
    });
  });

  group('Create offline defers push', () {
    testWidgets('save while offline does not trigger sync', (tester) async {
      // Setup: SyncOrchestrator.isSupabaseOnline = false
      // Act: Fill form, tap Save
      // Assert: Project saved, enrolled, syncLocalAgencyProjects NOT called
    });
  });
```

---

## Phase 11: Validation
> Run flutter test + flutter analyze to verify no regressions.

### Sub-phase 11.1: Run all tests
**Agent:** qa-testing-agent

#### Step 11.1.1: Run full test suite

```bash
pwsh -Command "flutter test"
```

Fix any failures. Common issues to watch for:
- `UserRole.viewer` references in test files (update to use `.inspector`)
- `isViewer` references (remove or update)
- Mock providers that set `UserRole.viewer` (change to `UserRole.inspector`)
- `fetchRemoteProjects()` mocks that expect Supabase calls (update to expect SQLite calls)

### Sub-phase 11.2: Run static analysis
**Agent:** qa-testing-agent

#### Step 11.2.1: Run flutter analyze

```bash
pwsh -Command "flutter analyze"
```

Fix any warnings. Expected issues:
- Unused imports after removing viewer-related code
- Missing `dart:io` import if File usage was added without it

---

## Dependency Graph

```
Phase 1 (Provider + Roles) ─────┐
                                 ├──► Phase 3 (Sync Engine)
Phase 2 (Supabase Migrations) ──┘         │
                                           ▼
                                    Phase 4 (ProjectProvider + Lifecycle)
                                           │
                                           ▼
                                    Phase 5 (SoftDeleteService)
                                           │
                               ┌───────────┼───────────┐
                               ▼           ▼           ▼
                          Phase 6      Phase 7     Phase 8
                          (Setup)      (List)      (SyncProvider)
                               │           │           │
                               └───────────┼───────────┘
                                           ▼
                                    Phase 9 (Tests - Sync)
                                           │
                                           ▼
                                    Phase 10 (Tests - Projects)
                                           │
                                           ▼
                                    Phase 11 (Validation)
```

## Batch Dispatch Strategy

**Group A (can run in parallel):** Phase 1 + Phase 2
- 1.1-1.4 auth-agent: Role changes, provider fix
- 2.1-2.4 backend-supabase-agent: SQL migrations

**Group B (after A):** Phase 3 + Phase 4 + Phase 5
- 3.1-3.5 backend-data-layer-agent: Sync engine changes
- 4.1-4.2 backend-data-layer-agent: Provider + lifecycle
- 5.1 backend-data-layer-agent: SoftDeleteService

**Group C (after B, can run in parallel):** Phase 6 + Phase 7 + Phase 8
- 6.1-6.2 frontend-flutter-specialist-agent: ProjectSetupScreen
- 7.1 frontend-flutter-specialist-agent: ProjectListScreen
- 8.1 backend-data-layer-agent: SyncProvider wiring

**Group D (after C, can run in parallel):** Phase 9 + Phase 10
- 9.1-9.2 qa-testing-agent: Sync engine tests
- 10.1-10.3 qa-testing-agent: Project tests

**Group E (after D):** Phase 11
- 11.1-11.2 qa-testing-agent: Full validation
