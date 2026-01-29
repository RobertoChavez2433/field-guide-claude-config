# New Fixes and Implementations

## Fix: FormFillScreen Infinite Loading Spinner (0582B Form)

**Status**: Ready to implement
**Date**: 2026-01-29

### Problem
The 0582B form shows an infinite loading spinner because `FormFillScreen._performAutoFill()` tries to access repositories directly via Provider, but they're not registered - only the higher-level Providers are.

**Error**: `Could not find the correct Provider<ProjectRepository> above this FormFillScreen Widget`

### Root Cause
In `lib/features/toolbox/presentation/screens/form_fill_screen.dart` lines 269-272:
```dart
final projectRepo = context.read<ProjectRepository>();      // NOT registered
final contractorRepo = context.read<ContractorRepository>(); // NOT registered
final locationRepo = context.read<LocationRepository>();     // NOT registered
final entryRepo = context.read<DailyEntryRepository>();      // NOT registered
```

These repositories are internal to their providers and not exposed in the MultiProvider.

### Solution
Use the existing `AutoFillContextBuilder` from the Provider tree (already registered in main.dart lines 425-427) instead of creating a new instance.

### Changes

#### File: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`

**1. Remove unused imports** (lines 18-21):
```dart
// DELETE these lines:
import 'package:construction_inspector/features/projects/data/repositories/project_repository.dart';
import 'package:construction_inspector/features/contractors/data/repositories/contractor_repository.dart';
import 'package:construction_inspector/features/locations/data/repositories/location_repository.dart';
import 'package:construction_inspector/features/entries/data/repositories/daily_entry_repository.dart';
```

**2. Simplify `_performAutoFill` method** (~line 269):

Replace:
```dart
// Read all dependencies from context BEFORE any async operation
final projectRepo = context.read<ProjectRepository>();
final contractorRepo = context.read<ContractorRepository>();
final locationRepo = context.read<LocationRepository>();
final entryRepo = context.read<DailyEntryRepository>();
final fieldRegistryService = context.read<FieldRegistryService>();

// Build auto-fill context (include carry-forward based on per-form toggle)
final contextBuilder = AutoFillContextBuilder(
  prefsService: prefsService,
  projectRepository: projectRepo,
  contractorRepository: contractorRepo,
  locationRepository: locationRepo,
  entryRepository: entryRepo,
  fieldRegistryService: fieldRegistryService,
);
```

With:
```dart
// Use the pre-configured AutoFillContextBuilder from Provider tree
final contextBuilder = context.read<AutoFillContextBuilder>();
```

### Verification
1. Hot restart the app (`R` in terminal)
2. Navigate to the 0582B form
3. Confirm the form loads without infinite spinner
4. Verify auto-fill still works (fields populated from project context)
5. Run analyzer: `pwsh -Command "flutter analyze"`

---

# Entry Wizard Enhancements - Comprehensive Plan

**Created**: 2026-01-29
**Status**: COMPLETE (All PRs implemented 2026-01-29)

## Overview

Three features implemented across 4 PRs:
1. **PR 1**: Remove Test Results Section
2. **PR 2**: Add "Calculate New Quantity +" button + Enhanced Calculator
3. **PR 3**: Add "Start New Form" button
4. **PR 0** (First): Fix FormFillScreen Provider issue (above)

---

## PR 1: Remove Test Results Section

**Scope**: Small PR - Clean removal of unused feature

### Phase 1.1: Remove UI from Report Screen

**File**: `lib/features/entries/presentation/screens/report_screen.dart`

| Line | Change |
|------|--------|
| 87 | Delete `_testResultsController` declaration |
| 97 | Delete `_testResultsFocus` declaration |
| 137 | Remove `testResults:` from `_saveIfEditing()` |
| 289, 299 | Remove controller/focus disposal |
| 582-583 | Remove section call `_buildTestResultsSection(entry)` |
| 1476-1536 | Delete entire `_buildTestResultsSection()` method |

### Phase 1.2: Remove Testing Keys

**File**: `lib/shared/testing_keys/entries_keys.dart`

- Delete `reportTestResultsSection` (line 200)
- Delete `reportTestResultsField` (line 203)

### Phase 1.3: Update Data Model

**File**: `lib/features/entries/data/models/daily_entry.dart`

| Line | Change |
|------|--------|
| 17 | Remove `final String? testResults;` |
| 39 | Remove `this.testResults,` from constructor |
| 62, 82 | Remove from `copyWith()` |
| 107 | Remove `'test_results': testResults,` from `toMap()` |
| 134 | Remove from `fromMap()` |

### Phase 1.4: Database Migration

