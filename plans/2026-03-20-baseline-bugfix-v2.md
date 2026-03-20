# Baseline Bugfix V2 Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Fix all 16 bugs discovered during the 96-flow E2E test suite to reach a stable baseline.
**Spec:** Conversation-based, no spec file. Design decisions in this plan header.
**Analysis:** `.claude/dependency_graphs/2026-03-20-baseline-bugfix-v2/`

**Architecture:** Backend/data fixes first (RPC migration, auth provider, draft discard), then UI fixes (contractor dialog, project provider, photo dialog, project setup, forms), then mechanical testing keys last. Each phase is independently verifiable.
**Blast Radius:** ~18 direct files, 1 migration, ~6 testing key files, 2 test assets

**Adversarial Review Status:**
- Code review: REJECT -> all CRITICAL/HIGH findings addressed in this revision
- Security review: APPROVE WITH CONDITIONS -> M-1 (cross-user data) and M-2 (test assets) addressed

---

## Phase 1: Backend & Data Layer Fixes

### Sub-phase 1.1: BUG-17 — Stop clearing local data on sign-out

**Files:**
- Modify: `lib/features/auth/presentation/providers/auth_provider.dart:323-358,365-379,771-789`

**Agent:** auth-agent

#### Step 1.1.1: Remove clearLocalCompanyData from signOut()

In `signOut()` (line 338), remove the database clearing block:

```dart
// REMOVE these lines (335-338):
      final db = _databaseService;
      if (db != null) {
        await AuthService.clearLocalCompanyData(db);
      }
```

After the fix, `signOut()` try block should read:

```dart
    try {
      await _authService.signOut();
      BackgroundSyncHandler.dispose();
      // WHY: BUG-17 — Don't clear local data on logout. Data persists for
      // re-login. Only clear on account delete or company switch (future).
      _isLoading = false;
      _currentUser = null;
      _isPasswordRecovery = false;
      await _preferencesService?.clearPasswordRecoveryActive();
      await _clearSecureStorageOnSignOut();
      _userProfile = null;
      _company = null;
      attributionRepository.clearCache();
      notifyListeners();
      return true;
    }
```

#### Step 1.1.2: Remove clearLocalCompanyData from signOutLocally()

In `signOutLocally()` (lines 369-372), remove the database clearing block:

```dart
// REMOVE these lines (368-371):
    final db = _databaseService;
    if (db != null) {
      await AuthService.clearLocalCompanyData(db);
    }
```

After the fix, `signOutLocally()` should read:

```dart
  Future<void> signOutLocally() async {
    BackgroundSyncHandler.dispose();
    // WHY: BUG-17 — Don't clear local data on sign-out. Preserves offline data
    // for re-login. clearLocalCompanyData kept for future account-delete/company-switch.
    _currentUser = null;
    _isPasswordRecovery = false;
    await _preferencesService?.clearPasswordRecoveryActive();
    await _clearSecureStorageOnSignOut();
    _userProfile = null;
    _company = null;
    attributionRepository.clearCache();
    notifyListeners();
  }
```

#### Step 1.1.3: Remove clearLocalCompanyData from _mockSignOut()

In `_mockSignOut()` (lines 776-779), remove the database clearing block:

```dart
// REMOVE these lines (776-779):
    final db = _databaseService;
    if (db != null) {
      await AuthService.clearLocalCompanyData(db);
    }
```

After the fix, `_mockSignOut()` should read:

```dart
  Future<bool> _mockSignOut() async {
    await Future.delayed(const Duration(milliseconds: 100));
    BackgroundSyncHandler.dispose();
    // WHY: BUG-17 — Mirror real signOut behavior: don't clear local data.
    await _clearSecureStorageOnSignOut();
    _mockUserId = null;
    _mockUserEmail = null;
    _userProfile = null;
    _company = null;
    attributionRepository.clearCache();
    _isLoading = false;
    notifyListeners();
    return true;
  }
```

**NOTE:** Do NOT delete `AuthService.clearLocalCompanyData()` itself — it will be used below and for future account-delete features.

#### Step 1.1.4: Add company-switch guard in signIn()

**WHY (Security M-1):** If User A signs out and User B (different company) signs in on the same device, User B would see User A's cached data. On sign-in, compare the incoming user's company_id against local data. If different, clear local data.

In `signIn()` (around line 310, after `_currentUser = response.user` and before the profile load), add:

