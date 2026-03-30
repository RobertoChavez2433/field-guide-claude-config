---
feature: photos
type: architecture
scope: Photo Capture & Management with Sync Tracking
updated: 2026-03-30
---

# Photos Feature Architecture

## Directory Structure

```
lib/features/photos/
├── data/
│   ├── datasources/
│   │   ├── local/
│   │   │   ├── local_datasources.dart        # Barrel
│   │   │   └── photo_local_datasource.dart   # PhotoLocalDatasource
│   │   ├── remote/
│   │   │   ├── remote_datasources.dart       # Barrel
│   │   │   └── photo_remote_datasource.dart  # PhotoRemoteDatasource
│   │   └── datasources.dart                  # Top-level barrel
│   ├── models/
│   │   ├── models.dart
│   │   └── photo.dart                        # Photo model
│   ├── repositories/
│   │   ├── repositories.dart
│   │   └── photo_repository_impl.dart        # PhotoRepositoryImpl
│   └── data.dart
├── domain/
│   ├── repositories/
│   │   ├── repositories.dart
│   │   └── photo_repository.dart             # PhotoRepository (abstract)
│   └── domain.dart
├── presentation/
│   ├── providers/
│   │   ├── providers.dart
│   │   └── photo_provider.dart               # PhotoProvider
│   ├── widgets/
│   │   ├── widgets.dart
│   │   ├── photo_thumbnail.dart              # PhotoThumbnail
│   │   ├── photo_source_dialog.dart          # PhotoSourceDialog
│   │   └── photo_name_dialog.dart            # PhotoNameDialog
│   └── presentation.dart
├── di/
│   └── photos_providers.dart                 # photoProviders()
└── photos.dart                               # Feature entry point

lib/services/
├── photo_service.dart                        # PhotoService (cross-cutting)
└── image_service.dart                        # ImageService (thumbnail cache)
```

## Data Layer

### Model: `Photo`

**File**: `lib/features/photos/data/models/photo.dart`

Immutable model with UUID auto-generation. No `syncStatus` field — sync is tracked by SQLite triggers writing to the `change_log` table.

Key fields:
- `id` — UUID, auto-generated
- `entryId` — FK to DailyEntry (required)
- `projectId` — FK to Project (required; enables cross-entry queries)
- `filePath` — local device path (absolute)
- `filename` — human-readable name (e.g., `Photo 2026-01-15 RBWS 864130 (1).jpg`)
- `remotePath` — Supabase Storage path (null until synced)
- `caption` — user-provided label (shown as thumbnail overlay or text below)
- `notes` — additional observations
- `locationId` — optional FK to project Location
- `latitude / longitude` — GPS captured at shot time (optional)
- `capturedAt` — shot timestamp (indexed; default `DateTime.now()`)
- `createdAt / updatedAt` — lifecycle timestamps
- `createdByUserId` — Supabase auth UID for attribution

Helper getter: `hasLocation` returns true when both GPS fields are non-null.

Serialization: `toMap()` / `Photo.fromMap()` using snake_case column names matching the SQLite `photos` table.

### Local Datasource: `PhotoLocalDatasource`

**File**: `lib/features/photos/data/datasources/local/photo_local_datasource.dart`

Extends `ProjectScopedDatasource<Photo>`. SQLite table: `photos`. Default order: `captured_at DESC`.

Key methods beyond the base class:
| Method | Purpose |
|--------|---------|
| `create(Photo)` | Alias for `insert` (backward compat) |
| `getByEntryId(String)` | Photos for a specific entry |
| `softDeleteByEntryId(String, {userId})` | Sets `deleted_at`/`deleted_by`; triggers change_log UPDATE for sync |
| `getCountByEntryId(String)` | Count for badge display |
| `updatePhoto(Photo)` | Update and return rows affected |
| `deletePhoto(String)` | Hard delete by ID, returns rows affected |
| `getCountByProjectId(String)` | Project-level count |
| `updateEntryId(String, String)` | Re-parent photo to a new entry (temp ID resolution) |
| `getAllPhotos()` | Debug utility — logs all records |

