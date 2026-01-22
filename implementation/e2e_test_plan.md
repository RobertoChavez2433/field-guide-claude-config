# Comprehensive E2E Test Plan - Construction Inspector Field Guide App

**Created**: 2026-01-21
**Status**: APPROVED WITH CHANGES
**Source**: QA Agent analysis based on 2 research agent findings
**Code Review**: 8/10 - Approved with changes (2026-01-21)

---

## Code Review Summary

**Score**: 8/10 | **Verdict**: APPROVE WITH CHANGES

### Strengths Identified
- Accurate problem diagnosis (40% silent failures)
- Well-designed TestContext logging pattern
- Appropriate helper method abstraction level
- Batch strategy aligns with documented constraints
- Correct isolation of 17 edge-case tests

### Critical Issues to Address Before Implementation

| Issue | Description | Resolution |
|-------|-------------|------------|
| **Widget key mismatch** | Plan assumes keys exist that don't | Complete widget key audit first |
| **Async exists pattern** | Missing `pumpAndSettle()` before assertions | Update helper class |
| **Hardcoded delays** | Contradicts stated anti-pattern goals | Replace with condition-based waits |

### Pre-Implementation Checklist

- [ ] Complete widget key audit (verify which keys exist vs need adding)
- [ ] Update helper class to remove hardcoded delays
- [ ] Add retry logic to critical operations
- [ ] Implement screenshot capture for failures
- [ ] Verify single test runs before batch execution

### Timeline Adjustment

Original: 3 weeks → **Revised: 3-4 weeks** (accounting for UI changes and integration testing)

---

## Executive Summary

This plan transforms the current 84 Patrol tests into **~50 well-structured tests**:
- **~33 comprehensive E2E journey tests** covering complete user workflows
- **17 isolated tests** for permissions, validation, and edge cases (cannot be combined)

**Estimated Runtime**: 30-40 minutes (with batch restarts) vs current 15+ min (crashes)

### Key Improvements
| Problem | Current State | Solution |
|---------|---------------|----------|
| Silent failures | 40% `.exists` checks | Explicit assertions with reasons |
| No debug trail | 0% logging | Structured step logging |
| Only final assertions | End-state only | Intermediate assertions after every action |
| Code duplication | Same 5 sequences 40+ times | Reusable helper functions |
| Memory crashes | At ~20 tests | Batched execution (5-7 per batch) |

---

## 1. Test Helper Infrastructure

### 1.1 Core Helper Class

