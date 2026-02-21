# 0582B Form Redesign Plan

**Date:** 2026-02-20
**Status:** Approved
**Scope:** Full teardown of current form system (0582B + 1174R), redesign and reimplement 0582B with testability, static preview, and modular architecture.

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Removal scope | Full teardown of both forms | Can't test current system, clean slate |
| Capabilities | All: auto-fill, smart parsing, calculations | Full feature parity with better architecture |
| PDF storage | Asset cloned identically per response | Exact reproduction every time |
| Editing UX | Editable form-shaped Flutter widget | Form IS the editing surface |
| Input method | SmartInputBar — field-aware, slides up on focus | Numeric pad for numbers, date picker for dates, dropdowns for enums |
| Row entry | Row-at-a-time (one row = one test) | Natural unit of work for inspectors |
| Calculations | Live with visual cue (grey/italic) | Immediate feedback, clear distinction from manual entry |
| Preview | On-demand PDF anytime + mandatory before export | Hybrid: Flutter widget for editing, PDF only when needed |
| Form layout (phone) | Reflow to fit (vertical cards) | Usability over visual fidelity; PDF preview shows real layout |
| Testing | Full flow via dart-mcp (happy path + key edges) | Claude runs the tests interactively via MCP tools |
| Modularity | Code-first: each form is a Dart class | Shared utility layer (auto-fill, PDF, input bar, header widgets), form-specific layout/calculations in code |
| Data storage | Generic DB: header_data + response_data JSON columns | form_type field tells Dart which class to use; DB doesn't change per form |
| Entry relationship | Entry preferred, not required | Normal flow anchors to daily entry; standalone possible |
| Auto-save | On navigate away + unsaved changes prompt | Practical, no constant DB writes |
| Auto-fill storage | Snapshot into form response | Self-contained historical record |

---

## Data Model

### form_responses table (restructured)

```sql
id              TEXT PRIMARY KEY    -- UUID
form_type       TEXT NOT NULL       -- "mdot_0582b" (maps to Dart class)
entry_id        TEXT                -- FK → daily_entries (nullable, preferred)
project_id      TEXT NOT NULL       -- FK → projects
header_data     TEXT                -- JSON: auto-filled + manual header fields
                                    --   {project_number, date, inspector, gauge_number, ...}
response_data   TEXT                -- JSON: form-specific body data
                                    --   {test_rows: [...], proctor_rows: [...], weights: {...}}
status          TEXT DEFAULT 'open' -- open | submitted | exported
created_at      TEXT NOT NULL       -- ISO8601
updated_at      TEXT NOT NULL       -- ISO8601
```

### Tables to remove
- `form_field_registry` — replaced by code-first field definitions
- `field_semantic_alias` — not needed with code-first
- `form_field_cache` — not needed
- `calculation_history` — recalculate on the fly

### Tables to keep (simplified)
- `inspector_forms` — stores PDF template bytes for built-in forms (the cloned asset)

---

## Architecture

### Component Overview

```
FormFillScreen (scaffold)
├── AppBar: form name, status, [Preview PDF] [Save] [Export]
│
├── Body: Mdot0582BFormWidget (scrollable, editable, reflowed for phone)
│   ├── FormHeaderSection (shared widget — project, date, inspector, etc.)
│   ├── Weight20_10Section (0582B-specific — 5 weight fields)
│   ├── NuclearGaugeTableSection (test rows — main data entry)
│   │   ├── Row 0 (tappable fields with ValueKeys)
│   │   ├── Row 1 ...
│   │   └── [+ Add Row]
│   ├── ProctorTableSection (verification rows)
│   └── NotesSection
│
└── SmartInputBar (slides up on field focus)
    ├── Field label + unit indicator
    ├── Field-specific input (numpad / date picker / dropdown)
    └── [< Prev] [Next >] [Done]
```

### State Management

```
FormFillScreen
├── listens to: FormResponseProvider (CRUD, save/load)
├── uses: AutoFillService (stateless utility)
├── uses: FormPdfService (generate PDF on demand)
│
└── local state (StatefulWidget):
    ├── activeFieldIndex (which field has focus)
    ├── fieldControllers (Map<String, TextEditingController>)
    ├── testRows (List<Map<String, dynamic>>)
    ├── calculatedValues (Map<String, double>) — live-updated
    └── userEditedFields (Set<String>) — track manual vs auto-fill
```

