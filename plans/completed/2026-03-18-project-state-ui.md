# Project State UI & Assignments Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Redesign the Projects tab with a 3-tab layout (My Projects / Company / Archived), per-project user assignments from the setup wizard, and clean role-aware enrollment/unenrollment flows.

**Spec:** `.claude/specs/2026-03-18-project-state-ui-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-18-project-state-ui/`

**Architecture:** New `project_assignments` table (Supabase + SQLite) synced via a new `ProjectAssignmentAdapter`. `ProjectProvider` gains tab state and computed lists partitioned from the merged view. A new `ProjectAssignmentProvider` manages in-memory wizard state for assigning team members. The project list screen is rewritten as a 3-tab `TabBarView` with filter chips and contextual actions.

**Tech Stack:** Flutter/Dart, Supabase (RLS + triggers), SQLite (sqflite), Provider (ChangeNotifier), GoRouter
**Blast Radius:** 22 direct files (11 new, 11 modified), 3 dependent (no changes), 9 test files, 1 delete = 35 total

---

## Phase 1: Supabase Migration

### Sub-phase 1.1: Create project_assignments Table + RLS + Triggers

**Files:**
- Create: `supabase/migrations/20260319100000_create_project_assignments.sql`
- Create: `supabase/rollbacks/20260319100000_rollback.sql`

**Agent:** `backend-supabase-agent`

#### Step 1.1.1: Write the migration SQL

Create `supabase/migrations/20260319100000_create_project_assignments.sql`:

```sql
-- FROM SPEC Section 2: project_assignments table
-- WHY: Tracks which users are assigned to which projects. Organizational, not access-control.

-- Helper function: check if current user is admin or engineer
-- NOTE: SECURITY DEFINER so it runs with the function owner's privileges,
-- allowing it to query user_profiles regardless of the caller's RLS context.
CREATE OR REPLACE FUNCTION is_admin_or_engineer()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM user_profiles
    WHERE id = auth.uid()
      AND status = 'approved'
      AND role IN ('admin', 'engineer')
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public;

-- Create the table
CREATE TABLE project_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  assigned_by UUID NOT NULL REFERENCES auth.users(id),
  company_id UUID NOT NULL REFERENCES companies(id),
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (project_id, user_id)
);

-- Enable RLS (FROM SPEC Section 2: RLS Policies)
ALTER TABLE project_assignments ENABLE ROW LEVEL SECURITY;

-- SELECT: Inspectors see their own assignments; admin/engineer see all in company (SC-7)
CREATE POLICY "see_assignments" ON project_assignments
  FOR SELECT TO authenticated
  USING (
    (user_id = auth.uid() OR is_admin_or_engineer())
    AND company_id = get_my_company_id()
  );

-- INSERT: Admin/engineer only, same company, assignee must be approved company member (MF-3)
CREATE POLICY "admin_engineer_assign" ON project_assignments
  FOR INSERT TO authenticated
  WITH CHECK (
    is_admin_or_engineer()
    AND company_id = get_my_company_id()
    AND assigned_by = auth.uid()
    AND user_id IN (
      SELECT id FROM user_profiles
      WHERE company_id = get_my_company_id() AND status = 'approved'
    )
  );

-- DELETE: Admin/engineer only, same company
CREATE POLICY "admin_engineer_unassign" ON project_assignments
  FOR DELETE TO authenticated
  USING (
    is_admin_or_engineer()
    AND company_id = get_my_company_id()
  );

-- REVIEW FIX (CRIT-1): enforce_created_by() writes to created_by_user_id, NOT assigned_by.
-- Must use a dedicated function for this table.
CREATE OR REPLACE FUNCTION enforce_assignment_assigned_by()
RETURNS TRIGGER AS $$
BEGIN
  NEW.assigned_by := auth.uid();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Trigger: enforce assigned_by = auth.uid() on INSERT (MF-2, server-side enforcement)
CREATE TRIGGER trg_project_assignments_assigned_by
  BEFORE INSERT ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION enforce_assignment_assigned_by();

-- Trigger: prevent timestamp spoofing on INSERT
CREATE TRIGGER trg_project_assignments_insert_ts
  BEFORE INSERT ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();

-- Trigger: auto-update updated_at on UPDATE
CREATE TRIGGER trg_project_assignments_updated_at
  BEFORE UPDATE ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger: populate company_id from project (NH-16 — denormalized for RPC integrity)
CREATE OR REPLACE FUNCTION populate_assignment_company_id()
RETURNS TRIGGER AS $$
BEGIN
  NEW.company_id := (SELECT company_id FROM projects WHERE id = NEW.project_id);
  -- REVIEW FIX (MED-2): Guard against NULL company_id from corrupted project rows
  IF NEW.company_id IS NULL THEN
    RAISE EXCEPTION 'project % has no company_id', NEW.project_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_project_assignments_company_id
  BEFORE INSERT ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION populate_assignment_company_id();

-- Audit logging (NH-18)
CREATE OR REPLACE FUNCTION log_assignment_change()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    RAISE LOG 'project_assignment_created: project=% user=% by=%', NEW.project_id, NEW.user_id, NEW.assigned_by;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    RAISE LOG 'project_assignment_deleted: project=% user=% by=%', OLD.project_id, OLD.user_id, auth.uid();
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_project_assignments_audit
  AFTER INSERT OR DELETE ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION log_assignment_change();

-- Indexes for performance
CREATE INDEX idx_project_assignments_project ON project_assignments(project_id);
CREATE INDEX idx_project_assignments_user ON project_assignments(user_id);
CREATE INDEX idx_project_assignments_company ON project_assignments(company_id);
```

#### Step 1.1.2: Write the rollback SQL

Create `supabase/rollbacks/20260319100000_rollback.sql`:

```sql
-- Rollback: drop project_assignments and helper function
DROP TRIGGER IF EXISTS trg_project_assignments_audit ON project_assignments;
DROP TRIGGER IF EXISTS trg_project_assignments_company_id ON project_assignments;
DROP TRIGGER IF EXISTS trg_project_assignments_updated_at ON project_assignments;
DROP TRIGGER IF EXISTS trg_project_assignments_insert_ts ON project_assignments;
DROP TRIGGER IF EXISTS trg_project_assignments_assigned_by ON project_assignments;
DROP FUNCTION IF EXISTS log_assignment_change();
DROP FUNCTION IF EXISTS populate_assignment_company_id();
DROP FUNCTION IF EXISTS enforce_assignment_assigned_by();
DROP TABLE IF EXISTS project_assignments;
DROP FUNCTION IF EXISTS is_admin_or_engineer();
```

#### Step 1.1.3: Push migration to Supabase

Run: `npx supabase db push`
Expected: Migration applied successfully, no errors.

#### Step 1.1.4: Verify table and RLS

Run: `npx supabase db diff`
Expected: No diff (migration matches remote).

---

## Phase 2: SQLite Schema + Migration

### Sub-phase 2.1: Add project_assignments Table to SQLite Schema

**Files:**
- Modify: `lib/core/database/schema/sync_engine_tables.dart:5-196`
- Modify: `lib/core/database/database_service.dart:53,79,104-176,247+`

**Agent:** `backend-data-layer-agent`

#### Step 2.1.1: Add createProjectAssignmentsTable to SyncEngineTables

In `lib/core/database/schema/sync_engine_tables.dart`, add after `createStorageCleanupQueueTable` (line ~94):

```dart
  // FROM SPEC Section 2: project_assignments local mirror
  // WHY: Tracks which users are assigned to which projects.
  // Sync adapter pulls from Supabase; local copy enables offline tab filtering.
  static const String createProjectAssignmentsTable = '''
    CREATE TABLE IF NOT EXISTS project_assignments (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      user_id TEXT NOT NULL,
      assigned_by TEXT NOT NULL,
      company_id TEXT NOT NULL,
      assigned_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      UNIQUE(project_id, user_id),
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
  ''';
```

#### Step 2.1.2: DO NOT add project_assignments to triggeredTables

**REVIEW FIX (CRIT-2):** Do NOT add `project_assignments` to `triggeredTables`.

The spec says "Pull-only on inspector devices (they never write assignments)." If we add
change_log triggers, the auto-enrollment INSERT in `onPullComplete` will fire the trigger
(even with pulling=1 guard, the admin/engineer direct writes would fire it), and inspectors
would accumulate permanent sync-queue failures because the RLS INSERT policy blocks them.

Instead, the `ProjectAssignmentAdapter` handles push for admin/engineer devices only.
The adapter should check the user's role before pushing, and skip push entirely for inspectors.
Add this to the adapter in Phase 4:

```dart
  // REVIEW FIX (CRIT-2): Only admin/engineer push assignments.
  // Inspector devices are pull-only for this table.
  // Change_log triggers are NOT installed — push is adapter-driven.
  bool get pushEnabled => true; // Engine checks role at push time
```

The implementing agent must ensure that change_log triggers are NOT installed for
`project_assignments`. The adapter relies on direct Supabase writes from the
`ProjectAssignmentProvider.save()` method (which runs on admin/engineer devices only),
not on change_log-driven push.

