# Dependency Graph: Dynamic Fringe Removal

## Direct Changes

| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/features/pdf/services/extraction/stages/grid_line_remover.dart` | `_removeGridLines()` | 298-613 | MODIFY — add fringe measurement + mask expansion after line drawing, before inpainting |
| `lib/features/pdf/services/extraction/stages/grid_line_remover.dart` | `_GridRemovalResult` | 241-283 | MODIFY — add 5 new fields: horizontalMaskPixels, verticalMaskPixels, fringePixelsAdded, avgFringeWidthH, avgFringeWidthV |
| `lib/features/pdf/services/extraction/stages/grid_line_remover.dart` | (new function) | — | CREATE — `_measureLineFringe()` helper function |
| `test/features/pdf/extraction/helpers/test_fixtures.dart` | `createSyntheticGridImage()` | 291-340 | REFERENCE — existing helper draws binary lines only |
| `test/features/pdf/extraction/helpers/test_fixtures.dart` | (new function) | — | CREATE — `createAntiAliasedGridImage()` helper |

## Dependent Files (callers/consumers)

| File | How It Uses GridLineRemover | Impact |
|------|---------------------------|--------|
| `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart:494` | Calls `gridLineRemover.remove()` | NO CHANGE — public API unchanged |
| `test/features/pdf/extraction/helpers/mock_stages.dart:158` | `MockGridLineRemover extends GridLineRemover` | NO CHANGE — mock overrides `remove()`, doesn't touch `_removeGridLines()` |
| `test/features/pdf/extraction/contracts/stage_2b5_to_2b6_contract_test.dart` | Creates `GridLineRemover()`, validates input contract | MINOR — may need metric key updates if contract checks per-page keys |
| `integration_test/grid_removal_diagnostic_test.dart:99` | Creates `GridLineRemover()` for diagnostic runs | NO CHANGE — uses public API |

## Test Files

| File | What It Tests | Change Needed |
|------|--------------|---------------|
| `test/features/pdf/extraction/stages/grid_line_remover_test.dart` | 6 existing tests: empty input, passthrough, fallback, diagnostics, metrics, pathological guard | MODIFY — add fringe-specific tests, update metric assertions |
| `test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart` | 2 tests: PNG validity, metric keys | MODIFY — add new metric keys to assertions |
| `test/features/pdf/extraction/contracts/stage_2b5_to_2b6_contract_test.dart` | Input contract validation | CHECK — verify no metric key assertions affected |

## Dead Code to Remove

| File | Symbol | Reason |
|------|--------|--------|
| `grid_line_remover.dart:535` | `notTextProtection = cv.bitwiseNOT(textProtection)` | Computed but never read. Dead since text protection was disabled. Remove the allocation AND the `notTextProtection?.dispose()` in finally block. |

## Data Flow

```
                    extraction_pipeline.dart
                           |
                    gridLineRemover.remove()
                           |
                    _removeGridLines()
                           |
    ┌──────────────────────┼──────────────────────┐
    |                      |                      |
 Steps 1-4            Step 5 (existing)      Step 6-8 (NEW)
 decode/morph/        Draw lines on          Measure fringe
 hough/cluster        removalMask            Expand mask
    |                      |                      |
    └──────────────────────┼──────────────────────┘
                           |
                    Steps 9-11 (existing)
                    inpaint + encode
                           |
                    _GridRemovalResult
                    (+ 5 new fields)
                           |
                    Per-page metrics dict
                    (+ 3 new keys)
```

## Blast Radius Summary

| Category | Count |
|----------|-------|
| Direct files modified | 1 (grid_line_remover.dart) |
| Test files modified | 2 (grid_line_remover_test.dart, stage_2b6_to_2biii_contract_test.dart) |
| Test helper modified | 1 (test_fixtures.dart — new function) |
| Dependent files (no change) | 4 (pipeline, mock, stage_2b5 contract, diagnostic test) |
| Dead code removed | 1 allocation (notTextProtection) |
| New functions created | 2 (_measureLineFringe, createAntiAliasedGridImage) |
| Public API changes | 0 |
