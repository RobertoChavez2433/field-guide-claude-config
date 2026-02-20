# Marionette UI Test Journeys

**Created**: 2026-02-19
**Purpose**: Comprehensive agent-driven UI testing via Marionette MCP
**Execution**: Claude connects to running debug app, executes each journey sequentially
**Coverage**: All 23 screens, 30+ dialogs, every form field, every button

## Prerequisites

- App running in debug mode with MarionetteBinding active
- Marionette MCP connected via VM service URI
- Fresh app install (clean database) for Pass 1
- Pass 2 uses data created in Pass 1

## Screenshot Protocol

Every journey follows this screenshot protocol:
- **BEFORE**: Screenshot before each major action
- **AFTER**: Screenshot after each major action
- **DIALOG**: Screenshot every dialog/sheet when opened
- **ERROR**: Screenshot + get_logs on any unexpected state
- **EMPTY**: Screenshot all empty/loading/error states encountered
- **SAVE**: Screenshot after any save/submit to confirm success

Save findings to: `.claude/test-results/YYYY-MM-DD-journey-N-findings.md`

---

# PASS 1: FRESH INSTALL (Creation Flows)

---

## Journey 1: Authentication Flow

**Goal**: Test all auth screens — register, login, forgot password
**Screens**: LoginScreen, RegisterScreen, ForgotPasswordScreen
**Pre-condition**: Fresh app, no authenticated user, Supabase not configured (bypasses real auth)

> **NOTE**: If Supabase is not configured, auth is bypassed and app goes straight to dashboard.
> If Supabase IS configured, test the full auth flow. If not, skip to Journey 2.

### Steps (Supabase configured)

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 1.1 | App launches to login screen | `take_screenshots` | Login form visible with email, password fields |
| 1.2 | Screenshot login screen layout | `take_screenshots` | Logo, form fields, buttons all visible and aligned |
| 1.3 | Tap "Sign Up" link | `tap` on "Sign Up" text | Navigate to register screen |
| 1.4 | Screenshot register screen | `take_screenshots` | 4 fields: name, email, password, confirm password |
| 1.5 | Test empty form submit | `tap` on "Create Account" | Validation errors appear on required fields |
| 1.6 | Screenshot validation errors | `take_screenshots` | Error messages visible, red styling |
| 1.7 | Fill name field | `enter_text` "Test Inspector" | Text appears in field |
| 1.8 | Fill email field | `enter_text` "test@example.com" | Text appears in field |
| 1.9 | Fill password (short) | `enter_text` "12345" | Text appears (obscured) |
| 1.10 | Fill confirm password (mismatch) | `enter_text` "12346" | Text appears (obscured) |
| 1.11 | Tap "Create Account" | `tap` | Validation: password too short + mismatch errors |
| 1.12 | Screenshot validation state | `take_screenshots` | Both password errors visible |
| 1.13 | Toggle password visibility | `tap` visibility icon | Password text becomes visible |
| 1.14 | Screenshot visible password | `take_screenshots` | Password text shown, icon changed |
| 1.15 | Navigate back to login | `tap` "Sign In" text | Login screen visible |
| 1.16 | Tap "Forgot Password?" | `tap` | Forgot password screen visible |
| 1.17 | Screenshot forgot password | `take_screenshots` | Email field, send button visible |
| 1.18 | Submit empty email | `tap` "Send Reset Link" | Validation error |
| 1.19 | Enter valid email | `enter_text` "test@example.com" | Email in field |
| 1.20 | Tap "Send Reset Link" | `tap` | Success view or error (depending on Supabase) |
| 1.21 | Screenshot result | `take_screenshots` | Success message or error snackbar |
| 1.22 | Navigate back to login | `tap` "Back to Sign In" | Login screen |

### Checks
- [ ] All form validations fire correctly
- [ ] Password visibility toggle works on both password fields
- [ ] Navigation between all 3 auth screens works
- [ ] Error states display properly (snackbars, inline errors)
- [ ] Loading spinner appears during async operations
- [ ] Keyboard types correct (email keyboard for email field)

---

## Journey 2: Project Setup

**Goal**: Create a complete project with locations, contractors, equipment, and pay items
**Screens**: ProjectListScreen, ProjectSetupScreen (4 tabs), PdfImportPreviewScreen
**Pre-condition**: Authenticated (or auth bypassed), no projects exist

