# Per-Line Dynamic Whitespace-Scan Inset

**Created**: 2026-02-18 | **Revised**: 2026-02-18 | **Status**: Ready for implementation
**Blocker Ref**: BLOCKER-5 in `_state.md`

## Overview

### Purpose
Replace the fixed 9px `maxScanDepth` in `_scanWhitespaceInset` with a per-line dynamic inset calculated from measured grid line widths. The line width sets the expected inset, then a local scan validates/refines around that expectation. This eliminates the `0->C` / `0->cent` corruption on right-aligned text while maintaining grid line removal.

### Scope
- **In scope**: New `_computeLineInset` function, per-line center correction, updated call sites in `_recognizeWithCellCrops`, before/after unit tests on known cells, fixture regeneration
- **Out of scope**: Changes to grid line detection, column detection, or any downstream stages

### Success Criteria
- Items 29 and 111 bid_amount values parse correctly (`$7,026.00` and `$5,179.30`)
- Zero new `|` pipe artifacts in any cell
- Scorecard bid_amount improves from 129/131 to 131/131
- No regression in parsed item count (stays at 131)
- Before/after tests prove insets are the minimum needed to clear grid line bodies + fringe, no excess

## Algorithm: `_computeLineInset`

### Inputs
- `image`: the preprocessed page image
- `edgePos`: pixel coordinate of the crop edge (at grid line center)
- `scanDirection`: +1 (inward from top/left) or -1 (inward from bottom/right)
- `perpStart` / `perpEnd`: perpendicular span for sampling
- `isHorizontalEdge`: axis flag
- `measuredLineWidthPx`: the specific grid line's width from `GridLineResult`

### Step 1: Map Cell Edge to Line Width

Each cell edge maps to a specific grid line's measured width:
- top -> `horizontalLineWidths[rowIndex]`
- bottom -> `horizontalLineWidths[rowIndex + 1]`
- left -> `verticalLineWidths[colIndex]`
- right -> `verticalLineWidths[colIndex + 1]`

### Step 2: Compute Dynamic Scan Depth Per Edge

Instead of fixed `maxScanDepth = 9`, compute per-edge:
```
w           = max(1, measuredLineWidthPx)
aa          = max(1, ceil(0.25 * w))       // anti-alias fringe (25% of line width)
drift       = 3                             // covers observed 1-3px center drift
plannedDepth = w + aa + drift               // total scan range
```

For Springfield values:
| Line width (w) | aa = ceil(0.25*w) | drift | plannedDepth | baselineInset = ceil(w/2)+1 |
|----------------|-------------------|-------|--------------|----------------------------|
| 2px | 1 | 3 | 6 | 2 |
| 3px | 1 | 3 | 7 | 3 |
| 4px | 1 | 3 | 8 | 3 |
| 5px | 2 | 3 | 10 | 4 |
| 6px | 2 | 3 | 11 | 4 |

### Step 3: Per-Line Center Correction (Before Scan)

The grid line positions from `_clusterIndicesToNormalized` are page-wide averages. The actual line center can drift locally by 1-3px. Before scanning, compute a local offset:

1. At the `edgePos`, sample a short perpendicular stripe (7-9 probes along the cell edge).
2. For each probe, scan a small window (e.g. ±`drift` px around `edgePos`) to find the local dark-pixel centroid.
3. Compute `delta` = median local center - `edgePos`.
4. Adjust: `correctedEdgePos = edgePos + delta`.
5. Scan from `correctedEdgePos` instead of raw `edgePos`.

This addresses the drift between page-averaged center and actual local center.

### Step 4: Scan With Width-Informed Termination

Use width as baseline inset, then scan to refine:

```
baselineInset = ceil(w / 2) + 1
```

Scan from `d = 0` to `d = plannedDepth`:
- Track dark pixel runs (contiguous dark pixels where `pixel.r < whiteThreshold`).
- When the scan encounters a dark run followed by **at least 2 consecutive white pixels**, that confirms the line has been exited.
- Record `refinedInset = d` at the point where the 2-white-pixel confirmation occurs.
- If no clear dark-then-white transition is found, fall back to `baselineInset`.

Final inset:
```
finalInset = clamp(max(baselineInset, refinedInset), 1, plannedDepth)
```

