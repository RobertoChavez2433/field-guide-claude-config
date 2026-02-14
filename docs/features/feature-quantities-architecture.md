---
feature: quantities
type: architecture
scope: Bid Items & Quantity Tracking
updated: 2026-02-13
---

# Quantities Feature Architecture

## Data Model

### Core Entities

| Entity | Fields | Type | Notes |
|--------|--------|------|-------|
| **BidItem** | id, projectId, itemNumber, description, unit, quantity, unitPrice, bidAmount, source, confidence, createdAt, updatedAt | Model | Extracted or manual bid item |
| **EntryQuantity** | id, entryId, bidItemId, quantityCompleted, notes | Model | Quantity tracking per entry |

### Key Models

**BidItem**:
- `projectId`: Required; bid items scoped to projects
- `itemNumber`: Item ID from bid document (e.g., "1", "1.1")
- `description`: Item description (e.g., "Excavation")
- `unit`: Unit of measurement (e.g., "CY", "tons", "LF")
- `quantity`: Bid quantity (total to complete)
- `unitPrice`: Price per unit
- `bidAmount`: Total amount (quantity × unitPrice)
- `source`: Enum {extracted, manual} - how item was created
- `confidence`: 0.0-1.0 score (for extracted items; 1.0 for manual)

**EntryQuantity**:
- `entryId`: Foreign key to DailyEntry (which entry tracked this quantity)
- `bidItemId`: Foreign key to BidItem (which item was worked on)
- `quantityCompleted`: Amount completed in this entry (nullable; may be partial)
- `notes`: Optional notes about the work

## Relationships

### Project → BidItems (1-N)
```
Project (1)
    ├─→ BidItem[] (all items in project budget)
    │   ├─→ itemNumber, description, pricing
    │   └─→ EntryQuantity[] (tracking across multiple entries)
    │       └─→ DailyEntry (when work was done)
    │
    └─→ Total Budget = SUM(bidAmount) for all items
```

### Entry → Quantities (1-N)
```
DailyEntry (1)
    ├─→ EntryQuantity[] (quantities completed in this entry)
    │   └─→ BidItem (which items were worked on)
    │
    └─→ Daily Totals:
        └─→ Total completed = SUM(quantityCompleted)
```

## Repository Pattern

### BidItemRepository

**Location**: `lib/features/quantities/data/repositories/bid_item_repository.dart`

```dart
class BidItemRepository {
  // CRUD
  Future<BidItem> create(BidItem item)
  Future<BidItem?> getById(String id)
  Future<List<BidItem>> listByProject(String projectId)
  Future<void> update(BidItem item)
  Future<void> delete(String id)

  // Specialized Queries
  Future<int> countByProject(String projectId)
  Future<double> getTotalBudget(String projectId)
  Future<List<BidItem>> listBySource(String projectId, BidItemSource source)
  Future<List<BidItem>> listLowConfidence(String projectId, {double threshold = 0.6})
}
```

### EntryQuantityRepository

**Location**: `lib/features/quantities/data/repositories/entry_quantity_repository.dart`

```dart
class EntryQuantityRepository {
  // CRUD
  Future<EntryQuantity> create(EntryQuantity quantity)
  Future<EntryQuantity?> getById(String id)
  Future<List<EntryQuantity>> listByEntry(String entryId)
  Future<void> update(EntryQuantity quantity)
  Future<void> delete(String id)

  // Specialized Queries
  Future<double> getTotalCompleted(String bidItemId)
  Future<List<EntryQuantity>> listByBidItem(String bidItemId)
}
```

## State Management

### Provider Type: ChangeNotifier

**BidItemProvider** (`lib/features/quantities/presentation/providers/bid_item_provider.dart`):

```dart
class BidItemProvider extends ChangeNotifier {
  // State
  List<BidItem> _items = [];
  bool _isLoading = false;
  String? _error;

  // Getters
  List<BidItem> get items => _items;
  bool get isLoading => _isLoading;
  String? get error => _error;
  double get totalBudget => _items.fold(0, (sum, item) => sum + item.bidAmount);
  List<BidItem> get lowConfidenceItems => _items.where((i) => i.confidence < 0.6).toList();

  // Methods
  Future<void> loadByProject(String projectId)
  Future<void> createBidItem(BidItem item)
  Future<void> updateBidItem(BidItem item)
  Future<void> deleteBidItem(String id)
}
```

**EntryQuantityProvider** (`lib/features/quantities/presentation/providers/entry_quantity_provider.dart`):

```dart
class EntryQuantityProvider extends ChangeNotifier {
  // State
  List<EntryQuantity> _quantities = [];
  bool _isLoading = false;

  // Getters
  List<EntryQuantity> get quantities => _quantities;
  bool get isLoading => _isLoading;

  // Methods
  Future<void> loadByEntry(String entryId)
  Future<void> recordQuantity(EntryQuantity quantity)
  Future<void> updateQuantity(EntryQuantity quantity)
  Future<void> removeQuantity(String id)
  Future<double> getTotalCompleted(String bidItemId)
}
```

### Initialization Lifecycle

```
Quantities Screen Loaded
    ↓
initState() calls BidItemProvider.loadByProject(projectId)
    ├─→ _isLoading = true
    │
    ├─→ Repository.listByProject(projectId)
    │   └─→ SQLite query all bid items
    │
    ├─→ _items = results
    ├─→ Calculate totalBudget, lowConfidenceItems
    ├─→ _isLoading = false
    └─→ notifyListeners() → displays bid items list
```

