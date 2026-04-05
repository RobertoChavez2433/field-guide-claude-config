---
feature: projects
type: architecture
scope: Project Management & Setup
updated: 2026-03-30
---

# Projects Feature Architecture

Projects are the central entity in the app. Every other feature (entries, quantities, contractors, locations, photos, forms, todos) is scoped to a project.

## File Structure

```
lib/features/projects/
├── data/
│   ├── models/
│   │   ├── project.dart               # Project entity
│   │   ├── project_mode.dart          # ProjectMode enum
│   │   ├── project_assignment.dart    # ProjectAssignment entity
│   │   ├── assignable_member.dart     # AssignableMember (lightweight UI model)
│   │   ├── merged_project_entry.dart  # MergedProjectEntry (local+remote view)
│   │   └── models.dart                # Barrel
│   ├── datasources/
│   │   ├── local/
│   │   │   ├── project_local_datasource.dart
│   │   │   └── local.dart
│   │   └── remote/
│   │       ├── project_remote_datasource_impl.dart   # Supabase impl
│   │       ├── project_remote_datasource.dart        # (barrel / re-export)
│   │       └── remote.dart
│   ├── repositories/
│   │   ├── project_repository.dart           # ProjectRepositoryImpl
│   │   ├── project_assignment_repository.dart
│   │   ├── synced_project_repository.dart
│   │   ├── company_members_repository.dart
│   │   └── repositories.dart
│   ├── services/
│   │   └── project_lifecycle_service.dart
│   └── data.dart
├── domain/
│   ├── repositories/
│   │   ├── project_repository.dart        # Abstract ProjectRepository
│   │   └── project_remote_datasource.dart # Abstract ProjectRemoteDatasource
│   └── usecases/
│       ├── delete_project_use_case.dart
│       ├── fetch_remote_projects_use_case.dart
│       ├── load_assignments_use_case.dart
│       └── load_company_members_use_case.dart
├── presentation/
│   ├── providers/
│   │   ├── project_provider.dart
│   │   ├── project_assignment_provider.dart
│   │   ├── project_settings_provider.dart
│   │   ├── project_sync_health_provider.dart
│   │   ├── project_import_runner.dart
│   │   └── providers.dart
│   ├── screens/
│   │   ├── project_list_screen.dart
│   │   ├── project_setup_screen.dart
│   │   └── screens.dart
│   ├── widgets/                          # 13 widgets (see below)
│   │   └── widgets.dart
│   └── presentation.dart
├── di/
│   └── projects_providers.dart
└── projects.dart
```

## Data Layer

### Models

| Class | File | Notes |
|-------|------|-------|
| `Project` | `data/models/project.dart` | Main entity — name, projectNumber, clientName, description, mode, isActive, companyId, createdByUserId, MDOT fields (mdotContractId, mdotProjectCode, mdotCounty, mdotDistrict, controlSectionId, routeStreet, constructionEng), deletedAt |
| `ProjectMode` | `data/models/project_mode.dart` | Enum: `localAgency` (Supabase sync), `mdot` (AASHTOWare sync) |
| `ProjectAssignment` | `data/models/project_assignment.dart` | Soft-deletable; projectId, userId, assignedBy, companyId — controls "My Projects" membership |
| `AssignableMember` | `data/models/assignable_member.dart` | Lightweight UI model: userId, displayName, role — shared between `CompanyMembersRepository` and the assignment wizard |
| `MergedProjectEntry` | `data/models/merged_project_entry.dart` | Wraps `Project` with isLocal, isRemoteOnly, isLocalOnly, isArchived, isAssigned, unassignedAt — used for the 3-tab project list view |

**ProjectMode** controls both backend routing and UI terminology:
- `localAgency` — syncs to Supabase; uses "Inspector's Daily Report" terminology
- `mdot` — syncs to AASHTOWare OpenAPI; uses "Daily Work Report" terminology; requires MDOT-specific fields