### Steps

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| **Empty State** | | | |
| 2.1 | Navigate to Projects tab | `tap` Projects nav button | Empty project list |
| 2.2 | Screenshot empty projects list | `take_screenshots` | "No projects" message, "Create Project" button visible |
| 2.3 | Navigate to Dashboard tab | `tap` Dashboard nav button | Dashboard with no-project state |
| 2.4 | Screenshot empty dashboard | `take_screenshots` | "No project selected" or empty state |
| **Create Project** | | | |
| 2.5 | Tap "New Project" FAB (from Projects tab) | `tap` FAB | ProjectSetupScreen opens |
| 2.6 | Screenshot project setup - Details tab | `take_screenshots` | Empty form with name, number, client, description |
| 2.7 | Try saving empty form | `tap` "Save" | Validation errors on required fields (name, number) |
| 2.8 | Screenshot validation errors | `take_screenshots` | Red error text on required fields |
| 2.9 | Enter project name | `enter_text` "Springfield Water System" | Text in name field |
| 2.10 | Enter project number | `enter_text` "864130" | Text in number field |
| 2.11 | Enter client name | `enter_text` "City of Springfield" | Text in client field |
| 2.12 | Enter description | `enter_text` "DWSRF Water System Improvements" | Text in description field |
| **Locations Tab** | | | |
| 2.13 | Tap "Locations" tab | `tap` | Locations tab selected, empty list |
| 2.14 | Screenshot empty locations | `take_screenshots` | Empty state or "Add Location" prompt |
| 2.15 | Tap "Add Location" | `tap` | AddLocationDialog opens |
| 2.16 | Screenshot add location dialog | `take_screenshots` | Name field visible |
| 2.17 | Enter location name | `enter_text` "Main Street" | Text in field |
| 2.18 | Save location | `tap` save/add button | Location appears in list |
| 2.19 | Add second location | Repeat: `tap` Add, `enter_text` "Pump Station", save | Two locations in list |
| 2.20 | Add third location | Repeat: `enter_text` "Water Tower" | Three locations |
| 2.21 | Screenshot locations list | `take_screenshots` | All 3 locations visible |
| **Contractors Tab** | | | |
| 2.22 | Tap "Contractors" tab | `tap` | Contractors tab, empty list |
| 2.23 | Screenshot empty contractors | `take_screenshots` | Empty state |
| 2.24 | Tap "Add Contractor" | `tap` | AddContractorDialog opens |
| 2.25 | Screenshot add contractor dialog | `take_screenshots` | Name, type fields visible |
| 2.26 | Enter contractor name | `enter_text` "ABC Construction" | Text in field |
| 2.27 | Select contractor type (if dropdown) | `tap` type selector | Type options visible |
| 2.28 | Save contractor | `tap` save button | Contractor appears in list |
| 2.29 | Add equipment to contractor | `tap` "Add Equipment" on contractor card | AddEquipmentDialog |
| 2.30 | Screenshot equipment dialog | `take_screenshots` | Equipment name field |
| 2.31 | Enter equipment | `enter_text` "Excavator" | Text in field |
| 2.32 | Save equipment | `tap` save | Equipment chip appears on contractor |
| 2.33 | Add more equipment | Repeat: "Dump Truck", "Loader" | Multiple equipment chips |
| 2.34 | Add second contractor | "XYZ Plumbing" with equipment "Pipe Threader" | Second contractor in list |
| 2.35 | Screenshot contractors with equipment | `take_screenshots` | Both contractors with equipment chips |
| **Pay Items Tab** | | | |
| 2.36 | Tap "Pay Items" tab | `tap` | Pay Items tab, empty list |
| 2.37 | Screenshot empty pay items | `take_screenshots` | Empty state |
| 2.38 | Tap "Add Pay Item" | `tap` | PayItemSourceDialog opens |
| 2.39 | Screenshot pay item source dialog | `take_screenshots` | "Manual" and "PDF Import" options |
| 2.40 | Choose "Manual" | `tap` | BidItemDialog opens |
| 2.41 | Screenshot bid item dialog | `take_screenshots` | Fields: item number, description, unit, quantity, unit price |
| 2.42 | Fill bid item: number | `enter_text` "1" | |
| 2.43 | Fill bid item: description | `enter_text` "Mobilization" | |
| 2.44 | Fill bid item: unit | `enter_text` "LS" | |
| 2.45 | Fill bid item: quantity | `enter_text` "1" | |
| 2.46 | Fill bid item: unit price | `enter_text` "50000.00" | |
| 2.47 | Save bid item | `tap` save | Item appears in pay items list |
| 2.48 | Add second bid item manually | "2", "8-inch Water Main", "LF", "2500", "85.00" | |
| 2.49 | Add third bid item manually | "3", "Fire Hydrant Assembly", "EA", "10", "4500.00" | |
| 2.50 | Screenshot pay items list | `take_screenshots` | 3 items visible with details |
| 2.51 | Edit a pay item | `tap` edit icon on item 1 | BidItemDialog opens pre-filled |
| 2.52 | Change unit price | Clear and `enter_text` "55000.00" | Updated value |
| 2.53 | Save edit | `tap` save | Updated value in list |
| 2.54 | Screenshot after edit | `take_screenshots` | Confirm updated price shows |
| **Save Project** | | | |
| 2.55 | Tap "Save" in AppBar | `tap` Save | Project saves, navigates back |
| 2.56 | Screenshot project list | `take_screenshots` | New project appears in list |
| 2.57 | Verify dashboard loads | `tap` Dashboard nav | Dashboard shows project data |
| 2.58 | Screenshot dashboard with project | `take_screenshots` | Stats cards populated |

### Checks
- [ ] Tab navigation works between all 4 tabs
- [ ] Form validation fires on required fields
- [ ] All dialogs open and close properly
- [ ] Equipment chips display correctly on contractor cards
- [ ] Pay item edit pre-fills existing values
- [ ] Delete buttons work for locations, contractors, equipment, bid items
- [ ] Project appears in list after save
- [ ] Dashboard reflects new project data

---

## Journey 3: Daily Entries (5 Entries)

**Goal**: Create 5 daily entries, each testing different feature combinations
**Screens**: EntryWizardScreen, QuantityCalculatorScreen, ReportScreen
**Pre-condition**: Project "Springfield Water System" exists with locations, contractors, pay items

