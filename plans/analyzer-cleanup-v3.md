# Analyzer Cleanup Plan v3

**Session**: 248
**Issues**: 30 analyzer warnings/info (VS Code may show 34 with additional hints)
**Goal**: Fix all analyzer issues to achieve clean build

## Issue Summary

| Category | Count | Severity | Files |
|----------|-------|----------|-------|
| `use_build_context_synchronously` | 1 | info | Production code |
| `unnecessary_null_comparison` | 21 | warning | Test files |
| `prefer_function_declarations_over_variables` | 5 | info | Test files |
| `unnecessary_nullable_for_final_variable_declarations` | 2 | info | Test files |
| `use_super_parameters` | 1 | info | Test helpers |

## Phase 1: Production Code Fix

**File**: `lib/features/entries/presentation/screens/entry_wizard_screen.dart:1942-1949`

**Issue**: Context used after mounted check but the analyzer sees them as "unrelated" because the context is accessed inside the `if` block after the check.

**Current Code**:
```dart
if (!context.mounted) return;
if (confirmed == true) {
  final formProvider = context.read<InspectorFormProvider>();
  await formProvider.deleteResponse(response.id);
  setState(() { ... });
}
```

**Fix**: Move context.read before the await to satisfy analyzer:
```dart
if (!context.mounted) return;
if (confirmed == true) {
  final formProvider = context.read<InspectorFormProvider>();
  await formProvider.deleteResponse(response.id);
  if (!mounted) return;  // Add check after await
  setState(() { ... });
}
```

## Phase 2: Test Null Comparison Fixes (21 issues)

These tests intentionally test null vs non-null state transitions. The tests are valid but the analyzer flags the comparisons.

**Strategy**: Add targeted ignores where the test pattern is intentional.

### entry_wizard_screen_test.dart (5 fixes)
| Line | Issue | Fix |
|------|-------|-----|
| 25 | `selectedLocationId != null` always false | Add ignore comment |
| 29 | `selectedLocationId != null` always true | Add ignore comment |
| 463 | Nullable type unnecessary | Change `final String? entryId` to `final String entryId` |
| 481 | `selectedLocationId != null` always false | Add ignore comment |
| 491 | `selectedLocationId != null` always true | Add ignore comment |

### project_setup_screen_test.dart (8 fixes)
| Lines | Pattern | Fix |
|-------|---------|-----|
| 54, 145, 229, 318, 328, 338 | `varName != null` always false | Add ignore comments |
| 452, 478 | `varName != null` always true | Add ignore comments |

### quantities_screen_test.dart (2 fixes)
| Line | Issue | Fix |
|------|-------|-----|
| 507 | `projectId != null` always false | Add ignore comment |
| 514 | `projectId != null` always true | Add ignore comment |

### calculator_screen_test.dart (2 null comparison fixes)
| Line | Issue | Fix |
|------|-------|-----|
| 323 | `result == null` always true | Add ignore comment |
| 330 | `result != null` always true | Add ignore comment |

### gallery_screen_test.dart (3 fixes)
| Line | Issue | Fix |
|------|-------|-----|
| 106, 143 | `selectedEntryId == null` always false | Add ignore comment |
| 306 | `selectedEntryId != null` always true | Add ignore comment |

### todos_screen_test.dart (3 fixes)
| Line | Issue | Fix |
|------|-------|-----|
| 484, 492 | `todo != null` always true | Add ignore comments |
| 547 | Nullable type unnecessary | Change `final DateTime? hasDueDate` to `final DateTime hasDueDate` |

## Phase 3: Function Declaration Fixes (5 issues)

**File**: `test/features/toolbox/presentation/screens/calculator_screen_test.dart`

Convert lambda assignments to function declarations:

| Line | Current | Fix |
|------|---------|-----|
| 275 | `final areaValidator = (String? value) => ...` | `String? areaValidator(String? value) => ...` |
| 284 | `final thicknessValidator = (String? value) => ...` | `String? thicknessValidator(String? value) => ...` |
| 293 | `final densityValidator = (String? value) => ...` | `String? densityValidator(String? value) => ...` |
| 302 | `final lengthValidator = (String? value) => ...` | `String? lengthValidator(String? value) => ...` |
| 311 | `final widthValidator = (String? value) => ...` | `String? widthValidator(String? value) => ...` |

## Phase 4: Super Parameters Fix (1 issue)

**File**: `test/golden/test_helpers.dart:127`

**Current**:
```dart
TolerantGoldenFileComparator(Uri testFile) : super(testFile);
```

**Fix**:
```dart
TolerantGoldenFileComparator(super.testFile);
```

## Files to Modify

| File | Changes |
|------|---------|
| `lib/features/entries/presentation/screens/entry_wizard_screen.dart` | 1 fix |
| `test/features/entries/presentation/screens/entry_wizard_screen_test.dart` | 5 fixes |
| `test/features/projects/presentation/screens/project_setup_screen_test.dart` | 8 fixes |
| `test/features/quantities/presentation/screens/quantities_screen_test.dart` | 2 fixes |
| `test/features/toolbox/presentation/screens/calculator_screen_test.dart` | 7 fixes |
| `test/features/toolbox/presentation/screens/gallery_screen_test.dart` | 3 fixes |
| `test/features/toolbox/presentation/screens/todos_screen_test.dart` | 3 fixes |
| `test/golden/test_helpers.dart` | 1 fix |

**Total**: 8 files, 30 fixes

## Verification

1. Run `pwsh -Command "flutter analyze"` - expect 0 issues
2. Run `pwsh -Command "flutter test"` - ensure tests still pass
3. Commit with message: `fix: resolve 30 analyzer warnings (tests + async safety)`

## Execution Order

1. Phase 1 (production code) - highest priority
2. Phase 4 (super_parameters) - simple single fix
3. Phase 3 (function declarations) - 5 straightforward conversions
4. Phase 2 (null comparisons) - 21 ignore comments
5. Verify & commit
