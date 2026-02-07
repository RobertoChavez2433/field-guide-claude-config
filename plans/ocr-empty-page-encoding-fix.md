# Plan: Fix OCR "Empty Page" + Encoding Corruption Pipeline

**Date**: 2026-02-07
**Research**: `.claude/logs/session-312-ocr-research.md`
**Test PDF**: Springfield DWSRF Water System Improvements CTC Pay Items (6 pages)

---

## Problem Summary

Two interacting bugs cause PDF import failures:

1. **Page 6**: Tesseract prints "Empty page!!" 42 times despite valid rendered images — zero text extracted
2. **Pages 2-4**: Dollar amounts silently corrupted (`$1z,500.00` → `$1,500.00` instead of `$17,500.00`)

---

## Part 1: Fix Tesseract "Empty Page" (RGBA → True Grayscale)

### Root Cause
`img.grayscale()` from the Dart `image` package sets R=G=B=luminance but **keeps 4-channel RGBA** format. When `encodePng()` runs, it checks `numChannels` (still 4) and produces an RGBA PNG (type 6, 32-bit). Leptonica creates a 32-bit Pix, and Tesseract's internal Otsu binarization fails silently on 32-bit RGBA input.

### Changes

#### 1A. `image_preprocessor.dart` — Add channel conversion (4 locations)

**`_preprocessIsolate()`** (line ~170, before `encodePng`):
```dart
// Convert to true 1-channel grayscale for Tesseract compatibility
processed = processed.convert(numChannels: 1);
return Uint8List.fromList(img.encodePng(processed));
```

**`_preprocessFallbackIsolate()`** (line ~221, before `encodePng`):
```dart
processed = processed.convert(numChannels: 1);
return Uint8List.fromList(img.encodePng(processed));
```

**`_preprocessWithEnhancementsIsolate()`** — TWO locations:
- Early exit path (line ~723, uniform image):
  ```dart
  processed = img.grayscale(processed);
  processed = processed.convert(numChannels: 1);
  return Uint8List.fromList(img.encodePng(processed));
  ```
- Main path (line ~770, after contrast enhancement):
  ```dart
  processed = processed.convert(numChannels: 1);
  return Uint8List.fromList(img.encodePng(processed));
  ```

#### 1B. `tesseract_ocr_engine.dart` — Fix `recognizeRegion()` (line ~265)

This method encodes a cropped `img.Image` directly to PNG for cell re-OCR. The cropped region inherits the parent's RGBA format.

```dart
// Convert to 1-channel grayscale before encoding
var grayCropped = img.grayscale(cropped);
grayCropped = grayCropped.convert(numChannels: 1);
final croppedBytes = Uint8List.fromList(img.encodePng(grayCropped));
```

#### 1C. `flusseract.cpp` — Add Pix diagnostic logging

In `CreatePixImageFromBytes()` (line ~254), after `pixReadMem`:
```cpp
logTrace("Image loaded from memory: %p.", image);
if (image) {
    logTrace("Pix: w=%d, h=%d, d=%d, spp=%d",
             pixGetWidth(image), pixGetHeight(image),
             pixGetDepth(image), pixGetSpp(image));
}
```

Helps verify the fix: should show `d=8, spp=1` instead of `d=32, spp=4`.

### Expected Results
- Debug images shrink ~4x in size (8-bit vs 32-bit PNG)
- Pix logs show `d=8, spp=1`
- Page 6 "Empty page!!" stops; text is extracted

---

## Part 2: Replace Dangerous Letter Stripping with Fail-Parse

### Root Cause
In `_normalizeNumericLike()` at `post_process_normalization.dart:331-332`, the OCR path strips ALL unrecognized letters via `replaceAll(RegExp(r'[^0-9\.\-]'), '')`. This turns `$1z,500.00` → `1500.00` — a wrong but valid-looking number that passes all downstream validation and is never corrected.

### Changes

#### 2A. `post_process_normalization.dart:331-332` — Fail-parse instead of stripping

**Before** (line 332):
```dart
// OCR path: remaining letters are likely stray artifacts, safe to strip.
cleaned = cleaned.replaceAll(RegExp(r'[^0-9\.\-]'), '');
```

**After**:
```dart
// Unrecognized letters make the number untrustworthy — fail the parse so
// post-processing can retry with the encoding flag or discard.
return '';
```

This makes both the OCR path and the encoding path return `''` (fail-parse) when unrecognized letters remain, instead of silently producing wrong numbers.

#### 2B. `post_process_normalization_test.dart` — Update test expectation

Line ~655: Change expected result from `'500.00'` to `''`:
```dart
test('z causes fail-parse without encoding flag', () {
  expect(
    PostProcessNormalization.normalizeCurrencyString(
      '\$z,500.00',
      hasEncodingCorruption: false,
    ),
    '',  // Fail parse — unknown letter makes number untrustworthy
  );
});
```

