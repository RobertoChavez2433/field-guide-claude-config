---
feature: toolbox
type: architecture
scope: Inspector Forms, Calculations, Todos, and Media Gallery
updated: 2026-02-13
---

# Toolbox Feature Architecture

## Data Model

### Core Entities

| Entity | Fields | Type | Notes |
|--------|--------|------|-------|
| **InspectorForm** | id, projectId, name, template, fields[], createdAt, updatedAt | Model | Form definition and schema |
| **FormResponse** | id, formId, entryId, responseData, submittedAt, syncStatus, createdAt, updatedAt | Model | Form submission and answers |
| **TodoItem** | id, projectId, title, description, dueDate, priority, completed, completedAt, createdAt, updatedAt | Model | Todo list item |
| **CalculationHistory** | id, projectId, type, inputs, output, calculatedAt, createdAt | Model | Calculation result history |
| **FormFieldEntry** | id, fieldName, fieldType, value | Value Object | Individual form field |

### Key Models

**InspectorForm**:
- `projectId`: Required; forms scoped to projects
- `name`: Display name (e.g., "Material Density Test")
- `template`: JSON form schema defining fields
- `fields`: Extracted field list for discovery

**FormResponse**:
- `formId`: Foreign key to InspectorForm
- `entryId`: Optional link to DailyEntry
- `responseData`: JSON map of fieldName → value
- `syncStatus`: Pending/synced for cloud sync

**TodoItem**:
- `projectId`: Required; todos scoped to projects
- `priority`: Enum {low, medium, high}
- `completed`: Boolean status
- `completedAt`: Timestamp when marked done

**CalculationHistory**:
- `type`: Enum {density, tonnage, material_estimate}
- `inputs`: JSON map of input parameters
- `output`: Calculated result value

## Relationships

### Project → Forms (1-N)
```
Project (1)
    ├─→ InspectorForm[] (forms for project)
    │   ├─→ FormResponse[] (submissions of this form)
    │   │   └─→ DailyEntry (optional entry reference)
    │   │
    │   └─→ Fields metadata (for auto-fill)
    │
    ├─→ CalculationHistory[] (results of calculations in project)
    │   └─→ Inputs/outputs for reference
    │
    └─→ TodoItem[] (todos for project)
```

## Repository Pattern

### InspectorFormRepository

**Location**: `lib/features/toolbox/data/repositories/inspector_form_repository.dart`

```dart
class InspectorFormRepository {
  // CRUD
  Future<InspectorForm> create(InspectorForm form)
  Future<InspectorForm?> getById(String id)
  Future<List<InspectorForm>> listByProject(String projectId)
  Future<void> update(InspectorForm form)
  Future<void> delete(String id)
}
```

### FormResponseRepository

**Location**: `lib/features/toolbox/data/repositories/form_response_repository.dart`

```dart
class FormResponseRepository {
  // CRUD
  Future<FormResponse> create(FormResponse response)
  Future<FormResponse?> getById(String id)
  Future<List<FormResponse>> listByForm(String formId)
  Future<List<FormResponse>> listByEntry(String entryId)
  Future<void> update(FormResponse response)
  Future<void> delete(String id)

  // Specialized
  Future<List<FormResponse>> listByStatus(SyncStatus status)
}
```

### CalculatorService

**Location**: `lib/features/toolbox/data/services/calculator_service.dart`

```dart
class CalculatorService {
  // Calculations
  double calculateDensity({required double weight, required double volume})
  double calculateTonnage({required double cubicYards, required double densityPcf})
  double calculateMaterialEstimate({required double quantityNeeded, required double densityPcf})

  // History
  Future<void> savCalculationHistory(CalculationHistory history)
  Future<List<CalculationHistory>> getHistory(String projectId, {String? type})
}
```

### FormParsingService

**Location**: `lib/features/toolbox/data/services/form_parsing_service.dart`

```dart
class FormParsingService {
  // Field discovery
  List<FormFieldEntry> parseFormFields(InspectorForm form)
  List<String> discoverFieldNames(String formJson)

  // Auto-fill
  Future<Map<String, dynamic>> generateAutoFillData(
    String entryId,
    String formId,
    Map<String, String> semanticAliases,
  )
}
```

## State Management

### Provider Type: ChangeNotifier

**InspectorFormProvider** (`lib/features/toolbox/presentation/providers/inspector_form_provider.dart`):

