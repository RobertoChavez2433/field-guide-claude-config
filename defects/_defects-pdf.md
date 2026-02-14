# Defects: PDF

Active patterns for pdf. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [CONFIG] 2026-02-14: PSM=6 (Single Block) Destroys Table OCR on Full Pages
**Pattern**: Default `OcrConfigV2(psmMode: 6)` tells Tesseract to treat entire page as one text block, disabling column detection. On table-heavy pages (2-6 of Springfield), reads across all 6 columns producing garbage (`I hc J IAA HS AT IE:`). Also `pageSegMode` getter missing `case 4` — PSM 4 silently falls to default singleBlock.
**Prevention**: Use PSM 7 (singleLine) per row crop for table pages. Use PSM 4 (singleColumn) for non-table pages. Add all PSM cases to the getter. Never use PSM 6 on table-structured content.
**Ref**: @lib/features/pdf/services/extraction/ocr/tesseract_config_v2.dart:75,84-98

### [DATA] 2026-02-14: ResultConverter Uses Substring Matching Instead of StageNames Constants
**Pattern**: `ResultConverter` checked `stageName.contains('page_renderer')` which didn't match the actual `StageNames.pageRendering` value (`page_rendering`). OCR detection silently broken for V2 pipeline.
**Prevention**: Always use `StageNames.*` constants for stage name comparisons. Never use substring/contains matching on stage names.
**Ref**: @lib/features/pdf/services/extraction/pipeline/result_converter.dart

### [DATA] 2026-02-14: QualityReport.isValid Rejects Valid Attempt-Exhausted Reports
**Pattern**: `isValid` used hardcoded score-to-status mapping without considering `reExtractionAttempts`. Score 0.55 at attempt 2 should be `partialResult` (not `reExtract`), but `isValid` always expected `reExtract` for 0.45-0.64 range.
**Prevention**: Centralize threshold logic in `QualityThresholds.statusForScore()` — never duplicate score-to-status mapping inline.
**Ref**: @lib/features/pdf/services/extraction/shared/quality_thresholds.dart

### [DATA] 2026-02-14: Divergent Threshold Constants Across 4 Files
**Pattern**: Score thresholds 0.85/0.65/0.45 were hardcoded independently in `quality_report.dart`, `quality_validator.dart`, `extraction_metrics.dart`, and pipeline exit logic. Changes to one file didn't propagate.
**Prevention**: Use `QualityThresholds.*` constants as single source of truth for all threshold comparisons.
**Ref**: @lib/features/pdf/services/extraction/shared/quality_thresholds.dart

### [DATA] 2026-02-06: Empty Uint8List Passes Null Guards But Crashes img.decodeImage()
**Pattern**: Native text path creates `Uint8List(0)` per page. Code checks `if (bytes == null)` but empty list is not null — `img.decodeImage()` throws RangeError on empty bytes instead of returning null.
**Prevention**: Always check `bytes == null || bytes.isEmpty` before passing to image decoders
**Ref**: @lib/features/pdf/services/table_extraction/cell_extractor.dart:761, :920

<!-- Add defects above this line -->
