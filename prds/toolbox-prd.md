# Toolbox PRD

## Purpose
Toolbox is the inspector's multi-tool -- a collection of utilities that reduce manual paperwork and field calculations. It bundles form filling, task management, construction calculators, and a photo gallery into a single feature, replacing the clipboard, calculator, and sticky notes that inspectors traditionally carry.

## Core Capabilities
- **Inspector Forms**: Fill PDF-based inspection forms (e.g., MDOT 0582B) with smart text parsing, field auto-fill from project context, and carry-forward of last-used values. Import custom PDF templates with automatic field discovery.
- **Todo Lists**: Project-scoped and entry-scoped task tracking with priority levels (low/normal/high), due dates, completion status, and overdue detection.
- **Construction Calculator**: HMA tonnage, concrete cubic yards, area (SF), volume (CF), and linear (LF) calculations with append-only history and notes. Density calculator for material testing.
- **Photo Gallery**: Browse and manage project photos with metadata.
- **Form Field Registry**: Single source of truth mapping PDF field names to semantic names, enabling auto-fill across different form templates. Supports field aliases for cross-form compatibility.

## Data Model
- Primary entities (7 SQLite tables):
  - `inspector_forms`: Form templates with field definitions, parsing keywords, table row config, template bytes
  - `form_responses`: Filled form data with JSON response_data, status (open/complete), linked to entry and project
  - `todo_items`: Tasks with priority, due_date, is_completed, project/entry linkage
  - `calculation_history`: Append-only calculation records with calc_type, input_data (JSON), result_data (JSON)
  - `form_field_registry`: Field definitions with semantic_name, pdf_field_name, auto_fill_source, category, sort_order
  - `field_semantic_aliases`: Maps alias strings to canonical semantic_name for cross-form field matching
  - `form_field_cache`: Stores last-used values per project/semantic_name for carry-forward auto-fill
- Sync: Sync to Cloud (forms, responses, todos, calculation history all have remote datasources)

## User Flow
Inspectors access the Toolbox from the bottom navigation bar. The home screen shows quick-access tiles: Forms, Todos, Calculator, and Gallery. For forms, inspectors select a template, fill fields (auto-populated where possible), preview the rendered PDF, and save. Todos can be created from the todo screen or inline from a daily entry. Calculator results can be optionally linked to an entry or project.

## Offline Behavior
Fully functional offline. All form templates, responses, todos, and calculations are stored locally in SQLite. PDF template bytes are cached in the `inspector_forms` table for offline rendering. Form auto-fill pulls from the local `form_field_cache`. Imported PDF templates are stored as BLOBs. All changes queue for sync when connectivity returns.

## Dependencies
- Features: projects (form/todo/calc scoping), entries (form response and todo linkage), photos (gallery), pdf (form PDF rendering)
- Packages: `uuid`, `sqflite`, `provider`, `syncfusion_flutter_pdf` (form PDF generation), `syncfusion_flutter_pdfviewer` (template preview)

## Owner Agent
backend-data-layer-agent (models, repositories, services), frontend-flutter-specialist-agent (screens, widgets, providers)
