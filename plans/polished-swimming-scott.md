# E2E Testing Remediation Plan

## Executive Summary

After 2 days of testing work, our E2E tests have fundamental issues preventing real user journey validation. This plan focuses on fixing **one complete journey first** (Entry Creation) to establish correct patterns, then propagating fixes across the test suite.

**Root Cause**: Tests were written TDD-style but UI widgets weren't fully instrumented with TestingKeys. Tests fall back to brittle text selectors or silently skip steps.

---

## Research Findings

### Does Patrol Need OCR?
**NO.** Patrol does NOT need OCR. It accesses the Flutter widget tree directly via Keys. OCR would only be needed for testing native platform UI (permissions dialogs, system settings) which Patrol handles via native automation APIs.

### What's Wrong with Current Tests

| Issue | Frequency | Impact |
|-------|-----------|--------|
| Missing TestingKeys in widgets | 40-50% | Tests can't find elements |
| Text selectors instead of Keys | 15-20% | Brittle, breaks with text changes |
| No seed data initialization | 10-15% | Dropdowns empty, edit tests fail |
| No data verification helpers | 100% | Tests tap buttons but don't verify results |
| Sync `.exists` checks | Multiple files | Race conditions, silent failures |

### Patrol Best Practices (from research)

1. **Always use Keys** - `$(TestingKeys.myButton)` not `$('Button Text')`
2. **Use `pumpAndTrySettle()`** for apps with animations/loading spinners
3. **Reset state between tests** - tests run in same process
4. **Mock backends, pre-seed data** - don't rely on external state
5. **Scroll explicitly** - use `scrollTo()` or specify scroll view
6. **Configure timeouts** - per-test and per-action timeouts available

---

## Phase 1: Fix Entry Creation Journey (Focus Test)

### Goal
Get ONE complete journey working end-to-end with proper data verification.

### Journey: Create Daily Entry
```
1. Launch app → Calendar screen visible
2. Tap FAB → Entry wizard opens
3. Select location from dropdown
4. Fill weather (condition, temps)
5. Enter activities text
6. Save entry
7. VERIFY: Entry appears in calendar list with correct data
8. Re-open entry → VERIFY: All data persisted
```

### Step 1.1: Add Missing TestingKeys to Widgets

**Files to modify:**
- `lib/features/entries/presentation/screens/entry_wizard_screen.dart`
- `lib/features/entries/presentation/widgets/` (various)
- `lib/shared/testing_keys.dart`

**Keys to add/verify:**
```dart
// Entry wizard - verify these exist on actual widgets
entryWizardLocationDropdown  // DropdownButtonFormField
entryWizardWeatherDropdown   // DropdownButtonFormField
entryWizardTempLow           // TextFormField
entryWizardTempHigh          // TextFormField
entryWizardActivities        // TextFormField
entryWizardSubmit            // ElevatedButton (or Save)
entryWizardClose             // IconButton (X)

// Calendar/Home screen - for verification
entryCard(String entryId)    // Dynamic key for entry cards
entryCardDate(String date)   // Alternative: find by date
```

### Step 1.2: Fix Test Helper Issues

**File:** `integration_test/patrol/helpers/patrol_test_helpers.dart`

**Fixes needed:**
1. Change sync `.exists` to async pattern:
```dart
// BAD (current)
if ($(key).exists) { ... }

// GOOD (fix)
if (await $(key).waitUntilVisible(timeout: Duration(seconds: 2)).exists) { ... }
// OR use try-catch pattern
```

2. Add data verification helpers:
```dart
/// Verify entry appears in calendar list
Future<void> verifyEntryInCalendar({
  required String activityText,
  DateTime? date,
}) async {
  // Navigate to calendar if not there
  await navigateToCalendar();

  // Look for entry card with activity text
  final entryFinder = $(activityText);
  await $.waitUntilVisible(entryFinder, timeout: Duration(seconds: 5));

  ctx.logAssert(
    'entry_in_calendar',
    'Entry with "$activityText" should appear in calendar',
    passed: entryFinder.exists,
  );
}

/// Verify field contains expected value
Future<void> verifyFieldValue(Key fieldKey, String expected) async {
  final field = $(fieldKey);
  // Read current value from TextField widget
  final widget = $.tester.widget<TextField>(field);
  final actual = widget.controller?.text ?? '';

  ctx.logAssert(
    'field_value_${fieldKey.toString()}',
    'Field should contain "$expected"',
    passed: actual.contains(expected),
  );
}
```

