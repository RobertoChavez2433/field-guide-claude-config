# Robust PDF Extraction with OCR

**Date**: 2026-02-02
**Status**: Ready for Implementation
**Scope**: ML Kit OCR integration for scanned PDF bid schedules

---

## Overview

### Purpose
Enable reliable import of scanned/image-based PDF bid schedules by integrating Google ML Kit on-device OCR. Currently, PDFs with no extractable text fail silently or produce empty results.

### Success Criteria
- [ ] Scanned PDFs with typed bid items import with ≥80% field accuracy
- [ ] OCR triggers automatically when text extraction is poor/empty
- [ ] No user intervention required - seamless experience
- [ ] Works fully offline (bundled ML Kit models)
- [ ] APK size increase ≤6MB

### Non-Goals (This Phase)
- PaddleOCR dual-engine (deferred - add later if ML Kit insufficient)
- Table structure detection (complex layouts)
- Handwritten text recognition
- Multi-language OCR (English only for now)

---

## Architecture Decisions

### Decision 1: ML Kit Bundled Models
**Choice**: Bundled (not unbundled)
**Rationale**:
- Only ~4-6MB APK impact
- Works immediately without download
- Critical for offline-first field use
- No Google Play Services dependency

**Trade-off**: Larger APK, but acceptable given offline requirements.

### Decision 2: Automatic OCR Detection
**Choice**: Auto-detect and run OCR when needed (Option A from brainstorming)
**Rationale**:
- Seamless UX - inspectors don't need to understand OCR
- Existing `_isLikelyScannedPdf()` detection can trigger OCR path
- Show small indicator "OCR processed" for transparency

**Flow**:
```
PDF Selected → Extract Text (Syncfusion)
                    ↓
            Text quality check
           /                 \
      Good text            Poor/Empty
          ↓                     ↓
    Existing parsers      Render to image
                               ↓
                      IMAGE PREPROCESSING
                      (contrast, deskew, denoise)
                               ↓
                          ML Kit OCR
                               ↓
                          OCR text
                               ↓
                       OcrPreprocessor
                       (text-level fixes: s→$, etc.)
                               ↓
                        Existing parsers
```

### Decision 3: Dual Preprocessing Strategy
**Choice**: Preprocess BOTH image (before OCR) AND text (after OCR)
**Rationale**:
- **Image preprocessing**: Improves ML Kit accuracy on low-quality scans
  - Contrast enhancement for faded documents
  - Deskewing for rotated scans
  - Denoising for dirty backgrounds
  - Binarization for better text/background separation
- **Text preprocessing**: Fixes OCR character-level errors
  - Existing OcrPreprocessor handles s→$, trailing s, etc.
  - Runs AFTER OCR on extracted text

### Decision 4: Page-by-Page Processing
**Choice**: Process one page at a time with isolate
**Rationale**:
- Memory constraint: Mid-range devices have ~100-150MB heap
- ML Kit OCR spikes 30-50MB per page at high resolution
- Isolate prevents UI blocking during processing

### Decision 4: Defer PaddleOCR
**Choice**: Implement ML Kit first, evaluate before adding PaddleOCR
**Rationale**:
- ML Kit handles 90%+ of typed bid schedules
- PaddleOCR adds 20-30MB + significant integration complexity
- Can add later if real-world testing shows gaps
- See `.claude/backlogged-plans/export-management-multiuser-plan.md` for future dual-engine notes

---

## Current State Analysis

### Existing PDF Import Pipeline
Location: `lib/features/pdf/services/pdf_import_service.dart`

```
PDF File
    ↓
extractRawText() - Syncfusion PdfTextExtractor
    ↓
_isLikelyScannedPdf() - Detection (chars/page, single-char ratio)
    ↓
Parser Cascade:
  1. ColumnLayoutParser (position-based)
  2. ClumpedTextParser (token + state machine)
  3. RegexFallbackParser (flexible patterns)
    ↓
Quality Gates (min 3 items, 70% valid, etc.)
    ↓
PdfImportResult with ParsedBidItem list
```

