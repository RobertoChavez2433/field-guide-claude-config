---
feature: entries
type: architecture
scope: Daily Job Site Entry Management
updated: 2026-02-13
---

# Entries Feature Architecture

## Data Model

### Core Entities

| Entity | Fields | Type | Notes |
|--------|--------|------|-------|
| **DailyEntry** | id, projectId, locationId, date, weather, tempLow, tempHigh, activities, siteSafety, sescMeasures, trafficControl, visitors, extrasOverruns, signature, signedAt, status, createdAt, updatedAt, syncStatus | Model | Main entry record |
| **EntryContractor** | id, entryId, contractorId, role | Junction | Links contractors to entries |
| **EntryPersonnel** | id, entryId, personnelTypeId, count | Model | Personnel counts for entry |
| **EntryEquipment** | id, entryId, equipmentId, hours | Model | Equipment usage for entry |
| **EntryQuantity** | id, entryId, bidItemId, quantityCompleted | Model | Quantities tracked for entry |

### Key Models

**DailyEntry**:
- `date`: Report date (indexed for calendar queries)
- `status`: Enum {draft, complete, submitted}
- `weather`: Enum {sunny, cloudy, overcast, rainy, snow, windy}
- `signature`: Base64-encoded signature image or tap points
- `syncStatus`: Tracks pending/synced state for cloud sync
- All fields except signature are required for completion

**EntryContractor**, **EntryPersonnel**, **EntryEquipment**:
- Bridge tables for many-to-many relationships
- Store entry-specific metadata (role, count, hours)

**EntryQuantity**:
- Links bid items to specific entry work
- Tracks quantity completed (nullable, set if partial)

## Relationships

### Project → Entries (1-N)
```
Project (1)
    ↓
DailyEntry[] (many per project, one per date/location)
    ├─→ Location (1)
    ├─→ Photos[] (via photo.entryId)
    ├─→ Contractors[] (via EntryContractor junction)
    ├─→ Personnel[] (via EntryPersonnel)
    ├─→ Equipment[] (via EntryEquipment)
    └─→ Quantities[] (via EntryQuantity)
```

### Entry Status Lifecycle
```
Draft (initial)
    ↓
(User edits entry)
    ↓
Complete (user marks complete)
    ↓
(User signs entry)
    ↓
Submitted (signature verified)
```

### Contractor Linkage
```
Contractor (master)
    ↓
EntryContractor junction (entry-specific assignment)
    ├─→ role: "prime", "sub", "equipment_supplier"
    └─→ DailyEntry
```

## Repository Pattern

### DailyEntryRepository

**Location**: `lib/features/entries/data/repositories/daily_entry_repository.dart`

```dart
class DailyEntryRepository {
  // CRUD
  Future<DailyEntry> create(DailyEntry entry)
  Future<DailyEntry?> getById(String id)
  Future<List<DailyEntry>> listByProject(String projectId)
  Future<List<DailyEntry>> listByDate(String projectId, DateTime date)
  Future<void> update(DailyEntry entry)
  Future<void> delete(String id)

  // Specialized
  Future<List<DailyEntry>> listByDateRange(String projectId, DateTime start, DateTime end)
  Future<int> countByStatus(String projectId, EntryStatus status)
  Future<List<DailyEntry>> listByLocationAndDate(String locationId, DateTime date)
}
```

### Supporting Repositories

**EntryContractorRepository**, **EntryPersonnelRepository**, **EntryEquipmentRepository**:
- Manage junction table relationships
- Methods: `addToEntry()`, `removeFromEntry()`, `updateHours()/count()`

## State Management

### Provider Type: ChangeNotifier

**DailyEntryProvider** (`lib/features/entries/presentation/providers/daily_entry_provider.dart`):

```dart
class DailyEntryProvider extends ChangeNotifier {
  // State
  List<DailyEntry> _entries = [];
  DailyEntry? _currentEntry;
  bool _isLoading = false;
  String? _error;

  // Getters
  List<DailyEntry> get entries => _entries;
  DailyEntry? get currentEntry => _currentEntry;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get canSubmit => _currentEntry?.status == EntryStatus.complete;

  // Methods
  Future<void> loadEntriesByProject(String projectId)
  Future<void> loadEntryById(String id)
  Future<void> createEntry(DailyEntry entry)
  Future<void> updateEntry(DailyEntry entry)
  Future<void> markComplete(String entryId)
  Future<void> submitWithSignature(String entryId, String signatureData)
  Future<void> deleteEntry(String id)
  Future<void> addContractor(String entryId, String contractorId, String role)
  Future<void> removeContractor(String entryId, String contractorId)
}
```

### Initialization Lifecycle

```
Home Screen loaded
    ↓
initState() calls loadEntriesByProject()
    ├─→ _isLoading = true → shows spinner
    │
    ├─→ Repository queries SQLite by projectId, date range
    │
    └─→ _entries = results
        _isLoading = false
        notifyListeners() → rebuilds calendar/list
```

### Entry Editing Flow

```
User opens entry detail
    ↓
loadEntryById() called
    ├─→ _currentEntry = entry from database
    ├─→ Loads related contractors, personnel, equipment
    └─→ notifyListeners() → builds form

User edits field (e.g., activities)
    ↓
updateEntry() called
    ├─→ _currentEntry = updated entry
    ├─→ Repository.update() writes to SQLite
    └─→ notifyListeners() → form field updates

User marks Complete
    ↓
markComplete() called
    ├─→ Validates required fields (location, weather, activities)
    ├─→ _currentEntry.status = complete
    ├─→ Repository.update()
    └─→ notifyListeners() → enables signature capture

User signs entry
    ↓
submitWithSignature(signatureData) called
    ├─→ Validates signature not empty
    ├─→ _currentEntry.signature = signatureData
    ├─→ _currentEntry.signedAt = now()
    ├─→ _currentEntry.status = submitted
    ├─→ Repository.update()
    └─→ notifyListeners() → shows submission success
```

