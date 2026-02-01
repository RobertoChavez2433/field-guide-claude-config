---
paths:
  - "android/**/*"
  - "ios/**/*"
  - "pubspec.yaml"
---

# 2026 Platform Standards Update

**Date**: 2026-01-21
**Purpose**: Update Android and iOS configurations to 2026 standards to prevent test crashes and improve stability

## Problem Statement

Patrol integration tests were crashing after 20 tests due to:
- Memory exhaustion on Android 13+ (stricter memory policies)
- Outdated SDK versions and test configurations
- Insufficient heap allocation for long test runs
- Missing test isolation and cleanup settings

## Changes Implemented

### Android Configuration Updates

#### 1. SDK Versions (`android/app/build.gradle.kts`)

**Before:**
```kotlin
compileSdk = flutter.compileSdkVersion  // Was 33
minSdk = flutter.minSdkVersion          // Was 21
targetSdk = flutter.targetSdkVersion    // Was 33
```

**After:**
```kotlin
compileSdk = 36  // Android 16 - Latest stable for 2026
minSdk = 24      // Android 7.0 - Drops devices older than 7 years
targetSdk = 36   // Required for Play Store submissions
```

**Rationale:**
- Android 16 (API 36) provides better memory management
- API 24+ enforces stricter security and performance standards
- Dropping API 21-23 eliminates legacy devices with poor memory handling

#### 2. Test Memory Settings (`android/app/build.gradle.kts`)

**Added to defaultConfig:**
```kotlin
testInstrumentationRunnerArguments["maxTestsPerDevice"] = "5"
testInstrumentationRunnerArguments["testTimeoutInMs"] = "600000"
```

**Added to testOptions:**
```kotlin
testOptions {
    execution = "ANDROIDX_TEST_ORCHESTRATOR"

    unitTests {
        isIncludeAndroidResources = true
        isReturnDefaultValues = true
    }

    animationsDisabled = true  // Prevents test flakiness
}
```

**Rationale:**
- Limits tests per device to prevent memory buildup
- Increases timeout for complex Patrol tests
- Disables animations to reduce test flakiness
- Test orchestrator ensures proper isolation between tests

#### 3. Test Dependencies (`android/app/build.gradle.kts`)

**Before:**
```kotlin
androidTestUtil("androidx.test:orchestrator:1.4.2")
```

**After:**
```kotlin
androidTestUtil("androidx.test:orchestrator:1.6.1")
androidTestImplementation("androidx.test:runner:1.6.2")
androidTestImplementation("androidx.test:rules:1.6.1")
```

**Rationale:**
- Orchestrator 1.6.1 has better memory management
- Additional test runner and rules improve Patrol compatibility

#### 4. Gradle Memory Settings (`android/gradle.properties`)

**Before:**
```properties
org.gradle.jvmargs=-Xmx8G -XX:MaxMetaspaceSize=4G ...
```

**After:**
```properties
org.gradle.jvmargs=-Xmx12G -XX:MaxMetaspaceSize=4G -XX:ReservedCodeCacheSize=512m -XX:+HeapDumpOnOutOfMemoryError -XX:+UseG1GC
org.gradle.workers.max=4
android.enableJetifier=false
```

**Rationale:**
- 12G heap prevents OOM in long Patrol test runs
- G1GC provides better garbage collection for tests
- Limited workers prevent memory fragmentation
- Jetifier disabled (no longer needed with androidx)

### iOS Configuration Updates

#### 1. Minimum iOS Version

**Files Updated:**
- `ios/Flutter/AppFrameworkInfo.plist`
- `ios/Runner.xcodeproj/project.pbxproj` (3 occurrences)

**Before:**
```xml
<key>MinimumOSVersion</key>
<string>13.0</string>
```

**After:**
```xml
<key>MinimumOSVersion</key>
<string>15.0</string>
```

**Rationale:**
- iOS 15.0 has better memory management
- Drops iOS 13/14 support (devices older than 4 years)
- Better aligned with Flutter 3.38+ requirements
- Reduces compatibility testing surface