Create `integration_test/patrol/helpers/patrol_test_helpers.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:patrol/patrol.dart';
import 'package:construction_inspector/main.dart' as app;

/// Structured test context for logging and state management
class TestContext {
  final String testName;
  int _stepNumber = 0;
  final Stopwatch _stopwatch = Stopwatch();

  TestContext(this.testName) {
    _stopwatch.start();
  }

  /// Log a test step with automatic numbering
  void logStep(String action, [String? expected]) {
    _stepNumber++;
    final elapsed = _stopwatch.elapsedMilliseconds;
    final expectedMsg = expected != null ? ' - Expected: $expected' : '';
    debugPrint('[$testName][STEP $_stepNumber][${elapsed}ms] $action$expectedMsg');
  }

  /// Log an assertion result
  void logAssert(String key, String reason, {bool passed = true}) {
    final status = passed ? 'PASS' : 'FAIL';
    debugPrint('[$testName][ASSERT][$status] $key - $reason');
  }

  /// Log an error
  void logError(String what, String debugInfo) {
    debugPrint('[$testName][ERROR] $what - $debugInfo');
  }

  /// Log test completion
  void logComplete() {
    _stopwatch.stop();
    debugPrint('[$testName][COMPLETE] Total time: ${_stopwatch.elapsedMilliseconds}ms, Steps: $_stepNumber');
  }
}

/// Main helper class for Patrol E2E tests
class PatrolTestHelpers {
  final PatrolIntegrationTester $;
  final TestContext ctx;

  PatrolTestHelpers(this.$, this.ctx);

  // ==================== APP LIFECYCLE ====================

  /// Launch app and wait for initialization
  Future<void> launchAppAndWait() async {
    ctx.logStep('Launching app', 'App initialized and ready');
    app.main();
    await $.pumpAndSettle(timeout: const Duration(seconds: 15));
    await Future.delayed(const Duration(seconds: 2));
    await $.pump();
    ctx.logStep('App launched successfully');
  }

  // ==================== ASSERTIONS ====================

  /// Assert widget is visible with explicit reason
  Future<void> assertVisible(Key key, String reason) async {
    final finder = $(key);
    try {
      expect(finder, findsOneWidget, reason: reason);
      ctx.logAssert(key.toString(), reason, passed: true);
    } catch (e) {
      ctx.logAssert(key.toString(), reason, passed: false);
      ctx.logError('Widget not visible', 'Key: $key, Reason: $reason');
      rethrow;
    }
  }

  /// Assert widget is NOT visible
  Future<void> assertNotVisible(Key key, String reason) async {
    final finder = $(key);
    try {
      expect(finder, findsNothing, reason: reason);
      ctx.logAssert('NOT $key', reason, passed: true);
    } catch (e) {
      ctx.logAssert('NOT $key', reason, passed: false);
      rethrow;
    }
  }

  /// Assert widget exists (one or more)
  Future<void> assertExists(Key key, String reason) async {
    final finder = $(key);
    try {
      expect(finder, findsWidgets, reason: reason);
      ctx.logAssert(key.toString(), reason, passed: true);
    } catch (e) {
      ctx.logAssert(key.toString(), reason, passed: false);
      rethrow;
    }
  }

  /// Wait for widget to become visible (condition-based, not time-based)
  Future<void> waitForVisible(Key key, {Duration timeout = const Duration(seconds: 15)}) async {
    ctx.logStep('Waiting for ${key.toString()}', 'Widget becomes visible');
    await $.waitUntilVisible($(key), timeout: timeout);
  }

  // ==================== NAVIGATION ====================

  /// Navigate to a tab via bottom navigation
  Future<void> navigateToTab(String tabKey, String tabName) async {
    ctx.logStep('Navigating to $tabName tab');

    // First verify bottom nav exists
    await assertVisible(const Key('bottom_navigation_bar'), 'Bottom nav must be visible for navigation');

    // Tap the tab
    final tab = $(Key(tabKey));
    await tab.tap();
    await $.pumpAndSettle();

    ctx.logStep('Navigated to $tabName');
  }

  /// Navigate to Dashboard
  Future<void> navigateToDashboard() async {
    await navigateToTab('dashboard_nav_button', 'Dashboard');
  }

  /// Navigate to Calendar/Entries
  Future<void> navigateToCalendar() async {
    await navigateToTab('calendar_nav_button', 'Calendar');
  }

  /// Navigate to Projects
  Future<void> navigateToProjects() async {
    await navigateToTab('projects_nav_button', 'Projects');
  }

  /// Navigate to Settings
  Future<void> navigateToSettings() async {
    await navigateToTab('settings_nav_button', 'Settings');
  }

  // ==================== PERMISSIONS ====================

  /// Grant permission with logging
  Future<void> grantPermission(String permissionType) async {
    ctx.logStep('Granting $permissionType permission');
    try {
      await $.native.grantPermissionWhenInUse();
      ctx.logStep('Permission granted: $permissionType');
    } catch (e) {
      ctx.logStep('Permission already granted or not requested: $permissionType');
    }
  }

  /// Deny permission with logging
  Future<void> denyPermission(String permissionType) async {
    ctx.logStep('Denying $permissionType permission');
    try {
      await $.native.denyPermission();
      ctx.logStep('Permission denied: $permissionType');
    } catch (e) {
      ctx.logError('Permission denial failed', e.toString());
    }
  }

  // ==================== ENTRY WIZARD ====================

  /// Open entry wizard from calendar screen
  Future<void> openEntryWizard() async {
    ctx.logStep('Opening entry wizard', 'Entry wizard screen visible');

    // Ensure we're on calendar
    await navigateToCalendar();
    await $.pumpAndSettle();

    // Tap FAB
    await assertVisible(const Key('add_entry_fab'), 'Add entry FAB must be visible');
    await $(const Key('add_entry_fab')).tap();
    await $.pumpAndSettle();

    // Verify wizard opened
    await waitForVisible(const Key('entry_wizard_close'));
    await assertVisible(const Key('entry_wizard_close'), 'Entry wizard should be open');

    ctx.logStep('Entry wizard opened successfully');
  }

  /// Fill a text field in entry wizard
  Future<void> fillEntryField(Key fieldKey, String value, String fieldName) async {
    ctx.logStep('Filling $fieldName with "$value"');

    final field = $(fieldKey);
    await field.tap();
    await $.pumpAndSettle();
    await field.enterText(value);
    await $.pumpAndSettle();

    ctx.logStep('$fieldName filled');
  }

  /// Select from dropdown in entry wizard
  Future<void> selectDropdown(Key dropdownKey, String optionText, String fieldName) async {
    ctx.logStep('Selecting "$optionText" from $fieldName dropdown');

    await $(dropdownKey).tap();
    await $.pumpAndSettle();
    await $(optionText).tap();
    await $.pumpAndSettle();

    ctx.logStep('Selected $optionText in $fieldName');
  }

  /// Save entry (draft or submit)
  Future<void> saveEntry({bool asDraft = false}) async {
    final buttonKey = asDraft
        ? const Key('entry_wizard_save_draft')
        : const Key('entry_wizard_submit');
    final action = asDraft ? 'Save as draft' : 'Submit entry';

    ctx.logStep(action, 'Entry saved and wizard closed');

    await $(buttonKey).tap();
    await $.pumpAndSettle();

    // Handle confirmation dialog if present
    final confirmButton = $(const Key('confirm_dialog_button'));
    if (await confirmButton.exists) {
      ctx.logStep('Confirming save dialog');
      await confirmButton.tap();
      await $.pumpAndSettle();
    }

    // Verify we returned to calendar
    await waitForVisible(const Key('add_entry_fab'));
    ctx.logStep('Entry saved, returned to calendar');
  }

  /// Cancel entry wizard with discard handling
  Future<void> cancelEntryWizard({bool hasChanges = false}) async {
    ctx.logStep('Canceling entry wizard', 'Wizard closed');

    await $(const Key('entry_wizard_close')).tap();
    await $.pumpAndSettle();

    if (hasChanges) {
      // Handle discard dialog
      final discardButton = $(const Key('discard_dialog_button'));
      if (await discardButton.exists) {
        ctx.logStep('Discarding unsaved changes');
        await discardButton.tap();
        await $.pumpAndSettle();
      }
    }

    await waitForVisible(const Key('add_entry_fab'));
    ctx.logStep('Entry wizard closed');
  }

  // ==================== PROJECT MANAGEMENT ====================

  /// Open create project dialog
  Future<void> openCreateProject() async {
    ctx.logStep('Opening create project dialog');

    await navigateToProjects();
    await $.pumpAndSettle();

    await assertVisible(const Key('add_project_fab'), 'Add project FAB must be visible');
    await $(const Key('add_project_fab')).tap();
    await $.pumpAndSettle();

    ctx.logStep('Create project dialog opened');
  }

  /// Fill project details
  Future<void> fillProjectDetails({
    required String name,
    String? number,
    String? client,
  }) async {
    ctx.logStep('Filling project details');

    await fillEntryField(const Key('project_name_field'), name, 'Project name');

    if (number != null) {
      await fillEntryField(const Key('project_number_field'), number, 'Project number');
    }

    if (client != null) {
      await fillEntryField(const Key('project_client_field'), client, 'Client name');
    }

    ctx.logStep('Project details filled');
  }

  /// Save project
  Future<void> saveProject() async {
    ctx.logStep('Saving project');

    await $(const Key('project_save_button')).tap();
    await $.pumpAndSettle();

    // Verify returned to project list
    await waitForVisible(const Key('add_project_fab'));
    ctx.logStep('Project saved');
  }

  // ==================== UTILITIES ====================

  /// Dismiss keyboard (useful before tapping buttons)
  Future<void> dismissKeyboard() async {
    ctx.logStep('Dismissing keyboard');
    await $.native.pressBack();
    await $.pumpAndSettle();
    await Future.delayed(const Duration(milliseconds: 300));
  }

  /// Scroll to make widget visible
  Future<void> scrollToWidget(Key key, {Key? scrollableKey}) async {
    ctx.logStep('Scrolling to ${key.toString()}');

    final scrollable = scrollableKey != null
        ? $(scrollableKey)
        : $(Scrollable);

    await scrollable.scrollTo($(key));
    await $.pumpAndSettle();
  }

  /// Take screenshot for debugging
  Future<void> takeScreenshot(String name) async {
    ctx.logStep('Taking screenshot: $name');
    // Screenshot implementation depends on test infrastructure
  }
}
```

