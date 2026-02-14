# Photos PRD

## Purpose
Enable inspectors to capture and attach photographic documentation to daily entries, providing visual evidence of site conditions, work progress, and issues. Photos are a critical component of construction inspection records and appear in generated PDF reports.

## Core Capabilities
- Capture photos from device camera or select from gallery
- Attach photos to a specific daily entry within a project
- Optional GPS geo-tagging (latitude/longitude) from device hardware
- Optional association with a project location via `location_id`
- Caption and notes fields for describing what the photo documents
- Custom filename support via rename dialog
- Thumbnail display in entry views and report screens
- Photo detail dialog for full-size viewing with metadata
- Local file storage with cloud sync of file and metadata

## Data Model
- Primary entity: `photos` (SQLite table)
- Key fields: `id` (UUID), `entry_id` (FK to daily_entries), `project_id` (FK to projects), `file_path` (local device path), `filename`, `remote_path` (cloud URL, null until synced), `notes`, `caption`, `location_id` (optional FK to locations), `latitude`, `longitude`, `captured_at`, `sync_status` (pending/synced/error), `created_at`, `updated_at`
- Foreign keys: `entry_id` -> `daily_entries(id)` CASCADE, `project_id` -> `projects(id)` CASCADE, `location_id` -> `locations(id)` SET NULL
- Indexes: `idx_photos_entry`, `idx_photos_project`, `idx_photos_sync_status`
- Sync: Sync to Cloud -- photo metadata syncs via sync queue; binary file uploads to Supabase Storage separately

## User Flow
During entry creation or from the report screen, the inspector taps "Add Photo" and chooses camera or gallery. After capture/selection, they can rename the file and add a caption or notes. The photo appears as a thumbnail in the entry's photo section. Tapping a thumbnail opens the detail dialog showing full-size image, caption, GPS coordinates, and timestamp.

## Offline Behavior
Full read/write offline. Photos are saved to local device storage immediately. Metadata is written to SQLite with `sync_status: pending`. File path is always local-first. When connectivity returns, the sync feature uploads the binary file to Supabase Storage and updates `remote_path`. If the device runs low on storage, photos are the largest consumer -- no automatic cleanup is performed; the user manages storage manually.

## Dependencies
- Features: entries (parent entry), projects (project scope), locations (optional location reference), pdf (photos included in reports), sync (file + metadata upload)
- Packages: `sqflite` (metadata storage), `provider` (state), `uuid` (ID generation), `image` (preprocessing if needed), `supabase_flutter` (storage upload)

## Owner Agent
backend-data-layer-agent (data layer), frontend-flutter-specialist-agent (presentation/widgets)
