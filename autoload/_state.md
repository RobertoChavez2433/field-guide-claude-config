# Session State

**Last Updated**: 2026-02-17 | **Session**: 362

## Current Phase
- **Phase**: Pipeline Architecture — Grid Line Bleed Fix + Row Classifier Debug
- **Status**: Root cause analysis complete. Anti-aliased grid line bleed identified as #1 upstream cause of 134 boilerplate rows. Fix designed (adaptive whitespace-scan insets). Ready to implement.

## HOT CONTEXT — Resume Here

### What Was Done This Session (362)

#### Full Root Cause Analysis of Row Classifier Problems
Used brainstorming skill + 3 parallel research agents to investigate why 134 rows are classified as boilerplate.

**Root Cause Chain (upstream-first):**
1. **RC1 — Grid Line Bleed (MOST UPSTREAM)**: 155 of 162 pipe `|` elements (95.7%) match vertical grid line X positions. Anti-aliased fringes (gray pixels at ~130-170) survive the `(width/2).ceil()+1` crop inset. These `|` elements get mapped to text-semantic columns, making `textPopulated.isNotEmpty`, which blocks the V3 price continuation check (requires `textPopulated.isEmpty`). **~70 rows affected.**
2. **RC2 — Row Grouping Splits Multi-Line Cells**: Y-center clustering (threshold 0.35×median height) splits wrapped descriptions in one grid cell into 2+ rows. Orphaned half loses item number → boilerplate. **~30 rows.**
3. **RC3 — Continuation Cascade**: One boilerplate row breaks the continuation chain for all following rows. **~20 rows.**
4. **RC4 — PSM Mode**: 1.8x threshold too high for multi-line cells at 1.3-1.5x. Medium priority.
5. **RC5 — Header Detection**: Actually correct. Pages 1-5 genuinely have no headers.

#### Designed Fix: Adaptive Whitespace-Scan Insets
Replace formula-based crop insets with actual pixel scanning:
- Scan from grid line center inward until pixel.r >= 230 (white)
- Sample at 3 positions (25%, 50%, 75%) per edge, take max
- Cap at 5px per direction
- Implement in `text_recognizer_v2.dart` lines 348-367

#### Verified Gray Header Fill Is Not A Concern
Checked diagnostic images: preprocessing (grayscale + contrast) converts gray fill to pure white. Scan threshold of 230 is safe.

### What Needs to Happen Next

1. **Implement adaptive whitespace-scan insets** in `text_recognizer_v2.dart` — replace lines 348-367
2. Run tests, regenerate fixtures, measure scorecard impact (expect ~70 boilerplate→priceContinuation)
3. If significant boilerplate remains, address RC2 (grid-aware row grouping) and RC3 (cascade recovery)

## Recent Sessions

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

### Session 358 (2026-02-16)
**Work**: Measured grid line widths in detector, used for precise pixel-based crop insets. Replaced old normalized inset (0.001) with `ceil(lineWidth/2)+1` px. All 807 extraction tests pass.
**Decisions**: Pixel-space insets applied after floor/ceil rounding. 3px fallback for missing width data.
**Next**: Regenerate fixtures, row merging, item# noise assessment.

## Active Plans

### Grid Line Bleed Fix — Adaptive Whitespace-Scan Insets (NEXT)
- Replace formula-based insets in `text_recognizer_v2.dart:348-367` with pixel scanning
- Scan from grid line center until pixel.r >= 230, cap at 5px, sample 3 positions per edge
- Expected impact: ~70 boilerplate rows → priceContinuation

### Row Classifier V3 + Column Label Fix (IN PROGRESS)
- Plan: `.claude/plans/2026-02-16-row-classifier-v3-column-labels.md`
- V3 classifier + row merger + column label propagation done.
- **Current focus**: RC1 (pipe artifacts) is upstream root cause. Fix that first, then reassess RC2 (row grouping) and RC3 (cascade).

### Cell-Level OCR Quality Tuning (BLOCKED — waiting on grid line bleed fix)
- Grid line width measurement + pixel-based insets done (Session 358), but insets insufficient
- Scorecard: 31 OK / 5 LOW / 12 BUG — blocked on grid line bleed → row classification

### Cell-Level OCR Implementation (COMPLETE)
- Plan: `.claude/plans/2026-02-16-cell-level-ocr-plan.md`

### Diagnostic Image Capture (COMPLETE)
- Plan: `.claude/plans/2026-02-16-diagnostic-image-capture.md`

### Phase 4: Cleanup — Workstream 3 PENDING
- Plan: `.claude/plans/2026-02-13-phase-4-cleanup-and-hooks.md`

### PRD 2.0 — R7 NOT STARTED
- PRD: `.claude/prds/pdf-extraction-v2-prd-2.0.md`

## Completed Plans (Recent)
- CropUpscaler Red Background Fix (Session 357 — Problem A root cause)
- Cell-Level OCR Implementation (Session 355 — code done, debugging in 356-357)
- Diagnostic Image Capture + Fixture Regen (Sessions 353-354)
- Grid Line Detection + Row-Level OCR (Sessions 343-347)
- OCR-Only Pipeline Migration (Sessions 331-338)

## Deferred Plans
- **AASHTOWARE Integration**: `.claude/backlogged-plans/AASHTOWARE_Implementation_Plan.md`

## Reference
- **Archive**: `.claude/logs/state-archive.md` (Sessions 193-357)
- **Defects**: Per-feature files in `.claude/defects/_defects-{feature}.md`
- **Branch**: `main`
- **Springfield PDF**: `C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf`
- **Ground Truth**: `test/features/pdf/extraction/fixtures/springfield_ground_truth_items.json` (131 items, $7,882,926.73, verified)