**Project** notable design choices:
- `projectNumber` is required and must be unique within a company
- `deletedAt` supports soft-delete (non-null = in trash)
- `isActive` = false means archived (not deleted)
- `Project.fromJson()` handles Supabase bool responses; `Project.fromMap()` handles SQLite int 0/1
- `Project.fromMetadataMap()` is a lightweight factory for enumeration (used by `FetchRemoteProjectsUseCase`)

### Datasources

**`ProjectLocalDatasource`** (`data/datasources/local/`) — extends `GenericLocalDatasource<Project>`. Table: `projects`. Provides `getActive()`, `search()`, `getByCompanyId()`, `getByProjectNumberInCompany()`, `setActive()`, `getOrphanedProjects()`, `insertAll()`, plus all base CRUD.

**`ProjectRemoteDatasourceImpl`** (`data/datasources/remote/`) — implements `ProjectRemoteDatasource` (domain interface). Single method: `softDeleteProject()` calls the `admin_soft_delete_project` Supabase RPC. The interface lives in `domain/repositories/project_remote_datasource.dart` to keep Supabase dependencies out of use cases.

### Repositories (Implementations)

| Class | Location | Purpose |
|-------|----------|---------|
| `ProjectRepositoryImpl` | `data/repositories/project_repository.dart` | Implements `ProjectRepository`. Coordinates `ProjectLocalDatasource` + `SyncControlService`. Handles project-number uniqueness checks, draft suppression, two-pass orphan cleanup |
| `ProjectAssignmentRepository` | `data/repositories/project_assignment_repository.dart` | CRUD for `project_assignments` table. Soft-deletes (sets deleted_at) so sync engine propagates tombstones |
| `SyncedProjectRepository` | `data/repositories/synced_project_repository.dart` | Manages `synced_projects` table — tracks which projects are enrolled for background sync on this device. `enroll()` / `unenroll()` are idempotent |
| `CompanyMembersRepository` | `data/repositories/company_members_repository.dart` | Fetches approved company members from Supabase `user_profiles`. Remote-only (no local cache). Returns `List<AssignableMember>` |

### Services

**`ProjectLifecycleService`** (`data/services/project_lifecycle_service.dart`) — handles three lifecycle operations:

1. **`enrollProject(projectId)`** — INSERT into `synced_projects` (idempotent, ConflictAlgorithm.ignore)
2. **`removeFromDevice(projectId)`** — hard-deletes all local child data in a single transaction (suppresses change_log triggers; preserves the `projects` metadata row for "not downloaded" visibility; returns photo file paths for cleanup)
3. **`deleteFromSupabase(projectId)`** — calls `admin_soft_delete_project` RPC; admin-only; also removes local metadata cache

Additional utilities: `getUnsyncedChangeCount()`, `getAllUnsyncedCounts()`, `canDeleteFromDatabase()`.

`removeFromDevice` uses `SyncControlService.suppressedWithDb()` so hard-deletes do not create change_log entries that would propagate to Supabase.

## Domain Layer

### Repository Interfaces

**`ProjectRepository`** (`domain/repositories/project_repository.dart`) — abstract interface extending `BaseRepository<Project>`. Key methods beyond standard CRUD: `getActive()`, `search()`, `getByCompanyId()`, `getByProjectNumberInCompany()`, `saveDraftSuppressed()`, `discardDraft()`, `create()` / `updateProject()` (return `RepositoryResult<Project>`), `setActive()`, `getCreatedByUserId()`, `getMetadataByCompanyId()`, `insertAll()`, `cleanupOrphanedProjects()`.

**`ProjectRemoteDatasource`** (`domain/repositories/project_remote_datasource.dart`) — abstract interface with `softDeleteProject(projectId)`. Lives in domain (not data) to allow use cases to depend on the interface without importing Supabase.

### Use Cases

