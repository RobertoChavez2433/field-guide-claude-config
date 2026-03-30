---
feature: toolbox
type: architecture
scope: Navigation hub for calculator, forms, gallery, and todos sub-features
updated: 2026-03-30
---

# Toolbox Feature Architecture

## Overview

Toolbox is a pure navigation hub. It owns no business logic, no data layer, and no providers. Its sole responsibility is presenting a 2×2 grid of cards that route to four independent sub-features: Forms, Calculator, Gallery, and To-Do's.

## Layer Structure

```
lib/features/toolbox/
├── domain/
│   └── domain.dart              # Barrel — empty placeholder for future cross-feature use cases
├── presentation/
│   └── screens/
│       └── toolbox_home_screen.dart   # Hub screen (StatelessWidget)
└── toolbox.dart                 # Feature barrel export
```

There is no `data/` layer, no `di/` layer, and no providers in this feature.

## Key Classes

### ToolboxHomeScreen

**File**: `lib/features/toolbox/presentation/screens/toolbox_home_screen.dart`

`StatelessWidget`. Renders a 2×2 `GridView` of `_ToolboxCard` widgets. Each card navigates to a named route via `context.pushNamed(...)`.

| Card | Route Name | Testing Key |
|------|-----------|-------------|
| Forms | `'forms'` | `TestingKeys.toolboxFormsCard` |
| Calculator | `'calculator'` | `TestingKeys.toolboxCalculatorCard` |
| Gallery | `'gallery'` | `TestingKeys.toolboxGalleryCard` |
| To-Do's | `'todos'` | `TestingKeys.toolboxTodosCard` |

The screen itself is keyed with `TestingKeys.toolboxHomeScreen`. Back navigation falls back to `'dashboard'` via `safeGoBack`.

### _ToolboxCard (private)

**File**: same file as `ToolboxHomeScreen`

Private `StatelessWidget`. Renders an icon in a colored circle above a text label, wrapped in a tappable `Card`. Receives `icon`, `label`, `color`, and `onTap` — no state.

## Barrel Exports

`toolbox.dart` exports both `domain/domain.dart` and `presentation/screens/toolbox_home_screen.dart`.

## Relationships

Toolbox depends on the router and four sub-features (by route name only — no direct imports of sub-feature code):

| Sub-feature | Feature Directory |
|-------------|------------------|
| Forms | `lib/features/forms/` |
| Calculator | `lib/features/calculator/` |
| Gallery | `lib/features/gallery/` |
| Todos | `lib/features/todos/` |

All business logic, state, data models, and repositories for these sub-features live in their own feature directories.

## Pattern

**Pure navigation hub.** No `initState`, no providers, no async calls. The screen is stateless and free of side effects. Any future cross-feature use cases (e.g., a unified toolbox badge count) would be introduced in `domain/domain.dart` without changing this pattern.

## File Locations Summary

```
lib/features/toolbox/                            # Hub only
├── domain/
│   └── domain.dart                              # Placeholder barrel (empty)
├── presentation/
│   └── screens/
│       └── toolbox_home_screen.dart             # ToolboxHomeScreen + _ToolboxCard
└── toolbox.dart                                 # Feature barrel export
```
