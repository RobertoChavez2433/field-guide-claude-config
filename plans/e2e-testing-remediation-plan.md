# E2E Testing Infrastructure Remediation Plan

**Created**: 2026-01-22
**Status**: READY
**Priority**: CRITICAL - Test infrastructure is broken, many tests excluded from execution

## Overview

The E2E test infrastructure has multiple critical issues preventing reliable test execution:
1. Test bundle excludes 11 test files (e2e_tests/ and isolated/ directories)
2. Navigation helpers use incorrect widget keys
3. Confirmation dialogs have inconsistent cancel button keys
4. No centralized testing keys file (causes key drift)
5. Golden test comparator not wired up
6. Multiple committed golden test failure images

This plan fixes all issues in dependency order, ensuring test reliability and maintainability.

---

## Phase 1: Foundation - Centralized Testing Keys (CRITICAL)

**Goal**: Create single source of truth for all test widget keys to prevent future drift.

### Task 1.1: Create Centralized Testing Keys File

**Effort**: Medium
**Agent**: flutter-specialist-agent

#### Summary
Create `lib/shared/testing_keys.dart` with all widget keys used across the app. This prevents key mismatches between implementation and tests.

#### Steps
1. Create new file `lib/shared/testing_keys.dart`
2. Define static const keys for:
   - Bottom navigation buttons (dashboard, calendar, projects, settings)
   - FABs (add_entry_fab, add_project_fab)
   - Dialog buttons (confirmation, delete, cancel variants)
   - Screen identifiers (entry_wizard, settings, etc.)
   - Entry wizard fields and buttons
3. Group keys by feature/category with documentation
4. Export from `lib/shared/shared.dart` barrel file

#### Implementation Details

**File**: `lib/shared/testing_keys.dart` (NEW)

```dart
/// Centralized testing keys for UI widgets
///
/// This file is the single source of truth for all widget keys used in tests.
/// Update this file when adding new testable widgets.
class TestingKeys {
  // Bottom Navigation
  static const bottomNavigationBar = Key('bottom_navigation_bar');
  static const dashboardNavButton = Key('dashboard_nav_button');
  static const calendarNavButton = Key('calendar_nav_button');
  static const projectsNavButton = Key('projects_nav_button');
  static const settingsNavButton = Key('settings_nav_button');

  // Floating Action Buttons
  static const addEntryFab = Key('add_entry_fab');
  static const addProjectFab = Key('add_project_fab');

  // Confirmation Dialogs
  static const confirmationDialog = Key('confirmation_dialog');
  static const confirmDialogButton = Key('confirm_dialog_button');
  static const cancelDialogButton = Key('cancel_dialog_button'); // Generic cancel
  static const deleteConfirmButton = Key('delete_confirm_button');
  static const confirmationDialogCancel = Key('confirmation_dialog_cancel'); // Delete dialog cancel

  // Unsaved Changes Dialog
  static const unsavedChangesDialog = Key('unsaved_changes_dialog');
  static const unsavedChangesCancel = Key('unsaved_changes_cancel');
  static const discardDialogButton = Key('discard_dialog_button');

  // Entry Wizard
  static const entryWizardClose = Key('entry_wizard_close');
  static const entryWizardSaveDraft = Key('entry_wizard_save_draft');
  static const entryWizardSubmit = Key('entry_wizard_submit');

  // Project Management
  static const projectSaveButton = Key('project_save_button');
  static const projectsList = Key('projects_list');

  // Settings
  static const settingsSignOutButton = Key('settings_sign_out_button');

  // Authentication
  static const loginEmailField = Key('login_email_field');
  static const loginPasswordField = Key('login_password_field');
  static const loginSignInButton = Key('login_sign_in_button');

  // Photo Capture
  static const photoCaptureCamera = Key('photo_capture_camera');
  static const photoCaptureGallery = Key('photo_capture_gallery');

  // Screen Identifiers
  static const homeScreen = Key('home_screen');
}
```

**File**: `lib/shared/shared.dart`
- Add export: `export 'testing_keys.dart';`

