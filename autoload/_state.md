# Session State

**Last Updated**: 2026-02-19 | **Session**: 384

## Current Phase
- **Phase**: Pipeline Quality - OpenCV Integration
- **Status**: Design plan complete. Next: fix 8 stale tests (PR #1), then implement GridLineRemover with opencv_dart (PR #2). Target: 131/131 bid_amount (100% accuracy).

## HOT CONTEXT - Resume Here

### What Was Done This Session (384)

#### 1. OpenCV Integration Design (Brainstorming Session)
- Dispatched 3 parallel research agents: current inset code analysis, opencv_dart API research, pipeline stage mapping.
- 4th agent researched community best practices (Camelot, Tabula, img2table, Multi-Type-TD-TSR, Leptonica).
- **Community consensus**: Full-page line removal BEFORE cell cropping. Every major production pipeline does this. No per-cell removal in production.

#### 2. Design Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Line removal scope | Full page before cell cropping | Community consensus; line continuity needed for morphological detection |
| Removal technique | Inpainting (Telea algorithm) | Reconstructs text strokes where lines intersect (items 29/113) |
| Legacy code handling | Delete ~304 lines immediately | Clean break; no feature flags or dead code |
| Implementation sequence | Fix stale tests first → OpenCV PR | Green baseline before major changes |
| Stage output | Full diagnostic capture | Same pattern as all other stages |

#### 3. Plan Exported
- Full design doc: `.claude/plans/2026-02-19-opencv-grid-line-removal-design.md`
- 4 implementation phases across 2 PRs
- opencv_dart v2.2.1+3 confirmed compatible (Flutter 3.38.9 / Dart 3.10.8)
- New stage: GridLineRemover (2B-ii.6) between GridLineDetector and TextRecognizerV2

### What Needs to Happen Next

1. **Phase 1 (PR #1)**: Fix 8 stale test expectations — 6 whitespace_inset_tests + 1 golden baseline + 1 scorecard gate
2. **Phase 2 (PR #2)**: Add opencv_dart, implement GridLineRemover, integrate into pipeline, delete inset code
3. **Phase 3**: Update all tests, regenerate Springfield fixtures
4. **Phase 4**: Validate 131/131 bid_amount — items 29 & 113 via inpainting

## Blockers

### BLOCKER-5: 2 Pre-existing bid_amount Gaps (Items 29, 113) — DESIGN COMPLETE
**Impact**: 129/131 bid_amount. $9,026 delta.
**Root cause**: Text physically touching grid line fringe zone — pixel-threshold scanning limit.
**Fix**: OpenCV morphological line removal + Telea inpainting. Design plan ready.
**Status**: Design complete. Implementation next session.

### BLOCKER-6: Global Test Suite Has Unrelated Existing Failures
**Impact**: Full-repo flutter test remains non-green outside extraction scope.
**Status**: Pre-existing/unrelated.

### BLOCKER-7: Fixture Generator Requires SPRINGFIELD_PDF Runtime Define
**Impact**: Fixtures must be regenerated manually via dart-define.
**Status**: Mitigated.

### BLOCKER-8: 8 Extraction Test Expectations Stale
**Impact**: 6 whitespace_inset_tests + 1 golden baseline + 1 scorecard gate.
**Status**: Open. Phase 1 priority — fix before OpenCV work.

## Recent Sessions

### Session 384 (2026-02-19)
**Work**: Brainstorming session — designed OpenCV grid line removal integration. 4 research agents gathered context. Community consensus: full-page removal before cell cropping. Plan exported.
**Decisions**: Inpainting (Telea), delete inset code, fix tests first then OpenCV PR.
**Next**: Phase 1 — fix 8 stale tests. Then Phase 2 — implement GridLineRemover.

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

## Active Plans

### OpenCV Integration for Grid Line Removal — DESIGN COMPLETE
- **Plan file**: `.claude/plans/2026-02-19-opencv-grid-line-removal-design.md`
- Package: `opencv_dart` v2.2.1+3 (core + imgproc + imgcodecs + photo)
- Algorithm: adaptiveThreshold → morphologyEx(MORPH_OPEN) → inpaint(TELEA)
- New stage: `GridLineRemover` (2B-ii.6) between GridLineDetector and TextRecognizerV2
- Deletes ~304 lines of inset scanning code from TextRecognizerV2
- 4 phases, 2 PRs. Phase 1: fix stale tests. Phase 2: implement + validate.

### Scorecard Threshold Alignment
- Ref: test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart
- Status: Strict gates in place. 1 LOW remaining (quality status label). Included in Phase 1 test fixes.

## Reference
- **Archive**: .claude/logs/state-archive.md (Sessions 193-379)
- **Defects**: .claude/defects/_defects-pdf.md
- **Ground Truth**: test/features/pdf/extraction/fixtures/springfield_ground_truth_items.json (131 items)
- **Current scorecard**: 54 OK / 1 LOW / 0 BUG, parsed 131, bid_amount 129, quality 0.977.
- **Design plan**: .claude/plans/2026-02-19-opencv-grid-line-removal-design.md
- **Code changes (Session 383)**: `text_recognizer_v2.dart` lines 724-725 (plannedDepth, baselineInset) and line 744 (removed floor)
