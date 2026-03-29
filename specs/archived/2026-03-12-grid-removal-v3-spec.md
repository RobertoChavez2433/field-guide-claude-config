# Grid Removal v3: Morphological Isolation + HoughLinesP + Text Protection

**Date**: 2026-03-12
**Status**: APPROVED (post-adversarial review)
**Supersedes**: `.claude/specs/2026-03-11-grid-removal-v2-spec.md`
**Adversarial Review**: `.claude/adversarial_reviews/2026-03-12-grid-removal-v3/review.md`

## Overview

### Purpose
Replace the matched-filter-based grid line removal (v2) with morphological isolation + HoughLinesP coordinate extraction + text protection masking. This eliminates the fundamental flaw where perpendicular lines dominate the matched filter signal at intersections, and adds explicit protection for text characters that touch grid lines.

### Scope

**Included:**
- New morphological isolation + HoughLinesP pipeline within the grid line remover stage (2B-ii.6)
- Text protection mask to preserve characters at grid line contact points
- Contract tests for grid stages (currently missing)
- Updated diagnostic image output for the new mask approach
- Updated unit tests for remover

**Excluded:**
- Detector changes -- the existing GridLineDetector (stage 2B-ii.5) remains as-is
- Pipeline restructuring -- no new stages, just enhanced removal logic within the existing stage
- Downstream stage changes -- column detector, text recognizer, synthetic region builder all consume normalized positions which don't change
- GridLine model changes -- pixel coordinates stay as local variables in the remover (YAGNI: no downstream consumer uses them)

### Success Criteria
- [ ] Springfield PDF extraction: >= 130/131 items matched (currently 56/131)
- [ ] Diagnostic diff images show <= 5% excess mask pixels (currently 42-76%)
- [ ] All 751 existing unit tests pass
- [ ] Text characters at grid line contact points preserved (visual inspection of diagnostic images at Item No./Description and Description/Unit boundaries)
- [ ] No regression in pipeline report baseline

### Approach Selected
**Option A: Morphological Isolation + HoughLinesP** (from brainstorming)

**Why alternatives were rejected:**
- **Option B (HoughLinesP on binary, no text protection)**: Risk of detecting text baselines as lines; no safety net for text at contact points
- **Option C (Keep detector + HoughLinesP refinement in remover)**: HoughLinesP on raw image (not morphologically cleaned) gives less precise results; more complex with two detection methods

---

## Algorithm & Data Flow

### Modified Stage: GridLineRemover (2B-ii.6)

The remover's `_removeGridLines()` function gets replaced. No new pipeline stages -- everything happens within the existing remover stage.

### Algorithm (6 steps)

