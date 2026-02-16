# Plan: Full Pipeline Diagnostic Image Capture + PRD Update

**Status**: IN PROGRESS
**Created**: 2026-02-16 (Session 353)
**Context**: The stage trace diagnostic currently captures JSON at 10 of 14 stage boundaries, but zero image data. The entire image pipeline (Stages 2B-i through 2B-iii) is a black box — we can't see what Tesseract receives or how preprocessing affects quality. OCR is producing garbled text (`||8`, `[Fence &`, `| ©`) and we're debugging blind. Additionally, the PRD 2.0 is outdated — missing row-strip OCR, synthetic regions, and CropUpscaler documentation.

**Approach**: Save raw images at every stage — no overlays, no annotations. The existing JSON fixtures already describe what the pipeline read. The images show what the pipeline saw. Developer opens both side by side.

---

## Phase 1: Add `onDiagnosticImage` callback to pipeline

### 1A: Thread callback through method signatures

Add one optional parameter to 4 method signatures:

```dart
void Function(String name, Uint8List pngBytes)? onDiagnosticImage,
```

| File | Method | Line |
|------|--------|------|
| `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` | `extract()` | ~205 |
| `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` | `_runExtractionStages()` | ~346 |
| `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart` | `recognize()` | ~66 |
| `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart` | `_recognizeWithRowStrips()` | ~231 |

Pass through at each call site. When `null` (production), zero overhead via `?.` operator.

### 1B: Insert image capture calls

**After Stage 2B-i** (~line 392) — rendered pages:
```dart
for (final entry in renderedPages.entries) {
  onDiagnosticImage?.call('page_${entry.key}_rendered', entry.value.imageBytes);
}
```

**After Stage 2B-ii** (~line 401) — preprocessed pages:
```dart
for (final entry in preprocessedPages.entries) {
  onDiagnosticImage?.call('page_${entry.key}_preprocessed', entry.value.enhancedImageBytes);
}
```

**Inside `_recognizeWithRowStrips()`** after `img.copyCrop()` (~line 352) — raw strip:
```dart
onDiagnosticImage?.call(
  'page_${pageIndex}_row_${strip.rowIndex}_strip_raw',
  Uint8List.fromList(img.encodePng(cropped)),
);
```

**Inside `_recognizeWithRowStrips()`** after upscaling (~line 390) — strip as sent to Tesseract:
```dart
onDiagnosticImage?.call(
  'page_${pageIndex}_row_${strip.rowIndex}_strip_ocr',
  cropBytes,  // already PNG-encoded at this point
);
```

### 1C: Add missing `onStageOutput` calls for JSON metadata

4 stages currently have no `onStageOutput` call. Add them:

| Stage | Data to capture |
|-------|----------------|
| **2B-i Page Rendering** | pages rendered, DPI, renderer used, page dimensions |
| **2B-ii Preprocessing** | contrast before/after per page, fallback flags |
| **2B-iii Text Recognition** | total elements, per-page counts, row/PSM stats |
| **4A Phase 1B Refinement** | refined row classifications (full `toMap()`) |

Check `stage_names.dart` for existing constants. Add new ones if needed.

### Files modified:
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
- `lib/features/pdf/services/extraction/stages/stage_names.dart` (if new constants needed)

---

## Phase 2: Update fixture generator

### Modify: `integration_test/generate_golden_fixtures_test.dart`

**Changes:**
1. Wire up `onDiagnosticImage` callback — save each image as a PNG file to `diagnostic_images/` subdirectory
2. Wire up `onStageOutput` for the 4 new JSON fixtures
3. Write `capture_manifest.json` listing all saved images with metadata (filename, stage, page, row)

**Output directory:**
```
test/features/pdf/extraction/fixtures/
├── springfield_*.json                    ← existing (10 files)
├── springfield_rendering_metadata.json   ← NEW
├── springfield_preprocessing_stats.json  ← NEW
├── springfield_ocr_metrics.json          ← NEW
├── springfield_phase1b_refinement.json   ← NEW
└── diagnostic_images/                    ← NEW
    ├── capture_manifest.json
    ├── page_0_rendered.png               ← what PDF rendering produced
    ├── page_0_preprocessed.png           ← after grayscale + contrast
    ├── page_0_row_00_strip_raw.png       ← raw crop from preprocessed image
    ├── page_0_row_00_strip_ocr.png       ← after upscaling, exactly what Tesseract saw
    ├── page_0_row_01_strip_raw.png
    ├── page_0_row_01_strip_ocr.png
    ├── ... (all rows for all 6 pages)
    └── page_5_row_18_strip_ocr.png
```

**Estimated count:** 6 rendered + 6 preprocessed + ~284 strips × 2 = ~580 images

### Add to `.gitignore`:
```
test/features/pdf/extraction/fixtures/diagnostic_images/
```

### Files modified:
- `integration_test/generate_golden_fixtures_test.dart`
- `.gitignore`

---

## Phase 3: Update stage trace diagnostic test

### Modify: `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`

**Changes:**
1. Add test groups for the 4 new JSON fixtures (rendering, preprocessing, OCR metrics, Phase 1B)
2. Add "Diagnostic Image Availability" group — verifies expected images exist on disk, prints file paths for manual inspection
3. Print image paths alongside each stage analysis so developer knows which PNG to open
4. Update `stageToFilename` mapping if needed

### Files modified:
- `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`

---

## Phase 4: Update PRD and documentation

### Modify: `.claude/prds/pdf-extraction-v2-prd-2.0.md`

The PRD is outdated (last updated 2026-02-14). Missing:

**Section 2 (Stage-by-Stage) — update existing stages:**
- Stage 2B-iii: Row-strip OCR (replaced cell-level)
- Stage 4B: Synthetic regions for grid pages
- Stage 4C: Grid-aware column detection

**New Section 9 (or after Section 8): Diagnostic Capture System**
- `onDiagnosticImage` callback specification and usage
- Image capture points (4 types: rendered, preprocessed, strip_raw, strip_ocr)
- Fixture directory structure

**Section 10 (Testing Strategy) — update:**
- Stage trace diagnostic test documentation
- Fixture generation process
- New JSON fixtures and diagnostic image verification

**Section 12 (File Map) — update:**
- Add/update file entries for all modified files

### Also update:
- `.claude/memory/MEMORY.md` — Add note about diagnostic capture system
- `.claude/autoload/_state.md` — Session 353 summary

### Files modified:
- `.claude/prds/pdf-extraction-v2-prd-2.0.md`
- `.claude/memory/MEMORY.md`
- `.claude/autoload/_state.md`

---

## Verification

1. **Run integration test** — regenerate fixtures + diagnostic images
2. **Check diagnostic_images/** — should contain ~580 PNGs + manifest
3. **Run stage trace diagnostic** — should pass all tests including new groups
4. **Run full PDF test suite** — no regressions

---

## Summary

| Phase | What | Production Code | Test Code | Docs |
|-------|------|:-:|:-:|:-:|
| 1 | `onDiagnosticImage` callback + missing `onStageOutput` calls | 3 files modified | — | — |
| 2 | Fixture generator saves images | — | 1 file modified | 1 file (.gitignore) |
| 3 | Stage trace test updates | — | 1 file modified | — |
| 4 | PRD + memory + state updates | — | — | 3 files modified |

**Total production code changes:** ~30 lines across 3 files (1 callback param + ~20 capture calls + stage name constants)
**Total test code changes:** ~100 lines across 2 files
**New files:** 0 (no overlay renderer needed)
