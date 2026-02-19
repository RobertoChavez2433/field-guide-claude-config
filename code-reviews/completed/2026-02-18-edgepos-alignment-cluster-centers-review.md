# EdgePos Alignment Review: Page-Wide Center Averaging Drift

Date: 2026-02-18  
Scope: Root-cause analysis only (no code changes)  
Problem statement: `edgePos` can land ~1-3 px away from true local gridline center at specific rows; hypothesis is page-wide averaging in `_clusterIndicesToNormalized`.

## Executive Summary

The hypothesis is validated.

1. Grid line detection currently projects vertical lines across a page-level scan range and collapses each candidate run to a single normalized center.
2. That center is row-agnostic and is later used to build per-cell crop edges.
3. Empirical Springfield measurements show row-local drift from those global centers in the exact range discussed (typically ~1-3 px, with larger tails).
4. This drift directly affects `edgePos` used by `_scanWhitespaceInset` and can contribute to under-trimming of line artifacts at specific rows.

## Severity-Ranked Findings

### 1) High: Row-specific geometry is discarded before OCR crop building

`_detectVerticalLines` builds vertical candidates by coverage over `clampedStartY..clampedEndY`, then `_clusterIndicesToNormalized` emits one center per contiguous run.

Key code:

- Candidate accumulation over full scan-height:
  - `lib/features/pdf/services/extraction/stages/grid_line_detector.dart:447`
  - `lib/features/pdf/services/extraction/stages/grid_line_detector.dart:457`
  - `lib/features/pdf/services/extraction/stages/grid_line_detector.dart:458`
- Collapse to global centers:
  - `lib/features/pdf/services/extraction/stages/grid_line_detector.dart:462`
  - `lib/features/pdf/services/extraction/stages/grid_line_detector.dart:278`
  - `lib/features/pdf/services/extraction/stages/grid_line_detector.dart:297`

Impact:

This design intentionally loses row-local line trajectory/curvature/skew info. Downstream stages receive only page-level center coordinates.

### 2) High: Drift is real and material in Springfield fixtures

Read-only analysis on page preprocessed images + `springfield_grid_lines.json` measured local row-band line centers near each global line center:

- Overall (959 row-line samples):
  - Mean abs drift: `0.972 px`
  - P95 abs drift: `2.740 px`
  - Max abs drift: `7.521 px`

Per-page summary:

- Page 0: mean `0.344`, p95 `0.952`, max `1.069`
- Page 1: mean `1.680`, p95 `3.734`, max `4.486`
- Page 2: mean `0.857`, p95 `2.276`, max `2.989`
- Page 3: mean `0.448`, p95 `1.369`, max `2.356`
- Page 4: mean `1.462`, p95 `2.876`, max `3.792`
- Page 5: mean `0.348`, p95 `0.699`, max `7.521` (tail outlier rows)

Known pipe rows:

- Page 2 row 26: mean abs drift `2.020 px`, max `2.224 px`
- Page 4 row 25: mean abs drift `2.264 px`, max `2.938 px`

These directly corroborate 1-3 px row-level misalignment on problematic rows.

### 3) Medium: Merging can add additional center bias

Nearby center merging (`kMinLineSpacing = 0.005`) averages centers that are close in normalized space.

Key code:

- `lib/features/pdf/services/extraction/stages/grid_line_detector.dart:20`
- `lib/features/pdf/services/extraction/stages/grid_line_detector.dart:311`
- `lib/features/pdf/services/extraction/stages/grid_line_detector.dart:477`

At high image widths, this spacing represents non-trivial pixel distance, so local multi-peak structure can be averaged into a slightly shifted center.

### 4) Medium: Drift propagates unchanged into `edgePos`

In `TextRecognizerV2`, cell bounds come from normalized line centers, then convert to pixel edges (`floor/ceil`) and become scan origins for `_scanWhitespaceInset`.

Key code:

- Bounds to pixels:
  - `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:337`
  - `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:343`
- Inset scan edge use:
  - `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:360`
  - `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:611`

If center is off locally, scan starts from an off-local edge.

### 5) Medium: Existing tests do not detect row-varying center drift

Current stage tests validate straight synthetic grids and count/merge behavior, but not local row wobble/skew behavior.

Key test file:

- `test/features/pdf/extraction/stages/stage_2b_grid_line_detector_test.dart:151`
- `test/features/pdf/extraction/stages/stage_2b_grid_line_detector_test.dart:173`
- `test/features/pdf/extraction/stages/stage_2b_grid_line_detector_test.dart:248`

Coverage gap:

No test asserts detector accuracy under row-dependent line displacement.

## Root-Cause Chain

1. Page-level projection and clustering produce one vertical center per line.
2. True local center varies by row (document warp/scan artifacts/thickness variation).
3. OCR crop edges use global center-derived boundaries.
4. `_scanWhitespaceInset` starts from these boundaries.
5. Local offset can place scan origin in a less representative pixel region for that row.

This does not require a detector bug; it is a representational limitation of scalar-center output for a row-varying geometry problem.

## Alternatives and Refactor Scope

### Option A: Per-row centers (structural fix)

Concept:

Store row-segment-specific vertical center info (or line polylines) and use row-local centers for crop edges.

Pros:

- Correct model for row-varying geometry.
- Addresses root cause directly.

Cons:

- Larger refactor:
  - `GridLineResult` schema change
  - serialization/migration impact
  - downstream consumers (`TextRecognizerV2`, possibly column/stage diagnostics)
  - test fixture regeneration and compatibility updates

Risk:

- Medium-high implementation risk, high correctness upside.

### Option B: Local recentering at crop-time (targeted mitigation)

Concept:

Keep global centers in stage output, but locally recenter scan start near each row/cell before applying insets.

Pros:

- Lower blast radius.
- Can recover local alignment without fully changing grid model.

Cons:

- More heuristic behavior in OCR stage.
- May still lag full per-row representation in edge cases.

Risk:

- Medium risk, medium-high practical gain.

### Option C: Keep current model, tune thresholds only

Pros:

- Minimal code churn.

Cons:

- Does not resolve structural center drift.
- Likely unstable across PDFs/pages.

Risk:

- High risk of incomplete fix.

## Recommended Path

1. Add regression coverage first for row-varying line displacement in `stage_2b_grid_line_detector_test.dart`.
2. Implement targeted local recentering (Option B) as an intermediate step to reduce current defects quickly.
3. Plan per-row center model (Option A) if quality targets still miss after Option B.

## Suggested Test Additions

1. Horizontal drift synthetic: line y varies by x in small controlled wobble; assert stable detection and center accuracy envelope.
2. Vertical drift synthetic: line x varies by y; assert one logical line, bounded center bias, no false splits.

These tests should explicitly guard against row-specific center drift regressions.

## Investigation Artifacts

Inputs used:

- `test/features/pdf/extraction/fixtures/springfield_grid_lines.json`
- `test/features/pdf/extraction/fixtures/diagnostic_images/page_*_preprocessed.png`

Method:

- For each row band (between adjacent horizontal lines), estimate local dark-line center near each global line center in a limited x-window.
- Drift = `x_local - x_global`.
- Aggregate per-page and overall statistics.

No repository code was modified during this analysis.