#### Step 2.1.3: Add project_assignments indexes

In `lib/core/database/schema/sync_engine_tables.dart`, add to the `indexes` list:

```dart
    'CREATE INDEX IF NOT EXISTS idx_project_assignments_project ON project_assignments(project_id)',
    'CREATE INDEX IF NOT EXISTS idx_project_assignments_user ON project_assignments(user_id)',
    'CREATE INDEX IF NOT EXISTS idx_project_assignments_company ON project_assignments(company_id)',
```

#### Step 2.1.4: Add unassigned_at column to createSyncedProjectsTable

In `lib/core/database/schema/sync_engine_tables.dart`, modify the `createSyncedProjectsTable` constant to add `unassigned_at`:

```dart
  // FROM SPEC Section 2: synced_projects gains unassigned_at for visual badge
  static const String createSyncedProjectsTable = '''
    CREATE TABLE IF NOT EXISTS synced_projects (
      project_id TEXT PRIMARY KEY,
      synced_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      unassigned_at TEXT
    )
  ''';
```

#### Step 2.1.5: Wire table creation in _onCreate

In `lib/core/database/database_service.dart`, inside `_onCreate` (after line ~165, the storage_cleanup_queue line), add:

```dart
    // FROM SPEC: project_assignments local mirror for offline tab filtering
    await db.execute(SyncEngineTables.createProjectAssignmentsTable);
```

#### Step 2.1.6: Bump DB version to 37 and add migration

In `lib/core/database/database_service.dart`:

1. Change `version: 36` to `version: 37` in both `_initDatabase` (line 53) and `_initInMemoryDatabase` (line 79).

2. Add migration at end of `_onUpgrade` (after the `if (oldVersion < 36)` block):

```dart
    // FROM SPEC: Phase 2 — project_assignments table + synced_projects.unassigned_at
    if (oldVersion < 37) {
      // Create project_assignments table
      await db.execute(SyncEngineTables.createProjectAssignmentsTable);

      // Add unassigned_at to synced_projects
      await _addColumnIfNotExists(db, 'synced_projects', 'unassigned_at', 'TEXT');

      // Create indexes
      await db.execute(
        'CREATE INDEX IF NOT EXISTS idx_project_assignments_project ON project_assignments(project_id)',
      );
      await db.execute(
        'CREATE INDEX IF NOT EXISTS idx_project_assignments_user ON project_assignments(user_id)',
      );
      await db.execute(
        'CREATE INDEX IF NOT EXISTS idx_project_assignments_company ON project_assignments(company_id)',
      );

      // REVIEW FIX (CRIT-2): Do NOT install change_log triggers for project_assignments.
      // This table uses adapter-driven push (admin/engineer only), not trigger-driven push.
      // Installing triggers would cause RLS denial storms on inspector devices.
    }
```

#### Step 2.1.7: Verify

Run: `pwsh -Command "flutter test test/features/projects/data/services/project_lifecycle_service_test.dart"`
Expected: All existing tests PASS (schema change is additive, no breakage).

Run: `pwsh -Command "flutter analyze lib/core/database/"`
Expected: No new analysis errors.

---

## Phase 3: Data Layer (Model + Repository)

### Sub-phase 3.1: ProjectAssignment Model

**Files:**
- Create: `lib/features/projects/data/models/project_assignment.dart`

**Agent:** `backend-data-layer-agent`

#### Step 3.1.1: Create the model

Create `lib/features/projects/data/models/project_assignment.dart`:

```dart
import 'package:uuid/uuid.dart';

/// Represents a project-to-user assignment.
///
/// FROM SPEC Section 2: Assignments are organizational (not access-control).
/// They control what appears in "My Projects" and who is formally placed
/// on a project by an admin/engineer.
class ProjectAssignment {
  final String id;
  final String projectId;
  final String userId;
  final String assignedBy;
  final String companyId;
  final DateTime assignedAt;
  final DateTime updatedAt;

  ProjectAssignment({
    String? id,
    required this.projectId,
    required this.userId,
    required this.assignedBy,
    required this.companyId,
    DateTime? assignedAt,
    DateTime? updatedAt,
  })  : id = id ?? const Uuid().v4(),
        assignedAt = assignedAt ?? DateTime.now(),
        updatedAt = updatedAt ?? DateTime.now();

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'project_id': projectId,
      'user_id': userId,
      'assigned_by': assignedBy,
      'company_id': companyId,
      'assigned_at': assignedAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  factory ProjectAssignment.fromMap(Map<String, dynamic> map) {
    return ProjectAssignment(
      id: map['id'] as String,
      projectId: map['project_id'] as String,
      userId: map['user_id'] as String,
      assignedBy: map['assigned_by'] as String,
      companyId: map['company_id'] as String,
      assignedAt: DateTime.parse(map['assigned_at'] as String),
      updatedAt: DateTime.parse(map['updated_at'] as String),
    );
  }
}
```

### Sub-phase 3.2: ProjectAssignment Repository

**Files:**
- Create: `lib/features/projects/data/repositories/project_assignment_repository.dart`

**Agent:** `backend-data-layer-agent`

#### Step 3.2.1: Create the repository

Create `lib/features/projects/data/repositories/project_assignment_repository.dart`:

```dart
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:sqflite/sqflite.dart';
import '../models/project_assignment.dart';

/// Repository for project_assignments CRUD.
///
/// FROM SPEC Section 2: Local SQLite operations. Supabase writes are
/// handled by the sync engine via ProjectAssignmentAdapter.
class ProjectAssignmentRepository {
  final DatabaseService _dbService;

  ProjectAssignmentRepository(this._dbService);

  Future<Database> get _db => _dbService.database;

  /// Get all assignments for a project.
  Future<List<ProjectAssignment>> getByProject(String projectId) async {
    final db = await _db;
    final rows = await db.query(
      'project_assignments',
      where: 'project_id = ?',
      whereArgs: [projectId],
    );
    return rows.map(ProjectAssignment.fromMap).toList();
  }

  /// Get all assignments for the current user.
  Future<List<ProjectAssignment>> getByUser(String userId) async {
    final db = await _db;
    final rows = await db.query(
      'project_assignments',
      where: 'user_id = ?',
      whereArgs: [userId],
    );
    return rows.map(ProjectAssignment.fromMap).toList();
  }

  /// Get project IDs assigned to a user.
  Future<Set<String>> getAssignedProjectIds(String userId) async {
    final db = await _db;
    final rows = await db.query(
      'project_assignments',
      columns: ['project_id'],
      where: 'user_id = ?',
      whereArgs: [userId],
    );
    return rows.map((r) => r['project_id'] as String).toSet();
  }

  /// Insert a single assignment.
  Future<void> insert(ProjectAssignment assignment) async {
    final db = await _db;
    await db.insert(
      'project_assignments',
      assignment.toMap(),
      conflictAlgorithm: ConflictAlgorithm.ignore,
    );
  }

  /// Bulk-insert assignments (used by wizard save).
  Future<void> insertAll(List<ProjectAssignment> assignments) async {
    final db = await _db;
    final batch = db.batch();
    for (final a in assignments) {
      batch.insert(
        'project_assignments',
        a.toMap(),
        conflictAlgorithm: ConflictAlgorithm.ignore,
      );
    }
    await batch.commit(noResult: true);
    Logger.db('Inserted ${assignments.length} project assignments');
  }

  /// Delete an assignment by project + user.
  Future<void> deleteByProjectAndUser(String projectId, String userId) async {
    final db = await _db;
    await db.delete(
      'project_assignments',
      where: 'project_id = ? AND user_id = ?',
      whereArgs: [projectId, userId],
    );
  }

  /// Delete all assignments for a project (used when replacing assignments on save).
  Future<void> deleteAllForProject(String projectId) async {
    final db = await _db;
    await db.delete(
      'project_assignments',
      where: 'project_id = ?',
      whereArgs: [projectId],
    );
  }
}
```

### Sub-phase 3.3: Extend MergedProjectEntry

**Files:**
- Modify: `lib/features/projects/data/models/merged_project_entry.dart:10-30`

**Agent:** `backend-data-layer-agent`

#### Step 3.3.1: Add isArchived, isAssigned, unassignedAt fields

In `lib/features/projects/data/models/merged_project_entry.dart`, add three new fields:

```dart
class MergedProjectEntry {
  final Project project;
  final bool isLocal;
  final bool isRemoteOnly;
  final bool isLocalOnly;

  // FROM SPEC Section 4: Two-badge system needs archived + assignment state
  /// True when project.isActive == false (admin/engineer archived it).
  final bool isArchived;

  /// True when the current user has a project_assignment row for this project.
  final bool isAssigned;

  /// Non-null if the user was previously assigned but has since been unassigned.
  /// FROM SPEC Section 2: set on synced_projects row, NOT deleted.
  final String? unassignedAt;

  const MergedProjectEntry({
    required this.project,
    required this.isLocal,
    required this.isRemoteOnly,
    this.isLocalOnly = false,
    this.isArchived = false,
    this.isAssigned = false,
    this.unassignedAt,
  });
}
```

