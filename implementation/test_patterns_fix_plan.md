# Test Patterns & Keys Implementation Plan

**Last Updated**: 2026-01-21
**Status**: READY FOR IMPLEMENTATION
**Source**: Analysis of defects.md, patrol_test_fix_plan_v2.md, and current test infrastructure

---

## Executive Summary

This plan addresses recurring test issues across the Field Guide App by implementing a comprehensive Key strategy and standardizing test patterns. The goal is to make tests more reliable, maintainable, and resistant to UI changes.

**Current Issues**:
1. Missing Keys on critical widgets (FABs, tabs, dialogs, buttons)
2. Text-based selectors used instead of Key selectors (fragile, locale-dependent)
3. Auth state assumptions causing test failures
4. Inconsistent test helper patterns across 13 Patrol tests and 45 unit tests

**Target Outcomes**:
- 95%+ Patrol test pass rate (currently 65%)
- Zero text-based selectors in integration tests
- Auth bypass mechanism for offline testing
- Standardized test helper library

**Estimated Effort**: 12-16 hours across 5 phases

---

## Phase 1: Critical Widget Keys (HIGH PRIORITY)

**Effort**: 3-4 hours
**Impact**: Fixes 10+ failing Patrol tests
**Agent**: `flutter-specialist-agent`

### Overview
Add Keys to widgets that Patrol tests need to interact with. These are widgets that tests tap, scroll to, or verify existence of.

---

### Task 1.1: Entry Management Keys

**File**: `lib/features/entries/presentation/screens/home_screen.dart`

**Keys to Add**:

**Line ~80-100** (FAB):
```dart
// Find the FloatingActionButton in the Scaffold
FloatingActionButton(
  key: const Key('add_entry_fab'),  // ADD THIS
  onPressed: _handleAddEntry,
  child: const Icon(Icons.add),
)
```

**Line ~200-250** (Calendar tabs/navigation):
```dart
// Find BottomNavigationBar or similar navigation widget
BottomNavigationBarItem(
  key: const Key('home_tab'),  // ADD THIS
  icon: Icon(Icons.home),
  label: 'Home',
)
// OR if using TabBar:
Tab(
  key: const Key('calendar_tab'),  // ADD THIS
  icon: Icon(Icons.calendar_today),
  text: 'Calendar',
)
```

**Investigation Required**:
- Locate the actual navigation widget (BottomNavigationBar vs TabBar)
- Add Keys to all navigation items (home, calendar, entries tabs)

**Tests Fixed**:
- `entry_management_test.dart` tests 1-10 (all 10 tests)

---

### Task 1.2: Entry Wizard Keys

**File**: `lib/features/entries/presentation/screens/entry_wizard_screen.dart`

**Keys to Add**:

**Line ~300-400** (TabBar for wizard sections):
```dart
// Find the TabBar widget
TabBar(
  key: const Key('entry_wizard_tabs'),  // ADD THIS
  controller: _tabController,
  tabs: [
    Tab(key: const Key('entry_wizard_tab_basics'), text: 'Basics'),
    Tab(key: const Key('entry_wizard_tab_weather'), text: 'Weather'),
    Tab(key: const Key('entry_wizard_tab_activities'), text: 'Activities'),
    Tab(key: const Key('entry_wizard_tab_personnel'), text: 'Personnel'),
    Tab(key: const Key('entry_wizard_tab_quantities'), text: 'Quantities'),
    Tab(key: const Key('entry_wizard_tab_photos'), text: 'Photos'),
  ],
)
```

**Line ~500-600** (Action buttons):
```dart
// Close button in AppBar
IconButton(
  key: const Key('entry_wizard_close'),  // ADD THIS
  icon: const Icon(Icons.close),
  onPressed: _handleClose,
)

// Save Draft button
ElevatedButton(
  key: const Key('entry_wizard_save_draft'),  // ADD THIS
  onPressed: _saveDraft,
  child: const Text('Save Draft'),
)

// Submit button
ElevatedButton(
  key: const Key('entry_wizard_submit'),  // ADD THIS
  onPressed: _submit,
  child: const Text('Submit'),
)
```

**Investigation Required**:
- Determine exact tab names and order
- Locate all action buttons (save, submit, cancel, finalize)

**Tests Fixed**:
- `entry_management_test.dart` tests 2-9 (8 tests)

---

### Task 1.3: Entry Basics Section Keys

**File**: `lib/features/entries/presentation/widgets/entry_basics_section.dart`

**Keys to Add**:

```dart
// Temperature fields
TextField(
  key: const Key('entry_wizard_temp_low'),
  controller: tempLowController,
  decoration: const InputDecoration(labelText: 'Low Temp'),
)

TextField(
  key: const Key('entry_wizard_temp_high'),
  controller: tempHighController,
  decoration: const InputDecoration(labelText: 'High Temp'),
)

// Activities field
TextField(
  key: const Key('entry_wizard_activities'),
  controller: activitiesController,
  decoration: const InputDecoration(labelText: 'Activities'),
)
```

**Tests Fixed**:
- `entry_management_test.dart` tests 4-6 (3 tests)

---

### Task 1.4: Weather Widget Keys

**File**: `lib/features/entries/presentation/widgets/` (locate weather widget)

**Keys to Add**:

```dart
// Weather condition buttons
IconButton(
  key: const Key('weather_sunny'),
  icon: const Icon(Icons.wb_sunny),
  onPressed: () => onWeatherSelected('sunny'),
)

IconButton(
  key: const Key('weather_cloudy'),
  icon: const Icon(Icons.cloud),
  onPressed: () => onWeatherSelected('cloudy'),
)

IconButton(
  key: const Key('weather_rainy'),
  icon: const Icon(Icons.wb_cloudy),
  onPressed: () => onWeatherSelected('rainy'),
)
```

**Investigation Required**:
- Locate the weather selection widget file
- Identify all weather condition options

**Tests Fixed**:
- `entry_management_test.dart` test 4 (weather data test)

---

### Task 1.5: Auth Screen Keys (Already Mostly Complete)

**Status Check**:
- ✅ `login_screen.dart` - Has all required Keys
- ✅ `register_screen.dart` - Has screen title and field Keys
- ✅ `forgot_password_screen.dart` - Has screen title and field Keys

**Missing Keys**:

**File**: `lib/features/auth/presentation/screens/register_screen.dart`

**Line ~180-200** (Back to login button):
```dart
TextButton(
  key: const Key('register_back_to_login_button'),  // ADD THIS
  onPressed: () => context.go('/login'),
  child: const Text('Already have an account? Sign In'),
)
```

**Tests Fixed**:
- `auth_flow_test.dart` test 7 (navigate back from sign up)

---

## Phase 2: Dialog & Modal Keys (MEDIUM PRIORITY)

**Effort**: 2-3 hours
**Impact**: Fixes dialog interaction tests
**Agent**: `flutter-specialist-agent`

### Overview
Add Keys to dialog buttons, form fields, and confirmation prompts.

---

### Task 2.1: Confirmation Dialog Keys

**File**: `lib/shared/widgets/confirmation_dialog.dart`

**Keys to Add**:

```dart
class ConfirmationDialog extends StatelessWidget {
  // ...

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      key: const Key('confirmation_dialog'),  // ADD THIS
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(
          key: const Key('confirmation_dialog_cancel'),  // ADD THIS
          onPressed: () => Navigator.pop(context, false),
          child: Text(cancelText),
        ),
        ElevatedButton(
          key: Key('confirmation_dialog_${confirmText.toLowerCase().replaceAll(' ', '_')}'),  // Dynamic Key
          onPressed: () => Navigator.pop(context, true),
          child: Text(confirmText),
        ),
      ],
    );
  }
}
```

**Alternative**: Use specific Keys for common actions:
```dart
Key('confirm_dialog_button')     // Generic confirm
Key('delete_confirm_button')     // Delete confirmations
Key('discard_dialog_button')     // Discard changes
```

**Tests Fixed**:
- `entry_management_test.dart` test 9 (cancel entry creation)
- `entry_management_test.dart` test 11 (delete draft entry)

---

### Task 2.2: Contractor Dialog Keys

**Investigation Required**: Locate contractor add/edit dialog

**Likely Files**:
- `lib/features/contractors/presentation/widgets/contractor_dialog.dart`
- OR inline in `lib/features/projects/presentation/screens/project_setup_screen.dart`

**Keys to Add**:

```dart
// Contractor form fields
TextField(
  key: const Key('contractor_name_field'),
  decoration: const InputDecoration(labelText: 'Name'),
)

TextField(
  key: const Key('contractor_company_field'),
  decoration: const InputDecoration(labelText: 'Company'),
)

// Type selection
RadioListTile(
  key: const Key('contractor_type_prime'),
  title: const Text('Prime Contractor'),
  value: ContractorType.prime,
  // ...
)

RadioListTile(
  key: const Key('contractor_type_sub'),
  title: const Text('Subcontractor'),
  value: ContractorType.subcontractor,
  // ...
)

// Action buttons
ElevatedButton(
  key: const Key('contractor_save_button'),
  onPressed: _save,
  child: const Text('Save'),
)

TextButton(
  key: const Key('contractor_cancel_button'),
  onPressed: _cancel,
  child: const Text('Cancel'),
)
```

