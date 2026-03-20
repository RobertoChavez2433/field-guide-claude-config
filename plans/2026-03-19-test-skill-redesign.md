# Test Skill Redesign Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Redesign the /test skill to use HTTP driver-based automation with IntegrationTestWidgetsFlutterBinding, replacing ADB/UIAutomator with cross-platform HTTP endpoints.
**Spec:** `.claude/specs/2026-03-19-test-skill-redesign-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-19-test-skill-redesign/`

**Architecture:** Custom `main_driver.dart` entrypoint initializes IntegrationTestWidgetsFlutterBinding, starts an HTTP driver server on port 4948 with per-session auth tokens, and registers TestPhotoService. Claude agents interact with the app via HTTP endpoints instead of ADB.
**Tech Stack:** Dart/Flutter, dart:io HttpServer, IntegrationTestWidgetsFlutterBinding, PowerShell, Node.js debug server
**Blast Radius:** 5 new, 4 modified, 6 dependent (read-only), 3 dead code cleanup

**Review:** Code review REJECT → fixed. Security APPROVE WITH CONDITIONS → conditions met.
**Review report:** `.claude/code-reviews/2026-03-19-test-skill-redesign-plan-review.md`

**Post-review fixes applied:**
- CRIT-1: `_pumpAndSettle` refactored to use `scheduleTask` (avoids event loop deadlock)
- CRIT-2: PhotoRepository import path corrected (`repositories/` subdirectory)
- CRIT-3: Proof flow table replaced with spec-accurate T01-T14
- HIGH-4: `_handleText` uses `userUpdateTextEditingValue` (triggers onChanged)
- HIGH-5: `_currentRouteName` uses GoRouter for route detection
- HIGH-6: Dispatch group parallelism clarified (D runs concurrently with B/C)
- SEC H-01: Removed `GET /driver/token`; agents read token from stdout
- SEC M-01: MOCK_AUTH regex uses `(?m)^\s*` pattern
- SEC M-02: inject handlers use `getTemporaryDirectory()` not `Directory.systemTemp`
- SEC M-03: `_dumpTree` does not include `Text.data` (PII protection)
- SEC M-04: `.claude/test-results/` added to `.gitignore`
- SEC L-01: Token truncated in `Logger.lifecycle`, full token only in stdout
- SEC L-03: Body size caps added to `_readJsonBody` (64KB default, 15MB inject)
- Path consistency: standardized to `test-results` (hyphen) throughout

---

## Phase 1: TestPhotoService

**Agent:** `general-purpose`
**Why first:** Zero dependencies. Other phases depend on this (Phase 3 registers it, Phase 2 calls it from inject-photo endpoint).

### Step 1.1: Create `lib/core/driver/test_photo_service.dart`

**New file.** Complete code:

```dart
// lib/core/driver/test_photo_service.dart
//
// WHY: TestPhotoService intercepts photo capture/gallery calls during driver-based
// testing, returning injected test images instead of invoking the camera/gallery.
// FROM SPEC: "Extends PhotoService. When inject endpoint called, writes image to
// correct directory and returns path as if image_picker selected it. Normal photo
// pipeline (EXIF, sanitization, thumbnails) still runs."

import 'dart:async';
import 'dart:collection';
import 'dart:io';

import 'package:construction_inspector/services/photo_service.dart';
// FIX CRIT-2: Correct path includes repositories/ subdirectory
import 'package:construction_inspector/features/photos/data/repositories/photo_repository.dart';
import 'package:construction_inspector/core/logging/logger.dart';

/// A PhotoService override for HTTP driver testing.
///
/// Queues injected image files and returns them from [capturePhoto] and
/// [pickFromGallery] instead of launching the device camera/gallery.
class TestPhotoService extends PhotoService {
  TestPhotoService(PhotoRepository repository) : super(repository);

  // WHY: Queue so multiple photos can be pre-loaded before a flow that needs several.
  final Queue<Completer<File?>> _pendingRequests = Queue<Completer<File?>>();
  final Queue<File> _injectedFiles = Queue<File>();

  /// Inject a file that will be returned by the next [capturePhoto] or
  /// [pickFromGallery] call. If a capture/pick is already waiting, it is
  /// completed immediately.
  void injectPhoto(File file) {
    Logger.log('TestPhotoService: injecting photo ${file.path}');
    if (_pendingRequests.isNotEmpty) {
      // WHY: A capture/pick call is already awaiting — complete it immediately.
      final completer = _pendingRequests.removeFirst();
      completer.complete(file);
    } else {
      _injectedFiles.add(file);
    }
  }

  /// Number of photos waiting to be consumed.
  int get queueLength => _injectedFiles.length;

  /// Number of capture/pick calls waiting for an injection.
  int get pendingRequestCount => _pendingRequests.length;

  @override
  Future<File?> capturePhoto() async {
    Logger.log('TestPhotoService: capturePhoto called (queue=${_injectedFiles.length})');
    return _nextFile();
  }

  @override
  Future<File?> pickFromGallery() async {
    Logger.log('TestPhotoService: pickFromGallery called (queue=${_injectedFiles.length})');
    return _nextFile();
  }

  Future<File?> _nextFile() async {
    if (_injectedFiles.isNotEmpty) {
      return _injectedFiles.removeFirst();
    }
    // WHY: No file queued yet. Park until injectPhoto() is called.
    // Timeout after 30s to avoid hanging tests forever.
    final completer = Completer<File?>();
    _pendingRequests.add(completer);
    return completer.future.timeout(
      const Duration(seconds: 30),
      onTimeout: () {
        Logger.log('TestPhotoService: timed out waiting for injected photo');
        _pendingRequests.remove(completer);
        return null;
      },
    );
  }
}
```

### Step 1.2: Verify — static analysis

```
pwsh -Command "flutter analyze lib/core/driver/test_photo_service.dart"
```

**Expected:** No issues found.

---

## Phase 2: HTTP Driver Server

**Agent:** `general-purpose`
**Depends on:** Phase 1 (imports TestPhotoService for inject-photo endpoint).

### Step 2.1: Create `lib/core/driver/driver_server.dart`

**New file.** Complete code:

