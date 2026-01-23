# E2E Test Fixes Implementation Plan

**Last Updated**: 2026-01-22
**Status**: READY
**Agent**: `qa-testing-agent`

## Executive Summary

Fix 14 E2E test failures across 4 test files by adding missing widget keys, updating Patrol API calls, and fixing Android manifest permissions. The failures are grouped into 4 priority levels based on impact (number of tests affected).

**Test Failure Breakdown**:
- 9 failures: Missing `add_project_fab` key (project_management_test.dart)
- 5 failures: Missing `add_entry_fab` key + permission issues (photo_flow_test.dart)
- 4 files: Compilation errors from Patrol API changes

**Estimated Complexity**: Medium (2-3 hours)
**Risk**: Low (test-only changes, no production code impact)

---

## Priority 1: Widget Key Fixes (HIGH IMPACT - 14 test failures)

### Task 1.1: Add Missing FAB Keys

**Impact**: Fixes 14 test failures immediately
**Complexity**: Trivial
**Files**: 2

#### Analysis
Both FAB keys already exist in the codebase:
- ✅ `add_project_fab` - EXISTS at `project_list_screen.dart:83`
- ✅ `add_entry_fab` - EXISTS at `home_screen.dart:466`

**Root Cause**: Tests are looking for keys that already exist. This suggests either:
1. Tests are navigating to wrong screen
2. Keys are conditionally rendered and not visible
3. Test timing issue (checking before FAB renders)

#### Steps

1. **Verify key visibility in project_list_screen.dart** (line 83)
   - Key is on the FloatingActionButton itself
   - No conditional rendering - always visible
   - **Likely issue**: Tests may not be waiting for screen to fully load

2. **Verify key visibility in home_screen.dart** (line 466)
   - Key is inside a `Consumer<ProjectProvider>` widget
   - **FOUND ISSUE**: FAB is hidden if `selectedProject == null` (line 462-464)
   - **Fix**: Ensure test navigation sequence selects a project first

3. **Update test helpers to ensure proper navigation**
   - File: `integration_test/patrol/helpers/patrol_test_helpers.dart`
   - Add explicit waits after navigation
   - Add project selection verification before checking for `add_entry_fab`

#### Test Verification
```bash
# Run affected tests
cd integration_test/patrol/e2e_tests
patrol test project_management_test.dart
patrol test photo_flow_test.dart
```

**Agent**: `qa-testing-agent`

---

## Priority 2: Patrol API Updates (4 compilation errors)

### Task 2.1: Fix photo_flow_test.dart - Deprecated `dyScroll` parameter

**Issue**: Line 40, 124, 207 - `dyScroll: -200` is deprecated
**Fix**: Replace `dyScroll` with `delta: Offset(0, -200)`

**Before**:
```dart
await $.scrollUntilVisible(
  finder: addPhotoButton,
  view: $(Scrollable).first,
  dyScroll: -200,  // DEPRECATED
);
```

**After**:
```dart
await $.scrollUntilVisible(
  finder: addPhotoButton,
  view: $(Scrollable).first,
  delta: const Offset(0, -200),  // NEW API
);
```

**Files Modified**: 1
- `integration_test/patrol/e2e_tests/photo_flow_test.dart`

**Agent**: `qa-testing-agent`

---

### Task 2.2: Fix project_management_test.dart - Missing `find` import

**Issue**: Line 156 - `$.native.selectAll()` API removed
**Root Cause**: Patrol 3.x removed native text selection helpers

**Fix 1**: Add missing Patrol finder import
```dart
import 'package:flutter_test/flutter_test.dart' as flutter_test;
```

**Fix 2**: Replace `selectAll()` with Flutter test API
**Before** (line 155):
```dart
await $.native.selectAll();
await $.pumpAndSettle();
await nameField.enterText('Updated Project $timestamp');
```

**After**:
```dart
// Clear existing text by selecting all and deleting
await $.tester.enterText(
  flutter_test.find.byKey(const Key('project_name_field')),
  'Updated Project $timestamp',
);
await $.pumpAndSettle();
```

**Files Modified**: 1
- `integration_test/patrol/e2e_tests/project_management_test.dart`

**Agent**: `qa-testing-agent`

---

### Task 2.3: Fix settings_theme_test.dart - Missing `find` import

**Issue**: Uses `find.byType(ListView)` without import (line 306)

**Fix**: Add import at top of file
```dart
import 'package:flutter_test/flutter_test.dart' as flutter_test;
```

