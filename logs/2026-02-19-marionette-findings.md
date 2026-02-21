# Marionette UI Test Findings

**Date**: 2026-02-19
**Session**: 397
**App State**: NOT fresh install — 3 existing projects from prior sessions
**Auth**: Supabase not configured, auth bypassed (offline-only mode)

---

## Journey 1: Authentication Flow — SKIPPED (Auth Bypassed)

**Status**: SKIPPED
**Reason**: Supabase not configured. App launches directly to Projects screen.

### Notes
- Auth screens (Login, Register, Forgot Password) cannot be tested without Supabase config
- App correctly detects missing Supabase and enters offline-only mode
- No crash or error on launch

---

## Journey 2: Project Setup — IN PROGRESS (stopped at Pay Items PDF import)

**Status**: PARTIAL — completed Details, Locations, Contractors tabs. Pay Items PDF import triggered but Marionette MCP crashed during heavy pipeline rendering.

### What Was Tested
- **Details tab**: Form validation (empty submit), field entry, duplicate project number check
- **Locations tab**: Empty state, Add Location dialog, added 3 locations (Main Street, Pump Station, Water Tower)
- **Contractors tab**: Empty state, Add Contractor dialog, added ABC Construction (Sub, 3 equipment: Excavator, Dump Truck, Loader) and XYZ Plumbing (Sub, 1 equipment: Pipe Threader)
- **Pay Items tab**: Empty state, Add Pay Item source dialog (Manual vs PDF Import), triggered PDF import with Springfield PDF

### What Was NOT Tested (resume here)
- Pay Items: PDF import preview/results screen, item review, accept/reject flow
- Pay Items: Manual bid item entry, edit, delete
- Save project and verify it appears in project list
- Dashboard reflection of new project data

### Issues Found

| # | Type | Screen | Description | Severity |
|---|------|--------|-------------|----------|
| P1 | Bug | ProjectSetup/Details | Description field has no ValueKey — cannot be automated via Marionette | Low |
| P2 | Bug | ProjectSetup/Contractors | Both "+ Add Equipment" buttons share the same key `project_add_equipment_button` — duplicate keys across contractors. Had to use coordinates to tap the correct one. | Medium |
| P3 | UX | ProjectSetup/PayItems | "Import from PDF" should be the FIRST option in the Add Pay Item dialog, not second. PDF import is the primary use case — manual entry is the fallback. (User feedback) | Medium |
| P4 | Infra | Pipeline/Rendering | Marionette MCP server crashes during heavy PDF pipeline rendering (15-page render at 300 DPI). Memory pressure disconnects the VM service. | High |
| P5 | OK | ProjectSetup/Details | Form validation works correctly — red borders and error messages on required fields (Name, Number) when saving empty form | Pass |
| P6 | OK | ProjectSetup/Details | Duplicate project number check works — snackbar "A project with number '864130' already exists." | Pass |
| P7 | OK | ProjectSetup/Locations | Empty state displays correctly with "No locations added yet" and Add button | Pass |
| P8 | OK | ProjectSetup/Locations | Add Location dialog works — Name (required) + Description fields, Cancel/Add buttons | Pass |
| P9 | OK | ProjectSetup/Locations | Location cards display with pin icon, name, and delete button | Pass |
| P10 | OK | ProjectSetup/Contractors | Empty state displays correctly | Pass |
| P11 | OK | ProjectSetup/Contractors | Add Contractor dialog works — Name + Type dropdown (defaults to Subcontractor) | Pass |
| P12 | OK | ProjectSetup/Contractors | Contractor cards expand on tap to show equipment section | Pass |
| P13 | OK | ProjectSetup/Contractors | Equipment chips display with X to remove, count updates correctly | Pass |
| P14 | OK | ProjectSetup/Contractors | Add Equipment dialog works — Name + Description fields | Pass |
| P15 | OK | ProjectSetup/PayItems | Add Pay Item source dialog shows "Add Manually" and "Import from PDF" options | Pass |
| P16 | OK | ProjectSetup/PayItems | PDF import triggers system file picker correctly | Pass |
| P17 | OK | Navigation | All 4 tabs (Details, Locations, Contractors, Pay Items) navigate correctly | Pass |
| P18 | OK | Navigation | Bottom nav bar works — Dashboard, Calendar, Projects, Settings tabs all navigate | Pass |