### Entry 1: Basic Entry (Weather + Activities + Safety)

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 3.1 | From dashboard, tap "New Entry" | `tap` New Entry button | EntryWizardScreen opens |
| 3.2 | Screenshot entry wizard - empty | `take_screenshots` | All sections visible: location, weather, text fields |
| 3.3 | Select location dropdown | `tap` location dropdown | Location options appear |
| 3.4 | Screenshot location dropdown | `take_screenshots` | 3 locations from project setup visible |
| 3.5 | Select "Main Street" | `tap` "Main Street" | Location selected |
| 3.6 | Tap weather selector | `tap` weather widget | Weather options appear |
| 3.7 | Screenshot weather options | `take_screenshots` | Weather condition choices |
| 3.8 | Select "Sunny" or first option | `tap` weather option | Weather set |
| 3.9 | Enter temp low | `enter_text` "45" in tempLow field | Temperature entered |
| 3.10 | Enter temp high | `enter_text` "72" in tempHigh field | Temperature entered |
| 3.11 | Enter activities | `enter_text` "Installed 200 LF of 8-inch water main on Main Street. Completed hydrant assembly at Station 12+50." | Long text in field |
| 3.12 | Enter site safety | `enter_text` "All workers wore PPE. Safety briefing conducted at 7:00 AM." | Text in field |
| 3.13 | Enter SESC measures | `enter_text` "Silt fence maintained. Dewatering pump operational." | Text in field |
| 3.14 | Enter traffic control | `enter_text` "Lane closure on Main St from Oak to Elm. Flaggers on both ends." | Text in field |
| 3.15 | Enter visitors | `enter_text` "John Smith - City Engineer, inspected valve installation" | Text in field |
| 3.16 | Scroll down to verify all fields | `scroll_to` bottom | All content visible |
| 3.17 | Screenshot filled form | `take_screenshots` | All fields populated |
| 3.18 | Tap Save/Generate Report | `tap` save button | Entry saves, Report screen opens |
| 3.19 | Screenshot report | `take_screenshots` | Report shows all entered data correctly |
| 3.20 | Verify data in report | `take_screenshots` | Weather, temps, activities, safety all match |

### Entry 2: Entry with Quantities (Manual + Calculator)

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 3.21 | Navigate back to dashboard | `tap` back | Dashboard |
| 3.22 | Create new entry | `tap` New Entry | Entry wizard |
| 3.23 | Select location "Pump Station" | `tap` dropdown, select | Location set |
| 3.24 | Set weather "Cloudy" | `tap` weather, select | Weather set |
| 3.25 | Enter temps: 38 / 55 | `enter_text` in both fields | Temps set |
| 3.26 | Enter activities | `enter_text` "Concrete pour for pump station foundation" | Text entered |
| 3.27 | Scroll to quantities section | `scroll_to` quantities area | Quantities section visible |
| 3.28 | Screenshot empty quantities section | `take_screenshots` | No quantities yet |
| 3.29 | Tap "Add Quantity" | `tap` add quantity button | Bid item picker sheet opens |
| 3.30 | Screenshot bid item picker | `take_screenshots` | Available bid items listed |
| 3.31 | Select "8-inch Water Main" (item 2) | `tap` item | Quantity dialog opens |
| 3.32 | Screenshot quantity dialog | `take_screenshots` | Quantity field, notes field |
| 3.33 | Enter quantity value | `enter_text` "150" | Value entered |
| 3.34 | Enter quantity notes | `enter_text` "Sta 10+00 to 11+50" | Notes entered |
| 3.35 | Save quantity | `tap` save | Quantity appears in entry |
| 3.36 | Add second quantity - "Fire Hydrant Assembly" | `tap` add, select item 3 | Dialog opens |
| 3.37 | Enter quantity "2" with notes "Sta 10+50 and 11+00" | `enter_text` | Filled |
| 3.38 | Save | `tap` save | Second quantity in list |
| 3.39 | Tap Calculator button | `tap` calculator icon | QuantityCalculatorScreen opens |
| 3.40 | Screenshot calculator | `take_screenshots` | HMA tab with fields |
| 3.41 | Switch to Concrete tab | `tap` Concrete tab | Concrete fields visible |
| 3.42 | Enter length "20" | `enter_text` "20" | |
| 3.43 | Enter width "15" | `enter_text` "15" | |
| 3.44 | Enter thickness "6" | `enter_text` "6" | |
| 3.45 | Tap "Calculate" | `tap` | Result appears |
| 3.46 | Screenshot calculation result | `take_screenshots` | CY result shown |
| 3.47 | Tap "Use Result" | `tap` | Returns to entry wizard with value |
| 3.48 | Screenshot entry with quantities | `take_screenshots` | Quantities section shows items |
| 3.49 | Save entry | `tap` save | Report opens |
| 3.50 | Screenshot report with quantities | `take_screenshots` | Quantities displayed in report |

### Entry 3: Entry with Contractors & Equipment

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 3.51 | Create new entry from dashboard | `tap` New Entry | Wizard opens |
| 3.52 | Set location "Water Tower" | Select from dropdown | Set |
| 3.53 | Set weather, temps (52/68) | Fill fields | Set |
| 3.54 | Enter activities | `enter_text` "Tower foundation excavation" | Set |
| 3.55 | Scroll to contractors section | `scroll_to` | Contractors visible |
| 3.56 | Screenshot contractors section | `take_screenshots` | Contractors from project listed |
| 3.57 | Toggle "ABC Construction" active | `tap` toggle/checkbox | Contractor selected for this entry |
| 3.58 | Set personnel count for ABC | `tap` personnel area, enter count | Count set |
| 3.59 | Toggle equipment "Excavator" | `tap` equipment toggle | Equipment marked active |
| 3.60 | Toggle equipment "Dump Truck" | `tap` | Active |
| 3.61 | Toggle "XYZ Plumbing" active | `tap` | Contractor selected |
| 3.62 | Set personnel count for XYZ | Enter count | Set |
| 3.63 | Toggle "Pipe Threader" equipment | `tap` | Active |
| 3.64 | Screenshot contractors filled | `take_screenshots` | Both contractors with personnel + equipment |
| 3.65 | Test "Add Equipment" from entry | `tap` Add Equipment | AddEquipmentDialog |
| 3.66 | Screenshot add equipment dialog | `take_screenshots` | Equipment name field |
| 3.67 | Add "Crane" | `enter_text`, save | New equipment chip |
| 3.68 | Test "Add Personnel Type" from entry | `tap` Add Personnel Type | Dialog |
| 3.69 | Screenshot add personnel type dialog | `take_screenshots` | Name, short code fields |
| 3.70 | Add "Foreman" / "FM" | `enter_text`, save | New type available |
| 3.71 | Save entry | `tap` save | Report |
| 3.72 | Screenshot report contractors section | `take_screenshots` | Personnel + equipment displayed |

