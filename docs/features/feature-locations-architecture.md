---
feature: locations
type: architecture
scope: Job Site Location Management
updated: 2026-03-30
---

# Locations Feature Architecture

## Overview

Simple CRUD feature that manages named job-site locations scoped to a project. No dedicated screens — UI is embedded in entries and projects features. Single model, single repository.

## Directory Structure

```
lib/features/locations/
├── data/
│   ├── models/
│   │   ├── location.dart
│   │   └── models.dart
│   ├── datasources/
│   │   ├── local/
│   │   │   ├── location_local_datasource.dart
│   │   │   └── local.dart
│   │   ├── remote/
│   │   │   ├── location_remote_datasource.dart
│   │   │   └── remote.dart
│   │   └── datasources.dart
│   ├── repositories/
│   │   ├── location_repository_impl.dart
│   │   └── repositories.dart
│   └── data.dart
├── domain/
│   ├── repositories/
│   │   ├── location_repository.dart      # Abstract interface
│   │   └── repositories.dart
│   └── domain.dart
├── presentation/
│   ├── providers/
│   │   ├── location_provider.dart
│   │   └── providers.dart
│   └── presentation.dart
├── di/
│   └── locations_providers.dart
└── locations.dart                        # Barrel: re-exports data + domain + presentation
```

## Data Layer

### Model: `Location`

File: `lib/features/locations/data/models/location.dart`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `String` | UUID, auto-generated |
| `projectId` | `String` | Required; scopes location to a project |
| `name` | `String` | Required display name |
| `description` | `String?` | Optional details |
| `latitude` | `double?` | Nullable GPS coordinate |
| `longitude` | `double?` | Nullable GPS coordinate |
| `createdAt` | `DateTime` | Auto-set on construction |
| `updatedAt` | `DateTime` | Auto-set; refreshed in `copyWith` |
| `createdByUserId` | `String?` | Supabase auth user ID |

No `address` field — the old doc was inaccurate. GPS coordinates are optional (device GPS may be unavailable).

### Datasources

**`LocationLocalDatasource`** (`data/datasources/local/location_local_datasource.dart`)
- Extends `ProjectScopedDatasource<Location>`
- Table: `locations`, ordered `name ASC`
- Extra method: `search(String projectId, String query)` — name LIKE query within project
- Inherits: `getById`, `getAll`, `getByProjectId`, `insert`, `update`, `delete`, `deleteByProjectId`, `getCountByProject`, `insertAll`, `getCount`, `getPaged`, `getByProjectIdPaged`

**`LocationRemoteDatasource`** (`data/datasources/remote/location_remote_datasource.dart`)
- Extends `BaseRemoteDatasource<Location>`
- Table: `locations`
- Extra method: `getByProjectId(String projectId)` — Supabase query ordered by name
- Currently unused at runtime (sync is change-log driven); wired for future direct-fetch

## Domain Layer

### Repository Interface: `LocationRepository`

File: `lib/features/locations/domain/repositories/location_repository.dart`

```dart
abstract class LocationRepository implements ProjectScopedRepository<Location> {
  Future<List<Location>> search(String projectId, String query);
  Future<RepositoryResult<Location>> updateLocation(Location location);
  Future<void> deleteByProjectId(String projectId);
  Future<void> insertAll(List<Location> locations);
}
```

Inherits from `ProjectScopedRepository<Location>` (shared base), which provides: `getById`, `getAll`, `getByProjectId`, `save`, `create`, `update`, `delete`, `getCountByProject`, `getCount`, `getPaged`, `getByProjectIdPaged`.

No use cases — operations are simple enough to call the repository directly from the provider.

### Repository Implementation: `LocationRepositoryImpl`

File: `lib/features/locations/data/repositories/location_repository_impl.dart`

- Implements `LocationRepository`
- Constructor: `LocationRepositoryImpl(LocationLocalDatasource _localDatasource)`
- `create`: enforces unique name per project via `UniqueNameValidator.isNameDuplicate`
- `updateLocation`: enforces unique name per project (excluding the item being renamed) via `UniqueNameValidator.isNameDuplicateExcluding`
- `update`: delegates to `updateLocation`
- `save`: upsert — checks `getById`, calls `insert` or `update` accordingly
- Returns `RepositoryResult<Location>` for write operations (carries error message on failure)

## Presentation Layer

### Provider: `LocationProvider`

File: `lib/features/locations/presentation/providers/location_provider.dart`

```dart
class LocationProvider extends BaseListProvider<Location, LocationRepository>
```

- Extends `BaseListProvider` (shared base); holds `List<Location> items`
- Sorted alphabetically by `name`
- Write operations guarded by `canWrite()` callback (set at DI time)

Key members:

| Member | Notes |
|--------|-------|
| `locations` | Alias for `items` |
| `hasLocations` | Alias for `hasItems` |
| `locationCount` | Alias for `itemCount` |
| `loadLocations(String projectId)` | Alias for `loadItems(projectId)` |
| `createLocation(Location)` | Guarded; calls `createItem` |
| `updateLocation(Location)` | Guarded; calls `updateItem` |
| `deleteLocation(String id)` | Guarded; calls `deleteItem` |
| `getLocationById(String id)` | Read-only lookup; no state change |

No screens owned by this feature — `LocationProvider` is consumed by entries and projects UIs.

## Dependency Injection

File: `lib/features/locations/di/locations_providers.dart`

```dart
List<SingleChildWidget> locationProviders({
  required LocationRepository locationRepository,
  required AuthProvider authProvider,
}) {
  return [
    ChangeNotifierProvider(
      create: (_) {
        final p = LocationProvider(locationRepository);
        p.canWrite = () => authProvider.canEditFieldData;
        return p;
      },
    ),
  ];
}
```

- Tier 4 provider (depends on repository + auth)
- Write guard wired to `authProvider.canEditFieldData`

## Relationships

### Depends On
- **projects** — `projectId` is a required FK; locations are project-scoped
- **auth** — `canEditFieldData` guard via `AuthProvider`
- **shared** — `ProjectScopedRepository`, `BaseListProvider`, `ProjectScopedDatasource`, `BaseRemoteDatasource`, `RepositoryResult`, `UniqueNameValidator`
- **core/database** — `DatabaseService` injected into `LocationLocalDatasource`

### Required By
- **entries** — entry forms embed location selection (picks from `LocationProvider.locations`)
- **projects** — project setup/detail screens manage the location list for a project

## Patterns

- **Simple CRUD**: no use cases, repository called directly from provider
- **Unique name enforcement**: handled in `LocationRepositoryImpl`, not in UI
- **Offline-first**: all reads/writes go to SQLite; sync is change-log driven (no per-record sync status)
- **No dedicated screens**: UI is hosted entirely in entries and projects features
- **Write guard**: viewer-role users cannot create/update/delete locations (`canWrite` callback)

## Offline Behavior

All operations are local-only at runtime. Supabase propagation is handled by the sync engine reading the `change_log` table (populated by SQLite triggers on INSERT/UPDATE/DELETE to `locations`). `LocationRemoteDatasource` exists for future direct-fetch scenarios.
