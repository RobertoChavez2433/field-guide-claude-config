# OCR Fallback Implementation Plan

**Status**: DEFERRED - For future use when scanned PDFs are encountered
**Created**: 2026-01-31 | **Session**: 226

## Important Note

**Current PDFs are NOT scanned.** Analysis of test fixtures shows the issue is text extraction formatting (clumped columns), not missing text. Existing parsers (`ClumpedTextParser`, `ColumnLayoutParser`) handle these cases.

**Implement this plan when:**
- Users report PDFs with zero extracted text
- `_isLikelyScannedPdf()` returns true (< 50 chars/page OR >30% single-char words)
- Actual scanned/photographed documents need to be imported

---

## Overview

Add on-device OCR as a fallback parser for scanned PDFs in the bid schedule import flow. OCR will be the 4th tier in the fallback chain, triggered when the PDF is detected as scanned/image-based.

**Branch**: `feature/ocr-fallback` (already created)

## Architecture Decision: OCR Engine Strategy

**Selected: Dual Engine for Best Accuracy**

| Platform | OCR Engine | Accuracy | Notes |
|----------|------------|----------|-------|
| Android | mobile_ocr (PaddleOCR v5) | ~96% | ~20MB model download on first use |
| iOS | mobile_ocr (Apple Vision) | ~95% | Uses system framework, no download |
| Windows | flusseract (Tesseract) | ~87% | ~23MB tessdata bundled |

This approach maximizes accuracy on mobile (where most usage occurs) while still supporting Windows desktop.

## Text Extraction Clarification

**Current app uses Syncfusion Flutter PDF** (not Python libraries):
- `PdfTextExtractor.extractText()` - plain text extraction
- `PdfTextExtractor.extractTextLines()` - text with position data
- pypdf/pdfplumber are Python-only (would need backend like Docling)

**Why OCR is needed**: Scanned PDFs have no text layer - they're just images. Syncfusion extracts nothing. OCR converts page images to text.

## New Fallback Chain

```
ColumnLayoutParser → ClumpedTextParser → RegexFallback → OcrParser (NEW)
                                                              ↓
                                              (only if scanned PDF detected)
```

## Dependencies to Add

```yaml
# pubspec.yaml
dependencies:
  pdfx: ^2.9.2           # PDF page to image (Android, iOS, Windows, macOS)
  flusseract: ^0.1.1     # Tesseract OCR (all platforms)
```

**Notes**:
- pdfx uses PDFium on Windows, native renderers on iOS/macOS
- flusseract compiles Tesseract from source (~10 min first build)
- Tessdata models: ~23MB per language, bundle `eng.traineddata`

---

## Phase 0: Dependencies & Project Setup (1 hour)

### Goal
Add OCR dependencies and configure platform-specific build settings.

### Files to Modify

| File | Changes |
|------|---------|
| `pubspec.yaml` | Add pdfx, flusseract dependencies |
| `pubspec.yaml` | Add tessdata asset |
| `android/app/proguard-rules.pro` | ProGuard rules for Tesseract if needed |

### Assets to Add

```
assets/
  tessdata/
    eng.traineddata    # ~23MB English model
```

### Verification
- [ ] `flutter pub get` succeeds
- [ ] `pwsh -Command "flutter build apk --debug"` completes (expect ~10min first time)
- [ ] No analyzer errors

---

## Phase 1: PDF to Image Service (1.5 hours)

### Goal
Create service to convert PDF pages to images using pdfx.

### Files to Create

**`lib/features/pdf/services/ocr/pdf_to_image_service.dart`**

```dart
/// Converts PDF pages to images for OCR processing.
/// Uses pdfx package for cross-platform PDF rendering.
class PdfToImageService {
  /// Convert all pages of a PDF to images.
  /// Returns list of PNG bytes, one per page.
  Future<List<Uint8List>> convertPdfToImages(
    Uint8List pdfBytes, {
    int dpi = 200,
    void Function(int current, int total)? onProgress,
  }) async;

  /// Convert a single PDF page to image.
  Future<Uint8List> convertPageToImage(
    Uint8List pdfBytes,
    int pageIndex, {
    int dpi = 200,
  }) async;
}
```

### Key Implementation Notes
- Use `PdfDocument.openData()` from pdfx
- Render at 200 DPI (balance quality vs speed)
- Return PNG format for lossless OCR input
- Handle page count limits (max 50 pages for performance)

### Verification
- [ ] Can convert test PDF page to image bytes
- [ ] Multi-page PDF returns correct page count

---

## Phase 2: OCR Service (2 hours)

### Goal
Create OCR service with isolate-based processing to avoid UI blocking.

### Files to Create

**`lib/features/pdf/services/ocr/tessdata_manager.dart`**

```dart
/// Manages tessdata model files for Tesseract OCR.
class TessdataManager {
  /// Get path to tessdata directory, extracting from assets if needed.
  Future<String> getTessdataPath() async;

  /// Check if required model is available.
  Future<bool> isModelAvailable(String language) async;

  /// Extract bundled model from assets to app directory.
  Future<void> extractBundledModel() async;
}
```