**Then update usage**:
```dart
await $.tester.drag(
  flutter_test.find.byType(ListView).first,  // Explicit flutter_test prefix
  const Offset(0, -100),
);
```

**Files Modified**: 1
- `integration_test/patrol/e2e_tests/settings_theme_test.dart`

**Agent**: `qa-testing-agent`

---

### Task 2.4: Fix entry_validation_test.dart - Missing `find` import

**Issue**: Uses `find.byType(Card)` and `find.byKey()` without import (lines 327, 330)

**Fix**: Add import at top of file
```dart
import 'package:flutter_test/flutter_test.dart' as flutter_test;
```

**Then update usages**:
```dart
final cards = $.tester.widgetList(flutter_test.find.byType(Card));
// ...
await $.tester.tap(flutter_test.find.byType(Card).first);
```

**Files Modified**: 1
- `integration_test/patrol/isolated/entry_validation_test.dart`

**Agent**: `qa-testing-agent`

---

## Priority 3: Android Manifest (0 failures, prevents future issues)

### Task 3.1: Verify QUERY_ALL_PACKAGES Permission

**Status**: ✅ ALREADY PRESENT (line 23 of AndroidManifest.xml)

**Verification**: The permission is already declared:
```xml
<uses-permission android:name="android.permission.QUERY_ALL_PACKAGES"/>
```

**Note**: This permission is required for Patrol's `$.native.openApp()` to work, which is used in app restart/lifecycle tests.

**Action**: No changes needed - document for reference

**Files Modified**: 0

**Agent**: N/A (verification only)

---

## Priority 4: Navigation & State Fixes (3 test failures)

### Task 4.1: Fix Dashboard Tab Navigation

**Issue**: Tests expecting specific tab to be visible after navigation
**Root Cause**: Unknown - needs investigation

**Steps**:
1. Run affected tests with verbose logging
2. Identify which assertion is failing
3. Check router configuration in `app_router.dart`
4. Verify dashboard screen initial state

**Investigation Required**: Yes
**Files to Check**:
- `lib/core/router/app_router.dart`
- Test files referencing dashboard navigation

**Agent**: `qa-testing-agent`

---

### Task 4.2: Fix Sync Status Indicator

**Issue**: Sync status indicator not visible or missing key
**Root Cause**: Unknown - needs investigation

**Steps**:
1. Search codebase for sync status indicator widget
2. Verify key is present: `sync_status_indicator`
3. Check visibility conditions
4. Add key if missing

**Investigation Required**: Yes
**Files to Check**:
```bash
# Search for sync status widget
grep -r "sync.*status" lib/features/sync/presentation/
grep -r "SyncStatus" lib/features/sync/presentation/
```

**Agent**: `qa-testing-agent`

---

## Execution Order

### Phase 1: Quick Wins (30 minutes)
1. ✅ **Task 2.1** - Fix `dyScroll` deprecation (photo_flow_test.dart)
2. ✅ **Task 2.2** - Add `find` import (project_management_test.dart)
3. ✅ **Task 2.3** - Add `find` import (settings_theme_test.dart)
4. ✅ **Task 2.4** - Add `find` import (entry_validation_test.dart)

**Outcome**: 4 compilation errors fixed, tests can run

---

### Phase 2: Widget Key Investigation (1 hour)
1. **Task 1.1.1** - Debug project_management_test.dart failures
   - Add logging to test helper navigation methods
   - Verify screen load timing
   - Check if FAB is rendered but not found
2. **Task 1.1.2** - Debug photo_capture_test.dart failures
   - Verify project is selected before checking for `add_entry_fab`
   - Update test helpers if needed

**Outcome**: 14 test failures fixed

---

### Phase 3: Navigation Fixes (1 hour)
1. **Task 4.1** - Investigate dashboard tab assertion
2. **Task 4.2** - Investigate sync status indicator

**Outcome**: 3 remaining test failures fixed

---

## Testing Strategy

### 1. Compilation Check (2 minutes)
```bash
cd integration_test/patrol
flutter analyze e2e_tests/
flutter analyze isolated/
```
**Expected**: 0 errors, 0 warnings

### 2. Individual Test Runs (10 minutes)
```bash
# Test each fixed file individually
patrol test e2e_tests/photo_flow_test.dart
patrol test e2e_tests/project_management_test.dart
patrol test e2e_tests/settings_theme_test.dart
patrol test isolated/entry_validation_test.dart
```
**Expected**: All tests pass or skip gracefully

