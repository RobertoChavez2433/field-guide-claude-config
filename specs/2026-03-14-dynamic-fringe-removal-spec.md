# Dynamic Per-Line Grayscale Fringe Removal

**Date**: 2026-03-14
**Status**: Reviewed — MUST-FIX items addressed
**Scope**: `GridLineRemover._removeGridLines()` in Stage 2B-ii.6

## Overview

### Purpose

Grid lines in rasterized PDFs have anti-aliased fringe pixels (grayscale 128-200) that survive the binary threshold (128) and remain in the image after grid removal. Tesseract reads these as characters (`|`, `CB`, `Be`, `®`, etc.), creating phantom OCR elements that cascade into downstream failures.

The current removal mask is drawn at the detector's measured `widthPixels` — the binary-thresholded core width. This misses the soft gradient pixels around each line edge.

### Problem Evidence

- Pre-wave1 baseline removed 2.34M mask pixels; current code removes 1.97M (-16%)
- Latest Springfield run produces 1,579 OCR elements vs 1,429 baseline (+150 phantom elements)
- OCR cell corpus shows 60% edge dark fraction (`avg_raw_edge_dark_fraction: 0.595`), confirming grid residue in cell crops
- Item numbers read as `aE`, `ha`, `BE`, `Bi`, `®`, `oo`, `kd` instead of real numbers
- Unit column reads as `CB`, `CEB`, `Be`, `BA`, `Bo` instead of `EA`

### Success Criteria

- [ ] Per-line fringe width is measured dynamically from the grayscale image
- [ ] Removal mask expands to cover measured fringe without static thickness hacks
- [ ] `avg_raw_edge_dark_fraction` in crop residue metrics decreases
- [ ] No visible text erosion in diagnostic PNGs (`page_N_grid_line_removed`)
- [ ] Springfield item count does not regress from committed-code baseline (105/131)
- [ ] Existing grid_line_remover tests continue to pass
- [ ] All existing security guards (maxDim=8000, >50 lines/axis, empty image, channel check) preserved unchanged

### Non-Goals

- No text protection subtraction from the removal mask (inpainting handles contact points)
- No changes to text_recognizer_v2.dart retry logic (separate concern)
- No changes to grid_line_detection (upstream stage unchanged)
- No adaptive per-page or per-image threshold tuning

## Algorithm Design

### Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `fringeThreshold` | 200 | Grayscale cutoff for fringe. Anti-aliased pixels fall in 128-200 range. Clean PDF background is 245-255. Fixed constant — simple, testable. |
| `maxFringeScan` | 3px | Max pixels to scan outward from line edge per side. Anti-aliasing at 300 DPI rarely exceeds 2-3px. Hard safety cap — actual fringe determined by measurement. Max expandedThickness = 50 (widthPixels cap) + 3 + 3 = 56, well within `cv.line` limits. |
| `sampleCount` | 10 | Perpendicular profile samples per line. Evenly spaced at 10%-90% of line span. Median tolerates 2-3 text-contact outliers. Cost: ~11K pixel reads total (~1ms). |
| `_kBinaryThreshold` | 128 | Existing constant. Used as lower bound for fringe band — pixels below this are line core, not fringe. |

### Fringe Band Definition

The fringe is specifically the grayscale band **128 ≤ value < 200**:
- Pixels < 128: line core or text (already in binary, handled by existing mask)
- Pixels 128-199: anti-aliased fringe (the target — not in binary, not in mask, visible to Tesseract)
- Pixels ≥ 200: clean background (safe to ignore)

The scan stops when it hits EITHER boundary: `gray[x,y] >= 200` (background) OR `gray[x,y] < 128` (line core / text / adjacent grid line). This prevents intersection pixels from being counted as fringe.

### Insertion Point

Inside `_removeGridLines()`, after the existing `removalMask` is built from merged line coordinates (after the V-lines drawing loop) and before `maskedRemovalMask` assignment.

The existing `removalMask` construction (drawing lines at detector positions with detector thickness) remains unchanged. The new code measures fringe and expands the mask. All existing security guards upstream (maxDim, line count, empty image, channel check) are preserved untouched.

### Algorithm Steps

