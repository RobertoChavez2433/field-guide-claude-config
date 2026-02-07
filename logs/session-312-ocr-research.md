# Session 312 Research: OCR "Empty Page" + Encoding Corruption

**Date**: 2026-02-07 | **Session**: 312
**Test PDF**: Springfield DWSRF Water System Improvements CTC Pay Items (6 pages, 1154842 bytes)

---

## Issue 1: Tesseract "Empty page!!" on Page 6

### Symptoms
- Page 6 has catastrophic encoding corruption (score=91, reversed text)
- Correctly routed to per-page OCR
- Rendered image (1733620 bytes) is perfectly readable
- Preprocessed image (973461 bytes) is perfectly readable
- Debug images saved at `C:\Users\rseba\AppData\Local\Temp\field_guide_logs\pdf_debug_images\`
- Tesseract says "Empty page!!" ~42 times despite valid Pix pointers (non-null)

### Root Cause Analysis

#### PNG Color Type Mismatch (Most Likely Cause)
The Dart `image` package v4's `grayscale()` function does **NOT reduce channels**:
- Sets R=G=B=luminance but keeps 4-channel RGBA format
- `encodePng()` checks `numChannels` to pick PNG color type:
  - 1 channel -> grayscale PNG (type 0, 8-bit)
  - 2 channels -> grayscale+alpha (type 4)
  - 3 channels -> RGB (type 2, 24-bit)
  - 4 channels -> RGBA (type 6, 32-bit)
- **Result**: After grayscale(), image is still 4 channels -> produces RGBA PNG
- Leptonica creates 32-bit Pix from RGBA PNG
- Tesseract may struggle with 32-bit RGBA during internal Otsu binarization

**Source**: Dart `image` package PNG encoder in `_writeHeader`:
```dart
..writeByte(image.hasPalette
    ? PngColorType.indexed
    : image.numChannels == 1
    ? PngColorType.grayscale
    : image.numChannels == 2
    ? PngColorType.grayscaleAlpha
    : image.numChannels == 3
    ? PngColorType.rgb
    : PngColorType.rgba)
```

**Fix**: Add `processed = processed.convert(numChannels: 1)` after grayscale + contrast to produce true 8-bit grayscale PNG.

#### Preprocessing Pipeline Flow
```
PDF page render (pdfx) -> RGBA PNG (1733620 bytes)
  -> img.decodeImage() -> Image(4 channels, uint8)
  -> img.grayscale() -> Image(4 channels, R=G=B=lum, A=255)
  -> img.adjustColor(contrast: 1.3) -> Image(4 channels, enhanced)
  -> img.encodePng() -> RGBA PNG (973461 bytes) <-- PROBLEM: still 4 channels
  -> PixImage.fromBytes() -> pixReadMem() -> 32-bit Pix
  -> SetPixImage() -> api->SetImage()
  -> api->GetHOCRText(0) -> Recognize() -> "Empty page!!"
```

### The "42 Image Loads" Mystery
The logs show ~42 "Image loaded from memory" + "Using user_defined_dpi=300" patterns. Expected: max 3 (auto PSM, sparse preprocessed, sparse raw). The extra calls likely come from cell-level re-OCR in `cell_extractor.dart:_reOcrMergedBlock` which calls `recognizeRegion()` for each merged block.

### Key Files
| File | Lines | Purpose |
|------|-------|---------|
| `lib/features/pdf/services/ocr/image_preprocessor.dart` | 152-171 | `_preprocessIsolate()` - main preprocessing |
| `lib/features/pdf/services/ocr/image_preprocessor.dart` | 195-222 | `_preprocessFallbackIsolate()` - fallback |
| `lib/features/pdf/services/ocr/image_preprocessor.dart` | 708-771 | `_preprocessWithEnhancementsIsolate()` - full pipeline |
| `lib/features/pdf/services/ocr/tesseract_ocr_engine.dart` | 284-364 | `recognizeWithConfidence()` - main OCR entry |
| `lib/features/pdf/services/ocr/tesseract_ocr_engine.dart` | 248-282 | `recognizeRegion()` - cell re-OCR |
| `lib/features/pdf/services/pdf_import_service.dart` | 564-708 | `_ocrCorruptedPages()` - per-page OCR routing |
| `lib/features/pdf/services/pdf_import_service.dart` | 651-697 | PSM fallback logic |
| `packages/flusseract/src/flusseract.cpp` | 249-255 | `CreatePixImageFromBytes()` - C++ image load |
| `packages/flusseract/src/flusseract.cpp` | 90-109 | `SetPixImage()` - DPI + SetImage |
| `packages/flusseract/src/flusseract.cpp` | 119-125 | `HOCRText()` - recognition |
| `packages/flusseract/lib/tesseract.dart` | 131-146 | `hocrText()` - Dart wrapper |
| `packages/flusseract/lib/pix_image.dart` | 24-37 | `PixImage.fromBytes()` - image creation |

### C++ Stream Capture Mechanism
```
CAPTURE_STD_STREAMS() -> redirects stdout/stderr to pipes (4096 byte buffer)
  -> C++ function runs (Tesseract prints to stderr)
