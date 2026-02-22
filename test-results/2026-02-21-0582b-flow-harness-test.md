# 0582B Flow Harness Test Results

**Date**: 2026-02-21 | **Session**: 435
**Config**: `{"flow": "0582b-forms", "data": {}}`
**Target**: `lib/test_harness.dart` on Windows

## Summary

Tested the full 0582B entry flow across 5 screens using the flow harness with dart-mcp + flutter_driver. All core flows work end-to-end. Found 3 issues (1 bug, 2 minor).

## Screens Tested

| Screen | Status | Notes |
|--------|--------|-------|
| FormsListScreen | PASS (with bug) | Renders, but saved forms list always empty |
| FormViewerScreen | PASS | Header, tests, proctors, standards, remarks all render |
| ProctorEntryScreen | PASS | Input, live calc, validation, save all work |
| QuickTestEntryScreen | PASS | SmartInputBar, field nav, auto-calc, send all work |
| WeightsEntryScreen | PASS | Add readings, delta calc, pass/fail, save all work |

## Findings

### BUG-1: FormsListScreen never loads saved responses (Race Condition)
- **Severity**: Medium
- **Location**: `forms_list_screen.dart:24-36`
- **Symptom**: "Saved 0582B Forms" section always shows "No saved forms yet for this project" even when responses exist in DB.
- **Root Cause**: `didChangeDependencies` fires before `ProjectProvider.loadProjects()` completes asynchronously (harness_providers.dart:119). Since `selectedProject` is null at first render, `loadResponsesForProject` is never called. The `_didLoadResponses = true` guard prevents it from retrying.
- **Impact**: Users in real app won't see this (project loads before navigation), but harness cannot test the saved forms list.
- **Fix Options**:
  1. FormsListScreen: Watch `ProjectProvider` and re-trigger load when `selectedProject` changes from null.
  2. Harness: Make `buildHarnessProviders` await `loadProjects()` synchronously before returning.

### MINOR-2: Header auto-fill partially empty in harness
- **Severity**: Low (harness-only)
- **Location**: `form_viewer_screen.dart:76-91`
- **Symptom**: Only Date and Job Number populate. Inspector, Cert, Phone, Gauge, Route, Construction Eng are blank.
- **Root Cause**: Auto-fill reads from `PreferencesService` (inspector name, cert, phone, gauge) and `Project` model (controlSectionId, routeStreet, constructionEng). Both are empty in the harness seed data.
- **Fix**: Seed `PreferencesService` values and extend `Project` model seed with optional fields in `harness_seed_data.dart`.

### MINOR-3: Test viewer shows "Station" label instead of value for empty station
- **Severity**: Low (cosmetic)
- **Location**: `form_viewer_screen.dart:397`
- **Symptom**: Test #1 displays "Proctor #1 · Station" — the word "Station" is the field label, not the value (which is empty).
- **Root Cause**: The template string `'Station ${tests[i]['station'] ?? '--'}'` evaluates to `'Station --'` when station is null, but the display text for the proctor number line uses a different pattern: `'Proctor #${...} · Station ${...}'` which shows "Station" as a label prefix followed by the value.
- **Fix**: When station is null/empty, either omit the station portion or show "Station: --" more clearly.

## Flow Navigation Verified

1. FormsListScreen → tap "New 0582B" → FormViewerScreen (via `form-fill` route)
2. FormViewerScreen → tap "Proctor" → ProctorEntryScreen → Save → pops back to FormViewerScreen (reloads data)
3. FormViewerScreen → tap "+ Test" → QuickTestEntryScreen → Send to Form → pops back (reloads)
4. FormViewerScreen → tap "Weights" → WeightsEntryScreen → Save → pops back (reloads)
5. FormViewerScreen → Save (app bar) → "Form saved" snackbar

## Feature Verification

### ProctorEntryScreen
- [x] 4 input fields render (Moisture %, Volume Mold, Wet Soil+Mold, Mold)
- [x] Calculated card updates live (Wet Soil g/lbs, Wet PCF)
- [x] One-Point Result shows Max Density + Optimum Moisture when valid
- [x] Warning banner for out-of-range values ("exceeds Michigan Cone upper boundary")
- [x] Save button disabled when one-point fails, enabled when valid
- [x] Successful save with snackbar confirmation + auto-pop

### QuickTestEntryScreen
- [x] Auto-selects single proctor (P#1 chip with checkmark)
- [x] SmartInputBar appears on field tap (label, input, </>/ Done)
- [x] Field navigation via next/prev buttons
- [x] Max Density auto-populated from proctor (read-only)
- [x] Moisture PCF and % Compaction auto-calculated
- [x] Recheck toggle present
- [x] Location section renders (Station, Distance L/R, Depth, Item of Work)
- [x] Send to Form disabled without wet density, enabled with it
- [x] Successful send with snackbar + auto-pop

### WeightsEntryScreen
- [x] Auto-selects single proctor (no chip UI shown for 1 proctor)
- [x] 2 initial reading fields + "Add Reading" button
- [x] Delta calculation displays per reading pair
- [x] FAIL state: "Not yet passing" with red deltas > 10g
- [x] PASS state: "PASS: consolidation achieved" with green deltas <= 10g
- [x] Save enabled with 2+ readings regardless of pass/fail
- [x] Successful save with snackbar + auto-pop
- [x] Weights display in proctor card on FormViewerScreen after save

### FormViewerScreen
- [x] Quick action bar (Test, Proctor, Weights buttons)
- [x] Header fields editable (TextFormField)
- [x] Tests section shows count and test details
- [x] Proctors section shows count, proctor details, and 20/10 weights
- [x] Standards section with FormFieldCell ("Tap to enter")
- [x] Remarks TextFormField
- [x] AppBar save button works
- [x] Data reloads after returning from sub-screens