### Existing OCR Support
- **OcrPreprocessor** (`lib/features/pdf/services/parsers/ocr_preprocessor.dart`)
  - Fixes character-level OCR errors AFTER text is extracted
  - Patterns: s→$, trailing s, spaced letters, period as thousands separator
  - Activates when ≥2 OCR indicators detected

- **Scanned PDF Detection** (`_isLikelyScannedPdf()`)
  - Empty text → returns true
  - <50 chars/page → returns true
  - >30% single-char words → returns true

### Gap: No Image-to-Text Pipeline
Currently, if Syncfusion extracts no text, the import fails. Need to:
1. Render PDF page to image
2. Run ML Kit text recognition
3. Feed result into existing parser pipeline

---

## Implementation Phases

### Phase 1: ML Kit Integration Foundation (PR #1)

**Estimated Effort**: 1-2 days

#### Package Addition
```yaml
# pubspec.yaml
dependencies:
  google_mlkit_text_recognition: ^0.15.0  # On-device OCR
  image: ^4.0.0                           # Image preprocessing in isolate
```

#### New Files

**`lib/features/pdf/services/ocr/ml_kit_ocr_service.dart`**
```dart
/// On-device OCR using Google ML Kit bundled models.
///
/// Processes images page-by-page to manage memory.
/// Returns raw text that feeds into existing parser pipeline.
class MlKitOcrService {
  final TextRecognizer _textRecognizer;

  MlKitOcrService() : _textRecognizer = TextRecognizer();

  /// Recognize text from image bytes.
  /// Returns extracted text string.
  Future<String> recognizeFromBytes(Uint8List imageBytes) async {
    final inputImage = InputImage.fromBytes(
      bytes: imageBytes,
      metadata: InputImageMetadata(...),
    );
    final result = await _textRecognizer.processImage(inputImage);
    return result.text;
  }

  /// Recognize text from file path.
  Future<String> recognizeFromFile(String imagePath) async {
    final inputImage = InputImage.fromFilePath(imagePath);
    final result = await _textRecognizer.processImage(inputImage);
    return result.text;
  }

  /// Get confidence score for recognized text.
  /// Useful for quality indicators.
  Future<OcrResult> recognizeWithConfidence(Uint8List imageBytes) async {
    // Returns text + confidence + bounding boxes
  }

  /// Release resources when done.
  void dispose() {
    _textRecognizer.close();
  }
}

class OcrResult {
  final String text;
  final double confidence;
  final List<TextBlock> blocks;
}
```

**`lib/features/pdf/services/ocr/pdf_page_renderer.dart`**
```dart
/// Renders PDF pages to images for OCR processing.
///
/// Uses Syncfusion to render pages at configurable DPI.
/// Processes in isolate to avoid UI blocking.
class PdfPageRenderer {
  /// Default DPI for OCR (balance quality vs memory)
  static const int defaultDpi = 150;

  /// Render single page to image bytes.
  /// Uses isolate for background processing.
  Future<Uint8List?> renderPage(
    PdfDocument document,
    int pageIndex, {
    int dpi = defaultDpi,
  }) async {
    return compute(_renderPageIsolate, RenderParams(
      documentBytes: document.saveSync(),
      pageIndex: pageIndex,
      dpi: dpi,
    ));
  }

  /// Render multiple pages (generator for memory efficiency).
  Stream<PageImage> renderPages(
    PdfDocument document, {
    int? startPage,
    int? endPage,
    int dpi = defaultDpi,
  }) async* {
    final start = startPage ?? 0;
    final end = endPage ?? document.pages.count - 1;

    for (int i = start; i <= end; i++) {
      final bytes = await renderPage(document, i, dpi: dpi);
      if (bytes != null) {
        yield PageImage(pageIndex: i, bytes: bytes);
      }
    }
  }
}

class PageImage {
  final int pageIndex;
  final Uint8List bytes;
}
```

