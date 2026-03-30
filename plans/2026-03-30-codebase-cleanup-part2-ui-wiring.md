# Part 2: UI-Unreachable Feature Wiring

**Size:** L (5 phases, 10 sub-items, cross-cutting)
**Depends on:** Part 1 (dead code removal) — no file conflicts expected, can run independently.

---

## Phase 6: Wire Unreachable Screens

### Sub-phase 6.1: U1 — PersonnelTypesScreen Navigation

**Files:**
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart`
- Test: `test/features/projects/presentation/screens/project_setup_screen_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 6.1.1: Add "Manage Personnel Types" button to contractors tab

In `_buildContractorsTab()` (line 518), add a button between the contractor list and the "Add Contractor" button. Insert after the `Expanded` block (line 611) and before the `if (canManageProjects)` block (line 612).

```dart
// WHY: U1 — PersonnelTypesScreen is fully built with route /personnel-types/:projectId
// but no navigation path exists. This button provides access from the contractors tab
// where personnel types are contextually relevant.
if (canManageProjects && contractors.isNotEmpty)
  Padding(
    padding: const EdgeInsets.fromLTRB(
      AppTheme.space4,
      AppTheme.space2,
      AppTheme.space4,
      0,
    ),
    child: SizedBox(
      width: double.infinity,
      child: TextButton.icon(
        onPressed: () => context.push('/personnel-types/$_projectId'),
        icon: const Icon(Icons.people_outline),
        label: const Text('Manage Personnel Types'),
      ),
    ),
  ),
```

Insert this inside the `Column.children` list, after the existing `Expanded` widget that renders the contractor list (or empty state), and before the existing `if (canManageProjects)` "Add Contractor" `Padding` at line 612.

The exact insertion point is between lines 611 and 612 in `_buildContractorsTab()`:
```
// Line 611: closing paren of Expanded
),
// >>> INSERT NEW BUTTON HERE <<<
if (canManageProjects)
  Padding(  // existing "Add Contractor" button at line 612
```

#### Step 6.1.2: Verify

Run: `pwsh -Command "flutter test test/features/projects/presentation/screens/project_setup_screen_test.dart"`

If no existing test file, add a widget test verifying:
- The "Manage Personnel Types" button is visible when `canManageProjects == true` and contractors list is non-empty
- Tapping it calls `context.push('/personnel-types/$projectId')`
- The button is hidden when contractors list is empty

---

### Sub-phase 6.2: U2 — QuantityCalculatorScreen Navigation

**Files:**
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart`
- Test: `test/features/entries/presentation/screens/entry_editor_screen_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 6.2.1: Add calculator icon to the entry editor overflow menu

The entry editor has a `PopupMenuButton<String>` in the AppBar `actions` (line 877). Add a new `PopupMenuItem` for the quantity calculator before the delete item.

Insert at line 900 (inside `itemBuilder`), before the debug PDF item:

```dart
// WHY: U2 — QuantityCalculatorScreen is fully built with route
// /quantity-calculator/:entryId but no navigation path exists.
// The overflow menu is the natural home since calculation is an
// occasional action, not a primary workflow.
if (_entry != null)
  PopupMenuItem(
    value: 'calculator',
    child: const ListTile(
      leading: Icon(Icons.calculate_outlined),
      title: Text('Quantity Calculator'),
      contentPadding: EdgeInsets.zero,
    ),
  ),
```

Then handle the selection in `onSelected` (line 879). Add before the `if (value == 'delete')` check:

```dart
if (value == 'calculator' && _entry != null) {
  final result = await context.push<QuantityCalculatorResult>(
    '/quantity-calculator/${_entry!.id}',
  );
  // WHY: QuantityCalculatorScreen returns a QuantityCalculatorResult via Navigator.pop.
  // If the user completed a calculation, the result can be used to populate quantity fields.
  if (result != null && mounted) {
    // TODO(U2): Wire result into quantity entry field when quantity section is implemented
    SnackBarHelper.showSuccess(context, '${result.description}: ${result.value} ${result.unit}');
  }
}
```

Add the import at the top of `entry_editor_screen.dart`:
```dart
import 'package:construction_inspector/features/quantities/presentation/screens/quantity_calculator_screen.dart';
import 'package:go_router/go_router.dart';
```

