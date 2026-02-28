---
paths:
  - "integration_test/**/*.dart"
  - "test/**/*.dart"
  - "lib/shared/testing_keys/testing_keys.dart"
  - "lib/shared/testing_keys/quantities_keys.dart"
  - "lib/test_harness/**/*.dart"
  - "lib/test_harness.dart"
  - "lib/driver_main.dart"
---

# Testing Guide

Complete guide to testing in the Construction Inspector app: unit tests, Patrol E2E, widget harness, and PDF stage trace testing.

---

## Unit Tests

### Run Commands

```powershell
# All unit tests
pwsh -Command "flutter test"

# Specific test file
pwsh -Command "flutter test test/features/pdf/extraction/some_test.dart"

# Specific test by name
pwsh -Command "flutter test test/features/pdf/extraction/ --name 'stage trace'"
```

**CRITICAL**: Always use `pwsh -Command "..."` wrapper. Never run `flutter` or `dart` directly in Git Bash -- it silently fails.

---

## Patrol E2E Testing

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

### Test Bundle Registration

To include a test in the bundle, add import and group() call to `test_config.dart`:

```dart
// Add import
import 'patrol/e2e_tests/my_new_test.dart' as patrol__e2e_tests__my_new_test;

// Add group in main()
group('patrol.e2e_tests.my_new_test', patrol__e2e_tests__my_new_test.main);
```

**Note**: Files in `isolated/` are intentionally excluded for standalone execution.

### Test Patterns

#### Navigation Testing

```dart
import 'package:construction_inspector/shared/shared.dart';

// Navigate using bottom navigation
await $(TestingKeys.projectsNavButton).tap();
await $(TestingKeys.calendarNavButton).tap();
await $(TestingKeys.dashboardNavButton).tap();
await $(TestingKeys.settingsNavButton).tap();
```

#### Dialog Testing

```dart
// Handle confirmation dialog
await $(TestingKeys.confirmDialogButton).tap();  // Confirm
await $(TestingKeys.cancelDialogButton).tap();   // Cancel (generic)
await $(TestingKeys.confirmationDialogCancel).tap();  // Cancel (delete dialog)
await $(TestingKeys.unsavedChangesCancel).tap();  // Cancel (unsaved changes)
```

#### Waiting for UI Updates

```dart
// Wait for visibility (preferred over delays)
await $(TestingKeys.projectCard('project-123')).waitUntilVisible();

// Wait for element to disappear
await $(TestingKeys.confirmationDialog).waitUntilGone();
```

### Common Pitfalls

#### Hardcoded Keys

```dart
// BAD
await $(Key('my_button')).tap();

// GOOD
await $(TestingKeys.myButton).tap();
```

#### Hardcoded Delays

```dart
// BAD
await Future.delayed(Duration(seconds: 2));

// GOOD
await $(TestingKeys.loadingIndicator).waitUntilGone();
```

#### Missing Mounted Checks

```dart
// BAD
await someAsyncOperation();
context.read<Provider>().doThing();

// GOOD
await someAsyncOperation();
if (!mounted) return;
context.read<Provider>().doThing();
```

---

## Widget Test Harness (Isolated Screen Testing)

Purpose: render one screen at a time with real providers backed by in-memory SQLite for faster, lower-load UI testing than full-app launch.

### Launch Sequence

1. Write `harness_config.json` at project root:
   ```json
   {"screen":"ProctorEntryScreen","data":{"responseId":"test-response-001"}}
   ```
2. `pwsh -Command "flutter run -d windows -t lib/test_harness.dart"`
3. Interact with the rendered screen manually or via Patrol tests

### Config Fields

- `screen` (required): registry key from `lib/test_harness/screen_registry.dart`
- `data` (optional): per-screen constructor/seed inputs

### Adding a New Screen to Harness

1. Add a registry entry in `lib/test_harness/screen_registry.dart`
2. Add `ValueKey` coverage for interactive elements in the screen widget
3. Add/update keys in `lib/shared/testing_keys/testing_keys.dart`
4. If the screen needs extra context, extend harness seeding via `harness_config.json` `data`

### Flow Mode (Multi-Screen Journey Testing)

Wires up real GoRouter routes so screens navigate naturally without relaunching the app per screen.