```dart
      // WHY: Security M-1 — Prevent cross-company data leakage on device handoff.
      // If the signing-in user belongs to a different company than the cached data,
      // clear all local data so they start fresh.
      if (_databaseService != null) {
        final db = await _databaseService!.database;
        final cachedCompanies = await db.query('companies', limit: 1);
        if (cachedCompanies.isNotEmpty) {
          final cachedCompanyId = cachedCompanies.first['id'] as String?;
          // Load the new user's profile to check company
          final newProfile = await _authService.loadUserProfile(_currentUser!.id);
          if (newProfile != null && newProfile.companyId != null &&
              cachedCompanyId != null && newProfile.companyId != cachedCompanyId) {
            Logger.auth('[AuthProvider] Company switch detected: clearing local data');
            await AuthService.clearLocalCompanyData(_databaseService!);
          }
        }
      }
```

**NOTE:** This guard runs only when there IS cached data AND it belongs to a different company. Same-user re-login preserves data (the whole point of BUG-17). Different-company login clears data (security requirement).

#### Step 1.1.5: Verify

Run: `pwsh -Command "flutter analyze lib/features/auth/"`

---

### Sub-phase 1.2: BUG-15 + BUG-7 — Fix integrity RPC and add entry_contractors

**Files:**
- Create: `supabase/migrations/20260320000003_fix_integrity_rpc_v2.sql`

**Agent:** backend-supabase-agent

#### Step 1.2.1: Create migration to fix RPC return type and allowlist

Create `supabase/migrations/20260320000003_fix_integrity_rpc_v2.sql`:

```sql
-- BUG-15: Revert RPC from RETURNS json to RETURNS TABLE so Dart receives List<Map>.
-- BUG-7: Add entry_contractors to the allowlist (17 tables total).
--
-- WHY: The previous migration (20260320000002) changed to RETURNS json, but
-- integrity_checker.dart expects `rpcResultList is List` which only works with
-- RETURNS TABLE. Supabase PostgREST wraps RETURNS TABLE rows in an array.
--
-- ADVERSARIAL REVIEW FIXES (C1, C2):
-- - C1: projects branch has no alias 't', so soft-delete filter is applied inline per branch
-- - C2: All hashtext calls use id::text cast (hashtext accepts text, not uuid)

-- Drop the existing function (both overloads if any)
DROP FUNCTION IF EXISTS public.get_table_integrity(text, boolean);
DROP FUNCTION IF EXISTS public.get_table_integrity(text);

CREATE OR REPLACE FUNCTION public.get_table_integrity(
  p_table_name text,
  p_supports_soft_delete boolean DEFAULT true
)
RETURNS TABLE(row_count bigint, max_updated_at text, id_checksum bigint)
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  v_company_id uuid;
  v_sql text;
BEGIN
  -- Derive company from the calling user's JWT (no client-supplied company_id)
  v_company_id := get_my_company_id();
  IF v_company_id IS NULL THEN
    RAISE EXCEPTION 'Could not determine company_id for current user';
  END IF;

  -- Allowlist: 17 tables (BUG-7: entry_contractors added)
  -- WHY: Prevents arbitrary table access via dynamic SQL. Each table has a
  -- known path to company_id for RLS-equivalent server-side scoping.
  IF p_table_name NOT IN (
    'projects',
    'project_assignments',
    'locations',
    'contractors',
    'equipment',
    'bid_items',
    'personnel_types',
    'daily_entries',
    'photos',
    'entry_equipment',
    'entry_quantities',
    'entry_contractors',
    'entry_personnel_counts',
    'inspector_forms',
    'form_responses',
    'todo_items',
    'calculation_history'
  ) THEN
    RAISE EXCEPTION 'Table % is not in the integrity check allowlist', p_table_name;
  END IF;

  -- WHY: Each table requires a different company scoping path depending on its
  -- position in the FK hierarchy. All paths anchor to projects.company_id.
  -- NOTE: projects branch uses NO alias (direct table), all others use alias 't'.
  -- Soft-delete filter is applied inline per branch to handle the alias difference.

  IF p_table_name = 'projects' THEN
    -- Direct company_id column on projects (NO alias)
    v_sql := format(
      'SELECT count(*)::bigint, coalesce(max(updated_at)::text, ''''), coalesce(sum(abs(hashtext(id::text)))::bigint, 0) FROM %I WHERE company_id = %L',
      p_table_name, v_company_id
    );
    -- WHY (C1 fix): projects has no alias, so soft-delete uses unqualified column name
    IF p_supports_soft_delete THEN
      v_sql := v_sql || ' AND deleted_at IS NULL';
    END IF;

  ELSIF p_table_name = 'project_assignments' THEN
    v_sql := format(
      'SELECT count(*)::bigint, coalesce(max(t.updated_at)::text, ''''), coalesce(sum(abs(hashtext(t.id::text)))::bigint, 0) FROM %I t WHERE t.company_id = %L',
      p_table_name, v_company_id
    );
    IF p_supports_soft_delete THEN
      v_sql := v_sql || ' AND t.deleted_at IS NULL';
    END IF;

  ELSIF p_table_name IN ('locations', 'contractors', 'bid_items', 'personnel_types', 'daily_entries', 'todo_items', 'calculation_history') THEN
    -- One hop: project_id -> projects.company_id
    v_sql := format(
      'SELECT count(*)::bigint, coalesce(max(t.updated_at)::text, ''''), coalesce(sum(abs(hashtext(t.id::text)))::bigint, 0) FROM %I t WHERE t.project_id IN (SELECT id FROM projects WHERE company_id = %L)',
      p_table_name, v_company_id
    );
    IF p_supports_soft_delete THEN
      v_sql := v_sql || ' AND t.deleted_at IS NULL';
    END IF;

  ELSIF p_table_name = 'equipment' THEN
    -- Two hops: contractor_id -> contractors.project_id -> projects.company_id
    v_sql := format(
      'SELECT count(*)::bigint, coalesce(max(t.updated_at)::text, ''''), coalesce(sum(abs(hashtext(t.id::text)))::bigint, 0) FROM %I t WHERE t.contractor_id IN (SELECT id FROM contractors WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L))',
      p_table_name, v_company_id
    );
    IF p_supports_soft_delete THEN
      v_sql := v_sql || ' AND t.deleted_at IS NULL';
    END IF;

  ELSIF p_table_name IN ('photos', 'entry_equipment', 'entry_quantities', 'entry_contractors', 'entry_personnel_counts') THEN
    -- Two hops: entry_id -> daily_entries.project_id -> projects.company_id
    v_sql := format(
      'SELECT count(*)::bigint, coalesce(max(t.updated_at)::text, ''''), coalesce(sum(abs(hashtext(t.id::text)))::bigint, 0) FROM %I t WHERE t.entry_id IN (SELECT id FROM daily_entries WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L))',
      p_table_name, v_company_id
    );
    IF p_supports_soft_delete THEN
      v_sql := v_sql || ' AND t.deleted_at IS NULL';
    END IF;

  ELSIF p_table_name IN ('inspector_forms', 'form_responses') THEN
    -- inspector_forms has project_id; form_responses has project_id
    v_sql := format(
      'SELECT count(*)::bigint, coalesce(max(t.updated_at)::text, ''''), coalesce(sum(abs(hashtext(t.id::text)))::bigint, 0) FROM %I t WHERE t.project_id IN (SELECT id FROM projects WHERE company_id = %L)',
      p_table_name, v_company_id
    );
    IF p_supports_soft_delete THEN
      v_sql := v_sql || ' AND t.deleted_at IS NULL';
    END IF;

  ELSE
    RAISE EXCEPTION 'No scoping path defined for table %', p_table_name;
  END IF;

  -- WHY: RETURN QUERY EXECUTE produces a row set that PostgREST wraps as JSON array,
  -- matching the Dart expectation of `rpcResultList is List`.
  RETURN QUERY EXECUTE v_sql;
END;
$$;

-- Security: restrict access to authenticated users only
REVOKE ALL ON FUNCTION public.get_table_integrity(text, boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_table_integrity(text, boolean) TO authenticated;
```

#### Step 1.2.2: Verify migration syntax

Run: `pwsh -Command "Get-Content supabase/migrations/20260320000003_fix_integrity_rpc_v2.sql | Select-String 'entry_contractors'"` to confirm the table is in the allowlist.

#### Step 1.2.3: Push migration

Run: `npx supabase db push`

---

### Sub-phase 1.3: BUG-2 + BUG-8 — Fix draft discard crash