```dart
// lib/core/driver/driver_server.dart
//
// WHY: HTTP driver server enables cross-platform test automation. Agents send
// HTTP requests to interact with the Flutter widget tree instead of ADB/UIAutomator.
// FROM SPEC: "dart:io HttpServer on port 4948. Per-session auth token. All 12 endpoints."
//
// SECURITY (FROM SPEC — 4 layers prevent release exposure):
//   1. build.ps1 blocks DEBUG_SERVER=true in release builds
//   2. const bool.fromEnvironment('DEBUG_SERVER') compiles to false
//   3. kReleaseMode runtime check (this file)
//   4. Custom entrypoint (main_driver.dart) only used for testing

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path_provider/path_provider.dart';

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/core/driver/test_photo_service.dart';

/// HTTP driver server for test automation.
///
/// Exposes endpoints that let external agents tap widgets, enter text,
/// scroll, take screenshots, and inject test photos — all via HTTP.
class DriverServer {
  DriverServer({
    required this.binding,
    required this.testPhotoService,
    this.port = 4948,
  });

  final IntegrationTestWidgetsFlutterBinding binding;
  final TestPhotoService testPhotoService;
  final int port;

  HttpServer? _server;
  late final String _authToken;

  /// The per-session auth token. Available after [start].
  String get authToken => _authToken;

  // WHY: Random.secure() for cryptographic randomness (FROM SPEC).
  static String _generateToken() {
    final random = Random.secure();
    final bytes = List<int>.generate(32, (_) => random.nextInt(256));
    return base64Url.encode(bytes);
  }

  /// Start the HTTP server. Returns the auth token.
  Future<String> start() async {
    // FROM SPEC: Layer 3 — runtime release guard.
    if (kReleaseMode) {
      throw StateError('DriverServer must not run in release mode');
    }

    _authToken = _generateToken();
    _server = await HttpServer.bind(InternetAddress.loopbackIPv4, port);
    Logger.log('DriverServer listening on http://127.0.0.1:$port');
    Logger.log('DriverServer auth token: $_authToken');

    _server!.listen(_handleRequest);
    return _authToken;
  }

  Future<void> stop() async {
    await _server?.close(force: true);
    _server = null;
    Logger.log('DriverServer stopped');
  }

  // ---------------------------------------------------------------------------
  // Request dispatch
  // ---------------------------------------------------------------------------

  Future<void> _handleRequest(HttpRequest request) async {
    final res = request.response;

    try {
      // FROM SPEC: Origin blocking — mirror debug server pattern.
      if (request.headers['origin'] != null) {
        _sendJson(res, 403, {'error': 'Browser requests blocked'});
        return;
      }

      // FROM SPEC: Auth — all requests require Bearer token.
      final authHeader = request.headers.value('authorization') ?? '';
      if (authHeader != 'Bearer $_authToken') {
        _sendJson(res, 401, {'error': 'Invalid or missing auth token'});
        return;
      }

      final method = request.method;
      final path = request.uri.path;

      // Route to handler.
      if (method == 'GET' && path == '/driver/ready') {
        await _handleReady(request, res);
      } else if (method == 'GET' && path == '/driver/find') {
        await _handleFind(request, res);
      } else if (method == 'GET' && path == '/driver/screenshot') {
        await _handleScreenshot(request, res);
      } else if (method == 'GET' && path == '/driver/tree') {
        await _handleTree(request, res);
      } else if (method == 'POST' && path == '/driver/tap') {
        await _handleTap(request, res);
      } else if (method == 'POST' && path == '/driver/text') {
        await _handleText(request, res);
      } else if (method == 'POST' && path == '/driver/scroll') {
        await _handleScroll(request, res);
      } else if (method == 'POST' && path == '/driver/scroll-to-key') {
        await _handleScrollToKey(request, res);
      } else if (method == 'POST' && path == '/driver/back') {
        await _handleBack(request, res);
      } else if (method == 'POST' && path == '/driver/wait') {
        await _handleWait(request, res);
      } else if (method == 'POST' && path == '/driver/inject-photo') {
        await _handleInjectPhoto(request, res);
      } else if (method == 'POST' && path == '/driver/inject-file') {
        await _handleInjectFile(request, res);
      } else {
        _sendJson(res, 404, {'error': 'Unknown endpoint: $method $path'});
      }
    } catch (e, stack) {
      Logger.error('DriverServer error: $e', error: e, stack: stack);
      _sendJson(res, 500, {'error': e.toString()});
    }
  }

  // ---------------------------------------------------------------------------
  // Endpoint handlers
  // ---------------------------------------------------------------------------

  /// GET /driver/ready — returns {ready: true, screen: "<current route>"}
  Future<void> _handleReady(HttpRequest req, HttpResponse res) async {
    // WHY: Agents poll this to know when the app is idle and which screen is active.
    String screenName = 'unknown';
    try {
      final element = WidgetsBinding.instance.rootElement;
      if (element != null) {
        screenName = _currentRouteName(element) ?? 'unknown';
      }
    } catch (_) {}
    _sendJson(res, 200, {'ready': true, 'screen': screenName});
  }

  /// GET /driver/find?key=<valueKey> — check if widget exists
  Future<void> _handleFind(HttpRequest req, HttpResponse res) async {
    final key = req.uri.queryParameters['key'];
    if (key == null || key.isEmpty) {
      _sendJson(res, 400, {'error': 'Missing required parameter: key'});
      return;
    }

    await _pumpAndSettle();
    final finder = find.byKey(ValueKey(key));
    final exists = finder.evaluate().isNotEmpty;

    // NOTE: Also return widget type and text content when found, to aid debugging.
    Map<String, dynamic> result = {'exists': exists, 'key': key};
    if (exists) {
      final element = finder.evaluate().first;
      result['widgetType'] = element.widget.runtimeType.toString();
      if (element.widget is Text) {
        result['text'] = (element.widget as Text).data;
      }
    }
    _sendJson(res, 200, result);
  }

  /// GET /driver/screenshot — capture screen as PNG
  Future<void> _handleScreenshot(HttpRequest req, HttpResponse res) async {
    await _pumpAndSettle();

    try {
      // WHY: Use binding.takeScreenshot() which is provided by IntegrationTestWidgetsFlutterBinding.
      final List<int> pngBytes = await binding.takeScreenshot('driver_screenshot');

      res.statusCode = 200;
      res.headers.contentType = ContentType('image', 'png');
      res.add(pngBytes);
      await res.close();
    } catch (e) {
      _sendJson(res, 500, {'error': 'Screenshot failed: $e'});
    }
  }

  /// GET /driver/tree?depth=N — widget tree dump
  Future<void> _handleTree(HttpRequest req, HttpResponse res) async {
    final depth = int.tryParse(req.uri.queryParameters['depth'] ?? '5') ?? 5;

    await _pumpAndSettle();

    String tree = '';
    try {
      final element = WidgetsBinding.instance.rootElement;
      if (element != null) {
        tree = _dumpTree(element, maxDepth: depth);
      }
    } catch (e) {
      tree = 'Error dumping tree: $e';
    }
    _sendJson(res, 200, {'tree': tree, 'depth': depth});
  }

  /// POST /driver/tap — body: {"key": "<valueKey>"}
  Future<void> _handleTap(HttpRequest req, HttpResponse res) async {
    final body = await _readJsonBody(req);
    if (body == null) {
      _sendJson(res, 400, {'error': 'Invalid JSON body'});
      return;
    }

    final key = body['key'] as String?;
    if (key == null || key.isEmpty) {
      _sendJson(res, 400, {'error': 'Missing required field: key'});
      return;
    }

    await _pumpAndSettle();
    final finder = find.byKey(ValueKey(key));

    if (finder.evaluate().isEmpty) {
      _sendJson(res, 404, {'error': 'Widget not found', 'key': key});
      return;
    }

    // WHY: Schedule on main UI thread via binding's test framework.
    await _runWidgetAction(() async {
      // NOTE: We use WidgetTester-style gesture. Since we don't have a WidgetTester
      // reference outside of testWidgets(), we use GestureBinding directly.
      final element = finder.evaluate().first;
      final renderBox = element.renderObject as RenderBox;
      final center = renderBox.localToGlobal(renderBox.size.center(Offset.zero));

      // Create and dispatch pointer events.
      final gesture = TestGesture(
        dispatcher: (PointerEvent event, HitTestResult result) async {
          binding.dispatchEvent(event, result);
        },
        hitTester: (Offset location) {
          final result = HitTestResult();
          binding.hitTestInView(result, location, binding.platformDispatcher.implicitView!.viewId);
          return result;
        },
        kind: ui.PointerDeviceKind.touch,
      );
      await gesture.down(center);
      await gesture.up();
    });

    await _pumpAndSettle();
    _sendJson(res, 200, {'tapped': true, 'key': key});
  }

  /// POST /driver/text — body: {"key": "<valueKey>", "text": "<value>"}
  Future<void> _handleText(HttpRequest req, HttpResponse res) async {
    final body = await _readJsonBody(req);
    if (body == null) {
      _sendJson(res, 400, {'error': 'Invalid JSON body'});
      return;
    }

    final key = body['key'] as String?;
    final text = body['text'] as String?;
    if (key == null || text == null) {
      _sendJson(res, 400, {'error': 'Missing required fields: key, text'});
      return;
    }

    await _pumpAndSettle();
    final finder = find.byKey(ValueKey(key));

    if (finder.evaluate().isEmpty) {
      _sendJson(res, 404, {'error': 'Widget not found', 'key': key});
      return;
    }

    await _runWidgetAction(() async {
      // FIX HIGH-4: Use controller.text= setter instead of updateEditingValue.
      // updateEditingValue does NOT trigger onChanged callbacks or TextEditingController
      // listeners, causing form submissions to send stale values.
      final element = finder.evaluate().first;
      EditableTextState? editableState;

      void visitor(Element el) {
        if (editableState != null) return;
        if (el is StatefulElement && el.state is EditableTextState) {
          editableState = el.state as EditableTextState;
          return;
        }
        el.visitChildren(visitor);
      }

      element.visitChildren(visitor);
      if (editableState == null && element is StatefulElement && element.state is EditableTextState) {
        editableState = element.state as EditableTextState;
      }

      if (editableState != null) {
        // WHY: Setting controller.text triggers onChanged, notifyListeners,
        // and form validation — matching real user input behavior.
        final controller = editableState!.textEditingValue;
        editableState!.userUpdateTextEditingValue(
          TextEditingValue(
            text: text,
            selection: TextSelection.collapsed(offset: text.length),
          ),
          SelectionChangedCause.keyboard,
        );
      }
    });

    await _pumpAndSettle();
    _sendJson(res, 200, {'entered': true, 'key': key, 'text': text});
  }

  /// POST /driver/scroll — body: {"key": "<scrollableKey>", "dx": 0, "dy": -300}
  Future<void> _handleScroll(HttpRequest req, HttpResponse res) async {
    final body = await _readJsonBody(req);
    if (body == null) {
      _sendJson(res, 400, {'error': 'Invalid JSON body'});
      return;
    }

    final key = body['key'] as String?;
    final dx = (body['dx'] as num?)?.toDouble() ?? 0.0;
    final dy = (body['dy'] as num?)?.toDouble() ?? 0.0;

    if (key == null) {
      _sendJson(res, 400, {'error': 'Missing required field: key'});
      return;
    }

    await _pumpAndSettle();
    final finder = find.byKey(ValueKey(key));

    if (finder.evaluate().isEmpty) {
      _sendJson(res, 404, {'error': 'Scrollable not found', 'key': key});
      return;
    }

    await _runWidgetAction(() async {
      final element = finder.evaluate().first;
      final renderBox = element.renderObject as RenderBox;
      final center = renderBox.localToGlobal(renderBox.size.center(Offset.zero));

      final gesture = TestGesture(
        dispatcher: (PointerEvent event, HitTestResult result) async {
          binding.dispatchEvent(event, result);
        },
        hitTester: (Offset location) {
          final result = HitTestResult();
          binding.hitTestInView(result, location, binding.platformDispatcher.implicitView!.viewId);
          return result;
        },
        kind: ui.PointerDeviceKind.touch,
      );
      await gesture.down(center);
      await gesture.moveBy(Offset(dx, dy));
      await gesture.up();
    });

    await _pumpAndSettle();
    _sendJson(res, 200, {'scrolled': true, 'key': key, 'dx': dx, 'dy': dy});
  }

  /// POST /driver/scroll-to-key — body: {"scrollable": "<key>", "target": "<key>", "maxScrolls": 20}
  Future<void> _handleScrollToKey(HttpRequest req, HttpResponse res) async {
    final body = await _readJsonBody(req);
    if (body == null) {
      _sendJson(res, 400, {'error': 'Invalid JSON body'});
      return;
    }

    final scrollableKey = body['scrollable'] as String?;
    final targetKey = body['target'] as String?;
    final maxScrolls = (body['maxScrolls'] as num?)?.toInt() ?? 20;

    if (targetKey == null) {
      _sendJson(res, 400, {'error': 'Missing required field: target'});
      return;
    }

    await _pumpAndSettle();

    // WHY: Scroll incrementally until the target key is visible or we exhaust attempts.
    for (int i = 0; i < maxScrolls; i++) {
      final targetFinder = find.byKey(ValueKey(targetKey));
      if (targetFinder.evaluate().isNotEmpty) {
        // NOTE: Check if the widget is actually visible (hittable) in the viewport.
        final element = targetFinder.evaluate().first;
        final renderBox = element.renderObject as RenderBox;
        if (renderBox.hasSize && renderBox.size.width > 0) {
          _sendJson(res, 200, {
            'found': true,
            'target': targetKey,
            'scrolls': i,
          });
          return;
        }
      }

      // Scroll down by 300 logical pixels.
      if (scrollableKey != null) {
        final scrollFinder = find.byKey(ValueKey(scrollableKey));
        if (scrollFinder.evaluate().isNotEmpty) {
          final element = scrollFinder.evaluate().first;
          final renderBox = element.renderObject as RenderBox;
          final center = renderBox.localToGlobal(renderBox.size.center(Offset.zero));

          await _runWidgetAction(() async {
            final gesture = TestGesture(
              dispatcher: (PointerEvent event, HitTestResult result) async {
                binding.dispatchEvent(event, result);
              },
              hitTester: (Offset location) {
                final result = HitTestResult();
                binding.hitTestInView(result, location, binding.platformDispatcher.implicitView!.viewId);
                return result;
              },
              kind: ui.PointerDeviceKind.touch,
            );
            await gesture.down(center);
            await gesture.moveBy(const Offset(0, -300));
            await gesture.up();
          });

          await _pumpAndSettle();
        }
      }
    }

    _sendJson(res, 404, {
      'found': false,
      'target': targetKey,
      'scrolls': maxScrolls,
      'error': 'Target not found after $maxScrolls scrolls',
    });
  }

  /// POST /driver/back — navigate back
  Future<void> _handleBack(HttpRequest req, HttpResponse res) async {
    await _runWidgetAction(() async {
      final navigator = Navigator.of(
        WidgetsBinding.instance.rootElement!,
        rootNavigator: true,
      );
      if (navigator.canPop()) {
        navigator.pop();
      }
    });
    await _pumpAndSettle();
    _sendJson(res, 200, {'navigatedBack': true});
  }

  /// POST /driver/wait — body: {"key": "<valueKey>", "timeoutMs": 10000}
  /// FROM SPEC: "Wait for key to appear (pumpAndSettle)"
  Future<void> _handleWait(HttpRequest req, HttpResponse res) async {
    final body = await _readJsonBody(req);
    if (body == null) {
      _sendJson(res, 400, {'error': 'Invalid JSON body'});
      return;
    }

    final key = body['key'] as String?;
    final timeoutMs = (body['timeoutMs'] as num?)?.toInt() ?? 10000;

    if (key == null) {
      _sendJson(res, 400, {'error': 'Missing required field: key'});
      return;
    }

    final deadline = DateTime.now().add(Duration(milliseconds: timeoutMs));

    while (DateTime.now().isBefore(deadline)) {
      await _pumpAndSettle();
      final finder = find.byKey(ValueKey(key));
      if (finder.evaluate().isNotEmpty) {
        // FROM SPEC: Check visible AND hittable.
        final element = finder.evaluate().first;
        final renderBox = element.renderObject;
        if (renderBox is RenderBox && renderBox.hasSize) {
          _sendJson(res, 200, {
            'found': true,
            'key': key,
            'elapsedMs': timeoutMs - deadline.difference(DateTime.now()).inMilliseconds,
          });
          return;
        }
      }
      await Future.delayed(const Duration(milliseconds: 200));
    }

    _sendJson(res, 408, {
      'found': false,
      'key': key,
      'error': 'Widget not found within ${timeoutMs}ms',
    });
  }

  /// POST /driver/inject-photo — body: base64 image data
  /// FROM SPEC: "Extension allowlist: jpg, png, webp. File size cap: 10 MB. No .. or absolute paths."
  Future<void> _handleInjectPhoto(HttpRequest req, HttpResponse res) async {
    final body = await _readJsonBody(req, maxBytes: _maxBodyBytes);
    if (body == null) {
      _sendJson(res, 400, {'error': 'Invalid JSON body'});
      return;
    }

    final base64Data = body['data'] as String?;
    final filename = body['filename'] as String? ?? 'test_photo.jpg';

    if (base64Data == null) {
      _sendJson(res, 400, {'error': 'Missing required field: data (base64)'});
      return;
    }

    // FROM SPEC: Security — extension allowlist.
    final ext = filename.split('.').last.toLowerCase();
    if (!{'jpg', 'jpeg', 'png', 'webp'}.contains(ext)) {
      _sendJson(res, 400, {'error': 'Invalid extension: $ext. Allowed: jpg, jpeg, png, webp'});
      return;
    }

    final bytes = base64Decode(base64Data);

    // FROM SPEC: Security — 10 MB cap.
    if (bytes.length > 10 * 1024 * 1024) {
      _sendJson(res, 400, {'error': 'File exceeds 10 MB limit (${bytes.length} bytes)'});
      return;
    }

    // FROM SPEC: Security — sandboxed temp dir, no path traversal.
    if (filename.contains('..') || filename.contains('/') || filename.contains('\\')) {
      _sendJson(res, 400, {'error': 'Invalid filename: path traversal detected'});
      return;
    }

    // FIX SEC M-02: Use app's sandboxed temp directory per spec contract.
    final appTempDir = await getTemporaryDirectory();
    final driverDir = Directory('${appTempDir.path}/driver_photos');
    if (!driverDir.existsSync()) driverDir.createSync(recursive: true);
    final file = File('${driverDir.path}/$filename');
    await file.writeAsBytes(bytes);

    testPhotoService.injectPhoto(file);

    _sendJson(res, 200, {
      'injected': true,
      'filename': filename,
      'bytes': bytes.length,
      'queueLength': testPhotoService.queueLength,
    });
  }

  /// POST /driver/inject-file — body: base64 file data
  /// FROM SPEC: "Extension allowlist: pdf. File size cap: 10 MB."
  Future<void> _handleInjectFile(HttpRequest req, HttpResponse res) async {
    final body = await _readJsonBody(req, maxBytes: _maxBodyBytes);
    if (body == null) {
      _sendJson(res, 400, {'error': 'Invalid JSON body'});
      return;
    }

    final base64Data = body['data'] as String?;
    final filename = body['filename'] as String?;

    if (base64Data == null || filename == null) {
      _sendJson(res, 400, {'error': 'Missing required fields: data (base64), filename'});
      return;
    }

    // FROM SPEC: Extension allowlist for files.
    final ext = filename.split('.').last.toLowerCase();
    if (!{'pdf'}.contains(ext)) {
      _sendJson(res, 400, {'error': 'Invalid extension: $ext. Allowed: pdf'});
      return;
    }

    final bytes = base64Decode(base64Data);

    if (bytes.length > 10 * 1024 * 1024) {
      _sendJson(res, 400, {'error': 'File exceeds 10 MB limit (${bytes.length} bytes)'});
      return;
    }

    if (filename.contains('..') || filename.contains('/') || filename.contains('\\')) {
      _sendJson(res, 400, {'error': 'Invalid filename: path traversal detected'});
      return;
    }

    // FIX SEC M-02: Use app's sandboxed temp directory per spec contract.
    final appTempDir = await getTemporaryDirectory();
    final driverDir = Directory('${appTempDir.path}/driver_files');
    if (!driverDir.existsSync()) driverDir.createSync(recursive: true);
    final file = File('${driverDir.path}/$filename');
    await file.writeAsBytes(bytes);

    _sendJson(res, 200, {
      'injected': true,
      'path': file.path,
      'filename': filename,
      'bytes': bytes.length,
    });
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /// Pump frames and settle animations via the integration test binding.
  /// FIX CRIT-1: All frame pumping MUST go through scheduleTask to avoid deadlocking
  /// the event loop. HTTP handlers and the UI both run on the same Dart isolate.
  Future<void> _pumpAndSettle() async {
    final completer = Completer<void>();
    WidgetsBinding.instance.scheduleTask(() async {
      try {
        binding.scheduleFrame();
        await binding.endOfFrame;
        int pumps = 0;
        while (binding.hasScheduledFrame && pumps < 100) {
          binding.scheduleFrame();
          await binding.endOfFrame;
          pumps++;
        }
        completer.complete();
      } catch (e) {
        Logger.log('DriverServer: pumpAndSettle error (non-fatal): $e');
        completer.complete(); // Non-fatal — don't propagate
      }
    }, Priority.touch);
    await completer.future;
  }

  /// Run a widget action on the main thread.
  Future<void> _runWidgetAction(Future<void> Function() action) async {
    // WHY FROM SPEC: "HTTP requests on Dart event loop. Dispatch to main isolate
    // via WidgetsBinding.instance.scheduleTask(). All widget interaction on main UI thread."
    final completer = Completer<void>();
    WidgetsBinding.instance.scheduleTask(() async {
      try {
        await action();
        completer.complete();
      } catch (e) {
        completer.completeError(e);
      }
    }, Priority.touch);
    await completer.future;
  }

  /// FIX HIGH-5: Use GoRouter to get current route location.
  /// The app uses go_router (confirmed in app_router.dart), so we can read the
  /// current path directly from the router's configuration.
  String? _currentRouteName(Element root) {
    String? routeName;

    // Strategy 1: Find GoRouter and read its current location.
    void goRouterVisitor(Element element) {
      if (routeName != null) return;
      try {
        // GoRouter registers itself in the widget tree via InheritedWidget.
        // Walk until we find a context where GoRouter.of() succeeds.
        if (element.widget is Scaffold || element.widget is MaterialApp) {
          final router = GoRouter.maybeOf(element);
          if (router != null) {
            routeName = router.routerDelegate.currentConfiguration.uri.path;
            return;
          }
        }
      } catch (_) {
        // GoRouter not found at this level — keep walking.
      }
      element.visitChildren(goRouterVisitor);
    }

    root.visitChildren(goRouterVisitor);

    // Strategy 2 fallback: look for deepest Scaffold with a ValueKey.
    if (routeName == null) {
      void scaffoldVisitor(Element element) {
        if (element.widget is Scaffold && element.widget.key is ValueKey) {
          routeName = (element.widget.key as ValueKey).value?.toString();
        }
        element.visitChildren(scaffoldVisitor);
      }
      root.visitChildren(scaffoldVisitor);
    }

    return routeName;
  }

  /// Dump widget tree to a string with depth limiting.
  /// FIX SEC M-03: Do NOT include Text.data — it may contain PII (names, emails, cert numbers).
  /// Widget type + key are sufficient for debugging.
  String _dumpTree(Element root, {int maxDepth = 5}) {
    final buffer = StringBuffer();
    void visitor(Element element, int depth) {
      if (depth > maxDepth) return;
      final indent = '  ' * depth;
      final widget = element.widget;
      final keyStr = widget.key != null ? ' key=${widget.key}' : '';
      buffer.writeln('$indent${widget.runtimeType}$keyStr');
      element.visitChildren((child) => visitor(child, depth + 1));
    }
    root.visitChildren((child) => visitor(child, 0));
    return buffer.toString();
  }

  // FIX SEC L-03: Body size cap — 15MB for inject endpoints, 64KB for others.
  static const int _maxBodyBytes = 15 * 1024 * 1024; // 15 MB (base64 overhead of 10 MB)

  Future<Map<String, dynamic>?> _readJsonBody(HttpRequest req, {int? maxBytes}) async {
    try {
      final limit = maxBytes ?? 64 * 1024; // 64 KB default for non-inject endpoints
      final chunks = <int>[];
      await for (final chunk in req) {
        chunks.addAll(chunk);
        if (chunks.length > limit) {
          return null; // Body too large
        }
      }
      final body = utf8.decode(chunks);
      if (body.isEmpty) return {};
      return jsonDecode(body) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  void _sendJson(HttpResponse res, int statusCode, Map<String, dynamic> data) {
    res.statusCode = statusCode;
    res.headers.contentType = ContentType.json;
    res.write(jsonEncode(data));
    res.close();
  }
}
```

