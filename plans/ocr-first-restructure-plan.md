# OCR-First PDF Import Restructuring Plan

**Date**: 2026-02-02
**Status**: READY FOR IMPLEMENTATION
**Methodology**: Test-Driven Development (Red-Green-Refactor)
**Scope**: Restructure PDF import to be OCR-first with enhanced preprocessing

---

## Executive Summary

Restructure the PDF import pipeline to prioritize OCR as the **primary extraction method** with Syncfusion text extraction as a fallback. This inverts the current architecture where OCR is only used when text extraction fails.

### Key Changes
1. **Always OCR first** - Every PDF goes through OCR pipeline
2. **200 DPI starting point** - Iteratively test higher DPI for accuracy
3. **Enhanced image preprocessing** - Add deskewing + rotation detection
4. **25-page warning** - Process all pages but warn if > 25
5. **Syncfusion fallback** - Use text extraction if OCR catastrophically fails
6. **Pipeline flow**: OCR → Text Cleanup → Parse Enhancement

### Success Criteria
- [ ] All PDFs (scanned or digital) go through OCR first
- [ ] Deskewing and rotation detection improve accuracy on angled scans
- [ ] 200 DPI produces better results than 150 DPI (validate with tests)
- [ ] PDFs > 25 pages show warning but still process
- [ ] OCR + parsing pipeline produces ≥80% field accuracy on test fixtures
- [ ] All tests written BEFORE implementation (TDD)

---

## Architecture: OCR-First Pipeline

### Current Flow (OCR as fallback)
```
PDF → Extract Text (Syncfusion) → Quality Check
                                        ↓
                                   Good text?
                                   /        \
                                YES         NO
                                 ↓           ↓
                            Parse items    OCR
```

### New Flow (OCR-first)
```
PDF → Check page count → Render pages to images (200 DPI)
          ↓                           ↓
      Warn if > 25         IMAGE PREPROCESSING
                           (grayscale, contrast, deskew,
                            rotation detect, binarize, denoise)
                                      ↓
                              ML KIT OCR (per page)
                                      ↓
                              TEXT PREPROCESSING
                              (OcrPreprocessor: s→$,
                               trailing s, spacing fixes)
                                      ↓
                           Text Normalization (clumped text)
                                      ↓
                              Parser Cascade
                           (Column → Clumped → Regex)
                                      ↓
                           Quality Check & Warnings
                                      ↓
                           ┌──────────────────┐
                           │ OCR FAILED?      │
                           │ (empty/garbled)  │
                           └────┬─────────────┘
                                ↓ YES
                      FALLBACK: Syncfusion Text Extract
                                      ↓
                              Parser Cascade
                                      ↓
                           PdfImportResult
```

---

## TDD Approach: Red-Green-Refactor

Each PR follows strict TDD:

1. **RED**: Write failing test defining expected behavior
2. **GREEN**: Implement minimal code to pass test
3. **REFACTOR**: Clean up while keeping tests green

### Test Fixtures Required

Create before implementation:

| Fixture | Purpose | Characteristics |
|---------|---------|-----------------|
| `test/assets/pdfs/digital_bid_schedule.pdf` | Baseline | Clean digital PDF, good text extraction |
| `test/assets/pdfs/scanned_straight.pdf` | OCR happy path | Scanned, straight, good quality |
| `test/assets/pdfs/scanned_rotated_5deg.pdf` | Deskew test | Scanned at 5° angle |
| `test/assets/pdfs/scanned_faded.pdf` | Contrast test | Low contrast, needs enhancement |
| `test/assets/pdfs/scanned_noisy.pdf` | Denoise test | Dirty background, speckles |
| `test/assets/pdfs/30_pages.pdf` | Page limit warning | > 25 pages |
| `test/assets/pdfs/mixed_quality.pdf` | Fallback test | Some pages OCR fails |

---

## Implementation Phases

### Phase 1: Enhanced Image Preprocessing (PR #1)

**Goal**: Add deskewing and rotation detection to improve OCR accuracy on angled scans.

#### TDD Steps

**RED (Write failing tests first)**

File: `test/features/pdf/services/ocr/image_preprocessor_test.dart`

```dart
group('Rotation detection', () {
  test('detectRotation returns angle for rotated image', () async {
    // Load rotated test image
    final bytes = await loadTestAsset('test/assets/images/rotated_5deg.png');
    final preprocessor = ImagePreprocessor();

    final angle = await preprocessor.detectRotation(bytes);

    // Should detect 5° rotation (within ±1° tolerance)
    expect(angle, inInclusiveRange(4.0, 6.0));
  });

  test('deskew corrects rotation to near-zero', () async {
    final bytes = await loadTestAsset('test/assets/images/rotated_5deg.png');
    final preprocessor = ImagePreprocessor();

    final deskewed = await preprocessor.deskew(bytes);
    final newAngle = await preprocessor.detectRotation(deskewed);

    // After deskewing, should be < 1° rotation
    expect(newAngle.abs(), lessThan(1.0));
  });

  test('preprocess applies deskewing when rotation > threshold', () async {
    final bytes = await loadTestAsset('test/assets/images/rotated_5deg.png');
    final preprocessor = ImagePreprocessor();

    final processed = await preprocessor.preprocess(bytes);
    final angle = await preprocessor.detectRotation(processed);

    // After full preprocessing, rotation should be corrected
    expect(angle.abs(), lessThan(1.0));
  });
});

group('Preprocessing pipeline', () {
  test('applies all steps in correct order', () async {
    final bytes = await loadTestAsset('test/assets/images/faded_rotated.png');
    final preprocessor = ImagePreprocessor();

    // Track which steps were applied
    final stats = await preprocessor.preprocessWithStats(bytes);

    expect(stats.appliedSteps, containsAll([
      'grayscale',
      'contrastEnhancement',
      'rotationDetection',
      'deskewing',
      'adaptiveThreshold',
      'denoising',
    ]));
    expect(stats.appliedSteps, orderedEquals([
      'grayscale',
      'rotationDetection',
      'deskewing',
      'contrastEnhancement',
      'adaptiveThreshold',
      'denoising',
    ]));
  });
});
```

