---
feature: photos
type: overview
scope: Photo Capture & Management with Sync Tracking
updated: 2026-03-30
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
| `lib/features/photos/data/models/photo.dart` | `Photo` model with metadata, GPS, sync status |
| `lib/features/photos/data/datasources/local/photo_local_datasource.dart` | `PhotoLocalDatasource` — SQLite persistence |
| `lib/features/photos/data/datasources/remote/photo_remote_datasource.dart` | `PhotoRemoteDatasource` — Supabase sync |
| `lib/features/photos/domain/repositories/photo_repository.dart` | `PhotoRepository` abstract interface |
| `lib/features/photos/data/repositories/photo_repository_impl.dart` | `PhotoRepositoryImpl` — concrete implementation |
| `lib/features/photos/presentation/providers/photo_provider.dart` | `PhotoProvider` — photo state management |
| `lib/features/photos/presentation/widgets/photo_source_dialog.dart` | `PhotoSourceDialog` — camera vs. gallery picker |
| `lib/features/photos/presentation/widgets/photo_thumbnail.dart` | `PhotoThumbnail` — thumbnail display widget |
| `lib/features/photos/presentation/widgets/photo_name_dialog.dart` | `PhotoNameDialog` — name/caption input dialog |
| `lib/features/photos/di/photos_providers.dart` | DI registrations for photos feature |

## Screens

None. The Photos feature has no standalone screens. Its widgets (`PhotoSourceDialog`, `PhotoThumbnail`, `PhotoNameDialog`) are embedded within the entries and gallery features.

## Providers

| Provider | Type | Description |
|----------|------|-------------|
| `PhotoProvider` | `ChangeNotifier` | Manages photo list state; load, add, delete, and sync-status updates |

## Data Sources

- **Device Camera/Gallery**: Photo capture via camera plugin or gallery picker
- **SQLite**: Photo metadata persisted locally via `PhotoLocalDatasource` (path, captions, GPS, sync status)
- **Device File System**: Photo files stored locally with project/entry organization
- **Supabase** (sync): Photos uploaded via `PhotoRemoteDatasource` during sync operations

## Integration Points

**Depends on:**
- `core/database` — SQLite schema for photos and metadata
- `projects` — Photo project linking via `projectId` foreign key
- `services/photo` — Device camera/gallery access and file storage

**Required by:**
- `entries` — Entry detail screen embeds `PhotoThumbnail` for linked photos
- `gallery` — Gallery screen displays all photos using `PhotoThumbnail`
- `settings` — Photo storage management and cleanup options

## Offline Behavior

Photos are **fully offline-capable**. Capture, storage, and metadata management occur entirely locally. Photos are stored on device file system with metadata in SQLite. Cloud sync handles async upload of photo files and metadata updates via `PhotoRemoteDatasource`. Inspectors can work with photos entirely offline; synchronization happens asynchronously during dedicated sync operations.

## Edge Cases & Limitations

- **File System Permissions**: Camera/gallery access requires Android/iOS permissions; must request at capture time
- **Storage Space**: Photos consume significant storage; no automatic cleanup implemented
- **Thumbnail Caching**: Thumbnails generated on-demand (not cached); large galleries may be slow
- **Photo Deletion**: Soft-delete only (flag in database); files not removed from device until sync cleanup
- **GPS Coordinates**: Optional; devices without GPS or location disabled return null
- **Photo Format**: Expects JPEG/PNG; other formats may fail thumbnail generation
- **Duplicate Detection**: No automatic deduplication; manual deletion required

## Detailed Specifications

See `rules/database/schema-patterns.md` for:
- SQLite schema for photos table and foreign key relationships
- Indexing on entryId, projectId, date for efficient queries
