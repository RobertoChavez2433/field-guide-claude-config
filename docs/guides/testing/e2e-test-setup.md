# E2E Test Setup Guide

> **Used By**: [qa-testing-agent](../../../agents/qa-testing-agent.md) and [planning-agent](../../../agents/planning-agent.md) for test environment configuration and CI/CD integration

Complete device and environment setup for running Patrol E2E tests.

## Prerequisites

- Android device/emulator with API 24+ (Android 7.0+)
- iOS device/simulator with iOS 15.0+
- Patrol CLI installed: `dart pub global activate patrol_cli`
- ADB (Android Debug Bridge) in PATH for Android testing

---

## Device Configuration

### 1. Animation Settings

Animations interfere with test stability. Disable all animations before running tests.

#### Android

**Option A: Manual (Developer Options)**
1. Enable Developer Options: Settings > About > Tap "Build Number" 7 times
2. Settings > System > Developer Options
3. Set all animation scales to **Animation off**:
   - Window animation scale > OFF
   - Transition animation scale > OFF
   - Animator duration scale > OFF

**Option B: ADB Commands**
```bash
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
```

**Verify**:
```bash
adb shell settings get global window_animation_scale
# Should output: 0
```

#### iOS

**Simulator**:
```bash
# Disable CoreAnimation animations
defaults write com.apple.CoreSimulator.SimulatorWindow AutomationModeEnabled -bool YES
```

**Physical Device**:
1. Settings > Accessibility > Motion > Reduce Motion > ON
2. Settings > General > Accessibility > Increase Contrast > Reduce Transparency > ON

---

### 2. Battery and Power Settings

Prevent device throttling during long test runs.

#### Android

**Disable Battery Optimization**:
```bash
# For debug builds
adb shell dumpsys deviceidle whitelist +com.example.construction_inspector

# Keep screen awake
adb shell svc power stayon true
```

**Manual**:
- Settings > Battery > Battery Optimization > All Apps > Construction Inspector > Don't optimize
- Keep device plugged in during tests
- Disable power saving mode

#### iOS

- Keep device plugged in
- Disable Low Power Mode: Settings > Battery > Low Power Mode > OFF
- Disable Auto-Lock: Settings > Display & Brightness > Auto-Lock > Never

---

### 3. Locale and Timezone

Use consistent locale/timezone for predictable text matching and timestamps.

#### Android

```bash
# Set locale to English (US)
adb shell "setprop persist.sys.locale en-US; setprop ctl.restart zygote"

# Set timezone to America/New_York
adb shell setprop persist.sys.timezone "America/New_York"
```

#### iOS

- Settings > General > Language & Region > Region > United States
- Settings > General > Date & Time > Time Zone > New York

**Recommended for CI**: Use UTC timezone to avoid daylight saving time issues.

---

### 4. Permissions

Grant required permissions before tests to avoid permission prompts.

#### Android

Run the provided script or use individual commands:

```bash
./integration_test/grant-permissions.sh
```

Or manually:
```bash
PACKAGE="com.example.construction_inspector"
adb shell pm grant $PACKAGE android.permission.CAMERA
adb shell pm grant $PACKAGE android.permission.ACCESS_FINE_LOCATION
adb shell pm grant $PACKAGE android.permission.ACCESS_COARSE_LOCATION
adb shell pm grant $PACKAGE android.permission.READ_EXTERNAL_STORAGE
adb shell pm grant $PACKAGE android.permission.WRITE_EXTERNAL_STORAGE
adb shell pm grant $PACKAGE android.permission.READ_MEDIA_IMAGES
adb shell pm grant $PACKAGE android.permission.READ_MEDIA_VIDEO
```

#### iOS

Patrol handles iOS permissions automatically via native test helpers.

---

## Clean Test Environment

Ensure a fresh state before each test run.

### Android

```bash
# Force stop app
adb shell am force-stop com.example.construction_inspector

# Clear all app data (database, preferences, files)
adb shell pm clear com.example.construction_inspector

# Wipe emulator to factory state (if needed)
adb -e emu avd coldboot
```

### iOS

```bash
# Uninstall app from simulator
xcrun simctl uninstall booted com.example.constructionInspector

# Erase simulator to factory state (if needed)
xcrun simctl erase booted
```

### Project Cleanup

```bash
# Remove lock files
rm -rf .dart_tool/package_config.json
rm -rf build/

# Clean and get dependencies
flutter clean && flutter pub get
```

---

## Test Configuration Flags

Pass these `--dart-define` flags to control test behavior.

| Flag | Purpose | Default |
|------|---------|---------|
| `PATROL_TEST=true` | Enables test mode (disables timers, in-app animations) | `false` |
| `MOCK_AUTH=true` | Uses mock authentication (no Supabase) | `false` |
| `MOCK_WEATHER=true` | Uses mock weather service (no OpenWeather API) | `false` |
| `MOCK_DATA=true` | Uses mock Supabase sync (local-only data) | `false` |
| `TEST_TIME=<ISO8601>` | Fixed timestamp for deterministic tests | Current time |

**Example**:
```bash
patrol test --dart-define=PATROL_TEST=true --dart-define=TEST_TIME=2026-01-15T10:00:00Z
```

---

## Running Tests

### Quick Start: Full Offline Mode

Run all tests with complete network isolation:

```bash
patrol test \
  --dart-define=PATROL_TEST=true \
  --dart-define=MOCK_AUTH=true \
  --dart-define=MOCK_WEATHER=true \
  --dart-define=MOCK_DATA=true
```