**File**: `lib/core/database/database_service.dart`

- Increment version from 18 → 19
- Add migration to remove `test_results` column (SQLite requires table recreation)

### Phase 1.5: Update Schema

**File**: `lib/core/database/schema/entry_tables.dart`

- Remove `test_results TEXT,` from CREATE TABLE (line 16)

### Phase 1.6: Update Tests

**Files**:
- `test/data/models/daily_entry_test.dart` - Remove testResults references
- `test/features/entries/presentation/screens/report_screen_test.dart`
- `test/data/repositories/daily_entry_repository_test.dart`
- `integration_test/patrol/fixtures/test_seed_data.dart`

### PR 1 Verification
```bash
pwsh -Command "flutter analyze lib/"
pwsh -Command "flutter test"
# Search for orphaned references
grep -r "testResults\|test_results" lib/ test/
```

---

## PR 2: "Calculate New Quantity +" Button

**Scope**: Medium-Large PR - New calculator functionality

### Phase 2.1: Extend Calculator Service

#### 2.1.1: Add Calculation Types

**File**: `lib/features/toolbox/data/models/calculation_history.dart`

```dart
enum CalculationType {
  hma,
  concrete,
  area,      // NEW: Length × Width = SF
  volume,    // NEW: L × W × D = CF
  linear,    // NEW: Simple measurement
}
```

#### 2.1.2: Add Input Models

**File**: `lib/features/toolbox/data/services/calculator_service.dart`

Add new classes:
```dart
class AreaInput {
  final double lengthFt;
  final double widthFt;
  // toMap(), fromMap()
}

class VolumeInput {
  final double lengthFt;
  final double widthFt;
  final double depthFt;
  // toMap(), fromMap()
}

class LinearInput {
  final double valueFt;
  final String label; // e.g., "Curb Length"
  // toMap(), fromMap()
}
```

Add calculation methods:
```dart
CalculationResult calculateArea(AreaInput input);
CalculationResult calculateVolume(VolumeInput input);
CalculationResult calculateLinear(LinearInput input);
```

#### 2.1.3: Update Provider

**File**: `lib/features/toolbox/presentation/providers/calculator_provider.dart`

Add methods for new calculation types.

### Phase 2.2: Create Quantity Calculator Screen

**New File**: `lib/features/quantities/presentation/screens/quantity_calculator_screen.dart`

```dart
class QuantityCalculatorScreen extends StatefulWidget {
  final String entryId;
  final String? bidItemId;
  final CalculationType? initialType;

  // Returns result to calling screen
}
```

**Features**:
- Tab interface: HMA | Concrete | Area | Volume | Linear
- Shows ALL measurements/inputs while calculating (visible breakdown)
- "Use Result" button returns calculated value
- Calculation history visible
- Links result to bid item selection

### Phase 2.3: Add Route

**File**: `lib/core/router/app_router.dart`

```dart
GoRoute(
  path: '/quantity-calculator/:entryId',
  name: 'quantity-calculator',
  builder: (context, state) {
    final entryId = state.pathParameters['entryId']!;
    final type = state.uri.queryParameters['type'];
    return QuantityCalculatorScreen(
      entryId: entryId,
      initialType: type != null ? CalculationType.values.byName(type) : null,
    );
  },
),
```

### Phase 2.4: Add Button to Entry Wizard

**File**: `lib/features/entries/presentation/screens/entry_wizard_screen.dart`

Location: `_buildQuantitiesSection()` around line 1872

```dart
// Existing Add Quantity button
OutlinedButton.icon(
  key: TestingKeys.quantityAddButton,
  onPressed: () => _showBidItemPicker(context),
  icon: const Icon(Icons.add),
  label: const Text('Add Quantity'),
),
const SizedBox(width: 12),
// NEW: Calculate button
OutlinedButton.icon(
  key: TestingKeys.quantityCalculateButton,
  onPressed: () => _launchQuantityCalculator(context),
  icon: const Icon(Icons.calculate),
  label: const Text('Calculate New Quantity'),
),
```

Add methods:
- `_launchQuantityCalculator()` - Shows type selection, navigates to calculator
- `_showCalculationTypeDialog()` - Dialog to select Area/Volume/Linear/HMA/Concrete
- `_addCalculatedQuantity()` - Adds result to quantities list with bid item link

### Phase 2.5: Add Testing Keys

**File**: `lib/shared/testing_keys/quantities_keys.dart`

```dart
static const quantityCalculateButton = Key('quantity_calculate_button');
static const calculationTypeDialog = Key('calculation_type_dialog');
```

**File**: `lib/shared/testing_keys/toolbox_keys.dart`