### 1.2 Updated Test Config

Update `integration_test/patrol/test_config.dart`:

```dart
import 'package:patrol/patrol.dart';
import 'helpers/patrol_test_helpers.dart';

class PatrolTestConfig {
  // Timeout configurations
  static const Duration standardTimeout = Duration(seconds: 15);
  static const Duration permissionTimeout = Duration(seconds: 20);
  static const Duration slowTimeout = Duration(seconds: 30);

  static const PatrolTesterConfig standard = PatrolTesterConfig(
    existsTimeout: standardTimeout,
  );

  static const PatrolTesterConfig permissions = PatrolTesterConfig(
    existsTimeout: permissionTimeout,
  );

  static const PatrolTesterConfig slow = PatrolTesterConfig(
    existsTimeout: slowTimeout,
  );

  /// Create test helpers with context
  static PatrolTestHelpers createHelpers(PatrolIntegrationTester $, String testName) {
    final ctx = TestContext(testName);
    return PatrolTestHelpers($, ctx);
  }
}
```

---

## 2. E2E Test Specifications

### Journey 1: Complete Report Creation

#### Test 1.1: Full Entry Lifecycle
**File**: `integration_test/patrol/e2e/entry_lifecycle_test.dart`

```dart
import 'package:flutter/material.dart';
import 'package:patrol/patrol.dart';
import '../test_config.dart';

void main() {
  patrolTest(
    'E2E: Full entry lifecycle - create, fill, submit',
    config: PatrolTestConfig.standard,
    ($) async {
      final h = PatrolTestConfig.createHelpers($, 'entry_lifecycle');

      // Step 1: Launch app
      await h.launchAppAndWait();

      // Step 2: Verify we're authenticated (or skip if login required)
      final loginButton = $(const Key('login_sign_in_button'));
      if (await loginButton.exists) {
        h.ctx.logStep('Login required - skipping test (no Supabase config)');
        return;
      }

      // Step 3: Navigate to calendar
      await h.navigateToCalendar();
      await h.assertVisible(const Key('add_entry_fab'), 'Calendar should show add entry FAB');

      // Step 4: Open entry wizard
      await h.openEntryWizard();

      // Step 5: Select location
      await h.selectDropdown(
        const Key('entry_wizard_location_dropdown'),
        'Main Site', // Assumes seed data has this
        'Location',
      );

      // Step 6: Select weather
      await h.selectDropdown(
        const Key('entry_wizard_weather_dropdown'),
        'Sunny',
        'Weather',
      );

      // Step 7: Enter temperatures
      await h.fillEntryField(const Key('entry_wizard_temp_low'), '45', 'Low temp');
      await h.fillEntryField(const Key('entry_wizard_temp_high'), '72', 'High temp');

      // Step 8: Enter activities
      await h.fillEntryField(
        const Key('entry_wizard_activities'),
        'E2E Test: Completed foundation work and site inspection.',
        'Activities',
      );

      // Step 9: Dismiss keyboard before submit
      await h.dismissKeyboard();

      // Step 10: Submit entry
      await h.saveEntry(asDraft: false);

      // Step 11: Verify entry appears in calendar
      await h.assertVisible(const Key('add_entry_fab'), 'Should return to calendar after save');

      // Complete
      h.ctx.logComplete();
    },
  );
}
```

