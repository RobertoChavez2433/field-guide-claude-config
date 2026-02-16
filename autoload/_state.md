# Session State

**Last Updated**: 2026-02-16 | **Session**: 356

## Current Phase
- **Phase**: Pipeline Architecture — Cell-Level OCR Debugging
- **Status**: Cell-level OCR IS implemented and running. Fixtures regenerated. Multiple potential problems identified — need investigation plan before fixing.

## HOT CONTEXT — Resume Here

### What Was Done This Session (356)

#### Regenerated Fixtures with Cell-Level OCR (first time!)
- Cell-level OCR was already implemented in working tree (`_recognizeWithCellCrops`) but **fixtures had never been regenerated** with it
- Old fixtures were from row-strip era — showing 284 elements, 3071x142 crops
- Ran: `flutter test integration_test/generate_golden_fixtures_test.dart -d windows --dart-define=SPRINGFIELD_PDF=...`
- New fixtures: 805 OCR elements, 1596 diagnostic images, 261 classified rows

#### Stage Trace Results (Cell-Level OCR)

| Metric | Row Strips (old) | Cell Crops (new) | Target |
|--------|-----------------|------------------|--------|
| OCR elements | 284 | **805** | ~780 |
| Diagnostic images | 278 (row strips) | **1596** (cell crops) | — |
| Data rows classified | 4 | **85** | ~131 |
| Grid rows in cell grid | 47 | **236** | ~131 |
| Rows with price data | 7 | **126** | ~131 |
| unitPrice populated | 6.4% | **45.8%** | ~100% |
| bidAmount populated | 12.8% | **50.8%** | ~100% |
| Parsed items | 32 | **1** | ~131 |
| GT matches | 26/131 | **0/131** | >= 80% |

Cell-level OCR massively improved element count and price recognition.
BUT parsed items **dropped to 1** because of column labeling failure.

#### Potential Problems Identified (NOT YET CONFIRMED — NEED INVESTIGATION)

**Problem A: Red Background on ALL Upscaled Crops**
- Visually confirmed: raw cell crops are perfect grayscale (black text, white bg)
- After CropUpscaler pads them: **bright RED background** with black text
- `crop_upscaler.dart:71`: `img.Image()` defaults to RGBA, but input crops are 1-channel grayscale from `image_preprocessor_v2.dart:229` (`convert(numChannels: 1)`)
- `img.fill(padded, color: img.ColorRgb8(255, 255, 255))` on 1-channel image — unclear if R=255 maps to luminance=255 or just red channel
- `img.compositeImage()` compositing 1-channel onto RGBA — may only write to R channel
- **This affects EVERY cell crop sent to Tesseract** — all 1056 cells per attempt
- Images to inspect: `diagnostic_images/page_0_row_02_col_0_ocr.png` (red), `page_0_row_02_col_0_raw.png` (clean)
- Needs: Test what `image` package does with mixed-channel fill + composite. May need `numChannels: resized.numChannels` on padded image or convert crop to RGB before padding.

**Problem B: DPI Defaults to 300, Not 400**
- `pipeline_config.dart:85`: `this.ocrDpi = 300` — default is 300 DPI
- Fixture generator uses `const PipelineConfig()` with no override
- Re-extraction strategy bumps to 400 DPI on retry, but first attempt is 300
- Previous session (354) showed 400 DPI — may have been a re-extraction attempt
- Needs: Verify if we want 400 as default or if 300 is intentional for performance

**Problem C: source_dpi Calculation is Wrong for Cell Crops**
- `tesseract_engine_v2.dart:276`: `_computeSourceDpi()` divides crop pixel size by FULL PAGE point size
- Item# cell: 320px crop / 613pt page = scale 0.52 → 72 * 0.52 = **25 DPI** (wrong)
- Should divide by the cell's physical portion of the page, not the whole page
- This is **metadata only** — doesn't affect Tesseract's OCR processing
- BUT could affect downstream coordinate transforms if anything uses source_dpi
- Needs: Trace if source_dpi is used anywhere for coordinate math or just reporting

**Problem D: Column Semantic Labeling Wrong**
- Column detector labels: `description, description, quantity, quantity, unitPrice, bidAmount`
- Should be: `itemNumber, description, unit, quantity, unitPrice, bidAmount`
- No `itemNumber` column → RowParser skips all rows → 1 parsed item
- The header row OCR on page 0 may not be producing "Item No." text for col 0
- Col 0 is narrow (140px raw, 320px upscaled) — possibly header text unreadable
- Needs: Check col 0 header crop images, check column detector's header matching logic

