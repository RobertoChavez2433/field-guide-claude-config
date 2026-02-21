# 0582B Form Testing Findings

**Date**: 2026-02-21
**Session**: 416
**Method**: dart-mcp + Flutter Driver (driver_main.dart)
**Test**: End-to-end form creation, data entry, calculations, save, preview, export, navigation

---

## Working Correctly

| # | Feature | Details |
|---|---------|---------|
| 1 | Form creation | "New 0582B" from Forms list creates form with status: open |
| 2 | Header pre-fill | Project Number (864130) and Date (2026-02-20) auto-populated |
| 3 | Inspector text entry | TextFormField accepts input, persists after `done` action |
| 4 | Cell tap → SmartInputBar | Tapping a cell switches SmartInputBar to that field |
| 5 | Value entry via SmartInputBar | Type in SmartInputBar + "Next >" saves value to cell |
| 6 | Live calculations | Moisture PCF and % Compaction compute correctly in real-time |
| 7 | Calculation math verified | Row 1: 135.2/8.5/140.0 → PCF 124.61, Comp 89.01%. Row 2: 142.8/7.2/145.0 → PCF 133.21, Comp 91.87% |
| 8 | Add Row | Creates properly indexed row 2 with empty fields and delete button |
| 9 | Save | Save button works, snackbar "Form saved" appears |
| 10 | Export gating | "Preview PDF is required before export" snackbar — correct gate |
| 11 | Back navigation | Returns to Forms list without unsaved-changes prompt (already saved) |
| 12 | Stale route recovery | Error UI "Form response not found" + "Go Back" button works (Session 414 fix) |

---

## Bugs Found

### BUG-1: SmartInputBar value lost on direct cell tap
**Severity**: High
**Steps**: Enter value in SmartInputBar → tap a different cell directly (instead of "Next >")
**Expected**: Value auto-saves to the previous cell before switching
**Actual**: Value is silently discarded; previous cell remains empty
**Impact**: Data loss — user must always use "Next >" to save, which is not discoverable

### BUG-2: "Next >" doesn't advance to next field
**Severity**: Medium
**Steps**: Enter value in SmartInputBar → tap "Next >"
**Expected**: Value saves AND SmartInputBar advances to the next editable field in the row
**Actual**: Value saves but SmartInputBar stays on the same field (label doesn't change)
**Impact**: "Next >" is misleading — it acts as "Save" not "Save & Next"

### BUG-3: "Done" button unresponsive
**Severity**: Medium
**Steps**: Enter value in SmartInputBar → tap "Done" button (`input_bar_done_button`)
**Expected**: Value saves and SmartInputBar dismisses
**Actual**: Flutter Driver timeout — button either doesn't exist, is hidden, or causes a state change that removes the widget before the driver can confirm the tap
**Note**: May work for human tap but driver can't confirm. Needs manual verification.

### BUG-4: PDF preview fails — template not found
**Severity**: High (Blocker for preview/export)
**Steps**: Tap preview (eye icon) button in AppBar
**Expected**: PDF preview dialog/screen opens
**Actual**: Nothing visible happens. Logs show: `[FormPDF] Asset template not found: assets/templates/forms/mdot_0582b_density.pdf`
**Root cause**: The PDF template file doesn't exist in `assets/templates/forms/`. The code-first form needs either a template PDF created or a programmatic PDF generation path.

### BUG-5: No saved form list — can't re-open saved forms
**Severity**: High
**Steps**: Save a form → navigate back to Forms list
**Expected**: A list of previously saved form responses (with date, inspector, status) appears below the "New 0582B" button
**Actual**: Only the form type card with "New 0582B" is shown. No way to re-open or view saved forms.
**Impact**: Users lose access to all saved work unless they remember the exact route.

---

## UX Issues

### UX-1: Raw field keys in SmartInputBar
SmartInputBar shows `wet_density`, `moisture_percent`, `max_density`, `form_field_inspector` instead of human-readable labels like "Wet Density", "% Moisture", "Max Density", "Inspector".

### UX-2: No visual highlight on selected cell
When a cell is selected (SmartInputBar active for that field), the cell in the grid has no visual differentiation (no border highlight, no color change). User can't tell which cell they're editing.

### UX-3: Calculated vs editable cells look too similar
Both use the same dark container style. Calculated fields (Moisture PCF, % Compaction) should be visually distinct (different background, italic text, or a label) so users know they're read-only.

### UX-4: No row numbers or visual separation
Multiple test rows stack vertically with only a thin gap between cards. No "Test 1", "Test 2" headers. Hard to distinguish rows when scrolling.

### UX-5: Field labels disappear after value entry
Once a value is entered in a cell, the label (e.g., "Wet Density") is replaced by just the number ("135.2"). User loses context of what each cell represents.

### UX-6: Overall layout not field-ready
The current grid of unlabeled number cells feels like a developer debug view. Construction inspectors in the field need:
- Clear field labels that persist alongside values
- Visual hierarchy (header section distinct from data entry)
- Obvious flow direction (which field to fill next)
- Touch-friendly sizing for gloved/outdoor use

---

## Recommendations (Priority Order)

1. **Fix BUG-1** (auto-save on cell switch) — data loss is the worst UX
2. **Fix BUG-2** (Next > should advance) — core workflow improvement
3. **Fix BUG-5** (saved form list) — users need to re-open forms
4. **Create PDF template** or implement programmatic PDF generation (BUG-4)
5. **UI redesign** — address UX-1 through UX-6 as a batch in a Phase 3 UX polish pass
