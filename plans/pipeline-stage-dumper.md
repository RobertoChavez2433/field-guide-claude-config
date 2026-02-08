# Pipeline Stage Dumper - Implementation Plan

## Context

After 316+ sessions of PDF extraction fixes, regressions keep appearing because there's no way to visually inspect what each pipeline stage produces. Debugging relies on scattered `debugPrint` statements and JSON diagnostic logs. This tool lets you open a single text file and see exactly what happened at every stage - where data was correct and where it went wrong.

## What We're Building

A Dart test file (`pipeline_stage_dumper_test.dart`) that:
1. Loads a JSON fixture (e.g., `springfield_page1.json`)
2. Runs each pipeline stage independently, capturing intermediate state
3. Writes a comprehensive text report to `Troubleshooting/pipeline_dumps/`

## Output Format

The dump file will be organized as a series of clearly separated stages, each showing ALL data (no truncation). Every stage shows its complete input/output as clean aligned tables.

### Stage Layout

```
================================================================================
  PIPELINE STAGE DUMP
  Fixture: springfield_page1.json
  Date: 2026-02-08 12:00:00
  Elements: 73 across 1 page(s)
================================================================================


================================================================================
  STAGE 1: RAW INPUT ELEMENTS
================================================================================

Page 0 (73 elements):

  #    Text                              X-Left  X-Right  Y-Top  Y-Bot  Conf
  ---  --------------------------------  ------  -------  -----  -----  ----
    0  BID SCHEDULE                         300      500     50     70  1.00
    1  ITEM                                  50       90    120    140  1.00
    2  NO.                                   50       90    145    165  1.00
    3  DESCRIPTION OF WORK                  120      380    120    165  1.00
    4  QUANTITY                             400      480    120    165  1.00
    5  UNIT                                 500      560    120    165  1.00
    6  UNIT PRICE                           580      670    120    165  1.00
    7  AMOUNT                               690      750    120    165  1.00
    8  1                                     50       90    180    200  1.00
    9  Mobilization                         120      280    180    200  1.00
   10  1                                    400      480    180    200  1.00
   11  LS                                   500      560    180    200  1.00
   12  $50,000.00                           580      670    180    200  1.00
   13  $50,000.00                           690      750    180    200  1.00
  ... (all elements listed)


================================================================================
  STAGE 2: ROW CLASSIFICATION
================================================================================

  Row  Page  Y-Pos   Type           Conf   Elements  Keywords  Digits  Text Preview
  ---  ----  ------  -------------  -----  --------  --------  ------  ----------------------------------
    0     0   120.0  HEADER          0.95         7         4    0.0%  ITEM NO. DESCRIPTION OF WORK QUA...
    1     0   180.0  DATA            0.90         6         0   33.3%  1 Mobilization 1 LS $50,000.00 ...
    2     0   215.0  DATA            0.90         6         0   33.3%  2 Traffic Control 1 LS $25,000....
    3     0   250.0  DATA            0.90         6         0   33.3%  3 Clearing and Grubbing 5.2 AC ...
  ... (all rows listed)


================================================================================
  STAGE 3: TABLE REGION
================================================================================

  Detection: V2 (RowClassifier + RegionDetector)

  Start Page:  0          End Page:  0
  Start Y:     120.0      End Y:     515.0

  Header Y Positions:
    [0]  120.0
    [1]  145.0

  Elements in table region: 67 of 73 total (6 excluded - above/below table)

  Excluded elements:
    "BID SCHEDULE" at y:50 (above table start y:120)


================================================================================
  STAGE 4: COLUMN BOUNDARIES
================================================================================

  Detection Method:  HEADER
  Confidence:        95.0%

  Column         Start-X   End-X    Width   Header Element(s)
  -----------    -------   ------   -----   ---------------------------
  itemNumber          50      110      60   "ITEM", "NO."
  description        120      390     270   "DESCRIPTION OF WORK"
  quantity           400      490      90   "QUANTITY"
  unit               500      570      70   "UNIT"
  unitPrice          580      680     100   "UNIT PRICE"
  bidAmount          690      760      70   "AMOUNT"

  X-Axis Map (0 to 800):
  0         50   110 120                              390 400   490 500 570 580    680 690  760    800
  |          |===|   |================================|   |=====|   |===|   |======|   |====|       |
             Item#   Description                          Qty       Unit   Price      Amount


================================================================================
  STAGE 5: CELL EXTRACTION (Element-to-Column Assignment)
================================================================================

Each row shows what text landed in each column, plus which elements were assigned.

  Row  Page  Y-Pos   itemNumber    description                 quantity  unit  unitPrice    bidAmount
  ---  ----  ------  ----------    -------------------------   --------  ----  ----------   ----------
    0     0   130.0  ITEM/NO.      DESCRIPTION OF WORK         QUANTITY  UNIT  UNIT PRICE   AMOUNT
    1     0   190.0  1             Mobilization                1         LS    $50,000.00   $50,000.00
    2     0   225.0  2             Traffic Control              1         LS    $25,000.00   $25,000.00
    3     0   260.0  3             Clearing and Grubbing        5.2       AC    $2,500.00    $13,000.00
    4     0   295.0  4             Unclassified Excavation      1,250     CY    $15.00       $18,750.00
    5     0   330.0  5             Embankment, Common Borrow    850       CY    $12.00       $10,200.00
    6     0   365.0  6             Subgrade Compaction          3,500     SY    $3.50        $12,250.00
    7     0   400.0  7             Aggregate Base Course, 6 in  2,800     SY    $8.00        $22,400.00
    8     0   435.0  8             Hot Mix Asphalt, Type B      650       TON   $95.00       $61,750.00
    9     0   470.0  9             Concrete Curb and Gutter, T  1,200     LF    $22.00       $26,400.00
   10     0   505.0  10            Concrete Sidewalk, 5 inch    450       SY    $45.00       $20,250.00

  Unassigned elements (outside all column boundaries): 0
  Re-OCR'd cells: 0


================================================================================
  STAGE 6: PARSED BID ITEMS
================================================================================

  #   Item#  Description                   Qty        Unit  UnitPrice     Conf  Warnings
  --  -----  ---------------------------   ---------  ----  -----------   ----  --------
   1  1      Mobilization                       1.00  LS     $50,000.00  1.00
   2  2      Traffic Control                    1.00  LS     $25,000.00  1.00
   3  3      Clearing and Grubbing              5.20  AC      $2,500.00  1.00
   4  4      Unclassified Excavation        1,250.00  CY         $15.00  1.00
   5  5      Embankment, Common Borrow        850.00  CY         $12.00  1.00
   6  6      Subgrade Compaction            3,500.00  SY          $3.50  1.00
   7  7      Aggregate Base Course, 6 in    2,800.00  SY          $8.00  1.00
   8  8      Hot Mix Asphalt, Type B          650.00  TON        $95.00  1.00
   9  9      Concrete Curb and Gutter, T    1,200.00  LF         $22.00  1.00
  10  10     Concrete Sidewalk, 5 inch        450.00  SY         $45.00  1.00

  RAW vs PARSED comparison (showing only items where raw != parsed):
  (none - all items parsed cleanly)


================================================================================
  STAGE 7: POST-PROCESSING
================================================================================

  Input:  10 items
  Output: 10 items

  Changes Applied:
    Splits:     0
    Merges:     0
    Repairs:    0
    Dedupes:    0

  Repair Notes:
    (none)


================================================================================
  SUMMARY
================================================================================

  Pipeline:     fixture -> rowClassify -> tableRegion -> columns -> cells -> parse -> postProcess
  Elements:     73 input -> 67 in table -> 11 rows -> 10 items (1 header skipped)
  Columns:      HEADER method, 95.0% confidence
  Quality:      10/10 items valid (100%), avg confidence 1.00
  Warnings:     0 total

  VERDICT: CLEAN EXTRACTION
```