```
Input: grayscale PNG bytes + GridLineResult (from detector)

Step 1: DECODE + VALIDATE
  gray = cv.imdecode(pngBytes, IMREAD_GRAYSCALE)
  // SECURITY: Preserve maxDim=8000 guard (from v2 line 237-242)
  // SECURITY: Preserve pathological line count guard >50 per axis (from v2 line 253-258)
  // SAFETY: assert(gray.channels == 1)
  // SAFETY: Defensive re-sort lines by position (S11, from v2 line 260-262)
  (_, binary) = cv.threshold(gray, 128, 255, THRESH_BINARY_INV)
  // Lines + text = white (255), background = black (0)

Step 2: MORPHOLOGICAL ISOLATION
  // Kernel size derived from detector grid boundaries, not raw page dimensions.
  // Use span between first and last detected line per axis.
  // Floor at 30px minimum.
  hKernelWidth = max(30, min(cols ~/ 20, gridSpanX ~/ 3))
  vKernelHeight = max(30, min(rows ~/ 20, gridSpanY ~/ 3))
  hKernel = getStructuringElement(MORPH_RECT, (hKernelWidth, 1))
  vKernel = getStructuringElement(MORPH_RECT, (1, vKernelHeight))
  hMask = morphologyEx(binary, MORPH_OPEN, hKernel)  // H-lines only
  vMask = morphologyEx(binary, MORPH_OPEN, vKernel)  // V-lines only
  // Text destroyed (max 30px wide << 128px kernel). Lines survive (2300+px).
  // H-kernel erode destroys V-lines (and vice versa) -- eliminates
  // perpendicular-line interference that killed the matched filter.

Step 3: HoughLinesP COORDINATE EXTRACTION
  hSegments = HoughLinesP(hMask, rho=1.0, theta=PI/180, threshold=80,
                           minLineLength=cols/4, maxLineGap=30)
  vSegments = HoughLinesP(vMask, rho=1.0, theta=PI/180, threshold=80,
                           minLineLength=rows/8, maxLineGap=30)
  // SECURITY: If hSegments.rows > 500 or vSegments.rows > 500,
  //   log warning and fallback to detector positions for that axis.
  // Returns Vec4i arrays: (x1, y1, x2, y2) per segment
  // No Canny needed -- morphological output is already binary

Step 4: CLUSTER, MERGE & CROSS-REFERENCE
  // SAFETY: Defensive re-sort detector lines by position (S11)
  For H-segments: cluster by y-midpoint (tolerance = 5px), take avg Y + min/max X
  For V-segments: cluster by x-midpoint (tolerance = 5px), take avg X + min/max Y
  Cross-reference with detector positions (reject outliers >15px from any detector line)
  // Result: one merged line per physical grid line, with pixel start/end coords
  // Line width: use detector's widthPixels directly (no separate measurement step)
  //
  // FALLBACK: For any detector line with no matching HoughLinesP segment,
  //   use detector's normalized position * image dimension as pixel center.
  //   Draw straight line at that position (NO matched filter). This is NOT v2 --
  //   v2 used matched filter at endpoints. This fallback skips the matched filter entirely.

Step 5: BUILD REMOVAL MASK WITH TEXT PROTECTION
  gridMask = hMask | vMask              // All morphologically-detected grid pixels
  textPixels = binary & ~gridMask       // Dark pixels that are NOT grid lines = text
  textProtection = dilate(textPixels, 5x5 rect kernel)  // 2px safety margin
  //
  // KNOWN LIMITATION: At H/V intersections, gridMask is a filled rectangle
  // (lineWidth x lineWidth). Text pixels inside the intersection zone are
  // classified as grid and removed. This is acceptable: intersection zones
  // are small (~3x5px = 15px area) and text sits within cells, not at
  // intersection corners. Damage is strictly less than v1 or v2.

  removalMask = Mat.zeros(h, w)
  For each merged H-line: cv.line(removalMask, start, end, 255, thickness=widthPixels)
  For each merged V-line: cv.line(removalMask, start, end, 255, thickness=widthPixels)
  removalMask = removalMask & ~textProtection  // Subtract text pixels from mask

Step 6: INPAINT
  cleaned = cv.inpaint(gray, removalMask, 1.0, INPAINT_TELEA)
```

### Native Memory Management

Every `cv.Mat`, `cv.Scalar`, `cv.Point`, and `cv.Vec4i` returned by OpenCV must be disposed.
The implementation MUST use a structured try/finally pattern.

**Mat allocation inventory per page (~16 objects):**

| Step | Objects Created | Disposed When |
|------|----------------|---------------|
| 1 | `gray`, `binary` | finally block |
| 2 | `hKernel`, `vKernel`, `hMask`, `vMask` | finally block |
| 3 | `hSegments`, `vSegments` | after extracting coords to Dart lists |
| 3 | N x `Vec4i` (one per segment row) | immediately after reading val1-val4 |
| 5 | `gridMask`, `notGridMask` (from bitwiseNOT), `textPixels`, `textDilateKernel`, `textProtection`, `notTextProtection` (from bitwiseNOT), `removalMask`, final `maskedResult` | finally block |
| 6 | `cleaned` | after imencode, in finally block |
| - | `white` (Scalar), Points (per line draw) | finally / scoped finally |

