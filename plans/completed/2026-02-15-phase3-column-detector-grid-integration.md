# Phase 3: ColumnDetectorV2 Grid Line Integration

## Context

Phase 1 added GridLineDetector (Stage 2B-ii.5) which detects horizontal and vertical grid lines per page. Phase 2 modified TextRecognizerV2 to use grid lines for row cropping + PSM 7/4. Phase 3 integrates grid lines into ColumnDetectorV2 as a high-confidence Layer 0 that provides precise column boundaries from grid geometry and semantic assignment from header keyword matching.

Parent plan: `.claude/plans/2026-02-14-grid-line-detection-row-ocr.md` (lines 103-119)

---

## Overview

### Purpose
Add grid line integration to ColumnDetectorV2 as Layer 0 that uses per-page grid boundaries for column geometry and header keyword matching for semantic assignment.

### Scope

**Included**:
- New `_detectFromGridLines()` method (Layer 0) in column_detector_v2.dart
- Per-page independent column detection (each page solves itself)
- Grid boundaries + keyword matching hybrid approach (Option D)
- Fallback: grid boundaries + Layer 1 semantics when per-page keywords fail
- Layers 1-2 still run for diagnostic comparison when Layer 0 succeeds
- Anchor correction runs as validation-only for grid pages
- Pre-task: investigate + fix page 1 grid misclassification in GridLineDetector
- Full test coverage for all column detector layers
- Delete `_detectFromLines()` TODO stub
- Golden test and fixture updates

