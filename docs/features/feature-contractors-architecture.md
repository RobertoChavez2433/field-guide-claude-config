---
feature: contractors
type: architecture
scope: Contractor, Equipment & Personnel Management
updated: 2026-02-13
---

# Contractors Feature Architecture

## Data Model

### Core Entities

| Entity | Fields | Type | Notes |
|--------|--------|------|-------|
| **Contractor** | id, projectId, name, type, contactName, phone, createdAt, updatedAt | Model | Prime or sub contractor |
| **Equipment** | id, projectId, name, description, createdAt, updatedAt | Model | Equipment type or instance |
| **PersonnelType** | id, projectId, name, description, createdAt, updatedAt | Model | Personnel category |
| **EntryContractor** | id, entryId, contractorId, role | Junction | Links contractor to entry |
| **EntryEquipment** | id, entryId, equipmentId, hoursUsed | Junction | Links equipment to entry with usage |
| **EntryPersonnel** | id, entryId, personnelTypeId, count | Junction | Links personnel type to entry with count |

### Key Models

**Contractor**:
- `type`: Enum {prime, sub} - determines role in project hierarchy
- `contactName`: Optional contact person at contractor
- `phone`: Optional phone number
- Helper getters: `isPrime`, `isSub`

**Equipment**:
- `projectId`: Required; equipment scoped to project
- `name`: Display name (e.g., "Cement Mixer #1")
- `description`: Optional details (e.g., "10-yard mixer")

**PersonnelType**:
- `projectId`: Required; personnel types scoped to project
- `name`: Display name (e.g., "Foreman", "Laborer")
- `description`: Optional details (e.g., "On-site project lead")

**Entry***: (Junction tables)
- Connect main entities to DailyEntry
- Store entry-specific data (role, hoursUsed, count)

## Relationships

### Project → Contractors (1-N)
```
Project (1)
    ├─→ Contractor[] (prime and sub contractors)
    │   ├─→ contactName, phone (optional)
    │   └─→ Referenced in entries via EntryContractor
    │
    ├─→ Equipment[] (equipment available for project)
    │   └─→ Assigned to entries via EntryEquipment with hours
    │
    └─→ PersonnelType[] (personnel categories for project)
        └─→ Used in entries via EntryPersonnel with count
```

### Entry → Contractors/Equipment/Personnel (M-N)
```
DailyEntry (1)
    ├─→ EntryContractor[] (contractors on-site for this entry)
    │   ├─→ role: "prime", "sub", "consultant"
    │   └─→ Contractor (master record)
    │
    ├─→ EntryEquipment[] (equipment used on this entry)
    │   ├─→ hoursUsed: decimal hours
    │   └─→ Equipment (master record)
    │
    └─→ EntryPersonnel[] (personnel on-site for this entry)
        ├─→ count: integer count
        └─→ PersonnelType (master record)
```

## Repository Pattern

### ContractorRepository

**Location**: `lib/features/contractors/data/repositories/contractor_repository.dart`

```dart
class ContractorRepository {
  // CRUD
  Future<Contractor> create(Contractor contractor)
  Future<Contractor?> getById(String id)
  Future<List<Contractor>> listByProject(String projectId)
  Future<void> update(Contractor contractor)
  Future<void> delete(String id)

  // Specialized Queries
  Future<List<Contractor>> listByType(String projectId, ContractorType type)
  Future<int> countByProject(String projectId)
  Future<List<Contractor>> listActiveByEntry(String entryId)
}
```

### EquipmentRepository

**Location**: `lib/features/contractors/data/repositories/equipment_repository.dart`

```dart
class EquipmentRepository {
  // CRUD
  Future<Equipment> create(Equipment equipment)
  Future<Equipment?> getById(String id)
  Future<List<Equipment>> listByProject(String projectId)
  Future<void> update(Equipment equipment)
  Future<void> delete(String id)

  // Specialized Queries
  Future<int> countByProject(String projectId)
  Future<List<Equipment>> listUsedByEntry(String entryId)
}
```

### PersonnelTypeRepository

**Location**: `lib/features/contractors/data/repositories/personnel_type_repository.dart`

