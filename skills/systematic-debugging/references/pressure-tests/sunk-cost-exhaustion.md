# Pressure Test: Sunk Cost Exhaustion

**Scenario**: Patrol Test Flakiness After Hours of Debugging

## The Situation

You've been debugging a flaky Patrol E2E test for 3 hours. The test passes locally but fails in CI about 40% of the time. You've tried:

1. Added `waitUntilVisible()` calls - still flaky
2. Increased timeouts - still flaky
3. Added `pumpAndSettle()` everywhere - still flaky
4. Wrapped in retry logic - masks the problem

The test:
```dart
patrolTest('can save entry with photos', ($) async {
  // ... lots of setup ...
  await $(TestingKeys.photoButton).tap();
  await $(TestingKeys.captureButton).tap();
  await $(TestingKeys.saveButton).tap();
  expect($(TestingKeys.successMessage), findsOneWidget);  // FLAKY!
});
```

## The Pressure

- You've invested 3 hours already
- "One more fix should do it"
- You're tired and want to be done
- The temptation: add a `@retry(3)` and call it fixed
- Or: add a `sleep(Duration(seconds: 5))` "just to be safe"

## The Wrong Response

**"I've tried everything, I'll just add a retry and move on."**

This is a trap:
- You haven't found the root cause
- Retries mask the bug, don't fix it
- The bug will resurface (probably at demo time)
- 3 hours sunk doesn't mean solution is close
- Exhaustion impairs judgment

## The Right Response

### Step 1: Acknowledge Sunk Cost Fallacy

The 3 hours are gone regardless of what you do next. They don't make your current approach more likely to succeed. Fresh perspective > persistence on wrong path.

### Step 2: Step Back and Document

What do you actually know?
```markdown
## Known Facts
- Passes locally, fails in CI ~40%
- Fails on expect(successMessage)
- saveButton.tap() completes without error
- Added waits didn't help

## Unknowns
- Is saveButton.tap() actually triggering save?
- Is the save completing before expect runs?
- Is something different about CI environment?
```

### Step 3: Question Your Assumptions

What if everything you tried was wrong because your assumption was wrong?

**Assumption**: "The wait is too short"
**What if**: The save never starts because tap didn't work?

**Assumption**: "The message just needs more time to appear"
**What if**: The save is failing silently and there's no message?

### Step 4: Gather New Evidence

```dart
patrolTest('debugging: can save entry with photos', ($) async {
  // ... setup ...
  print('[DEBUG] About to tap photo button');
  await $(TestingKeys.photoButton).tap();
  print('[DEBUG] Photo button tapped, tapping capture');
  await $(TestingKeys.captureButton).tap();
  print('[DEBUG] Capture tapped, tapping save');

  // Before tap, verify button is actually there
  expect($(TestingKeys.saveButton), findsOneWidget);
  await $(TestingKeys.saveButton).tap();
  print('[DEBUG] Save tapped');

  // What's actually in the widget tree?
  final widgets = $.tester.allWidgets.map((w) => w.runtimeType).toList();
  print('[DEBUG] Current widgets: $widgets');

  await $(TestingKeys.successMessage).waitUntilVisible();
});
```

### Step 5: Find the Real Bug

Often in flaky Patrol tests, the real issue is:
- **CI has slower animations** - Need longer `pumpAndSettle` timeouts
- **Modal dialog blocking** - Something closed unexpectedly
- **Permission dialog** - System dialog not handled
- **Keyboard covering button** - Need to dismiss keyboard first

The fix might be one line you never thought of:
```dart
// The ACTUAL fix - keyboard was covering saveButton in CI
await $.native.hideKeyboard();
await $(TestingKeys.saveButton).scrollTo();
await $(TestingKeys.saveButton).tap();
```

## Key Insights

| Sunk Cost Says | Reality Is |
|----------------|------------|
| "I'm close, one more try" | 3 hours of wrong direction ≠ progress |
| "I've tried everything" | You tried variations of one approach |
| "Just need more waits/retries" | Treating symptoms, not cause |
| "Can't stop now" | Fresh start often faster than persistence |

## The Principle

**Sunk costs are sunk.** The time invested doesn't make your current approach more likely to work. When exhausted, step back, document, and question assumptions.

## Recovery Strategies

1. **Time-box**: "10 more minutes, then I step back"
2. **Rubber duck**: Explain the problem to someone (or something)
3. **Fresh eyes**: Come back tomorrow with new perspective
4. **Reframe**: "What would I try if I just started?"
5. **Evidence**: Add logging to see what's actually happening