### Remote Datasource: `PhotoRemoteDatasource`

**File**: `lib/features/photos/data/datasources/remote/photo_remote_datasource.dart`

Extends `BaseRemoteDatasource<Photo>`. Supabase table: `photos`. Storage bucket: `entry-photos`.

Storage path format (company-scoped): `entries/{companyId}/{entryId}/{filename}` — validated by `_validateStoragePath()` before upload (SEC-NEW-7 defense in depth).

Key methods:
| Method | Purpose |
|--------|---------|
| `getByEntryId(String)` | Query Supabase `photos` table by entry |
| `getByProjectId(String)` | Query by project |
| `uploadPhoto(File, String, {companyId})` | Upload bytes via background isolate (`compute`); returns remote path |
| `getPhotoUrl(String)` | Signed URL, 1-hour expiry (SEC-2 — no public URLs) |
| `downloadPhoto(String)` | Returns raw bytes from Storage |
| `deletePhotoFile(String)` | Remove file from Storage bucket |
| `deletePhotoComplete(String, String?)` | Delete DB record + storage file |

### Domain Interface: `PhotoRepository`

**File**: `lib/features/photos/domain/repositories/photo_repository.dart`

Extends `BaseRepository<Photo>`.

```dart
abstract class PhotoRepository implements BaseRepository<Photo> {
  Future<RepositoryResult<Photo>> createPhoto(Photo photo);
  Future<RepositoryResult<Photo>> getPhotoById(String id);
  Future<RepositoryResult<List<Photo>>> getPhotosForEntry(String entryId);
  Future<RepositoryResult<List<Photo>>> getPhotosForProject(String projectId);
  Future<PagedResult<Photo>> getByProjectIdPaged(String projectId, {required int offset, required int limit});
  Future<RepositoryResult<Photo>> updatePhoto(Photo photo);
  Future<RepositoryResult<void>> deletePhoto(String id, {bool deleteFile = true});
  Future<RepositoryResult<void>> deletePhotosForEntry(String entryId, {bool deleteFiles = true});
  Future<RepositoryResult<int>> getPhotoCountForEntry(String entryId);
  Future<RepositoryResult<int>> getPhotoCountForProject(String projectId);
  Future<RepositoryResult<void>> updateEntryId(String photoId, String newEntryId);
}
```

All results are wrapped in `RepositoryResult<T>` (success/failure discriminated union) or `PagedResult<T>` for paginated queries.

### Repository Implementation: `PhotoRepositoryImpl`

**File**: `lib/features/photos/data/repositories/photo_repository_impl.dart`

Depends only on `PhotoLocalDatasource` — no remote datasource in the constructor. Remote sync is handled by the sync feature via the change_log mechanism, not by this repository directly.

`deletePhoto` optionally deletes the physical file before removing the DB record (`deleteFile: true` default). `deletePhotosForEntry` uses `softDeleteByEntryId` to preserve trash/recovery semantics and propagate `deleted_at` to Supabase via sync.

## Presentation Layer

No dedicated screens — the photos feature provides reusable widgets consumed by entries, gallery, and forms features.

### Provider: `PhotoProvider`

**File**: `lib/features/photos/presentation/providers/photo_provider.dart`

`ChangeNotifier`. Takes `PhotoRepository` and a `CanWriteCallback` (write guard injected from `AuthProvider.canEditFieldData`).

State:
- `photos` — full list for current entry/project
- `pagedItems` — accumulated pages for gallery infinite scroll
- `isLoading` / `error`
- `hasMorePhotos` / `totalPhotoCount` (from `PagedResult`)