**GREEN (Implement to pass tests)**

File: `lib/features/pdf/services/ocr/image_preprocessor.dart`

```dart
/// Rotation detection threshold (degrees).
/// Images rotated less than this are considered straight.
const double kRotationThreshold = 2.0;

class ImagePreprocessor {
  // ... existing code ...

  /// Detect rotation angle of image using projection profile method.
  /// Returns angle in degrees (-45 to +45).
  Future<double> detectRotation(Uint8List imageBytes) async {
    return compute(_detectRotationIsolate, imageBytes);
  }

  /// Deskew image by rotating to correct angle.
  Future<Uint8List> deskew(Uint8List imageBytes) async {
    final angle = await detectRotation(imageBytes);
    if (angle.abs() < kRotationThreshold) {
      return imageBytes; // No rotation needed
    }
    return compute(_deskewIsolate, (imageBytes, angle));
  }

  /// Enhanced preprocessing with rotation correction.
  @override
  Future<Uint8List> preprocess(Uint8List imageBytes) async {
    return compute(_preprocessEnhancedIsolate, imageBytes);
  }

  /// Preprocessing with statistics tracking (for testing/diagnostics).
  Future<PreprocessingStats> preprocessWithStats(Uint8List imageBytes) async {
    return compute(_preprocessWithStatsIsolate, imageBytes);
  }
}

/// Isolate function for rotation detection.
double _detectRotationIsolate(Uint8List bytes) {
  final image = img.decodeImage(bytes);
  if (image == null) return 0.0;

  // Convert to grayscale
  final gray = img.grayscale(image);

  // Use projection profile method
  // Test angles from -45° to +45° in 0.5° increments
  double bestAngle = 0.0;
  double maxVariance = 0.0;

  for (double angle = -45; angle <= 45; angle += 0.5) {
    final rotated = img.copyRotate(gray, angle: angle);
    final variance = _calculateProjectionVariance(rotated);

    if (variance > maxVariance) {
      maxVariance = variance;
      bestAngle = angle;
    }
  }

  return bestAngle;
}

/// Calculate variance of horizontal projection profile.
/// Higher variance = better aligned text lines.
double _calculateProjectionVariance(img.Image image) {
  // Sum pixel intensities per row
  final rowSums = List<int>.filled(image.height, 0);
  for (int y = 0; y < image.height; y++) {
    for (int x = 0; x < image.width; x++) {
      final pixel = image.getPixel(x, y);
      rowSums[y] += img.getLuminance(pixel).toInt();
    }
  }

  // Calculate variance
  final mean = rowSums.reduce((a, b) => a + b) / rowSums.length;
  final variance = rowSums.map((s) => (s - mean) * (s - mean)).reduce((a, b) => a + b) / rowSums.length;

  return variance;
}

/// Isolate function for deskewing.
Uint8List _deskewIsolate((Uint8List, double) params) {
  final bytes = params.$1;
  final angle = params.$2;

  final image = img.decodeImage(bytes);
  if (image == null) return bytes;

  // Rotate image by negative angle to correct
  final corrected = img.copyRotate(image, angle: -angle);

  return Uint8List.fromList(img.encodePng(corrected));
}

/// Enhanced preprocessing with all steps.
Uint8List _preprocessEnhancedIsolate(Uint8List bytes) {
  final image = img.decodeImage(bytes);
  if (image == null) return bytes;

  var processed = image;

  // Step 1: Convert to grayscale
  processed = img.grayscale(processed);

  // Step 2: Detect and correct rotation
  final angle = _detectRotationIsolate(bytes);
  if (angle.abs() >= kRotationThreshold) {
    processed = img.copyRotate(processed, angle: -angle);
  }

  // Step 3: Enhance contrast
  processed = img.adjustColor(processed, contrast: 1.3);

  // Step 4: Adaptive threshold (binarization)
  processed = _adaptiveThreshold(processed);

  // Step 5: Denoise
  processed = img.gaussianBlur(processed, radius: 1);

  return Uint8List.fromList(img.encodePng(processed));
}

/// Preprocessing result with statistics.
class PreprocessingStats {
  final Uint8List processedBytes;
  final List<String> appliedSteps;
  final double detectedRotation;
  final ImageStats imageStats;

  const PreprocessingStats({
    required this.processedBytes,
    required this.appliedSteps,
    required this.detectedRotation,
    required this.imageStats,
  });
}
```

**REFACTOR**
- Extract projection profile calculation to separate function
- Add comprehensive inline documentation
- Optimize rotation detection (test fewer angles if variance plateaus)

#### Files Modified
- `lib/features/pdf/services/ocr/image_preprocessor.dart` - Add deskewing
- `test/features/pdf/services/ocr/image_preprocessor_test.dart` - Rotation tests

#### Validation
- [ ] Tests pass: rotation detection accurate within ±1°
- [ ] Tests pass: deskewing corrects 5° rotation
- [ ] Tests pass: preprocessing applies steps in correct order
- [ ] `flutter analyze` clean

---

### Phase 2: 200 DPI Rendering with Adaptive Increase (PR #2)

**Goal**: Increase DPI from 150 to 200 and add mechanism to test higher DPI iteratively.

#### TDD Steps

**RED (Write failing tests first)**

File: `test/features/pdf/services/ocr/pdf_page_renderer_test.dart`

