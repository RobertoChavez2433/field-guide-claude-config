# Pipeline Report Redesign Spec

## Overview

Replace the 1,039-line scorecard with a scannable report that visually mirrors the PDF table. Two grid views: Clean Grid (assembled values) and OCR Grid (raw Tesseract output with confidence). Stage summary compressed to one row per stage.

## Success Criteria

- Clean Grid table visually comparable to the PDF table (same rows x 6 columns per page)
- OCR Grid shows exactly what Tesseract read per cell with confidence scores
- Low-confidence OCR elements (<0.50) bolded to flag noise
- Stage summary is one row per stage, no inlined JSON blobs
- All classified rows shown (data, header, boilerplate, continuation, total, section header, blank)
- Full 131 GT item verdicts retained
- JSON trace: one additive change (stage input/output/excluded counts added to stage_metrics)
- Scorecard significantly shorter than current 1,039 lines
- Pipe characters in OCR text escaped to prevent markdown table corruption

## Scorecard Layout (scorecard.md)

### Section 1: Header (3 lines, unchanged)

```
# Springfield Extraction Scorecard
> Date: 2026-03-13T09:02:00 | Platform: windows | Tesseract: 5.5.0
> Git: 5b23975 | Duration: 42s | Verdict: PASS (0 regressions)
> Versions: Flutter 3.x | Dart 3.x | pdfrx x.x | flusseract x.x
```

### Section 1.5: Regressions (conditional, only when gate fails)

If the regression gate fails, list the specific regressions between Header and Stage Summary:

```markdown
## Regressions
- item_count: 61 -> 55 (-6)
- checksum: $4,500,000 -> $4,200,000
```

Omitted entirely when verdict is PASS.

### Section 2: Stage Summary

One row per stage. Columns: Stage, In, Out, Excluded, Time(ms), Status.
Status = OK (current >= previous), REGRESSED (worse), NEW (no previous baseline).

Drop all per-page breakdowns, pattern distributions, and complex metric maps from the scorecard. Those stay in JSON only.

```markdown
| Stage | In | Out | Excl | Time(ms) | Status |
|-------|-----|-----|------|----------|--------|
| document_analysis | 6 | 6 | 0 | 150 | OK |
| page_rendering | 6 | 6 | 0 | 1200 | OK |
| image_preprocessing | 6 | 6 | 0 | 800 | OK |
| grid_line_detection | 6 | 6 | 0 | 340 | OK |
| grid_line_removal | 6 | 6 | 0 | 890 | OK |
| text_recognition | 6 | 1562 | 0 | 4200 | OK |
| element_validation | 1562 | 1562 | 0 | 5 | OK |
| row_classification | 1562 | 137 | 0 | 45 | OK |
| row_merging | 137 | 67 | 70 | 8 | OK |
| cell_extraction | 67 | 67 | 0 | 12 | OK |
| numeric_interpretation | 67 | 67 | 0 | 3 | OK |
| row_parsing | 67 | 61 | 6 | 8 | OK |
| post_processing | 61 | 61 | 0 | 15 | OK |
| quality_validation | 61 | 61 | 0 | 2 | OK |
```

### Section 3: Clean Grid (per page)

