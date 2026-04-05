# Feature Documentation

This folder contains overviews and architecture documentation for all 17 features of the Construction Inspector App.

## Structure

Each feature has two documents:
- **`feature-{name}-overview.md`** - Quick reference, purpose, capabilities, data model, sync strategy
- **`feature-{name}-architecture.md`** - Deep-dive technical architecture, implementation patterns

## Features

| Feature | Primary Rule Context | Overview | Architecture |
|---------|----------------------|----------|--------------|
| Auth | `rules/auth/supabase-auth.md` | [overview](feature-auth-overview.md) | [architecture](feature-auth-architecture.md) |
| PDF | `rules/pdf/pdf-generation.md` | [overview](feature-pdf-overview.md) | [architecture](feature-pdf-architecture.md) |
| Sync | `rules/sync/sync-patterns.md` + `rules/backend/supabase-sql.md` | [overview](feature-sync-overview.md) | [architecture](feature-sync-architecture.md) |
| Contractors | `rules/backend/data-layer.md` | [overview](feature-contractors-overview.md) | [architecture](feature-contractors-architecture.md) |
| Dashboard | `rules/frontend/flutter-ui.md` | [overview](feature-dashboard-overview.md) | [architecture](feature-dashboard-architecture.md) |
| Entries | `rules/frontend/flutter-ui.md` + `rules/backend/data-layer.md` | [overview](feature-entries-overview.md) | [architecture](feature-entries-architecture.md) |
| Locations | `rules/backend/data-layer.md` | [overview](feature-locations-overview.md) | [architecture](feature-locations-architecture.md) |
| Photos | `rules/backend/data-layer.md` + `rules/pdf/pdf-generation.md` | [overview](feature-photos-overview.md) | [architecture](feature-photos-architecture.md) |
| Projects | `rules/backend/data-layer.md` + `rules/architecture.md` | [overview](feature-projects-overview.md) | [architecture](feature-projects-architecture.md) |
| Quantities | `rules/backend/data-layer.md` | [overview](feature-quantities-overview.md) | [architecture](feature-quantities-architecture.md) |
| Settings | `rules/frontend/flutter-ui.md` | [overview](feature-settings-overview.md) | [architecture](feature-settings-architecture.md) |
| Toolbox | `rules/frontend/flutter-ui.md` | [overview](feature-toolbox-overview.md) | [architecture](feature-toolbox-architecture.md) |
| Weather | `rules/frontend/flutter-ui.md` + `rules/architecture.md` | [overview](feature-weather-overview.md) | [architecture](feature-weather-architecture.md) |

## How Implementers And Reviewers Use This

Routing tables load slim rules first. These feature docs provide deeper context when the task needs:
- Understanding feature scope and constraints
- Identifying feature-to-feature dependencies
- Implementing feature-specific patterns
- Maintaining architectural consistency

### Typical Consumers

- **auth-agent** → Auth docs
- **pdf-agent** → PDF docs
- **implement workers touching sync code** → Sync docs
- **implement workers touching presentation code** → Dashboard, Entries, Settings, Weather, Toolbox docs
- **implement workers touching data-layer code** → Contractors, Locations, Photos, Projects, Quantities docs
- **code-review-agent** → All feature docs (read-only)
- **qa-testing-agent** → All feature docs (test perspective)

## Quick Links

- [PRDs](../../prds/) - Product requirements for all features
- [Architecture Rules](../../architecture-decisions/) - Constraints per feature
- [Implementation Guides](../guides/) - How-to guides for common patterns
