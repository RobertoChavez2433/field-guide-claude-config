# Key Learnings & Patterns

## Project: Field Guide App (Construction Inspector)

### Build Tips
- Build folder lock: kill dart.exe and construction_inspector.exe, wait 5s, then delete build/

### PDF Extraction Pipeline
- **OCR-ONLY pipeline** — Native text extraction is OFF. CMap corruption across PDFs made native extraction unreliable. 2 weeks spent decoding corruption, scrapped. DO NOT suggest native/hybrid extraction.
- V2 pipeline: DocumentQualityProfiler → PageRenderer → ImagePreprocessor → TextRecognizer → ElementValidator → RowClassifier → RegionDetector → ColumnDetector → CellExtractor → RowParser → PostProcessor → QualityValidator
- Springfield PDF: 131 items across 6 pages, headers split multi-line ("Item\nNo.", "Est.\nQuantity")
- **PSM Mode**: Default PSM=6 (single block) produces garbage on table-heavy pages. Needs investigation for table-structured PDFs.
- RowClassifier (Phase 1A pre-column, Phase 1B post-column) classifies rows into 6 types
- TableRegionDetector uses two-pass linear scan with cross-page header confirmation
- **OCR Preprocessing**: Removed binarization — clean PDFs need grayscale + contrast only. Binarization destroyed 92% of image data.
- **Diagnostic Image Capture**: `onDiagnosticImage` callback in pipeline captures raw PNGs at 4 stages (rendered, preprocessed, strip_raw, strip_ocr). Plus 4 new JSON fixtures (rendering metadata, preprocessing stats, OCR metrics, Phase 1B refinement). Images saved to `test/features/pdf/extraction/fixtures/diagnostic_images/` (gitignored). Run fixture generator to populate.
- **Current baseline (2026-02-19, Session 394)**: Scorecard `68 OK / 3 LOW / 0 BUG` (72 metrics), quality `0.993`, parsed `131/131`, GT matched `131/131` (100%), bid_amount `131/131`, unit_price `131/131`. Math backsolve fixed items 100, 121. 850 extraction tests green.
- **Math backsolve** (Session 394): When `qty × unitPrice ≠ bidAmount`, derive `unitPrice = bidAmount / qty`. Only apply when backsolve round-trips within $0.02. Confidence penalty `kAdjMathBacksolve = -0.03`. Located in `post_processor_v2.dart:_applyConsistencyRules`.
- **Zero-conf sentinel** (Session 394): Tesseract sometimes reports 0.0 confidence when `x_wconf` HOCR attribute is absent. Sentinel in `field_confidence_scorer.dart:_scoreField` replaces 0.0 with 0.50 neutral prior when cell has valid text. Improved quality from 0.990 → 0.993 but B2 conf gap (Δ0.066) still persists.
- **Grid line positions are accurate to <1px** — `grid_line_detector.dart` reports line CENTER (midpoint of dark pixel run). Cell boundaries placed at line centers. `edgePos = floor(center * imageWidth)`. Max structural drift < 1px (floor rounding only).
- **Drift correction REMOVED** (Session 380-383): `_correctEdgePosForLineDrift` caused 35 pipe artifacts. Now scan directly from edgePos.
- **Inset algorithm** (Session 383): `_computeLineInset` uses `plannedDepth = w+aa+5`, `baselineInset = ceil(w/2)+ceil(w*0.25)+1`. REMOVED the `baselineInset` floor — scan p75 result is trusted directly. This fixed 4 missing items (ghost OCR from thin-line fringe).
- **OpenCV grid line removal IMPLEMENTED** (Session 385-386): `GridLineRemover` stage (2B-ii.6) uses `adaptiveThreshold` + `morphologyEx(MORPH_OPEN)` + `inpaint(TELEA)`. Package: `opencv_dart` v2.2.1+3. Resolved items 29/113 bid_amount gaps. Legacy inset scanning code removed from TextRecognizerV2.
- **Tesseract `$` misread pattern**: `$110.00` -> `"Si"` (PSM7 word segmentation failure on right-aligned text in wide cell). Re-OCR fallback IMPLEMENTED (PSM8+whitelist) but FAILS because same low-res crop is reused. Root cause is crop pixel width, not PSM mode. Plan: `.claude/plans/2026-02-19-low-confidence-reocr-fallback.md`.
- **CropUpscaler threshold gap (Session 388)**: `kMinCropWidth=300` too low. unitPrice (355px) and bidAmount (381px) columns escape upscaling despite having ALL 16 OCR errors. Upscaled columns (itemNumber 143px→300, unit 220px→300, quantity 294px→300) have ZERO errors. Fix: raise to 500px. See BLOCKER-8 in `_state.md`.
- **Broken `sourceDpi` metric**: `tesseract_engine_v2.dart:273-285` computes `72 * (cropPx / pagePts)` for crops, yielding nonsensical 27-31 "DPI". ALL columns are actually at 300 DPI (whole page renders at 300 DPI). The issue is absolute pixel width, not DPI.
- **bidAmount confidence crisis**: Mean 0.846 (worst field). 28/131 items (21.4%) below 0.80. 4 items (#15,29,73,86) at conf 0.0 despite CORRECT text. Likely Tesseract confidence reporting bug at 401px crop width.
- **CRITICAL: img.getLuminance() broken on 1-channel images** — returns only 0.299*r (g=0, b=0 on 1-channel). Use `pixel.r` directly for grayscale pixel reading. This caused grid detection to fail (every pixel appeared "dark").
- **CRITICAL: img.Image() defaults numChannels=3** — When creating canvas for compositing 1-channel crops, MUST pass `numChannels: crop.numChannels`. Otherwise white (255) reads as (r=255,g=0,b=0) = red. compositeImage alpha-blends with a=255, replacing destination entirely. This broke ALL cell OCR for sessions 342-356.
- **Row Classifier**: Numeric content gate — DATA rows must have numeric values in qty/price/amount columns
- **Post-Processing**: Validation validates item numbers (^\d+(\.\d+)?$) and units (57 known units)

### Logging System
- DebugLogger: 9 categories in `Troubleshooting/Detailed App Wide Logs/session_YYYY-MM-DD_HH-MM-SS/`
- PDF/OCR pipeline has excellent coverage (59+ calls)
- Column detection pipeline now has logging (added Session 284)
- Log files: app_session.log, ocr.log, pdf_import.log, sync.log, database.log, auth.log, navigation.log, errors.log, ui.log

### Agent Usage Patterns
- User prefers ALL work done via agents - research, implementation, testing
- Use parallel agents when tasks are independent
- pdf-agent for PDF analysis; frontend-flutter-specialist-agent for Dart code changes
- code-review-agent for verification; qa-testing-agent for testing
- Agents sometimes revert each other's changes - verify file state after parallel agent runs
- **FIXED (2026-02-11)**: All agents now have `permissionMode: acceptEdits` to prevent file-write failures
- Global `~/.claude/settings.json` has `"defaultMode": "acceptEdits"` so built-in subagents inherit it
- Known Claude Code Windows bugs: #4462, #7032, #5465 - subagent file writes may not persist
- Context handoff: subagents start fresh - always pass full context in Task prompt or write to `.claude/plans/`

### Dart/Flutter Gotchas
- Raw strings `r'...'` cannot contain single quotes - use `\x27` instead
- Pre-existing test failure: table_locator_test "rejects section heading" (expects Y=1700, gets 1610)
- post_process_normalization.dart `cleanOcrArtifacts()` removes commas from text (regex `[;:,!]`)

### CRITICAL: Memory File Location
- **ALWAYS** use `.claude/memory/MEMORY.md` (project dir), NOT the auto-memory dir
- Wrong: `C:\Users\rseba\.claude\projects\...\memory\MEMORY.md`
- Right: `C:\Users\rseba\Projects\Field Guide App\.claude\memory\MEMORY.md`