```
EXISTING (unchanged, including all security guards):
  1. Decode grayscale image, threshold to binary
  2. Morphological isolation → hMask, vMask
  3. HoughLinesP → segment extraction
  4. Cluster, merge, cross-reference with detector → mergedH, mergedV
  5. Build removalMask by drawing merged lines at detector thickness

NEW (inserted after step 5):
  6. Count H-mask pixels: horizontalMaskPixels = countNonZero(removalMask)
     (captured BEFORE V-lines are drawn)

  --- Draw V-lines on removalMask (existing code, reordered) ---

  7. Count V-mask pixels: verticalMaskPixels = countNonZero(removalMask) - horizontalMaskPixels
     (approximate — intersection overlap attributed to H)

  8. For each merged line (H and V separately):
     a. Compute sample positions along the line span:
        - sampleCount = min(10, max(3, lineSpan / 2))
        - Evenly spaced from 10% to 90% of line length
        - All positions clamped to [0, dimension-1]
        - Lines with span < 5px: skip fringe scan entirely

     b. At each sample point, scan perpendicular in BOTH directions:
        - Compute scan start: lineCenter ± (thickness / 2 + 1)
        - Clamp start to [0, rows-1] (H-lines) or [0, cols-1] (V-lines)
        - If gray value at start < 128: detector thickness is too narrow,
          skip this sample (don't count core pixels as fringe)
        - Walk outward pixel by pixel in the grayscale image:
          * Check bounds: 0 <= coord < dimension
          * Read gray[x,y]
          * If value < 128: STOP (hit line core or text)
          * If value >= 200: STOP (hit background)
          * Otherwise (128-199): count as fringe pixel
        - Cap at maxFringeScan (3px)
        - Record fringeWidth for this side at this sample

     c. Compute per-line fringe widths:
        - fringeSide1 = median of valid side-1 measurements
        - fringeSide2 = median of valid side-2 measurements
        (For H-lines: above/below. For V-lines: left/right.)
        - If fewer than 3 valid measurements on a side, fringeSide = 0

     d. If fringeSide1 + fringeSide2 > 0:
        - Redraw line on removalMask with expanded thickness:
          expandedThickness = originalThickness + fringeSide1 + fringeSide2
        - Shift line center by (fringeSide2 - fringeSide1) / 2
          to handle asymmetric fringe

EXISTING (unchanged):
  9. maskedRemovalMask = removalMask  (no text protection subtraction)
 10. Inpaint with maskedRemovalMask
 11. Encode outputs and diagnostic images
```

### Why No Text Protection Subtraction

Text protection is intentionally NOT applied to the removal mask:

1. **Fringe scan is surgical** — only extends 0-3px from the measured line edge
2. **Fringe band excludes text** — scan stops at pixels < 128 (text cores), so text strokes cannot inflate fringe measurements
3. **Median filters text-contact outliers** — 10 samples per line, text contact affects 1-2 at most
4. **Inpainting reconstructs, doesn't delete** — `cv.inpaint(TELEA)` fills masked pixels from surrounding context; a glyph edge that overlaps the fringe zone is reconstructed from adjacent glyph pixels
5. **Text cores are solid black** (grayscale 0-50), far below the fringe zone (128-200)
6. **Text protection causes grid residue** — carving holes in the mask at line positions leaves exactly the residue we're trying to eliminate

The existing `textProtection` computation is kept for diagnostic metrics only. It is not subtracted from the removal mask. The `notTextProtection` Mat allocation (currently dead code) should be removed.

### Handling Asymmetric Fringe

Fringe can be asymmetric — wider on one side of the line than the other. This happens when:
- A line is near the edge of the grid (one side is margin, the other is cell content)
- Rendering sub-pixel alignment differs per side

The algorithm measures each side independently (fringeSide1, fringeSide2) and shifts the expanded line center to cover the actual fringe distribution. For example:

```
Original line:     center=500, thickness=3  → pixels 499-501
Measured fringe:   above=2, below=1
Expanded line:     center=500.5, thickness=6 → pixels 498-503
                   (shifted 0.5px toward the wider fringe)
```

Since `cv.line` uses integer coordinates, the shift is rounded. A 0.5px shift becomes either 0 or 1px depending on rounding — this is acceptable given the 1px granularity of the mask.

### Diagnostic Outputs

