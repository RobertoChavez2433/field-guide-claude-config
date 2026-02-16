# Phase 2 Implementation Plan: TextRecognizerV2 Cell-Level Cropping

**Parent Plan**: `2026-02-14-grid-line-detection-row-ocr.md`
**Phase**: 2 of 4
**Created**: 2026-02-14
**Priority**: OCR accuracy first (100% target for Springfield PDF)

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Crop strategy | Cell-level (row x column) | 100% accuracy target — eliminates all cross-column confusion |
| Vertical line erasing | Skip for now | Characters don't touch lines in Springfield PDF. Add later if accuracy requires it |
| Row padding | 2px inward from grid lines | Validated against actual PDF — generous whitespace between text and lines |
| Wrapped row detection | Row height >1.4x median -> PSM 6 | Catches item 26 (2-line wrap ~ 2x normal) without false positives |
| Normal cell PSM | PSM 7 (single line) | Each cell is one line of text. PSM 7 skips layout analysis = fast + accurate |
| Non-grid page fallback | PSM 4 (single column) | Safer than PSM 6 for free-form text pages; may never trigger for Springfield |
| Grid-only OCR | Only OCR inside grid boundary | Drops legal boilerplate at source — eliminates downstream filtering heuristics |
| Header row | OCR it like any other row | Keeps OCR stage dumb; header detection belongs downstream |
| Optimization | Sequential, reuse engine | Simple, predictable. Parallel per-page documented as future optimization |
| Edge columns | 0.0->v[0] and v[M]->1.0 | N vertical lines -> N+1 columns, matching Phase 3 expectations |

---

## Overview

**Purpose**: Modify `TextRecognizerV2` to use grid line data from Phase 1 for cell-level cropping, achieving near-100% OCR accuracy on the Springfield bid schedule.

**Scope**:
- Cell-level cropping using both horizontal AND vertical grid lines
- Adaptive PSM: PSM 7 (single line) for normal-height cells, PSM 6 (single block) for tall/wrapped cells
- Coordinate mapping from cell-relative -> page-normalized space (using existing `CoordinateNormalizer.fromCropRelative()`)
- No vertical line erasing (documented for future if needed)
- Sequential OCR on reused Tesseract instance (parallel documented as future optimization)

**What's excluded**:
- Column semantic assignment (Phase 3)
- Pipeline wiring (Phase 4)
- Vertical line erasing (future if accuracy requires it)

**Success Criteria**:
- [ ] All 6 grid pages produce cell-level OCR elements with correct page-normalized coordinates
- [ ] Wrapped rows (item 26) produce complete text, not truncated
- [ ] Non-grid pages (`hasGrid == false`) fall back to full-page OCR with PSM 4
- [ ] Existing `recognizeCrop()` + `fromCropRelative()` reused — no reinventing coordinate math

---

## Cell Cropping Algorithm

Core logic inside `TextRecognizerV2._recognizeWithCellCropping()`:

```
For each grid page:
  1. Get horizontal lines [h0, h1, h2, ...hN] and vertical lines [v0, v1, ...vM]
  2. For each row pair (h[i], h[i+1]):
     For each column pair (v[j], v[j+1]):
       a. Compute cell region (normalized):
          left   = v[j]       (first column: 0.0)
          top    = h[i] + inwardPadPx/imageHeight   (2px inward)
          right  = v[j+1]     (last column: 1.0)
          bottom = h[i+1] - inwardPadPx/imageHeight (2px inward)
       b. Compute row height in pixels
       c. Determine PSM:
          - medianRowHeight = median of all row heights on this page
          - if rowHeightPx > medianRowHeight * 1.4 -> PSM 6 (wrapped)
          - else -> PSM 7 (single line)
       d. Crop cell from preprocessed image
       e. Call engine.recognizeCrop() with cell bytes + cell region + config(psm)
       f. Elements returned are already crop-relative
       g. Convert to page-normalized via CoordinateNormalizer.fromCropRelative()
       h. Add all elements to page's element list
  3. Sort elements by (top, left) for consistent ordering
```

