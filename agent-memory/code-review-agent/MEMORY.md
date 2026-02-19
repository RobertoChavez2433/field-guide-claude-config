# Agent Memory — Code Review Agent

## Patterns Discovered

### Dead Code Accumulation (seen in 4 reviews)
Unused files, methods, and classes accumulate across versions (V1/V2/V3). Entire files like ConcurrencyGateV2, TesseractPoolV2, RowClassifierV2, and 270-line methods like `_recognizeWithRowStrips` survived multiple sessions before detection.
**Caught in**: full-codebase, v2-pipeline, dead-code-prunekit, KISS/DRY
**Prevention**: Run `flutter_prunekit unused_code` periodically. Delete superseded code immediately when new version ships.

### God Classes / God Methods (seen in 3 reviews)
Files exceeding 1,000+ lines recur: entry_wizard_screen (2,610), report_screen (2,761), ColumnDetectorV2 (1,824), PostProcessorV2 (1,472), _runExtractionStages (482-line method).
**Caught in**: full-codebase, v2-pipeline, KISS/DRY
**Prevention**: Flag any file >500 lines or method >100 lines. Decompose into helper/strategy classes proactively.

### Duplicated Test Helpers (seen in 2 reviews)
`_createOcrElement` duplicated 8x, `_createClassifiedRows` 6x, `CoordinateMetadata` boilerplate 12x. `test_fixtures.dart` exists but is under-adopted.
**Caught in**: v2-pipeline, KISS/DRY
**Prevention**: Always check `test/features/pdf/extraction/helpers/test_fixtures.dart` before writing new helpers. Add missing factories there, not inline.

### Duplicated Utility Logic (seen in 2 reviews)
`_median` implemented 4 times (one was buggy for even-length lists), header keyword dicts duplicated in row_classifier and column_detector, regex patterns duplicated 3-4x with inconsistencies.
**Caught in**: v2-pipeline, KISS/DRY
**Prevention**: Check `shared/` directory (math_utils.dart, header_keywords.dart, extraction_patterns.dart) before defining local helpers.

### Pipe Artifact / Whitespace Inset Failures (seen in 4 reviews)
Leading `|` in OCR output caused by grid-line remnants surviving inset trimming. Root cause: first-white termination in non-monotonic edge profiles. Global grid-line centers drift 1-3px from local row centers.
**Caught in**: edgepos-alignment, whitespace-inset-rca, springfield-scorecard, per-line-dynamic-inset
**Prevention**: Width-driven inset with dark-run-then-2-white termination (implemented 2026-02-19). Monitor raw field values for leading `|` in scorecard.

### Tests Validating Deprecated Code (seen in 2 reviews)
Test files importing from `deprecated/` or testing superseded stages. Creates false confidence.
**Caught in**: full-codebase, dead-code-prunekit
**Prevention**: After any version migration, grep test imports for old version references. Delete or retarget immediately.

### Magic Numbers and Strings (seen in 2 reviews)
Quality thresholds (0.85/0.65/0.45) duplicated across 3+ files, hardcoded stage label strings, magic string `springfield-864130`, `totalStages = 13` drifting.
**Caught in**: v2-pipeline, KISS/DRY
**Prevention**: Use QualityThresholds constants, StageNames constants, derive counts from actual data.

### firstWhere Without orElse (seen in 2 reviews)
13+ instances of `.firstWhere()` without `orElse` callback. At least one (post_processor_v2.dart:259) is a production crash risk.
**Caught in**: full-codebase, v2-pipeline
**Prevention**: Always use `.where(...).firstOrNull` pattern. Never bare `.firstWhere()`.

## Gotchas & Quirks

### Non-Monotonic Pixel Edge Profiles
Grid line edges can be white at d=0 then dark at d=1..6. Any scan that breaks on first white pixel will miss the dark run entirely. This is the core whitespace inset failure mode.

### Global Grid Centers Drift Per-Row
Grid line detection collapses vertical lines to page-level centers. True local center varies by row. Mean drift ~1px, P95 ~2.7px, max ~7.5px in Springfield.