```dart
group('DPI handling', () {
  test('renderPage uses 200 DPI by default', () async {
    final document = await loadTestPdf('test/assets/pdfs/digital_bid_schedule.pdf');
    final renderer = PdfPageRenderer();

    final pageImage = await renderer.renderPage(document, 0);

    // At 200 DPI, an 8.5" x 11" page should be ~1700 x 2200 pixels
    // Allow ±10% tolerance for rounding
    expect(pageImage!.width, inInclusiveRange(1530, 1870));
    expect(pageImage.height, inInclusiveRange(1980, 2420));
  });

  test('renderPage accepts custom DPI', () async {
    final document = await loadTestPdf('test/assets/pdfs/digital_bid_schedule.pdf');
    final renderer = PdfPageRenderer();

    final pageImage300 = await renderer.renderPage(document, 0, dpi: 300);
    final pageImage150 = await renderer.renderPage(document, 0, dpi: 150);

    // 300 DPI should be 2x dimensions of 150 DPI
    expect(pageImage300!.width / pageImage150!.width, closeTo(2.0, 0.1));
  });

  test('renderPages processes all pages at specified DPI', () async {
    final document = await loadTestPdf('test/assets/pdfs/digital_bid_schedule.pdf');
    final renderer = PdfPageRenderer();

    final pages = await renderer.renderPages(document, dpi: 200).toList();

    expect(pages.length, equals(document.pages.count));
    for (final page in pages) {
      expect(page.width, greaterThan(1500)); // 200 DPI minimum
    }
  });
});

group('DPI comparison tests', () {
  test('higher DPI produces larger images', () async {
    final document = await loadTestPdf('test/assets/pdfs/scanned_straight.pdf');
    final renderer = PdfPageRenderer();

    final page150 = await renderer.renderPage(document, 0, dpi: 150);
    final page200 = await renderer.renderPage(document, 0, dpi: 200);
    final page300 = await renderer.renderPage(document, 0, dpi: 300);

    expect(page150!.bytes.length, lessThan(page200!.bytes.length));
    expect(page200.bytes.length, lessThan(page300!.bytes.length));
  });
});
```

**GREEN (Implement to pass tests)**

File: `lib/features/pdf/services/ocr/pdf_page_renderer.dart`

```dart
class PdfPageRenderer {
  /// Default DPI for OCR.
  /// Started at 150, increased to 200 for better accuracy.
  /// TODO: Test 250 and 300 DPI if 200 DPI results are insufficient.
  static const int defaultDpi = 200;

  /// DPI values to test iteratively for accuracy improvement.
  /// Use these in manual testing to find optimal DPI.
  static const List<int> testDpiValues = [150, 200, 250, 300, 400];

  // ... rest of implementation uses defaultDpi ...
}
```

Update `_renderPageIsolate` to correctly calculate dimensions at 200 DPI:

```dart
Future<_RenderResult> _renderPageIsolate(_RenderParams params) async {
  // ... existing setup ...

  // Calculate dimensions based on DPI
  // pdfx page.width/height are in points (72 DPI)
  // Scale to target DPI: pixels = (points / 72) * targetDPI
  final scale = params.dpi / 72.0;
  final targetWidth = page.width * scale;
  final targetHeight = page.height * scale;

  debugPrint('[Renderer] Rendering page ${params.pageIndex} at ${params.dpi} DPI: ${targetWidth}x${targetHeight}');

  // ... rest of rendering ...
}
```

**REFACTOR**
- Add logging of rendered dimensions for debugging
- Document DPI recommendations based on testing
- Extract DPI calculation to separate function for clarity

#### Files Modified
- `lib/features/pdf/services/ocr/pdf_page_renderer.dart` - Change default to 200 DPI
- `test/features/pdf/services/ocr/pdf_page_renderer_test.dart` - DPI validation tests

#### Validation
- [ ] Tests pass: 200 DPI is default
- [ ] Tests pass: custom DPI works correctly
- [ ] Tests pass: higher DPI produces larger images
- [ ] Manual test: compare OCR accuracy at 150 vs 200 vs 250 DPI
- [ ] Document results: which DPI gives best accuracy/performance trade-off

---

### Phase 3: OCR-First Pipeline Restructure (PR #3)

**Goal**: Invert pipeline so OCR runs FIRST, Syncfusion is FALLBACK.

#### TDD Steps

**RED (Write failing tests first)**

File: `test/features/pdf/services/pdf_import_service_ocr_first_test.dart`