Note: `go_router` may already be imported transitively — check before adding.

#### Step 6.2.2: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`

Verify:
- "Quantity Calculator" menu item appears in overflow menu when entry exists
- Tapping navigates to `/quantity-calculator/:entryId`

---

### Sub-phase 6.3: U3 — FormViewerScreen Routing

**Files:**
- Modify: `lib/features/forms/data/registries/form_screen_registry.dart`
- Modify: `lib/core/router/app_router.dart` (line 687-708)
- Test: `test/features/forms/data/registries/form_screen_registry_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 6.3.1: Register FormViewerScreen as the fallback in the router

The current `/form/:responseId` route (app_router.dart line 687) falls back to `MdotHubScreen` when the registry has no builder for the `formType`. This is incorrect — `MdotHubScreen` is 0582B-specific and should not render arbitrary form types.

Replace the fallback at line 707:
```dart
// BEFORE:
// NOTE: Fallback to MdotHubScreen for 0582B when registry not yet populated.
return MdotHubScreen(responseId: responseId);

// AFTER:
// WHY: U3 — FormViewerScreen is the generic viewer with PDF preview + auto-fill.
// It handles any form type gracefully, unlike MdotHubScreen which is 0582B-specific.
// MdotHubScreen is registered in FormScreenRegistry as 'mdot_0582b', so it's
// still reached via the registry path for 0582B forms.
return FormViewerScreen(responseId: responseId);
```

Add the import at the top of `app_router.dart`:
```dart
import 'package:construction_inspector/features/forms/presentation/screens/form_viewer_screen.dart';
```

Verify `MdotHubScreen` is registered in `FormScreenRegistry` for `mdot_0582b`. Check the seeding code:

Search for where `FormScreenRegistry.instance.register` is called. If `mdot_0582b` is not registered, add registration in the form infrastructure startup code (likely in `main.dart` or a form bootstrap file):

```dart
FormScreenRegistry.instance.register('mdot_0582b', ({
  required String formId,
  required String responseId,
  required String projectId,
}) => MdotHubScreen(responseId: responseId));
```

#### Step 6.3.2: Verify

Run: `pwsh -Command "flutter test test/features/forms/"`

Verify:
- Known form type `mdot_0582b` still routes to `MdotHubScreen` via registry
- Unknown form type falls back to `FormViewerScreen`

---

## Phase 7: Wire Export Providers to UI

### Sub-phase 7.1: U4 — EntryExportProvider "Export All Forms" Button

**Files:**
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart`
- Test: `test/features/entries/presentation/screens/entry_editor_screen_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.1.1: Add "Export All Forms" to the overflow menu

In `entry_editor_screen.dart`, the `PopupMenuButton` `itemBuilder` (line 900) already has items. Add a new entry:

```dart
// WHY: U4 — EntryExportProvider has a full stack (Provider -> UseCase -> Repository -> DB)
// but no UI button triggers it. This gives users access to batch-export all forms
// attached to an entry as PDFs.
if (_entry != null)
  const PopupMenuItem(
    value: 'export_forms',
    child: ListTile(
      leading: Icon(Icons.file_copy_outlined),
      title: Text('Export All Forms'),
      contentPadding: EdgeInsets.zero,
    ),
  ),
```

Handle in `onSelected`:
```dart
if (value == 'export_forms' && _entry != null) {
  final authProvider = context.read<AuthProvider>();
  final exportProvider = context.read<EntryExportProvider>();

  // WHY: Show progress indicator while exporting
  SnackBarHelper.showInfo(context, 'Exporting forms...');

  final paths = await exportProvider.exportAllFormsForEntry(
    _entry!.id,
    currentUserId: authProvider.userId,
  );

  if (!mounted) return;
  if (paths.isEmpty) {
    SnackBarHelper.showError(
      context,
      exportProvider.errorMessage ?? 'No forms to export',
    );
  } else {
    SnackBarHelper.showSuccess(
      context,
      'Exported ${paths.length} form(s)',
    );
    // WHY: Use the printing package's Printing.sharePdf for cross-platform sharing.
    // For multiple files, share the first and note the rest in the message.
    // TODO(U4): Consider a file list dialog for multi-file sharing UX.
  }
}
```

Add import:
```dart
import 'package:construction_inspector/features/entries/presentation/providers/entry_export_provider.dart';
```

#### Step 7.1.2: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`

