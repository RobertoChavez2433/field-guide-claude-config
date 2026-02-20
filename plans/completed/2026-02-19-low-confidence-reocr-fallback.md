# Low-Confidence Re-OCR Fallback for Numeric Columns

**Created**: 2026-02-19 | **Session**: 386
**Status**: Design Complete, Ready for Implementation
**Blocker**: BLOCKER-5 (final fix for last 1 unit_price gap)

## Overview

After the first OCR pass on cell-cropped images in `TextRecognizerV2`, check each cell in **numeric columns** (quantity=col3, unitPrice=col4, bidAmount=col5). If a cell has:
- confidence < 0.5, AND
- text contains NO digit character (0-9)

Then **re-OCR that specific cell crop** with:
- PSM8 (single word mode) instead of PSM7
- Numeric whitelist: `$0123456789,. -`

Replace the original OCR element with the re-OCR'd result only if the new result contains at least one digit.

## Problem Statement

Item #100 (HMA, Approach) has unitPrice OCR'd as `"Si"` (conf=0.46) + `"logo"` (conf=0.31) instead of `$110.00`. Tesseract PSM7 splits the dollar amount into two nonsense fragments:

| Fragment | Confidence | Width | Misread of |
|----------|-----------|-------|------------|
| `Si`     | 0.46      | 33px  | `$1` -> `S` + `i` |
| `logo`   | 0.31      | 94px  | `10.00` -> `l` + `o` + `g` + `o` |

Root cause: right-aligned text in a 354px-wide cell crop (~60% empty whitespace on left). PSM7 breaks word segmentation at the `$1` boundary.

Post-processing currently infers the correct price ($45,100 / 410 = $110) but we want to fix upstream.

## File Changes

### File 1: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`

#### A. Add constants (near other static constants in class)

```dart
/// Numeric column indices for re-OCR eligibility (quantity, unitPrice, bidAmount).
static const Set<int> _numericColumnIndices = {3, 4, 5};

/// Confidence threshold below which re-OCR is considered.
static const double _reOcrConfidenceThreshold = 0.5;

/// Whitelist for numeric re-OCR (dollar sign, digits, comma, period, space, hyphen).
static const String _numericReOcrWhitelist = r'$0123456789,. -';
```

#### B. Add re-OCR counters in `_recognizeWithCellCrops`

```dart
int reOcrAttempts = 0;
int reOcrSuccesses = 0;
```

#### C. Update return record type of `_recognizeWithCellCrops`

Add `reOcrAttempts` and `reOcrSuccesses` fields. Update ALL return statements (including early returns) to include these new fields with value 0 for early returns.

#### D. Insert re-OCR logic

**Location**: After the coordinate-mapping loop that produces `pageMapped` elements, BEFORE `pageElements.addAll(pageMapped)`.

Change `pageMapped` from `final` to `var`.

```dart
// === Low-confidence re-OCR for numeric columns ===
if (_numericColumnIndices.contains(cell.columnIndex) &&
    cell.rowIndex > 0) {
  final shouldReOcr = pageMapped.isNotEmpty &&
      pageMapped.every((e) =>
          e.confidence < _reOcrConfidenceThreshold &&
          !e.text.contains(RegExp(r'[0-9]')));

  if (shouldReOcr) {
    reOcrAttempts++;
    try {
      final reOcrConfig = baseConfig.copyWith(
        psmMode: 8,
        whitelist: _numericReOcrWhitelist,
      );
      final reOcrElements = await engine.recognizeCrop(
        cropBytes: cropBytes,
        width: preparedCrop.image.width,
        height: preparedCrop.image.height,
        pageIndex: pageIndex,
        cropRegionNormalized: cellBounds,
        renderSize: renderSize,
        pageSize: pageSize,
        config: reOcrConfig,
      );

      final reOcrText = reOcrElements.map((e) => e.text).join(' ');
      final hasDigit = reOcrText.contains(RegExp(r'[0-9]'));

      if (hasDigit && reOcrElements.isNotEmpty) {
        // Re-map re-OCR elements to page coordinates
        final reOcrMapped = <OcrElement>[];
        for (final element in reOcrElements) {
          final preparedCropPixelBounds = CoordinateNormalizer.toPixels(
            normalizedBounds: element.boundingBox,
            renderSizePixels: ocrCropSizePixels,
          );
          final cropRelativePixelBounds = _mapPreparedCropBoundsToOriginal(
            preparedCropPixelBounds: preparedCropPixelBounds,
            originalCropWidth: cropWidth.toDouble(),
            originalCropHeight: cropHeight.toDouble(),
            scaleFactor: preparedCrop.scaleFactor,
            paddingPixels: preparedCrop.paddingPixels.toDouble(),
          );
          if (cropRelativePixelBounds.width <= 0 ||
              cropRelativePixelBounds.height <= 0) {
            continue;
          }
          final pageBounds = CoordinateNormalizer.fromCropRelative(
            elementInCrop: cropRelativePixelBounds,
            cropSizePixels: originalCropSizePixels,
            cropRegionNormalized: cellBounds,
          );
          reOcrMapped.add(element.copyWith(boundingBox: pageBounds));
        }

        if (reOcrMapped.isNotEmpty) {
          pageMapped = reOcrMapped;
          reOcrSuccesses++;
        }
      }
    } catch (e) {
      warnings.add(
        'Page ${pageIndex + 1}: Cell (row ${cell.rowIndex + 1}, '
        'col ${cell.columnIndex + 1}) re-OCR failed: $e',
      );
    }
  }
}
```

