# Pattern: Design System Widget

## How We Do It
All design system components live in `lib/core/design_system/` and are exported via the `design_system.dart` barrel. Each component is a `StatelessWidget` that reads from `Theme.of(context)`, `FieldGuideColors.of(context)`, and `DesignConstants` — never hardcoding colors or dimensions. Components have docstrings showing usage examples.

## Exemplars

### AppGlassCard (lib/core/design_system/app_glass_card.dart:18)
Core glassmorphic card with optional accent color tinting. Uses `FieldGuideColors.surfaceGlass` for background, `DesignConstants.radiusMedium` for corners, and supports `accentColor` for a 3px left border. Has static `buildGlassDecoration()` helper for reuse by other widgets.

Key API:
```dart
const AppGlassCard({
  required this.child,
  this.accentColor,      // 3px left border tint
  this.onTap,
  this.onLongPress,
  this.padding,          // default: space4
  this.margin,           // default: symmetric vertical 4px
  this.borderRadius,     // default: radiusMedium (12)
  this.elevation,        // default: elevationLow (2)
  this.selected = false, // highlighted state
})
```

### AppDialog (lib/core/design_system/app_dialog.dart:21)
Static-only class with `show<T>()` method. Wraps `showDialog` + `AlertDialog` with `AppText.titleLarge` for title. Inherits all styling from `dialogTheme`.

Key API:
```dart
static Future<T?> show<T>(
  BuildContext context, {
  required String title,
  required Widget content,
  List<Widget>? actions,      // default: single "OK" button
  bool barrierDismissible = true,
})
```

### AppBottomSheet (lib/core/design_system/app_bottom_sheet.dart:23)
Static-only class with `show<T>()` method. Wraps `showModalBottomSheet` with glass background (`surfaceElevated`), `AppDragHandle`, and bottom safe area. Uses `DesignConstants.radiusXLarge` for top corners.

Key API:
```dart
static Future<T?> show<T>(
  BuildContext context, {
  required Widget Function(BuildContext) builder,
  bool isScrollControlled = true,
})
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `AppGlassCard.buildGlassDecoration` | `app_glass_card.dart:60` | `static BoxDecoration buildGlassDecoration({surfaceColor, borderColor, radius, shadowColor, blurRadius})` | When other widgets need the same glass decoration without the full card |
| `AppDialog.show` | `app_dialog.dart:27` | `static Future<T?> show<T>(context, {title, content, actions?, barrierDismissible?})` | Replace all raw `showDialog` + `AlertDialog` combos |
| `AppBottomSheet.show` | `app_bottom_sheet.dart:30` | `static Future<T?> show<T>(context, {builder, isScrollControlled?})` | Replace all raw `showModalBottomSheet` calls |

## Imports
```dart
import 'package:construction_inspector/core/design_system/design_system.dart';
```
Single barrel import provides all components.
