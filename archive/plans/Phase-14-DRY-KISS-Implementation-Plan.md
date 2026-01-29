# Phase 14: DRY/KISS Utilities Implementation Plan

**Created**: 2026-01-28 (Session 175)
**Source**: Code Review Backlog Analysis
**Estimated PRs**: 6 phases (A-F)
**Total Items**: 18 verified issues

---

## Executive Summary

Phase 14 addresses technical debt accumulated during rapid feature development (Phases 1-13). Items were identified through code reviews and prioritized by risk and maintainability impact.

### Priority Matrix

| Priority | Count | Description |
|----------|-------|-------------|
| Critical | 2 | Enum deserialization crashes |
| High | 2 | Async safety violations |
| Medium | 8 | DRY violations, architecture |
| Low | 6 | Documentation, style |

---

## Phase A: Enum Safety (Critical)

**PR Size**: Small (~100 LOC)
**Risk**: High (prevents production crashes)
**Dependencies**: None

### A.1: Fix CalculationType.byName() Crash

**File**: `lib/features/toolbox/data/models/calculation_history.dart:94`

**Issue**: Direct `.byName()` without fallback throws `StateError` on unknown values.

**Current Code**:
```dart
calcType: CalculationType.values.byName(map['calc_type'] as String),
```

**Root Cause**: Database may contain enum values from newer app version, or data corruption.

**Fix**:
```dart
calcType: CalculationType.values.where((e) => e.name == map['calc_type']).firstOrNull
    ?? CalculationType.hma,
```

**Test**: Add unit test with unknown enum value to verify fallback.

**Ref**: Backlog Item #1

---

### A.2: Fix TodoPriority Index-Based Serialization

**File**: `lib/features/toolbox/data/models/todo_item.dart:94,111`

**Issue**: Uses `.index` for serialization - enum reordering corrupts data.

**Current Code**:
```dart
// Line 94 (toMap)
'priority': priority.index,

// Line 111 (fromMap)
priority: TodoPriority.values[map['priority'] as int? ?? 1],
```

**Root Cause**: Index-based storage is fragile. If `TodoPriority` enum is reordered, stored data becomes incorrect.

**Fix**:
```dart
// toMap (line 94)
'priority': priority.name,

// fromMap (line 111)
priority: TodoPriority.values.where((e) => e.name == map['priority']).firstOrNull
    ?? TodoPriority.normal,
```

**Migration**: Add backwards-compatibility for existing int-based data:
```dart
priority: map['priority'] is int
    ? TodoPriority.values[map['priority'] as int]  // Legacy int format
    : TodoPriority.values.where((e) => e.name == map['priority']).firstOrNull
        ?? TodoPriority.normal,
```

**Test**: Add unit tests for both int and string deserialization.

**Ref**: Backlog Item #2

---

### A.3: Create Shared Enum Parsing Utility

**New File**: `lib/shared/utils/enum_utils.dart`

**Issue**: Pattern `.values.where((e) => e.name == value).firstOrNull ?? default` appears 5+ times.

**Occurrences Found**:
| File | Line | Enum Type |
|------|------|-----------|
| `inspector_form.dart` | 154 | `TemplateSource` |
| `form_field_entry.dart` | 278 | `PdfFieldType` |
| `form_field_entry.dart` | 284 | `FieldValueType` |
| `form_field_entry.dart` | 290 | `AutoFillSource` |
| `auto_fill_result.dart` | 71-76 | `AutoFillSource`, `AutoFillConfidence` |

**Implementation**:
```dart
/// Safe enum parsing utilities.
///
/// Provides null-safe enum deserialization with optional defaults.
/// Use instead of `.byName()` which throws on unknown values.
extension EnumByNameOrNull<T extends Enum> on Iterable<T> {
  /// Find enum by name, returning null if not found.
  ///
  /// Example:
  /// ```dart
  /// final source = AutoFillSource.values.byNameOrNull('project');
  /// ```
  T? byNameOrNull(String? name) {
    if (name == null) return null;
    return where((e) => e.name == name).firstOrNull;
  }

  /// Find enum by name with fallback default.
  ///
  /// Example:
  /// ```dart
  /// final source = AutoFillSource.values.byNameOr('unknown', AutoFillSource.project);
  /// ```
  T byNameOr(String? name, T defaultValue) {
    return byNameOrNull(name) ?? defaultValue;
  }
}
```

**Refactor Targets**: Update all 5 occurrences to use extension.

**Ref**: Backlog Item #4

---

## Phase B: Async Safety (High)

**PR Size**: Medium (~150 LOC)
**Risk**: High (prevents disposed widget errors)
**Dependencies**: None

### B.1: Add Mounted Checks in FormFillScreen Auto-Fill Methods

**File**: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`