### Entry 4: Entry with Photos

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 3.73 | Create new entry from dashboard | New Entry | Wizard |
| 3.74 | Set location, weather, temps, activities | Fill basic fields | Set |
| 3.75 | Scroll to photos/attachments section | `scroll_to` | Photos section visible |
| 3.76 | Screenshot empty photos section | `take_screenshots` | No photos, add button visible |
| 3.77 | Tap "Add Photo" | `tap` | PhotoSourceDialog opens |
| 3.78 | Screenshot photo source dialog | `take_screenshots` | Camera / Gallery options |
| 3.79 | Select "Gallery" (camera may not work in test) | `tap` Gallery | File picker opens |
| 3.80 | (Note: file picker is system UI - may need manual intervention or skip) | | |
| 3.81 | If photo attaches, screenshot photo thumbnail | `take_screenshots` | Photo visible in attachments |
| 3.82 | Test "Add Form" button | `tap` Add Form | FormSelectionDialog |
| 3.83 | Screenshot form selection dialog | `take_screenshots` | Available forms listed |
| 3.84 | Select a form | `tap` | Form attaches to entry |
| 3.85 | Screenshot entry with form attached | `take_screenshots` | Form thumbnail visible |
| 3.86 | Save entry | `tap` save | Report |
| 3.87 | Screenshot report attachments section | `take_screenshots` | Photos/forms displayed |

### Entry 5: Full Coverage Entry (Everything Combined)

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 3.88 | Create new entry | New Entry | Wizard |
| 3.89 | Fill ALL fields: location, weather, temps, activities, safety, SESC, traffic, visitors | Fill all | All populated |
| 3.90 | Add 2 quantities with calculator | Add quantities | Quantities section |
| 3.91 | Set contractors and equipment | Toggle all | Contractors section |
| 3.92 | Attempt photo attachment | Add Photo flow | Attachments |
| 3.93 | Attach a form | Add Form flow | Form attached |
| 3.94 | Scroll through entire form top to bottom | `scroll_to` progressively | All sections visible |
| 3.95 | Screenshot complete entry (multiple screenshots) | `take_screenshots` at each section | Full documentation |
| 3.96 | Save entry | `tap` save | Report |
| 3.97 | Screenshot full report | `take_screenshots` (scroll through) | All data visible |
| 3.98 | Test "Export PDF" from report | `tap` Export PDF icon | PDF export flow triggers |
| 3.99 | Screenshot PDF export dialog/result | `take_screenshots` | Export options or preview |
| 3.100 | Test "Duplicate Entry" from report menu | `tap` PopupMenu, Duplicate | New entry created |
| 3.101 | Screenshot duplicated entry | `take_screenshots` | Pre-filled with original data |

### Entry Checks (All 5)
- [ ] Location dropdown populates from project
- [ ] Weather selector works
- [ ] All text fields accept input and display correctly
- [ ] Quantities can be added, edited, deleted
- [ ] Calculator returns results correctly
- [ ] Contractors toggle on/off properly
- [ ] Equipment chips toggle
- [ ] Personnel counts editable
- [ ] Photos can be attached (if system picker works)
- [ ] Forms can be attached
- [ ] Save navigates to report
- [ ] Report displays all entered data accurately
- [ ] PDF export triggers
- [ ] Duplicate entry pre-fills correctly

---

## Journey 4: Toolbox Features

**Goal**: Test all 4 toolbox tools — Forms, Calculator, Gallery, Todos
**Screens**: ToolboxHomeScreen, FormsListScreen, FormFillScreen, CalculatorScreen, GalleryScreen, TodosScreen, FormImportScreen, FieldMappingScreen

### Toolbox Navigation

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 4.1 | Navigate to Toolbox (from dashboard stat card or route) | `tap` Toolbox card | ToolboxHomeScreen |
| 4.2 | Screenshot toolbox home | `take_screenshots` | 4 cards: Forms, Calculator, Gallery, To-Do's |

### Calculator Tool

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 4.3 | Tap "Calculator" card | `tap` | CalculatorScreen opens |
| 4.4 | Screenshot calculator - HMA tab | `take_screenshots` | Area, thickness, density fields |
| 4.5 | Enter area "5000" | `enter_text` | Value in field |
| 4.6 | Enter thickness "4" | `enter_text` | Value in field |
| 4.7 | Verify density default "145" | Read field | Pre-populated |
| 4.8 | Tap "Calculate" | `tap` | Result card appears |
| 4.9 | Screenshot HMA result | `take_screenshots` | Tonnage result shown |
| 4.10 | Tap "Copy" | `tap` | Clipboard (verify via snackbar) |
| 4.11 | Tap "Save" | `tap` | Saved to history |
| 4.12 | Tap "Clear" | `tap` | Fields reset to empty |
| 4.13 | Screenshot cleared state | `take_screenshots` | All fields empty, result gone |
| 4.14 | Switch to Concrete tab | `tap` | Concrete fields visible |
| 4.15 | Enter length "30", width "20", thickness "8" | `enter_text` each | Fields filled |
| 4.16 | Calculate and screenshot | `tap` Calculate, `take_screenshots` | CY result |
| 4.17 | Save to history | `tap` Save | History entry added |
| 4.18 | Scroll to history section | `scroll_to` | History entries visible |
| 4.19 | Screenshot calculation history | `take_screenshots` | Both saved calculations shown |
| 4.20 | Test history copy button | `tap` copy on history item | Clipboard snackbar |