```dart
group('OCR-first pipeline', () {
  test('always attempts OCR first, even for digital PDFs', () async {
    final service = PdfImportService();
    final pdfPath = 'test/assets/pdfs/digital_bid_schedule.pdf';

    final result = await service.importBidSchedule(pdfPath, 'test-project');

    // Even digital PDFs should go through OCR first
    expect(result.usedOcr, isTrue);
    expect(result.ocrConfidence, isNotNull);
    expect(result.ocrConfidence, greaterThan(0.7)); // Digital should have high confidence
  });

  test('uses Syncfusion fallback when OCR catastrophically fails', () async {
    final service = PdfImportService();
    // Mock OCR service to return empty text
    final pdfPath = 'test/assets/pdfs/digital_bid_schedule.pdf';

    final result = await service.importBidSchedule(pdfPath, 'test-project');

    // Should detect OCR failure and fall back
    expect(result.metadata['ocrFailed'], isTrue);
    expect(result.metadata['usedFallback'], equals('syncfusion'));
    expect(result.bidItems.isNotEmpty, isTrue); // Fallback should succeed
  });

  test('applies text preprocessing after OCR', () async {
    // PDF with known OCR errors (s → $, etc.)
    final service = PdfImportService();
    final pdfPath = 'test/assets/pdfs/scanned_with_ocr_errors.pdf';

    final result = await service.importBidSchedule(pdfPath, 'test-project');

    // Should have corrected OCR errors
    final descriptions = result.bidItems.map((i) => i.description).join(' ');
    expect(descriptions, contains('\$')); // Should have $ not s
    expect(descriptions.contains(RegExp(r'\$\d+\.\d{2}s')), isFalse); // No trailing s
  });

  test('processes PDFs over 25 pages with warning', () async {
    final service = PdfImportService();
    final pdfPath = 'test/assets/pdfs/30_pages.pdf';

    final result = await service.importBidSchedule(pdfPath, 'test-project');

    expect(result.warnings, contains(contains('30 pages')));
    expect(result.warnings, contains(contains('25 pages')));
    expect(result.metadata['pageCount'], equals(30));
    expect(result.bidItems.isNotEmpty, isTrue); // Should still process
  });
});

group('Pipeline flow validation', () {
  test('pipeline executes steps in correct order', () async {
    final service = PdfImportService();
    final pdfPath = 'test/assets/pdfs/scanned_rotated_5deg.pdf';

    // Enable diagnostics to track pipeline execution
    final result = await service.importBidSchedule(
      pdfPath,
      'test-project',
      exportDiagnostics: true,
    );

    final diagnostics = result.diagnostics!;
    expect(diagnostics.metadata['pipelineSteps'], orderedEquals([
      'pageCountCheck',
      'renderPages',
      'imagePreprocessing',
      'ocrRecognition',
      'textPreprocessing',
      'normalization',
      'parsing',
    ]));
  });
});
```

**GREEN (Implement to pass tests)**

File: `lib/features/pdf/services/pdf_import_service.dart`

Major restructure of `importBidSchedule()`:

```dart
/// Maximum pages before showing warning (not a hard limit).
const int kMaxPagesBeforeWarning = 25;

/// Minimum OCR quality to avoid fallback.
/// If OCR produces very little text with low confidence, try Syncfusion.
const double kMinOcrConfidenceForSuccess = 0.3;
const int kMinOcrCharsForSuccess = 100;

Future<PdfImportResult> importBidSchedule(
  String pdfPath,
  String projectId, {
  Uint8List? pdfBytes,
  bool exportDiagnostics = false,
}) async {
  _diagnostics.logPipelineEntry('importBidSchedule (OCR-FIRST)', context: {
    'pdfPath': pdfPath,
    'projectId': projectId,
  });

  final warnings = <String>[];
  final pipelineSteps = <String>[];

  try {
    final bytes = await _loadPdfSource(pdfPath, pdfBytes);
    final document = PdfDocument(inputBytes: bytes);
    final pageCount = document.pages.count;

    pipelineSteps.add('pageCountCheck');

    // Step 1: Check page count and warn if > 25
    if (pageCount > kMaxPagesBeforeWarning) {
      warnings.add(
        'PDF has $pageCount pages. Processing may take longer than usual. '
        'Consider splitting documents over ${kMaxPagesBeforeWarning} pages for faster imports.'
      );
      _diagnostics.log('WARNING: $pageCount pages exceeds recommended limit of $kMaxPagesBeforeWarning');
    }

    // Step 2: ALWAYS run OCR pipeline first
    _diagnostics.log('Starting OCR-first pipeline...');
    pipelineSteps.add('ocrPipeline');

    final ocrResult = await _runOcrPipeline(
      document,
      pipelineSteps: pipelineSteps,
    );

    String extractedText = ocrResult.text;
    double? ocrConfidence = ocrResult.confidence;
    bool usedOcr = true;
    bool usedFallback = false;

    // Step 3: Check if OCR catastrophically failed
    if (_ocrCatastrophicFailure(extractedText, ocrConfidence, pageCount)) {
      _diagnostics.log('OCR catastrophic failure detected - falling back to Syncfusion');
      warnings.add('OCR processing had low confidence. Using text extraction fallback.');

      pipelineSteps.add('syncfusionFallback');
      extractedText = extractRawText(document);
      usedFallback = true;

      // If fallback also fails, we're done
      if (extractedText.trim().isEmpty) {
        warnings.add('No text could be extracted. PDF may be image-only or corrupted.');
      }
    }

    // Extract page samples for diagnostics
    final pageSamples = _extractPageSamples(document);
    final isClumpedText = _detectClumpedText(extractedText);

    // Step 4: Parser cascade (same as before)
    pipelineSteps.add('parserCascade');

    // Try column parser first...
    // Try clumped parser second...
    // Regex fallback...
    // [Existing parser cascade code]

    // Build metadata
    final metadata = {
      'source': 'bid_schedule',
      'file': pdfPath,
      'pageCount': pageCount,
      'usedOcr': usedOcr,
      'ocrFailed': usedFallback,
      'usedFallback': usedFallback ? 'syncfusion' : null,
      'pipelineSteps': pipelineSteps,
    };

    // ... rest of result building ...

  } catch (e) {
    _diagnostics.logParserFailure('importBidSchedule', 'Exception: $e');
    rethrow;
  }
}

/// Run complete OCR pipeline: Render → Preprocess → OCR → Text Cleanup
Future<({String text, double confidence})> _runOcrPipeline(
  PdfDocument document, {
  required List<String> pipelineSteps,
}) async {
  final pageCount = document.pages.count;
  _diagnostics.logOcrPipelineStart(pageCount);
  final stopwatch = Stopwatch()..start();

  final ocrService = MlKitOcrService();
  final renderer = PdfPageRenderer();
  final imagePreprocessor = ImagePreprocessor();
  final buffer = StringBuffer();
  final pageConfidences = <double>[];

  try {
    pipelineSteps.add('renderPages');

    // Process page by page for memory efficiency
    await for (final pageImage in renderer.renderPages(document)) {
      pipelineSteps.add('imagePreprocessing');

      // IMAGE PREPROCESSING: deskew, contrast, denoise
      final preprocessedImage = await imagePreprocessor.preprocess(pageImage.bytes);

      pipelineSteps.add('ocrRecognition');

      // ML KIT OCR with confidence tracking
      final ocrResult = await ocrService.recognizeWithConfidence(
        preprocessedImage,
        width: pageImage.width,
        height: pageImage.height,
      );

      pageConfidences.add(ocrResult.confidence);

      pipelineSteps.add('textPreprocessing');

      // TEXT PREPROCESSING: Fix OCR character errors (s→$, etc.)
      final cleanedText = OcrPreprocessor.process(ocrResult.text);

      _diagnostics.logOcrPageResult(
        pageImage.pageIndex + 1,
        cleanedText.length,
      );

      buffer.writeln(cleanedText);
      buffer.writeln(''); // Page separator
    }

    stopwatch.stop();
    final totalChars = buffer.length;

    // Calculate average confidence
    final avgConfidence = pageConfidences.isEmpty
        ? 0.0
        : pageConfidences.reduce((a, b) => a + b) / pageConfidences.length;

    _diagnostics.logOcrPipelineComplete(totalChars, stopwatch.elapsed, avgConfidence: avgConfidence);

    return (text: buffer.toString(), confidence: avgConfidence);
  } finally {
    ocrService.dispose();
  }
}

/// Check if OCR failed so badly we should try Syncfusion fallback.
bool _ocrCatastrophicFailure(String ocrText, double? confidence, int pageCount) {
  // Empty or near-empty text
  if (ocrText.trim().length < kMinOcrCharsForSuccess) {
    return true;
  }

  // Very low confidence
  if (confidence != null && confidence < kMinOcrConfidenceForSuccess) {
    return true;
  }

  // Less than 10 chars per page (basically nothing)
  final charsPerPage = ocrText.length / pageCount;
  if (charsPerPage < 10) {
    return true;
  }

  return false;
}
```

