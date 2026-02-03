# Plan: Table-Aware PDF Extraction (Layered Approach)

## Problem Statement
The app's PDF parsing cannot correctly extract bid schedule tables from scanned PDFs. The PDF has:
- Bad embedded text from scanner OCR (garbage like "sEcTroN", "s3 90.000.00")
- Clear visual table structure with grid lines
- Boilerplate text (Articles 1-3) before the table
- 131 bid items across 6 pages

Current extraction produces:
- Item 115: "Monument Box, Adjust S700.00|" (price in description, wrong chars)
- Should be: Description="Monument Box, Adjust", Price="$700.00"

## Root Cause
**The table has visible grid lines that define exact column boundaries, but we're not detecting or using them.**

## Proposed Solution: Layered Column Detection

**Layer 1: Header-Based Detection (Fast Path)**
- Find header row via OCR ("Item No", "Description", "Unit", etc.)
- Use header word bounding boxes to define column boundaries
- Apply those boundaries to assign all OCR elements to columns

**Layer 2: Table Line Detection (Verification/Fallback)**
- Detect actual vertical grid lines in rendered image
- Use line positions to verify/correct column boundaries
- Fall back to this if header detection fails or confidence is low

**Layer 3: Cross-Validation**
- Compare columns from both methods
- Flag discrepancies for review
- Use line detection as ground truth when methods disagree

---

## Implementation Details

### New Files
```
lib/features/pdf/services/ocr/
├── table_line_detector.dart    # Detect grid lines in images
├── header_column_detector.dart # Find columns via header OCR
└── column_detector.dart        # Unified interface, layered detection
```

### Modified Files
```
lib/features/pdf/services/pdf_import_service.dart
  - Use ColumnDetector before row reconstruction
lib/features/pdf/services/ocr/ocr_row_reconstructor.dart
  - Accept column boundaries, assign elements to columns
```

---

## Layer 1: Header-Based Column Detection

**Purpose:** Fast, works when header row is clearly OCR'd

```dart
/// header_column_detector.dart
class HeaderColumnDetector {
  /// Header keywords to find
  static const headerKeywords = ['item', 'description', 'unit', 'quantity', 'price', 'amount'];

  /// Find column boundaries from header row OCR elements
  ColumnBoundaries? detectFromHeader(List<OcrElement> elements, int pageWidth) {
    // 1. Find elements matching header keywords
    // 2. Group by Y position (find the header row)
    // 3. Extract X positions of each header word
    // 4. Define column boundaries between headers
    // 5. Return ColumnBoundaries with confidence score
  }
}

class ColumnBoundaries {
  final double itemNoStart;
  final double descriptionStart;
  final double unitStart;
  final double quantityStart;
  final double unitPriceStart;
  final double bidAmountStart;
  final double confidence; // 0.0-1.0
}
```

**Algorithm:**
1. Scan OCR elements for header keywords
2. Find row where multiple keywords appear (Y-clustering)
3. Get X position of each keyword's bounding box
4. Column boundary = midpoint between adjacent headers
5. Confidence based on: how many headers found, alignment consistency

---

## Layer 2: Table Line Detection

**Purpose:** Ground truth from visual grid, verification

```dart
/// table_line_detector.dart
class TableLineDetector {
  /// Detect vertical lines in page image
  Future<List<double>> detectVerticalLines(
    Uint8List imageBytes,
    int width,
    int height,
  ) async {
    // 1. Convert to grayscale
    // 2. Threshold to binary (dark lines become white on black)
    // 3. Scan columns: find X positions where vertical run > 50% of height
    // 4. Cluster nearby X positions (lines may be slightly wobbly)
    // 5. Return sorted list of X positions
  }

  /// Detect horizontal lines (for row boundaries)
  Future<List<double>> detectHorizontalLines(...) async {
    // Similar but scan rows
  }

  /// Convert line positions to column boundaries
  ColumnBoundaries linesToBoundaries(List<double> verticalLines, int pageWidth) {
    // Map detected lines to column semantics
    // First line after left margin = item no start
    // etc.
  }
}
```

**Algorithm (simple line detection):**
```dart
List<double> findVerticalLines(Uint8List grayscale, int width, int height) {
  final lines = <double>[];
  final threshold = 50; // Dark pixel threshold
  final minRunLength = height * 0.4; // Line must span 40% of page

  for (int x = 0; x < width; x++) {
    int runLength = 0;
    int maxRun = 0;

    for (int y = 0; y < height; y++) {
      final pixel = grayscale[y * width + x];
      if (pixel < threshold) {
        runLength++;
        maxRun = max(maxRun, runLength);
      } else {
        runLength = 0;
      }
    }

    if (maxRun >= minRunLength) {
      lines.add(x.toDouble());
    }
  }

  return clusterLines(lines, tolerance: 5.0);
}
```

---

## Layer 3: Unified Column Detector

