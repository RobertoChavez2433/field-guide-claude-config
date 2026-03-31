# Pattern: Three-Tier Color System

## How We Do It
Colors are organized in three tiers. Tier 1 is Material 3's `Theme.of(context).colorScheme.*` for standard tokens (primary, error, surface variants). Tier 2 is `FieldGuideColors.of(context).*` — a ThemeExtension with 16 semantic colors that adapt across dark/light/high-contrast themes. Tier 3 is `AppColors.*` — static constants for domain colors that intentionally don't change with theme (weather icons, entry status badges). The deprecated `AppTheme.*` color constants (797 violations across 76 files) must all be replaced with the appropriate tier.

## Exemplars

### FieldGuideColors (lib/core/theme/field_guide_colors.dart:12)
ThemeExtension with const instances for dark, light, high-contrast. Static accessor `FieldGuideColors.of(context)` mirrors `Theme.of(context)` pattern. Falls back to dark if extension missing.

16 semantic colors: `surfaceElevated`, `surfaceGlass`, `surfaceBright`, `textTertiary`, `textInverse`, `statusSuccess`, `statusWarning`, `statusInfo`, `warningBackground`, `warningBorder`, `shadowLight`, `gradientStart`, `gradientEnd`, `accentAmber`, `accentOrange`, `dragHandleColor`.

### AppColors (lib/core/theme/colors.dart:5)
Static constants class. Weather colors (`weatherSunny`, `weatherCloudy`, etc.), entry status badges (`entryDraft`, `entryComplete`, `entrySynced`), photo viewer, gradients. Two utility methods: `getWeatherColor(String)`, `getEntryStatusColor(String)`.

### AppTheme DEPRECATED (lib/core/theme/app_theme.dart:9)
Has @Deprecated annotations on ~40+ members. Each annotation specifies the replacement. Example:
- `@Deprecated('Use Theme.of(context).colorScheme.primary instead') static const Color primaryCyan = ...`
- `@Deprecated('Use FieldGuideColors.of(context).statusSuccess instead') static const Color successGreen = ...`

Still has 3 theme getters (`darkTheme`, `lightTheme`, `highContrastTheme`) and 3 gradient/decoration helpers that are NOT deprecated (still used).

## Migration Map (AppTheme → Correct Tier)

| AppTheme Member | Replacement | Tier |
|-----------------|-------------|------|
| `primaryCyan` | `Theme.of(context).colorScheme.primary` | 1 |
| `primaryBlue` | `Theme.of(context).colorScheme.tertiary` or `AppColors.primaryBlue` | 3 |
| `successGreen` | `FieldGuideColors.of(context).statusSuccess` | 2 |
| `warningOrange` | `FieldGuideColors.of(context).statusWarning` | 2 |
| `errorRed` | `Theme.of(context).colorScheme.error` | 1 |
| `cardBackground` | `Theme.of(context).colorScheme.surfaceContainerHigh` | 1 |
| `borderColor` | `Theme.of(context).colorScheme.outlineVariant` | 1 |
| `surfaceHighest` | `Theme.of(context).colorScheme.surfaceContainerHighest` | 1 |
| `textPrimary` | `Theme.of(context).colorScheme.onSurface` | 1 |

(Full mapping derivable from @Deprecated annotations in app_theme.dart)

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `FieldGuideColors.of` | field_guide_colors.dart:149 | `static FieldGuideColors of(BuildContext context)` | Access semantic colors |
| `AppColors.getWeatherColor` | colors.dart:183 | `static Color getWeatherColor(String weather)` | Weather condition → color |
| `AppColors.getEntryStatusColor` | colors.dart:203 | `static Color getEntryStatusColor(String status)` | Entry status → color |
| `AppTheme.getPrimaryGradient` | app_theme.dart:1731 | `static LinearGradient getPrimaryGradient({...})` | NOT deprecated, still used |
| `AppTheme.getGlassmorphicDecoration` | app_theme.dart:1755 | `static BoxDecoration getGlassmorphicDecoration({...})` | NOT deprecated, still used |

## Imports
```dart
// Tier 1 — no import needed, available via Theme.of(context)
// Tier 2:
import 'package:construction_inspector/core/theme/field_guide_colors.dart';
// Tier 3:
import 'package:construction_inspector/core/theme/colors.dart';
// DEPRECATED — remove this import:
import 'package:construction_inspector/core/theme/app_theme.dart';
```

## Lint Rules Targeting This Pattern
- A12: `no_deprecated_app_theme` — no AppTheme.* color constants (ERROR)
- A13: `no_hardcoded_colors` — no Colors.* in presentation except transparent (WARNING)
