# Delete Flow Fix Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Wire up cascade soft-delete UI, add Supabase cascade trigger, fix daily_entries RLS security gap, and fix removed-project reappearance bug.
**Spec:** User-approved decisions from S09 delete flow investigation (S656)
**Analysis:** `.claude/dependency_graphs/2026-03-26-delete-flow-fix/`

**Architecture:** Replace RemovalDialog with ProjectDeleteSheet for admin/engineer, add AFTER UPDATE trigger on Supabase projects table for cascade soft-delete, tighten daily_entries DELETE RLS policy, and preserve project metadata row during device removal.
**Tech Stack:** Flutter/Dart, Supabase (PostgreSQL triggers, RLS), SQLite
**Blast Radius:** 8 direct, 6 dependent, 4 tests, 0 cleanup

---

## Phase 1: Supabase — Cascade Trigger + RLS Fix

**Agent:** `backend-supabase-agent`

### 1A: Create cascade soft-delete trigger on projects table

> **WHY:** When `deleted_at` is set on a project (via `admin_soft_delete_project` RPC or sync push), child tables must cascade automatically. Currently only the project row is soft-deleted on Supabase; children are orphaned.

**Step 1A.1:** Create migration file `supabase/migrations/20260326200000_project_cascade_soft_delete.sql`

Write the cascade trigger function. The trigger fires AFTER UPDATE on `projects` when `deleted_at` transitions NULL -> non-NULL. It sets `deleted_at` and `updated_at` on all child tables but NOT `deleted_by` — the existing `stamp_deleted_by` BEFORE UPDATE trigger on each child table will set `deleted_by = auth.uid()` automatically.

