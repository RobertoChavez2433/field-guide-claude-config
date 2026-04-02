# UI Refactor Gap Closure Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Close all gaps between the March 6/28 UI refactor plans and the actual codebase by adopting the design-system library that was built but never rolled out.
**Spec:** `.claude/code-reviews/2026-04-02-ui-refactor-gap-audit-codex-review.md`
**Tailor:** `.claude/tailor/2026-04-02-ui-refactor-gap-closure/`

**Architecture:** The design-system library at `lib/core/design_system/` already contains all needed components (AppScaffold, AppGlassCard, AppProgressBar, AppSectionHeader, AppText, AppTextField, AppDialog, AppBottomSheet, AppChip). This plan migrates production code onto those components. No new design-system components needed except enhancing AppDialog with icon support.
**Tech Stack:** Flutter, Provider, go_router, design_system barrel
**Blast Radius:** ~57 migration files + 8 lint rule files (6 new rules + barrel + docs), 0 dependent, 0 cleanup

---

## Phase 1: AppDialog Enhancement

> Prerequisite for Phase 3 (modal standardization). The confirmation dialogs need icon support.

### Sub-phase 1.1: Add icon/iconColor params to AppDialog.show

**Files:**
- Modify: `lib/core/design_system/app_dialog.dart:27-53`
- Modify: `test/core/design_system/app_dialog_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 1.1.1: Read current AppDialog source

Read `lib/core/design_system/app_dialog.dart` to understand the current implementation.

#### Step 1.1.2: Add icon and iconColor parameters

Modify `AppDialog.show` to accept optional `icon` and `iconColor` parameters. When provided, render the title as a `Row` with the icon and `AppText.titleLarge`. When not provided, keep existing behavior.

```dart
// WHY: Confirmation dialogs need icon+title layout. Adding params here avoids
// each callsite building its own Row(Icon, Text) pattern.
// FROM SPEC: Confirmation dialog migration requires icon support
static Future<T?> show<T>(
  BuildContext context, {
  required String title,
  required Widget content,
  List<Widget>? actions,
  bool barrierDismissible = true,
  IconData? icon,
  Color? iconColor,
  Key? dialogKey,
}) {
  return showDialog<T>(
    context: context,
    barrierDismissible: barrierDismissible,
    builder: (dialogContext) {
      final cs = Theme.of(dialogContext).colorScheme;
      final titleWidget = icon != null
          ? Row(
              children: [
                Icon(icon, color: iconColor ?? cs.primary),
                const SizedBox(width: 12),
                Flexible(child: AppText.titleLarge(title)),
              ],
            )
          : AppText.titleLarge(title);

      return AlertDialog(
        key: dialogKey,
        title: titleWidget,
        content: content,
        actions: actions ?? [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('OK'),
          ),
        ],
      );
    },
  );
}
```

#### Step 1.1.3: Update AppDialog test

Add test cases for the icon variant. Verify icon renders when provided, doesn't render when null.

#### Step 1.1.4: Run targeted test

Run: `pwsh -Command "flutter test test/core/design_system/app_dialog_test.dart"`
Expected: PASS

#### Step 1.1.5: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

---

## Phase 2: Dashboard Redesign

> The highest-value change — transforms the dashboard from raw containers to design-system composition.

### Sub-phase 2.1: Migrate DashboardStatCard to AppGlassCard + AppText

**Files:**
- Modify: `lib/features/dashboard/presentation/widgets/dashboard_stat_card.dart:6-103`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.1.1: Read current source

Read `lib/features/dashboard/presentation/widgets/dashboard_stat_card.dart` completely.

#### Step 2.1.2: Replace Container with AppGlassCard

Replace the inner `Container(decoration: BoxDecoration(...))` with `AppGlassCard(child: ..., accentColor: color)`. Keep the `TweenAnimationBuilder` wrapper for entrance animation.

Key changes:
- Remove the manual `BoxDecoration` with gradient, border, and boxShadow
- Replace with `AppGlassCard(accentColor: color, child: ...)`
- Replace `Text(value, style: tt.titleLarge!.copyWith(color: color, letterSpacing: -0.5))` with `AppText.titleLarge(value, color: color)`
- Replace `Text(label, style: tt.labelSmall!.copyWith(color: cs.onSurfaceVariant, letterSpacing: 0.3))` with `AppText.labelSmall(label, color: cs.onSurfaceVariant)`
- Keep `RepaintBoundary`, icon container, and `Material`+`InkWell` for tap behavior (use AppGlassCard's `onTap` instead)
- Add `import 'package:construction_inspector/core/design_system/design_system.dart';` if not present

#### Step 2.1.3: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 2.2: Migrate BudgetOverviewCard to AppGlassCard + AppProgressBar + AppSectionHeader

**Files:**
- Modify: `lib/features/dashboard/presentation/widgets/budget_overview_card.dart:8-188`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.2.1: Read current source

Read `lib/features/dashboard/presentation/widgets/budget_overview_card.dart` completely.

#### Step 2.2.2: Replace manual progress bar with AppProgressBar

Replace the `LinearProgressIndicator` wrapped in `ClipRRect`+`SizedBox` with:
```dart
// WHY: AppProgressBar provides gradient animation and consistent styling
AppProgressBar(
  value: usedPercentage.clamp(0.0, 1.0),
  height: 14,
  gradientColors: [progressColor, progressColor.withValues(alpha: 0.7)],
)
```

Where `progressColor` is computed the same way it currently is (based on usedPercentage thresholds).

#### Step 2.2.3: Replace header with AppSectionHeader

Replace the manual gradient header `Container` with `AppSectionHeader(title: 'BUDGET OVERVIEW')`.

Note: The current header has a gradient background and wallet icon. `AppSectionHeader` is simpler (text only with optional trailing). The gradient header should be kept as-is since it's a hero element — only replace the text portion with AppSectionHeader-style uppercase + letterSpacing, or keep the custom header and just migrate the text to `AppText.labelLarge`.

**Decision**: Keep the custom gradient header (it's a unique hero element). Migrate text inside it:
- Replace `Text('BUDGET OVERVIEW', style: tt.labelLarge!.copyWith(...))` with `AppText.labelLarge('BUDGET OVERVIEW', color: fg.textInverse)`

#### Step 2.2.4: Migrate remaining Text widgets to AppText

- `Text(currencyFormat, style: tt.displaySmall!.copyWith(...))` → `AppText.displaySmall(currencyFormat, color: cs.onSurface)`
- `Text('TOTAL CONTRACT', style: tt.labelSmall!.copyWith(...))` → `AppText.labelSmall('TOTAL CONTRACT', color: fg.textTertiary)`
- `Text(percentUsed, style: tt.titleSmall!.copyWith(...))` → `AppText.titleSmall(percentUsed, color: progressColor)`

#### Step 2.2.5: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 2.3: Migrate TrackedItemRow to AppGlassCard + AppProgressBar

**Files:**
- Modify: `lib/features/dashboard/presentation/widgets/tracked_item_row.dart:8-139`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.3.1: Read current source

Read `lib/features/dashboard/presentation/widgets/tracked_item_row.dart` completely.

#### Step 2.3.2: Replace Container with AppGlassCard

Replace the outer `Container(decoration: BoxDecoration(...gradient...))` with:
```dart
// WHY: AppGlassCard provides consistent glass styling without manual BoxDecoration
AppGlassCard(
  onTap: onTap,
  margin: const EdgeInsets.only(bottom: DesignConstants.space3),
  child: Row(
    children: [
      // percentage badge (keep existing)
      // ...item info column
    ],
  ),
)
```

Remove the `Material`+`InkWell` wrapper since `AppGlassCard.onTap` handles this.

#### Step 2.3.3: Replace LinearProgressIndicator with AppProgressBar

Replace:
```dart
LinearProgressIndicator(
  value: percentage.clamp(0.0, 1.0),
  backgroundColor: cs.outline,
  valueColor: AlwaysStoppedAnimation<Color>(progressColor),
)
```
With:
```dart
AppProgressBar(
  value: percentage.clamp(0.0, 1.0),
  height: 8,
  gradientColors: [progressColor, progressColor.withValues(alpha: 0.7)],
  trackColor: cs.outline,
)
```

#### Step 2.3.4: Migrate Text widgets to AppText

- `Text('$percentageDisplay%', style: tt.titleMedium!.copyWith(...))` → `AppText.titleMedium('$percentageDisplay%', color: progressColor)`
- `Text('${item.itemNumber} - ${item.description}', style: tt.bodyMedium!.copyWith(...))` → `AppText.bodyMedium('${item.itemNumber} - ${item.description}', color: cs.onSurface, maxLines: 1, overflow: TextOverflow.ellipsis)`
- `Text(quantityText, style: tt.labelSmall!.copyWith(...))` → `AppText.labelSmall(quantityText, color: cs.onSurfaceVariant)`

#### Step 2.3.5: Add remaining quantity display

Add explicit remaining quantity display after the used/total text:
```dart
// FROM SPEC: Tracked rows should show explicit quantities and remaining values
final remaining = item.bidQuantity - usedQuantity;
// In the quantity text:
'${NumberFormat('#,##0.#').format(usedQuantity)}/${NumberFormat('#,##0.#').format(item.bidQuantity)} ${item.unit} (${NumberFormat('#,##0.#').format(remaining)} remaining)'
```

#### Step 2.3.6: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 2.4: Migrate AlertItemRow to AppGlassCard + add AppProgressBar

**Files:**
- Modify: `lib/features/dashboard/presentation/widgets/alert_item_row.dart:7-71`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.4.1: Read current source

Read `lib/features/dashboard/presentation/widgets/alert_item_row.dart` completely.

#### Step 2.4.2: Replace Container with AppGlassCard and add progress bar

Replace the manual `Container` with `AppGlassCard`. Add an `AppProgressBar` that the spec requires but is currently missing. Add explicit quantity breakdown.

The `AlertItemRow` constructor needs a new `usedQuantity` parameter to compute the progress bar value.

```dart
// FROM SPEC: AlertItemRow should include a progress bar and explicit quantity breakdown
class AlertItemRow extends StatelessWidget {
  final BidItem item;
  final double percentage;
  final double usedQuantity; // NEW — needed for quantity display

