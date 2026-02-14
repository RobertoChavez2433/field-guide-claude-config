---
feature: entries
type: overview
scope: Daily Job Site Entry Management
updated: 2026-02-13
---

# Entries Feature Overview

## Purpose

The Entries feature enables construction inspectors to create and manage daily job site reports. Each entry captures weather conditions, site activities, safety measures, personnel, equipment, contractors, and attached photos. Entries support offline creation, draft-to-complete workflow, and signature-based submission for compliance and documentation.

## Key Responsibilities

- **Daily Entry Creation**: Capture date, weather, temperature, activities, and safety information for each job site visit
- **Site Documentation**: Record personnel, equipment, contractors involved in daily work
- **Photo Attachment**: Link photos captured on-site to specific entries
- **Quantity Tracking**: Reference extracted bid items and track quantities completed
- **Entry Status Management**: Draft → Complete → Submitted lifecycle with signature support
- **Entry Aggregation**: Display entries as calendar view or list for project review
- **Data Validation**: Ensure required fields (location, weather, activities) are complete before submission

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/entries/data/models/daily_entry.dart` | DailyEntry model with weather, activities, signature fields |
| `lib/features/entries/data/repositories/daily_entry_repository.dart` | CRUD operations for entries |
| `lib/features/entries/presentation/providers/daily_entry_provider.dart` | Entry state management |
| `lib/features/entries/presentation/screens/home_screen.dart` | Calendar and entry list view |
| `lib/features/entries/presentation/screens/report_screen.dart` | Entry details and editing |
| `lib/features/entries/presentation/screens/entry_wizard_screen.dart` | Multi-step entry creation |

## Data Sources

- **SQLite**: Persists daily entries, contractors, personnel, equipment, and quantities locally
- **Photos**: Links to photos stored in `photos` feature
- **Bid Items**: References extracted bid items from `quantities` feature
- **Contractors**: Links to contractor and equipment data from `contractors` feature
- **Weather Data**: Optional integration with `weather` feature (currently placeholder)

## Integration Points

**Depends on:**
- `core/database` - SQLite schema for entries and related entities
- `contractors` - Contractor, equipment, and personnel type data
- `photos` - Photo storage and retrieval
- `quantities` - Bid items for quantity tracking
- `locations` - Project locations for entry references
- `projects` - Project context for entries

**Required by:**
- `dashboard` - Entry data for home screen statistics and summaries
- `sync` - Entry data synced to Supabase after completion
- `toolbox` - Form responses linked to entries (optional)
- `pdf` - Entries may reference extracted PDF bid items

## Offline Behavior

Entries are **fully offline-capable**. Inspectors can create, edit, and complete entries without network connectivity. All data is stored locally until sync operations occur. Entry creation is immediate; changes persist in SQLite. Sync is deferred until connectivity available (handled by `sync` feature).

## Edge Cases & Limitations

- **Signature Capture**: Requires biometric signature or tap-based signature widget; no digital PKI verification
- **Photo References**: Entries can reference existing photos; new photos must be created via `photos` feature
- **Contractor Assignment**: Contractors must be pre-created in project setup before assignment to entry
- **Multi-Location Support**: Entries reference single location per date; multi-location work requires separate entries
- **Status Immutability**: Entry status transitions are one-way (Draft → Complete → Submitted); no rollback
- **Signature Timestamp**: `signedAt` auto-populated when signature captured; cannot be manually edited

## Detailed Specifications

See `architecture-decisions/entries-constraints.md` for:
- Hard rules on entry status transitions and immutability
- Validation requirements for complete/submitted entries
- Offline behavior and sync status semantics

See `rules/database/schema-patterns.md` for:
- SQLite schema design for entries and relationships
- Foreign key constraints and cascade behavior
- Indexing strategy for date-based queries