The `baselineInset` acts as a floor (never remove less than half the line), and `plannedDepth` acts as a ceiling (never scan past the width-informed bound).

### Step 5: Increased Probe Density + Robust Aggregation

Current code uses 3 probes at 25/50/75% of the perpendicular span, aggregated with `max`. This is too sparse and too sensitive to outliers (one probe hitting text inflates the whole edge).

New approach:
- Use 7-9 probes evenly spaced along the perpendicular span (or stride-based for very wide cells).
- Aggregate with **median** or **p75** instead of max.
  - Median: robust to 1-2 outlier probes hitting text or anomalies.
  - P75: slightly more conservative (removes more fringe) but still resistant to outliers.
- Recommended: **p75** -- errs on the side of removing slightly more fringe rather than leaving artifacts, while still ignoring the worst-case outlier probe.

### Fallback
When `hasHWidths` / `hasVWidths` is false, the old `_scanWhitespaceInset` remains as-is (existing behavior, no regression).

## Key Data Available at Call Site

The per-edge width lookup is trivial -- all data already in scope in `_recognizeWithCellCrops`:
- Top: `gridPage.horizontalLineWidths[cell.rowIndex]`
- Bottom: `gridPage.horizontalLineWidths[cell.rowIndex + 1]`
- Left: `gridPage.verticalLineWidths[cell.columnIndex]`
- Right: `gridPage.verticalLineWidths[cell.columnIndex + 1]`

Cell crop edges sit at grid line centers (from `_computeCellCrops`). Left/top are `floor()`'d, right/bottom are `ceil()`'d to pixel coords. Each crop includes roughly half the grid line body on each edge.

