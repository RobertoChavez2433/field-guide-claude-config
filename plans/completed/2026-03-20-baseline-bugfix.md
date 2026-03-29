# Baseline Bug Fix Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Fix 13 bugs from E2E baseline test to achieve 80%+ pass rate (up from 39.6%)
**Spec:** `.claude/specs/2026-03-20-baseline-bugfix-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-20-baseline-bugfix/`

**Architecture:** Bug fixes across sync engine, data models, UI widgets, auth flow, and test infrastructure. No new abstractions — targeted fixes to existing code with safety nets for data migration.
**Tech Stack:** Flutter/Dart, SQLite (sqflite), Supabase (PostgreSQL), Provider state management
**Blast Radius:** 22 direct, 7 dependent, 4 tests, 3 new files

---

## Phase 0: Supabase Migrations (DEPLOY FIRST)

> Bug 7 trigger + Bug 9 RPC — must be deployed before Dart client changes.

### Sub-phase 0.1: Display Name Trigger Fix (Bug 7)
**Files:**
- Create: `supabase/migrations/20260320000000_fix_handle_new_user.sql`
**Agent**: `backend-supabase-agent`

**Step 1:** Create the migration file to fix the `handle_new_user` trigger so it populates `display_name` from registration metadata, with a 200-char server-side constraint.

```sql
-- File: supabase/migrations/20260320000000_fix_handle_new_user.sql
-- WHY: Bug 7 — registration sends full_name in user metadata, but the trigger
-- never wrote it into profiles.display_name. This left display_name NULL for
-- new users, causing blank names in the UI.
-- NOTE: COALESCE + SUBSTR enforces a 200-char ceiling server-side (adversarial review #4).

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  _display_name text;
BEGIN
  -- Extract display name from registration metadata, cap at 200 chars
  _display_name := COALESCE(
    SUBSTR(TRIM(NEW.raw_user_meta_data->>'full_name'), 1, 200),
    ''
  );

  -- NOTE: Table is user_profiles, PK column is id (not user_id).
  INSERT INTO public.user_profiles (id, display_name, created_at, updated_at)
  VALUES (
    NEW.id,
    _display_name,
    NOW(),
    NOW()
  )
  ON CONFLICT (id) DO UPDATE
    SET display_name = CASE
          WHEN user_profiles.display_name IS NULL OR user_profiles.display_name = ''
          THEN EXCLUDED.display_name
          ELSE user_profiles.display_name
        END,
        updated_at = NOW();

  RETURN NEW;
END;
$$;

-- WHY: Also add a CHECK constraint for the 200-char limit on the column itself
-- so any future direct inserts are also guarded.
ALTER TABLE public.user_profiles
  DROP CONSTRAINT IF EXISTS user_profiles_display_name_length;
ALTER TABLE public.user_profiles
  ADD CONSTRAINT user_profiles_display_name_length CHECK (char_length(display_name) <= 200);

-- FROM SPEC: Backfill existing users with NULL display_name from auth metadata.
-- NOTE: Only sets display_name where it's currently NULL — preserves existing names.
UPDATE public.user_profiles
SET display_name = SUBSTR(TRIM(au.raw_user_meta_data->>'full_name'), 1, 200),
    updated_at = NOW()
FROM auth.users au
WHERE user_profiles.id = au.id
  AND (user_profiles.display_name IS NULL OR user_profiles.display_name = '')
  AND au.raw_user_meta_data->>'full_name' IS NOT NULL
  AND TRIM(au.raw_user_meta_data->>'full_name') != '';
```

**Expected outcome:** Trigger now writes `display_name` from metadata on signup. Existing users with NULL names are backfilled from auth metadata. ON CONFLICT preserves non-empty existing names.

---

### Sub-phase 0.2: Integrity RPC Fix (Bug 9)
**Files:**
- Create: `supabase/migrations/20260320000001_fix_integrity_rpc.sql`
**Agent**: `backend-supabase-agent`

**Step 1:** Create the migration to fix the `get_table_integrity` RPC so it conditionally applies the `deleted_at IS NULL` filter based on a parameter.

```sql
-- File: supabase/migrations/20260320000001_fix_integrity_rpc.sql
-- WHY: Bug 9 — the integrity RPC unconditionally filters by deleted_at IS NULL,
-- but tables like project_assignments have no deleted_at column. This causes
-- SQL errors when the integrity checker queries those tables.
-- FROM SPEC: Deploy BEFORE Dart client changes so the RPC is available when
-- the updated integrity_checker.dart calls it.

CREATE OR REPLACE FUNCTION public.get_table_integrity(
  p_table_name text,
  p_company_id uuid,
  p_supports_soft_delete boolean DEFAULT true
)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  _count bigint;
  _max_ts text;
  _checksum bigint;
  _where_clause text;
BEGIN
  -- WHY (Security H1): Allowlist prevents arbitrary table enumeration via this
  -- SECURITY DEFINER function. Must include all 17 synced tables + project_assignments.
  IF p_table_name NOT IN (
    'projects', 'project_assignments', 'locations', 'contractors',
    'daily_entries', 'entry_weather', 'entry_activities', 'entry_safety',
    'entry_visitors', 'photos', 'equipment', 'personnel_types',
    'entry_personnel_counts', 'entry_equipment', 'bid_items',
    'entry_quantities', 'todo_items', 'form_responses'
  ) THEN
    RAISE EXCEPTION 'Invalid table name: %', p_table_name;
  END IF;

  -- Build WHERE clause conditionally based on whether table supports soft delete
  IF p_supports_soft_delete THEN
    _where_clause := ' AND deleted_at IS NULL';
  ELSE
    _where_clause := '';
  END IF;

  -- Count
  EXECUTE format('SELECT COUNT(*) FROM %I WHERE TRUE' || _where_clause, p_table_name)
    INTO _count;

  -- Max updated_at
  EXECUTE format('SELECT MAX(updated_at)::text FROM %I WHERE TRUE' || _where_clause, p_table_name)
    INTO _max_ts;

  -- ID checksum (hashtext-based)
  EXECUTE format(
    'SELECT COALESCE(SUM(hashtext(id::text)), 0) FROM %I WHERE TRUE' || _where_clause,
    p_table_name
  ) INTO _checksum;

  -- NOTE: Return structure matches what IntegrityChecker._checkTable() expects
  RETURN json_build_object(
    'row_count', _count,
    'max_updated_at', _max_ts,
    'id_checksum', _checksum
  );
END;
$$;
```