```dart
static const quantityCalculatorScreen = Key('quantity_calculator_screen');
static const quantityCalculatorUseResultButton = Key('quantity_calculator_use_result');
static const calculatorAreaTab = Key('calculator_area_tab');
static const calculatorVolumeTab = Key('calculator_volume_tab');
static const calculatorLinearTab = Key('calculator_linear_tab');
```

### PR 2 Verification
```bash
pwsh -Command "flutter analyze lib/"
pwsh -Command "flutter test"
# Manual: Test calculation flow from entry wizard
```

---

## PR 3: "Start New Form" Button + Attachments Section Enhancement

**Scope**: Medium PR - Button in Attachments section, forms display alongside photos

### Phase 3.1: Rename Section from "Photos" to "Attachments"

**File**: `lib/features/entries/presentation/screens/entry_wizard_screen.dart`

Location: `_buildPhotosSection()` at lines 1445-1532 (rename method too)

```dart
// Rename method: _buildPhotosSection() → _buildAttachmentsSection()
// Update header text: 'Photos' → 'Attachments'
// Update count badge: '(${_entryPhotos.length})' → '(${_entryPhotos.length + _entryForms.length})'
```

### Phase 3.2: Add Form State Management

**File**: `lib/features/entries/presentation/screens/entry_wizard_screen.dart`

Add state variable (near line 103):
```dart
List<FormResponse> _entryForms = [];
```

Add load method call in `_loadEntry()` (after line 545):
```dart
await _loadFormsForEntry(entryId);
```

Add method:
```dart
Future<void> _loadFormsForEntry(String entryId) async {
  final formProvider = context.read<InspectorFormProvider>();
  await formProvider.loadResponsesForEntry(entryId);
  if (mounted) {
    setState(() {
      _entryForms = formProvider.responsesForEntry;
    });
  }
}
```

### Phase 3.3: Create Form Thumbnail Widget

**New File**: `lib/features/toolbox/presentation/widgets/form_thumbnail.dart`

```dart
class FormThumbnail extends StatelessWidget {
  final FormResponse response;
  final InspectorForm form;
  final VoidCallback? onTap;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: GestureDetector(
            onTap: onTap,
            onLongPress: onDelete,
            child: Container(
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.primaryBlue.withValues(alpha: 0.3)),
              ),
              child: Stack(
                children: [
                  // Form icon centered
                  Center(
                    child: Icon(
                      Icons.description,
                      size: 48,
                      color: AppTheme.primaryBlue,
                    ),
                  ),
                  // Status badge (top-right)
                  Positioned(
                    top: 4,
                    right: 4,
                    child: _buildStatusBadge(response.status),
                  ),
                  // Delete button (top-left)
                  if (onDelete != null)
                    Positioned(
                      top: 4,
                      left: 4,
                      child: _buildDeleteButton(),
                    ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          form.name,  // e.g., "MDOT 0582B Density"
          style: const TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w500,
            color: AppTheme.textPrimary,
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }
}
```

### Phase 3.4: Update Grid to Show Both Photos and Forms

**File**: `lib/features/entries/presentation/screens/entry_wizard_screen.dart`

In `_buildAttachmentsSection()`, update the GridView to show unified attachments:

```dart
// Combine photos and forms into unified list
final attachments = [
  ..._entryPhotos.map((p) => _AttachmentItem.photo(p)),
  ..._entryForms.map((f) => _AttachmentItem.form(f)),
];

GridView.builder(
  shrinkWrap: true,
  physics: const NeverScrollableScrollPhysics(),
  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
    crossAxisCount: 3,
    crossAxisSpacing: 8,
    mainAxisSpacing: 8,
    childAspectRatio: 0.75,
  ),
  itemCount: attachments.length,
  itemBuilder: (context, index) {
    final item = attachments[index];
    return item.when(
      photo: (photo) => PhotoThumbnail(
        photo: photo,
        onTap: () => _showPhotoDetail(photo),
        onDelete: () => _confirmDeletePhoto(photo, index),
        style: PhotoThumbnailStyle.withTextBelow,
      ),
      form: (response) => FormThumbnail(
        key: TestingKeys.formThumbnail(response.id),
        response: response,
        form: _getFormForResponse(response),
        onTap: () => _openFormResponse(response),
        onDelete: () => _confirmDeleteForm(response),
      ),
    );
  },
)
```

### Phase 3.5: Add "Start New Form" Button to Attachments Section

**File**: `lib/features/entries/presentation/screens/entry_wizard_screen.dart`

Location: After the "Add Photo" button (around line 1512-1529)

