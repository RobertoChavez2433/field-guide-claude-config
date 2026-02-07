# Per-Page Text Quality Gate Design

**Status**: Research & Design Phase (DO NOT IMPLEMENT YET)
**Author**: PDF Agent
**Date**: 2026-02-06
**Context**: Fix encoding corruption on mixed-quality PDF pages (e.g., Springfield page 6)

---

## Problem Statement

### Current Behavior (All-or-Nothing)
The native text extraction pipeline uses a **document-level** viability check (`needsOcr()`) that looks at aggregate statistics across all pages:
- If `charsPerPage >= 50` AND `singleCharRatio <= 30%` → Use native text for ALL pages
- Otherwise → OCR ALL pages

### The Bug
On Springfield PDF page 6, the font encoding is corrupted, producing:
- `7` → `z`
- `3` → `e`
- `9` ↔ `6` (swapped)
- `,` → `'`
- `.` → `'`

Example: `$7,882,926.73` becomes `$z'882'629'ze`

The document-level check passes (most pages have good text), so ALL pages use native text, including the corrupted page 6. We need **per-page routing** to OCR only the bad pages.

---

## Current Architecture

### Pipeline Flow (pdf_import_service.dart:673-830)

```
1. Load PDF document
2. extractRawText(document) → concatenate all pages into single string
3. needsOcr(rawText, pageCount) → document-level decision
   ├─ If FALSE (native text viable):
   │  └─ NativeTextExtractor.extractFromDocument(document)
   │     └─ Returns List<List<OcrElement>> (one list per page)
   │        └─ Pass to TableExtractor.extract()
   │
   └─ If TRUE (OCR needed):
      └─ _runOcrPipeline(document)
         └─ Returns elementsPerPage: List<List<OcrElement>>
            └─ Pass to TableExtractor.extract()
```

### Key Components

**NativeTextExtractor** (`native_text_extractor.dart:44-115`)
- Input: `PdfDocument`, `renderDpi`
- Process: For each page, extract `TextWord` objects via Syncfusion API
- Output: `List<List<OcrElement>>` (one list per page)
- Post-processing: `_fixReversedText()` per page (lines 117-208)

**needsOcr()** (`pdf_import_service.dart:274-305`)
- Input: `String extractedText`, `int pageCount`
- Checks:
  1. Empty text → OCR
  2. `charsPerPage < 50` → OCR
  3. `singleCharRatio > 0.30` → OCR
- Output: `bool` (true = needs OCR)

**TableExtractor** (`table_extractor.dart:112-120`)
- Input: `List<List<OcrElement>> ocrElementsPerPage`, `List<Uint8List> pageImages`
- Process: Column detection, cell extraction, row parsing
- Output: `List<ParsedBidItem>`
- **Key insight**: Already designed to handle per-page element lists

---

## Design: Per-Page Quality Scoring

### Phase 1: Heuristics for Encoding Corruption Detection

#### Signal 1: Digit-to-Letter Substitution Ratio
**Hypothesis**: Corrupted fonts substitute digits with letters in predictable patterns.

```dart
/// Count how many "words" contain digit-like letters in digit-expected contexts.
/// Example: "$z'882'629'ze" has 'z' where dollar amounts expect digits.
double _digitLetterSubstitutionScore(String text) {
  // Pattern: dollar amounts with letters mixed in
  // $z'882 → 'z' is suspicious
  // $7,882 → normal

  final dollarAmountPattern = RegExp(r'\$[\d\w,.\'\s]+');
  final matches = dollarAmountPattern.allMatches(text);

  if (matches.isEmpty) return 0.0;

  int suspiciousMatches = 0;
  for (final match in matches) {
    final amount = text.substring(match.start, match.end);

    // Check for letters in positions where digits are expected
    // After $, between commas, before decimals
    if (amount.contains(RegExp(r'\$[a-zA-Z]'))) suspiciousMatches++;
    if (amount.contains(RegExp(r'[a-zA-Z]\d|\d[a-zA-Z]'))) suspiciousMatches++;
  }

  return suspiciousMatches / matches.length;
}
```