3. Add scroll-to-field helper:
```dart
Future<void> scrollToAndFill(Key fieldKey, String value) async {
  await $(fieldKey).scrollTo();
  await $(fieldKey).enterText(value);
  await $.pumpAndSettle();
}
```

### Step 1.3: Create Seed Data Fixture

**New file:** `integration_test/patrol/fixtures/test_data.dart`

```dart
/// Seed data for E2E tests
class TestDataFixture {
  static const testProjectId = 'e2e-test-project';
  static const testLocationId = 'e2e-test-location';
  static const testLocationName = 'Main Site';

  /// Initialize test database with required seed data
  static Future<void> seedDatabase() async {
    final db = DatabaseService.instance;

    // Create test project if not exists
    final existingProject = await db.getProject(testProjectId);
    if (existingProject == null) {
      await db.insertProject(Project(
        id: testProjectId,
        name: 'E2E Test Project',
        projectNumber: 'E2E-001',
      ));

      // Create test location
      await db.insertLocation(Location(
        id: testLocationId,
        projectId: testProjectId,
        name: testLocationName,
      ));
    }
  }

  /// Clean up test data after test run
  static Future<void> cleanup() async {
    // Delete entries created during test
    // Keep project/location for next run
  }
}
```

### Step 1.4: Rewrite Entry Lifecycle Test

**File:** `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`

```dart
patrolTest(
  'Journey: Complete entry creation with verification',
  config: PatrolTestConfig.slow,
  ($) async {
    final h = PatrolTestConfig.createHelpers($, 'entry_journey');

    // Setup: Seed data
    await TestDataFixture.seedDatabase();

    // Step 1: Launch app
    await h.launchAppAndWait();
    h.ctx.logStep('App launched');

    // Step 2: Verify calendar screen
    await h.assertVisible(TestingKeys.addEntryFab, 'Calendar FAB visible');

    // Step 3: Open entry wizard
    await $(TestingKeys.addEntryFab).tap();
    await $.pumpAndSettle();
    await h.assertVisible(TestingKeys.entryWizardClose, 'Wizard opened');

    // Step 4: Select location (REQUIRED)
    h.ctx.logStep('Selecting location');
    await $(TestingKeys.entryWizardLocationDropdown).tap();
    await $.pumpAndSettle();
    await $(TestDataFixture.testLocationName).tap();
    await $.pumpAndSettle();

    // Step 5: Fill weather
    h.ctx.logStep('Filling weather data');
    await $(TestingKeys.entryWizardWeatherDropdown).tap();
    await $.pumpAndSettle();
    await $('Cloudy').tap();  // TODO: Add key for dropdown options
    await $.pumpAndSettle();

    await $(TestingKeys.entryWizardTempLow).scrollTo();
    await $(TestingKeys.entryWizardTempLow).enterText('55');
    await $(TestingKeys.entryWizardTempHigh).enterText('72');

    // Step 6: Fill activities (unique text for verification)
    final activityText = 'E2E Test Activity ${DateTime.now().millisecondsSinceEpoch}';
    h.ctx.logStep('Entering activities: $activityText');
    await $(TestingKeys.entryWizardActivities).scrollTo();
    await $(TestingKeys.entryWizardActivities).enterText(activityText);

    // Step 7: Submit entry
    h.ctx.logStep('Submitting entry');
    await $(TestingKeys.entryWizardSubmit).scrollTo();
    await $(TestingKeys.entryWizardSubmit).tap();
    await $.pumpAndSettle(timeout: Duration(seconds: 10));

    // Step 8: VERIFY - Back on calendar
    await h.assertVisible(TestingKeys.addEntryFab, 'Returned to calendar');

    // Step 9: VERIFY - Entry appears in list
    h.ctx.logStep('Verifying entry in calendar');
    await h.verifyEntryInCalendar(activityText: activityText);

    // Step 10: Re-open entry and verify data persisted
    h.ctx.logStep('Re-opening entry to verify persistence');
    await $(activityText).tap();
    await $.pumpAndSettle();

    // Verify fields contain expected values
    await h.verifyFieldValue(TestingKeys.entryWizardActivities, activityText);

    h.ctx.logComplete();
  },
);
```

