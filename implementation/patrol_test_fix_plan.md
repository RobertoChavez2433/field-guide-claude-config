# Patrol Test Fix & Test Infrastructure Improvement Plan

**Last Updated**: 2026-01-21
**Status**: READY FOR IMPLEMENTATION
**Source**: Synthesized from 4 research agents' findings (Session 25)

---

## Overview

This plan addresses the current state where Patrol tests execute on device but have low pass rates (3/69 passing, ~13 failing on test-specific issues). The plan focuses on improving test reliability, reducing redundancy, and filling coverage gaps across the entire test infrastructure.

**Current Test State**:
- 613 unit tests passing
- 93 golden tests passing
- 69 Patrol tests (infrastructure working, but fragile)
- Issues: widget not found, permission dialogs, timing, text-based finders

---

## Phase 1: Quick Wins - Test Cleanup (1-2 hours)

### Priority: CRITICAL
**Agent**: `qa-testing-agent`

### Task 1.1: Delete Redundant Test Files

**DELETE ENTIRELY** (save ~350 lines):
```
test/widget_test.dart                                    # Placeholder only (11 lines)
test/data/datasources/contractor_datasource_test.dart    # Tests mock, not real code
test/data/datasources/location_datasource_test.dart      # Tests mock, not real code
test/data/datasources/entry_datasource_test.dart         # Tests mock, not real code
```

**Verification**:
```bash
flutter test  # Should still pass 613 tests (minus these ~15)
```

### Task 1.2: Consolidate Model Tests

**Target**: 8 model test files (2111 lines → reduce 75% to ~528 lines)

**Create Generic Test Utility** (`test/helpers/model_test_helpers.dart`):
```dart
/// Generic model test suite - DRY for all models
class ModelTestSuite<T> {
  final T Function(Map<String, dynamic>) fromMap;
  final Map<String, dynamic> Function(T) toMap;
  final T validInstance;
  final Map<String, dynamic> validMap;

  void runStandardTests() {
    test('fromMap creates valid instance', () {
      final result = fromMap(validMap);
      expect(result, isNotNull);
    });

    test('toMap produces valid map', () {
      final map = toMap(validInstance);
      expect(map, isA<Map<String, dynamic>>());
    });

    test('roundtrip preserves data', () {
      final map = toMap(validInstance);
      final result = fromMap(map);
      expect(toMap(result), equals(map));
    });
  }
}
```

**Refactor Model Tests** (8 files):
```
test/features/projects/data/models/project_test.dart
test/features/locations/data/models/location_test.dart
test/features/entries/data/models/daily_entry_test.dart
test/features/quantities/data/models/bid_item_test.dart
test/features/contractors/data/models/contractor_test.dart
test/features/contractors/data/models/equipment_test.dart
test/features/quantities/data/models/entry_quantity_test.dart
test/features/photos/data/models/photo_test.dart
```

**Pattern** (reduce each file from ~250 lines to ~60 lines):
```dart
void main() {
  final testSuite = ModelTestSuite<Project>(
    fromMap: Project.fromMap,
    toMap: (p) => p.toMap(),
    validInstance: TestData.createProject(),
    validMap: TestData.createProject().toMap(),
  );

  group('Project Model', () {
    testSuite.runStandardTests();

    // Only test Project-specific edge cases
    test('isActive defaults to true', () {
      final project = Project(name: 'Test', projectNumber: '123');
      expect(project.isActive, true);
    });
  });
}
```

**Estimated Savings**: ~1,583 lines

---

## Phase 2: Widget Keys Addition (2-3 hours)

### Priority: CRITICAL
**Agent**: `flutter-specialist-agent`

### Task 2.1: Authentication Screens (30 min)

**File**: `lib/features/auth/presentation/screens/register_screen.dart`

Add Keys (currently missing):
```dart
// Line ~80 (email field)
TextFormField(
  key: const Key('register_email_field'),  // ADD
  controller: _emailController,
  // ...
)

// Line ~95 (password field)
TextFormField(
  key: const Key('register_password_field'),  // ADD
  controller: _passwordController,
  // ...
)

// Line ~110 (confirm password field)
TextFormField(
  key: const Key('register_confirm_password_field'),  // ADD
  controller: _confirmPasswordController,
  // ...
)

// Line ~130 (sign up button)
ElevatedButton(
  key: const Key('register_sign_up_button'),  // ADD
  onPressed: _handleSignUp,
  child: const Text('Sign Up'),
)

// Line ~145 (back to login link)
TextButton(
  key: const Key('register_back_to_login_button'),  // ADD
  onPressed: () => context.push('/login'),
  child: const Text('Sign In'),
)
```

**File**: `lib/features/auth/presentation/screens/forgot_password_screen.dart`

Add Keys (currently missing):
```dart
// Email field
TextFormField(
  key: const Key('forgot_password_email_field'),  // ADD
  // ...
)

// Submit button
ElevatedButton(
  key: const Key('forgot_password_submit_button'),  // ADD
  // ...
)

// Back button
TextButton(
  key: const Key('forgot_password_back_button'),  // ADD
  // ...
)
```

**Files Already Complete**:
- `lib/features/auth/presentation/screens/login_screen.dart` (4 Keys already present)

### Task 2.2: Entry Management Screens (60 min)

**File**: `lib/features/entries/presentation/screens/entry_wizard_screen.dart`

**CRITICAL**: Entry wizard has NO Keys. Add to major navigation/actions:

