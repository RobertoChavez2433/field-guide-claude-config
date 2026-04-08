Date: 2026-04-06
Author: Codex
Status: Active
Scope: Reduce Springfield OCR runtime below the current worker-pool plateau by changing the per-page recognition shape, not the worker boundary.

## Why This Plan Exists

The persistent `2`-worker pool is no longer the main problem.

Latest measured S25 Springfield run:
- `131/131`
- exact checksum preserved
- no bogus rows
- total duration: `120s`
- `text_recognition`: `100715 ms`
- `image_preprocessing`: `13630 ms`
- worker bootstrap: `11 ms`
- worker total estimated queue time: `38 ms`

That means:
- worker startup is negligible
- worker transport is negligible
- queueing is negligible
- the remaining bottleneck is page-local OCR execution

The current grid OCR path still does:
- `822` planned cell crops
- `822` prepared crops
- `854` OCR calls
- only `20` retries total

Interpretation:
- retries are not the main runtime problem
- preprocessing is secondary
- the big lever is first-pass OCR call volume and per-call overhead

## Protected End Goals

These are non-negotiable:
- keep Springfield at `131/131`
- keep checksum at `$7,882,926.73`
- keep bogus rows at `0`
- do not regress the active worker-pool path
- preserve no-visual-regression intent, even if raw-grid gating still needs stronger automation

Stretch goal:
- create a credible path to `< 60s` on S25

## Current Pipeline Read

Relevant code:
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
- `lib/features/pdf/services/extraction/stages/ocr_page_recognition_executor.dart`
- `lib/features/pdf/services/extraction/stages/ocr_grid_page_recognition_stage.dart`
- `lib/features/pdf/services/extraction/stages/ocr_cell_recognition_stage.dart`
- `lib/features/pdf/services/extraction/stages/ocr_retry_resolution_stage.dart`
- `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart`
- `lib/features/pdf/services/extraction/shared/crop_upscaler.dart`

Current hot path:
1. decode preprocessed page once
2. plan all grid cell crops
3. copy each crop from the page image
4. upscale and pad each crop
5. PNG-encode each crop
6. OCR each crop
7. parse HOCR XML for each crop
8. map crop-relative words back to page coordinates
9. run retry OCR only on a narrow subset of cells

Why that matters:
- almost every cell still forces a full OCR call
- the worker pool only overlaps pages; it does not reduce work inside a page
- the cell loop is still strictly serial inside each worker

## Measured Constraints From Springfield

Measured from the latest green S25 worker-pool artifacts:
- `planned_cell_crops = 822`
- `total_ocr_calls = 854`
- `re_ocr_attempts = 20`
- `re_ocr_successes = 2`
- `psm7_calls = 780`
- `psm6_calls = 42`
- `psm8_calls = 13`
- `psm11_calls = 7`

Retry distribution:
- column `0` item number: `12`
- column `1` description: `7`
- column `4` unit price: `1`

Retry reasons:
- `short_token = 11`
- `short_or_noisy = 7`
- `malformed = 1`
- `low_confidence = 1`

Interpretation:
- item-number protection still matters for correctness
- description retries matter some, but not enough to dominate runtime
- retry reduction alone cannot deliver the needed wall-time cut

## Primary-Source Guidance Anchoring The Next Phase

Tesseract:
- FAQ:
  https://github.com/tesseract-ocr/tesseract/wiki/FAQ/ec7f89630d433163f88ef98df058a02d00d9fdd3
- Release notes:
  https://github.com/tesseract-ocr/tesseract/wiki/ReleaseNotes/7d40c6ba2d3619a5185666be9f920845d5920925
- ImproveQuality:
  https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
- Command-line usage:
  https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html
- Oversubscription issue:
  https://github.com/tesseract-ocr/tesseract/issues/3109
- Advanced API reference:
  https://tesseract-ocr.github.io/tessapi/3.x/a01281.html

Dart / Flutter:
- Dart isolates:
  https://dart.dev/language/isolates
- Flutter isolate performance:
  https://docs.flutter.dev/perf/isolates
- `TransferableTypedData`:
  https://api.dart.dev/dart-isolate/TransferableTypedData-class.html

Key implications for the next phase:
- keep the current worker model
- do not reintroduce shared-engine concurrency
- match PSM to the real crop or band layout
- exploit alternative result formats where full HOCR is not needed
- if using `SetRectangle` or other region-level recognition, treat it as a deliberate recognition-shape change, not a drop-in optimization

## Ranked Runtime Options

### Option 1: Row-banded OCR with x-based column assignment

Shape:
- OCR one row band at a time instead of six independent cells
- assign recognized words back into columns by x position using known grid boundaries
- fall back to per-cell OCR only when row-band confidence or structure is insufficient