### Todos Tool

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 4.21 | Navigate back, tap "To-Do's" | `tap` | TodosScreen |
| 4.22 | Screenshot empty todos | `take_screenshots` | Empty state message |
| 4.23 | Tap Add (+) FAB | `tap` | Add todo dialog opens |
| 4.24 | Screenshot add todo dialog | `take_screenshots` | Title, description, due date, priority fields |
| 4.25 | Enter title "Order pipe fittings" | `enter_text` | Text in field |
| 4.26 | Enter description "Need 2-inch elbows and tees for pump station" | `enter_text` | Text in field |
| 4.27 | Tap due date picker | `tap` due date area | System date picker opens |
| 4.28 | Select a future date | `tap` date | Date set |
| 4.29 | Set priority to "High" | `tap` High segment | High selected |
| 4.30 | Save todo | `tap` save | Todo appears in list |
| 4.31 | Add 2 more todos with different priorities | Repeat flow | 3 todos total |
| 4.32 | Screenshot todos list | `take_screenshots` | 3 todos with different priorities |
| 4.33 | Tap checkbox on first todo | `tap` checkbox | Todo marked complete (strikethrough) |
| 4.34 | Screenshot completed todo | `take_screenshots` | Strikethrough styling |
| 4.35 | Test filter menu - "Active" | `tap` filter, "Active" | Only non-completed shown |
| 4.36 | Screenshot filtered view | `take_screenshots` | Completed todo hidden |
| 4.37 | Test filter - "Completed" | `tap` filter, "Completed" | Only completed shown |
| 4.38 | Test sort - "Priority" | `tap` sort, "Priority" | Reordered by priority |
| 4.39 | Test sort - "Due Date" | `tap` sort, "Due Date" | Reordered by date |
| 4.40 | Edit a todo | `tap` todo card | Edit dialog opens pre-filled |
| 4.41 | Screenshot edit dialog | `take_screenshots` | Pre-filled fields |
| 4.42 | Change title, save | `enter_text`, save | Updated in list |
| 4.43 | Delete a todo | `tap` delete icon | Confirmation dialog |
| 4.44 | Screenshot delete confirmation | `take_screenshots` | Confirm/cancel buttons |
| 4.45 | Confirm delete | `tap` confirm | Todo removed from list |
| 4.46 | Test "Clear completed" from menu | `tap` more menu, "Clear completed" | Confirmation dialog |
| 4.47 | Confirm clear | `tap` | Completed todos removed |

### Gallery Tool

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 4.48 | Navigate back, tap "Gallery" | `tap` | GalleryScreen |
| 4.49 | Screenshot gallery | `take_screenshots` | Photos from entries (if any) or empty state |
| 4.50 | Test filter button | `tap` filter icon | Filter bottom sheet |
| 4.51 | Screenshot filter sheet | `take_screenshots` | Date chips, entry filter |
| 4.52 | Select "Today" filter | `tap` | Filtered to today's photos |
| 4.53 | Select "This Week" filter | `tap` | Broader filter |
| 4.54 | Select "Custom Range" | `tap` | Date range picker opens |
| 4.55 | Screenshot date range picker | `take_screenshots` | Calendar UI |
| 4.56 | Cancel and clear filters | `tap` cancel, then "Clear All" | All photos shown |
| 4.57 | If photos exist, tap a thumbnail | `tap` photo | Full-screen viewer opens |
| 4.58 | Screenshot full-screen viewer | `take_screenshots` | Photo with info panel |
| 4.59 | Test pinch-to-zoom (if possible) | Interaction test | Zoom behavior |
| 4.60 | Navigate back to gallery | `tap` back | Gallery grid |

### Forms Tool

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 4.61 | Navigate back, tap "Forms" | `tap` | FormsListScreen |
| 4.62 | Screenshot forms list | `take_screenshots` | Available forms with "Built-in" badges |
| 4.63 | Tap "Start" on first form | `tap` | FormFillScreen opens |
| 4.64 | Screenshot empty form | `take_screenshots` | Form fields visible |
| 4.65 | Fill first few fields | `enter_text` each | Fields populated |
| 4.66 | Test auto-fill menu | `tap` auto-fill icon | Auto-fill options appear |
| 4.67 | Screenshot auto-fill options | `take_screenshots` | Auto-fill empty, re-fill, clear, carry-forward |
| 4.68 | Select "Auto-fill empty" | `tap` | Auto-fillable fields populated |
| 4.69 | Screenshot auto-filled form | `take_screenshots` | Auto-filled indicator visible |
| 4.70 | Toggle "Show only fields needing input" | `tap` switch | Filtered view |
| 4.71 | Screenshot filtered fields | `take_screenshots` | Only unfilled fields shown |
| 4.72 | Switch to Preview tab (mobile) | `tap` Preview tab | PDF preview |
| 4.73 | Screenshot preview | `take_screenshots` | PDF rendering of form |
| 4.74 | Tap Save | `tap` save | Form saved |
| 4.75 | Tap Submit | `tap` submit | Form submitted |
| 4.76 | Test Export PDF | `tap` export icon | Export options dialog |
| 4.77 | Screenshot export dialog | `take_screenshots` | Preview/Share/Save options |
| 4.78 | Test close with unsaved changes | Make edit, tap X | Unsaved changes dialog |
| 4.79 | Screenshot unsaved changes dialog | `take_screenshots` | Discard/Cancel/Save options |

### Form Import (if testable)

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 4.80 | Navigate to form import (from forms or route) | Navigate | FormImportScreen |
| 4.81 | Screenshot form import | `take_screenshots` | "Choose File" button, instructions |
| 4.82 | (File picker is system UI - may need skip) | | |

