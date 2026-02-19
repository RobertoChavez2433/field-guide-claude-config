# Plan: Remove Drift Correction, Scan Directly From edgePos

**Date**: 2026-02-19 | **Session**: 380
**Status**: Ready for implementation (TDD red-green)

## Problem Statement

`_computeLineInset` in `text_recognizer_v2.dart` scans from a drift-corrected edge position but returns the inset relative to that corrected position. The caller applies the inset to the ORIGINAL `edgePos`, losing the drift delta (1-3px). This causes 35 pipe `|` artifacts across 17 items (31 field-level occurrences).

### Root Cause (Confirmed by Full-Document Analysis)

1. **Grid line positions are accurate to <1px** (floor/ceil rounding only)
2. **The drift correction layer (`_correctEdgePosForLineDrift`) solves a <1px problem** while introducing 1-3px false corrections when nearby content enters the scan window
3. **`baselineInset = ceil(w/2) + 1` is universally insufficient** — fails for 41 of 42 vertical lines across all 6 pages. Shortfall ranges from 0.1px (4px lines) to 1.5px (6px lines)
4. **The scan itself (walking pixel-by-pixel until 2 consecutive white pixels) already works correctly** when started from `edgePos` — it naturally handles sub-pixel offset, line width, and AA fringe

### Evidence

- 35 pipe `|` elements across 17 items, concentrated on pages 1 and 4 (5-6px lines)
- ALL pipes at START of values, 100% aligned with vertical grid lines
- Page 0 (4px lines) has zero pipes; pages 1-4 (5-6px lines) have them
- Structural drift (edgePos vs true center) is always <1px — just floor rounding
- The scan walks 4-8px from edgePos and correctly finds white within `plannedDepth`

## Fix: Remove Drift Correction, Scan Directly From edgePos

### What Changes

1. **Remove `_correctEdgePosForLineDrift`** — no longer needed (grid positions are accurate)
2. **Scan directly from `edgePos`** in `_computeLineInset` — the scan walks through whatever's there (line body + AA) and stops at 2 consecutive whites
3. **Update `baselineInset` formula** — increase from `ceil(w/2) + 1` to `ceil(w/2) + ceil(w*0.25) + 1` to properly account for line half-width + AA margin
4. **Keep `plannedDepth` as scan cap** — already proportional to line width (`w + ceil(w*0.25) + 3`)
5. **Keep `_capInsetPairForInterior`** — existing safety net prevents cell collapse

### What Stays The Same

- `_scanRefinedInsetAtProbe` — scan logic, 2-consecutive-white termination, threshold 230
- `_capInsetPairForInterior` — interior preservation guard
- Probe-based p75 aggregation — robust multi-probe measurement
- Legacy `_scanWhitespaceInset` fallback — used when width arrays unavailable
- `CropUpscaler` — upscaling after crop is unaffected

### Files Modified

| File | Change |
|------|--------|
| `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart` | Remove drift correction, update scan origin, update baselineInset formula |
| `test/features/pdf/extraction/stages/whitespace_inset_test.dart` | Add drift sweep tests, width coverage, caller-frame verification |
| `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart` | Replace `expect(true, isTrue)` with hard assertions |
| `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart` | Add pipe artifact fixture scan |
| All Springfield fixture JSON files | Regenerated after fix |

## Implementation Steps (TDD Red-Green)

### Phase 1: Write Failing Tests (RED)

**Step 1.1: Drift Sweep Unit Tests** (`whitespace_inset_test.dart`)

Add synthetic image tests for `_computeLineInset` (via `testComputeLineInset`):

| Test | Setup | Expected Behavior |
|------|-------|-------------------|
| 0px drift, w=5 | Band centered at edgePos | inset clears line body + AA |
| +1px drift, w=5 | Band shifted +1 from edgePos | inset still clears (scan walks through) |
| +2px drift, w=5 | Band shifted +2 from edgePos | inset still clears |
| +3px drift, w=5 | Band shifted +3 from edgePos | inset still clears |
| -1px drift, w=5 | Band shifted -1 from edgePos | inset still clears |
| -2px drift, w=5 | Band shifted -2 from edgePos | inset still clears |
| -3px drift, w=5 | Band shifted -3 from edgePos | inset still clears |
| w=4, centered | 4px band | inset >= 3 (ceil(4/2)+1) |
| w=6, centered | 6px band | inset >= 4 (ceil(6/2)+1) |
| w=6, +0.5px drift | 6px band shifted 0.5px | inset clears entire line |

**Key assertion pattern**: For each test, verify that `edgePos + returned_inset` lands PAST the last dark pixel of the test band. This is the **caller-frame verification** — it tests the contract the caller depends on.

**Step 1.2: Scorecard Hard Assertions** (`stage_trace_diagnostic_test.dart`)

Replace `expect(true, isTrue)` at line 3861 with:
```dart
expect(parsedItemCount, greaterThanOrEqualTo(131));
expect(withAmountCount, greaterThanOrEqualTo(124)); // current baseline, raise after fix
expect(bugCount, equals(0));
```

