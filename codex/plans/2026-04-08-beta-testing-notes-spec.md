# 2026-04-08 Beta Testing Notes Spec

## Objective

Turn the latest beta testing notes into a single implementation spec and
execution backlog that is grounded in actual source seams, existing repair/lint
work, and honest verification status.

This spec is not just a bug list. It is the working product/architecture
contract for closing the current beta UX/state/sync gaps.

## Completion Standard

An item is not complete until all of the following are true:

- the source behavior is fixed
- stale local state is repaired or deliberately ruled out when relevant
- the canonical provider/view state updates without manual refresh
- targeted tests cover the contract where feasible
- relevant custom lint/contract enforcement is added when the static signal is
  honest
- the fix is verified on-device when the issue was originally device-reported

## Architecture Rules Driving This Spec

- One state-ownership rule per screen:
  - detail screens render live provider/model state, not stale screen-local
    copies after mutation
- One mutation contract:
  - every create/update/delete must either update canonical provider state or
    trigger an immediate required reload path
- One route-intent layer:
  - continue today, new entry, open submitted, edit draft, and adjacent entry
    actions must flow through shared route-intent helpers
- One preload contract:
  - screens and sheets must not expose interactive controls before their
    required builtin/project data is ready
- One responsive content contract:
  - dialogs and sheets must have explicit constraints and visible scrolling
    affordances
- One sync recovery rule:
  - any sync bug that can poison local state is incomplete without a repair path

## Spec Matrix

### A. State Ownership And Mutation Refresh

#### A1. Project deletion refresh

- User note:
  - deleting a project leaves stale UI until manual refresh
- Current source status:
  - `ProjectProvider.deleteProject()` already removes the project and rebuilds
    merged state, and optionally refetches remote projects
- Files:
  - `lib/features/projects/presentation/providers/project_provider_mutations.dart`
  - `lib/features/projects/presentation/providers/project_provider_data_actions.dart`
- Current assessment:
  - likely partially fixed in source, but still needs device verification across
    project list, dashboard selection, and any dependent widgets
- Required contract:
  - delete must remove the item from the visible canonical collection without a
    pull-to-refresh
  - if the deleted project was selected, selection must move to a valid fallback
    state immediately

#### A2. Activities edit does not render saved text

- User note:
  - after editing Activities and tapping Done, the typed text does not show
- Verified source gap:
  - `EntryActivitiesSection` view mode renders
    `DailyEntry.activitiesDisplayText(entry?.activities)` from the widget entry
    snapshot
  - the section exits edit mode before the provider-backed entry refresh is
    guaranteed to be visible
- Files:
  - `lib/features/entries/presentation/widgets/entry_activities_section.dart`
  - `lib/features/entries/presentation/controllers/entry_editing_controller.dart`
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart`
- Root-cause class:
  - state-ownership drift between controller-owned live draft text and
    widget-entry snapshot rendering
- Required contract:
  - after save, the read-only section must render the just-saved value from the
    live canonical state path without requiring a full screen reload

#### A3. Cross-account trash contamination

- User note:
  - another account can see prior account trash items
- Files:
  - `lib/features/settings/presentation/screens/trash_screen.dart`
  - `lib/features/settings/presentation/controllers/trash_screen_controller.dart`
  - `lib/features/settings/data/repositories/trash_repository.dart`
  - `lib/services/soft_delete_service.dart`
- Verified source seam:
  - `TrashRepository.getDeletedItems()` filters non-admin rows by
    `deleted_by = userId`
  - this is likely too weak for multi-user/multi-project shared-device state
- Required contract:
  - non-admin users only see trash records they are allowed to restore/delete
  - account switch must not preserve prior user trash view state
- 2026-04-09 source/test hardening:
  - `TrashScreen` now treats `userId + isAdmin` as a reload boundary instead
    of loading once for the life of the mounted screen
  - when auth scope changes:
    - grouped trash state resets
    - selection/filter state clears
    - trash items reload for the new scope
  - contract test now simulates an in-place user switch and proves the first
    user's trash rows are replaced by the second user's rows
- Honest status:
  - source/test-closed for mounted-screen account switching
  - still needs real multi-account device verification before it can leave the
    live backlog

### B. Entry Flow Honesty And Date Handling

#### B1. Continue Today title honesty

- User note:
  - opening an existing entry from dashboard still says `New Entry`
- Current source status:
  - `EntryEditorAppBar` now uses the entry date when an entry exists
- Files:
  - `lib/features/dashboard/presentation/widgets/dashboard_todays_entry.dart`
  - `lib/features/entries/presentation/widgets/entry_editor_app_bar.dart`
- Current assessment:
  - likely fixed in source; needs device verification

#### B2. Submitted today entry should prompt instead of starting a new entry

- User note:
  - submitted entry should offer unsubmit/open, not silently create new
- Current source status:
  - `DashboardTodaysEntry` already prompts the user and calls
    `undoSubmission()` before opening when requested
- Files:
  - `lib/features/dashboard/presentation/widgets/dashboard_todays_entry.dart`
  - `lib/features/entries/presentation/providers/daily_entry_provider_submission_actions.dart`
  - `lib/features/entries/presentation/screens/entry_editor_dialogs.dart`
- Current assessment:
  - closed 2026-04-09 with source, contract-test, and S21 device verification

#### B3. Entry date editing / backdating

- User notes:
  - backdating via calendar already works and must be preserved
  - users need an intuitive way to make a report for a different date
- Files:
  - `lib/features/dashboard/presentation/widgets/dashboard_todays_entry.dart`
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart`
  - `lib/features/entries/presentation/widgets/entry_header_card.dart`
  - `lib/features/entries/presentation/widgets/home_calendar_section.dart`
- Current assessment:
  - feature gap, not just bug

#### B4. Daily-entry PDF preview red screen

- User note:
  - entry export/preview hit another red screen on-device
- Verified root cause:
  - this was a `printing` package race, not a stale IDR/PDF mapping problem
  - `PdfPreviewRaster._raster()` checked `mounted`, awaited `page.toPng()`,
    then wrote back into `pages[pageNum]`
  - if the preview disposed during that await, `dispose()` cleared `pages` and
    the resumed write crashed with `RangeError`
- Files:
  - `third_party/printing_patched/lib/src/preview/raster.dart`
  - `pubspec.yaml`
  - `test/core/exports/printing_raster_patch_contract_test.dart`
- Required contract:
  - previewing an already-generated entry PDF must not red-screen if the
    preview route is rebuilding or being torn down while the preview raster is
    still in flight
- 2026-04-09 closure:
  - app now uses a vendored patched `printing` package
  - the patched raster path re-checks `mounted` after `await page.toPng()` and
    safely handles list shrinkage before write-back
  - verified on the S21 after reinstall by reopening the same
    `Continue Today's Entry -> Export PDF` flow with a cleared log buffer and
    no new `RangeError` / `Duplicate GlobalKey` entries

#### B5. Daily-entry / IDR PDF mapping fidelity

- User notes:
  - entry PDF mappings are still wrong
  - contractor/equipment rows do not line up with the real PDF
  - equipment check-state is not honestly represented
  - exported text must preserve the canonical template formatting
- Canonical source of truth:
  - `Pre-devolopment and brainstorming/Form Templates for export/IDR 2019-XX-XX Initials.pdf`
  - shipped runtime template: `assets/templates/idr_template.pdf`
- Verified audit findings:
  - the writer does not currently set the day dropdown field
  - the writer only fills text fields; checkbox state is not written
  - equipment rows are under-mapped relative to the real template
  - equipment row assignment is position-based and currently depends on load
    order instead of a stable export order
  - the first subcontractor personnel block is only partially mapped
- Files:
  - `lib/features/pdf/services/idr_pdf_template_writer.dart`
  - `lib/features/entries/presentation/controllers/pdf_data_builder.dart`
  - `test/features/forms/services/form_export_mapping_matrix_test.dart`
  - `test/services/pdf_field_mapping_test.dart`
- Required contract:
  - the exported IDR must preserve the canonical AcroForm field structure
  - contractor/personnel/equipment rows must map deterministically
  - used equipment must be visible both by text row and checkbox state
  - blank/unused rows must clear cleanly
  - daily-entry export must continue to use the canonical clean template and
    must remain editable after export

#### B6. Connectivity recovery / stale offline state

- User note:
  - after connectivity is restored, the app can stay on a blank dashboard with
    a stuck offline banner
- Live S21 proof:
  - Android connectivity was validated as restored while the app still showed
    `Select Project`, an offline banner, and a spinner/blank dashboard state
- Proof artifacts:
  - `.codex/tmp/live_debug/post-adb-recover.png`
  - `.codex/tmp/live_debug/post-network-restore-2.png`
  - `.codex/tmp/live_debug/post-retry-tap.png`
- Files:
  - `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`
  - `lib/features/sync/presentation/providers/sync_provider.dart`
  - `lib/features/network/` and app-lifecycle connectivity owners
- Required contract:
  - when Android connectivity returns, the app must clear stale offline state,
    recover to a valid visible project/dashboard state, and not strand the user
    behind a stale banner/loading view

### C. Responsive Layout And Dialog/Sheet Contracts

#### C1. Equipment manager scroll affordance

- User note:
  - equipment popup only shows one row at a time and scrolling is unclear
- Files:
  - `lib/features/entries/presentation/widgets/equipment_manager_dialog.dart`
  - `lib/features/projects/presentation/widgets/add_equipment_dialog.dart`
- Current source status:
  - `EquipmentManagerDialog` now has constrained height, scrollbar, and helper
    copy when multiple rows exist
- Current assessment:
  - closed 2026-04-09 for the contractor equipment-manager path with source,
    widget tests, and S21 device verification
  - still worth verifying whether other standalone equipment dialogs use the
    same contract

#### C2. Calendar overflow

- User note:
  - calendar screen overflows instead of adapting
- Files:
  - `lib/features/entries/presentation/widgets/home_calendar_section.dart`
  - `lib/features/entries/presentation/screens/home_screen.dart`
  - `lib/core/design_system/layout/`