| Class | File | Purpose |
|-------|------|---------|
| `DeleteProjectUseCase` | `domain/usecases/delete_project_use_case.dart` | Authorization check (creator or admin) → Supabase RPC soft-delete → local cascade via `SoftDeleteService`. Returns `DeleteProjectResult` with `success` + `rpcSucceeded` flags. Offline-safe: RPC failure does not block local cascade |
| `FetchRemoteProjectsUseCase` | `domain/usecases/fetch_remote_projects_use_case.dart` | Loads enrolled (local) + unenrolled projects from SQLite for the merged project view. Returns `FetchRemoteProjectsResult` with `localProjects`, `remoteProjects`, `allKnownProjectIds` |
| `LoadAssignmentsUseCase` | `domain/usecases/load_assignments_use_case.dart` | Queries `ProjectAssignmentRepository` for assigned project IDs and `SyncedProjectRepository` for unassigned_at state. Returns `AssignmentState` |
| `LoadCompanyMembersUseCase` | `domain/usecases/load_company_members_use_case.dart` | Authorization gate (`canManageProjects` required) wrapping `CompanyMembersRepository.getApprovedMembers()`. Throws `StateError` if unauthorized |

## Presentation Layer

### Providers

| Class | Type | Purpose |
|-------|------|---------|
| `ProjectProvider` | `ChangeNotifier` | Central project state: local list, merged view, selected project, role-filtered getters (`myProjects`, `companyProjects`, `archivedProjects`), tab state, search, CRUD operations |
| `ProjectAssignmentProvider` | `ChangeNotifier` | In-memory wizard state for the assignments step: member list, checked set, diff-and-save on commit |
| `ProjectSettingsProvider` | `ChangeNotifier` | Persists last-selected project ID and auto-load preference |
| `ProjectSyncHealthProvider` | `ChangeNotifier` | Cache of `Map<projectId, unsyncedCount>` + error set; exposes `getSyncStatus()` → `ProjectSyncStatus` enum |
| `ProjectImportRunner` | `ChangeNotifier` | State machine for the import banner: idle → enrolling → syncing → complete / failed |

**`ProjectProvider` key design points:**
- Initialized via `initWithAuth()` which wires an auth listener to reload projects when companyId changes and trigger sync on login
- Inspector role enforcement: `selectProject()` / `setSelectedProject()` silently reject unassigned project IDs; `filteredProjects` and `myProjects` filter by `_assignedProjectIds`
- `_buildMergedView()` computes `_mergedProjects` from `_projects` (enrolled) + `_remoteProjects` (unenrolled) with isLocal/isRemoteOnly/isLocalOnly/isArchived/isAssigned flags
- `deleteProject()` requires explicit `currentUserId` + `isAdmin` params — no ambient-identity fallback
- `CompanyFilter` enum (all / onDevice / notDownloaded) applied to the Company tab

### Screens

- **`ProjectListScreen`** — 3-tab layout: My Projects, Company, Archived. Filter chips on Company tab.
- **`ProjectSetupScreen`** — Multi-step wizard for create/edit. Steps: project details, bid items/pay items, locations, contractors, assignments.

### Widgets (14)

| Widget | Purpose |
|--------|---------|
| `ProjectFilterChips` | Filter chips for Company tab (all / on device / not downloaded) |
| `ProjectTabBar` | Tab bar widget for 3-tab project list |
| `ProjectDetailsForm` | Form fields for project name, number, mode, MDOT fields |
| `ProjectImportBanner` | Progress banner shown during project import (tracks `ProjectImportRunner`) |
| `ProjectSwitcher` | Compact selector for switching active project |
| `ProjectEmptyState` | Empty state widget for project lists |
| `EquipmentChip` | Chip for equipment entries in the setup wizard |
| `AddEquipmentDialog` | Dialog for adding equipment during setup |
| `AddLocationDialog` | Dialog for adding a location during setup |
| `BidItemDialog` | Dialog for adding bid/pay items manually |
| `PayItemSourceDialog` | Source-selection dialog (PDF extract vs manual entry) for pay items |
| `RemovalDialog` | Confirmation dialog for removing a project from device |
| `ProjectDeleteSheet` | Bottom sheet for permanent project deletion (admin only) |
| `AssignmentsStep` | Wizard step for assigning company members to a project |