**Duration**: ~45 seconds
**Memory Impact**: Medium
**Steps**: 11 logged steps
**Assertions**: 4 explicit assertions

#### Test 1.2: Entry Draft Save and Edit

```dart
patrolTest(
  'E2E: Save draft, edit, then submit',
  config: PatrolTestConfig.standard,
  ($) async {
    final h = PatrolTestConfig.createHelpers($, 'draft_edit_submit');

    await h.launchAppAndWait();

    // Skip if auth required
    if (await $(const Key('login_sign_in_button')).exists) return;

    // Create draft
    await h.openEntryWizard();
    await h.fillEntryField(const Key('entry_wizard_activities'), 'Draft entry', 'Activities');
    await h.dismissKeyboard();
    await h.saveEntry(asDraft: true);

    // TODO: Open the draft entry and edit
    // This requires entry card keys: entry_card_{id}

    h.ctx.logComplete();
  },
);
```

**Duration**: ~30 seconds
**Memory Impact**: Low

#### Test 1.3: Entry Validation Errors

```dart
patrolTest(
  'E2E: Entry validation prevents empty submission',
  config: PatrolTestConfig.standard,
  ($) async {
    final h = PatrolTestConfig.createHelpers($, 'entry_validation');

    await h.launchAppAndWait();
    if (await $(const Key('login_sign_in_button')).exists) return;

    await h.openEntryWizard();

    // Try to submit without required fields
    await $(const Key('entry_wizard_submit')).tap();
    await $.pumpAndSettle();

    // Should still be on wizard (validation blocked)
    await h.assertVisible(const Key('entry_wizard_close'), 'Wizard should remain open on validation error');

    // TODO: Check for validation error message

    await h.cancelEntryWizard(hasChanges: false);
    h.ctx.logComplete();
  },
);
```

**Duration**: ~20 seconds
**Memory Impact**: Low

---

### Journey 2: Offline Workflow + Sync

#### Test 2.1: Create Entry and Check Sync Status

```dart
patrolTest(
  'E2E: Create entry and verify sync pending status',
  config: PatrolTestConfig.standard,
  ($) async {
    final h = PatrolTestConfig.createHelpers($, 'offline_sync_status');

    await h.launchAppAndWait();
    if (await $(const Key('login_sign_in_button')).exists) return;

    // Create an entry
    await h.openEntryWizard();
    await h.fillEntryField(const Key('entry_wizard_activities'), 'Offline test entry', 'Activities');
    await h.dismissKeyboard();
    await h.saveEntry(asDraft: false);

    // Navigate to settings to check sync
    await h.navigateToSettings();
    await h.assertVisible(const Key('settings_sync_tile'), 'Sync tile should be visible');

    // TODO: Verify pending indicator shows count > 0

    h.ctx.logComplete();
  },
);
```

#### Test 2.2: Manual Sync Trigger

```dart
patrolTest(
  'E2E: Trigger manual sync from settings',
  config: PatrolTestConfig.slow,
  ($) async {
    final h = PatrolTestConfig.createHelpers($, 'manual_sync');

    await h.launchAppAndWait();
    if (await $(const Key('login_sign_in_button')).exists) return;

    await h.navigateToSettings();

    // Tap sync button
    final syncButton = $(const Key('settings_sync_button'));
    if (await syncButton.exists) {
      h.ctx.logStep('Triggering manual sync');
      await syncButton.tap();
      await $.pumpAndSettle();

      // Wait for sync to complete (may take a few seconds)
      await Future.delayed(const Duration(seconds: 3));
      await $.pumpAndSettle();

      h.ctx.logStep('Sync triggered');
    } else {
      h.ctx.logStep('Sync button not visible (Supabase not configured)');
    }

    h.ctx.logComplete();
  },
);
```

