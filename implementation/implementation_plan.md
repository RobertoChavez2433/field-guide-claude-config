# Patrol Full Test Suite Fix - Implementation Plan

**Last Updated**: 2026-01-21
**Status**: READY FOR IMPLEMENTATION
**Source**: Research findings from 4 technical investigations (memory/batching, MANAGE_EXTERNAL_STORAGE, Permission.photos asymmetry, contractor test failure)

---

## Overview

This plan addresses running the full Patrol test suite (84 tests across 12 files) without crashes, and fixes 3 critical permission/policy issues. The highest priority is implementing a batched test runner to prevent native resource exhaustion after ~20 tests.

**Current State**: 19/20 tests passing (95%), but only when running small batches manually
**Goal**: Run all 84 tests reliably with automated batching and device resets

---

## Task 1: Batched Patrol Test Runner (P0 - CRITICAL)

### Summary
Create PowerShell script to run Patrol tests in batches of 15-20 with device resets between batches to prevent memory exhaustion from native resource accumulation (Dalvik VM, Surface flinger, SQLite connections).

### Problem Analysis
- **Root Cause**: Native Android resources accumulate across sequential test runs
- **Current Config**: Already optimal (12GB JVM heap, Test Orchestrator 1.6.1, maxTestsPerDevice=5)
- **Solution**: Reset app between batches using `adb shell pm clear com.fvconstruction.construction_inspector`
- **Test Count**: 84 total tests across 12 files

### Test Batches (4 batches, 15-24 tests each)

**Batch 1 (20 tests) - Smoke + Permissions**:
- `app_smoke_test.dart` (3 tests)
- `auth_flow_test.dart` (10 tests)
- `camera_permission_test.dart` (3 tests)
- `location_permission_test.dart` (4 tests)

**Batch 2 (20 tests) - Core Features**:
- `entry_management_test.dart` (11 tests)
- `photo_capture_test.dart` (5 tests)
- `contractors_flow_test.dart` (4 tests)

**Batch 3 (20 tests) - Secondary Features**:
- `project_management_test.dart` (9 tests)
- `quantities_flow_test.dart` (5 tests)
- `settings_flow_test.dart` (6 tests)

**Batch 4 (24 tests) - Flow + Offline**:
- `navigation_flow_test.dart` (14 tests)
- `offline_mode_test.dart` (10 tests)

### Implementation Steps

1. Create PowerShell script `run_patrol_batched.ps1` in project root
2. Script features:
   - Run batches sequentially
   - Device reset between batches (`adb shell pm clear`)
   - Aggregate results to single report
   - Stop on first batch failure (optional flag to continue)
   - Colorized output for status visibility
   - Total time tracking

### PowerShell Script (Full Code)

```powershell
#!/usr/bin/env pwsh
#
# Batched Patrol Test Runner
# Runs Patrol tests in batches with device resets to prevent memory exhaustion
#
# Usage:
#   ./run_patrol_batched.ps1                    # Run all 4 batches
#   ./run_patrol_batched.ps1 -Batch 2           # Run specific batch only
#   ./run_patrol_batched.ps1 -ContinueOnError   # Don't stop on batch failure
#

param(
    [int]$Batch = 0,           # 0 = all batches, 1-4 = specific batch
    [switch]$ContinueOnError,  # Continue running batches even if one fails
    [switch]$SkipReset         # Skip device reset (for debugging)
)

$ErrorActionPreference = "Stop"
$StartTime = Get-Date

# ANSI color codes for output
$Colors = @{
    Reset   = "`e[0m"
    Red     = "`e[31m"
    Green   = "`e[32m"
    Yellow  = "`e[33m"
    Blue    = "`e[34m"
    Cyan    = "`e[36m"
    Bold    = "`e[1m"
}

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "Reset")
    Write-Host "$($Colors[$Color])$Message$($Colors.Reset)"
}

function Write-SectionHeader {
    param([string]$Title)
    Write-Host ""
    Write-ColorOutput "═══════════════════════════════════════════════════════════════" "Cyan"
    Write-ColorOutput "  $Title" "Bold"
    Write-ColorOutput "═══════════════════════════════════════════════════════════════" "Cyan"
    Write-Host ""
}

