# Report Screen + Form Completion Debug PR-Sized Plan (2026-01-29)

## Goal
Mirror entry wizard attachments/form flows in report screen, fix autofill visibility default, and close remaining Form Completion Debug gaps with minimal-risk PRs.

---

## Phase 1 (PR): Report Screen Parity With Entry Wizard
**Why now:** High-impact UX bug. Users cannot start/open/delete forms from report screen despite entry wizard supporting it. This is the main blocker reported in Form Completion Debug Issue #1.

### Scope
- Add "Start New Form" button to report screen attachments section.
- Display form thumbnails alongside photos (combined attachments grid).
- Load and manage form responses for the report entry.
- Add required testing keys for report form button and thumbnails.

### Changes
- **Add state + loaders**
  - `lib/features/entries/presentation/screens/report_screen.dart`:
    - Add `_entryForms` list state and `_loadFormsForEntry()`.
    - Load responses and forms during entry load (mirror entry wizard logic).
    - Add `_openFormResponse()` and `_confirmDeleteForm()`.
- **Attachments grid parity**
  - `lib/features/entries/presentation/screens/report_screen.dart`:
    - Combine photos + forms in attachments grid (same ordering rules as entry wizard: photos first, then forms).
    - Update header count to total attachments (photos + forms).
    - Update empty-state copy to reflect both photos/forms.
- **Start New Form button**
  - `lib/features/entries/presentation/screens/report_screen.dart`:
    - Add OutlinedButton with `TestingKeys.reportAddFormButton` and `Icons.edit_document`.
    - Wire to `_showFormSelectionDialog()` (reuse entry wizard dialog).
- **Testing keys**
  - `lib/shared/testing_keys/entries_keys.dart`:
    - Add `reportAddFormButton`.
    - Add `reportFormThumbnail(String formId)` for attachment grid if needed.
  - `lib/shared/testing_keys/testing_keys.dart`:
    - Expose keys via facade.

### Verification
- Open report screen for an entry; verify:
  - "Start New Form" appears next to "Add Photo".
  - Form selection dialog opens and creates a response.
  - Saved form appears in attachments grid.
  - Form thumbnail opens in form fill screen; delete removes it.

---

## Phase 2 (PR): Autofill Visibility Default Fix
**Why now:** Current default hides auto-filled fields, making autofill appear broken (Form Completion Debug Issue #2). One-line change with high UX impact.

### Changes
- `lib/features/toolbox/presentation/screens/form_fill_screen.dart:65`
  - Change `bool _showOnlyManualFields = true;` → `false`.

### Optional Enhancement (if desired)
- Add a small hint showing how many fields are hidden when toggle is ON.
  - `lib/features/toolbox/presentation/widgets/form_fields_tab.dart` or toggle area in `form_fill_screen.dart`.

### Verification
- Open form fill; verify all fields visible by default.
- Toggle "Show only fields needing input" ON/OFF and confirm behavior.

---

## Phase 3 (PR): Template Sectioning Decision + Lightweight Fix
**Why now:** Issue #4 mentions “flat field list vs sectioned template.” We need a decision to avoid rework.

### Option A (Low-risk, minimal changes)
**Add category grouping without changing JSON structure**
- Use existing `category` field in `FormFieldEntry` (already supported by registry).
- Update render logic to group fields by category in UI.

**Files:**
- `lib/features/toolbox/presentation/widgets/form_fields_tab.dart`

**Reasoning:**
- Does not require asset schema changes.
- Works with existing registry data and avoids re-seeding complexity.

### Option B (Schema-altering)
**Add `sections` to JSON form definitions and render sections explicitly**
- Update JSON in `assets/data/forms/*.json` with `sections` arrays.
- Update `FormSeedService` to parse sections and apply ordering/grouping.

**Files:**
- `assets/data/forms/mdot_0582b_density.json`
- `assets/data/forms/mdot_1174r_concrete.json`
- `lib/features/toolbox/data/services/form_seed_service.dart`
- `lib/features/toolbox/presentation/widgets/form_fields_tab.dart`

**Reasoning:**
- More faithful to template structure, but higher risk and requires re-seeding + migration considerations.

**Decision needed:** pick A or B before implementation.

---

## Phase 4 (PR): Test Coverage for New Behaviors
**Why now:** Prevent regressions in report screen attachments and autofill toggle behavior.

### Changes
- `test/features/entries/presentation/screens/report_screen_test.dart`
  - Add tests for report attachments header count + Start New Form button presence.
- `test/features/toolbox/presentation/screens/form_fill_screen_test.dart`
  - Add test verifying default toggle OFF (all fields visible).

---

## Findings Reference (from review)
- Missing report-screen Start New Form button + form attachments: `lib/features/entries/presentation/screens/report_screen.dart:2284` and `:2369`.
- Missing `reportAddFormButton` testing key: `lib/shared/testing_keys/entries_keys.dart`.
- Autofill visibility default still ON: `lib/features/toolbox/presentation/screens/form_fill_screen.dart:65`.
- Sectioned template gap: no section/grouping metadata in JSON; UI renders flat list.

---

## Next Step
Confirm Phase 3 option (A or B). If you choose A, I can implement Phase 1+2 immediately and draft tests for Phase 4.