- Verified source seam:
  - `HomeCalendarSection` uses `TableCalendar` inside a plain `Column`
    without responsive constraints beyond the surrounding screen

#### C3. Windows dashboard duplicate side panel

- User note:
  - Windows/dashboard two-pane mode shows the same content twice and is not
    useful yet
- Files:
  - `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`
- Verified source gap:
  - large breakpoint currently renders `_DashboardScrollView` plus
    `_DashboardSidePanel`, and the side panel duplicates quick stats/budget

### D. Forms Gallery And Preload Contracts

#### D1. Forms screen empty / add sheet stuck

- User note:
  - Forms screen shows no forms
  - tapping `+` opens an unusable bottom sheet
- Files:
  - `lib/features/forms/presentation/screens/form_gallery_screen.dart`
  - `lib/features/forms/presentation/providers/inspector_form_provider.dart`
  - `lib/features/forms/presentation/providers/document_provider.dart`
  - `lib/core/design_system/surfaces/app_bottom_sheet.dart`
- Current source status:
  - the bottom-sheet contract itself was improved
  - `FormGalleryScreen` still relies on opportunistic builtin-form loading in
    `didChangeDependencies()`
- Root-cause class:
  - preload contract gap

#### D2. Saved responses do not show after saving 0582B

- User note:
  - saved 0582B does not appear in the saved responses section
- Files:
  - `lib/features/forms/presentation/screens/form_gallery_screen.dart`
  - `lib/features/forms/presentation/providers/document_provider.dart`
  - `lib/features/forms/presentation/providers/inspector_form_provider_response_actions.dart`
- Current assessment:
  - likely stale preload/reload contract between response save and gallery list

#### D3. Generic form attachment contract

- Product intent:
  - attachable forms should share one entry-link contract instead of each form
    inventing its own entry-picker / create-entry / attach mutation flow
  - pay apps remain outside this contract
- 2026-04-09 source status:
  - `ResolveFormAttachmentEntryUseCase` and
    `CreateFormAttachmentEntryUseCase` now own generic entry candidate lookup
    and create-for-attach behavior
  - `FormEntryAttachmentOwner` now owns the shared picker/attach flow
  - `AttachStep` and `FormsListScreen` both route through that shared owner
  - new lint `no_form_response_entry_attachment_mutation_outside_owner` blocks
    raw `copyWith(entryId: ...)` drift in form presentation code
- Honest status:
  - source/test/lint closed
  - still needs device proof that attached forms continue to bundle/export
    correctly after the generic attachment refactor

#### D4. Attached form cards inside entry editor

- User note:
  - once a form is already attached inside an entry, the card should not show
    internal quick-action chips like `+ Test`, `+ Proctor`, or `+ Weights`
  - the card should show the export-style filename for the attachment
  - that name must be editable because inspectors/company workflows use file
    naming conventions
  - tapping the attachment card should open the actual form wizard/editor
  - `View Form` must stay available as a fast preview/verification action
- Device proof of the pre-fix failure:
  - `.codex/tmp/live_debug/entry-attached-0582b-forms-visible.png`
- Files:
  - `lib/features/entries/presentation/widgets/entry_form_card.dart`
  - `lib/features/entries/presentation/widgets/entry_forms_section.dart`
  - `lib/features/forms/data/services/form_attachment_display_name_policy.dart`
  - `lib/features/forms/data/services/form_export_filename_policy.dart`
- Required contract:
  - all attached forms render through the same generic attachment-card pattern
  - export/display naming comes from one shared policy
  - editing the attachment name updates the same filename policy used by export
  - preview is separate from edit/open-form intent
- 2026-04-09 closure:
  - source/test/lint are now closed for the shared attachment-card contract
  - S21 device proof is closed on the real attached 0582B row:
    - no internal `+ Test / + Proctor / + Weights` chips remain
    - the card shows the export-style filename
    - tapping the card opens the real 0582B wizard/editor
    - `View Form` opens the real PDF preview shell
    - renaming the attachment persists the new filename
      `CompanyPrefix_0582B_Apr08.pdf`
  - shared seam hardening:
    - `AppTextField` now forwards its key to the underlying `TextFormField`,
      which made the rename dialog honestly driver-testable instead of only
      wrapper-detectable
  - proof artifacts:
    - `.codex/tmp/live_debug/entry-editor-after-scroll-forms.png`
    - `.codex/tmp/live_debug/entry-form-card-open-result.png`
    - `.codex/tmp/live_debug/entry-form-card-preview-result.png`
    - `.codex/tmp/live_debug/entry-attachment-renamed-final.png`

### E. 0582B Domain Correctness And Export Flow

#### E1. Station formatting should include `+`

- User note:
  - station in quick test should display `xx+xx`
- Files:
  - `lib/features/forms/presentation/widgets/hub_quick_test_content.dart`
  - `lib/features/forms/presentation/widgets/form_viewer_sections.dart`
  - possible formatter helpers to be added
- Verified source gap:
  - station is rendered raw, with no display formatter

#### E2. Item of work values are wrong / need names and density requirements

- User note:
  - item-of-work options are not aligned with the 0582B PDF/table
  - app should show human names while export maps to the corresponding code
  - density requirement data must be visible
- Files:
  - `lib/features/forms/presentation/widgets/hub_quick_test_content.dart`
  - `lib/features/forms/data/pdf/mdot_0582b_pdf_filler.dart`
  - new 0582B constants/lookup module likely needed
- Verified source gap:
  - quick test currently hardcodes `Mainline / Shoulder / Other`
  - PDF filler writes `item_of_work` directly

#### E3. Original/recheck numbering logic

- User note:
  - originals should number chronologically
  - rechecks should sequence after the original until a passing test
- Files:
  - `lib/features/forms/presentation/controllers/mdot_hub_controller.dart`
  - `lib/features/forms/presentation/controllers/mdot_hub_controller_actions.dart`
  - `lib/features/forms/data/services/mdot_0582b_calculator.dart`

#### E4. Export should not be blocked by missing required fields

- User note:
  - 0582B export should still work with missing fields
- Verified source gap:
  - `validateMdot0582B()` adds export-only required fields
  - `FormResponseRepository.markAsExported()` rejects export when missing fields exist
- Files:
  - `lib/features/forms/data/validators/mdot_0582b_validator.dart`
  - `lib/features/forms/data/repositories/form_response_repository.dart`
- Current source status:
  - hub export path no longer blocks on `validateForExport()` inside
    `ExportFormUseCase`
  - generic `markAsExported()` validation still exists and should be revisited
    only if the generic form-viewer export flow needs the same product contract

#### E5. Decimal precision should be `.0`, not `.00`

- User note:
  - 0582B should display one decimal place
- Files:
  - `lib/features/forms/presentation/widgets/hub_quick_test_content.dart`
  - `lib/features/forms/presentation/widgets/form_viewer_sections.dart`
  - `lib/features/forms/presentation/controllers/mdot_hub_controller_*`
  - `lib/features/forms/data/pdf/mdot_0582b_pdf_filler.dart`

#### E6. Export flow UX is broken

- User note:
  - multiple bottom sheets
  - no file path selection
  - need export-to-dated-folder support
  - should ask whether to attach this to a form or export as-is
- Files:
  - `lib/features/forms/presentation/screens/mdot_hub_screen.dart`
  - `lib/features/pdf/services/pdf_output_service.dart`
  - `lib/features/forms/data/services/form_pdf_service.dart`

#### E7. Entry export contract drift

- Product/architecture note:
  - entry export is part of the same export-artifact contract as forms/pay apps
  - preview/save/share/export-record behavior should not drift between old
    dialogs and preview screens
- 2026-04-09 source status:
  - entry save/share/export-record ownership now lives in
    `EntryPdfActionOwner`
  - `EntryPdfPreviewScreen` uses the shared owner
  - dead `report_pdf_actions_dialog.dart` and
    `report_debug_pdf_actions_dialog.dart` surfaces were removed
  - new lint `no_direct_entry_pdf_actions_outside_owner` now blocks save/share
    drift from reappearing in entry presentation files
- Honest status:
  - source/test/lint closed
  - still needs S21 verification after the owner migration

### F. Resume, Restoration, And Navigation Recovery

#### F1. App foreground resume becomes slow/stuck

- User note:
  - app comes back slowly from background and can feel frozen
- Files:
  - `lib/features/sync/application/sync_lifecycle_manager.dart`
  - `lib/core/router/app_router.dart`
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart`
- Current source status:
  - some resume-sync throttling/restoration exclusions were already added
- Current assessment:
  - still needs broader app-wide verification

#### F2. Back from resumed screen closes the app / restoration loops

- User note:
  - after backgrounding, back can close the app and restart to the same bad
    screen
- Files:
  - `lib/core/router/app_router.dart`
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart`

## Lint-First Backlog

### Ready To Implement Honestly

- `no_dashboard_duplicate_side_panel_before_desktop_redesign`
- `no_form_creation_action_before_builtin_forms_ready`
  - only after builtin-form readiness has a shared owner
- `no_raw_0582b_item_of_work_options`

### Not Honest Enough Yet For Static Lint Alone

- state ownership per screen
- mutation contract completeness
- foreground resume safety
- trash scope correctness

## Contract Test Backlog

- activities save shows visible text immediately
- project delete removes the item without manual refresh
- continue today opens existing draft honestly
- submitted today entry prompts for open vs revert
- forms `+` action stays disabled until builtin forms are loaded
- forms add sheet never opens empty when enabled
- wide dashboard does not render duplicate quick-stats/budget content
- incomplete 0582B export still produces an editable export artifact
- account switch does not leak prior account trash rows
- app resume/back does not strand the user on a broken root stack

## Implementation Order

### Wave 1

- save this spec + append tracker references
- fix activities state-ownership rendering
- remove duplicate wide dashboard side panel
- add tests for those two issues

Status:
- completed
- landed:
  - `EntryActivitiesSection` now renders read-only activities from the live
    controller snapshot first, closing the stale-after-save gap
  - `ProjectDashboardScreen` no longer renders the temporary duplicate large
    side panel
  - regression test added:
    - `test/features/entries/presentation/widgets/entry_activities_section_test.dart`

