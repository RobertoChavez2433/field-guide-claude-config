# Toolbox PRD

## Purpose
Toolbox is a navigation hub that gives inspectors quick access to four independent utility features: Forms, Calculator, Gallery, and Todos. It replaces the clipboard, calculator, and sticky notes that inspectors traditionally carry. The toolbox itself is a lightweight shell -- all business logic, data, and screens live in the individual features it delegates to.

## Architecture
Toolbox is **not** a full feature with data/domain layers. It consists of exactly two files:
- `lib/features/toolbox/toolbox.dart` -- barrel export
- `lib/features/toolbox/presentation/screens/toolbox_home_screen.dart` -- a 2x2 grid of navigation tiles

Each tile pushes a named route (`forms`, `calculator`, `gallery`, `todos`) via go_router. The four target features are fully independent modules under `lib/features/`.

## Sub-Features

### Forms (`lib/features/forms/`, ~30 files)
Fill PDF-based inspection forms (e.g., MDOT 0582B) with smart text parsing, field auto-fill from project context, and carry-forward of last-used values. Import custom PDF templates with automatic field discovery. Includes specialized entry screens for Proctor, Quick Test, and Weights data. Supports PDF preview and export.

### Calculator (`lib/features/calculator/`, 7 files)
Construction calculators for HMA tonnage, concrete cubic yards, area (SF), volume (CF), linear (LF), and density. Append-only calculation history with optional notes and project/entry linkage.

### Gallery (`lib/features/gallery/`, 3 files)
Photo gallery viewer with date-range filtering (today, this week, this month, custom), entry-based filtering, and sorting. Presentation-only feature that reads from the `photos` feature's repository -- no data layer of its own.

### Todos (`lib/features/todos/`, 6 files)
Project-scoped and entry-scoped task tracking with priority levels (low/normal/high), due dates, completion status, and overdue detection. Tasks can be created standalone or linked to a daily entry.

## Data Model
Tables are defined in `lib/core/database/schema/toolbox_tables.dart` but are logically owned by their respective features:

| Table | Owning Feature | Purpose |
|-------|---------------|---------|
| `inspector_forms` | forms | Form templates with field definitions, parsing config, template bytes |
| `form_responses` | forms | Filled form data with JSON response_data, status, entry/project linkage |
| `todo_items` | todos | Tasks with priority, due_date, is_completed, project/entry linkage |
| `calculation_history` | calculator | Append-only calculation records with calc_type, input/result JSON |

Gallery has no tables -- it reads from the `photos` table owned by the photos feature.

Sync: forms, todos, and calculator all have remote datasources for cloud sync.

## User Flow
1. Inspector taps the Toolbox icon in the bottom navigation bar.
2. `ToolboxHomeScreen` displays a 2x2 grid with four tiles: Forms, Calculator, Gallery, and To-Do's.
3. Tapping a tile pushes the corresponding named route, navigating into that feature's own screen stack.
4. Each feature manages its own navigation, state, and data independently -- the toolbox has no further involvement after the initial push.

## Offline Behavior
Each sub-feature is fully functional offline. Form templates, responses, todos, and calculations are stored locally in SQLite. PDF template bytes are cached as BLOBs in `inspector_forms` for offline rendering. All changes queue for sync when connectivity returns. The toolbox hub itself has no offline concerns (it is stateless).

## Dependencies
- **Toolbox hub**: `go_router` (navigation), `AppTheme` (styling), `TestingKeys` (testability)
- **Forms**: projects, entries (scoping/linkage), pdf (rendering), `syncfusion_flutter_pdf`, `syncfusion_flutter_pdfviewer`
- **Calculator**: projects, entries (optional linkage), `uuid`
- **Gallery**: photos (photo data), entries (entry filter), no own data dependencies
- **Todos**: projects, entries (scoping/linkage), `uuid`

## Owner Agent
frontend-flutter-specialist-agent (toolbox hub screen), backend-data-layer-agent + frontend-flutter-specialist-agent (sub-features)