Mirrors the PDF table. Shows all rows that reach cell extraction (data, header, continuation, total, section header — boilerplate/blank rows are filtered upstream by row_merging and won't appear). 8 columns: Row, Type, Item No., Description, Unit, Est. Quantity, Unit Price, Bid Amount.

Description column truncated to 40 chars in Clean Grid. No truncation in OCR Grid (noise visibility matters more than formatting).

All cell values must have `|` escaped to `\|` and newlines replaced with spaces to prevent markdown table corruption.

Row type abbreviations:
- `hdr` = header
- `data` = data row
- `cont-p` = price continuation
- `cont-d` = description continuation
- `boil` = boilerplate
- `sect` = section header
- `totl` = total
- `blnk` = blank

Example:

```markdown
### Page 1

| Row | Type | Item No. | Description | Unit | Est. Quantity | Unit Price | Bid Amount |
|-----|------|----------|-------------|------|---------------|------------|------------|
| 0 | hdr | Item No. | Description | Unit | Est. Quantity | Unit Price | Bid Amount |
| 1 | data | 1 | Mobilization, Bonds, & Insurance (5% Max) | LSUM | 1 | $390,000.00 | $390,000.00 |
| 2 | data | 2 | Pre-Construction Video Survey | LSUM | 1 | $16,603.48 | $16,603.48 |
| 3 | data | 3 | Traffic Control | LSUM | 1 | $860,970.00 | $860,970.00 |
| 4 | data | 4 | Flag Control | LSUM | 1 | $21,760.00 | $21,760.00 |
| 5 | data | 5 | Erosion Control, Inlet Protection, Fabric Drop | EA | 164 | $87.45 | $14,341.80 |
```

Cell values are the assembled text from `Cell.value` (the joined OCR elements). Empty cells show blank.

### Section 4: OCR Grid (per page)

Same table structure as Clean Grid but each cell shows the raw OCR elements with confidence in parentheses. Elements below 0.50 confidence are **bolded** to visually flag noise/artifacts.

Example:

```markdown
### Page 1 — OCR

| Row | Type | Item No. | Description | Unit | Est. Quantity | Unit Price | Bid Amount |
|-----|------|----------|-------------|------|---------------|------------|------------|
| 1 | data | 1(.97) | Mobilization,(.96) Bonds,(.94) &(.88) Insurance(.95) (5%(.91) Max)(.90) | LSUM(.92) | 1(.95) | $390,000.00(.94) | $390,000.00(.93) |
| 3 | data | **IE(.26)** 4(.95) | Tree(.96) Clearing(.93) **reef(.23)** | **BRA(.26)** EA(.79) | 1(.95) | $2,500.00(.91) | $2,500.00(.90) |
```

Format per element: `text(confidence)` with confidence as 2 decimal places.
Bold threshold: confidence < 0.50.

### Section 5: Item Verdicts

Full table with all 131 GT items + BOGUS items. Same format as current scorecard (unchanged).

```markdown
## Item Flow (131 Ground Truth Items)

| # | Verdict | Description (trunc) | Unit E/A | Amount E/A | $ Delta |
|---|---------|---------------------|----------|------------|---------|
| 1 | PASS | Mobilization, Bon... | LSUM/LSUM | 390000.00/390000.00 | $0 |
| 2 | FAIL | Pre-Construction ... | LSUM/LSUM | 16603.48/16603.00 | -$0 |
| 6 | MISS | Erosion Control, ... | FT/— | 1792.00/— | — |
| BOGUS_0 | BOGUS | | | | |
```

### Section 6: Summary Footer (unchanged)

```markdown
## Summary
- Items: 61 / 131 GT (46.6%)
- Checksum: $X / $Y GT
- Field Accuracy: description 85.2% | unit 90.1% | quantity 88.5% | unit_price 92.0% | bid_amount 91.5%
```

## What Gets Removed from Scorecard

1. **Stage Statistics multi-row format** with per-metric rows and inlined JSON blobs -> replaced by one-row-per-stage summary
2. **Performance Summary** percentage breakdown -> stays in JSON only
3. **Cell Extraction Detail** 700-line `<details>` element dump -> replaced by OCR Grid table
4. **Collapsible `<details>` sections** -> gone entirely

## What Stays in JSON Only

- Per-page stage metrics (e.g., grid_line_removal per_page breakdown)
- Pattern distributions
- Performance percentage breakdown by stage
- Full element-level data with bounding boxes and coordinate metadata
- Sidecar entries

## JSON Trace Changes

One additive change to `_buildStageMetrics`: add `input_count`, `output_count`, `excluded_count` fields from each `StageReport`. These are needed by the Stage Summary table but are not currently serialized to JSON. This is non-breaking (additive only), so `schema_version` stays at 1.

The `cell_grid` key already contains all data needed for both grid tables. No other JSON changes.

## Implementation Notes

- Data source for Clean Grid + OCR Grid: `cell_grid` array in the JSON trace (already built by `_buildCellGrid`)
- Each `cell_grid` entry has: `row_index`, `type`, `page_index`, `cells[]` with `value`, `confidence`, `elements[]`
- The `elements[]` array within each cell has `text` and `confidence` per OCR element
- Stage Summary reads `input_count`, `output_count`, `excluded_count`, `elapsed_ms` from `stage_metrics` in JSON trace
- Previous baseline comparison for Status column uses `loadPreviousReport()`
- Row index in grids is sequential position (0-based loop counter from cell_grid), not the original classified row index
- Confidence values clamped to 0.0-1.0 before formatting (guards against NaN/Infinity from corrupted images)

## Files to Modify

1. `test/features/pdf/extraction/helpers/report_generator.dart` — rewrite `generateScorecard()` method
   - Replace Stage Statistics section with one-row-per-stage summary
   - Replace Cell Extraction Detail section with Clean Grid + OCR Grid
   - Remove Performance Summary section
   - Keep Item Flow and Summary Footer sections

No other files need changes.
