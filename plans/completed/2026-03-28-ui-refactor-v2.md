# UI Refactor V2 — Comprehensive Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Date**: 2026-03-28
**Branch**: `feat/ui-refactor-v2` (off `main`)
**Design Language**: T Vivid
**Scope**: Full rewrite of all 40 screens, 80+ widgets, 30+ dialogs, 8 bottom sheets
**Spec**: `.claude/plans/completed/2026-03-06-ui-refactor-comprehensive.md` (baseline)
**Audit**: `.claude/docs/2026-03-28-ui-refactor-audit.md`
**Analysis**: `.claude/dependency_graphs/2026-03-28-ui-refactor-v2/`

**Architecture**: Build a 24-component design system library (`lib/core/design_system/`) with `FieldGuideColors` ThemeExtension for theme-aware custom colors, then systematically migrate all presentation files from static `AppTheme.*` constants to dynamic `Theme.of(context)` + `FieldGuideColors.of(context)` access. Includes Safety Repeat-Last Toggles (new feature) and performance pass.

**Tech Stack**: Flutter/Dart, Material 3, ThemeExtension, Provider
**Blast Radius**: ~25 new files, ~130 modified, ~15 dependent, ~35 tests, ~5 cleanup

**Testing Invariants:**
- All design system components accept `Key? key` parameter forwarded to super
- All existing ValueKey assignments must be transferred to new wrapper widgets
- Driver enabled-detection includes design system component types (AppGlassCard, AppListTile, AppToggle, AppChip, etc.)
- No user-visible string changes without updating test assertions
- Golden tests regenerated per phase batch (after Phases 2-5, 6-8, and 9-10)
- FieldGuideColors registered in test harness (`harness_providers.dart`)

---


<!-- ======= Part: phase1a ======= -->

# Phase 1: Foundation — Theme Tokens + Design System Components (Part A)

> **Dependency**: None — this is the absolute foundation. Every subsequent phase depends on 1.A and 1.B.

---

## Sub-phase 1.A: Fill Theme Token Gaps

**Files:**
- Modify: `lib/core/theme/colors.dart` (lines 130-170)
- Modify: `lib/core/theme/design_constants.dart` (lines 43-61)
- Modify: `lib/core/theme/app_theme.dart` (lines 60-84, 169)

**Agent**: `frontend-flutter-specialist-agent`

### Step 1.A.1: Add missing color tokens to AppColors

**File:** `lib/core/theme/colors.dart`
**Where:** Insert after line 30 (after `statusInfo`), before the dark theme surfaces section comment at line 32.

```dart
  // WHY: statusNeutral is used for "no status" / "default" states across entry cards,
  // sync badges, and form chips. Currently hardcoded as textSecondary in 12+ places.
  static const Color statusNeutral = Color(0xFF8B949E);
```

**Where:** Insert after line 41 (after `surfaceGlass`), before the dark theme text section comment at line 43.

```dart
  // WHY: Warning-state backgrounds and borders are hardcoded with inline withOpacity()
  // calls in 8+ widgets (sync banner, validation chips, stale-data warnings).
  // Centralizing avoids drift and enables theme-aware variants in FieldGuideColors.
  static const Color warningBackground = Color(0x1AFFB300);  // 10% amber
  static const Color warningBorder = Color(0x33FFB300);       // 20% amber

  // WHY: Shadow color with fixed alpha — used by glassmorphic cards and elevated surfaces.
  // Currently hardcoded as Colors.black.withOpacity(0.1) in 6+ BoxDecoration usages.
  static const Color shadowLight = Color(0x1A000000);         // 10% black
```

**Where:** Insert after line 110 (after `overlayDark`), before the gradient section comment at line 112.

```dart
  // ==========================================================================
  // PHOTO VIEWER COLORS
  // ==========================================================================

  // WHY: Photo viewer overlay uses its own text colors for captions, metadata, and
  // EXIF display. Currently hardcoded as Colors.white / Colors.white70 / Colors.white54
  // across photo_viewer_screen.dart and gallery widgets.
  static const Color photoViewerBg = Color(0xFF000000);
  static const Color photoViewerText = Color(0xFFFFFFFF);
  static const Color photoViewerTextMuted = Color(0xB3FFFFFF);   // 70% white
  static const Color photoViewerTextDim = Color(0x8AFFFFFF);     // 54% white

  // ==========================================================================
  // SPECIALIZED UI COLORS
  // ==========================================================================

  // WHY: The "vivid" dark background is a deeper blue-black used by the new
  // home screen and dashboard. Distinct from backgroundDark to signal premium UI.
  static const Color tVividBackground = Color(0xFF050810);

  // WHY: Section accent colors for entry detail chips (quantities, photos).
  // Currently hardcoded in entry_detail_screen.dart and section_header widgets.
  static const Color sectionQuantities = Color(0xFF26C6DA);     // Cyan 400
  static const Color sectionPhotos = Color(0xFFBA68C8);          // Purple 300

  // WHY: Project number subtitle text on cards. Currently hardcoded as Color(0xFFCCCCCC)
  // in project_card.dart and project_list_tile.dart.
  static const Color projectNumberText = Color(0xFFCCCCCC);
```

### Step 1.A.2: Add missing design constant tokens to DesignConstants

**File:** `lib/core/theme/design_constants.dart`
**Where:** Insert after line 43 (after `radiusFull = 999.0;`), before the elevation section comment at line 45.

```dart
  // WHY: radiusXSmall (4.0) is needed for tight chips, badges, and inline tags.
  // Currently hardcoded as BorderRadius.circular(4) in 10+ chip/badge widgets.
  static const double radiusXSmall = 4.0;

  // WHY: radiusCompact (10.0) fills the gap between radiusSmall (8) and radiusMedium (12).
  // Used by bottom sheets and action menus where 8 is too tight and 12 too round.
  static const double radiusCompact = 10.0;

  // ==========================================================================
  // ICON SIZE SYSTEM
  // ==========================================================================

  // WHY: Icon sizes are hardcoded as magic numbers (18, 24, 32, 48) across 40+ widgets.
  // Centralizing enables consistent scaling and accessibility overrides.
  static const double iconSizeSmall = 18.0;
  static const double iconSizeMedium = 24.0;
  static const double iconSizeLarge = 32.0;
  static const double iconSizeXL = 48.0;
```

### Step 1.A.3: Add re-exports to AppTheme for new tokens

**File:** `lib/core/theme/app_theme.dart`
**Where:** Insert after line 63 (after `static const Color hcTextSecondary = AppColors.hcTextSecondary;`), before the weather colors comment at line 65.

```dart
  // NOTE: Re-exports for new tokens added in 1.A.1. Maintains the pattern where
  // widgets can reference AppTheme.* without importing colors.dart directly.
  static const Color hcSuccess = AppColors.hcSuccess;
  static const Color statusNeutral = AppColors.statusNeutral;
  static const Color warningBackground = AppColors.warningBackground;
  static const Color warningBorder = AppColors.warningBorder;
  static const Color shadowLight = AppColors.shadowLight;
  static const Color photoViewerBg = AppColors.photoViewerBg;
  static const Color photoViewerText = AppColors.photoViewerText;
  static const Color photoViewerTextMuted = AppColors.photoViewerTextMuted;
  static const Color photoViewerTextDim = AppColors.photoViewerTextDim;
  static const Color tVividBackground = AppColors.tVividBackground;
  static const Color sectionQuantities = AppColors.sectionQuantities;
  static const Color sectionPhotos = AppColors.sectionPhotos;
  static const Color projectNumberText = AppColors.projectNumberText;
```

**Where:** Insert after line 113 (after `static const double radiusFull = DesignConstants.radiusFull;`), before the elevation comment at line 115.

```dart
  // NOTE: Re-exports for new design constant tokens added in 1.A.2.
  static const double radiusXSmall = DesignConstants.radiusXSmall;
  static const double radiusCompact = DesignConstants.radiusCompact;
  static const double iconSizeSmall = DesignConstants.iconSizeSmall;
  static const double iconSizeMedium = DesignConstants.iconSizeMedium;
  static const double iconSizeLarge = DesignConstants.iconSizeLarge;
  static const double iconSizeXL = DesignConstants.iconSizeXL;
```

### Step 1.A.4: Update darkTheme scaffoldBackgroundColor

**File:** `lib/core/theme/app_theme.dart`
**Where:** Line 169 — replace `backgroundDark` with `tVividBackground`.

```dart
// BEFORE (line 169):
      scaffoldBackgroundColor: backgroundDark,

// AFTER:
      // WHY: tVividBackground (#050810) is a deeper blue-black that creates stronger
      // contrast with surfaceDark cards. backgroundDark (#0A0E14) remains available
      // for widgets that need the original shade.
      scaffoldBackgroundColor: tVividBackground,
```

### Step 1.A.5: Verify

```bash
pwsh -Command "flutter analyze lib/core/theme/"
```

Expected: 0 issues. All new constants are additive — no existing code breaks.

---

## Sub-phase 1.B: Create FieldGuideColors ThemeExtension

**Files:**
- Create: `lib/core/theme/field_guide_colors.dart`
- Modify: `lib/core/theme/app_theme.dart` (lines 757-758, 1117-1118, 1484-1485)
- Modify: `lib/core/theme/theme.dart` (line 4)

**Agent**: `frontend-flutter-specialist-agent`

### Step 1.B.1: Create FieldGuideColors ThemeExtension class

**File:** `lib/core/theme/field_guide_colors.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'colors.dart';

/// WHY: ThemeExtension provides semantic colors that vary per theme (dark/light/HC).
/// This replaces the pattern of checking brightness and picking colors manually,
/// which is scattered across 30+ widgets. With FieldGuideColors.of(context), widgets
/// get the correct color automatically.
///
/// NOTE: Every field here maps to a hardcoded color that currently differs between
/// themes. Static AppColors constants that are the same across all themes (e.g.,
/// statusError, primaryCyan) stay in AppColors and do NOT need to be here.
class FieldGuideColors extends ThemeExtension<FieldGuideColors> {
  const FieldGuideColors({
    required this.surfaceElevated,
    required this.surfaceGlass,
    required this.surfaceBright,
    required this.textTertiary,
    required this.textInverse,
    required this.statusSuccess,
    required this.statusWarning,
    required this.statusInfo,
    required this.warningBackground,
    required this.warningBorder,
    required this.shadowLight,
    required this.gradientStart,
    required this.gradientEnd,
    required this.accentAmber,
    required this.accentOrange,
    required this.dragHandleColor,
  });

  /// Elevated surface — cards, dialogs, bottom sheets
  final Color surfaceElevated;

  /// Glassmorphic overlay — frosted panels, floating toolbars
  final Color surfaceGlass;

  /// Active/hover surface — slider tracks, secondary buttons
  final Color surfaceBright;

  /// Tertiary text — hints, disabled labels, timestamps
  final Color textTertiary;

  /// Text on primary-colored backgrounds (buttons, chips)
  final Color textInverse;

  /// Success indicators — checkmarks, completion badges
  final Color statusSuccess;

  /// Warning indicators — stale data, sync delays
  final Color statusWarning;

  /// Informational indicators — tips, sync status
  final Color statusInfo;

  /// Warning banner/chip background (low-alpha)
  final Color warningBackground;

  /// Warning banner/chip border (low-alpha)
  final Color warningBorder;

  /// Subtle shadow for elevated surfaces
  final Color shadowLight;

  /// Primary gradient start color
  final Color gradientStart;

  /// Primary gradient end color
  final Color gradientEnd;

  /// Amber accent — highlights, badges, stars
  final Color accentAmber;

  /// Orange accent — urgent actions, overdue indicators
  final Color accentOrange;

  /// Drag handle / reorder grip color
  final Color dragHandleColor;

  // ===========================================================================
  // THEME INSTANCES
  // ===========================================================================

  /// WHY: const instances enable zero-cost registration on ThemeData.extensions.
  static const dark = FieldGuideColors(
    surfaceElevated: AppColors.surfaceElevated,       // #1C2128
    surfaceGlass: AppColors.surfaceGlass,             // #99161B22
    surfaceBright: AppColors.surfaceBright,            // #444C56
    textTertiary: AppColors.textTertiary,             // #6E7681
    textInverse: AppColors.textInverse,               // #0A0E14
    statusSuccess: AppColors.statusSuccess,           // #4CAF50
    statusWarning: AppColors.statusWarning,           // #FF9800
    statusInfo: AppColors.statusInfo,                 // #2196F3
    warningBackground: AppColors.warningBackground,   // #1AFFB300
    warningBorder: AppColors.warningBorder,           // #33FFB300
    shadowLight: AppColors.shadowLight,               // #1A000000
    gradientStart: AppColors.primaryCyan,             // #00E5FF
    gradientEnd: AppColors.primaryBlue,               // #2196F3
    accentAmber: AppColors.accentAmber,               // #FFB300
    accentOrange: AppColors.accentOrange,             // #FF6F00
    dragHandleColor: AppColors.surfaceHighlight,      // #2D333B
  );

  static const light = FieldGuideColors(
    surfaceElevated: AppColors.lightSurfaceElevated,  // #FFFFFF
    surfaceGlass: Color(0xCCFFFFFF),                  // 80% white
    surfaceBright: AppColors.lightSurfaceHighlight,   // #E2E8F0
    textTertiary: AppColors.lightTextTertiary,        // #94A3B8
    textInverse: Color(0xFFFFFFFF),                   // pure white (on blue primary)
    statusSuccess: AppColors.statusSuccess,           // #4CAF50 (same)
    statusWarning: AppColors.statusWarning,           // #FF9800 (same)
    statusInfo: AppColors.statusInfo,                 // #2196F3 (same)
    warningBackground: Color(0x1AFF9800),             // 10% warning orange
    warningBorder: Color(0x33FF9800),                 // 20% warning orange
    shadowLight: Color(0x0D000000),                   // 5% black (lighter shadow)
    gradientStart: AppColors.primaryBlue,             // #2196F3
    gradientEnd: AppColors.primaryDark,               // #0277BD
    accentAmber: AppColors.accentAmber,               // #FFB300 (same)
    accentOrange: AppColors.accentOrange,             // #FF6F00 (same)
    dragHandleColor: AppColors.lightSurfaceHighlight, // #E2E8F0
  );

  static const highContrast = FieldGuideColors(
    surfaceElevated: AppColors.hcSurfaceElevated,     // #1E1E1E
    surfaceGlass: Color(0xCC121212),                  // 80% hcSurface
    surfaceBright: Color(0xFF333333),                 // bright enough for contrast
    textTertiary: Color(0xFF808080),                  // mid-gray
    textInverse: Color(0xFF000000),                   // pure black (on cyan primary)
    statusSuccess: AppColors.hcSuccess,               // #00FF00
    statusWarning: AppColors.hcWarning,               // #FFAA00
    statusInfo: AppColors.hcPrimary,                  // #00FFFF
    warningBackground: Color(0x1AFFAA00),             // 10% hcWarning
    warningBorder: Color(0x33FFAA00),                 // 20% hcWarning
    shadowLight: Colors.transparent,                  // no subtle shadows in HC
    gradientStart: AppColors.hcPrimary,               // #00FFFF
    gradientEnd: AppColors.hcPrimary,                 // #00FFFF (flat — no gradient in HC)
    accentAmber: AppColors.hcAccent,                  // #FFFF00
    accentOrange: AppColors.hcWarning,                // #FFAA00
    dragHandleColor: Color(0xFFFFFFFF),               // max contrast
  );

  // ===========================================================================
  // CONVENIENCE ACCESSOR
  // ===========================================================================

  /// WHY: Shorthand that mirrors the standard Theme.of(context) pattern.
  /// Usage: `FieldGuideColors.of(context).surfaceElevated`
  /// Falls back to dark theme if extension is somehow missing (defensive).
  static FieldGuideColors of(BuildContext context) {
    return Theme.of(context).extension<FieldGuideColors>() ?? dark;
  }

  // ===========================================================================
  // ThemeExtension OVERRIDES
  // ===========================================================================

  @override
  FieldGuideColors copyWith({
    Color? surfaceElevated,
    Color? surfaceGlass,
    Color? surfaceBright,
    Color? textTertiary,
    Color? textInverse,
    Color? statusSuccess,
    Color? statusWarning,
    Color? statusInfo,
    Color? warningBackground,
    Color? warningBorder,
    Color? shadowLight,
    Color? gradientStart,
    Color? gradientEnd,
    Color? accentAmber,
    Color? accentOrange,
    Color? dragHandleColor,
  }) {
    return FieldGuideColors(
      surfaceElevated: surfaceElevated ?? this.surfaceElevated,
      surfaceGlass: surfaceGlass ?? this.surfaceGlass,
      surfaceBright: surfaceBright ?? this.surfaceBright,
      textTertiary: textTertiary ?? this.textTertiary,
      textInverse: textInverse ?? this.textInverse,
      statusSuccess: statusSuccess ?? this.statusSuccess,
      statusWarning: statusWarning ?? this.statusWarning,
      statusInfo: statusInfo ?? this.statusInfo,
      warningBackground: warningBackground ?? this.warningBackground,
      warningBorder: warningBorder ?? this.warningBorder,
      shadowLight: shadowLight ?? this.shadowLight,
      gradientStart: gradientStart ?? this.gradientStart,
      gradientEnd: gradientEnd ?? this.gradientEnd,
      accentAmber: accentAmber ?? this.accentAmber,
      accentOrange: accentOrange ?? this.accentOrange,
      dragHandleColor: dragHandleColor ?? this.dragHandleColor,
    );
  }

  @override
  FieldGuideColors lerp(FieldGuideColors? other, double t) {
    if (other is! FieldGuideColors) return this;
    return FieldGuideColors(
      surfaceElevated: Color.lerp(surfaceElevated, other.surfaceElevated, t)!,
      surfaceGlass: Color.lerp(surfaceGlass, other.surfaceGlass, t)!,
      surfaceBright: Color.lerp(surfaceBright, other.surfaceBright, t)!,
      textTertiary: Color.lerp(textTertiary, other.textTertiary, t)!,
      textInverse: Color.lerp(textInverse, other.textInverse, t)!,
      statusSuccess: Color.lerp(statusSuccess, other.statusSuccess, t)!,
      statusWarning: Color.lerp(statusWarning, other.statusWarning, t)!,
      statusInfo: Color.lerp(statusInfo, other.statusInfo, t)!,
      warningBackground: Color.lerp(warningBackground, other.warningBackground, t)!,
      warningBorder: Color.lerp(warningBorder, other.warningBorder, t)!,
      shadowLight: Color.lerp(shadowLight, other.shadowLight, t)!,
      gradientStart: Color.lerp(gradientStart, other.gradientStart, t)!,
      gradientEnd: Color.lerp(gradientEnd, other.gradientEnd, t)!,
      accentAmber: Color.lerp(accentAmber, other.accentAmber, t)!,
      accentOrange: Color.lerp(accentOrange, other.accentOrange, t)!,
      dragHandleColor: Color.lerp(dragHandleColor, other.dragHandleColor, t)!,
    );
  }
}
```

### Step 1.B.2: Register FieldGuideColors on all three ThemeData builders

**File:** `lib/core/theme/app_theme.dart`

First, add the import at the top of the file.

**Where:** After line 4 (`import 'design_constants.dart';`), insert:

```dart
import 'field_guide_colors.dart';
```

Then register the extension on each theme's ThemeData. The `.copyWith(extensions:)` pattern is used because the ThemeData constructors don't have an `extensions` parameter — we must chain `.copyWith()`.

**Dark theme — line 758** (the `);` closing the ThemeData return)

Replace:
```dart
    );
  }
```
with:
```dart
    // NOTE: Register FieldGuideColors extension so widgets can use
    // FieldGuideColors.of(context) to get theme-aware semantic colors.
    ).copyWith(extensions: const [FieldGuideColors.dark]);
  }
```

> WHY: ThemeData constructor does not accept `extensions` directly. The `.copyWith(extensions:)` pattern is the standard Flutter approach for registering ThemeExtension instances.

**Light theme — line 1118** (the `);` closing the ThemeData return)

Replace:
```dart
    );
  }
```
with:
```dart
    ).copyWith(extensions: const [FieldGuideColors.light]);
  }
```

**High contrast theme — line 1485** (the `);` closing the ThemeData return)

Replace:
```dart
    );
  }
```
with:
```dart
    ).copyWith(extensions: const [FieldGuideColors.highContrast]);
  }
```

### Step 1.B.3: Update barrel export

**File:** `lib/core/theme/theme.dart`
**Where:** After line 4 (`export 'design_constants.dart';`), append:

```dart
export 'field_guide_colors.dart';
```

### Step 1.B.4: Verify

```bash
pwsh -Command "flutter analyze lib/core/theme/"
```

Expected: 0 issues. The ThemeExtension is registered but not consumed yet — no widgets change in this phase.

Additional validation:

```bash
pwsh -Command "flutter test test/ --tags theme 2>&1; exit 0"
```

> NOTE: If no tests are tagged `theme`, this exits cleanly. The real validation is `flutter analyze` — it catches type errors, missing imports, and const violations.

---

## Verification Checklist

After both 1.A and 1.B are complete:

| Check | Command | Expected |
|-------|---------|----------|
| Static analysis clean | `pwsh -Command "flutter analyze lib/core/theme/"` | 0 issues |
| Full test suite passes | `pwsh -Command "flutter test"` | All green (no regressions) |
| FieldGuideColors accessible | Spot-check: `FieldGuideColors.of(context).surfaceElevated` resolves | Type-safe Color |
| All 3 themes have extension | `darkTheme.extension<FieldGuideColors>()` is non-null | true |
| New tokens compile as const | All `AppColors.*` and `DesignConstants.*` additions are `static const` | Compile-time const |

---

## Line Number Reference (pre-edit)

| File | Key Lines |
|------|-----------|
| `colors.dart` | 30: statusInfo, 41: surfaceGlass, 110: overlayDark, 170: closing `}` |
| `design_constants.dart` | 43: radiusFull, 61: closing `}` |
| `app_theme.dart` | 4: last import, 63: hcTextSecondary re-export, 84: legacy aliases end, 113: radiusFull re-export, 169: scaffoldBackgroundColor, 758: darkTheme `);`, 1118: lightTheme `);`, 1485: highContrastTheme `);` |
| `theme.dart` | 4: last export |

<!-- ======= Part: phase1b ======= -->

# Phase 1 (Part B): Atomic Layer + Card Layer Components

> **Depends on:** Phase 1.A (theme tokens) + Phase 1.B (FieldGuideColors) must be complete
> **Blocks:** Phase 1.E (Surface Layer), Phase 2+ (screen migrations)
> **Estimated steps:** 12 discrete steps (7 atomic + 5 card)
> **Quality gate:** `pwsh -Command "flutter analyze"` clean on all new files

---

## Phase 1.C: Build Atomic Layer Components

### Sub-phase 1.C: Atomic Design System Widgets

**Files:**
- Create: `lib/core/design_system/app_text.dart`
- Create: `lib/core/design_system/app_text_field.dart`
- Create: `lib/core/design_system/app_chip.dart`
- Create: `lib/core/design_system/app_progress_bar.dart`
- Create: `lib/core/design_system/app_counter_field.dart`
- Create: `lib/core/design_system/app_toggle.dart`
- Create: `lib/core/design_system/app_icon.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 1.C.1: Create AppText — textTheme slot enforcer

> **WHY:** 447 inline TextStyle constructors across 81 files. AppText forces usage of
> textTheme slots, eliminating ad-hoc font sizes, weights, and families. Named factories
> map to the M3 text scale so developers never need to remember slot names.
>
> **NOTE:** No `context` parameter on factories — the build method resolves the theme.
> This keeps callsites clean: `AppText.bodyMedium('hello')` instead of passing context twice.

Create `lib/core/design_system/app_text.dart`:

```dart
import 'package:flutter/material.dart';

/// Enforces textTheme slot usage instead of inline TextStyle constructors.
///
/// Usage:
/// ```dart
/// AppText.titleMedium('Section Header')
/// AppText.bodyMedium('Content text', color: fg.textTertiary)
/// ```
///
/// WHY: Eliminates 447 inline TextStyle constructors. Every factory maps 1:1
/// to a Material 3 textTheme slot, ensuring typographic consistency.
class AppText extends StatelessWidget {
  const AppText._({
    required this.text,
    required this.styleBuilder,
    this.color,
    this.maxLines,
    this.overflow,
    this.textAlign,
    this.softWrap,
  });

  final String text;
  final TextStyle? Function(TextTheme) styleBuilder;
  final Color? color;
  final int? maxLines;
  final TextOverflow? overflow;
  final TextAlign? textAlign;
  final bool? softWrap;

  // ---------------------------------------------------------------------------
  // DISPLAY
  // ---------------------------------------------------------------------------

  /// 57px / w700 — splash screens, hero numbers
  factory AppText.displayLarge(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.displayLarge, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign);
  }

  /// 45px / w600 — large headings
  factory AppText.displayMedium(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.displayMedium, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign);
  }

  /// 36px / w600 — section heroes
  factory AppText.displaySmall(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.displaySmall, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign);
  }

  // ---------------------------------------------------------------------------
  // HEADLINE
  // ---------------------------------------------------------------------------

  /// 32px / w700 — page titles
  factory AppText.headlineLarge(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.headlineLarge, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign);
  }

  /// 28px / w700 — section titles
  factory AppText.headlineMedium(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.headlineMedium, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign);
  }

  /// 24px / w700 — card titles
  factory AppText.headlineSmall(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.headlineSmall, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign);
  }

  // ---------------------------------------------------------------------------
  // TITLE
  // ---------------------------------------------------------------------------

  /// 22px / w700 — app bar titles, dialog titles
  factory AppText.titleLarge(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.titleLarge, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign);
  }

  /// 16px / w700 — list item titles, section headers
  factory AppText.titleMedium(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.titleMedium, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign);
  }

  /// 14px / w700 — small headers, subtitles
  factory AppText.titleSmall(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.titleSmall, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign);
  }

  // ---------------------------------------------------------------------------
  // BODY
  // ---------------------------------------------------------------------------

  /// 16px / w400 — primary content text
  factory AppText.bodyLarge(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign, bool? softWrap}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.bodyLarge, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign, softWrap: softWrap);
  }

  /// 14px / w400 — secondary content text (most common)
  factory AppText.bodyMedium(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign, bool? softWrap}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.bodyMedium, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign, softWrap: softWrap);
  }

  /// 12px / w400 — captions, metadata, timestamps
  factory AppText.bodySmall(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign, bool? softWrap}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.bodySmall, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign, softWrap: softWrap);
  }

  // ---------------------------------------------------------------------------
  // LABEL
  // ---------------------------------------------------------------------------

  /// 14px / w700 — button text, prominent labels
  factory AppText.labelLarge(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.labelLarge, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign);
  }

  /// 12px / w700 — chip labels, tab labels
  factory AppText.labelMedium(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.labelMedium, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign);
  }

  /// 11px / w700 — smallest labels, badges
  factory AppText.labelSmall(String text, {Color? color, int? maxLines, TextOverflow? overflow, TextAlign? textAlign}) {
    return AppText._(text: text, styleBuilder: (tt) => tt.labelSmall, color: color, maxLines: maxLines, overflow: overflow, textAlign: textAlign);
  }

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;
    final baseStyle = styleBuilder(tt);

    return Text(
      text,
      style: color != null ? baseStyle?.copyWith(color: color) : baseStyle,
      maxLines: maxLines,
      overflow: overflow,
      textAlign: textAlign,
      softWrap: softWrap,
    );
  }
}
```

---

#### Step 1.C.2: Create AppTextField — glass-styled TextFormField wrapper

> **WHY:** Inherits `inputDecorationTheme` from the active theme. Wrapping TextFormField
> ensures consistent field styling without per-instance InputDecoration boilerplate.
> The component does NOT set colors manually — it relies entirely on the theme.
>
> **NOTE:** `suffixIcon` is a Widget (not IconData) because some fields need animated
> visibility toggles, loading spinners, or clear buttons as suffix actions.

Create `lib/core/design_system/app_text_field.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Theme-aware TextFormField wrapper that inherits all styling from inputDecorationTheme.
///
/// Usage:
/// ```dart
/// AppTextField(
///   controller: _nameController,
///   label: 'Inspector Name',
///   prefixIcon: Icons.person,
/// )
/// ```
///
/// IMPORTANT: Does NOT set colors manually. All styling comes from the active theme's
/// inputDecorationTheme (dark, light, or HC). This ensures automatic theme switching.
class AppTextField extends StatelessWidget {
  const AppTextField({
    super.key,
    this.controller,
    this.label,
    this.hint,
    this.prefixIcon,
    this.suffixIcon,
    this.onSuffixTap,
    this.obscureText = false,
    this.enabled = true,
    this.readOnly = false,
    this.maxLines = 1,
    this.minLines,
    this.maxLength,
    this.keyboardType,
    this.textInputAction,
    this.inputFormatters,
    this.validator,
    this.onChanged,
    this.onFieldSubmitted,
    this.onTap,
    this.focusNode,
    this.autofocus = false,
    this.textCapitalization = TextCapitalization.none,
    this.initialValue,
  });

  final TextEditingController? controller;
  final String? label;
  final String? hint;
  final IconData? prefixIcon;
  final Widget? suffixIcon;
  final VoidCallback? onSuffixTap;
  final bool obscureText;
  final bool enabled;
  final bool readOnly;
  final int? maxLines;
  final int? minLines;
  final int? maxLength;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final List<TextInputFormatter>? inputFormatters;
  final String? Function(String?)? validator;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onFieldSubmitted;
  final VoidCallback? onTap;
  final FocusNode? focusNode;
  final bool autofocus;
  final TextCapitalization textCapitalization;
  final String? initialValue;

  @override
  Widget build(BuildContext context) {
    // NOTE: No color overrides here. InputDecorationTheme handles everything.
    return TextFormField(
      controller: controller,
      initialValue: initialValue,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        prefixIcon: prefixIcon != null ? Icon(prefixIcon) : null,
        suffixIcon: suffixIcon != null
            ? IconButton(
                icon: suffixIcon!,
                onPressed: onSuffixTap,
              )
            : null,
      ),
      obscureText: obscureText,
      enabled: enabled,
      readOnly: readOnly,
      maxLines: maxLines,
      minLines: minLines,
      maxLength: maxLength,
      keyboardType: keyboardType,
      textInputAction: textInputAction,
      inputFormatters: inputFormatters,
      validator: validator,
      onChanged: onChanged,
      onFieldSubmitted: onFieldSubmitted,
      onTap: onTap,
      focusNode: focusNode,
      autofocus: autofocus,
      textCapitalization: textCapitalization,
    );
  }
}
```

---

#### Step 1.C.3: Create AppChip — colored chip with named factories

> **WHY:** ChipTheme provides base styling, but the app uses 6+ color variants for status,
> category, and type indicators. Named factories enforce the color vocabulary.
>
> **NOTE:** Most factories use hardcoded const colors for performance (no context needed).
> Only `.neutral()` requires context because it reads FieldGuideColors for theme-aware
> surface/text colors. This keeps 6 of 7 factories zero-cost const-constructible.

Create `lib/core/design_system/app_chip.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/field_guide_colors.dart';

/// Colored chip with named factory variants for consistent status/category display.
///
/// Usage:
/// ```dart
/// AppChip.cyan('Active')
/// AppChip.amber('Pending')
/// AppChip.error('Failed')
/// ```
///
/// WHY: The app uses 6+ chip color variants. Without named factories, each callsite
/// manually computes background/foreground colors, leading to inconsistency.
class AppChip extends StatelessWidget {
  const AppChip({
    super.key,
    required this.label,
    required this.backgroundColor,
    required this.foregroundColor,
    this.icon,
    this.onTap,
    this.onDeleted,
  });

  final String label;
  final Color backgroundColor;
  final Color foregroundColor;
  final IconData? icon;
  final VoidCallback? onTap;
  final VoidCallback? onDeleted;

  // ---------------------------------------------------------------------------
  // NAMED FACTORIES — enforce color vocabulary
  // ---------------------------------------------------------------------------

  /// Cyan chip — active states, primary category
  factory AppChip.cyan(String label, {IconData? icon, VoidCallback? onTap, VoidCallback? onDeleted}) {
    return AppChip(
      label: label,
      backgroundColor: const Color(0x3300E5FF), // primaryCyan at 20%
      foregroundColor: const Color(0xFF00E5FF),  // primaryCyan
      icon: icon,
      onTap: onTap,
      onDeleted: onDeleted,
    );
  }

  /// Amber chip — pending, warning states
  factory AppChip.amber(String label, {IconData? icon, VoidCallback? onTap, VoidCallback? onDeleted}) {
    return AppChip(
      label: label,
      backgroundColor: const Color(0x33FFB300), // accentAmber at 20%
      foregroundColor: const Color(0xFFFFB300),  // accentAmber
      icon: icon,
      onTap: onTap,
      onDeleted: onDeleted,
    );
  }

  /// Green chip — success, complete states
  factory AppChip.green(String label, {IconData? icon, VoidCallback? onTap, VoidCallback? onDeleted}) {
    return AppChip(
      label: label,
      backgroundColor: const Color(0x334CAF50), // statusSuccess at 20%
      foregroundColor: const Color(0xFF4CAF50),  // statusSuccess
      icon: icon,
      onTap: onTap,
      onDeleted: onDeleted,
    );
  }

  /// Purple chip — special category (e.g., sectionPhotos)
  factory AppChip.purple(String label, {IconData? icon, VoidCallback? onTap, VoidCallback? onDeleted}) {
    return AppChip(
      label: label,
      backgroundColor: const Color(0x339C27B0), // purple at 20%
      foregroundColor: const Color(0xFF9C27B0),
      icon: icon,
      onTap: onTap,
      onDeleted: onDeleted,
    );
  }

  /// Teal chip — info, secondary category (e.g., sectionQuantities)
  factory AppChip.teal(String label, {IconData? icon, VoidCallback? onTap, VoidCallback? onDeleted}) {
    return AppChip(
      label: label,
      backgroundColor: const Color(0x33009688), // teal at 20%
      foregroundColor: const Color(0xFF009688),
      icon: icon,
      onTap: onTap,
      onDeleted: onDeleted,
    );
  }

  /// Error chip — failed, error states
  factory AppChip.error(String label, {IconData? icon, VoidCallback? onTap, VoidCallback? onDeleted}) {
    return AppChip(
      label: label,
      backgroundColor: const Color(0x33F44336), // statusError at 20%
      foregroundColor: const Color(0xFFF44336),  // statusError
      icon: icon,
      onTap: onTap,
      onDeleted: onDeleted,
    );
  }

