# Calendar Auto-Collapse + Contractor Editing + Export Fix Plan

## Objectives
- Calendar: restore 45 percent height and auto-collapse to week on scroll, expand at top.
- Contractor editing (personnel + equipment) available in calendar report and report screen.
- Persist contractor selection via `entry_contractors` table (Option A, minimal).
- Export: save dialog with editable filename prefilled with selected date; no Android "Bytes are required" errors.
- Keep tests green: add/update keys and patrol tests in the same PRs.

## Constraints
- No breaking test changes between PRs.
- Add new keys and update patrol tests in same PR.
- Do not remove old keys until `rg` shows no references.
- Export stays report PDF + photos.pdf when photos exist.
- Existing E2E tests must continue to pass; adjust waits/keys only within the PR that changes UI.

---

## PR 1 - Calendar Auto-Collapse
### Scope
- Provider state and scroll behavior only.

### Steps
1. Add `_userFormat` and `_isCollapsed` to `CalendarFormatProvider`.
2. Update `setFormat` to set `_userFormat` and clear `_isCollapsed`.
3. Add `collapseToWeek` and `expandToUserFormat` helpers.
4. In `home_screen.dart`, set calendar height to 0.45.
5. Add scroll listener to `_reportScrollController` with `mounted` guard.
6. Add small hysteresis to avoid flicker at top (optional but preferred).

### Tests
- Unit test: `CalendarFormatProvider` preserves `_userFormat` and toggles `_isCollapsed`.
- Widget test: scroll report preview triggers collapse/expand without changing manual week selection.

---

## PR 2 - Contractor Editing in Calendar Report
### Scope
- Calendar report view uses same contractor editor as report screen (personnel + equipment).

### Steps
1. Extract contractor editor widget from `report_screen.dart` into a shared widget.
2. Replace read-only personnel summary in `home_screen.dart` with the shared contractor editor.
3. Ensure edits write via `EntryPersonnelLocalDatasource` and `EntryEquipmentLocalDatasource`.
4. Confirm equipment selection is available in the calendar report view.

### Keys and tests
1. Add contractor-specific keys for edit buttons and rows in calendar report view.
2. Update patrol tests to use new keys.
3. Add widget test: calendar report contractor editor renders both personnel and equipment controls.

---

## PR 3 - Contractor Persistence (Option A)
### Scope
- Persist contractor selection even when counts are zero.

### Steps
1. Add `entry_contractors` table (`entry_id`, `contractor_id`, `created_at`).
2. Add local datasource for insert/delete/get by entry.
3. When a contractor is added, insert into `entry_contractors`.
4. On load, seed `_personnelCounts` and contractor list from `entry_contractors`.
5. Keep existing counts behavior; no zero-count rows required.

### Tests
1. Add unit tests for `EntryContractorsLocalDatasource` insert/get/remove.
2. Add unit test: combining `entry_contractors` with `entry_personnel_counts` yields stable contractor list.
3. Update E2E: add contractor with zero counts, reopen entry, contractor still visible.

---

## PR 4 - Report Header Inline Edits
### Scope
- Location and weather editable in report header.

### Steps
1. Ensure header buttons open dropdowns and persist changes.
2. Update local UI state after save.

### Keys and tests
1. Add keys for header edit buttons and dropdowns.
2. Update REQUIRED_UI_KEYS and patrol tests.
3. Add widget test: location and weather update persists after leaving and returning to report.

---

## PR 5 - Export Fix (Editable Filename + Android Save)
### Scope
- Fix Android "Bytes are required" and add editable filename prompt.

### Steps
1. Add filename prompt dialog with prefilled date-based name.
2. Android: use directory picker + filename prompt, then write bytes directly.
3. Desktop/iOS: keep save dialog but prefill suggested filename and allow edit.
4. Ensure folder export still writes report PDF + photos.pdf.

### Tests
- Unit test: filename dialog default prefilled with date format.
- Unit test: save flow chooses folder export when photos exist, single PDF otherwise.
- Manual device verification for export with and without photos.

---

## Files Likely Touched
- `lib/features/entries/presentation/providers/calendar_format_provider.dart`
- `lib/features/entries/presentation/screens/home_screen.dart`
- `lib/features/entries/presentation/screens/report_screen.dart`
- `lib/features/entries/presentation/widgets/` (new shared contractor editor)
- `lib/features/contractors/data/datasources/local/entry_contractors_local_datasource.dart` (new)
- `lib/core/database/database_service.dart` (migration)
- `lib/features/pdf/services/pdf_service.dart`
- `lib/shared/testing_keys.dart`
- `integration_test/patrol/REQUIRED_UI_KEYS.md`

---

## Acceptance Criteria
- Calendar height is 45 percent and collapses/expands on scroll without flicker.
- Contractor editing (personnel + equipment) works in calendar report and report screen.
- Contractor selection persists across sessions even with zero counts.
- Header location and weather editable inline.
- Export uses editable filename prompt and succeeds on Android.
- Tests updated in same PRs as keys and UI changes.