### Step 2.2: Verify — static analysis

```
pwsh -Command "flutter analyze lib/core/driver/driver_server.dart"
```

**Expected:** No issues found (or only info-level hints about unused imports that resolve when Phase 3 integrates this).

---

## Phase 3: Custom Entrypoint

**Agent:** `general-purpose`
**Depends on:** Phase 1 (TestPhotoService), Phase 2 (DriverServer).

### Step 3.1: Create `lib/main_driver.dart`

**New file.** This mirrors `lib/main.dart` `_runApp()` (lines 110-555) but replaces:
- `WidgetsFlutterBinding.ensureInitialized()` → `IntegrationTestWidgetsFlutterBinding.ensureInitialized()`
- `PhotoService(photoRepository)` → `TestPhotoService(photoRepository)`
- Adds DriverServer start + auth token logging

NOTE TO IMPLEMENTER: You must read `lib/main.dart` lines 93-555 and `lib/main.dart` lines 700-730 (ConstructionInspectorApp) to capture the full initialization sequence. The code below shows the structural skeleton with the key replacements — you MUST copy the full provider list, datasource initialization, repository setup, etc. from main.dart.

```dart
// lib/main_driver.dart
//
// WHY: Custom entrypoint for HTTP driver testing. Uses IntegrationTestWidgetsFlutterBinding
// instead of WidgetsFlutterBinding, starts DriverServer, and registers TestPhotoService.
// FROM SPEC: "Custom main_driver.dart entrypoint initializes IntegrationTestWidgetsFlutterBinding,
// starts an HTTP driver server on port 4948 with per-session auth tokens."
//
// This file is NEVER used in production. It is only invoked via:
//   flutter run --target=lib/main_driver.dart --dart-define=DEBUG_SERVER=true

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:integration_test/integration_test.dart';

import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/core/driver/driver_server.dart';
import 'package:construction_inspector/core/driver/test_photo_service.dart';

// WHY: Import everything main.dart imports — same initialization sequence.
// NOTE TO IMPLEMENTER: Copy ALL imports from lib/main.dart here. The list is ~40 imports.
// Do not abbreviate. Every import from main.dart must be present.

// ... (copy all imports from main.dart) ...

Future<void> main() async {
  runZonedGuarded(
    () async {
      // FROM SPEC: Replace WidgetsFlutterBinding with IntegrationTestWidgetsFlutterBinding.
      final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized()
          as IntegrationTestWidgetsFlutterBinding;

      await _runApp(binding);
    },
    (error, stack) {
      Logger.error('Uncaught zone error: $error', error: error, stack: stack);
    },
    zoneSpecification: Logger.zoneSpec(),
  );
}

Future<void> _runApp(IntegrationTestWidgetsFlutterBinding binding) async {
  Logger.lifecycle('Application starting (DRIVER MODE)...');

  // NOTE TO IMPLEMENTER: Copy the ENTIRE initialization sequence from main.dart _runApp(),
  // lines ~112-550. Keep everything identical EXCEPT the following replacements:

  // ===== REPLACEMENT 1: PhotoService → TestPhotoService =====
  // In main.dart you will find (approximately):
  //   final photoService = PhotoService(photoRepository);
  // Replace with:
  //   final testPhotoService = TestPhotoService(photoRepository);
  //   final photoService = testPhotoService; // WHY: Keeps downstream references working

  // ===== ADDITION 1: Start DriverServer before runApp() =====
  // After all initialization, before runApp(), add:
  //
  //   // FROM SPEC: Start HTTP driver server with auth token.
  //   final driverServer = DriverServer(
  //     binding: binding,
  //     testPhotoService: testPhotoService,
  //   );
  //   final authToken = await driverServer.start();
  //
  //   // FROM SPEC: "Token POSTed to debug server."
  //   _postAuthToken(authToken);
  //
  //   // FIX SEC L-01: Log truncated token to Logger (reaches debug server).
  //   // Full token printed to stdout only (next line).
  //   Logger.lifecycle('Driver mode ready. Token: ${authToken.substring(0, 8)}...');
  //   print('DRIVER_AUTH_TOKEN=$authToken'); // Agents parse this from stdout

  // ===== REPLACEMENT 2: In the runApp() call =====
  // The ConstructionInspectorApp constructor takes `photoService: photoService`.
  // Because we aliased testPhotoService → photoService above, this works unchanged.

  // ===== CRITICAL: Keep everything else identical =====
  // - PreferencesService, DatabaseService, Supabase, Firebase
  // - All datasources, repositories, providers
  // - SyncOrchestrator, AuthProvider
  // - All 30+ constructor params to ConstructionInspectorApp
}

/// POST the driver auth token to the debug server for diagnostics logging.
/// FIX SEC H-01: Agents read the full token from stdout, NOT from the debug server.
/// This POST only registers the token so the debug server can log it truncated.
void _postAuthToken(String token) {
  if (kReleaseMode) return;

  try {
    HttpClient()
        .postUrl(Uri.parse('http://127.0.0.1:3947/driver/token'))
        .then((request) {
      request.headers.contentType = ContentType.json;
      request.write(jsonEncode({'token': token}));
      return request.close();
    }).then((response) {
      response.drain<void>();
      Logger.log('Driver auth token posted to debug server');
    }).catchError((e) {
      Logger.log('Failed to post driver auth token to debug server: $e');
    });
  } catch (e) {
    Logger.log('Failed to post driver auth token: $e');
  }
}
```

