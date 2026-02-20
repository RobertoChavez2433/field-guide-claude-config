# Plan: M&P Extraction Service

## Context

Pay items are extracted from bid schedule PDFs via the OCR pipeline. The `measurementPayment` field is already wired end-to-end (database column, BidItem model, ParsedBidItem model, BidItemDetailSheet UI, PdfImportPreviewScreen display) but never populated. Users upload a second PDF containing Measurement & Payment descriptions to enrich existing pay items.

**M&P Document Format** (Springfield: 13 pages, 131 items):
```
Item 1.    Mobilization, Bonds, & Insurance (5% Max):  Shall be paid for on a lump sum
           basis for the Contractor's costs to provide required bonds...

Item 2.    Pre-Construction Video Survey:  Shall be paid for on a lump sum basis...
```

Sequential `Item N.` entries with underlined title + paragraph body. Item numbers match bid schedule exactly.

**Existing pipeline is NOT modified in any way.** This is a new, independent service.

## Approach: Native-First with OCR Fallback + Quality Gate

```
M&P PDF
  │
  ├─ Step 1: QUALITY GATE (reuse TextQualityAnalyzer + PdfTextExtractor)
  │    Extract native text per page → run corruption/quality checks
  │    Per-page decision: needsOcr = corruptionScore > 15 || singleCharRatio > 0.30
  │
  ├─ Step 2a: NATIVE PATH (clean pages)
  │    Use PdfTextExtractor text directly — fast, high confidence
  │
  ├─ Step 2b: OCR FALLBACK (corrupt/scanned pages)
  │    Render → Preprocess → Tesseract OCR (reuse stage classes, new instances)
  │
  ├─ Step 3: PARSE "Item N." entries from assembled text
  │
  ├─ Step 4: MATCH to existing bid items by item number
  │
  ├─ Step 5: SCORE confidence per entry
  │
  └─ Preview Screen → User confirms → Update bid_items.measurement_payment
```

### Reused Existing Infrastructure (no modifications)

| Component | Location | How Used |
|-----------|----------|----------|
| `TextQualityAnalyzer` | `extraction/shared/text_quality_analyzer.dart` | Mixin — corruption detection, quality scoring |
| `PageProfile` | `extraction/models/document_profile.dart` | `needsOcr` gate per page |
| `PdfTextExtractor` | `syncfusion_flutter_pdf` | Native text extraction |
| `PageRendererV2` | `extraction/stages/page_renderer_v2.dart` | Render pages for OCR fallback (new instance) |
| `ImagePreprocessorV2` | `extraction/stages/image_preprocessor_v2.dart` | Preprocess for OCR fallback (new instance) |
| `TextRecognizerV2` | `extraction/stages/text_recognizer_v2.dart` | Tesseract OCR for fallback pages (new instance) |
| `TesseractEngineV2` | `extraction/ocr/tesseract_engine_v2.dart` | OCR engine (new instance) |
| `PdfImportProgressManager` | `pdf/presentation/widgets/` | Progress UI during extraction |

## Implementation

### 1. M&P Models

**Create** `lib/features/pdf/services/mp/mp_models.dart`

```dart
/// Extraction strategy chosen per page by the quality gate
enum MpExtractionStrategy { native, ocr }

/// Single parsed M&P entry
class MpEntry {
  final String itemNumber;           // "1", "2", etc.
  final String title;                // Description/title text
  final String body;                 // Full M&P paragraph (title + body combined)
  final int pageIndex;               // Source page
  final MpExtractionStrategy strategy;  // How this page was extracted
  final double confidence;           // Extraction confidence (1.0 for native, OCR-derived for fallback)
}

/// Match result between MpEntry and existing BidItem
class MpMatch {
  final MpEntry entry;
  final String? bidItemId;
  final String? bidItemDescription;
  final double confidence;           // Combined extraction + match confidence
  final bool isMatched;
}

/// Full extraction result
class MpExtractionResult {
  final List<MpMatch> matches;
  final int totalParsed;
  final int totalMatched;
  final int totalUnmatched;
  final int nativePages;             // Pages that used native extraction
  final int ocrPages;                // Pages that fell back to OCR
  final double overallConfidence;
  final Duration elapsed;
  final List<String> warnings;
  final Map<String, dynamic> qualityMetrics;  // Per-page corruption scores, strategy choices
}
```

