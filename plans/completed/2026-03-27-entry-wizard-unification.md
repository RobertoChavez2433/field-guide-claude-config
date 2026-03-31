# Entry Wizard Unification Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Eliminate create/edit entry screen bifurcation into a unified draft-based editor, fix extrasOverruns data loss, seed 0582B form, clean up contractor card tokens, and rename "Materials Used" to "Pay Items Used".
**Spec:** `.claude/specs/2026-03-27-entry-wizard-unification-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-27-entry-wizard-unification/`

**Architecture:** The entry editor becomes a single unified screen that always operates on a persisted DailyEntry. The create route immediately inserts a draft row (or finds an existing one for the same project+date), then loads the full editor. All 9 sections are always visible. The header auto-expands/collapses based on whether location and weather are set.
**Tech Stack:** Flutter, SQLite (drift-style raw queries), Provider, GoRouter
**Blast Radius:** 13 direct files, 0 dependents, 2 test files, 11 dead code items + 1 file deletion

---

## Phase 1: Data Layer

### Sub-phase 1.1: ExtrasOverruns Controller in EntryEditingController

**Files:**
- Modify: `lib/features/entries/presentation/controllers/entry_editing_controller.dart:55-126`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 1.1.1: Add extrasOverruns controller, focus node, and disposal

In `entry_editing_controller.dart`, add the extrasOverruns controller and focus node alongside the existing fields.

After the existing `visitorsController`/`visitorsFocus` declarations (around line 73), add:

```dart
// WHY: extrasOverruns field exists on DailyEntry but was never wired to a controller,
// causing data loss on save — the field was displayed read-only but never persisted from edits.
final extrasOverrunsController = TextEditingController();
final extrasOverrunsFocus = FocusNode();
```

In the `dispose()` method, after `_visitorsController.dispose()` and `_visitorsFocus.dispose()`, add:

```dart
extrasOverrunsController.dispose();
extrasOverrunsFocus.dispose();
```

NOTE: The existing controllers use a private naming convention (`_activitiesController`) with public getters. Follow the same pattern — add private field `_extrasOverrunsController` with public getter `extrasOverrunsController`, and `_extrasOverrunsFocus` with public getter `extrasOverrunsFocus`. Match whichever pattern the existing fields use.

#### Step 1.1.2: Wire extrasOverruns into populateFrom

In `populateFrom(DailyEntry entry)` (lines 90-100), after `_visitorsController.text = entry.visitors ?? '';`, add:

```dart
// WHY: Without this, editing an existing entry with extrasOverruns shows an empty field
_extrasOverrunsController.text = entry.extrasOverruns ?? '';
```

#### Step 1.1.3: Wire extrasOverruns into buildEntry

In `buildEntry(DailyEntry base)` (lines 106-126), add to the `copyWith` call:

```dart
extrasOverruns: _extrasOverrunsController.text.trim().isEmpty ? null : _extrasOverrunsController.text.trim(),
```

NOTE: This goes alongside the existing `visitors:` line in the copyWith block.

#### Step 1.1.4: Wire dirty tracking

NOTE: The existing controllers do NOT use `addListener` for dirty tracking. Instead, dirty state is managed via `onChanged: (_) => widget.controller.markDirty()` in the UI TextFields (see `_EditableSafetyCardState.build` at line 1393). The `markDirty()` method is public on `EntryEditingController` (line 152).

No code change needed in the controller itself — dirty tracking for extrasOverruns will be wired in the UI when the TextField is added in Phase 3 (Step 3.1.1) with `onChanged: (_) => widget.controller.markDirty()`.

#### Step 1.1.5: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`
Expected: Existing tests still pass (no behavioral change yet, just wiring)

---

### Sub-phase 1.2: Safety Fields Query

**Files:**
- Modify: `lib/features/entries/data/datasources/daily_entry_local_datasource.dart`
- Modify: `lib/features/entries/data/repositories/daily_entry_repository.dart`

**Agent**: `backend-data-layer-agent`

#### Step 1.2.1: Add getLastEntrySafetyFields to datasource

In `daily_entry_local_datasource.dart`, add a new method:

```dart
/// Returns the 5 safety field values from the most recent entry in the given project.
/// Returns null if no previous entries exist.
/// WHY: "Copy from last entry" feature needs to pre-fill safety fields from the
/// most recent same-project entry to save inspectors from re-typing repetitive data.
Future<Map<String, String?>?> getLastEntrySafetyFields(String projectId) async {
  // CRITICAL FIX: db is DatabaseService, not Database. Must call db.database first.
  // Pattern from getDatesWithEntries() at line 72-73 of this same file.
  final database = await db.database;
  // FROM SPEC: "returns 5 safety field values from most recent entry"
  final results = await database.rawQuery(
    '''SELECT site_safety, sesc_measures, traffic_control, visitors, extras_overruns, date
       FROM $tableName
       WHERE project_id = ? AND deleted_at IS NULL AND status != ?
       ORDER BY date DESC, created_at DESC
       LIMIT 1''',
    [projectId, EntryStatus.draft.name],
  );
  if (results.isEmpty) return null;
  final row = results.first;
  return {
    'siteSafety': row['site_safety'] as String?,
    'sescMeasures': row['sesc_measures'] as String?,
    'trafficControl': row['traffic_control'] as String?,
    'visitors': row['visitors'] as String?,
    'extrasOverruns': row['extras_overruns'] as String?,
    'date': row['date'] as String?,
  };
}
```