**REFACTOR**
- Extract OCR failure detection to separate method with clear thresholds
- Add comprehensive logging at each pipeline step
- Document why we use specific confidence/length thresholds
- Clean up variable naming for clarity

#### Files Modified
- `lib/features/pdf/services/pdf_import_service.dart` - Major restructure
- `test/features/pdf/services/pdf_import_service_ocr_first_test.dart` - New tests

#### Validation
- [ ] Tests pass: OCR runs first for all PDFs
- [ ] Tests pass: Syncfusion fallback works when OCR fails
- [ ] Tests pass: Text preprocessing applied after OCR
- [ ] Tests pass: 25+ page warning shown
- [ ] Tests pass: Pipeline steps tracked in metadata
- [ ] `flutter analyze` clean

---

### Phase 4: Remove needsOcr() Detection Logic (PR #4)

**Goal**: Clean up obsolete detection code since we always OCR now.

#### TDD Steps

**RED (Write failing tests first)**

File: `test/features/pdf/services/pdf_import_service_test.dart`

```dart
group('OCR detection removal', () {
  test('needsOcr method no longer exists', () {
    final service = PdfImportService();

    // This should not compile after removal
    // expect(() => service.needsOcr('test', 1), throwsNoSuchMethodError);
  });

  test('all PDFs go through OCR regardless of text quality', () async {
    final service = PdfImportService();

    // Digital PDF with perfect text extraction
    final digitalResult = await service.importBidSchedule(
      'test/assets/pdfs/digital_bid_schedule.pdf',
      'test-project',
    );
    expect(digitalResult.usedOcr, isTrue);

    // Scanned PDF with poor text extraction
    final scannedResult = await service.importBidSchedule(
      'test/assets/pdfs/scanned_faded.pdf',
      'test-project',
    );
    expect(scannedResult.usedOcr, isTrue);

    // Empty text extraction (would have triggered needsOcr before)
    final emptyResult = await service.importBidSchedule(
      'test/assets/pdfs/scanned_straight.pdf',
      'test-project',
    );
    expect(emptyResult.usedOcr, isTrue);
  });
});
```

**GREEN (Implement to pass tests)**

File: `lib/features/pdf/services/pdf_import_service.dart`

Remove:
- `needsOcr()` method (lines 197-241 in current version)
- `kMinCharsPerPage` constant (only used by needsOcr)
- `kMaxSingleCharRatio` constant (only used by needsOcr)

Keep:
- `_ocrCatastrophicFailure()` for fallback detection (different purpose)

**REFACTOR**
- Update comments that referenced `needsOcr()`
- Remove related debug logging that mentioned detection
- Clean up any test files that tested `needsOcr()` logic

#### Files Modified
- `lib/features/pdf/services/pdf_import_service.dart` - Remove detection method
- `test/features/pdf/services/pdf_import_service_test.dart` - Remove detection tests
- `test/features/pdf/services/pdf_import_service_ocr_test.dart` - Remove detection tests

#### Validation
- [ ] Tests pass: OCR always runs
- [ ] Code search: no references to `needsOcr` remain
- [ ] `flutter analyze` clean
- [ ] All existing PDF tests still pass

---

### Phase 5: UI Updates for OCR-First (PR #5)

**Goal**: Update preview screen to reflect OCR-first approach.

#### TDD Steps

**RED (Write failing tests first)**

File: `test/features/pdf/presentation/screens/pdf_import_preview_screen_test.dart`

