# Dependency Graph

## Design System Barrel — Who Imports It

`lib/core/design_system/design_system.dart` is the barrel file exporting all 25 components.

### Direct importers (production)
| File | Feature |
|------|---------|
| `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` | dashboard |
| `lib/features/entries/presentation/screens/drafts_list_screen.dart` | entries |
| `lib/features/entries/presentation/screens/entries_list_screen.dart` | entries |
| `lib/features/gallery/presentation/screens/gallery_screen.dart` | gallery |
| `lib/features/quantities/presentation/screens/quantities_screen.dart` | quantities |
| `lib/features/settings/presentation/screens/trash_screen.dart` | settings |
| `lib/features/todos/presentation/screens/todos_screen.dart` | todos |

### NOT importing design_system.dart (but should, based on spec)
All other presentation screens using raw `AlertDialog`, `showDialog`, `showModalBottomSheet`, `TextStyle(`, or `Scaffold(` directly.

## Dashboard Screen — What It Imports

`lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` imports:
- `lib/core/theme/app_theme.dart` — Still using `AppTheme.getPrimaryGradient()`
- `lib/core/theme/design_constants.dart` — DesignConstants tokens
- `lib/core/theme/field_guide_colors.dart` — FieldGuideColors extension
- `lib/core/design_system/design_system.dart` — Barrel (but uses almost nothing from it)
- `lib/features/dashboard/presentation/widgets/widgets.dart` — Dashboard widget barrel
- 7 provider imports (project, entry, location, bid_item, entry_quantity, contractor)

## Confirmation Dialog — Import Chain

`lib/shared/widgets/confirmation_dialog.dart` imports:
- `lib/shared/shared.dart` (re-exports testing keys, etc.)

Imported by: Transitively via `shared.dart` → used throughout the app. Extremely high blast radius.

## Modal Bottom Sheet Files (8 production)

| File | Feature |
|------|---------|
| `lib/features/projects/presentation/screens/project_list_screen.dart` | projects |
| `lib/features/entries/presentation/screens/home_screen.dart` | entries |
| `lib/features/settings/presentation/screens/admin_dashboard_screen.dart` | settings |
| `lib/features/quantities/presentation/widgets/bid_item_detail_sheet.dart` | quantities |
| `lib/features/projects/presentation/widgets/project_switcher.dart` | projects |
| `lib/features/pdf/presentation/widgets/extraction_banner.dart` | pdf |
| `lib/features/gallery/presentation/screens/gallery_screen.dart` | gallery |
| `lib/features/forms/presentation/screens/form_gallery_screen.dart` | forms |

## showDialog Files (19 production)

| File | Count |
|------|-------|
| `lib/features/todos/presentation/screens/todos_screen.dart` | 4 |
| `lib/features/entries/presentation/widgets/contractor_editor_widget.dart` | 2 |
| `lib/features/settings/presentation/widgets/sign_out_dialog.dart` | 1 |
| `lib/features/settings/presentation/widgets/clear_cache_dialog.dart` | 1 |
| `lib/features/calculator/presentation/screens/calculator_screen.dart` | 1 |
| `lib/features/pdf/presentation/helpers/pdf_import_helper.dart` | 1 |
| `lib/features/pdf/presentation/helpers/mp_import_helper.dart` | 1 |
| `lib/features/projects/presentation/widgets/bid_item_dialog.dart` | 1 |
| `lib/features/projects/presentation/widgets/add_location_dialog.dart` | 1 |
| `lib/features/projects/presentation/widgets/add_equipment_dialog.dart` | 1 |
| `lib/features/projects/presentation/widgets/add_contractor_dialog.dart` | 1 |
| `lib/features/entries/presentation/screens/entries_list_screen.dart` | 1 |
| `lib/features/entries/presentation/screens/home_screen.dart` | 1 |
| `lib/features/entries/presentation/screens/report_widgets/report_debug_pdf_actions_dialog.dart` | 1 |
| `lib/features/entries/presentation/screens/report_widgets/report_pdf_actions_dialog.dart` | 1 |

## Data Flow Diagram

```
design_system.dart (barrel)
  ├── app_scaffold.dart ──────→ 0 production importers (only test)
  ├── app_glass_card.dart ────→ driver_server.dart (only)
  ├── app_progress_bar.dart ──→ 0 importers
  ├── app_section_header.dart → 0 importers
  ├── app_text.dart ──────────→ 0 production importers (only test)
  ├── app_text_field.dart ────→ driver_server.dart (only)
  ├── app_bottom_sheet.dart ──→ 0 production importers (only test)
  ├── app_dialog.dart ────────→ 0 production importers (only test)
  └── app_chip.dart ──────────→ driver_server.dart (only)

  7 screens import barrel → use AppLoadingState/AppEmptyState/AppToggle only

  Raw patterns still in use:
    AlertDialog(           → 48 occurrences / 30 files
    showDialog(            → 19 occurrences / 15 files
    showModalBottomSheet(  → 8 production files
    TextStyle(             → 215 occurrences / 50 files
    Scaffold(              → Used directly (not AppScaffold)
    LinearProgressIndicator → Used instead of AppProgressBar
```