#### Files to Modify

| File | Changes |
|------|---------|
| `lib/shared/testing_keys.dart` | CREATE - Centralized keys |
| `lib/shared/shared.dart` | Add export for testing_keys.dart |

#### Verification
1. `flutter analyze` - No errors
2. Keys compile and are accessible via `import 'package:construction_inspector/shared/shared.dart'`

---

## Phase 2: UI Implementation - Fix Widget Keys (CRITICAL)

**Goal**: Update all widget implementations to use centralized keys from TestingKeys class.

### Task 2.1: Fix Bottom Navigation Keys

**Effort**: Small
**Agent**: flutter-specialist-agent

#### Summary
Update `ScaffoldWithNavBar` to use TestingKeys constants instead of string-based keys.

#### Steps
1. Import `package:construction_inspector/shared/shared.dart` in `lib/core/router/app_router.dart`
2. Replace `Key('dashboard_nav_button')` with `TestingKeys.dashboardNavButton`
3. Replace `Key('calendar_nav_button')` with `TestingKeys.calendarNavButton`
4. Replace `Key('projects_nav_button')` with `TestingKeys.projectsNavButton`
5. Replace `Key('settings_nav_button')` with `TestingKeys.settingsNavButton`
6. Replace `Key('bottom_navigation_bar')` with `TestingKeys.bottomNavigationBar`

#### Files to Modify

| File | Changes |
|------|---------|
| `lib/core/router/app_router.dart` | Lines ~150-200: Replace navigation destination keys with TestingKeys |

#### Verification
1. `flutter analyze` - No errors
2. Manual test: Navigate between tabs using bottom navigation
3. All 4 tabs accessible

---

### Task 2.2: Standardize Confirmation Dialog Cancel Keys

**Effort**: Medium
**Agent**: flutter-specialist-agent

#### Summary
Fix the three different cancel button keys in confirmation_dialog.dart to use consistent naming from TestingKeys.

**Current state**:
- Line 33: `cancel_dialog_button` (generic)
- Line 77: `confirmation_dialog_cancel` (delete)
- Line 132: `unsaved_changes_cancel` (unsaved changes)

**Target state**:
- Generic dialog: `TestingKeys.cancelDialogButton`
- Delete dialog: `TestingKeys.confirmationDialogCancel`
- Unsaved changes: `TestingKeys.unsavedChangesCancel`

#### Steps
1. Import TestingKeys in `lib/shared/widgets/confirmation_dialog.dart`
2. Line 33: Replace `Key('cancel_dialog_button')` with `TestingKeys.cancelDialogButton`
3. Line 77: Replace `Key('confirmation_dialog_cancel')` with `TestingKeys.confirmationDialogCancel`
4. Line 132: Replace `Key('unsaved_changes_cancel')` with `TestingKeys.unsavedChangesCancel`
5. Update other dialog keys (confirm buttons, dialog containers)

#### Files to Modify

| File | Changes |
|------|---------|
| `lib/shared/widgets/confirmation_dialog.dart` | Lines 20,33,66,77,125,132,137,142: Replace hardcoded keys with TestingKeys |

#### Verification
1. `flutter analyze` - No errors
2. Manual test: Open and dismiss each dialog type
3. Cancel buttons work correctly

---

### Task 2.3: Update FAB and Other Widget Keys

**Effort**: Small
**Agent**: flutter-specialist-agent

#### Summary
Update FABs and other common widgets to use TestingKeys.

#### Steps
1. Find all `Key('add_entry_fab')` usages
2. Replace with `TestingKeys.addEntryFab`
3. Find all `Key('add_project_fab')` usages
4. Replace with `TestingKeys.addProjectFab`
5. Update entry wizard, settings, auth screen keys

#### Files to Modify

