# Defects: PDF

Active patterns for pdf. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

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

### [CONFIG] 2026-02-14: PSM=6 (Single Block) Destroys Table OCR on Full Pages
**Pattern**: Default `OcrConfigV2(psmMode: 6)` tells Tesseract to treat entire page as one text block, disabling column detection. On table-heavy pages (2-6 of Springfield), reads across all 6 columns producing garbage (`I hc J IAA HS AT IE:`). Also `pageSegMode` getter missing `case 4` — PSM 4 silently falls to default singleBlock.
**Prevention**: Use PSM 7 (singleLine) per row crop for table pages. Use PSM 4 (singleColumn) for non-table pages. Add all PSM cases to the getter. Never use PSM 6 on table-structured content.
**Ref**: @lib/features/pdf/services/extraction/ocr/tesseract_config_v2.dart:75,84-98

### [DATA] 2026-02-15: Region Detector Ignores Grid Line Data — 0 Regions on Grid Pages
**Pattern**: `RegionDetectorV2.detect()` only accepts `ClassifiedRows` and requires `RowType.header` rows to create table regions. Cell-cropped OCR fragments header text ("IB" instead of "Item No.") so row classifier finds 0 headers → 0 regions → 0 items. Grid detector already knows all 6 pages are tables but this data is never passed to the region detector.
**Prevention**: Region detection should use grid line data as a primary signal for table presence. Grid pages with `hasGrid=true` should produce table regions regardless of header row detection. Design options in `plans/2026-02-15-grid-aware-region-detection-design.md`.
**Ref**: @lib/features/pdf/services/extraction/stages/region_detector_v2.dart:41-43,80

<!-- Add defects above this line -->