**Edge handling:**
- First column: `left = 0.0` to `v[0]` (content left of first vertical line — the Item No. column)
- Last column: `v[M]` to `right = 1.0` (content right of last vertical line — Bid Amount column)
- This means N vertical lines -> N+1 column regions, matching Phase 3's expectation

**Wrapped row detection:**
- Compute median row height across all rows on the page
- Rows >1.4x median are considered wrapped -> use PSM 6
- 1.4x threshold catches item 26 (2-line wrap ~ 2x normal height) while ignoring minor height variations

**Non-grid page fallback:**
- Pages where `gridLineResult.hasGrid == false` -> `_recognizeFullPage()` with PSM 4 (single column)

---

## Files to Modify (3)

### 1. `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart` — Primary changes

| Change | Details |
|--------|---------|
| New parameter | `GridLines? gridLines` added to `recognize()` (optional, backward compatible) |
| New method | `_recognizeWithCellCropping()` — cell-level crop + OCR loop |
| New method | `_recognizeFullPage()` — extracted from current logic, uses PSM 4 |
| New helper | `_determineRowPsm()` — compares row height to median, returns 7 or 6 |
| New helper | `_computeCellRegions()` — builds list of normalized `Rect` from grid lines |
| Per-page fork | `gridLines.pages[pageIndex].hasGrid` -> cell cropping, else -> full page |
| StageReport | New metrics: `cells_cropped`, `wrapped_rows`, `psm7_calls`, `psm6_calls` |

**Per-page fork logic:**
```
if gridLines != null && gridLines.pages[pageIndex].hasGrid:
  -> _recognizeWithCellCropping(page, gridLineResult, engine, config)
else:
  -> _recognizeFullPage(page, engine, config.copyWith(psmMode: 4))
```

### 2. `lib/features/pdf/services/extraction/ocr/tesseract_config_v2.dart` — Add PSM 4

Add to `pageSegMode` getter:
```dart
case 4: return PageSegMode.singleColumn;
```

### 3. `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart` — Per-call PSM

Add `tess.setPageSegMode(cfg.pageSegMode)` before each `hocrText()` call in both `recognizeImage()` and `recognizeCrop()`, so PSM can change between calls on the same Tesseract instance.

### No new files needed

All infrastructure exists:
- `recognizeCrop()` already exists in `TesseractEngineV2` (lines 90-128)
- `CoordinateNormalizer.fromCropRelative()` already exists (lines 48-67)
- Models (`OcrElement`, `GridLines`) already defined

---

## Test Plan

### A. Files modified to compile (signature changes only)

| # | File | Change | Why |
|---|------|--------|-----|
| 1 | `helpers/mock_stages.dart` | Add `GridLines? gridLines` param to `MockTextRecognizerV2.recognize()` | Mock must match new signature |
| 2 | `stages/stage_2b_text_recognizer_test.dart` | No signature changes needed (gridLines is nullable, existing calls pass `null` implicitly) | Backward compatible |
| 3 | `contracts/stage_2_to_3_contract_test.dart` | No changes needed | Contract tests don't call TextRecognizerV2 directly |
| 4 | `pipeline/re_extraction_loop_test.dart` | No changes needed (uses MockTextRecognizerV2 which gets signature update) | Pipeline wiring is Phase 4 |
| 5 | `pipeline/extraction_pipeline_test.dart` | No changes needed | Pipeline wiring is Phase 4 |

### B. New cell cropping tests (16 tests)

File: `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart`

Added inside a new group `'recognize with cell cropping'` alongside existing 7 tests. Uses the existing `MockOcrEngine` enhanced to track `recognizeCrop()` calls and PSM configs.

#### Group 1: Cell Region Computation (3 tests)

| # | Test | What it validates |
|---|------|-------------------|
| 1 | Correct cell regions from grid lines | 5 horizontal + 3 vertical lines -> 4 rows x 4 columns = 16 cell `Rect`s with correct normalized bounds |
| 2 | Edge columns extend to page boundary | First column starts at `0.0`, last column ends at `1.0` |
| 3 | 2px inward padding applied | Cell top/bottom are inset by `2px / imageHeight` from the raw horizontal line positions |

