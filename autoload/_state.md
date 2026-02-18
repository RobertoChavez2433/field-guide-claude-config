# Session State

**Last Updated**: 2026-02-17 | **Session**: 363

## Current Phase
- **Phase**: Pipeline Architecture — Row Merger Header Fix + Remaining Quality Gaps
- **Status**: Two major fixes landed (adaptive whitespace-scan insets + grid margin fix). Scorecard improved from 31/5/12 to 38/8/2. BLOCKER: row merger doesn't merge consecutive header rows.

## HOT CONTEXT — Resume Here

### What Was Done This Session (363)

#### 1. Implemented Adaptive Whitespace-Scan Insets (RC1 Fix)
- Added `_scanWhitespaceInset` static method to `TextRecognizerV2` (`text_recognizer_v2.dart:582-632`)
- Scans from grid line edge inward until pixel.r >= 230, samples at 3 positions (25/50/75%), takes max, caps at 5px
- Replaced formula-based `(lineWidth/2).ceil()+1` insets at lines 348-367
- **Impact**: Boilerplate rows dropped from 134 → 21. Data rows hit 131 (target). Price continuation jumped from 29 → 114.

#### 2. Fixed Grid Line Detector Page Margin Filter
- Changed `kPageMargin` from 0.05 → 0.01 in `grid_line_detector.dart:21`
- The top horizontal line of the header row on pages 1-5 sits at Y≈0.044, which was filtered out by the 0.05 margin
- Updated test at `stage_2b_grid_line_detector_test.dart:233-246` to use 0.005/0.01 thresholds
- **Impact**: Headers now detected on all 6 pages (17 raw header rows across 6 pages)

#### 3. Updated Golden Test Expectations
- `springfield_golden_test.dart:163`: quality baseline updated from `closeTo(0.794, 0.02)` → `closeTo(0.902, 0.02)`, status from `reviewFlagged` → `autoAccept`

#### 4. Investigated Row Merger — Found BLOCKER
- Row merger (`row_merger.dart:53-57`) passes header rows through individually — no merging of consecutive headers
- Pages 1-5 have 3 header rows each (row grouper splits multi-line header "Item\nNo." into 3 physical rows)
- Result: 17 merged header rows instead of 6 (one logical header per page)
- All other row types merge correctly: data✓, priceContinuation✓, descContinuation✓, boilerplate✓, total✓

#### 5. Upstream Classifier Issue Noted
- ~7 rows on page 1 containing price data (`$334.00`, `$500.00`, `$3,513.00`) classified as boilerplate instead of priceContinuation
- Part of the remaining 21 boilerplate rows — likely RC2 remnants (row grouping splits)

### What Needs to Happen Next

1. **BLOCKER: Merge consecutive header rows** in `row_merger.dart` — when consecutive header rows are on the same page, merge elements into one logical header row. Expected: 17 → 6 headers.
2. **Regenerate fixtures** after merger fix, re-run scorecard
3. **Investigate 21 remaining boilerplate rows** — some contain valid price data misclassified by the classifier (RC2: row grouping splits multi-line cells)
4. **Address Stage 14 Cell Extraction split rows BUG** — header content appearing as orphaned split artifacts
5. **Close the $609K checksum gap** (7.74%) — unit_price OCR gaps on ~28 items

## Blockers

### BLOCKER: Row Merger Does Not Merge Consecutive Headers
- **File**: `row_merger.dart:53-57`
- **Problem**: `case RowType.header` passes through individually, never merges consecutive headers on same page
- **Impact**: 17 header rows instead of 6, inflated merged row count, partial column names in cell extraction
- **Fix**: Check if previous merged row is also header on same page → append elements instead of creating new row
- **Scope**: Only headers affected. Data/continuation/boilerplate/total all work correctly.

## Recent Sessions

### Session 363 (2026-02-17)
**Work**: Implemented adaptive whitespace-scan insets (RC1 fix). Fixed grid line detector kPageMargin 0.05→0.01 (unblocked per-page header detection). Audited row merger — found header merging blocker. Updated golden test expectations.
**Scorecard**: 38 OK / 8 LOW / 2 BUG (was 31/5/12). Quality 0.903. 130 items extracted.
**Decisions**: Per-page header detection works. Label propagation not needed (grid_line method gets 36/36 labels independently). Row merger header fix is next blocker.
**Next**: 1) Fix header merging in row_merger.dart 2) Regenerate fixtures 3) Investigate remaining 21 boilerplate rows.

