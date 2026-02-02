# Systematic Debugging Skill

**Purpose**: Root cause analysis framework that prevents guess-and-check debugging.

## Iron Law

> **NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST**

Every fix must be preceded by understanding WHY the bug exists. Guessing wastes time and creates new bugs.

## Before Starting: Check _defects.md

Before debugging ANY issue:
1. Read `.claude/autoload/_defects.md`
2. Search for matching pattern (ASYNC, E2E, FLUTTER, DATA, CONFIG)
3. Apply known prevention strategies if pattern matches

@.claude/skills/systematic-debugging/references/defects-integration.md

## Four-Phase Framework

### Phase 1: Root Cause Investigation

**Goal**: Understand the bug before touching code.

1. **Read the error** - Full message, stack trace, context
2. **Reproduce** - Exact steps that trigger the bug
3. **Isolate** - Minimal reproduction case
4. **Timeline** - When did this last work? What changed?

**Key Questions**:
- What is the EXACT error message?
- What are the EXACT steps to reproduce?
- When did this start happening?
- What changed recently (commits, dependencies, config)?

@.claude/skills/systematic-debugging/references/root-cause-tracing.md

### Phase 2: Pattern Analysis

**Goal**: Find similar working code to understand the gap.

1. **Find working example** - Similar code that works correctly
2. **Compare differences** - What's different about the failing case?
3. **Check timing** - Is this a race condition or async issue?
4. **Validate assumptions** - Is the data actually what you think it is?

**Analysis Checklist**:
- [ ] Found working code that does similar thing
- [ ] Identified specific difference
- [ ] Checked for async/timing issues
- [ ] Validated input data is correct

@.claude/skills/systematic-debugging/references/defense-in-depth.md

### Phase 3: Hypothesis Testing

**Goal**: Test ONE hypothesis at a time.

1. **Form hypothesis** - "The bug occurs because X"
2. **Design test** - How to confirm/deny this hypothesis
3. **Test minimally** - Smallest change to test hypothesis
4. **Evaluate** - Did it confirm or deny?

**Rules**:
- ONE hypothesis per test
- Revert failed changes before trying next hypothesis
- Log your hypotheses and results

### Phase 4: Implementation

**Goal**: Fix with confidence.

1. **Write failing test** - Captures the bug
2. **Apply targeted fix** - Minimal change to fix root cause
3. **Verify test passes** - Bug is actually fixed
4. **Check regressions** - Run related tests

@.claude/skills/systematic-debugging/references/condition-based-waiting.md

## Stop Conditions

**STOP and reassess if**:
- 3+ failed fix attempts - This is likely an architectural issue
- Fix requires changing 5+ files - Scope is too broad
- You can't explain the root cause - Go back to Phase 1
- The "fix" just suppresses symptoms - You haven't found root cause

## After Fixing: Update _defects.md

If you discovered a new pattern:
1. Identify category: ASYNC, E2E, FLUTTER, DATA, CONFIG
2. Write pattern, prevention, and reference
3. Add to `.claude/autoload/_defects.md`

## Pressure Test Scenarios

These scenarios test your ability to resist common debugging anti-patterns:
@.claude/skills/systematic-debugging/references/pressure-tests/production-emergency.md
@.claude/skills/systematic-debugging/references/pressure-tests/sunk-cost-exhaustion.md
@.claude/skills/systematic-debugging/references/pressure-tests/authority-pressure.md

## Rationalization Prevention

| If You Think... | Stop And... |
|-----------------|-------------|
| "Let me just try this quick fix" | Form a hypothesis first |
| "I'll add a retry and see if it helps" | Find the root cause |
| "The tests are flaky, I'll skip them" | Find why they're flaky |
| "I've been on this too long, just ship it" | Take a break, come back fresh |
| "It works on my machine" | Reproduce in failing environment |

## Flutter-Specific Debug Commands

```bash
# Full analysis
flutter analyze

# Verbose test output
flutter test --verbose

# Specific test with logging
flutter test test/path/file.dart -r expanded

# Patrol verbose mode
patrol test --verbose

# Check for async issues
flutter test --enable-vmservice
```

## Anti-Patterns

| Don't | Do Instead |
|-------|-----------|
| Add random delays | Find what you're waiting for |
| Catch and ignore errors | Handle errors explicitly |
| "Works now, don't know why" | Understand the fix |
| Skip reproduction | Reliable repro is essential |
| Change multiple things | One change at a time |