**Issue**: `_autoFillFromContext()` and `_autoFillAll()` use context after await without mounted checks.

**Locations**:
- Line 256: After `contextBuilder.buildContext()` await
- Line 302: After `contextBuilder.buildContext()` await

**Current Code (line 256-272)**:
```dart
final autoFillContext = await contextBuilder.buildContext(
  context: context,
  projectId: project?.id,
  entryId: response.entryId,
  includeCarryForward: _useCarryForward,
);

// NO MOUNTED CHECK!
final autoFillEngine = AutoFillEngine();
final results = autoFillEngine.autoFill(...);
```

**Fix**:
```dart
final autoFillContext = await contextBuilder.buildContext(
  context: context,
  projectId: project?.id,
  entryId: response.entryId,
  includeCarryForward: _useCarryForward,
);

if (!mounted) return;  // ADD THIS

final autoFillEngine = AutoFillEngine();
final results = autoFillEngine.autoFill(...);
```

**Apply Same Fix**: Line 302 in `_autoFillAll()`.

**Ref**: Backlog Items #13, #31

---

### B.2: Document AutoFillContextBuilder Async Pattern

**File**: `lib/features/toolbox/data/services/auto_fill_context_builder.dart`

**Issue**: Method accepts `BuildContext` but is async - callers must add mounted checks.

**Current Signature (line 34)**:
```dart
Future<AutoFillContext> buildContext({
  required BuildContext context,
  String? projectId,
  String? entryId,
  bool includeCarryForward = true,
}) async {
```

**Action**: Add documentation warning:
```dart
/// Build auto-fill context from app state.
///
/// **IMPORTANT**: This method is async. Callers MUST check `mounted`
/// after awaiting this method before using the result or accessing context.
///
/// Example:
/// ```dart
/// final ctx = await builder.buildContext(context: context, ...);
/// if (!mounted) return;  // Required!
/// // Safe to use ctx here
/// ```
Future<AutoFillContext> buildContext({...})
```

**Ref**: Backlog Item #13

---

## Phase C: DRY Extraction (Medium)

**PR Size**: Medium (~200 LOC)
**Risk**: Low (pure refactoring)
**Dependencies**: Phase A (enum utils)

### C.1: Extract _generateInitialsFromName to Shared Utility

**Files**:
- `lib/features/settings/presentation/screens/settings_screen.dart:38-42`
- `lib/shared/services/preferences_service.dart:80-84`

**Issue**: Identical 5-line method duplicated in both files.

**Current Code (both locations)**:
```dart
String _generateInitialsFromName(String name) {
  final parts = name.trim().split(RegExp(r'\s+'));
  if (parts.isEmpty) return '';
  return parts.map((p) => p.isNotEmpty ? p[0].toUpperCase() : '').join();
}
```

**Fix**: Move to `lib/shared/utils/string_utils.dart`:
```dart
/// Generate initials from a full name.
///
/// Example: "John Doe" -> "JD", "Mary Jane Watson" -> "MJW"
String generateInitialsFromName(String name) {
  final parts = name.trim().split(RegExp(r'\s+'));
  if (parts.isEmpty) return '';
  return parts.map((p) => p.isNotEmpty ? p[0].toUpperCase() : '').join();
}
```

**Update Callers**:
- `settings_screen.dart`: Import and call `generateInitialsFromName()`
- `preferences_service.dart`: Already in shared, rename from private to public

**Ref**: Backlog Item #14

---

### C.2: Extract _getFieldIcon to Shared Widget Helper

**Files**:
- `lib/features/toolbox/presentation/screens/form_import_screen.dart:359-377`
- `lib/features/toolbox/presentation/screens/field_mapping_screen.dart:499-517`

**Issue**: Identical 19-line method duplicated in both screens.

**Current Code (both locations)**:
```dart
IconData _getFieldIcon(String fieldType) {
  switch (fieldType.toLowerCase()) {
    case 'text':
    case 'textarea':
      return Icons.text_fields;
    case 'checkbox':
      return Icons.check_box_outlined;
    case 'radio':
      return Icons.radio_button_checked;
    case 'dropdown':
      return Icons.arrow_drop_down_circle_outlined;
    case 'date':
      return Icons.calendar_today;
    case 'signature':
      return Icons.draw;
    default:
      return Icons.input;
  }
}
```

**Fix**: Create `lib/features/toolbox/presentation/utils/field_icon_utils.dart`:
```dart
import 'package:flutter/material.dart';