**Expected outcome:** The RPC accepts `p_supports_soft_delete` and omits the `deleted_at` filter when `false`.

---

### Sub-phase 0.3: Push Migrations
**Agent**: `backend-supabase-agent`

**Step 1:** Push both migrations to Supabase remote.

```bash
npx supabase db push
```

**Step 2:** Verify migrations applied.

```bash
npx supabase db pull --schema public
```

**Expected outcome:** Both migrations applied without errors. The trigger and RPC are updated on remote.

---

## Phase 1: Sync Engine Fixes (Bugs 1, 9, 10)

> Highest priority — Bug 1 unblocks 12+ test flows.

### Sub-phase 1.1: Engine-Internal Enrollment (Bug 1)
**Files:**
- Modify: `lib/features/sync/engine/sync_engine.dart` (lines ~1107-1182, ~1386-1441)
**Agent**: `backend-supabase-agent`

**Step 1:** In `_pull()`, after the `project_assignments` adapter runs, add engine-internal enrollment logic that writes to `synced_projects` immediately (filtered by current user).

In `sync_engine.dart`, locate the block inside the `for (final adapter in _registry.adapters)` loop where `adapter.tableName == 'project_assignments' && count > 0`. After the existing `await _loadSyncedProjectIds();` call, add the enrollment logic:

```dart
        // Inside _pull(), after the project_assignments block:
        if (adapter.tableName == 'project_assignments' && count > 0) {
          Logger.sync('Reloaded synced project IDs after pulling $count project_assignments');
          await _loadSyncedProjectIds();

          // WHY: Bug 1 — Engine-internal enrollment. The main.dart onPullComplete
          // callback also does this, but runs too late (after _pull returns).
          // By enrolling here inside the pull loop, subsequent adapters
          // (entries, todos, etc.) see the project IDs immediately.
          // FROM SPEC: Filter by user_id = userId (adversarial review #1).
          await _enrollProjectsFromAssignments();
        }
```

**Step 2:** Add the `_enrollProjectsFromAssignments()` method to `SyncEngine`:

```dart
  /// WHY: Bug 1 — Populates synced_projects from project_assignments for the
  /// current user. Called engine-internally during pull so downstream adapters
  /// see enrolled projects within the same pull cycle.
  Future<void> _enrollProjectsFromAssignments() async {
    if (userId.isEmpty) {
      Logger.sync('Cannot enroll projects: no current user ID');
      return;
    }

    // NOTE: Filter by current user to prevent cross-user enrollment
    final assignments = await db.query(
      'project_assignments',
      columns: ['project_id'],
      where: 'user_id = ?',
      whereArgs: [userId],
    );

    if (assignments.isEmpty) {
      Logger.sync('No project_assignments for user $userId');
      return;
    }

    int enrolled = 0;
    for (final row in assignments) {
      final projectId = row['project_id'] as String;
      // INSERT OR IGNORE — idempotent, won't duplicate
      await db.execute(
        'INSERT OR IGNORE INTO synced_projects (project_id) VALUES (?)',
        [projectId],
      );
      enrolled++;
    }

    if (enrolled > 0) {
      Logger.sync('Engine-enrolled $enrolled projects from assignments');
      await _loadSyncedProjectIds();
    }
  }
```

**Step 3:** Add the fresh-restore guard. After the `_enrollProjectsFromAssignments()` call in the `project_assignments` block, add:

```dart
          // WHY: Fresh-restore guard (adversarial review #1). If both synced_projects
          // AND local project_assignments are empty after the adapter runs, the cursor
          // may be stale from a previous install. Delete it so next pull fetches fresh.
          if (_syncedProjectIds.isEmpty) {
            final localAssignments = await db.query('project_assignments');
            if (localAssignments.isEmpty) {
              await db.execute(
                "DELETE FROM sync_metadata WHERE key = 'project_assignments_cursor'",
              );
              Logger.sync('Fresh-restore: cleared project_assignments cursor');
            }
          }
```

**Step 4:** Fix `_loadSyncedProjectIds()` — remove the implicit `count > 0` guard that causes the method to skip contractor loading when projects list is empty after orphan cleaning.

In `_loadSyncedProjectIds()`, the current code nests all logic inside `if (_syncedProjectIds.isNotEmpty)`. The contractor-loading section has a redundant `if (_syncedProjectIds.isEmpty)` check inside the `isNotEmpty` block (from orphan cleaning). This is correct as-is; the actual bug is that when `synced_projects` table is empty, we never even attempt to load. The fix is already handled by Step 1-3 (enrollment happens before load is needed).

No additional change needed to `_loadSyncedProjectIds()` — the enrollment in Step 1-3 ensures `synced_projects` is populated before downstream adapters check it.

**Verification:**
```
pwsh -Command "flutter test test/features/sync/ --name 'sync_engine'"
```
**Expected:** Tests pass. No "Pull skip (no loaded projects)" log lines during a normal pull cycle.

---