### Checks (Journey 2)
- [x] Tab navigation works between all 4 tabs
- [x] Form validation fires on required fields (Name, Number)
- [x] All dialogs open and close properly (Location, Contractor, Equipment)
- [x] Equipment chips display correctly on contractor cards
- [ ] Pay item edit pre-fills existing values (NOT TESTED)
- [ ] Delete buttons work for locations, contractors, equipment, bid items (NOT TESTED)
- [ ] Project appears in list after save (NOT TESTED — PDF import in progress when crashed)
- [ ] Dashboard reflects new project data (NOT TESTED)

---

## Journey 3: Daily Entries — PARTIAL (Session 407)

**Date**: 2026-02-20
**Status**: PARTIAL — created 2 entries, tested core wizard features

### What Was Tested
- **Entry 1**: Auto-filled location (17th Street), weather (Snow, 31/46F). Filled all Safety fields (site safety, SESC, traffic control, visitors). Submitted successfully. Report generated.
- **Entry 2**: Changed location via dropdown (tested dropdown interaction). Incremented personnel (Foreman: 2, Laborer: 3). Toggled equipment chips (Excavator, Dump Truck). Filled Activities text. Submitted. Report showed all data correctly.

### Issues Found

| # | Type | Screen | Description | Severity |
|---|------|--------|-------------|----------|
| P5 | UX | EntryWizard | Auto-fill carries forward stale weather data (Snow, 31/46F) on every new entry — user might not notice incorrect weather | Medium |
| P6 | Bug | EntryWizard | `scroll_to` cannot scroll UP — only scrolls down. Once past the Activities field, cannot return to it without closing/reopening. Marionette limitation or missing reverse scroll. | Medium |
| P7 | OK | EntryWizard | Location dropdown works — shows all project locations, selection updates correctly | Pass |
| P8 | OK | EntryWizard | Personnel increment/decrement buttons work correctly (Foreman +2, Laborer +3) | Pass |
| P9 | OK | EntryWizard | Equipment FilterChips toggle on/off with checkmark + cyan highlight | Pass |
| P10 | OK | EntryWizard | Text entry works in all TextFormFields (activities, safety, SESC, traffic, visitors) | Pass |
| P11 | OK | EntryWizard | "Generate Report" button works, creates entry and navigates to report screen | Pass |
| P12 | OK | Report | Report displays all entered data correctly — activities, contractors (5 personnel, 2 equipment), safety fields | Pass |
| P13 | OK | Report | Contractors only appear on report when personnel count > 0 (correct behavior) | Pass |
| P14 | OK | Dashboard | Entry count increments correctly after each new entry (117 → 118 → 119) | Pass |

### Not Tested (resume here)
- Entry with quantities (Add Quantity / Calculator integration)
- Entry with photos/attachments
- Duplicate Entry flow
- Export PDF from report

---

## Journey 4: Toolbox Features — PARTIAL (Session 407)

**Date**: 2026-02-20
**Status**: PARTIAL — Calculator and Forms tested, Gallery and Todos MISSING from UI

### What Was Tested
- **Toolbox Home**: Only 2 cards visible (Forms, Calculator) — expected 4
- **HMA Calculator**: Area=5000, Thickness=4, Density=145 → 120.83 tons. Copy/Save/Clear buttons work. "Saved to history" confirmation.
- **Concrete Calculator**: Length=30, Width=20, Thickness=8 → 14.81 CY. Formula breakdown shown.
- **Forms List**: 2 built-in forms (MDOT 0582B Density 17 fields, MDOT 1174R Concrete 20 fields) with "Built-in" badges
- **Form Fill**: Split view — fields on left, live PDF preview on right. Auto-fill populated Contractor, Project Name, Subcontractor, Job Number, Route, Date. Source tags (Prime Contractor, Project) with dismissible chips. "Create Pre-filled Project Form?" dialog appeared.

