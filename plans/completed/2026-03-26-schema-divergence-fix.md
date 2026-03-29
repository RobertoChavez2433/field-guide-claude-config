# Schema Divergence Fix Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Align SQLite and Supabase schemas for all 17 synced tables, unblocking sync.
**Spec:** Divergence audit at `.claude/test_results/2026-03-26_08-11/`
**Analysis:** `.claude/dependency_graphs/2026-03-26-schema-divergence-fix/`

**Architecture:** Single Supabase migration adds missing columns + updates RLS. SQLite migration v41 adds columns to project_assignments. Model and adapter updated for soft-delete.
**Tech Stack:** SQL (Supabase), Dart (Flutter), PostgREST
**Blast Radius:** 7 direct, 3 dependent, 1 test fixture, 0 cleanup

---

## Phase 1: Supabase Migration

**Agent:** `backend-supabase-agent`
**File:** `supabase/migrations/20260326100000_schema_divergence_fix.sql` (NEW)

### Step 1.1: Create the migration file

Create `supabase/migrations/20260326100000_schema_divergence_fix.sql` with the following content.

WHY: A single migration addresses all 4 Supabase divergences atomically. The timestamp `20260326100000` sorts after the existing `20260326000000_tighten_project_select_rls.sql`.

```sql
-- Migration: Fix schema divergences between SQLite and Supabase
-- FROM SPEC: Divergence audit 2026-03-26
--
-- Fixes:
--   1. project_assignments: add created_by_user_id, deleted_at, deleted_by (soft-delete support)
--   2. project_assignments: replace USING(false) UPDATE policy with soft-delete-only policy
--   3. entry_personnel_counts: add missing created_at column
--   4. daily_entries, photos: drop stale sync_status columns and indexes

-- ============================================================================
-- FIX 1: Add missing columns to project_assignments
-- WHY: The sync engine's _pushUpsert unconditionally stamps created_by_user_id on all
-- payloads (sync_engine.dart:881). Without this column, PostgREST returns PGRST204.
-- deleted_at/deleted_by enable soft-delete, matching all other 16 synced tables.
-- ============================================================================

ALTER TABLE project_assignments
  ADD COLUMN IF NOT EXISTS created_by_user_id UUID REFERENCES auth.users(id);

ALTER TABLE project_assignments
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE project_assignments
  ADD COLUMN IF NOT EXISTS deleted_by UUID REFERENCES auth.users(id);

-- Index for soft-delete filtering (matches pattern on other tables)
CREATE INDEX IF NOT EXISTS idx_project_assignments_deleted_at
  ON project_assignments(deleted_at);

-- ============================================================================
-- FIX 1b: Server-enforce created_by_user_id via trigger (like enforce_assignment_assigned_by)
-- WHY: created_by_user_id must be server-stamped to prevent spoofing. The existing
-- enforce_created_by() function (from 20260305000000) does exactly this — it sets
-- NEW.created_by_user_id = auth.uid(). We reuse it for project_assignments.
-- NOTE: enforce_created_by() already exists and is used on all 16 other synced tables.
-- ============================================================================

DROP TRIGGER IF EXISTS enforce_created_by_project_assignments ON project_assignments;
CREATE TRIGGER enforce_created_by_project_assignments
  BEFORE INSERT ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION enforce_created_by();

-- ============================================================================
-- FIX 1c: Apply stamp_deleted_by trigger to project_assignments
-- WHY: All other 16 synced tables have this trigger (applied in 20260313100000).
-- project_assignments was excluded because it didn't have deleted_at/deleted_by.
-- Now that it does, apply the same trigger for parity.
-- NOTE: stamp_deleted_by() already exists (20260313100000). It guards the
-- NULL->non-NULL transition on deleted_at and stamps deleted_by = auth.uid().
-- ============================================================================

DROP TRIGGER IF EXISTS trg_project_assignments_stamp_deleted_by ON project_assignments;
CREATE TRIGGER trg_project_assignments_stamp_deleted_by
  BEFORE UPDATE ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION stamp_deleted_by();

-- ============================================================================
-- FIX 1d: Apply lock_created_by trigger to project_assignments
-- WHY: All other synced tables have this trigger (20260305000000). It prevents
-- created_by_user_id from being erased on UPDATE. Uses COALESCE to preserve
-- the original value.
-- ============================================================================

DROP TRIGGER IF EXISTS lock_created_by_project_assignments ON project_assignments;
CREATE TRIGGER lock_created_by_project_assignments
  BEFORE UPDATE ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION lock_created_by();

-- ============================================================================
-- FIX 1e: Replace UPDATE RLS policy — allow soft-delete only
-- WHY: Current policy "no_update_assignments" uses USING(false), blocking ALL updates.
-- We need to allow UPDATE for soft-delete (setting deleted_at/deleted_by) by admin/engineer.
--
-- SECURITY: The policy is narrowly scoped:
--   - USING: Only admin/engineer, same company
--   - WITH CHECK: Only allows setting deleted_at (non-NULL) and deleted_by.
--     All other columns must remain unchanged (enforced by column equality checks).
--     This prevents privilege escalation (e.g., changing user_id or project_id).
-- ============================================================================

DROP POLICY IF EXISTS "no_update_assignments" ON project_assignments;

CREATE POLICY "soft_delete_assignments" ON project_assignments
  FOR UPDATE TO authenticated
  USING (
    -- WHO: Only admin/engineer can soft-delete assignments
    is_admin_or_engineer()
    -- SCOPE: Only own company's assignments
    AND company_id = get_my_company_id()
  )
  WITH CHECK (
    -- WHAT: Only soft-delete mutations are allowed.
    -- deleted_at must be set (this IS a soft-delete operation).
    deleted_at IS NOT NULL
    -- NOTE: Column immutability (project_id, user_id, assigned_by, company_id,
    --       assigned_at) is enforced by lock_assignment_columns() trigger (FIX 5).
    --       stamp_deleted_by() trigger enforces deleted_by = auth.uid(),
    --       update_updated_at_column() trigger enforces updated_at = now(),
    --       lock_created_by() trigger preserves created_by_user_id.
  );

-- ============================================================================
-- FIX 1f: Update audit trigger to include UPDATE (soft-delete) events
-- WHY: The existing log_assignment_change() only fires on INSERT OR DELETE.
-- With soft-delete, actual DELETEs won't happen — we need to log UPDATEs
-- where deleted_at transitions from NULL to non-NULL.
-- ============================================================================

CREATE OR REPLACE FUNCTION log_assignment_change()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    RAISE LOG 'project_assignment_created: project=% user=% by=%', NEW.project_id, NEW.user_id, NEW.assigned_by;
    RETURN NEW;
  ELSIF TG_OP = 'UPDATE' THEN
    -- Log soft-delete events (deleted_at NULL -> non-NULL)
    IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
      RAISE LOG 'project_assignment_soft_deleted: project=% user=% by=%', NEW.project_id, NEW.user_id, auth.uid();
    END IF;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    RAISE LOG 'project_assignment_deleted: project=% user=% by=%', OLD.project_id, OLD.user_id, auth.uid();
    RETURN OLD;
  ELSE
    RETURN NULL;
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Re-bind the audit trigger to include UPDATE
DROP TRIGGER IF EXISTS trg_project_assignments_audit ON project_assignments;
CREATE TRIGGER trg_project_assignments_audit
  AFTER INSERT OR UPDATE OR DELETE ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION log_assignment_change();

-- ============================================================================
-- FIX 2: Add missing created_at to entry_personnel_counts
-- WHY: SQLite has created_at (added in v24 migration). Supabase's original
-- CREATE TABLE in catchup_v23 only had: id, entry_id, contractor_id, type_id,
-- count, created_at. But the created_at was on the original table. The column
-- was added by 20260305000000 (soft-delete migration) as part of the bulk
-- ALTER TABLE. However, the audit found it missing — likely the column wasn't
-- in the original catchup_v23 CREATE TABLE and wasn't added later.
-- Adding it now with DEFAULT now() for any existing rows.
-- ============================================================================

ALTER TABLE entry_personnel_counts
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- ============================================================================
-- FIX 3: Drop stale sync_status columns from daily_entries and photos
-- WHY: SQLite removed sync_status in v31 (sync engine rewrite). These Supabase
-- columns were created in catchup_v23 and are now dead weight. The pull side
-- uses _stripUnknownColumns so they're harmless, but cleaning up for parity.
-- ============================================================================

ALTER TABLE daily_entries DROP COLUMN IF EXISTS sync_status;
ALTER TABLE photos DROP COLUMN IF EXISTS sync_status;

-- Drop the stale indexes too (they reference the dropped column)
DROP INDEX IF EXISTS idx_daily_entries_sync_status;
DROP INDEX IF EXISTS idx_photos_sync_status;

-- ============================================================================
-- FIX 4: Add project_assignments to purge_soft_deleted_records()
-- WHY (REVIEW LOW-1): Now that project_assignments has soft-delete, the purge
-- function must include it. Without this, soft-deleted assignments accumulate forever.
-- Placed AFTER locations and BEFORE projects in FK teardown order (assignments
-- reference projects, so delete assignments before purging projects).
-- ============================================================================

CREATE OR REPLACE FUNCTION purge_soft_deleted_records()
RETURNS void
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  -- Leaf junction tables (deepest children first)
  -- [FIX: H5] entry_personnel is ACTIVE (26 file references, has datasources).
  -- Must remain in purge function despite being described as "legacy" elsewhere.
  DELETE FROM entry_quantities WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM entry_equipment WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM entry_personnel WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM entry_personnel_counts WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM entry_contractors WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Photos (depend on entries and projects)
  DELETE FROM photos WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Toolbox tables (including inspector_forms)
  DELETE FROM form_responses WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM inspector_forms WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM todo_items WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM calculation_history WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Personnel types
  DELETE FROM personnel_types WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Bid items
  DELETE FROM bid_items WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Equipment (depends on contractors)
  DELETE FROM equipment WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Daily entries (depend on projects)
  DELETE FROM daily_entries WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Contractors (depend on projects)
  DELETE FROM contractors WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Locations (depend on projects)
  DELETE FROM locations WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Project assignments (depend on projects — added by divergence fix 2026-03-26)
  DELETE FROM project_assignments WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Projects (top-level parent — deleted last)
  DELETE FROM projects WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  RAISE LOG 'purge_soft_deleted_records: completed at %', NOW();
END;
$$;

-- ============================================================================
-- FIX 4b: Reload PostgREST schema cache
-- WHY: PostgREST caches the schema on startup. After adding columns, the cache
-- is stale and new columns will return PGRST204. NOTIFY forces a reload.
-- ============================================================================

-- ============================================================================
-- FIX 5: Column immutability trigger for project_assignments
-- WHY (REVIEW HIGH-2): The UPDATE RLS WITH CHECK only enforces deleted_at IS NOT NULL.
-- It does NOT prevent modifying project_id, user_id, assigned_by, or company_id
-- in the same UPDATE. RLS must be the enforcement boundary, not client behavior.
-- This trigger raises an exception if any immutable column changes.
-- ============================================================================

CREATE OR REPLACE FUNCTION lock_assignment_columns()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.project_id IS DISTINCT FROM OLD.project_id
     OR NEW.user_id IS DISTINCT FROM OLD.user_id
     OR NEW.assigned_by IS DISTINCT FROM OLD.assigned_by
     OR NEW.company_id IS DISTINCT FROM OLD.company_id
     OR NEW.assigned_at IS DISTINCT FROM OLD.assigned_at THEN
    RAISE EXCEPTION 'Cannot modify immutable columns on project_assignments';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

DROP TRIGGER IF EXISTS trg_project_assignments_lock_columns ON project_assignments;
CREATE TRIGGER trg_project_assignments_lock_columns
  BEFORE UPDATE ON project_assignments
  FOR EACH ROW EXECUTE FUNCTION lock_assignment_columns();

-- ============================================================================
-- FIX 6: Update projects SELECT RLS to exclude soft-deleted assignments
-- WHY (REVIEW CRITICAL-1): The tighten_project_select_rls migration
-- (20260326000000) uses EXISTS(SELECT 1 FROM project_assignments ...) without
-- filtering deleted_at. After soft-delete is enabled, a soft-deleted assignment
-- would still grant project SELECT access to an inspector — privilege escalation.
-- ============================================================================

DROP POLICY IF EXISTS "company_projects_select" ON projects;

CREATE POLICY "company_projects_select" ON projects
  FOR SELECT TO authenticated
  USING (
    company_id = get_my_company_id()
    AND (
      is_admin_or_engineer()
      OR EXISTS (
        SELECT 1 FROM project_assignments
        WHERE project_assignments.project_id = projects.id
          AND project_assignments.user_id = auth.uid()
          AND project_assignments.deleted_at IS NULL
      )
    )
  );

-- ============================================================================
-- FIX 7: Reload PostgREST schema cache
-- WHY: PostgREST caches the schema on startup. After adding columns, the cache
-- is stale and new columns will return PGRST204. NOTIFY forces a reload.
-- ============================================================================

NOTIFY pgrst, 'reload schema';
```

