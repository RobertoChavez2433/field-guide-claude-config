---
feature: weather
type: overview
scope: Weather Integration & Condition Tracking
updated: 2026-03-30
---

# Weather Feature Overview

## Purpose

The Weather feature fetches current weather conditions (temperature, condition string) for a given GPS coordinate and date. It is a thin service-only feature with no screens, no local data layer, and no sync involvement. Weather data is fetched on demand via the Open-Meteo API and surfaced to the entries feature when an inspector creates or edits a daily entry.

## Key Responsibilities

- **Weather Fetching**: Retrieve condition, high temperature, and low temperature from Open-Meteo for a given lat/lon and date
- **GPS Resolution**: Obtain the device's current position via `geolocator` and pass coordinates to the API call
- **Unit Conversion**: Convert Celsius API values to Fahrenheit and WMO weather codes to human-readable strings
- **Test Mode Support**: Return mock weather data when `TestModeConfig.useMockWeather` is true, bypassing network and GPS permissions

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/weather/domain/weather_service_interface.dart` | Domain contract — `WeatherServiceInterface` abstract class |
| `lib/features/weather/services/weather_service.dart` | Concrete implementation — `WeatherService` + `WeatherData` model |
| `lib/features/weather/di/weather_providers.dart` | DI wiring — `weatherProviders()` registers `WeatherService` via Provider |
| `lib/features/weather/weather.dart` | Feature barrel export |

### Class Summary

- `WeatherServiceInterface` — abstract; declares `fetchWeather(lat, lon, date)` and `fetchWeatherForCurrentLocation(date)`
- `WeatherService implements WeatherServiceInterface` — concrete service backed by Open-Meteo REST API
- `WeatherData` — simple value object with `condition`, `tempHigh`, `tempLow`
- `weatherProviders({required WeatherService weatherService})` — returns a `List<SingleChildWidget>` registering `WeatherService` as a `Provider<WeatherService>.value`

## Integration Points

**Depends on:** nothing (no cross-feature dependencies at runtime)

**Required by:**
- `entries` — `entry_editor_screen.dart` reads `WeatherService` to auto-populate weather fields when creating/editing a daily entry

## Offline Behavior

Weather fetching is **not offline-capable**. The service returns `null` when the network is unavailable or GPS is denied. Callers are expected to handle null gracefully. No caching layer exists; weather data is not stored in SQLite.

## Edge Cases & Limitations

- **Network Dependency**: Requires internet connection; silently returns `null` on timeout or non-200 responses (10-second timeout)
- **GPS Permissions**: Returns `null` if location services are disabled or permission denied/denied-forever
- **Test Mode**: `TestModeConfig.useMockWeather` bypasses both GPS and network, returning a fixed mock location (Denver, CO) and configurable mock weather values
- **No Dashboard Integration**: Dashboard does not currently consume the weather service
- **No Data Persistence**: `WeatherData` is ephemeral; it is not written to SQLite or Supabase
