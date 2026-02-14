# Weather Constraints

**Feature**: Weather & Environmental Data
**Scope**: All code in `lib/features/weather/` and weather integration logic

---

## Hard Rules (Violations = Reject)

### Placeholder Service (No Real API Yet)
- ✗ No external weather API integration (OpenWeather, WeatherAPI, etc.) until explicitly scoped
- ✓ Weather feature is placeholder: Stub service returning mock data
- ✓ Service interface defined, ready for API integration when needed
- ✗ No hardcoding API keys or endpoints

**Why**: Phase 1 focuses on offline-first features; weather API deferred to Phase 2.

### Manual Entry in Entries
- ✗ No auto-fetching weather conditions at entry creation
- ✓ Inspector can optionally add weather notes (text field) to entries
- ✓ Supported fields: temperature (manual), conditions (dropdown: sunny/cloudy/rainy), wind_speed (manual, optional)
- ✗ No blocking entry creation due to missing weather (weather optional)

**Why**: Offline-first; network required for real-time API calls.

### Weather-Entry Association
- ✓ Entry can reference weather conditions (optional entry_weather record)
- ✓ Weather conditions immutable after entry SUBMITTED (snapshot at observation time)
- ✗ No changing weather data after entry marked SUBMITTED

**Why**: Audit trail; weather conditions must match work performed.

### No Persistence Requirement for Weather History
- ✗ No analytics/reporting on weather trends (future scope)
- ✓ Weather stored only when attached to entries (no standalone weather table)
- ✗ No syncing weather independently (synced as part of entry)

**Why**: Weather is contextual metadata for entries; not analyzed separately yet.

---

## Soft Guidelines (Violations = Discuss)

### Performance Targets
- Weather field load (if API integrated): < 1 second (with fallback to manual)
- Manual entry: < 100ms
- Weather condition render: < 100ms

### Future API Integration
- When API added, recommend: Caching results (same conditions for 1+ hour likely)
- When API added, recommend: Fallback to manual entry if API unavailable
- When API added, recommend: Request permission for location (GPS) to enable auto-fetch

### Test Coverage
- Target: >= 80% for placeholder service
- After API integration: >= 85%

---

## Integration Points

- **Depends on**:
  - `entries` (weather conditions attached to entries)
  - `sync` (weather data synced as part of entry submission)

- **Required by**:
  - `entries` (optional weather association)
  - `dashboard` (current conditions display, optional)

---

## Performance Targets

- Weather field load: < 1 second (with fallback)
- Manual entry: < 100ms
- Render conditions: < 100ms

---

## Testing Requirements

- >= 80% test coverage for placeholder service
- Unit tests: Manual weather entry validation, immutability after submission
- Integration tests: Create entry with weather→submit→verify immutable
- Edge cases: Missing optional fields (temperature blank, conditions not selected), corrupted weather data
- Placeholder-to-API migration path: Service interface supports both mock and real API seamlessly

---

## Reference

- **Architecture**: `docs/features/feature-weather-architecture.md`
- **Shared Rules**: `architecture-decisions/data-validation-rules.md`
- **Sync Integration**: `architecture-decisions/sync-constraints.md`
