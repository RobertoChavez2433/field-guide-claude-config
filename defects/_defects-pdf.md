# Defects: PDF

Active patterns for pdf. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [DATA] 2026-03-15: Crop Boundaries at Grid Line Centers Include TELEA Interpolation Artifacts (Session 570)
**Pattern**: `_computeCellCrops` places crop edges at `GridLine.position` (grid line center). `cv.inpaint` TELEA at mask boundary produces gray pixels (not white). Both adjacent cells include the center pixel via `floor`/`ceil` rounding. After 2x OCR upscale, 1-2px gray stripes become pipe `|` artifacts (18.3% avg edge dark fraction). The docblock comment "no inset needed because inpainting makes it clean" is provably false.
**Prevention**: Inset crop edges by `(halfWidth + fringe + 1px safety)` beyond the grid line center, using per-line fringe measurements threaded from grid_line_remover. Plan ready at `.claude/plans/2026-03-14-fringe-edge-crop-boundaries.md`.
**Ref**: @lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:1175-1219

### [DATA] 2026-03-15: halfThick Formula Mismatch Between Scanner and cv.line (Session 570)
**Pattern**: `_measureLineFringe` used `line.thickness ~/ 2` for halfThick, but `cv.line()` uses `(thickness + 1) ~/ 2` for its actual half-extent. For odd thicknesses (T=3, most common), the scanner started probing inside the line body, all samples were skipped, fringe reported as 0 → no mask expansion → fringe residue survived.
**Prevention**: Always use `(thickness + 1) ~/ 2` to match cv.line's pixel half-extent. The `centerShift` asymmetric correction was also contradictory with `maxFringeSide` symmetric expansion — don't combine two compensation strategies that fight each other.
**Ref**: @lib/features/pdf/services/extraction/stages/grid_line_remover.dart:855

### [DATA] 2026-03-14: Anti-Aliased Fringe Band (128-200) Survives Binary Threshold and Causes Phantom OCR Elements (Session 567)
**Pattern**: Grid line removal mask uses detector `widthPixels` from binary threshold (128), but anti-aliased fringe pixels (grayscale 128-200) survive thresholding and remain in OCR crops. Tesseract reads these as `|`, `CB`, `Be`, `®`, etc., creating +150 phantom elements that cascade into item loss (105→82).
**Prevention**: Measure fringe dynamically from the grayscale image (scan perpendicular to each line, detect 128-200 band pixels), expand removal mask to cover. Use dual-boundary stop (>=200 OR <128) to avoid counting intersection pixels as fringe.
**Ref**: @lib/features/pdf/services/extraction/stages/grid_line_remover.dart, `.claude/specs/2026-03-14-dynamic-fringe-removal-spec.md`

### [E2E] 2026-03-14: Wave-1 Grid Tuning Must Be Reversible Until Springfield Beats Baseline (Session 566)
**Pattern**: Conservative fringe-expansion and text-protected removal changes in `GridLineRemover` materially regressed the real Springfield extraction before any upstream gain was proven. The run recovered only after grid-removal behavior was rolled back while leaving diagnostics in place.
**Prevention**: Treat Stage `2B-ii.6` tuning as experimental until both the cell harness and Springfield improve over the archived pre-wave baseline. Keep diagnostics, but revert behavioral tuning immediately when control columns or item totals regress.
**Ref**: @lib/features/pdf/services/extraction/stages/grid_line_remover.dart

### [DATA] 2026-03-15: _buildCell() Left-to-Right Sort Scrambles Wrapped Descriptions (Session 574)
**Pattern**: `CellExtractorV2._buildCell()` sorts OCR fragments by `boundingBox.left` only. When a description wraps to two lines within one grid cell, line 2 words (lower X) interleave before line 1 words, producing scrambled text like `"Allowance) Private Property Landscape Repair (Cash"` instead of `"Private Property Landscape Repair (Cash Allowance)"`.
**Prevention**: Sort Y-first (using Y-band tolerance = 0.5 * median fragment height), then X within each band. This preserves reading order for multi-line cells without breaking single-line text with baseline jitter.
**Ref**: @lib/features/pdf/services/extraction/stages/cell_extractor_v2.dart:528

### [DATA] 2026-03-09: BLOCKER-35 — Cross-Device Checksum Divergence $500K (Session 530)
**Pattern**: After pdfrx migration, both Windows and S25 Ultra extract 130 items (item count parity achieved), but computed checksums diverge by $500K: Windows=$7,602,768.73, S25=$8,102,768.73. OCR element counts also differ slightly (1249 vs 1246). Specific differences: item 94 normalized as "Boy" (Windows) vs "Bey" (S25), item 108 qty changed on Windows but not S25.
**Root Cause**: Unknown. pdfrx uses same bundled PDFium on both platforms — pixel output should be identical. Hypotheses: (1) Tesseract OCR non-determinism across platforms, (2) preprocessing timing differences causing different image quality, (3) subtle pixel differences despite same PDFium (different CPU architecture, float precision). Need pixel-by-pixel comparison of rendered images + element-by-element OCR diff.
**Prevention**: Compare rendered page images byte-for-byte between devices. If pixels differ, root cause is in PDFium/platform. If pixels match, root cause is in Tesseract/preprocessing.
**Ref**: `test/features/pdf/extraction/device-baselines/post-migration/COMPARISON-REPORT.md`

### [DATA] 2026-03-09: R2 Plan Gap — First priceContinuation Path Unchecked (Session 527)
**Pattern**: `_isMinorTextContent` fix targets SECOND priceContinuation path (lines 281-298), but "Boy" row hits FIRST path (lines 265-278) because item-column text goes to `itemElements`, not `textPopulated`. First path checks `textPopulated.isEmpty` → true → classifies as priceContinuation before reaching the fix.
**Prevention**: Add `!itemElements.any((e) => e.text.trim().isNotEmpty)` guard to first priceContinuation path (line 267). Both paths must check for item-column text.
**Ref**: @lib/features/pdf/services/extraction/stages/row_classifier_v3.dart:265-278

<!-- Add defects above this line -->
