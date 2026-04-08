# PDF OCR Runtime Stabilization Plan

Date: 2026-04-06
Branch: `sync-engine-refactor`
Owner: Codex
Status: Active

## Objective

Resume the OCR/PDF extraction optimization loop without losing the protected Springfield baseline.

Non-negotiable acceptance gates:
- Android Springfield extraction returns `131/131`
- Exact checksum match: `$7,882,926.73`
- No bogus rows
- No new visual regression in clean-grid / OCR-grid output
- `quality_status = autoAccept`, but this is no longer sufficient on its own

Performance goals:
- Phase 0 recovery goal: restore the green Android baseline at or below the prior `~140s`
- Phase 1 target: `<= 120s` on the same Android Springfield run
- Phase 2 target: `<= 90s` only after the baseline is stable again
- Stretch target: `<= 60s` only if quality remains unchanged and the higher-risk execution changes prove stable

## Feasibility Note

The current fast Android run is `128s`, and `text_recognition` alone takes `102457 ms` or `80.3%` of wall time.

That means:
- sub-`60s` will not come from retry trimming, row parsing, or post-processing
- sub-`60s` is unlikely from crop-target tuning alone
- sub-`60s` probably requires a later execution-model change such as bounded OCR parallelism and/or another structural speedup

Inference: the correct order is to recover the green baseline first, then reclaim safe runtime, then evaluate the higher-risk work needed for the final stretch target.

## Current Known States

### Protected Green Baseline

Android Springfield on `sm-g996u` with the safer OCR crop target:
- `131/131`
- exact checksum match
- `autoAccept`
- runtime about `139927 ms`
- dominant stage: `text_recognition` at about `114583 ms`

This is the correctness baseline to protect.

### Current Faster Candidate

Android Springfield on `sm-g996u` with the current `400/450` crop target split:
- `130/131`
- checksum `$7,880,946.73`
- duration `128s`
- `text_recognition = 102457 ms`
- total OCR calls `850`
- cells OCR'd `822`
- retries attempted `18`
- retries succeeded `2`
- dominant issue: item-number fidelity regression

Observed failures from the uploaded artifacts:
- item `9` is missing because the item-number cell OCR came back blank
- item `62` is misread as `62 B`
- one bogus row is emitted downstream

Important artifact paths:
- `tools/debug-server/artifacts/springfield-sm-g996u-report.json`
- `tools/debug-server/artifacts/springfield-sm-g996u-scorecard.md`
- `tools/debug-server/artifacts/springfield-sm-g996u-stage-trace.json`
- `tools/debug-server/artifacts/springfield-sm-g996u-stage-trace-summary.json`

### First Iteration Result

The first Codex iteration after this plan:
- added a strict Springfield acceptance gate to the integration harness
- restored a protected higher-DPI lane for item-number crops
- forced retry on alpha-contaminated item-number tokens such as `62 B`

Verified local Windows result against the Springfield PDF fixture:
- `131/131`
- exact checksum `$7,882,926.73`
- no bogus rows
- duration about `89s`
- `text_recognition` about `74965 ms`

What this means:
- the first patch set is directionally correct
- the known `9` and `62` failures are resolved on Windows
- Android validation was still required before this iteration could be considered closed

### Android Confirmation On S25

Confirmed Android validation on `sm-s938u` using the debug-server URL input path:
- `131/131`
- exact checksum `$7,882,926.73`
- no bogus rows
- strict Springfield gate passes even with `NO_GATE=true`
- plain harness duration about `91s`
- plain `text_recognition` about `72411 ms`

Confirmed Android debug-artifact run on `sm-s938u`:
- `131/131`
- exact checksum
- no bogus rows
- duration about `95s`
- `text_recognition` about `75837 ms`
- total OCR calls `854`
- cells OCR'd `822`
- retries attempted `20`
- retries succeeded `2`

This closes the first recovery iteration on Android as well as Windows.

### Current Runtime-Only Candidate

The next code change under test is no longer the wide-description fallback.

