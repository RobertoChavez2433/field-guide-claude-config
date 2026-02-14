# Dashboard PRD

## Purpose
Give inspectors a single-screen overview of their active project's health, including entry counts, budget tracking, location coverage, and alerts, so they can quickly assess progress without drilling into individual records.

## Core Capabilities
- Project summary header with name, number, and date range
- Entry statistics (total entries, entries this week/month, latest entry date)
- Budget overview card showing bid item totals vs. quantities installed
- Location coverage summary (locations with entries vs. total locations)
- Contractor activity summary (active contractors count)
- Alert/tracked item rows for items needing attention (over-budget items, stale locations)
- Pull-to-refresh to reload all dashboard data

## Data Model
- Primary entity: None -- the dashboard is a read-only aggregation view
- Data sources: `projects`, `daily_entries`, `locations`, `bid_items`, `entry_quantities`, `contractors`
- Key aggregations: entry count by project, sum of quantities used vs. estimated, contractor count, location count
- Sync: N/A -- dashboard reads from local SQLite; no writes

## User Flow
After selecting a project, the inspector lands on the dashboard tab (bottom navigation). The screen loads all project-scoped data in parallel and displays stat cards and alert rows. Tapping a stat card or alert navigates to the relevant detail screen (entries list, bid items, locations). Pull-down refreshes data from local storage.

## Offline Behavior
Fully functional offline. All dashboard data is aggregated from local SQLite tables. No network calls are made from the dashboard itself. Data freshness depends on the last successful sync. The dashboard does not display sync status indicators -- that responsibility belongs to the sync feature.

## Dependencies
- Features: projects (selected project context), entries (entry counts), locations (location counts), quantities (budget tracking), contractors (contractor counts)
- Packages: `provider` (reactive state from multiple providers), `go_router` (navigation to detail screens), `intl` (date/number formatting)

## Owner Agent
frontend-flutter-specialist-agent