**Peak native memory estimate:**
- At 2550x3300 (typical Springfield): ~16 x 8.4 MB = ~134 MB peak
- At 8000x8000 (maxDim): ~16 x 64 MB = ~1 GB peak (may need maxDim reduction)
- Recommended: monitor peak memory; consider maxDim=6000 if OOM on mobile

**Helper pattern for HoughLinesP extraction:**
```dart
List<(int x1, int y1, int x2, int y2)> _extractSegments(cv.Mat houghResult) {
  final segments = <(int, int, int, int)>[];
  try {
    for (int i = 0; i < houghResult.rows; i++) {
      final v = houghResult.at<cv.Vec4i>(i, 0);
      segments.add((v.val1, v.val2, v.val3, v.val4));
      v.dispose();
    }
  } finally {
    houghResult.dispose();
  }
  return segments;
}
```

### Security Guards (Preserved from v2)

These existing invariants MUST be preserved in the v3 implementation:

| Guard | Current Location | Purpose |
|-------|-----------------|---------|
| `maxDim = 8000` | `grid_line_remover.dart:237-242` | Reject oversized images before processing |
| `hLines.length > 50 \|\| vLines.length > 50` | `grid_line_remover.dart:253-258` | Reject pathological line counts |
| Defensive re-sort by position (S11) | `grid_line_remover.dart:260-262` | Guard against unsorted detector output |
| Empty image check | `grid_line_remover.dart:223-225` | Guard against zero-byte input |

**New guard:** HoughLinesP segment cap at 500 per axis. If exceeded, log warning and use detector fallback.

### Why HoughLinesP + Detector Cross-Reference

The detector finds lines via coverage analysis (proven reliable). HoughLinesP finds precise
pixel paths on morphologically-cleaned images. Cross-referencing prevents false positives
from HoughLinesP (e.g., a text baseline fragment surviving morphological isolation) by only
accepting HoughLinesP segments within 15px of a detector-confirmed line.

If HoughLinesP fails to find a segment for a detector line (fallback), use the detector's
normalized position converted to pixels as a straight line at center. NO matched filter
refinement -- the matched filter is what failed in v2.

---

## Diagnostic Outputs

The remover already emits diagnostic images via `onDiagnosticImage` callback. The v3 approach updates/adds:

| Callback Name | Content | New? |
|---------------|---------|------|
| `page_N_h_morph` | Horizontal morphological isolation (Step 2) | NEW |
| `page_N_v_morph` | Vertical morphological isolation (Step 2) | NEW |
| `page_N_text_protection` | Text protection mask (Step 5) | NEW |
| `page_N_grid_line_mask` | Final removal mask after text subtraction | UPDATED |
| `page_N_grid_line_removed` | Cleaned result after inpainting | UPDATED (existing) |

Note: follows existing naming convention (no `.png` extension in callback name).

---

## StageReport Metrics (Updated)

Replace matched-filter metrics with morphological/HoughLinesP metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `morph_h_segments` | int | HoughLinesP H-segments before filtering |
| `morph_v_segments` | int | HoughLinesP V-segments before filtering |
| `hough_accepted` | int | Segments accepted after cross-reference |
| `hough_rejected` | int | Segments rejected (>15px from detector line) |
| `hough_fallback_lines` | int | Detector lines with no HoughLinesP match (used fallback) |
| `text_protection_pixels` | int | Pixels in text protection mask |
| `mask_pixels_total` | int | Total pixels in final removal mask (existing) |
| `mask_coverage_ratio` | double | mask_pixels / (h*w) (existing) |
| `foreground_fraction` | double | countNonZero(binary) / (h*w) -- threshold health check |

---

## Text-Grid Contact Analysis