### 2. M&P Extraction Service

**Create** `lib/features/pdf/services/mp/mp_extraction_service.dart`

```dart
class MpExtractionService with TextQualityAnalyzer {
  // OCR fallback components (only instantiated if needed)
  PageRendererV2? _renderer;
  ImagePreprocessorV2? _preprocessor;
  TextRecognizerV2? _recognizer;
  TesseractEngineV2? _ocrEngine;

  Future<MpExtractionResult> extract(
    Uint8List pdfBytes,
    List<BidItem> existingBidItems, {
    void Function(String stage, double progress)? onProgress,
  }) async {
    // Step 1: Quality Gate — native extraction + corruption check per page
    // Step 2: For clean pages, use native text; for corrupt pages, OCR fallback
    // Step 3: Assemble text, parse Item N. entries
    // Step 4: Match to existing bid items
    // Step 5: Score and return
  }
}
```

**Quality Gate logic** (Step 1):
```dart
final document = PdfDocument(inputBytes: pdfBytes);
final textExtractor = PdfTextExtractor(document);
final pageTexts = <int, String>{};          // pageIndex → text
final pageStrategies = <int, MpExtractionStrategy>{};

for (var i = 0; i < document.pages.count; i++) {
  final nativeText = textExtractor.extractText(startPageIndex: i, endPageIndex: i);
  final profile = analyzePageText(pageIndex: i, extractedText: nativeText, analyzedAt: DateTime.now());

  if (!profile.needsOcr && nativeText.length >= 50) {
    // Native text is clean — use it directly (confidence: 1.0)
    pageTexts[i] = nativeText;
    pageStrategies[i] = MpExtractionStrategy.native;
  } else {
    // Corrupt or empty — fall back to OCR for this page
    final ocrText = await _ocrPage(pdfBytes, i);
    pageTexts[i] = ocrText;
    pageStrategies[i] = MpExtractionStrategy.ocr;
  }
}
```

**Item parsing** (Step 3) — regex on assembled text:
```dart
// Pattern: "Item N." followed by underlined title, colon, then body text
// Body extends until next "Item N." or end of text
final pattern = RegExp(
  r'Item\s+(\d+)\.?\s+(.+?)(?::\s*|\.\s+)(.+?)(?=Item\s+\d+\.|$)',
  multiLine: true,
  dotAll: true,
);
```

**Matching** (Step 4) — simple integer item number lookup:
```dart
final bidItemMap = {for (final item in existingBidItems) item.itemNumber: item};
for (final entry in parsedEntries) {
  final match = bidItemMap[entry.itemNumber];
  // Normalized comparison: strip leading zeros, trim whitespace
}
```

### 3. M&P Import Helper

**Create** `lib/features/pdf/presentation/helpers/mp_import_helper.dart`

Parallel to `PdfImportHelper` (`pdf_import_helper.dart:10-125`):
- File picker for M&P PDF
- Progress UI via `PdfImportProgressManager`
- Invokes `MpExtractionService.extract()`
- Navigates to `MpImportPreviewScreen` with result
- Error handling with snackbar

### 4. M&P Preview Screen

**Create** `lib/features/pdf/presentation/screens/mp_import_preview_screen.dart`

Similar to `PdfImportPreviewScreen` but for enrichment:
- Summary header: "Found N M&P entries, N matched to pay items"
- Quality badge: "Native extraction" (green) or "OCR fallback" (amber) indicator
- Per-page strategy indicator in quality metrics
- List of matched items with confidence bars
- Each row: item number badge, bid item description, M&P text preview (2 lines, expandable)
- Unmatched entries section with warning styling
- Select/deselect individual items
- "Apply to N items" button → calls `BidItemProvider.enrichWithMp()`
- Success snackbar with count

### 5. PayItemSourceDialog — Add Third Option