```dart
// Line ~150 (wizard stepper/tabs)
TabBar(
  key: const Key('entry_wizard_tabs'),  // ADD
  tabs: [
    Tab(key: const Key('entry_wizard_tab_general'), text: 'General'),
    Tab(key: const Key('entry_wizard_tab_weather'), text: 'Weather'),
    Tab(key: const Key('entry_wizard_tab_activities'), text: 'Activities'),
    Tab(key: const Key('entry_wizard_tab_personnel'), text: 'Personnel'),
    Tab(key: const Key('entry_wizard_tab_equipment'), text: 'Equipment'),
    Tab(key: const Key('entry_wizard_tab_quantities'), text: 'Quantities'),
    Tab(key: const Key('entry_wizard_tab_photos'), text: 'Photos'),
  ],
)

// Line ~250 (project dropdown)
DropdownButtonFormField<String>(
  key: const Key('entry_wizard_project_dropdown'),  // ADD
  // ...
)

// Line ~280 (location dropdown)
DropdownButtonFormField<String>(
  key: const Key('entry_wizard_location_dropdown'),  // ADD
  // ...
)

// Line ~320 (date picker)
InkWell(
  key: const Key('entry_wizard_date_picker'),  // ADD
  onTap: _selectDate,
  // ...
)

// Line ~450 (weather condition buttons)
IconButton(
  key: const Key('weather_sunny'),  // ADD
  icon: const Icon(Icons.wb_sunny),
  // ...
)
IconButton(
  key: const Key('weather_cloudy'),  // ADD
  icon: const Icon(Icons.cloud),
  // ...
)
IconButton(
  key: const Key('weather_rainy'),  // ADD
  icon: const Icon(Icons.water_drop),
  // ...
)

// Line ~520 (temperature fields)
TextFormField(
  key: const Key('entry_wizard_temp_low'),  // ADD
  controller: _tempLowController,
  // ...
)
TextFormField(
  key: const Key('entry_wizard_temp_high'),  // ADD
  controller: _tempHighController,
  // ...
)

// Line ~600 (activities text field)
TextFormField(
  key: const Key('entry_wizard_activities'),  // ADD
  controller: _activitiesController,
  maxLines: 8,
  // ...
)

// Line ~700 (save draft button)
TextButton(
  key: const Key('entry_wizard_save_draft'),  // ADD
  onPressed: _saveDraft,
  child: const Text('Save Draft'),
)

// Line ~710 (submit button)
ElevatedButton(
  key: const Key('entry_wizard_submit'),  // ADD
  onPressed: _submit,
  child: const Text('Submit'),
)

// Line ~100 (cancel/close button)
IconButton(
  key: const Key('entry_wizard_close'),  // ADD
  icon: const Icon(Icons.close),
  onPressed: _handleCancel,
)
```

**File**: `lib/features/entries/presentation/screens/home_screen.dart`

Already has:
- `add_entry_fab` (line 466) ✓
- `entry_card_{id}` (line 1778) ✓

Add missing:
```dart
// Line ~800 (calendar navigation)
IconButton(
  key: const Key('calendar_prev_month'),  // ADD
  icon: const Icon(Icons.chevron_left),
  // ...
)
IconButton(
  key: const Key('calendar_next_month'),  // ADD
  icon: const Icon(Icons.chevron_right),
  // ...
)

// Line ~1200 (filter dropdown)
DropdownButton<String>(
  key: const Key('entry_filter_dropdown'),  // ADD
  // ...
)

// Line ~1500 (edit entry button in card)
IconButton(
  key: Key('entry_edit_${entry.id}'),  // ADD (dynamic)
  icon: const Icon(Icons.edit),
  // ...
)

// Line ~1520 (delete entry button in card)
IconButton(
  key: Key('entry_delete_${entry.id}'),  // ADD (dynamic)
  icon: const Icon(Icons.delete),
  // ...
)
```

### Task 2.3: Project Management Screens (30 min)

**File**: `lib/features/projects/presentation/screens/project_list_screen.dart`

Already has:
- `add_project_fab` (line 82) ✓
- `project_card_{id}` (line 190) ✓

Add missing:
```dart
// Line ~120 (filter toggle)
IconButton(
  key: const Key('project_filter_toggle'),  // ADD
  icon: const Icon(Icons.filter_list),
  // ...
)

// Line ~150 (search field)
TextField(
  key: const Key('project_search_field'),  // ADD
  // ...
)

// Line ~200+ (in project card)
IconButton(
  key: Key('project_edit_${project.id}'),  // ADD (dynamic)
  icon: const Icon(Icons.edit),
  // ...
)
```

**File**: `lib/features/projects/presentation/screens/project_setup_screen.dart`

Add Keys to all form fields:
```dart
TextFormField(
  key: const Key('project_name_field'),  // ADD
  // ...
)
TextFormField(
  key: const Key('project_number_field'),  // ADD
  // ...
)
TextFormField(
  key: const Key('project_client_field'),  // ADD
  // ...
)
ElevatedButton(
  key: const Key('project_save_button'),  // ADD
  // ...
)
```

### Task 2.4: Dashboard & Settings (20 min)

**File**: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`

Already has:
- `dashboard_entries_card` (line 234) ✓
- `dashboard_locations_card` (line 245) ✓
- `dashboard_pay_items_card` (line 265) ✓

Good coverage. No immediate additions needed.

**File**: `lib/features/settings/presentation/screens/settings_screen.dart`

Add Keys:
```dart
// Theme selector
DropdownButton<ThemeMode>(
  key: const Key('settings_theme_dropdown'),  // ADD
  // ...
)

// Sync settings button
ListTile(
  key: const Key('settings_sync_tile'),  // ADD
  title: const Text('Sync Settings'),
  // ...
)

// Personnel types button
ListTile(
  key: const Key('settings_personnel_types_tile'),  // ADD
  title: const Text('Personnel Types'),
  // ...
)

