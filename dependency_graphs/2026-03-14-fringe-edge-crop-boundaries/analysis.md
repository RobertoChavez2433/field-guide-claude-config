# Dependency Graph: Fringe-Edge Crop Boundaries

## Data Flow (Current)
```
GridLineDetector.detect() → GridLines (position + widthPixels only)
        ↓
GridLineRemover.remove(gridLines) → (cleanedPages, StageReport)
  └── _removeGridLines() internally:
      └── _clusterAndCrossRef() → _MergeResult (lines[] with implicit bestDetIdx)
      └── _measureLineFringe() → fringeResults[] parallel to allLines
      └── Pass 2: uses fringe for mask expansion, then DISCARDS
      └── Returns _GridRemovalResult (aggregate fringe stats only)
  └── GridLines input passes through UNTOUCHED
        ↓
Pipeline: _buildGridLinesForOcr(gridLines, report) → ocrGridLines (no fringe)
        ↓
TextRecognizerV2.recognize(gridLines: ocrGridLines)
  └── _computeCellCrops(sortedH, sortedV) → uses GridLine.position only
```

## Data Flow (Target)
```
GridLineRemover.remove(gridLines) → (cleanedPages, StageReport, enrichedGridLines)
  └── _removeGridLines() returns per-detector-line fringe via _GridRemovalResult
  └── remove() builds new GridLine objects with fringeSide1/fringeSide2
        ↓
Pipeline uses enrichedGridLines → TextRecognizerV2
  └── _computeCellCrops insets by (halfWidth + fringe + 1) / imageDim
```

## Direct Changes

| File | Symbol | Lines | Change |
|------|--------|-------|--------|
| `lib/.../models/grid_lines.dart` | `GridLine` | 6-16 | Add fringeSide1, fringeSide2 fields |
| `lib/.../models/grid_lines.dart` | `GridLineResult.toMap` | 57-69 | Serialize fringe arrays |
| `lib/.../models/grid_lines.dart` | `GridLineResult.fromMap` | 73-108 | Parse fringe arrays (default 0) |
| `lib/.../stages/grid_line_remover.dart` | `_MergedLine` | 807-811 | Add detectorIndex field |
| `lib/.../stages/grid_line_remover.dart` | `_MergeResult` | 929-935 | Add detectorIndices list |
| `lib/.../stages/grid_line_remover.dart` | `_clusterAndCrossRef` | 944-1096 | Track bestDetIdx per line |
| `lib/.../stages/grid_line_remover.dart` | `_fallbackLines` | 1104+ | Track detector indices for fallbacks |
| `lib/.../stages/grid_line_remover.dart` | `_GridRemovalResult` | 277-338 | Add perLineFringe maps |
| `lib/.../stages/grid_line_remover.dart` | `_removeGridLines` | 353-785 | Build fringe map after Pass 2 |
| `lib/.../stages/grid_line_remover.dart` | `GridLineRemover.remove` | 57-272 | Return enriched GridLines (3-tuple) |
| `lib/.../pipeline/extraction_pipeline.dart` | `_runExtractionStages` | 494-498 | Capture 3rd return value |
| `lib/.../pipeline/extraction_pipeline.dart` | `_buildGridLinesForOcr` | 763-798 | Accept enriched GridLines |
| `lib/.../stages/text_recognizer_v2.dart` | `_computeCellCrops` | 1175-1219 | Add imageDim params, apply fringe insets |
| `lib/.../stages/text_recognizer_v2.dart` | `_recognizeWithCellCrops` | 430-433 | Pass image dimensions |

## Dependent Files (callers/consumers)

| File | Dependency |
|------|-----------|
| `lib/.../pipeline/extraction_pipeline.dart` | Calls `gridLineRemover.remove()` — must update destructuring |
| `test/.../stages/grid_line_remover_test.dart` | Tests `GridLineRemover` — must update for 3-tuple return |
| `test/.../contracts/stage_2b6_to_2biii_contract_test.dart` | Contract test — must verify fringe data flows |
| `test/.../stages/stage_2b_text_recognizer_test.dart` | Tests `_computeCellCrops` indirectly — must verify insets |

## Test Files

| File | What to Update |
|------|---------------|
| `test/.../stages/stage_2b_grid_line_detector_test.dart` | GridLineResult toMap/fromMap round-trips with fringe |
| `test/.../stages/grid_line_remover_test.dart` | Return type change, fringe data assertions |
| `test/.../contracts/stage_2b6_to_2biii_contract_test.dart` | Fringe carried through contract |
| `test/.../stages/stage_2b_text_recognizer_test.dart` | Crop bounds inset verification |
| `test/.../helpers/test_fixtures.dart` | `gl()` helper — add fringe params |
| `test/.../helpers/mock_stages.dart` | Mock GridLineRemover return type |

## Blast Radius Summary
- **Direct**: 4 source files (grid_lines.dart, grid_line_remover.dart, extraction_pipeline.dart, text_recognizer_v2.dart)
- **Dependent**: 1 file (extraction_pipeline.dart also consumer)
- **Tests**: 6 test files
- **Cleanup**: 0 (no dead code)
- **Column detection**: UNCHANGED (uses position for semantics, not crops)