  const AlertItemRow({
    super.key,
    required this.item,
    required this.percentage,
    required this.usedQuantity, // NEW
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final fg = FieldGuideColors.of(context);
    final isOver90 = percentage > 0.9;
    final accentColor = isOver90 ? cs.error : fg.statusWarning;

    return AppGlassCard(
      accentColor: accentColor,
      margin: const EdgeInsets.only(bottom: DesignConstants.space2),
      padding: const EdgeInsets.symmetric(
        horizontal: DesignConstants.space3,
        vertical: DesignConstants.space2 + 2,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isOver90 ? Icons.error_outline : Icons.warning_amber_rounded,
                color: accentColor,
                size: 18,
              ),
              const SizedBox(width: DesignConstants.space2 + 2),
              Expanded(
                child: AppText.bodyMedium(
                  '${item.itemNumber} ${item.description}',
                  color: cs.onSurface,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DesignConstants.space2,
                  vertical: DesignConstants.space1,
                ),
                decoration: BoxDecoration(
                  color: accentColor,
                  borderRadius: BorderRadius.circular(DesignConstants.radiusXSmall),
                ),
                child: AppText.labelMedium(
                  '${(percentage * 100).toStringAsFixed(0)}%',
                  color: fg.textInverse,
                ),
              ),
            ],
          ),
          const SizedBox(height: DesignConstants.space2),
          // FROM SPEC: Progress bar was missing from AlertItemRow
          AppProgressBar(
            value: percentage.clamp(0.0, 1.0),
            height: 4,
            gradientColors: [accentColor, accentColor.withValues(alpha: 0.7)],
          ),
          const SizedBox(height: DesignConstants.space1),
          // FROM SPEC: Show explicit quantity breakdown
          AppText.bodySmall(
            '${NumberFormat('#,##0.#').format(usedQuantity)}/${NumberFormat('#,##0.#').format(item.bidQuantity)} ${item.unit}',
            color: fg.textTertiary,
          ),
        ],
      ),
    );
  }
}
```

#### Step 2.4.3: Update AlertItemRow callsite in project_dashboard_screen.dart

The callsite in `_buildApproachingLimit()` needs to pass the new `usedQuantity` parameter. Read the screen file to find the exact callsite and update it.

#### Step 2.4.4: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 2.5: Dashboard screen — 3-stat row, draft pill, section headers

**Files:**
- Modify: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.5.1: Read current dashboard screen

Read `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` completely (it's ~730 lines).

#### Step 2.5.2: Replace Scaffold with AppScaffold

At line 57 (or wherever `Scaffold(` appears in the build method), replace with `AppScaffold(`. The parameters map 1:1.

#### Step 2.5.3: Reduce stat row from 4 to 3 (remove Contractors)

In `_buildQuickStats()` at line 324, the current code builds 4 `DashboardStatCard` widgets. Remove the Contractors card. The remaining 3 should be: Entries, Locations, Bid Items (or whichever 3 make sense — read the actual cards to determine).

#### Step 2.5.4: Convert drafts card to compact AppChip.cyan pill

In `_buildReviewDraftsCard()` at line 247, replace the full-width card with a compact `AppChip.cyan` pill:

```dart
// FROM SPEC: Drafts should be a compact pill, not a full-width card
Widget _buildDraftsPill(String projectId) {
  return Consumer<DailyEntryProvider>(
    builder: (context, provider, _) {
      final draftCount = provider.draftEntries.length;
      if (draftCount == 0) return const SizedBox.shrink();
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: DesignConstants.space4),
        child: AppChip.cyan(
          '$draftCount Draft${draftCount > 1 ? 's' : ''} — Tap to Review',
          icon: Icons.edit_note,
          onTap: () {
            // NOTE: Route '/entries/drafts/$projectId' does not exist in app_router.dart.
            // Implementer MUST read the existing _buildReviewDraftsCard navigation target
            // and use the same route/action here. Check project_dashboard_screen.dart for
            // the current drafts card's onTap to find the correct navigation.
          },
        ),
      );
    },
  );
}
```

Replace the `_buildReviewDraftsCard` call in the build method with `_buildDraftsPill`.

#### Step 2.5.5: Add AppSectionHeader for Tracked Items and Approaching Limit sections

In `_buildTrackedItems()` and `_buildApproachingLimit()`, add `AppSectionHeader` at the top of each section:

```dart
// In _buildTrackedItems():
AppSectionHeader(title: 'Top Tracked'),

