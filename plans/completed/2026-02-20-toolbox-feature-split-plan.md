# Toolbox Feature Split Plan

**Date**: 2026-02-20
**Catalog Source**: `.claude/code-reviews/2026-02-20-master-refactor-catalog.md`
**Scope**: Split `lib/features/toolbox/` (76 files, 7 sub-features) into independent feature directories

---

## Context & Key Findings

The toolbox feature is a UI hub containing 7 independent sub-features. Organic growth means every new form type, calculator mode, or gallery filter lands in the same 76-file directory. This plan extracts Calculator, Todos, Gallery, and Forms into their own feature directories.

**No overlap with existing plans:**
- Entries plan — covers `lib/features/entries/` only (E-01→E-18)
- PDF pipeline plan — covers `lib/features/pdf/` only (P-01→P-13)
- 0582B form redesign — handles FormFillScreen teardown + rebuild. This plan defines `lib/features/forms/` as the landing target for that work.

**Key discoveries from context gather:**
- Routes are **already root-level** (`/calculator`, `/todos`, `/gallery`, `/forms` exist in router) — no route path changes needed
- 0582B partial implementation already deleted old-system services (`auto_fill_engine`, `density_calculator_service`, `form_parsing_service`, `form_calculation_service`, `auto_fill_context_builder`)
- `form_field_registry_local_datasource.dart` has **zero references** — dead code, delete in Phase 4
- `DensityCalculatorService` has zero references — dead code, delete in Phase 1

**Target outcome**: `lib/features/toolbox/` shrinks from 76 files to ~3 (home screen + barrel).

---

## Phase 0: Already Complete

Routes are already root-level in `app_router.dart`. No router path changes needed in this plan — only import updates per phase.

---

## Phase 1: Calculator Extraction

**Goal**: Move calculator sub-feature to `lib/features/calculator/`.

### Files to Move

| From (`lib/features/toolbox/`) | To (`lib/features/calculator/`) |
|---|---|
| `data/services/calculator_service.dart` | `data/services/calculator_service.dart` |
| `data/datasources/local/calculation_history_local_datasource.dart` | `data/datasources/local/calculation_history_local_datasource.dart` |
| `data/datasources/remote/calculation_history_remote_datasource.dart` | `data/datasources/remote/calculation_history_remote_datasource.dart` |
| `data/models/calculation_history.dart` | `data/models/calculation_history.dart` |
| `presentation/providers/calculator_provider.dart` | `presentation/providers/calculator_provider.dart` |
| `presentation/screens/calculator_screen.dart` | `presentation/screens/calculator_screen.dart` |

### Files to Delete

| File | Reason |
|---|---|
| `data/services/density_calculator_service.dart` | Zero references — dead code (confirmed by prunekit) |

### New Directory Structure

```
lib/features/calculator/
├── calculator.dart                          ← barrel export
├── data/
│   ├── datasources/
│   │   ├── local/calculation_history_local_datasource.dart
│   │   └── remote/calculation_history_remote_datasource.dart
│   ├── models/
│   │   └── calculation_history.dart
│   └── services/
│       └── calculator_service.dart
└── presentation/
    ├── providers/
    │   └── calculator_provider.dart
    └── screens/
        └── calculator_screen.dart
```

### main.dart Changes

Update import paths:
```dart
// Before
import 'package:construction_inspector/features/toolbox/data/datasources/local/calculation_history_local_datasource.dart';
import 'package:construction_inspector/features/toolbox/presentation/providers/calculator_provider.dart';

// After
import 'package:construction_inspector/features/calculator/calculator.dart';
```

### Router Changes

Update single import in `app_router.dart`:
```dart
// Before
import 'package:construction_inspector/features/toolbox/toolbox.dart';

// After — add alongside existing toolbox import (remove once all phases done)
import 'package:construction_inspector/features/calculator/calculator.dart';
```

### Barrel Export (`calculator.dart`)

```dart
export 'data/datasources/local/calculation_history_local_datasource.dart';
export 'data/datasources/remote/calculation_history_remote_datasource.dart';
export 'data/models/calculation_history.dart';
export 'data/services/calculator_service.dart';
export 'presentation/providers/calculator_provider.dart';
export 'presentation/screens/calculator_screen.dart';
```

### Testing

**dart-mcp smoke test**:
1. Launch app
2. Navigate to toolbox home
3. Tap Calculator tile → verify `CalculatorScreen` renders
4. Perform a simple calculation → verify result displays
5. Check history tab → verify calculation_history_local_datasource loads correctly

**Widget test harness stub**: `test/features/calculator/presentation/screens/calculator_screen_test.dart`
```dart
// Harness: wrap CalculatorScreen in minimal provider scaffold
// Verify: HMA and Concrete tabs render, result card appears on calculation
```

