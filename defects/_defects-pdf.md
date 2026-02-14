# Defects: PDF

Active patterns for pdf. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [DATA] 2026-02-06: Empty Uint8List Passes Null Guards But Crashes img.decodeImage()
**Pattern**: Native text path creates `Uint8List(0)` per page. Code checks `if (bytes == null)` but empty list is not null — `img.decodeImage()` throws RangeError on empty bytes instead of returning null.
**Prevention**: Always check `bytes == null || bytes.isEmpty` before passing to image decoders
**Ref**: @lib/features/pdf/services/table_extraction/cell_extractor.dart:761, :920

### [DATA] 2026-02-06: Element Count Thresholds Tuned for OCR, Not Native Text
**Pattern**: `kMaxDataElements=8` and `kMaxContinuationElements=3` were tuned for OCR (groups words). Native text creates 1 element per word, so a 7-column bid row = 11+ elements → misclassified as UNKNOWN.
**Prevention**: When adding word-level extraction, review all element count thresholds. Use secondary signals (hasNumericContent) as guards instead of rigid caps.
**Ref**: @lib/features/pdf/services/table_extraction/row_classifier.dart:82-85

### [DATA] 2026-02-06: OCR Used on Digital PDFs Without Trying Native Text First
**Pattern**: `importBidSchedule()` always renders PDF to images and runs Tesseract OCR, even on digital PDFs with extractable native text.
**Prevention**: Always try native text extraction first, fall back to OCR only when `needsOcr()` returns true
**Ref**: @lib/features/pdf/services/pdf_import_service.dart:694

### [DATA] 2026-02-06: Adaptive Thresholding Destroys Clean PDF Images
**Pattern**: Unconditional binarization converts 300 DPI grayscale to binary, destroying 92% of image data
**Prevention**: Only apply binarization to noisy scans/photos; clean PDF renders need grayscale + contrast only
**Ref**: @lib/features/pdf/services/ocr/image_preprocessor.dart:152-177

### [DATA] 2026-02-04: Substring Keyword Matching Causes False Positives
**Pattern**: Using `String.contains()` for keyword matching allows substring false positives
**Prevention**: Use word-boundary matching (RegExp `\bKEYWORD\b`) for single-word patterns
**Ref**: @lib/features/pdf/services/table_extraction/table_locator.dart:299

### [DATA] 2026-02-04: else-if Chain Blocks Multi-Category Keyword Matching
**Pattern**: Using `else if` chain in keyword matching prevents independent elements from matching different categories
**Prevention**: Use independent `if` + `continue` pattern
**Ref**: @lib/features/pdf/services/table_extraction/header_column_detector.dart:228

<!-- Add defects above this line -->