**Files:**
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart:359`

**Agent:** frontend-flutter-specialist-agent

#### Step 1.3.1: Remove 'equipment' from direct-delete list

In `_discardDraft()` at line 359, change:

```dart
// BEFORE:
for (final table in ['equipment', 'bid_items', 'contractors', 'locations', 'personnel_types']) {

// AFTER:
// WHY: BUG-2/8 — equipment has contractor_id (not project_id). FK CASCADE
// on contractors(id) auto-deletes equipment when contractors are deleted.
for (final table in ['bid_items', 'contractors', 'locations', 'personnel_types']) {
```

#### Step 1.3.2: Verify

Run: `pwsh -Command "flutter analyze lib/features/projects/presentation/screens/project_setup_screen.dart"`

---

## Phase 2: UI Logic Fixes

### Sub-phase 2.1: BUG-1 — Fix contractor type not saving (Navigator.pop before await)

**Files:**
- Modify: `lib/features/projects/presentation/widgets/add_contractor_dialog.dart:98-120`

**Agent:** frontend-flutter-specialist-agent

#### Step 2.1.1: Move Navigator.pop after await

Replace `_handleAdd` method (lines 98-120):

```dart
  Future<void> _handleAdd(BuildContext context) async {
    if (_nameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a contractor name')),
      );
      return;
    }

    final contractor = Contractor(
      projectId: widget.projectId,
      name: _nameController.text,
      type: _selectedType,
    );

    final contractorProvider = context.read<ContractorProvider>();
    // WHY: BUG-1 — Must await the create before popping. Previous code popped
    // first, which detached the context and lost the operation result.
    final success = await contractorProvider.createContractor(contractor);
    if (!context.mounted) return;
    if (success) {
      Navigator.pop(context);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(contractorProvider.error ?? 'Failed to add')),
      );
    }
  }
```

#### Step 2.1.2: Verify

Run: `pwsh -Command "flutter analyze lib/features/projects/presentation/widgets/add_contractor_dialog.dart"`

---

### Sub-phase 2.2: BUG-4 — Fix unarchive UI not updating

**Files:**
- Modify: `lib/features/projects/presentation/providers/project_provider.dart:556-566`

**Agent:** frontend-flutter-specialist-agent

#### Step 2.2.1: Add _buildMergedView() before notifyListeners()

In `toggleActive()`, after updating `_selectedProject` and before `notifyListeners()`, add the merged view rebuild:

```dart
    try {
      await _repository.setActive(id, newStatus);
      final index = _projects.indexWhere((p) => p.id == id);
      if (index != -1) {
        _projects[index] = project.copyWith(isActive: newStatus);
      }
      if (_selectedProject?.id == id) {
        _selectedProject = _selectedProject!.copyWith(isActive: newStatus);
      }
      // WHY: BUG-4 — archivedProjects getter reads from _mergedProjects,
      // which is only rebuilt by _buildMergedView(). Without this call,
      // the UI never sees the status change.
      _buildMergedView();
      notifyListeners();
      return true;
    }
```

#### Step 2.2.2: Verify

Run: `pwsh -Command "flutter analyze lib/features/projects/presentation/providers/project_provider.dart"`

---

### Sub-phase 2.3: BUG-9 — Fix photo dialog controller lifecycle

**Files:**
- Modify: `lib/features/entries/presentation/widgets/photo_detail_dialog.dart`

**Agent:** frontend-flutter-specialist-agent

#### Step 2.3.1: Convert from function-based to StatefulWidget

Replace the entire file. Keep the `PhotoDetailResult` class. Convert the `showPhotoDetailDialog` function to a thin wrapper that shows a dialog containing a new `_PhotoDetailDialogContent` StatefulWidget.

The StatefulWidget must:
1. Accept the same params: `photo`, `locations`, `imageService`
2. Create `filenameController` and `descriptionController` in `initState()`
3. Dispose both controllers in `dispose()`
4. Move `selectedLocationId` to state
5. Keep all existing UI layout identical

```dart
/// Shows a dialog to view and edit photo details.
/// Returns [PhotoDetailResult] if saved, null if cancelled.
Future<PhotoDetailResult?> showPhotoDetailDialog({
  required BuildContext context,
  required Photo photo,
  required List<Location> locations,
  required ImageService imageService,
}) {
  return showDialog<PhotoDetailResult>(
    context: context,
    builder: (dialogContext) => _PhotoDetailDialog(
      photo: photo,
      locations: locations,
      imageService: imageService,
    ),
  );
}

class _PhotoDetailDialog extends StatefulWidget {
  final Photo photo;
  final List<Location> locations;
  final ImageService imageService;

  const _PhotoDetailDialog({
    required this.photo,
    required this.locations,
    required this.imageService,
  });

  @override
  State<_PhotoDetailDialog> createState() => _PhotoDetailDialogState();
}

class _PhotoDetailDialogState extends State<_PhotoDetailDialog> {
  late final TextEditingController _filenameController;
  late final TextEditingController _descriptionController;
  String? _selectedLocationId;