Verify:
- "Export All Forms" menu item appears when entry exists
- Tapping calls `EntryExportProvider.exportAllFormsForEntry`
- Error state shows snackbar

---

### Sub-phase 7.2: U5 — FormExportProvider "Export PDF" Button

**Files:**
- Modify: `lib/features/forms/presentation/screens/mdot_hub_screen.dart`
- Test: `test/features/forms/presentation/screens/mdot_hub_screen_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.2.1: Add "Export PDF" button to MdotHubScreen app bar

In `mdot_hub_screen.dart`, the AppBar `actions` (line 796-808) currently have a preview button and a save button. Add an export button between them:

```dart
// WHY: U5 — FormExportProvider has a full stack (Provider -> UseCase -> Repository -> DB)
// but no UI button triggers exportFormToPdf(). This button generates a finalized PDF
// (not just a preview) that can be shared or saved.
if (_headerConfirmed)
  IconButton(
    onPressed: _loading || _saving ? null : _exportPdf,
    icon: const Icon(Icons.ios_share),
    tooltip: 'Export PDF',
  ),
```

Add the `_exportPdf` method in the state class, near `_previewPdf`:

```dart
Future<void> _exportPdf() async {
  if (_response == null) return;
  final exportProvider = context.read<FormExportProvider>();
  final authProvider = context.read<AuthProvider>();

  final path = await exportProvider.exportFormToPdf(
    _response!.id,
    currentUserId: authProvider.userId,
  );

  if (!mounted) return;
  if (path != null) {
    SnackBarHelper.showSuccess(context, 'PDF exported');
    // WHY: Use Printing.sharePdf for cross-platform PDF sharing
    await Printing.sharePdf(
      bytes: await File(path).readAsBytes(),
      filename: 'MDOT_0582B_${_response!.id.substring(0, 8)}.pdf',
    );
  } else {
    SnackBarHelper.showError(
      context,
      exportProvider.errorMessage ?? 'Export failed',
    );
  }
}
```

Add imports:
```dart
import 'dart:io';
import 'package:construction_inspector/features/forms/presentation/providers/form_export_provider.dart';
```

Note: `dart:io` and `printing` are already imported in this file.

#### Step 7.2.2: Verify

Run: `pwsh -Command "flutter test test/features/forms/"`

Verify:
- Export button visible when header is confirmed
- Calls `FormExportProvider.exportFormToPdf` with correct responseId
- Error handling shows snackbar

---

## Phase 8: Wire Project Fields for Form Auto-Fill

### Sub-phase 8.1: U6 — Project Header Fields (controlSectionId, routeStreet, constructionEng)

**Files:**
- Modify: `lib/features/projects/presentation/widgets/project_details_form.dart`
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart`
- Test: `test/features/projects/presentation/widgets/project_details_form_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.1.1: Add controllers to ProjectSetupScreen

In `project_setup_screen.dart`, add three new `TextEditingController` declarations after the existing controllers (line 55):

```dart
final _controlSectionIdController = TextEditingController();
final _routeStreetController = TextEditingController();
final _constructionEngController = TextEditingController();
```

Dispose them in `dispose()` (after line 208):
```dart
_controlSectionIdController.dispose();
_routeStreetController.dispose();
_constructionEngController.dispose();
```

#### Step 8.1.2: Load values in _loadProjectData

In `_loadProjectData()` (line 130), after line 140 (`_descriptionController.text = project.description ?? '';`), add:

```dart
_controlSectionIdController.text = project.controlSectionId ?? '';
_routeStreetController.text = project.routeStreet ?? '';
_constructionEngController.text = project.constructionEng ?? '';
```

#### Step 8.1.3: Save values in _saveProject

In `_saveProject()`, the `copyWith` call for editing (line 925) needs the new fields:

```dart
final updated = existing.copyWith(
  name: _nameController.text,
  projectNumber: _numberController.text,
  clientName: _clientController.text.isEmpty ? null : _clientController.text,
  description: _descriptionController.text.isEmpty ? null : _descriptionController.text,
  controlSectionId: _controlSectionIdController.text.isEmpty ? null : _controlSectionIdController.text,
  routeStreet: _routeStreetController.text.isEmpty ? null : _routeStreetController.text,
  constructionEng: _constructionEngController.text.isEmpty ? null : _constructionEngController.text,
);
```

Also update the `Project(...)` constructor call for new projects (line 962):

```dart
final project = Project(
  id: _projectId,
  name: _nameController.text,
  projectNumber: _numberController.text,
  clientName: _clientController.text.isEmpty ? null : _clientController.text,
  description: _descriptionController.text.isEmpty ? null : _descriptionController.text,
  controlSectionId: _controlSectionIdController.text.isEmpty ? null : _controlSectionIdController.text,
  routeStreet: _routeStreetController.text.isEmpty ? null : _routeStreetController.text,
  constructionEng: _constructionEngController.text.isEmpty ? null : _constructionEngController.text,
  companyId: companyId,
  createdByUserId: userId,
);
```

#### Step 8.1.4: Update ProjectDetailsForm widget

In `project_details_form.dart`, add three new controller parameters:

```dart
class ProjectDetailsForm extends StatelessWidget {
  final GlobalKey<FormState> formKey;
  final TextEditingController nameController;
  final TextEditingController numberController;
  final TextEditingController clientController;
  final TextEditingController descriptionController;
  // WHY: U6 — These fields feed form auto-fill (0582B header).
  // Without them, auto-fill always gets null for control section, route, and construction engineer.
  final TextEditingController? controlSectionIdController;
  final TextEditingController? routeStreetController;
  final TextEditingController? constructionEngController;
  final bool readOnly;
  // ...
```

Make them optional (nullable) for backward compatibility.

Add to the constructor:
```dart
const ProjectDetailsForm({
  super.key,
  required this.formKey,
  required this.nameController,
  required this.numberController,
  required this.clientController,
  required this.descriptionController,
  this.controlSectionIdController,
  this.routeStreetController,
  this.constructionEngController,
  this.readOnly = false,
});
```

Add fields after the Description field (after line 93) in the `Column.children`:

```dart
// WHY: U6 — These fields are read by MdotHubScreen auto-fill service.
// Null controllers mean these are optional — only shown when provided.
if (controlSectionIdController != null) ...[
  const SizedBox(height: AppTheme.space4),
  const Divider(),
  const SizedBox(height: AppTheme.space2),
  Text(
    'Form Auto-Fill Fields',
    style: Theme.of(context).textTheme.titleSmall,
  ),
  const SizedBox(height: AppTheme.space2),
  TextFormField(
    controller: controlSectionIdController,
    readOnly: readOnly,
    decoration: const InputDecoration(
      labelText: 'Control Section ID',
      hintText: 'e.g., 12345',
      helperText: 'Used in 0582B form header',
    ),
  ),
],
if (routeStreetController != null) ...[
  const SizedBox(height: AppTheme.space4),
  TextFormField(
    controller: routeStreetController,
    readOnly: readOnly,
    decoration: const InputDecoration(
      labelText: 'Route / Street',
      hintText: 'e.g., M-37 or Main St',
      helperText: 'Used in 0582B form header',
    ),
  ),
],
if (constructionEngController != null) ...[
  const SizedBox(height: AppTheme.space4),
  TextFormField(
    controller: constructionEngController,
    readOnly: readOnly,
    decoration: const InputDecoration(
      labelText: 'Construction Engineer',
      hintText: 'e.g., John Smith, PE',
      helperText: 'Used in 0582B form header',
    ),
  ),
],
```

#### Step 8.1.5: Pass controllers in _buildDetailsTab

In `project_setup_screen.dart`, `_buildDetailsTab()` (line 366), update the `ProjectDetailsForm` instantiation:

```dart
ProjectDetailsForm(
  formKey: _formKey,
  nameController: _nameController,
  numberController: _numberController,
  clientController: _clientController,
  descriptionController: _descriptionController,
  controlSectionIdController: _controlSectionIdController,
  routeStreetController: _routeStreetController,
  constructionEngController: _constructionEngController,
  readOnly: !canManageProjects,
),
```

#### Step 8.1.6: Verify

Run: `pwsh -Command "flutter test test/features/projects/"`

Verify:
- New fields appear in the Details tab
- Values load from existing project data
- Values save correctly on project save
- Auto-fill in MdotHubScreen receives non-null values for these fields

---

### Sub-phase 8.2: U7 — MDOT Project Mode and Fields

**Files:**
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart`
- Modify: `lib/features/projects/presentation/widgets/project_details_form.dart`
- Test: `test/features/projects/presentation/widgets/project_details_form_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.2.1: Add mode and MDOT controllers to ProjectSetupScreen

After the controllers added in U6, add:

```dart
ProjectMode _projectMode = ProjectMode.localAgency;
final _mdotContractIdController = TextEditingController();
final _mdotProjectCodeController = TextEditingController();
final _mdotCountyController = TextEditingController();
final _mdotDistrictController = TextEditingController();
```

Dispose all four in `dispose()`.

#### Step 8.2.2: Load mode and MDOT fields in _loadProjectData

After loading U6 fields:

```dart
_projectMode = project.mode;
_mdotContractIdController.text = project.mdotContractId ?? '';
_mdotProjectCodeController.text = project.mdotProjectCode ?? '';
_mdotCountyController.text = project.mdotCounty ?? '';
_mdotDistrictController.text = project.mdotDistrict ?? '';
```

#### Step 8.2.3: Save mode and MDOT fields in _saveProject

Add to both `copyWith` (edit path) and `Project(...)` (create path):

```dart
mode: _projectMode,
mdotContractId: _mdotContractIdController.text.isEmpty ? null : _mdotContractIdController.text,
mdotProjectCode: _mdotProjectCodeController.text.isEmpty ? null : _mdotProjectCodeController.text,
mdotCounty: _mdotCountyController.text.isEmpty ? null : _mdotCountyController.text,
mdotDistrict: _mdotDistrictController.text.isEmpty ? null : _mdotDistrictController.text,
```

#### Step 8.2.4: Add mode selector and MDOT fields to ProjectDetailsForm

Add parameters to `ProjectDetailsForm`:

```dart
final ProjectMode? projectMode;
final ValueChanged<ProjectMode?>? onProjectModeChanged;
final TextEditingController? mdotContractIdController;
final TextEditingController? mdotProjectCodeController;
final TextEditingController? mdotCountyController;
final TextEditingController? mdotDistrictController;
```

Import `ProjectMode`:
```dart
import 'package:construction_inspector/features/projects/data/models/project_mode.dart';
```

Add a project mode dropdown at the top of the form (before the name field):

```dart
// WHY: U7 — Project mode determines terminology (IDR vs DWR) and which
// backend the project syncs to. Without this selector, mode is always localAgency.
if (projectMode != null && onProjectModeChanged != null) ...[
  DropdownButtonFormField<ProjectMode>(
    value: projectMode,
    decoration: const InputDecoration(
      labelText: 'Project Mode',
    ),
    items: ProjectMode.values.map((mode) => DropdownMenuItem(
      value: mode,
      child: Text(mode.displayName),
    )).toList(),
    onChanged: readOnly ? null : onProjectModeChanged,
  ),
  const SizedBox(height: AppTheme.space4),
],
```

Add MDOT-specific fields that appear only when mode is `mdot`:

```dart
if (projectMode == ProjectMode.mdot) ...[
  const Divider(),
  const SizedBox(height: AppTheme.space2),
  Text(
    'MDOT Fields',
    style: Theme.of(context).textTheme.titleSmall,
  ),
  const SizedBox(height: AppTheme.space2),
  if (mdotContractIdController != null)
    TextFormField(
      controller: mdotContractIdController,
      readOnly: readOnly,
      decoration: const InputDecoration(
        labelText: 'MDOT Contract ID',
        hintText: 'AASHTOWare contract reference',
      ),
    ),
  if (mdotProjectCodeController != null) ...[
    const SizedBox(height: AppTheme.space4),
    TextFormField(
      controller: mdotProjectCodeController,
      readOnly: readOnly,
      decoration: const InputDecoration(
        labelText: 'MDOT Project Code',
      ),
    ),
  ],
  if (mdotCountyController != null) ...[
    const SizedBox(height: AppTheme.space4),
    TextFormField(
      controller: mdotCountyController,
      readOnly: readOnly,
      decoration: const InputDecoration(
        labelText: 'County',
        hintText: 'e.g., Washtenaw',
      ),
    ),
  ],
  if (mdotDistrictController != null) ...[
    const SizedBox(height: AppTheme.space4),
    TextFormField(
      controller: mdotDistrictController,
      readOnly: readOnly,
      decoration: const InputDecoration(
        labelText: 'District',
        hintText: 'e.g., University Region',
      ),
    ),
  ],
  const SizedBox(height: AppTheme.space4),
],
```

#### Step 8.2.5: Pass mode and MDOT controllers in _buildDetailsTab

Update the `ProjectDetailsForm` call:

```dart
ProjectDetailsForm(
  formKey: _formKey,
  nameController: _nameController,
  numberController: _numberController,
  clientController: _clientController,
  descriptionController: _descriptionController,
  controlSectionIdController: _controlSectionIdController,
  routeStreetController: _routeStreetController,
  constructionEngController: _constructionEngController,
  projectMode: _projectMode,
  onProjectModeChanged: (mode) {
    if (mode != null) setState(() => _projectMode = mode);
  },
  mdotContractIdController: _mdotContractIdController,
  mdotProjectCodeController: _mdotProjectCodeController,
  mdotCountyController: _mdotCountyController,
  mdotDistrictController: _mdotDistrictController,
  readOnly: !canManageProjects,
),
```

#### Step 8.2.6: Verify

Run: `pwsh -Command "flutter test test/features/projects/"`

Verify:
- Project mode dropdown appears and defaults to Local Agency
- Selecting MDOT reveals MDOT-specific fields
- Values persist through save/load cycle

---

### Sub-phase 8.3: U8 — UserCertification Read-Only View

**Files:**
- Create: `lib/features/settings/data/models/user_certification.dart`
- Create: `lib/features/settings/data/datasources/local/user_certification_local_datasource.dart`
- Modify: `lib/features/settings/presentation/screens/settings_screen.dart` (or profile screen)
- Test: `test/features/settings/data/models/user_certification_test.dart`

**Agent**: `backend-data-layer-agent` (model + datasource), then `frontend-flutter-specialist-agent` (UI)

#### Step 8.3.1: Create UserCertification model

```dart
// lib/features/settings/data/models/user_certification.dart

/// Read-only model for user certifications synced from Supabase.
/// WHY: U8 — The user_certifications table exists in SQLite (sync_engine_tables.dart)
/// but has no model class, repository, or UI. Data is managed server-side;
/// this is a view-only mirror.
class UserCertification {
  final String id;
  final String userId;
  final String certType;
  final String certNumber;
  final DateTime? expiryDate;
  final DateTime createdAt;
  final DateTime updatedAt;

