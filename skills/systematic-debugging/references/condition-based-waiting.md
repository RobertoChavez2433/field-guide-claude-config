# Condition-Based Waiting

ADB/UIAutomator and Flutter test patterns for handling async operations.

## Iron Law

> **NEVER USE HARDCODED DELAYS. WAIT FOR CONDITIONS.**

`sleep 5` or `Future.delayed(Duration(seconds: 2))` is a code smell. Something observable should change.

## ADB Element Polling

Wait for UI elements via uiautomator dump.

```bash
# Poll for element by text
while ! adb shell uiautomator dump /dev/tty | grep -q "Save"; do
  sleep 1
done

# Poll for element by content-desc (Flutter Key)
while ! adb shell uiautomator dump /dev/tty | grep -q 'content-desc="save_button"'; do
  sleep 1
done
```

## Screenshot-Based Verification

Wait for visual state via Claude vision.

```bash
# Capture and verify screen state
adb exec-out screencap -p > screenshot.png
# Pass to Claude vision for verification
```

## Logcat-Based Waiting

Wait for Flutter log output.

```bash
# Wait for specific log message
adb logcat -s flutter | grep -m 1 "Sync completed"

# Wait for error absence (no new errors for 3s)
timeout 3 adb logcat -s flutter | grep -i error
```

## Widget Test Patterns

Standard Flutter test waiting (still relevant for unit/widget tests).

```dart
// BAD: Hardcoded delay
await Future.delayed(Duration(seconds: 1));

// GOOD: Pump until idle
await tester.pumpAndSettle();

// GOOD: Pump specific duration for animations
await tester.pump(Duration(milliseconds: 300));

// GOOD: Wait for specific widget to disappear
await tester.pumpAndSettle();
expect(find.byType(LoadingIndicator), findsNothing);
```

## Async Operation Patterns

Generalized async waiting in tests.

```dart
await tester.runAsync(() async {
  await provider.syncData();
});
await tester.pumpAndSettle();
```

## Common Waiting Scenarios

### Loading States

```bash
# ADB: Poll logcat for "loaded" message
adb logcat -s flutter | grep -m 1 "loaded"

# ADB: Screenshot check for loading spinner gone
adb exec-out screencap -p > screenshot.png
# Verify via Claude vision that spinner is no longer visible
```

### Navigation Transitions

```bash
# ADB: Poll uiautomator for new screen element
while ! adb shell uiautomator dump /dev/tty | grep -q 'content-desc="project_list_screen"'; do
  sleep 1
done
```

### Form Submission

```bash
# ADB: Poll for success element after tap
adb shell input tap 540 1800  # Tap submit button
while ! adb shell uiautomator dump /dev/tty | grep -q "Success"; do
  sleep 1
done
```

## Debugging Flaky Waits

When waits are flaky:

### 1. Check Element Exists in XML Dump

```bash
# Dump full UI tree and inspect
adb shell uiautomator dump /dev/tty | python -c "import sys; print(sys.stdin.read())" > ui_dump.xml
# Search for your element in the dump
```

### 2. Increase Poll Interval Temporarily

```bash
# Temporarily increase to see if it's just slow
while ! adb shell uiautomator dump /dev/tty | grep -q "target_element"; do
  sleep 2  # Was: 1
done
```

### 3. Add Intermediate Logcat Checkpoints

```bash
# Monitor logcat between steps to find where it stalls
adb logcat -s flutter -d | tail -20
# Check what the last Flutter log message was
```

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| `sleep N` in test scripts | Arbitrary, slow, flaky | Poll for condition |
| Very long ADB timeouts | Hides real problems | Find what's slow |
| Retry loops without limits | Infinite hang risk | Add max attempts |
| Ignoring logcat errors | Misses Flutter exceptions | Check logcat after every ADB action |

## When Delays Are Acceptable

Rarely, but:
- Animation timing tests (testing the animation itself)
- Debounce behavior tests (testing the debounce delay)
- Rate limit tests (testing rate limiting works)

Even then, prefer:
```dart
// Test the debounce duration specifically
await tester.pump(kDebounceDuration);
```