LOG_STD_STREAMS() -> restores streams, reads pipe, logs via logInfo/logError
logTrace() -> goes through Flutter logger callback (independent of capture)
```

- "Image loaded from memory: %p." -> from `logTrace()` in `CreatePixImageFromBytes()`
- "Using user_defined_dpi=%d" -> from `logTrace()` in `SetPixImage()`
- "Empty page!!" -> from Tesseract stderr, captured by `HOCRText()`'s CAPTURE

### PSM Fallback Logic
```
1. Preprocessed + auto PSM (pooled engine)
   -> if < 3 elements:
2. Preprocessed + sparse PSM 11 (new engine)
   -> if still < 3 elements:
3. Raw image + sparse PSM 11 (same engine)
   -> use best result from all 3 attempts
```

---

## Issue 2: Pages 2-4 Encoding Corruption Not Fixed

### Corruption Scores
| Page | Score | Letters in $ | Total $ | Apostrophes | Verdict |
|------|-------|-------------|---------|-------------|---------|
| 1 | 4 | 2 | 6 | 0 | POSSIBLY_CORRUPTED |
| 2 | 8 | 4 | 30 | 0 | LIKELY_CORRUPTED |
| 3 | 12 | 6 | 22 | 0 | LIKELY_CORRUPTED |
| 4 | 11 | 4 | 26 | 1 | LIKELY_CORRUPTED |
| 5 | 2 | 1 | 21 | 0 | CLEAN |
| 6 | 91 | 26 | 23 | 13 | LIKELY_CORRUPTED |

### Two Thresholds
- **kCorruptionScoreThreshold = 15** (`pdf_import_service.dart:34`): Triggers OCR routing
- **Score > 5** (`pdf_import_service.dart:954`): Triggers `hasEncodingCorruption` flag for normalization

Pages 2-4 (scores 8-12): Above 5 (encoding flag set) but below 15 (no OCR routing).

### Score Formula
```dart
score = (apostrophesInNumbers * 3) + (lettersInDollarAmounts * 2);
// in native_text_extractor.dart:305
```

### Root Cause: Two-Bug Interaction

#### Bug A: Dangerous Letter Stripping (THE MAIN PROBLEM)
In `_normalizeNumericLike()` at `post_process_normalization.dart:331-332`:
```dart
// OCR path: remaining letters are likely stray artifacts, safe to strip.
cleaned = cleaned.replaceAll(RegExp(r'[^0-9\.\-]'), '');
```
This strips ALL unrecognized letters, turning `$1z,500.00` -> `1500.00` (WRONG, should be `17500.00`).

The encoding path (line 326-329) correctly returns '' (fail parse) on unrecognized letters.

#### Bug B: Encoding Flag Not in Initial Parse
`TableRowParser._parseQuantity/Price` (lines 364, 372) call `PostProcessNumeric` WITHOUT `hasEncodingCorruption`:
```dart
double? _parseQuantity(String text) {
    return PostProcessNumeric.parseQuantity(text);  // no encoding flag!
}
```

#### The Combined Effect
1. Initial parse runs WITHOUT encoding flag
2. `z` in `$1z,500.00` is not in OCR substitution map -> falls through to stripping
3. Stripping produces `1500.00` - wrong but valid
4. `PostProcessEngine._normalizeItem` checks `isValidPrice(1500.00)` -> TRUE
5. Re-parse with encoding flag NEVER triggered
6. Wrong number `1500.00` persists instead of correct `17500.00`

### Encoding Substitution Maps
**OCR substitutions** (always active, near digits):
- O/o -> 0
- I/l/L/! -> 1
- B/b -> 8

**Encoding substitutions** (only when hasEncodingCorruption=true, near digits):
- z/Z -> 7
- e (lowercase) -> 3
- J -> 3

**Apostrophe handling** (only when hasEncodingCorruption=true):
- `'` -> `,` (thousands separator)