NOTE: Uses `final database = await db.database;` then `database.rawQuery(...)` — matching the existing pattern at `daily_entry_local_datasource.dart:72-73`. Added `created_at DESC` tiebreaker per spec. Uses `$tableName` instead of hardcoded `'daily_entries'` for consistency.

#### Step 1.2.2: Add getLastEntrySafetyFields to repository

In `daily_entry_repository.dart`, add:

```dart
/// Returns safety fields from the most recent non-draft entry in the project.
/// WHY: Supports the "Copy from last entry" button in the safety card.
/// Returns null map values for missing fields, or null if no entries exist.
Future<Map<String, String?>?> getLastEntrySafetyFields(String projectId) async {
  // NOTE: Uses _localDatasource (the field name in this repository class, line 11).
  // Returns raw map instead of RepositoryResult — simpler for a read-only convenience query.
  return _localDatasource.getLastEntrySafetyFields(projectId);
}
```

NOTE: The datasource field is named `_localDatasource` (see `daily_entry_repository.dart:11`). Returns nullable map directly instead of RepositoryResult — avoids the `.when()` antipattern since `RepositoryResult` has no `.when()` method (only `.data`, `.error`, `.isSuccess`).

#### Step 1.2.3: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`
Expected: Existing tests still pass

---

### Sub-phase 1.3: 0582B Form Seeding

**Files:**
- Modify: `lib/main.dart:200-307`

**Agent**: `backend-data-layer-agent`

#### Step 1.3.1: Add _seedBuiltinForms function

Add a top-level or static function near the startup logic in `main.dart`:

```dart
/// Seeds the built-in 0582B form if not already present.
/// WHY: Fresh installs need the 0582B form available without manual setup.
/// FROM SPEC: "one InspectorForm row (id: 'mdot_0582b', isBuiltin: true, projectId: null)"
Future<void> _seedBuiltinForms(InspectorFormRepository formRepository) async {
  final hasBuiltins = await formRepository.hasBuiltinForms();
  if (hasBuiltins) return;

  // FROM SPEC: name must be 'MDOT 0582B Density' (not just 'MDOT 0582B')
  // GROUND TRUTH FIX: createForm returns RepositoryResult — check it.
  final result = await formRepository.createForm(InspectorForm(
    id: 'mdot_0582b',
    name: 'MDOT 0582B Density',
    templatePath: FormPdfService.mdot0582bTemplatePath,
    isBuiltin: true,
  ));
  if (!result.isSuccess) {
    Logger.db('Failed to seed 0582B form: ${result.error}');
  }
}
```

NOTE: Check the `FormPdfService` import — it may already be imported in main.dart or may need to be added. The path is `lib/features/forms/services/form_pdf_service.dart` or similar — verify by searching for the class.

#### Step 1.3.2: Call _seedBuiltinForms at startup

In `main.dart`, find the fresh install block (around lines 302-304) and the general startup flow. The seeding should run on EVERY startup (not just fresh install) since the check is idempotent:

After `inspectorFormRepository` is created (around line 230) and before the app runs, add:

```dart
// WHY: Idempotent — checks hasBuiltinForms() first, only seeds if missing.
// Runs every startup (not just fresh install) to handle upgrades from pre-seed versions.
await _seedBuiltinForms(inspectorFormRepository);
```

NOTE: Find the right insertion point — it must be after `inspectorFormRepository` is initialized but before the `runApp()` call. Look for where other startup tasks run.

#### Step 1.3.3: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`
Expected: Existing tests still pass (seeding is startup-only)

---

## Phase 2: Entry Screen Unification

### Sub-phase 2.1: Draft Creation and Route Unification