### Session 362 (2026-02-17)
**Work**: Full root cause analysis of row classifier boilerplate problem. 3 parallel agents researched V3 logic, fixture data, upstream stages. Found RC1: anti-aliased grid line bleed (155/162 pipes at grid line positions). Designed adaptive whitespace-scan inset fix. Verified gray header fill is not a concern via diagnostic images.
**Decisions**: RC1 (pipe artifacts from anti-aliased grid line fringes) is the #1 upstream fix. Implement adaptive whitespace-scan insets in text_recognizer_v2.dart. Cap at 5px, sample 3 positions per edge.
**Next**: 1) Implement whitespace-scan insets 2) Regenerate fixtures 3) Address RC2/RC3 if needed.

### Session 361 (2026-02-17)
**Work**: Regenerated fixtures. Ran stage trace + golden tests (all pass). Scorecard: 31 OK/5 LOW/12 BUG. Identified first upstream BUG at Stage 08 price continuation (47%).
**Decisions**: Debug row_classifier_v3.dart price continuation logic next. Upstream-first approach.
**Next**: Fix price continuation detection in V3 classifier, fix header detection (2/6 pages).

### Session 360 (2026-02-16)
**Work**: Ran scorecard (22 OK/4 LOW/22 BUG). Brainstormed Row Classifier V3 + Column Label fix. Wrote detailed 24-step implementation plan.
**Decisions**: Rewrite classifier (V3), template label propagation, disable anchor correction for grid pages, add row merger stage.
**Next**: Implement plan Phase 1-4.

### Session 359 (2026-02-16)
**Work**: Regenerated fixtures (+4.6% quality, +18 GT matches). Full pipeline diagnostic. Added scorecard test to stage trace. Identified 2 upstream bugs: 4A row classification and 4C column labels.
**Decisions**: Fix upstream stages to 100% before moving downstream.
**Next**: Fix 4A row classification, 4C column labels, row merging.

## Active Plans

### Row Merger Header Fix (BLOCKER — NEXT)
- Merge consecutive header rows on same page in `row_merger.dart`
- Expected: 17 → 6 merged header rows

### Remaining Boilerplate Investigation (AFTER BLOCKER)
- 21 boilerplate rows remain, ~7 contain valid price data
- RC2 (row grouping splits) is likely cause
- May need classifier adjustment or row grouping fix

### Cell-Level OCR Quality Tuning (IN PROGRESS)
- Adaptive whitespace-scan insets DONE (Session 363)
- Grid margin fix DONE (Session 363)
- Scorecard: 38 OK / 8 LOW / 2 BUG

### Phase 4: Cleanup — Workstream 3 PENDING
- Plan: `.claude/plans/2026-02-13-phase-4-cleanup-and-hooks.md`

### PRD 2.0 — R7 NOT STARTED
- PRD: `.claude/prds/pdf-extraction-v2-prd-2.0.md`

## Completed Plans (Recent)
- Adaptive Whitespace-Scan Insets (Session 363 — RC1 fix)
- Grid Line Detector Margin Fix (Session 363 — kPageMargin 0.05→0.01)
- CropUpscaler Red Background Fix (Session 357)
- Cell-Level OCR Implementation (Session 355)
- Diagnostic Image Capture + Fixture Regen (Sessions 353-354)
- Grid Line Detection + Row-Level OCR (Sessions 343-347)
- OCR-Only Pipeline Migration (Sessions 331-338)

## Deferred Plans
- **AASHTOWARE Integration**: `.claude/backlogged-plans/AASHTOWARE_Implementation_Plan.md`

## Reference
- **Archive**: `.claude/logs/state-archive.md` (Sessions 193-362)
- **Defects**: Per-feature files in `.claude/defects/_defects-{feature}.md`
- **Branch**: `main`
- **Springfield PDF**: `C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf`
- **Ground Truth**: `test/features/pdf/extraction/fixtures/springfield_ground_truth_items.json` (131 items, $7,882,926.73, verified)
