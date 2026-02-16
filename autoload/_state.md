# Session State

**Last Updated**: 2026-02-15 | **Session**: 350

## Current Phase
- **Phase**: Pipeline Architecture — Row-Strip OCR Implementation
- **Status**: Brainstorming complete. Step 1 (row-strip OCR) approved. Ready to plan implementation.

## HOT CONTEXT — Resume Here

### What Was Done This Session (350)

#### Deep-Dive OCR Brainstorming — COMPLETE
- Traced actual pipeline data through fixtures: 939 elements → 267 rows → 0 headers → 0 regions → 0 columns → 0 items
- Identified TRUE root causes (most upstream first):
  1. Grid lines NOT removed from image before cell cropping
  2. Margin columns (0→5.3%, 94.7→100%) OCR'd, producing garbage
  3. PSM 7 (single line) used on multi-line headers ("Item\nNo.")
  4. Narrow columns (140px) produce garbage even after upscaling
  5. source_dpi metadata broken for crops (reports 31 DPI, actual ~700 effective)
- Researched community best practices: morphological line removal is standard, NOT painting white
- Researched cross-platform OCR: Tesseract is only offline option for iOS+Android+Windows
- Researched cloud OCR: Google Cloud Vision (1000 pages/month FREE), AWS Textract ($0.015/page with native table structure)
- Evaluated opencv_dart: supports all 3 platforms, provides morphological ops, +30-50MB app size
- Evaluated textify package: pure Dart template matching, NOT suitable for our use case

#### Decision: 3-Step Escalation Path
```
Step 1: Row-strip OCR (zero new deps)         ← APPROVED
  └─ Still bad? → Step 2: opencv_dart + morphological line removal
      └─ Still bad? → Step 3: Google Cloud Vision (free tier)
```

#### Brainstorming Plan Saved
- `.claude/plans/2026-02-15-ocr-improvement-brainstorming.md`

### What Needs to Happen Next

**PRIORITY 1: Plan row-strip OCR implementation (Step 1)**
- Modify TextRecognizerV2 to crop full rows instead of cells for grid pages
- Assign text to columns using vertical grid line X-positions
- Also: skip margin columns, use PSM 6 for headers
- Also: grid-aware region detection (Options B/C from earlier brainstorming)

**PRIORITY 2: Implement Step 1**
- Estimated: 1-2 sessions

**PRIORITY 3: Fixture regeneration + accuracy assessment**
- Target: >=80/131 ground truth matches

### Pipeline vs Ground Truth Scoreboard

| Metric | Session 349 | Target |
|--------|-------------|--------|
| Rendering quality | pdfx @ 300 DPI | 300 DPI |
| Grid pages detected | 6/6 | 6 |
| OCR elements | 939 | — |
| Classified rows | 267 (105 data, 0 header) | — |
| Header rows | 0 (OCR fragments) | >=6 |
| Table regions | 0 | >=1 |
| Columns detected | 0 (no regions) | 6 |
| Ground truth matches | 0/131 | >= 80% |

## Recent Sessions

### Session 350 (2026-02-15)
**Work**: Deep OCR brainstorming. Traced actual data through pipeline. Researched community practices (morphological line removal), cross-platform OCR options, cloud OCR pricing, opencv_dart, textify. Established 3-step escalation path.
**Decisions**: Row-strip OCR first (zero deps). opencv_dart if needed. Cloud Vision as last resort. Painting white not recommended — morphological ops are standard but need OpenCV.
**Next**: 1) Plan row-strip OCR implementation 2) Implement 3) Measure accuracy

### Session 349 (2026-02-15)
**Work**: Code review (3 fixes). Fixture regen revealed 0 regions (region detector ignores grid data). Brainstormed grid-aware region detection (Options B/C).
**Decisions**: Renderer works at 300 DPI. Region detection is blocker. Option A rejected.
**Next**: Decide B vs C → superseded by row-strip OCR approach


## Active Plans

### Row-Strip OCR + Escalation Path (PRIMARY)
- Brainstorming: `.claude/plans/2026-02-15-ocr-improvement-brainstorming.md`
- Implementation plan: TBD (next step)

### Grid-Aware Region Detection (SUPERSEDED — folded into row-strip plan)
- Design: `.claude/plans/2026-02-15-grid-aware-region-detection-design.md`
- Options B/C still valid — will be included in row-strip implementation

### Column Semantic Mapping Fix — COMPLETE
- Plan: `.claude/plans/2026-02-15-column-semantic-mapping-fix.md`

### Phase 4: Cleanup — Workstream 3 PENDING
- Plan: `.claude/plans/2026-02-13-phase-4-cleanup-and-hooks.md`

### PRD 2.0 — R7 NOT STARTED
- PRD: `.claude/prds/pdf-extraction-v2-prd-2.0.md`

## Completed Plans (Recent)
- Column Semantic Mapping Fix (Sessions 348-349)
- Grid Line Detection + Row-Level OCR (Sessions 343-347)
- OCR-Only Pipeline Migration (Sessions 331-338)

## Deferred Plans
- **AASHTOWARE Integration**: `.claude/backlogged-plans/AASHTOWARE_Implementation_Plan.md`

## Reference
- **Archive**: `.claude/logs/state-archive.md` (Sessions 193-348)
- **Defects**: Per-feature files in `.claude/defects/_defects-{feature}.md`
- **Branch**: `main`
- **Springfield PDF**: `C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf`
- **Ground Truth**: `test/features/pdf/extraction/fixtures/springfield_ground_truth_items.json` (131 items, $7,882,926.73, verified)