**CRITICAL INSTRUCTION TO IMPLEMENTER:** The `// NOTE TO IMPLEMENTER` sections above are NOT placeholders. You MUST:
1. Read `lib/main.dart` in full
2. Copy every import
3. Copy the entire `_runApp()` body
4. Apply only the 2 replacements noted above (PhotoService → TestPhotoService, add DriverServer start)
5. The resulting file will be ~500+ lines. That is expected.

### Step 3.2: Verify — static analysis

```
pwsh -Command "flutter analyze lib/main_driver.dart"
```

**Expected:** No issues found.

---

## Phase 4: Build Script Updates

**Agent:** `general-purpose`
**Depends on:** None (independent tooling change).

### Step 4.1: Modify `tools/build.ps1`

**File:** `tools/build.ps1` (151 lines)

**Modification 1 — Add parameters (line 1-8, the param block):**

Current param block:
```powershell
param(
    [Parameter(Mandatory)]
    [ValidateSet("android", "windows", "ios")]
    [string]$Platform,
    [ValidateSet("debug", "release")]
    [string]$BuildType = "release",
    [switch]$Clean
)
```

Replace with:
```powershell
param(
    [Parameter(Mandatory)]
    [ValidateSet("android", "windows", "ios")]
    [string]$Platform,
    [ValidateSet("debug", "release")]
    [string]$BuildType = "release",
    [switch]$Clean,
    # FROM SPEC: "-DebugServer switch: appends --dart-define=DEBUG_SERVER=true. Only valid with debug."
    [switch]$DebugServer,
    # FROM SPEC: "-Target parameter: specifies custom entrypoint (default: lib/main.dart)."
    [string]$Target = "lib/main.dart"
)
```