```dart
Row(
  children: [
    Expanded(
      child: OutlinedButton.icon(
        key: TestingKeys.entryWizardAddPhoto,
        onPressed: _isCapturingPhoto ? null : () => _showPhotoSourceDialog(),
        icon: _isCapturingPhoto
            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
            : const Icon(Icons.add_a_photo),
        label: Text(_isCapturingPhoto ? 'Capturing...' : 'Add Photo'),
      ),
    ),
    const SizedBox(width: 12),
    Expanded(
      child: OutlinedButton.icon(
        key: TestingKeys.entryWizardAddForm,
        onPressed: () => _showFormSelectionDialog(context),
        icon: const Icon(Icons.edit_document),
        label: const Text('Start New Form'),
      ),
    ),
  ],
)
```

### Phase 3.6: Create Form Selection Dialog

**New File**: `lib/features/entries/presentation/widgets/form_selection_dialog.dart`

```dart
class FormSelectionDialog extends StatelessWidget {
  final List<InspectorForm> forms;

  const FormSelectionDialog({super.key, required this.forms});

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      key: TestingKeys.formSelectionDialog,
      title: const Text('Select Form'),
      content: SizedBox(
        width: double.maxFinite,
        child: ListView.builder(
          shrinkWrap: true,
          itemCount: forms.length,
          itemBuilder: (context, index) {
            final form = forms[index];
            return ListTile(
              key: TestingKeys.formSelectionItem(form.id),
              leading: Icon(
                form.isBuiltin ? Icons.description : Icons.description_outlined,
                color: AppTheme.primaryBlue,
              ),
              title: Text(form.name),
              subtitle: Text('${form.parsedFieldDefinitions.length} fields'),
              trailing: form.isBuiltin
                  ? Chip(
                      label: const Text('Built-in', style: TextStyle(fontSize: 10)),
                      backgroundColor: AppTheme.statusInfo.withValues(alpha: 0.1),
                    )
                  : null,
              onTap: () => Navigator.of(context).pop(form),
            );
          },
        ),
      ),
      actions: [
        TextButton(
          key: TestingKeys.formSelectionCancelButton,
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
      ],
    );
  }
}
```

### Phase 3.7: Add Form Action Methods

**File**: `lib/features/entries/presentation/screens/entry_wizard_screen.dart`

```dart
Future<void> _showFormSelectionDialog(BuildContext context) async {
  final formProvider = context.read<InspectorFormProvider>();
  final projectId = context.read<ProjectProvider>().selectedProject?.id;

  if (projectId == null) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Please select a project first')),
    );
    return;
  }

  await formProvider.loadFormsForProject(projectId);
  if (!mounted) return;

  final selectedForm = await showDialog<InspectorForm>(
    context: context,
    builder: (context) => FormSelectionDialog(forms: formProvider.forms),
  );

  if (selectedForm != null && mounted) {
    await _startForm(selectedForm);
  }
}

Future<void> _startForm(InspectorForm form) async {
  final formProvider = context.read<InspectorFormProvider>();
  final projectId = context.read<ProjectProvider>().selectedProject?.id;
  final entryId = widget.entryId ?? _entryId;

  final response = FormResponse(
    formId: form.id,
    projectId: projectId,
    entryId: entryId,  // Link to current entry
  );

  final created = await formProvider.createResponse(response);
  if (!mounted) return;

  if (created != null) {
    // Navigate to form fill screen
    context.pushNamed('form-fill', pathParameters: {'responseId': created.id});
    // Refresh forms list when returning
    await _loadFormsForEntry(entryId!);
  }
}

Future<void> _openFormResponse(FormResponse response) async {
  context.pushNamed('form-fill', pathParameters: {'responseId': response.id});
}

Future<void> _confirmDeleteForm(FormResponse response) async {
  final confirmed = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('Delete Form?'),
      content: const Text('This will permanently delete this form response.'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
        TextButton(
          onPressed: () => Navigator.pop(context, true),
          child: Text('Delete', style: TextStyle(color: AppTheme.statusError)),
        ),
      ],
    ),
  );

  if (confirmed == true && mounted) {
    final formProvider = context.read<InspectorFormProvider>();
    await formProvider.deleteResponse(response.id);
    setState(() {
      _entryForms.removeWhere((f) => f.id == response.id);
    });
  }
}

InspectorForm? _getFormForResponse(FormResponse response) {
  final formProvider = context.read<InspectorFormProvider>();
  return formProvider.getFormById(response.formId);
}
```

### Phase 3.8: Add Testing Keys

**File**: `lib/shared/testing_keys/entries_keys.dart`

