---
feature: photos
type: architecture
scope: Photo Capture & Management with Sync Tracking
updated: 2026-02-13
---

# Photos Feature Architecture

## Data Model

### Core Entities

| Entity | Fields | Type | Notes |
|--------|--------|------|-------|
| **Photo** | id, entryId, projectId, filePath, filename, remotePath, notes, caption, locationId, latitude, longitude, capturedAt, syncStatus, createdAt, updatedAt | Model | Photo metadata and references |

### Key Models

**Photo**:
- `id`: UUID, auto-generated if not provided
- `entryId`: Foreign key to DailyEntry (required; links photo to job site work)
- `projectId`: Foreign key to Project (required; enables cross-entry queries)
- `filePath`: Local device path (e.g., `/storage/emulated/0/.../photo_abc123.jpg`)
- `filename`: Human-readable filename (e.g., `photo_20260213_154530.jpg`)
- `remotePath`: Cloud storage URL (null until synced)
- `caption`: User-provided description (e.g., "Pipe installation at Station 12+50")
- `notes`: Additional notes or observations
- `locationId`: Reference to project location (optional, for fine-grained filtering)
- `latitude/longitude`: GPS coordinates captured at time of photo (optional)
- `capturedAt`: Timestamp when photo was taken (indexed for range queries)
- `syncStatus`: Enum {pending, synced, error} for cloud sync tracking
- `createdAt/updatedAt`: Lifecycle timestamps

## Relationships

### Entry → Photos (1-N)
```
DailyEntry (1)
    ├─→ Photo[] (many photos per entry)
    │   ├─→ filePath (device storage)
    │   ├─→ remotePath (cloud storage after sync)
    │   └─→ metadata (caption, GPS, location)
    │
    └─→ Referenced in entry detail screen
        ├─→ Displays thumbnails
        ├─→ Allows annotation/edit
        └─→ Syncs on entry sync
```

### Project → Photos (1-N)
```
Project (1)
    ↓
Photo[] (all photos for project, across all entries)
    ├─→ Filtered by date range for dashboard
    ├─→ Grouped by location for site documentation
    └─→ Counted for project statistics
```

### Photo Sync Lifecycle
```
Photo captured/stored locally
    ├─→ syncStatus = pending
    ├─→ filePath = device storage
    └─→ remotePath = null

Sync operation initiated
    ├─→ Upload filePath to cloud storage
    ├─→ Receive remotePath from cloud
    └─→ Update photo.remotePath

Sync completes
    ├─→ syncStatus = synced
    ├─→ Photo now backed up in cloud
    └─→ Soft-delete on device (optional)
```

## Repository Pattern

### PhotoRepository

**Location**: `lib/features/photos/data/repositories/photo_repository.dart`

```dart
class PhotoRepository {
  // CRUD
  Future<Photo> create(Photo photo)
  Future<Photo?> getById(String id)
  Future<List<Photo>> listByEntry(String entryId)
  Future<List<Photo>> listByProject(String projectId)
  Future<void> update(Photo photo)
  Future<void> delete(String id)

  // Specialized Queries
  Future<List<Photo>> listByDateRange(String projectId, DateTime start, DateTime end)
  Future<List<Photo>> listByLocation(String locationId)
  Future<List<Photo>> listByStatus(SyncStatus status)
  Future<int> countByEntry(String entryId)
  Future<int> countByProject(String projectId)
  Future<List<Photo>> listRecentByProject(String projectId, int limit)
}
```

### PhotoService (Cross-cutting)

**Location**: `services/photo/photo_service.dart`

```dart
class PhotoService {
  // Capture & Storage
  Future<Photo?> captureFromCamera(String entryId, String projectId)
  Future<Photo?> pickFromGallery(String entryId, String projectId)
  Future<String> savePhotoLocally(File photo, String entryId)

  // File Operations
  Future<Uint8List?> loadPhotoBytes(String filePath)
  Future<Uint8List?> generateThumbnail(String filePath, {int size = 200})
  Future<void> deletePhotoFile(String filePath)

  // Metadata
  Future<(double? latitude, double? longitude)> getGpsCoordinates()
  String generateFilename() => 'photo_${DateTime.now().millisecondsSinceEpoch}.jpg'
}
```

