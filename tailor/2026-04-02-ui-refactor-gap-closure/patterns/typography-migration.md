# Pattern: Typography Migration

## How We Do It
The app should use `AppText.*` factories (from `lib/core/design_system/app_text.dart`) instead of raw `Text(style: TextStyle(...))` or `Text(style: tt.bodyMedium!.copyWith(...))`. Each `AppText` factory maps 1:1 to a Material 3 textTheme slot.

## Common Migration Patterns

### Simple text with theme slot
```dart
// BEFORE
Text('Hello', style: tt.bodyMedium)
// AFTER
AppText.bodyMedium('Hello')
```

### Text with color override
```dart
// BEFORE
Text('Hello', style: tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant))
// AFTER
AppText.bodyMedium('Hello', color: cs.onSurfaceVariant)
```

### Text with maxLines/overflow
```dart
// BEFORE
Text('Long text', style: tt.bodySmall, maxLines: 1, overflow: TextOverflow.ellipsis)
// AFTER
AppText.bodySmall('Long text', maxLines: 1, overflow: TextOverflow.ellipsis)
```

### Text with additional styling (letterSpacing, fontWeight)
AppText does NOT support `letterSpacing` or `fontWeight` overrides — it enforces the textTheme slot exactly. For cases where `copyWith(letterSpacing: ...)` is used:
- If the letterSpacing is purely decorative → drop it, use plain `AppText.*`
- If the letterSpacing is semantic (e.g., section headers) → use `AppSectionHeader` which handles its own letterSpacing
- If the fontWeight differs from the slot → choose the correct slot (e.g., `titleMedium` is w700, `bodyMedium` is w400)

### Cases where AppText does NOT apply
- `RichText` / `TextSpan` compositions — keep as-is
- `TextFormField` decoration labels — handled by `AppTextField`
- Button text — handled by button theme
- `AppBar` title text — handled by app bar theme

## Slot Selection Guide

| Current Pattern | Select |
|----------------|--------|
| `tt.displaySmall` or 36px heading | `AppText.displaySmall` |
| `tt.titleLarge` or 22px title | `AppText.titleLarge` |
| `tt.titleMedium` or 16px bold | `AppText.titleMedium` |
| `tt.titleSmall` or 14px bold | `AppText.titleSmall` |
| `tt.bodyLarge` or 16px regular | `AppText.bodyLarge` |
| `tt.bodyMedium` or 14px regular | `AppText.bodyMedium` |
| `tt.bodySmall` or 12px regular | `AppText.bodySmall` |
| `tt.labelLarge` or 14px bold button | `AppText.labelLarge` |
| `tt.labelMedium` or 12px bold chip | `AppText.labelMedium` |
| `tt.labelSmall` or 11px bold badge | `AppText.labelSmall` |

## Imports
```dart
import 'package:construction_inspector/core/design_system/design_system.dart';
```
