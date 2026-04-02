# Pattern: Confirmation Dialog

## How We Do It
Shared confirmation dialogs are top-level functions in `lib/shared/widgets/confirmation_dialog.dart`, exported via `shared.dart`. They use `showDialog` + raw `AlertDialog` with `TestingKeys` for E2E automation. The migration replaces the internal `AlertDialog` construction with `AppDialog.show` while preserving the public function signatures.

## Exemplars

### showConfirmationDialog (lib/shared/widgets/confirmation_dialog.dart:7)
Generic confirmation with customizable title, message, optional icon, and destructive styling. Returns `bool`. Currently builds raw `AlertDialog` with `TestingKeys.confirmationDialog` key.

### showDeleteConfirmationDialog (lib/shared/widgets/confirmation_dialog.dart:61)
Specialized delete confirmation with error-colored delete button. Returns `bool`. Also builds raw `AlertDialog`.

### showUnsavedChangesDialog (lib/shared/widgets/confirmation_dialog.dart:124)
Save/discard/cancel three-way dialog. Returns `bool?` (true=discard, false=save, null=cancel).

## Migration Strategy

**Critical constraint**: `AppDialog.show` takes `title` as a `String` and renders it via `AppText.titleLarge`. But the confirmation dialogs use `Row(children: [Icon, Text(title)])` for icon+title layout. Two options:

1. **Pass the icon+title Row as the `content` and use a simple title string** — Breaks the layout pattern
2. **Extend AppDialog.show to accept an optional `icon` parameter** — Better approach, keeps the API clean

Recommended: Add `IconData? icon` and `Color? iconColor` params to `AppDialog.show`, then the confirmation dialog migration is straightforward.

**Testing keys must be preserved**: `TestingKeys.confirmationDialog`, `TestingKeys.cancelDialogButton`, `TestingKeys.deleteConfirmButton`, `TestingKeys.confirmationDialogCancel` are used by E2E tests.

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `showConfirmationDialog` | `confirmation_dialog.dart:7` | `Future<bool> showConfirmationDialog({context, title, message, confirmText?, cancelText?, isDestructive?, icon?, iconColor?})` | Any confirm/cancel prompt |
| `showDeleteConfirmationDialog` | `confirmation_dialog.dart:61` | `Future<bool> showDeleteConfirmationDialog({context, itemName, customMessage?})` | Delete confirmation |
| `showUnsavedChangesDialog` | `confirmation_dialog.dart:124` | `Future<bool?> showUnsavedChangesDialog({context, isEditMode?})` | Unsaved changes prompt |

## Imports
```dart
import 'package:construction_inspector/shared/shared.dart'; // includes confirmation_dialog
import 'package:construction_inspector/core/design_system/design_system.dart'; // for AppDialog.show
```
