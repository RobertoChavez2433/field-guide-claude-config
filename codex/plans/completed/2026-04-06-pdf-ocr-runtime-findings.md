# PDF OCR Runtime Findings

Date: 2026-04-06
Scope: Springfield Android OCR/PDF extraction runtime and fidelity

## Local Findings

- The protected baseline is the Android Springfield run that returns `131/131` with exact checksum `$7,882,926.73`.
- The current faster branch is materially faster but regresses to `130/131` with checksum `$7,880,946.73`.
- The regression is localized to item-number OCR, not a broad parser failure.
- Known bad rows in the current fast run:
  - page 2, row 4: blank item-number for item `9`
  - page 4, row 3: item number misread as `62 B`
  - one downstream bogus row is emitted
- The checksum miss is exactly `$1,980.00`, matching the missing item `9` amount.

## Runtime Findings

- `text_recognition` is the dominant bottleneck at `102457 ms` in the fast Android run.
- That is about `80.3%` of the observed wall time.
- Image preprocessing is second at `16888 ms`, far behind OCR.
- Retry overhead is not the main cost:
  - total OCR calls: `850`
  - cells OCR'd: `822`
  - retries attempted: `18`
  - retries succeeded: `2`

## Pipeline Findings

- OCR cell recognition is effectively serialized today.
- [ocr_grid_page_recognition_stage.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/stages/ocr_grid_page_recognition_stage.dart#L138) iterates cells in a plain `for` loop and awaits both first-pass OCR and retry resolution.
- Tesseract pooling in [tesseract_engine_v2.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart#L312) avoids re-init churn but does not parallelize work.
- `effectiveDpi` is metadata only in [tesseract_engine_v2.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart#L109). Real OCR behavior is driven by crop dimensions, image bytes, PSM, and retry policy.
- The current crop upscaler uses `400` DPI default and `450` DPI for descriptions in [crop_upscaler.dart](C:/Users/rseba/Projects/Field_Guide_App/lib/features/pdf/services/extraction/shared/crop_upscaler.dart#L24).
- Scaling is uniform by render DPI ratio and does not adapt to crop geometry or character size.

## Gate Findings

- `quality_status = autoAccept` is not sufficient to protect the Springfield baseline.
- The bad `130/131` run still ends as `autoAccept`.
- The integration harness currently relies on:
  - regression vs previous baseline
  - weak sanity checks
- It does not currently enforce:
  - exact `131` item count
  - exact checksum
  - zero bogus rows
  - survival of known-risk item numbers such as `9` and `62`

## Research Summary

### Tesseract docs

- ImproveQuality: image preparation, rescaling, borders, and segmentation choice heavily affect OCR quality.
  - https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
- Command-Line-Usage: page segmentation mode should match the expected crop layout.
  - https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html
- FAQ: repeated recognition with the same API instance can be affected by adaptive learning; `classify_enable_learning=0` is a documented consistency lever.
  - https://tesseract-ocr.github.io/tessdoc/FAQ.html
- Benchmarks and data files: `tessdata_fast` is materially faster than `tessdata_best`, but this is explicitly an accuracy tradeoff.
  - https://tesseract-ocr.github.io/tessdoc/Benchmarks.html
  - https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html

### Community guidance

- Willus Dotkom's Tesseract thread is directly relevant: practical OCR quality tracks character pixel height more than nominal DPI, and larger rendered glyphs can degrade recognition.
  - https://groups.google.com/g/tesseract-ocr/c/Wdh_JJwnw94

## Practical Conclusions

- Sub-`60s` is not realistic from parser changes or retry trimming alone.
- The next safe engineering order is:
  - harden the Springfield correctness gate
  - recover the item-number lane
  - then reclaim runtime with selective OCR input sizing
  - only later evaluate bounded OCR parallelism and higher-risk Tesseract configuration changes

## Iteration Result

First Codex iteration after this analysis:
- strict Springfield gate added to the integration harness
- item-number crops now use a protected higher target DPI lane
- alpha-contaminated item numbers now force retry

Observed local result on Windows using the Springfield PDF fixture:
- `131/131`
- exact checksum
- no bogus rows
- duration about `89s`
- `text_recognition` about `74965 ms`

Observed Android result on `sm-s938u` using the debug-server URL fixture path:
- `131/131`
- exact checksum `$7,882,926.73`
- no bogus rows
- strict Springfield gate passes even with `NO_GATE=true`
- duration about `91s` in the plain run
- `text_recognition` about `72411 ms` in the plain run

Observed Android debug-artifact run on `sm-s938u`:
- `131/131`
- exact checksum
- no bogus rows
- duration about `95s`
- `text_recognition` about `75837 ms`
- total OCR calls `854`
- cells OCR'd `822`
- retries attempted `20`
- retries succeeded `2`
- average OCR width `548.985`
- average OCR height `144.895`
- average scale factor `1.389`

Artifact paths from the confirmed S25 debug run:
- `tools/debug-server/artifacts/springfield-sm-s938u-report.json`
- `tools/debug-server/artifacts/springfield-sm-s938u-scorecard.md`
- `tools/debug-server/artifacts/springfield-sm-s938u-stage-trace-summary.json`

What this proves:
- the first iteration fixes the known `9` and `62` failures on Windows
- the first iteration also generalizes to the S25 Android device
- the strict gate passes even with `NO_GATE=true`, which is the intended behavior

What it does not prove yet:
- sub-`60s` remains unresolved

## Later Iterations

### Wide-description fallback was rejected

Validated on `sm-s938u`:
- correctness stayed green at `131/131`
- runtime regressed to about `109s` in the plain run
- traced run regressed to about `116s`
- `text_recognition` rose to about `90215 ms`
- OCR call volume stayed flat at `854`
- retries stayed flat at `20/2`
- average OCR width fell to about `524.186`
- average scale factor fell to about `1.361`

Conclusion:
- the change reduced pixel budget but made recognition harder per crop
- this was a bad performance trade and was reverted

### Adaptive learning disabled is retained

Engine-level change retained:
- `classify_enable_learning=0` is now applied to each pooled Tesseract lane

Observed S25 result after keeping only the adaptive-learning change:
- `131/131`
- exact checksum
- no bogus rows
- duration about `113s`
- `text_recognition` about `91284 ms`

What this means:
- disabling adaptive learning did not harm the protected Springfield output
- the runtime gain is modest at best
- this is useful mainly as a consistency guard, not a path to `<= 60s`

### First-pass structured whitelists were rejected

Experiment:
- applied first-pass whitelists to item-number, unit, and numeric data rows while leaving headers unfiltered

Observed S25 result:
- regressed to `130/131`
- item `9` went back to `MISS`
- runtime stayed poor at about `116s`

Conclusion:
- structured first-pass whitelists are not safe in the current crop/PSM setup
- the experiment was reverted

## Current Best Reading

- The protected S25 path is green again after reverting the unsafe experiments.
- The current retained delta beyond the original recovery patch is only the adaptive-learning guard.
- S25 runtime is still materially variable across clean green runs, observed roughly from `91s` to `115s` without thermal throttling.
- Safe crop-budget and simple Tesseract-search-space tweaks have not produced meaningful wins without quality risk.
- The next serious runtime step likely needs structural change, most plausibly bounded OCR parallelism or another execution-model improvement.

## Failed Worker Prototype

### Bounded page-worker OCR is not viable in its current form

Experiment:
- prototype page-level OCR workers inside `TextRecognizerV2`
- serialize preprocessed page inputs into worker isolates
- keep serial page fallback if a worker reports failure

Observed S25 behavior on `sm-s938u`:
- pipeline reaches `STAGE_START stage=text_recognition pages=6`
- no `STAGE_COMPLETE stage=text_recognition` log is ever emitted
- the app remains alive and visible for several minutes with no extraction progress
- the Flutter tool eventually stops the app; the run exits as `did not complete`

Important negative evidence:
- earlier pipeline stages still complete normally
- there is no immediate Dart exception surfaced back to the harness
- the failure is a hang, not a fast correctness regression

Practical conclusion:
- the current worker-isolate integration should be treated as failed
- keep the prototype code disabled by default until a refactor proves a safe worker boundary
- do not spend more iteration time trying to tune this exact implementation

### Recovery after disabling the worker path

Recovery action:
- disable automatic page-worker activation in `TextRecognizerV2`

Recovered S25 result:
- Springfield gate passes again
- `131/131`
- exact checksum preserved
- no bogus rows
- plain harness duration about `109s`
- `text_recognition` about `85287 ms`

Interpretation:
- the hang is tied to the active worker path, not the earlier retained serial baseline
- the branch should remain on the protected serial path while the next refactor is designed

## Deeper Structural Analysis

### The current OCR call is synchronous on the active isolate

Local wrapper finding:
- `packages/flusseract/lib/tesseract.dart` exposes `Future<String> hocrText(...)`, but the body directly calls the native `HOCRText(handle)` function before returning.
- That means the expensive native OCR work still blocks the current Dart isolate.
- Consequence: `Future.wait` on the current isolate would not create real OCR overlap.

Practical implication:
- true OCR concurrency requires separate isolates or a deeper native worker model
- simple async fan-out inside `TextRecognizerV2` is not enough

### Two serialization layers exist today

Code-path findings:
- `TextRecognizerV2.recognize()` iterates pages sequentially.
- `OcrGridPageRecognitionStage.recognize()` then iterates cell-by-cell sequentially inside each page.

Practical implication:
- page-level overlap is the cleaner first structural boundary
- it preserves intra-page ordering, retry rules, and row parsing behavior
- it is lower risk than changing cell ordering inside a page

### OpenMP is already capped to one thread

Local runtime finding:
- `OcrRuntimeSetup.ensureConfigured()` already applies `OMP_THREAD_LIMIT=1` on Android and Windows.

Why this matters:
- the repo is already aligned with Tesseract guidance for “many images / many workers” mode
- the next step should not be another OpenMP tweak
- the next step should add outer concurrency on top of the existing `OMP_THREAD_LIMIT=1` cap

### Rendering is the isolate boundary, not OCR

Repo constraint:
- full-pipeline background execution was previously rejected because `pdfrx` rendering needs the Flutter engine context on the main isolate

But:
- OCR happens after rendering and preprocessing
- `flusseract` is an FFI wrapper, not a MethodChannel plugin
- so OCR-only worker isolates remain plausible even though page rendering cannot move

### Primary-source guidance matches this direction

Official Tesseract guidance:
- Release notes state Tesseract is thread-safe with multiple instances in parallel threads, with some remaining global control-parameter caveats.
- FAQ says repeated decoding with the same `TessBaseAPI` can yield inconsistent results and recommends `classify_enable_learning=0`.
- FAQ also says Tesseract 4 uses up to four CPU threads per page and specifically recommends `OMP_THREAD_LIMIT=1` when processing many images, with one Tesseract process per CPU core.

Mapped conclusion:
- separate OCR workers with separate `TessBaseAPI` instances are a documented fit
- the current repo already applies the `OMP_THREAD_LIMIT=1` side of that advice
- bounded page-level OCR workers are now the highest-signal next experiment
