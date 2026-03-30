---
feature: quantities
type: architecture
scope: Bid Items & Quantity Tracking
updated: 2026-03-30
---

# Quantities Feature Architecture

## Directory Layout

```
lib/features/quantities/
├── data/
│   ├── models/
│   │   ├── models.dart
│   │   ├── bid_item.dart
│   │   └── entry_quantity.dart
│   ├── datasources/
│   │   ├── datasources.dart
│   │   ├── local/
│   │   │   ├── local_datasources.dart
│   │   │   ├── bid_item_local_datasource.dart
│   │   │   └── entry_quantity_local_datasource.dart
│   │   └── remote/
│   │       ├── remote_datasources.dart
│   │       ├── bid_item_remote_datasource.dart
│   │       └── entry_quantity_remote_datasource.dart
│   └── repositories/
│       ├── repositories.dart
│       ├── bid_item_repository_impl.dart
│       └── entry_quantity_repository_impl.dart
├── domain/
│   ├── domain.dart
│   ├── models/
│   │   ├── models.dart
│   │   └── import_batch_result.dart
│   └── repositories/
│       ├── repositories.dart
│       ├── bid_item_repository.dart
│       └── entry_quantity_repository.dart
├── presentation/
│   ├── presentation.dart
│   ├── providers/
│   │   ├── providers.dart
│   │   ├── bid_item_provider.dart
│   │   └── entry_quantity_provider.dart
│   ├── screens/
│   │   ├── screens.dart
│   │   ├── quantities_screen.dart
│   │   └── quantity_calculator_screen.dart
│   └── widgets/
│       ├── widgets.dart
│       ├── quantity_summary_header.dart
│       ├── bid_item_card.dart
│       └── bid_item_detail_sheet.dart
├── utils/
│   └── budget_sanity_checker.dart
├── di/
│   └── quantities_providers.dart
└── quantities.dart
```

## Data Layer

### Models (`data/models/`)

**BidItem** — project-level pay item extracted from bid documents or created manually.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `String` | UUID, auto-generated |
| `projectId` | `String` | Required — scopes bid items to a project |
| `itemNumber` | `String` | Item ID from bid document (e.g., "1", "1.1") |
| `description` | `String` | Line item description |
| `unit` | `String` | Unit of measurement (EA, FT, SY, CY, etc.) |
| `bidQuantity` | `double` | Bid quantity (total to complete) |
| `unitPrice` | `double?` | Price per unit — nullable; OCR may miss it |
| `bidAmount` | `double?` | Total from source PDF. Preferred over `bidQuantity * unitPrice` when present (avoids OCR misread inflation) |
| `measurementPayment` | `String?` | M&P description text enriched from PDF |
| `createdByUserId` | `String?` | Supabase auth user ID |
| `createdAt`, `updatedAt` | `DateTime` | Auto-set |

**EntryQuantity** — per-entry quantity logged against a bid item.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `String` | UUID, auto-generated |
| `entryId` | `String` | FK to daily_entries |
| `bidItemId` | `String` | FK to bid_items |
| `quantity` | `double` | Amount completed in this entry |
| `notes` | `String?` | Optional work notes |
| `projectId` | `String?` | Denormalized; auto-resolved from parent entry on insert if null |
| `createdByUserId` | `String?` | Supabase auth user ID |
| `createdAt`, `updatedAt` | `DateTime` | Auto-set |

### Datasources

**`BidItemLocalDatasource`** extends `ProjectScopedDatasource<BidItem>`.
- Table: `bid_items`, ordered by `item_number ASC`
- Extra methods: `getByItemNumber(projectId, itemNumber)`, `search(projectId, query)`

**`EntryQuantityLocalDatasource`** extends `GenericLocalDatasource<EntryQuantity>`.
- Table: `entry_quantities`
- Extra methods: `getByEntryId`, `getByBidItemId`, `getTotalUsedForBidItem`, `getTotalUsedByProject` (JOIN on daily_entries), `softDeleteByEntryId` (sets `deleted_at`/`deleted_by` to drive change_log), `deleteByBidItemId`, `getCountByEntry`
- Override `insert`: auto-resolves `project_id` from parent `daily_entries` row when missing

**`BidItemRemoteDatasource`** extends `BaseRemoteDatasource<BidItem>`.
- Table: `bid_items`
- Extra methods: `getByProjectId`, `search`

**`EntryQuantityRemoteDatasource`** extends `BaseRemoteDatasource<EntryQuantity>`.
- Table: `entry_quantities`
- Extra methods: `getByEntryId`, `getByBidItemId`, `deleteByEntryId`

## Domain Layer

### Repository Interfaces (`domain/repositories/`)

