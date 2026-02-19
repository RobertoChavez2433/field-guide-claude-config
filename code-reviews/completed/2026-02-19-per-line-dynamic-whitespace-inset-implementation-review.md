# Per-Line Dynamic Whitespace Inset - Implementation + Review

Date: 2026-02-19
Plan: `.claude/plans/2026-02-18-per-line-dynamic-whitespace-inset.md`

## Scope Executed

- Implemented width-driven inset computation and call-site wiring in:
  - `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
- Added/updated tests:
  - `test/features/pdf/extraction/stages/whitespace_inset_test.dart`
  - `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart`
- Regenerated Springfield fixtures via integration harness.

## What Changed

1. Added `_computeLineInset(...)` (dynamic per-line scan):
   - Width-aware depth/floor/cap math
   - Per-line local center correction
   - Dark-run then 2-white termination
   - 7-9 probes + p75 aggregation
2. Wired top/bottom/left/right inset decisions in `_recognizeWithCellCrops(...)` to measured line widths when present; retained legacy fallback scan when widths are missing.
3. Added safety guard `_capInsetPairForInterior(...)` to prevent over-consumption of crop span when width data is noisy (preserves at least 2px interior when possible).
4. Added Stage 2B integration tests to exercise:
   - Width-driven path with noisy width inputs
   - Missing-width fallback path behavior
5. Added Springfield snapshot tests for right-edge insets (items 29, 111, healthy control cell).

## Verification Run

- `flutter test test/features/pdf/extraction/stages/whitespace_inset_test.dart`
  - Passed (`+10`, `0 failed`)
- `flutter test test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart`
  - Passed (`+34`, `0 failed`)
- `flutter test test/features/pdf/extraction/`
  - Passed (`+853`, `0 failed`)
- `flutter test test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`
  - Passed (`+31`, `0 failed`)
  - Scorecard totals: `51 OK | 4 LOW | 0 BUG`
- `dart run tool/generate_springfield_fixtures.dart`
  - Fails in this environment (`dart:ui is not available on this platform`)
- Substituted fixture regeneration command:
  - `flutter test integration_test/generate_golden_fixtures_test.dart -d windows --dart-define=SPRINGFIELD_PDF="...Pay Items.pdf"`
  - Passed (`+1`, `0 failed`) and regenerated fixture set.

## Code Review Results

Initial review findings were resolved:

- Resolved: width-driven inset collapse/over-consumption risk (now guarded by span-aware cap).
- Resolved: missing Stage 2B coverage for width-driven path (new integration tests added).

No remaining implementation-level defects were reported after the remediation pass.

## Plan Completeness Status

- Step 1: Complete
- Step 2: Complete
- Step 3: Complete
- Step 4: Complete
- Step 5: Partial

## Remaining Blockers vs Plan Success Criteria

1. Item 29 fixed: `bid_amount=7026.0`.
2. Item 111 still unresolved:
   - `bid_amount=null`
   - `raw_bid_amount="| $5,179.30"`
3. Raw pipe artifacts still present in fixture output (17 items with leading `|` in at least one raw numeric field).
4. Bid amount completeness remains below target:
   - `non_null bid_amount = 124/131` (target in plan: `131/131`).

## References

- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:349`
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:708`
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:924`
- `test/features/pdf/extraction/stages/whitespace_inset_test.dart:178`
- `test/features/pdf/extraction/stages/whitespace_inset_test.dart:194`
- `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart:396`
- `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart:432`
- `test/features/pdf/extraction/fixtures/springfield_parsed_items.json:744`
- `test/features/pdf/extraction/fixtures/springfield_parsed_items.json:2903`
