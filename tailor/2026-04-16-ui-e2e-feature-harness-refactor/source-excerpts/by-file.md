# Source Excerpts — By File

Compact excerpts so the plan writer does not need to re-read the whole file. Line numbers refer to the files as they existed at branch `gocr-integration` tip `53707175`.

---

## `lib/core/driver/driver_data_sync_routes.dart` (full file)

```dart
class DriverDataSyncRoutes {
  DriverDataSyncRoutes._();

  static const sync = '/driver/sync';
  static const resetIntegrityCheck = '/driver/reset-integrity-check';
  static const localRecord = '/driver/local-record';
  static const changeLog = '/driver/change-log';
  static const createRecord = '/driver/create-record';
  static const injectSyncPoison = '/driver/inject-sync-poison';
  static const updateRecord = '/driver/update-record';
  static const runSyncRepairs = '/driver/run-sync-repairs';
  static const syncStatus = '/driver/sync-status';
  static const removeFromDevice = '/driver/remove-from-device';
  static const restoreProjectRemote = '/driver/restore-project-remote';

  static bool isQueryPath(String path) => path == localRecord || path == changeLog || path == syncStatus;
  static bool isMutationPath(String path) => path == createRecord || path == updateRecord;
  static bool isMaintenancePath(String path) =>
      path == sync || path == resetIntegrityCheck || path == injectSyncPoison ||
      path == runSyncRepairs || path == removeFromDevice || path == restoreProjectRemote;
  static bool matches(String path) => isQueryPath(path) || isMutationPath(path) || isMaintenancePath(path);
}
```

The canonical shape for a new `/driver/*` route module.

---

## `lib/core/driver/driver_interaction_routes.dart` (full file)

```dart
class DriverInteractionRoutes {
  DriverInteractionRoutes._();
  static const tap = '/driver/tap';
  static const tapText = '/driver/tap-text';
  static const drag = '/driver/drag';
  static const text = '/driver/text';
  static const scroll = '/driver/scroll';
  static const scrollToKey = '/driver/scroll-to-key';
  static const back = '/driver/back';
  static const wait = '/driver/wait';
  static const navigate = '/driver/navigate';
  static const dismissKeyboard = '/driver/dismiss-keyboard';
  static const dismissOverlays = '/driver/dismiss-overlays';
  static const currentRoute = '/driver/current-route';

  static bool isGesturePath(String path) =>
      path == tap || path == tapText || path == drag || path == text ||
      path == scroll || path == scrollToKey;
  static bool isNavigationPath(String path) => path == back || path == navigate || path == currentRoute;
  static bool isSystemPath(String path) => path == wait || path == dismissKeyboard || path == dismissOverlays;
  static bool matches(String path) => isGesturePath(path) || isNavigationPath(path) || isSystemPath(path);
}
```

Every step verb in the per-feature YAML resolves to one of these paths.

---

## `lib/core/driver/driver_server.dart:141-179`

```dart
Future<void> _handleRequest(HttpRequest request) async {
  final res = request.response;
  try {
    if (request.headers['origin'] != null) {
      await _sendJson(res, 403, {'error': 'Browser requests blocked'});
      return;
    }
    final method = request.method;
    final path = request.uri.path;

    if (await _diagnosticsHandler.handle(request, res)) return;
    if (await _deletePropagationHandler.handle(request, res)) return;
    if (await _fileInjectionHandler.handle(request, res)) return;
    if (await _dataSyncHandler.handle(request, res)) return;
    if (await _shellHandler.handle(request, res)) return;
    if (await _interactionHandler.handle(request, res)) return;

    await _sendJson(res, 404, {'error': 'Unknown endpoint: $method $path'});
  } on Exception catch (e, stack) {
    Logger.error('DriverServer error: $e', error: e, stack: stack);
    await _sendJson(res, 500, {'error': 'Internal server error'});
  }
}
```

Insertion point for a new `_seedHandler.handle(…)` call.

---

## `lib/core/driver/screen_contract_registry.dart:5-38`

```dart
class ScreenContract {
  const ScreenContract({
    required this.id,
    required this.rootKey,
    required this.routes,
    this.seedArgs = const <String>[],
    this.actionKeys = const <String>[],
    this.stateKeys = const <String>[],
  });
  final String id;
  final Key rootKey;
  final List<String> routes;
  final List<String> seedArgs;
  final List<String> actionKeys;
  final List<String> stateKeys;

  Map<String, dynamic> toDiagnosticsMap({
    required String? activeRoute,
    required Set<String> visibleRootKeys,
  }) {
    final rootKeyValue = _serializeKey(rootKey);
    return {
      'id': id,
      'route': activeRoute,
      'rootKey': rootKeyValue,
      'rootPresent': rootKeyValue != null && visibleRootKeys.contains(rootKeyValue),
      'routes': routes,
      'seedArgs': seedArgs,
      'actions': actionKeys,
      'states': stateKeys,
    };
  }
}
```

And one example entry (screen_contract_registry.dart:151-162):

```dart
'SyncDashboardScreen': const ScreenContract(
  id: 'SyncDashboardScreen',
  rootKey: TestingKeys.syncDashboardScreen,
  routes: ['/sync/dashboard'],
  actionKeys: [
    'sync_now_tile',
    'sync_view_conflicts_tile',
    'sync_resume_sync_button',
    'sync_now_full_button',
  ],
  stateKeys: ['sync_dashboard_screen', 'sync_state_badge'],
),
```

---

## `lib/core/driver/screen_registry.dart:28-36, 111-120`