  @override
  void initState() {
    super.initState();
    final currentName = widget.photo.filename
        .replaceAll('.jpg', '')
        .replaceAll('.jpeg', '');
    _filenameController = TextEditingController(text: currentName);
    _descriptionController = TextEditingController(text: widget.photo.notes ?? '');
    _selectedLocationId = widget.photo.locationId;
  }

  @override
  void dispose() {
    // WHY: BUG-9 — Controllers must be disposed to prevent memory leaks.
    // The previous StatefulBuilder approach had no dispose lifecycle.
    _filenameController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // ... same Dialog UI as before, but using _filenameController,
    // _descriptionController, _selectedLocationId, and setState()
    // instead of setDialogState()
  }
}
```

Keep all existing widget tree structure — just move it into the `build()` method. Replace `filenameController` -> `_filenameController`, `descriptionController` -> `_descriptionController`, `selectedLocationId` -> `_selectedLocationId`, `setDialogState` -> `setState`, and `dialogContext` -> `context`.

#### Step 2.3.2: Verify

Run: `pwsh -Command "flutter analyze lib/features/entries/presentation/widgets/photo_detail_dialog.dart"`

---

### Sub-phase 2.4: BUG-10 — Fix duplicate GlobalKeys on project edit navigation

**Files:**
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart:43`

**Agent:** frontend-flutter-specialist-agent

#### Step 2.4.1: Scope FormState key to project ID

Replace the GlobalKey declaration at line 43:

```dart
// BEFORE:
  final _formKey = GlobalKey<FormState>();

// AFTER:
  // WHY: BUG-10 — During GoRouter transitions, two ProjectSetupScreen instances
  // can coexist briefly. A plain GlobalKey collides. Scoping to projectId ensures
  // each instance has a unique key. The debugLabel is for diagnostics only.
  late final _formKey = GlobalKey<FormState>(
    debugLabel: 'projectSetup_${widget.projectId ?? "new"}',
  );
```

#### Step 2.4.2: Add ValueKey at router call site (REQUIRED)

**WHY (Adversarial H2):** The debugLabel fix alone is a no-op — it doesn't change key identity. The real fix is ensuring GoRouter creates a fresh widget instance when navigating to a different project. Find the route that builds `ProjectSetupScreen` in `lib/core/router/app_router.dart` and add a `ValueKey`:

```dart
ProjectSetupScreen(
  key: ValueKey(projectId),
  projectId: projectId,
)
```

Search `app_router.dart` for `ProjectSetupScreen` and add the `key: ValueKey(projectId)` parameter. This ensures GoRouter treats navigations to different projects as distinct widget instances, preventing overlay key collisions during transitions.

#### Step 2.4.3: Verify

Run: `pwsh -Command "flutter analyze lib/features/projects/presentation/screens/project_setup_screen.dart"`
Run: `pwsh -Command "flutter analyze lib/core/router/app_router.dart"`

---

### Sub-phase 2.5: BUG-5 — Add contractor edit capability

**Files:**
- Modify: `lib/features/projects/presentation/widgets/add_contractor_dialog.dart`
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart:558-678`

**Agent:** frontend-flutter-specialist-agent

#### Step 2.5.1: Add edit mode to AddContractorDialog

Add optional `existingContractor` parameter to the widget:

```dart
class AddContractorDialog extends StatefulWidget {
  final String projectId;
  final Contractor? existingContractor;

  const AddContractorDialog({
    super.key,
    required this.projectId,
    this.existingContractor,
  });

  static Future<void> show(BuildContext context, String projectId, {Contractor? existingContractor}) {
    return showDialog(
      context: context,
      builder: (context) => AddContractorDialog(
        projectId: projectId,
        existingContractor: existingContractor,
      ),
    );
  }
  // ...
}
```

In `_AddContractorDialogState`, update `initState` and the dialog:

```dart
  @override
  void initState() {
    super.initState();
    if (widget.existingContractor != null) {
      _nameController.text = widget.existingContractor!.name;
      _selectedType = widget.existingContractor!.type;
    }
  }
```

Update the dialog title:

```dart
  title: Text(widget.existingContractor != null ? 'Edit Contractor' : 'Add Contractor'),
```

Update the save button label:

```dart
  child: Text(widget.existingContractor != null ? 'Save' : 'Add'),
