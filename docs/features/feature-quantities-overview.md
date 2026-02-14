---
feature: quantities
type: overview
scope: Bid Items & Quantity Tracking
updated: 2026-02-13
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

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/quantities/data/models/bid_item.dart` | Bid item model with pricing and quantity |
| `lib/features/quantities/data/models/entry_quantity.dart` | Entry-specific quantity tracking |
| `lib/features/quantities/data/repositories/bid_item_repository.dart` | Bid item CRUD operations |
| `lib/features/quantities/data/repositories/entry_quantity_repository.dart` | Quantity tracking |
| `lib/features/quantities/presentation/providers/bid_item_provider.dart` | Bid item state management |
| `lib/features/quantities/presentation/providers/entry_quantity_provider.dart` | Quantity state management |
| `lib/features/quantities/presentation/screens/quantities_screen.dart` | Quantity tracking UI |
| `lib/features/quantities/presentation/screens/quantity_calculator_screen.dart` | Budget calculator |

## Data Sources

- **SQLite**: Persists bid items and entry-specific quantities
- **PDF Extraction**: Bid items extracted from project PDFs (via `pdf` feature)
- **Daily Entries**: Quantities completed recorded in entries (via `entries` feature)

## Integration Points

**Depends on:**
- `core/database` - SQLite schema for bid_items and entry_quantities tables
- `pdf` - Extracted bid items from PDF documents
- `entries` - Quantity completion data recorded in entries
- `projects` - Bid items scoped to projects

**Required by:**
- `dashboard` - Budget and quantity metrics for project overview
- `entries` - Entry detail screen references bid items for quantity entry
- `sync` - Quantity data synced to Supabase

## Offline Behavior

Quantities are **fully offline-capable**. Bid item creation, quantity tracking, and budget calculations occur entirely offline. All data persists in SQLite. Cloud sync handles async push. Inspectors can track quantities entirely offline; sync happens during dedicated sync operations.

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