**`lib/features/pdf/services/ocr/image_preprocessor.dart`**
```dart
/// Image preprocessing to improve OCR accuracy on low-quality scans.
///
/// Applies enhancements BEFORE passing image to ML Kit:
/// - Contrast enhancement for faded documents
/// - Grayscale conversion for consistent processing
/// - Adaptive thresholding (binarization) for text/background separation
/// - Noise reduction for dirty/speckled backgrounds
/// - Deskewing for rotated scans (future enhancement)
///
/// Uses Flutter's `image` package for processing in isolate.
class ImagePreprocessor {
  /// Process image to improve OCR quality.
  /// Runs in isolate to avoid blocking UI.
  Future<Uint8List> preprocess(Uint8List imageBytes) async {
    return compute(_preprocessIsolate, imageBytes);
  }

  /// Check if preprocessing would help this image.
  /// Returns true for low-contrast or noisy images.
  Future<bool> needsPreprocessing(Uint8List imageBytes) async {
    final stats = await compute(_analyzeImageIsolate, imageBytes);
    return stats.contrast < 0.5 || stats.noiseLevel > 0.3;
  }
}

/// Isolate function for image preprocessing.
Future<Uint8List> _preprocessIsolate(Uint8List bytes) async {
  final image = img.decodeImage(bytes);
  if (image == null) return bytes;

  var processed = image;

  // 1. Convert to grayscale for consistent processing
  processed = img.grayscale(processed);

  // 2. Enhance contrast (helps with faded scans)
  processed = img.adjustColor(
    processed,
    contrast: 1.3,  // Boost contrast 30%
  );

  // 3. Apply adaptive threshold for binarization
  // This separates text from background more clearly
  processed = _adaptiveThreshold(processed);

  // 4. Denoise (remove small speckles)
  processed = img.gaussianBlur(processed, radius: 1);

  return Uint8List.fromList(img.encodePng(processed));
}

/// Adaptive thresholding for better text/background separation.
img.Image _adaptiveThreshold(img.Image src) {
  final dst = img.Image.from(src);
  final blockSize = 15;
  final c = 10; // Constant subtracted from mean

  for (int y = 0; y < src.height; y++) {
    for (int x = 0; x < src.width; x++) {
      // Calculate local mean in block around pixel
      final mean = _localMean(src, x, y, blockSize);
      final pixel = src.getPixel(x, y);
      final gray = img.getLuminance(pixel);

      // Threshold: white if above (mean - c), black otherwise
      final newValue = gray > (mean - c) ? 255 : 0;
      dst.setPixelRgba(x, y, newValue, newValue, newValue, 255);
    }
  }
  return dst;
}

/// Image statistics for preprocessing decision.
class ImageStats {
  final double contrast;    // 0.0-1.0, higher = more contrast
  final double noiseLevel;  // 0.0-1.0, higher = more noise
  final double brightness;  // 0.0-1.0, average brightness
}
```

#### Android Configuration

**Verify 64-bit only** (ML Kit requirement) in `android/app/build.gradle.kts`:
```kotlin
android {
    defaultConfig {
        ndk {
            abiFilters += listOf("arm64-v8a", "x86_64")
            // NO armeabi-v7a or x86 (32-bit)
        }
    }
}
```

#### Tests

**`test/features/pdf/services/ocr/ml_kit_ocr_service_test.dart`**
- Test text recognition from sample images
- Test error handling for corrupt images
- Test memory cleanup on dispose

**`test/features/pdf/services/ocr/pdf_page_renderer_test.dart`**
- Test page rendering at various DPI
- Test page range selection
- Test isolate execution

---

### Phase 2: OCR Pipeline Integration (PR #2)

**Estimated Effort**: 2-3 days