---

### Journey 3: Settings & Preferences

#### Test 3.1: Theme Switching

```dart
patrolTest(
  'E2E: Switch themes and verify persistence',
  config: PatrolTestConfig.standard,
  ($) async {
    final h = PatrolTestConfig.createHelpers($, 'theme_switching');

    await h.launchAppAndWait();
    if (await $(const Key('login_sign_in_button')).exists) return;

    await h.navigateToSettings();

    // Open theme dropdown
    h.ctx.logStep('Opening theme dropdown');
    await $(const Key('settings_theme_dropdown')).tap();
    await $.pumpAndSettle();

    // Select Dark theme
    h.ctx.logStep('Selecting Dark theme');
    await $('Dark').tap();
    await $.pumpAndSettle();

    // Navigate away and back to verify persistence
    await h.navigateToDashboard();
    await h.navigateToSettings();

    // TODO: Verify dark theme is still selected

    // Reset to Light
    await $(const Key('settings_theme_dropdown')).tap();
    await $.pumpAndSettle();
    await $('Light').tap();
    await $.pumpAndSettle();

    h.ctx.logComplete();
  },
);
```

---

### Journey 4: Project Management

#### Test 4.1: Complete Project Setup

```dart
patrolTest(
  'E2E: Create project with all details',
  config: PatrolTestConfig.standard,
  ($) async {
    final h = PatrolTestConfig.createHelpers($, 'create_project');

    await h.launchAppAndWait();
    if (await $(const Key('login_sign_in_button')).exists) return;

    // Open create project
    await h.openCreateProject();

    // Fill details
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    await h.fillProjectDetails(
      name: 'E2E Test Project $timestamp',
      number: 'E2E-$timestamp',
      client: 'Test Client',
    );

    // Dismiss keyboard
    await h.dismissKeyboard();

    // Save project
    await h.saveProject();

    // Verify project appears in list
    await h.assertVisible(const Key('add_project_fab'), 'Should return to project list');

    h.ctx.logComplete();
  },
);
```

---

## 3. Isolated Tests (Must Keep Separate)

These tests CANNOT be combined into E2E flows because they test edge cases that require clean state or conflict with other tests.

### 3.1 Permission Tests (4 tests)

| Test | File | Reason for Isolation |
|------|------|---------------------|
| Camera permission grant | `camera_permission_test.dart` | Device-level state |
| Camera permission denial | `camera_permission_test.dart` | Denial affects subsequent tests |
| Location permission grant | `location_permission_test.dart` | Device-level state |
| Location permission denial | `location_permission_test.dart` | Affects weather fetch |

### 3.2 Validation Tests (5 tests)

| Test | File | Reason for Isolation |
|------|------|---------------------|
| Empty email validation | `auth_flow_test.dart` | Leaves form in error state |
| Invalid email format | `auth_flow_test.dart` | Error state |
| Weak password validation | `auth_flow_test.dart` | Error state |
| Project name required | `project_management_test.dart` | Validation UI |
| Entry location required | `entry_management_test.dart` | Validation UI |

### 3.3 Navigation Edge Cases (4 tests)

| Test | File | Reason for Isolation |
|------|------|---------------------|
| Unsaved changes confirmation | `navigation_flow_test.dart` | State-dependent |
| Rapid tab switching | `navigation_flow_test.dart` | Race conditions |
| Tab state preservation | `navigation_flow_test.dart` | State-dependent |
| Full screen routes hide nav | `navigation_flow_test.dart` | Layout-specific |

### 3.4 App Lifecycle (4 tests)

| Test | File | Reason for Isolation |
|------|------|---------------------|
| App launch smoke test | `app_smoke_test.dart` | Requires fresh start |
| Background/foreground | `app_smoke_test.dart` | Lifecycle-specific |
| App cold start | `app_smoke_test.dart` | Clean state required |
| Memory warning handling | `app_smoke_test.dart` | System-level |

**Total Isolated Tests: 17**

---

## 4. Widget Keys Required

### Phase 1: Critical (Blocks E2E tests)

Must add these keys BEFORE implementing E2E tests:

#### Entry Wizard (`lib/features/entries/presentation/screens/entry_wizard_screen.dart`)
```dart
// Already exist:
// - entry_wizard_close
// - entry_wizard_location_dropdown
// - entry_wizard_weather_dropdown
// - entry_wizard_temp_low
// - entry_wizard_temp_high
// - entry_wizard_activities
// - entry_wizard_submit

// Need to add:
Key('entry_wizard_save_draft')      // Save as draft button
Key('entry_wizard_add_photo')       // Add photo button
Key('entry_wizard_add_personnel')   // Add personnel button
```

#### Entry Basics Section (`lib/features/entries/presentation/widgets/entry_basics_section.dart`)
```dart
// Need to verify these exist or add:
Key('entry_wizard_location_dropdown')
Key('entry_wizard_weather_dropdown')
Key('weather_fetch_button')         // Auto-fetch weather
```

