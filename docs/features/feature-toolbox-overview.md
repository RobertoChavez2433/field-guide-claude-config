---
feature: toolbox
type: overview
scope: Inspector Forms, Calculations, Todos, and Media Gallery
updated: 2026-02-13
---

# Toolbox Feature Overview

## Purpose

The Toolbox feature provides construction inspectors with a suite of productivity tools including inspector forms (dynamic questionnaires), calculation utilities (density calculations, material estimates), todo list management, and photo gallery. These tools enable specialized workflows not covered by daily entries, such as material testing, equipment diagnostics, and custom field documentation.

## Key Responsibilities

- **Inspector Forms**: Create and fill dynamic forms with field validation and auto-fill logic
- **Form Parsing**: Parse form templates, discover fields, and extract responses
- **Form Calculations**: Auto-calculate derived fields based on user input (e.g., density from weight/volume)
- **Material Calculator**: Density, tonnage, and material estimate calculations
- **Todo Management**: Create, track, and complete todo items with priority and due dates
- **Photo Gallery**: Browse all project photos with filtering and tagging
- **Calculation History**: Persist calculation results for reference
- **Field Mapping**: Manage semantic field aliases for form field discovery

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/toolbox/data/models/inspector_form.dart` | Inspector form model |
| `lib/features/toolbox/data/models/form_response.dart` | Form submission and response data |
| `lib/features/toolbox/data/models/todo_item.dart` | Todo item model |
| `lib/features/toolbox/data/models/calculation_history.dart` | Calculation result history |
| `lib/features/toolbox/data/services/form_parsing_service.dart` | Form field discovery and parsing |
| `lib/features/toolbox/data/services/calculator_service.dart` | Calculation engine |
| `lib/features/toolbox/presentation/screens/toolbox_home_screen.dart` | Toolbox hub |
| `lib/features/toolbox/presentation/screens/forms_list_screen.dart` | Form listing and selection |
| `lib/features/toolbox/presentation/screens/form_fill_screen.dart` | Form filling UI |
| `lib/features/toolbox/presentation/screens/calculator_screen.dart` | Calculator UI |
| `lib/features/toolbox/presentation/screens/gallery_screen.dart` | Photo gallery |

## Data Sources

- **SQLite**: Persists inspector forms, form responses, todos, calculation history
- **Photos**: Gallery displays photos from `photos` feature
- **Form Templates**: JSON/YAML form definitions (bundled or downloaded)
- **Calculation Services**: Built-in calculators for density, material estimates

## Integration Points

**Depends on:**
- `core/database` - SQLite schema for forms, responses, todos, calculations
- `photos` - Photo gallery references
- `entries` - Forms linked to entries (optional)
- `projects` - Forms scoped to projects

**Required by:**
- `entries` - Entry detail may reference form responses
- `dashboard` - Pending forms or todos displayed
- All features - Toolbox accessible from main menu

## Offline Behavior

Toolbox is **fully offline-capable**. Form creation, filling, calculation, todo management, and gallery browsing occur entirely offline. All data persists in SQLite. Cloud sync handles async push of form responses. Inspectors can use all toolbox features entirely offline; sync happens during dedicated sync operations.

## Edge Cases & Limitations

- **Dynamic Fields**: Form field discovery relies on semantic aliases; new field types require manual mapping
- **Complex Calculations**: Density and tonnage calculations assume standard material properties (no custom material database)
- **Form Versioning**: No form version tracking; form updates overwrite previous versions
- **Todo Recurrence**: No recurring todos; manual creation required for repeated tasks
- **Gallery Performance**: Large galleries (1000+ photos) may load slowly; pagination recommended
- **Calculation Precision**: Floating-point calculations may have rounding errors (display to 2 decimals)

## Detailed Specifications

See `architecture-decisions/toolbox-constraints.md` for:
- Hard rules on form field discovery and semantic mapping
- Calculator precision requirements and material assumptions
- Todo lifecycle and completion semantics

See `rules/database/schema-patterns.md` for:
- SQLite schema for forms, responses, todos, calculations
- Indexing for efficient form/todo queries

