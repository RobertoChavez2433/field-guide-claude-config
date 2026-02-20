# OpenCV Grid Line Removal — Design Plan

**Created**: 2026-02-19 | **Session**: 384
**Goal**: Achieve 100% field accuracy on Springfield PDF extraction

## Overview

### Purpose
Replace pixel-level inset scanning (~304 lines) with OpenCV morphological grid line removal. This eliminates the fundamental limit where text physically touching grid lines cannot be separated by threshold-based scanning.

### Scope
- Fix 8 stale test expectations (green baseline)
- Add `opencv_dart` dependency (core + imgproc + imgcodecs + photo modules)
- New `GridLineRemover` stage (2B-ii.6) using adaptive threshold + morphological open + inpainting
- Delete ~304 lines of inset scanning code from `TextRecognizerV2`
- Update all affected tests, regenerate Springfield fixtures

### Success Criteria
- 131/131 items parsed, 131/131 GT matched
- **131/131 bid_amount** (currently 129/131 — items 29, 113)
- 0 BUG, 0 LOW on scorecard
- All extraction tests green
- No regression on any other metric

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Line removal scope | Full page before cell cropping | Community consensus: Camelot, Tabula, img2table, Multi-Type-TD-TSR, Leptonica all do full-page. Line continuity needed for morphological detection. |
| Removal technique | Inpainting (Telea algorithm) | Reconstructs text strokes where lines intersect, vs simple white-fill which leaves gaps. Critical for items 29/113. |
| Legacy code handling | Delete immediately | Clean break. No feature flags, no dead code. If lines are removed from image, insets serve no purpose. |
| Implementation sequence | Fix stale tests first → OpenCV PR | Green baseline before major changes. Isolates failures. |
| Stage output | Full diagnostic capture | Same pattern as all other stages: StageReport + fixture JSON + diagnostic images. |

---

## Data Flow

### New Pipeline Sequence
```
[2B-ii]   ImagePreprocessorV2 → PreprocessedPage (grayscale + contrast)
[2B-ii.5] GridLineDetector → GridLines { positions, widths }
[2B-ii.6] GridLineRemover → CleanedPages (lines erased via inpainting)  ← NEW
[2B-iii]  TextRecognizerV2 → OcrElements (from clean cell crops)
```

### GridLineRemover Algorithm (9 steps)
```
1. Convert PreprocessedPage image → OpenCV Mat (CV_8UC1 grayscale)
2. adaptiveThreshold(ADAPTIVE_THRESH_MEAN_C, THRESH_BINARY_INV, blockSize=15, C=-2) → binary
3. getStructuringElement(MORPH_RECT, (width/30, 1)) → horizontal kernel
4. morphologyEx(MORPH_OPEN, horizKernel) → horizontal line mask
5. getStructuringElement(MORPH_RECT, (1, height/30)) → vertical kernel
6. morphologyEx(MORPH_OPEN, vertKernel) → vertical line mask
7. add(horizLines, vertLines) → combined mask
8. dilate(mask, 3x3 kernel, iterations=1) → expanded mask (covers AA fringe)
9. inpaint(original, mask, inpaintRadius=2, INPAINT_TELEA) → clean image
```

### Critical Invariant
Grid line POSITIONS from GridLineDetector remain valid after line removal. The operation only changes pixel VALUES (dark → white/inpainted), not pixel POSITIONS. `_computeCellCrops()` in TextRecognizerV2 works identically on the cleaned image.

### Stage I/O Contract
| | Type | Description |
|---|---|---|
| **Input** | `Map<int, PreprocessedPage>` + `GridLines` | Same as current TextRecognizerV2 inputs |
| **Output** | `Map<int, PreprocessedPage>` | Same type, `enhancedImageBytes` has lines removed |
| **Diagnostics** | `StageReport` + fixture JSON | Lines detected/page, pixels modified, timing, mask images |

---

## Code Changes Summary

### New Files
| File | Purpose |
|------|---------|
| `lib/features/pdf/services/extraction/stages/grid_line_remover.dart` | GridLineRemover stage implementation |
| `test/features/pdf/extraction/stages/grid_line_remover_test.dart` | Unit tests |

