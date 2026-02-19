# Row-Strip OCR Implementation Plan — Full Package

**Status**: APPROVED — Ready for implementation
**Created**: 2026-02-15 (Session 351)
**Parent**: `.claude/plans/2026-02-15-ocr-improvement-brainstorming.md` (Step 1 of 3-step escalation)

## Overview

Modify 4 pipeline stages for grid pages to replace cell-level OCR with row-strip OCR:

| Change | Stage | What Happens |
|--------|-------|-------------|
| **Row-strip OCR** | 2B-iii (TextRecognizer) | Crop full rows instead of cells. Tesseract gets wide images with context. |
| **Grid-aware regions** | 4B (RegionDetector) via pipeline | Grid pages auto-create synthetic regions from grid bounds. No header detection needed. |
| **Skip margins** | 2B-iii (TextRecognizer) | Don't OCR columns at page edges (0→first vertical, last vertical→1.0). |
| **Fix PSM** | 2B-iii (TextRecognizer) | Use PSM 6 (block) for header rows, PSM 7 (line) for data rows. |

**Non-grid pages are completely unaffected** — all existing logic continues to work.

**Post-OCR column assignment**: After row-strip OCR, assign text to columns using vertical grid line X-positions from the existing `GridLineResult`.

## Phase 1: Row-Strip OCR in TextRecognizerV2

### Current Flow (cell cropping)
```
Grid lines → _computeCellRegions() → (rows × columns) cells → OCR each cell → map coords back
```

### New Flow (row-strip)
```
Grid lines → _computeRowStrips() → rows only → OCR each row → map coords back
```

### Key Method: `_computeRowStrips()`

**Input**: `GridLineResult` for the page (horizontal lines, vertical lines)

**Logic**:
1. Sort horizontal lines ascending (already sorted from grid detector)
2. Get margin boundaries: `leftMargin = verticalLines.first`, `rightMargin = verticalLines.last`
3. For each consecutive pair of horizontal lines `(h[i], h[i+1])`:
   - Create strip: `Rect(leftMargin, h[i], rightMargin, h[i+1])`
   - This excludes left/right margin columns automatically
4. Return list of `_RowStrip(rowIndex, bounds)`

**Example** (Springfield page 1, 7 vertical lines):
- Vertical lines: `[0.049, 0.105, 0.456, 0.543, 0.658, 0.797, 0.947]`
- Left margin: `0.049`, Right margin: `0.947`
- Each row strip spans X: `0.049 → 0.947` (89.8% of page width vs. individual cells at 5-35%)

### PSM Selection

| Row | PSM | Rationale |
|-----|-----|-----------|
| First row (index 0) | PSM 6 (block) | Headers are multi-line ("Item\nNo.") |
| All other rows | PSM 7 (single line) | Data rows are single-line values |

Replaces current `_determineRowPsm()` height heuristic that never triggers on uniform grids.

### Upscaling

Row strips ~900px wide at 300 DPI — well above 300px `kMinCropWidth` threshold. **No upscaling triggered** for width. Height may trigger for thin rows (<40px), which is correct.

### Coordinate Mapping

Same 2-step pattern as today:
1. `CoordinateNormalizer.fromOcrPixels()` — Tesseract pixels → normalized within crop (0.0–1.0)
2. `CoordinateNormalizer.fromCropRelative()` — crop-relative → page-relative using strip bounds

**Example**: Tesseract finds "MOBILIZATION" at x=120 in a 900px-wide strip
- Step 1: `120/900 = 0.133` (normalized within strip)
- Step 2: Strip starts at x=0.049, width=0.898 → page x = `0.049 + (0.133 × 0.898) = 0.169`
- Result: element at page x=0.169, falls in Description column (0.105–0.456)

**No changes to CoordinateNormalizer needed.**

### Key Files Modified
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
  - Replace `_recognizeWithCellCropping()` with `_recognizeWithRowStrips()`
  - Replace `_computeCellRegions()` with `_computeRowStrips()`
  - Update PSM selection logic
  - Update metrics (`cells_cropped` → `rows_ocr'd`)