### Step 1.2: Verification queries (for the implementing agent to run mentally, not in migration)

After `npx supabase db push`, verify:

```sql
-- Check project_assignments has new columns
SELECT column_name FROM information_schema.columns
WHERE table_name = 'project_assignments'
ORDER BY ordinal_position;
-- Expected: id, project_id, user_id, assigned_by, company_id, assigned_at, updated_at, created_by_user_id, deleted_at, deleted_by

-- Check entry_personnel_counts has created_at
SELECT column_name FROM information_schema.columns
WHERE table_name = 'entry_personnel_counts' AND column_name = 'created_at';

-- Check sync_status is gone
SELECT column_name FROM information_schema.columns
WHERE table_name = 'daily_entries' AND column_name = 'sync_status';
-- Expected: 0 rows

-- Check UPDATE policy
SELECT policyname FROM pg_policies
WHERE tablename = 'project_assignments' AND cmd = 'UPDATE';
-- Expected: soft_delete_assignments
```

---

## Phase 2: SQLite + Model Layer

**Agent:** `backend-data-layer-agent`

### Step 2.1: Update createProjectAssignmentsTable in sync_engine_tables.dart

**File:** `lib/core/database/schema/sync_engine_tables.dart` (lines 100-112)

WHY: Add `created_by_user_id`, `deleted_at`, `deleted_by` to match Supabase and all other synced tables.