  const UserCertification({
    required this.id,
    required this.userId,
    required this.certType,
    required this.certNumber,
    this.expiryDate,
    required this.createdAt,
    required this.updatedAt,
  });

  factory UserCertification.fromMap(Map<String, dynamic> map) {
    return UserCertification(
      id: map['id'] as String,
      userId: map['user_id'] as String,
      certType: map['cert_type'] as String,
      certNumber: map['cert_number'] as String,
      expiryDate: map['expiry_date'] != null
          ? DateTime.parse(map['expiry_date'] as String)
          : null,
      createdAt: DateTime.parse(map['created_at'] as String),
      updatedAt: DateTime.parse(map['updated_at'] as String),
    );
  }

  /// Human-readable certification type for display.
  String get displayType {
    switch (certType) {
      case 'nuclear_gauge':
        return 'Nuclear Gauge';
      case 'aci':
        return 'ACI Concrete';
      case 'mdot':
        return 'MDOT Certification';
      default:
        return certType.replaceAll('_', ' ');
    }
  }

  /// Whether this certification has expired.
  bool get isExpired =>
      expiryDate != null && expiryDate!.isBefore(DateTime.now());
}
```

#### Step 8.3.2: Create read-only local datasource

```dart
// lib/features/settings/data/datasources/local/user_certification_local_datasource.dart

import 'package:construction_inspector/core/database/database_service.dart';
import '../../models/user_certification.dart';

/// Read-only datasource for user_certifications table.
/// WHY: U8 — Data is synced from Supabase. Local access is read-only.
class UserCertificationLocalDatasource {
  final DatabaseService _db;

