# Implementation Plan: Row Classifier V3 + Column Label Fix

**Date**: 2026-02-16
**Session**: 360
**Bugs**: Stage 08 Row Classification, Stage 11 Column Label Propagation
**Approach**: Fix upstream → downstream. Bug #2 (labels) first, then Bug #1 (classifier rewrite + merger).

---

## Current Scorecard (Baseline)

```
Totals: 22 OK  |  4 LOW  |  22 BUG  (48 metrics)
First upstream BUG: Stage 08 Row Classification Data rows (expected: 131, actual: 206)
```

| Stage | Metric | Expected | Actual | Status |
|-------|--------|----------|--------|--------|
| 08 Row Classification | Data rows | 131 | 206 | BUG |
| 08 Row Classification | Unknown rows | 0 | 96 | BUG |
| 08 Row Classification | Continuation | ~150 | 29 | BUG |
| 08 Row Classification | Headers | 6 | 2 | BUG |
| 11 Column Detection | Page labels | 36/36 | 26/36 | BUG |
| 14 Cell Extraction | Grid rows | ~131 | 293 | BUG |
| 16 Row Parsing | w/ unit_price | 131 | 20 (15%) | BUG |
| 16 Row Parsing | Total $ | $7,882,926.73 | $670,147.68 (9%) | BUG |
| 23 Quality | Completeness | 100% | 61.8% | BUG |

---

## Phase 1: Column Label Propagation (Bug #2)

### Problem

Grid-line column detection finds correct boundaries on all pages but assigns wrong labels on continuation pages that lack header rows. Per-page keyword matching fails because there is no header text to match on pages 1-5.

**Root cause confirmed from fixture data**: Pages 1-5 have no header band text for columns 3-4. The keyword matcher assigns `unitPrice` to col 3 (wrong) and `null` to col 4 (wrong). Page 0 has all 6/6 labels correct at 0.95 confidence. All pages have identical column boundaries (within 1%).

### Fix: Label Propagation Within Column Detector

**File**: `lib/features/pdf/services/extraction/stages/column_detector_v2.dart`

**Location**: Inside `detect()` method (line 120), after per-page grid labeling completes (~line 534), before final column map output.

#### Algorithm (generic, not PDF-specific)

```
// Runs after all grid pages have been individually labeled via keyword matching.
// Handles any multi-page table where continuation pages lack header rows.

_propagateGridPageLabels(gridPageColumns, gridPageConfidences):

  1. FIND TEMPLATE PAGE:
     - For each grid page, count columns with non-null semantic labels
     - templatePage = page with highest semantic count
     - Tie-break: prefer lowest page index (first page most likely to have header)
     - If templatePage has fewer than 4 semantics, abort (no reliable template)

  2. GET TEMPLATE COLUMNS:
     - templateCols = gridPageColumns[templatePage]
     - templateCount = templateCols.length

  3. FOR EACH OTHER GRID PAGE:
     - pageCols = gridPageColumns[pageIndex]

     a. COLUMN COUNT CHECK:
        - If pageCols.length != templateCount → skip (different table structure)

     b. BOUNDARY ALIGNMENT CHECK:
        - For each column i in 0..templateCount-1:
          - tolerance = 0.02 (2% of normalized page width)
          - leftAligned = |pageCols[i].startX - templateCols[i].startX| < tolerance
          - rightAligned = |pageCols[i].endX - templateCols[i].endX| < tolerance
          - If NOT (leftAligned AND rightAligned) → skip this page

     c. PROPAGATE MISSING LABELS:
        - For each column i where pageCols[i].semantic == null
          AND templateCols[i].semantic != null:
          - pageCols[i] = pageCols[i].copyWith(semantic: templateCols[i].semantic)

     d. RECALCULATE CONFIDENCE:
        - newSemanticCount = count of non-null semantics after propagation
        - gridPageConfidences[pageIndex] = _gridLayerConfidenceForMatches(newSemanticCount)
```

**Where to insert**: After the existing per-page grid labeling loop (which ends around line 534 inside `_detectFromGridLines()`), before `weakSemanticPages` is computed. This ensures propagation happens before the weak-page borrowing logic at line 235.

Alternatively, insert as a new private method `_propagateGridPageLabels()` called from `detect()` at ~line 234, right after `gridLayer0` is computed but before `_borrowLayer1SemanticsForWeakGridPages()`.

### Cleanup: Disable Anchor Correction for Grid Pages

**File**: `lib/features/pdf/services/extraction/stages/column_detector_v2.dart`

**Current code** (lines 287-322): `_correctWithAnchors()` is called for all pages, but for grid pages it only computes a diagnostic offset and then `continue`s — never overriding grid geometry.