**Threshold**: `> 0.3` (30% of dollar amounts have letter substitutions) → Corruption likely

#### Signal 2: Punctuation Substitution Rate
**Hypothesis**: Corrupted fonts substitute punctuation (`,` → `'`, `.` → `'`).

```dart
/// Detect abnormal quote-to-digit ratios in numeric contexts.
double _punctuationSubstitutionScore(String text) {
  // Normal: "Item 123, Section 4.5" → commas and periods
  // Corrupted: "Item 623' Section 5'4" → quotes instead

  final numericContextPattern = RegExp(r'\d[\'\,\.]\d');
  final matches = numericContextPattern.allMatches(text);

  if (matches.isEmpty) return 0.0;

  int quoteCount = 0;
  int normalPunctCount = 0;

  for (final match in matches) {
    final segment = text.substring(match.start, match.end);
    if (segment.contains("'")) quoteCount++;
    if (segment.contains(",") || segment.contains(".")) normalPunctCount++;
  }

  // If quotes outnumber normal punctuation, likely corruption
  final total = quoteCount + normalPunctCount;
  return total > 0 ? quoteCount / total : 0.0;
}
```

**Threshold**: `> 0.5` (50% of numeric separators are quotes) → Corruption likely

#### Signal 3: Digit Swap Detection (9 ↔ 6)
**Hypothesis**: Specific digit swaps occur consistently.

```dart
/// Detect if swapping 9↔6 improves structural coherence.
/// This is EXPERIMENTAL and may have false positives.
double _digitSwapScore(String text) {
  // Check if swapping 9↔6 makes numbers more "normal"
  // E.g., if page has "629" but should be "926", we might detect
  // unusually high 6-frequency in positions where 9 is expected.

  // Count digit frequencies
  final digitCounts = <int, int>{};
  for (final char in text.codeUnits) {
    if (char >= 48 && char <= 57) { // '0'-'9'
      digitCounts[char] = (digitCounts[char] ?? 0) + 1;
    }
  }

  final count6 = digitCounts[54] ?? 0; // '6'
  final count9 = digitCounts[57] ?? 0; // '9'

  // If 6 appears 3x more often than 9, suspicious
  // (Bid schedules typically have balanced digit distribution)
  if (count9 == 0) return 0.0;
  final ratio = count6 / count9;

  return ratio > 3.0 ? 0.5 : 0.0; // Binary signal
}
```

**Threshold**: `> 0.4` → Corruption likely
**Risk**: False positives on legitimate data with 6-heavy item numbers

#### Signal 4: Header Keyword Garbling
**Hypothesis**: If standard bid table headers are garbled, entire page is corrupted.

```dart
/// Check if standard headers are present and readable.
double _headerGarblingScore(List<OcrElement> pageElements) {
  final standardHeaders = {
    'ITEM', 'DESCRIPTION', 'UNIT', 'QUANTITY', 'PRICE', 'AMOUNT'
  };

  final pageTextUpper = pageElements.map((e) => e.text.toUpperCase()).join(' ');

  int foundHeaders = 0;
  int garbedHeaders = 0;

  for (final header in standardHeaders) {
    if (pageTextUpper.contains(header)) {
      foundHeaders++;
    } else {
      // Check if a garbled version exists (e.g., "PRIC3" instead of "PRICE")
      final fuzzyMatch = RegExp(header.split('').map((c) => '[$c\\d]').join());
      if (fuzzyMatch.hasMatch(pageTextUpper)) {
        garbedHeaders++;
      }
    }
  }

  if (foundHeaders + garbedHeaders == 0) return 0.0; // Not a table page

  return garbedHeaders / (foundHeaders + garbedHeaders);
}
```

