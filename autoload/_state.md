# Session State

**Last Updated**: 2026-02-19 | **Session**: 383

## Current Phase
- **Phase**: Pipeline Quality - OpenCV Integration Planning
- **Status**: Inset algorithm improved (131/131 items, 0 BUG). Remaining gap: 2 bid_amounts need OpenCV morphological line removal. 8 test expectations need updating.

## HOT CONTEXT - Resume Here

### What Was Done This Session (383)

#### 1. Root Cause Investigation — 4 Missing Items (64, 74, 75, 77)
- Dispatched 5 parallel agents to trace the full pipeline upstream.
- **Root cause chain (confirmed)**: Anti-aliased grid line fringe pixels survive the inset algorithm → PSM 7 reads the fringe as garbage ("al", "ot", "re", "or") → rows misclassified as `priceContinuation` → row merger absorbs them into preceding items → 4 items lost, 3 bogus items created.
- Page 3 has width-2 horizontal lines. The `_scanRefinedInsetAtProbe` had `plannedDepth = w+aa+3 = 6` which exactly matched the anti-aliased dark extent → scan returned null → fell back to `baselineInset = 3` (insufficient).
- Additionally, line 745 used `baselineInset` as a FLOOR on all scan results, overriding dynamic measurements.

#### 2. Inset Algorithm Fix (2 code changes)
- `plannedDepth`: `w + aa + 3` → `w + aa + 5` (scan has room to find line end for thin lines)
- Removed `baselineInset` floor on line 745: scan results are now trusted, not overridden
- `baselineInset` kept at `+1` (conservative fallback for when scan returns null)

#### 3. Results After Fix
- **131/131 items parsed** (was 127), **131/131 GT matched** (was 124), **0 bogus** (was 3)
- **Checksum PASS** (was FAIL), **0 BUG** (was 2), quality **0.977** (was 0.916)
- **54 OK / 1 LOW / 0 BUG** (was 48 OK / 5 LOW / 2 BUG)
- bid_amount: 129/131 (was 124) — 2 remaining are pre-existing

#### 4. Pre-existing bid_amount Gap (Items 29, 113)
- Diagnostic images show `$7,026.00` and `$2,000.00` with last `0` half-cut at right crop edge
- Right vertical lines on pages 1, 4 are width=5 (thickest in document)
- Text physically extends into the grid line fringe zone — no inset value can distinguish fringe from content
- **This is a fundamental limit of pixel-threshold scanning** — confirmed pre-existing (items were empty/null in committed HEAD too)

#### 5. OpenCV Research
- `opencv_dart` v2.2.1+3 is the recommended package — FFI-based, Windows/Android/iOS, Dart 3.10+ compatible
- **Morphological line removal** would solve both the fringe issue and the over-cropping issue:
  - `adaptiveThreshold` handles anti-aliasing natively (local neighborhoods, not fixed threshold)
  - `morphologyEx(MORPH_OPEN)` with directional kernels detects lines by SHAPE, not position
  - Can remove grid lines without touching adjacent text
- Would replace ~200 lines of inset scanning with ~20 lines of OpenCV calls
- Performance: ~500ms for full document (vs ~5s current Dart pixel scanning)
- Binary size: +15-30MB (mitigated by selective module inclusion)

#### 6. Test Status
- 848 pass, 8 fail in extraction suite
- 6 failures: `whitespace_inset_test.dart` — test expectations for old algorithm behavior (need updating)
- 1 failure: scorecard strict gate (1 LOW for quality status label "autoAccept" vs "acceptable")
- 1 failure: golden baseline (needs fixture regeneration)

### What Needs to Happen Next

1. **Plan OpenCV integration** — design the `GridLineRemover` stage using `opencv_dart` morphological operations
2. **Update 6 whitespace_inset_test expectations** to match new algorithm (no baselineInset floor, increased plannedDepth)
3. **Update scorecard Quality Status expectation** from "acceptable" to "autoAccept" (or fix upstream)
4. **Update golden baseline** test
5. Consider whether to keep or simplify the inset algorithm once OpenCV handles line removal

## Blockers

### BLOCKER-5: 2 Pre-existing bid_amount Gaps (Items 29, 113) — REDUCED
**Impact**: 129/131 bid_amount. $9,026 delta. Items have text physically touching grid line fringe zone.
**Root cause**: Pixel-threshold scanning cannot distinguish grid line fringe from adjacent text content.
**Fix**: OpenCV morphological line removal (planned for next session).
**Status**: Open. Reduced from 7 missing items to 2.

### BLOCKER-6: Global Test Suite Has Unrelated Existing Failures
**Impact**: Full-repo flutter test remains non-green outside extraction scope.
**Status**: Pre-existing/unrelated.

### BLOCKER-7: Fixture Generator Requires SPRINGFIELD_PDF Runtime Define
**Impact**: Fixtures must be regenerated manually via dart-define.
**Status**: Mitigated.

### BLOCKER-8: 8 Extraction Test Expectations Stale
**Impact**: 6 whitespace_inset_tests + 1 golden baseline + 1 scorecard gate need updating for new algorithm.
**Status**: Open. Quick fix — test expectation updates only, no code changes.

## Recent Sessions

### Session 383 (2026-02-19)
**Work**: Root-caused 4 missing items to anti-aliased grid line fringe + baselineInset floor. Fixed with 2 code changes. Recovered 131/131 items, 0 BUG. Investigated remaining 2 bid_amounts — pre-existing, need OpenCV. Researched opencv_dart package.
**Decisions**: OpenCV morphological line removal is the path forward for the last 2 bid_amounts. Keep inset fix. Next session: plan OpenCV integration.
**Scorecard**: 54 OK / 1 LOW / 0 BUG (was 48/5/2).

### Session 382 (2026-02-19)
**Work**: Deep investigation of 7 missing GT items. Discovered mystery: Tesseract produces garbage for 4 cells despite clear diagnostic images.
**Next**: Debug OCR-to-element mapping path.

### Session 381 (2026-02-19)
**Work**: Implemented drift-offset plan, tightened scorecard thresholds.

### Session 380 (2026-02-19)
**Work**: Rigorous multi-agent investigation proved drift-correction frame mismatch.

### Session 379 (2026-02-19)
**Work**: Root-cause confirmation for pipe artifacts tied to inset frame mismatch.

## Active Plans

### OpenCV Integration for Grid Line Removal (NEXT SESSION)
- Package: `opencv_dart` v2.2.1+3 (pub.dev)
- Approach: `adaptiveThreshold` + `morphologyEx(MORPH_OPEN)` with directional kernels + `dilate` for fringe
- New stage: `GridLineRemover` between ImagePreprocessor and TextRecognizer
- Would eliminate need for `_scanWhitespaceInset`, `_computeLineInset`, `_scanRefinedInsetAtProbe` (~200 lines)
- Research saved in agent output files

### Scorecard Threshold Alignment
- Ref: test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart
- Status: Strict gates in place. 1 LOW remaining (quality status label).

## Reference
- **Archive**: .claude/logs/state-archive.md (Sessions 193-376)
- **Defects**: .claude/defects/_defects-pdf.md
- **Ground Truth**: test/features/pdf/extraction/fixtures/springfield_ground_truth_items.json (131 items)
- **Current scorecard**: 54 OK / 1 LOW / 0 BUG, parsed 131, bid_amount 129, quality 0.977.
- **Code changes**: `text_recognizer_v2.dart` lines 724-725 (plannedDepth, baselineInset) and line 744 (removed floor)
- **OpenCV research**: Agent output in temp files (summarized in session notes above)