### Quantity Tracking Flow

```
Entry Detail Screen → Quantity Section
    ↓
User selects bid item to track
    ├─→ BidItemPicker dialog opens
    │   └─→ Shows BidItemProvider.items
    │
    ├─→ User selects item and enters quantityCompleted
    │
    ├─→ recordQuantity(entryId, bidItemId, quantity) called
    │   ├─→ EntryQuantityRepository.create(EntryQuantity)
    │   │   └─→ SQLite INSERT
    │   │
    │   ├─→ _quantities.add(newQuantity)
    │   └─→ notifyListeners() → displays in entry detail
    │
    └─→ Entry now has quantity tracking
        └─→ Budget calculations updated automatically
```

## Offline Behavior

**Fully offline**: Bid item storage, quantity tracking, and budget calculations happen entirely offline. All data persists in SQLite. Cloud sync handles async push. Inspectors can track quantities entirely offline; sync happens during dedicated sync operations.

### Read Path (Offline)
- Bid item list queries SQLite by projectId
- Quantity lookups query by entryId or bidItemId
- Budget calculations local (sum operations)
- No cloud dependency

### Write Path (Offline)
- Bid item creation/updates written immediately to SQLite
- Quantity tracking persisted immediately
- All changes local until sync

## Testing Strategy

### Unit Tests (Model-level)
- **BidItem**: Constructor, copyWith, budget calculation (quantity × unitPrice)
- **EntryQuantity**: Constructor, copyWith
- **Confidence handling**: Extracted items 0.0-1.0, manual items 1.0

Location: `test/features/quantities/data/models/`

### Repository Tests (Data-level)
- **CRUD operations**: Create, read, update, delete items and quantities
- **Query filters**: List by projectId, bidItemId, low confidence
- **Budget calculation**: getTotalBudget() and getTotalCompleted()
- **Offline behavior**: All tests mock database

Location: `test/features/quantities/data/repositories/`

### Widget Tests (Provider-level)
- **BidItemProvider**: Mock repository, load items, verify state
- **EntryQuantityProvider**: Mock repository, record/update quantities
- **Quantities screen**: Verify bid items listed, quantities recorded, budget updated

Location: `test/features/quantities/presentation/providers/`

### Integration Tests
- **Extract and track**: PDF extraction → bid items created → quantities tracked in entry
- **Budget calculation**: Create multiple entries → track different items → verify budget totals
- **Low confidence**: Extract with low confidence → filter in UI → manual review

Location: `test/features/quantities/presentation/screens/`

### Test Coverage
- ≥ 90% for repositories (critical budget data)
- ≥ 85% for providers (state management)
- 80% for screens (quantity tracking UX)

## Performance Considerations

### Target Response Times
- Load 100 bid items: < 500 ms
- Record quantity: < 100 ms
- Calculate budget: < 50 ms (local sum operation)
- Find quantity total: < 200 ms (multi-entry query)

### Memory Constraints
- Bid item in memory: ~300 bytes
- 100 bid items: ~30 KB
- Quantity record: ~150 bytes

### Optimization Opportunities
- Cache bid items by project (avoid repeated queries)
- Lazy-load quantity details (load only when viewing entry)
- Pre-calculate budget totals (cache and update on change)
- Batch quantity updates (if bulk upload added)

## File Locations

```
lib/features/quantities/
├── data/
│   ├── models/
│   │   ├── models.dart
│   │   ├── bid_item.dart
│   │   └── entry_quantity.dart
│   │
│   ├── datasources/
│   │   ├── local/
│   │   │   ├── local_datasources.dart
│   │   │   ├── bid_item_local_datasource.dart
│   │   │   └── entry_quantity_local_datasource.dart
│   │   └── remote/
│   │       ├── remote_datasources.dart
│   │       ├── bid_item_remote_datasource.dart
│   │       └── entry_quantity_remote_datasource.dart
│   │
│   └── repositories/
│       ├── repositories.dart
│       ├── bid_item_repository.dart
│       └── entry_quantity_repository.dart
│
├── presentation/
│   ├── screens/
│   │   ├── screens.dart
│   │   ├── quantities_screen.dart
│   │   └── quantity_calculator_screen.dart
│   │
│   ├── widgets/
│   │   ├── widgets.dart
│   │   ├── quantity_summary_header.dart
│   │   ├── bid_item_card.dart
│   │   └── bid_item_detail_sheet.dart
│   │
│   ├── providers/
│   │   ├── providers.dart
│   │   ├── bid_item_provider.dart
│   │   └── entry_quantity_provider.dart
│   │
│   └── presentation.dart
│
└── quantities.dart                   # Feature entry point

lib/core/database/
└── database_service.dart             # SQLite schema for bid_items and entry_quantities tables
```

### Import Pattern

```dart
// Within quantities feature
import 'package:construction_inspector/features/quantities/data/models/bid_item.dart';
import 'package:construction_inspector/features/quantities/data/models/entry_quantity.dart';
import 'package:construction_inspector/features/quantities/data/repositories/bid_item_repository.dart';
import 'package:construction_inspector/features/quantities/presentation/providers/bid_item_provider.dart';

// Barrel export
import 'package:construction_inspector/features/quantities/quantities.dart';
```