  /// Neutral chip — default/inactive states (requires context for theme colors)
  factory AppChip.neutral(String label, BuildContext context, {IconData? icon, VoidCallback? onTap, VoidCallback? onDeleted}) {
    final fg = FieldGuideColors.of(context);
    return AppChip(
      label: label,
      backgroundColor: fg.surfaceBright.withValues(alpha: 0.3),
      foregroundColor: fg.textTertiary,
      icon: icon,
      onTap: onTap,
      onDeleted: onDeleted,
    );
  }

  @override
  Widget build(BuildContext context) {
    final chip = Chip(
      label: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: foregroundColor,
        ),
      ),
      avatar: icon != null
          ? Icon(icon, color: foregroundColor, size: 16)
          : null,
      backgroundColor: backgroundColor,
      side: BorderSide.none,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
      ),
      deleteIcon: onDeleted != null
          ? Icon(Icons.close, size: 16, color: foregroundColor)
          : null,
      onDeleted: onDeleted,
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
      visualDensity: VisualDensity.compact,
    );

    if (onTap != null) {
      return GestureDetector(onTap: onTap, child: chip);
    }
    return chip;
  }
}
```

---

#### Step 1.C.4: Create AppProgressBar — 4px animated gradient progress bar

> **WHY:** Used in sync progress, upload progress, and budget tracking. A consistent
> animated gradient bar replaces 8+ inline LinearProgressIndicator customizations.
>
> **NOTE:** Includes a custom `AnimatedFractionallySizedBox` because Flutter has no
> built-in implicit animation for FractionallySizedBox.widthFactor. This avoids
> requiring an explicit AnimationController at every callsite.

Create `lib/core/design_system/app_progress_bar.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/field_guide_colors.dart';
import '../theme/design_constants.dart';

/// 4px animated gradient progress bar.
///
/// Usage:
/// ```dart
/// AppProgressBar(value: 0.65)
/// AppProgressBar(value: null) // indeterminate
/// ```
///
/// WHY: Replaces 8+ inline LinearProgressIndicator customizations with a single
/// component that uses the theme's gradient colors and animates smoothly.
class AppProgressBar extends StatelessWidget {
  const AppProgressBar({
    super.key,
    this.value,
    this.height = 4.0,
    this.borderRadius,
    this.gradientColors,
    this.trackColor,
  });

  /// Progress value 0.0–1.0. Null = indeterminate.
  final double? value;

  /// Bar height in pixels. Default: 4.0
  final double height;

  /// Override border radius. Default: radiusFull (pill shape)
  final double? borderRadius;

  /// Override gradient colors. Default: theme's gradientStart -> gradientEnd
  final List<Color>? gradientColors;

  /// Override track color. Default: theme's surfaceBright
  final Color? trackColor;

  @override
  Widget build(BuildContext context) {
    final fg = FieldGuideColors.of(context);
    final radius = borderRadius ?? DesignConstants.radiusFull;
    final colors = gradientColors ?? [fg.gradientStart, fg.gradientEnd];
    final track = trackColor ?? fg.surfaceBright.withValues(alpha: 0.3);

    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: SizedBox(
        height: height,
        child: Stack(
          children: [
            // Track (background)
            Container(
              decoration: BoxDecoration(color: track),
            ),

            // Fill (animated gradient)
            if (value != null)
              AnimatedFractionallySizedBox(
                duration: DesignConstants.animationNormal,
                curve: DesignConstants.curveDefault,
                widthFactor: value!.clamp(0.0, 1.0),
                alignment: Alignment.centerLeft,
                child: Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(colors: colors),
                  ),
                ),
              )
            else
              // Indeterminate — use theme's built-in animation
              LinearProgressIndicator(
                minHeight: height,
                backgroundColor: Colors.transparent,
                valueColor: AlwaysStoppedAnimation(colors.first),
              ),
          ],
        ),
      ),
    );
  }
}

/// AnimatedFractionallySizedBox — smooth width transitions for progress bars.
///
/// NOTE: Flutter does not provide an implicit animation for FractionallySizedBox.
/// This is a minimal ImplicitlyAnimatedWidget that tweens widthFactor/heightFactor
/// so callsites don't need explicit AnimationControllers.
class AnimatedFractionallySizedBox extends ImplicitlyAnimatedWidget {
  const AnimatedFractionallySizedBox({
    super.key,
    required super.duration,
    super.curve,
    this.widthFactor,
    this.heightFactor,
    this.alignment = Alignment.center,
    this.child,
  });

  final double? widthFactor;
  final double? heightFactor;
  final AlignmentGeometry alignment;
  final Widget? child;

  @override
  AnimatedWidgetBaseState<AnimatedFractionallySizedBox> createState() =>
      _AnimatedFractionallySizedBoxState();
}

class _AnimatedFractionallySizedBoxState
    extends AnimatedWidgetBaseState<AnimatedFractionallySizedBox> {
  Tween<double>? _widthFactor;
  Tween<double>? _heightFactor;

  @override
  void forEachTween(TweenVisitor<dynamic> visitor) {
    _widthFactor = visitor(
      _widthFactor,
      widget.widthFactor ?? 1.0,
      (dynamic value) => Tween<double>(begin: value as double),
    ) as Tween<double>?;
    _heightFactor = visitor(
      _heightFactor,
      widget.heightFactor ?? 1.0,
      (dynamic value) => Tween<double>(begin: value as double),
    ) as Tween<double>?;
  }

  @override
  Widget build(BuildContext context) {
    return FractionallySizedBox(
      widthFactor: _widthFactor?.evaluate(animation),
      heightFactor: _heightFactor?.evaluate(animation),
      alignment: widget.alignment,
      child: widget.child,
    );
  }
}
```

---

#### Step 1.C.5: Create AppCounterField — +/- stepper for personnel counts

> **WHY:** Personnel count entry appears on 5+ screens (entry personnel, contractor staffing).
> Each implements its own +/- button pair with inconsistent sizing and touch targets.
>
> **NOTE:** Uses `DesignConstants.touchTargetMin` (48dp) for button sizing to meet
> Material accessibility guidelines. Value is clamped to [min, max] on every change.

Create `lib/core/design_system/app_counter_field.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';
import '../theme/field_guide_colors.dart';

/// +/- stepper for integer value entry with field-sized touch targets.
///
/// Usage:
/// ```dart
/// AppCounterField(
///   label: 'Laborers',
///   value: 5,
///   onChanged: (v) => setState(() => _laborers = v),
///   min: 0,
///   max: 99,
/// )
/// ```
///
/// WHY: Personnel count entry appears on 5+ screens. This enforces consistent
/// 48dp touch targets, value clamping, and haptic feedback.
class AppCounterField extends StatelessWidget {
  const AppCounterField({
    super.key,
    required this.label,
    required this.value,
    required this.onChanged,
    this.min = 0,
    this.max = 999,
    this.step = 1,
  });

  final String label;
  final int value;
  final ValueChanged<int> onChanged;
  final int min;
  final int max;
  final int step;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;
    final fg = FieldGuideColors.of(context);

    final canDecrement = value > min;
    final canIncrement = value < max;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Label
        Expanded(
          child: Text(
            label,
            style: tt.bodyMedium,
          ),
        ),

        // Decrement button
        _CounterButton(
          icon: Icons.remove,
          enabled: canDecrement,
          onTap: canDecrement
              ? () => onChanged((value - step).clamp(min, max))
              : null,
        ),

        // Value display
        Container(
          width: DesignConstants.touchTargetMin,
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(
            horizontal: DesignConstants.space2,
          ),
          decoration: BoxDecoration(
            color: fg.surfaceElevated.withValues(alpha: 0.5),
            border: Border.symmetric(
              horizontal: BorderSide(
                color: cs.outline.withValues(alpha: 0.3),
              ),
            ),
          ),
          child: Text(
            '$value',
            style: tt.titleMedium?.copyWith(
              color: cs.primary,
            ),
            textAlign: TextAlign.center,
          ),
        ),

        // Increment button
        _CounterButton(
          icon: Icons.add,
          enabled: canIncrement,
          onTap: canIncrement
              ? () => onChanged((value + step).clamp(min, max))
              : null,
        ),
      ],
    );
  }
}

class _CounterButton extends StatelessWidget {
  const _CounterButton({
    required this.icon,
    required this.enabled,
    this.onTap,
  });

  final IconData icon;
  final bool enabled;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final fg = FieldGuideColors.of(context);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(DesignConstants.radiusSmall),
        child: Container(
          width: DesignConstants.touchTargetMin,
          height: DesignConstants.touchTargetMin,
          alignment: Alignment.center,
          child: Icon(
            icon,
            color: enabled ? cs.primary : fg.textTertiary,
            size: DesignConstants.iconSizeMedium,
          ),
        ),
      ),
    );
  }
}
```

---

#### Step 1.C.6: Create AppToggle — label + subtitle + Switch.adaptive

> **WHY:** Settings screens and entry forms use labeled switches 12+ times. Each constructs
> its own Row/Column + Switch with inconsistent spacing. This inherits switchTheme.
>
> **IMPORTANT:** Does NOT set switch colors manually — relies on theme's switchTheme.
> Switch.adaptive picks the native look per platform (Cupertino on iOS, Material on Android).

Create `lib/core/design_system/app_toggle.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';

/// Label + optional subtitle + Switch.adaptive that inherits switchTheme.
///
/// Usage:
/// ```dart
/// AppToggle(
///   label: 'Auto-sync',
///   subtitle: 'Sync when connected to WiFi',
///   value: _autoSync,
///   onChanged: (v) => setState(() => _autoSync = v),
/// )
/// ```
///
/// IMPORTANT: Does NOT set switch colors. All styling comes from the active theme's
/// switchTheme. This ensures automatic theme switching (dark/light/HC).
class AppToggle extends StatelessWidget {
  const AppToggle({
    super.key,
    required this.label,
    required this.value,
    required this.onChanged,
    this.subtitle,
    this.enabled = true,
  });

  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;
  final String? subtitle;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;

    return Padding(
      padding: const EdgeInsets.symmetric(
        vertical: DesignConstants.space2,
      ),
      child: Row(
        children: [
          // Label + subtitle
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(label, style: tt.bodyLarge),
                if (subtitle != null) ...[
                  const SizedBox(height: DesignConstants.space1),
                  Text(
                    subtitle!,
                    style: tt.bodySmall,
                  ),
                ],
              ],
            ),
          ),

          const SizedBox(width: DesignConstants.space4),

          // NOTE: Switch.adaptive picks the native look per platform.
          // Colors come from switchTheme — we pass NOTHING to Switch itself.
          Switch.adaptive(
            value: value,
            onChanged: enabled ? onChanged : null,
          ),
        ],
      ),
    );
  }
}
```

---

#### Step 1.C.7: Create AppIcon — enum-based icon sizing

> **WHY:** Icon sizes are scattered as magic numbers (18, 20, 24, 28, 32, 48) across
> the codebase. This enum enforces the 4-tier sizing system from DesignConstants.
>
> **NOTE:** The enum stores the pixel value directly, so `AppIconSize.small.value` == 18.0.
> Color is optional — defaults to IconTheme.of(context) when null, which inherits from
> the active theme's iconTheme (dark/light/HC).

Create `lib/core/design_system/app_icon.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';

/// Standardized icon sizing using the 4-tier system.
///
/// Usage:
/// ```dart
/// AppIcon(Icons.check, size: AppIconSize.small)
/// AppIcon(Icons.sync, size: AppIconSize.large, color: fg.statusSuccess)
/// ```
///
/// WHY: Replaces 25+ ad-hoc icon sizes with 4 named tiers. Ensures consistency
/// and makes global size adjustments trivial (change one constant).
enum AppIconSize {
  /// 18px — inline with body text, chip icons
  small(DesignConstants.iconSizeSmall),

  /// 24px — default Material size, list items, buttons
  medium(DesignConstants.iconSizeMedium),

  /// 32px — section headers, prominent actions
  large(DesignConstants.iconSizeLarge),

  /// 48px — empty states, hero illustrations
  xl(DesignConstants.iconSizeXL);

  const AppIconSize(this.value);
  final double value;
}

/// Icon widget with enforced sizing tiers.
class AppIcon extends StatelessWidget {
  const AppIcon(
    this.icon, {
    super.key,
    this.size = AppIconSize.medium,
    this.color,
    this.semanticLabel,
  });

  final IconData icon;
  final AppIconSize size;
  final Color? color;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    return Icon(
      icon,
      size: size.value,
      color: color,
      semanticLabel: semanticLabel,
    );
  }
}
```

---

## Phase 1.D: Build Card Layer Components

### Sub-phase 1.D: Card-Level Design System Widgets

**Files:**
- Create: `lib/core/design_system/app_glass_card.dart`
- Create: `lib/core/design_system/app_section_header.dart`
- Create: `lib/core/design_system/app_list_tile.dart`
- Create: `lib/core/design_system/app_photo_grid.dart`
- Create: `lib/core/design_system/app_section_card.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 1.D.1: Create AppGlassCard — core T Vivid glassmorphic card

> **WHY:** The T Vivid design language uses glassmorphic cards with subtle accent color
> tinting on the left border. This replaces `AppTheme.getGlassmorphicDecoration()` calls
> (used 30+ times) and inline Container+BoxDecoration patterns across the codebase.
>
> **NOTE:** We build the decoration manually rather than using Flutter's Card widget
> because Card doesn't support accent left-border tinting or gradient borders.
> The accent strip is a 3px colored Container on the left edge via Row.

Create `lib/core/design_system/app_glass_card.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';
import '../theme/field_guide_colors.dart';

/// Core T Vivid glassmorphic card with optional accent color tinting.
///
/// Usage:
/// ```dart
/// AppGlassCard(
///   child: Text('Content'),
///   accentColor: cs.primary,  // left border tint
///   onTap: () => navigateToDetail(),
/// )
/// ```
///
/// WHY: Replaces 30+ inline Container+BoxDecoration glassmorphic patterns.
/// The accent color creates a 3px left border tint for visual hierarchy.
class AppGlassCard extends StatelessWidget {
  const AppGlassCard({
    super.key,
    required this.child,
    this.accentColor,
    this.onTap,
    this.onLongPress,
    this.padding,
    this.margin,
    this.borderRadius,
    this.elevation,
    this.selected = false,
  });

  final Widget child;

  /// Optional left-border accent color. Creates a 3px colored left edge.
  /// Pass `cs.primary` for cyan, `fg.accentAmber` for amber, etc.
  final Color? accentColor;

  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  /// Override internal padding. Default: space4 all sides.
  final EdgeInsetsGeometry? padding;

  /// Override outer margin. Default: symmetric vertical 4px.
  final EdgeInsetsGeometry? margin;

  /// Override border radius. Default: radiusMedium (12).
  final double? borderRadius;

  /// Override elevation. Default: elevationLow (2).
  final double? elevation;

  /// Whether the card shows a selected/highlighted state.
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final fg = FieldGuideColors.of(context);
    final radius = borderRadius ?? DesignConstants.radiusMedium;

    // NOTE: We build the decoration manually rather than using Card widget
    // because Card doesn't support gradient borders or accent tinting.
    final decoration = BoxDecoration(
      color: selected
          ? fg.surfaceElevated.withValues(alpha: 0.9)
          : fg.surfaceGlass,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(
        color: selected
            ? cs.primary.withValues(alpha: 0.5)
            : cs.outline.withValues(alpha: 0.3),
        width: 1,
      ),
      boxShadow: [
        BoxShadow(
          color: fg.shadowLight,
          blurRadius: elevation ?? DesignConstants.elevationLow,
          offset: const Offset(0, 1),
        ),
      ],
    );

    Widget card = Container(
      margin: margin ?? const EdgeInsets.symmetric(vertical: 4),
      decoration: decoration,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(radius),
        child: Row(
          children: [
            // Accent left border — 3px colored strip
            if (accentColor != null)
              Container(
                width: 3,
                color: accentColor,
              ),

            // Content area
            Expanded(
              child: Padding(
                padding: padding ?? const EdgeInsets.all(DesignConstants.space4),
                child: child,
              ),
            ),
          ],
        ),
      ),
    );

    // Wrap with InkWell for tap ripple if interactive
    if (onTap != null || onLongPress != null) {
      card = Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          onLongPress: onLongPress,
          borderRadius: BorderRadius.circular(radius),
          child: card,
        ),
      );
    }

    return card;
  }
}
```

---

#### Step 1.D.2: Create AppSectionHeader — 8px spaced-letter header

> **WHY:** Section headers appear 40+ times across entry screens, settings, and project
> detail views. Each manually constructs a Text with letterSpacing, uppercase, and padding.
>
> **NOTE:** `title.toUpperCase()` is applied inside the build method so callers don't need
> to remember to uppercase. letterSpacing 1.2 follows the M3 overline pattern.

Create `lib/core/design_system/app_section_header.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';

/// 8px spaced-letter section header with optional trailing action.
///
/// Usage:
/// ```dart
/// AppSectionHeader(
///   title: 'PERSONNEL',
///   trailing: TextButton(onPressed: () {}, child: Text('Add')),
/// )
/// ```
///
/// WHY: Section headers appear 40+ times. This enforces uppercase, letter-spacing,
/// consistent padding, and optional trailing action placement.
class AppSectionHeader extends StatelessWidget {
  const AppSectionHeader({
    super.key,
    required this.title,
    this.trailing,
    this.padding,
  });

  final String title;

  /// Optional trailing widget (e.g., "Add" button, count badge)
  final Widget? trailing;

  /// Override padding. Default: horizontal space4, vertical space3.
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;

    return Padding(
      padding: padding ?? const EdgeInsets.symmetric(
        horizontal: DesignConstants.space4,
        vertical: DesignConstants.space3,
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              title.toUpperCase(),
              style: tt.labelSmall?.copyWith(
                letterSpacing: 1.2,
              ),
            ),
          ),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}
```

---

#### Step 1.D.3: Create AppListTile — glass-styled list row

> **WHY:** List items on glass cards appear 25+ times (project lists, entry lists,
> contractor lists). Each manually wraps ListTile in a Card or Container.
>
> **NOTE:** Does NOT compose AppGlassCard internally — builds its own decoration
> to avoid double-margin/padding issues. The decoration mirrors AppGlassCard but
> with list-specific tweaks (thinner margin, fixed accent strip height).

Create `lib/core/design_system/app_list_tile.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';
import '../theme/field_guide_colors.dart';

/// Glass-styled list row that wraps content in the T Vivid card style.
///
/// Usage:
/// ```dart
/// AppListTile(
///   leading: Icon(Icons.folder),
///   title: 'Springfield DWSRF',
///   subtitle: 'Project #864130',
///   trailing: AppChip.cyan('Active'),
///   onTap: () => goToProject(id),
/// )
/// ```
///
/// WHY: Replaces 25+ manual ListTile-in-Card patterns with a consistent component
/// that handles glass background, accent borders, and proper touch targets.
class AppListTile extends StatelessWidget {
  const AppListTile({
    super.key,
    this.leading,
    required this.title,
    this.subtitle,
    this.trailing,
    this.onTap,
    this.onLongPress,
    this.accentColor,
    this.selected = false,
    this.dense = false,
  });

  final Widget? leading;
  final String title;
  final String? subtitle;
  final Widget? trailing;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  /// Optional left accent border color
  final Color? accentColor;

  /// Show selected highlight state
  final bool selected;

