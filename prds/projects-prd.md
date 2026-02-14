# Projects PRD

## Purpose
Projects are the top-level organizational unit in Field Guide. Every daily entry, location, contractor, bid item, photo, and form response belongs to a project. Without projects, inspectors have no context for their work.

## Core Capabilities
- Create, edit, and archive construction projects with contract metadata
- Support dual operating modes: Local Agency (Supabase sync) and MDOT (AASHTOWare sync)
- Manage project-scoped locations, contractors, equipment, and bid items from a single setup wizard
- Auto-load last active project on app startup (configurable in Settings)
- Track MDOT-specific fields: contract ID, project code, county, and district

## Data Model
- Primary entity: `Project` (SQLite table: `projects`)
- Key fields: `id`, `name`, `project_number`, `client_name`, `description`, `is_active`, `mode`, `mdot_contract_id`, `mdot_project_code`, `mdot_county`, `mdot_district`, `created_at`, `updated_at`
- Sync: Sync to Cloud (Supabase for Local Agency mode; AASHTOWare planned for MDOT mode)
- Related tables: `locations` (FK to projects), `bid_items` (FK to projects), `contractors` (project-scoped), `equipment` (FK to contractors)

## User Flow
Inspectors start by selecting or creating a project from the project list screen. The project setup wizard walks them through adding a project name, number, mode, locations, contractors, equipment, and bid items in a single guided flow. Once set up, the project becomes the active context for all daily entries.

## Offline Behavior
Full read/write offline. Projects are created and edited locally in SQLite. Changes queue to `sync_queue` for upload when connectivity returns. Project list, setup wizard, and all sub-entity management work without network. Conflict resolution uses last-write-wins with timestamps.

## Dependencies
- Features: locations, contractors, quantities (bid items), entries, sync
- Packages: `uuid`, `sqflite`, `provider`, `go_router`, `supabase_flutter`

## Owner Agent
backend-data-layer-agent (data/models, repositories), frontend-flutter-specialist-agent (presentation)