## Files to Create

### 1. Test file: `test/features/pdf/table_extraction/pipeline_stage_dumper_test.dart`

This is the main file. It:
- Loads fixtures via `FixtureLoader`
- Calls each pipeline component independently (same order as `TableExtractor.extract()`)
- Builds a `StringBuffer` with formatted output
- Writes to `Troubleshooting/pipeline_dumps/<fixture_name>_dump.txt`

**Pipeline stages to replicate** (matching `table_extractor.dart` exactly):

```
1. Build ocrByPage map from fixture
2. RowClassifier.classifyAllRows(ocrByPage)  ->  List<RowClassification>
3. TableRegionDetector.detectRegions(rowClassifications)  ->  List<TableRegion>
4. _extractHeaderRowElements (replicate logic from table_extractor.dart:568-681)
5. HeaderColumnDetector.detectColumns(headerElements, tableWidth, tableStartX)  ->  ColumnBoundaries
6. CellExtractor.extractRows(columnBoundaries, tableElements)  ->  List<TableRow>
7. TableRowParser.parseRows(rows, rowClassifications: ...)  ->  List<ParsedBidItem>
8. PostProcessEngine.process(items)  ->  ProcessedResult
```

**Components used directly** (no mocks - real pipeline):
- `RowClassifier` from `row_classifier.dart`
- `TableRegionDetector` from `table_region_detector.dart`
- `TableLocator` from `table_locator.dart` (legacy fallback)
- `HeaderColumnDetector` from `header_column_detector.dart`
- `CellExtractor` from `cell_extractor.dart`
- `TableRowParser` from `table_row_parser.dart`
- `PostProcessEngine` from `post_process/post_process_engine.dart`
- `FixtureLoader` from `fixtures/fixture_loader.dart`

### 2. Output directory: `Troubleshooting/pipeline_dumps/`

Already exists as `Troubleshooting/` - just add a subdirectory.

## Key Design Decisions

1. **Uses synchronous `extractRows()`** not `extractRowsWithReOcr()` - no OCR engine needed for fixtures
2. **Shows ALL rows** - no truncation, the user scrolls
3. **X-Axis Map** in Stage 4 - ASCII visualization of column positions on a number line
4. **RAW vs PARSED diff** in Stage 6 - only shows items where raw differs from parsed (highlights where parsing changed data)
5. **VERDICT line** - quick pass/fail summary: CLEAN EXTRACTION / DEGRADED / FAILED
6. **Multiple fixture support** - separate test per fixture, each produces its own dump file

## Fixtures to Dump

Each fixture gets its own test and dump file:
- `springfield_page1.json` -> `springfield_page1_dump.txt`
- `springfield_page2.json` -> `springfield_page2_dump.txt`
- `springfield_real_v2.json` -> `springfield_real_v2_dump.txt`
- `springfield_edge_cases.json` -> `springfield_edge_cases_dump.txt`

## Verification

1. Run: `pwsh -Command "flutter test test/features/pdf/table_extraction/pipeline_stage_dumper_test.dart"`
2. Check output: Open `Troubleshooting/pipeline_dumps/springfield_page1_dump.txt`
3. Verify: All 8 stages present, all rows shown, X-axis map renders correctly
4. Compare: Run against edge case fixtures and verify divergence is visible
