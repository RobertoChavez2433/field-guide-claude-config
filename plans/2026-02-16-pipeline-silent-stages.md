# Pipeline Audit: Add Silent Stage Fixtures

## Context

The pipeline audit identified 6 silent/semi-silent stages where data transforms but isn't captured in fixtures. Currently 14 stages emit fixture data; we need to add capture points for coordinate clamping, row pathway routing, column detection layer scores, orphan elements, and post-processing sub-phases — so every transformation is visible in one place.

The user also wants:
- Clean sequential numbering (1-23) replacing the current 0/2B/4A mess
- At least 3 GT trace items from the 114-131 range

## Chronological Stage Numbering (1-23)

Replace the old naming scheme with clean sequential numbers in the scorecard/trace test display:

| # | Stage Name Constant | Display Label | Fixture | Status |
|---|---------------------|--------------|---------|--------|
| 1 | `documentAnalysis` | Document Analysis | `springfield_document_profile.json` | EXISTS |
| 2 | `pageRendering` | Page Rendering | `springfield_rendering_metadata.json` | EXISTS |
| 3 | `imagePreprocessing` | Image Preprocessing | `springfield_preprocessing_stats.json` | EXISTS |
| 4 | `gridLineDetection` | Grid Line Detection | `springfield_grid_lines.json` | EXISTS |
| 5 | `textRecognition` | Text Recognition | `springfield_ocr_metrics.json` | EXISTS |
| 6 | `elementValidation` | Element Validation | `springfield_unified_elements.json` | EXISTS |
| 7 | `elementClamping` | Element Clamping | `springfield_element_clamping.json` | **NEW** |
| 8 | `rowClassification` | Row Classification | `springfield_classified_rows.json` | EXISTS |
| 9 | `regionDetection` | Region Detection | `springfield_detected_regions.json` | EXISTS |
| 10 | `rowPathways` | Row Pathways | `springfield_row_pathways.json` | **NEW** |
| 11 | `columnDetection` | Column Detection | `springfield_column_map.json` | EXISTS |
| 12 | `columnDetectionLayers` | Column Detection Layers | `springfield_column_detection_layers.json` | **NEW** |
| 13 | `postColumnRefinement` | Post-Column Refinement | `springfield_phase1b_refinement.json` | EXISTS |
| 14 | `cellExtraction` | Cell Extraction | `springfield_cell_grid.json` | EXISTS |
| 15 | `orphanElements` | Orphan Elements | `springfield_orphan_elements.json` | **NEW** |
| 16 | `rowParsing` | Row Parsing | `springfield_parsed_items.json` | EXISTS |
| 17 | `postNormalize` | Post-Process: Normalize | `springfield_post_normalize.json` | **NEW** |
| 18 | `postSplit` | Post-Process: Split | `springfield_post_split.json` | **NEW** |
| 19 | `postValidate` | Post-Process: Validate | `springfield_post_validate.json` | **NEW** |
| 20 | `postSequenceCorrect` | Post-Process: Sequence | `springfield_post_sequence_correct.json` | **NEW** |
| 21 | `postDeduplicate` | Post-Process: Deduplicate | `springfield_post_deduplicate.json` | **NEW** |
| 22 | `postProcessing` | Post-Processing (Final) | `springfield_processed_items.json` | EXISTS |
| 23 | `qualityValidation` | Quality Validation | `springfield_quality_report.json` | EXISTS |