**`lib/features/pdf/services/ocr/ocr_service.dart`**

```dart
/// On-device OCR service using Tesseract.
/// All OCR operations run in isolates to avoid UI blocking.
class OcrService {
  /// Initialize OCR engine.
  Future<void> init() async;

  /// Check if OCR is ready (models available).
  Future<bool> isReady() async;

  /// Perform OCR on an image and return extracted text.
  Future<String> recognizeImage(Uint8List imageBytes) async;

  /// Perform OCR on multiple images (PDF pages).
  Future<String> recognizePages(
    List<Uint8List> pageImages, {
    void Function(int current, int total)? onProgress,
  }) async;
}
```

### Key Implementation Notes
- Follow isolate pattern from `lib/services/image_service.dart:62-78`
- Extract tessdata from assets on first use
- Cache tessdata path after extraction
- Log OCR confidence per page for diagnostics

### Verification
- [ ] OcrService.init() completes without error
- [ ] recognizeImage() returns text from test image
- [ ] UI remains responsive during OCR (isolate working)

---

## Phase 3: OCR Parser (1.5 hours)

### Goal
Create OcrParser that integrates with existing parser architecture.

### Files to Create

**`lib/features/pdf/services/parsers/ocr_parser.dart`**

```dart
/// OCR-based parser for scanned PDFs.
/// Converts pages to images, runs OCR, then feeds text through ClumpedTextParser.
class OcrParser {
  final OcrService _ocrService = OcrService();
  final PdfToImageService _pdfToImageService = PdfToImageService();
  final ClumpedTextParser _textParser = ClumpedTextParser();

  /// Parse a scanned PDF using OCR.
  Future<List<ParsedBidItem>> parse(
    Uint8List pdfBytes, {
    void Function(String stage, int current, int total)? onProgress,
  }) async {
    // 1. Ensure OCR models available
    // 2. Convert PDF pages to images
    // 3. Run OCR on each page
    // 4. Feed OCR text through ClumpedTextParser.parseText()
    // 5. Apply OCR confidence penalty (15%)
    // 6. Add "Extracted via OCR" warning
  }
}
```

### Files to Modify

**`lib/features/pdf/services/parsers/parsers.dart`**
```dart
export 'ocr_parser.dart';  // Add export
```

### Key Implementation Notes
- Reuse `ClumpedTextParser.parseText()` for OCR output
- Apply 15% confidence penalty to all OCR items
- Add warning to each item: "Extracted via OCR"
- Track OCR-specific diagnostics

### Verification
- [ ] OcrParser can be instantiated
- [ ] parse() returns items with OCR warnings
- [ ] Confidence scores are reduced by 15%

---

## Phase 4: Import Service Integration (1.5 hours)

### Goal
Integrate OCR parser into the main import fallback chain.

### Files to Modify

**`lib/features/pdf/services/pdf_import_service.dart`**

1. Add `ocr` to `ParserType` enum (line ~25):
```dart
enum ParserType {
  columnLayout,
  clumpedText,
  regexFallback,
  ocr,  // NEW
}
```

2. Add `onProgress` parameter to `importBidSchedule()`:
```dart
Future<PdfImportResult> importBidSchedule(
  String pdfPath,
  String projectId, {
  Uint8List? pdfBytes,
  bool exportDiagnostics = false,
  void Function(String stage, int current, int total)? onProgress,  // NEW
}) async
```

3. Add OCR fallback after regex (when scanned PDF detected):
```dart
// After regex fallback yields no items AND PDF is likely scanned:
if (bidItems.isEmpty && isScannedPdf) {
  try {
    final ocrParser = OcrParser();
    final ocrItems = await ocrParser.parse(bytes, onProgress: onProgress);

    if (ocrItems.isNotEmpty) {
      return PdfImportResult(
        parsedItems: ocrItems,
        bidItems: ocrItems.map((p) => p.toBidItem(projectId)).toList(),
        parserUsed: ParserType.ocr,
        warnings: ['Items extracted via OCR - please verify accuracy'],
        // ... diagnostics
      );
    }
  } catch (e) {
    debugPrint('[PDF Import] OCR fallback failed: $e');
  }
}
```

### Verification
- [ ] Scanned PDF triggers OCR fallback
- [ ] Normal PDFs skip OCR entirely
- [ ] ParserType.ocr is set in result
- [ ] onProgress callback is invoked

---

## Phase 5: UI Integration (1.5 hours)

### Goal
Add OCR progress UI and warnings for OCR-processed items.

### Files to Modify

**`lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`**

1. Add state for OCR progress:
```dart
bool _isProcessingOcr = false;
String _ocrStage = '';
int _ocrProgress = 0;
int _ocrTotal = 0;
```

2. Add OCR progress overlay:
```dart
Widget _buildOcrProgressOverlay() {
  return Center(
    child: Card(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircularProgressIndicator(),
          Text('Processing scanned PDF...'),
          Text('$_ocrStage ($_ocrProgress/$_ocrTotal)'),
          LinearProgressIndicator(
            value: _ocrTotal > 0 ? _ocrProgress / _ocrTotal : null,
          ),
        ],
      ),
    ),
  );
}
```