Replace the `createProjectAssignmentsTable` constant (lines 100-112):

```dart
  // FROM SPEC Section 2: project_assignments local mirror
  // WHY: Tracks which users are assigned to which projects.
  // Sync adapter pulls from Supabase; local copy enables offline tab filtering.
  // NOTE: created_by_user_id/deleted_at/deleted_by added for schema parity with
  // all other 16 synced tables (divergence fix 2026-03-26).
  static const String createProjectAssignmentsTable = '''
    CREATE TABLE IF NOT EXISTS project_assignments (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      user_id TEXT NOT NULL,
      assigned_by TEXT NOT NULL,
      company_id TEXT NOT NULL,
      created_by_user_id TEXT,
      assigned_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      deleted_at TEXT,
      deleted_by TEXT,
      UNIQUE(project_id, user_id),
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
  ''';
```

### Step 2.2: Bump database version 40 → 41 and add migration

**File:** `lib/core/database/database_service.dart`

#### Step 2.2.1: Update version constant

At line 53, change:
```dart
      version: 40,
```
to:
```dart
      version: 41,
```

Also at line 79 (in-memory database), change:
```dart
      version: 40,
```
to:
```dart
      version: 41,
```

#### Step 2.2.2: Add migration block

At line 1722 (after the `if (oldVersion < 40)` block's closing brace, just before the closing `}` of `_onUpgrade`), add:

```dart
    // Migration v41: Add created_by_user_id, deleted_at, deleted_by to project_assignments.
    // WHY: Schema divergence fix — all other 16 synced tables have these columns.
    // The sync engine's _pushUpsert stamps created_by_user_id on all payloads (line 881),
    // and _pushDelete sends deleted_at/deleted_by for soft-delete tables.
    // FROM SPEC: Divergence audit 2026-03-26
    if (oldVersion < 41) {
      await _addColumnIfNotExists(db, 'project_assignments', 'created_by_user_id', 'TEXT');
      await _addColumnIfNotExists(db, 'project_assignments', 'deleted_at', 'TEXT');
      await _addColumnIfNotExists(db, 'project_assignments', 'deleted_by', 'TEXT');
      Logger.db('v41 migration: added created_by_user_id, deleted_at, deleted_by to project_assignments');
    }
```

### Step 2.3: Update schema_verifier.dart

**File:** `lib/core/database/schema_verifier.dart`

#### Step 2.3.1: Add project_assignments entry to expectedSchema

WHY: The schema verifier is the self-healing safety net. Without this entry, it can't detect or repair missing columns on project_assignments.

At line 139 (after the `synced_projects` entry), add a new entry for `project_assignments`. The final block around lines 137-148 should look like:

```dart
    'synced_projects': [
      'project_id', 'synced_at', 'unassigned_at',
    ],
```

NOTE: This replaces the existing `synced_projects` entry at line 138-140 which is missing `unassigned_at`. The column was added in the `createSyncedProjectsTable` DDL (sync_engine_tables.dart:67) but never added to the verifier.

Then add a new `project_assignments` entry right after `synced_projects`:

```dart
    'project_assignments': [
      'id', 'project_id', 'user_id', 'assigned_by', 'company_id',
      'created_by_user_id', 'assigned_at', 'updated_at',
      'deleted_at', 'deleted_by',
    ],
```

#### Step 2.3.2: Add project_id to change_log entry

WHY: The `change_log` table has a `project_id` column (added in the CREATE TABLE at sync_engine_tables.dart:31) but the verifier's `expectedSchema` at line 127-130 is missing it.

Replace the `change_log` entry (lines 127-130):

```dart
    'change_log': [
      'id', 'table_name', 'record_id', 'operation', 'changed_at',
      'processed', 'error_message', 'retry_count', 'metadata', 'project_id',
    ],
```

### Step 2.4: Update ProjectAssignment model

**File:** `lib/features/projects/data/models/project_assignment.dart`

WHY: Add 3 new optional fields for soft-delete support and user attribution, matching the new SQLite/Supabase columns.

Replace the entire file content:

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
  final String? createdByUserId;
  final DateTime assignedAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final String? deletedBy;

  ProjectAssignment({
    String? id,
    required this.projectId,
    required this.userId,
    required this.assignedBy,
    required this.companyId,
    this.createdByUserId,
    DateTime? assignedAt,
    DateTime? updatedAt,
    this.deletedAt,
    this.deletedBy,
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
      'created_by_user_id': createdByUserId,
      'assigned_at': assignedAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      'deleted_at': deletedAt?.toIso8601String(),
      'deleted_by': deletedBy,
    };
  }

  factory ProjectAssignment.fromMap(Map<String, dynamic> map) {
    return ProjectAssignment(
      id: map['id'] as String? ?? (throw ArgumentError('ProjectAssignment.fromMap: missing required field id')),
      projectId: map['project_id'] as String? ?? (throw ArgumentError('ProjectAssignment.fromMap: missing required field project_id')),
      userId: map['user_id'] as String? ?? (throw ArgumentError('ProjectAssignment.fromMap: missing required field user_id')),
      assignedBy: map['assigned_by'] as String? ?? '',
      companyId: map['company_id'] as String? ?? '',
      createdByUserId: map['created_by_user_id'] as String?,
      assignedAt: map['assigned_at'] != null
          ? DateTime.parse(map['assigned_at'] as String)
          : DateTime.now(),
      updatedAt: map['updated_at'] != null
          ? DateTime.parse(map['updated_at'] as String)
          : DateTime.now(),
      deletedAt: map['deleted_at'] != null
          ? DateTime.parse(map['deleted_at'] as String)
          : null,
      deletedBy: map['deleted_by'] as String?,
    );
  }

  ProjectAssignment copyWith({
    String? id,
    String? projectId,
    String? userId,
    String? assignedBy,
    String? companyId,
    String? createdByUserId,
    DateTime? assignedAt,
    DateTime? updatedAt,
    DateTime? deletedAt,
    String? deletedBy,
  }) {
    return ProjectAssignment(
      id: id ?? this.id,
      projectId: projectId ?? this.projectId,
      userId: userId ?? this.userId,
      assignedBy: assignedBy ?? this.assignedBy,
      companyId: companyId ?? this.companyId,
      createdByUserId: createdByUserId ?? this.createdByUserId,
      assignedAt: assignedAt ?? this.assignedAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      deletedBy: deletedBy ?? this.deletedBy,
    );
  }
}
```

### Step 2.5: Update ProjectAssignmentAdapter

**File:** `lib/features/sync/adapters/project_assignment_adapter.dart`

WHY: Flip `supportsSoftDelete` to `true` so the sync engine routes deletes through `_pushDelete` (UPDATE with deleted_at/deleted_by) instead of hard DELETE.

Replace the entire file content:

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

/// Sync adapter for the project_assignments table.
///
/// FROM SPEC Section 2 (Sync Considerations):
/// - ScopeType.direct — uses company_id filter (like projects)
/// - SELECT RLS scopes data by role: inspectors get own rows, admins/engineers get all (SC-7)
/// - Soft-delete support: matches all other 16 synced tables (divergence fix 2026-03-26)
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

  // WHY: Changed from false to true (divergence fix 2026-03-26).
  // project_assignments now has deleted_at/deleted_by columns on both SQLite and
  // Supabase. The sync engine routes deletes through _pushDelete (UPDATE with
  // deleted_at/deleted_by) instead of hard DELETE, matching all other 16 tables.
  @override
  bool get supportsSoftDelete => true;
}
```

