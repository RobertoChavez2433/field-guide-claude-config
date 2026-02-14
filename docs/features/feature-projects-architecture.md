---
feature: projects
type: architecture
scope: Project Management & Setup
updated: 2026-02-13
---

# Projects Feature Architecture

## Data Model

### Core Entities

| Entity | Fields | Type | Notes |
|--------|--------|------|-------|
| **Project** | id, name, mode, budget, bidDocument, startDate, endDate, createdAt, updatedAt, syncStatus | Model | Main project record |
| **ProjectMode** | mdot, localAgency | Enum | Workflow mode for project |

### Key Models

**Project**:
- `name`: Display name (required; e.g., "Highway 101 Reconstruction")
- `mode`: Enum {mdot, localAgency} - determines workflow and field requirements
- `budget`: Total project budget in USD (nullable)
- `bidDocument`: File path to bid PDF (nullable; linked during setup)
- `startDate`: Project start date (nullable)
- `endDate`: Project end date (nullable)
- `syncStatus`: Enum {pending, synced} for cloud sync tracking

**ProjectMode**:
- `mdot` - State-level project with MDOT workflows and requirements
- `localAgency` - Local agency project with simplified workflows

## Relationships

### Project Hierarchy
```
Project (1)
    ├─→ DailyEntry[] (all entries for project)
    ├─→ Location[] (all job site locations)
    ├─→ Contractor[] (all assigned contractors)
    ├─→ Equipment[] (all equipment available)
    ├─→ PersonnelType[] (all personnel categories)
    ├─→ BidItem[] (all extracted bid items from PDF)
    ├─→ Photo[] (all photos for project)
    └─→ InspectorForm[] (all forms created in project)
```

## Repository Pattern

### ProjectRepository

**Location**: `lib/features/projects/data/repositories/project_repository.dart`

```dart
class ProjectRepository {
  // CRUD
  Future<Project> create(Project project)
  Future<Project?> getById(String id)
  Future<List<Project>> listAll()
  Future<void> update(Project project)
  Future<void> delete(String id)

  // Specialized Queries
  Future<Project?> getCurrentProject()
  Future<void> setCurrentProject(String projectId)
  Future<List<Project>> listByMode(ProjectMode mode)
  Future<int> countByMode(ProjectMode mode)
}
```

## State Management

### Provider Type: ChangeNotifier

**ProjectProvider** (`lib/features/projects/presentation/providers/project_provider.dart`):

```dart
class ProjectProvider extends ChangeNotifier {
  // State
  List<Project> _projects = [];
  Project? _currentProject;
  bool _isLoading = false;
  String? _error;

  // Getters
  List<Project> get projects => _projects;
  Project? get currentProject => _currentProject;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get hasCurrentProject => _currentProject != null;

  // Methods
  Future<void> loadProjects()
  Future<void> createProject(Project project)
  Future<void> updateProject(Project project)
  Future<void> deleteProject(String id)
  Future<void> setCurrentProject(String projectId)
  Future<void> clearCurrentProject()
}
```

**ProjectSettingsProvider** (`lib/features/projects/presentation/providers/project_settings_provider.dart`):

Manages project-specific settings (not shown here; domain-specific implementation).

### Initialization Lifecycle

```
App Start
    ↓
checkAuthAndNavigate()
    ├─→ If authenticated: ProjectProvider.loadProjects()
    │   ├─→ _isLoading = true
    │   │
    │   ├─→ Repository.listAll()
    │   │   └─→ SQLite query all projects
    │   │
    │   ├─→ _projects = results
    │   ├─→ _currentProject = previously selected (if any)
    │   ├─→ _isLoading = false
    │   └─→ notifyListeners() → navigate to Dashboard or ProjectList
    │
    └─→ If not authenticated: navigate to LoginScreen
```

### Project Selection Flow

```
Project List Screen Loaded
    ↓
User sees list of all projects
    ├─→ ProjectProvider.projects displayed as list items
    │
    ├─→ User taps project
    │   ├─→ ProjectProvider.setCurrentProject(projectId)
    │   │   ├─→ Repository.setCurrentProject(id)
    │   │   │   └─→ SQLite UPDATE (persist user preference)
    │   │   │
    │   │   ├─→ _currentProject = project
    │   │   └─→ notifyListeners()
    │   │
    │   └─→ Router navigates to Dashboard with projectId
    │
    └─→ Dashboard loads with current project context
        └─→ All downstream features read projectId from provider
```

### Project Creation Flow