Existing diagnostic images are unchanged:
- `page_N_grid_line_mask` — now shows the expanded mask (fringe included)
- `page_N_grid_line_removed` — the cleaned image for visual verification
- `page_N_h_morph`, `page_N_v_morph` — unchanged (morph happens before fringe scan)
- `page_N_text_protection` — unchanged (kept for metrics, not applied)

### Report Metrics

Updated metrics in the per-page report:
- `horizontal_mask_pixels` — actual H-mask pixel count (counted after drawing H-lines, before V-lines)
- `vertical_mask_pixels` — V-mask pixel count (total minus H, approximate due to intersection overlap)
- `fringe_pixels_added` — NEW: total pixels added by fringe expansion (expanded total - pre-expansion total)
- `avg_fringe_width_h` — NEW: average measured fringe width across H-lines (mean of per-line medians)
- `avg_fringe_width_v` — NEW: average measured fringe width across V-lines

New metric keys must be added to the contract test assertions.

## Data Model

No data model changes. The `_GridRemovalResult` struct gains five new fields for fringe and mask metrics:
- `int horizontalMaskPixels`
- `int verticalMaskPixels`
- `int fringePixelsAdded`
- `double avgFringeWidthH`
- `double avgFringeWidthV`

The `_MergedLine` struct is unchanged — fringe expansion redraws lines on the existing `removalMask` Mat using the expanded thickness.

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Fringe scan hits intersection (adjacent grid line) | Scan stops at `gray < 128` — adjacent line core pixels are well below the fringe band. Intersection pixels are not counted as fringe. |
| All 10 samples measure 0 fringe | No expansion for this line. Original thickness is sufficient. |
| Line span < 5px | Skip fringe scan entirely. Keep original thickness. |
| Line span < 10 but ≥ 5px | Scale sample count: `min(10, max(3, span / 2))`. Minimum 3 for valid median. |
| Grayscale image has unusual brightness | fringeThreshold=200 is conservative. If background is darker (e.g., 220), we might over-capture. Monitor via `avg_fringe_width` metrics. |
| Line at image edge (< 3px from border) | Scan start and each step clamped to `[0, dimension-1]`. Scan fewer pixels on the edge side. |
| Scan start pixel is < 128 (inside line core) | Detector thickness is too narrow for this line. Skip this sample — don't count core pixels as fringe. Log warning if > 50% of samples skip. |
| Scan start pixel is ≥ 200 (already in background) | Fringe width = 0 for this sample. No expansion needed on this side. |

## Testing Strategy

### Unit Tests (grid_line_remover_test.dart)

| Test | Focus | Priority |
|------|-------|----------|
| Fringe measurement on anti-aliased synthetic image | Create image with explicit grayscale gradient (128-200 band) around a line, verify measured fringe width matches expected | HIGH |
| No fringe on clean binary line | Line drawn at grayscale 0 with no gradient → fringe = 0 | HIGH |
| Intersection does not inflate fringe | Two crossing lines, verify fringe measurement ignores intersection pixels (stops at < 128) | HIGH |
| Bounds clamping near image edge | Line at y=1 with thickness=4, verify no crash and scan is clamped | HIGH |
| Asymmetric fringe handling | Wider fringe on one side → verify mask expansion is asymmetric | MED |
| Text near line doesn't inflate median | 2 of 10 samples near dark text, median still reflects true fringe | MED |
| Short line sample count scaling | Line of 8px span → 4 samples. Line of 3px span → skipped. | LOW |
| Fringe metrics in report | Verify `fringe_pixels_added`, `avg_fringe_width_h/v` are present and sensible | MED |

**Synthetic test image helper**: Tests require a new `createAntiAliasedGridImage()` helper that draws lines with explicit grayscale gradients (e.g., core=0, fringe band=[140, 170, 195] for a 3px gradient) instead of the existing `createSyntheticGridImage()` which only draws binary black/white lines.

### Integration Verification

- Run Springfield pipeline, compare `page_N_grid_line_mask` PNGs before/after
- Compare `avg_raw_edge_dark_fraction` in crop residue metrics (should decrease)
- Compare item count and field accuracy in scorecard
- Visually inspect `page_N_grid_line_removed` for text erosion near grid lines

### Rollback Criteria

