# UI Refactor — Comprehensive Implementation Plan

**Date**: 2026-03-06
**Branch**: `feat/ui-refactor` (off `main`)
**Design Language**: T Vivid
**Scope**: Full rewrite of all 38 screens, 80+ widgets, ~40 modal surfaces
**Reference Docs**:
- `.claude/plans/2026-03-06-ui-refactor-decisions.md` — locked decisions
- `.claude/docs/ui-refactor-reference-2026-03-06.md` — per-file violation registry
- `.claude/docs/ui-audit-theme-tokens-2026-03-06.md` — token inventory + gap analysis
- `.claude/plans/ui-dependency-map.md` — provider/widget/route maps

---

## Phase 1: Foundation — Theme Tokens + Design System Components

**Goal**: Fill all token gaps, build the 20-component design system library, and establish the T Vivid foundation that every subsequent phase depends on.

**Commit**: `feat(design-system): add T Vivid component library and fill token gaps`

### Phase 1.A: Fill Theme Token Gaps

All changes in this subphase target three files:
- `lib/core/theme/colors.dart` (add new color constants to `AppColors`)
- `lib/core/theme/design_constants.dart` (add new radius/icon size constants)
- `lib/core/theme/app_theme.dart` (add re-exports to `AppTheme` facade)

#### Step 1.A.1: Add new color tokens to `AppColors` in `colors.dart`

Add these static constants to the `AppColors` class:

```dart
static const Color statusNeutral = Color(0xFF8B949E);      // same as textSecondary — inactive/never-synced
static const Color warningBackground = Color(0x1AFFB300);   // amber at 10% opacity — warning chip bg
static const Color warningBorder = Color(0x33FFB300);       // amber at 20% opacity — warning chip border
static const Color shadowLight = Color(0x1A000000);         // black at 10% — standard card/footer shadow
static const Color photoViewerBg = Color(0xFF000000);       // photo viewer scaffold background
static const Color photoViewerText = Color(0xFFFFFFFF);     // photo viewer primary text
static const Color photoViewerTextMuted = Color(0xB3FFFFFF); // white70 — photo viewer secondary
static const Color photoViewerTextDim = Color(0x8AFFFFFF);  // white54 — photo viewer tertiary
static const Color tVividBackground = Color(0xFF050810);    // T Vivid near-black scaffold bg
static const Color sectionQuantities = Color(0xFF26C6DA);   // teal — quantities section accent
static const Color sectionPhotos = Color(0xFFBA68C8);        // purple — photos section accent
static const Color projectNumberText = Color(0xFFCCCCCC);    // visible project number text
```

#### Step 1.A.2: Add new radius and icon size tokens to `DesignConstants` in `design_constants.dart`

Add these static constants to the `DesignConstants` class:

```dart
// Radius
static const double radiusXSmall = 4.0;   // chips, badges, small elements
static const double radiusCompact = 10.0; // project list cards, hub widgets

// Icon sizes
static const double iconSizeSmall = 18.0;  // small inline icons
static const double iconSizeMedium = 24.0; // standard Material default
static const double iconSizeLarge = 32.0;  // large state icons
static const double iconSizeXL = 48.0;     // empty state, hero icons
```

#### Step 1.A.3: Add all re-exports to `AppTheme` facade in `app_theme.dart`

Add these re-exports to the `AppTheme` class (in the static constants section alongside existing re-exports):

**Colors** (from AppColors):
```dart
static const Color statusNeutral = AppColors.statusNeutral;
static const Color warningBackground = AppColors.warningBackground;
static const Color warningBorder = AppColors.warningBorder;
static const Color shadowLight = AppColors.shadowLight;
static const Color photoViewerBg = AppColors.photoViewerBg;
static const Color photoViewerText = AppColors.photoViewerText;
static const Color photoViewerTextMuted = AppColors.photoViewerTextMuted;
static const Color photoViewerTextDim = AppColors.photoViewerTextDim;
static const Color tVividBackground = AppColors.tVividBackground;
static const Color overlayDark = AppColors.overlayDark;           // already defined, just not re-exported
static const List<Color> gradientSuccess = AppColors.gradientSuccess; // already defined, just not re-exported
static const Color sectionQuantities = AppColors.sectionQuantities;
static const Color sectionPhotos = AppColors.sectionPhotos;
static const Color projectNumberText = AppColors.projectNumberText;
static const Color entryDraft = AppColors.entryDraft;
static const Color entryComplete = AppColors.entryComplete;
static const Color entrySubmitted = AppColors.entrySubmitted;
static const Color entrySynced = AppColors.entrySynced;
```

**Spacing** (already exist in DesignConstants, just add re-exports):
```dart
static const double space12 = DesignConstants.space12;  // 48.0
static const double space16 = DesignConstants.space16;  // 64.0
```

> **CAUTION**: `space12` = 48.0 (12th step in 4px grid), NOT 12px. For 12px spacing, use `space3`. Similarly `space16` = 64.0, not 16px. For 16px spacing, use `space4`.

**Radius**:
```dart
static const double radiusXSmall = DesignConstants.radiusXSmall;   // 4.0
static const double radiusCompact = DesignConstants.radiusCompact; // 10.0
```

**Icon sizes**:
```dart
static const double iconSizeSmall = DesignConstants.iconSizeSmall;   // 18.0
static const double iconSizeMedium = DesignConstants.iconSizeMedium; // 24.0
static const double iconSizeLarge = DesignConstants.iconSizeLarge;   // 32.0
static const double iconSizeXL = DesignConstants.iconSizeXL;         // 48.0
```

**Animation** (already exist in DesignConstants, just add re-exports):
```dart
static const Duration animationPageTransition = DesignConstants.animationPageTransition; // 350ms
static const Curve curveDecelerate = DesignConstants.curveDecelerate; // Curves.easeOut
static const Curve curveAccelerate = DesignConstants.curveAccelerate; // Curves.easeIn
static const Curve curveBounce = DesignConstants.curveBounce;         // Curves.elasticOut
```

#### Step 1.A.4: Update T Vivid background in ThemeData builders

In `app_theme.dart`, update the `darkTheme` builder's `scaffoldBackgroundColor` from `AppColors.backgroundDark` (#0A0E14) to `AppColors.tVividBackground` (#050810).

Do the same for any `ColorScheme.dark()` `surface` or `background` values that reference `backgroundDark` in the dark theme builder (lines 130-764). Keep `lightTheme` and `highContrastTheme` unchanged.

**Expected result**: `AppTheme` now exports 17 new tokens. All three theme files compile. No existing code breaks because these are additive-only changes.

#### Step 1.A.5: Create `FieldGuideColors` ThemeExtension

Create `lib/core/theme/field_guide_colors.dart` — a `ThemeExtension<FieldGuideColors>` that provides custom semantic colors with per-theme values. This ensures all design system components are truly theme-aware across dark, light, and high-contrast themes.

**Why**: Static `AppTheme.*` color constants resolve to a single dark-theme value regardless of which theme is active. For true theme-awareness, components must read colors from `Theme.of(context)`. Material 3's `ColorScheme` covers standard slots (primary, error, surface, onSurface, outline), but app-specific colors need a custom extension.

**Fields** (16 custom color properties):

| Field | Dark | Light | HC | Purpose |
|-------|------|-------|-----|---------|
| `surfaceElevated` | `#1C2128` | `#FFFFFF` | `#1E1E1E` | Cards, dialogs, elevated containers |
| `surfaceGlass` | `#99161B22` | `#CCFFFFFF` | `#CC121212` | Glassmorphic overlays |
| `surfaceBright` | `#444C56` | `#E2E8F0` | `#333333` | Disabled/active elements |
| `textTertiary` | `#6E7681` | `#94A3B8` | `#808080` | Disabled text, hints |
| `textInverse` | `#0A0E14` | `#FFFFFF` | `#000000` | Text on primary-colored bg |
| `statusSuccess` | `#4CAF50` | `#4CAF50` | `#00FF00` | Success states |
| `statusWarning` | `#FF9800` | `#FF9800` | `#FFAA00` | Warning states |
| `statusInfo` | `#2196F3` | `#2196F3` | `#00FFFF` | Info states |
| `warningBackground` | `#1AFFB300` | `#1AFF9800` | `#1AFFAA00` | Warning chip bg |
| `warningBorder` | `#33FFB300` | `#33FF9800` | `#33FFAA00` | Warning chip border |
| `shadowLight` | `#1A000000` | `#0D000000` | `transparent` | Subtle card shadow |
| `gradientStart` | `primaryCyan` | `primaryBlue` | `hcPrimary` | Primary gradient start |
| `gradientEnd` | `primaryBlue` | `primaryDark` | `hcPrimary` | Primary gradient end |
| `accentAmber` | `#FFB300` | `#FFB300` | `#FFFF00` | Amber accent |
| `accentOrange` | `#FF6F00` | `#FF6F00` | `#FFAA00` | Orange accent |
| `dragHandleColor` | `surfaceHighlight` | `lightSurfaceHighlight` | `#FFFFFF` | Bottom sheet drag handle |

Implementation:
- Class: `FieldGuideColors extends ThemeExtension<FieldGuideColors>`
- Include `copyWith()` and `lerp()` methods (required by ThemeExtension)
- Provide `static const dark`, `static const light`, `static const highContrast` named constructors
- Provide `static FieldGuideColors of(BuildContext context)` convenience accessor
- Add to barrel export in `lib/core/theme/theme.dart`

**Color access patterns** for all components:
```dart
final cs = Theme.of(context).colorScheme;    // M3 standard colors
final tt = Theme.of(context).textTheme;       // Typography
final fg = FieldGuideColors.of(context);      // App-specific custom colors
```

**Mapping rules** (used by all 20 component specs in Phases 1.B–1.E):

| Old (static) | New (theme-aware) |
|---|---|
| `AppTheme.surfaceElevated` | `fg.surfaceElevated` |
| `AppTheme.surfaceHighlight` | `cs.outline` |
| `AppTheme.surfaceDark` | `cs.surface` |
| `AppTheme.primaryCyan` | `cs.primary` |
| `AppTheme.textPrimary` | `cs.onSurface` |
| `AppTheme.textSecondary` | `cs.onSurfaceVariant` |
| `AppTheme.textTertiary` | `fg.textTertiary` |
| `AppTheme.textInverse` | `fg.textInverse` |
| `AppTheme.accentAmber` | `fg.accentAmber` |
| `AppTheme.statusError` | `cs.error` |
| `AppTheme.statusSuccess` | `fg.statusSuccess` |
| `AppTheme.statusWarning` | `fg.statusWarning` |
| `AppTheme.warningBackground` | `fg.warningBackground` |
| `AppTheme.warningBorder` | `fg.warningBorder` |
| `AppTheme.shadowLight` | `fg.shadowLight` |
| `Colors.black.withOpacity(*)` (shadows) | `fg.shadowLight` |

**Theme-independent constants** (remain as static `AppTheme.*`): All spacing (`space*`), radius (`radius*`), icon sizes (`iconSize*`), animation durations/curves, elevation values. Also domain-specific colors that are the same across all themes: weather colors, entry status colors, photo viewer colors.

**Components that should INHERIT from Material theme** (do NOT set colors manually):
- `AppTextField` → inherits from `inputDecorationTheme`
- `AppToggle` → inherits from `switchTheme`
- `AppDialog` → inherits from `dialogTheme`
- `AppBottomSheet` → inherits from `bottomSheetTheme`
- `AppLoadingState` → inherits from `progressIndicatorTheme`
- `AppScaffold` → inherits `scaffoldBackgroundColor`

#### Step 1.A.6: Register `FieldGuideColors` on all 3 ThemeData builders

In `app_theme.dart`, add the `extensions` parameter to each ThemeData builder:

- `darkTheme`: `extensions: const [FieldGuideColors.dark]`
- `lightTheme`: `extensions: const [FieldGuideColors.light]`
- `highContrastTheme`: `extensions: const [FieldGuideColors.highContrast]`

**Expected result**: `FieldGuideColors.of(context)` returns the correct color set for the active theme. All 20 design system components use this instead of static `AppTheme.*` color constants.

---

### Phase 1.B: Build Atomic Layer Components

Create directory `lib/core/design_system/` and all atomic components.

#### Step 1.B.1: Create `lib/core/design_system/app_text.dart`

> Already theme-aware. Callers should pass `cs.onSurfaceVariant` instead of `AppTheme.textSecondary` for secondary text color.