#### Modify Existing Files

**`lib/features/pdf/services/pdf_import_service.dart`**

Add OCR path to `importBidSchedule()`:

```dart
// After existing text extraction
String extractedText = await extractRawText(document);

// NEW: Check if OCR is needed
if (_needsOcr(extractedText, document)) {
  extractedText = await _runOcrPipeline(document);
  _logDiagnostic('OCR pipeline activated');
}

// Continue with existing parser cascade...
```

Add new methods:

```dart
/// Determine if OCR should be run.
bool _needsOcr(String extractedText, PdfDocument document) {
  // Empty text - definitely needs OCR
  if (extractedText.trim().isEmpty) return true;

  // Very little text per page
  final charsPerPage = extractedText.length / document.pages.count;
  if (charsPerPage < 50) return true;

  // High ratio of single-char words (OCR artifact indicator)
  final words = extractedText.split(RegExp(r'\s+'));
  final singleCharWords = words.where((w) => w.length == 1).length;
  if (words.isNotEmpty && singleCharWords / words.length > 0.3) {
    return true;
  }

  return false;
}

/// Run OCR on all pages and concatenate text.
/// Pipeline: Render → Image Preprocess → ML Kit OCR → Text Preprocess
Future<String> _runOcrPipeline(PdfDocument document) async {
  final ocrService = MlKitOcrService();
  final renderer = PdfPageRenderer();
  final imagePreprocessor = ImagePreprocessor();
  final buffer = StringBuffer();

  try {
    // Process page by page for memory efficiency
    await for (final pageImage in renderer.renderPages(document)) {
      // Step 1: IMAGE PREPROCESSING (before OCR)
      // Enhances contrast, denoises, binarizes for better OCR accuracy
      final preprocessedImage = await imagePreprocessor.preprocess(pageImage.bytes);
      _logDiagnostic('Image preprocessed: ${pageImage.bytes.length} → ${preprocessedImage.length} bytes');

      // Step 2: ML KIT OCR
      final rawText = await ocrService.recognizeFromBytes(preprocessedImage);
      _logDiagnostic('OCR page ${pageImage.pageIndex + 1}: ${rawText.length} chars');

      // Step 3: TEXT PREPROCESSING (after OCR)
      // Fixes character-level OCR errors (s→$, trailing s, etc.)
      // Note: OcrPreprocessor is applied later in the parser pipeline
      // via TextNormalizer, so we just pass raw text here

      buffer.writeln(rawText);
      buffer.writeln(''); // Page separator
    }

    return buffer.toString();
  } finally {
    ocrService.dispose();
  }
}
```

**`lib/features/pdf/data/models/pdf_import_result.dart`**

Add OCR metadata:

```dart
class PdfImportResult {
  // ... existing fields ...

  /// Whether OCR was used for text extraction.
  final bool usedOcr;

  /// OCR confidence if applicable (0.0-1.0).
  final double? ocrConfidence;
}
```

**`lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`**

Show OCR indicator:

```dart
// In build(), after item count display
if (widget.result.usedOcr) {
  Chip(
    avatar: Icon(Icons.document_scanner, size: 16),
    label: Text('OCR processed'),
    backgroundColor: AppTheme.primaryBlue.withOpacity(0.1),
  ),
}
```

#### Diagnostics Integration

**`lib/features/pdf/services/parsers/parser_diagnostics.dart`**

Add OCR-specific logging:

```dart
static void logOcrPipelineStart(int pageCount) {
  if (!kPdfParserDiagnostics) return;
  debugPrint('[OCR] Starting OCR pipeline for $pageCount pages');
}

static void logOcrPageResult(int page, int charCount, double confidence) {
  if (!kPdfParserDiagnostics) return;
  debugPrint('[OCR] Page $page: $charCount chars, ${(confidence * 100).toInt()}% confidence');
}

static void logOcrPipelineComplete(int totalChars, Duration elapsed) {
  if (!kPdfParserDiagnostics) return;
  debugPrint('[OCR] Complete: $totalChars chars in ${elapsed.inMilliseconds}ms');
}
```