## Phase 2: Grid-Aware Synthetic Regions (Pipeline-Level, Option C)

### The Problem

Region detector scans for HEADER rows → finds none (OCR fragments) → 0 regions → 0 columns → 0 items. Entire downstream pipeline starves.

### The Fix

Grid pages don't need header detection — the grid itself defines table boundaries. Create synthetic regions at pipeline level.

### Implementation: `_createSyntheticRegions()`

**Location**: `extraction_pipeline.dart`

**Logic per grid page**:
```
startY = horizontalLines.first    (e.g., 0.0715 on page 1)
endY   = horizontalLines.last     (e.g., 0.8303 on page 1)
headerRowIndices = [0]            (first row between lines 0-1 is always the header)
```

**Output**: `TableRegion` per grid page.

### Pipeline Branching

```
After Stage 4A (row classification):

  Grid pages?  ──YES──→ _createSyntheticRegions(gridLines)
       │
       NO
       │
       ▼
  RegionDetectorV2.detect(classifiedRows)  ← existing logic, untouched
       │
       ▼
  Merge both region sources into DetectedRegions
```

**Mixed documents**: Both paths run, results merged. Each `TableRegion` carries its own page indices.

### Header Row Handling

Synthetic header (row index 0) tells downstream:
- **Column detector**: Extract header text from row 0 for semantic identification
- **Row parser**: Skip row 0 when parsing data items
- **Cell extractor**: Include row 0 but mark as header

### What Stays Unchanged
- `RegionDetectorV2` — zero modifications
- `ColumnDetectorV2` Layer 0 — already reads grid lines directly
- Stage 4A row classification — still runs but grid pages don't depend on it for regions

### Key Files Modified
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`
  - Add `_createSyntheticRegions()` method
  - Add pipeline branching after Stage 4A
  - Add region merging for mixed documents

## Phase 3: Column Assignment from Grid Lines

### The Approach

After row-strip OCR, each `OcrElement` has a page-normalized bounding box. Stage 4D (CellExtractor) assigns elements to columns:

```
For each element in a row:
  Find which column boundary pair (startX, endX) contains element.xCenter
  Assign element to that column's cell
