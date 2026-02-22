# Forms Feature Defects

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