### Modified Files
| File | Change |
|------|--------|
| `pubspec.yaml` | Add `opencv_dart: ^2.2.1+3` + hooks config |
| `lib/features/pdf/services/extraction/stages/stage_names.dart` | Add `gridLineRemoval` constant |
| `lib/features/pdf/services/extraction/stages/stages.dart` | Export GridLineRemover |
| `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` | Insert GridLineRemover between GridLineDetector and TextRecognizerV2 |
| `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart` | Delete ~304 lines of inset code, simplify `_recognizeWithCellCrops` |
| `tool/generate_springfield_fixtures.dart` | Add GridLineRemover fixture capture |

### Deleted Code (~304 lines in text_recognizer_v2.dart)
| Method | Lines | Purpose (now obsolete) |
|--------|-------|------------------------|
| `_scanWhitespaceInset()` | 654–704 | Legacy blind pixel scan |
| `_computeLineInset()` | 708–746 | Width-driven inset |
| `_buildProbePositions()` | 748–778 | Probe coordinate generation |
| `_scanRefinedInsetAtProbe()` | 780–824 | Per-probe state machine |
| `_percentileInt()` | 826–836 | P75 aggregation |
| `_capInsetPairForInterior()` | 857–895 | Collapse prevention |
| Inset dispatch block | 313–443 | Edge-by-edge resolution |

### Test Changes
| File | Action |
|------|--------|
| `whitespace_inset_test.dart` | DELETE (code removed) |
| `stage_2b_text_recognizer_test.dart` | Remove inset test cases |
| `cell_boundary_verification_test.dart` | Update if tests inset-derived bounds |
| `extraction_pipeline_test.dart` | Add GridLineRemover stage |
| `springfield_golden_test.dart` | Regenerate fixtures + baseline |
| `stage_trace_diagnostic_test.dart` | Update scorecard expectations |

---

## Implementation Phases

### Phase 1: Fix Stale Tests (PR #1 — quick, <30min)

**Goal**: Green test baseline before OpenCV changes.

**Files to update:**
1. `test/features/pdf/extraction/stages/whitespace_inset_test.dart` — 6 expectations for new algorithm behavior (no baselineInset floor, increased plannedDepth)
2. `test/features/pdf/extraction/golden/springfield_golden_test.dart` — regenerate golden baseline
3. `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart` — scorecard Quality Status "autoAccept" vs "acceptable"

**Agent**: qa-testing-agent
**Verify**: `pwsh -Command "flutter test test/features/pdf/extraction/"` — all pass

---

### Phase 2: Add opencv_dart + Implement GridLineRemover (PR #2)

#### Step 2A: Dependency Setup
- Add `opencv_dart: ^2.2.1+3` to `pubspec.yaml`
- Configure hooks in `pubspec.yaml`:
  ```yaml
  hooks:
    user_defines:
      dartcv4:
        include_modules:
          - imgproc
          - imgcodecs
          - photo
  ```
- `flutter pub get`
- Verify Windows build compiles

