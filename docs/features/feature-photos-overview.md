---
feature: photos
type: overview
scope: Photo Capture & Management with Sync Tracking
updated: 2026-02-13
---

# Photos Feature Overview

## Purpose

The Photos feature enables construction inspectors to capture, store, and manage photos from job sites. Photos are linked to daily entries and projects, with support for offline capture, metadata annotation, GPS tracking, and cloud sync. The feature handles local storage, thumbnail generation, and sync status tracking to coordinate with the cloud backend.

## Key Responsibilities

- **Photo Capture**: Capture photos using device camera or load from device gallery
- **Metadata Management**: Add captions, notes, location tags, and GPS coordinates to photos
- **Local Storage**: Store photos on device with standardized naming and organization
- **Thumbnail Generation**: Create thumbnails for gallery preview and list views
- **Entry Linking**: Associate photos with specific daily entries
- **Sync Tracking**: Tag photos with sync status (pending/synced) for cloud push
- **Photo Retrieval**: Load photos by entry, project, location, or date range

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/photos/data/models/photo.dart` | Photo model with metadata, GPS, sync status |
| `lib/features/photos/data/repositories/photo_repository.dart` | CRUD and query operations |
| `lib/features/photos/presentation/providers/photo_provider.dart` | Photo state management |
| `lib/features/photos/presentation/widgets/photo_thumbnail.dart` | Thumbnail display widget |
| `services/photo/photo_service.dart` | Cross-cutting photo capture and storage service |
| `lib/features/photos/data/datasources/local/photo_local_datasource.dart` | SQLite persistence |

## Data Sources

- **Device Camera/Gallery**: Photo capture via camera plugin or gallery picker
- **SQLite**: Photo metadata persisted locally (path, captions, GPS, sync status)
- **Device File System**: Photo files stored locally with project/entry organization
- **Cloud Storage** (sync): Photos uploaded to Supabase during sync operations (future)

## Integration Points

**Depends on:**
- `core/database` - SQLite schema for photos and metadata
- `entries` - Photo entry linking via `entryId` foreign key
- `projects` - Photo project linking via `projectId` foreign key
- `locations` - Optional location tagging via `locationId` foreign key
- `services/photo` - Device camera/gallery access and storage

**Required by:**
- `entries` - Entry detail screen displays linked photos
- `dashboard` - Photo count and recent photos for project summary
- `sync` - Photo files and metadata synced to Supabase
- `toolbox` - Gallery screen displays all photos with filtering

## Offline Behavior

Photos are **fully offline-capable**. Capture, storage, and metadata management occur entirely locally. Photos are stored on device file system with metadata in SQLite. Cloud sync (if implemented) handles async upload of photo files and metadata updates. Inspectors can work with photos entirely offline; synchronization happens asynchronously during dedicated sync operations.

## Edge Cases & Limitations

- **File System Permissions**: Camera/gallery access requires Android/iOS permissions; must request at capture time
- **Storage Space**: Photos consume significant storage; no automatic cleanup implemented
- **Thumbnail Caching**: Thumbnails generated on-demand (not cached); large galleries may be slow
- **Photo Deletion**: Soft-delete only (flag in database); files not removed from device until sync cleanup
- **GPS Coordinates**: Optional; devices without GPS or location disabled return null
- **Photo Format**: Expects JPEG/PNG; other formats may fail thumbnail generation
- **Duplicate Detection**: No automatic deduplication; manual deletion required

## Detailed Specifications

See `architecture-decisions/photos-constraints.md` for:
- Hard rules on photo file naming and organization
- Storage quotas and cleanup policies
- Metadata validation and nullable field guidelines
- Sync status semantics and conflict resolution

See `rules/database/schema-patterns.md` for:
- SQLite schema for photos table and foreign key relationships
- Indexing on entryId, projectId, date for efficient queries

