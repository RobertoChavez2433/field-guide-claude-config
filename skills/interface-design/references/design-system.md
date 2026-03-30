# Design System Reference

Field Guide App design system. Single import: `package:construction_inspector/core/design_system/design_system.dart`.

## Theme Extensions

### FieldGuideColors
`lib/core/theme/field_guide_colors.dart`

ThemeExtension that provides the T Vivid glassmorphic color palette. Access via `Theme.of(context).extension<FieldGuideColors>()`.

### DesignConstants
`lib/core/theme/design_constants.dart`

Static constants for spacing, radius, elevation, icon sizes, animation durations, and shadow definitions. Use instead of magic numbers.

---

## Design System Components

All components live in `lib/core/design_system/`. Import via the barrel: `design_system.dart`.

| File | Component | Purpose |
|------|-----------|---------|
| `app_scaffold.dart` | `AppScaffold` | Scaffold wrapper with SafeArea that inherits scaffoldBackgroundColor from ThemeData |
| `app_dialog.dart` | `AppDialog` | Themed dialog with standardized title/content/actions layout |
| `app_bottom_sheet.dart` | `AppBottomSheet` | Glass bottom sheet with drag handle and consistent styling |
| `app_bottom_bar.dart` | `AppBottomBar` | Sticky bottom action bar with blur backdrop for persistent actions |
| `app_text_field.dart` | `AppTextField` | Theme-aware TextFormField wrapper that inherits all styling from inputDecorationTheme |
| `app_text.dart` | `AppText` | Enforces textTheme slot usage instead of inline TextStyle constructors |
| `app_icon.dart` | `AppIcon` | Standardized icon sizing using the 4-tier system |
| `app_toggle.dart` | `AppToggle` | Label + optional subtitle + Switch.adaptive that inherits switchTheme |
| `app_glass_card.dart` | `AppGlassCard` | Core T Vivid glassmorphic card with optional accent color tinting |
| `app_counter_field.dart` | `AppCounterField` | +/- stepper for integer value entry with field-sized touch targets |
| `app_error_state.dart` | `AppErrorState` | Error state display with icon, message, and optional retry button |
| `app_info_banner.dart` | `AppInfoBanner` | Colored info/warning banner with icon and message |
| `app_drag_handle.dart` | `AppDragHandle` | Bottom sheet drag handle indicator |
| `app_budget_warning_chip.dart` | `AppBudgetWarningChip` | Budget warning chip with severity-based coloring |
| `app_chip.dart` | `AppChip` | Colored chip with named factory variants for consistent status/category display |
| `app_list_tile.dart` | `AppListTile` | Glass-styled list row that wraps content in the T Vivid card style |
| `app_empty_state.dart` | `AppEmptyState` | Empty state placeholder with icon, title, optional subtitle, and optional CTA |
| `app_loading_state.dart` | `AppLoadingState` | Full-screen loading state with optional label |
| `app_mini_spinner.dart` | `AppMiniSpinner` | Inline loading spinner for buttons, list items, and status indicators |
| `app_photo_grid.dart` | `AppPhotoGrid` | Photo thumbnail grid with optional add button |
| `app_progress_bar.dart` | `AppProgressBar` | 4px animated gradient progress bar |
| `app_section_card.dart` | `AppSectionCard` | Card with a colored header strip containing an icon + title, followed by body content |
| `app_section_header.dart` | `AppSectionHeader` | 8px spaced-letter section header with optional trailing action |
| `app_sticky_header.dart` | `AppStickyHeader` | Blur-backdrop sticky header for use in CustomScrollView / NestedScrollView |

---

## Usage

```dart
// Single import for all components
import 'package:construction_inspector/core/design_system/design_system.dart';

// Access theme extensions
final colors = Theme.of(context).extension<FieldGuideColors>()!;

// Use design constants
const radius = DesignConstants.radiusMd;
```