**Problem E: Item# Column (col 0) Nearly Empty**
- Only 19/236 (8.1%) of grid rows have an item number
- Raw crops show clear digits ("1", "2", "8", "11") — human-readable
- After upscaling to red-background image, OCR may fail to read them
- Could be Problem A (red bg kills OCR) or could be OCR config issue
- Needs: Fix Problem A first, then re-evaluate item# recognition rate

#### Critical Insight from This Session
- **Sessions 342-355 were debugging row-strip OCR** — but cell-level OCR was already implemented and uncommitted
- Fixtures were never regenerated after cell-level OCR was coded
- This session finally ran the pipeline with cell-level OCR and revealed a new set of problems (A-E above) that are DIFFERENT from the row-strip problems

### What Needs to Happen Next

**PRIORITY 1: Investigate and fix Problem A (red background)**
- This potentially affects all OCR results. Fix it first, regenerate, then see what improves.
- Need to understand `image` package behavior with mixed channel types

**PRIORITY 2: Set DPI to 400 (Problem B)**
- One-line change in pipeline_config.dart
- Regenerate to see if higher DPI helps item# column

**PRIORITY 3: Fix column semantic labeling (Problem D)**
- After A+B are fixed and fixtures regenerated, check if col 0 now has item numbers
- If yes, column detector may self-correct. If no, fix labeling logic.

**DO NOT start fixing until a plan is approved.**

## Recent Sessions

### Session 356 (2026-02-16)
**Work**: Regenerated fixtures with cell-level OCR (first time). Ran stage trace. Found 5 potential problems: red background on upscaled crops, DPI default 300 not 400, source_dpi calc wrong for crops, column labels wrong, item# column empty. Visually confirmed red background on diagnostic images.
**Decisions**: None yet — investigation only. All changes reverted.
**Next**: 1) Plan investigation of Problem A (red bg) 2) Fix DPI default 3) Regenerate and reassess

### Session 355 (2026-02-16)
**Work**: Systematic debugging of stage trace diagnostic. Inspected OCR strip images — confirmed perfectly readable. Root cause: PSM 7 on full-row strips can't handle grid lines. Designed cell-level OCR plan.
**Decisions**: Cell-level OCR is the fix. Grid line inset prevents previous cell-cropping failure.
**Next**: Implement cell-level OCR (was already done in working tree)

### Session 354 (2026-02-16)
**Work**: Regenerated fixtures with ROW-STRIP code (not cell-level). 27 items, 26/131 GT matches (20%).
**Decisions**: Row classifier is #1 blocker.
**Next**: Fix row classifier (superseded by cell-level OCR findings)

### Session 353 (2026-02-16)
**Work**: Implemented diagnostic image capture system. 14 JSON fixtures, onDiagnosticImage callback.
**Decisions**: Raw images only. Images gitignored.

### Session 352 (2026-02-15)
**Work**: Traced pipeline failure cascade. 0 header rows → 0 regions → everything empty.
**Decisions**: Synthetic regions is Priority 1.

## Active Plans

### Cell-Level OCR Debugging (THIS SESSION — IN PROGRESS)
- Cell-level OCR code exists but has problems A-E listed above
- No plan file yet — needs planning session

### Cell-Level OCR Implementation (COMPLETE — code exists in working tree)
- Plan: `.claude/plans/2026-02-16-cell-level-ocr-plan.md`
- Code is implemented but has issues found this session

### Diagnostic Image Capture (COMPLETE)
- Plan: `.claude/plans/2026-02-16-diagnostic-image-capture.md`

### Phase 4: Cleanup — Workstream 3 PENDING
- Plan: `.claude/plans/2026-02-13-phase-4-cleanup-and-hooks.md`

### PRD 2.0 — R7 NOT STARTED
- PRD: `.claude/prds/pdf-extraction-v2-prd-2.0.md`

## Completed Plans (Recent)
- Cell-Level OCR Implementation (Session 355 — code done, debugging in 356)
- Diagnostic Image Capture + Fixture Regen (Sessions 353-354)
- Grid Line Detection + Row-Level OCR (Sessions 343-347)
- OCR-Only Pipeline Migration (Sessions 331-338)

## Deferred Plans
- **AASHTOWARE Integration**: `.claude/backlogged-plans/AASHTOWARE_Implementation_Plan.md`

## Reference
- **Archive**: `.claude/logs/state-archive.md` (Sessions 193-350)
- **Defects**: Per-feature files in `.claude/defects/_defects-{feature}.md`
- **Branch**: `main`
- **Springfield PDF**: `C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf`
- **Ground Truth**: `test/features/pdf/extraction/fixtures/springfield_ground_truth_items.json` (131 items, $7,882,926.73, verified)