/// Get icon for a PDF field type.
///
/// Maps field type strings to Material icons for consistent display
/// across form import and field mapping screens.
IconData getFieldTypeIcon(String fieldType) {
  switch (fieldType.toLowerCase()) {
    case 'text':
    case 'textarea':
      return Icons.text_fields;
    case 'checkbox':
      return Icons.check_box_outlined;
    case 'radio':
      return Icons.radio_button_checked;
    case 'dropdown':
      return Icons.arrow_drop_down_circle_outlined;
    case 'date':
      return Icons.calendar_today;
    case 'signature':
      return Icons.draw;
    default:
      return Icons.input;
  }
}
```

**Ref**: Backlog Item #28

---

### C.3: Consolidate Auto-Fill Context Building Logic

**File**: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`

**Issue**: `_autoFillFromContext()` (lines 242-288) and `_autoFillAll()` (lines 290-342) share ~80% identical code.

**Shared Code Pattern**:
```dart
// Both methods do:
1. Check prefs/project (4 lines)
2. Build context (6 lines)
3. Create engine (1 line)
4. Run autoFill (8 lines)
// Only difference: forceOverwrite param and post-processing
```

**Fix**: Extract shared logic:
```dart
/// Perform auto-fill operation and return results.
///
/// Builds context, runs engine, returns results without applying them.
/// Caller handles result application and UI feedback.
Future<AutoFillResults?> _performAutoFill({
  required InspectorForm form,
  required String? entryId,
  required bool forceOverwrite,
}) async {
  final prefsService = context.read<PreferencesService>();
  if (!prefsService.autoFillEnabled && !forceOverwrite) return null;

  final projectProvider = context.read<ProjectProvider>();
  final project = projectProvider.selectedProject;

  final contextBuilder = AutoFillContextBuilder();
  final autoFillContext = await contextBuilder.buildContext(
    context: context,
    projectId: project?.id,
    entryId: entryId,
    includeCarryForward: _useCarryForward,
  );

  if (!mounted) return null;

  final autoFillEngine = AutoFillEngine();
  return autoFillEngine.autoFill(
    form: form,
    context: autoFillContext,
    fields: _fieldEntries,
    existingValues: _collectFieldValuesAsStrings(),
    userEditedFields: _userEditedFields,
    forceOverwrite: forceOverwrite,
  );
}
```

**Refactor Callers**:
```dart
Future<void> _autoFillFromContext(InspectorForm form, FormResponse response) async {
  final results = await _performAutoFill(
    form: form,
    entryId: response.entryId,
    forceOverwrite: false,
  );
  if (results == null || !mounted) return;

  // Apply results to empty fields only
  for (final entry in results.results.entries) {
    if (_userEditedFields.contains(entry.key)) continue;
    final controller = _fieldControllers[entry.key];
    if (controller != null && controller.text.isEmpty) {
      controller.text = entry.value.value;
      _autoFillResults[entry.key] = entry.value;
    }
  }
}
```

**Ref**: Backlog Item #19

---

## Phase D: Code Quality (Medium)

**PR Size**: Small (~100 LOC)
**Risk**: Low (non-breaking improvements)
**Dependencies**: None

### D.1: Add toString() to CalculationHistory

**File**: `lib/features/toolbox/data/models/calculation_history.dart`

**Issue**: Missing `toString()` makes debugging difficult.

**Implementation**:
```dart
@override
String toString() => 'CalculationHistory('
    'id: $id, '
    'calcType: ${calcType.name}, '
    'result: $result, '
    'createdAt: $createdAt)';
```

**Ref**: Backlog Item #5

---

