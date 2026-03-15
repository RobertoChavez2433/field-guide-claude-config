# Adversarial Review: Dynamic Per-Line Grayscale Fringe Removal

**Spec**: `.claude/specs/2026-03-14-dynamic-fringe-removal-spec.md`
**Date**: 2026-03-14
**Reviewers**: code-review-agent (opus), security-agent (opus)

## MUST-FIX (all addressed in spec update)

1. **Intersection scan bug** — Fringe scan counted pixels < 200 as fringe, but grid line pixels at intersections (< 128) would also match. Fix: define fringe as the 128-200 band with dual-boundary stop (`>= 200 || < 128`).

2. **H/V mask pixel tracking unspecified** — Drawing both H and V on one Mat makes decomposition impossible. Fix: count H pixels after H-lines drawn but before V-lines; derive V from total.

3. **Synthetic test image inadequate** — Existing `createSyntheticGridImage()` draws binary lines with no anti-aliasing. Fix: spec defines new `createAntiAliasedGridImage()` helper with explicit gradients.

4. **Perpendicular scan bounds** — Scan start could be negative for lines near image edge with wide thickness. Fix: clamp start AND each step to `[0, dimension-1]`.

5. **Sample position clamping** — 10%-90% positions must be clamped to valid image coordinates.

6. **Security guard preservation** — Spec must explicitly state existing guards are untouched. Fix: added to success criteria and security constraints section.

## SHOULD-CONSIDER (noted, deferred, or handled)

- **Scan start validation** (detector thickness mismatch): Handled as skip-sample + warning if gray < 128 at start point
- **More samples for long lines**: Deferred — try 10 first, adjust based on results
- **Text erosion regression test**: Added to integration verification
- **Rollback criteria**: Added explicit thresholds (item count < 105, avg_fringe > 3.0, visible text erosion)
- **Document max expandedThickness**: Added to parameters table (50 + 3 + 3 = 56)
- **Worst-case pixel reads bound**: Added to performance table (6K reads < 0.1ms)
- **Remove dead `notTextProtection` allocation**: Added to files-to-modify
- **Short line minimum**: Lines < 5px span skip fringe scan entirely

## NICE-TO-HAVE (logged for future)

- Fringe scan clamp event counter metric (`fringe_clamped_count`)
- Replace fragile line number references with code pattern references
- Consider directional dilation as simpler alternative to per-line redraw (if asymmetric case is rare)
- Clarify fringe scan behavior on fallback lines (when HoughLinesP > 500 cap)
- Verify `gray.at<int>()` allocation behavior in opencv_dart; switch to `ptrAt()` if needed

## Codebase Pattern Compliance

- Follows existing `_removeGridLines()` structure: compute → draw → encode
- Metrics follow existing naming pattern (`horizontal_mask_pixels`, `vertical_mask_pixels`)
- Test structure follows existing `grid_line_remover_test.dart` patterns (synthetic images, metric assertions)
- No new Mat allocations — consistent with existing memory discipline
- Security guard preservation follows existing defensive coding pattern

## Security Assessment

- **Resource exhaustion**: Bounded by existing 50-line cap × 10 samples × 3px × 2 sides = 6K reads max. Trivially safe.
- **Bounds checking**: All pixel access coordinates clamped to image dimensions. Spec mandates this explicitly.
- **Integer overflow**: Max thickness = 56, well within int range and `cv.line` limits.
- **Memory safety**: No new Mat allocations. Dead `notTextProtection` allocation flagged for removal.
- **Existing guards**: All 5 guards preserved unchanged (maxDim, line count, empty image, channel check, empty inpaint).
