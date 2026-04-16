# Pattern — Adding a `/driver/*` Endpoint

How this repo does it today: a small `*Routes` class holds path constants and a `matches()` predicate; a `*Handler` class owns the `handle(request, response)` dispatch; `DriverServer._handleRequest` calls each handler in a strict order and returns on the first `true`.

## Exemplars

- `lib/core/driver/driver_data_sync_routes.dart` + `lib/core/driver/driver_data_sync_handler.dart` (with `part` files for query/mutation/maintenance groups).
- `lib/core/driver/driver_shell_handler.dart` (single-file: `DriverShellRoutes` + `DriverShellHandler`).
- `lib/core/driver/driver_interaction_routes.dart` + `driver_interaction_handler.dart` (`part` files for gesture/navigation/system).

## Reusable pieces

**`*Routes` class shape** (from `driver_data_sync_routes.dart:1-36` and `driver_shell_handler.dart:15-31`):

```dart
class DriverDataSyncRoutes {
  DriverDataSyncRoutes._();
  static const sync = '/driver/sync';
  // …
  static bool isQueryPath(String path) { … }
  static bool matches(String path) => isQueryPath(path) || isMutationPath(path) || isMaintenancePath(path);
}
```

**`*Handler` shape** (from `driver_data_sync_handler.dart:23-74`):

```dart
class DriverDataSyncHandler {
  DriverDataSyncHandler({ required … });
  Future<bool> handle(HttpRequest request, HttpResponse response) async {
    if (!DriverDataSyncRoutes.matches(request.uri.path)) return false;
    switch ((request.method, request.uri.path)) {
      case ('POST', DriverDataSyncRoutes.sync): await _handleSync(request, response);
      // …
      default: return false;
    }
    return true;
  }
}
```

**Release-mode gate** (lifted verbatim from the existing handler):

```dart
Future<bool> _rejectReleaseOrProfile(HttpResponse response) async {
  if (kReleaseMode || kProfileMode) {
    await _sendJson(response, 403, {'error': 'Not available in release mode'});
    return true;
  }
  return false;
}
```

**JSON body reader** — use the existing `_readJsonBody(request, maxBytes: …)` pattern; see `driver_data_sync_handler.dart:179-199`.

**Server wiring** — `DriverServer._handleRequest` uses a cascade of `if (await _xHandler.handle(…)) return;`. A new handler slots into that cascade in `driver_server.dart:141-174` and is constructed in the `DriverServer` constructor.

## Ownership and imports

- Handlers live in `lib/core/driver/` (flat, no `handlers/` subfolder).
- Handler dependencies flow through `DriverServer` constructor injection — never static singletons from feature code.
- Do not import `package:flutter/material.dart` into handlers — stick to `dart:io` + `package:flutter/foundation.dart` for `kDebugMode`/`kReleaseMode`. Widget inspection goes through `DriverWidgetInspector` (already injected).
- All handlers use `Logger.log` / `Logger.error` for non-frame-critical output; do not `print`.

## Applied to `/driver/seed`

Minimum viable shape:

```dart
class DriverSeedRoutes {
  DriverSeedRoutes._();
  static const seed = '/driver/seed';
  static bool matches(String path) => path == seed;
}

class DriverSeedHandler {
  DriverSeedHandler({required DatabaseService? databaseService}) : _db = databaseService;
  final DatabaseService? _db;

  Future<bool> handle(HttpRequest req, HttpResponse res) async {
    if (!DriverSeedRoutes.matches(req.uri.path)) return false;
    if (req.method != 'POST') return false;
    if (await _rejectReleaseOrProfile(res)) return true;
    // read body → dispatch to HarnessSeedData.seedBaseData / seedScreenData …
    return true;
  }
}
```

Wire into `DriverServer._handleRequest` before `_shellHandler.handle(…)` so `/driver/find` callers that wait for a seeded sentinel key work after a seed.