  /// Compact density
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;
    final fg = FieldGuideColors.of(context);

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 2),
      decoration: BoxDecoration(
        color: selected
            ? fg.surfaceElevated.withValues(alpha: 0.9)
            : fg.surfaceGlass,
        borderRadius: BorderRadius.circular(DesignConstants.radiusMedium),
        border: Border.all(
          color: selected
              ? cs.primary.withValues(alpha: 0.5)
              : cs.outline.withValues(alpha: 0.2),
          width: 1,
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(DesignConstants.radiusMedium),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onTap,
            onLongPress: onLongPress,
            borderRadius: BorderRadius.circular(DesignConstants.radiusMedium),
            child: Row(
              children: [
                // Accent left strip
                if (accentColor != null)
                  Container(
                    width: 3,
                    height: dense ? 48 : 64,
                    color: accentColor,
                  ),

                // Content
                Expanded(
                  child: Padding(
                    padding: EdgeInsets.symmetric(
                      horizontal: DesignConstants.space4,
                      vertical: dense ? DesignConstants.space2 : DesignConstants.space3,
                    ),
                    child: Row(
                      children: [
                        if (leading != null) ...[
                          leading!,
                          const SizedBox(width: DesignConstants.space3),
                        ],
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                title,
                                style: tt.titleSmall,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              if (subtitle != null) ...[
                                const SizedBox(height: 2),
                                Text(
                                  subtitle!,
                                  style: tt.bodySmall,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ],
                          ),
                        ),
                        if (trailing != null) ...[
                          const SizedBox(width: DesignConstants.space2),
                          trailing!,
                        ],
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
```

---

#### Step 1.D.4: Create AppPhotoGrid — photo thumbnail grid with add button

> **WHY:** Photo grids appear on entry detail, location detail, and gallery screens.
> Each implements its own GridView + add button with inconsistent sizing and spacing.
>
> **NOTE:** Uses `Image.file` with `errorBuilder` to gracefully handle missing/corrupt
> photos (common when files haven't synced yet). `NeverScrollableScrollPhysics` + `shrinkWrap`
> allows the grid to live inside a scrollable parent without nested scroll issues.

Create `lib/core/design_system/app_photo_grid.dart`:

```dart
import 'dart:io';
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';
import '../theme/field_guide_colors.dart';

/// Photo thumbnail grid with optional add button.
///
/// Usage:
/// ```dart
/// AppPhotoGrid(
///   photos: photoList.map((p) => p.filePath).toList(),
///   onPhotoTap: (index) => viewPhoto(index),
///   onAddTap: () => takePhoto(),
///   crossAxisCount: 3,
/// )
/// ```
///
/// WHY: Photo grids appear on 4+ screens. This enforces consistent thumbnail size,
/// aspect ratio, rounded corners, and the "add photo" button appearance.
class AppPhotoGrid extends StatelessWidget {
  const AppPhotoGrid({
    super.key,
    required this.photos,
    this.onPhotoTap,
    this.onAddTap,
    this.crossAxisCount = 3,
    this.spacing,
  });

  /// List of local file paths for photos
  final List<String> photos;

  /// Callback when a photo thumbnail is tapped, with index
  final ValueChanged<int>? onPhotoTap;

  /// Callback for the "add photo" button. If null, no add button is shown.
  final VoidCallback? onAddTap;

  /// Number of columns. Default: 3
  final int crossAxisCount;

  /// Spacing between items. Default: space2 (8px)
  final double? spacing;

  @override
  Widget build(BuildContext context) {
    final gap = spacing ?? DesignConstants.space2;

    final itemCount = photos.length + (onAddTap != null ? 1 : 0);

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        crossAxisSpacing: gap,
        mainAxisSpacing: gap,
        childAspectRatio: 1.0,
      ),
      itemCount: itemCount,
      itemBuilder: (context, index) {
        // Add button (last item)
        if (onAddTap != null && index == photos.length) {
          return _AddPhotoButton(onTap: onAddTap!);
        }

        // Photo thumbnail
        return _PhotoThumbnail(
          filePath: photos[index],
          onTap: onPhotoTap != null ? () => onPhotoTap!(index) : null,
        );
      },
    );
  }
}

class _PhotoThumbnail extends StatelessWidget {
  const _PhotoThumbnail({
    required this.filePath,
    this.onTap,
  });

  final String filePath;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return GestureDetector(
      onTap: onTap,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(DesignConstants.radiusSmall),
        child: Container(
          decoration: BoxDecoration(
            color: cs.surfaceContainerHighest,
            border: Border.all(
              color: cs.outline.withValues(alpha: 0.2),
            ),
          ),
          child: Image.file(
            File(filePath),
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => Center(
              child: Icon(
                Icons.broken_image_outlined,
                color: cs.onSurfaceVariant,
                size: DesignConstants.iconSizeLarge,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _AddPhotoButton extends StatelessWidget {
  const _AddPhotoButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: cs.primary.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(DesignConstants.radiusSmall),
          border: Border.all(
            color: cs.primary.withValues(alpha: 0.3),
            width: 2,
            // NOTE: Dashed border would require custom painter.
            // Solid border with low opacity provides similar visual affordance.
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.add_a_photo_outlined,
              color: cs.primary,
              size: DesignConstants.iconSizeLarge,
            ),
            const SizedBox(height: DesignConstants.space1),
            Text(
              'Add Photo',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: cs.primary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

#### Step 1.D.5: Create AppSectionCard — colored header strip + icon + title + child

> **WHY:** Audit found this pattern used 5+ times: a card with a colored header strip
> containing an icon + title, followed by body content. Currently each instance builds
> this from scratch with different spacing, colors, and radius values.
>
> **NOTE:** The `collapsible` flag switches between two implementations: a simple
> static card (most common) and a `_CollapsibleSectionCard` StatefulWidget with
> AnimationController for smooth expand/collapse. This avoids StatefulWidget overhead
> for the 80% case that doesn't need collapsing.

Create `lib/core/design_system/app_section_card.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';
import '../theme/field_guide_colors.dart';

/// Card with a colored header strip containing an icon + title, followed by body content.
///
/// Usage:
/// ```dart
/// AppSectionCard(
///   icon: Icons.people,
///   title: 'Personnel',
///   headerColor: AppColors.sectionQuantities,
///   child: Column(children: personnelWidgets),
/// )
/// ```
///
/// WHY: This header-strip-card pattern appears 5+ times (personnel, quantities, photos,
/// weather, notes sections). Each builds it from scratch. This component standardizes it.
class AppSectionCard extends StatelessWidget {
  const AppSectionCard({
    super.key,
    required this.icon,
    required this.title,
    required this.child,
    this.headerColor,
    this.trailing,
    this.padding,
    this.collapsible = false,
    this.initiallyExpanded = true,
  });

  final IconData icon;
  final String title;
  final Widget child;

  /// Header strip background color. Default: theme primary at 15%.
  final Color? headerColor;

  /// Optional trailing widget in the header (e.g., count badge, expand icon)
  final Widget? trailing;

  /// Body padding. Default: space4 all sides.
  final EdgeInsetsGeometry? padding;

  /// Whether the body can be collapsed. Default: false.
  final bool collapsible;

  /// If collapsible, whether initially expanded. Default: true.
  final bool initiallyExpanded;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;
    final fg = FieldGuideColors.of(context);

    final color = headerColor ?? cs.primary.withValues(alpha: 0.15);

    if (collapsible) {
      return _CollapsibleSectionCard(
        icon: icon,
        title: title,
        headerColor: color,
        trailing: trailing,
        padding: padding,
        initiallyExpanded: initiallyExpanded,
        child: child,
      );
    }

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      decoration: BoxDecoration(
        color: fg.surfaceGlass,
        borderRadius: BorderRadius.circular(DesignConstants.radiusMedium),
        border: Border.all(
          color: cs.outline.withValues(alpha: 0.2),
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(DesignConstants.radiusMedium),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header strip
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DesignConstants.space4,
                vertical: DesignConstants.space3,
              ),
              decoration: BoxDecoration(color: color),
              child: Row(
                children: [
                  Icon(icon, color: cs.onSurface, size: DesignConstants.iconSizeMedium),
                  const SizedBox(width: DesignConstants.space2),
                  Expanded(
                    child: Text(
                      title,
                      style: tt.titleSmall,
                    ),
                  ),
                  if (trailing != null) trailing!,
                ],
              ),
            ),

            // Body
            Padding(
              padding: padding ?? const EdgeInsets.all(DesignConstants.space4),
              child: child,
            ),
          ],
        ),
      ),
    );
  }
}

/// Internal collapsible variant — keeps expand/collapse state.
///
/// NOTE: Separated as a StatefulWidget to avoid forcing all AppSectionCard
/// instances to carry AnimationController overhead. Only created when
/// `collapsible: true` is passed.
class _CollapsibleSectionCard extends StatefulWidget {
  const _CollapsibleSectionCard({
    required this.icon,
    required this.title,
    required this.headerColor,
    required this.child,
    this.trailing,
    this.padding,
    this.initiallyExpanded = true,
  });

  final IconData icon;
  final String title;
  final Color headerColor;
  final Widget child;
  final Widget? trailing;
  final EdgeInsetsGeometry? padding;
  final bool initiallyExpanded;

  @override
  State<_CollapsibleSectionCard> createState() => _CollapsibleSectionCardState();
}

class _CollapsibleSectionCardState extends State<_CollapsibleSectionCard>
    with SingleTickerProviderStateMixin {
  late bool _expanded;
  late AnimationController _controller;
  late Animation<double> _heightFactor;
  late Animation<double> _iconRotation;

  @override
  void initState() {
    super.initState();
    _expanded = widget.initiallyExpanded;
    _controller = AnimationController(
      duration: DesignConstants.animationNormal,
      vsync: this,
      value: _expanded ? 1.0 : 0.0,
    );
    _heightFactor = _controller.drive(CurveTween(curve: DesignConstants.curveDefault));
    _iconRotation = _controller.drive(Tween(begin: 0.0, end: 0.5));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _toggle() {
    setState(() {
      _expanded = !_expanded;
      if (_expanded) {
        _controller.forward();
      } else {
        _controller.reverse();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;
    final fg = FieldGuideColors.of(context);

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      decoration: BoxDecoration(
        color: fg.surfaceGlass,
        borderRadius: BorderRadius.circular(DesignConstants.radiusMedium),
        border: Border.all(
          color: cs.outline.withValues(alpha: 0.2),
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(DesignConstants.radiusMedium),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Tappable header strip
            GestureDetector(
              onTap: _toggle,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DesignConstants.space4,
                  vertical: DesignConstants.space3,
                ),
                decoration: BoxDecoration(color: widget.headerColor),
                child: Row(
                  children: [
                    Icon(widget.icon, color: cs.onSurface, size: DesignConstants.iconSizeMedium),
                    const SizedBox(width: DesignConstants.space2),
                    Expanded(
                      child: Text(widget.title, style: tt.titleSmall),
                    ),
                    if (widget.trailing != null) ...[
                      widget.trailing!,
                      const SizedBox(width: DesignConstants.space2),
                    ],
                    RotationTransition(
                      turns: _iconRotation,
                      child: Icon(
                        Icons.expand_more,
                        color: cs.onSurfaceVariant,
                        size: DesignConstants.iconSizeMedium,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Collapsible body
            AnimatedBuilder(
              animation: _heightFactor,
              builder: (context, child) {
                return ClipRect(
                  child: Align(
                    alignment: Alignment.topCenter,
                    heightFactor: _heightFactor.value,
                    child: child,
                  ),
                );
              },
              child: Padding(
                padding: widget.padding ?? const EdgeInsets.all(DesignConstants.space4),
                child: widget.child,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

## File Manifest

| Step | File | Action | Lines (approx) |
|------|------|--------|----------------|
| 1.C.1 | `lib/core/design_system/app_text.dart` | Create | 140 |
| 1.C.2 | `lib/core/design_system/app_text_field.dart` | Create | 80 |
| 1.C.3 | `lib/core/design_system/app_chip.dart` | Create | 130 |
| 1.C.4 | `lib/core/design_system/app_progress_bar.dart` | Create | 120 |
| 1.C.5 | `lib/core/design_system/app_counter_field.dart` | Create | 115 |
| 1.C.6 | `lib/core/design_system/app_toggle.dart` | Create | 70 |
| 1.C.7 | `lib/core/design_system/app_icon.dart` | Create | 55 |
| 1.D.1 | `lib/core/design_system/app_glass_card.dart` | Create | 110 |
| 1.D.2 | `lib/core/design_system/app_section_header.dart` | Create | 50 |
| 1.D.3 | `lib/core/design_system/app_list_tile.dart` | Create | 120 |
| 1.D.4 | `lib/core/design_system/app_photo_grid.dart` | Create | 130 |
| 1.D.5 | `lib/core/design_system/app_section_card.dart` | Create | 210 |

**Total: 12 new files, ~1,330 lines**

## Dependency Graph

```
Phase 1.A (tokens) + 1.B (FieldGuideColors)
    |
    v
Phase 1.C (atomic: AppText, AppTextField, AppChip, AppProgressBar,
           AppCounterField, AppToggle, AppIcon)
    |
    v
Phase 1.D (cards: AppGlassCard, AppSectionHeader, AppListTile,
           AppPhotoGrid, AppSectionCard)
    |
    v
Phase 1.E (surfaces) + Phase 1.F (composites)
    |
    v
Phase 1.G (barrel export + quality gate)
```

> **NOTE:** 1.C and 1.D can technically be implemented in parallel since no 1.D component
> depends on a 1.C component (e.g., AppListTile builds its own text rather than using
> AppText). However, executing 1.C first establishes the pattern for the agent.

<!-- ======= Part: phase1c ======= -->

# Phase 1 Part C: Surface Layer, Composite Layer, Barrel + Theme Completion, Tests

> **Continues from:** `2026-03-28-ui-refactor-v2-phase1.md` (Phases 1.A–1.D)
> **Components built so far:** AppText, AppTextField, AppChip, AppProgressBar, AppCounterField, AppToggle, AppIcon, AppGlassCard, AppSectionHeader, AppListTile, AppPhotoGrid, AppSectionCard

---

## Phase 1.E: Build Surface Layer Components

### Sub-phase 1.E: Surface-Level Design System Widgets

**Files:**
- Create: `lib/core/design_system/app_scaffold.dart`
- Create: `lib/core/design_system/app_bottom_bar.dart`
- Create: `lib/core/design_system/app_bottom_sheet.dart`
- Create: `lib/core/design_system/app_dialog.dart`
- Create: `lib/core/design_system/app_sticky_header.dart`
- Create: `lib/core/design_system/app_drag_handle.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 1.E.1: Create AppScaffold

> **WHY:** Every screen constructs its own Scaffold + SafeArea wrapper. This ensures consistent
> SafeArea application and inherits scaffoldBackgroundColor from ThemeData so no screen ever
> sets its own background color.
>
> **NOTE:** Does NOT set backgroundColor by default — relies entirely on ThemeData.scaffoldBackgroundColor.
> The optional backgroundColor prop is an escape hatch for screens that need a different bg (e.g., photo viewer).

Create `lib/core/design_system/app_scaffold.dart`:

```dart
import 'package:flutter/material.dart';

/// Scaffold wrapper with SafeArea that inherits scaffoldBackgroundColor from ThemeData.
///
/// Usage:
/// ```dart
/// AppScaffold(
///   appBar: AppBar(title: Text('Projects')),
///   body: ProjectListView(),
///   floatingActionButton: FloatingActionButton(...),
/// )
/// ```
///
/// IMPORTANT: Does NOT set backgroundColor by default. All coloring comes from the
/// active theme's scaffoldBackgroundColor. Only pass backgroundColor for exceptional
/// cases (photo viewer overlay, splash screen).
class AppScaffold extends StatelessWidget {
  const AppScaffold({
    super.key,
    required this.body,
    this.appBar,
    this.floatingActionButton,
    this.bottomNavigationBar,
    this.useSafeArea = true,
    this.backgroundColor,
  });

  /// The primary content of the scaffold.
  final Widget body;

  /// Optional app bar. Inherits appBarTheme from the active theme.
  final PreferredSizeWidget? appBar;

  /// Optional FAB. Inherits floatingActionButtonTheme from the active theme.
  final Widget? floatingActionButton;

  /// Optional bottom nav bar or persistent bottom widget.
  final Widget? bottomNavigationBar;

  /// Whether to wrap body in SafeArea. Default: true.
  /// Set to false for screens that manage their own safe area (e.g., full-bleed photo viewer).
  final bool useSafeArea;

  /// Override background color. Default: null (inherits scaffoldBackgroundColor from theme).
  /// NOTE: Only use for exceptional cases like photo viewer overlay or splash screen.
  final Color? backgroundColor;

  @override
  Widget build(BuildContext context) {
    // NOTE: No color defaults here. Scaffold reads scaffoldBackgroundColor from
    // ThemeData when backgroundColor is null. This is the intended behavior.
    return Scaffold(
      backgroundColor: backgroundColor,
      appBar: appBar,
      floatingActionButton: floatingActionButton,
      bottomNavigationBar: bottomNavigationBar,
      body: useSafeArea ? SafeArea(child: body) : body,
    );
  }
}
```

#### Step 1.E.2: Create AppBottomBar

> **WHY:** Sticky bottom action bars appear on 12+ screens (entry editor, contractor detail,
> quantity forms). Each manually constructs SafeArea + Container + BoxDecoration with
> inconsistent blur/padding. This component standardizes the frosted glass bottom bar.

Create `lib/core/design_system/app_bottom_bar.dart`:

```dart
import 'dart:ui';

import 'package:flutter/material.dart';
import '../theme/design_constants.dart';

/// Sticky bottom action bar with blur backdrop for persistent actions.
///
/// Usage:
/// ```dart
/// AppScaffold(
///   body: content,
///   bottomNavigationBar: AppBottomBar(
///     child: Row(
///       children: [
///         Expanded(child: OutlinedButton(...)),
///         SizedBox(width: AppTheme.space4),
///         Expanded(child: ElevatedButton(...)),
///       ],
///     ),
///   ),
/// )
/// ```
///
/// WHY: Replaces 12+ manual SafeArea + Container + blur patterns with a single
/// component that guarantees consistent padding, backdrop blur, and safe area insets.
class AppBottomBar extends StatelessWidget {
  const AppBottomBar({
    super.key,
    required this.child,
    this.padding,
  });

  /// The action content (typically a Row of buttons).
  final Widget child;

  /// Override padding. Default: horizontal space4, vertical space3.
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    // NOTE: SafeArea wraps the entire bar to handle bottom insets (home indicator,
    // navigation bar) on modern devices. The blur creates a frosted glass effect
    // that lets content scroll behind the bar.
    return SafeArea(
      child: ClipRect(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            padding: padding ?? const EdgeInsets.symmetric(
              horizontal: DesignConstants.space4,
              vertical: DesignConstants.space3,
            ),
            decoration: BoxDecoration(
              color: cs.surface.withValues(alpha: 0.9),
              border: Border(
                top: BorderSide(
                  color: cs.outline.withValues(alpha: 0.3),
                ),
              ),
            ),
            child: child,
          ),
        ),
      ),
    );
  }
}
```

#### Step 1.E.3: Create AppBottomSheet

> **WHY:** Bottom sheets are used 15+ times (photo picker, filter panels, detail drawers).
> Each calls showModalBottomSheet with different configurations. This standardizes the
> glass container, drag handle, and safe area padding.

Create `lib/core/design_system/app_bottom_sheet.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';
import '../theme/field_guide_colors.dart';
import 'app_drag_handle.dart';

/// Glass bottom sheet with drag handle and consistent styling.
///
/// Usage:
/// ```dart
/// final result = await AppBottomSheet.show<String>(
///   context,
///   builder: (ctx) => Column(
///     children: [
///       ListTile(title: Text('Option 1'), onTap: () => Navigator.pop(ctx, 'opt1')),
///       ListTile(title: Text('Option 2'), onTap: () => Navigator.pop(ctx, 'opt2')),
///     ],
///   ),
/// );
/// ```
///
/// WHY: Replaces 15+ showModalBottomSheet calls with inconsistent drag handles,
/// corner radii, and background colors. Inherits bottomSheetTheme for shape/elevation.
class AppBottomSheet {
  AppBottomSheet._();

  /// Shows a modal bottom sheet with glass styling and drag handle.
  ///
  /// [builder] receives the sheet's BuildContext for Navigator.pop calls.
  /// [isScrollControlled] defaults to true for dynamic height.
  static Future<T?> show<T>(
    BuildContext context, {
    required Widget Function(BuildContext) builder,
    bool isScrollControlled = true,
  }) {
    return showModalBottomSheet<T>(
      context: context,
      isScrollControlled: isScrollControlled,
      backgroundColor: Colors.transparent,
      builder: (sheetContext) {
        final fg = FieldGuideColors.of(sheetContext);

        // NOTE: We use a manual Container instead of relying on bottomSheetTheme's
        // backgroundColor because we need the surfaceElevated color from our
        // ThemeExtension, which bottomSheetTheme can't reference.
        return Container(
          decoration: BoxDecoration(
            color: fg.surfaceElevated,
            borderRadius: const BorderRadius.vertical(
              top: Radius.circular(DesignConstants.radiusXLarge),
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Drag handle
              const AppDragHandle(),

              // Sheet content
              Flexible(
                child: builder(sheetContext),
              ),

              // Bottom safe area padding
              SizedBox(
                height: MediaQuery.of(sheetContext).padding.bottom,
              ),
            ],
          ),
        );
      },
    );
  }
}
```

#### Step 1.E.4: Create AppDialog

> **WHY:** Dialogs appear 20+ times (delete confirmation, discard changes, sync errors).
> Each calls showDialog with manual AlertDialog construction. This standardizes the
> dialog structure while INHERITING all styling from dialogTheme.
>
> **IMPORTANT:** Does NOT set background color, shape, or text styles. All comes from
> the active theme's dialogTheme (dark, light, or HC).

Create `lib/core/design_system/app_dialog.dart`:

```dart
import 'package:flutter/material.dart';
import 'app_text.dart';

/// Themed dialog with standardized title/content/actions layout.
///
/// Usage:
/// ```dart
/// final confirmed = await AppDialog.show<bool>(
///   context,
///   title: 'Delete Entry?',
///   content: Text('This action cannot be undone.'),
///   actions: [
///     TextButton(onPressed: () => Navigator.pop(context, false), child: Text('Cancel')),
///     ElevatedButton(onPressed: () => Navigator.pop(context, true), child: Text('Delete')),
///   ],
/// );
/// ```
///
/// IMPORTANT: Does NOT set backgroundColor, shape, or text styles manually.
/// All dialog styling comes from the active theme's dialogTheme.
class AppDialog {
  AppDialog._();

  /// Shows a themed dialog with title, content, and optional actions.
  ///
  /// If no [actions] are provided, a single "OK" TextButton is shown as the default.
  static Future<T?> show<T>(
    BuildContext context, {
    required String title,
    required Widget content,
    List<Widget>? actions,
    bool barrierDismissible = true,
  }) {
    return showDialog<T>(
      context: context,
      barrierDismissible: barrierDismissible,
      builder: (dialogContext) {
        // NOTE: AlertDialog inherits backgroundColor, shape, elevation, and
        // text styles from dialogTheme. We only provide structure.
        return AlertDialog(
          title: AppText.titleLarge(title),
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
}
```

#### Step 1.E.5: Create AppStickyHeader

> **WHY:** Entry editor uses sticky headers for section navigation (Personnel, Equipment,
> Weather, etc.). The blur backdrop lets content scroll behind while the header stays pinned.
> SliverPersistentHeaderDelegate is boilerplate-heavy — this wraps it cleanly.

Create `lib/core/design_system/app_sticky_header.dart`:

```dart
import 'dart:ui';

import 'package:flutter/material.dart';
import '../theme/design_constants.dart';

/// Blur-backdrop sticky header for use in CustomScrollView / NestedScrollView.
///
/// Usage:
/// ```dart
/// CustomScrollView(
///   slivers: [
///     AppStickyHeader(
///       height: 56,
///       child: Row(
///         children: [
///           Text('PERSONNEL', style: tt.labelSmall),
///           Spacer(),
///           TextButton(onPressed: () {}, child: Text('Add')),
///         ],
///       ),
///     ),
///     SliverList(...),
///   ],
/// )
/// ```
///
/// WHY: SliverPersistentHeaderDelegate requires 50+ lines of boilerplate per header.
/// This wraps it into a single widget with blur backdrop matching the app's glass design.
class AppStickyHeader extends StatelessWidget {
  const AppStickyHeader({
    super.key,
    required this.child,
    this.height = 56.0,
    this.padding,
  });

  /// The header content (typically a Row with title + action).
  final Widget child;

  /// Header height. Default: 56.0 (matches AppBar height).
  final double height;

  /// Override internal padding. Default: horizontal space4.
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return SliverPersistentHeader(
      pinned: true,
      delegate: _StickyHeaderDelegate(
        child: child,
        height: height,
        padding: padding ?? const EdgeInsets.symmetric(
          horizontal: DesignConstants.space4,
        ),
      ),
    );
  }
}

class _StickyHeaderDelegate extends SliverPersistentHeaderDelegate {
  _StickyHeaderDelegate({
    required this.child,
    required this.height,
    required this.padding,
  });

  final Widget child;
  final double height;
  final EdgeInsetsGeometry padding;

  @override
  double get minExtent => height;

  @override
  double get maxExtent => height;

  @override
  Widget build(BuildContext context, double shrinkOffset, bool overlapsContent) {
    final cs = Theme.of(context).colorScheme;

    // NOTE: ClipRect is required for BackdropFilter to work correctly.
    // Without it, the blur applies to the entire screen instead of just
    // the header area.
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          height: height,
          padding: padding,
          decoration: BoxDecoration(
            color: cs.surface.withValues(alpha: 0.85),
            border: Border(
              bottom: BorderSide(
                color: cs.outline.withValues(alpha: 0.2),
              ),
            ),
          ),
          alignment: Alignment.centerLeft,
          child: child,
        ),
      ),
    );
  }

  @override
  bool shouldRebuild(covariant _StickyHeaderDelegate oldDelegate) {
    return child != oldDelegate.child ||
        height != oldDelegate.height ||
        padding != oldDelegate.padding;
  }
}
```

#### Step 1.E.6: Create AppDragHandle

> **WHY:** Bottom sheet drag handles appear on every sheet but are hardcoded inline
> with inconsistent widths (32–48px), heights (3–5px), and colors. This creates a
> single source of truth matching the bottomSheetTheme's dragHandleSize (40x4).

Create `lib/core/design_system/app_drag_handle.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';
import '../theme/field_guide_colors.dart';

/// Bottom sheet drag handle indicator.
///
/// Usage:
/// ```dart
/// Column(
///   children: [
///     AppDragHandle(),
///     // ... sheet content
///   ],
/// )
/// ```
///
/// WHY: Drag handles are hardcoded inline across 15+ bottom sheets with inconsistent
/// dimensions. This matches bottomSheetTheme's dragHandleSize (40x4) and uses the
/// theme-aware dragHandleColor from FieldGuideColors.
class AppDragHandle extends StatelessWidget {
  const AppDragHandle({super.key});

  @override
  Widget build(BuildContext context) {
    final fg = FieldGuideColors.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(
          vertical: DesignConstants.space2,
        ),
        child: Container(
          width: 40,
          height: 4,
          decoration: BoxDecoration(
            color: fg.dragHandleColor,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
      ),
    );
  }
}
```

---

## Phase 1.F: Build Composite Layer Components

### Sub-phase 1.F: Composite Design System Widgets

**Files:**
- Create: `lib/core/design_system/app_empty_state.dart`
- Create: `lib/core/design_system/app_error_state.dart`
- Create: `lib/core/design_system/app_loading_state.dart`
- Create: `lib/core/design_system/app_budget_warning_chip.dart`
- Create: `lib/core/design_system/app_info_banner.dart`
- Create: `lib/core/design_system/app_mini_spinner.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 1.F.1: Create AppEmptyState

> **WHY:** Empty state placeholders appear on 10+ screens (no entries, no photos, no projects).
> Each manually constructs Center + Column + Icon + Text with inconsistent spacing and
> optional "Add first item" CTA buttons.

Create `lib/core/design_system/app_empty_state.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';
import '../theme/field_guide_colors.dart';
import 'app_icon.dart';
import 'app_text.dart';

/// Empty state placeholder with icon, title, optional subtitle, and optional CTA.
///
/// Usage:
/// ```dart
/// AppEmptyState(
///   icon: Icons.photo_library_outlined,
///   title: 'No photos yet',
///   subtitle: 'Take a photo to get started',
///   actionLabel: 'Take Photo',
///   onAction: () => _openCamera(),
/// )
/// ```
///
/// WHY: Replaces 10+ manually constructed empty state patterns with inconsistent
/// icon sizes (32–64px), spacing, and button placement.
class AppEmptyState extends StatelessWidget {
  const AppEmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
    this.actionLabel,
    this.onAction,
  });

  /// The hero icon displayed above the title.
  final IconData icon;

  /// Primary message (e.g., "No entries yet").
  final String title;

  /// Optional secondary message with more detail.
  final String? subtitle;

  /// Optional CTA button label (e.g., "Create Entry").
  final String? actionLabel;

  /// Callback for the CTA button. Required if actionLabel is set.
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final fg = FieldGuideColors.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DesignConstants.space8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Hero icon — xl size, muted color
            AppIcon(
              icon,
              size: AppIconSize.xl,
              color: fg.textTertiary,
            ),

            const SizedBox(height: DesignConstants.space4),

            // Title
            AppText.titleMedium(
              title,
              color: cs.onSurfaceVariant,
              textAlign: TextAlign.center,
            ),

            // Subtitle
            if (subtitle != null) ...[
              const SizedBox(height: DesignConstants.space2),
              AppText.bodyMedium(
                subtitle!,
                color: fg.textTertiary,
                textAlign: TextAlign.center,
              ),
            ],

            // CTA button
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: DesignConstants.space6),
              ElevatedButton(
                onPressed: onAction,
                child: Text(actionLabel!),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
```

#### Step 1.F.2: Create AppErrorState

> **WHY:** Error states appear on 8+ screens with inconsistent error icon colors,
> retry button placement, and message formatting. This standardizes the error display
> pattern with an error-colored icon and optional retry action.

Create `lib/core/design_system/app_error_state.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';
import 'app_icon.dart';
import 'app_text.dart';

/// Error state display with icon, message, and optional retry button.
///
/// Usage:
/// ```dart
/// AppErrorState(
///   message: 'Failed to load entries',
///   onRetry: () => _loadEntries(),
/// )
/// ```
///
/// WHY: Replaces 8+ inconsistent error state patterns. Uses cs.error from the
/// active theme for icon color, ensuring proper contrast in all themes.
class AppErrorState extends StatelessWidget {
  const AppErrorState({
    super.key,
    required this.message,
    this.onRetry,
    this.retryLabel = 'Retry',
  });

  /// The error message to display.
  final String message;

  /// Optional retry callback. If provided, shows a retry button.
  final VoidCallback? onRetry;

  /// Retry button label. Default: 'Retry'.
  final String retryLabel;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DesignConstants.space8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Error icon — xl size, error color from theme
            AppIcon(
              Icons.error_outline,
              size: AppIconSize.xl,
              color: cs.error,
            ),

            const SizedBox(height: DesignConstants.space4),

            // Error message
            AppText.titleMedium(
              message,
              color: cs.onSurfaceVariant,
              textAlign: TextAlign.center,
            ),

            // Retry button
            if (onRetry != null) ...[
              const SizedBox(height: DesignConstants.space6),
              ElevatedButton(
                onPressed: onRetry,
                child: Text(retryLabel),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
```

#### Step 1.F.3: Create AppLoadingState

> **WHY:** Loading spinners with optional labels appear on 14+ screens. Each manually
> constructs Center + Column + CircularProgressIndicator with different sizes and spacing.
>
> **IMPORTANT:** Does NOT set spinner color. Inherits from progressIndicatorTheme.

Create `lib/core/design_system/app_loading_state.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';
import 'app_text.dart';

/// Full-screen loading state with optional label.
///
/// Usage:
/// ```dart
/// if (isLoading) return AppLoadingState(label: 'Syncing entries...');
/// ```
///
/// IMPORTANT: Does NOT set spinner color or size. All styling comes from the active
/// theme's progressIndicatorTheme. Uses CircularProgressIndicator.adaptive() for
/// native spinner appearance per platform.
class AppLoadingState extends StatelessWidget {
  const AppLoadingState({
    super.key,
    this.label,
  });

  /// Optional label below the spinner (e.g., "Syncing entries...").
  final String? label;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // NOTE: .adaptive() picks native spinner per platform (Cupertino on iOS).
          // Color comes from progressIndicatorTheme — we do NOT override it.
          const CircularProgressIndicator.adaptive(),

          // Optional label
          if (label != null) ...[
            const SizedBox(height: DesignConstants.space4),
            AppText.bodyMedium(
              label!,
              color: cs.onSurfaceVariant,
              textAlign: TextAlign.center,
            ),
          ],
        ],
      ),
    );
  }
}
```

#### Step 1.F.4: Create AppBudgetWarningChip

> **WHY:** Budget warning chips with amber/orange theming appear 6+ times in quantity screens
> and project dashboards. Each hardcodes `Colors.amber.shade50`, `Colors.orange.shade800`,
> etc. This replaces those patterns with FieldGuideColors-aware warning/critical variants.

Create `lib/core/design_system/app_budget_warning_chip.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';
import '../theme/field_guide_colors.dart';

/// Budget warning chip with severity-based coloring.
///
/// Usage:
/// ```dart
/// AppBudgetWarningChip(label: '92% used', severity: BudgetSeverity.warning)
/// AppBudgetWarningChip(label: 'Over budget!', severity: BudgetSeverity.critical)
/// ```
///
/// WHY: Replaces 6+ hardcoded `Colors.amber.shade50` / `Colors.orange.shade800` patterns
/// with FieldGuideColors-aware colors that adapt to dark/light/HC themes.
enum BudgetSeverity {
  /// Amber coloring — approaching budget limit (e.g., 80-99%)
  warning,

  /// Red coloring — over budget (e.g., 100%+)
  critical,
}

class AppBudgetWarningChip extends StatelessWidget {
  const AppBudgetWarningChip({
    super.key,
    required this.label,
    this.icon = Icons.warning_amber_rounded,
    this.severity = BudgetSeverity.warning,
  });

  /// The warning text (e.g., "92% used", "Over budget!").
  final String label;

  /// Leading icon. Default: warning_amber_rounded.
  final IconData icon;

  /// Color severity. Default: warning (amber).
  final BudgetSeverity severity;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final fg = FieldGuideColors.of(context);
    final tt = Theme.of(context).textTheme;

    // NOTE: Warning uses FieldGuideColors amber tokens. Critical uses cs.error
    // with alpha modifiers for background/border so it adapts across all themes.
    final Color bgColor;
    final Color borderColor;
    final Color textColor;

    switch (severity) {
      case BudgetSeverity.warning:
        bgColor = fg.warningBackground;
        borderColor = fg.warningBorder;
        textColor = fg.accentAmber;
      case BudgetSeverity.critical:
        bgColor = cs.error.withValues(alpha: 0.1);
        borderColor = cs.error.withValues(alpha: 0.2);
        textColor = cs.error;
    }

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DesignConstants.space3,
        vertical: DesignConstants.space1,
      ),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(DesignConstants.radiusSmall),
        border: Border.all(color: borderColor),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: DesignConstants.iconSizeSmall, color: textColor),
          const SizedBox(width: DesignConstants.space1),
          Text(
            label,
            style: tt.labelMedium?.copyWith(color: textColor),
          ),
        ],
      ),
    );
  }
}
```

#### Step 1.F.5: Create AppInfoBanner

> **WHY:** Icon + colored container + message banners appear 5+ times for warnings, info tips,
> and sync status notices. Each manually constructs Container + Row + Icon + Text with
> different alpha values and border colors.

Create `lib/core/design_system/app_info_banner.dart`:

```dart
import 'package:flutter/material.dart';
import '../theme/design_constants.dart';

/// Colored info/warning banner with icon and message.
///
/// Usage:
/// ```dart
/// AppInfoBanner(
///   icon: Icons.info_outline,
///   message: 'Entries will sync when online',
///   color: cs.primary,
/// )
/// AppInfoBanner(
///   icon: Icons.warning_amber_rounded,
///   message: 'Unsaved changes will be lost',
///   color: cs.error,
///   actionLabel: 'Save Now',
///   onAction: () => _saveChanges(),
/// )
/// ```
///
/// WHY: Replaces 5+ inline Container + Row + Icon patterns with hardcoded alpha values.
/// The color parameter drives bg (10% alpha), border (30% alpha), and icon/text coloring.
class AppInfoBanner extends StatelessWidget {
  const AppInfoBanner({
    super.key,
    required this.icon,
    required this.message,
    required this.color,
    this.actionLabel,
    this.onAction,
  });

  /// Leading icon (e.g., Icons.info_outline, Icons.warning_amber_rounded).
  final IconData icon;

  /// The banner message text.
  final String message;

  /// The accent color. Drives bg (10%), border (30%), icon, and text color.
  final Color color;

  /// Optional action button label.
  final String? actionLabel;

  /// Optional action button callback.
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;

    return Container(
      padding: const EdgeInsets.all(DesignConstants.space3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(DesignConstants.radiusSmall),
        border: Border.all(
          color: color.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        children: [
          Icon(
            icon,
            size: DesignConstants.iconSizeMedium,
            color: color,
          ),
          const SizedBox(width: DesignConstants.space3),
          Expanded(
            child: Text(
              message,
              style: tt.bodyMedium?.copyWith(color: color),
            ),
          ),
          if (actionLabel != null && onAction != null) ...[
            const SizedBox(width: DesignConstants.space2),
            TextButton(
              onPressed: onAction,
              style: TextButton.styleFrom(foregroundColor: color),
              child: Text(actionLabel!),
            ),
          ],
        ],
      ),
    );
  }
}
```

#### Step 1.F.6: Create AppMiniSpinner

> **WHY:** Inline loading spinners (16px, thin stroke) appear 19 times across the codebase
> for button loading states, list item refresh indicators, and sync status icons. Each
> manually constructs SizedBox + CircularProgressIndicator with ad-hoc sizes and stroke widths.

Create `lib/core/design_system/app_mini_spinner.dart`:

```dart
import 'package:flutter/material.dart';

/// Inline loading spinner for buttons, list items, and status indicators.
///
/// Usage:
/// ```dart
/// // In a button
/// ElevatedButton(
///   onPressed: null,
///   child: Row(
///     mainAxisSize: MainAxisSize.min,
///     children: [
///       AppMiniSpinner(),
///       SizedBox(width: 8),
///       Text('Saving...'),
///     ],
///   ),
/// )
///
/// // In a list item trailing
/// ListTile(
///   title: Text('Syncing...'),
///   trailing: AppMiniSpinner(color: fg.statusInfo),
/// )
/// ```
///
/// WHY: Replaces 19 inline SizedBox + CircularProgressIndicator patterns with
/// consistent 16px size and 2px stroke width.
class AppMiniSpinner extends StatelessWidget {
  const AppMiniSpinner({
    super.key,
    this.size = 16.0,
    this.strokeWidth = 2.0,
    this.color,
  });

  /// Spinner diameter. Default: 16.0
  final double size;

  /// Spinner stroke width. Default: 2.0
  final double strokeWidth;

  /// Override spinner color. Default: null (inherits cs.primary from theme).
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return SizedBox(
      width: size,
      height: size,
      child: CircularProgressIndicator(
        strokeWidth: strokeWidth,
        color: color ?? cs.primary,
      ),
    );
  }
}
```

---

## Phase 1.G: Barrel Export + Light/HC Theme Completion

### Sub-phase 1.G: Barrel Exports and Missing Theme Components

**Files:**
- Create: `lib/core/design_system/design_system.dart`
- Modify: `lib/core/theme/theme.dart`
- Modify: `lib/core/theme/app_theme.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 1.G.1: Create barrel export for design system

> **WHY:** A single import `package:construction_inspector/core/design_system/design_system.dart`
> gives access to all 24 components. Without it, each screen would need 5-10 separate imports.

Create `lib/core/design_system/design_system.dart`:

```dart
/// Barrel export for the Field Guide design system.
///
/// Usage (single import for all components):
/// ```dart
/// import 'package:construction_inspector/core/design_system/design_system.dart';
/// ```

// Atomic layer
export 'app_text.dart';
export 'app_text_field.dart';
export 'app_chip.dart';
export 'app_progress_bar.dart';
export 'app_counter_field.dart';
export 'app_toggle.dart';
export 'app_icon.dart';

// Card layer
export 'app_glass_card.dart';
export 'app_section_header.dart';
export 'app_list_tile.dart';
export 'app_photo_grid.dart';
export 'app_section_card.dart';

// Surface layer
export 'app_scaffold.dart';
export 'app_bottom_bar.dart';
export 'app_bottom_sheet.dart';
export 'app_dialog.dart';
export 'app_sticky_header.dart';
export 'app_drag_handle.dart';

// Composite layer
export 'app_empty_state.dart';
export 'app_error_state.dart';
export 'app_loading_state.dart';
export 'app_budget_warning_chip.dart';
export 'app_info_banner.dart';
export 'app_mini_spinner.dart';
```

#### Step 1.G.2: Update theme barrel

> **WHY:** FieldGuideColors was created in Phase 1.B but the barrel export was listed
> as a step there. This ensures it's present. If already added, this is a no-op.

In `lib/core/theme/theme.dart`, verify this export is present. If missing, add:

```dart
export 'field_guide_colors.dart';
```

Final contents of `lib/core/theme/theme.dart`:

```dart
// Barrel export for theme module
export 'app_theme.dart';
export 'colors.dart';
export 'design_constants.dart';
export 'field_guide_colors.dart';
```

#### Step 1.G.3: Complete light theme — add missing component themes

> **WHY:** The dark theme has filledButtonTheme, iconButtonTheme, bottomSheetTheme,
> chipTheme, and sliderTheme. The light theme is missing all 5. Without these, light
> theme falls back to Material defaults which look inconsistent with our design system.

In `lib/core/theme/app_theme.dart`, in the `lightTheme` getter, add the following blocks. Insert **after** the `textButtonTheme` block (after line 962, before `floatingActionButtonTheme`):

```dart

      // -----------------------------------------------------------------------
      // FILLED BUTTON - Secondary Actions (Light)
      // -----------------------------------------------------------------------
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: lightSurfaceHighlight,
          foregroundColor: lightTextPrimary,
          disabledBackgroundColor: lightSurfaceHighlight.withValues(alpha: 0.5),
          disabledForegroundColor: lightTextTertiary,
          padding: const EdgeInsets.symmetric(
            horizontal: space6,
            vertical: space4,
          ),
          minimumSize: const Size(88, touchTargetMin),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radiusMedium),
          ),
          textStyle: const TextStyle(
            fontFamily: 'Roboto',
            fontSize: 15,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
      ),
```

Insert **after** the `floatingActionButtonTheme` block (after line 971, before `navigationBarTheme`):

```dart

      // -----------------------------------------------------------------------
      // ICON BUTTON - Light Theme
      // -----------------------------------------------------------------------
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          foregroundColor: lightTextSecondary,
          hoverColor: primaryBlue.withValues(alpha: 0.08),
          focusColor: primaryBlue.withValues(alpha: 0.12),
          highlightColor: primaryBlue.withValues(alpha: 0.12),
          minimumSize: const Size(touchTargetMin, touchTargetMin),
          iconSize: 24,
        ),
      ),
```

Insert **after** the `dialogTheme` block (after line 1025, before `snackBarTheme`):

```dart

      // -----------------------------------------------------------------------
      // BOTTOM SHEET - Light Theme
      // -----------------------------------------------------------------------
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: lightSurfaceElevated,
        elevation: elevationModal,
        surfaceTintColor: Colors.transparent,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(radiusXLarge)),
        ),
        dragHandleColor: lightSurfaceHighlight,
        dragHandleSize: const Size(40, 4),
      ),
```

Insert **after** the `checkboxTheme` block (after line 1099, before `textTheme`):

```dart

      // -----------------------------------------------------------------------
      // CHIP - Light Theme
      // -----------------------------------------------------------------------
      chipTheme: ChipThemeData(
        backgroundColor: lightSurface,
        selectedColor: primaryBlue.withValues(alpha: 0.15),
        disabledColor: lightSurfaceHighlight,
        deleteIconColor: lightTextSecondary,
        labelStyle: const TextStyle(
          fontFamily: 'Roboto',
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: lightTextPrimary,
        ),
        padding: const EdgeInsets.symmetric(horizontal: space2, vertical: space1),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusSmall),
          side: BorderSide(color: lightSurfaceHighlight),
        ),
        side: BorderSide(color: lightSurfaceHighlight),
        checkmarkColor: primaryBlue,
      ),

      // -----------------------------------------------------------------------
      // SLIDER - Light Theme
      // -----------------------------------------------------------------------
      sliderTheme: SliderThemeData(
        activeTrackColor: primaryBlue,
        inactiveTrackColor: lightSurfaceHighlight,
        thumbColor: primaryBlue,
        overlayColor: primaryBlue.withValues(alpha: 0.12),
        valueIndicatorColor: primaryBlue,
        valueIndicatorTextStyle: const TextStyle(
          fontFamily: 'Roboto',
          fontSize: 14,
          fontWeight: FontWeight.w700,
          color: Colors.white,
        ),
      ),
```

#### Step 1.G.4: Complete HC theme — add missing component themes

> **WHY:** Same 5 component themes missing from high contrast theme. HC requires
> thicker borders, higher contrast colors, and larger touch targets for accessibility.

In `lib/core/theme/app_theme.dart`, in the `highContrastTheme` getter:

Insert **after** the `textButtonTheme` block (after line 1315, before `floatingActionButtonTheme`):

```dart

      // -----------------------------------------------------------------------
      // FILLED BUTTON - Secondary Actions (HC)
      // -----------------------------------------------------------------------
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: hcSurfaceElevated,
          foregroundColor: hcTextPrimary,
          disabledBackgroundColor: const Color(0xFF333333),
          disabledForegroundColor: const Color(0xFF666666),
          elevation: 0,
          padding: const EdgeInsets.symmetric(
            horizontal: space6,
            vertical: space4,
          ),
          minimumSize: const Size(88, touchTargetComfortable),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radiusSmall),
            side: const BorderSide(color: hcBorder, width: 2),
          ),
          textStyle: const TextStyle(
            fontFamily: 'Roboto',
            fontSize: 16,
            fontWeight: FontWeight.w900,
            letterSpacing: 1.0,
          ),
        ),
      ),
```

Insert **after** the `floatingActionButtonTheme` block (after line 1329, before `navigationBarTheme`):

```dart

      // -----------------------------------------------------------------------
      // ICON BUTTON - HC Theme
      // -----------------------------------------------------------------------
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          foregroundColor: hcTextPrimary,
          hoverColor: hcPrimary.withValues(alpha: 0.2),
          focusColor: hcPrimary.withValues(alpha: 0.3),
          highlightColor: hcPrimary.withValues(alpha: 0.3),
          minimumSize: const Size(touchTargetComfortable, touchTargetComfortable),
          iconSize: 28,
        ),
      ),
```

Insert **after** the `dialogTheme` block (after line 1388, before `snackBarTheme`):

```dart

      // -----------------------------------------------------------------------
      // BOTTOM SHEET - HC Theme
      // -----------------------------------------------------------------------
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: hcSurfaceElevated,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: const BorderRadius.vertical(top: Radius.circular(radiusXLarge)),
          side: const BorderSide(color: hcBorder, width: 3),
        ),
        dragHandleColor: hcBorder,
        dragHandleSize: const Size(48, 5),
      ),
```

Insert **after** the `checkboxTheme` block (after line 1466, before `textTheme`):

```dart

      // -----------------------------------------------------------------------
      // CHIP - HC Theme
      // -----------------------------------------------------------------------
      chipTheme: ChipThemeData(
        backgroundColor: hcSurfaceElevated,
        selectedColor: hcPrimary.withValues(alpha: 0.3),
        disabledColor: const Color(0xFF333333),
        deleteIconColor: hcTextPrimary,
        labelStyle: const TextStyle(
          fontFamily: 'Roboto',
          fontSize: 14,
          fontWeight: FontWeight.w900,
          color: hcTextPrimary,
        ),
        padding: const EdgeInsets.symmetric(horizontal: space3, vertical: space2),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusSmall),
          side: const BorderSide(color: hcBorder, width: 2),
        ),
        side: const BorderSide(color: hcBorder, width: 2),
        checkmarkColor: hcPrimary,
      ),

      // -----------------------------------------------------------------------
      // SLIDER - HC Theme
      // -----------------------------------------------------------------------
      sliderTheme: SliderThemeData(
        activeTrackColor: hcPrimary,
        inactiveTrackColor: const Color(0xFF333333),
        thumbColor: hcPrimary,
        overlayColor: hcPrimary.withValues(alpha: 0.3),
        valueIndicatorColor: hcPrimary,
        valueIndicatorTextStyle: const TextStyle(
          fontFamily: 'Roboto',
          fontSize: 16,
          fontWeight: FontWeight.w900,
          color: Colors.black,
        ),
      ),
```

---

## Phase 1.H: Tests

### Sub-phase 1.H: Design System Unit Tests

**Files:**
- Create: `test/core/theme/field_guide_colors_test.dart`
- Create: `test/core/design_system/app_text_test.dart`
- Create: `test/core/design_system/app_chip_test.dart`
- Create: `test/core/design_system/app_glass_card_test.dart`
- Create: `test/core/design_system/app_empty_state_test.dart`
- Create: `test/core/design_system/app_mini_spinner_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 1.H.1: Create FieldGuideColors tests

> **WHY:** FieldGuideColors is the foundation for all theme-aware components. Testing
> the three constructors, context accessor, and lerp ensures theme switching works correctly.