**Threshold**: `> 0.3` (30% of headers garbled) → Corruption likely

---

### Phase 2: Composite Quality Score

Combine signals into a single per-page quality score:

```dart
class PageQualityMetrics {
  final double digitLetterSubstitution;
  final double punctuationSubstitution;
  final double digitSwap;
  final double headerGarbling;
  final double compositeScore;

  PageQualityMetrics({
    required this.digitLetterSubstitution,
    required this.punctuationSubstitution,
    required this.digitSwap,
    required this.headerGarbling,
  }) : compositeScore = _calculateComposite(
         digitLetterSubstitution,
         punctuationSubstitution,
         digitSwap,
         headerGarbling,
       );

  static double _calculateComposite(
    double digitLetter,
    double punctuation,
    double digitSwap,
    double headerGarbling,
  ) {
    // Weighted average (tune weights empirically)
    const weights = {
      'digitLetter': 0.35,      // Most reliable
      'punctuation': 0.30,      // Strong signal
      'headerGarbling': 0.25,   // Context-dependent
      'digitSwap': 0.10,        // Experimental
    };

    return (digitLetter * weights['digitLetter']!) +
           (punctuation * weights['punctuation']!) +
           (headerGarbling * weights['headerGarbling']!) +
           (digitSwap * weights['digitSwap']!);
  }

  /// True if page quality is too low for native text.
  bool get needsOcr => compositeScore > 0.35;
}
```

**Quality Score Interpretation**:
- `0.0 - 0.20`: Clean native text (high confidence)
- `0.20 - 0.35`: Borderline (use native text, log warning)
- `0.35 - 1.00`: Corrupted (trigger OCR fallback)

---

## Design: Per-Page Routing Mechanism

### Architecture Changes

#### New Method: `_assessPageQuality()`

```dart
/// Assess quality of native text extraction for a single page.
///
/// Returns PageQualityMetrics with composite score and individual signal scores.
PageQualityMetrics _assessPageQuality(
  List<OcrElement> pageElements,
  int pageIndex,
) {
  // Concatenate page text for string-based heuristics
  final pageText = pageElements.map((e) => e.text).join(' ');

  final digitLetterScore = _digitLetterSubstitutionScore(pageText);
  final punctuationScore = _punctuationSubstitutionScore(pageText);
  final digitSwapScore = _digitSwapScore(pageText);
  final headerGarblingScore = _headerGarblingScore(pageElements);

  return PageQualityMetrics(
    digitLetterSubstitution: digitLetterScore,
    punctuationSubstitution: punctuationScore,
    digitSwap: digitSwapScore,
    headerGarbling: headerGarblingScore,
  );
}
```

#### Modified Method: `importBidSchedule()` (lines 673-830)

**Current flow** (simplified):
```dart
final rawText = extractRawText(document);
final ocrNeeded = needsOcr(rawText, pageCount);

if (!ocrNeeded) {
  // Use native text for ALL pages
  final nativeElementsPerPage = _nativeTextExtractor.extractFromDocument(document);
  // ... pass to TableExtractor
} else {
  // OCR ALL pages
  final ocrResult = await _runOcrPipeline(document);
  // ... pass to TableExtractor
}
```