### Sub-phase 1.2: Integrity Checker (Bug 9)
**Files:**
- Modify: `lib/features/sync/engine/integrity_checker.dart` (lines ~151-236)
**Agent**: `backend-supabase-agent`

**Step 1:** Modify `_checkTable()` to accept the adapter (not just tableName) and use `adapter.supportsSoftDelete` to conditionally apply the `deleted_at` filter.

Find the method signature and update it:

```dart
  // OLD:
  Future<TableIntegrityResult> _checkTable(String tableName) async {

  // NEW:
  // WHY: Bug 9 — Tables like project_assignments have no deleted_at column.
  // Pass the adapter so we can check supportsSoftDelete.
  Future<TableIntegrityResult> _checkTable(TableAdapter adapter) async {
    final tableName = adapter.tableName;
```

**Step 2:** Inside `_checkTable()`, wrap the `deleted_at IS NULL` filter conditionally:

```dart
    // OLD:
    final localCountResult = await _db.rawQuery(
      'SELECT COUNT(*) as cnt FROM $tableName WHERE deleted_at IS NULL',
    );

    // NEW:
    // WHY: Bug 9 — Only filter by deleted_at if the table supports soft delete.
    final whereClause = adapter.supportsSoftDelete ? ' WHERE deleted_at IS NULL' : '';
    final localCountResult = await _db.rawQuery(
      'SELECT COUNT(*) as cnt FROM $tableName$whereClause',
    );
```

Apply the same pattern to all other queries in `_checkTable()` that use `deleted_at IS NULL`.

**Step 3:** Update all call sites of `_checkTable()` to pass the adapter instead of `adapter.tableName`:

```dart
    // OLD:
    final result = await _checkTable(adapter.tableName);

    // NEW:
    final result = await _checkTable(adapter);
```

**Step 4:** Update the Supabase RPC call within `_checkTable()` to pass the `supportsSoftDelete` parameter:

```dart
    // OLD:
    final remoteResult = await _supabase.rpc('get_table_integrity', params: {
      'p_table_name': tableName,
      'p_company_id': companyId,
    });

    // NEW:
    // WHY: Bug 9 — Pass soft-delete flag to RPC so it also conditionally filters.
    final remoteResult = await _supabase.rpc('get_table_integrity', params: {
      'p_table_name': tableName,
      'p_company_id': companyId,
      'p_supports_soft_delete': adapter.supportsSoftDelete,
    });
```

**Verification:**
```
pwsh -Command "flutter test test/features/sync/ --name 'integrity'"
```
**Expected:** No SQL errors when checking tables without `deleted_at`.

---

### Sub-phase 1.3: OrphanScanner (Bug 10)
**Files:**
- Modify: `lib/features/sync/engine/orphan_scanner.dart` (line ~27, ~84)
**Agent**: `backend-supabase-agent`

**Step 1:** Remove the `.eq('company_id', companyId)` filter from the photos query since the `photos` table has no `company_id` column. Replace with a path-based filter:

```dart
    // OLD (line ~27):
    final remotePhotos = await _client
        .from('photos')
        .select('remote_path')
        .eq('company_id', companyId)
        .not('remote_path', 'is', null)
        .neq('remote_path', '');

    // NEW:
    // WHY: Bug 10 — photos table has no company_id column. RLS already scopes
    // by company via project_id. Simply remove the invalid filter.
    // NOTE: companyId is still used for the storage bucket path prefix below.
    final remotePhotos = await _client
        .from('photos')
        .select('remote_path')
        .not('remote_path', 'is', null)
        .neq('remote_path', '');
```

**Step 2:** Add a path assertion before the auto-delete block to prevent accidental deletion of files outside the company's path:

```dart
    // Before the delete call (line ~84):
    if (deletable.isNotEmpty) {
      // WHY: Bug 10 adversarial review — assert all paths belong to this company
      // before deletion to prevent cross-company data loss.
      final companyPrefix = 'entries/$companyId/';
      final safePaths = <String>[];
      for (final f in deletable) {
        if (!f.path.startsWith(companyPrefix)) {
          Logger.error('OrphanScanner: refusing to delete path outside company scope: ${f.path}');
          continue;
        }
        safePaths.add(f.path);
      }
      if (safePaths.isNotEmpty) {
        await _client.storage.from(_bucket).remove(safePaths);
      }
    }
```

**Verification:**
```
pwsh -Command "flutter test test/features/sync/ --name 'orphan'"
```
**Expected:** No `photos.company_id` reference errors. Only company-scoped paths are deletable.

---

## Phase 2: Data Layer Fixes (Bug 2)

> Todo priority serialization — critical for push to succeed.

### Sub-phase 2.1: TodoItem.toMap() Fix
**Files:**
- Modify: `lib/features/todos/data/models/todo_item.dart` (line ~102)
**Agent**: `backend-data-layer-agent`

**Step 1:** Fix `toMap()` to serialize priority as integer index instead of string name:

```dart
    // OLD (line 102):
    'priority': priority.name,

    // NEW:
    // WHY: Bug 2 — Supabase column is smallint. Sending 'normal' (string) causes
    // PostgreSQL error 22P02 "invalid input syntax for type smallint".
    'priority': priority.index,
```

**Verification:**
```
pwsh -Command "flutter test test/features/todos/ --name 'toMap'"
```
**Expected:** `toMap()` returns `{'priority': 1}` for `TodoPriority.normal`, not `{'priority': 'normal'}`.

---

### Sub-phase 2.2: TodoPriorityConverter
**Files:**
- Modify: `lib/features/sync/adapters/type_converters.dart` (add new class)
- Modify: `lib/features/sync/adapters/todo_item_adapter.dart` (lines 17-19)
**Agent**: `backend-data-layer-agent`

**Step 1:** Add `TodoPriorityConverter` to `type_converters.dart`:

```dart
/// WHY: Bug 2 — During the transition period, Supabase may still have rows
/// with string priority values ('low', 'normal', 'high') from before the fix.
/// toRemote() converts strings to ints for Supabase. toLocal() is passthrough
/// since SQLite already stores ints after the migration.
class TodoPriorityConverter implements TypeConverter {
  const TodoPriorityConverter();

  static const _nameToIndex = {
    'low': 0,
    'normal': 1,
    'high': 2,
  };

  @override
  dynamic toRemote(dynamic value) {
    // WHY: Handle legacy string values during transition
    if (value is String) {
      return _nameToIndex[value] ?? 1; // default to normal
    }
    if (value is int) return value;
    return 1; // default to normal
  }

  @override
  dynamic toLocal(dynamic value) {
    // NOTE: Passthrough — SQLite stores as int, _parsePriority() handles both
    return value;
  }
}
```

**Step 2:** Register the converter in `todo_item_adapter.dart`:

```dart
  // OLD (lines 17-19):
  @override
  Map<String, TypeConverter> get converters => const {
      'is_completed': BoolIntConverter(),
    };

  // NEW:
  @override
  Map<String, TypeConverter> get converters => const {
      'is_completed': BoolIntConverter(),
      'priority': TodoPriorityConverter(),
    };
```

**Verification:**
```
pwsh -Command "flutter test test/features/todos/"
```
**Expected:** Converter correctly maps `'normal'` → `1`, `'high'` → `2`, passthrough ints.

---

### Sub-phase 2.3: DB Migration v39
**Files:**
- Modify: `lib/core/database/database_service.dart` (version bump + migration)
**Agent**: `backend-data-layer-agent`

**Step 1:** Bump the database version from 38 to 39.

**Step 2:** Add the v39 migration to fix string priority values in local SQLite and reset error-state change_log entries scoped to 22P02 errors:

```dart
    // In _onUpgrade, add after the v38 block:
    if (oldVersion < 39) {
      // WHY: Bug 2 — Clean up any todo rows that stored priority as string name
      // instead of integer index. Reset to 1 (normal) as safe default.
      await db.execute('''
        UPDATE todo_items SET priority = 1
        WHERE typeof(priority) = 'text'
      ''');
      Logger.db('v39 migration: converted string priority values to int');

      // FROM SPEC (MUST-FIX #2): Reset change_log entries for todo_items that
      // failed with 22P02 (invalid input syntax for integer). Scoped to this
      // specific error to avoid masking legitimate RLS denials or constraint violations.
      final resetCount = await db.rawUpdate('''
        UPDATE change_log
        SET processed = 0, retry_count = 0, error_message = NULL
        WHERE table_name = 'todo_items'
          AND processed = 0
          AND error_message LIKE '%22P02%'
      ''');
      if (resetCount > 0) {
        Logger.db('v39 migration: reset $resetCount todo change_log entries with 22P02 errors');
      }
    }
```

**Verification:**
```
pwsh -Command "flutter test test/core/database/"
```
**Expected:** Migration runs cleanly. String priority values converted to integer 1. 22P02 error entries reset for retry.

---

## Phase 3: UI Fixes (Bugs 3, 4, 6, 8, 11)

> Home screen, contractor dialog, project setup, testing keys.

### Sub-phase 3.1: ContractorController Init (Bug 3)
**Files:**
- Modify: `lib/features/entries/presentation/screens/home_screen.dart` (lines ~73-121, ~172-176)
**Agent**: `frontend-flutter-specialist-agent`

**Step 1:** Add a `_controllersInitialized` flag to the state class:

```dart
  // Add to state class fields:
  bool _controllersInitialized = false;
```

**Step 2:** Move `ContractorEditingController` initialization from `addPostFrameCallback` in `initState()` to `didChangeDependencies()`:

```dart
  // OLD initState (lines 95-101):
  WidgetsBinding.instance.addPostFrameCallback((_) {
    final dbService = context.read<DatabaseService>();
    _contractorController = ContractorEditingController(
      countsDatasource: EntryPersonnelCountsLocalDatasource(dbService),
      equipmentDatasource: EntryEquipmentLocalDatasource(dbService),
      contractorsDatasource: EntryContractorsLocalDatasource(dbService),
    );
    _loadProjectData();
  });

  // NEW initState — remove the addPostFrameCallback block entirely, replace with:
  WidgetsBinding.instance.addPostFrameCallback((_) {
    _loadProjectData();
  });
```

**Step 3:** Update `didChangeDependencies()`:

```dart
  // OLD (lines 172-176):
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _entryProvider = context.read<DailyEntryProvider>();
  }

  // NEW:
  // WHY: Bug 3 — Moving controller init to didChangeDependencies avoids
  // LateInitializationError when the build method runs before the
  // addPostFrameCallback completes. didChangeDependencies is called before
  // build and has access to inherited widgets via context.
  // NOTE: This deviates from the "initState-only" rule in architecture.md.
  // Documented in Phase 7.
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _entryProvider = context.read<DailyEntryProvider>();
    if (!_controllersInitialized) {
      _controllersInitialized = true;
      final dbService = context.read<DatabaseService>();
      _contractorController = ContractorEditingController(
        countsDatasource: EntryPersonnelCountsLocalDatasource(dbService),
        equipmentDatasource: EntryEquipmentLocalDatasource(dbService),
        contractorsDatasource: EntryContractorsLocalDatasource(dbService),
      );
    }
  }
```

**Verification:**
```
pwsh -Command "flutter test test/features/dashboard/ --name 'home_screen'"
```
**Expected:** No `LateInitializationError` on `_contractorController`. Controllers initialized before first build.

---