// Sign out button
ListTile(
  key: const Key('settings_sign_out_tile'),  // ADD
  title: const Text('Sign Out'),
  // ...
)
```

### Task 2.5: Contractor & Quantities Screens (20 min)

**File**: `lib/features/contractors/presentation/screens/contractor_list_screen.dart`

Add Keys (if file exists):
```dart
FloatingActionButton(
  key: const Key('add_contractor_fab'),  // ADD
  // ...
)
```

**File**: `lib/features/quantities/presentation/screens/quantities_screen.dart`

Add Keys:
```dart
FloatingActionButton(
  key: const Key('add_bid_item_fab'),  // ADD
  // ...
)
```

**Summary**:
- Total Keys to Add: ~50+
- Files Modified: 10
- Priority Order: Entry wizard → Auth → Projects → Dashboard/Settings → Contractors/Quantities

---

## Phase 3: Test Helper Refactoring (2-3 hours)

### Priority: HIGH
**Agent**: `qa-testing-agent`

### Task 3.1: Extract Shared Mocks (60 min)

**Problem**: 15+ inline `_Mock*` classes duplicated across test files

**Create**: `test/helpers/mocks/` directory structure:
```
test/helpers/mocks/
├── mock_repositories.dart      # All repository mocks
├── mock_providers.dart         # All provider mocks
└── mock_services.dart          # All service mocks
```

**File**: `test/helpers/mocks/mock_repositories.dart`
```dart
import 'package:construction_inspector/shared/data/repository_result.dart';
import 'package:construction_inspector/features/projects/data/repositories/project_repository.dart';
// ... other imports

/// Shared mock for ProjectRepository
class MockProjectRepository implements ProjectRepository {
  final List<Project> _projects = [];

  @override
  Future<RepositoryResult<List<Project>>> getAll() async {
    return RepositoryResult.success(_projects);
  }

  @override
  Future<RepositoryResult<Project>> create(Project project) async {
    _projects.add(project);
    return RepositoryResult.success(project);
  }

  // ... other standard CRUD methods with consistent sorting

  void addTestData(List<Project> projects) {
    _projects.addAll(projects);
  }

  void clear() {
    _projects.clear();
  }
}

// Repeat for other repositories:
// - MockLocationRepository
// - MockDailyEntryRepository
// - MockBidItemRepository
// - MockContractorRepository
// - MockPhotoRepository
```

**File**: `test/helpers/mocks/mock_providers.dart`
```dart
import 'package:flutter/foundation.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_provider.dart';
// ... other imports

/// Shared mock for ProjectProvider (minimal for widget tests)
class MockProjectProvider extends ChangeNotifier {
  final List<Project> _projects = [];

  List<Project> get projects => _projects;

  void setProjects(List<Project> projects) {
    _projects.clear();
    _projects.addAll(projects);
    notifyListeners();
  }
}

// Repeat for other providers:
// - MockDailyEntryProvider
// - MockLocationProvider
// - MockBidItemProvider
```

**Refactor Existing Tests** to use shared mocks (15+ files):
```dart
// OLD (inline mock - REMOVE)
class _MockProjectRepository implements ProjectRepository {
  final List<Project> _projects = [];
  // ... 50+ lines
}

// NEW (shared mock - USE)
import 'package:construction_inspector/test/helpers/mocks/mock_repositories.dart';

void main() {
  late MockProjectRepository mockRepo;

  setUp(() {
    mockRepo = MockProjectRepository();
  });

  test('...', () async {
    mockRepo.addTestData([TestData.createProject()]);
    // ... test
  });
}
```

**Files to Refactor** (15 files, ~1200 lines saved):
```
test/features/projects/data/repositories/project_repository_test.dart
test/features/locations/data/repositories/location_repository_test.dart
test/features/entries/data/repositories/daily_entry_repository_test.dart
test/features/quantities/data/repositories/bid_item_repository_test.dart
test/features/contractors/data/repositories/contractor_repository_test.dart
test/features/photos/data/repositories/photo_repository_test.dart
test/features/projects/presentation/providers/project_provider_test.dart
test/features/entries/presentation/providers/daily_entry_provider_test.dart
test/features/locations/presentation/providers/location_provider_test.dart
test/features/quantities/presentation/providers/bid_item_provider_test.dart
test/features/contractors/presentation/providers/contractor_provider_test.dart
test/services/photo_service_test.dart
test/services/sync_service_test.dart (if exists)
```

### Task 3.2: Centralize Sorting Logic (30 min)

**Problem**: 18 different sort implementations fragmented in mocks

**Create**: `test/helpers/test_sorting.dart`
```dart
/// Centralized sorting utilities for test consistency
class TestSorting {
  /// Sort projects by updated_at DESC (newest first)
  static List<Project> sortProjects(List<Project> projects) {
    final sorted = List<Project>.from(projects);
    sorted.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    return sorted;
  }

  /// Sort entries by date DESC (newest first)
  static List<DailyEntry> sortEntries(List<DailyEntry> entries) {
    final sorted = List<DailyEntry>.from(entries);
    sorted.sort((a, b) => b.date.compareTo(a.date));
    return sorted;
  }

  /// Sort by item number (numeric sort)
  static List<BidItem> sortBidItems(List<BidItem> items) {
    final sorted = List<BidItem>.from(items);
    sorted.sort((a, b) {
      final aNum = int.tryParse(a.itemNumber) ?? 0;
      final bNum = int.tryParse(b.itemNumber) ?? 0;
      return aNum.compareTo(bNum);
    });
    return sorted;
  }

  /// Sort by name alphabetically
  static List<Location> sortLocations(List<Location> locations) {
    final sorted = List<Location>.from(locations);
    sorted.sort((a, b) => a.name.compareTo(b.name));
    return sorted;
  }

  // Add other domain-specific sorts as needed
}
```

**Update Mock Repositories** to use centralized sorting:
```dart
// In mock_repositories.dart
class MockProjectRepository implements ProjectRepository {
  @override
  Future<RepositoryResult<List<Project>>> getAll() async {
    final sorted = TestSorting.sortProjects(_projects);
    return RepositoryResult.success(sorted);
  }
}
```

### Task 3.3: Fix Seed Data Timestamps (20 min)

**Problem**: All seed data records have identical timestamps (breaks sort tests)

**File**: `lib/core/database/seed_data_service.dart`

**Current** (lines 473-730):
```dart
final now = DateTime.now().toIso8601String();