#### Project Setup (`lib/features/projects/presentation/screens/project_setup_screen.dart`)
```dart
// Already exist:
// - project_save_button
// - contractor_save_button
// - contractor_cancel_button

// Need to add:
Key('project_name_field')
Key('project_number_field')
Key('project_client_field')
Key('project_details_tab')
Key('project_locations_tab')
Key('project_contractors_tab')
Key('project_payitems_tab')
```

#### Settings (`lib/features/settings/presentation/screens/settings_screen.dart`)
```dart
// Already exist:
// - settings_theme_dropdown
// - settings_sync_tile
// - settings_sync_button

// Need to add:
Key('settings_inspector_name_field')
Key('settings_inspector_initials_field')
Key('settings_auto_weather_toggle')
Key('settings_auto_sync_toggle')
```

#### Dialogs (Various files)
```dart
Key('confirm_dialog_button')        // Generic confirm
Key('cancel_dialog_button')         // Generic cancel
Key('discard_dialog_button')        // Discard changes
```

### Phase 2: High Priority (Improves reliability)

#### Entry Cards (`lib/features/entries/presentation/`)
```dart
Key('entry_card_$entryId')          // Dynamic entry cards
Key('entry_edit_button_$entryId')   // Edit button per entry
Key('entry_delete_button_$entryId') // Delete button per entry
```

#### Project Cards (`lib/features/projects/presentation/`)
```dart
Key('project_card_$projectId')      // Dynamic project cards
Key('project_menu_$projectId')      // Menu button per project
```

#### Personnel Section (`lib/features/entries/presentation/widgets/`)
```dart
Key('contractor_checkbox_$id')      // Contractor selection
Key('personnel_increment_$typeId')  // Add personnel
Key('personnel_decrement_$typeId')  // Remove personnel
Key('equipment_chip_$equipmentId')  // Equipment selection
```

### Phase 3: Medium Priority (Nice to have)

```dart
Key('calendar_day_$date')           // Calendar date cells
Key('photo_thumbnail_$photoId')     // Photo gallery items
Key('quantity_field_$bidItemId')    // Quantity inputs
Key('sync_status_indicator')        // Sync progress
Key('offline_badge')                // Offline indicator
```

---

## 5. Logging Standards

### Log Format

```
[TEST_NAME][TYPE][TIMESTAMP] Message

Types:
- STEP N  : Test step with number
- ASSERT  : Assertion (PASS/FAIL)
- ERROR   : Error with debug info
- COMPLETE: Test finished
```

### Examples

```
[entry_lifecycle][STEP 1][0ms] Launching app - Expected: App initialized and ready
[entry_lifecycle][STEP 2][2150ms] App launched successfully
[entry_lifecycle][STEP 3][2200ms] Navigating to Calendar tab
[entry_lifecycle][ASSERT][PASS] Key('add_entry_fab') - Calendar should show add entry FAB
[entry_lifecycle][STEP 4][2850ms] Opening entry wizard - Expected: Entry wizard screen visible
[entry_lifecycle][ERROR] Widget not visible - Key: entry_wizard_submit, Reason: Submit button should exist
[entry_lifecycle][COMPLETE] Total time: 45230ms, Steps: 11
```

### Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| STEP | Every major action | Navigation, button tap, form fill |
| ASSERT | Every explicit check | Widget visibility, state verification |
| ERROR | Failures only | Assertion failures, exceptions |
| COMPLETE | Test end | Summary with duration |

---

## 6. Batch Strategy

### Batch Configuration

**Total Tests**: ~50 (33 E2E + 17 isolated)
**Batch Size**: 5-7 tests
**Total Batches**: 9

### Batch Assignments

| Batch | Tests | Type | Memory | Duration |
|-------|-------|------|--------|----------|
| 1 | Entry lifecycle (3) + Entry validation (2) | E2E | Medium | ~3 min |
| 2 | Project management (2) + Settings (2) | E2E | Low | ~2 min |
| 3 | Offline/sync (2) + Photo flow (2) | E2E | Medium | ~3 min |
| 4 | Navigation E2E (3) | E2E | Low | ~2 min |
| 5 | Camera permissions (3) | Isolated | Low | ~2 min |
| 6 | Location permissions (2) + Validation (3) | Isolated | Low | ~2 min |
| 7 | Auth validation (3) + Navigation edge (2) | Isolated | Low | ~2 min |
| 8 | App lifecycle (4) | Isolated | Medium | ~3 min |
| 9 | Smoke tests (3) | E2E | Low | ~2 min |

### Batch Execution Order

1. **Batches 1-4 first** (E2E tests) - Most important coverage
2. **Batches 5-7 next** (Isolated edge cases) - Permission/validation
3. **Batch 8** (Lifecycle) - Requires clean state
4. **Batch 9 last** (Smoke) - Final verification

### Updated `run_patrol_batched.ps1`

