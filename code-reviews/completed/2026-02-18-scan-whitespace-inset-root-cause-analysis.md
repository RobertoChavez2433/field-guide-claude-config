# Scan Whitespace Inset Root Cause Analysis

Date: 2026-02-18  
Scope: Root-cause investigation only (no code changes)  
Target: Why `_scanWhitespaceInset` fails to remove some pipe (`|`) artifacts that appear 2.5-5 px from grid centers even with `maxScanDepth=9`.

## Executive Summary

The primary root cause is not scan depth.  
The issue is a scan termination rule mismatch with real pixel structure at the left edge:

1. `_scanWhitespaceInset` stops as soon as it sees the first "white" pixel (`pixel.r >= 230`).
2. In failing pipe cells, the edge profile is non-monotonic:
   - `d=0` is white (>=230),
   - `d=1..6` is dark (<230),
   - `d>=7` is white again.
3. Because the loop breaks at `d=0`, inset stays `0` and is clamped to `1`, leaving the dark run intact.
4. Therefore increasing `maxScanDepth` from 5 to 9 cannot fix these specific cells, because the loop never reaches deeper depths.

## Files Investigated

- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
- `lib/features/pdf/services/extraction/stages/image_preprocessor_v2.dart`
- `lib/features/pdf/services/extraction/shared/crop_upscaler.dart`
- `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart`
- `test/features/pdf/extraction/fixtures/springfield_grid_lines.json`
- `test/features/pdf/extraction/fixtures/springfield_cell_grid.json`
- `test/features/pdf/extraction/fixtures/springfield_parsed_items.json`
- `test/features/pdf/extraction/fixtures/diagnostic_images/capture_manifest.json`
- `test/features/pdf/extraction/fixtures/diagnostic_images/page_2_row_26_col_5_raw.png`
- `test/features/pdf/extraction/fixtures/diagnostic_images/page_2_row_26_col_5_ocr.png`
- `test/features/pdf/extraction/fixtures/diagnostic_images/page_4_row_25_col_4_raw.png`
- `test/features/pdf/extraction/fixtures/diagnostic_images/page_4_row_25_col_4_ocr.png`

## Relevant Code Behavior

In `text_recognizer_v2.dart`:

1. `_scanWhitespaceInset(...)` scans inward from each crop edge.
2. It samples 3 perpendicular points (25/50/75%).
3. For each sample, it loops `d = 0..maxScanDepth`.
4. It breaks immediately when `pixel.r >= whiteThreshold` (current threshold 230).
5. It returns `maxInset`, clamped to minimum `1`.

Key lines:

- `if (pixel.r >= whiteThreshold) break;` at `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:621`
- `inset = d + 1` update at `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:624`
- minimum clamp `return maxInset < 1 ? 1 : maxInset;` at `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:631`

## Confirmed Affected Cells

From fixture grid values containing `|`:

1. Page 2, row 26, col 5
2. Page 4, row 25, col 4

Mapped diagnostic images:

- `page_2_row_26_col_5_raw.png`
- `page_2_row_26_col_5_ocr.png`
- `page_4_row_25_col_4_raw.png`
- `page_4_row_25_col_4_ocr.png`

Visual verification: both raw and OCR images still show a left vertical stroke.

## Runtime-Equivalent Reconstruction Results

A read-only reconstruction reproduced runtime crop math from page-level preprocessed images + grid lines, matching raw crop dimensions exactly.

### Cell A: Page 2, Row 26, Col 5

1. Raw bounds: `L=2037 T=2522 R=2419 B=2614` (382x92)
2. Insets: `top=4 bottom=4 left=1 right=1`
3. Final bounds: `L=2038 T=2526 R=2418 B=2610` (380x84)
4. Matches image size: `page_2_row_26_col_5_raw.png` = 380x84

### Cell B: Page 4, Row 25, Col 4

1. Raw bounds: `L=1683 T=2432 R=2038 B=2523` (355x91)
2. Insets: `top=3 bottom=3 left=1 right=2`
3. Final bounds: `L=1684 T=2435 R=2036 B=2520` (352x85)
4. Matches image size: `page_4_row_25_col_4_raw.png` = 352x85

## Critical Pixel Evidence (Full Page, Pre-Inset, Left Edge)

For each sample y-line, the left-edge sequence (`d=0..10`) is:

### Page 2, Row 26, Col 5 (`left=2037`, y=[2545,2568,2591])

- `237,117,45,18,48,132,207,255,255,255,255`
- `246,138,62,18,42,134,208,255,255,255,255`
- `243,158,86,20,30,117,194,255,255,255,255`

### Page 4, Row 25, Col 4 (`left=1683`, y=[2455,2478,2500])

- `238,153,56,41,42,125,224,255,255,255,255`
- `245,158,58,41,41,121,219,255,255,255,255`
- `252,161,60,38,38,117,219,255,255,255,255`

Interpretation:

1. At `d=0`, all samples are white (>=230).
2. At `d=1..6`, they are dark (<230).
3. Scan logic breaks at `d=0`, never reaching the dark run.
4. Left inset becomes raw `0`, then clamped to `1`.

This precisely explains why a visible left stroke remains.

## Hypotheses Evaluated and Outcome

1. Missing line-width gating disables scan (`hasVWidths/hasHWidths` false): **Rejected for Springfield primary cases**
   - Grid fixtures show width arrays present and count-matching line arrays on all relevant pages.

2. `maxScanDepth=9` insufficient for remaining 2.5-5 px artifacts: **Rejected for these pipe cells**
   - Loop exits at `d=0`; depth is never exercised.

3. Sampling blind spots (25/50/75) miss localized artifacts: **Low likelihood for observed pipe cases**
   - Pipe spans full row height in affected cells; sampled y-lines intersect artifact.

4. Coordinate-space mismatch between scan and image: **Not primary**
   - Reconstruction from page image + line map reproduces runtime crop sizes exactly.

5. First-white termination over non-monotonic edge profile: **Confirmed primary root cause**
   - Direct pixel sequences show white then dark behavior that defeats current loop logic.

## Why This Survived Prior Tuning

Changing `maxScanDepth` addresses only "not far enough" failures.  
This failure mode is "terminates too early," which depth tuning cannot correct.

## Secondary Observations

1. Stage 2B keeps grayscale (no binarization), and OCR receives grayscale crop bytes.
2. Whitespace detection threshold (`r >= 230`) and OCR-visible stroke intensities overlap.
3. This can make thresholding fragile near anti-aliased edges, especially when edge profiles are non-monotonic.

## Final Root Cause Statement

For the surviving Springfield pipe artifacts, `_scanWhitespaceInset` fails because it assumes the first encountered white pixel implies transition into whitespace.  
In actual failing cells, edge pixels are white at `d=0` but darker pixels follow immediately inward (`d=1..6`).  
The current "break-on-first-white" rule therefore terminates prematurely, returns only minimum inset, and leaves a vertical stroke that OCR reads as `|`.

## Investigation Notes

1. No source files were modified during this investigation.
2. Analysis used explorer/worker agents plus read-only scripts and fixture/image inspection.