Outcome of that experiment:
- validated on `sm-s938u`
- kept `131/131`
- increased runtime to about `109s` plain and `116s` traced
- raised `text_recognition` instead of lowering it
- was reverted

Current retained runtime/config delta after later iterations:
- keep the item-number protection and alpha-contamination retry recovery
- keep `classify_enable_learning=0` on pooled Tesseract lanes
- do not keep the wide-description fallback
- do not keep first-pass structured whitelists

Latest confirmed S25 green rerun on the retained config:
- `131/131`
- exact checksum `$7,882,926.73`
- no bogus rows
- duration about `113s`
- `text_recognition` about `91284 ms`

Interpretation:
- the pipeline is green again after reverting the unsafe experiments
- the adaptive-learning guard is safe to keep
- the remaining gap to the earlier `~91-95s` S25 run is too large to close with simple crop-target or whitelist tweaks alone

### Deeper Execution Analysis

The next phase should treat the execution model, not crop heuristics, as the primary lever.

Confirmed local constraints:
- page OCR is serialized in `TextRecognizerV2`
- cell OCR is serialized again inside `OcrGridPageRecognitionStage`
- `flusseract` OCR calls are synchronous native calls on the current isolate, despite returning `Future<String>`
- `OMP_THREAD_LIMIT=1` is already applied on Android and Windows by `OcrRuntimeSetup`

Implication:
- `Future.wait` on the main isolate will not deliver real OCR parallelism
- further micro-tuning of crop DPI, whitelists, or retry heuristics is unlikely to close the runtime gap safely
- the next credible speedup path is bounded OCR worker isolates after rendering/preprocessing completes

## Pipeline Analysis

### What Is Actually Slow

The wall-time distribution is clear:
- `text_recognition` dominates at `80.3%`
- image preprocessing is a distant second at `13.2%`
- everything after OCR is effectively noise compared to OCR cost

The main OCR path is also still serialized:
- `OcrGridPageRecognitionStage.recognize()` loops cell-by-cell in a plain `for` loop
- each cell awaits OCR before moving to the next
- Tesseract instance pooling only avoids re-init churn; it does not parallelize work

Conclusion: later performance work must focus on OCR execution and OCR input size, not parser stages.

### What Actually Regressed

The regression is localized and diagnosable:
- page 2, row 4, item-number cell is blank for "Clearing & Grubbing" even though the rest of the row is correct
- page 4, row 3 item number becomes `62 B`, which then fails item-number parsing
- checksum is short by exactly `$1,980.00`, matching the missing item 9 row

This points to upstream OCR fidelity, not downstream row grouping or math logic.

### Why The Faster Branch Regressed

The current code confirms the main risk:
- default crop target is now `400`
- description crop target is `450`
- scaling is driven by `renderDpi -> targetDpi`
- scaling does not adapt to crop geometry or observed character size

The likely failure mode is:
- narrowing the default crop target reduced the pixel budget for narrow numeric cells
- the first place this breaks is the item-number lane, where tiny tokens have little redundancy

### What Is Not The Root Cause

These are not the primary issues:
- page rendering
- grid detection
- row parsing
- retry count overhead
- full-page fallback behavior

Evidence:
- only `18` retries were attempted across `822` OCR'd cells
- only `2` retries succeeded
- the performance problem is baseline OCR cost, not retry amplification

### Important Implementation Constraints

Two local code facts matter for the next iterations:

1. `effectiveDpi` is metadata only
- it is passed into coordinate metadata
- it does not change Tesseract recognition behavior directly
- actual fidelity and runtime are governed by crop pixel width, crop pixel height, PNG payload, PSM choice, and retry count

2. `autoAccept` is not a reliable correctness gate
- the bad `130/131` run still ended in `autoAccept`
- Springfield needs an explicit artifact-level comparator for item count, checksum, and bogus rows

## Tesseract Guidance Mapped To This Pipeline

Current Tesseract documentation and community guidance line up well with the local evidence.