**Change**: Skip the `_correctWithAnchors()` call entirely when all pages are grid pages. Specifically:
- At line 287, wrap the anchor correction block in a check: `if (nonGridPages.isNotEmpty)`
- Remove Layer 3 diagnostic emission for grid-only documents
- Keep anchor correction active for documents that have non-grid pages (it's useful there)

### Files Changed

| File | Change | Lines Affected |
|------|--------|----------------|
| `column_detector_v2.dart` | Add `_propagateGridPageLabels()` method | New method ~20-30 lines |
| `column_detector_v2.dart` | Call propagation after grid labeling | Insert at ~line 234 |
| `column_detector_v2.dart` | Skip anchor correction for grid-only docs | Lines 287-322 |

### Tests to Update

1. **`test/features/pdf/extraction/stages/stage_4c_column_detector_test.dart`**
   - Update expectations: all pages should have 6/6 labels after propagation
   - Update confidence expectations: pages 1-5 should now match template confidence
   - Add unit test for `_propagateGridPageLabels()` edge cases:
     - Pages with different column counts (should NOT propagate)
     - Pages with misaligned boundaries (should NOT propagate)
     - Template page selection when multiple pages have same semantic count

2. **`test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`**
   - Scorecard metric `**11 Column Detection — Page labels` → 26/36 → 36/36 → OK
   - Scorecard metric `11 Column Detection — Columns` → stays 6 → OK (unchanged)

3. **Fixtures to regenerate** (after Phase 1 only):
   - `springfield_column_map.json` — labels will change on pages 1-5
   - `springfield_column_detection_layers.json` — Layer 3 removed for grid pages
   - Downstream fixtures will be regenerated after all phases complete

---

## Phase 2: Row Classifier V3 (Bug #1)

### Problem

V2 row classifier (`row_classifier_v2.dart`, lines 1-944) uses content-only scoring with a `dataLikelihood` composite score. It has no awareness of split-row patterns. The `_isContinuation()` method (line 610-636) explicitly REJECTS rows with numeric/currency content (lines 616-617), which means price-only rows are classified as DATA or UNKNOWN instead of continuation.

### Dependency on Phase 1

V3 classifier requires correct column semantics to determine zones. Phase 1 must be completed first so that all pages have correct labels for zone computation.

### New File: `lib/features/pdf/services/extraction/stages/row_classifier_v3.dart`

**Replaces**: Classification logic in `row_classifier_v2.dart` (lines 91-246 classify method, lines 595-636 isDataRow/isContinuation, lines 683-731 dataLikelihood)
**Keeps**: Row grouping logic from V2 (lines 738-832) — this works well and is independent of classification
**Input**: Validated OCR elements (Stage 06), grid line boundaries (Stage 04), column definitions with semantics (Stage 11)
**Output**: `ClassifiedRows` with updated `RowType` enum

### Updated RowType Enum

**File**: `lib/features/pdf/services/extraction/models/classified_rows.dart` (current enum at lines 9-18)

```dart
// BEFORE (V2):
enum RowType {
  header,
  subheader,       // REMOVE — merge into header
  data,
  continuation,    // REMOVE — split into two specific types
  boilerplate,
  sectionHeader,
  total,
  unknown,         // REMOVE — V3 classifies everything
}

// AFTER (V3):
enum RowType {
  header,              // Column header row (ITEM NO., DESCRIPTION, etc.)
  data,                // Primary item row (has item# in itemNumber column)
  priceContinuation,   // Price-only row (elements in price/amount columns only)
  descContinuation,    // Description overflow (text elements, no item#, no prices)
  sectionHeader,       // Section dividers (EARTHWORK, DRAINAGE, etc.)
  total,               // Total/subtotal rows
  blank,               // Empty or whitespace-only rows
  boilerplate,         // Legal text, footnotes, contract language
}
```

**Impact of enum change**: Every file that references `RowType.continuation`, `RowType.unknown`, or `RowType.subheader` must be updated. Search for these references:
- `RowType.continuation` → decide per-usage if it should be `priceContinuation` or `descContinuation`
- `RowType.unknown` → remove (no longer produced)
- `RowType.subheader` → change to `RowType.header`

### V3 Classification Algorithm

**Core concept**: Zone-based classification using column semantics. Zones are DYNAMIC — derived from whatever labels the column detector assigned, not hardcoded to specific column positions.

```
class RowClassifierV3:

  // --- ZONE COMPUTATION (runs once per document) ---

  _computeZones(columnDefs):
    textZone = {}      // columns containing item/description/unit/quantity
    priceZone = {}     // columns containing unitPrice/bidAmount

    for each columnDef in columnDefs:
      semantic = columnDef.semantic
      if semantic in {itemNumber, description, unit, quantity}:
        textZone.add(columnDef)
      else if semantic in {unitPrice, bidAmount}:
        priceZone.add(columnDef)

    // Find the itemNumber column specifically (for item# pattern matching)
    itemNumColumn = columnDefs.firstWhere(c => c.semantic == 'itemNumber', orElse: null)
    descColumn = columnDefs.firstWhere(c => c.semantic == 'description', orElse: null)

  // --- ELEMENT-TO-COLUMN MAPPING (runs per element) ---

  _mapElementToColumn(element, columnDefs):
    // Find which column this element overlaps most with
    bestOverlap = 0
    bestColumn = null
    for each col in columnDefs:
      overlapStart = max(element.normalizedX, col.startX)
      overlapEnd = min(element.normalizedX + element.normalizedWidth, col.endX)
      overlap = max(0, overlapEnd - overlapStart)
      if overlap > bestOverlap:
        bestOverlap = overlap
        bestColumn = col
    return bestColumn

  // --- ROW CLASSIFICATION (runs per row, in sequence) ---

  classify(rows, columnDefs, gridLines):
    zones = _computeZones(columnDefs)
    medianHeight = _computeMedianElementHeight(rows)
    previousRow = null

    for each row in rows:
      // Step 1: Map elements to columns
      elementsByColumn = {}
      for each element in row.elements:
        col = _mapElementToColumn(element, columnDefs)
        elementsByColumn[col] ??= []
        elementsByColumn[col].add(element)

      // Step 2: Compute zone occupancy
      textPopulated = elementsByColumn.keys.where(c => c in zones.textZone)
                        .expand(c => elementsByColumn[c])
                        .where(e => e.text.trim().isNotEmpty)
                        .toList()
      pricePopulated = elementsByColumn.keys.where(c => c in zones.priceZone)
                        .expand(c => elementsByColumn[c])
                        .where(e => e.text.trim().isNotEmpty)
                        .toList()

      // Step 3: Classify (rules applied in priority order)
      rowType = _classifyRow(row, textPopulated, pricePopulated,
                             elementsByColumn, zones, medianHeight, previousRow)

      previousRow = ClassifiedRow(type: rowType, ...)

    return ClassifiedRows(rows: allClassifiedRows)

  // --- CLASSIFICATION RULES (priority order) ---

  _classifyRow(row, textPop, pricePop, elemsByCol, zones, medianH, prevRow):

    // a. BLANK — no content
    if row.elements.isEmpty OR row.elements.every(e => e.text.trim().isEmpty):
      return RowType.blank

    // b. HEADER — matches column header keywords
    headerKeywordCount = _countHeaderKeywords(row.elements)
    keywordDensity = headerKeywordCount / row.elements.length
    if headerKeywordCount >= 3 OR (headerKeywordCount >= 2 AND keywordDensity > 0.60):
      return RowType.header

    // c. TOTAL — contains "TOTAL"/"SUBTOTAL" + numeric content
    joinedText = row.elements.map(e => e.text).join(' ').toUpperCase()
    if _containsTotalKeyword(joinedText) AND _hasNumericContent(pricePop):
      return RowType.total

    // d. DATA — has item number pattern in itemNumber column
    itemNumElements = elemsByCol[zones.itemNumColumn] ?? []
    hasItemNumber = itemNumElements.any(e => ExtractionPatterns.itemNumber.hasMatch(e.text))
    if hasItemNumber AND textPop.isNotEmpty AND row.elements.length >= 2 AND row.elements.length <= 20:
      return RowType.data

    // e. PRICE_CONTINUATION — price zone populated, text zone empty
    if pricePop.isNotEmpty AND textPop.isEmpty:
      if prevRow != null AND prevRow.type in {data, descContinuation}:
        yGap = _computeYGap(row, prevRow)
        if yGap < medianH * 2.0:
          return RowType.priceContinuation

    // f. DESC_CONTINUATION — text zone populated, no item#, no prices
    if textPop.isNotEmpty AND pricePop.isEmpty AND !hasItemNumber:
      if prevRow != null AND prevRow.type in {data, priceContinuation, descContinuation}:
        yGap = _computeYGap(row, prevRow)
        if yGap < medianH * 2.0:
          return RowType.descContinuation

    // g. SECTION_HEADER — wide text, no numeric columns, few elements
    descElements = elemsByCol[zones.descColumn] ?? []
    rowSpan = _computeRowSpan(row.elements)  // normalized width of row content
    if rowSpan > 0.60 AND pricePop.isEmpty AND row.elements.length <= 5:
      if _isUpperOrTitleCase(joinedText):
        return RowType.sectionHeader

    // h. BOILERPLATE — everything else
    return RowType.boilerplate

  // --- HEADER KEYWORD MATCHING ---

  _countHeaderKeywords(elements):
    keywords = {
      'ITEM', 'NO', 'NO.', 'NUMBER',
      'DESCRIPTION',
      'UNIT', 'UNITS',
      'QTY', 'QUANTITY', 'EST', 'EST.',
      'PRICE', 'UNIT PRICE',
      'AMOUNT', 'BID AMOUNT', 'BID',
    }
    return elements.where(e => keywords.contains(e.text.trim().toUpperCase())).length

  // --- HELPER METHODS ---

  _containsTotalKeyword(text):
    return text.contains('TOTAL') OR text.contains('SUBTOTAL')

  _hasNumericContent(elements):
    return elements.any(e => RegExp(r'[\d$,.]').hasMatch(e.text))

  _computeYGap(currentRow, previousRow):
    // Edge-to-edge vertical gap between rows
    prevBottom = previousRow.elements.map(e => e.normalizedY + e.normalizedHeight).max
    currTop = currentRow.elements.map(e => e.normalizedY).min
    return currTop - prevBottom

  _computeRowSpan(elements):
    leftmost = elements.map(e => e.normalizedX).min
    rightmost = elements.map(e => e.normalizedX + e.normalizedWidth).max
    return rightmost - leftmost

  _isUpperOrTitleCase(text):
    return text == text.toUpperCase() OR text.split(' ').every(w => w[0].isUpperCase)
```

### Row Grouping (Reuse from V2)

**Keep**: The row grouping logic from `row_classifier_v2.dart` lines 738-832:
- Adaptive Y-threshold (0.35× median height)
- Split rows with 2+ item numbers in left 20% column
- Sort elements left-to-right within rows

**Extract** this into a shared utility or keep in V3 file. The grouping is classification-agnostic.

### Pipeline Input Change

**Critical**: V3 classifier needs column definitions as input, which come from Stage 11 (Column Detection). But currently in the pipeline (line 524-536 of `extraction_pipeline.dart`), row classification runs at Stage 4A BEFORE column detection at Stage 4C (line 770).

**Options**:
1. **Reorder pipeline**: Move row classification AFTER column detection
2. **Two-pass**: Keep V2 grouping in current position, run V3 classification after column detection

**Recommended**: Reorder pipeline. Since V3 needs column semantics, it must run after column detection. The new pipeline order:

```
Current order:                    New order:
Stage 0:  Document Analysis       Stage 0:  Document Analysis
Stage 2B: OCR (render/preproc/    Stage 2B: OCR (render/preproc/
          grid/text)                        grid/text)
Stage 3:  Element Validation      Stage 3:  Element Validation
Stage 4A: Row Classification ←    Stage 4B: Region Detection (needs elements only)
Stage 4B: Region Detection        Stage 4C: Column Detection (needs regions + elements)
Stage 4C: Column Detection        Stage 4A: Row Classification V3 (needs columns + elements) ← MOVED
Stage 4D: Cell Extraction         Stage 4A.5: Row Merger (NEW, needs classified rows)
Stage 4E: Row Parsing             Stage 4D: Cell Extraction (now receives merged rows)
Stage 5:  Post-Processing         Stage 4E: Row Parsing
Stage 6:  Quality Validation      Stage 5:  Post-Processing
                                  Stage 6:  Quality Validation
```

**Impact**: Region detection (Stage 4B) currently receives `classifiedRows` as input (line 540). Check if it actually uses row classification data or just elements. If it only needs elements + grid lines, reordering is safe. If it needs classified rows, we need the two-pass approach.

**File to check**: `lib/features/pdf/services/extraction/stages/region_detector_v2.dart` — verify what inputs it requires.

### Phase 1B Refinement — REMOVE

V2 Phase 1B (`refinePostColumn()`, lines 258-391 of `row_classifier_v2.dart`) refines `UNKNOWN` rows after column detection. Since V3:
- Runs AFTER column detection (already has column context)
- Has no `UNKNOWN` type (every row classified in single pass)
- Handles section headers directly in the main classification

**Remove**: Phase 1B call in pipeline at line 788 of `extraction_pipeline.dart`.

### Constants

```dart
class RowClassifierV3 {
  // Header detection
  static const int kMinHeaderKeywords = 3;
  static const int kMinHeaderKeywordsWithDensity = 2;
  static const double kHeaderKeywordDensity = 0.60;

  // Data row bounds
  static const int kMinDataElements = 2;
  static const int kMaxDataElements = 20;

  // Continuation gap tolerance
  static const double kMaxRowGapMultiplier = 2.0;  // gap < 2× median height

  // Section header detection
  static const double kSectionHeaderMinWidth = 0.60;  // >60% of table width
  static const int kMaxSectionHeaderElements = 5;

  // Row grouping (carried from V2)
  static const double kRowGroupingMultiplier = 0.35;  // Y-threshold = 0.35× median height
}
```

### Files Changed

| File | Change | Details |
|------|--------|---------|
| `classified_rows.dart` | Update RowType enum | Remove unknown/subheader/continuation, add priceContinuation/descContinuation/blank |
| `row_classifier_v3.dart` | NEW FILE | ~300-400 lines, zone-based classifier |
| `extraction_pipeline.dart` | Reorder stages, use V3 | Move 4A after 4C, remove Phase 1B call |
| `row_classifier_v2.dart` | Deprecate/remove | No longer called from pipeline |

---

## Phase 3: Row Merger (New Stage)

### New File: `lib/features/pdf/services/extraction/stages/row_merger.dart`

**Position in pipeline**: After Row Classification V3 (new Stage 4A), before Cell Extraction (Stage 4D)
**Input**: `ClassifiedRows` from V3 classifier + `ColumnMap` from column detector
**Output**: `MergedRows` — each merged row combines a DATA row with its continuation(s)

### MergedRow Model

```dart
/// A single logical item row, potentially assembled from multiple physical rows.
///
/// In split-row bid tabulations, a single item may span:
/// - Row N: item#, description, unit, quantity (DATA row)
/// - Row N+1: unit_price, bid_amount (PRICE_CONTINUATION row)
/// - Optionally Row N-1 or N+2: description overflow (DESC_CONTINUATION row)
class MergedRow {
  final ClassifiedRow base;                        // The DATA row (anchor)
  final List<ClassifiedRow> priceContinuations;    // Price-only rows
  final List<ClassifiedRow> descContinuations;     // Description overflow rows
  final RowType type;                              // Passthrough: base.type for DATA, own type for non-data

  /// All OCR elements from base + all continuations
  List<OcrElement> get allElements => [
    ...base.elements,
    ...descContinuations.expand((r) => r.elements),
    ...priceContinuations.expand((r) => r.elements),
  ];

  /// Page index from the base row
  int get pageIndex => base.pageIndex;

  /// Row index from the base row
  int get rowIndex => base.rowIndex;

  /// Whether this merged row consumed any continuation rows
  bool get hasContinuations => priceContinuations.isNotEmpty || descContinuations.isNotEmpty;

  /// Number of physical rows consumed
  int get physicalRowCount => 1 + priceContinuations.length + descContinuations.length;
}

/// Output of the row merger stage
class MergedRows {
  final List<MergedRow> rows;
  final int totalPhysicalRows;      // Before merging
  final int totalMergedRows;        // After merging
  final int dataRowsWithPrice;      // DATA rows that got a priceContinuation
  final int dataRowsWithDesc;       // DATA rows that got a descContinuation
  final int orphanContinuations;    // Continuations with no preceding DATA row
}
```

### Merger Algorithm

```
class RowMerger:

  merge(classifiedRows, columnMap):
    mergedRows = []
    orphanCount = 0
    i = 0

    while i < classifiedRows.length:
      row = classifiedRows[i]

      CASE row.type:

        DATA:
          // Start a new merged row anchored on this DATA row
          merged = MergedRow(base: row)
          j = i + 1

          // Consume all following continuations
          while j < classifiedRows.length:
            next = classifiedRows[j]

            if next.type == PRICE_CONTINUATION:
              merged.priceContinuations.add(next)
              j++
            else if next.type == DESC_CONTINUATION:
              merged.descContinuations.add(next)
              j++
            else:
              break  // Hit non-continuation — end of this item's rows

          mergedRows.add(merged)
          i = j

        HEADER, SECTION_HEADER, TOTAL:
          // Non-data structural rows pass through as single-row MergedRows
          mergedRows.add(MergedRow(base: row, type: row.type))
          i++

        PRICE_CONTINUATION, DESC_CONTINUATION:
          // Orphan continuation — no preceding DATA row
          // This shouldn't happen with correct classification, but handle gracefully
          orphanCount++
          // Attach to previous merged row if it exists and is DATA
          if mergedRows.isNotEmpty AND mergedRows.last.type == DATA:
            if row.type == PRICE_CONTINUATION:
              mergedRows.last.priceContinuations.add(row)
            else:
              mergedRows.last.descContinuations.add(row)
          else:
            // Truly orphaned — emit as boilerplate
            mergedRows.add(MergedRow(base: row.copyWith(type: BOILERPLATE)))
          i++

        BLANK, BOILERPLATE:
          // Skip — don't include in merged output
          i++

    return MergedRows(
      rows: mergedRows,
      totalPhysicalRows: classifiedRows.length,
      totalMergedRows: mergedRows.length,
      dataRowsWithPrice: mergedRows.where(m => m.priceContinuations.isNotEmpty).length,
      dataRowsWithDesc: mergedRows.where(m => m.descContinuations.isNotEmpty).length,
      orphanContinuations: orphanCount,
    )
```

### Stage Registration

**File**: `lib/features/pdf/services/extraction/stages/stage_names.dart` (lines 5-29)

Add:
```dart
static const rowMerging = 'row_merging';
```

**File**: `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`

Insert row merger stage call after V3 classification, before cell extraction. The merger emits:
- `MergedRows` object → passed to cell extraction
- `StageReport` with diagnostics (merge counts, orphan count)
- Fixture snapshot for `springfield_merged_rows.json`

### Downstream Impact

After row merging, downstream stages receive `MergedRow` objects instead of `ClassifiedRow`:

| Stage | Before | After |
|-------|--------|-------|
| Cell Extraction (4D) | 293 ClassifiedRows, many split | ~131 MergedRows, prices attached |
| Row Parsing (4E) | Parses split rows separately, loses prices | Parses complete merged rows |
| Post-Processing (5) | 109 items, 15% with price | ~131 items, ~90%+ with price |

**Cell extraction change**: Currently iterates `ClassifiedRow` objects. Must be updated to iterate `MergedRow.allElements` instead, which includes elements from all continuation rows merged into one.

### Files Changed

| File | Change | Details |
|------|--------|---------|
| `row_merger.dart` | NEW FILE | ~150-200 lines |
| `classified_rows.dart` | Add MergedRow + MergedRows models | ~60 lines |
| `stage_names.dart` | Add `rowMerging` constant | 1 line |
| `extraction_pipeline.dart` | Insert merger stage, update downstream inputs | ~20 lines |
| Cell extraction stage | Accept MergedRow instead of ClassifiedRow | TBD after reading cell extraction code |

---

## Phase 4: Test & Fixture Updates

### 4A: Stage Trace Diagnostic Test

**File**: `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`

| Update | Description |
|--------|-------------|
| New test group | "Stage 4A.5: Row Merging analysis" — load `springfield_merged_rows.json`, report merge stats |
| Scorecard updates | Stage 08 expectations (data=131, priceCont=~131, descCont=variable, headers=6) |
| Scorecard updates | Stage 11 page labels → 36/36 |
| Scorecard updates | Stage 14 grid rows → ~131 |
| Scorecard updates | Stage 16 w/unit_price → 120+, total $ → ~$7M+ |
| New fixture ref | Add `springfield_merged_rows.json` to fixture readiness check |
| Item traces | Update traces — prices should now appear in Parsed 4E and Processed 5 columns |

### 4B: Golden Fixture Generator

**File**: `integration_test/generate_golden_fixtures_test.dart`

| Update | Description |
|--------|-------------|
| New fixture emission | `springfield_merged_rows.json` — output from row merger stage |
| Stage mapping | Add `StageNames.rowMerging: 'springfield_merged_rows'` to `stageToFilename` (lines 15-39) |
| Pipeline call | Update to pass column definitions to row classifier |

### 4C: Contract Tests

| File | Update |
|------|--------|
| `stage_2_to_3_contract_test.dart` | Verify unchanged (OCR → validation contract unaffected) |
| `stage_4a_to_4b_contract_test.dart` | Rename/update — stage ordering changed. Row classification now outputs V3 types. |
| `stage_4b_to_4c_contract_test.dart` | Update — region detection → column detection contract may change |
| NEW: `stage_4a_to_merger_contract_test.dart` | V3 classified rows → merger input contract |
| NEW: `merger_to_4d_contract_test.dart` | Merged rows → cell extraction contract |

### 4D: Unit Tests

| File | Type | Description |
|------|------|-------------|
| `row_classifier_v3_test.dart` | NEW | Test each classification rule with synthetic rows |
| `row_merger_test.dart` | NEW | Test merging: DATA+PRICE, DATA+DESC+PRICE, orphans, edge cases |
| `stage_4c_column_detector_test.dart` | UPDATE | Label propagation tests |
| `extraction_pipeline_test.dart` | UPDATE | Pipeline includes merger, uses V3 classifier |
| `stage_4b_region_detector_test.dart` | UPDATE | May need update if input changes |

**V3 classifier test cases**:
- Row with item# in itemNumber column → DATA
- Row with only price/amount elements → PRICE_CONTINUATION (if preceded by DATA)
- Row with only text elements, no item# → DESC_CONTINUATION (if preceded by DATA)
- Row matching header keywords → HEADER
- Row with "TOTAL" + currency → TOTAL
- Wide text row, uppercase, no numbers → SECTION_HEADER
- Empty row → BLANK
- Everything else → BOILERPLATE
- Orphan price row (no preceding DATA) → should not be PRICE_CONTINUATION
- Sequence: DATA → PRICE_CONT → DESC_CONT → DATA (valid chain)
- Large Y-gap between rows → breaks continuation chain

**Row merger test cases**:
- Single DATA row with no continuations → MergedRow with 1 physical row
- DATA + PRICE_CONTINUATION → MergedRow with 2 physical rows, price attached
- DATA + DESC_CONTINUATION + PRICE_CONTINUATION → MergedRow with 3 physical rows
- DATA + PRICE_CONT + DESC_CONT (reversed order) → still merges correctly
- Orphan PRICE_CONTINUATION → attached to previous DATA or emitted as boilerplate
- HEADER rows pass through unchanged
- BLANK/BOILERPLATE rows skipped
- Multiple DATA rows in sequence (no continuations) → each becomes separate MergedRow

### 4E: Mock Stages

**File**: `test/features/pdf/extraction/helpers/mock_stages.dart`

| Update | Description |
|--------|-------------|
| Add MockRowMerger | Returns predefined MergedRows for pipeline tests |
| Update MockRowClassifier | Return V3 RowType values (priceContinuation, descContinuation, etc.) |
| Remove Phase 1B mock | No longer needed |

### 4F: Fixture Regeneration

**ALL Springfield fixtures must be regenerated** after code changes. Run the golden fixture generator integration test.

| Fixture | Expected Change |
|---------|----------------|
| `springfield_classified_rows.json` | New RowType values, ~131 data + ~131 priceCont + variable descCont |
| `springfield_column_map.json` | Pages 1-5 labels fixed (all 6/6) |
| `springfield_column_detection_layers.json` | Layer 3 removed for grid pages |
| `springfield_merged_rows.json` | NEW — ~131 merged items |
| `springfield_cell_grid.json` | ~131 grid rows instead of 293, prices populated |
| `springfield_parsed_items.json` | 131 items with prices |
| `springfield_processed_items.json` | Better post-processing input |
| `springfield_quality_report.json` | Improved scores |
| `springfield_phase1b_refinement.json` | REMOVED (Phase 1B eliminated) |
| `springfield_ocr_metrics.json` | Unchanged (upstream of all changes) |
| `springfield_grid_lines.json` | Unchanged |
| `springfield_unified_elements.json` | Unchanged |
| `springfield_document_profile.json` | Unchanged |
| Post-process sub-fixtures | Will change due to better input data |

---

## Execution Order (Detailed)

| Step | Phase | Description | Files | Depends On |
|------|-------|-------------|-------|------------|
| 1 | P1 | Add `_propagateGridPageLabels()` method | `column_detector_v2.dart` | — |
| 2 | P1 | Call propagation in `detect()` after grid labeling | `column_detector_v2.dart` | Step 1 |
| 3 | P1 | Skip anchor correction for grid-only docs | `column_detector_v2.dart` | — |
| 4 | P1 | Update column detector tests | `stage_4c_column_detector_test.dart` | Steps 1-3 |
| 5 | P1 | Regenerate column fixtures, verify scorecard | `springfield_column_map.json` etc. | Steps 1-3 |
| 6 | P2 | Update RowType enum (add/remove types) | `classified_rows.dart` | — |
| 7 | P2 | Fix all RowType references across codebase | Multiple files | Step 6 |
| 8 | P2 | Check region detector inputs (does it need classified rows?) | `region_detector_v2.dart` | — |
| 9 | P2 | Create `row_classifier_v3.dart` with zone-based algorithm | New file | Steps 6, 8 |
| 10 | P2 | Write V3 unit tests | New file | Step 9 |
| 11 | P2 | Reorder pipeline: move classification after column detection | `extraction_pipeline.dart` | Steps 8, 9 |
| 12 | P2 | Remove Phase 1B call from pipeline | `extraction_pipeline.dart` | Step 11 |
| 13 | P3 | Add MergedRow/MergedRows models | `classified_rows.dart` | Step 6 |
| 14 | P3 | Create `row_merger.dart` | New file | Step 13 |
| 15 | P3 | Write merger unit tests | New file | Step 14 |
| 16 | P3 | Add `rowMerging` stage name | `stage_names.dart` | — |
| 17 | P3 | Register merger in pipeline, update downstream inputs | `extraction_pipeline.dart` | Steps 14, 16 |
| 18 | P3 | Update cell extraction to accept MergedRow | Cell extraction file | Step 17 |
| 19 | P4 | Update mock stages | `mock_stages.dart` | Steps 9, 14 |
| 20 | P4 | Update/create contract tests | `stage_*_contract_test.dart` | Steps 11, 17 |
| 21 | P4 | Update stage trace diagnostic test + scorecard | `stage_trace_diagnostic_test.dart` | Steps 9, 14, 17 |
| 22 | P4 | Update golden fixture generator | `generate_golden_fixtures_test.dart` | Steps 16, 17 |
| 23 | P4 | Regenerate ALL Springfield fixtures | `springfield_*.json` | All code changes |
| 24 | P4 | Run full test suite, verify scorecard improvement | All tests | Step 23 |

---

## Expected Scorecard After Implementation

| Metric | Before | After (Expected) |
|--------|--------|-------------------|
| Stage 08: Data rows | 206 (BUG) | ~131 (OK) |
| Stage 08: Unknown rows | 96 (BUG) | 0 (OK) — type removed |
| Stage 08: Price continuations | N/A | ~131 (OK) — new metric |
| Stage 08: Desc continuations | 29 (BUG) | variable (OK) |
| Stage 08: Headers | 2 (BUG) | 6 (OK) |
| Stage 11: Page labels | 26/36 (BUG) | 36/36 (OK) |
| NEW: Row Merger: Merged rows | N/A | ~131 (OK) |
| NEW: Row Merger: w/ price cont | N/A | ~120+ (OK) |
| Stage 14: Grid rows | 293 (BUG) | ~131 (OK) |
| Stage 16: Parsed items | 135 (OK) | ~131 (OK) |
| Stage 16: GT matched | 105/131 80% (LOW) | ~125+ (OK) |
| Stage 16: w/ unit_price | 20 15% (BUG) | ~120+ (OK) |
| Stage 16: w/ bid_amount | 25 19% (BUG) | ~120+ (OK) |
| Stage 16: Total $ | $670K 9% (BUG) | ~$7M+ (OK) |
| Stage 23: Quality score | 0.794 (LOW) | >0.85 (OK) |
| Stage 23: Completeness | 61.8% (BUG) | ~90%+ (OK) |
| Stage 23: Checksum | FAIL (BUG) | Closer to PASS |
| **Overall** | **22 OK / 4 LOW / 22 BUG** | **~40 OK / 2 LOW / ~6 BUG** |

---

## Decisions Log

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Rewrite vs patch classifier | Rewrite (V3) | V2 designed for content-only scoring; V3 needs grid-aware zones. Clean slate for new pipeline. |
| 2 | Row types | 8 explicit types, no `unknown` | Every row should be classifiable with grid + column context |
| 3 | Grid-aware classification | Yes, use column semantics for zones | Dynamic zones avoid hardcoded column positions — works on any bid tab PDF |
| 4 | Column label fix | Template propagation from best-labeled page | Continuation pages inherently lack headers; per-page matching can't work |
| 5 | Anchor correction for grid pages | Disable | Grid geometry is pixel-precise; anchor correction adds no positional value |
| 6 | Layer selection bug | Not the root cause | Layer 3 inherits labels from Layer 0 — fixing selection alone doesn't fix labeling |
| 7 | Phase 1B refinement | Remove | V3 runs after column detection, has full context in single pass |
| 8 | Row merging | New stage after classification | Clean separation: classify rows → merge rows → extract cells |
| 9 | Pipeline reorder | Move classification after column detection | V3 needs column semantics as input; region detection may not need classified rows |

---

## Open Questions (Resolve During Implementation)

1. **Region detector dependency**: Does `region_detector_v2.dart` require `ClassifiedRows` as input, or only elements + grid lines? This determines if pipeline reorder is safe. (Step 8)
2. **Cell extraction input**: How tightly coupled is cell extraction to `ClassifiedRow`? May need adapter or interface change for `MergedRow`. (Step 18)
3. **Post-processor V2**: Does `post_processor_v2.dart` reference `RowType.continuation` or `RowType.unknown`? These types are being removed. (Step 7)
4. **Fixture generator timing**: Can we regenerate fixtures incrementally (after Phase 1, then after Phase 2+3) or only once at the end? Incremental is preferred for validation. (Steps 5, 23)