```dart
/// column_detector.dart
class ColumnDetector {
  final HeaderColumnDetector _headerDetector;
  final TableLineDetector _lineDetector;

  /// Detect columns using layered approach
  Future<ColumnBoundaries> detectColumns(
    List<OcrElement> ocrElements,
    Uint8List pageImage,
    int width,
    int height,
  ) async {
    // Layer 1: Try header detection (fast)
    final headerResult = _headerDetector.detectFromHeader(ocrElements, width);

    // Layer 2: Run line detection (ground truth)
    final lineResult = await _lineDetector.detectVerticalLines(pageImage, width, height);
    final lineBoundaries = _lineDetector.linesToBoundaries(lineResult, width);

    // Layer 3: Cross-validate
    if (headerResult != null && lineBoundaries != null) {
      // Compare boundaries, use line detection if significant mismatch
      if (_boundariesMatch(headerResult, lineBoundaries, tolerance: 20.0)) {
        return headerResult.copyWith(confidence: 0.95); // High confidence
      } else {
        // Mismatch - trust line detection
        debugPrint('[ColumnDetector] Header/line mismatch, using line detection');
        return lineBoundaries.copyWith(confidence: 0.85);
      }
    }

    // Fallback: use whichever worked
    return lineBoundaries ?? headerResult ?? _defaultBoundaries(width);
  }
}
```

---

## Integration with Row Reconstructor

```dart
/// Updated ocr_row_reconstructor.dart
class OcrRowReconstructor {
  /// Reconstruct rows WITH column boundaries
  List<OcrRow> reconstructRowsWithColumns(
    List<OcrElement> elements,
    ColumnBoundaries columns,
  ) {
    // 1. Group elements by Y (existing logic)
    final rows = _groupByY(elements);

    // 2. For each row, assign elements to columns by X position
    for (final row in rows) {
      for (final element in row.elements) {
        element.column = _assignColumn(element.boundingBox.left, columns);
      }
    }

    // 3. Build OcrRow with column assignments
    return rows.map((r) => OcrRow(
      elements: r.elements,
      itemNo: _getColumnText(r, Column.itemNo),
      description: _getColumnText(r, Column.description),
      unit: _getColumnText(r, Column.unit),
      quantity: _getColumnText(r, Column.quantity),
      unitPrice: _getColumnText(r, Column.unitPrice),
      bidAmount: _getColumnText(r, Column.bidAmount),
    )).toList();
  }

  Column _assignColumn(double x, ColumnBoundaries cols) {
    if (x < cols.descriptionStart) return Column.itemNo;
    if (x < cols.unitStart) return Column.description;
    if (x < cols.quantityStart) return Column.unit;
    if (x < cols.unitPriceStart) return Column.quantity;
    if (x < cols.bidAmountStart) return Column.unitPrice;
    return Column.bidAmount;
  }
}
```

---

## Implementation Steps

### PR 1: Header-Based Column Detection (3-4 hours)
- [ ] Create `header_column_detector.dart`
- [ ] Implement header keyword search in OCR elements
- [ ] Y-clustering to find header row
- [ ] Extract X positions as column boundaries
- [ ] Add 10+ unit tests
- [ ] Integrate with `ocr_row_reconstructor.dart`
- [ ] Test on Springfield PDF

### PR 2: Table Line Detection (4-5 hours)
- [ ] Create `table_line_detector.dart`
- [ ] Implement grayscale conversion (use image package)
- [ ] Implement vertical line scanning
- [ ] Implement line clustering
- [ ] Add 10+ unit tests with test images
- [ ] Verify on Springfield PDF pages

### PR 3: Unified Column Detector (2-3 hours)
- [ ] Create `column_detector.dart`
- [ ] Implement layered detection logic
- [ ] Cross-validation between methods
- [ ] Confidence scoring
- [ ] Integration tests

### PR 4: Pipeline Integration (2-3 hours)
- [ ] Update `pdf_import_service.dart` to use ColumnDetector
- [ ] Pass columns to row reconstructor
- [ ] Update diagnostics to log column detection
- [ ] End-to-end test on Springfield PDF

### PR 5: Edge Cases & Polish (2-3 hours)
- [ ] Handle multi-page column consistency
- [ ] Handle wrapped descriptions (multi-line cells)
- [ ] Handle missing columns gracefully
- [ ] Performance optimization

---

## Verification

### Success Criteria
- [ ] 131 bid items extracted (not 136 with boilerplate)
- [ ] No prices in description fields
- [ ] No OCR artifacts (|, É, S instead of $)
- [ ] Unit prices correctly populated (not $0.00)
- [ ] Quantities correctly extracted
- [ ] Total verifiable: $7,882,926.73

### Test Cases
- [ ] Springfield PDF (primary test case)
- [ ] Native digital PDF (should still work)
- [ ] PDF without grid lines (header detection only)
- [ ] PDF with partial grid (graceful degradation)

---

## Files Summary

| File | Type | Purpose |
|------|------|---------|
| `header_column_detector.dart` | NEW | Find columns via header OCR |
| `table_line_detector.dart` | NEW | Find columns via grid lines |
| `column_detector.dart` | NEW | Unified layered detection |
| `pdf_import_service.dart` | MODIFY | Use column detection |
| `ocr_row_reconstructor.dart` | MODIFY | Accept column boundaries |

## Estimated Time

| PR | Time |
|----|------|
| PR 1: Header detection | 3-4 hours |
| PR 2: Line detection | 4-5 hours |
| PR 3: Unified detector | 2-3 hours |
| PR 4: Integration | 2-3 hours |
| PR 5: Polish | 2-3 hours |
| **Total** | **13-18 hours** |

---

## Key Insight

**The table's vertical grid lines are the ground truth for column boundaries.**

Current code extracts text positions but doesn't know which column each element belongs to. By detecting the actual visual lines OR using header positions, we can definitively assign every OCR element to the correct column before any parsing logic runs.

This transforms the problem from "parse unstructured text" to "read structured cells" - which is much easier and more reliable.