### Component Responsibilities

| Component | Type | Responsibility |
|-----------|------|----------------|
| `FormResponseProvider` | ChangeNotifier | Load/save/delete responses. List by project/entry. Status management. |
| `AutoFillService` | Stateless utility | Given context (project, entry, inspector, weather) → Map<String, String> of field values |
| `Mdot0582BCalculator` | Stateless utility | Given row values → calculated fields (% compaction, moisture pcf, etc.). Pure functions. |
| `FormPdfService` | Stateless utility | Takes form data + PDF template bytes → filled PDF bytes |

### Shared Widgets (reusable across future forms)

| Widget | Purpose |
|--------|---------|
| `FormHeaderSection` | Project, date, inspector fields — auto-fillable |
| `FormTableSection` | Configurable data table with editable rows, add/delete |
| `SmartInputBar` | Field-aware input strip — adapts per field type |
| `CalculatedFieldCell` | Displays auto-calculated value with grey/italic style |
| `FormFieldCell` | Single tappable/editable cell with ValueKey |

### Form-Specific (0582B only)

| Widget/Class | Purpose |
|--------------|---------|
| `Mdot0582BFormWidget` | The editable form layout — sections, field order, visual structure |
| `Mdot0582BCalculator` | Density/compaction/moisture formulas |
| `Weight20_10Section` | Specialized 5-weight entry widget |

---

## Auto-Fill Flow

```
User opens form (from daily entry or standalone)
  │
  ├── entry exists?
  │   YES → AutoFillService.fill(entry, project, inspector, weather)
  │         → populate header fields, mark as auto-filled (grey text)
  │   NO  → header fields empty, user enters manually
  │
  └── user edits an auto-filled field?
      → remove grey styling, add to userEditedFields
      → future auto-fill calls skip that field
```

## Calculation Flow

```
User enters value in test row field
  │
  → Mdot0582BCalculator.recalculate(rowData)
  → returns {moisture_pcf: 7.7, percent_compaction: 98.5, ...}
  → update calculatedValues map
  → UI rebuilds calculated cells with italic/grey style
```

## Save Flow

```
User navigates away (or taps Save)
  │
  → Collect header_data from controllers
  → Collect test_rows + proctor_rows from local state
  → FormResponseProvider.save(response)
  → Writes to form_responses table as JSON
```

---

## ValueKey Convention (for dart-mcp testability)

```dart
// Header fields
ValueKey('form_field_project_number')
ValueKey('form_field_date')
ValueKey('form_field_inspector')

// Test row fields (indexed)
ValueKey('test_row_0_dry_density')
ValueKey('test_row_0_wet_density')
ValueKey('test_row_0_percent_compaction')

// Actions
ValueKey('add_test_row_button')
ValueKey('preview_pdf_button')
ValueKey('save_button')
ValueKey('export_button')

// Smart input bar
ValueKey('input_bar_next_button')
ValueKey('input_bar_done_button')
ValueKey('input_bar_value_field')
```

---

## Testing Strategy

### Unit Tests (pure Dart)
- `Mdot0582BCalculator` — every formula, edge cases (zero, null, negative)
- `AutoFillService` — given context, correct fields filled
- `FormPdfService` — given data, PDF bytes contain expected values
- `FormResponse` model — JSON serialization round-trip

### Widget Tests (Flutter test framework)
- `SmartInputBar` — shows correct input type per field
- `FormFieldCell` — tap triggers focus, displays value
- `CalculatedFieldCell` — shows italic/grey, updates on value change
- `FormHeaderSection` — renders all header fields, accepts input
- `FormTableSection` — add/delete rows, field navigation

### Integration Tests (dart-mcp — run by Claude)

**Happy path journey:**
1. Launch app via dart-mcp
2. Navigate to forms list
3. Tap "New 0582B"
4. Verify header auto-filled (if from entry)
5. Tap test_row_0_dry_density → verify input bar appears
6. Enter "128.5" → tap Next
7. Enter "136.2" (wet density) → tap Next
8. Enter "130.0" (max density)
9. Verify test_row_0_percent_compaction shows calculated value
10. Tap add_test_row_button → verify row 1 appears
11. Tap save_button
12. Navigate away → navigate back → verify data persisted
13. Tap preview_pdf_button → verify PDF preview screen opens
14. Tap export_button → verify status = exported