| File | Changes |
|------|---------|
| `lib/features/entries/presentation/screens/home_screen.dart` | Replace add_entry_fab key |
| `lib/features/projects/presentation/screens/project_list_screen.dart` | Replace add_project_fab key |
| `lib/features/entries/presentation/screens/entry_wizard_screen.dart` | Replace entry wizard keys |
| `lib/features/settings/presentation/screens/settings_screen.dart` | Replace settings keys |
| `lib/features/auth/presentation/screens/*.dart` | Replace auth keys |

#### Verification
1. `flutter analyze` - No errors
2. Grep for remaining hardcoded test keys (should only find legacy references in tests)

---

## Phase 3: Test Infrastructure - Fix Test Helpers (CRITICAL)

**Goal**: Update all test helpers to use correct keys and reference TestingKeys class.

### Task 3.1: Fix Navigation Helper Keys

**Effort**: Small
**Agent**: qa-testing-agent

#### Summary
Update `navigation_helper.dart` to use correct navigation button keys.

**Current issues**:
- Line 13: `$(#nav_home)` - doesn't exist
- Line 19: `$(#nav_projects)` - doesn't exist
- Line 25: `$(#nav_dashboard)` - doesn't exist

**Correct keys**: `calendar_nav_button`, `projects_nav_button`, `dashboard_nav_button`

#### Steps
1. Update imports to include TestingKeys
2. Line 13: Replace `$(#nav_home)` with `$(TestingKeys.calendarNavButton)`
3. Line 19: Replace `$(#nav_projects)` with `$(TestingKeys.projectsNavButton)`
4. Line 25: Replace `$(#nav_dashboard)` with `$(TestingKeys.dashboardNavButton)`
5. Add settings navigation method using `TestingKeys.settingsNavButton`

#### Files to Modify

| File | Changes |
|------|---------|
| `integration_test/helpers/navigation_helper.dart` | Lines 1,13,19,25: Fix navigation keys, add import |

#### Verification
1. File compiles without errors
2. All navigation methods reference valid keys

---

### Task 3.2: Fix Auth Test Helper Settings Navigation

**Effort**: Small
**Agent**: qa-testing-agent

#### Summary
Fix `auth_test_helper.dart` line 53 which uses non-existent `#nav_settings` key.

#### Steps
1. Import TestingKeys
2. Line 53: Replace `$(#nav_settings)` with `$(TestingKeys.settingsNavButton)`

#### Files to Modify

| File | Changes |
|------|---------|
| `integration_test/helpers/auth_test_helper.dart` | Lines 1,53: Add import, fix settings nav key |

#### Verification
1. File compiles
2. signOut() method references correct key

---

### Task 3.3: Fix Patrol Test Helpers Dialog Handling

**Effort**: Medium
**Agent**: qa-testing-agent

#### Summary
Update `patrol_test_helpers.dart` to handle all three cancel button variants.

**Current state**: Line 543 only knows about `confirmation_dialog_cancel`

**Target**: Support all three cancel keys based on dialog type

#### Steps
1. Import TestingKeys
2. Update `handleConfirmationDialog()` method (lines 525-551)
3. Add parameter `DialogType dialogType = DialogType.generic` enum
4. Switch on dialog type to use correct cancel key:
   - Generic: `TestingKeys.cancelDialogButton`
   - Delete: `TestingKeys.confirmationDialogCancel`
   - UnsavedChanges: `TestingKeys.unsavedChangesCancel`
5. Update confirm button handling to use TestingKeys

#### Files to Modify

| File | Changes |
|------|---------|
| `integration_test/patrol/helpers/patrol_test_helpers.dart` | Lines 1,525-551: Add import, update handleConfirmationDialog with DialogType enum |

#### Implementation Detail