#### Group 2: PSM Selection (3 tests)

| # | Test | What it validates |
|---|------|-------------------|
| 4 | Normal row -> PSM 7 | Row height at median -> config has `psmMode: 7` |
| 5 | Wrapped row -> PSM 6 | Row height >1.4x median -> config has `psmMode: 6` |
| 6 | Median computed correctly | 27 normal rows + 1 tall row -> median reflects normal height, not skewed by outlier |

#### Group 3: Coordinate Mapping (3 tests)

| # | Test | What it validates |
|---|------|-------------------|
| 7 | Cell-relative -> page-normalized | Element at `(0.5, 0.5)` in cell covering `[x:0.2-0.4, y:0.3-0.4]` -> page position `(0.3, 0.35)` |
| 8 | Elements from different cells don't overlap | Two adjacent cells produce elements with non-overlapping bounding boxes |
| 9 | All elements pass `isNormalized()` validation | Every element from cell cropping has coords in `0.0-1.0` range |

#### Group 4: Grid vs Non-Grid Fork (3 tests)

| # | Test | What it validates |
|---|------|-------------------|
| 10 | Grid page uses cell cropping | Page with `hasGrid == true` -> `recognizeCrop()` called N times, `recognizeImage()` not called |
| 11 | Non-grid page uses PSM 4 full page | Page with `hasGrid == false` -> `recognizeImage()` called once with PSM 4 config |
| 12 | Mixed document: both paths execute | Page 0 no grid + Page 1 grid -> page 0 gets full-page OCR, page 1 gets cell cropping |

#### Group 5: StageReport Metrics (2 tests)

| # | Test | What it validates |
|---|------|-------------------|
| 13 | Metrics track cell cropping stats | `cells_cropped`, `psm7_calls`, `psm6_calls` counts match expected |
| 14 | Wrapped row count in metrics | 1 tall row among 28 -> `wrapped_rows: 1` |

#### Group 6: Engine PSM Changes (2 tests)

| # | Test | What it validates |
|---|------|-------------------|
| 15 | PSM 4 case returns singleColumn | `OcrConfigV2(psmMode: 4).pageSegMode == PageSegMode.singleColumn` |
| 16 | Per-call PSM override works | Two consecutive `recognizeCrop()` calls with different PSM configs -> each uses correct mode |

### C. Diagnostic test update

File: `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`

Add new section: "Stage 2B-iii: Text Recognition analysis" that prints:
- Per-page OCR method (cell-cropped vs full-page)
- Cells cropped count per page
- PSM 7/6 split
- Wrapped row count
- Guard with fixture existence check (like grid lines test)

### D. Golden & fixture updates — deferred to Phase 4

| File | Phase 2 action | Phase 4 action |
|------|---------------|---------------|
| `golden/stage_trace_diagnostic_test.dart` | Add diagnostic section (guarded) | Verify section prints expected cell counts |
| `golden/springfield_golden_test.dart` | No changes — baselines stay at current values (1 item, 0.615 quality) | Update baselines toward 131 items / 0.85+ quality |
| `golden/springfield_benchmark_test.dart` | No changes | Add grid-line cell-cropping benchmark configs |
| All `fixtures/*.json` | Not regenerated | Regenerated — all fixtures cascade from better OCR |

### E. Fixture regeneration cascade (Phase 4)

When `tool/generate_springfield_fixtures.dart` runs with the wired pipeline:

```
springfield_grid_lines.json       <- NEW (from Phase 1)
springfield_unified_elements.json <- CHANGED (cell-level elements, ~800 vs ~30)
springfield_classified_rows.json  <- CHANGED (cleaner rows from better OCR)
springfield_detected_regions.json <- CHANGED (regions based on cleaner rows)
springfield_column_map.json       <- CHANGED (grid_line method, 6 columns, 0.95 confidence)
springfield_cell_grid.json        <- CHANGED (proper cell values from 6-column detection)
springfield_parsed_items.json     <- CHANGED (131 items with correct values)
springfield_processed_items.json  <- CHANGED (131 items post-processing)
springfield_quality_report.json   <- CHANGED (score jumps from 0.615 toward 0.85+)
```

