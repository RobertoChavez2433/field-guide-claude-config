# Calendar View Redesign - CODEx Implementation Plan

## Objectives
- Keep calendar header/top area unchanged.
- Move entries list to a full-width middle section.
- Move report preview to a full-width bottom section with full scroll and inline editing.
- Preserve empty-day UX with visible sections and a Create Entry CTA.
- Avoid breaking tests: update tests in same PR where UI changes remove or replace keys.

## Key Constraints
- Do not break existing E2E tests between phases.
- Preserve existing TestingKeys unless explicitly replaced and tests updated in same phase.
- Maintain inline editing behavior and auto-save.

---

## Phase 0 - Investigation + Baseline Verification (No functional changes)
### Subphase 0.1 - Inventory keys and test touchpoints
1. Locate all uses of `TestingKeys.homeViewFullReportButton`.
2. Locate layout entry points: `_buildSelectedDayContent`, `_buildEntryList`, `_buildReportPreview`.
3. Identify any tests that assume split layout or report button navigation.

### Subphase 0.2 - Baseline verification
1. Run `flutter analyze`.
2. Run Patrol subset: `entry_management_test.dart` and `entry_lifecycle_test.dart`.
3. Capture current failures and link to layout overflow if present.

Deliverable: Baseline notes and file map for subsequent phases.

---

## Phase 1 - Layout Restructure (Single PR: UI + Tests together)
### Subphase 1.1 - Convert selected day content to vertical stack
1. Update `_buildSelectedDayContent` in `lib/features/entries/presentation/screens/home_screen.dart`:
   - Keep calendar/header area as-is.
   - Replace Row split with Column layout:
     - Date header row
     - Entry list section (full width)
     - Report section (full width, Expanded)
2. Keep loading/empty state behavior consistent with new layout.

### Subphase 1.2 - Entry list middle section (full-width)
1. Replace `_buildEntryList` usage with a horizontal list (full width):
   - `SizedBox(height: <compact height>)`
   - `ListView.builder(scrollDirection: Axis.horizontal)`
2. For tablets, optionally allow multi-column grid if already desired; otherwise defer.
3. Ensure each card keeps `TestingKeys.entryCard(entryId)` and selection highlight.
4. Add `TestingKeys.homeEntryListHorizontal` for scroll targeting.

### Subphase 1.3 - Report preview bottom section (full-width, editable)
1. Update `_buildReportPreview` to be full width with vertical scroll:
   - Keep header section (location + project) without ?View Full Report? button.
   - Preserve inline editing sections and auto-save behavior.
   - Use `SingleChildScrollView` within a constrained `Expanded` to avoid overflow.
2. Add new keys for report container and scroll view:
   - `homeReportPreviewSection`
   - `homeReportPreviewScrollView`
3. Ensure all editable fields remain functional and are reachable by scroll.

### Subphase 1.4 - Empty day UX (blank sections + CTA)
1. If `entries.isEmpty`:
   - Show date header + entry count (0 entries).
   - Show entry list section as blank area (e.g., placeholder text or empty list).
   - Show report section as blank (e.g., placeholder message).
   - Keep ?Create Entry? button visible.
2. Add key(s) to empty placeholders if needed for tests.

### Subphase 1.5 - Testing keys + E2E updates (same PR)
1. Keep `TestingKeys.homeViewFullReportButton` defined but remove it from UI.
2. Update tests that tap the full report button to instead scroll and validate report content.
3. Add helper methods for:
   - selecting entry on calendar
   - scrolling report preview
4. Update tests in:
   - `integration_test/patrol/e2e_tests/entry_management_test.dart`
   - `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`
   - `integration_test/patrol/helpers/patrol_test_helpers.dart`

Deliverable: New vertical layout + updated tests, all passing.

---

## Phase 2 - Inline Editing Stability & Accessibility (Polish PR)
### Subphase 2.1 - Focus + auto-save stability
1. Validate that scrolling doesn?t drop focus unexpectedly.
2. Ensure `_saveIfEditing()` triggers on section switches and app lifecycle changes.
3. If needed, add a small debounce on text changes or explicit save on scroll end.

### Subphase 2.2 - Keyboard + small screen validation
1. Test on small device dimensions to avoid RenderFlex overflow.
2. Ensure scrollable report is still hit-testable with keyboard open.
3. Adjust padding/margins if necessary.

Deliverable: Stable inline editing across device sizes.

---

## Phase 3 - Test Coverage Expansion (Optional PR)
### Subphase 3.1 - Empty day coverage
1. Add E2E test for empty day to verify blank sections + Create Entry visible.

### Subphase 3.2 - Multi-entry horizontal scroll
1. Add E2E test that scrolls entry list horizontally and selects a non-first entry.
2. Verify report preview updates to that entry.

Deliverable: Additional E2E coverage for new UX.

---

## Notes and Guardrails
- Avoid `pumpAndSettle()`; use condition-based waits and `scrollTo()` before tap.
- Preserve `TestingKeys.entryCard(entryId)` and calendar day keys.
- Keep the calendar header UI unchanged.
- Run tests after each PR-sized change set.

## Verification Checklist
1. `flutter analyze`
2. `pwsh -File run_patrol_debug.ps1`
3. Manual check on phone + tablet sizes
4. Verify inline editing persists and auto-saves