### Isolate Code Cannot Import Shared Utils
`grid_line_detector.dart`'s `_median` runs inside a `compute()` isolate and cannot import `MathUtils`. Must inline logic or restructure data passing.

### flutter_prunekit False Positives on Methods
~80% of 577 "unused methods" are false positives (private calls, framework callbacks, Provider getters, barrel exports). Types and variables have much higher accuracy (~97%+).

### PipelineResult.fromMap Lossy Round-Trip
`PipelineResult.fromMap` silently drops documentHash and actual PipelineConfig. Any round-trip through serialization loses context.

### QualityReport.isValid Contradicts QualityValidator
`isValid` getter does not account for the `attemptNumber >= 2` override in `_determineStatus`. Third-attempt reports with 0.50 score are incorrectly marked invalid.

## Architectural Decisions

### Normalized Coordinates Only (0.0-1.0)
All extraction stages work in normalized coordinate space via CoordinateNormalizer. Pixel values must never leak into stage outputs.

### Data-Accounting Assertions
Every stage must satisfy `outputCount + excludedCount == inputCount` in its StageReport. Violations throw StateError immediately. Prevents silent data loss.

### OCR-Only Pipeline (No Hybrid)
DocumentQualityProfiler always returns `ocr` strategy. No native/hybrid code paths. V1/hybrid code belongs in `deprecated/` only. Enforced by pdf-v2-constraints.md.

### No V1/V2 Imports in Active Code
Active pipeline code must not import from `deprecated/` or superseded version files. Tests must test the production version.

### Stage Isolation via Typed I/O
Each pipeline stage receives typed input and produces typed output. No hidden mutable state between stages. Stages are injected into ExtractionPipeline constructor for testability.

### Centralized Domain Constants
Header keywords in `shared/header_keywords.dart`, regex patterns in `shared/extraction_patterns.dart`, quality thresholds in `QualityThresholds`, stage names in `StageNames`. New stages must use these.

## Frequently Referenced Files

| File/Directory | Reviewed In | Notes |
|---------------|-------------|-------|
| `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart` | 5 reviews | Whitespace inset logic, dead _recognizeWithRowStrips, _median dupe |
| `lib/features/pdf/services/extraction/stages/column_detector_v2.dart` | 3 reviews | God class (1824 lines), firstWhere, header keywords dupe |
| `lib/features/pdf/services/extraction/stages/post_processor_v2.dart` | 3 reviews | God class (1472 lines), crash-risk firstWhere |
| `lib/features/pdf/services/extraction/stages/grid_line_detector.dart` | 2 reviews | Global center drift, isolate _median |
| `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` | 3 reviews | God method (482 lines), lossy fromMap |
| `lib/features/pdf/services/extraction/stages/quality_validator.dart` | 2 reviews | Wrong strategy escalation, buggy median |
| `lib/features/pdf/services/extraction/models/quality_report.dart` | 2 reviews | isValid contradicts validator, magic thresholds |
| `lib/features/pdf/services/extraction/stages/row_classifier_v2.dart` | 2 reviews | Entire file dead (V3 active) |
| `lib/features/entries/presentation/screens/entry_wizard_screen.dart` | 1 review | God class (2610 lines), bypasses DI |
| `lib/features/entries/presentation/screens/report_screen.dart` | 1 review | God class (2761 lines), bypasses DI |
| `lib/features/pdf/services/extraction/shared/post_process_utils.dart` | 2 reviews | Dead methods, overlapping artifact cleaning |
| `test/features/pdf/extraction/helpers/test_fixtures.dart` | 2 reviews | Under-adopted; should be single source for test helpers |
| `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart` | 3 reviews | God test (1000+ lines), scorecard driver |
| `test/features/pdf/extraction/fixtures/springfield_parsed_items.json` | 2 reviews | Key fixture for pipe artifact tracking |
| `lib/services/sync_service.dart` | 2 reviews | Legacy, 18+14 duplicate methods, dead SyncResult fields |
| `lib/main.dart` | 1 review | 622 lines, 28-param constructor, service locator anti-pattern |
| `lib/features/pdf/services/extraction/shared/` | 3 reviews | Central shared utils; check here before defining local helpers |
