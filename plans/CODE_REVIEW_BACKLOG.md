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
| 2026-01-28 | 156 | code-review-agent | Phases 3 & 4 |