Potential upside:
- replace roughly `822` first-pass cell calls with about `137` row calls
- largest credible call-volume reduction without collapsing all page structure into one OCR pass

Main risks:
- row bands may blur column boundaries for numeric fields
- row-level OCR can merge or reorder words across columns
- item-number and bid-amount fidelity must be explicitly protected

Assessment:
- highest upside
- medium to high regression risk
- best candidate once a lower-overhead result-format seam exists

### Option 2: Column-group or lane-banded OCR

Shape:
- combine only selected columns into shared OCR bands
- likely candidates:
  - description + unit
  - numeric trio (`quantity`, `unit_price`, `bid_amount`)

Potential upside:
- materially fewer first-pass calls than cell OCR
- lower risk than whole-row OCR because grouping can respect semantic similarity

Main risks:
- still needs word-to-column reassignment
- numeric lanes are sensitive to whitespace and decimal punctuation

Assessment:
- medium upside
- medium risk
- viable fallback if whole-row OCR proves too unstable

### Option 3: Full column-strip OCR per page

Shape:
- OCR one tall strip per page column
- assign words to rows by y overlap with known row boundaries

Potential upside:
- massive call reduction
- could bring first-pass calls down to about `36`

Main risks:
- highest layout-analysis burden
- long strips amplify line-merging and line-order ambiguity
- likely too fragile for Springfield numeric fidelity as a first attempt

Assessment:
- highest theoretical upside
- highest risk
- not the first experiment

### Option 4: Cheaper OCR result format for crops and future bands

Shape:
- stop using HOCR when bounding boxes are enough
- use direct word boxes / TSV-like word data instead of HOCR XML generation and XML parsing

Potential upside:
- reduces per-call overhead
- creates the right seam for future row or lane recognizers
- lower-risk refactor than changing the recognition geometry immediately

Main risks:
- smaller upside than reducing call volume
- still keeps one OCR call per crop if used alone

Assessment:
- low risk
- enabling refactor, not the final answer by itself
- should happen before bigger banding experiments

### Option 5: Retry minimization and more policy gating

Shape:
- reduce retry triggers
- tune malformed / low-confidence policies further

Potential upside:
- small

Why small:
- only `20` retries out of `854` OCR calls

Assessment:
- worthwhile only after bigger work
- not the next main path

### Option 6: Preprocessing-only optimization

Shape:
- reduce the `~13.6s` preprocessing stage

Potential upside:
- bounded by current preprocessing cost

Assessment:
- helpful later
- cannot solve the current gap alone

## Chosen Direction

The next phase should combine:
1. a lower-overhead OCR result-format seam
2. an alternate page recognition strategy that can try a lower-call-count recognition shape
3. explicit fallback back to the current per-cell path when structure confidence is not good enough

That means the immediate order is:
1. engine/result-format seam
2. alternate per-page recognition executor seam
3. row-banded proof behind opt-in config
4. S25 Springfield comparison against the protected cell path

## Progress Update

Completed in this worktree on 2026-04-06:
- added an explicit OCR output-format seam in `OcrConfigV2`
- kept HOCR as the protected default path
- added a direct word-box recognition path in `TesseractEngineV2` using
  `flusseract` bounding boxes for lower-overhead experiments
- extended focused OCR tests for config round-trip, word-box parsing, and
  failure diagnostics

Implication:
- the next OCR refactor slice should start from alternate page-recognition
  geometry, not from result-format plumbing

## Hard Scope Boundaries

This plan does not include:
- switching away from Tesseract
- introducing PaddleOCR
- reworking the worker pool again
- platform-specific OCR backends
- native extraction as the main Springfield path
- speculative global DPI retuning

## Completion Gates

Architecture gates:
- an alternate per-page recognition shape can be added without rewriting `TextRecognizerV2`
- OCR result-format choice is explicit and testable
- current cell OCR remains the default fallback path

Correctness gates:
- Springfield remains `131/131`
- checksum stays exact
- bogus rows stay at `0`
- item-number lane remains protected

Runtime gates:
- any new experiment must publish direct before/after call-count evidence
- any new experiment must publish direct S25 timing evidence
- future work should prefer “fewer OCR calls” over “same calls with more policy”

## Recommended First Implementation Slice

Start with the lowest-risk enabling refactor:
- support non-HOCR word-box output in the OCR engine/config path
- keep default Springfield behavior unchanged
- use that seam to power the first banded recognizer experiment later

Rationale:
- it preserves the protected path
- it avoids speculative geometry changes in the same slice
- it sets up the real runtime experiment instead of hard-coding HOCR as the only usable output