// All entries get same timestamp
db.insert('entry_personnel', {
  'created_at': now,  // PROBLEM: All identical
  'updated_at': now,
  // ...
});
```

**Fix** (add variance):
```dart
Future<void> seedDatabase(Database db) async {
  final baseTime = DateTime.now();

  // Helper to create timestamps with variance
  DateTime variedTime(int minutesOffset) {
    return baseTime.subtract(Duration(minutes: minutesOffset));
  }

  // Example: Vary entry timestamps by 10 minutes each
  int offset = 0;
  for (final entryData in testEntries) {
    final timestamp = variedTime(offset).toIso8601String();
    db.insert('entries', {
      'created_at': timestamp,
      'updated_at': timestamp,
      // ...
    });
    offset += 10;
  }

  // Apply same pattern to:
  // - entry_personnel (offset by 5 min each)
  // - entry_quantities (offset by 5 min each)
  // - entry_equipment (offset by 5 min each)
  // - photos (offset by 15 min each)
}
```

### Task 3.4: Create Patrol Test Helper (40 min)

**Create**: `integration_test/helpers/auth_test_helper.dart`
```dart
import 'package:patrol/patrol.dart';
import 'package:construction_inspector/main.dart' as app;

/// Reusable authentication helper for Patrol tests
class AuthTestHelper {
  final PatrolTester $;

  AuthTestHelper(this.$);

  /// Launch app and verify on login screen
  Future<void> launchApp() async {
    app.main();
    await $.pumpAndSettle();
    await waitForLoginScreen();
  }

  /// Wait for login screen to appear
  Future<void> waitForLoginScreen() async {
    await $.waitUntilVisible($(Key('login_email_field')));
  }

  /// Sign in with test credentials (assumes demo mode or test account)
  Future<void> signInAsGuest() async {
    // For tests, use demo mode or test account
    // This pattern allows tests to bypass auth if needed
    await $.tap($(Key('login_email_field')));
    await $.enterText($('demo@test.com'));
    await $.pumpAndSettle();

    await $.tap($(Key('login_password_field')));
    await $.enterText($('testpass123'));
    await $.pumpAndSettle();

    await $.tap($(Key('login_sign_in_button')));
    await $.pumpAndSettle();

    // Wait for navigation to dashboard
    await waitForDashboard();
  }

  /// Wait for dashboard to appear after login
  Future<void> waitForDashboard() async {
    await $.waitUntilVisible($(Key('add_entry_fab')), timeout: Duration(seconds: 10));
  }

  /// Sign out (navigate to settings, tap sign out)
  Future<void> signOut() async {
    final settingsIcon = $(Icons.settings);
    if (settingsIcon.exists) {
      await settingsIcon.tap();
      await $.pumpAndSettle();

      await $.tap($(Key('settings_sign_out_tile')));
      await $.pumpAndSettle();

      // Confirm if dialog appears
      final confirmButton = $('Sign Out');
      if (confirmButton.exists) {
        await confirmButton.tap();
        await $.pumpAndSettle();
      }
    }
  }

  /// Reset app state between tests
  Future<void> resetAppState() async {
    // Clear permissions (if possible via Patrol)
    try {
      await $.native.grantPermissionWhenInUse(); // Reset to default
    } catch (e) {
      // Ignore if not supported
    }

    // Restart app
    await launchApp();
  }
}
```

**Create**: `integration_test/helpers/navigation_helper.dart`
```dart
import 'package:flutter/material.dart';
import 'package:patrol/patrol.dart';

/// Reusable navigation patterns for Patrol tests
class NavigationHelper {
  final PatrolTester $;

  NavigationHelper(this.$);

  /// Navigate to Calendar/Home tab
  Future<void> goToHomeTab() async {
    final homeTab = $('Home');
    final calendarTab = $('Calendar');
    final entriesTab = $('Entries');

    if (homeTab.exists) {
      await homeTab.tap();
    } else if (calendarTab.exists) {
      await calendarTab.tap();
    } else if (entriesTab.exists) {
      await entriesTab.tap();
    }
    await $.pumpAndSettle();
  }

  /// Navigate to Projects tab
  Future<void> goToProjectsTab() async {
    final projectsTab = $('Projects');
    if (projectsTab.exists) {
      await projectsTab.tap();
      await $.pumpAndSettle();
    }
  }

  /// Navigate to Dashboard tab
  Future<void> goToDashboardTab() async {
    final dashboardTab = $('Dashboard');
    if (dashboardTab.exists) {
      await dashboardTab.tap();
      await $.pumpAndSettle();
    }
  }

  /// Open FAB menu (if exists)
  Future<void> tapAddEntryFab() async {
    await $.tap($(Key('add_entry_fab')));
    await $.pumpAndSettle();
  }

  /// Wait for element with custom timeout
  Future<void> waitFor(dynamic selector, {Duration timeout = const Duration(seconds: 5)}) async {
    await $.waitUntilVisible(selector, timeout: timeout);
  }
}
```

**Update Patrol Tests** to use helpers:
```dart
// In auth_flow_test.dart
import '../helpers/auth_test_helper.dart';

void main() {
  patrolTest('displays login screen on app launch', ($) async {
    final auth = AuthTestHelper($);
    await auth.launchApp();

    // Verify login screen elements
    expect($(Key('login_email_field')), findsOneWidget);
    expect($(Key('login_password_field')), findsOneWidget);
  });
}

// In entry_management_test.dart
import '../helpers/auth_test_helper.dart';
import '../helpers/navigation_helper.dart';

void main() {
  patrolTest('creates new entry', ($) async {
    final auth = AuthTestHelper($);
    final nav = NavigationHelper($);

    await auth.launchApp();
    await auth.signInAsGuest();
    await nav.goToHomeTab();
    await nav.tapAddEntryFab();

    // Entry wizard should open
    expect($(Key('entry_wizard_tabs')), findsOneWidget);
  });
}
```

**Estimated Savings**: ~800 lines of duplicated code removed

---

## Phase 4: Patrol Test Fixes (3-4 hours)

### Priority: HIGH
**Agent**: `qa-testing-agent`

### Task 4.1: Replace Fixed Delays with waitUntilVisible (60 min)

**Problem**: Tests use `Future.delayed(seconds: 3)` instead of waiting for specific elements

**Pattern to Replace** (found in 10+ tests):
```dart
// BAD (current)
await Future.delayed(const Duration(seconds: 3));
await $.pumpAndSettle();