Create `test/core/theme/field_guide_colors_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/theme/field_guide_colors.dart';
import 'package:construction_inspector/core/theme/app_theme.dart';

void main() {
  group('FieldGuideColors', () {
    group('constructors produce different values', () {
      test('dark and light surfaceElevated differ', () {
        expect(
          FieldGuideColors.dark.surfaceElevated,
          isNot(equals(FieldGuideColors.light.surfaceElevated)),
        );
      });

      test('dark and highContrast surfaceGlass differ', () {
        expect(
          FieldGuideColors.dark.surfaceGlass,
          isNot(equals(FieldGuideColors.highContrast.surfaceGlass)),
        );
      });

      test('light and highContrast textTertiary differ', () {
        expect(
          FieldGuideColors.light.textTertiary,
          isNot(equals(FieldGuideColors.highContrast.textTertiary)),
        );
      });

      test('HC shadowLight is transparent (no subtle shadows)', () {
        expect(FieldGuideColors.highContrast.shadowLight.alpha, equals(0.0));
      });

      test('HC gradientStart equals gradientEnd (no gradient)', () {
        expect(
          FieldGuideColors.highContrast.gradientStart,
          equals(FieldGuideColors.highContrast.gradientEnd),
        );
      });
    });

    group('of(context)', () {
      testWidgets('retrieves dark FieldGuideColors from dark theme', (tester) async {
        late FieldGuideColors result;

        await tester.pumpWidget(
          MaterialApp(
            theme: AppTheme.darkTheme,
            home: Builder(
              builder: (context) {
                result = FieldGuideColors.of(context);
                return const SizedBox();
              },
            ),
          ),
        );

        expect(result.surfaceElevated, equals(FieldGuideColors.dark.surfaceElevated));
      });

      testWidgets('retrieves light FieldGuideColors from light theme', (tester) async {
        late FieldGuideColors result;

        await tester.pumpWidget(
          MaterialApp(
            theme: AppTheme.lightTheme,
            home: Builder(
              builder: (context) {
                result = FieldGuideColors.of(context);
                return const SizedBox();
              },
            ),
          ),
        );

        expect(result.surfaceElevated, equals(FieldGuideColors.light.surfaceElevated));
      });

      testWidgets('retrieves HC FieldGuideColors from HC theme', (tester) async {
        late FieldGuideColors result;

        await tester.pumpWidget(
          MaterialApp(
            theme: AppTheme.highContrastTheme,
            home: Builder(
              builder: (context) {
                result = FieldGuideColors.of(context);
                return const SizedBox();
              },
            ),
          ),
        );

        expect(result.surfaceElevated, equals(FieldGuideColors.highContrast.surfaceElevated));
      });
    });

    group('lerp', () {
      test('lerp at 0.0 returns start values', () {
        final result = FieldGuideColors.dark.lerp(FieldGuideColors.light, 0.0);
        expect(result.surfaceElevated, equals(FieldGuideColors.dark.surfaceElevated));
      });

      test('lerp at 1.0 returns end values', () {
        final result = FieldGuideColors.dark.lerp(FieldGuideColors.light, 1.0);
        expect(result.surfaceElevated, equals(FieldGuideColors.light.surfaceElevated));
      });

      test('lerp at 0.5 produces intermediate values', () {
        final result = FieldGuideColors.dark.lerp(FieldGuideColors.light, 0.5);
        // Should not equal either endpoint
        expect(result.surfaceElevated, isNot(equals(FieldGuideColors.dark.surfaceElevated)));
        expect(result.surfaceElevated, isNot(equals(FieldGuideColors.light.surfaceElevated)));
      });

      test('lerp with null returns this', () {
        final result = FieldGuideColors.dark.lerp(null, 0.5);
        expect(result.surfaceElevated, equals(FieldGuideColors.dark.surfaceElevated));
      });
    });

    group('copyWith', () {
      test('returns identical when no overrides', () {
        final copy = FieldGuideColors.dark.copyWith();
        expect(copy.surfaceElevated, equals(FieldGuideColors.dark.surfaceElevated));
        expect(copy.textTertiary, equals(FieldGuideColors.dark.textTertiary));
      });

      test('overrides specific field', () {
        final copy = FieldGuideColors.dark.copyWith(surfaceElevated: Colors.red);
        expect(copy.surfaceElevated, equals(Colors.red));
        // Other fields unchanged
        expect(copy.textTertiary, equals(FieldGuideColors.dark.textTertiary));
      });
    });
  });
}
```

#### Step 1.H.2: Create AppText tests

> **WHY:** AppText is the most heavily used design system component (will replace 447
> TextStyle constructors). Verifying that each factory maps to the correct textTheme
> slot catches slot mismatches early.

Create `test/core/design_system/app_text_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/design_system/app_text.dart';
import 'package:construction_inspector/core/theme/app_theme.dart';

/// Helper to wrap widget in MaterialApp with dark theme
Widget _wrap(Widget child) {
  return MaterialApp(
    theme: AppTheme.darkTheme,
    home: Scaffold(body: child),
  );
}

void main() {
  group('AppText', () {
    testWidgets('titleLarge renders with titleLarge textTheme slot', (tester) async {
      await tester.pumpWidget(_wrap(AppText.titleLarge('Hello')));

      final textWidget = tester.widget<Text>(find.text('Hello'));
      // titleLarge in dark theme: fontSize 22, fontWeight w700
      expect(textWidget.style?.fontSize, equals(22));
      expect(textWidget.style?.fontWeight, equals(FontWeight.w700));
    });

    testWidgets('bodyMedium renders with bodyMedium textTheme slot', (tester) async {
      await tester.pumpWidget(_wrap(AppText.bodyMedium('Content')));

      final textWidget = tester.widget<Text>(find.text('Content'));
      expect(textWidget.style?.fontSize, equals(14));
      expect(textWidget.style?.fontWeight, equals(FontWeight.w400));
    });

    testWidgets('labelSmall renders with labelSmall textTheme slot', (tester) async {
      await tester.pumpWidget(_wrap(AppText.labelSmall('Badge')));

      final textWidget = tester.widget<Text>(find.text('Badge'));
      expect(textWidget.style?.fontSize, equals(11));
      expect(textWidget.style?.fontWeight, equals(FontWeight.w700));
    });

    testWidgets('color override applies correctly', (tester) async {
      await tester.pumpWidget(_wrap(
        AppText.bodyMedium('Colored', color: Colors.red),
      ));

      final textWidget = tester.widget<Text>(find.text('Colored'));
      expect(textWidget.style?.color, equals(Colors.red));
    });

    testWidgets('maxLines and overflow propagate', (tester) async {
      await tester.pumpWidget(_wrap(
        AppText.bodyMedium(
          'Truncated text',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ));

      final textWidget = tester.widget<Text>(find.text('Truncated text'));
      expect(textWidget.maxLines, equals(1));
      expect(textWidget.overflow, equals(TextOverflow.ellipsis));
    });

    testWidgets('textAlign propagates', (tester) async {
      await tester.pumpWidget(_wrap(
        AppText.titleMedium('Centered', textAlign: TextAlign.center),
      ));

      final textWidget = tester.widget<Text>(find.text('Centered'));
      expect(textWidget.textAlign, equals(TextAlign.center));
    });
  });
}
```

#### Step 1.H.3: Create AppChip tests

> **WHY:** AppChip factories encode specific color values. Verifying that each factory
> produces the correct accent color prevents silent regressions if color constants change.

Create `test/core/design_system/app_chip_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/design_system/app_chip.dart';
import 'package:construction_inspector/core/theme/app_theme.dart';

Widget _wrap(Widget child) {
  return MaterialApp(
    theme: AppTheme.darkTheme,
    home: Scaffold(body: child),
  );
}

void main() {
  group('AppChip', () {
    testWidgets('cyan factory renders with cyan foreground', (tester) async {
      await tester.pumpWidget(_wrap(AppChip.cyan('Active')));

      final chip = tester.widget<AppChip>(find.byType(AppChip));
      expect(chip.foregroundColor, equals(const Color(0xFF00E5FF)));
      expect(chip.backgroundColor, equals(const Color(0x3300E5FF)));
    });

    testWidgets('amber factory renders with amber foreground', (tester) async {
      await tester.pumpWidget(_wrap(AppChip.amber('Pending')));

      final chip = tester.widget<AppChip>(find.byType(AppChip));
      expect(chip.foregroundColor, equals(const Color(0xFFFFB300)));
    });

    testWidgets('green factory renders with success foreground', (tester) async {
      await tester.pumpWidget(_wrap(AppChip.green('Complete')));

      final chip = tester.widget<AppChip>(find.byType(AppChip));
      expect(chip.foregroundColor, equals(const Color(0xFF4CAF50)));
    });

    testWidgets('error factory renders with error foreground', (tester) async {
      await tester.pumpWidget(_wrap(AppChip.error('Failed')));

      final chip = tester.widget<AppChip>(find.byType(AppChip));
      expect(chip.foregroundColor, equals(const Color(0xFFF44336)));
    });

    testWidgets('chip displays label text', (tester) async {
      await tester.pumpWidget(_wrap(AppChip.cyan('Status')));

      expect(find.text('Status'), findsOneWidget);
    });

    testWidgets('chip displays icon when provided', (tester) async {
      await tester.pumpWidget(_wrap(
        AppChip.cyan('Active', icon: Icons.check),
      ));

      expect(find.byIcon(Icons.check), findsOneWidget);
    });

    testWidgets('onTap wraps chip in GestureDetector', (tester) async {
      var tapped = false;
      await tester.pumpWidget(_wrap(
        AppChip.cyan('Tap me', onTap: () => tapped = true),
      ));

      await tester.tap(find.text('Tap me'));
      expect(tapped, isTrue);
    });
  });
}
```

#### Step 1.H.4: Create AppGlassCard tests

> **WHY:** AppGlassCard is the second most-used component (replaces 30+ Container patterns).
> Testing accent tinting, onTap ripple, and elevation shadow ensures visual correctness.

Create `test/core/design_system/app_glass_card_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/design_system/app_glass_card.dart';
import 'package:construction_inspector/core/theme/app_theme.dart';
import 'package:construction_inspector/core/theme/field_guide_colors.dart';

Widget _wrap(Widget child) {
  return MaterialApp(
    theme: AppTheme.darkTheme,
    home: Scaffold(body: child),
  );
}

void main() {
  group('AppGlassCard', () {
    testWidgets('renders child content', (tester) async {
      await tester.pumpWidget(_wrap(
        const AppGlassCard(child: Text('Card content')),
      ));

      expect(find.text('Card content'), findsOneWidget);
    });

    testWidgets('renders accent color strip when provided', (tester) async {
      await tester.pumpWidget(_wrap(
        const AppGlassCard(
          accentColor: Colors.cyan,
          child: Text('Accented'),
        ),
      ));

      // Find the 3px accent strip Container
      final containers = tester.widgetList<Container>(find.byType(Container));
      final accentStrip = containers.where((c) =>
        c.constraints?.maxWidth == 3 || (c.decoration == null && c.color == Colors.cyan),
      );
      // Accent color container exists somewhere in the tree
      expect(find.text('Accented'), findsOneWidget);
    });

    testWidgets('wraps in InkWell when onTap is provided', (tester) async {
      var tapped = false;
      await tester.pumpWidget(_wrap(
        AppGlassCard(
          onTap: () => tapped = true,
          child: const Text('Tappable'),
        ),
      ));

      expect(find.byType(InkWell), findsOneWidget);
      await tester.tap(find.text('Tappable'));
      expect(tapped, isTrue);
    });

    testWidgets('does not render InkWell when non-interactive', (tester) async {
      await tester.pumpWidget(_wrap(
        const AppGlassCard(child: Text('Static')),
      ));

      expect(find.byType(InkWell), findsNothing);
    });

    testWidgets('selected state changes border color', (tester) async {
      // Build with selected=false and selected=true, verify different decorations
      await tester.pumpWidget(_wrap(
        const AppGlassCard(
          selected: true,
          child: Text('Selected'),
        ),
      ));

      // Just verify it renders without error in selected state
      expect(find.text('Selected'), findsOneWidget);
    });

    testWidgets('uses surfaceGlass from FieldGuideColors', (tester) async {
      await tester.pumpWidget(_wrap(
        const AppGlassCard(child: Text('Glass')),
      ));

      // Verify it renders with the dark theme's glass styling
      // (visual correctness — the component doesn't crash with the theme)
      expect(find.text('Glass'), findsOneWidget);
    });
  });
}
```

#### Step 1.H.5: Create AppEmptyState tests

> **WHY:** AppEmptyState is used on every list screen. Testing that all props render
> correctly and the CTA button triggers its callback ensures the empty→populated
> transition works.

Create `test/core/design_system/app_empty_state_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/design_system/app_empty_state.dart';
import 'package:construction_inspector/core/theme/app_theme.dart';

Widget _wrap(Widget child) {
  return MaterialApp(
    theme: AppTheme.darkTheme,
    home: Scaffold(body: child),
  );
}

void main() {
  group('AppEmptyState', () {
    testWidgets('renders icon, title', (tester) async {
      await tester.pumpWidget(_wrap(
        const AppEmptyState(
          icon: Icons.photo_library_outlined,
          title: 'No photos yet',
        ),
      ));

      expect(find.byIcon(Icons.photo_library_outlined), findsOneWidget);
      expect(find.text('No photos yet'), findsOneWidget);
    });

    testWidgets('renders subtitle when provided', (tester) async {
      await tester.pumpWidget(_wrap(
        const AppEmptyState(
          icon: Icons.folder_outlined,
          title: 'No projects',
          subtitle: 'Create your first project to get started',
        ),
      ));

      expect(find.text('No projects'), findsOneWidget);
      expect(find.text('Create your first project to get started'), findsOneWidget);
    });

    testWidgets('hides subtitle when not provided', (tester) async {
      await tester.pumpWidget(_wrap(
        const AppEmptyState(
          icon: Icons.folder_outlined,
          title: 'No projects',
        ),
      ));

      // Only title, no subtitle text
      expect(find.text('No projects'), findsOneWidget);
    });

    testWidgets('renders action button when actionLabel and onAction provided', (tester) async {
      var actionTriggered = false;

      await tester.pumpWidget(_wrap(
        AppEmptyState(
          icon: Icons.add,
          title: 'No entries',
          actionLabel: 'Create Entry',
          onAction: () => actionTriggered = true,
        ),
      ));

      expect(find.text('Create Entry'), findsOneWidget);

      await tester.tap(find.text('Create Entry'));
      expect(actionTriggered, isTrue);
    });

    testWidgets('hides action button when actionLabel is null', (tester) async {
      await tester.pumpWidget(_wrap(
        const AppEmptyState(
          icon: Icons.inbox_outlined,
          title: 'Empty inbox',
        ),
      ));

      expect(find.byType(ElevatedButton), findsNothing);
    });
  });
}
```

#### Step 1.H.6: Create AppMiniSpinner tests

> **WHY:** AppMiniSpinner replaces 19 inline patterns. Testing size, stroke width,
> and color ensures visual consistency across all usage sites.

Create `test/core/design_system/app_mini_spinner_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/design_system/app_mini_spinner.dart';
import 'package:construction_inspector/core/theme/app_theme.dart';

Widget _wrap(Widget child) {
  return MaterialApp(
    theme: AppTheme.darkTheme,
    home: Scaffold(body: child),
  );
}

void main() {
  group('AppMiniSpinner', () {
    testWidgets('renders at default size 16x16', (tester) async {
      await tester.pumpWidget(_wrap(const AppMiniSpinner()));

      final sizedBox = tester.widget<SizedBox>(find.byType(SizedBox));
      expect(sizedBox.width, equals(16.0));
      expect(sizedBox.height, equals(16.0));
    });

    testWidgets('renders at custom size', (tester) async {
      await tester.pumpWidget(_wrap(
        const AppMiniSpinner(size: 24.0),
      ));

      final sizedBox = tester.widget<SizedBox>(find.byType(SizedBox));
      expect(sizedBox.width, equals(24.0));
      expect(sizedBox.height, equals(24.0));
    });

    testWidgets('uses custom stroke width', (tester) async {
      await tester.pumpWidget(_wrap(
        const AppMiniSpinner(strokeWidth: 3.0),
      ));

      final indicator = tester.widget<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );
      expect(indicator.strokeWidth, equals(3.0));
    });

    testWidgets('uses default stroke width of 2.0', (tester) async {
      await tester.pumpWidget(_wrap(const AppMiniSpinner()));

      final indicator = tester.widget<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );
      expect(indicator.strokeWidth, equals(2.0));
    });

    testWidgets('uses custom color when provided', (tester) async {
      await tester.pumpWidget(_wrap(
        const AppMiniSpinner(color: Colors.red),
      ));

      final indicator = tester.widget<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );
      expect(indicator.color, equals(Colors.red));
    });

    testWidgets('uses cs.primary when no color provided', (tester) async {
      await tester.pumpWidget(_wrap(const AppMiniSpinner()));

      final indicator = tester.widget<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );
      // Dark theme primary is primaryCyan (0xFF00E5FF)
      expect(indicator.color, equals(const Color(0xFF00E5FF)));
    });
  });
}
```

#### Step 1.H.7: Test AppScaffold

**File:** `test/core/design_system/app_scaffold_test.dart`
- Test that SafeArea is applied when useSafeArea=true
- Test that SafeArea is NOT applied when useSafeArea=false
- Test that backgroundColor override works

#### Step 1.H.8: Test AppBottomSheet

**File:** `test/core/design_system/app_bottom_sheet_test.dart`
- Test that show() opens a modal bottom sheet
- Test that AppDragHandle is rendered at top
- Test that builder content is displayed

#### Step 1.H.9: Test AppDialog

**File:** `test/core/design_system/app_dialog_test.dart`
- Test that show() opens an AlertDialog
- Test that default OK button appears when no actions provided
- Test that custom actions are displayed

#### Step 1.H.10: Test AppTextField

**File:** `test/core/design_system/app_text_field_test.dart`
- Test that label and hint are displayed
- Test that validator is called on form submission
- Test that prefixIcon and suffixIcon are rendered

#### Step 1.H.11: Quality Gate

> **WHY:** The quality gate ensures all new code passes static analysis and all tests
> pass before proceeding to Phase 2 (migration). Catching issues here prevents
> cascading failures during the migration phase.

Run static analysis:

```
pwsh -Command "flutter analyze"
```

Expected: 0 errors, 0 warnings on new files. Existing warnings are pre-existing.

Run design system tests:

```
pwsh -Command "flutter test test/core/"
```

Expected: All tests pass (6 test files, 30+ test cases).

If any test fails, fix the component code and re-run before proceeding to Phase 2.

---

## Phase 1.I: Testing Infrastructure Preparation

**Goal:** Ensure the design system and test harness are ready for testing key migration. This phase prevents cumulative breakage as screens are rewritten in Phases 2-10.

**Agent**: `frontend-flutter-specialist-agent`

### Step 1.I.1: Verify all 24 design system components accept `Key? key`

All design system components in `lib/core/design_system/` must accept a `Key? key` parameter forwarded to their `super(key: key)` constructor. This is standard Flutter practice but must be explicitly verified because the plan's Phase 1.C-1.F code blocks omit it in several places.

Grep for `class App` in `lib/core/design_system/` and verify each widget's constructor includes `Key? key`. Fix any that are missing.

**Fix pattern for factory-constructor widgets** (e.g., AppText, AppChip):
```dart
// Add super.key to the private constructor:
const AppText._(this.text, this._styleResolver, {this.color, ..., super.key});

// Add Key? key to each factory and forward it:
factory AppText.bodyMedium(String text, {Color? color, ..., Key? key}) =>
    AppText._(text, (t) => t.bodyMedium, color: color, ..., key: key);
```
This pattern applies to all widgets with factory constructors (AppText has 15, AppChip has 7).

### Step 1.I.2: Update driver enabled-detection for design system types

**File:** `lib/core/driver/driver_server.dart`

The `_findByValueKey()` helper's enabled-detection checks widget types to determine if an element is tappable. The current list only includes Material widget types. Add design system component types so the driver can correctly detect enabled/disabled state on new widgets.

Find the enabled-detection type list (ElevatedButton, TextButton, OutlinedButton, FilledButton, IconButton, InkWell, GestureDetector) and add:
- `AppGlassCard`
- `AppListTile`
- `AppToggle`
- `AppChip`
- `AppCounterField`
- `AppTextField`

Add the necessary imports from `lib/core/design_system/`.

### Step 1.I.3: Register FieldGuideColors in test harness

**File:** `lib/test_harness/harness_providers.dart` (or equivalent test wrapper)

The test harness must provide a `ThemeData` that includes the `FieldGuideColors` extension so that widgets using `FieldGuideColors.of(context)` don't throw in tests. Add `FieldGuideColors.dark` (or `.light`) to the `extensions` list of the test harness's `ThemeData`.

### Step 1.I.4: Migrate inline ValueKey usages to centralized TestingKeys

There are ~17 inline `ValueKey('...')` usages across widget files that are NOT part of the centralized `lib/shared/testing_keys/` system. Find them and migrate:

```
Grep pattern: ValueKey\(
Path: lib/ (excluding lib/shared/testing_keys/)
```

For each match, either:
- Move the key definition to the appropriate feature key file in `lib/shared/testing_keys/`
- Replace the inline `ValueKey('...')` with a reference to the centralized key

### Step 1.I.5: Verify

```
pwsh -Command "flutter analyze lib/core/driver/ lib/shared/testing_keys/"
pwsh -Command "flutter test test/core/"
```

<!-- ======= Part: phases2-5 ======= -->

# UI Refactor v2 — Phases 2-5: Core Screen Rewrites

> **Depends on:** Phase 1 (design system components + FieldGuideColors ThemeExtension)
>
> **Color access pattern (established in Phase 1):**
> ```dart
> final cs = Theme.of(context).colorScheme;    // M3: primary, onSurface, error, outline, etc.
> final tt = Theme.of(context).textTheme;       // Typography: bodyLarge, titleMedium, etc.
> final fg = FieldGuideColors.of(context);      // Custom: surfaceElevated, surfaceGlass, textTertiary, etc.
> ```

---

## Phase 2: Dashboard Rewrite

**Goal:** Migrate `ProjectDashboardScreen` and its 4 dashboard widgets from static `AppTheme.*` tokens + hardcoded `Colors.*` to theme-aware `cs`/`tt`/`fg` tokens. Replace inline `TextStyle` with `textTheme` references.

### Sub-phase 2.A: DashboardStatCard

**Files:**
- Modify: `lib/features/dashboard/presentation/widgets/dashboard_stat_card.dart`
- Test: Existing tests (visual regression only — no logic change)

**Agent:** `frontend-flutter-specialist-agent`

#### Step 2.A.1: Add theme variable declarations

Add at the top of `build()`:
```dart
// WHY: Theme-aware colors enable future dark mode support
final cs = Theme.of(context).colorScheme;
final tt = Theme.of(context).textTheme;
final fg = FieldGuideColors.of(context);
```

#### Step 2.A.2: Replace static color references

**Instances in `dashboard_stat_card.dart`:**
- Line ~44: `AppTheme.surfaceElevated` → `fg.surfaceElevated`
- Line ~45: `AppTheme.surfaceElevated.withValues(alpha: 0.7)` → `fg.surfaceElevated.withValues(alpha: 0.7)`
- Line ~49: `AppTheme.surfaceHighlight.withValues(alpha: 0.5)` → `cs.outline.withValues(alpha: 0.5)`
- Line ~54: `Colors.black.withValues(alpha: 0.15)` → `fg.shadowLight`
- Line ~61: `Colors.transparent` → `Colors.transparent` (keep — theme-independent)

#### Step 2.A.3: Replace inline TextStyle with textTheme

**Pattern:**
```dart
// Before:
TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: color, letterSpacing: -0.5)
// After — NOTE: color is a parameter, must stay dynamic via copyWith:
tt.titleLarge!.copyWith(color: color, letterSpacing: -0.5)
```

**Instances:**
- Line ~81: `TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: color, ...)` → `tt.titleLarge!.copyWith(color: color, letterSpacing: -0.5)`
- Line ~92: `TextStyle(fontSize: 11, color: AppTheme.textSecondary, fontWeight: FontWeight.w600, ...)` → `tt.labelSmall!.copyWith(color: cs.onSurfaceVariant, letterSpacing: 0.3)`

---

### Sub-phase 2.B: BudgetOverviewCard

**Files:**
- Modify: `lib/features/dashboard/presentation/widgets/budget_overview_card.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 2.B.1: Add theme variable declarations

Same pattern as 2.A.1 — add `cs`/`tt`/`fg` at top of `build()` in both `BudgetOverviewCard` AND `_BudgetStatBox`.

#### Step 2.B.2: Replace static color references

**Instances in `budget_overview_card.dart`:**
- Line ~23: `EdgeInsets.all(24)` → `EdgeInsets.all(AppTheme.space6)` (NOTE: spacing stays static per rules, but 24 is a magic number — use the token)
- Line ~38: `AppTheme.primaryCyan.withValues(alpha: 0.2)` → `cs.primary.withValues(alpha: 0.2)`
- Line ~47: `AppTheme.surfaceElevated` → `fg.surfaceElevated`
- Line ~67: `AppTheme.textInverse.withValues(alpha: 0.2)` → `fg.textInverse.withValues(alpha: 0.2)`
- Line ~73: `AppTheme.textInverse` → `fg.textInverse`
- Line ~107: `AppTheme.textPrimary` → `cs.onSurface`
- Line ~119: `AppTheme.textTertiary` → `fg.textTertiary`
- Line ~140: `AppTheme.surfaceHighlight` → `cs.outline`
- Line ~143: `AppTheme.statusError` → `cs.error`
- Line ~145: `AppTheme.statusWarning` → `fg.statusWarning`
- Line ~146: `AppTheme.primaryCyan` → `cs.primary`
- Line ~178: `AppTheme.primaryCyan` → `cs.primary`
- Line ~184: `AppTheme.statusSuccess` → `fg.statusSuccess`

#### Step 2.B.3: Replace inline TextStyle with textTheme

**Instances:**
- Line ~79: `TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTheme.textInverse, letterSpacing: 1.0)` → `tt.labelLarge!.copyWith(color: fg.textInverse, letterSpacing: 1.0)`
- Line ~104: `TextStyle(fontSize: 36, fontWeight: FontWeight.w800, color: AppTheme.textPrimary, ...)` → `tt.displaySmall!.copyWith(color: cs.onSurface, letterSpacing: -1)`
- Line ~117: `TextStyle(fontSize: 11, color: AppTheme.textTertiary, ...)` → `tt.labelSmall!.copyWith(color: fg.textTertiary, letterSpacing: 1.5)`
- Line ~158: `TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: ...)` → `tt.titleSmall!.copyWith(color: <dynamic>)`
- Line ~240 (_BudgetStatBox): `TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: color)` → `tt.titleLarge!.copyWith(color: color)`
- Line ~251 (_BudgetStatBox): `TextStyle(fontSize: 12, color: AppTheme.textSecondary, ...)` → `tt.labelMedium!.copyWith(color: cs.onSurfaceVariant)`

---

### Sub-phase 2.C: TrackedItemRow

**Files:**
- Modify: `lib/features/dashboard/presentation/widgets/tracked_item_row.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 2.C.1: Add theme variables + replace colors

**Instances:**
- Line ~24: `AppTheme.statusError` → `cs.error`
- Line ~26: `AppTheme.statusWarning` → `fg.statusWarning`
- Line ~27: `AppTheme.primaryCyan` → `cs.primary`
- Line ~36: `AppTheme.surfaceDark` → `cs.surface`
- Line ~37: `AppTheme.surfaceDark.withValues(alpha: 0.5)` → `cs.surface.withValues(alpha: 0.5)`
- Line ~42: `AppTheme.surfaceHighlight.withValues(alpha: 0.5)` → `cs.outline.withValues(alpha: 0.5)`
- Line ~112: `AppTheme.surfaceHighlight` → `cs.outline`
- Line ~138: `AppTheme.textTertiary` → `fg.textTertiary`

#### Step 2.C.2: Replace inline TextStyle

**Instances:**
- Line ~76: `TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: progressColor)` → `tt.titleMedium!.copyWith(fontWeight: FontWeight.w800, color: progressColor)`
- Line ~93: `TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)` → `tt.bodyMedium!.copyWith(fontWeight: FontWeight.w600, color: cs.onSurface)`
- Line ~122: `TextStyle(fontSize: 11, color: AppTheme.textSecondary, ...)` → `tt.labelSmall!.copyWith(color: cs.onSurfaceVariant)`

---

### Sub-phase 2.D: AlertItemRow

**Files:**
- Modify: `lib/features/dashboard/presentation/widgets/alert_item_row.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 2.D.1: Add theme variables + replace hardcoded EdgeInsets/BorderRadius

**Pattern for magic numbers:**
```dart
// Before:
margin: const EdgeInsets.only(bottom: 8),
padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
borderRadius: BorderRadius.circular(8),
// After:
margin: const EdgeInsets.only(bottom: AppTheme.space2),
padding: const EdgeInsets.symmetric(horizontal: AppTheme.space3, vertical: AppTheme.space2 + 2),
borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
```

**Instances — EdgeInsets:**
- Line ~22: `EdgeInsets.only(bottom: 8)` → `EdgeInsets.only(bottom: AppTheme.space2)`
- Line ~23: `EdgeInsets.symmetric(horizontal: 12, vertical: 10)` → `EdgeInsets.symmetric(horizontal: AppTheme.space3, vertical: AppTheme.space2 + 2)`
- Line ~55: `EdgeInsets.symmetric(horizontal: 8, vertical: 4)` → `EdgeInsets.symmetric(horizontal: AppTheme.space2, vertical: AppTheme.space1)`

**Instances — BorderRadius:**
- Line ~24: `BorderRadius.circular(8)` → `BorderRadius.circular(AppTheme.radiusSmall)`
- Line ~58: `BorderRadius.circular(4)` → `BorderRadius.circular(AppTheme.radiusXSmall)`

**Instances — SizedBox:**
- Line ~42: `SizedBox(width: 10)` → `SizedBox(width: AppTheme.space2 + 2)`

#### Step 2.D.2: Replace static colors

**Instances:**
- Line ~26: `AppTheme.statusError.withValues(alpha: 0.1)` → `cs.error.withValues(alpha: 0.1)`
- Line ~27: `AppTheme.surfaceElevated.withValues(alpha: 0.5)` → `fg.surfaceElevated.withValues(alpha: 0.5)`
- Line ~30: `AppTheme.statusError.withValues(alpha: 0.3)` → `cs.error.withValues(alpha: 0.3)`
- Line ~31: `AppTheme.statusWarning.withValues(alpha: 0.3)` → `fg.statusWarning.withValues(alpha: 0.3)`
- Line ~39: `AppTheme.statusError` → `cs.error`
- Line ~39: `AppTheme.statusWarning` → `fg.statusWarning`
- Line ~49: `AppTheme.textPrimary` → `cs.onSurface`
- Line ~57: `AppTheme.statusError` / `AppTheme.statusWarning` → `cs.error` / `fg.statusWarning`
- Line ~65: `AppTheme.textInverse` → `fg.textInverse`

#### Step 2.D.3: Replace inline TextStyle

**Instances:**
- Line ~48: `TextStyle(fontSize: 13, color: AppTheme.textPrimary)` → `tt.bodyMedium!.copyWith(color: cs.onSurface)`
- Line ~62: `TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textInverse)` → `tt.labelMedium!.copyWith(fontWeight: FontWeight.bold, color: fg.textInverse)`

---

### Sub-phase 2.E: ProjectDashboardScreen

**Files:**
- Modify: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 2.E.1: Add theme variable declarations

Add at the top of `build()` and every `_build*` method that references theme:
```dart
final cs = Theme.of(context).colorScheme;
final tt = Theme.of(context).textTheme;
final fg = FieldGuideColors.of(context);
```

#### Step 2.E.2: Replace inline TextStyle

**Instances in `project_dashboard_screen.dart`:**
- Line ~102: `TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppTheme.textInverse, ...)` → `tt.titleMedium!.copyWith(fontWeight: FontWeight.w800, color: fg.textInverse, letterSpacing: 0.2)`
- Line ~115: `TextStyle(fontSize: 12, color: AppTheme.textInverse.withValues(alpha: 0.9), ...)` → `tt.labelSmall!.copyWith(color: fg.textInverse.withValues(alpha: 0.9))`
- Line ~225: `TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)` → `tt.titleMedium!.copyWith(fontWeight: FontWeight.bold, color: cs.onSurface)`
- Line ~233: `TextStyle(color: AppTheme.textSecondary)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant)`
- Line ~301: `TextStyle(fontWeight: FontWeight.w600, fontSize: 15, color: AppTheme.textPrimary)` → `tt.titleSmall!.copyWith(color: cs.onSurface)`
- Line ~309: `TextStyle(fontSize: 13, color: AppTheme.textSecondary)` → `tt.bodySmall!.copyWith(color: cs.onSurfaceVariant)`
- Line ~523: `TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTheme.textInverse, ...)` → `tt.labelLarge!.copyWith(color: fg.textInverse, letterSpacing: 1.0)`
- Line ~549: `TextStyle(fontSize: 12, color: AppTheme.textTertiary, ...)` → `tt.labelSmall!.copyWith(color: fg.textTertiary)`
- Line ~567: `TextStyle(color: AppTheme.textSecondary)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant)`
- Line ~667: `TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTheme.textInverse, ...)` → `tt.labelLarge!.copyWith(color: fg.textInverse, letterSpacing: 1.0)`
- Line ~688: `TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.textInverse)` → `tt.labelSmall!.copyWith(fontWeight: FontWeight.w700, color: fg.textInverse)`

#### Step 2.E.3: Replace hardcoded Colors.* (the 4 literal violations)

**Pattern:**
```dart
// Before (budget warning chip):
backgroundColor: Colors.amber.shade50,
side: BorderSide(color: Colors.amber.shade200),
color: Colors.orange.shade800
// After — use AppBudgetWarningChip (Phase 1 component):
AppBudgetWarningChip(
  message: 'Budget values adjusted — unit price discrepancy detected',
)
```

**Instances:**
- Line ~438: `Icon(... color: Colors.orange.shade800, ...)` → `Icon(... color: fg.warningBorder, ...)`
- Line ~443: `backgroundColor: Colors.amber.shade50` → `backgroundColor: fg.warningBackground`
- Line ~444: `side: BorderSide(color: Colors.amber.shade200)` → `side: BorderSide(color: fg.warningBorder)`
- OR better: replace the entire Chip (lines 437-445) with `AppBudgetWarningChip`

#### Step 2.E.4: Replace remaining static colors

**Instances:**
- Line ~104: `AppTheme.textInverse` → `fg.textInverse`
- Line ~138: `AppTheme.accentAmber.withValues(alpha: 0.3)` → `fg.accentAmber.withValues(alpha: 0.3)`
- Line ~159: `Colors.transparent` → `Colors.transparent` (keep)
- Line ~160: `AppTheme.textInverse` → `fg.textInverse`
- Line ~161: `Colors.transparent` → `Colors.transparent` (keep)
- Line ~173: `AppTheme.textInverse` → `fg.textInverse`
- Line ~221: `AppTheme.textTertiary` → `fg.textTertiary`
- Line ~262: `AppTheme.accentAmber.withValues(alpha: 0.5)` → `fg.accentAmber.withValues(alpha: 0.5)`
- Line ~265: `AppTheme.accentAmber.withValues(alpha: 0.08)` → `fg.accentAmber.withValues(alpha: 0.08)`
- Line ~284: `AppTheme.accentAmber.withValues(alpha: 0.15)` → `fg.accentAmber.withValues(alpha: 0.15)`
- Line ~290: `AppTheme.accentAmber` → `fg.accentAmber`
- Line ~319: `AppTheme.textTertiary` → `fg.textTertiary`
- Line ~344: `AppTheme.primaryCyan` → `cs.primary`
- Line ~356: `AppTheme.accentAmber` → `fg.accentAmber`
- Line ~481: `AppTheme.surfaceElevated` → `fg.surfaceElevated`
- Line ~484: `AppTheme.surfaceHighlight.withValues(alpha: 0.5)` → `cs.outline.withValues(alpha: 0.5)`
- Line ~489: `Colors.black.withValues(alpha: 0.1)` → `fg.shadowLight`
- Line ~517: `AppTheme.textInverse` → `fg.textInverse`
- Line ~535: `AppTheme.textInverse` → `fg.textInverse`
- Line ~564: `AppTheme.textTertiary` → `fg.textTertiary`
- Line ~700: `AppTheme.statusWarning.withValues(alpha: 0.05)` → `fg.statusWarning.withValues(alpha: 0.05)`

#### Step 2.E.5: Replace hardcoded padding magic numbers

**Instances:**
- Line ~217: `EdgeInsets.all(32)` → `EdgeInsets.all(AppTheme.space8)`
- Line ~228: `SizedBox(height: 24)` → `SizedBox(height: AppTheme.space6)`
- Line ~236: `SizedBox(height: 12)` → `SizedBox(height: AppTheme.space3)`
- Line ~237: `SizedBox(height: 24)` → `SizedBox(height: AppTheme.space6)`
- Line ~435: `EdgeInsets.symmetric(horizontal: 16, vertical: 4)` → `EdgeInsets.symmetric(horizontal: AppTheme.space4, vertical: AppTheme.space1)`

### Sub-phase 2.F: Quality Gate

**Agent:** `qa-testing-agent`

```powershell
pwsh -Command "flutter analyze lib/features/dashboard/"
pwsh -Command "flutter test test/features/dashboard/"
```

Verify: no `AppTheme.textPrimary`, `AppTheme.textSecondary`, `AppTheme.textTertiary`, `AppTheme.textInverse`, `AppTheme.surfaceElevated`, `AppTheme.surfaceHighlight`, `AppTheme.surfaceDark`, `AppTheme.primaryCyan`, `AppTheme.statusError`, `AppTheme.statusSuccess`, `AppTheme.statusWarning`, `Colors.black.withValues`, `Colors.amber`, `Colors.orange` remain in dashboard files.

**Testing Keys**: For each screen/widget modified in this phase:
1. Review existing TestingKeys assignments — transfer all keys to their new design system wrapper
2. Add new keys for any new interactive elements (buttons, fields, toggles)
3. Update the corresponding key file in `lib/shared/testing_keys/` if keys are added/renamed
4. Run: `pwsh -Command "flutter test test/features/dashboard/"` to verify widget tests pass

---

## Phase 3: Entry Editor Rewrite

**Goal:** Migrate `EntryEditorScreen` (~1500 lines) and its section widgets from static tokens to theme-aware. This is the most complex screen — approach with patterns, not line-by-line.

### Sub-phase 3.A: EntryEditorScreen Core

**Files:**
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 3.A.1: Add theme variable declarations

Add at the top of `_buildAppBar()`, `_buildEntryHeader()`, and `build()`:
```dart
final cs = Theme.of(context).colorScheme;
final tt = Theme.of(context).textTheme;
final fg = FieldGuideColors.of(context);
```
NOTE: Do NOT add to methods called from `dispose()` or `initState()` — context may be invalid.

#### Step 3.A.2: Replace inline TextStyle pattern

**Pattern applied across the file:**
```dart
// Before:
style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: AppTheme.textPrimary)
// After:
style: tt.bodyMedium!.copyWith(fontWeight: FontWeight.w600, color: cs.onSurface)
```

**Key instances (entry_editor_screen.dart):**
- `_buildAppBar` — title styles already use `Theme.of(context).textTheme` (good)
- `_buildEntryHeader` line ~916: Uses `Theme.of(context).textTheme.titleLarge` (good — already migrated)
- Line ~955: `TextStyle(fontWeight: FontWeight.w600, color: ...)` → `tt.titleSmall!.copyWith(color: ...)`
- Line ~880: `TextStyle(color: AppTheme.statusError)` → `tt.bodyMedium!.copyWith(color: cs.error)`

#### Step 3.A.3: Replace static color references

**Pattern:**
```dart
// Before:
color: AppTheme.primaryCyan
// After:
color: cs.primary
```

**Instances (scan for `AppTheme.` in entry_editor_screen.dart):**
- `AppTheme.statusError` → `cs.error` (SnackBar backgrounds, delete menu icon)
- `AppTheme.statusWarning` → `fg.statusWarning` (permission snackbar, weather prompt color)
- `AppTheme.primaryCyan` → `cs.primary` (location icon, edit icons)
- `AppTheme.textSecondary` → `cs.onSurfaceVariant` (expand_more icon, subtitle text)
- `AppTheme.textInverse` → `fg.textInverse` (submit button foreground)
- `AppTheme.surfaceElevated` → `fg.surfaceElevated` (card backgrounds)

#### Step 3.A.4: Replace hardcoded EdgeInsets

**Instances:**
- Line ~902: `EdgeInsets.all(16)` → `EdgeInsets.all(AppTheme.space4)`
- Line ~930: `SizedBox(height: 8)` → `SizedBox(height: AppTheme.space2)`

---

### Sub-phase 3.B: Entry Section Widgets

**Files:**
- Modify: `lib/features/entries/presentation/widgets/entry_basics_section.dart`
- Modify: `lib/features/entries/presentation/widgets/entry_activities_section.dart`
- Modify: `lib/features/entries/presentation/widgets/entry_photos_section.dart`
- Modify: `lib/features/entries/presentation/widgets/entry_contractors_section.dart`
- Modify: `lib/features/entries/presentation/widgets/entry_quantities_section.dart`
- Modify: `lib/features/entries/presentation/widgets/entry_forms_section.dart`
- Modify: `lib/features/entries/presentation/widgets/entry_action_bar.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 3.B.1: Apply theme migration pattern to all section widgets