```
User taps "New Project" button
    ↓
Project Setup Screen opened (multi-step wizard)
    ├─→ Step 1: Basic info (name, mode, budget, dates)
    ├─→ Step 2: Add locations
    ├─→ Step 3: Add contractors
    ├─→ Step 4: Add equipment types
    ├─→ Step 5: Add personnel types
    ├─→ Step 6: Link bid document (optional)
    │
    ├─→ User completes wizard
    │   ├─→ createProject(project) called
    │   │   ├─→ ProjectRepository.create()
    │   │   │   └─→ SQLite INSERT
    │   │   │
    │   │   ├─→ _projects.add(newProject)
    │   │   ├─→ _currentProject = newProject (auto-select)
    │   │   └─→ notifyListeners()
    │   │
    │   └─→ Router navigates to Dashboard
    │
    └─→ New project now available for entry creation
```

## Offline Behavior

**Fully offline**: Project creation, configuration, and selection happen entirely offline. All data persists in SQLite. Bid PDF linking is local file system. Cloud sync handles async push. Inspectors can set up projects entirely offline; sync happens during dedicated sync operations.

### Read Path (Offline)
- Project list queries SQLite (all projects or by mode)
- Current project selection persisted locally
- No cloud dependency

### Write Path (Offline)
- Project creation/updates written immediately to SQLite
- Settings changes (current project) persisted immediately
- All changes tagged with `syncStatus: pending`

## Testing Strategy

### Unit Tests (Model-level)
- **Project**: Constructor, copyWith, toMap/fromMap
- **ProjectMode**: Enum handling, serialization
- **Budget validation**: Non-negative amounts
- **Date validation**: startDate < endDate

Location: `test/features/projects/data/models/project_test.dart`

### Repository Tests (Data-level)
- **CRUD operations**: Create, read, update, delete projects
- **Current project**: Get/set current project (persistence)
- **Query filters**: List by mode, count by mode
- **Offline behavior**: All tests mock database

Location: `test/features/projects/data/repositories/project_repository_test.dart`

### Widget Tests (Provider-level)
- **ProjectProvider**: Mock repository, trigger operations, verify state
- **Project list**: Verify projects displayed, selection updates
- **Current project**: Verify set/clear current project
- **Navigation**: Select project → navigate to dashboard

Location: `test/features/projects/presentation/providers/project_provider_test.dart`

### Integration Tests
- **Create project**: New project wizard → setup locations/contractors → complete → project in list
- **Select project**: Create 2 projects → select first → verify currentProject is first
- **Edit project**: Update budget/dates → verify persisted

Location: `test/features/projects/presentation/screens/`

### Test Coverage
- ≥ 90% for repository (critical data)
- ≥ 85% for provider (state management)
- 80% for screens (wizard flow testing)

## Performance Considerations

### Target Response Times
- Load all projects: < 500 ms (typically < 20 projects)
- Create project: < 200 ms (single INSERT)
- Set current project: < 100 ms (UPDATE only)

### Memory Constraints
- Project in memory: ~500 bytes
- Project list (20 projects): ~10 KB

### Optimization Opportunities
- Cache project list (unlikely to change during session)
- Lazy-load project details (load only when viewing setup)
- Batch operations (if bulk project import added later)

## File Locations

```
lib/features/projects/
├── data/
│   ├── models/
│   │   ├── models.dart
│   │   ├── project.dart
│   │   └── project_mode.dart
│   │
│   ├── datasources/
│   │   ├── local/
│   │   │   ├── local.dart
│   │   │   └── project_local_datasource.dart
│   │   └── remote/
│   │       ├── remote.dart
│   │       └── project_remote_datasource.dart
│   │
│   └── repositories/
│       ├── repositories.dart
│       └── project_repository.dart
│
├── presentation/
│   ├── screens/
│   │   ├── screens.dart
│   │   ├── project_list_screen.dart
│   │   └── project_setup_screen.dart
│   │
│   ├── widgets/
│   │   ├── widgets.dart
│   │   ├── project_details_form.dart
│   │   ├── add_location_dialog.dart
│   │   ├── add_contractor_dialog.dart
│   │   ├── add_equipment_dialog.dart
│   │   ├── bid_item_dialog.dart
│   │   └── pay_item_source_dialog.dart
│   │
│   ├── providers/
│   │   ├── providers.dart
│   │   ├── project_provider.dart
│   │   └── project_settings_provider.dart
│   │
│   └── presentation.dart
│
└── projects.dart                     # Feature entry point

lib/core/database/
└── database_service.dart             # SQLite schema for projects table
```

### Import Pattern

```dart
// Within projects feature
import 'package:construction_inspector/features/projects/data/models/project.dart';
import 'package:construction_inspector/features/projects/data/models/project_mode.dart';
import 'package:construction_inspector/features/projects/data/repositories/project_repository.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_provider.dart';

// Barrel export
import 'package:construction_inspector/features/projects/projects.dart';
```