**Files:**
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart:77-289`
- Modify: `lib/core/router/app_router.dart:429-455`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.1.1: Remove _isCreateMode and add draft state tracking

In `entry_editor_screen.dart`, replace the `_isCreateMode` getter (line 83) and modify state fields:

Remove:
```dart
bool get _isCreateMode => widget.entryId == null;
```

Add state field:
```dart
// WHY: Draft tracking replaces create/edit mode bifurcation.
// The screen always has an entry — either loaded or freshly created as draft.
bool _isDraftEntry = false;
```

NOTE: The `_isCreateMode` getter is referenced throughout the file. Every reference must be updated in subsequent steps. Do NOT do a blind find-replace — each usage needs different handling.

#### Step 2.1.2: Rewrite _loadEntryData to always resolve to an entry

Replace the entire `_loadEntryData` method (lines 205-289) with a unified version:

```dart
/// Loads or creates the entry, then loads all related data.
/// WHY: Unified flow — no create/edit branching. Both paths end with a loaded _entry.
/// FROM SPEC: "Create route: checks for existing draft on same project+date first, creates if not found"
Future<void> _loadEntryData() async {
  final entryProvider = context.read<DailyEntryProvider>();
  final locationProvider = context.read<LocationProvider>();
  final projectProvider = context.read<ProjectProvider>();
  final contractorProvider = context.read<ContractorProvider>();
  final equipmentProvider = context.read<EquipmentProvider>();
  final quantityProvider = context.read<EntryQuantityProvider>();
  final photoProvider = context.read<PhotoProvider>();
  final personnelTypeProvider = context.read<PersonnelTypeProvider>();
  final formProvider = context.read<InspectorFormProvider>();
  final bidItemProvider = context.read<BidItemProvider>();

  DailyEntry? entry;

  if (widget.entryId != null) {
    // Edit route — load existing entry
    entry = await entryProvider.loadEntry(widget.entryId!);
  } else {
    // Create route — check for existing draft on same project+date
    // FROM SPEC: "checks for existing draft on same project+date first, creates if not found"
    // CRITICAL FIX: DailyEntryProvider has NO getByDate() method.
    // Use DailyEntryRepository via the provider's repository getter, or use the
    // DailyEntryLocalDatasource which has getByDate(projectId, date).
    // Pattern: access repository through entryProvider or read datasource from context.
    final existingEntries = await entryProvider.repository.getByDate(
      widget.projectId, widget.date!,
    );
    // SECURITY FIX: Filter to drafts only — don't reopen submitted entries
    final existingDraft = existingEntries
        .where((e) => e.status == EntryStatus.draft)
        .firstOrNull;
    if (existingDraft != null) {
      entry = existingDraft;
    } else {
      // Persist minimal draft immediately
      // FROM SPEC: "persist minimal draft immediately (projectId + date + status: draft)"
      // HIGH FIX: Spec says all fields null/empty — do NOT pre-fill locationId or weather.
      // HIGH FIX: Must include createdByUserId for auth checks (canEditEntry).
      final draft = DailyEntry(
        id: _pendingEntryId,
        projectId: widget.projectId,
        date: widget.date!,
        status: EntryStatus.draft,
        createdByUserId: context.read<AuthProvider>().userId,
      );
      // CRITICAL FIX: RepositoryResult has no .when() method.
      // Use .isSuccess / .data / .error pattern.
      final result = await entryProvider.createEntry(draft);
      if (result != null) {
        entry = result;
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to create entry')),
        );
      }
      _isDraftEntry = true;
    }
  }

  if (entry == null) {
    if (mounted) setState(() => _isLoading = false);
    return;
  }

  // MINOR FIX: Track draft status for ALL drafts (new + reopened) so back-button
  // discard prompt fires for reopened empty drafts too.
  // MINOR FIX: Promote nullable entry to local non-null variable for Dart flow analysis
  final loadedEntry = entry!;
  _isDraftEntry = loadedEntry.status == EntryStatus.draft;

  // Unified data loading — always runs regardless of how we got the entry
  final projectId = loadedEntry.projectId;
  await Future.wait([
    quantityProvider.loadQuantitiesForEntry(loadedEntry.id),
    bidItemProvider.loadBidItems(projectId),
    locationProvider.loadLocations(projectId),
    photoProvider.loadPhotosForEntry(loadedEntry.id),
    formProvider.loadResponsesForEntry(loadedEntry.id),
    personnelTypeProvider.loadTypesForProject(projectId),
    contractorProvider.loadContractors(projectId),
  ]);

  final contractorIds = contractorProvider.contractors.map((c) => c.id).toList();
  await equipmentProvider.loadEquipmentForContractors(contractorIds);

  await _contractorController?.loadForEntry(
    loadedEntry.id, projectId,
    personnelTypeProvider: personnelTypeProvider,
    contractorProvider: contractorProvider,
    equipmentProvider: equipmentProvider,
  );

  _editingController.populateFrom(entry!);
  await _photoManager.loadPhotos(photoProvider, loadedEntry.id);
  await _formManager.loadForms(formProvider, loadedEntry.id);

  final location = loadedEntry.locationId != null
      ? locationProvider.getLocationById(loadedEntry.locationId!)
      : null;
  final project = projectProvider.getProjectById(projectId);

  if (mounted) {
    setState(() {
      _entry = entry;
      _locationName = location?.name;
      _projectName = project?.name ?? 'Unknown Project';
      _projectNumber = project?.projectNumber ?? '';
      _isLoading = false;
    });
  }
}
```

NOTE: `entryProvider.repository` returns `DailyEntryRepository` via `BaseListProvider.repository` getter (public, `base_list_provider.dart:14`). `getByDate()` returns `List<DailyEntry>` (see `daily_entry_repository.dart:44`, `daily_entry_local_datasource.dart:27-33`).

NOTE: The `DailyEntry` constructor uses all named optional params (see model source). `createdAt`/`updatedAt` auto-populate via constructor defaults. Weather is intentionally left null (not `WeatherCondition.sunny`) so the adaptive header expands.

#### Step 2.1.3: Update build method to remove create/edit branching

In the `build` method (lines 1020-1074), replace:

```dart
_isCreateMode ? _buildCreateSections() : _buildEditSections(),
```

With:

```dart
// WHY: Unified sections — no more create/edit branching
// FROM SPEC: "No _isCreateMode branching in entry_editor_screen.dart"
_buildSections(),
```

Also update the loading state title:

Replace:
```dart
appBar: AppBar(title: Text(_isCreateMode ? 'New Entry' : 'Loading...')),
```

With:
```dart
appBar: AppBar(title: const Text('Loading...')),
```

Also update the "not found" guard — remove the `!_isCreateMode &&` check:

Replace:
```dart
if (!_isCreateMode && _entry == null) {
```

With:
```dart
if (_entry == null) {
```

#### Step 2.1.4: Create unified _buildSections method

Create a `_buildSections()` method that merges `_buildCreateSections()` and `_buildEditSections()`. This should return ALL 9 sections that were previously only in edit mode.

```dart
/// Builds all 9 entry sections in unified layout.
/// WHY: Replaces _buildCreateSections + _buildEditSections bifurcation.
/// FROM SPEC: "Create entry navigates to unified screen with all 9 sections visible"
List<Widget> _buildSections() {
  // NOTE: Reuse the exact widget list from _buildEditSections(), removing any
  // _isCreateMode conditionals. All sections are always visible.
  // The implementation should be the body of the old _buildEditSections()
  // with _isCreateMode references removed.
  //
  // IMPORTANT: Copy the full implementation from _buildEditSections (lines 1145-1265).
  // Do NOT invent widgets — use the exact existing section widgets.
}
```

NOTE: The actual implementation is just the body of `_buildEditSections()`. Copy it verbatim and remove any `_isCreateMode` conditionals within it.

#### Step 2.1.5: Implement adaptive header expansion

Find the header/basics section in the sections list. The header should auto-expand when location or weather is empty, and collapse when set.

```dart
// FROM SPEC: "Header auto-expands when location/weather empty, collapses when set"
// WHY: New drafts need the user to set location/weather first, but existing entries
// should show a compact header to maximize screen real estate.
final bool _headerExpanded = _entry?.locationId == null || _entry?.weather == null;
```

Pass `_headerExpanded` as the initial expansion state to whichever widget handles the header. Check how `EntryBasicsSection` or the header widget accepts expansion state — it may use `initiallyExpanded`, `isExpanded`, or similar. Adapt accordingly.

#### Step 2.1.6: Implement back button draft discard prompt

Override `_onBackPressed` or the back button handler. Find where the back navigation is handled (likely in `_buildAppBar` or a `WillPopScope`/`PopScope`):

First, add the `_isEmptyDraft()` helper method that the spec defines:

```dart
/// FROM SPEC: "checks no locationId, no weather, no temperature, no activities,
/// no safety fields, no contractors, no photos, no quantities, no forms"
/// WHY: Only prompt to discard if the entry is truly empty — any meaningful data means keep.
bool _isEmptyDraft() {
  final entry = _entry;
  if (entry == null) return true;

  // Check model fields
  if (entry.locationId != null) return false;
  if (entry.weather != null) return false;
  if (entry.tempLow != null || entry.tempHigh != null) return false;

  // Check text controllers (may have unsaved edits)
  if (_editingController.activitiesController.text.trim().isNotEmpty) return false;
  if (_editingController.siteSafetyController.text.trim().isNotEmpty) return false;
  if (_editingController.sescController.text.trim().isNotEmpty) return false;
  if (_editingController.trafficController.text.trim().isNotEmpty) return false;
  if (_editingController.visitorsController.text.trim().isNotEmpty) return false;
  if (_editingController.extrasOverrunsController.text.trim().isNotEmpty) return false;

  // Check related entities via their providers/managers
  // GROUND TRUTH FIX: ContractorEditingController has `contractorsById` (Map), not `contractors`
  if (_contractorController != null && _contractorController!.contractorsById.isNotEmpty) return false;
  if (_photoManager.photos.isNotEmpty) return false;
  final quantityProvider = context.read<EntryQuantityProvider>();
  if (quantityProvider.quantities.isNotEmpty) return false;
  final formProvider = context.read<InspectorFormProvider>();
  if (formProvider.responses.isNotEmpty) return false;

  return true;
}
```

NOTE: Check the actual getter names on `_contractorController`, `_photoManager`, `EntryQuantityProvider`, and `InspectorFormProvider`. They may use `.items`, `.entries`, `.data` instead of `.contractors`, `.photos`, `.quantities`, `.responses`. Verify against actual source.

Then implement back navigation:

```dart
/// FROM SPEC: "Back button: if empty draft -> prompt keep/discard; if has data -> auto-save + pop"
Future<bool> _handleBackNavigation() async {
  // HIGH FIX: Use _isEmptyDraft() instead of isDirty — isDirty only tracks text changes,
  // not whether location/weather/contractors/photos/etc have been set.
  if (_isDraftEntry && _isEmptyDraft()) {
    // Empty draft — ask user
    final shouldDiscard = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Discard empty draft?'),
        content: const Text('This entry has no data yet.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Keep Draft'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Discard'),
          ),
        ],
      ),
    );
    if (shouldDiscard == true && _entry != null) {
      // CRITICAL FIX: Use entryProvider to delete, not context.read<DailyEntryRepository>()
      // which is not registered as a standalone Provider.
      final entryProvider = context.read<DailyEntryProvider>();
      await entryProvider.deleteEntry(_loadedEntry.id);
    }
    return true; // Allow pop
  }

  // Has data — auto-save before popping
  if (_editingController.isDirty) {
    await _autoSaveEntry();
  }
  return true; // Allow pop
}
```

NOTE: Check how back navigation is currently handled. If there's a `WillPopScope`, replace it with `PopScope` (Flutter 3.x preferred). If there's a custom back button in the app bar, wire to this method.

NOTE: Check if `DailyEntryProvider` has a `deleteEntry(id)` method. If not, check for `delete(id)` or route through the repository. The existing `_confirmDelete` method at line 693 shows the current delete pattern — reuse it.

#### Step 2.1.7: Update AppBar references to _isCreateMode

Search the `_buildAppBar` method for any `_isCreateMode` references and replace:
- Title: Use `_entry?.status == EntryStatus.draft ? 'New Entry' : 'Edit Entry'` or similar
- Any conditional buttons: Remove the create/edit branching

#### Step 2.1.8: Update all remaining _isCreateMode references

Search the entire file for `_isCreateMode`. Each reference needs individual attention:
- In save methods: Unify into a single save flow (always updates the existing draft/entry)
- In UI conditionals: Remove or replace with status-based checks
- In navigation: Remove create-mode-specific navigation

NOTE: This is the most error-prone step. Every `_isCreateMode` reference must be addressed. Do NOT leave any references — the getter is being deleted.

#### Step 2.1.9: Update route in app_router.dart

In `app_router.dart`, the create route (lines 429-443) currently passes `entryId` as an optional query param. No structural change needed here since the screen now handles the null entryId case by creating a draft. However, verify the `/report/:entryId` route (lines 444-455) still works — the `projectId: ''` is problematic since we now always need it for data loading.

For the report route, the entry's `projectId` will be loaded from the database, so the empty string passed from the router is overridden during `_loadEntryData`. Verify this is the case. If not, the router may need to look up the entry's projectId:

```dart
// NOTE: The report route passes projectId: '' because it only has entryId.
// _loadEntryData handles this by loading the entry first, then using entry.projectId.
// No change needed IF the unified _loadEntryData uses entry.projectId for all subsequent loads.
```

#### Step 2.1.10: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`
Expected: Some tests may fail due to the create/edit unification — note failures for Phase 6

