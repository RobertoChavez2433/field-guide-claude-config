# Ground Truth

## Design System Components

| Component | File:Line | Signature | Status |
|-----------|-----------|-----------|--------|
| `AppScaffold` | `lib/core/design_system/app_scaffold.dart:17` | `class AppScaffold extends StatelessWidget` | VERIFIED |
| `AppGlassCard` | `lib/core/design_system/app_glass_card.dart:18` | `class AppGlassCard extends StatelessWidget` | VERIFIED |
| `AppProgressBar` | `lib/core/design_system/app_progress_bar.dart:15` | `class AppProgressBar extends StatelessWidget` | VERIFIED |
| `AppSectionHeader` | `lib/core/design_system/app_section_header.dart:16` | `class AppSectionHeader extends StatelessWidget` | VERIFIED |
| `AppText` | `lib/core/design_system/app_text.dart:13` | `class AppText extends StatelessWidget` | VERIFIED |
| `AppTextField` | `lib/core/design_system/app_text_field.dart:17` | `class AppTextField extends StatelessWidget` | VERIFIED |
| `AppBottomSheet.show` | `lib/core/design_system/app_bottom_sheet.dart:30` | `static Future<T?> show<T>(BuildContext context, {required Widget Function(BuildContext) builder, bool isScrollControlled = true})` | VERIFIED |
| `AppDialog.show` | `lib/core/design_system/app_dialog.dart:27` | `static Future<T?> show<T>(BuildContext context, {required String title, required Widget content, List<Widget>? actions, bool barrierDismissible = true})` | VERIFIED |
| `AppChip` | `lib/core/design_system/app_chip.dart:16` | `class AppChip extends StatelessWidget` | VERIFIED |
| `AppChip.cyan` | `lib/core/design_system/app_chip.dart:39` | `factory AppChip.cyan(String label, ...)` | VERIFIED |
| `design_system.dart` | `lib/core/design_system/design_system.dart:1` | Barrel export, 25 components | VERIFIED |

## AppText Factory Methods

| Factory | File:Line | Maps To | Size/Weight |
|---------|-----------|---------|-------------|
| `AppText.displayLarge` | `app_text.dart:38` | `tt.displayLarge` | 57px / w700 |
| `AppText.displayMedium` | `app_text.dart:43` | `tt.displayMedium` | 45px / w600 |
| `AppText.displaySmall` | `app_text.dart:48` | `tt.displaySmall` | 36px / w600 |
| `AppText.headlineLarge` | `app_text.dart:57` | `tt.headlineLarge` | 32px / w700 |
| `AppText.headlineMedium` | `app_text.dart:62` | `tt.headlineMedium` | 28px / w700 |
| `AppText.headlineSmall` | `app_text.dart:67` | `tt.headlineSmall` | 24px / w700 |
| `AppText.titleLarge` | `app_text.dart:76` | `tt.titleLarge` | 22px / w700 |
| `AppText.titleMedium` | `app_text.dart:81` | `tt.titleMedium` | 16px / w700 |
| `AppText.titleSmall` | `app_text.dart:86` | `tt.titleSmall` | 14px / w700 |
| `AppText.bodyLarge` | `app_text.dart:95` | `tt.bodyLarge` | 16px / w400 |
| `AppText.bodyMedium` | `app_text.dart:100` | `tt.bodyMedium` | 14px / w400 |
| `AppText.bodySmall` | `app_text.dart:105` | `tt.bodySmall` | 12px / w400 |
| `AppText.labelLarge` | `app_text.dart:114` | `tt.labelLarge` | 14px / w700 |
| `AppText.labelMedium` | `app_text.dart:119` | `tt.labelMedium` | 12px / w700 |
| `AppText.labelSmall` | `app_text.dart:124` | `tt.labelSmall` | 11px / w700 |

## Dashboard Widgets

| Widget | File:Line | Current Pattern | Target Pattern |
|--------|-----------|-----------------|----------------|
| `DashboardStatCard` | `dashboard_stat_card.dart:6` | `Container` + `BoxDecoration` + `Text` | `AppGlassCard` + `AppText` |
| `BudgetOverviewCard` | `budget_overview_card.dart:8` | `Container` + `LinearProgressIndicator` | `AppGlassCard` + `AppProgressBar` |
| `TrackedItemRow` | `tracked_item_row.dart:8` | `Container` + `LinearProgressIndicator` | `AppGlassCard` + `AppProgressBar` |
| `AlertItemRow` | `alert_item_row.dart:7` | `Container` + no progress bar | `AppGlassCard` + `AppProgressBar` |

