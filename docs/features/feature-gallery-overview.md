---
feature: gallery
type: overview
scope: Photo gallery browsing and viewing
updated: 2026-03-30
---

# Gallery Feature Overview

## Purpose

The Gallery feature provides photo browsing for construction inspectors. It displays all photos associated with a selected project in a grid view, supports date-based and entry-based filtering, and offers a full-screen photo viewer with swipe navigation. Gallery is a read-only presentation feature — it does not own any data and delegates entirely to the photos and entries features for data access.

## Key Responsibilities

- **Photo Browsing**: Grid view of all photos for the active project, sorted newest-first
- **Date-Based Filtering**: Filter photos by today, this week, this month, or a custom date range
- **Entry-Based Filtering**: Filter photos by a specific daily entry via a dropdown
- **Full-Screen Viewer**: Tap any photo to enter a full-screen swipe-through viewer with caption, notes, timestamp, and user attribution
- **Active Filter Display**: Chip bar showing applied filters with per-chip and clear-all removal

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/gallery/di/gallery_providers.dart` | DI wiring — registers `GalleryProvider` with `PhotoRepository` and `DailyEntryRepository` |
| `lib/features/gallery/presentation/providers/gallery_provider.dart` | State — photo loading, filter state, `GalleryFilter` enum |
| `lib/features/gallery/presentation/screens/gallery_screen.dart` | Gallery grid screen, filter sheet, full-screen viewer |
| `lib/features/gallery/domain/domain.dart` | Domain barrel (currently empty — no use cases) |
| `lib/features/gallery/gallery.dart` | Feature barrel export |

## Screens (1)

| Screen | Route Trigger |
|--------|--------------|
| `GalleryScreen` | Navigated from toolbox hub |

## Providers (1)

| Provider | Responsibility |
|----------|---------------|
| `GalleryProvider` | Loads photos and entries for a project; manages grid view state, `GalleryFilter` selection, custom date range, entry filter, and full-screen viewer navigation |

## Integration Points

**Depends on:**
- `photos` — `PhotoRepository` and `Photo` model are the primary data source
- `entries` — `DailyEntryRepository` and `DailyEntry` model used to populate the entry filter dropdown
- `projects` — reads `ProjectProvider.selectedProject` to determine which project to load photos for
- `auth` — `UserAttributionText` widget used in the full-screen viewer to display the uploader's name

**Required by:**
- `toolbox` — navigation hub that links to `GalleryScreen`

## Offline Behavior

Gallery is **fully offline-capable**. All photos and entries are loaded from local SQLite via `PhotoRepository` and `DailyEntryRepository`. No network calls are made.