### Wave 2

- formalize forms preload contract
- fix forms gallery/create flow honesty
- add the preload contract tests

Status:
- partially completed
- landed:
  - `FormGalleryScreen` now blocks interactive create flow until builtin forms
    are actually ready
  - the gallery now shows an honest loading/empty-preload state instead of a
    misleading empty interactive surface
  - the add-form bottom sheet now closes with the sheet context instead of the
    parent screen context, which matches the stuck-sheet root cause
  - preload contract tests added/updated in
    `test/features/forms/presentation/screens/form_gallery_screen_test.dart`

### Wave 3

- fix 0582B correctness:
  - item of work registry
  - station formatting
  - precision formatting
  - export-with-missing-fields policy

### Wave 4

- audit and repair trash/account scoping
- continue resume/restoration hardening
- add any new repair jobs required by dirty upgrade/device state

## Honest Status Snapshot At Spec Creation

- already likely fixed in source but still needs device verification:
  - continue-today title honesty
  - submitted-today prompt
  - some equipment dialog scroll affordance work
- actively unresolved in source:
  - 0582B export policy/domain fidelity
  - trash cross-account leakage
  - remaining resume/back-stack edge cases
- newly improved in source and awaiting broader device verification:
  - activities immediate render after save
  - dashboard wide duplicate panel removal
  - forms preload honesty and add-sheet closure path
  - incomplete 0582B export no longer blocked on the hub export path

## 2026-04-08 23:59 ET Additional 0582B + Gallery Closure

### Landed

- Added a real 0582B item-of-work catalog backed by page 2 of the shipped
  PDF template:
  - `lib/features/forms/data/registries/mdot_0582b_item_of_work_catalog.dart`
- Added shared 0582B display formatting helpers:
  - one-decimal formatting
  - station `xx+xx` formatting
  - station input formatter
  - `lib/features/forms/data/services/mdot_0582b_display_formatter.dart`
- Updated the 0582B quick-test UI so it no longer uses fake
  `Mainline / Shoulder / Other` placeholders:
  - dropdown now uses the shipped catalog codes
  - the screen now shows the real item description, minimum compaction, export
    code, and spec section
  - station entry now auto-formats with `+`
  - calculated values now display to one decimal
- Updated read-only 0582B surfaces to use the same formatting rules:
  - `form_viewer_sections.dart`
  - `entry_form_card.dart`
- Updated 0582B PDF export mapping:
  - station values are normalized to `xx+xx`
  - item-of-work exports use the correct code even when a description is stored
  - numeric output is normalized to one decimal where the form is user-facing
- Fixed the saved-responses stale list path in Forms Gallery:
  - returning from a form now reloads `DocumentProvider` for the active project
  - this covers both opening an existing response and creating a new response
- Added lint:
  - `no_raw_0582b_item_of_work_options`
  - purpose: prevent the old fake inline item-of-work options from coming back

### Also Closed

- The generic form-viewer export path now matches the product rule that exports
  are artifacts, not a terminal lock:
  - exported form responses remain editable
  - already-exported responses can be exported again
  - `markAsExported()` no longer acts like an export-completeness gate after
    the PDF has already been generated successfully

### Verification

- `flutter analyze` on the touched forms/gallery/export files: green
- `flutter test`
  - `test/features/forms/data/registries/mdot_0582b_item_of_work_catalog_test.dart`
  - `test/features/forms/data/services/mdot_0582b_display_formatter_test.dart`
  - `test/features/forms/data/pdf/mdot_0582b_pdf_filler_test.dart`
  - `test/features/forms/presentation/screens/form_gallery_screen_test.dart`
  - `test/features/forms/data/repositories/form_response_repository_test.dart`
  - `test/features/forms/presentation/controllers/form_viewer_controller_test.dart`
- `dart test`
  - `fg_lint_packages/field_guide_lints/test/architecture/no_raw_0582b_item_of_work_options_test.dart`
- root `dart run custom_lint`: green

### Honest Remaining Gaps

- 0582B original/recheck numbering behavior is still not fully aligned with the
  user note yet; this pass fixed the catalog/formatting/export contract, not
  the test-number sequencing logic.
- 0582B export destination UX is still open:
  - dated-folder selection
  - attach-vs-export decision
  - multiple-bottom-sheet cleanup
- broader app issues from the spec are still open:
  - trash cross-account scope
  - calendar overflow
  - resume/back-stack recovery

## 2026-04-09 00:34 ET Next Iteration Slice

### Newly Confirmed Root Causes

- `MDOT 1126` header preload is broken because the form does not honor one
  canonical header store:
  - create/carry-forward uses `FormResponse.headerData`
  - render/edit path uses nested `responseData['header']`
- Pay-app export is still incomplete for the actual intended field workflow:
  - users need a project workbook that accumulates pay apps over time
  - current export flow only produces a one-off workbook artifact and then
    offers one-off file actions

### TODO: Immediate Implementation Order

- [ ] make `headerData` the canonical MDOT 1126 header source
- [ ] add shared builtin-form header autofill helpers for 1126-style headers
- [ ] migrate legacy nested `responseData['header']` forward on load/edit
- [ ] add regression coverage so a fresh 1126 draft renders seeded header data
- [ ] add a pay-app project-workbook export path that accumulates saved pay apps
- [ ] update pay-app export UX copy/actions so the workflow is honest
- [ ] add regression coverage for project-workbook export behavior

## 2026-04-09 06:04 ET Implemented Slice

### Closed In This Pass

- [x] make `headerData` the canonical MDOT 1126 header source
- [x] add shared builtin-form header autofill helpers for 1126-style headers
- [x] migrate legacy nested `responseData['header']` forward on load/edit
- [x] add a pay-app project-workbook export path that accumulates saved pay apps
- [x] update pay-app export UX copy/actions so the workflow is honest
- [x] add regression coverage for project-workbook export behavior

### What Changed

- MDOT 1126 / SESC:
  - `FormHeaderOwnershipService` now owns legacy-header migration
  - screen load normalizes older records into canonical `headerData`
  - header step now reads only the canonical header map
- Pay App:
  - canonical project workbook is now rebuilt and written under a stable local
    project-specific path on each successful export
  - `Save Project Workbook` now saves a copy of that maintained workbook
    instead of relying on a one-off rebuild only when the button is tapped
- Enforcement:
  - new lint `no_nested_form_header_access_outside_header_owners`

### Remaining TODOs From This Area

- [ ] run manual/device validation for the updated pay-app workbook flow
- [ ] continue broader SESC hardening beyond header ownership

### Additional Coverage Landed

- [x] widget-level regression coverage that the 1126 header screen renders
  seeded canonical header values
  - `test/features/forms/presentation/widgets/header_step_test.dart`

## 2026-04-09 06:28 ET Device Validation Results

### Closed On Device

- A2. Activities edit does not render saved text
  - closed on the S21
  - entered `Placed erosion controls and verified traffic setup.`
  - read-only activities section rendered the new value immediately after save
- B1. Continue Today title honesty
  - closed on the S21
  - today-entry reopen shows `Apr 9, 2026`, not `New Entry`
- D2. Saved responses do not show after saving 0582B
  - effectively closed for the current build
  - Forms Gallery showed populated saved responses for both:
    - `MDOT 1126 Weekly SESC`
    - `MDOT 0582B Density`
- E5. 0582B display precision
  - partially validated on-device
  - quick-test values are rendering at one decimal (`119.0`, `131.5`, `98.5`)
- F cold-start expectation
  - force-stop + relaunch returns to `Projects` when auth is not needed
  - this matches the product expectation for a true cold restart

### Still Open After Device Validation

- C2. Calendar overflow
  - still open
  - reproduced on-device with live overflow stripe:
    `BOTTOM OVERFLOWED BY 154 PIXELS`
- D1. Forms screen empty / add sheet stuck
  - partially improved, not honestly closed
  - improved:
    - forms gallery is populated
    - `+` sheet now shows real options
    - `Scroll for more` affordance is visible
  - still open:
    - selecting `MDOT 1126 Weekly SESC` from the sheet dismissed it and left
      the app on `/forms` instead of clearly opening a create flow
- 1126 / SESC header preload standardization
  - partially improved, not closed
  - on-device saved-response open showed:
    - project name populated
    - contractor name populated
    - inspector name populated
  - still blank:
    - permit number
    - location
- E6. Pay-app export destination UX
  - improved, but not fully aligned with the desired vision yet
  - confirmed:
    - export workflow now reaches a clean post-export dialog
    - `Save Project Workbook` opens Android DocumentsUI
  - still open:
    - picker opened into a generic folder-selection flow, not an obviously
      dated export destination
    - attach-vs-export decision remains open

### New Device-Only Finding Added To Spec

#### F3. External picker resume / restoration drift

- New root-cause class:
  - app restoration loses project-scoped context after leaving for external
    Android file-picker flows
- Repro from live device:
  - open `Pay Items`
  - export a pay app
  - tap `Save Project Workbook`
  - Android DocumentsUI opens
  - relaunch app from launcher
- Observed result:
  - app resumes into orphaned `Pay Items` with `0 items`
  - visible screen and driver route diverge
  - Android back returns to the picker task instead of a valid app root
- Control case:
  - force-stop + relaunch returns correctly to `Projects`
- Required contract:
  - returning from external pickers must restore a valid project-scoped route
    or fall back cleanly to `Projects`
  - route state and visible UI must not diverge after resume
  - app back must never resurrect the picker task as the next “screen”

### Device Validation Artifact Set

- `.codex/tmp/s21-1126-saved-response-open.png`
- `.codex/tmp/s21-0582b-saved-response-open.png`
- `.codex/tmp/s21-pay-app-export-finished.png`
- `.codex/tmp/s21-pay-app-save-workbook-system-picker.png`
- `.codex/tmp/s21-activities-after-save.png`
- `.codex/tmp/s21-continue-today-reopen.png`
- `.codex/tmp/s21-calendar-screen.png`
- `.codex/tmp/s21-calendar-entry-open.png`