---

### Sub-phase 2.2: EntryActionBar Simplification

**Files:**
- Modify: `lib/features/entries/presentation/widgets/entry_action_bar.dart:11-151`
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart` (callsite)

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.2.1: Remove create mode from EntryActionBar

In `entry_action_bar.dart`, remove:
- `isCreateMode` parameter
- `onSaveDraft` callback
- `onSubmit` callback
- `_buildCreateActions` method

The widget should only have the edit-mode indicator/save behavior. The simplified constructor:

```dart
/// WHY: Create mode no longer exists — all entries are persisted drafts edited in-place.
/// FROM SPEC: "EntryActionBar.isCreateMode param, onSaveDraft, onSubmit, _buildCreateActions"
class EntryActionBar extends StatelessWidget {
  final bool isDirty;
  final bool isSaving;
  // ... keep only edit-mode params and callbacks
```

NOTE: Check what the edit-mode build method (`_buildEditModeIndicator` or similar) needs and keep only those params.

#### Step 2.2.2: Update EntryActionBar callsite in entry_editor_screen.dart

Find where `EntryActionBar` is instantiated in the entry editor screen and remove the create-mode params:

Remove: `isCreateMode: _isCreateMode`, `onSaveDraft: _saveDraft`, `onSubmit: _persistCreateEntry`

#### Step 2.2.3: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`
Expected: Tests may need updating — note for Phase 6

---

## Phase 3: Safety Card Enhancement

### Sub-phase 3.1: ExtrasOverruns TextField and Copy Button

**Files:**
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart` (safety card section, lines 1343-1480)

**Agent**: `frontend-flutter-specialist-agent`

#### Step 3.1.1: Add extrasOverruns TextField to edit mode

In the `_EditableSafetyCard` build method (or wherever the safety card edit mode is built), find the section with the 4 TextFields (siteSafety, sesc, traffic, visitors). After the visitors field, add:

```dart
// WHY: extrasOverruns was read-only in view mode and missing entirely in edit mode,
// causing data loss — any existing value was displayed but couldn't be modified.
// FROM SPEC: "extrasOverruns persists on save and is editable in the safety card"
const SizedBox(height: 12),
TextField(
  controller: _editingController.extrasOverrunsController,
  focusNode: _editingController.extrasOverrunsFocus,
  decoration: const InputDecoration(
    labelText: 'Extras / Overruns',
    hintText: 'Enter any extras or overruns...',
  ),
  maxLines: 3,
  minLines: 1,
  key: TestingKeys.entryWizardExtras,
),
```

NOTE: Check how the other TextFields in the safety card are structured — they may use custom `InputDecoration`, specific styling, or wrapper widgets. Match the exact pattern. The `TestingKeys.entryWizardExtras` key already exists in `entries_keys.dart`.

NOTE: The safety card is `_EditableSafetyCard` which receives the `EntryEditingController` as `widget.controller`. The new controller/focus are already accessible via `widget.controller.extrasOverrunsController`.

MEDIUM FIX: Also update `_EditableSafetyCardState._startEditing()` (line 1324-1330) to populate the new extrasOverruns controller. The method manually sets the 4 safety controllers from the entry — add the 5th:
```dart
// After the existing 4 controller population lines in _startEditing():
widget.controller.extrasOverrunsController.text = widget.entry.extrasOverruns ?? '';
```

MEDIUM FIX: Add `onChanged: (_) => widget.controller.markDirty()` to the extrasOverruns TextField (matching the pattern of the other 4 fields in the card).

#### Step 3.1.2: Add "Copy from last entry" button

MEDIUM FIX: The `_copyFromLastEntry` method lives on `_EntryEditorScreenState`, but the button is inside `_EditableSafetyCard`. Add an `onCopyFromLast` callback parameter to `_EditableSafetyCard`:

```dart
// In _EditableSafetyCard class (line 1303), add to constructor:
final VoidCallback? onCopyFromLast;
```

Then in `_buildSafetySection` wrapper (line 1274), pass the callback:
```dart
_EditableSafetyCard(
  // ... existing params ...
  onCopyFromLast: _copyFromLastEntry,
)
```

In the safety card build method, add the button in the edit mode section (after the "Done" button or above the fields):

```dart
// FROM SPEC: "'Copy from last entry' fills empty safety fields from most recent same-project entry"
// WHY: Inspectors often have identical safety conditions across entries in the same project.
if (widget.onCopyFromLast != null)
  Align(
    alignment: Alignment.centerLeft,
    child: TextButton.icon(
      onPressed: widget.onCopyFromLast,
      icon: const Icon(Icons.content_copy, size: 16),
      label: const Text('Copy from last entry'),
    ),
  ),
```

#### Step 3.1.3: Implement _copyFromLastEntry method

Add to the screen state class:

```dart
/// Copies safety fields from the most recent non-draft entry in the same project.
/// FROM SPEC: "fills only empty fields, toast with source date"
Future<void> _copyFromLastEntry() async {
  // CRITICAL FIX: DailyEntryRepository is NOT registered as a standalone Provider.
  // Access through DailyEntryProvider's public repository getter instead.
  final entryProvider = context.read<DailyEntryProvider>();
  final fields = await entryProvider.repository.getLastEntrySafetyFields(_entry!.projectId);

  if (fields == null) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No previous entries found')),
      );
    }
    return;
  }

  final controller = _editingController;
  int copiedCount = 0;

  // WHY: Only fill empty fields — don't overwrite user's existing input
  if (controller.siteSafetyController.text.isEmpty && fields['siteSafety'] != null) {
    controller.siteSafetyController.text = fields['siteSafety']!;
    copiedCount++;
  }
  if (controller.sescController.text.isEmpty && fields['sescMeasures'] != null) {
    controller.sescController.text = fields['sescMeasures']!;
    copiedCount++;
  }
  if (controller.trafficController.text.isEmpty && fields['trafficControl'] != null) {
    controller.trafficController.text = fields['trafficControl']!;
    copiedCount++;
  }
  if (controller.visitorsController.text.isEmpty && fields['visitors'] != null) {
    controller.visitorsController.text = fields['visitors']!;
    copiedCount++;
  }
  if (controller.extrasOverrunsController.text.isEmpty && fields['extrasOverruns'] != null) {
    controller.extrasOverrunsController.text = fields['extrasOverruns']!;
    copiedCount++;
  }

  if (copiedCount > 0) {
    controller.markDirty();
    if (mounted) {
      // FROM SPEC: "toast with source date"
      // MINOR FIX: Format raw ISO date for human readability
      final rawDate = fields['date'];
      final sourceDate = rawDate != null
          ? DateFormat('MMM d, y').format(DateTime.parse(rawDate))
          : 'previous entry';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Copied $copiedCount field(s) from $sourceDate')),
      );
    }
  } else if (mounted) {
    // FROM SPEC: "Button still visible but tap is a no-op (all fields already have content)"
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('All fields already have data')),
    );
  }
}
```

NOTE: Repository returns `Map<String, String?>?` directly (nullable map, not RepositoryResult). The controller getter names (`siteSafetyController`, `sescController`, `trafficController`, `visitorsController`, `extrasOverrunsController`) are verified against `entry_editing_controller.dart:55-73`. Calls `markDirty()` after copying to trigger auto-save on next blur.

#### Step 3.1.4: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`
Expected: Tests compile and safety card changes are visible

