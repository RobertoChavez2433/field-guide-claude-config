# Quantities PRD

## Purpose
Quantities tracks the work performed against contract bid items on a daily basis. Construction inspectors must document how much of each pay item was installed each day -- these records drive contractor payments and project accounting. Without accurate quantity tracking, payment disputes and budget overruns become inevitable.

## Core Capabilities
- Define bid items per project with item number, description, unit of measure, bid quantity, unit price, and measurement/payment specification text
- Record daily quantities against bid items within daily entries, with optional notes
- View quantity summary per bid item showing total installed vs. bid quantity with progress indicators
- Import bid items from PDF bid schedules via the PDF extraction pipeline
- Calculate running totals and remaining quantities across all entries for a project
- Drill into individual bid item detail sheets showing per-entry breakdown

## Data Model
- Primary entities: `BidItem` (SQLite table: `bid_items`), `EntryQuantity` (SQLite table: `entry_quantities`)
- BidItem key fields: `id`, `project_id`, `item_number`, `description`, `unit`, `bid_quantity`, `unit_price`, `measurement_payment`, `created_at`, `updated_at`
- EntryQuantity key fields: `id`, `entry_id`, `bid_item_id`, `quantity`, `notes`, `created_at`, `updated_at`
- Sync: Sync to Cloud (both tables sync via Supabase adapter)
- Foreign keys: `bid_items.project_id` -> `projects.id`, `entry_quantities.entry_id` -> `daily_entries.id`, `entry_quantities.bid_item_id` -> `bid_items.id`

## User Flow
During project setup, inspectors add bid items manually or import them from a PDF bid schedule. When creating or editing a daily entry, inspectors select which bid items had work performed that day and enter the installed quantity with optional notes. The quantities screen provides a project-level summary showing each bid item's progress toward its contracted amount.

## Offline Behavior
Full read/write offline. Bid items and entry quantities are stored in SQLite and queued for sync. The quantity calculator screen works entirely offline. PDF bid schedule import processes locally using the extraction pipeline. All summary calculations are computed from local data.

## Dependencies
- Features: projects (bid items belong to a project), entries (quantities attach to daily entries), pdf (bid schedule import)
- Packages: `uuid`, `sqflite`, `provider`

## Owner Agent
backend-data-layer-agent (models, repositories, datasources), frontend-flutter-specialist-agent (screens, widgets)
