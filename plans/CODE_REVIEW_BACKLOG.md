# Code Review Backlog

**Created**: 2026-01-28 (Session 156)
**Source**: Code review of Phases 3 & 4

Items identified during code review that are not blocking but should be addressed in future phases.

---

## Priority: Should Consider

### 1. Enum Deserialization Safety in CalculationHistory
**File**: `lib/features/toolbox/data/models/calculation_history.dart:94`
**Issue**: Uses `.byName()` without fallback - throws on unknown values
**Current**:
```dart
calcType: CalculationType.values.byName(map['calc_type'] as String),
```
**Better**:
```dart
calcType: CalculationType.values.where((e) => e.name == map['calc_type']).firstOrNull ?? CalculationType.hma,
```
**Risk**: Database contains unknown value from newer app version → crash
**Target Phase**: 14 (DRY/KISS Utilities)

---

### 2. Index-Based Enum Serialization in TodoItem
**File**: `lib/features/toolbox/data/models/todo_item.dart:111`
**Issue**: Uses index-based lookup - fragile if enum order changes
**Current**:
```dart
priority: TodoPriority.values[map['priority'] as int? ?? 1],
```
**Better**: Use `.name` for serialization and `.byName`/`.where` for deserialization
**Risk**: Enum reordering corrupts stored data
**Target Phase**: 14 (DRY/KISS Utilities)

---

### 3. Missing `updatedAt` in Immutable Models
**Files**:
- `lib/features/toolbox/data/models/field_semantic_alias.dart`
- `lib/features/toolbox/data/models/calculation_history.dart`
**Issue**: Models only have `createdAt`, deviating from standard pattern
**Decision**: Intentionally immutable - these are append-only/reference entities
**Action**: Add inline documentation explaining immutability design choice
**Target Phase**: 14 (Documentation pass)

---

### 4. Shared Enum Parsing Utility
**Pattern**: `.values.where((e) => e.name == value).firstOrNull ?? default` appears in multiple files
**Files Using Pattern**:
- `lib/features/toolbox/data/models/form_field_entry.dart` (correctly)
- `lib/features/toolbox/data/models/inspector_form.dart` (correctly)
**Opportunity**: Extract to shared utility
```dart
// lib/shared/utils/enum_utils.dart
T? parseEnum<T extends Enum>(List<T> values, String? name, [T? defaultValue]) {
  if (name == null) return defaultValue;
  return values.where((e) => e.name == name).firstOrNull ?? defaultValue;
}
```
**Target Phase**: 14 (DRY/KISS Utilities - item 14.2)

---

## Priority: Minor (Nice to Have)

### 5. Missing `toString()` Methods
**Files**:
- `lib/features/toolbox/data/models/calculation_history.dart`
- `lib/features/toolbox/data/models/todo_item.dart`
**Issue**: Missing `toString()` makes debugging harder
**Note**: `FormFieldEntry` and `FieldSemanticAlias` correctly have `toString()`
**Target Phase**: 14

---

### 6. FormSeedService Optional Parameter
**File**: `lib/features/toolbox/data/services/form_seed_service.dart:49`
**Current**:
```dart
FormSeedService(this._repository, [this._registryService]);
```
**Better**: Named parameter for clarity
```dart
FormSeedService(this._repository, {FieldRegistryService? registryService})
    : _registryService = registryService;
```
**Risk**: Low - backward compatibility concern is documented
**Target Phase**: 14

---

### 7. Document Case Normalization in Alias Lookup
**Files**:
- `lib/features/toolbox/data/datasources/local/field_semantic_alias_local_datasource.dart:53`
- `lib/features/toolbox/data/services/field_registry_service.dart:328`
**Issue**: Aliases normalized to lowercase on storage and lookup (consistent, but undocumented)
**Action**: Add doc comment to `FieldSemanticAlias` model explaining normalization
**Target Phase**: 14

---

