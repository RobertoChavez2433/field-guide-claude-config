---
name: interface-design
description: Flutter design system and UI tokens
agent: frontend-flutter-specialist-agent
---

# Interface Design Skill

**Purpose**: Consistent UI through design system discipline.

## Core Principle

> **STATE DESIGN CHOICES BEFORE WRITING COMPONENTS**

Never build a widget without first referencing the design system. Ad-hoc styling creates inconsistency.

## Design System Location

`.claude/docs/design-system.md` - Central design decisions

If this file doesn't exist, create it with the initialization workflow.

## Workflows

### 1. Init - Create Design System

When starting fresh or design system doesn't exist:

```markdown
## Design System

### Colors
| Token | Value | Usage |
|-------|-------|-------|
| primary | [value] | [where to use] |
| ...

### Typography
| Token | Style | Usage |
|-------|-------|-------|
| headlineLarge | [spec] | [where to use] |
| ...

### Spacing
| Token | Value | Usage |
|-------|-------|-------|
| xs | 4.0 | [where to use] |
| ...

### Components
| Component | Spec | Usage |
|-----------|------|-------|
| PrimaryButton | [spec] | [where to use] |
| ...
```

### 2. Audit - Check Code Against System

Before modifying UI:

1. Read `.claude/docs/design-system.md`
2. Read target widget/screen
3. Check for violations:
   - Hardcoded colors (should use `AppTheme.*`)
   - Hardcoded padding (should use spacing tokens)
   - Inconsistent text styles (should use `Theme.of(context).textTheme.*`)
4. Report findings

### 3. Extract - Document Existing Patterns

When design system is empty but app exists:

1. Scan `lib/core/theme/app_theme.dart`
2. Document existing tokens
3. Scan common widgets for patterns
4. Document component specs

### 4. Status - Check Design Health

Report on:
- Design system completeness
- Token coverage
- Violation count in codebase

## Flutter Integration

### AppTheme Tokens

Reference: `lib/core/theme/app_theme.dart`

```dart
// Use these, not hardcoded values
AppTheme.primaryColor      // Not Colors.blue
AppTheme.surfaceColor      // Not Color(0xFFFFFFFF)
AppTheme.errorColor        // Not Colors.red
AppTheme.spacing.sm        // Not EdgeInsets.all(8.0)
```

### Theme Access

```dart
// Text styles
Theme.of(context).textTheme.headlineLarge
Theme.of(context).textTheme.bodyMedium

// Colors
Theme.of(context).colorScheme.primary
Theme.of(context).colorScheme.surface

// Custom extensions
Theme.of(context).extension<AppColors>()
```

### Spacing Constants

```dart
// Standardized spacing
const double kSpacingXs = 4.0;
const double kSpacingSm = 8.0;
const double kSpacingMd = 16.0;
const double kSpacingLg = 24.0;
const double kSpacingXl = 32.0;
```

## Reference Documents

@.claude/skills/interface-design/references/flutter-tokens.md
@.claude/skills/interface-design/references/construction-domain.md

## Before Building Any Widget

Checklist:
- [ ] Read design system (`.claude/docs/design-system.md`)
- [ ] Identify applicable tokens
- [ ] Reference `AppTheme.*` for colors
- [ ] Use theme text styles
- [ ] Apply spacing constants
- [ ] Consider construction domain needs

## Construction Domain Considerations

This app is for construction inspectors in the field:

| Need | Design Implication |
|------|-------------------|
| Outdoor use | High contrast, readable in sunlight |
| Gloved hands | Large touch targets (48dp minimum) |
| Rushed users | Minimal taps, clear hierarchy |
| Dirty screens | Tolerant of smudges, clear hit areas |
| Variable lighting | Works in bright sun and shade |

@.claude/skills/interface-design/references/construction-domain.md

## Widget Development Flow

```
1. REFERENCE design system
   └─> What tokens apply?

2. DESIGN widget spec
   └─> Colors, typography, spacing

3. BUILD with tokens
   └─> AppTheme.*, Theme.of(context).*

4. VERIFY against system
   └─> No hardcoded values?

5. UPDATE system if new pattern
   └─> Document for reuse
```

## Anti-Patterns

| Anti-Pattern | Problem | Do This Instead |
|--------------|---------|-----------------|
| Hardcoded `Color(0xFF...)` | Inconsistent, hard to change | Use `AppTheme.*` |
| Inline `TextStyle(...)` | Duplicated, inconsistent | Use `Theme.of(context).textTheme.*` |
| Magic number padding | No consistency | Use spacing constants |
| One-off widgets | Duplication | Extract to shared widgets |
| Ignoring theme | Light/dark mode breaks | Always reference theme |

## Design System File Template

```markdown
# Design System

## Colors

### Primary Palette
| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| primary | [hex] | [hex] | CTAs, accent |
| onPrimary | [hex] | [hex] | Text on primary |

### Semantic Colors
| Token | Value | Usage |
|-------|-------|-------|
| success | [hex] | Completion, save |
| warning | [hex] | Caution states |
| error | [hex] | Errors, delete |

## Typography

| Token | Size | Weight | Usage |
|-------|------|--------|-------|
| displayLarge | 57sp | 400 | Hero text |
| headlineLarge | 32sp | 400 | Screen titles |
| titleLarge | 22sp | 500 | Section headers |
| bodyLarge | 16sp | 400 | Primary content |
| labelLarge | 14sp | 500 | Buttons, labels |

## Spacing

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4.0 | Tight internal |
| sm | 8.0 | Related elements |
| md | 16.0 | Default |
| lg | 24.0 | Section separation |
| xl | 32.0 | Major sections |

## Components

### Buttons
- Primary: Filled, primary color, 48dp height
- Secondary: Outlined, border only
- Text: No background, primary text

### Cards
- Elevation: 1
- Border radius: 12.0
- Padding: md (16.0)

### Input Fields
- Height: 56dp
- Border radius: 8.0
- Label: Above field
```
