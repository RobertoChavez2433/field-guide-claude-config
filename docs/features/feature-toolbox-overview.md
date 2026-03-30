---
feature: toolbox
type: overview
scope: Navigation hub for calculator, forms, gallery, and todos
updated: 2026-03-30
---

# Toolbox Feature Overview

## Purpose

The Toolbox feature is a pure navigation hub. It provides a 2x2 grid of cards that route inspectors to the four productivity sub-features: Forms, Calculator, Gallery, and To-Do's. It owns no business logic, no state, and no data layer — all of that lives in the respective sub-feature directories.

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/toolbox/presentation/screens/toolbox_home_screen.dart` | `ToolboxHomeScreen` — hub screen with grid navigation |
| `lib/features/toolbox/domain/domain.dart` | Domain barrel (placeholder; no exported symbols yet) |
| `lib/features/toolbox/toolbox.dart` | Feature barrel — re-exports domain and screen |

## Screens

**ToolboxHomeScreen** (`StatelessWidget`)

Renders a `GridView.count(crossAxisCount: 2)` with four `_ToolboxCard` entries:

| Card | Route name pushed |
|------|-------------------|
| Forms | `forms` |
| Calculator | `calculator` |
| Gallery | `gallery` |
| To-Do's | `todos` |

The screen has no providers, no async data loading, and no local state. It uses `safeGoBack` with `fallbackRouteName: 'dashboard'` for the back button.

## Architecture Notes

- **No providers** — toolbox has no `ChangeNotifier` or DI registration.
- **No data layer** — no models, repositories, or datasources exist under `lib/features/toolbox/`.
- **No use cases** — the domain barrel is an empty placeholder for future cross-feature use cases.
- The feature barrel (`toolbox.dart`) exports only the domain barrel and the home screen.

## Integration Points

**Depends on (navigation targets only):**
- `calculator` — routed via `context.pushNamed('calculator')`
- `forms` — routed via `context.pushNamed('forms')`
- `gallery` — routed via `context.pushNamed('gallery')`
- `todos` — routed via `context.pushNamed('todos')`

**Required by:**
- `core/router` — `ToolboxHomeScreen` registered as a named route (`toolbox`)
- `dashboard` — Toolbox entry point accessible from main navigation

## Offline Behavior

Not applicable. The screen is stateless and performs no I/O. Offline behavior is fully determined by each sub-feature.