  UserCertificationLocalDatasource(this._db);

  Future<List<UserCertification>> getByUserId(String userId) async {
    final db = await _db.database;
    final rows = await db.query(
      'user_certifications',
      where: 'user_id = ?',
      whereArgs: [userId],
      orderBy: 'cert_type ASC',
    );
    return rows.map(UserCertification.fromMap).toList();
  }
}
```

#### Step 8.3.3: Add certifications display to settings/profile

Add a "My Certifications" section in the Settings screen or Edit Profile screen. The exact location depends on the current settings screen layout. Display as a simple list of cards showing cert type, number, and expiry status.

This is a lightweight read-only widget — a `FutureBuilder` that queries `UserCertificationLocalDatasource.getByUserId()` on load and displays the results.

```dart
// Widget sketch — integrate into settings or profile screen
Widget _buildCertificationsSection(String userId) {
  return FutureBuilder<List<UserCertification>>(
    future: _certDatasource.getByUserId(userId),
    builder: (context, snapshot) {
      if (!snapshot.hasData || snapshot.data!.isEmpty) {
        return const SizedBox.shrink(); // WHY: Hide section when no certs exist
      }
      final certs = snapshot.data!;
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Certifications'),
          ...certs.map((cert) => ListTile(
            title: Text(cert.displayType),
            subtitle: Text(cert.certNumber),
            trailing: cert.isExpired
                ? const Chip(label: Text('Expired'))
                : cert.expiryDate != null
                    ? Text('Exp: ${DateFormat.yMMMd().format(cert.expiryDate!)}')
                    : null,
          )),
        ],
      );
    },
  );
}
```

#### Step 8.3.4: Verify

Run: `pwsh -Command "flutter test test/features/settings/"`

Verify:
- `UserCertification.fromMap` correctly parses all fields
- Read-only datasource queries by userId
- Widget renders correctly with empty list (hidden) and populated list

---

## Phase 9: Activate AppTerminology MDOT Mode

### Sub-phase 9.1: U9 — Call AppTerminology.setMode on Project Switch

**Files:**
- Modify: `lib/features/projects/presentation/providers/project_provider.dart`
- Test: `test/features/projects/presentation/providers/project_provider_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 9.1.1: Add setMode call in setSelectedProject and selectProject