### Next Fix Order Updated From Device Truth

- fix F3 external-picker resume/restoration drift first
- fix C2 calendar overflow
- finish 1126 header preload completion (`Permit number`, `Location`)
- return to D1 forms-gallery create flow with deterministic keyed targets and
  close or fix the remaining `+`-sheet dismissal behavior

## 2026-04-09 07:12 ET Source Closure Before Next Device Pass

### Checked Off In Source

- [x] F3. External-picker resume/restoration drift
  - `AppRouter.isRestorableRoute()` is now root-route only for restoration and
    explicitly rejects project-scoped utility/editor/export flows
  - `QuantitiesScreen` now reloads project-scoped providers when selected
    project context is restored after first build, which closes the observed
    orphaned `Pay Items / 0 items` path in source
- [x] C2. Calendar overflow fix landed in source
  - compact home/day content now uses a scrollable layout instead of nesting
    `Expanded` content inside a narrow stacked column path
- [x] D1. Forms `+` create flow is fixed in source
  - the add sheet now returns the selected form from the sheet context
  - selecting `MDOT 1126 Weekly SESC` now routes through the shared
    `form-new` dispatcher instead of dismissing back to `/forms`
- [x] 1126 header preload completion is fixed in source
  - `MDOT 1126` header autofill now falls back permit from
    `mdotContractId -> controlSectionId -> projectNumber`
  - location now falls back from `routeStreet -> first project location ->
    mdotCounty`

### Regression Validation For This Slice

- `flutter analyze` on the affected router/quantities/forms/calendar files: green
- `flutter test`
  - `test/features/quantities/presentation/screens/quantities_screen_test.dart`
  - `test/features/forms/presentation/screens/form_gallery_screen_test.dart`
  - `test/core/router/app_router_test.dart`
- root `dart run custom_lint`: green

### Still Requires On-Device Proof

- [ ] confirm pay-app export -> Android picker -> launcher resume no longer
      strands the app on an orphaned pay-items screen
- [ ] confirm the calendar overflow is gone on the S21
- [ ] confirm selecting `MDOT 1126 Weekly SESC` from Forms `+` visibly opens the
      create flow on-device
- [ ] confirm `Permit number` and `Location` are populated in the live 1126
      header flow on-device

## 2026-04-09 07:20 ET Device Revalidation Of The Latest Source Slice

### Closed On Device

- [x] C2. Calendar overflow
  - revalidated on the S21
  - no overflow stripe in the live screen
  - no `BOTTOM OVERFLOWED` / `RenderFlex overflowed` logs after opening
    Calendar
- [x] D1. Forms `+` create flow
  - revalidated on the S21
  - the bottom sheet renders correctly
  - selecting the sheet instance of `MDOT 1126 Weekly SESC` opens the 1126
    form create flow instead of dropping back to the gallery
- [x] 1126 header preload completion
  - revalidated on the S21
  - live header now shows:
    - `Project name: Springfield DWSRF`
    - `Contractor name: City of Springfield`
    - `Inspector name: E2E Test Admin`
    - `Permit number: 864130`
    - `Location: Barberry`

### Still Open After Revalidation

- [!] F3. External picker resume / restoration drift is only partially improved
  - improvement:
    - the old `Pay Items / 0 items` orphaned blank-state repro did not return
  - still broken:
    - after `Save Project Workbook` -> launcher relaunch, the visible UI came
      back to dashboard while the driver route still reported `/quantities`
    - pressing Android back resurfaced `DocumentsUI` again instead of staying
      inside the app
  - honest status:
    - the worst stale-project-state symptom is improved
    - route/UI restoration truth and back-stack recovery are still not closed

### New Requirement Added During Validation

- [ ] 1126 preview/export parity
  - user direction:
    - `MDOT 1126` needs the same preview affordance as the other forms
  - verified source gap:
    - `Mdot1126FormScreen` app bar currently has no preview/export actions
    - unlike `FormViewerScreen` and `MdotHubScreen`, it does not expose the
      standard preview/export shell

## 2026-04-09 08:05 ET MDOT 1126 Parity And Picker Resume Retest

### Closed In Source

- [x] 1126 preview/export parity
  - `Mdot1126FormScreen` now exposes the standard preview/export app-bar
    actions
  - preview uses the shared `FormPdfPreviewScreen`
  - export uses `FormExportProvider` + shared file sharing path
- [x] Android launcher resume hardening for external picker flows
  - `MainActivity` launch mode is now `singleTask`
  - relaunching from the launcher clears the old above-activity picker stack
    instead of leaving `DocumentsUI` behind the app

### Regression Validation

- `flutter analyze`
  - `lib/features/forms/presentation/screens/mdot_1126_form_screen.dart`
  - `test/features/forms/presentation/screens/mdot_1126_form_screen_test.dart`
- `flutter test`
  - `test/features/forms/presentation/screens/mdot_1126_form_screen_test.dart`
- root `dart run custom_lint`

### Closed On Device

- [x] 1126 preview/export parity
  - 1126 now shows both preview and export icons in the app bar on the S21
  - tapping preview opens the live `PDF Preview` screen for the 1126 form
- [x] External picker resume/back-stack lockout
  - repro rerun:
    - export pay app
    - tap `Save Project Workbook`
    - `DocumentsUI` opens
    - relaunch app from launcher
    - press Android back
  - result on the new build:
    - app resumes back into the pay-app flow
    - Android back returns to `Pay Items`
    - `DocumentsUI` no longer resurfaces behind the app

### Residual Non-Blocking Diagnostics Issue

- [ ] driver route reporting after launcher relaunch
  - after the picker resume relaunch, visible UI showed pay-app detail while
    `/driver/ready` still reported `/quantities`
  - user-facing navigation/back behavior is now correct
  - remaining issue appears limited to driver route inspection truth rather than
    production routing behavior

## 2026-04-09 09:15 ET Audit Reconciliation: Unverified Closure Backlog

This backlog exists to separate true remaining work from items that were fixed
in source but never fully proven, or were only partially proven during the
overnight/device passes.

### Open Product Work

- [ ] A3. Cross-account trash contamination
  - no later closure was recorded after the original report
  - required proof:
    - switching accounts on the same device does not show prior-user trash
    - non-admin trash visibility is scoped correctly
- [ ] B3. Entry date editing / different-date report flow
  - calendar backdating works, but the explicit in-flow date-edit affordance is
    still a feature gap
  - required proof:
    - entry/new-entry flow exposes an honest date-edit path without regressing
      existing calendar backdating
- [ ] E3. 0582B original/recheck numbering logic
  - still explicitly open in the spec/tracker
  - required proof:
    - originals increment chronologically
    - rechecks chain correctly until a passing test resets the path
- [ ] E6. 0582B export destination UX
  - still open:
    - dated-folder support
    - attach-vs-export decision
    - cleanup of the multi-surface export flow
- [ ] 1126 / SESC broader hardening beyond header preload
  - header autofill and preview/export parity are closed, but broader wizard
    and carry-forward friction were never fully closed
- [ ] grouped conflict viewer usefulness
  - latest device notes still describe grouped conflict cards as too generic to
    be actionable
- [ ] support-facing sync issue taxonomy
  - simplified user sync status exists, but report classification is still too
    weak to make issue reports consistently actionable

### Source-Landed But Still Needing Honest Closure

- [x] A1. Project deletion refresh
  - closed 2026-04-09 with fresh S21 proof
  - device results:
    - `Remove from device` now removes the project from `My Projects`
      immediately with no manual refresh
    - the empty-state screen appears right away with `No projects on your
      device`
    - a full cold relaunch keeps the project out of `My Projects`; it remains
      available/not-downloaded instead of silently reappearing on-device
    - explicit user download from `Company -> Remote` restores the project
      normally:
      - download confirmation appears
      - import completes successfully
      - the project returns as `On Device`
  - source fixes now closed together:
    - provider selection fallback repair for active-project deletion
    - enrolled/on-device semantics now come from
      `projects INNER JOIN synced_projects` instead of raw metadata-row
      presence
    - delete sheet moved onto the scrollable bottom-sheet contract so the
      confirm action remains reachable even when a persistent sync banner is
      present
    - delete sheet gained explicit bottom action clearance so the sync error
      banner cannot hide the confirm button on smaller screens
    - explicit local removal now writes a manual-removal marker and both
      enrollment owners respect it:
      - application `SyncEnrollmentService`
      - engine `EnrollmentHandler`
- [x] B2. Submitted today entry prompt path
  - closed 2026-04-09 with explicit S21 proof
  - device results:
    - dashboard correctly shows `Today's Entry Submitted` after submitting the
      existing Apr 9, 2026 Springfield draft
    - tapping the card opens `Today's Entry Already Exists`
    - `Open Submitted` opens the existing submitted report instead of creating
      a new entry
    - `Revert to Draft` reopens the same entry in editable state and shows
      `Entry reverted to draft`
    - backing to dashboard after revert restores the honest draft state:
      `1 Draft — Tap to Review` plus `Continue Today's Entry`
  - proof artifacts:
    - `.codex/tmp/s21-after-submit-confirm.png`
    - `.codex/tmp/s21-submitted-entry-prompt.png`
    - `.codex/tmp/s21-open-submitted-branch.png`
    - `.codex/tmp/s21-revert-to-draft-branch.png`
    - `.codex/tmp/s21-dashboard-after-revert-back.png`
- [x] C1. Equipment manager scroll/discovery
  - closed 2026-04-09 for the entry contractor equipment-manager path
  - source changes:
    - stop auto-focusing the name field when equipment already exists so the
      list is visible on open
    - always show the scroll helper copy when more than one equipment item is
      present
    - wrap the dialog content in a constrained `SingleChildScrollView` and
      shrink the equipment-list viewport under keyboard insets
  - device results on S21:
    - opening `Manage Equipment for Hoffman Brothers` no longer auto-opens the
      keyboard
    - existing equipment rows are visible immediately on open
    - helper copy now makes scrolling/discovery explicit
    - focusing the name field no longer shows the yellow/black overflow stripe
      that previously reproduced on-device
  - proof artifacts:
    - `.codex/tmp/s21-equip-final-open.png`
    - `.codex/tmp/s21-equip-final-keyboard.png`
  - remaining caution:
    - this closes the contractor equipment-manager path that matched the user
      report
    - the separate standalone add/edit equipment dialogs should still be
      audited if they are meant to follow the same responsive contract