```dart
group('OCR-first UI updates', () {
  testWidgets('always shows OCR indicator for all imports', (tester) async {
    final result = PdfImportResult(
      bidItems: [createMockBidItem()],
      usedOcr: true,
      ocrConfidence: 0.92,
    );

    await tester.pumpWidget(createTestApp(
      child: PdfImportPreviewScreen(
        importResult: result,
        projectId: 'test-project',
      ),
    ));

    // OCR indicator should always be visible
    expect(find.text('OCR 92%'), findsOneWidget);
    expect(find.byIcon(Icons.document_scanner), findsOneWidget);
  });

  testWidgets('shows fallback indicator when Syncfusion used', (tester) async {
    final result = PdfImportResult(
      bidItems: [createMockBidItem()],
      usedOcr: true,
      ocrConfidence: 0.15, // Low confidence
      metadata: {
        'ocrFailed': true,
        'usedFallback': 'syncfusion',
      },
    );

    await tester.pumpWidget(createTestApp(
      child: PdfImportPreviewScreen(
        importResult: result,
        projectId: 'test-project',
      ),
    ));

    // Should show fallback warning
    expect(find.text(contains('fallback')), findsOneWidget);
    expect(find.text('OCR 15%'), findsOneWidget); // Still show OCR attempted
  });

  testWidgets('shows page count warning for >25 pages', (tester) async {
    final result = PdfImportResult(
      bidItems: [createMockBidItem()],
      usedOcr: true,
      metadata: {'pageCount': 30},
      warnings: ['PDF has 30 pages. Processing may take longer than usual.'],
    );

    await tester.pumpWidget(createTestApp(
      child: PdfImportPreviewScreen(
        importResult: result,
        projectId: 'test-project',
      ),
    ));

    // Should show page count in header
    expect(find.text(contains('30 pages')), findsOneWidget);
  });
});
```

**GREEN (Implement to pass tests)**

File: `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`

Update summary header to always show OCR info:

```dart
// In build(), summary header section
Container(
  width: double.infinity,
  padding: const EdgeInsets.all(16),
  color: AppTheme.primaryBlue.withValues(alpha: 0.1),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'Found ${_editableItems.length} pay items',
        style: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w600,
          color: AppTheme.textPrimary,
        ),
      ),

      // Page count (if available)
      if (widget.importResult.metadata['pageCount'] != null) ...[
        const SizedBox(height: 4),
        Text(
          '${widget.importResult.metadata['pageCount']} pages processed',
          style: TextStyle(fontSize: 13, color: AppTheme.textSecondary),
        ),
      ],

      const SizedBox(height: 4),
      Text(
        'All items extracted via OCR. Review and edit items before importing.',
        style: TextStyle(fontSize: 13, color: AppTheme.textSecondary),
      ),

      // OCR confidence chip (always shown now)
      const SizedBox(height: 8),
      Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          // OCR confidence
          Chip(
            avatar: Icon(
              Icons.document_scanner,
              size: 16,
              color: _getConfidenceColor(widget.importResult.ocrConfidence),
            ),
            label: Text(
              widget.importResult.ocrConfidence != null
                  ? 'OCR ${(widget.importResult.ocrConfidence! * 100).toStringAsFixed(0)}%'
                  : 'OCR processed',
              style: TextStyle(
                fontSize: 12,
                color: _getConfidenceColor(widget.importResult.ocrConfidence),
              ),
            ),
            backgroundColor: _getConfidenceColor(widget.importResult.ocrConfidence)
                .withValues(alpha: 0.1),
            side: BorderSide.none,
          ),

          // Fallback indicator if used
          if (widget.importResult.metadata['usedFallback'] != null)
            Chip(
              avatar: Icon(Icons.warning_amber, size: 16, color: AppTheme.warning),
              label: Text(
                'Used ${widget.importResult.metadata['usedFallback']} fallback',
                style: TextStyle(fontSize: 12, color: AppTheme.warning),
              ),
              backgroundColor: AppTheme.warning.withValues(alpha: 0.1),
              side: BorderSide.none,
            ),
        ],
      ),

      if (_selectedIndices.isNotEmpty) ...[
        const SizedBox(height: 8),
        Text(
          '${_selectedIndices.length} items selected for import',
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: AppTheme.primaryBlue,
          ),
        ),
      ],
    ],
  ),
),

// Helper to get confidence color
Color _getConfidenceColor(double? confidence) {
  if (confidence == null) return AppTheme.textSecondary;
  if (confidence >= 0.8) return AppTheme.success;
  if (confidence >= 0.5) return AppTheme.warning;
  return AppTheme.error;
}
```

**REFACTOR**
- Extract confidence chip widget to separate component
- Add accessibility labels for screen readers
- Improve color contrast for low-vision users

#### Files Modified
- `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart` - UI updates
- `test/features/pdf/presentation/screens/pdf_import_preview_screen_test.dart` - Widget tests

#### Validation
- [ ] Tests pass: OCR indicator always shown
- [ ] Tests pass: Fallback indicator shown when applicable
- [ ] Tests pass: Page count displayed
- [ ] Manual test: UI looks good on phone and tablet
- [ ] `flutter analyze` clean

---

### Phase 6: Integration Tests with Real Fixtures (PR #6)

**Goal**: End-to-end tests with real PDF fixtures covering all scenarios.

#### TDD Steps

**RED (Write failing tests first)**

File: `test/features/pdf/integration/ocr_first_integration_test.dart`