---

## Phase 4: Contractor Card Token Migration

### Sub-phase 4.1: entry_contractors_section.dart Token Migration

**Files:**
- Modify: `lib/features/entries/presentation/widgets/entry_contractors_section.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 4.1.1: Replace header hardcoded values

FROM SPEC: Typography and spacing replacements for the section header.

Replace in the header area:
```
EdgeInsets.all(16)          → EdgeInsets.all(AppTheme.space4)
Radius.circular(12)         → Radius.circular(AppTheme.radiusMedium)
SizedBox(width: 8)          → SizedBox(width: AppTheme.space2)
fontSize: 16, bold           → Theme.of(context).textTheme.titleMedium
```

NOTE: For typography, replace `TextStyle(fontSize: 16, fontWeight: FontWeight.bold)` with `Theme.of(context).textTheme.titleMedium`. If the text style also has color, apply color separately: `Theme.of(context).textTheme.titleMedium?.copyWith(color: ...)`.

#### Step 4.1.2: Replace summary badge values

```
fontSize: 12, textSecondary  → Theme.of(context).textTheme.labelSmall
```

#### Step 4.1.3: Replace footer hardcoded values

FROM SPEC: Footer padding should match header — both `space4` (16px):
```
EdgeInsets.all(12)           → EdgeInsets.all(AppTheme.space4)  // Match header per spec
SizedBox(width: 4)           → SizedBox(width: AppTheme.space2)  // Match header icon gap per spec
fontSize: 13, primaryCyan    → Theme.of(context).textTheme.labelMedium?.copyWith(color: AppTheme.primaryCyan)
```

#### Step 4.1.4: Replace empty state

```
italic, textSecondary        → Theme.of(context).textTheme.bodySmall?.copyWith(fontStyle: FontStyle.italic)
```

#### Step 4.1.5: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`
Expected: No functional changes, only visual token alignment

