---
feature: projects
type: overview
scope: Project Management & Setup
updated: 2026-03-30
---

# Projects Feature Overview

## Purpose

The Projects feature manages construction projects from setup through completion. Each project represents a distinct job (e.g., a highway reconstruction, bridge repair, or local agency work). Projects store core metadata (name, mode, budget, timeline), define project-level resources (contractors, locations, equipment), and serve as the context for all daily entries and documentation. Projects are the central entity of the app — all other data is scoped to a project.

## Key Responsibilities

- **Project Creation**: Create new projects with name, budget, mode (MDOT/Local Agency), and timeline
- **Project Configuration**: Define project details (contractor relationships, locations, equipment types, personnel categories)
- **Project Mode Management**: Support MDOT (state-level) and Local Agency modes with different workflows
- **Bid Document Management**: Link PDF bid documents to projects (for extraction); manual and PDF-import sources
- **Budget Management**: Track project budget and bid items for quantity tracking
- **Project Listing**: Display all projects with filtering (on-device, not-downloaded) and search
- **Project Navigation**: Set current project context for downstream features via `ProjectSwitcher`
- **Inspector Assignment**: Assign company members to projects via `ProjectAssignmentProvider`
- **Sync Enrollment**: Enroll projects for background sync via `ProjectLifecycleService` and `SyncedProjectRepository`
- **Sync Health**: Surface per-project sync status via `ProjectSyncHealthProvider`
- **Remote Import**: Fetch and import company projects from Supabase via `ProjectImportRunner`

## Key Files

### Models

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/projects/data/models/project.dart` | `Project` | Project record with budget, timeline, mode |
| `lib/features/projects/data/models/project_mode.dart` | `ProjectMode` (enum) | MDOT vs Local Agency modes |
| `lib/features/projects/data/models/project_assignment.dart` | `ProjectAssignment` | Inspector assignment to a project |
| `lib/features/projects/data/models/assignable_member.dart` | `AssignableMember` | Company member eligible for assignment |
| `lib/features/projects/data/models/merged_project_entry.dart` | `MergedProjectEntry` | Combined project+entry view for reporting |

### Repositories & Services

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/projects/data/repositories/project_repository.dart` | `ProjectRepositoryImpl` | Project CRUD operations (implements `ProjectRepository`) |
| `lib/features/projects/data/repositories/synced_project_repository.dart` | `SyncedProjectRepository` | Manages `synced_projects` table for sync enrollment |
| `lib/features/projects/data/repositories/company_members_repository.dart` | `CompanyMembersRepository` | Fetches company member profiles from Supabase for assignment wizard |
| `lib/features/projects/data/repositories/project_assignment_repository.dart` | `ProjectAssignmentRepository` | CRUD for project inspector assignments |
| `lib/features/projects/data/services/project_lifecycle_service.dart` | `ProjectLifecycleService` | Handles project import (enroll), device removal, and DB deletion lifecycle |

### Domain

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/projects/domain/repositories/project_repository.dart` | `ProjectRepository` (abstract) | Domain contract for project persistence |
| `lib/features/projects/domain/repositories/project_remote_datasource.dart` | `ProjectRemoteDatasource` (abstract) | Domain contract for remote project data |
| `lib/features/projects/domain/usecases/delete_project_use_case.dart` | `DeleteProjectUseCase` | Orchestrates project deletion with cascade |
| `lib/features/projects/domain/usecases/fetch_remote_projects_use_case.dart` | `FetchRemoteProjectsUseCase` | Fetches available projects from Supabase |
| `lib/features/projects/domain/usecases/load_assignments_use_case.dart` | `LoadAssignmentsUseCase` | Loads current inspector assignments for a project |
| `lib/features/projects/domain/usecases/load_company_members_use_case.dart` | `LoadCompanyMembersUseCase` | Loads assignable company members for the assignment wizard |

### Screens

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/projects/presentation/screens/project_list_screen.dart` | `ProjectListScreen` | Lists all projects; handles on-device/remote filtering and project switching |
| `lib/features/projects/presentation/screens/project_setup_screen.dart` | `ProjectSetupScreen` | Multi-step wizard for project creation and configuration |

