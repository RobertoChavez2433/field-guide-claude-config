# Pattern: Table Adapter & Scope Type (Pull Filtering)

## How We Do It
Every synced table has a concrete `TableAdapter` subclass that declares its FK dependencies (for push ordering), its `ScopeType` (for pull filtering), and type converters (for column-level data transformation). The `ScopeType` enum determines how the SyncEngine filters records during pull: `direct` (company_id), `viaProject` (project_id IN synced_projects), `viaEntry` (same as viaProject after denormalization), `viaContractor` (contractor_id chain). The SyncRegistry holds all adapters in FK dependency order.

## Exemplars

### ScopeType (scope_type.dart:13-29)
```dart
enum ScopeType {
  direct,       // company_id filter (projects, project_assignments)
  viaProject,   // project_id IN synced_projects
  viaEntry,     // semantically via entry, but SQL same as viaProject
  viaContractor, // contractor_id → contractors.project_id
}
```

### TableAdapter (table_adapter.dart:15-180, abstract base)
Key overridable properties:
- `tableName`, `scopeType`, `fkDependencies`
- `converters`, `localOnlyColumns`, `remoteOnlyColumns`
- `skipPull`, `insertOnly`, `isFileAdapter`
- `shouldSkipPush(localRecord)`, `naturalKeyColumns`
- `fkColumnMap` (per-record FK blocking)
- `pullFilter(companyId, userId)` (custom ScopeType.direct filter)

### SyncRegistry (sync_registry.dart:63-107)
```dart
class SyncRegistry {
  static final SyncRegistry instance = SyncRegistry._();
  final List<TableAdapter> adapters = [];
  final Map<String, TableAdapter> _byName = {};

  void registerAdapters(List<TableAdapter> adapterList) { ... }
  TableAdapter adapterFor(String tableName) { ... }
  List<String> get dependencyOrder => adapters.map((a) => a.tableName).toList();
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `convertForRemote` | `table_adapter.dart:134` | `Map<String, dynamic> convertForRemote(Map<String, dynamic> local)` | Pre-push conversion |
| `convertForLocal` | `table_adapter.dart:155` | `Map<String, dynamic> convertForLocal(Map<String, dynamic> remote)` | Post-pull conversion |
| `shouldSkipPush` | `table_adapter.dart:96` | `bool shouldSkipPush(Map<String, dynamic> localRecord)` | Per-record push skip |
| `pullFilter` | `table_adapter.dart:62` | `Map<String, dynamic> pullFilter(String companyId, String userId)` | Custom direct-scope filter |
| `adapterFor` | `sync_registry.dart:93` | `TableAdapter adapterFor(String tableName)` | Lookup adapter by name |

## All 22 Adapters

| Adapter | ScopeType | skipPull | insertOnly |
|---------|-----------|----------|------------|
| ProjectAdapter | direct | false | false |
| ProjectAssignmentAdapter | direct | false | false |
| LocationAdapter | viaProject | false | false |
| ContractorAdapter | viaProject | false | false |
| EquipmentAdapter | viaContractor | false | false |
| PersonnelTypeAdapter | viaProject | false | false |
| BidItemAdapter | viaProject | false | false |
| DailyEntryAdapter | viaProject | false | false |
| EntryContractorsAdapter | viaEntry | false | false |
| EntryEquipmentAdapter | viaEntry | false | false |
| EntryPersonnelCountsAdapter | viaEntry | false | false |
| EntryQuantitiesAdapter | viaEntry | false | false |
| PhotoAdapter | viaEntry | false | false |
| InspectorFormAdapter | direct | false | false |
| FormResponseAdapter | viaProject | false | false |
| FormExportAdapter | viaEntry | false | false |
| EntryExportAdapter | viaEntry | false | false |
| DocumentAdapter | viaEntry | false | false |
| TodoItemAdapter | viaProject | false | false |
| CalculationHistoryAdapter | viaProject | false | false |
| ConsentRecordAdapter | direct | true | true |
| SupportTicketAdapter | direct | true | false |

## Gap Analysis for Spec

**No dirty-scope awareness**: Pull iterates ALL adapters regardless. The spec wants a `DirtyScopeTracker` that tracks which (project_id, table_name) pairs are dirty, and `_pull()` only processes dirty adapters during quick sync.

**ScopeType is static**: Each adapter's scope is fixed at compile time. The dirty scope concept is orthogonal — it's about WHEN to pull, not HOW to filter. The scope filter logic in `_pull()` can be reused but gated by dirty tracking.
