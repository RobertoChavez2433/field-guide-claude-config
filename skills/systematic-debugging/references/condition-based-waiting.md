# Condition-Based Waiting

Flutter/Patrol-adapted patterns for handling async operations in tests.

## Iron Law

> **NEVER USE HARDCODED DELAYS. WAIT FOR CONDITIONS.**

`Future.delayed(Duration(seconds: 2))` is a code smell. Something observable should change.

## Flutter Test Patterns

### Widget Tests

```dart
// BAD: Hardcoded delay
await Future.delayed(Duration(seconds: 1));

// GOOD: Pump until idle
await tester.pumpAndSettle();

// GOOD: Pump specific duration for animations
await tester.pump(Duration(milliseconds: 300));

// GOOD: Wait for specific widget
await tester.pumpAndSettle();
expect(find.byType(LoadingIndicator), findsNothing);
```

### Async Operations

```dart
// BAD: Arbitrary delay
await Future.delayed(Duration(seconds: 2));
expect(find.text('Data loaded'), findsOneWidget);

// GOOD: Wait for condition
await tester.pumpAndSettle(timeout: Duration(seconds: 5));
expect(find.text('Data loaded'), findsOneWidget);

// GOOD: Pump until widget appears
while (find.text('Data loaded').evaluate().isEmpty) {
  await tester.pump(Duration(milliseconds: 100));
}
```

## Patrol Test Patterns

### Visibility Waiting

```dart
// BAD: Delay before interaction
await Future.delayed(Duration(seconds: 1));
await $(TestingKeys.button).tap();

// GOOD: Wait for visibility
await $(TestingKeys.button).waitUntilVisible();
await $(TestingKeys.button).tap();

// GOOD: Wait with timeout
await $(TestingKeys.button).waitUntilVisible(timeout: Duration(seconds: 10));
```

### Gone Waiting

```dart
// BAD: Delay for dialog to close
await $(TestingKeys.confirmButton).tap();
await Future.delayed(Duration(seconds: 1));

// GOOD: Wait for dialog to disappear
await $(TestingKeys.confirmButton).tap();
await $(TestingKeys.dialog).waitUntilGone();
```

### Scroll Then Tap

```dart
// BAD: Tap something that might be off-screen
await $(TestingKeys.itemAtBottom).tap(); // May fail!

// GOOD: Scroll into view first
await $(TestingKeys.itemAtBottom).scrollTo();
await $(TestingKeys.itemAtBottom).tap();
```

## Common Waiting Scenarios

### Loading States

```dart
// Wait for loading to complete
Future<void> waitForLoading(PatrolTester $) async {
  // Wait for loading indicator to appear
  await $(TestingKeys.loadingIndicator).waitUntilVisible(
    timeout: Duration(seconds: 2),
  );

  // Wait for loading indicator to disappear
  await $(TestingKeys.loadingIndicator).waitUntilGone(
    timeout: Duration(seconds: 30),
  );
}
```

### Navigation Transitions

```dart
// Wait for navigation to complete
Future<void> waitForScreen(PatrolTester $, Key screenKey) async {
  await $(screenKey).waitUntilVisible(timeout: Duration(seconds: 5));
}
```

### Form Submission

```dart
// Wait for form to submit and navigate
Future<void> submitAndWait(PatrolTester $) async {
  await $(TestingKeys.submitButton).tap();

  // Wait for current screen to be replaced
  await $(TestingKeys.currentForm).waitUntilGone();

  // Wait for success screen
  await $(TestingKeys.successScreen).waitUntilVisible();
}
```

## Debugging Flaky Waits

When tests are flaky:

### 1. Check What You're Waiting For

```dart
// Is the key correct?
debugPrint('Looking for: ${TestingKeys.myWidget}');

// Is the widget actually there?
final finder = $(TestingKeys.myWidget);
debugPrint('Found: ${finder.evaluate().length} widgets');
```

### 2. Increase Timeout (Temporarily)

```dart
// Temporarily increase to see if it's just slow
await $(TestingKeys.button).waitUntilVisible(
  timeout: Duration(seconds: 30), // Was: 5
);
```

### 3. Add Intermediate Waits

```dart
// Break into steps to find where it fails
await $(TestingKeys.trigger).tap();
debugPrint('Tapped trigger');

await $(TestingKeys.loading).waitUntilVisible();
debugPrint('Loading appeared');

await $(TestingKeys.loading).waitUntilGone();
debugPrint('Loading gone');

await $(TestingKeys.result).waitUntilVisible();
debugPrint('Result appeared');
```

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| `Future.delayed(Duration(seconds: N))` | Arbitrary, slow, flaky | Wait for condition |
| Very long timeouts | Hides real problems | Find what's slow |
| `sleep()` | Blocks everything | Use async waits |
| Retry loops without limits | Infinite hang risk | Add max attempts |
| Ignoring wait failures | Tests pass falsely | Let waits throw |

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