### High-signal guidance

- Tesseract quality is sensitive to image preparation, rescaling, borders, and segmentation choice
- page segmentation mode must match the text layout
- Tesseract is not good at table recognition on its own, so custom segmentation is normal and necessary
- whitelists and dictionary controls can help when the input is codes, digits, or structured tokens instead of natural language
- `tessdata_fast` is materially faster than `tessdata_best`, but this is an explicit quality tradeoff
- reusing the same `TessBaseAPI` across many images can interact with the adaptive classifier; the FAQ suggests disabling learning with `classify_enable_learning=0` when consistency matters
- more rendered DPI is not automatically better; practical accuracy correlates strongly with character pixel height, and oversized glyphs can degrade results

### What That Means Here

Mapped to this codebase:
- the existing PSM strategy is directionally correct and should not be replaced wholesale
- the crop-prep policy is the first place to optimize because our table segmentation is custom and already the main control point
- selective per-column or per-cell scaling is more promising than a single global target
- item-number cells should be treated as a protected lane with stricter validity checks
- switching to `tessdata_fast` is too risky before all quality gates are hardened
- adaptive-learning experiments are possible later because the wrapper already exposes `setVariable()`

## Non-Negotiable Guardrails To Add

Before further speed work, harden the regression gates.

Required guardrails:
- Springfield Android run must assert `131` items exactly
- Springfield Android run must assert exact checksum `$7,882,926.73`
- Springfield Android run must fail on bogus rows
- Springfield Android run must specifically confirm item `9` and item `62` survive
- clean-grid and OCR-grid artifact diff must be reviewed for the known problem rows

Test and harness additions:
- add a strict Springfield artifact comparator around the debug-server report output
- add unit coverage for item-number retry on alpha-contaminated tokens such as `62 B`
- add unit coverage for blank-item-number recovery conditions
- add a focused fixture or golden-style diagnostic check for the two known bad cells if practical

## Workstreams

## Workstream A: Recover Correctness First

Goal:
- get back to `131/131` without regressing runtime back beyond the old green baseline

Primary experiments in order:

1. Raise protection for item-number crops
- preferred direction: stop using the current lower default crop target for the item-number lane
- options:
  - raise the default target modestly, likely into the `425-450` range
  - or keep the default lane lower and give column `0` its own protected target floor
  - or define a minimum OCR width/height floor for item-number crops regardless of page render DPI

2. Tighten item-number retry entry conditions
- current retry logic triggers mainly on short tokens and low-confidence cases
- add a forced retry path when item-number OCR contains alpha contamination or an invalid item-number pattern
- `62 B` should not be accepted without at least one stricter retry

3. Add a small controlled border to item-number crops
- use a modest white border only for narrow item-number crops
- keep it small; Tesseract docs note borders can help, but oversized borders can also hurt

4. Keep description protection intact
- description OCR is not the main regression source
- do not lower description-target fidelity while recovering the item-number lane

Stop condition:
- Springfield Android returns `131/131`
- exact checksum matches
- no bogus row remains

## Workstream B: Make Quality Regressions Impossible To Miss

Goal:
- make the protected baseline machine-enforced, not memory-enforced

Required changes:
- hard fail the Springfield integration path when artifact outputs disagree with the ground truth on count or checksum
- emit a focused failure summary naming missing item numbers and bogus rows
- make it easy to compare a candidate report against the last protected baseline artifact

Reason:
- the current `quality_status` logic can still call a visibly bad extraction `autoAccept`
- that is acceptable as a heuristic score, but not as the final release gate

## Workstream C: Safe Runtime Wins After Green Is Restored

Goal:
- reduce OCR cost without touching the recovered quality baseline

Best candidates:

1. Replace fixed crop targets with geometry-aware sizing
- current scaling ignores the actual crop dimensions
- use per-column and per-crop rules based on observed width and height
- preserve a minimum pixel floor for narrow numeric cells
- cap unnecessary oversizing for wider easy cells

