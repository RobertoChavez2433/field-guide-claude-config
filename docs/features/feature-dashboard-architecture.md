---
feature: dashboard
type: architecture
scope: Project Home & Overview Aggregation
updated: 2026-03-30
---

# Dashboard Feature Architecture

## Overview

Dashboard is a **presentation-only** feature. It has no data layer, no repository, no DI setup, and no own domain models. All displayed data is sourced by reading from other features' providers directly via `Consumer` and `context.read<T>()`.

## Layer Structure

```
lib/features/dashboard/
├── domain/
│   └── domain.dart              # Placeholder barrel — no use cases or interfaces
├── presentation/
│   ├── presentation.dart        # Barrel re-exporting screens barrel
│   ├── screens/
│   │   ├── screens.dart         # Screens barrel
│   │   └── project_dashboard_screen.dart
│   └── widgets/
│       ├── widgets.dart         # Widgets barrel
│       ├── dashboard_stat_card.dart
│       ├── budget_overview_card.dart
│       ├── tracked_item_row.dart
│       └── alert_item_row.dart
└── dashboard.dart               # Feature barrel (domain + presentation)
```

No `data/` layer. No `di/` layer.

## Screen: ProjectDashboardScreen

`ProjectDashboardScreen` is a `StatefulWidget` with no constructor parameters. On `initState`, it uses `addPostFrameCallback` to call `_loadProjectData()`, which parallel-loads data from five providers using `Future.wait`:

| Provider called | Method |
|----------------|--------|
| `DailyEntryProvider` | `loadEntries(projectId)` |
| `LocationProvider` | `loadLocations(projectId)` |
| `BidItemProvider` | `loadBidItems(projectId)` |
| `ContractorProvider` | `loadContractors(projectId)` |
| `EntryQuantityProvider` | `loadTotalUsedByProject(projectId)` |

The project ID is obtained from `context.read<ProjectProvider>().selectedProject`.

### Build sections (rendered via `CustomScrollView` + `SliverList`)

1. **Gradient SliverAppBar** — project name, project number, client name; "New Entry" action button; "Switch project" leading icon
2. `_buildReviewDraftsCard` — shown only when `DailyEntryProvider.draftEntries.length > 0`; navigates to `drafts` route
3. `_buildQuickStats` — four `DashboardStatCard` widgets: Entries, Pay Items, Contractors, Toolbox
4. `_buildBudgetOverview` — `BudgetOverviewCard` + optional `AppBudgetWarningChip` when `BudgetSanityChecker.hasDiscrepancy(bidItems)` is true
5. `_buildTrackedItems` — top 10 bid items sorted by usage percentage (descending, only items with `used > 0`); each row is a `TrackedItemRow`
6. `_buildApproachingLimit` — bid items at `>= 75%` usage; each row is an `AlertItemRow`; hidden when list is empty

### No-project-selected state

When `ProjectProvider.selectedProject` is null (or the selected project ID is no longer in `projects`), the screen renders a centered empty state with a "View Projects" button that navigates to the `projects` route. Stale references after `removeFromDevice` are handled by clearing `selectedProject` via `addPostFrameCallback`.

## Widgets

### DashboardStatCard

`StatelessWidget`. Animated entry (scale + opacity via `TweenAnimationBuilder`). Required params: `label`, `value`, `icon`, `color`. Optional: `onTap`.

### BudgetOverviewCard

`StatelessWidget`. Params: `totalBudget`, `totalUsed`, `isLoading`. Displays total contract value, animated progress bar (color shifts to warning at 75%, error at 90%), and used/remaining sub-boxes via private `_BudgetStatBox`. Budget math is done in `_buildBudgetOverview` on the screen, not in the card itself.

### TrackedItemRow

`StatelessWidget`. Params: `item` (`BidItem`), `usedQuantity` (`double`), `onTap`. Displays a percentage badge, item number + description, and a progress bar. Color logic: error at `>90%`, warning at `>75%`, primary otherwise.

### AlertItemRow

`StatelessWidget`. Params: `item` (`BidItem`), `percentage` (`double`). No `onTap`. Displays icon (error icon at `>90%`, warning icon otherwise) and a colored percentage badge.

## State Management

Dashboard uses `Consumer`, `Consumer2`, and `Consumer3` from the Provider package to subscribe to other features' providers. It does **not** own any `ChangeNotifier`. The screen itself is `StatefulWidget` only to support `initState` data loading and the `mounted` check after async calls.

Provider subscriptions in use:

| Widget / section | Providers consumed |
|---|---|
| Root scaffold | `ProjectProvider` |
| `_buildReviewDraftsCard` | `DailyEntryProvider` |
| `_buildQuickStats` | `DailyEntryProvider`, `BidItemProvider`, `ContractorProvider` |
| `_buildBudgetOverview` | `BidItemProvider`, `EntryQuantityProvider` |
| `_buildTrackedItems` | `BidItemProvider`, `EntryQuantityProvider` |
| `_buildApproachingLimit` | `BidItemProvider`, `EntryQuantityProvider` |

## Relationships

Dashboard reads from these external features:

```
ProjectDashboardScreen
    ├─→ ProjectProvider          (projects feature)
    ├─→ DailyEntryProvider       (entries feature)
    ├─→ LocationProvider         (locations feature)
    ├─→ BidItemProvider          (quantities feature)
    ├─→ EntryQuantityProvider    (quantities feature)
    └─→ ContractorProvider       (contractors feature)
```

Budget sanity check:
```
BudgetSanityChecker.hasDiscrepancy()   (quantities/utils)
```

Dashboard has **no outbound dependencies** to data/domain layers of any feature. It only reads from providers already registered in the widget tree.

## Budget Calculation

Budget math is performed inline in `_buildBudgetOverview`, not in a separate use case:

- `totalBudget`: prefers `bidAmount` (source of truth from PDF OCR) over `bidQuantity * unitPrice` to avoid OCR comma/period inflation
- `totalUsed`: derives effective unit price from `bidAmount / bidQuantity` when `bidAmount` is present; otherwise falls back to `unitPrice`

## Offline Behavior

Fully offline. All data originates from local SQLite via the providers. No network calls are made by the dashboard. Pull-to-refresh (`RefreshIndicator` wrapping `CustomScrollView`) triggers `_loadProjectData()` again.

## Navigation

Dashboard navigates to these routes via `go_router`:

| Action | Route |
|---|---|
| New Entry button | `pushNamed('entry', pathParameters: {projectId, date})` |
| Switch project | `goNamed('projects')` |
| Draft review card | `pushNamed('drafts', pathParameters: {projectId})` |
| Entries stat card | `pushNamed('entries')` |
| Pay Items stat card | `pushNamed('quantities')` |
| Contractors stat card | `pushNamed('project-edit', queryParameters: {tab: '2'})` |
| Toolbox stat card | `pushNamed('toolbox')` |
| View All (tracked items) | `pushNamed('quantities')` |
| Approaching Limit overflow | `pushNamed('quantities')` |
