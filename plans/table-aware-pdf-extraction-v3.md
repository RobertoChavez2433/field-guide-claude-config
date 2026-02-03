# Plan V3: Table-Aware PDF Extraction (Unified Pipeline)

## Overview

**Purpose**: Reliably extract bid schedule tables from any PDF type (digital with bad text layers, scanned/image-only).

**Key Decision**: Complete refactor with new `TableExtractor` pipeline. No legacy cases to preserve - previous implementation never achieved acceptable accuracy.

## Problems Solved

| Problem | Example | Solution |
|---------|---------|----------|
| Price in description | "Monument Box, Adjust S700.00\|" | Column boundary detection |
| OCR artifacts | "S700" instead of "$700", "ÉA" instead of "EA" | OCR postprocessing cleanup |
| Boilerplate parsed as items | Item 1.02 = "Name of Project: DWSRF..." | Table start auto-detection |
| Missing unit prices | Item shows "No unit price" | Cell-level re-OCR when merged |
| Contract text as items | Item 1.03 = "The undersigned Bidder..." | Boilerplate filtering |
| Cross-page mixing | Elements from page 1 mixed with page 2 | Page-aware processing |

## Core Strategy

1. **Auto-detect table start** - Skip contract boilerplate, find actual bid schedule
2. **Dual column detection** - Header-based AND line-based with cross-validation
3. **Cell-level re-OCR** - When OCR returns merged blocks spanning columns
4. **Accuracy over speed** - No hard time limit, show progress feedback
5. **Opportunistic robustness** - Use repeated headers when present, gracefully continue when not

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. TABLE LOCATOR                                                │
│    - Find "Item No." / "Description" headers                    │
│    - Detect table grid lines                                    │
│    - Skip contract boilerplate (Articles, legal text)           │
│    - Output: TableRegion (page range, Y bounds)                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. COLUMN DETECTOR                                              │
│    - Header-based: X positions of header keywords               │
│    - Line-based: Vertical grid lines from image                 │
│    - Cross-validate both methods                                │
│    - Output: ColumnBoundaries (list of X ranges per column)     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. CELL EXTRACTOR                                               │
│    - For each row, extract text per column                      │
│    - Detect merged blocks spanning columns                      │
│    - Re-OCR individual cells if needed                          │
│    - Output: List<TableRow> with cell values                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. ROW PARSER                                                   │
│    - Convert cells to typed fields (itemNo, desc, unit, etc.)   │
│    - Skip header rows (including repeated headers)              │
│    - Validate: item number format, unit is known, price > 0     │
│    - Output: List<ParsedBidItem>                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Table Locator

**Purpose**: Find where the actual bid schedule table starts, skipping contract boilerplate.

**Input**: Rendered page images + OCR text

**Detection Strategy** (in order of reliability):

