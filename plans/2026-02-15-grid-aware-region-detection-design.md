# Grid-Aware Region Detection Design

**Status**: BRAINSTORMING (Phase 2 — exploring options)
**Created**: 2026-02-15 Session 349
**Problem**: Region detector requires header rows, but cell-cropped OCR produces garbage fragments that can't match header keywords → 0 regions → 0 items extracted.

## Problem Analysis

### Root Cause Chain
1. PageRendererV2 renders at 300 DPI (2558x3295) — WORKING
2. GridLineDetector detects 6 grid pages with correct grid lines — WORKING
3. TextRecognizerV2 crops cells, runs OCR per cell — produces fragments ("IB" instead of "Item No.")
4. RowClassifierV2 needs 3+ header keywords — "IB or | [" matches 0 → classified as `unknown`
5. RegionDetectorV2 needs `RowType.header` rows — 0 headers → 0 regions
6. ColumnDetectorV2 needs regions — 0 regions → 0 columns → 0 items

### Key Insight
The grid line detector ALREADY KNOWS which pages are tables (6/6 pages have grids). But this information is never consumed by the region detector. The pipeline has the answer but doesn't use it.

### Current Pipeline Data Flow
```
Stage 2B-ii.5: GridLineDetector → GridLines (grid pages, horizontal/vertical lines)
Stage 2B-iii:  TextRecognizerV2 → elements (uses gridLines for cell cropping)
Stage 4A:      RowClassifierV2  → ClassifiedRows (NO grid awareness)
Stage 4B:      RegionDetectorV2 → DetectedRegions (NO grid awareness, needs headers)
Stage 4C:      ColumnDetectorV2 → ColumnMap (HAS gridLines, but needs regions)
```

### What the Grid Provides
Per page with `hasGrid == true`:
- `horizontalLines`: normalized Y positions (e.g., [0.071, 0.099, 0.127, ...])
- `verticalLines`: normalized X positions
- `confidence`: 1.0

From horizontal lines we can derive:
- Table start Y: first horizontal line
- Table end Y: last horizontal line
- Row count: horizontalLines.length - 1

## Option B: Grid+Header Hybrid (in Region Detector)

**Concept**: Region detector gains `gridLines` parameter. Grid pages → auto-create regions from grid bounds. Non-grid pages → existing header-row scan.

### Changes Required
1. `RegionDetectorV2.detect()` — add optional `GridLines?` parameter
2. New `_createGridRegions()` — grid bounds → TableRegion per page
3. `extraction_pipeline.dart:473` — pass `gridLines` to region detector
4. Existing header-scan code untouched

### Region Creation from Grid
```dart
// For each grid page:
TableRegion(
  startPageIndex: pageIndex,
  endPageIndex: pageIndex,  // Grid = per-page, not cross-page
  startY: gridPage.horizontalLines.first,
  endY: gridPage.horizontalLines.last,
  headerRowIndices: [],  // Grid doesn't know which row is header
)
```

### Open Questions
- Multi-page tables: Grid detection is per-page. Should adjacent grid pages merge into one region?
- Missing headerRowIndices: Downstream code may expect header indices. Need to verify.
- Priority: When a page has BOTH grid data AND header rows, which wins?

### Pros
- Additive change (no existing code modified)
- Region detector = single source of truth for "where are the tables"
- Non-grid PDFs continue working exactly as before

### Cons
- headerRowIndices empty for grid regions
- Two code paths in region detector
- Region detector's purpose blurs (grid + header signals)

## Option C: Pipeline-Level Split (Grid Pages Skip Region Detection)

**Concept**: Pipeline becomes grid-aware. Grid pages skip region detection entirely; pipeline creates synthetic regions from grid bounds. Region detector only handles non-grid pages.

### Changes Required
1. `extraction_pipeline.dart` — conditional branching after Stage 4A
2. Synthetic `DetectedRegions` created from `GridLines` for grid pages
3. Merge synthetic + detected regions for downstream stages
4. Region detector unchanged

### Pros
- Clean separation of grid path vs header path
- Region detector stays focused on header-based detection
- Pipeline orchestration is explicit about the split

### Cons
- Pipeline gets branching logic
- Must handle mixed documents (some pages grid, some not)
- May need to reconcile two region sources

## Decision Needed

User to decide between Option B and Option C in next session. Key question: should the region detector be the single place that creates regions (Option B), or should the pipeline handle the split (Option C)?

## Constraints (from pdf-v2-constraints.md)
- OCR-only routing (no hybrid native/OCR strategies)
- No V1 imports in V2 code
- No legacy compatibility flags

## Related Files
- `lib/features/pdf/services/extraction/stages/region_detector_v2.dart`
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`
- `lib/features/pdf/services/extraction/models/detected_regions.dart`
- `lib/features/pdf/services/extraction/models/grid_lines.dart` (GridLines model)