**`BidItemRepository`** implements `ProjectScopedRepository<BidItem>`:
```
getByItemNumber(projectId, itemNumber) → BidItem?
search(projectId, query) → List<BidItem>
updateBidItem(bidItem) → RepositoryResult<BidItem>
deleteByProjectId(projectId) → void
insertAll(bidItems) → void
```
Inherits from base: `getById`, `getAll`, `getByProjectId`, `getByProjectIdPaged`, `create`, `update`, `delete`, `save`, `getPaged`, `getCount`, `getCountByProject`

**`EntryQuantityRepository`** implements `BaseRepository<EntryQuantity>`:
```
getByEntryId(entryId) → List<EntryQuantity>
getByBidItemId(bidItemId) → List<EntryQuantity>
getTotalUsedForBidItem(bidItemId) → double
getTotalUsedByProject(projectId) → Map<String, double>
create(quantity) → RepositoryResult<EntryQuantity>
updateQuantity(quantity) → RepositoryResult<EntryQuantity>
deleteByEntryId(entryId) → void
deleteByBidItemId(bidItemId) → void
getCountByEntry(entryId) → int
insertAll(quantities) → void
saveQuantitiesForEntry(entryId, quantities) → RepositoryResult<void>
```

### Domain Models (`domain/models/`)

**`ImportBatchResult`** — result of a batch bid item import operation.
- `importedCount: int` — items successfully imported
- `duplicateCount: int` — items skipped due to duplicates
- `replacedCount: int` — items replaced (when using replace strategy)
- `errors: List<String>` — errors encountered
- `isSuccess: bool` — true when `errors.isEmpty`
- `totalProcessed: int` — sum of all three counts

**`DuplicateStrategy`** (enum, same file) — `skip`, `replace`, `error`

### Repository Implementations (`data/repositories/`)

**`BidItemRepositoryImpl`** implements `BidItemRepository`:
- Constructor: `BidItemRepositoryImpl(BidItemLocalDatasource)`
- `create` checks for duplicate `itemNumber` within project before inserting
- `updateBidItem` validates existence and checks for item number collision on rename
- `insertAll` delegates to local datasource for batch import

**`EntryQuantityRepositoryImpl`** implements `EntryQuantityRepository`:
- Constructor: `EntryQuantityRepositoryImpl(EntryQuantityLocalDatasource)`
- `create` validates `quantity >= 0`
- `updateQuantity` validates existence and `quantity >= 0`
- `deleteByEntryId` delegates to `softDeleteByEntryId` (preserves change_log audit trail)
- `saveQuantitiesForEntry` soft-deletes existing then batch-inserts replacement list

## Presentation Layer

### Providers

**`BidItemProvider`** extends `BaseListProvider<BidItem, BidItemRepository>`:
- Viewer role guard on `createItem`, `updateItem`, `deleteItem` via `canWrite` callback
- Search state: `_searchQuery` with `filteredBidItems` computed getter
- Pagination: `loadItemsPaged`, `loadMoreItems`, `pagedItems`, `hasMoreItems`
- Import: `importBatch(items, {strategy})` → `ImportBatchResult`; handles skip/replace/error strategies with deduplication against in-memory items
- M&P enrichment: `enrichWithMeasurementPayment(matches)` updates `measurementPayment` field on matched items
- Convenience aliases: `bidItems`, `loadBidItems(projectId)`, `createBidItem`, `updateBidItem`, `deleteBidItem`, `getBidItemById`, `getBidItemByNumber`

**`EntryQuantityProvider`** extends `ChangeNotifier`:
- State: `_quantities` (for current entry), `_usedByBidItem` (Map<bidItemId, total> cache), `_currentEntryId`
- Load methods: `loadQuantitiesForEntry(entryId)`, `loadTotalUsedByProject(projectId)`
- CRUD: `addQuantity`, `updateQuantity`, `removeQuantity` — update `_usedByBidItem` cache in-place
- Bulk: `saveQuantitiesForEntry(entryId, quantities)` — delegates to repo, reloads totals from DB
- Cascades: `deleteQuantitiesForEntry`, `deleteQuantitiesForBidItem`
- Queries: `getTotalUsedForBidItem` (cache-first), `getQuantitiesForBidItemFromDb` (DB query), `getCountForEntry`

### Screens

**`QuantitiesScreen`** — project-level bid item list.
- Loads via `BidItemProvider.loadBidItems` + `EntryQuantityProvider.loadTotalUsedByProject` in `addPostFrameCallback`
- Sort options: item number, description, value (ascending/descending)
- Search: client-side filter on `itemNumber`, `description`, `unit`
- Budget discrepancy banner: `BudgetSanityChecker.hasDiscrepancy` → shows `AppBudgetWarningChip` when totals diverge > 10%
- PDF import: delegates to `PdfImportHelper.importFromPdf`
- Item tap: opens `BidItemDetailSheet.show`