```sql
-- =============================================================================
-- Migration: Cascade soft-delete from projects to all child tables
-- FROM SPEC: Setting deleted_at on a project must cascade to all 14 child tables.
-- WHY: Without this, soft-deleting a project on Supabase leaves child rows visible
-- to other users. The sync engine only pushes the project row's deleted_at change;
-- children must be cascaded server-side.
--
-- INTERACTION: Each child table has a BEFORE UPDATE trigger (stamp_deleted_by)
-- that fires when deleted_at transitions NULL -> non-NULL. That trigger sets
-- deleted_by = auth.uid(). We intentionally do NOT set deleted_by here because
-- stamp_deleted_by will handle it. We only set deleted_at and updated_at.
-- =============================================================================

CREATE OR REPLACE FUNCTION cascade_project_soft_delete()
RETURNS TRIGGER AS $$
DECLARE
  v_now TIMESTAMPTZ := NOW();
BEGIN
  -- WHY: Only fire on soft-delete transition (NULL -> non-NULL)
  -- Skip if this is a restore (non-NULL -> NULL) or a non-delete update
  IF OLD.deleted_at IS NOT NULL OR NEW.deleted_at IS NULL THEN
    RETURN NEW;
  END IF;

  -- FROM SPEC: Direct children with project_id column (9 tables)
  -- WHY: Only cascade to rows that are not already soft-deleted
  UPDATE locations SET deleted_at = v_now, updated_at = v_now
    WHERE project_id = NEW.id AND deleted_at IS NULL;

  UPDATE contractors SET deleted_at = v_now, updated_at = v_now
    WHERE project_id = NEW.id AND deleted_at IS NULL;

  UPDATE daily_entries SET deleted_at = v_now, updated_at = v_now
    WHERE project_id = NEW.id AND deleted_at IS NULL;

  UPDATE bid_items SET deleted_at = v_now, updated_at = v_now
    WHERE project_id = NEW.id AND deleted_at IS NULL;

  UPDATE personnel_types SET deleted_at = v_now, updated_at = v_now
    WHERE project_id = NEW.id AND deleted_at IS NULL;

  UPDATE photos SET deleted_at = v_now, updated_at = v_now
    WHERE project_id = NEW.id AND deleted_at IS NULL;

  UPDATE form_responses SET deleted_at = v_now, updated_at = v_now
    WHERE project_id = NEW.id AND deleted_at IS NULL;

  UPDATE todo_items SET deleted_at = v_now, updated_at = v_now
    WHERE project_id = NEW.id AND deleted_at IS NULL;

  UPDATE calculation_history SET deleted_at = v_now, updated_at = v_now
    WHERE project_id = NEW.id AND deleted_at IS NULL;

  UPDATE inspector_forms SET deleted_at = v_now, updated_at = v_now
    WHERE project_id = NEW.id AND deleted_at IS NULL;

  -- FROM SPEC: Indirect children (via contractors -> equipment)
  UPDATE equipment SET deleted_at = v_now, updated_at = v_now
    WHERE deleted_at IS NULL AND contractor_id IN (
      SELECT id FROM contractors WHERE project_id = NEW.id
    );

  -- FROM SPEC: Indirect children (via daily_entries -> junction tables)
  UPDATE entry_contractors SET deleted_at = v_now, updated_at = v_now
    WHERE deleted_at IS NULL AND entry_id IN (
      SELECT id FROM daily_entries WHERE project_id = NEW.id
    );

  UPDATE entry_equipment SET deleted_at = v_now, updated_at = v_now
    WHERE deleted_at IS NULL AND entry_id IN (
      SELECT id FROM daily_entries WHERE project_id = NEW.id
    );

  UPDATE entry_personnel_counts SET deleted_at = v_now, updated_at = v_now
    WHERE deleted_at IS NULL AND entry_id IN (
      SELECT id FROM daily_entries WHERE project_id = NEW.id
    );

  UPDATE entry_quantities SET deleted_at = v_now, updated_at = v_now
    WHERE deleted_at IS NULL AND entry_id IN (
      SELECT id FROM daily_entries WHERE project_id = NEW.id
    );

  -- FROM SPEC: project_assignments has deleted_at/deleted_by columns and is in stamp_deleted_by.
  -- WHY: Without this, assignments remain active after project soft-delete,
  -- causing orphaned assignments visible to team members.
  UPDATE project_assignments SET deleted_at = v_now, updated_at = v_now
    WHERE project_id = NEW.id AND deleted_at IS NULL;

  -- IMPORTANT: This cascade MUST only be invoked via authenticated user sessions
  -- (not service_role or pg_cron). stamp_deleted_by on each child table will call
  -- auth.uid() and RAISE EXCEPTION if it returns NULL.

  RAISE LOG 'cascade_project_soft_delete: project=% cascaded to all children', NEW.id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- WHY: AFTER UPDATE so the project row is already committed when children cascade.
-- stamp_deleted_by fires BEFORE UPDATE on each child, setting deleted_by = auth.uid().
DROP TRIGGER IF EXISTS trg_projects_cascade_soft_delete ON projects;
CREATE TRIGGER trg_projects_cascade_soft_delete
  AFTER UPDATE ON projects
  FOR EACH ROW
  EXECUTE FUNCTION cascade_project_soft_delete();

-- Least-privilege: function is trigger-only, no direct execute needed
REVOKE ALL ON FUNCTION cascade_project_soft_delete() FROM PUBLIC;
```

**Verify:** Review the trigger interaction mentally:
1. `admin_soft_delete_project` RPC sets `deleted_at` on projects row
2. `stamp_deleted_by` BEFORE UPDATE fires on projects, stamps `deleted_by = auth.uid()`
3. Row is written
4. `cascade_project_soft_delete` AFTER UPDATE fires, UPDATEs child tables
5. For each child UPDATE, `stamp_deleted_by` BEFORE UPDATE fires, stamps `deleted_by = auth.uid()`
6. All children now have `deleted_at`, `updated_at`, and `deleted_by` set correctly

### 1B: Tighten daily_entries and todo_items DELETE RLS policies