---

## Phase 3: Dependent Updates

**Agent:** `backend-supabase-agent`

### Step 3.1: Update supabase-verifier.js verifyCascadeDelete

**File:** `tools/debug-server/supabase-verifier.js` (lines 451-463)

WHY: `verifyCascadeDelete` currently checks `project_assignments` as hard-deleted (expects 0 rows). With soft-delete, it should check for soft-deleted records (deleted_at IS NOT NULL) like all other child tables.

Replace the `project_assignments` check block (lines 451-463) with:

```javascript
    // Check project_assignments (soft-deleted, matching all other tables)
    // WHY: Changed from hard-delete to soft-delete (divergence fix 2026-03-26)
    try {
      const assignments = await this.queryRecords('project_assignments', { project_id: `eq.${projectId}` });
      const activeAssignments = assignments.filter(r => !r.deleted_at);
      if (activeAssignments.length > 0) {
        details.push(`FAIL: project_assignments has ${activeAssignments.length} active records (expected 0)`);
        allPassed = false;
      } else {
        details.push(`OK: project_assignments — ${assignments.length} records, all soft-deleted`);
      }
    } catch (e) {
      details.push(`ERROR: project_assignments — ${e.message}`);
      allPassed = false;
    }
```

### Step 3.2: Update project_lifecycle_integration_test.dart schema fixture