3. Add warning banner for OCR results:
```dart
if (result.parserUsed == ParserType.ocr) {
  Container(
    color: AppTheme.warning.withOpacity(0.1),
    child: Row(children: [
      Icon(Icons.warning_amber, color: AppTheme.warning),
      Text('This PDF was processed using OCR. Please verify all values.'),
    ]),
  ),
}
```

### Verification
- [ ] Progress UI shows during OCR processing
- [ ] Warning banner appears for OCR results
- [ ] User can review/edit OCR-extracted items

---

## Phase 6: Quality Gates & Edge Cases (1 hour)

### Goal
Add OCR-specific quality thresholds and handle edge cases.

### Files to Modify

**`lib/features/pdf/services/parsers/parser_quality_thresholds.dart`**

Add OCR-specific thresholds:
```dart
/// OCR-specific quality thresholds (more lenient due to OCR noise).
class OcrQualityThresholds {
  static const double minValidItemRatio = 0.60;      // vs 0.70 normal
  static const double minAverageConfidence = 0.50;   // vs 0.60 normal
  static const int minCharsPerPage = 100;            // Skip blank pages
  static const int maxPagesForOcr = 50;              // Performance limit
}
```

**`lib/features/pdf/services/parsers/ocr_parser.dart`**

Add edge case handling:
- Skip pages with < 100 chars (blank/corrupt)
- Limit to 50 pages max
- Handle OCR timeout gracefully
- Log per-page OCR confidence

### Verification
- [ ] Large PDFs (>50 pages) are handled
- [ ] Blank pages don't crash OCR
- [ ] Quality gates prevent garbage output

---

## Phase 7: Testing (2 hours)

### Goal
Comprehensive testing of OCR functionality.

### Files to Create

| File | Purpose |
|------|---------|
| `test/features/pdf/ocr/pdf_to_image_service_test.dart` | Image conversion tests |
| `test/features/pdf/ocr/ocr_service_test.dart` | OCR engine tests |
| `test/features/pdf/ocr/ocr_parser_test.dart` | Parser integration tests |
| `test/fixtures/pdf/scanned_bid_schedule.pdf` | Test fixture (scanned PDF) |

### Test Cases

**PdfToImageService:**
- Converts single page to image
- Handles multi-page PDF
- Respects DPI setting

**OcrService:**
- Initializes successfully
- Recognizes text from image
- Handles empty/corrupt image

**OcrParser:**
- Parses scanned bid schedule
- Applies OCR confidence penalty
- Feeds OCR text through ClumpedTextParser
- Reports progress correctly

### Verification
- [ ] All unit tests pass
- [ ] Can process real scanned PDF on device

---

## Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| 0 | 1 hour | Dependencies, tessdata asset |
| 1 | 1.5 hours | PdfToImageService |
| 2 | 2 hours | TessdataManager, OcrService with isolates |
| 3 | 1.5 hours | OcrParser |
| 4 | 1.5 hours | Import service integration |
| 5 | 1.5 hours | UI progress & warnings |
| 6 | 1 hour | Quality gates & edge cases |
| 7 | 2 hours | Testing |
| **Total** | **12 hours** | |

---

## Critical Files Reference

| File | Purpose |
|------|---------|
| `lib/features/pdf/services/pdf_import_service.dart` | Main integration point |
| `lib/features/pdf/services/parsers/clumped_text_parser.dart` | Reuse for OCR text parsing |
| `lib/services/image_service.dart` | Pattern reference for isolates |
| `lib/features/pdf/services/parsers/parser_quality_thresholds.dart` | Add OCR thresholds |

---

## Future Enhancements

1. **Cloud OCR fallback**: Docling backend via Supabase + Railway for hardest documents
2. **Multi-language support**: Add additional tessdata/PaddleOCR models
3. **OCR caching**: Cache OCR results to avoid re-processing
4. **Confidence tuning**: Adjust OCR confidence penalties based on real-world results

---

## Research Summary (Session 226)

### On-Device OCR Options
| Package | Platforms | Accuracy | Size |
|---------|-----------|----------|------|
| mobile_ocr (Ente) | Android/iOS | ~96% | 20MB |
| flusseract | All (Win/Mac/Linux/iOS/Android) | ~87% | 23MB |
| flutter_native_ocr | Android/iOS | Good | System |

### PDF to Image Options
| Package | Platforms | Notes |
|---------|-----------|-------|
| pdfx | All except Linux | Uses PDFium, well maintained |
| pdf_image_renderer | Android/iOS only | Native renderers |

### Cloud OCR (For Future Backend)
| Service | Accuracy | Cost |
|---------|----------|------|
| Azure Document Intelligence | 99.8% printed | $1.50/1K pages |
| Google Cloud Vision | 98% | $1.50/1K pages |
| Docling (self-hosted) | 94%+ tables | Free (hosting only) |

### Key Finding
Syncfusion Flutter PDF **cannot convert PDF pages to images**. Must use pdfx or similar for OCR pipeline.
