---
paths:
  - "integration_test/**/*.dart"
  - "test/**/*.dart"
  - "lib/shared/testing_keys/testing_keys.dart"
  - "lib/shared/testing_keys/quantities_keys.dart"
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

---

## MCP Testing Tools

### Dart MCP (`mcp__dart-mcp__*`)
Use for: launching app, running tests, getting logs, hot reload, analyzing files.

Key tools:
- `launch_app` — launch in debug mode, captures VM service URI
- `run_tests` — run flutter tests without launching app UI
- `get_app_logs` — retrieve console output
- `hot_reload` / `hot_restart` — reload after code changes
- `analyze_files` — static analysis on specific files
- `dart_format` — format Dart files

### Marionette MCP (`mcp__marionette__*`)
Use for: visual spot-checks, screenshots, UI interaction verification.

**Connection workflow:**
1. `dart-mcp launch_app` — captures VM service URI
2. `marionette connect` with the URI
3. `get_interactive_elements` — discover available UI elements
4. Interact via `tap`, `enter_text`, `scroll_to`
5. `take_screenshots` to verify state
6. `get_logs` to debug issues

**Element targeting**: Elements matched by `ValueKey<String>` or text content.
Keys are more reliable — add `key: ValueKey('my_key')` if element not found.

### MCP Stability Rules — CRITICAL
- **NEVER** `Stop-Process -Name 'dart'` — kills both `dart-mcp` and `marionette_mcp` servers, requires full Claude Code restart
- **SAFE kill**: `Stop-Process -Name 'construction_inspector' -Force -ErrorAction SilentlyContinue`
- **If tools show "No such tool available"** — MCP servers were killed — restart Claude Code session
- **Marionette WebSocket drops during**: heavy rendering (PDF pipeline at 300 DPI), GC pauses, rapid sequential ops — Flutter platform limitation, no reconnect in current version
- **Marionette recovery**: relaunch app via `dart-mcp launch_app`, then `marionette connect` with new VM URI

### Marionette Usage Guidelines
- Use for **ad-hoc visual checks and screenshots only** — not full 340-step journeys
- Add delays between rapid operations (tap, then wait, then screenshot)
- **Never** trigger heavy rendering (PDF import) while Marionette is connected
- For stable, repeatable E2E regression — use `integration_test/` Dart files (no WebSocket dependency)

### Testing Strategy (Hybrid Approach — Session 402 Decision)
1. **Stable regression** — `integration_test/` Dart files (headless, no WebSocket fragility)
2. **Visual spot-checks** — Marionette for screenshots at key screens
3. **Unit coverage** — `test/` for models, repos, providers, services

### UI Test Journey Plan
Living document: `.claude/plans/completed/2026-02-19-marionette-ui-test-journeys.md`
8 journeys, 23 screens, 30+ dialogs, ~340 interaction steps.
Test findings: `.claude/test-results/`

---

## PDF Extraction Stage Trace Testing

### Springfield Fixture Workflow

**CRITICAL: Always regenerate fixtures before scorecard/stage trace work.**
Stale fixtures from older pipeline versions produce misleading results. Do NOT analyze failures against stale fixtures.

Regeneration command (substitute the actual path to your Springfield PDF):

```powershell
pwsh -Command "flutter test integration_test/generate_golden_fixtures_test.dart -d windows --dart-define='SPRINGFIELD_PDF=<your-local-path-to-springfield-pdf>'"
```

Regeneration takes 2-3 minutes. Run this whenever any pipeline stage code has changed.

### Stage Trace Commands

```powershell
pwsh -Command "flutter test test/features/pdf/ --dart-define=PDF_PARSER_DIAGNOSTICS=true"
pwsh -Command "flutter test test/features/pdf/services/<test_file>.dart"
pwsh -Command "flutter test test/features/pdf/"
```

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
- If no output for 60s — kill the process and report as timeout