```dart
class PersonnelTypeRepository {
  // CRUD
  Future<PersonnelType> create(PersonnelType type)
  Future<PersonnelType?> getById(String id)
  Future<List<PersonnelType>> listByProject(String projectId)
  Future<void> update(PersonnelType type)
  Future<void> delete(String id)

  // Specialized Queries
  Future<int> countByProject(String projectId)
  Future<List<PersonnelType>> listUsedByEntry(String entryId)
}
```

### Entry*Repository

**EntryContractorRepository**, **EntryEquipmentRepository**, **EntryPersonnelRepository**:
- Manage junction table relationships
- Methods: `addToEntry()`, `removeFromEntry()`, `updateHours()/count()`

## State Management

### Provider Type: ChangeNotifier

**ContractorProvider** (`lib/features/contractors/presentation/providers/contractor_provider.dart`):

```dart
class ContractorProvider extends ChangeNotifier {
  // State
  List<Contractor> _contractors = [];
  bool _isLoading = false;
  String? _error;

  // Getters
  List<Contractor> get contractors => _contractors;
  List<Contractor> get primes => _contractors.where((c) => c.isPrime).toList();
  List<Contractor> get subs => _contractors.where((c) => c.isSub).toList();
  bool get isLoading => _isLoading;
  String? get error => _error;

  // Methods
  Future<void> loadByProject(String projectId)
  Future<void> createContractor(Contractor contractor)
  Future<void> updateContractor(Contractor contractor)
  Future<void> deleteContractor(String id)
  Future<void> addToEntry(String entryId, String contractorId, String role)
  Future<void> removeFromEntry(String entryId, String contractorId)
}
```

**EquipmentProvider** (`lib/features/contractors/presentation/providers/equipment_provider.dart`):

```dart
class EquipmentProvider extends ChangeNotifier {
  // State
  List<Equipment> _equipment = [];
  bool _isLoading = false;

  // Getters
  List<Equipment> get equipment => _equipment;
  bool get isLoading => _isLoading;

  // Methods
  Future<void> loadByProject(String projectId)
  Future<void> createEquipment(Equipment equipment)
  Future<void> updateEquipment(Equipment equipment)
  Future<void> deleteEquipment(String id)
  Future<void> addToEntry(String entryId, String equipmentId, double hours)
  Future<void> removeFromEntry(String entryId, String equipmentId)
}
```

**PersonnelTypeProvider** (`lib/features/contractors/presentation/providers/personnel_type_provider.dart`):

```dart
class PersonnelTypeProvider extends ChangeNotifier {
  // State
  List<PersonnelType> _types = [];
  bool _isLoading = false;

  // Getters
  List<PersonnelType> get types => _types;
  bool get isLoading => _isLoading;

  // Methods
  Future<void> loadByProject(String projectId)
  Future<void> createType(PersonnelType type)
  Future<void> updateType(PersonnelType type)
  Future<void> deleteType(String id)
  Future<void> addToEntry(String entryId, String typeId, int count)
  Future<void> removeFromEntry(String entryId, String typeId)
}
```

### Initialization Lifecycle

```
Project Setup Screen Loaded
    ↓
initState() calls provider initialization
    ├─→ ContractorProvider.loadByProject(projectId)
    ├─→ EquipmentProvider.loadByProject(projectId)
    └─→ PersonnelTypeProvider.loadByProject(projectId)

Each provider:
    ├─→ _isLoading = true → shows skeleton
    ├─→ Repository.listByProject(projectId)
    └─→ _list = results, _isLoading = false
        notifyListeners() → displays list
```

### Entry Assignment Flow

```
Entry Detail Screen → Add Contractor Dialog
    ↓
User selects contractor from list
    ├─→ Selects role (e.g., "prime", "sub")
    │
    ├─→ addToEntry(entryId, contractorId, role) called
    │   ├─→ EntryContractorRepository.addToEntry()
    │   │   └─→ Inserts to entry_contractors junction table
    │   │
    │   ├─→ _contractors updated locally
    │   └─→ notifyListeners() → displays updated list
    │
    └─→ DailyEntry now has contractor assigned
        └─→ Entry detail shows contractor in list
```

## Offline Behavior

