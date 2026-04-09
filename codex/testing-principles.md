# Testing Principles

User preference baseline for test work in this repo.

## Core Principles

- Test real behavior, not mock existence.
- Prefer integration with real production seams over complex mock stacks.
- Do not add test-only methods or lifecycle APIs to production classes.
- Mock only after understanding the real dependency chain and side effects.
- When mocking data, mirror the full real structure, not a partial guess.
- Treat tests as part of implementation, not follow-up.

## Practical Rules

- Before adding a mock, first ask whether the real implementation is simpler
  and more honest for the test.
- Do not assert on mock-only placeholders, fake test IDs, or mock presence.
- If a seam is hard to test, prefer extracting a real pure helper or explicit
  production owner over adding test-only escape hatches.
- Avoid extension-method-heavy mutation seams when a mockable class method or
  use case would make the production architecture clearer.
- If a test depends on repository/provider side effects, keep those side effects
  real or mock at a lower level instead of mocking away the behavior under test.

## Red Flags

- Assertion is only proving a mock rendered.
- Mock setup is larger than the behavior under test.
- Production code grows methods only used in tests.
- Mocking is added "to be safe" without understanding what the test needs.
- The mock omits fields the real data shape normally carries.
