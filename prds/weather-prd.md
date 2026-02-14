# Weather PRD

## Purpose
Weather conditions directly affect construction work and must be documented in daily inspection reports. This feature automatically captures high/low temperatures and weather conditions using the inspector's GPS location, eliminating manual lookups and ensuring accurate, timestamped weather records on every daily entry.

## Core Capabilities
- Fetch daily weather data (condition, high temperature, low temperature) from Open-Meteo API using GPS coordinates
- Auto-fetch weather when creating a new daily entry (configurable in Settings)
- Convert WMO weather codes to human-readable conditions (Clear, Partly Cloudy, Foggy, Drizzle, Rain, Snow, Thunderstorm)
- Convert Celsius API responses to Fahrenheit for US construction industry standard
- GPS location detection with graceful permission handling and timeout
- Mock weather support for testing (bypasses GPS and API calls via TestModeConfig)

## Data Model
- Primary entity: `WeatherData` (in-memory class, not a standalone SQLite table)
- Key fields: `condition` (String), `tempHigh` (int, Fahrenheit), `tempLow` (int, Fahrenheit)
- Storage: Weather data is persisted as fields on the `daily_entries` table (`weather_condition`, `temp_high`, `temp_low`), not in a separate weather table
- Sync: Syncs with the parent daily entry record (no independent sync)

## User Flow
When an inspector creates a new daily entry, the app automatically fetches weather for the current GPS location and date (if auto-fetch is enabled in Settings). The weather data populates the entry's weather fields. Inspectors can manually refresh weather or override values. Weather appears in the daily entry header and is included in generated PDF reports.

## Offline Behavior
Weather fetch requires network connectivity and GPS access. When offline, the weather fields remain empty or retain previously fetched values. Inspectors can manually enter weather data at any time. The auto-fetch setting is stored locally in SharedPreferences. Mock mode (for testing) returns hardcoded Denver, CO weather without network or GPS.

## Dependencies
- Features: entries (weather data attaches to daily entries), settings (auto-fetch toggle)
- Packages: `http` (API calls), `geolocator` (GPS location), `dart:convert` (JSON parsing)

## Owner Agent
backend-data-layer-agent (WeatherService, WeatherData model)