```dart
enum DialogType { generic, delete, unsavedChanges }

Future<void> handleConfirmationDialog({
  bool confirm = true,
  bool isDelete = false, // DEPRECATED: Use dialogType instead
  DialogType dialogType = DialogType.generic,
}) async {
  $.log('Handling confirmation dialog (confirm: $confirm)');

  if (confirm) {
    final deleteButton = $(TestingKeys.deleteConfirmButton);
    final confirmButton = $(TestingKeys.confirmDialogButton);

    if (isDelete && deleteButton.exists) {
      await deleteButton.tap();
    } else if (confirmButton.exists) {
      await confirmButton.tap();
    } else {
      throw StateError('No confirmation button found');
    }
  } else {
    // Determine correct cancel key based on dialog type
    final Key cancelKey;
    switch (dialogType) {
      case DialogType.delete:
        cancelKey = TestingKeys.confirmationDialogCancel;
        break;
      case DialogType.unsavedChanges:
        cancelKey = TestingKeys.unsavedChangesCancel;
        break;
      case DialogType.generic:
      default:
        cancelKey = TestingKeys.cancelDialogButton;
    }

    final cancelButton = $(cancelKey);
    if (!cancelButton.exists) {
      throw StateError('Cancel button not found for dialog type: $dialogType');
    }
    await cancelButton.tap();
  }

  await $.pumpAndSettle();
}
```

#### Verification
1. File compiles
2. All three dialog types can be handled
3. Backwards compatible with existing tests using `isDelete`

---

## Phase 4: Test Bundle - Include All Tests (CRITICAL)

**Goal**: Ensure all test files in e2e_tests/ and isolated/ directories are included in test_bundle.dart.

### Task 4.1: Update Test Bundle Generation

**Effort**: Medium
**Agent**: qa-testing-agent

#### Summary
Update `integration_test/test_bundle.dart` to include the 11 missing test files from e2e_tests/ and isolated/ directories.

**Currently excluded tests**:

**e2e_tests/** (5 files):
- `e2e_tests/entry_lifecycle_test.dart`
- `e2e_tests/offline_sync_test.dart`
- `e2e_tests/photo_flow_test.dart`
- `e2e_tests/project_management_test.dart`
- `e2e_tests/settings_theme_test.dart`

**isolated/** (6 files):
- `isolated/auth_validation_test.dart`
- `isolated/navigation_edge_test.dart`
- `isolated/entry_validation_test.dart`
- `isolated/app_lifecycle_test.dart`
- `isolated/camera_permission_test.dart`
- `isolated/location_permission_test.dart`

#### Steps
1. Add imports for all missing test files (lines 11-24 area)
2. Add group() calls for each test (lines 82-95 area)
3. Follow existing naming convention: `patrol.e2e_tests.{filename}` and `patrol.isolated.{filename}`
4. Regenerate bundle if using patrol CLI: `patrol build`

#### Files to Modify

| File | Changes |
|------|---------|
| `integration_test/test_bundle.dart` | Lines 11-24 (imports), 82-95 (groups): Add 11 missing test files |

#### Implementation Detail

**Add imports** (after line 24):
```dart
import 'patrol/e2e_tests/entry_lifecycle_test.dart' as patrol__e2e_tests__entry_lifecycle_test;
import 'patrol/e2e_tests/offline_sync_test.dart' as patrol__e2e_tests__offline_sync_test;
import 'patrol/e2e_tests/photo_flow_test.dart' as patrol__e2e_tests__photo_flow_test;
import 'patrol/e2e_tests/project_management_test.dart' as patrol__e2e_tests__project_management_test;
import 'patrol/e2e_tests/settings_theme_test.dart' as patrol__e2e_tests__settings_theme_test;
import 'patrol/isolated/auth_validation_test.dart' as patrol__isolated__auth_validation_test;
import 'patrol/isolated/navigation_edge_test.dart' as patrol__isolated__navigation_edge_test;
import 'patrol/isolated/entry_validation_test.dart' as patrol__isolated__entry_validation_test;
import 'patrol/isolated/app_lifecycle_test.dart' as patrol__isolated__app_lifecycle_test;
import 'patrol/isolated/camera_permission_test.dart' as patrol__isolated__camera_permission_test;
import 'patrol/isolated/location_permission_test.dart' as patrol__isolated__location_permission_test;
```

**Add groups** (after line 95):
```dart
group('patrol.e2e_tests.entry_lifecycle_test', patrol__e2e_tests__entry_lifecycle_test.main);
group('patrol.e2e_tests.offline_sync_test', patrol__e2e_tests__offline_sync_test.main);
group('patrol.e2e_tests.photo_flow_test', patrol__e2e_tests__photo_flow_test.main);
group('patrol.e2e_tests.project_management_test', patrol__e2e_tests__project_management_test.main);
group('patrol.e2e_tests.settings_theme_test', patrol__e2e_tests__settings_theme_test.main);
group('patrol.isolated.auth_validation_test', patrol__isolated__auth_validation_test.main);
group('patrol.isolated.navigation_edge_test', patrol__isolated__navigation_edge_test.main);
group('patrol.isolated.entry_validation_test', patrol__isolated__entry_validation_test.main);
group('patrol.isolated.app_lifecycle_test', patrol__isolated__app_lifecycle_test.main);
group('patrol.isolated.camera_permission_test', patrol__isolated__camera_permission_test.main);
group('patrol.isolated.location_permission_test', patrol__isolated__location_permission_test.main);
```

#### Verification
1. `flutter analyze integration_test/test_bundle.dart` - No errors
2. All imports resolve correctly
3. Test count increases from 12 to 23 tests

---

## Phase 5: Test Fixes - Update Individual Tests (HIGH PRIORITY)

**Goal**: Fix key mismatches in individual test files.

### Task 5.1: Fix Project Management Test Keys

**Effort**: Small
**Agent**: qa-testing-agent

#### Summary
Fix `project_management_test.dart` which uses `Key('projects_tab')` instead of correct `projects_nav_button`.

**Issues**:
- Line 28: `Key('projects_tab')` - doesn't exist
- Line 55: `Key('projects_tab')` - doesn't exist
- Line 87: `Key('projects_tab')` - doesn't exist
- Line 129: `Key('projects_tab')` - doesn't exist

#### Steps
1. Import TestingKeys
2. Replace all `Key('projects_tab')` with `TestingKeys.projectsNavButton`
3. Update any other hardcoded keys to use TestingKeys

#### Files to Modify

| File | Changes |
|------|---------|
| `integration_test/patrol/e2e_tests/project_management_test.dart` | Lines 1,28,55,87,129: Add import, replace projects_tab key |

#### Verification
1. File compiles
2. Test references correct navigation button key

---

### Task 5.2: Fix Offline Mode Test

**Effort**: Medium
**Agent**: qa-testing-agent

#### Summary
Fix `offline_mode_test.dart` issues:
- Line 25: Uses text finder `$('Home')` but UI label is 'Calendar'
- Missing authentication handling (test starts without login)

#### Steps
1. Import TestingKeys
2. Line 25: Replace `$('Home')` with `$(TestingKeys.calendarNavButton)`
3. Add authentication setup at test start:
   ```dart
   // Wait for app to load
   await Future.delayed(const Duration(seconds: 3));
   await $.pumpAndSettle();

   // Skip auth if not configured or already logged in
   final addEntryFab = $(TestingKeys.addEntryFab);
   if (!addEntryFab.exists) {
     // Assume we need to log in
     // This test requires auth to be bypassed or demo mode
     // For now, verify we're on a valid screen
   }
   ```
4. Replace hardcoded `Key('add_entry_fab')` with `TestingKeys.addEntryFab`

#### Files to Modify

| File | Changes |
|------|---------|
| `integration_test/patrol/offline_mode_test.dart` | Lines 1,25,36: Add import, fix navigation, add auth handling |

#### Verification
1. File compiles
2. Test references correct keys
3. Test handles auth state gracefully

---

### Task 5.3: Update All Other Tests to Use TestingKeys

**Effort**: Large
**Agent**: qa-testing-agent

#### Summary
Systematically replace all hardcoded `Key('...')` references in remaining test files with TestingKeys constants.

#### Steps
1. For each test file in `integration_test/patrol/`:
   - Import TestingKeys
   - Replace hardcoded navigation keys
   - Replace hardcoded dialog keys
   - Replace hardcoded FAB keys
   - Replace hardcoded screen identifier keys
2. Use grep to find all remaining hardcoded Key() references
3. Update or document any keys not in TestingKeys (add to TestingKeys if needed)

#### Files to Modify

| File | Changes |
|------|---------|
| `integration_test/patrol/app_smoke_test.dart` | Replace hardcoded keys with TestingKeys |
| `integration_test/patrol/auth_flow_test.dart` | Replace hardcoded keys with TestingKeys |
| `integration_test/patrol/camera_permission_test.dart` | Replace hardcoded keys with TestingKeys |
| `integration_test/patrol/contractors_flow_test.dart` | Replace hardcoded keys with TestingKeys |
| `integration_test/patrol/entry_management_test.dart` | Replace hardcoded keys with TestingKeys |
| `integration_test/patrol/location_permission_test.dart` | Replace hardcoded keys with TestingKeys |
| `integration_test/patrol/navigation_flow_test.dart` | Replace hardcoded keys with TestingKeys |
| `integration_test/patrol/photo_capture_test.dart` | Replace hardcoded keys with TestingKeys |
| `integration_test/patrol/quantities_flow_test.dart` | Replace hardcoded keys with TestingKeys |
| `integration_test/patrol/settings_flow_test.dart` | Replace hardcoded keys with TestingKeys |
| `integration_test/patrol/e2e_tests/*.dart` | Replace hardcoded keys with TestingKeys |
| `integration_test/patrol/isolated/*.dart` | Replace hardcoded keys with TestingKeys |

#### Verification
1. All test files compile
2. `grep -r "Key\('add_entry_fab'\)" integration_test/` returns no results
3. `grep -r "Key\('.*nav.*'\)" integration_test/` returns no results
4. All tests reference TestingKeys for common widgets

---

## Phase 6: Golden Tests - Wire Up Comparator (MEDIUM PRIORITY)

**Goal**: Enable tolerant golden file comparison and clean up failure images.

### Task 6.1: Create Flutter Test Config

**Effort**: Small
**Agent**: qa-testing-agent

#### Summary
Create `test/flutter_test_config.dart` to wire up the `TolerantGoldenFileComparator` that's defined but unused.

#### Steps
1. Create `test/flutter_test_config.dart`
2. Wire up TolerantGoldenFileComparator from test_helpers.dart
3. Configure tolerance threshold (0.1% as defined in test_helpers.dart)

#### Files to Modify

| File | Changes |
|------|---------|
| `test/flutter_test_config.dart` | CREATE - Wire up golden comparator |

#### Implementation Detail

```dart
import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'golden/test_helpers.dart';

Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  // Set up tolerant golden file comparator
  if (goldenFileComparator is LocalFileComparator) {
    final testUrl = (goldenFileComparator as LocalFileComparator).basedir;
    goldenFileComparator = TolerantGoldenFileComparator(testUrl);
  }

  await testMain();
}
```

#### Verification
1. File compiles
2. Golden tests use tolerant comparator
3. Run golden tests: `flutter test test/golden/`

---

### Task 6.2: Clean Up Golden Test Failure Images

**Effort**: Small
**Agent**: qa-testing-agent

#### Summary
Remove the 20 committed failure images from `test/golden/pdf/failures/` directory. These should not be committed to version control.

**Files to remove** (all in `test/golden/pdf/failures/`):
- All `*_masterImage.png` files
- All `*_testImage.png` files
- All `*_maskedDiff.png` files
- All `*_isolatedDiff.png` files

#### Steps
1. Delete all files in `test/golden/pdf/failures/` directory
2. Add `test/golden/pdf/failures/` to `.gitignore`
3. Verify directory is empty (or add .gitkeep if needed for structure)

#### Files to Modify

| File | Changes |
|------|---------|
| `.gitignore` | Add `test/golden/pdf/failures/` |
| `test/golden/pdf/failures/*.png` | DELETE all 20 files |

#### Verification
1. `git status` shows failures directory removed
2. Directory is in .gitignore
3. Golden tests regenerate failure images locally when needed

---

### Task 6.3: Update Golden Test Documentation

**Effort**: Small
**Agent**: qa-testing-agent

#### Summary
Document the golden test setup and tolerance configuration.

#### Steps
1. Update or create `test/golden/README.md`
2. Document tolerance threshold (0.1%)
3. Document how to update golden files
4. Document what to do with failure images (don't commit)

#### Files to Modify

| File | Changes |
|------|---------|
| `test/golden/README.md` | CREATE or UPDATE - Document golden test process |

#### Verification
1. README explains golden test workflow
2. Contributors know not to commit failure images

---

## Phase 7: Documentation Updates (LOW PRIORITY)

**Goal**: Update documentation to reflect infrastructure changes.

### Task 7.1: Update Test Documentation

**Effort**: Small
**Agent**: qa-testing-agent

#### Summary
Update test documentation to reference TestingKeys and new test organization.

#### Steps
1. Update `integration_test/patrol/REQUIRED_UI_KEYS.md` to reference TestingKeys class
2. Add note about using TestingKeys instead of hardcoded keys
3. Update any E2E test plan documentation

#### Files to Modify

| File | Changes |
|------|---------|
| `integration_test/patrol/REQUIRED_UI_KEYS.md` | Add reference to TestingKeys class |
| `.claude/docs/testing-guide.md` | Update if exists, or CREATE with testing best practices |

#### Verification
1. Documentation is clear and accurate
2. New contributors understand to use TestingKeys

---

### Task 7.2: Update Defects Log

**Effort**: Small
**Agent**: qa-testing-agent

#### Summary
Log the key mismatch pattern to `.claude/memory/defects.md` to prevent recurrence.

#### Steps
1. Add new defect entry above `<!-- Add new defects above this line -->`
2. Document the pattern of hardcoded test keys
3. Document prevention: always use TestingKeys class

#### Files to Modify

| File | Changes |
|------|---------|
| `.claude/memory/defects.md` | Add defect: Hardcoded Test Keys |

#### Implementation Detail

```markdown
### 2026-01-22: Hardcoded Test Widget Keys
**Pattern**: Using `Key('widget_name')` directly in both widgets and tests
**Root Cause**: No centralized source of truth for test keys, causing drift between implementation and tests
**Prevention**:
- Always use `TestingKeys` class from `lib/shared/testing_keys.dart`
- Never hardcode `Key('...')` in widgets or tests
- Add new keys to TestingKeys when adding testable widgets
**Impact**: 14+ tests excluded from test bundle, navigation helpers broken, dialog handling inconsistent
**Ref**: @.claude/plans/e2e-testing-remediation-plan.md
```

#### Verification
1. Defect logged in correct format
2. Prevention guidance is clear

---

## Execution Order

### Phase 1 (Foundation) - MUST COMPLETE FIRST
1. **Task 1.1**: Create TestingKeys class - `flutter-specialist-agent`

### Phase 2 (UI Updates) - DEPENDS ON PHASE 1
2. **Task 2.1**: Fix bottom navigation keys - `flutter-specialist-agent`
3. **Task 2.2**: Standardize dialog cancel keys - `flutter-specialist-agent`
4. **Task 2.3**: Update FAB and other keys - `flutter-specialist-agent`

### Phase 3 (Test Helpers) - DEPENDS ON PHASE 1
5. **Task 3.1**: Fix navigation helper keys - `qa-testing-agent`
6. **Task 3.2**: Fix auth helper keys - `qa-testing-agent`
7. **Task 3.3**: Fix patrol helpers dialog handling - `qa-testing-agent`

### Phase 4 (Test Bundle) - CAN RUN IN PARALLEL WITH PHASE 2-3
8. **Task 4.1**: Update test bundle - `qa-testing-agent`

### Phase 5 (Individual Tests) - DEPENDS ON PHASE 1-4
9. **Task 5.1**: Fix project management test - `qa-testing-agent`
10. **Task 5.2**: Fix offline mode test - `qa-testing-agent`
11. **Task 5.3**: Update all other tests - `qa-testing-agent`

### Phase 6 (Golden Tests) - CAN RUN IN PARALLEL
12. **Task 6.1**: Create flutter_test_config.dart - `qa-testing-agent`
13. **Task 6.2**: Clean up failure images - `qa-testing-agent`
14. **Task 6.3**: Update golden test docs - `qa-testing-agent`

### Phase 7 (Documentation) - LAST
15. **Task 7.1**: Update test documentation - `qa-testing-agent`
16. **Task 7.2**: Update defects log - `qa-testing-agent`

---

## Verification Checklist

### Critical Path (Must Pass)
- [ ] `flutter analyze` - 0 errors
- [ ] `flutter test` - All unit tests pass
- [ ] `patrol build` - Test bundle compiles
- [ ] Test count: 23 tests in bundle (was 12, added 11)
- [ ] No hardcoded navigation keys in tests
- [ ] No hardcoded dialog keys in tests
- [ ] Bottom navigation works in manual testing
- [ ] All dialog types (generic, delete, unsaved) work

### E2E Tests (After Full Implementation)
- [ ] Run E2E suite: `patrol test`
- [ ] Navigation tests pass (use correct nav button keys)
- [ ] Dialog tests pass (handle all cancel button variants)
- [ ] Project management tests pass (use correct projects_nav_button)
- [ ] Offline mode test compiles and handles auth
- [ ] All 23 tests in bundle execute

### Golden Tests
- [ ] `flutter test test/golden/` - Uses tolerant comparator
- [ ] No failure images committed to git
- [ ] `test/golden/pdf/failures/` in .gitignore

### Code Quality
- [ ] All TestingKeys references compile
- [ ] No remaining `Key('add_entry_fab')` in codebase
- [ ] No remaining `Key('.*nav.*')` in codebase
- [ ] Defects log updated with prevention guidance

---

## Risk Assessment

### High Risk
- **Breaking existing tests**: Changing keys will break tests until all references updated
  - **Mitigation**: Complete Phase 1-3 in single session, test incrementally

### Medium Risk
- **Missing key references**: May not find all hardcoded keys in first pass
  - **Mitigation**: Use comprehensive grep patterns, systematic file review

### Low Risk
- **Golden test tolerance**: 0.1% threshold may be too strict or too loose
  - **Mitigation**: Can adjust threshold in flutter_test_config.dart after testing

---

## Success Criteria

1. All 23 test files included in test_bundle.dart (0 excluded)
2. All widget keys defined in TestingKeys class (0 hardcoded)
3. All tests use TestingKeys constants (0 hardcoded Key() for common widgets)
4. All dialog types handled correctly (3 cancel button variants supported)
5. Golden test comparator wired up (TolerantGoldenFileComparator active)
6. No failure images in version control (failures/ in .gitignore)
7. `flutter analyze` passes (0 errors)
8. E2E test pass rate >90% (up from current broken state)

---

## Estimated Effort

| Phase | Tasks | Effort | Agent |
|-------|-------|--------|-------|
| Phase 1 | 1 task | 2 hours | flutter-specialist-agent |
| Phase 2 | 3 tasks | 3 hours | flutter-specialist-agent |
| Phase 3 | 3 tasks | 3 hours | qa-testing-agent |
| Phase 4 | 1 task | 2 hours | qa-testing-agent |
| Phase 5 | 3 tasks | 6 hours | qa-testing-agent |
| Phase 6 | 3 tasks | 2 hours | qa-testing-agent |
| Phase 7 | 2 tasks | 1 hour | qa-testing-agent |
| **Total** | **16 tasks** | **19 hours** | Both agents |

**Critical path**: Phases 1-5 (16 hours)
**Optional**: Phases 6-7 (3 hours)

---

## Notes

- This plan prioritizes test reliability over test coverage (fix infrastructure first)
- TestingKeys pattern prevents future key drift
- All changes are backwards compatible (tests still compile during migration)
- Golden test fixes can be deferred if time is limited
- Recommend completing Phases 1-5 in single session for consistency
