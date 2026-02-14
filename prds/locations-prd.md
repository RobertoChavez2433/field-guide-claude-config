# Locations PRD

## Purpose
Allow inspectors to define and manage physical locations within a construction project so that daily entries, photos, and quantities can be scoped to specific areas of the job site. Locations provide spatial context for all inspection data.

## Core Capabilities
- CRUD operations for locations scoped to a project
- Name and description fields for human-readable identification
- Optional GPS coordinates (latitude/longitude) for geo-tagging
- Location selection during entry creation (required field on daily entries)
- Location reference on photos for spatial organization
- Location-based filtering and grouping of entries

## Data Model
- Primary entity: `locations` (SQLite table)
- Key fields: `id` (UUID), `project_id` (FK to projects), `name` (required), `description` (optional), `latitude` (optional REAL), `longitude` (optional REAL), `created_at`, `updated_at`
- Foreign key: `project_id` references `projects(id)` with ON DELETE CASCADE
- Index: `idx_locations_project` on `project_id`
- Sync: Sync to Cloud -- locations are created locally and pushed via sync queue

## User Flow
When setting up a project, the inspector creates locations representing distinct areas of the job site (e.g., "Station 12+50", "Bridge Deck North", "Retention Pond"). During entry creation, they select a location from a dropdown. Locations can also be edited from the report screen via an inline edit dialog. GPS coordinates can be auto-captured from the device or entered manually.

## Offline Behavior
Full read/write offline. All location data is stored in SQLite with no network dependency. New locations and edits queue to `sync_queue` for cloud push. GPS capture works offline via device hardware. Locations are loaded into `LocationProvider` on project selection and cached in memory for fast access throughout the session.

## Dependencies
- Features: projects (parent scope), entries (location_id FK), photos (optional location_id reference)
- Packages: `sqflite` (local storage), `provider` (state management), `uuid` (ID generation)

## Owner Agent
backend-data-layer-agent
