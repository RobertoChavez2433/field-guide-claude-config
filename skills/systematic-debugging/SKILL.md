---
name: systematic-debugging
description: Root cause analysis framework that prevents guess-and-check debugging
context: fork
agent: qa-testing-agent
user-invocable: true
---

# Systematic Debugging Skill

**Purpose**: Root cause analysis framework that prevents guess-and-check debugging.

## Iron Law

> **NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST**

Every fix must be preceded by understanding WHY the bug exists. Guessing wastes time and creates new bugs.

> **Real-World Impact**: Systematic debugging takes 15–30 minutes. Thrashing without process takes 2–3 hours and often leaves the root cause unfound.

## Before Starting: Use Existing Results

**Do NOT run the full test suite on skill startup.** The user typically already has recent test/scorecard results before invoking this skill. Ask what results they have or review context before launching any test runs. Only run tests when the investigation requires it (e.g., to reproduce a specific failure, validate a hypothesis, or check regressions after a fix).

## Before Starting: Check Per-Feature Defects

Before debugging ANY issue:
1. Read `.claude/defects/_defects-{feature}.md` for the relevant feature
2. Search for matching pattern (ASYNC, E2E, FLUTTER, DATA, CONFIG)
3. Apply known prevention strategies if pattern matches

@.claude/skills/systematic-debugging/references/defects-integration.md

## Four-Phase Framework

### Phase 1: Root Cause Investigation

**Goal**: Understand the bug before touching code.

1. **Read the error** - Full message, stack trace, context
2. **Reproduce** - Exact steps that trigger the bug
3. **Isolate** - Minimal reproduction case
4. **Gather Evidence in Multi-Component Systems** - Before proposing a fix, instrument each component boundary. Add logging/echo at the entry and exit of each layer (e.g., Stage 4A → Stage 4B → Stage 4D). Confirm which layer produces the unexpected output before touching any code.
5. **Trace Data Flow** - Follow the data path end-to-end. A bug that appears in Stage 4E may originate in Stage 3. See root-cause-tracing.md for the full checklist.
6. **Timeline** - When did this last work? What changed?

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
5. **When You Don't Know** — If you cannot explain why the bug occurs, say "I don't understand X yet." Do NOT pretend to understand. Do NOT propose a fix for something you cannot explain. Return to Phase 1 and gather more evidence.

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
5. **If fix doesn't work (< 3 tries)** — Revert, return to Phase 1. Your hypothesis was wrong. Form a new one.
6. **If fix doesn't work (≥ 3 tries)** — **STOP**. Do not try another fix. The architecture or your understanding of the system is the problem. State explicitly: "I have tried 3 hypotheses and none resolved the root cause. I need to re-examine the system." Then go back to Phase 1 with fresh eyes.

@.claude/skills/systematic-debugging/references/condition-based-waiting.md

## Red Flags — STOP and Follow Process

These thought patterns mean you're off-track. Stop immediately and return to Phase 1:

- "Let me just try one more thing…"
- "I think I see the problem" (before you've confirmed with evidence)
- "This is probably caused by…" (without looking at data)
- "The fix didn't work but the next one will"
- "I'll add a workaround and come back to the root cause"
- Starting to modify code before you can explain WHY the bug exists

## Your Human Partner's Signals

When the user says any of these, they are telling you to stop guessing:

- **"Stop guessing"** — Return to Phase 1 immediately. State what evidence you have and what is still unknown.
- **"Ultrathink this"** — Take extended time to reason through the full system before touching any code.
- **"Walk me through it"** — Explain your current understanding of the data flow before proposing a fix.
- **"You've been on this too long"** — Summarize your hypotheses, state what you've ruled out, and ask for guidance.

## Stop Conditions

**STOP and reassess if**:
- 3+ failed fix attempts — This is likely an architectural issue
- Fix requires changing 5+ files — Scope is too broad
- You can't explain the root cause — Go back to Phase 1
- The "fix" just suppresses symptoms — You haven't found root cause

> **When process reveals no root cause**: 95% of the time, "no root cause found" means the investigation was incomplete — not that the root cause doesn't exist. Expand Phase 1.

## After Fixing: Update Per-Feature Defects

If you discovered a new pattern:
1. Identify category: ASYNC, E2E, FLUTTER, DATA, CONFIG
2. Write pattern, prevention, and reference
3. Add to `.claude/defects/_defects-{feature}.md` for the relevant feature

## Pressure Test Scenarios

> Pressure test scenarios available in `references/pressure-tests/` — invoke on demand if needed.

## Rationalization Prevention

| If You Think... | Stop And... |
|-----------------|-------------|
| "Let me just try this quick fix" | Form a hypothesis first |
| "I'll add a retry and see if it helps" | Find the root cause |
| "The tests are flaky, I'll skip them" | Find why they're flaky |
| "I've been on this too long, just ship it" | Take a break, come back fresh |
| "It works on my machine" | Reproduce in failing environment |
| "The pattern is too long to trace fully" | That's exactly when you must trace it |
| "One more fix and it'll work" | Count your attempts — if ≥ 3, STOP |
| "I see the problem" | Verify with evidence before touching code |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|-----------------|
| 1: Root Cause Investigation | Read error, reproduce, isolate, instrument boundaries, trace data flow | Can explain WHY the bug exists |
| 2: Pattern Analysis | Find working example, compare, validate data | Specific difference identified |
| 3: Hypothesis Testing | Form ONE hypothesis, test minimally, evaluate | Hypothesis confirmed or denied |
| 4: Implementation | Write failing test, targeted fix, verify, regressions | Test passes, no regressions |

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