```dart
class InspectorFormProvider extends ChangeNotifier {
  // State
  List<InspectorForm> _forms = [];
  InspectorForm? _currentForm;
  bool _isLoading = false;
  String? _error;

  // Getters
  List<InspectorForm> get forms => _forms;
  InspectorForm? get currentForm => _currentForm;
  bool get isLoading => _isLoading;

  // Methods
  Future<void> loadByProject(String projectId)
  Future<void> createForm(InspectorForm form)
  Future<void> deleteForm(String id)
  Future<void> selectForm(String formId)
}
```

**TodoProvider** (`lib/features/toolbox/presentation/providers/todo_provider.dart`):

```dart
class TodoProvider extends ChangeNotifier {
  // State
  List<TodoItem> _todos = [];
  bool _isLoading = false;

  // Getters
  List<TodoItem> get todos => _todos;
  List<TodoItem> get activeTodos => _todos.where((t) => !t.completed).toList();
  List<TodoItem> get completedTodos => _todos.where((t) => t.completed).toList();

  // Methods
  Future<void> loadByProject(String projectId)
  Future<void> createTodo(TodoItem todo)
  Future<void> completeTodo(String id)
  Future<void> deleteTodo(String id)
}
```

**CalculatorProvider** (`lib/features/toolbox/presentation/providers/calculator_provider.dart`):

```dart
class CalculatorProvider extends ChangeNotifier {
  // State
  List<CalculationHistory> _history = [];

  // Methods
  double calculateDensity({required double weight, required double volume})
  Future<void> saveDensityCalculation(...)
  Future<void> loadHistory(String projectId)
}
```

### Initialization Lifecycle

```
Toolbox Home Screen Loaded
    ↓
initState() calls provider initialization
    ├─→ InspectorFormProvider.loadByProject(projectId)
    ├─→ TodoProvider.loadByProject(projectId)
    └─→ CalculatorProvider.loadHistory(projectId)

Each provider:
    ├─→ _isLoading = true
    ├─→ Repository.listByProject(projectId)
    └─→ _list = results, _isLoading = false
        notifyListeners() → displays in tabs
```

### Form Filling Flow

```
User selects form from list
    ↓
InspectorFormProvider.selectForm(formId) called
    ├─→ _currentForm = form
    ├─→ notifyListeners()
    └─→ Router navigates to FormFillScreen

Form Fill Screen Loaded
    ├─→ Parses form fields
    ├─→ Optional: Loads auto-fill data
    │   ├─→ FormParsingService.generateAutoFillData()
    │   ├─→ Maps previous entry data to form fields
    │   └─→ Pre-populates matching fields
    │
    ├─→ User fills form fields
    │
    ├─→ User submits form
    │   ├─→ FormResponseRepository.create(FormResponse)
    │   │   └─→ SQLite INSERT
    │   │
    │   ├─→ _history updated (if calculator)
    │   └─→ notifyListeners() → success message
    │
    └─→ Form submitted, linked to entry (optional)
```

## Offline Behavior

**Fully offline**: Forms, calculations, todos, and gallery browsing happen entirely offline. All data persists in SQLite. Cloud sync handles async push of form responses. Inspectors can use all toolbox features entirely offline; sync happens during dedicated sync operations.

### Read Path (Offline)
- Form list queries SQLite by projectId
- Todo queries SQLite
- Calculation history loaded from SQLite
- Photo gallery queries from photos feature
- No cloud dependency

### Write Path (Offline)
- Form responses written immediately to SQLite
- Todos created/completed immediately
- Calculation history saved immediately
- All changes local until sync

## Testing Strategy

### Unit Tests (Service-level)
- **CalculatorService**: Density, tonnage, estimate calculations with known inputs
- **FormParsingService**: Field discovery, auto-fill mapping
- **Validation**: Forms with missing required fields rejected

Location: `test/features/toolbox/data/services/`

### Repository Tests (Data-level)
- **CRUD operations**: Create, read, update, delete forms, responses, todos
- **Query filters**: List by projectId, form, status
- **Offline behavior**: All tests mock database

Location: `test/features/toolbox/data/repositories/`

### Widget Tests (Provider-level)
- **InspectorFormProvider**: Load forms, select form, verify state
- **TodoProvider**: Load todos, complete, delete, verify counts
- **CalculatorProvider**: Calculate, save history, verify persisted
- **Form fill**: Parse fields, fill form, submit, verify response saved