#### Step 3.3.2: Verify

Run: `pwsh -Command "flutter analyze lib/features/projects/data/"`
Expected: No analysis errors. Existing callers of MergedProjectEntry use named parameters — new fields have defaults, so no breakage.

---

## Phase 4: Sync Adapter

### Sub-phase 4.1: ProjectAssignmentAdapter

**Files:**
- Create: `lib/features/sync/adapters/project_assignment_adapter.dart`
- Modify: `lib/features/sync/engine/sync_registry.dart:23-42`

**Agent:** `backend-supabase-agent`

#### Step 4.1.1: Create the adapter

Create `lib/features/sync/adapters/project_assignment_adapter.dart`:

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

/// Sync adapter for the project_assignments table.
///
/// FROM SPEC Section 2 (Sync Considerations):
/// - ScopeType.direct — uses company_id filter (like projects)
/// - SELECT RLS scopes data by role: inspectors get own rows, admins/engineers get all (SC-7)
/// - No soft-delete support: assignments are hard-deleted
class ProjectAssignmentAdapter extends TableAdapter {
  @override
  String get tableName => 'project_assignments';

  // WHY: ScopeType.direct because project_assignments has its own company_id column.
  // The engine uses company_id = ? filter for pull, matching the ProjectAdapter pattern.
  @override
  ScopeType get scopeType => ScopeType.direct;

  // WHY: project_assignments depends on projects existing first.
  // The projects adapter runs before this one in FK dependency order.
  @override
  List<String> get fkDependencies => const ['projects'];

  // NOTE: Assignments use hard delete (no deleted_at/deleted_by columns).
  // The Supabase RLS DELETE policy handles authorization.
  @override
  bool get supportsSoftDelete => false;
}
```

#### Step 4.1.2: Register adapter in sync_registry.dart

In `lib/features/sync/engine/sync_registry.dart`, add the import at top:

```dart
import 'package:construction_inspector/features/sync/adapters/project_assignment_adapter.dart';
```

Then add `ProjectAssignmentAdapter()` to the adapter list, after `ProjectAdapter()` (since it depends on projects):

```dart
void registerSyncAdapters() {
  SyncRegistry.instance.registerAdapters([
    ProjectAdapter(),
    ProjectAssignmentAdapter(), // FROM SPEC: must come after ProjectAdapter (FK dep)
    LocationAdapter(),
    // ... rest unchanged
  ]);
}
```

#### Step 4.1.3: Verify

Run: `pwsh -Command "flutter analyze lib/features/sync/"`
Expected: No analysis errors.

### Sub-phase 4.2: Add onPullComplete Callback to SyncEngine

**Files:**
- Modify: `lib/features/sync/engine/sync_engine.dart:1089-1254`

**Agent:** `backend-supabase-agent`

#### Step 4.2.1: Add onPullComplete callback field

In `lib/features/sync/engine/sync_engine.dart`, add a callback field to the SyncEngine class (near the other callback fields like `onProgress`):

```dart
  /// FROM SPEC Section 2 (Sync Considerations):
  /// Called after each table's pull completes with the pulled rows and current user ID.
  /// Used by the assignment flow to detect new assignments for the current user
  /// and auto-enroll them into synced_projects.
  Future<void> Function(String tableName, int pulledCount)? onPullComplete;
