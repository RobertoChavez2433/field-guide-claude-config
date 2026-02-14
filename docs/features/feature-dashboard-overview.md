---
feature: dashboard
type: overview
scope: Project Home & Overview Aggregation
updated: 2026-02-13
---

# Dashboard Feature Overview

## Purpose

The Dashboard feature provides the home screen and project overview interface. It aggregates data from across the app (entries, photos, quantities, contractors, weather) to display current project status, key metrics, recent activity, and quick-access shortcuts. The dashboard is the primary navigation hub after project selection.

## Key Responsibilities

- **Project Overview**: Display selected project name, location, status
- **Key Metrics**: Show entry count, photo count, quantities tracked, contractors assigned
- **Recent Activity**: Display latest entries, photos, and activity timeline
- **Quick Actions**: Shortcuts to create new entry, upload photo, view quantities
- **Budget Summary**: Display bid amount, tracked quantities, remaining budget estimate
- **Alert Display**: Show overdue items, pending photos, incomplete entries
- **Weather Integration**: Display current weather for project location (placeholder)

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` | Main dashboard layout |
| `lib/features/dashboard/presentation/widgets/dashboard_stat_card.dart` | Stats card component |
| `lib/features/dashboard/presentation/widgets/budget_overview_card.dart` | Budget display widget |
| `lib/features/dashboard/presentation/widgets/tracked_item_row.dart` | Activity list item |
| `lib/features/dashboard/presentation/widgets/alert_item_row.dart` | Alert/warning display |

## Data Sources

- **Projects**: Currently selected project context
- **Entries**: Daily entry data (count, status, recent)
- **Photos**: Photo count, recent uploads, sync status
- **Quantities**: Bid item counts, completed quantities, budget tracking
- **Contractors**: Active contractors, equipment in use
- **Weather**: Current conditions for project location

## Integration Points

**Depends on:**
- `projects` - Current project context (passed via route params)
- `entries` - Entry count, recent entries, status distribution
- `photos` - Photo count, recent photos, pending sync
- `quantities` - Budget data, quantity tracking, bid item counts
- `contractors` - Active contractor count, equipment list
- `weather` - Current weather conditions (optional)
- `locations` - Project location for weather/context

**Required by:**
- `core/router` - Dashboard is primary shell route after auth
- All features - Dashboard provides quick navigation to feature screens

## Offline Behavior

Dashboard is **fully offline-capable**. All data displayed is read from local SQLite. No network calls required. Aggregation and summary calculations happen in-memory. Cloud sync status display shows pending items, but sync itself happens separately.

## Edge Cases & Limitations

- **Real-time Updates**: Dashboard does not auto-refresh; requires screen reload or manual pull-to-refresh
- **Stale Data**: Aggregated metrics may lag behind actual data if other features don't notify observers
- **Weather Integration**: Currently placeholder; network dependency added when implemented
- **Multi-Project**: Dashboard shows only one project at a time; no cross-project view
- **Permission-Based Visibility**: All dashboard data assumes authenticated user with project access

## Detailed Specifications

See `architecture-decisions/dashboard-constraints.md` for:
- Hard rules on metric calculation and aggregation
- Real-time update vs. lazy-load trade-offs
- Weather integration requirements

See `rules/frontend/flutter-ui.md` for:
- Dashboard layout and responsive design rules
- Card component spacing and theming

