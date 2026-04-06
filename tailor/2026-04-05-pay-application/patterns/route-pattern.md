# Pattern: Route Registration

## How We Do It
Each feature exports a top-level function returning `List<RouteBase>` from `lib/core/router/routes/<feature>_routes.dart`. Routes use `GoRoute` with `path`, `name`, and `builder`. They're spread into `AppRouter._buildRouter()` routes list. Shell routes (bottom nav tabs) vs full-screen routes (detail views, wizards).

## Exemplars

### formRoutes (`lib/core/router/routes/form_routes.dart`)
```dart
List<RouteBase> formRoutes() => [
  GoRoute(
    path: '/form-viewer/:responseId',
    name: 'formViewer',
    builder: (context, state) {
      final responseId = state.pathParameters['responseId']!;
      return FormViewerScreen(responseId: responseId);
    },
  ),
  GoRoute(
    path: '/form-gallery/:responseId',
    name: 'formGallery',
    builder: (context, state) {
      final responseId = state.pathParameters['responseId']!;
      return FormGalleryScreen(responseId: responseId);
    },
  ),
];
```

### Registration in AppRouter (`lib/core/router/app_router.dart:152-157`)
```dart
routes: [
  ...authRoutes(),
  ShellRoute(...),  // bottom nav tabs
  ...settingsRoutes(rootNavigatorKey: _rootNavigatorKey),
  ...entryRoutes(),
  ...projectRoutes(),
  ...formRoutes(),
  ...toolboxRoutes(),
  ...syncRoutes(),
  // ADD: ...payAppRoutes(),
],
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `_shellPage` | `app_router.dart:82` | `static Page<void> _shellPage(LocalKey key, Widget child)` | Fade-transition page for shell tabs |
| `_fadeTransition` | `app_router.dart:91` | `static Widget _fadeTransition(...)` | Standard animation |

## New Routes Needed
```dart
List<RouteBase> payAppRoutes() => [
  GoRoute(path: '/pay-app/:payAppId', name: 'payAppDetail', ...),
  GoRoute(path: '/pay-app/:payAppId/compare', name: 'contractorComparison', ...),
  GoRoute(path: '/analytics/:projectId', name: 'projectAnalytics', ...),
];
```

## Imports
```dart
import 'package:go_router/go_router.dart';
```
