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
**Overall**: ✅ **100% Complete** (Session 160 - fixed remaining items)

### Phase 5 Requirements Verification

| Step | Requirement | Status | Notes |
|------|-------------|--------|-------|
| 5.1 | AutoFill engine with provenance | ✅ Complete | `AutoFillEngine`, `AutoFillResult` with source/confidence |
| 5.2 | Inspector profile expansion | ✅ Complete | Phone, cert, agency in settings + PreferencesService |
| 5.3 | Carry-forward cache | ✅ Complete | Read + write paths, per-form toggle in auto-fill menu |
| 5.4 | UI auto-fill indicators | ✅ Complete | `AutoFillIndicator` widget, bulk apply/clear actions |
| 5.5 | Context hydration | ✅ Complete | Builder reads cache from FieldRegistryService via context |

### ~~Priority: Critical (Must Fix for Phase 5 Completion)~~ RESOLVED

#### ~~8. Carry-Forward Cache Never Populated~~ ✅ FIXED (Session 160)
**File**: `lib/features/toolbox/data/services/auto_fill_context_builder.dart`
**Resolution**: Added `includeCarryForward` parameter, reads `FieldRegistryService.getCarryForwardCache(projectId)` from Provider context.

---

#### ~~9. No Write Path for Carry-Forward Cache~~ ✅ FIXED (Session 160)
**Files**: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`, `lib/features/toolbox/data/services/field_registry_service.dart`
**Resolution**: Added `updateCarryForwardCache()` method to FieldRegistryService, called from `FormFillScreen._saveForm()` on successful save.

---

#### ~~10. Missing "Use Last Value" Toggle Per Form~~ ✅ FIXED (Session 160)
**File**: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`
**Resolution**: Added `_useCarryForward` state (defaults from global setting), toggle in auto-fill menu, controls both read and write paths.

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
| ~~5 (Completion)~~ | ~~8, 9, 10~~ | ~~Critical carry-forward completion~~ ✅ DONE |
| 6 | 12, 13, 15 | State consolidation, async safety |
| 9 | 11 | Test updates for auto-fill engine |
| 14 | 1, 2, 3, 4, 5, 6, 7, 14, 16 | DRY/KISS Utilities + shared patterns |
| 7 | 17 | UX confidence indicators |

---

## Phase 6 Code Review - 2026-01-28 (Session 161)

**Commits Reviewed**: `16edc36`
**Scope**: Calculation Engine + 0582B Density Automation
**Overall**: ✅ **PASS** - All 9 files pass code review

### Phase 6 Requirements Verification

| Step | Requirement | Status | Notes |
|------|-------------|--------|-------|
| 6.1 | Safe calculation service | ✅ Complete | `FormCalculationService` + `DensityCalculatorService` |
| 6.2 | Registry-driven calculations | ✅ Complete | `DynamicFormField` + `form_fill_screen` recalculation |
| 6.3 | 0582B field definitions + tests | ✅ Complete | 25 fields in JSON, 115 new tests |
| 6.4 | Align density field naming | ✅ Complete | Standardized + backward compat via synonyms |

### File Assessment Summary

| File | Verdict | Notes |
|------|---------|-------|
| `form_calculation_service.dart` | ✅ PASS | Excellent whitelist security, recursive descent parser |
| `density_calculator_service.dart` | ✅ PASS | Clean domain abstraction, proper DI |
| `dynamic_form_field.dart` | ✅ PASS | Good calculated field UI with toggle |
| `form_fill_screen.dart` | ✅ PASS | Proper mounted checks, good state management |
| `services.dart` | ✅ PASS | Proper barrel exports with hide workaround |
| `main.dart` | ✅ PASS | Service properly registered |
| `mdot_0582b_density.json` | ✅ PASS | Well-structured 25 fields with formulas |
| `form_seed_service.dart` | ✅ PASS | Good fallback strategy |
| `form_parsing_service.dart` | ✅ PASS | Excellent regex documentation |

### Redundancies Identified

#### 18. Duplicate CalculationResult Classes (LOW PRIORITY)
**Files**: `form_calculation_service.dart:19`, `calculator_service.dart:65`
**Issue**: Two different classes with same name, requiring `hide` in barrel export
**Recommendation**: Rename to `FormCalculationResult` vs `CalculationResult`
**Target Phase**: 14

---

#### 19. Auto-Fill Context Building Duplication (LOW PRIORITY)
**File**: `lib/features/toolbox/presentation/screens/form_fill_screen.dart:164-264`
**Issue**: `_autoFillFromContext()` and `_autoFillAll()` share ~80% identical code
**Recommendation**: Extract common method with `forceOverwrite` parameter
**Target Phase**: 14

---

#### 20. Magic Numbers for Compaction Spec Ranges (LOW PRIORITY)
**File**: `lib/features/toolbox/data/services/density_calculator_service.dart:251-260`
**Issue**: Hardcoded 95, 98, 102, 105 spec values
**Recommendation**: Extract to named constants (e.g., `kMinCompaction = 95`)
**Target Phase**: 14

---

### Test Coverage Assessment

| Service | Test File | Coverage |
|---------|-----------|----------|
| `form_calculation_service.dart` | ✅ 55 tests | Excellent - arithmetic, precedence, security |
| `density_calculator_service.dart` | ✅ 45 tests | Excellent - all calculations, real-world |
| `form_seed_service.dart` | ✅ 15 tests | Good - JSON validation, field definitions |
| `dynamic_form_field.dart` | Gap | Widget tests needed (future) |
| `form_fill_screen.dart` | Gap | Integration tests needed (future) |

### Security Assessment

| Check | Status |
|-------|--------|
| Whitelist-only characters in formulas | ✅ PASS |
| No code injection vectors | ✅ PASS |
| Input validation at boundaries | ✅ PASS |

### Positive Observations

1. **Excellent Security**: Whitelist pattern rejects injection attempts (tests at lines 261-275)
2. **Domain Knowledge**: `DensityCalculatorService` has proper MDOT spec awareness (95-105%)
3. **Proper DI**: Services inject dependencies, testable architecture
4. **Good Documentation**: Regex patterns well-documented with examples
5. **Backward Compatibility**: Parsing service supports both `target_density` and `max_density`

### Updated Summary by Target Phase

| Phase | Items | Description |
|-------|-------|-------------|
| 6 | 12, 13, 15 | State consolidation, async safety |
| 9 | 11 | Test updates for auto-fill engine |
| 14 | 1-7, 14, 16, 18-20 | DRY/KISS Utilities + redundancy fixes |
| 7 | 17 | UX confidence indicators |

### Review History Update

| Date | Session | Reviewer | Scope |
|------|---------|----------|-------|
| 2026-01-28 | 161 | code-review-agent | Phase 6 (Calculations) |
| 2026-01-28 | 159 | code-review-agent | Phase 5 (Auto-Fill) |
| 2026-01-28 | 156 | code-review-agent | Phases 3 & 4 |