Location: `test/features/toolbox/presentation/providers/`

### Integration Tests
- **Full form workflow**: Select form → fill fields → auto-fill works → submit → response persisted
- **Calculator**: Input values → calculate → save history → display in history
- **Todo lifecycle**: Create → complete → display in completed list

Location: `test/features/toolbox/presentation/screens/`

### Test Coverage
- ≥ 90% for services (calculation and parsing logic)
- ≥ 85% for repositories (data persistence)
- ≥ 80% for providers (state management)
- 70% for screens (form UI complex; focus on critical paths)

## Performance Considerations

### Target Response Times
- Load forms: < 500 ms (typically < 10 forms)
- Parse form fields: < 200 ms (JSON parsing)
- Calculate density: < 50 ms (arithmetic)
- Load todos: < 300 ms
- Gallery render: < 1 second (lazy-load photos)

### Memory Constraints
- Form template: ~5-10 KB per form
- Form response: ~500 bytes per response
- Todo item: ~100 bytes per todo
- Calculation: ~50 bytes per history entry

### Optimization Opportunities
- Cache forms by project (avoid repeated queries)
- Lazy-load form fields (parse on demand)
- Paginate gallery (50 photos per page)
- Batch form submissions (if bulk upload added)

## File Locations

```
lib/features/toolbox/
├── data/
│   ├── models/
│   │   ├── models.dart
│   │   ├── inspector_form.dart
│   │   ├── form_response.dart
│   │   ├── todo_item.dart
│   │   ├── calculation_history.dart
│   │   └── [other models]
│   │
│   ├── services/
│   │   ├── services.dart
│   │   ├── form_parsing_service.dart
│   │   ├── calculator_service.dart
│   │   ├── density_calculator_service.dart
│   │   ├── auto_fill_engine.dart
│   │   └── [other services]
│   │
│   ├── datasources/
│   │   ├── local/
│   │   │   ├── local_datasources.dart
│   │   │   ├── inspector_form_local_datasource.dart
│   │   │   ├── form_response_local_datasource.dart
│   │   │   ├── todo_item_local_datasource.dart
│   │   │   └── calculation_history_local_datasource.dart
│   │   └── remote/
│   │       ├── remote_datasources.dart
│   │       └── [remote datasources]
│   │
│   └── repositories/
│       ├── repositories.dart
│       ├── inspector_form_repository.dart
│       └── form_response_repository.dart
│
├── presentation/
│   ├── screens/
│   │   ├── screens.dart
│   │   ├── toolbox_home_screen.dart
│   │   ├── forms_list_screen.dart
│   │   ├── form_fill_screen.dart
│   │   ├── calculator_screen.dart
│   │   ├── gallery_screen.dart
│   │   ├── todos_screen.dart
│   │   └── form_import_screen.dart
│   │
│   ├── widgets/
│   │   ├── widgets.dart
│   │   ├── dynamic_form_field.dart
│   │   ├── form_fields_tab.dart
│   │   ├── form_preview_tab.dart
│   │   ├── form_status_card.dart
│   │   ├── form_thumbnail.dart
│   │   ├── auto_fill_indicator.dart
│   │   ├── table_rows_section.dart
│   │   └── [other widgets]
│   │
│   ├── providers/
│   │   ├── providers.dart
│   │   ├── inspector_form_provider.dart
│   │   ├── form_import_provider.dart
│   │   ├── todo_provider.dart
│   │   ├── calculator_provider.dart
│   │   ├── gallery_provider.dart
│   │   └── [other providers]
│   │
│   ├── utils/
│   │   └── field_icon_utils.dart
│   │
│   └── presentation.dart
│
└── toolbox.dart                      # Feature entry point

lib/core/database/
└── database_service.dart             # SQLite schema for forms, responses, todos, calculations
```

### Import Pattern

```dart
// Within toolbox feature
import 'package:construction_inspector/features/toolbox/data/models/inspector_form.dart';
import 'package:construction_inspector/features/toolbox/data/services/calculator_service.dart';
import 'package:construction_inspector/features/toolbox/presentation/providers/inspector_form_provider.dart';

// Barrel export
import 'package:construction_inspector/features/toolbox/toolbox.dart';
```

