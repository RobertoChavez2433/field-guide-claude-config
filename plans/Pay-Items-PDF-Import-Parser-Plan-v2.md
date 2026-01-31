# Implementation Plan: Smart Pay Item PDF Import Parser v2

**Last Updated**: 2026-01-31
**Status**: READY FOR IMPLEMENTATION
**Reviewer**: Senior Code Review

---

## Problem Statement

Current PDF import fails on column-based PDFs (like the CTC pay items sample) because:
1. `PdfTextExtractor.extractText()` returns plain text with no positional data
2. Regex patterns expect all columns on a single line
3. Wrapped descriptions break the line-by-line parsing

**Solution**: Use `extractTextLines()` API (already validated in `tooling/pdf_textline_spike.dart`) to detect columns by X-position clustering and handle wrapped text by Y-position grouping.

---

## Code Review Findings

### Gaps in Original Plan

| Gap | Finding | Resolution |
|-----|---------|------------|
| Phase 0 redundant | `tooling/pdf_textline_spike.dart` already proves API works | Skip Phase 0 |
| No batch import | `BidItemRepository.insertAll()` exists at line 163 but not exposed in provider | Add `importBatch()` to provider |
| Quantities reload missing | Uses `pushNamed()` without await, no reload | Change to `await pushNamed<bool>()` and reload |
| Confidence field | Plan mentions but BidItem has no field | Create `ParsedBidItem` wrapper class |
| Warnings unused | `PdfImportResult.warnings` exists but never populated | Populate during parsing |
| Measurement specs unclear | Original says "enrich existing" but code creates new items | Fix: Match by item number and update measurementPayment on existing items |

### Existing Infrastructure (No Changes Needed)

- `PdfImportResult` with `warnings` field
- `BidItemRepository.insertAll()` for batch insert
- `BidItemProvider.getBidItemByNumber()` for duplicate detection
- Preview screen with full edit/delete/select capabilities
- Route `'import-preview'` properly configured

---

## Phase 1: Data Structures

### 1.1 Create ParsedBidItem Model

**File**: `lib/features/pdf/data/models/parsed_bid_item.dart` (NEW)

```dart
class ParsedBidItem {
  final String itemNumber;
  final String description;
  final String unit;
  final double bidQuantity;
  final double? unitPrice;
  final double confidence;  // 0.0-1.0
  final List<String> warnings;

  bool get needsReview => confidence < 0.8 || warnings.isNotEmpty;

  BidItem toBidItem(String projectId) => BidItem(...);
  factory ParsedBidItem.fromBidItem(BidItem b, {double confidence = 1.0});
}
```

### 1.2 Update PdfImportResult

**File**: `lib/features/pdf/services/pdf_import_service.dart` (MODIFY lines 14-24)

Add:
```dart
enum ParserType { columnLayout, regexFallback }

class PdfImportResult {
  final List<ParsedBidItem> parsedItems;  // NEW
  final List<BidItem> bidItems;           // Keep for backwards compat
  final Map<String, dynamic> metadata;
  final List<String> warnings;
  final ParserType parserUsed;            // NEW

  int get lowConfidenceCount => parsedItems.where((p) => p.needsReview).length;
}
```

---

## Phase 2: Column-Aware Parser

### 2.1 Create ColumnLayoutParser

**File**: `lib/features/pdf/services/parsers/column_layout_parser.dart` (NEW)

Core algorithm:
1. Extract all text lines with `extractTextLines()`
2. Collect word X-positions, cluster by gaps > threshold
3. Identify header row by keywords (Item, Description, Unit, Qty, Price)
4. Map clusters to column semantics based on header positions
5. Group lines by Y-position into logical rows
6. Detect wrapped descriptions: lines in description column without item number
7. Calculate confidence based on parsing success

**Key Classes**:
```dart
class ColumnLayoutParser {
  Future<List<ParsedBidItem>> parse(PdfDocument document);
}

class ColumnLayout {
  final double itemNumberStart, itemNumberEnd;
  final double descriptionStart, descriptionEnd;
  final double unitStart, unitEnd;
  final double quantityStart, quantityEnd;
  final double unitPriceStart, unitPriceEnd;
}
```

### 2.2 Confidence Scoring

| Criterion | Score |
|-----------|-------|
| Item number matches pattern `\d+(\.\d+)?` | +0.3 |
| Unit in known list (EA, FT, CY, SY, TON, etc.) | +0.2 |
| Quantity parses as valid number | +0.2 |
| Unit price parses (if present) | +0.2 |
| Description length 5-200 chars | +0.1 |

---

## Phase 3: Integrate Parser with Fallback

**File**: `lib/features/pdf/services/pdf_import_service.dart` (MODIFY)