---

### Sub-phase 4.2: contractor_editor_widget.dart Token Migration

**Files:**
- Modify: `lib/features/entries/presentation/widgets/contractor_editor_widget.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 4.2.1: Replace ContractorEditorWidget typography

Apply FROM SPEC token mapping:

```
Edit contractor name (fontSize: 15, bold)    → textTheme.titleSmall
View contractor name (fontSize: 14, w600)    → textTheme.titleSmall
Type badge (fontSize: 10, w600)              → textTheme.labelSmall
Personnel count (fontSize: 11)               → textTheme.labelSmall
Counts display (fontSize: 12)                → textTheme.bodySmall
Equipment chips view (fontSize: 11)          → textTheme.labelSmall
Equipment chips edit (fontSize: 12)          → textTheme.labelSmall
Counter label (fontSize: 11)                 → textTheme.labelSmall
Counter value (fontSize: 14, bold)           → textTheme.titleSmall
"Equipment" label (fontSize: 13, w600)       → textTheme.labelMedium
"Add Equipment" (fontSize: 11, w500)         → textTheme.labelSmall?.copyWith(color: AppTheme.primaryCyan)
"Add Personnel Type" (fontSize: 11, w500)    → textTheme.labelSmall?.copyWith(color: AppTheme.primaryCyan)
```

#### Step 4.2.2: Replace ContractorEditorWidget spacing

```
EdgeInsets.all(16)                           → EdgeInsets.all(AppTheme.space4)
border width 2                               → keep as-is (not a design token)
AppTheme.radiusMedium                        → already correct, keep
Type badge padding (horizontal: 6, vertical: 2) → keep as-is (sub-token level)
Type badge radius: 4                         → AppTheme.radiusSmall (which is 8)
```

WAIT — `radiusSmall` is 8 but the current value is 4. The spec says "hardcoded 4 -> AppTheme.radiusSmall". Since `radiusSmall = 8`, this is a deliberate visual change to make badges more rounded. Apply as specified.

```
Equipment wrap spacing: 6/4 (view)           → AppTheme.space2 / AppTheme.space1 (8/4)
Equipment wrap spacing: 6/6 (edit)           → AppTheme.space2 / AppTheme.space2 (8/8)
Personnel wrap spacing: 16/8                 → AppTheme.space4 / AppTheme.space2 (16/8) — FROM SPEC
```

NOTE: `space2/space1` means `Wrap(spacing: AppTheme.space2, runSpacing: AppTheme.space1)`. These are `double` values.

#### Step 4.2.3: Replace ContractorEditorWidget border radius

```
hardcoded 12 → AppTheme.radiusMedium (which is 12 — no visual change, just tokenized)
hardcoded 4  → AppTheme.radiusSmall (changes from 4 to 8 — deliberate per spec)
```

#### Step 4.2.4: Replace ContractorSummaryWidget mixed arithmetic

Find instances of `space2 + space1`, `space1 + 2`, `space1 / 2` and replace with clean token references:

```
space2 + space1 (8+4=12)    → AppTheme.space3 (12)
space1 + 2 (4+2=6)          → 6.0 (no exact token, keep as literal OR use space2-2)
space1 / 2 (4/2=2)          → 2.0 (sub-token, keep as literal)
```

NOTE: For values without exact token matches, prefer the nearest token if visually acceptable, or keep the literal with a comment explaining why no token fits. The goal is "zero hardcoded font sizes" per the spec — spacing literals without tokens are acceptable.

#### Step 4.2.5: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`
Expected: No functional changes

