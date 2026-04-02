# Code Review: UI Refactor Gap Closure Plan — Cycle 1

**Reviewer**: Code Review Agent
**Date**: 2026-04-02
**Verdict**: **REJECT**

## Blocking Issues (5)

| # | Issue | Severity | Phase |
|---|-------|----------|-------|
| 1 | Navigator.pop(context) pops screen not dialog — AppDialog.show doesn't expose dialogContext | Crash | 3.1, 3.2 |
| 2 | WeatherService.getWeather() does not exist — actual API is fetchWeather(lat, lon, date) positional | Compile error | 2.6 |
| 3 | WeatherData.temperature does not exist — has tempHigh/tempLow (int) | Compile error | 2.6 |
| 4 | Logger.weather() does not exist — available: sync, pdf, db, auth, ocr, nav, ui, photo, lifecycle, bg, error | Compile error | 2.6 |
| 5 | Route /entries/drafts/$projectId not defined in router | Runtime crash | 2.5 |

## Suggestions (8)

1. AppDialog enhancement is safe (0 existing callers) — should note this
2. entry_forms_section.dart listed in 3 phases — consolidate
3. add_equipment_dialog.dart exists in both entries/ and projects/ — clarify
4. scaffold_with_nav_bar.dart has no actual snackbar calls — remove from Phase 6
5. pdf_data_builder.dart uses pre-captured ScaffoldMessengerState, not context — can't trivially replace
6. AlertItemRow.usedQuantity requires upstream data plumbing — verify availability
7. WeatherSummaryCard missing import for WeatherData type
8. DesignConstants.animationFast (150ms) may be too fast for tab transitions

## Minor Items
- Phase 2.5.3: Unresolved which 3 stat cards to keep
- Phase 2.6.2: Missing app_providers.dart wiring for WeatherProvider
- Phase 3.4: Some showModalBottomSheet calls pass params AppBottomSheet.show doesn't accept
- Phase 5.1: confirmation_dialog.dart has no text inputs — remove from AppTextField list
- TextStyle count discrepancy (124 claimed, ~94 listed)

## Positive Observations
- Logical phasing, good defensive IMPORTANT callouts
- ValueKey analysis is thorough and correct
- Quality gate grep patterns are strong verification
