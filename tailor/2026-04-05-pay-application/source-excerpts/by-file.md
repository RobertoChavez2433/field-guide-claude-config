# Source Excerpts — By File

## lib/core/database/schema/entry_export_tables.dart (full)
See `patterns/schema-pattern.md` — full CREATE TABLE + indexes for the closest existing analog.

## lib/core/database/schema/form_export_tables.dart (full)
See `patterns/schema-pattern.md` — full CREATE TABLE + indexes for another analog.

## lib/core/database/schema/quantity_tables.dart (full)
```dart
class QuantityTables {
  static const String createBidItemsTable = '''
    CREATE TABLE bid_items (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      item_number TEXT NOT NULL,
      description TEXT NOT NULL,
      unit TEXT NOT NULL,
      bid_quantity REAL NOT NULL,
      unit_price REAL,
      bid_amount REAL,
      measurement_payment TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
  ''';

  static const String createEntryQuantitiesTable = '''
    CREATE TABLE entry_quantities (
      id TEXT PRIMARY KEY,
      entry_id TEXT NOT NULL,
      bid_item_id TEXT NOT NULL,
      quantity REAL NOT NULL,
      notes TEXT,
      project_id TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (entry_id) REFERENCES daily_entries(id) ON DELETE CASCADE,
      FOREIGN KEY (bid_item_id) REFERENCES bid_items(id) ON DELETE CASCADE
    )
  ''';

  static const List<String> indexes = [
    'CREATE INDEX idx_bid_items_project ON bid_items(project_id)',
    'CREATE INDEX idx_bid_items_deleted_at ON bid_items(deleted_at)',
    'CREATE INDEX idx_entry_quantities_entry ON entry_quantities(entry_id)',
    'CREATE INDEX idx_entry_quantities_deleted_at ON entry_quantities(deleted_at)',
  ];
}
```

## lib/features/sync/adapters/simple_adapters.dart (full)
See `patterns/sync-adapter-pattern.md` — complete 13 AdapterConfig entries including entry_exports and form_exports file adapter configs with buildStoragePath functions.

## lib/features/sync/engine/sync_registry.dart (full)
See `patterns/sync-adapter-pattern.md` — complete registration order and SyncRegistry class.

## lib/features/sync/engine/sync_engine_tables.dart (triggers)
- `triggeredTables`: 22 tables (line 133-156)
- `tablesWithDirectProjectId`: 14 tables (line 164-169)
- `tablesWithBuiltinFilter`: ['inspector_forms'] (line 173)
- `triggersForTable()`: generates 3 triggers (INSERT/UPDATE/DELETE) per table, gated by `sync_control.pulling='0'`

## lib/core/config/app_terminology.dart (full)
```dart
class AppTerminology {
  static bool useMdotTerms = false;
  static String get dailyReport => useMdotTerms ? 'Daily Work Report' : "Inspector's Daily Report";
  static String get dailyReportShort => useMdotTerms ? 'DWR' : 'IDR';
  static String get bidItem => useMdotTerms ? 'Pay Item' : 'Bid Item';
  static String get bidItemPlural => useMdotTerms ? 'Pay Items' : 'Bid Items';
  static String get contractModification => useMdotTerms ? 'Change Order' : 'Contract Modification';
  static String get pdfFilenamePrefix => useMdotTerms ? 'DWR' : 'IDR';
  static void setMode({required bool mdotMode}) { useMdotTerms = mdotMode; }
}
```

## lib/features/auth/presentation/providers/auth_provider.dart:216
```dart
bool get canEditFieldData => isApproved && (_userProfile?.canEditFieldData ?? false);
```

## lib/features/quantities/domain/repositories/entry_quantity_repository.dart (full)
```dart
abstract class EntryQuantityRepository implements BaseRepository<EntryQuantity> {
  Future<List<EntryQuantity>> getByEntryId(String entryId);
  Future<List<EntryQuantity>> getByBidItemId(String bidItemId);
  Future<double> getTotalUsedForBidItem(String bidItemId);
  Future<Map<String, double>> getTotalUsedByProject(String projectId);
  Future<RepositoryResult<EntryQuantity>> create(EntryQuantity quantity);
  Future<RepositoryResult<EntryQuantity>> updateQuantity(EntryQuantity quantity);
  Future<void> deleteByEntryId(String entryId);
  Future<void> deleteByBidItemId(String bidItemId);
  Future<int> getCountByEntry(String entryId);
  Future<void> insertAll(List<EntryQuantity> quantities);
  Future<RepositoryResult<void>> saveQuantitiesForEntry(String entryId, List<EntryQuantity> quantities);
}
```

## lib/features/quantities/domain/repositories/bid_item_repository.dart (full)
```dart
abstract class BidItemRepository implements ProjectScopedRepository<BidItem> {
  Future<BidItem?> getByItemNumber(String projectId, String itemNumber);
  Future<List<BidItem>> search(String projectId, String query);
  Future<RepositoryResult<BidItem>> updateBidItem(BidItem bidItem);
  Future<void> deleteByProjectId(String projectId);
  Future<void> insertAll(List<BidItem> bidItems);
}
```
