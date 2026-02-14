# Design System

Central design decisions for the Construction Inspector App.

Reference implementation: `lib/core/theme/app_theme.dart`
Related skill: `.claude/skills/interface-design/SKILL.md`

## Colors

| Token | Value | Usage |
|-------|-------|-------|
| primary | - | CTAs, accent elements |
| surface | - | Card backgrounds |
| error | - | Error states, delete actions |

> Extract actual values from `lib/core/theme/app_theme.dart`

## Typography

| Token | Style | Usage |
|-------|-------|-------|
| headlineLarge | - | Screen titles |
| titleLarge | - | Section headers |
| bodyLarge | - | Primary content |
| labelLarge | - | Buttons, labels |

## Spacing

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4.0 | Tight internal spacing |
| sm | 8.0 | Related elements |
| md | 16.0 | Default spacing |
| lg | 24.0 | Section separation |
| xl | 32.0 | Major sections |

## Components

### Buttons
- Primary: Filled, primary color, 48dp height minimum
- Secondary: Outlined, border only
- Text: No background, primary text color

### Cards
- Elevation: 1
- Border radius: 12.0
- Padding: md (16.0)

### Input Fields
- Height: 56dp
- Border radius: 8.0
- Label: Above field

## Construction Domain
- High contrast for outdoor use / sunlight
- Large touch targets (48dp minimum) for gloved hands
- Minimal taps for common actions
- Clear visual hierarchy for rushed users