### Sub-phase 3.2: Calendar Flexible Wrap (Bug 4)
**Files:**
- Modify: `lib/features/entries/presentation/screens/home_screen.dart` (line ~389)
**Agent**: `frontend-flutter-specialist-agent`

**Step 1:** Wrap the calendar `Consumer` in a `Flexible` widget:

```dart
  // OLD (line ~387-392):
  Consumer<DailyEntryProvider>(
    builder: (context, entryProvider, _) {
      return _buildCalendarSection(entryProvider);
    },
  ),

  // NEW:
  // WHY: Bug 4 — The calendar month view's intrinsic height can exceed the
  // remaining space in the Column, causing RenderFlex overflow. Flexible with
  // FlexFit.loose allows it to shrink when space is constrained.
  Flexible(
    fit: FlexFit.loose,
    child: Consumer<DailyEntryProvider>(
      builder: (context, entryProvider, _) {
        return _buildCalendarSection(entryProvider);
      },
    ),
  ),
```

**Verification:**
```
pwsh -Command "flutter test test/features/dashboard/ --name 'calendar'"
```
**Expected:** No RenderFlex overflow in calendar month view on small screens.

---

### Sub-phase 3.3: Contractor Dropdown (Bug 6)
**Files:**
- Modify: `lib/features/projects/presentation/widgets/add_contractor_dialog.dart` (line ~55)
**Agent**: `frontend-flutter-specialist-agent`

**Step 1:** Replace `initialValue:` with `value:` on the `DropdownButtonFormField`:

```dart
  // OLD (line ~55):
  initialValue: _selectedType,

  // NEW:
  // WHY: Bug 6 — DropdownButtonFormField uses `value:`, not `initialValue:`.
  // Using `initialValue:` alongside `onChanged` + `setState` causes a Flutter
  // assertion crash because both the form field and the widget try to manage state.
  // FROM SPEC: Remove initialValue entirely, don't just add value alongside it.
  value: _selectedType,
```

**Important:** Ensure `initialValue` is fully removed, not just supplemented with `value:`. Having both causes an assertion error.

**Verification:**
```
pwsh -Command "flutter test test/features/contractors/"
```
**Expected:** Contractor type dropdown correctly saves Prime vs Sub selection.

---

### Sub-phase 3.4: Ghost Project (Bug 8)
**Files:**
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart` (lines ~958-970)
**Agent**: `frontend-flutter-specialist-agent`

**Step 1:** Add `_discardDraft()` call before the early return on duplicate project number:

```dart
  // OLD (inside _saveProject(), after the duplicate-number SnackBar):
  _tabController.animateTo(0);
  }
  return;

  // NEW:
  _tabController.animateTo(0);
  }
  // WHY: Bug 8 — When a duplicate project number is detected, the draft was
  // already created in SQLite. Without discarding it, the ghost draft persists
  // and appears in the project list.
  await _discardDraft();
  return;
```

**Verification:**
```
pwsh -Command "flutter test test/features/projects/ --name 'duplicate'"
```
**Expected:** No ghost projects left behind after duplicate number rejection.

---

### Sub-phase 3.5: Entry Edit Keys (Bug 11)
**Files:**
- Modify: `lib/shared/testing_keys/entries_keys.dart` (line ~80)
- Modify: `lib/features/entries/presentation/screens/home_screen.dart` (line ~1311)
**Agent**: `frontend-flutter-specialist-agent`

**Step 1:** Convert the static key to a factory method that takes a section parameter. First, define the `EntrySection` enum and factory in `entries_keys.dart`:

```dart
  // OLD (line 80):
  static const entryEditButton = Key('entry_edit_button');

  // NEW:
  // WHY: Bug 11 — entryEditButton was a static const used in 4 sections
  // (weather, activities, safety, visitors), creating duplicate keys in the
  // same widget tree. Factory method generates unique keys per section.
  // NOTE: Using enum for type safety (adversarial review #11).
  static Key entryEditButton(EntrySection section) =>
      Key('entry_edit_button_${section.name}');
```

**Step 2:** Add the `EntrySection` enum to `entries_keys.dart`:

```dart
/// WHY: Bug 11 — Enum for entry preview sections to generate unique widget keys.
enum EntrySection {
  weather,
  activities,
  safety,
  visitors,
}
```

**Step 3:** Update `home_screen.dart` at line ~1311 — in `_buildEditablePreviewSection`, pass the section enum. The method needs an `EntrySection` parameter:

```dart
  // OLD call sites (4 places in home_screen.dart):
  _buildEditablePreviewSection(/* ... */)

  // NEW call sites — add section parameter to each:
  _buildEditablePreviewSection(section: EntrySection.weather, /* ... */)
  _buildEditablePreviewSection(section: EntrySection.activities, /* ... */)
  _buildEditablePreviewSection(section: EntrySection.safety, /* ... */)
  _buildEditablePreviewSection(section: EntrySection.visitors, /* ... */)
