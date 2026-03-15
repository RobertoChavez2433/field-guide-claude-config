# Plan Review: Dynamic Fringe Removal

**Plan**: `.claude/plans/2026-03-14-dynamic-fringe-removal.md`
**Spec**: `.claude/specs/2026-03-14-dynamic-fringe-removal-spec.md`
**Date**: 2026-03-14

## Code Review Agent: APPROVE with fixes

### CRITICAL
1. **Metric naming mismatch**: Plan uses `avgFringeWidth`/`maxFringeWidth`, spec requires `avgFringeWidthH`/`avgFringeWidthV` split by orientation. Must fix in `_GridRemovalResult`, metric dict, and contract tests.
2. **Scan-start double-read**: `step=0` re-reads the boundary pixel already checked by `startVal`. Functionally correct (pixel counted once) but `step` should start at 1 since the boundary pixel is already validated by the start condition check.

### HIGH
3. **Missing tests**: Plan has 2 fringe tests. Spec requires 8 including HIGH-priority intersection test, bounds clamping test. Must add at minimum: intersection test, bounds test.
4. **Line number drift**: Phases 3+ reference line numbers that shift after Phase 2 insertions. Add note to implementer.

### MEDIUM
5. **DRY**: `median()` function duplicated — could import from shared utils if available
6. **KISS**: H/V drawing loops rewritten identically — could insert only the `countNonZero` call between existing loops to minimize diff
7. **`notTextProtection` removal** should be explicit in the replacement block comment

### LOW
8. Default constructor params vs required — acceptable for phased implementation
9. Add `greaterThan(0)` assertions for H/V mask pixels in fringe test

## Security Agent: APPROVE

All 5 security guards preserved. Bounds checking safe. Resource exhaustion bounded (6K reads max). No new Mat allocations. No integer overflow risk (max thickness = 56). One low note: add defensive `.clamp()` on line center coordinates.

## Actions Taken

- CRITICAL #1: Will fix during implementation — split fringe metrics by H/V orientation
- CRITICAL #2: Will fix during implementation — start scan loop at step=1
- HIGH #3: Will fix during implementation — add intersection + bounds tests
- HIGH #4: Noted — implementer should use code patterns not line numbers
- MEDIUM/LOW: Noted in plan for implementer awareness