## Offline Behavior

**Fully offline**: Entries created, edited, and submitted entirely offline. Network-dependent sync handled separately by `sync` feature.

### Read Path (Offline)
- Entry list queries SQLite by projectId, location, date
- Related entities (contractors, equipment, photos) lazy-loaded on demand
- No cloud dependency

### Write Path (Offline)
- Entry creation/updates written immediately to SQLite
- Status changes (Draft → Complete → Submitted) persisted locally
- Signature data stored as Base64 blob in entry record
- All changes tagged with `syncStatus: pending`

### Sync Status
- Entries marked `syncStatus: pending` until synced
- Sync adapter (in `sync` feature) batches entries by status
- On successful sync, status changed to `synced`
- Failed syncs keep `pending` status for retry

## Testing Strategy

### Unit Tests (Model-level)
- **DailyEntry**: Constructor, copyWith, toMap/fromMap
- **Status validation**: Cannot submit if not complete, cannot complete if required fields missing
- **Enum handling**: WeatherCondition and EntryStatus serialization

Location: `test/features/entries/data/models/daily_entry_test.dart`

### Repository Tests (Data-level)
- **CRUD operations**: Create, read, update, delete entries
- **Query filters**: List by projectId, date range, location, status
- **Transactions**: Atomic updates of entry + related contractors/equipment
- **Offline behavior**: All tests mock database (no network)

Location: `test/features/entries/data/repositories/daily_entry_repository_test.dart`

### Widget Tests (Provider-level)
- **DailyEntryProvider**: Mock repository, trigger state changes, verify listeners called
- **Home screen calendar**: Verify entries displayed by date, count by status
- **Entry detail form**: Verify form fields populate, edits trigger updates
- **Signature capture**: Mock signature input, verify signature persisted

Location: `test/features/entries/presentation/providers/daily_entry_provider_test.dart`

### Integration Tests (Full Flow)
- **Create entry workflow**: New entry → add contractors → mark complete → sign → submit
- **Edit entry**: Load existing entry → change weather/activities → save → verify persisted
- **Navigation**: Home → entry list → detail → back → list refreshes

Location: `test/features/entries/presentation/screens/home_screen_test.dart`

### Test Coverage
- ≥ 90% for models and repositories (high-criticality data)
- ≥ 80% for providers (UI state logic)
- 70% for screens (integration testing only)

## Performance Considerations

### Target Response Times
- Load entry list (50 entries): < 500 ms
- Save entry with 5 contractors/equipment: < 1 second
- Calendar view render: < 300 ms
- Signature capture: < 100 ms (local storage only)

### Memory Constraints
- Entry list in memory: ~100 KB per 50 entries
- Signature data (Base64): ~50-100 KB per entry
- Related entities cached: ~50 KB (contractors, equipment)

### Optimization Opportunities
- Pagination for entry list (50 per page)
- Lazy load contractor details (load only when viewing entry)
- Batch signature uploads during sync (reduce network calls)
- Index on (projectId, date) for fast calendar queries

## File Locations

```
lib/features/entries/
├── data/
│   ├── models/
│   │   ├── models.dart
│   │   ├── daily_entry.dart
│   │   ├── entry_contractor.dart
│   │   ├── entry_personnel.dart
│   │   ├── entry_equipment.dart
│   │   └── entry_quantity.dart
│   │
│   ├── datasources/
│   │   ├── local/
│   │   │   ├── local_datasources.dart
│   │   │   └── daily_entry_local_datasource.dart
│   │   └── remote/
│   │       ├── remote_datasources.dart
│   │       └── daily_entry_remote_datasource.dart
│   │
│   └── repositories/
│       ├── repositories.dart
│       └── daily_entry_repository.dart
│
├── presentation/
│   ├── screens/
│   │   ├── screens.dart
│   │   ├── home_screen.dart
│   │   ├── entries_list_screen.dart
│   │   └── entry_editor_screen.dart          # Unified create + edit screen
│   │
│   ├── widgets/
│   │   ├── widgets.dart
│   │   ├── entry_basics_section.dart
│   │   ├── entry_safety_section.dart
│   │   ├── contractor_editor_widget.dart
│   │   ├── bid_item_picker_sheet.dart
│   │   ├── quantity_dialog.dart
│   │   └── [report_widgets/] - Report screen specific dialogs
│   │
│   ├── providers/
│   │   ├── providers.dart
│   │   ├── daily_entry_provider.dart
│   │   └── calendar_format_provider.dart
│   │
│   └── models/
│       ├── models.dart
│       └── contractor_ui_state.dart
│
└── entries.dart                      # Feature entry point

lib/core/database/
└── database_service.dart             # SQLite schema for daily_entries table
```

### Import Pattern

```dart
// Within entries feature
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';
import 'package:construction_inspector/features/entries/data/repositories/daily_entry_repository.dart';
import 'package:construction_inspector/features/entries/presentation/providers/daily_entry_provider.dart';

// From other features (barrel export)
import 'package:construction_inspector/features/entries/entries.dart';
```

