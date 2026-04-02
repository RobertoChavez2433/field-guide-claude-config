# Source Excerpts — By Concern

## Concern 1: Dashboard Redesign

### Current Dashboard Screen Structure (project_dashboard_screen.dart)
- `build()` at line 53 — Main build with `Scaffold` (should be `AppScaffold`)
- `_buildQuickStats()` at line 324 — Builds 4-stat row (should be 3, remove Contractors)
- `_buildReviewDraftsCard()` at line 247 — Full-width drafts card (should be compact `AppChip.cyan` pill)
- `_buildBudgetOverview()` at line 394 — Budget section
- `_buildTrackedItems()` at line 442 — Top tracked items
- `_buildApproachingLimit()` at line 574 — Alert items approaching limit

### DashboardStatCard — Full Source
```dart
// lib/features/dashboard/presentation/widgets/dashboard_stat_card.dart:6-103
// Uses Container + BoxDecoration + gradient + manual Text styling
// Key issue: Should use AppGlassCard instead of manual Container
// Key issue: Text(value, style: tt.titleLarge!.copyWith(...)) → AppText.titleLarge(value, color: color)
// Key issue: Text(label, style: tt.labelSmall!.copyWith(...)) → AppText.labelSmall(label, color: ...)
```
Constructor: `DashboardStatCard({label, value, icon, color, onTap?})`

### BudgetOverviewCard — Key Issues
```dart
// lib/features/dashboard/presentation/widgets/budget_overview_card.dart:8-188
// Uses Container + gradient header + LinearProgressIndicator
// Key issue: LinearProgressIndicator → AppProgressBar(value: usedPercentage)
// Key issue: Manual Text styling throughout → AppText.*
// Key issue: 'BUDGET OVERVIEW' header → AppSectionHeader(title: 'BUDGET OVERVIEW')
```

### TrackedItemRow — Key Issues
```dart
// lib/features/dashboard/presentation/widgets/tracked_item_row.dart:8-139
// Uses Container + gradient + LinearProgressIndicator + manual Text
// Key issue: Container → AppGlassCard
// Key issue: LinearProgressIndicator → AppProgressBar
// Key issue: Only shows used/total, should show explicit quantities and remaining
```

### AlertItemRow — Key Issues
```dart
// lib/features/dashboard/presentation/widgets/alert_item_row.dart:7-71
// Uses Container with conditional colors, NO progress bar
// Key issue: Missing AppProgressBar (spec requires one)
// Key issue: Container → AppGlassCard(accentColor: ...)
// Key issue: No quantity breakdown shown
```

## Concern 2: Design System Adoption

### Barrel File (design_system.dart)
```dart
// lib/core/design_system/design_system.dart — exports 25 components
// 7 screens import it but only use AppLoadingState/AppEmptyState/AppToggle
// Zero production usage of: AppScaffold, AppGlassCard, AppProgressBar,
//   AppSectionHeader, AppText, AppTextField, AppBottomSheet, AppDialog
```

### Key Component APIs (see patterns/ for full source)
- `AppScaffold({body, appBar?, fab?, bottomNav?, useSafeArea?, backgroundColor?})`
- `AppGlassCard({child, accentColor?, onTap?, padding?, margin?, borderRadius?, elevation?, selected?})`
- `AppProgressBar({value?, height?, borderRadius?, gradientColors?, trackColor?})`
- `AppSectionHeader({title, trailing?, padding?})`
- `AppText.{slot}(text, {color?, maxLines?, overflow?, textAlign?})`
- `AppTextField({controller?, label?, hint?, prefixIcon?, ...24 more params})`
- `AppDialog.show(context, {title, content, actions?, barrierDismissible?})`
- `AppBottomSheet.show(context, {builder, isScrollControlled?})`
- `AppChip.{cyan|amber|green|purple|teal|error|neutral}(label, {icon?, onTap?, onDeleted?})`

## Concern 3: Modal Standardization

### showConfirmationDialog — Current Implementation
```dart
// lib/shared/widgets/confirmation_dialog.dart:7-56
// Uses showDialog + AlertDialog with TestingKeys
// Migration: Replace internal AlertDialog with AppDialog.show
// CONSTRAINT: Must preserve TestingKeys (confirmationDialog, cancelDialogButton, etc.)
```

### showDeleteConfirmationDialog — Current Implementation
```dart
// lib/shared/widgets/confirmation_dialog.dart:61-101
// Same pattern as above, with error-colored delete button
```

## Concern 4: Typography (215 callsites)

Top files by TextStyle( count:
| File | Count |
|------|-------|
| `lib/core/theme/app_theme.dart` | 91 (theme definition — DO NOT CHANGE) |
| `lib/features/entries/presentation/screens/entry_editor_screen.dart` | 9 |
| `lib/features/forms/presentation/screens/form_viewer_screen.dart` | 9 |
| `lib/features/quantities/presentation/widgets/bid_item_card.dart` | 6 |
| `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart` | 6 |
| `lib/features/pdf/presentation/screens/mp_import_preview_screen.dart` | 6 |

Note: `app_theme.dart` has 91 TextStyle definitions (this is the theme itself — not a migration target). Actual feature-code TextStyle count is ~124.

## Concern 5: Snackbar Cleanup

### SnackBarHelper — Centralized Pattern
```dart
// lib/shared/utils/snackbar_helper.dart:9-130
// 6 static methods: showSuccess, showError, showErrorWithAction, showInfo, showWarning, showWithAction
// Import: package:construction_inspector/shared/utils/snackbar_helper.dart
```

## Concern 6: Page Transitions

### Current Router (app_router.dart:106-125)
```dart
// 4 shell routes all use NoTransitionPage:
//   '/'         → ProjectDashboardScreen
//   '/calendar' → HomeScreen
//   '/projects' → ProjectListScreen
//   '/settings' → SettingsScreen
// Migration: Replace with CustomTransitionPage + fade/slide
```

## Concern 7: Weather Card (NEW — requires WeatherProvider)

### Current Weather Feature Structure
```
lib/features/weather/
├── di/weather_providers.dart     — registers Provider<WeatherService>
├── domain/weather_service_interface.dart — abstract contract
├── services/weather_service.dart — Open-Meteo API implementation
└── barrel files
```

WeatherProvider (ChangeNotifier) does NOT exist. Only a plain `Provider<WeatherService>.value` is registered.
To add a weather card to the dashboard, a `WeatherProvider extends ChangeNotifier` needs to be created that:
1. Fetches weather via `WeatherService`
2. Caches the result
3. Exposes `WeatherData?` for the dashboard card