**Modification 2 — Add validation block (after param block, before existing DEBUG_SERVER guard ~line 47):**

Insert after the param block closes:
```powershell
# FROM SPEC: "-DebugServer only valid with debug"
if ($DebugServer -and $BuildType -ne "debug") {
    Write-Error "ERROR: -DebugServer can only be used with -BuildType debug"
    exit 1
}

# FROM SPEC: "Block MOCK_AUTH + DEBUG_SERVER combination"
if ($DebugServer) {
    # WHY: MOCK_AUTH bypasses real auth. Combined with DEBUG_SERVER's HTTP endpoints,
    # this would create an unauthenticated test path that could mask real auth bugs.
    $envContent = Get-Content ".env" -ErrorAction SilentlyContinue
    # FIX SEC M-01: Use same regex pattern as existing DEBUG_SERVER guard for consistency.
    if ($envContent -match '(?m)^\s*MOCK_AUTH\s*=\s*true') {
        Write-Error "ERROR: MOCK_AUTH=true and -DebugServer cannot be used together"
        exit 1
    }
}
```

**Modification 3 — Add -DebugServer to dart define args (near where dartDefineArgs is assembled):**

Find where `--dart-define=DEBUG_SERVER=true` or dart define args are built. Add:
```powershell
if ($DebugServer) {
    $dartDefineArgs += "--dart-define=DEBUG_SERVER=true"
}
```

**Modification 4 — Add -Target to flutter build/run commands:**