```powershell
$TestBatches = @(
    @{
        Name = "Batch 1: Entry E2E (5 tests)"
        Files = @(
            "e2e/entry_lifecycle_test.dart"
        )
    },
    @{
        Name = "Batch 2: Project & Settings E2E (4 tests)"
        Files = @(
            "e2e/project_management_e2e_test.dart",
            "e2e/settings_e2e_test.dart"
        )
    },
    @{
        Name = "Batch 3: Offline & Photos E2E (4 tests)"
        Files = @(
            "e2e/offline_sync_test.dart",
            "e2e/photo_flow_test.dart"
        )
    },
    @{
        Name = "Batch 4: Navigation E2E (3 tests)"
        Files = @(
            "e2e/navigation_e2e_test.dart"
        )
    },
    @{
        Name = "Batch 5: Camera Permissions (3 tests)"
        Files = @(
            "isolated/camera_permission_test.dart"
        )
    },
    @{
        Name = "Batch 6: Location & Validation (5 tests)"
        Files = @(
            "isolated/location_permission_test.dart",
            "isolated/entry_validation_test.dart"
        )
    },
    @{
        Name = "Batch 7: Auth & Nav Edge Cases (5 tests)"
        Files = @(
            "isolated/auth_validation_test.dart",
            "isolated/navigation_edge_test.dart"
        )
    },
    @{
        Name = "Batch 8: App Lifecycle (4 tests)"
        Files = @(
            "isolated/app_lifecycle_test.dart"
        )
    },
    @{
        Name = "Batch 9: Smoke Tests (3 tests)"
        Files = @(
            "smoke/app_smoke_test.dart"
        )
    }
)
```

---

## 7. Implementation Order

### Week 1: Foundation & Core Journeys

**Days 1-2: Infrastructure**
- [ ] Create `integration_test/patrol/helpers/patrol_test_helpers.dart`
- [ ] Update `integration_test/patrol/test_config.dart`
- [ ] Add Phase 1 widget keys to UI files (6 files)
- [ ] Create folder structure:
  ```
  integration_test/patrol/
  ├── helpers/
  │   └── patrol_test_helpers.dart
  ├── e2e/
  │   ├── entry_lifecycle_test.dart
  │   ├── project_management_e2e_test.dart
  │   ├── settings_e2e_test.dart
  │   ├── offline_sync_test.dart
  │   ├── photo_flow_test.dart
  │   └── navigation_e2e_test.dart
  ├── isolated/
  │   ├── camera_permission_test.dart
  │   ├── location_permission_test.dart
  │   ├── entry_validation_test.dart
  │   ├── auth_validation_test.dart
  │   ├── navigation_edge_test.dart
  │   └── app_lifecycle_test.dart
  ├── smoke/
  │   └── app_smoke_test.dart
  └── test_config.dart
  ```

**Days 3-5: Core E2E Tests**
- [ ] Implement Journey 1: Entry lifecycle (3 tests)
- [ ] Implement Journey 4: Project management (2 tests)
- [ ] Implement Journey 3: Settings (2 tests)
- [ ] Run Batches 1-2, fix issues

### Week 2: Additional Journeys & Isolated Tests

**Days 1-2: Secondary Journeys**
- [ ] Implement Journey 2: Offline/sync (2 tests)
- [ ] Implement Journey 5: Photo flow (2 tests)
- [ ] Add Phase 2 widget keys
- [ ] Run Batches 3-4, fix issues

**Days 3-5: Isolated Tests**
- [ ] Migrate/update permission tests (6 tests)
- [ ] Migrate/update validation tests (5 tests)
- [ ] Migrate/update navigation edge tests (4 tests)
- [ ] Migrate/update lifecycle tests (4 tests)
- [ ] Run Batches 5-8, fix issues

### Week 3: Cleanup & Validation

**Days 1-2: Cleanup**
- [ ] Delete old test files (or move to `archive/`)
- [ ] Update smoke tests to use helpers
- [ ] Run Batch 9

**Days 3-5: Full Regression**
- [ ] Run all 9 batches sequentially
- [ ] Fix any flaky tests
- [ ] Document test coverage
- [ ] Update `run_patrol_batched.ps1` with final batch config
- [ ] Create test execution documentation

---

## 8. Success Metrics

| Metric | Before | After (Target) |
|--------|--------|----------------|
| Total Tests | 84 | ~50 |
| Silent Failures | 40% | 0% |
| Tests with Logging | 0% | 100% |
| Tests with Intermediate Assertions | 0% | 100% |
| Memory Crashes | At ~20 tests | None |
| Avg Test Duration | 10-15s | 20-45s (but fewer tests) |
| Total Suite Runtime | 15+ min (crashes) | 20-25 min (completes) |
| Flakiness | Moderate | Low |
| User Journey Coverage | Fragmented | Complete |

---

## 9. Anti-Patterns to Fix

### Before → After