# Define test batches
$TestBatches = @(
    @{
        Name = "Batch 1: Smoke + Permissions (20 tests)"
        Files = @(
            "app_smoke_test.dart",
            "auth_flow_test.dart",
            "camera_permission_test.dart",
            "location_permission_test.dart"
        )
    },
    @{
        Name = "Batch 2: Core Features (20 tests)"
        Files = @(
            "entry_management_test.dart",
            "photo_capture_test.dart",
            "contractors_flow_test.dart"
        )
    },
    @{
        Name = "Batch 3: Secondary Features (20 tests)"
        Files = @(
            "project_management_test.dart",
            "quantities_flow_test.dart",
            "settings_flow_test.dart"
        )
    },
    @{
        Name = "Batch 4: Flow + Offline (24 tests)"
        Files = @(
            "navigation_flow_test.dart",
            "offline_mode_test.dart"
        )
    }
)

# Results tracking
$Results = @{
    TotalBatches = 0
    PassedBatches = 0
    FailedBatches = 0
    SkippedBatches = 0
    BatchResults = @()
}

function Reset-Device {
    Write-ColorOutput "Resetting device app data..." "Yellow"
    try {
        $result = adb shell pm clear com.fvconstruction.construction_inspector 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "Warning: Device reset failed: $result" "Yellow"
            return $false
        }
        Write-ColorOutput "Device reset successful" "Green"
        Start-Sleep -Seconds 2  # Allow device to stabilize
        return $true
    } catch {
        Write-ColorOutput "Error during device reset: $_" "Red"
        return $false
    }
}

function Run-Batch {
    param(
        [int]$BatchNumber,
        [hashtable]$BatchConfig
    )

    Write-SectionHeader $BatchConfig.Name

    # Reset device before batch (unless skipped)
    if (-not $SkipReset) {
        if (-not (Reset-Device)) {
            Write-ColorOutput "Device reset failed, but continuing..." "Yellow"
        }
    }

    # Build test target list
    $TestTargets = @()
    foreach ($file in $BatchConfig.Files) {
        $TestTargets += "integration_test/patrol/$file"
    }

    Write-ColorOutput "Test files ($($TestTargets.Count)):" "Cyan"
    foreach ($target in $TestTargets) {
        Write-Host "  - $target"
    }
    Write-Host ""

    # Run patrol test
    Write-ColorOutput "Running patrol test..." "Cyan"
    $TestArgs = @("test") + $TestTargets

    $TestStartTime = Get-Date
    try {
        & patrol @TestArgs
        $TestExitCode = $LASTEXITCODE
    } catch {
        $TestExitCode = 1
        Write-ColorOutput "Exception during test execution: $_" "Red"
    }
    $TestEndTime = Get-Date
    $TestDuration = $TestEndTime - $TestStartTime

    # Record result
    $BatchResult = @{
        BatchNumber = $BatchNumber
        Name = $BatchConfig.Name
        Files = $BatchConfig.Files
        Duration = $TestDuration
        Success = ($TestExitCode -eq 0)
        ExitCode = $TestExitCode
    }
    $Results.BatchResults += $BatchResult

    # Display result
    Write-Host ""
    if ($TestExitCode -eq 0) {
        Write-ColorOutput "✓ Batch $BatchNumber PASSED" "Green"
        Write-ColorOutput "  Duration: $($TestDuration.ToString('mm\:ss'))" "Green"
        $Results.PassedBatches++
        return $true
    } else {
        Write-ColorOutput "✗ Batch $BatchNumber FAILED (Exit code: $TestExitCode)" "Red"
        Write-ColorOutput "  Duration: $($TestDuration.ToString('mm\:ss'))" "Red"
        $Results.FailedBatches++
        return $false
    }
}

# Main execution
Write-SectionHeader "Patrol Batched Test Runner"
Write-ColorOutput "Total batches: $($TestBatches.Count)" "Cyan"
Write-ColorOutput "Total tests: 84" "Cyan"

if ($Batch -gt 0) {
    Write-ColorOutput "Running specific batch: $Batch" "Yellow"
}

