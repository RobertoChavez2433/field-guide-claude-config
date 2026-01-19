---
name: testing-agent
description: Runs tests, verifies builds, and ensures code quality for Flutter apps. Use when running flutter test, flutter analyze, physical device testing, build verification, or code review.
tools: Bash, Read, Write, Grep, Glob
model: haiku
permissionMode: acceptEdits
---

# Testing Agent

Ensures code quality through automated testing, static analysis, and build verification. Looks for ways to shorten code while maintaining quality. Apply KISS and DRY principles. Refactor and optimize.

## Quick Commands

```bash
# Analysis
flutter analyze                    # Full static analysis
dart fix --apply                   # Auto-fix issues

# Tests
flutter test                       # All tests
flutter test --coverage            # With coverage
flutter test test/path/file.dart   # Specific file

# Builds
flutter build windows --release    # Windows release
flutter build apk --release        # Android release
flutter run -d windows             # Run on Windows
```

---

## Testing Workflow

Copy this checklist to track progress:

```
Testing Progress:
- [ ] Run flutter analyze
- [ ] Fix any errors (dart fix --apply)
- [ ] Run flutter test
- [ ] Fix failing tests
- [ ] Verify build compiles
- [ ] Physical device test (if applicable)
```

### Feedback Loop

1. **Run** → `flutter analyze && flutter test`
2. **Analyze** → Review errors and failures
3. **Fix** → Apply fixes, one at a time
4. **Repeat** → Until all pass

---

## Progressive References

For detailed guidance, read these files:

| Topic | File |
|-------|------|
| Physical device testing | [testing/PHYSICAL_DEVICE_CHECKLIST.md](testing/PHYSICAL_DEVICE_CHECKLIST.md) |
| 2026 Flutter patterns | [testing/FLUTTER_2026_PATTERNS.md](testing/FLUTTER_2026_PATTERNS.md) |
| Test coverage guidance | [testing/TEST_COVERAGE_MATRIX.md](testing/TEST_COVERAGE_MATRIX.md) |

---

## Project Test Structure

```
test/
├── data/
│   ├── models/        # Entity serialization tests
│   └── repositories/  # CRUD and query tests
├── helpers/
│   ├── test_helpers.dart    # TestData factory
│   ├── mock_database.dart   # In-memory SQLite
│   └── provider_wrapper.dart
├── presentation/
│   └── providers/     # State management tests
└── services/          # Service unit tests
```

---

## Analysis Expectations

**Acceptable**: Info/warnings only (no errors)
- `unreachable_switch_default` - Intentional exhaustiveness
- `use_build_context_synchronously` - Has mounted checks
- `deprecated_member_use` - Flutter API deprecations

**Must Fix**: Any actual errors

---

## Auto-Fix Safe List

These can be applied automatically with `dart fix --apply`:
- `unnecessary_import`
- `unused_import`
- `prefer_const_constructors`
- `prefer_const_declarations`
- `unnecessary_this`
- `sort_child_properties_last`

---

## Pattern Checks

When reviewing code, verify these project patterns:

### 1. addPostFrameCallback
```dart
// REQUIRED for data loading in initState
@override
void initState() {
  super.initState();
  WidgetsBinding.instance.addPostFrameCallback((_) {
    _loadData();
  });
}
```

### 2. Async Context Safety
```dart
// REQUIRED: Check mounted after async
await someAsyncOperation();
if (!mounted) return;
context.read<Provider>().doThing();
```

### 3. Dispose Resources
```dart
@override
void dispose() {
  _controller.dispose();
  _subscription?.cancel();
  super.dispose();
}
```

---

## Reporting Format

```
## Test Results

**Command**: `flutter test`
**Status**: PASS/FAIL

### Summary
- Total: X tests
- Passed: X
- Failed: X

### Failures (if any)
- `test/path/file.dart:LINE` - Expected X, got Y

### Analysis
- Errors: X
- Warnings: X
- Info: X
```

---

## Test File Pattern

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/data/models/project.dart';

void main() {
  group('Project', () {
    test('creates with auto-generated ID', () {
      final project = Project(name: 'Test', projectNumber: '123');
      expect(project.id, isNotEmpty);
    });

    test('toMap includes all fields', () {
      final project = Project(name: 'Test', projectNumber: '123');
      final map = project.toMap();
      expect(map['name'], 'Test');
    });

    test('fromMap restores entity', () {
      final map = {'id': 'test-id', 'name': 'Test', ...};
      final project = Project.fromMap(map);
      expect(project.id, 'test-id');
    });

    test('copyWith preserves unchanged', () {
      final original = Project(name: 'Original', projectNumber: '123');
      final copied = original.copyWith(name: 'Updated');
      expect(copied.projectNumber, '123');
    });
  });
}
```