**Modify** `lib/features/projects/presentation/widgets/pay_item_source_dialog.dart`

- Add `bool hasBidItems` parameter (default false)
- Third option: icon `Icons.description`, title "Enrich with M&P", description "Add measurement & payment descriptions from PDF"
- Only shown when `hasBidItems == true`
- Returns `'mp'` when tapped

### 6. Project Setup Screen — Handle M&P

**Modify** `lib/features/projects/presentation/screens/project_setup_screen.dart`

- Pass `hasBidItems: bidItems.isNotEmpty` to `PayItemSourceDialog.show()`
- Handle `'mp'` result → invoke `MpImportHelper.importMp()`

### 7. Router — Add Route

**Modify** `lib/core/router/app_router.dart`

- Add `mp-import-preview` route under project scope
- Extra: `MpExtractionResult`

### 8. BidItemProvider — Enrichment Method

**Modify** `lib/features/quantities/presentation/providers/bid_item_provider.dart`

```dart
Future<int> enrichWithMeasurementPayment(List<MpMatch> matches) async {
  int updated = 0;
  for (final match in matches.where((m) => m.isMatched)) {
    final existing = _items.firstWhereOrNull((i) => i.id == match.bidItemId);
    if (existing != null) {
      final enriched = existing.copyWith(measurementPayment: match.entry.body);
      await _repository.save(enriched);
      updated++;
    }
  }
  if (_currentProjectId != null) await loadByProject(_currentProjectId!);
  return updated;
}
```

### 9. Testing Keys

**Modify** `lib/shared/testing_keys/quantities_keys.dart`

- `payItemSourceMp`, `mpPreviewScreen`, `mpPreviewApplyButton`, `mpPreviewSelectAll`

## Files Summary

| File | Action |
|------|--------|
| `lib/features/pdf/services/mp/mp_models.dart` | Create |
| `lib/features/pdf/services/mp/mp_extraction_service.dart` | Create |
| `lib/features/pdf/presentation/helpers/mp_import_helper.dart` | Create |
| `lib/features/pdf/presentation/screens/mp_import_preview_screen.dart` | Create |
| `lib/features/projects/presentation/widgets/pay_item_source_dialog.dart` | Modify |
| `lib/features/projects/presentation/screens/project_setup_screen.dart` | Modify |
| `lib/core/router/app_router.dart` | Modify |
| `lib/features/quantities/presentation/providers/bid_item_provider.dart` | Modify |
| `lib/shared/testing_keys/quantities_keys.dart` | Modify |

## Test Plan

### Unit Tests

**Create** `test/features/pdf/services/mp/mp_extraction_service_test.dart`

| Test | Validates |
|------|-----------|
| Quality gate: clean native text → strategy=native | `TextQualityAnalyzer` integration, corruption < 15 |
| Quality gate: corrupted text → strategy=ocr | CMap corruption detection triggers OCR fallback |
| Quality gate: empty pages → strategy=ocr | Empty native text triggers OCR fallback |
| Quality gate: scanned PDF (no embedded text) → strategy=ocr | Photo/scan detection |
| Item parser: Springfield-format items | Regex parses "Item N. Title: Body" correctly |
| Item parser: multi-paragraph items (bullet points) | Items 1, 3 with bullet sub-items |
| Item parser: items spanning page boundaries | Item body continues on next page |
| Item parser: preamble skipped | Sections 1.01, 1.02 before items are ignored |
| Item parser: varying whitespace/formatting | Tabs, extra spaces, line breaks handled |
| Item matcher: exact match by integer | "1" matches "1", "01" matches "1" |
| Item matcher: partial set (fewer M&P than bid items) | Unmatched bid items reported |
| Item matcher: extra M&P items (not in bid schedule) | Unmatched M&P entries warned |
| Confidence: native extraction → 1.0 base | Clean native text gets high confidence |
| Confidence: OCR extraction → derived from Tesseract | OCR pages get Tesseract-based confidence |
| End-to-end: full extraction with mock PDF bytes | All steps produce valid MpExtractionResult |

