# Form Completion Debug v5 - Comprehensive Plan (Updated)

**Created**: 2026-01-29 | **Session**: 202
**Updated**: 2026-01-30
**Status**: READY

## Executive Summary

Five issues identified during Windows testing and PDF inspection:

| # | Issue | Root Cause | Severity |
|---|-------|------------|----------|
| 1 | Missing "Start New Form" button | report_screen.dart lacks button that exists in entry_wizard_screen.dart | High |
| 2 | Autofill appears broken | Fields are filled but hidden by filter toggle defaulting to ON | High |
| 3 | Inspector fields not filling | Inspector profile not configured (user setup issue) | Low |
| 4 | 0582B form flow/layout wrong + missing fields | Current UI is flat + missing table grouping + missing PDF fields (20/10 weights) | High |
| 5 | Live preview not updating | Preview depends on responseData which only updates on save | High |

---

## Issue 1: Missing "Start New Form" Button on Report Screen

### Problem
The entry edit/report screen (`report_screen.dart`) only shows "Add Photo" button, but `entry_wizard_screen.dart` has both "Add Photo" AND "Start New Form" buttons.

### Evidence
- **Screenshot**: Report screen shows "Attachments" section with only "Add Photo" button
- **Code comparison**:
  - `entry_wizard_screen.dart:1547-1573` - Has BOTH buttons in a Row
  - `report_screen.dart:2368-2385` - Only has "Add Photo" button

### Root Cause
When the "Start New Form" button was added in commit `0e03b95` (Session 195), it was only added to `entry_wizard_screen.dart`, not to `report_screen.dart`.

### Fix Required

**File**: `lib/features/entries/presentation/screens/report_screen.dart`
**Location**: Lines 2368-2385

**Current code**:
```dart
Row(
  children: [
    Expanded(
      child: OutlinedButton.icon(
        key: TestingKeys.reportAddPhotoButton,
        onPressed: _isCapturingPhoto ? null : () => _showPhotoSourceDialog(entry),
        icon: _isCapturingPhoto
            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
            : const Icon(Icons.add_a_photo),
        label: Text(_isCapturingPhoto ? 'Capturing...' : 'Add Photo'),
      ),
    ),
    // MISSING: Start New Form button!
  ],
),
```

**Required change**:
```dart
Row(
  children: [
    Expanded(
      child: OutlinedButton.icon(
        key: TestingKeys.reportAddPhotoButton,
        onPressed: _isCapturingPhoto ? null : () => _showPhotoSourceDialog(entry),
        icon: _isCapturingPhoto
            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
            : const Icon(Icons.add_a_photo),
        label: Text(_isCapturingPhoto ? 'Capturing...' : 'Add Photo'),
      ),
    ),
    const SizedBox(width: 12),
    Expanded(
      child: OutlinedButton.icon(
        key: TestingKeys.reportAddFormButton,  // NEW KEY
        onPressed: () => _showFormSelectionDialog(),
        icon: const Icon(Icons.edit_document),
        label: const Text('Start New Form'),
      ),
    ),
  ],
),
```

### Implementation Tasks

**Task 1.1**: Add TestingKey
- File: `lib/shared/testing_keys.dart`
- Add: `static const reportAddFormButton = Key('report_add_form_button');`

**Task 1.2**: Add `_showFormSelectionDialog()` method to report_screen.dart
- Copy pattern from `entry_wizard_screen.dart`
- Import `FormSelectionDialog` if needed
- Add form state tracking (`_entryForms` list) if not present

**Task 1.3**: Add Button to Row
- Add SizedBox(width: 12) spacer
- Add "Start New Form" Expanded button

**Task 1.4**: Add form response handling
- Add `_entryForms` list state variable
- Add `_loadFormsForEntry()` method
- Add `_openFormResponse()` method
- Add `_confirmDeleteForm()` method
- May need to add FormProvider interaction

---

## Issue 2: Autofill Appears Broken (But IS Working)

### Problem
User sees empty fields on form fill screen, thinks autofill is broken.

### Evidence - Debug Logs CONFIRM Autofill Works
```
[AutoFill] Filled project_number from AutoFillSource.project: "864130"
[AutoFill] Filled control_section from AutoFillSource.project: "864130"
[AutoFill] Filled date from AutoFillSource.entry: "01/29/2026"
[AutoFill] Filled location from AutoFillSource.location: "17th Street"
[AutoFill] Filled station from AutoFillSource.location: "17th Street"
[AutoFill] Results: 5 filled, 10 unfilled
```