## State Management

### Provider Type: ChangeNotifier

**PhotoProvider** (`lib/features/photos/presentation/providers/photo_provider.dart`):

```dart
class PhotoProvider extends ChangeNotifier {
  // State
  List<Photo> _photos = [];
  Photo? _currentPhoto;
  bool _isLoading = false;
  String? _error;
  Map<String, Uint8List> _thumbnailCache = {};

  // Getters
  List<Photo> get photos => _photos;
  Photo? get currentPhoto => _currentPhoto;
  bool get isLoading => _isLoading;
  String? get error => _error;
  int get pendingPhotoCount => _photos.where((p) => p.syncStatus == SyncStatus.pending).length;

  // Methods
  Future<void> loadPhotosByEntry(String entryId)
  Future<void> loadPhotosByProject(String projectId)
  Future<void> capturePhoto(String entryId, String projectId)
  Future<void> pickPhotoFromGallery(String entryId, String projectId)
  Future<void> updatePhotoCaption(String photoId, String caption)
  Future<void> updatePhotoNotes(String photoId, String notes)
  Future<void> deletePhoto(String photoId)
  Future<Uint8List?> getThumbnail(String photoId)
  Future<void> markPhotoSynced(String photoId)
}
```

### Initialization Lifecycle

```
Entry Detail Screen Loaded
    ↓
initState() calls loadPhotosByEntry(entryId)
    ├─→ _isLoading = true → shows skeleton loader
    │
    ├─→ Repository.listByEntry(entryId)
    │   └─→ SQLite query with entryId = ?
    │
    └─→ _photos = results
        _isLoading = false
        notifyListeners() → displays photo list
```

### Photo Capture Flow

```
User taps "Capture Photo" button
    ↓
capturePhoto(entryId, projectId) called
    ├─→ _isLoading = true → shows progress
    │
    ├─→ PhotoService.captureFromCamera()
    │   ├─→ Request camera permission
    │   ├─→ Launch camera intent
    │   ├─→ On success: save to device storage
    │   └─→ Return File
    │
    ├─→ Repository.create(Photo)
    │   ├─→ Generate UUID
    │   ├─→ Set syncStatus = pending
    │   ├─→ Insert to SQLite
    │   └─→ Return created Photo
    │
    ├─→ _photos.add(newPhoto)
    ├─→ _isLoading = false
    └─→ notifyListeners() → shows new photo in list
```

### Photo Sync Flow

```
Sync operation triggered (in sync feature)
    ↓
Query all photos with syncStatus = pending
    ├─→ Repository.listByStatus(pending)
    │
    ├─→ For each pending photo:
    │   ├─→ Upload filePath to cloud storage
    │   ├─→ Receive remotePath URL from cloud
    │   ├─→ Update Photo.remotePath = url
    │   ├─→ Update Photo.syncStatus = synced
    │   └─→ Repository.update(photo)
    │
    └─→ All pending photos now synced
        ├─→ notifyListeners() → UI shows sync success
        └─→ Optional: delete local files to save space
```

## Offline Behavior

**Fully offline**: Photo capture, storage, and metadata management occur entirely offline. All files stored on device; cloud sync happens separately in dedicated sync operations.

### Read Path (Offline)
- Photo list queries SQLite by entryId or projectId
- Thumbnail generation from local filePath (on-demand)
- No cloud dependency

### Write Path (Offline)
- Photo file saved to device storage immediately
- Metadata (caption, GPS, notes) persisted to SQLite immediately
- All photos tagged with `syncStatus: pending` until synced
- Changes are immediate and offline-safe