## 2026-04-09 09:52 ET S21 Validation: Equipment Manager Closed

- Recreated the original equipment-manager complaint on the live Springfield
  draft with a contractor that already had equipment.
- Final source approach:
  - localize the fix to `EquipmentManagerDialog`
  - do not auto-open the keyboard when the user needs to review existing
    equipment first
  - keep the dialog keyboard-safe with local scroll constraints instead of a
    broad dialog-host behavior change
- Device proof:
  - open state now shows both existing equipment rows plus the helper text
    `Scroll to review and manage all equipment.`
  - input state remains functional when the user focuses `Equipment Name`
  - the previous `BOTTOM OVERFLOWED BY ... PIXELS` failure no longer appears
- Supporting test coverage added:
  - autofocus disabled when equipment already exists
  - autofocus retained when the list is empty
  - helper copy shown when multiple equipment items exist
  - outer scroll view present for keyboard-safe layout

## 2026-04-09 11:05 ET Forms/Export Device Closure Slice

### Closed In Source

- [x] E3. 0582B original/recheck numbering logic
  - added `Mdot0582bTestNumberingService` as the canonical owner for:
    - next original numbering
    - recheck chaining after an explicit failure
    - reset back to original numbering after a passing recheck
  - `MdotHubController` now resolves the next visible test number through that
    service instead of blindly incrementing every send
  - quick-test UI now renders honest next-test labels such as:
    - `Test #2 · Recheck #1`
  - pass/fail chaining is only held open when it can be evaluated honestly from
    `percent_compaction` plus the selected item-of-work density requirement
  - regression coverage:
    - `test/features/forms/data/services/mdot_0582b_test_numbering_service_test.dart`
- [x] pay-app workbook accumulation proof now exists in source
  - added:
    - `test/features/pay_applications/domain/usecases/build_project_pay_app_workbook_use_case_test.dart`
  - locks the contract that the canonical workbook contains one worksheet per
    saved pay application in pay-app-number order

### Closed On Device

- [x] 1126 saved-response preview/export path
  - live 1126 response opens with autofilled header values intact
  - preview renders the actual 1126 PDF on the S21
  - export succeeds and shows the in-app `PDF exported` confirmation
  - proof artifacts:
    - `.codex/tmp/forms-audit-1126-open.png`
    - `.codex/tmp/forms-audit-1126-preview-settled.png`
    - `.codex/tmp/forms-audit-1126-export-result.png`
- [x] 0582B incomplete export path
  - live 0582B export succeeds on-device even with an incomplete current draft
  - this matches the product rule that export is not blocked just because the
    current row is incomplete
  - proof artifact:
    - `.codex/tmp/forms-audit-0582b-export.png`
- [x] 0582B original/recheck numbering behavior
  - live repro/validation sequence on the S21:
    - filled a failing original `Test #2`
    - after send, the screen stayed on `Test #2 · Recheck #1`
    - filled a passing recheck
    - after send, the screen reset to `Test #3`
  - proof artifacts:
    - `.codex/tmp/0582b-numbering-start.png`
    - `.codex/tmp/0582b-failing-original-filled.png`
    - `.codex/tmp/0582b-after-failing-send.png`
    - `.codex/tmp/0582b-recheck-passing-filled.png`
    - `.codex/tmp/0582b-after-passing-recheck-send.png`
- [x] pay-app workbook accumulation
  - pulled the canonical workbook from the S21 app sandbox:
    - `.codex/tmp/pay-app-canonical-workbook.xlsx`
  - inspected workbook sheet names directly:
    - `Pay App #1`
    - `Pay App #2`
    - `Pay App #3`
  - this closes the earlier “not proven to append over time” gap for the
    currently saved Springfield pay applications

### Honest Remaining Forms/Export Backlog

- [ ] E6. 0582B export destination UX
  - still open:
    - dated-folder support
    - attach-vs-export decision
    - cleanup of the multi-surface export flow
- [ ] 1126 / SESC broader hardening beyond header + preview/export parity
  - still not fully proven:
    - carry-forward/week-over-week workflow
    - attach-step/create-entry flow
    - recurring reminder behavior
- [ ] generic form-viewer export parity still needs explicit closure if the same
      “incomplete export is allowed” rule must hold outside the hub/specialized
      form shells
- [ ] C3. Windows dashboard duplicate side panel
  - source duplicate-panel removal landed, but no Windows validation pass was
    recorded
- [ ] E4. generic 0582B export parity
  - hub export path no longer blocks incomplete forms, but the generic
    form-viewer export contract still needs explicit confirmation if the same
    product rule must hold there
- [ ] pay-app project workbook accumulation proof
  - maintained workbook path exists, but repeated real exports have not yet
    been proven to append/accumulate correctly across multiple pay apps
- [ ] F1. broader foreground resume slowness
  - the external-picker resume/back-stack path is closed, but the original
    app-wide slow/frozen resume complaint is not fully retired yet

## 2026-04-09 11:30 ET Shared Form PDF Contract Slice

### Landed In This Pass

- Added a shared preview/export owner:
  - `lib/features/forms/presentation/support/form_pdf_action_owner.dart`
  - purpose:
    - centralize form preview shell, export/share shell, and builtin-form lookup
      so new forms do not reimplement PDF action handling
- Migrated current form shells onto the shared owner:
  - `lib/features/forms/presentation/screens/mdot_1126_form_screen.dart`
  - `lib/features/forms/presentation/screens/mdot_hub_screen.dart`
  - `lib/features/forms/presentation/screens/form_viewer_screen.dart`
- Added enforcement lint:
  - `no_direct_form_pdf_actions_outside_owner`
  - purpose:
    - top-level form screens must not directly call:
      - `generateFilledPdf`
      - `generatePreviewPdf`
      - `generateDebugPdf`
      - `sharePdfFile`
      - `exportFormToPdf`
    - future forms must route those actions through the shared owner or the
      approved controller path

### Verification

- `flutter test test/features/forms/presentation/support/form_pdf_action_owner_test.dart test/features/forms/presentation/screens/mdot_1126_form_screen_test.dart test/features/forms/presentation/controllers/form_viewer_controller_test.dart`
- `dart test test/architecture/no_direct_form_pdf_actions_outside_owner_test.dart`
  in `fg_lint_packages/field_guide_lints`
- `flutter analyze` on the touched form screen/support/test files
- root `dart run custom_lint`

### S21 Device Proof

- 1126 saved response still opens through the current form screen with preview
  and export actions present
- 1126 preview still opens the live PDF preview shell
- 1126 export still hands off to Android share chooser with the generated PDF
- 0582B hub still opens the live PDF preview shell
- 0582B export still hands off to Android share chooser with the generated PDF
- proof artifacts:
  - `.codex/tmp/forms-1126-open-shared-owner.png`
  - `.codex/tmp/forms-1126-preview-shared-owner.png`
  - `.codex/tmp/forms-1126-export-chooser.png`
  - `.codex/tmp/forms-0582b-open-shared-owner.png`
  - `.codex/tmp/forms-0582b-preview-shared-owner-settled.png`
  - `.codex/tmp/forms-0582b-export-late.png`

### Honest Status After This Pass

- shared preview/export ownership for current forms is now source/test/device
  closed
- this does not close the remaining broader forms backlog:
  - generic attach-to-entry UX for non-pay-app forms still needs a unified
    product path
  - generic form-viewer export parity still needs an explicit product decision
    if incomplete-export should be allowed there too
  - broader 1126 / SESC carry-forward, attach-step, and reminder flows still
    need end-to-end closure

## 2026-04-09 11:45 ET Export Contract Direction Added

- Product intent clarified:
  - the export contract must extend beyond forms
  - daily entries and pay applications are also first-class export artifacts
- explicit rules captured:
  - forms:
    - previewable
    - exportable standalone
    - attachable to daily entries
    - included in entry bundle export when attached
  - daily entries:
    - previewable
    - exportable standalone
    - bundle root for attached forms/photos
    - not attachable to another entry
  - pay applications:
    - preview/export/save/share capable
    - not attachable to entries
    - remain project-scoped standalone artifacts
- follow-up plan created:
  - `.codex/plans/2026-04-09-export-artifact-contract-plan.md`
- implementation order added there:
  - shared export capability registry
  - shared exported-file follow-up owner
  - entry export alignment
  - generic form attachment contract

## 2026-04-09 12:00 ET Export Capability Registry Slice

### Landed In This Pass

- Added a shared export capability registry:
  - `lib/core/exports/export_artifact_capability_registry.dart`
- Registered baseline export artifact families:
  - `form`
  - `entry`
  - `pay_app`
- Began adopting the registry in live owners:
  - `FormPdfActionOwner`
  - `EntryPdfPreviewScreen`
  - `showReportPdfActionsDialog`
  - `PayAppDetailFileOps`
  - `QuantitiesPayAppExporter`
- Added enforcement lint:
  - `export_artifact_capability_registry_contract_sync`
  - purpose:
    - prevent the baseline artifact families from drifting out of the shared
      registry as more exportable surfaces are added

### Verification

- `flutter test test/core/exports/export_artifact_capability_registry_test.dart test/features/forms/presentation/support/form_pdf_action_owner_test.dart`
- `dart test test/architecture/export_artifact_capability_registry_contract_sync_test.dart`
  in `fg_lint_packages/field_guide_lints`
- targeted `flutter analyze`
- root `dart run custom_lint`

### Honest Status After This Pass

- the registry baseline is now source/test/lint closed
- this is an architectural standardization slice, not the final export UX pass
- still open:
  - shared exported-file follow-up owner across pay-app detail/settings export
    history/post-export flows
  - deeper entry export alignment beyond the capability declaration
  - generic attach-to-entry contract for forms

