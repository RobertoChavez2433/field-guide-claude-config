# OCR Accuracy Fixes — Dependency Graph

## Direct Changes

### 1. post_process_utils.dart — Curly quote normalization (Fix #1)
- **File**: `lib/features/pdf/services/extraction/shared/post_process_utils.dart`
- **Method**: `cleanDescriptionArtifacts` (line 39-58)
- **Change**: Convert curly quotes → straight quotes BEFORE the strip rule
- **Current**: `.replaceAll(RegExp(r'[\u201C\u201D\u2018\u2019`]'), '')` — deletes curly quotes
- **Fix**: `.replaceAll(RegExp(r'[\u201C\u201D]'), '"').replaceAll(RegExp(r'[\u2018\u2019]'), "'").replaceAll('`', '')`
- **Impact**: Item 52 (trailing `"` preserved instead of stripped)

### 2. post_process_utils.dart — Unit case normalization (Fix #2)
- **File**: `lib/features/pdf/services/extraction/shared/post_process_utils.dart`
- **Method**: `normalizeUnit` (line 308-311) → calls `_cleanUnitText` (line 318-325) → calls `_normalizeUnitInternal` (line 349)
- **Change**: Ensure `.toUpperCase()` is applied before registry lookup
- **Method**: `_cleanUnitText` (line 318-325) — already strips periods and whitespace
- **Note**: `_cleanOcrArtifacts` (line 333-346) strips quotes and punctuation but does NOT uppercase
- **Check**: Does `_normalizeUnitInternal` already uppercase? Need to verify UnitRegistry behavior
- **Impact**: Item 106 (`Ft` → `FT`)

### 3. text_recognizer_v2.dart — Drop fringe term from crop insets (Fix #3)
- **File**: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
- **Method**: `_computeCellCrops` (line 1174-1243)
- **Lines**: 1209-1212 (inset calculations)
- **Current**: `(widthPixels + 1) ~/ 2 + fringeSideN + 1`
- **Fix**: `(widthPixels + 1) ~/ 2 + 1` (drop fringe term)
- **Math**: Whitewash covers `halfWidth + maxFringe + 2px` = 4px from center. New crop = `halfWidth + 1` = 2px from center. 2px pure white buffer.
- **Impact**: Item 130 (y descender no longer clipped), possibly item 62

### 4. cell_extractor_v2.dart — Y-band sort fix for short punctuation (Fix #4)
- **File**: `lib/features/pdf/services/extraction/stages/cell_extractor_v2.dart`
- **Method**: `_buildCell` (line 517-571)
- **Current**: `medianHeight * 0.5` tolerance treats short glyphs (like `-`) as different Y-band
- **Fix**: Anchor short/isolated punctuation fragments to the nearest word fragment's Y-band, OR use Y-center clustering instead of Y-top comparison
- **Impact**: Items 26, 36, 37, 38 (dash/word displacement)

### 5. crop_upscaler.dart — Column-selective upscale for descriptions (Fix #5)
- **File**: `lib/features/pdf/services/extraction/shared/crop_upscaler.dart`
- **Constants**: `kTargetDpi = 600.0` (line 26), `kMaxScaleFactor = 4.0` (line 27)
- **Method**: `computeScaleFactor` (line 114-126)
- **Current**: All columns upscaled to 600 DPI (2x from 300 DPI input)
- **Fix**: Allow per-column target DPI. Description column → 900 DPI (3x). Numeric columns stay at 600 DPI.
- **Mechanism**: `CropUpscaler` constructor takes `targetDpi` parameter, TextRecognizerV2 creates per-column instances
- **Note**: Previous blanket 900 DPI caused comma/period confusion in numerics — MUST be column-selective
- **Impact**: Item 38 superscript `th` gets 18-24px instead of 12-16px

### 6. text_recognizer_v2.dart — Item number candidate rejection (Fix #6)
- **File**: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
- **Method**: `_selectBestCandidate` (line 1003-1046)
- **Current**: For itemNumber, if all retry candidates return blank, `>` at 0.47 wins by default
- **Fix**: In `_selectBestCandidate` for `itemNumber` kind, reject candidates where text has no digits at all
- **Also check**: `_scoreCandidate` (line 938-1001) — itemNumber scoring penalizes alpha chars (`-8.0 * alphaCount`) but `>` has 0 alphaCount so penalty doesn't apply. Add: if `digitCount == 0` for itemNumber, score = -100
- **Impact**: Item 62 (row with `>` would be skipped/marked as bad instead of becoming BOGUS)

## Dependent Files (2+ levels)

| File | Dependency |
|------|-----------|
| `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` | Creates TextRecognizerV2 and CellExtractorV2 |
| `lib/features/pdf/services/extraction/stages/post_processor_v2.dart` | Calls PostProcessUtils.cleanDescriptionArtifacts, normalizeUnit |
| `lib/features/pdf/services/extraction/stages/value_normalizer.dart` | Consumes cell extraction output |

## Test Files

| File | Tests |
|------|-------|
| `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart` | TextRecognizerV2 |
| `test/features/pdf/extraction/stages/stage_4d_cell_extractor_test.dart` | CellExtractorV2._buildCell |
| `test/features/pdf/extraction/shared/post_process_utils_test.dart` | PostProcessUtils (NEW from prior plan) |
| `integration_test/springfield_report_test.dart` | End-to-end validation |

## Data Flow

```
PDF → page_rendering → image_preprocessing → grid_line_detection
  → grid_line_removal (whitewash) → text_recognition (CropUpscaler → Tesseract)
  → element_validation → row_classification → cell_extraction (_buildCell sort)
  → numeric_interpretation → row_parsing → post_processing (cleanDescriptionArtifacts, normalizeUnit)
  → quality_validation → output
```

## Blast Radius

- **Direct**: 4 source files (post_process_utils, text_recognizer_v2, cell_extractor_v2, crop_upscaler)
- **Dependent**: 3 files (pipeline, post_processor_v2, value_normalizer) — no changes needed, just consumers
- **Tests**: 3 test files + 1 integration test
- **Cleanup**: None