**Tests Fixed**:
- `contractors_flow_test.dart` tests 1, 3 (add/edit contractor)

---

### Task 2.3: Photo Source Dialog Keys (Already Complete)

**Status**: ✅ `photo_source_dialog.dart` already has `Key('photo_capture_camera')`

**Verification**: Add Key to gallery option for completeness:

```dart
ListTile(
  key: const Key('photo_capture_gallery'),  // ADD THIS
  leading: const Icon(Icons.photo_library),
  title: const Text('Choose from Gallery'),
  onTap: () => Navigator.pop(context, PhotoSource.gallery),
)
```

**Tests Fixed**:
- `camera_permission_test.dart` tests 1-3 (all 3 tests already passing with Phase 1 of patrol fix plan)

---

## Phase 3: Navigation Keys (MEDIUM PRIORITY)

**Effort**: 2-3 hours
**Impact**: Enables navigation flow tests
**Agent**: `flutter-specialist-agent`

### Overview
Add Keys to bottom navigation, drawer items, and primary navigation widgets.

---

### Task 3.1: Main Navigation Keys

**File**: `lib/main.dart` or main scaffold widget (investigate location)

**Keys to Add**:

```dart
BottomNavigationBar(
  items: [
    BottomNavigationBarItem(
      key: const Key('nav_home'),  // ADD THIS
      icon: Icon(Icons.home),
      label: 'Home',
    ),
    BottomNavigationBarItem(
      key: const Key('nav_projects'),  // ADD THIS
      icon: Icon(Icons.folder),
      label: 'Projects',
    ),
    BottomNavigationBarItem(
      key: const Key('nav_dashboard'),  // ADD THIS
      icon: Icon(Icons.dashboard),
      label: 'Dashboard',
    ),
    BottomNavigationBarItem(
      key: const Key('nav_settings'),  // ADD THIS
      icon: Icon(Icons.settings),
      label: 'Settings',
    ),
  ],
)
```

**Investigation Required**:
- Locate the main navigation widget
- Determine if app uses BottomNavigationBar, NavigationRail, or Drawer

**Tests Fixed**:
- `navigation_flow_test.dart` (all navigation tests)

---

### Task 3.2: Project List Keys

**File**: `lib/features/projects/presentation/screens/project_list_screen.dart`

**Keys to Add**:

```dart
// Add Project FAB
FloatingActionButton(
  key: const Key('add_project_fab'),  // ADD THIS
  onPressed: _addProject,
  child: const Icon(Icons.add),
)

// Project cards (dynamic Keys)
Card(
  key: Key('project_card_${project.id}'),  // ADD THIS
  child: ListTile(
    title: Text(project.name),
    // ...
  ),
)
```

**Tests Fixed**:
- `project_management_test.dart` (project CRUD tests)

---

### Task 3.3: Dashboard Keys

**File**: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`

**Keys to Add**:

```dart
// Dashboard widgets
Card(
  key: const Key('dashboard_recent_entries'),
  child: // Recent entries widget
)

Card(
  key: const Key('dashboard_active_contractors'),
  child: // Active contractors widget
)

Card(
  key: const Key('dashboard_quantities_summary'),
  child: // Quantities summary widget
)
```

**Investigation Required**:
- Identify all dashboard widgets/cards
- Add Keys to each section

**Tests Fixed**:
- `navigation_flow_test.dart` (dashboard navigation)

---

## Phase 4: Test Pattern Standardization (HIGH PRIORITY)

**Effort**: 3-4 hours
**Impact**: Makes all tests more maintainable
**Agent**: `qa-testing-agent`

### Overview
Replace text selectors with Key selectors, remove conditional navigation, and create standardized test helpers.

---

### Task 4.1: Replace Text Selectors in Auth Tests

**File**: `integration_test/patrol/auth_flow_test.dart`

**Changes**:

**Lines 71, 95, 116, 136, 243** - Replace text with Keys:
```dart
// BEFORE
expect($('Create Account'), findsWidgets);
expect($('Reset Password'), findsWidgets);
expect($('Email'), findsWidgets);