## 2026-04-09 12:15 ET Shared Exported-File Action Owner Slice

### Landed In This Pass

- Added shared exported-file follow-up owner:
  - `lib/features/pay_applications/presentation/support/export_artifact_file_action_owner.dart`
- Migrated duplicate save/share orchestration onto it:
  - `PayAppDetailFileOps`
  - `SettingsSavedExportActions`
  - pay-app post-export follow-up inside `QuantitiesPayAppExporter`
- Added architecture lint:
  - `no_direct_export_artifact_file_service_usage_outside_owner`
  - purpose:
    - keep direct `ExportArtifactFileService.readBytes/saveCopy/shareFile`
      calls inside the shared owner

### Verification

- `flutter test test/features/pay_applications/presentation/support/export_artifact_file_action_owner_test.dart test/features/settings/presentation/screens/settings_saved_exports_screen_test.dart test/core/exports/export_artifact_capability_registry_test.dart`
- `dart test test/architecture/export_artifact_capability_registry_contract_sync_test.dart test/architecture/no_direct_export_artifact_file_service_usage_outside_owner_test.dart`
  in `fg_lint_packages/field_guide_lints`
- targeted `flutter analyze`
- root `dart run custom_lint`

### Honest Status After This Pass

- exported-file save/share follow-up is now standardized in source
- this does not yet close the remaining export backlog:
  - entry export still has duplicated UI ownership
  - attach-to-entry is still not a generic form capability
  - capability-driven user copy/messages still need a fuller pass

### Verification And Contract-Test Backlog Added From This Audit

- [ ] add/close contract test: project delete removes the item without manual
      refresh and repairs selection immediately
- [ ] add/close contract test: submitted today entry prompts for
      open-vs-unsubmit/revert instead of silently creating a new draft
- [ ] add/close contract test: account switch does not leak trash rows between
      users
- [ ] add/close contract test: resume/back never strands the user on a broken
      root stack
- [ ] follow up on driver route reporting truth after launcher relaunch
  - not a product blocker, but still a diagnostics correctness gap

### Lint Watchlist Added From This Audit

- [ ] audit whether a lint can enforce navigation/restoration ownership for
      external intents and picker return paths
  - goal: reduce future home/back lockout regressions
  - honest caution:
    - a lint cannot prove Android task-stack correctness by itself
    - but it may be able to restrict where restoration-sensitive navigation and
      external-intent launches are owned
- [ ] audit whether a lint can ban screen-local model snapshots for read-only
      rendering immediately after mutation when a live provider/controller value
      already exists
  - goal: reduce stale UI/state-ownership regressions like Activities
- [ ] audit whether a lint can require destructive mutations to go through
      approved provider/reload owners
  - goal: reduce stale delete/update UI across project list and similar flows
- [ ] audit whether a lint can enforce shared route-intent helpers for
      continue/edit/open-submitted entry flows beyond the current entry-routing
      slice
- [ ] audit whether a lint can enforce preload gating on action triggers, not
      just on the final screen implementation
  - goal: prevent enabled actions from opening empty forms/sheets
- [ ] record which of the above are not honest enough for static lint and must
      stay as contract tests/runtime verification instead

## 2026-04-09 09:45 ET Enforcement + Closure Slice

### Landed In This Pass

- Added new architecture lint:
  - `no_form_new_route_calls_outside_approved_owners`
  - purpose:
    - keep new-form route ownership constrained to the approved creation entry
      points that already handle project context and preload gating
  - approved owners:
    - `FormGalleryScreen`
    - `ProjectDashboardScreen`
    - `EntryEditorBody`
    - `weekly_sesc_toolbox_todo.dart`
- Closed a real source gap in project deletion:
  - deleting the currently selected project now repairs selection immediately to
    a valid fallback project when one exists instead of always dropping to
    `null`
  - file:
    - `lib/features/projects/presentation/providers/project_provider_mutations.dart`
- Added the missing submitted-entry regression coverage:
  - `DashboardTodaysEntry` now has widget tests proving:
    - submitted today entry shows the open-vs-revert decision
    - `Revert to Draft` calls `undoSubmission()` and opens the existing entry
    - `Open Submitted` skips undo and opens the existing entry
  - file:
    - `test/features/dashboard/presentation/widgets/dashboard_todays_entry_test.dart`

### Verification

- `flutter test test/features/projects/presentation/providers/project_provider_test.dart`
- `flutter test test/features/dashboard/presentation/widgets/dashboard_todays_entry_test.dart`
- `dart test test/architecture/no_form_new_route_calls_outside_approved_owners_test.dart`
  in `fg_lint_packages/field_guide_lints`
- `flutter analyze` on the touched provider/dashboard/lint files
- root `dart run custom_lint`

### Honest Status After This Pass

- A1. Project deletion refresh is stronger in source now:
  - provider fallback selection is repaired
  - contract test coverage exists for provider behavior
  - still needs on-device proof for the original visible-list/manual-refresh
    user complaint
- B2. Submitted today entry prompt is now closed at source + contract-test
  level and is now also closed on-device

## 2026-04-09 09:26 ET S21 Validation: Submitted-Today Continue Flow Closed

- Revalidated the original user-reported bug on the latest driver build using
  the real Springfield project and a live Apr 9, 2026 draft.
- End-to-end device sequence:
  - selected Springfield from `Projects`
  - opened `1 Draft — Tap to Review`
  - reviewed and submitted the existing Apr 9 draft
  - returned to dashboard and confirmed `Today's Entry Submitted`
  - tapped the submitted card and validated both branches
- Device proof:
  - `Open Submitted` opened the existing report in submitted/read-only state
    with the submitted banner visible
  - `Revert to Draft` reopened the same entry in editable form state and
    surfaced the green `Entry reverted to draft` confirmation
  - backing back to dashboard restored the honest draft affordance instead of
    leaving the app in a contradictory/new-entry state
- Conclusion:
  - the original bug is closed:
    - dashboard no longer starts a brand-new entry when today's entry is
      already submitted
    - the user now gets a truthful decision point and both resulting actions
      work on-device

## 2026-04-09 Pay-App Sync/Export Contract Update

### Intent Clarified

- filled forms and canonical field data must remain backed up/syncable
- local export history does not need Supabase backup
- pay applications follow the same rule:
  - canonical pay-app data must sync/back up
  - workbook/export artifacts remain local-only

### Landed Architecture

- local-only export-history sync surface retired for:
  - `entry_exports`
  - `form_exports`
  - `export_artifacts`
- canonical `pay_applications` kept in the sync engine
- `pay_applications.export_artifact_id` is now optional local metadata, not
  remote truth
- pay-app detail/workbook flows resolve artifacts by either:
  - direct `export_artifact_id`
  - fallback `source_record_id`
- deleting a local artifact only clears local linkage
- deleting a pay app is now a separate canonical-data action

### Verification Already Closed

- source/test/analyze/custom-lint verification is green for the split
- S21 upgrade proof is closed for:
  - schema shape
  - trigger retirement on local-only export-history tables
  - canonical sync triggers retained on `pay_applications`
  - clean queue after upgrade

### Still Open For Honest Closure

- on-device end-to-end pay-app creation/export validation after the split
- queue proof that export-history tables do not re-enter `change_log`
- sync proof that canonical `pay_applications` still drains cleanly

## 2026-04-09 Pay-App E2E Result

### Closed

- on-device pay-app creation/export validation after the split
- queue proof that export-history tables do not re-enter `change_log`

### Result

- real S21 export created a new canonical `pay_applications` row
- only that canonical row entered `change_log`
- local-only export history stayed local:
  - `export_artifacts`
  - `form_exports`
  - `entry_exports`

### New Truth Discovered

- sync still cannot fully close because the linked backend schema is behind:
  - remote `pay_applications.export_artifact_id` is still `NOT NULL`
  - sync fails with Postgres `23502`

### Containment Landed

- this backend mismatch now blocks immediately instead of poisoning sync:
  - first failure is quarantined into blocked queue state
  - startup repair converts already-poisoned matching rows into blocked state
  - repeat sync no longer retries the row forever

### Still Open

- apply `20260409130500_make_pay_apps_canonical_and_artifact_optional.sql`
  on the linked remote project
- after the remote migration, rerun `Repair Sync State` and prove the blocked
  pay-app row drains cleanly

## 2026-04-09 Pay-App Sync Closure

### Closed

- linked backend migration for canonical pay apps
- blocked pay-app row repair after backend deployment
- end-to-end S21 proof that canonical pay-app sync drains cleanly while local
  export history stays local-only

### Verification

- remote schema:
  - `public.pay_applications.export_artifact_id` is nullable
  - export-artifact FK delete rule is `SET NULL`
- S21:
  - blocked pay-app row was requeued through `Repair Sync State`
  - follow-up sync drained to `0 pending / 0 blocked / 0 unprocessed`
- remote data:
  - `pay_applications/91571c6c-8f54-456e-89fd-9b0957480333` exists
  - `application_number = 4`
  - `export_artifact_id = null`

### Product Outcome

- filled forms and canonical pay apps still back up through sync
- export history remains local-only and no longer enters `change_log`
- stale blocked pay-app rows have a legitimate repair path after backend fixes

## 2026-04-09 D3 Bundle Verification Update

### Closed

- attached-form inclusion in the daily-entry export bundle

### Verification

- live form linkage still exists on-device:
  - `form_responses/c1b792f9-1248-420f-a218-a029fce446de`
  - `entry_id = fb3ddde9-9429-48d5-bf4e-de2fabdfebe1`
- entry preview/export shell is now keyed and source-tested:
  - `report_pdf_preview_dialog`
  - `report_pdf_save_as_button`
  - `report_pdf_share_button`
- S21 proof:
  - reopening the attached draft entry and tapping export opened
    `Daily Entry Preview`
  - tapping save opened `Export Folder Name` with suggested folder `04-09`
    rather than the standalone PDF save path
  - screenshot: `.codex/tmp/entry-export-folder-dialog.png`