### Issues Found

| # | Type | Screen | Description | Severity |
|---|------|--------|-------------|----------|
| P15 | Bug | ToolboxHome | Only 2 cards shown (Forms, Calculator). **Gallery and To-Do's cards are MISSING** — journey plan expected 4 tools. Either not implemented or not rendering. | High |
| P16 | UX | FormFill | Closing form with auto-filled data does NOT show "unsaved changes" dialog — auto-filled data may be lost silently | Medium |
| P17 | OK | Calculator | HMA tab computes correctly: (5000 × 4 × 145) / 2000 = 120.83 tons | Pass |
| P18 | OK | Calculator | Concrete tab computes correctly: (30 × 20 × 8/12) / 27 = 14.81 CY | Pass |
| P19 | OK | Calculator | Tab switching works, Save to history works, formula breakdown displayed | Pass |
| P20 | OK | Calculator | Density pre-fills to 145 pcf | Pass |
| P21 | OK | Forms | Form list shows built-in forms with field counts and badges | Pass |
| P22 | OK | FormFill | Auto-fill correctly populates fields from project/contractor/inspector data | Pass |
| P23 | OK | FormFill | Live PDF preview renders on right side with populated data | Pass |

---

## Journey 5: Settings & Profile — COMPLETE (Session 407)

**Date**: 2026-02-20
**Status**: COMPLETE — all sections verified

### What Was Tested
- **Appearance**: Dark Mode (default), Light Mode, High Contrast — radio buttons with icons. Theme switch is instant.
- **Inspector Profile**: Robert Sebastian (Full Name), RS (auto-generated initials), Phone "Not set", Certification Number "Not set". Edit pencil icons on each field.
- **Toggles**: Use Last Values (ON), Auto-load Last Project (ON), Auto-fetch Weather (ON), Auto-sync on WiFi (ON)
- **Account**: Sign Out button present
- **Cloud Sync**: "4 pending", "Last sync: Never synced", "Sync Now" button, "4 pending changes - Will sync when online"
- **Weather API**: Open-Meteo (Free) — "Active" badge
- **Data**: Backup Data, Restore Data, Clear Cached Exports
- **About**: Version 1.0.0 (Build 1), Licenses
- **Clear Cache Dialog**: Confirmation dialog with "Cancel" / "Clear Cache" — explains data is safe

### Issues Found

| # | Type | Screen | Description | Severity |
|---|------|--------|-------------|----------|
| P24 | OK | Settings | Theme switching works instantly (Dark/Light/High Contrast) | Pass |
| P25 | OK | Settings | All toggle switches visible with correct labels and descriptions | Pass |
| P26 | OK | Settings | Inspector profile shows name, initials, phone, cert number with edit icons | Pass |
| P27 | OK | Settings | Cloud sync section shows pending count, last sync time, sync button | Pass |
| P28 | OK | Settings | Clear Cached Exports dialog appears with proper warning text | Pass |
| P29 | OK | Settings | Version and Licenses section present at bottom | Pass |

---

## Journey 6: Browse & Edit — COMPLETE (Session 407-408)

**Date**: 2026-02-20
**Status**: COMPLETE — entries list, report inline editing, calendar view all tested