**Fully offline**: Contractor, equipment, and personnel management occur entirely offline. All data persists in SQLite. Cloud sync handles async push. Inspectors can manage contractors entirely offline; sync happens during dedicated sync operations.

### Read Path (Offline)
- Contractor/equipment/personnel lists query SQLite by projectId
- Entry assignments lazy-loaded from junction tables
- No cloud dependency

### Write Path (Offline)
- Contractor creation/updates written immediately to SQLite
- Entry assignments (via junction tables) persisted immediately
- All changes local until sync

## Testing Strategy

### Unit Tests (Model-level)
- **Contractor**: Constructor, copyWith, type enum handling
- **Equipment/PersonnelType**: Constructor, copyWith
- **Enum handling**: ContractorType.values.byName() serialization

Location: `test/features/contractors/data/models/`

### Repository Tests (Data-level)
- **CRUD operations**: Create, read, update, delete contractors/equipment/personnel
- **Query filters**: List by projectId, type, usage
- **Junction tables**: Add/remove from entry, update hours/count
- **Offline behavior**: All tests mock database

Location: `test/features/contractors/data/repositories/`

### Widget Tests (Provider-level)
- **ContractorProvider**: Mock repository, trigger operations, verify state
- **Equipment/PersonnelType providers**: Similar pattern
- **List display**: Verify contractors/equipment/personnel displayed
- **Type filtering**: Verify prime/sub filtering works

Location: `test/features/contractors/presentation/providers/`

### Integration Tests
- **Create and assign**: New contractor → assign to entry → verify in entry detail
- **Update and sync**: Change contractor info → verify persisted → ready for sync
- **Multi-entity**: Create contractors + equipment + personnel → assign to same entry

Location: `test/features/contractors/presentation/`

### Test Coverage
- ≥ 90% for repositories (critical data)
- ≥ 85% for providers (state management)
- 70% for screens (UI testing)

## Performance Considerations

### Target Response Times
- Load 20 contractors: < 300 ms
- Add contractor to entry: < 100 ms
- Save contractor info: < 100 ms

### Memory Constraints
- Contractor list: ~100 bytes per contractor × N
- Equipment list: ~80 bytes per equipment × N
- Personnel list: ~60 bytes per type × N

### Optimization Opportunities
- Cache contractors by project (avoid repeated queries)
- Lazy-load junction data (load only when viewing entry)
- Batch operations (add multiple contractors in single transaction)

## File Locations

```
lib/features/contractors/
├── data/
│   ├── models/
│   │   ├── models.dart
│   │   ├── contractor.dart
│   │   ├── equipment.dart
│   │   ├── personnel_type.dart
│   │   ├── entry_contractor.dart
│   │   ├── entry_equipment.dart
│   │   └── entry_personnel.dart
│   │
│   ├── datasources/
│   │   ├── local/
│   │   │   ├── local_datasources.dart
│   │   │   ├── contractor_local_datasource.dart
│   │   │   ├── equipment_local_datasource.dart
│   │   │   ├── personnel_type_local_datasource.dart
│   │   │   └── entry_*_local_datasource.dart
│   │   └── remote/
│   │       ├── remote_datasources.dart
│   │       └── [remote datasources]
│   │
│   └── repositories/
│       ├── repositories.dart
│       ├── contractor_repository.dart
│       ├── equipment_repository.dart
│       └── personnel_type_repository.dart
│
├── presentation/
│   ├── providers/
│   │   ├── providers.dart
│   │   ├── contractor_provider.dart
│   │   ├── equipment_provider.dart
│   │   └── personnel_type_provider.dart
│   │
│   └── presentation.dart
│
└── contractors.dart                  # Feature entry point

lib/core/database/
└── database_service.dart             # SQLite schema for all contractor-related tables
```

### Import Pattern

```dart
// Within contractors feature
import 'package:construction_inspector/features/contractors/data/models/contractor.dart';
import 'package:construction_inspector/features/contractors/data/repositories/contractor_repository.dart';
import 'package:construction_inspector/features/contractors/presentation/providers/contractor_provider.dart';

// Barrel export
import 'package:construction_inspector/features/contractors/contractors.dart';
```