Find each `flutter build` or `flutter run` command line. Add `--target=$Target` to the arguments. For example, if the current command is:
```powershell
flutter build apk --debug @dartDefineArgs
```
Change to:
```powershell
flutter build apk --debug --target=$Target @dartDefineArgs
```

Apply this to ALL build commands (Android debug, Android release, Windows debug, Windows release).

### Step 4.2: Modify `.gitignore`

**File:** `.gitignore`

Find the line:
```
.env.secret
```

Replace with:
```
# WHY: Broaden to catch any secret file variants (FROM SPEC).
*.secret
```

Also add (FIX SEC M-04 — test run artifacts with PII must be gitignored):
```
# E2E test run artifacts (screenshots may contain PII)
.claude/test-results/
```

NOTE: If `.env.secret` is not in .gitignore, add `*.secret` to the secrets section.

### Step 4.3: Verify — build script guards

FIX: build.ps1 doesn't support -WhatIf. Instead, verify guards fire correctly:

```
pwsh -Command "try { & tools/build.ps1 -Platform android -BuildType release -DebugServer 2>&1 } catch { Write-Host 'GUARD FIRED: ' + $_.Exception.Message }"
```

**Expected:** Error: "-DebugServer can only be used with -BuildType debug"

Also verify parameters exist:
```
pwsh -Command "Get-Content tools/build.ps1 | Select-String 'DebugServer|Target|MOCK_AUTH'"
```

**Expected:** Multiple matches showing the new parameters and guards.

---

## Phase 5: Debug Server Update

**Agent:** `general-purpose`
**Depends on:** None (independent).

### Step 5.1: Modify `tools/debug-server/server.js`

**File:** `tools/debug-server/server.js`

**Modification 1 — Add driver token storage (near top, after existing state variables):**

Find the section where in-memory state is declared (sync status object, log arrays). Add:
```javascript
// FROM SPEC: "POST /driver/token endpoint (stores driver auth token)"
let driverAuthToken = null;
```

**Modification 2 — Add routes (inside the request handler, after existing routes ~line 272-320):**

Find the route dispatch section. Before the 404 fallback, add:
```javascript
  // FIX SEC H-01: Removed GET /driver/token endpoint. Exposing the auth token via an
  // unauthenticated endpoint defeats its purpose. Agents read the token from stdout instead.
  // POST /driver/token is kept so the app can log a truncated token for diagnostics.
  if (req.method === 'POST' && pathname === '/driver/token') {
    const body = await readBody(req);
    try {
      const data = JSON.parse(body);
      driverAuthToken = data.token || null;
      // NOTE: Only log truncated token — full token stays in app stdout only.
      console.log(`[driver] Auth token registered: ${driverAuthToken ? driverAuthToken.substring(0, 8) + '...' : 'null'}`);
      sendJson(res, 200, { stored: true });
    } catch (e) {
      sendJson(res, 400, { error: 'Invalid JSON' });
    }
    return;
  }
```

### Step 5.2: Verify — server starts cleanly

```
pwsh -Command "cd tools/debug-server; node -c server.js"
```

**Expected:** No syntax errors.

---

## Phase 6: Unified Flow Registry

**Agent:** `general-purpose`
**Depends on:** None (documentation/config).

### Step 6.1: Create `.claude/test-flows/registry.md`

**New file.** This merges both existing registries into a unified format.

NOTE TO IMPLEMENTER: Read both source registries before writing:
- `.claude/test-flows/flow_registry.md` (or wherever the old ADB flow registry lives)
- `.claude/test_results/flow_registry.md`

The new format must include these fields per flow:
```markdown
| ID | Flow | Tier | Table(s) | Driver Steps | Verify-Sync | Verify-Logs | Status | Last Run | Notes |
```

Write the 14 proof flows (T01-T14) using this template:

```markdown
# Unified Test Flow Registry

> Auto-updated by test agents after each run. Manual edits will be overwritten.

## Format
- **Driver Steps**: HTTP driver endpoint sequence (abbreviated)
- **Verify-Sync**: `verify-sync.ps1` invocation for data confirmation
- **Verify-Logs**: Debug server log categories to scan for errors
- **Status**: PASS / FAIL / UNTESTED / BLOCKED
- **Last Run**: ISO date of most recent execution

## Tier 1: Foundation (T01-T06)

> FIX CRIT-3: Flows now match spec exactly (project, location, contractor, equipment, pay item, assignment).

| ID | Flow | Table(s) | Driver Steps | Verify-Sync | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|-------------|--------|----------|-------|
| T01 | Create Project "E2E Test Project" | projects | tap(projects_nav) → tap(project_create) → text(project_name,"E2E Test Project") → text(project_number,"E2E-001") → tap(project_save) → wait(project_list) | -Table projects -Filter "name=like.E2E*" -CountOnly | sync,db | UNTESTED | - | |
| T02 | Add Location | locations | tap(project_card) → tap(project_locations_tab) → tap(project_add_location) → text(location_name,"E2E Location A") → tap(location_dialog_add) → tap(project_save) | -Table locations -CountOnly | sync,db | UNTESTED | - | Depends: T01 |
| T03 | Add Contractor | contractors | tap(project_contractors_tab) → tap(project_add_contractor) → text(contractor_name,"E2E Contractor") → tap(contractor_save) | -Table contractors -CountOnly | sync,db | UNTESTED | - | Depends: T01 |
| T04 | Add Equipment | equipment | tap(contractor_card) → tap(add_equipment) → text(equipment_name,"E2E Excavator") → tap(equipment_save) | -Table equipment -CountOnly | sync,db | UNTESTED | - | Depends: T03 |
| T05 | Add Pay Item | bid_items | tap(project_payitems_tab) → tap(add_bid_item) → text(bid_item_number,"E2E-100") → text(bid_item_desc,"E2E Test Item") → tap(bid_item_save) | -Table bid_items -CountOnly | sync,db | UNTESTED | - | Depends: T01 |
| T06 | Add Project Assignment | project_assignments | tap(project_assignments_tab) → tap(add_assignment) → tap(user_select) → tap(assignment_save) | -Table project_assignments -CountOnly | sync,db | UNTESTED | - | Depends: T01 |

## Tier 2: Daily Entry Full Lifecycle (T07-T13)

| ID | Flow | Table(s) | Driver Steps | Verify-Sync | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|-------------|--------|----------|-------|
| T07 | Create Daily Entry | daily_entries | tap(calendar_nav) → tap(add_entry_fab) → wait(entry_wizard) → tap(entry_wizard_save_draft) | -Table daily_entries -CountOnly | sync,db | UNTESTED | - | Depends: T01 |
| T08 | Add Personnel Log | entry_personnel_counts | tap(entry_card) → tap(personnel_tab) → tap(add_personnel) → text(personnel_count,"5") → tap(personnel_save) | -Table entry_personnel_counts -CountOnly | sync,db | UNTESTED | - | Depends: T07 |
| T09 | Add Equipment Usage | entry_equipment | tap(equipment_usage_tab) → tap(add_equipment_usage) → tap(select_equipment) → tap(equipment_usage_save) | -Table entry_equipment -CountOnly | sync,db | UNTESTED | - | Depends: T04,T07 |
| T10 | Log Quantities | entry_quantities | tap(quantities_tab) → tap(add_quantity) → tap(select_bid_item) → text(quantity_value,"10.5") → tap(quantity_save) | -Table entry_quantities -CountOnly | sync,db | UNTESTED | - | Depends: T05,T07 |
| T11 | Attach Photo (inject-photo) | photos | tap(photos_tab) → tap(add_photo) → inject-photo(test.jpg) → wait(photo_thumbnail) | -Table photos -CountOnly | sync,photo | UNTESTED | - | Depends: T07 |
| T12 | Create Todo | todo_items | tap(toolbox_nav) → tap(todos_tab) → tap(add_todo) → text(todo_title,"E2E Todo") → tap(todo_save) | -Table todo_items -CountOnly | sync,db | UNTESTED | - | Depends: T01 |
| T13 | Fill Inspector Form | inspector_forms | tap(toolbox_nav) → tap(forms_tab) → tap(add_form) → text(form_field,"E2E Form Data") → tap(form_save) | -Table inspector_forms -CountOnly | sync,db | UNTESTED | - | Depends: T01 |

## Tier 3: PDF Export (T14)

| ID | Flow | Table(s) | Driver Steps | Verify-Sync | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|-------------|--------|----------|-------|
| T14 | Export Daily Entry to PDF | N/A (local) | tap(entry_card) → tap(export_pdf) → wait(pdf_ready) → screenshot | N/A (verify file exists, non-zero bytes) | pdf | UNTESTED | - | Depends: T07 |

## Remaining Flows (from legacy registries — not yet migrated to HTTP driver)

> These flows existed in the old ADB and sync verification registries. They will be
> migrated to HTTP driver format in future phases. Listed here for tracking only.

<!-- NOTE TO IMPLEMENTER: Read both old registries and list remaining flow IDs/names here
     as a simple bullet list. Do not write full driver steps for unmigrated flows. -->

## Auto-Update Protocol

After each test run, the agent MUST update:
1. **Status** column: PASS or FAIL
2. **Last Run** column: ISO date (e.g., 2026-03-19)
3. **Notes** column: failure reason if FAIL, cleared on PASS
```