### What Was Tested
- **Entries List**: Grouped by date (Today, Dec 11 2024, Dec 10 2024...). Each card shows location, activities preview, weather icon, temp, status badge. Filter (funnel) and refresh icons in toolbar.
- **Entry Report**: Full report rendered correctly with all sections
- **Inline Location Edit**: Change Location dialog opens with dropdown of all project locations. Location change persists and updates entries list.
- **Inline Weather Edit**: Change Weather dialog opens with 6 conditions (Sunny, Cloudy, Overcast, Rainy, Snow, Windy) with icons. Dropdown selection works (note: Marionette has tap offset issues with dropdown overlays).
- **Inline Temperature Edit**: Tapping temperature section reveals `report_temp_low_field` and `report_temp_high_field` text fields. Fields appear and are editable but **values did not persist** when tapping away — potential bug with number-type field auto-save or Marionette enter_text not triggering onChanged.
- **Inline Activities Edit**: Tapping Activities card reveals `report_activities_field` TextField. Text replacement works and **persists correctly** — confirmed in entries list after navigating away.
- **Inline Contractor Edit**: Tapping contractor row opens rich inline editor with -/+ personnel counters (Foreman, Laborer, Operator), "+ Add Type" button, equipment FilterChips (toggle on/off), and "Done" button. Changes persist and summary header updates ("6 personnel, 3 equipment").
- **Safety Section**: All sub-fields display correctly (Site Safety, SESC Measures, Traffic Control, Visitors).
- **Report Menu**: Three-dot menu shows Duplicate Entry, Generate Debug PDF, Delete Entry (red).
- **Export PDF**: Button generates PDF with filename "IDR 2026-02-20 864130.pdf". Dialog offers Cancel, Preview, Save As, Share (primary).
- **Calendar View**: Month/2 Weeks/Week toggles work. Today (Feb 20) highlighted cyan. Entry chips below calendar for selected date show location + status. Tapping chip selects it and shows detail. Week view shows inline Weather/Activities sections with edit pencil icons.
- **Dashboard**: Stats cards show 119 Entries, 131 Pay Items, 17 Contractors, Toolbox. Budget Overview: $7,882,927 total, 17.8% used ($1.4M / $6.48M remaining).

### Issues Found

| # | Type | Screen | Description | Severity |
|---|------|--------|-------------|----------|
| P30 | UX | EntriesList | Entry 1 (17th Street, no activities) shows "Complete" status — should arguably be "Draft" since activities field is empty | Low |
| P34 | Bug | Report/TempEdit | Inline temperature edit fields appear but entered values do NOT persist when tapping away — auto-save may not fire for number-type TextFields | Medium |
| P35 | Infra | Report/Dropdowns | Marionette tap offset issue with dropdown overlays — tapping a dropdown item may select the wrong one (location "Barberry" → saved "27th Street"). Affects location and weather change dialogs. | Low |
| P31 | OK | EntriesList | Entries grouped by date with correct headings | Pass |
| P32 | OK | EntriesList | Entry cards show location, weather icon, temp range, status badge, activities preview | Pass |
| P33 | OK | EntriesList | Filter and refresh icons present in toolbar | Pass |
| P36 | OK | Report/Location | Change Location dialog opens, dropdown shows all project locations | Pass |
| P37 | OK | Report/Weather | Change Weather dialog opens with 6 conditions + icons | Pass |
| P38 | OK | Report/Activities | Inline activities text edit works and persists | Pass |
| P39 | OK | Report/Contractors | Inline contractor edit: personnel ±, equipment chips, Add Type, Done all work | Pass |
| P40 | OK | Report/Contractors | Summary header updates after contractor edit (personnel + equipment counts) | Pass |
| P41 | OK | Report/Safety | All safety sub-fields display (Site Safety, SESC, Traffic, Visitors) | Pass |
| P42 | OK | Report/Menu | Popup menu shows Duplicate Entry, Generate Debug PDF, Delete Entry | Pass |
| P43 | OK | Report/PDF | Export PDF generates "IDR YYYY-MM-DD #.pdf", offers Preview/Save As/Share | Pass |
| P44 | OK | Calendar | Month/2 Weeks/Week view modes all render correctly | Pass |
| P45 | OK | Calendar | Today highlighted, entry chips selectable, detail shown below | Pass |
| P46 | OK | Calendar | Week view shows inline edit pencils for Weather/Activities | Pass |
| P47 | OK | Dashboard | Stats cards accurate (119 entries, 131 pay items, 17 contractors) | Pass |
| P48 | OK | Dashboard | Budget overview: $7.88M total, 17.8% used, progress bar correct | Pass |

---

## Journey 7: Quantities & PDF — COMPLETE (Session 408)

**Date**: 2026-02-20
**Status**: COMPLETE — quantities screen, search, sort, bid item detail, PDF export all tested