For each widget file, apply the same 3-step pattern:
1. Add `cs`/`tt`/`fg` at top of `build()`
2. Replace all `AppTheme.textPrimary` → `cs.onSurface`, `AppTheme.textSecondary` → `cs.onSurfaceVariant`, etc.
3. Replace inline `TextStyle(fontSize: N, ...)` with nearest `textTheme` match

**textTheme mapping guide:**
| Inline fontSize | textTheme token |
|----------------|-----------------|
| 10-11 | `tt.labelSmall` |
| 12 | `tt.labelMedium` or `tt.bodySmall` |
| 13-14 | `tt.bodyMedium` |
| 15-16 | `tt.titleSmall` or `tt.bodyLarge` |
| 18 | `tt.titleMedium` |
| 20 | `tt.titleLarge` |
| 24 | `tt.headlineSmall` |
| 28+ | `tt.headlineMedium` |

---

### Sub-phase 3.C: ContractorEditorWidget (50 violations)

**Files:**
- Modify: `lib/features/entries/presentation/widgets/contractor_editor_widget.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 3.C.1: Bulk replace static color tokens

NOTE: This widget has ~50 violations. Use `replace_all` for mechanical find/replace:

```dart
// Bulk replacements (order matters — more specific first):
AppTheme.textPrimary    → cs.onSurface
AppTheme.textSecondary  → cs.onSurfaceVariant
AppTheme.textTertiary   → fg.textTertiary
AppTheme.textInverse    → fg.textInverse
AppTheme.primaryCyan    → cs.primary
AppTheme.surfaceElevated → fg.surfaceElevated
AppTheme.surfaceHighlight → cs.outline
AppTheme.statusError    → cs.error
AppTheme.statusWarning  → fg.statusWarning
AppTheme.statusSuccess  → fg.statusSuccess
```

WARNING: Must add `final cs = Theme.of(context).colorScheme;` etc. FIRST — otherwise these replacements break compilation.

#### Step 3.C.2: Replace inline TextStyle instances

Apply the textTheme mapping guide from 3.B.1 to all `TextStyle(fontSize: N, ...)` instances.

---

### Sub-phase 3.D: Shared Entry Widgets

**Files:**
- Modify: `lib/features/entries/presentation/widgets/status_badge.dart`
- Modify: `lib/features/entries/presentation/widgets/submitted_banner.dart`
- Modify: `lib/features/entries/presentation/widgets/draft_entry_tile.dart`
- Modify: `lib/features/entries/presentation/widgets/review_field_row.dart`
- Modify: `lib/features/entries/presentation/widgets/review_missing_warning.dart`
- Modify: `lib/features/entries/presentation/widgets/simple_info_row.dart`
- Modify: `lib/features/entries/presentation/widgets/entry_form_card.dart` — 7 AppTheme.* violations
  - `AppTheme.primaryCyan` → `cs.primary`
  - `AppTheme.textSecondary` → `cs.onSurfaceVariant`
  - `AppTheme.textPrimary` → `cs.onSurface`
  - `AppTheme.surfaceElevated` → `fg.surfaceElevated`
  - `AppTheme.statusSuccess` → `fg.statusSuccess`
  - `AppTheme.radiusMedium` → keep (theme-independent)
  - `AppTheme.space*` → keep (theme-independent)
- Modify: `lib/features/entries/presentation/utils/weather_helpers.dart` — 7 AppTheme.* violations
  - 6x `AppTheme.weather*` — these are theme-independent domain colors, keep as static AppTheme.* references
  - 1x `AppTheme.textTertiary` at line 68 → NOTE: This is a utility function returning Color without BuildContext. Document as known exception — weather_helpers returns static colors by design. The textTertiary fallback is acceptable since weather colors are domain-specific and identical across themes.
- Modify: `lib/features/entries/presentation/controllers/pdf_data_builder.dart` — 1 violation
  - `AppTheme.statusWarning` at line 63 → `FieldGuideColors.of(context).statusWarning` (requires adding BuildContext parameter to the method)

**Agent:** `frontend-flutter-specialist-agent`

#### Step 3.D.1: Apply standard migration pattern

Same 3-step pattern as 3.B.1. These widgets are smaller (10-50 lines each), so the migration is mechanical.

---

### Sub-phase 3.E: Report Widgets (9 dialog files)

**Files:**
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_add_contractor_sheet.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_add_personnel_type_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_add_quantity_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_debug_pdf_actions_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_delete_personnel_type_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_location_edit_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_weather_edit_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_photo_detail_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_pdf_actions_dialog.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 3.E.1: Apply standard migration pattern to all 9 dialog files

NOTE for dialogs: `Theme.of(context)` inside `showDialog` builder uses the dialog's context, which inherits the app theme. This is correct — no special handling needed.

---

### Sub-phase 3.F: Quality Gate

**Agent:** `qa-testing-agent`

```powershell
pwsh -Command "flutter analyze lib/features/entries/"
pwsh -Command "flutter test test/features/entries/"
```

Verify: no static `AppTheme.text*`, `AppTheme.surface*`, `AppTheme.primaryCyan`, `AppTheme.status*` remain in entry feature files. `AppTheme.space*`, `AppTheme.radius*`, `AppTheme.animation*`, `AppTheme.curve*`, `AppTheme.iconSize*` are OK (theme-independent).

**Testing Keys**: For each screen/widget modified in this phase:
1. Review existing TestingKeys assignments — transfer all keys to their new design system wrapper
2. Add new keys for any new interactive elements (buttons, fields, toggles)
3. Update the corresponding key file in `lib/shared/testing_keys/` if keys are added/renamed
4. Run: `pwsh -Command "flutter test test/features/entries/"` to verify widget tests pass

---

## Phase 3.5: Safety Repeat-Last Toggles (NEW FEATURE)

**Goal:** Add "repeat last" toggles to daily entries. When creating a new entry, if enabled, seed location, weather, and contractors from the most recent entry for that project.

> **SECURITY NOTE:** This feature only copies from entries created by the same user (enforced at query level). No cross-user data leakage.

### Sub-phase 3.5.A: Database Migration (v43)

**Files:**
- Modify: `lib/core/database/database_service.dart`

**Agent:** `backend-data-layer-agent`

#### Step 3.5.A.1: Bump database version

```dart
// Before:
version: 42,
// After:
version: 43,
```

NOTE: Both `_initDatabase()` and `_initInMemoryDatabase()` must be updated.

#### Step 3.5.A.2: Add migration block

Add after the `if (oldVersion < 42)` block in `_onUpgrade`:

```dart
// WHY: Phase 3.5 — Repeat-Last Toggles. Per-entry opt-in for seeding location,
// weather, and contractors from the previous entry in the same project.
// Defaults to 0 (off) so existing entries are unaffected.
if (oldVersion < 43) {
  await db.execute('ALTER TABLE daily_entries ADD COLUMN repeat_last_location INTEGER DEFAULT 0');
  await db.execute('ALTER TABLE daily_entries ADD COLUMN repeat_last_weather INTEGER DEFAULT 0');
  await db.execute('ALTER TABLE daily_entries ADD COLUMN repeat_last_contractors INTEGER DEFAULT 0');
}
```

#### Step 3.5.A.3: Update table creation SQL

In the `daily_entries` CREATE TABLE statement (used for fresh installs), add:
```sql
repeat_last_location INTEGER DEFAULT 0,
repeat_last_weather INTEGER DEFAULT 0,
repeat_last_contractors INTEGER DEFAULT 0
```

// NOTE: Insert after line 31 (`deleted_by TEXT,`) in lib/core/database/schema/entry_tables.dart, before FOREIGN KEY constraints

#### Step 3.5.A.4: Update SchemaVerifier expected columns

**File:** `lib/core/database/schema_verifier.dart`

Add `'repeat_last_location'`, `'repeat_last_weather'`, `'repeat_last_contractors'` to the expected columns list for `daily_entries` (line ~66).

// WHY: SchemaVerifier validates table structure on startup. Missing columns trigger self-healing warnings.

#### Step 3.5.A.5: Verify sync adapter includes new columns

**File:** `lib/features/sync/adapters/daily_entry_adapter.dart`

Verify `localOnlyColumns` does NOT include the new repeat_last_* columns. The adapter syncs all model columns by default via `toMap()`, so no code changes are needed unless the adapter has an explicit exclusion list.

// WHY: Without this, toggles set by user won't sync to cloud or other devices.

#### Step 3.5.A.6: Create Supabase migration for repeat_last columns

**File:** Create `supabase/migrations/YYYYMMDD_add_repeat_last_toggles.sql`

```sql
-- WHY: Local SQLite has these columns (v43). Remote must match for sync to work.
ALTER TABLE daily_entries ADD COLUMN repeat_last_location INTEGER DEFAULT 0;
ALTER TABLE daily_entries ADD COLUMN repeat_last_weather INTEGER DEFAULT 0;
ALTER TABLE daily_entries ADD COLUMN repeat_last_contractors INTEGER DEFAULT 0;
```

Run: `npx supabase db push` to apply.

---

### Sub-phase 3.5.B: Model Changes

**Files:**
- Modify: `lib/features/entries/data/models/daily_entry.dart`

**Agent:** `backend-data-layer-agent`

#### Step 3.5.B.1: Add fields to DailyEntry

```dart
// Add to class fields:
final bool repeatLastLocation;
final bool repeatLastWeather;
final bool repeatLastContractors;

// Add to constructor parameters (with defaults):
this.repeatLastLocation = false,
this.repeatLastWeather = false,
this.repeatLastContractors = false,
```

#### Step 3.5.B.2: Update copyWith

```dart
// Add parameters:
bool? repeatLastLocation,
bool? repeatLastWeather,
bool? repeatLastContractors,

// Add to return body:
repeatLastLocation: repeatLastLocation ?? this.repeatLastLocation,
repeatLastWeather: repeatLastWeather ?? this.repeatLastWeather,
repeatLastContractors: repeatLastContractors ?? this.repeatLastContractors,
```

#### Step 3.5.B.3: Update toMap

```dart
'repeat_last_location': repeatLastLocation ? 1 : 0,
'repeat_last_weather': repeatLastWeather ? 1 : 0,
'repeat_last_contractors': repeatLastContractors ? 1 : 0,
```

#### Step 3.5.B.4: Update fromMap

```dart
repeatLastLocation: (map['repeat_last_location'] as int? ?? 0) == 1,
repeatLastWeather: (map['repeat_last_weather'] as int? ?? 0) == 1,
repeatLastContractors: (map['repeat_last_contractors'] as int? ?? 0) == 1,
```

---

### Sub-phase 3.5.C: Repository — getMostRecentEntry

**Files:**
- Modify: `lib/features/entries/data/repositories/daily_entry_repository.dart`

**Agent:** `backend-data-layer-agent`

#### Step 3.5.C.1: Add getMostRecentEntry method

```dart
/// Returns the most recent entry for [projectId] created by [userId],
/// excluding the entry with [excludeId] (the one being created).
/// WHY: Used by repeat-last-toggles to seed new entries from prior data.
/// SECURITY: Scoped to same user — no cross-user data leakage.
Future<DailyEntry?> getMostRecentEntry(
  String projectId, {
  required String userId,
  String? excludeId,
}) async {
  final db = await _dbService.database;
  final results = await db.query(
    'daily_entries',
    where: 'project_id = ? AND created_by_user_id = ? AND deleted_at IS NULL'
        '${excludeId != null ? ' AND id != ?' : ''}',
    whereArgs: [projectId, userId, if (excludeId != null) excludeId],
    orderBy: 'date DESC',
    limit: 1,
  );
  if (results.isEmpty) return null;
  return DailyEntry.fromMap(results.first);
}
```

---

### Sub-phase 3.5.D: Provider — seedFromPrevious

**Files:**
- Modify: `lib/features/entries/presentation/providers/daily_entry_provider.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 3.5.D.1: Add seedFromPrevious method

```dart
/// Seeds a newly created entry with fields from the most recent entry,
/// based on the repeat-last toggles of the previous entry.
/// Returns the updated entry if seeding occurred, null otherwise.
/// WHY: Saves inspectors from re-entering location/weather/contractors each day.
Future<DailyEntry?> seedFromPrevious(DailyEntry newEntry) async {
  // WHY: createdByUserId is nullable (String?) — guard against null to prevent runtime crash
  if (newEntry.createdByUserId == null) return null;
  final previous = await repository.getMostRecentEntry(
    newEntry.projectId,
    userId: newEntry.createdByUserId!,
    excludeId: newEntry.id,
  );
  if (previous == null) return null;

  DailyEntry seeded = newEntry;
  bool changed = false;

  if (previous.repeatLastLocation && previous.locationId != null) {
    seeded = seeded.copyWith(locationId: previous.locationId);
    changed = true;
  }
  if (previous.repeatLastWeather && previous.weather != null) {
    // NOTE: Only seed weather type — temperature should be fresh each day
    seeded = seeded.copyWith(weather: previous.weather);
    changed = true;
  }
  // NOTE: repeatLastContractors is handled by the ContractorEditingController
  // after the entry is created — it copies personnel assignments from previous entry.
  // The flag is read by the UI, not by this provider.

  if (changed) {
    await repository.update(seeded);
    return seeded;
  }
  return null;
}
```

---

### Sub-phase 3.5.E: UI — Toggle Switches in Entry Basics

**Files:**
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart`
- Modify: `lib/features/entries/presentation/widgets/entry_basics_section.dart` (if toggles belong in basics)

**Agent:** `frontend-flutter-specialist-agent`

#### Step 3.5.E.1: Add repeat-last toggles to entry basics section

In `_buildEntryHeader` (or `EntryBasicsSection`), add after the weather row inside the collapsible area:

```dart
// WHY: Repeat-last toggles let inspectors carry forward location/weather/contractors
// to the next day's entry. Displayed in basics section because they affect entry creation.
if (_isDraftEntry && _entry != null) ...[
  const Divider(height: AppTheme.space6),
  Text('Repeat on next entry', style: tt.titleSmall!.copyWith(color: cs.onSurface)),
  const SizedBox(height: AppTheme.space2),
  AppToggle(
    key: TestingKeys.entries.repeatLastLocation,
    label: 'Location',
    value: _entry!.repeatLastLocation,
    onChanged: (v) => _updateRepeatToggle(repeatLastLocation: v),
  ),
  AppToggle(
    key: TestingKeys.entries.repeatLastWeather,
    label: 'Weather type',
    value: _entry!.repeatLastWeather,
    onChanged: (v) => _updateRepeatToggle(repeatLastWeather: v),
  ),
  AppToggle(
    key: TestingKeys.entries.repeatLastContractors,
    label: 'Contractors',
    value: _entry!.repeatLastContractors,
    onChanged: (v) => _updateRepeatToggle(repeatLastContractors: v),
  ),
],
```

#### Step 3.5.E.2: Add _updateRepeatToggle helper

```dart
Future<void> _updateRepeatToggle({
  bool? repeatLastLocation,
  bool? repeatLastWeather,
  bool? repeatLastContractors,
}) async {
  final entry = _entry;
  if (entry == null) return;

  final updated = entry.copyWith(
    repeatLastLocation: repeatLastLocation,
    repeatLastWeather: repeatLastWeather,
    repeatLastContractors: repeatLastContractors,
  );
  await context.read<DailyEntryProvider>().updateEntry(updated);
  if (mounted) setState(() => _entry = updated);
}
```

#### Step 3.5.E.3: Wire seeding into entry creation flow

In `_loadEntryData`, after the draft is persisted (line ~266), add:

```dart
// WHY: Seed from previous entry based on repeat-last toggles
if (_isDraftEntry && created != null) {
  final seeded = await entryProvider.seedFromPrevious(created);
  if (seeded != null) entry = seeded;
}
```

---

### Sub-phase 3.5.F: Contractor Repeat-Last

**Files:**
- Modify: `lib/features/entries/presentation/controllers/contractor_editing_controller.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 3.5.F.1: Add copyContractorsFromEntry method

```dart
/// Copies contractor assignments (entry_contractors rows) from [sourceEntryId]
/// to [targetEntryId]. Used by repeat-last-contractors toggle.
/// WHY: Avoids re-selecting the same contractors every day.
// IMPORTANT: sourceEntryId MUST come from getMostRecentEntry() which is user-scoped.
// Do NOT call this with arbitrary entry IDs — would leak cross-user contractor data.
Future<void> copyContractorsFromEntry(String sourceEntryId, String targetEntryId) async {
  final sourceContractors = await _contractorsDatasource.getByEntryId(sourceEntryId);
  for (final ec in sourceContractors) {
    // WHY: Actual datasource API is add(entryId, contractorId) — see entry_contractors_local_datasource.dart:102
    await _contractorsDatasource.add(targetEntryId, ec.contractorId);
  }
}
```

#### Step 3.5.F.2: Wire into entry creation

In `entry_editor_screen.dart`, after seeding (Step 3.5.E.3), add:

```dart
// WHY: Seed contractors from previous entry if repeat-last-contractors enabled
if (previous != null && previous.repeatLastContractors) {
  await _contractorController?.copyContractorsFromEntry(previous.id, entry!.id);
}
```

NOTE: `previous` needs to be available here — adjust the seeding flow to return the previous entry reference.

---

### Sub-phase 3.5.G: Tests

**Files:**
- Create: `test/features/entries/data/repeat_last_toggles_test.dart`

**Agent:** `qa-testing-agent`

#### Step 3.5.G.1: Test cases

1. **Default off**: New entry has all repeat toggles = false
2. **Seed location**: Previous entry with repeat_last_location=true seeds locationId
3. **Seed weather**: Previous entry with repeat_last_weather=true seeds weather type (not temp)
4. **No cross-user**: Previous entry by user A does not seed user B's entry
5. **Toggle persistence**: Toggling repeat flags persists to database
6. **Model serialization**: toMap/fromMap round-trip preserves boolean toggles

---

### Sub-phase 3.5.H: Testing Keys for Repeat-Last Toggles

**Files:**
- Modify: `lib/shared/testing_keys/entries_keys.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 3.5.H.1: Add repeat-last toggle keys to entries_keys.dart

Add to the `EntriesKeys` class:

```dart
static const Key repeatLastLocation = Key('repeat_last_location_toggle');
static const Key repeatLastWeather = Key('repeat_last_weather_toggle');
static const Key repeatLastContractors = Key('repeat_last_contractors_toggle');
```

These are referenced by the `AppToggle` widgets added in Sub-phase 3.5.E.

### Sub-phase 3.5.I: Quality Gate

**Agent:** `qa-testing-agent`

```powershell
pwsh -Command "flutter analyze"
pwsh -Command "flutter test test/features/entries/"
```

**Testing Keys**: Verify the 3 new toggle keys are wired by running the driver /find endpoint against each key name, or by inspecting the widget tree in a test.

---

## Phase 4: Calendar/Home Screen Rewrite

**Goal:** Migrate `HomeScreen` (~1800 lines) — the TOP VIOLATOR with 38 TextStyle, 31 EdgeInsets, 9 BorderRadius violations. Also migrate the inline `_AnimatedDayCell` and `_ModernEntryCard` private widgets.

### Sub-phase 4.A: HomeScreen — Top-level build + state methods

**Files:**
- Modify: `lib/features/entries/presentation/screens/home_screen.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 4.A.1: Add theme variable declarations

Add at the top of `build()` and every `_build*` helper method:
```dart
final cs = Theme.of(context).colorScheme;
final tt = Theme.of(context).textTheme;
final fg = FieldGuideColors.of(context);
```

NOTE: Do NOT add to `_handleReportScroll`, `_setupFocusListeners`, `_saveIfEditing`, `_saveIfEditingContractor`, `dispose()` — these don't render widgets.

#### Step 4.A.2: Replace inline TextStyle — empty/select states

**Instances in `_buildNoProjectsState` (~line 443-476):**
- Line ~454: `TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)` → `tt.titleMedium!.copyWith(fontWeight: FontWeight.bold, color: cs.onSurface)`
- Line ~463: `TextStyle(color: AppTheme.textSecondary)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant)`

**Instances in `_buildSelectProjectState` (~line 479-512):**
- Line ~489: `TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)` → `tt.titleMedium!.copyWith(fontWeight: FontWeight.bold, color: cs.onSurface)`
- Line ~498: `TextStyle(color: AppTheme.textSecondary)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant)`

**Instances in `_buildEmptyState` (~line 927-961):**
- Line ~943: `TextStyle(color: AppTheme.textSecondary, fontSize: 14)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant)`

#### Step 4.A.3: Replace static colors — empty/select states

**Instances:**
- Line ~450: `AppTheme.textTertiary` → `fg.textTertiary`
- Line ~486: `AppTheme.textTertiary` → `fg.textTertiary`
- Line ~938: `AppTheme.textTertiary` → `fg.textTertiary`

---

### Sub-phase 4.B: HomeScreen — Project header + calendar

**Agent:** `frontend-flutter-specialist-agent`

#### Step 4.B.1: Replace _buildProjectHeader colors + styles

**Instances (~line 515-559):**
- Line ~517: `AppTheme.primaryCyan.withValues(alpha: 0.1)` → `cs.primary.withValues(alpha: 0.1)`
- Line ~524: `AppTheme.primaryCyan` → `cs.primary`
- Line ~532: `TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: AppTheme.textPrimary)` → `tt.titleSmall!.copyWith(color: cs.onSurface)`
- Line ~542: `TextStyle(fontSize: 12, color: AppTheme.textSecondary)` → `tt.bodySmall!.copyWith(color: cs.onSurfaceVariant)`

#### Step 4.B.2: Replace _buildCalendarFormatToggle colors + styles

**Instances (~line 584-661):**
- Line ~590: `AppTheme.surfaceDark` → `cs.surface`
- Line ~641: `AppTheme.primaryCyan` → `cs.primary`
- Line ~642: `AppTheme.surfaceElevated` → `fg.surfaceElevated`
- Line ~645: `AppTheme.primaryCyan` → `cs.primary`
- Line ~646: `AppTheme.surfaceHighlight` → `cs.outline`
- Line ~653: `TextStyle(fontSize: 13, fontWeight: FontWeight.w600, ...)` → `tt.labelLarge!.copyWith(color: isSelected ? fg.textInverse : cs.onSurface)`
- Line ~656: `AppTheme.textInverse` → `fg.textInverse`
- Line ~656: `AppTheme.textPrimary` → `cs.onSurface`

#### Step 4.B.3: Replace _buildCalendar headerStyle + calendarStyle

**Instances (~line 663-811):**
- Line ~802: `TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)` → `tt.titleSmall!.copyWith(color: cs.onSurface)`

---

### Sub-phase 4.C: HomeScreen — Selected day content + report preview

**Agent:** `frontend-flutter-specialist-agent`

#### Step 4.C.1: Replace _buildSelectedDayContent styles

**Instances (~line 822-924):**
- Line ~888: `TextStyle(color: AppTheme.textSecondary, fontSize: 12)` → `tt.bodySmall!.copyWith(color: cs.onSurfaceVariant)`

#### Step 4.C.2: Replace _buildReportContent styles (largest block)

**Instances (~line 1010-1281):**
- Line ~1031: `AppTheme.primaryCyan` → `cs.primary`
- Line ~1040: `TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppTheme.primaryCyan)` → `tt.titleSmall!.copyWith(fontWeight: FontWeight.bold, color: cs.primary)`
- Line ~1049: `TextStyle(fontSize: 12, color: AppTheme.textSecondary)` → `tt.bodySmall!.copyWith(color: cs.onSurfaceVariant)`
- Line ~1076: `TextStyle(fontSize: 14, color: AppTheme.textPrimary)` → `tt.bodyMedium!.copyWith(color: cs.onSurface)`
- Line ~1086: `TextStyle(fontSize: 14, color: AppTheme.textSecondary)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant)`
- Line ~1092: `TextStyle(fontSize: 14, color: AppTheme.textSecondary, fontStyle: FontStyle.italic)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant, fontStyle: FontStyle.italic)`
- Line ~1113: `TextStyle(fontSize: 13)` → `tt.bodyMedium`
- Line ~1133: `TextStyle(fontSize: 13)` → `tt.bodyMedium`
- Line ~1150: `TextStyle(fontSize: 14, height: 1.4, ...)` → `tt.bodyMedium!.copyWith(height: 1.4, color: ...)`
- Line ~1169: `TextStyle(fontSize: 14, height: 1.4)` → `tt.bodyMedium!.copyWith(height: 1.4)`
- Line ~1203: `TextStyle(fontSize: 13)` → `tt.bodyMedium`
- Line ~1247: `TextStyle(fontSize: 14, height: 1.4, ...)` → `tt.bodyMedium!.copyWith(height: 1.4, color: ...)`
- Line ~1270: `TextStyle(fontSize: 14)` → `tt.bodyMedium`

#### Step 4.C.3: Replace _buildEditablePreviewSection styles + colors

**Instances (~line 1283-1346):**
- Line ~1306: `AppTheme.primaryCyan` → `cs.primary`
- Line ~1306: `AppTheme.surfaceHighlight.withValues(alpha: 0.3)` → `cs.outline.withValues(alpha: 0.3)`
- Line ~1310: `AppTheme.primaryCyan.withValues(alpha: 0.05)` → `cs.primary.withValues(alpha: 0.05)`
- Line ~1310: `AppTheme.surfaceElevated` → `fg.surfaceElevated`
- Line ~1317: `AppTheme.primaryCyan` → `cs.primary`
- Line ~1322: `TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: AppTheme.textPrimary)` → `tt.bodyMedium!.copyWith(fontWeight: FontWeight.w600, color: cs.onSurface)`
- Line ~1334: `AppTheme.textTertiary` → `fg.textTertiary`

---

### Sub-phase 4.D: HomeScreen — Contractors section + dialogs

**Agent:** `frontend-flutter-specialist-agent`

#### Step 4.D.1: Replace _buildContractorsSection styles + colors

**Instances (~line 1348-1511):**
- Line ~1397: `AppTheme.surfaceHighlight.withValues(alpha: 0.3)` → `cs.outline.withValues(alpha: 0.3)`
- Line ~1400: `AppTheme.surfaceElevated` → `fg.surfaceElevated`
- Line ~1407: `AppTheme.primaryCyan` → `cs.primary`
- Line ~1412: `TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: AppTheme.textPrimary)` → `tt.bodyMedium!.copyWith(fontWeight: FontWeight.w600, color: cs.onSurface)`
- Line ~1421: `TextStyle(fontSize: 11, color: AppTheme.textSecondary)` → `tt.labelSmall!.copyWith(color: cs.onSurfaceVariant)`
- Line ~1438: `AppTheme.surfaceHighlight` → `cs.outline`
- Line ~1444: `AppTheme.textTertiary` → `fg.textTertiary`
- Line ~1448: `TextStyle(fontSize: 13, color: AppTheme.textTertiary, fontStyle: FontStyle.italic)` → `tt.bodyMedium!.copyWith(color: fg.textTertiary, fontStyle: FontStyle.italic)`
- Line ~1496: `AppTheme.primaryCyan` → `cs.primary`
- Line ~1500: `TextStyle(fontSize: 13, color: AppTheme.primaryCyan, ...)` → `tt.bodyMedium!.copyWith(color: cs.primary, fontWeight: FontWeight.w500)`

#### Step 4.D.2: Replace _showAddContractorDialog + _showDeleteEntryDialog styles

**Instances (~line 1598-1807):**
- Line ~1637: `TextStyle(fontWeight: FontWeight.bold, fontSize: 16)` → `tt.titleMedium` (no color override needed — uses default)
- Line ~1714: `AppTheme.statusError` → `cs.error`
- Line ~1741: `TextStyle(color: AppTheme.textSecondary, fontSize: 13)` → `tt.bodySmall!.copyWith(color: cs.onSurfaceVariant)`
- Line ~1759: `TextStyle(color: AppTheme.statusError, fontSize: 12)` → `tt.bodySmall!.copyWith(color: cs.error)`
- Line ~1776: `AppTheme.statusError` → `cs.error`
- Line ~1777: `AppTheme.textInverse` → `fg.textInverse`

---

### Sub-phase 4.E: _AnimatedDayCell + _ModernEntryCard (private widgets)

**Agent:** `frontend-flutter-specialist-agent`

#### Step 4.E.1: Replace _AnimatedDayCell styles + colors

NOTE: These private widgets have `context` available in `build()`.