```dart
Future<PdfImportResult> importBidSchedule(...) async {
  // Try column parser first
  try {
    final parsedItems = await _columnParser.parse(document);
    if (parsedItems.isNotEmpty) {
      return PdfImportResult(
        parsedItems: parsedItems,
        bidItems: parsedItems.map((p) => p.toBidItem(projectId)).toList(),
        parserUsed: ParserType.columnLayout,
        warnings: _collectWarnings(parsedItems),
      );
    }
  } catch (e) {
    debugPrint('[PDF Import] Column parser failed, using regex fallback');
  }

  // Fallback to existing regex parser
  final bidItems = _parseBidSchedule(_extractAllText(document), projectId);
  return PdfImportResult(
    parsedItems: bidItems.map((b) => ParsedBidItem.fromBidItem(b)).toList(),
    bidItems: bidItems,
    parserUsed: ParserType.regexFallback,
    warnings: bidItems.isEmpty ? ['No items found. PDF may be scanned.'] : [],
  );
}
```

---

## Phase 4: Batch Import & Duplicates

### 4.1 Add importBatch to BidItemProvider

**File**: `lib/features/quantities/presentation/providers/bid_item_provider.dart` (MODIFY)

Add after line 117:
```dart
enum DuplicateStrategy { skip, replace, error }

class ImportBatchResult {
  final int importedCount;
  final int duplicateCount;
  final List<String> errors;
}

Future<ImportBatchResult> importBatch(
  List<BidItem> items, {
  DuplicateStrategy strategy = DuplicateStrategy.skip,
}) async {
  final toInsert = <BidItem>[];
  final duplicates = <BidItem>[];

  for (final item in items) {
    final existing = getBidItemByNumber(item.itemNumber);
    if (existing != null) {
      if (strategy == DuplicateStrategy.skip) {
        duplicates.add(item);
      } else if (strategy == DuplicateStrategy.replace) {
        await repository.update(existing.copyWith(...));
      }
    } else {
      toInsert.add(item);
    }
  }

  if (toInsert.isNotEmpty) {
    await repository.insertAll(toInsert);  // Uses existing method at line 163
    _items.addAll(toInsert);
    sortItems();
  }

  return ImportBatchResult(...);
}
```

### 4.2 Update Preview Screen Import

**File**: `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart` (MODIFY lines 228-263)

Change from loop to batch:
```dart
final result = await provider.importBatch(selectedItems);

String message = 'Imported ${result.importedCount} items';
if (result.duplicateCount > 0) {
  message += ' (${result.duplicateCount} duplicates skipped)';
}
```

---

## Phase 5: Fix Quantities Screen Reload

**File**: `lib/features/quantities/presentation/screens/quantities_screen.dart` (MODIFY lines 384-389)

Change:
```dart
// BEFORE
context.pushNamed('import-preview', ...);

// AFTER
final imported = await context.pushNamed<bool>('import-preview', ...);
if (imported == true && mounted) {
  await context.read<BidItemProvider>().loadBidItems(project.id);
}
```

---

## Phase 6: Preview Screen Enhancements

**File**: `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart` (MODIFY)

### 6.1 Warning Banner (after line 98)

```dart
if (widget.importResult.warnings.isNotEmpty)
  Container(
    color: AppTheme.warning.withOpacity(0.15),
    padding: EdgeInsets.all(12),
    child: Column(
      children: widget.importResult.warnings.map((w) => Text('• $w')).toList(),
    ),
  ),
```

### 6.2 Confidence Indicator in Card (line 295+)

```dart
if (item.confidence < 1.0)
  Row(
    children: [
      LinearProgressIndicator(value: item.confidence, ...),
      Text('${(item.confidence * 100).toInt()}%'),
    ],
  ),
```

### 6.3 Low-Confidence Highlight

```dart
Card(
  color: item.needsReview ? AppTheme.warning.withOpacity(0.1) : null,
  ...
)
```

---

## Phase 7: Addendum & Duplicate Item Number Handling

### 7.1 Detect Addendum Boundaries

In `ColumnLayoutParser`, track addendum sections:
```dart
final addendumPattern = RegExp(r'ADDENDUM\s*[A-Z#]?\s*(\d+)?', caseSensitive: false);
String? currentAddendum;

// When addendum detected, prefix item numbers: "A1-203.03"
```

### 7.2 Suffix Duplicate Item Numbers

```dart
// In parser, after all items collected:
final seen = <String, int>{};
for (final item in parsedItems) {
  final count = seen[item.itemNumber] ?? 0;
  if (count > 0) {
    item.itemNumber = '${item.itemNumber}${String.fromCharCode(96 + count)}'; // 1a, 1b, etc
    item.warnings.add('Duplicate item number - suffixed');
  }
  seen[item.itemNumber] = count + 1;
}
```

---

## Phase 8: Measurement Specs Enrichment

**Objective**: Import measurement specs PDF and update the `measurementPayment` field on EXISTING bid items (matched by item number).

### 8.1 Update importMeasurementSpecs

**File**: `lib/features/pdf/services/pdf_import_service.dart` (MODIFY `_parseMeasurementSpecs`)

Current behavior (WRONG): Creates new BidItems with quantity=0
New behavior: Return parsed specs that will be matched to existing items