## DI Wiring

**`projects_providers.dart`** (`di/`) — `projectProviders()` returns a `List<SingleChildWidget>` for insertion into the root provider tree. Registered providers:

- `ChangeNotifierProvider.value` — `ProjectSettingsProvider`
- `Provider<LoadCompanyMembersUseCase>.value` — optional; only registered when non-null (admin/engineer roles)
- `ChangeNotifierProvider` — `ProjectProvider` (created inline; wires `initWithAuth()`)
- `ChangeNotifierProvider.value` — `ProjectAssignmentProvider`
- `Provider<ProjectLifecycleService>.value`
- `ChangeNotifierProvider.value` — `ProjectSyncHealthProvider`
- `ChangeNotifierProvider.value` — `ProjectImportRunner`

The `ProjectProvider` constructor receives: `ProjectRepository`, `SyncedProjectRepository`, `DeleteProjectUseCase`, `LoadAssignmentsUseCase`, `FetchRemoteProjectsUseCase`, and a `canManageProjects` callback from `AuthProvider`.

## Key Patterns

### ProjectMode (Dual-Backend)
`ProjectMode.localAgency` syncs to Supabase; `ProjectMode.mdot` syncs to AASHTOWare. The mode also controls terminology via `AppTerminology.setMode()` (called on project selection). MDOT projects carry additional header fields (contract ID, project code, county, district, control section, route, construction engineer).

### Merged Project View
`ProjectProvider._buildMergedView()` merges enrolled (`_projects`) and unenrolled (`_remoteProjects`) into `List<MergedProjectEntry>`, deduplicating by ID. Local entries take precedence. "Not downloaded" projects are sourced from SQLite metadata (populated by background sync), never from a live Supabase query — pull-to-refresh triggers sync for freshness.

### SyncedProjectRepository (Enrollment)
`synced_projects` table tracks which projects are enrolled on this device. Enrollment drives background sync scope. `FetchRemoteProjectsUseCase` distinguishes local (enrolled) from available (unenrolled) by comparing `synced_projects` rows against all project metadata.

### Draft Suppression
`ProjectRepositoryImpl.saveDraftSuppressed()` and `discardDraft()` both run inside `SyncControlService.runSuppressed()`, ensuring draft saves and discards never create change_log entries.

### Delete Flow
`DeleteProjectUseCase` enforces: creator-or-admin check → Supabase RPC (fires server cascade trigger) → local cascade via `SoftDeleteService`. RPC failure is tolerated offline; change_log entries are preserved for deferred push. `ProjectLifecycleService.removeFromDevice()` is a separate operation — removes data from the device without touching Supabase.

### Import Runner
`ProjectImportRunner` is a state machine (idle → enrolling → syncing → complete/failed) that drives the `ProjectImportBanner` widget. Used when an inspector downloads (imports) a remote project to their device.

## Relationships

```
Project (1)
    ├─→ DailyEntry[]           (entries feature)
    ├─→ BidItem[] / PayItem[]  (quantities feature)
    ├─→ Contractor[]           (contractors feature)
    ├─→ Location[]             (locations feature)
    ├─→ Photo[]                (photos feature)
    ├─→ InspectorForm[]        (forms feature)
    ├─→ TodoItem[]             (todos feature)
    └─→ ProjectAssignment[]    (projects feature — user membership)
```

## Offline Behavior

Projects are fully offline-capable:
- Create, edit, archive, and delete all work without connectivity
- Sync status tracked via `change_log` SQLite triggers (no per-model `syncStatus` field)
- `SyncedProjectRepository` enrollment and unenrollment are local-only operations
- Assignment wizard saves to local SQLite; sync engine pushes via `ProjectAssignmentAdapter`
- `removeFromDevice` suppresses change_log triggers so local-only cleanup does not propagate deletions to Supabase
