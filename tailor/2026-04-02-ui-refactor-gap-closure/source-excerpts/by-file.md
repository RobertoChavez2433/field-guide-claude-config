# Source Excerpts — By File

## lib/core/design_system/app_scaffold.dart
- `AppScaffold` (line 17-60): Scaffold wrapper with SafeArea. Parameters: `body`, `appBar?`, `floatingActionButton?`, `bottomNavigationBar?`, `useSafeArea?`, `backgroundColor?`. Delegates to `Scaffold` with `backgroundColor` passthrough.

## lib/core/design_system/app_glass_card.dart
- `AppGlassCard` (line 18-144): Glassmorphic card with accent tint. Uses `FieldGuideColors.surfaceGlass` background, `DesignConstants.radiusMedium` corners. Static `buildGlassDecoration()` at line 60 for external reuse.

## lib/core/design_system/app_progress_bar.dart
- `AppProgressBar` (line 15-83): 4px animated gradient progress bar. Uses `AnimatedFractionallySizedBox` for smooth transitions. Supports determinate (`value: 0.65`) and indeterminate (`value: null`).

## lib/core/design_system/app_section_header.dart
- `AppSectionHeader` (line 16-56): 8px spaced-letter section header. Auto-uppercases title. Optional `trailing` widget (e.g., count badge, add button).

## lib/core/design_system/app_text.dart
- `AppText` (line 13-142): 15 named factories mapping to Material 3 textTheme slots. Supports `color`, `maxLines`, `overflow`, `textAlign`, `softWrap` overrides. No `letterSpacing` or `fontWeight` overrides by design.

## lib/core/design_system/app_text_field.dart
- `AppTextField` (line 17-107): TextFormField wrapper. 24 parameters covering all common form field needs. Inherits all styling from `inputDecorationTheme`.

## lib/core/design_system/app_dialog.dart
- `AppDialog.show` (line 27-53): Static method wrapping `showDialog` + `AlertDialog`. Uses `AppText.titleLarge` for title. Default single "OK" button if no actions provided.

## lib/core/design_system/app_bottom_sheet.dart
- `AppBottomSheet.show` (line 30-73): Static method wrapping `showModalBottomSheet`. Glass background with `AppDragHandle`, bottom safe area, `radiusXLarge` top corners.

## lib/core/design_system/app_chip.dart
- `AppChip` (line 16-161): 7 named factories (cyan, amber, green, purple, teal, error, neutral). Uses `Chip` widget internally with `labelMedium` text style. `onTap` wraps in `GestureDetector`.

## lib/features/dashboard/presentation/widgets/dashboard_stat_card.dart
- `DashboardStatCard` (line 6-103): Animated stat card. Uses `TweenAnimationBuilder` for entrance, manual `Container`+`BoxDecoration`+gradient. 2 `Text` widgets with `copyWith`.

## lib/features/dashboard/presentation/widgets/budget_overview_card.dart
- `BudgetOverviewCard` (line 8-188): Budget card with gradient header, animated total, progress bar, used/remaining stats. Uses `LinearProgressIndicator`, `Container`+`BoxDecoration`, and `_BudgetStatBox` helper.

## lib/features/dashboard/presentation/widgets/tracked_item_row.dart
- `TrackedItemRow` (line 8-139): Tracked item with percentage badge, 8px progress bar, quantity text. Uses `Container`+gradient+`LinearProgressIndicator`.

## lib/features/dashboard/presentation/widgets/alert_item_row.dart
- `AlertItemRow` (line 7-71): Warning/error row. Conditional colors based on `isOver90`. No progress bar. Shows only percentage badge.

## lib/shared/widgets/confirmation_dialog.dart
- `showConfirmationDialog` (line 7-56): Generic confirm dialog with optional icon. Uses `TestingKeys.confirmationDialog`.
- `showDeleteConfirmationDialog` (line 61-101): Delete-specific confirm with error styling.
- `showUnsavedChangesDialog` (line 124-~): Three-button save/discard/cancel.

## lib/shared/utils/snackbar_helper.dart
- `SnackBarHelper` (line 9-130): 6 static methods for typed snackbars. Uses semantic theme colors.

## lib/core/router/app_router.dart
- `_buildRouter()` (line 82-138): GoRouter setup. Shell routes at line 106-127 use `NoTransitionPage` for 4 bottom-nav screens.

## lib/features/weather/services/weather_service.dart
- `WeatherData` (line 11): Data class with weather fields.
- `WeatherService` (line 27): Open-Meteo API implementation of `WeatherServiceInterface`.

## lib/features/weather/di/weather_providers.dart
- `weatherProviders()` (line 6-12): Registers `Provider<WeatherService>.value`. No ChangeNotifier/WeatherProvider.
