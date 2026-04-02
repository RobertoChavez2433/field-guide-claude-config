# Pattern: Modal Migration

## How We Do It
All modals should use the design system wrappers:
- **Dialogs**: `AppDialog.show` replaces `showDialog` + `AlertDialog`
- **Bottom sheets**: `AppBottomSheet.show` replaces `showModalBottomSheet`

Both wrappers handle theming, glass styling, and consistent layout automatically.

## Dialog Migration Exemplar

### Before (raw pattern)
```dart
final result = await showDialog<bool>(
  context: context,
  builder: (dialogContext) {
    return AlertDialog(
      title: Text('Delete Item?'),
      content: Text('This cannot be undone.'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: Text('Cancel')),
        ElevatedButton(onPressed: () => Navigator.pop(dialogContext, true), child: Text('Delete')),
      ],
    );
  },
);
```

### After (design system)
```dart
final result = await AppDialog.show<bool>(
  context,
  title: 'Delete Item?',
  content: Text('This cannot be undone.'),
  actions: [
    TextButton(onPressed: () => Navigator.pop(context, false), child: Text('Cancel')),
    ElevatedButton(onPressed: () => Navigator.pop(context, true), child: Text('Delete')),
  ],
);
```

## Bottom Sheet Migration Exemplar

### Before (raw pattern)
```dart
showModalBottomSheet(
  context: context,
  isScrollControlled: true,
  builder: (ctx) => Column(
    mainAxisSize: MainAxisSize.min,
    children: [...],
  ),
);
```

### After (design system)
```dart
AppBottomSheet.show(
  context,
  builder: (ctx) => Column(
    mainAxisSize: MainAxisSize.min,
    children: [...],
  ),
);
```

## Files Requiring Dialog Migration (30 files, 48 AlertDialog occurrences)

### High-traffic dialog files (multiple AlertDialogs)
| File | Count |
|------|-------|
| `lib/features/settings/presentation/widgets/sign_out_dialog.dart` | 4 |
| `lib/features/todos/presentation/screens/todos_screen.dart` | 3 |
| `lib/shared/widgets/confirmation_dialog.dart` | 3 |
| `lib/features/entries/presentation/screens/entry_editor_screen.dart` | 3 |
| `lib/features/settings/presentation/screens/personnel_types_screen.dart` | 3 |
| `lib/features/entries/presentation/widgets/contractor_editor_widget.dart` | 2 |
| `lib/features/entries/presentation/widgets/entry_forms_section.dart` | 2 |
| `lib/features/forms/presentation/screens/form_viewer_screen.dart` | 2 |
| `lib/features/forms/presentation/screens/forms_list_screen.dart` | 2 |
| `lib/features/settings/presentation/screens/admin_dashboard_screen.dart` | 2 |
| `lib/features/settings/presentation/screens/trash_screen.dart` | 2 |
| `lib/features/settings/presentation/screens/settings_screen.dart` | 2 |

### Single-AlertDialog files (18 files with 1 each)
These are straightforward 1:1 replacements.

## Files Requiring Bottom Sheet Migration (8 production files)

| File | Notes |
|------|-------|
| `lib/features/projects/presentation/screens/project_list_screen.dart` | Project actions sheet |
| `lib/features/entries/presentation/screens/home_screen.dart` | Entry actions |
| `lib/features/settings/presentation/screens/admin_dashboard_screen.dart` | Admin actions |
| `lib/features/quantities/presentation/widgets/bid_item_detail_sheet.dart` | Bid item details |
| `lib/features/projects/presentation/widgets/project_switcher.dart` | Project switcher |
| `lib/features/pdf/presentation/widgets/extraction_banner.dart` | PDF extraction |
| `lib/features/gallery/presentation/screens/gallery_screen.dart` | Gallery filter |
| `lib/features/forms/presentation/screens/form_gallery_screen.dart` | Form gallery |

## Imports
```dart
import 'package:construction_inspector/core/design_system/design_system.dart';
```