**File:** `test/features/projects/integration/project_lifecycle_integration_test.dart`

#### Step 3.2.1: Add project_assignments table to _createFullSchema

WHY: The test's `_createFullSchema` (line 339) creates a minimal schema for lifecycle tests. It currently does NOT create a `project_assignments` table. With soft-delete, `removeFromDevice` in `ProjectLifecycleService` will need to soft-delete (or at minimum query) project_assignments. Add it to the fixture.

At line 403 (after the `form_responses` CREATE TABLE, before the closing `}` of `_createFullSchema`), add:

```dart
  await db.execute('CREATE TABLE project_assignments (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT, assigned_by TEXT, company_id TEXT, created_by_user_id TEXT, assigned_at TEXT, updated_at TEXT, deleted_at TEXT, deleted_by TEXT)');
```

#### Step 3.2.2: Add synced_projects.unassigned_at column

WHY: The test fixture at line 355-358 creates `synced_projects` without `unassigned_at`. The schema verifier expects this column (after our Step 2.3.1 fix). While the test doesn't use SchemaVerifier directly, maintaining consistency prevents confusion.

Replace line 355-358:

```dart
  await db.execute('''
    CREATE TABLE synced_projects (
      project_id TEXT PRIMARY KEY,
      synced_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      unassigned_at TEXT
    )
  ''');
```