```dart
import 'package:flutter/material.dart';

/// Enforces textTheme slots — eliminates inline TextStyle throughout the app.
/// Usage: AppText.bodySmall('Caption text', color: cs.onSurfaceVariant)
class AppText extends StatelessWidget {
  final String text;
  final TextStyle? Function(TextTheme) _styleResolver;
  final Color? color;
  final TextOverflow? overflow;
  final int? maxLines;
  final TextAlign? textAlign;
  final FontWeight? fontWeight;

  const AppText._(
    this.text,
    this._styleResolver, {
    this.color,
    this.overflow,
    this.maxLines,
    this.textAlign,
    this.fontWeight,
  });

  factory AppText.displayLarge(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.displayLarge, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.displayMedium(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.displayMedium, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.displaySmall(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.displaySmall, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.headlineLarge(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.headlineLarge, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.headlineMedium(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.headlineMedium, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.headlineSmall(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.headlineSmall, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.titleLarge(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.titleLarge, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.titleMedium(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.titleMedium, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.titleSmall(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.titleSmall, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.bodyLarge(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.bodyLarge, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.bodyMedium(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.bodyMedium, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.bodySmall(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.bodySmall, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.labelLarge(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.labelLarge, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.labelMedium(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.labelMedium, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  factory AppText.labelSmall(String text, {Color? color, TextOverflow? overflow, int? maxLines, TextAlign? textAlign, FontWeight? fontWeight}) =>
      AppText._(text, (t) => t.labelSmall, color: color, overflow: overflow, maxLines: maxLines, textAlign: textAlign, fontWeight: fontWeight);

  @override
  Widget build(BuildContext context) {
    final baseStyle = _styleResolver(Theme.of(context).textTheme);
    return Text(
      text,
      style: baseStyle?.copyWith(
        color: color,
        fontWeight: fontWeight,
      ),
      overflow: overflow,
      maxLines: maxLines,
      textAlign: textAlign,
    );
  }
}
```

#### Step 1.B.2: Create `lib/core/design_system/app_text_field.dart`

Glass-styled `TextFormField` wrapper. Props: `label`, `hint`, `controller`, `validator`, `keyboardType`, `maxLines` (default 1), `onChanged`, `prefixIcon`, `suffixIcon`, `enabled` (default true).

**Inherits from Theme**: Do not specify `fillColor`, border colors, label/hint styles — they are already set per-theme in each ThemeData builder's `inputDecorationTheme`. Only specify structural props (padding, `borderRadius: AppTheme.radiusSmall`, `maxLines`). This ensures correct appearance across dark, light, and high-contrast themes automatically.

#### Step 1.B.3: Create `lib/core/design_system/app_chip.dart`

Colored chip with factory constructors for each accent variant:
- `.cyan()` — accent = `cs.primary`
- `.amber()` — accent = `fg.accentAmber`
- `.green()` — accent = `fg.statusSuccess`
- `.purple()` — accent = `AppTheme.sectionPhotos` (static, domain-specific)
- `.teal()` — accent = `AppTheme.sectionQuantities` (static, domain-specific)
- `.error()` — accent = `cs.error`
- `.neutral()` — accent = `cs.onSurfaceVariant`

Each variant renders: Container with `accentColor.withOpacity(0.1)` background, `accentColor.withOpacity(0.2)` border (1px), `BorderRadius.circular(AppTheme.radiusFull)`, padding `EdgeInsets.symmetric(horizontal: AppTheme.space3, vertical: AppTheme.space1)`.

Content: Row with optional Icon (size `AppTheme.iconSizeSmall`, color = accentColor) + SizedBox(width: AppTheme.space1) + label text style: `tt.labelSmall!.copyWith(color: accentColor)`.

Props: `String label`, `IconData? icon`, `VoidCallback? onTap`, `bool selected` (when selected, background opacity goes to 0.2, border to 0.4).

#### Step 1.B.4: Create `lib/core/design_system/app_progress_bar.dart`

4px gradient progress bar.

Props: `double value` (0.0-1.0), `Color? startColor` (default `fg.gradientStart`), `Color? endColor` (default `fg.gradientEnd`), `double height` (default 4.0).

Implementation: `LayoutBuilder` → Stack:
- Background: Container(height, decoration: BoxDecoration(color: cs.surfaceContainerHighest, borderRadius: AppTheme.radiusFull))
- Foreground: FractionallySizedBox(widthFactor: value.clamp(0,1)) → Container(height, decoration: BoxDecoration(gradient: LinearGradient(colors: [startColor, endColor]), borderRadius: AppTheme.radiusFull))

Animate with `AnimatedFractionallySizedBox` or `TweenAnimationBuilder<double>` using `AppTheme.animationNormal` duration.

#### Step 1.B.5: Create `lib/core/design_system/app_counter_field.dart`

+/- stepper for personnel counts.

Props: `int value`, `ValueChanged<int> onChanged`, `int min` (default 0), `int? max`, `String? label`.

Layout: Row with:
- Optional AppText.labelSmall(label) above
- IconButton(Icons.remove_circle_outline, size: AppTheme.iconSizeMedium, color: value > min ? cs.primary : fg.textTertiary, onPressed: value > min ? () => onChanged(value - 1) : null)
- SizedBox(width: AppTheme.space2)
- AppText.titleMedium(value.toString())
- SizedBox(width: AppTheme.space2)
- IconButton(Icons.add_circle_outline, size: AppTheme.iconSizeMedium, color: max == null || value < max ? cs.primary : fg.textTertiary, onPressed: max == null || value < max ? () => onChanged(value + 1) : null)

Container decoration: fg.surfaceElevated background, cs.outline border, radiusSmall.

#### Step 1.B.6: Create `lib/core/design_system/app_toggle.dart`

Props: `String label`, `String? subtitle`, `bool value`, `ValueChanged<bool> onChanged`, `bool enabled` (default true).

**Inherits from Theme**: Do not specify `activeColor` or `activeTrackColor` — `Switch.adaptive` inherits from `switchTheme`, which is configured per-theme. Only specify label/subtitle using `AppText` widgets. Subtitle color: `cs.onSurfaceVariant`.

Layout: Row with:
- Expanded Column: AppText.bodyMedium(label), if subtitle != null: AppText.bodySmall(subtitle, color: cs.onSurfaceVariant)
- Switch.adaptive(value: value, onChanged: enabled ? onChanged : null)

#### Step 1.B.7: Create `lib/core/design_system/app_icon.dart`

```dart
enum AppIconSize {
  small(18),
  medium(24),
  large(32),
  xl(48);
  final double value;
  const AppIconSize(this.value);
}

class AppIcon extends StatelessWidget {
  final IconData icon;
  final AppIconSize size;
  final Color? color;

  const AppIcon(this.icon, {this.size = AppIconSize.medium, this.color, super.key});

  @override
  Widget build(BuildContext context) => Icon(icon, size: size.value, color: color);
}
```

---

### Phase 1.C: Build Card Layer Components

#### Step 1.C.1: Create `lib/core/design_system/app_glass_card.dart`

Core T Vivid card — the most important component.

Props: `Widget child`, `Color? accentColor`, `EdgeInsets? padding` (default `EdgeInsets.all(AppTheme.space4)`), `double? borderRadius` (default `AppTheme.radiusMedium`), `VoidCallback? onTap`, `bool elevated` (default true).

Implementation:
```dart
final fg = FieldGuideColors.of(context);
final cs = Theme.of(context).colorScheme;
final bgColor = accentColor != null
    ? Color.lerp(fg.surfaceElevated, accentColor, 0.03)!.withOpacity(0.7)
    : fg.surfaceElevated.withOpacity(0.7);
final borderColor = accentColor?.withOpacity(0.1) ?? cs.outline;
final shadowColor = elevated
    ? (accentColor?.withOpacity(0.04) ?? fg.shadowLight)
    : Colors.transparent;

return GestureDetector(
  onTap: onTap,
  child: Container(
    padding: padding,
    decoration: BoxDecoration(
      color: bgColor,
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(color: borderColor, width: 1),
      boxShadow: elevated ? [BoxShadow(color: shadowColor, blurRadius: 24, offset: Offset(0, 2))] : null,
    ),
    child: child,
  ),
);
```

If `onTap` is provided, wrap in `Material(color: Colors.transparent)` + `InkWell` instead of `GestureDetector` to get ripple.

#### Step 1.C.2: Create `lib/core/design_system/app_section_header.dart`

8px spaced-letter header for T Vivid sections.

Props: `String title`, `IconData? icon`, `Color? color` (default `cs.onSurfaceVariant`), `Widget? trailing`.

Layout: Row(children: [
  if icon: AppIcon(icon, size: AppIconSize.small, color: color.withOpacity(0.65)),
  if icon: SizedBox(width: AppTheme.space2),
  Text(title.toUpperCase(), style: textTheme.labelSmall.copyWith(color: color.withOpacity(0.65), letterSpacing: 1.5, fontSize: 11)),
  Spacer(),
  if trailing: trailing,
])

Padding: `EdgeInsets.only(bottom: AppTheme.space3)`.

#### Step 1.C.3: Create `lib/core/design_system/app_list_tile.dart`

Glass-styled list row built on AppGlassCard.

Props: `String title`, `String? subtitle`, `Widget? leading`, `Widget? trailing`, `VoidCallback? onTap`, `Color? accentColor`, `EdgeInsets? contentPadding`.

Implementation: AppGlassCard(accentColor: accentColor, onTap: onTap, padding: contentPadding ?? EdgeInsets.all(AppTheme.space4), child: Row(children: [
  if leading: leading, if leading: SizedBox(width: AppTheme.space3),
  Expanded(Column(crossAxisAlignment: start, children: [
    AppText.bodyLarge(title),
    if subtitle: AppText.bodySmall(subtitle, color: cs.onSurfaceVariant),
  ])),
  if trailing: trailing,
]))

#### Step 1.C.4: Create `lib/core/design_system/app_photo_grid.dart`

Photo thumbnail grid with add button.

Props: `List<dynamic> photos`, `VoidCallback? onAddPhoto`, `ValueChanged<dynamic>? onPhotoTap`, `int crossAxisCount` (default 3), `bool showAddButton` (default true).

Uses GridView.builder with SliverGridDelegateWithFixedCrossAxisCount. Each cell: ClipRRect(borderRadius: AppTheme.radiusSmall) + Image or add-button. Add button: AppGlassCard with Icon(Icons.add_a_photo, size: AppTheme.iconSizeLarge, color: fg.textTertiary).

---

### Phase 1.D: Build Surface Layer Components

#### Step 1.D.1: Create `lib/core/design_system/app_scaffold.dart`

Wraps Scaffold with SafeArea and T Vivid background.