#### E. Propagate metrics in `recognize` method

Add `reOcrAttempts` and `reOcrSuccesses` accumulators, accumulate from `cropResult`, include in StageReport metrics map.

### File 2: `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart`

**CRITICAL**: Fix per-call whitelist application to prevent leakage.

In `recognizeCrop` (and `recognizeImage`), after `tess.setPageSegMode(cfg.pageSegMode)`, add:

```dart
// Apply or clear whitelist per call to prevent leakage between calls
if (cfg.whitelist != null && cfg.whitelist!.isNotEmpty) {
  tess.setWhiteList(cfg.whitelist!);
} else {
  tess.setWhiteList('');
}
```

### File 3: `tesseract_config_v2.dart` — No changes needed

PSM 8 already mapped to `PageSegMode.singleWord`. `whitelist` field and `copyWith` already exist.

## Test Plan

### New test group in `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart`

Group: `'low-confidence numeric re-OCR'`

| # | Test | Verifies |
|---|------|----------|
| 1 | re-OCRs numeric column cell when conf < 0.5 and no digits | Happy path: PSM8 + whitelist used on retry |
| 2 | skips re-OCR for non-numeric column cells (e.g. col 1 description) | Column guard works |
| 3 | skips re-OCR when confidence >= 0.5 | Threshold guard works |
| 4 | skips re-OCR when text contains digits | Digit guard works |
| 5 | keeps original result when re-OCR produces no digits | Fallback safety |
| 6 | replaces original result when re-OCR produces digits | Replacement logic |
| 7 | tracks reOcrAttempts and reOcrSuccesses in report metrics | Metrics propagation |
| 8 | skips re-OCR for header row (rowIndex == 0) | Header exclusion |

Mock strategy: `MockOcrEngine` captures `RecognizeCropCall` with config — tests can inspect `call.config.psmMode` and `call.config.whitelist`. The `cropElementProvider` checks config to distinguish initial vs re-OCR calls.

## Edge Cases and Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Whitelist persistence across Tesseract calls | High — would corrupt all subsequent OCR | File 2 fix clears whitelist on every call |
| Performance (~50-100ms per re-OCR) | Low — only ~1-3 cells per document trigger | Narrow conditions (conf<0.5 AND no digits) |
| PSM8 on multi-fragment cell | Low — original has multiple elements | `every()` requires ALL fragments to fail |
| Empty re-OCR result | None — guarded | `hasDigit && reOcrElements.isNotEmpty` check |
| Header row false trigger | None — guarded | `cell.rowIndex > 0` condition |
| Non-bid-schedule PDFs with different column counts | Low | Cell-level OCR only fires on grid-detected PDFs |

## Expected Outcome

- Item #100 unitPrice: `"Si"` -> `"$110.00"` at Stage 4D (cell grid level)
- Post-processing price inference no longer needed for item #100
- Scorecard: 55 OK / 0 LOW / 0 BUG maintained
- unit_price: 130/131 -> 131/131 at Stage 4E (before post-processing)
- Quality score: 0.993 -> potentially higher (one fewer repair needed)

## Validation Steps

1. Run `pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart"` — all tests pass including new group
2. Run `pwsh -Command "flutter test test/features/pdf/extraction/"` — full extraction suite green
3. Regenerate Springfield fixtures and confirm item #100 unitPrice reads `$110.00` at cell grid level
4. Run stage trace diagnostic — confirm 131/131 unit_price at Stage 4E (no post-processing inference needed)