```

**Step 4:** Update `_buildEditablePreviewSection` method signature and key usage:

```dart
  // OLD:
  Widget _buildEditablePreviewSection(/* existing params */) {
    // ...
    Icon(
      Icons.edit_outlined,
      key: TestingKeys.entryEditButton,
      // ...

  // NEW:
  Widget _buildEditablePreviewSection({
    required EntrySection section,
    /* existing params */
  }) {
    // ...
    Icon(
      Icons.edit_outlined,
      key: TestingKeys.entryEditButton(section),
      // ...
```

**Verification:**
```
pwsh -Command "flutter test test/features/entries/ test/features/dashboard/"
```
**Expected:** No duplicate key warnings. Each section gets a unique key.

---

## Phase 4: Auth & Config Fixes (Bugs 7, 15)

> Registration, profile, config — auth-agent territory.

### Sub-phase 4.1: Name Required at Registration (Bug 7)
**Files:**
- Modify: `lib/features/auth/presentation/screens/register_screen.dart` (lines ~82-91)
**Agent**: `auth-agent`

**Step 1:** Add a validator to the name `TextFormField` in the registration form:

```dart
  // OLD (the name TextFormField around line 82-91 — no validator):
  TextFormField(
    controller: _nameController,
    decoration: const InputDecoration(labelText: 'Full Name'),
    textCapitalization: TextCapitalization.words,
  ),

  // NEW:
  // WHY: Bug 7 — Without a validator, users can register with a blank name,
  // leaving display_name empty even after the trigger fix.
  TextFormField(
    controller: _nameController,
    decoration: const InputDecoration(labelText: 'Full Name'),
    textCapitalization: TextCapitalization.words,
    validator: (value) {
      if (value == null || value.trim().isEmpty) {
        return 'Name is required';
      }
      if (value.trim().length > 200) {
        return 'Name must be 200 characters or less';
      }
      return null;
    },
  ),
```

**Verification:**
```
pwsh -Command "flutter test test/features/auth/ --name 'register'"
```
**Expected:** Registration form rejects blank names. 200-char client-side limit matches server-side.

---

### Sub-phase 4.2: Profile Completion Gate (Bug 7)
**Files:**
- Modify: `lib/features/auth/presentation/screens/profile_setup_screen.dart` (lines ~79-105, ~118)
- Modify: `lib/core/router/app_router.dart` (line ~125+)
**Agent**: `auth-agent`

**Step 1:** Remove or disable the "Skip for now" button on the profile setup screen so name is always populated:

```dart
  // OLD (line ~118):
  actions: [
    TextButton(
      onPressed: _isSaving ? null : _skip,
      child: const Text('Skip for now'),
    ),
  ],

  // NEW:
  // WHY: Bug 7 adversarial review — existing users may have NULL display_name.
  // Removing skip forces name entry on profile setup.
  // NOTE: Keep _skip() method but don't expose it in UI.
  actions: const [],
```

**Step 2:** Add a profile-completion redirect in `app_router.dart` so existing users with NULL/empty `display_name` are routed to profile setup:

```dart
  // In the router's redirect logic (around line 125+), add after auth check:
  // WHY: Bug 7 — Existing users who registered before the trigger fix may have
  // NULL display_name. Gate them through profile setup.
  if (isAuthenticated && authProvider.currentProfile != null) {
    final profile = authProvider.currentProfile!;
    if ((profile.displayName == null || profile.displayName!.trim().isEmpty) &&
        !state.matchedLocation.startsWith('/profile-setup')) {
      return '/profile-setup';
    }
  }
```

**Verification:**
```
pwsh -Command "flutter test test/features/auth/ test/core/router/"
```
**Expected:** Users with NULL display_name are redirected to profile setup. No skip button visible.

---

### Sub-phase 4.3: Stale Config Banner (Bug 15)
**Files:**
- Modify: `lib/features/auth/presentation/providers/app_config_provider.dart` (lines 62-66)
**Agent**: `auth-agent`

**Step 1:** Fix `isConfigStale` to return `false` when there's been no server contact yet:

```dart
  // OLD (lines 62-66):
  bool get isConfigStale {
    final lastContact = _latestServerContact;
    if (lastContact == null) return true;
    return DateTime.now().toUtc().difference(lastContact) > _staleThreshold;
  }

  // NEW:
  // WHY: Bug 15 — On first login, _latestServerContact is null because no sync
  // cycle has completed yet. Returning true shows the "config stale" banner
  // immediately, confusing new users. Return false when null (no data to be stale).
  bool get isConfigStale {
    final lastContact = _latestServerContact;
    if (lastContact == null) return false;
    return DateTime.now().toUtc().difference(lastContact) > _staleThreshold;
  }
```

**Step 2:** In `checkConfig()`, add a fallback timestamp on failure so the "no timestamp" state can't persist indefinitely:

```dart
  // OLD catch block (around line 179):
    } catch (e) {
      Logger.ui('[AppConfigProvider] Config fetch failed: $e');
      _error = e.toString();
      // Fail open - do not block app usage
    }

  // NEW:
  // WHY: Bug 15 (FROM SPEC) — If checkConfig() fails (network unavailable),
  // set timestamp to now as fallback. Otherwise the "no timestamp" state
  // persists indefinitely and the stale banner never shows even after
  // extended offline use.
    } catch (e) {
      Logger.ui('[AppConfigProvider] Config fetch failed: $e');
      _error = e.toString();
      // Fail open — set a fallback timestamp so staleness tracking starts
      if (_lastConfigCheckAt == null) {
        _lastConfigCheckAt = DateTime.now().toUtc();
        await _secureStorage.write(
          key: 'last_config_check_at',
          value: _lastConfigCheckAt!.toIso8601String(),
        );
      }
    }
```

**Step 3:** Trigger `checkConfig()` eagerly on login. In the auth flow (where `loadAndRestore` or `onAuthChanged` is called in `main.dart`), add:

```dart
  // After successful auth, eagerly fetch config so the timestamp is populated.
  // WHY: Bug 15 — Without this, _latestServerContact stays null until the
  // first sync cycle completes, which may not happen immediately.
  // NOTE: Best-effort, non-blocking. Errors are caught inside checkConfig().
  unawaited(appConfigProvider.checkConfig());
```

**Verification:**
```
pwsh -Command "flutter test test/features/auth/"
```
**Expected:** No stale config banner on first login. Timestamp populated after login even if sync hasn't run.

---

## Phase 5: Sync UI Fix (Bug 16)

> Snackbar dedup — sync provider + router.

### Sub-phase 5.1: SyncProvider Dedup Flag (Bug 16)
**Files:**
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart` (lines ~30, ~83-147)
- Modify: `lib/core/router/app_router.dart` (lines ~656-669)
**Agent**: `backend-supabase-agent`

**Step 1:** Add a dedup flag to `SyncProvider`:

```dart
  // Add to SyncProvider class fields (around line 30):
  // WHY: Bug 16 — Without dedup, every sync cycle fires onSyncErrorToast when
  // there's a persistent error, queuing unlimited snackbars.
  bool _syncErrorSnackbarVisible = false;
```

**Step 2:** Guard the toast call with the flag in `_setupListeners()`:

```dart
  // OLD (around line 122):
  if (hasPersistentSyncFailure) {
    onSyncErrorToast?.call(_lastError!);
  }

  // NEW:
  if (hasPersistentSyncFailure && !_syncErrorSnackbarVisible) {
    _syncErrorSnackbarVisible = true;
    onSyncErrorToast?.call(_lastError!);
  }
```

**Step 2b:** ALSO guard the RLS denial toast paths (lines ~102 and ~107 in `_setupListeners`). Without this, RLS toasts bypass the dedup:

```dart
  // OLD (line ~102):
  onSyncErrorToast?.call(rlsMessage);

  // NEW (both occurrences at ~102 and ~107):
  if (!_syncErrorSnackbarVisible) {
    _syncErrorSnackbarVisible = true;
    onSyncErrorToast?.call(rlsMessage);
  }
```

**Step 3:** Add a method to reset the flag:

```dart
  /// Called when the sync error snackbar is dismissed (timer or user action).
  void clearSyncErrorSnackbarFlag() {
    _syncErrorSnackbarVisible = false;
  }
```

**Step 4:** In `app_router.dart`, update the SnackBar to reset the flag on dismissal:

```dart
  // OLD (lines 656-669):
  syncProvider.onSyncErrorToast ??= (message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Sync error: $message'),
        backgroundColor: Colors.red.shade700,
        duration: const Duration(seconds: 4),
        action: SnackBarAction(
          label: 'Details',
          textColor: Colors.white,
          onPressed: () => context.push('/sync/dashboard'),
        ),
      ),
    );
  };

  // NEW:
  // WHY: Bug 16 — Reset the dedup flag when the snackbar is dismissed so
  // future errors (after resolution + recurrence) can show again.
  syncProvider.onSyncErrorToast ??= (message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Sync error: $message'),
        backgroundColor: Colors.red.shade700,
        duration: const Duration(seconds: 4),
        action: SnackBarAction(
          label: 'Details',
          textColor: Colors.white,
          onPressed: () => context.push('/sync/dashboard'),
        ),
      ),
    ).closed.then((_) {
      syncProvider.clearSyncErrorSnackbarFlag();
    });
  };
```

**Verification:**
```
pwsh -Command "flutter test test/features/sync/ --name 'provider'"
```
**Expected:** Only one sync error snackbar shown per error occurrence. Flag resets on dismiss.

---

## Phase 6: Test Infrastructure (Bug 5)

> Photo direct-inject endpoint — depends on PhotoRepository being available.

### Sub-phase 6.1: Direct-Inject Endpoint (Bug 5)
**Files:**
- Modify: `lib/core/driver/driver_server.dart` (line ~77-126)
- Modify: `lib/core/driver/test_photo_service.dart`
- Modify: `lib/main_driver.dart` (line ~102)
**Agent**: `qa-testing-agent`

**Step 1:** Add a release/profile mode guard at the top of `driver_server.dart`:

```dart
  // At the top of the file, after imports:
  import 'package:flutter/foundation.dart';

  // WHY: Bug 5 adversarial review — the driver server must NEVER run in release
  // or profile builds. Guard at construction time.
  // (This may already exist — verify and add if missing)
```

**Step 2:** Add the `injectPhotoDirect()` method to `TestPhotoService` that creates a SQLite record directly via `PhotoRepository`:

```dart
  // In test_photo_service.dart, add:
  // WHY: Bug 5 — The existing injectPhoto() only queues a file for the next
  // capturePhoto()/pickFromGallery() call. For atomic test flows, we need to
  // create the photo record directly in SQLite without UI interaction.
  Future<Map<String, dynamic>> injectPhotoDirect({
    required File file,
    required String entryId,
    required String projectId,
    required PhotoRepository photoRepository,
  }) async {
    // NOTE: Guard against release/profile mode
    if (kReleaseMode || kProfileMode) {
      throw StateError('injectPhotoDirect is only available in debug mode');
    }

    // Strip EXIF data by re-encoding through the image package
    // WHY: Adversarial review — injected photos shouldn't carry test EXIF data
    final bytes = await file.readAsBytes();
    final image = img.decodeImage(bytes);
    final cleanBytes = image != null ? img.encodeJpg(image, quality: 85) : bytes;

    // Write clean bytes to a temp file
    final cleanFile = File('${file.parent.path}/clean_${file.uri.pathSegments.last}');
    await cleanFile.writeAsBytes(cleanBytes);

    // Create the photo record directly
    final photo = await photoRepository.createFromFile(
      file: cleanFile,
      entryId: entryId,
      projectId: projectId,
    );

    return {
      'id': photo.id,
      'entryId': photo.entryId,
      'localPath': photo.localPath,
    };
  }
```

**Step 3:** Add the route handler in `driver_server.dart`:

```dart
  // In the route registration section (around line 77-126), add:
  // Route: POST /inject-photo-direct
  if (path == '/inject-photo-direct' && method == 'POST') {
    await _handleInjectPhotoDirect(req, res);
    return;
  }
```

**Step 4:** Implement `_handleInjectPhotoDirect()` in `driver_server.dart`:

```dart
  Future<void> _handleInjectPhotoDirect(HttpRequest req, HttpResponse res) async {
    // WHY: Bug 5 — Atomic photo injection for E2E tests. Creates the SQLite
    // record directly instead of queuing for UI capture.
    if (kReleaseMode || kProfileMode) {
      await _sendJson(res, 403, {'error': 'Not available in release mode'});
      return;
    }

    final body = await _readJsonBody(req, maxBytes: _maxBase64BodyBytes);
    if (body == null) {
      await _sendJson(res, 400, {'error': 'Invalid JSON body'});
      return;
    }

    final base64Data = body['base64Data'] as String?;
    final filename = body['filename'] as String?;
    final entryId = body['entryId'] as String?;
    final projectId = body['projectId'] as String?;

    if (base64Data == null || filename == null || entryId == null || projectId == null) {
      await _sendJson(res, 400, {
        'error': 'Missing required fields: base64Data, filename, entryId, projectId',
      });
      return;
    }

    // Reuse existing validation from _handleInjectPhoto
    final allowedExtensions = ['.jpg', '.jpeg', '.png'];
    final ext = filename.contains('.') ? '.${filename.split('.').last.toLowerCase()}' : '';
    if (!allowedExtensions.contains(ext)) {
      await _sendJson(res, 400, {'error': 'Invalid file extension: $ext'});
      return;
    }
    if (filename.contains('/') || filename.contains('\\') || filename.contains('..')) {
      await _sendJson(res, 400, {'error': 'Invalid filename'});
      return;
    }

    final bytes = base64Decode(base64Data);

    final appTempDir = await getTemporaryDirectory();
    final driverDir = Directory('${appTempDir.path}/driver_photos');
    if (!driverDir.existsSync()) driverDir.createSync(recursive: true);
    final file = File('${driverDir.path}/$filename');
    await file.writeAsBytes(bytes);

    final result = await testPhotoService.injectPhotoDirect(
      file: file,
      entryId: entryId,
      projectId: projectId,
      photoRepository: _photoRepository,
    );

    await _sendJson(res, 200, {
      'injected': true,
      'direct': true,
      ...result,
    });
  }
```

**Step 5:** In `main_driver.dart`, ensure `PhotoRepository` is passed to `DriverServer`:

```dart
  // In _runApp() around line 102, when constructing DriverServer:
  // WHY: Bug 5 — DriverServer needs PhotoRepository for direct-inject endpoint.
  final driverServer = DriverServer(
    testPhotoService: testPhotoService,
    photoRepository: photoRepository,  // <-- add this parameter
    // ... existing params
  );
```

**Step 6:** Update `DriverServer` constructor to accept `PhotoRepository`:

```dart
  // In driver_server.dart constructor:
  final PhotoRepository _photoRepository;

  DriverServer({
    required this.testPhotoService,
    required PhotoRepository photoRepository,
    // ... existing params
  }) : _photoRepository = photoRepository;
```

**Verification:**
```
pwsh -Command "flutter test test/test_harness/"
```
**Expected:** Direct-inject endpoint creates SQLite record atomically. EXIF data stripped. Release/profile mode throws.

---

## Phase 7: Architecture Documentation

> Document the didChangeDependencies deviation for Bug 3.

### Sub-phase 7.1: Update architecture.md (Bug 3 deviation)
**Files:**
- Modify: `.claude/rules/architecture.md`
**Agent**: `general-purpose`

**Step 1:** Add a documented exception for `didChangeDependencies` usage:

```markdown
## Known Deviations

### didChangeDependencies for Provider-Dependent Controllers (Bug 3 Fix)
**File:** `home_screen.dart`
**Why:** `ContractorEditingController` requires `DatabaseService` from Provider, which is not available in `initState()`. Using `addPostFrameCallback` created a race condition causing `LateInitializationError` when build ran before the callback. Moving to `didChangeDependencies` with a `_controllersInitialized` guard is the established Flutter pattern for this case.
**Guard:** `_controllersInitialized` flag prevents re-initialization on dependency changes.
```

**Expected outcome:** Architecture deviation documented for future reference.

---

## Phase 8: Verification

### Sub-phase 8.1: Full Test Suite
**Agent**: `qa-testing-agent`

**Step 1:** Run the complete test suite:

```
pwsh -Command "flutter test"
```

**Expected:** All tests pass. Zero regressions.

**Step 2:** If any tests fail, triage:
- Test failure related to a bug fix → investigate and fix in the relevant phase
- Pre-existing test failure → document but do not block

---

### Sub-phase 8.2: Static Analysis
**Agent**: `qa-testing-agent`

**Step 1:** Run static analysis:

```
pwsh -Command "flutter analyze"
```

**Expected:** No new warnings or errors introduced by the bug fixes.

**Step 2:** If analysis issues found, fix unused imports, missing types, etc.

---

## Dispatch Plan

| Group | Phases | Parallelizable | Agent(s) |
|-------|--------|---------------|----------|
| G0 | Phase 0 (Supabase) | No — must complete first | `backend-supabase-agent` |
| G1 | Phase 1 (Sync) + Phase 2 (Data) | Yes — independent domains | `backend-supabase-agent`, `backend-data-layer-agent` |
| G2 | Phase 3 (UI) + Phase 4 (Auth) + Phase 5 (Sync UI) | Yes — independent domains | `frontend-flutter-specialist-agent`, `auth-agent`, `backend-supabase-agent` |
| G3 | Phase 6 (Test Infra) | No — depends on G1/G2 for stable base | `qa-testing-agent` |
| G4 | Phase 7 (Docs) + Phase 8 (Verification) | Docs parallel, verification last | `general-purpose`, `qa-testing-agent` |

**Total estimated time:** 45-60 minutes with parallel dispatch.