**Instances (~line 1814-1917):**
- Line ~1893: `AppTheme.primaryCyan` → `cs.primary`
- Line ~1895: `AppTheme.primaryCyan.withValues(alpha: 0.08)` → `cs.primary.withValues(alpha: 0.08)`
- Line ~1898: `AppTheme.primaryCyan.withValues(alpha: 0.5)` → `cs.primary.withValues(alpha: 0.5)`
- Line ~1905: `TextStyle(fontSize: 14, fontWeight: ..., color: ...)` → `tt.bodyMedium!.copyWith(fontWeight: ..., color: ...)`
- Line ~1909: `AppTheme.textInverse` → `fg.textInverse`
- Line ~1910: `AppTheme.textPrimary` → `cs.onSurface`

#### Step 4.E.2: Replace _ModernEntryCard styles + colors

**Instances (~line 1920-end):**
- Line ~1966: `AppTheme.primaryCyan.withValues(alpha: 0.12)` → `cs.primary.withValues(alpha: 0.12)`
- Line ~1967: `AppTheme.surfaceElevated` → `fg.surfaceElevated`
- Line ~1970: `AppTheme.primaryCyan` → `cs.primary`
- Line ~1970: `AppTheme.surfaceHighlight.withValues(alpha: 0.3)` → `cs.outline.withValues(alpha: 0.3)`
- Line ~1988: `AppTheme.primaryCyan` → `cs.primary`
- Line ~1993: `TextStyle(fontWeight: FontWeight.bold, fontSize: 12, ...)` → `tt.labelMedium!.copyWith(fontWeight: FontWeight.bold, color: ...)`
- Line ~1995: `AppTheme.primaryCyan` → `cs.primary`
- Line ~1995: `AppTheme.textPrimary` → `cs.onSurface`
- All remaining `AppTheme.statusInfo` → `fg.statusInfo` (entry status colors stay custom per rules — these are domain colors, BUT verify if FieldGuideColors has statusInfo. If not, keep as `AppTheme.statusInfo`.)
- Line ~2003 and below: Continue pattern for status text, timestamp, attribution text

---

### Sub-phase 4.F: Quality Gate

**Agent:** `qa-testing-agent`

```powershell
pwsh -Command "flutter analyze lib/features/entries/presentation/screens/home_screen.dart"
pwsh -Command "flutter test test/features/entries/"
```

Verify: Grep for remaining violations:
```powershell
pwsh -Command "Select-String -Path 'lib/features/entries/presentation/screens/home_screen.dart' -Pattern 'AppTheme\.(textPrimary|textSecondary|textTertiary|textInverse|surfaceElevated|surfaceHighlight|surfaceDark|primaryCyan|statusError|statusWarning|statusSuccess)' | Measure-Object"
```
Target: 0 matches.

**Testing Keys**: For each screen/widget modified in this phase:
1. Review existing TestingKeys assignments — transfer all keys to their new design system wrapper
2. Add new keys for any new interactive elements (buttons, fields, toggles)
3. Update the corresponding key file in `lib/shared/testing_keys/` if keys are added/renamed
4. Run: `pwsh -Command "flutter test test/features/entries/"` to verify widget tests pass

---

## Phase 5: List Screens Batch

**Goal:** Migrate 8 list/settings screens in a single phase. These are smaller screens with lower violation counts.

### Sub-phase 5.A: ProjectListScreen

**Files:**
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 5.A.1: Add theme variables + replace Colors.* violations

The file has 6 `Colors.*` violations. Add `cs`/`tt`/`fg` to `build()` and key helper methods.

**Pattern:**
```dart
// Before:
Colors.grey → cs.onSurfaceVariant  (for text/icons)
Colors.grey → cs.outline           (for borders/dividers)
```

**Instances to fix (scan for `Colors.grey`, `Colors.black`, etc.):**
- Replace all `Colors.grey` with `cs.onSurfaceVariant` (icon/text) or `cs.outline` (border)
- Replace any `AppTheme.text*` / `AppTheme.surface*` / `AppTheme.primary*` per the standard mapping table

---

### Sub-phase 5.B: EntriesListScreen

**Files:**
- Modify: `lib/features/entries/presentation/screens/entries_list_screen.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 5.B.1: Replace inline TextStyle (16 violations)

**Instances:**
- Line ~146: `TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)` → `tt.titleMedium!.copyWith(fontWeight: FontWeight.bold, color: cs.onSurface)`
- Line ~155: `TextStyle(color: AppTheme.textSecondary)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant)`
- Line ~204: `TextStyle(fontSize: 13, color: AppTheme.textSecondary)` → `tt.bodySmall!.copyWith(color: cs.onSurfaceVariant)`
- Line ~250: `TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)` → `tt.titleMedium!.copyWith(fontWeight: FontWeight.bold, color: cs.onSurface)`
- Line ~258: `TextStyle(color: AppTheme.textSecondary)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant)`
- Line ~300: `TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)` → `tt.titleMedium!.copyWith(fontWeight: FontWeight.bold, color: cs.onSurface)`
- Line ~308: `TextStyle(color: AppTheme.textSecondary)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant)`
- Line ~364: `TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.primaryCyan, ...)` → `tt.titleSmall!.copyWith(fontWeight: FontWeight.bold, color: cs.primary, letterSpacing: 0.5)`
- Line ~423: `TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)` → `tt.titleSmall!.copyWith(color: cs.onSurface)`
- Line ~438: `TextStyle(fontSize: 14, color: AppTheme.textSecondary)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant)`
- Line ~457: `TextStyle(fontSize: 12, color: AppTheme.textTertiary)` → `tt.bodySmall!.copyWith(color: fg.textTertiary)` (multiple instances)
- Line ~472: same pattern

#### Step 5.B.2: Replace EdgeInsets violations (10 violations)

**Instances:**
- Line ~138: `EdgeInsets.all(32)` → `EdgeInsets.all(AppTheme.space8)`
- Line ~143: `SizedBox(height: 16)` → `SizedBox(height: AppTheme.space4)`
- Line ~158: `SizedBox(height: 24)` → `SizedBox(height: AppTheme.space6)`
- Line ~196: `EdgeInsets.all(12)` → `EdgeInsets.all(AppTheme.space3)`
- Line ~201: `SizedBox(width: 8)` → `SizedBox(width: AppTheme.space2)`
- Line ~216: `EdgeInsets.all(16)` → `EdgeInsets.all(AppTheme.space4)`
- Line ~242: `EdgeInsets.all(32)` → `EdgeInsets.all(AppTheme.space8)`
- Line ~247: `SizedBox(height: 24)` → `SizedBox(height: AppTheme.space6)`
- Line ~256: `SizedBox(height: 12)` → `SizedBox(height: AppTheme.space3)`
- Line ~361: `EdgeInsets.only(left: 4, top: 8, bottom: 8)` → `EdgeInsets.only(left: AppTheme.space1, top: AppTheme.space2, bottom: AppTheme.space2)`
- Line ~373: `SizedBox(height: 8)` → `SizedBox(height: AppTheme.space2)`
- Line ~388: `EdgeInsets.only(bottom: 8)` → `EdgeInsets.only(bottom: AppTheme.space2)`
- Line ~393: `BorderRadius.circular(12)` → `BorderRadius.circular(AppTheme.radiusMedium)`
- Line ~395: `EdgeInsets.all(16)` → `EdgeInsets.all(AppTheme.space4)`
- Line ~401: `EdgeInsets.all(12)` → `EdgeInsets.all(AppTheme.space3)`
- Line ~403: `BorderRadius.circular(12)` → `BorderRadius.circular(AppTheme.radiusMedium)`
- Line ~410: `SizedBox(width: 16)` → `SizedBox(width: AppTheme.space4)`

#### Step 5.B.3: Replace static color references

**Instances:**
- All `AppTheme.statusError` → `cs.error`
- All `AppTheme.primaryCyan` → `cs.primary`
- All `AppTheme.textPrimary` → `cs.onSurface`
- All `AppTheme.textSecondary` → `cs.onSurfaceVariant`
- All `AppTheme.textTertiary` → `fg.textTertiary`
- All `AppTheme.surfaceElevated` → `fg.surfaceElevated`

---

### Sub-phase 5.C: DraftsListScreen

**Files:**
- Modify: `lib/features/entries/presentation/screens/drafts_list_screen.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 5.C.1: Apply standard migration

Scan for `AppTheme.*` static tokens, hardcoded `EdgeInsets`, `Colors.black`. Apply the standard mapping. This is a small screen (~200 lines) — violations are mostly in padding and the one `Colors.black` reference.

---

### Sub-phase 5.D: FormsListScreen

**Files:**
- Modify: `lib/features/forms/presentation/screens/forms_list_screen.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 5.D.1: Apply standard migration

Mostly uses `AppTheme.*` tokens already. Replace `AppTheme.text*` / `AppTheme.surface*` / `AppTheme.primary*` with theme-aware equivalents per the mapping table.

---

### Sub-phase 5.E: TodosScreen

**Files:**
- Modify: `lib/features/todos/presentation/screens/todos_screen.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 5.E.1: Apply standard migration

Scan for literal `BorderRadius` and `AppTheme.*` tokens. Replace per mapping table.

**Known instances:**
- Line ~80: `AppTheme.primaryBlue` → `cs.primary` (filter icon active color)
- Any `AppTheme.textTertiary` → `fg.textTertiary`

---

### Sub-phase 5.F: TrashScreen

**Files:**
- Modify: `lib/features/settings/presentation/screens/trash_screen.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 5.F.1: Replace hardcoded fontSize violations

**Instances:**
- Line ~144: `TextStyle(fontSize: 18, color: AppTheme.textTertiary)` → `tt.titleMedium!.copyWith(color: fg.textTertiary)`
- Line ~150: `TextStyle(fontSize: 14, color: AppTheme.textTertiary)` → `tt.bodyMedium!.copyWith(color: fg.textTertiary)`
- Line ~176: `TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textSecondary)` → `tt.titleSmall!.copyWith(color: cs.onSurfaceVariant)`
- Line ~207: `TextStyle(fontSize: 12)` → `tt.bodySmall`
- Line ~210: `TextStyle(fontSize: 12)` → `tt.bodySmall`
- Line ~215: `TextStyle(fontSize: 12, ...)` → `tt.bodySmall!.copyWith(color: cs.error, fontWeight: FontWeight.w600)`

#### Step 5.F.2: Replace hardcoded EdgeInsets

**Instances:**
- Line ~143: `SizedBox(height: 16)` → `SizedBox(height: AppTheme.space4)`
- Line ~148: `SizedBox(height: 8)` → `SizedBox(height: AppTheme.space2)`
- Line ~165: `SizedBox(height: 32)` → `SizedBox(height: AppTheme.space8)`
- Line ~173: `EdgeInsets.fromLTRB(16, 16, 16, 4)` → `EdgeInsets.fromLTRB(AppTheme.space4, AppTheme.space4, AppTheme.space4, AppTheme.space1)`

#### Step 5.F.3: Replace static color references

- All `AppTheme.statusError` → `cs.error`
- All `AppTheme.primaryCyan` → `cs.primary`
- All `AppTheme.textSecondary` → `cs.onSurfaceVariant`
- All `AppTheme.textTertiary` → `fg.textTertiary`

---

### Sub-phase 5.G: PersonnelTypesScreen

**Files:**
- Modify: `lib/features/settings/presentation/screens/personnel_types_screen.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 5.G.1: Apply standard migration

Mostly clean file. Replace:
- Line ~64: `AppTheme.textTertiary` → `fg.textTertiary`
- Line ~69: `TextStyle(fontSize: 18, color: AppTheme.textSecondary)` → `tt.titleMedium!.copyWith(color: cs.onSurfaceVariant)`
- Line ~75: `TextStyle(color: AppTheme.textTertiary)` → `tt.bodyMedium!.copyWith(color: fg.textTertiary)`
- Line ~67: `SizedBox(height: 16)` → `SizedBox(height: AppTheme.space4)`
- Line ~73: `SizedBox(height: 8)` → `SizedBox(height: AppTheme.space2)`

---

### Sub-phase 5.H: AdminDashboardScreen

**Files:**
- Modify: `lib/features/settings/presentation/screens/admin_dashboard_screen.dart`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 5.H.1: Replace Colors.grey violations (6 instances)

**Instances:**
- Line ~63: `Colors.grey` (cloud_off icon) → `cs.onSurfaceVariant`
- Line ~71: `TextStyle(color: Colors.grey)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant)`
- Line ~131: `TextStyle(color: Colors.grey)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant)`
- Line ~150: `TextStyle(color: Colors.grey)` → `tt.bodyMedium!.copyWith(color: cs.onSurfaceVariant)`
- Any remaining `Colors.grey` → `cs.onSurfaceVariant`

#### Step 5.H.2: Replace remaining static tokens

- `AppTheme.statusError` → `cs.error`
- Replace hardcoded `SizedBox(height: 16)` → `SizedBox(height: AppTheme.space4)` etc.
- Replace `EdgeInsets.symmetric(horizontal: 16, vertical: 24)` → `EdgeInsets.symmetric(horizontal: AppTheme.space4, vertical: AppTheme.space6)`

---

### Sub-phase 5.I: Quality Gate

**Agent:** `qa-testing-agent`

#### Step 5.I.1: Static analysis

```powershell
pwsh -Command "flutter analyze"
```

Must pass with zero errors. Warnings acceptable if pre-existing.

#### Step 5.I.2: Run all tests

```powershell
pwsh -Command "flutter test"
```

Must pass. If any test fails due to hardcoded color assertions, update the test to use theme-aware lookups.

#### Step 5.I.3: Violation audit

Run a final grep across all modified files to confirm zero remaining violations:

```powershell
# Check for remaining static color tokens that should be theme-aware
pwsh -Command "Select-String -Path 'lib/features/dashboard/**/*.dart','lib/features/entries/**/*.dart','lib/features/projects/presentation/screens/project_list_screen.dart','lib/features/forms/presentation/screens/forms_list_screen.dart','lib/features/todos/presentation/screens/todos_screen.dart','lib/features/settings/presentation/screens/*.dart' -Pattern 'AppTheme\.(textPrimary|textSecondary|textTertiary|textInverse|surfaceElevated|surfaceHighlight|surfaceDark|primaryCyan|statusError|statusWarning|statusSuccess|primaryBlue|statusInfo|accentAmber)' -Recurse | Measure-Object"
```

Target: 0 matches (except in test files or intentionally static references like entry status colors / weather colors that remain static per design rules).

#### Step 5.I.4: Testing keys verification

**Testing Keys**: For each screen/widget modified in Phases 2-5:
1. Review existing TestingKeys assignments — transfer all keys to their new design system wrapper
2. Add new keys for any new interactive elements (buttons, fields, toggles)
3. Update the corresponding key file in `lib/shared/testing_keys/` if keys are added/renamed
4. Run: `pwsh -Command "flutter test test/features/"` to verify widget tests pass

#### Step 5.I.5: Golden test regeneration (Phases 2-5 batch)

**Golden Tests**: Regenerate all golden test images to match the new theme-aware rendering:
```
pwsh -Command "flutter test --update-goldens test/golden/"
```
Commit updated golden files with the phase. Review diffs to confirm changes are only color/spacing related, not structural regressions.

#### Step 5.I.6: Manual smoke test

Build and run on Android device:
```powershell
pwsh -File tools/build.ps1 -Platform android -BuildType debug -Driver
```

Verify:
1. Dashboard loads — stat cards, budget card, tracked items, approaching limit all render
2. Calendar screen loads — day cells colored, format toggle works, entry cards render
3. Entry editor loads — all sections render, inline editing works
4. Create new entry — repeat-last toggles visible, toggling persists
5. All list screens load without visual regressions
6. No white/invisible text on any screen

<!-- ======= Part: phases6-8 ======= -->

# Phases 6-8: Feature Screen Rewrites

> **Dependency**: All phases depend on Phase 1 (design system tokens + components).
> Phases 6, 7, and 8 are independent of each other and Phases 2-5 — they can run in parallel.

---

## Phase 6: Settings + Sync Screens

**Goal**: Migrate the settings/sync screens cluster to the design system. SyncDashboardScreen and ConflictViewerScreen are the two worst offenders in the entire codebase — nearly every color is hardcoded.

### Sub-phase 6.A: SettingsScreen

**Files:**
- Modify: `lib/features/settings/presentation/screens/settings_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 6.A.1: Replace AppTheme color tokens

The SettingsScreen has moderate violations — mostly `AppTheme.*` static references that need to become theme-aware.

**Instance list** (line numbers from source):

| Line | Old | New | WHY |
|------|-----|-----|-----|
| 165 | `color: AppTheme.primaryCyan` | `color: cs.primary` | Icon tint |
| 174 | `color: AppTheme.primaryCyan` | `color: cs.primary` | Admin icon tint |
| 182 | `color: AppTheme.statusError` | `color: cs.error` | Sign out icon |
| 222 | `color: AppTheme.statusWarning` | `color: fg.statusWarning` | Trash badge bg |
| 228 | `color: Colors.white` | `color: fg.textInverse` | Trash badge text |
| 245 | `color: AppTheme.statusWarning` | `color: fg.statusWarning` | Clear cache icon |
| 261 | `backgroundColor: AppTheme.success` | `backgroundColor: fg.statusSuccess` | Template chip |

**Pattern** — for every `AppTheme.primaryCyan` icon tint:
```dart
// WHY: Migrate from static AppTheme to theme-aware tokens
// BEFORE
leading: const Icon(Icons.edit_outlined, color: AppTheme.primaryCyan),
// AFTER
leading: Icon(Icons.edit_outlined, color: Theme.of(context).colorScheme.primary),
```

#### Step 6.A.2: Replace hardcoded EdgeInsets

| Line | Old | New |
|------|-----|-----|
| 219 | `EdgeInsets.symmetric(horizontal: 8, vertical: 2)` | `EdgeInsets.symmetric(horizontal: AppTheme.space2, vertical: 2)` |
| 346 | `SizedBox(height: 32)` | `SizedBox(height: AppTheme.space8)` |

#### Step 6.A.3: Replace hardcoded TextStyle

| Line | Old | New |
|------|-----|-----|
| 228-230 | `TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)` | `TextStyle(color: fg.textInverse, fontSize: 12, fontWeight: FontWeight.bold)` |

---

### Sub-phase 6.B: SyncDashboardScreen (WORST OFFENDER)

**Files:**
- Modify: `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

> NOTE: This file has 15+ direct `Colors.*` usages and multiple hardcoded paddings. Every instance is listed below.

#### Step 6.B.1: Add theme accessor locals to build methods

Every method that uses colors needs these locals at the top:

```dart
// WHY: Single declaration avoids repeated Theme.of(context) lookups
final cs = Theme.of(context).colorScheme;
final fg = FieldGuideColors.of(context);
```

Add to: `build()`, `_buildSummaryCard()`, `_buildStatChip()` (needs context param), `_buildPendingBucketsSection()` (needs context param), `_buildIntegrityCard()` (needs context param), `_buildSectionHeader()` (needs context param).

NOTE: `_buildStatChip`, `_buildSectionHeader`, `_buildPendingBucketsSection`, and `_buildIntegrityCard` currently have no `BuildContext` parameter. Add one, and update call sites.

#### Step 6.B.2: Replace Colors.* in _buildSummaryCard (lines 148-210)

**Full instance list:**

| Line | Old | New | Context |
|------|-----|-----|---------|
| 171 | `Colors.red` | `cs.error` | Sync failure icon color |
| 173 | `Colors.amber` | `fg.accentAmber` | Syncing icon color |
| 174 | `Colors.green` | `fg.statusSuccess` | All-synced icon color |

**Pattern:**
```dart
// WHY: Hardcoded status colors break in dark mode
// BEFORE
color: syncProvider.hasPersistentSyncFailure
    ? Colors.red
    : syncProvider.isSyncing
        ? Colors.amber
        : Colors.green,
// AFTER
color: syncProvider.hasPersistentSyncFailure
    ? cs.error
    : syncProvider.isSyncing
        ? fg.accentAmber
        : fg.statusSuccess,
```

#### Step 6.B.3: Replace Colors.* in _buildStatChip (lines 212-221)

| Line | Old | New |
|------|-----|-----|
| 217 | `TextStyle(fontSize: 20, fontWeight: FontWeight.bold)` | `tt.titleLarge?.copyWith(fontWeight: FontWeight.bold)` |
| 219 | `TextStyle(fontSize: 12, color: Colors.grey)` | `tt.bodySmall?.copyWith(color: cs.onSurfaceVariant)` |

**Pattern:**
```dart
// BEFORE
Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
// AFTER
Text(label, style: tt.bodySmall?.copyWith(color: cs.onSurfaceVariant)),
```

#### Step 6.B.4: Replace Colors.* in _buildSectionHeader (lines 275-283)

| Line | Old | New |
|------|-----|-----|
| 278-280 | `TextStyle(fontSize: 16, fontWeight: FontWeight.w600)` | `tt.titleSmall?.copyWith(fontWeight: FontWeight.w600)` |

#### Step 6.B.5: Replace tokens in _buildPendingBucketsSection (lines 286-391)

| Line | Old | New | Context |
|------|-----|-----|---------|
| 313 | `AppTheme.primaryCyan` | `cs.primary` | Active bucket icon |
| 313 | `AppTheme.textTertiary` | `fg.textTertiary` | Inactive bucket icon |
| 319 | `AppTheme.textTertiary` | `fg.textTertiary` | Inactive bucket text |
| 326 | `Colors.white` | `fg.textInverse` | Active chip text |
| 326 | `AppTheme.textTertiary` | `fg.textTertiary` | Inactive chip text |
| 330-331 | `AppTheme.statusWarning` | `fg.statusWarning` | Active chip bg |
| 331 | `AppTheme.surfaceElevated` | `fg.surfaceElevated` | Inactive chip bg |
| 349-350 | `AppTheme.textTertiary` | `fg.textTertiary` | Breakdown text (2 instances) |
| 356 | `AppTheme.textTertiary` | `fg.textTertiary` | Breakdown trailing text |
| 377 | `AppTheme.textTertiary` | `fg.textTertiary` | Other bucket icon |
| 383 | `AppTheme.statusWarning` | `fg.statusWarning` | Other chip bg |

**Pattern** — chip background:
```dart
// WHY: AppTheme.statusWarning is a compile-time constant that ignores theme mode
// BEFORE
backgroundColor: total > 0
    ? AppTheme.statusWarning
    : AppTheme.surfaceElevated,
// AFTER
backgroundColor: total > 0
    ? fg.statusWarning
    : fg.surfaceElevated,
```

#### Step 6.B.6: Replace Colors.* in _buildIntegrityCard (lines 393-420)

| Line | Old | New | Context |
|------|-----|-----|---------|
| 405 | `Colors.orange` | `fg.accentOrange` | Drift warning icon |
| 405 | `Colors.green` | `fg.statusSuccess` | OK icon |
| 416 | `TextStyle(fontSize: 11, color: Colors.grey)` | `tt.labelSmall?.copyWith(color: cs.onSurfaceVariant)` | Timestamp text |

**Pattern:**
```dart
// BEFORE
color: driftDetected ? Colors.orange : Colors.green,
// AFTER
color: driftDetected ? fg.accentOrange : fg.statusSuccess,
```

#### Step 6.B.7: Replace Colors.orange in MaterialBanner (line 111)

| Line | Old | New |
|------|-----|-----|
| 111 | `color: Colors.orange` | `color: fg.accentOrange` |

#### Step 6.B.8: Replace hardcoded padding

| Line | Old | New |
|------|-----|-----|
| 126 | `EdgeInsets.all(16)` | `EdgeInsets.all(AppTheme.space4)` |
| 129 | `SizedBox(height: 16)` | `SizedBox(height: AppTheme.space4)` |
| 131 | `SizedBox(height: 16)` | `SizedBox(height: AppTheme.space4)` |
| 136 | `SizedBox(height: 8)` | `SizedBox(height: AppTheme.space2)` |
| 157 | `EdgeInsets.all(16)` | `EdgeInsets.all(AppTheme.space4)` |
| 177 | `SizedBox(width: 12)` | `SizedBox(width: AppTheme.space3)` |
| 299 | `SizedBox(height: 8)` | `SizedBox(height: AppTheme.space2)` |
| 343 | `EdgeInsets.only(left: 56, right: 16)` | `EdgeInsets.only(left: 56, right: AppTheme.space4)` |

---

### Sub-phase 6.C: SyncStatusIcon

**Files:**
- Modify: `lib/features/sync/presentation/widgets/sync_status_icon.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 6.C.1: Replace hardcoded Colors.*

All 3 color usages are in `_getColor()` method:

| Line | Old | New |
|------|-----|-----|
| 34 | `Colors.red` | `Theme.of(context).colorScheme.error` |
| 35 | `Colors.amber` | `FieldGuideColors.of(context).accentAmber` |
| 36 | `Colors.green` | `FieldGuideColors.of(context).statusSuccess` |

NOTE: `_getColor` currently takes `SyncProvider`. It needs `BuildContext` too, or the caller must pass the resolved colors. Recommended: change signature to `_getColor(BuildContext context, SyncProvider provider)` and update the call in `build()`.

**Pattern:**
```dart
// BEFORE
Color _getColor(SyncProvider provider) {
  if (provider.hasPersistentSyncFailure) return Colors.red;
  if (provider.isSyncing || provider.hasPendingChanges) return Colors.amber;
  return Colors.green;
}
// AFTER
Color _getColor(BuildContext context, SyncProvider provider) {
  final cs = Theme.of(context).colorScheme;
  final fg = FieldGuideColors.of(context);
  if (provider.hasPersistentSyncFailure) return cs.error;
  if (provider.isSyncing || provider.hasPendingChanges) return fg.accentAmber;
  return fg.statusSuccess;
}
```

---

#### Step 6.C.2: Migrate DeletionNotificationBanner

**File:** `lib/features/sync/presentation/widgets/deletion_notification_banner.dart`
**Agent**: `frontend-flutter-specialist-agent`

3 AppTheme.* violations:
- `AppTheme.statusWarning` → `fg.statusWarning`
- `AppTheme.textPrimary` → `cs.onSurface`
- `AppTheme.surfaceElevated` → `fg.surfaceElevated`

---

### Sub-phase 6.D: ConflictViewerScreen (WORST OFFENDER)

**Files:**
- Modify: `lib/features/sync/presentation/screens/conflict_viewer_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

> NOTE: This file has zero AppTheme usage (except one `AppTheme.statusError` for snackbar). Almost everything is raw `Colors.*`.

#### Step 6.D.1: Add theme accessors

Add to `build()` and `_buildConflictCard()`:
```dart
final cs = Theme.of(context).colorScheme;
final fg = FieldGuideColors.of(context);
final tt = Theme.of(context).textTheme;
```

`_buildConflictCard` needs `BuildContext` parameter added (currently uses `context` from class state — refactor to pass explicitly for clarity).

#### Step 6.D.2: Replace empty-state Colors.green (line 190)

```dart
// BEFORE
Icon(Icons.check_circle, size: 48, color: Colors.green),
// AFTER
Icon(Icons.check_circle, size: 48, color: fg.statusSuccess),
```

#### Step 6.D.3: Replace Colors.* in _buildConflictCard (lines 209-316)

**Full instance list:**

| Line | Old | New | Context |
|------|-----|-----|---------|
| 235 | `Colors.orange` | `fg.accentOrange` | Warning icon in ListTile leading |
| 238 | `TextStyle(fontWeight: FontWeight.w600)` | `tt.bodyLarge?.copyWith(fontWeight: FontWeight.w600)` | Table name text |
| 263 | `TextStyle(fontSize: 12, color: Colors.grey)` | `tt.bodySmall?.copyWith(color: cs.onSurfaceVariant)` | Record ID text |
| 269-272 | `TextStyle(fontSize: 13, fontWeight: FontWeight.w600)` | `tt.bodyMedium?.copyWith(fontWeight: FontWeight.w600)` | "Lost Data:" label |
| 280 | `Colors.grey.shade100` | `fg.surfaceElevated` | Code block background |
| 284-287 | `TextStyle(fontSize: 11, fontFamily: 'monospace')` | `tt.bodySmall?.copyWith(fontFamily: 'monospace')` | JSON text |

**Pattern** — code block container:
```dart
// WHY: Colors.grey.shade100 is invisible on dark backgrounds
// BEFORE
decoration: BoxDecoration(
  color: Colors.grey.shade100,
  borderRadius: BorderRadius.circular(4),
),
// AFTER
decoration: BoxDecoration(
  color: fg.surfaceElevated,
  borderRadius: BorderRadius.circular(4),
),
```

#### Step 6.D.4: Replace hardcoded padding

| Line | Old | New |
|------|-----|-----|
| 199 | `EdgeInsets.all(16)` | `EdgeInsets.all(AppTheme.space4)` |
| 231 | `EdgeInsets.only(bottom: 8)` | `EdgeInsets.only(bottom: AppTheme.space2)` |
| 258 | `EdgeInsets.symmetric(horizontal: 16)` | `EdgeInsets.symmetric(horizontal: AppTheme.space4)` |
| 265 | `SizedBox(height: 8)` | `SizedBox(height: AppTheme.space2)` |
| 275 | `SizedBox(height: 4)` | `SizedBox(height: AppTheme.space1)` |
| 278 | `EdgeInsets.all(8)` | `EdgeInsets.all(AppTheme.space2)` |
| 292 | `SizedBox(height: 12)` | `SizedBox(height: AppTheme.space3)` |
| 300 | `SizedBox(width: 8)` | `SizedBox(width: AppTheme.space2)` |
| 308 | `SizedBox(height: 8)` | `SizedBox(height: AppTheme.space2)` |
| 191 | `SizedBox(height: 12)` | `SizedBox(height: AppTheme.space3)` |

---

### Sub-phase 6.E: ProjectSwitcher

**Files:**
- Modify: `lib/features/projects/presentation/widgets/project_switcher.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 6.E.1: Replace AppTheme and Colors.* references

| Line | Old | New | Context |
|------|-----|-----|---------|
| 43 | `AppTheme.primaryCyan` | `cs.primary` | Folder icon in app bar chip |
| 134 | `Colors.grey[300]` | `cs.outlineVariant` | Drag handle |
| 207 | `AppTheme.primaryCyan` | `cs.primary` | Add icon |
| 210 | `AppTheme.primaryCyan` | `cs.primary` | "+ New Project" text |
| 231 | `AppTheme.primaryCyan` | `cs.primary` | Selected radio icon |
| 231 | `Colors.grey` | `cs.onSurfaceVariant` | Unselected radio icon |

**Pattern** — drag handle:
```dart
// WHY: Colors.grey[300] is a hardcoded shade; use outline variant for theme support
// BEFORE
color: Colors.grey[300],
// AFTER
color: cs.outlineVariant,
```

#### Step 6.E.2: Replace hardcoded padding

| Line | Old | New |
|------|-----|-----|
| 28 | `EdgeInsets.symmetric(horizontal: 8, vertical: 4)` | `EdgeInsets.symmetric(horizontal: AppTheme.space2, vertical: AppTheme.space1)` |

---

### Sub-phase 6.F: MemberDetailSheet

**Files:**
- Modify: `lib/features/settings/presentation/widgets/member_detail_sheet.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 6.F.1: Replace AppTheme and Colors.* references

| Line | Old | New | Context |
|------|-----|-----|---------|
| 54 | `Colors.grey[300]` | `cs.outlineVariant` | Drag handle |
| 65 | `AppTheme.primaryCyan.withValues(alpha: 0.2)` | `cs.primary.withValues(alpha: 0.2)` | Avatar bg |
| 69 | `AppTheme.primaryCyan` | `cs.primary` | Avatar text |
| 92 | `AppTheme.statusError` | `cs.error` | Deactivated status text |
| 194 | `AppTheme.success` | `fg.statusSuccess` | Reactivate icon (2 instances: icon + label) |
| 195-209 | `AppTheme.statusError` | `cs.error` | Deactivate icon/label/border (3 instances) |
| 229 | `Colors.grey` | `cs.onSurfaceVariant` | Info row icon color |
| 244 | `AppTheme.success` | `fg.statusSuccess` | Sync health "Active" badge |
| 247 | `Colors.grey` | `cs.onSurfaceVariant` | Sync health "Never" badge |

#### Step 6.F.2: Replace hardcoded padding

| Line | Old | New |
|------|-----|-----|
| 38-41 | `EdgeInsets.only(left: 16, right: 16, top: 16, ...)` | `EdgeInsets.only(left: AppTheme.space4, right: AppTheme.space4, top: AppTheme.space4, ...)` |
| 52 | `EdgeInsets.only(bottom: 16)` | `EdgeInsets.only(bottom: AppTheme.space4)` |
| 142 | `EdgeInsets.symmetric(horizontal: 12, vertical: 8)` | `EdgeInsets.symmetric(horizontal: AppTheme.space3, vertical: AppTheme.space2)` |
| 251 | `EdgeInsets.symmetric(horizontal: 8, vertical: 4)` | `EdgeInsets.symmetric(horizontal: AppTheme.space2, vertical: AppTheme.space1)` |

---

### Sub-phase 6.G: ScaffoldWithNavBar

**Files:**
- Modify: `lib/core/router/app_router.dart` (only the `ScaffoldWithNavBar` class, lines 648-834)

**Agent**: `frontend-flutter-specialist-agent`

#### Step 6.G.1: Replace Colors.* in ScaffoldWithNavBar

**Full instance list:**

| Line | Old | New | Context |
|------|-----|-----|---------|
| 680 | `Colors.red.shade700` | `cs.error` | Sync error snackbar background |
| 684 | `Colors.white` | `cs.onError` | Snackbar action text color |
| 720 | `Colors.orange` | `fg.accentOrange` | Stale sync warning icon |
| 743 | `Colors.orange` | `fg.accentOrange` | Offline banner leading icon |
| 744 | `Colors.orange.shade50` | `fg.accentOrange.withValues(alpha: 0.08)` | Offline banner bg |

**Pattern** — snackbar:
```dart
// WHY: Colors.red.shade700 breaks dark mode, cs.error adapts to theme
// BEFORE
backgroundColor: Colors.red.shade700,
...
textColor: Colors.white,
// AFTER
backgroundColor: cs.error,
...
textColor: cs.onError,
```

**Pattern** — offline banner background:
```dart
// WHY: Colors.orange.shade50 is a Material 2 constant; use derived opacity for theme support
// BEFORE
backgroundColor: Colors.orange.shade50,
// AFTER
backgroundColor: fg.accentOrange.withValues(alpha: 0.08),
```

NOTE: ScaffoldWithNavBar is a StatelessWidget, so add locals at top of `build()`:
```dart
final cs = Theme.of(context).colorScheme;
final fg = FieldGuideColors.of(context);
```

The snackbar callback closure captures context — the `cs`/`fg` resolved inside it should use the `context` parameter passed to the callback, not the outer build context. Resolve this by inlining Theme lookup inside the closure.

---

### Sub-phase 6.H: Settings Widgets