### Providers

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/projects/presentation/providers/project_provider.dart` | `ProjectProvider` | Core project state: current project, list, CRUD, filter (`CompanyFilter`) |
| `lib/features/projects/presentation/providers/project_assignment_provider.dart` | `ProjectAssignmentProvider` | Assignment state: load/add/remove inspectors on a project |
| `lib/features/projects/presentation/providers/project_settings_provider.dart` | `ProjectSettingsProvider` | Per-project settings state management |
| `lib/features/projects/presentation/providers/project_sync_health_provider.dart` | `ProjectSyncHealthProvider` | Per-project sync health status (`ProjectSyncStatus` enum) |
| `lib/features/projects/presentation/providers/project_import_runner.dart` | `ProjectImportRunner` | Drives remote project import flow (`ImportState` enum) |

### Widgets (13)

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/projects/presentation/widgets/add_contractor_dialog.dart` | `AddContractorDialog` | Dialog to add a contractor to a project |
| `lib/features/projects/presentation/widgets/add_equipment_dialog.dart` | `AddEquipmentDialog` | Dialog to add equipment type to a project |
| `lib/features/projects/presentation/widgets/add_location_dialog.dart` | `AddLocationDialog` | Dialog to add a location to a project |
| `lib/features/projects/presentation/widgets/assignments_step.dart` | `AssignmentsStep` | Setup wizard step for inspector assignments |
| `lib/features/projects/presentation/widgets/bid_item_dialog.dart` | `BidItemDialog` | Dialog to manually create a bid item |
| `lib/features/projects/presentation/widgets/equipment_chip.dart` | `EquipmentChip` | Chip widget representing an equipment type |
| `lib/features/projects/presentation/widgets/pay_item_source_dialog.dart` | `PayItemSourceDialog` | Dialog to choose bid item source (manual vs PDF import) |
| `lib/features/projects/presentation/widgets/project_delete_sheet.dart` | `ProjectDeleteSheet` | Bottom sheet for confirming project deletion |
| `lib/features/projects/presentation/widgets/project_details_form.dart` | `ProjectDetailsForm` | Form for editing core project details |
| `lib/features/projects/presentation/widgets/project_empty_state.dart` | `ProjectEmptyState` | Empty-state UI with variant enum (`EmptyStateVariant`) |
| `lib/features/projects/presentation/widgets/project_filter_chips.dart` | `ProjectFilterChips` | Filter chips for on-device/not-downloaded views |
| `lib/features/projects/presentation/widgets/project_import_banner.dart` | `ProjectImportBanner` | Banner shown during remote project import |
| `lib/features/projects/presentation/widgets/project_switcher.dart` | `ProjectSwitcher` | Bottom-sheet picker for switching the active project |
| `lib/features/projects/presentation/widgets/project_tab_bar.dart` | `ProjectTabBar` | Tab bar for project list (implements `PreferredSizeWidget`) |
| `lib/features/projects/presentation/widgets/removal_dialog.dart` | `RemovalDialog` | Dialog for choosing remove-from-device vs full delete (`RemovalChoice` enum) |

## Data Sources

- **SQLite**: Persists project records with metadata, budget, timeline, and child tables (contractors, locations, bid_items, personnel_types, daily_entries, project_assignments)
- **`synced_projects` table**: Tracks which projects are enrolled on this device for background sync
- **Bid PDFs**: Optional PDF documents linked to projects (extracted via `pdf` feature); can also be imported remotely
- **Supabase**: Remote project profiles and company member data for assignment wizard and project import

## Integration Points

**Depends on:**
- `core/database` — SQLite schema for projects and all child tables
- `sync` — `SyncControlService` used by `ProjectLifecycleService` during enrollment
- `locations` — Locations created within project context
- `contractors` — Contractors assigned to projects
- `pdf` — PDF extraction for bid item import

**Required by:**
- `dashboard` — Current project context for home screen
- `entries` — Entries scoped to projects
- `quantities` — Bid items and quantities scoped to projects
- `contractors` — Contractor lists filtered per project
- `locations` — Locations filtered per project
- `photos` — Photos belong to projects
- `sync` — Sync enrollment and health status driven by projects feature
- All features — Projects provide the primary data isolation context

## Offline Behavior

Projects are **fully offline-capable**. Creation, configuration, and editing occur entirely offline. All data persists in SQLite. Bid PDF linking is local. Project import (from Supabase) and the assignment wizard require connectivity. Cloud sync handles async push. Inspectors can set up and manage projects entirely offline; sync happens during dedicated sync operations.

## Edge Cases & Limitations

- **Project Deletion**: `ProjectLifecycleService` supports both hard-delete (remove from device) and sync-and-remove; child data cascade is explicit per-table
- **Budget Validation**: No validation of budget amount against bid items; no automatic alerts if overrun
- **Multiple Projects**: Users can have multiple projects; only one selected at a time
- **Bid Document Linking**: PDF linking is manual or via remote import (no auto-detection of new PDFs)
- **Archived Projects**: No archive functionality; completed projects remain in list indefinitely
- **Mode Immutability**: `ProjectMode` cannot be changed after creation (hard requirement for state transitions)
- **Assignment Security**: `CompanyMembersRepository` does not enforce role authorization — callers (`LoadCompanyMembersUseCase`, `ProjectSetupScreen`) must verify admin/engineer role before invoking

## Detailed Specifications

See `rules/database/schema-patterns.md` for:
- SQLite schema for projects table and relationships
- Indexing for efficient project queries

See `rules/sync/sync-patterns.md` for:
- Sync enrollment via `ProjectLifecycleService.enrollProject`
- `synced_projects` table semantics