```

### Edge Cases

| Case | Resolution |
|------|-----------|
| Element spans two columns | Assign to column containing `xCenter` |
| Element outside all columns | Discard (margin garbage) |
| No elements in a column | Empty cell (e.g., blank quantity) |
| Element exactly on boundary | Assign to right column (endX exclusive) |

### Key Files Modified
- Stage 4D cell extractor (if it needs changes for wider elements)
- May be minimal — Stage 4D already collects elements within column boundaries

## Testing Strategy — Stage-by-Stage Data Capture

### Fixture Chain (Input → Output at Every Stage Boundary)

Each stage gets its own fixture pair. Regenerate full chain after implementation.

| Stage | Input Fixture | Output Fixture | What We Verify |
|-------|--------------|----------------|----------------|
| 2B-ii.5 → 2B-iii | `springfield_grid_lines.json` | `springfield_unified_elements.json` | Row-strip OCR produces readable text, not garbage |
| 2B-iii → 3 | `springfield_unified_elements.json` | (validated elements) | All elements normalized 0.0–1.0, valid confidence |
| 3 → 4A | Validated elements | `springfield_classified_rows.json` | Header rows detected (>=6), data rows correct |
| 4A → 4B | Classified rows + grid lines | `springfield_detected_regions.json` | >=1 region per grid page, synthetic regions have headerRowIndices |
| 4B → 4C | Detected regions + grid lines | `springfield_column_map.json` | 6 columns, correct semantics, no margin columns |
| 4C → 4D | Column map + elements | `springfield_cell_grid.json` | Cells populated, elements assigned to correct columns |
| 4D → 4E | Cell grid + column map | `springfield_parsed_items.json` | Item numbers, descriptions, dollar amounts parsed |
| 4E → 5 | Parsed items | `springfield_processed_items.json` | Confidence scores, format validation |

### Contract Tests (Stage Boundary Validation)

Update each existing contract test:

| Test File | Validates |
|-----------|-----------|
| `stage_3_to_4a_contract_test.dart` | Elements → classified rows (headers now detected) |
| `stage_4a_to_4b_contract_test.dart` | Classified rows → regions (synthetic regions for grid pages) |
| `stage_4b_to_4c_contract_test.dart` | Regions → column map (6 columns, correct semantics) |
| `stage_4c_to_4d_contract_test.dart` | Column map → cell grid (elements in correct cells) |
| `stage_4d_to_4e_contract_test.dart` | Cell grid → parsed items (valid bid items) |

### Unit Tests Per Phase

**Phase 1 (Row-Strip OCR):**
- `_computeRowStrips()` — correct strip bounds from grid lines, margins excluded
- `_computeRowStrips()` — single horizontal line pair (edge case)
- `_computeRowStrips()` — page with no grid (falls back to existing logic)
- PSM selection — row 0 gets PSM 6, others get PSM 7
- Coordinate mapping — crop-relative → page-relative round-trip accuracy
- Skip margin — elements outside vertical line bounds excluded

**Phase 2 (Synthetic Regions):**
- `_createSyntheticRegions()` — correct TableRegion bounds from grid lines
- `_createSyntheticRegions()` — headerRowIndices = [0] for each grid page
- Pipeline branching — grid pages use synthetic, non-grid uses detector
- Mixed document — both region sources merged without overlap
- Empty grid lines — graceful fallback to existing region detector

**Phase 3 (Column Assignment):**
- Element xCenter → correct column assignment
- Element spanning two columns → assigned by xCenter
- Element outside all columns → discarded
- Empty column → empty cell (no crash)
- All 6 Springfield columns receive expected content types

### Golden Test (End-to-End)

**`springfield_golden_test.dart`** — regenerate all fixtures, compare against `springfield_ground_truth_items.json`.

**Success criteria**: >=80/131 ground truth matches (up from 0/131)

### Stage Trace Diagnostic

**`stage_trace_diagnostic_test.dart`** — run after implementation:

```
Stage 2B-iii: 939 elements → expecting ~200-300 (fewer, cleaner from row strips)
Stage 4A:     267 rows, 0 headers → expecting headers detected (>=6)
Stage 4B:     0 regions → expecting >=6 (one per grid page)
Stage 4C:     0 columns → expecting 6
Stage 4E:     0 items → expecting >=80 matching ground truth
```

### Regression Safety

- All 324 existing unit tests must still pass (non-grid logic untouched)
- Contract tests verify stage boundaries haven't broken
- Golden test is the final accuracy gate

## Key Files Reference

| File | Role | Modified In |
|------|------|-------------|
| `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart` | Cell/row OCR | Phase 1 |
| `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` | Pipeline wiring | Phase 2 |
| `lib/features/pdf/services/extraction/stages/grid_line_detector.dart` | Grid data source | Read-only |
| `lib/features/pdf/services/extraction/shared/crop_upscaler.dart` | Crop upscaling | Read-only (no changes) |
| `lib/features/pdf/services/extraction/pipeline/coordinate_normalizer.dart` | Coord transforms | Read-only (no changes) |
| `test/features/pdf/extraction/contracts/stage_*_contract_test.dart` | Contract tests | All phases |
| `test/features/pdf/extraction/golden/springfield_golden_test.dart` | Golden test | Phase 3 |
| `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart` | Diagnostic | Phase 3 |

## Success Criteria

| Metric | Before | Target |
|--------|--------|--------|
| Header rows detected | 0 | >=6 |
| Table regions | 0 | >=6 |
| Columns detected | 0 | 6 |
| Ground truth matches | 0/131 | >=80/131 |
| Existing tests passing | 324 | 324 (no regression) |