#### Step 2B: Implement GridLineRemover
- New file: `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
- Class: `GridLineRemover` with `Future<(Map<int, PreprocessedPage>, StageReport)> remove(...)` signature
- Image conversion: `package:image` ↔ OpenCV Mat (prefer PNG round-trip for initial implementation, optimize to direct byte copy later if needed)
- Diagnostic output: line mask PNG bytes, per-page metrics
- Register in `stage_names.dart` (`static const gridLineRemoval = 'grid_line_removal'`)
- Export from `stages.dart`

#### Step 2C: Pipeline Integration
- `extraction_pipeline.dart`: Insert GridLineRemover call between GridLineDetector and TextRecognizerV2
- Pass cleaned `PreprocessedPage` map to TextRecognizerV2 instead of original
- Fixture generator: capture `springfield_grid_line_removal.json`

#### Step 2D: Delete Inset Code
- `text_recognizer_v2.dart`: Remove all 6 inset methods + dispatch block
- Simplify `_recognizeWithCellCrops`: raw cell bounds → `copyCrop` → upscale → OCR (no inset adjustment)
- Remove `_fallbackLineInsetPx` constant

**Agent**: pdf-agent (implementation), frontend-flutter-specialist-agent (Dart code changes)

---

### Phase 3: Test Updates + Validation (PR #2 continued)

**New tests:**
- `grid_line_remover_test.dart` — unit tests with synthetic images containing known grid lines
- Contract test: GridLineDetector output → GridLineRemover input

**Updated tests:**
- DELETE `whitespace_inset_test.dart` (code removed)
- `stage_2b_text_recognizer_test.dart` — remove inset-related test cases
- `cell_boundary_verification_test.dart` — update if needed
- `extraction_pipeline_test.dart` — add GridLineRemover in mock stage list
- `re_extraction_loop_test.dart` — update if pipeline stage count changed
- Mock stages helper — add GridLineRemover mock

**Regenerate:**
- All Springfield fixtures via fixture generator
- Golden baseline

**Verify**: Full scorecard — target 55 OK / 0 LOW / 0 BUG

---

### Phase 4: Validate 100% Accuracy

- Regenerate Springfield fixtures with full pipeline
- Run stage trace diagnostic
- Verify items 29, 113 bid_amounts recovered
- If inpainting works: all success criteria met
- If not: investigate diagnostic images, tune parameters:
  - `inpaintRadius` (try 2, 3, 4)
  - `blockSize` for adaptiveThreshold (try 11, 15, 21)
  - Kernel divisor (try /20, /25, /30, /40)
  - Mask dilation iterations (try 1, 2)

---

## Tuning Parameters Reference

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `blockSize` | 15 | 11-31 (odd) | Adaptive threshold neighborhood size |
| `C` | -2.0 | -5.0 to 0 | Threshold constant (negative = more sensitive) |
| Kernel divisor | 30 | 20-50 | Min line length = dimension/divisor |
| Mask dilation | 1 iteration | 1-3 | AA fringe coverage (3x3 RECT kernel) |
| `inpaintRadius` | 2 | 1-5 | Text reconstruction reach |

---

## opencv_dart Package Reference

| Field | Value |
|-------|-------|
| Package | `opencv_dart` ^2.2.1+3 |
| Dart SDK | 3.10+ (we have 3.10.8) |
| Flutter | 3.38+ (we have 3.38.9) |
| Modules needed | core (auto), imgproc, imgcodecs, photo |
| Binary size | +8-20MB depending on platform |
| Platforms | Windows x64, Android arm64/armv7, iOS arm64 |

### Key APIs
```dart
import 'package:opencv_dart/opencv_dart.dart' as cv;

// Thresholding
cv.adaptiveThreshold(src, maxVal, method, type, blockSize, C)

// Morphological operations
cv.getStructuringElement(shape, ksize)
cv.morphologyEx(src, op, kernel)
cv.dilate(src, kernel, iterations: n)

// Arithmetic
cv.add(src1, src2)

// Inpainting
cv.inpaint(src, mask, inpaintRadius, flags)

// Image conversion
cv.imdecode(bytes, flags)  // Uint8List → Mat
cv.imencode('.png', mat)   // Mat → Uint8List

// CRITICAL: Always dispose Mats to avoid native memory leaks
mat.dispose()
```

### Async Variants
All functions have `Async` variants (e.g., `adaptiveThresholdAsync`, `morphologyExAsync`) that run on background threads. Use these to avoid blocking the UI isolate.

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| opencv_dart build fails on Windows | Pin version, verify build in Step 2A before any code changes |
| Binary size too large | Module inclusion limits to ~8-20MB. Acceptable for construction app. |
| Inpainting doesn't fix items 29/113 | Tune parameters in Phase 4. Worst case: same 129/131 as today (no regression). |
| Text stroke damage from aggressive morphology | Kernel length `width/30` ≈ 70px at our DPI, far exceeding any text stroke. Safe. |
| AA fringe residue after removal | Mask dilation of 1-2px covers fringe. Validated in diagnostic images. |
| Memory leaks from Mat objects | Explicit `.dispose()` calls. Unit tests verify no leaks. |

---

## Agent Assignments

| Phase | Agent | Task |
|-------|-------|------|
| 1 | qa-testing-agent | Fix 8 stale test expectations |
| 2A | frontend-flutter-specialist-agent | Dependency setup, build verification |
| 2B | pdf-agent | Implement GridLineRemover |
| 2C | pdf-agent | Pipeline integration |
| 2D | pdf-agent + code-review-agent | Delete inset code, verify clean removal |
| 3 | qa-testing-agent | New tests + test updates |
| 4 | pdf-agent | Fixture regeneration, scorecard validation |
