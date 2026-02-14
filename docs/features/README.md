# Feature Documentation

This folder contains overviews and architecture documentation for all 13 features of the Construction Inspector App.

## Structure

Each feature has two documents:
- **`feature-{name}-overview.md`** - Quick reference, purpose, capabilities, data model, sync strategy
- **`feature-{name}-architecture.md`** - Deep-dive technical architecture, implementation patterns

## Features

| Feature | Primary Agent | Overview | Architecture |
|---------|---------------|----------|--------------|
| Auth | auth-agent | [overview](feature-auth-overview.md) | [architecture](feature-auth-architecture.md) |
| PDF | pdf-agent | [overview](feature-pdf-overview.md) | [architecture](feature-pdf-architecture.md) |
| Sync | backend-supabase-agent | [overview](feature-sync-overview.md) | [architecture](feature-sync-architecture.md) |
| Contractors | backend-data-layer-agent | [overview](feature-contractors-overview.md) | [architecture](feature-contractors-architecture.md) |
| Dashboard | frontend-flutter-specialist-agent | [overview](feature-dashboard-overview.md) | [architecture](feature-dashboard-architecture.md) |
| Entries | frontend-flutter-specialist-agent | [overview](feature-entries-overview.md) | [architecture](feature-entries-architecture.md) |
| Locations | backend-data-layer-agent | [overview](feature-locations-overview.md) | [architecture](feature-locations-architecture.md) |
| Photos | backend-data-layer-agent | [overview](feature-photos-overview.md) | [architecture](feature-photos-architecture.md) |
| Projects | backend-data-layer-agent | [overview](feature-projects-overview.md) | [architecture](feature-projects-architecture.md) |
| Quantities | backend-data-layer-agent | [overview](feature-quantities-overview.md) | [architecture](feature-quantities-architecture.md) |
| Settings | frontend-flutter-specialist-agent | [overview](feature-settings-overview.md) | [architecture](feature-settings-architecture.md) |
| Toolbox | backend-data-layer-agent | [overview](feature-toolbox-overview.md) | [architecture](feature-toolbox-architecture.md) |
| Weather | frontend-flutter-specialist-agent | [overview](feature-weather-overview.md) | [architecture](feature-weather-architecture.md) |

## How Agents Use This

Each agent loads relevant feature documentation via their `specialization.shared_rules` frontmatter. This provides context for:
- Understanding feature scope and constraints
- Identifying feature-to-feature dependencies
- Implementing feature-specific patterns
- Maintaining architectural consistency

### Agent Specializations

- **auth-agent** → Auth docs
- **pdf-agent** → PDF docs
- **backend-supabase-agent** → Sync docs
- **frontend-flutter-specialist-agent** → Dashboard, Entries, Settings, Weather docs
- **backend-data-layer-agent** → Contractors, Locations, Photos, Projects, Quantities, Toolbox docs
- **planning-agent** → All feature docs (cross-cutting)
- **code-review-agent** → All feature docs (read-only)
- **qa-testing-agent** → All feature docs (test perspective)

## Quick Links

- [PRDs](../../prds/) - Product requirements for all features
- [Architecture Rules](../../architecture-decisions/) - Constraints per feature
- [Implementation Guides](../guides/) - How-to guides for common patterns
