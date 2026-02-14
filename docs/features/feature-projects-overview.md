---
feature: projects
type: overview
scope: Project Management & Setup
updated: 2026-02-13
---

# Projects Feature Overview

## Purpose

The Projects feature manages construction projects from setup through completion. Each project represents a distinct job (e.g., a highway reconstruction, bridge repair, or local agency work). Projects store core metadata (name, mode, budget, timeline), define project-level resources (contractors, locations, equipment), and serve as the context for all daily entries and documentation.

## Key Responsibilities

- **Project Creation**: Create new projects with name, budget, mode (MDOT/Local Agency), and timeline
- **Project Configuration**: Define project details (contractor relationships, locations, equipment types, personnel categories)
- **Project Mode Management**: Support MDOT (state-level) and Local Agency modes with different workflows
- **Bid Document Management**: Link PDF bid documents to projects (for extraction)
- **Budget Management**: Track project budget and bid items for quantity tracking
- **Project Listing**: Display all projects with filtering and search
- **Project Navigation**: Set current project context for downstream features

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/projects/data/models/project.dart` | Project model with budget, timeline, mode |
| `lib/features/projects/data/models/project_mode.dart` | Enum for MDOT vs Local Agency modes |
| `lib/features/projects/data/repositories/project_repository.dart` | Project CRUD operations |
| `lib/features/projects/presentation/screens/project_list_screen.dart` | Project listing and selection |
| `lib/features/projects/presentation/screens/project_setup_screen.dart` | Project creation/configuration |
| `lib/features/projects/presentation/providers/project_provider.dart` | Project state management |

## Data Sources

- **SQLite**: Persists project records with metadata, budget, timeline
- **Bid PDFs**: Optional PDF documents linked to projects (extracted via `pdf` feature)
- **Project Locations**: Locations created and linked during project setup
- **Contractors**: Prime/sub contractors assigned during project setup
- **Equipment/Personnel**: Equipment and personnel types defined per project

## Integration Points

**Depends on:**
- `core/database` - SQLite schema for projects and related tables
- `locations` - Locations created within project context
- `contractors` - Contractors assigned to projects

**Required by:**
- `dashboard` - Current project context for home screen
- `entries` - Entries scoped to projects
- `photos` - Photos belong to projects
- `quantities` - Bid items and quantities scoped to projects
- `toolbox` - Forms scoped to projects
- All features - Projects provide context for data isolation

## Offline Behavior

Projects are **fully offline-capable**. Creation, configuration, and editing occur entirely offline. All data persists in SQLite. Bid PDF linking is local. Cloud sync handles async push. Inspectors can set up and manage projects entirely offline; sync happens during dedicated sync operations.

## Edge Cases & Limitations

- **Project Deletion**: Soft-delete only; entries and photos referencing deleted project remain accessible
- **Budget Validation**: No validation of budget amount against bid items; no automatic alerts if overrun
- **Multiple Projects**: Users can have multiple projects; only one selected at a time
- **Bid Document Linking**: PDF linking is manual (no auto-detection of new PDFs)
- **Archived Projects**: No archive functionality; completed projects remain in list indefinitely
- **Mode Immutability**: ProjectMode cannot be changed after creation (hard requirement for state transitions)

## Detailed Specifications

See `architecture-decisions/projects-constraints.md` for:
- Hard rules on project mode selection and immutability
- Budget validation and financial tracking semantics
- Project deletion and data cascade behavior

See `rules/database/schema-patterns.md` for:
- SQLite schema for projects table and relationships
- Indexing for efficient project queries