// GOOD (replace with)
await $.waitUntilVisible($(Key('expected_element')));
```

**Files to Fix**:
```
integration_test/patrol/entry_management_test.dart  (8 occurrences)
integration_test/patrol/auth_flow_test.dart         (4 occurrences)
integration_test/patrol/project_management_test.dart (6 occurrences)
integration_test/patrol/navigation_flow_test.dart   (3 occurrences)
```

**Example Fix** (`entry_management_test.dart` line 23):
```dart
// OLD
patrolTest('displays calendar/home screen with entries', ($) async {
  app.main();
  await $.pumpAndSettle();

  await Future.delayed(const Duration(seconds: 3));  // REMOVE
  await $.pumpAndSettle();

  // Navigate to calendar/home tab
  final calendarTab = $('Calendar');
  // ...
});

// NEW
patrolTest('displays calendar/home screen with entries', ($) async {
  final auth = AuthTestHelper($);
  final nav = NavigationHelper($);

  await auth.launchApp();
  await auth.signInAsGuest();  // Handle auth properly
  await nav.goToHomeTab();

  // Verify add entry FAB is visible (means screen loaded)
  await $.waitUntilVisible($(Key('add_entry_fab')));
  expect($(Key('add_entry_fab')), findsOneWidget);
});
```

### Task 4.2: Replace Text Finders with Key Finders (45 min)

**Problem**: Tests use fragile `$('Text')` finders that break on UI text changes

**Pattern to Replace**:
```dart
// BAD (current - breaks if text changes)
await $('Sign In').tap();
await $('Save Draft').tap();

// GOOD (replace with - stable)
await $(Key('login_sign_in_button')).tap();
await $(Key('entry_wizard_save_draft')).tap();
```

**Files to Fix** (all patrol tests):
```
integration_test/patrol/auth_flow_test.dart          (~15 text finders)
integration_test/patrol/entry_management_test.dart   (~25 text finders)
integration_test/patrol/project_management_test.dart (~10 text finders)
integration_test/patrol/navigation_flow_test.dart    (~8 text finders)
integration_test/patrol/app_smoke_test.dart          (~5 text finders)
```

**Mapping** (create reference doc):
```dart
// Auth Flow
'Sign In' → Key('login_sign_in_button')
'Sign Up' → Key('login_sign_up_button')
'Forgot password?' → Key('forgot_password_link') // ADD THIS KEY
'Email' → Key('login_email_field') // Already has key
'Password' → Key('login_password_field') // Already has key

// Entry Management
'Next' → Key('entry_wizard_next_button') // ADD THIS KEY
'Save Draft' → Key('entry_wizard_save_draft')
'Submit' → Key('entry_wizard_submit')
'Weather' → Key('entry_wizard_tab_weather')
'Activities' → Key('entry_wizard_tab_activities')
'Low Temp' → Key('entry_wizard_temp_low')
'High Temp' → Key('entry_wizard_temp_high')

// Projects
'Projects' → Key('projects_tab') // ADD THIS KEY
'New Project' → Key('add_project_fab')

// Settings
'Settings' → Key('settings_tab') // ADD THIS KEY
'Sign Out' → Key('settings_sign_out_tile')
```

### Task 4.3: Add State Reset Between Tests (30 min)

**Problem**: Tests don't reset permissions/state, causing cross-test contamination

**Create**: `integration_test/patrol/test_config.dart`
```dart
import 'package:patrol/patrol.dart';

/// Global test configuration for Patrol tests
class PatrolTestConfig {
  /// Standard timeout for widget visibility
  static const existsTimeout = Duration(seconds: 10);

  /// Standard config
  static const PatrolTesterConfig standard = PatrolTesterConfig(
    existsTimeout: existsTimeout,
  );

  /// Config for permission tests (longer timeout)
  static const PatrolTesterConfig permissions = PatrolTesterConfig(
    existsTimeout: Duration(seconds: 15),
  );

