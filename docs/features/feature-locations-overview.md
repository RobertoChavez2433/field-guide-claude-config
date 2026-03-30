---
feature: locations
type: overview
scope: Job Site Location Management with GPS
updated: 2026-03-30
---

# Locations Feature Overview

## Purpose

The Locations feature manages job site locations within construction projects. Locations represent specific geographic areas where work is performed (e.g., "Station 12+50", "Bridge Approach", "Downtown Intersection"). Each location stores GPS coordinates, a name, and an optional description, enabling site-specific documentation and entry filtering.

## Key Responsibilities

- **Location Creation**: Add new job site locations with name, description, and GPS coordinates
- **Location Management**: Edit and delete locations from projects
- **GPS Tracking**: Capture and store latitude/longitude for each location (nullable)
- **Location Linking**: Reference locations in daily entries
- **Location Queries**: Filter entries by location within a project
- **Unique Name Enforcement**: Prevent duplicate location names within the same project

## Key Files

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/locations/data/models/location.dart` | `Location` | Location model with GPS fields, `toMap`/`fromMap` |
| `lib/features/locations/data/datasources/local/location_local_datasource.dart` | `LocationLocalDatasource` | SQLite persistence; extends `ProjectScopedDatasource<Location>` |
| `lib/features/locations/data/datasources/remote/location_remote_datasource.dart` | `LocationRemoteDatasource` | Supabase read path; extends `BaseRemoteDatasource<Location>` |
| `lib/features/locations/domain/repositories/location_repository.dart` | `LocationRepository` | Domain interface (abstract); extends `ProjectScopedRepository<Location>` |
| `lib/features/locations/data/repositories/location_repository_impl.dart` | `LocationRepositoryImpl` | Repository implementation; wraps local datasource |
| `lib/features/locations/presentation/providers/location_provider.dart` | `LocationProvider` | State management; extends `BaseListProvider<Location, LocationRepository>` |
| `lib/features/locations/di/locations_providers.dart` | `locationProviders()` | DI wiring; registers `LocationProvider` as `ChangeNotifierProvider` |

## No Dedicated Screens

The locations feature has **no standalone presentation screens**. Location UI is embedded directly in the `entries` and `projects` features (selection dropdowns, creation dialogs). Only the provider layer lives under `presentation/`.

## Providers

| Provider | Type | Description |
|----------|------|-------------|
| `LocationProvider` | `ChangeNotifier` | Manages the location list for the active project. Write access gated by `authProvider.canEditFieldData`. |

## Data Sources

- **SQLite** (`locations` table): Primary persistence for all location records.
- **Supabase** (`LocationRemoteDatasource`): Remote read path used by the sync engine for pull operations.
- **Change Log**: SQLite triggers auto-populate `change_log` on INSERT/UPDATE/DELETE; drives sync push.

## Integration Points

**Depends on:**
- `core/database` — SQLite schema for `locations` table
- `projects` — Locations are scoped to a project (`project_id` foreign key)
- `auth` — `AuthProvider.canEditFieldData` gates write operations in `LocationProvider`

**Required by:**
- `entries` — Entry records reference a location for site-specific documentation
- `projects` — Project setup flow embeds location creation

## Offline Behavior

Locations are **fully offline-capable**. All CRUD operations persist to SQLite immediately. GPS coordinate capture uses the device's local positioning (no network required). Coordinates are nullable — missing GPS is valid. Cloud sync runs asynchronously during dedicated sync operations.

## Edge Cases & Limitations

- **GPS Accuracy**: Device GPS accuracy varies (±5–20 meters); no precision validation
- **GPS Availability**: Coordinates nullable — GPS may be unavailable indoors or in dense areas
- **Duplicate Prevention**: `UniqueNameValidator` enforces unique names within a project; no proximity-based deduplication
- **Location Deletion**: Soft-delete only; entries referencing deleted locations remain accessible
- **No Address Fields**: The model stores `name`, `description`, `latitude`, `longitude` only — no street address fields
- **Remote Datasource**: `LocationRemoteDatasource` is read-only in the current sync pattern; push is handled via the change log

## Detailed Specifications

See `rules/database/schema-patterns.md` for:
- SQLite schema for the `locations` table
- Indexing on `project_id` for efficient project-scoped queries

See `rules/sync/sync-patterns.md` for:
- How the change log drives sync push for location records
