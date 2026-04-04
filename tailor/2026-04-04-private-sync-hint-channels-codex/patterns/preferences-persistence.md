# Pattern: Preferences Persistence

## How We Do It

The app uses `PreferencesService` (a `ChangeNotifier` wrapping `SharedPreferences`) for persisting simple key-value data locally. It follows a key-constant pattern with typed getters/setters. For the `device_install_id`, this service is the natural home — it already stores device-scoped preferences like `keyGaugeNumber` and `keyPasswordRecoveryActive`. Alternatively, `FlutterSecureStorage` could be used for the device_install_id if we want it to survive app data clears (but SharedPreferences is simpler and sufficient since the server generates a new channel on re-registration anyway).

## Exemplars

### PreferencesService (`lib/shared/services/preferences_service.dart:11`)

```dart
class PreferencesService extends ChangeNotifier {
  SharedPreferences? _prefs;
  bool _initialized = false;

  // Preference keys
  static const String keyGaugeNumber = 'gauge_number';
  static const String keyLastRoute = 'last_route_location';
  static const String keyDebugLogDir = 'debug_log_dir';
  static const String keyPasswordRecoveryActive = 'password_recovery_active';

  Future<void> initialize() async {
    if (_initialized) return;
    _prefs = await SharedPreferences.getInstance();
    _initialized = true;
    notifyListeners();
  }

  // Typed getter/setter pattern:
  String? get gaugeNumber {
    _ensureInitialized();
    return _prefs!.getString(keyGaugeNumber);
  }

  Future<void> setGaugeNumber(String value) async {
    _ensureInitialized();
    await _prefs!.setString(keyGaugeNumber, value);
    notifyListeners();
  }

  // Generic accessors for migration compatibility:
  String? getString(String key) { ... }
  Future<void> setString(String key, String value) async { ... }
}
```

**Pattern for device_install_id:**
```dart
static const String keyDeviceInstallId = 'device_install_id';

String get deviceInstallId {
  _ensureInitialized();
  var id = _prefs!.getString(keyDeviceInstallId);
  if (id == null || id.isEmpty) {
    id = const Uuid().v4();
    _prefs!.setString(keyDeviceInstallId, id);
  }
  return id;
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `initialize()` | `preferences_service.dart:29` | `Future<void> initialize()` | Must call before any access |
| `getString(key)` | `preferences_service.dart:177` | `String? getString(String key)` | Generic string read |
| `setString(key, value)` | `preferences_service.dart:183` | `Future<void> setString(String key, String value)` | Generic string write |
| `getBool(key)` | `preferences_service.dart:189` | `bool? getBool(String key)` | Generic bool read |

## Imports

```dart
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter/foundation.dart';
import 'package:construction_inspector/core/logging/logger.dart';
```