```dart
class ScreenRegistryEntry {
  const ScreenRegistryEntry({ required this.builder, this.seedArgs = const <String>[] });
  final ScreenBuilder builder;
  final List<String> seedArgs;
}

final Map<String, ScreenRegistryEntry> screenRegistryEntries = {
  'LoginScreen': ScreenRegistryEntry(builder: (_) => const LoginScreen()),
  'RegisterScreen': ScreenRegistryEntry(builder: (_) => const RegisterScreen()),
  // …
  'ProjectSetupScreen': ScreenRegistryEntry(
    seedArgs: const ['projectId', 'initialTab'],
    builder: (data) => ProjectSetupScreen(
      projectId: data['projectId'] as String?,
      initialTab: data['initialTab'] as int?,
    ),
  ),
  // …
};
```

---

## `lib/core/driver/harness_seed_data.dart:213-234`

```dart
Future<void> seedScreenData(
  DatabaseService dbService,
  String screen,
  Map<String, dynamic> data,
) async {
  switch (screen) {
    case 'MdotHubScreen':
    case 'FormGalleryScreen':
    case 'FormViewerScreen':
    case 'QuickTestEntryScreen':
    case 'ProctorEntryScreen':
    case 'WeightsEntryScreen':
      await _seedFormData(dbService, data);
      return;
    case 'PayApplicationDetailScreen':
    case 'ContractorComparisonScreen':
      await seedPayAppData(dbService, data);
      return;
    default:
      return;
  }
}
```

Add cases here when a feature spec introduces a new precondition family.

---

## `lib/core/driver/flows/flow_definition.dart` (full file)

```dart
import 'package:go_router/go_router.dart';

class FlowDefinition {
  const FlowDefinition({
    required this.name,
    required this.routes,
    required this.defaultInitialLocation,
    required this.seedScreens,
  });

  final String name;
  final List<RouteBase> routes;
  final String defaultInitialLocation;
  final List<String> seedScreens;
}
```

---

## `lib/features/auth/data/models/user_role.dart:33-44, 67-72`

```dart
bool get isAdmin => this == admin;
bool get isEngineer => this == engineer;
bool get isOfficeTechnician => this == officeTechnician;

bool get canManageProjects =>
    this == admin || this == engineer || this == officeTechnician;

bool get canManageProjectFieldData => canEditFieldData;
bool get canEditFieldData => true;
```

The role gating column in spec § Feature Taxonomy resolves exactly to these flags.

---

## `lib/features/forms/data/services/form_pdf_field_writer.dart:18-52`

```dart
void setField(PdfForm form, String name, String value) {
  try {
    final variations = generateFieldNameVariations(name);
    for (final variation in variations) {
      for (var i = 0; i < form.fields.count; i++) {
        final field = form.fields[i];
        if (field.name == variation) {
          if (_setFieldByType(field, value)) return;
        }
      }
      final lowerVariation = variation.toLowerCase();
      for (var i = 0; i < form.fields.count; i++) {
        final field = form.fields[i];
        if (field.name?.toLowerCase() == lowerVariation) {
          if (_setFieldByType(field, value)) return;
        }
      }
    }
  } on Exception catch (e) {
    Logger.pdf('[FormPDF] Error setting field "$name": $e');
  }
}
```

Read pattern for the AcroForm inspection helper is the same `form.fields[i]` / `field.name` walk, minus `_setFieldByType`.

---

## `test/features/forms/services/form_pdf_field_writer_test.dart:17-60`

```dart
final templateBytes = await rootBundle.load(kFormTemplateMdot0582b);
final document = PdfDocument(inputBytes: templateBytes.buffer.asUint8List());
try {
  final fRow1 = _findField(document.form, 'FRow1');
  expect(fRow1.readOnly, isTrue);
  writer.setField(document.form, 'FRow1', '2594');
  final savedBytes = Uint8List.fromList(await document.save());
  final reopened = PdfDocument(inputBytes: savedBytes);
  try {
    final savedF = _findField(reopened.form, 'FRow1');
    expect(savedF.text, '2594');
  } finally { reopened.dispose(); }
} finally { document.dispose(); }
```

Round-trip proof that syncfusion handles inspection for the harness.

---

## `lib/core/driver/driver_shell_handler.dart:75-143` (find endpoint)

```dart
Future<void> _handleFind(HttpRequest request, HttpResponse response) async {
  final key = request.uri.queryParameters['key'];
  if (key == null || key.isEmpty) {
    await _sendJson(response, 400, {'error': 'Missing required parameter: key'});
    return;
  }
  await _waitForFrame();
  final element = _widgetInspector.findByValueKey(key);
  final Map<String, dynamic> result = {'exists': element != null, 'key': key};
  if (element != null) {
    result['widgetType'] = element.widget.runtimeType.toString();
    // enabled detection + visibility detection …
  }
  await _sendJson(response, 200, result);
}
```

How sub-flow `assertions: - find: <key>` resolves at the driver.

---

## `lib/core/driver/driver_interaction_handler_navigation_routes.dart:74-113` (current-route)

```dart
Future<void> _handleCurrentRouteRoute(DriverInteractionHandler handler, HttpRequest req, HttpResponse res) async {
  String? route;
  var canPop = false;
  var hasBottomNav = false;
  handler._runWidgetAction(() {
    final root = WidgetsBinding.instance.rootElement;
    if (root == null) return;
    final router = handler._findRouter(root);
    if (router != null) {
      route = router.routerDelegate.currentConfiguration.uri.path;
      canPop = router.canPop();
    } else {
      route = handler._widgetInspector.currentRouteName(root);
    }
    // bottom nav probe …
  });
  await handler._sendJson(res, 200, {'route': route ?? 'unknown', 'hasBottomNav': hasBottomNav, 'canPop': canPop});
}
```

`deep_link_entry` + `nav_bar_switch_mid_flow` sub-flows use this to assert arrival.