---

## Phase 2: Propagate Fixes to Other Tests

After Phase 1 succeeds, apply same patterns to:

### 2.1 Project Management Tests
- Add missing keys: `projectNameField`, `projectNumberField`, `projectClientField`
- Add tab keys: `projectDetailsTab`, `projectLocationsTab`, etc.
- Add `verifyProjectInList()` helper

### 2.2 Settings/Theme Tests
- Replace `$('Dark')` with `TestingKeys.themeDarkOption`
- Add keys for all theme dropdown options
- Add `verifyThemeApplied()` helper

### 2.3 Photo Flow Tests
- Fix scroll delta issues (was `Offset`, now `double`)
- Add camera/gallery mock or skip on CI
- Add `verifyPhotoInGallery()` helper

### 2.4 Sync Tests
- Add `syncStatusIndicator` key to UI
- Add Supabase mock for offline testing
- Add `verifySyncStatus()` helper

---

## Phase 3: Test Infrastructure Improvements

### 3.1 Test Data Management
- Implement `TestDataFixture` for all tests
- Add cleanup in `tearDown` or `tearDownAll`
- Consider SQLite in-memory for faster tests

### 3.2 Configuration Updates
- Add `pumpAndTrySettle()` as default (handles loading spinners)
- Increase default timeout for CI environments
- Add screenshot capture on failure

### 3.3 CI Integration
- Pre-grant permissions in CI config
- Run tests with `--dart-define` for env config
- Add test sharding for parallel execution

---

## Files to Modify

### High Priority (Phase 1)
| File | Changes |
|------|---------|
| `lib/features/entries/presentation/screens/entry_wizard_screen.dart` | Verify/add TestingKeys to all form fields |
| `lib/shared/testing_keys.dart` | Add any missing keys, add dynamic `entryCard(id)` |
| `integration_test/patrol/helpers/patrol_test_helpers.dart` | Fix sync `.exists`, add verification helpers |
| `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart` | Rewrite with proper journey pattern |
| `integration_test/patrol/fixtures/test_data.dart` | NEW - seed data fixture |

### Medium Priority (Phase 2)
| File | Changes |
|------|---------|
| `lib/features/projects/presentation/screens/project_setup_screen.dart` | Add field keys |
| `lib/features/settings/presentation/screens/settings_screen.dart` | Add theme option keys |
| `integration_test/patrol/e2e_tests/project_management_test.dart` | Apply journey pattern |
| `integration_test/patrol/e2e_tests/settings_theme_test.dart` | Replace text selectors |

---

## Verification Checklist

After implementation, verify:

1. [ ] Entry creation journey passes on real device
2. [ ] Entry data persists after wizard close
3. [ ] Entry appears in calendar with correct text
4. [ ] Re-opening entry shows saved data
5. [ ] No "Found 0 widgets" errors
6. [ ] No silent test skips (all steps execute)
7. [ ] Test cleans up created data
8. [ ] Test runs reliably 3x in a row

### Run Command
```bash
patrol test integration_test/patrol/e2e_tests/entry_lifecycle_test.dart --device RFCNC0Y975L --verbose
```

---

## Timeline Estimate

| Phase | Scope | Effort |
|-------|-------|--------|
| Phase 1 | Entry journey | 2-3 hours |
| Phase 2 | Other tests | 3-4 hours |
| Phase 3 | Infrastructure | 2-3 hours |

**Recommendation**: Complete Phase 1 first, verify it works, then proceed. Don't try to fix everything at once.

---

## Key Decisions (Confirmed)

1. **Seed data strategy**: Fixture class - Dart code creates seed data at test start
2. **Test isolation**: Unique IDs per run - timestamp-based IDs, no cleanup needed
3. **Photo tests**: Skip camera tests on CI - only run on real devices with manual interaction

---

## Implementation Notes

### Unique ID Pattern
```dart
// Each test run generates unique IDs
final testRunId = DateTime.now().millisecondsSinceEpoch;
final entryId = 'e2e-entry-$testRunId';
final activityText = 'E2E Activity $testRunId';
```

### Camera Test Annotation
```dart
@Tags(['requires-camera'])  // Skip on CI
patrolTest('E2E: Capture photo from camera', ...);
```

### CI Configuration
```yaml
# patrol.yaml or CI config
patrol test --exclude-tags=requires-camera
```