## Key Files
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:584` -- current scan function
- `lib/features/pdf/services/extraction/models/grid_lines.dart` -- `GridLineResult` model (per-line width arrays)
- `test/features/pdf/extraction/fixtures/springfield_grid_lines.json` -- line widths per page
- `test/features/pdf/extraction/fixtures/springfield_rendering_metadata.json` -- page pixel dims

## Test Design

### 3A: Unit Tests -- `_computeLineInset` in isolation

New file: `test/features/pdf/extraction/stages/whitespace_inset_test.dart`

Create synthetic test images with known grid lines and verify insets:

| Test case | Setup | Expected inset |
|-----------|-------|----------------|
| 3px line, no text nearby | 3px dark stripe on white | ~3 (baselineInset=3, scan confirms at dark-then-2-white boundary) |
| 5px line, text 6px away | 5px stripe, white gap, dark text | ~4 (scan exits line body, stops before text) |
| 5px line, text 2px away | 5px stripe, 2px gap, text | ~4, capped at baselineInset -- does NOT extend into text |
| 2px line, clean edge | 2px stripe on white | ~2 (baselineInset=2, scan confirms) |
| No width data (fallback) | Same image, no measured width | Falls through to old `_scanWhitespaceInset` |
| Dark-run-then-2-white termination | Line with 1px fringe beyond body | Scan finds fringe, exits after 2 white pixels |
| plannedDepth cap respected | Contrived case where dark extends far | Never exceeds plannedDepth |
| Center drift correction | Line center shifted 2px from edgePos | correctedEdgePos adjusts, inset still correct |
| Probe aggregation (p75 not max) | One probe hits text, others don't | p75 aggregation ignores the outlier probe |

### 3B: Before/After Integration -- Known Springfield Cells

Capture the **actual inset values** returned for specific cells before and after:

- **Item 29, bidAmount column** (right edge) -- currently overcropped, should shrink
- **Item 111, bidAmount column** (right edge) -- same corruption pattern
- **A healthy cell** (e.g. Item 1, description column) -- should stay the same or shrink, never grow

These tests read the real Springfield preprocessed image and grid line data from fixtures, call the inset function, and assert the returned value.

### 3C: Golden Fixture Regeneration

After implementation, regenerate all Springfield fixtures and verify:
- `springfield_parsed_items.json` -- Items 29/111 bid_amount values fixed
- Stage trace diagnostic -- scorecard bid_amount improves to 131/131
- No new `LOW` or `BUG` entries in the scorecard

## Implementation Steps

### Step 1: Write before-snapshot tests
- New test file: `test/features/pdf/extraction/stages/whitespace_inset_test.dart`
- Unit tests with synthetic images (Section 3A cases -- write against OLD function first to establish baseline behavior)
- Integration tests that call the **current** `_scanWhitespaceInset` on real Springfield data for Items 29, 111, and a healthy cell -- capture current inset values as assertions
- These tests pass against the current code (they document the "before" state)

### Step 2: Implement `_computeLineInset`
- New static method in `text_recognizer_v2.dart` alongside existing `_scanWhitespaceInset`
- Signature: `static int _computeLineInset(img.Image image, int edgePos, int scanDirection, int perpStart, int perpEnd, bool isHorizontalEdge, int measuredLineWidthPx)`
- Sub-steps:
  1. Compute `w`, `aa`, `drift`, `plannedDepth`, `baselineInset` from `measuredLineWidthPx`
  2. Per-line center correction: sample perpendicular stripe, find local dark centroid, compute `delta`, adjust `edgePos`
  3. Scan `d = 0..plannedDepth` with dark-run-then-2-white termination
  4. 7-9 probes with p75 aggregation
  5. Return `clamp(max(baselineInset, refinedInset), 1, plannedDepth)`

### Step 3: Wire up call sites
- In `_recognizeWithCellCrops`, replace the 4 `_scanWhitespaceInset` calls with `_computeLineInset` when width data is available
- Pass the correct per-edge width:
  - Top: `gridPage.horizontalLineWidths[cell.rowIndex]`
  - Bottom: `gridPage.horizontalLineWidths[cell.rowIndex + 1]`
  - Left: `gridPage.verticalLineWidths[cell.columnIndex]`
  - Right: `gridPage.verticalLineWidths[cell.columnIndex + 1]`
- Keep `_scanWhitespaceInset` as fallback when `hasHWidths` / `hasVWidths` is false

### Step 4: Update before-snapshot tests to "after" expectations
- Synthetic image tests: assert new insets match width-informed scan behavior
- Springfield integration tests: assert insets are minimum necessary (driven by measured line width)
- Items 29/111 right-edge insets should be smaller, driven by actual line width not fixed 9px
- Add new test cases for center correction and probe aggregation

### Step 5: Regenerate golden fixtures and validate
- Run fixture generator: `pwsh -Command "dart run tool/generate_springfield_fixtures.dart"`
- Run extraction test suite: `pwsh -Command "flutter test test/features/pdf/extraction/"`
- Run stage trace diagnostic: verify scorecard bid_amount -> 131/131
- Verify no new `LOW` or `BUG` entries

## Agent Assignments

| Step | Agent | Reason |
|------|-------|--------|
| 1 | qa-testing-agent | Test design and writing |
| 2-3 | frontend-flutter-specialist-agent | Dart implementation |
| 4 | qa-testing-agent | Update test assertions |
| 5 | qa-testing-agent | Fixture regen and validation |

## Risk Mitigation

- Step 1 locks in the "before" -- if anything regresses during implementation, tests catch it immediately
- The old function stays as fallback -- PDFs without width data are unaffected
- `plannedDepth` cap prevents overcrop: bounded by `w + aa + drift`, never unbounded
- `baselineInset` floor prevents undercrop: always removes at least `ceil(w/2) + 1`
- p75 aggregation prevents single-probe outliers from inflating the inset
- Center correction addresses the drift between page-averaged and local line positions

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Modify vs replace | New function, old as fallback | Clean separation, no regression risk for PDFs without width data |
| Scan behavior | Width as baseline + scan refine (not width-only or scan-only) | Width sets floor/cap, scan finds actual boundary within those bounds |
| Scan termination | Dark run then 2 consecutive white pixels | Confirms line exit without chasing dark pixels past a white gap |
| AA margin | `max(1, ceil(0.25 * w))` -- proportional to line width | Adapts to thicker/thinner lines instead of fixed 1px |
| Center correction | Per-line local offset delta before scanning | Addresses page-wide averaging drift in `_clusterIndicesToNormalized` |
| Probe density | 7-9 probes with p75 aggregation | Robust to local anomalies; max-of-3 was too sensitive to one probe hitting text |
| Hard cap | `plannedDepth = w + aa + drift` | Bounded by measured width, not arbitrary constant; drift=3 covers observed range |
| Test approach | Before/after + golden regen | Locks in current behavior, proves improvement, catches regressions |