if ($SkipReset) {
    Write-ColorOutput "WARNING: Device reset disabled" "Yellow"
}

if ($ContinueOnError) {
    Write-ColorOutput "Mode: Continue on error" "Yellow"
}

Write-Host ""

# Check if device is connected
Write-ColorOutput "Checking for connected device..." "Cyan"
$DeviceCheck = adb devices 2>&1 | Select-String -Pattern "device$"
if (-not $DeviceCheck) {
    Write-ColorOutput "ERROR: No Android device connected" "Red"
    Write-ColorOutput "Connect a device via USB or start an emulator, then try again." "Red"
    exit 1
}
Write-ColorOutput "Device connected: $($DeviceCheck.Line)" "Green"

# Run batches
$BatchesToRun = if ($Batch -gt 0) { @($Batch) } else { 1..$TestBatches.Count }

foreach ($batchNum in $BatchesToRun) {
    $Results.TotalBatches++
    $batchConfig = $TestBatches[$batchNum - 1]

    $success = Run-Batch -BatchNumber $batchNum -BatchConfig $batchConfig

    if (-not $success -and -not $ContinueOnError) {
        Write-Host ""
        Write-ColorOutput "Stopping execution due to batch failure" "Red"
        Write-ColorOutput "Use -ContinueOnError flag to run all batches regardless of failures" "Yellow"
        break
    }

    # Pause between batches
    if ($batchNum -lt $TestBatches.Count) {
        Write-ColorOutput "Pausing 5 seconds before next batch..." "Yellow"
        Start-Sleep -Seconds 5
    }
}

# Final summary
$EndTime = Get-Date
$TotalDuration = $EndTime - $StartTime

Write-SectionHeader "Test Summary"

Write-Host "Batches:"
Write-ColorOutput "  Total:   $($Results.TotalBatches)" "Cyan"
Write-ColorOutput "  Passed:  $($Results.PassedBatches)" "Green"
Write-ColorOutput "  Failed:  $($Results.FailedBatches)" "Red"
Write-Host ""

Write-Host "Batch Details:"
foreach ($result in $Results.BatchResults) {
    $status = if ($result.Success) { "PASS" } else { "FAIL" }
    $color = if ($result.Success) { "Green" } else { "Red" }
    $duration = $result.Duration.ToString('mm\:ss')
    Write-ColorOutput "  Batch $($result.BatchNumber): $status ($duration)" $color
}

Write-Host ""
Write-ColorOutput "Total Duration: $($TotalDuration.ToString('hh\:mm\:ss'))" "Cyan"

# Exit with appropriate code
if ($Results.FailedBatches -gt 0) {
    Write-Host ""
    Write-ColorOutput "TESTS FAILED" "Red"
    exit 1
} else {
    Write-Host ""
    Write-ColorOutput "ALL TESTS PASSED" "Green"
    exit 0
}
```

### Files to Create
| File | Purpose |
|------|---------|
| `run_patrol_batched.ps1` | Batched test runner with device resets |

### Testing Steps
1. Ensure Android device/emulator connected: `adb devices`
2. Run full suite: `pwsh run_patrol_batched.ps1`
3. Run specific batch: `pwsh run_patrol_batched.ps1 -Batch 2`
4. Continue on errors: `pwsh run_patrol_batched.ps1 -ContinueOnError`

### Estimated Effort
- **Implementation**: 30 minutes (script creation)
- **Testing**: 45 minutes (run all 4 batches, ~12 minutes per batch)
- **Total**: 1.5 hours

### Agent Assignment
**Agent**: `qa-testing-agent`

---

## Task 2: Remove MANAGE_EXTERNAL_STORAGE Permission (P0 - CRITICAL)

### Summary
Remove MANAGE_EXTERNAL_STORAGE permission to avoid Google Play rejection. FilePicker v8.0.0 handles scoped storage internally on Android 10+, making this dangerous permission unnecessary.

### Problem Analysis
- **Risk**: HIGH - Google Play rejects apps with MANAGE_EXTERNAL_STORAGE unless absolutely necessary
- **Root Cause**: Permission added for PDF export, but FilePicker handles scoped storage internally
- **2026 Policy**: Google requires "All Files Access" permission only for file managers, backup apps, anti-virus
- **Current Usage**: Only checked before FilePicker.platform.saveFile() operations

### Implementation Steps

1. **Remove from AndroidManifest.xml** (line 23)
   - Remove: `<uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE"/>`