## Completed (No Action Needed)

### SQL Pattern in getDependentFields
**File**: `lib/features/toolbox/data/datasources/local/form_field_registry_local_datasource.dart:95`
**Concern**: `fieldName` in LIKE pattern
**Status**: Low risk - internal data only, not user input
**Decision**: Acceptable for current use case

---

## Summary by Target Phase

| Phase | Items | Description |
|-------|-------|-------------|
| 14 | 1, 2, 3, 4, 5, 6, 7 | DRY/KISS Utilities + shared patterns |

---

## Review History

| Date | Session | Reviewer | Scope |
|------|---------|----------|-------|
| 2026-01-28 | 159 | code-review-agent | Phase 5 (Auto-Fill) |
| 2026-01-28 | 156 | code-review-agent | Phases 3 & 4 |

---

## Phase 5 Code Review - 2026-01-28 (Session 159)

**Commits Reviewed**: `543d1ba`, `1c0e81f`
**Scope**: Smart Auto-Fill + Carry-Forward Defaults
**Overall**: ~85% complete - read infrastructure solid, write path for carry-forward missing

### Phase 5 Requirements Verification

| Step | Requirement | Status | Notes |
|------|-------------|--------|-------|
| 5.1 | AutoFill engine with provenance | ✅ Complete | `AutoFillEngine`, `AutoFillResult` with source/confidence |
| 5.2 | Inspector profile expansion | ✅ Complete | Phone, cert, agency in settings + PreferencesService |
| 5.3 | Carry-forward cache | ⚠️ Partial | Read infrastructure complete, write path missing, no per-form toggle |
| 5.4 | UI auto-fill indicators | ✅ Complete | `AutoFillIndicator` widget, bulk apply/clear actions |
| 5.5 | Context hydration | ⚠️ Partial | Builder exists but doesn't integrate carry-forward cache |

### Priority: Critical (Must Fix for Phase 5 Completion)

#### 8. Carry-Forward Cache Never Populated
**File**: `lib/features/toolbox/data/services/auto_fill_context_builder.dart:153`
**Issue**: `carryForwardCache` is always initialized as empty `<String, String>{}` and never populated. `FieldRegistryService.getCarryForwardCache()` exists but is never called.
**Fix**: Inject `FieldRegistryService` and call `getCarryForwardCache(projectId)` to populate context.
**Impact**: Step 5.3 carry-forward feature does not function
**Target Phase**: 5 (Completion)

---

#### 9. No Write Path for Carry-Forward Cache
**Files**: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`, `lib/features/toolbox/presentation/providers/form_fill_provider.dart`
**Issue**: When user saves a form, field values are never written to `form_field_cache`. Datasource has `upsert()` and `upsertBatch()` methods but they are never called.
**Fix**: Add cache update logic in `FormFillProvider.saveResponse()` or `FormFillScreen._saveForm()`.
**Impact**: Step 5.3 incomplete - cache will always be empty
**Target Phase**: 5 (Completion)

---

#### 10. Missing "Use Last Value" Toggle Per Form
**File**: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`
**Issue**: Settings has global `useLastValues` toggle, but Step 5.3 specifies "add 'Use last value' toggle per form."
**Fix**: Add per-form toggle in form fill UI that allows override per form session.
**Impact**: Step 5.3 not fully implemented
**Target Phase**: 5 (Completion)

---

### Priority: Major (Should Fix)

#### 11. Tests Don't Test Actual Auto-Fill Engine
**File**: `test/features/toolbox/presentation/screens/form_fill_screen_test.dart`
**Issue**: Test file defines local `AutoFillContext` and `FormAutoFillHelper` classes that duplicate/diverge from actual implementation. Tests pass but don't verify real code.
**Fix**: Update tests to use actual `AutoFillEngine`, `AutoFillContext`, `AutoFillResult` classes.
**Target Phase**: 6 or 9 (QA phase)

---

