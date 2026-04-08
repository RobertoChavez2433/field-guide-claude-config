# PDF Extraction Stage Standardization Plan

Date: 2026-04-05
Owner: Codex
Status: Completed

## Goal

Bring the PDF extraction system to one consistent stage architecture:

- each stage has one clear job
- each meaningful boundary can emit a traceable output snapshot
- stage names are explicit and stable
- stage registry/report/fixture generation all use the same contract
- retry/caching logic does not hide data flow
- tests can verify stage outputs without running the app

## What Is Already Standardized

- Stage registry, stage definitions, stage trace sink, and trace snapshots exist.
- OCR recognition is split into traced sub-stages:
  - `ocr_cell_crop_planning`
  - `ocr_crop_preparation`
  - `ocr_cell_recognition`
  - `ocr_retry_resolution`
  - `ocr_coordinate_mapping`
- Post-processing is split into traced sub-stages:
  - `post_normalize`
  - `post_split`
  - `post_validate`
  - `post_sequence_correct`
  - `post_deduplicate`
  - `post_math_validation`
  - `post_checksum`
  - `post_field_confidence`
- M&P extraction has real staged boundaries for quality gate, page text assembly, parsing, matching, and summary.
- OCR preparation caching exists and preserves trace visibility.
- Provisional row classification is a named pipeline stage.
- Final row classification is now decomposed into:
  - `row_grouping`
  - `row_feature_extraction`
  - `row_semantic_classification`
  - `row_rescue_adjustment`
- OCR engine results now carry structured HOCR diagnostics and warnings so
  parser failures no longer collapse to silent empty output.

## Standardization Rules For Remaining Work

- Every stage should either:
  - perform one transformation, or
  - act as a thin orchestrator over explicit sub-stages.
- If a stage can “repair”, “rescue”, “fallback”, or “re-score” data, that logic must be visible as its own stage or sub-stage output.
- If a stage can drop or exclude data, that decision must be represented in trace output.
- If a stage uses page-aware or region-aware heuristics, those decisions must be inspectable in stage diagnostics.
- Legacy numbered or opaque naming is not allowed in end-state trace/test/report output.

## Remaining Refactor TODO

### 1. Row classification breakdown

- [x] Split `row_classifier_v3.dart` into explicit sub-stages under the shared trace contract.
- [x] Add `row_grouping` stage so row boundaries are observable independently of row semantics.
- [x] Add `row_feature_extraction` stage so per-row signals are visible before classification.
- [x] Add `row_semantic_classification` stage so rule decisions are isolated from grouping and rescue.
- [x] Add `row_rescue_adjustment` stage so rescue/recovery logic no longer happens invisibly inside classification.
- [x] Keep `row_classification` as the final aggregate stage output for downstream compatibility.
- [x] Ensure final pipeline classification emits the new row sub-stage outputs without colliding with provisional classification traces.
- [x] Add row-level decision reasons to trace output so regressions can be debugged without reading code.
- [x] Preserve data-accounting guarantees from OCR elements to classified rows.

### 2. Grid cleanup breakdown

- [x] Finish splitting `grid_line_remover.dart` from “structured internals” into real components or stage-like units.
- [x] Expose grid-mask construction decisions in trace output, not only final cleaned images.
- [x] Trace which pages used passthrough, inpaint, or failed passthrough fallback.
- [x] Add tests for fringe/crop interactions so grid-line metadata is not silently mismatched between OCR prep and OCR recognition.

### 3. Column detection breakdown

- [x] Split `column_detector_v2.dart` into explicit stages or components:
  - grid-seeded detection
  - header-based detection
  - text-alignment detection
  - whitespace-gap detection
  - missing-column inference
- [x] Promote current layer diagnostics to first-class trace outputs instead of one mixed blob.
- [x] Preserve page-aware column maps and make page adjustments explicit in trace output.
- [x] Add regression coverage for pages that mix grid and non-grid behavior.

### 4. Region detection breakdown

- [x] Split `region_detector_v2.dart` into explicit responsibilities:
  - header candidate evaluation
  - header pairing/continuation
  - table span resolution
  - orphan/excluded row handling
- [x] Make row pathway and exclusion decisions fully visible in trace output.
- [x] Add tests for page-bottom header suppression and cross-page continuation decisions.

### 5. Cell extraction breakdown