**Key edge cases:**
- Empty form save
- Missing required fields on export attempt
- Add row then delete row
- Navigate away with unsaved changes → prompt appears
- Auto-fill from daily entry vs standalone form
- Calculate with missing dependent fields (graceful null handling)

---

## Implementation Phases

### Phase 1: Teardown
**Goal:** Remove all current form code cleanly.

Remove:
- All files under `lib/features/toolbox/` related to forms (screens, widgets, services, providers, models, datasources)
- Form JSON definitions: `assets/data/forms/mdot_0582b_density.json`, `assets/data/forms/mdot_1174r_concrete.json`
- PDF templates: `assets/templates/forms/mdot_0582b_density.pdf`, `assets/templates/forms/mdot_1174r_concrete.pdf`
- DB tables: `form_field_registry`, `field_semantic_alias`, `form_field_cache`, `calculation_history`
- Router entries for form screens
- Provider registrations in `main.dart`
- All imports/references across codebase

Keep:
- `inspector_forms` table (simplified)
- `form_responses` table (will restructure in Phase 2)
- Non-form toolbox features (calculator, gallery, todos)

**Verify:** App builds and runs. Forms list shows empty state or is hidden.

---

### Phase 2: Data Layer
**Goal:** New data foundation for form responses.

Build:
- Restructured `form_responses` table (form_type, header_data, response_data)
- `FormResponse` model with typed JSON parsing
- `FormResponseRepository` + `FormResponseLocalDatasource`
- `FormResponseProvider` (ChangeNotifier — CRUD, list by project/entry)
- `Mdot0582BCalculator` — pure functions for all density calculations
- `AutoFillService` — stateless, reads from existing project/entry/inspector/weather providers

**Verify:** Unit tests for calculator formulas and auto-fill context mapping.

---

### Phase 3: Shared Widgets
**Goal:** Reusable form UI components.

Build:
- `FormFieldCell` — tappable editable cell with ValueKey
- `CalculatedFieldCell` — grey/italic display, live-updating
- `FormHeaderSection` — project, date, inspector fields (auto-fillable)
- `FormTableSection` — configurable table with add/delete rows
- `SmartInputBar` — field-aware input strip (numeric, date, dropdown, text), slides up on focus

All widgets get ValueKeys per naming convention.

**Verify:** Widget tests for each component. Launch via dart-mcp, verify widgets render.

---

### Phase 4: 0582B Form Screen
**Goal:** The main form editing experience.

Build:
- `Mdot0582BFormWidget` — editable form layout (reflowed for phone)
- `FormFillScreen` — scaffold, app bar, save/navigate-away logic
- Wire: field focus → SmartInputBar, value change → calculator, auto-fill on open
- Route registration, forms list entry point
- Store 0582B PDF template as cloned asset

**Verify:** dart-mcp full journey — open, fill header, enter test row, verify calculation, save, reload, data persists.

---

### Phase 5: PDF Preview + Export
**Goal:** On-demand PDF preview and export flow.

Build:
- `FormPdfService` — fill PDF template with form data → bytes
- Preview screen (tap Preview → generate → display in viewer)
- Export flow: Preview → Confirm → Save/Share
- Mandatory preview before export
- Status transitions (open → submitted → exported)

**Verify:** dart-mcp — fill form, tap Preview, verify screen opens, tap Export, verify status. Unit test PDF field filling.

---

### Phase 6: Polish + Edge Cases
**Goal:** Robust handling of real-world scenarios.

Build:
- Unsaved changes prompt on navigate away
- Empty form save handling
- Required fields warning on export
- Add row / delete row
- Auto-fill from daily entry vs standalone
- Graceful calculation with missing fields

**Verify:** dart-mcp edge case test runs.

---

## Agent Assignments

| Phase | Primary Agent | Support |
|-------|--------------|---------|
| Phase 1: Teardown | frontend-flutter-specialist | — |
| Phase 2: Data Layer | backend-data-layer-agent | — |
| Phase 3: Shared Widgets | frontend-flutter-specialist | interface-design skill |
| Phase 4: 0582B Form Screen | frontend-flutter-specialist | backend-data-layer-agent |
| Phase 5: PDF Preview + Export | pdf-agent | frontend-flutter-specialist |
| Phase 6: Polish + Edge Cases | frontend-flutter-specialist | qa-testing-agent |
| All phases: Testing | qa-testing-agent (dart-mcp) | — |
