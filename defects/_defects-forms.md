# Forms Feature Defects

## BUG-4: 20/10 weights calc fired on every keystroke with no confirmation gate
**Status**: RESOLVED | **Severity**: High | **Found**: Session 442 | **Resolved**: Session 442
**Location**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart:294`
**Symptom**: Entering first 20/10 reading immediately triggered MDD/OMC calculation. Second reading changed calc mid-entry, producing out-of-bounds one-point results.
**Root Cause**: Plan's "No gate" decision was wrong. `_recalcProctor()` used `_finalWeightAsDouble` unconditionally — no confirmation step before weight fed into calc chain.
**Fix**: Added `_weightsConfirmed` boolean. Calc passes `null` for `wetSoilMoldG` until user taps "Confirm Weights". Fields lock after confirmation. SEND requires confirmation.

### [FLUTTER] 2026-02-22: Plan decisions can contradict real-world workflow
**Pattern**: Brainstorming plans may decide "no gate needed" but actual field inspectors need explicit confirmation steps.
**Prevention**: For multi-step data entry flows, always validate plan decisions against real inspector workflow before implementing. Ask user if unclear.
**Ref**: `.claude/plans/2026-02-22-0582b-proctor-2010-redesign.md` line 33

## BUG-2: Header confirmation inferred from autofill state in hub flow
**Status**: RESOLVED | **Severity**: High | **Found**: Session 441 | **Resolved**: Session 441
**Location**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart:148`
**Symptom**: Header could appear confirmed and auto-advance without explicit user confirmation when autofill populated fields.
**Root Cause**: `_headerConfirmed` fallback treated non-empty header data as confirmation.
**Fix**: Gate confirmation strictly on persisted `header_confirmed == true` or explicit confirm action.

## BUG-3: Quick Test status pill stayed "sent" during next in-progress test
**Status**: RESOLVED | **Severity**: Medium | **Found**: Session 441 | **Resolved**: Session 441
**Location**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart:453`
**Symptom**: After sending Test #1, pill could misrepresent Test #2 in-progress state.
**Root Cause**: Status evaluation favored historical sent state semantics over active section entering semantics.
**Fix**: Prioritize `entering` while quick-test section is expanded; show sent when collapsed with saved tests.

## BUG-1: FormsListScreen never loads saved responses (Race Condition)
**Status**: OPEN | **Severity**: Medium | **Found**: Session 435
**Location**: `lib/features/forms/presentation/screens/forms_list_screen.dart:24-36`
**Symptom**: "Saved 0582B Forms" section always shows "No saved forms yet for this project" even when responses exist in DB.
**Root Cause**: `didChangeDependencies` fires before `ProjectProvider.loadProjects()` completes. Since `selectedProject` is null at first render, `loadResponsesForProject` is never called. The `_didLoadResponses = true` guard prevents retry.
**Impact**: Affects harness testing; may also affect real app if FormsListScreen is navigated to before project loads.
**Fix Options**:
1. Watch `ProjectProvider` and re-trigger load when `selectedProject` changes from null.
2. Harness: Make `buildHarnessProviders` await `loadProjects()` synchronously before returning.

## MINOR-2: Header auto-fill partially empty in harness
**Status**: OPEN | **Severity**: Low (harness-only) | **Found**: Session 435
**Location**: `lib/features/forms/presentation/screens/form_viewer_screen.dart:76-91`, `lib/test_harness/harness_seed_data.dart`
**Symptom**: Only Date and Job Number auto-fill. Inspector, Cert, Phone, Gauge, Route, Construction Eng are blank.
**Root Cause**: `PreferencesService` has no seeded values; `Project` model seed lacks optional fields.
**Fix**: Seed `PreferencesService` values and extend `Project` seed with `controlSectionId`, `routeStreet`, `constructionEng`.

## MINOR-3: Empty station displays as label text in test viewer
**Status**: OPEN | **Severity**: Low (cosmetic) | **Found**: Session 435
**Location**: `lib/features/forms/presentation/screens/form_viewer_screen.dart:397`
**Symptom**: Test card shows "Proctor #1 · Station" — "Station" is the label, not a value.
**Root Cause**: Template string shows `Station ${value ?? '--'}` but when null it reads awkwardly.
**Fix**: Omit station portion when empty, or format as "Station: --".