```

#### Step 2.5.2: Add _handleEdit logic alongside _handleAdd

Rename `_handleAdd` to `_handleSave` and branch on edit vs create:

```dart
  Future<void> _handleSave(BuildContext context) async {
    if (_nameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a contractor name')),
      );
      return;
    }

    final contractorProvider = context.read<ContractorProvider>();
    bool success;

    if (widget.existingContractor != null) {
      // WHY: BUG-5 — Edit mode: update existing contractor with new name/type.
      final updated = widget.existingContractor!.copyWith(
        name: _nameController.text,
        type: _selectedType,
      );
      success = await contractorProvider.updateContractor(updated);
    } else {
      final contractor = Contractor(
        projectId: widget.projectId,
        name: _nameController.text,
        type: _selectedType,
      );
      success = await contractorProvider.createContractor(contractor);
    }

    if (!context.mounted) return;
    if (success) {
      Navigator.pop(context);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(contractorProvider.error ?? 'Failed to save')),
      );
    }
  }
```

Update the button's onPressed from `_handleAdd` to `_handleSave`.

#### Step 2.5.3: Add edit button to contractor card in project_setup_screen.dart

In the contractor card (line 599 area), change `trailing` from a single `IconButton` to a `Row`:

```dart
  trailing: Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      IconButton(
        key: TestingKeys.contractorEditButton(contractor.id),
        icon: const Icon(Icons.edit_outlined, color: AppTheme.primaryCyan),
        onPressed: () => AddContractorDialog.show(
          context,
          _projectId!,
          existingContractor: contractor,
        ),
      ),
      IconButton(
        key: TestingKeys.contractorDeleteButton(contractor.id),
        icon: const Icon(Icons.delete_outline, color: AppTheme.statusError),
        onPressed: () => _confirmDeleteContractor(contractor),
      ),
    ],
  ),
```

#### Step 2.5.4: Add contractorEditButton to testing keys

**WHY (Adversarial M2):** Step 2.5.3 uses `TestingKeys.contractorEditButton(contractor.id)` which doesn't exist yet. Add it now to avoid compile errors.

In `lib/shared/testing_keys/contractors_keys.dart`, add:

```dart
  /// Creates a key for the edit button on a contractor card
  static Key contractorEditButton(String contractorId) => Key('contractor_edit_button_$contractorId');
```

Then forward it in `lib/shared/testing_keys/testing_keys.dart` in the TestingKeys facade class:

```dart
  static Key contractorEditButton(String contractorId) =>
      ContractorsTestingKeys.contractorEditButton(contractorId);
```

#### Step 2.5.5: Verify

Run: `pwsh -Command "flutter analyze lib/features/projects/"`

---

### Sub-phase 2.6: BUG-13 — Add form response delete button

**Files:**
- Modify: `lib/features/forms/presentation/screens/forms_list_screen.dart:171-186`

**Agent:** frontend-flutter-specialist-agent

#### Step 2.6.1: Add delete button next to "Open" button

Replace the `trailing` of the saved response `ListTile` (around line 176):

```dart
// BEFORE:
  trailing: FilledButton(
    onPressed: () { context.pushNamed('form-fill', ...); },
    child: const Text('Open'),
  ),

// AFTER:
  trailing: Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      FilledButton(
        onPressed: () {
          context.pushNamed(
            'form-fill',
            pathParameters: {'responseId': response.id},
          );
        },
        child: const Text('Open'),
      ),
      const SizedBox(width: 8),
      IconButton(
        // WHY: BUG-13 — Delete button for form responses. Uses existing
        // InspectorFormProvider.deleteResponse() which is already implemented.
        icon: const Icon(Icons.delete_outline, color: AppTheme.statusError),
        onPressed: () async {
          final confirmed = await showDialog<bool>(
            context: context,
            builder: (ctx) => AlertDialog(
              title: const Text('Delete Response?'),
              content: const Text('This action cannot be undone.'),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx, false),
                  child: const Text('Cancel'),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(ctx, true),
                  child: const Text('Delete', style: TextStyle(color: AppTheme.statusError)),
                ),
              ],
            ),
          );
          if (confirmed == true && context.mounted) {
            await context.read<InspectorFormProvider>().deleteResponse(response.id);
          }
        },
      ),
    ],
  ),
