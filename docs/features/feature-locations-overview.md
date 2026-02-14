---
feature: locations
type: overview
scope: Job Site Location Management with GPS
updated: 2026-02-13
---

# Locations Feature Overview

## Purpose

The Locations feature manages job site locations within construction projects. Locations represent specific geographic areas or addresses where work is performed (e.g., "Station 12+50", "Bridge Approach", "Downtown Intersection"). Each location stores GPS coordinates, address information, and metadata to enable site-specific documentation and photo tagging.

## Key Responsibilities

- **Location Creation**: Add new job site locations with address, description, and GPS coordinates
- **Location Management**: Edit and delete locations from projects
- **GPS Tracking**: Capture and store latitude/longitude for each location
- **Location Linking**: Reference locations in daily entries and photos
- **Location Queries**: Filter entries and photos by location
- **Address Management**: Store street address, cross streets, landmark information

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/locations/data/models/location.dart` | Location model with GPS and address fields |
| `lib/features/locations/data/repositories/location_repository.dart` | Location CRUD operations |
| `lib/features/locations/presentation/providers/location_provider.dart` | Location state management |
| `lib/features/locations/data/datasources/local/location_local_datasource.dart` | SQLite persistence |

## Data Sources

- **SQLite**: Persists location records with GPS and address data
- **Device GPS**: Current coordinates captured at location creation (via cross-cutting service)
- **Project Setup**: Locations created during project initialization in `projects` feature
- **Daily Entries**: Locations referenced in entry records

## Integration Points

**Depends on:**
- `core/database` - SQLite schema for locations table
- `projects` - Locations scoped to projects
- `services` - GPS/location service for coordinate capture

**Required by:**
- `entries` - Entry detail screen requires location selection
- `photos` - Photo tagging with location (optional)
- `dashboard` - Location-based filtering and summaries
- `toolbox` - Location filtering for form responses

## Offline Behavior

Locations are **fully offline-capable**. Creation, editing, and GPS capture occur entirely offline. All data persists in SQLite. GPS coordinates captured via device's local positioning (no network required). Cloud sync handles async push. Inspectors can manage locations entirely offline; sync happens during dedicated sync operations.

## Edge Cases & Limitations

- **GPS Accuracy**: Device GPS accuracy varies (±5-20 meters); no validation or high-precision guarantees
- **GPS Availability**: GPS may be unavailable indoors or in dense urban areas (coordinates nullable)
- **Duplicate Prevention**: No automatic detection of nearby locations; manual deduplication required
- **Location Deletion**: Soft-delete only; entries and photos referencing deleted locations remain accessible
- **Address Validation**: No address validation or geolocation lookup; addresses stored as-is
- **Offline GPS**: GPS coordinates must be captured while online (or via device's local cache)

## Detailed Specifications

See `architecture-decisions/locations-constraints.md` for:
- Hard rules on GPS coordinate storage and precision
- Address field validation and formatting
- Location deletion and data integrity

See `rules/database/schema-patterns.md` for:
- SQLite schema for locations table
- Indexing on projectId for efficient queries

