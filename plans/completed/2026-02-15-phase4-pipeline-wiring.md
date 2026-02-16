# Phase 4: Pipeline Wiring + Fixtures

**Parent plan**: `2026-02-14-grid-line-detection-row-ocr.md`
**Prerequisite**: Phases 1-3 complete (GridLineDetector, row cropping, grid-based column detection)
**Agent**: `frontend-flutter-specialist-agent` (pipeline code) + manual fixture regeneration

---

## Overview

Wire the already-implemented GridLineDetector stage into the extraction pipeline so it executes between image preprocessing (Stage 2B-ii) and text recognition (Stage 2B-iii). Pass GridLines data downstream to text recognizer and column detector. Regenerate all Springfield fixtures and update golden test expectations.

### Success Criteria

- [ ] GridLineDetector runs as Stage 2B.5 in the pipeline
- [ ] GridLines passed to TextRecognizerV2 and ColumnDetectorV2
- [ ] `springfield_grid_lines.json` fixture generated
- [ ] All extraction tests pass
- [ ] Golden test expectations updated to reflect improved extraction quality

---

## Step 1: Wire GridLineDetector into ExtractionPipeline

**File**: `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`

### 1A. Add field + constructor parameter

Between `imagePreprocessor` and `textRecognizer`:

**Field** (insert after line 148):
```dart
final GridLineDetector gridLineDetector;
```

**Constructor param** (insert after line 165 `ImagePreprocessorV2? imagePreprocessor,`):
```dart
GridLineDetector? gridLineDetector,
```

**Initializer** (insert after line 178 `imagePreprocessor = imagePreprocessor ?? ImagePreprocessorV2(),`):
```dart
gridLineDetector = gridLineDetector ?? GridLineDetector(),
```

### 1B. Insert Stage 2B.5 call

Insert after line 402 (after preprocessing debug log, before text recognition):

```dart
// Stage 2B.5: Grid Line Detection
final (gridLines, stage2B5Report) = await gridLineDetector.detect(
  preprocessedPages: preprocessedPages,
);
reports.add(stage2B5Report);

DebugLogger.pdf(
  '[Pipeline] Stage 2B.5 complete: ${gridLines.gridPages.length} grid pages, '
  '${gridLines.nonGridPages.length} non-grid pages',
);

onStageOutput?.call(StageNames.gridLineDetection, gridLines.toMap());
```

### 1C. Pass gridLines to text recognizer

Modify the `textRecognizer.recognize()` call at line ~405:

```dart
final (elements, stage2BiiiReport) = await textRecognizer.recognize(
  pages: preprocessedPages,
  originalPages: renderedPages,
  engine: ocrEngine,
  gridLines: gridLines,  // NEW
);
```

### 1D. Pass gridLines to column detector

Modify the `columnDetector.detect()` call at line ~464:

```dart
final (columnMap, stage4CReport) = await columnDetector.detect(
  detectedRegions: detectedRegions,
  classifiedRows: classifiedRows,
  extractionResult: extractionResult,
  gridLines: gridLines,  // NEW
);
```

### 1E. Update totalStages constant

Change line 352:
```dart
const totalStages = 13; // was 12
```

---

## Step 2: Regenerate Springfield Fixtures

The fixture generator already maps `StageNames.gridLineDetection` to `springfield_grid_lines.json` (verified in `tool/generate_springfield_fixtures.dart:15`).

```bash
pwsh -Command "dart run tool/generate_springfield_fixtures.dart <path-to-springfield.pdf>"
```

**Expected output**: 11 fixture files including new `springfield_grid_lines.json`

**Verify**:
- `springfield_grid_lines.json` exists and contains `pages` map with grid detection results
- Grid pages (2-6) show `hasGrid: true` with horizontal + vertical lines
- Page 1 shows `hasGrid: false` (cover page)

---

## Step 3: Update Golden Test Expectations

**File**: `test/features/pdf/extraction/golden/springfield_golden_test.dart`

After fixture regeneration, update these values based on actual results:

| Metric | Current | Expected Direction |
|--------|---------|-------------------|
| Item count (line 76) | 1 | Increase toward 131 |
| Quality score (line 82) | 0.615 | Increase toward 0.85+ |
| Match rate (line ~175) | 0% | Increase toward 90%+ |
| Total amount | $0 | Converge toward $7,882,926.73 |

Exact values determined after running fixture generator.

---

## Step 4: Run Full Test Suite

```bash
# Grid line detector tests (Phase 1)
pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_2b_grid_line_detector_test.dart"

# Column detector tests (Phase 3)
pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_4c_column_detector_test.dart"

# Golden + diagnostic tests
pwsh -Command "flutter test test/features/pdf/extraction/golden/"

# Pipeline tests
pwsh -Command "flutter test test/features/pdf/extraction/pipeline/"

# All extraction tests
pwsh -Command "flutter test test/features/pdf/extraction/"
```

---

## Files Modified

| File | Change |
|------|--------|
| `lib/.../pipeline/extraction_pipeline.dart` | Add GridLineDetector field/param, insert Stage 2B.5, pass gridLines downstream, bump totalStages |
| `test/.../golden/springfield_golden_test.dart` | Update item count, quality score, match rate expectations |

## Files Already Ready (No Changes Needed)

| File | Status |
|------|--------|
| `test/.../helpers/mock_stages.dart` | MockGridLineDetector already implemented |
| `tool/generate_springfield_fixtures.dart` | Grid line fixture mapping already present |
| `test/.../golden/stage_trace_diagnostic_test.dart` | Grid line analysis test already present |
| `test/.../pipeline/extraction_pipeline_test.dart` | Uses default constructor (auto picks up new stage) |

## Files Generated

| File | Source |
|------|--------|
| `test/.../fixtures/springfield_grid_lines.json` | Fixture generator |
| All other `springfield_*.json` fixtures | Regenerated with grid-aware OCR |

---

## Future: Phase 5 (V1 Cleanup) — Separate PR

Items deferred from Phase 4 for a dedicated cleanup pass:

1. **Test comments**: Remove `StructurePreserver` references in `stage_3_to_4a_contract_test.dart`
2. **Hardcoded stage names**: `'document_analyzer'` → `StageNames.documentAnalysis` in `full_pipeline_integration_test.dart:230`
3. **Incorrect strategy values**: `'overall_strategy': 'native'` → `'ocr_only'` in test mock data
4. **Model cleanup**: Remove `ExtractionMethod.native` enum value (OCR-only pipeline never produces it)
5. **Dead getters**: Remove `nativePageCount`, `hybridPageCount` from `DocumentProfile`
6. **Strategy validation**: Simplify `PageProfile.isValid` to only accept `'ocr'`, `DocumentProfile` to only accept `'ocr_only'`
7. **Test updates**: ~50 test files using `ExtractionMethod.native` need migration to `ExtractionMethod.ocr`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Fixture generator fails on Springfield PDF | Verify PDF path exists; check for Tesseract engine availability |
| Golden test values hard to predict before fixtures | Run generator first, then update expectations from actual output |
| Pipeline tests break from new constructor param | Default value `GridLineDetector()` ensures backward compatibility |
| Performance regression from extra stage | GridLineDetector processes already-in-memory images; ~50ms per page |

---

## Verification Checklist

- [ ] `extraction_pipeline.dart` compiles with GridLineDetector wired in
- [ ] `flutter test test/features/pdf/extraction/` — all tests pass
- [ ] `springfield_grid_lines.json` fixture exists with valid grid data
- [ ] Golden test expectations match regenerated fixture values
- [ ] Stage trace diagnostic shows grid line detection stage
- [ ] No regressions in non-grid-related tests
