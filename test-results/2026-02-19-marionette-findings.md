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

## Journey 3: Daily Entries — NOT STARTED

---

## Journey 4: Toolbox Features — NOT STARTED

---

## Journey 5: Settings & Profile — NOT STARTED

---

## Journey 6: Browse & Edit — NOT STARTED

---

## Journey 7: Quantities & PDF — NOT STARTED

---

## Journey 8: Cleanup & Lifecycle — NOT STARTED

---

## Master Problem Checklist

| # | Journey | Type | Screen | Description | Severity |
|---|---------|------|--------|-------------|----------|
| P1 | J2 | Bug | Details | Description field missing ValueKey (not automatable) | Low |
| P2 | J2 | Bug | Contractors | Duplicate `project_add_equipment_button` key across multiple contractors | Medium |
| P3 | J2 | UX | Pay Items | "Import from PDF" should be first option, not second | Medium |
| P4 | J2 | Infra | Pipeline | Marionette MCP crashes during heavy PDF rendering (memory pressure) | High |

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
