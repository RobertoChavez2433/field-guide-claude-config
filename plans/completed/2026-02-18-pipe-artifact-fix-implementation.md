# Implementation Plan: Pipe Artifact Elimination — Scan Termination Fix

**Date**: 2026-02-18 | **Session**: 370
**Strategy**: Fix-and-observe (scan fix only, observe cascade on 9 boilerplate-misclassified items)
**Testing**: Integration-level via fixture regeneration + stage trace scorecard (no new unit tests)

## Overview

**Purpose**: Eliminate pipe `|` artifacts from OCR output by fixing the scan termination logic in `_scanWhitespaceInset`, then observe whether the fix cascades to recover 9 additional items whose prices were lost to boilerplate misclassification.

**Scope**:
- **In scope**: Single code change to `text_recognizer_v2.dart`, doc comment update, fixture regeneration, stage trace verification
- **Out of scope**: Row classifier changes (deferred pending observation), Cat C parser hardening, scorecard threshold changes
- **Deferred**: If the 9 items don't recover, a follow-up plan for row classifier guard

**Success Criteria**:
- [ ] Pipe count in `springfield_parsed_items.json` drops from 2 to 0
- [ ] Items 58 (bid_amount) and 111 (unit_price) recover non-null values
- [ ] No regression in existing 858 tests
- [ ] Stage trace scorecard shows improvement (observed, not gated)
- [ ] Bonus: Items 27-32, 59, 112, 113 recover unit_price (cascade success)

## Root Cause Summary

### Primary: Break-on-first-white (2 items directly affected)
`_scanWhitespaceInset` stops at the first white pixel (`pixel.r >= 230`). In failing cells, the edge profile is non-monotonic: `d=0` is white (anti-aliased fringe), `d=1..6` is dark (grid line body), `d=7+` is white. The loop breaks at `d=0`, returns inset=1, leaving the grid line intact. OCR reads it as `|`.

### Secondary: Boilerplate misclassification (9 items cascade)
Items 27-32, 59, 112, 113 have price elements with a slightly lower Y-center than item/description elements. Row grouping splits prices into a separate row. That row contains `|` pipe artifacts + real prices. Pipes cause the row classifier to tag the row as `boilerplate`. Stage 4D skips boilerplate → prices lost.

**Chain**: Pipe artifacts → pipes grouped with prices → boilerplate classification → prices skipped

If the scan fix eliminates pipes upstream, those rows may reclassify as DATA/CONTINUATION, recovering prices automatically.

## Implementation Steps

### Step 1: Update `_scanWhitespaceInset` inner loop

**File**: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
**Lines**: 608-628

Replace "break on first white" with "scan all depths, track furthest dark pixel":

**Current** (lines 610-625):
```dart
for (final perpPos in samplePositions) {
  int inset = 0;
  for (int d = 0; d < maxScanDepth; d++) {
    // ... coordinate computation ...
    final pixel = image.getPixel(px, py);
    if (pixel.r >= whiteThreshold) {
      break;                          // ← premature exit
    }
    inset = d + 1;
  }
  if (inset > maxInset) maxInset = inset;
}
```

**Fixed**:
```dart
for (final perpPos in samplePositions) {
  int lastDark = -1;
  for (int d = 0; d < maxScanDepth; d++) {
    // ... coordinate computation (unchanged) ...
    final pixel = image.getPixel(px, py);
    if (pixel.r < whiteThreshold) {
      lastDark = d;
    }
  }
  final inset = lastDark + 1;        // 0 if no dark pixels found
  if (inset > maxInset) maxInset = inset;
}
```

**Behavior change**:
| Case | Profile | Before | After |
|------|---------|--------|-------|
| A2 (pipe-producing) | white(d=0) → dark(d=1..6) → white(d=7+) | inset=1 | inset=7 |
| A1 (normal) | dark(d=0..1) → white(d=2+) | inset=2 | inset=2 (same) |
| Clean cell | all white | inset=1 | inset=1 (same) |

### Step 2: Update doc comment

**Lines**: 575-578

Change "Max scan depth is 5px" to reflect actual behavior: scans up to `maxScanDepth` (9px), returns furthest dark pixel + 1. Remove reference to "break on first white" termination.

### Step 3: Regenerate Springfield fixtures

```
pwsh -Command "dart run tool/generate_springfield_fixtures.dart"
```

### Step 4: Run full PDF extraction test suite

```
pwsh -Command "flutter test test/features/pdf/extraction/"
```

Verify: 858+ tests pass, 0 failures.

### Step 5: Verify results in regenerated fixtures

Check `springfield_parsed_items.json`:
1. **Pipe count**: grep for `"| ` — expect 0 (down from 2)
2. **Item 111**: `unit_price` should be `739.90` (was null)
3. **Item 58**: `bid_amount` should be `10206.80` (was null)
4. **Items 27-32, 59, 112, 113**: Check if `unit_price` recovered (cascade observation)
5. **Total null unit_price count**: Compare against current 24

### Step 6: Run stage trace scorecard

```
pwsh -Command "flutter test test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart --name 'Pipeline Scorecard'"
```

Observe scorecard changes — don't gate on thresholds, just record deltas.

## Decision Gate After Verification

| Outcome | Cascade items recovered | Next action |
|---------|------------------------|-------------|
| **Best case** | All 9 (27-32, 59, 112, 113) | Commit, update state, move to Cat C parser fixes |
| **Partial** | Some but not all 9 | Investigate which failed — row classifier guard needed for remaining |
| **Minimal** | Only 111 + 58 | Row classifier guard plan needed as follow-up |

No additional code changes in this plan regardless of outcome — observe and record.

## Files Touched

| File | Change | Risk |
|------|--------|------|
| `text_recognizer_v2.dart:608-628` | Replace inner loop logic | Low — scan depth capped at 9, min clamp preserved |
| `text_recognizer_v2.dart:575-578` | Doc comment update | None |
| `test/.../springfield_*.json` (14 fixtures) | Regenerated | None — test data only |

**No other source files modified.** Single method change, single file.

## Prior Analysis References

- Root cause analysis: `.claude/code-reviews/2026-02-18-scan-whitespace-inset-root-cause-analysis.md`
- Original fix plan: `.claude/plans/2026-02-18-pipe-artifact-scan-fix.md`
- Pixel evidence: Page 2 row 26 col 5, Page 4 row 25 col 4
- Blocker cascade investigation: Session 370 (this session)

## Current Baseline (Pre-Fix)

- 858 tests passing, 0 failures
- 2 pipe instances in parsed_items (items 58, 111)
- 24 items with null unit_price
- 24 items with null bid_amount
- Blocker breakdown: 1 pipe + 6 Cat B + 8 Cat C + 9 uncategorized (boilerplate cascade)