These will PASS on current code (they're documenting the baseline). After the fix, raise `withAmountCount` threshold to 131.

**Step 1.3: Pipe Artifact Fixture Scan** (`cell_boundary_verification_test.dart`)

Add a test that reads `springfield_cell_grid.json` and asserts zero cell values starting with `|`. This will FAIL on current fixtures (35 pipes exist) — proving the test catches the bug.

**Step 1.4: Ground Truth Regression Test** (new or extend existing)

Compare all 131 parsed items against `springfield_ground_truth_items.json`. Record every field match/mismatch. Assert:
- Zero regressions (fields correct before must remain correct after)
- Improvement count >= 0 (pipe removal should increase correctness)

This will PASS on current code (establishes the baseline). After the fix, verify improvements.

### Phase 2: Apply the Fix (GREEN)

**Step 2.1: Modify `_computeLineInset`** (`text_recognizer_v2.dart:708-756`)

Before:
```dart
final correctedEdgePos = _correctEdgePosForLineDrift(...);
// scan from correctedEdgePos
final refinedInset = _scanRefinedInsetAtProbe(edgePos: correctedEdgePos, ...);
// return inset relative to correctedEdgePos (BUG: caller applies to original edgePos)
```

After:
```dart
// Scan directly from edgePos — grid positions are accurate (<1px error)
// The scan naturally handles sub-pixel offset by walking through the line body + AA
final refinedInset = _scanRefinedInsetAtProbe(edgePos: edgePos, ...);
// Returned inset IS in caller's frame (no coordinate mismatch)
```

**Step 2.2: Update `baselineInset` formula**

Before: `baselineInset = ceil(w/2) + 1`
After: `baselineInset = ceil(w/2) + ceil(w * 0.25) + 1`

This ensures the floor covers half-width + AA margin. For w=6: old=4, new=5. For w=5: old=4, new=5. For w=4: old=3, new=4.

**Step 2.3: Remove `_correctEdgePosForLineDrift` method**

Delete the method entirely (lines ~790-845). It's no longer called.

**Step 2.4: Update `plannedDepth`**

Remove `driftPx` from the depth calculation since drift correction is gone:
Before: `plannedDepth = w + aa + driftPx` (where driftPx=3)
After: `plannedDepth = w + aa + 2` (keep small margin for sub-pixel rounding, but no drift window needed)

Or keep a small safety margin. The scan cap just prevents runaway scanning — it doesn't need to be tight.

### Phase 3: Regenerate Fixtures & Verify (VERIFY)

**Step 3.1: Regenerate all Springfield fixtures**
```
pwsh -Command "flutter test integration_test/generate_golden_fixtures_test.dart -d windows --dart-define=SPRINGFIELD_PDF=..."
```

**Step 3.2: Run all extraction tests**
```
pwsh -Command "flutter test test/features/pdf/extraction/"
```

**Step 3.3: Verify pipe count = 0**
The pipe artifact fixture scan test (Step 1.3) should now PASS.

**Step 3.4: Raise scorecard thresholds**
Update `withAmountCount` assertion to 131 (or whatever the new actual count is).

**Step 3.5: Run stage trace diagnostics**
```
pwsh -Command "flutter test test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart"
```

**Step 3.6: Run ground truth regression test**
Verify zero regressions, count improvements.

### Phase 4: Update Existing Tests

**Step 4.1: Update whitespace_inset_test.dart**
- Remove/update the old drift test at line 122 (it tested `_correctEdgePosForLineDrift` behavior)
- Update Springfield snapshot assertions if inset values changed
- Verify all new drift sweep tests pass

**Step 4.2: Update mock_stages.dart if needed**
If any test mocks reference `_correctEdgePosForLineDrift`, remove those references.

**Step 4.3: Update stage contract tests**
If Stage 2b contracts reference drift-related behavior, update expectations.

## Verification Criteria

| Criterion | Target | How to Verify |
|-----------|--------|---------------|
| Pipe artifacts | 0 (from 35) | Fixture scan test |
| bid_amount completeness | 131/131 (from 124/131) | Scorecard assertion |
| Parsed items | 131/131 | Scorecard assertion |
| Ground truth regressions | 0 | Regression test |
| Extraction test suite | All pass | `flutter test test/features/pdf/extraction/` |
| Stage trace diagnostics | 55 OK / 0 LOW / 0 BUG (target) | Diagnostic test |
| Drift sweep tests | All pass | Unit tests |

## Agent Assignments

| Phase | Agent | Task |
|-------|-------|------|
| 1.1-1.4 | frontend-flutter-specialist-agent | Write failing tests |
| 2.1-2.4 | frontend-flutter-specialist-agent | Apply code fix |
| 3.1-3.6 | qa-testing-agent | Regenerate, run tests, verify |
| 4.1-4.3 | code-review-agent | Review changes, verify no regressions |

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Over-cropping clips text | Scan stops at 2-consecutive-white gap; `_capInsetPairForInterior` prevents cell collapse; ground truth regression test catches any field loss |
| Removing drift correction breaks edge case | Grid positions are accurate to <1px (proven across all 42 lines); scan from edgePos handles sub-pixel offset naturally |
| baselineInset increase too aggressive | Formula is `ceil(w/2) + ceil(w*0.25) + 1` — for w=6 that's 5px, well within the 10+ px gap to nearest text |
| Legacy fallback path affected | `_scanWhitespaceInset` is unchanged; only the width-driven path is modified |

## Decision Log

| Decision | Rationale |
|----------|-----------|
| Remove drift correction (not fix it) | Grid positions accurate to <1px; drift correction solves a <1px problem while creating 1-3px false corrections; removal is simpler and more robust |
| TDD red-green approach | User preference; proves tests catch the bug before fix is applied |
| Update baselineInset formula | Current formula (`ceil(w/2)+1`) fails for 41/42 lines; new formula covers half-width + AA margin |
| Keep scan-based approach (not formula-only) | Scan adapts to actual pixel content; formula is just the safety floor |
| 3-layer protection | Scan cap (lineWidth-proportional), interior preservation (existing), ground truth regression (new test) |
