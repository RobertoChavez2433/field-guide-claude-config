# Defects: PDF

Active patterns for pdf. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [QUALITY] 2026-02-19: Permissive Scorecard Assertions Can Hide Real Extraction Regressions
**Pattern**: Stage trace scorecard assertions allowed degraded outputs (`parsed>=126`, `withAmount>=122`, `bugCount<=2`) to pass, creating false-green confidence while pipeline quality remained below target.
**Prevention**: Keep strict gates aligned to target outcomes (`parsed>=131`, `withAmount>=131`, `bugCount==0`, `lowCount==0`) and treat failures as upstream blockers instead of relaxing assertions.
**Ref**: @test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart:3900-3905

### [QUALITY] 2026-02-18: RowParserV3 Stage Confidence Can Mask High Skip Rates
**Pattern**: `RowParserV3` computes `StageReport.stageConfidence` from confidences of emitted items, while excluded/skipped rows do not reduce that value. A run can report high stage confidence even when many input rows are skipped.
**Prevention**: Include skip/exclusion ratio as a penalty term in stage confidence, or raise warning severity / fail guard when `excludedCount / inputCount` exceeds threshold.
**Ref**: @lib/features/pdf/services/extraction/stages/row_parser_v3.dart:241-279

### [DATA] 2026-02-18: Relaxed/Rescue PriceContinuation Gates Can Misclassify Rows When Item-Number Semantic Is Missing
**Pattern**: Mixed text+price rows can be incorrectly promoted to `priceContinuation` if `itemNumber` semantic is absent from `columnMap` (or unset per-page). In that case `hasItemNumber` is always false, so continuation gates may absorb legitimate base rows into prior items.
**Prevention**: Require `zones.itemNumberColumn != null` before relaxed mixed-text price-continuation gate and boilerplate rescue sweep are allowed. Add explicit test coverage for missing-item-semantic behavior.
**Ref**: @lib/features/pdf/services/extraction/stages/row_classifier_v3.dart:284,376

### [DATA] 2026-02-19: _correctEdgePosForLineDrift Returns Inset in Wrong Coordinate Frame
**Status**: FIXED (Session 381). Drift correction removed, baselineInset updated. Pipe artifacts: 0.
**Ref**: @lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:708-756

### [RESOLVED] 2026-02-19: Tesseract Produced Garbage for Items 64, 74, 75, 77 — Grid Line Fringe + baselineInset Floor
**Status**: FIXED (Session 383). All 4 items recovered. 131/131 GT matched, 0 bogus.
**Root cause (confirmed)**: Two-layer failure:
1. `_scanRefinedInsetAtProbe` had `plannedDepth = w+aa+3 = 6` for width-2 horizontal lines on page 3. Anti-aliased fringe extended exactly 6 dark pixels → scan returned null → fell back to `baselineInset = 3` (insufficient to clear fringe).
2. Line 745 used `baselineInset` as a FLOOR on all scan results, overriding dynamic measurements.
3. Residual fringe pixels, after 2.3x upscaling, became a prominent dark bar. PSM 7 read the bar as "al"/"ot"/"re"/"or" instead of the actual digits above.
**Fix**: Increased `plannedDepth` to `w+aa+5`. Removed `baselineInset` floor (line 745). Scan results now trusted.
**Ref**: @lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:724-744

### [DATA] 2026-02-19: Items 29, 113 bid_amount — Text Touches Grid Line Fringe Zone
**Pattern**: Right vertical lines on pages 1, 4 are width=5 (thickest in document). Bid amount text ($7,026.00, $2,000.00) physically extends into the grid line fringe zone. No pixel-threshold inset can distinguish fringe from content. Diagnostic images show last `0` half-cut.
**Prevention**: OpenCV morphological line removal (`adaptiveThreshold` + `morphologyEx(MORPH_OPEN)`) can erase grid lines by shape without touching adjacent text.
**Status**: Open. Pre-existing (items were empty/null in committed HEAD). OpenCV integration planned for next session.
**Ref**: Diagnostic images `page_1_row_24_col_5_*.png`, `page_4_row_27_col_5_*.png`

### [DATA] 2026-02-16: CropUpscaler numChannels Mismatch Causes Red Background
**Pattern**: `img.Image()` defaults to `numChannels: 3` (RGB). When input crop is 1-channel grayscale (from `convert(numChannels: 1)`), the `image` package reads `.g=0`, `.b=0` from 1-channel pixels, so white (255) becomes `(r=255,g=0,b=0)` = pure red. `compositeImage` with `a=255` replaces destination entirely. Every upscaled cell crop sent to Tesseract had red background.
**Prevention**: Always match `numChannels` when creating canvas images for compositing. Test with 1-channel inputs, not just default 3-channel. Existing tests missed this because they used `img.Image(width:, height:)` which defaults to 3 channels.
**Ref**: @lib/features/pdf/services/extraction/shared/crop_upscaler.dart:71

<!-- Add defects above this line -->