```

**NOTE:** Ensure `InspectorFormProvider` is imported. Also check that `AppTheme` is already imported (it should be based on the existing Card styling).

#### Step 2.6.2: Verify

Run: `pwsh -Command "flutter analyze lib/features/forms/presentation/screens/forms_list_screen.dart"`

---

### Sub-phase 2.7: BUG-14 — Fix inject-photo-direct for sync lifecycle

**Files:**
- Create: `test_assets/test_photo_1.jpg` (small ~10KB test JPEG)
- Create: `test_assets/test_photo_2.jpg` (small ~10KB test JPEG)
- Modify: `lib/core/driver/test_photo_service.dart:64-108`

**Agent:** backend-data-layer-agent

#### Step 2.7.1: Bundle test photo assets

Create `test_assets/` directory with two small JPEG files. Generate two 100x100 pixel JPEG images with distinct solid colors (one blue, one red) using the `image` package, and save them.

**IMPORTANT (Security M-2):** Do NOT register `test_assets/` in `pubspec.yaml` as Flutter assets. These files are read by the test harness code only (via `File` IO in debug mode), not via Flutter's asset bundle. They must NOT be bundled into release APKs.

#### Step 2.7.2: Update injectPhotoDirect to copy to persistent photo directory

In `test_photo_service.dart`, modify `injectPhotoDirect()` to copy the cleaned file to the app's persistent photo directory instead of leaving it in temp:

```dart
  Future<Map<String, dynamic>> injectPhotoDirect({
    required File file,
    required String entryId,
    required String projectId,
    required PhotoRepository photoRepository,
    required String photoDirectory,  // NEW: persistent photo dir path
  }) async {
    if (kReleaseMode || kProfileMode) {
      throw StateError('injectPhotoDirect is only available in debug mode');
    }

    final bytes = await file.readAsBytes();
    final image = img.decodeImage(bytes);
    if (image == null) {
      throw StateError('injectPhotoDirect: could not decode image for EXIF strip: ${file.path}');
    }
    final cleanBytes = img.encodeJpg(image, quality: 85);

    // WHY: BUG-14 — Write to the persistent photo directory (same as real photos)
    // so Phase 1 sync upload finds the file at the expected path.
    final baseName = file.uri.pathSegments.last.replaceAll(RegExp(r'[/\\]'), '_').replaceAll('..', '_');
    final filename = 'test_${DateTime.now().microsecondsSinceEpoch}_$baseName';
    final persistentFile = File('$photoDirectory/$filename');
    await persistentFile.writeAsBytes(cleanBytes);

    final photo = Photo(
      entryId: entryId,
      projectId: projectId,
      filePath: persistentFile.path,  // WHY: Use persistent path, not temp
      filename: filename,
    );
    final result = await photoRepository.createPhoto(photo);
    if (!result.isSuccess || result.data == null) {
      throw StateError('injectPhotoDirect: failed to create photo record: ${result.error}');
    }
    final created = result.data!;

    return {
      'id': created.id,
      'entryId': created.entryId,
      'localPath': created.filePath,
    };
  }
```

#### Step 2.7.3: Update driver endpoint caller in driver_server.dart

**WHY (Adversarial H1):** The driver endpoint at `lib/core/driver/driver_server.dart` (around line 603, `_handleInjectPhotoDirect`) calls `testPhotoService.injectPhotoDirect()`. It must pass the persistent photo directory.

Find `_handleInjectPhotoDirect` in `driver_server.dart` and update it to resolve the photo directory and pass it:

```dart
  // In _handleInjectPhotoDirect, before calling injectPhotoDirect:
  // Get the app's persistent photo directory
  final appDir = await getApplicationDocumentsDirectory();
  final photoDir = Directory('${appDir.path}/photos');
  if (!await photoDir.exists()) {
    await photoDir.create(recursive: true);
  }

  // Pass photoDirectory to injectPhotoDirect
  final result = await testPhotoService.injectPhotoDirect(
    file: tempFile,
    entryId: entryId,
    projectId: projectId,
    photoRepository: photoRepository,
    photoDirectory: photoDir.path,  // NEW parameter
  );
