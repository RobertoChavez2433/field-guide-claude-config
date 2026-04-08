Date: 2026-04-06
Author: Codex
Status: Active
Parent: `2026-04-06-ocr-per-page-optimization-plan.md`

## End Goals

- preserve the current persistent worker-pool architecture
- reduce page-local OCR work instead of revisiting worker transport
- keep Springfield at `131/131` with exact checksum and no bogus rows
- create a measured path toward `< 60s` with lower OCR call volume

## Hard Stop Scope

This TODO is complete when:
- the next refactor seam exists for lower-overhead OCR result formats
- an alternate per-page recognition strategy can be added without touching worker orchestration again
- the first lower-call-count recognizer experiment is clearly scoped

This TODO does not include:
- switching OCR engines
- another worker-pool redesign
- speculative global crop retuning
- raw-grid visual gating expansion

## Execution Queue

1. Lock the measured page-local bottleneck.
- Record the latest Springfield numbers in the plan.
- Make the call-volume problem explicit: `822` crops, `854` OCR calls, only `20` retries.

2. Add a lower-overhead OCR output seam.
- Completed 2026-04-06:
- Support a direct word-box result mode in the OCR engine/config layer.
- Keep HOCR as the default path until the alternate recognizer is proven.

3. Split page-recognition shape from OCR output format.
- Keep the current cell recognizer intact.
- Add a seam for alternate page-local recognition strategies so experiments do not rework `TextRecognizerV2` again.

4. Prepare the first lower-call-count experiment.
- Scope a row-banded proof with x-based column assignment and explicit cell fallback.
- Protect item-number and numeric-column correctness gates up front.

5. Re-verify locally.
- analyzer green on touched OCR files
- engine/config tests green
- strategy seam tests green

## Follow-On Queue

1. Implement the first opt-in row-banded page recognizer proof.
2. Measure S25 Springfield with:
- current cell path
- row-banded proof
- fallback counts
- OCR call-count deltas
3. Reject or keep the proof based on Springfield gates first, runtime second.