Internal `StageNames` constants stay the same (they're identifiers, not display labels). The clean numbering is used in the **scorecard and trace test display only** via a display order map.

## Files to Modify

### 1. `lib/features/pdf/services/extraction/stages/stage_names.dart`
Add 9 new constants: `elementClamping`, `rowPathways`, `columnDetectionLayers`, `orphanElements`, `postNormalize`, `postSplit`, `postValidate`, `postSequenceCorrect`, `postDeduplicate`.

### 2. `lib/features/pdf/services/extraction/stages/element_validator.dart`
- Track clamped elements in a diagnostic list during validation
- Return `(result, report, clampingDiagnostics)` — expand tuple to include a `Map<String, dynamic>`
- Clamping data: `{total_clamped, clamped_elements: [{text, page_index, original_bbox, clamped_bbox}]}`

### 3. `lib/features/pdf/services/extraction/stages/region_detector_v2.dart`
- Track pathway decisions for every row during detection
- Return `(result, report, pathwayDiagnostics)` — expand tuple
- Pathway data: `{total_rows, decisions: [{row_index, page_index, type, decision, reason}]}`

### 4. `lib/features/pdf/services/extraction/stages/column_detector_v2.dart`
- Track each layer's result (method, confidence, columns found, whether selected)
- Return `(result, report, layerDiagnostics)` — expand tuple
- Layer data: `{layers_attempted: [{layer, method, confidence, columns_found, selected}]}`

### 5. `lib/features/pdf/services/extraction/stages/post_processor_v2.dart`
- Accept `onStageOutput` callback parameter
- Emit intermediate snapshots after each sub-phase:
  - **post_normalize**: Items after per-item normalization
  - **post_split**: Items after splitting expansion
  - **post_validate**: Items after consistency rules
  - **post_sequence_correct**: Items after sequence-based corrections
  - **post_deduplicate**: Items after deduplication

### 6. `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`
- After Stage 6/element_validation: emit `elementClamping` from diagnostics
- After Stage 9/region_detection: emit `rowPathways` from diagnostics
- After Stage 11/column_detection: emit `columnDetectionLayers` from diagnostics
- After Stage 14/cell_extraction: emit `orphanElements` extracted from CellGrid
- Pass `onStageOutput` into PostProcessorV2 for sub-phase emissions

### 7. `integration_test/generate_golden_fixtures_test.dart`
- Add 9 new entries to `stageToFilename` map

### 8. `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`
- Load 9 new fixture files in setUpAll (with graceful null handling)
- Add test cases for each new stage in "Stage-by-Stage Pipeline Trace" group
- Refactor scorecard to use clean 1-23 numbering
- Add scorecard rows for the 9 new stages
- Add GT trace items: #115, #120, #125, #131

## Implementation Approach

### Stage Return Types
Expand the tuple return type from `(Output, StageReport)` to `(Output, StageReport, Map<String, dynamic>)` for stages 3, 4B, 4C. The third element is the diagnostic map.

### Orphan Elements (Stage 4D)
No stage code changes needed. Pipeline extracts from CellGrid:
```dart
onStageOutput?.call(StageNames.orphanElements, {
  'orphans': cellGrid.orphans.map((o) => o.toMap()).toList(),
  'total_orphans': cellGrid.orphans.length,
});
```

### Post-Processing Sub-phases
Pass callback into PostProcessorV2 (same pattern as TextRecognizerV2 with onDiagnosticImage):
```dart
final postResult = postProcessor.process(
  parsedItems,
  context,
  onStageOutput: onStageOutput,
);
```

### Display Order Map (in trace test)
```dart
const stageDisplayOrder = {
  StageNames.documentAnalysis: (1, 'Document Analysis'),
  StageNames.pageRendering: (2, 'Page Rendering'),
  // ... through ...
  StageNames.qualityValidation: (23, 'Quality Validation'),
};
```

## GT Trace Items

Current: `['1', '3', '5', '10', '50', '100']`
New: `['1', '3', '5', '10', '50', '100', '115', '120', '125', '131']`

## Verification

1. `pwsh -Command "flutter test test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart"` — passes
2. Scorecard displays stages 1-23 in order
3. GT traces include items 115, 120, 125, 131
4. New fixture files in `stageToFilename` map
5. Missing fixtures handled gracefully (skip pattern)

## Execution Order

1. `stage_names.dart` — add 9 new constants
2. `element_validator.dart` — expand return tuple with clamping diagnostics
3. `region_detector_v2.dart` — expand return tuple with pathway decisions
4. `column_detector_v2.dart` — expand return tuple with layer results
5. `post_processor_v2.dart` — accept onStageOutput callback, emit sub-phase snapshots
6. `extraction_pipeline.dart` — wire up all new emissions, handle expanded tuples
7. `generate_golden_fixtures_test.dart` — add 9 entries to stageToFilename
8. `stage_trace_diagnostic_test.dart` — load fixtures, add tests, update scorecard with 1-23 numbering, add GT items