### Step 3.3: Update ProjectAssignmentRepository for soft-delete awareness

**File:** `lib/features/projects/data/repositories/project_assignment_repository.dart`

WHY: With soft-delete, queries should exclude soft-deleted records by default. The `getByProject`, `getByUser`, and `getAssignedProjectIds` methods need `WHERE deleted_at IS NULL` filters. Without this, soft-deleted assignments would still appear in "My Projects" and other UI surfaces.

#### Step 3.3.1: Update getByProject (line 18-26)

Replace:

```dart
  Future<List<ProjectAssignment>> getByProject(String projectId) async {
    final db = await _db;
    final rows = await db.query(
      'project_assignments',
      where: 'project_id = ?',
      whereArgs: [projectId],
    );
    return rows.map(ProjectAssignment.fromMap).toList();
  }
```

With:

```dart
  /// Get all active (non-soft-deleted) assignments for a project.
  Future<List<ProjectAssignment>> getByProject(String projectId) async {
    final db = await _db;
    final rows = await db.query(
      'project_assignments',
      where: 'project_id = ? AND deleted_at IS NULL',
      whereArgs: [projectId],
    );
    return rows.map(ProjectAssignment.fromMap).toList();
  }
```

#### Step 3.3.2: Update getByUser (line 29-37)

