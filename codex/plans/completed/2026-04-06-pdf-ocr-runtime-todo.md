# PDF OCR Runtime TODO

Date: 2026-04-06
Status: Active

## Immediate

- Keep the current green S25 state intact:
  - strict Springfield gate passes
  - `131/131`
  - exact checksum
  - no bogus rows
- Record repeated S25 runs to quantify runtime variance under the current retained config.
- Compare clean repeated runs against the earlier `~91-95s` S25 recovery baseline.
- Preserve the rule that the S25 is the active test device and do not use the S21.
- Prototype the next structural runtime cut at the OCR execution layer, not via more crop tuning.
- Keep automatic OCR page workers disabled until a refactor proves an isolate-safe design.

## Current OCR Recovery Iterations

- Protected the item-number lane from the reduced crop target.
- Forced retry for alpha-contaminated item-number tokens such as `62 B`.
- Re-score item-number retries so invalid first-pass tokens are less sticky.
- Rejected and reverted: wide-description fallback to the default OCR lane.
- Retained: disable Tesseract adaptive learning with `classify_enable_learning=0`.
- Rejected and reverted: first-pass structured whitelists on data rows.
- Consider small item-number-only border tuning only if a later runtime change reopens the numeric-lane risk.
- Rejected: first bounded page-worker OCR prototype. It hangs on the S25 during `text_recognition`.

## After Green Baseline Is Restored

- Replace global OCR scaling with geometry-aware per-lane scaling.
- Separate measurement of debug-artifact overhead from plain harness runtime on the S25.
- Measure debug artifact overhead separately from lower-overhead timing.
- If another Tesseract-variable experiment is attempted, treat it as opt-in and verify on S25 first:
  - `load_system_dawg=0`
  - `load_freq_dawg=0`
- Confirm isolate viability for OCR-only workers after rendering/preprocessing.
- Do not retry the current `compute()` worker wiring as-is.
- Design a `TextRecognizerV2` refactor that separates:
  - page orchestration
  - page execution strategy
  - worker payload serialization
  - worker lifecycle and logging
- Validate any future worker design with a narrow two-page proof before rerunning full Springfield.

## Later Stretch Work

- Expand bounded OCR parallelism only after the first worker prototype stays green on the S25.
- Verify deterministic aggregation and repeated-run stability on Android.
- Measure per-run variance before and after any structural parallelism change.
- Re-evaluate the `<= 60s` target only after quality is stable across repeated runs.