### Key Files
| File | Lines | Purpose |
|------|-------|---------|
| `post_process_normalization.dart` | 242-354 | `_normalizeNumericLike()` - THE stripping bug |
| `post_process_normalization.dart` | 266-295 | OCR digit substitutions |
| `post_process_normalization.dart` | 297-312 | Encoding digit substitutions |
| `post_process_normalization.dart` | 323-336 | Unrecognized letter handling (strip vs fail) |
| `post_process_numeric.dart` | 29-48 | `parseCurrency()` wrapper |
| `post_process_numeric.dart` | 102-121 | `parseQuantity()` wrapper |
| `post_process_engine.dart` | 212-287 | `_normalizeItem()` - re-parse logic |
| `post_process_engine.dart` | 236-251 | Quantity re-parse (only if invalid) |
| `post_process_engine.dart` | 254-269 | Price re-parse (only if invalid) |
| `post_process_config.dart` | - | `hasEncodingCorruption` flag |
| `table_row_parser.dart` | 364-372 | Initial parse WITHOUT encoding flag |
| `pdf_import_service.dart` | 34 | `kCorruptionScoreThreshold = 15` |
| `pdf_import_service.dart` | 889-894 | OCR routing decision loop |
| `pdf_import_service.dart` | 954-957 | Encoding flag decision (score > 5) |
| `native_text_extractor.dart` | 262-329 | `analyzeEncodingCorruption()` |

### All Call Sites for parseQuantity/parseCurrency
These ALL need `hasEncodingCorruption` threaded:
- `table_row_parser.dart:365` - `_parseQuantity()`
- `table_row_parser.dart:372` - `_parsePrice()`
- `table_row_parser.dart:595` - quantity in alternate path
- `table_row_parser.dart:598` - price in alternate path
- `post_process_consistency.dart:101,124,176,177`
- `post_process_splitter.dart:110,111,169,180,255,318,323,350,390,391,478,500`
- `post_process_math_validation.dart:128`

### Existing Test Coverage
- `post_process_normalization_test.dart` line 655: Tests `$z,500.00` WITHOUT encoding -> expects `500.00` (stripping behavior that needs to change)
- 103+ normalization tests, 13 encoding-specific tests
- 1373+ total PDF tests across 64+ files

---

## Flusseract Native Layer Reference

### PixImage.fromBytes() Flow (pix_image.dart:24-37)
```dart
static PixImage fromBytes(Uint8List imageBytes) {
    ffi.Pointer<ffi.Uint8> imageBytesPtr =
        calloc.allocate<ffi.Uint8>(imageBytes.length);
    try {
      imageBytesPtr.asTypedList(imageBytes.length).setAll(0, imageBytes);
      return PixImage._(imageBytes: imageBytesPtr, length: imageBytes.length);
      // ^ calls CreatePixImageFromBytes synchronously in constructor
    } finally {
      calloc.free(imageBytesPtr); // Safe: pixReadMem already copied data
    }
}
```

### C++ Functions (flusseract.cpp)
- `Create()` -> "Creating Tesseract API instance." (logTrace)
- `Init()` -> "Tesseract initialized languages..." (logInfo) [has CAPTURE_STD_STREAMS]
- `SetPixImage()` -> checks user_defined_dpi, calls SetSourceResolution [NO capture]
- `CreatePixImageFromBytes()` -> pixReadMem -> "Image loaded from memory: %p." [has CAPTURE]
- `HOCRText()` -> GetHOCRText(0) -> Recognize [has CAPTURE - captures "Empty page!!"]
- `UTF8Text()` -> GetUTF8Text [has CAPTURE]

### DPI Threading
```
TesseractOcrEngine._setDpi(tess, 300)
  -> tess.setVariable('user_defined_dpi', '300')
    -> stored in _variables map (if _needsInit=true)
    -> or applied immediately via SetVariable FFI call
  -> SetPixImage reads user_defined_dpi and calls SetSourceResolution(300)
```