**NEW flow** (per-page routing):
```dart
final rawText = extractRawText(document);
final ocrNeeded = needsOcr(rawText, pageCount);

List<List<OcrElement>> finalElementsPerPage;
List<Uint8List> finalPageImages;
bool usedMixedMode = false;

if (!ocrNeeded) {
  // STEP 1: Extract native text from ALL pages
  final nativeElementsPerPage = _nativeTextExtractor.extractFromDocument(document);

  // STEP 2: Assess quality per page
  final pageQualities = <PageQualityMetrics>[];
  final pagesNeedingOcr = <int>[];

  for (int i = 0; i < nativeElementsPerPage.length; i++) {
    final quality = _assessPageQuality(nativeElementsPerPage[i], i);
    pageQualities.add(quality);

    if (quality.needsOcr) {
      pagesNeedingOcr.add(i);
      DebugLogger.pdf('Page ${i + 1} quality LOW (${(quality.compositeScore * 100).toStringAsFixed(1)}%) - will OCR', data: {
        'digitLetterSub': quality.digitLetterSubstitution,
        'punctuationSub': quality.punctuationSubstitution,
        'digitSwap': quality.digitSwap,
        'headerGarbling': quality.headerGarbling,
      });
    }
  }

  // STEP 3: If some pages need OCR, use mixed mode
  if (pagesNeedingOcr.isNotEmpty) {
    usedMixedMode = true;
    finalElementsPerPage = await _buildMixedElementsPerPage(
      document: document,
      nativeElementsPerPage: nativeElementsPerPage,
      pagesNeedingOcr: pagesNeedingOcr,
      pageQualities: pageQualities,
    );

    // Mixed mode needs page images for the OCR'd pages
    finalPageImages = await _generateSelectivePageImages(document, pagesNeedingOcr);
  } else {
    // All pages passed quality check - use native text
    finalElementsPerPage = nativeElementsPerPage;
    finalPageImages = List.generate(pageCount, (_) => Uint8List(0)); // Empty for native-only
  }

  // ... pass finalElementsPerPage to TableExtractor
} else {
  // Document-level check failed - OCR ALL pages (existing path)
  final ocrResult = await _runOcrPipeline(document);
  finalElementsPerPage = ocrResult.elementsPerPage;
  finalPageImages = ocrResult.pageImages;
}
```

#### New Method: `_buildMixedElementsPerPage()`

```dart
/// Build merged element list: native text for good pages, OCR for bad pages.
Future<List<List<OcrElement>>> _buildMixedElementsPerPage({
  required PdfDocument document,
  required List<List<OcrElement>> nativeElementsPerPage,
  required List<int> pagesNeedingOcr,
  required List<PageQualityMetrics> pageQualities,
}) async {
  final result = <List<OcrElement>>[];
  final ocrEngine = OcrEngineFactory.create(usePool: true);
  final renderer = PdfPageRenderer();

  DebugLogger.pdf('Building mixed-mode elements', data: {
    'totalPages': nativeElementsPerPage.length,
    'pagesNeedingOcr': pagesNeedingOcr.length,
    'ocrPageList': pagesNeedingOcr.join(', '),
  });

  for (int i = 0; i < nativeElementsPerPage.length; i++) {
    if (pagesNeedingOcr.contains(i)) {
      // OCR this page
      DebugLogger.pdf('OCR page ${i + 1} (quality: ${(pageQualities[i].compositeScore * 100).toStringAsFixed(1)}%)');

      final pageImage = await renderer.renderPageToPng(
        document,
        pageIndex: i,
        dpi: 300, // Match native text rendering DPI
      );

      final ocrResult = await ocrEngine.recognizeText(
        imageBytes: pageImage,
        mode: OcrMode.structured,
      );

      result.add(ocrResult.elements);
    } else {
      // Use native text
      result.add(nativeElementsPerPage[i]);
    }
  }

  return result;
}
```

#### New Method: `_generateSelectivePageImages()`

```dart
/// Generate page images ONLY for pages that will be OCR'd.
/// Used in mixed mode to provide line detection images.
Future<List<Uint8List>> _generateSelectivePageImages(
  PdfDocument document,
  List<int> pagesNeedingOcr,
) async {
  final renderer = PdfPageRenderer();
  final pageImages = <Uint8List>[];

  for (int i = 0; i < document.pages.count; i++) {
    if (pagesNeedingOcr.contains(i)) {
      // Render this page (for line detection in TableExtractor)
      final image = await renderer.renderPageToPng(document, pageIndex: i, dpi: 300);
      pageImages.add(image);
    } else {
      // Native text page - no image needed
      pageImages.add(Uint8List(0));
    }
  }

  return pageImages;
}
```

