---
feature: gallery
type: architecture
updated: 2026-03-30
---

# Gallery Feature Architecture

## Directory Structure

```
lib/features/gallery/
├── gallery.dart                          # Feature barrel export
├── di/
│   └── gallery_providers.dart            # DI wiring (Tier 4 providers)
├── domain/
│   └── domain.dart                       # Domain barrel (empty — no use cases)
└── presentation/
    ├── providers/
    │   └── gallery_provider.dart         # Gallery state — filters, photo list, loading
    └── screens/
        └── gallery_screen.dart           # GalleryScreen + _FilterSheet + _PhotoViewerScreen
```

## Data Layer

Gallery has **no data layer of its own**. It accesses data exclusively through repository interfaces owned by other features:

| Repository | Owner Feature | Usage |
|------------|--------------|-------|
| `PhotoRepository` | `photos` | Load all photos for a project |
| `DailyEntryRepository` | `entries` | Load entries for the entry filter dropdown |

### Data Model

Gallery uses the `Photo` model from `lib/features/photos/data/models/photo.dart` and the `DailyEntry` model from `lib/features/entries/data/models/daily_entry.dart`. It defines no models of its own.

## Domain Layer

The domain barrel (`domain/domain.dart`) is intentionally empty. Pass-through use cases were removed as YAGNI — `GalleryProvider` calls repositories directly. There are no domain use cases, exceptions, or utilities in this feature.

### Filter Enum

`GalleryFilter` is defined in `gallery_provider.dart` alongside the provider (presentation layer):

| Value | Behavior |
|-------|---------|
| `all` | No date restriction |
| `today` | Photos captured on today's date |
| `thisWeek` | Photos from the start of the current calendar week |
| `thisMonth` | Photos from the current calendar month |
| `custom` | Photos within a user-specified `DateTimeRange` |

## Presentation Layer

### Providers

| Class | Type | Responsibility |
|-------|------|---------------|
| `GalleryProvider` | `ChangeNotifier` | Loads photos and entries via repositories; manages `GalleryFilter` selection, custom date range (`_customStartDate`/`_customEndDate`), entry filter (`_selectedEntryId`), loading state, and filtered photo list |

`GalleryProvider` applies all active filters client-side via `_applyFilters()` after every filter change or data load. Photos are sorted newest-first (`capturedAt` descending).

### Screens

| Class | Type | Purpose |
|-------|------|---------|
| `GalleryScreen` | `StatefulWidget` | Main gallery screen — 3-column photo grid, active filters chip bar, filter bottom sheet trigger |
| `_FilterSheet` | `StatelessWidget` (private) | Bottom sheet — date filter chips, custom date range picker, entry dropdown |
| `_PhotoViewerScreen` | `StatefulWidget` (private) | Full-screen viewer — `PageView` with swipe navigation, `InteractiveViewer` for pinch-zoom, caption/notes/timestamp/attribution panel |

`GalleryScreen` navigates back to `toolbox` as its fallback route (`safeGoBack(context, fallbackRouteName: 'toolbox')`).

## DI Wiring (`di/gallery_providers.dart`)

`galleryProviders(...)` returns a `List<SingleChildWidget>` registered at Tier 4:

- `ChangeNotifierProvider` for `GalleryProvider` — constructed with injected `PhotoRepository` and `DailyEntryRepository`

Cross-feature repository injection is intentional: gallery is a read-only aggregation view, not a data owner.

## Architectural Patterns

### Lightweight Presentation Feature
Gallery has no data layer, no use cases, and no domain models. It is a pure presentation-tier aggregation — `GalleryProvider` reads from two external repositories and manages view state only.

### Client-Side Filtering
All filtering (date range, entry) is applied in-memory by `GalleryProvider._applyFilters()`. No query-time filtering is performed against the repository or SQLite. This is appropriate given the expected photo volume per project.

### Inline Full-Screen Viewer
The full-screen viewer (`_PhotoViewerScreen`) is a private class within `gallery_screen.dart`, navigated via `Navigator.push` (not go_router). It receives the full photo list and initial index, enabling swipe navigation without additional provider lookups.

### No Repository Pattern Ownership
Gallery does not define or own any repository interface. It consumes `PhotoRepository` (from `photos/domain/repositories/`) and `DailyEntryRepository` (from `entries/domain/repositories/`) as injected dependencies.

## Relationships to Other Features

| Feature | Relationship |
|---------|-------------|
| **Photos** | Primary data source — `PhotoRepository.getPhotosForProject()` provides all photo records |
| **Entries** | Filter data source — `DailyEntryRepository.getByProjectId()` populates the entry filter dropdown |
| **Projects** | Context source — `GalleryScreen` reads `ProjectProvider.selectedProject` to get the active project ID |
| **Auth** | Attribution display — `UserAttributionText` widget shows the uploader's name in the full-screen viewer |
| **Toolbox** | Navigation parent — toolbox hub routes to `GalleryScreen` |