### Tesseract Instance Pool
- `TesseractInstancePool.getInstance()` -> returns cached `TesseractOcrEngine(isPooled: true)`
- Pooled instances ignore `dispose()` calls
- `disposeInternal()` for actual cleanup (called by pool)
- PSM fallback creates NON-pooled engine: `OcrEngineFactory.create(pageSegMode: sparseText)`

---

## PDF Rendering Pipeline

### PdfPageRenderer (pdf_page_renderer.dart)
- `defaultDpi = 300`
- Windows: uses `printing` package to rasterize
- Returns `PageImage(bytes, width, height, pageIndex)`
- Output format: RGBA PNG from rasterization

### Image Preprocessing (image_preprocessor.dart)
```
_preprocessIsolate (main path):
  1. img.decodeImage(bytes) -> Image (4ch RGBA)
  2. img.grayscale() -> Image (4ch, R=G=B=lum)  [DOES NOT reduce channels]
  3. img.adjustColor(contrast: 1.3)
  4. img.encodePng() -> RGBA PNG              [4ch -> type 6 RGBA]

_preprocessFallbackIsolate:
  1. Same + downscale to 1600px max

_preprocessWithEnhancementsIsolate (full):
  1. Rotation detection + correction
  2. Skew detection + correction
  3. Grayscale
  4. Adaptive contrast
  5. (Binarization REMOVED - was destroying text)
```

Binarization was removed in commit `836b856` because adaptive thresholding destroyed fine text in headers for clean PDFs. Comment at line 167: "Binarization removed - preserves grayscale image quality for clean PDFs".

---

## Complete PDF Extraction Pipeline (End-to-End)

### Phase 1: PDF Import Entry Point
**File**: `pdf_import_service.dart` -> `importBidSchedule()`

```
User selects PDF -> importBidSchedule(pdfPath, projectId, pdfBytes)
  1. Load PDF via PdfDocument (syncfusion or pdfx)
  2. Check native text viability (extractRawText, analyze clumping/headers)
  3. If viable -> Phase 2A (native text path)
  4. If not viable -> Phase 2B (full OCR path)
```

### Phase 2A: Native Text Path
**Files**: `native_text_extractor.dart`, `pdf_import_service.dart:860-960`

```
extractFromDocument(pdfDocument)
  For each page:
    1. Extract text elements via Syncfusion extractTextLines()
    2. Detect reversed text (pattern score: forwardScore vs reversedScore)
    3. If reversed, flip element text
    4. Analyze encoding corruption per page (analyzeEncodingCorruption)
       - Count apostrophes in dollar amounts (weight 3)
       - Count letters in dollar amounts (weight 2)
       - Score formula: (apostrophes * 3) + (letters * 2)
  Returns: elementsPerPage + corruptionScores

Per-page corruption routing:
  - Score > 15 (kCorruptionScoreThreshold) -> route to OCR (Phase 2B per-page)
  - Score > 5 -> set hasEncodingCorruption flag for post-processing
  - Score <= 5 -> use native text as-is
```

### Phase 2B: OCR Path (Full or Per-Page)
**Files**: `pdf_import_service.dart:340-560`, `_ocrCorruptedPages:564-708`

```
Full OCR path (when native text not viable):
  For each page:
    1. Render page to PNG (PdfPageRenderer, 300 DPI)
    2. Preprocess image (ImagePreprocessor)
    3. OCR with Tesseract (recognizeWithConfidence)
    4. Collect elements per page

Per-page OCR (when some pages corrupted):
  _ocrCorruptedPages():
    For each page:
      If clean -> use native elements, empty image
      If corrupted:
        1. Render page to PNG at 300 DPI
        2. Preprocess (grayscale + contrast)
        3. Save debug images if diagnostics enabled
        4. OCR with auto PSM
        5. PSM fallback if < 3 elements:
           a. Sparse PSM on preprocessed image
           b. Sparse PSM on raw image
        6. Use best result
```

### Phase 3: Table Extraction Pipeline
**Files**: `table_extractor.dart`, `table_locator.dart`, `header_column_detector.dart`, `line_column_detector.dart`, `cell_extractor.dart`, `table_row_parser.dart`