```

Make sure `path_provider` is imported (`import 'package:path_provider/path_provider.dart';`). It should already be available since other parts of the driver use it.

#### Step 2.7.4: Verify

Run: `pwsh -Command "flutter analyze lib/core/driver/"`

---

## Phase 3: Testing Keys (BUG-3/11/12)

### Sub-phase 3.1: Wire testing keys across all affected widgets

**Files:**
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_location_edit_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_weather_edit_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/review_summary_screen.dart`
- Modify: `lib/features/entries/presentation/widgets/entry_basics_section.dart`
- Modify: `lib/features/entries/presentation/widgets/entry_quantities_section.dart`
- Modify: `lib/features/settings/presentation/screens/edit_profile_screen.dart`
- Modify: `lib/features/settings/presentation/screens/settings_screen.dart`
- Modify: `lib/features/settings/presentation/screens/trash_screen.dart`
- Modify: `lib/features/settings/presentation/widgets/member_detail_sheet.dart`
- Modify: `lib/features/todos/presentation/screens/todos_screen.dart`
- Modify: `lib/features/photos/presentation/widgets/photo_thumbnail.dart`
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart` (equipment chip)
- Modify: `lib/shared/testing_keys/entries_keys.dart` (add any missing key definitions)
- Modify: `lib/shared/testing_keys/settings_keys.dart` (add any missing key definitions)
- Modify: `lib/shared/testing_keys/testing_keys.dart` (add any missing key definitions)
- Modify: `lib/shared/testing_keys/toolbox_keys.dart` (add any missing key definitions)

**Agent:** frontend-flutter-specialist-agent

#### Step 3.1.1: Audit existing testing key definitions

Read each testing keys file to identify which keys already exist vs need to be added. The git status shows these files are already modified, meaning some keys may already be defined but not yet wired to widgets.

Key categories needed:
- **Location dropdown items:** `locationOption(id)` keys on DropdownMenuItem widgets
- **Weather dialog items:** `weatherOption(name)` keys on weather selection widgets
- **Submit confirmation:** `submitCancelButton`, `submitConfirmButton` on dialog buttons
- **Todo delete:** `todoDeleteButton(id)` on IconButton
- **Form response "Open":** Testing key on the FilledButton
- **Edit profile fields:** `settingsInspectorNameField` etc. on TextFormField widgets
- **Photo thumbnail delete:** Key on the GestureDetector/delete button
- **Equipment chip delete:** Key on the delete action within equipment chips

#### Step 3.1.2: Wire keys to widgets

For each file, add `key: TestingKeys.keyName` to the relevant widget. This is mechanical — the pattern is:

```dart
// Example: adding key to a DropdownMenuItem
DropdownMenuItem(
  key: TestingKeys.locationOption(loc.id),
  value: loc.id,
  child: Text(loc.name),
),

// Example: adding key to an IconButton
IconButton(
  key: TestingKeys.todoDeleteButton(todo.id),
  icon: const Icon(Icons.delete),
  onPressed: () => _deleteTodo(todo),
),
```

**BUG-12 (EquipmentChip delete):** The `EquipmentChip` widget at `lib/features/projects/presentation/widgets/equipment_chip.dart` encapsulates the Chip's `onDeleted` handler internally. The delete icon is not separately tappable by the test driver.

**Approach (committed):** Add a `deleteKey` parameter to `EquipmentChip` and forward it to the Chip's internal delete icon. In `equipment_chip.dart`, add:

```dart
class EquipmentChip extends StatelessWidget {
  final Equipment equipment;
  final VoidCallback onDelete;
  final Key? deleteKey;  // NEW: for test automation

  const EquipmentChip({
    super.key,
    required this.equipment,
    required this.onDelete,
    this.deleteKey,
  });
```

Then in the Chip widget, replace `onDeleted: onDelete` with a custom trailing `IconButton`:

```dart
  // Instead of Chip(onDeleted:), use InputChip or a Row with a keyed delete button
  InputChip(
    label: Text(equipment.name),
    deleteIcon: Icon(Icons.cancel, key: deleteKey, size: 18),
    onDeleted: onDelete,
  )
```

At the call site in `project_setup_screen.dart:_buildEquipmentChip`, pass:
```dart
EquipmentChip(
  equipment: equipment,
  onDelete: () => _confirmDeleteEquipment(equipment, contractorId),
  deleteKey: TestingKeys.equipmentDeleteButton(equipment.id),
)
```

Add `equipmentDeleteButton(String id)` to testing keys if not present

#### Step 3.1.3: Verify all files compile

Run: `pwsh -Command "flutter analyze"`

---

## Phase 4: Final Verification

### Sub-phase 4.1: Full static analysis

**Agent:** general-purpose

#### Step 4.1.1: Run full analysis

Run: `pwsh -Command "flutter analyze"`

Expect zero errors. Warnings are acceptable if pre-existing.

#### Step 4.1.2: Run existing tests

Run: `pwsh -Command "flutter test"`

All existing tests must pass. No new tests are added in this plan — the E2E suite validates these fixes.

#### Step 4.1.3: Push RPC migration

Run: `npx supabase db push`

Verify the migration applies cleanly.