Replace:

```dart
  Future<List<ProjectAssignment>> getByUser(String userId) async {
    final db = await _db;
    final rows = await db.query(
      'project_assignments',
      where: 'user_id = ?',
      whereArgs: [userId],
    );
    return rows.map(ProjectAssignment.fromMap).toList();
  }
```

With:

```dart
  /// Get all active (non-soft-deleted) assignments for the current user.
  Future<List<ProjectAssignment>> getByUser(String userId) async {
    final db = await _db;
    final rows = await db.query(
      'project_assignments',
      where: 'user_id = ? AND deleted_at IS NULL',
      whereArgs: [userId],
    );
    return rows.map(ProjectAssignment.fromMap).toList();
  }
```

#### Step 3.3.3: Update getAssignedProjectIds (line 40-49)

Replace:

```dart
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
```

With:

```dart
  /// Get project IDs for active (non-soft-deleted) assignments.
  Future<Set<String>> getAssignedProjectIds(String userId) async {
    final db = await _db;
    final rows = await db.query(
      'project_assignments',
      columns: ['project_id'],
      where: 'user_id = ? AND deleted_at IS NULL',
      whereArgs: [userId],
    );
    return rows.map((r) => r['project_id'] as String).toSet();
  }
```

### Step 3.4: Add deleted_at IS NULL to replaceAllForProject

**File:** `lib/features/projects/data/repositories/project_assignment_repository.dart`

WHY (REVIEW MEDIUM-6): `replaceAllForProject` does `DELETE ... WHERE project_id = ?` without soft-delete awareness. This would hard-delete soft-deleted records that may be pending sync push. Scope the delete to active records only.

In the `replaceAllForProject` method, replace:
```dart
      await txn.delete(
        'project_assignments',
        where: 'project_id = ?',
        whereArgs: [projectId],
      );
```

With:
```dart
      // WHY: Only delete active assignments. Soft-deleted records may be pending sync push.
      await txn.delete(
        'project_assignments',
        where: 'project_id = ? AND deleted_at IS NULL',
        whereArgs: [projectId],
      );
```

### Step 3.5: Update deleteByProjectAndUser for soft-delete awareness

**File:** `lib/features/projects/data/repositories/project_assignment_repository.dart`

WHY (REVIEW MEDIUM-1): `deleteByProjectAndUser` does a hard DELETE without `AND deleted_at IS NULL`. If a record is already soft-deleted and pending sync push, the hard delete removes it before the sync engine can push the soft-delete to Supabase. Add the filter for consistency.

Replace the `deleteByProjectAndUser` method (lines 103-111):

```dart
  /// Delete an active assignment by project + user.
  /// WHY: Only deletes active (non-soft-deleted) records. Soft-deleted records
  /// may be pending sync push and should not be removed locally.
  Future<void> deleteByProjectAndUser(String projectId, String userId) async {
    final db = await _db;
    await db.delete(
      'project_assignments',
      where: 'project_id = ? AND user_id = ? AND deleted_at IS NULL',
      whereArgs: [projectId, userId],
    );
  }
```

Also replace the `deleteAllForProject` method (lines 113-122):

```dart
  /// Delete all active assignments for a project (standalone, non-transactional).
  /// Prefer [replaceAllForProject] when replacing assignments atomically.
  Future<void> deleteAllForProject(String projectId) async {
    final db = await _db;
    await db.delete(
      'project_assignments',
      where: 'project_id = ? AND deleted_at IS NULL',
      whereArgs: [projectId],
    );
  }
```

### Step 3.6: Fix conflict_log in test fixture

**File:** `test/features/projects/integration/project_lifecycle_integration_test.dart`

WHY (REVIEW MEDIUM-4): The `conflict_log` CREATE TABLE in the test fixture is missing `conflict_count` column, which is present in the actual schema (schema_verifier.dart line 134).

Replace the conflict_log block (lines 369-380):

