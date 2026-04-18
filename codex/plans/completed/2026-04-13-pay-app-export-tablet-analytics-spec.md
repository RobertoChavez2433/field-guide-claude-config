# Pay App Export + Tablet Analytics + Calculator Revamp (Spec)

**Date:** 2026-04-13
**Owner:** Field Guide App

## Objectives
- Make pay-app export reliably support creating and exporting copies of existing pay applications by date range without destroying saved records.
- Improve the pay-app export flow so previous pay apps can be selected/viewed and re-exported in one interface.
- Enable deterministic pay item and pay app inspection in analytics by item and by app.
- Fix tablet layout issues: entry editor sectioning, project list layout, and quantities pay-item interactions.
- Improve quantity calculator presentation and reuse existing toolbox-style calculator primitives.

## 1) Pay-app Copy Export Semantics (Highest Priority)
- [ ] Audit current end-to-end path: `PayAppDateRangeDialog` -> `QuantitiesPayAppExportSelection` -> `PayApplicationProvider.exportPayApp` -> `PreparePayAppExportUseCase` -> `CollectPayAppExportDataUseCase` -> `PersistPayAppExportUseCase`.
- [ ] Remove hard-block behavior for `replaceExisting == true` in provider and flows.
- [ ] Split exact-match handling into explicit outcomes:
  - [ ] `open existing` (navigate detail)
  - [ ] `export copy` (generate a new pay-app row/artifact with same period)
- [ ] Update `PreparePayAppExportUseCase` so date validation allows exact-match path only when copy mode is requested.
- [ ] Introduce explicit copy mode parameters if needed (`isCopyFromExisting` / `preserveExisting`), keeping default behavior protective.
- [ ] Update `CollectPayAppExportDataUseCase` so collect/build for existing range creates **new** IDs and artifact when copy flow is selected.
  - [ ] Preserve previous pay-app state as required for chain/reference.
  - [ ] Keep existing chain links (`previousApplicationId`) intact unless explicitly recomputed.
- [ ] Update `PersistPayAppExportUseCase`:
  - [ ] Existing-pay-app flow should use **create** for copied pay-app row + create new artifact.
  - [ ] Do not mutate/replace source pay-application IDs.
  - [ ] Keep artifact deletion/cleanup rules tied to failed persistence.
- [ ] Ensure repository create is not violated by exact date check for copy flow:
  - [ ] For copy flow, duplicate-by-range rule should not block; add explicit bypass or separate insert logic.
- [ ] Add regression tests in domain/provider/flow for:
  - [ ] exact-match -> open existing
  - [ ] exact-match -> save copy
  - [ ] copy keeps source pay-app unchanged
  - [ ] copy adds new row and new artifact

## 2) Export UI: Pay-App Export Range + Existing Selection in One Screen
- [ ] Replace current immediate “exact match opens only” modal with a dedicated export UI in `QuantitiesPayAppExportRangeSelector`.
- [ ] UX on selection screen:
  - [ ] Date pickers and live validation (existing, overlaps, sequence)
  - [ ] Existing match details list (pay-app number/date/summary)
  - [ ] Actions: `Export New Copy`, `Open Existing`, `Continue` for available range.
- [ ] Keep progress dialog and existing export pipeline wiring unchanged where behavior is proven.
- [ ] Ensure pay-app number validation remains for user-entered number but does not block copy of existing range.

## 3) Analytics: Pay-App and Pay-Item Drilldown
- [ ] Expand analytics provider with selection state:
  - [ ] selected pay-app id
  - [ ] selected pay item id
- [ ] Add derived filtered item/activity model for selected pay app and selected pay item.
- [ ] Update `project_analytics_screen` to support:
  - [ ] List of pay apps (tap to select/apply detail)
  - [ ] Detail pane showing selected pay-app period/metrics.
  - [ ] List of items with tap to isolate that item across all saved apps and current filter.
  - [ ] Clear selection affordances and fallback to summary view.
