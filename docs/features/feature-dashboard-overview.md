---
feature: dashboard
type: overview
scope: Project Home & Overview Aggregation
updated: 2026-03-30
---

# Dashboard Feature Overview

## Purpose

The Dashboard feature provides the home screen and project overview interface. It aggregates data from across the app (entries, quantities, contractors, locations) to display current project status, key metrics, tracked items, and budget summary. The dashboard is the primary navigation hub after project selection.

## Key Responsibilities

- **Project Overview**: Display selected project name, location, status
- **Key Metrics**: Show entry count, quantities tracked, contractors assigned
- **Budget Summary**: Display bid amount, tracked quantities, remaining budget estimate
- **Alert Display**: Show overdue items and warning conditions
- **Tracked Items**: List quantity line items with usage progress

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` | Main dashboard layout (`ProjectDashboardScreen`) |
| `lib/features/dashboard/presentation/widgets/tracked_item_row.dart` | Quantity line-item row with usage (`TrackedItemRow`) |
| `lib/features/dashboard/presentation/widgets/alert_item_row.dart` | Alert/warning display row (`AlertItemRow`) |
| `lib/features/dashboard/presentation/widgets/budget_overview_card.dart` | Budget summary card (`BudgetOverviewCard`) |
| `lib/features/dashboard/presentation/widgets/dashboard_stat_card.dart` | Stat summary card (`DashboardStatCard`) |

## Architecture Notes

Dashboard is a **presentation-only feature**. There is no data layer, no DI module, and no dashboard-specific providers or use cases. The domain directory exists as a placeholder only (see `lib/features/dashboard/domain/domain.dart`). All data is consumed directly from other features' providers via `context.watch` / `Provider.of`.

## Integration Points

**Depends on (reads providers from):**
- `projects` — Current project context (`ProjectProvider`)
- `entries` — Entry count and status (`DailyEntryProvider`)
- `quantities` — Bid items and usage (`BidItemProvider`, `EntryQuantityProvider`)
- `contractors` — Active contractor list (`ContractorProvider`)
- `locations` — Project location context (`LocationProvider`)

**Required by:**
- `core/router` — Dashboard is the primary shell route after auth
- All features — Dashboard provides quick navigation to feature screens

## Screens

| Screen | Class | Description |
|--------|-------|-------------|
| Project Dashboard | `ProjectDashboardScreen` | Aggregated project overview; single screen; `StatefulWidget` |

## Offline Behavior

Dashboard is **fully offline-capable**. All data displayed is read from local SQLite via the upstream feature providers. No direct network calls are made. Aggregation and budget calculations happen in-memory within the screen state.

## Edge Cases & Limitations

- **Real-time Updates**: Dashboard does not auto-refresh; requires screen reload or manual pull-to-refresh
- **Stale Data**: Aggregated metrics may lag if upstream providers have not reloaded
- **Weather Integration**: Removed from current implementation; no weather dependency
- **Multi-Project**: Dashboard shows only one project at a time; no cross-project view

## Detailed Specifications

See `rules/frontend/flutter-ui.md` for:
- Dashboard layout and responsive design rules
- Card component spacing and theming