```dart
/// Result for measurement specs import (different from bid schedule)
class MeasurementSpecResult {
  final List<ParsedMeasurementSpec> specs;
  final List<String> warnings;
}

class ParsedMeasurementSpec {
  final String itemNumber;
  final String measurementPaymentText;
  final String? descriptionIfMissing;  // Optional: fill if existing item has no description
}
```

### 8.2 Add enrichExistingItems to BidItemProvider

**File**: `lib/features/quantities/presentation/providers/bid_item_provider.dart` (MODIFY)

```dart
/// Enrich existing bid items with measurement/payment specs
/// Returns count of items updated and list of unmatched specs
Future<EnrichResult> enrichWithMeasurementSpecs(
  List<ParsedMeasurementSpec> specs,
) async {
  int updatedCount = 0;
  final unmatched = <String>[];

  for (final spec in specs) {
    final existing = getBidItemByNumber(spec.itemNumber);
    if (existing != null) {
      final updated = existing.copyWith(
        measurementPayment: spec.measurementPaymentText,
      );
      await repository.update(updated);
      _updateItemInList(updated);
      updatedCount++;
    } else {
      unmatched.add(spec.itemNumber);
    }
  }

  notifyListeners();
  return EnrichResult(
    updatedCount: updatedCount,
    unmatchedItemNumbers: unmatched,
  );
}

class EnrichResult {
  final int updatedCount;
  final List<String> unmatchedItemNumbers;
}
```

### 8.3 Update Preview/Import Flow for Measurement Specs

When `PdfImportType.measurementSpecs` is selected:
1. Parse specs from PDF (item numbers + measurement text)
2. Show preview with matched/unmatched status
3. On import: call `enrichWithMeasurementSpecs()` instead of `importBatch()`
4. Show result: "Updated 15 items. 3 specs had no matching bid items."

**Preview Screen Changes**:
- For measurement specs, show which items will be updated vs which have no match
- Different UI: "Update Existing Items" button instead of "Import Items"

---

## File Summary

### New Files
```
lib/features/pdf/data/models/parsed_bid_item.dart
lib/features/pdf/data/models/parsed_measurement_spec.dart (NEW)
lib/features/pdf/services/parsers/column_layout_parser.dart
lib/features/pdf/services/parsers/parsers.dart (barrel)
```

### Modified Files
```
lib/features/pdf/services/pdf_import_service.dart
lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart
lib/features/quantities/presentation/providers/bid_item_provider.dart
lib/features/quantities/presentation/screens/quantities_screen.dart
```

---

## Implementation Order

| Phase | Description | Est. LOC |
|-------|-------------|----------|
| 1 | ParsedBidItem model + PdfImportResult update | ~80 |
| 2 | ColumnLayoutParser | ~300 |
| 3 | Integrate parser with fallback | ~60 |
| 4 | Batch import + duplicate handling | ~100 |
| 5 | Fix quantities reload (3 lines) | ~5 |
| 6 | Preview UI enhancements | ~80 |
| 7 | Addendum + duplicate suffixing | ~50 |
| 8 | Measurement specs enrichment | ~120 |
| **Total** | | **~795** |

---

## Verification

### Per-Phase Checks
1. **Phase 1**: `flutter analyze` passes, model has all required methods
2. **Phase 2**: Run spike against sample CTC PDF, verify items extracted
3. **Phase 3**: Break column parser intentionally, verify regex fallback works
4. **Phase 4**: Import same PDF twice, verify duplicates skipped/counted
5. **Phase 5**: Import items from quantities screen, verify list updates
6. **Phase 6**: Import PDF with low-confidence items, verify visual indicators
7. **Phase 7**: Import PDF with addendum, verify prefixing works
8. **Phase 8**: Import bid schedule first, then import M&P specs, verify measurementPayment updated on existing items

### End-to-End Test: Bid Schedule Import
1. Build Windows app: `pwsh -Command "flutter build windows"`
2. Create new project
3. Navigate to Pay Items tab
4. Import sample CTC PDF (Bid Schedule type)
5. Verify all items parsed with correct descriptions (including wrapped)
6. Check for low-confidence indicators on uncertain items
7. Import selected items
8. Verify list updates immediately
9. Import same PDF again - verify "X duplicates skipped" message

### End-to-End Test: Measurement Specs Enrichment
1. With existing project that has bid items imported
2. Click Import, select "Measurement Specs" type
3. Select M&P PDF file
4. Preview shows which specs match existing items
5. Click "Update Existing Items"
6. Verify measurementPayment field updated on matched items
7. Check a bid item detail - should show M&P text

### Regression Check
- Import a simple single-line format PDF (should use regex fallback)
- Verify existing import functionality unchanged

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Column detection fails | Regex fallback always available |
| Wrapped text grouped wrong | Conservative Y-threshold; user can edit in preview |
| Large PDF slow | Process page-by-page; existing spike shows good perf |
| Batch insert partial failure | Repository.insertAll uses transaction |

---

## Out of Scope

- OCR for scanned PDFs (show warning instead)
- Performance optimization with isolates (defer unless needed)