// AFTER
expect($(Key('register_screen_title')), findsOneWidget);
expect($(Key('forgot_password_screen_title')), findsOneWidget);
expect($(Key('register_email_field')), findsOneWidget);
```

**Tests Improved**: All 10 auth flow tests become more reliable

---

### Task 4.2: Replace Text Selectors in Entry Tests

**File**: `integration_test/patrol/entry_management_test.dart`

**Changes**:

**Lines 31-40** - Replace conditional tab navigation:
```dart
// BEFORE
final calendarTab = $(Key('calendar_tab'));
final homeTab = $(Key('home_tab'));
final entriesTab = $(Key('entries_tab'));

if (calendarTab.exists) {
  await calendarTab.tap();
} else if (homeTab.exists) {
  await homeTab.tap();
}

// AFTER
// Use explicit navigation with error handling
try {
  await $(Key('home_tab')).tap();
  await $.pumpAndSettle();
} catch (e) {
  // Fallback to calendar tab
  await $(Key('calendar_tab')).tap();
  await $.pumpAndSettle();
}
```

**Tests Improved**: All 11 entry management tests

---

### Task 4.3: Remove Conditional Exists Checks

**Files**: All Patrol test files

**Pattern to Replace**:
```dart
// BEFORE (fragile, masks failures)
if (widget.exists) {
  await widget.tap();
  // test continues
} else {
  // skip test or try alternative
}

// AFTER (explicit, fails fast)
expect(widget, findsOneWidget);  // Assert widget exists
await widget.tap();
await $.pumpAndSettle();
```

**Benefits**:
- Tests fail fast with clear error messages
- No silent skips
- Easier to debug

**Files to Update**:
- `auth_flow_test.dart` (lines 131-138, 194-199, 240-248)
- `entry_management_test.dart` (lines 31-40, 58-67, 92-96, 142-146)
- `contractors_flow_test.dart` (conditional swipe gesture handling)

---

### Task 4.4: Create Test Helper Library

**New File**: `integration_test/helpers/test_helpers.dart`

**Contents**:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:patrol/patrol.dart';

/// Common test helper functions for Field Guide App
class TestHelpers {
  /// Navigate to home screen from any screen
  static Future<void> navigateToHome(PatrolTester $) async {
    final homeTab = $(Key('home_tab'));
    if (homeTab.exists) {
      await homeTab.tap();
      await $.pumpAndSettle();
      return;
    }

    // Fallback: navigate via calendar
    final calendarTab = $(Key('calendar_tab'));
    await calendarTab.tap();
    await $.pumpAndSettle();
  }

  /// Open entry wizard for new entry
  static Future<void> openNewEntryWizard(PatrolTester $) async {
    await navigateToHome($);

    final fab = $(Key('add_entry_fab'));
    expect(fab, findsOneWidget);
    await fab.tap();
    await $.pumpAndSettle();

    // Verify wizard opened
    await $.waitUntilVisible($(Key('entry_wizard_tabs')));
  }

  /// Navigate to specific wizard tab
  static Future<void> navigateToWizardTab(PatrolTester $, String tabName) async {
    final tab = $(Key('entry_wizard_tab_$tabName'));
    expect(tab, findsOneWidget);
    await tab.tap();
    await $.pumpAndSettle();
  }

  /// Confirm dialog action (delete, discard, etc)
  static Future<void> confirmDialog(PatrolTester $, String action) async {
    final button = $(Key('${action}_confirm_button'));
    await $.waitUntilVisible(button);
    await button.tap();
    await $.pumpAndSettle();
  }

  /// Navigate to project setup screen
  static Future<void> openProjectSetup(PatrolTester $) async {
    final projectsTab = $(Key('nav_projects'));
    await projectsTab.tap();
    await $.pumpAndSettle();

    final addProjectFab = $(Key('add_project_fab'));
    await addProjectFab.tap();
    await $.pumpAndSettle();
  }

  /// Navigate to specific project setup tab
  static Future<void> navigateToProjectTab(PatrolTester $, String tabName) async {
    final tab = $(Key('project_${tabName}_tab'));
    expect(tab, findsOneWidget);
    await tab.tap();
    await $.pumpAndSettle();
  }
}

/// Wait helpers with common timeouts
class WaitHelpers {
  static const shortWait = Duration(seconds: 3);
  static const mediumWait = Duration(seconds: 5);
  static const longWait = Duration(seconds: 10);

  /// Wait for widget with timeout
  static Future<void> waitFor(PatrolTester $, Finder finder, {Duration? timeout}) async {
    await $.waitUntilVisible(finder, timeout: timeout ?? mediumWait);
  }
}
```

