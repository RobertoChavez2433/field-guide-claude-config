---
feature: locations
type: architecture
scope: Job Site Location Management with GPS
updated: 2026-02-13
---

# Locations Feature Architecture

## Data Model

### Core Entities

| Entity | Fields | Type | Notes |
|--------|--------|------|-------|
| **Location** | id, projectId, name, description, address, latitude, longitude, createdAt, updatedAt | Model | Job site location with GPS |

### Key Models

**Location**:
- `projectId`: Required; locations scoped to projects
- `name`: Display name (e.g., "Station 12+50", "Bridge Approach")
- `description`: Optional additional details (e.g., "Right of way work area")
- `address`: Optional street address or landmark
- `latitude/longitude`: Optional GPS coordinates (nullable if GPS unavailable)
- `createdAt/updatedAt`: Lifecycle timestamps

## Relationships

### Project → Locations (1-N)
```
Project (1)
    ↓
Location[] (multiple job site locations within project)
    ├─→ Referenced in DailyEntry (entryId → locationId)
    ├─→ Tagged in Photo (photoId → locationId)
    └─→ Metadata: address, GPS, description
```

### Entry → Location (N-1)
```
DailyEntry
    ├─→ locationId (required; which site this entry covers)
    ↓
Location (specific job site)
    └─→ GPS, address, name
```

## Repository Pattern

### LocationRepository

**Location**: `lib/features/locations/data/repositories/location_repository.dart`

```dart
class LocationRepository {
  // CRUD
  Future<Location> create(Location location)
  Future<Location?> getById(String id)
  Future<List<Location>> listByProject(String projectId)
  Future<void> update(Location location)
  Future<void> delete(String id)

  // Specialized Queries
  Future<int> countByProject(String projectId)
  Future<Location?> findNearest(double latitude, double longitude, {double radiusKm = 1})
}
```

## State Management

### Provider Type: ChangeNotifier

**LocationProvider** (`lib/features/locations/presentation/providers/location_provider.dart`):

```dart
class LocationProvider extends ChangeNotifier {
  // State
  List<Location> _locations = [];
  Location? _currentLocation;
  bool _isLoading = false;
  String? _error;

  // Getters
  List<Location> get locations => _locations;
  Location? get currentLocation => _currentLocation;
  bool get isLoading => _isLoading;
  String? get error => _error;

  // Methods
  Future<void> loadByProject(String projectId)
  Future<void> createLocation(Location location)
  Future<void> updateLocation(Location location)
  Future<void> deleteLocation(String id)
  Future<Location?> captureCurrentLocation(String projectId)
}
```

### Initialization Lifecycle

```
Project Setup Screen Loaded
    ↓
initState() calls LocationProvider.loadByProject(projectId)
    ├─→ _isLoading = true → shows skeleton
    │
    ├─→ Repository.listByProject(projectId)
    │   └─→ SQLite query with projectId = ?
    │
    └─→ _locations = results
        _isLoading = false
        notifyListeners() → displays location list
```

### Location Creation Flow

```
User taps "Add Location" button
    ↓
Location creation dialog opened
    ├─→ User enters: name, description, address
    │
    ├─→ Optional: User taps "Capture GPS"
    │   ├─→ Device GPS service queries current position
    │   ├─→ latitude/longitude populated from GPS
    │   └─→ User can confirm or edit coordinates
    │
    ├─→ createLocation(location) called
    │   ├─→ LocationRepository.create()
    │   │   └─→ SQLite INSERT
    │   │
    │   ├─→ _locations.add(newLocation)
    │   └─→ notifyListeners() → list refreshes
    │
    └─→ Dialog closes → location visible in list
```

## Offline Behavior

**Fully offline**: Location creation, editing, GPS capture, and queries happen entirely offline. GPS coordinate capture requires device GPS (not cloud-dependent).

### Read Path (Offline)
- Location list queries SQLite by projectId
- No cloud dependency

### Write Path (Offline)
- Location creation/updates written immediately to SQLite
- GPS coordinates persisted locally
- No sync status tracking (locations are static reference data)

## Testing Strategy

### Unit Tests (Model-level)
- **Location**: Constructor, copyWith, toMap/fromMap
- **GPS coordinates**: Nullable fields, decimal precision
- **Address handling**: Optional field serialization

Location: `test/features/locations/data/models/location_test.dart`

### Repository Tests (Data-level)
- **CRUD operations**: Create, read, update, delete locations
- **Query filters**: List by projectId, count by project
- **GPS queries**: Find nearest location (radius-based)
- **Offline behavior**: All tests mock database

Location: `test/features/locations/data/repositories/location_repository_test.dart`

### Widget Tests (Provider-level)
- **LocationProvider**: Mock repository, trigger operations, verify state
- **Location list**: Verify locations displayed by project
- **GPS capture**: Mock GPS service, verify coordinates captured
- **Selection**: Tap location → currentLocation updated

Location: `test/features/locations/presentation/providers/location_provider_test.dart`

### Integration Tests
- **Create with GPS**: Add location → capture GPS → save → verify in database
- **Edit**: Load location → change address → save → verify persisted
- **Navigation**: Locations screen → entry wizard → select location → verify selected

Location: `test/features/locations/presentation/integration/`

### Test Coverage
- ≥ 90% for repository (critical data)
- ≥ 85% for provider (state management)
- 70% for screens (navigation testing)

## Performance Considerations

### Target Response Times
- Load 10 locations: < 300 ms
- Create location: < 100 ms
- Capture GPS: 1-3 seconds (device-dependent)
- Find nearest: < 500 ms (Haversine calculation)

### Memory Constraints
- Location in memory: ~200 bytes per location
- Location list: ~2 KB for 10 locations

### Optimization Opportunities
- Cache locations list (avoid repeated queries)
- Batch GPS updates (if capture multiple locations)
- Index on projectId (fast project-scoped queries)
- Lazy-load GPS details (only when viewing location)

## File Locations

```
lib/features/locations/
├── data/
│   ├── models/
│   │   ├── models.dart
│   │   └── location.dart
│   │
│   ├── datasources/
│   │   ├── local/
│   │   │   ├── local.dart
│   │   │   └── location_local_datasource.dart
│   │   └── remote/
│   │       ├── remote.dart
│   │       └── location_remote_datasource.dart
│   │
│   └── repositories/
│       ├── repositories.dart
│       └── location_repository.dart
│
├── presentation/
│   ├── providers/
│   │   ├── providers.dart
│   │   └── location_provider.dart
│   │
│   └── presentation.dart
│
└── locations.dart                    # Feature entry point

lib/core/database/
└── database_service.dart             # SQLite schema for locations table

services/
└── location/                         # GPS/location service (cross-cutting)
    └── location_service.dart
```

### Import Pattern

```dart
// Within locations feature
import 'package:construction_inspector/features/locations/data/models/location.dart';
import 'package:construction_inspector/features/locations/data/repositories/location_repository.dart';
import 'package:construction_inspector/features/locations/presentation/providers/location_provider.dart';

// Cross-cutting service
import 'package:construction_inspector/services/location/location_service.dart';

// Barrel export
import 'package:construction_inspector/features/locations/locations.dart';
```