#### Flow `harness_config.json` Format
```json
{
  "flow": "0582b-forms",
  "startAt": "/forms",
  "data": {
    "responseId": "harness-response-001"
  }
}
```
- `flow`: key into `lib/test_harness/flow_registry.dart` (triggers flow mode instead of single-screen mode).
- `startAt`: optional initial route path (defaults to flow's `defaultInitialLocation`).
- `data`: shared seed data, same as single-screen mode.

#### Available Flows
| Flow Key | Start | Screens |
|----------|-------|---------|
| `0582b-forms` | `/forms` | FormsListScreen, FormViewerScreen, QuickTestEntryScreen, ProctorEntryScreen, WeightsEntryScreen, ToolboxHomeScreen |

#### Add a New Flow
1. Add a `FlowDefinition` entry in `lib/test_harness/flow_registry.dart`.
2. Copy needed `GoRoute` entries from `app_router.dart` (without auth redirects/shell routes).
3. Include fallback routes used by `safeGoBack` in the flow's screens.
4. List seed screen names in `seedScreens`.

---

## Widget Keys -- TestingKeys Class

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

// 3. Use in Patrol test
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

---

## Process Management

- **NEVER** `Stop-Process -Name 'dart'` -- can kill background Dart processes
- **SAFE kill**: `Stop-Process -Name 'construction_inspector' -Force -ErrorAction SilentlyContinue`

---

## Testing Strategy (3-Tier)

1. **Unit tests** -- `test/` for models, repositories, providers, and services
2. **Widget harness tests** -- `lib/test_harness.dart` + `harness_config.json` for isolated screen interaction
3. **Patrol E2E** -- `integration_test/patrol/` for full integration tests with native platform interaction

UI test findings: `.claude/test-results/YYYY-MM-DD-ui-test-findings.md`

---

## PDF Extraction Stage Trace Testing

### Run Commands

```powershell
# Stage trace tests
pwsh -Command "flutter test test/features/pdf/extraction/ --name 'stage trace'"

# All PDF tests
pwsh -Command "flutter test test/features/pdf/"

# With diagnostics
pwsh -Command "flutter test test/features/pdf/ --dart-define=PDF_PARSER_DIAGNOSTICS=true"

# Specific test file
pwsh -Command "flutter test test/features/pdf/services/<test_file>.dart"
```

### Current Baseline

- **68 OK / 3 LOW / 0 BUG**
- Quality: **0.993**
- Ground truth coverage: **131/131 GT matched**

Validates the PDF extraction pipeline end-to-end against ground truth fixtures.

### Springfield Fixture Workflow

**CRITICAL: Always regenerate fixtures before scorecard/stage trace work.**
Stale fixtures from older pipeline versions produce misleading results. Do NOT analyze failures against stale fixtures.

Regeneration command (substitute the actual path to your Springfield PDF):

```powershell
pwsh -Command "flutter test integration_test/generate_golden_fixtures_test.dart -d windows --dart-define='SPRINGFIELD_PDF=<your-local-path-to-springfield-pdf>'"
```

Regeneration takes 2-3 minutes. Run this whenever any pipeline stage code has changed.

### Scorecard Display Format

When presenting scorecard results, ALWAYS use this table format:

| # | Stage | Metric | Expected | Actual | % | Status |
|---|-------|--------|----------|--------|---|--------|

Bold rows where Status is LOW or BUG.

### GT Item Trace Format

Each ground-truth item gets exactly 4 rows:

| Item# | Layer | Description | Unit | Qty | Price | Amount |
|-------|-------|-------------|------|-----|-------|--------|

Layers: Ground Truth, Cell Grid 4D, Parsed 4E, Processed 5

### Bogus Items Format

| Item# | Description | Unit | Qty | Price | Amount | Fields |
|-------|-------------|------|-----|-------|--------|--------|

Never dump raw test output. Always format into tables.

### Test Monitoring Rules

- Report total pass/fail counts from output
- Quote specific failure messages (assertion text, expected vs actual values)
- Group failures by feature/file
- Never say "tests passed" without reading the runner output
- If no output for 60s -- kill the process and report as timeout

---

## Resources

- TestingKeys: `lib/shared/testing_keys/testing_keys.dart`
- UI Keys Reference: `integration_test/patrol/REQUIRED_UI_KEYS.md`
- Golden Tests: `test/golden/README.md`
- Defects to Avoid: `.claude/defects/_defects-{feature}.md` (per-feature defect files)
- Screen Registry: `lib/test_harness/screen_registry.dart`