```
TableExtractor.extract(elements, pageImages, ...)
  1. TableLocator.locateTable(elements)
     - Find header row (keyword matching: Item, Description, Unit, Quantity, Price, Amount)
     - Find data region boundaries
     - Returns: TableRegion with header/data bounds

  2. ColumnDetector.detectColumns(elements, headerElements)
     - HeaderColumnDetector: keyword-based column identification
     - LineColumnDetector: grid line analysis from page images
     - Returns: ColumnBoundaries with column definitions

  3. CellExtractor.extractCells(elements, columnBoundaries, pageImages)
     For each row:
       - Assign elements to columns (exact match, tolerance, nearest)
       - Detect merged blocks (elements spanning multiple columns)
       - Re-OCR merged blocks via recognizeRegion() if page images available
       - Build TableRow with CellValue per column

  4. TableRowParser.parseRows(tableRows, columnBoundaries)
     - Classify rows (RowClassifier): DATA, HEADER, CONTINUATION, SUBTOTAL, etc.
     - Parse DATA rows into ParsedBidItem:
       - itemNumber, description, unit from text cells
       - quantity via _parseQuantity() -> PostProcessNumeric.parseQuantity()
       - unitPrice via _parsePrice() -> PostProcessNumeric.parseCurrency()
       - bidAmount computed or extracted
```

### Phase 4: Post-Processing Pipeline
**Files**: `post_process_engine.dart`, `post_process_normalization.dart`, `post_process_numeric.dart`, `post_process_consistency.dart`, `post_process_splitter.dart`, `post_process_validation.dart`, `post_process_math_validation.dart`

```
PostProcessEngine.process(items, config)
  1. _normalizeItem() per item:
     - Clean description artifacts
     - Normalize unit (aliases, case)
     - Re-parse quantity/price if invalid (with encoding flag if set)

  2. _analyzeBatchPatterns():
     - Detect systematic column shifts
     - Identify missing/duplicate item numbers

  3. PostProcessSplitter:
     - Fix column-shifted data (quantity in unit column, etc.)
     - Detect merged cells

  4. PostProcessConsistency:
     - Cross-validate quantity * unitPrice = bidAmount
     - Flag inconsistencies

  5. PostProcessMathValidation:
     - Verify arithmetic relationships
     - Flag computation errors

  6. PostProcessValidation:
     - Validate item number format (^\d+(\.\d+)?$)
     - Validate unit against 57 known units
```

### Phase 5: Data Storage
```
Validated ParsedBidItems -> BidItem model -> SQLite database
  - Stored in bid_items table
  - Linked to project via project_id foreign key
```

### Key Constants
| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| `defaultDpi` | 300 | pdf_page_renderer.dart:74 | PDF rendering resolution |
| `kCorruptionScoreThreshold` | 15 | pdf_import_service.dart:34 | OCR routing threshold |
| `kCorruptionLogThreshold` | 5 | native_text_extractor.dart:37 | Logging threshold |
| `kMaxDataElements` | 8 | row_classifier.dart | Max elements for DATA row |
| `kMaxContinuationElements` | 3 | row_classifier.dart | Max elements for CONTINUATION |
| `kColumnOverlapTolerance` | varies | cell_extractor.dart | Column assignment tolerance |

### Package Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| `syncfusion_flutter_pdf` | - | PDF text extraction (native path) |
| `pdfx` | - | PDF rendering to images |
| `printing` | - | PDF rasterization (Windows) |
| `flusseract` | local | Tesseract 5 OCR via FFI |
| `image` | 4.5.x | Image preprocessing (grayscale, contrast) |
| `xml` | - | HOCR parsing |

### Commit History (OCR/Encoding focus)
| Hash | Description |
|------|-------------|
| `0995d78` | launch.json |
| `47b2ea3` | Thread DPI through cell extraction pipeline |
| `63544c7` | Encoding-aware normalization, debug images, PSM fallback |
| `d8a869a` | Respect user_defined_dpi in Tesseract SetPixImage |
| `c713c77` | Thread DPI to Tesseract, eliminate double OCR recognition |
| `d8b259f` | Code review fixes for PDF extraction pipeline |
| `a7237e3` | Per-page OCR fallback for corrupted pages |
| `92904a7` | Encoding-aware item number normalizer |
| `9cdd787` | Native text pipeline crash and classification bugs |
| `3db9e34` | PDF extraction pipeline redesign (native text first) |
| `836b856` | Remove destructive binarization from OCR preprocessing |
