# Entries PRD

## Purpose
Enable inspectors to create, edit, and manage daily construction log entries -- the core record of what happened on a job site each day. Entries are the central entity that ties together weather, activities, contractors, equipment, personnel, quantities, and photos into a single daily report.

## Core Capabilities
- Create daily entries scoped to a project and location with date selection
- Multi-step entry wizard for structured data capture (basics, contractors, quantities, photos, safety)
- Weather recording (condition, temperature range)
- Free-text fields for activities, site safety, SESC measures, traffic control, visitors, and extras/overruns
- Entry status lifecycle: draft -> complete -> submitted
- Digital signature capture with timestamp
- Calendar-based entry list view with format toggling
- Read-only report view for completed entries with PDF generation actions
- Inline editing of contractors, personnel counts, equipment, and quantities from the report screen

## Data Model
- Primary entity: `daily_entries` (SQLite table)
- Key fields: `id`, `project_id`, `location_id`, `date`, `weather`, `temp_low`, `temp_high`, `activities`, `site_safety`, `sesc_measures`, `traffic_control`, `visitors`, `extras_overruns`, `signature`, `signed_at`, `status` (draft/complete/submitted), `sync_status` (pending/synced/error)
- Related junction tables: `entry_contractors`, `entry_equipment`, `entry_personnel_counts`, `entry_quantities`
- Sync: Sync to Cloud -- entries are created/edited locally and pushed via sync queue

## User Flow
From the home screen, the inspector taps "New Entry" to launch the entry wizard, selecting a date and location. They step through sections to record weather, activities, contractors on-site, quantities installed, and photos. Saving marks the entry as draft. When complete, they can sign and submit. The entries list shows all entries for the active project in a calendar view, and tapping an entry opens the report screen.

## Offline Behavior
Full read/write offline. Entries, junction records, and all associated data are stored in SQLite. The entry wizard works entirely against local storage. Changes queue to `sync_queue` with `sync_status` tracking per entry. Conflict resolution uses last-write-wins.

## Dependencies
- Features: projects (parent scope), locations (entry location), contractors (on-site tracking), quantities (installed amounts), photos (site documentation), weather (conditions), pdf (report generation)
- Packages: `sqflite`, `provider`, `uuid`, `go_router`, `intl`

## Owner Agent
backend-data-layer-agent (data layer), frontend-flutter-specialist-agent (presentation)
