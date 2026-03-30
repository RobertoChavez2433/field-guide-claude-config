# Defects: PDF

Active patterns for pdf. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [ASYNC] 2026-03-27: pdfrx rendering fails silently in background isolates (Session 659)
**Pattern**: `pdfrxFlutterInitialize()` and `PdfDocument.openData()` require the full Flutter engine context, not just `BackgroundIsolateBinaryMessenger`. In a worker isolate, page renders silently return null (caught by try/catch), pipeline completes instantly with 0 items. The `BackgroundIsolateBinaryMessenger.ensureInitialized()` fix from S580 was necessary but not sufficient.
**Prevention**: Do NOT run pdfrx rendering in background isolates. Either run the full pipeline on the main thread (current fix), or split architecture: render pages on main thread, pass images to worker isolate for OCR/parsing only.
**Ref**: @lib/features/pdf/services/extraction/stages/page_renderer_v2.dart:229-293, @lib/features/pdf/presentation/helpers/pdf_import_helper.dart

### [DATA] 2026-03-16: Background isolate missing BackgroundIsolateBinaryMessenger init (Session 580)
**Pattern**: `ExtractionJobRunner._workerEntryPoint()` did not call `BackgroundIsolateBinaryMessenger.ensureInitialized(rootIsolateToken)`. `pdfrx` uses platform channels for page rendering → all 6 pages failed with "Bad state: BackgroundIsolateBinaryMessenger.instance value is invalid". Extraction completed in 246ms with 0 items — silent total failure.
**Prevention**: ANY isolate that uses platform channels (pdfrx, path_provider, etc.) MUST call `BackgroundIsolateBinaryMessenger.ensureInitialized()` before any work. Pass `RootIsolateToken.instance!` via the init message.
**Ref**: @lib/features/pdf/services/extraction/runner/extraction_job_runner.dart:334

### [DATA] 2026-03-15: Crop Boundaries at Grid Line Centers Include TELEA Interpolation Artifacts (Session 570)
**Pattern**: `_computeCellCrops` places crop edges at `GridLine.position` (grid line center). `cv.inpaint` TELEA at mask boundary produces gray pixels (not white). Both adjacent cells include the center pixel via `floor`/`ceil` rounding. After 2x OCR upscale, 1-2px gray stripes become pipe `|` artifacts (18.3% avg edge dark fraction). The docblock comment "no inset needed because inpainting makes it clean" is provably false.
**Prevention**: Inset crop edges by `(halfWidth + fringe + 1px safety)` beyond the grid line center, using per-line fringe measurements threaded from grid_line_remover. Plan ready at `.claude/plans/completed/2026-03-14-fringe-edge-crop-boundaries.md`.
**Ref**: @lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:1175-1219

### [DATA] 2026-03-15: halfThick Formula Mismatch Between Scanner and cv.line (Session 570)
**Pattern**: `_measureLineFringe` used `line.thickness ~/ 2` for halfThick, but `cv.line()` uses `(thickness + 1) ~/ 2` for its actual half-extent. For odd thicknesses (T=3, most common), the scanner started probing inside the line body, all samples were skipped, fringe reported as 0 → no mask expansion → fringe residue survived.
**Prevention**: Always use `(thickness + 1) ~/ 2` to match cv.line's pixel half-extent. The `centerShift` asymmetric correction was also contradictory with `maxFringeSide` symmetric expansion — don't combine two compensation strategies that fight each other.
**Ref**: @lib/features/pdf/services/extraction/stages/grid_line_remover.dart:855

### [DATA] 2026-03-14: Anti-Aliased Fringe Band (128-200) Survives Binary Threshold and Causes Phantom OCR Elements (Session 567)
**Pattern**: Grid line removal mask uses detector `widthPixels` from binary threshold (128), but anti-aliased fringe pixels (grayscale 128-200) survive thresholding and remain in OCR crops. Tesseract reads these as `|`, `CB`, `Be`, `®`, etc., creating +150 phantom elements that cascade into item loss (105→82).
**Prevention**: Measure fringe dynamically from the grayscale image (scan perpendicular to each line, detect 128-200 band pixels), expand removal mask to cover. Use dual-boundary stop (>=200 OR <128) to avoid counting intersection pixels as fringe.
**Ref**: @lib/features/pdf/services/extraction/stages/grid_line_remover.dart, `.claude/specs/archived/2026-03-14-dynamic-fringe-removal-spec.md`


<!-- Add defects above this line -->