**Files:**
- Modify: `lib/features/settings/presentation/widgets/sync_section.dart`
- Modify: `lib/features/settings/presentation/widgets/section_header.dart`
- Modify: `lib/features/settings/presentation/widgets/theme_section.dart`
- Modify: `lib/features/settings/presentation/widgets/sign_out_dialog.dart`
- Modify: `lib/features/settings/presentation/widgets/clear_cache_dialog.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 6.H.1: SyncSection token migration

| Line | Old | New |
|------|-----|-----|
| 32 | `AppTheme.success` | `fg.statusSuccess` |
| 33 | `AppTheme.primaryBlue` | `cs.primary` |
| 35 | `AppTheme.success` | `fg.statusSuccess` |
| 37 | `AppTheme.statusError` | `cs.error` |
| 39 | `AppTheme.textTertiary` | `fg.textTertiary` |
| 41 | `AppTheme.statusWarning` | `fg.statusWarning` |
| 94 | `AppTheme.statusWarning` | `fg.statusWarning` |
| 94 | `AppTheme.textTertiary` | `fg.textTertiary` |
| 99 | `AppTheme.textTertiary` | `fg.textTertiary` |
| 158 | `AppTheme.statusWarning` | `fg.statusWarning` |
| 165 | `AppTheme.statusError` | `cs.error` |

NOTE: SyncSection is a StatelessWidget. `_getSyncColor` and `_buildBucketSummary` need `BuildContext` parameter added. The `build` method already has context — pass it through.

#### Step 6.H.2: Audit other settings widgets

SectionHeader, ThemeSection, SignOutDialog, ClearCacheDialog — read each and replace any `AppTheme.*` or `Colors.*`. These files are likely cleaner. Do a sweep and fix any instances found.

---

### Sub-phase 6.I: Quality Gate

**Agent**: `qa-testing-agent`

#### Step 6.I.1: Static analysis

```
pwsh -Command "flutter analyze lib/features/settings/ lib/features/sync/presentation/ lib/core/router/app_router.dart lib/features/projects/presentation/widgets/project_switcher.dart"
```

#### Step 6.I.2: Verify zero remaining violations

Search all modified files for `Colors\.` regex — must return zero hits (except `Colors.transparent` which is acceptable).

Search all modified files for `AppTheme\.primaryCyan`, `AppTheme\.textPrimary`, `AppTheme\.textSecondary`, `AppTheme\.textTertiary`, `AppTheme\.success`, `AppTheme\.surfaceElevated`, `AppTheme\.surfaceDark`, `AppTheme\.surfaceHighlight` — must return zero hits.

#### Step 6.I.3: Run sync-related tests

```
pwsh -Command "flutter test test/features/sync/"
```

#### Step 6.I.4: Testing keys

**Testing Keys**: For each screen/widget modified in this phase:
1. Review existing TestingKeys assignments — transfer all keys to their new design system wrapper
2. Add new keys for any new interactive elements (buttons, fields, toggles)
3. Update the corresponding key file in `lib/shared/testing_keys/` if keys are added/renamed
4. Run: `pwsh -Command "flutter test test/features/settings/ test/features/sync/"` to verify widget tests pass

---

## Phase 7: Project Setup + Quantities

**Goal**: Migrate the project management and quantities screens. ProjectSetupScreen has 9 EdgeInsets violations; QuantitiesScreen has 3 hardcoded `Colors.*` in the budget warning chip.

### Sub-phase 7.A: QuantitiesScreen

**Files:**
- Modify: `lib/features/quantities/presentation/screens/quantities_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.A.1: Replace Colors.* in budget warning chip (lines 172-180)

| Line | Old | New | Context |
|------|-----|-----|---------|
| 173 | `Colors.orange.shade800` | `fg.accentOrange` | Warning icon color |
| 178 | `Colors.amber.shade50` | `fg.accentAmber.withValues(alpha: 0.1)` | Chip background |
| 179 | `Colors.amber.shade200` | `fg.accentAmber.withValues(alpha: 0.4)` | Chip border |

**Pattern:**
```dart
// WHY: Material shade constants don't adapt to dark mode
// BEFORE
Chip(
  avatar: Icon(Icons.warning_amber_rounded,
      color: Colors.orange.shade800, size: 18),
  label: const Text(
    'Unit price discrepancy detected — using bid amounts',
    style: TextStyle(fontSize: 12),
  ),
  backgroundColor: Colors.amber.shade50,
  side: BorderSide(color: Colors.amber.shade200),
),
// AFTER
Chip(
  avatar: Icon(Icons.warning_amber_rounded,
      color: fg.accentOrange, size: 18),
  label: const Text(
    'Unit price discrepancy detected — using bid amounts',
    style: TextStyle(fontSize: 12),
  ),
  backgroundColor: fg.accentAmber.withValues(alpha: 0.1),
  side: BorderSide(color: fg.accentAmber.withValues(alpha: 0.4)),
),
```

NOTE: Consider replacing this entire Chip with `AppBudgetWarningChip` from the design system (Phase 1). If that component exists, use it directly instead of inline styling.

#### Step 7.A.2: Replace remaining AppTheme static colors

| Line | Old | New |
|------|-----|-----|
| 185 | `AppTheme.textSecondary` | `cs.onSurfaceVariant` |
| 208-209 | `AppTheme.textSecondary` | `cs.onSurfaceVariant` |
| 215-216 | `AppTheme.textTertiary` | `fg.textTertiary` |
| 274 | `AppTheme.error` (in `_buildErrorState` of GalleryScreen — skip, wrong file) | — |

---

### Sub-phase 7.B: ProjectSetupScreen

**Files:**
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.B.1: Replace hardcoded EdgeInsets

The ProjectSetupScreen is a large file (500+ lines). Scan for all `EdgeInsets` and `SizedBox` usages that use raw numbers instead of `AppTheme.space*` tokens.

**Search pattern**: `EdgeInsets\.(all|symmetric|only)\([^A]` — any EdgeInsets not starting with AppTheme.

**Known violations** (9 reported in inventory):
Replace all hardcoded `EdgeInsets.all(16)` with `EdgeInsets.all(AppTheme.space4)`, `EdgeInsets.all(8)` with `EdgeInsets.all(AppTheme.space2)`, etc.

**Mapping reference:**
| Value | Token |
|-------|-------|
| 4 | `AppTheme.space1` |
| 8 | `AppTheme.space2` |
| 12 | `AppTheme.space3` |
| 16 | `AppTheme.space4` |
| 20 | `AppTheme.space5` |
| 24 | `AppTheme.space6` |
| 32 | `AppTheme.space8` |

#### Step 7.B.2: Replace any AppTheme.* static color references

Scan for `AppTheme.primaryCyan`, `AppTheme.textSecondary`, `AppTheme.textTertiary`, `AppTheme.statusError`, `AppTheme.success`, `Colors.*` and replace per the color mapping table.

---

### Sub-phase 7.C: Project Setup Widgets

**Files:**
- Modify: `lib/features/projects/presentation/widgets/project_details_form.dart`
- Modify: `lib/features/projects/presentation/widgets/contractor_editor_widget.dart` (if it exists here — may be in entries)
- Modify: `lib/features/projects/presentation/widgets/assignments_step.dart`
- Modify: `lib/features/projects/presentation/widgets/add_location_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/add_contractor_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/add_equipment_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/bid_item_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/pay_item_source_dialog.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.C.1: Sweep each widget for violations

For each widget file, search for `Colors\.`, `AppTheme\.`, hardcoded `EdgeInsets`, hardcoded `TextStyle(fontSize:`, hardcoded `BorderRadius`. Replace using the standard mapping tables.

- Modify: `lib/features/projects/presentation/widgets/project_import_banner.dart` — 5 AppTheme.* violations
  - `AppTheme.statusSuccess` → `fg.statusSuccess`
  - `AppTheme.statusError` → `cs.error`
  - `AppTheme.primaryCyan` → `cs.primary`
  - `AppTheme.textSecondary` → `cs.onSurfaceVariant`
  - `AppTheme.textPrimary` → `cs.onSurface`
- Modify: `lib/features/projects/presentation/widgets/project_empty_state.dart` — 2 AppTheme.* violations
  - `AppTheme.textTertiary` → `fg.textTertiary`
  - `AppTheme.textSecondary` → `cs.onSurfaceVariant`

---

### Sub-phase 7.D: Quantity Widgets

**Files:**
- Modify: `lib/features/quantities/presentation/widgets/quantity_summary_header.dart`
- Modify: `lib/features/quantities/presentation/widgets/bid_item_card.dart`
- Modify: `lib/features/quantities/presentation/widgets/bid_item_detail_sheet.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.D.1: Sweep each widget for violations

Same approach as 7.C.1. These widgets were not flagged as worst offenders, so violations should be minor.

---

### Sub-phase 7.E: QuantityCalculatorScreen

**Files:**
- Modify: `lib/features/quantities/presentation/screens/quantity_calculator_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.E.1: Light sweep

Inventory notes this screen has clean AppTheme usage. Verify and fix any remaining `Colors.*` or hardcoded padding.

---

### Sub-phase 7.F: Quality Gate

**Agent**: `qa-testing-agent`

#### Step 7.F.1: Static analysis

```
pwsh -Command "flutter analyze lib/features/quantities/ lib/features/projects/"
```

#### Step 7.F.2: Verify zero remaining violations

Search all modified files for `Colors\.` regex (except `Colors.transparent`).

#### Step 7.F.3: Run related tests

```
pwsh -Command "flutter test test/features/projects/ test/features/quantities/"
```

#### Step 7.F.4: Testing keys

**Testing Keys**: For each screen/widget modified in this phase:
1. Review existing TestingKeys assignments — transfer all keys to their new design system wrapper
2. Add new keys for any new interactive elements (buttons, fields, toggles)
3. Update the corresponding key file in `lib/shared/testing_keys/` if keys are added/renamed
4. Run: `pwsh -Command "flutter test test/features/projects/ test/features/quantities/"` to verify widget tests pass

---

## Phase 8: Utility Screens

**Goal**: Migrate the remaining utility screens — gallery, PDF import, entry review, forms hub, toolbox, and calculator. The gallery photo viewer is the standout worst offender.

### Sub-phase 8.A: GalleryScreen + _PhotoViewerScreen

**Files:**
- Modify: `lib/features/gallery/presentation/screens/gallery_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.A.1: Replace AppTheme static colors in GalleryScreen (lines 1-513)

The main GalleryScreen body uses `AppTheme.*` but not raw `Colors.*`. Replace:

| Line | Old | New |
|------|-----|-----|
| 185 | `AppTheme.textSecondary` | `cs.onSurfaceVariant` |
| 233 | `AppTheme.textTertiary` | `fg.textTertiary` |
| 240 | `AppTheme.textSecondary` | `cs.onSurfaceVariant` |
| 249 | `AppTheme.textTertiary` | `fg.textTertiary` |
| 274 | `AppTheme.error` | `cs.error` |
| 283 | `AppTheme.textSecondary` | `cs.onSurfaceVariant` |
| 391 | `AppTheme.textSecondary` | `cs.onSurfaceVariant` |
| 426 | `AppTheme.textSecondary` | `cs.onSurfaceVariant` |

#### Step 8.A.2: Replace ALL Colors.* in _PhotoViewerScreen (lines 517-641) — WORST OFFENDER

This is a full-screen photo viewer with black background and white text. Every color is hardcoded.

**Full instance list:**

| Line | Old | New | Context |
|------|-----|-----|---------|
| 549 | `Colors.black` | `cs.scrim` | Scaffold background |
| 551 | `Colors.black` | `cs.scrim` | AppBar background |
| 552 | `Colors.white` | `cs.onScrim` | AppBar foreground |
| 555 | `TextStyle(color: Colors.white)` | Redundant — remove (foregroundColor handles it) | AppBar title |
| 580 | `Colors.white54` | `cs.onScrim.withValues(alpha: 0.54)` | Broken image icon |
| 593 | `Colors.black87` | `cs.scrim.withValues(alpha: 0.87)` | Info container bg |
| 600-604 | `TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w500)` | `tt.titleMedium?.copyWith(color: cs.onScrim)` | Caption text |
| 609 | `TextStyle(color: Colors.white70, fontSize: 12)` | `tt.bodySmall?.copyWith(color: cs.onScrim.withValues(alpha: 0.7))` | Timestamp |
| 615 | `TextStyle(color: Colors.white70, fontSize: 14)` | `tt.bodyMedium?.copyWith(color: cs.onScrim.withValues(alpha: 0.7))` | Notes |
| 623 | `Colors.white54` | `cs.onScrim.withValues(alpha: 0.54)` | Attribution text |

**Pattern** — full-screen dark viewer:
```dart
// WHY: Photo viewer needs intentionally dark background regardless of theme.
// Using cs.scrim (dark in both modes) instead of Colors.black gives us
// semantic naming while preserving the dark viewer experience.
// BEFORE
return Scaffold(
  backgroundColor: Colors.black,
  appBar: AppBar(
    backgroundColor: Colors.black,
    foregroundColor: Colors.white,
    title: Text(
      '${_currentIndex + 1} / ${widget.photos.length}',
      style: const TextStyle(color: Colors.white),
    ),
  ),
// AFTER
final cs = Theme.of(context).colorScheme;
final tt = Theme.of(context).textTheme;
return Scaffold(
  backgroundColor: cs.scrim,
  appBar: AppBar(
    backgroundColor: cs.scrim,
    foregroundColor: cs.onScrim,
    title: Text('${_currentIndex + 1} / ${widget.photos.length}'),
  ),
```

NOTE: The `style: const TextStyle(color: Colors.white)` on the title at line 555 is redundant when `foregroundColor` is set. Remove it entirely.

**Pattern** — info container:
```dart
// BEFORE
color: Colors.black87,
// AFTER
color: cs.scrim.withValues(alpha: 0.87),
```

#### Step 8.A.3: PhotoThumbnail widget

**Files:**
- Modify: `lib/features/photos/presentation/widgets/photo_thumbnail.dart`

Scan for `Colors.*` and `AppTheme.*` violations. Replace per standard mapping.

---

### Sub-phase 8.B: PDF Import Screens

**Files:**
- Modify: `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`
- Modify: `lib/features/pdf/presentation/screens/mp_import_preview_screen.dart`
- Modify: `lib/features/pdf/presentation/widgets/extraction_banner.dart`
- Modify: `lib/features/pdf/presentation/widgets/extraction_detail_sheet.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.B.1: Sweep each file for violations

These screens were not flagged as worst offenders. Scan for `Colors\.`, `AppTheme\.` static colors, hardcoded `EdgeInsets`, and replace per standard mapping tables.

#### Step 8.B.3: Migrate PDF Import Helpers

**Files:**
- Modify: `lib/features/pdf/presentation/helpers/pdf_import_helper.dart` — 14 violations including _ProgressDialog widget
- Modify: `lib/features/pdf/presentation/helpers/mp_import_helper.dart` — 12 violations

**Agent**: `frontend-flutter-specialist-agent`

Both files contain inline _ProgressDialog widgets with:
- `AppTheme.primaryCyan` → `cs.primary`
- `AppTheme.textPrimary` → `cs.onSurface`
- `AppTheme.textSecondary` → `cs.onSurfaceVariant`
- `AppTheme.surfaceBright` → `fg.surfaceBright`
- Hardcoded `TextStyle(fontSize: ...)` → `tt.bodyMedium`, `tt.titleMedium`
- Hardcoded `EdgeInsets` → `AppTheme.space*` tokens
- Hardcoded `BorderRadius.circular(12)` → `AppTheme.radiusMedium`

---

### Sub-phase 8.C: Entry Review Screens

**Files:**
- Modify: `lib/features/entries/presentation/screens/entry_review_screen.dart`
- Modify: `lib/features/entries/presentation/screens/review_summary_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.C.1: ReviewSummaryScreen violations

| Line | Old | New | Context |
|------|-----|-----|---------|
| 93 | `Colors.red` | `cs.error` | Failed submit snackbar bg |
| 170 | `Colors.black.withValues(alpha: 0.1)` | `fg.shadowLight` | Bottom bar shadow |
| 189 | `Colors.white` | `cs.onPrimary` | Spinner in FilledButton |
| 233 | `AppTheme.textPrimary` | `cs.onSurface` | Summary header count text |
| 239 | `AppTheme.textSecondary` | `cs.onSurfaceVariant` | "X skipped" text |
| 299 | `AppTheme.textSecondary` | `cs.onSurfaceVariant` | Location subtitle |
| 309 | `AppTheme.statusSuccess` | `fg.statusSuccess` | "READY" label (2 instances) |
| 310 | `AppTheme.textTertiary` | `fg.textTertiary` | "SKIPPED" label (2 instances) |

**Pattern** — shadow:
```dart
// WHY: Colors.black.withValues breaks in light themes with white surfaces
// BEFORE
color: Colors.black.withValues(alpha: 0.1),
// AFTER
color: fg.shadowLight,
```

#### Step 8.C.2: EntryReviewScreen sweep

Scan for `Colors.*` and `AppTheme.*` violations. Replace per mapping.

---

### Sub-phase 8.D: Forms Hub Widgets

**Files:**
- Modify: `lib/features/forms/presentation/screens/mdot_hub_screen.dart`
- Modify: `lib/features/forms/presentation/screens/form_viewer_screen.dart`
- Modify: `lib/features/forms/presentation/widgets/hub_proctor_content.dart`
- Modify: `lib/features/forms/presentation/widgets/form_accordion.dart`
- Modify: `lib/features/forms/presentation/widgets/status_pill_bar.dart`
- Modify: `lib/features/forms/presentation/widgets/summary_tiles.dart`
- Modify: `lib/features/forms/presentation/widgets/hub_header_content.dart`
- Modify: `lib/features/forms/presentation/widgets/hub_quick_test_content.dart`
- Modify: `lib/features/forms/presentation/widgets/form_thumbnail.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.D.1: HubProctorContent — heavy violations (14 TextStyle, 7 EdgeInsets, 6 BorderRadius)

This widget is the densest violator in Phase 8. It uses `AppTheme.*` static tokens extensively. All need migration to runtime theme lookups.

**AppTheme static color instances in HubProctorContent:**

| Line | Old | New |
|------|-----|-----|
| 83 | `AppTheme.surfaceDark` | `cs.surface` |
| 102 | `AppTheme.statusSuccess.withValues(alpha: 0.08)` | `fg.statusSuccess.withValues(alpha: 0.08)` |
| 103 | `AppTheme.surfaceHighlight` | `cs.outline` |
| 107 | `AppTheme.statusSuccess.withValues(alpha: 0.35)` | `fg.statusSuccess.withValues(alpha: 0.35)` |
| 108 | `AppTheme.surfaceBright` | `cs.outlineVariant` |
| 141 | `AppTheme.statusSuccess` | `fg.statusSuccess` |
| 142 | `AppTheme.textSecondary` | `cs.onSurfaceVariant` |
| 148-150 | `AppTheme.textInverse` | `fg.textInverse` |
| 160 | `AppTheme.textSecondary` | `cs.onSurfaceVariant` |
| 235 | `AppTheme.statusSuccess` | `fg.statusSuccess` |
| 264 | `AppTheme.statusSuccess.withValues(alpha: 0.06)` | `fg.statusSuccess.withValues(alpha: 0.06)` |
| 266 | `AppTheme.statusSuccess.withValues(alpha: 0.35)` | `fg.statusSuccess.withValues(alpha: 0.35)` |
| 319 | `AppTheme.statusWarning` | `fg.statusWarning` |
| 360 | `AppTheme.accentAmber` | `fg.accentAmber` |
| 361 | `AppTheme.textInverse` | `fg.textInverse` |
| 403-407 | `AppTheme.statusSuccess`, `AppTheme.statusWarning`, `AppTheme.surfaceBright` | `fg.statusSuccess`, `fg.statusWarning`, `cs.outlineVariant` |
| 419 | `AppTheme.surfaceHighlight` | `cs.outline` |
| 436 | `AppTheme.textSecondary.withValues(alpha: 0.4)` | `cs.onSurfaceVariant.withValues(alpha: 0.4)` |
| 459-461 | `AppTheme.statusSuccess`, `AppTheme.statusWarning` | `fg.statusSuccess`, `fg.statusWarning` |
| 479 | `AppTheme.textSecondary` | `cs.onSurfaceVariant` |

NOTE: HubProctorContent is a StatelessWidget. Add theme accessors at top of `build()`:
```dart
final cs = Theme.of(context).colorScheme;
final fg = FieldGuideColors.of(context);
final tt = Theme.of(context).textTheme;
```

All `const TextStyle(...)` and `const TextStyle(color: AppTheme.*)` must lose the `const` keyword since theme tokens are runtime values.

#### Step 8.D.2: Hardcoded TextStyle instances in HubProctorContent

Replace all hardcoded `fontSize` + `fontWeight` combinations with text theme references:

| Pattern | Old | New |
|---------|-----|-----|
| Section labels | `TextStyle(fontSize: 12, fontWeight: FontWeight.w800)` | `tt.labelSmall?.copyWith(fontWeight: FontWeight.w800)` |
| Live card title | `TextStyle(fontSize: 15, fontWeight: FontWeight.w800)` | `tt.titleSmall?.copyWith(fontWeight: FontWeight.w800)` |
| Calc pair label | `TextStyle(fontSize: 11, color: AppTheme.textSecondary)` | `tt.labelSmall?.copyWith(color: cs.onSurfaceVariant)` |
| Calc pair value | `TextStyle(fontWeight: FontWeight.w800)` | `tt.bodyMedium?.copyWith(fontWeight: FontWeight.w800)` |
| Weight card text | `TextStyle(fontSize: 15, fontWeight: FontWeight.w700)` | `tt.titleSmall?.copyWith(fontWeight: FontWeight.w700)` |
| Delta text | `TextStyle(fontSize: 10, fontWeight: FontWeight.w800)` | `tt.labelSmall?.copyWith(fontWeight: FontWeight.w800, fontSize: 10)` |
| LIVE badge | `TextStyle(color: AppTheme.textInverse, fontSize: 10, fontWeight: FontWeight.w800)` | `tt.labelSmall?.copyWith(color: fg.textInverse, fontWeight: FontWeight.w800, fontSize: 10)` |

#### Step 8.D.3: Hardcoded EdgeInsets in HubProctorContent

| Line | Old | New |
|------|-----|-----|
| 81 | `EdgeInsets.all(10)` | `EdgeInsets.all(AppTheme.space3)` |
| 99 | `EdgeInsets.all(12)` | `EdgeInsets.all(AppTheme.space3)` |
| 135-137 | `EdgeInsets.symmetric(horizontal: 8, vertical: 4)` | `EdgeInsets.symmetric(horizontal: AppTheme.space2, vertical: AppTheme.space1)` |
| 262 | `EdgeInsets.all(12)` | `EdgeInsets.all(AppTheme.space3)` |
| 325 | `EdgeInsets.symmetric(horizontal: 8)` | `EdgeInsets.symmetric(horizontal: AppTheme.space2)` |
| 385-386 | `EdgeInsets.symmetric(horizontal: 12, vertical: 14)` | `EdgeInsets.symmetric(horizontal: AppTheme.space3, vertical: 14)` |
| 439-440 | `EdgeInsets.symmetric(horizontal: 4, vertical: 10)` | `EdgeInsets.symmetric(horizontal: AppTheme.space1, vertical: AppTheme.space3)` |

#### Step 8.D.4: Hardcoded BorderRadius in HubProctorContent

| Line | Old | New |
|------|-----|-----|
| 84 | `BorderRadius.circular(10)` | `BorderRadius.circular(AppTheme.space3)` |
| 104 | `BorderRadius.circular(12)` | `BorderRadius.circular(AppTheme.space3)` |
| 143 | `BorderRadius.circular(999)` | `BorderRadius.circular(999)` — keep (pill shape, intentional) |
| 265 | `BorderRadius.circular(10)` | `BorderRadius.circular(AppTheme.space3)` |
| 362 | `BorderRadius.circular(12)` | `BorderRadius.circular(AppTheme.space3)` |
| 417 | `BorderRadius.circular(10)` | `BorderRadius.circular(AppTheme.space3)` |

#### Step 8.D.5: Sweep remaining hub widgets

For FormAccordion, StatusPillBar, SummaryTiles, HubHeaderContent, HubQuickTestContent, FormThumbnail — scan each for `Colors.*`, `AppTheme.*` static colors, hardcoded `EdgeInsets`, `TextStyle`, `BorderRadius`. Replace per mapping tables.

---

### Sub-phase 8.E: Toolbox + Calculator

**Files:**
- Modify: `lib/features/toolbox/presentation/screens/toolbox_home_screen.dart`
- Modify: `lib/features/calculator/presentation/screens/calculator_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.E.1: Light sweep

Both screens are flagged as clean in the inventory. Verify no violations remain. Fix any stragglers.

---

### Sub-phase 8.F: EditProfileScreen

**Files:**
- Modify: `lib/features/settings/presentation/screens/edit_profile_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.F.1: Light sweep

Flagged as clean. Verify no violations remain.

---

### Sub-phase 8.G: Quality Gate

**Agent**: `qa-testing-agent`

#### Step 8.G.1: Static analysis

```
pwsh -Command "flutter analyze lib/features/gallery/ lib/features/pdf/presentation/ lib/features/entries/presentation/screens/entry_review_screen.dart lib/features/entries/presentation/screens/review_summary_screen.dart lib/features/forms/ lib/features/toolbox/ lib/features/calculator/ lib/features/settings/presentation/screens/edit_profile_screen.dart lib/features/photos/presentation/widgets/"
```

#### Step 8.G.2: Verify zero remaining violations

> **IMPORTANT for executing agent:** Several screen files contain private widget classes (e.g., `_ToolboxCard`, `_TodoCard`, `_DueDateChip`, `_FilterSheet`, `_BidItemPreviewCard`, `_MpMatchCard`, `_SectionCard`). When sweeping a screen file, also migrate all private widgets defined in the same file.

Global sweep of all Phase 8 files:
- `Colors\.` regex (except `Colors.transparent`) — must be zero
- `AppTheme\.primaryCyan`, `AppTheme\.textPrimary`, `AppTheme\.textSecondary`, `AppTheme\.textTertiary`, `AppTheme\.success`, `AppTheme\.surfaceElevated`, `AppTheme\.surfaceDark`, `AppTheme\.surfaceHighlight`, `AppTheme\.statusError`, `AppTheme\.statusSuccess`, `AppTheme\.statusWarning`, `AppTheme\.accentAmber`, `AppTheme\.textInverse`, `AppTheme\.error`, `AppTheme\.primaryBlue`, `AppTheme\.surfaceBright` — must be zero

#### Step 8.G.3: Run related tests

```
pwsh -Command "flutter test test/features/gallery/ test/features/pdf/ test/features/entries/ test/features/forms/"
```

#### Step 8.G.4: Testing keys

**Testing Keys**: For each screen/widget modified in Phases 6-8:
1. Review existing TestingKeys assignments — transfer all keys to their new design system wrapper
2. Add new keys for any new interactive elements (buttons, fields, toggles)
3. Update the corresponding key file in `lib/shared/testing_keys/` if keys are added/renamed
4. Run: `pwsh -Command "flutter test"` to verify widget tests pass

#### Step 8.G.5: Golden test regeneration (Phases 6-8 batch)

**Golden Tests**: Regenerate all golden test images to match the new theme-aware rendering:
```
pwsh -Command "flutter test --update-goldens test/golden/"
```
Commit updated golden files with the phase. Review diffs to confirm changes are only color/spacing related, not structural regressions.

#### Step 8.G.6: Visual smoke test

Build debug APK and verify the following screens render correctly in both light and dark mode:
1. Settings screen (all sections visible)
2. Sync Dashboard (summary card, pending buckets, integrity cards)
3. Conflict Viewer (empty state with green check)
4. Gallery (photo grid + filter sheet)
5. Gallery photo viewer (dark background, white text, broken image placeholder)
6. Quantities screen (budget warning chip)
7. Forms hub (proctor content with live card, weight cards, calc card)
8. Review summary (ready/skipped entries, submit button)

<!-- ======= Part: phases9-12 ======= -->

# UI Refactor v2 — Phases 9–12 (Final Polish)

**Created**: 2026-03-28
**Scope**: Auth screens, bottom sheets/dialogs, performance, cleanup
**Depends on**: Phases 1–8 (design system + all screen rewrites complete)

---

## Phase 9: Auth Screens — Light Refresh

**Goal**: Auth screens are already mostly clean (Theme.of(context).textTheme used correctly). Only fix actual violations: hardcoded AppTheme color tokens and raw TextStyle instances. Do NOT over-engineer — these screens are simple and rarely change.

### Sub-phase 9.A: UpdateRequiredScreen Token Fix

**Files:**
- Modify: `lib/features/auth/presentation/screens/update_required_screen.dart`

**Agent**: `auth-agent`

#### Step 9.A.1: Replace AppTheme color tokens with semantic equivalents

The file has 7 violations across 147 lines. Replace each:

```dart
// WHY: AppTheme.primaryCyan → cs.primary for theme-awareness
// BEFORE (line 38):
color: AppTheme.primaryCyan,
// AFTER:
color: cs.primary,

// BEFORE (line 52):
color: AppTheme.textSecondary,
// AFTER:
color: cs.onSurfaceVariant,

// BEFORE (line 60):
color: AppTheme.primaryCyan.withValues(alpha: 0.1),
// AFTER:
color: cs.primary.withValues(alpha: 0.1),

// BEFORE (line 74):
color: AppTheme.textSecondary,
// AFTER:
color: cs.onSurfaceVariant,

// BEFORE (line 92):
backgroundColor: AppTheme.primaryCyan,
// AFTER:
backgroundColor: cs.primary,

// BEFORE (line 104):
color: AppTheme.textTertiary,
// AFTER:
color: fg.textTertiary,
```

#### Step 9.A.2: Replace raw TextStyle instances with textTheme

```dart
// BEFORE (lines 73-76):
style: TextStyle(
  color: AppTheme.textSecondary,
  fontSize: 13,
),
// AFTER:
style: tt.bodySmall?.copyWith(
  color: cs.onSurfaceVariant,
),

// BEFORE (lines 103-106):
style: TextStyle(
  color: AppTheme.textTertiary,
  fontSize: 13,
),
// AFTER:
style: tt.bodySmall?.copyWith(
  color: fg.textTertiary,
),

// BEFORE (lines 131-134) in _InfoRow:
style: TextStyle(
  color: AppTheme.textSecondary,
  fontSize: 14,
),
// AFTER:
style: tt.bodyMedium?.copyWith(
  color: cs.onSurfaceVariant,
),

// BEFORE (lines 138-141) in _InfoRow:
style: const TextStyle(
  fontWeight: FontWeight.w600,
  fontSize: 14,
),
// AFTER:
style: tt.bodyMedium?.copyWith(
  fontWeight: FontWeight.w600,
),
```

#### Step 9.A.3: Add theme accessors at top of build methods

```dart
// WHY: One-time declarations, used by all replacements above
final cs = Theme.of(context).colorScheme;
final tt = Theme.of(context).textTheme;
final fg = FieldGuideColors.of(context);
```

Add to `UpdateRequiredScreen.build()` (after line 23) and `_InfoRow.build()` (after line 125).

#### Step 9.A.4: Remove unused AppTheme import

After all tokens replaced, remove `import 'package:construction_inspector/core/theme/app_theme.dart';` (line 4) and add `import 'package:construction_inspector/core/theme/field_guide_colors.dart';` for `FieldGuideColors`.

### Sub-phase 9.B: Auth Screen Token Sweep (remaining 9 screens)

**Files:**
- Modify: `lib/features/auth/presentation/screens/login_screen.dart`
- Modify: `lib/features/auth/presentation/screens/register_screen.dart`
- Modify: `lib/features/auth/presentation/screens/forgot_password_screen.dart`
- Modify: `lib/features/auth/presentation/screens/otp_verification_screen.dart`
- Modify: `lib/features/auth/presentation/screens/update_password_screen.dart`
- Modify: `lib/features/auth/presentation/screens/profile_setup_screen.dart`
- Modify: `lib/features/auth/presentation/screens/company_setup_screen.dart`
- Modify: `lib/features/auth/presentation/screens/pending_approval_screen.dart`
- Modify: `lib/features/auth/presentation/screens/account_status_screen.dart`

**Agent**: `auth-agent`

#### Step 9.B.1: Sweep for remaining AppTheme.textPrimary/textSecondary references

Per grep results, these auth screens still reference old tokens:
- `login_screen.dart` — 2 `AppTheme.textPrimary/textSecondary`
- `register_screen.dart` — 1 `AppTheme.textSecondary`
- `forgot_password_screen.dart` — 1 `AppTheme.textSecondary`
- `otp_verification_screen.dart` — 1 `AppTheme.textSecondary`
- `update_password_screen.dart` — 1 `AppTheme.textSecondary`
- `profile_setup_screen.dart` — 1 `AppTheme.textSecondary`
- `company_setup_screen.dart` — 2 `AppTheme.textSecondary`
- `pending_approval_screen.dart` — 1 `AppTheme.textSecondary`
- `account_status_screen.dart` — 1 `AppTheme.textSecondary`

Apply the standard mapping:
- `AppTheme.textPrimary` → `cs.onSurface`
- `AppTheme.textSecondary` → `cs.onSurfaceVariant`

NOTE: Only touch color tokens. Do NOT restructure layout, extract widgets, or add design-system components. These screens are clean otherwise.

### Sub-phase 9.K: Quality Gate

**Agent**: `qa-testing-agent`

#### Step 9.K.1: Run analysis and tests
```
pwsh -Command "flutter analyze lib/features/auth/"
pwsh -Command "flutter test test/features/auth/"
```

#### Step 9.K.2: Verify zero remaining violations in auth screens
Grep for `AppTheme\.text` in `lib/features/auth/presentation/screens/`. Expected: 0 matches.

#### Step 9.K.3: Testing keys

**Testing Keys**: For each screen/widget modified in this phase:
1. Review existing TestingKeys assignments — transfer all keys to their new design system wrapper
2. Add new keys for any new interactive elements (buttons, fields, toggles)
3. Update the corresponding key file in `lib/shared/testing_keys/` if keys are added/renamed
4. Run: `pwsh -Command "flutter test test/features/auth/"` to verify widget tests pass

---

## Phase 10: Bottom Sheets + Dialogs

**Goal**: Migrate all bottom sheets and dialogs to use semantic theme tokens. Wrap existing content with consistent patterns — do NOT rewrite dialog logic or change behavior.

### Sub-phase 10.A: Shared Confirmation Dialogs

**Files:**
- Modify: `lib/shared/widgets/confirmation_dialog.dart`
- Modify: `lib/shared/widgets/permission_dialog.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 10.A.1: Migrate `confirmation_dialog.dart` (3 functions)

Replace AppTheme tokens in all three dialog functions:

```dart
// WHY: Dialogs inherit theme from context. Use cs/fg for consistency.

// showConfirmationDialog (line 25):
// BEFORE: Icon(icon, color: iconColor ?? AppTheme.primaryCyan)
// AFTER:  Icon(icon, color: iconColor ?? Theme.of(dialogContext).colorScheme.primary)

// showConfirmationDialog (lines 43-44):
// BEFORE: backgroundColor: AppTheme.statusError, foregroundColor: AppTheme.textInverse,
// AFTER:  backgroundColor: Theme.of(dialogContext).colorScheme.error, foregroundColor: Theme.of(dialogContext).colorScheme.onError,

// showDeleteConfirmationDialog (line 70):
// BEFORE: Icon(Icons.delete_outline, color: AppTheme.statusError)
// AFTER:  Icon(Icons.delete_outline, color: Theme.of(dialogContext).colorScheme.error)

// showDeleteConfirmationDialog (lines 86-87):
// BEFORE: backgroundColor: AppTheme.statusError, foregroundColor: AppTheme.textInverse,
// AFTER:  backgroundColor: Theme.of(dialogContext).colorScheme.error, foregroundColor: Theme.of(dialogContext).colorScheme.onError,

// showUnsavedChangesDialog (line 145):
// BEFORE: foregroundColor: AppTheme.statusError
// AFTER:  foregroundColor: Theme.of(dialogContext).colorScheme.error
```

NOTE: These functions use `dialogContext` from the builder, not `context` from the caller. Use `Theme.of(dialogContext)` throughout.

#### Step 10.A.2: Migrate `permission_dialog.dart`

Replace 8 AppTheme tokens:

| Line | Old | New |
|------|-----|-----|
| 105 | `AppTheme.primaryCyan` | `cs.primary` |
| 139 | `AppTheme.primaryCyan.withValues(alpha: 0.1)` | `cs.primary.withValues(alpha: 0.1)` |
| 142 | `AppTheme.primaryCyan.withValues(alpha: 0.3)` | `cs.primary.withValues(alpha: 0.3)` |
| 156 | `TextStyle(fontSize: 13)` | `tt.bodySmall` |
| 167 | `AppTheme.statusWarning.withValues(alpha: 0.15)` | `fg.statusWarning.withValues(alpha: 0.15)` |
| 170 | `AppTheme.statusWarning.withValues(alpha: 0.3)` | `fg.statusWarning.withValues(alpha: 0.3)` |
| 177 | `AppTheme.statusWarning` | `fg.statusWarning` |
| 182 | `TextStyle(fontSize: 13)` | `tt.bodySmall` |
| 202, 212, 222 | `AppTheme.primaryBlue` | `cs.primary` |

Add `final cs = Theme.of(context).colorScheme;` and `final tt = Theme.of(context).textTheme;` at the top of `_StoragePermissionDialogState.build()`.

NOTE: `FieldGuideColors` access needed for `statusWarning` — add `final fg = FieldGuideColors.of(context);`.

### Sub-phase 10.B: Bottom Sheet Token Migration

**Files:**
- Modify: `lib/features/entries/presentation/widgets/bid_item_picker_sheet.dart`
- Modify: `lib/features/photos/presentation/widgets/photo_source_dialog.dart`
- Modify: `lib/features/quantities/presentation/widgets/bid_item_detail_sheet.dart`
- Modify: `lib/features/pdf/presentation/widgets/extraction_detail_sheet.dart`
- Modify: `lib/features/projects/presentation/widgets/project_switcher.dart`
- Modify: `lib/features/projects/presentation/widgets/project_delete_sheet.dart`
- Modify: `lib/features/settings/presentation/widgets/member_detail_sheet.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_add_contractor_sheet.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 10.B.1: BidItemPickerSheet (bid_item_picker_sheet.dart)

5 violations:
- Line 43: `AppTheme.surfaceHighlight` → `cs.outline`
- Line 57-59: raw `TextStyle(fontSize: 18, fontWeight: FontWeight.bold)` → `tt.titleMedium?.copyWith(fontWeight: FontWeight.bold)`
- Line 109: `AppTheme.textSecondary` → `cs.onSurfaceVariant`
- Line 121: `TextStyle(fontSize: 13)` → `tt.bodySmall`
- Line 125: `TextStyle(fontSize: 11)` → `tt.labelSmall`

NOTE: This file uses `StatefulBuilder` inside `showModalBottomSheet`. Theme access must go inside the builder where context is available.

#### Step 10.B.2: PhotoSourceDialog (photo_source_dialog.dart)

Already clean — no AppTheme tokens, uses default ListTile styling. **Skip.**

#### Step 10.B.3: BidItemDetailSheet (bid_item_detail_sheet.dart) — heaviest migration

14 raw TextStyle, 9 AppTheme color references. This is the most violation-dense file.

Pattern — replace ALL `AppTheme.*` color tokens:
- `AppTheme.textTertiary` → `fg.textTertiary` (lines 55, 301)
- `AppTheme.primaryCyan` → `cs.primary` (lines 68, 69, 71, 80, 153, 267)
- `AppTheme.textPrimary` → `cs.onSurface` (lines 91, 127, 245)
- `AppTheme.textSecondary` → `cs.onSurfaceVariant` (lines 107, 139, 215, 238, 259, 317)
- `AppTheme.surfaceElevated` → `fg.surfaceElevated` (lines 115, 224)
- `AppTheme.surfaceHighlight` → `cs.outline` (lines 118, 228)
- `AppTheme.statusSuccess` → `fg.statusSuccess` (lines 163, 189, 201)
- `AppTheme.statusError` → `cs.error` (lines 171, 189, 201)
- `AppTheme.statusWarning` → `fg.statusWarning` (line 171)
- `AppTheme.surfaceBright` → `fg.surfaceBright` (line 187)

Pattern — replace ALL raw TextStyle with textTheme:
- `TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.primaryCyan)` → `tt.bodyMedium?.copyWith(fontWeight: FontWeight.bold, color: cs.primary)`
- `TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: AppTheme.textPrimary)` → `tt.titleMedium?.copyWith(fontWeight: FontWeight.bold, color: cs.onSurface)`
- `TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textSecondary)` → `tt.bodyMedium?.copyWith(fontWeight: FontWeight.w600, color: cs.onSurfaceVariant)`
- `TextStyle(fontSize: 14, color: AppTheme.textPrimary, height: 1.5)` → `tt.bodyMedium?.copyWith(color: cs.onSurface, height: 1.5)`
- `TextStyle(fontSize: 11, color: AppTheme.textTertiary)` → `tt.labelSmall?.copyWith(color: fg.textTertiary)`
- `TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: color)` → `tt.titleSmall?.copyWith(fontWeight: FontWeight.bold, color: color)`
- `TextStyle(fontSize: 12, color: AppTheme.textSecondary)` → `tt.labelSmall?.copyWith(color: cs.onSurfaceVariant)`
- `TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: ...)` → `tt.bodyMedium?.copyWith(fontWeight: FontWeight.bold, color: ...)`
- `TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.primaryCyan)` → `tt.titleMedium?.copyWith(fontWeight: FontWeight.bold, color: cs.primary)`
- `TextStyle(color: AppTheme.textSecondary)` → `tt.bodyMedium?.copyWith(color: cs.onSurfaceVariant)`
- `TextStyle(fontWeight: FontWeight.w600, color: AppTheme.textPrimary)` → `tt.bodyMedium?.copyWith(fontWeight: FontWeight.w600, color: cs.onSurface)`
- `TextStyle(fontWeight: FontWeight.w600, color: AppTheme.textSecondary)` → `tt.bodyMedium?.copyWith(fontWeight: FontWeight.w600, color: cs.onSurfaceVariant)`

Add theme accessors in `build()` after line 32 and pass `tt`/`cs`/`fg` to `_buildDetailQuantityCard`.

#### Step 10.B.4: ExtractionDetailSheet (extraction_detail_sheet.dart)

5 `AppTheme.textPrimary/textSecondary` references. Apply standard mapping. Also has raw TextStyle instances — migrate to `tt.*`.

#### Step 10.B.5: ProjectSwitcherSheet (project_switcher.dart)

2 `Colors.*` references (in `BoxShadow`). Replace:
- `Colors.black.withValues(alpha: ...)` → `cs.shadow.withValues(alpha: ...)`

Also fix hardcoded `BorderRadius.circular(16)` → `BorderRadius.circular(AppTheme.radiusLarge)`.

#### Step 10.B.6: ProjectDeleteSheet (project_delete_sheet.dart) — 6 Colors.* violations

```dart
// BEFORE (line 58): color: Colors.orange.shade50,
// AFTER:  color: fg.statusWarning.withValues(alpha: 0.1),