### Contact Patterns in Springfield Tables

1. **Dollar amounts near right V-line**: Trailing `00` in amounts like `$1,792.00` within 1-2px of rightmost vertical grid line
2. **Dollar signs near left V-line**: `$` in "Unit Price" column close to left column boundary
3. **Header row text**: Bold "Item No." / "Description" close to both bounding H-lines
4. **Multi-line rows**: Row 26 "Non-Hazardous Contaminated Material / Handling And" -- text wraps, reducing gap to grid lines
5. **Most body text**: 5-10px clearance from grid lines -- contact is the exception

### How Text Protection Works at Contact Points

**Scenario: Character touching H-line (e.g., "l" in "Inlet" with bottom touching H-line)**
- `hMorphMask`: H-kernel (128px) erosion destroys the "l" (only 2px wide). H-line survives.
- `textPixels = binary & ~gridMask`: The "l" body pixels NOT overlapping H-line are preserved as text.
- Contact-point pixels (where character overlaps H-line) are in `gridMask`, so NOT in `textPixels`.
- `removalMask & ~textProtection`: The "l" body is protected (with 2px dilation margin). Only the 1-2px overlap zone is removed.
- **Result**: Character loses 1-2px at contact point. Inpainting fills from surrounding character pixels. Tesseract recognizes the character.

**Scenario: Character touching V-line (e.g., trailing "0" near right V-line)**
- `vMorphMask`: V-kernel (165px) erosion destroys the "0" (only 42px tall). V-line survives.
- Text protection preserves the "0" body with 2px margin. Only 1-3px overlap with V-line removed.
- **Result**: Character loses 1-3px from edge. Shape retained for OCR.

**Scenario: Text at H/V intersection**
- gridMask at intersection is a filled rectangle (~3x5px). All pixels classified as grid.
- **Result**: Any text pixels in the intersection rectangle are removed. ACCEPTED LIMITATION -- intersection zones are small and text sits within cells, not at corners. Damage strictly less than v1/v2.

**Scenario: Small punctuation ON grid line (3x3 period on 5px line)**
- Period entirely within grid line width. Destroyed by removal.
- **Result**: Unavoidable for ANY approach. Extremely rare in these tables.

### Damage Comparison

| Approach | Damage at contact points | Excess mask pixels |
|----------|------------------------|--------------------|
| v1 (morphological dilation + inpaint) | 10-12px zone | 25-38% excess |
| v2 (matched filter endpoints) | 5-8px zone (mask deviates) | 42-76% excess |
| **v3 (morph isolation + HoughLinesP + text protection)** | **1-3px at true overlap only** | **< 5% target** |

---

## Edge Cases

| Scenario | Handling | Expected Outcome |
|----------|----------|-----------------|
| No grid lines detected | Remover passes through unchanged (existing behavior) | No mask, no inpainting |
| Text character entirely within grid line width | Removed -- unavoidable for any approach | Tesseract handles missing period via context |
| Multi-line row text close to H-line | Text protection mask preserves text (2px margin); H-line mask is narrow (2-3px) | 1-2px loss at contact max |
| Dollar amounts touching right V-line | Text protection subtracts trailing digit pixels from V-line mask | Character preserved except 1-2px overlap |
| HoughLinesP returns no segments for a page | Fallback to detector positions as straight lines (no matched filter) | Graceful degradation |
| HoughLinesP returns >500 segments | Log warning, fallback to detector positions for that axis | Security: prevent resource exhaustion |
| HoughLinesP returns spurious segments | Cross-reference with detector positions -- reject segments >15px from any detected line | False positives filtered |
| Very thick lines (>5px) producing dual HoughLinesP detections | Merge by position clustering (5px tolerance) | Single merged line |
| Page with no text at all | Text protection mask is empty; removal mask unmodified | Full grid removal |
| Small image (cols < 600 or rows < 600) | Kernel size floored at 30px | Degenerate input handled safely |
| Text at H/V intersection corner | Absorbed into gridMask, removed | Accepted limitation (intersection area ~15px) |