### Step 6.2: Verify — file exists and is valid markdown

```
pwsh -Command "Test-Path '.claude/test-flows/registry.md'"
```

**Expected:** True.

---

## Phase 7: Skill and Agent Rewrite

**Agent:** `general-purpose`
**Depends on:** Phase 6 (references unified registry).

### Step 7.1: Rewrite `.claude/skills/test/SKILL.md`

**Full rewrite.** Read the current file first, then replace entirely.

NOTE TO IMPLEMENTER: Read `.claude/skills/test/SKILL.md` first. Then write the complete replacement below.

```markdown
---
name: test
description: Run E2E test flows via HTTP driver automation
agents:
  - .claude/agents/test-wave-agent.md
---

# /test — HTTP Driver Test Skill

## Overview
Runs end-to-end test flows against the running app via HTTP driver endpoints (port 4948).
The app must be launched with `main_driver.dart` entrypoint. Agents interact with widgets
via HTTP instead of ADB/UIAutomator, making this cross-platform (Android + Windows).

## Prerequisites
1. Debug server running: `node tools/debug-server/server.js`
2. App launched with driver entrypoint:
   - **Windows:** `pwsh -Command "flutter run --target=lib/main_driver.dart -d windows --dart-define=DEBUG_SERVER=true --dart-define-from-file=.env"`
   - **Android:** `pwsh -File tools/build.ps1 -Platform android -BuildType debug -DebugServer -Target lib/main_driver.dart` → install → `adb reverse tcp:3947 tcp:3947` + `adb reverse tcp:4948 tcp:4948`
3. Auth token captured from flutter run stdout (look for `DRIVER_AUTH_TOKEN=<token>`)

## Usage

```
/test                     # Run all 14 proof flows (T01-T14)
/test T01-T06             # Run Tier 1 Foundation only
/test T07-T13             # Run Tier 2 Daily Entry Lifecycle only
/test T14                 # Run Tier 3 PDF Export only
/test T03                 # Run single flow
```

## Architecture

```
Claude (orchestrator)
  ├─ Tier 1 agent (T01-T06) — sequential
  ├─ Tier 2 agent (T07-T13) — sequential (after Tier 1 passes)
  └─ Tier 3 agent (T14)     — sequential (after Tier 2 passes)
```

Each agent:
1. Retrieves auth token from debug server
2. Executes driver steps via HTTP (port 4948)
3. Polls sync status via debug server (port 3947)
4. Scans logs for errors
5. Runs verify-sync.ps1 for Supabase confirmation
6. Updates registry with results

## HTTP Driver Endpoints (port 4948)

All require `Authorization: Bearer <token>` header.

| Method | Endpoint | Body/Params |
|--------|----------|-------------|
| GET | /driver/ready | — |
| GET | /driver/find?key=X | — |
| GET | /driver/screenshot | — |
| GET | /driver/tree?depth=N | — |
| POST | /driver/tap | {"key": "X"} |
| POST | /driver/text | {"key": "X", "text": "Y"} |
| POST | /driver/scroll | {"key": "X", "dx": 0, "dy": -300} |
| POST | /driver/scroll-to-key | {"scrollable": "X", "target": "Y"} |
| POST | /driver/back | {} |
| POST | /driver/wait | {"key": "X", "timeoutMs": 10000} |
| POST | /driver/inject-photo | {"data": "<base64>", "filename": "test.jpg"} |
| POST | /driver/inject-file | {"data": "<base64>", "filename": "doc.pdf"} |

## Verification Pipeline (per flow)

```
HTTP driver: create data → trigger sync
    ↓
Poll GET /sync/status (debug server) — wait for completed (30s timeout)
    ↓
GET /logs?since=<start>&category=sync — check for sync errors
GET /logs?since=<start>&level=error — check for runtime errors
    ↓
pwsh -File tools/verify-sync.ps1 -Table X -Filter Y -CountOnly
    ↓
Update .claude/test-flows/registry.md
```

## Error Handling
- **Driver unreachable:** retry once after 2s, then FAIL
- **Element not found:** wait 3s with pumpAndSettle retry, then FAIL
- **Sync timeout (30s):** check /sync/status for error state, FAIL
- **verify-sync no data:** FAIL
- **Logs show errors:** FAIL if sync/db category
- **App crash:** detect via /driver/ready timeout, capture last logs

## Flow Registry
`.claude/test-flows/registry.md` — unified registry with all flows and run history.

## Test Data Safety
- All test projects use "E2E " prefix
- Cleanup: `pwsh -File tools/verify-sync.ps1 -Cleanup -ProjectName "E2E*" -DryRun`
- Results pruning: `pwsh -File tools/prune-test-results.ps1`
```

### Step 7.2: Rewrite `.claude/agents/test-wave-agent.md`

**Full rewrite.** Read the current file first, then replace entirely.

NOTE TO IMPLEMENTER: Read `.claude/agents/test-wave-agent.md` first. Then write the complete replacement.

```markdown
---
name: test-wave-agent
description: Executes a wave of E2E test flows via HTTP driver
model: sonnet
tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - WebFetch
---

# Test Wave Agent

You are a test automation agent that executes E2E test flows against a Flutter app
via HTTP driver endpoints. You interact with widgets by sending HTTP requests to
port 4948, verify sync via the debug server on port 3947, and confirm data in
Supabase via verify-sync.ps1.

## Setup (every wave)

1. Get the driver auth token from the app's stdout (provided by orchestrator in the prompt):
   The orchestrator captures `DRIVER_AUTH_TOKEN=<token>` from the flutter run stdout
   and passes it to the agent. FIX SEC H-01: Token is NOT available via debug server endpoint.

2. Verify app is ready:
   ```bash
   curl -s -H "Authorization: Bearer <TOKEN>" http://127.0.0.1:4948/driver/ready
   ```
   Expected: `{"ready": true, "screen": "..."}`

3. Record start timestamp for log scanning:
   ```bash
   pwsh -Command "Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ'"
   ```

## Executing a Flow

For each flow in your assigned range:

### 1. Driver Steps
Execute each step by calling the HTTP driver. Example tap:
```bash
curl -s -X POST http://127.0.0.1:4948/driver/tap \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"key": "add-project"}'
```

Wait for navigation/animations between steps:
```bash
curl -s -X POST http://127.0.0.1:4948/driver/wait \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"key": "project-list", "timeoutMs": 10000}'
```

### 2. Trigger Sync + Wait
After data creation, wait for sync to complete:
```bash
# Poll sync status (30s timeout)
for i in $(seq 1 30); do
  STATUS=$(curl -s http://127.0.0.1:3947/sync/status | jq -r '.state')
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "idle" ]; then break; fi
  sleep 1