#### Tests

**`test/features/pdf/services/pdf_import_service_ocr_test.dart`**
- Test `_needsOcr()` detection logic
- Test OCR pipeline integration
- Test result includes `usedOcr` flag
- Test with sample scanned PDF (add to test assets)

---

### Phase 3: Quality & Edge Cases (PR #3)

**Estimated Effort**: 1-2 days

#### Memory Management

Add adaptive DPI based on page size and device memory:

```dart
/// Adaptive DPI based on page size and device memory.
int _calculateOptimalDpi(Size pageSize, int availableMemoryMb) {
  final pageArea = pageSize.width * pageSize.height;

  if (availableMemoryMb < 100 || pageArea > 1000000) {
    return 100; // Low quality, safe
  } else if (availableMemoryMb < 150 || pageArea > 500000) {
    return 150; // Medium quality
  } else {
    return 200; // High quality
  }
}
```

#### Error Handling

Handle OCR failures gracefully:

```dart
Future<String> _runOcrPipeline(PdfDocument document) async {
  try {
    // ... existing OCR code ...
  } on PlatformException catch (e) {
    _logDiagnostic('OCR platform error: ${e.message}');
    return ''; // Fall through to "no items found" warning
  } on OutOfMemoryError {
    _logDiagnostic('OCR out of memory - trying lower DPI');
    return _runOcrPipelineLowMemory(document);
  }
}
```

#### User Feedback for Long Operations

Show progress during OCR:

```dart
// State
bool _isProcessingOcr = false;
int _currentOcrPage = 0;
int _totalOcrPages = 0;

// UI during OCR
if (_isProcessingOcr) {
  Column(
    children: [
      CircularProgressIndicator(),
      SizedBox(height: 8),
      Text('Processing page $_currentOcrPage of $_totalOcrPages'),
      Text('This may take a moment for scanned documents'),
    ],
  ),
}
```

---

## Database Changes

**None required for OCR-only phase.**

The OCR integration uses existing data models (`ParsedBidItem`, `PdfImportResult`). New fields (`usedOcr`, `ocrConfidence`) are transient - not persisted.

---

## File Summary

### New Files
| File | Purpose |
|------|---------|
| `lib/features/pdf/services/ocr/ml_kit_ocr_service.dart` | ML Kit wrapper |
| `lib/features/pdf/services/ocr/pdf_page_renderer.dart` | PDF to image |
| `lib/features/pdf/services/ocr/image_preprocessor.dart` | Image enhancement before OCR |
| `lib/features/pdf/services/ocr/ocr.dart` | Barrel export |
| `test/features/pdf/services/ocr/ml_kit_ocr_service_test.dart` | Unit tests |
| `test/features/pdf/services/ocr/pdf_page_renderer_test.dart` | Unit tests |
| `test/features/pdf/services/ocr/image_preprocessor_test.dart` | Preprocessing tests |
| `test/features/pdf/services/pdf_import_service_ocr_test.dart` | Integration tests |
| `test/assets/scanned_bid_schedule.pdf` | Test fixture |
| `test/assets/faded_scan.png` | Low-contrast test image |
| `test/assets/noisy_scan.png` | Noisy background test image |

### Modified Files
| File | Changes |
|------|---------|
| `pubspec.yaml` | Add google_mlkit_text_recognition, image |
| `android/app/build.gradle.kts` | Verify 64-bit ABI filter |
| `lib/features/pdf/services/pdf_import_service.dart` | Add OCR path |
| `lib/features/pdf/services/parsers/parser_diagnostics.dart` | OCR logging |
| `lib/features/pdf/data/models/pdf_import_result.dart` | Add usedOcr field |
| `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart` | OCR indicator |
| `lib/features/pdf/presentation/screens/pdf_import_screen.dart` | Progress UI |

