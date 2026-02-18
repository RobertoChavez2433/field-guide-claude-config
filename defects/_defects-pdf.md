# Defects: PDF

Active patterns for pdf. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [DATA] 2026-02-17: Anti-Aliased Grid Line Fringes Survive Crop Insets — 155 Pipe Artifacts
**Pattern**: `(lineWidth/2).ceil()+1` crop inset only covers the "dark core" (pixels < 128) of grid lines. Anti-aliased fringes at ~130-170 pixel values extend 1-2px beyond measured width. CropUpscaler magnifies these fringes up to 4x. Tesseract reads them as `|` with high confidence (avg 0.88). 155 of 162 pipe elements match vertical grid line X positions (95.7%). These pipes map to text-semantic columns, blocking V3 price continuation detection (`textPopulated.isEmpty` fails).
**Prevention**: Use adaptive whitespace-scan insets instead of formula-based: scan from grid line center until pixel.r >= 230 (true white), cap at 5px. Sample at 3 positions per edge, take max. Implement in `text_recognizer_v2.dart:348-367`.
**Ref**: @lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:348-367

### [DATA] 2026-02-16: CropUpscaler numChannels Mismatch Causes Red Background
**Pattern**: `img.Image()` defaults to `numChannels: 3` (RGB). When input crop is 1-channel grayscale (from `convert(numChannels: 1)`), the `image` package reads `.g=0`, `.b=0` from 1-channel pixels, so white (255) becomes `(r=255,g=0,b=0)` = pure red. `compositeImage` with `a=255` replaces destination entirely. Every upscaled cell crop sent to Tesseract had red background.
**Prevention**: Always match `numChannels` when creating canvas images for compositing. Test with 1-channel inputs, not just default 3-channel. Existing tests missed this because they used `img.Image(width:, height:)` which defaults to 3 channels.
**Ref**: @lib/features/pdf/services/extraction/shared/crop_upscaler.dart:71

### [DATA] 2026-02-15: ColumnDef.copyWith Cannot Set headerText to Null
**Pattern**: `copyWith(headerText: null)` uses `headerText ?? this.headerText`, so null is indistinguishable from "not provided". Validation that needs to revert a semantic to null silently keeps the old value.
**Prevention**: Use sentinel pattern (`Object? headerText = _sentinel`) in copyWith for nullable fields. Test that `copyWith(headerText: null)` actually produces null.
**Ref**: @lib/features/pdf/services/extraction/models/column_map.dart:28-40

### [DATA] 2026-02-15: Blind Position Fallback Maps Margins as Data Columns
**Pattern**: `_mapColumnSemantics` in row_parser used `standardOrder[i]` fallback when headerText is null, mapping narrow margin columns (5.3% width page-edge gutters) as 'itemNumber'. Grid creates 8 columns from 7 lines but 2 are margins.
**Prevention**: Never use position-based semantic guessing. Column detector should provide all semantics via header OCR + anchor-relative inference + content validation. Row parser should skip null-header columns.
**Ref**: @lib/features/pdf/services/extraction/stages/row_parser_v2.dart:400-418

### [DATA] 2026-02-15: img.getLuminance() Fails on 1-Channel Images
**Pattern**: `img.getLuminance(pixel)` computes `0.299*r + 0.587*g + 0.114*b`. On 1-channel images (from `convert(numChannels: 1)`), `pixel.g=0` and `pixel.b=0`, so white pixel (255) returns luminance 76 — below 128 "dark" threshold. Every pixel appears dark.
**Prevention**: Use `pixel.r` directly for single-channel images, not `getLuminance()`. Always verify pixel reading functions handle single-channel images from the `image` package.
**Ref**: @lib/features/pdf/services/extraction/stages/grid_line_detector.dart:224-229

<!-- Add defects above this line -->