**Inherits from Theme**: Do not set a default `backgroundColor`. `Scaffold` inherits `scaffoldBackgroundColor` from the active ThemeData, which is already set per-theme (#050810 dark, light bg for light, hc bg for high contrast).

Props: `Widget body`, `PreferredSizeWidget? appBar`, `Widget? floatingActionButton`, `Widget? bottomNavigationBar`, `bool useSafeArea` (default true), `Color? backgroundColor`.

```dart
return Scaffold(
  backgroundColor: backgroundColor,
  appBar: appBar,
  floatingActionButton: floatingActionButton,
  bottomNavigationBar: bottomNavigationBar,
  body: useSafeArea ? SafeArea(child: body) : body,
);
```

#### Step 1.D.2: Create `lib/core/design_system/app_bottom_bar.dart`

Sticky bottom action bar with blur backdrop.

Props: `Widget child`, `EdgeInsets? padding` (default `EdgeInsets.symmetric(horizontal: AppTheme.space4, vertical: AppTheme.space3)`).

Implementation:
```dart
return SafeArea(
  child: ClipRect(
    child: BackdropFilter(
      filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
      child: Container(
        padding: padding,
        decoration: BoxDecoration(
          color: cs.surface.withOpacity(0.9),
          border: Border(top: BorderSide(color: cs.outline, width: 1)),
        ),
        child: child,
      ),
    ),
  ),
);
```

#### Step 1.D.3: Create `lib/core/design_system/app_bottom_sheet.dart`

Glass sheet with drag handle and SafeArea.

Static method: `static Future<T?> show<T>(BuildContext context, {required Widget Function(BuildContext) builder, bool isScrollControlled = true})`

Calls `showModalBottomSheet` with:
- `backgroundColor: Colors.transparent`
- `isScrollControlled: isScrollControlled`
- `builder`: returns Container with decoration (color: fg.surfaceElevated, borderRadius: top-left/right AppTheme.radiusXLarge) wrapping Column([AppDragHandle(), Flexible(child: builder(context)), SizedBox(height: MediaQuery.of(context).viewPadding.bottom)])

> Alternatively, omit explicit `backgroundColor` on the inner Container and let `bottomSheetTheme.backgroundColor` handle it.

#### Step 1.D.4: Create `lib/core/design_system/app_dialog.dart`

Static method: `static Future<T?> show<T>(BuildContext context, {required String title, required Widget content, List<Widget>? actions})`

**Inherits from Theme**: Do not specify `backgroundColor` or `shape` on `AlertDialog` — they inherit from `dialogTheme`, which is configured per-theme. Only specify `title` (using `AppText.titleLarge`), `content`, and `actions`.

Calls `showDialog` with:
- AlertDialog with:
  - `title: AppText.titleLarge(title)`
  - `content: content`
  - `actions: actions` — if null, defaults to single TextButton('OK', onPressed: Navigator.pop)

#### Step 1.D.5: Create `lib/core/design_system/app_sticky_header.dart`

Blur-backdrop sticky context header for scroll views (used in entry editor).

Props: `Widget child`, `double height` (default 56).

Used as a `SliverPersistentHeaderDelegate`:
```dart
class AppStickyHeaderDelegate extends SliverPersistentHeaderDelegate {
  final Widget child;
  final double headerHeight;
  // ... implements minExtent/maxExtent = headerHeight
  // build: ClipRect + BackdropFilter(blur 10,10) + Container(color: cs.surface.withOpacity(0.85), child: child)
}
```

Also provide a convenience `SliverPersistentHeader` wrapper:
```dart
class AppStickyHeader extends StatelessWidget {
  // Wraps SliverPersistentHeader(delegate: AppStickyHeaderDelegate(...), pinned: true)
}
```

---

### Phase 1.E: Build Composite Layer Components

#### Step 1.E.1: Create `lib/core/design_system/app_empty_state.dart`

Props: `IconData icon`, `String title`, `String? subtitle`, `String? actionLabel`, `VoidCallback? onAction`.

Layout: Center(Column(mainAxisAlignment: center, children: [
  AppIcon(icon, size: AppIconSize.xl, color: fg.textTertiary),
  SizedBox(height: AppTheme.space4),
  AppText.titleMedium(title, color: cs.onSurfaceVariant),
  if subtitle: SizedBox(height: AppTheme.space2),
  if subtitle: AppText.bodyMedium(subtitle, color: fg.textTertiary, textAlign: center),
  if actionLabel && onAction: SizedBox(height: AppTheme.space6),
  if actionLabel && onAction: ElevatedButton(onPressed: onAction, child: Text(actionLabel)),
]))

#### Step 1.E.2: Create `lib/core/design_system/app_error_state.dart`

Props: `String message`, `VoidCallback? onRetry`, `String retryLabel` (default 'Retry').

Same layout as AppEmptyState but: icon = Icons.error_outline, icon color = cs.error, title = message, actionLabel = retryLabel, onAction = onRetry.

#### Step 1.E.3: Create `lib/core/design_system/app_loading_state.dart`

Props: `String? label`.

**Inherits from Theme**: Do not specify `valueColor` on `CircularProgressIndicator.adaptive` — it inherits from `progressIndicatorTheme`, configured per-theme. Label color: `cs.onSurfaceVariant`.

Layout: Center(Column(mainAxisAlignment: center, children: [
  CircularProgressIndicator.adaptive(),
  if label: SizedBox(height: AppTheme.space4),
  if label: AppText.bodySmall(label, color: cs.onSurfaceVariant),
]))

#### Step 1.E.4: Create `lib/core/design_system/app_budget_warning_chip.dart`

Replaces the identical budget discrepancy chip pattern in `project_dashboard_screen.dart:427-433` and `quantities_screen.dart:173-179`.

Props: `String message`.

Layout: Container(
  padding: EdgeInsets.symmetric(horizontal: AppTheme.space3, vertical: AppTheme.space1),
  decoration: BoxDecoration(
    color: fg.warningBackground,
    borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
    border: Border.all(color: fg.warningBorder),
  ),
  child: Row(mainAxisSize: min, children: [
    AppIcon(Icons.warning_amber_rounded, size: AppIconSize.small, color: fg.statusWarning),
    SizedBox(width: AppTheme.space1),
    Flexible(child: AppText.bodySmall(message, color: fg.statusWarning)),
  ]),
)

#### Step 1.E.5: Create `lib/core/design_system/app_drag_handle.dart`

Replaces the identical drag handle pattern in `project_switcher.dart:128-137` and `member_detail_sheet.dart:47-56`.

No required props. Optional `Color? color` (default `fg.dragHandleColor`).

Layout:
```dart
Center(
  child: Container(
    margin: EdgeInsets.symmetric(vertical: AppTheme.space3),
    width: 40,
    height: 4,
    decoration: BoxDecoration(
      color: color ?? fg.dragHandleColor,
      borderRadius: BorderRadius.circular(AppTheme.radiusFull),
    ),
  ),
)
```

---

### Phase 1.F: Barrel Export + Quality Gate

#### Step 1.F.1: Create `lib/core/design_system/design_system.dart`

Barrel export file:
```dart
export 'app_text.dart';
export 'app_text_field.dart';
export 'app_chip.dart';
export 'app_progress_bar.dart';
export 'app_counter_field.dart';
export 'app_toggle.dart';
export 'app_icon.dart';
export 'app_glass_card.dart';
export 'app_section_header.dart';
export 'app_list_tile.dart';
export 'app_photo_grid.dart';
export 'app_scaffold.dart';
export 'app_bottom_bar.dart';
export 'app_bottom_sheet.dart';
export 'app_dialog.dart';
export 'app_sticky_header.dart';
export 'app_empty_state.dart';
export 'app_error_state.dart';
export 'app_loading_state.dart';
export 'app_budget_warning_chip.dart';
export 'app_drag_handle.dart';
```

#### Step 1.F.2: Quality Gate

1. Run `pwsh -Command "flutter analyze"` — zero errors, zero warnings in new files
2. Run `pwsh -Command "flutter test"` — all existing tests pass (no regressions)
3. Verify all 20 component files exist in `lib/core/design_system/`
4. Verify all new tokens are accessible via `AppTheme.*`
5. Verify `import 'package:construction_inspector/core/design_system/design_system.dart';` compiles
6. Verify `FieldGuideColors.of(context)` compiles and returns correct values for all three themes
7. Verify no `AppTheme.*` color constants used inside any design system component file (spacing/radius/animation constants are OK)

**Commit**: `feat(design-system): add T Vivid component library with 20 components, FieldGuideColors ThemeExtension, and WeatherProvider`

---

### Phase 1.G: Enhance WeatherService + Create WeatherProvider

**Goal**: Extend `WeatherService` to support current temperature and location name. Create `WeatherProvider` for caching and refresh-on-app-open behavior. The dashboard (Phase 2) consumes this provider for a weather summary card.

#### Step 1.G.1: Enhance `WeatherData` model

Extend `WeatherData` in `lib/features/weather/services/weather_service.dart`:

```dart
class WeatherData {
  final String condition;
  final int tempHigh;
  final int tempLow;
  final int? tempCurrent;     // NEW: current temperature in Fahrenheit
  final String? locationName;  // NEW: reverse-geocoded city name (e.g., "Springfield")

  WeatherData({
    required this.condition,
    required this.tempHigh,
    required this.tempLow,
    this.tempCurrent,
    this.locationName,
  });
}
```

#### Step 1.G.2: Add current temperature to API call

In `WeatherService.fetchWeather()`, add `current=temperature_2m` to the Open-Meteo query parameters alongside the existing `daily` params. Parse `current.temperature_2m` from the response to populate `tempCurrent` (convert from Celsius using existing `celsiusToFahrenheit`).

#### Step 1.G.3: Add reverse geocoding for location name

Add a `fetchLocationName(double lat, double lon)` method to `WeatherService`. Use Open-Meteo's reverse geocoding API (`https://geocoding-api.open-meteo.com/v1/search?name=`) or the `geocoding` Flutter package to convert GPS coordinates to a city name. Cache the result — location name rarely changes.

#### Step 1.G.4: Create `WeatherProvider`

Create `lib/features/weather/presentation/providers/weather_provider.dart`:

```dart
class WeatherProvider extends ChangeNotifier {
  final WeatherService _weatherService;

  WeatherData? _currentWeather;
  bool _isLoading = false;
  String? _error;
  DateTime? _lastFetch;

  WeatherData? get currentWeather => _currentWeather;
  bool get isLoading => _isLoading;
  String? get error => _error;

  /// Refresh weather data. Called on app open and pull-to-refresh.
  /// Skips fetch if last fetch was < 15 minutes ago (unless force=true).
  Future<void> refresh({bool force = false}) async { ... }
}
```

- Caches weather data in memory with 15-minute TTL
- Refreshes on `refresh()` call (triggered by dashboard `initState` / pull-to-refresh)
- Exposes `currentWeather`, `isLoading`, `error`

#### Step 1.G.5: Register WeatherProvider in `main.dart`

Add `ChangeNotifierProvider<WeatherProvider>` to the provider list in `main.dart`. Initialize with the existing `WeatherService` instance.

#### Step 1.G.6: Quality Gate

1. `pwsh -Command "flutter analyze"` — zero issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Verify `WeatherData` has `tempCurrent` and `locationName` fields
4. Verify `WeatherProvider.refresh()` fetches and caches data

---

## Phase 2: Dashboard Rewrite

**Goal**: Rewrite `ProjectDashboardScreen` using locked T Vivid "Premium Elevated — Vivid Variant" mockup.

**Commit**: `feat(dashboard): rewrite with T Vivid design system`

### Phase 2.A: Replace Dashboard Widgets

#### Step 2.A.1: Rewrite `lib/features/dashboard/presentation/widgets/dashboard_stat_card.dart`

Current violations: `fontSize:11,22`, `Colors.black.withValues:54`, `Colors.transparent:61`.

Rewrite using design system:
- Replace Container with `AppGlassCard`
- Replace `TextStyle(fontSize: 22)` with `AppText.titleLarge`
- Replace `TextStyle(fontSize: 11, color: textSecondary)` with `AppText.labelSmall(color: cs.onSurfaceVariant)`
- Replace `Colors.black.withValues(alpha: 0.15)` with `fg.shadowLight`
- Replace `Colors.transparent` with `Colors.transparent` (acceptable, keep)
- Replace all raw `SizedBox` spacing with `AppTheme.space*` tokens
- Replace `BorderRadius.circular(N)` with `AppTheme.radius*` tokens

Props: `String title`, `String value`, `IconData icon`, `Color accentColor`, `VoidCallback? onTap`.

#### Step 2.A.2: Rewrite `lib/features/dashboard/presentation/widgets/budget_overview_card.dart`

Current violations: 7 inline fontSize.

Rewrite using design system:
- Use `AppGlassCard` with `accentColor: cs.primary` as outer container
- Contract value: `AppText.headlineMedium` or `AppText.titleLarge`
- Labels: `AppText.labelSmall(color: cs.onSurfaceVariant)`
- Used/remaining boxes: Two inner `AppGlassCard` children side by side
- Progress bar: `AppProgressBar(value: usedFraction)`
- Replace all `TextStyle(fontSize: N)` with `AppText.*` constructors
- Replace all raw spacing with `AppTheme.space*`

#### Step 2.A.3: Rewrite `lib/features/dashboard/presentation/widgets/tracked_item_row.dart`

Current violations: `fontSize:11,13,16`, `Colors.transparent:46`.

Rewrite:
- Use `AppGlassCard` with `accentColor: Color(0xFF26C6DA)` (teal/tracked)
- Item name: `AppText.bodyLarge`
- Percentage: `AppText.titleMedium(color: accentColor)`
- Progress bar: `AppProgressBar`
- **New: explicit quantities** — show "used/total units" and "remaining" text below progress bar
- Labels: `AppText.bodySmall(color: cs.onSurfaceVariant)`
- Replace `Colors.transparent` → keep (acceptable)

#### Step 2.A.4: Rewrite `lib/features/dashboard/presentation/widgets/alert_item_row.dart`

Current violations: `fontSize:12,13`, 2 raw BR.

Rewrite:
- Use `AppGlassCard` with `accentColor: fg.statusWarning`
- Item name: `AppText.bodyLarge`
- Percentage: `AppText.titleMedium(color: statusWarning)`
- Progress bar: `AppProgressBar(startColor: fg.statusWarning, endColor: fg.accentOrange)`
- **New: explicit quantities** — show "used/total units" and "remaining"
- Replace `BorderRadius.circular(N)` with `AppTheme.radius*`

---

### Phase 2.B: Rewrite ProjectDashboardScreen

**File**: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`

Current violations: 24 inline fontSize, `Colors.orange.shade800:427`, `Colors.amber.shade50:432`, `Colors.amber.shade200:433`, `Colors.black.withValues:477`.

#### Step 2.B.1: Structural changes

- Replace `Scaffold` with `AppScaffold`
- Keep `CustomScrollView` layout with `SliverAppBar` (works well for dashboard)
- **Replace 4-stat row** (Entries, Pay Items, Contractors, Toolbox) **with 3-stat row** (Entries, Pay Items, Toolbox) using rewritten `DashboardStatCard`
- **Budget card**: Move to hero position (first item after stats). Use rewritten `BudgetOverviewCard` with contract value prominent, used/remaining split boxes.
- **CTA**: Add "Today's Entry" action card — `AppGlassCard(accentColor: fg.accentAmber)` with action text and right arrow icon. OnTap: navigate to entry editor for today's date.
- **Approaching Limit section**: `AppSectionHeader('Approaching Limit')` + list of `AlertItemRow` with explicit quantities
- **Top Tracked section**: `AppSectionHeader('Top Tracked')` + list of `TrackedItemRow` with explicit quantities
- **Weather**: Compact weather summary card via `WeatherProvider` (Phase 1.G). Shows location name (e.g., "Springfield"), current temperature (`AppText.titleMedium`), and "H: X° / L: Y°" (`AppText.bodySmall`). Use weather condition icon from `WeatherConditionHelpers`. Show loading spinner while fetching, "Weather unavailable" if error. Auto-refreshes on dashboard `initState` via `WeatherProvider.refresh()`.
- **Project number**: Change color to `AppTheme.projectNumberText` — visible white-ish
- **Drafts**: Compact pill below stats — `AppChip.cyan('N Drafts', icon: Icons.edit_note)`

#### Step 2.B.2: Token migration

- Replace all `Colors.orange.shade800` → `fg.statusWarning` (via `FieldGuideColors.of(context)`)
- Replace all `Colors.amber.shade50` → `fg.warningBackground`
- Replace all `Colors.amber.shade200` → `fg.warningBorder`
- Replace `Colors.black.withValues(alpha: 0.1)` → `fg.shadowLight`
- Replace all inline `TextStyle(fontSize: N)` with `AppText.*` constructors
- Replace all raw `SizedBox(height: N)` with `SizedBox(height: AppTheme.space*)`
- Replace all raw `EdgeInsets` with `AppTheme.space*` values
- Replace all raw `BorderRadius.circular(N)` with `AppTheme.radius*`

#### Step 2.B.3: Quality Gate

1. `pwsh -Command "flutter analyze"` — zero issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Verify zero `Colors.*` in `lib/features/dashboard/presentation/`
4. Verify zero inline `TextStyle(fontSize:` in `lib/features/dashboard/presentation/`
5. Verify zero raw `SizedBox(height: N)` where N matches a token value
6. Update any existing dashboard widget tests to match new component structure

**Commit**: `feat(dashboard): rewrite with T Vivid design system`

---

## Phase 3: Entry Editor Rewrite

**Goal**: Rewrite `EntryEditorScreen` and all 7 entry section widgets using locked "J Final" mockup with color-coded floating glass section cards.

**Commit**: `feat(entry-editor): rewrite with T Vivid color-coded glass sections`

**CRITICAL**: EntryEditorScreen reads from 14 providers/services (DailyEntryProvider, LocationProvider, ProjectProvider, ContractorProvider, EquipmentProvider, EntryQuantityProvider, PhotoProvider, PersonnelTypeProvider, InspectorFormProvider, BidItemProvider, AuthProvider, DatabaseService, PdfService, PhotoService). Do NOT change provider wiring — only change presentation/layout. Rewrite section widgets first, then the screen.

### Phase 3.A: Rewrite Entry Section Widgets

Each section widget gets its assigned accent color and glass card treatment.

#### Step 3.A.1: Rewrite `lib/features/entries/presentation/widgets/entry_basics_section.dart`

- **Accent**: `cs.primary` (#00E5FF)
- Wrap in `AppGlassCard(accentColor: cs.primary)`
- Section header: `AppSectionHeader('Basics', icon: Icons.info_outline, color: cs.primary)`
- Replace `TextStyle(fontWeight: FontWeight.bold, fontSize: 16)` → `AppText.titleMedium`
- Replace all raw spacing with `AppTheme.space*`
- Use `AppTextField` for text inputs

#### Step 3.A.2: Rewrite `lib/features/entries/presentation/widgets/entry_activities_section.dart`

- **Accent**: `cs.tertiary` (#2196F3)
- Wrap in `AppGlassCard(accentColor: cs.tertiary)`
- Section header: `AppSectionHeader('Activities', icon: Icons.description, color: cs.tertiary)`
- **Activities text area always fully visible** — no collapse/truncation
- Add word count below text area: `AppText.bodySmall('${wordCount} words', color: textTertiary)`
- Add auto-save timestamp: `AppText.bodySmall('Auto-saved ${timeAgo}', color: textTertiary)`
- Replace inline `TextStyle(fontSize: 14,16)` → `AppText.bodyMedium`/`AppText.titleMedium`
- Replace raw spacing with tokens

#### Step 3.A.3: Rewrite `lib/features/entries/presentation/widgets/entry_contractors_section.dart`

- **Accent**: `fg.accentAmber` (#FFC107)
- Wrap in `AppGlassCard(accentColor: fg.accentAmber)`
- Section header: `AppSectionHeader('Contractors', icon: Icons.people, color: fg.accentAmber)`
- **Keep existing tap-to-expand flow** — tap contractor row to expand inline with personnel counters and equipment toggles. Hit Done to collapse.
- "Add Contractor" button at bottom
- Replace `TextStyle(fontSize: 12,13,16)` → `AppText.bodySmall`/`AppText.bodyMedium`/`AppText.titleMedium`
- Replace raw spacing with tokens

#### Step 3.A.4: Rewrite `lib/features/entries/presentation/widgets/contractor_editor_widget.dart`

**Highest violation widget**: 17 inline fontSize, 5 raw BR(4).

- Restyle with T Vivid amber accent
- Replace all 17 `TextStyle(fontSize: N)` instances:
  - fontSize 12 → `AppText.bodySmall`
  - fontSize 13 → `AppText.bodySmall` (close enough, no 13px slot)
  - fontSize 14 → `AppText.bodyMedium`
  - fontSize 16 → `AppText.titleMedium`
- Replace all `BorderRadius.circular(4)` → `AppTheme.radiusXSmall`
- Use `AppCounterField` for personnel +/- steppers
- Use `AppChip` for equipment toggle chips
- Replace raw spacing with tokens

#### Step 3.A.5: Rewrite `lib/features/entries/presentation/widgets/entry_safety_section.dart`

- **Accent**: `fg.statusSuccess` (#66BB6A / green)
- Wrap in `AppGlassCard(accentColor: fg.statusSuccess)`
- Section header: `AppSectionHeader('Safety', icon: Icons.health_and_safety, color: fg.statusSuccess)`
- **5 fields**: Site Safety, SESC, Traffic Control, Visitors on Site, Extras & Overruns
- Use `AppTextField` for text inputs (inherits from `inputDecorationTheme`)
- Replace `TextStyle(fontSize: 16)` → `AppText.titleMedium`
- Replace raw spacing with tokens
- **Note**: Repeat-last toggles for safety fields are added in Phase 3.5 (separate feature work)

#### Step 3.A.6: Rewrite `lib/features/entries/presentation/widgets/entry_quantities_section.dart`

- **Accent**: `AppTheme.sectionQuantities` (teal)
- Wrap in `AppGlassCard(accentColor: AppTheme.sectionQuantities)`
- Section header: `AppSectionHeader('Quantities', icon: Icons.straighten, color: AppTheme.sectionQuantities)`
- Replace 12 inline fontSize → `AppText.*`
- Replace 5 raw BR → `AppTheme.radius*`
- Replace raw spacing with tokens

#### Step 3.A.7: Rewrite `lib/features/entries/presentation/widgets/entry_photos_section.dart`

- **Accent**: `AppTheme.sectionPhotos` (purple)
- Wrap in `AppGlassCard(accentColor: AppTheme.sectionPhotos)`
- Section header: `AppSectionHeader('Photos', icon: Icons.photo_camera, color: AppTheme.sectionPhotos)`
- Use `AppPhotoGrid` for photo thumbnail display
- Replace `TextStyle(fontSize: 12,16)` → `AppText.bodySmall`/`AppText.titleMedium`

#### Step 3.A.8: Rewrite `lib/features/entries/presentation/widgets/entry_forms_section.dart`

- **Accent**: `cs.onSurfaceVariant` (neutral gray)
- Wrap in `AppGlassCard(accentColor: cs.onSurfaceVariant)`
- Section header: `AppSectionHeader('Forms', icon: Icons.assignment, color: cs.onSurfaceVariant)`
- Replace `TextStyle(fontSize: 16)` → `AppText.titleMedium`

#### Step 3.A.9: Rewrite `lib/features/entries/presentation/widgets/entry_action_bar.dart`

- Replace with `AppBottomBar` containing a single "Save Draft" button
- **No Submit button** — submission happens through the separate review flow
- Add "Auto-saves on edit" hint text on the left: `AppText.bodySmall('Auto-saves on edit', color: textTertiary)`
- Right side: `ElevatedButton` with "Save Draft" label
- **Edit mode**: Keep the existing auto-save status indicator ("Saving...", "Unsaved changes", "All changes saved"). Restyle with `AppText.bodySmall` and theme-aware colors (`cs.onSurfaceVariant` for status text, `fg.statusSuccess` for "All changes saved").
- Replace 5 inline fontSize → `AppText.*`
- Replace raw BR → `AppTheme.radius*`

#### Step 3.A.10: Restyle `lib/features/entries/presentation/widgets/submitted_banner.dart`

- Replace `fontSize: 13` → `AppText.bodySmall`
- Replace `fontSize: 12` → `AppText.bodySmall`
- Apply T Vivid glass card treatment
- Replace raw spacing with tokens

---

### Phase 3.B: Rewrite EntryEditorScreen

**File**: `lib/features/entries/presentation/screens/entry_editor_screen.dart`

#### Step 3.B.1: Structural changes

- Replace `Scaffold` with `AppScaffold`
- Keep `CustomScrollView` layout
- **Sticky header**: Use `AppStickyHeader` as `SliverPersistentHeader(pinned: true)` showing: project name + "MM" marker + entry number. NO temperature (already in Basics card).
- **Body**: `SliverList` of the 7 section widgets, each wrapped in `Padding(padding: EdgeInsets.symmetric(horizontal: AppTheme.space4, vertical: AppTheme.space2))` — creates the floating card effect with gaps.
- **Bottom bar**: `AppBottomBar` with Save Draft only (built into rewritten EntryActionBar)
- Section order: Basics → Activities → Contractors → Safety → Quantities → Photos → Forms

#### Step 3.B.2: Token migration

- Replace all 5 inline `TextStyle(fontSize: 14,16)` → `AppText.*`
- Replace all 3 raw `BorderRadius.circular(8,12)` → `AppTheme.radiusSmall`/`AppTheme.radiusMedium`
- Replace raw spacing with tokens

#### Step 3.B.3: Quality Gate

1. `pwsh -Command "flutter analyze"` — zero issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Verify all 7 section widgets wrapped in `AppGlassCard` with correct accent color
4. Verify zero inline `TextStyle(fontSize:` in entry editor + section widgets
5. Verify zero raw `Colors.*` in entry editor + section widgets
6. Verify sticky header shows project name + entry number (no temp)
7. Verify bottom bar is Save Draft only
8. Update any existing entry editor/section widget tests to match new structure

**Commit**: `feat(entry-editor): rewrite with T Vivid color-coded glass sections`

---

## Phase 3.5: Safety Repeat-Last Toggles (NEW FEATURE)

**Goal**: Add "repeat last entry" toggle functionality to Site Safety, SESC, and Traffic Control fields in the safety section. This is NEW FEATURE work separated from the UI restyle.

**Commit**: `feat(entry-editor): add repeat-last-entry toggles for safety fields`

### Phase 3.5.A: Data Layer

#### Step 3.5.A.1: Add query for most recent previous entry

Add a method to `DailyEntryProvider` that retrieves the most recent previous entry for the same project:

```dart
Future<DailyEntry?> getMostRecentEntry(String projectId, DateTime beforeDate) async { ... }
```

Query the `daily_entries` table for the given `projectId` with `date < beforeDate`, ordered by `date DESC`, limit 1.

### Phase 3.5.B: UI Implementation

#### Step 3.5.B.1: Add repeat-last toggles to `EntrySafetySection`

- Convert `EntrySafetySection` from `StatelessWidget` to `StatefulWidget` (or accept prefill data via props)
- Site Safety, SESC, and Traffic Control each get an `AppToggle` labeled "Repeat last entry"
- When toggled ON: prefill the field value from the most recent previous entry. Show subtitle with source date (e.g., "From 03/05/2026")
- When toggled OFF: clear the prefilled value, restore empty field
- **Visitors and Extras & Overruns do NOT get this toggle** (unique per day)
- Edge case: no previous entry exists → toggle is disabled with tooltip "No previous entry"
- Edge case: previous entry has empty value for that field → toggle enabled but prefills empty string (no-op)

### Phase 3.5.C: Quality Gate

1. `pwsh -Command "flutter analyze"` — zero issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Verify toggle prefills from correct (most recent) entry
4. Verify toggle disabled when no previous entry exists
5. Verify Visitors and Extras & Overruns have no toggle

**Commit**: `feat(entry-editor): add repeat-last-entry toggles for safety fields`

---

## Phase 4: Calendar/Home Screen

**Goal**: Simplify HomeScreen — remove inline editable report, make calendar read-only date picker with entry dots.

**Commit**: `feat(calendar): simplify to read-only date picker with T Vivid`

**CRITICAL**: HomeScreen is the largest file (2000+ lines, 9 providers/services). This is a structural simplification that REMOVES complexity.

### Phase 4.A: Remove Inline Editable Report

#### Step 4.A.1: Remove the inline report section from `lib/features/entries/presentation/screens/home_screen.dart`

The bottom portion of the HomeScreen currently renders an inline editable daily report below the calendar. Remove this entire section. The calendar should be the primary content.

When the user taps a date that has an entry, show a compact entry card (AppGlassCard) below the calendar with entry summary info. Tapping the card navigates to the full EntryEditorScreen via `context.go('/entry/$projectId/$date')` or `context.go('/report/$entryId')`.

#### Step 4.A.2: Calendar becomes read-only

- Calendar widget: keep `TableCalendar` but remove all editing callbacks
- Entry dots: keep the dot indicators below dates that have entries
- Selected date: show a list of entries for that date below the calendar (if any) as `AppListTile` cards
- Tap entry card → opens full editor
- Remove all the inline entry editing widgets, contractor pickers, photo sections etc. from this screen

#### Step 4.A.3: Clean up provider imports

After removing the inline report, these providers/services are no longer needed by HomeScreen — remove from imports:
- `ContractorProvider` — only used for inline contractor editing
- `EquipmentProvider` — only used for inline equipment editing
- `PersonnelTypeProvider` — only used for inline personnel editing
- `PhotoProvider` — only used for inline photo section
- `BidItemProvider` — only used for inline quantities section
- `DatabaseService` — only used to initialize ContractorEditingController

**Simplified HomeScreen providers**: `ProjectProvider`, `DailyEntryProvider`, `LocationProvider`, `AuthProvider`, `CalendarFormatProvider`.

### Phase 4.B: T Vivid Restyle

#### Step 4.B.1: Apply T Vivid styling to HomeScreen

- Replace `Scaffold` with `AppScaffold`
- Style the calendar widget with T Vivid colors: dark background, cyan accent for selected date, subtle dots
- Entry summary cards below calendar: use `AppGlassCard`
- Replace all inline `TextStyle` → `AppText.*`
- Replace all raw spacing → tokens
- Fix bottom cutoff bug at line 1604 (contractor picker sheet) — if picker sheet still exists, wrap in SafeArea
- Restyle `DeletionNotificationBanner` (`lib/features/sync/presentation/widgets/deletion_notification_banner.dart`) — replace 2 `fontSize: 14` violations with `AppText.bodyMedium`
- Preserve `ViewOnlyBanner` for viewer-role users — apply T Vivid tokens

#### Step 4.B.2: Quality Gate

1. `pwsh -Command "flutter analyze"` — zero issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Verify no inline editing UI remains on calendar screen
4. Verify tap-on-date shows entry cards
5. Verify tap-on-entry-card navigates to editor
6. Update or remove TestingKeys that reference removed inline editing widgets (e.g., `TestingKeys.homeReportPreviewScrollView`, `calendarReportContractorsSection`, `calendarReportAddContractorButton`)
7. Update any HomeScreen tests to match simplified structure

**Commit**: `feat(calendar): simplify to read-only date picker with T Vivid`

---

## Phase 5: List Screens Batch

**Goal**: Restyle all list screens with glass list cards.

**Commit**: `feat(lists): restyle all list screens with T Vivid glass cards`

> **Theme-aware color replacements (applies to Phases 5–10)**: All `Colors.*` replacements in these phases use the theme-aware pattern from Phase 1.A.5. Use `cs.*` (ColorScheme) and `fg.*` (FieldGuideColors) — NOT static `AppTheme.*` color constants. See **Appendix C** for the full mapping. Key replacements: `Colors.red` → `cs.error`, `Colors.green` → `fg.statusSuccess`, `Colors.amber`/`Colors.orange` → `fg.statusWarning`, `Colors.grey` → `cs.onSurfaceVariant`, `Colors.white` (on primary bg) → `fg.textInverse`, `Colors.grey[300]`/`grey.shade100` → `cs.outline`, `Colors.black.withValues(alpha:*)` → `fg.shadowLight`.

### Phase 5.A: ProjectListScreen

**File**: `lib/features/projects/presentation/screens/project_list_screen.dart`
**Violations**: 10 inline fontSize, 5 raw BR (6,8,10,12).

#### Step 5.A.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Each project list item → `AppListTile` or `AppGlassCard`
- Replace all `TextStyle(fontSize: 12,13,14,15,16)` → `AppText.*`
- Replace `BR.circular(6)` → `AppTheme.radiusCompact` (new token)
- Replace `BR.circular(8)` → `AppTheme.radiusSmall`
- Replace `BR.circular(10)` → `AppTheme.radiusCompact`
- Replace `BR.circular(12)` → `AppTheme.radiusMedium`
- Replace raw spacing → tokens

### Phase 5.B: EntriesListScreen

**File**: `lib/features/entries/presentation/screens/entries_list_screen.dart`
**Violations**: 11 inline fontSize, 3 raw BR.

#### Step 5.B.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Each entry item → `AppListTile` or `AppGlassCard`
- Replace inline fontSize → `AppText.*`
- Replace raw BR → tokens
- Replace raw spacing → tokens

### Phase 5.C: DraftsListScreen

**File**: `lib/features/entries/presentation/screens/drafts_list_screen.dart`
**Violations**: 2 inline fontSize, 1 shadow.

#### Step 5.C.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Rewrite `DraftEntryTile` (`lib/features/entries/presentation/widgets/draft_entry_tile.dart`, 6 inline fontSize) to use `AppGlassCard` + `AppText.*`
- Replace `Colors.black.withValues(alpha: 0.1)` → `fg.shadowLight`
- Replace inline fontSize → `AppText.*`
- Replace raw spacing → tokens

### Phase 5.D: FormsListScreen

**File**: `lib/features/forms/presentation/screens/forms_list_screen.dart`
**Violations**: 1 inline fontSize.

#### Step 5.D.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Restyle `FormAccordion` (`lib/features/forms/presentation/widgets/form_accordion.dart`) — 4 inline fontSize (11,12,15,15), 4 raw BR (10,14,14,999):
  - Replace fontSize → `AppText.*`
  - Replace `BR.circular(10)` → `AppTheme.radiusCompact`
  - Replace `BR.circular(14)` → `AppTheme.radiusMedium` (closest)
  - Replace `BR.circular(999)` → `AppTheme.radiusFull`
  - Replace `Colors.transparent` → keep (acceptable)
- Restyle `StatusPillBar` (`status_pill_bar.dart`) — fontSize 11, BR(20):
  - Replace fontSize → `AppText.labelSmall`
  - Replace `BR.circular(20)` → `AppTheme.radiusXLarge`

### Phase 5.E: TodosScreen

**File**: `lib/features/todos/presentation/screens/todos_screen.dart`
**Violations**: 2 inline fontSize (12), 2 raw BR(12).

#### Step 5.E.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Replace `BR.circular(12)` → `AppTheme.radiusMedium` (2 instances at lines 131, 579)
- Todo items: wrap in `AppGlassCard`
- Replace 2 `fontSize: 12` violations (in `_DueDateChip` and `_buildFilterMenuItem`) → `AppText.bodySmall`

### Phase 5.F: TrashScreen

**File**: `lib/features/settings/presentation/screens/trash_screen.dart`
**Violations**: 6 inline fontSize (12,14,18).

#### Step 5.F.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Replace `TextStyle(fontSize: 12)` → `AppText.bodySmall`
- Replace `TextStyle(fontSize: 14)` → `AppText.bodyMedium`
- Replace `TextStyle(fontSize: 18)` → `AppText.titleLarge` (closest)
- Trash items: wrap in `AppGlassCard` or `AppListTile`

### Phase 5.G: PersonnelTypesScreen

**File**: `lib/features/settings/presentation/screens/personnel_types_screen.dart`
**Violations**: 1 inline fontSize (18).

#### Step 5.G.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Replace `TextStyle(fontSize: 18)` → `AppText.titleLarge`
- Personnel type items: wrap in `AppListTile`

### Phase 5.H: AdminDashboardScreen

**File**: `lib/features/settings/presentation/screens/admin_dashboard_screen.dart`
**Violations**: 3 inline fontSize, 3 raw BR (4,12), 5 Colors violations.

#### Step 5.H.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Replace `Colors.grey:90,109` → `cs.onSurfaceVariant` (empty state text)
- Replace `Colors.grey:265,281` → `cs.onSurfaceVariant` (inactive role/sync badges)
- Replace `Colors.white:148` → `fg.textInverse`
- Replace `BR.circular(4)` → `AppTheme.radiusXSmall`
- Replace `BR.circular(12)` → `AppTheme.radiusMedium`
- User items: use `AppListTile`
- Role badges: use `AppChip`

### Phase 5.I: Quality Gate

1. `pwsh -Command "flutter analyze"` — zero issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Verify zero `Colors.*` in all list screen files
4. Verify zero inline `TextStyle(fontSize:` in all list screen files
5. Verify zero raw `BorderRadius.circular(N)` in all list screen files
6. Update any existing list screen tests to match new glass card structure

**Commit**: `feat(lists): restyle all list screens with T Vivid glass cards`

---

## Phase 6: Settings + Sync Screens

**Goal**: Restyle settings with glass sections and fix all sync screen token violations (worst offenders).

**Commit**: `feat(settings-sync): restyle settings and sync screens with T Vivid`

### Phase 6.A: SettingsScreen

**File**: `lib/features/settings/presentation/screens/settings_screen.dart`
**Violations**: `Colors.white:223`, `BR.circular(12):218`, `fontSize:11,12`:254,224. Bottom cutoff bug at line 339.

#### Step 6.A.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Each settings group → `AppGlassCard` with `AppSectionHeader` title
- Replace `Colors.white:223` → `fg.textInverse`
- Replace `BR.circular(12)` → `AppTheme.radiusMedium`
- Replace `fontSize: 11` → `AppText.labelSmall`
- Replace `fontSize: 12` → `AppText.bodySmall`
- **Fix bottom cutoff bug**: Replace `SizedBox(height: 32)` at line 339 with `SizedBox(height: MediaQuery.of(context).padding.bottom + AppTheme.space8)`

#### Step 6.A.2: Restyle settings widgets

- `SyncSection` (`lib/features/settings/presentation/widgets/sync_section.dart`): Replace `fontSize:12` → `AppText.bodySmall`. Vivid treatment for sync status indicators.
- `SectionHeader` (`lib/features/settings/presentation/widgets/section_header.dart`): Replace with `AppSectionHeader` usage or update internal `fontSize:14` → `AppText.titleSmall`
- `ThemeSection`, `ClearCacheDialog`, `SignOutDialog`: Apply T Vivid tokens if they have violations

### Phase 6.B: SyncDashboardScreen

**File**: `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`
**Violations**: 7 inline fontSize, 8 Colors violations (including `Colors.green` in integrity card). **WORST OFFENDER FILE.**

#### Step 6.B.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Replace `Colors.red:161` → `cs.error`
- Replace `Colors.amber:163` → `fg.statusWarning`
- Replace `Colors.green:164` → `fg.statusSuccess`
- Replace `Colors.grey:208,395` → `cs.onSurfaceVariant`
- Replace `Colors.white:305` → `fg.textInverse`
- Replace `Colors.orange:384` → `fg.statusWarning`
- Replace `Colors.green:384` (integrity card ternary) → `fg.statusSuccess`
- Replace all 7 inline fontSize instances:
  - 11 → `AppText.labelSmall`
  - 12 → `AppText.bodySmall`
  - 16 → `AppText.bodyLarge` or `AppText.titleMedium`
  - 20 → `AppText.headlineSmall`
- Use `AppGlassCard` for sync table sections
- Use `AppProgressBar` for sync progress indicators

### Phase 6.C: SyncStatusIcon Widget

**File**: `lib/features/sync/presentation/widgets/sync_status_icon.dart`
**Violations**: `Colors.red:34`, `Colors.amber:35`, `Colors.green:36`.

#### Step 6.C.1: Fix

- Replace `Colors.red` → `cs.error`
- Replace `Colors.amber` → `fg.statusWarning`
- Replace `Colors.green` → `fg.statusSuccess`

### Phase 6.D: ConflictViewerScreen

**File**: `lib/features/sync/presentation/screens/conflict_viewer_screen.dart`
**Violations**: 3 inline fontSize, 1 raw BR(4), 4 Colors violations.

#### Step 6.D.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Replace `Colors.green:188` → `fg.statusSuccess`
- Replace `Colors.orange:232` → `fg.statusWarning`
- Replace `Colors.grey:261` → `cs.onSurfaceVariant`
- Replace `Colors.grey.shade100:277` → `cs.outline`
- Replace `BR.circular(4)` → `AppTheme.radiusXSmall`
- Replace fontSize 11,12,13 → `AppText.labelSmall`/`AppText.bodySmall`

### Phase 6.E: ProjectSelectionScreen

**File**: `lib/features/sync/presentation/screens/project_selection_screen.dart`
**Violations**: `Colors.red:146`, `Colors.grey:213`.

#### Step 6.E.1: Fix

- Replace `Colors.red` → `cs.error`
- Replace `Colors.grey` → `cs.onSurfaceVariant`
- Use `AppListTile` for project items

### Phase 6.F: MemberDetailSheet

**File**: `lib/features/settings/presentation/widgets/member_detail_sheet.dart`
**Violations**: `Colors.grey[300]:53`, `Colors.grey:227,245`, `fontSize:11,13,13,18` (4 violations), `BR(2,12)`.

#### Step 6.F.1: Restyle

- Replace `Colors.grey[300]:53` → `cs.outline`
- Replace `Colors.grey:227,245` → `cs.onSurfaceVariant`
- Replace `fontSize: 11` → `AppText.labelSmall`
- Replace `fontSize: 13` (2 instances) → `AppText.bodySmall`
- Replace `fontSize: 18` → `AppText.titleLarge`
- Replace `BR.circular(2)` → use `AppDragHandle` component instead (that's the drag handle bar)
- Replace `BR.circular(12)` → `AppTheme.radiusMedium`
- **Fix bottom cutoff bug**: Change `viewInsets.bottom` → `viewPadding.bottom` at line 36-40

### Phase 6.G: ProjectSwitcher

**File**: `lib/features/projects/presentation/widgets/project_switcher.dart`
**Violations**: `Colors.grey[300]:133`, `Colors.grey:226`, `BR(2,8)`.

#### Step 6.G.1: Restyle

- Replace `Colors.grey[300]:133` → `cs.outline`
- Replace `Colors.grey:226` → `cs.onSurfaceVariant`
- Replace `BR.circular(2)` → use `AppDragHandle` component
- Replace `BR.circular(8)` → `AppTheme.radiusSmall`
- **Fix bottom cutoff bug**: Change `viewInsets.bottom` → `viewPadding.bottom` at line 116-120

### Phase 6.H: ScaffoldWithNavBar (Navigation Shell)

**File**: `lib/core/router/app_router.dart` (lines 543-689)
**Violations**: 3 Colors violations in sync toast/banner. **NOT covered by any other phase.**

#### Step 6.H.1: Fix Colors violations

- Replace `Colors.red.shade700:571` (sync error toast bg) → `cs.error` (via `Theme.of(context).colorScheme.error`)
- Replace `Colors.white:575` (toast action text) → `fg.textInverse`
- Replace `Colors.orange:609` (stale sync banner icon) → `fg.statusWarning`

### Phase 6.I: Quality Gate

1. `pwsh -Command "flutter analyze"` — zero issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Verify zero `Colors.*` in `lib/features/sync/presentation/`
4. Verify zero `Colors.*` in `lib/features/settings/presentation/`
5. Verify all 6 confirmed bottom-cutoff bugs are fixed
6. Update `sync_status_icon_test.dart` — replace `Colors.green`/`Colors.amber`/`Colors.red` assertions with `AppTheme.statusSuccess`/`statusWarning`/`statusError` (or theme-aware equivalents)
7. Update any other sync/settings tests affected by color changes

**Commit**: `feat(settings-sync): restyle settings and sync screens with T Vivid`

**Bottom-cutoff bugs addressed so far** (consolidated checklist):
1. SettingsScreen line 339: `SizedBox(height: 32)` → `MediaQuery.of(context).padding.bottom + AppTheme.space8` (Phase 6.A)
2. MemberDetailSheet line 40: `viewInsets.bottom` → `viewPadding.bottom` (Phase 6.F)
3. ProjectSwitcher line 120: `viewInsets.bottom` → `viewPadding.bottom` (Phase 6.G)
4. PdfImportPreviewScreen line 193: bottomNavigationBar not in SafeArea (Phase 8.B.1)
5. MpImportPreviewScreen line 72: bottomNavigationBar not in SafeArea (Phase 8.B.2)
6. HomeScreen line 1604: contractor picker sheet SafeArea (removed by Phase 4 simplification)

---

## Phase 7: Project Setup + Quantities

**Goal**: Restyle project setup tabs and quantities screens. Extract `AppBudgetWarningChip`.

**Commit**: `feat(projects-quantities): restyle with T Vivid and extract budget chip`

### Phase 7.A: QuantitiesScreen

**File**: `lib/features/quantities/presentation/screens/quantities_screen.dart`
**Violations**: 3 inline fontSize, `Colors.orange.shade800:173`, `Colors.amber.shade50:178`, `Colors.amber.shade200:179`.

#### Step 7.A.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Replace budget discrepancy chip (lines 173-179) with `AppBudgetWarningChip`
- Replace inline fontSize → `AppText.*`
- Use `AppGlassCard` for section containers

#### Step 7.A.2: Restyle quantities widgets

- `BidItemCard` (`lib/features/quantities/presentation/widgets/bid_item_card.dart`, 6 inline fontSize): Replace all → `AppText.*`. Wrap in `AppGlassCard`.
- `BidItemDetailSheet` (`lib/features/quantities/presentation/widgets/bid_item_detail_sheet.dart`, 11 inline fontSize): Replace all → `AppText.*`. Use `AppProgressBar` for usage bars.
- `QuantitySummaryHeader` (`lib/features/quantities/presentation/widgets/quantity_summary_header.dart`, fontSize 12,22): Replace → `AppText.bodySmall`/`AppText.titleLarge`.

### Phase 7.B: ProjectSetupScreen

**File**: `lib/features/projects/presentation/screens/project_setup_screen.dart`
**Violations**: 2 inline fontSize (10,12), 1 raw BR(4).

#### Step 7.B.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Keep tab structure (works well)
- Restyle tabs with T Vivid colors
- Replace `fontSize: 10` → `AppText.labelSmall`
- Replace `fontSize: 12` → `AppText.bodySmall`
- Replace `BR.circular(4)` → `AppTheme.radiusXSmall`
- Use `AppTextField` for form inputs
- Use `AppGlassCard` for tab content sections

#### Step 7.B.2: Restyle project widgets

- `PayItemSourceDialog` (`lib/features/projects/presentation/widgets/pay_item_source_dialog.dart`): Replace `fontSize:12,14` → `AppText.*`. Replace `BR.circular(6,8)` → `AppTheme.radiusCompact`/`AppTheme.radiusSmall`.
- `ProjectDetailsForm` (`lib/features/projects/presentation/widgets/project_details_form.dart`): Use `AppTextField` for inputs.
- `EquipmentChip` (`lib/features/projects/presentation/widgets/equipment_chip.dart`): Replace with `AppChip` usage.
- `AddContractorDialog`, `AddEquipmentDialog`, `AddLocationDialog`, `BidItemDialog`: Use `AppDialog` patterns, `AppTextField` for inputs. Apply T Vivid tokens.

### Phase 7.C: QuantityCalculatorScreen

Already fully tokenized — no changes needed.

### Phase 7.D: Quality Gate

1. `pwsh -Command "flutter analyze"` — zero issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Verify `AppBudgetWarningChip` used in both dashboard and quantities (no more copy-pasted warning chip)

**Commit**: `feat(projects-quantities): restyle with T Vivid and extract budget chip`

---

## Phase 8: Utility Screens

**Goal**: Restyle remaining utility screens — gallery, toolbox, calculator, PDF import, entry review screens.

**Commit**: `feat(utility): restyle remaining utility screens with T Vivid`

### Phase 8.A: GalleryScreen

**File**: `lib/features/gallery/presentation/screens/gallery_screen.dart`
**Violations**: 4 inline fontSize, 10 Colors violations (photo viewer overlay).

#### Step 8.A.1: Restyle

- Replace `Scaffold` with `AppScaffold`
- Replace photo viewer overlay colors:
  - `Colors.black:549,551` → `AppTheme.photoViewerBg`
  - `Colors.white:552,555,601` → `AppTheme.photoViewerText`
  - `Colors.white54:581,623` → `AppTheme.photoViewerTextDim`
  - `Colors.black87:593` → `AppTheme.photoViewerBg.withOpacity(0.87)` (or keep as-is, it's intentional)
  - `Colors.white70:609,615` → `AppTheme.photoViewerTextMuted`
- Replace inline fontSize → `AppText.*`

#### Step 8.A.2: Restyle photos widgets

- `PhotoThumbnail` (`lib/features/photos/presentation/widgets/photo_thumbnail.dart`): Replace `BR.circular(4,8)` → `AppTheme.radiusXSmall`/`AppTheme.radiusSmall`, `SizedBox(2)` keep as-is (sub-pixel intentional).
- `PhotoNameDialog` (`lib/features/photos/presentation/widgets/photo_name_dialog.dart`): Replace `fontSize:12` → `AppText.bodySmall`, `BR.circular(8)` → `AppTheme.radiusSmall`.
- `PhotoSourceDialog`: Apply T Vivid tokens.

### Phase 8.B: PDF Import Screens

#### Step 8.B.1: PdfImportPreviewScreen

**File**: `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`
**Violations**: 6 inline fontSize, 1 raw BR(4). **Bottom cutoff bug at line 193-195.**

- Replace `Scaffold` with `AppScaffold`
- **Fix bottom cutoff**: Wrap `bottomNavigationBar` content in `SafeArea`
- Replace `fontSize: 11,12,13,14,16` → `AppText.labelSmall`/`bodySmall`/`bodyMedium`/`bodyLarge`
- Replace `BR.circular(4)` → `AppTheme.radiusXSmall`
- Also restyle `_BidItemPreviewCard` (private inner class, same file) — 6 additional fontSize violations + 1 raw BR(4). Replace all → `AppText.*` and `AppTheme.radiusXSmall`.

#### Step 8.B.2: MpImportPreviewScreen

**File**: `lib/features/pdf/presentation/screens/mp_import_preview_screen.dart`
**Violations**: 4 inline fontSize (10,12,12,16). **Bottom cutoff bug at line 72.**

- Replace `Scaffold` with `AppScaffold`
- **Fix bottom cutoff**: Wrap `bottomNavigationBar` content in `SafeArea`
- Replace `fontSize: 10` → `AppText.labelSmall`
- Replace `fontSize: 12` → `AppText.bodySmall`
- Replace `fontSize: 16` → `AppText.bodyLarge`

#### Step 8.B.3: PdfImportProgressDialog

**File**: `lib/features/pdf/presentation/widgets/pdf_import_progress_dialog.dart`
**Violations**: 3 inline fontSize (13,14,16).

- Replace → `AppText.bodySmall`/`AppText.bodyMedium`/`AppText.titleMedium`
- Use `AppProgressBar` for import progress

### Phase 8.C: Entry Review Screens

#### Step 8.C.1: EntryReviewScreen

**File**: `lib/features/entries/presentation/screens/entry_review_screen.dart`
**Violations**: 2 inline fontSize.

- Replace `Scaffold` with `AppScaffold`
- Replace inline fontSize → `AppText.*`
- Use `AppGlassCard` for review sections

#### Step 8.C.2: ReviewSummaryScreen

**File**: `lib/features/entries/presentation/screens/review_summary_screen.dart`
**Violations**: 5 inline fontSize, `Colors.red:91`, `Colors.black.withValues:167`, `Colors.white:187`.

- Replace `Scaffold` with `AppScaffold`
- Replace `Colors.red:91` → `cs.error`
- Replace `Colors.black.withValues(alpha: 0.1):167` → `fg.shadowLight`
- Replace `Colors.white:187` → `fg.textInverse`
- Replace inline fontSize → `AppText.*`

#### Step 8.C.3: Restyle review widgets

- `ReviewFieldRow` (4 inline fontSize) → `AppText.*`
- `ReviewMissingWarning` (fontSize 12,13, BR(8)) → `AppText.bodySmall`, `AppTheme.radiusSmall`
- `SimpleInfoRow` (fontSize 12,14) → `AppText.bodySmall`/`AppText.bodyMedium`
- `SubmittedBanner` (fontSize 12,13) → `AppText.bodySmall`

### Phase 8.D: Forms Hub Widgets

#### Step 8.D.1: Restyle MdotHub child widgets

- `HubProctorContent` (`lib/features/forms/presentation/widgets/hub_proctor_content.dart`): **11 inline fontSize, 6 raw BR** — replace all. Use `AppGlassCard` for sections, `AppText.*` for text, `AppTheme.radius*` for borders. Replace `BR.circular(10,12)` → `radiusCompact`/`radiusMedium`, `BR.circular(999)` → `radiusFull`.
- `HubHeaderContent`: Replace `fontSize:10` → `AppText.labelSmall`, `BR.circular(10,12,999)` → tokens.
- `HubQuickTestContent`: Replace `fontSize:11` → `AppText.labelSmall`, `BR.circular(10,12)` → tokens.
- `SummaryTiles`: Replace `fontSize:11,15` → `AppText.labelSmall`/`AppText.bodyLarge`, `BR.circular(10)` → `radiusCompact`.
- `FormThumbnail`: Replace `fontSize:10` → `AppText.labelSmall`, `BR.circular(4,8)` → `radiusXSmall`/`radiusSmall`.

#### Step 8.D.2: Restyle `lib/features/forms/presentation/screens/form_viewer_screen.dart`

- Replace `Scaffold` with `AppScaffold`
- Fix inline dialogs (line 223: discard changes, line 546: text edit) — apply `AppDialog` styling
- Replace raw `EdgeInsets.symmetric(horizontal: 12, vertical: 10)` with token values
- Apply T Vivid tokens to any remaining violations

### Phase 8.E: Toolbox + Calculator

Already fully tokenized. Only change: replace `Scaffold` with `AppScaffold` if not already using SafeArea.

### Phase 8.F: Quality Gate

1. `pwsh -Command "flutter analyze"` — zero issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Verify PDF import bottom cutoff bugs fixed
4. Verify zero `Colors.*` violations in gallery photo viewer (uses named tokens now)
5. Update any existing PDF import, entry review, or forms tests

**Commit**: `feat(utility): restyle remaining utility screens with T Vivid`

---

## Phase 9: Auth Screens — Light Refresh

**Goal**: Swap to T Vivid tokens on all 10 auth screens. No structural changes — these are already the gold standard.

**Commit**: `feat(auth): light refresh with T Vivid tokens`

### Phase 9.A: Fix Colors.white Violations

#### Step 9.A.1: Replace Colors.white → AppTheme.textInverse

- `profile_setup_screen.dart:201` — `Colors.white` → `fg.textInverse`
- `company_setup_screen.dart:277` — `Colors.white` → `fg.textInverse`
- `company_setup_screen.dart:387` — `Colors.white` → `fg.textInverse`
- `edit_profile_screen.dart:240` — `Colors.white` → `fg.textInverse`
- `login_screen.dart` — check for any `Colors.white` on buttons
- `register_screen.dart` — check for any `Colors.white` on buttons

### Phase 9.B: Apply T Vivid Background

#### Step 9.B.1: Background color

If auth screens use `backgroundDark`, they'll automatically get the updated `tVividBackground` from the ThemeData change in Phase 1.A.4. If any use explicit `AppTheme.backgroundDark`, update to `AppTheme.tVividBackground` or just use the Scaffold's theme-inherited background.

### Phase 9.C: Minor Token Fixes

#### Step 9.C.1: Fix all violations in `update_required_screen.dart`

This screen has ~12 violations (not just fontSize):
- `fontSize: 13` (lines 75, 105) → `AppText.bodySmall`
- `fontSize: 14` (lines 133, 140) → `AppText.bodyMedium`
- `FontWeight.bold` (line 44) → use `AppText.titleLarge` or `AppText.titleMedium`
- `FontWeight.w600` (line 139) → use `AppText.labelLarge`
- `EdgeInsets.all(32)` (line 31) → `EdgeInsets.all(AppTheme.space8)`
- `EdgeInsets.all(16)` (line 58) → `EdgeInsets.all(AppTheme.space4)`
- `SizedBox(height: 24)` (line 40) → `SizedBox(height: AppTheme.space6)`
- `SizedBox(height: 16)` (lines 48, 97) → `SizedBox(height: AppTheme.space4)`
- `SizedBox(height: 32)` (line 83) → `SizedBox(height: AppTheme.space8)`
- `Icon size: 80` (line 37) → keep as-is (no token for 80px, intentionally large hero icon)

#### Step 9.C.2: Verify remaining auth screens are clean

These auth screens have been verified as fully tokenized — no changes needed:
- `forgot_password_screen.dart` — clean
- `update_password_screen.dart` — clean
- `pending_approval_screen.dart` — clean
- `account_status_screen.dart` — clean
- `otp_verification_screen.dart` — minor: `FontWeight.bold` at line 234 and raw `EdgeInsets.symmetric(vertical: 12)` at line 269. Fix both.

### Phase 9.D: Quality Gate

1. `pwsh -Command "flutter analyze"` — zero issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Verify zero `Colors.*` in `lib/features/auth/presentation/`
4. Verify no `Colors.*` or inline `TextStyle(fontSize:` in `lib/features/auth/presentation/` or `lib/features/settings/presentation/screens/edit_profile_screen.dart`

**Commit**: `feat(auth): light refresh with T Vivid tokens`

---

## Phase 10: Bottom Sheets + Dialogs

**Goal**: Migrate all ~40 modal surfaces to use `AppBottomSheet`/`AppDialog` with consistent drag handle, SafeArea, and glass styling.

**Commit**: `feat(modals): standardize all sheets and dialogs with T Vivid`

### Phase 10.A: Bottom Sheets (8 total)

For each bottom sheet, wrap with `AppBottomSheet.show()` to get consistent:
- Glass background (`surfaceElevated`)
- Rounded top corners (`radiusXLarge`)
- `AppDragHandle` at top
- SafeArea bottom padding

#### Step 10.A.1: Migrate each bottom sheet

| # | File | Current | Action |
|---|------|---------|--------|
| 1 | `admin_dashboard_screen.dart:367` | `showModalBottomSheet` + `MemberDetailSheet` | Use `AppBottomSheet.show`. Already restyled in Phase 6.F. |
| 2 | `bid_item_detail_sheet.dart:17` | `showModalBottomSheet` + DraggableScrollableSheet | Wrap outer in `AppBottomSheet.show`. Keep DraggableScrollableSheet inside. |
| 3 | `project_switcher.dart:69` | `showModalBottomSheet` + `_ProjectSwitcherSheet` | Use `AppBottomSheet.show`. Already fixed in Phase 6.G. |
| 4 | `photo_source_dialog.dart:25` | `showModalBottomSheet` | Use `AppBottomSheet.show`. |
| 5 | `gallery_screen.dart:304` | `showModalBottomSheet` photo options | Use `AppBottomSheet.show`. |
| 6 | ~~`home_screen.dart:1604`~~ | ~~contractor picker~~ | **Removed by Phase 4** — inline editing section deleted. No migration needed. |
| 7 | `bid_item_picker_sheet.dart:16` | `showModalBottomSheet` + DraggableScrollableSheet | Wrap outer in `AppBottomSheet.show`. Keep DraggableScrollableSheet inside. |
| 8 | `report_add_contractor_sheet.dart:16` | `showModalBottomSheet` (already has SafeArea) | Use `AppBottomSheet.show` for consistency. |

### Phase 10.B: Dialogs (~30 total)

For each dialog, ensure it uses `AppDialog` styling (surfaceElevated background, radiusLarge corners). For simple confirmations that use the shared `ConfirmationDialog`, update that single shared widget.

#### Step 10.B.1: Update shared `ConfirmationDialog`

**File**: `lib/shared/widgets/confirmation_dialog.dart`

Update the AlertDialog styling:
- `backgroundColor`: **Inherit from Theme** — do not set explicitly. The `dialogTheme.backgroundColor` is already configured per-theme. If explicit control needed, use `fg.surfaceElevated`.
- `shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusLarge))`
- Title text: use `AppText.titleLarge`
- Content text: use `AppText.bodyMedium`
- Button styles: T Vivid accent colors

This single change affects all confirmation dialogs across the app (delete project, archive project, restore/purge trash, approve/reject user, clear cache, sign out, role change, discard changes).

#### Step 10.B.2: Update form-input dialogs

These dialogs contain form fields — update to use `AppTextField` and T Vivid styling:

- `add_contractor_dialog.dart`
- `add_equipment_dialog.dart`
- `add_location_dialog.dart`
- `bid_item_dialog.dart`
- `photo_name_dialog.dart`
- `report_add_personnel_type_dialog.dart`
- `report_add_quantity_dialog.dart`
- `report_location_edit_dialog.dart`

For each: update AlertDialog background/shape, use `AppTextField` for inputs, use `AppText.*` for labels.

#### Step 10.B.3: Update remaining dialogs

- `pay_item_source_dialog.dart`: Replace BR(6,8) → tokens, fontSize 12,14 → `AppText.*`
- `form_selection_dialog.dart`: Replace fontSize 10 → `AppText.labelSmall`, BR(12) → `AppTheme.radiusMedium`
- `quantity_dialog.dart`: Replace fontSize 13 → `AppText.bodySmall`
- `photo_detail_dialog.dart`: Replace 2 fontSize → `AppText.*`, 5 BR(8) → `AppTheme.radiusSmall`
- `report_photo_detail_dialog.dart`: Replace 2 fontSize → `AppText.*`, 5 BR(8) → `AppTheme.radiusSmall`
- `report_weather_edit_dialog.dart`: Apply T Vivid tokens
- `report_debug_pdf_actions_dialog.dart`: Apply T Vivid tokens
- `report_delete_personnel_type_dialog.dart`: Apply T Vivid tokens
- `pdf_import_progress_dialog.dart`: Already done in Phase 8.B.3
- Todo create/edit/delete dialogs in `todos_screen.dart`: Apply T Vivid tokens
- Personnel type add/edit/delete dialogs in `personnel_types_screen.dart`: Apply T Vivid tokens

#### Step 10.B.4: Migrate remaining inline dialogs

These inline `showDialog` calls are not covered by the shared `ConfirmationDialog` or form-input dialogs above:

| # | File:Line | Dialog Purpose | Action |
|---|-----------|---------------|--------|
| 1 | `entries_list_screen.dart:524` | Delete entry confirmation | Apply `AppDialog` styling, use `fg.*` colors |
| 2 | `entry_editor_screen.dart:293` | Undo submission confirmation | Apply `AppDialog` styling |
| 3 | `review_summary_screen.dart:34` | Submit entries confirmation | Apply `AppDialog` styling |
| 4 | `entry_forms_section.dart:101` | Delete form confirmation | Apply `AppDialog` styling |
| 5 | `contractor_editor_widget.dart:322` | Add personnel type inline dialog | Apply `AppDialog` + `AppTextField` styling |
| 6 | `contractor_editor_widget.dart:357` | Delete personnel type confirmation | Apply `AppDialog` styling |
| 7 | `form_viewer_screen.dart:223` | Discard changes confirmation | Apply `AppDialog` styling |
| 8 | `form_viewer_screen.dart:546` | Text edit inline dialog | Apply `AppDialog` + `AppTextField` styling |
| 9 | `mdot_hub_screen.dart:590` | Unsaved changes confirmation | Apply `AppDialog` styling |
| 10 | `pdf_service.dart:322` | PDF password prompt | Apply `AppDialog` + `AppTextField` styling |
| 11 | `report_pdf_actions_dialog.dart` | PDF export actions | Apply T Vivid tokens (missing from Phase 10.B.3) |

### Phase 10.C: Update Shared Widgets

#### Step 10.C.1: Restyle remaining shared widgets

- `EmptyStateWidget` (`lib/shared/widgets/empty_state_widget.dart`): Consider replacing with `AppEmptyState` usage, or update internal styling to match.
- `PermissionDialog` (`lib/shared/widgets/permission_dialog.dart`): Apply T Vivid dialog styling.
- `SearchBarField` (`lib/shared/widgets/search_bar_field.dart`): Apply T Vivid input styling (glass background, cyan focus border).
- `StaleConfigWarning`, `VersionBanner`, `ViewOnlyBanner`: Apply T Vivid tokens.
- `ContextualFeedbackOverlay` (`lib/shared/widgets/contextual_feedback_overlay.dart`): Check for violations, apply T Vivid tokens.
- `DeletionNotificationBanner` — already restyled in Phase 4.B.1 (verify)
- `ViewOnlyBanner` — already addressed in Phase 4.B.1 (verify)

### Phase 10.D: Quality Gate

1. `pwsh -Command "flutter analyze"` — zero issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Verify all bottom sheets have drag handle + SafeArea
4. Verify all dialogs have surfaceElevated background + radiusLarge corners
5. Update any ConfirmationDialog tests (golden tests need regeneration)
6. Verify no dialogs were missed by searching for `showDialog(` across `lib/features/`

**Commit**: `feat(modals): standardize all sheets and dialogs with T Vivid`

---

## Phase 11: Performance Pass

**Goal**: Optimize scroll performance, add lazy loading, tune animations.

**Commit**: `perf: scroll smoothing, lazy slivers, repaint boundaries`

### Phase 11.A: RepaintBoundary

#### Step 11.A.1: Add RepaintBoundary to list items

Wrap these list item widgets in `RepaintBoundary`:
- `AppListTile` (add inside the component itself so all list screens benefit)
- `AppGlassCard` (add when used as list items — optional `bool wrapInRepaintBoundary = false` prop)
- `DraftEntryTile`
- `BidItemCard`
- `FormAccordion`
- `TrackedItemRow`
- `AlertItemRow`
- `DashboardStatCard`

### Phase 11.B: Lazy Slivers

#### Step 11.B.1: Convert long lists to SliverList.builder

Screens that need conversion from `ListView(children: [...])` to `ListView.builder` or `SliverList.builder`:
- `AdminDashboardScreen` — user lists can grow
- `TrashScreen` — deleted items can grow
- `ProjectListScreen` — project list (currently uses `ListView(`, NOT `.builder`)
- `SyncDashboardScreen` — sync table rows
- `ReviewSummaryScreen` — review entries
- `MpImportPreviewScreen` — import items
- `SettingsScreen` — fixed content, but convert for consistency

Already using `.builder` (no changes needed):
- `EntriesListScreen` — already uses `ListView.builder`
- `TodosScreen` — already uses `ListView.builder`
- `GalleryScreen` — verify `GridView.builder`

### Phase 11.C: Scroll Physics Tuning

#### Step 11.C.1: Consistent scroll physics

Add `BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics())` to all CustomScrollView/ListView instances for consistent iOS-like scroll feel across platforms. Or use `ClampingScrollPhysics` for Android-native feel — match the existing pattern in the app.

### Phase 11.D: Page Transitions

#### Step 11.D.1: Custom page transitions

Add smooth page transitions to `go_router` configuration in `lib/core/router/app_router.dart`:
- Use `CustomTransitionPage` with `FadeTransition` + `SlideTransition` combination
- Duration: `AppTheme.animationPageTransition` (350ms)
- Curve: `AppTheme.curveDecelerate` (easeOut)

### Phase 11.E: Quality Gate

1. `pwsh -Command "flutter analyze"` — zero issues
2. `pwsh -Command "flutter test"` — all tests pass
3. Visual smoke test: verify scrolling feels smooth on device

**Commit**: `perf: scroll smoothing, lazy slivers, repaint boundaries`

---

## Phase 12: Cleanup

**Goal**: Delete unused old widgets, remove any remaining hardcoded values, final validation.

**Commit**: `chore: remove old widgets and clean remaining hardcoded values`

### Phase 12.A: Delete Unused Widgets

#### Step 12.A.1: Identify and delete dead widgets

After all screens are rewritten, check if any old widget files are no longer imported:
- If `EmptyStateWidget` is fully replaced by `AppEmptyState`, delete it
- If `SectionHeader` (settings) is fully replaced by `AppSectionHeader`, delete it
- Any other widgets that were replaced by design system components

Use `grep -r 'import.*widget_name' lib/` to verify zero imports before deleting.

### Phase 12.B: Final Token Sweep

#### Step 12.B.1: Search for remaining violations

Run these searches to find any remaining hardcoded values:
1. `grep -r 'Colors\.' lib/features/` — should only find `Colors.transparent` (acceptable)
2. `grep -r 'TextStyle(fontSize:' lib/features/` — should be zero
3. `grep -r 'BorderRadius.circular(' lib/features/` — should only reference `AppTheme.radius*` tokens
4. `grep -r 'SizedBox(height: [0-9]' lib/features/` — should only find values without token equivalents (2, 3, 6 — sub-pixel)
5. `grep -r 'FontWeight\.' lib/features/` — should only be in design system components
6. `grep -r 'Color(0x' lib/features/` — should be zero (all hex colors should use named tokens, including sectionQuantities and sectionPhotos)

Fix any remaining violations found.

### Phase 12.C: Legacy Cleanup

#### Step 12.C.1: Remove legacy color aliases if unused

Check if these legacy aliases in `AppTheme` are still referenced anywhere:
- `secondaryAmber` (alias for `accentAmber`)
- `success` (alias for `statusSuccess`)
- `warning` (alias for `statusWarning`)
- `error` (alias for `statusError`)

If any are still used, do a find-and-replace to the canonical name, then remove the alias.

**Note**: These aliases are heavily used — `success` has 11+ usages, `warning` has 8+, `error` has 6+, `secondaryAmber` has 3. Total ~30+ replacements across 10+ files. Scope this as a systematic find-and-replace, not a quick cleanup.

### Phase 12.D: Final Quality Gate

1. `pwsh -Command "flutter analyze"` — zero errors, zero warnings
2. `pwsh -Command "flutter test"` — all tests pass
3. `pwsh -File tools/build.ps1 -Platform android -BuildType debug` — builds successfully
4. Install on device and smoke test:
   - Dashboard renders with T Vivid styling
   - Entry editor shows 7 color-coded glass sections
   - Calendar shows read-only date picker
   - All list screens show glass cards
   - Settings shows glass sections
   - Sync dashboard shows semantic colors (no raw red/green/amber)
   - All bottom sheets have drag handle + SafeArea
   - No bottom-cutoff bugs on any screen
   - Scrolling is smooth throughout

**Commit**: `chore: remove old widgets and clean remaining hardcoded values`

---

## Summary

| Phase | Scope | Files | Risk |
|-------|-------|-------|------|
| 1 | Foundation: tokens + 20 components | ~26 new files, 4 modified | LOW |
| 2 | Dashboard rewrite | 5 files | MEDIUM |
| 3 | Entry editor rewrite | 10 files | HIGH |
| 3.5 | Safety repeat-last toggles (new feature) | 2 files | LOW-MEDIUM |
| 4 | Calendar/Home simplification | 1 file (2000+ lines) | HIGH |
| 5 | List screens batch (8 screens) | ~12 files | LOW-MEDIUM |
| 6 | Settings + sync screens | ~11 files | MEDIUM |
| 7 | Project setup + quantities | ~10 files | MEDIUM |
| 8 | Utility screens | ~15 files | MEDIUM |
| 9 | Auth screens light refresh | ~8 files | LOW |
| 10 | Bottom sheets + dialogs (~40) | ~30 files | MEDIUM |
| 11 | Performance pass | ~10 files | LOW |
| 12 | Cleanup | Variable | LOW |

**Total estimated files touched**: ~100+ presentation files
**New files created**: ~24 (design system + barrel export)
**Bugs fixed**: 6 confirmed bottom-cutoff bugs
**Tokens added**: 20+ new tokens + FieldGuideColors ThemeExtension (16 per-theme color fields)
**Components created**: 20 reusable components + WeatherProvider

---

## Appendix A: Section Color Assignments (Entry Editor)

| Section | Accent Color | Hex |
|---------|-------------|-----|
| Basics | `cs.primary` | #00E5FF |
| Activities | `cs.tertiary` | #2196F3 |
| Contractors | `fg.accentAmber` | #FFC107 |
| Safety | `fg.statusSuccess` | #66BB6A |
| Quantities | `AppTheme.sectionQuantities` | #26C6DA |
| Photos | `AppTheme.sectionPhotos` | #BA68C8 |
| Forms | `cs.onSurfaceVariant` | #8B949E |

## Appendix B: Typography Mapping Cheat Sheet

| Old Pattern | New Pattern |
|-------------|-------------|
| `TextStyle(fontSize: 10)` | `AppText.labelSmall` (11px, closest) |
| `TextStyle(fontSize: 11, color: textSecondary)` | `AppText.labelSmall(color: cs.onSurfaceVariant)` |
| `TextStyle(fontSize: 12, color: textSecondary)` | `AppText.bodySmall(color: cs.onSurfaceVariant)` |
| `TextStyle(fontSize: 12, color: textTertiary)` | `AppText.bodySmall(color: fg.textTertiary)` |
| `TextStyle(fontSize: 13)` | `AppText.bodySmall` (12px, closest) |
| `TextStyle(fontSize: 14)` | `AppText.bodyMedium` |
| `TextStyle(fontSize: 14, fontWeight: bold)` | `AppText.labelLarge` |
| `TextStyle(fontSize: 15)` | `AppText.bodyLarge` (16px, closest) |
| `TextStyle(fontSize: 16)` | `AppText.bodyLarge` |
| `TextStyle(fontSize: 16, fontWeight: bold)` | `AppText.titleMedium` |
| `TextStyle(fontSize: 18)` | `AppText.titleLarge` (22px) or `headlineSmall` (24px) |
| `TextStyle(fontSize: 20)` | `AppText.headlineSmall` |
| `TextStyle(fontSize: 22)` | `AppText.titleLarge` |
| `TextStyle(fontSize: 36)` | `AppText.displaySmall` |

## Appendix C: Color Replacement Cheat Sheet

> **All replacements use theme-aware references** via `FieldGuideColors.of(context)` (`fg`) or `Theme.of(context).colorScheme` (`cs`). Do NOT replace `Colors.*` with static `AppTheme.*` color constants — that would still be hardcoded to a single theme.

| Old | New (theme-aware) | Source |
|-----|-------------------|--------|
| `Colors.red` | `cs.error` | ColorScheme |
| `Colors.green` | `fg.statusSuccess` | FieldGuideColors |
| `Colors.amber` | `fg.statusWarning` | FieldGuideColors |
| `Colors.orange` | `fg.statusWarning` | FieldGuideColors |
| `Colors.orange.shade800` | `fg.statusWarning` | FieldGuideColors |
| `Colors.amber.shade50` | `fg.warningBackground` | FieldGuideColors |
| `Colors.amber.shade200` | `fg.warningBorder` | FieldGuideColors |
| `Colors.grey` | `cs.onSurfaceVariant` | ColorScheme |
| `Colors.grey[300]` | `cs.outline` | ColorScheme |
| `Colors.grey.shade100` | `cs.outline` | ColorScheme |
| `Colors.white` (on primary bg) | `fg.textInverse` | FieldGuideColors |
| `Colors.black.withValues(alpha: 0.1)` | `fg.shadowLight` | FieldGuideColors |
| `Colors.black.withValues(alpha: 0.15)` | `fg.shadowLight` | FieldGuideColors |
| `Colors.black` (photo viewer) | `AppTheme.photoViewerBg` | Static (same across all themes) |
| `Colors.white` (photo viewer) | `AppTheme.photoViewerText` | Static (same across all themes) |
| `Colors.white70` (photo viewer) | `AppTheme.photoViewerTextMuted` | Static (same across all themes) |
| `Colors.white54` (photo viewer) | `AppTheme.photoViewerTextDim` | Static (same across all themes) |
| `Colors.transparent` | Keep as-is (acceptable) | — |

## Appendix D: Radius Replacement Cheat Sheet

| Old | New |
|-----|-----|
| `BorderRadius.circular(4)` | `BorderRadius.circular(AppTheme.radiusXSmall)` |
| `BorderRadius.circular(6)` | `BorderRadius.circular(AppTheme.radiusCompact)` |
| `BorderRadius.circular(8)` | `BorderRadius.circular(AppTheme.radiusSmall)` |
| `BorderRadius.circular(10)` | `BorderRadius.circular(AppTheme.radiusCompact)` |
| `BorderRadius.circular(12)` | `BorderRadius.circular(AppTheme.radiusMedium)` |
| `BorderRadius.circular(14)` | `BorderRadius.circular(AppTheme.radiusMedium)` |
| `BorderRadius.circular(16)` | `BorderRadius.circular(AppTheme.radiusLarge)` |
| `BorderRadius.circular(20)` | `BorderRadius.circular(AppTheme.radiusXLarge)` |
| `BorderRadius.circular(24)` | `BorderRadius.circular(AppTheme.radiusXLarge)` |
| `BorderRadius.circular(999)` | `BorderRadius.circular(AppTheme.radiusFull)` |
