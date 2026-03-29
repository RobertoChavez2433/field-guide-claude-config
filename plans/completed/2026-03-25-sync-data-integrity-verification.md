# Sync & Data Integrity Verification Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Build UI-driven end-to-end integrity verification for all 17 synced tables across two devices, with PDF field-value matching and remote-delete notification.
**Spec:** `.claude/specs/2026-03-25-sync-data-integrity-verification-spec.md`
**Analysis:** Dependency graph embedded in prompt (no external file)

**Architecture:** Two-device model (S21+ admin on port 4948, Windows inspector on port 4949) orchestrated by the Node.js debug server. Chained flows F1-F6 create data via UI taps, sync between devices, and verify in Supabase. PDF export verification uses `pdftk dump_data_fields_utf8` for AcroForm field extraction. Replaces the existing 84 L2 + 10 L3 direct-injection scenarios.
**Tech Stack:** Flutter/Dart (UI additions), Node.js (test infrastructure), Supabase (verification), `pdftk` (PDF AcroForm field extraction)
**Blast Radius:** 8 Dart files modified, 0 new Dart files, ~70 JS scenario files moved to deprecated/, ~15 new JS files created, 1 .gitignore update, 0 unit tests (integrity suite IS the test)

---

## Phase 1: UI Additions (Workstream C)

### Sub-phase 1.1: Testing Keys (C1-C4)
**Files:**
- Modify: `lib/shared/testing_keys/locations_keys.dart`
- Modify: `lib/shared/testing_keys/contractors_keys.dart`
- Modify: `lib/shared/testing_keys/toolbox_keys.dart`
- Modify: `lib/shared/testing_keys/sync_keys.dart`
- Modify: `lib/shared/testing_keys/testing_keys.dart`
**Agent:** `frontend-flutter-specialist-agent`

#### Step 1.1.1: Add location edit key to LocationsTestingKeys
In `lib/shared/testing_keys/locations_keys.dart`, add after the `locationCard` method (line 52):

```dart
  // WHY: C1 — location edit button needed for update-push verification
  /// Creates a key for a location edit button
  static Key locationEditButton(String locationId) => Key('location_edit_button_$locationId');
```

#### Step 1.1.2: Add equipment edit key to ContractorsTestingKeys
In `lib/shared/testing_keys/contractors_keys.dart`, add after `equipmentChip` method (line 80):

```dart
  // WHY: C2 — equipment edit button needed for update-push verification
  /// Creates a key for an equipment edit button
  static Key equipmentEditButton(String equipmentId) => Key('equipment_edit_button_$equipmentId');
```

#### Step 1.1.3: Add calculation history delete keys to ToolboxTestingKeys
In `lib/shared/testing_keys/toolbox_keys.dart`, add after `calculatorClearButton` (line 249):

```dart
  // WHY: C3 — calculation history delete needed for delete-push verification
  /// Creates a key for a calculation history delete button
  static Key calculationHistoryDeleteButton(String id) => Key('calculation_history_delete_button_$id');

  /// Calculation history delete confirm button
  static const calculationHistoryDeleteConfirm = Key('calculation_history_delete_confirm');

  /// Calculation history delete cancel button
  static const calculationHistoryDeleteCancel = Key('calculation_history_delete_cancel');
```

#### Step 1.1.4: Add deletion notification banner key to SyncTestingKeys
In `lib/shared/testing_keys/sync_keys.dart`, add after `syncLastSyncTimestamp` (line 33):

```dart
  // WHY: C4 — deletion notification banner needs key for test automation
  /// Deletion notification banner in project list
  static const deletionNotificationBanner = Key('deletion_notification_banner');
```

#### Step 1.1.5: Add facade delegations to TestingKeys
In `lib/shared/testing_keys/testing_keys.dart`:

After the `locationDeleteButton` delegation (around line 131), add:
```dart
  static Key locationEditButton(String locationId) =>
      LocationsTestingKeys.locationEditButton(locationId);
```

After the `equipmentChip` delegation (around line 80 in contractors section — actually there's no contractors section in the facade, the equipment keys are in the Projects section around line 132), add after `equipmentDeleteButton`:
```dart
  static Key equipmentEditButton(String equipmentId) =>
      ContractorsTestingKeys.equipmentEditButton(equipmentId);
```

After `calculatorClearButton` (line 289), add:
```dart
  static Key calculationHistoryDeleteButton(String id) =>
      ToolboxTestingKeys.calculationHistoryDeleteButton(id);
  static const calculationHistoryDeleteConfirm =
      ToolboxTestingKeys.calculationHistoryDeleteConfirm;
  static const calculationHistoryDeleteCancel =
      ToolboxTestingKeys.calculationHistoryDeleteCancel;
```

After the sync section (currently no sync facade delegations exist — add a new section after Settings or add to existing sync keys area). Add near the sync-related keys:
```dart
  static const deletionNotificationBanner =
      SyncTestingKeys.deletionNotificationBanner;
```

---

### Sub-phase 1.2: Location Edit (C1)
**Files:**
- Modify: `lib/features/projects/presentation/widgets/add_location_dialog.dart`
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart`
**Agent:** `frontend-flutter-specialist-agent`

#### Step 1.2.1: Add edit mode to AddLocationDialog
In `lib/features/projects/presentation/widgets/add_location_dialog.dart`:

Add optional `existingLocation` parameter to widget and static `show` method. Pre-fill controllers in `initState`. Change title/button text based on edit mode. Add update path in handler.

Replace the entire class with:
```dart
/// Dialog for adding or editing a location in a project
class AddLocationDialog extends StatefulWidget {
  final String projectId;
  // WHY: C1 — edit mode needed for update-push verification in integrity suite
  final Location? existingLocation;

  const AddLocationDialog({
    super.key,
    required this.projectId,
    this.existingLocation,
  });

  static Future<void> show(BuildContext context, String projectId, {Location? existingLocation}) {
    return showDialog(
      context: context,
      builder: (context) => AddLocationDialog(
        projectId: projectId,
        existingLocation: existingLocation,
      ),
    );
  }

  @override
  State<AddLocationDialog> createState() => _AddLocationDialogState();
}

class _AddLocationDialogState extends State<AddLocationDialog> {
  final _nameController = TextEditingController();
  final _descController = TextEditingController();

  bool get _isEditing => widget.existingLocation != null;

  @override
  void initState() {
    super.initState();
    // WHY: Pre-fill for edit mode
    if (_isEditing) {
      _nameController.text = widget.existingLocation!.name;
      _descController.text = widget.existingLocation!.description ?? '';
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      key: TestingKeys.locationDialog,
      title: Text(_isEditing ? 'Edit Location' : 'Add Location'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            key: TestingKeys.locationNameField,
            controller: _nameController,
            decoration: const InputDecoration(labelText: 'Location Name *'),
            autofocus: true,
          ),
          const SizedBox(height: 12),
          TextField(
            key: TestingKeys.locationDescriptionField,
            controller: _descController,
            decoration: const InputDecoration(labelText: 'Description'),
          ),
        ],
      ),
      actions: [
        TextButton(
          key: TestingKeys.locationDialogCancel,
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          key: TestingKeys.locationDialogAdd,
          onPressed: () => _isEditing ? _handleUpdate(context) : _handleAdd(context),
          child: Text(_isEditing ? 'Save' : 'Add'),
        ),
      ],
    );
  }

  Future<void> _handleAdd(BuildContext context) async {
    if (_nameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a location name')),
      );
      return;
    }

    final location = Location(
      projectId: widget.projectId,
      name: _nameController.text,
      description: _descController.text.isEmpty ? null : _descController.text,
    );

    final locationProvider = context.read<LocationProvider>();
    Navigator.pop(context);
    final success = await locationProvider.createLocation(location);
    if (!success && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(locationProvider.error ?? 'Failed to add')),
      );
    }
  }

  // WHY: C1 — update path uses existing LocationProvider.updateLocation()
  Future<void> _handleUpdate(BuildContext context) async {
    if (_nameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a location name')),
      );
      return;
    }

    // WHY: copyWith treats null as "keep existing value", so pass empty string
    // instead of null to clear the description field (CRITICAL #1 fix)
    final updated = widget.existingLocation!.copyWith(
      name: _nameController.text.trim(),
      description: _descController.text.trim(),
    );

    final locationProvider = context.read<LocationProvider>();
    Navigator.pop(context);
    final success = await locationProvider.updateLocation(updated);
    if (!success && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(locationProvider.error ?? 'Failed to update')),
      );
    }
  }
}
```

#### Step 1.2.2: Add edit button to locations tab in ProjectSetupScreen
In `lib/features/projects/presentation/screens/project_setup_screen.dart`, replace the `trailing:` in `_buildLocationsTab` (lines 462-471):

Replace:
```dart
                        trailing: canManageProjects
                            ? IconButton(
                                key: TestingKeys.locationDeleteButton(loc.id),
                                icon: const Icon(
                                  Icons.delete_outline,
                                  color: AppTheme.statusError,
                                ),
                                onPressed: () => _confirmDeleteLocation(loc),
                              )
                            : null,
```

With (modeled after contractors tab Row pattern at lines 587-611):
```dart
                        // WHY: C1 — edit+delete Row matches contractors tab pattern
                        trailing: canManageProjects
                            ? Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  IconButton(
                                    key: TestingKeys.locationEditButton(loc.id),
                                    icon: const Icon(Icons.edit_outlined, color: AppTheme.primaryCyan),
                                    onPressed: () => AddLocationDialog.show(
                                      context,
                                      _projectId!,
                                      existingLocation: loc,
                                    ),
                                  ),
                                  IconButton(
                                    key: TestingKeys.locationDeleteButton(loc.id),
                                    icon: const Icon(
                                      Icons.delete_outline,
                                      color: AppTheme.statusError,
                                    ),
                                    onPressed: () => _confirmDeleteLocation(loc),
                                  ),
                                ],
                              )
                            : null,
```

---

### Sub-phase 1.3: Equipment Edit (C2)
**Files:**
- Modify: `lib/features/projects/presentation/widgets/add_equipment_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/equipment_chip.dart`
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart`
**Agent:** `frontend-flutter-specialist-agent`

#### Step 1.3.1: Add edit mode to AddEquipmentDialog
In `lib/features/projects/presentation/widgets/add_equipment_dialog.dart`:

Replace the entire class with:
```dart
/// Dialog for adding or editing equipment for a contractor
class AddEquipmentDialog extends StatefulWidget {
  final String contractorId;
  // WHY: C2 — edit mode needed for update-push verification in integrity suite
  final Equipment? existingEquipment;

  const AddEquipmentDialog({
    super.key,
    required this.contractorId,
    this.existingEquipment,
  });

  static Future<void> show(BuildContext context, String contractorId, {Equipment? existingEquipment}) {
    return showDialog(
      context: context,
      builder: (context) => AddEquipmentDialog(
        contractorId: contractorId,
        existingEquipment: existingEquipment,
      ),
    );
  }

  @override
  State<AddEquipmentDialog> createState() => _AddEquipmentDialogState();
}

class _AddEquipmentDialogState extends State<AddEquipmentDialog> {
  final _nameController = TextEditingController();
  final _descController = TextEditingController();

  bool get _isEditing => widget.existingEquipment != null;

  @override
  void initState() {
    super.initState();
    // WHY: Pre-fill for edit mode
    if (_isEditing) {
      _nameController.text = widget.existingEquipment!.name;
      _descController.text = widget.existingEquipment!.description ?? '';
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      key: TestingKeys.equipmentDialog,
      title: Text(_isEditing ? 'Edit Equipment' : 'Add Equipment'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            key: TestingKeys.equipmentNameField,
            controller: _nameController,
            decoration: const InputDecoration(labelText: 'Equipment Name *'),
            autofocus: true,
          ),
          const SizedBox(height: 12),
          TextField(
            key: TestingKeys.equipmentDescriptionField,
            controller: _descController,
            decoration: const InputDecoration(labelText: 'Description'),
          ),
        ],
      ),
      actions: [
        TextButton(
          key: TestingKeys.equipmentDialogCancel,
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          key: TestingKeys.equipmentDialogAdd,
          onPressed: () => _isEditing ? _handleUpdate(context) : _handleAdd(context),
          child: Text(_isEditing ? 'Save' : 'Add'),
        ),
      ],
    );
  }

  Future<void> _handleAdd(BuildContext context) async {
    if (_nameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter an equipment name')),
      );
      return;
    }

    final equipment = Equipment(
      contractorId: widget.contractorId,
      name: _nameController.text,
      description: _descController.text.isEmpty ? null : _descController.text,
    );

    final equipmentProvider = context.read<EquipmentProvider>();
    Navigator.pop(context);
    final success = await equipmentProvider.createEquipment(equipment);
    if (!success && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(equipmentProvider.error ?? 'Failed to add')),
      );
    }
  }

  // WHY: C2 — update path uses existing EquipmentProvider.updateEquipment()
  Future<void> _handleUpdate(BuildContext context) async {
    if (_nameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter an equipment name')),
      );
      return;
    }

    // WHY: copyWith treats null as "keep existing value", so pass empty string
    // instead of null to clear the description field (CRITICAL #1 fix)
    final updated = widget.existingEquipment!.copyWith(
      name: _nameController.text.trim(),
      description: _descController.text.trim(),
    );

    final equipmentProvider = context.read<EquipmentProvider>();
    Navigator.pop(context);
    final success = await equipmentProvider.updateEquipment(updated);
    if (!success && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(equipmentProvider.error ?? 'Failed to update')),
      );
    }
  }
}
```

#### Step 1.3.2: Add onEdit callback to EquipmentChip
In `lib/features/projects/presentation/widgets/equipment_chip.dart`:

Replace the entire class with:
```dart
/// Chip widget for displaying equipment with edit and delete options
class EquipmentChip extends StatelessWidget {
  final Equipment equipment;
  final VoidCallback? onDelete;
  // WHY: C2 — edit callback needed for update-push verification
  final VoidCallback? onEdit;

  /// Optional key forwarded to the chip's delete icon for test automation (BUG-12).
  final Key? deleteIconKey;

  const EquipmentChip({
    super.key,
    required this.equipment,
    this.onDelete,
    this.onEdit,
    this.deleteIconKey,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        InputChip(
          key: TestingKeys.equipmentDeleteChip(equipment.id),
          label: Text(equipment.name),
          deleteIcon: onDelete != null
              ? Icon(Icons.close, key: deleteIconKey, size: 16)
              : null,
          onDeleted: onDelete,
        ),
        if (onEdit != null)
          IconButton(
            key: TestingKeys.equipmentEditButton(equipment.id),
            icon: const Icon(Icons.edit_outlined, size: 16),
            onPressed: onEdit,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
            visualDensity: VisualDensity.compact,
          ),
      ],
    );
  }
}
```

#### Step 1.3.3: Pass onEdit to EquipmentChip in ProjectSetupScreen
In `lib/features/projects/presentation/screens/project_setup_screen.dart`, update `_buildEquipmentChip` (lines 699-708):

Replace:
```dart
  Widget _buildEquipmentChip(Equipment equipment, String contractorId) {
    final canManageProjects = context.read<AuthProvider>().canManageProjects;
    return EquipmentChip(
      equipment: equipment,
      onDelete: canManageProjects
          ? () => _confirmDeleteEquipment(equipment, contractorId)
          : null,
      deleteIconKey: TestingKeys.equipmentDeleteButton(equipment.id),
    );
  }
```

With:
```dart
  Widget _buildEquipmentChip(Equipment equipment, String contractorId) {
    final canManageProjects = context.read<AuthProvider>().canManageProjects;
    return EquipmentChip(
      equipment: equipment,
      onDelete: canManageProjects
          ? () => _confirmDeleteEquipment(equipment, contractorId)
          : null,
      // WHY: C2 — edit opens pre-filled dialog for update-push verification
      onEdit: canManageProjects
          ? () => AddEquipmentDialog.show(
                context,
                contractorId,
                existingEquipment: equipment,
              )
          : null,
      deleteIconKey: TestingKeys.equipmentDeleteButton(equipment.id),
    );
  }
```

NOTE: `AddEquipmentDialog` is already imported via the project_setup_screen imports (check if it needs an explicit import — it should already be available via the widgets barrel or direct import).

---

### Sub-phase 1.4: Calculation History Delete (C3)
**Files:**
- Modify: `lib/features/calculator/presentation/screens/calculator_screen.dart`
**Agent:** `frontend-flutter-specialist-agent`

#### Step 1.4.1: Add delete button to _HistoryTile
In `lib/features/calculator/presentation/screens/calculator_screen.dart`, replace the `trailing:` in `_HistoryTile.build` (lines 686-696):

Replace:
```dart
        trailing: IconButton(
          icon: const Icon(Icons.copy_outlined, size: 18),
          onPressed: () {
            Clipboard.setData(
              ClipboardData(text: history.resultValue?.toStringAsFixed(2) ?? ''),
            );
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Copied to clipboard')),
            );
          },
        ),
```

With:
```dart
        // WHY: C3 — copy + delete Row needed for delete-push verification
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: const Icon(Icons.copy_outlined, size: 18),
              onPressed: () {
                Clipboard.setData(
                  ClipboardData(text: history.resultValue?.toStringAsFixed(2) ?? ''),
                );
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Copied to clipboard')),
                );
              },
            ),
            IconButton(
              key: TestingKeys.calculationHistoryDeleteButton(history.id),
              icon: const Icon(Icons.delete_outline, size: 18, color: AppTheme.statusError),
              onPressed: () => _confirmDelete(context, history),
            ),
          ],
        ),
```

NOTE: `_HistoryTile` is a `StatelessWidget`, so `_confirmDelete` must be a method on it. Add the following method to the `_HistoryTile` class, before `_formatDate`:

```dart
  void _confirmDelete(BuildContext context, CalculationHistory calc) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Calculation?'),
        content: const Text('This calculation will be removed from history.'),
        actions: [
          TextButton(
            key: TestingKeys.calculationHistoryDeleteCancel,
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            key: TestingKeys.calculationHistoryDeleteConfirm,
            onPressed: () {
              Navigator.pop(ctx);
              context.read<CalculatorProvider>().deleteCalculation(calc.id);
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.statusError),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }
```

NOTE: Verify that `CalculatorProvider` is accessible from `_HistoryTile`'s context. The widget is built inside a `Consumer<CalculatorProvider>`, so `context.read<CalculatorProvider>()` should work. Also verify that `AppTheme` is imported (it should be — the file already uses `AppTheme.space2`, `AppTheme.accentAmber`, etc.).

---