### Verification Criteria
- [ ] `flutter analyze` passes with zero new warnings
- [ ] App builds and calculator is accessible from toolbox home
- [ ] Calculation history persists across navigations
- [ ] No remaining `toolbox/` imports in calculator files

---

## Phase 2: Todos Extraction

**Goal**: Move todos sub-feature to `lib/features/todos/`.

### Files to Move

| From (`lib/features/toolbox/`) | To (`lib/features/todos/`) |
|---|---|
| `data/datasources/local/todo_item_local_datasource.dart` | `data/datasources/local/todo_item_local_datasource.dart` |
| `data/datasources/remote/todo_item_remote_datasource.dart` | `data/datasources/remote/todo_item_remote_datasource.dart` |
| `data/models/todo_item.dart` | `data/models/todo_item.dart` |
| `presentation/providers/todo_provider.dart` | `presentation/providers/todo_provider.dart` |
| `presentation/screens/todos_screen.dart` | `presentation/screens/todos_screen.dart` |

### New Directory Structure

```
lib/features/todos/
├── todos.dart                               ← barrel export
├── data/
│   ├── datasources/
│   │   ├── local/todo_item_local_datasource.dart
│   │   └── remote/todo_item_remote_datasource.dart
│   └── models/
│       └── todo_item.dart
└── presentation/
    ├── providers/
    │   └── todo_provider.dart
    └── screens/
        └── todos_screen.dart
```

### main.dart Changes

Update import paths for `todo_item_local_datasource`, `todo_item_remote_datasource`, and `todo_provider` to use `lib/features/todos/todos.dart` barrel.

Note: `TodoProvider` is constructed with `TodoItemDatasource` + `syncService` — constructor signature unchanged, just import path updates.

### Testing

**dart-mcp smoke test**:
1. Navigate to toolbox home
2. Tap Todos tile → verify `TodosScreen` renders
3. Add a todo item → verify it appears in list
4. Mark todo complete → verify state updates
5. Navigate away and back → verify persistence

**Widget test harness stub**: `test/features/todos/presentation/screens/todos_screen_test.dart`

### Verification Criteria
- [ ] `flutter analyze` passes
- [ ] Todo items sync correctly (remote datasource still wired to SyncService)
- [ ] No remaining `toolbox/` imports in todos files

---

## Phase 3: Gallery Extraction

**Goal**: Move gallery sub-feature to `lib/features/gallery/`.

### Files to Move

| From (`lib/features/toolbox/`) | To (`lib/features/gallery/`) |
|---|---|
| `presentation/providers/gallery_provider.dart` | `presentation/providers/gallery_provider.dart` |
| `presentation/screens/gallery_screen.dart` | `presentation/screens/gallery_screen.dart` |

### Cross-Feature Dependencies

`GalleryProvider` depends on `photoRepository` and `dailyEntryRepository` — both injected via `main.dart` constructor. No change to dependency wiring needed; only import paths update.

### New Directory Structure

```
lib/features/gallery/
├── gallery.dart                             ← barrel export
└── presentation/
    ├── providers/
    │   └── gallery_provider.dart
    └── screens/
        └── gallery_screen.dart
```

Note: Gallery has no data layer of its own — it reads from `lib/features/photos/` and `lib/features/entries/` repositories. This is intentional: gallery is a presentation-only view over existing data.

### Testing

**dart-mcp smoke test**:
1. Navigate to toolbox home
2. Tap Gallery tile → verify `GalleryScreen` renders
3. Verify photos load (if any exist in test project)
4. Tap a photo → verify viewer opens

**Widget test harness stub**: `test/features/gallery/presentation/screens/gallery_screen_test.dart`

### Verification Criteria
- [ ] `flutter analyze` passes
- [ ] Photos display correctly (cross-feature dependency intact)
- [ ] Filter sheet opens and functions
- [ ] No remaining `toolbox/` imports in gallery files

---

## Phase 4: Forms Migration to `lib/features/forms/`

**Goal**: Define `lib/features/forms/` as the permanent home for all form code. Move all remaining form-related files out of toolbox. After this phase, `lib/features/toolbox/` contains only the home screen.

**Dependency**: 0582B form redesign should be at a stable checkpoint before executing this phase (form_fill_screen.dart uncommitted changes resolved).

### Pre-Migration Audit

Before moving, run prunekit and check for zero-reference files. Confirmed dead code to delete (do NOT migrate):