In `project_provider.dart`, the `setSelectedProject()` method (line 401) sets `_selectedProject` and persists selection. Add the terminology activation after setting the project.

Import AppTerminology:
```dart
import 'package:construction_inspector/core/config/app_terminology.dart';
```

In `setSelectedProject()` (line 409), after `_selectedProject = project;`:

```dart
// WHY: U9 — AppTerminology.setMode() exists with full dual-terminology support
// but is never called. Activating it here ensures the UI uses correct terms
// (IDR vs DWR, Bid Item vs Pay Item) based on the selected project's mode.
AppTerminology.setMode(mdotMode: project?.isMdotProject ?? false);
```

In `selectProject()` (line 372), after `_selectedProject = project;` (line 382):

```dart
AppTerminology.setMode(mdotMode: project.isMdotProject);
```

Also add the call in `clearSelectedProject()` (line 415):

```dart
AppTerminology.setMode(mdotMode: false);
```

And in `clearScreenCache()` (line 424), after `_selectedProject = null;`:

```dart
AppTerminology.setMode(mdotMode: false);
```

#### Step 9.1.2: Verify

Run: `pwsh -Command "flutter test test/features/projects/"`

Verify:
- `AppTerminology.useMdotTerms` is true when an MDOT project is selected
- `AppTerminology.useMdotTerms` is false when a local agency project is selected
- `AppTerminology.useMdotTerms` resets to false on clear