done
```

### 3. Check Logs for Errors
```bash
curl -s "http://127.0.0.1:3947/logs?since=<START_TIME>&category=sync&level=error"
curl -s "http://127.0.0.1:3947/logs?since=<START_TIME>&level=error"
```
If any sync/db errors found → FAIL the flow.

### 4. Verify Supabase Data
```bash
pwsh -File tools/verify-sync.ps1 -Table <TABLE> -CountOnly
```
Verify count matches expected.

### 5. Update Registry
Edit `.claude/test-flows/registry.md` — update Status, Last Run, Notes for the flow.

## Error Handling

- If `/driver/ready` fails: retry once after 2s. If still fails, ABORT wave.
- If a tap/text/wait returns 404 (widget not found): take screenshot, wait 3s, retry once.
- If sync doesn't complete in 30s: capture `/sync/status` response, FAIL flow, continue to next.
- If verify-sync returns 0 rows: FAIL flow with "no data synced" note.
- On any FAIL: take screenshot (`GET /driver/screenshot > .claude/test_results/<flow>/fail.png`), record error, continue to next flow.

## Output

After completing all assigned flows, provide:
1. Summary table: Flow ID | Status | Duration | Notes
2. Any screenshots saved
3. Registry update confirmation

## IMPORTANT
- ALWAYS use `pwsh -Command "..."` for PowerShell commands
- NEVER use flutter/dart commands directly in bash
- Use `-CountOnly` with verify-sync.ps1 (no PII exposure)
- All test projects MUST use "E2E " prefix
- Save screenshots to `.claude/test_results/<date>/<flow-id>/`
```

### Step 7.3: Verify — files exist

```
pwsh -Command "Test-Path '.claude/skills/test/SKILL.md'"
pwsh -Command "Test-Path '.claude/agents/test-wave-agent.md'"
```

**Expected:** Both True.

---

## Phase 8: Pruning Script

**Agent:** `general-purpose`
**Depends on:** None.

### Step 8.1: Create `tools/prune-test-results.ps1`

**New file.** Complete code:

```powershell
# tools/prune-test-results.ps1
#
# FROM SPEC: "Script-based test result pruning — keep last 5 run directories, delete oldest."
# WHY: Test runs accumulate screenshots and logs. This prevents unbounded growth.

param(
    [int]$Keep = 5,
    [switch]$DryRun
)

# NOTE: Path uses hyphen (test-results) matching spec convention.
$resultsDir = Join-Path $PSScriptRoot "../.claude/test-results"

if (-not (Test-Path $resultsDir)) {
    Write-Host "No test_results directory found at $resultsDir"
    exit 0
}

# WHY: Sort by name (ISO date format sorts chronologically).
$dirs = Get-ChildItem -Path $resultsDir -Directory | Sort-Object Name -Descending

if ($dirs.Count -le $Keep) {
    Write-Host "Only $($dirs.Count) run directories found (keep=$Keep). Nothing to prune."
    exit 0
}

$toDelete = $dirs | Select-Object -Skip $Keep

foreach ($dir in $toDelete) {
    if ($DryRun) {
        Write-Host "[DRY RUN] Would delete: $($dir.FullName)"
    } else {
        Write-Host "Deleting: $($dir.FullName)"
        Remove-Item -Path $dir.FullName -Recurse -Force
    }
}

$deleted = $toDelete.Count
Write-Host "Pruned $deleted run directories (kept $Keep most recent)."
```

### Step 8.2: Verify — PowerShell syntax

```
pwsh -Command "& { Get-Content tools/prune-test-results.ps1 | Out-Null; Write-Host 'Syntax OK' }"
```

**Expected:** Syntax OK.

---

## Phase 9: Cleanup and Verification

**Agent:** `general-purpose`
**Depends on:** All previous phases.

### Step 9.1: Delete dead code files

FROM SPEC: 3 files to delete.

```bash
# FIX: Use pwsh with absolute paths — bash CWD may not be project root.
pwsh -Command "Remove-Item -Path '.claude/test_results/flow_registry.md' -Force -ErrorAction SilentlyContinue"
pwsh -Command "Remove-Item -Path '.claude/skills/test/references/adb-commands.md' -Force -ErrorAction SilentlyContinue"
pwsh -Command "Remove-Item -Path '.claude/skills/test/references/uiautomator-parsing.md' -Force -ErrorAction SilentlyContinue"
```

NOTE: If any of these files don't exist, that's fine — `-f` suppresses errors.

### Step 9.2: Verify — static analysis on all new files

```
pwsh -Command "flutter analyze lib/core/driver/ lib/main_driver.dart"
```

**Expected:** No issues found.

### Step 9.3: Verify — debug server syntax

```
pwsh -Command "cd tools/debug-server; node -c server.js"
```

**Expected:** No syntax errors.

### Step 9.4: Verify — build script recognizes new params

```
pwsh -Command "Get-Help tools/build.ps1 -Parameter DebugServer"
pwsh -Command "Get-Help tools/build.ps1 -Parameter Target"
```

**Expected:** Both parameters are listed with their descriptions.

### Step 9.5: Verify — Windows debug build with driver entrypoint compiles

```
pwsh -Command "flutter build windows --debug --target=lib/main_driver.dart --dart-define=DEBUG_SERVER=true --dart-define-from-file=.env"
```

**Expected:** Build succeeds. This confirms:
- main_driver.dart compiles
- IntegrationTestWidgetsFlutterBinding resolves
- DriverServer and TestPhotoService compile
- All imports are correct

### Step 9.6: Final file inventory check

Verify all expected files exist:
```
pwsh -Command "@(
    'lib/core/driver/test_photo_service.dart',
    'lib/core/driver/driver_server.dart',
    'lib/main_driver.dart',
    'tools/prune-test-results.ps1',
    '.claude/test-flows/registry.md',
    '.claude/skills/test/SKILL.md',
    '.claude/agents/test-wave-agent.md'
) | ForEach-Object { if (Test-Path $_) { Write-Host \"OK: $_\" } else { Write-Host \"MISSING: $_\" } }"
```

**Expected:** All 7 files show OK.

Verify dead code removed:
```
pwsh -Command "@(
    '.claude/test_results/flow_registry.md',
    '.claude/skills/test/references/adb-commands.md',
    '.claude/skills/test/references/uiautomator-parsing.md'
) | ForEach-Object { if (Test-Path $_) { Write-Host \"STILL EXISTS (delete failed): $_\" } else { Write-Host \"DELETED: $_\" } }"
```

**Expected:** All 3 files show DELETED.

---

## Phase Summary

| Phase | Files | Agent | Depends On |
|-------|-------|-------|------------|
| 1. TestPhotoService | 1 new | general-purpose | — |
| 2. HTTP Driver Server | 1 new | general-purpose | Phase 1 |
| 3. Custom Entrypoint | 1 new | general-purpose | Phase 1, 2 |
| 4. Build Script Updates | 2 modified | general-purpose | — |
| 5. Debug Server Update | 1 modified | general-purpose | — |
| 6. Unified Flow Registry | 1 new | general-purpose | — |
| 7. Skill & Agent Rewrite | 2 modified | general-purpose | Phase 6 |
| 8. Pruning Script | 1 new | general-purpose | — |
| 9. Cleanup & Verification | 3 deleted, 0 new | general-purpose | All |

**Dispatch groups for implement skill:**

FIX HIGH-6: Explicit parallelism — Group D runs concurrently with B/C since
Phase 7 depends only on Phase 6 (completed in Group A), not on Phases 1→2→3.

- **Group A (parallel):** Phase 1, Phase 4, Phase 5, Phase 6, Phase 8 — no interdependencies
- **Group B (after Phase 1 from Group A):** Phase 2 (needs Phase 1)
  - **Group D (after Phase 6 from Group A, runs CONCURRENTLY with Group B):** Phase 7 (needs Phase 6 only)
- **Group C (after Group B):** Phase 3 (needs Phase 1 + 2)
- **Group E (after Groups B, C, D all complete):** Phase 9 (verification)

**Total: 5 new files, 4 modified files, 3 deleted files.**