2. **Simplify PermissionService.dart** (lines 19-56)
   - Remove MANAGE_EXTERNAL_STORAGE from `hasStoragePermission()`
   - Remove MANAGE_EXTERNAL_STORAGE from `requestStoragePermission()`
   - Remove MANAGE_EXTERNAL_STORAGE from `isStoragePermissionPermanentlyDenied()`
   - Keep legacy storage (API < 13) and photos permission (API 13+)

3. **Update permission flow logic**
   - For Android 13+: Use Permission.photos (granular)
   - For Android < 13: Use Permission.storage (legacy)
   - FilePicker will handle scoped storage dialog automatically

### Files to Modify
| File | Changes |
|------|---------|
| `android/app/src/main/AndroidManifest.xml` | Remove line 23 (MANAGE_EXTERNAL_STORAGE) |
| `lib/services/permission_service.dart` | Remove MANAGE_EXTERNAL_STORAGE checks and requests (lines 19-56, 62-65) |

### Code Changes

**Before (permission_service.dart lines 19-56)**:
```dart
// Check MANAGE_EXTERNAL_STORAGE for Android 11+
final status = await Permission.manageExternalStorage.status;
if (status.isGranted) return true;

// Try MANAGE_EXTERNAL_STORAGE first (Android 11+)
var status = await Permission.manageExternalStorage.request();
```

**After**:
```dart
// No MANAGE_EXTERNAL_STORAGE check - FilePicker handles scoped storage internally
// Just check photos (Android 13+) or legacy storage (Android < 13)
```

### Testing Steps
1. Run `flutter analyze` - should pass
2. Test PDF export on Android 13+ device (should show scoped storage picker)
3. Test PDF export on Android 11-12 device (should show legacy storage picker)
4. Verify no "All Files Access" permission request dialog appears
5. Verify PDF saves successfully to user-selected location

### Rollback Procedure
If FilePicker fails to save:
1. Revert AndroidManifest.xml line 23
2. Revert permission_service.dart changes
3. Run `flutter clean && flutter pub get`

### Estimated Effort
- **Implementation**: 20 minutes
- **Testing**: 30 minutes (test on multiple Android versions)
- **Total**: 1 hour

### Agent Assignment
**Agent**: `data-layer-agent`

---

## Task 3: Fix Permission.photos Asymmetry (P1 - HIGH)

### Summary
Add Permission.photos.request() to requestStoragePermission() flow on Android 13+ to match the existing check in hasStoragePermission(). Currently checks for photos permission but never requests it.

### Problem Analysis
- **Issue**: hasStoragePermission() checks Permission.photos, but requestStoragePermission() never requests it
- **Impact**: Users on Android 13+ see "Allow access to all files?" instead of "Allow access to photos?"
- **Root Cause**: Request flow skips photos permission and goes straight to manageExternalStorage/storage
- **User Experience**: More invasive permission dialog than necessary

### Implementation Steps

1. **Update requestStoragePermission()** in `lib/services/permission_service.dart` (lines 30-56)
2. **Add Permission.photos request FIRST** on Android 13+
3. **Fall back to legacy permissions** if photos permission denied
4. **Maintain backward compatibility** with Android < 13

### Files to Modify
| File | Changes |
|------|---------|
| `lib/services/permission_service.dart` | Add Permission.photos.request() before legacy permissions (lines 30-56) |

### Code Changes

**Before (lines 30-56)**:
```dart
Future<bool> requestStoragePermission() async {
  if (!Platform.isAndroid) return true;

  debugPrint('[Permission] Requesting storage permission...');

  // Try MANAGE_EXTERNAL_STORAGE first (Android 11+)
  var status = await Permission.manageExternalStorage.request();
  // ... rest of flow
}
```