### Still Open

- the separate 1126 attach-step/create-entry UI flow still needs direct live
  proof
## 2026-04-09 15:35 ET MDOT 1126 Typed Signature, Attach Flow, And Reminder Date Closure

- [x] typed signature replaces drawn signature for MDOT 1126
  - the signature step now validates typed signer text and stamps a PNG generated from typed text instead of using the drawn pad path
  - on-device on the S21, tapping `Sign` no longer crashes the app or the driver
- [x] 1126 same-date attach path
  - verified on-device after fresh rebuild that a signed 1126 for `2026-04-09` reopens the Apr 9 entry surface correctly
- [x] 1126 no-match create-entry path
  - verified on-device with a fresh `2026-04-11` 1126 draft
  - attach step now shows:
    - notice that no entry matches the inspection date
    - `Create new entry for 2026-04-11`
    - `Choose a different existing entry`
  - driver-keyed tap on `Create new entry for 2026-04-11` created a new daily entry and navigated to `/entry/.../2026-04-11`
  - debug log proves the created entry id was `cee75291-e61e-46f7-ba47-b5c10bb291ef`
- [x] reminder-triggered 1126 due-date propagation
  - fixed the `form-new` path so `inspectionDate` query parameters flow through `FormNewDispatcherScreen` into `createMdot1126Response`
  - verified on-device with `/form/new/mdot_1126?inspectionDate=2026-04-15`
  - rainfall step opened with `Apr 15, 2026`, proving reminder-created drafts no longer silently default to `DateTime.now()`

Notes:
- an earlier wrong-entry result during no-match testing was caused by raw adb coordinate flakiness, not product logic
- reliable closure was established using the driver’s widget-text tap endpoint instead of raw screen taps

## 2026-04-09 15:58 ET Shared Form Export Contract Closure

- [x] generic form-viewer export parity
  - `FormViewerController.export()` no longer requires preview first
  - generic viewer export no longer submits or marks forms exported
  - successful exports now route through the shared `Form Exported` dialog
- [x] dedicated-shell export parity across shipped forms
  - verified on-device that:
    - generic fallback viewer export opens `Form Exported`
    - 0582B live shell export opens `Form Exported`
    - 1126 live shell export opens `Form Exported`
  - all three surfaces now expose:
    - `Not Now`
    - `Save Copy`
    - `Share File`
- [x] forms remain editable after export
  - re-queried the live device DB after generic-viewer and dedicated-shell
    exports
  - sampled rows still showed `status = open`
- proof artifacts:
  - `.codex/tmp/generic-form-viewer-export-dialog.png`

## 2026-04-09 22:30 ET Attached Form Card UX Closure

- [x] attached forms in the entry-editor Forms section now use the export-name
  presentation contract
  - on-device attached 0582B no longer shows internal quick-action chips
  - the visible card title is the export-style filename
  - the filename is editable and the renamed value persists on-device:
    `CompanyPrefix_0582B_Apr08.pdf`
  - tapping the card opens the form wizard/editor
  - `View Form` remains available and opens PDF preview for quick verification
- proof artifacts:
  - `.codex/tmp/live_debug/entry-for-rename-proof.png`
  - `.codex/tmp/live_debug/entry-form-open-after-tap.png`
  - `.codex/tmp/live_debug/entry-attached-form-preview-open.png`

Status change:
- remove the attached-form-card UX item from the active backlog
- this leaves the real remaining forms/export backlog as:
  - 0582B export destination UX / dated-folder policy
  - broader 1126 / SESC reminder/workflow hardening
  - sync issue taxonomy / reporting
  - conflict viewer usefulness
  - `.codex/tmp/mdot-0582b-live-export-dialog.png`
  - `.codex/tmp/mdot-1126-live-export-dialog.png`

## 2026-04-09 16:03 ET Additional Verified Closures

### Closed

- shared standalone form export follow-up is now end-to-end device-verified
- 1126 typed-signature identity drift is source/test/device-verified enough to
  leave the highest-risk forms backlog

### Verification

- shared form `Save Copy` branch
  - from the live generic 0582B viewer on the S21, `Save Copy` opens Android's
    system folder picker instead of silently failing or looping back to share
  - screenshot:
    - `.codex/tmp/0582b-save-copy-picker-verified.png`
- 1126 signature identity
  - fresh driver build reaches signature step with authenticated signer prompt:
    `Type "E2E Test Admin" to sign this form.`
  - signing still advances cleanly to attach step
  - screenshots:
    - `.codex/tmp/1126-signature-step-fresh-build.png`
    - `.codex/tmp/1126-post-sign-attach-fresh-build.png`

### Source Contract Added

- `TypedSignatureField` now blocks signing when no expected signer identity is
  available instead of accepting any non-empty typed name
- `BuildCarryForward1126UseCase` no longer carries forward prior inspector
  identity into the next weekly draft
- `SignFormResponseUseCase` now persists `typed_signer_name` alongside the
  minted audit id
- `Mdot1126SignatureStep` now prefers the authenticated profile display name
  over editable header text when validating the signer

### Still Open

- 0582B export UX product closure:
  - dated-folder behavior
  - attach-vs-export decision
  - remaining multi-surface flow cleanup
- cross-account trash live two-account validation
- conflict viewer usefulness
- sync issue taxonomy / reporting

## 2026-04-09 16:40 ET Entry Date Editing Closure

### Closed

- in-flow entry date editing is now source/device-closed for both:
  - clean date change
  - collision -> open existing draft

### Root Cause

- `EntryEditorScreen` only loaded entry state on first mount
- when the route changed to a different `/entry/:projectId/:date?entryId=...`
  context, the widget state was reused but the screen did not reload
- result:
  - route could point at one date/entry while the visible header still showed
    the previous entry

### Landed

- added explicit route-identity binding helper:
  - `lib/features/entries/presentation/screens/entry_editor_route_binding.dart`
- `EntryEditorScreen.didUpdateWidget(...)` now:
  - detects route identity changes
  - regenerates the pending create-mode id when needed
  - reloads the editor state for the new route context

### Verification

- `flutter test test/features/entries/presentation/screens/entry_editor_route_binding_test.dart`
- targeted `flutter analyze`
- root `dart run custom_lint`

### S21 Device Proof

- clean branch:
  - Apr 24 draft -> edit date -> Apr 25
  - route changed to `/entry/.../2026-04-25`
  - visible header updated to `Apr 25, 2026`
  - proof:
    - `.codex/tmp/entry-date-edit-after-fix-clean-25.png`
- collision branch:
  - Apr 23 draft -> edit date -> Apr 24
  - conflict dialog showed `Entry Already Exists`
  - tapping `Open Existing Draft` changed the route to `/entry/.../2026-04-24`
  - visible header updated to `Apr 24, 2026` instead of staying stale on Apr 23
  - proof:
    - `.codex/tmp/entry-date-edit-after-fix-clean.png`
    - `.codex/tmp/entry-date-edit-after-fix-open-existing.png`

## 2026-04-09 16:55 ET 1126 Weekly Draft Dedupe + Forms Context Slice

### Closed In This Pass

- repeated same-date MDOT 1126 creation now reopens the same draft instead of
  creating duplicates
- standalone/shared form export now uses one date-aware filename policy
- Forms screen now surfaces linked-vs-standalone context on saved responses
- Forms screen export history is now scoped to form PDFs only

### Landed

- new 1126 draft resolver:
  - `lib/features/forms/domain/usecases/load_open_1126_draft_for_date_use_case.dart`
- `InspectorFormProvider.createMdot1126Response(...)` now returns the existing
  same-date open draft before carry-forward/create
- weekly reminder model now carries optional draft-resume context:
  - `resumeResponseId`
- reminder/banner/toolbox/dashboard taps now resume the draft when one exists
- new shared filename policy:
  - `lib/features/forms/data/services/form_export_filename_policy.dart`
- `ExportFormUseCase` now defaults to that shared policy
- `MdotHubScreen` no longer hardcodes its own 0582B filename
- `FormGalleryResponseTile` now shows:
  - `Standalone`
  - `Linked to daily entry`
- `FormGalleryScreen` export history now only loads `form_pdf` artifacts

### Verification

- `flutter test test/features/forms/domain/usecases/load_open_1126_draft_for_date_use_case_test.dart test/features/forms/domain/usecases/compute_weekly_sesc_reminder_use_case_test.dart test/features/forms/presentation/screens/form_new_dispatcher_screen_test.dart`
- `flutter test test/features/forms/data/services/form_export_filename_policy_test.dart test/features/forms/presentation/widgets/form_gallery_response_tile_test.dart test/features/forms/presentation/screens/form_gallery_screen_test.dart test/features/forms/domain/usecases/export_form_use_case_test.dart`
- targeted `flutter analyze`
- root `dart run custom_lint`

### S21 Device Proof

- 1126 draft dedupe:
  - first open:
    - `/form/new/mdot_1126?inspectionDate=2026-04-15`
    - route resolved to `/form/ee145e67-a904-4a0d-ba23-068a6525d3bd`
  - second open with the same inspection date:
    - same route resolved again to
      `/form/ee145e67-a904-4a0d-ba23-068a6525d3bd`
  - this proves same-date weekly creation now resumes instead of duplicating
- date-aware form filename:
  - 0582B export dialog now shows:
    - `MDOT_0582B_2026-04-08_fa74c344.pdf`
  - proof:
    - `.codex/tmp/0582b-export-dialog-dated-filename.png`
- Forms screen response context:
  - saved responses now show live `Standalone` / `Linked to daily entry`
  - proof:
    - `.codex/tmp/forms-gallery-linked-history-cleanup.png`
- Forms export history scope:
  - visible artifact list now shows only `Form PDFs`
  - proof:
    - `.codex/tmp/forms-gallery-export-history-form-only-2.png`

### Still Open After This Pass

- 0582B export UX still needs the remaining product-policy slice:
  - dated-folder behavior for standalone form exports
  - any remaining multi-surface flow cleanup beyond the shared owner path