```dart
void main() {
  setUpAll(() async {
    // Ensure test fixtures exist
    await verifyTestFixtures();
  });

  group('OCR-first integration tests', () {
    test('digital PDF: high confidence OCR with accurate extraction', () async {
      final service = PdfImportService();
      final result = await service.importBidSchedule(
        'test/assets/pdfs/digital_bid_schedule.pdf',
        'test-project',
      );

      expect(result.usedOcr, isTrue);
      expect(result.ocrConfidence, greaterThanOrEqualTo(0.8));
      expect(result.bidItems.length, greaterThan(10));
      expect(result.warnings, isEmpty);

      // Spot check: first item should have complete fields
      final firstItem = result.bidItems.first;
      expect(firstItem.itemNumber, isNotEmpty);
      expect(firstItem.description, isNotEmpty);
      expect(firstItem.unit, isNotEmpty);
      expect(firstItem.bidQuantity, greaterThan(0));
      expect(firstItem.unitPrice, isNotNull);
    });

    test('scanned straight: good OCR with minor corrections', () async {
      final service = PdfImportService();
      final result = await service.importBidSchedule(
        'test/assets/pdfs/scanned_straight.pdf',
        'test-project',
      );

      expect(result.usedOcr, isTrue);
      expect(result.ocrConfidence, greaterThanOrEqualTo(0.7));
      expect(result.bidItems.length, greaterThan(5));

      // Text preprocessing should have fixed OCR errors
      final allText = result.bidItems.map((i) => '${i.description} ${i.itemNumber}').join(' ');
      expect(allText, contains('\$')); // Should have currency symbols
      expect(allText.contains(RegExp(r's\d+\.\d{2}')), isFalse); // No s→$ errors
    });

    test('scanned rotated 5°: deskewing improves accuracy', () async {
      final service = PdfImportService();
      final result = await service.importBidSchedule(
        'test/assets/pdfs/scanned_rotated_5deg.pdf',
        'test-project',
      );

      expect(result.usedOcr, isTrue);
      expect(result.ocrConfidence, greaterThanOrEqualTo(0.65)); // Lower but acceptable
      expect(result.bidItems.isNotEmpty, isTrue);

      // Deskewing should have helped
      final diagnostics = result.diagnostics;
      expect(diagnostics?.metadata['appliedDeskewing'], isTrue);
    });

    test('scanned faded: contrast enhancement improves OCR', () async {
      final service = PdfImportService();
      final result = await service.importBidSchedule(
        'test/assets/pdfs/scanned_faded.pdf',
        'test-project',
      );

      expect(result.usedOcr, isTrue);
      expect(result.bidItems.isNotEmpty, isTrue);

      // May have lower confidence but should still extract items
      if (result.ocrConfidence != null && result.ocrConfidence! < 0.6) {
        expect(result.warnings, isNotEmpty); // Should warn about low quality
      }
    });

    test('30 pages: processes all with warning', () async {
      final service = PdfImportService();
      final result = await service.importBidSchedule(
        'test/assets/pdfs/30_pages.pdf',
        'test-project',
      );

      expect(result.usedOcr, isTrue);
      expect(result.metadata['pageCount'], equals(30));
      expect(result.warnings, contains(contains('30 pages')));
      expect(result.bidItems.isNotEmpty, isTrue);
    });

    test('mixed quality: uses fallback when OCR fails', () async {
      final service = PdfImportService();
      final result = await service.importBidSchedule(
        'test/assets/pdfs/mixed_quality.pdf',
        'test-project',
      );

      // May have used fallback if OCR was very poor
      if (result.metadata['usedFallback'] != null) {
        expect(result.metadata['usedFallback'], equals('syncfusion'));
        expect(result.warnings, contains(contains('fallback')));
      }

      // Should still get items either way
      expect(result.bidItems.isNotEmpty, isTrue);
    });
  });

  group('Pipeline performance tests', () {
    test('5-page PDF completes in under 30 seconds', () async {
      final service = PdfImportService();
      final stopwatch = Stopwatch()..start();

      await service.importBidSchedule(
        'test/assets/pdfs/scanned_straight.pdf', // 5 pages
        'test-project',
      );

      stopwatch.stop();
      expect(stopwatch.elapsed.inSeconds, lessThan(30));
    });
  });
}

Future<void> verifyTestFixtures() async {
  final requiredFixtures = [
    'test/assets/pdfs/digital_bid_schedule.pdf',
    'test/assets/pdfs/scanned_straight.pdf',
    'test/assets/pdfs/scanned_rotated_5deg.pdf',
    'test/assets/pdfs/scanned_faded.pdf',
    'test/assets/pdfs/scanned_noisy.pdf',
    'test/assets/pdfs/30_pages.pdf',
    'test/assets/pdfs/mixed_quality.pdf',
  ];

  for (final path in requiredFixtures) {
    final file = File(path);
    if (!await file.exists()) {
      throw Exception('Missing test fixture: $path');
    }
  }
}
```

**GREEN (Create test fixtures and ensure tests pass)**

1. Gather or create 7 PDF test fixtures covering scenarios
2. Add to `test/assets/pdfs/` directory
3. Update `.gitattributes` to track PDFs with LFS if large
4. Run tests and iterate on thresholds until all pass

**REFACTOR**
- Extract common test setup to helper functions
- Add detailed comments explaining what each fixture tests
- Document expected outcomes for each fixture in README

#### Files Added
- `test/features/pdf/integration/ocr_first_integration_test.dart` - Integration tests
- `test/assets/pdfs/digital_bid_schedule.pdf` - Test fixture
- `test/assets/pdfs/scanned_straight.pdf` - Test fixture
- `test/assets/pdfs/scanned_rotated_5deg.pdf` - Test fixture
- `test/assets/pdfs/scanned_faded.pdf` - Test fixture
- `test/assets/pdfs/scanned_noisy.pdf` - Test fixture
- `test/assets/pdfs/30_pages.pdf` - Test fixture
- `test/assets/pdfs/mixed_quality.pdf` - Test fixture
- `test/assets/pdfs/README.md` - Fixture documentation

#### Validation
- [ ] All integration tests pass
- [ ] Test fixtures are documented
- [ ] Performance test passes (< 30s for 5 pages)
- [ ] Coverage report shows >80% for OCR components