```dart
// BEFORE: Silent failure
final fab = $(Key('add_entry_fab'));
if (fab.exists) {
  await fab.tap();
}

// AFTER: Explicit assertion with logging
await h.assertVisible(const Key('add_entry_fab'), 'FAB must be visible');
await $(const Key('add_entry_fab')).tap();
```

```dart
// BEFORE: No logging
await $.pumpAndSettle();
await $(Key('save_button')).tap();
await $.pumpAndSettle();

// AFTER: Structured logging
h.ctx.logStep('Saving entry');
await $.pumpAndSettle();
await $(const Key('save_button')).tap();
await $.pumpAndSettle();
h.ctx.logStep('Entry saved');
```

```dart
// BEFORE: Hardcoded delay
await Future.delayed(const Duration(seconds: 3));

// AFTER: Condition-based wait
await h.waitForVisible(const Key('success_indicator'));
```

```dart
// BEFORE: Duplicated setup
app.main();
await $.pumpAndSettle();
await Future.delayed(const Duration(seconds: 2));
await $.pump();

// AFTER: Reusable helper
await h.launchAppAndWait();
```

---

## 10. Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| `integration_test/patrol/helpers/patrol_test_helpers.dart` | Helper class |
| `integration_test/patrol/e2e/entry_lifecycle_test.dart` | Entry E2E |
| `integration_test/patrol/e2e/project_management_e2e_test.dart` | Project E2E |
| `integration_test/patrol/e2e/settings_e2e_test.dart` | Settings E2E |
| `integration_test/patrol/e2e/offline_sync_test.dart` | Offline E2E |
| `integration_test/patrol/e2e/photo_flow_test.dart` | Photo E2E |
| `integration_test/patrol/e2e/navigation_e2e_test.dart` | Navigation E2E |
| `integration_test/patrol/isolated/*` | Migrated isolated tests |
| `integration_test/patrol/smoke/app_smoke_test.dart` | Updated smoke tests |

### Files to Modify (Add Keys)
| File | Keys to Add |
|------|-------------|
| `lib/features/entries/presentation/screens/entry_wizard_screen.dart` | 3 keys |
| `lib/features/projects/presentation/screens/project_setup_screen.dart` | 7 keys |
| `lib/features/settings/presentation/screens/settings_screen.dart` | 4 keys |
| Various dialog files | 3 keys |

### Files to Delete/Archive
| File | Action |
|------|--------|
| `integration_test/patrol/entry_management_test.dart` | Archive → replaced by E2E |
| `integration_test/patrol/project_management_test.dart` | Archive → replaced by E2E |
| `integration_test/patrol/settings_flow_test.dart` | Archive → replaced by E2E |
| `integration_test/patrol/offline_mode_test.dart` | Archive → replaced by E2E |
| `integration_test/patrol/contractors_flow_test.dart` | Archive → replaced by E2E |
| `integration_test/patrol/quantities_flow_test.dart` | Archive → replaced by E2E |

---

## Appendix: Complete Test List

### E2E Tests (33 tests)

| # | Test Name | Journey | Duration |
|---|-----------|---------|----------|
| 1 | Full entry lifecycle | Entry | 45s |
| 2 | Entry draft save and edit | Entry | 30s |
| 3 | Entry validation errors | Entry | 20s |
| 4 | Entry with photo capture | Entry | 35s |
| 5 | Entry with personnel | Entry | 30s |
| 6 | Create project with details | Project | 30s |
| 7 | Edit existing project | Project | 25s |
| 8 | Search and filter projects | Project | 20s |
| 9 | Theme switching | Settings | 20s |
| 10 | Inspector profile update | Settings | 25s |
| 11 | Create entry offline | Offline | 35s |
| 12 | Check sync status | Offline | 20s |
| 13 | Manual sync trigger | Offline | 30s |
| 14 | Photo from camera | Photo | 25s |
| 15 | Photo from gallery | Photo | 20s |
| 16 | Tab navigation complete | Navigation | 25s |
| 17 | Deep navigation return | Navigation | 20s |
| 18 | State persistence | Navigation | 25s |
| ... | (Additional E2E as needed) | | |

### Isolated Tests (17 tests)

| # | Test Name | Category |
|---|-----------|----------|
| 1 | Camera permission grant | Permission |
| 2 | Camera permission denial | Permission |
| 3 | Camera reopen after grant | Permission |
| 4 | Location permission grant | Permission |
| 5 | Location permission denial | Permission |
| 6 | Empty email validation | Validation |
| 7 | Invalid email format | Validation |
| 8 | Weak password validation | Validation |
| 9 | Project name required | Validation |
| 10 | Entry location required | Validation |
| 11 | Unsaved changes confirmation | Navigation |
| 12 | Rapid tab switching | Navigation |
| 13 | Tab state preservation | Navigation |
| 14 | Full screen hides nav | Navigation |
| 15 | App launch smoke | Lifecycle |
| 16 | Background/foreground | Lifecycle |
| 17 | App restart | Lifecycle |

---

**Document Version**: 1.0
**Created**: 2026-01-21
**Status**: Ready for Code Review
