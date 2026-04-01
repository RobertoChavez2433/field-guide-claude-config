# Pattern: Entrypoint Initialization

## How We Do It
The app has two entrypoints: `main.dart` (production) and `main_driver.dart` (test driver). Both follow the same pattern: zone setup → `AppInitializer.initialize()` → consent/support factory → auth listener → AppRouter construction → `runApp()`. The duplication between them is the core problem the spec addresses. Both call `createConsentAndSupportProviders()` to share factory logic (H1 fix already applied), but the auth listener, consent loading, Sentry gate, and AppRouter construction are still duplicated.

## Exemplars

### main.dart (`lib/main.dart:81-187`)
```dart
Future<void> main() async {
  await SentryFlutter.init(
    (options) {
      options.dsn = const String.fromEnvironment('SENTRY_DSN');
      options.tracesSampleRate = 0.1;
      options.beforeSendTransaction = _beforeSendTransaction;
      options.beforeSend = _beforeSendSentry;
      options.attachScreenshot = false;
      options.attachViewHierarchy = false;
    },
    appRunner: () async {
      WidgetsFlutterBinding.ensureInitialized();
      runZonedGuarded(
        () => _runApp(),
        (error, stack) { Logger.error(...); },
        zoneSpecification: Logger.zoneSpec(),
      );
    },
  );
}

Future<void> _runApp() async {
  final deps = await AppInitializer.initialize(logDirOverride: kAppLogDirOverride);
  Analytics.trackAppLaunch();

  // Consent/support factory (shared with main_driver.dart)
  final consentSupport = createConsentAndSupportProviders(...);
  final consentProvider = consentSupport.consentProvider;
  consentProvider.loadConsentState();
  if (consentProvider.hasConsented) enableSentryReporting();

  // Auth listener (DUPLICATED in main_driver.dart)
  bool wasAuth = deps.authProvider.isAuthenticated;
  deps.authProvider.addListener(() { ... });

  // AppRouter construction (DUPLICATED in main_driver.dart)
  final appRouter = AppRouter(authProvider: deps.authProvider, consentProvider: consentProvider);

  runApp(ConstructionInspectorApp(
    providers: buildAppProviders(deps),
    appRouter: appRouter,
    consentProvider: consentProvider,
    supportProvider: supportProvider,
  ));
}
```

### main_driver.dart (`lib/main_driver.dart:30-121`)
```dart
Future<void> main() async {
  runZonedGuarded(
    () async {
      WidgetsFlutterBinding.ensureInitialized();
      await _runApp();
    },
    (error, stack) { Logger.error(...); },
    zoneSpecification: Logger.zoneSpec(),
  );
}

Future<void> _runApp() async {
  final baseDeps = await AppInitializer.initialize(logDirOverride: kAppLogDirOverride);

  // Driver-specific: swap PhotoService
  final testPhotoService = TestPhotoService(baseDeps.photoRepository);
  final deps = baseDeps.copyWith(photoService: testPhotoService);

  // Driver-specific: start DriverServer
  final driverServer = DriverServer(testPhotoService: testPhotoService, ...);
  await driverServer.start();

  // Same consent/support factory as main.dart
  final consentSupport = createConsentAndSupportProviders(...);
  consentProvider.loadConsentState();
  if (consentProvider.hasConsented) enableSentryReporting();

  // DUPLICATED auth listener (mirrors main.dart)
  bool wasAuth = deps.authProvider.isAuthenticated;
  deps.authProvider.addListener(() { ... });

  // DUPLICATED AppRouter construction
  final appRouter = AppRouter(authProvider: deps.authProvider, consentProvider: consentProvider);

  runApp(RepaintBoundary(
    key: driverScreenshotKey,
    child: ConstructionInspectorApp(...),
  ));
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| AppInitializer.initialize | app_initializer.dart:361 | `static Future<AppDependencies> initialize({String logDirOverride})` | Shared initialization |
| createConsentAndSupportProviders | consent_support_factory.dart:29 | `ConsentSupportResult createConsentAndSupportProviders({...})` | Consent/support provider factory |
| buildAppProviders | app_providers.dart:37 | `List<SingleChildWidget> buildAppProviders(AppDependencies deps)` | Provider list assembly |
| _beforeSendSentry | main.dart:28 | `SentryEvent? _beforeSendSentry(SentryEvent event, Hint hint)` | PII scrubbing for Sentry |
| _beforeSendTransaction | main.dart:68 | `SentryTransaction? _beforeSendTransaction(SentryTransaction tx)` | Consent-gate for Sentry transactions |
| enableSentryReporting | sentry_consent.dart:16 | `void enableSentryReporting()` | Enable Sentry after consent |

## Imports
```dart
import 'package:construction_inspector/core/di/app_initializer.dart';
import 'package:construction_inspector/core/di/app_providers.dart';
import 'package:construction_inspector/core/router/app_router.dart';
import 'package:construction_inspector/core/config/sentry_consent.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/core/analytics/analytics.dart';
import 'package:construction_inspector/features/settings/di/consent_support_factory.dart';
import 'package:construction_inspector/features/settings/presentation/providers/consent_provider.dart';
import 'package:construction_inspector/features/settings/presentation/providers/support_provider.dart';
import 'package:construction_inspector/features/settings/presentation/providers/theme_provider.dart';
```