Current first candidate in this workstream:
- keep the protected item-number lane intact
- preserve the higher-DPI description lane
- use adaptive-learning disablement as a consistency guard, not as a major speed lever
- treat further micro-tuning experiments as low-confidence unless they produce repeated green S25 wins

Revised next candidate:
- prototype bounded page-level OCR overlap after page rendering and preprocessing
- each worker should own its own Tesseract engine instances
- keep per-page ordering deterministic and aggregate page outputs by page index
- retain a fallback path to the current serial behavior if worker OCR fails

Result of the first prototype:
- current page-worker implementation is not viable on `sm-s938u`
- the run reaches `text_recognition` and then hangs indefinitely until the tool stops the app
- automatic worker activation is now disabled again to protect the green baseline

Updated implication:
- the next parallelism attempt needs a refactor-level design, not another patch on the current `compute()` prototype
- likely focus: isolate-safe worker contracts, explicit lifecycle/logging, and a much smaller first proof before touching the full Springfield path

2. Separate protected lanes from cheap lanes
- item numbers are high-risk and low-bandwidth
- quantity, unit, price, and amount cells may be able to run with narrower targets once the validity checks are hardened

3. Bounded OCR parallelism
- prefer page-level over cell-level as the first structural cut
- page-level overlap minimizes behavior change inside each page
- do not attempt this with plain `Future.wait` on the main isolate; actual isolate workers are required
- the point is selective shrinking, not global shrinking

3. Verify diagnostic overhead separately from pipeline cost
- trace upload, artifact upload, and verbose diagnostics are useful for iteration
- they should not be confused with the production-like runtime target
- keep using the diagnostic harness for comparisons, but validate final runtime in a lower-overhead mode too

4. Trim avoidable OCR work only where impact is real
- header reuse across repeated pages may save a little
- retry-count trimming will not save much because retries are already rare
- downstream parser optimization is not worth prioritizing

## Workstream D: Structured Tesseract Configuration Experiments

Goal:
- test Tesseract options that may improve stability or lane-specific accuracy without changing the architecture yet

Candidate experiments:

1. Disable dictionary DAWGs for structured numeric lanes
- test `load_system_dawg=0`
- test `load_freq_dawg=0`
- apply only to numeric/code-like lanes, not descriptions

2. Disable adaptive learning for consistency experiments
- test `classify_enable_learning=0`
- important because this pipeline reuses pooled Tesseract instances across many crops
- compare both quality and runtime against the protected baseline

3. Wire `oemMode` only if a concrete experiment justifies it
- the config object carries it today, but the engine does not use it
- this is not a first-line optimization

These experiments are medium risk and should happen only after Workstreams A and B are complete.

## Workstream E: High-Risk Work Needed For The `<= 60s` Stretch

Goal:
- determine whether the final stretch target is possible without quality loss

Reality check:
- current OCR is effectively serial
- with `102s` inside OCR alone, the only realistic path toward `<= 60s` is a structural speedup

Likely candidates:

1. Bounded OCR parallelism
- parallelize at the page level, lane level, or batched cell level
- keep worker count conservative
- each worker should own isolated Tesseract instances rather than sharing one mutable pool

2. Dedicated OCR worker isolates
- offload OCR from the main isolate
- use small fixed worker counts and preserve deterministic ordering in aggregation

3. Only then consider model-level tradeoffs
- `tessdata_fast` or other model swaps are last-resort experiments
- they are incompatible with the current "no quality loss" requirement unless proven otherwise by the full Springfield gate

Entry criteria for this phase:
- baseline already green
- safer runtime wins already harvested
- diagnostic and production-like timing both plateau above the target

Exit criteria:
- `131/131`
- exact checksum
- no visual regression
- stable repeated runs on Android
- measured runtime improvement large enough to matter, not just noise

## Explicit "Do Not Prioritize" List

Do not spend the next iteration on:
- broad parser rewrites
- row-grouping speculation
- full-page fallback redesign
- whole-pipeline refactors unrelated to OCR
- model swaps before quality gates are strict
- retry micro-optimizations as a primary speed strategy