---

## Integration Points

### 1. NativeTextExtractor (native_text_extractor.dart)
**No changes needed.** Already returns `List<List<OcrElement>>` per page.

### 2. PdfImportService (pdf_import_service.dart)
**Changes**:
- Add `_assessPageQuality()` method
- Add `_digitLetterSubstitutionScore()`, `_punctuationSubstitutionScore()`, `_digitSwapScore()`, `_headerGarblingScore()` helper methods
- Add `PageQualityMetrics` class
- Add `_buildMixedElementsPerPage()` method
- Add `_generateSelectivePageImages()` method
- Modify `importBidSchedule()` to implement per-page routing (lines 716-829)

### 3. TableExtractor (table_extractor.dart)
**No changes needed.** Already accepts `List<List<OcrElement>> ocrElementsPerPage` and `List<Uint8List> pageImages`. Mixed mode will pass:
- `ocrElementsPerPage`: Native elements for good pages, OCR elements for bad pages
- `pageImages`: Empty bytes for native pages, rendered images for OCR pages

### 4. Diagnostics & Logging
**Add** to diagnostics export:
- Per-page quality scores
- List of pages that triggered OCR fallback
- Reason codes (which heuristics triggered)

---

## Edge Cases & Risks

### Edge Case 1: All Pages Fail Quality Check
**Scenario**: Document-level `needsOcr() = false`, but ALL pages fail per-page quality check.

**Handling**: Fall back to full OCR pipeline (same as if `needsOcr() = true` initially).

```dart
if (pagesNeedingOcr.length == pageCount) {
  DebugLogger.pdf('All pages failed quality check - falling back to full OCR');
  // Call _runOcrPipeline() instead of mixed mode
}
```

### Edge Case 2: Non-Table Pages (Cover, Summary, Notes)
**Scenario**: Quality heuristics expect bid table structure. Cover pages have no headers/amounts.

