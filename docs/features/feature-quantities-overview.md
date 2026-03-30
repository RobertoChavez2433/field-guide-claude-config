---
feature: quantities
type: overview
scope: Bid Items & Quantity Tracking
updated: 2026-03-30
---

# Quantities Feature Overview

## Purpose

The Quantities feature manages bid items extracted from project bid documents and tracks quantities completed during daily work. Bid items represent individual line items in a project budget (e.g., "Item 1: Excavation, 1000 CY @ $5/CY"). Inspectors track completion progress by recording quantities completed in daily entries, enabling real-time budget tracking and project progress monitoring.

## Key Responsibilities

- **Bid Item Management**: Store extracted bid items from PDF documents (via `pdf` feature)
- **Quantity Tracking**: Record quantities completed per bid item in daily entries
- **Budget Tracking**: Calculate budget used and remaining based on quantity completion
- **Quantity Queries**: Filter and search bid items by project, status, category
- **Progress Summaries**: Calculate total quantities completed, percentage complete, budget metrics
- **Quantity Editing**: Manually create or edit bid items if PDF extraction unavailable
- **Budget Sanity Checking**: Validate budget figures via `BudgetSanityChecker`

## Key Files

### Domain Models
| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/quantities/data/models/bid_item.dart` | `BidItem` | Bid item with pricing and quantity fields |
| `lib/features/quantities/data/models/entry_quantity.dart` | `EntryQuantity` | Entry-specific quantity tracking model |
| `lib/features/quantities/domain/models/import_batch_result.dart` | `ImportBatchResult` | Result of a batch bid-item import operation |

### Data Sources (4 total)
| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/quantities/data/datasources/local/bid_item_local_datasource.dart` | `BidItemLocalDatasource` | SQLite reads/writes for bid items |
| `lib/features/quantities/data/datasources/local/entry_quantity_local_datasource.dart` | `EntryQuantityLocalDatasource` | SQLite reads/writes for entry quantities |
| `lib/features/quantities/data/datasources/remote/bid_item_remote_datasource.dart` | `BidItemRemoteDatasource` | Supabase sync for bid items |
| `lib/features/quantities/data/datasources/remote/entry_quantity_remote_datasource.dart` | `EntryQuantityRemoteDatasource` | Supabase sync for entry quantities |

### Domain Repository Interfaces (2 total)
| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/quantities/domain/repositories/bid_item_repository.dart` | `BidItemRepository` | Abstract contract for bid item persistence |
| `lib/features/quantities/domain/repositories/entry_quantity_repository.dart` | `EntryQuantityRepository` | Abstract contract for entry quantity persistence |

### Repository Implementations (2 total)
| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/quantities/data/repositories/bid_item_repository_impl.dart` | `BidItemRepositoryImpl` | Concrete bid item repository |
| `lib/features/quantities/data/repositories/entry_quantity_repository_impl.dart` | `EntryQuantityRepositoryImpl` | Concrete entry quantity repository |

### Providers (2 total)
| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/quantities/presentation/providers/bid_item_provider.dart` | `BidItemProvider` | Bid item state management |
| `lib/features/quantities/presentation/providers/entry_quantity_provider.dart` | `EntryQuantityProvider` | Entry quantity state management |

### Screens (2 total)
| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/quantities/presentation/screens/quantities_screen.dart` | `QuantitiesScreen` | Quantity tracking and bid item list UI |
| `lib/features/quantities/presentation/screens/quantity_calculator_screen.dart` | `QuantityCalculatorScreen` | Budget/quantity calculator UI |

### Widgets (3 total)
| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/quantities/presentation/widgets/bid_item_card.dart` | `BidItemCard` | Card displaying a single bid item |
| `lib/features/quantities/presentation/widgets/bid_item_detail_sheet.dart` | `BidItemDetailSheet` | Bottom sheet with full bid item details |
| `lib/features/quantities/presentation/widgets/quantity_summary_header.dart` | `QuantitySummaryHeader` | Summary header showing totals and progress |

### Utilities
| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/quantities/utils/budget_sanity_checker.dart` | `BudgetSanityChecker` | Validates budget figures for consistency |

## Data Sources

- **SQLite**: Persists bid items and entry-specific quantities via local datasources
- **Supabase**: Remote datasources sync bid items and entry quantities to cloud
- **PDF Extraction**: Bid items extracted from project PDFs (via `pdf` feature), result wrapped in `ImportBatchResult`
- **Daily Entries**: Quantities completed recorded in entries (via `entries` feature)

## Integration Points

**Required by:**
- `entries` — Entry detail screen references bid items for quantity entry
- `dashboard` — Budget and quantity metrics for project overview
- `projects` — Bid items are scoped to projects; project context drives all queries

**Depends on:**
- `core/database` — SQLite schema for `bid_items` and `entry_quantities` tables
- `projects` — Bid items are project-scoped
- `pdf` — Extracted bid items imported from PDF documents

## Offline Behavior

Quantities are **fully offline-capable**. Bid item creation, quantity tracking, and budget calculations occur entirely offline. All data persists in SQLite. Cloud sync handles async push via the remote datasources. Inspectors can track quantities entirely offline; sync happens during dedicated sync operations.

## Edge Cases & Limitations

- **Quantity Extraction**: Relies on PDF extraction quality; manual verification often required
- **Partial Completion**: Quantities may be updated incrementally (not required to match bid quantity)
- **Negative Quantities**: No validation; quantity can exceed bid quantity (overage tracking)
- **Pricing Changes**: Unit prices extracted from PDF; no historical price tracking if updated
- **Multi-Unit Items**: Items with different units (CY, tons, LF) require manual unit tracking
- **Budget Overruns**: No automatic alerts if quantities exceed budget; manual monitoring required
- **Deletion**: Soft-delete only; entries referencing deleted items remain accessible

## Detailed Specifications

See `architecture-decisions/quantities-constraints.md` for:
- Hard rules on quantity validation and negative handling
- Budget calculation semantics and rounding
- Bid item extraction quality thresholds

See `rules/database/schema-patterns.md` for:
- SQLite schema for bid_items and entry_quantities tables
- Indexing for efficient project-scoped queries