  /// Config for slow operations (network, database)
  static const PatrolTesterConfig slow = PatrolTesterConfig(
    existsTimeout: Duration(seconds: 20),
  );
}
```

**Add setUp/tearDown** to each test file:
```dart
void main() {
  late AuthTestHelper auth;

  setUp(() {
    // Initialize helpers (will be recreated for each test)
  });

  tearDown(() async {
    // Note: Patrol doesn't support full app reset between tests
    // Best practice: Each test should be independent
    // Use auth.resetAppState() if needed within test
  });

  patrolTest(
    'test name',
    ($) async {
      auth = AuthTestHelper($);
      await auth.launchApp();
      // ... test
    },
    config: PatrolTestConfig.standard,
  );
}
```

### Task 4.4: Fix Specific Failing Tests (90 min)

**Test**: `auth_flow_test.dart` - "handles invalid credentials with error message" (line 84)

**Issue**: Waits for error but doesn't check for specific element

**Fix**:
```dart
patrolTest('handles invalid credentials with error message', ($) async {
  final auth = AuthTestHelper($);
  await auth.launchApp();

  // Enter invalid credentials
  await $(Key('login_email_field')).enterText('wrong@example.com');
  await $.pumpAndSettle();

  await $(Key('login_password_field')).enterText('wrongpassword');
  await $.pumpAndSettle();

  // Tap sign in
  await $(Key('login_sign_in_button')).tap();
  await $.pumpAndSettle();

  // Wait for error SnackBar (NOT fixed delay)
  // SnackBar contains 'Invalid login credentials' or similar
  await $.waitUntilVisible($('Invalid'), timeout: Duration(seconds: 5));

  // Verify error message visible
  expect($('Invalid'), findsWidgets);  // Partial text match
});
```

**Test**: `entry_management_test.dart` - "opens create entry wizard from FAB" (line 52)

**Issue**: Doesn't verify wizard actually opened

**Fix**:
```dart
patrolTest('opens create entry wizard from FAB', ($) async {
  final auth = AuthTestHelper($);
  final nav = NavigationHelper($);

  await auth.launchApp();
  await auth.signInAsGuest();
  await nav.goToHomeTab();

  // Tap add entry FAB
  await nav.tapAddEntryFab();

  // Verify entry wizard opened by checking for wizard-specific element
  await $.waitUntilVisible($(Key('entry_wizard_tabs')));
  expect($(Key('entry_wizard_tabs')), findsOneWidget);
  expect($(Key('entry_wizard_tab_general')), findsOneWidget);
});
```

**Test**: `entry_management_test.dart` - "navigates through entry wizard steps" (line 89)

**Issue**: Uses text finders for navigation, doesn't verify step change

**Fix**:
```dart
patrolTest('navigates through entry wizard steps', ($) async {
  final auth = AuthTestHelper($);
  final nav = NavigationHelper($);

  await auth.launchApp();
  await auth.signInAsGuest();
  await nav.goToHomeTab();
  await nav.tapAddEntryFab();

  // Verify on General tab (default)
  await $.waitUntilVisible($(Key('entry_wizard_tab_general')));

  // Tap Weather tab
  await $(Key('entry_wizard_tab_weather')).tap();
  await $.pumpAndSettle();

  // Verify weather section visible
  await $.waitUntilVisible($(Key('weather_sunny')));
  expect($(Key('weather_sunny')), findsOneWidget);

  // Tap Activities tab
  await $(Key('entry_wizard_tab_activities')).tap();
  await $.pumpAndSettle();

  // Verify activities section visible
  await $.waitUntilVisible($(Key('entry_wizard_activities')));
  expect($(Key('entry_wizard_activities')), findsOneWidget);
});
```

**Test**: `photo_capture_test.dart` - Permission handling issues

**Issue**: Permission dialogs block test execution

**Fix** (add permission setup):
```dart
patrolTest('captures photo from camera', ($) async {
  final auth = AuthTestHelper($);

  await auth.launchApp();
  await auth.signInAsGuest();

  // Grant camera permission BEFORE opening camera
  await $.native.grantPermissionWhenInUse();

  // Navigate to entry wizard photos tab
  final nav = NavigationHelper($);
  await nav.goToHomeTab();
  await nav.tapAddEntryFab();

  await $(Key('entry_wizard_tab_photos')).tap();
  await $.pumpAndSettle();

  // Look for camera button
  final cameraButton = $(Key('photo_capture_camera'));  // ADD THIS KEY
  if (cameraButton.exists) {
    await cameraButton.tap();
    await $.pumpAndSettle();

    // Handle native camera (mock or skip in CI)
    await $.native.pressBack();  // Cancel camera
  }
});
```

**Test**: `camera_permission_test.dart` - Add permission reset

**Fix**:
```dart
void main() {
  patrolTest('requests camera permission', ($) async {
    final auth = AuthTestHelper($);
    await auth.launchApp();

    // Ensure permission is NOT granted initially
    // (Patrol doesn't have deny API, so test assumes clean state)

    await auth.signInAsGuest();

    // Navigate to photo capture
    // ... trigger camera

    // When permission dialog appears, grant it
    await $.native.grantPermissionWhenInUse();

    // Verify camera opens
  });
}
```

### Task 4.5: Add Missing Patrol Tests (Stretch Goal - 60 min)

**Create**: `integration_test/patrol/contractors_flow_test.dart`
```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:patrol/patrol.dart';
import '../helpers/auth_test_helper.dart';
import '../helpers/navigation_helper.dart';
import 'test_config.dart';

void main() {
  patrolTest(
    'adds contractor to project',
    ($) async {
      final auth = AuthTestHelper($);
      final nav = NavigationHelper($);

      await auth.launchApp();
      await auth.signInAsGuest();

      // Navigate to contractors (via dashboard or settings)
      await nav.goToDashboardTab();

      // Look for contractors section
      final contractorsCard = $(Key('dashboard_contractors_card'));  // ADD THIS KEY
      if (contractorsCard.exists) {
        await contractorsCard.tap();
        await $.pumpAndSettle();

        // Add new contractor
        await $(Key('add_contractor_fab')).tap();
        await $.pumpAndSettle();

        // Fill contractor form
        await $(Key('contractor_name_field')).enterText('Test Contractor LLC');
        await $.pumpAndSettle();

        await $(Key('contractor_type_dropdown')).tap();
        await $.pumpAndSettle();
        await $('Subcontractor').tap();
        await $.pumpAndSettle();

        // Save contractor
        await $(Key('contractor_save_button')).tap();
        await $.pumpAndSettle();

        // Verify contractor appears in list
        expect($('Test Contractor LLC'), findsWidgets);
      }
    },
    config: PatrolTestConfig.standard,
  );
}
```

**Create**: `integration_test/patrol/quantities_flow_test.dart`
```dart
void main() {
  patrolTest(
    'records quantity for bid item',
    ($) async {
      final auth = AuthTestHelper($);
      final nav = NavigationHelper($);

      await auth.launchApp();
      await auth.signInAsGuest();
      await nav.goToHomeTab();
      await nav.tapAddEntryFab();

      // Navigate to Quantities tab
      await $(Key('entry_wizard_tab_quantities')).tap();
      await $.pumpAndSettle();

      // Add quantity
      await $(Key('add_quantity_button')).tap();  // ADD THIS KEY
      await $.pumpAndSettle();

      // Select bid item
      await $(Key('quantity_bid_item_dropdown')).tap();  // ADD THIS KEY
      await $.pumpAndSettle();
      await $('1000').tap();  // Assumes bid item 1000 exists
      await $.pumpAndSettle();

      // Enter quantity
      await $(Key('quantity_amount_field')).enterText('25.5');  // ADD THIS KEY
      await $.pumpAndSettle();

      // Save quantity
      await $(Key('quantity_save_button')).tap();  // ADD THIS KEY
      await $.pumpAndSettle();

      // Verify quantity appears
      expect($('25.5'), findsWidgets);
    },
    config: PatrolTestConfig.standard,
  );
}
```

**Create**: `integration_test/patrol/complete_flow_test.dart`
```dart
void main() {
  patrolTest(
    'complete workflow: login → create entry → logout',
    ($) async {
      final auth = AuthTestHelper($);
      final nav = NavigationHelper($);

      // 1. Login
      await auth.launchApp();
      await auth.signInAsGuest();

      // 2. Create entry
      await nav.goToHomeTab();
      await nav.tapAddEntryFab();

      // Fill basic entry info
      await $(Key('entry_wizard_project_dropdown')).tap();
      await $.pumpAndSettle();
      // Select first project
      final projectOptions = $.tester.widgetList(find.byType(DropdownMenuItem));
      if (projectOptions.isNotEmpty) {
        await $.tester.tap(find.byType(DropdownMenuItem).first);
        await $.pumpAndSettle();
      }

      // Add activities
      await $(Key('entry_wizard_tab_activities')).tap();
      await $.pumpAndSettle();
      await $(Key('entry_wizard_activities')).enterText('Test work completed');
      await $.pumpAndSettle();

      // Save draft
      await $(Key('entry_wizard_save_draft')).tap();
      await $.pumpAndSettle();

      // Verify returned to home
      await $.waitUntilVisible($(Key('add_entry_fab')));

      // 3. Logout
      await auth.signOut();

      // Verify back on login screen
      await $.waitUntilVisible($(Key('login_email_field')));
      expect($(Key('login_email_field')), findsOneWidget);
    },
    config: PatrolTestConfig.slow,
  );
}
```

---

## Phase 5: Coverage Gaps - Missing Tests (Ongoing)

### Priority: MEDIUM
**Agent**: `qa-testing-agent` + `data-layer-agent`

### Task 5.1: CRITICAL Missing Tests (High Priority)

**Create**: `test/features/auth/presentation/providers/auth_provider_test.dart` (NEW)
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
// ... imports

void main() {
  group('AuthProvider', () {
    test('signIn succeeds with valid credentials', () async {
      // Test auth flow
    });

    test('signIn fails with invalid credentials', () async {
      // Test error handling
    });

    test('signOut clears user state', () async {
      // Test logout
    });

    test('isLoading state toggles correctly', () async {
      // Test loading state
    });
  });
}
```