### F. Test summary

| Category | Files | New tests | Modified |
|----------|-------|-----------|----------|
| Signature updates | 1 (`mock_stages.dart`) | 0 | 1 mock class |
| New cell cropping tests | 1 (`stage_2b_text_recognizer_test.dart`) | 16 | 0 |
| Engine/config tests | 1-2 (engine/config test files) | 2 | 0 |
| Diagnostic trace | 1 (`stage_trace_diagnostic_test.dart`) | 1 section | 0 |
| **Phase 4 deferred** | 3+ (golden, benchmark, all fixtures) | 0 | ~20 assertions |

**Total: 19 new tests, 4 files touched in Phase 2. ~20 assertion updates deferred to Phase 4.**

---

## Implementation Order

```
Step 1: tesseract_config_v2.dart
         Add PSM 4 case. Smallest change, zero risk.

Step 2: tesseract_engine_v2.dart
         Add per-call setPageSegMode() before hocrText().
         Test: verify PSM switching works.

Step 3: text_recognizer_v2.dart
         a. Add GridLines? parameter to recognize()
         b. Extract current logic to _recognizeFullPage() with PSM 4
         c. Add _computeCellRegions() helper
         d. Add _determineRowPsm() helper
         e. Add _recognizeWithCellCropping() method
         f. Wire per-page fork (hasGrid -> cells, else -> full page)

Step 4: mock_stages.dart
         Update MockTextRecognizerV2 signature.

Step 5: stage_2b_text_recognizer_test.dart
         a. Enhance MockOcrEngine to track recognizeCrop() calls + configs
         b. Add 16 new cell cropping tests
         c. Verify existing 7 tests still pass unchanged

Step 6: Engine/config test files
         Add PSM 4 case test + per-call PSM test.

Step 7: stage_trace_diagnostic_test.dart
         Add "Stage 2B-iii: Text Recognition" diagnostic section.

Step 8: Run full test suite
         pwsh -Command "flutter test test/features/pdf/extraction/"
```

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| PSM switching on same Tesseract instance fails silently | High | `setPageSegMode()` is documented API. If it fails, add test that detects wrong output and recreate instance. |
| Cell crops too small (<15px height) | Medium | Set minimum crop height; if below threshold, merge with adjacent row and use PSM 6. |
| Coordinate rounding accumulates error | Medium | Use `double` throughout, only round at final pixel conversion. All tests assert `isNormalized()`. |
| `recognizeCrop()` returns empty for valid cells | Medium | Log warning per-cell, don't fail entire page. StageReport tracks empty cell count. |
| Wrapped row threshold (1.4x) too aggressive or too loose | Low | Tunable constant. Springfield has one wrapped row (item 26) — easy to validate. Adjust if future PDFs differ. |
| Sequential OCR too slow (estimated 3-8s for 6 pages) | Low | Acceptable for accuracy-first goal. Parallel per-page documented as future optimization. |
| No vertical line erasing hurts accuracy on other PDFs | Low | Documented for future. Springfield grid lines are thin and characters don't touch them. |

---

## Future Optimizations (documented, not implemented)

1. **Parallel per-page OCR** — each page gets its own Tesseract isolate, cells within page sequential
2. **Vertical line erasing** — 3-5px white band at each vertical line position before OCR
3. **Skip empty cells** — check dark pixel count before OCR, skip blank cells
4. **Adaptive line thickness** — measure actual grid line width and adjust padding accordingly

---

## Verification

```
pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart"
pwsh -Command "flutter test test/features/pdf/extraction/ocr/"
pwsh -Command "flutter test test/features/pdf/extraction/"
```

All existing tests pass unchanged (GridLines parameter is optional). 19 new tests pass. No fixture regeneration needed until Phase 4.

---

## Agent Assignment

| Task | Agent |
|------|-------|
| Steps 1-3 (config, engine, recognizer) | `frontend-flutter-specialist-agent` |
| Steps 4-7 (mocks, tests, diagnostics) | `qa-testing-agent` |
| Code review | `code-review-agent` |