- [x] Split `cell_extractor_v2.dart` into explicit steps:
  - candidate row selection
  - region eligibility filtering
  - column assignment
  - per-cell fragment merge
  - row-level cell materialization
- [x] Trace element-to-column assignment decisions, including fallback assignment paths.
- [x] Make excluded rows and skipped row types inspectable as structured stage output.
- [x] Add tests for ambiguous boundary assignment and region-header handling.

### 6. Quality validation breakdown

- [x] Split `quality_validator.dart` into explicit score calculators or validation sub-stages:
  - completeness
  - coherence
  - math score
  - confidence distribution
  - structural score
  - checksum score
  - final status selection
- [x] Emit each score contribution independently in the trace/report surface.
- [x] Add coverage proving retry strategy selection is explainable from stage outputs.

### 7. Extraction pipeline orchestration cleanup

- [x] Reduce `extraction_pipeline.dart` to orchestration only.
- [x] Extract the repeated “run stage, add report, emit trace, send progress” pattern into reusable helpers.
- [x] Make provisional and final classification/header-consolidation flows easier to follow by isolating them behind named runner methods.
- [x] Make retry selection, cache reuse, and attempt comparison easier to inspect in the trace.
- [x] Add clear separation between per-attempt artifacts and best-attempt artifacts.

### 8. OCR engine silent-failure cleanup

- [x] Audit `tesseract_engine_v2.dart` for HOCR parse failures and empty-output fallbacks that still collapse too quietly.
- [x] Record parser-failure provenance as structured diagnostics, not only warnings/logs.
- [x] Add tests for timeout fallback and partially parsed page output.

### 9. Naming cleanup

- [x] Remove remaining opaque contract/test names that still imply old numbered-stage terminology.
- [x] Ensure fixture/report filenames align with explicit stage ids.
- [x] Preserve compatibility aliases only where tooling still needs them, and document each alias.

### 10. Stage trace and fixture completeness

- [x] Audit every extraction stage for a canonical `StageNames` id and `StageRegistry` definition.
- [x] Ensure every new sub-stage has a fixture filename and report display name where appropriate.
- [x] Update Springfield report generation to surface new sub-stages where they add debugging value.
- [x] Update comparison tooling to prefer canonical stage ids and only fall back to aliases when necessary.

### 11. Test coverage gaps

- [x] Add row-classification sub-stage tests and pipeline trace assertions.
- [x] Add column-detection layer stage tests once that split lands.
- [x] Add region-detection pathway and exclusion diagnostics tests.
- [x] Add cell-extraction assignment provenance tests.
- [x] Add quality-validation score-breakdown tests.
- [x] Add characterization tests for known issue classes:
  - dormant isolate/rendering constraints
  - ordinal/superscript OCR degradation
  - edge-glyph and descender loss
- [x] Keep stage-trace contract tests updated whenever a stage is renamed, split, or gains new required artifacts.

### 12. Performance and data-flow verification

- [x] Add per-sub-stage timing visibility anywhere a former god stage is split.
- [x] Verify cache boundaries do not hide stale data or cross-attempt contamination.
- [x] Verify no stage silently drops rows, elements, or items between boundaries.
- [x] Add comparison helpers for pre/post counts at row, cell, and item boundaries.

## Scoped Remaining Worklist

No in-scope refactor items remain open on this branch.

Archived report compatibility is intentionally preserved in read/fallback paths
only:

- `test/features/pdf/extraction/helpers/report_generator.dart`
- `tools/pipeline_comparator.dart`

Those shims exist only so older generated reports can still be compared or
read. New runtime/test output uses canonical stage ids.

## Completion Notes

- `ExtractionPipeline` is now an orchestrator over named helper segments rather
  than one long policy-bearing method.
- Former god stages now either have extracted sub-stage classes or are thin
  orchestrators over those classes.
- Grid cleanup sub-stages and the grid-page OCR branch now have direct stage
  tests, not only integration coverage.
- Count-flow, cache-key isolation, timing visibility, and characterization
  coverage are all present in the focused extraction suite.

## Definition Of Done

- All major former god stages are either decomposed or reduced to thin orchestrators.
- Every meaningful transformation boundary has a stable stage id, trace output, and tests.
- Stage trace tests, report generation, and fixture generation all run against the same canonical stage registry.
- Failure, fallback, rescue, and exclusion paths are visible in structured outputs.
- The remaining extraction pipeline can be debugged from stage outputs without relying on app-only repros or log spelunking.