**5 fields WERE successfully filled!** But the user can't see them.

### Root Cause
The "Show only fields needing input" toggle:
1. **Defaults to ON** (`_showOnlyManualFields = true` in form_fill_screen.dart)
2. **Filter HIDES auto-filled fields** that have values

**Filter logic** in `form_fields_tab.dart:44-66`:
```dart
if (fieldEntry == null || !fieldEntry.isAutoFillable) {
  return true; // Show non-auto-fillable fields
}
final isEmpty = controller?.text.isEmpty ?? true;
final isUserEdited = autoFillConfig.userEditedFields.contains(fieldName);
return isEmpty || isUserEdited;  // Returns FALSE for filled auto-fill fields!
```

For an auto-filled field with a value:
- `isEmpty = false` (field HAS a value like "864130")
- `isUserEdited = false` (user didn't manually edit it)
- Result: `false || false = false` → **FIELD IS HIDDEN**

### Solution

**Change default toggle state from ON to OFF**

**File**: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`

Find line with:
```dart
bool _showOnlyManualFields = true;
```

Change to:
```dart
bool _showOnlyManualFields = false;
```

This way:
- User sees ALL fields by default, including auto-filled ones
- User can toggle ON to hide auto-filled fields if they want a cleaner view
- No logic changes needed, just default value change

### Optional Enhancement

Add visual feedback showing how many fields are hidden when toggle is ON:
```dart
// In toggle area:
if (_showOnlyManualFields)
  Text('(${hiddenCount} auto-filled fields hidden)',
       style: TextStyle(fontSize: 12, color: AppTheme.textSecondary))
```

---

## Issue 3: Inspector Fields Not Auto-Filling

### Problem
Inspector-related fields show "Could not fill":
```
[AutoFill] Could not fill inspector from AutoFillSource.inspectorProfile
[AutoFill] Could not fill certification_number from AutoFillSource.inspectorProfile
[AutoFill] Could not fill inspector_phone from AutoFillSource.inspectorProfile
```

### Root Cause
```
[AutoFillContext]   Inspector: (not set)
```

The inspector profile is **not configured**. This is a **user setup issue**, not a code bug.

### Resolution
**No code fix needed.** User action required:
1. Go to Settings → Inspector Profile
2. Fill in Name, Certification Number, Phone
3. Auto-fill will then work for inspector fields

### Optional Enhancement
Show hint banner when inspector profile is empty:
- On FormFillScreen, detect if inspector fields failed due to missing profile
- Show dismissible banner: "Set up your inspector profile in Settings to auto-fill inspector fields"

---

## Issue 4: 0582B Form Layout + Missing Fields (PDF-Verified)

### Problem
The form fill screen has multiple issues with the MDOT 0582B Density form:

1. **Wrong layout** - left side does NOT mirror the PDF flow
2. **Missing grouping** - should have two repeating test groups (Top table + Bottom table)
3. **Missing 20/10 weights** fields
4. **Flat field list** - fields displayed sequentially instead of organized by PDF sections
5. **No push-to-row flow** - user cannot enter a test, push it to a row, and clear inputs

### Verified PDF Structure (assets/templates/forms/mdot_0582b_density.pdf)

**Top Table (12 rows x 16 columns)**
- PDF fields: `1Row1` ... `16Row12`
- Column headers (1-16):
  1) TEST (Original/Recheck)
  2) TEST DEPTH (inch)
  3) COUNTS (MC)
  4) COUNTS (DC)
  5) DRY DENSITY (pcf)
  6) WET DENSITY (pcf)
  7) MOISTURE (pcf)
  8) MOISTURE (%)
  9) MAX DENSITY (pcf)
  10) PERCENT COMPACTION
  11) STATION
  12) DISTANCE FROM C/L (LEFT)
  13) DISTANCE FROM C/L (RIGHT)
  14) DEPTH BELOW PLAN GRADE (ft)
  15) ITEM OF WORK
  16) TEST NUMBER

**Bottom Table (5 rows x 10 columns)**
- PDF fields: `ARow1` ... `JRow5`
- Column headers (A-J):
  A) TEST NUMBER
  B) MOISTURE (%)
  C) VOLUME MOLD (cu. ft.)
  D) WET SOIL + MOLD (g)
  E) MOLD (g)
  F) WET SOIL (g)
  G) WET SOIL (lbs)
  H) COMPACTED SOIL WET (pcf)
  I) MAX DENSITY (pcf)
  J) OPTIMUM MOISTURE (%)

**20/10 Weights fields**
- PDF fields: `1st`, `2nd`, `3rd`, `4th`, `5th`

**Remarks**
- PDF field: `REMARKS 1`
- Current UI uses "Notes"; must rename section/label to **Remarks** to match PDF.

### Required Flow (Left Side / Entry UI)

We need **two repeating test entry groups**, in a condensed two-column layout:

**Top Table Entry (Rows 1–12)**
- Left Column: Test Type, Counts (MC), Dry Density, Moisture (pcf), Max Density, Station, Depth Below Plan Grade
- Right Column: Test Depth, Counts (DC), Wet Density, Moisture (%), % Compaction, Distance from C/L (Left/Right stacked under label), Item of Work

**Bottom Table Entry (Rows 1–5)**
- Left Column: Test Number (A), Volume Mold (C), Mold (E), Wet Soil (lbs) (G), Max Density (I)
- Right Column: Moisture % (B), Wet Soil + Mold (D), Wet Soil (F), Compacted Soil Wet (H), Optimum Moisture (J)

Each group must:
- Have its own input fields
- Have an "Add Test" button that:
  - pushes the test to the **first available row** in that group
  - clears that group’s input fields

### Implementation Tasks for Issue 4

**Task 4.1: Update Form JSON**
- File: `assets/data/forms/mdot_0582b_density.json`
- Add 20/10 weights fields (pdfField: `1st`, `2nd`, `3rd`, `4th`, `5th`)
- Add mapping for top table fields (1-16) and bottom table fields (A-J)
- Add parsing keywords for new fields
- Rename "Notes" field/label to "Remarks" (pdfField: `REMARKS 1`)

**Task 4.2: Grouped Test Entry UI**
- Replace single quick-entry section with two grouped entry panels:
  - Top Table Entry
  - Bottom Table Entry
- Each panel has its own controllers + Add button
- On Add: build a row map with `group: 'top' | 'bottom'` and append to table rows
- Clear only that group’s controllers after add

**Task 4.3: Grouped Table Display**
- Replace TableRowsSection with two sections (Top Rows, Bottom Rows)
- Each section filters rows by `group`
- Keep delete controls scoped to correct group

**Task 4.4: PDF Fill Logic**
- Update `FormPdfService` row fill to:
  - Split rows by `group`
  - Map top rows to `1Row#...16Row#`
  - Map bottom rows to `ARow#...JRow#`
- Add logic to fill `1st`..`5th` 20/10 weights fields

---

## Issue 5: Live Preview Not Updating

### Problem
The preview tab does not update as users type.

### Root Cause
`FormPreviewTab` regenerates only when `response.responseData` changes. `FormFillScreen` only updates `_response` on save. So the preview hash never changes while typing.

### Fix Required

Two options (choose one):

**Option A (Preferred - lightweight)**
- On every field change, update `_response` with current controller values (responseData)
- This updates the preview hash and triggers refresh

**Option B**
- Pass the live controller values directly to `FormPreviewTab` and regenerate from those

### Files
- `lib/features/toolbox/presentation/screens/form_fill_screen.dart`
- `lib/features/toolbox/presentation/widgets/form_preview_tab.dart`
- `lib/features/toolbox/data/services/form_pdf_service.dart`

---

## Implementation Plan (Updated)

### Phase 1: Fix Autofill Visibility (Quick Win)

**Effort**: 5 minutes

**Task 1**: Change default toggle value
- File: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`
- Change: `bool _showOnlyManualFields = true;` → `bool _showOnlyManualFields = false;`

### Phase 2: Add Start New Form Button to Report Screen

**Effort**: 30-45 minutes

**Task 2.1**: Add TestingKey
- File: `lib/shared/testing_keys.dart`
- Add key constant

**Task 2.2**: Add form state and methods to report_screen.dart
- Add `_entryForms` list
- Add `_loadFormsForEntry()`
- Add `_showFormSelectionDialog()`
- Add form thumbnail display in Attachments grid
- Add form tap/delete handlers

**Task 2.3**: Update Attachments section
- Change header to show forms count
- Update empty state text
- Add forms to grid
- Add button to Row

### Phase 3: 0582B Form Restructure (High Priority)

**Effort**: 2-4 hours

**Task 3.1**: Update MDOT 0582B JSON
- Add 20/10 weights fields (`1st`..`5th`)
- Add all top-row + bottom-row field mappings
- Add parsing keywords/synonyms for new fields
- Rename "Notes" field/label to "Remarks"

**Task 3.2**: Grouped Test Entry UI
- Replace single quick entry with two grouped entry panels
- Top panel layout: Station on left; Dist from C/L on right with Left/Right stacked under label; Item of Work paired with Depth Below Plan Grade
- Bottom panel layout: Test Number column A mapping
- Add push-to-row behavior + clear after push

**Task 3.3**: Grouped Table Row Display
- Separate Top Rows and Bottom Rows sections
- Filter by row group

**Task 3.4**: PDF Fill Mapping
- Map top rows to `1Row#..16Row#`
- Map bottom rows to `ARow#..JRow#`
- Map 20/10 weights

### Phase 4: Live Preview Fix

**Effort**: 30-60 minutes

**Task 4.1**: Update responseData on field change
- Update `_response` with live controller values on each change
- Ensure preview hash updates

---

## Testing Checklist

### Phase 1: Autofill Visibility
- [ ] Open FormFillScreen (MDOT 0582B Density)
- [ ] Verify toggle defaults to OFF
- [ ] Verify ALL fields are visible
- [ ] Turn toggle ON - verify auto-filled fields hide
- [ ] Turn toggle OFF - verify fields visible again

### Phase 2: Report Screen Button
- [ ] Open existing entry via report screen
- [ ] Verify "Start New Form" button appears next to "Add Photo"
- [ ] Tap "Start New Form" - verify form selection dialog opens
- [ ] Select a form - verify form opens for filling
- [ ] Save form - verify it appears in Attachments grid
- [ ] Tap form thumbnail - verify it opens for editing

### Phase 3: 0582B Restructure
- [ ] Open 0582B form
- [ ] Verify Top Table Entry group present (station on left; dist from C/L on right with L/R stacked)
- [ ] Verify Bottom Table Entry group present (Test Number in column A)
- [ ] Enter a top test, press Add → row appears in Top table and fields clear
- [ ] Enter a bottom test, press Add → row appears in Bottom table and fields clear
- [ ] Verify 20/10 weights visible and mapped
- [ ] Verify Remarks section label and mapping to PDF

### Phase 4: Live Preview
- [ ] Open preview tab
- [ ] Type into a field and verify preview updates without saving

---

## Files to Modify

| File | Phase | Changes |
|------|-------|---------|
| `lib/features/toolbox/presentation/screens/form_fill_screen.dart` | 1,4 | Toggle default + live preview updates |
| `lib/shared/testing_keys.dart` | 2 | Add `reportAddFormButton` |
| `lib/features/entries/presentation/screens/report_screen.dart` | 2 | Add button, methods, form handling |
| `assets/data/forms/mdot_0582b_density.json` | 3 | Add 20/10 weights + top/bottom table fields + rename Notes→Remarks |
| `lib/features/toolbox/presentation/widgets/form_fields_tab.dart` | 3 | Replace quick entry with grouped entry panels |
| `lib/features/toolbox/presentation/widgets/table_rows_section.dart` | 3 | Grouped table display |
| `lib/features/toolbox/data/services/form_pdf_service.dart` | 3 | Row group mapping + 20/10 weights |

---

## PDF Field Reference (0582B)

**Top Table Fields**: `1Row1`..`16Row12`
**Bottom Table Fields**: `ARow1`..`JRow5`
**20/10 Weights**: `1st`, `2nd`, `3rd`, `4th`, `5th`
**Remarks**: `REMARKS 1`
**Header Fields**: `DATE`, `CONTROL SECTION ID`, `JOB NUMBER`, `ROUTE NUMBER or STREET`, `GAUGE NUMBER`, `DENSITY INSPECTOR`, `CERTIFICATION NUMBER`, `DENSITY INSPECTOR PHONE NUMBER`, `CONSTRUCTION ENG MDOT`, `ASST CONST ENG CONSULTANT ENG`, `AGENCYCOMPANY.1`

---

## Historical Context

| Session | Commit | Changes |
|---------|--------|---------|
| 195 | `0e03b95` | Added Start New Form button to entry_wizard only |
| 199 | `4f4256e` | Added filter toggle (defaults ON - the problem) |
| 201 | `fb158a3` | Added isInitializing flag, registry repopulation |
| 202 | (current) | Updated plan + PDF-verified mapping |