Also update test name to reflect new behavior.

---

## Part 3: Force Re-Parse When Encoding Corruption Detected

### Root Cause
`PostProcessEngine._normalizeItem()` only re-parses quantity/price when `isValidQuantity()` or `isValidPrice()` returns false. After Part 2's fix, corrupted values will fail initial parse (return null), so re-parse WILL trigger. But we should also force re-parse of values that were initially parsed without the encoding flag, in case any slipped through as wrong-but-valid.

### Changes

#### 3A. `post_process_engine.dart` — Force re-parse when encoding flag is set

**Lines ~238-252** (quantity re-parse guard):
```dart
// BEFORE:
if (!PostProcessNumeric.isValidQuantity(item.bidQuantity, item.unit)) {

// AFTER:
if (hasEncoding || !PostProcessNumeric.isValidQuantity(item.bidQuantity, item.unit)) {
```

**Lines ~255-269** (price re-parse guard):
```dart
// BEFORE:
if (!PostProcessNumeric.isValidPrice(item.unitPrice)) {

// AFTER:
if (hasEncoding || !PostProcessNumeric.isValidPrice(item.unitPrice)) {
```

**Rationale**: When `hasEncodingCorruption=true`, always re-parse with the encoding substitution maps (z→7, e→3, J→3, apostrophe→comma) to ensure correct values regardless of what the initial parse produced.

---

## Part 4: Thread `hasEncodingCorruption` Through Entire Pipeline

### Root Cause
The encoding flag is defined in `PostProcessConfig` and correctly used in `PostProcessEngine._normalizeItem()`, but **19+ call sites** in 4 other files call `parseQuantity()`/`parseCurrency()` without the flag. This means encoding substitutions are never applied during initial parsing, consistency checks, column splitting, or math validation.

### Strategy
Rather than adding `hasEncodingCorruption` as a parameter to every individual method, pass it through via the classes that orchestrate the pipeline. Each sub-processor already receives its items from `PostProcessEngine`, which has access to `config.hasEncodingCorruption`.

### Changes

#### 4A. `table_row_parser.dart` — Thread flag through initial parsing

Add `hasEncodingCorruption` to `parseRows()` signature and internal helpers:

```dart
// parseRows() — add parameter
List<ParsedBidItem> parseRows(
  List<TableRow> rows,
  ColumnBoundaries boundaries, {
  bool hasEncodingCorruption = false,
})

// _parseQuantity (line ~364) — add parameter
double? _parseQuantity(String text, {bool hasEncodingCorruption = false}) {
  return PostProcessNumeric.parseQuantity(text, hasEncodingCorruption: hasEncodingCorruption);
}

// _parsePrice (line ~371) — add parameter
double? _parsePrice(String text, {bool hasEncodingCorruption = false}) {
  return PostProcessNumeric.parseCurrency(text, hasEncodingCorruption: hasEncodingCorruption);
}
```

Update ALL internal call sites (lines ~183, ~184, ~595, ~598) to pass the flag.

#### 4B. Caller chain: `pdf_import_service.dart` → `table_extractor.dart` → `table_row_parser.dart`

Thread `hasEncodingCorruption` from the import service through to the row parser. The import service already computes the flag at line 954. It needs to pass it down through `TableExtractor.extract()` to `TableRowParser.parseRows()`.

- `table_extractor.dart` `extract()` method — add `hasEncodingCorruption` parameter
- Pass it through to `TableRowParser.parseRows()`

#### 4C. `post_process_consistency.dart` — Add flag parameter

Add `hasEncodingCorruption` to `applyConsistencyRules()` and thread through:
- `resolveBidAmount()` → lines 101, 124
- `_attemptConsistencyRepair()` → lines 176, 177

Total: 4 call sites.

#### 4D. `post_process_splitter.dart` — Add flag parameter

Add `hasEncodingCorruption` to public methods and thread to all call sites:
- `splitMultiItemRows()` → lines 110, 111
- `splitMergedUnitQuantity()` / `extractQuantityAndUnit()` → lines 169, 180, 255
- `handleDetectedPrice()` → lines 318, 323
- `detectAndExtractQuantity()` → line 350
- `applyColumnShift()` → lines 390, 391
- Helper methods → lines 478, 500

Total: 10+ call sites.

#### 4E. `post_process_math_validation.dart` — Add flag parameter

Add `hasEncodingCorruption` to validation methods and thread to line 128.

Total: 1 call site.

#### 4F. `post_process_engine.dart` — Pass flag to all sub-processors

The engine already has `config.hasEncodingCorruption`. Update calls to each sub-processor:

```dart
PostProcessConsistency.applyConsistencyRules(
  items,
  hasEncodingCorruption: config.hasEncodingCorruption,
);

PostProcessSplitter.splitMultiItemRows(
  items,
  hasEncodingCorruption: config.hasEncodingCorruption,
);

// ... same pattern for all sub-processor calls
```

### Complete Call Site Inventory

| File | Method | Lines | Count |
|------|--------|-------|-------|
| `table_row_parser.dart` | `_parseQuantity`, `_parsePrice` | 183, 184, 365, 372, 595, 598 | 6 |
| `post_process_consistency.dart` | `resolveBidAmount`, `_attemptConsistencyRepair` | 101, 124, 176, 177 | 4 |
| `post_process_splitter.dart` | Various methods | 110, 111, 169, 180, 255, 318, 323, 350, 390, 391, 478, 500 | 12 |
| `post_process_math_validation.dart` | `_validateItem` | 128 | 1 |
| **Total** | | | **23** |

---

## Implementation Order

### Phase 1: Image Channel Fix (Part 1)
**Files**: `image_preprocessor.dart`, `tesseract_ocr_engine.dart`, `flusseract.cpp`
**Risk**: Low — adds channel conversion before encoding
**Test**: `pwsh -Command "flutter test test/features/pdf/services/ocr/"`
**Agent**: `backend-data-layer-agent`

### Phase 2: Stop Letter Stripping + Force Re-Parse (Parts 2 + 3)
**Files**: `post_process_normalization.dart`, `post_process_engine.dart`, `post_process_normalization_test.dart`
**Risk**: Medium — changes parse behavior for unrecognized letters
**Test**: `pwsh -Command "flutter test test/features/pdf/table_extraction/post_process/"`
**Agent**: `backend-data-layer-agent`

### Phase 3: Thread Encoding Flag (Part 4)
**Files**: `table_row_parser.dart`, `table_extractor.dart`, `pdf_import_service.dart`, `post_process_consistency.dart`, `post_process_splitter.dart`, `post_process_math_validation.dart`, `post_process_engine.dart`
**Risk**: Medium — many call sites, need to trace caller chains carefully
**Test**: `pwsh -Command "flutter test test/features/pdf/table_extraction/"` then `pwsh -Command "flutter test test/features/pdf/"`
**Agent**: `backend-data-layer-agent`

### Phase 4: Full Verification
```
pwsh -Command "flutter test test/features/pdf/services/ocr/"
pwsh -Command "flutter test test/features/pdf/table_extraction/"
pwsh -Command "flutter test"
```
Manual: Import Springfield PDF — verify page 6 OCR works, pages 2-4 dollar amounts correct.

---

## Complete File Change Matrix

| File | Part | Changes | Risk |
|------|------|---------|------|
| `image_preprocessor.dart` | 1A | Add `convert(numChannels: 1)` in 4 locations | Low |
| `tesseract_ocr_engine.dart` | 1B | Add grayscale + convert in `recognizeRegion()` | Low |
| `flusseract.cpp` | 1C | Add Pix diagnostic logging | Low |
| `post_process_normalization.dart` | 2A | Replace letter stripping with fail-parse | Medium |
| `post_process_normalization_test.dart` | 2B | Update expected test result + test name | Low |
| `post_process_engine.dart` | 3A, 4F | Force re-parse + pass flag to sub-processors | Medium |
| `table_row_parser.dart` | 4A | Thread flag through initial parsing (6 sites) | Medium |
| `table_extractor.dart` | 4B | Thread flag from import service to row parser | Low |
| `pdf_import_service.dart` | 4B | Pass flag to table extractor | Low |
| `post_process_consistency.dart` | 4C | Add flag parameter (4 sites) | Medium |
| `post_process_splitter.dart` | 4D | Add flag parameter (12 sites) | Medium |
| `post_process_math_validation.dart` | 4E | Add flag parameter (1 site) | Low |

**Total files modified**: 12
**Total call sites updated**: ~28
**Test files modified**: 1+ (normalization test; possibly consistency/splitter/engine tests if assertions change)

---

## Encoding Substitution Reference

### Always Active (OCR)
| Char | Maps To | Context |
|------|---------|---------|
| O, o | 0 | Adjacent to digits |
| I, l, L, ! | 1 | Adjacent to digits |
| B, b | 8 | Adjacent to digits |

### Only When `hasEncodingCorruption=true`
| Char | Maps To | Context |
|------|---------|---------|
| z, Z | 7 | Adjacent to digits |
| e (lowercase) | 3 | Adjacent to digits |
| J | 3 | Adjacent to digits |
| ' (apostrophe) | , (comma) | Thousands separator |

### Unmapped (Causes Fail-Parse)
Any letter not in the above maps → returns `''` (both paths after Part 2 fix).