If any of these occur after implementation, revert fringe expansion and investigate:
- Springfield item count drops below 105 (committed baseline)
- `avg_fringe_width` exceeds 3.0 (scan hitting cap on most lines — threshold or cap is wrong)
- Visible text erosion in diagnostic PNGs
- New OCR artifacts traceable to over-removal

## Performance Considerations

| Operation | Cost | Impact |
|-----------|------|--------|
| Grayscale pixel reads | Worst case: 100 lines × 10 × 2 × 3 = 6K reads | < 0.1ms, negligible |
| Line redrawing | ~185 `cv.line` calls (already exists, just wider) | < 1ms, negligible |
| No new OpenCV Mat allocations | Reuses existing `removalMask` and reads from existing `gray` | Zero memory impact |
| No new image encoding | Diagnostic PNGs already encoded | Zero I/O impact |
| Pixel access method | Use `gray.at<int>(row, col)`. If opencv_dart allocates temporaries, switch to `ptrAt()` | Verify during implementation |

Total added cost: < 2ms on a 135-179s pipeline. Unmeasurable.

## Security Constraints

**All existing security guards MUST be preserved unchanged:**
- Empty image guard (line ~329)
- `maxDim=8000` image size guard (line ~344)
- Pathological line count `>50` per axis guard (line ~354)
- Channel count validation (line ~363)
- Empty inpaint result guard (line ~545)

The fringe scan adds no new attack surface:
- Bounded by `maxFringeScan=3` and `sampleCount=10` — maximum 6K pixel reads
- All pixel coordinates clamped to image bounds before access
- No new Mat allocations, no new file I/O, no new external calls

## Files to Modify

| File | Change |
|------|--------|
| `lib/features/pdf/services/extraction/stages/grid_line_remover.dart` | Add fringe measurement + mask expansion in `_removeGridLines()`. Fix h/v mask pixel tracking. Add fringe metrics to `_GridRemovalResult`. Remove dead `notTextProtection` allocation. |
| `test/features/pdf/extraction/stages/grid_line_remover_test.dart` | Add `createAntiAliasedGridImage()` helper. Add fringe measurement tests (intersection, bounds, asymmetric). Update metric key assertions. |
| `test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart` | Add `fringe_pixels_added`, `avg_fringe_width_h`, `avg_fringe_width_v` to contract assertions. |

## Decisions Made

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| Fixed fringeThreshold=200 | Simple, testable, covers 128-200 fringe range | Adaptive per-page (unnecessary complexity for digital PDFs), gradient-based (fragile) |
| Fixed maxFringeScan=3px | Covers real anti-aliasing at 300 DPI | Dynamic scaling with line width (fringe is edge property, not width property), 5px (overkill) |
| 10 samples per line | Robust median, negligible cost | 5 (less robust), 20 (overkill) |
| No text protection subtraction | Surgical scan + median + inpainting handles contact points; fringe band (128-200) excludes text cores | Soft threshold text mask (over-engineering), connected components filter (complex) |
| Fringe band stops at <128 | Prevents intersection pixels and text from being counted as fringe | No lower bound (would count intersections as fringe — review MUST-FIX #1) |
| H/V pixel tracking via sequential counting | Count H pixels after H-lines drawn, derive V from total | Separate Mats per orientation (extra allocation, more complex disposal) |
| Measure then adjust approach | Start with these parameters, verify via diagnostic PNGs, adjust if needed | Extensive upfront modeling (slower iteration) |

## Adversarial Review Summary

Review conducted by code-review-agent and security-agent on 2026-03-14.

### Addressed (MUST-FIX)
- Intersection scan bug: fringe band now defined as 128-200 with dual-boundary stop condition
- H/V mask pixel tracking: sequential counting approach specified
- Synthetic test helper: `createAntiAliasedGridImage()` specified
- Bounds checking: all coordinates clamped before pixel access
- Sample position clamping: explicit clamp to `[0, dimension-1]`
- Security guards: explicit preservation constraint added to success criteria

### Noted (SHOULD-CONSIDER)
- Scan start validation when detector thickness is wrong: handled as skip-sample + warning
- More samples for long lines with many intersections: deferred — try 10 first, adjust if needed
- Text erosion regression test: added to integration verification
- Rollback criteria: added explicit thresholds
- Remove dead `notTextProtection` allocation: added to files-to-modify