---

## Testing Strategy

### New Tests

**1. Contract Test: Stage 2B-ii.5 to 2B-ii.6** (currently missing)
- File: `test/features/pdf/extraction/contracts/stage_2b5_to_2b6_contract_test.dart`
- Validates: GridLineResult passed to remover has valid positions, widths
- Validates: Remover output preserves page count, image dimensions
- Validates: StageReport satisfies no-data-loss invariant

**2. Contract Test: Stage 2B-ii.6 to 2B-iii** (currently missing)
- File: `test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart`
- Validates: Cleaned pages have valid PNG bytes, same dimensions as input
- Validates: StageReport metrics contain expected keys

**3. Remover Unit Tests** (update existing `grid_line_remover_test.dart`)
- Test morphological isolation produces clean line masks on synthetic images
- Test HoughLinesP returns segments near detector positions
- Test text protection mask correctly excludes text pixels
- Test removal mask width matches detector widthPixels
- Test fallback when HoughLinesP fails to find a detector line
- Test diagnostic image emission for new image types
- Test security guards preserved (maxDim, pathological count, empty input)

**4. Synthetic Text-Contact Test** (new)
- File: `test/features/pdf/extraction/stages/grid_line_remover_morph_test.dart`
- Create synthetic images with text touching grid lines at known positions
- Verify: text pixels preserved, grid line pixels removed
- Verify: mask excess < 5% vs grid-line-only pixels
- Test cases: character above H-line, character left of V-line, character at intersection corner

**5. Integration: Diagnostic Test** (update `grid_removal_diagnostic_test.dart`)
- Generate new diagnostic images for visual inspection
- Add morphological mask and text protection mask outputs
- Compare mask pixel counts vs v1/v2 baselines

**6. Integration: Pipeline Report** (run `springfield_report_test.dart`)
- Establish new baseline after v3 implementation
- Regression gate must pass

### Existing Tests (must continue passing)
- All 751 unit tests
- `stage_2b_grid_line_detector_test.dart` -- unchanged, detector not modified
- `stage_2b_text_recognizer_test.dart` -- crop logic unchanged
- `stage_4c_column_detector_test.dart` -- consumes normalized positions unchanged

---

## Performance

| Step | Estimated Time | Notes |
|------|---------------|-------|
| Decode + Threshold | ~5ms | Single pass |
| Morphological open (2x) | ~10ms | Two kernel passes |
| HoughLinesP (2x) | ~10-15ms | On clean morph output |
| Cluster + cross-reference | ~1ms | Pure Dart, small arrays |
| Text protection mask | ~5ms | Bitwise ops on full image |
| Build removal mask | ~1ms | Line drawing |
| Inpaint | ~10-30ms | TELEA, narrow mask |
| Mat disposal overhead | ~2ms | ~16 Mat dispose calls |
| Diagnostic image encoding | ~20-30ms | 5 diagnostic PNGs (if callback enabled) |
| **Total** | **~65-100ms** | vs current ~30-50ms |

Realistic per-page estimate including diagnostic output. Still negligible vs OCR (2-5s/page).

---

## OpenCV API Reference (verified in opencv_dart 2.2.1+3)

All functions confirmed available:

| Function | Dart Signature |
|----------|---------------|
| `threshold` | `(double, Mat) threshold(InputArray src, double thresh, double maxval, int type)` |
| `getStructuringElement` | `Mat getStructuringElement(int shape, (int,int) ksize)` |
| `morphologyEx` | `Mat morphologyEx(Mat src, int op, Mat kernel)` |
| `HoughLinesP` | `Mat HoughLinesP(InputArray image, double rho, double theta, int threshold, {double minLineLength, double maxLineGap})` |
| `bitwiseAND` | `Mat bitwiseAND(InputArray src1, InputArray src2, {OutputArray? dst})` |
| `bitwiseNOT` | `Mat bitwiseNOT(InputArray src, {OutputArray? dst})` |
| `bitwiseOR` | `Mat bitwiseOR(InputArray src1, InputArray src2, {OutputArray? dst})` |
| `dilate` | `Mat dilate(Mat src, Mat kernel, {Mat? dst, int iterations})` |
| `inpaint` | `Mat inpaint(InputArray src, InputArray mask, double radius, int flags)` |
| `line` | `Mat line(InputOutputArray img, Point pt1, Point pt2, Scalar color, {int thickness})` |
| `imdecode` | `Mat imdecode(Uint8List buf, int flags)` |
| `imencode` | `(bool, Uint8List) imencode(String ext, InputArray img)` |
| `countNonZero` | `int countNonZero(Mat src)` |

HoughLinesP output: Mat of Vec4i rows. Read via `lines.at<cv.Vec4i>(i, 0)` -> `.val1`(x1), `.val2`(y1), `.val3`(x2), `.val4`(y2). Each Vec4i must be disposed after reading.

---

## Migration / Cleanup

### Files Modified
| File | Change |
|------|--------|
| `stages/grid_line_remover.dart` | Replace `_removeGridLines()` with morph+HoughLinesP approach; remove `_matchedFilterY/X`; update `_GridRemovalResult` metrics |

### Files Added
| File | Purpose |
|------|---------|
| `test/.../contracts/stage_2b5_to_2b6_contract_test.dart` | Grid stage contract test |
| `test/.../contracts/stage_2b6_to_2biii_contract_test.dart` | Grid-to-OCR contract test |
| `test/.../stages/grid_line_remover_morph_test.dart` | Synthetic text-touching-gridline tests |

### Dead Code Removed
- `_matchedFilterY()` (~45 lines)
- `_matchedFilterX()` (~42 lines)
- `_GridRemovalResult.sampleCount` and `matchScoreStats` fields
- `matchScoreValues` accumulation and statistics computation (~40 lines)
- Total: ~130 lines removed

### NO Data Model Changes
GridLine model (`grid_lines.dart`) is NOT modified. Pixel coordinates are local variables
inside the remover only. No downstream consumer needs them. (YAGNI per adversarial review.)

---

## Key Constants

| Constant | Value | Rationale |
|----------|-------|-----------|
| Binarization threshold | 128 | Matches detector's `kDarkPixelThreshold` |
| H-kernel width | `max(30, min(cols/20, gridSpanX/3))` | Derived from detector boundaries; destroys text, preserves lines |
| V-kernel height | `max(30, min(rows/20, gridSpanY/3))` | Same principle for vertical |
| Min kernel dimension | 30px | Safety floor for small/degenerate images |
| HoughLinesP rho | 1.0 | 1px distance resolution (standard) |
| HoughLinesP theta | PI/180 | 1-degree angular resolution |
| HoughLinesP threshold | 80 | Min votes; start here, tune if needed |
| H minLineLength | `cols/4` (~637px) | Reject text remnants |
| V minLineLength | `rows/8` (~412px) | Reject text remnants |
| maxLineGap | 30 | Merge small gaps in lines |
| Max HoughLinesP segments | 500 per axis | Security cap to prevent resource exhaustion |
| Cluster tolerance | 5px | Merge HoughLinesP segments belonging to same physical line |
| Cross-reference tolerance | 15px | Max distance from detector position to accept HoughLinesP segment |
| Text protection dilation | 5x5 rect kernel | 2px safety margin around text |
| Inpaint radius | 1.0 | Minimal influence zone (same as v2) |
| Inpaint method | INPAINT_TELEA | Fast marching, best for narrow masks |
| maxDim | 8000 | SECURITY: reject oversized images |
| Max lines per axis | 50 | SECURITY: reject pathological grid line counts |