Key methods:
| Method | Notes |
|--------|-------|
| `loadPhotosForEntry(String)` | Loads all photos for an entry into `photos` |
| `loadPhotosForProject(String)` | Loads all photos for a project into `photos` |
| `loadPhotosPaged(String, {offset, limit})` | First-page load for gallery; default limit 20 |
| `loadMorePhotos()` | Appends next page to `pagedItems` |
| `addPhoto(Photo)` | Write-guarded; prepends to `photos` list |
| `updatePhoto(Photo)` | Updates in-place by ID |
| `deletePhoto(String)` | Write-guarded; removes from list |
| `deletePhotosForEntry(String)` | Write-guarded cascade delete |
| `getPhotoCountForEntry(String)` | Async DB query for count badges |
| `getPhotoCountForProject(String)` | Async DB query for dashboard stats |
| `getPhotoById(String)` | Synchronous lookup from loaded `photos` |
| `clear()` | Resets all state |

### Widget: `PhotoThumbnail`

**File**: `lib/features/photos/presentation/widgets/photo_thumbnail.dart`

`StatefulWidget`. Loads thumbnail via `ImageService.getThumbnail()` (singleton from Provider tree — not instantiated per widget). Uses a cached `Future` initialized in `didChangeDependencies` to prevent reloads on rebuild. Wrapped in `RepaintBoundary` to isolate scroll repaints.

Two display styles via `PhotoThumbnailStyle` enum:
- `withTextBelow` — filename or caption as text below image (entry wizard)
- `withCaptionOverlay` — caption as semi-transparent overlay at bottom (gallery/report)

Supports optional `onTap`, `onDelete`, `onLongPress` callbacks. Shows GPS indicator badge when `photo.hasLocation` is true.

### Widget: `PhotoSourceDialog`

**File**: `lib/features/photos/presentation/widgets/photo_source_dialog.dart`

`StatelessWidget` rendered as a modal bottom sheet. Static `PhotoSourceDialog.show(context)` returns `PhotoSource?` (enum: `camera` or `gallery`). Used as the entry point before calling `PhotoService.capturePhoto()` or `PhotoService.pickFromGallery()`.

### Widget: `PhotoNameDialog`

**File**: `lib/features/photos/presentation/widgets/photo_name_dialog.dart`

`StatefulWidget` shown as a blocking `AlertDialog`. Presents a photo preview, filename field, optional location dropdown, description field, and GPS read-out. Returns `PhotoNameResult?` (filename, description, locationId). Deletes the temp file if the user cancels. Uses `ImageService` singleton from Provider tree.

## Cross-Cutting Services

### `PhotoService`

**File**: `lib/services/photo_service.dart`

Orchestrates camera/gallery capture, file storage, GPS tagging, and DB record creation. Depends on `PhotoRepository`. Lives in `lib/services/` (not inside the feature) because it is consumed by entries and forms features as well.

Key responsibilities:
- `capturePhoto()` / `pickFromGallery()` — wraps `image_picker`; 85% quality, 1920x1080 max
- `savePhoto(...)` — copies temp file to app documents `photos/` dir, creates `Photo` record via repository
- `generateCompanyFilename(...)` — formats `Photo YYYY-MM-DD INITIALS PROJECT (N)` naming convention
- `getNextPhotoSequence(...)` — scans `photos/` dir to determine next sequence number
- `getCurrentLocation()` — GPS via `geolocator`; returns mock position in test mode
- `capturePhotoWithLocation(...)` / `pickFromGalleryWithLocation(...)` — convenience methods combining capture + GPS
- `renamePhoto(...)` — renames file on disk and updates DB record
- `updatePhotoEntryId(...)` — delegates to `repository.updateEntryId` for temp ID resolution after entry save

### `ImageService`

**File**: `lib/services/image_service.dart`

Singleton (`factory` constructor). Handles thumbnail generation and caching. Used directly by `PhotoThumbnail` and `PhotoNameDialog`.

Three-tier cache:
1. In-memory LRU (50 entries max) — instant
2. Disk cache (`tmp/thumbnails/`) — survives rebuilds, cleared by settings "clear cache" action
3. On-demand generation in background isolate (`compute`) — JPEG at 85% quality, resized to `maxSize`

Key method: `getThumbnail(String imagePath, {int maxSize = 300})` — returns `Uint8List?`.
Cache cleared via `clearCache()` (called from settings feature).