---

## Phase 10: Design System Adoption (Progressive)

### Sub-phase 10.1: U10 — Proof-of-Concept Design System Migration

**Files:**
- Modify: `lib/features/settings/presentation/screens/trash_screen.dart`
- Modify: `lib/features/todos/presentation/screens/todos_screen.dart`
- Modify: `lib/features/gallery/presentation/screens/gallery_screen.dart`
- Modify: `lib/features/entries/presentation/screens/entries_list_screen.dart`
- Modify: `lib/features/entries/presentation/screens/drafts_list_screen.dart`
- Test: `test/features/settings/presentation/screens/trash_screen_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 10.1.1: Identify priority components

The design system has 24 components in `lib/core/design_system/`. Only `AppBudgetWarningChip` and `AppToggle` are used in production code. Priority adoption order:

1. **`AppEmptyState`** — Replace inline "no items" patterns (icon + text column)
2. **`AppErrorState`** — Replace inline error displays
3. **`AppLoadingState`** — Replace `Center(child: CircularProgressIndicator())`

These three replace the most common inline patterns across screens.

#### Step 10.1.2: Migrate 5 screens as proof of concept

Target screens (chosen because they have clear empty/loading/error patterns):

**Screen 1: `trash_screen.dart`**
Replace inline empty state with `AppEmptyState`:
```dart
// BEFORE:
const Center(child: Text('Trash is empty'))