> **WHY:** Current DELETE policy on `daily_entries` and `todo_items` uses `NOT is_viewer()` which is always TRUE (viewer role doesn't exist). Any authenticated company member can delete any entry. Inspectors should only delete their own entries.

**Step 1B.1:** Add RLS fix to the same migration file `supabase/migrations/20260326200000_project_cascade_soft_delete.sql`

Append to the migration:

```sql
-- =============================================================================
-- RLS Fix: Tighten daily_entries DELETE policy
-- FROM SPEC: Inspector can only delete entries they created.
-- Admin/Engineer can delete any entry in their company.
-- WHY: Current policy uses NOT is_viewer() which is always TRUE — any company
-- member can delete any entry. This is a privilege escalation vulnerability.
-- =============================================================================

DROP POLICY IF EXISTS "company_daily_entries_delete" ON daily_entries;
CREATE POLICY "company_daily_entries_delete" ON daily_entries
  FOR DELETE TO authenticated
  USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND (
      -- FROM SPEC: Admin/Engineer can delete any entry in their company
      is_admin_or_engineer()
      -- FROM SPEC: Inspector can only delete entries they created
      OR created_by_user_id = auth.uid()
    )
  );

-- =============================================================================
-- RLS Fix: Tighten todo_items DELETE policy (same vulnerability)
-- FROM SPEC: Same pattern as daily_entries — inspector can only delete own items.
-- =============================================================================

DROP POLICY IF EXISTS "company_todo_items_delete" ON todo_items;
CREATE POLICY "company_todo_items_delete" ON todo_items
  FOR DELETE TO authenticated
  USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND (
      is_admin_or_engineer()
      OR created_by_user_id = auth.uid()
    )
  );
```

**Verify:** `is_admin_or_engineer()` is defined in `supabase/migrations/20260319100000_create_project_assignments.sql` and checks `role IN ('admin', 'engineer') AND status = 'approved'`. Inspectors fail this check, so they fall through to the `OR created_by_user_id = auth.uid()` branch.

### 1C: Push migration to Supabase

**Step 1C.1:** Push the migration

```bash
npx supabase db push
```

**Step 1C.2:** Verify the trigger exists

```bash
npx supabase db diff
```

Diff should be empty (no schema drift).

---

## Phase 2: Data Layer — Fix removeFromDevice Reappearance Bug

**Agent:** `backend-data-layer-agent`

### 2A: Skip project row deletion in removeFromDevice

> **WHY:** `removeFromDevice()` hard-deletes the project row (line 232 of `project_lifecycle_service.dart`). After deletion, `fetchRemoteProjects()` no longer finds a local row, so the project vanishes entirely. The fix: keep the project metadata row so it appears in the "Not Downloaded" filter after `synced_projects` is removed.

**Step 2A.1:** Edit `lib/features/projects/data/services/project_lifecycle_service.dart` line 231-232

Remove the project row hard-delete:

```dart
// BEFORE (line 231-232):
      // Step 7: Hard-delete project row
      await txn.delete('projects', where: 'id = ?', whereArgs: [projectId]);

// AFTER:
      // Step 7: SKIP — preserve project metadata row
      // WHY (REAPPEARANCE FIX): Keeping the projects row allows fetchRemoteProjects()
      // to find it via `WHERE company_id = ? AND deleted_at IS NULL`. Since
      // synced_projects was deleted in Step 8, the project is not in enrolledIds,
      // so it appears in _remoteProjects (available for re-download).
      // The row is lightweight (just metadata, no child data remains).
```

**Step 2A.2:** Update the method's doc comment at line 63-72

```dart
// BEFORE (line 70):
  /// 5. Hard-delete project row

// AFTER:
  /// 5. Preserve project metadata row (for "Not Downloaded" tab visibility)
```

**Step 2A.3:** Update the step numbering comment at line 234

```dart
// BEFORE (line 234):
      // Step 8: Remove from synced_projects

// AFTER:
      // Step 7: Remove from synced_projects (renumbered — old step 7 removed)
```

And line 237-243:

```dart
// BEFORE (line 237):
      // Step 9: Clean legacy change_log entries for the project record itself

// AFTER:
      // Step 8: Clean legacy change_log entries for the project record itself (renumbered)
```

**Verify:** After this change, removing a project from device will:
1. Delete all child data (entries, contractors, photos, etc.)
2. Delete `synced_projects` row (unenrolls from sync)
3. Keep project metadata row (name, number, company_id, etc.)
4. `fetchRemoteProjects()` finds it as a remote project available for download

---

## Phase 3: UI — Wire Up ProjectDeleteSheet + Role Gating

**Agent:** `frontend-flutter-specialist-agent`

### 3A: Add testing keys for ProjectDeleteSheet

> **WHY:** `ProjectDeleteSheet` has no testing keys. Need them for e2e verification.

**Step 3A.1:** Add keys to `lib/shared/testing_keys/projects_keys.dart`

Insert after the Removal Dialog section (after line 187):

```dart
  // ============================================
  // Project Delete Sheet
  // ============================================
  /// "Remove from this device" checkbox in delete sheet
  static const deleteSheetRemoveFromDevice = Key('delete_sheet_remove_from_device');

  /// "Delete from database" checkbox in delete sheet
  static const deleteSheetDeleteFromDatabase = Key('delete_sheet_delete_from_database');

  /// Confirm button in delete sheet
  static const deleteSheetConfirmButton = Key('delete_sheet_confirm_button');
```

### 3B: Add keys to ProjectDeleteSheet widget

**Step 3B.1:** Edit `lib/features/projects/presentation/widgets/project_delete_sheet.dart`

Add import at top:

```dart
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';
```

Add key to the "Remove from this device" CheckboxListTile (line 78):

```dart
          CheckboxListTile(
            key: ProjectsTestingKeys.deleteSheetRemoveFromDevice, // FROM SPEC: e2e testing key
            value: _removeFromDevice,
```

Add key to the "Delete from database" CheckboxListTile (line 91):

```dart
          CheckboxListTile(
            key: ProjectsTestingKeys.deleteSheetDeleteFromDatabase, // FROM SPEC: e2e testing key
            value: _deleteFromDatabase,
```

Add key to the Confirm ElevatedButton (line 122):

```dart
            child: ElevatedButton(
              key: ProjectsTestingKeys.deleteSheetConfirmButton, // FROM SPEC: e2e testing key
```

### 3C: Export ProjectDeleteSheet from barrel file

**Step 3C.1:** Edit `lib/features/projects/presentation/widgets/widgets.dart`

Add after line 14 (`export 'removal_dialog.dart';`):

```dart
export 'project_delete_sheet.dart';
```

### 3D: Replace _showRemovalDialog with role-aware logic

> **WHY:** Currently all roles see `RemovalDialog` (device-only removal). Admin/Engineer should see `ProjectDeleteSheet` with database delete option. Inspector should keep `RemovalDialog` (device-only).

**Step 3D.1:** Edit `lib/features/projects/presentation/screens/project_list_screen.dart`

Replace the entire `_showRemovalDialog` method (lines 537-571) with:

```dart
  // ---------------------------------------------------------------------------
  // My Projects long-press: Role-aware delete flow
  // ---------------------------------------------------------------------------

  Future<void> _showRemovalDialog(MergedProjectEntry entry) async {
    final authProvider = context.read<AuthProvider>();
    final orchestrator = context.read<SyncOrchestrator>();
    final lifecycleService = context.read<ProjectLifecycleService>();

    // FROM SPEC (BUG-006): Refresh DNS before gating connectivity-dependent options.
    await orchestrator.checkDnsReachability();
    final isOnline = orchestrator.isSupabaseOnline;
    final unsyncedCount =
        await lifecycleService.getUnsyncedChangeCount(entry.project.id);
    if (!mounted) return;

    // FROM SPEC: Inspector sees device-only RemovalDialog; Admin/Engineer sees ProjectDeleteSheet
    if (authProvider.isInspector) {
      // WHY: Inspector cannot delete from database — only remove from device
      await _showInspectorRemovalDialog(entry, isOnline, unsyncedCount);
    } else {
      // WHY: Admin/Engineer gets ProjectDeleteSheet with database delete option
      await _showDeleteSheet(entry, authProvider, isOnline, unsyncedCount);
    }
  }

  /// FROM SPEC: Inspector-only path — keeps existing RemovalDialog behavior
  Future<void> _showInspectorRemovalDialog(
    MergedProjectEntry entry,
    bool isOnline,
    int unsyncedCount,
  ) async {
    final choice = await RemovalDialog.show(
      context: context,
      projectName: entry.project.name,
      hasPendingChanges: unsyncedCount > 0,
      isOnline: isOnline,
    );

    if (!mounted) return;
    switch (choice) {
      case RemovalChoice.syncAndRemove:
        try {
          final orchestrator = context.read<SyncOrchestrator>();
          await orchestrator.syncLocalAgencyProjects();
          if (!mounted) return;
          await _handleRemoveFromDevice(entry.project.id);
        } catch (e) {
          if (!mounted) return;
          SnackBarHelper.showError(context, 'Sync failed: $e');
        }
      case RemovalChoice.deleteFromDevice:
        await _handleRemoveFromDevice(entry.project.id);
      case RemovalChoice.cancel:
        break;
    }
  }

  /// FROM SPEC: Admin/Engineer path — ProjectDeleteSheet with database delete option
  Future<void> _showDeleteSheet(
    MergedProjectEntry entry,
    AuthProvider authProvider,
    bool isOnline,
    int unsyncedCount,
  ) async {
    // FROM SPEC: Role gating — Admin=any project, Engineer=own projects only
    final canDelete = await context.read<ProjectLifecycleService>().canDeleteFromDatabase(
      entry.project.id,
      authProvider.userId!,
      isAdmin: authProvider.isAdmin,
    );
    if (!mounted) return;

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => ProjectDeleteSheet(
        projectName: entry.project.name,
        unsyncedCount: unsyncedCount,
        canDeleteFromDatabase: canDelete,
        isOffline: !isOnline,
        onRemoveFromDevice: () async {
          // WHY: Same as inspector path — just remove local data
          await _handleRemoveFromDevice(entry.project.id);
        },
        onDeleteFromDatabase: () async {
          // FROM SPEC: Confirmation dialog before database delete
          await _confirmAndDeleteFromDatabase(entry, authProvider);
        },
      ),
    );
  }

  /// FROM SPEC: Two-step confirmation for database deletes
  Future<void> _confirmAndDeleteFromDatabase(
    MergedProjectEntry entry,
    AuthProvider authProvider,
  ) async {
    if (!mounted) return;

    // FROM SPEC: "Are you sure? This will delete all project data" confirmation
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Project Permanently?'),
        content: Text(
          'This will delete "${entry.project.name}" and all associated data '
          '(entries, photos, contractors, etc.) for all team members. '
          'This action cannot be undone.',
        ),
        actions: [
          TextButton(
            key: ProjectsTestingKeys.projectRemoteDeleteDialogCancel,
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            key: ProjectsTestingKeys.projectRemoteDeleteDialogConfirm,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.statusError,
            ),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete Permanently'),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    // FROM SPEC (TOCTOU): Re-check authorization after async dialog gap
    // WHY (SEC-M3): Refresh profile to catch role changes during dialog
    final currentAuth = context.read<AuthProvider>();
    await currentAuth.refreshUserProfile();
    if (!mounted) return;
    if (!currentAuth.canDeleteProject(createdByUserId: entry.project.createdByUserId)) {
      if (mounted) {
        SnackBarHelper.showError(context, 'Delete permission revoked');
      }
      return;
    }

    try {
      final projectProvider = context.read<ProjectProvider>();
      final success = await projectProvider.deleteProject(
        entry.project.id,
        currentUserId: currentAuth.userId!,
        isAdmin: currentAuth.isAdmin,
      );
      if (!mounted) return;
      if (success) {
        SnackBarHelper.showSuccess(context, 'Project deleted permanently');
      } else {
        SnackBarHelper.showError(context, projectProvider.error ?? 'Delete failed');
      }
    } catch (e) {
      if (!mounted) return;
      SnackBarHelper.showError(context, 'Failed to delete project: $e');
    }
  }
```

**Step 3D.2:** Add `isInspector` getter to `AuthProvider`

The `AuthProvider` at `lib/features/auth/presentation/providers/auth_provider.dart` has `isAdmin` (line 172) and `isEngineer` (line 187) but does NOT have `isInspector`. Add it after `isEngineer`:

```dart
  // FROM SPEC: Inspector role check for delete flow gating
  // WHY: Needed to gate _showRemovalDialog — inspector sees RemovalDialog, not ProjectDeleteSheet
  bool get isInspector => userProfile?.role == UserRole.inspector;
```

**Step 3D.3:** Verify `createdByUserId` accessor exists on the project model

The confirmation dialog uses `entry.project.createdByUserId`. Verify this field exists on the `Project` model at `lib/features/projects/data/models/project.dart`. It should map to the `created_by_user_id` column.

---

## Phase 4: Tests

**Agent:** `qa-testing-agent`

### 4A: Unit test — removeFromDevice preserves project row

**Step 4A.1:** Edit `test/features/projects/data/services/project_lifecycle_service_test.dart`

Add a new test:

```dart
  test('removeFromDevice preserves project metadata row', () async {
    // WHY (REAPPEARANCE FIX): After device removal, project row must remain
    // so fetchRemoteProjects() can show it in "Not Downloaded" tab.

    // Arrange: Insert a project and enroll it
    await db.insert('projects', {
      'id': 'proj-1',
      'name': 'Test Project',
      'company_id': 'company-1',
      'created_by_user_id': 'user-1',
      'created_at': DateTime.now().toUtc().toIso8601String(),
      'updated_at': DateTime.now().toUtc().toIso8601String(),
    });
    await service.enrollProject('proj-1');

    // Act
    await service.removeFromDevice('proj-1');

    // Assert: project row still exists
    final projectRows = await db.query('projects', where: 'id = ?', whereArgs: ['proj-1']);
    expect(projectRows, hasLength(1), reason: 'Project metadata row should be preserved');
    expect(projectRows.first['name'], equals('Test Project'));

    // Assert: synced_projects row is gone
    final syncRows = await db.query('synced_projects', where: 'project_id = ?', whereArgs: ['proj-1']);
    expect(syncRows, isEmpty, reason: 'synced_projects enrollment should be removed');

    // Assert (REVIEW FIX — MEDIUM #2): Verify reappearance in "Not Downloaded" query
    // WHY: This is the actual user-facing bug — the project must appear as available
    // for re-download after device removal. Simulate fetchRemoteProjects() query.
    final availableRows = await db.query(
      'projects',
      columns: ['id', 'name', 'company_id'],
      where: 'company_id = ? AND deleted_at IS NULL',
      whereArgs: ['company-1'],
    );
    expect(availableRows, hasLength(1), reason: 'Project should appear in available list');
    expect(availableRows.first['id'], equals('proj-1'));

    // Verify it is NOT in synced_projects (i.e., it's "unenrolled" = available for download)
    final enrolledRows = await db.query('synced_projects');
    final enrolledIds = enrolledRows.map((r) => r['project_id'] as String).toSet();
    expect(enrolledIds.contains('proj-1'), isFalse,
        reason: 'Project should not be enrolled (available for re-download)');
  });
```

Note: This test may require adding `projects` table to the test schema setup. Check the existing `setUp` block in the test file and add the `CREATE TABLE projects` statement if missing.

### 4B: Unit test — _showRemovalDialog role gating (widget test)

**Step 4B.1:** Create `test/features/projects/presentation/screens/project_delete_flow_test.dart`

```dart
// test/features/projects/presentation/screens/project_delete_flow_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/projects/presentation/widgets/project_delete_sheet.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';

void main() {
  group('ProjectDeleteSheet', () {
    // WHY: Verify the dead code is now properly wired and functional

    testWidgets('shows both checkboxes', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: ProjectDeleteSheet(
            projectName: 'Test Project',
            unsyncedCount: 0,
            canDeleteFromDatabase: true,
            onRemoveFromDevice: () {},
            onDeleteFromDatabase: () {},
          ),
        ),
      ));

      expect(find.byKey(ProjectsTestingKeys.deleteSheetRemoveFromDevice), findsOneWidget);
      expect(find.byKey(ProjectsTestingKeys.deleteSheetDeleteFromDatabase), findsOneWidget);
      expect(find.byKey(ProjectsTestingKeys.deleteSheetConfirmButton), findsOneWidget);
    });

    testWidgets('database delete disabled when canDeleteFromDatabase is false', (tester) async {
      // FROM SPEC: Inspector sees disabled "Delete from database" checkbox
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: ProjectDeleteSheet(
            projectName: 'Test Project',
            unsyncedCount: 0,
            canDeleteFromDatabase: false,
            onRemoveFromDevice: () {},
            onDeleteFromDatabase: () {},
          ),
        ),
      ));

      final dbCheckbox = tester.widget<CheckboxListTile>(
        find.byKey(ProjectsTestingKeys.deleteSheetDeleteFromDatabase),
      );
      // WHY: onChanged is null when disabled
      expect(dbCheckbox.onChanged, isNull);
    });

    testWidgets('database delete disabled when offline', (tester) async {
      // FROM SPEC (M14): Database delete requires connectivity
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: ProjectDeleteSheet(
            projectName: 'Test Project',
            unsyncedCount: 0,
            canDeleteFromDatabase: true,
            isOffline: true,
            onRemoveFromDevice: () {},
            onDeleteFromDatabase: () {},
          ),
        ),
      ));

      final dbCheckbox = tester.widget<CheckboxListTile>(
        find.byKey(ProjectsTestingKeys.deleteSheetDeleteFromDatabase),
      );
      expect(dbCheckbox.onChanged, isNull);
    });

    testWidgets('shows unsynced warning when count > 0', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: ProjectDeleteSheet(
            projectName: 'Test Project',
            unsyncedCount: 3,
            canDeleteFromDatabase: true,
            onRemoveFromDevice: () {},
            onDeleteFromDatabase: () {},
          ),
        ),
      ));

      expect(find.text('3 unsynced changes will be lost.'), findsOneWidget);
    });

    testWidgets('confirm button calls onDeleteFromDatabase when database checked', (tester) async {
      var dbDeleteCalled = false;

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () => showModalBottomSheet(
                context: context,
                builder: (_) => ProjectDeleteSheet(
                  projectName: 'Test Project',
                  unsyncedCount: 0,
                  canDeleteFromDatabase: true,
                  onRemoveFromDevice: () {},
                  onDeleteFromDatabase: () { dbDeleteCalled = true; },
                ),
              ),
              child: const Text('Open'),
            ),
          ),
        ),
      ));

      // Open the sheet
      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      // Check "Delete from database"
      await tester.tap(find.byKey(ProjectsTestingKeys.deleteSheetDeleteFromDatabase));
      await tester.pump();

      // Tap confirm
      await tester.tap(find.byKey(ProjectsTestingKeys.deleteSheetConfirmButton));
      await tester.pumpAndSettle();

      expect(dbDeleteCalled, isTrue);
    });
  });
}
```

**Step 4B.2:** Add role-gating verification tests to the same file

Append to the `main()` function in `project_delete_flow_test.dart`:

```dart
  // REVIEW FIX (MEDIUM #1): Verify screen-level role gating
  // WHY: The core Path C wiring must be tested — inspector sees RemovalDialog,
  // admin/engineer sees ProjectDeleteSheet. Without this, a wiring bug could
  // show the wrong dialog to the wrong role.

  group('Role gating at screen level', () {
    // NOTE: These tests verify the branching logic conceptually.
    // Full screen-level widget tests with mocked providers would require
    // pumping ProjectListScreen with MultiProvider, which is complex.
    // The implementing agent should check if a simpler approach exists
    // (e.g., extracting the role-gating logic into a testable function).

    // NOTE: Full screen-level role gating (inspector sees RemovalDialog,
    // admin/engineer sees ProjectDeleteSheet) requires pumping ProjectListScreen
    // with mocked AuthProvider/ProjectProvider/SyncOrchestrator/ProjectLifecycleService.
    // This is deferred to e2e testing (S09 re-run). Server-side RLS on projects
    // UPDATE (is_admin_or_engineer()) is the real enforcement layer.

    testWidgets('ProjectDeleteSheet confirm button calls onRemoveFromDevice when only remove checked', (tester) async {
      // WHY: Verify the remove-only path (no database delete) works correctly
      var removeCalled = false;

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () => showModalBottomSheet(
                context: context,
                builder: (_) => ProjectDeleteSheet(
                  projectName: 'Test Project',
                  unsyncedCount: 0,
                  canDeleteFromDatabase: true,
                  onRemoveFromDevice: () { removeCalled = true; },
                  onDeleteFromDatabase: () {},
                ),
              ),
              child: const Text('Open'),
            ),
          ),
        ),
      ));

      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      // Check "Remove from this device" only
      await tester.tap(find.byKey(ProjectsTestingKeys.deleteSheetRemoveFromDevice));
      await tester.pump();

      // Tap confirm
      await tester.tap(find.byKey(ProjectsTestingKeys.deleteSheetConfirmButton));
      await tester.pumpAndSettle();

      expect(removeCalled, isTrue, reason: 'onRemoveFromDevice should fire when only remove is checked');
    });

    testWidgets('checking database auto-checks remove from device', (tester) async {
      // FROM SPEC: Checking "Delete from database" auto-checks "Remove from this device"
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () => showModalBottomSheet(
                context: context,
                builder: (_) => ProjectDeleteSheet(
                  projectName: 'Test Project',
                  unsyncedCount: 0,
                  canDeleteFromDatabase: true,
                  onRemoveFromDevice: () {},
                  onDeleteFromDatabase: () {},
                ),
              ),
              child: const Text('Open'),
            ),
          ),
        ),
      ));

      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      // Check "Delete from database"
      await tester.tap(find.byKey(ProjectsTestingKeys.deleteSheetDeleteFromDatabase));
      await tester.pump();

      // Verify "Remove from this device" is auto-checked
      final removeCheckbox = tester.widget<CheckboxListTile>(
        find.byKey(ProjectsTestingKeys.deleteSheetRemoveFromDevice),
      );
      expect(removeCheckbox.value, isTrue,
          reason: 'Remove checkbox should be auto-checked when database is checked');

      // Verify remove checkbox is disabled (cannot uncheck when database is checked)
      expect(removeCheckbox.onChanged, isNull,
          reason: 'Remove checkbox should be disabled when database is checked');
    });
  });
```

**Step 4B.3:** Run tests

```bash
pwsh -Command "flutter test test/features/projects/presentation/screens/project_delete_flow_test.dart"
pwsh -Command "flutter test test/features/projects/data/services/project_lifecycle_service_test.dart"
```

### 4C: Run full project-related test suite

**Step 4C.1:** Run all project-related tests to catch regressions

```bash
pwsh -Command "flutter test test/features/projects/"
```

---

## Phase 5: Integration Verification

**Agent:** `general-purpose`

### 5A: Static analysis

**Step 5A.1:** Run flutter analyze

```bash
pwsh -Command "flutter analyze"
```

Fix any issues found.

### 5B: Run full test suite

**Step 5B.1:** Run all tests

```bash
pwsh -Command "flutter test"
```

### 5C: Push Supabase migration and verify

**Step 5C.1:** Push migration (if not already done in Phase 1C)

```bash
npx supabase db push
```

**Step 5C.2:** Verify no schema drift

```bash
npx supabase db diff
```

---

## File Change Summary

| File | Change | Phase |
|------|--------|-------|
| `supabase/migrations/20260326200000_project_cascade_soft_delete.sql` | NEW — cascade trigger + RLS fix | 1A, 1B |
| `lib/features/projects/data/services/project_lifecycle_service.dart` | Remove project row deletion (line 232) | 2A |
| `lib/shared/testing_keys/projects_keys.dart` | Add 3 testing keys | 3A |
| `lib/features/projects/presentation/widgets/project_delete_sheet.dart` | Add testing keys + import | 3B |
| `lib/features/projects/presentation/widgets/widgets.dart` | Export project_delete_sheet.dart | 3C |
| `lib/features/projects/presentation/screens/project_list_screen.dart` | Replace _showRemovalDialog with role-aware flow | 3D |
| `lib/features/auth/presentation/providers/auth_provider.dart` | Add `isInspector` getter (if missing) | 3D |
| `test/features/projects/data/services/project_lifecycle_service_test.dart` | Add reappearance fix test | 4A |
| `test/features/projects/presentation/screens/project_delete_flow_test.dart` | NEW — ProjectDeleteSheet widget tests | 4B |

## Security Checklist

- [ ] Cascade trigger uses `SECURITY DEFINER` to bypass RLS for child updates
- [ ] `stamp_deleted_by` on each child sets `deleted_by = auth.uid()` (not spoofable)
- [ ] daily_entries DELETE RLS now requires `is_admin_or_engineer() OR created_by_user_id = auth.uid()`
- [ ] todo_items DELETE RLS follows same pattern
- [ ] TOCTOU re-check in `_confirmAndDeleteFromDatabase` after async dialog gap
- [ ] Client-side role check (`isInspector`) is defense-in-depth; server RLS is the real guard
- [ ] `canDeleteFromDatabase` queries local SQLite (client-side); server `admin_soft_delete_project` RPC validates server-side