**Usage in Tests**:
```dart
import 'helpers/test_helpers.dart';

patrolTest('creates new entry', ($) async {
  app.main();
  await $.pumpAndSettle();

  await TestHelpers.openNewEntryWizard($);
  await TestHelpers.navigateToWizardTab($, 'weather');

  // Test continues...
});
```

**Benefits**:
- Reduces code duplication across 13 Patrol tests
- Centralizes navigation logic
- Easier to update if navigation changes

---

## Phase 5: Auth Bypass Mechanism (MEDIUM PRIORITY)

**Effort**: 2-3 hours
**Impact**: Enables testing without Supabase credentials
**Agent**: `data-layer-agent` or `auth-agent`

### Overview
Create a test-only auth bypass that allows Patrol tests to skip authentication when running without Supabase configured.

---

### Task 5.1: Add Test-Only Auth Bypass Flag

**File**: `lib/core/config/supabase_config.dart`

**Changes**:

```dart
class SupabaseConfig {
  static const String url = String.fromEnvironment('SUPABASE_URL');
  static const String anonKey = String.fromEnvironment('SUPABASE_ANON_KEY');

  static bool get isConfigured => url.isNotEmpty && anonKey.isNotEmpty;

  // ADD THIS: Test bypass flag
  static const bool bypassAuthForTests = String.fromEnvironment(
    'BYPASS_AUTH_FOR_TESTS',
    defaultValue: 'false',
  ) == 'true';
}
```

---

### Task 5.2: Update Router Redirect Logic

**File**: `lib/core/router/app_router.dart`

**Changes**:

```dart
redirect: (context, state) {
  // BEFORE
  final isAuthenticated = SupabaseConfig.isConfigured &&
    Supabase.instance.client.auth.currentUser != null;

  // AFTER
  final isAuthenticated = SupabaseConfig.bypassAuthForTests ||
    (SupabaseConfig.isConfigured && Supabase.instance.client.auth.currentUser != null);

  // Rest of redirect logic...
}
```

---

### Task 5.3: Update Auth Provider for Test Bypass

**File**: `lib/features/auth/presentation/providers/auth_provider.dart`

**Changes**:

```dart
class AuthProvider extends ChangeNotifier {
  // ...

  /// Check if user is authenticated (bypasses auth in test mode)
  bool get isAuthenticated {
    if (SupabaseConfig.bypassAuthForTests) {
      return true;  // Always authenticated in test mode
    }

    return _isAuthenticated;
  }

  /// Sign in (bypasses in test mode)
  Future<bool> signIn({required String email, required String password}) async {
    if (SupabaseConfig.bypassAuthForTests) {
      _isAuthenticated = true;
      notifyListeners();
      return true;
    }

    // Normal sign-in logic...
  }
}
```

---

### Task 5.4: Update Patrol Test Configuration

**File**: `integration_test/patrol/test_config.dart`

**Add bypass documentation**:

```dart
/// Global test configuration for Patrol tests
///
/// Auth Bypass:
/// To run tests without Supabase credentials, use:
/// ```
/// patrol test --dart-define=BYPASS_AUTH_FOR_TESTS=true
/// ```
///
/// This bypasses authentication and allows tests to run completely offline.
class PatrolTestConfig {
  // ...
}
```

**Benefits**:
- Tests run without Supabase configuration
- No need to mock auth in every test
- True offline testing
- Faster test execution (no network calls)

**Tests Fixed**:
- All 13 Patrol test files can run offline
- Auth flow tests can test UI without actual Supabase calls

---

## Execution Order

### Sequential Implementation (Recommended)

**Week 1 (8 hours)**:
1. **Day 1-2**: Phase 1 (Critical Widget Keys) - 3-4 hours
2. **Day 2-3**: Phase 4 (Test Pattern Standardization) - 3-4 hours

**Week 2 (6 hours)**:
3. **Day 4**: Phase 2 (Dialog & Modal Keys) - 2-3 hours
4. **Day 5**: Phase 3 (Navigation Keys) - 2-3 hours

**Week 3 (Optional, 3 hours)**:
5. **Day 6**: Phase 5 (Auth Bypass) - 2-3 hours

### Parallel Implementation (If Multiple Agents Available)

**Stream 1** (flutter-specialist-agent):
- Phase 1: Critical Widget Keys (4 hours)
- Phase 2: Dialog & Modal Keys (3 hours)
- Phase 3: Navigation Keys (3 hours)

**Stream 2** (qa-testing-agent):
- Phase 4: Test Pattern Standardization (4 hours)

**Stream 3** (auth-agent):
- Phase 5: Auth Bypass (3 hours)

**Total Time**: ~10 hours with parallel execution

---

## Expected Test Results by Phase

| Phase | Tests Fixed | Cumulative Pass Rate |
|-------|-------------|----------------------|
| Start | N/A | 13/20 (65%) - Current state after Patrol fix plan |
| Phase 1 | 10 tests | 18/20 (90%) |
| Phase 2 | 2 tests | 19/20 (95%) |
| Phase 3 | 1 test | 20/20 (100%) |
| Phase 4 | 0 new (stability) | 20/20 (100%) |
| Phase 5 | 0 new (infrastructure) | 20/20 (100%) |

**Note**: Pass rate assumes Phases 1-4 of patrol_test_fix_plan_v2.md are complete.

---

## Files Modified Summary

### Lib Files (Widget Keys)

| File | Changes | Phase |
|------|---------|-------|
| `lib/features/entries/presentation/screens/home_screen.dart` | Add FAB, navigation tab Keys | Phase 1 |
| `lib/features/entries/presentation/screens/entry_wizard_screen.dart` | Add TabBar, button Keys | Phase 1 |
| `lib/features/entries/presentation/widgets/entry_basics_section.dart` | Add form field Keys | Phase 1 |
| `lib/features/entries/presentation/widgets/[weather_widget].dart` | Add weather button Keys | Phase 1 |
| `lib/features/auth/presentation/screens/register_screen.dart` | Add back button Key | Phase 1 |
| `lib/shared/widgets/confirmation_dialog.dart` | Add dialog and button Keys | Phase 2 |
| `lib/features/contractors/presentation/widgets/[contractor_dialog].dart` | Add form and button Keys | Phase 2 |
| `lib/features/photos/presentation/widgets/photo_source_dialog.dart` | Add gallery option Key | Phase 2 |
| `lib/main.dart` or scaffold | Add navigation bar Keys | Phase 3 |
| `lib/features/projects/presentation/screens/project_list_screen.dart` | Add FAB, card Keys | Phase 3 |
| `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` | Add widget section Keys | Phase 3 |
| `lib/core/config/supabase_config.dart` | Add auth bypass flag | Phase 5 |
| `lib/core/router/app_router.dart` | Update redirect for bypass | Phase 5 |
| `lib/features/auth/presentation/providers/auth_provider.dart` | Add bypass logic | Phase 5 |

**Total**: ~14 files

---

### Test Files (Pattern Updates)

| File | Changes | Phase |
|------|---------|-------|
| `integration_test/patrol/auth_flow_test.dart` | Replace text→Key selectors, remove conditionals | Phase 4 |
| `integration_test/patrol/entry_management_test.dart` | Replace text→Key selectors, remove conditionals | Phase 4 |
| `integration_test/patrol/contractors_flow_test.dart` | Remove conditional navigation | Phase 4 |
| `integration_test/patrol/project_management_test.dart` | Update to use Key selectors | Phase 4 |
| `integration_test/patrol/navigation_flow_test.dart` | Update to use Key selectors | Phase 4 |
| `integration_test/patrol/quantities_flow_test.dart` | Update to use Key selectors | Phase 4 |
| `integration_test/patrol/settings_flow_test.dart` | Update to use Key selectors | Phase 4 |
| `integration_test/helpers/test_helpers.dart` | CREATE new helper library | Phase 4 |
| `integration_test/patrol/test_config.dart` | Add bypass documentation | Phase 5 |

**Total**: ~9 files

---

## Investigation Tasks

Before implementation, investigate these unknowns:

### 1. Home Screen Navigation Widget
- **File**: `lib/features/entries/presentation/screens/home_screen.dart`
- **Find**: BottomNavigationBar, TabBar, or NavigationRail
- **Action**: Add Keys to all navigation items

### 2. Entry Wizard Tab Structure
- **File**: `lib/features/entries/presentation/screens/entry_wizard_screen.dart`
- **Find**: TabBar widget and all tab names
- **Action**: Verify tab count and names match test expectations

### 3. Weather Widget Location
- **Search**: `lib/features/entries/presentation/widgets/` or `lib/features/weather/`
- **Find**: Weather condition selection buttons
- **Action**: Add Keys to all weather options

### 4. Contractor Dialog Location
- **Search**: `lib/features/contractors/presentation/widgets/` or inline in project_setup_screen.dart
- **Find**: Add/edit contractor form dialog
- **Action**: Add Keys to all form fields and buttons

### 5. Main Navigation Structure
- **File**: Likely `lib/main.dart` or `lib/core/router/app_scaffold.dart`
- **Find**: Main app navigation widget
- **Action**: Add Keys to all navigation destinations

---

## Verification Checklist

After each phase:

### Phase 1 Verification
- [ ] Run `flutter analyze` - 0 errors
- [ ] Run `flutter test` - all unit tests pass
- [ ] Run `patrol test integration_test/patrol/entry_management_test.dart`
- [ ] Verify 8+ entry tests pass
- [ ] Run `patrol test integration_test/patrol/auth_flow_test.dart`
- [ ] Verify test 7 passes

### Phase 2 Verification
- [ ] Run `flutter analyze` - 0 errors
- [ ] Run `patrol test integration_test/patrol/contractors_flow_test.dart`
- [ ] Verify contractor tests 1, 3 pass
- [ ] Run `patrol test integration_test/patrol/entry_management_test.dart`
- [ ] Verify tests 9, 11 pass

### Phase 3 Verification
- [ ] Run `flutter analyze` - 0 errors
- [ ] Run `patrol test integration_test/patrol/navigation_flow_test.dart`
- [ ] Verify all navigation tests pass
- [ ] Run `patrol test integration_test/patrol/project_management_test.dart`
- [ ] Verify project CRUD tests pass

### Phase 4 Verification
- [ ] Run `flutter analyze` - 0 errors
- [ ] Run `patrol test` - all 20 tests
- [ ] Verify 100% pass rate
- [ ] Code review: No text-based selectors remain in test files
- [ ] Code review: No conditional `.exists` checks masking failures

### Phase 5 Verification
- [ ] Run tests without Supabase config:
  ```bash
  patrol test --dart-define=BYPASS_AUTH_FOR_TESTS=true
  ```
- [ ] Verify all tests pass in bypass mode
- [ ] Run tests WITH Supabase config (normal mode)
- [ ] Verify bypass doesn't affect normal operation
- [ ] Test auth flow still works with real Supabase

---

## Success Criteria

### Primary Goals
1. **Pass Rate**: 20/20 Patrol tests passing (100%)
2. **Zero Text Selectors**: All tests use Key selectors
3. **Test Helpers**: Reusable helper library implemented
4. **Auth Bypass**: Tests can run completely offline

### Secondary Goals
1. **Execution Time**: Patrol test suite completes in < 5 minutes
2. **Flakiness**: Tests run 3x in a row without new failures
3. **Maintainability**: Adding new tests requires minimal boilerplate
4. **Documentation**: All test patterns documented in test_helpers.dart

### Quality Metrics
- 0 analyzer errors introduced
- 363 unit tests still passing
- Test code coverage > 70% (measure with `flutter test --coverage`)
- No hardcoded timeouts > 10 seconds (indicates fragile test)

---

## Risk Mitigation

### High Risk Items

**1. Home Screen Navigation Unknown**
- **Risk**: Can't find navigation widget
- **Mitigation**: Search entire codebase for BottomNavigationBar, TabBar
- **Fallback**: Ask user to identify navigation widget location

**2. Weather Widget Location Unknown**
- **Risk**: Widget may be inline, not separate file
- **Mitigation**: Search for weather-related Icons in entry wizard
- **Fallback**: Add Keys inline in entry_wizard_screen.dart

**3. Auth Bypass Breaking Real Auth**
- **Risk**: Bypass flag affects production
- **Mitigation**: Only use String.fromEnvironment (compile-time, not runtime)
- **Test**: Verify normal build doesn't have bypass enabled

### Medium Risk Items

**1. Dynamic Widget Keys**
- **Risk**: Keys with dynamic IDs may cause test brittleness
- **Mitigation**: Use predictable, stable ID patterns
- **Example**: `Key('project_card_${project.id}')` instead of `Key('card_$index')`

**2. Test Helper Over-Engineering**
- **Risk**: Helpers become too complex, hide test logic
- **Mitigation**: Keep helpers simple, 1-2 actions max
- **Rule**: If helper has > 3 parameters, make it more specific

### Low Risk Items

**1. Key Naming Collisions**
- **Risk**: Two widgets have same Key
- **Mitigation**: Use descriptive, scoped Key names
- **Pattern**: `[feature]_[widget]_[action]` (e.g., `entry_wizard_save_draft`)

**2. Performance Impact of Keys**
- **Risk**: Adding Keys slows down app
- **Mitigation**: Keys have zero runtime overhead in Flutter
- **Evidence**: Keys are compile-time metadata

---

## Agent Assignments

### Phase 1: flutter-specialist-agent
**Focus**: Widget Keys implementation
**Command**: Add Keys to all critical interaction widgets
**Files**: 6 lib files (entry screens, auth screens, widgets)

### Phase 2: flutter-specialist-agent
**Focus**: Dialog and modal Keys
**Command**: Add Keys to dialogs, forms, confirmation prompts
**Files**: 3 lib files (dialogs, contractor widgets)

### Phase 3: flutter-specialist-agent
**Focus**: Navigation Keys
**Command**: Add Keys to navigation bars, tabs, FABs
**Files**: 3 lib files (main scaffold, project/dashboard screens)

### Phase 4: qa-testing-agent
**Focus**: Test pattern refactoring
**Command**: Replace text selectors, remove conditionals, create helpers
**Files**: 9 integration test files

### Phase 5: auth-agent OR data-layer-agent
**Focus**: Auth bypass mechanism
**Command**: Implement test-only auth bypass flag
**Files**: 3 lib files (config, router, auth provider)

---

## Post-Implementation

### Documentation Updates

**1. Update Test README**
- File: `integration_test/patrol/README.md`
- Add: Key naming conventions
- Add: Test helper usage examples
- Add: Auth bypass instructions

**2. Update CLAUDE.md**
- Section: Testing Guidelines
- Add: Link to test_helpers.dart
- Add: Key selector best practices

**3. Create Test Patterns Guide**
- File: `.claude/rules/testing-patterns.md`
- Content: When to use Keys vs text vs icons
- Content: How to write stable Patrol tests

### Maintenance Tasks

**1. Audit Existing Tests**
- Review all 45 unit tests for text selectors
- Update golden tests if UI changed
- Verify widget tests use Keys where appropriate

**2. Add Pre-Commit Hook**
- Check: No new text selectors in integration tests
- Check: All new interactive widgets have Keys
- Tool: Use grep to enforce patterns

**3. Monitor Test Stability**
- Track: Test pass rate over 7 days
- Alert: If pass rate drops below 95%
- Action: Investigate flaky tests immediately

---

## Notes

### Device-Specific Considerations
- Keys are device-agnostic (work on all platforms)
- Auth bypass tested on Android, should work on iOS
- Navigation widget may differ on tablet vs phone layouts

### Localization Impact
- Text selectors fail with locale changes
- Key selectors unaffected by language
- This plan makes app more testable in multiple languages

### Test Isolation
- Auth bypass allows true test isolation
- No shared state between tests
- Each test can run independently

### Future Enhancements
- Consider: Mock data service for offline testing
- Consider: Test data seeding helpers
- Consider: Screenshot comparison testing (golden images)

---

## Appendix: Key Naming Conventions

### Pattern
`[feature]_[screen/widget]_[element]_[action/type]`

### Examples
```dart
// Auth
Key('login_email_field')
Key('login_sign_in_button')
Key('register_screen_title')
Key('forgot_password_submit_button')

