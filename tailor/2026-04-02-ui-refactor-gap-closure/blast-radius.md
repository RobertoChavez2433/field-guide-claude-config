# Blast Radius

## Design System Components — Current Blast Radius

All design system components have **near-zero production blast radius** because they are not yet adopted. This is a key insight: adoption can proceed incrementally without breaking anything, since nothing currently depends on them in production.

| Component | Production Importers | Test Importers | Driver |
|-----------|---------------------|----------------|--------|
| `AppScaffold` | 0 | 1 (app_scaffold_test) | No |
| `AppGlassCard` | 0 | 1 (app_glass_card_test) | Yes |
| `AppProgressBar` | 0 | 0 | No |
| `AppSectionHeader` | 0 | 0 | No |
| `AppText` | 0 | 1 (app_text_test) | No |
| `AppTextField` | 0 | 1 (app_text_field_test) | Yes |
| `AppBottomSheet` | 0 | 1 (app_bottom_sheet_test) | No |
| `AppDialog` | 0 | 1 (app_dialog_test) | No |
| `AppChip` | 0 | 1 (app_chip_test) | Yes |

## Dashboard Widget Changes — Blast Radius

Dashboard widgets are **only used from** `project_dashboard_screen.dart` via the `widgets.dart` barrel. Changes to these widgets are localized.

| Widget | Importers |
|--------|-----------|
| `DashboardStatCard` | `project_dashboard_screen.dart` (via barrel) |
| `BudgetOverviewCard` | `project_dashboard_screen.dart` (via barrel) |
| `TrackedItemRow` | `project_dashboard_screen.dart` (via barrel) |
| `AlertItemRow` | `project_dashboard_screen.dart` (via barrel) |

## Confirmation Dialog — HIGH Blast Radius

`lib/shared/widgets/confirmation_dialog.dart` is exported via `lib/shared/shared.dart`, which is imported throughout the entire app. Changing its internals (switching from raw `AlertDialog` to `AppDialog.show`) is safe as long as the external API (`showConfirmationDialog`, `showDeleteConfirmationDialog`, `showUnsavedChangesDialog`) remains unchanged.

**Safe migration strategy**: Change the internal implementation to use `AppDialog.show` while keeping the same function signatures. All callers are unaffected.

## Modal Migration — Per-File Blast Radius

Each modal/dialog file is typically self-contained. The `showDialog` and `showModalBottomSheet` calls are local to each file. Migration is file-by-file with no cross-file impact.

### showModalBottomSheet Files (8 production)
Each call is local — replacing with `AppBottomSheet.show` affects only that file.

### AlertDialog Files (30 files, 48 occurrences)
Each `AlertDialog` is constructed locally. Replacing with `AppDialog.show` is a per-file change.

## Typography Migration — Distributed Blast Radius

215 `TextStyle(` callsites across 50 files. Each is a local replacement — changing `TextStyle(...)` to the appropriate `AppText.*` factory or `tt.*` textTheme slot. No cross-file impact per change, but high volume.

## Router Transitions — Low Blast Radius

4 `NoTransitionPage` usages in `app_router.dart`, all within the shell route builder. Changing to `CustomTransitionPage` affects only navigation animation, no business logic.

## Dead Code Targets (Design System Related)

The following design system components have zero importers (not even via barrel in production code that actually uses them):
- `AppProgressBar` — 0 total importers
- `AppSectionHeader` — 0 total importers

These are not dead code per se — they are built but never wired. The migration will create their first production consumers.