### Toolbox Checks
- [ ] All 4 toolbox cards navigate correctly
- [ ] Calculator: both tabs compute correctly, history saves
- [ ] Todos: CRUD works, filters work, sort works, priority colors correct
- [ ] Gallery: filters work, photo viewer opens, zoom works
- [ ] Forms: fill, auto-fill, preview, save, submit, export all work
- [ ] Unsaved changes dialog appears when needed

---

## Journey 5: Settings & Profile

**Goal**: Test every setting toggle, dialog, and section
**Screens**: SettingsScreen, PersonnelTypesScreen

### Steps

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 5.1 | Tap Settings nav button | `tap` | SettingsScreen opens |
| 5.2 | Screenshot full settings screen (scroll through) | `take_screenshots` multiple | All sections visible |
| **Inspector Profile** | | | |
| 5.3 | Tap inspector name field | `tap` | EditInspectorDialog opens |
| 5.4 | Screenshot edit inspector dialog | `take_screenshots` | Name field |
| 5.5 | Enter name "John Inspector" | `enter_text` | Text entered |
| 5.6 | Save | `tap` save | Name updated in settings |
| 5.7 | Tap initials field | `tap` | Dialog opens |
| 5.8 | Enter "JI" | `enter_text`, save | Initials set |
| 5.9 | Tap phone field | `tap` | Dialog opens |
| 5.10 | Enter "(555) 123-4567" | `enter_text`, save | Phone set |
| 5.11 | Tap cert number field | `tap` | Dialog opens |
| 5.12 | Enter "CERT-2026-001" | `enter_text`, save | Cert set |
| 5.13 | Tap agency field | `tap` | Dialog opens |
| 5.14 | Enter "City of Springfield" | `enter_text`, save | Agency set |
| 5.15 | Screenshot completed profile | `take_screenshots` | All 5 fields populated |
| **Toggles** | | | |
| 5.16 | Toggle "Enable Auto-Fill" | `tap` switch | Switch state changes |
| 5.17 | Toggle "Use Last Values" | `tap` switch | Switch state changes |
| 5.18 | Toggle "Auto-load Last Project" | `tap` switch | Switch state changes |
| 5.19 | Toggle "Auto-sync on WiFi" | `tap` switch | Switch state changes |
| 5.20 | Toggle "Auto-fetch Weather" | `tap` switch | Switch state changes |
| 5.21 | Screenshot all toggles in new state | `take_screenshots` | Toggled values |
| 5.22 | Toggle each back | `tap` each | Restored |
| **Appearance** | | | |
| 5.23 | Test theme selection | `tap` theme options | Theme changes |
| 5.24 | Screenshot each theme | `take_screenshots` | Visual theme applied |
| **Personnel Types** | | | |
| 5.25 | Navigate to PersonnelTypesScreen | `tap` personnel types (if accessible from settings, or navigate via route) | PersonnelTypesScreen |
| 5.26 | Screenshot personnel types | `take_screenshots` | List of types |
| 5.27 | Tap Add (+) | `tap` | Add dialog |
| 5.28 | Enter "Superintendent" / "SI" | `enter_text` | Filled |
| 5.29 | Save | `tap` | New type in list |
| 5.30 | Edit existing type | `tap` edit | Edit dialog pre-filled |
| 5.31 | Change short code | `enter_text`, save | Updated |
| 5.32 | Delete a type | `tap` delete | Confirmation dialog |
| 5.33 | Screenshot delete confirmation | `take_screenshots` | Warning about impact |
| 5.34 | Confirm delete | `tap` | Type removed |
| 5.35 | Test drag reorder | (May not be possible via Marionette) | Reorder |
| **Other Settings** | | | |
| 5.36 | Tap "Clear Cached Exports" | `tap` | ClearCacheDialog |
| 5.37 | Screenshot clear cache dialog | `take_screenshots` | Confirmation |
| 5.38 | Cancel (don't clear yet) | `tap` cancel | Dialog closes |
| 5.39 | Tap "Licenses" | `tap` | License page opens |
| 5.40 | Screenshot licenses page | `take_screenshots` | Flutter license viewer |
| 5.41 | Navigate back | `tap` back | Settings |

### Settings Checks
- [ ] All 5 inspector profile fields editable via dialog
- [ ] All toggle switches work (toggle on, toggle off)
- [ ] Theme changes apply visually
- [ ] Personnel types: add, edit, delete, reorder all work
- [ ] Clear cache dialog appears
- [ ] Licenses page opens
- [ ] No crashes on any interaction

---

# PASS 2: SEEDED DATA (View/Edit/Delete Flows)

**Pre-condition**: All data from Pass 1 exists (1 project, 5 entries, todos, calculations, forms)

---

## Journey 6: Browse & Edit Existing Data

**Goal**: Test viewing, inline editing, and navigation with existing data
**Screens**: Dashboard, HomeScreen (Calendar), EntriesList, ReportScreen

### Steps

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| **Dashboard Review** | | | |
| 6.1 | Open app to dashboard | `take_screenshots` | Dashboard populated with stats |
| 6.2 | Verify stats cards show correct counts | `take_screenshots` | Entries: 5, Pay Items: 3, Contractors: 2 |
| 6.3 | Tap Entries stat card | `tap` | Navigates to EntriesList |
| 6.4 | Screenshot entries list | `take_screenshots` | 5 entries grouped by date |
| 6.5 | Verify entry cards show weather, status, temp | Visual check | Data matches |
| **Calendar View** | | | |
| 6.6 | Navigate to Calendar tab | `tap` Calendar nav | HomeScreen with calendar |
| 6.7 | Screenshot calendar view | `take_screenshots` | Calendar with entry indicators |
| 6.8 | Tap a day with entries | `tap` date | Entries for that day shown |
| 6.9 | Screenshot day entries | `take_screenshots` | Entry cards below calendar |
| 6.10 | Tap an entry card | `tap` | Report or split view |
| **Inline Editing on Report** | | | |
| 6.11 | Open Report for Entry 1 | Navigate to report | Report screen with all data |
| 6.12 | Tap temperature section | `tap` | Inline edit mode |
| 6.13 | Change temp low to "48" | Clear + `enter_text` "48" | Updated |
| 6.14 | Tap away to save | `tap` outside | Auto-saves |
| 6.15 | Screenshot updated temp | `take_screenshots` | New temp displayed |
| 6.16 | Tap activities section | `tap` | Inline edit mode |
| 6.17 | Append text to activities | `enter_text` additional text | Text extended |
| 6.18 | Tap away to save | `tap` outside | Auto-saves |
| 6.19 | Tap location in header | `tap` | Location edit dialog |
| 6.20 | Screenshot location edit dialog | `take_screenshots` | Current location, change options |
| 6.21 | Change location | Select different location | Updated in header |
| 6.22 | Tap weather in header | `tap` | Weather edit dialog |
| 6.23 | Screenshot weather edit dialog | `take_screenshots` | Weather options |
| 6.24 | Change weather | Select different option | Updated |
| **Quantity Editing on Report** | | | |
| 6.25 | Open report for Entry 2 (has quantities) | Navigate | Report with quantities |
| 6.26 | Tap edit on a quantity | `tap` edit icon | Quantity edit mode |
| 6.27 | Change quantity value | `enter_text` new value | Updated |
| 6.28 | Save quantity edit | `tap` save | New value displayed |
| 6.29 | Screenshot updated quantities | `take_screenshots` | New values shown |
| **Contractor Editing on Report** | | | |
| 6.30 | Open report for Entry 3 (has contractors) | Navigate | Report with contractors |
| 6.31 | Tap contractor section to edit | `tap` | Edit mode |
| 6.32 | Change personnel count | `enter_text` new count | Updated |
| 6.33 | Toggle equipment off/on | `tap` equipment toggle | State changes |
| 6.34 | Save contractor edits | `tap` save | Updated display |
| 6.35 | Screenshot updated contractors | `take_screenshots` | New values |
| **Entries List Filtering** | | | |
| 6.36 | Go to entries list | Navigate | All entries |
| 6.37 | Tap filter icon | `tap` | Date range picker |
| 6.38 | Select date range | Pick dates | Filtered list |
| 6.39 | Screenshot filtered entries | `take_screenshots` | Only matching entries shown |
| 6.40 | Clear filter | `tap` clear | All entries restored |
| 6.41 | Pull to refresh | `scroll_to` (pull down gesture) | List refreshes |

### Browse & Edit Checks
- [ ] Dashboard stats are accurate
- [ ] Calendar shows entry indicators on correct dates
- [ ] Inline editing works for all text fields
- [ ] Location and weather dialogs work on report
- [ ] Quantity edit/delete works on report
- [ ] Contractor edit works on report
- [ ] Date range filter works on entries list
- [ ] All auto-saves fire correctly

---

## Journey 7: Quantities & PDF Export

**Goal**: Test quantities browsing, bid item details, and PDF generation
**Screens**: QuantitiesScreen, BidItemDetailSheet, ReportScreen (PDF export)

### Steps

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| 7.1 | Navigate to Quantities (from dashboard card) | `tap` Pay Items stat | QuantitiesScreen |
| 7.2 | Screenshot quantities list | `take_screenshots` | 3 bid items with details |
| 7.3 | Verify summary header (count + total value) | Visual check | Correct totals |
| 7.4 | Test search | `tap` search, `enter_text` "water" | Filtered to water main item |
| 7.5 | Screenshot search results | `take_screenshots` | Filtered list |
| 7.6 | Clear search | Clear field | Full list restored |
| 7.7 | Test sort - "Item Number" | `tap` sort menu, select | Sorted by number |
| 7.8 | Test sort - "Description" | `tap` sort | Sorted alphabetically |
| 7.9 | Test sort - "Value" | `tap` sort | Sorted by value |
| 7.10 | Tap a bid item card | `tap` | BidItemDetailSheet opens |
| 7.11 | Screenshot bid item detail sheet | `take_screenshots` | Item details, usage history |
| 7.12 | Dismiss sheet | Swipe down or tap outside | Sheet closes |
| **PDF Export** | | | |
| 7.13 | Open a report with data | Navigate to Entry 5 report | Full report |
| 7.14 | Tap Export PDF icon | `tap` | PDF generation starts |
| 7.15 | Screenshot PDF export result | `take_screenshots` | Export dialog/preview |
| 7.16 | Test "Duplicate Entry" from menu | `tap` PopupMenu, Duplicate | Entry duplicated |
| 7.17 | Screenshot duplicated entry | `take_screenshots` | Pre-filled copy |
| 7.18 | Test "Delete Entry" from menu | `tap` PopupMenu, Delete | Delete confirmation dialog |
| 7.19 | Screenshot delete confirmation | `take_screenshots` | Warning with details |
| 7.20 | Cancel delete | `tap` Cancel | Entry preserved |

### Quantities & PDF Checks
- [ ] Quantities list populates correctly
- [ ] Search filters work
- [ ] All 3 sort options work
- [ ] Bid item detail sheet shows correct data
- [ ] PDF export generates successfully
- [ ] Duplicate entry creates correct copy
- [ ] Delete confirmation shows before deletion

---

## Journey 8: Cleanup & Lifecycle

**Goal**: Test destructive actions, project management, and sign-out
**Screens**: EntriesListScreen, ProjectListScreen, SettingsScreen

### Steps

| # | Action | Marionette Command | Verify |
|---|--------|-------------------|--------|
| **Delete an Entry** | | | |
| 8.1 | Go to entries list | Navigate | Entry list |
| 8.2 | Long-press an entry | Long-press gesture | Delete option appears |
| 8.3 | Screenshot delete option | `take_screenshots` | Delete confirmation with entry details |
| 8.4 | Confirm delete | `tap` Delete | Entry removed |
| 8.5 | Screenshot updated list | `take_screenshots` | Entry gone, count reduced |
| **Archive a Project** | | | |
| 8.6 | Go to Projects list | `tap` Projects nav | Project list |
| 8.7 | Tap archive icon on project | `tap` archive toggle | Project archived |
| 8.8 | Screenshot archived project | `take_screenshots` | "Archived" badge visible |
| 8.9 | Verify dashboard reflects no active project | `tap` Dashboard | Empty or changed state |
| 8.10 | Screenshot dashboard after archive | `take_screenshots` | No-project state |
| 8.11 | Un-archive project | `tap` archive toggle again | Project active again |
| 8.12 | Screenshot restored project | `take_screenshots` | Active badge |
| **Edit Project** | | | |
| 8.13 | Tap edit icon on project | `tap` edit | ProjectSetupScreen with data |
| 8.14 | Screenshot pre-filled project | `take_screenshots` | All fields populated |
| 8.15 | Navigate through all 4 tabs | `tap` each tab | Data preserved in all tabs |
| 8.16 | Screenshot each tab | `take_screenshots` x4 | Locations, contractors, pay items all present |
| 8.17 | Delete a location | `tap` delete on a location | Confirmation dialog |
| 8.18 | Screenshot delete location dialog | `take_screenshots` | Confirmation |
| 8.19 | Confirm delete | `tap` | Location removed |
| 8.20 | Navigate back without saving | `tap` back | Back to project list |
| **Project Search** | | | |
| 8.21 | Tap search icon on project list | `tap` | Search bar appears |
| 8.22 | Enter search query "Spring" | `enter_text` | Filtered results |
| 8.23 | Screenshot search results | `take_screenshots` | Matching projects shown |
| 8.24 | Clear search | `tap` close | Full list restored |
| **Delete Project (Two-Step)** | | | |
| 8.25 | Long-press project card | Long-press | Delete option |
| 8.26 | Screenshot first confirmation dialog | `take_screenshots` | Warning with data list |
| 8.27 | Tap confirm in first dialog | `tap` | Second dialog appears |
| 8.28 | Screenshot type-DELETE dialog | `take_screenshots` | Must type "DELETE" |
| 8.29 | Type "DELETE" | `enter_text` "DELETE" | Text entered |
| 8.30 | Confirm final deletion | `tap` | Project deleted |
| 8.31 | Screenshot empty projects list | `take_screenshots` | Project gone |
| **Clear Cache & Sign Out** | | | |
| 8.32 | Go to Settings | `tap` Settings nav | Settings screen |
| 8.33 | Tap "Clear Cached Exports" | `tap` | ClearCacheDialog |
| 8.34 | Confirm clear | `tap` confirm | Cache cleared |
| 8.35 | Tap "Sign Out" | `tap` | SignOutDialog |
| 8.36 | Screenshot sign out dialog | `take_screenshots` | Confirmation |
| 8.37 | Confirm sign out | `tap` | Returns to login (or handles auth bypass) |
| 8.38 | Screenshot final state | `take_screenshots` | Login screen or empty state |

### Cleanup Checks
- [ ] Entry deletion works from list (long-press)
- [ ] Project archive/unarchive toggles correctly
- [ ] Dashboard reflects project state changes
- [ ] Project edit shows all saved data
- [ ] Two-step project deletion works (type DELETE)
- [ ] Project search works
- [ ] Clear cache completes without error
- [ ] Sign out returns to auth screen

---

# Bottom Navigation Bar Tests (Cross-Journey)

Run these checks during any journey:

| # | Check | How |
|---|-------|-----|
| N.1 | Dashboard tab navigates correctly | `tap` Dashboard icon |
| N.2 | Calendar tab navigates correctly | `tap` Calendar icon |
| N.3 | Projects tab navigates correctly | `tap` Projects icon |
| N.4 | Settings tab navigates correctly | `tap` Settings icon |
| N.5 | Active tab is visually highlighted | Screenshot each tab |
| N.6 | Rapid tab switching doesn't crash | Tap all 4 quickly |
| N.7 | Back navigation works from all screens | `tap` back button |

---

# Findings Report Template

After each journey, record findings in this format:

```markdown
## Journey N: [Name] — Findings

**Date**: YYYY-MM-DD
**Status**: PASS / FAIL / PARTIAL

### Bugs (Functional Failures)
| # | Screen | Description | Screenshot | Severity |
|---|--------|-------------|------------|----------|
| B1 | | | | Critical/High/Medium/Low |

### UI Issues (Visual/Layout)
| # | Screen | Description | Screenshot | Severity |
|---|--------|-------------|------------|----------|
| U1 | | | | |

### UX Friction (Usability)
| # | Screen | Description | Screenshot | Suggestion |
|---|--------|-------------|------------|------------|
| X1 | | | | |

### Passed Checks
- [x] Check 1
- [x] Check 2
```

---

# Execution Order

1. Journey 1 (Auth) — establishes session
2. Journey 2 (Project Setup) — creates data foundation
3. Journey 3 (5 Entries) — main workflow, depends on project
4. Journey 4 (Toolbox) — independent features
5. Journey 5 (Settings) — configuration
6. Journey 6 (Browse & Edit) — uses Pass 1 data
7. Journey 7 (Quantities & PDF) — uses Pass 1 data
8. Journey 8 (Cleanup) — destructive, run LAST