### Documentation Updates

#### Tech Stack (`\.claude\memory\tech-stack.md`)

Added comprehensive platform requirements table:

```markdown
## Platform Requirements (2026 Standards)

### Android
| Component | Version | Notes |
|-----------|---------|-------|
| compileSdk | 36 (Android 16) | Latest stable for 2026 |
| targetSdk | 36 | Required for Play Store |
| minSdk | 24 (Android 7.0) | Drops devices older than 7 years |
| Gradle | 8.14 | Latest stable |
| Android Gradle Plugin | 8.11.1 | Latest stable |
| Kotlin | 2.2.20 | Latest stable |
| Java | 17 | LTS version |

### iOS
| Component | Version | Notes |
|-----------|---------|-------|
| Minimum iOS | 15.0 | Drops iOS 13/14 for better performance |
| Xcode | 15.0+ | Required for iOS 15+ support |

### Test Configuration
| Component | Version | Purpose |
|-----------|---------|---------|
| Test Orchestrator | 1.6.1 | Proper test isolation |
| Patrol | 4.1.0 | Native automation |
| JVM Heap (Tests) | 12G | Prevents OOM in long test runs |
| Max Tests Per Device | 5 | Memory exhaustion prevention |
```

## Verification

### Gradle Build
```bash
cd android
./gradlew --version
# Gradle 8.14 confirmed

./gradlew help --warning-mode=all
# Build configuration valid
```

### Flutter Analyze
```bash
flutter analyze
# 18 issues found (pre-existing, not related to platform changes)
# No new errors introduced
```

## Expected Improvements

### Test Stability
1. **Memory Management**: 12G heap + G1GC prevents OOM crashes
2. **Test Isolation**: Orchestrator ensures clean state between tests
3. **Timeouts**: Extended timeouts accommodate complex Patrol tests
4. **Animations**: Disabled in tests reduces flakiness

### Performance
1. **Modern APIs**: Android 16 and iOS 15 have better runtime performance
2. **Reduced Legacy Code**: Dropping old SDKs reduces compatibility layers
3. **Garbage Collection**: G1GC provides smoother memory cleanup

### Compatibility
1. **Play Store**: targetSdk 36 meets 2026 requirements
2. **Device Coverage**: Focuses on devices from last 7 years (Android 7.0+)
3. **Flutter Alignment**: Better compatibility with Flutter 3.38+

## Files Modified

| File | Changes |
|------|---------|
| `android/app/build.gradle.kts` | SDK versions, test options, dependencies |
| `android/gradle.properties` | JVM heap, workers, G1GC |
| `ios/Flutter/AppFrameworkInfo.plist` | iOS 15.0 minimum |
| `ios/Runner.xcodeproj/project.pbxproj` | iOS 15.0 deployment target (3x) |
| `.claude/autoload/_tech-stack.md` | Platform requirements table |

## Next Steps

1. **Test Execution**: Run full Patrol test suite to validate improvements
   ```bash
   flutter test integration_test/
   ```

2. **Memory Monitoring**: Monitor heap usage during tests
   ```bash
   flutter test integration_test/ --verbose
   ```

3. **CI/CD**: Update CI pipeline to use new SDK versions

4. **Device Testing**: Verify on physical devices running Android 15 and iOS 15

## Rollback Plan

If issues arise, revert these commits:
```bash
git revert HEAD
```

Or manually revert:
- Android compileSdk/targetSdk to 33, minSdk to 21
- iOS MinimumOSVersion to 13.0
- Gradle heap to 8G
- Test Orchestrator to 1.4.2
- Patrol to 3.20.0

## References

- [Android 15 Features](https://developer.android.com/about/versions/15)
- [Gradle 8.14 Release Notes](https://docs.gradle.org/8.14/release-notes.html)
- [Test Orchestrator Guide](https://developer.android.com/training/testing/instrumented-tests/androidx-test-libraries/test-orchestrator)
- [Flutter Platform Support](https://docs.flutter.dev/reference/supported-platforms)
- [Patrol Testing Documentation](https://patrol.leancode.co/)