### Sync Status
- `pending` - Photo waiting to be uploaded
- `synced` - Photo uploaded to cloud storage
- `error` - Sync failed (retry on next sync)
- Repository provides `listByStatus()` for sync batching

## Testing Strategy

### Unit Tests (Model-level)
- **Photo**: Constructor, copyWith, toMap/fromMap
- **Nullable fields**: caption, notes, GPS coordinates
- **Enum handling**: SyncStatus serialization

Location: `test/features/photos/data/models/photo_test.dart`

### Repository Tests (Data-level)
- **CRUD operations**: Create, read, update, delete photos
- **Query filters**: List by entryId, projectId, date range, location, status
- **Sync status**: Filter pending photos, update synced status
- **Offline behavior**: All tests mock database

Location: `test/features/photos/data/repositories/photo_repository_test.dart`

### Widget Tests (Provider-level)
- **PhotoProvider**: Mock repository, trigger operations, verify state updates
- **Photo list**: Verify photos displayed by entry, thumbnails shown
- **Capture flow**: Mock camera/gallery, verify photo created
- **Sync status**: Verify pending/synced visual indicators

Location: `test/features/photos/presentation/providers/photo_provider_test.dart`

### Integration Tests
- **Capture and save**: Camera → photo file saved → SQLite record created
- **Edit metadata**: Load photo → edit caption → save → verify persisted
- **Multi-entry photos**: Create 3 entries, assign 2 photos each, verify filtering

Location: `test/features/photos/presentation/widgets/`

### Test Coverage
- ≥ 90% for repository (high-criticality data persistence)
- ≥ 85% for provider (state management)
- 70% for widgets (camera mocking limitations)

## Performance Considerations

### Target Response Times
- Load 20 photos: < 500 ms
- Generate thumbnail (100x100): < 200 ms
- Save photo metadata: < 100 ms
- Photo capture: device-dependent (1-3 seconds)

### Memory Constraints
- Thumbnail cache: ~100 KB per 20 photos (200x200 PNG)
- Full photo in memory: ~2-5 MB per photo (device-dependent)
- Metadata in memory: ~100 bytes per photo

### Optimization Opportunities
- Lazy-load thumbnails (generate on demand, not on load)
- Cache thumbnails in SQLite BLOB column
- Paginate photo lists (50 per page)
- Compress photos before saving (90% quality JPEG)
- Background sync for photos (prioritize small photos first)

## File Locations

```
lib/features/photos/
├── data/
│   ├── models/
│   │   ├── models.dart
│   │   └── photo.dart
│   │
│   ├── datasources/
│   │   ├── local/
│   │   │   ├── local_datasources.dart
│   │   │   └── photo_local_datasource.dart
│   │   └── remote/
│   │       ├── remote_datasources.dart
│   │       └── photo_remote_datasource.dart
│   │
│   └── repositories/
│       ├── repositories.dart
│       └── photo_repository.dart
│
├── presentation/
│   ├── widgets/
│   │   ├── widgets.dart
│   │   ├── photo_thumbnail.dart
│   │   ├── photo_source_dialog.dart
│   │   └── photo_name_dialog.dart
│   │
│   ├── providers/
│   │   ├── providers.dart
│   │   └── photo_provider.dart
│   │
│   └── presentation.dart
│
└── photos.dart                       # Feature entry point

services/photo/
├── photo_service.dart                # Camera, gallery, thumbnail generation
└── photo_service_impl.dart           # Platform-specific implementation

lib/core/database/
└── database_service.dart             # SQLite schema for photos table
```

### Import Pattern

```dart
// Within photos feature
import 'package:construction_inspector/features/photos/data/models/photo.dart';
import 'package:construction_inspector/features/photos/data/repositories/photo_repository.dart';
import 'package:construction_inspector/features/photos/presentation/providers/photo_provider.dart';

// Cross-cutting service
import 'package:construction_inspector/services/photo/photo_service.dart';

// Barrel export
import 'package:construction_inspector/features/photos/photos.dart';
```