**After**:
```dart
Future<bool> requestStoragePermission() async {
  if (!Platform.isAndroid) return true;

  debugPrint('[Permission] Requesting storage permission...');

  // For Android 13+ (API 33+), request granular photo permission FIRST
  if (await _isAndroid13OrHigher()) {
    debugPrint('[Permission] Requesting photos permission (Android 13+)...');
    var status = await Permission.photos.request();
    debugPrint('[Permission] Photos permission status: $status');

    if (status.isGranted) {
      debugPrint('[Permission] Storage permission granted via photos permission');
      return true;
    }
    // If photos denied, fall through to legacy permissions
    debugPrint('[Permission] Photos permission denied, trying legacy permissions...');
  }

  // Fall back to legacy storage permission for Android < 13 or if photos denied
  var status = await Permission.storage.request();
  debugPrint('[Permission] Legacy storage status: $status');

  if (status.isGranted) {
    debugPrint('[Permission] Storage permission granted via legacy storage');
    return true;
  }

  debugPrint('[Permission] Storage permission denied');
  return false;
}
```

**Note**: After Task 2 completes, MANAGE_EXTERNAL_STORAGE will already be removed, so this implementation assumes Task 2 is done first.

### Testing Steps
1. Test on Android 13+ device:
   - Should see "Allow access to photos?" dialog (not "all files")
   - Grant permission - should return true
   - Deny permission - should fall back to legacy dialog
2. Test on Android 11-12 device:
   - Should skip photos permission
   - Should see legacy storage dialog
3. Test on Android < 11 device:
   - Should see standard storage dialog
4. Verify photo capture still works on all Android versions

### Estimated Effort
- **Implementation**: 30 minutes
- **Testing**: 30 minutes (test across Android versions)
- **Total**: 1 hour

### Agent Assignment
**Agent**: `data-layer-agent`

---

## Task 4: Fix Contractor Test Keyboard Overlay (P2 - MEDIUM)

### Summary
Fix "adds contractor to project" test failure where Save button is not hit-testable due to soft keyboard overlaying AlertDialog action buttons.

### Problem Analysis
- **Test**: `integration_test/patrol/contractors_flow_test.dart` line 120-128
- **Issue**: After entering text in contractor name field, keyboard remains open and overlays Save button
- **Dialog**: `lib/features/projects/presentation/screens/project_setup_screen.dart` lines 586-658
- **Key**: Save button already has Key('contractor_save_button')

### Solution Options

**Option A: Test-Side Fix (RECOMMENDED)**
Dismiss keyboard before tapping Save button:
```dart
// After entering contractor name
await nameField.enterText('Test Contractor ${DateTime.now().millisecondsSinceEpoch}');
await $.pumpAndSettle();

// Dismiss keyboard
await $.native.tap(Selector(text: 'Add Contractor'));  // Tap dialog title
await $.pumpAndSettle();

// OR use native Android back button
await $.native.pressBack();
await $.pumpAndSettle();

// Then tap Save
await $(Key('contractor_save_button')).tap();
```

**Option B: UI-Side Fix**
Wrap dialog content in SingleChildScrollView:
```dart
content: SingleChildScrollView(
  child: Column(
    mainAxisSize: MainAxisSize.min,
    children: [ /* fields */ ],
  ),
),
```

**Recommendation**: Use Option A (test-side fix) to keep UI unchanged and avoid potential regression in production dialogs.

### Implementation Steps

1. **Modify contractors_flow_test.dart** (lines 115-128)
2. **Add keyboard dismissal** after text entry
3. **Verify Save button is hit-testable** before tapping
4. **Add comments** explaining keyboard handling

### Files to Modify
| File | Changes |
|------|---------|
| `integration_test/patrol/contractors_flow_test.dart` | Add keyboard dismissal before Save button tap (lines 115-128) |

### Code Changes

**Before (lines 115-128)**:
```dart
// Save contractor
final saveButton = $('Save');
final createButton = $('Create');
final addButtonFinal = $('Add');

if (saveButton.exists) {
  await saveButton.tap();
  await $.pumpAndSettle();
} else if (createButton.exists) {
  await createButton.tap();
  await $.pumpAndSettle();
} else if (addButtonFinal.exists) {
  await addButtonFinal.tap();
  await $.pumpAndSettle();
}
```

