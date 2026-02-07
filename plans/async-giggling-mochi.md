# Plan: Fix OCR "Empty Page" + Encoding Corruption

## Context
Springfield PDF import fails on page 6 ("Empty page!!") and pages 2-4 have wrong dollar amounts from letter stripping. Research saved at `.claude/logs/session-312-ocr-research.md`.

## Part 1: Fix Tesseract "Empty page!!" (Page 6)

**Root cause**: `img.grayscale()` keeps 4-channel RGBA -> `encodePng()` produces RGBA PNG -> Tesseract struggles with 32-bit image.

**Fix**: Convert to 1-channel before encoding PNG.

### Changes:
1. **`image_preprocessor.dart`** - Add `processed = processed.convert(numChannels: 1)` before `encodePng()` in:
   - `_preprocessIsolate()` (line ~169)
   - `_preprocessFallbackIsolate()` (line ~220)
   - `_preprocessWithEnhancementsIsolate()` (line ~769)

2. **`flusseract.cpp`** - Add Pix diagnostic logging in `CreatePixImageFromBytes()`:
   ```cpp
   logTrace("Pix: w=%d, h=%d, d=%d, spp=%d", pixGetWidth(image), pixGetHeight(image), pixGetDepth(image), pixGetSpp(image));
   ```

## Part 2: Remove Dangerous Letter Stripping

**Root cause**: `_normalizeNumericLike()` strips unrecognized letters on OCR path, producing wrong-but-valid numbers.

### Changes:
1. **`post_process_normalization.dart:331-332`** - Replace stripping with fail-parse:
   ```dart
   // BEFORE (dangerous):
   cleaned = cleaned.replaceAll(RegExp(r'[^0-9\.\-]'), '');
   // AFTER (safe):
   return '';  // Fail parse - unknown letters mean we can't trust the number
   ```

2. **`post_process_engine.dart:238-251,255-269`** - When `hasEncodingCorruption=true`, ALWAYS re-parse (remove the `isValidQuantity`/`isValidPrice` guard):
   ```dart
   if (hasEncoding || !PostProcessNumeric.isValidQuantity(...)) {
   ```

3. **Update tests** in `post_process_normalization_test.dart:655` - Change expected result from `'500.00'` to `''` (fail parse instead of strip).

## Part 3: Lower OCR Corruption Threshold

**`pdf_import_service.dart:34`** - Change `kCorruptionScoreThreshold` from 15 to 7. Pages with 4+ letters in dollar amounts (score >= 8) should get OCR as safety net.

## Verification
1. `pwsh -Command "flutter test test/features/pdf/table_extraction/"` - table extraction tests
2. `pwsh -Command "flutter test test/features/pdf/services/ocr/"` - OCR tests
3. `pwsh -Command "flutter test"` - full suite
4. Manual test with Springfield PDF - verify page 6 OCR works, pages 2-4 dollar amounts correct