```

#### Step 4.2.2: Call onPullComplete in _pullTable

In `lib/features/sync/engine/sync_engine.dart`, inside `_pullTable()`, add the callback invocation AFTER the while loop completes but BEFORE the cursor update (between line ~1242 and line ~1244):

```dart
    // FROM SPEC Section 2 (MF-5): Notify listeners after pull completes for this table.
    // WHY: Assignment adapter uses this to detect new assignments and auto-enroll.
    if (totalPulled > 0 && onPullComplete != null) {
      await onPullComplete!(adapter.tableName, totalPulled);
    }

    // Update cursor
    if (maxUpdatedAt != null) {
```

#### Step 4.2.3: Verify

Run: `pwsh -Command "flutter analyze lib/features/sync/engine/"`
Expected: No analysis errors.

---

## Phase 5: Provider Layer

### Sub-phase 5.1: Extend ProjectProvider with Tab State + Computed Lists

**Files:**
- Modify: `lib/features/projects/presentation/providers/project_provider.dart:14-547`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 5.1.1: Add imports

At top of `lib/features/projects/presentation/providers/project_provider.dart`, add:

```dart
import '../../../data/repositories/project_assignment_repository.dart';
```

#### Step 5.1.2: Add tab state fields

In the `// State` section (after line ~53), add:

```dart
  // FROM SPEC Section 5: Tab state for 3-tab layout
  int _currentTabIndex = 0;
  CompanyFilter _companyFilter = CompanyFilter.all;

  // FROM SPEC Section 5: Assignment-aware computed lists
  Set<String> _assignedProjectIds = {};
  Map<String, String?> _syncedProjectUnassignedAt = {};
```

#### Step 5.1.3: Add CompanyFilter enum

At the TOP of the file (before the class), add:

```dart
/// FROM SPEC Section 4: Filter chips on Company tab.
enum CompanyFilter { all, onDevice, notDownloaded }
```

#### Step 5.1.4: Add tab state getters

In the `// Getters` section, add:

```dart
  /// Current tab index (0=My Projects, 1=Company, 2=Archived).
  int get currentTabIndex => _currentTabIndex;

  /// Current filter for Company tab.
  CompanyFilter get companyFilter => _companyFilter;

  /// FROM SPEC Section 5: My Projects = local + assigned (or self-enrolled), not archived.
  List<MergedProjectEntry> get myProjects => _mergedProjects
      .where((e) => e.isLocal && !e.isArchived)
      .toList();

  /// FROM SPEC Section 5: Company = all active company projects (for browsing).
  List<MergedProjectEntry> get companyProjects {
    final active = _mergedProjects.where((e) => !e.isArchived).toList();
    switch (_companyFilter) {
      case CompanyFilter.all:
        return active;
      case CompanyFilter.onDevice:
        return active.where((e) => e.isLocal).toList();
      case CompanyFilter.notDownloaded:
        return active.where((e) => e.isRemoteOnly).toList();
    }
  }

  /// FROM SPEC Section 5: Archived = projects where isActive == false.
  List<MergedProjectEntry> get archivedProjects => _mergedProjects
      .where((e) => e.isArchived)
      .toList();

  /// Badge counts for tab bar.
  int get myProjectsCount => myProjects.length;
  int get companyProjectsCount =>
      _mergedProjects.where((e) => !e.isArchived).length;
  int get archivedProjectsCount => archivedProjects.length;
```

#### Step 5.1.5: Add tab state setters

In the `// Actions` section, add:

```dart
  /// Set the active tab index.
  void setTabIndex(int index) {
    if (_currentTabIndex != index) {
      _currentTabIndex = index;
      notifyListeners();
    }
  }

  /// Set the Company tab filter.
  void setCompanyFilter(CompanyFilter filter) {
    if (_companyFilter != filter) {
      _companyFilter = filter;
      notifyListeners();
    }
  }

  /// Load assignment state for the current user.
  /// Called during initialization and after sync completes.
  Future<void> loadAssignments(String userId, DatabaseService dbService) async {
    try {
      final db = await dbService.database;

      // Load assigned project IDs
      final assignmentRows = await db.query(
        'project_assignments',
        columns: ['project_id'],
        where: 'user_id = ?',
        whereArgs: [userId],
      );
      _assignedProjectIds = assignmentRows
          .map((r) => r['project_id'] as String)
          .toSet();

      // Load synced_projects unassigned_at
      final syncedRows = await db.query('synced_projects');
      _syncedProjectUnassignedAt = {
        for (final r in syncedRows)
          r['project_id'] as String: r['unassigned_at'] as String?,
      };

      _buildMergedView();
      notifyListeners();
    } catch (e) {
      Logger.sync('Failed to load assignments: $e');
    }
  }

  /// Enroll a project on this device (add to synced_projects).
  /// FROM SPEC Section 3: Inspector self-enrolls from Company tab.
  Future<void> enrollProject(String projectId, DatabaseService dbService) async {
    try {
      final db = await dbService.database;
      await db.insert(
        'synced_projects',
        {
          'project_id': projectId,
          'synced_at': DateTime.now().toUtc().toIso8601String(),
        },
        conflictAlgorithm: ConflictAlgorithm.ignore,
      );
      Logger.sync('Enrolled project: $projectId');
    } catch (e) {
      Logger.sync('Failed to enroll project: $e');
      rethrow;
    }
  }

  /// Unenroll a project from this device (remove from synced_projects + local data).
  /// FROM SPEC Section 3: Multi-step removal dialog handles sync-first safety.
  Future<void> unenrollProject(String projectId, DatabaseService dbService) async {
    try {
      final db = await dbService.database;
      await db.delete(
        'synced_projects',
        where: 'project_id = ?',
        whereArgs: [projectId],
      );
      Logger.sync('Unenrolled project: $projectId');
    } catch (e) {
      Logger.sync('Failed to unenroll project: $e');
      rethrow;
    }
  }
```

#### Step 5.1.6: Update _buildMergedView to include assignment + archived state

Replace the existing `_buildMergedView` method in `project_provider.dart`:

```dart
  /// Merge [_projects] (enrolled/local) and [_remoteProjects] (unenrolled),
  /// deduplicating by project id. Local entries take precedence.
  ///
  /// FROM SPEC Section 5: Single-pass computation with assignment + archived state.
  void _buildMergedView() {
    final remoteIds = _remoteProjects.map((p) => p.id).toSet();
    final merged = <String, MergedProjectEntry>{};

    // Add local projects first -- local takes precedence
    for (final p in _projects) {
      merged[p.id] = MergedProjectEntry(
        project: p,
        isLocal: true,
        isRemoteOnly: false,
        isLocalOnly: !remoteIds.contains(p.id),
        isArchived: !p.isActive,
        isAssigned: _assignedProjectIds.contains(p.id),
        unassignedAt: _syncedProjectUnassignedAt[p.id],
      );
    }

    // Add remote-only projects (not already in local)
    for (final p in _remoteProjects) {
      if (p.deletedAt != null) continue; // spec: deleted_at IS NULL
      if (!merged.containsKey(p.id)) {
        merged[p.id] = MergedProjectEntry(
          project: p,
          isLocal: false,
          isRemoteOnly: true,
          isLocalOnly: false,
          isArchived: !p.isActive,
          isAssigned: _assignedProjectIds.contains(p.id),
          unassignedAt: null,
        );
      }
    }

    _mergedProjects = merged.values.toList();
  }
```

#### Step 5.1.7: Verify

Run: `pwsh -Command "flutter analyze lib/features/projects/presentation/providers/project_provider.dart"`
Expected: No analysis errors. The `sqflite` import may be needed for `ConflictAlgorithm` — add `import 'package:sqflite/sqflite.dart';` at top if missing.

### Sub-phase 5.2: Create ProjectAssignmentProvider (Wizard State)

**Files:**
- Create: `lib/features/projects/presentation/providers/project_assignment_provider.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 5.2.1: Create the provider

Create `lib/features/projects/presentation/providers/project_assignment_provider.dart`:

```dart
import 'package:flutter/foundation.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import '../../data/models/project_assignment.dart';
import '../../data/repositories/project_assignment_repository.dart';

/// A lightweight member summary for the assignment wizard UI.
///
/// FROM SPEC Section 4 (AssignmentListTile): Checkbox + name + role badge.
class AssignableMember {
  final String userId;
  final String displayName;
  final String role;

  const AssignableMember({
    required this.userId,
    required this.displayName,
    required this.role,
  });
}

/// In-memory wizard state for project assignments.
///
/// FROM SPEC Section 5 (SC-12): Assignments held in-memory during wizard;
/// only written to DB on final save.
class ProjectAssignmentProvider extends ChangeNotifier {
  final ProjectAssignmentRepository _repository;

  ProjectAssignmentProvider(this._repository);

  // In-memory state
  List<AssignableMember> _companyMembers = [];
  Set<String> _assignedUserIds = {};
  Set<String> _originalAssignedUserIds = {};
  bool _isLoading = false;
  String _searchQuery = '';
  // REVIEW FIX (HIGH-2): Creator is always assigned and can't be unchecked.
  String? _lockedUserId;

  // Getters
  bool get isLoading => _isLoading;
  int get assignedCount => _assignedUserIds.length;

  /// Members filtered by search query.
  List<AssignableMember> get filteredMembers {
    if (_searchQuery.isEmpty) return _companyMembers;
    final q = _searchQuery.toLowerCase();
    return _companyMembers.where((m) {
      return m.displayName.toLowerCase().contains(q) ||
          m.role.toLowerCase().contains(q);
    }).toList();
  }

  /// Whether a user is currently assigned (in-memory toggle state).
  bool isAssigned(String userId) => _assignedUserIds.contains(userId);

  /// Whether there are unsaved changes.
  bool get hasChanges => !setEquals(_assignedUserIds, _originalAssignedUserIds);

  /// Set the search query for filtering the member list.
  void setSearchQuery(String query) {
    _searchQuery = query;
    notifyListeners();
  }

  /// Load current assignments + company members for the wizard.
  ///
  /// [companyMembers] is pre-fetched from Supabase user_profiles
  /// by the calling screen (avoids direct Supabase dependency here).
  Future<void> loadForProject({
    required String projectId,
    required List<AssignableMember> companyMembers,
    String? creatorUserId, // REVIEW FIX (HIGH-2): Lock the creator
  }) async {
    _isLoading = true;
    notifyListeners();

    try {
      _companyMembers = companyMembers;
      _lockedUserId = creatorUserId;

      // Load existing assignments from local DB
      final existing = await _repository.getByProject(projectId);
      _assignedUserIds = existing.map((a) => a.userId).toSet();
      // REVIEW FIX (HIGH-2): Auto-assign creator if not already assigned
      if (creatorUserId != null) _assignedUserIds.add(creatorUserId);
      _originalAssignedUserIds = Set.from(_assignedUserIds);
      _searchQuery = '';
    } catch (e) {
      Logger.db('Failed to load assignments for project $projectId: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Whether a user is the locked creator (cannot be unassigned).
  bool isLocked(String userId) => userId == _lockedUserId;

  /// Toggle a user's assignment in-memory.
  /// FROM SPEC Section 5: Toggle in-memory, only write on save.
  /// REVIEW FIX (HIGH-2): Creator can't be unchecked.
  void toggleAssignment(String userId) {
    if (userId == _lockedUserId) return; // Creator is locked
    if (_assignedUserIds.contains(userId)) {
      _assignedUserIds.remove(userId);
    } else {
      _assignedUserIds.add(userId);
    }
    notifyListeners();
  }

  /// Save assignments to local DB.
  ///
  /// FROM SPEC Section 5: Diff against original, insert new, delete removed.
  /// Returns the list of newly added assignments (for sync tracking).
  Future<List<ProjectAssignment>> save({
    required String projectId,
    required String assignedBy,
    required String companyId,
  }) async {
    final added = _assignedUserIds.difference(_originalAssignedUserIds);
    final removed = _originalAssignedUserIds.difference(_assignedUserIds);

    // Delete removed assignments
    for (final userId in removed) {
      await _repository.deleteByProjectAndUser(projectId, userId);
    }

    // Insert new assignments
    final newAssignments = added.map((userId) => ProjectAssignment(
      projectId: projectId,
      userId: userId,
      assignedBy: assignedBy,
      companyId: companyId,
    )).toList();

    if (newAssignments.isNotEmpty) {
      await _repository.insertAll(newAssignments);
    }

    Logger.db('Saved assignments: +${added.length} -${removed.length} for project $projectId');

    // Update original to match current
    _originalAssignedUserIds = Set.from(_assignedUserIds);
    notifyListeners();

    return newAssignments;
  }

  /// Clear wizard state.
  void clear() {
    _companyMembers = [];
    _assignedUserIds = {};
    _originalAssignedUserIds = {};
    _searchQuery = '';
    _isLoading = false;
    notifyListeners();
  }
}
```

#### Step 5.2.2: Verify

Run: `pwsh -Command "flutter analyze lib/features/projects/presentation/providers/project_assignment_provider.dart"`
Expected: No analysis errors.

### Sub-phase 5.3: Extend SyncProvider with Pending Notifications

**Files:**
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart:18-260`

**Agent:** `backend-supabase-agent`

#### Step 5.3.1: Add pending notifications state

In `lib/features/sync/presentation/providers/sync_provider.dart`, add fields and methods:

Add field after `_circuitBreakerDismissedAt` (line ~36):

```dart
  // FROM SPEC Section 5 (SC-9): Pending notifications queue.
  // Assignment adapter's onPullComplete adds messages. UI shows snackbars after sync.
  final List<String> _pendingNotifications = [];

  /// Pending notification messages to show after sync completes.
  List<String> get pendingNotifications => List.unmodifiable(_pendingNotifications);
```

Add methods:

```dart
  /// Add a notification to the pending queue.
  /// Called by the auto-enrollment logic after sync detects a new assignment.
  void addNotification(String message) {
    _pendingNotifications.add(message);
    // NOTE: Don't notifyListeners here — batch notifications are shown after sync completes.
  }

  /// Clear all pending notifications after the UI has displayed them.
  void clearNotifications() {
    _pendingNotifications.clear();
    // No notifyListeners needed — UI already consumed the messages.
  }
```

#### Step 5.3.2: Verify

Run: `pwsh -Command "flutter analyze lib/features/sync/presentation/providers/sync_provider.dart"`
Expected: No analysis errors.

---

## Phase 6: UI Widgets

### Sub-phase 6.1: ProjectEmptyState Widget

**Files:**
- Create: `lib/features/projects/presentation/widgets/project_empty_state.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 6.1.1: Create empty state widget

Create `lib/features/projects/presentation/widgets/project_empty_state.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/theme/app_theme.dart';

/// FROM SPEC Section 4 (Empty States): 4 variants depending on context.
enum EmptyStateVariant {
  /// My Projects tab: "No projects on your device" + Browse CTA.
  myProjects,

  /// Company tab: no projects at all in company.
  noCompanyProjects,

  /// Company tab: filter yields no results.
  filteredEmpty,

  /// Archived tab: no archived projects.
  archived,
}

class ProjectEmptyState extends StatelessWidget {
  final EmptyStateVariant variant;
  final VoidCallback? onBrowse;

  const ProjectEmptyState({
    super.key,
    required this.variant,
    this.onBrowse,
  });

  @override
  Widget build(BuildContext context) {
    final (icon, title, subtitle, showButton) = switch (variant) {
      EmptyStateVariant.myProjects => (
        Icons.folder_open,
        'No projects on your device',
        'Browse available projects to get started.',
        true,
      ),
      EmptyStateVariant.noCompanyProjects => (
        Icons.business,
        'No company projects yet',
        'Ask your admin to create one.',
        false,
      ),
      EmptyStateVariant.filteredEmpty => (
        Icons.filter_list_off,
        'No projects match this filter',
        'Try a different filter.',
        false,
      ),
      EmptyStateVariant.archived => (
        Icons.archive_outlined,
        'No archived projects',
        'Completed projects will appear here.',
        false,
      ),
    };

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 64, color: AppTheme.textSecondary),
            const SizedBox(height: 16),
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              subtitle,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: AppTheme.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            if (showButton && onBrowse != null) ...[
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: onBrowse,
                icon: const Icon(Icons.search),
                label: const Text('Browse Available Projects'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
```

### Sub-phase 6.2: ProjectTabBar Widget

**Files:**
- Create: `lib/features/projects/presentation/widgets/project_tab_bar.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 6.2.1: Create tab bar widget

Create `lib/features/projects/presentation/widgets/project_tab_bar.dart`:

```dart
import 'package:flutter/material.dart';

/// FROM SPEC Section 4: TabBar with 3 tabs + badge counts.
/// My Projects (N) | Company (N) | Archived (N)
class ProjectTabBar extends StatelessWidget implements PreferredSizeWidget {
  final TabController controller;
  final int myProjectsCount;
  final int companyCount;
  final int archivedCount;

  const ProjectTabBar({
    super.key,
    required this.controller,
    required this.myProjectsCount,
    required this.companyCount,
    required this.archivedCount,
  });

  @override
  Size get preferredSize => const Size.fromHeight(kTextTabBarHeight);

  @override
  Widget build(BuildContext context) {
    return TabBar(
      controller: controller,
      tabs: [
        _buildTab('My Projects', myProjectsCount),
        _buildTab('Company', companyCount),
        _buildTab('Archived', archivedCount),
      ],
    );
  }

  Widget _buildTab(String label, int count) {
    return Tab(
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label),
          if (count > 0) ...[
            const SizedBox(width: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: Colors.grey.shade200,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                '$count',
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
```

### Sub-phase 6.3: ProjectFilterChips Widget

**Files:**
- Create: `lib/features/projects/presentation/widgets/project_filter_chips.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 6.3.1: Create filter chips widget

Create `lib/features/projects/presentation/widgets/project_filter_chips.dart`:

```dart
import 'package:flutter/material.dart';
import '../providers/project_provider.dart';

/// FROM SPEC Section 4: Filter chips for Company tab.
/// All | On Device | Not Downloaded
class ProjectFilterChips extends StatelessWidget {
  final CompanyFilter selected;
  final ValueChanged<CompanyFilter> onChanged;

  const ProjectFilterChips({
    super.key,
    required this.selected,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Wrap(
        spacing: 8,
        children: CompanyFilter.values.map((filter) {
          final label = switch (filter) {
            CompanyFilter.all => 'All',
            CompanyFilter.onDevice => 'On Device',
            CompanyFilter.notDownloaded => 'Not Downloaded',
          };
          return FilterChip(
            label: Text(label),
            selected: selected == filter,
            onSelected: (_) => onChanged(filter),
          );
        }).toList(),
      ),
    );
  }
}
```

### Sub-phase 6.4: RemovalDialog Widget

**Files:**
- Create: `lib/features/projects/presentation/widgets/removal_dialog.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 6.4.1: Create multi-step removal dialog

Create `lib/features/projects/presentation/widgets/removal_dialog.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/theme/app_theme.dart';

/// FROM SPEC Section 3: Multi-step unenrollment dialog.
/// Options: Sync & Remove / Delete from Device / Cancel
enum RemovalChoice { syncAndRemove, deleteFromDevice, cancel }

class RemovalDialog extends StatelessWidget {
  final String projectName;
  final bool hasPendingChanges;
  final bool isOnline; // REVIEW FIX (HIGH-3): Greyed out Sync & Remove when offline

  const RemovalDialog({
    super.key,
    required this.projectName,
    required this.hasPendingChanges,
    required this.isOnline,
  });

  /// Show the removal dialog and return the user's choice.
  static Future<RemovalChoice> show({
    required BuildContext context,
    required String projectName,
    required bool hasPendingChanges,
    required bool isOnline,
  }) async {
    final result = await showDialog<RemovalChoice>(
      context: context,
      builder: (_) => RemovalDialog(
        projectName: projectName,
        hasPendingChanges: hasPendingChanges,
        isOnline: isOnline,
      ),
    );
    return result ?? RemovalChoice.cancel;
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Remove Project'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Remove "$projectName" from this device?'),
          if (hasPendingChanges) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.statusWarning.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.statusWarning),
              ),
              child: const Row(
                children: [
                  Icon(Icons.warning_amber, color: AppTheme.statusWarning, size: 20),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'This project has unsynced changes. '
                      'Removing without syncing will lose local edits.',
                      style: TextStyle(fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(RemovalChoice.cancel),
          child: const Text('Cancel'),
        ),
        if (hasPendingChanges)
          Tooltip(
            message: isOnline ? '' : 'You\'re offline — sync unavailable',
            child: TextButton(
              // REVIEW FIX (HIGH-3): FROM SPEC Section 6: Greyed out with tooltip when offline
              onPressed: isOnline
                  ? () => Navigator.of(context).pop(RemovalChoice.syncAndRemove)
                  : null,
              child: const Text('Sync & Remove'),
            ),
          ),
        TextButton(
          onPressed: () => Navigator.of(context).pop(RemovalChoice.deleteFromDevice),
          style: TextButton.styleFrom(foregroundColor: AppTheme.statusError),
          child: const Text('Delete from Device'),
        ),
      ],
    );
  }
}
```

### Sub-phase 6.5: AssignmentsStep Widget (Wizard)

**Files:**
- Create: `lib/features/projects/presentation/widgets/assignments_step.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 6.5.1: Create the wizard step widget

Create `lib/features/projects/presentation/widgets/assignments_step.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/theme/app_theme.dart';
import '../providers/project_assignment_provider.dart';

/// FROM SPEC Section 4 (AssignmentsStep): Wizard step with searchable member list.
/// Admin/engineer assigns team members via checkbox list.
class AssignmentsStep extends StatelessWidget {
  const AssignmentsStep({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<ProjectAssignmentProvider>(
      builder: (context, provider, _) {
        if (provider.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }

        final members = provider.filteredMembers;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Search bar
            Padding(
              padding: const EdgeInsets.all(16),
              child: TextField(
                decoration: InputDecoration(
                  hintText: 'Search members...',
                  prefixIcon: const Icon(Icons.search),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12),
                ),
                onChanged: provider.setSearchQuery,
              ),
            ),
            // Assigned count
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                '${provider.assignedCount} member${provider.assignedCount == 1 ? '' : 's'} assigned',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppTheme.textSecondary,
                ),
              ),
            ),
            const SizedBox(height: 8),
            // Member list
            Expanded(
              child: members.isEmpty
                  ? const Center(
                      child: Text('No members found'),
                    )
                  : ListView.builder(
                      itemCount: members.length,
                      itemBuilder: (context, index) {
                        final member = members[index];
                        final assigned = provider.isAssigned(member.userId);
                        final locked = provider.isLocked(member.userId);
                        return AssignmentListTile(
                          member: member,
                          isAssigned: assigned,
                          isLocked: locked,
                          onToggle: locked ? null : () => provider.toggleAssignment(member.userId),
                        );
                      },
                    ),
            ),
          ],
        );
      },
    );
  }
}

/// FROM SPEC Section 4 (AssignmentListTile): Checkbox + name + role badge.
class AssignmentListTile extends StatelessWidget {
  final AssignableMember member;
  final bool isAssigned;
  final bool isLocked; // REVIEW FIX (HIGH-2): Creator can't be unchecked
  final VoidCallback? onToggle;

  const AssignmentListTile({
    super.key,
    required this.member,
    required this.isAssigned,
    this.isLocked = false,
    this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Checkbox(
        value: isAssigned,
        onChanged: isLocked ? null : (_) => onToggle?.call(),
      ),
      title: Text(member.displayName),
      subtitle: isLocked ? const Text('Creator', style: TextStyle(fontSize: 11)) : null,
      trailing: _RoleBadge(role: member.role),
      onTap: isLocked ? null : onToggle,
    );
  }
}

class _RoleBadge extends StatelessWidget {
  final String role;

  const _RoleBadge({required this.role});

  @override
  Widget build(BuildContext context) {
    final (color, label) = switch (role) {
      'admin' => (Colors.purple, 'Admin'),
      'engineer' => (Colors.blue, 'Engineer'),
      'inspector' => (Colors.green, 'Inspector'),
      _ => (Colors.grey, role),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }
}
```

### Sub-phase 6.6: Update widgets barrel export

**Files:**
- Modify: `lib/features/projects/presentation/widgets/widgets.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 6.6.1: Add new widget exports

Append to `lib/features/projects/presentation/widgets/widgets.dart`:

```dart
export 'project_empty_state.dart';
export 'project_tab_bar.dart';
export 'project_filter_chips.dart';
export 'removal_dialog.dart';
export 'assignments_step.dart';
```

#### Step 6.6.2: Verify all widgets compile

Run: `pwsh -Command "flutter analyze lib/features/projects/presentation/widgets/"`
Expected: No analysis errors.

---

## Phase 7: Project List Screen Rewrite

### Sub-phase 7.1: Rewrite project_list_screen.dart with 3-Tab Layout

**Files:**
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart:20-897`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 7.1.1: Replace class definition with TabController mixin

Replace the `_ProjectListScreenState` class to add `SingleTickerProviderStateMixin` and a `TabController`:

In the state class declaration, change:

```dart
class _ProjectListScreenState extends State<ProjectListScreen> {
```
to:
```dart
class _ProjectListScreenState extends State<ProjectListScreen>
    with SingleTickerProviderStateMixin {
```

#### Step 7.1.2: Add TabController and init

Replace the state fields and initState:

```dart
  bool _isSearching = false;
  final _searchController = TextEditingController();
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(() {
      if (!_tabController.indexIsChanging) {
        context.read<ProjectProvider>().setTabIndex(_tabController.index);
      }
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _refresh();
      // FROM SPEC: Load assignments for the current user
      final authProvider = context.read<AuthProvider>();
      final userId = authProvider.userId;
      if (userId != null) {
        context.read<ProjectProvider>().loadAssignments(
          userId,
          context.read<DatabaseService>(),
        );
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }
```

#### Step 7.1.3: Rewrite the build method with TabBarView

Replace the existing `build` method with a 3-tab layout. The full implementation should:

1. Use `Consumer<ProjectProvider>` for the body.
2. Add `ProjectTabBar` in the `AppBar.bottom`.
3. Use `TabBarView` with 3 children: My Projects list, Company list (with filter chips), Archived list.
4. Each tab uses `ListView.builder` for performance (FROM SPEC Section 9).
5. Each tab shows `ProjectEmptyState` when empty.
6. My Projects empty state has `onBrowse` that switches to Company tab.
7. Company tab has `ProjectFilterChips` at top.
8. Project cards show two-badge system: location badge (On Device green / Remote grey) + lifecycle badge (Active cyan / Archived amber / Unassigned red outline).

The AppBar should include:
- Search toggle icon.
- Conditionally show "+" FAB only for admin/engineer roles (FROM SPEC: project creation restricted to Admin + Engineer).

Key implementation pattern for each tab's project list:

```dart
Widget _buildProjectList(List<MergedProjectEntry> projects) {
  return ListView.builder(
    // FROM SPEC Section 9: ListView.builder for performance
    itemCount: projects.length,
    itemBuilder: (context, index) {
      final entry = projects[index];
      return _buildProjectCard(entry);
    },
  );
}
```

The project card should include:
- Project name and number.
- Location badge: green "On Device" chip if `isLocal`, grey "Remote" if not.
- Lifecycle badge: cyan "Active" if `!isArchived`, amber "Archived" if `isArchived`, red outline "Unassigned" if `unassignedAt != null`.
- Contextual tap actions per the spec's tab/action matrix.

For the Company tab's "Not Downloaded" cards, tap should show a download confirmation dialog, then call `enrollProject` + trigger sync.

For My Projects long-press, show `RemovalDialog`.

#### Step 7.1.4: Verify

Run: `pwsh -Command "flutter analyze lib/features/projects/presentation/screens/project_list_screen.dart"`
Expected: No analysis errors.

---

## Phase 8: Project Setup Wizard (Assignments Tab)

### Sub-phase 8.1: Add 5th Tab to Setup Wizard

**Files:**
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart:38-849`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 8.1.1: Add import for AssignmentsStep and provider

At top of `project_setup_screen.dart`, add:

```dart
import 'package:construction_inspector/features/projects/presentation/providers/project_assignment_provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
```

#### Step 8.1.2: Change tab count from 4 to 5

In `initState`, change:

```dart
    _tabController = TabController(
      length: 5, // WHY: FROM SPEC — added Assignments tab as 5th tab
      vsync: this,
      initialIndex: widget.initialTab ?? 0,
    );
```

#### Step 8.1.3: Add "Assignments" tab label

Find the `TabBar` widget in the build method and add a 5th tab:

```dart
  const Tab(text: 'Assignments'),
```

#### Step 8.1.4: Add AssignmentsStep to TabBarView

Find the `TabBarView` children and add the 5th child:

```dart
  // FROM SPEC Section 4: Assignment tab — admin/engineer assigns team members.
  // Only shown when editing (need existing project ID + company members).
  const AssignmentsStep(),
```

#### Step 8.1.5: Load assignments when editing

In the `_loadProjectData` method (or initState's postFrameCallback for editing), add code to load company members and assignments:

```dart
  Future<void> _loadAssignments() async {
    if (_projectId == null) return;

    // FROM SPEC Section 5: Load company members from Supabase for assignment wizard.
    try {
      final authProvider = context.read<AuthProvider>();
      final companyId = authProvider.userProfile?.companyId;
      if (companyId == null) return;

      // Fetch approved company members from Supabase
      final response = await Supabase.instance.client
          .from('user_profiles')
          .select('id, display_name, role')
          .eq('company_id', companyId)
          .eq('status', 'approved');

      final members = (response as List).map((row) {
        return AssignableMember(
          userId: row['id'] as String,
          displayName: (row['display_name'] as String?) ?? 'Unknown',
          role: (row['role'] as String?) ?? 'inspector',
        );
      }).toList();

      if (!mounted) return;
      await context.read<ProjectAssignmentProvider>().loadForProject(
        projectId: _projectId!,
        companyMembers: members,
      );
    } catch (e) {
      Logger.db('Failed to load assignment data: $e');
    }
  }
```

Call `_loadAssignments()` from `_loadProjectData()` (for editing) and from the postFrameCallback (for new projects, only after draft insert).

#### Step 8.1.6: Save assignments in _saveProject

In `_saveProject()`, after the project is successfully saved (around the `if (success)` block), add:

```dart
      // FROM SPEC Section 5 (SC-12): Save assignments on final wizard save.
      if (mounted) {
        try {
          final assignmentProvider = context.read<ProjectAssignmentProvider>();
          if (assignmentProvider.hasChanges) {
            final authProvider = context.read<AuthProvider>();
            // REVIEW FIX (HIGH-4): Guard against null userId — don't write empty string
            final userId = authProvider.userId;
            final companyId = authProvider.userProfile?.companyId;
            if (userId != null && companyId != null) {
              await assignmentProvider.save(
                projectId: _projectId!,
                assignedBy: userId,
                companyId: companyId,
              );
            }
          }
        } catch (e) {
          Logger.db('Failed to save assignments: $e');
          // Non-critical: project was saved successfully
        }
      }
```

#### Step 8.1.7: Verify

Run: `pwsh -Command "flutter analyze lib/features/projects/presentation/screens/project_setup_screen.dart"`
Expected: No analysis errors.

---

## Phase 9: Integration Wiring (main.dart + Sync Hooks)

### Sub-phase 9.1: Register Providers in main.dart

**Files:**
- Modify: `lib/main.dart:525-750`

**Agent:** `general-purpose`

#### Step 9.1.1: Add imports

At top of `lib/main.dart`, add:

```dart
import 'package:construction_inspector/features/projects/data/repositories/project_assignment_repository.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_assignment_provider.dart';
```

#### Step 9.1.2: Create repository in app initialization

In the `main()` function or the service initialization section, add:

```dart
  final projectAssignmentRepository = ProjectAssignmentRepository(dbService);
```

Also add the field to `ConstructionInspectorApp`:

```dart
  final ProjectAssignmentRepository projectAssignmentRepository;
```

And add to the constructor's `required` parameters.

#### Step 9.1.3: Register ProjectAssignmentProvider

In the `MultiProvider` providers list (after the `ProjectProvider` block), add:

```dart
        ChangeNotifierProvider(
          create: (_) => ProjectAssignmentProvider(projectAssignmentRepository),
        ),
```

#### Step 9.1.4: Wire onPullComplete for auto-enrollment

In the SyncProvider creation block (around line 724-745), extend the `onSyncCycleComplete` callback to also handle pending notifications:

```dart
            // FROM SPEC Section 5 (SC-9): Show pending notifications after sync
            syncProvider.onSyncCycleComplete = () async {
              try {
                final counts = await projectLifecycleService.getAllUnsyncedCounts();
                projectSyncHealthProvider.updateCounts(counts);
              } catch (e) {
                Logger.sync('Health provider update failed: $e');
              }
            };
```

Additionally, wire the `onPullComplete` callback on the SyncEngine (via the orchestrator) to detect new assignments and auto-enroll:

This is done by extending the SyncOrchestrator's engine setup. In the `syncOrchestrator` initialization in `main()`, after the engine is available, set:

```dart
  // FROM SPEC Section 2 (MF-5): Auto-enrollment on assignment pull.
  // When a new project_assignments row is pulled for the current user,
  // auto-insert into synced_projects and queue a notification.
  syncOrchestrator.engine?.onPullComplete = (tableName, pulledCount) async {
    if (tableName != 'project_assignments') return;
    // Re-check local assignments vs synced_projects to find new ones
    final userId = authProvider.userId;
    if (userId == null) return;
    final db = await dbService.database;
    final assignments = await db.query(
      'project_assignments',
      columns: ['project_id'],
      where: 'user_id = ?',
      whereArgs: [userId],
    );
    final synced = await db.query('synced_projects', columns: ['project_id']);
    final syncedIds = synced.map((r) => r['project_id'] as String).toSet();
    for (final row in assignments) {
      final projectId = row['project_id'] as String;
      if (!syncedIds.contains(projectId)) {
        await db.insert(
          'synced_projects',
          {
            'project_id': projectId,
            'synced_at': DateTime.now().toUtc().toIso8601String(),
          },
          conflictAlgorithm: ConflictAlgorithm.ignore,
        );
        Logger.sync('Auto-enrolled assigned project: $projectId');
        // FROM SPEC SC-9: Queue notification for display after sync
        syncProvider.addNotification('You\'ve been assigned to a new project');
      }
    }

    // REVIEW FIX (CRIT-4): Detect deleted assignments → set unassigned_at
    // FROM SPEC Section 2: "On pull, assignment deleted for current user
    // → set unassigned_at on synced_projects row (do NOT delete)"
    final assignedProjectIds = assignments.map((r) => r['project_id'] as String).toSet();
    final syncedProjectRows = await db.query('synced_projects');
    for (final row in syncedProjectRows) {
      final projectId = row['project_id'] as String;
      final currentUnassigned = row['unassigned_at'] as String?;
      // If project is enrolled but no longer assigned, mark as unassigned
      if (!assignedProjectIds.contains(projectId) && currentUnassigned == null) {
        // Check if the project was EVER assigned (had an assignment row before)
        // Only mark unassigned if there's evidence of prior assignment
        await db.update(
          'synced_projects',
          {'unassigned_at': DateTime.now().toUtc().toIso8601String()},
          where: 'project_id = ?',
          whereArgs: [projectId],
        );
        Logger.sync('Marked project as unassigned: $projectId');
      }
      // If re-assigned (assignment restored), clear unassigned_at
      if (assignedProjectIds.contains(projectId) && currentUnassigned != null) {
        await db.update(
          'synced_projects',
          {'unassigned_at': null},
          where: 'project_id = ?',
          whereArgs: [projectId],
        );
        Logger.sync('Cleared unassigned status for project: $projectId');
      }
    }
  };
```

NOTE: The exact wiring point depends on where the SyncEngine is accessible. If the engine is not directly accessible from main.dart, this callback should be set in the SyncOrchestrator constructor or initialization method. The implementing agent should check `sync_orchestrator.dart` for the correct hook point.

#### Step 9.1.5: Verify

Run: `pwsh -Command "flutter analyze lib/main.dart"`
Expected: No analysis errors.

---

## Phase 10: Cleanup + Route Audit

### Sub-phase 10.1: Delete Legacy project_selection_screen.dart

**Files:**
- Delete: `lib/features/sync/presentation/screens/project_selection_screen.dart`
- Modify: `lib/core/router/app_router.dart:31,615-623`
- Modify: `lib/features/sync/presentation/screens/sync_dashboard_screen.dart:267`

**Agent:** `general-purpose`

#### Step 10.1.1: Remove the route from app_router.dart

In `lib/core/router/app_router.dart`:

1. Remove the import on line 31:
```dart
// DELETE: import 'package:construction_inspector/features/sync/presentation/screens/project_selection_screen.dart';
```

2. Remove the GoRoute block (lines 615-623):
```dart
// DELETE: The entire GoRoute for '/sync/project-selection'
```

#### Step 10.1.2: Update sync_dashboard_screen.dart reference

In `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`, line 267, change the navigation to go to the project list screen instead:

```dart
          // FROM SPEC Section 11: Redirect to project list (Company tab) instead of deleted screen
          onTap: () => context.go('/projects'),
```

NOTE: The implementing agent should verify the exact route path for the projects tab. If the projects screen is at a different route, use the correct path.

#### Step 10.1.3: Delete the file

Delete `lib/features/sync/presentation/screens/project_selection_screen.dart`.

#### Step 10.1.4: Verify

Run: `pwsh -Command "flutter analyze lib/core/router/ lib/features/sync/presentation/screens/"`
Expected: No analysis errors, no dangling imports.

### Sub-phase 10.2: Delete Legacy Test File

**Files:**
- Delete: `test/features/sync/presentation/screens/project_selection_read_only_test.dart`

**Agent:** `general-purpose`

#### Step 10.2.1: Delete the test

Delete `test/features/sync/presentation/screens/project_selection_read_only_test.dart`.

#### Step 10.2.2: Verify remaining tests pass

Run: `pwsh -Command "flutter test test/features/projects/"`
Expected: All existing project tests PASS (or skip gracefully if they reference modified widgets).

---

## Phase 11: Tests

### Sub-phase 11.1: ProjectAssignment Model + Repository Unit Tests

**Files:**
- Create: `test/features/projects/data/models/project_assignment_test.dart`
- Create: `test/features/projects/data/repositories/project_assignment_repository_test.dart`

**Agent:** `qa-testing-agent`

#### Step 11.1.1: Write model tests

Create `test/features/projects/data/models/project_assignment_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/projects/data/models/project_assignment.dart';

void main() {
  group('ProjectAssignment', () {
    test('creates with auto-generated ID', () {
      final a = ProjectAssignment(
        projectId: 'proj-1',
        userId: 'user-1',
        assignedBy: 'admin-1',
        companyId: 'company-1',
      );
      expect(a.id, isNotEmpty);
      expect(a.projectId, 'proj-1');
      expect(a.userId, 'user-1');
    });

    test('toMap produces correct keys', () {
      final a = ProjectAssignment(
        id: 'test-id',
        projectId: 'proj-1',
        userId: 'user-1',
        assignedBy: 'admin-1',
        companyId: 'company-1',
      );
      final map = a.toMap();
      expect(map['id'], 'test-id');
      expect(map['project_id'], 'proj-1');
      expect(map['user_id'], 'user-1');
      expect(map['assigned_by'], 'admin-1');
      expect(map['company_id'], 'company-1');
      expect(map.containsKey('assigned_at'), true);
      expect(map.containsKey('updated_at'), true);
    });

    test('fromMap round-trips correctly', () {
      final original = ProjectAssignment(
        id: 'test-id',
        projectId: 'proj-1',
        userId: 'user-1',
        assignedBy: 'admin-1',
        companyId: 'company-1',
      );
      final restored = ProjectAssignment.fromMap(original.toMap());
      expect(restored.id, original.id);
      expect(restored.projectId, original.projectId);
      expect(restored.userId, original.userId);
      expect(restored.assignedBy, original.assignedBy);
      expect(restored.companyId, original.companyId);
    });
  });
}
```

#### Step 11.1.2: Verify

Run: `pwsh -Command "flutter test test/features/projects/data/models/project_assignment_test.dart"`
Expected: All tests PASS.

### Sub-phase 11.2: ProjectAssignmentProvider Unit Tests

**Files:**
- Create: `test/features/projects/presentation/providers/project_assignment_provider_test.dart`

**Agent:** `qa-testing-agent`

#### Step 11.2.1: Write provider tests

Create `test/features/projects/presentation/providers/project_assignment_provider_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_assignment_provider.dart';
import 'package:construction_inspector/features/projects/data/repositories/project_assignment_repository.dart';
import 'package:construction_inspector/core/database/database_service.dart';

void main() {
  late ProjectAssignmentProvider provider;
  late ProjectAssignmentRepository repository;
  late DatabaseService dbService;

  setUp(() async {
    dbService = DatabaseService.forTesting();
    await dbService.initInMemory();
    repository = ProjectAssignmentRepository(dbService);
    provider = ProjectAssignmentProvider(repository);
  });

  group('ProjectAssignmentProvider', () {
    test('starts with empty state', () {
      expect(provider.assignedCount, 0);
      expect(provider.filteredMembers, isEmpty);
      expect(provider.isLoading, false);
      expect(provider.hasChanges, false);
    });

    test('loadForProject populates members', () async {
      final members = [
        const AssignableMember(userId: 'u1', displayName: 'Alice', role: 'admin'),
        const AssignableMember(userId: 'u2', displayName: 'Bob', role: 'inspector'),
      ];
      await provider.loadForProject(
        projectId: 'proj-1',
        companyMembers: members,
      );
      expect(provider.filteredMembers.length, 2);
      expect(provider.assignedCount, 0);
    });

    test('toggleAssignment adds and removes', () async {
      final members = [
        const AssignableMember(userId: 'u1', displayName: 'Alice', role: 'admin'),
      ];
      await provider.loadForProject(
        projectId: 'proj-1',
        companyMembers: members,
      );
      expect(provider.isAssigned('u1'), false);
      provider.toggleAssignment('u1');
      expect(provider.isAssigned('u1'), true);
      expect(provider.assignedCount, 1);
      expect(provider.hasChanges, true);
      provider.toggleAssignment('u1');
      expect(provider.isAssigned('u1'), false);
      expect(provider.hasChanges, false);
    });

    test('setSearchQuery filters members', () async {
      final members = [
        const AssignableMember(userId: 'u1', displayName: 'Alice Admin', role: 'admin'),
        const AssignableMember(userId: 'u2', displayName: 'Bob Inspector', role: 'inspector'),
      ];
      await provider.loadForProject(
        projectId: 'proj-1',
        companyMembers: members,
      );
      provider.setSearchQuery('alice');
      expect(provider.filteredMembers.length, 1);
      expect(provider.filteredMembers.first.userId, 'u1');
    });

    test('clear resets all state', () async {
      final members = [
        const AssignableMember(userId: 'u1', displayName: 'Alice', role: 'admin'),
      ];
      await provider.loadForProject(
        projectId: 'proj-1',
        companyMembers: members,
      );
      provider.toggleAssignment('u1');
      provider.clear();
      expect(provider.assignedCount, 0);
      expect(provider.filteredMembers, isEmpty);
      expect(provider.hasChanges, false);
    });
  });
}
```

#### Step 11.2.2: Verify

Run: `pwsh -Command "flutter test test/features/projects/presentation/providers/project_assignment_provider_test.dart"`
Expected: All tests PASS.

### Sub-phase 11.3: ProjectProvider Tab State Unit Tests

**Files:**
- Create: `test/features/projects/presentation/providers/project_provider_tabs_test.dart`

**Agent:** `qa-testing-agent`

#### Step 11.3.1: Write provider tab tests

Create `test/features/projects/presentation/providers/project_provider_tabs_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_provider.dart';
import 'package:construction_inspector/features/projects/data/models/merged_project_entry.dart';
import 'package:construction_inspector/features/projects/data/models/project.dart';
import 'package:construction_inspector/features/projects/data/repositories/project_repository.dart';
import 'package:construction_inspector/core/database/database_service.dart';

void main() {
  group('ProjectProvider tab state', () {
    test('setTabIndex updates and notifies', () {
      final dbService = DatabaseService.forTesting();
      final repo = ProjectRepository(dbService);
      final provider = ProjectProvider(repo);
      int notifyCount = 0;
      provider.addListener(() => notifyCount++);

      provider.setTabIndex(1);
      expect(provider.currentTabIndex, 1);
      expect(notifyCount, 1);

      // Same index doesn't notify
      provider.setTabIndex(1);
      expect(notifyCount, 1);
    });

    test('setCompanyFilter updates and notifies', () {
      final dbService = DatabaseService.forTesting();
      final repo = ProjectRepository(dbService);
      final provider = ProjectProvider(repo);
      int notifyCount = 0;
      provider.addListener(() => notifyCount++);

      provider.setCompanyFilter(CompanyFilter.onDevice);
      expect(provider.companyFilter, CompanyFilter.onDevice);
      expect(notifyCount, 1);
    });
  });
}
```

#### Step 11.3.2: Verify

Run: `pwsh -Command "flutter test test/features/projects/presentation/providers/project_provider_tabs_test.dart"`
Expected: All tests PASS.

### Sub-phase 11.4: Widget Tests

**Files:**
- Create: `test/features/projects/presentation/widgets/project_empty_state_test.dart`
- Create: `test/features/projects/presentation/widgets/removal_dialog_test.dart`

**Agent:** `qa-testing-agent`

#### Step 11.4.1: Write empty state widget test

Create `test/features/projects/presentation/widgets/project_empty_state_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/projects/presentation/widgets/project_empty_state.dart';

void main() {
  group('ProjectEmptyState', () {
    testWidgets('myProjects variant shows browse button', (tester) async {
      bool browseTapped = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ProjectEmptyState(
              variant: EmptyStateVariant.myProjects,
              onBrowse: () => browseTapped = true,
            ),
          ),
        ),
      );

      expect(find.text('No projects on your device'), findsOneWidget);
      expect(find.text('Browse Available Projects'), findsOneWidget);
      await tester.tap(find.text('Browse Available Projects'));
      expect(browseTapped, true);
    });

    testWidgets('archived variant has no browse button', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ProjectEmptyState(
              variant: EmptyStateVariant.archived,
            ),
          ),
        ),
      );

      expect(find.text('No archived projects'), findsOneWidget);
      expect(find.text('Browse Available Projects'), findsNothing);
    });
  });
}
```

#### Step 11.4.2: Write removal dialog test

Create `test/features/projects/presentation/widgets/removal_dialog_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/projects/presentation/widgets/removal_dialog.dart';

void main() {
  group('RemovalDialog', () {
    testWidgets('shows warning when pending changes exist', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: RemovalDialog(
              projectName: 'Test Project',
              hasPendingChanges: true,
            ),
          ),
        ),
      );

      expect(find.text('Remove Project'), findsOneWidget);
      expect(find.textContaining('unsynced changes'), findsOneWidget);
      expect(find.text('Sync & Remove'), findsOneWidget);
      expect(find.text('Delete from Device'), findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);
    });

    testWidgets('hides sync option when no pending changes', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: RemovalDialog(
              projectName: 'Test Project',
              hasPendingChanges: false,
            ),
          ),
        ),
      );

      expect(find.text('Sync & Remove'), findsNothing);
      expect(find.text('Delete from Device'), findsOneWidget);
    });
  });
}
```

#### Step 11.4.3: Verify all tests

Run: `pwsh -Command "flutter test test/features/projects/"`
Expected: All tests PASS.

### Sub-phase 11.5: Update Existing Tests for Modified APIs

**Files:**
- Modify: `test/features/projects/presentation/screens/project_list_screen_test.dart`
- Modify: `test/features/settings/presentation/screens/settings_screen_test.dart`

**Agent:** `qa-testing-agent`

#### Step 11.5.1: Update project_list_screen_test.dart

The project list screen now requires `ProjectAssignmentProvider` in the widget tree. Update test setup to include the new provider. The implementing agent should:

1. Add the `ProjectAssignmentProvider` to the `MultiProvider` in test setup.
2. Update any assertions that reference the old single-list UI to match the new tab-based layout.

#### Step 11.5.2: Update settings_screen_test.dart if needed

Check if any settings tests reference the deleted `project-selection` route or `ProjectSelectionScreen`. If so, update or remove those assertions.

#### Step 11.5.3: Verify all tests

Run: `pwsh -Command "flutter test"`
Expected: All tests PASS (full suite).

---

## Phase Summary

| Phase | What | Files | Agent |
|-------|------|-------|-------|
| 1 | Supabase migration | 2 new | backend-supabase-agent |
| 2 | SQLite schema + migration | 2 modified | backend-data-layer-agent |
| 3 | Data layer (model + repo + extend merged entry) | 2 new, 1 modified | backend-data-layer-agent |
| 4 | Sync adapter + engine callback | 1 new, 2 modified | backend-supabase-agent |
| 5 | Provider layer (tab state + assignment provider + notifications) | 1 new, 2 modified | frontend-flutter-specialist-agent |
| 6 | UI widgets (6 new widgets) | 6 new, 1 modified | frontend-flutter-specialist-agent |
| 7 | Project list screen rewrite | 1 modified (major) | frontend-flutter-specialist-agent |
| 8 | Setup wizard assignments tab | 1 modified | frontend-flutter-specialist-agent |
| 9 | main.dart wiring + sync hooks | 1 modified | general-purpose |
| 10 | Cleanup (delete legacy, route audit) | 2 deleted, 2 modified | general-purpose |
| 11 | Tests | 6 new, 2 modified | qa-testing-agent |

**Total: 18 new, 12 modified, 2 deleted = 32 files**