```dart
/// Add Form button in attachments section
static const entryWizardAddForm = Key('entry_wizard_add_form');

/// Form thumbnail in attachments grid
static Key formThumbnail(String formId) => Key('form_thumbnail_$formId');
```

**File**: `lib/shared/testing_keys/toolbox_keys.dart`

```dart
/// Form selection dialog
static const formSelectionDialog = Key('form_selection_dialog');
static const formSelectionCancelButton = Key('form_selection_cancel_button');
static Key formSelectionItem(String formId) => Key('form_selection_item_$formId');
```

### Phase 3.9: Update Barrel Exports

**File**: `lib/features/entries/presentation/widgets/widgets.dart`
```dart
export 'form_selection_dialog.dart';
```

**File**: `lib/features/toolbox/presentation/widgets/widgets.dart`
```dart
export 'form_thumbnail.dart';
```

### PR 3 Verification
```bash
pwsh -Command "flutter analyze lib/"
pwsh -Command "flutter test"
# Manual:
# 1. Open entry wizard
# 2. Click "Start New Form" in Attachments section
# 3. Select 0582B from dialog
# 4. Fill form, save
# 5. Return to entry wizard - form shows in Attachments grid
```

---

## File Summary

### Files to Create
| File | PR |
|------|-----|
| `lib/features/quantities/presentation/screens/quantity_calculator_screen.dart` | PR 2 |
| `lib/features/entries/presentation/widgets/form_selection_dialog.dart` | PR 3 |
| `lib/features/toolbox/presentation/widgets/form_thumbnail.dart` | PR 3 |

### Files to Modify
| File | PR |
|------|-----|
| `lib/features/entries/presentation/screens/report_screen.dart` | PR 1 |
| `lib/features/entries/data/models/daily_entry.dart` | PR 1 |
| `lib/core/database/schema/entry_tables.dart` | PR 1 |
| `lib/core/database/database_service.dart` | PR 1 |
| `lib/shared/testing_keys/entries_keys.dart` | PR 1, 3 |
| `lib/features/toolbox/data/models/calculation_history.dart` | PR 2 |
| `lib/features/toolbox/data/services/calculator_service.dart` | PR 2 |
| `lib/features/toolbox/presentation/providers/calculator_provider.dart` | PR 2 |
| `lib/features/entries/presentation/screens/entry_wizard_screen.dart` | PR 2, 3 |
| `lib/core/router/app_router.dart` | PR 2 |
| `lib/shared/testing_keys/toolbox_keys.dart` | PR 2, 3 |
| `lib/shared/testing_keys/quantities_keys.dart` | PR 2 |
| `lib/features/entries/presentation/widgets/widgets.dart` | PR 3 |
| `lib/features/toolbox/presentation/widgets/widgets.dart` | PR 3 |

### Test Files to Update
| File | PR |
|------|-----|
| `test/data/models/daily_entry_test.dart` | PR 1 |
| `test/features/entries/presentation/screens/report_screen_test.dart` | PR 1 |
| `test/data/repositories/daily_entry_repository_test.dart` | PR 1 |
| `integration_test/patrol/fixtures/test_seed_data.dart` | PR 1 |

---

## Implementation Order

1. **PR 0**: Fix FormFillScreen Provider issue (prerequisite - fixes 0582B form)
2. **PR 1**: Remove Test Results Section (independent, can parallel with PR 0)
3. **PR 2**: Calculate New Quantity button + Enhanced Calculator (Materials section)
4. **PR 3**: Start New Form button + Attachments enhancement (Attachments section)

---

## Section Layout Reference

After implementation:

```
┌─────────────────────────────────────────────────────────────┐
│ Materials Used                                              │
├─────────────────────────────────────────────────────────────┤
│ [Quantity cards here...]                                    │
│                                                             │
│ ┌─────────────┐ ┌───────────────────────┐                   │
│ │ + Add       │ │ 🧮 Calculate New      │                   │
│ │   Quantity  │ │    Quantity           │                   │
│ └─────────────┘ └───────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Attachments                                    (3 photos, 1 form) │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│ │ 📷       │ │ 📷       │ │ 📷       │ │ 📄       │        │
│ │ [image]  │ │ [image]  │ │ [image]  │ │ [form    │        │
│ │          │ │          │ │          │ │  icon]   │        │
│ ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤        │
│ │Photo 1   │ │Photo 2   │ │Photo 3   │ │MDOT 0582B│        │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│                                                             │
│ ┌─────────────────────┐ ┌─────────────────────┐            │
│ │ 📷 Add Photo        │ │ 📄 Start New Form   │            │
│ └─────────────────────┘ └─────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

All buttons use `OutlinedButton.icon` with cyan/teal theme styling.