**Create**: `test/features/auth/services/auth_service_test.dart` (NEW)
```dart
void main() {
  group('AuthService', () {
    test('signIn calls Supabase client', () async {
      // Test service layer
    });

    test('getCurrentUser returns user when authenticated', () async {
      // Test user retrieval
    });

    test('signOut calls Supabase signOut', () async {
      // Test logout
    });
  });
}
```

**Create**: `test/features/sync/presentation/providers/sync_provider_test.dart` (NEW - CRITICAL)
```dart
void main() {
  group('SyncProvider', () {
    test('syncAll triggers sync service', () async {
      // Test offline-first sync
    });

    test('isSyncing state updates correctly', () async {
      // Test loading state
    });

    test('lastSyncTime updates after successful sync', () async {
      // Test timestamp tracking
    });
  });
}
```

**Create**: `test/services/sync_service_test.dart` (NEW - CRITICAL)
```dart
void main() {
  group('SyncService', () {
    test('syncAll uploads pending local changes', () async {
      // Test upload
    });

    test('syncAll downloads new remote changes', () async {
      // Test download
    });

    test('handles sync conflicts (last-write-wins)', () async {
      // Test conflict resolution
    });

    test('retries failed syncs up to max attempts', () async {
      // Test retry logic
    });
  });
}
```

**Create**: `test/core/database/database_service_test.dart` (NEW - CRITICAL)
```dart
void main() {
  group('DatabaseService', () {
    test('onCreate creates all tables', () async {
      // Test schema creation
    });

    test('onUpgrade migrates from v8 to v9', () async {
      // Test migration
    });

    test('NOT NULL constraints enforced', () async {
      // Test constraint validation
    });

    test('foreign key ON DELETE CASCADE works', () async {
      // Test referential integrity
    });
  });
}
```

### Task 5.2: Missing Repository Tests (Medium Priority)

**Create**: `test/features/contractors/data/repositories/contractor_repository_test.dart` (NEW)
```dart
void main() {
  group('ContractorRepository', () {
    test('getAll returns sorted contractors', () async {});
    test('create adds contractor to database', () async {});
    test('update modifies existing contractor', () async {});
    test('delete removes contractor', () async {});
    test('getByProject filters by project ID', () async {});
  });
}
```

**Create**: `test/features/contractors/data/repositories/equipment_repository_test.dart` (NEW)

**Create**: `test/features/contractors/data/repositories/personnel_type_repository_test.dart` (NEW)

### Task 5.3: Missing Model Tests (Medium Priority)

**Create**: `test/features/contractors/data/models/entry_personnel_test.dart` (NEW)

**Create**: `test/features/contractors/data/models/entry_equipment_test.dart` (NEW)

**Create**: `test/features/quantities/data/models/entry_quantity_test.dart` (NEW)

### Task 5.4: Missing Patrol Flow Tests (Low Priority)

**Create**: `integration_test/patrol/pdf_export_test.dart` (NEW)
```dart
void main() {
  patrolTest('exports entry to PDF', ($) async {
    // Test PDF generation
  });
}
```

**Create**: `integration_test/patrol/offline_sync_test.dart` (NEW)
```dart
void main() {
  patrolTest('creates entry offline and syncs later', ($) async {
    // Test offline-first workflow
  });
}
```

**Create**: `integration_test/patrol/settings_flow_test.dart` (NEW)
```dart
void main() {
  patrolTest('changes theme mode', ($) async {
    // Test theme switching
  });

  patrolTest('configures sync settings', ($) async {
    // Test sync configuration
  });
}
```

### Task 5.5: Estimated Test File Counts

**Summary of Missing Tests**:

| Category | Missing Files | Estimated Lines | Priority |
|----------|---------------|-----------------|----------|
| Auth Provider/Service | 2 | ~400 | CRITICAL |
| Sync Provider/Service | 2 | ~600 | CRITICAL |
| Database Service | 1 | ~300 | CRITICAL |
| Contractor Repos | 3 | ~600 | HIGH |
| Missing Models | 3 | ~450 | MEDIUM |
| Patrol Flows | 3 | ~500 | LOW |
| **TOTAL** | **14** | **~2,850** | - |

---

## Execution Order

### Sprint 1 (Week 1): Foundation
1. **Phase 1: Quick Wins** (qa-testing-agent) - 1-2 hours
2. **Phase 2.1-2.2: Auth & Entry Keys** (flutter-specialist-agent) - 1.5 hours
3. **Phase 3.1-3.2: Mock Refactoring** (qa-testing-agent) - 1.5 hours

**Deliverable**: Cleaner test suite, key infrastructure in place

### Sprint 2 (Week 2): Patrol Stability
4. **Phase 2.3-2.5: Remaining Keys** (flutter-specialist-agent) - 1 hour
5. **Phase 3.3-3.4: Seed Data & Helpers** (qa-testing-agent) - 1 hour
6. **Phase 4.1-4.3: Patrol Test Fixes** (qa-testing-agent) - 2 hours

**Deliverable**: Patrol tests stable, higher pass rate

### Sprint 3 (Week 3): Patrol Coverage
7. **Phase 4.4: Fix Specific Tests** (qa-testing-agent) - 1.5 hours
8. **Phase 4.5: New Patrol Tests** (qa-testing-agent) - 1 hour

**Deliverable**: 80%+ Patrol tests passing, new flow coverage

### Sprint 4 (Ongoing): Test Coverage
9. **Phase 5.1: CRITICAL Tests** (data-layer-agent + qa-testing-agent) - 4 hours
10. **Phase 5.2-5.4: Remaining Tests** (qa-testing-agent) - 6 hours

**Deliverable**: Core feature test coverage complete

---

## Verification Checklist

### After Phase 1 (Cleanup)
- [ ] `flutter test` passes (~600 tests)
- [ ] No redundant test files exist
- [ ] Model tests use generic test utility

### After Phase 2 (Keys)
- [ ] All auth screens have Keys on form fields and buttons
- [ ] Entry wizard has Keys on tabs, fields, and actions
- [ ] Project/Dashboard screens have Keys on major elements
- [ ] Settings screen has Keys on navigation tiles

### After Phase 3 (Refactoring)
- [ ] Shared mocks in `test/helpers/mocks/`
- [ ] Sorting logic centralized in `test/helpers/test_sorting.dart`
- [ ] Seed data has timestamp variance
- [ ] Patrol helpers exist: `AuthTestHelper`, `NavigationHelper`

### After Phase 4 (Patrol Fixes)
- [ ] No `Future.delayed` in patrol tests (use `waitUntilVisible`)
- [ ] Text finders replaced with Key finders where possible
- [ ] Permission tests handle dialogs correctly
- [ ] `patrol test` passes 80%+ tests on device

### After Phase 5 (Coverage)
- [ ] Auth provider/service tests exist and pass
- [ ] Sync service tests exist and pass
- [ ] Database service tests exist and pass
- [ ] Contractor repository tests exist and pass
- [ ] `flutter test --coverage` shows >80% coverage on critical paths

---

## Agent Assignments

| Phase | Agent | Responsibility |
|-------|-------|----------------|
| 1 | `qa-testing-agent` | Delete redundant tests, create model test utility |
| 2 | `flutter-specialist-agent` | Add Keys to all UI elements |
| 3.1-3.2 | `qa-testing-agent` | Extract mocks, centralize sorting |
| 3.3 | `data-layer-agent` | Fix seed data timestamps |
| 3.4 | `qa-testing-agent` | Create Patrol test helpers |
| 4 | `qa-testing-agent` | Fix Patrol tests (timing, finders, state) |
| 5.1 | `data-layer-agent` + `qa-testing-agent` | CRITICAL missing tests (auth, sync, database) |
| 5.2-5.5 | `qa-testing-agent` | Remaining coverage gaps |

---

## Risk Assessment

### High Risk
- **Phase 2**: Adding Keys may require UI regression testing (golden tests help)
- **Phase 4**: Patrol tests may still fail on CI without device emulator

### Medium Risk
- **Phase 3.1**: Mock extraction may break existing tests if not careful
- **Phase 5.1**: Sync service mocking complex (Supabase interactions)

### Low Risk
- **Phase 1**: Simple deletions, easy to verify
- **Phase 3.4**: Helpers are additive, don't break existing tests

---

## Success Metrics

### Phase 1-3 Success
- Unit tests: 600+ passing (down from 613 due to deletions, up due to new model tests)
- Golden tests: 93 passing (unchanged)
- Test codebase: ~4,400 lines removed, ~1,200 lines added (net -3,200 lines)

### Phase 4 Success
- Patrol tests: 55+ passing (80%+ pass rate, up from 3/69)
- Test reliability: No flaky tests due to timing issues
- Test maintainability: Key-based finders reduce brittleness

### Phase 5 Success
- Auth coverage: 100% (provider + service)
- Sync coverage: 100% (provider + service)
- Database coverage: 80%+ (schema, migrations, constraints)
- Overall coverage: >80% on critical paths

---

## Notes

- All file paths are absolute from project root: `C:\Users\rseba\Projects\Field Guide App\`
- This plan assumes Supabase credentials are configured via environment variables (from defects.md fix)
- Patrol tests require physical device or emulator (cannot run in headless CI without setup)
- Golden tests should run in CI to catch UI regressions from Key additions
- Sync service tests may require Supabase local dev setup or extensive mocking

---

## References

- Current test state: `.claude/implementation/implementation_plan.md`
- Defects log: `.claude/memory/defects.md`
- Coding standards: `.claude/rules/coding-standards.md`
- Test helpers: `test/helpers/test_helpers.dart`
- Patrol setup: `integration_test/patrol/setup_patrol.md`