---

## Summary of Changes

### Components Modified
| Component | Change Type | Description |
|-----------|-------------|-------------|
| ImagePreprocessor | Enhancement | Add deskewing + rotation detection |
| PdfPageRenderer | Configuration | Increase default DPI to 200 |
| PdfImportService | Major Restructure | OCR-first with Syncfusion fallback |
| PdfImportService | Removal | Delete needsOcr() detection logic |
| PdfImportPreviewScreen | UI Update | Always show OCR info, page count |
| Test Fixtures | New | 7 PDF fixtures for testing |

### Test Coverage by Phase
| Phase | Unit Tests | Integration Tests | Widget Tests |
|-------|------------|-------------------|--------------|
| 1 | 8 | 0 | 0 |
| 2 | 5 | 0 | 0 |
| 3 | 12 | 0 | 0 |
| 4 | 3 | 0 | 0 |
| 5 | 0 | 0 | 5 |
| 6 | 0 | 8 | 0 |
| **Total** | **28** | **8** | **5** |

### Performance Expectations
| Scenario | Target | Measured |
|----------|--------|----------|
| 5-page scanned PDF | < 30s | TBD |
| 10-page digital PDF | < 45s | TBD |
| 25-page mixed PDF | < 120s | TBD |
| Memory peak (5 pages) | < 200MB | TBD |

---

## Risk Mitigation

### Risk 1: Deskewing too slow
**Mitigation**:
- Limit rotation detection to ±15° instead of ±45°
- Use 1° increments instead of 0.5° (faster but less accurate)
- Add flag to skip deskewing if processing time > 10s/page

### Risk 2: 200 DPI not sufficient
**Mitigation**:
- Test 250 and 300 DPI iteratively
- Add adaptive DPI: start at 200, retry at 300 if confidence < 0.6
- Document findings in plan

### Risk 3: OCR accuracy still poor on real-world PDFs
**Mitigation**:
- Collect problematic PDFs from user testing
- Tune preprocessing parameters (contrast, threshold values)
- Consider adding text enhancement step (sharpen, despeckle)
- Future: Add PaddleOCR as secondary engine

### Risk 4: Breaking existing imports
**Mitigation**:
- Run full test suite after each PR
- Test with 20+ existing PDFs from production
- Feature flag to temporarily revert to old behavior if needed

---

## Verification Checklist

### Per-PR Verification
Each PR must pass:
- [ ] All new tests pass (RED → GREEN achieved)
- [ ] All existing tests still pass (no regressions)
- [ ] `flutter analyze` reports 0 issues
- [ ] Code reviewed for TDD compliance
- [ ] Documentation updated

### Final Acceptance (All 6 PRs Complete)
- [ ] All 7 test fixtures import successfully
- [ ] OCR confidence ≥ 0.7 for clean scans
- [ ] OCR confidence ≥ 0.5 for faded/rotated scans
- [ ] Text preprocessing fixes s→$, trailing s, spacing errors
- [ ] Deskewing handles ≤10° rotation accurately
- [ ] 200 DPI vs 150 DPI comparison documented
- [ ] 25+ page warning displays correctly
- [ ] Syncfusion fallback works when OCR fails
- [ ] No `needsOcr()` references remain in codebase
- [ ] UI always shows OCR indicator
- [ ] Integration tests cover happy path + edge cases
- [ ] Performance targets met (< 30s for 5 pages)
- [ ] Memory usage acceptable (< 200MB for 5 pages)

---

## Future Enhancements (Deferred)

### Iteration 1: Adaptive DPI
If 200 DPI results are insufficient:
- Test 250 DPI on problematic fixtures
- Test 300 DPI on problematic fixtures
- Implement adaptive DPI: retry at higher DPI if confidence < threshold

### Iteration 2: Advanced Preprocessing
If basic deskewing is insufficient:
- Add perspective correction for photos of documents
- Add unsharp mask for blurry scans
- Add morphological operations (erosion/dilation) for broken characters

### Iteration 3: Dual-Engine OCR
If ML Kit accuracy is insufficient:
- Add PaddleOCR as secondary engine
- Try ML Kit first, fall back to Paddle if confidence < 0.6
- Compare accuracy and decide on default

### Iteration 4: Table Structure Detection
For grid-based bid schedules:
- Detect table structure using line detection
- Extract cells and reconstruct rows
- Handle multi-line cells and merged cells

---

## Definition of Done

This plan is COMPLETE when:
1. All 6 PRs merged to main
2. All verification checklist items checked
3. 424+ tests passing (existing + 41 new)
4. No analyzer warnings
5. User can import scanned PDFs with ≥80% accuracy
6. OCR-first approach validated on 20+ real-world PDFs
7. Performance acceptable (< 30s for 5 pages)
8. Documentation updated with DPI findings
9. Plan marked COMPLETE in state file

---

## Implementation Timeline

Assuming 1-2 days per PR:

| Week | PRs | Focus |
|------|-----|-------|
| 1 | #1-2 | Enhanced preprocessing, 200 DPI |
| 2 | #3-4 | OCR-first restructure, cleanup |
| 3 | #5-6 | UI updates, integration tests |

**Total**: 2-3 weeks for complete OCR-first restructure.

---

## Agent Assignments

| Phase | Primary Agent | Supporting Agent |
|-------|---------------|------------------|
| PR #1 | pdf-agent | qa-testing-agent |
| PR #2 | pdf-agent | qa-testing-agent |
| PR #3 | pdf-agent | code-review-agent |
| PR #4 | pdf-agent | code-review-agent |
| PR #5 | flutter-specialist-agent | pdf-agent |
| PR #6 | qa-testing-agent | pdf-agent |

---

**End of Plan**
