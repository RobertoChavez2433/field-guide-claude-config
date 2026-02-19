---
paths:
  - "integration_test/**/*.dart"
  - "test/**/*.dart"
  - "lib/shared/testing_keys/testing_keys.dart"
---

# E2E Testing Guide

Complete guide to E2E testing with Patrol in the Construction Inspector app.

## Quick Reference

### Run Tests
```bash
# All tests
patrol test

# Specific test file
patrol test integration_test/patrol/e2e_tests/navigation_flow_test.dart

# Verbose output
patrol test --verbose
```

### Test Structure
```
integration_test/patrol/
├── e2e_tests/              # Full E2E flows registered in test_config.dart
├── isolated/               # Standalone tests NOT in test_config.dart
├── helpers/                # Shared test utilities
├── test_config.dart        # Test registration for Patrol
└── REQUIRED_UI_KEYS.md     # Widget key reference
```

## Widget Keys - TestingKeys Class

**All widget keys are centralized in `lib/shared/testing_keys/testing_keys.dart`.**

### Key Rules

1. **Never** use hardcoded `Key('...')` strings in widgets or tests
2. **Always** reference keys from the `TestingKeys` class
3. **Import** via: `import 'package:construction_inspector/shared/shared.dart';`
4. **Add new keys** to TestingKeys when creating testable widgets

### Adding New Keys

```dart
// 1. Add to lib/shared/testing_keys/testing_keys.dart
class TestingKeys {
  static const myNewButton = Key('my_new_button');
}

// 2. Use in widget
ElevatedButton(
  key: TestingKeys.myNewButton,
  onPressed: _handlePress,
  child: Text('Press Me'),
)

// 3. Use in test
import 'package:construction_inspector/shared/shared.dart';

await $(TestingKeys.myNewButton).tap();
```

### Key Categories

See `integration_test/patrol/REQUIRED_UI_KEYS.md` for complete list:
- Bottom Navigation
- Floating Action Buttons
- Confirmation Dialogs (3 cancel button variants)
- Dashboard Cards
- Settings Screen
- Entry Wizard
- Project Setup
- Authentication
- Photo Capture
- Dynamic Key Helpers (for list items)

## Test Bundle Registration

To include a test in the bundle, add import and group() call to `test_config.dart`:

```dart
// Add import
import 'patrol/e2e_tests/my_new_test.dart' as patrol__e2e_tests__my_new_test;

// Add group in main()
group('patrol.e2e_tests.my_new_test', patrol__e2e_tests__my_new_test.main);
```

**Note**: Files in `isolated/` are intentionally excluded for standalone execution.

## Test Patterns

### Navigation Testing

```dart
import 'package:construction_inspector/shared/shared.dart';

// Navigate using bottom navigation
await $(TestingKeys.projectsNavButton).tap();
await $(TestingKeys.calendarNavButton).tap();
await $(TestingKeys.dashboardNavButton).tap();
await $(TestingKeys.settingsNavButton).tap();
```

### Dialog Testing

```dart
// Handle confirmation dialog
await $(TestingKeys.confirmDialogButton).tap();  // Confirm
await $(TestingKeys.cancelDialogButton).tap();   // Cancel (generic)
await $(TestingKeys.confirmationDialogCancel).tap();  // Cancel (delete dialog)
await $(TestingKeys.unsavedChangesCancel).tap();  // Cancel (unsaved changes)
```

### Waiting for UI Updates

```dart
// Wait for visibility (preferred over delays)
await $(TestingKeys.projectCard('project-123')).waitUntilVisible();

// Wait for element to disappear
await $(TestingKeys.confirmationDialog).waitUntilGone();
```

## Common Pitfalls

### Hardcoded Keys
```dart
// BAD
await $(Key('my_button')).tap();

// GOOD
await $(TestingKeys.myButton).tap();
```

### Hardcoded Delays
```dart
// BAD
await Future.delayed(Duration(seconds: 2));

// GOOD
await $(TestingKeys.loadingIndicator).waitUntilGone();
```

### Missing Mounted Checks
```dart
// BAD
await someAsyncOperation();
context.read<Provider>().doThing();

// GOOD
await someAsyncOperation();
if (!mounted) return;
context.read<Provider>().doThing();
```

## Resources

- TestingKeys: `lib/shared/testing_keys/testing_keys.dart`
- UI Keys Reference: `integration_test/patrol/REQUIRED_UI_KEYS.md`
- Golden Tests: `test/golden/README.md`
- Defects to Avoid: `.claude/defects/_defects-{feature}.md` (per-feature defect files)
