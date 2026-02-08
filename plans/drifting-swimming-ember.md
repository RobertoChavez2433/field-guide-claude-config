# Fix Multi-Line Header Detection & Per-Page Header Extraction

## Context

The pipeline stage dumps from the Springfield DWSRF PDF show 88.5% valid items (15 invalid) with jumbled data. Root cause analysis reveals **two bugs** in the column detection stage:

1. **Page 0**: The header cell "Est.\nQuantity" spans two visual lines. Only "Est." is captured as a header element; "Quantity" on line 2 is missing entirely. This causes the quantity column to be missed (5 columns instead of 6), merging quantity data into unit cells.

2. **Pages 1-5**: `_detectColumnsPerPage()` at line 1039 hardcodes `headerRowElements: <OcrElement>[]` - it **never** passes header elements for per-page detection. All continuation pages fall to 0% confidence fallback, losing the correct column structure.

## Bug 1 Fix: Two-Line Header Scanning in `_extractHeaderRowElements()`

### Problem
`_extractHeaderRowElements()` collects elements matching `headerRowYPositions` with 40px tolerance. On page 0, "Est." (Y~2490) is collected but "Quantity" (line 2 of same cell, likely Y~2510-2520) is either not extracted by Syncfusion's native text layer, or falls outside the Y collection window.

### Fix: Expand Y scan to capture second header line

**File**: `lib/features/pdf/services/table_extraction/table_extractor.dart`
**Method**: `_extractHeaderRowElements()` (line 744)

After the initial collection of header elements (line 789-792), add a **second-line scan phase**:

1. Determine the Y range of collected elements (min/max Y of collected elements)
2. Calculate a "second line Y band" extending below the max Y by up to `kSecondLineYTolerance` (~30-40px below the lowest collected element)
3. Collect additional elements from the same page that fall within this second line band
4. Pass both first-line and second-line elements to `_combineMultiRowHeaders()`

```
// Pseudocode
if (headerRowElements.isNotEmpty) {
  final maxCollectedY = max(element.boundingBox.bottom for each element);
  final secondLineBand = maxCollectedY + kSecondLineYTolerance; // ~35px
  final secondLineElements = headerPageElements.where(
    element.yCenter > maxCollectedY && element.yCenter <= secondLineBand
  );
  headerRowElements.addAll(secondLineElements);
}
```

This ensures multi-line header cells like "Est.\nQuantity", "Unit\nPrice", "Bid\nAmount" all get both lines captured. The existing `_combineMultiRowHeaders()` will then merge vertically-aligned pairs (same X within 25px).

### Constants
- `kSecondLineYTolerance = 35.0` - Max distance below first header line to scan for second line

## Bug 2 Fix: Per-Page Header Element Extraction

### Problem
`_detectColumnsPerPage()` at line 1038-1039:
```dart
final detected = await columnDetector.detectColumns(
  headerRowElements: <OcrElement>[],  // ← ALWAYS EMPTY!
```

Pages 1-5 have repeated headers (visible in OCR at Y~176-184) but they're never extracted.

### Fix: Extract header elements per-page using repeated header Y positions

**File**: `lib/features/pdf/services/table_extraction/table_extractor.dart`
**Method**: `_detectColumnsPerPage()` (line 979)

For each continuation page (pageIdx != startPage), extract header elements using the per-page header Y positions:

1. The `headerRowYPositions` list already contains Y values for repeated headers on pages 1-5 (~176-184)
2. For each page, find elements whose Y position matches any of the non-startPage header Y positions (with 40px tolerance)
3. Apply the same second-line scan from Bug 1
4. Pass these elements as `headerRowElements` instead of an empty list

```
// For each page in the loop:
final pageHeaderElements = _extractPerPageHeaderElements(
  pageElements: pageElements,
  headerRowYPositions: tableRegion.headerRowYPositions,
  tableRegion: tableRegion,
  pageIdx: pageIdx,
);

final detected = await columnDetector.detectColumns(
  headerRowElements: pageHeaderElements,  // ← Actual elements!
  ...
);
```

### New helper method: `_extractPerPageHeaderElements()`
- For startPage: use existing `_extractHeaderRowElements()` logic
- For continuation pages: match elements against headerRowYPositions that are NOT near startY (the ones that were previously filtered out - Y~176-184)
- Apply the same two-line scan to capture multi-line headers on continuation pages
- The `_combineMultiRowHeaders()` in HeaderColumnDetector will handle merging

## Files to Modify

| File | Changes |
|------|---------|
| `lib/features/pdf/services/table_extraction/table_extractor.dart` | Add second-line scan to `_extractHeaderRowElements()`, add `_extractPerPageHeaderElements()`, update `_detectColumnsPerPage()` to pass real header elements |

## Verification

1. **Run existing PDF extraction tests**:
   ```
   pwsh -Command "flutter test test/features/pdf/table_extraction/"
   ```
   All 1373+ tests must continue passing.

2. **Run pipeline stage dumper tests**:
   ```
   pwsh -Command "flutter test test/features/pdf/table_extraction/pipeline_stage_dumper_test.dart"
   ```

3. **Run app with diagnostics** on the Springfield PDF:
   ```
   pwsh -Command "flutter run -d windows --dart-define=PDF_PARSER_DIAGNOSTICS=true"
   ```
   Verify:
   - `hasQuantityColumn: true` in stage dump
   - `globalColumnCount: 6`
   - Per-page detection shows non-zero header elements for pages 1-5
   - `validItemPercentage` improves from 88.5%

4. **Check pipeline dump artifacts** for:
   - `detectingColumns.end` should show `globalColumnNames` including `quantity`
   - Per-page columns should show > 0% confidence on continuation pages