| File | Reason |
|---|---|
| `data/datasources/local/form_field_registry_local_datasource.dart` | Zero references — old form system, superseded by 0582B |
| Any `auto_fill_result.dart`, `template_validation_result.dart`, `form_field_entry.dart` still with zero refs | Verify via prunekit before deleting |

### Files to Move

**Data layer:**

| From (`lib/features/toolbox/`) | To (`lib/features/forms/`) |
|---|---|
| `data/datasources/local/form_response_local_datasource.dart` | `data/datasources/local/form_response_local_datasource.dart` |
| `data/datasources/local/inspector_form_local_datasource.dart` | `data/datasources/local/inspector_form_local_datasource.dart` |
| `data/datasources/remote/form_response_remote_datasource.dart` | `data/datasources/remote/form_response_remote_datasource.dart` |
| `data/datasources/remote/inspector_form_remote_datasource.dart` | `data/datasources/remote/inspector_form_remote_datasource.dart` |
| `data/models/form_response.dart` | `data/models/form_response.dart` |
| `data/models/inspector_form.dart` | `data/models/inspector_form.dart` |
| `data/repositories/form_response_repository.dart` | `data/repositories/form_response_repository.dart` |
| `data/repositories/inspector_form_repository.dart` | `data/repositories/inspector_form_repository.dart` |
| `data/services/auto_fill_service.dart` | `data/services/auto_fill_service.dart` |
| `data/services/form_pdf_service.dart` | `data/services/form_pdf_service.dart` |
| `data/services/form_state_hasher.dart` | `data/services/form_state_hasher.dart` |
| `data/services/mdot_0582b_calculator.dart` | `data/services/mdot_0582b_calculator.dart` |

**Presentation layer:**

| From (`lib/features/toolbox/`) | To (`lib/features/forms/`) |
|---|---|
| `presentation/providers/inspector_form_provider.dart` | `presentation/providers/inspector_form_provider.dart` |
| `presentation/screens/form_fill_screen.dart` | `presentation/screens/form_fill_screen.dart` |
| `presentation/screens/forms_list_screen.dart` | `presentation/screens/forms_list_screen.dart` |
| `presentation/utils/field_icon_utils.dart` | `presentation/utils/field_icon_utils.dart` |
| `presentation/widgets/auto_fill_indicator.dart` | `presentation/widgets/auto_fill_indicator.dart` |
| `presentation/widgets/calculated_field_cell.dart` | `presentation/widgets/calculated_field_cell.dart` |
| `presentation/widgets/density_grouped_entry_section.dart` | `presentation/widgets/density_grouped_entry_section.dart` |
| `presentation/widgets/dynamic_form_field.dart` | `presentation/widgets/dynamic_form_field.dart` |
| `presentation/widgets/form_field_cell.dart` | `presentation/widgets/form_field_cell.dart` |
| `presentation/widgets/form_fields_config.dart` | `presentation/widgets/form_fields_config.dart` |
| `presentation/widgets/form_fields_tab.dart` | `presentation/widgets/form_fields_tab.dart` |
| `presentation/widgets/form_header_section.dart` | `presentation/widgets/form_header_section.dart` |
| `presentation/widgets/form_preview_tab.dart` | `presentation/widgets/form_preview_tab.dart` |
| `presentation/widgets/form_status_card.dart` | `presentation/widgets/form_status_card.dart` |
| `presentation/widgets/form_table_section.dart` | `presentation/widgets/form_table_section.dart` |
| `presentation/widgets/form_test_history_card.dart` | `presentation/widgets/form_test_history_card.dart` |
| `presentation/widgets/form_thumbnail.dart` | `presentation/widgets/form_thumbnail.dart` |
| `presentation/widgets/mdot_0582b_form_widget.dart` | `presentation/widgets/mdot_0582b_form_widget.dart` |
| `presentation/widgets/parsing_preview.dart` | `presentation/widgets/parsing_preview.dart` |
| `presentation/widgets/quick_entry_section.dart` | `presentation/widgets/quick_entry_section.dart` |
| `presentation/widgets/smart_input_bar.dart` | `presentation/widgets/smart_input_bar.dart` |
| `presentation/widgets/table_rows_section.dart` | `presentation/widgets/table_rows_section.dart` |
| `presentation/widgets/weight_20_10_section.dart` | `presentation/widgets/weight_20_10_section.dart` |

### New Directory Structure