---

## Testing Strategy

### Unit Tests
- `MlKitOcrService`: Text recognition accuracy, resource cleanup
- `PdfPageRenderer`: Page rendering, DPI settings, isolate execution
- `ImagePreprocessor`: Contrast enhancement, denoising, binarization
- `_needsOcr()`: Detection thresholds

### Image Preprocessor Tests
- Test contrast enhancement on faded scan
- Test noise reduction on speckled image
- Test binarization improves text/background separation
- Test preprocessing decision logic (`needsPreprocessing()`)
- Test isolate execution doesn't block UI

### Integration Tests
- Full pipeline: Scanned PDF → OCR → Parser → Preview
- Memory: Process 20-page document without crash
- Error recovery: Corrupt page doesn't stop entire import

### Manual Testing
- Test with 10-20 real bid schedule PDFs:
  - Clean digital PDFs (should NOT trigger OCR)
  - Scanned but clear (should OCR successfully)
  - Low-quality scans (should OCR with warnings)
  - Mixed (some pages scanned, some digital)

### Acceptance Metrics
| Metric | Target |
|--------|--------|
| OCR triggers appropriately | 95% correct detection |
| Field extraction accuracy | ≥80% on clear scans |
| Processing time | <30s for 10-page PDF |
| Memory peak | <80MB additional |
| No crashes | 100% |

---

## Risk Mitigation

### Risk 1: ML Kit accuracy insufficient
**Mitigation**:
- Test with real bid schedules early
- OcrPreprocessor already handles common OCR errors
- Can add PaddleOCR as fallback later

### Risk 2: Memory issues on low-end devices
**Mitigation**:
- Page-by-page processing
- Adaptive DPI based on available memory
- Catch OutOfMemoryError and retry at lower quality

### Risk 3: Long processing times frustrate users
**Mitigation**:
- Show progress indicator with page count
- Process in background isolate (UI stays responsive)
- Add "Cancel" option for very long documents

### Risk 4: 64-bit only breaks some devices
**Mitigation**:
- Android minSdk 24 already drops most 32-bit devices
- 2026 device market is 95%+ 64-bit
- Document requirement in release notes

---

## Future: PaddleOCR Dual-Engine

If ML Kit proves insufficient for complex bid schedules:

1. Add `paddle_ocr` or `onnx_mobile_ocr` package (~20-30MB)
2. Create `PaddleOcrService` with same interface
3. Add OCR engine selector: `enum OcrEngine { mlKit, paddleOcr, auto }`
4. Auto mode: Try ML Kit first, fall back if confidence < 70%
5. Table structure detection for grid-based bid schedules

---

## Dependencies

**Blocked by**: Nothing
**Blocks**: Nothing (export management is separate plan)

---

## Implementation Order

```
Week 1:
├── PR #1: ML Kit Foundation
│   ├── Add package
│   ├── Create MlKitOcrService
│   ├── Create PdfPageRenderer
│   └── Unit tests

Week 2:
├── PR #2: Pipeline Integration
│   ├── Integrate into PdfImportService
│   ├── Add OCR detection logic
│   ├── Update result model
│   └── Integration tests

Week 2-3:
├── PR #3: Quality & Polish
│   ├── Memory management
│   ├── Error handling
│   ├── Progress UI
│   └── Manual testing with real PDFs
```

---

## Verification Checklist

Before marking complete:

- [ ] `flutter analyze` passes
- [ ] All new tests pass
- [ ] Manual test: Clean PDF does NOT trigger OCR
- [ ] Manual test: Scanned PDF DOES trigger OCR
- [ ] Manual test: OCR results feed correctly into parsers
- [ ] Manual test: Preview shows "OCR processed" indicator
- [ ] Manual test: 20-page PDF processes without memory crash
- [ ] APK size increase measured and documented