---

## Phase 5: Rename + Cleanup

### Sub-phase 5.1: Rename "Materials Used" to "Pay Items Used"

**Files:**
- Modify: `lib/features/entries/presentation/widgets/entry_quantities_section.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 5.1.1: Replace header text

Search for the string `'Materials Used'` (or `"Materials Used"`) in `entry_quantities_section.dart` and replace with `'Pay Items Used'`.

```dart
// FROM SPEC: "UI reads 'Pay Items Used' not 'Materials Used'"
```

NOTE: There may be multiple occurrences (header, empty state text, tooltips). Replace ALL of them. Also search other files for "Materials Used" that reference this section — there may be references in test files or navigation labels.

#### Step 5.1.2: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`
Expected: Any test asserting "Materials Used" text will fail — note for Phase 6

---

### Sub-phase 5.2: Delete Dead Code

**Files:**
- Delete: `lib/features/entries/presentation/widgets/entry_safety_section.dart`
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart`
- Modify: `lib/features/toolbox/presentation/screens/mdot_hub_screen.dart:680-688`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 5.2.1: Delete entry_safety_section.dart

FROM SPEC: "EntrySafetySection (entire file entry_safety_section.dart)" is dead code.

Delete the file entirely. Then search for any imports of this file and remove them:

```dart
// Search for: import '...entry_safety_section.dart'
// Remove any import lines found
```

#### Step 5.2.2: Remove dead methods from entry_editor_screen.dart

Verify these methods no longer exist (they should have been removed in Phase 2, but confirm):

- `_buildCreateSections()` — replaced by `_buildSections()`
- `_buildEditSections()` — replaced by `_buildSections()`
- `_persistCreateEntry()` — replaced by unified save
- `_saveDraft()` — replaced by unified save
- `_extrasController` standalone field (line 115) — replaced by controller in EntryEditingController

If any remain, remove them now.

#### Step 5.2.3: Remove transient InspectorForm fallback from MdotHubScreen

In `mdot_hub_screen.dart` (lines 680-688), replace the `firstWhere` with `orElse` fallback:

```dart
// BEFORE:
final form = provider.forms.firstWhere(
  (f) => f.id == 'mdot_0582b' || f.name.toLowerCase().contains('0582'),
  orElse: () => InspectorForm(
    id: 'mdot_0582b',
    name: 'MDOT 0582B',
    templatePath: FormPdfService.mdot0582bTemplatePath,
    isBuiltin: true,
  ),
);