**After**:
```dart
// Dismiss keyboard before tapping Save (prevents overlay on dialog buttons)
await $.native.pressBack();  // Native Android back dismisses keyboard
await $.pumpAndSettle();
await Future.delayed(const Duration(milliseconds: 500));

// Save contractor
final saveButton = $(Key('contractor_save_button'));
if (saveButton.exists) {
  await saveButton.tap();
  await $.pumpAndSettle();
} else {
  // Fallback to text-based search
  final saveByText = $('Save');
  if (saveByText.exists) {
    await saveByText.tap();
    await $.pumpAndSettle();
  }
}
```

### Testing Steps
1. Run test: `patrol test integration_test/patrol/contractors_flow_test.dart`
2. Verify "adds contractor to project" test passes
3. Verify other 3 contractor tests still pass
4. Manually test contractor creation in app (ensure keyboard doesn't break UX)

### Rollback Procedure
If test still fails or causes regression:
1. Revert contractors_flow_test.dart changes
2. Consider Option B (UI-side fix) as alternative

### Estimated Effort
- **Implementation**: 20 minutes
- **Testing**: 20 minutes
- **Total**: 40 minutes

### Agent Assignment
**Agent**: `qa-testing-agent`

---

## Execution Order

### Phase 1: Critical Infrastructure (P0)
**Duration**: ~2.5 hours

1. **Task 1: Batched Test Runner** (1.5 hours) - `qa-testing-agent`
   - Highest priority - enables running full suite
   - Create run_patrol_batched.ps1 script
   - Test all 4 batches with device resets

2. **Task 2: Remove MANAGE_EXTERNAL_STORAGE** (1 hour) - `data-layer-agent`
   - Critical for Google Play compliance
   - Remove from AndroidManifest.xml
   - Simplify PermissionService.dart

### Phase 2: Permission Flow Improvement (P1)
**Duration**: ~1 hour

3. **Task 3: Fix Permission.photos Asymmetry** (1 hour) - `data-layer-agent`
   - Depends on Task 2 completion
   - Add photos permission request for Android 13+
   - Better UX with granular permissions

### Phase 3: Test Reliability (P2)
**Duration**: ~40 minutes

4. **Task 4: Fix Contractor Test** (40 minutes) - `qa-testing-agent`
   - Independent of other tasks
   - Add keyboard dismissal in test
   - Can run in parallel with Phase 2

**Total Estimated Duration**: ~4 hours

---

## Verification

### After Task 1 (Batched Runner)
- [ ] Script runs all 4 batches successfully
- [ ] Device resets occur between batches (check logcat)
- [ ] No memory-related crashes in batch 3-4
- [ ] Total runtime < 60 minutes
- [ ] Exit code 0 if all tests pass

### After Task 2 (Remove MANAGE_EXTERNAL_STORAGE)
- [ ] `flutter analyze` passes
- [ ] No permission dialogs requesting "All Files Access"
- [ ] PDF export works on Android 13+ (scoped storage picker)
- [ ] PDF export works on Android 11-12 (legacy picker)
- [ ] PDFs save to user-selected location successfully

### After Task 3 (Permission.photos)
- [ ] Android 13+ shows "Allow photos?" dialog (not "all files")
- [ ] Granting photos permission returns true
- [ ] Denying photos permission falls back to legacy
- [ ] Photo capture still works on all Android versions
- [ ] No regression on Android < 13

### After Task 4 (Contractor Test)
- [ ] `adds contractor to project` test passes
- [ ] Other 3 contractor tests still pass
- [ ] No regression in manual contractor creation flow
- [ ] Keyboard dismissal doesn't interfere with UX

### Full Suite Verification
After all tasks complete:
1. Run `flutter analyze` - 0 errors, ~21 info warnings (expected)
2. Run `flutter test` - 392 tests passing (363 unit + 29 golden)
3. Run `pwsh run_patrol_batched.ps1` - All 84 Patrol tests passing
4. Manual smoke test:
   - Create project
   - Add contractor (verify no keyboard issues)
   - Capture photo (verify photos permission on Android 13+)
   - Export PDF (verify scoped storage picker, no "all files" dialog)
5. Check Google Play Policy Compliance:
   - No MANAGE_EXTERNAL_STORAGE permission in manifest
   - Granular permissions (photos, camera, location) instead of broad permissions

---

## Rollback Procedures

### Task 1 Rollback (Batched Runner)
- Delete `run_patrol_batched.ps1`
- Continue using `patrol test` for manual batch testing
- No code changes to revert

### Task 2 Rollback (MANAGE_EXTERNAL_STORAGE)
```bash
cd /c/Users/rseba/Projects/Field\ Guide\ App
git checkout HEAD -- android/app/src/main/AndroidManifest.xml
git checkout HEAD -- lib/services/permission_service.dart
flutter clean
flutter pub get
```

### Task 3 Rollback (Permission.photos)
```bash
git checkout HEAD -- lib/services/permission_service.dart
flutter clean
```

### Task 4 Rollback (Contractor Test)
```bash
git checkout HEAD -- integration_test/patrol/contractors_flow_test.dart
```

### Full Rollback (All Tasks)
```bash
cd /c/Users/rseba/Projects/Field\ Guide\ App
git stash
rm -f run_patrol_batched.ps1
flutter clean
flutter pub get
```

---

## Success Metrics

### Quantitative
- **Test Coverage**: 84/84 Patrol tests passing (100%)
- **Batch Success**: 4/4 batches complete without crashes
- **Runtime**: Full suite completes in < 60 minutes
- **Memory**: No OOM crashes in any batch
- **Permissions**: 0 violations of Google Play policies

### Qualitative
- Automated test runner saves manual effort
- Granular permissions improve user trust (photos vs all files)
- More reliable CI/CD integration (batched tests)
- Better Android 13+ user experience
- Google Play submission readiness

---

## Dependencies

### External Dependencies
- Android device or emulator connected via ADB
- PowerShell 7+ installed (already available per global CLAUDE.md)
- Patrol 3.20.0 (already installed)
- Android SDK with ADB in PATH

### Task Dependencies
```
Task 1 (Batched Runner)
  ├── No dependencies
  └── Can run immediately

Task 2 (Remove MANAGE_EXTERNAL_STORAGE)
  ├── No dependencies
  └── Should complete before Task 3

Task 3 (Permission.photos)
  ├── Depends on: Task 2 completion
  └── Code assumes MANAGE_EXTERNAL_STORAGE removed

Task 4 (Contractor Test)
  ├── No dependencies
  └── Can run in parallel with Tasks 2-3
```

**Recommended Execution**: Sequential (Phase 1 → Phase 2 → Phase 3) for clear progress tracking

---

## Notes

### Known Limitations
- Batch script requires PowerShell 7+ (already available)
- Device must remain connected during full test run (~60 min)
- Some tests may still be flaky due to timing/animation issues
- Test batches optimized for current test distribution (may need adjustment if tests added)

### Future Improvements
- Add test retry logic (3 attempts before marking failure)
- Parallel batch execution (if multiple devices available)
- CI/CD integration (GitHub Actions with Android emulator)
- Test result HTML report generation
- Automatic screenshot capture on test failure

### Related Documentation
- `.claude/docs/2026-platform-standards-update.md` - Platform version standards
- `integration_test/patrol/README.md` - Patrol test documentation
- `integration_test/patrol/QUICK_START.md` - Patrol setup guide
- `.claude/memory/defects.md` - Known issues and anti-patterns

---

## Agent Assignments Summary

| Task | Agent | Duration | Priority |
|------|-------|----------|----------|
| Task 1: Batched Test Runner | `qa-testing-agent` | 1.5 hours | P0 |
| Task 2: Remove MANAGE_EXTERNAL_STORAGE | `data-layer-agent` | 1 hour | P0 |
| Task 3: Fix Permission.photos | `data-layer-agent` | 1 hour | P1 |
| Task 4: Fix Contractor Test | `qa-testing-agent` | 40 minutes | P2 |

**Total Effort**: ~4 hours across 2 specialized agents

---

## Questions for User (If Any)

None - all research findings are complete and actionable. Ready for implementation approval.