**Handling**:
- `_headerGarblingScore()` returns `0.0` if no headers found (not a table page)
- Dollar amount checks return `0.0` if no amounts found
- **Risk**: Cover pages might trigger false negatives (quality looks "good" when it's actually not a table). But this is acceptable — OCR on a cover page won't hurt, and the TableExtractor will simply find no table rows.

### Edge Case 3: Legitimate Data with 'z' in Item Numbers
**Scenario**: Item number "7z-001" triggers digit-letter substitution heuristic.

**Mitigation**:
- Heuristics check CONTEXT (dollar amounts, numeric positions), not all text
- Composite score requires multiple signals to trigger
- Threshold `> 0.35` allows some noise

### Edge Case 4: Page with Small Amount of Text
**Scenario**: Page 10 is a continuation with only 2 bid items (50 chars total).

**Handling**: Quality heuristics work on **ratio-based** signals, not absolute counts. 2 items with corrupted dollar signs still score high on `digitLetterSubstitutionScore`.

### Risk 1: OCR Slowdown
**Impact**: OCR is ~10-50x slower than native text extraction.

**Mitigation**: Only OCR pages that fail quality check (expected: <10% of pages in most documents).

**Benchmark**: Springfield PDF (12 pages):
- Native-only: ~200ms
- Mixed (1 page OCR): ~200ms + 2000ms = 2.2s
- Full OCR: ~24s

**Trade-off**: 2.2s is acceptable for correctness.

### Risk 2: False Positives (Good Pages Flagged as Bad)
**Impact**: Unnecessarily OCR a clean page.

**Mitigation**:
- Tune threshold conservatively (`> 0.35` not `> 0.20`)
- Log quality scores for manual review
- Use weighted composite (prioritize high-precision signals)

### Risk 3: False Negatives (Bad Pages Not Detected)
**Impact**: Corrupted data passes through to bid items.

**Mitigation**:
- Post-processing validation (e.g., "does this dollar amount parse?")
- User-facing import report shows suspicious values
- Future: ML-based anomaly detection on parsed bid items

---

## Testing Strategy

### Unit Tests
1. **Heuristic Tests** (`test/features/pdf/services/quality_gate_test.dart`)
   - `_digitLetterSubstitutionScore()` with known good/bad strings
   - `_punctuationSubstitutionScore()` with quote-heavy vs normal text
   - `_digitSwapScore()` with 6/9 swapped numbers
   - `_headerGarblingScore()` with garbled headers

2. **Composite Score Tests**
   - Verify weights sum to 1.0
   - Test threshold boundaries (0.34, 0.35, 0.36)

3. **Integration Tests**
   - `_buildMixedElementsPerPage()` with mock OCR engine
   - `_generateSelectivePageImages()` with mock renderer

### Fixture Tests
1. **Springfield PDF** (known corruption on page 6)
   - Assert page 6 quality score `> 0.35`
   - Assert pages 1-5, 7-12 quality score `< 0.35`
   - Assert final bid items match expected (OCR'd page 6)

2. **Clean PDF** (all pages native text)
   - Assert all pages quality score `< 0.35`
   - Assert no OCR calls made

3. **Synthetic Corrupted PDF**
   - Manually create PDF with known encoding issues
   - Assert quality gate detects them

---

## Performance Considerations

### Current Native Text Path (Springfield, 12 pages)
- `extractRawText()`: ~50ms
- `NativeTextExtractor.extractFromDocument()`: ~150ms
- Total: ~200ms

### Proposed Per-Page Routing (Springfield, 1 bad page)
- `extractRawText()`: ~50ms
- `NativeTextExtractor.extractFromDocument()`: ~150ms
- `_assessPageQuality()` × 12 pages: ~10ms (string operations)
- `_buildMixedElementsPerPage()`:
  - 11 pages native: 0ms (already extracted)
  - 1 page OCR: ~2000ms (render + OCR)
- Total: ~2210ms

**Regression**: +2000ms for 1 OCR'd page vs current (which would produce garbage).

### Worst Case: All Pages Need OCR
- Same as current full OCR path (~24s for 12 pages)
- No performance regression

---

## Open Questions (For User)

1. **Threshold Tuning**: Is `> 0.35` the right threshold, or should it be more conservative (`> 0.40`)?

2. **Digit Swap Heuristic**: The 9↔6 swap detection is experimental. Should we disable it initially and add it later based on real-world data?

3. **Header Garbling Weight**: Should header garbling be weighted higher than 0.25? It's a strong signal when headers are expected, but not all pages have headers.

4. **Diagnostic Export**: Should per-page quality scores be included in the import report JSON, or just logged to console?

5. **User Notification**: Should the app show a toast/notification when mixed mode is used? ("Some pages required OCR for accuracy")

---

## Next Steps (When Ready to Implement)

1. **Create `PageQualityMetrics` class** in `lib/features/pdf/services/text_quality/`
2. **Implement heuristic methods** in `page_quality_assessor.dart`
3. **Add unit tests** for each heuristic
4. **Modify `pdf_import_service.dart`** to implement per-page routing
5. **Add integration test** with Springfield PDF fixture
6. **Run full test suite** to verify no regressions
7. **Manual testing** with Springfield PDF, observe logs
8. **Tune thresholds** based on real-world results
9. **Update diagnostics export** to include quality metrics

---

## References

- **Current Code**: `lib/features/pdf/services/pdf_import_service.dart:673-830`
- **Native Text Extractor**: `lib/features/pdf/services/text_extraction/native_text_extractor.dart:44-115`
- **Table Extractor**: `lib/features/pdf/services/table_extraction/table_extractor.dart:112-120`
- **Character Substitution Evidence**: User-provided context (7→z, 3→e, 9↔6, ,→', .→')