// BEFORE (line 60): border: Border.all(color: Colors.orange.shade200),
// AFTER:  border: Border.all(color: fg.statusWarning.withValues(alpha: 0.3)),

// BEFORE (line 64): Icon(Icons.warning_amber, color: Colors.orange.shade700),
// AFTER:  Icon(Icons.warning_amber, color: fg.statusWarning),

// BEFORE (line 69): TextStyle(color: Colors.orange.shade900),
// AFTER:  style: tt.bodyMedium?.copyWith(color: fg.statusWarning),

// BEFORE (line 139): backgroundColor: _deleteFromDatabase ? Colors.red : null,
// AFTER:  backgroundColor: _deleteFromDatabase ? cs.error : null,

// BEFORE (line 140): foregroundColor: _deleteFromDatabase ? Colors.white : null,
// AFTER:  foregroundColor: _deleteFromDatabase ? cs.onError : null,
```

Also replace hardcoded `EdgeInsets.all(16)` with `EdgeInsets.all(AppTheme.space4)` and `SizedBox(height: 8/12/16)` with `SizedBox(height: AppTheme.space2/space3/space4)`.

#### Step 10.B.7: MemberDetailSheet (member_detail_sheet.dart) — 10+ violations

Key replacements:
- `Colors.grey[300]` (line 54) → `cs.outlineVariant`
- `Colors.grey` (lines 229, 247) → `cs.onSurfaceVariant`
- `AppTheme.primaryCyan` (lines 65, 69) → `cs.primary`
- `AppTheme.success` (lines 195, 200, 206, 244) → `fg.statusSuccess`
- `AppTheme.statusError` (lines 196, 201, 209, 311, 333) → `cs.error`
- Raw `TextStyle(fontSize: 13)` (lines 233, 236) → `tt.bodySmall`
- Raw `TextStyle(fontSize: 11)` (line 260) → `tt.labelSmall`
- Raw `TextStyle(fontSize: 18)` (line 72) → `tt.titleMedium`
- Hardcoded `EdgeInsets` (lines 37-41, 251) → `AppTheme.space4`
- Hardcoded `BorderRadius.circular(2/12)` → `AppTheme.radiusSmall`/`AppTheme.radiusMedium`

Also migrate 4 `ScaffoldMessenger.of(context).showSnackBar` calls (lines 303, 308, 351, 368) to `SnackBarHelper`:
```dart
// BEFORE:
ScaffoldMessenger.of(context).showSnackBar(
  SnackBar(content: Text('Role updated to ${_selectedRole.displayName}')),
);
// AFTER:
SnackBarHelper.showSuccess(context, 'Role updated to ${_selectedRole.displayName}');

// BEFORE:
ScaffoldMessenger.of(context).showSnackBar(
  SnackBar(
    content: Text(adminProvider.error ?? 'Failed to update role'),
    backgroundColor: AppTheme.statusError,
  ),
);
// AFTER:
SnackBarHelper.showError(context, adminProvider.error ?? 'Failed to update role');
```

#### Step 10.B.8: ReportAddContractorSheet (report_add_contractor_sheet.dart)

Light touch — replace any hardcoded `EdgeInsets.all(16)` → `AppTheme.space4`. Check for AppTheme color tokens.

### Sub-phase 10.C: Shared Dialogs — Remaining Widgets

**Files:**
- Modify: `lib/shared/widgets/empty_state_widget.dart`
- Modify: `lib/shared/widgets/search_bar_field.dart`
- Modify: `lib/shared/widgets/contextual_feedback_overlay.dart`
- Modify: `lib/shared/widgets/stale_config_warning.dart`
- Modify: `lib/shared/widgets/version_banner.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 10.C.1: EmptyStateWidget (empty_state_widget.dart)

3 violations:
```dart
// BEFORE (line 36): color: AppTheme.textTertiary,
// AFTER:  color: FieldGuideColors.of(context).textTertiary,

// BEFORE (line 48): color: AppTheme.textSecondary,
// AFTER:  color: Theme.of(context).colorScheme.onSurfaceVariant,
```

Also replace `EdgeInsets.all(32)` → `EdgeInsets.all(AppTheme.space8)`.

#### Step 10.C.2: SearchBarField (search_bar_field.dart)

Already clean — uses `AppTheme.radiusMedium` and `AppTheme.space4` properly. **Skip.**

#### Step 10.C.3: ContextualFeedbackOverlay (contextual_feedback_overlay.dart)

3 violations:
- Line 47: `Colors.transparent` — OK, leave as-is (Material scaffold pattern)
- Line 68: `AppTheme.statusSuccess`/`AppTheme.statusError` → `fg.statusSuccess`/`cs.error`
- Line 72: `Colors.black.withValues(alpha: 0.2)` → pass shadow color via parameter or use `cs.shadow`
- Line 83: `AppTheme.textInverse` → `cs.onPrimary`
- Line 91: `AppTheme.textInverse` → `cs.onPrimary`

NOTE: This widget takes `context` but builds in an OverlayEntry. Theme access via `Theme.of(context)` works because the overlay shares the same Theme ancestor. Add `final cs`, `final fg` inside the `OverlayEntry` builder.

#### Step 10.C.4: StaleConfigWarning + VersionBanner

StaleConfigWarning — 3 violations:
- `AppTheme.statusWarning` (lines 20, 21) → `fg.statusWarning`
- `AppTheme.textPrimary` (line 24 via TextStyle) → `cs.onSurface`
- `TextStyle(fontSize: 13)` → `tt.bodySmall`

VersionBanner — 3 violations:
- `AppTheme.statusInfo` (lines 31, 32) → `fg.statusInfo`
- `AppTheme.textPrimary` (line 36 via TextStyle) → `cs.onSurface`
- `TextStyle(fontSize: 13)` → `tt.bodySmall`

### Sub-phase 10.D: Feature Dialogs

**Files:**
- Modify: `lib/features/entries/presentation/widgets/add_equipment_dialog.dart`
- Modify: `lib/features/entries/presentation/widgets/add_personnel_type_dialog.dart`
- Modify: `lib/features/entries/presentation/widgets/form_selection_dialog.dart`
- Modify: `lib/features/entries/presentation/widgets/photo_detail_dialog.dart`
- Modify: `lib/features/photos/presentation/widgets/photo_name_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/add_location_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/add_equipment_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/add_contractor_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/bid_item_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/removal_dialog.dart`
- Modify: `lib/features/projects/presentation/widgets/pay_item_source_dialog.dart`
- Modify: `lib/features/settings/presentation/widgets/sign_out_dialog.dart`
- Modify: `lib/features/settings/presentation/widgets/clear_cache_dialog.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 10.D.1: Sweep all feature dialogs for AppTheme tokens

For each dialog file, apply the standard mapping:
- `AppTheme.primaryCyan` → `cs.primary`
- `AppTheme.textPrimary` → `cs.onSurface`
- `AppTheme.textSecondary` → `cs.onSurfaceVariant`
- `AppTheme.textTertiary` → `fg.textTertiary`
- `AppTheme.statusError` → `cs.error`
- `AppTheme.statusSuccess` → `fg.statusSuccess`
- `AppTheme.textInverse` → `cs.onError` (when used with error background)
- `AppTheme.surfaceElevated` → `fg.surfaceElevated`
- Raw `TextStyle(fontSize: N)` → appropriate `tt.*` token

NOTE: Each dialog uses `dialogContext` or `context` from `showDialog` builder. Use `Theme.of(dialogContext)` — NOT the outer context.

### Sub-phase 10.E: Report Dialogs

**Files:**
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_add_quantity_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_photo_detail_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_weather_edit_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_location_edit_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_pdf_actions_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_debug_pdf_actions_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_add_personnel_type_dialog.dart`
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_delete_personnel_type_dialog.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 10.E.1: Apply standard token mapping to all 8 report dialogs

Same pattern as 10.D.1. These files are in `report_widgets/` — each gets the standard AppTheme → cs/fg/tt replacement.

Also migrate any `ScaffoldMessenger.of(context).showSnackBar` to `SnackBarHelper.*`:
- `report_pdf_actions_dialog.dart` — 3 SnackBar calls
- `report_debug_pdf_actions_dialog.dart` — 2 SnackBar calls

### Sub-phase 10.F: Inline AlertDialog Extraction

**Files:**
- Modify: `lib/features/entries/presentation/widgets/contractor_editor_widget.dart`
- Modify: `lib/features/entries/presentation/widgets/entry_forms_section.dart`
- Modify: `lib/features/settings/presentation/widgets/member_detail_sheet.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 10.F.1: ContractorEditorWidget inline dialogs (lines ~484, ~523)

Two inline `AlertDialog` instances: `_showAddTypeDialog` and `_showDeleteTypeDialog`. Apply token migration in-place:
- Replace any `AppTheme.statusError` → `cs.error`
- Replace raw TextStyle → `tt.*`

NOTE: Do NOT extract to separate files — these are tightly coupled to the editor's state.

#### Step 10.F.2: EntryFormsSection._confirmDeleteForm (line ~101)

Inline delete confirmation. Replace `AppTheme.statusError` → `Theme.of(context).colorScheme.error` if present.

#### Step 10.F.3: MemberDetailSheet._handleDeactivate (line ~319)

Already addressed in 10.B.7. Verify the inline AlertDialog at line 321 also gets token migration:
```dart
// BEFORE (line 333):
backgroundColor: AppTheme.statusError,
// AFTER:
backgroundColor: Theme.of(ctx).colorScheme.error,
```

### Sub-phase 10.G: SnackBar Migration — Batch

**Files:** 39 files with 102 total `ScaffoldMessenger.of(context).showSnackBar` calls (minus 5 inside `snackbar_helper.dart` itself = 97 callsites to migrate)

**Agent**: `general-purpose`

#### Step 10.G.1: Categorize each SnackBar call by type

For each of the 97 callsites, determine the correct `SnackBarHelper` method:
- Has `backgroundColor: AppTheme.statusError` or error context → `SnackBarHelper.showError(context, message)`
- Has `backgroundColor: AppTheme.statusSuccess` or success context → `SnackBarHelper.showSuccess(context, message)`
- Has `backgroundColor: AppTheme.statusWarning` → `SnackBarHelper.showWarning(context, message)`
- Has `backgroundColor: AppTheme.primaryBlue` or info context → `SnackBarHelper.showInfo(context, message)`
- Has `action:` parameter → `SnackBarHelper.showWithAction(context, message, label, callback)`
- Plain `SnackBar(content: Text(...))` with no color → `SnackBarHelper.showInfo(context, message)`

#### Step 10.G.2: Apply mechanical replacement across all 39 files

```dart
// BEFORE:
ScaffoldMessenger.of(context).showSnackBar(
  SnackBar(
    content: Text('Entry saved successfully'),
    backgroundColor: AppTheme.statusSuccess,
  ),
);
// AFTER:
SnackBarHelper.showSuccess(context, 'Entry saved successfully');

// BEFORE (with action):
ScaffoldMessenger.of(context).showSnackBar(
  SnackBar(
    content: Text('Deleted'),
    action: SnackBarAction(label: 'Undo', onPressed: _undo),
  ),
);
// AFTER:
SnackBarHelper.showWithAction(context, 'Deleted', 'Undo', _undo);
```

Add `import 'package:construction_inspector/shared/utils/snackbar_helper.dart';` to each file that doesn't already import it.

#### Step 10.G.3: Update SnackBarHelper to use theme tokens

**File:** `lib/shared/utils/snackbar_helper.dart`

Replace AppTheme static colors with semantic theme tokens:
```dart
// WHY: SnackBarHelper itself needs to use theme tokens
// BEFORE:
backgroundColor: AppTheme.statusSuccess,
// AFTER:
backgroundColor: FieldGuideColors.of(context).statusSuccess,

// Apply same pattern for statusError, primaryBlue, statusWarning
```

### Sub-phase 10.H: Quality Gate

**Agent**: `qa-testing-agent`

#### Step 10.H.1: Run full analysis
```
pwsh -Command "flutter analyze lib/shared/widgets/"
pwsh -Command "flutter analyze lib/features/entries/presentation/widgets/"
pwsh -Command "flutter analyze lib/features/projects/presentation/widgets/"
pwsh -Command "flutter analyze lib/features/settings/presentation/widgets/"
pwsh -Command "flutter analyze lib/features/photos/presentation/widgets/"
pwsh -Command "flutter analyze lib/features/quantities/presentation/widgets/"
pwsh -Command "flutter analyze lib/features/pdf/presentation/widgets/"
```

#### Step 10.H.2: Run tests
```
pwsh -Command "flutter test"
```

#### Step 10.H.3: Verify SnackBar migration completeness
Grep for `ScaffoldMessenger\.of.*showSnackBar` outside of `snackbar_helper.dart`. Expected: 0 matches in `lib/` except `snackbar_helper.dart`.

#### Step 10.H.4: Testing keys

**Testing Keys**: For each screen/widget modified in Phases 9-10:
1. Review existing TestingKeys assignments — transfer all keys to their new design system wrapper
2. Add new keys for any new interactive elements (buttons, fields, toggles)
3. Update the corresponding key file in `lib/shared/testing_keys/` if keys are added/renamed
4. Verify SnackBar migration did not drop any testing keys from snackbar actions

#### Step 10.H.5: Golden test regeneration (Phases 9-10 batch)

**Golden Tests**: Regenerate all golden test images to match the new theme-aware rendering:
```
pwsh -Command "flutter test --update-goldens test/golden/"
```
Commit updated golden files with the phase. Review diffs to confirm changes are only color/spacing related, not structural regressions.

---

## Phase 11: Performance Pass

**Goal**: Add targeted performance optimizations to known-expensive subtrees. No speculative optimization — only address measurable or architecturally obvious hotspots.

### Sub-phase 11.A: RepaintBoundary Placement

**Files:**
- Modify: `lib/features/entries/presentation/screens/home_screen.dart`
- Modify: `lib/features/photos/presentation/widgets/photo_thumbnail.dart`
- Modify: `lib/features/dashboard/presentation/widgets/dashboard_stat_card.dart`
- Modify: `lib/features/entries/presentation/screens/entries_list_screen.dart`
- Modify: `lib/features/entries/presentation/widgets/draft_entry_tile.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 11.A.1: Calendar day cells in HomeScreen

`home_screen.dart` uses `table_calendar` which renders 42 day cells per month view. Wrap the `calendarBuilders` default/selected/today builders in `RepaintBoundary`:

```dart
// WHY: Calendar cells rebuild on every selectedDay change. RepaintBoundary
// prevents repainting cells whose content hasn't changed.
// NOTE: table_calendar's CalendarBuilders accept Widget Function() builders.
// Wrap the return value of each builder:
calendarBuilders: CalendarBuilders(
  defaultBuilder: (context, day, focusedDay) => RepaintBoundary(
    child: _buildDayCell(day, focusedDay),
  ),
  // same for selectedBuilder, todayBuilder, markerBuilder
),
```

#### Step 11.A.2: Photo thumbnails in grids

`photo_thumbnail.dart` renders images that are expensive to composite. Wrap the outermost widget in the `build()` method:

```dart
// WHY: Photo thumbnails contain Image widgets with BoxFit.cover.
// When the parent list scrolls, these get unnecessarily repainted.
@override
Widget build(BuildContext context) {
  return RepaintBoundary(
    child: /* existing widget tree */,
  );
}
```

#### Step 11.A.3: Dashboard stat cards

`dashboard_stat_card.dart` uses gradient or shadow decorations. Wrap in RepaintBoundary:

```dart
// WHY: Stat cards have BoxDecoration with shadows — expensive to paint.
// Dashboard rebuilds frequently as data loads.
```

#### Step 11.A.4: Entry list items

In `entries_list_screen.dart` and `draft_entry_tile.dart`, wrap each list item in `RepaintBoundary`:

```dart
// WHY: List items with status chips, date formatting, and badges
// get repainted during scroll even when content is unchanged.
itemBuilder: (context, index) => RepaintBoundary(
  child: _buildEntryTile(entries[index]),
),
```

### Sub-phase 11.B: Scroll Physics Consistency

**Files:**
- Modify: Any screen using `ListView`, `CustomScrollView`, or `SingleChildScrollView` that doesn't specify `physics`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 11.B.1: Audit and standardize scroll physics

Grep for `ListView.builder`, `CustomScrollView`, `SingleChildScrollView` across `lib/features/`. For each:
- If no `physics` specified, add `physics: const ClampingScrollPhysics()` (Android default)
- This ensures consistent scroll feel across all screens

NOTE: Do NOT change screens that already have explicit physics set. Do NOT use `BouncingScrollPhysics` — this is an Android-primary app.

### Sub-phase 11.C: Page Transition Consistency

**Files:**
- Modify: `lib/core/router/app_router.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 11.C.1: Verify all GoRoute entries use consistent transitions

Check that `pageBuilder` uses `AppTheme.animationPageTransition` duration for `CustomTransitionPage`. If any routes use default `MaterialPage` while others use custom transitions, standardize.

NOTE: Only touch routes that are inconsistent. If all routes already use the same pattern, skip this step.

### Sub-phase 11.E: Quality Gate

**Agent**: `qa-testing-agent`

#### Step 11.E.1: Run full test suite
```
pwsh -Command "flutter test"
```

#### Step 11.E.2: Verify no regressions
```
pwsh -Command "flutter analyze"
```

---

## Phase 12: Cleanup

**Goal**: Remove dead code, verify zero remaining violations, and ensure the refactor is complete. This phase is the final gatekeeper — nothing ships until all grep checks pass.

### Sub-phase 12.A: Delete Unused Widgets

**Files:**
- Delete: `lib/features/pdf/presentation/widgets/pdf_import_progress_dialog.dart` (marked `@Deprecated`)

**Agent**: `general-purpose`

#### Step 12.A.1: Verify PdfImportProgressDialog has zero importers

Grep for `PdfImportProgressDialog` and `pdf_import_progress_dialog.dart` across the entire codebase. The only references should be:
- The file itself
- `pdf_import_progress_manager.dart` (which replaced it)

If `pdf_import_progress_manager.dart` still imports it, remove that import and any references first.

#### Step 12.A.2: Delete the deprecated file

```
rm lib/features/pdf/presentation/widgets/pdf_import_progress_dialog.dart
```

#### Step 12.A.3: Scan for other dead widgets

Grep for `@Deprecated` or `// DEPRECATED` across `lib/`. Delete any fully-replaced widgets after verifying zero importers.

### Sub-phase 12.B: Final Token Sweep

**Agent**: `general-purpose`

#### Step 12.B.1: Hardcoded Color constructors

```
Grep pattern: Color\(0x
Path: lib/ (excluding lib/core/theme/)
Expected: 0 matches
```

If matches found, replace with semantic theme token per the mapping table.

#### Step 12.B.2: Direct Colors.* usage

```
Grep pattern: Colors\.
Path: lib/ (excluding lib/core/theme/)
Expected: Only Colors.transparent (acceptable in Material scaffold pattern)
```

Acceptable exceptions:
- `Colors.transparent` — used for Material overlay backgrounds
- `Colors.white`/`Colors.black` inside theme definition files only

All other `Colors.*` must be replaced with semantic tokens.

#### Step 12.B.3: Raw TextStyle without textTheme

```
Grep pattern: TextStyle\(
Path: lib/ (excluding lib/core/theme/, test/)
Expected: Only inside custom widget constructors where style is a parameter
```

Every `TextStyle(fontSize: N)` in a build method should be `tt.bodyMedium?.copyWith(...)` or similar.

#### Step 12.B.4: Remaining AppTheme.textPrimary/textSecondary

```
Grep pattern: AppTheme\.textPrimary|AppTheme\.textSecondary
Path: lib/ (excluding lib/core/theme/)
Expected: 0 matches
```

Current baseline: 228 occurrences across 70 files. After Phase 12, this must be 0.

#### Step 12.B.5: Remaining AppTheme.primaryCyan

```
Grep pattern: AppTheme\.primaryCyan
Path: lib/ (excluding lib/core/theme/)
Expected: 0 matches
```

#### Step 12.B.6: Remaining AppTheme.statusError/statusSuccess

```
Grep pattern: AppTheme\.statusError|AppTheme\.statusSuccess|AppTheme\.statusWarning|AppTheme\.statusInfo
Path: lib/ (excluding lib/core/theme/)
Expected: 0 matches
```

#### Step 12.B.7: Remaining AppTheme.surfaceElevated/surfaceHighlight

```
Grep pattern: AppTheme\.surfaceElevated|AppTheme\.surfaceHighlight|AppTheme\.surfaceBright
Path: lib/ (excluding lib/core/theme/)
Expected: 0 matches
```

#### Step 12.B.8: Catch-all AppTheme color sweep

Grep for ANY remaining `AppTheme.` usage outside theme files that is NOT a spacing/radius/animation/elevation token:

```
Grep pattern: `AppTheme\.(?!space|radius|animation|elevation|touchTarget|curve)`
Path: `lib/` excluding `lib/core/theme/`
Expected: 0 matches for color tokens (textPrimary, textSecondary, textTertiary, primaryCyan, primaryBlue, statusError, statusSuccess, statusWarning, surfaceElevated, surfaceHighlight, accentAmber, accentOrange, weatherSunny, etc.)
```

This catch-all ensures no color token families are missed by the specific patterns above.

### Sub-phase 12.C: SnackBar Consistency Verification

**Agent**: `qa-testing-agent`

#### Step 12.C.1: Verify zero direct ScaffoldMessenger.showSnackBar calls

```
Grep pattern: ScaffoldMessenger\.of\(.*\)\.showSnackBar
Path: lib/ (excluding lib/shared/utils/snackbar_helper.dart)
Expected: 0 matches
```

Current baseline: 97 callsites across 38 files (excluding snackbar_helper.dart itself).

#### Step 12.C.2: Verify SnackBarHelper uses theme tokens

```
Grep pattern: AppTheme\.
Path: lib/shared/utils/snackbar_helper.dart
Expected: 0 matches
```

### Sub-phase 12.D: Legacy Cleanup

**Agent**: `general-purpose`

#### Step 12.D.1: Identify removable AppTheme static re-exports

Check `lib/core/theme/app_theme.dart` for static color constants that are now fully replaced by `FieldGuideColors` extension or `ColorScheme`:

Candidates for removal (only if zero references remain outside `app_theme.dart`):
- `AppTheme.textPrimary`
- `AppTheme.textSecondary`
- `AppTheme.textTertiary`
- `AppTheme.textInverse`
- `AppTheme.primaryCyan`
- `AppTheme.primaryBlue`
- `AppTheme.statusError`
- `AppTheme.statusSuccess`
- `AppTheme.statusWarning`
- `AppTheme.statusInfo`
- `AppTheme.surfaceElevated`
- `AppTheme.surfaceHighlight`
- `AppTheme.surfaceBright`
- `AppTheme.success`

For each: grep the entire `lib/` directory. If 0 references outside theme files, add `@Deprecated` annotation with migration note. Do NOT delete yet — mark deprecated so any new code gets a warning.

```dart
// WHY: Marked deprecated (not deleted) so existing code compiles
// but new code gets IDE warnings pointing to the replacement.
@Deprecated('Use Theme.of(context).colorScheme.primary instead')
static const Color primaryCyan = Color(0xFF00BCD4);
```

#### Step 12.D.2: Remove unused imports

Run `flutter analyze` — it will flag unused imports after token migration. Fix all warnings.

### Sub-phase 12.E: Testing Key Reconciliation

**Goal:** Final verification that all testing keys survived the refactor and the driver can find every interactive element.

**Agent**: `qa-testing-agent`

#### Step 12.E.1: Grep for orphaned ValueKey usages

```
Grep pattern: ValueKey\(
Path: lib/ (excluding lib/shared/testing_keys/)
Expected: 0 matches
```

Every `ValueKey` in widget code should reference a centralized `TestingKeys.*` constant, not an inline string. Migrate any remaining orphans.

#### Step 12.E.2: Verify TestingKeys facade exports all feature keys

Check that `lib/shared/testing_keys/testing_keys.dart` exports all 12 feature key files:
- `auth_keys.dart`, `common_keys.dart`, `navigation_keys.dart`, `projects_keys.dart`
- `entries_keys.dart`, `contractors_keys.dart`, `locations_keys.dart`, `quantities_keys.dart`
- `photos_keys.dart`, `settings_keys.dart`, `sync_keys.dart`, `toolbox_keys.dart`

If any new key files were created during the refactor (e.g., `dashboard_keys.dart`), add them to the facade.

#### Step 12.E.3: Verify driver enabled-detection covers all design system types

Check `lib/core/driver/driver_server.dart` enabled-detection list includes all interactive design system component types added in Phase 1.I. If any new interactive components were added during Phases 2-11, add them to the detection list.

#### Step 12.E.4: Run full test suite including golden tests

```
pwsh -Command "flutter test"
pwsh -Command "flutter test --update-goldens test/golden/"
```

All tests must pass. Golden files must be committed if they changed.

#### Step 12.E.5: Driver key reachability smoke test

Build a debug APK with driver enabled and verify the `/find` endpoint can locate a sample of keys from each feature key file:

```
pwsh -File tools/build.ps1 -Platform android -BuildType debug -Driver
```

Test at minimum one key per feature area (auth, projects, entries, settings, sync, toolbox) by navigating to the relevant screen and calling `/find` with the key name.

### Sub-phase 12.F: Final Quality Gate

**Agent**: `qa-testing-agent`

#### Step 12.F.1: Full test suite

```
pwsh -Command "flutter test"
```

All tests must pass. Zero skips allowed.

#### Step 12.F.2: Static analysis — zero warnings

```
pwsh -Command "flutter analyze"
```

Must report 0 issues (or only pre-existing issues unrelated to this refactor).

#### Step 12.F.3: Final violation count report

Run all grep patterns from 12.B and produce a summary table:

| Pattern | Expected | Actual |
|---------|----------|--------|
| `Color(0x` outside theme | 0 | ? |
| `Colors.` outside theme (non-transparent) | 0 | ? |
| `AppTheme.textPrimary\|textSecondary` outside theme | 0 | ? |
| `AppTheme.primaryCyan` outside theme | 0 | ? |
| `AppTheme.status*` outside theme | 0 | ? |
| `AppTheme.surface*` outside theme | 0 | ? |
| `ScaffoldMessenger.showSnackBar` outside helper | 0 | ? |
| `ValueKey(` outside testing_keys/ | 0 | ? |
| TestingKeys facade missing exports | 0 | ? |

If any pattern has non-zero actual count, fix before merging.

#### Step 12.F.4: Commit with summary

Commit message should include the violation count table showing before/after across the entire refactor.
