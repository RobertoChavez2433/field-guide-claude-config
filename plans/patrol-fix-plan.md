# Patrol Test Infrastructure Fix - Implementation Plan

**Last Updated**: 2026-01-21
**Status**: PHASE 1 COMPLETE - READY FOR TEST RUN
**Source**: QA Agent investigation + user-reported JDK error + planning analysis

---

## Overview
Fix Patrol integration test infrastructure to enable automated Android testing.

---

## Task Status Summary

| Task | Priority | Status | Notes |
|------|----------|--------|-------|
| Task 1: JDK 17+ | P0 | ✅ DONE | Java 21 verified (Session 16) |
| Task 2: patrol bootstrap | P0 | ⚠️ N/A | Not needed in Patrol CLI 3.11.0 |
| Task 3: Dynamic device detection | P1 | ✅ DONE | run_patrol.ps1 updated (Session 17) |
| Task 4: Widget keys | P1 | ⏳ Pending | Login screen keys needed |
| Task 5: Replace delays | P2 | ⏳ Pending | 50+ occurrences |
| Task 6: First test run | P0 | ⏳ Ready | Can attempt now |

---

## Completed Tasks

### Task 1: JDK 17+ Configuration ✅
- **Completed**: Session 16
- **Result**: Java 21.0.8 installed and working
- **Verification**: `java -version` returns 21.0.8

### Task 2: Native Test Infrastructure ⚠️ NOT NEEDED
- **Discovery**: Patrol CLI 3.11.0 doesn't have `bootstrap` command
- **How it works**: Native test infrastructure is generated automatically on first `patrol test` run
- **Note**: androidTest directory will be created when running tests

### Task 3: Dynamic Device Detection ✅
- **Completed**: Session 17
- **Implementation**: run_patrol.ps1 now uses `flutter devices --machine`
- **Features**:
  - Auto-detects first connected Android device
  - Error handling for no device
  - Displays device name before running

---

## Remaining Tasks

### Task 4: Add Missing Widget Keys (P1)

Add keys to login screen widgets for Patrol test selectors:

```dart
// lib/features/auth/presentation/screens/login_screen.dart
TextField(
  key: const Key('login_email_field'),
  // ...
),
TextField(
  key: const Key('login_password_field'),
  // ...
),
ElevatedButton(
  key: const Key('login_sign_in_button'),
  // ...
),
TextButton(
  key: const Key('login_sign_up_button'),
  // ...
),
```

**Agent**: flutter-specialist-agent

### Task 5: Replace Hardcoded Delays (P2)

Replace `Future.delayed()` with Patrol smart waiting:

```dart
// Before
await Future.delayed(const Duration(seconds: 3));

// After
await $.waitUntilVisible($(LoginScreen));
```

**Files affected**: 50+ occurrences in integration_test/*.dart

**Agent**: qa-testing-agent

### Task 6: First Test Run (P0 - READY NOW)

```powershell
# Option 1: Use the updated script
pwsh .\run_patrol.ps1

# Option 2: Direct command
patrol test --target integration_test/patrol/app_smoke_test.dart --verbose
```

**Success Criteria**:
- [ ] Smoke test completes without infrastructure errors
- [ ] App launches on device
- [ ] Tests can interact with native elements

---

## Test Files Available

| Test File | Description |
|-----------|-------------|
| `app_smoke_test.dart` | Basic app launch |
| `camera_permission_test.dart` | Native camera permission |
| `location_permission_test.dart` | Native location permission |
| `photo_capture_test.dart` | Photo capture flow |
| `auth_flow_test.dart` | Authentication flow |
| `project_management_test.dart` | Project CRUD |
| `entry_management_test.dart` | Entry CRUD |
| `navigation_flow_test.dart` | App navigation |
| `offline_mode_test.dart` | Offline functionality |

---

## Next Steps

1. **Run smoke test** to verify infrastructure
2. **Add widget keys** if tests fail due to missing selectors
3. **Iterate** on test fixes as needed

---

## Rollback Plan

```powershell
cd "C:\Users\rseba\Projects\Field Guide App"
git restore .
git clean -fd
rm -r android/app/src/androidTest -ErrorAction SilentlyContinue
```
