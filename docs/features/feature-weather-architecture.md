---
feature: weather
type: architecture
scope: Weather Integration (Open-Meteo API)
updated: 2026-03-30
---

# Weather Feature Architecture

## Pattern

Service-first feature. No data layer and no screens. Consists of a domain interface, a single service implementation, a lightweight presentation provider, and DI wiring.

```
lib/features/weather/
├── di/
│   └── weather_providers.dart      # Provider registration (Tier 4)
├── domain/
│   ├── domain.dart                 # Barrel: exports WeatherServiceInterface
│   └── weather_service_interface.dart  # Abstract contract
├── presentation/
│   └── providers/
│       └── weather_provider.dart   # ChangeNotifier wrapper for fetch/cached state
├── services/
│   ├── services.dart               # Barrel: exports WeatherService + WeatherData
│   └── weather_service.dart        # Implementation + WeatherData model
└── weather.dart                    # Feature barrel (re-exports domain + services)
```

## Layer Structure

| Layer | File | Contents |
|-------|------|----------|
| Domain | `domain/weather_service_interface.dart` | `WeatherServiceInterface` (abstract) |
| Service | `services/weather_service.dart` | `WeatherService`, `WeatherData` |
| Presentation | `presentation/providers/weather_provider.dart` | `WeatherProvider` fetch/cached UI state |
| DI | `di/weather_providers.dart` | `weatherProviders()` function |

There is no `data/`, no screen layer, and no `domain/usecases/` or `domain/repositories/` subdirectory.

## Key Classes

### WeatherServiceInterface

Abstract contract in `domain/weather_service_interface.dart`. Enables mock substitution in tests.

```dart
abstract class WeatherServiceInterface {
  Future<WeatherData?> fetchWeatherForCurrentLocation(DateTime date);
  Future<WeatherData?> fetchWeather(double lat, double lon, DateTime date);
}
```

### WeatherData

Value object defined in `services/weather_service.dart` (not a separate models file):

```dart
class WeatherData {
  final String condition;   // Human-readable (e.g., "Clear", "Rain")
  final int tempHigh;       // Fahrenheit
  final int tempLow;        // Fahrenheit
}
```

WMO weather codes are converted to condition strings via `WeatherService.weatherCodeToCondition(int code)`. Temperature is fetched in Celsius and converted via `WeatherService.celsiusToFahrenheit(double celsius)`.

### WeatherService

Concrete implementation in `services/weather_service.dart`. Calls the **Open-Meteo API** (free, no API key, `https://api.open-meteo.com/v1/forecast`).

Key methods:
- `fetchWeather(double lat, double lon, DateTime date)` — fetches daily high/low and weather code for a specific date and coordinates
- `fetchWeatherForCurrentLocation(DateTime date)` — resolves GPS via `Geolocator`, then delegates to `fetchWeather`
- `getCurrentLocation()` — handles location permission checks; returns `null` on denial or timeout (10s)

Test mode: when `TestModeConfig.useMockWeather` is true, both `getCurrentLocation()` and `fetchWeather()` return mock data (Denver, CO coordinates; configurable condition/temps from `TestModeConfig`), bypassing network and permission prompts.

API request fields: `temperature_2m_max`, `temperature_2m_min`, `weather_code` (daily). Timeout: 10 seconds.

## DI Wiring

`weather_providers.dart` registers a single `Provider<WeatherService>.value` at Tier 4 of the app provider tree:

```dart
List<SingleChildWidget> weatherProviders({
  required WeatherService weatherService,
}) => [
  Provider<WeatherService>.value(value: weatherService),
];
```

`WeatherService` is instantiated in `lib/core/bootstrap/app_initializer.dart` as part of `FeatureDeps` and passed into `app_providers.dart` via `weatherProviders(weatherService: deps.weatherService)`.

## Relationships

### Entries → Weather (primary consumer)

`entry_editor_screen.dart` calls `context.read<WeatherService>()` and invokes `fetchWeatherForCurrentLocation(date)` in `_autoFetchWeather()` to pre-fill weather conditions when creating or editing a daily entry. The `WeatherData` result (condition string, high/low temps) is applied directly to entry state.

### Test coverage

`test/services/weather_service_test.dart` covers weather-code conversion and temperature conversion logic. Runtime consumers use `WeatherProvider` when they need cached fetch state.

## No Local Storage / No Sync

Weather data is not persisted to SQLite and is not part of the sync system. Each fetch is live from the Open-Meteo API (or mock in test mode). There is no cache table, no `change_log` entry, and no Supabase upload path.

## Offline Behavior

If GPS is unavailable (permission denied, services off, or timeout), `getCurrentLocation()` returns `null` and no fetch is attempted. If the API call fails or times out (10 s), `fetchWeather()` returns `null`. The caller (`entry_editor_screen.dart`) handles `null` gracefully — weather fields remain empty and the inspector can fill them manually.

## Import Pattern

```dart
// Full feature barrel (domain + service)
import 'package:construction_inspector/features/weather/weather.dart';

// Service only
import 'package:construction_inspector/features/weather/services/weather_service.dart';

// Interface only (for test doubles)
import 'package:construction_inspector/features/weather/domain/weather_service_interface.dart';
```