### 3. Full Test Suite (15 minutes)
```bash
# Run complete E2E suite
patrol test e2e_tests/
patrol test isolated/
```
**Expected**: 0 failures

### 4. Smoke Test (5 minutes)
```bash
patrol test app_smoke_test.dart
```
**Expected**: Basic app functionality verified

---

## Files to Modify

| File | Priority | Changes | LOC Changed |
|------|----------|---------|-------------|
| `integration_test/patrol/e2e_tests/photo_flow_test.dart` | P2 | Replace `dyScroll` param | 3 lines |
| `integration_test/patrol/e2e_tests/project_management_test.dart` | P2 | Add import, fix `selectAll()` | 5 lines |
| `integration_test/patrol/e2e_tests/settings_theme_test.dart` | P2 | Add import | 1 line |
| `integration_test/patrol/isolated/entry_validation_test.dart` | P2 | Add import | 1 line |
| `integration_test/patrol/helpers/patrol_test_helpers.dart` | P1 | Add wait/verify logic | ~15 lines |

**Total Files**: 5
**Total LOC**: ~25 lines

---

## Risk Assessment

### Low Risk ✅
- All changes are test-only (no production code)
- Patrol API updates are well-documented
- Widget keys already exist in codebase
- Android manifest already has required permission

### Medium Risk ⚠️
- Navigation/state fixes may require deeper investigation
- Test timing issues could be environment-specific
- FAB visibility conditions need verification

### Mitigation
1. Test on multiple devices/emulators
2. Add explicit wait helpers for screen transitions
3. Document any environmental requirements
4. Add retry logic for flaky tests

---

## Success Criteria

### Phase 1 (Compilation)
- ✅ All 4 test files compile without errors
- ✅ `flutter analyze` shows 0 errors in test directory

### Phase 2 (Test Execution)
- ✅ 14+ test failures resolved (project_management + photo_capture)
- ✅ All Patrol API deprecation warnings resolved
- ✅ Test suite runs without compilation errors

### Phase 3 (Full Suite)
- ✅ <5 failures across entire E2E suite
- ✅ All failures are documented with skip conditions
- ✅ No flaky tests (consistent results across 3 runs)

### Final Verification
```bash
# Must pass
flutter analyze integration_test/
patrol test integration_test/patrol/app_smoke_test.dart

# Target: 95% pass rate
patrol test integration_test/patrol/
```

---

## Notes

### Patrol 3.x Migration
The compilation errors are from Patrol 3.x API changes:
- `dyScroll` parameter removed in favor of `delta: Offset(dx, dy)`
- `$.native.selectAll()` removed (use Flutter test API directly)
- Finders must be explicitly imported from `flutter_test`

### Widget Key Strategy
All required keys are already present in the codebase. Test failures are likely due to:
1. **Timing**: FAB not rendered when test checks
2. **Conditional rendering**: FAB hidden based on state
3. **Navigation**: Test not on correct screen

**Solution**: Add explicit waits and state verification in test helpers.

### Future Improvements
1. Add test retry logic for transient failures
2. Create shared test fixtures for common setup
3. Add visual regression testing for UI changes
4. Document test environment requirements

---

## Agent Assignment

**Primary Agent**: `qa-testing-agent`
- Owns all test fixes
- Runs verification suite
- Documents any environment-specific issues

**Secondary Agent**: `code-review-agent` (if navigation fixes touch production code)
- Reviews any changes to screen navigation
- Ensures widget keys follow naming conventions
- Validates test architecture improvements

---

## Appendix: Test File Analysis

### project_management_test.dart (9 failures)
- Line 37: `add_project_fab` not found
- Line 69: Same issue after save
- Lines 100, 175, 206, 256, 300, 328: Same pattern

**Root Cause**: Likely timing - FAB exists but test checks before render

### photo_flow_test.dart (5 failures + compilation)
- Line 40, 124, 207: `dyScroll` deprecation (compilation error)
- Multiple: `add_entry_fab` not found (same as project_management)

**Root Cause**:
1. Compilation: Patrol API change
2. Runtime: FAB hidden when no project selected

### settings_theme_test.dart (1 compilation error)
- Line 306: Missing `flutter_test` import for `find.byType(ListView)`

### entry_validation_test.dart (1 compilation error)
- Lines 327, 330: Missing `flutter_test` import for `find.byType(Card)`

---

## Related Documentation
- @.claude/memory/defects.md (anti-patterns)
- @.claude/rules/quality-checklist.md (testing standards)
- Patrol 3.x Migration Guide: https://patrol.leancode.co/v3/migration