```dart
  await db.execute('''
    CREATE TABLE conflict_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      table_name TEXT NOT NULL,
      record_id TEXT NOT NULL,
      winner TEXT NOT NULL,
      lost_data TEXT NOT NULL,
      detected_at TEXT NOT NULL,
      dismissed_at TEXT,
      expires_at TEXT NOT NULL,
      conflict_count INTEGER NOT NULL DEFAULT 0
    )
  ''');
```

### Step 3.7: Add project_assignments to _directChildTables in ProjectLifecycleService

**File:** `lib/features/projects/data/services/project_lifecycle_service.dart`

WHY (REVIEW HIGH-3): `_directChildTables` lists tables for cascade operations (removeFromDevice, conflict_log cleanup). project_assignments is a direct child of projects (FK: project_id) and must be included so that:
1. `removeFromDevice` deletes local assignment rows when un-enrolling a project
2. Conflict_log entries for assignments are cleaned up properly

Find the `_directChildTables` list and add `'project_assignments'` to it. It should be placed early in the list (before locations/contractors) since assignments are a direct project dependency.

NOTE: `removeFromDevice` is a local-only operation — hard-deleting local rows is correct here. The sync engine handles synced soft-deletes separately via `_pushDelete`.

---

## Phase 4: Verification

**Agent:** `general-purpose`

### Step 4.1: Push Supabase migration

```
npx supabase db push
```

WHY: Applies the new migration to remote Supabase. Watch for errors — if any ALTER TABLE fails, the migration is not applied.

### Step 4.2: Run Flutter tests

```
pwsh -Command "flutter test"
```

WHY: Verifies the model changes compile and existing tests pass. Key tests to watch:
- `test/features/sync/engine/sync_engine_delete_test.dart` — exercises `_pushDelete` path
- `test/features/projects/integration/project_lifecycle_integration_test.dart` — exercises schema fixture
- `test/core/database/change_log_trigger_project_id_test.dart` — exercises sync engine tables

### Step 4.3: Run Flutter analyze

```
pwsh -Command "flutter analyze"
```

WHY: Catches type errors from the model changes (e.g., callers passing wrong arg count to ProjectAssignment constructor).

---

## Summary of All Changes

### New files (1):
| File | Purpose |
|------|---------|
| `supabase/migrations/20260326100000_schema_divergence_fix.sql` | Supabase migration — all 4 fixes |

### Modified files (7):
| File | Change |
|------|--------|
| `lib/core/database/schema/sync_engine_tables.dart` | Add 3 columns to createProjectAssignmentsTable |
| `lib/core/database/database_service.dart` | Bump v40→v41, add migration block |
| `lib/core/database/schema_verifier.dart` | Add project_assignments entry, fix change_log + synced_projects |
| `lib/features/projects/data/models/project_assignment.dart` | Add createdByUserId, deletedAt, deletedBy |
| `lib/features/sync/adapters/project_assignment_adapter.dart` | supportsSoftDelete → true |
| `lib/features/projects/data/repositories/project_assignment_repository.dart` | Add `AND deleted_at IS NULL` to all queries + deletes |
| `lib/features/projects/data/services/project_lifecycle_service.dart` | Add project_assignments to _directChildTables |

### Dependent files (2):
| File | Change |
|------|--------|
| `tools/debug-server/supabase-verifier.js` | verifyCascadeDelete: hard-delete → soft-delete check |
| `test/features/projects/integration/project_lifecycle_integration_test.dart` | Add project_assignments table, synced_projects.unassigned_at, conflict_log.conflict_count |

### Security audit checklist:
- [x] UPDATE RLS policy scoped to admin/engineer only
- [x] UPDATE RLS policy scoped to same company (get_my_company_id())
- [x] WITH CHECK enforces deleted_at IS NOT NULL (soft-delete only)
- [x] stamp_deleted_by() trigger prevents deleted_by spoofing
- [x] lock_created_by() trigger prevents created_by_user_id erasure
- [x] enforce_created_by() trigger stamps created_by_user_id on INSERT
- [x] lock_assignment_columns() trigger prevents modifying immutable columns (REVIEW HIGH-2 FIX)
- [x] company_projects_select RLS updated to exclude soft-deleted assignments (REVIEW CRITICAL-1 FIX)
- [x] project_assignments added to _directChildTables for cascade cleanup (REVIEW HIGH-3 FIX)
- [x] Audit trigger updated to log soft-delete events
