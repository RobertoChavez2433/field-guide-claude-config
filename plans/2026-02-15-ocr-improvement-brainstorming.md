# OCR Improvement Brainstorming — Session 350

**Status**: BRAINSTORMING COMPLETE — Step 1 approved for implementation
**Created**: 2026-02-15

## Problem Statement

The cell-cropped OCR pipeline produces 0/131 ground truth matches on Springfield because:
1. Grid lines are NOT removed from images before cell cropping — grid pixels confuse Tesseract
2. Margin columns (0→5.3% and 94.7→100%) are OCR'd, producing garbage ("IB", "IR", "IN")
3. Multi-line headers ("Item\nNo.") get PSM 7 (single line) — reads one line, fragments text
4. Narrow columns (5-11% page width, ~140px at 300 DPI) produce garbage even after upscaling to 300px
5. source_dpi metadata is misleading (31 DPI reported for ~700 effective DPI crops)

## Root Cause (Most Upstream)

**`_computeCellRegions` in text_recognizer_v2.dart:525** — the decision to crop individual cells is the architectural bottleneck. Narrow cells simply don't have enough pixels for reliable Tesseract OCR, and grid line contamination at cell boundaries compounds the problem.

## Research Findings

### Cell Cropping Is Standard — But Preprocessing Matters
- Per-cell OCR is used by img2table, OpenCV+Tesseract tutorials, etc.
- BUT all working implementations include grid line removal (morphological operations)
- The Dart `image` package cannot do morphological operations
- `opencv_dart` (pub.dev) supports iOS/Android/Windows but adds ~30-50MB

### Community Does NOT Recommend "Paint White" for Line Removal
- Morphological operations are the standard (erosion + dilation to isolate lines by structure)
- Painting white damages text touching lines, misses anti-aliased edges
- Even Leptonica (Tesseract's own library) uses a 6-step morphological process
- Sources: OpenCV docs, Leptonica docs, multiple GitHub repos, academic papers

### Tesseract Limitations for Tables
- Official docs: "Tesseract has a problem recognizing text/data from tables without custom segmentation"
- Character x-height must be 20+ pixels for reliable results
- PSM 7 (single line) is wrong for multi-line cells — PSM 6 (block) or PSM 8 (single word) better

### Cross-Platform OCR Options
- **Tesseract (flusseract)**: Only offline OCR that works on iOS + Android + Windows
- **Google ML Kit**: Excellent but iOS + Android only (no Windows)
- **Apple Vision**: iOS only
- **PaddleOCR**: Unmaintained Flutter binding (2021)
- **Textify**: Pure Dart template matching — requires clean images, won't work for our use case

### Cloud OCR Options (sync-time fallback)
- **Google Cloud Vision**: 1,000 pages/month FREE. Each page = 1 unit. No structured table output.
- **AWS Textract**: $0.015/page, returns structured TABLE/CELL data natively. Best for tables.
- **Google Document AI**: $0.03/page, tables + key-value pairs. Most expensive.

## Decision: 3-Step Escalation Path

```
Step 1: Row-strip OCR (zero new deps)         ← APPROVED FOR IMPLEMENTATION
  ├─ Works? → Done
  └─ Still bad? →
      Step 2: Add opencv_dart + morphological line removal
        ├─ Works? → Done
        └─ Still bad? →
            Step 3: Google Cloud Vision (sync-time fallback, free tier)
              └─ Works? → Done
```

### Step 1: Row-Strip OCR (NEXT)
- Crop full rows between horizontal grid lines (full page width)
- Tesseract gets wide image with context — sidesteps narrow column problem
- Assign text to columns afterward using vertical grid line X-positions
- Also: skip margin columns, use PSM 6 for header rows
- **Zero new dependencies**

### Step 2: opencv_dart + Morphological Line Removal (IF NEEDED)
- Add `opencv_dart` package (~30-50MB, supports all 3 platforms)
- Proper morphological operations: directional opening to isolate grid lines, subtract from image
- Handles anti-aliased edges, text touching lines, sub-pixel artifacts
- Community-standard approach

### Step 3: Google Cloud Vision (IF NEEDED)
- Send full page images during sync
- 1,000 pages/month free — covers typical usage
- Better OCR quality than Tesseract
- Still need to map text to columns using grid coordinates
- OR use AWS Textract ($0.09/document) for native table structure

## Related Plans
- Grid-aware region detection: `.claude/plans/2026-02-15-grid-aware-region-detection-design.md`
- Column semantic mapping fix: `.claude/plans/2026-02-15-column-semantic-mapping-fix.md` (COMPLETE)

## Key Files
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart` — cell cropping logic
- `lib/features/pdf/services/extraction/shared/crop_upscaler.dart` — crop upscaling
- `lib/features/pdf/services/extraction/stages/grid_line_detector.dart` — grid detection
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` — pipeline wiring
- `test/features/pdf/extraction/fixtures/springfield_unified_elements.json` — current OCR output
- `test/features/pdf/extraction/fixtures/springfield_ground_truth_items.json` — 131 target items