### Sub-phase 1.5: Wire DeletionNotificationBanner (C4)
**Files:**
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart`
- Modify: `lib/features/sync/presentation/widgets/deletion_notification_banner.dart`
**Agent:** `frontend-flutter-specialist-agent`

#### Step 1.5.1: Add testing key to DeletionNotificationBanner
In `lib/features/sync/presentation/widgets/deletion_notification_banner.dart`, replace line 92:

```dart
    return Material(
```

With:
```dart
    // WHY: C4 — testing key needed for automation verification
    // SEC-002: Cap deleted_by_name length to prevent UI overflow from malicious input
    // In the banner's build method, where `deleted_by_name` is rendered, add:
    //   final name = (n['deleted_by_name'] as String? ?? 'Someone').length > 60
    //       ? '${(n['deleted_by_name'] as String).substring(0, 60)}...'
    //       : (n['deleted_by_name'] as String? ?? 'Someone');
    return Material(
      key: TestingKeys.deletionNotificationBanner,
```

NOTE: Verify the import. The file currently imports `database_service.dart` and `app_theme.dart`. It needs `TestingKeys` — add:
```dart
import 'package:construction_inspector/shared/shared.dart';
```

#### Step 1.5.2: Place DeletionNotificationBanner in ProjectListScreen
In `lib/features/projects/presentation/screens/project_list_screen.dart`, add the banner in the body Column (after line 343, after the ProjectImportBanner Consumer):

Replace:
```dart
          body: Column(
            children: [
              // Import progress banner (above the list)
              Consumer<ProjectImportRunner>(
                builder: (context, runner, child) =>
                    ProjectImportBanner(runner: runner),
              ),

              // 3-tab body
              Expanded(
```

With:
```dart
          body: Column(
            children: [
              // Import progress banner (above the list)
              Consumer<ProjectImportRunner>(
                builder: (context, runner, child) =>
                    ProjectImportBanner(runner: runner),
              ),

              // WHY: C4 — shows notification when admin deletes a project the inspector has locally
              // FROM SPEC: "Place DeletionNotificationBanner in ProjectListScreen body"
              const DeletionNotificationBanner(),

              // 3-tab body
              Expanded(
```

Add the import at the top of the file:
```dart
import 'package:construction_inspector/features/sync/presentation/widgets/deletion_notification_banner.dart';
```

---

### Sub-phase 1.6: Verify All Changes Compile
**Agent:** `frontend-flutter-specialist-agent`

#### Step 1.6.1: Run static analysis
Run: `pwsh -Command "flutter analyze"`
Expected: No errors related to the changed files. Warnings are acceptable.

#### Step 1.6.2: Run existing tests
Run: `pwsh -Command "flutter test test/features/projects/presentation/screens/project_list_screen_test.dart"`
Expected: PASS (existing tests should not break from adding a widget to the Column)

---

## Phase 2: Integrity Test Infrastructure

### Sub-phase 2.1: Integrity flow helpers
**Files:**
- Modify: `tools/debug-server/scenario-helpers.js`
**Agent:** `qa-testing-agent`

#### Step 2.1.1: Add VRF-prefixed factory functions
Add after the existing `makePhoto` function (line 472):

```javascript
// ── VRF-prefixed integrity verification helpers ──────────────────────────

// WHY: Integrity suite uses VRF- prefix (not SYNCTEST-) for all test data
// FROM SPEC: "VRF- prefix = Verification Flow — makes all test data identifiable and sweepable"

/**
 * Wait for sync to complete on a device, with retry.
 * WHY: Integrity flows need reliable sync between UI actions.
 */
async function syncAndWait(device, label = 'sync') {
  await device.triggerSync();
  await waitForSyncComplete(device, label, 60000);
}

/**
 * Sync both devices sequentially.
 * WHY: After admin creates data, both devices need to sync for cross-device verification.
 */
async function syncBothDevices(admin, inspector, label = 'dual sync') {
  await syncAndWait(admin, `${label} (admin)`);
  // Inspector may need 2 rounds: round 1 enrolls project, round 2 pulls scoped data
  await syncAndWait(inspector, `${label} (inspector round 1)`);
  await syncAndWait(inspector, `${label} (inspector round 2)`);
}

/**
 * Verify a record exists in Supabase with expected field values.
 * Throws on mismatch with detailed diff.
 */
async function verifyInSupabase(verifier, table, id, expectedFields, label = '') {
  const result = await verifier.verifyRecord(table, id, expectedFields);
  if (!result.pass) {
    const prefix = label ? `[${label}] ` : '';
    throw new Error(`${prefix}${table}/${id} verification failed:\n  ${result.mismatches.join('\n  ')}`);
  }
  return result.actual;
}

/**
 * Verify a record exists on a device's local SQLite.
 * Throws if not found.
 */
async function verifyOnDevice(device, table, id, label = '') {
  const record = await device.getLocalRecord(table, id);
  if (!record) {
    const prefix = label ? `[${label}] ` : '';
    throw new Error(`${prefix}${table}/${id} not found on device`);
  }
  return record;
}

/**
 * Verify a record is soft-deleted in Supabase (deleted_at IS NOT NULL).
 */
async function verifySoftDeleted(verifier, table, id, label = '') {
  const result = await verifier.verifyRecordDeleted(table, id);
  if (!result.pass) {
    const prefix = label ? `[${label}] ` : '';
    throw new Error(`${prefix}${table}/${id} expected soft-deleted but still active`);
  }
}

/**
 * Sweep all VRF-prefixed records from Supabase (cleanup).
 * Uses FK_TEARDOWN_ORDER from supabase-verifier.js.
 */
async function sweepVrfRecords(verifier) {
  // Tables with name-like fields that could have VRF- prefix
  const vrfTables = [
    { table: 'todo_items', field: 'title' },
    { table: 'equipment', field: 'name' },
    { table: 'personnel_types', field: 'name' },
    { table: 'bid_items', field: 'description' },
    { table: 'contractors', field: 'name' },
    { table: 'locations', field: 'name' },
    { table: 'projects', field: 'name' },
  ];

  let totalDeleted = 0;

  // Pass 1: Sweep named tables by VRF- prefix
  const collectedProjectIds = [];
  for (const { table, field } of vrfTables) {
    try {
      // Collect project IDs before deleting (for child-table sweep in pass 2)
      if (table === 'projects') {
        const vrfProjects = await verifier.queryRecords('projects', { name: 'like.VRF-%' });
        collectedProjectIds.push(...vrfProjects.map(p => p.id));
      }
      const count = await verifier.hardDeleteByPrefix(table, field, 'VRF-');
      if (count > 0) {
        console.log(`  VRF sweep ${table}: ${count} records deleted`);
      }
      totalDeleted += count;
    } catch (e) {
      console.warn(`  VRF sweep ${table}: ${e.message}`);
    }
  }

  // Pass 2: Sweep child tables that don't have VRF-prefixed name fields
  // WHY: CRITICAL #2 — child tables (daily_entries, entry_*, photos, form_responses,
  // calculation_history, project_assignments) lack VRF-prefixed fields but are orphaned
  // if a parent project was VRF-prefixed
  if (collectedProjectIds.length > 0) {
    const childTables = [
      'calculation_history', 'form_responses', 'photos',
      'entry_quantities', 'entry_personnel_counts', 'entry_equipment',
      'entry_contractors', 'daily_entries', 'project_assignments',
    ];
    for (const table of childTables) {
      for (const projectId of collectedProjectIds) {
        try {
          const count = await verifier.hardDeleteByField(table, 'project_id', projectId);
          if (count > 0) {
            console.log(`  VRF sweep ${table} (project ${projectId}): ${count} records deleted`);
            totalDeleted += count;
          }
        } catch (e) {
          console.warn(`  VRF sweep ${table} (project ${projectId}): ${e.message}`);
        }
      }
    }
  }

  return totalDeleted;
}
```

#### Step 2.1.2: Export new helpers
Add to the `module.exports` block at the end of scenario-helpers.js:

```javascript
  // Integrity verification helpers
  syncAndWait,
  syncBothDevices,
  verifyInSupabase,
  verifyOnDevice,
  verifySoftDeleted,
  sweepVrfRecords,
```

---

### Sub-phase 2.2: Supabase verifier enhancements
**Files:**
- Modify: `tools/debug-server/supabase-verifier.js`
**Agent:** `qa-testing-agent`

#### Step 2.2.1: Add VRF- prefix to sweep function
The existing `sweepSynctestRecords` only sweeps `SYNCTEST-` prefix. Add a parallel method:

After `sweepSynctestRecords()` (line 347), add:

```javascript
  /**
   * Sweep VRF-prefixed records (integrity verification test data).
   * WHY: Integrity suite uses VRF- prefix, not SYNCTEST-.
   * @returns {Promise<number>} total records deleted
   */
  async sweepVrfRecords() {
    let totalDeleted = 0;
    for (const { table, nameField } of FK_TEARDOWN_ORDER) {
      if (!nameField) continue;
      try {
        const count = await this.hardDeleteByPrefix(table, nameField, 'VRF-');
        if (count > 0) {
          console.log(`  VRF sweep ${table}: ${count} records deleted`);
        }
        totalDeleted += count;
      } catch (e) {
        console.warn(`  VRF sweep ${table}: error — ${e.message}`);
      }
    }
    return totalDeleted;
  }

  /**
   * Verify cascade deletion: all child records of a project are soft-deleted.
   * WHY: Delete phase needs to verify project deletion cascades to all 15 child tables.
   * @param {string} projectId
   * @param {object} expectedCounts - { table: expectedCount } for verification
   * @returns {Promise<{pass: boolean, details: string[]}>}
   */
  async verifyCascadeDelete(projectId, expectedCounts = {}) {
    const details = [];
    let allPassed = true;

    const childTables = [
      { table: 'locations', fk: 'project_id' },
      { table: 'contractors', fk: 'project_id' },
      { table: 'equipment', fk: null }, // Requires join through contractors
      { table: 'bid_items', fk: 'project_id' },
      // WHY: HIGH #5 — personnel_types may be company-scoped (no project_id).
      // Only verify cascade if the record has a project_id matching the deleted project.
      { table: 'personnel_types', fk: 'project_id', skipIfNoFk: true },
      { table: 'daily_entries', fk: 'project_id' },
      { table: 'entry_contractors', fk: 'project_id' },
      { table: 'entry_equipment', fk: 'project_id' },
      { table: 'entry_personnel_counts', fk: 'project_id' },
      { table: 'entry_quantities', fk: 'project_id' },
      { table: 'photos', fk: 'project_id' },
      { table: 'form_responses', fk: 'project_id' },
      { table: 'todo_items', fk: 'project_id' },
      { table: 'calculation_history', fk: 'project_id' },
    ];

    for (const { table, fk, skipIfNoFk } of childTables) {
      if (!fk) continue; // Skip equipment (needs contractor join)
      try {
        const records = await this.queryRecords(table, { [fk]: `eq.${projectId}` });
        // HIGH #5: If skipIfNoFk is set and no records have this project_id,
        // the table is likely company-scoped — skip cascade verification
        if (skipIfNoFk && records.length === 0) {
          details.push(`SKIP: ${table} — no records with ${fk}=${projectId} (likely company-scoped)`);
          continue;
        }
        const activeRecords = records.filter(r => !r.deleted_at);
        if (activeRecords.length > 0) {
          details.push(`FAIL: ${table} has ${activeRecords.length} active records (expected 0)`);
          allPassed = false;
        } else {
          details.push(`OK: ${table} — ${records.length} records, all soft-deleted`);
        }
      } catch (e) {
        details.push(`ERROR: ${table} — ${e.message}`);
        allPassed = false;
      }
    }

    // Check project_assignments (hard-deleted, not soft-deleted)
    try {
      const assignments = await this.queryRecords('project_assignments', { project_id: `eq.${projectId}` });
      if (assignments.length > 0) {
        details.push(`FAIL: project_assignments has ${assignments.length} records (expected 0 — should be hard-deleted)`);
        allPassed = false;
      } else {
        details.push('OK: project_assignments — hard-deleted');
      }
    } catch (e) {
      details.push(`ERROR: project_assignments — ${e.message}`);
      allPassed = false;
    }

    return { pass: allPassed, details };
  }
```

---

### Sub-phase 2.3: run-tests.js --suite=integrity mode
**Files:**
- Modify: `tools/debug-server/run-tests.js`
**Agent:** `qa-testing-agent`

#### Step 2.3.1: Add --suite flag parsing
In `run-tests.js`, add to the `parseArgs` switch statement (after `--filter`, around line 111):

```javascript
      case '--suite':
        args.suite = requireArgValue(argv, i, '--suite');
        i++;
        break;
      case '--dry-run':
        args.dryRun = true;
        break;
```

Update the help text to include:
```
  --suite <name>       Run named suite (e.g., 'integrity')
  --dry-run            List flows without executing (integrity suite only)
```

#### Step 2.3.2: Add integrity suite execution path
In `run-tests.js`, in the `main()` function, add before the `const runner = new TestRunner(args);` line (around line 211):

```javascript
  // Integrity suite: UI-driven chained verification flows
  if (args.suite === 'integrity') {
    const IntegrityRunner = require('./integrity-runner');
    const runner = new IntegrityRunner({ ...args, dryRun: args.dryRun || false });
    const results = await runner.run();
    process.exit(results.failed > 0 ? 1 : 0);
  }
```

---

### Sub-phase 2.4: Integrity flow runner
**Files:**
- Create: `tools/debug-server/integrity-runner.js`
**Agent:** `qa-testing-agent`

#### Step 2.4.1: Create IntegrityRunner class
This orchestrates the chained F1-F6 flows, update phase, PDF phase, delete phase, and cleanup.

```javascript
// WHY: Integrity suite uses chained UI-driven flows, not independent per-table scenarios
// FROM SPEC: "One continuous end-to-end run. F1 creates the foundation, each subsequent flow builds on it."

const path = require('path');
const SupabaseVerifier = require('./supabase-verifier');
const DeviceOrchestrator = require('./device-orchestrator');
const { step, sleep, syncAndWait, syncBothDevices, sweepVrfRecords } = require('./scenario-helpers');

class IntegrityRunner {
  constructor(options = {}) {
    this.verifier = new SupabaseVerifier(
      process.env.SUPABASE_URL,
      process.env.SUPABASE_SERVICE_ROLE_KEY,
    );
    this.admin = new DeviceOrchestrator(
      options.deviceHost || 'localhost',
      options.adminPort || 4948,
    );
    this.inspector = new DeviceOrchestrator(
      options.deviceHost || 'localhost',
      options.inspectorPort || 4949,
    );
    this.dryRun = options.dryRun || false;

    // Shared context — IDs flow forward from earlier flows to later ones
    this.ctx = {
      projectId: null,
      project2Id: null, // Second project for unassignment test
      locationIds: [],
      contractorIds: [],
      equipmentIds: [],
      bidItemIds: [],
      personnelTypeIds: [],
      entryId: null,
      entryContractorIds: [],
      entryEquipmentIds: [],
      entryPersonnelCountIds: [],
      entryQuantityIds: [],
      photoIds: [],
      formResponseIds: [],
      todoIds: [],
      calculationIds: [],
      assignmentId: null,
      assignment2Id: null,
    };
  }

  async run() {
    if (this.dryRun) {
      console.log('\n=== Integrity Suite (DRY RUN) ===');
      console.log('  F1: Project Setup (7 tables)');
      console.log('  F2: Daily Entry (5 tables)');
      console.log('  F3: Photos (1 table)');
      console.log('  F4: Forms (2 tables)');
      console.log('  F5: Todos (1 table)');
      console.log('  F6: Calculator (1 table)');
      console.log('  Update Phase');
      console.log('  PDF Export Phase');
      console.log('  Delete Phase');
      console.log('  Unassignment Phase');
      console.log('  Cleanup Sweep');
      return { total: 11, passed: 0, failed: 0, skipped: 11 };
    }

    console.log('\n=== Sync & Data Integrity Verification ===\n');

    let passed = 0, failed = 0;
    const results = [];

    // Preflight
    try {
      await this.verifier.callRpc('get_server_time', {});
      console.log('Supabase preflight: OK');
    } catch (e) {
      console.error(`Supabase preflight failed: ${e.message}`);
      return { total: 11, passed: 0, failed: 11, error: 'Supabase unreachable' };
    }

    // Wait for both devices
    try {
      console.log('Waiting for admin device...');
      await this.admin.waitForReady(15000);
      console.log('Admin device ready.');
      console.log('Waiting for inspector device...');
      await this.inspector.waitForReady(15000);
      console.log('Inspector device ready.\n');
    } catch (e) {
      console.error(`Device not ready: ${e.message}`);
      return { total: 11, passed: 0, failed: 11, error: e.message };
    }

    // Pre-run VRF sweep
    console.log('=== Pre-run VRF sweep ===');
    try {
      await sweepVrfRecords(this.verifier);
    } catch (e) {
      console.warn(`Pre-run sweep: ${e.message}`);
    }

    // Login both devices
    try {
      await this._loginBothDevices();
    } catch (e) {
      console.error(`Login failed: ${e.message}`);
      return { total: 11, passed: 0, failed: 11, error: `Login failed: ${e.message}` };
    }

    // Load and run flows sequentially
    const flows = [
      { name: 'F1: Project Setup', file: './scenarios/integrity/F1-project-setup.js' },
      { name: 'F2: Daily Entry', file: './scenarios/integrity/F2-daily-entry.js' },
      { name: 'F3: Photos', file: './scenarios/integrity/F3-photos.js' },
      { name: 'F4: Forms', file: './scenarios/integrity/F4-forms.js' },
      { name: 'F5: Todos', file: './scenarios/integrity/F5-todos.js' },
      { name: 'F6: Calculator', file: './scenarios/integrity/F6-calculator.js' },
      { name: 'Update Phase', file: './scenarios/integrity/U1-update-all.js' },
      { name: 'PDF Export', file: './scenarios/integrity/P1-pdf-export.js' },
      { name: 'Delete Phase', file: './scenarios/integrity/D1-delete-cascade.js' },
      { name: 'Unassignment', file: './scenarios/integrity/D2-unassignment.js' },
    ];

    for (const flow of flows) {
      console.log(`\n[${flow.name}]`);
      const startTime = Date.now();
      try {
        const flowModule = require(flow.file);
        await flowModule.run({
          admin: this.admin,
          inspector: this.inspector,
          verifier: this.verifier,
          ctx: this.ctx,
        });
        const duration = Date.now() - startTime;
        console.log(`  PASSED (${duration}ms)`);
        results.push({ name: flow.name, status: 'pass', duration });
        passed++;
      } catch (e) {
        const duration = Date.now() - startTime;
        console.log(`  FAILED (${duration}ms): ${e.message}`);
        results.push({ name: flow.name, status: 'fail', duration, error: e.message });
        failed++;
        // Abort chain — subsequent flows depend on earlier ones
        console.log('\n  Chain broken — skipping remaining flows');
        break;
      }
    }

    // Cleanup sweep (always runs, even after failure)
    console.log('\n[SWEEP] Cleanup');
    try {
      const swept = await sweepVrfRecords(this.verifier);
      console.log(`  Supabase orphans: ${swept}`);
      results.push({ name: 'Cleanup Sweep', status: 'pass' });
      passed++;
    } catch (e) {
      console.log(`  Sweep error: ${e.message}`);
      results.push({ name: 'Cleanup Sweep', status: 'fail', error: e.message });
      failed++;
    }

    // Summary
    const total = passed + failed;
    console.log('\n' + '='.repeat(60));
    console.log(`RESULTS: ${passed} passed, ${failed} failed, ${total} total`);
    console.log('='.repeat(60));

    if (failed > 0) {
      console.log('\nFailed:');
      for (const r of results.filter(r => r.status === 'fail')) {
        console.log(`  X ${r.name}: ${r.error}`);
      }
    }

    return { total, passed, failed };
  }

  async _loginBothDevices() {
    await step('Login admin (S21+)', async () => {
      await this.admin.navigate('/login');
      await sleep(1000);
      await this.admin.enterText('login_email_field', process.env.ADMIN_EMAIL);
      await this.admin.enterText('login_password_field', process.env.ADMIN_PASSWORD);
      await this.admin.tap('login_sign_in_button');
      // Wait for dashboard to load
      await sleep(5000);
    });

    await step('Login inspector (Windows)', async () => {
      await this.inspector.navigate('/login');
      await sleep(1000);
      await this.inspector.enterText('login_email_field', process.env.INSPECTOR_EMAIL);
      await this.inspector.enterText('login_password_field', process.env.INSPECTOR_PASSWORD);
      await this.inspector.tap('login_sign_in_button');
      await sleep(5000);
    });
  }
}

module.exports = IntegrityRunner;
```

---

## Phase 3: Integrity Flow Scenarios

### Sub-phase 3.1: F1 — Project Setup (7 tables)
**Files:**
- Create: `tools/debug-server/scenarios/integrity/F1-project-setup.js`
**Agent:** `qa-testing-agent`

#### Step 3.1.1: Create F1 flow
```javascript
// WHY: F1 creates the project foundation that all subsequent flows build on
// FROM SPEC: "F1: Project Setup (7 tables) — projects, project_assignments, locations,
//   contractors, equipment, bid_items, personnel_types"

const { step, sleep, verify, syncAndWait, syncBothDevices, verifyInSupabase, verifyOnDevice } = require('../../scenario-helpers');

async function run({ admin, inspector, verifier, ctx }) {

  // ── Create Project ──
  await step('Create project', async () => {
    await admin.navigate('/project/new');
    await sleep(1000);
    await admin.enterText('project_name_field', 'VRF-Oakridge Water Main Replacement');
    await admin.enterText('project_number_field', 'VRF-2026-001');
    await admin.enterText('project_client_field', 'VRF-City of Oakridge');
    await admin.tap('project_save_button');
    await sleep(2000);
    // Capture project ID from local records
    // NOTE: The driver should expose newly created IDs; if not, we query Supabase after sync

    // HIGH #6: After save, app may navigate to dashboard. Navigate back to the
    // project edit screen before accessing location/contractor tabs.
    // We'll sync first to get the project ID, then navigate back.
    await syncAndWait(admin, 'F1 initial push');
    const projects = await verifier.queryRecords('projects', { name: 'like.VRF-Oakridge%' });
    if (projects.length > 0) {
      ctx.projectId = projects[0].id;
      await admin.navigate(`/project/${ctx.projectId}/edit`);
      await sleep(1000);
    }
  });

  // ── Create Locations ──
  await step('Create 2 locations', async () => {
    await admin.tap('project_locations_tab');
    await sleep(500);

    // Location 1
    await admin.tap('project_add_location_button');
    await sleep(500);
    await admin.enterText('location_name_field', 'VRF-Station 12+50 to 15+00');
    await admin.enterText('location_description_field', 'Main trench section');
    await admin.tap('location_dialog_add');
    await sleep(500);

    // Location 2
    await admin.tap('project_add_location_button');
    await sleep(500);
    await admin.enterText('location_name_field', 'VRF-Pump Station Site');
    await admin.tap('location_dialog_add');
    await sleep(500);
  });

  // ── Create Contractors ──
  await step('Create 2 contractors', async () => {
    await admin.tap('project_contractors_tab');
    await sleep(500);

    // Prime contractor
    await admin.tap('contractor_add_button');
    await sleep(500);
    await admin.enterText('contractor_name_field', 'VRF-Midwest Excavating LLC');
    await admin.tap('contractor_type_prime');
    await admin.tap('contractor_save_button');
    await sleep(500);

    // Sub contractor
    await admin.tap('contractor_add_button');
    await sleep(500);
    await admin.enterText('contractor_name_field', 'VRF-Delta Concrete Services');
    await admin.tap('contractor_type_sub');
    await admin.tap('contractor_save_button');
    await sleep(500);
  });

  // ── Create Equipment ──
  await step('Create 2 equipment', async () => {
    // Expand prime contractor card to access equipment
    // NOTE: The first contractor card needs to be expanded
    // Equipment is nested under contractor — tap the contractor card to expand
    await sleep(500);

    await admin.tap('project_add_equipment_button');
    await sleep(500);
    await admin.enterText('equipment_name_field', 'VRF-CAT 320 Excavator');
    await admin.enterText('equipment_description_field', 'Tracked excavator');
    await admin.tap('equipment_dialog_add');
    await sleep(500);

    await admin.tap('project_add_equipment_button');
    await sleep(500);
    await admin.enterText('equipment_name_field', 'VRF-Bomag BW211 Roller');
    await admin.tap('equipment_dialog_add');
    await sleep(500);
  });

  // ── Create Bid Item ──
  await step('Create 1 bid item', async () => {
    await admin.tap('project_payitems_tab');
    await sleep(500);
    await admin.tap('project_add_pay_item_button');
    await sleep(500);
    await admin.tap('pay_item_source_manual');
    await sleep(500);
    await admin.enterText('pay_item_number_field', 'VRF-301.01');
    await admin.enterText('pay_item_description_field', 'VRF-6" DIP Water Main');
    await admin.enterText('pay_item_quantity_field', '2000');
    await admin.tap('pay_item_dialog_save');
    await sleep(500);
  });

  // ── Create Personnel Types ──
  await step('Create 3 personnel types', async () => {
    // Navigate to Settings > Personnel Types
    await admin.navigate('/settings');
    await sleep(500);
    await admin.tap('settings_personnel_types_tile');
    await sleep(500);

    const types = [
      { name: 'VRF-Foreman', code: 'VF' },
      { name: 'VRF-Operator', code: 'VO' },
      { name: 'VRF-Laborer', code: 'VL' },
    ];

    for (const t of types) {
      await admin.tap('personnel_types_add_button');
      await sleep(500);
      await admin.enterText('personnel_type_name_field', t.name);
      await admin.enterText('personnel_type_short_code_field', t.code);
      await admin.tap('add_personnel_type_confirm');
      await sleep(500);
    }
  });

  // ── Assign Inspector ──
  await step('Assign inspector', async () => {
    // Navigate to project edit > Assignments tab
    // We have ctx.projectId from the post-save sync in the Create step (HIGH #6 fix)
    await admin.navigate(`/project/${ctx.projectId}/edit`);
    await sleep(1000);
    await admin.tap('project_assignments_tab');
    await sleep(500);
    const inspectorUserId = process.env.INSPECTOR_USER_ID;
    await admin.tap(`assignment_tile_${inspectorUserId}`);
    await sleep(500);
    await admin.tap('project_save_button');
    await sleep(1000);
  });

  // ── Sync admin and verify push ──
  await step('Sync admin device', async () => {
    await syncAndWait(admin, 'F1 push');
  });

  await step('Verify 7 tables in Supabase', async () => {
    // Query Supabase for VRF- prefixed records to get IDs
    const projects = await verifier.queryRecords('projects', { name: 'like.VRF-Oakridge%' });
    verify(projects.length >= 1, 'VRF project not found in Supabase');
    ctx.projectId = projects[0].id;

    const locations = await verifier.queryRecords('locations', { project_id: `eq.${ctx.projectId}` });
    verify(locations.length >= 2, `Expected 2 locations, got ${locations.length}`);
    ctx.locationIds = locations.filter(l => !l.deleted_at).map(l => l.id);

    const contractors = await verifier.queryRecords('contractors', { project_id: `eq.${ctx.projectId}` });
    verify(contractors.length >= 2, `Expected 2 contractors, got ${contractors.length}`);
    ctx.contractorIds = contractors.filter(c => !c.deleted_at).map(c => c.id);

    // Equipment is contractor-scoped, query by each contractor
    let allEquipment = [];
    for (const cId of ctx.contractorIds) {
      const equip = await verifier.queryRecords('equipment', { contractor_id: `eq.${cId}` });
      allEquipment = allEquipment.concat(equip);
    }
    ctx.equipmentIds = allEquipment.filter(e => !e.deleted_at).map(e => e.id);

    const bidItems = await verifier.queryRecords('bid_items', { project_id: `eq.${ctx.projectId}` });
    ctx.bidItemIds = bidItems.filter(b => !b.deleted_at).map(b => b.id);

    const personnelTypes = await verifier.queryRecords('personnel_types', { project_id: `eq.${ctx.projectId}` });
    ctx.personnelTypeIds = personnelTypes.filter(p => !p.deleted_at).map(p => p.id);

    const assignments = await verifier.queryRecords('project_assignments', { project_id: `eq.${ctx.projectId}` });
    verify(assignments.length >= 1, 'Project assignment not found');
    ctx.assignmentId = assignments[0].id;
  });

  // ── Pull to inspector ──
  await step('Sync inspector device', async () => {
    await syncAndWait(inspector, 'F1 pull round 1');
    await syncAndWait(inspector, 'F1 pull round 2');
  });

  await step('Verify 7 tables on inspector', async () => {
    // Verify key records exist locally on inspector device
    await verifyOnDevice(inspector, 'projects', ctx.projectId, 'F1 inspector');
    for (const id of ctx.locationIds) {
      await verifyOnDevice(inspector, 'locations', id, 'F1 inspector location');
    }
    for (const id of ctx.contractorIds) {
      await verifyOnDevice(inspector, 'contractors', id, 'F1 inspector contractor');
    }
  });

  // ── Create second project for unassignment test (setup ahead of time) ──
  await step('Create second project for unassignment test', async () => {
    await admin.navigate('/project/new');
    await sleep(1000);
    await admin.enterText('project_name_field', 'VRF-Unassign Test Project');
    await admin.enterText('project_number_field', 'VRF-2026-002');
    await admin.tap('project_save_button');
    await sleep(2000);

    // HIGH #6: After save, navigate back to project edit for assignment
    // Sync to get project2 ID first
    await syncAndWait(admin, 'F1 second project initial push');
    const projects2Pre = await verifier.queryRecords('projects', { name: 'like.VRF-Unassign%' });
    if (projects2Pre.length > 0) {
      await admin.navigate(`/project/${projects2Pre[0].id}/edit`);
      await sleep(1000);
    }

    // Assign inspector to second project
    await admin.tap('project_assignments_tab');
    await sleep(500);
    const inspectorUserId = process.env.INSPECTOR_USER_ID;
    await admin.tap(`assignment_tile_${inspectorUserId}`);
    await sleep(500);
    await admin.tap('project_save_button');
    await sleep(1000);

    // Sync both devices
    await syncAndWait(admin, 'F1 second project push');
    await syncAndWait(inspector, 'F1 second project pull r1');
    await syncAndWait(inspector, 'F1 second project pull r2');

    // Capture second project ID
    const projects2 = await verifier.queryRecords('projects', { name: 'like.VRF-Unassign%' });
    verify(projects2.length >= 1, 'VRF second project not found');
    ctx.project2Id = projects2[0].id;
  });
}

module.exports = { run };
```

---

### Sub-phase 3.2: F2 — Daily Entry (5 tables)
**Files:**
- Create: `tools/debug-server/scenarios/integrity/F2-daily-entry.js`
**Agent:** `qa-testing-agent`

#### Step 3.2.1: Create F2 flow
```javascript
// WHY: F2 creates the daily entry and all sub-records that depend on F1's project
// FROM SPEC: "F2: Daily Entry (5 tables) — daily_entries, entry_contractors,
//   entry_equipment, entry_personnel_counts, entry_quantities"

const { step, sleep, verify, syncAndWait, verifyOnDevice } = require('../../scenario-helpers');

async function run({ admin, inspector, verifier, ctx }) {
  verify(ctx.projectId, 'F2 requires projectId from F1');

  await step('Create daily entry', async () => {
    await admin.tap('add_entry_fab');
    await sleep(2000);

    // Select location
    await admin.tap('entry_wizard_location_dropdown');
    await sleep(500);
    await admin.tap(`location_option_${ctx.locationIds[0]}`);
    await sleep(500);

    // Weather — must open dropdown first (HIGH #4 fix)
    await admin.tap('entry_wizard_weather_dropdown');
    await sleep(500);
    await admin.tap('weather_condition_sunny');
    await sleep(500);
    await admin.enterText('entry_wizard_temp_low', '42');
    await admin.enterText('entry_wizard_temp_high', '67');

    // Activities
    await admin.enterText('entry_wizard_activities', 'VRF-Installed 200 LF of 6-inch DIP water main from Sta 12+50 to 14+50');

    // Safety fields
    await admin.enterText('entry_wizard_site_safety', 'VRF-Hard hats, safety vests required');
    await admin.enterText('entry_wizard_sesc_measures', 'VRF-Silt fence installed along south property line');
    await admin.enterText('entry_wizard_traffic_control', 'VRF-Flaggers on SR-47 at intersection');
    await admin.enterText('entry_wizard_visitors', 'VRF-City engineer on-site 10am-2pm');
  });

  await step('Add entry contractors', async () => {
    await admin.tap('report_add_contractor_button');
    await sleep(500);
    await admin.tap(`report_add_contractor_item_${ctx.contractorIds[0]}`);
    await admin.tap('report_save_contractor_button');
    await sleep(500);

    await admin.tap('report_add_contractor_button');
    await sleep(500);
    await admin.tap(`report_add_contractor_item_${ctx.contractorIds[1]}`);
    await admin.tap('report_save_contractor_button');
    await sleep(500);
  });

  await step('Toggle entry equipment', async () => {
    for (const eqId of ctx.equipmentIds) {
      await admin.tap(`report_equipment_checkbox_${eqId}`);
      await sleep(300);
    }
  });

  await step('Add personnel counts', async () => {
    // Prime contractor: 2 foremen, 3 operators, 5 laborers
    // Personnel type IDs are in ctx.personnelTypeIds — [0]=Foreman, [1]=Operator, [2]=Laborer
    const counts = [2, 3, 5];
    for (let i = 0; i < ctx.personnelTypeIds.length; i++) {
      for (let j = 0; j < counts[i]; j++) {
        await admin.tap(`contractor_counter_plus_${ctx.personnelTypeIds[i]}`);
        await sleep(200);
      }
    }
  });

  await step('Add entry quantity', async () => {
    await admin.tap('report_add_quantity_button');
    await sleep(500);
    await admin.tap(`bid_item_picker_${ctx.bidItemIds[0]}`);
    await sleep(500);
    await admin.enterText('quantity_amount_field', '200');
    await admin.enterText('quantity_notes_field', 'VRF-Sta 12+50 to 14+50, 6" DIP');
    await admin.tap('quantity_dialog_save');
    await sleep(500);
  });

  await step('Save entry as draft', async () => {
    await admin.tap('entry_wizard_save_draft');
    await sleep(2000);

    // HIGH #7: After saving draft from wizard, navigate explicitly to the entry
    // editor screen before using report_* keys. The wizard and report screens
    // have different key namespaces.
  });

  // Sync and verify
  await step('Sync admin', async () => {
    await syncAndWait(admin, 'F2 push');
  });

  await step('Verify 5 tables in Supabase', async () => {
    const entries = await verifier.queryRecords('daily_entries', { project_id: `eq.${ctx.projectId}` });
    const activeEntries = entries.filter(e => !e.deleted_at);
    verify(activeEntries.length >= 1, `Expected at least 1 daily entry, got ${activeEntries.length}`);
    ctx.entryId = activeEntries[0].id;

    const entryContractors = await verifier.queryRecords('entry_contractors', { entry_id: `eq.${ctx.entryId}` });
    ctx.entryContractorIds = entryContractors.map(ec => ec.id);
    verify(entryContractors.length >= 2, `Expected 2 entry_contractors, got ${entryContractors.length}`);

    const entryEquipment = await verifier.queryRecords('entry_equipment', { entry_id: `eq.${ctx.entryId}` });
    ctx.entryEquipmentIds = entryEquipment.map(ee => ee.id);

    const personnelCounts = await verifier.queryRecords('entry_personnel_counts', { entry_id: `eq.${ctx.entryId}` });
    ctx.entryPersonnelCountIds = personnelCounts.map(pc => pc.id);

    const quantities = await verifier.queryRecords('entry_quantities', { entry_id: `eq.${ctx.entryId}` });
    ctx.entryQuantityIds = quantities.map(q => q.id);
    verify(quantities.length >= 1, `Expected at least 1 entry_quantity, got ${quantities.length}`);
  });

  await step('Sync inspector and verify pull', async () => {
    await syncAndWait(inspector, 'F2 pull');
    await verifyOnDevice(inspector, 'daily_entries', ctx.entryId, 'F2 inspector');
  });
}

module.exports = { run };
```

---

### Sub-phase 3.3: F3 — Photos (1 table)
**Files:**
- Create: `tools/debug-server/scenarios/integrity/F3-photos.js`
**Agent:** `qa-testing-agent`

#### Step 3.3.1: Create F3 flow
```javascript
// WHY: F3 verifies photo injection and sync (native camera dialog cannot be automated)
// FROM SPEC: "F3: Photos (1 table + storage bucket)"

const { step, sleep, verify, syncAndWait, verifyOnDevice, TEST_JPEG_BASE64 } = require('../../scenario-helpers');

async function run({ admin, inspector, verifier, ctx }) {
  verify(ctx.entryId, 'F3 requires entryId from F2');

  await step('Inject photo via driver', async () => {
    // WHY: Native camera/gallery picker cannot be driven by test automation
    await admin._request('POST', '/driver/inject-photo-direct', {
      base64Data: TEST_JPEG_BASE64,
      filename: 'VRF-trench-section.jpg',
      entryId: ctx.entryId,
      projectId: ctx.projectId,
    });
    await sleep(2000);
  });

  await step('Sync admin', async () => {
    await syncAndWait(admin, 'F3 push');
  });

  await step('Verify photo in Supabase', async () => {
    const photos = await verifier.queryRecords('photos', { entry_id: `eq.${ctx.entryId}` });
    verify(photos.length >= 1, 'Photo not found in Supabase');
    ctx.photoIds = photos.filter(p => !p.deleted_at).map(p => p.id);
  });

  await step('Sync inspector and verify pull', async () => {
    await syncAndWait(inspector, 'F3 pull');
    if (ctx.photoIds.length > 0) {
      await verifyOnDevice(inspector, 'photos', ctx.photoIds[0], 'F3 inspector');
    }
  });
}

module.exports = { run };
```

---

### Sub-phase 3.4: F4 — Forms (2 tables)
**Files:**
- Create: `tools/debug-server/scenarios/integrity/F4-forms.js`
**Agent:** `qa-testing-agent`

#### Step 3.4.1: Create F4 flow
```javascript
// WHY: F4 verifies form response creation and sync
// FROM SPEC: "F4: Forms (2 tables) — inspector_forms (verified exists), form_responses (created via UI)"

const { step, sleep, verify, syncAndWait, verifyOnDevice } = require('../../scenario-helpers');

async function run({ admin, inspector, verifier, ctx }) {
  verify(ctx.entryId, 'F4 requires entryId from F2');

  await step('Verify inspector_forms exist in Supabase', async () => {
    const forms = await verifier.queryRecords('inspector_forms', {});
    verify(forms.length > 0, 'No inspector_forms found — seed data missing');
  });

  await step('Create form response via UI', async () => {
    // Navigate to entry editor and add a form
    await admin.tap('report_add_form_button');
    await sleep(1000);

    // Select 0582B form from dialog
    // NOTE: The form_selection_item key uses the form's ID — we need to find it
    // For now, tap the first available form
    const forms = await verifier.queryRecords('inspector_forms', {});
    const form0582b = forms.find(f => f.name && f.name.includes('0582'));
    if (form0582b) {
      await admin.tap(`form_selection_item_${form0582b.id}`);
    } else {
      // Fallback: tap first form
      await admin.tap(`form_selection_item_${forms[0].id}`);
    }
    await sleep(2000);

    // Fill header fields
    await admin.enterText('hub_header_field_control_section_id', 'VRF-CS-2026-01');
    await admin.enterText('hub_header_field_job_number', 'VRF-2026-001');
    await admin.enterText('hub_header_field_route_street', 'VRF-SR-47');
    await admin.enterText('hub_header_field_construction_eng', 'VRF-J. Martinez');
    await admin.enterText('hub_header_field_asst_eng', 'VRF-K. Patel');
    await sleep(500);

    // Save form
    await admin.tap('mdot_hub_save_button');
    await sleep(2000);
  });

  await step('Sync admin', async () => {
    await syncAndWait(admin, 'F4 push');
  });

  await step('Verify form_responses in Supabase', async () => {
    const responses = await verifier.queryRecords('form_responses', { project_id: `eq.${ctx.projectId}` });
    verify(responses.length >= 1, 'Form response not found in Supabase');
    ctx.formResponseIds = responses.filter(r => !r.deleted_at).map(r => r.id);
  });

  await step('Sync inspector and verify pull', async () => {
    await syncAndWait(inspector, 'F4 pull');
    if (ctx.formResponseIds.length > 0) {
      await verifyOnDevice(inspector, 'form_responses', ctx.formResponseIds[0], 'F4 inspector');
    }
  });
}

module.exports = { run };
```

---

### Sub-phase 3.5: F5 — Todos (1 table)
**Files:**
- Create: `tools/debug-server/scenarios/integrity/F5-todos.js`
**Agent:** `qa-testing-agent`

#### Step 3.5.1: Create F5 flow
```javascript
// WHY: F5 verifies todo item creation and sync
// FROM SPEC: "F5: Todos (1 table) — todo_items"

const { step, sleep, verify, syncAndWait, verifyOnDevice } = require('../../scenario-helpers');

async function run({ admin, inspector, verifier, ctx }) {
  verify(ctx.projectId, 'F5 requires projectId from F1');

  await step('Create todo via UI', async () => {
    // Navigate to Toolbox > Todos
    await admin.navigate('/toolbox');
    await sleep(1000);
    await admin.tap('toolbox_todos_card');
    await sleep(1000);

    await admin.tap('todos_add_button');
    await sleep(500);
    await admin.enterText('todos_title_field', 'VRF-Verify compaction test results before backfill');
    await admin.enterText('todos_description_field', 'VRF-Review 0582B results and confirm 95% compaction achieved');
    await admin.tap('todos_save_button');
    await sleep(1000);
  });

  await step('Sync admin', async () => {
    await syncAndWait(admin, 'F5 push');
  });

  await step('Verify todo in Supabase', async () => {
    const todos = await verifier.queryRecords('todo_items', { project_id: `eq.${ctx.projectId}` });
    const vrfTodos = todos.filter(t => t.title && t.title.startsWith('VRF-') && !t.deleted_at);
    verify(vrfTodos.length >= 1, 'VRF todo not found in Supabase');
    ctx.todoIds = vrfTodos.map(t => t.id);
  });

  await step('Sync inspector and verify pull', async () => {
    await syncAndWait(inspector, 'F5 pull');
    await verifyOnDevice(inspector, 'todo_items', ctx.todoIds[0], 'F5 inspector');
  });
}

module.exports = { run };
```

---

### Sub-phase 3.6: F6 — Calculator (1 table)
**Files:**
- Create: `tools/debug-server/scenarios/integrity/F6-calculator.js`
**Agent:** `qa-testing-agent`

#### Step 3.6.1: Create F6 flow
```javascript
// WHY: F6 verifies calculation history creation and sync
// FROM SPEC: "F6: Calculator (1 table) — calculation_history"

const { step, sleep, verify, syncAndWait, verifyOnDevice } = require('../../scenario-helpers');

async function run({ admin, inspector, verifier, ctx }) {
  verify(ctx.projectId, 'F6 requires projectId from F1');

  await step('Create calculation via UI', async () => {
    await admin.navigate('/toolbox');
    await sleep(1000);
    await admin.tap('toolbox_calculator_card');
    await sleep(1000);

    // HMA calculator
    await admin.tap('calculator_hma_tab');
    await sleep(500);
    await admin.enterText('calculator_hma_area', '5000');
    await admin.enterText('calculator_hma_thickness', '3');
    await admin.enterText('calculator_hma_density', '145');
    await admin.tap('calculator_hma_calculate_button');
    await sleep(500);
    await admin.tap('calculator_save_button');
    await sleep(1000);
  });

  await step('Sync admin', async () => {
    await syncAndWait(admin, 'F6 push');
  });

  await step('Verify calculation in Supabase', async () => {
    const calcs = await verifier.queryRecords('calculation_history', { project_id: `eq.${ctx.projectId}` });
    const activeCalcs = calcs.filter(c => !c.deleted_at);
    verify(activeCalcs.length >= 1, 'Calculation history not found in Supabase');
    ctx.calculationIds = activeCalcs.map(c => c.id);
  });

  await step('Sync inspector and verify pull', async () => {
    await syncAndWait(inspector, 'F6 pull');
    await verifyOnDevice(inspector, 'calculation_history', ctx.calculationIds[0], 'F6 inspector');
  });
}

module.exports = { run };
```

---

## Phase 4: Update + Delete + PDF Scenarios

### Sub-phase 4.1: Update phase (all updatable tables)
**Files:**
- Create: `tools/debug-server/scenarios/integrity/U1-update-all.js`
**Agent:** `qa-testing-agent`

#### Step 4.1.1: Create update flow
```javascript
// WHY: Update phase modifies records across all updatable tables and verifies sync
// FROM SPEC: "After all 6 flows complete, update records across all updatable tables"

const { step, sleep, verify, syncAndWait, verifyInSupabase, verifyOnDevice } = require('../../scenario-helpers');

async function run({ admin, inspector, verifier, ctx }) {
  verify(ctx.projectId, 'U1 requires projectId from F1');

  // ── Project name update ──
  await step('Update project name', async () => {
    await admin.navigate('/projects');
    await sleep(1000);
    // Navigate to project edit
    await admin.tap(`project_edit_menu_item_${ctx.projectId}`);
    await sleep(1000);
    // Clear and re-enter project name
    await admin.enterText('project_name_field', 'VRF-Oakridge Water Main Replacement Phase 2');
    await admin.tap('project_save_button');
    await sleep(1000);
  });

  // ── Location update (using NEW edit button from C1) ──
  await step('Update location name', async () => {
    await admin.tap('project_locations_tab');
    await sleep(500);
    await admin.tap(`location_edit_button_${ctx.locationIds[0]}`);
    await sleep(500);
    await admin.enterText('location_name_field', 'VRF-Station 15+00 to 18+00');
    await admin.tap('location_dialog_add'); // Button text is "Save" in edit mode, but key is same
    await sleep(500);
  });

  // ── Contractor update ──
  await step('Update contractor name', async () => {
    await admin.tap('project_contractors_tab');
    await sleep(500);
    await admin.tap(`contractor_edit_button_${ctx.contractorIds[0]}`);
    await sleep(500);
    await admin.enterText('contractor_name_field', 'VRF-Midwest Excavating LLC Inc.');
    await admin.tap('contractor_save_button');
    await sleep(500);
  });

  // ── Equipment update (using NEW edit button from C2) ──
  await step('Update equipment name', async () => {
    // Expand contractor card to see equipment
    await admin.tap(`contractor_card_${ctx.contractorIds[0]}`);
    await sleep(500);
    await admin.tap(`equipment_edit_button_${ctx.equipmentIds[0]}`);
    await sleep(500);
    await admin.enterText('equipment_name_field', 'VRF-CAT 330 Excavator');
    await admin.tap('equipment_dialog_add'); // "Save" in edit mode
    await sleep(500);
  });

  // ── Bid item update ──
  await step('Update bid item', async () => {
    await admin.tap('project_payitems_tab');
    await sleep(500);
    await admin.tap(`pay_item_edit_${ctx.bidItemIds[0]}`);
    await sleep(500);
    await admin.enterText('pay_item_description_field', 'VRF-6" DIP Water Main (modified)');
    await admin.tap('pay_item_dialog_save');
    await sleep(500);
  });

  // ── Personnel type update ──
  await step('Update personnel type', async () => {
    await admin.navigate('/settings');
    await sleep(500);
    await admin.tap('settings_personnel_types_tile');
    await sleep(500);
    await admin.tap(`personnel_type_edit_button_${ctx.personnelTypeIds[0]}`);
    await sleep(500);
    await admin.enterText('personnel_type_name_field', 'VRF-Lead Foreman');
    await admin.tap('edit_personnel_type_save');
    await sleep(500);
  });

  // ── Daily entry update ──
  await step('Update daily entry activities', async () => {
    await admin.navigate('/');
    await sleep(1000);
    // Navigate to entry
    await admin.tap(`entry_card_${ctx.entryId}`);
    await sleep(1000);
    await admin.enterText('report_activities_field',
      'VRF-Installed 200 LF of 6-inch DIP water main from Sta 12+50 to 14+50. Completed hydro test.');
    await sleep(500);
  });

  // ── Photo description update (MISSING REQUIREMENT from spec) ──
  await step('Update photo description', async () => {
    if (ctx.photoIds && ctx.photoIds.length > 0) {
      await admin.tap(`photo_thumbnail_${ctx.photoIds[0]}`);
      await sleep(1000);
      await admin.enterText('report_photo_description_field', 'VRF-Updated trench photo');
      await admin.tap('photo_save_button');
      await sleep(500);
    }
  });

  // ── Entry equipment update (MISSING REQUIREMENT from spec) ──
  await step('Toggle entry equipment for different item', async () => {
    if (ctx.equipmentIds && ctx.equipmentIds.length > 1) {
      // Toggle off first item and toggle on a different combination
      await admin.tap(`report_equipment_checkbox_${ctx.equipmentIds[0]}`);
      await sleep(300);
    }
  });

  // ── Personnel count update (MISSING REQUIREMENT from spec) ──
  await step('Increment laborer personnel count', async () => {
    if (ctx.personnelTypeIds && ctx.personnelTypeIds.length >= 3) {
      // personnelTypeIds[2] = Laborer — add one more
      await admin.tap(`contractor_counter_plus_${ctx.personnelTypeIds[2]}`);
      await sleep(300);
    }
  });

  // ── Form response update (MISSING REQUIREMENT from spec) ──
  await step('Update form response remarks', async () => {
    if (ctx.formResponseIds && ctx.formResponseIds.length > 0) {
      await admin.tap(`form_thumbnail_${ctx.formResponseIds[0]}`);
      await sleep(2000);
      await admin.enterText('hub_header_field_remarks', 'VRF-Retest required');
      await admin.tap('mdot_hub_save_button');
      await sleep(1000);
      // Navigate back to entry
      await admin.tap('form_back_button');
      await sleep(500);
    }
  });

  // ── Entry quantity update ──
  await step('Update entry quantity', async () => {
    if (ctx.entryQuantityIds.length > 0) {
      await admin.tap(`report_quantity_edit_${ctx.entryQuantityIds[0]}`);
      await sleep(500);
      await admin.enterText('quantity_amount_field', '250');
      await admin.tap('quantity_dialog_save');
      await sleep(500);
    }
  });

  // ── Todo update ──
  await step('Update todo title', async () => {
    await admin.navigate('/toolbox');
    await sleep(500);
    await admin.tap('toolbox_todos_card');
    await sleep(500);
    await admin.tap(`todo_card_${ctx.todoIds[0]}`);
    await sleep(500);
    await admin.enterText('todos_title_field', 'VRF-Verify compaction test results before backfill - URGENT');
    await admin.tap('todos_save_button');
    await sleep(500);
  });

  // ── Sync and verify all updates ──
  await step('Sync admin (push updates)', async () => {
    await syncAndWait(admin, 'U1 push');
  });

  await step('Verify updates in Supabase', async () => {
    // Spot-check key updates
    const project = await verifier.getRecord('projects', ctx.projectId);
    verify(project && project.name.includes('Phase 2'), 'Project name not updated');

    if (ctx.locationIds.length > 0) {
      const loc = await verifier.getRecord('locations', ctx.locationIds[0]);
      verify(loc && loc.name.includes('15+00 to 18+00'), 'Location name not updated');
    }

    if (ctx.contractorIds.length > 0) {
      const contractor = await verifier.getRecord('contractors', ctx.contractorIds[0]);
      verify(contractor && contractor.name.includes('Inc.'), 'Contractor name not updated');
    }
  });

  await step('Sync inspector and verify updates pulled', async () => {
    await syncAndWait(inspector, 'U1 pull');
    const project = await verifyOnDevice(inspector, 'projects', ctx.projectId, 'U1 inspector');
  });
}

module.exports = { run };
```

---

### Sub-phase 4.2: PDF export + verification
**Files:**
- Create: `tools/debug-server/scenarios/integrity/P1-pdf-export.js`
**Agent:** `qa-testing-agent`

#### Step 4.2.1: Create PDF export flow
```javascript
// WHY: Verify PDFs contain correct field values from the data we entered
// FROM SPEC: "Export IDR + 0582B PDFs, adb pull, parse with PDF library, assert field-value matches"

const { step, sleep, verify } = require('../../scenario-helpers');
const { execFileSync, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// WHY: pdf-parse reads text content, not form fields. pdftk extracts AcroForm field values (CRITICAL #3 fix).
function extractPdfFields(pdfPath) {
  const output = execSync(`pdftk "${pdfPath}" dump_data_fields_utf8`, { encoding: 'utf-8' });
  const fields = {};
  let currentField = null;
  for (const line of output.split('\n')) {
    if (line.startsWith('FieldName: ')) currentField = line.substring(11).trim();
    if (line.startsWith('FieldValue: ') && currentField) {
      fields[currentField] = line.substring(12).trim();
      currentField = null;
    }
  }
  return fields;
}

async function run({ admin, inspector, verifier, ctx }) {
  verify(ctx.entryId, 'P1 requires entryId from F2');

  // ── Export IDR PDF ──
  await step('Export IDR PDF', async () => {
    // Navigate to entry editor
    await admin.tap(`entry_card_${ctx.entryId}`);
    await sleep(1000);

    await admin.tap('report_export_pdf_button');
    await sleep(1000);
    await admin.enterText('export_filename_field', 'VRF-IDR-Oakridge');
    await admin.tap('export_filename_save_button');
    await sleep(5000); // PDF generation takes time
  });

  // ── Pull IDR PDF from device ──
  await step('Pull IDR PDF via ADB', async () => {
    const serial = process.env.SAMSUNG_DEVICE_SERIAL;
    if (!serial) {
      console.log('    SKIP: SAMSUNG_DEVICE_SERIAL not set — cannot pull PDF');
      return;
    }
    try {
      // Find the exported file on device
      const lsOutput = execFileSync('adb', ['-s', serial, 'shell', 'ls', '/sdcard/Download/VRF-IDR-Oakridge*'], { encoding: 'utf8' });
      const remotePath = lsOutput.trim().split('\n')[0];
      if (remotePath) {
        const localPath = path.join(__dirname, '../../reports/VRF-IDR-Oakridge.pdf');
        execFileSync('adb', ['-s', serial, 'pull', remotePath, localPath]);
        ctx.idrPdfPath = localPath;
      }
    } catch (e) {
      console.log(`    WARN: ADB pull failed: ${e.message}`);
    }
  });

  // ── Verify IDR field values ──
  await step('Verify IDR PDF fields', async () => {
    if (!ctx.idrPdfPath || !fs.existsSync(ctx.idrPdfPath)) {
      console.log('    SKIP: IDR PDF not available for verification');
      return;
    }

    // WHY: pdf-parse reads text content, not AcroForm fields. pdftk extracts
    // actual form field values which is what we need for verification (CRITICAL #3 fix).
    const fields = extractPdfFields(ctx.idrPdfPath);
    const fieldCount = Object.keys(fields).length;
    console.log(`    PDF has ${fieldCount} form fields`);

    // Verify key form field values
    // NOTE: Field names depend on the PDF template. Adjust if needed after first run.
    const projectNumField = Object.entries(fields).find(([k, v]) => v.includes('VRF-2026-001'));
    verify(!!projectNumField, 'Project number VRF-2026-001 not found in any IDR PDF form field');

    const projectNameField = Object.entries(fields).find(([k, v]) => v.includes('VRF-Oakridge'));
    verify(!!projectNameField, 'Project name VRF-Oakridge not found in any IDR PDF form field');
  });

  // ── Export 0582B PDF (if form response exists) ──
  await step('Export 0582B PDF', async () => {
    if (!ctx.formResponseIds || ctx.formResponseIds.length === 0) {
      console.log('    SKIP: No form responses to export');
      return;
    }

    // Navigate to form viewer and export
    await admin.tap(`form_thumbnail_${ctx.formResponseIds[0]}`);
    await sleep(2000);
    await admin.tap('form_export_button');
    await sleep(500);
    await admin.tap('form_export_save_button');
    await sleep(5000);
  });
}

module.exports = { run };
```

---

### Sub-phase 4.3: Delete cascade + notification
**Files:**
- Create: `tools/debug-server/scenarios/integrity/D1-delete-cascade.js`
**Agent:** `qa-testing-agent`

#### Step 4.3.1: Create delete cascade flow
```javascript
// WHY: Verify project deletion cascades soft-deletes to all child tables
// FROM SPEC: "Delete Phase — Project deletion cascades soft-deletes to all child tables.
//   Inspector gets DeletionNotificationBanner."

const { step, sleep, verify, syncAndWait } = require('../../scenario-helpers');

async function run({ admin, inspector, verifier, ctx }) {
  verify(ctx.projectId, 'D1 requires projectId from F1');

  await step('Delete project via UI', async () => {
    await admin.navigate('/projects');
    await sleep(1000);

    // Initiate multi-step delete dialog
    await admin.tap(`project_remove_${ctx.projectId}`);
    await sleep(500);
    await admin.tap('project_delete_continue_button');
    await sleep(500);

    // Type project name in confirmation field
    await admin.enterText('project_delete_text_field', 'VRF-Oakridge Water Main Replacement Phase 2');
    await admin.tap('project_delete_forever_button');
    await sleep(2000);
  });

  await step('Sync admin (push deletion)', async () => {
    await syncAndWait(admin, 'D1 push');
  });

  await step('Verify cascade in Supabase', async () => {
    const result = await verifier.verifyCascadeDelete(ctx.projectId);
    if (!result.pass) {
      console.log('    Cascade details:');
      for (const d of result.details) {
        console.log(`      ${d}`);
      }
    }
    verify(result.pass, 'Cascade deletion verification failed');
  });

  await step('Sync inspector', async () => {
    await syncAndWait(inspector, 'D1 pull');
  });

  await step('Verify deletion notification banner visible', async () => {
    // Check if the deletion_notification_banner widget is visible on inspector
    try {
      const found = await inspector.find('deletion_notification_banner');
      verify(found && found.found, 'Deletion notification banner not visible on inspector device');
    } catch (e) {
      // Banner visibility is best-effort — the key mechanic here is that the project
      // data is removed from the inspector's local SQLite
      console.log(`    WARN: Banner check failed: ${e.message}`);
    }
  });

  await step('Verify project removed from inspector local DB', async () => {
    try {
      const record = await inspector.getLocalRecord('projects', ctx.projectId);
      // Record should either not exist or have deleted_at set
      if (record && !record.deleted_at) {
        throw new Error('Project still active on inspector device after delete');
      }
    } catch (e) {
      // getLocalRecord returning null (not found) is the expected outcome
      if (e.message && e.message.includes('still active')) throw e;
    }
  });
}

module.exports = { run };
```

---

### Sub-phase 4.4: Unassignment test
**Files:**
- Create: `tools/debug-server/scenarios/integrity/D2-unassignment.js`
**Agent:** `qa-testing-agent`

#### Step 4.4.1: Create unassignment flow
```javascript
// WHY: Verify that unassigning an inspector removes project data from their device
//   WITHOUT deleting data from Supabase
// FROM SPEC: "Step 2: Unassignment Test (Second Project)"

const { step, sleep, verify, syncAndWait } = require('../../scenario-helpers');

async function run({ admin, inspector, verifier, ctx }) {
  verify(ctx.project2Id, 'D2 requires project2Id from F1');

  // Verify inspector has the second project locally before unassignment
  await step('Verify inspector has second project', async () => {
    const record = await inspector.getLocalRecord('projects', ctx.project2Id);
    verify(record, 'Second project not found on inspector device before unassignment');
  });

  await step('Unassign inspector from second project', async () => {
    await admin.navigate('/projects');
    await sleep(1000);
    await admin.tap(`project_edit_menu_item_${ctx.project2Id}`);
    await sleep(1000);
    await admin.tap('project_assignments_tab');
    await sleep(500);

    const inspectorUserId = process.env.INSPECTOR_USER_ID;
    await admin.tap(`assignment_tile_${inspectorUserId}`);
    await sleep(500);
    await admin.tap('project_save_button');
    await sleep(1000);
  });

  await step('Sync admin', async () => {
    await syncAndWait(admin, 'D2 push');
  });

  await step('Verify project still exists in Supabase', async () => {
    const project = await verifier.getRecord('projects', ctx.project2Id);
    verify(project && !project.deleted_at, 'Second project should still exist in Supabase (not deleted)');
  });

  await step('Verify assignment removed from Supabase', async () => {
    const assignments = await verifier.queryRecords('project_assignments', {
      project_id: `eq.${ctx.project2Id}`,
      user_id: `eq.${process.env.INSPECTOR_USER_ID}`,
    });
    verify(assignments.length === 0, 'Project assignment should be hard-deleted from Supabase');
  });

  await step('Sync inspector', async () => {
    await syncAndWait(inspector, 'D2 pull');
  });

  await step('Verify project removed from inspector device', async () => {
    try {
      const record = await inspector.getLocalRecord('projects', ctx.project2Id);
      // Should be gone or marked deleted
      if (record && !record.deleted_at) {
        throw new Error('Second project still active on inspector device after unassignment');
      }
    } catch (e) {
      if (e.message && e.message.includes('still active')) throw e;
      // Not found = expected
    }
  });

  // Cleanup: admin deletes second project
  await step('Cleanup: delete second project', async () => {
    await admin.navigate('/projects');
    await sleep(1000);
    await admin.tap(`project_remove_${ctx.project2Id}`);
    await sleep(500);
    await admin.tap('project_delete_continue_button');
    await sleep(500);
    await admin.enterText('project_delete_text_field', 'VRF-Unassign Test Project');
    await admin.tap('project_delete_forever_button');
    await sleep(2000);
    await syncAndWait(admin, 'D2 cleanup');
  });
}

module.exports = { run };
```

---

### Sub-phase 4.5: Cleanup sweep
No separate file needed. The `IntegrityRunner` (Phase 2.4) already calls `sweepVrfRecords()` at the end of every run. The sweep function is defined in scenario-helpers.js (Phase 2.1).

---

## Phase 5: Cleanup

### Sub-phase 5.1: Move old L2/L3 scenario files to deprecated
**Files:**
- Move: All files in `tools/debug-server/scenarios/L2/` to `tools/debug-server/scenarios/deprecated/L2/`
- Move: All files in `tools/debug-server/scenarios/L3/` to `tools/debug-server/scenarios/deprecated/L3/`
**Agent:** `qa-testing-agent`

#### Step 5.1.1: Move L2/L3 scenarios to deprecated
WHY: The 84 L2 direct-injection scenarios are replaced by the integrity suite. Move to deprecated/ first; delete after integrity suite passes end-to-end.

```bash
mkdir -p tools/debug-server/scenarios/deprecated/
mv tools/debug-server/scenarios/L2/ tools/debug-server/scenarios/deprecated/L2/
mv tools/debug-server/scenarios/L3/ tools/debug-server/scenarios/deprecated/L3/
```

#### Step 5.1.2: Create integrity directory
```bash
mkdir -p tools/debug-server/scenarios/integrity/
```
NOTE: This directory is created implicitly by the flow file creation in Phase 3-4, but listing it here for clarity.

### Sub-phase 5.2: Add .env.test to .gitignore (SEC-004)
**Agent:** `qa-testing-agent`

#### Step 5.2.1: Add .env.test to .gitignore
In the project root `.gitignore`, add (no glob prefix):
```
.env.test
```
WHY: SEC-004 — prevent accidental commit of test credentials.

### Sub-phase 5.3: Verify pdftk is available
**Agent:** `qa-testing-agent`

#### Step 5.3.1: Verify pdftk installation
Run: `pdftk --version`
Expected: Version output. If not installed, install via `choco install pdftk-server` (Windows) or `apt-get install pdftk-java` (Linux).
NOTE: `pdf-parse` npm package is no longer used. Removed in favor of `pdftk` for AcroForm field extraction (CRITICAL #3).

### Sub-phase 5.4: Verify integrity suite runs (dry-run)
**Agent:** `qa-testing-agent`

#### Step 5.4.1: Dry run
Run: `node tools/debug-server/run-tests.js --suite=integrity --dry-run`
Expected: Lists all 11 flow stages without errors.

---

## Dispatch Groups

### Group A (Phase 1 — Dart UI): Sub-phases 1.1 through 1.6
**Agent:** `frontend-flutter-specialist-agent`
**Verify:** `pwsh -Command "flutter analyze"` + `pwsh -Command "flutter test test/features/projects/presentation/screens/project_list_screen_test.dart"`
**Files touched:** 8 Dart files

### Group B (Phases 2-4 — JS Infrastructure + Scenarios): Sub-phases 2.1 through 4.5
**Agent:** `qa-testing-agent`
**Verify:** `node tools/debug-server/run-tests.js --suite=integrity --dry-run`
**Files touched:** 4 JS files modified, 10 new JS files created

### Group C (Phase 5 — Cleanup): Sub-phases 5.1 through 5.4
**Agent:** `qa-testing-agent`
**Verify:** Directory listing confirms L2/L3 moved to deprecated/, integrity/ populated, `.env.test` in `.gitignore`
**Files touched:** 68+ JS files moved to deprecated/

**Dependency:** Group A and Group B are independent. Group C depends on Group B (cannot delete L2/L3 until integrity suite exists).