// AFTER:
// WHY: The 0582B form is now seeded at startup, so the transient fallback is dead code.
// FROM SPEC: "Transient InspectorForm fallback in mdot_hub_screen.dart:682-687"
final form = provider.forms.firstWhereOrNull(
  (f) => f.id == 'mdot_0582b' || f.name.toLowerCase().contains('0582'),
);
if (form == null) {
  // This should never happen after startup seeding, but handle gracefully
  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(content: Text('0582B form not found. Please restart the app.')),
  );
  return;
}
```

NOTE: Check if `firstWhereOrNull` is available (it's from `package:collection`). If not imported, add the import or use a try-catch pattern instead.

NOTE: Check what happens after this `form` variable is used — there may be navigation or form opening logic that needs the non-null `form`. Ensure the early return handles the control flow correctly.

#### Step 5.2.4: Remove standalone _extrasController

In `entry_editor_screen.dart`, find and remove:

```dart
final _extrasController = TextEditingController();
```

And its corresponding `dispose()` call. This is replaced by `_editingController.extrasOverrunsController`.

Also search for any references to `_extrasController` in the file and replace with `_editingController.extrasOverrunsController`.

#### Step 5.2.5: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`
Expected: Compilation succeeds, some tests may fail due to removed widgets

---

## Phase 6: Test Updates

### Sub-phase 6.1: Update Entry Editor Tests

**Files:**
- Modify: `test/features/entries/presentation/screens/entry_editor_screen_test.dart`
- Modify: `test/features/entries/presentation/screens/entry_editor_report_test.dart`

**Agent**: `qa-testing-agent`

#### Step 6.1.1: Audit test failures

Run: `pwsh -Command "flutter test test/features/entries/ 2>&1"`

Collect all test failures. They will likely fall into these categories:
1. Tests referencing `isCreateMode` or create-mode-specific widgets
2. Tests referencing `EntryActionBar` with old params (`isCreateMode`, `onSaveDraft`, `onSubmit`)
3. Tests referencing `EntrySafetySection` (deleted)
4. Tests asserting "Materials Used" text (renamed)
5. Tests expecting separate create vs edit navigation flows

#### Step 6.1.2: Fix create-mode test references

For tests that set up a "create mode" scenario (no entryId), update them to:
- Mock the `DailyEntryRepository.create()` call for draft creation
- Mock `DailyEntryProvider.getByDate()` to return empty list (so draft is created)
- Expect the unified editor screen with all 9 sections

#### Step 6.1.3: Fix EntryActionBar test references

Update any test that constructs `EntryActionBar` with removed params:
- Remove `isCreateMode:` param
- Remove `onSaveDraft:` param
- Remove `onSubmit:` param

#### Step 6.1.4: Fix EntrySafetySection references

Remove or replace any tests that import or reference `EntrySafetySection`. The safety fields are now part of `_EditableSafetyCard` (inline in the entry editor).

#### Step 6.1.5: Fix "Materials Used" assertions

Replace `'Materials Used'` with `'Pay Items Used'` in test assertions.

#### Step 6.1.6: Add test for "Copy from last entry"

Add a test that verifies:
1. Safety card shows "Copy from last entry" button
2. Tapping it fills empty fields from mock data
3. Already-filled fields are NOT overwritten
4. Toast shows source date

```dart
testWidgets('Copy from last entry fills only empty safety fields', (tester) async {
  // Setup: mock repository to return safety fields
  // Pre-fill one field (siteSafety) so it should NOT be overwritten
  // Tap "Copy from last entry"
  // Assert: pre-filled field unchanged, other 4 fields populated
  // Assert: SnackBar with source date shown
});
```

NOTE: Match the test setup pattern used in existing tests — check how providers and repositories are mocked, how the screen is pumped, etc.

#### Step 6.1.7: Add test for extrasOverruns persistence

Add a test that verifies:
1. Enter text in extrasOverruns field
2. Save the entry
3. Verify the saved entry has extrasOverruns value

#### Step 6.1.8: Add test for draft discard on back

Add a test that verifies:
1. Navigate to create entry (creates draft)
2. Don't enter any data
3. Press back
4. Verify discard dialog appears
5. Tap "Discard" → verify draft is deleted

#### Step 6.1.9: Final verification

Run: `pwsh -Command "flutter test test/features/entries/"`
Expected: All tests pass

Run: `pwsh -Command "flutter analyze"`
Expected: No new analysis issues