#### 12. FormFillScreen Uses Local State Instead of Provider
**File**: `lib/features/toolbox/presentation/screens/form_fill_screen.dart:52-54`
**Issue**: Screen maintains own `_autoFillResults` and `_userEditedFields` state instead of using `FormFillProvider`. Creates dual state and potential sync issues.
**Fix**: Fully migrate to `FormFillProvider` or remove unused provider.
**Target Phase**: 6

---

#### 13. Async Context Safety in AutoFillContextBuilder
**File**: `lib/features/toolbox/data/services/auto_fill_context_builder.dart:34-150`
**Issue**: Method is `async` but uses `context.read<T>()` without mounted check. Could cause issues if widget disposes during async operation.
**Fix**: Pass providers as parameters rather than reading from context inside async method.
**Target Phase**: 6

---

### Priority: Minor (Nice to Have)

#### 14. Duplicate _generateInitialsFromName Method
**Files**: `lib/features/settings/presentation/screens/settings_screen.dart:38-50`, `lib/shared/services/preferences_service.dart:72-84`
**Issue**: Identical logic in both files (DRY violation)
**Fix**: Remove duplicate from `settings_screen.dart`, use `prefsService.effectiveInitials` consistently
**Target Phase**: 14 (DRY/KISS)

---

#### 15. Hardcoded Auto-Fillable Field List
**File**: `lib/features/toolbox/presentation/screens/form_fill_screen.dart:286-304`
**Issue**: `_isFieldAutoFillable()` and `_getAutoFillSource()` use hardcoded string lists. `FormFieldEntry` already has `isAutoFillable` and `autoFillSource` properties.
**Fix**: Remove temporary methods once registry integration is complete (as noted in TODOs)
**Target Phase**: 6

---

#### 16. Magic Strings in Auto-Fill Matching
**File**: `lib/features/toolbox/data/services/auto_fill_engine.dart:233-380`
**Issue**: Semantic name matching uses hardcoded string lists (e.g., `['inspector', 'inspector_name', 'technician']`). Fragile and hard to maintain.
**Fix**: Move mappings to configuration file or `field_semantic_aliases` table
**Target Phase**: 14

---

#### 17. No Confidence Level Visual Differentiation
**File**: `lib/features/toolbox/presentation/widgets/auto_fill_indicator.dart`
**Issue**: `AutoFillResult.confidence` (high/medium/low) exists but indicator doesn't visually differentiate.
**Fix**: Optionally show different styling for low-confidence carry-forward values
**Target Phase**: 7 (UX)

---

### Positive Observations

1. **Clean Architecture**: Solid separation - `AutoFillEngine` (logic), `AutoFillContextBuilder` (data), `AutoFillResult` (provenance), UI indicator
2. **Provenance Tracking**: `AutoFillResult` properly tracks source, confidence, user edits - matches spec
3. **Inspector Profile**: Complete - phone, cert number, agency in settings + PreferencesService
4. **Database Schema**: Migration v15 properly adds `form_field_cache` with unique constraint and indexes
5. **Datasource Tests**: `FormFieldCacheLocalDatasourceTest` has comprehensive CRUD coverage
6. **UI Integration**: Auto-fill indicators with source-specific icons/colors provide good UX
7. **Bulk Operations**: "Auto-fill all" and "Clear auto-filled only" properly implemented
8. **Global Aliases**: `FieldRegistryService` seeds comprehensive field alias list

---

### Summary by Target Phase

| Phase | Items | Description |
|-------|-------|-------------|
| 5 (Completion) | 8, 9, 10 | Critical carry-forward completion |
| 6 | 12, 13, 15 | State consolidation, async safety |
| 9 | 11 | Test updates for auto-fill engine |
| 14 | 1, 2, 3, 4, 5, 6, 7, 14, 16 | DRY/KISS Utilities + shared patterns |
| 7 | 17 | UX confidence indicators |