### D.2: Add toString() to TodoItem

**File**: `lib/features/toolbox/data/models/todo_item.dart`

**Issue**: Missing `toString()` makes debugging difficult.

**Implementation**:
```dart
@override
String toString() => 'TodoItem('
    'id: $id, '
    'title: $title, '
    'priority: ${priority.name}, '
    'isCompleted: $isCompleted)';
```

**Ref**: Backlog Item #5

---

### D.3: Update FormSeedService to Named Parameter

**File**: `lib/features/toolbox/data/services/form_seed_service.dart:49`

**Issue**: Uses positional optional parameter (deprecated style).

**Current**:
```dart
FormSeedService(this._repository, [this._registryService]);
```

**Fix**:
```dart
FormSeedService(this._repository, {FieldRegistryService? registryService})
    : _registryService = registryService;
```

**Update Callers**: Search for `FormSeedService(` and update to named parameter.

**Ref**: Backlog Item #6

---

### D.4: Remove Temporary Auto-Fill Field Helpers

**File**: `lib/features/toolbox/presentation/screens/form_fill_screen.dart:446-491`

**Issue**: Hardcoded `_isFieldAutoFillable()` and `_getAutoFillSource()` methods with TODO comments indicating they should be removed.

**Current Code**:
```dart
/// Temporary: Check if a field should be auto-fillable.
/// TODO: Remove when FormFieldRegistryRepository is integrated.
bool _isFieldAutoFillable(String fieldName) {
  const autoFillableFields = {
    'project_number', 'project_name', 'date', 'contractor', ...
  };
  return autoFillableFields.contains(fieldName.toLowerCase());
}

/// Temporary: Get auto-fill source for a field.
/// TODO: Remove when FormFieldRegistryRepository is integrated.
AutoFillSource? _getAutoFillSource(String fieldName) { ... }
```

**Verification**: Confirm `FormFieldEntry.isAutoFillable` and `FormFieldEntry.autoFillSource` properties are populated from registry.

**Action**:
1. Verify registry integration is complete (check `_loadFieldEntries()`)
2. Remove both temporary methods
3. Remove fallback path that creates entries with hardcoded values

**Ref**: Backlog Items #15, #32

---

## Phase E: Configuration Extraction (Low)

**PR Size**: Small (~80 LOC)
**Risk**: Low (constants only)
**Dependencies**: None

### E.1: Extract Compaction Spec Constants

**File**: `lib/features/toolbox/data/services/density_calculator_service.dart:251-262`

**Issue**: Magic numbers (95.0, 98.0, 102.0, 105.0) repeated without documentation.

**Current Code**:
```dart
if (percentCompaction < 95.0) {
  return 'BELOW SPEC (< 95%)';
} else if (percentCompaction > 105.0) {
  return 'ABOVE SPEC (> 105%)';
} else if (percentCompaction >= 95.0 && percentCompaction < 98.0) {
  return 'Acceptable (low)';
} // ...
```

**Fix**: Add constants at class level:
```dart
/// MDOT Standard Specification compaction thresholds.
///
/// These values represent the acceptable range for percent compaction
/// per MDOT construction standards.
class DensityCompactionSpecs {
  /// Minimum acceptable compaction (%)
  static const minAcceptable = 95.0;

  /// Maximum acceptable compaction (%)
  static const maxAcceptable = 105.0;

  /// Start of "good" compaction range (%)
  static const goodRangeStart = 98.0;

  /// End of "good" compaction range (%)
  static const goodRangeEnd = 102.0;

  DensityCompactionSpecs._();
}
```

**Refactor Method**:
```dart
String getCompactionStatusMessage(double percentCompaction) {
  if (percentCompaction < DensityCompactionSpecs.minAcceptable) {
    return 'BELOW SPEC (< ${DensityCompactionSpecs.minAcceptable.toInt()}%)';
  } // ...
}
```

**Ref**: Backlog Item #20

---

### E.2: Document Semantic Alias Magic Strings

**File**: `lib/features/toolbox/data/services/auto_fill_engine.dart:233-373`

**Issue**: Hardcoded semantic name lists in `_resolveXxxField()` methods.

**Analysis**: 15+ arrays of aliases spread across 6 methods. Full extraction to config class would be significant refactoring with low ROI.

