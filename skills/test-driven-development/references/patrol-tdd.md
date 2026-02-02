# Patrol TDD

Test-Driven Development workflow for Patrol E2E tests.

## TDD for E2E Tests

E2E tests are typically written BEFORE implementing complete user flows.

### The Pattern

1. **Define the flow** - What should the user be able to do?
2. **Write the test** - Using TestingKeys that don't exist yet
3. **Make it compile** - Add TestingKeys, stub screens
4. **Run to see RED** - Test fails because screens aren't implemented
5. **Implement screens** - GREEN phase
6. **Run to verify** - Test passes

## Example: New Entry Flow

### Step 1: Define the Flow

User story: "As an inspector, I want to create a new daily entry for today's work."

Flow:
1. Tap FAB on dashboard
2. Select project
3. Select location
4. Save entry
5. See entry in list

### Step 2: Write the Test (RED)

```dart
// integration_test/patrol/e2e_tests/create_entry_test.dart
import 'package:construction_inspector/shared/shared.dart';
import 'package:patrol/patrol.dart';

void main() {
  patrolTest('inspector can create new daily entry', ($) async {
    await $.pumpWidgetAndSettle(const MyApp());

    // Navigate to create entry
    await $(TestingKeys.newEntryFab).tap();

    // Select project
    await $(TestingKeys.projectDropdown).tap();
    await $(TestingKeys.projectOption('project-1')).tap();

    // Select location
    await $(TestingKeys.locationDropdown).tap();
    await $(TestingKeys.locationOption('location-1')).tap();

    // Save
    await $(TestingKeys.saveEntryButton).tap();

    // Verify entry created
    await $(TestingKeys.entryCard).waitUntilVisible();
    expect($('Today'), findsOneWidget);
  });
}
```

### Step 3: Add TestingKeys

```dart
// lib/shared/testing_keys.dart
class TestingKeys {
  // Entry creation flow
  static const newEntryFab = Key('new_entry_fab');
  static const projectDropdown = Key('project_dropdown');
  static Key projectOption(String id) => Key('project_option_$id');
  static const locationDropdown = Key('location_dropdown');
  static Key locationOption(String id) => Key('location_option_$id');
  static const saveEntryButton = Key('save_entry_button');
  static const entryCard = Key('entry_card');
}
```

### Step 4: Run to See Failure

```bash
patrol test -t integration_test/patrol/e2e_tests/create_entry_test.dart
```

Expected failure: Keys not found, screens not implemented.

### Step 5: Implement Screens (GREEN)

Build each screen, wiring TestingKeys:

```dart
// Dashboard FAB
FloatingActionButton(
  key: TestingKeys.newEntryFab,
  onPressed: () => context.push('/entries/new'),
  child: Icon(Icons.add),
)

// Project dropdown
DropdownButton<String>(
  key: TestingKeys.projectDropdown,
  items: projects.map((p) => DropdownMenuItem(
    key: TestingKeys.projectOption(p.id),
    value: p.id,
    child: Text(p.name),
  )).toList(),
  // ...
)
```

### Step 6: Verify Test Passes

```bash
patrol test -t integration_test/patrol/e2e_tests/create_entry_test.dart
# ✓ inspector can create new daily entry
```

## Common Patrol TDD Patterns

### Waiting Patterns

```dart
// Wait for navigation
await $(TestingKeys.targetScreen).waitUntilVisible();

// Wait for loading to complete
await $(TestingKeys.loadingIndicator).waitUntilGone();

// Wait for list to populate
await $(TestingKeys.listItem).waitUntilVisible();
```

### Scrolling Before Interaction

```dart
// For items that might be below the fold
await $(TestingKeys.itemAtBottom).scrollTo();
await $(TestingKeys.itemAtBottom).tap();
```

### Dynamic Keys

```dart
// In TestingKeys
static Key projectCard(String id) => Key('project_card_$id');
static Key entryRow(String id) => Key('entry_row_$id');

// In test
await $(TestingKeys.projectCard('project-123')).tap();
```

### Dialog Handling

```dart
// Confirm dialog
await $(TestingKeys.deleteButton).tap();
await $(TestingKeys.confirmDialogButton).waitUntilVisible();
await $(TestingKeys.confirmDialogButton).tap();
await $(TestingKeys.confirmDialogButton).waitUntilGone();
```

## Test File Structure

```dart
// integration_test/patrol/e2e_tests/feature_test.dart
import 'package:construction_inspector/main.dart';
import 'package:construction_inspector/shared/shared.dart';
import 'package:patrol/patrol.dart';

void main() {
  group('Feature Name', () {
    patrolTest('happy path scenario', ($) async {
      await $.pumpWidgetAndSettle(const MyApp());
      // Test steps
    });

    patrolTest('edge case scenario', ($) async {
      await $.pumpWidgetAndSettle(const MyApp());
      // Test steps
    });
  });
}
```

## TDD Flow Checklist

Before implementing a new screen/flow:

- [ ] **Define user story**: What is the user trying to do?
- [ ] **Write test first**: Complete test with all interactions
- [ ] **Add TestingKeys**: All keys the test needs
- [ ] **Run and see RED**: Test fails appropriately
- [ ] **Implement screens**: Wire keys, build UI
- [ ] **Run and see GREEN**: Test passes
- [ ] **Add to test bundle**: Register in `test_bundle.dart`

## Test Bundle Registration

After test is green, add to bundle:

```dart
// integration_test/test_bundle.dart
import 'patrol/e2e_tests/create_entry_test.dart' as create_entry_test;

void main() {
  group('patrol.e2e_tests.create_entry', create_entry_test.main);
}
```

## Debugging Failing Tests

When a test fails:

1. **Check the error message** - Which key wasn't found?
2. **Verify key is wired** - Is `key: TestingKeys.xxx` in widget?
3. **Check visibility** - Does widget need `scrollTo()` first?
4. **Add diagnostics**:

```dart
debugPrint('Looking for: ${TestingKeys.myWidget}');
debugPrint('Screen widgets: ${$.tester.allWidgets.length}');
```

## Known Defects Integration

Before writing E2E tests, check `.claude/autoload/_defects.md` for:

- `[E2E] TestingKeys Defined But Not Wired`
- `[E2E] Test Helper Missing scrollTo()`
- `[E2E] dismissKeyboard() Closes Dialogs`
- `[E2E] Git Bash Silent Output`