**`QuantityCalculatorScreen`** — tabbed calculator launched from entry wizard.
- Tabs: HMA Tonnage, Concrete Yards, Area, Volume, Linear
- Returns `QuantityCalculatorResult` via `Navigator.pop` when "Use Result" is tapped
- Saves calculation history via `CalculatorProvider.saveCalculation`

### Widgets

**`QuantitySummaryHeader`** — gradient card showing total contract value and item count.
- Inputs: `itemCount: int`, `totalValue: double`

**`BidItemCard`** — list tile for a bid item showing bid qty / used / remaining, progress bar, unit price, and total value.
- Inputs: `item: BidItem`, `usedQuantity: double`, `onTap: VoidCallback`
- Progress bar turns red when `percentUsed > 1.0` (over-run)

**`BidItemDetailSheet`** — modal bottom sheet with full bid item detail.
- Inputs: `item: BidItem`, `usedQuantity: double`
- Static factory: `BidItemDetailSheet.show(context, item, usedQuantity)`
- Sections: M&P description (if present), quantity breakdown, progress bar with %, contract value

## Utils

**`BudgetSanityChecker`** (`utils/budget_sanity_checker.dart`) — static utility, no instance needed.
- `hasDiscrepancy(items, {threshold = 0.10})` — returns `true` if `|bidAmount total - recalculated total| / recalculated > threshold`
- Guards: returns `false` if no items have `bidAmount` (nothing to compare)
- Logs discrepancy details via `Logger.db` when detected

## DI

**`quantities_providers.dart`** (`di/quantities_providers.dart`) — Tier 4 providers.

```dart
List<SingleChildWidget> quantityProviders({
  required BidItemRepository bidItemRepository,
  required EntryQuantityRepository entryQuantityRepository,
  required AuthProvider authProvider,
})
```

- Wires `BidItemProvider(bidItemRepository)` with `canWrite = () => authProvider.canEditFieldData`
- Wires `EntryQuantityProvider(entryQuantityRepository)`

## Key Patterns

### Two-Tier Model
BidItems are project-level pay items (the contract line items). EntryQuantities are per-entry usage records referencing those items. A single BidItem can accumulate EntryQuantity records across many daily entries. `EntryQuantityProvider._usedByBidItem` caches the per-item totals so the quantities screen can render progress bars without N+1 queries.

### Budget Calculation Priority
`bidAmount` (from source PDF) is preferred over `bidQuantity * unitPrice` when displaying totals. This avoids 1000x inflation from OCR comma/period misreads on unit prices. `BudgetSanityChecker` detects when the two methods diverge significantly and surfaces a warning in the UI.

### Soft Delete for Sync Safety
`EntryQuantityLocalDatasource.softDeleteByEntryId` sets `deleted_at`/`deleted_by` instead of hard-deleting. This ensures SQLite triggers fire `UPDATE` events into `change_log`, so deletions propagate to Supabase on the next sync cycle.

### Batch Import with Duplicate Handling
`BidItemProvider.importBatch` deduplicates against in-memory items using `getBidItemByNumber`. Three strategies: `skip` (default), `replace` (preserve existing ID), `error` (fail fast). Uses `repository.insertAll` for efficient batch writes.

### M&P Enrichment
After PDF M&P extraction, `BidItemProvider.enrichWithMeasurementPayment(matches)` writes `measurementPayment` text to matched bid items without triggering a full reload where possible.

## Relationships

### Consumed by
- **entries** — `EntryQuantityProvider` tracks quantities per daily entry; entry wizard launches `QuantityCalculatorScreen`
- **dashboard** — reads bid item totals and used quantities for budget overview widgets
- **projects** — `QuantitiesScreen` is accessed from the project detail; bid items are scoped to `projectId`

### Depends on
- **projects** — `ProjectProvider.selectedProject` drives the active project context in `QuantitiesScreen`
- **pdf** — `PdfImportHelper` orchestrates PDF → bid item extraction; `BidItemProvider.importBatch` + `enrichWithMeasurementPayment` consume results
- **auth** — `AuthProvider.canEditFieldData` gates write operations in `BidItemProvider`
- **calculator** — `QuantityCalculatorScreen` uses `CalculatorProvider` and `CalculatorService` from the calculator feature

## Offline Behavior

Fully offline. All bid item storage, quantity tracking, and budget calculations run against SQLite. Remote datasources exist for Supabase sync but are not called directly from providers — the sync engine reads the `change_log` table populated by SQLite triggers on `bid_items` and `entry_quantities`.
