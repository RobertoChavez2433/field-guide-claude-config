# Code Review: 0582B Proctor Redesign — Provider, Data Model, Testing Keys

**Date**: 2026-02-22
**Reviewer**: code-review-agent
**Scope**: InspectorFormProvider, testing keys, barrel files, unchanged sections

---

## Critical Issues (Must Fix)

### 1. 15 orphaned `ValueKey` testing keys in `testing_keys.dart`
**File**: `lib/shared/testing_keys/testing_keys.dart:221-274`

Keys reference old standalone screens that were deleted. No widget uses any of them.

Orphaned keys: `mdot0582bProctorMoistureField`, `mdot0582bProctorVolumeMoldField`, `mdot0582bProctorWetSoilMoldField`, `mdot0582bProctorMoldField`, `mdot0582bProctorSaveButton`, `mdot0582bQuickTestAddProctorButton`, `mdot0582bQuickTestProctorChip`, `mdot0582bQuickTestRecheckToggle`, `mdot0582bQuickTestSendButton`, `mdot0582bWeightsProctorChip`, `mdot0582bWeightsReadingField`, `mdot0582bWeightsAddReadingButton`, `mdot0582bWeightsSaveButton`, `mdot0582bFillSubmitButton`, `mdot0582bFillGoBackButton`.

**Fix**: Delete lines 221-274 from `testing_keys.dart`.

### 2. 9 orphaned keys in `toolbox_keys.dart` from deleted `form_fill_screen.dart`
**File**: `lib/shared/testing_keys/toolbox_keys.dart:38-69`

The "Forms - Fill Screen" section defines keys for a screen that no longer exists. `formFillScreen`, `formFillScrollView`, `formFillLoading`, `formFillError`, `formAddTestButton`, `formCancelButton`, `formField()`, `formTableRow()`, `formTableRowDelete()` are never referenced by any widget.

Note: `formPreviewPdfButton`, `formSaveButton`, `formExportButton` ARE still used by `form_viewer_screen.dart`.

**Fix**: Delete lines 41-44, 56-69. Rename section to "Forms - Viewer Screen".

### 3. Orphaned `hubProctorField` key
**File**: `lib/shared/testing_keys/toolbox_keys.dart:89`

Defined but never used. The proctor section uses `hubProctorSetupField` instead.

**Fix**: Delete line 89 and its re-export at `testing_keys.dart:200-201`.

---

## Suggestions (Should Consider)

### 1. Semantically stale "Add Weights" button in form_viewer_screen
**File**: `lib/features/forms/presentation/screens/form_viewer_screen.dart:328-333`

A separate "Weights" button exists alongside "Test" and "Proctor". All three point to the same `_openFlow('form-fill')`. Since weights are merged into proctor, remove the "Weights" button.

### 2. Test harness references deleted screens
**Files**: `lib/test_harness/screen_registry.dart:89-101`, `lib/test_harness/flow_registry.dart:28-30,56-72`

Still registers `FormFillScreen`, `QuickTestEntryScreen`, `ProctorEntryScreen`, `WeightsEntryScreen`. These are now stubs redirecting to `MdotHubScreen`. Consolidate or document.

### 3. Smart Input Bar keys orphaned
**File**: `lib/shared/testing_keys/toolbox_keys.dart:113-115`

`inputBarValueField`, `inputBarNextButton`, `inputBarDoneButton` defined for deleted `smart_input_bar.dart`.

**Fix**: Delete lines 111-115 and re-exports in `testing_keys.dart:280-282`.

### 4. `DropdownButtonFormField` uses `initialValue` instead of `value`
**File**: `lib/features/forms/presentation/widgets/hub_quick_test_content.dart:105,117`

`initialValue` is not a named parameter of `DropdownButtonFormField`. Should be `value:`.

---

## Minor

- Redundant `wet_soil_mold_g` assignment in `mdot_hub_screen.dart:388` — provider re-derives the same value.
- Four stub screen classes at `mdot_hub_screen.dart:886-920` are identical — could be consolidated.

---

## Positive Observations

- Provider `appendMdot0582bProctorRow` is defensive and correct: strips `chart_type`, normalizes weights to `List<String>`, derives `wet_soil_mold_g` from last reading.
- `updateMdot0582bProctorWeights` successfully removed — no trace anywhere.
- No `chart_type` leaks: only the defensive `remove` in provider.
- `widgets.dart` barrel is clean — only 7 active widget files exported.
- `screens.dart` barrel is clean — only active screens.
- Quick test and header sections are unaffected — no regressions.
- Hub proctor content keys are comprehensive — every interactive element has a key.
- New testing keys in `toolbox_keys.dart` use consistent naming and parameterized factories.

---

## KISS/DRY Opportunities

- **28 dead key definitions total** across `testing_keys.dart` and `toolbox_keys.dart`. Single cleanup commit.
- Testing keys dual-definition pattern: `ValueKey` block (lines 221-274) defines keys inline instead of delegating to `ToolboxTestingKeys`. Inconsistent with the rest of the file.