## Experiment Queue

Ordered next experiments:

1. Re-run Android Springfield after the first gate and item-number recovery patch
2. If Android is green, lock the new baseline and record runtime deltas versus `~140s` and `128s`
3. If Android is not green, inspect the remaining misses and tighten item-number recovery again
4. Test small item-number border padding if narrow-cell fidelity still fails
5. Once Android is green, replace fixed scaling with geometry-aware per-lane scaling
6. Measure diagnostic mode versus lower-overhead runtime
7. Only then evaluate adaptive-learning and DAWG experiments
8. Only after that, prototype bounded OCR parallelism

Updated state:
- the first bounded OCR parallelism prototype has already been attempted and failed by hanging on-device
- the next iteration should analyze refactor options for `TextRecognizerV2` rather than retrying the same worker wiring

## Expected File Targets

Primary code targets:
- `lib/features/pdf/services/extraction/shared/crop_upscaler.dart`
- `lib/features/pdf/services/extraction/stages/ocr_crop_preparation_stage.dart`
- `lib/features/pdf/services/extraction/stages/ocr_retry_resolution_stage.dart`
- `lib/features/pdf/services/extraction/stages/ocr_cell_policy.dart`
- `lib/features/pdf/services/extraction/stages/ocr_grid_page_recognition_stage.dart`
- `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart`
- `lib/features/pdf/services/extraction/ocr/tesseract_config_v2.dart`

Primary test and harness targets:
- `test/features/pdf/extraction/shared/crop_upscaler_test.dart`
- `test/features/pdf/extraction/stages/ocr_crop_preparation_stage_test.dart`
- `test/features/pdf/extraction/stages/ocr_text_recognizer_test.dart`
- add or extend retry-resolution tests for item-number invalid-token recovery
- `integration_test/springfield_report_test.dart`

## Verification Commands

Primary Android verification loop:

```powershell
adb -s RFCNC0Y975L reverse tcp:3947 tcp:3947
flutter test integration_test/springfield_report_test.dart -d RFCNC0Y975L `
  --dart-define=NO_GATE=true `
  --dart-define=DEBUG_SERVER=true `
  --dart-define=TRACE_TO_DEBUG_SERVER=true `
  --dart-define=TRACE_ARTIFACTS=true `
  --dart-define=TRACE_UPLOAD_ARTIFACTS=true `
  --dart-define=DEBUG_SERVER_URL=http://127.0.0.1:3947 `
  --dart-define=DEVICE_MODEL=sm-g996u `
  --dart-define=SPRINGFIELD_PDF_URL=http://127.0.0.1:3947/artifact/springfield_pay_items.pdf `
  --dart-define=SPRINGFIELD_GROUND_TRUTH_URL=http://127.0.0.1:3947/artifact/springfield_ground_truth_items.json
```

Secondary checks after each iteration:
- compare scorecard item flow against the protected baseline
- confirm item `9` and item `62` in the clean grid
- confirm no `BOGUS_*` rows appear
- record `text_recognition` time and total OCR calls

## End State

The desired end state is not "the fastest run."

The desired end state is:
- Springfield remains green at `131/131`
- checksum remains exact
- clean-grid output remains visually stable
- OCR runtime falls materially below the current green baseline
- the pipeline has an explicit quality gate strong enough to prevent another silent `130/131 autoAccept`

Practical expectation:
- the next iteration should restore correctness and harden gates
- the following iterations should reclaim safe runtime
- the `<= 60s` target should be treated as a later engineering phase, not a promise from crop tuning alone

## External References

Primary guidance used for this plan:
- Tesseract docs: ImproveQuality
- Tesseract docs: Command-Line-Usage
- Tesseract docs: FAQ
- Tesseract docs: Benchmarks
- Tesseract docs: Data Files in different versions
- Tesseract community discussion: Willus Dotkom on optimal image resolution