**Action**: Add documentation explaining the pattern and rationale:
```dart
/// Resolve inspector profile fields using semantic name matching.
///
/// Matches field semantic names against known aliases:
/// - Inspector name: 'inspector', 'inspector_name', 'technician', 'representative'
/// - Phone: 'inspector_phone', 'phone', 'technician_phone'
/// - Certification: 'certification', 'cert', 'certification_number', 'cert_number'
/// - Agency: 'agency', 'inspector_agency', 'company'
/// - Initials: 'initials', 'inspector_initials'
///
/// These aliases are intentionally hardcoded for performance. For user-defined
/// aliases, use the `field_semantic_aliases` table via FieldRegistryService.
(String?, String?) _resolveInspectorField(FormFieldEntry field, AutoFillContext context) {
```

**Future Consideration**: If aliases need to be user-configurable, extract to `SemanticAliasConfig` class.

**Ref**: Backlog Item #16

---

### E.3: Document Case Normalization in Alias Lookup

**Files**:
- `lib/features/toolbox/data/datasources/local/field_semantic_alias_local_datasource.dart:53,66`
- `lib/features/toolbox/data/services/field_registry_service.dart:345`

**Issue**: Aliases are normalized to lowercase on storage and lookup, but this is undocumented.

**Action**: Add doc comment to `FieldSemanticAlias` model:
```dart
/// A semantic alias mapping for form fields.
///
/// **Case Normalization**: Aliases are normalized to lowercase during both
/// storage and lookup. This ensures consistent matching regardless of
/// the case used in PDF field names or user input.
///
/// Example: Both "Inspector_Name" and "inspector_name" will match
/// the semantic name "inspector".
class FieldSemanticAlias {
```

**Ref**: Backlog Item #7

---

### E.4: Document Immutable Model Design Choice

**Files**:
- `lib/features/toolbox/data/models/field_semantic_alias.dart`
- `lib/features/toolbox/data/models/calculation_history.dart`

**Issue**: Models only have `createdAt`, missing `updatedAt`. This is intentional but undocumented.

**Action**: Add design note:
```dart
/// A calculation result stored in history.
///
/// **Immutability**: This model intentionally lacks an `updatedAt` field.
/// Calculation history entries are append-only and never modified after
/// creation. This simplifies synchronization and provides an audit trail.
class CalculationHistory {
```

**Ref**: Backlog Item #3

---

## Phase F: Cleanup (Low)

**PR Size**: Small (~50 LOC)
**Risk**: Low (dead code removal)
**Dependencies**: None

### F.1: Remove Stub Classes from FormImportProvider

**File**: `lib/features/toolbox/presentation/providers/form_import_provider.dart:118-149`

**Issue**: Stub classes (`_MinimalRepository`, `_StubRegistryDatasource`, `_StubAliasDatasource`) throw `UnimplementedError` in constructor.

**Current Code**:
```dart
class _StubRegistryDatasource extends FormFieldRegistryLocalDatasource {
  _StubRegistryDatasource() : super(throw UnimplementedError());
  // ...
}
```

**Analysis**: These stubs are never successfully instantiated due to constructor throw. They appear to be legacy code from before proper dependency injection.

**Action**:
1. Verify `FormImportProvider` always receives a valid `FormFieldRegistryRepository`
2. Remove `_MinimalRepository`, `_StubRegistryDatasource`, `_StubAliasDatasource` classes
3. Update `analyzeFields()` to require repository (fail fast if null)

**Ref**: Backlog Item #29

---

## Verification Removed (Not Issues)

### Item #22: Debug Print in form_state_hasher.dart
**Status**: FALSE ALARM
**Reason**: `debugPrint()` is automatically stripped in release builds by Dart SDK. No action needed.

### Item #23: Status Helper Methods in form_test_history_card.dart
**Status**: NOT A DUPLICATE
**Reason**: These methods (`_getStatusIcon`, `_getStatusColor`, `_getStatusLabel`) are unique to `FormResponseStatus` enum handling. Not duplicated elsewhere.

---

## Implementation Order

