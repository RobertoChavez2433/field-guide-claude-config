# Flutter Verification Commands

Specific commands for verifying Flutter project state.

## Critical: Windows/Git Bash

**Always use PowerShell for Flutter commands on Windows.**

Git Bash silently swallows output, causing false confidence.

```bash
# WRONG: Git Bash
flutter test  # Output may be lost

# RIGHT: PowerShell
pwsh -Command "flutter test"  # Full output visible
```

## Test Verification

### Run All Tests

```bash
pwsh -Command "flutter test"
```

**Expected output for pass**:
```
00:15 +247: All tests passed!
```

**Expected output for failure**:
```
00:12 +245 -2: Some tests failed.
```

### Run Specific Test File

```bash
pwsh -Command "flutter test test/data/repositories/project_repository_test.dart"
```

### Run Tests with Coverage

```bash
pwsh -Command "flutter test --coverage"
```

**Evidence required**: Coverage percentage and "All tests passed"

## Analyzer Verification

### Run Static Analysis

```bash
pwsh -Command "flutter analyze"
```

**Expected output for clean**:
```
Analyzing construction_inspector...
No issues found!
```

**Expected output with issues**:
```
Analyzing construction_inspector...
   info • Unused import: 'dart:async' • lib/file.dart:1:8 • unused_import
   error • The argument type 'String' can't be assigned to 'int' • lib/file.dart:25:10
```

### Auto-Fix Issues

```bash
pwsh -Command "dart fix --apply"
```

## Build Verification

### Android APK

```bash
pwsh -Command "flutter build apk --release"
```

**Expected output for success**:
```
Running Gradle task 'assembleRelease'...
✓ Built build/app/outputs/flutter-apk/app-release.apk (XX MB)
```

### Windows

```bash
pwsh -Command "flutter build windows --release"
```

### Clean Build

```bash
pwsh -Command "flutter clean && flutter build apk --release"
```

## E2E Test Verification

### Run All Patrol Tests

```bash
pwsh -Command "patrol test"
```

### Run Specific Patrol Test

```bash
pwsh -Command "patrol test -t integration_test/patrol/e2e_tests/navigation_flow_test.dart"
```

**Expected output for pass**:
```
✓ navigation flow test (15.3s)

1 test passed.
```

### Verbose Mode for Debugging

```bash
pwsh -Command "patrol test --verbose -t [path]"
```

## Golden Test Verification

### Run Golden Tests

```bash
pwsh -Command "flutter test test/golden/"
```

### Update Baselines

```bash
pwsh -Command "flutter test --update-goldens test/golden/"
```

## Quick Verification Script

Full verification in one command:

```bash
pwsh -Command "flutter analyze && flutter test && echo 'All checks passed!'"
```

**Evidence required**: "No issues found" AND "All tests passed"

## Verification Checklist by Task

### After Code Changes

- [ ] `flutter analyze` → No issues
- [ ] `flutter test` → All pass
- [ ] Changed functionality → Manual test

### Before Commit

- [ ] `flutter analyze` → No issues
- [ ] `flutter test` → All pass

### Before PR

- [ ] `flutter analyze` → No issues
- [ ] `flutter test` → All pass
- [ ] `flutter build apk --release` → Builds

### After Bug Fix

- [ ] Original bug → No longer reproduces
- [ ] `flutter test` → All pass (including new test for bug)

## Common Gotchas

### False Positive: Exit Code 0 with Warnings

```bash
$ pwsh -Command "flutter analyze"
Analyzing...
   info • ... • some_warning
# Exit code is still 0!
```

**Always read the full output**, not just exit code.

### False Positive: Partial Test Run

```bash
$ pwsh -Command "flutter test test/specific_test.dart"
+1: All tests passed!
# Only ran 1 test, not full suite!
```

**Before claiming "tests pass", run full suite.**

### False Positive: Cached Build

```bash
$ pwsh -Command "flutter build apk"
# Uses cached artifacts, may hide issues
```

**For thorough verification, clean first.**