| Signal | How to Detect | Confidence |
|--------|---------------|------------|
| Header row | "Item No." + "Description" + "Unit" on same Y-line | High |
| "BASE BID" marker | Text contains "BASE BID" - table follows | High |
| Grid lines | Horizontal + vertical lines forming cells | Medium |
| Dense numbers | High density of numeric patterns (item #, qty, $) | Low |

**Algorithm**:
```
1. Scan pages top-to-bottom
2. Look for header keywords within Y-threshold
3. If found, record as tableStartY
4. Look for "BASE BID" or similar markers as confirmation
5. Table ends at: last row with item number pattern OR page end
```

**Boilerplate Filtering**:
- Skip lines containing: "ARTICLE", "SECTION 00", "undersigned", "proposes and agrees"
- Skip lines before first header row detection
- Skip lines with no numeric content in first column position

**Output**:
```dart
class TableRegion {
  final int startPage;
  final int endPage;
  final double startY;  // Y position where table begins
  final double? endY;   // Y position where table ends (null = page bottom)
  final List<int> headerRowYPositions;  // For repeated header detection
}
```

---

## Stage 2: Column Detector

**Purpose**: Determine exact X-boundaries for each column using multiple signals.

**Input**: TableRegion + page images + OCR elements

### Method A: Header-Based
```
1. Find header row (already located by TableLocator)
2. Extract OCR elements on header Y-line
3. Match keywords: "Item", "Description", "Unit", "Quantity", "Price", "Amount"
4. Column boundary = midpoint between adjacent header centers
```

### Method B: Line-Based
```
1. Convert page image to grayscale
2. Apply edge detection (Sobel or Canny)
3. Find vertical lines: scan for continuous dark pixels in Y direction
4. Cluster X-positions of detected lines
5. Filter: lines must span >50% of table height
```

### Cross-Validation
```
1. Run both methods independently
2. Compare boundary positions (tolerance: 10px)
3. If aligned: HIGH confidence
4. If misaligned: prefer line-based (visual ground truth)
5. If line detection fails: fall back to header-based
6. If both fail: use standard column ratios as last resort
```

**Standard Column Ratios** (fallback):
| Column | % of table width |
|--------|------------------|
| Item No. | 8% |
| Description | 42% |
| Unit | 10% |
| Est. Quantity | 12% |
| Unit Price | 14% |
| Bid Amount | 14% |

**Output**:
```dart
class ColumnBoundaries {
  final List<ColumnDef> columns;
  final ColumnDetectionMethod method;  // header, lines, crossValidated, fallback
  final double confidence;
}

class ColumnDef {
  final String name;  // "itemNumber", "description", etc.
  final double startX;
  final double endX;
}
```

---

## Stage 3: Cell Extractor

**Purpose**: Extract text from each cell, handling merged OCR blocks.

**Input**: ColumnBoundaries + OCR elements per page

**Algorithm**:
```
1. Group OCR elements by Y-position (row clustering)
2. For each row:
   a. Assign elements to columns based on X-position
   b. Detect merged blocks (element spans multiple columns)
   c. If merged: trigger cell-level re-OCR
3. Output structured cells per row
```

**Merged Block Detection**:
```dart
bool isMergedBlock(OcrElement element, ColumnBoundaries bounds) {
  int columnsSpanned = 0;
  for (final col in bounds.columns) {
    if (element.overlapsX(col.startX, col.endX)) {
      columnsSpanned++;
    }
  }
  return columnsSpanned > 1;
}
```

**Cell-Level Re-OCR**:
```
When merged block detected:
1. For each column the block spans:
   a. Crop image to cell region (columnX, rowY, columnWidth, rowHeight)
   b. Run ML Kit OCR on cropped cell
   c. Use cell-specific result instead of merged text
2. Cache cell images to avoid re-rendering page
```

**Row Boundary Detection**:
- Primary: Horizontal grid lines from image
- Fallback: Y-clustering of OCR elements (current approach)
- Validation: Row height should be consistent (±20%)

**Output**:
```dart
class TableRow {
  final int rowIndex;
  final int pageIndex;
  final double yPosition;
  final Map<String, CellValue> cells;  // columnName -> value
  final bool usedCellReOcr;  // for diagnostics
}

class CellValue {
  final String text;
  final double confidence;
  final Rect bounds;
}
```

---

## Stage 4: Row Parser

**Purpose**: Convert raw cell text to typed `ParsedBidItem` fields with validation.

**Input**: List<TableRow>

**Parsing Rules per Column**:

| Column | Parse Logic | Validation |
|--------|-------------|------------|
| Item No. | Extract digits, allow decimals (e.g., "6", "203.03") | Must match `^\d+(\.\d+)?$` |
| Description | Trim whitespace, remove OCR artifacts | Non-empty, no price patterns |
| Unit | Uppercase, map aliases (e.g., "Ft" → "FT") | Must be in `knownUnits` |
| Est. Quantity | Parse number, handle commas | Must be > 0 |
| Unit Price | Strip `$`, parse number, handle `S` → `$` OCR error | Must be >= 0 |
| Bid Amount | Same as Unit Price | Optional (can be calculated) |

**Header Row Skipping**:
```dart
bool isHeaderRow(TableRow row) {
  final itemCell = row.cells['itemNumber']?.text.toUpperCase();
  final descCell = row.cells['description']?.text.toUpperCase();

  // Check for header keywords
  if (itemCell == 'ITEM' || itemCell == 'NO.' || itemCell == 'ITEM NO.') {
    return true;
  }
  if (descCell == 'DESCRIPTION') {
    return true;
  }
  return false;
}
```

**Repeated Header Handling**:
- Detect headers on pages 2+ and skip as items
- Optionally use repeated headers to validate column alignment consistency
- Do NOT fail if headers are not repeated - graceful degradation

**OCR Artifact Cleanup**:
```dart
String cleanPrice(String raw) {
  return raw
    .replaceAll('S', '\$')      // OCR: S → $
    .replaceAll('|', '')        // Stray pipes
    .replaceAll(RegExp(r'[ÉÈ]'), 'E')  // Accented E
    .replaceAll(RegExp(r'[^0-9\$.,]'), '');  // Keep only valid chars
}
```

**Confidence Scoring**:
```
+0.2 if itemNumber valid format
+0.2 if unit in knownUnits
+0.2 if quantity > 0
+0.2 if unitPrice >= 0
+0.2 if description has no price patterns
```

**Output**: `List<ParsedBidItem>` with confidence scores and warnings

---

## Progress UX & Diagnostics

**Progress Feedback**:
```
┌─────────────────────────────────────────┐
│  Processing PDF...                      │
│  This may take a few minutes.           │
│                                         │
│  ████████░░░░░░░░░░░░  Page 2 of 6      │
│                                         │
│  ✓ Table located                        │
│  ✓ Column boundaries detected           │
│  ● Extracting cells...                  │
│  ○ Parsing rows                         │
└─────────────────────────────────────────┘
```

**Progress Stages**:
```dart
enum ExtractionStage {
  rendering,        // "Rendering pages..."
  locatingTable,    // "Finding table..."
  detectingColumns, // "Detecting columns..."
  extractingCells,  // "Extracting cells..."
  reOcrCells,       // "Re-processing cells..." (only if needed)
  parsingRows,      // "Parsing bid items..."
  complete,         // "Done!"
}
```

**Diagnostics Metadata**:
```dart
class TableExtractionDiagnostics {
  final Duration totalTime;
  final int pagesProcessed;
  final TableRegion? tableRegion;
  final ColumnDetectionMethod columnMethod;
  final double columnConfidence;
  final int totalRowsFound;
  final int headerRowsSkipped;
  final int cellsReOcrd;
  final int itemsExtracted;
  final List<String> warnings;
}
```

**Warning Examples**:
- "Column detection fell back to standard ratios"
- "12 cells required re-OCR due to merged blocks"
- "Page 3 header row skipped"
- "Item 45: unit 'XYZ' not recognized, kept as-is"

---

## File Structure

**New Files**:
```
lib/features/pdf/services/table_extraction/
├── table_extractor.dart              # Main orchestrator
├── table_locator.dart                # Stage 1: Find table region
├── column_detector.dart              # Stage 2: Detect boundaries
│   ├── header_column_detector.dart   # Method A
│   └── line_column_detector.dart     # Method B
├── cell_extractor.dart               # Stage 3: Extract cell text
├── table_row_parser.dart             # Stage 4: Parse to bid items
└── models/
    ├── table_region.dart
    ├── column_boundaries.dart
    ├── table_row.dart
    └── extraction_diagnostics.dart
```

**Modified Files**:
```
lib/features/pdf/services/
├── pdf_import_service.dart           # Wire in TableExtractor
└── ocr/
    └── ml_kit_ocr_service.dart       # Add cell-level OCR method

lib/features/pdf/presentation/
└── screens/
    └── pdf_import_screen.dart        # Add progress UI
```

**Test Files**:
```
test/features/pdf/table_extraction/
├── table_locator_test.dart
├── column_detector_test.dart
├── cell_extractor_test.dart
├── table_row_parser_test.dart
├── table_extractor_integration_test.dart
└── fixtures/
    └── springfield_ocr_elements.json # Real test data
```

**Files to Deprecate** (after new pipeline proven):
```
lib/features/pdf/services/ocr/
├── ocr_row_reconstructor.dart        # Replaced by cell_extractor
└── ocr_row_parser.dart               # Replaced by table_row_parser
```

---

## Implementation Phases (PR Breakdown)

### PR 1: Foundation & Models
- Create `table_extraction/` directory structure
- Implement model classes: `TableRegion`, `ColumnBoundaries`, `TableRow`, `CellValue`, `ExtractionDiagnostics`
- Unit tests for models
- No integration yet

### PR 2: Table Locator
- Implement `TableLocator` class
- Header row detection (keyword matching + Y-clustering)
- "BASE BID" marker detection
- Boilerplate filtering logic
- Unit tests with mock OCR elements
- Integration test with Springfield fixture

### PR 3: Column Detector - Header Based
- Implement `HeaderColumnDetector`
- Find header keywords, calculate midpoints
- Confidence scoring
- Standard ratio fallback
- Unit tests

### PR 4: Column Detector - Line Based
- Implement `LineColumnDetector`
- Image grayscale conversion
- Vertical line detection (edge detection)
- X-position clustering
- Unit tests with test images

### PR 5: Column Detector - Unified
- Implement `ColumnDetector` (orchestrator)
- Cross-validation logic
- Method selection based on confidence
- Integration tests

### PR 6: Cell Extractor
- Implement `CellExtractor`
- Element-to-column assignment
- Merged block detection
- Cell-level re-OCR integration
- Add `recognizeRegion()` to `MlKitOcrService`
- Unit tests

### PR 7: Table Row Parser
- Implement `TableRowParser`
- Cell text → typed fields
- OCR artifact cleanup
- Header row skipping
- Confidence scoring
- Unit tests

### PR 8: Table Extractor Orchestrator
- Implement `TableExtractor` (main class)
- Wire all stages together
- Progress callback support
- Diagnostics collection
- Integration tests with Springfield PDF

### PR 9: UI Integration
- Progress dialog in `pdf_import_screen.dart`
- Stage-by-stage feedback
- "Processing PDF... This may take a few minutes." message
- Wire `TableExtractor` into `PdfImportService`

### PR 10: Cleanup & Polish
- Deprecate old `OcrRowReconstructor` and `OcrRowParser`
- Update diagnostics logging
- Add Springfield PDF as CI fixture
- Final integration tests

---

## Acceptance Criteria

- [ ] Extract all 131+ items from Springfield PDF with correct columns
- [ ] No prices in description fields
- [ ] No missing quantities when table shows them
- [ ] Contract boilerplate (Articles 1-3) not parsed as items
- [ ] Repeated headers on pages 2+ skipped (not parsed as items)
- [ ] Progress UI shows stage-by-stage feedback
- [ ] Diagnostics logged for debugging

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Line detection fails (no grid lines) | Fall back to header-based, then standard ratios |
| Header OCR is garbled | Line detection provides visual ground truth |
| Cell re-OCR is slow | Cache page images, only re-OCR problematic cells |
| Memory pressure on large PDFs | Existing DPI guardrails, process page-by-page |
| New pipeline breaks other PDFs | Keep old code until new pipeline proven on multiple PDFs |

---

## Test Fixtures Needed

1. **Springfield PDF** - Primary test case with grid lines, 6 pages, 131 items
2. **Scanned PDF** - Image-only, no text layer
3. **Digital PDF with bad text** - Text layer exists but garbled
4. **PDF without grid lines** - Header-based detection only
5. **PDF with repeated headers** - Validate header skipping
6. **PDF without repeated headers** - Validate graceful handling

---

## Agent Assignments

| PR | Agent |
|----|-------|
| PR 1-2 | pdf-agent |
| PR 3-5 | pdf-agent |
| PR 6-7 | pdf-agent |
| PR 8 | pdf-agent |
| PR 9 | frontend-flutter-specialist-agent |
| PR 10 | code-review-agent + qa-testing-agent |

---

## Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Complete refactor over incremental fix | No working legacy cases to preserve | 2026-02-02 |
| Auto-detect table start | Best UX for field users | 2026-02-02 |
| Dual column detection with cross-validation | Most robust for any PDF type | 2026-02-02 |
| Cell-level re-OCR for merged blocks | Most accurate extraction | 2026-02-02 |
| No hard time limit | Accuracy over speed, with progress feedback | 2026-02-02 |
| Opportunistic header validation | Use when present, don't fail when absent | 2026-02-02 |
| Unified `TableExtractor` pipeline | Clean architecture, single responsibility | 2026-02-02 |
