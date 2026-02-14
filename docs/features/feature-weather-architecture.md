---
feature: weather
type: architecture
scope: Weather Integration & Condition Tracking (Placeholder)
updated: 2026-02-13
---

# Weather Feature Architecture

## Data Model

### Core Entities

| Entity | Fields | Type | Notes |
|--------|--------|------|-------|
| **WeatherCondition** | sunny, cloudy, overcast, rainy, snow, windy | Enum | Conditions used in daily entries |
| **WeatherData** | location, temperature, condition, humidity, windSpeed, precipitation, timestamp | Value Object | Current weather (API response) |

### Key Models

**WeatherCondition** (Enum):
- Used in DailyEntry to record observed weather during job site visit
- Values: sunny, cloudy, overcast, rainy, snow, windy
- Manually selected by inspector (not from API)

**WeatherData** (API Response):
- `location`: Location name (e.g., project location)
- `temperature`: Current temperature (Fahrenheit or Celsius)
- `condition`: Current condition string (e.g., "Partly Cloudy")
- `humidity`: Relative humidity percentage
- `windSpeed`: Wind speed (mph or km/h)
- `precipitation`: Precipitation amount (if any)
- `timestamp`: When weather was fetched

## Relationships

### Entry → Weather (1-1)
```
DailyEntry
    └─→ weather: WeatherCondition? (enum; what inspector observed)
        ├─→ Manually selected by inspector
        └─→ Recorded with entry for documentation
```

### Location → Current Weather (1-1)
```
Location (GPS coordinates)
    └─→ Current Weather (fetched from API)
        ├─→ Temperature, conditions, wind
        └─→ Real-time data (cached locally)
```

## Repository Pattern

### WeatherService (Cross-cutting)

**Location**: `lib/features/weather/services/weather_service.dart`

```dart
class WeatherService {
  // Fetch weather
  Future<WeatherData?> getCurrentWeather(String location)
  Future<WeatherData?> getWeatherByCoordinates(double latitude, double longitude)
  Future<List<WeatherData>> getForecast(String location, {int days = 5})

  // Caching
  Future<WeatherData?> getCachedWeather(String location)
  Future<void> saveCachedWeather(String location, WeatherData data)

  // Status
  Future<bool> isNetworkAvailable()
}
```

**Implementation Notes**:
- Currently **placeholder** - returns mock data
- Future implementation will integrate with weather API
- Implements caching to reduce API calls
- Gracefully handles offline scenarios

## State Management

**No dedicated provider** (placeholder feature).

Future implementation would include:

```dart
class WeatherProvider extends ChangeNotifier {
  // State
  WeatherData? _currentWeather;
  bool _isLoading = false;
  String? _error;

  // Methods
  Future<void> fetchWeather(double latitude, double longitude)
  Future<void> fetchWeatherByLocation(String location)
}
```

### Initialization Lifecycle

```
Dashboard Loaded
    ↓
Optional: WeatherProvider.fetchWeather(lat, lng)
    ├─→ _isLoading = true
    │
    ├─→ WeatherService.getWeatherByCoordinates(lat, lng)
    │   ├─→ If network: fetch from API
    │   ├─→ Cache result locally
    │   └─→ Return WeatherData
    │
    ├─→ If error or offline:
    │   ├─→ WeatherService.getCachedWeather()
    │   └─→ Display cached data
    │
    └─→ _currentWeather = weather
        _isLoading = false
        notifyListeners() → displays weather
```

## Offline Behavior

**NOT offline-capable**. Feature requires network for weather APIs.

### Read Path
- Current weather: Requires network API call
- Cached weather: Can be displayed if cached locally
- Weather from entries: Historical data from DailyEntry.weather enum

### Write Path
- Weather conditions captured with entries (offline)
- Cached weather data saved locally if available

### Graceful Degradation
- API error or offline: Display cached weather + "offline" indicator
- No cached data: Show entry weather enum or "weather unavailable"
- Network recovers: Refresh weather automatically

## Testing Strategy

### Unit Tests (Service-level)
- **WeatherService**: Mock API responses, verify parsing
- **Caching**: Save/load cached weather, verify persistence
- **Offline fallback**: Verify cached data returned when API unavailable

Location: `test/features/weather/services/weather_service_test.dart`

### Widget Tests (Provider-level, future)
- **WeatherProvider**: Fetch weather, verify state updates
- **Error handling**: Network error displays fallback UI
- **Offline display**: Show cached weather when unavailable

Location: `test/features/weather/presentation/providers/`

### Integration Tests
- **Dashboard weather**: Load dashboard → fetch weather → display
- **Entry weather**: Capture entry weather condition → save with entry
- **Offline resilience**: Disable network → display cached weather + offline indicator

Location: `test/features/weather/integration/`

### Test Coverage
- ≥ 90% for service (API integration)
- ≥ 80% for provider (state management, future)
- 70% for screens (error handling, offline display)

## Performance Considerations

### Target Response Times
- Fetch weather: 1-3 seconds (API-dependent)
- Display cached weather: < 100 ms (local read)
- Cache lookup: < 50 ms (local operation)

### Memory Constraints
- Weather data in memory: ~1-2 KB
- Cached weather (multi-location): ~10 KB per location

### Optimization Opportunities
- Cache weather for 1 hour (reduce API calls)
- Batch weather requests (fetch for all locations once)
- Periodic background refresh (if location changes)
- Pre-fetch forecast when connectivity available

## File Locations

```
lib/features/weather/
├── services/
│   ├── services.dart
│   └── weather_service.dart
│
└── weather.dart                      # Feature entry point

lib/core/models/
└── weather_models.dart               # Shared weather data models
```

### Import Pattern

```dart
// Within weather feature
import 'package:construction_inspector/features/weather/services/weather_service.dart';

// Barrel export
import 'package:construction_inspector/features/weather/weather.dart';

// From entries (weather enum)
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';
```

## Future Implementation Notes

### API Selection Criteria
- No API key required (or easy registration)
- Free tier adequate for app usage
- Rate limits acceptable (≥ 1000 calls/day)
- Reliable uptime (99.9%+)
- JSON response format

### Candidate APIs
- OpenWeatherMap (free tier: 60 calls/minute)
- Weather.gov (US only, no API key required)
- Open-Meteo (free, no registration, 100k requests/day)

### Caching Strategy
- Cache weather for 1 hour per location
- Store in SQLite weather_cache table
- Invalidate on explicit refresh or 1-hour TTL
- Persist across app kills

### Sync Behavior
- Weather data is read-only (no upload)
- Historical weather stored in entries (WeatherCondition enum)
- No sync of weather API data

### Alerts (Future Enhancement)
- Severe weather warnings (wind > 40 mph, rain/snow, etc.)
- Notification when conditions change significantly
- Alert storage in SQLite for historical reference