**Create** `test/features/pdf/services/mp/mp_item_parser_test.dart`

Focused regex/parsing tests with hardcoded M&P text samples (no PDF/OCR dependency):

| Test | Input | Expected |
|------|-------|----------|
| Single item | `"Item 1. Title: Body text"` | 1 entry, itemNumber="1" |
| Multiple items | `"Item 1. T1: B1\nItem 2. T2: B2"` | 2 entries |
| Multi-line body | `"Item 3. Title:\n  Line1\n  - Bullet\n  Line2\nItem 4..."` | body includes all lines |
| Item with period after number | `"Item 10. Title: Body"` | itemNumber="10" |
| Item without period | `"Item 10 Title: Body"` | itemNumber="10" |
| Large item numbers | `"Item 131. Title: Body"` | itemNumber="131" |
| Preamble before items | `"SECTION 01 22 00\n1.01 SUMMARY...\nItem 1. ..."` | Skips preamble |

**Create** `test/features/pdf/services/mp/mp_quality_gate_test.dart`

Quality gate tests using `TextQualityAnalyzer` mixin directly:

| Test | Input | Expected |
|------|-------|----------|
| Clean English text | Normal spec text | corruptionScore < 15, strategy=native |
| CMap corrupted text | Mixed-case "sEcTroN", missing $ | corruptionScore > 15, strategy=ocr |
| High single-char ratio | "a b c d e f g h" | singleCharRatio > 0.30, strategy=ocr |
| Empty page | "" | charCount=0, strategy=ocr |
| Currency corruption | Amounts with 's' instead of '$' | currencyCorruption detected |

**Create** `test/features/pdf/services/mp/mp_item_matcher_test.dart`

| Test | Scenario | Expected |
|------|----------|----------|
| All items match | 131 M&P entries, 131 bid items | 131 matched, 0 unmatched |
| Partial match | 50 M&P entries, 131 bid items | 50 matched, 81 bid items without M&P |
| Extra M&P items | 135 M&P entries, 131 bid items | 131 matched, 4 unmatched M&P |
| No matches | M&P numbers don't align | 0 matched, warning emitted |
| Leading zeros | M&P "01" ↔ bid item "1" | Matched via normalization |

### Integration Test

**Create** `integration_test/mp_extraction_integration_test.dart`

- Load Springfield M&P PDF via `--dart-define=SPRINGFIELD_MP_PDF=...`
- Load Springfield bid items from ground truth fixture
- Run `MpExtractionService.extract()` end-to-end
- Assert: 131/131 items parsed
- Assert: 131/131 items matched
- Assert: quality gate chose `native` for all pages (Springfield M&P is clean text)
- Spot-check M&P body text for Items 1, 25, 50, 100, 131
- Assert: overall confidence > 0.95

### Widget Tests

**Create** `test/features/pdf/presentation/screens/mp_import_preview_screen_test.dart`

| Test | Validates |
|------|-----------|
| Renders matched items with confidence bars | UI displays all matched entries |
| Shows unmatched section when entries exist | Warning section appears |
| Select/deselect individual items | Checkbox toggles work |
| Apply button calls enrichWithMp | Provider method invoked correctly |
| Empty result shows appropriate message | Edge case UI |

**Create** `test/features/projects/presentation/widgets/pay_item_source_dialog_test.dart`

| Test | Validates |
|------|-----------|
| Shows 2 options when hasBidItems=false | M&P option hidden |
| Shows 3 options when hasBidItems=true | M&P option visible |
| M&P option returns 'mp' | Correct dialog result |

## Verification Checklist

- [ ] Quality gate correctly identifies clean vs corrupted pages
- [ ] Native extraction produces same text as OCR for clean Springfield M&P PDF
- [ ] All 131 Springfield items parsed and matched
- [ ] M&P text displays in BidItemDetailSheet after enrichment
- [ ] "Enrich with M&P" hidden when no bid items exist
- [ ] OCR fallback activates on corrupted/scanned PDFs
- [ ] Re-importing M&P overwrites existing text
- [ ] All unit tests pass
- [ ] `flutter analyze` clean