**Excluded**:
- Image-based Hough line detection (was the stub's original plan)
- Cross-page clustering (each page is independent)
- Changes to other pipeline stages (TextRecognizerV2 changes were Phase 2)

### Success Criteria
- [ ] All grid pages get columns via `grid_line` method at 0.85-0.95 confidence
- [ ] Page 1 correctly classified as grid page
- [ ] Per-page column boundaries match actual grid line positions
- [ ] Semantic headers assigned via keyword matching per page
- [ ] Layers 1-2 diagnostic output captured in StageReport for comparison
- [ ] Full column detector test coverage (all layers)
- [ ] Existing golden/pipeline tests pass with updated baselines

---

## Algorithm: Layer 0 `_detectFromGridLines()`

### Input
- `GridLines? gridLines` — from Stage 2B-ii.5 (per-page horizontal + vertical line positions)
- `DetectedRegions` / `ClassifiedRows` / `UnifiedExtractionResult` — same inputs the detector already receives

### Per-Page Flow

```
For each grid page (gridLineResult.hasGrid == true):

  1. BOUNDARIES: Take that page's verticalLines as column boundaries
     N vertical lines -> N+1 columns
     [0.0 -> line1, line1 -> line2, ..., lineN -> 1.0]

  2. SEMANTICS: Collect OCR elements from this page's header row
     (elements whose Y center falls between horizontalLines[0] and horizontalLines[1])
     For each column boundary pair:
       - Find OCR elements whose X center falls within [startX, endX]
       - Match text against HeaderKeywords.byColumn
       - Assign semantic name if matched

  3. BUILD: Create List<ColumnDef> for this page
     - startX, endX from grid lines
     - headerText from keyword match (or null if no match)
     - confidence: 0.95 if all 6 matched, 0.85 if 4-5, 0.75 if <4

  4. STORE in perPageAdjustments[pageIndex]
```

### Base Column Selection
- `columns` (ColumnMap's required base) = page with highest per-page confidence
- If tie -> lowest page index

### Keyword Failure Fallback (per-page)
When a page's keyword matching scores < 4 matches:
1. Keep grid boundaries (geometry is still precise)
2. Mark semantic assignment as incomplete
3. After Layer 0 completes, Layer 1 `_detectFromHeaders()` runs anyway (for diagnostics)
4. Borrow Layer 1's semantic assignment for pages where Layer 0 keywords failed
5. Confidence for those pages = min(grid_confidence, header_confidence)

### Non-Grid Pages
- Completely skipped by Layer 0
- Flow through Layers 1 -> 2 -> 2c -> fallback as today
- Their results stored alongside grid page results in the same ColumnMap

### Header Row Identification
The "header row" for keyword matching = OCR elements whose Y center falls between `horizontalLines[0]` and `horizontalLines[1]` (the first row band of the grid).

---

## Diagnostic Comparison: Layers 1-2 as Validation

Layer 0 result is **locked as final** for grid pages. Layers 1-2 run afterward and their results are captured in StageReport for testing — not used for the final output.

### Flow

```
detect() entry:
  |
  +- Layer 0: _detectFromGridLines()
  |   Result A: per-page columns for grid pages (LOCKED as final)
  |
  +- Layer 1: _detectFromHeaders()
  |   Result B: header keyword detection (diagnostic only for grid pages)
  |
  +- Layer 2/2c: _detectFromTextAlignment() / _detectFromWhitespaceGaps()
  |   Result C: alignment/gap detection (diagnostic only for grid pages)
  |
  +- Non-grid pages: use best of B/C as their actual result (unchanged behavior)
  |
  +- Layer 3: _correctWithAnchors()
  |   For grid pages: validation only (log agreement, don't override)
  |   For non-grid pages: applies corrections as today
  |
  +- Return ColumnMap + StageReport
```

### StageReport Additions

```dart
metrics: {
  // Existing metrics...

  // NEW: Layer 0 vs Layer 1 comparison
  'grid_layer0_page_count': 5,
  'grid_layer0_avg_confidence': 0.95,
  'layer1_diagnostic_method': 'header_keyword',
  'layer1_diagnostic_confidence': 0.82,

  // Per-page agreement tracking
  'layer0_vs_layer1_boundary_agreement': 0.94,  // % within 1% tolerance
  'layer0_vs_layer1_semantic_agreement': 1.0,    // % same headerText

  // Anchor validation
  'anchor_vs_grid_max_offset': 0.003,
}
```

### When to Remove Diagnostic Layers
Once across multiple test PDFs:
- `layer0_vs_layer1_boundary_agreement` consistently >= 0.90
- `layer0_vs_layer1_semantic_agreement` consistently == 1.0
- `grid_layer0_avg_confidence` consistently >= 0.90

Then add a flag to skip Layers 1-2 for grid pages (future optimization).

---

## Page 1 Grid Misclassification Fix

### Root Cause
Page 1 has dense text in the top 75% and a table in the bottom 25%. The grid detector's vertical line scan is bounded by `horizontalLines.first` to `horizontalLines.last`. Bold headings/underlines in the text region produce false horizontal line candidates, expanding the vertical scan region to ~75%+ of the page. Actual vertical grid lines only span the bottom 25%, so their coverage drops below the 40% threshold.

### Fix: Horizontal Line Density Filtering

In `_detectGridLinesIsolate()`, after initial horizontal line detection:
1. Compute spacing between consecutive horizontal lines
2. Find the largest group of lines with consistent spacing (within 50% of median spacing)
3. Discard outlier horizontal lines far from this dense cluster
4. Use the filtered set for vertical scan bounding

**Guard**: Only activate when raw horizontal lines span >60% of page height but densest cluster spans <50%. Otherwise use raw set as today (prevents regression on pages 2-6 where tables fill most of the page).

### Verification
- Page 1: ~7 horizontal lines + ~7 vertical lines, hasGrid = true
- Pages 2-6: unaffected (tables span most of the page, filter doesn't trigger)

---

## Test Plan

### Existing Coverage (stage_4c_column_detector_test.dart, 1754 lines)
- Header keyword matching (6 tests)
- Multi-row header assembly (3 tests)
- Column boundary calculation (4 tests)
- Fallback to standard ratios (3 tests)
- Missing column inference (3 tests)
- Text alignment clustering (2 tests)
- Whitespace gap detection (2 tests)
- Empty/edge cases (3 tests)
- Anchor correction (3 tests)
- StageReport validation (3 tests)

### New Tests — Layer 0 Grid Line Detection

| Test | Input | Expected |
|------|-------|----------|
| Grid page produces columns from vertical lines | GridLines with 6 verticals + OCR header | 7 columns, boundaries match lines, method='grid_line' |
| Semantic assignment via keyword matching | OCR elements in grid column bands | Correct headerText per column |
| Per-page independence | 3 grid pages, different line positions | perPageAdjustments has 3 entries |
| Base columns from highest confidence page | Pages at 0.95, 0.85, 0.90 | Base from 0.95 page |
| Confidence tiers: 6/6, 4/6, 2/6 | Varying keyword matches | 0.95, 0.85, 0.75 |
| Keyword failure borrows Layer 1 semantics | Garbled header OCR | Grid boundaries + Layer 1 headerText |
| Non-grid pages skip Layer 0 | Mix of grid/non-grid | Non-grid use Layer 1/2 |
| No grid lines -> full fallback | Empty GridLines | Layers 1-2 handle everything |
| N vertical lines -> N+1 columns | 4 vertical lines | 5 columns including margins |

### New Tests — Diagnostic Comparison

| Test | Input | Expected |
|------|-------|----------|
| StageReport captures both paths | Grid pages, both paths run | Report has agreement metrics |
| Boundary agreement metric | Layer 0 and Layer 1 within 1% | Agreement near 1.0 |
| Semantic agreement metric | Same headers both layers | Agreement = 1.0 |
| Anchor validation-only for grid pages | Grid columns + anchors | Log agreement, don't override |

### Grid Line Detector Fix Tests (stage_2b_grid_line_detector_test.dart)

| Test | Input | Expected |
|------|-------|----------|
| Table in bottom quarter with text above | Synthetic image: dark rows + grid | hasGrid = true, lines from table only |
| Density filtering activates correctly | Scattered lines + dense cluster | Dense cluster for vertical bounding |
| No filtering when table fills page | Grid spanning 90% | Same as today (no regression) |

### Golden Test Updates

**springfield_golden_test.dart**:
- Column count assertion -> update to new count
- Quality score -> update baseline
- Item match rate thresholds -> raise
- Numeric extraction coverage -> update

**stage_trace_diagnostic_test.dart**:
- Stage 4C column count -> update to grid_line output
- Add Layer 0 vs Layer 1 diagnostic printout
- Pipeline failure summary -> reflect new detection quality

### Fixture Regeneration

After implementation, regenerate via `tool/generate_springfield_fixtures.dart`:
- `springfield_column_map.json` (grid_line method + perPageAdjustments)
- `springfield_cell_grid.json` (better column boundaries)
- `springfield_parsed_items.json` (more items)
- `springfield_processed_items.json` (more complete items)
- `springfield_quality_report.json` (improved score)

---

## File Inventory

### Modified (8 files)

| File | Change | Phase |
|------|--------|-------|
| `lib/.../stages/grid_line_detector.dart` | Horizontal line density filtering | A |
| `lib/.../stages/column_detector_v2.dart` | Layer 0, delete stub, diagnostics, anchor validation mode | B |
| `test/.../stages/stage_2b_grid_line_detector_test.dart` | Density filtering tests | A |
| `test/.../stages/stage_4c_column_detector_test.dart` | Layer 0 + diagnostic tests (~13 new) | B |
| `test/.../golden/springfield_golden_test.dart` | Update regression baselines | C |
| `test/.../golden/stage_trace_diagnostic_test.dart` | Update Stage 4C expectations + diagnostics | C |
| `test/.../helpers/mock_stages.dart` | Add MockGridLineDetector if needed | B |
| `tool/generate_springfield_fixtures.dart` | Ensure grid_lines fixture included | C |

### Regenerated (5 fixtures)

| File | Why |
|------|-----|
| `springfield_column_map.json` | grid_line method + perPageAdjustments |
| `springfield_cell_grid.json` | Better column boundaries |
| `springfield_parsed_items.json` | More items parsed |
| `springfield_processed_items.json` | More complete items |
| `springfield_quality_report.json` | Improved quality score |

### No New Files
All changes are modifications to existing files.

---

## Implementation Phases

### Phase A: Grid Line Detector Fix (Page 1)
1. Add horizontal line density filtering to `_detectGridLinesIsolate()`
2. Add guard: only activate when lines span >60% but cluster spans <50%
3. Add tests for density filtering (3 tests)
4. Verify page 1 classifies as grid page
5. Verify pages 2-6 unaffected

**Verify**: `pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_2b_grid_line_detector_test.dart"`

### Phase B: Column Detector Layer 0
1. Delete `_detectFromLines()` stub (lines 524-550)
2. Add `GridLines? gridLines` parameter to `detect()`
3. Implement `_detectFromGridLines()`:
   - Per-page: grid boundaries + keyword matching in header row band
   - Base columns from highest confidence page
   - Keyword failure -> borrow Layer 1 semantics
4. Wire diagnostic comparison:
   - Layer 0 result locked, Layers 1-2 still run
   - StageReport captures agreement metrics
5. Anchor correction: validation-only mode for grid pages
6. Add all Layer 0 and diagnostic tests (13 tests)

**Verify**: `pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_4c_column_detector_test.dart"`

### Phase C: Golden Updates & Fixture Regeneration
1. Regenerate all Springfield fixtures
2. Update `springfield_golden_test.dart` baselines
3. Update `stage_trace_diagnostic_test.dart` expectations
4. Run full extraction test suite

**Verify**: `pwsh -Command "flutter test test/features/pdf/extraction/"`

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Density filtering breaks pages 2-6 | Low | High | Guard: only activate when lines span >60% but cluster <50%. Pages 2-6 tables fill page, filter won't trigger. |
| Header row band misidentified | Medium | Medium | If first grid row isn't header, keywords fail and Layer 1 semantics take over. |
| Grid vertical lines misaligned | Low | High | Lines are pixel-detected from preprocessed image. Preprocessor handles skew/rotation. |
| Diagnostic comparison adds latency | Low | Low | Layers 1-2 are ~50ms total. Skip flag added later. |
| Fixture regeneration breaks tests | Medium | Medium | Regenerate atomically in Phase C. Full suite before commit. |
| detect() signature change breaks callers | Low | Medium | GridLines? is optional, default null. Existing callers unchanged. |

---

## Decisions Log

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Replace `_detectFromLines()` stub entirely | Clean code. Original Hough transform plan superseded by GridLineDetector. |
| 2 | Grid boundaries + header keyword matching (Option D) | Grid solves geometry, keywords solve semantics. Reuses existing HeaderKeywords infrastructure. |
| 3 | Per-page independent, no cross-page clustering | Each page has own grid lines + header row. Self-sufficient. |
| 4 | Layers 1-2 run as diagnostics (Option B) | Validate Layer 0 correctness. Capture I/O for both paths. Optimize later when confident. |
| 5 | Anchor correction = validation-only for grid pages | Grid lines already per-page precise. Log agreement, don't override. |
| 6 | Grid boundaries + Layer 1 semantics on keyword failure | Keep precise geometry even when OCR garbles headers. |
| 7 | Page 1 fix via density filtering | Text above table creates false horizontal lines. Density filtering isolates real table cluster. |