## Weather Feature

| Symbol | File:Line | Status |
|--------|-----------|--------|
| `WeatherService` | `lib/features/weather/services/weather_service.dart:27` | VERIFIED |
| `WeatherServiceInterface` | `lib/features/weather/domain/weather_service_interface.dart:5` | VERIFIED |
| `WeatherData` | `lib/features/weather/services/weather_service.dart:11` | VERIFIED |
| `WeatherProvider` | — | FLAGGED: Does not exist. Only `Provider<WeatherService>.value` registered in DI |
| `weatherProviders()` | `lib/features/weather/di/weather_providers.dart:6` | VERIFIED — registers `Provider<WeatherService>` only |

## Snackbar Pattern

| Symbol | File:Line | Status |
|--------|-----------|--------|
| `SnackBarHelper` | `lib/shared/utils/snackbar_helper.dart:9` | VERIFIED — centralized helper with showSuccess/showError/showInfo/showWarning |

### Direct snackbar callsites (bypassing SnackBarHelper)

| File:Line | Status |
|-----------|--------|
| `lib/features/settings/presentation/screens/help_support_screen.dart` | VERIFIED — uses ScaffoldMessenger directly |
| `lib/features/settings/presentation/screens/consent_screen.dart` | VERIFIED — uses ScaffoldMessenger directly |
| `lib/features/settings/presentation/screens/legal_document_screen.dart` | VERIFIED — uses ScaffoldMessenger directly |
| `lib/features/projects/presentation/widgets/add_equipment_dialog.dart` | Additional — uses ScaffoldMessenger directly |
| `lib/features/projects/presentation/widgets/add_location_dialog.dart` | Additional — uses ScaffoldMessenger directly |
| `lib/features/entries/presentation/screens/entry_editor_screen.dart` | Additional — uses ScaffoldMessenger directly |
| `lib/features/entries/presentation/controllers/pdf_data_builder.dart` | Additional — uses ScaffoldMessenger directly |
| `lib/core/router/scaffold_with_nav_bar.dart` | Additional — uses ScaffoldMessenger directly |

**Note**: Audit identified 3 files but actual grep shows 10 files with direct ScaffoldMessenger/SnackBar usage. The centralized `SnackBarHelper` is used by some files but not all.

## ValueKey Inline Usages

| File:Line | Usage | Status |
|-----------|-------|--------|
| `lib/core/router/routes/project_routes.dart:24` | `key: ValueKey(projectId)` | VERIFIED |
| `lib/features/gallery/presentation/screens/gallery_screen.dart:374` | `key: ValueKey('entry_dropdown_${...}')` | VERIFIED |
| `lib/features/pdf/presentation/screens/mp_import_preview_screen.dart:190` | `key: ValueKey('mp_match_card_${...}')` | VERIFIED |

## Router Transitions

| File:Line | Current | Status |
|-----------|---------|--------|
| `lib/core/router/app_router.dart:107` | `NoTransitionPage(child: ProjectDashboardScreen())` | VERIFIED |
| `lib/core/router/app_router.dart:113` | `NoTransitionPage(child: HomeScreen())` | VERIFIED |
| `lib/core/router/app_router.dart:119` | `NoTransitionPage(child: ProjectListScreen())` | VERIFIED |
| `lib/core/router/app_router.dart:125` | `NoTransitionPage(child: SettingsScreen())` | VERIFIED |

## Quantitative Counts (Verified via Grep)

| Pattern | Count | Files | Audit Claimed |
|---------|-------|-------|---------------|
| `TextStyle(` in lib/ | 215 | 50 | 125 |
| `AlertDialog(` in lib/ | 48 | 30 | 62 |
| `showDialog(` in lib/ | 19 | 15 | 19 |
| `showModalBottomSheet(` in lib/ | 8 prod | 8 | 8 |
| `ScaffoldMessenger/SnackBar(` in lib/ | varies | 10 | 3 |
| `ValueKey(` in lib/ (excl driver) | 3 | 3 | 3 |
| `NoTransitionPage` in router | 4 | 1 | — |

**FLAGGED**: TextStyle count is 215, not 125 as the audit reported. Snackbar direct usages are 10 files, not 3.

## Lint Rules for Modified Files

All files being modified are in `*/presentation/*` paths. Active rules:
- **A3**: No raw SQL
- **A5**: No datasource imports
- **A8**: No service construction in widgets
- **A13**: No hardcoded `Colors.*`
- **D5**: Mounted check required after async

No new files are being created — this is purely a migration of existing widgets to design-system components.