## Dependency Injection

**File**: `lib/features/photos/di/photos_providers.dart`

```dart
List<SingleChildWidget> photoProviders({
  required PhotoRepository photoRepository,
  required PhotoService photoService,
  required ImageService imageService,
  required AuthProvider authProvider,
}) {
  return [
    ChangeNotifierProvider(
      create: (_) => PhotoProvider(
        photoRepository,
        canWrite: () => authProvider.canEditFieldData,
      ),
    ),
    Provider<PhotoService>.value(value: photoService),
    Provider<ImageService>.value(value: imageService),
  ];
}
```

`photoProviders()` is called at Tier 4 in `lib/main.dart`. `PhotoRepository` is wired to `PhotoRepositoryImpl(PhotoLocalDatasource(db))` in the root provider setup. `PhotoService` and `ImageService` are singleton instances passed in from main.

## Key Patterns

### File-Backed Model
Photos are split across two persistence layers:
- **SQLite** (`photos` table) — metadata: id, filePath, filename, caption, GPS, timestamps
- **Device filesystem** (`app_documents/photos/`) — actual JPEG files

`Photo.filePath` is the source of truth for the local file. `Photo.remotePath` is null until the sync engine uploads to Supabase Storage bucket `entry-photos`.

### Sync via Change Log
There is no `syncStatus` field on `Photo`. Sync readiness is tracked by SQLite triggers that write to the `change_log` table on every INSERT/UPDATE/DELETE to `photos`. The sync feature reads change_log entries and calls `PhotoRemoteDatasource.uploadPhoto()` for files that need uploading.

### Soft Delete for Entries
When an entry is deleted, `PhotoRepositoryImpl.deletePhotosForEntry()` calls `softDeleteByEntryId()` instead of hard-deleting. This sets `deleted_at` on the photo rows, which the SQLite trigger records as an UPDATE in change_log. The sync engine then propagates `deleted_at` to Supabase, respecting 30-day trash retention.

### Thumbnail Isolation
`ImageService` is a singleton; widgets must read it from the Provider tree (`context.read<ImageService>()`), not instantiate it directly. This was a performance fix (C2) — per-widget instantiation caused hundreds of duplicate service objects in photo-heavy gallery views.

### Write Guard
`PhotoProvider` accepts a `CanWriteCallback` injected from `AuthProvider.canEditFieldData`. Write operations (`addPhoto`, `deletePhoto`, `deletePhotosForEntry`) return early (null/false) with a log entry if the callback returns false. The default callback returns true until AuthProvider is wired.

### Storage Path Security
`PhotoRemoteDatasource.uploadPhoto()` validates the storage path against the regex `^entries/[a-f0-9-]+/[a-f0-9-]+/[a-zA-Z0-9_.-]+\.(jpg|jpeg|png|heic)$` before upload (SEC-NEW-7). URLs are served as signed URLs with 1-hour expiry, never as public URLs (SEC-2).

## Feature Relationships

| Relationship | Direction | Notes |
|---|---|---|
| **entries** | consumes photos | Photo attachment in entry wizard; `PhotoProvider.loadPhotosForEntry()`, `PhotoSourceDialog`, `PhotoNameDialog`, `PhotoThumbnail` |
| **gallery** | consumes photos | Photo browsing by project; `PhotoProvider.loadPhotosPaged()` + `loadMorePhotos()`, `PhotoThumbnail` |
| **settings** | consumes ImageService | "Clear cache" action calls `ImageService.clearCache()` |
| **sync** | consumes photos data | Reads change_log entries for photos; calls `PhotoRemoteDatasource.uploadPhoto()` during push |
| **projects** | depended on by photos | `Photo.projectId` — project-scoped; photos are always filtered within a project boundary |
| **locations** | depended on by photos | `Photo.locationId` / `PhotoNameDialog` location dropdown |
| **auth** | depended on by photos | `CanWriteCallback` injected from `AuthProvider.canEditFieldData`; `createdByUserId` set on save |