// In _buildApproachingLimit():
AppSectionHeader(title: 'Approaching Limit'),
```

#### Step 2.5.6: Migrate inline Text widgets to AppText

Scan the entire screen for `Text(` with inline `style:` and convert to appropriate `AppText.*` factories. Key patterns:
- Section titles → already handled by AppSectionHeader
- Stat labels → handled by DashboardStatCard migration
- Any remaining `Text(style: tt.*)` → `AppText.*`

#### Step 2.5.7: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 2.6: WeatherProvider and Dashboard Weather Card

**Files:**
- Create: `lib/features/weather/presentation/providers/weather_provider.dart`
- Modify: `lib/features/weather/di/weather_providers.dart`
- Create: `lib/features/dashboard/presentation/widgets/weather_summary_card.dart`
- Modify: `lib/features/dashboard/presentation/widgets/widgets.dart` (barrel)
- Modify: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.6.1: Create WeatherProvider

```dart
// WHY: Dashboard weather card needs a ChangeNotifier to fetch and cache weather data
// NOTE: Follows provider pattern from other features (e.g., LocationProvider)
import 'package:flutter/foundation.dart';
import 'package:construction_inspector/features/weather/services/weather_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';

class WeatherProvider extends ChangeNotifier {
  final WeatherService _weatherService;

  WeatherProvider({required WeatherService weatherService})
      : _weatherService = weatherService;

  WeatherData? _currentWeather;
  bool _isLoading = false;
  String? _error;

  WeatherData? get currentWeather => _currentWeather;
  bool get isLoading => _isLoading;
  String? get error => _error;

  /// Fetches weather for the given coordinates and date.
  /// NOTE: WeatherService.fetchWeather takes positional params (lat, lon, date).
  Future<void> fetchWeather({
    required double latitude,
    required double longitude,
    DateTime? date,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _currentWeather = await _weatherService.fetchWeather(
        latitude,
        longitude,
        date ?? DateTime.now(),
      );
    } catch (e) {
      _error = e.toString();
      // NOTE: Logger has no 'weather' category. Using 'ui' which covers UI-layer issues.
      Logger.ui('Failed to fetch weather: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
```

**IMPORTANT**: The actual API is `WeatherService.fetchWeather(lat, lon, date)` with positional params and a required `DateTime date` parameter. The code above reflects this. Verify by reading `WeatherService` before implementing.

#### Step 2.6.2: Register WeatherProvider in DI

Modify `lib/features/weather/di/weather_providers.dart` to add `ChangeNotifierProvider<WeatherProvider>`.

**NOTE**: Also verify that the callsite for `weatherProviders()` (likely in `app_providers.dart` or `main.dart`) passes the required `weatherService` parameter. Read the callsite to confirm it already constructs WeatherService or needs updating.

```dart
List<SingleChildWidget> weatherProviders({
  required WeatherService weatherService,
}) {
  return [
    Provider<WeatherService>.value(value: weatherService),
    ChangeNotifierProvider<WeatherProvider>(
      create: (_) => WeatherProvider(weatherService: weatherService),
    ),
  ];
}
```

#### Step 2.6.3: Create WeatherSummaryCard widget

Create `lib/features/dashboard/presentation/widgets/weather_summary_card.dart`:

```dart
// WHY: Dashboard needs a weather summary card backed by WeatherProvider
// FROM SPEC: Weather summary card was specified in March 6 plan but never built
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/core/theme/design_constants.dart';
import 'package:construction_inspector/core/theme/field_guide_colors.dart';
import 'package:construction_inspector/features/weather/presentation/providers/weather_provider.dart';
// NOTE: WeatherData is defined in weather_service.dart, not re-exported by provider.
import 'package:construction_inspector/features/weather/services/weather_service.dart';

class WeatherSummaryCard extends StatelessWidget {
  const WeatherSummaryCard({super.key});

  @override
  Widget build(BuildContext context) {
    final fg = FieldGuideColors.of(context);

    return Consumer<WeatherProvider>(
      builder: (context, provider, _) {
        if (provider.isLoading) {
          return const AppLoadingState(message: 'Loading weather...');
        }

        final weather = provider.currentWeather;
        if (weather == null) return const SizedBox.shrink();

        return AppGlassCard(
          accentColor: fg.statusInfo,
          child: Row(
            children: [
              Icon(_weatherIcon(weather), size: 32, color: fg.statusInfo),
              const SizedBox(width: DesignConstants.space3),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // NOTE: WeatherData has tempHigh (int) and tempLow (int), not temperature.
                    AppText.titleMedium(
                      '${weather.tempHigh}/${weather.tempLow}°F',
                    ),
                    AppText.bodySmall(
                      weather.condition,
                      color: fg.textTertiary,
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  IconData _weatherIcon(WeatherData weather) {
    // NOTE: Map weather conditions to icons. Read WeatherData fields to implement.
    return Icons.cloud;
  }
}
```

**IMPORTANT**: Read `WeatherData` class to get actual field names (temperature, condition, etc.) and adjust the widget accordingly.

#### Step 2.6.4: Add WeatherSummaryCard to dashboard widgets barrel

Add `export 'weather_summary_card.dart';` to `lib/features/dashboard/presentation/widgets/widgets.dart`.

#### Step 2.6.5: Wire WeatherSummaryCard into dashboard screen

Add the weather card to the dashboard build method, after the stats row and before the budget overview.

#### Step 2.6.6: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

**Lint preflight for Phase 2.6**: Two new files are created in this sub-phase (`weather_provider.dart` and `weather_summary_card.dart`). Before creating them, verify their target paths comply with all path-based lint rules (especially `replaceAll('\\', '/')` normalization per memory note).

### Sub-phase 2.7: Today's Entry CTA Card

> FROM SPEC: The spec (line 34) explicitly requires a separate "Today's Entry" CTA card on the dashboard. This was missing from the original plan.

**Files:**
- Create: `lib/features/dashboard/presentation/widgets/todays_entry_card.dart`
- Modify: `lib/features/dashboard/presentation/widgets/widgets.dart` (barrel)
- Modify: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.7.1: Create TodaysEntryCard widget

Create `lib/features/dashboard/presentation/widgets/todays_entry_card.dart`:

```dart
// FROM SPEC: "separate 'Today's Entry' CTA card" on the dashboard
// WHY: Spec requires a prominent action card for creating/resuming today's daily entry
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/core/theme/design_constants.dart';
import 'package:construction_inspector/core/theme/field_guide_colors.dart';

class TodaysEntryCard extends StatelessWidget {
  final VoidCallback onTap;
  final bool hasTodaysEntry;

  const TodaysEntryCard({
    super.key,
    required this.onTap,
    required this.hasTodaysEntry,
  });

  @override
  Widget build(BuildContext context) {
    final fg = FieldGuideColors.of(context);

    return AppGlassCard(
      accentColor: fg.statusSuccess,
      onTap: onTap,
      child: Row(
        children: [
          Icon(
            hasTodaysEntry ? Icons.edit_note : Icons.add_circle_outline,
            size: 32,
            color: fg.statusSuccess,
          ),
          const SizedBox(width: DesignConstants.space3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AppText.titleMedium(
                  hasTodaysEntry ? "Continue Today's Entry" : "Start Today's Entry",
                ),
                AppText.bodySmall(
                  hasTodaysEntry
                      ? 'Resume your daily inspection entry'
                      : 'Create a new entry for today',
                  color: fg.textTertiary,
                ),
              ],
            ),
          ),
          Icon(Icons.chevron_right, color: fg.textTertiary),
        ],
      ),
    );
  }
}
```

**NOTE**: The implementer should read the existing dashboard to determine how today's entry is detected (check DailyEntryProvider or similar) and wire the `hasTodaysEntry` and `onTap` parameters accordingly.

#### Step 2.7.2: Add TodaysEntryCard to dashboard widgets barrel

Add `export 'todays_entry_card.dart';` to `lib/features/dashboard/presentation/widgets/widgets.dart`.

#### Step 2.7.3: Wire TodaysEntryCard into dashboard screen

Add the card to the dashboard build method, after the stats row and before the weather card. The card should navigate to the entry editor for today's date.

#### Step 2.7.4: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 2.8: Project number text migration

> FROM SPEC: Spec line 89 says project number should use projectNumberText style.

**Files:**
- Modify: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.8.1: Migrate project number display

Read the dashboard screen and find the project number display. Migrate it to use `AppText.bodySmall` (or the appropriate semantic style matching `projectNumberText`). The implementer should read the current style and map it to the closest `AppText.*` factory.

#### Step 2.8.2: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

---

## Phase 3: Modal Standardization

> Migrate all raw showDialog/AlertDialog to AppDialog.show and showModalBottomSheet to AppBottomSheet.show.

### Sub-phase 3.1: Confirmation dialog migration

**Files:**
- Modify: `lib/shared/widgets/confirmation_dialog.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 3.1.1: Read current source

Read `lib/shared/widgets/confirmation_dialog.dart` completely.

#### Step 3.1.2: Migrate showConfirmationDialog internals to AppDialog.show

Replace the internal `showDialog` + `AlertDialog` with `AppDialog.show`. Preserve all TestingKeys and the same return behavior.

```dart
// WHY: Migrate shared dialog to design system while preserving public API
// IMPORTANT: TestingKeys must be preserved for E2E test automation
Future<bool> showConfirmationDialog({
  required BuildContext context,
  required String title,
  required String message,
  String confirmText = 'Confirm',
  String cancelText = 'Cancel',
  bool isDestructive = false,
  IconData? icon,
  Color? iconColor,
}) async {
  final result = await AppDialog.show<bool>(
    context,
    title: title,
    content: Text(message),
    icon: icon,
    iconColor: iconColor,
    dialogKey: TestingKeys.confirmationDialog,
    // NOTE: Navigator.pop(context) is safe here because Navigator.pop pops the
    // nearest enclosing route, which IS the dialog (created by showDialog inside
    // AppDialog.show). The outer context resolves to the dialog route, not the screen.
    actions: [
      TextButton(
        key: TestingKeys.cancelDialogButton,
        onPressed: () => Navigator.pop(context, false),
        child: Text(cancelText),
      ),
      ElevatedButton(
        key: _getConfirmButtonKey(confirmText),
        onPressed: () => Navigator.pop(context, true),
        style: isDestructive
            ? ElevatedButton.styleFrom(
                backgroundColor: Theme.of(context).colorScheme.error,
                foregroundColor: Theme.of(context).colorScheme.onError,
              )
            : null,
        child: Text(confirmText),
      ),
    ],
  );
  return result ?? false;
}
```

Similarly migrate `showDeleteConfirmationDialog` and `showUnsavedChangesDialog`.

#### Step 3.1.3: Add design_system import

Add `import 'package:construction_inspector/core/design_system/design_system.dart';` to the file.

#### Step 3.1.4: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 3.2: Feature dialog migration — High-traffic files

**Files (12 files with 2+ AlertDialog each):**
- Modify: `lib/features/settings/presentation/widgets/sign_out_dialog.dart` (4)
- Modify: `lib/features/todos/presentation/screens/todos_screen.dart` (3)
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart` (3)
- Modify: `lib/features/settings/presentation/screens/personnel_types_screen.dart` (3)
- Modify: `lib/features/entries/presentation/widgets/contractor_editor_widget.dart` (2)
- Modify: `lib/features/entries/presentation/widgets/entry_forms_section.dart` (2)
- Modify: `lib/features/forms/presentation/screens/form_viewer_screen.dart` (2)
- Modify: `lib/features/forms/presentation/screens/forms_list_screen.dart` (2)
- Modify: `lib/features/settings/presentation/screens/admin_dashboard_screen.dart` (2)
- Modify: `lib/features/settings/presentation/screens/trash_screen.dart` (2)
- Modify: `lib/features/settings/presentation/screens/settings_screen.dart` (2)
- Modify: `lib/features/entries/presentation/screens/entries_list_screen.dart` (1)

**Agent**: `frontend-flutter-specialist-agent`

**IMPORTANT (lint rule D5)**: After every `await AppDialog.show(...)` or `await AppBottomSheet.show(...)`, verify that the code checks `if (!context.mounted) return;` before using `context` again. This applies to all files in Phases 3.2, 3.3, and 3.4.

#### Step 3.2.1: For each file, read → migrate → verify

For each file in the list above:
1. Read the file completely
2. Find every `showDialog(` + `AlertDialog(` pattern
3. Replace with `AppDialog.show(context, title: ..., content: ..., actions: [...])`
4. Add `import 'package:construction_inspector/core/design_system/design_system.dart';` if not already imported
5. Preserve all existing TestingKeys on buttons

**Migration pattern** (from tailor):
```dart
// BEFORE
final result = await showDialog<bool>(
  context: context,
  builder: (dialogContext) {
    return AlertDialog(
      title: Text('Title'),
      content: Text('Message'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: Text('Cancel')),
        ElevatedButton(onPressed: () => Navigator.pop(dialogContext, true), child: Text('Confirm')),
      ],
    );
  },
);

// AFTER
// NOTE: Navigator.pop(context) is safe here — it pops the nearest enclosing route,
// which is the dialog created by showDialog inside AppDialog.show, not the screen.
final result = await AppDialog.show<bool>(
  context,
  title: 'Title',
  content: Text('Message'),
  actions: [
    TextButton(onPressed: () => Navigator.pop(context, false), child: Text('Cancel')),
    ElevatedButton(onPressed: () => Navigator.pop(context, true), child: Text('Confirm')),
  ],
);
```

**IMPORTANT**: Some files build custom `AlertDialog` content widgets. For these, keep the content as-is and just wrap with `AppDialog.show`.

**IMPORTANT (lint rule D5)**: After every `await AppDialog.show(...)`, check `if (!context.mounted) return;` before using `context` again.

#### Step 3.2.2: Run flutter analyze after all migrations

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 3.3: Feature dialog migration — Single-AlertDialog files

**Files (18 files with 1 AlertDialog each):**
- Modify: `lib/shared/widgets/permission_dialog.dart`
- Modify: `lib/features/photos/presentation/widgets/photo_name_dialog.dart`
- Modify: `lib/features/calculator/presentation/screens/calculator_screen.dart`
- Modify: `lib/features/pdf/services/pdf_service.dart`
- Modify: `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`
- Modify: `lib/features/entries/presentation/widgets/form_selection_dialog.dart`
- Modify: `lib/features/entries/presentation/widgets/add_personnel_type_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/review_summary_screen.dart`
- Modify: `lib/features/forms/presentation/screens/mdot_hub_screen.dart`
- Modify: `lib/features/settings/presentation/widgets/member_detail_sheet.dart`
- Modify: `lib/features/settings/presentation/widgets/clear_cache_dialog.dart`
- Modify: `lib/features/entries/presentation/widgets/add_equipment_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_add_personnel_type_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_weather_edit_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_delete_personnel_type_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_add_quantity_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/home_screen.dart`

**NOTE**: `entry_forms_section.dart` was removed from this list — it has 2 AlertDialogs and is already covered in Sub-phase 3.2.

**Agent**: `frontend-flutter-specialist-agent`

#### Step 3.3.1: Batch migrate all single-AlertDialog files

Same pattern as Sub-phase 3.2. For each file:
1. Read → find AlertDialog → replace with AppDialog.show → add import
2. Preserve all TestingKeys

#### Step 3.3.2: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 3.4: Bottom sheet migration

**Files (8 production files):**
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart`
- Modify: `lib/features/entries/presentation/screens/home_screen.dart`
- Modify: `lib/features/settings/presentation/screens/admin_dashboard_screen.dart`
- Modify: `lib/features/quantities/presentation/widgets/bid_item_detail_sheet.dart`
- Modify: `lib/features/projects/presentation/widgets/project_switcher.dart`
- Modify: `lib/features/pdf/presentation/widgets/extraction_banner.dart`
- Modify: `lib/features/gallery/presentation/screens/gallery_screen.dart`
- Modify: `lib/features/forms/presentation/screens/form_gallery_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 3.4.1: Batch migrate all showModalBottomSheet calls

For each file:
1. Read → find `showModalBottomSheet(` → replace with `AppBottomSheet.show(`
2. Remove manual `backgroundColor: Colors.transparent`, corner radius, and drag handle (AppBottomSheet provides these)
3. The `builder:` parameter maps directly — just pass the content widget

**Migration pattern** (from tailor):
```dart
// BEFORE
showModalBottomSheet(
  context: context,
  isScrollControlled: true,
  builder: (ctx) => MySheetContent(),
);

// AFTER
AppBottomSheet.show(
  context,
  builder: (ctx) => MySheetContent(),
);
```

4. Add `import 'package:construction_inspector/core/design_system/design_system.dart';` if not present

#### Step 3.4.2: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

---

## Phase 4: Typography Migration

> Replace ~124 feature-code TextStyle( callsites with AppText.* across ~49 files (excluding app_theme.dart which has 91 theme definitions — DO NOT CHANGE).

### Sub-phase 4.1: Entries feature typography (highest count)

**Files:**
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart` (9)
- Modify: `lib/features/entries/presentation/widgets/photo_detail_dialog.dart` (2)
- Modify: `lib/features/entries/presentation/widgets/form_selection_dialog.dart` (2)
- Modify: `lib/features/entries/presentation/widgets/entry_photos_section.dart` (1)
- Modify: `lib/features/entries/presentation/widgets/entry_form_card.dart` (1)
- Modify: `lib/features/entries/presentation/widgets/entry_forms_section.dart` (4)
- Modify: `lib/features/entries/presentation/screens/review_summary_screen.dart` (2)
- Modify: `lib/features/entries/presentation/widgets/entry_basics_section.dart` (2)
- Modify: `lib/features/entries/presentation/widgets/entry_action_bar.dart` (1)
- Modify: `lib/features/entries/presentation/widgets/draft_entry_tile.dart` (1)
- Modify: `lib/features/entries/presentation/widgets/bid_item_picker_sheet.dart` (1)
- Modify: `lib/features/entries/presentation/screens/home_screen.dart` (1)
- Modify: `lib/features/entries/presentation/screens/entry_review_screen.dart` (2)
- Modify: `lib/features/entries/presentation/screens/entries_list_screen.dart` (1)
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_debug_pdf_actions_dialog.dart` (1)
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_pdf_actions_dialog.dart` (1)
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_photo_detail_dialog.dart` (4)

**Agent**: `frontend-flutter-specialist-agent`

#### Step 4.1.1: Batch migrate entries feature TextStyle patterns

For each file:
1. Read completely
2. Find each `TextStyle(` usage in non-theme context
3. Determine the semantic slot from the typography migration pattern table
4. Replace with `AppText.*` if it's a standalone `Text` widget
5. If it's a `TextStyle` passed to a non-Text widget (e.g., `InputDecoration`), keep as-is
6. Add design_system import if needed

**Cases where TextStyle CANNOT be replaced:**
- `TextStyle` in `RichText`/`TextSpan` compositions
- `TextStyle` in `InputDecoration` (handled by `AppTextField` migration)
- `TextStyle` in button/chip styling (handled by theme)

#### Step 4.1.2: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 4.2: Forms feature typography

**Files:**
- Modify: `lib/features/forms/presentation/screens/form_viewer_screen.dart` (9)
- Modify: `lib/features/forms/presentation/screens/forms_list_screen.dart` (3)
- Modify: `lib/features/forms/presentation/widgets/hub_quick_test_content.dart` (1)
- Modify: `lib/features/forms/presentation/widgets/hub_proctor_content.dart` (1)

**Agent**: `frontend-flutter-specialist-agent`

#### Step 4.2.1: Batch migrate forms feature TextStyle patterns

Same approach as Sub-phase 4.1.

#### Step 4.2.2: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 4.3: Quantities feature typography

**Files:**
- Modify: `lib/features/quantities/presentation/widgets/bid_item_card.dart` (6)
- Modify: `lib/features/quantities/presentation/widgets/quantity_summary_header.dart` (3)
- Modify: `lib/features/quantities/presentation/screens/quantities_screen.dart` (2)

**Agent**: `frontend-flutter-specialist-agent`

#### Step 4.3.1: Batch migrate quantities feature TextStyle patterns

Same approach as Sub-phase 4.1.

#### Step 4.3.2: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 4.4: PDF feature typography

**Files:**
- Modify: `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart` (6)
- Modify: `lib/features/pdf/presentation/screens/mp_import_preview_screen.dart` (6)
- Modify: `lib/features/pdf/presentation/widgets/extraction_detail_sheet.dart` (1)
- Modify: `lib/features/pdf/presentation/widgets/extraction_banner.dart` (2)

**Agent**: `frontend-flutter-specialist-agent`

#### Step 4.4.1: Batch migrate PDF feature TextStyle patterns

Same approach as Sub-phase 4.1.

#### Step 4.4.2: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 4.5: Settings feature typography

**Files:**
- Modify: `lib/features/settings/presentation/screens/admin_dashboard_screen.dart` (5)
- Modify: `lib/features/settings/presentation/widgets/member_detail_sheet.dart` (4)
- Modify: `lib/features/settings/presentation/widgets/sync_section.dart` (2)
- Modify: `lib/features/settings/presentation/screens/settings_screen.dart` (2)
- Modify: `lib/features/settings/presentation/screens/personnel_types_screen.dart` (1)
- Modify: `lib/features/settings/presentation/screens/help_support_screen.dart` (1)
- Modify: `lib/features/settings/presentation/screens/legal_document_screen.dart` (1)

**Agent**: `frontend-flutter-specialist-agent`

#### Step 4.5.1: Batch migrate settings feature TextStyle patterns

Same approach as Sub-phase 4.1.

#### Step 4.5.2: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

### Sub-phase 4.6: Remaining features typography

**Files:**
- Modify: `lib/features/projects/presentation/widgets/assignments_step.dart` (1)
- Modify: `lib/features/projects/presentation/widgets/pay_item_source_dialog.dart` (3)
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart` (4)
- Modify: `lib/features/projects/presentation/widgets/project_switcher.dart` (2)
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart` (1)
- Modify: `lib/features/gallery/presentation/screens/gallery_screen.dart` (1)
- Modify: `lib/features/sync/presentation/screens/sync_dashboard_screen.dart` (4)
- Modify: `lib/features/sync/presentation/widgets/deletion_notification_banner.dart` (1)
- Modify: `lib/features/photos/presentation/widgets/photo_thumbnail.dart` (2)
- Modify: `lib/features/auth/presentation/screens/login_screen.dart` (1)
- Modify: `lib/features/auth/presentation/screens/register_screen.dart` (3)
- Modify: `lib/features/todos/presentation/screens/todos_screen.dart` (3)
- Modify: `lib/shared/widgets/contextual_feedback_overlay.dart` (1)

**Agent**: `frontend-flutter-specialist-agent`

#### Step 4.6.1: Batch migrate remaining TextStyle patterns

Same approach as Sub-phase 4.1.

#### Step 4.6.2: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

---

## Phase 5: Dialog Input Migration (AppTextField)

> Replace raw TextFormField in form dialogs with AppTextField.

### Sub-phase 5.1: Form dialog AppTextField migration

**Files:**
- Modify: `lib/features/projects/presentation/widgets/add_contractor_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/add_location_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/bid_item_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_add_quantity_dialog.dart`

**NOTE**: `confirmation_dialog.dart` was removed from this list — it has no text inputs.

**Agent**: `frontend-flutter-specialist-agent`

#### Step 5.1.1: Read each dialog and migrate TextFormField to AppTextField

For each file:
1. Read completely
2. Find `TextFormField(` usages
3. Replace with `AppTextField(` — parameters map almost 1:1:
   - `controller:` → `controller:`
   - `decoration: InputDecoration(labelText: ...)` → `label: ...`
   - `decoration: InputDecoration(hintText: ...)` → `hint: ...`
   - `decoration: InputDecoration(prefixIcon: Icon(Icons.x))` → `prefixIcon: Icons.x`
   - `validator:` → `validator:`
   - `onChanged:` → `onChanged:`
   - `keyboardType:` → `keyboardType:`
   - `textInputAction:` → `textInputAction:`
   - `maxLines:` → `maxLines:`
4. Add design_system import

#### Step 5.1.2: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

---

## Phase 6: Snackbar Cleanup

> Route all direct ScaffoldMessenger/SnackBar usage through SnackBarHelper.

### Sub-phase 6.1: Migrate direct snackbar callsites

**Files (7 files bypassing SnackBarHelper):**
- Modify: `lib/features/settings/presentation/screens/help_support_screen.dart`
- Modify: `lib/features/settings/presentation/screens/consent_screen.dart`
- Modify: `lib/features/settings/presentation/screens/legal_document_screen.dart`
- Modify: `lib/features/projects/presentation/widgets/add_equipment_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/add_location_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart`
- Modify: `lib/features/entries/presentation/controllers/pdf_data_builder.dart` — **NOTE**: This file uses a pre-captured `ScaffoldMessengerState` (not `BuildContext`), so it cannot use `SnackBarHelper.show*` directly. The implementer must either (a) refactor to pass BuildContext, or (b) leave this callsite as-is and document the exception.

**Agent**: `frontend-flutter-specialist-agent`

#### Step 6.1.1: Read each file and replace direct snackbar calls

For each file:
1. Read completely
2. Find `ScaffoldMessenger.of(context).showSnackBar(SnackBar(...))` patterns
3. Determine the semantic type (success, error, info, warning) from the color/context
4. Replace with the appropriate `SnackBarHelper.show*` method
5. Add `import 'package:construction_inspector/shared/utils/snackbar_helper.dart';` if not present (or use shared.dart barrel)

**Migration patterns:**
```dart
// Success (green background)
// BEFORE: ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Saved'), backgroundColor: successColor))
// AFTER: SnackBarHelper.showSuccess(context, 'Saved')

// Error (red background)
// BEFORE: ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed'), backgroundColor: errorColor))
// AFTER: SnackBarHelper.showError(context, 'Failed')

// Info (blue/primary background)
// BEFORE: ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Copied')))
// AFTER: SnackBarHelper.showInfo(context, 'Copied')
```

#### Step 6.1.2: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

---

## Phase 7: Cleanup — ValueKey, Page Transitions

### Sub-phase 7.1: ValueKey cleanup

**Files:**
- Modify: `lib/core/router/routes/project_routes.dart:24`
- Modify: `lib/features/gallery/presentation/screens/gallery_screen.dart:374`
- Modify: `lib/features/pdf/presentation/screens/mp_import_preview_screen.dart:190`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.1.1: Read each file and evaluate ValueKey usage

For each file:
1. Read the line with `ValueKey(`
2. Determine if it should be a `TestingKeys.*` constant or a dynamic identity key
3. If it's a widget identity key (like `ValueKey(projectId)` for route state), it's intentional — **leave as-is** or move to a named constant
4. If it's a testing key, extract to `TestingKeys.*`

Specific cases from ground truth:
- `project_routes.dart:24` — `ValueKey(projectId)` — This is a route state key, NOT a testing key. Leave as-is.
- `gallery_screen.dart:374` — `ValueKey('entry_dropdown_${...}')` — Widget-reset key. Leave as-is (has WHY comment).
- `mp_import_preview_screen.dart:190` — `ValueKey('mp_match_card_${...}')` — List identity key. Leave as-is (has WHY comment).

**Decision**: All 3 ValueKey usages are intentional identity/reset keys, not testing keys. They are correctly used. No changes needed. Mark as reviewed and accepted.

### Sub-phase 7.2: Page transitions

**Files:**
- Modify: `lib/core/router/app_router.dart:106-125`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.2.1: Read router shell routes

Read `lib/core/router/app_router.dart` lines 82-138.

#### Step 7.2.2: Replace NoTransitionPage with CustomTransitionPage

Replace each `NoTransitionPage` with a `CustomTransitionPage` that provides a subtle fade transition:

```dart
// FROM SPEC: March 6 Phase 11 called for fade/slide transitions
// WHY: NoTransitionPage creates abrupt visual cuts between bottom nav tabs
CustomTransitionPage(
  child: const ProjectDashboardScreen(),
  transitionsBuilder: (context, animation, secondaryAnimation, child) {
    return FadeTransition(opacity: animation, child: child);
  },
  transitionDuration: DesignConstants.animationFast,
)
```

Apply the same pattern to all 4 shell routes (dashboard, home, projects, settings).

#### Step 7.2.3: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

---

> **DEFERRED**: Spec lines 267-276 identify lazy-list conversion (replacing `Column`+`SingleChildScrollView` with `ListView.builder` / `SliverList`) and scroll physics standardization (`BouncingScrollPhysics` everywhere) as incomplete. These are performance optimizations that do not affect visual correctness and are deferred to a separate performance-focused plan. File a follow-up GitHub Issue labeled `enhancement/performance` if not already tracked.

---

## Phase 8: Design System Enforcement Lint Rules

> New lint rules that prevent regression to raw patterns. These run after the migration is complete, ensuring no one accidentally bypasses the design system.

### Sub-phase 8.1: Create no_raw_alert_dialog rule (A18)

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_alert_dialog.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.1.1: Implement no_raw_alert_dialog

```dart
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A18: Flags raw AlertDialog usage in presentation files.
///
/// Use AppDialog.show() instead. Raw AlertDialog is only allowed inside
/// the design system wrapper itself.
/// Severity: ERROR
class NoRawAlertDialog extends DartLintRule {
  NoRawAlertDialog() : super(code: _code);

  static const _code = LintCode(
    name: 'no_raw_alert_dialog',
    problemMessage:
        'Use AppDialog.show() instead of raw AlertDialog. '
        'The design system wrapper provides consistent theming.',
    correctionMessage:
        'Replace showDialog + AlertDialog with AppDialog.show(context, '
        'title: ..., content: ..., actions: [...])',
    errorSeverity: ErrorSeverity.ERROR,
  );

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    // NOTE: Only enforce in presentation layer
    if (!filePath.contains('/presentation/')) return;
    // NOTE: Skip test files
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    // NOTE: Allow inside the design system wrapper itself
    if (filePath.contains('/core/design_system/')) return;

    context.registry.addInstanceCreationExpression((node) {
      final typeName = node.constructorName.type.name2.lexeme;
      if (typeName == 'AlertDialog') {
        reporter.atNode(node.constructorName, _code);
      }
    });
  }
}
```

### Sub-phase 8.2: Create no_raw_show_dialog rule (A19)

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_show_dialog.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.2.1: Implement no_raw_show_dialog

```dart
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A19: Flags raw showDialog() usage in presentation files.
///
/// Use AppDialog.show() instead. Raw showDialog is only allowed inside
/// the design system wrapper itself.
/// Severity: ERROR
class NoRawShowDialog extends DartLintRule {
  NoRawShowDialog() : super(code: _code);

  static const _code = LintCode(
    name: 'no_raw_show_dialog',
    problemMessage:
        'Use AppDialog.show() instead of raw showDialog(). '
        'The design system wrapper provides consistent theming.',
    correctionMessage:
        'Replace with AppDialog.show(context, title: ..., content: ..., '
        'actions: [...])',
    errorSeverity: ErrorSeverity.ERROR,
  );

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    if (!filePath.contains('/presentation/')) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    if (filePath.contains('/core/design_system/')) return;
    // NOTE: Also allow in shared/widgets/ confirmation_dialog.dart since it
    // wraps AppDialog.show and is itself a shared utility
    if (filePath.contains('/shared/widgets/confirmation_dialog')) return;

    context.registry.addFunctionExpressionInvocation((node) {
      final function = node.function;
      if (function is SimpleIdentifier && function.name == 'showDialog') {
        reporter.atNode(function, _code);
      }
    });

    context.registry.addMethodInvocation((node) {
      if (node.methodName.name == 'showDialog' && node.target == null) {
        reporter.atNode(node.methodName, _code);
      }
    });
  }
}
```

**IMPORTANT**: Read the actual `confirmation_dialog.dart` after Phase 3 migration — if it now calls `AppDialog.show` internally (not raw `showDialog`), the allowlist for it can be removed.

### Sub-phase 8.3: Create no_raw_bottom_sheet rule (A20)

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_bottom_sheet.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.3.1: Implement no_raw_bottom_sheet

```dart
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A20: Flags raw showModalBottomSheet() usage in presentation files.
///
/// Use AppBottomSheet.show() instead. Raw showModalBottomSheet is only
/// allowed inside the design system wrapper itself.
/// Severity: ERROR
class NoRawBottomSheet extends DartLintRule {
  NoRawBottomSheet() : super(code: _code);

  static const _code = LintCode(
    name: 'no_raw_bottom_sheet',
    problemMessage:
        'Use AppBottomSheet.show() instead of raw showModalBottomSheet(). '
        'The design system wrapper provides consistent glass styling.',
    correctionMessage:
        'Replace with AppBottomSheet.show(context, builder: (ctx) => ...)',
    errorSeverity: ErrorSeverity.ERROR,
  );

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    if (!filePath.contains('/presentation/')) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    if (filePath.contains('/core/design_system/')) return;

    context.registry.addMethodInvocation((node) {
      if (node.methodName.name == 'showModalBottomSheet' && node.target == null) {
        reporter.atNode(node.methodName, _code);
      }
    });
  }
}
```

### Sub-phase 8.4: Create no_raw_scaffold rule (A21)

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_scaffold.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.4.1: Implement no_raw_scaffold

```dart
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A21: Flags raw Scaffold usage in presentation screen files.
///
/// Use AppScaffold instead. Raw Scaffold is only allowed inside
/// the design system wrapper and non-screen widgets.
/// Severity: WARNING (not all widgets need AppScaffold — only screens)
class NoRawScaffold extends DartLintRule {
  NoRawScaffold() : super(code: _code);

  static const _code = LintCode(
    name: 'no_raw_scaffold',
    problemMessage:
        'Use AppScaffold instead of raw Scaffold in screen files. '
        'AppScaffold provides consistent SafeArea and theming.',
    correctionMessage:
        'Replace Scaffold(...) with AppScaffold(body: ..., appBar: ...)',
    errorSeverity: ErrorSeverity.WARNING,
  );

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    // NOTE: Only enforce in screen files, not all presentation
    if (!filePath.contains('/presentation/screens/')) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    if (filePath.contains('/core/design_system/')) return;
    // NOTE: Allow in scaffold_with_nav_bar.dart (shell route wrapper)
    if (filePath.contains('scaffold_with_nav_bar')) return;

    context.registry.addInstanceCreationExpression((node) {
      final typeName = node.constructorName.type.name2.lexeme;
      if (typeName == 'Scaffold') {
        reporter.atNode(node.constructorName, _code);
      }
    });
  }
}
```

### Sub-phase 8.5: Create no_direct_snackbar rule (A22)

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_direct_snackbar.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.5.1: Implement no_direct_snackbar

```dart
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A22: Flags direct ScaffoldMessenger.showSnackBar usage in presentation files.
///
/// Use SnackBarHelper.show*() instead. Direct snackbar calls are only
/// allowed inside the centralized helper itself.
/// Severity: WARNING
class NoDirectSnackbar extends DartLintRule {
  NoDirectSnackbar() : super(code: _code);

  static const _code = LintCode(
    name: 'no_direct_snackbar',
    problemMessage:
        'Use SnackBarHelper.show*() instead of direct ScaffoldMessenger/'
        'SnackBar calls. The helper provides consistent theming.',
    correctionMessage:
        'Replace with SnackBarHelper.showSuccess/showError/showInfo/showWarning',
    errorSeverity: ErrorSeverity.WARNING,
  );

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    if (!filePath.contains('/presentation/')) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    // NOTE: Allow inside the helper itself
    if (filePath.contains('snackbar_helper')) return;

    context.registry.addMethodInvocation((node) {
      if (node.methodName.name == 'showSnackBar') {
        reporter.atNode(node.methodName, _code);
      }
    });
  }
}
```

### Sub-phase 8.6: Create no_inline_text_style rule (A23)

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_inline_text_style.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.6.1: Implement no_inline_text_style

```dart
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A23: Flags inline TextStyle() constructors in presentation files.
///
/// Use AppText.* factories or textTheme slots instead. Inline TextStyle
/// is only allowed inside theme definitions and design system components.
/// Severity: WARNING
class NoInlineTextStyle extends DartLintRule {
  NoInlineTextStyle() : super(code: _code);

  static const _code = LintCode(
    name: 'no_inline_text_style',
    problemMessage:
        'Use AppText.* factories or theme textTheme slots instead of '
        'inline TextStyle constructors.',
    correctionMessage:
        'Replace Text(style: TextStyle(...)) with AppText.bodyMedium(...) '
        'or the appropriate textTheme slot.',
    errorSeverity: ErrorSeverity.WARNING,
  );

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    if (!filePath.contains('/presentation/')) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    // NOTE: Allow in theme definitions and design system
    if (filePath.contains('/core/theme/')) return;
    if (filePath.contains('/core/design_system/')) return;
    // NOTE: Allow in snackbar helper (uses TextStyle for SnackBar content)
    if (filePath.contains('snackbar_helper')) return;

    context.registry.addInstanceCreationExpression((node) {
      final typeName = node.constructorName.type.name2.lexeme;
      if (typeName == 'TextStyle') {
        reporter.atNode(node.constructorName, _code);
      }
    });
  }
}
```

### Sub-phase 8.7: Register all new rules

**Files:**
- Modify: `fg_lint_packages/field_guide_lints/lib/architecture/architecture_rules.dart`
- Modify: `fg_lint_packages/field_guide_lints/lib/field_guide_lints.dart` (update docstring count)

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.7.1: Add imports and instances to architecture_rules.dart

Add imports for all 6 new rule files and add instances to the `architectureRules` list:

```dart
// Add imports:
import 'rules/no_raw_alert_dialog.dart';
import 'rules/no_raw_show_dialog.dart';
import 'rules/no_raw_bottom_sheet.dart';
import 'rules/no_raw_scaffold.dart';
import 'rules/no_direct_snackbar.dart';
import 'rules/no_inline_text_style.dart';

// Add to architectureRules list:
  NoRawAlertDialog(),
  NoRawShowDialog(),
  NoRawBottomSheet(),
  NoRawScaffold(),
  NoDirectSnackbar(),
  NoInlineTextStyle(),
```

Update the comment from `A1-A15, A17` to `A1-A15, A17-A23`.

#### Step 8.7.2: Update field_guide_lints.dart docstring

Update the architecture rule count from 16 to 22 in the library docstring.

#### Step 8.7.3: Update architecture.md rule tables

Add the new rules to the lint rule tables in `.claude/rules/architecture.md`:

Anti-Patterns (Enforced by Lint) table:
```
| Raw `AlertDialog(` in presentation | A18 | Use `AppDialog.show()` |
| Raw `showDialog(` in presentation | A19 | Use `AppDialog.show()` |
| Raw `showModalBottomSheet(` in presentation | A20 | Use `AppBottomSheet.show()` |
| Raw `Scaffold(` in screen files | A21 | Use `AppScaffold` |
| Direct `ScaffoldMessenger`/`showSnackBar` in presentation | A22 | Use `SnackBarHelper.show*()` |
| Inline `TextStyle(` in presentation | A23 | Use `AppText.*` or textTheme slots |
```

Lint Rule Path Triggers table — add to `*/presentation/*` row:
```
A18, A19, A20, A22, A23
```
Add to `*/presentation/screens/*`:
```
A21
```

#### Step 8.7.4: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues (the migration in Phases 1-7 should have already removed all violations)

---

## Phase 9: Quality Gate Verification

### Sub-phase 9.1: Final verification

**Agent**: `frontend-flutter-specialist-agent`

#### Step 9.1.1: Run flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues found

#### Step 9.1.2: Verify design system adoption counts

Run grep to verify migration progress:
- `AlertDialog(` in lib/ (excluding design_system) — should be 1 (inside AppDialog.show itself)
- `showDialog(` in lib/ (excluding design_system) — should be 1 (inside AppDialog.show itself)
- `showModalBottomSheet(` in lib/ (excluding design_system) — should be 1 (inside AppBottomSheet.show itself)
- `TextStyle(` in lib/ (excluding app_theme.dart and snackbar_helper.dart) — should be near 0 for presentation code
- `ScaffoldMessenger` in lib/ (excluding snackbar_helper.dart) — should be near 0

#### Step 9.1.3: Verify dashboard changes

Manually verify:
- Dashboard uses `AppScaffold` (not raw `Scaffold`)
- Stat row has 3 cards (not 4)
- Drafts show as compact chip pill (not full card)
- Budget overview uses `AppProgressBar`
- Tracked items use `AppGlassCard` + `AppProgressBar`
- Alert items have `AppProgressBar` and quantity breakdown
- Section headers use `AppSectionHeader`
- Weather card is present (when weather data available)
- Today's Entry CTA card is present (FROM SPEC line 34)
- Project number uses semantic AppText style (FROM SPEC line 89)