// Entries
Key('add_entry_fab')
Key('entry_wizard_tabs')
Key('entry_wizard_tab_weather')
Key('entry_wizard_save_draft')
Key('entry_card_${entryId}')

// Projects
Key('add_project_fab')
Key('project_details_tab')
Key('project_save_button')
Key('project_card_${projectId}')

// Navigation
Key('nav_home')
Key('nav_projects')
Key('home_tab')
Key('calendar_tab')

// Dialogs
Key('confirmation_dialog')
Key('confirmation_dialog_cancel')
Key('delete_confirm_button')
Key('discard_dialog_button')

// Weather
Key('weather_sunny')
Key('weather_cloudy')
Key('weather_rainy')

// Contractors
Key('contractor_name_field')
Key('contractor_type_prime')
Key('contractor_save_button')
```

### Anti-Patterns (Avoid)
```dart
// TOO GENERIC
Key('button')
Key('field1')

// TOO SPECIFIC (brittle)
Key('submit_button_on_line_145')
Key('text_field_with_blue_border')

// DYNAMIC INDEX (fragile)
Key('item_$index')  // Bad: index changes when list reorders
Key('item_${item.id}')  // Good: stable ID

// MIXED NAMING STYLES
Key('LoginEmailField')  // PascalCase
Key('login-email-field')  // kebab-case
// Use: snake_case consistently
```

---

**END OF PLAN**