- weekly reminder `resume draft` copy is source-landed, but I have not yet
  captured a device screenshot of the reminder surfaces themselves in a state
  where the resume banner/card is visible

## 2026-04-09 18:48 ET Rename Crash Closure

- The reported yellow border was confirmed as Flutter's red error screen, not a
  sizing/border issue.
- The crash path is now closed:
  - attached-form rename uses a dedicated `RenameAttachedFormDialog`
  - controller ownership stays inside the dialog route instead of caller-owned
    dialog content
- Local verification:
  - `flutter test test/features/entries/presentation/widgets/rename_attached_form_dialog_test.dart`
  - targeted `flutter analyze`
  - root `dart run custom_lint`
- S21 proof:
  - opened the live attached 0582B rename dialog
  - entered `0582B_Rename_Verify.pdf`
  - saved without any red-screen crash
  - the card updated live inside the entry editor
  - `/driver/local-record` confirms the persisted
    `attachment_display_name = 0582B_Rename_Verify.pdf`
- Proof artifacts:
  - `.codex/tmp/live_debug/device-current-screen-adb.png`
  - `.codex/tmp/live_debug/entry-rename-dialog-after-fix.png`
  - `.codex/tmp/live_debug/entry-rename-typed-after-fix.png`
  - `.codex/tmp/live_debug/entry-after-rename-save-fix.png`

## 2026-04-09 16:58 ET 0582B Export Decision + 1126 Attach Proof

### Closed

- 0582B attach-vs-export decision is now source/test/device-closed
- 0582B export now saves dirty hub draft state before export
- 1126 attach-step is now device-closed for both:
  - create a new same-date entry and attach
  - attach to an existing same-date entry
- standalone 1126 export now blocks after a signed form is edited

### Device Proof

- 0582B attach/export decision
  - the live 0582B shell now opens:
    - `Attach Before Export?`
    - `Export As Is`
    - `Attach and Export`
  - proof:
    - `.codex/tmp/0582b-attach-export-decision-3.png`
- 0582B save-before-export
  - edited `counts_mc` to `777` in the live hub
  - exported without manually saving first
  - pulled the live device DB and confirmed the same response now stores:
    - `hub_draft.test.counts_mc = "777"`
- 0582B attach before export
  - choosing `Attach and Export`:
    - showed `Attached to the 2026-04-08 daily entry before export.`
    - updated the live device DB row to a non-null `entry_id`
    - updated the Forms gallery subtitle to `Linked to daily entry`
  - proof:
    - `.codex/tmp/0582b-after-attach-export.png`
    - `.codex/tmp/forms-gallery-0582b-linked-after-attach.png`
- 1126 typed-signature + create-entry attach branch
  - `/form/new/mdot_1126?inspectionDate=2026-04-28`
  - typed signer prompt shown with `E2E Test Admin`
  - attach step showed `Create new entry for 2026-04-28`
  - tapping it navigated into the Apr 28 entry editor
  - proof:
    - `.codex/tmp/1126-signature-step-typed.png`
    - `.codex/tmp/1126-attach-step-create-entry.png`
    - `.codex/tmp/1126-after-create-entry-attach.png`
- 1126 existing-entry attach branch
  - `/form/new/mdot_1126?inspectionDate=2026-04-25`
  - attach step showed `2026-04-25 (matches inspection date)`
  - tapping it navigated into the Apr 25 entry editor
  - proof:
    - `.codex/tmp/1126-existing-entry-attach-step.png`
    - `.codex/tmp/1126-existing-entry-after-attach.png`
- 1126 export blocked after signed edit
  - opened signed 1126 `0c84aa6b-a660-4a73-902a-8b4779f79d5d`
  - changed inspection date from Apr 11 to Apr 12 via the keyed picker
  - tapping export now surfaces:
    - `Export blocked: measures, signature`
  - proof:
    - `.codex/tmp/1126-export-blocked-after-edit.png`
- attached entry-form card contract
  - fresh S21 build now shows attached 0582B forms in the entry editor as the
    export-style filename, not as 0582B quick-action chips
  - the live card now shows:
    - `CompanyPrefix_0582B_Apr08.pdf`
    - `MDOT_0582B • Tap to edit form`
    - separate `View Form` action
  - the old `+ Test`, `+ Proctor`, and `+ Weights` entry-card actions are gone
  - proof:
    - `.codex/tmp/live_debug/post-scroll-entry.png`
    - `.codex/tmp/live_debug/entry-form-open-after-tap.png`
    - `.codex/tmp/live_debug/entry-attached-form-preview-open.png`

### Source / Test Closure

- new dialog:
  - `lib/features/forms/presentation/widgets/form_export_decision_dialog.dart`
- shared strict export-validation policy:
  - `lib/features/forms/data/services/form_export_validation_policy.dart`
- prevention lint:
  - `no_signature_pad_field_usage`
- verification:
  - targeted `flutter test`
  - targeted `flutter analyze`
  - root `dart run custom_lint`

## 2026-04-09 17:20 ET Sync Status Conflict Residue Sweep

### New Device Finding

- Live S21 screenshot:
  - `0 Pending`
  - `0 Blocked`
  - `34 Conflicts`
- The same moment's driver sync status reported:
  - `pendingCount=0`
  - `blockedCount=0`
  - `unprocessedCount=0`

### Validation

- Latest full sync log on-device:
  - `Sync cycle (full): pushed=0 pulled=0 errors=0 conflicts=0 skippedFk=1 skippedPush=0`
- Read-only device DB inspection shows:
  - `84` raw undismissed `conflict_log` rows
  - `34` grouped logical records
- Top grouped records are historical `winner = remote` rows, mostly:
  - `form_responses/*`
  - `personnel_types/*`

### Meaning

- These are not `34` new unresolved sync failures.
- The engine already auto-resolved them by keeping the newer remote version.
- The product bug is the user-facing conflict surface:
  - historical remote-win conflict history is still being counted as active
    `need review`

### Open Follow-Up

- downgrade or auto-dismiss non-actionable remote-win conflict history in the
  user-facing sync status surface
- keep raw grouped conflict history available only for support/debug
- continue auditing the reported intermittent yellow border:
  - fresh driver screenshot did not capture the border
  - possible sizing/overlay cause is still under investigation

### Closure

- Reinstalled the latest build on the S21 and ran another full sync.
- User-facing Sync Status is now correct:
  - `Synced`
  - `0 Pending`
  - `0 Blocked`
  - `0 Conflicts`
- Raw grouped history is still preserved for debug:
  - `View Conflict Log`
  - `34 logical conflicts in grouped history`
- This closes the false-active conflict count bug for the product surface while
  preserving support/debug history.
- Proof:
  - `.codex/tmp/live_debug/device-sync-after-fix.png`

## 2026-04-09 Backlog Reconciliation

The historical spec contains many append-only TODO snapshots. The real
remaining backlog after the latest source and S21 verification passes is now:

- still genuinely open:
  - cross-account trash isolation still needs real two-account device proof
  - broader 1126 / SESC hardening beyond header + preview/export + attach flow
  - reminder-surface `resume draft` proof for the weekly SESC workflow
  - standalone-form dated-folder export policy / UX
  - grouped conflict viewer usefulness
  - support-facing sync issue taxonomy / reporting
  - broader app-wide resume/back validation outside the already-fixed picker
    path
  - Windows dashboard duplicate-pane validation
- implemented but still needing device proof:
  - none in the attached-form/export card slice after the 2026-04-09 S21 pass
- stale items that should be treated as checked off:
  - attached entry-form cards showing form-internal 0582B quick-action chips
  - attached-form tap-to-edit and separate preview affordance
  - generic attach-to-entry export/bundle behavior
  - entry export migration proof
  - pay-app workbook accumulation/export proof
  - false-active user-facing sync conflict count

## 2026-04-09 18:22 ET Rename-Flow Verification Crash

The earlier "yellow border" report is now explained by a real Flutter debug
error surface, not an app-painted border.

Device screenshot:
- `.codex/tmp/live_debug/device-crash-yellow-border-driver.png`

Runtime evidence captured from the debug server:
- `FlutterError: A TextEditingController was used after being disposed`
- framework assertion `_dependents.isEmpty`
- duplicate overlay `GlobalKey` errors

Meaning:
- the attached-form card contract itself is still product-correct on-device
- the remaining failure is the rename-save verification path under automated
  modal text entry
- this should be carried as a separate crash/verification seam, not as a
  regression of the attached-form card UI contract
## 2026-04-09 18:40 - Device Crash Clarification

- The reported "yellow border" is a Flutter red assertion screen, not a render-size border.
- Fresh device screenshot captured at `.codex/tmp/live_debug/device-current-after-crash-adb.png`.
- Runtime assertions observed from the same interaction:
  - `A TextEditingController was used after being disposed`
  - `_dependents.isEmpty`
  - duplicate overlay `GlobalKey` follow-on errors
- Trigger path: attached-form rename dialog teardown after automated text entry.
- Current code now routes the rename action through the dedicated dialog seam:
  - `lib/features/entries/presentation/widgets/rename_attached_form_dialog.dart`
  - caller normalized in `lib/features/entries/presentation/widgets/entry_forms_section.dart`

## 2026-04-09 18:40 - Reconciled Remaining TODOs

- Weekly SESC reminder live proof in a real resume-draft state.
- Narrowed 1126 / SESC workflow validation:
  - week-over-week reminder routing
  - carry-forward/resume polish
  - signed-response reopen/edit/re-export validation
- Standalone-form export destination UX decision and validation.
- Conflict viewer usefulness.
- Sync issue taxonomy/reporting refinement.
- Verification-only tail:
  - cross-account trash device proof
  - broader resume/back validation
  - Windows validation tail

### Explicitly Closed / Do Not Reopen

- Attached-form card contract and rename affordance shape
- generic form-viewer export parity
- 1126 attach-step/create-entry
- 0582B attach-vs-export decision
- entry bundle export with attached forms
- pay-app workbook accumulation/export proof
- false-active sync conflict count on the user-facing screen