### Single Test File

```bash
patrol test \
  -t integration_test/patrol/e2e_tests/app_smoke_test.dart \
  --dart-define=PATROL_TEST=true
```

### Isolated Tests (Not in Bundle)

Tests in `integration_test/patrol/isolated/` must be run individually:

```bash
patrol test \
  -t integration_test/patrol/isolated/auth_flow_test.dart \
  --dart-define=PATROL_TEST=true \
  --dart-define=MOCK_AUTH=true
```

### With Video Recording (Debugging)

Enable video recording for failed tests:

```bash
patrol test \
  --dart-define=PATROL_TEST=true \
  --record
```

Videos saved to: `build/patrol/videos/`

---

## Troubleshooting

### Test Hangs or Times Out

**Symptoms**: Test runs indefinitely, never completes.

**Causes**:
- `pumpAndSettle()` waiting for animations that never finish
- Timers/periodic tasks still running (e.g., auto-save, clock updates)
- Network requests hanging

**Solutions**:
1. Verify `PATROL_TEST=true` flag is passed
2. Check app timers are disabled when `TestModeConfig.isTestMode == true`
3. Replace `pumpAndSettle()` with explicit waits:
   ```dart
   // Bad
   await $.pumpAndSettle();

   // Good
   await $.waitUntilVisible($(TestingKeys.myWidget));
   await $.pump();
   ```
4. Disable device animations (see Device Configuration)

---

### Permission Denied Errors

**Symptoms**: Tests fail with permission errors (camera, location, storage).

**Solutions**:
1. Grant permissions via ADB before tests (see Permissions section)
2. Use Patrol's native permission helpers:
   ```dart
   await $.native.grantPermissionWhenInUse();
   ```
3. Check app manifest declares required permissions

---

### Flaky Tests (Intermittent Failures)

**Symptoms**: Tests pass sometimes, fail other times.

**Causes**:
- Animations not fully disabled
- Network delays (live API calls)
- Race conditions (async operations)
- Device resource constraints

**Solutions**:
1. Verify all animation settings are OFF
2. Use mock services (`MOCK_AUTH`, `MOCK_WEATHER`, `MOCK_DATA`)
3. Add explicit waits instead of `pumpAndSettle`:
   ```dart
   await $.waitUntilVisible($(TestingKeys.myWidget), timeout: Duration(seconds: 5));
   ```
4. Use `TEST_TIME` for deterministic timestamps
5. Increase device heap size (Android): Edit `android/gradle.properties`:
   ```properties
   org.gradle.jvmargs=-Xmx12G
   ```

---

### Widget Not Found Errors

**Symptoms**: `PatrolFinder could not find widget with key Key('my_key')`.

**Causes**:
- Widget not rendered yet
- Key typo or mismatch
- Widget conditionally rendered (e.g., based on auth state)

**Solutions**:
1. Check key exists in `lib/shared/testing_keys/testing_keys.dart` (single source of truth)
2. Use `waitUntilVisible` with sufficient timeout:
   ```dart
   await $.waitUntilVisible($(TestingKeys.loginButton), timeout: Duration(seconds: 10));
   ```
3. Check app state prerequisites (e.g., logged in, data loaded)

---

### Database State Issues

**Symptoms**: Tests fail due to leftover data from previous runs.

**Solutions**:
1. Clear app data before each run:
   ```bash
   adb shell pm clear com.example.construction_inspector
   ```
2. Use `PatrolTestConfig.resetState()` in test setup:
   ```dart
   setUpAll(() async {
     await PatrolTestConfig.resetState();
   });
   ```
3. Use isolated test data (unique IDs per test)

---

### Memory Issues (Android)

**Symptoms**: Tests crash with `OutOfMemoryError` or device freezes.

**Solutions**:
1. Increase JVM heap in `android/gradle.properties`:
   ```properties
   org.gradle.jvmargs=-Xmx12G
   ```
2. Use Test Orchestrator to reset memory between tests (configured in `build.gradle.kts`)
3. Reduce max tests per batch: `--max-workers=1`
4. Close background apps on device
5. Use emulator with more RAM (4GB+)

---

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Setup Android Emulator
  uses: reactivecircus/android-emulator-runner@v2
  with:
    api-level: 34
    target: default
    arch: x86_64
    profile: pixel_6
    script: |
      adb shell settings put global window_animation_scale 0
      adb shell settings put global transition_animation_scale 0
      adb shell settings put global animator_duration_scale 0
      patrol test \
        --dart-define=PATROL_TEST=true \
        --dart-define=MOCK_AUTH=true \
        --dart-define=MOCK_WEATHER=true \
        --dart-define=MOCK_DATA=true
```

---

## Best Practices

1. **Always disable animations** before running tests
2. **Use mock services** for network-free testing
3. **Clean app data** between test runs for isolation
4. **Fix timestamps** with `TEST_TIME` for deterministic results
5. **Grant permissions** upfront to avoid prompts
6. **Keep device plugged in** during long test runs
7. **Use explicit waits** instead of `pumpAndSettle` when possible
8. **Record videos** when debugging flaky tests
9. **Run tests in isolation** first, then in bundle
10. **Monitor device resources** (CPU, memory) during tests

---

## References

- [Patrol Documentation](https://patrol.leancode.co/)
- Testing Keys: `lib/shared/testing_keys/testing_keys.dart`
- Test Helpers: `integration_test/patrol/helpers/patrol_test_helpers.dart`
- Test Config: `integration_test/patrol/test_config.dart`
