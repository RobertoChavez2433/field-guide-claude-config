# Pattern: Snackbar Helper

## How We Do It
The centralized snackbar helper lives at `lib/shared/utils/snackbar_helper.dart`. It provides typed static methods (`showSuccess`, `showError`, `showInfo`, `showWarning`, `showWithAction`, `showErrorWithAction`) that use semantic theme colors. All snackbar usage should go through this helper.

## Exemplar

### SnackBarHelper (lib/shared/utils/snackbar_helper.dart:9)
Static utility class with 6 methods. Uses `FieldGuideColors.of(context)` for success/warning colors and `Theme.of(context).colorScheme` for error/primary colors.

## Files Bypassing SnackBarHelper (need migration)

| File | Current Usage |
|------|---------------|
| `lib/features/settings/presentation/screens/help_support_screen.dart` | Direct `ScaffoldMessenger.of(context).showSnackBar(...)` |
| `lib/features/settings/presentation/screens/consent_screen.dart` | Direct `ScaffoldMessenger.of(context).showSnackBar(...)` |
| `lib/features/settings/presentation/screens/legal_document_screen.dart` | Direct `ScaffoldMessenger.of(context).showSnackBar(...)` |
| `lib/features/projects/presentation/widgets/add_equipment_dialog.dart` | Direct usage |
| `lib/features/projects/presentation/widgets/add_location_dialog.dart` | Direct usage |
| `lib/features/entries/presentation/screens/entry_editor_screen.dart` | Direct usage |
| `lib/features/entries/presentation/controllers/pdf_data_builder.dart` | Direct usage |
| `lib/core/router/scaffold_with_nav_bar.dart` | Direct usage |

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `SnackBarHelper.showSuccess` | `snackbar_helper.dart:13` | `static void showSuccess(BuildContext context, String message)` | Completed actions |
| `SnackBarHelper.showError` | `snackbar_helper.dart:30` | `static void showError(BuildContext context, String message, {Duration? duration})` | Failures |
| `SnackBarHelper.showInfo` | `snackbar_helper.dart:81` | `static void showInfo(BuildContext context, String message)` | Neutral notifications |
| `SnackBarHelper.showWarning` | `snackbar_helper.dart:97` | `static void showWarning(BuildContext context, String message)` | Caution messages |
| `SnackBarHelper.showWithAction` | `snackbar_helper.dart:114` | `static void showWithAction(BuildContext context, String message, String actionLabel, VoidCallback onAction)` | Undo-style actions |
| `SnackBarHelper.showErrorWithAction` | `snackbar_helper.dart:52` | `static ScaffoldFeatureController showErrorWithAction(context, message, {actionLabel, onAction, duration})` | Error with action + controller |

## Imports
```dart
import 'package:construction_inspector/shared/utils/snackbar_helper.dart';
// or via barrel:
import 'package:construction_inspector/shared/shared.dart';
```