```
lib/features/forms/
├── forms.dart                               ← barrel export
├── data/
│   ├── datasources/
│   │   ├── local/
│   │   │   ├── form_response_local_datasource.dart
│   │   │   └── inspector_form_local_datasource.dart
│   │   └── remote/
│   │       ├── form_response_remote_datasource.dart
│   │       └── inspector_form_remote_datasource.dart
│   ├── models/
│   │   ├── form_response.dart
│   │   └── inspector_form.dart
│   ├── repositories/
│   │   ├── form_response_repository.dart
│   │   └── inspector_form_repository.dart
│   └── services/
│       ├── auto_fill_service.dart
│       ├── form_pdf_service.dart
│       ├── form_state_hasher.dart
│       └── mdot_0582b_calculator.dart
└── presentation/
    ├── providers/
    │   └── inspector_form_provider.dart
    ├── screens/
    │   ├── form_fill_screen.dart
    │   └── forms_list_screen.dart
    ├── utils/
    │   └── field_icon_utils.dart
    └── widgets/
        ├── auto_fill_indicator.dart
        ├── calculated_field_cell.dart
        ├── form_field_cell.dart
        ├── form_header_section.dart
        ├── form_table_section.dart
        ├── mdot_0582b_form_widget.dart
        ├── smart_input_bar.dart
        ├── weight_20_10_section.dart
        └── [remaining widgets...]
```

### main.dart Changes

Consolidate all form-related imports to `lib/features/forms/forms.dart` barrel. Remove all `toolbox/` imports for form code. After this phase, `main.dart` should import from `toolbox/` only for `ToolboxHomeScreen`.

### Toolbox Shell After Phase 4

`lib/features/toolbox/` reduces to:
```
lib/features/toolbox/
├── toolbox.dart                             ← barrel (exports ToolboxHomeScreen only)
└── presentation/
    └── screens/
        └── toolbox_home_screen.dart
```

### Cross-Feature Impact

`lib/features/entries/` references `FormResponse` and navigates to `/forms` — these are cross-feature dependencies via import paths. Update any direct `toolbox/` imports in entries to use `forms/` barrel.

### Testing

**dart-mcp smoke test**:
1. Navigate to toolbox home
2. Tap Forms tile → verify `FormsListScreen` renders
3. Tap an existing form response → verify `FormFillScreen` opens
4. Verify SmartInputBar appears on field tap
5. Verify calculated fields update on value entry

**Widget test harnesses** (per 0582B plan ValueKey convention):
- `form_field_cell_test.dart` — tap triggers focus, displays value
- `smart_input_bar_test.dart` — shows correct input type per field
- `form_table_section_test.dart` — add/delete rows
- `form_header_section_test.dart` — renders all header fields

### Verification Criteria
- [ ] `flutter analyze` passes
- [ ] `lib/features/toolbox/` contains only `toolbox_home_screen.dart` + barrel
- [ ] No `toolbox/` imports anywhere except in `toolbox_home_screen.dart` itself
- [ ] Full 0582B dart-mcp journey passes (from 0582B plan: open → fill header → enter row → verify calculation → save → reload → persist → preview → export)
- [ ] `form_field_registry_local_datasource.dart` deleted

---

## File Count Impact

| Feature | Before (in toolbox) | After (own directory) |
|---|---|---|
| Calculator | 6 files | `lib/features/calculator/` — 6 files |
| Todos | 5 files | `lib/features/todos/` — 5 files |
| Gallery | 2 files | `lib/features/gallery/` — 2 files |
| Forms | ~40 files | `lib/features/forms/` — ~39 files (1 deleted) |
| Toolbox | 76 files | 3 files (home screen + barrel + data barrel) |

---

## Agent Assignments

| Phase | Agent | Notes |
|---|---|---|
| Phase 1: Calculator | `frontend-flutter-specialist-agent` | Zero deps — safe solo extraction |
| Phase 2: Todos | `frontend-flutter-specialist-agent` | Zero deps — safe solo extraction |
| Phase 3: Gallery | `frontend-flutter-specialist-agent` | Photo dep injected — no data layer changes |
| Phase 4: Forms | `frontend-flutter-specialist-agent` + `backend-data-layer-agent` | Large move — run prunekit first, coordinate on dead code audit |
| All phases: Testing | `qa-testing-agent` (dart-mcp) | Smoke test after each phase before proceeding |

**Parallel execution note**: Phases 1, 2, and 3 have zero inter-dependencies — they CAN be executed in parallel by 3 agents using the dispatching-parallel-agents skill. Phase 4 must run after Phases 1–3 complete (to finalize the toolbox barrel).

---

## Execution Order

```
Phase 1 (Calculator) ─┐
Phase 2 (Todos)       ├─► All three can run in parallel ─► Phase 4 (Forms)
Phase 3 (Gallery)    ─┘
```

After all phases:
- `lib/features/toolbox/` = launcher shell only
- Each sub-feature owns its full stack independently
- Future additions (new calculator modes, new form types, gallery filters) land in the correct feature directory
