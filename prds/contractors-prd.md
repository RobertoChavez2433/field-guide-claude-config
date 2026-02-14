# Contractors PRD

## Purpose
Track the companies (prime and sub-contractors) working on a construction project, along with their equipment and personnel, so inspectors can log which contractors are on-site each day and what resources they are using.

## Core Capabilities
- CRUD operations for contractors scoped to a project
- Contractor type classification (prime vs. sub-contractor)
- Equipment tracking per contractor (machinery, tools)
- Personnel type management (laborer, operator, foreman, etc.)
- Personnel count tracking per entry per contractor
- Junction tables linking contractors and equipment to daily entries

## Data Model
- Primary entities:
  - `contractors` (SQLite table) -- companies on the project
  - `equipment` (SQLite table) -- machinery/tools per contractor
  - `personnel_types` (SQLite table) -- worker role categories
  - `entry_contractors` (junction) -- which contractors appear on an entry
  - `entry_equipment` (junction) -- which equipment was used on an entry
  - `entry_personnel_counts` (junction) -- headcounts per contractor per entry
- Key fields (contractors): `id`, `project_id`, `name`, `type` (prime/sub), `contact_name`, `phone`, `created_at`, `updated_at`
- Key fields (equipment): `id`, `contractor_id`, `name`, `description`
- Sync: Sync to Cloud -- contractors and equipment are created locally and synced via the sync queue

## User Flow
From the entry wizard, the inspector selects which contractors were on-site that day. For each contractor, they can record equipment usage and personnel headcounts by type. Contractors and equipment are managed at the project level and reused across entries.

## Offline Behavior
Full read/write offline. Contractors, equipment, and personnel types are stored in SQLite with no network dependency. All changes queue to `sync_queue` for cloud push when connectivity resumes. Conflict resolution uses last-write-wins at the record level.

## Dependencies
- Features: projects (parent scope), entries (junction linkage)
- Packages: `sqflite` (local storage), `provider` (state), `uuid` (ID generation)

## Owner Agent
backend-data-layer-agent