```
Phase A (Critical)   ────────────────────►  Tests Required
    │
    ├── A.1: CalculationType.byName fix
    ├── A.2: TodoPriority index fix
    └── A.3: Enum utility extraction

Phase B (High)       ────────────────────►  Tests Required
    │
    ├── B.1: Mounted checks in FormFillScreen
    └── B.2: Documentation for async pattern

Phase C (Medium)     ────────────────────►  Refactor Only
    │
    ├── C.1: Extract _generateInitialsFromName
    ├── C.2: Extract _getFieldIcon
    └── C.3: Consolidate auto-fill logic

Phase D (Medium)     ────────────────────►  Minor Changes
    │
    ├── D.1: CalculationHistory toString
    ├── D.2: TodoItem toString
    ├── D.3: FormSeedService named param
    └── D.4: Remove temp auto-fill helpers

Phase E (Low)        ────────────────────►  Documentation
    │
    ├── E.1: Compaction spec constants
    ├── E.2: Semantic alias documentation
    ├── E.3: Case normalization docs
    └── E.4: Immutable model design docs

Phase F (Low)        ────────────────────►  Cleanup
    │
    └── F.1: Remove stub classes
```

---

## Test Requirements

### Phase A Tests
- [ ] `calculation_history_test.dart`: Unknown enum value deserialization
- [ ] `todo_item_test.dart`: String-based priority serialization round-trip
- [ ] `todo_item_test.dart`: Legacy int-based priority migration
- [ ] `enum_utils_test.dart`: Extension method edge cases

### Phase B Tests
- [ ] `form_fill_screen_test.dart`: Auto-fill with disposed widget (no crash)

### Phase C Tests
- [ ] `string_utils_test.dart`: generateInitialsFromName edge cases
- [ ] `field_icon_utils_test.dart`: All field types mapped

---

## Success Criteria

| Phase | Criteria |
|-------|----------|
| A | All enum deserialization has fallbacks; analyzer passes |
| B | No `mounted` check warnings; async patterns documented |
| C | No duplicate methods; shared utilities extracted |
| D | All models have toString(); no temporary code |
| E | Magic numbers documented/extracted |
| F | No dead code; clean provider dependencies |

---

## References

| Item | Backlog Ref | Phase |
|------|-------------|-------|
| CalculationType.byName | #1 | A.1 |
| TodoPriority index | #2 | A.2 |
| Enum utility | #4 | A.3 |
| Missing updatedAt | #3 | E.4 |
| Missing toString | #5 | D.1, D.2 |
| FormSeedService param | #6 | D.3 |
| Case normalization | #7 | E.3 |
| Async context safety | #13 | B.1, B.2 |
| Duplicate initials | #14 | C.1 |
| Hardcoded auto-fill | #15 | D.4 |
| Magic strings | #16 | E.2 |
| Duplicate CalculationResult | #18 | Deferred |
| Auto-fill duplication | #19 | C.3 |
| Magic numbers | #20 | E.1 |
| FormFieldsTab params | #21 | Deferred |
| Duplicate _getFieldIcon | #28 | C.2 |
| Stub classes | #29 | F.1 |
| Async context builder | #31 | B.1 |
| Temp auto-fill helpers | #32 | D.4 |

---

## Deferred Items

### Item #18: Duplicate CalculationResult Classes
**Reason**: Both classes serve distinct domains (formula evaluation vs material calculations). Merging would add unnecessary coupling. Low ROI for refactoring.
**Future**: Consider if calculation subsystem is refactored.

### Item #21: FormFieldsTab 26 Parameters
**Reason**: Major refactoring to extract DTOs. Widget works correctly. Low ROI.
**Future**: Address if screen undergoes significant changes.

---

## Commit Message Templates

```
feat(toolbox): Phase 14A - Enum safety fixes

- Add fallback to CalculationType.byName deserialization
- Convert TodoPriority from index to name-based serialization
- Extract EnumByNameOrNull extension to shared utils
- Add backwards compatibility for legacy int priority format

Fixes: Backlog items #1, #2, #4
```

```
fix(toolbox): Phase 14B - Async context safety

- Add mounted checks after auto-fill context building
- Document async pattern requirements in AutoFillContextBuilder

Fixes: Backlog items #13, #31
```

```
refactor(toolbox): Phase 14C - DRY extraction

- Extract generateInitialsFromName to string_utils
- Extract getFieldTypeIcon to field_icon_utils
- Consolidate auto-fill methods in FormFillScreen

Fixes: Backlog items #14, #19, #28
```