// AFTER:
const AppEmptyState(
  icon: Icons.delete_outline,
  title: 'Trash is empty',
  subtitle: 'Deleted items will appear here',
)
```

**Screen 2: `todos_screen.dart`**
Replace inline empty/loading patterns.

**Screen 3: `gallery_screen.dart`**
Replace inline empty state and loading indicator.

**Screen 4: `entries_list_screen.dart`**
Replace inline empty/loading states.

**Screen 5: `drafts_list_screen.dart`**
Replace inline empty state.

For each screen:
1. Replace `Center(child: CircularProgressIndicator())` with `const AppLoadingState()`
2. Replace inline empty state columns (icon + text) with `AppEmptyState(icon: ..., title: ..., subtitle: ...)`
3. Add import: `import 'package:construction_inspector/core/design_system/design_system.dart';`

**IMPORTANT:** Preserve all existing `TestingKeys` and `Key` annotations. The design system components accept a `key` parameter — pass the existing keys through.

#### Step 10.1.3: Document the migration pattern

Add a `// WHY: Design system migration` comment on the first replacement in each file. This establishes the pattern for ongoing adoption across the codebase.

Pattern for future migration (not in this phase):
- `AppTextField` replacing raw `TextField` — deferred (requires controller refactoring)
- `AppDialog` / `AppBottomSheet` — deferred (requires call-site audit)
- `AppSectionCard` / `AppSectionHeader` — deferred (lower priority)

#### Step 10.1.4: Verify

Run: `pwsh -Command "flutter test test/features/settings/ test/features/todos/ test/features/gallery/ test/features/entries/"`

Verify:
- All migrated screens render correctly
- Empty states show proper icon, title, and subtitle
- Loading states show spinner
- No regressions in existing tests

---

## Execution Notes

### Phase Dependencies
```
Phase 6 (wire screens) — independent, can run first
Phase 7 (wire exports) — independent of Phase 6
Phase 8 (project fields) — U6 and U7 should run together (both modify ProjectDetailsForm)
Phase 9 (terminology) — depends on Phase 8 (U7 adds mode selector; U9 reads mode)
Phase 10 (design system) — independent, can run in parallel with any phase
```

### Recommended Dispatch Groups
- **Group A** (parallel): Phase 6 (6.1, 6.2, 6.3) + Phase 10
- **Group B** (sequential): Phase 8 (8.1 then 8.2 then 8.3)
- **Group C** (after Group B): Phase 9
- **Group D** (parallel with any): Phase 7 (7.1, 7.2)

### Risk Areas
| Item | Risk | Mitigation |
|------|------|------------|
| U3 (FormViewer fallback) | Could break 0582B routing if MdotHubScreen not registered | Verify registry seeding first |
| U7 (Project mode) | Null `mode` in existing projects | Default to `localAgency` already handled in `Project.fromMap` |
| U9 (Terminology) | Global static state, not reactive | Acceptable for now — screens rebuild on project switch via Provider |
| U6/U7 (ProjectDetailsForm) | Two sub-phases modify same widget | Must run sequentially |
| U4/U5 (Export) | Use cases may not be registered in Provider tree | Verify `EntryExportProvider` and `FormExportProvider` are in `main.dart` provider list |

### No-Touch Files
These files are NOT modified in this plan:
- `lib/core/database/` — schema already has all needed columns
- `lib/features/sync/` — no sync changes needed
- `lib/features/auth/` — no auth changes needed
- `supabase/migrations/` — no migration changes needed
