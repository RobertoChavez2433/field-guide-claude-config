# Tablet UI Fix Plan — Entry wizard, Quantities pane, Project list split

## Scope

Fix three tablet-specific UX defects without altering pay-app export behavior:

1) Activities card placement in daily entry wizard (tablet).
2) Pay item tap behavior in `Pay Items & Quantities` (tablet should stay inline, no bottom sheet).
3) Remove split-screen behavior from projects view (tablet should be single-column).

---

## 1) Daily Entry Wizard: move Activities card to left pane

- [ ] Inspect `lib/features/entries/presentation/widgets/entry_editor_body.dart`
  - [ ] In `medium:` branch, extend `AppAdaptiveLayout.body` stack to include Activities card underneath header.
  - [ ] Keep `EntryEditorSectionsList` in `detail:` but without Activities card.
- [ ] Inspect `lib/features/entries/presentation/widgets/entry_editor_sections_list.dart`
  - [ ] Add a flag (`includeActivitiesSection`, default `true`) to `EntryEditorSectionsList`.
  - [ ] Wrap existing `EntryActivitiesSection` block with this flag.
  - [ ] Preserve compact behavior by using default `true`.
- [ ] Wire `EntryEditorBody` to pass `includeActivitiesSection: false` for tablet detail pane.
- [ ] Validate:
  - [ ] Tablet: header + activities appear on left; right pane starts with contractors.
  - [ ] Compact: behavior unchanged (header + full sections list unchanged).

Files:
- `lib/features/entries/presentation/widgets/entry_editor_body.dart`
- `lib/features/entries/presentation/widgets/entry_editor_sections_list.dart`

---

## 2) Quantities: prevent pay-item bottom sheet on tablet

- [ ] Inspect `lib/features/quantities/presentation/screens/quantities_screen.dart`
  - [ ] In `_showBidItemDetail`, keep state assignment:
    - `_selectedItem = item`
    - `_selectedUsedQuantity = usedQuantity`
  - [ ] Gate bottom sheet open to compact only:
    - if `AppBreakpoint.of(context).isCompact` then `BidItemDetailSheet.show(...)`
    - else do not show modal.
  - [ ] Ensure list card selection still updates right detail pane on tablet.
- [ ] Optional cleanup:
  - [ ] Update method comment to clarify modal only in compact mode.
- [ ] Validate:
  - [ ] Tablet: selecting a pay item updates right detail pane immediately.
  - [ ] Phone: selecting a pay item still opens bottom sheet.

Files:
- `lib/features/quantities/presentation/screens/quantities_screen.dart`
- `lib/features/quantities/presentation/widgets/bid_item_detail_sheet.dart` (read-only confirmation)

---

## 3) Projects view: remove split-screen on tablet

- [ ] Inspect `lib/features/projects/presentation/screens/project_list_screen.dart`
  - [ ] Remove/neutralize medium `AppAdaptiveLayout` split usage.
  - [ ] Keep single-column body for both compact and medium.
  - [ ] Simplify `AppAdaptiveLayout` usage:
    - use `_buildBodyColumn(state)` directly in medium (or reuse compact branch).
  - [ ] Simplify `_handleSelectProject`:
    - keep `context.read<ProjectProvider>().selectProject(id)`
    - navigate to dashboard (or existing intended post-select route), not local pane state.
  - [ ] Remove now-unused selected-project detail state (`_selectedProjectId`) and dependent cleanup path.
- [ ] Remove any stale dependency on `ProjectListDetailPane`:
  - [ ] If unused, delete `onLocalRemoved` selection clear callback flow.
- [ ] Validate:
  - [ ] Tablet projects view renders as one-column list.
  - [ ] Selecting any project opens expected project context (current dashboard behavior on compact path should remain).

Files:
- `lib/features/projects/presentation/screens/project_list_screen.dart`
- `lib/features/projects/presentation/widgets/project_list_detail_pane.dart` (verify no remaining references; deprecate if obsolete)

---

## 4) Verification commands

- [ ] Run targeted tests around affected areas:
  - `flutter test test/features/entries/presentation/widgets/entry_activities_section_test.dart`
  - `flutter test test/features/quantities/presentation/screens/quantities_screen_test.dart`
  - `flutter test test/features/projects/presentation/screens/project_list_screen_test.dart`
- [ ] Run at least one manual tablet layout smoke test:
  - Entry editor in read-only mode confirms readable full report panel.
  - Quantities tablet shows inline pay item detail updates.
  - Projects list no longer occupies split panes.

---

## Notes / risk

- This patch is intentionally narrow to isolate tablet UX behavior.
- No export provider/use-case changes are involved here.