- [ ] Keep compact and tablet layouts but avoid dense “blob” layout.

## 4) Tablet Layout Fixes
- [ ] Daily entry wizard (tablet): move activities into list/detail section under header on left pane.
  - [ ] Update `EntryEditorBody` medium layout composition.
- [ ] Quantities (tablet): prevent bottom sheet on tap for pay item when detail pane is visible.
  - [ ] Open full-sheet only on phone breakpoints.
- [ ] Projects view (tablet): remove split/detail layout and restore single scrolling list.
  - [ ] Revisit any selection state or side effects added for split layout and simplify.

## 5) Quantity Calculator UX + Shape Reuse
- [ ] Redesign quantity unit button row to non-orange visual style, modernize button chips/cards.
- [ ] Reuse toolbox calculator styles/logics for shape + square-footage math where practical.
  - [ ] Create helper/config so quantity calculator can render same shape/unit selector style as toolbox.
  - [ ] Preserve existing `QuantityCalculatorResult` contract (`value`, `unit`, `type`, `description`).

## 6) Signature Stylus Path (minimum viable, deferred)
- [ ] Confirm existing signature input is touch-aware and supports stylus input.
- [ ] Add touch suppression during pen usage only if existing signature input API allows.
- [ ] Do not block this by full native palm-rejection work in this cycle.

## 7) End-to-End Verification on S21
- [ ] Build and deploy to connected S21 via Flutter run endpoint.
- [ ] Clear previous pay apps (as requested).
- [ ] Create four new pay apps in sequence:
  - [ ] normal export
  - [ ] exact-range re-export as copy
  - [ ] range gaps/validation checks
  - [ ] second exact re-export path
- [ ] Verify:
  - [ ] source pay-apps stay preserved
  - [ ] copied rows created with independent IDs
  - [ ] previous list remains available for subsequent export
  - [ ] analytics item and app filtering updates as expected
  - [ ] tablet interactions match requested behavior.

### 2026-04-13 S21 Pay-App XLSX Copy Evidence
- [x] Hot-restarted the active Flutter run on S21 `RFCNC0Y975L` after the
  Android save-copy patch.
- [x] From `/quantities`, selected saved Pay Application #5 via the export UI
  copy action instead of entering a new pay-app number.
- [x] Confirmed Android DocumentsUI opened for the XLSX save target in
  `Downloads` with filename `pay_app_5_2026-04-12_2026-04-18.xlsx`.
- [x] Pressed `SAVE`; Android created a second visible copy at
  `/sdcard/Download/pay_app_5_2026-04-12_2026-04-18 (1).xlsx` instead of
  mutating the saved pay-app row.
- [x] Pulled the visible workbook and verified it is a valid XLSX containing
  the `Quantities` sheet and expected project/pay-item strings:
  `Springfield DWSRF`, `Mobilization`, `Pre-Construction`, `Video Survey`.
- [x] Opened the second visible workbook copy in Microsoft Excel on the S21;
  Excel showed the document title `pay_app_5_2026-04-12_2026-04-18 (1)` and
  the selected sheet tab `Quantities`.

### 2026-04-13 PR + iOS Build Evidence
- [x] Committed and pushed the tracked app changes as
  `f2133ea248d10bb6824c9403ef40b5f2d19ae494`
  (`fix(pay-applications): export saved application workbooks`).
- [x] Created PR #290 from `sync-engine-refactor` into `main`.
- [x] Merged PR #290; merge commit:
  `d97066540c53d9ca97c0030aacf7fb7e21b9916f`.
- [x] Triggered CodeMagic workflow `ios-testflight` build
  `69dc8febbe1c98fae68a2cc7`.
- [x] CodeMagic build passed with 14 successful actions and no failed action.
- [x] CodeMagic produced signed IPA artifact `construction_inspector.ipa` plus
  `construction-inspector-tracking-app_7_artifacts.zip`.