### What Was Tested
- **Pay Items & Quantities screen**: Header shows "Total Contract Value $7,882,926.73" with "131 items" badge. Search bar, Import PDF button, Sort button in toolbar.
- **Item Cards**: Each shows item number (cyan badge), description, Bid Qty/Used/Remaining with progress bar, unit price and total value. Well-designed layout.
- **Search**: Typed "water" in search field — field accepted text and showed clear (X) button, but **list did NOT filter** (still showed "131 items"). Likely a bug where search onChange isn't triggered, or Marionette enter_text doesn't fire Flutter text change listeners.
- **Sort**: 3 options — Item Number (default), Description, Value. Sort by Value worked (reordered to show cheapest first: $0.20, $297.30...).
- **Sort Bug**: Item Number sort uses **string/lexicographic ordering** (#1, #10, #100) instead of numeric (#1, #2, #3...). User-confirmed bug.
- **Bid Item Detail Sheet**: Bottom sheet opens on item tap. Shows item number badge, description, M&P body text ("Measured and paid for individually..."), Quantities cards (Bid/Used/Remaining), progress bar with percentage.
- **M&P Integration**: Detail sheet correctly pulls M&P body text from extraction pipeline — validates end-to-end data flow.

### Issues Found

| # | Type | Screen | Description | Severity |
|---|------|--------|-------------|----------|
| P49 | Bug | Quantities/Search | Search field accepts text but does NOT filter the list — "131 items" remains after typing "water". Either search onChange not wired or Marionette limitation. | High |
| P50 | Bug | Quantities/Sort | Item Number sort uses STRING ordering (#1, #10, #100, #2...) instead of NUMERIC (#1, #2, #3...). User-confirmed. | High |
| P51 | OK | Quantities | Header shows correct total contract value and item count | Pass |
| P52 | OK | Quantities | Item cards display all fields: item #, description, Bid Qty/Used/Remaining, progress bar, prices | Pass |
| P53 | OK | Quantities/Sort | Sort by Value correctly reorders items ascending | Pass |
| P54 | OK | Quantities/Sort | Sort menu shows 3 options with icons, active sort highlighted | Pass |
| P55 | OK | Quantities/Detail | Bid item detail sheet shows item info, M&P body text, quantities breakdown | Pass |
| P56 | OK | Quantities/Detail | M&P extraction body text correctly displayed in detail sheet | Pass |

---

## Journey 8: Cleanup & Lifecycle — COMPLETE (Session 408)

**Date**: 2026-02-20
**Status**: COMPLETE — archive/unarchive, project edit, sign out dialog all tested

### What Was Tested
- **Projects Screen**: Single project card shows name, number, client, description, "Active" badge, date "Today", edit (pencil) and archive (box) icons. Search icon in toolbar. "+ New Project" FAB.
- **Archive Toggle**: Tapping archive icon changes badge from "Active" (green) to "Archived" (gray outline). Tapping again restores to "Active". Toggle is instant.
- **Dashboard After Archive**: Dashboard still shows the archived project's data (same stats, same title). May need a "no active project" state when all projects are archived.
- **Edit Project**: Opens "Edit Project" screen with 4 tabs (Details, Locations, Contractors, Pay Items). All data preserved:
  - Details: Name, Number, Client, Description all pre-filled
  - Locations: 8+ locations listed with pin icons and delete buttons
  - Contractors: 6+ contractors with type badges (Prime/Sub) and equipment counts
- **Sign Out**: Tapping "Sign Out" shows confirmation dialog: "Are you sure you want to sign out?" with Cancel and Sign Out (red) buttons. Cancel dismisses correctly.

### Issues Found

| # | Type | Screen | Description | Severity |
|---|------|--------|-------------|----------|
| P57 | UX | Dashboard | Dashboard still shows archived project data — should arguably show "No active project" or prompt to select a different project | Low |
| P58 | OK | Projects | Project card displays all info: name, number, client, description, status badge, date | Pass |
| P59 | OK | Projects | Archive/unarchive toggle works instantly with correct badge changes | Pass |
| P60 | OK | Projects | Edit opens with all data preserved across all 4 tabs | Pass |
| P61 | OK | Projects | Locations tab shows all locations with delete buttons | Pass |
| P62 | OK | Projects | Contractors tab shows all contractors with type badges and equipment counts | Pass |
| P63 | OK | Settings | Sign Out shows confirmation dialog with Cancel/Sign Out | Pass |

### Not Tested
- Entry deletion (long-press or from menu) — skipped to avoid data loss
- Two-step project deletion (type "DELETE") — skipped to preserve test data
- Clear Cached Exports — skipped (tested in Session 407)

---

## Master Problem Checklist

| # | Journey | Type | Screen | Description | Severity |
|---|---------|------|--------|-------------|----------|
| P1 | J2 | Bug | Details | Description field missing ValueKey (not automatable) | Low |
| P2 | J2 | Bug | Contractors | Duplicate `project_add_equipment_button` key across multiple contractors | Medium |
| P3 | J2 | UX | Pay Items | "Import from PDF" should be first option, not second | Medium |
| P4 | J2 | Infra | Pipeline | Marionette MCP crashes during heavy PDF rendering (memory pressure) | High |
| P5 | J3 | UX | EntryWizard | Auto-fill carries forward stale weather — user might not notice | Medium |
| P6 | J3 | Bug | EntryWizard | scroll_to only scrolls down, cannot scroll back up | Medium |
| P15 | J4 | Bug | ToolboxHome | Gallery and To-Do's cards MISSING — only Forms and Calculator shown | High |
| P16 | J4 | UX | FormFill | No "unsaved changes" dialog when closing form with auto-filled data | Medium |
| P30 | J6 | UX | EntriesList | Empty-activities entry shows "Complete" instead of "Draft" | Low |
| P34 | J6 | Bug | Report/TempEdit | Inline temp edit values don't persist when tapping away | Medium |
| P35 | J6 | Infra | Report/Dropdowns | Marionette tap offset with dropdown overlays (selects wrong item) | Low |
| P49 | J7 | Bug | Quantities/Search | Search field doesn't filter results | High |
| P50 | J7 | Bug | Quantities/Sort | Item Number sort is string-based, not numeric (#1, #10, #100 vs #1, #2, #3) | High |
| P57 | J8 | UX | Dashboard | Dashboard still shows archived project data instead of empty/prompt state | Low |

**Summary**: 14 issues found (3 High, 5 Medium, 4 Low, 2 Infra). 2 High-priority bugs are in Quantities screen (search + sort).

---

## Marionette Tool Keys Discovered

### Bottom Navigation
- `dashboard_nav_button`, `calendar_nav_button`, `projects_nav_button`, `settings_nav_button`

### Projects Screen
- `add_project_fab`, `project_filter_toggle`
- `project_card_{id}`, `project_edit_menu_item_{id}`, `project_archive_toggle_{id}`

### Project Setup
- `project_details_tab`, `project_locations_tab`, `project_contractors_tab`, `project_payitems_tab`
- `project_name_field`, `project_number_field`, `project_client_field` (Description field has NO key)
- `project_save_button`
- `project_add_location_button`, `location_dialog`, `location_name_field`, `location_description_field`, `location_dialog_cancel`, `location_dialog_add`
- `contractor_add_button`, `contractor_name_field`, `contractor_type_dropdown`, `contractor_save_button`, `contractor_cancel_button`
- `contractor_card_{id}`, `contractor_delete_{id}`
- `project_add_equipment_button` (DUPLICATE — same key on all contractors)
- `equipment_dialog`, `equipment_name_field`, `equipment_description_field`, `equipment_dialog_cancel`, `equipment_dialog_add`
- `equipment_delete_chip_{id}`
- `project_add_pay_item_button`

### Report Screen
- `report_screen_title`, `report_export_pdf_button`, `report_menu_button`
- `report_header_location_button`, `report_header_location_dropdown`
- `report_header_weather_button`, `report_header_weather_dropdown`
- `report_temperature_section`, `report_temp_low_field`, `report_temp_high_field`
- `report_activities_section`, `report_activities_field`
- `report_add_contractor_button`

### Quantities Screen
- `quantities_search_field`, `quantities_import_button`, `quantities_sort_button`
